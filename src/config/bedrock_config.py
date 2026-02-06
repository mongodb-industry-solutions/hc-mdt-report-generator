"""
Bedrock Client Configuration

Provides a centralized way to configure and access AWS Bedrock clients.
Configure BEDROCK_REGION and AWS_PROFILE in .env file to control access.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Import settings to get configuration from .env
try:
    from config.settings import settings
    BEDROCK_REGION = getattr(settings, 'bedrock_region', 'us-east-1')
    BEDROCK_MODEL = getattr(settings, 'bedrock_model', 'anthropic.claude-3-haiku-20240307-v1:0')
    logger.info(f"🔧 Bedrock region loaded from settings: {BEDROCK_REGION}")
    logger.info(f"🔧 Bedrock model loaded from settings: {BEDROCK_MODEL}")
except ImportError:
    BEDROCK_REGION = os.environ.get('BEDROCK_REGION', 'us-east-1')
    BEDROCK_MODEL = os.environ.get('BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')
    logger.warning("⚠️ Settings not available, falling back to environment variables")

def get_async_bedrock_client():
    """
    Get the AsyncBedrockClient
    
    Returns:
        AsyncBedrockClient class
    """
    logger.info("🤖 Using AWS Bedrock client")
    from infrastructure.llm.bedrock_client import AsyncBedrockClient
    return AsyncBedrockClient

# Convenience alias for easy importing
AsyncBedrockClient = get_async_bedrock_client()

def set_bedrock_region(region: str) -> None:
    """
    Set the Bedrock region programmatically
    
    Args:
        region: AWS region (e.g., 'us-east-1', 'us-west-2')
    """
    global BEDROCK_REGION
    
    BEDROCK_REGION = region
    
    # Update environment variable for compatibility
    os.environ['BEDROCK_REGION'] = BEDROCK_REGION
    
    # Update settings if available
    try:
        from config.settings import settings
        settings.bedrock_region = BEDROCK_REGION
        logger.info(f"🔄 Updated settings.bedrock_region to: {BEDROCK_REGION}")
    except ImportError:
        logger.warning("⚠️ Settings not available for runtime update")
    
    logger.info(f"🔄 Bedrock region set to: {BEDROCK_REGION}")

def set_bedrock_model(model: str) -> None:
    """
    Set the Bedrock model programmatically
    
    Args:
        model: Bedrock model ID (e.g., 'anthropic.claude-3-haiku-20240307-v1:0')
    """
    global BEDROCK_MODEL
    
    BEDROCK_MODEL = model
    
    # Update environment variable for compatibility
    os.environ['BEDROCK_MODEL'] = BEDROCK_MODEL
    
    # Update settings if available
    try:
        from config.settings import settings
        settings.bedrock_model = BEDROCK_MODEL
        logger.info(f"🔄 Updated settings.bedrock_model to: {BEDROCK_MODEL}")
    except ImportError:
        logger.warning("⚠️ Settings not available for runtime update")
    
    logger.info(f"🔄 Bedrock model set to: {BEDROCK_MODEL}")

def get_current_region() -> str:
    """Get the current Bedrock region"""
    return BEDROCK_REGION

def get_current_model() -> str:
    """Get the current Bedrock model"""
    return BEDROCK_MODEL

def is_bedrock_available() -> bool:
    """Check if Bedrock is properly configured"""
    try:
        import boto3
        # Try to create a session to verify credentials
        session = boto3.Session()
        region = session.region_name or BEDROCK_REGION
        return region is not None
    except Exception as e:
        logger.error(f"Bedrock not available: {e}")
        return False