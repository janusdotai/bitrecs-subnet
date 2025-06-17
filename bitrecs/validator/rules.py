import bittensor as bt
from bitrecs.protocol import BitrecsRequest
from bitrecs.utils import constants as CONST


def validate_br_request(synapse: BitrecsRequest) -> bool:        
    if not isinstance(synapse, BitrecsRequest):
        bt.logging.error(f"Invalid synapse item: {synapse}")
        return False
    if len(synapse.query) < CONST.MIN_QUERY_LENGTH or len(synapse.query) > CONST.MAX_QUERY_LENGTH:
        bt.logging.error(f"Invalid synampse Query!: {synapse}")
        return False
    if len(synapse.results) != 0:
        bt.logging.error(f"Results it not empty!: {synapse}")
        return False
    if synapse.context is None or synapse.context == "":
        bt.logging.error(f"Context is empty!: {synapse}")
        return False
    if len(synapse.context) > CONST.MAX_CONTEXT_TEXT_LENGTH:
        bt.logging.error(f"Context is too long!: {synapse}")
        return False
    if len(synapse.models_used) != 0:
        bt.logging.error(f"Models used is not empty!: {synapse}")
        return False
    if synapse.site_key is None or synapse.site_key == "":
        bt.logging.error(f"Site key is empty!: {synapse}")
        return False
    if synapse.num_results < 1 or synapse.num_results > CONST.MAX_RECS_PER_REQUEST:
        bt.logging.error(f"Number of recommendations should be less than {CONST.MAX_RECS_PER_REQUEST}!: {synapse}")
        return False
    
    return True