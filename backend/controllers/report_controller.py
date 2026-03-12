import json
import asyncio
import sys
from datetime import datetime, UTC
from typing import List, Optional, AsyncGenerator
import logging
import uuid

from fastapi import APIRouter, Query, HTTPException
from fastapi import Response
from fastapi.responses import StreamingResponse

from api.schemas.request_schemas import MDTReportRequest
from api.schemas.response_schemas import ReportResponse, PaginatedReportResponse
from services.report_service import ReportService
from utils.exceptions import ValidationException, NotFoundException, DatabaseException
from utils.pagination import paginate


router = APIRouter(prefix="/patients", tags=["Reports"])

report_service = ReportService()
logger = logging.getLogger(__name__)

@router.post("/{patient_id}/reports", response_model=ReportResponse, status_code=202)
async def create_mdt_report(patient_id: str, request: Optional[MDTReportRequest] = None):
    """
    Generate a comprehensive MDT (Multi-Disciplinary Team) report for a patient.
    
    This endpoint creates a report with 'PROCESSING' status and processes it asynchronously.
    The report generation happens in the background. Use GET endpoints to check status and results.
    
    Returns immediately with report UUID and 'PROCESSING' status.
    """
    try:
        # Extract report title from request if provided
        report_title = None
        if request and request.title:
            report_title = request.title
        
        # Create report record with PROCESSING status
        report = report_service.create_report_record(patient_id, report_title)

        # Reasoning effort no longer accepted from UI; backend applies defaults
        reasoning_effort = None
        
        # Extract NER configuration if provided
        ner_config = None
        if request and getattr(request, "ner_config", None):
            ner_config = {
                "max_entities_per_batch": request.ner_config.max_entities_per_batch,
                "max_content_size": request.ner_config.max_content_size,
                "chunk_overlapping": request.ner_config.chunk_overlapping,
                "continue_on_batch_errors": request.ner_config.continue_on_batch_errors,
            }

        # Extract JSON filter options
        json_date_from = None
        json_auto_filter = False
        if request:
            if getattr(request, "json_date_from", None):
                json_date_from = request.json_date_from
            if getattr(request, "json_auto_filter", None):
                json_auto_filter = bool(request.json_auto_filter)

        # Trigger report generation asynchronously (fire and forget)
        import asyncio
        asyncio.create_task(
            report_service.generate_report_async(
                report.uuid, patient_id, report_title, reasoning_effort, ner_config, json_date_from, json_auto_filter
            )
        )
        
        return ReportResponse(**report.model_dump())
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{patient_id}/reports/json-filter-check")
async def json_filter_check(
    patient_id: str,
    request: Optional[MDTReportRequest] = None
):
    """
    Check JSON filter impact without generating a full MDT report.
    Returns counts: total JSON docs considered, matched JSON docs, and reduction % for the first JSON document.
    """
    try:
        json_date_from = None
        json_auto_filter = False
        if request:
            if getattr(request, "json_date_from", None):
                json_date_from = request.json_date_from
            if getattr(request, "json_auto_filter", None):
                json_auto_filter = bool(request.json_auto_filter)

        result = await report_service.json_filter_check(
            patient_id=patient_id,
            json_date_from=json_date_from,
            json_auto_filter=json_auto_filter
        )
        return result
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{patient_id}/reports/{report_id}", response_model=ReportResponse)
def get_report(patient_id: str, report_id: str):
    """
    Retrieve a specific report for a patient.
    """
    try:
        report = report_service.get_report_by_uuid(report_id)
        # Verify the report belongs to the specified patient
        if report.patient_id != patient_id:
            raise NotFoundException(f"Report {report_id} not found for patient {patient_id}")
        return ReportResponse(**report.model_dump())
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{patient_id}/reports", response_model=PaginatedReportResponse)
def get_reports(patient_id: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    """
    Retrieve all reports for a patient.
    """
    try:
        reports = report_service.get_reports_by_patient_id(patient_id, page=page, page_size=page_size)
        report_responses = [ReportResponse(**report.model_dump()) for report in reports]
        paginated = paginate(report_responses, page, page_size)
        return PaginatedReportResponse(**paginated)
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{patient_id}/reports/statistics")
def get_report_statistics(patient_id: str):
    """
    Get statistics about reports for a patient.
    
    Returns:
    - Total number of reports
    - Reports by status
    - Total characters and words across all reports
    - Latest report date
    """
    try:
        stats = report_service.get_report_statistics(patient_id)
        return {
            "patient_id": patient_id,
            "statistics": stats
        }
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{patient_id}/reports/{report_id}", status_code=204)
def delete_report(patient_id: str, report_id: str):
    try:
        report = report_service.get_report_by_uuid(report_id)
        if report.patient_id != patient_id:
            raise NotFoundException(f"Report {report_id} not found for patient {patient_id}")
        report_service.delete_report(report_id)
        return Response(status_code=204)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{patient_id}/reports/stream")
async def create_mdt_report_stream(patient_id: str, request: Optional[MDTReportRequest] = None):
    """
    Generate a comprehensive MDT (Multi-Disciplinary Team) report for a patient with real-time progress updates.
    
    This endpoint returns a Server-Sent Events (SSE) stream that provides real-time progress updates
    during the report generation process. The stream will send progress updates and complete with
    the final report UUID.
    
    Returns a streaming response with progress updates in SSE format.
    """
    
    async def generate_report_with_progress() -> AsyncGenerator[str, None]:
        """Generate report with real-time progress updates."""
        try:

            # Extract report title from request if provided
            report_title = None
            if request and request.title:
                report_title = request.title
            
            # Send initial status
            initial_status = {
                "status": "STARTED",
                "progress": 0,
                "message": "Starting MDT report generation...",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(initial_status)}\n\n"
            sys.stdout.flush()  # Force flush
            
            # Use asyncio.Queue for real-time progress streaming
            progress_queue = asyncio.Queue()
            report_result = {"data": None, "error": None, "completed": False}
            
            # Progress callback function that immediately queues updates
            async def progress_callback(progress_data: dict):
                """Callback function to immediately queue progress updates."""
                progress_data["timestamp"] = datetime.now().isoformat()
                await progress_queue.put(progress_data)
            
            # Reasoning effort no longer accepted from UI; backend applies defaults
            reasoning_effort = None
                
            # Extract NER configuration if provided
            ner_config = None
            if request and getattr(request, "ner_config", None):
                ner_config = {
                    "max_entities_per_batch": request.ner_config.max_entities_per_batch,
                    "max_content_size": request.ner_config.max_content_size,
                    "chunk_overlapping": request.ner_config.chunk_overlapping,
                    "continue_on_batch_errors": request.ner_config.continue_on_batch_errors,
                }

            # Extract JSON filter options
            json_date_from = None
            json_auto_filter = False
            if request:
                if getattr(request, "json_date_from", None):
                    json_date_from = request.json_date_from
                if getattr(request, "json_auto_filter", None):
                    json_auto_filter = bool(request.json_auto_filter)

            # Start report generation in background
            async def run_report_generation():
                try:
                    result = await report_service.generate_report_with_progress(
                        patient_id=patient_id,
                        report_title=report_title,
                        progress_callback=progress_callback,
                        reasoning_effort=None,
                        ner_config=ner_config,
                        json_date_from=json_date_from,
                        json_auto_filter=json_auto_filter
                    )
                    report_result["data"] = result
                    report_result["completed"] = True
                    # Signal completion by adding None to queue
                    await progress_queue.put(None)
                except Exception as e:
                    report_result["error"] = e
                    report_result["completed"] = True
                    # Signal completion by adding None to queue
                    await progress_queue.put(None)
            
            # Dedicated progress streaming task running concurrently
            async def stream_progress_updates():
                """Dedicated concurrent task for streaming progress updates in real-time."""
                
                
                while True:
                    try:
                        # Short timeout for high responsiveness
                        progress_data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                        
                        # None signals completion
                        if progress_data is None:
                            break
                        
                        # Stream the progress update immediately
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        sys.stdout.flush()  # Force immediate delivery
                        
                    except asyncio.TimeoutError:
                        # Check if main task completed (without blocking)
                        if report_result["completed"]:
                            break
                        # Continue checking for updates (no blocking)
                        continue
                    except Exception as e:
                        break
                
                
            
            # Start report generation task concurrently (don't await yet)
            report_task = asyncio.create_task(run_report_generation())
            
            # Stream progress updates using the dedicated concurrent streaming task
            async for progress_update in stream_progress_updates():
                yield progress_update
            
            # Wait for report generation to complete (in case streaming ended early)
            await report_task
            
            # Check if report generation succeeded
            if report_result["error"]:
                raise report_result["error"]
            
            # Send completion status
            completion_status = {
                "status": "COMPLETED",
                "progress": 100,
                "message": "MDT report generation completed successfully",
                "report_uuid": report_result["data"].get("uuid"),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(completion_status)}\n\n"
            sys.stdout.flush()  # Force flush
            
        except ValidationException as e:
            error_status = {
                "status": "FAILED",
                "progress": 0,
                "message": f"Validation error: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_status)}\n\n"
            sys.stdout.flush()  # Force flush
            
        except NotFoundException as e:
            error_status = {
                "status": "FAILED",
                "progress": 0,
                "message": f"Not found: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_status)}\n\n"
            sys.stdout.flush()  # Force flush
            
        except Exception as e:
            error_status = {
                "status": "FAILED",
                "progress": 0,
                "message": f"Report generation failed: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_status)}\n\n"
            sys.stdout.flush()  # Force flush
    
    return StreamingResponse(
        generate_report_with_progress(),
        media_type="text/event-stream",  # Proper SSE MIME type
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "X-Content-Type-Options": "nosniff",
            "Transfer-Encoding": "chunked"
        }
    )


@router.post("/{patient_id}/reports/section-summary")
async def generate_section_summary(patient_id: str, request: dict):
    """
    Generate a narrative summary for a report section using LLM.
    
    Takes entities from a section and generates a comprehensive text summary.
    """
    try:
        logger.info(f"Section summary request for patient {patient_id}")
        
        section_title = request.get("section_title", "")
        entities = request.get("entities", [])
        
        logger.info(f"Processing section '{section_title}' with {len(entities)} entities")
        
        if not entities:
            logger.warning(f"No entities provided for section {section_title}")
            return {"summary": "No information available for this section."}
        
        # Enhanced logging
        entity_names = [entity.get('name', 'Unknown') for entity in entities[:3]]
        logger.info(f"Sample entities: {entity_names}")
        
        try:
            from services.section_summary_service import SectionSummaryService
            summary_service = SectionSummaryService()
            summary = await summary_service.generate_summary(section_title, entities)
            
            if summary:
                # Log if summary appears to be from fallback (contains specific pattern)
                if "is documented as:" in summary or "is comprehensively documented as:" in summary:
                    logger.warning(f"Summary for {section_title} appears to be from fallback function")
            else:
                logger.warning(f"Empty summary returned for {section_title}")
            
            return {"summary": summary}
            
        except ImportError as e:
            logger.error(f"Failed to import SectionSummaryService: {e}")
            # Create a detailed fallback summary
            fallback = self._create_detailed_fallback(section_title, entities)
            return {"summary": fallback}
        except Exception as e:
            logger.error(f"Error in SectionSummaryService: {e}")
            fallback = self._create_detailed_fallback(section_title, entities)
            return {"summary": fallback}
        
    except Exception as e:
        logger.error(f"Failed to generate section summary: {e}")
        return {"summary": ""}

def _create_detailed_fallback(section_title: str, entities: list) -> str:
    """Create a detailed fallback summary using entity data"""
    if not entities:
        return f"No information was available for the {section_title} section."
    
    summary_parts = [f"The {section_title} section includes important medical information."]
    
    # Include key data points with actual values
    for entity in entities[:4]:  # Limit to first 4 entities
        name = entity.get('name', 'Unknown')
        value = str(entity.get('value', '')).strip()
        
        if value and len(value) > 0:
            # Preserve full values for comprehensive fallback summaries
            # Only truncate extremely long values (over 1000 chars) to prevent display issues
            if len(value) > 1000:
                value = value[:1000] + " [continued with additional details]"
            summary_parts.append(f"The {name} is documented as: {value}.")
    
    if len(entities) > 4:
        remaining = len(entities) - 4
        summary_parts.append(f"Additional {remaining} data points were also extracted for this section.")
    
    return " ".join(summary_parts)