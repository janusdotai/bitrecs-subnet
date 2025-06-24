# import torch
# import numpy as np
# from typing import Callable, Any
# from loguru import logger

# class classproperty:
#     def __init__(self, func: Callable):
#         self.fget = func

#     def __get__(self, instance, owner: Any):
#         return self.fget(owner)


# class GPUInfo:
#     async def log_gpu_info():

#         gpus = GPUInfo.n_gpus
#         if gpus == 0:
#             logger.warning("WARNING - No GPUs found on this server")
#             return
        
#         try:

#             logger.info(f"Total GPU memory: {GPUInfo.total_memory} GB")
#             logger.info(f"Free GPU memory:  {GPUInfo.free_memory} GB")
#             logger.info(f"Used GPU memory: {GPUInfo.used_memory} GB")
#             logger.info(f"GPU utilization: {GPUInfo.gpu_utilization * 100}%")

#         except Exception as e:
#             logger.error(f"Error in log_gpu_info: {e}")
#             logger.warning("WARNING - GPUs found on this server with problems")
#             pass
        

#     @classproperty
#     def total_memory(cls):
#         return np.sum([torch.cuda.get_device_properties(i).total_memory / (1024**3) for i in range(cls.n_gpus)])

#     @classproperty
#     def used_memory(cls):
#         return cls.total_memory - cls.free_memory

#     @classproperty
#     def free_memory(cls):
#         return np.sum([torch.cuda.mem_get_info(i)[0] / (1024**3) for i in range(cls.n_gpus)])

#     @classproperty
#     def n_gpus(cls):
#         return torch.cuda.device_count()

#     @classproperty
#     def gpu_utilization(cls):
#         return cls.used_memory / cls.total_memory
