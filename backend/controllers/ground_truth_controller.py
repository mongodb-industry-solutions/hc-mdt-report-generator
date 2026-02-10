"""
Ground Truth Controller

API endpoints for:
1. Uploading ground truth PDFs with OCR extraction
2. Updating/editing extracted GT entities
3. Running evaluations
4. Retrieving evaluation results

UPDATED: Now uses separate collections for ground_truths and evaluations.
"""

import json
import asyncio
import logging
import base64
from datetime import datetime, timezone
from typing import Optional, List, AsyncGenerator

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from services.gt_ocr_service import GTOCRService
from services.gt_entity_extraction_service import GTEntityExtractionService
from services.evaluation_service import EvaluationService
from repositories.report_repository import ReportRepository
from repositories.ground_truth_repository import GroundTruthRepository
from repositories.evaluation_repository import EvaluationRepository
from domain.entities.ground_truth import GroundTruth, GroundTruthPDF, GroundTruthEntity
from utils.exceptions import NotFoundException, ValidationException

router = APIRouter(prefix="/patients", tags=["Ground Truth & Evaluation"])

logger = logging.getLogger(__name__)

# Repositories
report_repo = ReportRepository()
gt_repo = GroundTruthRepository()
eval_repo = EvaluationRepository()

# Services
gt_ocr_service = GTOCRService()
gt_extraction_service = GTEntityExtractionService()
evaluation_service = EvaluationService()


# Request/Response Models
class GTEntityUpdate(BaseModel):
    entity_name: str
    value: Optional[str] = None


class GTEntitiesUpdateRequest(BaseModel):
    entities: List[GTEntityUpdate]


class EvaluationResponse(BaseModel):
    status: str
    evaluated_at: Optional[str] = None
    summary: Optional[dict] = None
    details: Optional[List[dict]] = None
    worst_entities: Optional[List[dict]] = None


# ============================================
# ENDPOINT 1: Upload GT PDF with OCR Extraction
# ============================================

