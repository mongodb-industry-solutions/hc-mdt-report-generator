"""
File Format Handler

Handles file format detection, validation, and MIME type mapping.
Separates file format concerns from processing logic.
"""

from pathlib import Path
from typing import Set, Dict, Optional


class FileFormatHandler:
    """Handles file format detection and validation"""
    
    # Supported formats
    SUPPORTED_FORMATS: Set[str] = {
        '.pdf', '.pptx', '.docx', '.txt', '.md', '.csv', '.xml', '.json',
        '.png', '.jpg', '.jpeg', '.avif'
    }
    
    # Plain text formats (no OCR needed)
    PLAIN_TEXT_FORMATS: Set[str] = {
        '.txt', '.md', '.csv', '.xml', '.json'
    }
    
    # OCR-supported formats
    OCR_SUPPORTED_FORMATS: Set[str] = {
        '.png', '.jpeg', '.jpg', '.avif', '.pdf', '.pptx', '.docx'
    }
    
    # Image formats
    IMAGE_FORMATS: Set[str] = {
        '.png', '.jpeg', '.jpg', '.avif'
    }
    
    # Document formats
    DOCUMENT_FORMATS: Set[str] = {
        '.pdf', '.pptx', '.docx'
    }
    
    # MIME type mappings
    IMAGE_MIME_TYPES: Dict[str, str] = {
        '.png': 'image/png',
        '.jpeg': 'image/jpeg',
        '.jpg': 'image/jpeg',
        '.avif': 'image/avif'
    }
    
    DOCUMENT_MIME_TYPES: Dict[str, str] = {
        '.pdf': 'application/pdf',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    @classmethod
    def get_file_extension(cls, file_path: str) -> str:
        """Get normalized file extension"""
        return Path(file_path).suffix.lower()
    
    @classmethod
    def is_supported_format(cls, file_path: str) -> bool:
        """Check if file format is supported"""
        return cls.get_file_extension(file_path) in cls.SUPPORTED_FORMATS
    
    @classmethod
    def is_plain_text(cls, file_path: str) -> bool:
        """Check if file is plain text (no OCR needed)"""
        return cls.get_file_extension(file_path) in cls.PLAIN_TEXT_FORMATS
    
    @classmethod
    def is_ocr_supported(cls, file_path: str) -> bool:
        """Check if file format is supported by OCR"""
        return cls.get_file_extension(file_path) in cls.OCR_SUPPORTED_FORMATS
    
    @classmethod
    def is_image_format(cls, file_path: str) -> bool:
        """Check if file is an image format"""
        return cls.get_file_extension(file_path) in cls.IMAGE_FORMATS
    
    @classmethod
    def is_document_format(cls, file_path: str) -> bool:
        """Check if file is a document format"""
        return cls.get_file_extension(file_path) in cls.DOCUMENT_FORMATS
    
    @classmethod
    def get_mime_type(cls, file_path: str) -> Optional[str]:
        """Get MIME type for file"""
        extension = cls.get_file_extension(file_path)
        
        if extension in cls.IMAGE_MIME_TYPES:
            return cls.IMAGE_MIME_TYPES[extension]
        elif extension in cls.DOCUMENT_MIME_TYPES:
            return cls.DOCUMENT_MIME_TYPES[extension]
        
        return None
    
    @classmethod
    def get_document_type(cls, file_path: str) -> str:
        """Get document type for Mistral API"""
        if cls.is_image_format(file_path):
            return "image_url"
        elif cls.is_document_format(file_path):
            return "document_url"
        else:
            raise ValueError(f"Unsupported file format: {cls.get_file_extension(file_path)}")
    
    @classmethod
    def validate_file_exists(cls, file_path: str) -> None:
        """Validate that file exists"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
    
    @classmethod
    def validate_format(cls, file_path: str) -> None:
        """Validate file format is supported"""
        if not cls.is_supported_format(file_path):
            raise ValueError(f"Unsupported file format: {cls.get_file_extension(file_path)}") 