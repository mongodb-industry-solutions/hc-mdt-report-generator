from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ReportElement(BaseModel):
    type: str
    content: Any
    start_char: int
    end_char: int
    page: int
    metadata: Optional[dict] = None

class Report(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the report")
    patient_id: str = Field(..., description="Patient identifier")
    status: str = Field(default="PROCESSING", description="Report status")
    title: str
    filename: str
    file_type: str
    file_size: int
    created_at: datetime
    character_count: int
    word_count: int
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = []
    elements: List[ReportElement] = []
    content: Optional[Dict[str, Any]] = Field(default=None, description="The actual report content as JSON object")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the report") 