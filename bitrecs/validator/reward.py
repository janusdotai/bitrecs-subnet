# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2024 Bitrecs

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import math
import time
import json
import traceback
import numpy as np
import bittensor as bt
import jsonschema
import json_repair
from typing import List
from bitrecs.commerce.user_action import UserAction, ActionType
from bitrecs.protocol import BitrecsRequest
from bitrecs.commerce.product import Product, ProductFactory
from bitrecs.utils import constants as CONST

BASE_BOOST = 1/256
BASE_REWARD = 0.80
MAX_BOOST = 0.20
ALPHA_TIME_DECAY = 0.05

ACTION_WEIGHTS = {
    ActionType.VIEW_PRODUCT.value: 0.05,
    ActionType.ADD_TO_CART.value: 0.10,
    ActionType.PURCHASE.value: 0.85,
}


def does_sku_exist(sku: str, store_catalog: List[Product]) -> bool:
    """
    Check if sku exists in the context
    """
    if not sku or not store_catalog:
        return False
    if len(store_catalog) == 0:
        return False
    match = sku.lower().strip()
    for product in store_catalog:
        if product["sku"].lower().strip() == match:
            return True
    return False
   

def validate_result_schema(num_recs: int, results: list) -> bool:
    """
    Ensure results from Miner match the required schema
    """
    if num_recs < 1 or num_recs > CONST.MAX_RECS_PER_REQUEST:
        return False
    if len(results) != num_recs:
        bt.logging.error("Error validate_result_schema num_recs mismatch")
        return False
    
    schema = {
        "type": "object",
        "properties": {
            "sku": {"type": "string"},
            "name": {"type": "string"},
            "price": {"type": ["string", "number"]},
            "reason": {"type": "string"}
        },
        "required": ["sku", "name", "price", "reason"],
    }

    count = 0
    for item in results:
        try:            
            #thing = json.loads(item)
            thing = json_repair.loads(item)
            validated = jsonschema.validate(thing, schema)
            if validated is not None:
                return False            
            count += 1
        except json.decoder.JSONDecodeError as e:            
            bt.logging.trace(f"JSON JSONDecodeError ERROR: {e}")
            break
        except jsonschema.exceptions.ValidationError as e:            
            bt.logging.trace(f"JSON ValidationError ERROR: {e}")
            break
        except Exception as e:            
            bt.logging.trace(f"JSON Exception ERROR: {e}")
            break

    return count == len(results)


def calculate_miner_boost(hotkey: str, actions: List[UserAction]) -> float:
    """
    Reward miners who generate positive actions on ecommerce sites

    """
    try:
        if not actions or len(actions) == 0:
            return 0.0

        miner_actions = [a for a in actions if a["hot_key"].lower() == hotkey.lower()]
        if len(miner_actions) == 0:
            bt.logging.trace(f"Miner {hotkey} has no actions")
            return 0.0

        views = [v for v in miner_actions if v["action"] == ActionType.VIEW_PRODUCT.name]
        add_to_carts = [a for a in miner_actions if a["action"] == ActionType.ADD_TO_CART.name]
        purchases = [p for p in miner_actions if p["action"] == ActionType.PURCHASE.name]        

        if len(views) == 0 and len(add_to_carts) == 0 and len(purchases) == 0:
            bt.logging.trace(f"Miner {hotkey} has no parsed actions - skipping boost")
            return 0.0
        
        vf = ACTION_WEIGHTS[ActionType.VIEW_PRODUCT.value] * len(views)
        af = ACTION_WEIGHTS[ActionType.ADD_TO_CART.value] * len(add_to_carts)
        pf = ACTION_WEIGHTS[ActionType.PURCHASE.value] * len(purchases)
        total_boost = vf + af + pf
        bt.logging.trace(f"Miner {hotkey} total_boost: {total_boost} from views: ({len(views)}) add_to_carts: ({len(add_to_carts)}) purchases: ({len(purchases)})")

        # miner has no actions this round
        if total_boost == 0:
            return 0.0
        
        #TODO review this       
        if total_boost > BASE_BOOST:
            total_boost = MAX_BOOST / (1 + math.exp(-total_boost + BASE_BOOST))
        
        return min(max(total_boost, 0.0), MAX_BOOST)
    except Exception as e:
        bt.logging.error(f"Error in calculate_miner_boost: {e}")
        traceback.print_exc()
        return 0.0


