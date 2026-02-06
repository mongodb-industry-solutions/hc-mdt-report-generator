"""
Document OCR Service

Handles Optical Character Recognition (OCR) for various document formats
using AWS hybrid approach (Textract + Bedrock).

This service orchestrates text extraction from various document formats,
delegating specific processing to specialized components.
"""

import logging
from typing import Union, Dict, Any, Optional

from services.utils.file_format_handler import FileFormatHandler
from services.extractors.text_extractor import TextExtractor
from services.extractors.metadata_extractor import MetadataExtractor
from services.processors.ocr_processor import OCRProcessor
from utils.file_type_detector import detect_file_type_from_base64

logger = logging.getLogger(__name__)


class DocumentOCRService:
    """
    Service for performing OCR on documents using AWS hybrid approach (Textract + Bedrock).
    
    This service orchestrates the text extraction process by:
    1. Validating file formats and existence
    2. Routing to appropriate extractors (text vs OCR)
    3. Extracting metadata
    4. Providing a unified interface for all document types
    """
    
    def __init__(self):
        self.ocr_processor = None  # Lazy initialization
        self._initialized = False
        self._ocr_initialized = False
    
    async def initialize(self) -> None:
        """Initialize service (OCR processor initialized lazily when needed)"""
        if not self._initialized:
            self._initialized = True
            logger.info("Document OCR Service initialized successfully")
    
    async def _ensure_ocr_initialized(self) -> None:
        """Lazy initialization of OCR processor when actually needed"""
        if not self._ocr_initialized:
            if self.ocr_processor is None:
                self.ocr_processor = OCRProcessor()
            await self.ocr_processor.initialize()
            self._ocr_initialized = True
            logger.info("OCR processor initialized successfully")
    
    async def extract_text(self, source: Union[str, Dict[str, Any]], file_extension: Optional[str] = None) -> str:
        """
        Extract text from document. Handles file paths, base64 content, and plain text.
        
        Args:
            source: Either a file path (str) or a dict with base64 content
                   Dict format: {"base64_content": str}
            file_extension: Optional file extension (e.g., ".pdf", ".txt"). If not provided,
                          will be detected automatically from content.
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If format is not supported or input is invalid
            FileNotFoundError: If file doesn't exist (for file path input)
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        # Determine source type and validate
        if isinstance(source, dict):
            # Base64 content
            if 'base64_content' not in source:
                raise ValueError("Missing 'base64_content' in input dictionary")
            
            base64_content = source['base64_content']
            source_type = "base64"
            source_content = base64_content
            
            # Use provided file extension or detect from content
            if file_extension is None:
                file_extension = detect_file_type_from_base64(base64_content)
                logger.info(f"Detected file type from base64 content: {file_extension}")
            else:
                logger.info(f"Using provided file type: {file_extension}")
            
        else:
            # File path
            file_path = source
            FileFormatHandler.validate_file_exists(file_path)
            FileFormatHandler.validate_format(file_path)
            
            source_type = "file"
            source_content = file_path
            
            # Use provided file extension or get from path
            if file_extension is None:
                file_extension = FileFormatHandler.get_file_extension(file_path)
                logger.info(f"Detected file type from path: {file_extension}")
            else:
                logger.info(f"Using provided file type: {file_extension}")
            
            logger.info(f"Extracting text from file: {file_path}")
        
        # Route to appropriate extractor
        return await self._extract(
            source_type=source_type,
            source=source_content,
            file_extension=file_extension
        )
    
    def extract_metadata(self, source: Union[str, Dict[str, Any]], content: str) -> Dict[str, Any]:
        """
        Extract document metadata
        
        Args:
            source: Either a file path (str) or a dict with base64 content
            content: The extracted text content
            
        Returns:
            Metadata dictionary
        """
        return MetadataExtractor.extract(source, content)
    

    
    async def _extract(self, source_type: str, source: Union[str, bytes], file_extension: str) -> str:
        """
        Route to appropriate extractor based on file type
        
        Args:
            source_type: Either "file" or "base64"
            source: The source content (file path or base64 string)
            file_extension: The detected file extension
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If format is not supported
        """
        # Route to appropriate extractor based on file type
        if file_extension in FileFormatHandler.PLAIN_TEXT_FORMATS:
            logger.info(f"Routing to TextExtractor for format: {file_extension}")
            if source_type == "file":
                return TextExtractor.extract_text(source)
            else:  # base64
                return TextExtractor.extract_from_base64(source)
        
        if file_extension in FileFormatHandler.OCR_SUPPORTED_FORMATS:
            logger.info(f"Routing to OCRProcessor for format: {file_extension}")
            # Only initialize OCR when actually needed
            await self._ensure_ocr_initialized()
            if source_type == "file":
                return await self.ocr_processor.process_file(source)
            else:  # base64
                return await self.ocr_processor.process_base64(source, file_extension)
        
        raise ValueError(f"Unsupported file format for extraction: {file_extension}")