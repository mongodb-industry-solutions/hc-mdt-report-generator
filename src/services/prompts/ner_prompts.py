"""
Named Entity Recognition (NER) Prompts

Contains prompts used for legacy NER entity extraction from medical documents.
These prompts are used by the legacy ner_classifier.py module.
"""

# System prompt for NER extraction
NER_SYSTEM_PROMPT = """You are an expert Named Entity Recognition specialist for medical documents"""

# System prompt for NER aggregation
NER_AGGREGATION_SYSTEM_PROMPT = """You are an expert in information aggregation and synthesis."""

# System prompt for data extraction
NER_DATA_EXTRACTION_SYSTEM_PROMPT = """You are an expert in extracting relevant data from documents."""

# NER extraction prompt template (legacy format)
NER_EXTRACTION_PROMPT_TEMPLATE = """
    """

# NER data extraction prompt template (current format)
NER_DATA_EXTRACTION_PROMPT_TEMPLATE = """<DOCUMENT>
{content}
</DOCUMENT>
    
<ENTITIES>
{entities_text}
</ENTITIES>
    
TASK
****
    
Your task is to extract each of the entities defined in <ENTITIES> from the document in <DOCUMENT> following these rules:
    
- For each entity, return its value using verbatim text from the <DOCUMENT> inside tags of this form: <ENTITY_{{id}}_OUTPUT>...</ENTITY_{{id}}_OUTPUT> where {{id}} is the entity's ordinal number from the provided list.
- If the entity is not found in the document, just return empty tags for that entity, for example: <ENTITY_1_OUTPUT></ENTITY_1_OUTPUT>.

Example output:
<ENTITY_1_OUTPUT>some plain text from the document</ENTITY_1_OUTPUT>
<ENTITY_2_OUTPUT></ENTITY_2_OUTPUT>"""

# NER aggregation prompt template  
NER_AGGREGATION_PROMPT_TEMPLATE = """You are tasked with aggregating extracted values for a specific entity.

ENTITY NAME: {entity_name}
ENTITY DEFINITION: {entity_definition}
AGGREGATION INSTRUCTIONS: {aggregation_instructions}

VALUES TO AGGREGATE:
{values_text}

Your task is to:
1. Analyze all the provided values
2. Follow the specific aggregation instructions for this entity  
3. Create a comprehensive aggregated value that follows the entity's aggregation rules

IMPORTANT: Return ONLY the aggregated value as plain text. Do not include explanations, formatting, or additional text.

AGGREGATED VALUE:"""

# Detailed NER aggregation prompt template with XML formatting
NER_DETAILED_AGGREGATION_PROMPT_TEMPLATE = """You are tasked with aggregating extracted values for a specific entity.  

<ENTITY>  
- Name: {entity_name}  
- Definition: {entity_definition}  
</ENTITY>  

<VALUES>  
{values_text}  
</VALUES>  

INSTRUCTIONS:  
{aggregation_instructions}  

IMPORTANT RULES:  
- Always provide your response in the exact format shown below  
- If you find valid values, put the aggregated result in <o> tags , otherwise just write <o></o> 

REQUIRED FORMAT:  
<o>[your aggregated result here or leave empty if no valid values]</o>  

Examples:  

Example 1 - Valid values found:  
<o>12/06/2025</o>  

Example 2 - No valid values:  
<o></o>  

Now process the data above and provide your response:"""

def create_ner_extraction_prompt() -> str:
    """
    Create a formatted prompt for NER extraction (legacy format).
    
    Returns:
        Formatted prompt string
    """
    return NER_EXTRACTION_PROMPT_TEMPLATE

def create_ner_aggregation_prompt(
    entity_name: str,
    entity_definition: str, 
    aggregation_instructions: str,
    values_text: str
) -> str:
    """
    Create a formatted prompt for NER aggregation.
    
    Args:
        entity_name: Name of the entity being aggregated
        entity_definition: Definition of the entity
        aggregation_instructions: Specific instructions for aggregating this entity
        values_text: Formatted text containing the values to aggregate
        
    Returns:
        Formatted prompt string
    """
    return NER_AGGREGATION_PROMPT_TEMPLATE.format(
        entity_name=entity_name,
        entity_definition=entity_definition,
        aggregation_instructions=aggregation_instructions,
        values_text=values_text
    )

def create_ner_data_extraction_prompt(content: str, entities_text: str) -> str:
    """
    Create a formatted prompt for NER data extraction.
    
    Args:
        content: The document content to extract entities from
        entities_text: Formatted text containing the entities definitions
        
    Returns:
        Formatted prompt string
    """
    return NER_DATA_EXTRACTION_PROMPT_TEMPLATE.format(
        content=content,
        entities_text=entities_text
    )

def create_ner_detailed_aggregation_prompt(
    entity_name: str,
    entity_definition: str, 
    aggregation_instructions: str,
    values_text: str
) -> str:
    """
    Create a formatted prompt for detailed NER aggregation with XML output formatting.
    
    Args:
        entity_name: Name of the entity being aggregated
        entity_definition: Definition of the entity
        aggregation_instructions: Specific instructions for aggregating this entity
        values_text: Formatted text containing the values to aggregate
        
    Returns:
        Formatted prompt string with XML structure and examples
    """
    return NER_DETAILED_AGGREGATION_PROMPT_TEMPLATE.format(
        entity_name=entity_name,
        entity_definition=entity_definition,
        aggregation_instructions=aggregation_instructions,
        values_text=values_text
    ) 