from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ReportElementResponse(BaseModel):
    """Response schema for report elements"""
    type: str
    content: str
    start_char: int
    end_char: int
    page: int
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Element metadata")

class ReportResponse(BaseModel):
    """Response schema for report operations"""
    uuid: str = Field(..., description="Report UUID")
    patient_id: str = Field(..., description="Patient ID")
    status: str = Field(..., description="Report status")
    title: str = Field(..., description="Report title")
    filename: str
    file_type: str
    file_size: int
    created_at: datetime = Field(..., description="Creation timestamp")
    character_count: int
    word_count: int
    elapsed_seconds: Optional[float] = Field(default=None, description="Processing time in seconds")
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = []
    elements: List[ReportElementResponse] = []
    content: Optional[Dict[str, Any]] = Field(default=None, description="The actual report content as JSON object")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the report")

class PaginatedReportResponse(BaseModel):
    """Response schema for paginated reports"""
    total: int = Field(..., description="Total number of reports")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    items: List[ReportResponse] = Field(..., description="List of reports")

class PatientDocumentResponse(BaseModel):
    """Response schema for patient document operations"""
    uuid: str = Field(..., description="Document UUID")
    patient_id: str = Field(..., description="Patient ID")
    type: str = Field(..., description="Document type")
    source: Optional[str] = Field(default=None, description="Document source")
    status: str = Field(..., description="Document status")
    notes: Optional[str] = Field(default=None, description="Document notes")
    filename: Optional[str] = Field(default=None, description="Original filename")
    file_path: Optional[str] = Field(default=None, description="Path to stored file")
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Document last update timestamp")
    processing_started_at: Optional[datetime] = Field(default=None, description="When processing started")
    processing_completed_at: Optional[datetime] = Field(default=None, description="When processing completed")
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    parsed_document_uuid: Optional[str] = Field(default=None, description="UUID of parsed document if processing completed")
    
    # Document Categorization Results
    document_category: Optional[str] = Field(default=None, description="Document category determined by LLM")
    document_type: Optional[str] = Field(default=None, description="Document type identifier")
    categorization_completed_at: Optional[datetime] = Field(default=None, description="When categorization completed")
    
    # Structured Data Extraction Results
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, description="Structured data extracted from document")
    extraction_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Data extraction processing metadata")
    extraction_status: Optional[str] = Field(default=None, description="Status of data extraction process")
    extraction_completed_at: Optional[datetime] = Field(default=None, description="When data extraction completed")
    

class PaginatedPatientDocumentResponse(BaseModel):
    """Response schema for paginated patient documents"""
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    items: List[PatientDocumentResponse] = Field(..., description="List of documents")

class PatientDocumentUploadResponse(BaseModel):
    """Response schema for patient document upload"""
    uuid: str = Field(..., description="Document UUID")
    patient_id: Optional[str] = Field(default=None, description="Patient ID - null until extracted during processing")
    type: str = Field(..., description="Document type")
    source: Optional[str] = Field(default=None, description="Document source")
    status: str = Field(..., description="Document status")
    notes: Optional[str] = Field(default=None, description="Document notes")
    filename: Optional[str] = Field(default=None, description="Original filename")
    created_at: datetime = Field(..., description="Document creation timestamp")
    message: str = Field(..., description="Response message")
    # Add extracted data for full document retrieval
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, description="Structured data extracted from document")
    extraction_status: Optional[str] = Field(default=None, description="Status of data extraction process")
    # Add file content and OCR results for source viewer
    file_content: Optional[str] = Field(default=None, description="Base64 encoded file content")
    ocr_text: Optional[str] = Field(default=None, description="OCR extracted text")
    character_count: Optional[int] = Field(default=None, description="Character count")
    word_count: Optional[int] = Field(default=None, description="Word count")
    # Patient ID change tracking
    patient_id_changed: Optional[bool] = Field(default=False, description="True if patient_id was updated during processing")
    original_patient_id: Optional[str] = Field(default=None, description="Original patient_id if it was changed")

class ErrorResponse(BaseModel):
    """Response schema for errors"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Error details") 


class GenerationResponse(BaseModel):
    """Response schema for generation logs"""
    uuid: str
    timestamp_utc: datetime
    patient_id: str
    model_llm: str
    max_entities_per_batch: int
    aggregation_batch_size: int
    max_content_size: int
    chunk_overlapping: int
    max_concurrent_requests: int
    report_title: Optional[str] = None
    filenames_hash: str
    elapsed_seconds: float
    found_entities: int
    status: str
    error: Optional[str] = None
    report: Dict[str, Any]
    evaluation_status: Optional[str] = None
    evaluation_summary: Optional[Dict[str, Any]] = None
    evaluated_at: Optional[datetime] = None
    gt_status: Optional[str] = None  # Ground truth upload status

class GenerationsListResponse(BaseModel):
    """Response schema for list of generations with optional filtering"""
    items: List[GenerationResponse]
    total: int