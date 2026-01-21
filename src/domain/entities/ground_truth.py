"""
Ground Truth Entity - Standalone collection for GT data.

This entity represents ground truth data uploaded by users for evaluation.
It is stored in a separate 'ground_truths' collection, linked by patient_id and report_uuid.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid as uuid_lib


class GroundTruthPDF(BaseModel):
    """Metadata about the uploaded ground truth PDF stored as base64."""
    filename: str
    file_content: str = Field(..., description="Base64-encoded PDF content")
    pages: int = Field(default=1)
    file_size: int = Field(default=0)


class GroundTruthEntity(BaseModel):
    """A single ground truth entity with value and source info."""
    entity_name: str
    value: Optional[str] = None
    source: str = Field(default="extracted", description="'extracted' from OCR or 'manual' if user edited")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GroundTruth(BaseModel):
    """
    Ground truth data for evaluation.
    
    Stored in 'ground_truths' collection.
    Linked to a specific report and patient.
    Use created_at for finding the latest GT for a patient/report.
    """
    # Primary key
    uuid: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        description="Unique identifier for this ground truth record"
    )
    
    # Foreign keys
    patient_id: str = Field(..., description="Patient identifier - links to patient")
    report_uuid: str = Field(..., description="Report UUID - links to the specific report being evaluated")
    
    # Timestamps (use for finding latest)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this GT was uploaded"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this GT was last modified"
    )
    
    # OCR metadata
    ocr_engine: str = Field(..., description="OCR engine used: 'mistral' or 'easyocr'")
    ocr_text: Optional[str] = Field(default=None, description="Full OCR output text")
    
    # Original PDF
    original_pdf: Optional[GroundTruthPDF] = Field(default=None, description="Original PDF file as base64")
    
    # Extracted entities
    entities: List[GroundTruthEntity] = Field(default_factory=list)
    
    # Status
    status: str = Field(default="COMPLETED", description="PENDING, COMPLETED, FAILED")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


