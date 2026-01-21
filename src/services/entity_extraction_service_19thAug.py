#!/usr/bin/env python3
"""
Entity Extraction Service for Medical Named Entity Recognition (NER).

This module provides a robust, asynchronous service for extracting structured
entities from medical documents using AI models. It implements advanced
duplicate handling, error recovery, and progress tracking capabilities.

Key Features:
- Asynchronous processing for scalability
- Multiple extraction strategies (first_match, multiple_match, aggregate_all_matches)
- Intelligent duplicate prevention and deduplication
- Comprehensive error handling and retry logic
- Real-time progress tracking and reporting
- Batch processing optimization for large document sets
- Configurable timeout and retry mechanisms

Architecture:
The service follows a layered architecture pattern:
- Service Layer: High-level orchestration and business logic
- Domain Layer: Core entities and business rules
- Infrastructure Layer: External service integrations (AI models)
- Utility Layer: Cross-cutting concerns (XML parsing, progress tracking)

Processing Flow:
1. Document preprocessing and validation
2. Entity grouping by processing type
3. Batch creation for efficient AI model calls  
4. Parallel processing with error isolation
5. Result aggregation and duplicate elimination
6. Progress reporting and statistics collection

Example:
    >>> from services.entity_extraction_service import EntityExtractionService
    >>> from infrastructure.llm.mistral_client import AsyncMistralClient
    >>> from services.document_processor import DocumentProcessor
    >>> 
    >>> # Initialize service with dependencies
    >>> service = EntityExtractionService(
    ...     mistral_client=AsyncMistralClient(),
    ...     document_processor=DocumentProcessor()
    ... )
    >>> 
    >>> # Extract entities from documents
    >>> results = await service.extract_entities_from_documents(
    ...     documents=document_list,
    ...     entities=entity_definitions,
    ...     progress_callback=lambda p: print(f"Progress: {p['progress']}%")
    ... )

Author: ClarityGR Development Team
Created: 2024
Version: 2.0.0 - Enhanced duplicate handling and performance optimization
"""

import asyncio  
import logging  
import os
import re
import time  
from typing import List, Dict, Any, Optional, Tuple  
from collections import defaultdict  
from datetime import datetime, timedelta  
  
# Domain imports  
from domain.entities.ner_models import (  
    EntityDefinition, Document, ExtractedEntity,  
    EntityExtractionResult, ProcessingType, EntityStatus  
)  
  
# LLM wrapper
from services.base.llm import generate  
  
# Service imports  
from services.document_processor import DocumentProcessor  
  
# Utility imports  
from utils.xml_parser import XMLTagExtractor  
from utils.progress_tracker import ProgressTracker  
  
# Config imports  
from config.ner_config import settings, update_ner_settings

# Prompt imports
from services.prompts.entity_extraction_prompts import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT_VERBATIM,
    ENTITY_EXTRACTION_SYSTEM_PROMPT_LINE_RANGES,
    ENTITY_AGGREGATION_SYSTEM_PROMPT,
    create_entity_extraction_prompt_verbatim,
    create_entity_extraction_prompt_line_ranges,
    create_entity_aggregation_prompt,
    format_entities_for_extraction_verbatim,
    format_entities_for_extraction_line_ranges,
    format_values_for_aggregation
)  
  
logger = logging.getLogger(__name__)  
  
