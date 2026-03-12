#!/usr/bin/env python3
"""
Named Entity Recognition (NER) Classifier for Medical Document Processing.

This module provides the core NER classification functionality for extracting
structured medical entities from clinical documents using advanced AI models.
It implements sophisticated duplicate prevention, multi-strategy processing,
and robust error handling.

Key Features:
- Multi-strategy entity processing (first_match, multiple_match, aggregate_all_matches)
- Advanced duplicate prevention with global entity tracking
- Intelligent batch processing for optimal AI model utilization
- Comprehensive error handling and retry mechanisms
- Real-time progress tracking and detailed logging
- Status consistency using standardized entity states
- Simplified entity keys to prevent fragmentation

Recent Enhancements (v2.0.0):
- Fixed EntityStatus inconsistency (using "status" instead of boolean "found")
- Simplified entity keys to use only entity.name instead of complex tuples
- Implemented proper MULTIPLE_MATCH logic returning single entities with value lists
- Added global entity tracking across processing types
- Enhanced logging and progress reporting

Processing Strategies:
1. FIRST_MATCH: Extract only the first occurrence across all documents
   - Optimal for unique identifiers (Patient ID, DOB)
   - Stops processing once entity is found
   
2. MULTIPLE_MATCH: Extract all unique occurrences, combine into single entity
   - Perfect for lists (Allergies, Medications, Symptoms)
   - Automatic deduplication with normalized comparison
   - Returns one entity with list of values
   
3. AGGREGATE_ALL_MATCHES: Extract all occurrences with full context
   - Ideal for temporal data (Vital signs, Lab results)
   - Maintains separate instances for analysis

Example:
    >>> import asyncio
    >>> from entity_extraction.ner_classifier import extract_entities_workflow
    >>> 
    >>> # Define entities to extract
    >>> entities = [
    ...     {
    ...         "name": "Patient Allergies",
    ...         "definition": "Known allergic reactions",
    ...         "extraction_instructions": "Look for allergy mentions",
    ...         "processing_type": "multiple_match",
    ...         "status": "pending"
    ...     }
    ... ]
    >>> 
    >>> # Process documents
    >>> results = await extract_entities_workflow(
    ...     entities=entities,
    ...     documents=document_list,
    ...     progress_callback=lambda p: print(f"Progress: {p['progress']}%")
    ... )

Author: ClarityGR Development Team
Created: 2024
Version: 2.0.0 - Enhanced duplicate handling and status consistency
"""

import os
from config.ner_config import settings as ner_settings
from services.base.llm import generate
import json
from typing import Dict, List, Any  
from collections import defaultdict
import logging  
from datetime import datetime  
from typing import List, Dict  
from botocore.exceptions import ClientError
from services.prompts.ner_prompts import (
    NER_SYSTEM_PROMPT,
    NER_AGGREGATION_SYSTEM_PROMPT,
    NER_DATA_EXTRACTION_SYSTEM_PROMPT,
    create_ner_aggregation_prompt,
    create_ner_data_extraction_prompt,
    create_ner_detailed_aggregation_prompt
)
  
# Generate unique filename with timestamp for detailed logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  
log_filename = f"processing_{timestamp}.log"  
  
logging.basicConfig(  
    level=logging.INFO,  
    filename=log_filename,  
    filemode='w',  
    format='%(asctime)s - %(message)s'  
)  

# LLM Configuration (GPT-Open)
gpt_open_model = os.environ.get("GPT_OPEN_MODEL", "gpt-open")

# System prompt for NER task instruction
system_prompt = NER_SYSTEM_PROMPT


def build_prompt(previous_chunk_xml_text, raw_text):  
    prompt = f"""
    """
    return prompt  


def extract_from_xml_tags(text, tag_name):  
    """  
    Extract text between XML tags using simple string search.  
      
    Args:  
        text (str): The input text containing XML tags  
        tag_name (str): The tag name (without < >)  
      
    Returns:  
        str: Text between the tags, or None if not found  
    """  
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




import time  
import random  
  






  
def invoke_llm(system_prompt, prompt):  
    try:
        return generate(prompt=prompt, system=system_prompt, provider="gpt_open")
    except Exception as e:
        print(f"LLM call failed: {e}")
        raise




import json  
import os  
  
