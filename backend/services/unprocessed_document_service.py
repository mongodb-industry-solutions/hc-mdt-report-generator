"""
Unprocessed Document Service

Business logic for handling unprocessed documents from external sources.
Coordinates the conversion and processing of unprocessed documents into 
the standard document processing pipeline.

Note: Documents are retained in the unprocessed collection after processing
for record-keeping and audit purposes.
"""

import asyncio
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from repositories.unprocessed_document_repository import UnprocessedDocumentRepository
from domain.entities.unprocessed_document import UnprocessedDocument
from services.patient_document_service import PatientDocumentService
from api.schemas.request_schemas import PatientDocumentUploadRequest, DocumentType, DocumentStatus
from api.schemas.unprocessed_document_schemas import (
    UnprocessedDocumentResponse,
    UnprocessedDocumentDetailResponse,
    UnprocessedDocumentListResponse,
    ProcessDocumentsResponse,
    ProcessingSingleStatus,
    ProcessingStep,
    BatchProcessingStatusResponse,
    PatientUnprocessedCountResponse,
    UnprocessedCountsResponse
)
from services.utils.file_format_handler import FileFormatHandler
from utils.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


# Mapping from file extensions to DocumentType
FILE_TYPE_TO_DOCUMENT_TYPE: Dict[str, DocumentType] = {
    '.pdf': DocumentType.OTHER,
    '.docx': DocumentType.OTHER,
    '.pptx': DocumentType.OTHER,
    '.txt': DocumentType.OTHER,
    '.md': DocumentType.OTHER,
    '.csv': DocumentType.LAB_REPORT,
    '.xml': DocumentType.OTHER,
    '.json': DocumentType.OTHER,
    '.png': DocumentType.IMAGING,
    '.jpg': DocumentType.IMAGING,
    '.jpeg': DocumentType.IMAGING,
    '.avif': DocumentType.IMAGING,
}

# Module-level tracking for processing jobs (shared across requests)
_processing_jobs: Dict[str, Dict[str, Any]] = {}


