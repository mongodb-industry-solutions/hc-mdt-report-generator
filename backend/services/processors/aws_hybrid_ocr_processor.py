"""
AWS Hybrid OCR Processor

Handles OCR processing using AWS Textract for text extraction
and AWS Bedrock for text processing/cleanup when needed.

Replaces legacy OCR implementations with AWS-native solutions.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional

from infrastructure.aws.textract_client import AsyncTextractClient
from infrastructure.llm.bedrock_client import AsyncBedrockClient
from services.utils.file_format_handler import FileFormatHandler

logger = logging.getLogger(__name__)


class AWSHybridOCRProcessor:
    """
    AWS Hybrid OCR processor using Textract + Bedrock
    
    This processor:
    1. Uses AWS Textract for document text extraction (OCR)
    2. Uses AWS Bedrock (Claude) for text cleanup/processing if needed
    3. Maintains the same interface as the original OCR processor
    """
    
    def __init__(self, region_name: str = "us-east-1", profile_name: Optional[str] = None):
        self.region_name = region_name
        self.profile_name = profile_name
        self.max_file_size = 10 * 1024 * 1024  # 10MB (Textract limit)
        self._initialized = False
        
        # Text processing options
        self.enable_text_cleanup = True  # Use Bedrock for text cleanup
        self.cleanup_prompt = """Clean and format this OCR-extracted text from a medical document.

Instructions:
1. Fix obvious OCR errors (character recognition mistakes)
2. Preserve all medical terminology and numbers exactly
3. Maintain document structure and line breaks
4. Remove excessive whitespace but keep meaningful formatting
5. Do NOT summarize or change content - only clean formatting

Return the cleaned text directly, no explanations."""
    
    async def initialize(self) -> None:
        """Initialize the AWS hybrid OCR processor"""
        if not self._initialized:
            self._initialized = True
            logger.info("🔧 AWS Hybrid OCR processor initialized")
    
    def ensure_initialized(self) -> None:
        """Ensure processor is initialized"""
        if not self._initialized:
            raise RuntimeError("AWS Hybrid OCR processor not initialized. Call initialize() first.")
    
    async def process_file(self, file_path: str) -> str:
        """
        Process a file with AWS hybrid OCR (Textract + optional Bedrock cleanup)
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Extracted and cleaned text content
        """
        self.ensure_initialized()
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds AWS Textract limit ({self.max_file_size} bytes). "
                "Consider splitting the document or using a different processing method."
            )
        
        logger.info(f"🔍 Processing file with AWS Textract: {file_path}")
        
        # Step 1: Extract text using AWS Textract
        async with AsyncTextractClient(self.region_name, self.profile_name) as textract_client:
            raw_text = await textract_client.extract_text_from_file(file_path)
        
        logger.info(f"📄 Textract extracted {len(raw_text)} characters from {Path(file_path).name}")
        
        # Step 2: Optional text cleanup using Bedrock
        if self.enable_text_cleanup and raw_text.strip():
            cleaned_text = await self._cleanup_text_with_bedrock(raw_text)
            logger.info(f"🧹 Text cleaned with Bedrock Claude (final length: {len(cleaned_text)})")
            return cleaned_text
        
        return raw_text
    
    async def process_base64(self, base64_content: str, file_extension: str) -> str:
        """
        Process base64 content with AWS hybrid OCR
        
        Args:
            base64_content: Base64 encoded file content
            file_extension: File extension (e.g., '.pdf', '.png')
            
        Returns:
            Extracted and cleaned text content
        """
        self.ensure_initialized()
        
        # Check approximate size
        approx_size = len(base64_content) * 3 / 4
        if approx_size > self.max_file_size:
            logger.warning(f"Content size (~{approx_size} bytes) may exceed Textract limit")
        
        logger.info(f"🔍 Processing base64 content with AWS Textract (type: {file_extension})")
        
        # Step 1: Extract text using AWS Textract
        async with AsyncTextractClient(self.region_name, self.profile_name) as textract_client:
            raw_text = await textract_client.extract_text_from_base64(base64_content)
        
        logger.info(f"📄 Textract extracted {len(raw_text)} characters from base64 content")
        
        # Step 2: Optional text cleanup using Bedrock
        if self.enable_text_cleanup and raw_text.strip():
            cleaned_text = await self._cleanup_text_with_bedrock(raw_text)
            logger.info(f"🧹 Text cleaned with Bedrock Claude (final length: {len(cleaned_text)})")
            return cleaned_text
        
        return raw_text
    
    async def _cleanup_text_with_bedrock(self, raw_text: str) -> str:
        """
        Clean and format OCR text using AWS Bedrock (Claude)
        
        Args:
            raw_text: Raw text extracted by AWS Textract
            
        Returns:
            Cleaned and formatted text
        """
        try:
            # Check if text needs cleanup (basic heuristics)
            if len(raw_text.strip()) < 50:
                logger.info("Text too short for cleanup, returning as-is")
                return raw_text
            
            # Use Bedrock for text cleanup
            async with AsyncBedrockClient(region_name=self.region_name) as bedrock_client:
                system_prompt = "You are a medical document text processing specialist. Clean OCR errors while preserving all medical content exactly."
                
                user_prompt = f"{self.cleanup_prompt}\n\nOCR Text:\n{raw_text}"
                
                cleaned_text = await bedrock_client.invoke_bedrock_async_robust(
                    system_prompt=system_prompt,
                    prompt=user_prompt,
                    timeout_override=60  # Shorter timeout for cleanup
                )
                
                # Validate cleaned text isn't empty
                if not cleaned_text.strip():
                    logger.warning("Bedrock cleanup returned empty text, using original")
                    return raw_text
                
                return cleaned_text
                
        except Exception as e:
            logger.warning(f"Text cleanup with Bedrock failed: {e}")
            logger.info("Returning original Textract text")
            return raw_text
    
    def set_text_cleanup(self, enabled: bool) -> None:
        """Enable or disable Bedrock text cleanup"""
        self.enable_text_cleanup = enabled
        logger.info(f"Text cleanup with Bedrock: {'enabled' if enabled else 'disabled'}")
    
    def set_cleanup_prompt(self, prompt: str) -> None:
        """Set custom cleanup prompt for Bedrock"""
        self.cleanup_prompt = prompt
        logger.info("Custom cleanup prompt set")


# Backward compatibility - create an alias to maintain existing interface
class OCRProcessor(AWSHybridOCRProcessor):
    """
    Backward compatible OCR processor using AWS hybrid approach
    
    This maintains the same interface as the original OCR processor
    but uses AWS Textract + Bedrock instead of legacy implementations.
    """
    
    def __init__(self):
        # Use default region and profile from environment or AWS config
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        profile = os.environ.get("AWS_PROFILE")  # None if not set
        
        super().__init__(region_name=region, profile_name=profile)
        logger.info("🔄 OCR processor initialized with AWS hybrid approach (Textract + Bedrock)")