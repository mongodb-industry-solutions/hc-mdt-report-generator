"""
MDT Report Iterative Processing Prompt

This module contains the prompt template for iterative MDT report generation.
The prompt guides the LLM to process documents one by one and build the report
incrementally, following the processing rules for each entity type.
"""

MDT_REPORT_ITERATIVE_SYSTEM_PROMPT = """You are a medical data extraction specialist building MDT (Multi-Disciplinary Team) reports by processing patient documents iteratively.

Your role is to:
1. Analyze extracted medical data from each document
2. Update the report structure based on entity processing rules
3. Track source document metadata for traceability
4. Maintain consistency and accuracy throughout the process

Key principles:
- Be precise and accurate with medical terminology
- Preserve all relevant information from documents
- Follow processing rules strictly for each entity type
- Maintain proper French medical terminology where applicable
"""

MDT_REPORT_ITERATIVE_PROMPT_TEMPLATE = """## Current Document ({doc_index}/{total_docs})
Filename: {filename}
Created: {created_at}
Type: {doc_type}

## Extracted Data from Current Document
{extracted_data}

## Current Report State
{current_report}

## Entity Definitions and Processing Rules

### First Match Entities (keep only the first value found):
{first_match_entities}

### Multiple Match Entities (collect all unique values):
{multiple_match_entities}

### Aggregate All Matches Entities (aggregate and summarize):
{aggregate_entities}

## Processing Instructions

1. **Analyze the extracted data** from the current document
2. **For each entity found** in the extracted data:
   - Identify the entity name and its processing type
   - Apply the appropriate processing rule:
     * **first_match**: Only add if this entity hasn't been found before
     * **multiple_match**: Add to values array if not a duplicate
     * **aggregate_all_matches**: Add to values array and update aggregated_value

3. **Track metadata** for each value:
   - filename: {filename}
   - created_at: {created_at}
   - section_id: Extract from document structure if available, otherwise "section_1"
   - page_id: Default to 1 unless specified in the document

4. **For aggregate_all_matches entities**:
   - Follow the specific aggregation_instructions from the entity definition
   - Update the aggregated_value field appropriately
   - For dates: use the oldest/first date
   - For status fields: prioritize most recent or most significant value
   - For text fields: combine information coherently

5. **Update not_found_entities**:
   - Remove entities from not_found lists when they are found
   - Ensure all defined entities are tracked

## Example Processing

If the extracted data contains:
{{"Nom": "DA SILVA", "Prénom": "José", "Métastatique": "Oui"}}

And "Nom" is a first_match entity that's already in the report, do NOT update it.
If "Prénom" is a first_match entity not yet found, ADD it.
If "Métastatique" is an aggregate_all_matches entity, ADD to values and UPDATE aggregated_value.

## Output Format

Return ONLY a valid JSON object with the updated report structure. No explanations or markdown.

{{
  "first_match": {{
    "found_entities": [
      {{
        "entity_name": "string",
        "value": "string",
        "metadata": {{
          "filename": "string",
          "created_at": "string",
          "section_id": "string",
          "page_id": number
        }}
      }}
    ],
    "not_found_entities": [
      {{"entity_name": "string"}}
    ]
  }},
  "multiple_match": {{
    "found_entities": [
      {{
        "entity_name": "string",
        "values": [
          {{
            "value": "string",
            "metadata": {{...}}
          }}
        ]
      }}
    ],
    "not_found_entities": [...]
  }},
  "aggregate_all_matches": {{
    "found_entities": [
      {{
        "entity_name": "string",
        "values": [
          {{
            "value": "string",
            "metadata": {{...}}
          }}
        ],
        "aggregated_value": "string"
      }}
    ],
    "not_found_entities": [...]
  }}
}}
"""

def create_iterative_prompt(
    document_info: dict,
    current_report: str,
    doc_index: int,
    total_docs: int,
    entities_by_type: dict
) -> str:
    """
    Create a formatted prompt for iterative MDT report processing.
    
    Args:
        document_info: Dictionary with document details (filename, created_at, type, extracted_data)
        current_report: JSON string of current report state
        doc_index: Current document index (1-based)
        total_docs: Total number of documents
        entities_by_type: Dictionary grouping entities by processing type
        
    Returns:
        Formatted prompt string
    """
    return MDT_REPORT_ITERATIVE_PROMPT_TEMPLATE.format(
        doc_index=doc_index,
        total_docs=total_docs,
        filename=document_info['filename'],
        created_at=document_info['created_at'],
        doc_type=document_info['type'],
        extracted_data=document_info['extracted_data'],
        current_report=current_report,
        first_match_entities=entities_by_type['first_match'],
        multiple_match_entities=entities_by_type['multiple_match'],
        aggregate_entities=entities_by_type['aggregate_all_matches']
    )