class UnprocessedDocumentService:
    """
    Service for managing unprocessed documents from external sources.
    
    This service handles:
    1. Listing and retrieving unprocessed documents
    2. Converting unprocessed documents to the standard format
    3. Triggering processing through the existing pipeline
    
    Note: Documents are retained in the unprocessed collection after processing.
    """
    
    def __init__(self):
        self.repository = UnprocessedDocumentRepository()
        self.patient_document_service = PatientDocumentService()
    
    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    
    def get_by_id(self, doc_id: str) -> UnprocessedDocumentDetailResponse:
        """Get a single unprocessed document with full content"""
        document = self.repository.get_by_id(doc_id)
        return self._to_detail_response(document)
    
    def get_by_patient_id(
        self, 
        patient_id: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> UnprocessedDocumentListResponse:
        """Get paginated list of unprocessed documents for a patient"""
        skip = (page - 1) * page_size
        
        documents = self.repository.get_by_patient_id(
            patient_id=patient_id,
            skip=skip,
            limit=page_size + 1  # Fetch one extra to check if there are more
        )
        
        has_more = len(documents) > page_size
        if has_more:
            documents = documents[:page_size]
        
        total = self.repository.count_by_patient_id(patient_id)
        
        return UnprocessedDocumentListResponse(
            items=[self._to_response(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
    
    def get_counts_by_patient(self) -> UnprocessedCountsResponse:
        """Get unprocessed document counts for all patients"""
        counts_dict = self.repository.get_counts_by_patient()
        
        counts = [
            PatientUnprocessedCountResponse(patient_id=pid, count=count)
            for pid, count in counts_dict.items()
        ]
        
        total_documents = sum(c.count for c in counts)
        total_patients = len(counts)
        
        return UnprocessedCountsResponse(
            counts=counts,
            total_documents=total_documents,
            total_patients=total_patients
        )
    
    def get_patient_count(self, patient_id: str) -> int:
        """Get count of unprocessed documents for a specific patient"""
        return self.repository.count_by_patient_id(patient_id)
    
    # =========================================================================
    # PROCESSING OPERATIONS
    # =========================================================================
    
    async def process_documents(
        self, 
        patient_id: str, 
        document_ids: List[str]
    ) -> ProcessDocumentsResponse:
        """
        Process selected unprocessed documents.
        
        This method:
        1. Fetches the unprocessed documents
        2. Converts them to PatientDocumentUploadRequest format
        3. Creates new patient documents via the standard upload flow
        4. Triggers async processing for each document
        5. Returns job tracking information
        
        Args:
            patient_id: Patient ID for the documents
            document_ids: List of unprocessed document IDs to process
            
        Returns:
            ProcessDocumentsResponse with job tracking information
        """
        logger.info(f"Starting batch processing: {len(document_ids)} documents for patient {patient_id}")
        
        processing_jobs: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        processing_started = 0
        
        # Fetch all requested documents
        documents = self.repository.get_many_by_ids(document_ids)
        found_ids = {doc.id for doc in documents}
        
        # Check for missing documents
        for doc_id in document_ids:
            if doc_id not in found_ids:
                errors.append({
                    "document_id": doc_id,
                    "error": "Document not found in unprocessed collection"
                })
        
        # Process each found document
        for unprocessed_doc in documents:
            try:
                # Verify patient_id matches
                if unprocessed_doc.patient_id != patient_id:
                    errors.append({
                        "document_id": unprocessed_doc.id,
                        "error": f"Document belongs to patient {unprocessed_doc.patient_id}, not {patient_id}"
                    })
                    continue
                
                # Convert and create patient document
                result = await self._convert_and_process_document(unprocessed_doc)
                
                processing_jobs.append({
                    "unprocessed_document_id": unprocessed_doc.id,
                    "new_document_uuid": result["document_uuid"],
                    "filename": result["filename"],
                    "status": "processing_started"
                })
                processing_started += 1
                
                # Track the job for status queries
                _processing_jobs[unprocessed_doc.id] = {
                    "new_document_uuid": result["document_uuid"],
                    "started_at": datetime.now(timezone.utc),
                    "status": "processing"
                }
                
            except Exception as e:
                logger.error(f"Failed to start processing for document {unprocessed_doc.id}: {e}")
                errors.append({
                    "document_id": unprocessed_doc.id,
                    "error": str(e)
                })
        
        return ProcessDocumentsResponse(
            message=f"Processing started for {processing_started}/{len(document_ids)} documents",
            total_requested=len(document_ids),
            processing_started=processing_started,
            failed_to_start=len(errors),
            processing_jobs=processing_jobs,
            errors=errors
        )
    
    async def _convert_and_process_document(
        self, 
        unprocessed_doc: UnprocessedDocument
    ) -> Dict[str, Any]:
        """
        Convert an unprocessed document and trigger processing.
        
        Args:
            unprocessed_doc: The unprocessed document to convert
            
        Returns:
            Dict with document_uuid, filename, and status
        """
        file_name = unprocessed_doc.get_file_name()
        logger.info(f"Converting unprocessed document: {unprocessed_doc.id} ({file_name})")
        
        # Determine document type from file extension
        normalized_type = unprocessed_doc.get_normalized_file_type()
        doc_type = FILE_TYPE_TO_DOCUMENT_TYPE.get(normalized_type, DocumentType.OTHER)
        
        # Prepare content - ensure it's in the right format (base64)
        content = unprocessed_doc.get_content()
        
        # Content needs to be base64 encoded for the upload API
        # Check if it's already valid base64, otherwise encode it
        is_valid_base64 = False
        try:
            # Try to decode - if successful and re-encodes to same value, it's base64
            decoded = base64.b64decode(content, validate=True)
            # Additional check: valid base64 should re-encode to same string
            if base64.b64encode(decoded).decode('utf-8') == content:
                is_valid_base64 = True
        except Exception:
            pass
        
        if not is_valid_base64:
            # Content is not base64 (it's plain text, JSON, etc.) - encode it
            logger.info(f"Encoding content as base64 for document {unprocessed_doc.id}")
            content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Create upload request
        upload_request = PatientDocumentUploadRequest(
            file=content,
            filename=file_name,
            type=doc_type,
            source=unprocessed_doc.source_system or "External",
            status=DocumentStatus.QUEUED,
            notes=f"Imported from unprocessed documents (ID: {unprocessed_doc.id})"
        )
        
        # Upload document using existing service
        patient_document = self.patient_document_service.upload_document(
            patient_id=unprocessed_doc.patient_id,
            request=upload_request
        )
        
        logger.info(f"Created patient document {patient_document.uuid} from unprocessed {unprocessed_doc.id}")
        
        # Trigger async processing
        asyncio.create_task(
            self._process_and_cleanup(unprocessed_doc.id, patient_document)
        )
        
        return {
            "document_uuid": patient_document.uuid,
            "filename": patient_document.filename,
            "status": "processing_started"
        }
    
    async def _process_and_cleanup(
        self, 
        unprocessed_doc_id: str, 
        patient_document
    ) -> None:
        """
        Process a document through the standard pipeline.
        
        Note: Documents are NOT deleted from the unprocessed collection after processing.
        They are maintained for record-keeping and audit purposes.
        
        Args:
            unprocessed_doc_id: ID of the unprocessed document
            patient_document: The newly created PatientDocument
        """
        try:
            logger.info(f"Starting processing for document {patient_document.uuid}")
            
            # Define pipeline steps
            steps = [
                {"id": "upload", "name": "Upload", "order": 1},
                {"id": "text_extraction", "name": "Text Extraction", "order": 2},
                {"id": "patient_id", "name": "Patient ID", "order": 3},
                {"id": "categorization", "name": "Categorization", "order": 4},
                {"id": "data_extraction", "name": "Data Extraction", "order": 5},
                {"id": "complete", "name": "Complete", "order": 6}
            ]
            
            # Update tracking with steps
            if unprocessed_doc_id in _processing_jobs:
                _processing_jobs[unprocessed_doc_id]["status"] = "processing"
                _processing_jobs[unprocessed_doc_id]["current_step"] = "upload"
                _processing_jobs[unprocessed_doc_id]["current_step_index"] = 0
                _processing_jobs[unprocessed_doc_id]["total_steps"] = len(steps)
                _processing_jobs[unprocessed_doc_id]["steps"] = steps
                _processing_jobs[unprocessed_doc_id]["completed_steps"] = ["upload"]
            
            # Simulate step progress (in real scenario, we'd hook into actual processing)
            import asyncio
            
            step_ids = ["text_extraction", "patient_id", "categorization", "data_extraction"]
            for i, step_id in enumerate(step_ids):
                if unprocessed_doc_id in _processing_jobs:
                    _processing_jobs[unprocessed_doc_id]["current_step"] = step_id
                    _processing_jobs[unprocessed_doc_id]["current_step_index"] = i + 1
                    _processing_jobs[unprocessed_doc_id]["progress"] = int(((i + 1) / len(steps)) * 100)
                
                # Small delay to make progress visible
                await asyncio.sleep(0.3)
                
                if unprocessed_doc_id in _processing_jobs:
                    _processing_jobs[unprocessed_doc_id]["completed_steps"].append(step_id)
            
            # Process the document
            result = await self.patient_document_service.process_document(patient_document)
            
            logger.info(f"Processing completed for document {patient_document.uuid}")
            
            # Update tracking - mark complete
            if unprocessed_doc_id in _processing_jobs:
                _processing_jobs[unprocessed_doc_id]["status"] = "completed"
                _processing_jobs[unprocessed_doc_id]["current_step"] = "complete"
                _processing_jobs[unprocessed_doc_id]["current_step_index"] = len(steps) - 1
                _processing_jobs[unprocessed_doc_id]["progress"] = 100
                _processing_jobs[unprocessed_doc_id]["completed_steps"].append("complete")
                _processing_jobs[unprocessed_doc_id]["completed_at"] = datetime.now(timezone.utc)
            
            # Note: We intentionally keep the document in the unprocessed collection
            # for record-keeping and audit purposes
            logger.info(f"Unprocessed document {unprocessed_doc_id} retained after successful processing")
            
        except Exception as e:
            logger.error(f"Processing failed for document {patient_document.uuid}: {e}")
            
            # Update tracking
            if unprocessed_doc_id in _processing_jobs:
                _processing_jobs[unprocessed_doc_id]["status"] = "failed"
                _processing_jobs[unprocessed_doc_id]["error"] = str(e)
    
    def get_processing_status(self, document_ids: List[str]) -> BatchProcessingStatusResponse:
        """
        Get processing status for a batch of documents.
        
        Args:
            document_ids: List of unprocessed document IDs to check
            
        Returns:
            BatchProcessingStatusResponse with status of each document
        """
        statuses: List[ProcessingSingleStatus] = []
        completed = 0
        in_progress = 0
        failed = 0
        pending = 0
        
        for doc_id in document_ids:
            job = _processing_jobs.get(doc_id)
            
            if job is None:
                # Document not tracked - it was never submitted for processing
                statuses.append(ProcessingSingleStatus(
                    document_id=doc_id,
                    status="pending",
                    current_step="Not submitted for processing"
                ))
                pending += 1
            else:
                status = job.get("status", "unknown")
                
                # Build steps list from job data
                steps = None
                if job.get("steps"):
                    steps = [ProcessingStep(**s) for s in job["steps"]]
                
                statuses.append(ProcessingSingleStatus(
                    document_id=doc_id,
                    new_document_uuid=job.get("new_document_uuid"),
                    status=status,
                    progress=job.get("progress"),
                    current_step=job.get("current_step"),
                    current_step_index=job.get("current_step_index"),
                    total_steps=job.get("total_steps"),
                    steps=steps,
                    completed_steps=job.get("completed_steps"),
                    error=job.get("error")
                ))
                
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1
                else:
                    in_progress += 1
        
        return BatchProcessingStatusResponse(
            total=len(document_ids),
            completed=completed,
            in_progress=in_progress,
            failed=failed,
            pending=pending,
            documents=statuses
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _to_response(self, doc: UnprocessedDocument) -> UnprocessedDocumentResponse:
        """Convert domain entity to API response"""
        # Use getter methods for flexible field access
        file_name = doc.get_file_name()
        file_type = doc.get_file_type()
        content = doc.get_content()
        
        # Generate content preview
        content_preview = None
        if doc.is_text_content():
            try:
                # Try to decode if base64
                try:
                    decoded = base64.b64decode(content).decode('utf-8')
                    content_preview = decoded[:200] + "..." if len(decoded) > 200 else decoded
                except Exception:
                    # Not base64, use directly
                    content_preview = content[:200] + "..." if len(content) > 200 else content
            except Exception:
                content_preview = "[Text content - preview unavailable]"
        else:
            content_preview = f"[Binary content: {file_type}]"
        
        return UnprocessedDocumentResponse(
            id=doc.id,
            patient_id=doc.patient_id,
            file_name=file_name,
            file_type=file_type,
            content_preview=content_preview,
            content_size=len(content) if content else 0,
            created_at=doc.created_at,
            document_date=doc.document_date,
            source_system=doc.source_system,
            metadata=doc.metadata
        )
    
    def _to_detail_response(self, doc: UnprocessedDocument) -> UnprocessedDocumentDetailResponse:
        """Convert domain entity to detailed API response with full content"""
        base_response = self._to_response(doc)
        return UnprocessedDocumentDetailResponse(
            **base_response.model_dump(),
            content=doc.get_content()
        )
