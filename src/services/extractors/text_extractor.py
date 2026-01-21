"""
Text Extractor

Handles extraction of text from plain text files.
Separates text file reading from OCR processing.
"""

import logging
from pathlib import Path
from typing import Optional
import re

logger = logging.getLogger(__name__)


class TextExtractor:
    """Handles text extraction from plain text files"""
    
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text content from plain text files
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Extracted text content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file can't be decoded
        """
        try:
            logger.info(f"Extracting text from plain text file: {file_path}")
            
            # Try UTF-8 first
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    logger.info(f"Successfully extracted {len(content)} characters using UTF-8")
                    
                    return content
                    
            except UnicodeDecodeError:
                # Fallback to latin-1 encoding
                logger.warning(f"UTF-8 decoding failed for {file_path}, trying latin-1")
                with open(file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                    logger.info(f"Successfully extracted {len(content)} characters using latin-1")
                    
                    return content
                    
        except FileNotFoundError:
            logger.error(f"Text file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise
    
    @staticmethod
    def extract_from_base64(base64_content: str) -> str:
        """
        Extract text from base64 encoded content
        
        Args:
            base64_content: Base64 encoded text content
            
        Returns:
            Decoded text content
        """
        import base64
        
        try:
            logger.info("Extracting text from base64 content")
            
            # Decode base64
            decoded_bytes = base64.b64decode(base64_content)
            
            # Try UTF-8 first
            try:
                content = decoded_bytes.decode('utf-8')
                logger.info(f"Successfully decoded {len(content)} characters using UTF-8")
                
                
                return content
                
            except UnicodeDecodeError:
                # Fallback to latin-1 encoding
                logger.warning("UTF-8 decoding failed for base64 content, trying latin-1")
                content = decoded_bytes.decode('latin-1')
                logger.info(f"Successfully decoded {len(content)} characters using latin-1")
                
                
                return content
                
        except Exception as e:
            logger.error(f"Error extracting text from base64 content: {e}")
            raise
    
        """
        Check if the content is a chemotherapy administration XML document
        
        Args:
            content: The file content to check
            
        Returns:
            True if it's a chemotherapy XML document
        """
        # Check for XML declaration and chemotherapy-specific elements
        if not content.strip().startswith('<?xml'):
            return False
        
        # Look for chemotherapy-specific XML elements
        chemotherapy_indicators = [
            'Compte_rendu_administration',
            'Compte_rendu_admin',
            'Protocole',
            'Cycle',
            'Composant_administré',
            'Libellé_composant',
            'Quantité_administrée'
        ]
        
        content_lower = content.lower()
        matches = sum(1 for indicator in chemotherapy_indicators if indicator.lower() in content_lower)
        
        # If we find at least 3 chemotherapy indicators, consider it a chemotherapy XML
        return matches >= 3
        """
        Parse chemotherapy XML and convert to narrative text
        
        Args:
            content: Raw XML content
            
        Returns:
            Narrative text describing chemotherapy treatments
        """
        try:
            # Import here to avoid circular imports
            from services.processors.xml_chemotherapy_parser import XMLChemotherapyParser
            
            parser = XMLChemotherapyParser()
            narrative_text = parser.parse_chemotherapy_xml(content)
            
            logger.info(f"Successfully parsed chemotherapy XML into {len(narrative_text)} characters of narrative text")
            return narrative_text
            
        except Exception as e:
            logger.error(f"Error parsing chemotherapy XML: {e}")
            # Return original content as fallback
            return content 