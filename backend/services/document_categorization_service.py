"""
Document Categorization Service

Handles categorization of medical documents using available LLM providers.
This service performs the first LLM shot to categorize documents into predefined medical categories.

This service processes extracted text from documents to determine their medical document type
for better downstream processing and routing.
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

import os
from services.base.llm import a_generate
from services.prompts.document_categorization_prompts import (
    SYSTEM_PROMPT, 
    DOCUMENT_CATEGORIZATION_PROMPT
)

logger = logging.getLogger(__name__)


class DocumentCategorizationService:
    """
    Service for categorizing medical documents using available LLM providers.
    
    This service performs the first LLM shot to categorize documents into one of the following categories:
    - Administrative coding documents (PMSI/T2A)
    - Operative reports
    - Hospitalization/stay reports
    - Medical imaging reports
    - Consultation reports
    - Prescription documents
    - Laboratory test results
    - Medical correspondence/liaison letters
    """
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self) -> None:
        """No-op initialize retained for compatibility"""
        if not self._initialized:
            self._initialized = True
            logger.info("Document Categorization Service initialized successfully (no-op)")
    
    async def categorize_document(self, extracted_text: str, source_file: str = "unknown") -> Dict[str, Any]:
        """
        Categorize a medical document using the first LLM shot.
        
        Args:
            extracted_text: The extracted text from the document
            source_file: Name of the source file for tracking
            
        Returns:
            Dictionary containing categorization results
        """
        # Initialize if needed
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info(f"Starting document categorization for {source_file}")
            
            # Prepare the prompt with the document content
            user_prompt = DOCUMENT_CATEGORIZATION_PROMPT.format(content=extracted_text)
            
            # Generate categorization using GPT-Open via unified LLM
            response = await a_generate(
                prompt=user_prompt,
                system=SYSTEM_PROMPT,
                max_tokens=500,
                temperature=0.3,
                provider="gpt_open",
            )
            
            # Parse the response
            categorization_result = self._parse_categorization_response(response)
            
            # Add metadata
            result = {
                "categorization": categorization_result,
                "metadata": {
                    "source_file": source_file,
                    "categorization_completed_at": datetime.now().isoformat(),
                    "model": os.environ.get("GPT_OPEN_MODEL", "gpt-open"),
                    "text_length": len(extracted_text),
                    "raw_response": response
                }
            }
            
            logger.info(f"Document categorization completed for {source_file}: {categorization_result.get('category', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Document categorization failed for {source_file}: {e}")
            return {
                "categorization": {
                    "category": "unknown",
                    "confidence": "low",
                    "reasoning": f"Error during categorization: {str(e)}"
                },
                "metadata": {
                    "source_file": source_file,
                    "categorization_completed_at": datetime.now().isoformat(),
                    "model": os.environ.get("GPT_OPEN_MODEL", "gpt-open"),
                    "text_length": len(extracted_text),
                    "error": str(e)
                }
            }
    
    def _parse_categorization_response(self, response: str) -> Dict[str, str]:
        """
        Parse the LLM response to extract category, confidence, and reasoning.
        
        Args:
            response: Raw response from the LLM provider
            
        Returns:
            Dictionary with category, confidence, and reasoning
        """
        try:
            # Extract category
            category_match = re.search(r'<CATEGORY>(.*?)</CATEGORY>', response, re.DOTALL)
            category = category_match.group(1).strip() if category_match else "unknown"
            
            # Extract confidence
            confidence_match = re.search(r'<CONFIDENCE>(.*?)</CONFIDENCE>', response, re.DOTALL)
            confidence = confidence_match.group(1).strip() if confidence_match else "low"
            
            # Extract reasoning
            reasoning_match = re.search(r'<REASONING>(.*?)</REASONING>', response, re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
            
            return {
                "category": category,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.error(f"Error parsing categorization response: {e}")
            return {
                "category": "unknown",
                "confidence": "low",
                "reasoning": f"Error parsing response: {str(e)}"
            }
    
    def get_supported_categories(self) -> list:
        """
        Get the list of supported document categories.
        
        Returns:
            List of supported categories
        """
        return [
            "Administrative coding documents (PMSI/T2A)",
            "Operative reports",
            "Hospitalization/stay reports",
            "Medical imaging reports",
            "Consultation reports",
            "Prescription documents",
            "Laboratory test results",
            "Medical correspondence/liaison letters"
        ] 