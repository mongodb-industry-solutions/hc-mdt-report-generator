from typing import List, Dict, Any, Optional
from repositories.report_repository import ReportRepository
from repositories.evaluation_repository import EvaluationRepository
from repositories.ground_truth_repository import GroundTruthRepository
from repositories.generation_repository import GenerationRepository
from domain.entities.report import Report
from services.mdt_report_generator import MDTReportGenerator
from utils.exceptions import NotFoundException, DatabaseException, ValidationException
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportService:
    """
    Service for report-related business logic.
    
    This service orchestrates report creation and generation, including
    MDT (Multi-Disciplinary Team) reports from patient documents.
    
    Uses AWS Bedrock as primary LLM provider, with gpt_open as fallback.
    """
    
    def __init__(self):
        self.repository = ReportRepository()
        self.mdt_generator = MDTReportGenerator()

    def get_report_by_uuid(self, uuid: str) -> Report:
        """Get a MDT report by UUID"""
        try:
            return self.repository.get_by_uuid(uuid)
        except (NotFoundException, DatabaseException):
            raise

    def get_reports_by_patient_id(self, patient_id: str, page: int = 1, page_size: int = 10) -> List[Report]:
        """Get MDT reports for a patient with pagination"""
        skip = (page - 1) * page_size
        try:
            return self.repository.get_by_patient_id(patient_id, skip=skip, limit=page_size)
        except DatabaseException:
            raise

    def delete_report(self, uuid: str) -> None:
        """
        Delete a report and cascade delete all related data:
        - Evaluations linked to this report
        - Ground truths linked to this report
        - Generations that contain this report
        """
        try:
            # Ensure it exists
            _ = self.get_report_by_uuid(uuid)
            
            # Cascade delete related data
            eval_repo = EvaluationRepository()
            gt_repo = GroundTruthRepository()
            gen_repo = GenerationRepository()
            
            # Delete evaluations for this report
            eval_count = eval_repo.delete_by_report_uuid(uuid)
            logger.info(f"Cascade deleted {eval_count} evaluations for report {uuid}")
            
            # Delete ground truths for this report
            gt_count = gt_repo.delete_by_report_uuid(uuid)
            logger.info(f"Cascade deleted {gt_count} ground truths for report {uuid}")
            
            # Delete generations that contain this report
            gen_count = gen_repo.delete_by_report_uuid(uuid)
            logger.info(f"Cascade deleted {gen_count} generations for report {uuid}")
            
            # Finally, delete the report itself
            self.repository.delete_by_uuid(uuid)
            logger.info(f"Successfully deleted report {uuid} with all related data")
            
        except Exception as e:
            logger.error(f"Failed to delete report {uuid}: {e}")
            raise

    def create_report(self, report_data: Dict[str, Any]) -> Report:
        """Create a MDT report"""
        try:
            # Normalize status defensively before persisting
            content = report_data.get("content") or {}
            summary = content.get("summary") or {}
            ner_results = content.get("ner_results") or {}
            has_error = bool(ner_results.get("error"))
            try:
                entities_extracted = int(summary.get("entities_extracted", 0))
            except Exception:
                entities_extracted = 0
            total_docs_val = summary.get("total_documents")
            try:
                total_documents = int(total_docs_val) if total_docs_val is not None else 0
            except Exception:
                total_documents = 0
            zero_entities_failure = (total_documents > 0 and entities_extracted == 0)

            if has_error or zero_entities_failure:
                report_data = {**report_data, "status": "FAILED"}

            report = Report(**report_data)
            return self.repository.create(report)
        except DatabaseException:
            raise
    
    def create_report_record(self, patient_id: str, report_title: Optional[str] = None) -> Report:
        """
        Create a report record with PROCESSING status.
        
        This creates an initial report record that can be updated when generation completes.
        """
        try:
            import uuid
            from datetime import datetime
            
            if not report_title:
                report_title = f"MDT Report - Patient {patient_id}"
            
            # Create initial report data
            report_data = {
                "uuid": str(uuid.uuid4()),
                "patient_id": patient_id,
                "status": "PROCESSING",
                "title": report_title,
                "filename": f"mdt_report_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "file_type": "json",
                "file_size": 0,  # Will be updated when generation completes
                "created_at": datetime.now(),
                "character_count": 0,  # Will be updated when generation completes
                "word_count": 0,  # Will be updated when generation completes
                "author": "MDT Report Generator",
                "subject": f"MDT Report for Patient {patient_id}",
                "keywords": ["MDT", "medical", "report", "patient", patient_id],
                "elements": [],
                "content": None,  # Will be populated when generation completes
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "status": "PROCESSING",
                    "processing_method": "iterative_llm"
                }
            }
            
            # Create the report in the database
            report = self.create_report(report_data)
            logger.info(f"Created report record with UUID: {report.uuid} for patient {patient_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to create report record for patient {patient_id}: {e}")
            raise DatabaseException(f"Report record creation failed: {str(e)}")
    
    async def generate_report_async(self, report_uuid: str, patient_id: str, report_title: Optional[str] = None, reasoning_effort: Optional[str] = None, ner_config: Optional[dict] = None, json_date_from: Optional[str] = None, json_auto_filter: Optional[bool] = False) -> None:
        """
        Generate a comprehensive MDT report asynchronously and update the report record.
        
        This method runs in the background and updates the report status when complete.
        """
        try:
            logger.info(f"Starting async MDT report generation for patient {patient_id}, report {report_uuid}")
            
            # Check for LLM API keys before proceeding
            self._check_llm_api_keys()
            
            # Generate the MDT report content
            report_data = await self.mdt_generator.generate_mdt_report(patient_id, report_title, reasoning_effort, json_date_from=json_date_from, json_auto_filter=json_auto_filter)
            
            # If NER failed, mark FAILED and stop early
            try:
                ner_error = (report_data.get("content", {})
                                        .get("ner_results", {})
                                        .get("error"))
                if ner_error:
                    self.update_report_status(report_uuid, "FAILED", error_message=str(ner_error))
                    return
            except Exception:
                # Proceed to save; update_report_with_content will honor status
                pass

            # Update the report record with generated content
            self.update_report_with_content(report_uuid, report_data)
            
            logger.info(f"Completed async MDT report generation for patient {patient_id}, report {report_uuid}")
            
        except Exception as e:
            # Check if this is a critical error (e.g. missing API key)
            is_critical = False
            error_msg = str(e)
            
            if "CRITICAL:" in error_msg or "CriticalAPIError" in error_msg:
                is_critical = True
                logger.critical(f"CRITICAL ERROR: Report generation halted for patient {patient_id}, report {report_uuid}: {e}")
            else:
                logger.error(f"Failed to generate MDT report for patient {patient_id}, report {report_uuid}: {e}")
            
            # Update report status to FAILED
            self.update_report_status(report_uuid, "FAILED", error_message=error_msg)
            
            # If critical, log additional information to help debug
            if is_critical:
                import os
                logger.critical(f"Environment variables: AWS credentials configured: {'Yes' if 'AWS_DEFAULT_REGION' in os.environ else 'No (check AWS setup)'}")
                logger.critical(f"Environment variables: OPENAI_API_KEY present: {'Yes' if 'OPENAI_API_KEY' in os.environ else 'No'}")  # Keep for secondary option
                logger.critical(f"Settings: openai_api_key present: {'Yes' if hasattr(self.mdt_generator, 'settings') and getattr(self.mdt_generator.settings, 'openai_api_key', None) else 'No'}")
    
    def _check_llm_api_keys(self):
        """Check if the necessary API keys are present based on the provider"""
        import os
        from config.settings import settings
        
        # Check for provider configuration
        provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
        mode = get_current_mode()
        
        if provider == "ollama":
            # Ollama doesn't require API keys - skip all checks
            logger.info("🔑 Using Ollama - no API key required")
            return
        elif provider == "openai" or provider == "gpt_open":
            # Only require OpenAI API key when targeting OpenAI endpoints
            base_url = settings.gpt_open_base_url.lower() if getattr(settings, 'gpt_open_base_url', None) else ""
            is_openai_endpoint = base_url.startswith("https://api.openai.com")
            if is_openai_endpoint:
                api_key = os.environ.get("OPENAI_API_KEY", "")
                if not api_key:
                    logger.critical("❌ CRITICAL: No OpenAI API key found - report generation cannot continue")
                    raise ValueError("CRITICAL: Missing OpenAI API key - report generation cannot continue")
            else:
                logger.info("🔑 Skipping OpenAI API key requirement (non-OpenAI GPT-Open endpoint)")
        elif provider == "bedrock":
            # AWS Bedrock doesn't require explicit API keys (uses AWS credentials)
            logger.info("🔑 Using AWS Bedrock - using AWS credentials")
            return
    
    async def generate_report_with_progress(
        self, 
        patient_id: str, 
        report_title: Optional[str] = None, 
        progress_callback: Optional[callable] = None,
        reasoning_effort: Optional[str] = None,
        ner_config: Optional[Dict[str, Any]] = None,
        json_date_from: Optional[str] = None,
        json_auto_filter: Optional[bool] = False
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive MDT report with real-time progress updates.
        
        This method generates a report and calls the progress_callback function
        with progress updates throughout the generation process.
        
        Args:
            patient_id: The patient ID to generate the report for
            report_title: Optional custom title for the report
            progress_callback: Optional callback function to receive progress updates
            reasoning_effort: Optional reasoning effort level (low, medium, high)
            ner_config: Optional NER configuration parameters
            
        Returns:
            Dictionary containing the generated report data
        """
        # Check for LLM API keys before proceeding to avoid wasted work
        self._check_llm_api_keys()
        try:
            logger.info(f"Starting MDT report generation with progress for patient {patient_id}")
            
            # Send initial progress
            if progress_callback:
                await progress_callback({
                    "status": "INITIALIZING",
                    "progress": 0,
                    "message": "Initializing report generation...",
                    "current_step": "initialization"
                })
            
            # Generate the MDT report content with progress updates
            report_data = await self.mdt_generator.generate_mdt_report_with_progress(
                patient_id, 
                report_title, 
                progress_callback,
                reasoning_effort,
                ner_config,
                json_date_from=json_date_from,
                json_auto_filter=json_auto_filter
            )
            
            # Send completion progress
            if progress_callback:
                await progress_callback({
                    "status": "SAVING",
                    "progress": 95,
                    "message": "Saving report to database...",
                    "current_step": "saving"
                })
            
            # Create the report in the database
            report = self.create_report(report_data)
            
            logger.info(f"MDT report generated successfully with progress for patient {patient_id} - UUID: {report.uuid}")
            
            # Return the report data with UUID
            report_data["uuid"] = report.uuid
            return report_data
            
        except ValidationException as e:
            logger.error(f"Validation error during MDT report generation with progress: {e}")
            if progress_callback:
                await progress_callback({
                    "status": "FAILED",
                    "progress": 0,
                    "message": f"Validation error: {str(e)}",
                    "error": str(e),
                    "current_step": "validation_error"
                })
            raise
        except Exception as e:
            logger.error(f"Failed to generate MDT report with progress for patient {patient_id}: {e}")
            if progress_callback:
                await progress_callback({
                    "status": "FAILED",
                    "progress": 0,
                    "message": f"Report generation failed: {str(e)}",
                    "error": str(e),
                    "current_step": "generation_error"
                })
            raise DatabaseException(f"MDT report generation failed: {str(e)}")

    async def json_filter_check(self, patient_id: str, json_date_from: Optional[str] = None, json_auto_filter: Optional[bool] = False) -> Dict[str, Any]:
        """
        Compute JSON filter impact without generating a full report.
        Returns:
          {
            "total_json_documents": int,
            "matched_json_documents": int,
            "first_json": {
              "items_before": int,
              "items_after": int,
              "bytes_before": Optional[int],
              "bytes_after": Optional[int],
              "reduction_percent": float,
              "filter_date": Optional[str]
            }
          }
        Raises ValidationException if filtering cannot be applied.
        """
        try:
            # Retrieve processed documents
            docs = await self.mdt_generator._get_processed_documents(patient_id)
            # Log high-level doc inventory for debugging
            try:
                inventory = []
                for d in docs:
                    fn = getattr(d, 'filename', None)
                    has_b64 = bool(getattr(d, 'file_content', None))
                    ext = ''
                    try:
                        if isinstance(fn, str) and '.' in fn:
                            ext = fn.lower().rsplit('.', 1)[-1]
                    except Exception:
                        ext = ''
                    inventory.append({"filename": fn, "ext": ext, "has_base64": has_b64})
                logger.info(f"[JSON-FILTER-CHECK] Document inventory: {inventory}")
            except Exception:
                pass

            # Filter only JSON documents by filename
            json_docs = [d for d in docs if isinstance(getattr(d, 'filename', None), str) and getattr(d, 'filename').lower().endswith('.json')]

            if not json_docs:
                # Build informative message with inventory preview
                inv_preview = "; ".join([
                    f"{getattr(d,'filename', 'unknown')} (base64={'yes' if bool(getattr(d,'file_content', None)) else 'no'})"
                    for d in docs
                ])
                msg = f"No JSON documents available to apply filtering. Docs found: {inv_preview}"
                logger.warning(f"[JSON-FILTER-CHECK] {msg}")
                raise ValidationException(msg)

            matched_count = 0
            details: List[Dict[str, Any]] = []
            # Totals for overall reduction
            total_bytes_before = 0
            total_bytes_after = 0
            total_items_before = 0
            total_items_after = 0
            first_stats: Dict[str, Any] = {
                "items_before": 0,
                "items_after": 0,
                "bytes_before": None,
                "bytes_after": None,
                "reduction_percent": 0.0,
                "filter_date": None
            }

            reasons: List[str] = []
            for idx, doc in enumerate(json_docs):
                filename = getattr(doc, 'filename', f'json_{idx+1}')
                logger.info(f"[JSON-FILTER-CHECK] Processing {filename}")
                # Load original JSON from base64 file_content
                file_b64 = getattr(doc, 'file_content', None)
                parsed = self.mdt_generator._load_json_from_file_content(file_b64)
                if not isinstance(parsed, dict):
                    preview = self.mdt_generator._decode_text_preview(file_b64, limit=300)
                    reason = f"{filename}: original_json_not_available (cannot parse base64 JSON). decoded_preview='{preview}'"
                    logger.warning(f"[JSON-FILTER-CHECK] {reason}")
                    reasons.append(reason)
                    continue

                # Apply chosen filter
                if json_auto_filter:
                    preprocessed, stats = self.mdt_generator._filter_json_auto(parsed)
                else:
                    if not json_date_from:
                        # default: six months back
                        from datetime import datetime, timedelta
                        df = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
                        json_date_from = df
                    preprocessed, stats = self.mdt_generator._preprocess_json_lcrs(parsed, json_date_from)
                logger.info(f"[JSON-FILTER-CHECK] {filename}: stats={stats}")
                items_before = int(stats.get('items_before') or 0)
                items_after = int(stats.get('items_after') or 0)
                bytes_before = stats.get('bytes_before')
                bytes_after = stats.get('bytes_after')
                filter_date = stats.get('filter_date')

                if preprocessed is not None and items_after >= 0:
                    matched_count += 1
                    # Accumulate totals (treat None as 0)
                    try:
                        total_items_before += items_before
                        total_items_after += items_after
                        total_bytes_before += int(bytes_before or 0)
                        total_bytes_after += int(bytes_after or 0)
                    except Exception:
                        pass
                    preview_items = []
                    try:
                        lcrs = preprocessed.get('lCrs', []) if isinstance(preprocessed, dict) else []
                        for it in lcrs[:3]:
                            try:
                                preview_items.append({
                                    "CR_DATE": it.get('CR_DATE'),
                                    "LIBNATCR": it.get('LIBNATCR'),
                                    "_snippet": str(it)[:200]
                                })
                            except Exception:
                                continue
                    except Exception:
                        pass
                    details.append({
                        "filename": filename,
                        "items_before": items_before,
                        "items_after": items_after,
                        "bytes_before": bytes_before,
                        "bytes_after": bytes_after,
                        "filter_date": filter_date,
                        "preview": preview_items
                    })
                    if idx == 0:
                        first_stats = {
                            "items_before": items_before,
                            "items_after": items_after,
                            "bytes_before": bytes_before,
                            "bytes_after": bytes_after,
                            "reduction_percent": (0.0 if items_before == 0 else round(100.0 * (items_before - items_after) / max(items_before, 1), 2)),
                            "filter_date": filter_date
                        }
                else:
                    r = stats.get('reason', 'unknown_reason') if isinstance(stats, dict) else 'unknown_reason'
                    reason = f"{filename}: filtering_not_applied ({r})"
                    logger.warning(f"[JSON-FILTER-CHECK] {reason}")
                    reasons.append(reason)

            if matched_count == 0:
                reason_msg = "; ".join(reasons[:5])
                msg = f"Filtering could not be applied to any JSON document. Reasons: {reason_msg}"
                logger.warning(f"[JSON-FILTER-CHECK] {msg}")
                raise ValidationException(msg)

            # Compute overall reduction percent based on bytes (fallback to 0 if no bytes)
            overall_reduction_percent = 0.0
            try:
                if total_bytes_before > 0:
                    overall_reduction_percent = round(100.0 * (total_bytes_before - total_bytes_after) / total_bytes_before, 2)
            except Exception:
                overall_reduction_percent = 0.0

            return {
                "total_json_documents": len(json_docs),
                "matched_json_documents": matched_count,
                "first_json": first_stats,
                "details": details,
                # New overall totals (non-breaking)
                "total_bytes_before": total_bytes_before,
                "total_bytes_after": total_bytes_after,
                "overall_reduction_percent": overall_reduction_percent,
                "total_items_before": total_items_before,
                "total_items_after": total_items_after
            }
        except ValidationException:
            raise
        except Exception as e:
            import traceback
            logger.error(f"JSON filter check failed: {e}")
            logger.error(traceback.format_exc())
            raise DatabaseException(f"JSON filter check failed: {str(e)}")
    
    def update_report_with_content(self, report_uuid: str, report_data: Dict[str, Any]) -> Report:
        """
        Update a report record with generated content and honor provided status.
        """
        try:
            # Get the existing report
            existing_report = self.get_report_by_uuid(report_uuid)
            
            # Update with generated content
            update_data = {
                "status": report_data.get("status", "COMPLETED"),
                "content": report_data["content"],
                "metadata": report_data["metadata"],
                "file_size": report_data["file_size"],
                "character_count": report_data["character_count"],
                "word_count": report_data["word_count"],
                "elements": report_data.get("elements", [])
            }
            
            # Update in repository
            updated_report = self.repository.update(report_uuid, update_data)
            logger.info(f"Updated report {report_uuid} with generated content")
            return updated_report
            
        except Exception as e:
            logger.error(f"Failed to update report {report_uuid} with content: {e}")
            raise DatabaseException(f"Report update failed: {str(e)}")
    
    def update_report_status(self, report_uuid: str, status: str, error_message: Optional[str] = None) -> Report:
        """
        Update a report's status and optionally add error information.
        """
        try:
            update_data = {"status": status}
            
            if error_message:
                if not update_data.get("metadata"):
                    update_data["metadata"] = {}
                update_data["metadata"]["error"] = error_message
                update_data["metadata"]["failed_at"] = datetime.now().isoformat()
            
            updated_report = self.repository.update(report_uuid, update_data)
            logger.info(f"Updated report {report_uuid} status to {status}")
            return updated_report
            
        except Exception as e:
            logger.error(f"Failed to update report {report_uuid} status: {e}")
            raise DatabaseException(f"Report status update failed: {str(e)}")

    async def generate(self, patient_id: str, report_title: Optional[str] = None) -> Report:
        """
        Generate a comprehensive MDT report for a patient (synchronous version).  
        Args:
            patient_id: The patient ID to generate the report for
            report_title: Optional custom title for the report 
        Returns:
            The generated Report object
        """
        try:
            logger.info(f"Starting MDT report generation for patient {patient_id}")
            
            # Generate the MDT report
            report_data = await self.mdt_generator.generate_mdt_report(patient_id, report_title, "high", None)
            
            # Create the report in the database
            report = self.create_report(report_data)
            
            logger.info(f"MDT report generated successfully for patient {patient_id} - UUID: {report.uuid}")
            return report
            
        except ValidationException as e:
            logger.error(f"Validation error during MDT report generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate MDT report for patient {patient_id}: {e}")
            raise DatabaseException(f"MDT report generation failed: {str(e)}")
    
    def get_report_statistics(self, patient_id: str) -> Dict[str, Any]:
        """Get statistics about reports for a patient"""
        try:
            reports = self.repository.get_by_patient_id(patient_id, skip=0, limit=1000)
            
            stats = {
                "total_reports": len(reports),
                "reports_by_status": {},
                "total_characters": 0,
                "total_words": 0,
                "latest_report_date": None
            }
            
            for report in reports:
                # Count by status
                status = report.status
                stats["reports_by_status"][status] = stats["reports_by_status"].get(status, 0) + 1
                
                # Sum characters and words
                stats["total_characters"] += report.character_count or 0
                stats["total_words"] += report.word_count or 0
                
                # Track latest report
                if not stats["latest_report_date"] or report.created_at > stats["latest_report_date"]:
                    stats["latest_report_date"] = report.created_at
            
            return stats
            
        except DatabaseException:
            raise 