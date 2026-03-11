"""
Base Mistral Client

Provides a common interface for all Mistral AI service clients.
Handles initialization, API key management, and common error handling.
Supports both API and local modes based on MISTRAL_MODE environment variable.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BaseMistralClient:
    """Base class for all Mistral AI service clients with conditional local/API support"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._initialized = False
        self.system_prompt: Optional[str] = None
        
        # Check MISTRAL_MODE environment variable
        self.mistral_mode = os.environ.get("MISTRAL_MODE", "api").lower()
        
        if self.mistral_mode == "local":
            logger.info(f"🏠 Initializing {service_name} with LOCAL Mistral client")
            self._init_local_client()
        else:
            logger.info(f"🌐 Initializing {service_name} with API Mistral client")
            self._init_api_client()
    
    def _init_local_client(self):
        """Initialize local Mistral client"""
        try:
            from services.base.local_mistral_client import LocalBaseMistralClient
            self.client = LocalBaseMistralClient(self.service_name)
            self.model = "local-mistral"  # Simplified model name
            logger.info(f"✅ Local Mistral client initialized for {self.service_name}")
        except ImportError as e:
            logger.error(f"❌ Local Mistral client not available: {e}")
            # NEVER FALL BACK - raise error instead
            raise RuntimeError(
                f"Local Mistral mode requested but dependencies are missing: {e}. "
                "Please install required dependencies: pip install torch vllm>=0.8.1 mistral-common>=1.5.4"
            )
    
    def _init_api_client(self):
        """Initialize API Mistral client"""
        try:
            from mistralai.sdk import Mistral
            from mistralai import UserMessage, SystemMessage
            self.UserMessage = UserMessage
            self.SystemMessage = SystemMessage
            self.model = "mistral-small-latest"
            self.api_client = None  # Will be initialized in initialize()
            self.client = None  # Will be set in initialize() for OCR compatibility
            logger.info(f"✅ API Mistral client setup for {self.service_name}")
        except ImportError as e:
            logger.error(f"❌ Mistral API client not available: {e}")
            raise
    
    async def initialize(self) -> None:
        """Initialize Mistral client connection"""
        if self._initialized:
            return
            
        try:
            if self.mistral_mode == "local":
                # Local client handles its own initialization
                if hasattr(self.client, 'initialize'):
                    await self.client.initialize()
                self._initialized = True
                logger.info(f"🏠 Local Mistral {self.service_name} client initialized successfully")
            else:
                # API client initialization
                api_key = os.environ.get("MISTRAL_API_KEY")
                if not api_key:
                    logger.warning(f"⚠️ MISTRAL_API_KEY not found - {self.service_name} will use fallback responses")
                    self._initialized = True
                    return
                
                from mistralai.sdk import Mistral
                self.api_client = Mistral(api_key=api_key)
                self.client = self.api_client  # Set self.client for OCR and other services
                self._initialized = True
                logger.info(f"🌐 API Mistral {self.service_name} client initialized successfully")
                
        except Exception as e:
            # Log the failure and propagate the error so callers know initialization failed
            logger.error(
                f"Failed to initialize Mistral {self.service_name} client: {e}"
            )
            # Leave _initialized as False and re-raise to signal an unusable client
            raise
    
    def ensure_initialized(self) -> None:
        """Ensure client is initialized"""
        if not self._initialized:
            raise RuntimeError(f"Mistral {self.service_name} client not initialized. Call initialize() first.")
    
    @property
    def is_ready(self) -> bool:
        """Check if client is ready for use"""
        return self._initialized
    
    async def generate_text_with_system_prompt(self, system_prompt: str, user_prompt: str, 
                                             max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate text using Mistral AI with a system prompt (works with both local and API)
        """
        self.ensure_initialized()
        
        try:
            if self.mistral_mode == "local":
                # Use local client
                if hasattr(self.client, 'generate_text_with_system_prompt'):
                    return await self.client.generate_text_with_system_prompt(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                else:
                    logger.warning("Local client doesn't support generate_text_with_system_prompt")
                    return "Local processing unavailable"
            else:
                # Use API client
                if not self.api_client:
                    logger.warning("API client not available - returning fallback response")
                    return "API processing unavailable - using fallback"
                
                messages = [
                    self.SystemMessage(content=system_prompt),
                    self.UserMessage(content=user_prompt)
                ]
                
                response = self.api_client.chat.complete(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                if response and response.choices:
                    return response.choices[0].message.content.strip()
                else:
                    logger.warning("Empty response from Mistral AI")
                    return "No response generated"
                    
        except Exception as e:
            logger.error(f"Error generating text with Mistral AI: {e}")
            # Return fallback instead of raising
            return f"Processing error - fallback response for {self.service_name}"

    async def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate text using Mistral AI (simplified interface)"""
        return await self.generate_text_with_system_prompt("", prompt, max_tokens, temperature)