"""
Unprocessed Document API Schemas

Request and Response schemas for the unprocessed documents API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class UnprocessedDocumentResponse(BaseModel):
    """Response schema for a single unprocessed document"""
    id: str = Field(..., description="Unique document ID")
    patient_id: str = Field(..., description="Patient ID")
    file_name: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type (pdf, txt, json, etc.)")
    
    # Content preview (truncated for list views)
    content_preview: Optional[str] = Field(
        default=None, 
        description="First 200 characters of content (for text) or '[Binary content]'"
    )
    content_size: Optional[int] = Field(
        default=None, 
        description="Size of content in bytes"
    )
    
    # Metadata
    created_at: Optional[datetime] = Field(default=None, description="When document was added")
    document_date: Optional[datetime] = Field(default=None, description="Document date from source")
    source_system: Optional[str] = Field(default=None, description="Source system name")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UnprocessedDocumentDetailResponse(UnprocessedDocumentResponse):
    """Response schema for detailed document view (includes full content)"""
    content: str = Field(..., description="Full document content")


class UnprocessedDocumentListResponse(BaseModel):
    """Response schema for paginated list of unprocessed documents"""
    items: List[UnprocessedDocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more pages")


class PatientUnprocessedCountResponse(BaseModel):
    """Response schema for unprocessed document counts by patient"""
    patient_id: str = Field(..., description="Patient ID")
    count: int = Field(..., description="Number of unprocessed documents")


class UnprocessedCountsResponse(BaseModel):
    """Response schema for all patient unprocessed counts"""
    counts: List[PatientUnprocessedCountResponse] = Field(
        ..., 
        description="List of patient counts"
    )
    total_documents: int = Field(..., description="Total unprocessed documents")
    total_patients: int = Field(..., description="Number of patients with unprocessed docs")


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ProcessDocumentsRequest(BaseModel):
    """Request schema for processing selected unprocessed documents"""
    document_ids: List[str] = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="List of document IDs to process (max 50 at a time)"
    )


class ProcessDocumentsResponse(BaseModel):
    """Response schema for batch processing request"""
    message: str = Field(..., description="Status message")
    total_requested: int = Field(..., description="Number of documents requested")
    processing_started: int = Field(..., description="Number of documents started processing")
    failed_to_start: int = Field(..., description="Number of documents that failed to start")
    
    # Detailed results
    processing_jobs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Details of each processing job started"
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Errors for documents that failed to start"
    )


class ProcessingStep(BaseModel):
    """A single step in the processing pipeline"""
    id: str = Field(..., description="Step identifier")
    name: str = Field(..., description="Human-readable step name")
    order: int = Field(..., description="Step order in pipeline")


class ProcessingSingleStatus(BaseModel):
    """Status of a single document being processed"""
    document_id: str = Field(..., description="Original unprocessed document ID")
    new_document_uuid: Optional[str] = Field(
        default=None, 
        description="UUID of the new processed document"
    )
    status: str = Field(..., description="Processing status")
    progress: Optional[int] = Field(default=None, description="Processing progress (0-100)")
    current_step: Optional[str] = Field(default=None, description="Current processing step ID")
    current_step_index: Optional[int] = Field(default=None, description="Current step index (0-based)")
    total_steps: Optional[int] = Field(default=None, description="Total number of steps")
    steps: Optional[List[ProcessingStep]] = Field(default=None, description="All pipeline steps")
    completed_steps: Optional[List[str]] = Field(default=None, description="IDs of completed steps")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BatchProcessingStatusResponse(BaseModel):
    """Response schema for batch processing status check"""
    total: int = Field(..., description="Total documents in batch")
    completed: int = Field(..., description="Number completed")
    in_progress: int = Field(..., description="Number in progress")
    failed: int = Field(..., description="Number failed")
    pending: int = Field(..., description="Number pending")
    documents: List[ProcessingSingleStatus] = Field(
        ..., 
        description="Status of each document"
    )
