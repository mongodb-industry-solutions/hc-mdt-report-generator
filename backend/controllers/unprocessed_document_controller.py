"""
Unprocessed Document Controller

API endpoints for managing unprocessed documents from external EHR systems.
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from typing import List, Optional
import logging

from services.unprocessed_document_service import UnprocessedDocumentService
from api.schemas.unprocessed_document_schemas import (
    UnprocessedDocumentResponse,
    UnprocessedDocumentDetailResponse,
    UnprocessedDocumentListResponse,
    ProcessDocumentsRequest,
    ProcessDocumentsResponse,
    BatchProcessingStatusResponse,
    UnprocessedCountsResponse
)
from utils.exceptions import NotFoundException, ValidationException, DatabaseException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Unprocessed Documents"])


# ============================================================================
# LIST & COUNT ENDPOINTS
# ============================================================================

@router.get(
    "/unprocessed-documents/counts",
    response_model=UnprocessedCountsResponse,
    summary="Get unprocessed document counts for all patients"
)
async def get_unprocessed_counts():
    """
    Get counts of unprocessed documents grouped by patient ID.
    
    Useful for displaying badges in the UI showing how many documents
    each patient has waiting to be processed.
    """
    try:
        service = UnprocessedDocumentService()
        return service.get_counts_by_patient()
    except DatabaseException as e:
        logger.error(f"Database error getting unprocessed counts: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error getting unprocessed counts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{patient_id}/unprocessed-documents",
    response_model=UnprocessedDocumentListResponse,
    summary="Get unprocessed documents for a patient"
)
async def get_patient_unprocessed_documents(
    patient_id: str = Path(..., description="Patient ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get paginated list of unprocessed documents for a specific patient.
    
    Returns documents that are waiting in the unprocessed_documents collection
    to be processed through the standard document pipeline.
    """
    try:
        service = UnprocessedDocumentService()
        return service.get_by_patient_id(
            patient_id=patient_id,
            page=page,
            page_size=page_size
        )
    except DatabaseException as e:
        logger.error(f"Database error getting unprocessed documents for {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error getting unprocessed documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{patient_id}/unprocessed-documents/count",
    summary="Get count of unprocessed documents for a patient"
)
async def get_patient_unprocessed_count(
    patient_id: str = Path(..., description="Patient ID")
):
    """
    Get the count of unprocessed documents for a specific patient.
    
    Useful for showing badges in the UI.
    """
    try:
        service = UnprocessedDocumentService()
        count = service.get_patient_count(patient_id)
        return {"patient_id": patient_id, "count": count}
    except DatabaseException as e:
        logger.error(f"Database error getting unprocessed count for {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error getting unprocessed count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# SINGLE DOCUMENT ENDPOINTS
# ============================================================================

@router.get(
    "/{patient_id}/unprocessed-documents/{document_id}",
    response_model=UnprocessedDocumentDetailResponse,
    summary="Get a single unprocessed document"
)
async def get_unprocessed_document(
    patient_id: str = Path(..., description="Patient ID"),
    document_id: str = Path(..., description="Unprocessed document ID")
):
    """
    Get a single unprocessed document with full content.
    
    Returns complete document details including the raw content.
    """
    try:
        service = UnprocessedDocumentService()
        document = service.get_by_id(document_id)
        
        # Verify patient_id matches
        if document.patient_id != patient_id:
            raise HTTPException(
                status_code=404, 
                detail=f"Document {document_id} not found for patient {patient_id}"
            )
        
        return document
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except DatabaseException as e:
        logger.error(f"Database error getting unprocessed document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error getting unprocessed document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# PROCESSING ENDPOINTS
# ============================================================================

@router.post(
    "/{patient_id}/unprocessed-documents/process",
    response_model=ProcessDocumentsResponse,
    status_code=202,
    summary="Process selected unprocessed documents"
)
async def process_unprocessed_documents(
    patient_id: str = Path(..., description="Patient ID"),
    request: ProcessDocumentsRequest = Body(..., description="Documents to process")
):
    """
    Start processing selected unprocessed documents.
    
    This endpoint:
    1. Validates the selected documents exist and belong to the patient
    2. Converts each document to the standard format
    3. Triggers async processing through the normal pipeline
    4. Returns tracking information for monitoring progress
    
    Documents are removed from the unprocessed collection upon successful processing.
    Failed documents remain in the unprocessed collection for retry.
    
    **Note**: Processing happens asynchronously. Use the status endpoint to track progress.
    """
    try:
        service = UnprocessedDocumentService()
        
        # Validate request
        if not request.document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
        
        if len(request.document_ids) > 50:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 50 documents can be processed at once"
            )
        
        result = await service.process_documents(
            patient_id=patient_id,
            document_ids=request.document_ids
        )
        
        return result
        
    except HTTPException:
        raise
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseException as e:
        logger.error(f"Database error processing documents: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error processing documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{patient_id}/unprocessed-documents/process/status",
    response_model=BatchProcessingStatusResponse,
    summary="Get processing status for documents"
)
async def get_processing_status(
    patient_id: str = Path(..., description="Patient ID"),
    request: ProcessDocumentsRequest = Body(..., description="Documents to check status")
):
    """
    Get the processing status of previously submitted documents.
    
    Use this endpoint to poll for completion after calling the process endpoint.
    
    Status values:
    - `pending`: Document is waiting to start processing
    - `processing`: Document is currently being processed
    - `completed`: Document has been successfully processed and moved to documents collection
    - `failed`: Processing failed (document remains in unprocessed collection)
    """
    try:
        service = UnprocessedDocumentService()
        return service.get_processing_status(request.document_ids)
    except DatabaseException as e:
        logger.error(f"Database error getting processing status: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error getting processing status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post(
    "/{patient_id}/unprocessed-documents/process-all",
    response_model=ProcessDocumentsResponse,
    status_code=202,
    summary="Process all unprocessed documents for a patient"
)
async def process_all_unprocessed_documents(
    patient_id: str = Path(..., description="Patient ID"),
    limit: int = Query(50, ge=1, le=50, description="Maximum documents to process")
):
    """
    Start processing all unprocessed documents for a patient (up to limit).
    
    This is a convenience endpoint that fetches all unprocessed document IDs
    for the patient and processes them in batch.
    
    **Note**: Limited to 50 documents per call to prevent overload.
    """
    try:
        service = UnprocessedDocumentService()
        
        # Get all document IDs for the patient
        documents_response = service.get_by_patient_id(
            patient_id=patient_id,
            page=1,
            page_size=limit
        )
        
        if not documents_response.items:
            return ProcessDocumentsResponse(
                message="No unprocessed documents found for patient",
                total_requested=0,
                processing_started=0,
                failed_to_start=0,
                processing_jobs=[],
                errors=[]
            )
        
        # Extract document IDs
        document_ids = [doc.id for doc in documents_response.items]
        
        # Process them
        result = await service.process_documents(
            patient_id=patient_id,
            document_ids=document_ids
        )
        
        return result
        
    except DatabaseException as e:
        logger.error(f"Database error processing all documents: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error processing all documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
