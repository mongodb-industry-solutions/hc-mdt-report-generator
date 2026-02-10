"""
Entity Extraction Prompts

Contains prompts used for extracting medical entities from documents using AI.
These prompts guide the LLM to identify and extract specific medical entities
according to their definitions and processing rules.
"""

# System prompts for entity extraction
ENTITY_EXTRACTION_SYSTEM_PROMPT_VERBATIM = """You are an expert in extracting relevant data from documents."""

ENTITY_EXTRACTION_SYSTEM_PROMPT_LINE_RANGES = """You are an expert at locating information in documents using line numbers.

RULES:
- The document content is presented as enumerated lines in the form `L<number>: <content>` with each line wrapped to at most 80 characters.
- For each requested entity, you must return ONLY the line range where the entity appears.
- Use the exact format `L<start>-L<end>` (inclusive, 1-based indices). For a single line, use `L<n>-L<n>`.
- Do not include any verbatim document text in your output. Only return ranges inside the specified XML tags.
"""

# Entity extraction prompt templates
ENTITY_EXTRACTION_PROMPT_TEMPLATE_VERBATIM = """<DOCUMENT>
{document_content}
</DOCUMENT>

<ENTITIES>
{entities_text}
</ENTITIES>

TASK
****

Your task is to extract each of the entities defined in <ENTITIES> from the document in <DOCUMENT> following these rules:

- For each entity, return its value using verbatim text from the <DOCUMENT> inside tags of this form: <ENTITY_{id}_OUTPUT>...</ENTITY_{id}_OUTPUT> where {id} is the entity's ordinal number from the provided list.
- If the entity is not found in the document, just return empty tags for that entity, for example: <ENTITY_1_OUTPUT></ENTITY_1_OUTPUT>.

Example output:
<ENTITY_1_OUTPUT>some plain text from the document</ENTITY_1_OUTPUT>
<ENTITY_2_OUTPUT></ENTITY_2_OUTPUT>
"""

ENTITY_EXTRACTION_PROMPT_TEMPLATE_LINE_RANGES = """<DOCUMENT_LINES>
{document_content}
</DOCUMENT_LINES>

<ENTITIES>
{entities_text}
</ENTITIES>

TASK
****

Your task is to locate each entity defined in <ENTITIES> within <DOCUMENT_LINES> and return ONLY the corresponding line range(s), using the inclusive format `L<start>-L<end>`.

STRICT OUTPUT FORMAT:
- For each entity i, reply using XML tags <ENTITY_i_OUTPUT>...</ENTITY_i_OUTPUT> containing one or more ranges like `L3-L7`, separated by commas if multiple (e.g., `L24-L24,L36-L37`).
- If the description spans multiple lines, include the full span. When uncertain, prefer including the following line to ensure completeness.
- If not found, leave it empty: <ENTITY_i_OUTPUT></ENTITY_i_OUTPUT>.
- Do NOT include any additional text, explanations, or verbatim document content.

Examples:
<ENTITY_1_OUTPUT>L2-L2</ENTITY_1_OUTPUT>
<ENTITY_2_OUTPUT>L3-L10,L24-L25</ENTITY_2_OUTPUT>
<ENTITY_3_OUTPUT></ENTITY_3_OUTPUT>
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

def create_entity_extraction_prompt_verbatim(document_content: str, entities_text: str) -> str:
    return ENTITY_EXTRACTION_PROMPT_TEMPLATE_VERBATIM.format(
        document_content=document_content,
        entities_text=entities_text
    )

def create_entity_extraction_prompt_line_ranges(document_content: str, entities_text: str) -> str:
    return ENTITY_EXTRACTION_PROMPT_TEMPLATE_LINE_RANGES.format(
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

def format_entities_for_extraction_verbatim(entity_batch) -> str:
    entities_text = ""
    for idx, entity in enumerate(entity_batch, 1):
        entities_text += (
            f"<ENTITY_{idx}>\n"
            f"- id: {idx}\n"
            f"- Name: {entity.name}\n"
            f"- Definition: {entity.definition}\n"
            f"- Extraction instructions: {entity.extraction_instructions}, please write the extracted data in plain text format within tags <ENTITY_{idx}_OUTPUT>\n"
            + (f"- Valid values: {', '.join(entity.valid_values)}\n" if hasattr(entity, 'valid_values') and entity.valid_values else "")
            + f"</ENTITY_{idx}>\n"
        )
    return entities_text

def format_entities_for_extraction_line_ranges(entity_batch) -> str:
    entities_text = ""
    for idx, entity in enumerate(entity_batch, 1):
        entities_text += (
            f"<ENTITY_{idx}>\n"
            f"- id: {idx}\n"
            f"- Name: {entity.name}\n"
            f"- Definition: {entity.definition}\n"
            f"- Instructions: {entity.extraction_instructions}\n"
            + (f"- Valid values: {', '.join(entity.valid_values)}\n" if hasattr(entity, 'valid_values') and entity.valid_values else "")
            + f"- Return format: output one or more ranges 'L<start>-L<end>' separated by commas in <ENTITY_{idx}_OUTPUT>. If not found, leave empty.\n"
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