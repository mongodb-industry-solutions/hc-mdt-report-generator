"""
Evaluation Entity - Standalone collection for evaluation results.

This entity represents evaluation results comparing generated entities against ground truth.
It is stored in a separate 'evaluations' collection, linked by patient_id and report_uuid.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid as uuid_lib


class ExactMatchMetrics(BaseModel):
    """Exact match precision, recall, F1 scores."""
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    recall: float = Field(default=0.0, ge=0.0, le=1.0)
    f1: float = Field(default=0.0, ge=0.0, le=1.0)


class EvaluationSummary(BaseModel):
    """Summary metrics from evaluation."""
    exact_match: ExactMatchMetrics = Field(default_factory=ExactMatchMetrics)
    llm_semantic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    oov_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    entity_count: int = Field(default=0)
    matched_count: int = Field(default=0)
    missing_count: int = Field(default=0)
    extra_count: int = Field(default=0)


class EvaluationEntityDetail(BaseModel):
    """Per-entity evaluation detail."""
    entity_name: str
    gold_value: Optional[str] = None
    pred_value: Optional[str] = None
    exact_match: bool = Field(default=False)
    llm_score: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class WorstEntity(BaseModel):
    """Info about a poorly performing entity."""
    name: str
    f1: float = Field(default=0.0)


class Evaluation(BaseModel):
    """
    Evaluation results comparing generated entities against ground truth.
    
    Stored in 'evaluations' collection.
    Linked to a specific report, ground truth, and patient.
    Use created_at for finding the latest evaluation for a patient/report.
    """
    # Primary key
    uuid: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        description="Unique identifier for this evaluation"
    )
    
    # Foreign keys
    patient_id: str = Field(..., description="Patient identifier")
    report_uuid: str = Field(..., description="Report UUID being evaluated")
    ground_truth_uuid: str = Field(..., description="Ground truth UUID used for comparison")
    
    # Timestamps (use for finding latest)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this evaluation was run"
    )
    
    # Status
    status: str = Field(default="PENDING", description="PENDING, RUNNING, COMPLETED, FAILED")
    
    # LLM model used for semantic scoring
    llm_model: Optional[str] = Field(default=None, description="LLM model used for semantic scoring")
    
    # Results
    summary: Optional[EvaluationSummary] = Field(default=None, description="Summary metrics")
    details: List[EvaluationEntityDetail] = Field(default_factory=list, description="Per-entity details")
    worst_entities: List[WorstEntity] = Field(default_factory=list, description="Worst performing entities")
    
    # Error info
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


