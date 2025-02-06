from pathlib import Path

"""
Global constants

Constants:
    MAX_DENDRITE_TIMEOUT (int): Length of seconds given to miners to respond to a dendrite request.
    MIN_QUERY_LENGTH (int): Minimum length of a query.
    MAX_QUERY_LENGTH (int): Maximum length of a query.
    MAX_RECS_PER_REQUEST (int): Maximum number of recommendations per request.
    MAX_CONTEXT_LENGTH (int): Maximum length of a context.
    MIN_CATALOG_SIZE (int): Minimum size of a request catalog.
    MINER_BATTERY_INTERVAL (int): Length of seconds between miner checks.
    ACTION_SYNC_INTERVAL (int): Length of seconds between action syncs.
    VERSION_CHECK_INTERVAL (int): Length of seconds between version checks.
    CATALOG_DUPE_THRESHOLD (float): Threshold for duplicate products in a catalog.
    
"""
ROOT_DIR = Path(__file__).parent.parent
MAX_DENDRITE_TIMEOUT = 8
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 30
MAX_RECS_PER_REQUEST = 20
MAX_CONTEXT_LENGTH = 200_000
MIN_CATALOG_SIZE = 10
MAX_CATALOG_SIZE = 100_000
MINER_BATTERY_INTERVAL = 180
ACTION_SYNC_INTERVAL = 180
VERSION_CHECK_INTERVAL = 300
CATALOG_DUPE_THRESHOLD = 0.05