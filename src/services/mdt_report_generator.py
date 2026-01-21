"""  
Enhanced MDT Report Generator Service - Simplified Text-Based Version  
  
Uses simplified text extraction and focuses on NER processing.  
"""  
  
import logging  
import json  
import uuid  
import asyncio  
from typing import Dict, List, Any, Optional  
from datetime import datetime, timezone  
import hashlib
import time
from pathlib import Path  
import os
import base64
  
# Configure logging to avoid file creation issues  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  
    handlers=[logging.StreamHandler()]  # Console only  
)  
  
# Existing imports (unchanged)  
from services.patient_document_service import PatientDocumentService  
from domain.entities.patient_document import PatientDocument  
from utils.exceptions import ValidationException  
  
# NEW: Integrated processing imports  
from services.ner_workflow_orchestrator import extract_entities_workflow
from config.ner_config import settings as ner_settings
from config.settings import settings as app_settings
from repositories.generation_repository import GenerationRepository
from domain.entities.generation import GenerationLog
from utils.json_field_mapper import get_field_mapper
  
logger = logging.getLogger(__name__)  
  

def _resolve_current_llm_model() -> str:
  """Resolve the current LLM model as selected via the settings API/UI.

  Priority:
  1) Explicit environment variable LLM_MODEL (set by settings_controller)
  2) app_settings.gpt_open_model (OpenAI/Ollama path)
  3) app_settings.mistral_model (Mistral path)
  4) ner_settings.mistral_model (legacy fallback)
  """
  return (
    os.environ.get("LLM_MODEL")
    or getattr(app_settings, "gpt_open_model", None)
    or getattr(app_settings, "mistral_model", None)
    or ner_settings.mistral_model
  )

  
