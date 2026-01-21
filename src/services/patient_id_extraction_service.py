"""
Patient ID Extraction Service

Dedicated service for extracting patient identifiers (NumdosGR) from documents.
This runs independently of user-defined entity templates to ensure patient_id 
is always available, even if the template doesn't include NumdosGR.

SIMPLIFIED: Just 2 strategies - LLM extraction or auto-generate.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PatientIdExtractionService:
    """
    Service for extracting patient identifiers from medical documents - SIMPLIFIED.
    
    This service:
    1. Attempts to extract NumdosGR using LLM
    2. Auto-generates ID if not found
    3. Runs independently of user templates
    4. Never fails - always provides valid patient_id
    """
    
    def __init__(self):
        self.numdos_entity_definition = {
            "name": "NumdosGR",
            "definition": "Numéro d'identification unique du patient dans le système",
            "extraction_instructions": "Extraire le numéro d'identification du patient, généralement composé de chiffres et/ou lettres. Chercher des termes comme: NIP, Identifiant, Patient ID, Numéro patient, NIPCOMPLETE, NODOSSIER, etc.",
            "type": "string",
            "processing_type": "first_match"
        }
    
    async def extract_patient_id(
        self,
        document_text: str,
        document_uuid: str,
        current_patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract patient ID from document text - SIMPLIFIED.
        
        Strategy:
        1. Try LLM extraction of NumdosGR
        2. If not found, auto-generate from UUID
        
        Args:
            document_text: Raw OCR text from the document
            document_uuid: UUID of the document
            current_patient_id: Current patient_id (if it's AUTO_xxx, we'll replace it)
            
        Returns:
            Dictionary with:
            - patient_id: The extracted or generated patient ID
            - source: How the ID was obtained (extracted|auto)
            - confidence: Confidence level (high|low)
            - metadata: Additional extraction details
        """
        try:
            logger.info(f"Starting patient ID extraction for document {document_uuid}")
            
            # Strategy 1: Try LLM extraction of NumdosGR
            llm_result = await self._extract_with_llm(document_text)
            if llm_result["success"]:
                logger.info(f"✓ Found NumdosGR via LLM: {llm_result['patient_id']}")
                return llm_result
            
            # Strategy 2: NOT FOUND - return None (no auto-generation)
            logger.warning(f"⚠️  NumdosGR not found in document {document_uuid}")
            
            return {
                "patient_id": None,
                "source": "not_found",
                "confidence": "none",
                "success": False,
                "metadata": {
                    "extraction_method": "llm_failed",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "NumdosGR not found in document text"
                }
            }
            
        except Exception as e:
            logger.error(f"Patient ID extraction failed: {e}")
            # On error, return None
            return {
                "patient_id": None,
                "source": "error",
                "confidence": "none",
                "success": False,
                "metadata": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    async def _extract_with_llm(self, document_text: str) -> Dict[str, Any]:
        """
        Use LLM to extract NumdosGR from document.
        
        This follows the SAME LLM provider selection as entity extraction:
        - Checks LLM_PROVIDER environment variable
        - Uses Mistral client if provider="mistral"
        - Uses generate() function otherwise (GPT-Open)
        """
        try:
            import os
            import json
            import asyncio
            import re
            
            # Check which LLM provider to use (same as entity_extraction_service.py)
            provider = os.environ.get("LLM_PROVIDER", "").lower()
            
            # Create extraction prompt
            prompt = f"""Extract the patient ID (NumdosGR) from this medical document.

Entity Definition:
- Name: NumdosGR
- Definition: Numéro d'identification unique du patient dans le système
- Instructions: Extraire le numéro d'identification du patient, généralement composé de chiffres et/ou lettres. Chercher des termes comme: NIP, Identifiant, Patient ID, Numéro patient, NIPCOMPLETE, NODOSSIER, etc.

Document text (first 8000 chars):
{document_text[:8000]}

Return ONLY a JSON object with the entity name as key and extracted value as value.
Example: {{"NumdosGR": "123456788AC"}}

If not found, return: {{"NumdosGR": null}}

Return ONLY the JSON, no explanation."""

            system_prompt = "You are a medical data extraction specialist. Extract entities precisely as instructed."
            
            # Use the same LLM provider as entity extraction
            if provider == "mistral":
                logger.info("Using Mistral client for patient ID extraction")
                # Use Mistral official client (same as entity extraction)
                from infrastructure.llm.mistral_client import AsyncMistralClient
                
                mistral_client = AsyncMistralClient()
                response = await mistral_client.invoke_mistral_async_robust(
                    system_prompt,
                    prompt,
                    timeout_override=120,
                )
            else:
                logger.info(f"Using generate() function for patient ID extraction (provider={provider or 'default'})")
                # Use unified wrapper call (same as entity extraction)
                from services.base.llm import generate
                
                response = await asyncio.to_thread(
                    generate,
                    prompt,
                    system_prompt,
                    reasoning_effort="low",
                )
            
            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract from text
                logger.warning(f"Response is not valid JSON, attempting text extraction")
                patterns = [
                    r'"NumdosGR"\s*:\s*"([^"]+)"',
                    r'NumdosGR:\s*([^\s,}\n]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        result = {"NumdosGR": match.group(1)}
                        break
                else:
                    result = {"NumdosGR": None}
            
            # Check if NumdosGR was found
            if result.get("NumdosGR"):
                numdos_value = str(result["NumdosGR"]).strip()
                if numdos_value and numdos_value.lower() != "null":
                    return {
                        "patient_id": numdos_value,
                        "source": "extracted_llm",
                        "confidence": "high",
                        "success": True,
                        "metadata": {
                            "extraction_method": f"llm_{provider or 'default'}",
                            "entity": "NumdosGR",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
            
            return {"success": False}
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    
    def should_update_patient_id(self, current_patient_id: str, new_patient_id: str) -> bool:
        """
        Determine if we should update the patient_id.
        
        Rules:
        - Never update if new_patient_id is None (extraction failed)
        - Always update if current is None and new is not None (first extraction)
        - Never update if current is explicit (preserve existing)
        """
        # Don't update if new extraction failed
        if new_patient_id is None:
            return False
        
        # Always update if current is None (first successful extraction)
        if current_patient_id is None:
            return True
        
        # Don't overwrite explicit IDs (preserve existing)
        return False