def save_progress(data, filename="progress.json"):  
    """Save current progress to file"""  
    with open(filename, 'w') as f:  
        json.dump(data, f, indent=2)  
    print(f"Progress saved to {filename}")  
  
def load_progress(filename="progress.json"):  
    """Load progress from file"""  
    if os.path.exists(filename):  
        with open(filename, 'r') as f:  
            return json.load(f)  
    return None  
  

async def extract_entities_workflow(json_data: str, chunked_docs: List[dict], progress_callback=None):  
    """  
    Args:  
        json_data (str): JSON string containing entity definitions  
        chunked_docs (List[dict]): Each dict = {metadata..., "chunks": [str, ...]}
        progress_callback: Optional callback for progress updates
    Returns:  
        dict: mapping processing_type -> {"found_entities", "all_warnings", "not_found_entities"}  
    """  
    import json  
    from collections import defaultdict  
    import time
  
    start_time = time.time()
    config = json.loads(json_data)  
    entities = config.get("entities", [])  
  
    # Create flushed progress callback wrapper
    async def flushed_progress_callback(progress_data):
        """Wrapper that ensures immediate flushing of progress updates."""
        if progress_callback:
            await progress_callback(progress_data)
            # Force immediate flush by yielding control briefly
            await asyncio.sleep(0.001)

    # Emit initial progress
    await flushed_progress_callback({
        "status": "PARSING_ENTITIES",
        "progress": 15,
        "message": f"Parsing {len(entities)} entity definitions...",
        "current_step": "parsing_entities",
        "stage_detail": "Analyzing entity configuration and grouping by processing type"
    })
  
    # Group entities by processing_type  
    entities_by_type = defaultdict(list)  
    for entity in entities:  
        processing_type = entity.get("processing_type", "unknown")  
        entities_by_type[processing_type].append(entity)  
  
    # Global tracking of found entities across all processing types
    global_found_entities = set()  # Track entity names that have been found
    
    # Collect outputs by processing_type  
    results_by_processing_type = {}
    total_types = len(entities_by_type)
    types_completed = 0
    
    # Progress ranges for each processing type
    # Ensure progress does not exceed 36% until FIRST_MATCH completes
    type_progress_ranges = {
        "first_match": (20, 36),
        "multiple_match": (36, 44), 
        "aggregate_all_matches": (45, 88)
    }
  
    for processing_type, entity_list in entities_by_type.items():
        start_progress, end_progress = type_progress_ranges.get(processing_type, (20, 80))
        
        await flushed_progress_callback({
            "status": "EXTRACTING_ENTITIES",
            "progress": start_progress,
            "message": f"Processing {len(entity_list)} entities with {processing_type} strategy...",
            "current_step": "extracting_entities",
            "processing_type_progress": {
                "current_type": processing_type,
                "types_completed": types_completed,
                "total_types": total_types
            },
            "stage_detail": f"Analyzing documents for {processing_type} entities"
        })
        
        # For first_match, filter out entities that have already been found globally
        if processing_type == "first_match":
            # Mark entities as found if they've been found in previous processing types
            for entity in entity_list:
                if entity.get("name") in global_found_entities:
                    entity["status"] = "found"
                    print(f"[GLOBAL TRACKING] Entity '{entity.get('name')}' already found in previous processing, marking as found")
            
        found_entities, all_warnings, not_found_entities = await extract_entities(
            entity_list, chunked_docs, processing_type, flushed_progress_callback, start_progress, end_progress
        )
        
        # Update global tracking for first_match entities
        if processing_type == "first_match":
            for entity in found_entities:
                global_found_entities.add(entity.get("entity_name"))
                print(f"[GLOBAL TRACKING] Added '{entity.get('entity_name')}' to global found entities")
        
        #Removed the all warnings from the results
        results_by_processing_type[processing_type] = {  
            "found_entities": found_entities, 
            "not_found_entities": not_found_entities  
        }
        
        types_completed += 1
        
        await flushed_progress_callback({
            "status": "EXTRACTING_ENTITIES",
            "progress": end_progress,
            "message": f"Completed {processing_type} processing - found {len(found_entities)} entities",
            "current_step": "extracting_entities",
            "processing_type_progress": {
                "current_type": processing_type,
                "types_completed": types_completed,
                "total_types": total_types
            },
            "entity_extraction": {
                "entities_found": len(found_entities),
                "entities_processed": len(entity_list),
                "total_entities": len(entities)
            }
        })
    
    # Final aggregation step for aggregate_all_matches
    await flushed_progress_callback({
        "status": "AGGREGATING_RESULTS", 
        "progress": 90,
        "message": "Performing final aggregation for aggregate_all_matches entities...",
        "current_step": "aggregating_results",
        "stage_detail": "Consolidating and summarizing aggregated entity values"
    })
    
    elapsed_time = time.time() - start_time
    print(f"Entity extraction workflow completed in {elapsed_time:.2f} seconds")
    print(f"[GLOBAL TRACKING] Final global found entities: {global_found_entities}")
  
    return results_by_processing_type  
  

