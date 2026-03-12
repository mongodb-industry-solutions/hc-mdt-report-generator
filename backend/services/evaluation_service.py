"""
Evaluation Service

Evaluates generated entities against ground truth using:
1. Exact match Precision/Recall/F1 (for clinical precision)
2. Continuous LLM semantic scoring (0.0-1.0)
3. Per-entity breakdown (identifies which entities fail most)
4. OOV (Out of Vocabulary) rate tracking

UPDATED: 
- Now uses separate collections for ground_truths and evaluations.
- Respects LLM_PROVIDER setting (bedrock primary, gpt_open fallback)
- Fixed scoring: GT empty = 0, both empty = 0
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

from repositories.report_repository import ReportRepository
from repositories.ground_truth_repository import GroundTruthRepository
from repositories.evaluation_repository import EvaluationRepository
from domain.entities.evaluation import (
    Evaluation, EvaluationSummary, ExactMatchMetrics,
    EvaluationEntityDetail, WorstEntity
)
from domain.entities.ground_truth import GroundTruth

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Service to evaluate generated entities against ground truth.
    
    Metrics:
    1. Exact Match Precision/Recall/F1 (micro, value-level) - for clinical precision
    2. LLM Semantic Score (continuous 0.0-1.0) - captures semantic equivalence
    3. Per-Entity Breakdown - identifies which entities fail most
    4. OOV Rate - tracks out-of-vocabulary predictions
    
    UPDATED: Uses separate collections and respects LLM_PROVIDER setting (Bedrock primary).
    """

    def __init__(self):
        self.report_repo = ReportRepository()
        self.gt_repo = GroundTruthRepository()
        self.eval_repo = EvaluationRepository()

    async def evaluate_report(
        self,
        report_uuid: str,
        patient_id: str,
        ground_truth_uuid: Optional[str] = None,
        llm_provider: Optional[str] = None  # User's LLM selection from Settings
    ) -> Evaluation:
        """
        Evaluate a report against ground truth.
        
        Args:
            report_uuid: UUID of the report to evaluate
            patient_id: Patient ID for linking
            ground_truth_uuid: Optional specific GT UUID. If None, uses latest GT for the report.
            llm_provider: LLM provider for semantic scoring ("bedrock" or "gpt_open").
                         If None, falls back to LLM_PROVIDER env var (defaults to bedrock).
            
        Returns:
            Evaluation object with results (saved to evaluations collection)
        """
        # Get report
        report = self.report_repo.get_by_uuid(report_uuid)
        
        if not report.content or not report.content.get("ner_results", {}).get("entities"):
            raise ValueError(f"Report {report_uuid} has no extracted entities")
        
        # Get ground truth
        if ground_truth_uuid:
            ground_truth = self.gt_repo.get_by_uuid(ground_truth_uuid)
        else:
            ground_truth = self.gt_repo.get_latest_by_report(report_uuid)
        
        if not ground_truth:
            raise ValueError(f"No ground truth found for report {report_uuid}")
        
        # Extract entities
        gold_entities = ground_truth.entities
        pred_entities = report.content.get("ner_results", {}).get("entities", [])
        
        # Convert to normalized maps
        gold_map = self._entities_to_map(gold_entities)
        pred_map = self._entities_to_map(pred_entities)
        
        # Get all entity names
        all_entity_names = sorted(set(gold_map.keys()) | set(pred_map.keys()))
        
        # Calculate exact match metrics
        exact_metrics, entity_details = self._calculate_exact_match_metrics(
            gold_map, pred_map, all_entity_names
        )
        
        # Get LLM semantic scores (respects user's LLM selection)
        llm_scores = await self._get_llm_semantic_scores(gold_map, pred_map, llm_provider)
        
        # Update entity details with LLM scores
        for detail in entity_details:
            detail.llm_score = llm_scores.get(detail.entity_name, 0.0)
        
        # Calculate summary metrics
        summary = self._calculate_summary(exact_metrics, entity_details, gold_map, pred_map)
        
        # Find worst performing entities
        worst_entities = self._find_worst_entities(entity_details)
        
        # Resolve LLM model used
        resolved_model = llm_provider or os.environ.get("LLM_PROVIDER", "bedrock")
        
        # Create evaluation result
        evaluation = Evaluation(
            patient_id=patient_id,
            report_uuid=report_uuid,
            ground_truth_uuid=ground_truth.uuid,
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
            llm_model=resolved_model,
            summary=summary,
            details=entity_details,
            worst_entities=worst_entities
        )
        
        # Save to evaluations collection
        saved_evaluation = self.eval_repo.create(evaluation)
        
        logger.info(f"Evaluation completed for report {report_uuid}: F1={summary.exact_match.f1:.2f}, LLM_score={summary.llm_semantic_score:.2f}")
        return saved_evaluation

    def _entities_to_map(self, entities: List[Any]) -> Dict[str, str]:
        """
        Convert entity list to {name: normalized_value} map.
        
        Args:
            entities: List of entity objects or dicts
            
        Returns:
            Dictionary mapping entity names to normalized values
        """
        result = {}
        
        for entity in entities:
            # Handle both dict and Pydantic model
            if hasattr(entity, "entity_name"):
                name = entity.entity_name
                value = getattr(entity, "value", None)
            elif isinstance(entity, dict):
                name = entity.get("entity_name") or entity.get("name")
                value = entity.get("value")
            else:
                continue
            
            if not name:
                continue
            
            # Normalize value
            if value is None or (isinstance(value, str) and not value.strip()):
                normalized = ""
            else:
                normalized = str(value).strip().lower()
            
            result[name] = normalized
        
        return result

    def _calculate_exact_match_metrics(
        self,
        gold_map: Dict[str, str],
        pred_map: Dict[str, str],
        all_entity_names: List[str]
    ) -> Tuple[ExactMatchMetrics, List[EvaluationEntityDetail]]:
        """
        Calculate exact match precision, recall, F1 and per-entity details.
        
        Args:
            gold_map: Ground truth {name: value} map
            pred_map: Predicted {name: value} map
            all_entity_names: All entity names to evaluate
            
        Returns:
            Tuple of (ExactMatchMetrics, list of EvaluationEntityDetail)
        """
        tp = 0  # True positives (exact matches)
        fp = 0  # False positives (predicted but wrong/not in gold)
        fn = 0  # False negatives (in gold but not predicted)
        
        details = []
        
        for name in all_entity_names:
            gold_val = gold_map.get(name, "")
            pred_val = pred_map.get(name, "")
            
            # Determine match status
            exact_match = False
            
            if gold_val and pred_val:
                # Both have values
                if gold_val == pred_val:
                    exact_match = True
                    tp += 1
                else:
                    fp += 1  # Predicted wrong value
                    fn += 1  # Missing correct value
            elif pred_val and not gold_val:
                # Predicted but no gold value (could be extra or gold missing)
                fp += 1
            elif gold_val and not pred_val:
                # Gold has value but not predicted
                fn += 1
            # If both empty, no contribution to metrics (and no match!)
            
            # Create detail record
            detail = EvaluationEntityDetail(
                entity_name=name,
                gold_value=gold_val if gold_val else None,
                pred_value=pred_val if pred_val else None,
                exact_match=exact_match,
                llm_score=0.0,  # Will be filled by LLM scoring
                notes=None
            )
            details.append(detail)
        
        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics = ExactMatchMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4)
        )
        
        return metrics, details

    async def _get_llm_semantic_scores(
        self,
        gold_map: Dict[str, str],
        pred_map: Dict[str, str],
        llm_provider: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get continuous LLM semantic scores (0.0-1.0) for each entity.
        Uses user's LLM selection from Settings.
        
        SCORING RULES:
        - If GT (gold) is empty/null → Score 0.0 (cannot evaluate without ground truth)
        - If both are empty/null → Score 0.0 (no data to compare)
        - Otherwise → LLM evaluates semantic similarity
        
        Args:
            gold_map: Ground truth {name: value} map
            pred_map: Predicted {name: value} map
            llm_provider: LLM provider to use ("bedrock" or "gpt_open")
            
        Returns:
            Dictionary mapping entity names to semantic scores
        """
        # Pre-filter: only compare entities where GT has a value
        comparisons = {}
        pre_scores = {}
        
        for name in set(gold_map.keys()) | set(pred_map.keys()):
            gold_val = gold_map.get(name, "")
            pred_val = pred_map.get(name, "")
            
            # RULE: If GT is empty, score is 0.0 (cannot evaluate)
            if not gold_val:
                pre_scores[name] = 0.0
                continue
            
            # RULE: GT has value but pred is empty → score 0.0
            if not pred_val:
                pre_scores[name] = 0.0
                continue
            
            # Both have values - add to LLM comparison
            comparisons[name] = {
                "gold": gold_val,
                "predicted": pred_val
            }
        
        # If no comparisons needed, return pre_scores
        if not comparisons:
            logger.info("No entities with both GT and predicted values to compare via LLM")
            return pre_scores
        
        # Build LLM prompt
        system_prompt = """You are an evaluation assistant comparing predicted medical entity values against ground truth.

For each entity, return a CONTINUOUS score from 0.0 to 1.0:
- 1.0: Perfect semantic match (same meaning, regardless of phrasing/formatting)
- 0.7-0.9: Minor differences but clinically acceptable (e.g., "sein gauche" vs "sein G", "carcinome epidermoide" vs "carcinome épidermoïde")
- 0.3-0.6: Partial match, some correct information
- 0.1-0.2: Very weak match, minimal overlap
- 0.0: Completely incorrect or unrelated

Consider:
- Medical abbreviations (e.g., "BRCA1" = "BRCA 1")
- Accent/diacritic variations (e.g., "épidermoïde" = "epidermoide")
- Date format variations (e.g., "12/06/2024" = "12 juin 2024")
- Unit variations (e.g., "15%" = "15 pourcent")
- Extra context in predictions (e.g., gold="oropharynx" should match pred="oropharynx, centré sur amygdale")

Return ONLY valid JSON: {"entity_name": 0.85, ...}"""

        prompt = f"""Compare these entity extractions and score each 0.0-1.0:

{json.dumps(comparisons, ensure_ascii=False, indent=2)}

Respond with JSON only: {{"EntityName": 0.85, ...}}"""

        try:
            # Call LLM based on user's provider selection
            response = await self._call_llm(prompt, system_prompt, llm_provider)
            
            # Parse JSON response
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
                llm_scores = json.loads(json_str)
                
                # Merge LLM scores with pre_scores
                for name, score in llm_scores.items():
                    pre_scores[name] = min(1.0, max(0.0, float(score)))
                
                logger.info(f"LLM semantic scoring completed for {len(llm_scores)} entities")
                return pre_scores
                
        except Exception as e:
            logger.warning(f"LLM semantic scoring failed: {e}")
        
        # Fallback: use exact match as score (only for entities with GT values)
        logger.warning("Using fallback exact match scoring")
        for name in comparisons.keys():
            gold_val = gold_map.get(name, "")
            pred_val = pred_map.get(name, "")
            pre_scores[name] = 1.0 if gold_val == pred_val else 0.0
        
        return pre_scores

    async def _call_llm(self, prompt: str, system_prompt: str, llm_provider: Optional[str] = None) -> str:
        """
        Call LLM based on user's selection or LLM_PROVIDER environment variable.
        User's selection takes priority over environment variable.
        """
        # Use user's selection if provided, otherwise fall back to env var
        if llm_provider:
            provider = llm_provider.lower()
        else:
            provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
        
        logger.info(f"Evaluation LLM scoring using provider: {provider or 'bedrock (default)'}")
        
        # Route based on provider - Bedrock first, then gpt_open as fallback
        # - "bedrock" -> use AWS Bedrock (primary choice)
        # - "ollama" or "gpt" -> use gpt_open (which routes to Ollama if configured)
        if provider == "bedrock":
            return await self._call_bedrock(prompt, system_prompt)
        elif "ollama" in provider or "gpt" in provider:
            return await self._call_gpt_open(prompt, system_prompt)
        else:
            # Default to bedrock for unknown providers
            logger.warning(f"Unknown provider '{provider}', falling back to bedrock")
            return await self._call_bedrock(prompt, system_prompt)
    
    async def _call_bedrock(self, prompt: str, system_prompt: str) -> str:
        """Call AWS Bedrock for LLM scoring."""
        try:
            from infrastructure.llm.bedrock_client import AsyncBedrockClient
            
            logger.info("Using AWS Bedrock for evaluation semantic scoring")
            
            async with AsyncBedrockClient() as bedrock_client:
                response = await bedrock_client.invoke_bedrock_async_robust(
                    system_prompt,
                    prompt,
                    timeout_override=60  # 1 minute timeout for scoring
                )
            return response
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            logger.warning("Falling back to gpt_open")
            return await self._call_gpt_open(prompt, system_prompt)
    
    async def _call_gpt_open(self, prompt: str, system_prompt: str) -> str:
        """Call GPT-Open compatible server for LLM scoring."""
        from services.base.llm import a_generate
        
        logger.info("Using GPT-Open for evaluation semantic scoring")
        return await a_generate(
            prompt=prompt,
            system=system_prompt,
            temperature=0.0  # Deterministic for evaluation
        )

    def _calculate_summary(
        self,
        exact_metrics: ExactMatchMetrics,
        entity_details: List[EvaluationEntityDetail],
        gold_map: Dict[str, str],
        pred_map: Dict[str, str]
    ) -> EvaluationSummary:
        """
        Calculate summary metrics from detailed results.
        
        Args:
            exact_metrics: Exact match P/R/F1
            entity_details: Per-entity details with LLM scores
            gold_map: Ground truth map
            pred_map: Predicted map
            
        Returns:
            EvaluationSummary object
        """
        # Mean LLM semantic score (only for entities that were actually scored)
        # Exclude entities where GT was empty (score=0 by rule, not by comparison)
        scored_entities = [d for d in entity_details if d.gold_value]
        llm_scores = [d.llm_score for d in scored_entities]
        mean_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0
        
        # OOV rate: predictions not in gold vocabulary
        oov_count = sum(
            1 for d in entity_details
            if d.pred_value and d.gold_value and d.pred_value != d.gold_value
        )
        total_predictions = sum(1 for d in entity_details if d.pred_value)
        oov_rate = oov_count / total_predictions if total_predictions > 0 else 0.0
        
        # Count matched, missing, extra
        matched = sum(1 for d in entity_details if d.exact_match)
        missing = sum(1 for d in entity_details if d.gold_value and not d.pred_value)
        extra = sum(1 for d in entity_details if d.pred_value and not d.gold_value)
        
        return EvaluationSummary(
            exact_match=exact_metrics,
            llm_semantic_score=round(mean_llm_score, 4),
            oov_rate=round(oov_rate, 4),
            entity_count=len(entity_details),
            matched_count=matched,
            missing_count=missing,
            extra_count=extra
        )

    def _find_worst_entities(
        self,
        entity_details: List[EvaluationEntityDetail],
        top_n: int = 5
    ) -> List[WorstEntity]:
        """
        Find the worst performing entities by LLM score.
        Only considers entities where GT had a value (meaningful comparison).
        
        Args:
            entity_details: Per-entity evaluation details
            top_n: Number of worst entities to return
            
        Returns:
            List of WorstEntity objects
        """
        # Only include entities where GT had a value (meaningful to compare)
        meaningful_entities = [d for d in entity_details if d.gold_value]
        
        # Sort by LLM score ascending (worst first)
        sorted_details = sorted(meaningful_entities, key=lambda d: d.llm_score)
        
        return [
            WorstEntity(name=d.entity_name, f1=d.llm_score)
            for d in sorted_details[:top_n]
        ]

    def get_evaluation(self, report_uuid: str) -> Optional[Evaluation]:
        """
        Get the latest evaluation results for a report.
        
        Args:
            report_uuid: UUID of the report
            
        Returns:
            Evaluation object or None if not evaluated
        """
        return self.eval_repo.get_latest_by_report(report_uuid)

    def get_evaluation_by_uuid(self, evaluation_uuid: str) -> Optional[Evaluation]:
        """
        Get a specific evaluation by its UUID.
        
        Args:
            evaluation_uuid: UUID of the evaluation
            
        Returns:
            Evaluation object or None if not found
        """
        try:
            return self.eval_repo.get_by_uuid(evaluation_uuid)
        except Exception:
            return None

    def get_evaluation_summary(self, report_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get just the summary metrics for a report's latest evaluation.
        
        Args:
            report_uuid: UUID of the report
            
        Returns:
            Summary dict or None if not evaluated
        """
        evaluation = self.get_evaluation(report_uuid)
        
        if evaluation and evaluation.summary:
            return evaluation.summary.model_dump() if hasattr(evaluation.summary, 'model_dump') else evaluation.summary
        
        return None
    
    def get_evaluations_by_patient(self, patient_id: str, limit: int = 50) -> List[Evaluation]:
        """
        Get all evaluations for a patient.
        
        Args:
            patient_id: Patient identifier
            limit: Maximum number to return
            
        Returns:
            List of evaluations, newest first
        """
        return self.eval_repo.get_by_patient(patient_id, limit)
