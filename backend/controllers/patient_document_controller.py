from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, List
import base64
import os
from services.patient_document_service import PatientDocumentService
from config.database import MongoDBConnection
from api.schemas.request_schemas import PatientDocumentUploadRequest
from api.schemas.response_schemas import PatientDocumentUploadResponse, PaginatedPatientDocumentResponse, PatientDocumentResponse, ErrorResponse
from utils.exceptions import NotFoundException, ValidationException, DatabaseException
import logging
import asyncio
import re
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patient Documents"])
from fastapi import Response

# File validation configuration
MAX_FILE_SIZE_MB = 50
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'text/plain',
    'text/xml',
    'application/xml',
    'application/json',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

def validate_file_content(file_content: str, filename: str) -> None:
    """Validate uploaded file content and size - optimized for performance"""
    try:
        # First validate base64 format without fully decoding for performance
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', file_content):
            raise ValidationException("Invalid base64 content format")
        
        # Calculate approximate file size from base64 length (faster than full decode)
        # Base64 encoding increases size by ~33%, so original size ≈ base64_length * 0.75
        estimated_size_mb = (len(file_content) * 0.75) / (1024 * 1024)
        if estimated_size_mb > MAX_FILE_SIZE_MB:
            raise ValidationException(f"File too large: {estimated_size_mb:.1f}MB. Maximum allowed: {MAX_FILE_SIZE_MB}MB")
        
        # Basic file extension validation (simplified)
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.doc', '.docx', '.tiff', '.xml', '.json'}
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise ValidationException(f"File extension not allowed: {file_ext}. Allowed: {', '.join(sorted(allowed_extensions))}")
            
        logger.info(f"File validation passed: {filename} ({file_ext}, ~{estimated_size_mb:.1f}MB)")
        
    except Exception as e:
        if isinstance(e, ValidationException):
            raise
        raise ValidationException(f"File validation failed: {str(e)}")

@router.get("")
async def list_patients():
    """
    List all distinct patient IDs found in the system.

    Returns a simple structure with items: [patient_id, ...] and total count.
    """
    try:
        with MongoDBConnection() as db:
            documents_collection = db["documents"]
            reports_collection = db["reports"]

            doc_patient_ids = documents_collection.distinct("patient_id")
            rep_patient_ids = reports_collection.distinct("patient_id")

            # Merge and sort unique IDs, filter out falsy values
            unique_ids = sorted({pid for pid in list(doc_patient_ids) + list(rep_patient_ids) if pid})

        return {"items": unique_ids, "total": len(unique_ids)}
    except Exception as e:
        logger.error(f"Unexpected error listing patients: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{patient_id}/document", response_model=PatientDocumentUploadResponse, status_code=201)
