import re
from pathlib import Path

"""
Global constants

Constants:
    ROOT_DIR (Path): Root directory of the project.
    MAX_DENDRITE_TIMEOUT (int): Length of seconds given to miners to respond to a dendrite request.
    MIN_QUERY_LENGTH (int): Minimum length of a query.
    MAX_QUERY_LENGTH (int): Maximum length of a query.
    MAX_RECS_PER_REQUEST (int): Maximum number of recommendations per request.
    MAX_CONTEXT_LENGTH (int): Maximum length of a context.
    MIN_CATALOG_SIZE (int): Minimum size of a request catalog.
    MAX_CATALOG_SIZE (int): Maximum size of a request catalog.
    MINER_BATTERY_INTERVAL (int): Length of seconds between miner checks.
    ACTION_SYNC_INTERVAL (int): Length of seconds between action syncs.
    VERSION_CHECK_INTERVAL (int): Length of seconds between version checks.
    CATALOG_DUPE_THRESHOLD (float): Threshold for duplicate products in a catalog.
    R2_SYNC_INTERVAL (int): Length of seconds between R2 syncs.
    RE_PRODUCT_NAME (Pattern): Regular expression to match valid product names.
    RE_REASON (Pattern): Regular expression to match valid reasons.

"""
ROOT_DIR = Path(__file__).parent.parent
MAX_DENDRITE_TIMEOUT = 5
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 30
MAX_RECS_PER_REQUEST = 20
MAX_CONTEXT_LENGTH = 200_000
MIN_CATALOG_SIZE = 6
MAX_CATALOG_SIZE = 100_000
MINER_BATTERY_INTERVAL = 900
ACTION_SYNC_INTERVAL = 1800
VERSION_CHECK_INTERVAL = 600
CATALOG_DUPE_THRESHOLD = 0.05
R2_SYNC_INTERVAL = 3600
RE_PRODUCT_NAME = re.compile(r"[^A-Za-z0-9 |-]")
RE_REASON = re.compile(r"[^A-Za-z0-9 ]")