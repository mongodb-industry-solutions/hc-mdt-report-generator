"""  
Document Data Extraction Service  

Extracts data from documents:
- For JSON files: Parses and preserves the full JSON structure (lCrs, pat, etc.)
- For other files: Extracts plain text content
"""  

import json
import re
import logging  
from typing import Dict, Any  
from datetime import datetime  

logger = logging.getLogger(__name__)  


class DocumentDataExtractionService:  
    """  
    Service for extracting data from documents.
    
    For JSON files: Parses and preserves the full JSON structure (lCrs, pat, etc.)
    For other files: Extracts plain text content
    """  
      
    def __init__(self):  
        self._initialized = True
        logger.info("Document Data Extraction Service initialized")  
      
    async def initialize(self) -> None:  
        """No initialization needed"""  
        pass  
      
    async def extract_structured_data(self, document_text: str, category: str = "text",  
                                    source_file: str = "unknown") -> Dict[str, Any]:  
        """  
        Extract data from a document.
        
        For JSON files: Parses and returns the full JSON structure (lCrs, pat preserved)
        For other files: Returns cleaned text content
          
        Args:  
            document_text: The text content from the document  
            category: Document category (used for logging)
            source_file: Name of the source file for tracking  
              
        Returns:  
            Dictionary containing extracted data and metadata  
        """  
        try:  
            logger.info(f"Extracting data from {source_file}")  
            
            # Check if this is a JSON file
            is_json_file = source_file.lower().endswith('.json')
            
            if is_json_file:
                # Parse JSON and preserve full structure (lCrs, pat, etc.)
                return self._extract_from_json(document_text, source_file)
            else:
                # Regular text extraction
                return self._extract_from_text(document_text, source_file)
                
        except Exception as e:  
            logger.error(f"Extraction failed for {source_file}: {e}")  
            return self._create_error_result(source_file, str(e), document_text)  
    
    def _extract_from_json(self, document_text: str, source_file: str) -> Dict[str, Any]:
        """
        Parse JSON and preserve full structure including lCrs and pat.
        
        This is critical for source filtering to work - the lCrs array must be
        preserved so that each lCr can become its own document for filtering.
        """
        try:
            # Parse the JSON content
            parsed_json = json.loads(document_text)
            
            # Log what we found
            lcrs_count = 0
            has_pat = False
            if isinstance(parsed_json, dict):
                lcrs = parsed_json.get('lCrs', [])
                lcrs_count = len(lcrs) if isinstance(lcrs, list) else 0
                has_pat = 'pat' in parsed_json
            
            logger.info(f"✅ JSON parsed for {source_file}: {lcrs_count} lCrs found, pat={has_pat}")
            
            # Store the ENTIRE parsed JSON in extracted_data
            # This preserves lCrs, pat, and all other fields for downstream processing
            result = {
                "extracted_data": parsed_json,  # Full JSON structure preserved!
                "metadata": {
                    "source_file": source_file,
                    "document_category": "json_document",
                    "document_type": "json_document",
                    "extraction_completed_at": datetime.now().isoformat(),
                    "lcrs_count": lcrs_count,
                    "has_pat": has_pat,
                    "extraction_status": "success",
                    "processing_method": "json_parsing"
                }
            }
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON parse failed for {source_file}, falling back to text extraction: {e}")
            return self._extract_from_text(document_text, source_file)
    
    def _extract_from_text(self, document_text: str, source_file: str) -> Dict[str, Any]:
        """Extract plain text content for non-JSON files."""
        cleaned_text = self._clean_text(document_text)
        
        result = {
            "extracted_data": {
                "text": cleaned_text,
                "content": cleaned_text,
                "document_type": "text_document",
                "extraction_method": "text_only"
            },
            "metadata": {
                "source_file": source_file,
                "document_category": "text_document",
                "document_type": "text_document",
                "extraction_completed_at": datetime.now().isoformat(),
                "text_length": len(cleaned_text),
                "extraction_status": "success",
                "processing_method": "simple_text_extraction"
            }
        }
        
        logger.info(f"Text extraction completed for {source_file} - {len(cleaned_text)} characters")
        return result
      
    def _clean_text(self, text: str) -> str:  
        """Clean and normalize text content."""  
        if not text:  
            return ""  
          
        # Basic text cleaning  
        cleaned = text.strip()  
          
        # Remove excessive whitespace  
        cleaned = re.sub(r'\s+', ' ', cleaned)  
          
        # Remove control characters but keep newlines and tabs  
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\t')  
          
        return cleaned  
      
    def _create_error_result(self, source_file: str, error_message: str,   
                           document_text: str) -> Dict[str, Any]:  
        """Create error result structure"""  
        return {  
            "extracted_data": {  
                "text": document_text or "",
                "content": document_text or "",  
                "error": error_message,  
                "extraction_failed": True,  
                "document_type": "text_document"  
            },  
            "metadata": {  
                "source_file": source_file,  
                "document_category": "text_document",  
                "document_type": "text_document",   
                "extraction_completed_at": datetime.now().isoformat(),  
                "text_length": len(document_text) if document_text else 0,  
                "error": error_message,  
                "extraction_status": "failed",  
                "processing_method": "simple_text_extraction"  
            }  
        }  
      
    def get_supported_categories(self) -> list:  
        """Return list of supported document categories"""  
        return ["text_document", "json_document"]  
      
    def is_category_supported(self, category: str) -> bool:  
        """All categories are supported"""  
        return True  


# For backward compatibility, keep the old class name as an alias  
class SimpleDocumentDataExtractionService(DocumentDataExtractionService):  
    """Alias for backward compatibility"""  
    pass  
