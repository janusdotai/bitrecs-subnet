import wandb
from typing import Dict, Any, Optional

class WandbHelper:
    def __init__(
        self,
        project_name: str = "template-validator-testnet",
        entity: str = "bitrecs",
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None
    ):
        """
        Initialize WandB tracking
        """
        self.default_config = {
            "network": "testnet",
            "neuron_type": "validator",
            "sample_size": 5,
            "num_concurrent_forwards": 1,
            "vpermit_tao_limit": 1024,
            "run_name": f"validator_{wandb.util.generate_id()}"
        }
        
        if config:
            self.default_config.update(config)
            
        self.run = wandb.init(
            project=project_name,
            entity=entity,
            config=self.default_config,
            tags=tags,
            reinit=True
        )
        
    def log_weights(self, step: int, weights: Dict[str, float], prefix: str = "weights"):
        """
        Log weight updates to wandb
        """
        metrics = {f"{prefix}/{k}": v for k, v in weights.items()}
        metrics["step"] = step
        wandb.log(metrics)
    
    def log_metrics(self, metrics: Dict[str, float]):
        """
        Log arbitrary metrics to wandb
        """
        wandb.log(metrics)
        
    
    def finish(self):
        """
        Close wandb run
        """
        if self.run:
            self.run.finish()