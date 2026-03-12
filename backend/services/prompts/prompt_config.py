"""
Prompt Configuration

Centralized configuration for all prompt-related constants, settings, and parameters.
This module provides consistent configuration across all AI model interactions.
"""

from typing import Dict, Any
from enum import Enum

# Model Configuration
class ModelConfig:
    """Model configuration constants"""
    
    # Model names
    OPENAI_GPT35 = "gpt-3.5-turbo"
    OPENAI_GPT4 = "gpt-4"
    BEDROCK_CLAUDE = "anthropic.claude-v2"
    
    # Temperature settings for different use cases
    TEMPERATURE_DETERMINISTIC = 0.1  # For structured data extraction
    TEMPERATURE_BALANCED = 0.3       # For categorization
    TEMPERATURE_CREATIVE = 0.7       # For content generation
    
    # Token limits
    MAX_TOKENS_SHORT = 500           # For categorization
    MAX_TOKENS_MEDIUM = 2000         # For normalization
    MAX_TOKENS_LONG = 4000           # For structured extraction
    
    # Timeout settings (seconds)
    TIMEOUT_QUICK = 30               # For simple operations
    TIMEOUT_STANDARD = 60            # For normal operations
    TIMEOUT_EXTENDED = 120           # For complex operations

# Prompt Quality Standards
class PromptStandards:
    """Standards and guidelines for prompt quality"""
    
    # Required sections in system prompts
    REQUIRED_SYSTEM_SECTIONS = [
        "role_definition",      # Clear role definition
        "task_description",     # What the AI should do
        "output_format"         # How to format responses
    ]
    
    # Best practices for prompt construction
    BEST_PRACTICES = {
        "clarity": "Use clear, unambiguous language",
        "specificity": "Provide specific instructions and examples",
        "consistency": "Maintain consistent formatting and terminology",
        "completeness": "Include all necessary context and constraints",
        "testability": "Ensure prompts can be validated and tested"
    }
    
    # Maximum recommended prompt lengths
    MAX_SYSTEM_PROMPT_LENGTH = 1000
    MAX_USER_PROMPT_LENGTH = 8000

# Prompt Versioning
class PromptVersion:
    """Version tracking for prompts"""
    
    VERSION_SCHEMA = "MAJOR.MINOR.PATCH"
    
    # Current versions by prompt type
    VERSIONS = {
        "document_categorization": "1.0.0",
        "document_extraction": "1.0.0", 
        "document_chunking": "1.0.0",
        "text_normalization": "1.0.0",
        "entity_extraction": "1.0.0",
        "mdt_report_iterative": "1.0.0",
        "ner_prompts": "1.0.0"
    }

# Service-specific configurations
class ServiceConfig:
    """Configuration for different services"""
    
    DOCUMENT_CATEGORIZATION = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_BALANCED,
        "max_tokens": ModelConfig.MAX_TOKENS_SHORT,
        "timeout": ModelConfig.TIMEOUT_QUICK
    }
    
    DOCUMENT_EXTRACTION = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_DETERMINISTIC,
        "max_tokens": ModelConfig.MAX_TOKENS_LONG,
        "timeout": ModelConfig.TIMEOUT_STANDARD
    }
    
    DOCUMENT_CHUNKING = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_BALANCED,
        "max_tokens": ModelConfig.MAX_TOKENS_MEDIUM,
        "timeout": ModelConfig.TIMEOUT_STANDARD
    }
    
    TEXT_NORMALIZATION = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_DETERMINISTIC,
        "max_tokens": ModelConfig.MAX_TOKENS_LONG,
        "timeout": ModelConfig.TIMEOUT_STANDARD
    }
    
    ENTITY_EXTRACTION = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_DETERMINISTIC,
        "max_tokens": ModelConfig.MAX_TOKENS_LONG,
        "timeout": ModelConfig.TIMEOUT_EXTENDED
    }
    
    MDT_REPORT = {
        "model": ModelConfig.OPENAI_GPT35,
        "temperature": ModelConfig.TEMPERATURE_DETERMINISTIC,
        "max_tokens": ModelConfig.MAX_TOKENS_LONG,
        "timeout": ModelConfig.TIMEOUT_EXTENDED
    }

def get_service_config(service_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Configuration dictionary for the service
        
    Raises:
        ValueError: If service name is not recognized
    """
    config_map = {
        "document_categorization": ServiceConfig.DOCUMENT_CATEGORIZATION,
        "document_extraction": ServiceConfig.DOCUMENT_EXTRACTION,
        "document_chunking": ServiceConfig.DOCUMENT_CHUNKING,
        "text_normalization": ServiceConfig.TEXT_NORMALIZATION,
        "entity_extraction": ServiceConfig.ENTITY_EXTRACTION,
        "mdt_report": ServiceConfig.MDT_REPORT
    }
    
    if service_name not in config_map:
        raise ValueError(f"Unknown service: {service_name}")
    
    return config_map[service_name].copy()

def get_prompt_version(prompt_type: str) -> str:
    """
    Get version for a specific prompt type.
    
    Args:
        prompt_type: Type of prompt
        
    Returns:
        Version string
        
    Raises:
        ValueError: If prompt type is not recognized
    """
    if prompt_type not in PromptVersion.VERSIONS:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    return PromptVersion.VERSIONS[prompt_type] 