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
import json
import logging  
import time  
import os
from typing import List, Dict, Any, Optional, Tuple  
from collections import defaultdict  
from datetime import datetime, timedelta  
  
# Domain imports  
from domain.entities.ner_models import (  
    EntityDefinition, Document, DocumentChunk, ExtractedEntity,  
    EntityExtractionResult, ProcessingType, EntityStatus, SourceFilter  
)  
  
# Infrastructure imports  
from infrastructure.llm.mistral_client import AsyncMistralClient  
from infrastructure.llm.bedrock_client import AsyncBedrockClient
  
# Service imports  
from services.document_processor import DocumentProcessor
from services.source_filter_service import SourceFilterService  

# Unified LLM wrapper
from services.base.llm import generate
  
# Utility imports  
from utils.xml_parser import XMLTagExtractor  
from utils.progress_tracker import ProgressTracker  
  
# Config imports  
from config.ner_config import settings

# Prompt imports
from services.prompts.entity_extraction_prompts import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    ENTITY_AGGREGATION_SYSTEM_PROMPT,
    create_entity_extraction_prompt,
    create_entity_aggregation_prompt,
    format_entities_for_extraction,
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
      
    def __init__(
        self,
        document_processor: DocumentProcessor,
        progress_tracker: Optional[ProgressTracker] = None,
        source_filter_service: Optional[SourceFilterService] = None,
    ):
        """
        Initialize the EntityExtractionService with required dependencies.
        
        Args:
            document_processor (DocumentProcessor): Service for document parsing and chunking.
                                                   Converts raw documents into processable chunks.
                                                   
            progress_tracker (Optional[ProgressTracker]): Optional progress tracking service.
                                                         Defaults to new instance if not provided.
                                                         
            source_filter_service (Optional[SourceFilterService]): Optional service for filtering
                                                                  structured JSON data (lCrs) based
                                                                  on entity source_filters configuration.
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
            ...     document_processor=DocumentProcessor(),
            ...     progress_tracker=ProgressTracker()
            ... )
        """  
        self.document_processor = document_processor  
        self.progress_tracker = progress_tracker or ProgressTracker()  
        self.xml_extractor = XMLTagExtractor()
        self.source_filter_service = source_filter_service or SourceFilterService()

        # Optional: Orchestrator may set this to control LLM reasoning
        self.reasoning_effort: Optional[str] = None
          
        # Robust processing settings  
        self.max_batch_retries = getattr(settings, 'max_batch_retries', 2)  
        self.batch_timeout = getattr(settings, 'batch_timeout_seconds', 120000)  
        self.continue_on_errors = getattr(settings, 'continue_on_batch_errors', False)

    async def extract_entities_from_documents(  
        self,  
        documents: List[Document],  
        entities: List[EntityDefinition],
        progress_callback: Optional[callable] = None,
        ner_config: Optional[Dict[str, Any]] = None,
        structured_data: Optional[Dict[str, Any]] = None
    ) -> EntityExtractionResult:  
        """Extract entities with comprehensive error handling and recovery.
        
        Args:
            documents: List of processed Document objects
            entities: List of EntityDefinition to extract
            progress_callback: Optional async callback for progress updates
            ner_config: Optional NER configuration
            structured_data: Optional structured JSON data (lCrs) for source filtering
        """  
          
        logger.info(f"🚀 Starting robust entity extraction")  
        logger.info(f"📄 Documents: {len(documents)}, Entities: {len(entities)}")
        
        # Extract structured_data from document metadata if not provided
        if structured_data is None:
            structured_data = self._extract_structured_data_from_documents(documents)
            if structured_data:
                logger.info(f"📋 Extracted structured data with {len(structured_data.get('lCrs', []))} lCrs entries")
          
        # Log document details  
        for i, doc in enumerate(documents):  
            logger.info(f"📄 Doc {i+1}: {doc.metadata.get('filename', 'Unknown')} - {len(doc.chunks)} chunks")  
            total_content = sum(len(chunk.content) for chunk in doc.chunks)  
            logger.info(f"📄 Doc {i+1} total content: {total_content} chars")  
          
        # Log entity details  
        for i, entity in enumerate(entities):  
            has_filters = "with source_filters" if entity.source_filters else "no filters"
            logger.info(f"🎯 Entity {i+1}: {entity.name} (type: {entity.processing_type.value}, {has_filters})")  
          
        try:  
            # Separate entities: those with source_filters and those without
            entities_with_filters = [e for e in entities if e.source_filters]
            entities_without_filters = [e for e in entities if not e.source_filters]
            
            all_found_entities = []
            all_not_found_entities = []
            all_warnings = []
            results_by_type = {}
            
            # Process entities WITH source_filters individually (each gets filtered documents)
            if entities_with_filters:
                logger.info(f"📋 Processing {len(entities_with_filters)} entities with source_filters...")
                filtered_results = await self._extract_entities_with_source_filters(
                    entities_with_filters, documents, structured_data, progress_callback, ner_config
                )
                all_found_entities.extend(filtered_results.found_entities)
                all_not_found_entities.extend(filtered_results.not_found_entities)
                all_warnings.extend(filtered_results.warnings)
            
            # Process entities WITHOUT source_filters using OPTIMIZED merged batch logic
            # OPTIMIZATION: Merge docs + process all entities together in fewer LLM calls
            if entities_without_filters:
                logger.info(f"📋 Processing {len(entities_without_filters)} entities without source_filters (OPTIMIZED)...")
                
                # Get max content size and chunk overlap for merging
                max_content_size = getattr(settings, 'max_content_size', 30000)
                chunk_overlapping = getattr(settings, 'chunk_overlapping', 200)
                if ner_config:
                    max_content_size = ner_config.get('max_content_size', max_content_size)
                    chunk_overlapping = ner_config.get('chunk_overlapping', chunk_overlapping)
                
                # OPTIMIZATION: Merge all documents into batches (with chunking for oversized docs)
                merged_batches = self._merge_documents_into_batches(documents, max_content_size, chunk_overlapping)
                logger.info(f"📦 Merged {len(documents)} documents into {len(merged_batches)} batches (max_size={max_content_size}, overlap={chunk_overlapping})")
                
                if progress_callback:
                    await progress_callback({
                        "status": "EXTRACTING_ENTITIES",
                        "progress": 55,
                        "message": f"Processing {len(entities_without_filters)} entities across {len(merged_batches)} merged batches...",
                        "current_step": "processing_no_filter_merged",
                        "entities_count": len(entities_without_filters),
                        "batches_count": len(merged_batches)
                    })
                
                # Process each merged batch with ALL entities together
                for batch_idx, batch in enumerate(merged_batches):
                    try:
                        logger.info(f"🚀 Processing merged batch {batch_idx + 1}/{len(merged_batches)} with {len(entities_without_filters)} entities")
                        
                        batch_entities, batch_warnings = await self._process_merged_batch(
                            batch['content'],
                            entities_without_filters,
                            batch['documents'],
                            batch_idx
                        )
                        
                        # Add documents_mobilises metadata to found entities
                        source_info = []
                        for doc in batch['documents']:
                            doc_info = {
                                "date": doc.metadata.get("created_at") or doc.metadata.get("report_date", ""),
                                "libnatcr": doc.metadata.get("report_type", ""),
                                "title": (doc.chunks[0].metadata.get("TITLE", "") 
                                         if doc.chunks and doc.chunks[0].metadata else ""),
                                "filename": doc.metadata.get("filename", "")
                            }
                            if doc_info not in source_info:
                                source_info.append(doc_info)
                        
                        for fe in batch_entities:
                            fe.metadata["documents_mobilises"] = source_info
                        
                        all_found_entities.extend(batch_entities)
                        all_warnings.extend(batch_warnings)
                        
                        # Update progress
                        if progress_callback:
                            progress = 55 + ((batch_idx + 1) / len(merged_batches)) * 30
                            await progress_callback({
                                "status": "EXTRACTING_ENTITIES",
                                "progress": int(progress),
                                "message": f"Completed batch {batch_idx + 1}/{len(merged_batches)}...",
                                "current_step": f"batch_{batch_idx + 1}_complete"
                            })
                        
                    except Exception as e:
                        logger.error(f"❌ Failed processing merged batch {batch_idx}: {e}")
                        
                        if self.continue_on_errors:
                            logger.info("🔄 Continuing with partial results due to continue_on_errors=True")
                            all_warnings.append(f"Batch {batch_idx} failed: {str(e)}")
                        else:
                            logger.error("🛑 Aborting due to continue_on_errors=False")
                            raise
                
                # Check which entities were NOT found
                found_entity_names = {fe.entity_name for fe in all_found_entities}
                for ent in entities_without_filters:
                    if ent.name not in found_entity_names:
                        all_not_found_entities.append({
                            "entity_name": ent.name,
                            "error": "Entity not found in any document"
                        })
                
                logger.info(f"✅ Completed no-filter extraction: {len(all_found_entities)} entities found")
            
            # Combine all results
            final_result = EntityExtractionResult(
                found_entities=all_found_entities,
                not_found_entities=all_not_found_entities,
                warnings=all_warnings,
                processing_stats=self._build_processing_stats(results_by_type, entities)
            )
            logger.info(f"🎉 Robust extraction completed: {len(final_result.found_entities)} entities found")  
            return final_result  
              
        except Exception as e:  
            logger.error(f"❌ Critical error in extract_entities_from_documents: {e}")  
            return EntityExtractionResult(  
                found_entities=[],  
                not_found_entities=[{"entity_name": e.name, "error": "Critical extraction failure"} for e in entities],  
                warnings=[f"Critical extraction failure: {str(e)}"]  
            )
    
    def _extract_structured_data_from_documents(self, documents: List[Document]) -> Optional[Dict[str, Any]]:
        """Extract structured data (filtered_json) from document metadata."""
        for doc in documents:
            filtered_json = doc.metadata.get('filtered_json')
            if filtered_json and isinstance(filtered_json, dict):
                return filtered_json
        return None
    
    async def _extract_entities_with_source_filters(
        self,
        entities: List[EntityDefinition],
        all_documents: List[Document],
        structured_data: Optional[Dict[str, Any]],
        progress_callback: Optional[callable],
        ner_config: Optional[Dict[str, Any]]
    ) -> EntityExtractionResult:
        """
        Extract entities that have source_filters using filtered documents.
        
        OPTIMIZED: Merges filtered documents into batches to reduce LLM calls.
        - For each entity: filter docs → merge into batches → process in parallel
        - Different entities are processed in parallel (they have different filters)
        
        Implements "retry on not found" logic:
        1. Try extraction with filtered + merged documents
        2. If entity NOT FOUND and fallback_to_all=True, retry with all documents (merged)
        """
        all_found = []
        all_not_found = []
        all_warnings = []
        
        # Get max content size and chunk overlap for merging
        max_content_size = getattr(settings, 'max_content_size', 30000)
        chunk_overlapping = getattr(settings, 'chunk_overlapping', 200)
        if ner_config:
            max_content_size = ner_config.get('max_content_size', max_content_size)
            chunk_overlapping = ner_config.get('chunk_overlapping', chunk_overlapping)
        
        # Process entities in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        # Track completed entities for progress updates
        completed_entities = {'count': 0}
        progress_lock = asyncio.Lock()
        
        async def process_single_entity(entity, entity_index):
            """Process a single entity with its filtered + merged documents."""
            entity_found_list = []
            entity_not_found_list = []
            entity_warnings = []
            
            logger.info(f"🔍 Processing entity '{entity.name}' with source_filters...")
            
            # Get filtered documents for this specific entity
            filtered_docs = self.prepare_documents_for_entity(entity, structured_data, all_documents)
            
            # Capture mobilized documents metadata for persistence
            documents_mobilises = []
            for doc in filtered_docs:
                doc_info = {
                    "date": doc.metadata.get("created_at") or doc.metadata.get("report_date", ""),
                    "libnatcr": doc.metadata.get("report_type", ""),
                    "title": doc.chunks[0].metadata.get("TITLE", "") if doc.chunks and doc.chunks[0].metadata else "",
                    "filename": doc.metadata.get("filename", "")
                }
                if doc_info not in documents_mobilises:
                    documents_mobilises.append(doc_info)
            
            logger.info(f"📋 Mobilized {len(documents_mobilises)} unique documents for '{entity.name}'")
            
            # If no filtered docs and fallback enabled, use all docs immediately
            if not filtered_docs:
                if getattr(entity, 'fallback_to_all', False):
                    fallback_depth = getattr(entity, 'fallback_depth', 0)
                    logger.info(
                        f"⚠️ No documents matched filters for '{entity.name}', "
                        f"falling back to all documents (depth={fallback_depth})"
                    )
                    filtered_docs = self._apply_depth_to_documents(all_documents, fallback_depth)
                
                if not filtered_docs:
                    logger.warning(f"⚠️ No documents available for '{entity.name}'")
                    return [], [{"entity_name": entity.name, "error": "No documents matched source_filters"}], []
            
            logger.info(f"📄 Found {len(filtered_docs)} filtered documents for '{entity.name}'")
            
            # OPTIMIZATION: Merge filtered documents into batches (with chunking for oversized docs)
            merged_batches = self._merge_documents_into_batches(filtered_docs, max_content_size, chunk_overlapping)
            logger.info(f"📦 Merged {len(filtered_docs)} docs into {len(merged_batches)} batches for '{entity.name}'")
            
            try:
                async with semaphore:
                    # Process all merged batches for this entity
                    entity_found = False
                    for batch_idx, batch in enumerate(merged_batches):
                        batch_entities, batch_warnings = await self._process_merged_batch(
                            batch['content'],
                            [entity],
                            batch['documents'],
                            batch_idx
                        )
                        
                        entity_found_list.extend(batch_entities)
                        entity_warnings.extend(batch_warnings)
                        
                        # Check if entity was found in this batch
                        if any(fe.entity_name == entity.name for fe in batch_entities):
                            entity_found = True
                    
                    # PASS 2: If NOT found and fallback_to_all enabled, retry with all documents
                    if not entity_found and getattr(entity, 'fallback_to_all', False):
                        fallback_depth = getattr(entity, 'fallback_depth', 0)
                        logger.info(
                            f"🔄 Entity '{entity.name}' not found with filters, "
                            f"retrying with all documents (depth={fallback_depth})"
                        )
                        
                        fallback_docs = self._apply_depth_to_documents(all_documents, fallback_depth)
                        
                        if fallback_docs:
                            # Capture fallback documents metadata
                            fallback_docs_mobilises = []
                            for doc in fallback_docs:
                                doc_info = {
                                    "date": doc.metadata.get("created_at") or doc.metadata.get("report_date", ""),
                                    "libnatcr": doc.metadata.get("report_type", ""),
                                    "title": doc.chunks[0].metadata.get("TITLE", "") if doc.chunks and doc.chunks[0].metadata else "",
                                    "filename": doc.metadata.get("filename", "")
                                }
                                if doc_info not in fallback_docs_mobilises:
                                    fallback_docs_mobilises.append(doc_info)
                            
                            # OPTIMIZATION: Merge fallback docs too (with chunking for oversized docs)
                            fallback_batches = self._merge_documents_into_batches(fallback_docs, max_content_size, chunk_overlapping)
                            logger.info(f"📦 Merged {len(fallback_docs)} fallback docs into {len(fallback_batches)} batches")
                            
                            for batch_idx, batch in enumerate(fallback_batches):
                                retry_entities, retry_warnings = await self._process_merged_batch(
                                    batch['content'],
                                    [entity],
                                    batch['documents'],
                                    batch_idx
                                )
                                
                                entity_warnings.extend(retry_warnings)
                                
                                # Check if found in fallback
                                for fe in retry_entities:
                                    if fe.entity_name == entity.name:
                                        fe.metadata["documents_mobilises"] = fallback_docs_mobilises[:10]
                                        fe.metadata["documents_mobilises_original_filter"] = documents_mobilises
                                        fe.metadata["used_fallback"] = True
                                        fe.metadata["fallback_docs_count"] = len(fallback_docs)
                                        entity_found_list.append(fe)
                                        entity_found = True
                                
                                if entity_found:
                                    break
                    
                    # Inject mobilized documents into found entities (non-fallback)
                    for fe in entity_found_list:
                        if fe.entity_name == entity.name and "used_fallback" not in fe.metadata:
                            fe.metadata["documents_mobilises"] = documents_mobilises
                    
                    # If nothing found, add to not_found
                    if not any(fe.entity_name == entity.name for fe in entity_found_list):
                        entity_not_found_list.append({
                            "entity_name": entity.name,
                            "error": "Entity not found in any document"
                        })
                    
                    # Report progress after entity completes
                    async with progress_lock:
                        completed_entities['count'] += 1
                        if progress_callback:
                            # Progress from 10% to 50% as entities complete
                            progress = 10 + (completed_entities['count'] / len(entities)) * 40
                            await progress_callback({
                                "status": "EXTRACTING_ENTITIES",
                                "progress": int(progress),
                                "message": f"Completed entity {completed_entities['count']}/{len(entities)}: '{entity.name}'",
                                "current_step": f"filtered_entity_{completed_entities['count']}_complete",
                                "entity_name": entity.name,
                                "entities_completed": completed_entities['count'],
                                "total_entities": len(entities)
                            })
                    
                    return entity_found_list, entity_not_found_list, entity_warnings
                    
            except Exception as e:
                logger.error(f"❌ Failed to extract '{entity.name}': {e}")
                # Still report progress even on failure
                async with progress_lock:
                    completed_entities['count'] += 1
                    if progress_callback:
                        progress = 10 + (completed_entities['count'] / len(entities)) * 40
                        await progress_callback({
                            "status": "EXTRACTING_ENTITIES",
                            "progress": int(progress),
                            "message": f"Completed entity {completed_entities['count']}/{len(entities)}: '{entity.name}' (failed)",
                            "current_step": f"filtered_entity_{completed_entities['count']}_failed"
                        })
                return [], [{"entity_name": entity.name, "error": str(e)}], []
        
        # Process all entities in parallel
        tasks = [
            process_single_entity(entity, i) 
            for i, entity in enumerate(entities)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Entity {i} failed: {result}")
                all_not_found.append({
                    "entity_name": entities[i].name,
                    "error": str(result)
                })
            else:
                found, not_found, warnings = result
                all_found.extend(found)
                all_not_found.extend(not_found)
                all_warnings.extend(warnings)
        
        # Report progress
        if progress_callback:
            await progress_callback({
                "status": "EXTRACTING_ENTITIES",
                "progress": 50,
                "message": f"Processed {len(entities)} entities with filters ({len(all_found)} found)",
                "current_step": "filtered_entities_complete"
            })
        
        return EntityExtractionResult(
            found_entities=all_found,
            not_found_entities=all_not_found,
            warnings=all_warnings
        )
    
    def _apply_depth_to_documents(
        self, 
        documents: List[Document], 
        depth: int
    ) -> List[Document]:
        """
        Apply depth limit to documents (for fallback flow).
        
        Args:
            documents: List of documents
            depth: 0 = all docs, 1 = most recent, 2 = two most recent, etc.
            
        Returns:
            Filtered list of documents
        """
        if depth <= 0 or not documents:
            return documents
        
        # Sort by created_at date field (most recent first)
        sorted_docs = sorted(
            documents,
            key=lambda d: d.metadata.get('created_at', '') if d.metadata else '',
            reverse=True
        )
        
        logger.info(f"📊 Applied depth={depth} to {len(documents)} documents, returning {min(depth, len(sorted_docs))}")
        return sorted_docs[:depth]
    
    def _chunk_text_with_overlap(
        self,
        text: str,
        max_size: int,
        overlap: int
    ) -> List[str]:
        """
        Split text into chunks with overlap for context continuity.
        
        Args:
            text: Text to chunk
            max_size: Maximum size per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_size
            
            # If this is not the last chunk, try to break at a sentence/paragraph
            if end < len(text):
                # Look for a good break point (newline, period, space) in last 200 chars
                break_region = text[max(start, end - 200):end]
                
                # Try to find paragraph break first
                para_break = break_region.rfind('\n\n')
                if para_break != -1:
                    end = max(start, end - 200) + para_break + 2
                else:
                    # Try sentence break
                    sent_break = break_region.rfind('. ')
                    if sent_break != -1:
                        end = max(start, end - 200) + sent_break + 2
                    else:
                        # Try any newline
                        line_break = break_region.rfind('\n')
                        if line_break != -1:
                            end = max(start, end - 200) + line_break + 1
            
            chunks.append(text[start:end])
            
            # Next chunk starts with overlap
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _merge_documents_into_batches(
        self,
        documents: List[Document],
        max_content_size: int,
        chunk_overlapping: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple documents into batches based on MAX_CONTENT_SIZE limit.
        
        OPTIMIZATION: If documents have pat_text in metadata, prepend it only ONCE
        per batch instead of including it in every document. This saves significant
        context space when merging multiple lCrs from the same patient.
        
        CHUNKING: If a single document exceeds max_content_size, it is chunked
        with overlap to ensure no information is lost at boundaries.
        
        Args:
            documents: List of documents to merge
            max_content_size: Maximum characters per batch
            chunk_overlapping: Number of characters to overlap when chunking large docs
            
        Returns:
            List of batch dicts, each containing:
            - 'content': Merged text content (with pat_text prepended once)
            - 'documents': List of original documents in this batch
            - 'doc_indices': Original document indices
        """
        if not documents:
            return []
        
        # Extract shared pat_text from first document (all docs share same patient)
        shared_pat_text = ""
        if documents:
            shared_pat_text = documents[0].metadata.get("pat_text", "")
            if shared_pat_text:
                logger.info(f"📋 Found shared pat_text ({len(shared_pat_text)} chars) - will prepend once per batch")
        
        # Reserve space for pat_text in size calculations
        pat_overhead = len(shared_pat_text) + len("\n\n") if shared_pat_text else 0
        # Effective max size for content (excluding pat overhead)
        effective_max_size = max_content_size - pat_overhead
        
        batches = []
        current_batch_content = []
        current_batch_docs = []
        current_batch_indices = []
        current_size = 0  # Track content size (pat added at flush time)
        
        for i, doc in enumerate(documents):
            # Calculate document content size (all chunks combined)
            doc_content_parts = []
            for chunk in doc.chunks:
                doc_content_parts.append(chunk.content)
            doc_content = "\n\n---\n\n".join(doc_content_parts)
            doc_size = len(doc_content)
            
            # If single doc exceeds effective limit, CHUNK IT with overlap
            if doc_size > effective_max_size:
                # Flush current batch first
                if current_batch_content:
                    merged_content = "\n\n---\n\n".join(current_batch_content)
                    if shared_pat_text:
                        merged_content = f"{shared_pat_text}\n\n{merged_content}"
                    batches.append({
                        'content': merged_content,
                        'documents': current_batch_docs,
                        'doc_indices': current_batch_indices
                    })
                    current_batch_content = []
                    current_batch_docs = []
                    current_batch_indices = []
                    current_size = 0
                
                # CHUNK the oversized document
                doc_chunks = self._chunk_text_with_overlap(doc_content, effective_max_size, chunk_overlapping)
                logger.info(f"✂️ Doc {i} chunked: {doc_size} chars → {len(doc_chunks)} chunks (max={effective_max_size}, overlap={chunk_overlapping})")
                
                # Each chunk becomes its own batch
                for chunk_idx, chunk_text in enumerate(doc_chunks):
                    chunk_content = f"{shared_pat_text}\n\n{chunk_text}" if shared_pat_text else chunk_text
                    batches.append({
                        'content': chunk_content,
                        'documents': [doc],
                        'doc_indices': [i],
                        'chunk_index': chunk_idx,
                        'total_chunks': len(doc_chunks)
                    })
                continue
            
            # Check if adding this doc would exceed limit
            separator_size = len("\n\n---\n\n") if current_batch_content else 0
            if current_size + separator_size + doc_size > effective_max_size:
                # Flush current batch (prepend pat once)
                if current_batch_content:
                    merged_content = "\n\n---\n\n".join(current_batch_content)
                    if shared_pat_text:
                        merged_content = f"{shared_pat_text}\n\n{merged_content}"
                    batches.append({
                        'content': merged_content,
                        'documents': current_batch_docs,
                        'doc_indices': current_batch_indices
                    })
                # Start new batch with this doc
                current_batch_content = [doc_content]
                current_batch_docs = [doc]
                current_batch_indices = [i]
                current_size = doc_size
            else:
                # Add to current batch
                current_batch_content.append(doc_content)
                current_batch_docs.append(doc)
                current_batch_indices.append(i)
                current_size += separator_size + doc_size
        
        # Flush final batch (prepend pat once)
        if current_batch_content:
            merged_content = "\n\n---\n\n".join(current_batch_content)
            if shared_pat_text:
                merged_content = f"{shared_pat_text}\n\n{merged_content}"
            batches.append({
                'content': merged_content,
                'documents': current_batch_docs,
                'doc_indices': current_batch_indices
            })
        
        pat_savings = len(shared_pat_text) * (len(documents) - len(batches)) if shared_pat_text and len(batches) > 0 else 0
        logger.info(f"📦 Merged {len(documents)} documents into {len(batches)} batches (max_size={max_content_size}, overlap={chunk_overlapping}, pat_once=True, saved ~{pat_savings} chars)")
        for i, batch in enumerate(batches):
            logger.debug(f"  Batch {i}: {len(batch.get('documents', []))} docs, {len(batch['content'])} chars")
        
        return batches
    
    def _build_processing_stats(self, results_by_type: Dict, entities: List[EntityDefinition]) -> Dict[str, Any]:
        """Build processing statistics from results."""
        stats = {
            "total_processing_types": len(results_by_type),
            "successful_types": len([r for r in results_by_type.values() if r.found_entities]),
            "failed_types": 0
        }
        for proc_type, result in results_by_type.items():
            stats[proc_type] = {
                "processing_type": proc_type,
                "total_entities": len(result.found_entities) + len(result.not_found_entities),
                "found_count": len(result.found_entities),
                "not_found_count": len(result.not_found_entities),
                "successful_documents": 1,
                "failed_documents": 0,
                "processing_errors": 0
            }
        return stats  

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
                # Calculate progress based on completed documents, not document index
                progress_within_type = completed_docs['count'] / len(documents)
                progress = 15 + ((current_type_index + progress_within_type * 0.8) / total_types) * 70
                
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
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)  
        tasks = []  
          
        for i, doc in enumerate(documents):  
            task = self._process_document_robust(  
                semaphore, doc, entities, processing_type, entity_values_map, i, 
                report_document_progress, current_type_index, total_types, len(documents), ner_config
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
                    progress = 15 + ((current_type_index + 0.8) / total_types) * 70
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
        total_docs: int = 1,
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Process a single document with comprehensive error handling."""  
          
        async with semaphore:  
            try:  
                # Add timeout for individual document processing  
                async with asyncio.timeout(self.batch_timeout):  
                    result = await self._process_single_document_robust(  
                        document, entities, processing_type, entity_values_map, doc_index, 
                        current_type_index, total_types, total_docs, ner_config
                    )
                    
                    # Report progress ONLY when document is completed
                    if report_document_progress:
                        filename = document.metadata.get('filename', 'Unknown')
                        await report_document_progress(doc_index, f"Completed document: {filename} ({processing_type.value})")
                    
                    return result
            except asyncio.TimeoutError:  
                error_msg = f"Document {doc_index} processing timed out after {self.batch_timeout}s"  
                logger.error(f"⏰ {error_msg}")  
                raise TimeoutError(error_msg)  
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
        total_docs: int = 1,
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
                  
                # Process entities in batches with error isolation  
                batch_size = settings.max_entities_per_batch  
                if ner_config is not None:
                    try:
                        batch_size = int(ner_config.get("max_entities_per_batch", batch_size))
                    except Exception:
                        batch_size = batch_size
                for i in range(0, len(remaining_entities), batch_size):  
                    entity_batch = remaining_entities[i:i + batch_size]  
                      
                    try:  
                        batch_entities, batch_warnings = await self._process_entity_batch_robust(  
                            chunk, entity_batch, document, processing_type,   
                            entity_values_map, doc_index, chunk_idx
                        )  
                          
                        found_entities.extend(batch_entities)  
                        warnings.extend(batch_warnings)  
                          
                    except Exception as e:  
                        chunk_error = f"Doc {doc_index}, Chunk {chunk_idx}, Batch {i//batch_size} failed: {str(e)}"  
                        logger.error(f"❌ {chunk_error}")  
                        chunk_errors.append(chunk_error)  
                        warnings.append(chunk_error)  
                          
                        if not self.continue_on_errors:  
                            raise  
                          
                        logger.info("🔄 Continuing with next batch due to continue_on_errors=True")  
                        continue  
              
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

    async def _process_entity_batch_robust(  
        self,  
        chunk,  
        entity_batch: List[EntityDefinition],  
        document: Document,  
        processing_type: ProcessingType,  
        entity_values_map: Dict,  
        doc_index: int,  
        chunk_index: int
    ) -> Tuple[List[ExtractedEntity], List[str]]:  
        """Process entity batch with multiple retry attempts and fallback strategies."""  
          
        logger.info(f"🔍 Processing batch: Doc {doc_index}, Chunk {chunk_index}, {len(entity_batch)} entities")  
          
        # Build prompt (same as working version)  
        # Format entities for the prompt using centralized function
        entities_text = format_entities_for_extraction(entity_batch)
  
        system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT
        prompt = create_entity_extraction_prompt(chunk.content, entities_text)  
  
        # Retry logic for this specific batch  
        last_exception = None  
        for attempt in range(self.max_batch_retries + 1):  
            try:  
                provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
                logger.info(f"📞 Calling LLM (attempt {attempt + 1}/{self.max_batch_retries + 1})... provider={provider}")
                
                if provider == "mistral":
                    # Use Mistral official client
                    mistral_client = AsyncMistralClient()
                    model_response = await mistral_client.invoke_mistral_async_robust(
                        system_prompt,
                        prompt,
                        timeout_override=self.batch_timeout,
                    )
                elif provider == "bedrock":
                    # Use AWS Bedrock client
                    async with AsyncBedrockClient() as bedrock_client:
                        model_response = await bedrock_client.invoke_bedrock_async_robust(
                            system_prompt,
                            prompt,
                            timeout_override=self.batch_timeout,
                        )
                else:
                    # Unified wrapper call (runs in a thread to avoid blocking loop)
                    model_response = await asyncio.to_thread(
                        generate,
                        prompt,
                        system_prompt,
                        reasoning_effort=(self.reasoning_effort or "low"),
                    )
                  
                logger.info(f"📥 Received response (length: {len(model_response) if model_response else 0})")  
                  
                if not model_response or not model_response.strip():  
                    raise ValueError("Empty response from LLM")  
                  
                # Parse response (same as working version)  
                return self._parse_batch_response(  
                    model_response, entity_batch, document, chunk,   
                    processing_type, entity_values_map  
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

    async def _process_merged_batch(
        self,
        merged_content: str,
        entities: List[EntityDefinition],
        source_documents: List[Document],
        batch_index: int = 0
    ) -> Tuple[List[ExtractedEntity], List[str]]:
        """
        Process a merged batch of document content with multiple entities in a single LLM call.
        
        This is the optimized path for both filtered and non-filtered scenarios:
        - Merged content = multiple documents combined
        - Multiple entities processed in one call
        
        Args:
            merged_content: Pre-merged text content from multiple documents
            entities: List of entities to extract
            source_documents: Original documents (for metadata)
            batch_index: Index of this batch for logging
            
        Returns:
            Tuple of (found_entities, warnings)
        """
        logger.info(f"🚀 Processing merged batch {batch_index}: {len(merged_content)} chars, {len(entities)} entities, {len(source_documents)} source docs")
        
        # Format entities for the prompt
        entities_text = format_entities_for_extraction(entities)
        system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT
        prompt = create_entity_extraction_prompt(merged_content, entities_text)
        
        found_entities = []
        warnings = []
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_batch_retries + 1):
            try:
                provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
                logger.info(f"📞 Calling LLM for merged batch {batch_index} (attempt {attempt + 1}/{self.max_batch_retries + 1})... provider={provider}")
                
                if provider == "mistral":
                    mistral_client = AsyncMistralClient()
                    model_response = await mistral_client.invoke_mistral_async_robust(
                        system_prompt,
                        prompt,
                        timeout_override=self.batch_timeout,
                    )
                elif provider == "bedrock":
                    # Use AWS Bedrock client
                    async with AsyncBedrockClient() as bedrock_client:
                        model_response = await bedrock_client.invoke_bedrock_async_robust(
                            system_prompt,
                            prompt,
                            timeout_override=self.batch_timeout,
                        )
                else:
                    model_response = await asyncio.to_thread(
                        generate,
                        prompt,
                        system_prompt,
                        reasoning_effort=(self.reasoning_effort or "low"),
                    )
                
                logger.info(f"📥 Received response for merged batch {batch_index} (length: {len(model_response) if model_response else 0})")
                
                if not model_response or not model_response.strip():
                    raise ValueError("Empty response from LLM")
                
                # Parse response - use first source doc for metadata context
                primary_doc = source_documents[0] if source_documents else None
                primary_chunk = primary_doc.chunks[0] if primary_doc and primary_doc.chunks else None
                
                # Create a mock entity_values_map for the parser (not used for FIRST_MATCH)
                entity_values_map = {}
                
                # Parse the response
                result_entities, result_warnings = self._parse_batch_response(
                    model_response, 
                    entities, 
                    primary_doc if primary_doc else Document(chunks=[], metadata={}),
                    primary_chunk if primary_chunk else DocumentChunk(content="", metadata={}),
                    ProcessingType.FIRST_MATCH,  # Treat as first match for merged batches
                    entity_values_map
                )
                
                # Enrich metadata with all source documents
                source_info = []
                for doc in source_documents:
                    source_info.append({
                        "date": doc.metadata.get("created_at") or doc.metadata.get("report_date", ""),
                        "libnatcr": doc.metadata.get("report_type", ""),
                        "title": (doc.chunks[0].metadata.get("TITLE", "") 
                                 if doc.chunks and doc.chunks[0].metadata else ""),
                        "filename": doc.metadata.get("filename", "")
                    })
                
                for entity in result_entities:
                    entity.metadata["source_documents"] = source_info
                    entity.metadata["merged_batch_index"] = batch_index
                    entity.metadata["documents_count"] = len(source_documents)
                
                found_entities.extend(result_entities)
                warnings.extend(result_warnings)
                
                return found_entities, warnings
                
            except Exception as e:
                last_exception = e
                logger.error(f"❌ Merged batch {batch_index} attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                
                if attempt < self.max_batch_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ All {self.max_batch_retries + 1} attempts failed for merged batch {batch_index}")
                    break
        
        # All retries failed
        if self.continue_on_errors:
            logger.warning(f"⚠️ Returning empty results for merged batch {batch_index} (continue_on_errors=True)")
            return [], [f"Merged batch {batch_index} failed after {self.max_batch_retries + 1} attempts: {str(last_exception)}"]
        else:
            logger.error("🛑 Raising exception due to merged batch failure (continue_on_errors=False)")
            raise last_exception

    def _parse_batch_response(  
        self,  
        model_response: str,  
        entity_batch: List[EntityDefinition],  
        document: Document,  
        chunk,  
        processing_type: ProcessingType,  
        entity_values_map: Dict  
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
                    extracted = self.xml_extractor.extract_from_xml_tags(model_response, tag_name)  
                    extracted = extracted.strip() if extracted else ""  
                      
                    if not extracted:  
                        continue  
                      
                    # Mark entity as found  
                    entity.status = EntityStatus.FOUND  
                    logger.info(f"✅ Found: {entity.name} = '{extracted[:50]}...'")  
                      
                    # Create metadata  
                    selected_metadata = {  
                        "filename": document.metadata.get("filename"),  
                        "created_at": document.metadata.get("created_at"),  
                        "section_id": chunk.section_id,  
                        "page_id": chunk.page_id,
                        # Source document details from chunk metadata (for filtered reports)
                        "CR_DATE": chunk.metadata.get("CR_DATE") if chunk.metadata else None,
                        "LIBNATCR": chunk.metadata.get("LIBNATCR") if chunk.metadata else None,
                        "TITLE": chunk.metadata.get("TITLE") if chunk.metadata else None,
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
                          
                        # Check for duplicates (keep all unique values)
                        existing_values = [vx["value"].strip().lower() for vx in entity_values_map[entity_key]["values"]]
                        extracted_normalized = extracted.strip().lower()
                        values_list = entity_values_map[entity_key]["values"]

                        if extracted_normalized not in existing_values:
                            values_list.append({
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
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)  
        tasks = []  
          
        for entity_data in found_entities:  
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
                    provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
                    if provider == "mistral":
                        mistral_client = AsyncMistralClient()
                        result = await mistral_client.invoke_mistral_async_robust(
                            system_prompt,
                            prompt,
                            timeout_override=1200,
                        )
                    elif provider == "bedrock":
                        # Use AWS Bedrock client for aggregation
                        async with AsyncBedrockClient() as bedrock_client:
                            result = await bedrock_client.invoke_bedrock_async_robust(
                                system_prompt,
                                prompt,
                                timeout_override=1200,
                            )
                    else:
                        result = await asyncio.to_thread(
                            generate,
                            prompt,
                            system_prompt,
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
    
    # Source filtering methods for targeted extraction
    def prepare_documents_for_entity(
        self,
        entity: EntityDefinition,
        structured_data: Optional[Dict[str, Any]],
        all_documents: List[Document]
    ) -> List[Document]:
        """
        Prepare documents for extraction based on entity's source filters.
        
        With the "1 lCr = 1 Document" architecture, documents already have lCr-specific
        metadata (LIBNATCR, CR_DATE, TITLE) enabling direct filtering without accessing
        the original lCrs array.
        
        Filtering approaches:
        1. NEW (lcr_mode): Filter Document objects directly via their metadata
        2. LEGACY: Filter lCrs array and convert back to Documents
        
        Args:
            entity: EntityDefinition with optional source_filters
            structured_data: The structured JSON data (legacy, may be None)
            all_documents: List of Document objects to filter
            
        Returns:
            List of Document objects to use for this entity's extraction
        """
        # If no source filters, use all documents
        if not entity.source_filters:
            logger.debug(f"Entity '{entity.name}' has no source_filters, using all documents")
            return all_documents
        
        if not all_documents:
            return []
        
        # Check if documents are in lcr_mode (new architecture)
        is_lcr_mode = any(
            doc.metadata.get('lcr_mode', False) 
            for doc in all_documents 
            if doc.metadata
        )
        
        if is_lcr_mode:
            # NEW APPROACH: Filter Document objects directly
            logger.info(
                f"🔍 [lcr_mode] Applying {len(entity.source_filters)} source filter(s) "
                f"for entity '{entity.name}' directly on {len(all_documents)} documents"
            )
            filtered_docs = self.source_filter_service.filter_documents(
                all_documents,
                entity.source_filters
            )
            
            # If no results and fallback exists, try fallback filters
            if not filtered_docs and entity.fallback_filters:
                logger.info(
                    f"⚠️ Primary filters yielded no results for '{entity.name}', "
                    f"trying {len(entity.fallback_filters)} fallback filter(s)"
                )
                filtered_docs = self.source_filter_service.filter_documents(
                    all_documents,
                    entity.fallback_filters
                )
            
            if not filtered_docs:
                logger.info(
                    f"📭 No matching documents found for entity '{entity.name}' after filtering"
                )
                return []
            
            # Log which documents matched
            matched_info = [
                f"{d.metadata.get('LIBNATCR', 'Unknown')} ({d.metadata.get('CR_DATE', '?')})"
                for d in filtered_docs
            ]
            logger.debug(f"Matched documents for '{entity.name}': {matched_info}")
            
            return filtered_docs
        
        # LEGACY APPROACH: Filter via lCrs array (for backward compatibility)
        if not structured_data:
            logger.warning(
                f"Entity '{entity.name}' has source_filters but no structured_data provided, "
                "falling back to all documents"
            )
            return all_documents
        
        lcrs = structured_data.get('lCrs', [])
        if not lcrs:
            logger.warning(
                f"Entity '{entity.name}' has source_filters but no lCrs in structured_data, "
                "falling back to all documents"
            )
            return all_documents
        
        # Apply primary filters
        logger.info(
            f"🔍 [legacy] Applying {len(entity.source_filters)} source filter(s) for entity '{entity.name}'"
        )
        filtered_reports = self.source_filter_service.filter_reports(
            lcrs, 
            entity.source_filters
        )
        
        # If no results and fallback exists, try fallback filters
        if not filtered_reports and entity.fallback_filters:
            logger.info(
                f"⚠️ Primary filters yielded no results for '{entity.name}', "
                f"trying {len(entity.fallback_filters)} fallback filter(s)"
            )
            filtered_reports = self.source_filter_service.filter_reports(
                lcrs,
                entity.fallback_filters
            )
        
        if not filtered_reports:
            logger.info(
                f"📭 No matching reports found for entity '{entity.name}' after filtering"
            )
            # Return empty list - entity won't be found in expected sources
            return []
        
        # Get original filename from the first document for proper source linking
        source_filename = None
        if all_documents:
            source_filename = all_documents[0].metadata.get('filename')
            logger.debug(f"Using source filename '{source_filename}' for filtered documents")
        
        # Convert filtered reports to Document objects
        return self._reports_to_documents(filtered_reports, entity, source_filename=source_filename)
    
    def _reports_to_documents(
        self,
        reports: List[Dict[str, Any]],
        entity: EntityDefinition,
        source_filename: Optional[str] = None
    ) -> List[Document]:
        """
        Convert filtered reports to Document objects for processing.
        
        Passes the FULL JSON object of each report (all fields) to the LLM,
        not just the TEXTE field. This allows the LLM to access structured
        fields like DATEACTE, CR_DATE, LIBNATCR, etc. directly.
        
        Uses the same 10K character chunking logic as the no-filter case
        for consistency. Large reports are split with overlap.
        
        Args:
            reports: List of filtered report dictionaries
            entity: EntityDefinition (used to get focus_section from filters)
            source_filename: Original JSON filename for proper source document linking
            
        Returns:
            List of Document objects ready for entity extraction
        """
        documents = []
        
        # Use same chunking settings as DocumentProcessor (from ner_config)
        max_chunk_size = 10000  # Same as settings.max_content_size
        chunk_overlap = 20      # Same as settings.chunk_overlapping
        
        for report in reports:
            # Convert FULL report to JSON string (all fields, no filtering)
            try:
                report_json = json.dumps(report, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Failed to serialize report {report.get('ID', 'unknown')}: {e}")
                continue
            
            if not report_json.strip():
                logger.debug(f"Skipping report {report.get('ID', 'unknown')}: empty JSON")
                continue
            
            # Split into chunks if report JSON > 10K chars (same logic as no-filter case)
            chunks_content = self._split_content_by_size(
                report_json, 
                max_chunk_size, 
                chunk_overlap
            )
            
            # Create a Document for each chunk
            for chunk_idx, chunk_content in enumerate(chunks_content):
                chunk = DocumentChunk(
                    content=chunk_content,
                    section_id=f"{report.get('LIBNATCR', 'unknown')}_{chunk_idx}",
                    category=report.get('NATUREDOCT', 'report'),
                    page_id=chunk_idx,
                    metadata={
                        'CR_DATE': report.get('CR_DATE'),
                        'DATEACTE': report.get('DATEACTE'),
                        'LIBNATCR': report.get('LIBNATCR'),
                        'TITLE': report.get('TITLE'),
                        'CR_MEDECIN': report.get('CR_MEDRESP'),
                        'SERVICE': report.get('SERVICE'),
                        'report_id': report.get('ID'),
                        'chunk_index': chunk_idx,
                        'total_chunks': len(chunks_content),
                        'is_full_json': True,
                    }
                )
                
                # Use original source filename for proper document linking in UI
                # Fall back to synthetic name only if source_filename not available
                doc_filename = source_filename or f"{report.get('LIBNATCR', 'report')}_{report.get('CR_DATE', '')}_{chunk_idx}"
                
                doc = Document(
                    chunks=[chunk],
                    metadata={
                        'source_type': 'filtered_json_full',
                        'filename': doc_filename,  # Points to actual document in MongoDB
                        'display_name': f"{report.get('LIBNATCR', 'report')}_{report.get('CR_DATE', '')}",  # For UI display
                        'created_at': report.get('CR_DATE'),
                        'report_date': report.get('CR_DATE'),
                        'report_type': report.get('LIBNATCR'),
                        'report_id': report.get('ID'),
                    }
                )
                documents.append(doc)
        
        total_chunks = len(documents)
        logger.info(
            f"📄 Created {total_chunks} document chunk(s) from {len(reports)} filtered reports "
            f"for entity '{entity.name}' (full JSON, max {max_chunk_size} chars/chunk)"
        )
        return documents
    
    def _split_content_by_size(
        self, 
        content: str, 
        max_size: int, 
        overlap: int
    ) -> List[str]:
        """
        Split content into chunks by size with overlap.
        
        Same logic as DocumentProcessor._split_large_chunk() for consistency.
        
        Args:
            content: Text content to split
            max_size: Maximum chunk size in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of content chunks
        """
        # If content fits in one chunk, return as-is
        if len(content) <= max_size:
            return [content]
        
        chunks = []
        start = 0
        chunk_num = 1
        
        while start < len(content):
            end = min(start + max_size, len(content))
            chunk = content[start:end]
            chunks.append(chunk)
            
            if end >= len(content):
                break
            
            # Apply overlap for next chunk
            start = max(0, end - overlap)
            chunk_num += 1
        
        logger.debug(f"Split content ({len(content)} chars) into {len(chunks)} chunks")
        return chunks
