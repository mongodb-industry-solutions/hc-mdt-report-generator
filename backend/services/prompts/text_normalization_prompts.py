"""
Text Normalization Prompts

Contains prompts used for normalizing medical document text using AI.
These prompts guide the LLM to clean, structure, and normalize medical document text
while preserving all important medical information and data accuracy.
"""

# System prompt for text normalization
SYSTEM_PROMPT = """You are a medical document normalization expert. Your job is to clean, structure, and normalize medical document text while preserving all important medical information and data accuracy."""

# Base normalization prompt template
TEXT_NORMALIZATION_PROMPT = """You are a medical document normalization expert.

TASK: Normalize and clean the following medical document text while preserving all important medical information.

ORIGINAL FILE TYPE: {file_type}

NORMALIZATION RULES:
1. Clean up formatting issues (extra spaces, line breaks, etc.)
2. Standardize medical terminology and abbreviations
3. Structure unstructured data where possible
4. Preserve all medical data, measurements, and values exactly
5. Maintain document structure and logical flow
6. Remove OCR artifacts while keeping meaningful content
7. Standardize date formats to ISO format (YYYY-MM-DD) where possible
8. Clean up table formatting and ensure data alignment
9. Preserve all numerical values, units, and measurements exactly

ORIGINAL TEXT:
{raw_text}

IMPORTANT: You MUST respond using the exact XML format below. Do not add any text before or after the XML tags.

<NORMALIZED_TEXT>
[Your normalized text here - this is the main normalized content]
</NORMALIZED_TEXT>

<STRUCTURED_DATA>
[Any structured data extracted (tables, lists, etc.) in JSON format if applicable, or leave empty if none]
</STRUCTURED_DATA>

<NORMALIZATION_NOTES>
[Brief notes about what was normalized/changed, or "No changes needed" if minimal changes]
</NORMALIZATION_NOTES>

CRITICAL: Always start your response with <NORMALIZED_TEXT> and end with </NORMALIZATION_NOTES>. Do not include any other text outside these XML tags."""

# File type specific instructions
FILE_TYPE_INSTRUCTIONS = {
    'csv': """
SPECIAL INSTRUCTIONS FOR CSV FILES:
- Preserve the original data structure where possible
- Clean up any formatting issues while maintaining data integrity
- Ensure all fields and values are properly formatted
- Maintain any hierarchical structure present in the original""",
    
    'xml': """
SPECIAL INSTRUCTIONS FOR XML FILES:
- Preserve the original data structure where possible
- Clean up any formatting issues while maintaining data integrity
- Ensure all fields and values are properly formatted
- Maintain any hierarchical structure present in the original""",
    
    'json': """
SPECIAL INSTRUCTIONS FOR JSON FILES:
- Preserve the original data structure where possible
- Clean up any formatting issues while maintaining data integrity
- Ensure all fields and values are properly formatted
- Maintain any hierarchical structure present in the original""",
    
    'pdf': """
SPECIAL INSTRUCTIONS FOR PDF FILES:
- Clean up OCR artifacts and formatting issues
- Preserve table structures and data alignment
- Maintain document sections and headers
- Standardize spacing and typography
- Ensure medical terminology is properly formatted""",
    
    'txt': """
SPECIAL INSTRUCTIONS FOR TEXT FILES:
- Clean up any formatting inconsistencies
- Standardize line breaks and spacing
- Preserve document structure and sections
- Ensure medical terminology is properly formatted""",
    
    'md': """
SPECIAL INSTRUCTIONS FOR TEXT FILES:
- Clean up any formatting inconsistencies
- Standardize line breaks and spacing
- Preserve document structure and sections
- Ensure medical terminology is properly formatted"""
}

def create_normalization_prompt(raw_text: str, file_type: str = "unknown") -> str:
    """
    Create a formatted prompt for text normalization.
    
    Args:
        raw_text: The raw text to normalize (from OCR or plain text)
        file_type: Type of the original file (pdf, txt, csv, xml, json, etc.)
        
    Returns:
        Formatted prompt string
    """
    # Start with base prompt
    prompt = TEXT_NORMALIZATION_PROMPT.format(
        file_type=file_type.upper(),
        raw_text=raw_text
    )
    
    # Add file-type specific instructions if available
    file_type_lower = file_type.lower()
    if file_type_lower in FILE_TYPE_INSTRUCTIONS:
        prompt += FILE_TYPE_INSTRUCTIONS[file_type_lower]
    
    return prompt 