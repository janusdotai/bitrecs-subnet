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


import os
import time
import bittensor as bt
import asyncio
from datetime import timedelta
from bitrecs.base.validator import BaseValidatorNeuron
from bitrecs.commerce.user_action import UserAction
from bitrecs.utils.r2 import ValidatorUploadRequest
from bitrecs.utils.runtime import execute_periodically
from bitrecs.utils.uids import get_random_miner_uids2, ping_miner_uid
from bitrecs.utils.version import LocalMetadata
from bitrecs.validator import forward
from bitrecs.protocol import BitrecsRequest
from bitrecs.utils import constants as CONST
from bitrecs.utils.r2 import put_r2_upload
from dotenv import load_dotenv
load_dotenv()


class Validator(BaseValidatorNeuron):
    """
    Your validator neuron class. You should use this class to define your validator's behavior. In particular, you should replace the forward function with your own logic.

    This class inherits from the BaseValidatorNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a validator such as keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        self.load_state()
        self.total_request_in_interval = 0
        if not os.environ.get("BITRECS_PROXY_URL"):
            raise Exception("Please set the BITRECS_PROXY_URL environment variable.")
        


    async def forward(self, pr : BitrecsRequest = None):
        """
        Validator forward pass. Consists of:
        - Generating the query
        - Querying the miners
        - Getting the responses
        - Selecting a top candidate from the responses
        - Return top candidate to the client
        - Rewarding the miners
        - Updating the scores
        """                
        return await forward(self, pr)
    
     
    @execute_periodically(timedelta(seconds=CONST.VERSION_CHECK_INTERVAL))
    async def version_sync(self):
        bt.logging.trace(f"Version sync ran at {int(time.time())}")
        try:
            self.local_metadata = LocalMetadata.local_metadata()
            self.local_metadata.uid = self.uid
            self.local_metadata.hotkey = self.wallet.hotkey.ss58_address
            local_head = self.local_metadata.head
            remote_head = self.local_metadata.remote_head
            code_version = self.local_metadata.version
            bt.logging.info(f"Bitrecs Version:\033[32m {code_version}\033[0m")
            if local_head != remote_head:
                bt.logging.info(f"Head:\033[33m {local_head}\033[0m / Remote: \033[33m{remote_head}\033[0m")                
                bt.logging.warning(f"{self.neuron_type} version mismatch: Please update your code to the latest version.")
            else:
                 bt.logging.info(f"Head:\033[32m {local_head}\033[0m / Remote: \033[32m{remote_head}\033[0m")
        except Exception as e:
            bt.logging.error(f"Failed to get version with exception: {e}")
        return
    

    @execute_periodically(timedelta(seconds=CONST.MINER_BATTERY_INTERVAL))
    async def miner_sync(self):
        """
            Checks the miners in the metagraph for connectivity and updates the active miners list.
        """
        bt.logging.trace(f"\033[1;32m Validator miner_sync running {int(time.time())}.\033[0m")
        bt.logging.trace(f"neuron.sample_size: {self.config.neuron.sample_size}")
        bt.logging.trace(f"vpermit_tao_limit: {self.config.neuron.vpermit_tao_limit}")
        bt.logging.trace(f"block {self.subtensor.block} on step {self.step}")        
        
        #available_uids = get_random_miner_uids(self, k=self.config.neuron.sample_size, exclude=excluded)
        available_uids = get_random_miner_uids2(self, k=self.config.neuron.sample_size)
        bt.logging.trace(f"get_random_uids: {available_uids}")
        
        chosen_uids = available_uids
        bt.logging.trace(f"chosen_uids: {chosen_uids}")
        if len(chosen_uids) == 0:
            bt.logging.error("\033[1;31mNo random qualified miners found - check your connectivity \033[0m")
            return
        
        chosen_uids = list(set(chosen_uids))
        selected_miners = []
        for uid in chosen_uids:            
            bt.logging.trace(f"Checking uid: {uid} with stake {self.metagraph.S[uid]} and trust {self.metagraph.T[uid]}")
            if uid == self.uid:                
                continue
            if not self.metagraph.axons[uid].is_serving:
                continue
            # if self.metagraph.S[uid] == 0:
            #     bt.logging.trace(f"uid: {uid} stake 0T, skipping")
            #     continue
            this_stake = float(self.metagraph.S[uid])
            stake_limit = float(self.config.neuron.vpermit_tao_limit)
            if this_stake > stake_limit:
                bt.logging.trace(f"uid: {uid} has stake {this_stake} > {stake_limit}, skipping")
                continue

            try:                
                if ping_miner_uid(self, uid, 8091, 3):
                    bt.logging.trace(f"\033[1;32m ping: {uid}:OK \033[0m")
                    selected_miners.append(uid)
                else:
                    bt.logging.trace(f"\033[1;33m ping: {uid}:FALSE \033[0m")
            except Exception as e:
                bt.logging.trace(f"\033[1;33 {e} \033[0m")
                continue
        if len(selected_miners) == 0:
            self.active_miners = []
            bt.logging.error("\033[31mNo active miners selected in round - check your connectivity \033[0m")
            return
        
        self.active_miners = list(set(selected_miners))
        bt.logging.info(f"\033[1;32m Active miners: {self.active_miners}  \033[0m")
        

    @execute_periodically(timedelta(seconds=CONST.ACTION_SYNC_INTERVAL))
    async def action_sync(self):
        """
        Periodically fetch user actions 
        For mainnet, we retro 30 days as min end date
        """
        #sd, ed = UserAction.get_default_range(days_ago=1)
        sd, ed = UserAction.get_retro_range()
        bt.logging.trace(f"Gathering user actions for range: {sd} to {ed}")
        try:
            self.user_actions = UserAction.get_actions_range(start_date=sd, end_date=ed)
            bt.logging.trace(f"Success - User actions size: \033[1;32m {len(self.user_actions)} \033[0m")
        except Exception as e:
            bt.logging.error(f"Failed to get user actions with exception: {e}")
        return
    
    
    @execute_periodically(timedelta(seconds=CONST.R2_SYNC_INTERVAL))
    async def response_sync(self):
        """
        Periodically sync miner responses to R2
        """

        r2_enabled = self.config.r2.sync_on
        if not r2_enabled:
            bt.logging.trace(f"R2 Sync OFF at {int(time.time())}")        
            bt.logging.warning(f"R2 Sync is OFF set --r2.sync_on to enable")
            return

        start_time = time.perf_counter()
        bt.logging.info(f"Starting R2 Sync at {int(time.time())}")
        if not self.wallet or not self.wallet.hotkey:
            bt.logging.error("Hotkey not found - skipping R2 sync")
            return
        try:
            keypair = self.wallet.hotkey
            bt.logging.trace(f"Using hotkey with address: {keypair.ss58_address}")
                
            update_request = ValidatorUploadRequest(
                hot_key=self.wallet.hotkey.ss58_address,
                val_uid=self.config.netuid,
                step=str(self.step),
                llm_provider="OPEN_ROUTER",
                llm_model="ignored"
            )
            bt.logging.trace(f"Sending response sync request: {update_request}")
            sync_result = put_r2_upload(update_request, keypair)
            if sync_result:
                bt.logging.trace(f"\033[1;32m Success - R2 updated sync_result: {sync_result} \033[0m")
            else:
                bt.logging.error(f"\033[1;31m Failed to update R2 \033[0m")

        except Exception as e:
            bt.logging.error(f"Failed to update R2 with exception: {e}")
        finally:
            duration = time.perf_counter() - start_time
            bt.logging.info(f"R2 Sync complete in {duration:.2f} seconds")
    
    

async def main():
    bt.logging.info(f"\033[32m Starting Bitrecs Validator\033[0m ... {int(time.time())}")    
    with Validator() as validator:
        start_time = time.time()      
        while True:
            tasks = [
                asyncio.create_task(validator.version_sync()),
                asyncio.create_task(validator.miner_sync()),
                asyncio.create_task(validator.action_sync()),
                asyncio.create_task(validator.response_sync())
            ]                    
            await asyncio.gather(*tasks)
            
            bt.logging.info(f"Validator {validator.uid} running... {int(time.time())}")
            if time.time() - start_time > 300:
                bt.logging.info(
                    f"---Total request in last 5 minutes: {validator.total_request_in_interval}"
                )
                start_time = time.time()
                validator.total_request_in_interval = 0
            await asyncio.sleep(15)

if __name__ == "__main__": 
    asyncio.run(main())