@router.post("/{patient_id}/reports/{report_uuid}/ground-truth")
async def upload_ground_truth(
    patient_id: str,
    report_uuid: str,
    file: UploadFile = File(...),
    ocr_engine: str = Form(default="easyocr", description="OCR engine: 'mistral' or 'easyocr'"),
    llm_provider: Optional[str] = Form(default=None, description="LLM provider. If None, uses LLM_PROVIDER env var. Options: 'mistral', 'ollama', 'gpt_open'")
):
    """
    Upload a ground truth PDF and extract entities.
    
    Saves to ground_truths collection (separate from reports).
    
    Returns SSE stream with progress updates:
    - UPLOADING: File being uploaded
    - OCR_RUNNING: OCR extraction in progress
    - EXTRACTING_ENTITIES: LLM entity extraction
    - COMPLETED: Entities extracted and saved
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID to attach ground truth to
        file: PDF file upload
        ocr_engine: OCR engine to use ("mistral" or "easyocr")
        llm_provider: LLM provider for entity extraction ("mistral" or "gpt_open")
    """
    
    async def generate_progress() -> AsyncGenerator[str, None]:
        try:
            # Validate report exists and belongs to patient
            yield _sse_event("STARTED", 0, "Starting ground truth upload...")
            
            try:
                report = report_repo.get_by_uuid(report_uuid)
                if report.patient_id != patient_id:
                    raise NotFoundException(f"Report {report_uuid} not found for patient {patient_id}")
            except NotFoundException:
                yield _sse_event("FAILED", 0, f"Report {report_uuid} not found")
                return
            
            # Validate OCR engine
            if ocr_engine not in ["mistral", "easyocr"]:
                yield _sse_event("FAILED", 0, f"Invalid OCR engine: {ocr_engine}")
                return
            
            # Step 1: Read PDF content
            yield _sse_event("UPLOADING", 10, "Reading PDF file...")
            
            pdf_content = await file.read()
            file_size = len(pdf_content)
            
            if file_size > 20 * 1024 * 1024:  # 20MB limit
                yield _sse_event("FAILED", 10, "File too large. Maximum size is 20MB.")
                return
            
            # Convert to base64 for inline storage
            pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")
            
            yield _sse_event("UPLOADING", 20, "PDF read successfully")
            
            # Step 2: Run OCR
            yield _sse_event("OCR_RUNNING", 30, f"Running OCR with {ocr_engine}...")
            
            try:
                ocr_text, page_count = await gt_ocr_service.extract_text(
                    pdf_content=pdf_content,
                    ocr_engine=ocr_engine,
                    languages=["fr", "en"]
                )
            except Exception as e:
                logger.error(f"OCR failed: {e}")
                yield _sse_event("FAILED", 30, f"OCR extraction failed: {str(e)}")
                return
            
            yield _sse_event("OCR_RUNNING", 50, f"OCR completed: {len(ocr_text)} characters from {page_count} pages")
            
            # Step 3: Extract entities using LLM
            # Use the same template that was used to generate the report for consistency
            template_id = getattr(report, 'template_id', None) or report.metadata.get('template_id') if report.metadata else None
            yield _sse_event("EXTRACTING_ENTITIES", 60, f"Extracting entities with {llm_provider} (template_id: {template_id or 'active'})...")
            
            try:
                extracted_entities = await gt_extraction_service.extract_entities(
                    ocr_text, 
                    template_id=template_id,  # Pass template_id for consistency
                    llm_provider=llm_provider  # Pass user's LLM selection
                )
            except Exception as e:
                logger.error(f"Entity extraction failed: {e}")
                yield _sse_event("FAILED", 60, f"Entity extraction failed: {str(e)}")
                return
            
            yield _sse_event("EXTRACTING_ENTITIES", 80, f"Extracted {len(extracted_entities)} entities")
            
            # Step 4: Save ground truth to ground_truths collection
            yield _sse_event("SAVING", 90, "Saving ground truth to database...")
            
            # Create GroundTruth object with new schema
            gt_entities = [
                GroundTruthEntity(
                    entity_name=e["entity_name"],
                    value=e.get("value"),
                    source=e.get("source", "extracted"),
                    confidence=e.get("confidence", 0.9)
                )
                for e in extracted_entities
            ]
            
            ground_truth = GroundTruth(
                patient_id=patient_id,
                report_uuid=report_uuid,
                ocr_engine=ocr_engine,
                original_pdf=GroundTruthPDF(
                    filename=file.filename or f"gt_{report_uuid}.pdf",
                    file_content=pdf_base64,
                    pages=page_count,
                    file_size=file_size
                ),
                ocr_text=ocr_text,
                entities=gt_entities,
                status="COMPLETED"
            )
            
            # Save to ground_truths collection
            saved_gt = gt_repo.create(ground_truth)
            logger.info(f"Ground truth saved: {saved_gt.uuid}")
            
            # Step 5: Complete - send completion event
            logger.info(f"Sending COMPLETED event with {len(extracted_entities)} entities")
            completion_data = {
                "status": "COMPLETED",
                "progress": 100,
                "message": "Ground truth extraction completed",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "ground_truth_uuid": saved_gt.uuid,
                    "entity_count": len(extracted_entities),
                    "page_count": page_count,
                    "ocr_engine": ocr_engine,
                    "entities": extracted_entities
                }
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
            # Small delay to ensure SSE event is flushed in production
            await asyncio.sleep(0.1)
            logger.info("COMPLETED event sent successfully")
            
        except Exception as e:
            logger.error(f"GT upload failed: {e}")
            yield _sse_event("FAILED", 0, f"Unexpected error: {str(e)}")
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================
# ENDPOINT 2: Update GT Entities (User Edits)
# ============================================

