# config/ner_config.py  
"""Configuration management for NER entity extraction."""  
  
import os  
from typing import Dict, List, Optional, Any  
from dataclasses import dataclass, field  
from pydantic_settings import BaseSettings  
from pydantic import Field
import json
import logging

logger = logging.getLogger(__name__)
  
class NERSettings(BaseSettings):  
    """NER configuration settings with validation."""  
      
    # API Configuration  
    mistral_api_key: str = ""  # Now optional, validated based on mode
    mistral_model: str = "mistral-small-2503"  
    mistral_mode: str = "api"  # Add mode setting with default
      
    # Processing Configuration - Default values (overridable at runtime)
    max_entities_per_batch: int = Field(default=10)
    max_content_size: int = Field(default=10000)
    chunk_overlapping: int = Field(default=20)
    max_concurrent_requests: int = Field(default=4)  # Backend-only setting
    aggregation_batch_size: int = Field(default=5)   # Backend-only setting
    continue_on_batch_errors: bool = Field(default=False)
      
    # Retry Configuration  
    max_retry_attempts: int = 3  
    retry_base_delay: float = 1.0  
    retry_max_delay: float = 10.0  
      
    # Rate Limiting  
    rate_limit_delay: float = 0.5  
      
    # Circuit Breaker Configuration  
    circuit_breaker_failure_threshold: int = 5  
    circuit_breaker_recovery_timeout: int = 30  
      
    # Logging Configuration  
    log_level: str = "INFO"  
    enable_progress_logging: bool = True  
    log_file_pattern: str = "ner_processing_{timestamp}.log"  
      
    class Config:  
        env_prefix = ""  
        env_file = ".env"  
        extra = "ignore"  
      
    # Mistral API key is optional; no validation enforced
  
@dataclass  
class ProcessingConfig:  
    """Configuration for entity processing workflow."""  
      
    enable_parallel_processing: bool = True  
    enable_caching: bool = True  
    enable_partial_results: bool = True  
    progress_save_interval: int = 10  # Save progress every N processed documents  
      
    # Fallback configuration  
    enable_fallback: bool = True  
    fallback_timeout: float = 5.0  

# Global settings instance  
settings = NERSettings()  


def update_ner_settings(config_dict: Dict[str, Any]) -> None:
    """
    Update NER settings dynamically at runtime.
    
    Args:
        config_dict: Dictionary with configuration values to update
    """
    if not config_dict:
        return
        
    if "max_entities_per_batch" in config_dict:
        settings.max_entities_per_batch = config_dict["max_entities_per_batch"]
        
    if "max_content_size" in config_dict:
        settings.max_content_size = config_dict["max_content_size"]
        
    if "chunk_overlapping" in config_dict:
        settings.chunk_overlapping = config_dict["chunk_overlapping"]
        
    if "max_concurrent_requests" in config_dict:
        settings.max_concurrent_requests = config_dict["max_concurrent_requests"]
        
    if "aggregation_batch_size" in config_dict:
        settings.aggregation_batch_size = config_dict["aggregation_batch_size"]

    if "continue_on_batch_errors" in config_dict:
        settings.continue_on_batch_errors = bool(config_dict["continue_on_batch_errors"])

