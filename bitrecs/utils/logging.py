
import os
import logging
import bittensor as bt
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, timezone
from typing_extensions import List
from logging.handlers import RotatingFileHandler
from bitrecs.protocol import BitrecsRequest


EVENTS_LEVEL_NUM = 38
DEFAULT_LOG_BACKUP_COUNT = 10

SCHEMA_UPDATE_CUTOFF = datetime(2025, 4, 1, tzinfo=timezone.utc)


def setup_events_logger(full_path, events_retention_size):
    logging.addLevelName(EVENTS_LEVEL_NUM, "EVENT")

    logger = logging.getLogger("event")
    logger.setLevel(EVENTS_LEVEL_NUM)

    def event(self, message, *args, **kws):
        if self.isEnabledFor(EVENTS_LEVEL_NUM):
            self._log(EVENTS_LEVEL_NUM, message, args, **kws)

    logging.Logger.event = event

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        os.path.join(full_path, "events.log"),
        maxBytes=events_retention_size,
        backupCount=DEFAULT_LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(EVENTS_LEVEL_NUM)
    logger.addHandler(file_handler)

    return logger




timestamp_file = 'timestamp.txt'

def write_timestamp(current_time):
    tmp_file = timestamp_file + '.tmp'
    with open(tmp_file, 'w') as f:
        f.write(str(current_time))
    os.replace(tmp_file, timestamp_file)  # Atomic operation to replace the file


def read_timestamp():
    try:
        with open(timestamp_file, 'r') as f:
            timestamp_str = f.read()
            return float(timestamp_str)
    except (FileNotFoundError, ValueError):
        return None


def remove_timestamp_file():
    if os.path.exists(timestamp_file):
        os.remove(timestamp_file)


def log_miner_responses(step: int, responses: List[BitrecsRequest]) -> None:
    try:        
        frames = []
        for response in responses:
            headers = response.to_headers()
            df = pd.json_normalize(headers)          
            frames.append(df)
        final = pd.concat(frames)
        cwd = os.getcwd()
        p = os.path.join(cwd, 'miner_responses')
        if not os.path.exists(p):
            os.makedirs(p)        
        if len(final) > 0:
            utc_now = datetime.now(timezone.utc)
            created_at = utc_now.strftime("%Y-%m-%d_%H-%M-%S")
            full_path = os.path.join(p, f'miner_responses_step_{step}_{created_at}.csv')
            final.to_csv(full_path, index=False)
        bt.logging.info(f"Miner responses logged {len(final)}")
    except Exception as e:
        bt.logging.error(f"Error in logging miner responses: {e}")
        pass




def update_table_schema(conn: sqlite3.Connection, required_columns: list) -> None:
    """Update table schema to include any missing columns before cutoff date."""
    if datetime.now(timezone.utc) > SCHEMA_UPDATE_CUTOFF:
        return
        
    cursor = conn.cursor()
    # Get existing columns
    cursor.execute("PRAGMA table_info(miner_responses)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # Add any missing columns
    for col in required_columns:
        if col not in existing_columns:
            bt.logging.info(f"Adding missing column: {col}")
            alter_sql = f'ALTER TABLE miner_responses ADD COLUMN "{col}" TEXT'
            cursor.execute(alter_sql)
    conn.commit()


def log_miner_responses_to_sql(step: int, responses: List[BitrecsRequest]) -> None:
    try:
        frames = []
        for response in responses:
            if not isinstance(response, BitrecsRequest):
                bt.logging.warning(f"Skipping invalid response type: {type(response)}")
                continue
            data = {
                **response.to_headers(),
                **response.to_dict()
            }
            df = pd.json_normalize(data)          
            frames.append(df)
        final = pd.concat(frames)

        if len(final) > 0:
            utc_now = datetime.now(timezone.utc)
            created_at = utc_now.strftime("%Y-%m-%d %H:%M:%S")            
            db_path = os.path.join(os.getcwd(), 'miner_responses.db')            
            conn = sqlite3.connect(db_path)
            try:
                final['step'] = step
                final['created_at'] = created_at                
                dtype_dict = {col: 'TEXT' for col in final.columns}                
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='miner_responses';")
                table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    final.to_sql('miner_responses', conn, index=False, dtype=dtype_dict)
                else:
                    # Update schema if needed
                    update_table_schema(conn, list(final.columns))
                    final.to_sql('miner_responses', conn, index=False, if_exists='append', dtype=dtype_dict)
                conn.commit()
            except sqlite3.Error as e:
                bt.logging.error(f"SQLite error: {e}")
                conn.rollback()
            finally:
                conn.close()

        bt.logging.info(f"Miner responses logged {len(final)}")
    except Exception as e:
        bt.logging.error(f"Error in logging miner responses: {str(e)}")
        bt.logging.error(f"Columns in dataframe: {list(final.columns)}")