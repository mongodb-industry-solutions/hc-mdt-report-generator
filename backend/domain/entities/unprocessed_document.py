"""
Unprocessed Document Entity

Represents documents stored in the unprocessed_documents MongoDB collection.
These documents are pre-populated by external sources and awaiting processing.
Documents are retained in this collection even after processing for record-keeping.
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timezone
import json


class UnprocessedDocument(BaseModel):
    """
    Model for unprocessed documents from external sources.
    
    These documents are stored in the `unprocessed_documents` collection
    and contain raw content that hasn't been processed through the
    OCR/NER pipeline yet. Documents remain in this collection after
    processing for record-keeping and audit purposes.
    
    Schema (flexible to support various source formats):
    - _id: unique document ID
    - patient_id: patient identifier
    - filename/file_name: original filename
    - type/file_type: file extension/type
    - document/content: document content (can be array of sections or string)
    """
    
    # Primary identifier
    id: str = Field(..., alias="_id", description="Unique document ID")
    
    # Patient association
    patient_id: str = Field(..., description="Patient ID this document belongs to")
    
    # File information - support both naming conventions
    file_name: Optional[str] = Field(default=None, description="Original filename")
    filename: Optional[str] = Field(default=None, description="Original filename (alias)")
    file_type: Optional[str] = Field(default=None, description="File type/extension")
    type: Optional[str] = Field(default=None, alias="type", description="File type (alias)")
    
    # Document content - can be:
    # - List of document sections (for structured EHR data)
    # - String (base64 for binary, text for plaintext, JSON string)
    document: Optional[Union[List[Dict[str, Any]], str]] = Field(
        default=None, 
        description="Document content (array of sections or raw content)"
    )
    content: Optional[str] = Field(
        default=None, 
        description="Document content (base64, text, or JSON)"
    )
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional metadata from source system"
    )
    
    # Timestamps (may be provided by source or set on import)
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the document was added to unprocessed collection"
    )
    
    # Source system fields (optional)
    source_document_id: Optional[str] = Field(
        default=None, 
        alias="ehr_document_id",
        description="Original document ID in the source system"
    )
    source_system: Optional[str] = Field(
        default=None, 
        alias="ehr_system",
        description="Name of the source system"
    )
    document_date: Optional[datetime] = Field(
        default=None, 
        description="Document date (when the document was created)"
    )
    
    def get_file_name(self) -> str:
        """Get the filename from either field"""
        return self.file_name or self.filename or "unknown"
    
    def get_file_type(self) -> str:
        """Get the file type from either field"""
        return self.file_type or self.type or "unknown"
    
    def get_content(self) -> str:
        """
        Get the document content as a string.
        If document is a list of sections, convert to JSON string.
        """
        if self.content:
            return self.content
        if self.document:
            if isinstance(self.document, str):
                return self.document
            # Convert list of sections to JSON string
            return json.dumps(self.document, ensure_ascii=False)
        return ""
    
    class Config:
        populate_by_name = True  # Allow both 'id' and '_id' for population
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def get_normalized_file_type(self) -> str:
        """
        Get normalized file type with leading dot for consistency with FileFormatHandler.
        
        Returns:
            str: File extension with leading dot (e.g., '.pdf', '.txt')
        """
        file_type = self.get_file_type().lower().strip()
        if not file_type.startswith('.'):
            file_type = f'.{file_type}'
        return file_type
    
    def is_binary_content(self) -> bool:
        """
        Check if the content is likely binary (base64 encoded).
        
        Binary formats: PDF, DOCX, PPTX, images
        Unknown formats default to False (treat as text/processable)
        
        Returns:
            bool: True if content is known binary type
        """
        binary_types = {'.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg', '.avif'}
        return self.get_normalized_file_type() in binary_types
    
    def is_text_content(self) -> bool:
        """
        Check if the content is text-based (including unknown types).
        
        Known text formats: TXT, MD, CSV, XML, JSON
        Unknown formats default to True (treat as text/processable)
        
        Returns:
            bool: True if content is text or unknown type (not known binary)
        """
        # If it's a known binary type, return False
        if self.is_binary_content():
            return False
        # Everything else (known text types AND unknown types) is treated as text
        return True
