"""
Ground Truth Entity Extraction Service

Extracts entities from OCR text using the same LLM-based approach
as the main entity extraction, but optimized for ground truth documents.

UPDATED: Now supports template_id for consistency with report generation,
uses AWS Bedrock as primary choice and Mistral API as secondary choice.
"""

import os
import json
import logging
import re
import unicodedata
from typing import List, Dict, Any, Optional

from config.entity_config import get_active_template, get_template_by_id

logger = logging.getLogger(__name__)


# System prompt for GT entity extraction (mapping-focused)
GT_EXTRACTION_SYSTEM_PROMPT = """You are an expert medical data extractor. Your task is to map information from a medical document to specific entity names.

The text may have OCR errors or formatting issues - use your medical knowledge to interpret correctly.
Map the document's labels to the standardized entity names provided.
Extract values exactly as they appear in the document when possible.
If an entity is not found in the document, set its value to null."""


# Extraction prompt template (mapping-focused)
GT_EXTRACTION_PROMPT_TEMPLATE = """<DOCUMENT>
{document_text}
</DOCUMENT>

<ENTITY_TEMPLATE>
Extract these entities from the document:
{entities_list}
</ENTITY_TEMPLATE>

TASK:
Read the document and extract the value for each entity listed above.

CRITICAL - USE EXACT ENTITY NAMES:
- Use the EXACT entity names as shown above (with spaces and proper capitalization)
- Example: "Diagnosis Date", NOT "DIAGNOSIS_DATE"
- Example: "Cancer Location", NOT "CANCER_LOCATION"

EXTRACTION RULES:
- Extract verbatim values from the document
- For dates, preserve the original format (e.g., "12/06/2024", "June 12, 2024")
- For medical values, include units if present (e.g., "Ki67: 15%")
- If an entity is not found, set its value to null

Return ONLY valid JSON with the EXACT entity names as keys:
{{"Diagnosis Date": "extracted_value", "Cancer Location": "extracted_value", ...}}"""


