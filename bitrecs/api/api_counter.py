import json
import os
import asyncio
import time
from datetime import date
from typing import Dict, Any
import bittensor as bt

class APICounter:
    def __init__(self, save_path: str, auto_save_interval: int = 60):
        self.save_path = save_path
        self.auto_save_interval = auto_save_interval
        self.last_save_time = time.time()
        self.dirty = False
        self._save_lock = asyncio.Lock()
        
        # Load once on initialization
        self._load_data()
        
        # Start background save task
        self._save_task = None
        if auto_save_interval > 0:
            self._start_auto_save()

    def _load_data(self):
        """Load data once on startup"""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r') as f:
                    self.proxy_logs = json.load(f)
            except Exception as e:
                bt.logging.error(f"Error loading API logs: {e}")
                self.proxy_logs = {}
        else:
            self.proxy_logs = {}

    def update(self, is_success: bool):
        """Update counters in memory only"""
        today = str(date.today())
        if today not in self.proxy_logs:
            self.proxy_logs[today] = {"success": 0, "fail": 0}
        
        if is_success:
            self.proxy_logs[today]["success"] += 1
        else:
            self.proxy_logs[today]["fail"] += 1
        
        self.dirty = True

    async def save_if_needed(self):
        """Save only if data has changed and enough time has passed"""
        if not self.dirty:
            return
            
        current_time = time.time()
        if current_time - self.last_save_time >= self.auto_save_interval:
            await self.save()

    async def save(self):
        """Async save to disk with locking"""
        async with self._save_lock:
            if not self.dirty:
                return
                
            try:
                # Write to temp file first, then atomic rename
                temp_path = f"{self.save_path}.tmp"
                with open(temp_path, 'w') as f:
                    json.dump(self.proxy_logs, f, indent=2)
                
                # Atomic rename
                os.rename(temp_path, self.save_path)
                
                self.dirty = False
                self.last_save_time = time.time()
                bt.logging.trace(f"API counter saved to {self.save_path}")
                
            except Exception as e:
                bt.logging.error(f"Error saving API logs: {e}")

    def _start_auto_save(self):
        """Start background auto-save task"""
        async def auto_save_loop():
            while True:
                await asyncio.sleep(self.auto_save_interval)
                await self.save_if_needed()
        
        self._save_task = asyncio.create_task(auto_save_loop())

    async def shutdown(self):
        """Clean shutdown - save any pending changes"""
        if self._save_task:
            self._save_task.cancel()
        await self.save()

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get stats for last N days"""
        from datetime import datetime, timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        total_success = 0
        total_fail = 0
        
        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            if date_str in self.proxy_logs:
                total_success += self.proxy_logs[date_str]["success"]
                total_fail += self.proxy_logs[date_str]["fail"]
            current_date += timedelta(days=1)
        
        return {
            "success": total_success,
            "fail": total_fail,
            "total": total_success + total_fail,
            "success_rate": total_success / (total_success + total_fail) if (total_success + total_fail) > 0 else 0
        }
