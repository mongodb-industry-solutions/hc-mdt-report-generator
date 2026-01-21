from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


class GenerationLog(BaseModel):
    """Document schema for a generation run logged in MongoDB."""

    uuid: str = Field(..., description="Unique identifier for this generation log entry")
    timestamp_utc: datetime = Field(..., description="UTC time when the request arrived")
    patient_id: str = Field(..., description="Patient identifier")

    # Model and configuration used
    model_llm: str = Field(..., description="Model LLM used for extraction")
    max_entities_per_batch: int = Field(..., description="Advanced NER: Max entities per batch")
    aggregation_batch_size: int = Field(..., description="Advanced NER: Aggregation batch size")
    max_content_size: int = Field(..., description="Advanced NER: Max content size")
    chunk_overlapping: int = Field(..., description="Advanced NER: Chunk overlapping")
    max_concurrent_requests: int = Field(..., description="Advanced NER: Max concurrent requests")

    report_title: Optional[str] = Field(default=None, description="Optional report title")
    filenames_hash: str = Field(..., description="SHA256 hash of sorted filenames processed")
    elapsed_seconds: float = Field(..., description="Elapsed generation time in seconds")

    # Outcome
    found_entities: int = Field(..., description="Number of found entities")
    report: Dict[str, Any] = Field(..., description="Full report JSON payload")
    status: str = Field(default="COMPLETED", description="Outcome status: COMPLETED or FAILED")
    error: Optional[str] = Field(default=None, description="Error message when failed")

    # Evaluation
    evaluation_status: Optional[str] = Field(default=None, description="Evaluation status: COMPLETED or None")
    evaluation_summary: Optional[Dict[str, Any]] = Field(default=None, description="Aggregate evaluation metrics")
    evaluation_details: Optional[List[Dict[str, Any]]] = Field(default=None, description="Per-entity evaluation metrics")
    evaluated_at: Optional[datetime] = Field(default=None, description="UTC timestamp when evaluation completed")


