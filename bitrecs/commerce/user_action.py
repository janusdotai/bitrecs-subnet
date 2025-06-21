import os
import bittensor as bt
import requests
from enum import Enum
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field


class ActionType(Enum):
    VIEW_PRODUCT = "VIEW_PRODUCT"
    ADD_TO_CART = "ADD_TO_CART"
    PURCHASE = "PURCHASE"
    

@dataclass
class UserAction:
    ip: str = field(default_factory=str)
    site_info: str = field(default_factory=str)
    user: str = field(default_factory=str)
    action: str = field(default_factory=str)
    sku: str = field(default_factory=str)
    hot_key: str = field(default=str)
    created_at: str = field(default_factory=str)

    
    @staticmethod
    def get_actions(hot_key: str) -> list["UserAction"]:
        """
        Load all the actions attributed to this miner
        """
        actions = []
        try:             
            proxy_url = os.environ.get("BITRECS_PROXY_URL").removesuffix("/")
            r = requests.get(f"{proxy_url}/miner/{hot_key}")
            actions = r.json()
        except Exception as e:
            bt.logging.error(f"load_user_actions Exception: {e}")
        return actions
    
    
    @staticmethod
    def get_actions_range(start_date: datetime, end_date: datetime) -> list["UserAction"]:
        """
        Load all the actions for miners in a range
        """
        actions = []
        try:
            dt_from = int(start_date.timestamp())
            dt_to = int(end_date.timestamp())
            if dt_from >= dt_to:                
                raise ValueError("Start date must be less than end date")
            proxy_url = os.environ.get("BITRECS_PROXY_URL").removesuffix("/")
            r = requests.get(f"{proxy_url}/miner/stats/from/{dt_from}/to/{dt_to}")
            actions = r.json()
        except Exception as e:
            bt.logging.error(f"load_user_actions Exception: {e}")
        return actions
    

    @staticmethod
    def get_default_range(days_ago=7) -> tuple:
        """
        Get the default range for the actions
        """        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_ago)
        return start_date, end_date
    
    
    @staticmethod
    def get_retro_range() -> tuple:
        """
        Get retroactive range for the actions to let merchants settle.
        End date: 30 days ago from today
        Start date: 60 days ago from today (30 days before end date)
        """        
        end_date = datetime.now(timezone.utc) - timedelta(days=30)
        start_date = end_date - timedelta(days=30)
        return start_date, end_date
        
        