from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class ReportElement(BaseModel):
    type: str
    content: Any
    start_char: int
    end_char: int
    page: int
    metadata: Optional[dict] = None


class GroundTruthPDF(BaseModel):
    """Metadata about the uploaded ground truth PDF stored as base64."""
    filename: str
    file_content: str = Field(..., description="Base64-encoded PDF content")
    pages: int = Field(default=1)
    file_size: int = Field(default=0)


class GroundTruthEntity(BaseModel):
    """A single ground truth entity with value and source info."""
    entity_name: str
    value: Optional[str] = None
    source: str = Field(default="extracted", description="'extracted' from OCR or 'manual' if user edited")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class GroundTruth(BaseModel):
    """Ground truth data for evaluation, uploaded by user as scanned PDF."""
    uploaded_at: datetime
    ocr_engine: str = Field(..., description="OCR engine used: 'mistral' or 'easyocr'")
    original_pdf: Optional[GroundTruthPDF] = None
    ocr_text: Optional[str] = Field(default=None, description="Full OCR output text")
    entities: List[GroundTruthEntity] = Field(default_factory=list)


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
    """Evaluation results comparing generated entities against ground truth."""
    status: str = Field(default="PENDING", description="PENDING, COMPLETED, FAILED")
    evaluated_at: Optional[datetime] = None
    llm_model: Optional[str] = None
    summary: Optional[EvaluationSummary] = None
    details: List[EvaluationEntityDetail] = Field(default_factory=list)
    worst_entities: List[WorstEntity] = Field(default_factory=list)
    error: Optional[str] = None


class Report(BaseModel):
    """
    Report entity - stores generated MDT reports.
    
    NOTE: Ground truth and evaluation data are now stored in separate collections:
    - ground_truths collection (see domain/entities/ground_truth.py)
    - evaluations collection (see domain/entities/evaluation.py)
    
    Use GroundTruthRepository and EvaluationRepository to access this data.
    """
    uuid: str = Field(..., description="Unique identifier for the report")
    patient_id: str = Field(..., description="Patient identifier")
    template_id: Optional[str] = Field(default=None, description="Entity template ID used for extraction - ensures GT uses same template")
    status: str = Field(default="PROCESSING", description="Report status")
    title: str
    filename: str
    file_type: str
    file_size: int
    created_at: datetime
    character_count: int
    word_count: int
    elapsed_seconds: Optional[float] = Field(default=None, description="Processing time in seconds")
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = []
    elements: List[ReportElement] = []
    content: Optional[Dict[str, Any]] = Field(default=None, description="The actual report content as JSON object")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for the report")
    
    # DEPRECATED: These fields are kept for backward compatibility with existing data.
    # New data is stored in separate collections (ground_truths, evaluations).
    # These fields will be removed in a future version.
    ground_truth: Optional[GroundTruth] = Field(default=None, description="DEPRECATED: Use ground_truths collection instead")
    evaluation: Optional[Evaluation] = Field(default=None, description="DEPRECATED: Use evaluations collection instead") 