class GTEntityExtractionService:
    """
    Service to extract/map entities from ground truth OCR text using LLM.
    
    Supports:
    - Template ID for consistency with report generation
    - AWS Bedrock when LLM_PROVIDER is "bedrock" (primary choice)
    - Mistral API when LLM_PROVIDER is "mistral" (secondary choice)
    - Fallback to gpt_open for other providers
    """

    def __init__(self):
        self._entities_cache = None

    async def extract_entities(
        self,
        ocr_text: str,
        template_id: Optional[str] = None,
        entity_names: Optional[List[str]] = None,
        llm_provider: Optional[str] = None  # User's LLM selection from Settings
    ) -> List[Dict[str, Any]]:
        """
        Extract/map entities from OCR text.
        
        Args:
            ocr_text: Text extracted via OCR from ground truth PDF
            template_id: Optional template ID to use (for consistency with report)
            entity_names: Optional list of specific entity names to extract.
                         If None, uses all entities from template.
            llm_provider: LLM provider to use ("bedrock", "mistral", or "gpt_open").
                         If None, falls back to LLM_PROVIDER env var.
                         
        Returns:
            List of extracted entities with name, value, source, and confidence
        """
        # Get entity definitions from template
        entity_definitions = await self._get_entity_definitions(template_id, entity_names)
        
        if not entity_definitions:
            logger.warning("No entity definitions found for GT extraction")
            return []

        # Format entities for the prompt
        entities_list = self._format_entities_for_prompt(entity_definitions)
        
        # Create extraction prompt
        prompt = GT_EXTRACTION_PROMPT_TEMPLATE.format(
            document_text=ocr_text[:50000],  # Limit to prevent token overflow
            entities_list=entities_list
        )
        
        # Call LLM based on provider (user selection takes priority)
        try:
            response = await self._call_llm(prompt, GT_EXTRACTION_SYSTEM_PROMPT, llm_provider)
            
            # DEBUG: Log raw LLM response
            logger.info(f"GT extraction raw LLM response (first 500 chars): {response[:500]}")
            
            # Parse response
            extracted = self._parse_llm_response(response, entity_definitions)
            
            # DEBUG: Log extraction results
            found_count = sum(1 for e in extracted if e.get('value'))
            null_count = sum(1 for e in extracted if not e.get('value'))
            logger.info(f"GT extraction: {len(extracted)} total, {found_count} with values, {null_count} null")
            return extracted
            
        except Exception as e:
            logger.error(f"GT entity extraction failed: {e}")
            raise

    async def _call_llm(self, prompt: str, system_prompt: str, llm_provider: Optional[str] = None) -> str:
        """
        Call LLM based on user's selection or LLM_PROVIDER environment variable.
        User's selection takes priority over environment variable.
        """
        # Use user's selection if provided, otherwise fall back to env var
        if llm_provider:
            provider = llm_provider.lower()
        else:
            provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
        
        logger.info(f"GT extraction using LLM provider: {provider}")
        
        # Route based on provider - Bedrock first, then Mistral as secondary
        if provider == "bedrock":
            return await self._call_bedrock(prompt, system_prompt)
        elif "mistral" in provider:
            return await self._call_mistral(prompt, system_prompt)
        elif "ollama" in provider or "gpt" in provider:
            return await self._call_gpt_open(prompt, system_prompt)
        else:
            # Default to bedrock for unknown providers
            logger.warning(f"Unknown provider '{provider}', falling back to bedrock")
            return await self._call_bedrock(prompt, system_prompt)
    
    async def _call_bedrock(self, prompt: str, system_prompt: str) -> str:
        """Call AWS Bedrock for extraction."""
        try:
            from infrastructure.llm.bedrock_client import AsyncBedrockClient
            
            logger.info("Using AWS Bedrock for GT entity extraction")
            
            async with AsyncBedrockClient() as bedrock_client:
                response = await bedrock_client.invoke_bedrock_async_robust(
                    system_prompt,
                    prompt,
                    timeout_override=120  # 2 minute timeout for extraction
                )
            return response
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            # Fallback to gpt_open
            logger.warning("Falling back to gpt_open")
            return await self._call_gpt_open(prompt, system_prompt)
    
    async def _call_mistral(self, prompt: str, system_prompt: str) -> str:
        """Call Mistral API for extraction (secondary choice)."""
        try:
            from infrastructure.llm.mistral_client import AsyncMistralClient
            
            logger.info("Using Mistral API for GT entity extraction (secondary choice)")
            mistral_client = AsyncMistralClient()
            response = await mistral_client.invoke_mistral_async_robust(
                system_prompt,
                prompt,
                timeout_override=120  # 2 minute timeout for extraction
            )
            return response
            
        except ImportError as e:
            logger.error(f"Mistral client not available: {e}")
            # Fallback to gpt_open
            logger.warning("Falling back to gpt_open")
            return await self._call_gpt_open(prompt, system_prompt)
        except Exception as e:
            logger.error(f"Mistral API call failed: {e}")
            raise
    
    async def _call_gpt_open(self, prompt: str, system_prompt: str) -> str:
        """Call GPT-Open compatible server for extraction."""
        from services.base.llm import a_generate
        
        logger.info("Using GPT-Open for GT entity extraction")
        return await a_generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.0  # Deterministic for extraction
        )

    async def _get_entity_definitions(
        self,
        template_id: Optional[str] = None,
        entity_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entity definitions from template.
        
        Args:
            template_id: Optional specific template ID to use
            entity_names: Optional filter for specific entity names
            
        Returns:
            List of entity definition dictionaries
        """
        try:
            if template_id:
                # Fetch specific template by ID (for consistency with report)
                template = get_template_by_id(template_id)
                if template:
                    logger.info(f"Using template by ID: {template_id}")
                else:
                    logger.warning(f"Template {template_id} not found, falling back to active template")
                    template, source = get_active_template()
            else:
                # Use active template
                template, source = get_active_template()
                logger.info(f"Using active template (source: {source})")
            
            if not template:
                logger.warning("No template found for GT extraction")
                return []
            
            # Extract entities from template
            all_entities = template.get("entities", [])
            
            if entity_names:
                # Filter to requested entities
                return [e for e in all_entities if e.get("name") in entity_names]
            
            return all_entities
            
        except Exception as e:
            logger.error(f"Failed to get entity definitions: {e}")
            return []

    def _format_entities_for_prompt(self, entity_definitions: List[Dict[str, Any]]) -> str:
        """
        Format entity definitions for the extraction prompt.
        
        Args:
            entity_definitions: List of entity definition dicts
            
        Returns:
            Formatted string for prompt
        """
        lines = []
        for idx, entity in enumerate(entity_definitions, 1):
            name = entity.get("name", f"Entity_{idx}")
            definition = entity.get("definition", "")
            instructions = entity.get("extraction_instructions", "")
            
            line = f"{idx}. {name}"
            if definition:
                line += f": {definition}"
            if instructions:
                line += f" ({instructions})"
            
            lines.append(line)
        
        return "\n".join(lines)

    def _normalize_key(self, key: str) -> str:
        """
        Normalize entity key for matching.
        
        Handles variations like:
        - "Date de diagnostic" vs "DATE_DE_DIAGNOSTIC"
        - "Localisation primitive" vs "LOCALISATION_PRIMITIVE"
        - "Lésion primaire" vs "LESION_PRIMAIRE" (accents)
        
        Args:
            key: Entity name/key to normalize
            
        Returns:
            Normalized key (lowercase, no spaces/underscores/accents)
        """
        if not key:
            return ""
        
        # Remove accents (NFD decomposition then filter out combining marks)
        normalized = unicodedata.normalize('NFD', key)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # Lowercase and remove spaces/underscores/hyphens
        normalized = normalized.lower()
        normalized = normalized.replace(' ', '').replace('_', '').replace('-', '')
        
        return normalized

    def _parse_llm_response(
        self,
        response: str,
        entity_definitions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured entity list.
        
        Args:
            response: Raw LLM response text
            entity_definitions: Original entity definitions
            
        Returns:
            List of extracted entities
        """
        extracted_entities = []
        
        # Try to extract JSON from response
        try:
            # Find JSON in response (may have extra text)
            # Try to find the largest JSON object
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
            else:
                # Try parsing entire response as JSON
                parsed = json.loads(response)
            
            # Build mapping from normalized keys to original entity names
            entity_name_map = {}  # normalized_key -> original_name
            for e in entity_definitions:
                name = e.get("name")
                if name:
                    normalized = self._normalize_key(name)
                    entity_name_map[normalized] = name
            
            entity_name_set = set(entity_name_map.values())
            
            # DEBUG: Log what we're matching
            logger.info(f"GT parsing - Expected entity names: {list(entity_name_set)}")
            logger.info(f"GT parsing - LLM returned keys: {list(parsed.keys())}")
            
            matched_count = 0
            for llm_key, value in parsed.items():
                # Try exact match first
                if llm_key in entity_name_set:
                    matched_name = llm_key
                    matched_count += 1
                else:
                    # Try normalized match (handles UPPERCASE_UNDERSCORE vs "Accented Name")
                    normalized_llm_key = self._normalize_key(llm_key)
                    if normalized_llm_key in entity_name_map:
                        matched_name = entity_name_map[normalized_llm_key]
                        matched_count += 1
                        logger.debug(f"GT parsing - Fuzzy matched: '{llm_key}' -> '{matched_name}'")
                    else:
                        logger.debug(f"GT parsing - No match for key: '{llm_key}' (normalized: '{normalized_llm_key}')")
                        continue
                
                # Normalize value
                if value is None or (isinstance(value, str) and not value.strip()):
                    normalized_value = None
                    confidence = 0.0
                else:
                    normalized_value = str(value).strip()
                    confidence = 0.9  # High confidence for LLM extraction
                
                extracted_entities.append({
                    "entity_name": matched_name,  # Use the original template name
                    "value": normalized_value,
                    "source": "extracted",
                    "confidence": confidence
                })
            
            logger.info(f"GT parsing - Matched {matched_count}/{len(parsed)} LLM keys to entities")
            
            # Add missing entities with null values
            found_names = {e["entity_name"] for e in extracted_entities}
            for entity_def in entity_definitions:
                name = entity_def.get("name")
                if name and name not in found_names:
                    extracted_entities.append({
                        "entity_name": name,
                        "value": None,
                        "source": "extracted",
                        "confidence": 0.0
                    })
                    
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            # Return empty entities for all definitions
            for entity_def in entity_definitions:
                extracted_entities.append({
                    "entity_name": entity_def.get("name", "Unknown"),
                    "value": None,
                    "source": "extracted",
                    "confidence": 0.0
                })
        
        return extracted_entities

    async def extract_entities_with_confidence(
        self,
        ocr_text: str,
        template_id: Optional[str] = None,
        entity_names: Optional[List[str]] = None,
        verify: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract entities with optional verification pass for higher confidence.
        
        Args:
            ocr_text: OCR text to extract from
            template_id: Optional template ID to use
            entity_names: Optional filter for specific entities
            verify: If True, run a second pass to verify extractions
            
        Returns:
            List of extracted entities with confidence scores
        """
        # First extraction pass
        entities = await self.extract_entities(ocr_text, template_id, entity_names)
        
        if not verify:
            return entities
        
        # Verification pass (optional, increases API cost)
        verified_entities = []
        for entity in entities:
            if entity.get("value") and entity.get("confidence", 0) > 0.5:
                # Verify high-confidence extractions
                verified = await self._verify_extraction(
                    ocr_text,
                    entity["entity_name"],
                    entity["value"]
                )
                entity["confidence"] = verified["confidence"]
                if verified.get("corrected_value"):
                    entity["value"] = verified["corrected_value"]
            
            verified_entities.append(entity)
        
        return verified_entities

    async def _verify_extraction(
        self,
        ocr_text: str,
        entity_name: str,
        extracted_value: str
    ) -> Dict[str, Any]:
        """
        Verify an extracted value against the source text.
        
        Args:
            ocr_text: Original OCR text
            entity_name: Name of the entity
            extracted_value: Value that was extracted
            
        Returns:
            Dict with confidence and optional corrected_value
        """
        verification_prompt = f"""Verify this extraction from a medical document:

Entity: {entity_name}
Extracted Value: {extracted_value}

Source text snippet (search for the entity):
{ocr_text[:10000]}

Is this extraction correct? Respond with JSON:
{{"correct": true/false, "confidence": 0.0-1.0, "corrected_value": "..." or null}}"""

        try:
            response = await self._call_llm(
                verification_prompt,
                "You verify medical entity extractions. Return only JSON."
            )
            
            # Parse verification response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "confidence": result.get("confidence", 0.9),
                    "corrected_value": result.get("corrected_value")
                }
        except Exception as e:
            logger.warning(f"Verification failed for {entity_name}: {e}")
        
        return {"confidence": 0.9, "corrected_value": None}
