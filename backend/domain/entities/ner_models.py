#!/usr/bin/env python3
"""
Domain Models for Named Entity Recognition (NER) System.

This module contains the core domain models that define the structure and behavior
of entities, documents, and extraction results within the NER processing pipeline.

The models follow Domain-Driven Design (DDD) principles and provide:
- Strong typing with dataclasses and enums
- Immutable data structures where appropriate
- Clear separation of concerns
- Comprehensive validation and error handling

Classes:
    ProcessingType: Enumeration of entity processing strategies
    EntityStatus: Enumeration of entity extraction states
    EntityDefinition: Configuration for extracting specific entity types
    DocumentChunk: Segmented portion of a document for processing
    Document: Complete document with chunks and metadata
    ExtractedEntity: Successfully extracted entity with metadata
    EntityExtractionResult: Complete result of extraction process
    ProcessingProgress: Real-time progress tracking for long extractions

Example:
    >>> from domain.entities.ner_models import EntityDefinition, ProcessingType
    >>> 
    >>> # Define an entity for extraction
    >>> entity = EntityDefinition(
    ...     name="Patient Age",
    ...     definition="Age of the patient in years",
    ...     extraction_instructions="Look for age mentions like '65 years old'",
    ...     processing_type=ProcessingType.FIRST_MATCH
    ... )
    >>> 
    >>> print(f"Entity: {entity.name} - Status: {entity.status.value}")
    Entity: Patient Age - Status: pending

Author: ClarityGR Development Team
Created: 2024
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ProcessingType(Enum):
    """
    Enumeration of entity processing strategies for extraction workflows.
    
    This enum defines how entities should be processed when found in documents:
    
    Attributes:
        FIRST_MATCH: Extract only the first occurrence of an entity across all documents.
                    Useful for unique identifiers or demographics that don't change.
                    Example: Patient ID, Date of Birth
                    
        MULTIPLE_MATCH: Extract all unique occurrences of an entity, combining them
                       into a single entity with multiple values. Automatically
                       deduplicates based on normalized values.
                       Example: Allergies, Medications, Symptoms
                       
        AGGREGATE_ALL_MATCHES: Extract and aggregate all occurrences with additional
                             processing logic. Maintains separate instances for
                             temporal or contextual analysis.
                             Example: Vital signs over time, Treatment responses
    
    Example:
        >>> processing_type = ProcessingType.MULTIPLE_MATCH
        >>> print(f"Strategy: {processing_type.value}")
        Strategy: multiple_match
        
        >>> # Check if it's a multi-value strategy
        >>> allows_multiple = processing_type in [
        ...     ProcessingType.MULTIPLE_MATCH,
        ...     ProcessingType.AGGREGATE_ALL_MATCHES
        ... ]
        >>> print(f"Allows multiple values: {allows_multiple}")
        Allows multiple values: True
    """
    FIRST_MATCH = "first_match"
    MULTIPLE_MATCH = "multiple_match" 
    AGGREGATE_ALL_MATCHES = "aggregate_all_matches"


class EntityStatus(Enum):
    """
    Enumeration of entity extraction lifecycle states.
    
    Tracks the current state of an entity throughout the extraction process,
    enabling progress monitoring, error handling, and workflow optimization.
    
    Attributes:
        PENDING: Entity is queued for extraction but processing hasn't started.
                Default state for newly defined entities.
                
        PROCESSING: Entity extraction is currently in progress.
                   Used for real-time progress tracking in long-running jobs.
                   
        FOUND: Entity was successfully extracted from at least one document.
              Contains valid extraction results ready for downstream use.
              
        NOT_FOUND: Entity was not found in any processed documents.
                  May indicate need for definition refinement or source expansion.
                  
        FAILED: Entity extraction failed due to processing errors.
               Requires investigation and potential retry with different parameters.
    
    State Transitions:
        PENDING → PROCESSING → {FOUND, NOT_FOUND, FAILED}
        
    Example:
        >>> status = EntityStatus.FOUND
        >>> print(f"Status: {status.value}")
        Status: found
        
        >>> # Check if extraction was successful
        >>> is_successful = status == EntityStatus.FOUND
        >>> print(f"Extraction successful: {is_successful}")
        Extraction successful: True
    """
    PENDING = "pending"
    PROCESSING = "processing"
    FOUND = "found"
    NOT_FOUND = "not_found"
    FAILED = "failed"


@dataclass
class SourceFilter:
    """
    Filter configuration for selecting specific report types for entity extraction.
    
    This enables targeted extraction by pre-filtering structured JSON data (lCrs)
    based on report type, title keywords, content keywords, and temporal constraints.
    
    Attributes:
        libnatcr (str): Required. Report type label from LIBNATCR field.
                       Examples: "Pathology Report", "MDT Meeting", "Radiology Report", 
                       "Consultation Report", "Examination Report", "Operative Report"
                       
        title_keyword (Optional[str]): Optional keyword(s) to match in TITLE field.
                                      Use pipe (|) for OR logic: "NUCLEAIRE|PET"
                                      Case-insensitive matching.
                                      
        content_keyword (Optional[str]): Optional keyword(s) to match in TEXTE field.
                                        Use pipe (|) for OR logic: "PANENDOSCOPIE|ENDOSCOPIE"
                                        Case-insensitive matching.
                                        
        depth (int): Number of reports to use after filtering and date sorting.
                    0 = all matching reports (default)
                    1 = most recent report only
                    2 = two most recent reports, etc.
                    
        focus_section (Optional[str]): Optional section to focus on within the report.
                                      Example: "conclusion" to extract only the conclusion.
                                      If not found, full report text is used.
    
    Example:
        # Filter for most recent MDT Meeting report
        >>> filter1 = SourceFilter(libnatcr="MDT Meeting", depth=1)
        
        >>> # Filter for nuclear medicine reports
        >>> filter2 = SourceFilter(
        ...     libnatcr="Examination Report",
        ...     title_keyword="NUCLEAIRE",
        ...     focus_section="conclusion",
        ...     depth=1
        ... )
        
        >>> # Filter for panendoscopy reports (any type)
        >>> filter3 = SourceFilter(
        ...     libnatcr="Operative Report",
        ...     content_keyword="PAN-ENDOSCOPIE|PANENDOSCOPIE",
        ...     depth=0
        ... )
    """
    libnatcr: str
    title_keyword: Optional[str] = None
    content_keyword: Optional[str] = None
    depth: int = 0
    focus_section: Optional[str] = None


@dataclass
class EntityDefinition:
    """
    Configuration specification for extracting a specific type of entity.
    
    Defines how an entity should be identified, extracted, and processed from
    medical documents. Serves as the blueprint for the NER extraction pipeline.
    
    Attributes:
        name (str): Unique identifier for the entity type.
                   Should be descriptive and consistent across the system.
                   Example: "Patient Allergies", "Chief Complaint"
                   
        definition (str): Clear, comprehensive description of what constitutes
                         this entity. Used by AI models to understand context.
                         Example: "Any substance or condition that causes an
                                 adverse reaction in the patient"
                         
        extraction_instructions (str): Specific guidance for AI models on how
                                     to identify and extract this entity.
                                     Should include examples and edge cases.
                                     
        processing_type (ProcessingType): Strategy for handling multiple occurrences
                                        of this entity across documents.
                                        
        aggregation_instructions (Optional[str]): Additional instructions for
                                                 combining multiple values.
                                                 Used with MULTIPLE_MATCH types.
                                                 
        valid_values (Optional[List[str]]): Constrained list of acceptable values.
                                          Used for validation and standardization.
                                          Example: ["Type 1", "Type 2"] for diabetes
                                          
        status (EntityStatus): Current state in the extraction lifecycle.
                             Defaults to PENDING for new entities.
                             
        found (bool): Legacy field for backward compatibility.
                     Use status field for new implementations.
                     
        source_filters (Optional[List[SourceFilter]]): Primary filters for selecting
                                                      which reports to search.
                                                      Multiple filters use OR logic.
                                                      If None, all documents are searched.
                                                      
        fallback_filters (Optional[List[SourceFilter]]): Fallback filters used when
                                                        primary filters yield no results.
                                                        Provides a secondary search strategy.
    
    Example:
        >>> entity_def = EntityDefinition(
        ...     name="Patient Allergies",
        ...     definition="Substances that cause adverse reactions in the patient",
        ...     extraction_instructions="Look for terms like 'allergic to', 'allergy:', or 'adverse reaction to'",
        ...     processing_type=ProcessingType.MULTIPLE_MATCH,
        ...     aggregation_instructions="Combine all unique allergens into a list",
        ...     valid_values=["Penicillin", "Aspirin", "Iodine", "Latex", "None known"],
        ...     source_filters=[SourceFilter(libnatcr="Consultation Report", depth=0)]
        ... )
        >>> 
        >>> print(f"Entity: {entity_def.name}")
        >>> print(f"Type: {entity_def.processing_type.value}")
        Entity: Patient Allergies
        Type: multiple_match
    
    Note:
        The __post_init__ method automatically converts string processing_type
        values to ProcessingType enum instances for backward compatibility.
    """
    name: str
    definition: str
    extraction_instructions: str
    processing_type: ProcessingType = ProcessingType.AGGREGATE_ALL_MATCHES  # Default to aggregate
    aggregation_instructions: Optional[str] = None
    valid_values: Optional[List[str]] = None
    status: EntityStatus = EntityStatus.PENDING
    found: bool = False  # Legacy field - use status instead
    
    # Source filtering configuration for targeted extraction
    source_filters: Optional[List['SourceFilter']] = None
    fallback_filters: Optional[List['SourceFilter']] = None
    
    # Fallback to unfiltered search when filters yield no results
    fallback_to_all: bool = False  # If True, retry with all docs when filters fail
    fallback_depth: int = 0        # 0 = all docs, 1 = most recent doc, etc.
    
    def __post_init__(self):
        """
        Post-initialization processing to ensure data consistency.
        
        Automatically converts string processing_type values to ProcessingType
        enum instances and dict source_filters to SourceFilter objects,
        enabling flexible initialization from JSON/dict sources.
        """
        if isinstance(self.processing_type, str):
            self.processing_type = ProcessingType(self.processing_type)
        
        # Convert dict source_filters to SourceFilter objects
        if self.source_filters:
            self.source_filters = [
                SourceFilter(**sf) if isinstance(sf, dict) else sf
                for sf in self.source_filters
            ]
        if self.fallback_filters:
            self.fallback_filters = [
                SourceFilter(**sf) if isinstance(sf, dict) else sf
                for sf in self.fallback_filters
            ]


@dataclass
class DocumentChunk:
    """
    Segmented portion of a document optimized for AI processing.
    
    Documents are split into manageable chunks to:
    - Stay within AI model token limits
    - Maintain semantic coherence
    - Enable parallel processing
    - Preserve document structure context
    
    Attributes:
        content (str): The actual text content of this chunk.
                      Should be semantically complete where possible.
                      
        section_id (str): Identifier for the document section this chunk belongs to.
                         Example: "history", "examination", "plan"
                         
        category (str): Type of content in this chunk.
                       Defaults to "plain_text" but can specify "table", "list", etc.
                       
        page_id (Optional[int]): Source page number for PDF documents.
                               Useful for maintaining document structure.
                               
        metadata (Dict[str, Any]): Additional contextual information about the chunk.
                                  May include formatting, confidence scores, etc.
    
    Example:
        >>> chunk = DocumentChunk(
        ...     content="Patient presents with chest pain radiating to left arm",
        ...     section_id="chief_complaint",
        ...     category="clinical_note",
        ...     page_id=1,
        ...     metadata={"confidence": 0.95, "source": "OCR"}
        ... )
        >>> 
        >>> print(f"Chunk: {chunk.content[:30]}...")
        >>> print(f"Section: {chunk.section_id}")
        Chunk: Patient presents with chest pain...
        Section: chief_complaint
    """
    content: str
    section_id: str
    category: str = "plain_text"
    page_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """
    Complete document container with processed chunks and metadata.
    
    Represents a medical document that has been parsed, chunked, and prepared
    for entity extraction. Maintains document integrity while enabling
    efficient processing.
    
    Attributes:
        chunks (List[DocumentChunk]): Ordered list of document segments.
                                    Maintains original document flow.
                                    
        metadata (Dict[str, Any]): Document-level information including:
                                 - filename: Original file name
                                 - created_at: Document creation timestamp
                                 - doc_type: Type of medical document
                                 - patient_id: Associated patient identifier
                                 - file_size: Original file size in bytes
                                 
        doc_id (str): Unique identifier for this document instance.
                     Auto-generated UUID for tracking and referencing.
    
    Example:
        >>> from datetime import datetime
        >>> 
        >>> document = Document(
        ...     chunks=[
        ...         DocumentChunk(
        ...             content="Patient: John Doe, Age: 45",
        ...             section_id="demographics"
        ...         ),
        ...         DocumentChunk(
        ...             content="Chief complaint: Chest pain",
        ...             section_id="complaint"
        ...         )
        ...     ],
        ...     metadata={
        ...         "filename": "john_doe_consultation.pdf",
        ...         "created_at": datetime.now().isoformat(),
        ...         "doc_type": "consultation_note",
        ...         "patient_id": "P12345"
        ...     }
        ... )
        >>> 
        >>> print(f"Document ID: {document.doc_id}")
        >>> print(f"Chunks: {len(document.chunks)}")
        Document ID: 550e8400-e29b-41d4-a716-446655440000
        Chunks: 2
    """
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ExtractedEntity:
    """
    Successfully extracted entity with comprehensive metadata.
    
    Represents an entity that was successfully identified and extracted from
    a document, complete with provenance information and processing context.
    
    Attributes:
        entity_name (str): Name of the entity type that was extracted.
                          Should match EntityDefinition.name.
                          
        value (Union[str, List[str]]): The extracted value(s).
                                     Single string for FIRST_MATCH,
                                     List of strings for MULTIPLE_MATCH.
                                     
        metadata (Dict[str, Any]): Extraction context including:
                                 - filename: Source document
                                 - section_id: Document section where found
                                 - created_at: Document timestamp
                                 - page_id: Source page (for PDFs)
                                 - confidence: Extraction confidence score
                                 
        processing_type (ProcessingType): Strategy used for this extraction.
                                        Affects how value is structured.
                                        
        confidence (float): Confidence score from 0.0 to 1.0.
                           Indicates extraction reliability.
                           
        extracted_at (datetime): Timestamp when extraction occurred.
                                Auto-generated for audit trails.
    
    Example:
        >>> from datetime import datetime
        >>> 
        >>> entity = ExtractedEntity(
        ...     entity_name="Patient Allergies",
        ...     value=["Penicillin", "Aspirin"],
        ...     metadata={
        ...         "filename": "patient_history.pdf",
        ...         "section_id": "allergies",
        ...         "confidence": 0.92
        ...     },
        ...     processing_type=ProcessingType.MULTIPLE_MATCH,
        ...     confidence=0.92
        ... )
        >>> 
        >>> print(f"Entity: {entity.entity_name}")
        >>> print(f"Values: {', '.join(entity.value)}")
        >>> print(f"Source: {entity.metadata['filename']}")
        Entity: Patient Allergies
        Values: Penicillin, Aspirin
        Source: patient_history.pdf
    
    Note:
        For MULTIPLE_MATCH processing, value should be a list even if only
        one item is found, maintaining consistency in data structure.
    """
    entity_name: str
    value: Union[str, List[str]]
    metadata: Dict[str, Any]
    processing_type: ProcessingType
    confidence: float = 1.0
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EntityExtractionResult:
    """
    Comprehensive result container for entity extraction operations.
    
    Aggregates all outcomes from an extraction job, including successful
    extractions, missing entities, warnings, and performance statistics.
    
    Attributes:
        found_entities (List[ExtractedEntity]): Successfully extracted entities.
                                              Ready for downstream processing.
                                              
        not_found_entities (List[Dict[str, str]]): Entities that couldn't be found.
                                                  Each dict contains entity metadata
                                                  for analysis and refinement.
                                                  
        warnings (List[str]): Non-fatal issues encountered during extraction.
                            Examples: partial matches, low confidence, format issues.
                            
        processing_stats (Dict[str, Any]): Performance and quality metrics:
                                         - total_documents_processed: int
                                         - processing_time_seconds: float
                                         - entities_per_second: float
                                         - memory_usage_mb: float
                                         - error_rate: float
    
    Properties:
        success_rate (float): Percentage of entities successfully found.
        total_entities (int): Total number of entities attempted.
    
    Example:
        >>> result = EntityExtractionResult(
        ...     found_entities=[
        ...         ExtractedEntity(
        ...             entity_name="Patient Age",
        ...             value="45 years",
        ...             metadata={"filename": "chart.pdf"},
        ...             processing_type=ProcessingType.FIRST_MATCH
        ...         )
        ...     ],
        ...     not_found_entities=[
        ...         {"entity_name": "Insurance Provider", "reason": "not_mentioned"}
        ...     ],
        ...     warnings=["Low confidence extraction for Date of Birth"],
        ...     processing_stats={
        ...         "total_documents_processed": 5,
        ...         "processing_time_seconds": 12.3,
        ...         "entities_per_second": 2.4
        ...     }
        ... )
        >>> 
        >>> print(f"Found: {len(result.found_entities)} entities")
        >>> print(f"Success rate: {result.success_rate:.1%}")
        Found: 1 entities
        Success rate: 50.0%
    """
    found_entities: List[ExtractedEntity]
    not_found_entities: List[Dict[str, str]]
    warnings: List[str] = field(default_factory=list)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate the percentage of entities successfully extracted."""
        total = len(self.found_entities) + len(self.not_found_entities)
        if total == 0:
            return 0.0
        return (len(self.found_entities) / total) * 100
    
    @property
    def total_entities(self) -> int:
        """Get total number of entities attempted for extraction."""
        return len(self.found_entities) + len(self.not_found_entities)


