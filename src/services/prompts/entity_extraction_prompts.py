"""
Entity Extraction Prompts

Contains prompts used for extracting medical entities from documents using AI.
These prompts guide the LLM to identify and extract specific medical entities
according to their definitions and processing rules.
"""

# System prompt for entity extraction
ENTITY_EXTRACTION_SYSTEM_PROMPT = """You are an expert in extracting relevant data from documents."""

# Entity extraction prompt template
ENTITY_EXTRACTION_PROMPT_TEMPLATE = """<DOCUMENT>
{document_content}
</DOCUMENT>

<ENTITIES>
{entities_text}
</ENTITIES>

TASK
****

Your task is to extract each of the entities defined in <ENTITIES> from the document in <DOCUMENT> following these rules:

- For each entity, return its value using verbatim text from the <DOCUMENT> inside tags of this form: <ENTITY_{{id}}_OUTPUT>...</ENTITY_{{id}}_OUTPUT> where {{id}} is the entity's ordinal number from the provided list.
- If the entity is not found in the document, just return empty tags for that entity, for example: <ENTITY_1_OUTPUT></ENTITY_1_OUTPUT>.
- If you notice any inconsistency or error in the data or extraction process, please write them inside <WARNINGS> tags. If there are no warnings, omit this tag.

Example output:
<ENTITY_1_OUTPUT>some plain text from the document</ENTITY_1_OUTPUT>
<ENTITY_2_OUTPUT></ENTITY_2_OUTPUT>
<WARNINGS></WARNINGS>
"""

# System prompt for entity aggregation
ENTITY_AGGREGATION_SYSTEM_PROMPT = """You are an expert in information aggregation and synthesis."""

# Entity aggregation prompt template
ENTITY_AGGREGATION_PROMPT_TEMPLATE = """You are tasked with aggregating extracted values for a specific entity.

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
- If you find valid values, put the aggregated result in <OUTPUT> tags , otherwise just write <OUTPUT></OUTPUT>

REQUIRED FORMAT:
<OUTPUT>[your aggregated result here or leave empty if no valid values]</OUTPUT>

Examples:

Example 1 - Valid values found:
<OUTPUT>12/06/2025</OUTPUT>

Example 2 - No valid values:
<OUTPUT></OUTPUT>

Now process the data above and provide your response:"""

def create_entity_extraction_prompt(document_content: str, entities_text: str) -> str:
    """
    Create a formatted prompt for entity extraction.
    
    Args:
        document_content: The document content to extract entities from
        entities_text: Formatted text describing the entities to extract
        
    Returns:
        Formatted prompt string
    """
    return ENTITY_EXTRACTION_PROMPT_TEMPLATE.format(
        document_content=document_content,
        entities_text=entities_text
    )

def create_entity_aggregation_prompt(
    entity_name: str,
    entity_definition: str,
    aggregation_instructions: str,
    values_text: str
) -> str:
    """
    Create a formatted prompt for entity aggregation.
    
    Args:
        entity_name: Name of the entity being aggregated
        entity_definition: Definition of the entity
        aggregation_instructions: Specific instructions for aggregating this entity
        values_text: Formatted text containing the values to aggregate
        
    Returns:
        Formatted prompt string
    """
    return ENTITY_AGGREGATION_PROMPT_TEMPLATE.format(
        entity_name=entity_name,
        entity_definition=entity_definition,
        aggregation_instructions=aggregation_instructions,
        values_text=values_text
    )

def format_entities_for_extraction(entity_batch) -> str:
    """
    Format entity definitions for extraction prompt.
    
    Args:
        entity_batch: List of EntityDefinition objects
        
    Returns:
        Formatted entities text for the prompt
    """
    entities_text = ""
    for idx, entity in enumerate(entity_batch, 1):
        entities_text += (
            f"<ENTITY_{idx}>\n"
            f"-id:{idx}\n"
            f"-Name: {entity.name}\n"
            f"- Definition: {entity.definition}\n"
            f"- Extraction instructions: {entity.extraction_instructions}, please write the extracted data in plain text format within tags <ENTITY_{idx}_OUTPUT>\n"
            + (f"   - Valid values: {', '.join(entity.valid_values)}\n" if hasattr(entity, 'valid_values') and entity.valid_values else "")
            + f"</ENTITY_{idx}>\n"
        )
    return entities_text

def format_values_for_aggregation(values_list) -> str:
    """
    Format values for aggregation prompt.
    
    Args:
        values_list: List of values to be aggregated
        
    Returns:
        Formatted values text for the prompt
    """
    values_text = ""
    for val in values_list:
        values_text += f"{val}\n"
    return values_text 