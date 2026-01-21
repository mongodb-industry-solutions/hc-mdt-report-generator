from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class PaginationRequest(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Page size")

class CreateReportRequest(BaseModel):
    """Request schema for creating a report"""
    pass

class MDTReportRequest(BaseModel):
    """Request schema for generating MDT reports"""
    title: Optional[str] = Field(default=None, description="Custom title for the MDT report")
    include_timeline: bool = Field(default=True, description="Include medical timeline in the report")
    include_entities: bool = Field(default=True, description="Include extracted entities in the report")
    format: str = Field(default="text", description="Report format (text, json, pdf)")

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