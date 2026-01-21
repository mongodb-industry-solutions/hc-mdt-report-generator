import time  
import asyncio  
import logging  
import os
from mistralai import Mistral  
from typing import Dict, Any  
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  
from config.ner_config import settings  
  
logger = logging.getLogger(__name__)  

# Define critical error class at module level so it can be used in retry decorator
class CriticalAPIError(Exception):
    """Critical error that should abort the entire process without retrying"""
    pass
  
class AsyncMistralClient:  
    def __init__(self):  
        logger.info("🔧 Initializing AsyncMistralClient...")  
        
        # Check MISTRAL_MODE to determine which client to use
        self.mistral_mode = os.environ.get("MISTRAL_MODE", "api").lower()
        
        if self.mistral_mode == "local":
            logger.info("🏠 MISTRAL_MODE=local detected - routing to local client")
            try:
                from services.base.local_mistral_client import LocalBaseMistralClient
                self._local_client = LocalBaseMistralClient("EntityExtraction")
                self._is_local = True
                logger.info("✅ Local AsyncMistralClient routing enabled with singleton LocalBaseMistralClient")
            except ImportError as e:
                logger.error(f"❌ Local client not available: {e}")
                raise RuntimeError(f"Local mode requested but dependencies missing: {e}")
        else:
            logger.info("🌐 MISTRAL_MODE=api detected - using API client")
            
            # Debug API key presence
            api_key = settings.mistral_api_key
            if not api_key:
                # Try getting from environment directly
                api_key = os.environ.get("MISTRAL_API_KEY", "")
                logger.warning(f"⚠️ No API key found in settings, checking environment: {'Key found' if api_key else 'No key found'}")
            else:
                logger.info("✅ API key found in settings")
                
            # Force setting API key in environment for other components
            if api_key:
                os.environ["MISTRAL_API_KEY"] = api_key
                
            # Initialize client with API key
            self.client = Mistral(api_key=api_key)
            self.model = settings.mistral_model  
            self.max_retries = getattr(settings, 'mistral_max_retries', 3)  
            self.timeout_seconds = getattr(settings, 'mistral_timeout', 60)  
            self._is_local = False
            logger.info(f"✅ API AsyncMistralClient initialized with model: {self.model}")  
  
    async def __aenter__(self):  
        logger.info("🚪 Entering AsyncMistralClient context")  
        if self._is_local:
            # Initialize LocalBaseMistralClient
            await self._local_client.initialize()
        return self  
  
    async def __aexit__(self, exc_type, exc_val, exc_tb):  
        logger.info("🚪 Exiting AsyncMistralClient context")  
        if self._is_local:
            # LocalBaseMistralClient doesn't need cleanup in __aexit__
            return False
            
        if exc_type:  
            logger.error(f"❌ Exception in context: {exc_type.__name__}: {exc_val}")  
              
        if hasattr(self.client, 'close'):  
            try:  
                await self.client.close()  
                logger.info("🔌 Client connection closed")  
            except Exception as e:  
                logger.warning(f"⚠️ Error closing client: {e}")  
        return False  

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Only retry regular exceptions, not CriticalAPIError
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def invoke_mistral_sync_with_retry(self, system_prompt: str, prompt: str) -> str:
        """Synchronous Mistral call with built-in retry logic - routes based on mode."""
        if self._is_local:
            return self._local_client.invoke_mistral_sync_with_retry(system_prompt, prompt)
        
        # Original API logic for non-local mode
        logger.info("🤖 Starting Mistral API call with retry logic...")  
        logger.debug(f"Model: {self.model}")  
        logger.debug(f"System prompt length: {len(system_prompt) if system_prompt else 0}")  
        logger.debug(f"User prompt length: {len(prompt) if prompt else 0}")  
          
        try:
            # Check if we have a valid API key
            api_key = settings.mistral_api_key or os.environ.get("MISTRAL_API_KEY", "")
            
            # Create a new client instance with the current API key to ensure it's fresh
            client = Mistral(api_key=api_key)
            
            logger.info("📤 Sending request to Mistral API...")  
              
            response = client.chat.complete(  
                model=self.model,  
                messages=[  
                    {"role": "system", "content": system_prompt},  
                    {"role": "user", "content": prompt}  
                ],  
                temperature=getattr(settings, 'mistral_temperature', 0.1),  
                max_tokens=getattr(settings, 'mistral_max_tokens', 4000)  
            )  
              
            if response and response.choices and len(response.choices) > 0:  
                content = response.choices[0].message.content.strip()  
                logger.info("✅ Mistral API call successful")  
                logger.debug(f"Response length: {len(content)} characters")  
                return content  
            else:  
                logger.error("❌ Empty response from Mistral API")  
                raise Exception("Empty response from Mistral API")  
              
        except Exception as e:  
            logger.error(f"❌ API call failed: {e}")  
            raise  
  
    async def invoke_mistral_async_robust(self, system_prompt: str, prompt: str, timeout_override: int = None) -> str:
        """Async wrapper with timeout and comprehensive error handling - routes based on mode."""
        if self._is_local:
            return await self._local_client.invoke_mistral_async_robust(system_prompt, prompt, timeout_override)
        
        # Original API logic for non-local mode
        timeout = timeout_override or self.timeout_seconds  
        logger.info(f"🔄 Starting robust async Mistral call (timeout: {timeout}s)...")  
        
        try:  
            # Use asyncio.timeout for the entire operation  
            async with asyncio.timeout(timeout):  
                result = await asyncio.to_thread(  
                    self.invoke_mistral_sync_with_retry,  
                    system_prompt,  
                    prompt  
                )  
                logger.info("✅ Robust async Mistral call completed")  
                return result  
                  
        except asyncio.TimeoutError:  
            logger.error(f"⏰ Mistral API call timed out after {timeout} seconds")  
            raise TimeoutError(f"Mistral API call timed out after {timeout} seconds")  
        except Exception as e:  
            logger.error(f"❌ Robust async Mistral call failed: {type(e).__name__}: {e}")  
            raise
  
    async def invoke_mistral_async(self, system_prompt: str, prompt: str) -> str:
        """Simple async Mistral call - routes based on mode."""
        if self._is_local:
            return await self._local_client.invoke_mistral_async(system_prompt, prompt)
        
        # For API mode, use the robust version
        return await self.invoke_mistral_async_robust(system_prompt, prompt)