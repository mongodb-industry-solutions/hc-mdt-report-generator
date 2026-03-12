## 🛠️ **Updated NERWorkflowOrchestrator**

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional

from domain.entities.ner_models import EntityDefinition, ProcessingType
from services.entity_extraction_service import EntityExtractionService
from services.document_processor import DocumentProcessor
from utils.progress_tracker import ProgressTracker
from config.ner_config import settings, update_ner_settings

logger = logging.getLogger(__name__)

class NERWorkflowOrchestrator:

    
    def __init__(self):
        self.document_processor = None
        self.progress_tracker = ProgressTracker()
        
    async def extract_entities_workflow(
        self, 
        json_data: str, 
        chunked_docs: List[Dict],
        session_id: str = None,
        progress_callback: Optional[callable] = None,
        reasoning_effort: Optional[str] = "high",
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        
        start_time = time.time()

        logger.info("⏰ NO TIMEOUT LIMITS - This process will run as long as needed!")
        
        try:
            # Step 1: Parse configuration
            logger.info("📝 Step 1: Parsing entity configuration...")
            config = json.loads(json_data)
            entity_definitions = self._parse_entity_definitions(config.get("entities", []))
            logger.info(f"✅ Parsed {len(entity_definitions)} entity definitions")
            
            # Initialize document processor with custom NER config if available
            if ner_config:
                logger.info(f"Using custom NER config: {ner_config}")
                # Update global settings
                update_ner_settings(ner_config)
                # Initialize with the new settings
                self.document_processor = DocumentProcessor(
                    max_content_size=ner_config.get("max_content_size"),
                    chunk_overlapping=ner_config.get("chunk_overlapping")
                )
            else:
                logger.info("Using default NER config from settings")
                self.document_processor = DocumentProcessor()
            
            # Step 2: Process documents
            logger.info("📄 Step 2: Processing documents...")
            documents = self.document_processor.process_documents(chunked_docs)
            logger.info(f"✅ Processed {len(documents)} documents")
            
            # Step 3: Start progress tracking (with fallback)
            logger.info("📊 Step 3: Starting progress tracking...")
            await self._safe_start_tracking(
                total_documents=len(documents),
                total_entities=len(entity_definitions),
                session_id=session_id
            )
            logger.info("✅ Progress tracking started")
            
            # Step 4: Initialize clients - NO TIMEOUT!
            logger.info("🔌 Step 4: Initializing LLM client for long-running extraction (Bedrock primary)...")
            
            # Step 5: Create extraction service
            logger.info("🔧 Step 5: Creating extraction service...")
            # Enforce fail-fast globally in settings to avoid silent partials
            try:
                update_ner_settings({"continue_on_batch_errors": False})
            except Exception:
                pass
            extraction_service = EntityExtractionService(
                document_processor=self.document_processor,
                progress_tracker=self.progress_tracker
            )
            # Do not force global high; default to None so extraction uses low by default
            try:
                extraction_service.reasoning_effort = (reasoning_effort or None)
            except Exception:
                extraction_service.reasoning_effort = None
            
            # Enforce fail-fast: do not allow partial results
            if hasattr(extraction_service, 'continue_on_errors'):
                extraction_service.continue_on_errors = False
            
            logger.info("✅ NER extraction service created")
            
            # Step 6: Execute extraction - NO TIMEOUT!
            logger.info("🔍 Step 6: Starting INFINITE PATIENCE entity extraction...")
            logger.info("⏰ This step can take HOURS - no timeout limits applied!")
            
            # Extract structured_data (filtered_json) from chunked_docs for source filtering
            structured_data = self._extract_structured_data(chunked_docs)
            if structured_data:
                logger.info(f"📋 Found structured data with {len(structured_data.get('lCrs', []))} lCrs entries for source filtering")
            
            # THE MAIN EXTRACTION - NO asyncio.wait_for() timeout!
            result = await self._extract_with_infinite_resilience(
                extraction_service, documents, entity_definitions, progress_callback, ner_config, structured_data
            )
            
            logger.info("✅ Ultra-patient entity extraction completed")


            logger.info(f"🔍 DEBUG: Result type: {type(result)}")  
            logger.info(f"🔍 DEBUG: Result attributes: {dir(result) if hasattr(result, '__dict__') else 'No attributes'}")  
            if hasattr(result, 'found_entities'):  
                logger.info(f"🔍 DEBUG: Found entities count: {len(result.found_entities)}")  
                if result.found_entities:  
                    logger.info(f"🔍 DEBUG: First entity type: {type(result.found_entities[0])}")  
                    logger.info(f"🔍 DEBUG: First entity: {result.found_entities[0]}")  

            
            # Step 7: Format results
            logger.info("📋 Step 7: Formatting results...")
            formatted_results = self._format_results_by_processing_type(result)
            
            elapsed = time.time() - start_time
            logger.info(f"🎉 NER workflow completed successfully in {elapsed:.2f} seconds")
            return formatted_results
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"NER workflow failed after {elapsed:.2f} seconds: {e}")
            
            # Return partial results instead of complete failure
            return {
                "error_recovery": {
                    "found_entities": [],
                    "not_found_entities": [],
                    "error": str(e),
                    "duration": elapsed,
                    "status": "failed_with_grace"
                }
            }

    async def _extract_with_infinite_resilience(
        self,
        extraction_service: EntityExtractionService,
        documents: List,
        entity_definitions: List[EntityDefinition],
        progress_callback: Optional[callable] = None,
        ner_config: Optional[Dict[str, Any]] = None,
        structured_data: Optional[Dict[str, Any]] = None
    ):

        
        consecutive_failures = 0
        max_consecutive_failures = 10
        base_backoff = 30  # 30 seconds base backoff
        max_backoff = 300  # 5 minutes max backoff
        
        while True:  # INFINITE RETRY LOOP
            try:
                logger.info(f"🎯 Extraction attempt (consecutive failures: {consecutive_failures})")
                
                if consecutive_failures > 0:
                    logger.info(f"🔄 Recovering from {consecutive_failures} consecutive failures...")
                
                # THE ACTUAL EXTRACTION - NO TIMEOUT
                result = await extraction_service.extract_entities_from_documents(
                    documents=documents,
                    entities=entity_definitions,
                    progress_callback=progress_callback,
                    ner_config=ner_config,
                    structured_data=structured_data
                )
                
                # SUCCESS! Reset failure counter
                consecutive_failures = 0
                logger.info("✅ Extraction completed successfully with infinite resilience!")
                return result
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"❌ Extraction attempt failed ({consecutive_failures} consecutive): {e}")

                # Abort immediately on fatal client/config errors (e.g., 4xx except 429 or missing API key / model)
                try:
                    if self._is_fatal_error(e):
                        logger.critical("💥 Fatal error detected (non-retryable). Aborting extraction without retry.")
                        raise
                except Exception:
                    # If helper raises or cannot determine, continue normal flow
                    pass
                
                # Calculate backoff time
                backoff_time = min(base_backoff * (2 ** min(consecutive_failures - 1, 5)), max_backoff)
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"💥 Too many consecutive failures ({consecutive_failures}), giving up")
                    raise Exception(f"Extraction failed after {consecutive_failures} consecutive attempts: {str(e)}")
                
                logger.warning(f"⏳ Backing off for {backoff_time} seconds before retry...")
                logger.info(f"🔄 Will retry extraction (attempt {consecutive_failures + 1})")
                
                # Patient waiting with progress update
                for i in range(backoff_time):
                    if i % 30 == 0:  # Log every 30 seconds during backoff
                        remaining = backoff_time - i
                        logger.info(f"⏳ Backoff in progress... {remaining} seconds remaining")
                    await asyncio.sleep(1)
                
                logger.info("🔄 Backoff complete, retrying extraction...")
                continue  # Continue the infinite loop

    def _is_fatal_error(self, e: Exception) -> bool:
        """Detect non-retryable fatal errors that should abort immediately."""
        try:
            # requests-style HTTPError with response status
            response = getattr(e, "response", None)
            status = getattr(response, "status_code", None)
            if isinstance(status, int) and 400 <= status < 500 and status != 429:
                return True

            # Message-based heuristics
            s = str(e).lower()
            # Model missing / not found
            if ("model" in s and "not found" in s) or ("model" in s and "pull" in s and "first" in s):
                return True
            # API key missing
            if "missing llm api key" in s or "no openai api key" in s or "no llm api key" in s:
                return True
            # Connection refused to local provider that clearly won't recover
            if "connection refused" in s and ("localhost" in s or "127.0.0.1" in s):
                return True
        except Exception:
            pass
        return False

    async def _safe_start_tracking(self, total_documents: int, total_entities: int, session_id: str = None):
        """Safely start progress tracking with timeout."""
        try:
            await asyncio.wait_for(
                self.progress_tracker.start_tracking(
                    total_documents=total_documents,
                    total_entities=total_entities,
                    session_id=session_id
                ),
                timeout=10  # Keep this timeout - it's just for progress tracking setup
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ Progress tracking initialization timed out, continuing without it")
        except Exception as e:
            logger.warning(f"⚠️ Progress tracking failed: {e}, continuing without it")

    def _extract_structured_data(self, chunked_docs: List[Dict]) -> Optional[Dict[str, Any]]:
        """Extract structured data (filtered_json) from chunked_docs metadata for source filtering."""
        for doc in chunked_docs:
            metadata = doc.get('metadata', {})
            filtered_json = metadata.get('filtered_json')
            if filtered_json and isinstance(filtered_json, dict):
                logger.debug(f"Found filtered_json in doc: {metadata.get('filename', 'unknown')}")
                return filtered_json
            
            # Also check for preprocessed_extracted_data
            preprocessed = metadata.get('preprocessed_extracted_data')
            if preprocessed and isinstance(preprocessed, dict) and preprocessed.get('lCrs'):
                logger.debug(f"Found preprocessed_extracted_data in doc: {metadata.get('filename', 'unknown')}")
                return preprocessed
        
        return None
    
    def _parse_entity_definitions(self, entities_data: List[Dict]) -> List[EntityDefinition]:
        """Parse entity definitions from configuration including source_filters."""
        from domain.entities.ner_models import SourceFilter
        
        entity_definitions = []
        
        for entity_data in entities_data:
            try:
                # Parse source_filters if present
                source_filters = None
                if entity_data.get("source_filters"):
                    source_filters = [
                        SourceFilter(
                            libnatcr=sf.get("libnatcr", ""),
                            title_keyword=sf.get("title_keyword"),
                            content_keyword=sf.get("content_keyword"),
                            depth=sf.get("depth", 0),
                            focus_section=sf.get("focus_section")
                        )
                        for sf in entity_data.get("source_filters", [])
                    ]
                
                # Parse fallback_filters if present
                fallback_filters = None
                if entity_data.get("fallback_filters"):
                    fallback_filters = [
                        SourceFilter(
                            libnatcr=sf.get("libnatcr", ""),
                            title_keyword=sf.get("title_keyword"),
                            content_keyword=sf.get("content_keyword"),
                            depth=sf.get("depth", 0),
                            focus_section=sf.get("focus_section")
                        )
                        for sf in entity_data.get("fallback_filters", [])
                    ]
                
                entity_def = EntityDefinition(
                    name=entity_data.get("name", ""),
                    definition=entity_data.get("definition", ""),
                    extraction_instructions=entity_data.get("extraction_instructions", ""),
                    processing_type=ProcessingType(entity_data.get("processing_type", "aggregate_all_matches")),
                    aggregation_instructions=entity_data.get("aggregation_instructions"),
                    valid_values=entity_data.get("valid_values"),
                    source_filters=source_filters,
                    fallback_filters=fallback_filters,
                    fallback_to_all=entity_data.get("fallback_to_all", False),
                    fallback_depth=entity_data.get("fallback_depth", 0)
                )
                entity_definitions.append(entity_def)
                
                if source_filters:
                    logger.debug(f"Entity '{entity_def.name}' has {len(source_filters)} source_filters")
                
            except Exception as e:
                logger.error(f"Failed to parse entity definition: {entity_data}, error: {e}")
                continue
        
        return entity_definitions
    
    def _add_disclaimer_prefix(self, value):
        """Add French disclaimer prefix to entity values."""
        disclaimer = ""
        
        if isinstance(value, list):
            # Handle list values (multiple_match processing)
            return [f"{str(val)}{disclaimer}" if val and str(val).strip() else val for val in value]
        elif value and str(value).strip():
            # Handle single string values
            return f"{str(value)}{disclaimer}"
        else:
            # Return original value if empty/None
            return value
    
    def _add_disclaimer_to_entity_dict(self, entity_dict):
        """Add disclaimer prefix to all value fields in an entity dictionary."""
        # Handle 'value' field (most common)
        if 'value' in entity_dict:
            entity_dict['value'] = self._add_disclaimer_prefix(entity_dict['value'])
        
        # Handle 'values' array field (multiple_match entities)
        if 'values' in entity_dict and isinstance(entity_dict['values'], list):
            for value_item in entity_dict['values']:
                if isinstance(value_item, dict) and 'value' in value_item:
                    value_item['value'] = self._add_disclaimer_prefix(value_item['value'])
        
        # Handle 'aggregated_value' field (aggregate_all_matches entities)
        if 'aggregated_value' in entity_dict:
            entity_dict['aggregated_value'] = self._add_disclaimer_prefix(entity_dict['aggregated_value'])
        
        return entity_dict
    
    def _format_results_by_processing_type(self, result) -> Dict[str, Any]:  
        """Format results to match original function output format."""  
        
        # 🔍 DEBUG LINE - Add this at the very beginning  
        logger.info(f"🔍 DEBUG: Result processing_stats keys: {list(result.processing_stats.keys()) if hasattr(result, 'processing_stats') else 'No processing_stats'}")  
        
        logger.info("📋 Formatting results by processing type...")  
            
        results_by_type = {}  
        
        try:  
            # Handle different result structures  
            if hasattr(result, 'processing_stats') and hasattr(result, 'found_entities'):  
                logger.info(f"📊 Processing EntityExtractionResult with {len(result.found_entities)} found entities")  
                
                # Group found entities by processing type  
                entities_by_type = {}  
                for entity in result.found_entities:  
                    try:  
                        # Handle both object and dict formats  
                        if hasattr(entity, 'processing_type'):  
                            # It's an ExtractedEntity object  
                            processing_type = entity.processing_type.value  
                            entity_dict = {  
                                "entity_name": entity.entity_name,  
                                "value": entity.value,  
                                "metadata": entity.metadata  
                            }
                            # Add disclaimer to all value fields
                            entity_dict = self._add_disclaimer_to_entity_dict(entity_dict)
                        elif isinstance(entity, dict):  
                            # It's already a dictionary  
                            processing_type = entity.get('processing_type', 'unknown')  
                            entity_dict = {  
                                "entity_name": entity.get('entity_name', ''),  
                                "value": entity.get('value', ''),  
                                "metadata": entity.get('metadata', {})  
                            }
                            # Copy other fields that might contain values
                            if 'values' in entity:
                                entity_dict['values'] = entity['values']
                            if 'aggregated_value' in entity:
                                entity_dict['aggregated_value'] = entity['aggregated_value']
                            # Add disclaimer to all value fields
                            entity_dict = self._add_disclaimer_to_entity_dict(entity_dict)  
                        else:  
                            logger.warning(f"⚠️ Unknown entity format: {type(entity)}")  
                            continue  
                        
                        if processing_type not in entities_by_type:  
                            entities_by_type[processing_type] = []  
                        entities_by_type[processing_type].append(entity_dict)  
                        
                    except Exception as e:  
                        logger.error(f"❌ Error processing entity: {e}")  
                        logger.debug(f"Entity data: {entity}")  
                        continue  
                
                # Create results structure for each processing type  
                for processing_type in entities_by_type.keys():  
                    results_by_type[processing_type] = {  
                        "found_entities": entities_by_type[processing_type],  
                        "not_found_entities": [  
                            entity for entity in result.not_found_entities  
                            if isinstance(entity, dict)  
                        ]  
                    }  
                    
                    logger.info(f"✅ Processing type '{processing_type}': {len(entities_by_type[processing_type])} entities")  
                
                # If no entities were categorized, create a default structure  
                if not results_by_type and result.found_entities:  
                    logger.info("📝 Creating default structure for uncategorized entities")  
                    default_entities = []  
                    for entity in result.found_entities:  
                        try:  
                            if hasattr(entity, 'entity_name'):  
                                entity_dict = {  
                                    "entity_name": entity.entity_name,  
                                    "value": entity.value,  
                                    "metadata": entity.metadata  
                                }
                                # Add disclaimer to all value fields
                                entity_dict = self._add_disclaimer_to_entity_dict(entity_dict)
                            elif isinstance(entity, dict):  
                                entity_dict = entity.copy()  # Copy all fields
                                # Add disclaimer to all value fields
                                entity_dict = self._add_disclaimer_to_entity_dict(entity_dict)  
                            else:  
                                continue  
                            default_entities.append(entity_dict)  
                        except Exception as e:  
                            logger.error(f"❌ Error formatting entity: {e}")  
                            continue  
                    
                    results_by_type["default"] = {  
                        "found_entities": default_entities,  
                        "not_found_entities": result.not_found_entities  
                    }  
            
            elif isinstance(result, dict):  
                logger.info("📊 Processing dictionary result format")  
                # Result is already in dictionary format  
                results_by_type = result  
            
            else:  
                logger.warning(f"⚠️ Unknown result format: {type(result)}")  
                results_by_type = {  
                    "unknown": {  
                        "found_entities": [],  
                        "not_found_entities": [],  
                        "error": f"Unknown result format: {type(result)}"  
                    }  
                }  
        
            # Attach processing stats and error meta if available
            try:
                stats = getattr(result, 'processing_stats', {}) if hasattr(result, 'processing_stats') else {}
                # Detect errors from stats
                has_errors = False
                if isinstance(stats, dict):
                    # Either combined or per-type stats
                    for key, val in stats.items():
                        if isinstance(val, dict):
                            if (val.get('processing_errors', 0) > 0) or (val.get('failed_documents', 0) > 0):
                                has_errors = True
                                break
                    # Some implementations store top-level counts
                    if (stats.get('processing_errors', 0) > 0) or (stats.get('failed_documents', 0) > 0):
                        has_errors = True
                results_by_type["_meta"] = {"processing_stats": stats, "has_errors": has_errors}
            except Exception:
                pass

        except Exception as e:  
            logger.error(f"❌ Error formatting results: {e}")  
            logger.debug(f"Result data: {result}")  
            results_by_type = {  
                "error": {  
                    "found_entities": [],  
                    "not_found_entities": [],  
                    "error": f"Result formatting failed: {str(e)}"  
                }  
            }  
        
        logger.info(f"📋 Formatted results: {len(results_by_type)} processing types")  
        return results_by_type  


# Create global instance for backward compatibility
orchestrator = NERWorkflowOrchestrator()

# Backward compatible function
async def extract_entities_workflow(
    json_data: str,
    chunked_docs: List[Dict],
    progress_callback=None,
    reasoning_effort: Optional[str] = "high",
    ner_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    logger.info("🚀 Starting backward-compatible extraction...")
    return await orchestrator.extract_entities_workflow(
        json_data, chunked_docs, progress_callback=progress_callback, reasoning_effort=reasoning_effort, ner_config=ner_config
    )
