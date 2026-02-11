"""
AWS Textract Client

Handles document OCR using AWS Textract service for text extraction
from various document formats (PDF, images, etc.).
"""

import logging
import base64
import asyncio
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class AsyncTextractClient:
    """
    Async wrapper for AWS Textract OCR functionality
    
    Provides text extraction from documents using AWS Textract service.
    Supports both file paths and base64 content with various document formats.
    """
    
    def __init__(self, region_name: str = "us-east-1", profile_name: Optional[str] = None):
        """
        Initialize AWS Textract client
        
        Args:
            region_name: AWS region for Textract service
            profile_name: AWS profile name (optional, uses default if None)
        """
        self.region_name = region_name
        self.profile_name = profile_name
        self._client = None
        self.max_document_size = 10 * 1024 * 1024  # 10MB limit for sync operations
        self.max_text_length = 500000  # Limit for manageable text processing
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        logger.info("🔗 AsyncTextractClient context entered")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            # Textract client doesn't need explicit cleanup
            logger.info("🚪 AsyncTextractClient context exited")
    
    async def _ensure_client(self):
        """Ensure Textract client is initialized"""
        if self._client is None:
            try:
                if self.profile_name:
                    session = boto3.Session(profile_name=self.profile_name)
                    self._client = session.client('textract', region_name=self.region_name)
                else:
                    self._client = boto3.client('textract', region_name=self.region_name)
                
                logger.info(f"✅ AWS Textract client initialized (region: {self.region_name})")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AWS Textract client: {e}")
                raise
    
    async def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from a document file using AWS Textract
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported or too large
            ClientError: If AWS Textract operation fails
        """
        try:
            # Read file content
            with open(file_path, 'rb') as file:
                document_bytes = file.read()
            
            # Check file size
            if len(document_bytes) > self.max_document_size:
                raise ValueError(f"File too large: {len(document_bytes)} bytes (max: {self.max_document_size})")
            
            return await self.extract_text_from_bytes(document_bytes)
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to extract text from file {file_path}: {e}")
            raise
    
    async def extract_text_from_base64(self, base64_content: str) -> str:
        """
        Extract text from base64-encoded document content
        
        Args:
            base64_content: Base64 encoded document content
            
        Returns:
            Extracted text content as string
            
        Raises:
            ValueError: If content invalid or too large
            ClientError: If AWS Textract operation fails
        """
        try:
            # Decode base64 content
            document_bytes = base64.b64decode(base64_content)
            
            # Check size
            if len(document_bytes) > self.max_document_size:
                raise ValueError(f"Document too large: {len(document_bytes)} bytes (max: {self.max_document_size})")
            
            return await self.extract_text_from_bytes(document_bytes)
            
        except Exception as e:
            logger.error(f"Failed to extract text from base64 content: {e}")
            raise
    
    async def extract_text_from_bytes(self, document_bytes: bytes) -> str:
        """
        Extract text from document bytes using AWS Textract
        
        Args:
            document_bytes: Raw document binary content
            
        Returns:
            Extracted text content as string
            
        Raises:
            ClientError: If AWS Textract operation fails
        """
        await self._ensure_client()
        
        try:
            # Use detect_document_text for general text extraction
            # This is more appropriate for general OCR than analyze_document
            def _sync_textract_call():
                return self._client.detect_document_text(
                    Document={'Bytes': document_bytes}
                )
            
            # Run Textract call in thread pool to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                None, _sync_textract_call
            )
            
            # Extract text from Textract response
            extracted_text = self._parse_textract_response(response)
            
            # Limit text length for processing
            if len(extracted_text) > self.max_text_length:
                logger.warning(f"Text truncated from {len(extracted_text)} to {self.max_text_length} characters")
                extracted_text = extracted_text[:self.max_text_length]
            
            logger.info(f"✅ Textract extracted {len(extracted_text)} characters")
            return extracted_text
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"❌ AWS Textract error [{error_code}]: {error_message}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error in Textract extraction: {e}")
            raise
    
    def _parse_textract_response(self, response: Dict[str, Any]) -> str:
        """
        Parse AWS Textract response and extract clean text
        
        Args:
            response: Raw Textract response from detect_document_text
            
        Returns:
            Clean text extracted from the response
        """
        try:
            blocks = response.get('Blocks', [])
            lines = []
            
            # Extract LINE blocks which represent text lines
            for block in blocks:
                if block.get('BlockType') == 'LINE':
                    text = block.get('Text', '').strip()
                    if text:
                        lines.append(text)
            
            # Join lines with newlines to preserve document structure
            extracted_text = '\n'.join(lines)
            
            if not extracted_text.strip():
                logger.warning("No text found in Textract response")
                return ""
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Failed to parse Textract response: {e}")
            # Return raw text if parsing fails
            return str(response.get('Blocks', []))
    
    async def get_document_metadata(self, document_bytes: bytes) -> Dict[str, Any]:
        """
        Get document metadata from AWS Textract analysis
        
        Args:
            document_bytes: Raw document binary content
            
        Returns:
            Dictionary containing document metadata
        """
        await self._ensure_client()
        
        try:
            def _sync_analyze_call():
                return self._client.analyze_document(
                    Document={'Bytes': document_bytes},
                    FeatureTypes=['TABLES', 'FORMS']  # Extract structural information
                )
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, _sync_analyze_call
            )
            
            # Count different types of content
            blocks = response.get('Blocks', [])
            metadata = {
                'total_blocks': len(blocks),
                'lines_count': len([b for b in blocks if b.get('BlockType') == 'LINE']),
                'words_count': len([b for b in blocks if b.get('BlockType') == 'WORD']),
                'tables_count': len([b for b in blocks if b.get('BlockType') == 'TABLE']),
                'forms_count': len([b for b in blocks if b.get('BlockType') == 'KEY_VALUE_SET']),
                'textract_version': response.get('DocumentMetadata', {}).get('TextractVersion', 'unknown')
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to get document metadata: {e}")
            return {'error': str(e)}


async def test_textract_client():
    """Simple test function for AWS Textract client"""
    print("🧪 Testing AWS Textract client...")
    
    # Test with a simple text document (base64 encoded)
    test_content = "This is a test document for OCR processing."
    
    # Convert to simple image-like format for testing
    # In real usage, this would be actual PDF/image content
    test_base64 = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
    
    try:
        async with AsyncTextractClient() as textract_client:
            # This would fail with actual text, but shows the interface
            print("✅ AWS Textract client initialized successfully")
            print("📋 Client ready for document processing")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_textract_client())