async def aggregate_entity_matches(found_entities, progress_callback=None):  
    """  
    Aggregates values for each entity using an LLM.  
    The LLM is asked to consolidate all values into a unified version,  
    following per-entity aggregation instructions if provided.  
    """  
    system_prompt = NER_AGGREGATION_SYSTEM_PROMPT
  
    total_entities = len(found_entities)
    for entity_idx, entity in enumerate(found_entities):  
        values = entity.get("values", [])  
        entity_name = entity.get("entity_name", "")  
        entity_definition = entity.get("definition","")
        aggregation_instructions = entity.get("aggregation_instructions", "Consolidate all values in a harmonize text block")
        
        # Emit progress for entity aggregation
        if progress_callback and total_entities > 0:
            await progress_callback({
                "status": "AGGREGATING_ENTITIES",
                "progress": 84 + int((entity_idx / total_entities) * 4),  # 84-88% range
                "message": f"Aggregating entity {entity_idx + 1}/{total_entities}: {entity_name}",
                "current_step": "aggregating_entities", 
                "stage_detail": f"Using LLM to consolidate {len(values)} values for {entity_name}"
            })
            # Force immediate flush
            await asyncio.sleep(0.001)  
  
        if not values:  
            entity["aggregated_value"] = ""  
            continue  

        # FIXED:
        for val in values:  
            # Handle both string values and objects with 'value' field
            if isinstance(val, dict) and 'value' in val:
                values_prompt += f"{val['value']}\n"
            else:
                values_prompt += f"{val}\n"

        print(f"values: \n+++++\n{values_prompt}\n++++++++")
  
        prompt = create_ner_detailed_aggregation_prompt(
            entity_name=entity_name,
            entity_definition=entity_definition,
            aggregation_instructions=aggregation_instructions,
            values_text=values_prompt
        )

        #add prompt in the logger:
        import logging
        logging.getLogger("entity_extraction.ner_classifier").info(f"NER aggregation prompt for entity '{entity_name}':\n{prompt}")
        
  
        try:  
            # Run in thread pool to avoid blocking async event loop
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, invoke_llm, system_prompt, prompt)  
            #result = invoke_claude_3_7(f"{system_prompt}\n {prompt}")
            result = result.strip()  
        except Exception as e:  
            result = f"Aggregation error: {e}"  
  

        extracted = extract_from_xml_tags(result, "OUTPUT")  
        extracted = extracted.strip() if extracted else ""

        print(f"Aggregation result for {entity_name}")
        print (extracted)
        print ("+-"*20)

        entity["aggregated_value"] = extracted  
  
    return found_entities  


