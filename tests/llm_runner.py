# import json
# from pydantic import BaseModel, Field
# from typing import List, Optional, Dict, Set, Tuple
# from datetime import datetime
# import asyncio
# from dataclasses import asdict
# import secrets
# from random import SystemRandom

# from bitrecs.protocol import BitrecsRequest
# from bitrecs.commerce.product import Product
# from bitrecs.llms.prompt_factory import PromptFactory
# from bitrecs.llms.factory import LLM, LLMFactory

# safe_random = SystemRandom()

# class ModelResult(BaseModel):
#     """Track results and metadata for each model run"""
#     model_name: str
#     is_cloud: bool
#     duration: float = 0.0
#     request: Optional[BitrecsRequest] = None
#     error: Optional[str] = None
#     created_at: datetime = Field(default_factory=datetime.now)


# class ConcurrentLLMRunner:
#     """Handles concurrent execution of local and cloud LLM requests"""
    
#     def __init__(self, products: List[Product], num_recs: int = 6):
#         self.products = products
#         self.num_recs = num_recs
#         self.group_id = secrets.token_hex(16)
    
#     async def run_single_model(
#         self, 
#         sku: str,
#         model: str,
#         is_cloud: bool = False
#     ) -> ModelResult:
#         """Execute a single model and return results"""
#         start_time = datetime.now()
#         try:
#             # Prepare prompt
#             context = json.dumps([asdict(p) for p in self.products])
#             factory = PromptFactory(
#                 sku=sku,
#                 context=context,
#                 num_recs=self.num_recs,
#                 load_catalog=False
#             )
#             prompt = factory.generate_prompt()
            
#             # Query appropriate LLM
#             llm_response = LLMFactory.query_llm(
#                 server=LLM.OPEN_ROUTER if is_cloud else LLM.OLLAMA_LOCAL,
#                 model=model,
#                 system_prompt="You are a helpful assistant",
#                 temp=0.0,
#                 user_prompt=prompt
#             )
            
#             # Parse results
#             parsed_recs = PromptFactory.tryparse_llm(llm_response)
#             #assert len(parsed_recs) == self.num_recs
            
#             # Create BitrecsRequest
#             request = BitrecsRequest(
#                 created_at=datetime.now().isoformat(),
#                 user="test_user",
#                 num_results=self.num_recs,
#                 query=sku,
#                 context="[]",
#                 site_key=self.group_id,
#                 results=parsed_recs,
#                 models_used=[model],
#                 miner_uid=str(safe_random.randint(10, 1000)),
#                 miner_hotkey=secrets.token_hex(16)
#             )
            
#             duration = (datetime.now() - start_time).total_seconds()
#             return ModelResult(
#                 model_name=model,
#                 is_cloud=is_cloud,
#                 duration=duration,
#                 request=request
#             )
            
#         except Exception as e:
#             duration = (datetime.now() - start_time).total_seconds()
#             return ModelResult(
#                 model_name=model,
#                 is_cloud=is_cloud,
#                 duration=duration,
#                 error=str(e)
#             )
    
#     async def run_model_battery(
#         self,
#         sku: str,
#         local_models: List[str],
#         cloud_models: List[str],
#         include_random: bool = True,
#         num_random: int = 3
#     ) -> List[ModelResult]:
#         """Run all models concurrently"""
#         tasks = []
        
#         # Add random recommendation tasks if requested
#         if include_random:
#             for i in range(num_random):
                
#                 fake_recs = safe_random.sample(self.products, self.num_recs)
#                 req = BitrecsRequest(
#                     created_at=datetime.now().isoformat(),
#                     user="test_user",
#                     num_results=self.num_recs,
#                     query=sku,
#                     context="[]",
#                     site_key=self.group_id,
#                     results=[{"sku": r.sku} for r in fake_recs],
#                     models_used=[f"random-{i}"],
#                     miner_uid=str(safe_random.randint(10, 100)),
#                     miner_hotkey=secrets.token_hex(16)
#                 )
#                 result = ModelResult(
#                     model_name=f"random-{i}",
#                     is_cloud=False,
#                     request=req
#                 )
#                 tasks.append(result)
        
#         # Add local model tasks
#         for model in local_models:
#             task = self.run_single_model(sku, model, is_cloud=False)
#             tasks.append(task)
            
#         # Add cloud model tasks
#         for model in cloud_models:
#             task = self.run_single_model(sku, model, is_cloud=True)
#             tasks.append(task)
        
#         # Run all tasks concurrently
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         return [r for r in results if isinstance(r, ModelResult)]

#     def get_successful_requests(self, results: List[ModelResult]) -> List[BitrecsRequest]:
#         """Extract successful BitrecsRequests from results"""
#         return [r.request for r in results if r.request is not None]

#     def print_summary(self, results: List[ModelResult]):
#         """Print execution summary"""
#         print("\n=== Model Execution Summary ===")
#         print(f"Total models attempted: {len(results)}")
#         successful = len([r for r in results if r.request is not None])
#         print(f"Successful executions: {successful}")
#         print(f"Failed executions: {len(results) - successful}")
#         print("\nExecution times:")
#         for r in sorted(results, key=lambda x: x.duration):
#             status = "✓" if r.request else "✗"
#             print(f"{status} {r.model_name:30} {r.duration:6.2f}s")
#             if r.error:
#                 print(f"  Error: {r.error}")