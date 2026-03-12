"""
Text Normalizer

Handles text normalization using LLM providers.
Separates normalization logic from service orchestration.
"""

import logging
from typing import Dict, Any, Optional

from services.base.llm import a_generate
from services.prompts.text_normalization_prompts import SYSTEM_PROMPT, create_normalization_prompt

logger = logging.getLogger(__name__)


class TextNormalizer:
    """Handles text normalization using configurable LLM providers"""
    
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

    async def initialize(self) -> None:
        """No-op initializer retained for startup compatibility."""
        logger.info("TextNormalizer initialized (no-op)")
    
    async def normalize(self, raw_text: str, file_type: str = "unknown") -> Dict[str, Any]:
        """
        Normalize raw text data using configured LLM provider.
        
        Args:
            raw_text: The raw text to normalize (from OCR or plain text)
            file_type: Type of the original file (pdf, txt, csv, xml, json, etc.)
            
        Returns:
            Dictionary containing normalized text and metadata
        """
        logger.info(f"Starting text normalization for {file_type} file ({len(raw_text)} characters)")
        
        # Build normalization prompt based on file type
        prompt = self._build_normalization_prompt(raw_text, file_type)
        
        # Call LLM for normalization
        logger.info("Calling LLM for text normalization...")
        normalized_response = await self._invoke_llm(prompt)
        
        # Parse the normalized response
        normalized_data = self._parse_normalization_response(normalized_response)
        
        logger.info(f"Text normalization completed successfully")
        return normalized_data
    
    def _build_normalization_prompt(self, raw_text: str, file_type: str) -> str:
        """Build the normalization prompt based on file type"""
        return create_normalization_prompt(raw_text, file_type)
    
    async def _invoke_llm(self, prompt: str) -> str:
        """Call unified LLM for text normalization"""
        try:
            return await a_generate(
                prompt=prompt,
                system=self.system_prompt,
                max_tokens=4000,
                temperature=0.1,
                provider="gpt_open",
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_normalization_response(self, response: str) -> Dict[str, Any]:
        """Parse the normalization response from LLM"""
        try:
            # Debug: Log the actual response
            logger.debug(f"Raw LLM response: {response[:500]}...")
            
            # Extract normalized text
            normalized_text = self._extract_from_xml_tags(response, "NORMALIZED_TEXT")
            if not normalized_text:
                logger.warning("No normalized text found in response")
                logger.debug(f"Full response was: {response}")
                # Fallback: if no XML tags found, use the entire response as normalized text
                if response.strip():
                    logger.info("Using entire response as normalized text (fallback)")
                    return {
                        "normalized_text": response.strip(),
                        "structured_data": None,
                        "normalization_notes": "Used fallback parsing - no XML tags found",
                        "normalization_status": "success"
                    }
                return {"normalized_text": "", "normalization_status": "failed"}
            
            # Extract structured data if present
            structured_data = self._extract_from_xml_tags(response, "STRUCTURED_DATA")
            
            # Extract normalization notes
            normalization_notes = self._extract_from_xml_tags(response, "NORMALIZATION_NOTES")
            
            return {
                "normalized_text": normalized_text.strip(),
                "structured_data": structured_data.strip() if structured_data else None,
                "normalization_notes": normalization_notes.strip() if normalization_notes else None,
                "normalization_status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse normalization response: {e}")
            return {
                "normalized_text": "",
                "normalization_status": "failed",
                "error": f"Parsing error: {str(e)}"
            }
    
    def _extract_from_xml_tags(self, text: str, tag_name: str) -> Optional[str]:
        """Extract text between XML tags"""
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"
        
        start_index = text.find(start_tag)
        if start_index == -1:
            return None
        
        start_index += len(start_tag)
        end_index = text.find(end_tag, start_index)
        
        if end_index == -1:
            return None
        
        return text[start_index:end_index] 