@router.put("/{patient_id}/reports/{report_uuid}/ground-truth")
async def update_ground_truth_entities(
    patient_id: str,
    report_uuid: str,
    request: GTEntitiesUpdateRequest
):
    """
    Update ground truth entities after user verification/editing.
    Updates the latest GT for the given report.
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID
        request: Updated entities list
        
    Returns:
        Updated entity count
    """
    try:
        # Get latest ground truth for this report
        ground_truth = gt_repo.get_latest_by_report(report_uuid)
        
        if not ground_truth:
            raise ValidationException("No ground truth exists for this report. Upload a GT PDF first.")
        
        if ground_truth.patient_id != patient_id:
            raise NotFoundException(f"Ground truth not found for patient {patient_id}")
        
        # Build entity map from request
        update_map = {e.entity_name: e.value for e in request.entities}
        
        # Update entities
        updated_entities = []
        for entity in ground_truth.entities:
            entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else dict(entity)
            name = entity_dict.get("entity_name")
            if name in update_map:
                entity_dict["value"] = update_map[name]
                entity_dict["source"] = "manual"  # Mark as user-edited
                entity_dict["confidence"] = 1.0  # User-provided = full confidence
            updated_entities.append(entity_dict)
        
        # Add any new entities not in original list
        existing_names = {e.get("entity_name") for e in updated_entities}
        for name, value in update_map.items():
            if name not in existing_names:
                updated_entities.append({
                    "entity_name": name,
                    "value": value,
                    "source": "manual",
                    "confidence": 1.0
                })
        
        # Save updated ground truth
        gt_repo.update(ground_truth.uuid, {
            "entities": updated_entities,
            "updated_at": datetime.now(timezone.utc)
        })
        
        return {
            "status": "updated",
            "ground_truth_uuid": ground_truth.uuid,
            "entity_count": len(updated_entities),
            "message": "Ground truth entities updated successfully"
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update GT entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT 3: Get Ground Truth Data
# ============================================

@router.get("/{patient_id}/reports/{report_uuid}/ground-truth")
async def get_ground_truth(patient_id: str, report_uuid: str):
    """
    Get latest ground truth data for a report.
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID
        
    Returns:
        Ground truth data including entities and metadata
    """
    try:
        # Get latest ground truth for this report
        ground_truth = gt_repo.get_latest_by_report(report_uuid)
        
        if not ground_truth:
            return {
                "status": "not_found",
                "message": "No ground truth uploaded for this report"
            }
        
        if ground_truth.patient_id != patient_id:
            raise NotFoundException(f"Ground truth not found for patient {patient_id}")
        
        return {
            "status": "found",
            "ground_truth": {
                "uuid": ground_truth.uuid,
                "uploaded_at": ground_truth.created_at.isoformat() if ground_truth.created_at else None,
                "ocr_engine": ground_truth.ocr_engine,
                "page_count": ground_truth.original_pdf.pages if ground_truth.original_pdf else 0,
                "entity_count": len(ground_truth.entities),
                "entities": [e.model_dump() for e in ground_truth.entities]
            }
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get GT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT 4: Get GT PDF Preview
# ============================================

@router.get("/{patient_id}/reports/{report_uuid}/ground-truth/pdf")
async def get_ground_truth_pdf(patient_id: str, report_uuid: str):
    """
    Get the original ground truth PDF file.
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID
        
    Returns:
        PDF file stream
    """
    try:
        # Get latest ground truth for this report
        ground_truth = gt_repo.get_latest_by_report(report_uuid)
        
        if not ground_truth:
            raise NotFoundException("No ground truth uploaded for this report")
        
        if ground_truth.patient_id != patient_id:
            raise NotFoundException(f"Ground truth not found for patient {patient_id}")
        
        if not ground_truth.original_pdf or not ground_truth.original_pdf.file_content:
            raise NotFoundException("Ground truth PDF file not found")
        
        # Decode base64 to binary
        pdf_content = base64.b64decode(ground_truth.original_pdf.file_content)
        
        filename = ground_truth.original_pdf.filename or f"gt_{report_uuid}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get GT PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT 5: Run Evaluation
# ============================================

@router.post("/{patient_id}/reports/{report_uuid}/evaluate")
async def run_evaluation(
    patient_id: str, 
    report_uuid: str,
    llm_provider: Optional[str] = Query(default=None, description="LLM provider. If None, uses LLM_PROVIDER env var. Options: 'mistral', 'ollama', 'gpt_open'")
):
    """
    Run evaluation comparing generated entities against ground truth.
    
    Saves result to evaluations collection.
    
    Returns SSE stream with progress and final results.
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID
        llm_provider: LLM provider for semantic scoring ("mistral" or "gpt_open")
    """
    
    async def generate_progress() -> AsyncGenerator[str, None]:
        try:
            yield _sse_event("STARTED", 0, "Starting evaluation...")
            
            # Validate report
            try:
                report = report_repo.get_by_uuid(report_uuid)
                if report.patient_id != patient_id:
                    raise NotFoundException(f"Report {report_uuid} not found for patient {patient_id}")
            except NotFoundException:
                yield _sse_event("FAILED", 0, f"Report {report_uuid} not found")
                return
            
            # Check ground truth exists
            ground_truth = gt_repo.get_latest_by_report(report_uuid)
            if not ground_truth:
                yield _sse_event("FAILED", 0, "No ground truth uploaded. Please upload GT PDF first.")
                return
            
            # Check report has extracted entities
            if not report.content or not report.content.get("ner_results", {}).get("entities"):
                yield _sse_event("FAILED", 0, "Report has no extracted entities to evaluate")
                return
            
            yield _sse_event("LOADING_DATA", 20, "Loading entities...")
            
            # Run evaluation
            yield _sse_event("COMPARING", 40, "Comparing entities...")
            yield _sse_event("LLM_SCORING", 60, f"Getting LLM semantic scores with {llm_provider}...")
            
            try:
                evaluation = await evaluation_service.evaluate_report(
                    report_uuid=report_uuid,
                    patient_id=patient_id,
                    ground_truth_uuid=ground_truth.uuid,
                    llm_provider=llm_provider  # Pass user's LLM selection
                )
            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                yield _sse_event("FAILED", 60, f"Evaluation failed: {str(e)}")
                return
            
            yield _sse_event("SAVING", 90, "Saving results...")
            
            # Return completion with results
            logger.info(f"Sending evaluation COMPLETED event: {evaluation.uuid}")
            completion_data = {
                "status": "COMPLETED",
                "progress": 100,
                "message": "Evaluation completed successfully",
                "timestamp": datetime.now().isoformat(),
                "evaluation_uuid": evaluation.uuid,
                "summary": evaluation.summary.model_dump() if evaluation.summary else None,
                "worst_entities": [w.model_dump() for w in evaluation.worst_entities] if evaluation.worst_entities else []
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
            # Small delay to ensure SSE event is flushed in production
            await asyncio.sleep(0.1)
            logger.info("Evaluation COMPLETED event sent successfully")
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            yield _sse_event("FAILED", 0, f"Unexpected error: {str(e)}")
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ============================================
# ENDPOINT 6: Get Evaluation Results
# ============================================

@router.get("/{patient_id}/reports/{report_uuid}/evaluation")
async def get_evaluation(patient_id: str, report_uuid: str):
    """
    Get latest evaluation results for a report.
    
    Args:
        patient_id: Patient identifier
        report_uuid: Report UUID
        
    Returns:
        Evaluation results including summary and per-entity details
    """
    try:
        # Validate report belongs to patient
        report = report_repo.get_by_uuid(report_uuid)
        if report.patient_id != patient_id:
            raise NotFoundException(f"Report {report_uuid} not found for patient {patient_id}")
        
        # Get latest evaluation for this report
        evaluation = eval_repo.get_latest_by_report(report_uuid)
        
        if not evaluation:
            return {
                "status": "not_evaluated",
                "message": "Report has not been evaluated yet"
            }
        
        # Also get ground truth info
        ground_truth = gt_repo.get_latest_by_report(report_uuid)
        gt_info = None
        if ground_truth:
            gt_info = {
                "uuid": ground_truth.uuid,
                "uploaded_at": ground_truth.created_at.isoformat() if ground_truth.created_at else None,
                "ocr_engine": ground_truth.ocr_engine,
                "entity_count": len(ground_truth.entities)
            }
        
        return {
            "status": evaluation.status,
            "evaluation_uuid": evaluation.uuid,
            "evaluated_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
            "llm_model": evaluation.llm_model,
            "summary": evaluation.summary.model_dump() if evaluation.summary else None,
            "details": [d.model_dump() for d in evaluation.details] if evaluation.details else [],
            "worst_entities": [w.model_dump() for w in evaluation.worst_entities] if evaluation.worst_entities else [],
            "ground_truth_info": gt_info
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT 7: Get All GTs for a Patient
# ============================================

@router.get("/{patient_id}/ground-truths")
async def get_patient_ground_truths(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    Get all ground truths for a patient.
    
    Args:
        patient_id: Patient identifier
        limit: Maximum number to return (default 50)
        
    Returns:
        List of ground truths, newest first
    """
    try:
        ground_truths = gt_repo.get_by_patient(patient_id, limit)
        
        return {
            "patient_id": patient_id,
            "count": len(ground_truths),
            "ground_truths": [
                {
                    "uuid": gt.uuid,
                    "report_uuid": gt.report_uuid,
                    "created_at": gt.created_at.isoformat() if gt.created_at else None,
                    "ocr_engine": gt.ocr_engine,
                    "entity_count": len(gt.entities),
                    "status": gt.status
                }
                for gt in ground_truths
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get patient GTs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT 8: Get All Evaluations for a Patient
# ============================================

@router.get("/{patient_id}/evaluations")
async def get_patient_evaluations(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """
    Get all evaluations for a patient.
    
    Args:
        patient_id: Patient identifier
        limit: Maximum number to return (default 50)
        
    Returns:
        List of evaluations, newest first
    """
    try:
        evaluations = eval_repo.get_by_patient(patient_id, limit)
        
        return {
            "patient_id": patient_id,
            "count": len(evaluations),
            "evaluations": [
                {
                    "uuid": ev.uuid,
                    "report_uuid": ev.report_uuid,
                    "ground_truth_uuid": ev.ground_truth_uuid,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "status": ev.status,
                    "summary": ev.summary.model_dump() if ev.summary else None
                }
                for ev in evaluations
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get patient evaluations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Helper Functions
# ============================================

def _sse_event(status: str, progress: int, message: str) -> str:
    """Create an SSE event string."""
    event = {
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    return f"data: {json.dumps(event)}\n\n"