@dataclass
class ProcessingProgress:
    """
    Real-time progress tracking for long-running extraction operations.
    
    Provides detailed progress information for monitoring, user feedback,
    and performance optimization of extraction workflows.
    
    Attributes:
        total_documents (int): Total number of documents to process.
                             Set at job initialization.
                             
        processed_documents (int): Number of documents completed.
                                 Updated throughout processing.
                                 
        total_entities (int): Total number of entities to extract.
                            Calculated from all EntityDefinitions.
                            
        found_entities (int): Number of entities successfully extracted.
                            Updated as extractions complete.
                            
        failed_extractions (int): Number of extraction attempts that failed.
                                Useful for error rate monitoring.
                                
        start_time (datetime): When processing began.
                             Used for time-based calculations.
                             
        estimated_completion (Optional[datetime]): Projected completion time.
                                                 Based on current processing rate.
    
    Properties:
        completion_percentage (float): Progress percentage (0-100).
        processing_rate (float): Documents per second.
        estimated_time_remaining (timedelta): Time until completion.
    
    Example:
        >>> from datetime import datetime, timedelta
        >>> 
        >>> progress = ProcessingProgress(
        ...     total_documents=100,
        ...     processed_documents=25,
        ...     total_entities=50,
        ...     found_entities=30,
        ...     failed_extractions=2,
        ...     start_time=datetime.now() - timedelta(minutes=5)
        ... )
        >>> 
        >>> print(f"Progress: {progress.completion_percentage:.1f}%")
        >>> print(f"Found: {progress.found_entities}/{progress.total_entities} entities")
        >>> print(f"Success rate: {(progress.found_entities/progress.total_entities)*100:.1f}%")
        Progress: 25.0%
        Found: 30/50 entities
        Success rate: 60.0%
    """
    total_documents: int
    processed_documents: int
    total_entities: int
    found_entities: int
    failed_extractions: int
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    
    @property
    def completion_percentage(self) -> float:
        """
        Calculate completion percentage based on documents processed.
        
        Returns:
            float: Percentage complete (0.0 to 100.0)
        """
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100
    
    @property
    def processing_rate(self) -> float:
        """
        Calculate current processing rate in documents per second.
        
        Returns:
            float: Documents processed per second
        """
        elapsed = datetime.utcnow() - self.start_time
        elapsed_seconds = elapsed.total_seconds()
        if elapsed_seconds == 0:
            return 0.0
        return self.processed_documents / elapsed_seconds
    
    @property
    def estimated_time_remaining(self) -> Optional[datetime]:
        """
        Estimate completion time based on current processing rate.
        
        Returns:
            Optional[datetime]: Estimated completion time, or None if rate is zero
        """
        rate = self.processing_rate
        if rate == 0:
            return None
        
        remaining_docs = self.total_documents - self.processed_documents
        remaining_seconds = remaining_docs / rate
        return datetime.utcnow() + timedelta(seconds=remaining_seconds)
