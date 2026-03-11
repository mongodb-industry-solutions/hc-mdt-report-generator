"""
Section Summary Service - Generates narrative summaries for report sections using LLM
"""

import logging
from typing import List, Dict, Any
import asyncio
import json
import os

# Import the unified LLM service
from services.base.llm import a_generate

logger = logging.getLogger(__name__)


class SectionSummaryService:
    """
    Service for generating narrative summaries of medical report sections.
    
    Takes extracted entities and converts them into coherent, readable prose
    suitable for medical professionals.
    """
    
    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
        logger.info(f"🧠 Section Summary Service initialized with provider: {self.provider}")
    
    async def generate_summary(self, section_title: str, entities: List[Dict[str, Any]]) -> str:
        """
        Generate a narrative summary for a medical report section.
        
        Args:
            section_title: The name of the section (e.g., "Patient Information", "Clinical Summary")
            entities: List of entities with name, value, processing_type
            
        Returns:
            A narrative text summary of the section
        """
        try:
            logger.info(f"Generating summary for section: {section_title} using provider: {self.provider}")
            
            # Filter out empty entities
            valid_entities = [e for e in entities if e.get('value') and str(e.get('value')).strip()]
            logger.info(f"Found {len(valid_entities)} valid entities for {section_title}")
            
            if not valid_entities:
                return f"No specific information was extracted for the {section_title} section."
            
            # Create prompt for LLM with detailed entity information
            prompt = self._create_detailed_summary_prompt(section_title, valid_entities)
            logger.info(f"Generated prompt for {section_title}: {len(prompt)} characters")
            
            # Generate using the same provider pattern as entity extraction service
            if self.provider == "bedrock":
                # Use AWS Bedrock client (consistent with entity extraction service)
                from infrastructure.llm.bedrock_client import AsyncBedrockClient
                
                logger.info(f"🔄 Using AWS Bedrock for summary generation")
                async with AsyncBedrockClient() as bedrock_client:
                    response = await bedrock_client.invoke_bedrock_async_robust(
                        "You are a medical AI assistant specialized in creating comprehensive, detailed narrative summaries of medical report sections. Always write thorough, complete summaries that include all provided data. Write 3-5 paragraphs minimum with full context and details.",
                        prompt,
                        timeout_override=90
                    )
                    
                    logger.info(f"✅ Bedrock response for {section_title}: {len(response or '')} characters")
                    summary = response.strip() if response else ""
                
            else:
                # Use the unified LLM service (for GPT-Open and other providers)
                logger.info(f"🔄 Using unified LLM service ({self.provider}) for summary generation")
                response = await a_generate(
                    prompt=prompt,
                    system="You are a medical AI assistant specialized in creating comprehensive, detailed narrative summaries of medical report sections. Always write thorough, complete summaries that include all provided data. Write 3-5 paragraphs minimum with full context and details.",
                    max_tokens=2000,  # Significantly increased for comprehensive summaries
                    temperature=0.3   # Balanced for detailed yet natural language
                )
                
                logger.info(f"✅ LLM response for {section_title}: {len(response or '')} characters")
                # Clean and validate response
                summary = self._clean_summary(response)
            
            # More lenient validation - accept comprehensive summaries of appropriate length
            if len(summary.strip()) < 30:  # Further reduced threshold
                logger.warning(f"Generated summary too short for {section_title} ({len(summary)} chars), using enhanced fallback")
                return self._create_enhanced_fallback_summary(section_title, valid_entities)
            
            logger.info(f"Successfully generated comprehensive summary for {section_title} ({len(summary)} characters)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary for {section_title}: {e}")
            return self._create_enhanced_fallback_summary(section_title, entities)
    
    def _create_detailed_summary_prompt(self, section_title: str, entities: List[Dict[str, Any]]) -> str:
        """Create a comprehensive prompt with detailed entity information for section summarization"""
        
        # Format entities with their full values for comprehensive analysis
        entity_details = []
        for entity in entities:
            name = entity.get('name', 'Unknown')
            value = str(entity.get('value', '')).strip()
            
            if value:
                # Handle different value types (string, list, etc.)
                if isinstance(entity.get('value'), list):
                    value_text = "; ".join([str(v).strip() for v in entity.get('value', []) if str(v).strip()])
                else:
                    value_text = value
                
                # Preserve full entity values for comprehensive summaries
                # Only truncate extremely long values (over 2000 chars) to prevent prompt overflow
                if len(value_text) > 2000:
                    value_text = value_text[:2000] + " [content continues...]"
                
                entity_details.append(f"**{name}**: {value_text}")
        
        entities_text = "\n".join(entity_details)
        
        prompt = f"""You are a medical AI assistant creating a comprehensive, detailed narrative summary for the {section_title} section of a medical report.

IMPORTANT: Write a thorough, complete summary that includes ALL the provided information. Write 3-5 paragraphs minimum (200-400 words). Do not truncate, abbreviate, or omit any medical information. Provide complete details for every piece of data.

**EXTRACTED MEDICAL DATA:**
{entities_text}

**TASK:**
Write a detailed, professional medical narrative that:
1. Incorporates EVERY piece of provided medical information without exception
2. Creates flowing, coherent prose. Add bullet points if it enhances readability, but ensure they are fully detailed and not just lists of terms.
3. Groups related information logically into cohesive paragraphs
4. Uses appropriate medical terminology and clinical language
5. Maintains clinical accuracy and provides full context
6. Creates meaningful connections between different data points
7. Writes in third person perspective
8. Provides comprehensive details for all treatments, plans, and interventions
9. DO NOT include any introductory phrases like "Here is a narrative summary" or "Summary:" - just write the summary directly.

**WRITING REQUIREMENTS:**
- Write 3-5 complete paragraphs (minimum 200 words)
- Include ALL specific values, dates, measurements, and details from the data
- Use transitional phrases to connect information smoothly across paragraphs
- Focus on clinical significance and comprehensive patient care context
- Explain the significance of findings and their clinical implications
- Do NOT use headers, bullets, numbered lists, or abbreviations
- Write as continuous narrative text only
- NEVER truncate or summarize with "etc." or "..."

**COMPREHENSIVE EXAMPLE STYLE:**
Use this style for your summary, ensuring every detail is included and explained:
Instead of: "Age: 65, Gender: Male, DOB: 1958-03-15, Condition: CAD"
Write: "The patient is a 65-year-old male born on March 15, 1958, who presents with a documented history of coronary artery disease requiring comprehensive cardiovascular management and ongoing medical supervision..."
This is only an example of the level of detail and completeness expected. Your summary should be similarly comprehensive, including all provided data with full context and clinical significance.Do not use this specific example for the summary, but follow the same approach of fully incorporating all details into a rich, detailed narrative.

Generate a comprehensive, detailed narrative summary that includes every piece of medical information:"""

        return prompt
    
    def _clean_summary(self, raw_summary: str) -> str:
        """Clean and validate the generated summary"""
        if not raw_summary:
            return ""
        
        # Remove any unwanted formatting
        cleaned = raw_summary.strip()
        
        # Remove common LLM artifacts
        cleaned = cleaned.replace("**", "").replace("*", "")
        cleaned = cleaned.replace("###", "").replace("##", "").replace("#", "")
        
        # Remove any introductory phrases that might appear
        cleaned = cleaned.replace("Here is a narrative summary:", "").strip()
        cleaned = cleaned.replace("Summary:", "").strip()
        cleaned = cleaned.replace("Narrative:", "").strip()
        
        # Ensure proper sentence structure
        if not cleaned.endswith('.') and not cleaned.endswith('!') and not cleaned.endswith('?'):
            cleaned += '.'
        
        return cleaned
    
    def _create_enhanced_fallback_summary(self, section_title: str, entities: List[Dict[str, Any]]) -> str:
        """Create a detailed fallback summary that includes actual entity data"""
        valid_entities = [e for e in entities if e.get('value') and str(e.get('value')).strip()]
        
        if not valid_entities:
            return f"No information was available for the {section_title} section."
        
        if len(valid_entities) == 1:
            entity = valid_entities[0]
            name = entity.get('name', 'Information')
            value = str(entity.get('value', 'available')).strip()
            return f"For {section_title}: The {name} was documented as {value}."
        
        # Create a comprehensive fallback that includes actual data
        summary_parts = []
        summary_parts.append(f"The {section_title} section includes important medical information.")
        
        # Include key data points
        key_entities = valid_entities[:5]  # Limit to first 5 to avoid overly long text
        for entity in key_entities:
            name = entity.get('name', 'Unknown')
            value = str(entity.get('value', '')).strip()
            
            if value:
                # Preserve full values for comprehensive fallback summaries  
                # Only truncate extremely long values (over 1000 chars) to prevent display issues
                if len(value) > 1000:
                    value = value[:1000] + " [continued with additional clinical details]"
                summary_parts.append(f"The {name} is comprehensively documented as: {value}.")
        
        if len(valid_entities) > 5:
            remaining = len(valid_entities) - 5
            summary_parts.append(f"Additional {remaining} data points were also extracted for this section.")
        
        return " ".join(summary_parts)