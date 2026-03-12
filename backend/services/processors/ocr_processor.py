"""
OCR Processor

Handles OCR processing using AWS hybrid approach (Textract + Bedrock).
Migrated from legacy OCR to AWS-native solutions.
"""

import os
import logging
from typing import Optional

# Import the new AWS hybrid implementation
from services.processors.aws_hybrid_ocr_processor import AWSHybridOCRProcessor

logger = logging.getLogger(__name__)


class OCRProcessor(AWSHybridOCRProcessor):
    """
    OCR processor using AWS hybrid approach (Textract + Bedrock)
    
    This processor has been migrated from legacy OCR to use:
    1. AWS Textract for document text extraction (OCR)
    2. AWS Bedrock (Claude) for text cleanup/processing 
    
    Maintains the same interface as the original implementation for backward compatibility.
    """
    
    def __init__(self):
        # Use AWS configuration from environment
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        profile = os.environ.get("AWS_PROFILE")  # Uses default profile if None
        
        super().__init__(region_name=region, profile_name=profile)
        
        # Set file size limit (inherited from Textract limits)
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
        logger.info("OCR processor initialized with AWS")
        logger.info(f"AWS Region: {region}")
        logger.info(f"AWS Profile: {profile or 'default'}")
    
    async def process_file(self, file_path: str) -> str:
        """
        Process a file with AWS hybrid OCR (Textract + Bedrock cleanup)
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Extracted text content
        """
        # Delegate to parent AWS hybrid implementation
        return await super().process_file(file_path)
    
    async def process_base64(self, base64_content: str, file_extension: str) -> str:
        """
        Process base64 content with AWS hybrid OCR
        
        Args:
            base64_content: Base64 encoded file content
            file_extension: File extension (e.g., '.pdf', '.png')
            
        Returns:
            Extracted text content
        """
        # Delegate to parent AWS hybrid implementation
        return await super().process_base64(base64_content, file_extension) 