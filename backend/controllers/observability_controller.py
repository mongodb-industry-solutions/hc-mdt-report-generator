from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Query, HTTPException

from repositories.generation_repository import GenerationRepository
from repositories.evaluation_repository import EvaluationRepository
from repositories.ground_truth_repository import GroundTruthRepository
from api.schemas.response_schemas import GenerationsListResponse, GenerationResponse
from utils.exceptions import DatabaseException


router = APIRouter(prefix="/observability", tags=["Observability"])

logger = logging.getLogger(__name__)
generation_repo = GenerationRepository()
eval_repo = EvaluationRepository()
gt_repo = GroundTruthRepository()


@router.get("/generations", response_model=GenerationsListResponse)
def list_generations(
    start: Optional[str] = Query(None, description="Start ISO datetime (UTC) inclusive"),
    end: Optional[str] = Query(None, description="End ISO datetime (UTC) inclusive"),
    model_llm: Optional[str] = Query(None, description="Filter by LLM model"),
    filenames_hash: Optional[str] = Query(None, description="Filter by filenames hash"),
    patient_id: Optional[str] = Query(None, description="Optional filter by patient id"),
):
    try:
        filters: Dict[str, Any] = {"status": "COMPLETED"}

        # Date range filter on timestamp_utc
        if start or end:
            ts_filter: Dict[str, Any] = {}
            if start:
                try:
                    ts_filter["$gte"] = datetime.fromisoformat(start)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid 'start' datetime format")
            if end:
                try:
                    ts_filter["$lte"] = datetime.fromisoformat(end)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid 'end' datetime format")
            filters["timestamp_utc"] = ts_filter

        if model_llm:
            filters["model_llm"] = model_llm
        if filenames_hash:
            filters["filenames_hash"] = filenames_hash
        if patient_id:
            filters["patient_id"] = patient_id

        items = generation_repo.list(filters=filters, limit=1000)
        
        # Enrich each generation with evaluation and GT status
        enriched_responses = []
        for item in items:
            item_dict = item.model_dump()
            
            # Get report UUID from the generation
            report_uuid = None
            if item_dict.get("report") and isinstance(item_dict["report"], dict):
                report_uuid = item_dict["report"].get("uuid")
            
            # Check for existing evaluation and ground truth
            evaluation_status = None
            evaluation_summary = None
            gt_status = None
            
            if report_uuid:
                try:
                    # Check for evaluation
                    evaluation = eval_repo.get_latest_by_report(report_uuid)
                    if evaluation:
                        evaluation_status = evaluation.status
                        if evaluation.summary:
                            evaluation_summary = {
                                "macro_f1": evaluation.summary.exact_match.f1 if evaluation.summary.exact_match else 0,
                                "llm_score": evaluation.summary.llm_semantic_score
                            }
                    
                    # Check for ground truth
                    gt = gt_repo.get_latest_by_report(report_uuid)
                    if gt:
                        gt_status = gt.status
                except Exception as e:
                    logger.warning(f"Failed to get evaluation/GT status for report {report_uuid}: {e}")
            
            # Add enriched fields
            item_dict["evaluation_status"] = evaluation_status
            item_dict["evaluation_summary"] = evaluation_summary
            item_dict["gt_status"] = gt_status
            
            enriched_responses.append(GenerationResponse(**item_dict))
        
        return GenerationsListResponse(items=enriched_responses, total=len(enriched_responses))
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generations/filters")
def generations_filters():
    """Return distinct values for helpful filters (LLMs and docs hashes)."""
    try:
        llms = generation_repo.distinct_values("model_llm")
        hashes = generation_repo.distinct_values("filenames_hash")
        return {"llms": llms, "hashes": hashes}
    except DatabaseException as e:
        raise HTTPException(status_code=500, detail=str(e))
