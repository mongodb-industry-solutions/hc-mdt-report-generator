from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from api.schemas.request_schemas import DocumentType, DocumentStatus

class PatientDocument(BaseModel):
    """
    Model for patient documents.
    
    NOTE: For finding the latest document, use created_at/updated_at timestamps
    with sorting instead of is_latest flag. This is more scalable for bulk processing.
    
    Example: db.patient_documents.find({patient_id: "X"}).sort({created_at: -1}).limit(1)
    """
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique document identifier")
    patient_id: Optional[str] = Field(default=None, description="Patient ID - extracted during processing or manually assigned")
    type: DocumentType = Field(..., description="Document type")
    source: Optional[str] = Field(default=None, description="Document source")
    status: DocumentStatus = Field(default=DocumentStatus.QUEUED, description="Document status")
    notes: Optional[str] = Field(default=None, description="Document notes")
    filename: Optional[str] = Field(default=None, description="Original filename")
    file_path: Optional[str] = Field(default=None, description="Path to stored file")
    file_content: Optional[str] = Field(default=None, description="Base64 encoded file content")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Document creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Document last update timestamp")
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
    
    # OCR Results
    ocr_text: Optional[str] = Field(default=None, description="Raw text extracted from OCR")
    ocr_metadata: Optional[Dict[str, Any]] = Field(default=None, description="OCR processing metadata")
    ocr_completed_at: Optional[datetime] = Field(default=None, description="When OCR processing completed")
    character_count: Optional[int] = Field(default=None, description="Total character count from OCR")
    word_count: Optional[int] = Field(default=None, description="Total word count from OCR")
    
 
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 