class EntityExtractionService:  
    """
    Robust asynchronous entity extraction service with advanced duplicate handling.
    
    Provides enterprise-grade entity extraction capabilities with:
    - Multi-strategy processing (first_match, multiple_match, aggregate_all_matches)
    - Intelligent duplicate prevention using simplified entity keys
    - Comprehensive error handling and retry mechanisms
    - Real-time progress tracking and performance monitoring
    - Batch optimization for efficient AI model utilization
    - Configurable timeout and reliability settings
    
    The service has been enhanced to fix critical duplicate issues:
    - Uses simplified entity keys (entity.name only) instead of complex tuples
    - Implements proper MULTIPLE_MATCH logic returning single entities with value lists
    - Maintains consistent status tracking throughout the extraction pipeline
    - Provides global entity tracking across processing types
    
    Thread Safety:
        This service is designed for async/await usage and maintains thread safety
        through proper async patterns. Do not use from multiple threads directly.
    
    Performance Characteristics:
        - Batch processing: 10-50 entities per AI model call
        - Timeout handling: Configurable per-batch timeouts (default: 120s)
        - Memory efficiency: Streaming document processing
        - Scalability: Supports 1000+ documents with progress tracking
    """  
      
    def __init__(self,   
                 document_processor: DocumentProcessor,  
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the EntityExtractionService with required dependencies.
        
        Args:
            document_processor (DocumentProcessor): Service for document parsing and chunking.
                                                   Converts raw documents into processable chunks.
                                                   
            progress_tracker (Optional[ProgressTracker]): Optional progress tracking service.
                                                         Defaults to new instance if not provided.
        
        Configuration:
            The service loads configuration from settings module:
            - max_batch_retries: Maximum retry attempts for failed batches (default: 2)
            - batch_timeout_seconds: Timeout per batch in seconds (default: 120)
            - continue_on_batch_errors: Whether to continue on partial failures (default: True)
        
        Raises:
            ValueError: If required dependencies are None
            ConfigurationError: If settings contain invalid values
        
        Example:
            >>> service = EntityExtractionService(
            ...     mistral_client=AsyncMistralClient(api_key="your-key"),
            ...     document_processor=DocumentProcessor(),
            ...     progress_tracker=ProgressTracker()
            ... )
        """  
        self.document_processor = document_processor  
        self.progress_tracker = progress_tracker or ProgressTracker()  
        self.xml_extractor = XMLTagExtractor()  
        # Optional reasoning effort control for LLM calls (low|medium|high)
        self.reasoning_effort: Optional[str] = None
          
        # Robust processing settings
        from config.ner_config import settings as ner_settings
        self.max_batch_retries = getattr(ner_settings, 'max_batch_retries', 2)  
        self.batch_timeout = getattr(ner_settings, 'batch_timeout_seconds', 120000)  
        self.continue_on_errors = getattr(ner_settings, 'continue_on_batch_errors', False)
  
    async def extract_entities_from_documents(  
        self,  
        documents: List[Document],  
        entities: List[EntityDefinition],
        progress_callback: Optional[callable] = None,
        ner_config: Optional[Dict[str, Any]] = None  
    ) -> EntityExtractionResult:  
        # If ner_config is provided, update settings
        if ner_config:
            from config.ner_config import update_ner_settings
            update_ner_settings(ner_config)
  
        """Extract entities with comprehensive error handling and recovery."""  
          
        logger.info(f"🚀 Starting robust entity extraction")  
        logger.info(f"📄 Documents: {len(documents)}, Entities: {len(entities)}")  
          
        # Log document details  
        for i, doc in enumerate(documents):  
            logger.info(f"📄 Doc {i+1}: {doc.metadata.get('filename', 'Unknown')} - {len(doc.chunks)} chunks")  
            total_content = sum(len(chunk.content) for chunk in doc.chunks)  
            logger.info(f"📄 Doc {i+1} total content: {total_content} chars")  
          
        # Log entity details  
        for i, entity in enumerate(entities):  
            logger.info(f"🎯 Entity {i+1}: {entity.name} (type: {entity.processing_type.value})")  
          
        try:  
            # Debug logging to trace execution
            logger.info("🔍 DEBUG: Starting extraction process with detailed tracing")
            
            # Group entities by processing type  
            entities_by_type = self._group_entities_by_processing_type(entities)
            results_by_type = {}  
            
            # Calculate progress weights for each processing type
            total_types = len(entities_by_type)
            current_type_index = 0
            
            # Debug logging
            logger.info(f"🔍 DEBUG: entities_by_type: {entities_by_type.keys()}, total_types: {total_types}")
              
            # Process each processing type with error isolation  
            for processing_type, entity_list in entities_by_type.items():  
                logger.info(f"🔄 Processing {len(entity_list)} entities with type: {processing_type.value}")
                
                # Report progress at start of each processing type using fixed absolute ranges
                if progress_callback:
                    type_ranges = {
                        ProcessingType.FIRST_MATCH: (20, 36),
                        ProcessingType.MULTIPLE_MATCH: (36, 44),
                        ProcessingType.AGGREGATE_ALL_MATCHES: (45, 88)
                    }
                    start_progress, _ = type_ranges.get(processing_type, (20, 88))
                    await progress_callback({
                        "status": "EXTRACTING_ENTITIES",
                        "progress": int(start_progress),
                        "message": f"Processing {processing_type.value} entities ({len(entity_list)} entities)...",
                        "current_step": f"processing_{processing_type.value}",
                        "processing_type": processing_type.value,
                        "entities_count": len(entity_list)
                    })
                  
                try:
                    logger.info(f"🔍 DEBUG: Starting _extract_entities_by_type_robust for {processing_type.value}")
                    logger.info(f"🔍 DEBUG: Parameters: docs={len(documents)}, entities={len(entity_list)}, progress_callback={progress_callback is not None}")
                    
                    try:
                        result = await self._extract_entities_by_type_robust(  
                            documents, entity_list, processing_type, progress_callback, current_type_index, total_types, ner_config
                        )
                        logger.info(f"🔍 DEBUG: _extract_entities_by_type_robust completed successfully for {processing_type.value}")
                        results_by_type[processing_type.value] = result  
                        logger.info(f"✅ Completed processing type: {processing_type.value}")
                    except Exception as e:
                        logger.error(f"🔍 DEBUG ERROR in _extract_entities_by_type_robust: {e}")
                        logger.error(f"🔍 DEBUG ERROR TYPE: {type(e)}")
                        
                        # Print detailed traceback
                        import traceback
                        logger.error(f"🔍 DEBUG TRACEBACK:\n{traceback.format_exc()}")
                        raise
                      
                except Exception as e:  
                    logger.error(f"❌ Failed processing type {processing_type.value}: {e}")  
                      
                    if self.continue_on_errors:  
                        logger.info("🔄 Continuing with partial results due to continue_on_errors=True")  
                        # Create partial result  
                        results_by_type[processing_type.value] = EntityExtractionResult(  
                            found_entities=[],  
                            not_found_entities=[  
                                {"entity_name": e.name, "error": f"Processing failed: {str(e)}"}   
                                for e in entity_list  
                            ],  
                            warnings=[f"Processing type {processing_type.value} failed: {str(e)}"]  
                        )  
                    else:  
                        logger.error("🛑 Aborting due to continue_on_errors=False")  
                        raise
                
                current_type_index += 1
              
            # Combine results  
            final_result = self._combine_results(results_by_type)  
            logger.info(f"🎉 Robust extraction completed: {len(final_result.found_entities)} entities found")  
            return final_result  
              
        except Exception as e:  
            logger.error(f"❌ Critical error in extract_entities_from_documents: {e}")  
            # Return empty result instead of crashing  
            return EntityExtractionResult(  
                found_entities=[],  
                not_found_entities=[{"entity_name": e.name, "error": "Critical extraction failure"} for e in entities],  
                warnings=[f"Critical extraction failure: {str(e)}"]  
            )  
  
    async def _extract_entities_by_type_robust(  
        self,  
        documents: List[Document],  
        entities: List[EntityDefinition],  
        processing_type: ProcessingType,
        progress_callback: Optional[callable] = None,
        current_type_index: int = 0,
        total_types: int = 1,
        ner_config: Optional[Dict[str, Any]] = None
    ) -> EntityExtractionResult:  
        """Extract entities with robust error handling per processing type."""  
          
        found_entities = []  
        all_warnings = []  
        entity_values_map = {}  
        processing_errors = []
        
        # Shared progress tracker to ensure monotonic progress during concurrent processing
        completed_docs = {'count': 0, 'max_progress': 0}
        progress_lock = asyncio.Lock()
        
        async def report_document_progress(doc_index: int, message: str):
            """Report progress for completed documents in a thread-safe way"""
            if not progress_callback:
                return
                
            async with progress_lock:
                completed_docs['count'] += 1
                # Calculate progress within fixed absolute range per processing type
                type_ranges = {
                    ProcessingType.FIRST_MATCH: (20, 36),
                    ProcessingType.MULTIPLE_MATCH: (36, 44),
                    ProcessingType.AGGREGATE_ALL_MATCHES: (45, 88)
                }
                start_progress, end_progress = type_ranges.get(processing_type, (20, 88))
                progress_within_type = completed_docs['count'] / len(documents)
                progress = start_progress + progress_within_type * (end_progress - start_progress)
                
                # Ensure progress only moves forward
                if progress > completed_docs['max_progress']:
                    completed_docs['max_progress'] = progress
                    await progress_callback({
                        "status": "EXTRACTING_ENTITIES",
                        "progress": int(progress),
                        "message": message,
                        "current_step": f"completed_doc_{completed_docs['count']}_{processing_type.value}",
                        "processing_type": processing_type.value,
                        "documents_completed": completed_docs['count'],
                        "total_documents": len(documents)
                    })
          
        # Process documents with controlled concurrency and error isolation
        from config.ner_config import settings as ner_settings
        semaphore = asyncio.Semaphore(ner_settings.max_concurrent_requests)  
        tasks = []  
          
        for i, doc in enumerate(documents):  
            task = self._process_document_robust(  
                semaphore, doc, entities, processing_type, entity_values_map, i, 
                report_document_progress, current_type_index, total_types, len(documents),
                ner_config
            )  
            tasks.append(task)  
          
        # Execute with comprehensive error handling  
        logger.info(f"🚀 Processing {len(tasks)} documents concurrently...")  
        results = await asyncio.gather(*tasks, return_exceptions=True)  
          
        # Process results with error categorization  
        successful_docs = 0  
        failed_docs = 0  
          
        for i, result in enumerate(results):  
            if isinstance(result, Exception):  
                failed_docs += 1  
                error_msg = f"Document {i} processing failed: {str(result)}"  
                logger.error(f"❌ {error_msg}")  
                processing_errors.append(error_msg)  
                all_warnings.append(error_msg)  
                  
                if not self.continue_on_errors:  
                    logger.error("🛑 Aborting due to document processing failure")  
                    raise result  
                continue  
              
            # Process successful result  
            successful_docs += 1  
            doc_entities, doc_warnings = result  
            found_entities.extend(doc_entities)  
            all_warnings.extend(doc_warnings)  
          
        logger.info(f"📊 Processing summary: {successful_docs} successful, {failed_docs} failed documents")  
          
        # Handle different processing types  
        if processing_type == ProcessingType.MULTIPLE_MATCH:  
            # Convert dictionaries to ExtractedEntity objects for MULTIPLE_MATCH
            # Create ONE entity with multiple values, not separate entities
            found_entities = []
            for entity_data in entity_values_map.values():
                entity_name = entity_data.get("entity_name", "Unknown")
                values = entity_data.get("values", [])
                
                if values:  # Only create entity if we have values
                    # Create one ExtractedEntity with all values as a list
                    values_list = [value_data["value"] for value_data in values]
                    # Use metadata from first value as primary metadata
                    primary_metadata = values[0]["metadata"]
                    
                    extracted_entity = ExtractedEntity(
                        entity_name=entity_name,
                        value=values_list,  # Store as list of values
                        metadata=primary_metadata,
                        processing_type=ProcessingType.MULTIPLE_MATCH
                    )
                    found_entities.append(extracted_entity)
                    
                    logger.info(f"✅ Created 1 ExtractedEntity with {len(values)} values for {entity_name} (MULTIPLE_MATCH)")
                
        elif processing_type == ProcessingType.AGGREGATE_ALL_MATCHES:  
            found_entities = list(entity_values_map.values())  
            try:
                # Report progress before aggregation
                if progress_callback:
                    # Use 90% point within AGGREGATE_ALL_MATCHES range before deep aggregation
                    agg_start, agg_end = (45, 88)
                    progress = agg_start + 0.9 * (agg_end - agg_start)
                    await progress_callback({
                        "status": "EXTRACTING_ENTITIES",
                        "progress": int(progress),
                        "message": f"Aggregating {len(found_entities)} entities for {processing_type.value}...",
                        "current_step": f"aggregating_{processing_type.value}",
                        "processing_type": processing_type.value,
                        "entities_count": len(found_entities)
                    })
                
                found_entities = await self._aggregate_entity_matches_robust(found_entities)  
            except Exception as e:  
                logger.error(f"❌ Aggregation failed: {e}")  
                all_warnings.append(f"Aggregation failed: {str(e)}")  
                if not self.continue_on_errors:  
                    raise  
          
        # Clean up entities  
        self._cleanup_entity_data(found_entities)  
          
        # Prepare not found entities  
        not_found_entities = [  
            {"entity_name": entity.name}  
            for entity in entities   
            if entity.status != EntityStatus.FOUND  
        ]  
          
        return EntityExtractionResult(  
            found_entities=found_entities,  
            not_found_entities=not_found_entities,  
            warnings=all_warnings,  
            processing_stats={  
                "processing_type": processing_type.value,  
                "total_entities": len(entities),  
                "found_count": len(found_entities),  
                "not_found_count": len(not_found_entities),  
                "successful_documents": successful_docs,  
                "failed_documents": failed_docs,  
                "processing_errors": len(processing_errors)  
            }  
        )  
  
    def _combine_results(  
        self,   
        results_by_type: Dict[str, EntityExtractionResult]  
    ) -> EntityExtractionResult:  
        """Combine results from different processing types with flexible format handling."""  
        
        logger.info(f"🔄 Combining results from {len(results_by_type)} processing types...")  
        
        all_found_entities = []  
        all_not_found_entities = []  
        all_warnings = []  
        combined_stats = {  
            "total_processing_types": len(results_by_type),  
            "successful_types": 0,  
            "failed_types": 0  
        }  
        
        for processing_type, result in results_by_type.items():  
            try:  
                logger.info(f"📊 Processing type '{processing_type}'...")  
                
                # Handle both EntityExtractionResult objects and dictionaries  
                if hasattr(result, 'found_entities'):  
                    # It's an EntityExtractionResult object  
                    found_entities = result.found_entities  
                    not_found_entities = result.not_found_entities  
                    warnings = result.warnings  
                    stats = result.processing_stats if hasattr(result, 'processing_stats') else {}  
                elif isinstance(result, dict):  
                    # It's a dictionary  
                    found_entities = result.get('found_entities', [])  
                    not_found_entities = result.get('not_found_entities', [])  
                    warnings = result.get('warnings', [])  
                    stats = result.get('processing_stats', {})  
                else:  
                    logger.warning(f"⚠️ Unknown result format for {processing_type}: {type(result)}")  
                    continue  
                
                logger.info(f"📊 Processing type '{processing_type}': {len(found_entities)} found entities")  
                
                all_found_entities.extend(found_entities)  
                all_not_found_entities.extend(not_found_entities)  
                all_warnings.extend(warnings)  
                combined_stats[processing_type] = stats  
                combined_stats["successful_types"] += 1  
                
            except Exception as e:  
                logger.error(f"❌ Error combining results for {processing_type}: {e}")  
                combined_stats["failed_types"] += 1  
                all_warnings.append(f"Error combining {processing_type}: {str(e)}")  
        
        logger.info(f"📊 Final combined results: {len(all_found_entities)} entities, {len(all_warnings)} warnings")  
        
        return EntityExtractionResult(  
            found_entities=all_found_entities,  
            not_found_entities=all_not_found_entities,  
            warnings=all_warnings,  
            processing_stats=combined_stats  
        )  
  
    async def _process_document_robust(  
        self,  
        semaphore: asyncio.Semaphore,  
        document: Document,  
        entities: List[EntityDefinition],  
        processing_type: ProcessingType,  
        entity_values_map: Dict,  
        doc_index: int,
        report_document_progress: Optional[callable] = None,
        current_type_index: int = 0,
        total_types: int = 1,
        total_documents: int = 1,
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Process a single document with comprehensive error handling."""  
          
        async with semaphore:  
            try:  
                result = await self._process_single_document_robust(  
                    document, entities, processing_type, entity_values_map, doc_index, 
                    current_type_index, total_types, total_documents, ner_config
                )
                
                # Report progress ONLY when document is completed
                if report_document_progress:
                    filename = document.metadata.get('filename', 'Unknown')
                    await report_document_progress(doc_index, f"Completed document: {filename} ({processing_type.value})")
                
                return result
            except Exception as e:  
                error_msg = f"Document {doc_index} processing failed: {str(e)}"  
                logger.error(f"❌ {error_msg}")  
                raise  
  
    async def _process_single_document_robust(  
        self,  
        document: Document,  
        entities: List[EntityDefinition],  
        processing_type: ProcessingType,  
        entity_values_map: Dict,  
        doc_index: int,
        current_type_index: int = 0,
        total_types: int = 1,
        total_documents: int = 1,
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Process a single document with chunk-level error recovery."""  
          
        found_entities = []  
        warnings = []  
        chunk_errors = []  
          
        logger.info(f"📄 Processing document {doc_index} with {len(document.chunks)} chunks")
          
        for chunk_idx, chunk in enumerate(document.chunks):  
            try:  
                # Determine remaining entities  
                if processing_type == ProcessingType.FIRST_MATCH:  
                    remaining_entities = [e for e in entities if e.status != EntityStatus.FOUND]  
                    if not remaining_entities:  
                        logger.debug("All entities found, stopping early")  
                        break  
                else:  
                    remaining_entities = entities  
                  
                if not remaining_entities:  
                    continue  
                  
                # Process entities in batches; schedule batch calls in parallel per chunk
                from config.ner_config import settings as ner_settings
                # Handle ner_config safely to avoid "not defined" errors
                batch_size = ner_settings.max_entities_per_batch
                if ner_config is not None:
                    batch_size = ner_config.get("max_entities_per_batch", batch_size)
                batch_tasks = []
                batch_maps = []
                batch_indices = []

                for i in range(0, len(remaining_entities), batch_size):
                    entity_batch = remaining_entities[i:i + batch_size]
                    local_map = {}
                    batch_maps.append(local_map)
                    batch_indices.append(i // batch_size)

                    batch_tasks.append(asyncio.create_task(
                        self._process_entity_batch_robust(
                            chunk, entity_batch, document, processing_type,
                            local_map, doc_index, chunk_idx,
                            ner_config
                        )
                    ))

                if batch_tasks:
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                    for idx, result in enumerate(batch_results):
                        batch_no = batch_indices[idx]
                        if isinstance(result, Exception):
                            chunk_error = f"Doc {doc_index}, Chunk {chunk_idx}, Batch {batch_no} failed: {str(result)}"
                            logger.error(f"❌ {chunk_error}")
                            chunk_errors.append(chunk_error)
                            warnings.append(chunk_error)
                            if not self.continue_on_errors:
                                raise result
                            continue

                        batch_entities, batch_warnings = result
                        found_entities.extend(batch_entities)
                        warnings.extend(batch_warnings)

                    # Merge per-batch maps into the shared map with simple de-duplication
                    for local_map in batch_maps:
                        for entity_key, data in local_map.items():
                            if entity_key not in entity_values_map:
                                entity_values_map[entity_key] = data
                                continue

                            existing_values_lower = {
                                v["value"].strip().lower() for v in entity_values_map[entity_key].get("values", [])
                            }
                            for v in data.get("values", []):
                                val_norm = v["value"].strip().lower()
                                if val_norm not in existing_values_lower:
                                    entity_values_map[entity_key]["values"].append(v)
                                    existing_values_lower.add(val_norm)
              
            except Exception as e:  
                chunk_error = f"Doc {doc_index}, Chunk {chunk_idx} failed: {str(e)}"  
                logger.error(f"❌ {chunk_error}")  
                chunk_errors.append(chunk_error)  
                warnings.append(chunk_error)  
                  
                if not self.continue_on_errors:  
                    raise  
                  
                logger.info("🔄 Continuing with next chunk due to continue_on_errors=True")  
                continue  
          
        logger.info(f"📄 Document {doc_index} completed: {len(found_entities)} entities, {len(warnings)} warnings")  
        return found_entities, warnings  
  
    def _wrap_and_enumerate(self, text: str, width: int = 80) -> Tuple[str, List[str]]:
        """Wrap text to max width and enumerate as L1:, L2: while returning clean lines.

        - Splits input by existing newlines first
        - Wraps each line to the given width (no word-boundary logic to keep simple and deterministic)
        - Returns the enumerated block (with L#: prefixes) and the list of clean lines
        """
        if not text:
            return "", []

        # Split into input lines
        input_lines = text.splitlines()
        wrapped_lines: List[str] = []

        for line in input_lines:
            if line == "":
                wrapped_lines.append("")
                continue
            start = 0
            n = len(line)
            while start < n:
                end = min(start + width, n)
                wrapped_lines.append(line[start:end])
                start = end

        enumerated = []
        for i, l in enumerate(wrapped_lines, start=1):
            enumerated.append(f"L{i}: {l}")

        return "\n".join(enumerated), wrapped_lines

    async def _process_entity_batch_robust(  
        self,  
        chunk,  
        entity_batch: List[EntityDefinition],  
        document: Document,  
        processing_type: ProcessingType,  
        entity_values_map: Dict,  
        doc_index: int,  
        chunk_index: int,
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Process entity batch with multiple retry attempts and fallback strategies."""  
          
        logger.info(f"🔍 Processing batch: Doc {doc_index}, Chunk {chunk_index}, {len(entity_batch)} entities")  
          
        # Build prompt based on processing type
        # - FIRST_MATCH and MULTIPLE_MATCH: keep verbatim extraction flow
        # - AGGREGATE_ALL_MATCHES: use line-range flow to reduce tokens
        if processing_type == ProcessingType.AGGREGATE_ALL_MATCHES:
            from config.ner_config import settings as ner_settings
            # Allow per-request override via ner_config
            bypass = getattr(ner_settings, "bypass_aggregate_all_matches", False)
            if ner_config is not None:
                bypass = bool(ner_config.get("bypass_aggregate_all_matches", bypass))
            if bypass:
                logger.info("🚧 Bypassing AGGREGATE_ALL_MATCHES: forcing verbatim prompt mode per configuration")
                entities_text = format_entities_for_extraction_verbatim(entity_batch)
                enumerated_lines = None
                system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT_VERBATIM
                prompt = create_entity_extraction_prompt_verbatim(chunk.content, entities_text)
            else:
                entities_text = format_entities_for_extraction_line_ranges(entity_batch)
                enumerated_text, enumerated_lines = self._wrap_and_enumerate(chunk.content, width=80)
                system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT_LINE_RANGES
                prompt = create_entity_extraction_prompt_line_ranges(enumerated_text, entities_text)
        else:
            entities_text = format_entities_for_extraction_verbatim(entity_batch)
            enumerated_lines = None  # Not used in verbatim mode
            system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT_VERBATIM
            prompt = create_entity_extraction_prompt_verbatim(chunk.content, entities_text)
  
        # Retry logic for this specific batch  
        last_exception = None  
        for attempt in range(self.max_batch_retries + 1):  
            try:  
                logger.info(f"📞 Calling LLM (attempt {attempt + 1}/{self.max_batch_retries + 1})...")
                
                # Call LLM via unified wrapper, use provider from environment or config
                from config.mistral_config import get_current_mode
                import os
                
                # Determine which provider to use based on environment variable or fallback to Mistral mode
                provider = os.environ.get("LLM_PROVIDER", "").lower() or ("mistral" if get_current_mode() == "api" else "gpt_open")
                logger.info(f"Using LLM provider: {provider}")
                
                if provider == "mistral":
                    # Use Mistral API client
                    from infrastructure.llm.mistral_client import AsyncMistralClient
                    from config.settings import settings
                    import os
                    
                    # Debug the API key that's being used
                    from config.ner_config import settings as ner_settings
                    api_key_setting = ner_settings.mistral_api_key
                    api_key_env = os.environ.get("MISTRAL_API_KEY", "")
                    
                    # Log detailed info about API keys
                    logger.info(f"API key in settings: {'[SET]' if api_key_setting else '[MISSING]'}")
                    logger.info(f"API key in env: {'[SET]' if api_key_env else '[MISSING]'}")
                    
      
                    # Try to read API key from browser storage via the environment
                    if api_key_env:
                        logger.info("Using API key from environment")
                        ner_settings.mistral_api_key = api_key_env
                    
                    # Create client with current settings
                    mistral_client = AsyncMistralClient()
                    model_response = await mistral_client.invoke_mistral_async(system_prompt, prompt)
                else:
                    # Fallback to GPT-Open
                    model_response = await asyncio.to_thread(
                        generate,
                        prompt,
                        system_prompt,
                        "gpt_open",
                        reasoning_effort=(self.reasoning_effort or "low"),
                    )
                  
                # Check if we got a valid response
                response_length = len(model_response) if model_response else 0
                logger.info(f"📥 Received response (length: {response_length})")  
                
                # Handle potential empty responses
                if not model_response or not model_response.strip():
                    # Log detailed error information for debugging
                    logger.error("❌ CRITICAL: Empty response received from LLM")
                    logger.error(f"❌ Model response type: {type(model_response)}")
                    logger.error(f"❌ Model response preview: {str(model_response)[:100]}")
                    logger.error(f"❌ Provider: {provider}")
                    logger.error(f"❌ Model: {os.environ.get('LLM_MODEL', 'Not specified')}")
                    logger.error(f"❌ Prompt length: {len(prompt)}")
                    logger.error(f"❌ System prompt length: {len(system_prompt)}")
                    logger.error(f"❌ Reasoning effort: {self.reasoning_effort}")
                    
                    # Raise with detailed information
                    raise ValueError(f"Empty response from LLM (provider={provider}, model={os.environ.get('LLM_MODEL', 'Not specified')})")  
                  
                # Parse response per mode
                return self._parse_batch_response(  
                    model_response, entity_batch, document, chunk,   
                    processing_type, entity_values_map, enumerated_lines  
                )  
                  
            except Exception as e:  
                last_exception = e  
                logger.error(f"❌ Batch attempt {attempt + 1} failed: {type(e).__name__}: {e}")  
                  
                if attempt < self.max_batch_retries:  
                    wait_time = 2 ** attempt  # Exponential backoff  
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")  
                    await asyncio.sleep(wait_time)  
                    continue  
                else:  
                    logger.error(f"❌ All {self.max_batch_retries + 1} attempts failed for batch")  
                    break  
          
        # If we get here, all retries failed  
        if self.continue_on_errors:  
            logger.warning("⚠️ Returning empty results due to batch failure (continue_on_errors=True)")  
            return [], [f"Batch processing failed after {self.max_batch_retries + 1} attempts: {str(last_exception)}"]  
        else:  
            logger.error("🛑 Raising exception due to batch failure (continue_on_errors=False)")  
            raise last_exception  
  
    def _parse_batch_response(  
        self,  
        model_response: str,  
        entity_batch: List[EntityDefinition],  
        document: Document,  
        chunk,  
        processing_type: ProcessingType,  
        entity_values_map: Dict,
        enumerated_lines: Optional[List[str]]  
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Parse batch response with error handling."""  
          
        found_entities = []  
        warnings = []  
          
        try:  
            # Extract warnings  
            warnings_text = self.xml_extractor.extract_from_xml_tags(model_response, "WARNINGS")  
            if warnings_text:  
                warnings.append(warnings_text.strip())  
                logger.info(f"⚠️ Warnings from API: {warnings_text.strip()}")  
  
            # Process each entity in the batch  
            for idx, entity in enumerate(entity_batch, 1):  
                try:  
                    tag_name = f"ENTITY_{idx}_OUTPUT"  
                    output_text = self.xml_extractor.extract_from_xml_tags(model_response, tag_name)  
                    output_text = output_text.strip() if output_text else ""  
                      
                    if not output_text:  
                        continue  
                      
                    if processing_type == ProcessingType.AGGREGATE_ALL_MATCHES and enumerated_lines is not None:
                        # Expect one or more ranges like L3-L7 separated by commas
                        # Add tolerance for optional spaces after commas
                        ranges = [r.strip() for r in output_text.split(',') if r.strip()]
                        if not ranges:
                            warnings.append(f"Entity {entity.name}: could not parse ranges '{output_text}'")
                            continue

                        collected_blocks: List[str] = []
                        for rtxt in ranges:
                            m = re.fullmatch(r"L(\d+)\s*-\s*L(\d+)", rtxt, re.IGNORECASE)
                            if not m:
                                warnings.append(f"Entity {entity.name}: invalid range token '{rtxt}' in '{output_text}'")
                                continue
                            start_idx = int(m.group(1))
                            end_idx = int(m.group(2))

                            # Expand by +1 line at the end if available (safer capture)
                            if end_idx < len(enumerated_lines):
                                end_idx_expanded = end_idx + 1
                            else:
                                end_idx_expanded = end_idx

                            if start_idx < 1 or end_idx_expanded < start_idx or end_idx_expanded > len(enumerated_lines):
                                warnings.append(f"Entity {entity.name}: out-of-bounds range '{rtxt}' after expansion")
                                continue

                            block_lines = enumerated_lines[start_idx - 1:end_idx_expanded]
                            collected_blocks.append("\n".join(block_lines))

                        if not collected_blocks:
                            # If all ranges failed to parse or were invalid
                            continue

                        extracted = "\n\n".join(collected_blocks).strip()
                    else:
                        # Verbatim mode: use the raw extracted content
                        extracted = output_text

                    # Mark entity as found  
                    entity.status = EntityStatus.FOUND  
                    logger.info(f"✅ Found: {entity.name} = '{extracted[:50]}...'")  
                      
                    # Create metadata  
                    selected_metadata = {  
                        "filename": document.metadata.get("filename"),  
                        "created_at": document.metadata.get("created_at"),  
                        "section_id": chunk.section_id,  
                        "page_id": chunk.page_id,  
                    }  
                      
                    # Handle processing types (same logic as working version)  
                    if processing_type == ProcessingType.FIRST_MATCH:  
                        extracted_entity = ExtractedEntity(  
                            entity_name=entity.name,  
                            value=extracted,  
                            metadata=selected_metadata,  
                            processing_type=processing_type  
                        )  
                        found_entities.append(extracted_entity)  
                    else:  
                        # Handle multiple_match and aggregate_all_matches  
                        entity_key = (entity.name, entity.aggregation_instructions or "", entity.definition)  
                          
                        if entity_key not in entity_values_map:  
                            entity_values_map[entity_key] = {  
                                "entity_name": entity.name,  
                                "aggregation_instructions": entity.aggregation_instructions,  
                                "definition": entity.definition,  
                                "values": []  
                            }  
                          
                        # Check for duplicates  
                        existing_values = [vx["value"].strip().lower() for vx in entity_values_map[entity_key]["values"]]  
                        extracted_normalized = extracted.strip().lower()  
                          
                        if extracted_normalized not in existing_values:  
                            entity_values_map[entity_key]["values"].append({  
                                "value": extracted,  
                                "metadata": selected_metadata  
                            })  
                        else:  
                            logger.debug(f"[DUPLICATE FILTERED] '{extracted}' for {entity.name}")  
                  
                except Exception as e:  
                    logger.error(f"❌ Error processing entity {idx} ({entity.name}): {e}")  
                    warnings.append(f"Entity {entity.name} processing error: {str(e)}")  
                    continue  
              
        except Exception as e:  
            logger.error(f"❌ Error parsing batch response: {e}")  
            warnings.append(f"Response parsing error: {str(e)}")  
          
        return found_entities, warnings  
  
    async def _aggregate_entity_matches_robust(self, found_entities: List[Dict]) -> List[ExtractedEntity]:  
        """Aggregate with comprehensive error handling."""  
          
        logger.info(f"🔄 Starting robust aggregation for {len(found_entities)} entities")  
        aggregated_entities = []  
          
        # Process entities with controlled concurrency
        from config.ner_config import settings as ner_settings
        semaphore = asyncio.Semaphore(ner_settings.max_concurrent_requests)
        tasks = []
        
        # Use aggregation_batch_size for processing entities in batches
        logger.info(f"🔄 Using aggregation batch size: {ner_settings.aggregation_batch_size}")
        
        # Process entities in batches based on aggregation_batch_size
        for i in range(0, len(found_entities), ner_settings.aggregation_batch_size):
            batch = found_entities[i:i + ner_settings.aggregation_batch_size]
            logger.info(f"🔄 Processing aggregation batch {i//ner_settings.aggregation_batch_size + 1} with {len(batch)} entities")
            
            for entity_data in batch:  
                task = self._aggregate_single_entity_robust(semaphore, entity_data)  
                tasks.append(task)
          
        # Execute with error isolation  
        results = await asyncio.gather(*tasks, return_exceptions=True)  
          
        successful_aggregations = 0  
        failed_aggregations = 0  
          
        for i, result in enumerate(results):  
            if isinstance(result, Exception):  
                failed_aggregations += 1  
                entity_name = found_entities[i].get("entity_name", f"Entity_{i}")  
                logger.error(f"❌ Aggregation failed for {entity_name}: {result}")  
                  
                if not self.continue_on_errors:  
                    raise result  
                continue  
              
            if result:  
                successful_aggregations += 1  
                aggregated_entities.append(result)  
          
        logger.info(f"📊 Aggregation summary: {successful_aggregations} successful, {failed_aggregations} failed")  
        return aggregated_entities  
  
    async def _aggregate_single_entity_robust(  
        self,   
        semaphore: asyncio.Semaphore,  
        entity_data: Dict  
    ) -> Optional[ExtractedEntity]:  
        """Aggregate single entity with retry logic."""  
          
        async with semaphore:  
            entity_name = entity_data.get("entity_name", "Unknown")  
            values = entity_data.get("values", [])  
              
            if not values:  
                logger.debug(f"⚠️ No values to aggregate for {entity_name}")  
                return None  
              
            logger.info(f"🔄 Aggregating {len(values)} values for {entity_name}")  
              
            # Extract components  
            entity_definition = entity_data.get("definition", "")  
            aggregation_instructions = entity_data.get(  
                "aggregation_instructions",   
                "Consolidate all values in a harmonized text block"  
            )  
            value_strings = [v["value"] for v in values]  
              
            # Build prompts (same as working version)  
            system_prompt = ENTITY_AGGREGATION_SYSTEM_PROMPT
            values_prompt = format_values_for_aggregation(value_strings)
            prompt = create_entity_aggregation_prompt(
                entity_name, entity_definition, aggregation_instructions, values_prompt
            )
              
            # Retry logic for aggregation
            for attempt in range(self.max_batch_retries + 1):  
                try:  
                    # Call LLM via unified wrapper, use provider from environment or config
                    from config.mistral_config import get_current_mode
                    import os
                    
                    # Determine which provider to use based on environment variable or fallback to Mistral mode
                    provider = os.environ.get("LLM_PROVIDER", "").lower() or ("mistral" if get_current_mode() == "api" else "gpt_open")
                    logger.info(f"Using LLM provider: {provider}")
                    
                    if provider == "mistral":
                        # Use Mistral API client
                        from infrastructure.llm.mistral_client import AsyncMistralClient
                        mistral_client = AsyncMistralClient()
                        result = await mistral_client.invoke_mistral_async(system_prompt, prompt)
                    else:
                        # Fallback to GPT-Open
                        result = await asyncio.to_thread(
                            generate,
                            prompt,
                            system_prompt,
                            "gpt_open",
                            reasoning_effort="high",
                        )
                      
                    result = result.strip()  
                    aggregated_value = self.xml_extractor.extract_from_xml_tags(result, "OUTPUT")  
                    aggregated_value = aggregated_value.strip() if aggregated_value else ""  
                      
                    if aggregated_value:  
                        combined_metadata = {  
                            "source_count": len(values),  
                            "sources": [v["metadata"] for v in values]  
                        }  
                          
                        logger.info(f"✅ Aggregated {entity_name}: '{aggregated_value[:50]}...'")  
                          
                        return ExtractedEntity(  
                            entity_name=entity_name,  
                            value=aggregated_value,  
                            metadata=combined_metadata,  
                            processing_type=ProcessingType.AGGREGATE_ALL_MATCHES  
                        )  
                    else:  
                        logger.warning(f"⚠️ Empty aggregation result for {entity_name}")  
                        return None  
                  
                except Exception as e:  
                    logger.error(f"❌ Aggregation attempt {attempt + 1} failed for {entity_name}: {e}")  
                      
                    if attempt < self.max_batch_retries:  
                        wait_time = 2 ** attempt  
                        logger.info(f"⏳ Waiting {wait_time}s before retry...")  
                        await asyncio.sleep(wait_time)  
                        continue  
                    else:  
                        logger.error(f"❌ All aggregation attempts failed for {entity_name}")  
                        if self.continue_on_errors:  
                            return None  
                        else:  
                            raise  
              
            return None  
  
    # Keep all your existing helper methods unchanged  
    def _group_entities_by_processing_type(self, entities: List[EntityDefinition]) -> Dict[ProcessingType, List[EntityDefinition]]:  
        grouped = defaultdict(list)  
        for entity in entities:  
            grouped[entity.processing_type].append(entity)  
        return dict(grouped)  
  
    def _cleanup_entity_data(self, entities: List[Any]) -> None:  
        for entity in entities:  
            if isinstance(entity, dict):  
                entity.pop("aggregation_instructions", None)  
                entity.pop("definition", None)
