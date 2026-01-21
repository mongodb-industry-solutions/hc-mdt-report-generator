"""
Mistral Client Configuration

Provides a centralized way to switch between API and local Mistral clients.
Configure MISTRAL_MODE in .env file to either 'api' or 'local' to control which client is used.
"""

import logging
from typing import Type, Union

logger = logging.getLogger(__name__)

# Import settings to get configuration from .env
try:
    from config.settings import settings
    MISTRAL_MODE = settings.mistral_mode
    logger.info(f"🔧 Mistral mode loaded from settings: {MISTRAL_MODE}")
except ImportError:
    import os
    MISTRAL_MODE = os.environ.get('MISTRAL_MODE', 'api').lower()
    logger.warning("⚠️ Settings not available, falling back to environment variable")

def get_async_mistral_client():
    """
    Get the appropriate AsyncMistralClient based on configuration
    
    Returns:
        AsyncMistralClient class (either API or local version)
    """
    if MISTRAL_MODE == 'local':
        logger.info("🏠 Using local Mistral client (via infrastructure wrapper)")
        from infrastructure.llm.mistral_client import AsyncMistralClient
        return AsyncMistralClient
    else:
        logger.info("🌐 Using API Mistral client")
        from infrastructure.llm.mistral_client import AsyncMistralClient
        return AsyncMistralClient

def get_base_mistral_client():
    """
    Get the appropriate BaseMistralClient based on configuration
    
    Returns:
        BaseMistralClient class (either API or local version)
    """
    if MISTRAL_MODE == 'local':
        try:
            from services.base.local_mistral_client import LocalBaseMistralClient
            logger.info("🏠 Using local base Mistral client")
            return LocalBaseMistralClient
        except ImportError as e:
            logger.warning(f"⚠️ Local base Mistral client not available: {e}")
            logger.info("🌐 Falling back to API base Mistral client")
            from services.base.mistral_client import BaseMistralClient
            return BaseMistralClient
    else:
        logger.info("🌐 Using API base Mistral client")
        from services.base.mistral_client import BaseMistralClient
        return BaseMistralClient

# Convenience aliases for easy importing
AsyncMistralClient = get_async_mistral_client()
BaseMistralClient = get_base_mistral_client()

def set_mistral_mode(mode: str) -> None:
    """
    Set the Mistral mode programmatically
    
    Args:
        mode: Either 'api' or 'local'
    """
    global MISTRAL_MODE, AsyncMistralClient, BaseMistralClient
    
    if mode.lower() not in ['api', 'local']:
        raise ValueError("Mode must be either 'api' or 'local'")
    
    MISTRAL_MODE = mode.lower()
    
    # Update environment variable for compatibility
    import os
    os.environ['MISTRAL_MODE'] = MISTRAL_MODE
    
    # Update settings if available
    try:
        from config.settings import settings
        # Note: This won't persist to .env file, just updates runtime
        settings.mistral_mode = MISTRAL_MODE
        logger.info(f"🔄 Updated settings.mistral_mode to: {MISTRAL_MODE}")
    except ImportError:
        logger.warning("⚠️ Settings not available for runtime update")
    
    # Update the client classes
    AsyncMistralClient = get_async_mistral_client()
    BaseMistralClient = get_base_mistral_client()
    
    logger.info(f"🔄 Mistral mode set to: {MISTRAL_MODE}")
    logger.info("💡 Note: To persist this setting, update MISTRAL_MODE in your .env file")

def get_current_mode() -> str:
    """Get the current Mistral mode"""
    return MISTRAL_MODE

def is_local_mode() -> bool:
    """Check if using local mode"""
    return MISTRAL_MODE == 'local'

def is_api_mode() -> bool:
    """Check if using API mode"""
    return MISTRAL_MODE == 'api' 