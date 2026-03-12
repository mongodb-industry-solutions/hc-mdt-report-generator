"""
Metadata Extractor

Handles extraction of metadata from documents.
Separates metadata concerns from processing logic.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Union
from datetime import datetime
from utils.file_type_detector import detect_file_type_from_base64

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Handles metadata extraction from documents"""
    
    @staticmethod
    def extract_from_file(file_path: str, content: str) -> Dict[str, Any]:
        """
        Extract metadata from file path and content
        
        Args:
            file_path: Path to the file
            content: Extracted text content
            
        Returns:
            Metadata dictionary
        """
        try:
            file_info = Path(file_path)
            
            return {
                "title": file_info.stem,
                "filename": file_info.name,
                "file_type": file_info.suffix,
                "file_size": file_info.stat().st_size if file_info.exists() else 0,
                "processed_at": datetime.now().isoformat(),
                "character_count": len(content),
                "word_count": len(content.split()),
                "ocr_service": "bedrock-ocr-latest",
                "source_type": "file_path"
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata from file {file_path}: {e}")
            raise
    
    @staticmethod
    def extract_from_base64(content_dict: Dict[str, Any], content: str) -> Dict[str, Any]:
        """
        Extract metadata from base64 content dictionary
        
        Args:
            content_dict: Dictionary with base64 content info
            content: Extracted text content
            
        Returns:
            Metadata dictionary
        """
        try:
            filename = content_dict.get('filename', 'document')
            
            # Detect file type from base64 content
            base64_content = content_dict.get('base64_content', '')
            file_extension = detect_file_type_from_base64(base64_content)
            
            # Estimate file size from base64 (approximate)
            file_size = len(base64_content) * 3 // 4 if base64_content else 0
            
            return {
                "title": filename.rsplit('.', 1)[0] if '.' in filename else filename,
                "filename": filename,
                "file_type": file_extension,
                "file_size": file_size,
                "processed_at": datetime.now().isoformat(),
                "character_count": len(content),
                "word_count": len(content.split()),
                "ocr_service": "bedrock-ocr-latest",
                "source_type": "base64"
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata from base64 content: {e}")
            raise
    
    @staticmethod
    def extract(source: Union[str, Dict[str, Any]], content: str) -> Dict[str, Any]:
        """
        Extract metadata from source (file path or base64 dict)
        
        Args:
            source: Either a file path (str) or a dict with base64 content
            content: Extracted text content
            
        Returns:
            Metadata dictionary
        """
        if isinstance(source, dict):
            return MetadataExtractor.extract_from_base64(source, content)
        else:
            return MetadataExtractor.extract_from_file(source, content) 