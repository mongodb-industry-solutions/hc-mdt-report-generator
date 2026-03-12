import boto3
from botocore.config import Config
import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Define critical error class at module level so it can be used in retry decorator
class CriticalBedrockError(Exception):
    """Critical error that should abort the entire process without retrying"""
    pass


class AsyncBedrockClient:
    """Implementation of AsyncBedrockClient class with generic LLM interface."""
     
    def __init__(self, aws_access_key: Optional[str] = None, aws_secret_key: Optional[str] = None,
                 assumed_role: Optional[str] = None, region_name: Optional[str] = "us-east-1") -> None:
        logger.info("🔧 Initializing AsyncBedrockClient...")
        self.region_name = region_name
        self.assumed_role = assumed_role
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.model_id = "anthropic.claude-3-haiku-20240307-v1:0"  # Claude 3 Haiku
        self.max_retries = 3
        self.timeout_seconds = 120
        self.bedrock_runtime = None
        logger.info(f"✅ AsyncBedrockClient initialized with model: {self.model_id}")
    
    def _get_bedrock_client(
            self,
            runtime: Optional[bool] = True,
    ):
        """Create a boto3 client for Amazon Bedrock, with optional configuration overrides."""
        if self.region_name is None:
            target_region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        else:
            target_region = self.region_name
        session_kwargs = {"region_name": target_region}
        client_kwargs = {**session_kwargs}
        
        profile_name = os.environ.get("AWS_PROFILE")
        
        if profile_name:
            session_kwargs["profile_name"] = profile_name
        
        retry_config = Config(
            region_name=target_region,
            retries={
                "max_attempts": 10,
                "mode": "standard",
            },
        )
        session = boto3.Session(**session_kwargs)
        
        if self.assumed_role:
            sts = session.client("sts")
            response = sts.assume_role(
                RoleArn=str(self.assumed_role),
                RoleSessionName="bedrock-admin"
            )
            client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
            client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
            client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]
        
        if self.aws_access_key and self.aws_secret_key:
            client_kwargs["aws_access_key_id"] = self.aws_access_key
            client_kwargs["aws_secret_access_key"] = self.aws_secret_key
        
        service_name = 'bedrock-runtime' if runtime else 'bedrock'
        
        bedrock_client = session.client(
            service_name=service_name,
            config=retry_config,
            **client_kwargs
        )
    
        return bedrock_client
    
    async def __aenter__(self):  
        logger.info("🚪 Entering AsyncBedrockClient context")  
        # Initialize bedrock runtime
        if not self.bedrock_runtime:
            self.bedrock_runtime = self._get_bedrock_client(runtime=True)
        return self  
  
    async def __aexit__(self, exc_type, exc_val, exc_tb):  
        logger.info("🚪 Exiting AsyncBedrockClient context")  
        if exc_type:  
            logger.error(f"❌ Exception in context: {exc_type.__name__}: {exc_val}")  
              
        self._close_bedrock()
        return False

    def _format_claude_request(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Format request for Claude 3 Haiku model."""
        messages = []
        
        if user_prompt:
            messages.append({
                "role": "user",
                "content": user_prompt
            })
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 40000,
            "temperature": 0.1,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
            
        return body

    def _extract_claude_response(self, response_body: Dict[str, Any]) -> str:
        """Extract text content from Claude response."""
        try:
            content = response_body.get("content", [])
            if content and isinstance(content, list):
                # Claude returns content as list of content blocks
                for block in content:
                    if block.get("type") == "text":
                        return block.get("text", "")
            return ""
        except Exception as e:
            logger.error(f"Error extracting Claude response: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def invoke_bedrock_async_robust(self, system_prompt: str, prompt: str, timeout_override: Optional[int] = None) -> str:
        """
        Async Bedrock call with robust retry logic.
        """
        logger.info("🤖 Starting Bedrock API call with retry logic...")  
        logger.debug(f"Model: {self.model_id}")  
        logger.debug(f"System prompt length: {len(system_prompt) if system_prompt else 0}")  
        logger.debug(f"User prompt length: {len(prompt) if prompt else 0}")  
        
        try:
            if not self.bedrock_runtime:
                self.bedrock_runtime = self._get_bedrock_client(runtime=True)
            
            # Format request for Claude
            request_body = self._format_claude_request(system_prompt, prompt)
            
            # Make async call to Bedrock
            response = await asyncio.to_thread(
                self.bedrock_runtime.invoke_model,
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read().decode("utf-8"))
            result = self._extract_claude_response(response_body)
            
            logger.info(f"✅ Bedrock API call successful. Response length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bedrock API call failed: {e}")
            if "AccessDenied" in str(e) or "UnauthorizedOperation" in str(e):
                raise CriticalBedrockError(f"Access denied to Bedrock model {self.model_id}: {e}")
            raise

    async def invoke_bedrock_async(self, system_prompt: str, prompt: str) -> str:
        """
        Simple async Bedrock call.
        """
        return await self.invoke_bedrock_async_robust(system_prompt, prompt)
    
    def _close_bedrock(self):
        """Close Bedrock client."""
        if hasattr(self, 'bedrock') and self.bedrock:
            self.bedrock.close()
    
    def __del__(self):
        """Destructor."""
        self._close_bedrock()