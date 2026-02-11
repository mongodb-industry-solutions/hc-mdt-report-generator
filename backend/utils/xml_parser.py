# utils/xml_parser.py  
"""XML tag extraction utilities."""  
  
import re  
import logging  
from typing import Optional  
  
logger = logging.getLogger(__name__)  
  
class XMLTagExtractor:  
    """Utility class for extracting content from XML tags."""  
      
    @staticmethod  
    def extract_from_xml_tags(text: str, tag_name: str) -> Optional[str]:  
        """  
        Extract text between XML tags using optimized regex.  
          
        Args:  
            text: The input text containing XML tags  
            tag_name: The tag name (without < >)  
              
        Returns:  
            Text between the tags, or None if not found  
        """  
        if not text or not tag_name:  
            return None  
          
        try:  
            # Use regex for more robust extraction  
            pattern = rf'<{re.escape(tag_name)}>(.*?)</{re.escape(tag_name)}>'  
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)  
              
            if match:  
                return match.group(1)  
              
            return None  
              
        except Exception as e:  
            logger.error(f"XML extraction failed for tag '{tag_name}': {e}")  
            return None  
      
    @staticmethod  
    def extract_multiple_tags(text: str, tag_name: str) -> list[str]:  
        """Extract multiple occurrences of the same tag."""  
        if not text or not tag_name:  
            return []  
          
        try:  
            pattern = rf'<{re.escape(tag_name)}>(.*?)</{re.escape(tag_name)}>'  
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)  
            return [match.strip() for match in matches]  
              
        except Exception as e:  
            logger.error(f"Multiple XML extraction failed for tag '{tag_name}': {e}")  
            return []  