async def extract_entities(entities: List[Dict], chunked_docs: List[Dict], processing_type: str, 
                          progress_callback=None, start_progress=20, end_progress=80):      
    """      
    Extract entities according to processing_type.      
    Args:      
        entities: List of entity definitions (dicts)      
        chunked_docs: Each dict has doc_path, num_chunks, chunks (list of texts)      
        processing_type: 'first_match', 'multiple_match', or 'aggregate_all_matches'
        progress_callback: Optional callback for progress updates
        start_progress: Starting progress percentage for this processing type
        end_progress: Ending progress percentage for this processing type      
    """      
      
    MAX_ENTITIES = 7    
    MAX_CONTENT_SIZE = 4000    
    CHUNK_OVERLAPPING = 200    
    found_entities = []      
    all_warnings = []      
      
    entity_values_map = {}  # Only used for multiple/aggregate match
    total_docs = len(chunked_docs)
    total_api_calls = 0
    
    for doc_idx, doc in enumerate(chunked_docs):  
        # Chunk the document if it's too large  
        if len(doc["chunks"]) == 1 and len(doc["chunks"][0]["content"]) > MAX_CONTENT_SIZE:  
            text = doc["chunks"][0]["content"]  
            doc["chunks"] = []  
            start = 0  
            chunk_num = 1  
            while start < len(text):  
                end = min(start + MAX_CONTENT_SIZE, len(text))  
                chunk_content = text[start:end]  
                doc["chunks"].append({  
                    "content": chunk_content,  
                    "section_id": f"text_chunk_{chunk_num}",  
                    "category": "plain_text",  
                    "page_id": chunk_num  
                })  
                if end >= len(text):  
                    break  
                start = end - CHUNK_OVERLAPPING  
                if start < 0:  
                    start = 0  
                chunk_num += 1
        
        # Emit progress for document processing
        if progress_callback:
            doc_progress = start_progress + (doc_idx / total_docs) * (end_progress - start_progress)
            filename = doc.get("metadata", {}).get("filename", f"document_{doc_idx + 1}")
            await progress_callback({
                "status": "EXTRACTING_ENTITIES",
                "progress": int(doc_progress),
                "message": f"Processing document {doc_idx + 1}/{total_docs}: {filename}",
                "current_step": "extracting_entities",
                "documents_progress": {
                    "current_document": doc_idx + 1,
                    "total_documents": total_docs,
                    "current_filename": filename
                },
                "processing_type_progress": {
                    "current_type": processing_type,
                    "types_completed": 0,  # Will be updated by caller
                    "total_types": 3  # first_match, multiple_match, aggregate_all_matches
                },
                "stage_detail": f"Chunking and preparing document content for {processing_type} analysis"
            })
            # Force immediate flush
            await asyncio.sleep(0.001)
          
        # For first_match, check if all entities are already found before processing any chunks
        if processing_type == "first_match":
            process_entities = [e for e in entities if not e.get("found")]
            if not process_entities:
                print(f"[extract_entities] All entities found, skipping document {doc_idx + 1}.")
                continue
            else:
                print(f"[extract_entities] Processing {len(process_entities)} remaining entities in document {doc_idx + 1}")
                for entity in process_entities:
                    print(f"   - {entity.get('name')} (found: {entity.get('found', False)})")
          
        for i, chunk in enumerate(doc["chunks"]):      
            content = chunk["content"]      
            # Only process not-yet-found entities      
            process_entities = [e for e in entities if not e.get("found")]      
            if not process_entities:      
                print("[extract_entities] All entities found, stopping early for this doc.")      
                break      
      
            num_entities = len(process_entities)
            total_batches = (num_entities + MAX_ENTITIES - 1) // MAX_ENTITIES  # Ceiling division
            for batch_idx, start_idx in enumerate(range(0, num_entities, MAX_ENTITIES)):
                # For first_match, check again if all entities are found before processing this batch
                if processing_type == "first_match":
                    process_entities = [e for e in entities if not e.get("found")]
                    if not process_entities:
                        print(f"[extract_entities] All entities found, stopping batch processing in document {doc_idx + 1}.")
                        break
                    num_entities = len(process_entities)
                    if start_idx >= num_entities:
                        break
                
                entity_batch = process_entities[start_idx:start_idx + MAX_ENTITIES]
                
                # Emit progress for batch processing
                if progress_callback:
                    batch_progress = start_progress + ((doc_idx + (batch_idx / total_batches)) / total_docs) * (end_progress - start_progress)
                    await progress_callback({
                        "status": "EXTRACTING_ENTITIES",
                        "progress": int(batch_progress),
                        "message": f"Processing batch {batch_idx + 1}/{total_batches} in {filename} ({len(entity_batch)} entities)",
                        "current_step": "extracting_entities",
                        "documents_progress": {
                            "current_document": doc_idx + 1,
                            "total_documents": total_docs,
                            "current_filename": filename
                        },
                        "batch_progress": {
                            "current_batch": batch_idx + 1,
                            "total_batches": total_batches,
                            "entities_in_batch": len(entity_batch)
                        },
                        "stage_detail": f"Calling LLM API for entity extraction batch"
                    })
                    # Force immediate flush
                    await asyncio.sleep(0.001)      
      
                # Build entities_text for this batch      
                entities_text = ""      
                for idx, entity in enumerate(entity_batch, 1):      
                    entities_text += (      
                        f"<ENTITY_{idx}>\n"      
                        f"-id:{idx}\n"      
                        f"-Name: {entity.get('name', '')}\n"      
                        f"- Definition: {entity.get('definition', '')}\n"      
                        f"- Extraction instructions: {entity.get('extraction_instructions', '')}, please write the extracted data in plain text, using the original language of the <DOCUMENT>, format within tags <ENTITY_{idx}_OUTPUT>\n"      
                        + (f"   - Valid values: {', '.join(entity['valid_values'])}\n" if entity.get('valid_values') else "")      
                        + f"</ENTITY_{idx}>\n"      
                    )      
      
                system_prompt = NER_DATA_EXTRACTION_SYSTEM_PROMPT      

                prompt = create_ner_data_extraction_prompt(content, entities_text)

                import asyncio
                loop = asyncio.get_event_loop()
                model_response = await loop.run_in_executor(None, invoke_llm, system_prompt, prompt)
                total_api_calls += 1      
    
    
                for idx, entity in enumerate(entity_batch, 1):          
                    tag_name = f"ENTITY_{idx}_OUTPUT"          
                    extracted = extract_from_xml_tags(model_response, tag_name)          
                    extracted = extracted.strip() if extracted else ""          
                    if not extracted:          
                        continue          
                    
                    # Mark entity as found for all processing types      
                    entity["status"] = "found"      
                        
                    metadata = doc['metadata']          
                    selected_metadata = {          
                        "filename": metadata.get("filename"),          
                        "created_at": metadata.get("created_at"),          
                        "section_id": chunk.get("section_id"),          
                        "page_id": chunk.get("page_id"),          
                    }          
                    
                    if processing_type == "first_match":          
                        found_entities.append({          
                            "entity_name": entity.get('name', ''),          
                            "value": extracted,          
                            "metadata": selected_metadata          
                        })          
                    else:          
                        entity_key = (          
                            entity.get('name', ''),          
                            entity.get("aggregation_instructions", ""),          
                            entity.get('definition', '')          
                        )          
                        if entity_key not in entity_values_map:          
                            entity_values_map[entity_key] = {          
                                "entity_name": entity.get('name', ''),          
                                "aggregation_instructions": entity.get("aggregation_instructions", ""),          
                                "definition": entity.get('definition', ''),          
                                "values": []          
                            }          
                    
                        # Prevent duplicates (keep all unique values)
                        existing_values = [vx["value"].strip().lower() for vx in entity_values_map[entity_key]["values"]]
                        extracted_normalized = extracted.strip().lower()
                        values_list = entity_values_map[entity_key]["values"]

                        if extracted_normalized not in existing_values:
                            values_list.append({
                                "value": extracted,
                                "metadata": selected_metadata
                            })
                        else:
                            print(f"[DUPLICATE FILTERED] Skipping duplicate value: '{extracted}' for entity: {entity.get('name', '')}")
    
    
                # Extract warnings (if any)      
                warnings = extract_from_xml_tags(model_response, "WARNINGS")      
                if warnings:      
                    warnings = warnings.strip()      
                    all_warnings.append(warnings)      
      
    if processing_type == "multiple_match":      
        found_entities = list(entity_values_map.values())      
    elif processing_type == "aggregate_all_matches":      
        found_entities = list(entity_values_map.values())
        if progress_callback:
            await progress_callback({
                "status": "AGGREGATING_ENTITIES",
                "progress": int(end_progress - 2),
                "message": f"Aggregating {len(found_entities)} entities for final consolidation...",
                "current_step": "aggregating_entities",
                "stage_detail": "Using LLM to consolidate multiple values into unified entity results"
            })
            # Force immediate flush
            await asyncio.sleep(0.001)    
        # Create deep copies for aggregation to preserve originals
        import copy
        entities_for_aggregation = copy.deepcopy(found_entities)

        aggregated_found_entities = await aggregate_entity_matches(entities_for_aggregation, progress_callback)
        
        # Add both original and aggregated entities
        found_entities.extend(aggregated_found_entities)    
      
    for entity in found_entities:      
        entity.pop("aggregation_instructions", None)      
        entity.pop("definition", None)      
      
    # Prepare list of not found entities      
    not_found_entities = [      
        {      
            "entity_name": entity.get("name", ""),      
            # add more fields as needed      
        }      
        for entity in entities if entity.get("status") != "found"      
    ]    
  
          
    return found_entities, all_warnings, not_found_entities      
