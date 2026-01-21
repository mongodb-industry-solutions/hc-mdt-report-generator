from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class PaginationRequest(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Page size")

class CreateReportRequest(BaseModel):
    """Request schema for creating a report"""
    pass

class NERConfig(BaseModel):
    """Configuration for Named Entity Recognition processing"""
    max_entities_per_batch: int = Field(default=10, description="Maximum number of entities to process in a single batch")
    max_content_size: int = Field(default=10000, description="Maximum size of content chunks in characters")
    chunk_overlapping: int = Field(default=20, description="Overlap between chunks in characters")
    continue_on_batch_errors: bool = Field(default=False, description="If true, continue on batch errors; if false, fail fast")

class MDTReportRequest(BaseModel):
    """Request schema for generating MDT reports"""
    title: Optional[str] = Field(default=None, description="Custom title for the MDT report")
    include_timeline: bool = Field(default=True, description="Include medical timeline in the report")
    include_entities: bool = Field(default=True, description="Include extracted entities in the report")
    format: str = Field(default="text", description="Report format (text, json, pdf)")
    # Reasoning effort removed from UI; backend applies defaults and overrides internally
    reasoning_effort: Optional[str] = Field(default=None, description="Deprecated: UI no longer sets this")
    ner_config: Optional[NERConfig] = Field(default=None, description="NER processing configuration")
    # JSON filter options (only apply to JSON documents)
    # Option 1: BY DATE - cutoff date in YYYYMMDD (UI may send YYYY-MM-DD; backend accepts both)
    json_date_from: Optional[str] = Field(default=None, description="If provided (YYYYMMDD), filter lCrs by date >= this value")
    # Option 2: AUTO - from most recent RCP date
    json_auto_filter: Optional[bool] = Field(default=False, description="If true, filter from most recent RCP date (ignores json_date_from)")

class DocumentType(str, Enum):
    """Document type enumeration"""
    LAB_REPORT = "lab_report"
    DIAGNOSIS = "diagnosis"
    TREATMENT_PLAN = "treatment_plan"
    MEDICAL_HISTORY = "medical_history"
    IMAGING = "imaging"
    PRESCRIPTION = "prescription"
    REFERRAL = "referral"
    DISCHARGE_SUMMARY = "discharge_summary"
    OPERATION_REPORT = "operation_report"
    CONSULTATION = "consultation"
    OTHER = "other"

class DocumentStatus(str, Enum):
    """Document status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_MANUAL_INPUT = "requires_manual_input"

class PatientDocumentUploadRequest(BaseModel):
    """Request schema for uploading a document for a specific patient"""
    file_url: Optional[str] = Field(default=None, description="Path to the file")
    file: Optional[str] = Field(default=None, description="Base64 encoded file content")
    filename: Optional[str] = Field(default=None, description="Original filename (e.g., 'report.pdf', 'scan.docx')")
    type: DocumentType = Field(..., description="Type of document")
    source: Optional[str] = Field(default=None, description="Source of the document (e.g., 'hospital', 'gp', 'lab')")
    status: DocumentStatus = Field(default=DocumentStatus.QUEUED, description="Document processing status")
    notes: Optional[str] = Field(default=None, description="Optional notes about the document")

    class Config:
        use_enum_values = True 