async def upload_patient_document(
    patient_id: str = Path(..., description="Patient ID"),
    request: PatientDocumentUploadRequest = None
):
    """
    Upload a document for a specific patient.
    
    This endpoint allows uploading documents for patients with either:
    - file_url: Path to the file
    - file: Base64 encoded file content
    
    The document will be stored with 'queued' status. Processing happens asynchronously.
    Use GET endpoints to check processing status and results.
    """
    start_time = time.time()
    
    try:
        logger.info(f"[UPLOAD-TIMING] Starting upload for patient {patient_id}")
        
        # Validate file content if provided
        if request and request.file and request.filename:
            validation_start = time.time()
            validate_file_content(request.file, request.filename)
            validation_time = time.time() - validation_start
            logger.info(f"[UPLOAD-TIMING] File validation took {validation_time:.3f}s")
        
        service_start = time.time()
        service = PatientDocumentService()
        document = service.upload_document(patient_id, request)
        service_time = time.time() - service_start
        logger.info(f"[UPLOAD-TIMING] Document service upload took {service_time:.3f}s")
        
        logger.info(f"Uploaded document with UUID: {document.uuid} for patient: {patient_id}")
        
        # Trigger document processing asynchronously (fire and forget)
        # Use asyncio.create_task with proper error handling to ensure it doesn't block
        async def process_with_error_handling():
            try:
                await service.process_document(document)
            except Exception as e:
                logger.error(f"Background processing failed for document {document.uuid}: {e}")
                # Update document status to failed
                try:
                    service.update_status(document.uuid, "failed", errors=[str(e)])
                except Exception as update_error:
                    logger.error(f"Failed to update document status: {update_error}")
        
        # Create task but don't await it - fire and forget
        task_start = time.time()
        asyncio.create_task(process_with_error_handling())
        task_time = time.time() - task_start
        logger.info(f"[UPLOAD-TIMING] Async task creation took {task_time:.3f}s")
        
        # Return immediately without waiting for processing
        response_start = time.time()
        response = PatientDocumentUploadResponse(
            uuid=document.uuid,
            patient_id=document.patient_id,
            type=document.type,
            source=document.source,
            status=document.status,  # This will be "queued"
            notes=document.notes,
            filename=document.filename,
            created_at=document.created_at,
            message=f"Document uploaded successfully for patient {patient_id}. Processing queued."
        )
        response_time = time.time() - response_start
        total_time = time.time() - start_time
        
        logger.info(f"[UPLOAD-TIMING] Response creation took {response_time:.3f}s")
        logger.info(f"[UPLOAD-TIMING] Total upload endpoint took {total_time:.3f}s")
        
        return response
        
    except ValidationException as e:
        total_time = time.time() - start_time
        logger.error(f"[UPLOAD-TIMING] Validation error after {total_time:.3f}s: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        total_time = time.time() - start_time
        logger.error(f"[UPLOAD-TIMING] Database error after {total_time:.3f}s: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[UPLOAD-TIMING] Unexpected error after {total_time:.3f}s: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{patient_id}/documents", response_model=PaginatedPatientDocumentResponse)
async def get_patient_documents(
    patient_id: str = Path(..., description="Patient ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size")
):
    """
    Get all documents for a specific patient with pagination.
    """
    try:
        service = PatientDocumentService()
        paginated_result = service.get_by_patient_id(patient_id, page, page_size)
        
        # Convert PatientDocument to PatientDocumentResponse format
        document_responses = []
        for doc in paginated_result.items:
            document_responses.append(PatientDocumentResponse(
                uuid=doc.uuid,
                patient_id=doc.patient_id,
                type=doc.type,
                source=doc.source,
                status=doc.status,
                notes=doc.notes,
                filename=doc.filename,
                file_path=doc.file_path,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                processing_started_at=doc.processing_started_at,
                processing_completed_at=doc.processing_completed_at,
                errors=doc.errors,
                parsed_document_uuid=doc.parsed_document_uuid,
                # Document Categorization Results
                document_category=doc.document_category,
                document_type=doc.document_type,
                categorization_completed_at=doc.categorization_completed_at,
                # Structured Data Extraction Results
                extracted_data=doc.extracted_data,
                extraction_metadata=doc.extraction_metadata,
                extraction_status=doc.extraction_status,
                extraction_completed_at=doc.extraction_completed_at,

            ))
        
        return PaginatedPatientDocumentResponse(
            total=paginated_result.total,
            page=paginated_result.page,
            page_size=paginated_result.page_size,
            items=document_responses
        )
        
    except DatabaseException as e:
        logger.error(f"Database error retrieving documents for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error retrieving documents for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{patient_id}/document/{document_uuid}")
async def get_patient_document(
    patient_id: str = Path(..., description="Patient ID"),
    document_uuid: str = Path(..., description="Document UUID")
):
    """
    Get a specific document for a patient.
    Handles patient_id changes gracefully - if patient_id was updated during processing,
    returns the document with a patient_id_changed flag.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        
        # Check if patient_id has changed (e.g., due to NumdosGR extraction)
        patient_id_changed = document.patient_id != patient_id
        
        if patient_id_changed:
            logger.info(f"Patient ID changed for document {document_uuid}: {patient_id} → {document.patient_id}")
        
        return PatientDocumentUploadResponse(
            uuid=document.uuid,
            patient_id=document.patient_id,  # Always return current patient_id
            type=document.type,
            source=document.source,
            status=document.status,
            notes=document.notes,
            filename=document.filename,
            created_at=document.created_at,
            message=f"Document retrieved successfully" + (f" (patient_id updated to {document.patient_id})" if patient_id_changed else ""),
            extracted_data=document.extracted_data,
            extraction_status=document.extraction_status,
            # Include patient_id change tracking
            patient_id_changed=patient_id_changed,
            original_patient_id=patient_id if patient_id_changed else None
        )
        
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        logger.error(f"Database error retrieving document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error retrieving document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{patient_id}/document/{document_uuid}/process", status_code=202)
async def trigger_document_processing(
    patient_id: str = Path(..., description="Patient ID"),
    document_uuid: str = Path(..., description="Document UUID")
):
    """
    Manually trigger processing for a specific document.
    
    This is useful for retrying failed processing or processing documents
    that were uploaded but not automatically processed.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        
        # Verify the document belongs to the specified patient
        if document.patient_id != patient_id:
            raise HTTPException(status_code=404, detail=f"Document {document_uuid} not found for patient {patient_id}")
        
        # Check if document is in a state that can be processed
        if document.status in ["processing"]:
            raise HTTPException(status_code=409, detail="Document is already being processed")
        
        # Trigger processing asynchronously
        import asyncio
        asyncio.create_task(service.process_document(document))
        
        logger.info(f"Triggered processing for document {document_uuid}")
        
        return {
            "message": f"Processing triggered for document {document_uuid}",
            "document_uuid": document_uuid,
            "patient_id": patient_id,
            "status": "processing_queued"
        }
        
    except HTTPException:
        raise
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error triggering processing for document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{patient_id}/document/{document_uuid}/ocr", status_code=200)
async def get_document_ocr_results(
    patient_id: str = Path(..., description="Patient ID"),
    document_uuid: str = Path(..., description="Document UUID")
):
    """
    Get OCR results (extracted text) for a specific document.
    
    Returns the raw OCR text and metadata if OCR processing has been completed.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        
        # Verify the document belongs to the specified patient
        if document.patient_id != patient_id:
            raise HTTPException(status_code=404, detail=f"Document {document_uuid} not found for patient {patient_id}")
        
        # Check if OCR has been completed
        if not document.ocr_text:
            raise HTTPException(status_code=404, detail="OCR results not available for this document")
        
        return {
            "document_uuid": document_uuid,
            "patient_id": patient_id,
            "ocr_text": document.ocr_text,
            "character_count": document.character_count,
            "word_count": document.word_count,
            "ocr_completed_at": document.ocr_completed_at,
            "ocr_metadata": document.ocr_metadata
        }
        
    except HTTPException:
        raise
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error retrieving OCR results for document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{patient_id}/documents/by-filename/{filename}", response_model=PatientDocumentUploadResponse)
async def get_patient_document_by_filename(
    patient_id: str = Path(..., description="Patient ID"),
    filename: str = Path(..., description="Document filename")
):
    """
    Get a specific document for a patient by filename.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_filename(patient_id, filename)
        
        return PatientDocumentUploadResponse(
            uuid=document.uuid,
            patient_id=document.patient_id,
            type=document.type,
            source=document.source,
            status=document.status,
            notes=document.notes,
            filename=document.filename,
            created_at=document.created_at,
            message=f"Document retrieved successfully",
            extracted_data=document.extracted_data,
            extraction_status=document.extraction_status,
            # Include file content and OCR text for source viewer
            file_content=document.file_content,
            ocr_text=document.ocr_text,
            character_count=document.character_count,
            word_count=document.word_count
        )
        
    except NotFoundException as e:
        logger.warning(f"Document not found: {filename} for patient {patient_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        logger.error(f"Database error retrieving document {filename}: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error retrieving document {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{patient_id}/document/{document_uuid}/", status_code=200)
async def get_document_normalization_results(
    patient_id: str = Path(..., description="Patient ID"),
    document_uuid: str = Path(..., description="Document UUID")
):
    """
    Get results for a specific document.
    
    Returns the normalized text and metadata if normalization processing has been completed.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        
        # Verify the document belongs to the specified patient
        if document.patient_id != patient_id:
            raise HTTPException(status_code=404, detail=f"Document {document_uuid} not found for patient {patient_id}")
        
        # Check if normalization has been completed
        if not document.normalized_text:
            raise HTTPException(status_code=404, detail="Normalization results not available for this document")
        
        return {
            "document_uuid": document_uuid,
            "patient_id": patient_id,
            "normalized_text": document.normalized_text,
            "normalization_status": document.normalization_status,
            "normalized_character_count": document.normalized_character_count,
            "normalized_word_count": document.normalized_word_count,
            "normalization_completed_at": document.normalization_completed_at,
            "normalization_metadata": document.normalization_metadata,
            "original_character_count": document.character_count,
            "original_word_count": document.word_count
        }
        
    except HTTPException:
        raise
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error retrieving normalization results for document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{patient_id}/document/{document_uuid}", status_code=204)
async def delete_patient_document(
    patient_id: str = Path(..., description="Patient ID"),
    document_uuid: str = Path(..., description="Document UUID")
):
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        if document.patient_id != patient_id:
            raise NotFoundException(f"Document {document_uuid} not found for patient {patient_id}")
        service.delete_document(document_uuid)
        return Response(status_code=204)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error deleting document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# NEW UUID-BASED ENDPOINTS (Decoupled from patient_id)
# ============================================================================

@router.post("/documents", response_model=PatientDocumentUploadResponse, status_code=201)
async def upload_document_uuid_based(
    request: PatientDocumentUploadRequest
):
    """
    Upload a document WITHOUT specifying patient_id in the URL.
    
    This is the UUID-first approach:
    - Document gets a unique UUID for tracking
    - Patient ID will be extracted during processing (NumdosGR)
    - If extraction fails, document gets status 'requires_manual_input'
    - User can then manually assign patient_id via PATCH endpoint
    
    Returns:
    - uuid: Use this to track upload and processing progress
    - patient_id: null initially, populated after extraction
    - status: 'queued' initially
    """
    start_time = time.time()
    
    try:
        logger.info(f"[UPLOAD-UUID] Starting UUID-based upload")
        
        # Validate file content if provided
        if request and request.file and request.filename:
            validation_start = time.time()
            validate_file_content(request.file, request.filename)
            validation_time = time.time() - validation_start
            logger.info(f"[UPLOAD-UUID] File validation took {validation_time:.3f}s")
        
        service_start = time.time()
        service = PatientDocumentService()
        
        # Upload with patient_id = None (will be extracted during processing)
        document = service.upload_document(
            patient_id=None,  # UUID-first: patient_id extracted later
            request=request
        )
        service_time = time.time() - service_start
        logger.info(f"[UPLOAD-UUID] Document service upload took {service_time:.3f}s")
        
        logger.info(f"[UPLOAD-UUID] Uploaded document with UUID: {document.uuid} (patient_id will be extracted)")
        
        # Trigger document processing asynchronously
        async def process_with_error_handling():
            try:
                await service.process_document(document)
            except Exception as e:
                logger.error(f"Background processing failed for document {document.uuid}: {e}")
                try:
                    service.update_status(document.uuid, "failed", errors=[str(e)])
                except Exception as update_error:
                    logger.error(f"Failed to update document status: {update_error}")
        
        # Fire and forget
        asyncio.create_task(process_with_error_handling())
        
        total_time = time.time() - start_time
        logger.info(f"[UPLOAD-UUID] Total upload endpoint took {total_time:.3f}s")
        
        return PatientDocumentUploadResponse(
            uuid=document.uuid,
            patient_id=None,  # Not yet known
            type=document.type,
            source=document.source,
            status=document.status,  # "queued"
            notes=document.notes,
            filename=document.filename,
            created_at=document.created_at,
            message="Document uploaded successfully. Patient ID will be extracted during processing."
        )
        
    except ValidationException as e:
        total_time = time.time() - start_time
        logger.error(f"[UPLOAD-UUID] Validation error after {total_time:.3f}s: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[UPLOAD-UUID] Unexpected error after {total_time:.3f}s: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_uuid}", response_model=PatientDocumentUploadResponse)
async def get_document_by_uuid_only(
    document_uuid: str = Path(..., description="Document UUID")
):
    """
    Get document by UUID only - no patient_id required.
    Used for polling during processing when patient_id is not yet known.
    
    This endpoint allows tracking document processing status without knowing
    the final patient_id, which may be extracted during processing.
    """
    try:
        service = PatientDocumentService()
        document = service.get_by_uuid(document_uuid)
        
        return PatientDocumentUploadResponse(
            uuid=document.uuid,
            patient_id=document.patient_id,  # May be None if not yet extracted
            type=document.type,
            source=document.source,
            status=document.status,
            notes=document.notes,
            filename=document.filename,
            created_at=document.created_at,
            message=f"Document retrieved successfully",
            extracted_data=document.extracted_data,
            extraction_status=document.extraction_status,
            file_content=document.file_content,
            ocr_text=document.ocr_text,
            character_count=document.character_count,
            word_count=document.word_count
        )
        
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/documents/{document_uuid}/patient-id", response_model=PatientDocumentUploadResponse)
async def assign_patient_id_manually(
    document_uuid: str = Path(..., description="Document UUID"),
    patient_id: str = Body(..., embed=True, description="Patient ID to assign")
):
    """
    Manually assign a patient_id to a document when automatic extraction fails.
    
    This endpoint is used when:
    - Document status is 'requires_manual_input'
    - Patient ID could not be extracted from the document
    - User needs to manually provide the patient identifier
    
    Changes document status from 'requires_manual_input' to 'done'.
    """
    try:
        from api.schemas.request_schemas import DocumentStatus
        
        service = PatientDocumentService()
        
        # Get document
        document = service.get_by_uuid(document_uuid)
        
        # Validate document is in correct state
        if document.status != DocumentStatus.REQUIRES_MANUAL_INPUT:
            raise HTTPException(
                status_code=400, 
                detail=f"Document status is '{document.status}'. Can only assign patient_id to documents with status 'requires_manual_input'"
            )
        
        # Validate patient_id is not empty
        if not patient_id or not patient_id.strip():
            raise HTTPException(status_code=400, detail="Patient ID cannot be empty")
        
        # Update patient_id
        logger.info(f"Manually assigning patient_id={patient_id} to document {document_uuid}")
        updated_document = service.update_patient_id_from_extraction(
            document_uuid, 
            patient_id.strip()
        )
        
        # Update status to done
        service.update_status(document_uuid, DocumentStatus.DONE)
        
        # Reload document to get updated status
        updated_document = service.get_by_uuid(document_uuid)
        
        return PatientDocumentUploadResponse(
            uuid=updated_document.uuid,
            patient_id=updated_document.patient_id,
            type=updated_document.type,
            source=updated_document.source,
            status=updated_document.status,
            notes=updated_document.notes,
            filename=updated_document.filename,
            created_at=updated_document.created_at,
            message=f"Patient ID assigned manually: {patient_id}",
            extracted_data=updated_document.extracted_data,
            extraction_status=updated_document.extraction_status
        )
        
    except NotFoundException as e:
        logger.warning(f"Document not found: {document_uuid}")
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning patient_id to document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents", response_model=List[PatientDocumentUploadResponse])
async def list_documents_by_status(
    status: Optional[str] = Query(None, description="Filter by status (queued, processing, done, failed, requires_manual_input)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """
    List documents, optionally filtered by status.
    
    This endpoint is useful for:
    - Dashboard showing documents needing manual input
    - Monitoring processing queue
    - Batch upload progress tracking
    
    No patient_id required - returns documents across all patients.
    """
    try:
        db = MongoDBConnection.get_db()
        collection = db["documents"]
        
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Execute query with limit
        documents = list(
            collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        # Convert to response models
        results = []
        for doc in documents:
            results.append(
                PatientDocumentUploadResponse(
                    uuid=doc.get("uuid"),
                    patient_id=doc.get("patient_id"),
                    type=doc.get("type", "other"),
                    source=doc.get("source"),
                    status=doc.get("status", "queued"),
                    notes=doc.get("notes"),
                    filename=doc.get("filename"),
                    created_at=doc.get("created_at"),
                    message=f"Document {doc.get('status', 'unknown')}",
                    extracted_data=doc.get("extracted_data"),
                    extraction_status=doc.get("extraction_status")
                )
            )
        
        logger.info(f"Listed {len(results)} documents" + (f" with status={status}" if status else ""))
        return results
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