class MDTReportGenerator:  
    """Enhanced MDT Report Generator with simplified text processing."""  
      
    def __init__(self):  
        self.patient_document_service = PatientDocumentService()  
        self._entity_definitions = None  
        self._entity_config_json = None  
        self._active_template_id = None  # Track which template was used for GT consistency
        self.generation_repository = GenerationRepository()
  

    async def generate_mdt_report(self, patient_id: str, report_title: Optional[str] = None, reasoning_effort: Optional[str] = None, json_date_from: Optional[str] = None, json_auto_filter: Optional[bool] = False) -> Dict[str, Any]:  
        """Generate MDT report using simplified text extraction pipeline."""  
        try:  
            logger.info(f"Starting enhanced MDT report generation for patient {patient_id}")  
            # Timing: request arrival
            request_timestamp_utc = datetime.now(timezone.utc)
            start_perf = time.perf_counter()
            
            # Load entity definitions  
            logger.info("Loading entity definitions...")  
            await self._load_entity_definitions()  
            
            # Get documents from existing MongoDB  
            logger.info("Retrieving documents from MongoDB...")  
            documents = await self._get_processed_documents(patient_id)  
            if not documents:  
                raise ValidationException(f"No processed documents found for patient {patient_id}")  
            
            # Extract text content  
            logger.info("Extracting text from documents...")  
            text_documents = self._extract_text_from_all_documents(documents, json_date_from=json_date_from, json_auto_filter=json_auto_filter)  
            if not text_documents:  
                raise ValidationException(f"No text content could be extracted from documents")  
            
            # Prepare text documents for NER  
            logger.info("Preparing documents for NER...")  
            chunked_docs = self._prepare_text_documents_for_ner(text_documents, patient_id)  
            if not chunked_docs:  
                raise ValidationException(f"No documents could be prepared for NER processing")  
            
            # Extract entities from ALL documents at once  
            logger.info("Starting NER entity extraction...")  
            ner_results = await self._extract_entities(chunked_docs, reasoning_effort=reasoning_effort)  
            logger.info("NER entity extraction completed")  

            # Minimal normalization: ensure ner_results has an 'entities' array
            if isinstance(ner_results, dict) and "entities" not in ner_results:
                try:
                    flattened = []
                    for ptype, pdata in ner_results.items():
                        if isinstance(pdata, dict) and "found_entities" in pdata:
                            for ent in (pdata.get("found_entities") or []):
                                if isinstance(ent, dict):
                                    item = ent.copy()
                                    item.setdefault("processing_type", ptype)
                                    flattened.append(item)
                    ner_results = {
                        "entities": flattened,
                        "raw_results_by_type": ner_results,
                        "summary": {
                            "total_entities": len(flattened),
                            "by_processing_type": {
                                p: len(v.get("found_entities", []))
                                for p, v in ner_results.items()
                                if isinstance(v, dict)
                            },
                        },
                    }
                except Exception as norm_err:
                    logger.error(f"Failed to normalize ner_results: {norm_err}")
                    raise
            
            # Sort documents chronologically  
            logger.info("Creating report structure...")  
            documents.sort(key=lambda x: x.created_at)  
            
            # Create report content with NER results  
            report_content = {  
                "ner_results": ner_results,  
                "summary": {  
                    "total_documents": len(documents),  
                    "text_documents_processed": len(text_documents),  
                    "entities_extracted": self._count_found_entities(ner_results.get('entities', [])),  
                    "document_types": list(set(getattr(doc, 'type', 'unknown') for doc in documents)),  
                    "date_range": {  
                        "earliest": documents[0].created_at.isoformat() if documents else None,  
                        "latest": documents[-1].created_at.isoformat() if documents else None  
                    }  
                }  
            }  
            
            # Create final report  
            logger.info("Creating final report data...")  
            report_data = self._create_report_data(  
                patient_id, report_content, report_title, len(text_documents)  
            )  
            
            logger.info(f"Enhanced MDT report generation completed for patient {patient_id}")  

            # Persist generation log (success)
            try:
                filenames = sorted([d.get("filename", "") for d in text_documents if d.get("filename")])
                filenames_hash = self._compute_filenames_hash(filenames)
                elapsed_seconds = float(time.perf_counter() - start_perf)
                found_entities = self._count_found_entities(ner_results.get('entities', []))
                
                # Add processing time to report data for UI display
                report_data["elapsed_seconds"] = elapsed_seconds

                generation_log = GenerationLog(
                    uuid=str(uuid.uuid4()),
                    timestamp_utc=request_timestamp_utc,
                    patient_id=patient_id,
                    model_llm=_resolve_current_llm_model(),
                    max_entities_per_batch=ner_settings.max_entities_per_batch,
                    aggregation_batch_size=ner_settings.aggregation_batch_size,
                    max_content_size=ner_settings.max_content_size,
                    chunk_overlapping=ner_settings.chunk_overlapping,
                    max_concurrent_requests=ner_settings.max_concurrent_requests,
                    report_title=report_title,
                    filenames_hash=filenames_hash,
                    elapsed_seconds=elapsed_seconds,
                    found_entities=found_entities,
                    report=report_data,  # Use report_data which includes uuid
                    status="COMPLETED",
                    error=None,
                )
                self.generation_repository.create(generation_log)
            except Exception as log_err:
                logger.error(f"Failed to persist generation log (success path): {log_err}")

            return report_data  
            
        except Exception as e:  
            logger.error(f"MDT report generation failed for patient {patient_id}: {str(e)}")  
            logger.error(f"Error type: {type(e).__name__}")  
            
            # Log full traceback  
            import traceback  
            logger.error(f"Full traceback: {traceback.format_exc()}")  
            
            # Fail fast: propagate the error
            raise
    
    async def generate_mdt_report_with_progress(
        self, 
        patient_id: str, 
        report_title: Optional[str] = None, 
        progress_callback: Optional[callable] = None,
        reasoning_effort: Optional[str] = None,
        ner_config: Optional[Dict[str, Any]] = None,
        json_date_from: Optional[str] = None,
        json_auto_filter: Optional[bool] = False
    ) -> Dict[str, Any]:
        """Generate MDT report with real-time progress updates.
        
        Args:
            patient_id: The patient ID to generate the report for
            report_title: Optional custom title for the report
            progress_callback: Optional callback function for progress updates
            reasoning_effort: Optional reasoning effort level (low, medium, high)
            ner_config: Optional NER configuration parameters
        
        Returns:
            Dictionary containing the generated report data
        """
        try:
            logger.info(f"Starting enhanced MDT report generation with progress for patient {patient_id}")
            # Timing: request arrival
            request_timestamp_utc = datetime.now(timezone.utc)
            start_perf = time.perf_counter()
            
            # Step 1: Load entity definitions (1% progress)
            if progress_callback:
                await progress_callback({
                    "status": "LOADING_DEFINITIONS",
                    "progress": 1,
                    "message": "Loading entity definitions...",
                    "current_step": "loading_definitions"
                })
            
            logger.info("Loading entity definitions...")
            await self._load_entity_definitions()
            
            # Step 2: Get documents from MongoDB (2% progress)
            if progress_callback:
                await progress_callback({
                    "status": "RETRIEVING_DOCUMENTS",
                    "progress": 2,
                    "message": "Retrieving documents from MongoDB...",
                    "current_step": "retrieving_documents"
                })
            
            logger.info("Retrieving documents from MongoDB...")
            documents = await self._get_processed_documents(patient_id)
            if not documents:
                raise ValidationException(f"No processed documents found for patient {patient_id}")
            
            # Step 3: Extract text content (3% progress)
            if progress_callback:
                await progress_callback({
                    "status": "EXTRACTING_TEXT",
                    "progress": 3,
                    "message": f"Extracting text from {len(documents)} documents...",
                    "current_step": "extracting_text",
                    "documents_found": len(documents)
                })
            
            logger.info("Extracting text from documents...")
            text_documents = self._extract_text_from_all_documents(documents, json_date_from=json_date_from, json_auto_filter=json_auto_filter)
            if not text_documents:
                raise ValidationException(f"No text content could be extracted from documents")
            
            # Step 4: Prepare documents for NER (4% progress)
            if progress_callback:
                await progress_callback({
                    "status": "PREPARING_DOCUMENTS",
                    "progress": 4,
                    "message": f"Preparing {len(text_documents)} documents for NER processing...",
                    "current_step": "preparing_documents",
                    "text_documents_processed": len(text_documents)
                })
            
            logger.info("Preparing documents for NER...")
            chunked_docs = self._prepare_text_documents_for_ner(text_documents, patient_id)
            if not chunked_docs:
                raise ValidationException(f"No documents could be prepared for NER processing")
            
            # Step 5: Extract entities - This is the longest step (5% to 95% progress)
            if progress_callback:
                await progress_callback({
                    "status": "EXTRACTING_ENTITIES",
                    "progress": 5,
                    "message": f"Starting NER entity extraction on {len(chunked_docs)} document chunks...",
                    "current_step": "extracting_entities",
                    "chunked_documents": len(chunked_docs)
                })
            
            logger.info("Starting NER entity extraction...")
            ner_results = await self._extract_entities_with_progress(chunked_docs, progress_callback, reasoning_effort=reasoning_effort, ner_config=ner_config)
            logger.info("NER entity extraction completed")

            # Minimal normalization: ensure ner_results has an 'entities' array
            if isinstance(ner_results, dict) and "entities" not in ner_results:
                try:
                    flattened = []
                    for ptype, pdata in ner_results.items():
                        if isinstance(pdata, dict) and "found_entities" in pdata:
                            for ent in (pdata.get("found_entities") or []):
                                if isinstance(ent, dict):
                                    item = ent.copy()
                                    item.setdefault("processing_type", ptype)
                                    flattened.append(item)
                    ner_results = {
                        "entities": flattened,
                        "raw_results_by_type": ner_results,
                        "summary": {
                            "total_entities": len(flattened),
                            "by_processing_type": {
                                p: len(v.get("found_entities", []))
                                for p, v in ner_results.items()
                                if isinstance(v, dict)
                            },
                        },
                    }
                except Exception as norm_err:
                    logger.error(f"Failed to normalize ner_results: {norm_err}")
                    raise
            
            # Step 6: Create report structure (99% progress)
            if progress_callback:
                await progress_callback({
                    "status": "CREATING_REPORT",
                    "progress": 99,
                    "message": "Creating report structure...",
                    "current_step": "creating_report"
                })
            
            logger.info("Creating report structure...")
            documents.sort(key=lambda x: x.created_at)
            
            # Create report content with NER results
            report_content = {
                "ner_results": ner_results,
                "summary": {
                    "total_documents": len(documents),
                    "text_documents_processed": len(text_documents),
                    "entities_extracted": self._count_found_entities(ner_results.get('entities', [])),
                    "document_types": list(set(getattr(doc, 'type', 'unknown') for doc in documents)),
                    "date_range": {
                        "earliest": documents[0].created_at.isoformat() if documents else None,
                        "latest": documents[-1].created_at.isoformat() if documents else None
                    }
                }
            }
            
            # Step 7: Create final report (100% progress)
            if progress_callback:
                await progress_callback({
                    "status": "FINALIZING_REPORT",
                    "progress": 100,
                    "message": "Creating final report data...",
                    "current_step": "finalizing_report",
                    "entities_extracted": len(ner_results.get('entities', []))
                })
            
            logger.info("Creating final report data...")
            report_data = self._create_report_data(
                patient_id, report_content, report_title, len(text_documents)
            )
            
            logger.info(f"Enhanced MDT report generation with progress completed for patient {patient_id}")

            # Persist generation log (success)
            try:
                filenames = sorted([d.get("filename", "") for d in text_documents if d.get("filename")])
                filenames_hash = self._compute_filenames_hash(filenames)
                elapsed_seconds = float(time.perf_counter() - start_perf)
                found_entities = self._count_found_entities(ner_results.get('entities', []))
                
                # Add processing time to report data for UI display
                report_data["elapsed_seconds"] = elapsed_seconds

                generation_log = GenerationLog(
                    uuid=str(uuid.uuid4()),
                    timestamp_utc=request_timestamp_utc,
                    patient_id=patient_id,
                    model_llm=_resolve_current_llm_model(),
                    max_entities_per_batch=ner_settings.max_entities_per_batch,
                    aggregation_batch_size=ner_settings.aggregation_batch_size,
                    max_content_size=ner_settings.max_content_size,
                    chunk_overlapping=ner_settings.chunk_overlapping,
                    max_concurrent_requests=ner_settings.max_concurrent_requests,
                    report_title=report_title,
                    filenames_hash=filenames_hash,
                    elapsed_seconds=elapsed_seconds,
                    found_entities=found_entities,
                    report=report_data,  # Use report_data which includes uuid
                    status="COMPLETED",
                    error=None,
                )
                self.generation_repository.create(generation_log)
            except Exception as log_err:
                logger.error(f"Failed to persist generation log (success path): {log_err}")

            return report_data
            
        except Exception as e:
            logger.error(f"MDT report generation with progress failed for patient {patient_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log full traceback
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Do not store failed generations per product requirement

            raise  # Re-raise the original exception  



    def _extract_text_from_all_documents(self, documents: List[PatientDocument], json_date_from: Optional[str] = None, json_auto_filter: Optional[bool] = False) -> List[Dict[str, Any]]:  
        """Extract plain text from all documents using simplified approach."""  
        text_documents = []  
          
        logger.info(f"Starting text extraction from {len(documents)} documents")  
          
        for i, doc in enumerate(documents):  
            try:  
                filename = getattr(doc, 'filename', f'document_{i}')  
                logger.debug(f"Extracting text from document {i+1}/{len(documents)}: {filename}")  
                  
                # Get extracted_data  
                extracted_data = getattr(doc, 'extracted_data', {}) or {}  

                # If requested, preprocess JSON documents using date or AUTO (from most recent RCP)
                filtered_json = None
                filtered_meta = None
                if (json_date_from or json_auto_filter) and isinstance(filename, str) and filename.lower().endswith('.json'):
                    try:
                        # Load original JSON from file_content
                        parsed_original = self._load_json_from_file_content(getattr(doc, 'file_content', None))
                        if isinstance(parsed_original, dict):
                            # Apply filter
                            if json_auto_filter:
                                filtered_json, stats = self._filter_json_auto(parsed_original)
                                filtered_meta = {"mode": "auto", "filter_date": stats.get("filter_date")}
                            else:
                                filtered_json, stats = self._preprocess_json_lcrs(parsed_original, json_date_from)
                                filtered_meta = {"mode": "date", "filter_date": stats.get("filter_date")}
                        else:
                            stats = {"reason": "original_json_not_available"}
                        if filtered_json is not None:
                            # Log success with size before/after
                            logger.info(
                                f"JSON PREPROCESS SUCCESS for {filename}: lCrs items before={stats.get('items_before')} after={stats.get('items_after')} "
                                f"bytes_before={stats.get('bytes_before')} bytes_after={stats.get('bytes_after')}"
                            )
                            # IMPORTANT: do NOT overwrite extracted_data; preserve original text/content
                        else:
                            # Nothing to do (no lCrs or invalid input)
                            logger.info(f"JSON PREPROCESS SKIPPED for {filename}: {stats.get('reason', 'no-op')}")
                    except Exception as prep_err:
                        # Fallback: continue with original data
                        logger.error(f"JSON PREPROCESS FAILED for {filename}: {prep_err}")
                        try:
                            logger.exception(prep_err)
                        except Exception:
                            pass
                  
                # LOG the actual structure for debugging  
                logger.debug(f"Document {filename}: extracted_data type = {type(extracted_data)}")  
                if isinstance(extracted_data, dict):  
                    logger.debug(f"Document {filename}: keys = {list(extracted_data.keys())}")  
                  
                # Use simplified text extraction from ORIGINAL extracted_data  
                document_text = self._extract_simple_text_content(extracted_data, filename)  
                # If a filtered JSON is available for a .json file, use it as the text for NER
                if filtered_json is not None and isinstance(filename, str) and filename.lower().endswith('.json'):
                    try:
                        original_len = len(document_text or '')
                    except Exception:
                        original_len = 0
                    try:
                        reduced_text = json.dumps(filtered_json, ensure_ascii=False)
                    except Exception:
                        reduced_text = str(filtered_json)
                    logger.info(f"Using filtered JSON text for {filename}: {original_len} -> {len(reduced_text)} chars")
                    document_text = reduced_text
                  
                if document_text and len(document_text.strip()) > 10:  
                    text_doc = {  
                        "uuid": getattr(doc, 'uuid', str(uuid.uuid4())),  
                        "filename": filename,  
                        "document_type": getattr(doc, 'type', 'text_document'),  
                        "status": getattr(doc, 'status', 'processed'),  
                        "created_at": doc.created_at.isoformat(),  
                        "text_content": document_text,  
                        "text_length": len(document_text),  
                        "original_extracted_data": getattr(doc, 'extracted_data', {}) or {},  
                        "preprocessed_extracted_data": (filtered_json if filtered_json is not None else {}),
                        "filtered_json": filtered_json,
                        "filtered_json_meta": filtered_meta
                    }  
                    text_documents.append(text_doc)  
                    logger.info(f"✅ Successfully extracted {len(document_text)} chars from {filename}")  
                else:  
                    logger.warning(f"❌ No sufficient text content found in {filename}")  
                  
            except Exception as e:  
                filename = getattr(doc, 'filename', f'document_{i}')  
                logger.error(f"Failed to extract text from {filename}: {e}")  
                continue  
          
        logger.info(f"Successfully extracted text from {len(text_documents)}/{len(documents)} documents")  
        return text_documents  
  
    def _extract_simple_text_content(self, extracted_data: Any, filename: str) -> str:  
        """  
        Simplified text extraction - just get whatever text is available.  
        For JSON files with lCrs: serializes the full JSON structure.
        For other files: extracts text from standard keys.
        """  
        text_parts = []  
          
        try:  
            if not extracted_data:  
                logger.debug(f"{filename}: No extracted_data")  
                return ""  
              
            # If it's already a string, use it  
            if isinstance(extracted_data, str):  
                logger.debug(f"{filename}: extracted_data is string ({len(extracted_data)} chars)")  
                return self._clean_text(extracted_data)  
              
            # If it's a dict, look for text content  
            if isinstance(extracted_data, dict):  
                
                # NEW: Handle JSON files with lCrs structure
                # For JSON documents, serialize the full structure as text
                # The actual lCr splitting happens in _prepare_text_documents_for_ner
                if 'lCrs' in extracted_data:
                    lcrs_count = len(extracted_data.get('lCrs', []))
                    logger.info(f"{filename}: Found lCrs structure ({lcrs_count} reports), serializing JSON")
                    try:
                        json_text = json.dumps(extracted_data, ensure_ascii=False)
                        logger.info(f"{filename}: Serialized JSON ({len(json_text)} chars)")
                        return json_text
                    except Exception as e:
                        logger.warning(f"{filename}: JSON serialization failed: {e}")
                        # Fall through to other strategies
                  
                # Strategy 1: Direct text keys (most common)  
                text_keys = ['text', 'content', 'body', 'document_text', 'full_text', 'raw_text']  
                for key in text_keys:  
                    if key in extracted_data:  
                        value = extracted_data[key]  
                        if isinstance(value, str) and len(value.strip()) > 5:  
                            text_parts.append(value)  
                            logger.debug(f"{filename}: Found text in '{key}' ({len(value)} chars)")  
                  
                # Strategy 2: Nested content (like simplified service structure)  
                if 'extracted_data' in extracted_data:  
                    nested = extracted_data['extracted_data']  
                    if isinstance(nested, dict):  
                        for key in text_keys:  
                            if key in nested and isinstance(nested[key], str):  
                                text_parts.append(nested[key])  
                                logger.debug(f"{filename}: Found nested text in 'extracted_data.{key}'")  
                  
                # Strategy 3: If still no content, be aggressive  
                if not text_parts:  
                    logger.debug(f"{filename}: No standard text found, using aggressive extraction")  
                    for key, value in extracted_data.items():  
                        if isinstance(value, str) and len(value.strip()) > 20:  
                            text_parts.append(value)  
                            logger.debug(f"{filename}: Using '{key}' as text content ({len(value)} chars)")  
              
            # Combine all text parts  
            combined_text = '\n\n'.join(text_parts) if text_parts else ""  
            cleaned_text = self._clean_text(combined_text)  
              
            logger.debug(f"{filename}: Final text length: {len(cleaned_text)} chars")  
            return cleaned_text  
              
        except Exception as e:  
            logger.error(f"Text extraction failed for {filename}: {e}")  
            return ""  
  
    def _clean_text(self, text: str) -> str:  
        """Clean text content (same as simplified service)."""  
        if not text:  
            return ""  
          
        # Basic text cleaning  
        cleaned = text.strip()  
          
        # Remove excessive whitespace  
        import re  
        cleaned = re.sub(r'\s+', ' ', cleaned)  
          
        # Remove control characters but keep newlines and tabs  
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\t')  
          
        return cleaned  

    def _format_patient_info(self, pat: Dict[str, Any]) -> str:
        """Format patient info (pat section) as readable text for LLM context.
        
        Args:
            pat: Patient section from the JSON document
            
        Returns:
            Formatted patient info string
        """
        if not pat or not isinstance(pat, dict):
            return ""
        
        lines = ["=== INFORMATIONS PATIENT ==="]
        
        # Common patient fields to include
        field_labels = {
            'NumdosGR': 'Numéro dossier',
            'Nom': 'Nom',
            'Prenom': 'Prénom',
            'NomNaissance': 'Nom de naissance',
            'Sexe': 'Sexe',
            'DateNaissance': 'Date de naissance',
            'Age': 'Age',
            'Adresse': 'Adresse',
            'CodePostal': 'Code postal',
            'Ville': 'Ville',
            'Tel': 'Téléphone',
            'Email': 'Email',
            'MedecinTraitant': 'Médecin traitant',
            'NumeroSS': 'Numéro SS',
        }
        
        for field, label in field_labels.items():
            value = pat.get(field)
            if value and str(value).strip():
                lines.append(f"{label}: {value}")
        
        # Include any other fields not in the common list
        for key, value in pat.items():
            if key not in field_labels and value and str(value).strip():
                # Skip complex nested objects
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{key}: {value}")
        
        return '\n'.join(lines) if len(lines) > 1 else ""

    def _format_lcr_content(self, lcr: Dict[str, Any], field_mapper) -> str:
        """Format full lCr content as readable text for LLM.
        
        Includes all lCr fields (not just TEXTE) to provide full context.
        
        Args:
            lcr: Clinical report dictionary
            field_mapper: JSONFieldMapper for dynamic field access
            
        Returns:
            Formatted lCr content string
        """
        if not lcr or not isinstance(lcr, dict):
            return ""
        
        lines = ["=== COMPTE RENDU CLINIQUE ==="]
        
        # Add metadata fields first
        metadata_fields = [
            ('LIBNATCR', 'Type de document'),
            ('CR_DATE', 'Date'),
            ('TITLE', 'Titre'),
            ('SERVICE', 'Service'),
            ('ID', 'ID'),
        ]
        
        for field, label in metadata_fields:
            # Try field mapper first, then direct access
            value = None
            if field == 'LIBNATCR':
                value = field_mapper.get_report_type(lcr)
            elif field == 'CR_DATE':
                value = field_mapper.get_date(lcr)
            elif field == 'TITLE':
                value = field_mapper.get_title(lcr)
            elif field == 'SERVICE':
                value = field_mapper.get_service(lcr)
            elif field == 'ID':
                value = field_mapper.get_id(lcr)
            
            if not value:
                value = lcr.get(field)
            
            if value and str(value).strip():
                lines.append(f"{label}: {value}")
        
        lines.append("---")
        
        # Add the main text content (TEXTE)
        texte = field_mapper.get_text_content(lcr)
        if texte and str(texte).strip():
            lines.append(str(texte).strip())
        
        # Add any other significant fields that might contain useful info
        skip_fields = {'TEXTE', 'LIBNATCR', 'CR_DATE', 'TITLE', 'SERVICE', 'ID', 'CR_NAT', 'CR_TITLE'}
        for key, value in lcr.items():
            if key.upper() not in skip_fields and value:
                if isinstance(value, str) and len(value.strip()) > 10:
                    lines.append(f"\n{key}: {value}")
        
        return '\n'.join(lines)

    def _load_json_from_file_content(self, base64_content: Optional[str]) -> Optional[Dict[str, Any]]:
        """Decode base64 file_content and parse as JSON robustly. Returns dict or None.
        Tries multiple decodings and fallback extraction of JSON substring, logs safe previews on failure.
        """
        if not isinstance(base64_content, str) or not base64_content.strip():
            logger.debug("_load_json_from_file_content: empty or non-string base64_content")
            return None
        try:
            raw = base64.b64decode(base64_content)
        except Exception as e:
            logger.error(f"_load_json_from_file_content: base64 decode failed: {e}")
            return None

        encodings_to_try = ["utf-8", "utf-8-sig", "utf-16", "latin-1"]
        text: Optional[str] = None
        last_decode_error = None
        for enc in encodings_to_try:
            try:
                text = raw.decode(enc, errors='strict')
                break
            except Exception as de:
                last_decode_error = de
                continue

        if text is None:
            logger.error(f"_load_json_from_file_content: all decodings failed (last error: {last_decode_error})")
            return None

        # Strip BOM just in case and whitespace
        text = text.lstrip('\ufeff').strip()

        # Log a safe preview of the decoded text
        try:
            preview = (text[:500] + ('…' if len(text) > 500 else '')).replace('\n', ' ')
            logger.info(f"_load_json_from_file_content: decoded text length={len(text)} preview='{preview}'")
        except Exception:
            pass

        # Try direct JSON parse
        try:
            return json.loads(text)
        except Exception as je:
            # Fallback: attempt to extract JSON object substring
            try:
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    candidate = text[start:end+1]
                    return json.loads(candidate)
            except Exception as je2:
                # Log safe preview to help debug
                preview = text[:200].replace('\n', ' ') if isinstance(text, str) else ''
                logger.warning(f"_load_json_from_file_content: JSON parse failed; preview='{preview}' ... (len={len(text) if isinstance(text,str) else 0})")
                logger.warning(f"_load_json_from_file_content: errors: direct='{je}' fallback='{je2}'")
                return None
            # If candidate parse succeeded, we would have returned. If we reach here, it failed.
            preview = text[:200].replace('\n', ' ')
            logger.warning(f"_load_json_from_file_content: JSON parse failed (no valid substring). preview='{preview}'")
            return None

    def _decode_text_preview(self, base64_content: Optional[str], limit: int = 500) -> str:
        """Decode base64 content and return a safe text preview for logging/UI."""
        if not isinstance(base64_content, str) or not base64_content.strip():
            return ""
        try:
            raw = base64.b64decode(base64_content)
        except Exception:
            return ""
        for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                text = raw.decode(enc, errors='strict')
                text = text.lstrip('\ufeff').strip()
                return (text[:limit] + ('…' if len(text) > limit else '')).replace('\n', ' ')
            except Exception:
                continue
        return ""

    def _filter_json_auto(self, data: Any) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Filter from most recent RCP date; mirrors user's algorithm, returns (new_data, stats)."""
        stats: Dict[str, Any] = {}
        try:
            if not isinstance(data, dict):
                stats['reason'] = 'extracted_data_not_dict'
                return None, stats
            lcrs = data.get('lCrs')
            if not isinstance(lcrs, list):
                stats['reason'] = 'lCrs_missing_or_not_list'
                return None, stats
            # Compute sizes and counts before
            try:
                bytes_before = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            except Exception:
                bytes_before = None
            stats['bytes_before'] = bytes_before
            stats['items_before'] = len(lcrs)

            # Find most recent RCP date in CR_DATE
            rcp_dates: List[str] = []
            for item in lcrs:
                if isinstance(item, dict) and item.get('LIBNATCR') == 'RCP' and item.get('CR_DATE'):
                    rcp_dates.append(str(item['CR_DATE']))

            if not rcp_dates:
                stats['reason'] = 'no_rcp_found'
                return None, stats

            filter_date = max(rcp_dates)

            # Filter items by CR_DATE >= filter_date
            filtered: List[Any] = []
            for item in lcrs:
                try:
                    if not isinstance(item, dict):
                        continue
                    item_date = item.get('CR_DATE')
                    if item_date and str(item_date) >= filter_date:
                        filtered.append(item)
                except Exception:
                    continue

            # Sort filtered by CR_DATE descending
            try:
                filtered.sort(key=lambda it: str(it.get('CR_DATE', '')), reverse=True)
            except Exception:
                pass

            # Ensure the largest lCrs item (by character length) is included regardless of date
            try:
                def _item_chars(it):
                    try:
                        return len(json.dumps(it, ensure_ascii=False))
                    except Exception:
                        return len(str(it))
                def _same_item(a, b):
                    if isinstance(a, dict) and isinstance(b, dict):
                        for k in ("CLECR", "id", "UID"):
                            if k in a and k in b:
                                return a[k] == b[k]
                        try:
                            return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
                        except Exception:
                            return False
                    return a == b
                largest = None
                if isinstance(lcrs, list) and lcrs:
                    try:
                        largest = max(lcrs, key=_item_chars)
                    except Exception:
                        largest = max(lcrs, key=lambda it: len(str(it)))
                if largest is not None and not any(_same_item(largest, it) for it in filtered):
                    filtered.append(largest)
                    stats['largest_added'] = True
                    try:
                        stats['largest_len'] = _item_chars(largest)
                    except Exception:
                        pass
                    try:
                        filtered.sort(key=lambda it: str(it.get('CR_DATE', '')), reverse=True)
                    except Exception:
                        pass
                else:
                    stats['largest_added'] = False
            except Exception:
                pass

            new_data = dict(data)
            new_data['lCrs'] = filtered

            try:
                bytes_after = len(json.dumps(new_data, ensure_ascii=False).encode('utf-8'))
            except Exception:
                bytes_after = None
            stats['items_after'] = len(filtered)
            stats['bytes_after'] = bytes_after
            stats['filter_date'] = filter_date

            return new_data, stats
        except Exception as e:
            raise e
  
    def _prepare_text_documents_for_ner(self, text_documents: List[Dict], patient_id: str) -> List[Dict]:  
        """Prepare text documents for NER processing - ONE document per lCr (clinical report).
        
        This enables more granular source filtering as each lCr has its own metadata
        (LIBNATCR, CR_DATE, TITLE) which can be used for filtering during entity extraction.
        
        Uses JSONFieldMapper for dynamic field access to handle varying JSON structures.
        """  
        chunked_docs = []  
        lcr_count = 0
        fallback_count = 0
        
        # Get field mapper for dynamic field access
        field_mapper = get_field_mapper()
        
        logger.info(f"Preparing {len(text_documents)} text documents for NER (1 lCr = 1 Document)")  
        
        for doc in text_documents:  
            try:
                filename = doc.get('filename', 'unknown')
                
                # Get the filtered_json which contains lCrs (or fall back to original)
                filtered_json = doc.get('filtered_json') or doc.get('original_extracted_data') or {}
                lcrs = []
                
                # Try to extract lCrs array
                if isinstance(filtered_json, dict):
                    lcrs = filtered_json.get('lCrs', [])
                
                if not lcrs or not isinstance(lcrs, list):
                    # Fallback: treat entire document as one (no lCrs available)
                    text_content = doc.get('text_content', '')
                    if text_content and len(text_content.strip()) >= 10:
                        chunked_doc = {
                            "metadata": {
                                "patient_id": patient_id,
                                "document_id": doc['uuid'],
                                "document_type": doc['document_type'],
                                "filename": filename,
                                "report_type": "Document complet",
                                "LIBNATCR": "Document complet",
                                "CR_DATE": "",
                                "TITLE": "",
                                "created_at": doc['created_at'],
                                "filtered_json": filtered_json,
                                "filtered_json_meta": doc.get('filtered_json_meta'),
                                "lcr_mode": False
                            },
                            "chunks": [{
                                "content": text_content.strip(),
                                "section_id": "full_document",
                                "page_id": 1,
                                "category": "medical_document",
                                "metadata": {}
                            }]
                        }
                        chunked_docs.append(chunked_doc)
                        fallback_count += 1
                        logger.info(f"📄 {filename}: Prepared as single document (no lCrs) - {len(text_content)} chars")
                    continue
                
                # Extract patient info (pat section) to prepend to each lCr
                pat_section = filtered_json.get('pat', {}) if isinstance(filtered_json, dict) else {}
                pat_text = self._format_patient_info(pat_section) if pat_section else ""
                
                # ONE DOCUMENT PER lCr
                lcrs_processed = 0
                for idx, lcr in enumerate(lcrs):
                    if not isinstance(lcr, dict):
                        continue
                    
                    # Extract text content from lCr using dynamic field mapping
                    texte = field_mapper.get_text_content(lcr)
                    if not texte or len(str(texte).strip()) < 10:
                        continue  # Skip empty reports
                    
                    # Extract lCr-specific metadata using dynamic field mapping
                    libnatcr = field_mapper.get_report_type(lcr)
                    cr_date = field_mapper.get_date(lcr)
                    title = field_mapper.get_title(lcr)
                    service = field_mapper.get_service(lcr)
                    lcr_id = field_mapper.get_id(lcr)
                    
                    # Format created_at from CR_DATE for depth filtering
                    formatted_date = self._format_cr_date_for_metadata(cr_date)
                    
                    # Format full lCr content (all fields, not just TEXTE)
                    lcr_content = self._format_lcr_content(lcr, field_mapper)
                    
                    # OPTIMIZATION: Don't prepend pat here - store in metadata for merging
                    # pat_text will be prepended once per batch in entity_extraction_service
                    full_content = lcr_content
                    
                    # Create document with lCr's own metadata
                    chunked_doc = {
                        "metadata": {
                            "patient_id": patient_id,
                            "document_id": f"{doc['uuid']}_lcr_{idx}",
                            "document_type": doc['document_type'],
                            "filename": filename,
                            "lcr_index": idx,
                            "lcr_id": lcr_id,
                            # lCr-specific metadata for filtering
                            "report_type": libnatcr,
                            "LIBNATCR": libnatcr,
                            "CR_DATE": cr_date,
                            "TITLE": title,
                            "SERVICE": service,
                            "created_at": formatted_date or doc['created_at'],
                            "filtered_json": filtered_json,
                            "filtered_json_meta": doc.get('filtered_json_meta'),
                            "lcr_mode": True,
                            "pat_text": pat_text  # Store pat_text for batch merging
                        },
                        "chunks": [{
                            "content": full_content,
                            "section_id": f"lcr_{idx}",
                            "page_id": 1,
                            "category": "medical_document",
                            "metadata": {
                                "CR_DATE": cr_date,
                                "LIBNATCR": libnatcr,
                                "TITLE": title,
                            }
                        }]
                    }
                    
                    chunked_docs.append(chunked_doc)
                    lcrs_processed += 1
                    lcr_count += 1
                    logger.debug(f"  Created document for lCr[{idx}]: {libnatcr} - {cr_date} ({len(full_content)} chars)")
                
                if lcrs_processed > 0:
                    logger.info(f"📄 {filename}: Split into {lcrs_processed} lCr documents")
                else:
                    # All lCrs were empty, fall back to full text if available
                    text_content = doc.get('text_content', '')
                    if text_content and len(text_content.strip()) >= 10:
                        chunked_doc = {
                            "metadata": {
                                "patient_id": patient_id,
                                "document_id": doc['uuid'],
                                "document_type": doc['document_type'],
                                "filename": filename,
                                "report_type": "Document complet",
                                "LIBNATCR": "Document complet",
                                "created_at": doc['created_at'],
                                "filtered_json": filtered_json,
                                "lcr_mode": False
                            },
                            "chunks": [{
                                "content": text_content.strip(),
                                "section_id": "full_document",
                                "page_id": 1,
                                "category": "medical_document"
                            }]
                        }
                        chunked_docs.append(chunked_doc)
                        fallback_count += 1
                        logger.warning(f"⚠️ {filename}: All lCrs empty, using full text fallback")
                    
            except Exception as e:  
                logger.error(f"Failed to prepare {doc.get('filename', 'unknown')} for NER: {e}")  
                continue  
        
        logger.info(f"✅ Successfully prepared {len(chunked_docs)} documents for NER "
                   f"(lCr documents: {lcr_count}, fallback documents: {fallback_count})")  
        
        # DEBUG: Show what we're sending to NER  
        if chunked_docs:  
            total_chars = sum(len(doc['chunks'][0]['content']) for doc in chunked_docs)  
            avg_chars = total_chars // len(chunked_docs) if chunked_docs else 0
            logger.info(f"Documents prepared: {len(chunked_docs)} docs, avg size: {avg_chars} chars")  
            
            # Show sample of different document types
            lcr_sample = next((d for d in chunked_docs if d['metadata'].get('lcr_mode')), None)
            if lcr_sample:
                logger.debug(f"Sample lCr document:")
                logger.debug(f"  LIBNATCR: {lcr_sample['metadata'].get('LIBNATCR')}")
                logger.debug(f"  CR_DATE: {lcr_sample['metadata'].get('CR_DATE')}")
                logger.debug(f"  Content length: {len(lcr_sample['chunks'][0]['content'])} chars")
        
        return chunked_docs
    
    def _format_cr_date_for_metadata(self, cr_date: str) -> Optional[str]:
        """Convert CR_DATE (YYYYMMDD format) to ISO format for metadata.
        
        This enables depth filtering by date as the created_at field is used
        for sorting and filtering documents by recency.
        """
        if not cr_date:
            return None
        
        try:
            # Handle YYYYMMDD format
            date_str = str(cr_date).strip()
            if len(date_str) == 8 and date_str.isdigit():
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}-{month}-{day}T00:00:00"
            
            # Handle YYYY-MM-DD format
            if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                return f"{date_str}T00:00:00"
            
            # Already in ISO format
            if 'T' in date_str:
                return date_str
            
            return None
        except Exception:
            return None  
    

    async def _extract_entities(self, chunked_docs: List[Dict], reasoning_effort: Optional[str] = "high", ner_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract entities from chunked documents."""
        if not chunked_docs:
            logger.warning("No chunked documents available for entity extraction")
            return {"entities": [], "summary": {"total_entities": 0}}
        
        try:
            logger.info("Calling extract_entities_workflow...")
            
            ner_results = await extract_entities_workflow(  # Direct async call, no timeout
                json_data=self._entity_config_json,
                chunked_docs=chunked_docs,
                progress_callback=None,
                reasoning_effort=reasoning_effort,
                ner_config=ner_config
            )
      
            logger.info("extract_entities_workflow completed, processing results...")
            logger.debug(f"Raw NER results type: {type(ner_results)}")
            
            # Flatten results from processing types with deduplication
            all_entities = []
            entity_name_tracker = {}  # Track entity names to detect duplicates
            duplicate_count = 0
            
            # DEBUG: Log initial extraction summary
            
            if isinstance(ner_results, dict):
                logger.debug(f"NER results keys: {list(ner_results.keys())}")
                
                # DEBUG: Count total entities before deduplication
                total_entities_before = 0
                for ptype, presults in ner_results.items():
                    if isinstance(presults, dict) and 'found_entities' in presults:
                        total_entities_before += len(presults['found_entities'])
                
                for processing_type, type_results in ner_results.items():
                    logger.debug(f"Processing type '{processing_type}': {type(type_results)}")
                    
                    if isinstance(type_results, dict) and 'found_entities' in type_results:
                        found_entities = type_results['found_entities']
                        logger.debug(f"Found {len(found_entities)} entities for type '{processing_type}'")
                        
                        # DEBUG: Log processing type details
                        entity_names_in_type = [e.get('entity_name', '') for e in found_entities]
                        
                        for entity in found_entities:
                            try:
                                entity_name = entity.get('entity_name', '')
                                
                                  
                                # DEDUPLICATION LOGIC: Check if entity name already exists
                                if entity_name in entity_name_tracker:
                                    duplicate_count += 1
                                    existing_processing_type = entity_name_tracker[entity_name]['processing_type']
                                    
                              
                                    continue  # Skip this duplicate entity
                                
                                # Add processing_type to entity and track it
                                entity['processing_type'] = processing_type
                                entity_name_tracker[entity_name] = entity
                                all_entities.append(entity)
                                
                            except Exception as entity_error:
                                logger.error(f"Error processing individual entity: {entity_error}")
                                logger.debug(f"Problematic entity: {entity}")
                                continue
                    else:
                        logger.warning(f"Unexpected structure for processing type '{processing_type}': {type_results}")
            else:
                logger.error(f"NER results is not a dict: {type(ner_results)}")
                logger.debug(f"NER results content: {ner_results}")
            
            
            # DEBUG: List all final entity names
            final_entity_names = [e.get('entity_name', '') for e in all_entities]
            
            # CRITICAL FIX: Ensure all 37 entities are accounted for (found + not_found = 37)
            # Parse entity definitions to get all expected entities
            import json
            config = json.loads(self._entity_config_json)
            all_expected_entities = [entity.get("name", "") for entity in config.get("entities", [])]
            
            # Find which entities were not found
            found_entity_names = set(final_entity_names)
            not_found_entity_names = [name for name in all_expected_entities if name not in found_entity_names]
            
            # Add not_found entities to ensure total = 37
            for not_found_name in not_found_entity_names:
                not_found_entity = {
                    "entity_name": not_found_name,
                    "value": "",  # Empty value for not found
                    "metadata": {"status": "not_found"},
                    "processing_type": "not_found"
                }
                all_entities.append(not_found_entity)
            
            
            
            

            # Log deduplication summary
            if duplicate_count > 0:
                logger.info(f"DEDUPLICATION SUMMARY: {duplicate_count} duplicate entity occurrences were found and handled correctly. "
                           f"Each entity name now appears only once with the first value found. All 37 entities are accounted for "
                           f"(either found with values or marked as not_found). This is expected behavior for first_match entities.")
            else:
                logger.info(f"No duplicate entities detected. All {len(all_entities)} entities are unique.")
            
            logger.info(f"Creating final results structure with {len(all_entities)} total entities...")
            
            # Add programmatic "Date de présentation" as today's date
            today_date = datetime.now().strftime('%d/%m/%Y')
            presentation_date_entity = {
                "entity_name": "Date de présentation",
                "entity_value": today_date,
                "entity_type": "date",
                "processing_type": "programmatic",
                "confidence": 1.0,
                "source_document": "system_generated",
                "extraction_context": f"Automatically set to MDT meeting date: {today_date}",
                "notes": "Date de présentation du dossier à la RCP (générée automatiquement)"
            }
            
            # Add to entities list
            all_entities.append(presentation_date_entity)
            logger.info(f"Added programmatic 'Date de présentation': {today_date}")
            
            final_results = {
                "disclaimer": "Généré par IA — non destiné à un usage clinique." ,
                "entities": all_entities,
                "raw_results_by_type": ner_results,
                "summary": {
                    "total_entities": len(all_entities),
                    "duplicates_removed": duplicate_count,
                    "programmatic_entities_added": 1,
                    "by_processing_type": {
                        ptype: len(pdata.get('found_entities', []))
                        for ptype, pdata in ner_results.items()
                        if isinstance(pdata, dict)
                    }
                }
            }
            
            logger.info(f"Entity extraction completed successfully: {len(all_entities)} total entities extracted (after deduplication)")
            return final_results
            
        except asyncio.TimeoutError as timeout_error:
            logger.error(f"Entity extraction timed out unexpectedly: {timeout_error}")
            # Propagate failure immediately
            raise
            
        except Exception as e:
            logger.error(f"Entity extraction failed with error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log full traceback
            import traceback
            full_traceback = traceback.format_exc()
            logger.error(f"Full traceback: {full_traceback}")
            
            # Try to get more details about the error (logging only)
            try:
                error_details = {
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "chunked_docs_count": len(chunked_docs),
                    "entity_config_available": bool(self._entity_config_json)
                }
                logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
            except Exception as detail_error:
                logger.error(f"Could not create error details: {detail_error}")
            
            # Fail fast: propagate error instead of returning an error dict
            raise


    def _compute_filenames_hash(self, filenames: List[str]) -> str:
        """Compute deterministic SHA256 hash from sorted filenames list."""
        try:
            if not filenames:
                return hashlib.sha256(b"").hexdigest()
            # Ensure deterministic order
            sorted_names = sorted([str(name) for name in filenames])
            joined = "\n".join(sorted_names).encode("utf-8")
            return hashlib.sha256(joined).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute filenames hash: {e}")
            return hashlib.sha256(b"").hexdigest()

    def _count_found_entities(self, entities: Any) -> int:
        """Count only entities actually found by NER, excluding not_found and programmatic ones."""
        try:
            if not entities:
                return 0
            count = 0
            for ent in entities:
                try:
                    if not isinstance(ent, dict):
                        continue
                    processing_type = ent.get("processing_type", "")
                    if processing_type in ("not_found", "programmatic"):
                        continue
                    has_value = False
                    if "value" in ent and ent.get("value") not in (None, ""):
                        has_value = True
                    if not has_value and isinstance(ent.get("values"), list) and len(ent.get("values")) > 0:
                        has_value = True
                    if not has_value and ent.get("aggregated_value") not in (None, ""):
                        has_value = True
                    if has_value:
                        count += 1
                except Exception:
                    continue
            return count
        except Exception:
            return 0

    async def _extract_entities_with_progress(
        self, 
        chunked_docs: List[Dict], 
        progress_callback: Optional[callable] = None,
        reasoning_effort: Optional[str] = "high",
        ner_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract entities with progress updates."""
        if not chunked_docs:
            logger.warning("No documents available for entity extraction")
            return {"entities": [], "message": "No documents to process"}
        
        logger.info(f"Starting entity extraction with progress on {len(chunked_docs)} documents")
        
        # Create a wrapper callback that ensures immediate flushing
        async def flushed_progress_callback(progress_data):
            """Wrapper that ensures progress updates are immediately flushed."""
            if progress_callback:
                await progress_callback(progress_data)
                # Force immediate flush by yielding control briefly
                await asyncio.sleep(0.01)
        
        # Update progress at start of NER processing
        await flushed_progress_callback({
            "status": "EXTRACTING_ENTITIES",
            "progress": 10,
            "message": f"Processing {len(chunked_docs)} documents with NER workflow...",
            "current_step": "ner_processing",
            "chunked_documents": len(chunked_docs)
        })
        
        try:
            logger.info("Calling extract_entities_workflow with flushed progress callback...")
            
            # Start the entity extraction (this is the long-running part)
            ner_results = await extract_entities_workflow(
                json_data=self._entity_config_json,
                chunked_docs=chunked_docs,
                progress_callback=flushed_progress_callback,  # Use flushed wrapper
                reasoning_effort=reasoning_effort,
                ner_config=ner_config
            )
            
            # Update progress after extraction
            await flushed_progress_callback({
                "status": "PROCESSING_RESULTS",
                "progress": 96,
                "message": "Processing extraction results...",
                "current_step": "processing_results"
            })
            
            logger.info("extract_entities_workflow completed, processing results...")
            logger.debug(f"Raw NER results type: {type(ner_results)}")
            
            # Flatten results from processing types with deduplication
            all_entities = []
            entity_name_tracker = {}  # Track entity names to detect duplicates
            duplicate_count = 0
            
            # DEBUG: Log initial extraction summary
            
            if isinstance(ner_results, dict):
                logger.debug(f"NER results keys: {list(ner_results.keys())}")
                
                # DEBUG: Count total entities before deduplication
                total_entities_before = 0
                for ptype, presults in ner_results.items():
                    if isinstance(presults, dict) and 'found_entities' in presults:
                        total_entities_before += len(presults['found_entities'])
                
                for processing_type, type_results in ner_results.items():
                    logger.debug(f"Processing type '{processing_type}': {type(type_results)}")
                    
                    if isinstance(type_results, dict) and 'found_entities' in type_results:
                        found_entities = type_results['found_entities']
                        logger.debug(f"Found {len(found_entities)} entities for type '{processing_type}'")
                        
                        # DEBUG: Log processing type details
                        entity_names_in_type = [e.get('entity_name', '') for e in found_entities]
                        
                        for entity in found_entities:
                            try:
                                entity_name = entity.get('entity_name', '')
                                
                                # DEBUG: Log each entity being checked
                                
                                # DEDUPLICATION LOGIC: Check if entity name already exists
                                if entity_name in entity_name_tracker:
                                    duplicate_count += 1
                                    existing_processing_type = entity_name_tracker[entity_name]['processing_type']
                                    
                                    # DEBUG: Detailed duplicate information
                                    
                                    
                                    # LOG INFO for duplicate detection (this is expected behavior)
                                    logger.info(f"DUPLICATE ENTITY DETECTED: Entity '{entity_name}' found in both "
                                               f"'{existing_processing_type}' and '{processing_type}' processing types. "
                                               f"Keeping the first occurrence from '{existing_processing_type}' and "
                                               f"discarding duplicate from '{processing_type}'. (This is correct deduplication behavior)")
                                    
                                    # Log detailed entity info for debugging
                                    logger.debug(f"Existing entity: {entity_name_tracker[entity_name]}")
                                    logger.debug(f"Duplicate entity (discarded): {entity}")
                                    
                                    continue  # Skip this duplicate entity
                                
                                # Add processing_type to entity and track it
                                entity['processing_type'] = processing_type
                                entity_name_tracker[entity_name] = entity
                                all_entities.append(entity)
                                
                            except Exception as entity_error:
                                logger.error(f"Error processing individual entity: {entity_error}")
                                logger.debug(f"Problematic entity: {entity}")
                                continue
                    else:
                        logger.warning(f"Unexpected structure for processing type '{processing_type}': {type_results}")
            else:
                logger.error(f"NER results is not a dict: {type(ner_results)}")
                logger.debug(f"NER results content: {ner_results}")
            
            # DEBUG: Final comprehensive summary
            
            # DEBUG: List all final entity names
            final_entity_names = [e.get('entity_name', '') for e in all_entities]
            
            # CRITICAL FIX: Ensure all 37 entities are accounted for (found + not_found = 37)
            # Parse entity definitions to get all expected entities
            import json
            config = json.loads(self._entity_config_json)
            all_expected_entities = [entity.get("name", "") for entity in config.get("entities", [])]
            
            # Find which entities were not found
            found_entity_names = set(final_entity_names)
            not_found_entity_names = [name for name in all_expected_entities if name not in found_entity_names]
            
            # Add not_found entities to ensure total = 37
            for not_found_name in not_found_entity_names:
                not_found_entity = {
                    "entity_name": not_found_name,
                    "value": "",  # Empty value for not found
                    "metadata": {"status": "not_found"},
                    "processing_type": "not_found"
                }
                all_entities.append(not_found_entity)
            
            
            
            

            # Log deduplication summary
            if duplicate_count > 0:
                logger.info(f"DEDUPLICATION SUMMARY: {duplicate_count} duplicate entity occurrences were found and handled correctly. "
                           f"Each entity name now appears only once with the first value found. All 37 entities are accounted for "
                           f"(either found with values or marked as not_found). This is expected behavior for first_match entities.")
            else:
                logger.info(f"No duplicate entities detected. All {len(all_entities)} entities are unique.")
            
            # Final progress update (before adding programmatic entities)
            await flushed_progress_callback({
                "status": "ENTITY_EXTRACTION_COMPLETE",
                "progress": 98,
                "message": f"Entity extraction completed: {len(all_entities)} entities found (duplicates removed: {duplicate_count})",
                "current_step": "extraction_complete",
                "entities_extracted": len(all_entities),
                "duplicates_removed": duplicate_count
            })
            
            logger.info(f"Creating final results structure with {len(all_entities)} deduplicated entities...")
            
            # Add programmatic "Date de présentation" as today's date
            today_date = datetime.now().strftime('%d/%m/%Y')
            presentation_date_entity = {
                "entity_name": "Date de présentation",
                "entity_value": today_date,
                "entity_type": "date",
                "processing_type": "programmatic",
                "confidence": 1.0,
                "source_document": "system_generated",
                "extraction_context": f"Automatically set to MDT meeting date: {today_date}",
                "notes": "Date de présentation du dossier à la RCP (générée automatiquement)"
            }
            
            # Add to entities list
            all_entities.append(presentation_date_entity)
            logger.info(f"Added programmatic 'Date de présentation': {today_date}")
            
            final_results = {
                "entities": all_entities,
                "raw_results_by_type": ner_results,
                "summary": {
                    "total_entities": len(all_entities),
                    "duplicates_removed": duplicate_count,
                    "programmatic_entities_added": 1,
                    "by_processing_type": {
                        ptype: len(pdata.get('found_entities', []))
                        for ptype, pdata in ner_results.items()
                        if isinstance(pdata, dict)
                    }
                }
            }
            
            logger.info(f"Entity extraction with progress completed successfully: {len(all_entities)} total entities extracted")
            return final_results
            
        except asyncio.TimeoutError as timeout_error:
            logger.error(f"Entity extraction timed out after 5 hours: {timeout_error}")
            # Propagate failure immediately
            raise
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Propagate failure immediately
            raise


    def _create_report_data(self, patient_id: str, report_content: Dict[str, Any],  
                        report_title: Optional[str], total_documents: int) -> Dict[str, Any]:  
        """Create final report data with better error handling."""  
        try:  
            if not report_title:  
                report_title = f"MDT Report - Patient {patient_id}"  
            
            logger.debug("Creating JSON content...")  
            content_json = json.dumps(report_content, ensure_ascii=False, indent=2, default=str)  
            logger.debug(f"JSON content created, size: {len(content_json)} chars")  
            
            # Determine final status based on content error presence and zero-entities signal
            try:
                has_error = bool(report_content.get("ner_results", {}).get("error"))
            except Exception:
                has_error = False
            try:
                entities_extracted = int(report_content.get("summary", {}).get("entities_extracted", 0))
            except Exception:
                entities_extracted = 0
            # If there were documents but zero entities extracted, treat as failure
            zero_entities_failure = (total_documents > 0 and entities_extracted == 0)
            status = "FAILED" if (has_error or zero_entities_failure) else "COMPLETED"
            
            report_data = {  
                "uuid": str(uuid.uuid4()),  
                "patient_id": patient_id,  
                "template_id": self._active_template_id,  # Store template used for GT consistency
                "status": status,  
                "title": report_title,  
                "filename": f"mdt_report_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",  
                "file_type": "json",  
                "file_size": len(content_json.encode('utf-8')),  
                "created_at": datetime.now(),  
                "character_count": len(content_json),  
                "word_count": len(content_json.split()),  
                "author": "MDT Report Generator v2.0",  
                "subject": f"MDT Report for Patient {patient_id}",  
                "keywords": ["MDT", "medical", "report", "patient", patient_id],  
                "elements": [],  
                "content": report_content,  
                "metadata": {  
                    "generated_at": datetime.now().isoformat(),  
                    "total_documents_processed": total_documents,  
                    "report_version": "2.0",  
                    "processing_method": "simplified_text_extraction",
                    "template_id": self._active_template_id  
                }  
            }  
            
            logger.debug("Report data structure created successfully")  
            return report_data  
            
        except Exception as e:  
            logger.error(f"Failed to create report data: {str(e)}")  
            logger.error(f"Error type: {type(e).__name__}")  
            
            # Return minimal report structure on error  
            return {  
                "uuid": str(uuid.uuid4()),  
                "patient_id": patient_id,  
                "template_id": self._active_template_id,  # Store template used for GT consistency
                "status": "COMPLETED_WITH_ERRORS",  
                "title": report_title or f"MDT Report - Patient {patient_id}",  
                "filename": f"mdt_report_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",  
                "file_type": "json",  
                "file_size": 0,  
                "created_at": datetime.now(),  
                "character_count": 0,  
                "word_count": 0,  
                "author": "MDT Report Generator v2.0",  
                "subject": f"MDT Report for Patient {patient_id}",  
                "keywords": ["MDT", "medical", "report", "patient", patient_id],  
                "elements": [],  
                "content": {"error": str(e), "original_content": report_content},  
                "metadata": {  
                    "generated_at": datetime.now().isoformat(),  
                    "total_documents_processed": total_documents,  
                    "report_version": "2.0",  
                    "processing_method": "simplified_text_extraction",  
                    "template_id": self._active_template_id,
                    "error": str(e)  
                }  
            }  


    async def _load_entity_definitions(self):
        """Load entity definitions from the active template; fallback to file baseline.
        
        NOTE: Always reload to pick up template changes (no caching).
        """
        try:
            from config.entity_config import get_active_template, migrate_legacy_config
            
            # Try to get active template
            template, source = get_active_template()
            
            # If source is file (no templates in DB yet), attempt migration
            if source == "file":
                try:
                    logger.info("No active template found, attempting migration...")
                    migrate_legacy_config()
                    # Retry getting active template after migration
                    template, source = get_active_template()
                except Exception as me:
                    logger.warning(f"Migration failed or already done: {me}")
            
            # Build entity definitions from template
            self._entity_definitions = {"entities": template.get("entities", [])}
            self._entity_config_json = json.dumps(self._entity_definitions)
            
            # Store template_id for GT extraction consistency
            self._active_template_id = template.get("id") if isinstance(template, dict) else None
            
            # Validate entity definitions for potential duplicates
            self._validate_entity_definitions()
            
            template_name = template.get("name", "active template") if isinstance(template, dict) else "default"
            logger.info(f"Loaded {len(self._entity_definitions.get('entities', []))} entity definitions from {template_name} (source: {source}, template_id: {self._active_template_id})")
        except Exception as e:
            logger.error(f"Failed to load entity definitions: {e}")
            self._entity_definitions = {"entities": []}
            self._entity_config_json = json.dumps(self._entity_definitions)
    
    def _validate_entity_definitions(self):
        """Validate entity definitions and check for potential naming conflicts."""
        if not self._entity_definitions or 'entities' not in self._entity_definitions:
            return
        
        entities = self._entity_definitions['entities']
        entity_names = []
        processing_type_groups = {"first_match": [], "multiple_match": [], "aggregate_all_matches": []}
        duplicate_names = []
        
        for entity in entities:
            entity_name = entity.get('name', '')
            processing_type = entity.get('processing_type', 'unknown')
            
            # Check for duplicate entity names
            if entity_name in entity_names:
                duplicate_names.append(entity_name)
                logger.error(f"CONFIGURATION ERROR: Duplicate entity name '{entity_name}' found in entity definitions. "
                           f"This will cause conflicts during entity extraction.")
            else:
                entity_names.append(entity_name)
            
            # Group by processing type
            if processing_type in processing_type_groups:
                processing_type_groups[processing_type].append(entity_name)
        
        # Log configuration summary
        logger.info(f"Entity configuration validation summary:")
        logger.info(f"  - Total entities: {len(entities)}")
        logger.info(f"  - first_match: {len(processing_type_groups['first_match'])} entities")
        logger.info(f"  - multiple_match: {len(processing_type_groups['multiple_match'])} entities")
        logger.info(f"  - aggregate_all_matches: {len(processing_type_groups['aggregate_all_matches'])} entities")
        
        if duplicate_names:
            logger.error(f"CONFIGURATION WARNING: {len(duplicate_names)} duplicate entity names detected in configuration: {duplicate_names}")
            logger.error("These duplicates should be resolved in the gr_entities_definition.json file to prevent extraction issues.")
        else:
            logger.info("✅ All entity names in configuration are unique.")
        
        # Check for similar entity names that might cause confusion
        similar_names = self._find_similar_entity_names(entity_names)
        if similar_names:
            logger.warning(f"CONFIGURATION NOTICE: Found similar entity names that might cause confusion: {similar_names}")
    
    def _find_similar_entity_names(self, entity_names):
        """Find entity names that are very similar and might cause confusion."""
        similar_pairs = []
        
        for i, name1 in enumerate(entity_names):
            for name2 in entity_names[i+1:]:
                # Check for similar names (simple heuristic)
                if self._names_are_similar(name1, name2):
                    similar_pairs.append((name1, name2))
        
        return similar_pairs
    
    def _names_are_similar(self, name1, name2):
        """Check if two entity names are similar enough to cause confusion."""
        # Convert to lowercase for comparison
        n1, n2 = name1.lower(), name2.lower()
        
        # Check for exact matches after normalization
        if n1 == n2:
            return True
        
        # Check for one name being a substring of another
        if n1 in n2 or n2 in n1:
            return True
        
        # Check for very similar names (differing by only a few characters)
        if len(n1) > 5 and len(n2) > 5:
            # Simple edit distance check
            common_chars = sum(1 for c1, c2 in zip(n1, n2) if c1 == c2)
            similarity_ratio = common_chars / max(len(n1), len(n2))
            if similarity_ratio > 0.8:  # 80% similarity
                return True
        
        return False

    def _preprocess_json_lcrs(self, data: Any, date_from: str) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Filter lCrs array by CR_DATE >= date_from (YYYYMMDD). Returns (new_data, stats).
        - If input is not dict or lCrs missing, returns (None, {reason: ...}) to indicate no-op.
        - On success, returns deep-copied dict with filtered lCrs and stats with size before/after.
        """
        stats: Dict[str, Any] = {}
        try:
            if not isinstance(data, dict):
                stats['reason'] = 'extracted_data_not_dict'
                return None, stats
            lcrs = data.get('lCrs')
            if not isinstance(lcrs, list):
                stats['reason'] = 'lCrs_missing_or_not_list'
                return None, stats
            # Normalize date_from
            df = str(date_from).strip()
            if len(df) == 10 and df[4] == '-' and df[7] == '-':
                df = df.replace('-', '')
            if not (len(df) == 8 and df.isdigit()):
                stats['reason'] = 'invalid_date_from_format'
                return None, stats

            # Compute sizes and counts before
            try:
                bytes_before = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            except Exception:
                bytes_before = None
            stats['bytes_before'] = bytes_before
            stats['items_before'] = len(lcrs)

            def normalize_yyyymmdd(v: Any) -> Optional[str]:
                if v is None:
                    return None
                s = str(v).strip()
                if len(s) == 10 and s[4] == '-' and s[7] == '-':
                    s = s.replace('-', '')
                if len(s) == 8 and s.isdigit():
                    return s
                return None

            # Filter items
            filtered: List[Any] = []
            for item in lcrs:
                try:
                    if not isinstance(item, dict):
                        continue
                    dnorm = normalize_yyyymmdd(item.get('CR_DATE'))
                    if dnorm is None:
                        # Keep items without CR_DATE? Requirement says remove those BEFORE date; ambiguous -> keep only with date >=
                        continue
                    if dnorm >= df:
                        filtered.append(item)
                except Exception:
                    continue

            # Sort filtered lCrs by CR_DATE descending
            try:
                filtered.sort(key=lambda it: (normalize_yyyymmdd(it.get('CR_DATE')) or ''), reverse=True)
            except Exception:
                pass

            # Ensure the largest lCrs item (by character length) is included regardless of date
            try:
                def _item_chars(it):
                    try:
                        return len(json.dumps(it, ensure_ascii=False))
                    except Exception:
                        return len(str(it))
                def _same_item(a, b):
                    if isinstance(a, dict) and isinstance(b, dict):
                        for k in ("CLECR", "id", "UID"):
                            if k in a and k in b:
                                return a[k] == b[k]
                        try:
                            return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
                        except Exception:
                            return False
                    return a == b
                largest = None
                if isinstance(lcrs, list) and lcrs:
                    try:
                        largest = max(lcrs, key=_item_chars)
                    except Exception:
                        largest = max(lcrs, key=lambda it: len(str(it)))
                if largest is not None and not any(_same_item(largest, it) for it in filtered):
                    filtered.append(largest)
                    stats['largest_added'] = True
                    try:
                        stats['largest_len'] = _item_chars(largest)
                    except Exception:
                        pass
                    try:
                        filtered.sort(key=lambda it: (normalize_yyyymmdd(it.get('CR_DATE')) or ''), reverse=True)
                    except Exception:
                        pass
                else:
                    stats['largest_added'] = False
            except Exception:
                pass

            # Build new data structure preserving other keys
            new_data = dict(data)
            new_data['lCrs'] = filtered

            # Compute sizes and counts after
            try:
                bytes_after = len(json.dumps(new_data, ensure_ascii=False).encode('utf-8'))
            except Exception:
                bytes_after = None
            stats['items_after'] = len(filtered)
            stats['bytes_after'] = bytes_after
            # Expose the effective cutoff date used
            stats['filter_date'] = df

            return new_data, stats
        except Exception as e:
            # Bubble up to caller to log
            raise e

    async def _get_processed_documents(self, patient_id: str) -> List[PatientDocument]:  
        """Retrieve processed documents."""  
        try:  
            paginated_response = self.patient_document_service.get_by_patient_id(  
                patient_id, page=1, page_size=1000  
            )  
              
            all_documents = paginated_response.items  
            processed_documents = [  
                doc for doc in all_documents  
                if getattr(doc, 'extracted_data', None)  
            ]  
              
            logger.info(f"Found {len(processed_documents)}/{len(all_documents)} documents with extracted_data")  
            # Verbose inventory for debugging JSON filter issues
            try:
                inventory = []
                for i, d in enumerate(all_documents):
                    filename = getattr(d, 'filename', f'doc_{i+1}')
                    has_b64 = bool(getattr(d, 'file_content', None))
                    ed = getattr(d, 'extracted_data', None)
                    ed_type = type(ed).__name__
                    ed_keys = list(ed.keys())[:5] if isinstance(ed, dict) else []
                    inventory.append({
                        "filename": filename,
                        "has_base64": has_b64,
                        "extracted_data_type": ed_type,
                        "extracted_data_keys_preview": ed_keys
                    })
                logger.info(f"[MDT-GET-DOCS] Inventory: {inventory}")
            except Exception:
                pass
              
            # DEBUG: Show sample extracted_data structure  
            if processed_documents:  
                sample_doc = processed_documents[0]  
                sample_data = getattr(sample_doc, 'extracted_data', {})  
                logger.debug(f"Sample document structure:")  
                logger.debug(f"  Filename: {getattr(sample_doc, 'filename', 'unknown')}")  
                logger.debug(f"  Extracted_data type: {type(sample_data)}")  
                if isinstance(sample_data, dict):  
                    logger.debug(f"  Keys: {list(sample_data.keys())}")  
              
            return processed_documents  
              
        except Exception as e:  
            logger.error(f"Failed to retrieve documents for patient {patient_id}: {e}")  
            raise  
