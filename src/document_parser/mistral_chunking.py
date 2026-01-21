#!/usr/bin/env python3  
"""  
mistral_chunking.py  
  
Intelligent Document Processing Module using Mistral AI  
  
This module provides functionality for processing OCR'd text documents using Mistral AI's   
language model to perform intelligent text chunking and classification. The system splits   
raw text into meaningful, comprehensive chunks while preserving document structure and   
automatically merging related content sections.  
  
Key Features:  
- Splits large OCR text into manageable chunks (100-500 words)  
- Preserves document structure and related content groupings  
- Automatically merges continuation content using semantic analysis  
- Extracts and categorizes document sections  
- Handles XML-formatted responses from Mistral AI  
  
Dependencies:  
- mistralai: Mistral AI Python client library  
- os: Environment variable access  
- json: JSON data handling  
  
Environment Variables Required:  
- MISTRAL_API_KEY: Your Mistral AI API key  
  
Usage:  
    >>> long_text = "Your OCR'd document text here..."  
    >>> chunks = mistral_chunk_text(long_text)  
    >>> print(f"Created {len(chunks)} intelligent chunks")  
  
Author: [Your Name]  
Created: [Date]  
Last Modified: [Date]  
Version: 1.0  
  
License: [Your License]  
"""  
  

import os
from services.base.llm import generate
import json
from services.prompts.document_chunking_prompts import SYSTEM_PROMPT, create_chunking_prompt


# Use the native inference API to send a text message to Anthropic Claude.
api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-small-2503"

# Use centralized system prompt
system_prompt = SYSTEM_PROMPT




def build_prompt(previous_chunk_xml_text, raw_text):  
    """Build chunking prompt using centralized prompt system"""
    return create_chunking_prompt(previous_chunk_xml_text, raw_text)  


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

def invoke_mistral(system_prompt, prompt):
    # Backward-compatible name; uses GPT-Open under the hood
    return generate(prompt=prompt, system=system_prompt, provider="gpt_open")




def chunk_text(text, max_chunk_size=1000, overlap=0):  
    """  
    Splits OCR'ed text into chunks with overlap.  
    """  
    if max_chunk_size <= overlap:  
        raise ValueError("max_chunk_size must be greater than overlap")  
      
    chunks = []  
    start = 0  
    text_length = len(text)  
      
    while start < text_length:  
        end = min(start + max_chunk_size, text_length)  
        chunk = text[start:end]  
        chunks.append(chunk)  
          
        # If we've reached the end of the text, break out of the loop  
        if end == text_length:  
            break  
          
        start = end - overlap  
      
    return chunks 



def mistral_chunk_text(long_ocr_text): 
    max_chunk_size = 4000  
    overlap = 0  
    
    chunks = chunk_text(long_ocr_text, max_chunk_size, overlap)  
    
    previous_chunk = {}  
    all_chunks = []  
    section_id = 0  
    
    for i, chunk in enumerate(chunks):  
        print(f"Chunk {i+1}:\n{chunk}\n{'-'*40}")  
        
        formatted_prompt = build_prompt(  
            previous_chunk_xml_text=previous_chunk if previous_chunk else "None",  
            raw_text=chunk  
        )  
        
        model_response = invoke_mistral(system_prompt, formatted_prompt)  

        # ADD DEBUG: Check if model responded  
        print(f"Model response for chunk {i+1}: {len(model_response) if model_response else 0} characters") 


        chunks_xml_string = extract_from_xml_tags(model_response, "CHUNKS")  
        

        # ADD DEBUG: Check if XML was extracted  
        if not chunks_xml_string:  
            print(f"WARNING: No XML extracted for chunk {i+1}")  
            print(f"Raw model response: {model_response}")  
            print("="*50)  
            print(f"original prompt:\n{formatted_prompt}")
            print("="*50)  
            continue  # Skip this chunk if no valid XML  

        # Convert XML to Python list/dict  
        new_chunks = []  
        last_chunk_xml = None  
        
        if chunks_xml_string:  
            chunk_start = 0  
            while True:  
                chunk_xml = extract_from_xml_tags(chunks_xml_string[chunk_start:], "CHUNK")  
                if not chunk_xml:  
                    break  
                
                last_chunk_xml = chunk_xml  
                
                # Extract individual fields  
                content = extract_from_xml_tags(chunk_xml, "CONTENT") or ""  
                category = extract_from_xml_tags(chunk_xml, "CATEGORY") or ""  
                merge = extract_from_xml_tags(chunk_xml, "MERGE") or "FALSE"  
                
                section_id += 1  
                
                chunk_dict = {  
                    'page_id': i,  
                    'content': content.strip(),  
                    'category': category.strip(),  
                    'merge': merge.strip().upper() == 'TRUE',  
                    'section_id': section_id  
                }  
                new_chunks.append(chunk_dict)  
                
                # Find next chunk position  
                chunk_start = chunks_xml_string.find("</CHUNK>", chunk_start) + len("</CHUNK>")  
                if chunk_start >= len(chunks_xml_string):  
                    break  
        
        # Handle each chunk individually  
        for new_chunk in new_chunks:  
            if new_chunk.get('merge') and all_chunks:  
                print(f"MERGE DETECTED - Concatenating with previous chunk")  
                print(f"**Previous chunk content:\n{all_chunks[-1]['content']}")  
                print(f"**New content to merge:\n{new_chunk['content']}")  
                
                # Check if previous chunk is contained at the beginning of new chunk  
                if new_chunk['content'].startswith(all_chunks[-1]['content'].strip()):  
                    all_chunks[-1]['content'] = new_chunk['content']  
                else:  
                    # Concatenate the new content with the last chunk's content  
                    all_chunks[-1]['content'] += new_chunk['content']  
                
                # Decrement section_id since we merged instead of adding new  
                section_id -= 1  
                
            else:  
                # No merge - just add the new chunk  
                all_chunks.append(new_chunk)  
                print(f"Added new chunk with section_id: {new_chunk['section_id']}")  # Debug print  
        
        # Store the last chunk's raw XML for next iteration  
        previous_chunk = last_chunk_xml  

    return all_chunks

