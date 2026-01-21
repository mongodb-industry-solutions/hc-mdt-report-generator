import json
import asyncio
from typing import AsyncGenerator
from datetime import datetime
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.evaluation_service import EvaluationService


router = APIRouter(prefix="/evaluate", tags=["Evaluate"])

logger = logging.getLogger(__name__)
service = EvaluationService()


@router.get("/pending")
def get_pending():
    """Return list of pending generations to evaluate (summaries only)."""
    items = service.get_pending_generations()
    return {"total": len(items), "items": [
        {
            "uuid": i.get("uuid"),
            "timestamp_utc": i.get("timestamp_utc"),
            "model_llm": i.get("model_llm"),
            "filenames_hash": i.get("filenames_hash"),
            "patient_id": i.get("patient_id"),
        }
        for i in items
    ]}


@router.post("/stream")
async def run_evaluation_stream():
    """
    Start evaluation for all pending generations. Returns SSE stream with progress updates:
    - STARTED
    - PROGRESS (every item)
    - COMPLETED
    """

    async def generator() -> AsyncGenerator[str, None]:
        try:
            started = {
                "status": "STARTED",
                "timestamp": datetime.now().isoformat()
            }
            yield "data: " + json.dumps(started) + "\n\n"

            pending = service.get_pending_generations()
            total = len(pending)
            done = 0
            yield "data: " + json.dumps({"status": "PENDING_SUMMARY", "total": total}) + "\n\n"

            # Evaluate one by one to emit progress
            gold = service.load_gold()
            gold_entities = service._extract_entities(gold)
            for gen in pending:
                details, summary = await service._evaluate_one(gen, gold_entities)
                service.repo.update(gen["uuid"], {
                    "evaluation_status": "COMPLETED",
                    "evaluation_summary": summary,
                    "evaluation_details": details,
                    "evaluated_at": datetime.now().isoformat()
                })
                done += 1
                yield "data: " + json.dumps({"status": "PROGRESS", "done": done, "total": total}) + "\n\n"
                await asyncio.sleep(0)

            completed = {
                "status": "COMPLETED",
                "timestamp": datetime.now().isoformat()
            }
            yield "data: " + json.dumps(completed) + "\n\n"
        except Exception as e:
            err = {"status": "FAILED", "message": str(e)}
            yield "data: " + json.dumps(err) + "\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