def reward(
    num_recs: int, 
    store_catalog: list[Product], 
    response: BitrecsRequest,
    actions: List[UserAction]
) -> float:
    """
    Score the Miner's response to the BitrecsRequest 

    Nubmer of recommendations should match the requested number of recommendations
    Recommendations must exist in the original catalog
    Unique recommendations in the response is expected
    Malformed JSON or invliad skus will result in a 0.0 reward
    Miner rewards are boosted based on end-user actions on the ecommerce sites to encourage positive recs

    Returns:
    - float: The reward value for the miner.
    """    
    
    bt.logging.trace("*************** VALIDATOR REWARD *****************")
    
    try:
        score = 0.0
        if response.is_timeout:
            bt.logging.error(f"Miner {response.miner_uid} is_timeout is True, status: {response.dendrite.status_code}")
            return 0.0
        if response.is_failure:            
            bt.logging.error(f"Miner {response.miner_uid} is_failure is True, status: {response.dendrite.status_code}")
            return 0.0
        if not response.is_success:
            bt.logging.error(f"Miner {response.miner_uid} is_success is False, status: {response.dendrite.status_code}")
            return 0.0
        if len(response.results) != num_recs:
            bt.logging.error(f"Miner {response.miner_uid} num_recs mismatch, expected {num_recs} but got {len(response.results)}")
            return 0.0
        if not validate_result_schema(num_recs, response.results):
            bt.logging.error(f"Miner {response.miner_uid} failed schema validation: {response.miner_hotkey}")
            return 0.0

        valid_items = set()
        for result in response.results:
            try:
                product: Product = json_repair.loads(result)
                sku = product["sku"]
                if sku.lower() == response.query.lower():
                    bt.logging.warning(f"Miner {response.miner_uid} has query in results: {response.miner_hotkey}")
                    return 0.0
                                    
                if sku in valid_items:
                    bt.logging.warning(f"Miner {response.miner_uid} has duplicate results: {response.miner_hotkey}")
                    return 0.0
                
                if not does_sku_exist(sku, store_catalog):
                    bt.logging.warning(f"Miner {response.miner_uid} has invalid results: {response.miner_hotkey}")
                    return 0.00
                
                valid_items.add(sku)
            except Exception as e:
                bt.logging.error(f"JSON ERROR: {e}, miner data: {response.miner_hotkey}")
                return 0.0

        if len(valid_items) != num_recs:
            bt.logging.warning(f"Miner {response.miner_uid} invalid number of valid_items: {response.miner_hotkey}")
            return 0.0

        score = BASE_REWARD
        headers = response.to_headers()
        if "bt_header_dendrite_process_time" in headers:
            dendrite_time = float(headers["bt_header_dendrite_process_time"])
            bt.logging.trace(f"\033[32mMiner {response.miner_uid} dendrite_time: {dendrite_time} \033[0m")

            #TODO - warn of minerx
            if dendrite_time < 1.0:
                bt.logging.trace(f"\033[33mWARNING Miner {response.miner_uid} suspect dendrite_time: {dendrite_time} \033[0m")

            score = score - ALPHA_TIME_DECAY * float(dendrite_time)
        else:
            bt.logging.error(f"Error in reward: dendrite_time not found in headers")
            return 0.0
        
        # Adjust the rewards based on the actions
        boost = calculate_miner_boost(response.miner_hotkey, actions)        
        if boost > 0:
            bt.logging.trace(f"\033[32m Miner {response.miner_uid} boost: {boost} \033[0m")
            bt.logging.trace(f"\033[32m current: {score} \033[0m")
            score = score + boost
            bt.logging.trace(f"\033[32m after: {score} \033[0m")
        else:
            bt.logging.trace(f"\033[33m Miner {response.miner_uid} boost: {boost} \033[0m")

        bt.logging.info(f"\033[1;32m Final {score} \033[0m")
        return score
    except Exception as e:
        bt.logging.error(f"Error in rewards: {e}, miner data: {response}")
        return 0.0


def get_rewards(
    num_recs: int,
    ground_truth: BitrecsRequest,
    responses: List[BitrecsRequest],
    actions: List[UserAction] = None
) -> np.ndarray:
    """
    Returns an array of rewards for the given query and responses.

    Args:
    - num_recs (int): The number of results expected per miner response.
    - ground_truth (BitrecsRequest): The original ground truth which contains the catalog and query
    - responses (List[float]): A list of responses from the miners.
    - actions (List[UserAction]): A list of user actions across all miners. 

    Returns:
    - np.ndarray: An array of rewards for the given query and responses.
    """

    if num_recs < 1 or num_recs > CONST.MAX_RECS_PER_REQUEST:
        bt.logging.error(f"Invalid number of recommendations: {num_recs}")
        return np.zeros(len(responses), dtype=float)    
    
    store_catalog: list[Product] = ProductFactory.try_parse_context(ground_truth.context)
    if len(store_catalog) < CONST.MIN_CATALOG_SIZE or len(store_catalog) > CONST.MAX_CATALOG_SIZE:
        bt.logging.error(f"Invalid catalog size: {len(store_catalog)}")
        return np.zeros(len(responses), dtype=float)
    
    if not actions or len(actions) == 0:
        bt.logging.warning(f"\033[1;31m WARNING - no actions found in get_rewards \033[0m")
        
    return np.array(
        [reward(num_recs, store_catalog, response, actions) for response in responses], dtype=float
    )


