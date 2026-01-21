"""
OCR Processor

Handles the actual OCR processing using Mistral AI.
Separates OCR logic from service orchestration.
"""

import os
import base64
import logging
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Optional

from services.base.mistral_client import BaseMistralClient
from services.utils.file_format_handler import FileFormatHandler

logger = logging.getLogger(__name__)


class OCRProcessor(BaseMistralClient):
    """Handles OCR processing using Mistral AI"""
    
    def __init__(self):
        super().__init__("OCR")
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    async def process_file(self, file_path: str) -> str:
        """
        Process a file with OCR
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Extracted text content
        """
        self.ensure_initialized()
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            logger.warning(f"File size ({file_size} bytes) exceeds {self.max_file_size} bytes, using upload method")
            return await self._process_with_upload(file_path)
        
        # Process with base64 encoding
        return await self._process_with_base64(file_path)
    
    async def process_base64(self, base64_content: str, file_extension: str) -> str:
        """
        Process base64 content with OCR
        
        Args:
            base64_content: Base64 encoded file content
            file_extension: File extension (e.g., '.pdf', '.png')
            
        Returns:
            Extracted text content
        """
        self.ensure_initialized()
        
        # Check approximate size
        approx_size = len(base64_content) * 3 / 4
        if approx_size > self.max_file_size:
            logger.warning(f"Content size (~{approx_size} bytes) may exceed {self.max_file_size} bytes limit")
        
        # Create data URL
        mime_type = FileFormatHandler.get_mime_type(f"file{file_extension}")
        document_type = FileFormatHandler.get_document_type(f"file{file_extension}")
        data_url = f"data:{mime_type};base64,{base64_content}"
        
        # Process OCR
        logger.info(f"Processing OCR on base64 content with extension: {file_extension}")
        return await self._call_mistral_ocr(document_type, data_url)
    
    async def _process_with_base64(self, file_path: str) -> str:
        """Process file using base64 encoding"""
        # Encode file to base64
        base64_content = self._encode_file_to_base64(file_path)
        
        # Get file extension and process
        file_extension = FileFormatHandler.get_file_extension(file_path)
        return await self.process_base64(base64_content, file_extension)
    
    async def _process_with_upload(self, file_path: str) -> str:
        """Process file using upload method for large files"""
        try:
            def _sync_upload_and_process():
                # Upload file
                with open(file_path, 'rb') as file:
                    uploaded_file = self.client.files.upload(
                        file={
                            "file_name": Path(file_path).name,
                            "content": file,
                        },
                        purpose="ocr"
                    )
                
                # Get signed URL
                signed_url = self.client.files.get_signed_url(file_id=uploaded_file.id)
                
                # Process OCR
                ocr_response = self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": signed_url.url,
                    },
                    include_image_base64=True
                )
                
                # Clean up uploaded file
                try:
                    self.client.files.delete(file_id=uploaded_file.id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up uploaded file: {cleanup_error}")
                
                return ocr_response
            
            # Run in thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                ocr_response = await asyncio.get_event_loop().run_in_executor(
                    executor, _sync_upload_and_process
                )
            
            # Extract text
            return self._extract_text_from_response(ocr_response)
            
        except Exception as e:
            logger.error(f"OCR with upload failed for {file_path}: {e}")
            raise
    
    async def _call_mistral_ocr(self, document_type: str, data_url: str) -> str:
        """Call Mistral OCR API"""
        try:
            # Create document object
            document = {
                "type": document_type,
                f"{document_type.split('_')[0]}_url": data_url
            }
            
            # Call Mistral OCR API (synchronous, so we wrap it)
            def _sync_ocr_call():
                return self.client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True
                )
            
            # Run in thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                ocr_response = await asyncio.get_event_loop().run_in_executor(
                    executor, _sync_ocr_call
                )
            
            # Extract text from response
            return self._extract_text_from_response(ocr_response)
            
        except Exception as e:
            logger.error(f"Mistral OCR API call failed: {e}")
            raise
    
    def _extract_text_from_response(self, ocr_response) -> str:
        """Extract clean text from OCR response"""
        extracted_text = ""
        
        # Extract from pages (primary method)
        if hasattr(ocr_response, 'pages') and ocr_response.pages:
            page_texts = []
            for page in ocr_response.pages:
                if hasattr(page, 'markdown') and page.markdown:
                    page_texts.append(page.markdown)
            extracted_text = '\n\n'.join(page_texts)
        
        # Fallback extraction methods
        elif hasattr(ocr_response, 'text') and ocr_response.text:
            extracted_text = ocr_response.text
        elif hasattr(ocr_response, 'content') and ocr_response.content:
            extracted_text = ocr_response.content
        else:
            # Log unexpected response structure
            logger.warning(f"Unexpected OCR response structure: {type(ocr_response)}")
            extracted_text = str(ocr_response)
        
        logger.info(f"OCR extracted {len(extracted_text)} characters")
        return extracted_text
    
    def _encode_file_to_base64(self, file_path: str) -> str:
        """Encode file to base64 string"""
        try:
            with open(file_path, 'rb') as file:
                return base64.b64encode(file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding file {file_path}: {e}")
            raise 