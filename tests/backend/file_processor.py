import streamlit as st  
import os  
import tempfile  
import sys  
from typing import List, Dict, Any  
from pathlib import Path  
import time  
import asyncio  
import pickle  
import json  
import traceback  
from universal_document_parser import UniversalDocumentParser  
from ner_classifier import extract_entities_workflow, chunk_document_by_size  
from json_to_html import parse_json_to_html  
from ui_helpers import generate_error_html
from ui_helpers import display_results
from session_manager import (  
    save_session_to_disk
)  


async def process_files_async(files_data):      
    """Process the files asynchronously with enhanced error handling"""      
          
    # Create temporary directory to store files      
    with tempfile.TemporaryDirectory() as temp_dir:      
        st.subheader("⚙️ Processing Files...")      
              
        # Progress tracking      
        progress_bar = st.progress(0)      
        status_text = st.empty()      
        log_container = st.container()      
              
        # Save files to temporary directory      
        file_paths = []      
              
        # Handle both uploaded files and cached files      
        if files_data and isinstance(files_data[0], dict):      
            # Cached files      
            uploaded_files = files_data      
            total_steps = (len(uploaded_files) + 1 + len(uploaded_files) + 1 + 6 + 1) * 2      
        else:      
            # Fresh uploaded files      
            uploaded_files = files_data      
            total_steps = (len(uploaded_files) + 1 + len(uploaded_files) + 1 + 6 + 1) * 2      
              
        current_step = 0      
              
        with log_container:      
            st.markdown("**📝 Processing Log:**")      
            log_placeholder = st.empty()      
            logs = []      
              
        def update_progress(message: str, increment: bool = True):      
            nonlocal current_step      
            if increment:      
                current_step += 1      
            progress = min(current_step / total_steps, 1.0)      
            progress_bar.progress(progress)      
            status_text.text(message)      
            log_msg = f"[{time.strftime('%H:%M:%S')}] {message}"      
            logs.append(log_msg)      
            st.session_state.processing_logs.append(log_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            time.sleep(0.1)      
              
        def update_progress_no_increment(message: str):      
            progress = min(current_step / total_steps, 1.0)      
            progress_bar.progress(progress)      
            status_text.text(message)      
            log_msg = f"[{time.strftime('%H:%M:%S')}] {message}"      
            logs.append(log_msg)      
            st.session_state.processing_logs.append(log_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            time.sleep(0.1)      
              
        try:      
            # Step 1: Save files      
            update_progress("📁 Saving files...")      
            for file_data in uploaded_files:      
                if isinstance(file_data, dict):      
                    # Cached file      
                    file_path = os.path.join(temp_dir, file_data['name'])      
                    with open(file_path, "wb") as f:      
                        f.write(file_data['content'])      
                    file_paths.append(file_path)      
                    update_progress(f"✅ Saved: {file_data['name']}")      
                else:      
                    # Fresh uploaded file      
                    file_path = os.path.join(temp_dir, file_data.name)      
                    with open(file_path, "wb") as f:      
                        f.write(file_data.getbuffer())      
                    file_paths.append(file_path)      
                    update_progress(f"✅ Saved: {file_data.name}")      
                  
            # Step 2: Initialize parser      
            update_progress("🔄 Initializing UniversalDocumentParser...")      
                  
            parser = UniversalDocumentParser()      
            parsing_results = []      
            successful_parses = 0      
            total_chars = 0      
            total_words = 0      
                  
            # Step 3: Parse files      
            for file_path in file_paths:      
                filename = os.path.basename(file_path)      
                file_size = os.path.getsize(file_path) / 1024      
                      
                update_progress(f"📄 Parsing: {filename} ({file_size:.1f} KB)")      
                      
                try:      
                    # Get bypass setting from session state or default to True      
                    bypass_formatting = st.session_state.get('bypass_formatting', True)      
                    result = await parser.parse_document(str(file_path), bypass_formatting=bypass_formatting)      
                          
                    if result["status"] == "success":      
                        plain_text = result["result"]["plain_text"]      
                        word_count = len(plain_text.split())      
                        char_count = len(plain_text)      
                          
                        # Handle both string and list for document_elements safely  
                        try:  
                            document_elements = result["result"]["parsed_document"]["document_elements"]  
                            if isinstance(document_elements, str):  
                                # Plain text bypass mode - count as 1 element  
                                elements = 1  
                            elif isinstance(document_elements, list):  
                                # Structured document mode  
                                elements = len(document_elements)  
                            else:  
                                # Fallback for other types  
                                elements = 0  
                        except (KeyError, TypeError):  
                            # Fallback if structure is unexpected  
                            elements = 0  
                              
                        parsing_results.append({      
                            "filename": filename,      
                            "file_path": file_path,      
                            "result": result,      
                            "stats": {      
                                "chars": char_count,      
                                "words": word_count,      
                                "elements": elements      
                            }      
                        })      
                              
                        successful_parses += 1      
                        total_chars += char_count      
                        total_words += word_count      
                              
                        update_progress_no_increment(f"✅ Parsed {filename}: {char_count:,} chars, {word_count:,} words, {elements} elements")      
                    else:      
                        # Handle parsing errors  
                        error_info = result.get("result", {})  
                        if isinstance(error_info, dict):  
                            error_msg = error_info.get("errors", ["Unknown error"])  
                            if isinstance(error_msg, list):  
                                error_msg = "; ".join(error_msg)  
                        else:  
                            error_msg = result.get("error", "Unknown error")  
                              
                        log_msg = f"❌ Failed to parse {filename}: {error_msg}"  
                        logs.append(log_msg)      
                        st.session_state.processing_logs.append(log_msg)      
                        log_placeholder.text("\n".join(logs[-10:]))      
                              
                        parsing_results.append({      
                            "filename": filename,      
                            "file_path": file_path,      
                            "result": result,      
                            "stats": None      
                        })      
                              
                except Exception as e:      
                    error_msg = f"❌ Error parsing {filename}: {str(e)}"      
                    logs.append(error_msg)      
                    st.session_state.processing_logs.append(error_msg)      
                    log_placeholder.text("\n".join(logs[-10:]))      
                      
                    # Add full traceback for debugging  
                    traceback_msg = f"Full traceback for {filename}: {traceback.format_exc()}"  
                    logs.append(traceback_msg)  
                    st.session_state.processing_logs.append(traceback_msg)  
                          
                    parsing_results.append({      
                        "filename": filename,      
                        "file_path": file_path,      
                        "result": {"status": "error", "error": str(e)},      
                        "stats": None      
                    })      
                  
            # Display parsing summary      
            update_progress(f"📊 Parsing complete: {successful_parses}/{len(file_paths)} files successful")      
            logs.append(f"📈 Total: {total_chars:,} characters, {total_words:,} words")      
            st.session_state.processing_logs.append(f"📈 Total: {total_chars:,} characters, {total_words:,} words")      
            log_placeholder.text("\n".join(logs[-10:]))      
                  
        except Exception as e:      
            error_msg = f"❌ Error initializing parser: {str(e)}"      
            st.error(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
              
            # Add full traceback for debugging  
            traceback_msg = f"Full initialization traceback: {traceback.format_exc()}"  
            logs.append(traceback_msg)  
            st.session_state.processing_logs.append(traceback_msg)  
            log_placeholder.text("\n".join(logs[-10:]))  
              
            save_session_to_disk()  # Save state even on error      
            return      
              
        # Step 4: Process with second component      
        try:      
            def second_component_progress_callback(message: str):      
                nonlocal current_step      
                current_step += 1      
                progress = min(current_step / total_steps, 1.0)      
                progress_bar.progress(progress)      
                status_text.text(message)      
                log_msg = f"[{time.strftime('%H:%M:%S')}] {message}"      
                logs.append(log_msg)      
                st.session_state.processing_logs.append(log_msg)      
                log_placeholder.text("\n".join(logs[-10:]))      
                time.sleep(0.1)      
                  
            html_result = await process_with_second_component(      
                parsing_results,      
                second_component_progress_callback,      
                logs,      
                log_placeholder      
            )      
                  
        except Exception as e:      
            error_msg = f"❌ Error in second component: {str(e)}"      
            st.error(error_msg)      
            logs.append(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
              
            # Add full traceback for debugging  
            traceback_msg = f"Full second component traceback: {traceback.format_exc()}"  
            logs.append(traceback_msg)  
            st.session_state.processing_logs.append(traceback_msg)  
            log_placeholder.text("\n".join(logs[-10:]))      
              
            save_session_to_disk()  # Save state even on error      
            return      
              
        # Step 5: Complete and save results      
        progress_bar.progress(1.0)      
        status_text.text("✅ All processing completed!")      
        final_msg = "🎉 All done!"      
        logs.append(final_msg)      
        st.session_state.processing_logs.append(final_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        # Store results in session state      
        st.session_state.processing_results = parsing_results      
        st.session_state.html_result = html_result      
        st.session_state.processing_stats = {      
            'successful_parses': successful_parses,      
            'total_chars': total_chars,      
            'total_words': total_words      
        }      
        st.session_state.processing_complete = True      
              
        # Save to disk for persistence      
        save_session_to_disk()      
              
        # Display results      
        display_results(parsing_results, html_result, successful_parses, total_chars, total_words, st.session_state.extraction_result)      



async def process_with_second_component(parsing_results: List[Dict[str, Any]],       
                                      update_progress_callback,       
                                      logs: List[str],       
                                      log_placeholder) -> str:      
    """      
    Process parsed documents with entity extraction workflow with progress tracking      
          
    Args:      
        parsing_results: List of parsing results from UniversalDocumentParser      
        update_progress_callback: Function to call for progress updates      
        logs: List to append log messages to      
        log_placeholder: Streamlit placeholder for updating logs      
              
    Returns:      
        str: Raw HTML document to be rendered      
    """      
          
    try:      
        update_progress_callback("🔍 Executing entity extraction workflow (can take several minutes)...")      
              
        # Step 1: Load entity definitions      
        update_progress_callback("📋 Loading entity definitions...")      
        entity_definitions_path = "ner_classifier/gr_entities_definition.json"      
              
        try:      
            with open(entity_definitions_path, "r", encoding="utf-8") as f:      
                json_data = f.read()      
                      
            success_msg = f"✅ Entity definitions loaded from: {entity_definitions_path}"      
            logs.append(success_msg)      
            st.session_state.processing_logs.append(success_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
                      
        except FileNotFoundError:      
            error_msg = f"❌ Entity definitions file not found: {entity_definitions_path}"      
            logs.append(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            return generate_error_html(f"Entity definitions file not found: {entity_definitions_path}")      
              
        # Step 2: Process parsing results          
        update_progress_callback("🔄 Processing parsed documents...")          
        chunked_docs = []          
        successful_docs = 0          
        total_chunks = 0          
                    
        for i, result in enumerate(parsing_results):          
            if result["result"]["status"] == "success":          
                try:          
                    progress_msg = f"📄 Processing document {i+1}/{len(parsing_results)}: {result['filename']}"          
                    logs.append(progress_msg)          
                    st.session_state.processing_logs.append(progress_msg)          
                    log_placeholder.text("\n".join(logs[-10:]))          
                            
                    # Extract the parsed document from UniversalDocumentParser result          
                    try:  
                        parsed_result = result["result"]["result"]["parsed_document"]  
                        logs.append(f"Debug: parsed_result type: {type(parsed_result)}")  
                          
                        # Handle different result structures  
                        if isinstance(parsed_result, dict):  
                            # Check if it has the expected structure  
                            if "document_elements" in parsed_result:  
                                document_json = parsed_result  
                            else:  
                                # Create structure if missing  
                                document_json = {  
                                    "metadata": parsed_result.get("metadata", {}),  
                                    "document_elements": parsed_result  
                                }  
                        elif isinstance(parsed_result, str):  
                            # Plain text case - create minimal structure  
                            document_json = {  
                                "metadata": {},  
                                "document_elements": parsed_result  
                            }  
                        else:  
                            # Fallback - try to use plain_text from result  
                            plain_text = result["result"]["plain_text"]  
                            document_json = {  
                                "metadata": {},  
                                "document_elements": plain_text  
                            }  
                            logs.append(f"Debug: Used fallback plain_text approach")  
                              
                    except Exception as extract_error:  
                        # Ultimate fallback - use plain_text  
                        logs.append(f"Debug: Exception in extraction: {str(extract_error)}")  
                        plain_text = result["result"]["plain_text"]  
                        document_json = {  
                            "metadata": {},  
                            "document_elements": plain_text  
                        }  
                        logs.append(f"Debug: Used ultimate fallback with plain_text")  
                            
                    # Add metadata          
                    metadata = {          
                        "filename": result["filename"],          
                        "source": "streamlit_upload",          
                        "processed_at": time.strftime('%Y-%m-%d %H:%M:%S')          
                    }          
                            
                    # Safely add metadata to document_json  
                    if isinstance(document_json, dict):  
                        # Merge metadata safely  
                        if "metadata" not in document_json:  
                            document_json["metadata"] = {}  
                        document_json["metadata"].update(metadata)  
                    else:  
                        # If document_json is not a dict, create the structure  
                        document_json = {  
                            "metadata": metadata,  
                            "document_elements": document_json  
                        }  
                        logs.append(f"Debug: Restructured document_json to dict")  
                            
                    # Debug logging  
                    logs.append(f"Debug: Final document_json type: {type(document_json)}")  
                    if isinstance(document_json, dict):  
                        logs.append(f"Debug: document_json keys: {list(document_json.keys())}")  
                        doc_elements = document_json.get("document_elements", "N/A")  
                        logs.append(f"Debug: document_elements type: {type(doc_elements)}")  
                      
                    # Chunk the document          
                    overlap_chars = st.session_state.get('overlap_chars', 200)      
                    logs.append(f"Debug: About to chunk with overlap_chars={overlap_chars}")  
                      
                    chunks = chunk_document_by_size(document_json, max_chars=9000, overlap_chars=overlap_chars)          
                    logs.append(f"Debug: Chunking completed, got {len(chunks)} chunks")  
                            
                    chunked_docs.append({          
                        "doc_path": result["filename"],          
                        "num_chunks": len(chunks),          
                        "chunks": chunks,          
                        "metadata": metadata          
                    })          
                            
                    successful_docs += 1          
                    total_chunks += len(chunks)          
                            
                    success_msg = f"✅ Processed {result['filename']}: {len(chunks)} chunks created"          
                    logs.append(success_msg)          
                    st.session_state.processing_logs.append(success_msg)          
                    log_placeholder.text("\n".join(logs[-10:]))          
                            
                except Exception as doc_error:          
                    error_msg = f"❌ Error processing {result['filename']}: {str(doc_error)}"          
                    logs.append(error_msg)          
                    st.session_state.processing_logs.append(error_msg)  
                      
                    # Add full traceback for debugging  
                    traceback_msg = f"Full traceback: {traceback.format_exc()}"  
                    logs.append(traceback_msg)  
                    st.session_state.processing_logs.append(traceback_msg)  
                      
                    log_placeholder.text("\n".join(logs[-10:]))          
                    continue          
            else:          
                skip_msg = f"⚠️ Skipping failed document: {result['filename']}"          
                logs.append(skip_msg)          
                st.session_state.processing_logs.append(skip_msg)          
                log_placeholder.text("\n".join(logs[-10:]))          
    
                    
        # Validate we have documents to process      
        if not chunked_docs:      
            error_msg = "❌ No documents were successfully processed for entity extraction"      
            logs.append(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            return generate_error_html("No documents were successfully processed for entity extraction.")      
              
        # Step 3: Log processing summary      
        summary_msg = f"📊 Processing summary: {successful_docs} documents, {total_chunks} total chunks"      
        update_progress_callback(summary_msg)      
        logs.append(summary_msg)      
        st.session_state.processing_logs.append(summary_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        # Step 4: Run entity extraction workflow      
        update_progress_callback("🧠 Running entity extraction workflow...")      
        workflow_msg = "🔄 Executing entity extraction workflow... (this may take several minutes)"      
        logs.append(workflow_msg)      
        st.session_state.processing_logs.append(workflow_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        try:      
            # Add a small delay to show progress      
            await asyncio.sleep(0.1)      
                  
            extraction_result = extract_entities_workflow(json_data, chunked_docs)      
                  
            # Log extraction results summary      
            if isinstance(extraction_result, dict):      
                entity_count = 0      
                for section_name, section_data in extraction_result.items():      
                    if isinstance(section_data, dict) and 'found_entities' in section_data:      
                        entity_count += len(section_data['found_entities'])      
                      
                success_msg = f"✅ Entity extraction completed: {entity_count} entities found across {len(extraction_result)} sections"      
                logs.append(success_msg)      
                st.session_state.processing_logs.append(success_msg)      
                log_placeholder.text("\n".join(logs[-10:]))      
                update_progress_callback("✅ Entity extraction workflow completed!")      
            else:      
                success_msg = "✅ Entity extraction workflow completed"      
                logs.append(success_msg)      
                st.session_state.processing_logs.append(success_msg)      
                log_placeholder.text("\n".join(logs[-10:]))      
                update_progress_callback(success_msg)      
                      
        except Exception as workflow_error:      
            error_msg = f"❌ Entity extraction workflow failed: {str(workflow_error)}"      
            logs.append(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            return generate_error_html(f"Entity extraction workflow failed: {str(workflow_error)}")      
              
        # Step 5: Generate HTML report      
        update_progress_callback("📄 Generating HTML report...")      
        html_msg = "🔄 Generating HTML report..."      
        logs.append(html_msg)      
        st.session_state.processing_logs.append(html_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        try:      
            html_content = parse_json_to_html(extraction_result)    
            st.session_state.extraction_result = extraction_result    
                  
            # Calculate HTML stats      
            html_size_kb = len(html_content) / 1024      
            success_msg = f"✅ HTML report generated: {html_size_kb:.1f} KB"      
            logs.append(success_msg)      
            st.session_state.processing_logs.append(success_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            update_progress_callback("✅ HTML report generation completed!")      
                  
            return html_content      
                  
        except Exception as html_error:      
            error_msg = f"❌ HTML generation failed: {str(html_error)}"      
            logs.append(error_msg)      
            st.session_state.processing_logs.append(error_msg)      
            log_placeholder.text("\n".join(logs[-10:]))      
            return generate_error_html(f"HTML generation failed: {str(html_error)}")      
                  
    except Exception as e:      
        error_msg = f"❌ Unexpected error in entity extraction workflow: {str(e)}"      
        logs.append(error_msg)      
        st.session_state.processing_logs.append(error_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        # Log the full traceback for debugging      
        traceback_msg = f"Full traceback: {traceback.format_exc()}"      
        logs.append(traceback_msg)      
        st.session_state.processing_logs.append(traceback_msg)      
        log_placeholder.text("\n".join(logs[-10:]))      
              
        return generate_error_html(f"Unexpected error in entity extraction workflow: {str(e)}")      
