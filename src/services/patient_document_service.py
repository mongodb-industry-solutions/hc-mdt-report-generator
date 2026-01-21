from typing import List, Optional, Dict, Any, Union
from repositories.patient_document_repository import PatientDocumentRepository
from domain.entities.patient_document import PatientDocument
from utils.pagination import PaginatedResponse
from utils.exceptions import NotFoundException, ValidationException, DatabaseException
from api.schemas.request_schemas import PatientDocumentUploadRequest, DocumentStatus
from services.document_ocr_service import DocumentOCRService
from services.document_categorization_service import DocumentCategorizationService
from services.document_data_extraction_service import DocumentDataExtractionService
from utils.file_type_detector import detect_file_type_from_base64, detect_file_type_from_bytes
from utils.xml_cleaner import extract_clinical_text
from services.utils.file_format_handler import FileFormatHandler
import logging
import os
import tempfile
import base64
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class PatientDocumentService:
    """
    Service for patient document business logic and processing orchestration.
    
    This service coordinates the full document processing pipeline:
    1. Document upload and storage
    2. Text extraction (OCR for PDF/images, direct reading for text files)
    3. Data normalization (LLM-based text cleaning and structuring)
    4. Medical NER (entity extraction)
    5. Storage of processed results
    """
    def __init__(self):
        self.repository = PatientDocumentRepository()
        
        # Initialize processing services
        self.ocr_service = DocumentOCRService()
        self.document_categorization_service = DocumentCategorizationService()
        self.document_data_extraction_service = DocumentDataExtractionService()
        self.patient_id_extraction_service = None  # Lazy load to avoid circular imports

    def get_by_uuid(self, uuid: str) -> PatientDocument:
        """Get patient document by UUID"""
        try:
            return self.repository.get_by_uuid(uuid)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Service error retrieving patient document {uuid}: {e}")
            raise

    def get_by_patient_id(self, patient_id: str, page: int = 1, page_size: int = 10) -> PaginatedResponse[PatientDocument]:
        """Get patient documents by patient ID with pagination"""
        try:
            skip = (page - 1) * page_size
            documents = self.repository.get_by_patient_id(patient_id, skip, page_size)
            total = self.repository.count_by_patient_id(patient_id)
            
            return PaginatedResponse(
                items=documents,
                total=total,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            logger.error(f"Service error retrieving patient documents for patient {patient_id}: {e}")
            raise

    def get_by_filename(self, patient_id: str, filename: str) -> PatientDocument:
        """Get patient document by filename for a specific patient"""
        try:
            document = self.repository.get_by_filename(patient_id, filename)
            if not document:
                raise NotFoundException(f"Document with filename '{filename}' not found for patient {patient_id}")
            return document
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Service error retrieving document by filename {filename} for patient {patient_id}: {e}")
            raise

    def upload_document(self, patient_id: Optional[str], request: PatientDocumentUploadRequest) -> PatientDocument:
        """Upload a document for a patient (patient_id can be None for UUID-first uploads)"""
        try:
            # Validate that either file_url or file is provided
            if not request.file_url and not request.file:
                raise ValidationException("Either file_url or file (base64) must be provided")

            # Determine filename and file extension
            filename = None
            
            cleaned_base64: Optional[str] = None

            if request.file_url:
                # Extract filename from URL
                filename = Path(request.file_url).name
            elif request.file:
                # Decode base64 to validate it
                try:
                    file_content = base64.b64decode(request.file, validate=True)
                    
                    # Use provided filename if available, otherwise detect
                    if request.filename:
                        filename = request.filename
                    else:
                        # Try to detect file type from content
                        file_extension = detect_file_type_from_bytes(file_content)
                        
                        # Generate a filename with proper extension
                        patient_part = patient_id or "pending"
                        filename = f"uploaded_document_{patient_part}_{request.type}{file_extension}"

                    # If XML content, clean and convert to plain text to reduce size
                    try:
                        detected_ext = detect_file_type_from_bytes(file_content)
                        if detected_ext == '.xml':
                            try:
                                xml_text = file_content.decode('utf-8')
                            except UnicodeDecodeError:
                                xml_text = file_content.decode('latin-1')

                            cleaned_text = extract_clinical_text(xml_text)

                            # Re-encode cleaned text as base64 for storage
                            cleaned_base64 = base64.b64encode(cleaned_text.encode('utf-8')).decode('utf-8')

                            # Adjust filename to reflect text content if original did not specify
                            if not request.filename:
                                patient_part = patient_id or "pending"
                                filename = f"uploaded_document_{patient_part}_{request.type}.txt"
                    except Exception as cleaning_error:
                        logger.warning(f"XML cleaning failed, storing original content. Error: {cleaning_error}")
                    # PDF → text transformation using pypdf for text-based PDFs
                    try:
                        detected_ext = detect_file_type_from_bytes(file_content)
                        if detected_ext == '.pdf':
                            try:
                                import io
                                from pypdf import PdfReader

                                reader = PdfReader(io.BytesIO(file_content))
                                extracted_text_parts: List[str] = []
                                for page in reader.pages:
                                    extracted_text_parts.append(page.extract_text() or "")
                                extracted_text = "\n".join(extracted_text_parts).strip()

                                # Only replace if meaningful text extracted; fallback keeps original PDF
                                if extracted_text and len(extracted_text) >= 100:
                                    cleaned_base64 = base64.b64encode(extracted_text.encode('utf-8')).decode('utf-8')
                                    # Ensure filename is .txt so downstream treats as text
                                    if request.filename:
                                        base, _ = os.path.splitext(request.filename)
                                        filename = f"{base}.txt"
                                    else:
                                        patient_part = patient_id or "pending"
                                        filename = f"uploaded_document_{patient_part}_{request.type}.txt"
                            except Exception as pdf_err:
                                logger.warning(f"PDF text extraction failed, storing original content. Error: {pdf_err}")
                    except Exception as detection_err:
                        logger.warning(f"File type detection failed during PDF transform check: {detection_err}")
                except Exception as e:
                    raise ValidationException(f"Invalid base64 file content: {e}")

            # Check for existing document with same filename for this patient
            # Only check if patient_id is provided (skip for UUID-first uploads)
            existing_document = None
            if filename and patient_id:
                existing_document = self.repository.find_existing_document(patient_id, filename)

            if existing_document:
                # Replace existing document content
                logger.info(f"Replacing existing document {existing_document.uuid} with filename: {filename}")
                
                # Create new document data with updated timestamp
                new_document_data = PatientDocument(
                    patient_id=patient_id,
                    type=request.type,
                    source=request.source,
                    status=request.status,
                    notes=request.notes,
                    filename=filename,
                    file_path=request.file_url,
                    file_content=(cleaned_base64 if cleaned_base64 is not None else request.file),
                    updated_at=datetime.now(timezone.utc)
                ).model_dump()
                
                # Replace the existing document content
                return self.repository.replace_document_content(existing_document.uuid, new_document_data)
            else:
                # Create new document
                logger.info(f"Creating new document with filename: {filename}")
                document = PatientDocument(
                    patient_id=patient_id,
                    type=request.type,
                    source=request.source,
                    status=request.status,
                    notes=request.notes,
                    filename=filename,
                    file_path=request.file_url,
                    file_content=(cleaned_base64 if cleaned_base64 is not None else request.file)
                )

                # Save to database
                return self.repository.create(document)
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Service error uploading document for patient {patient_id}: {e}")
            raise
    


    def update_status(self, uuid: str, status: DocumentStatus, **kwargs) -> PatientDocument:
        """Update document status and optionally other fields"""
        try:
            update_data = {"status": status, "updated_at": datetime.now()}
            
            # Add optional fields
            if "processing_started_at" in kwargs:
                update_data["processing_started_at"] = kwargs["processing_started_at"]
            if "processing_completed_at" in kwargs:
                update_data["processing_completed_at"] = kwargs["processing_completed_at"]
            if "errors" in kwargs:
                update_data["errors"] = kwargs["errors"]
            if "parsed_document_uuid" in kwargs:
                update_data["parsed_document_uuid"] = kwargs["parsed_document_uuid"]

            return self.repository.update(uuid, update_data)
        except Exception as e:
            logger.error(f"Service error updating status for document {uuid}: {e}")
            raise
    
    def persist_text_results(self, uuid: str, raw_text: str, normalized_text: str, 
                           metadata: Dict[str, Any], normalization_results: Dict[str, Any]) -> PatientDocument:
        """Persist text extraction and normalization results to the document in MongoDB"""
        try:
            update_data = {
                "ocr_text": raw_text,  # Keep original field name for backward compatibility
                "normalized_text": normalized_text,
                "ocr_metadata": metadata,
                "normalization_metadata": normalization_results.get("metadata", {}),
                "normalization_status": normalization_results.get("normalization_status", "unknown"),
                "ocr_completed_at": datetime.now(),
                "normalization_completed_at": datetime.now(),
                "character_count": len(raw_text),
                "word_count": len(raw_text.split()),
                "normalized_character_count": len(normalized_text),
                "normalized_word_count": len(normalized_text.split()),
                "updated_at": datetime.now()
            }
            
            logger.info(f"Persisting text results for document {uuid} - Raw: {len(raw_text)} chars, Normalized: {len(normalized_text)} chars")
            return self.repository.update(uuid, update_data)
        except Exception as e:
            logger.error(f"Error persisting text results for document {uuid}: {e}")
            raise
    
    def persist_entity_results(self, uuid: str, entity_results: Dict[str, Any]) -> PatientDocument:
        """Persist entity extraction results to the document in MongoDB"""
        try:
            # Count total entities found
            total_entities = 0
            if entity_results:
                for processing_type, results in entity_results.items():
                    if processing_type == "metadata":
                        continue
                    found_entities = results.get("found_entities", [])
                    total_entities += len(found_entities)
            
            update_data = {
                "entity_results": entity_results,
                "entity_metadata": entity_results.get("metadata", {}) if entity_results else {},
                "entity_extraction_status": "success" if entity_results else "failed",
                "entity_extraction_completed_at": datetime.now(),
                "entities_found_count": total_entities,
                "updated_at": datetime.now()
            }
            
            logger.info(f"Persisting entity results for document {uuid} - {total_entities} entities found")
            return self.repository.update(uuid, update_data)
        except Exception as e:
            logger.error(f"Error persisting entity results for document {uuid}: {e}")
            raise

    def persist_categorization_results(self, uuid: str, categorization_results: Dict[str, Any]) -> PatientDocument:
        """Persist document categorization results to MongoDB"""
        try:
            categorization = categorization_results.get("categorization", {})
            metadata = categorization_results.get("metadata", {})
            
            update_data = {
                "document_category": "unknown",
                "categorization_metadata": metadata,
                "categorization_completed_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            category = categorization.get("category", "unknown")
            logger.info(f"Persisting categorization results for document {uuid} - Category: {category}")
            
            return self.repository.update(uuid, update_data)
        except Exception as e:
            logger.error(f"Error persisting categorization results for document {uuid}: {e}")
            raise

    def persist_extracted_data(self, uuid: str, extraction_results: Dict[str, Any]) -> PatientDocument:
        """Persist extracted structured data to the document in MongoDB"""
        try:
            extracted_data = extraction_results.get("extracted_data", {})
            metadata = extraction_results.get("metadata", {})
            
            update_data = {
                "extracted_data": extracted_data,
                "extraction_metadata": metadata,
                "extraction_status": metadata.get("extraction_status", "unknown"),
                "extraction_completed_at": datetime.now(),
                "document_type": metadata.get("document_type"),
                "updated_at": datetime.now()
            }
            
            # Log extraction results
            extraction_status = metadata.get("extraction_status", "unknown")
            logger.info(f"Persisting extracted data for document {uuid} - Status: {extraction_status}")
            
            return self.repository.update(uuid, update_data)
        except Exception as e:
            logger.error(f"Error persisting extracted data for document {uuid}: {e}")
            raise

    async def process_document(self, document: PatientDocument) -> Dict[str, Any]:
        """
        Orchestrate the complete document processing pipeline.
        
        This method coordinates:
        1. OCR processing (text extraction) - only for PDF/image files
        2. Complete workflow: Data normalization + Medical NER (entity extraction)
        3. Storage of processed results
        
        Args:
            document: The patient document to process
            
        Returns:
            Dictionary with processing results and metadata
        """
        try:
            logger.info(f"Starting document processing for {document.uuid}")
            
            # Update status to processing
            self.update_status(
                document.uuid,
                DocumentStatus.PROCESSING,
                processing_started_at=datetime.now()
            )
            
            # Step 1: Prepare source for processing (file path or base64)
            source = await self._prepare_source_for_processing(document)
            
            # Determine file type once for both OCR and normalization using utility functions
            if isinstance(source, dict):
                base64_content = source.get("base64_content", "")
                if base64_content:
                    file_extension = detect_file_type_from_base64(base64_content)
                else:
                    # Fallback to filename if available
                    file_extension = Path(document.filename).suffix if document.filename else ".unknown"
            else:
                # File path
                file_extension = FileFormatHandler.get_file_extension(source)
            
            file_type = file_extension.lstrip(".").lower()
            
            # Step 2: Text Extraction (OCR for PDF/images, direct reading for text files)
            logger.info(f"Step 1: Starting text extraction for {document.uuid}")
            raw_text = await self.ocr_service.extract_text(source, file_extension)
            logger.info(f"Text extraction completed - extracted {len(raw_text)} characters")
            
            # Persist raw text results to MongoDB immediately
            metadata = self.ocr_service.extract_metadata(source, raw_text)
            
            # Step 2.5: Extract Patient ID (NumdosGR) - Independent of user templates
            logger.info(f"Step 1.5: Extracting patient identifier for {document.uuid}")
            try:
                # Lazy load to avoid circular imports
                if self.patient_id_extraction_service is None:
                    from services.patient_id_extraction_service import PatientIdExtractionService
                    self.patient_id_extraction_service = PatientIdExtractionService()
                
                # Extract patient ID from OCR text
                patient_id_result = await self.patient_id_extraction_service.extract_patient_id(
                    document_text=raw_text,
                    document_uuid=document.uuid,
                    current_patient_id=document.patient_id
                )
                
                logger.info(f"Patient ID extraction result: {patient_id_result['patient_id']} (source: {patient_id_result['source']}, confidence: {patient_id_result['confidence']})")
                
                # Store extraction metadata
                metadata["patient_id_extraction"] = patient_id_result["metadata"]
                
                # Check if we should update the patient_id
                if patient_id_result["success"]:
                    new_patient_id = patient_id_result["patient_id"]
                    should_update = self.patient_id_extraction_service.should_update_patient_id(
                        document.patient_id,
                        new_patient_id
                    )
                    
                    if should_update:
                        logger.info(f"Updating patient_id from {document.patient_id} to {new_patient_id}")
                        self.update_patient_id_from_extraction(document.uuid, new_patient_id)
                        # Update the document object for remaining processing
                        document.patient_id = new_patient_id
                    else:
                        logger.info(f"Keeping existing patient_id: {document.patient_id}")
                else:
                    # Extraction failed - check if we need manual input
                    logger.warning(f"⚠️  Patient ID extraction failed for {document.uuid}")
                    if document.patient_id is None:
                        # No patient_id at all - require manual input
                        logger.info(f"Setting status to REQUIRES_MANUAL_INPUT for {document.uuid}")
                        # Note: We'll set status after processing completes, not here
                        # This allows OCR and other processing to complete normally
                    
            except Exception as e:
                logger.warning(f"Patient ID extraction failed with exception, using existing patient_id: {e}")
                # Continue with existing patient_id - not a critical failure
            
            # Step 3: Document Categorization
            logger.info(f"Step 2: Starting document categorization for {document.uuid}")
            #categorization_results = await self.document_categorization_service.categorize_document(
            #    raw_text, document.filename or "unknown"
            #)
            
            #document_category = categorization_results.get("categorization", {}).get("category", "unknown")
            #logger.info(f"Document categorized as: {document_category}")
            
            # BYPASS CATEGORIZATION: Set default values since categorization is disabled
            document_category = "unknown"
            categorization_results = {
                "categorization": {"category": "unknown"},
                "metadata": {
                    "categorization_completed_at": datetime.now().isoformat(),
                    "status": "bypassed"
                }
            }
            logger.info(f"Document categorization bypassed - using default category: {document_category}")
            
            # For now, use raw text as normalized text (we can add normalization later if needed)
            normalized_text = raw_text
            normalization_results = {
                "normalized_text": normalized_text,
                "normalization_status": "success"
            }
            entity_results = None
            
            # Persist text and normalization results to MongoDB
            self.persist_text_results(document.uuid, raw_text, normalized_text, metadata, normalization_results)
            
            # Persist categorization results to MongoDB
            self.persist_categorization_results(document.uuid, categorization_results)
            
            # Persist entity results to MongoDB
            self.persist_entity_results(document.uuid, entity_results)
            
            # Step 4: Data Extraction (Structured Data)
            logger.info(f"Step 3: Starting data extraction for {document.uuid}")
            extraction_results = None
            try:
                # Perform structured data extraction using the categorized document type
                extraction_results = await self.document_data_extraction_service.extract_structured_data(
                    normalized_text, 
                    "unknown", 
                    document.filename or "unknown"
                )
                
                # Persist extracted data to MongoDB
                self.persist_extracted_data(document.uuid, extraction_results)
                
                logger.info(f"Data extraction completed for {document.uuid}")
                
            except Exception as e:
                logger.error(f"Data extraction failed for {document.uuid}: {e}")
                # Continue processing even if data extraction fails
                extraction_results = {
                    "extracted_data": {"error": str(e)},
                    "metadata": {
                        "extraction_status": "failed",
                        "error": str(e)
                    }
                }
            
            # Step 5: Update document status to completed or requires_manual_input
            # Check if patient_id was extracted
            if document.patient_id is None:
                # Patient ID not found - require manual input
                logger.warning(f"⚠️  Document {document.uuid} completed processing but patient_id is None")
                final_status = DocumentStatus.REQUIRES_MANUAL_INPUT
                status_note = "Processing completed but patient ID not found - manual input required"
            else:
                # Normal completion
                final_status = DocumentStatus.DONE
                status_note = None
            
            self.update_status(
                document.uuid,
                final_status,
                processing_completed_at=datetime.now(),
                parsed_document_uuid=f"processed_{document.uuid}",
                notes=status_note
            )
            
            # Prepare results
            processing_results = {
                "status": "success",
                "document_uuid": document.uuid,
                "patient_id": document.patient_id,
                "metadata": metadata,
                "text_extraction_results": {
                    "raw_text": raw_text,
                    "character_count": len(raw_text),
                    "word_count": len(raw_text.split()),
                    "file_type": file_type
                },
                "normalization_results": {
                    "normalized_text": normalized_text,
                    "normalization_status": normalization_results.get("normalization_status", "unknown"),
                    "statistics": {
                        "original_character_count": len(raw_text),
                        "normalized_character_count": len(normalized_text),
                        "original_word_count": len(raw_text.split()),
                        "normalized_word_count": len(normalized_text.split())
                    },
                    "structured_data": normalization_results.get("structured_data"),
                    "normalization_notes": normalization_results.get("normalization_notes"),
                    "metadata": normalization_results.get("metadata", {})
                },
                "categorization_results": {
                    "category": document_category,
                    "categorization_data": categorization_results.get("categorization", {}),
                    "metadata": categorization_results.get("metadata", {})
                },
                "entity_results": {
                    "extraction_results": entity_results,
                    "statistics": {}  # Placeholder for entity statistics
                },
                "extraction_results": {
                    "extracted_data": extraction_results.get("extracted_data", {}) if extraction_results else {},
                    "metadata": extraction_results.get("metadata", {}) if extraction_results else {},
                    "extraction_status": extraction_results.get("metadata", {}).get("extraction_status", "unknown") if extraction_results else "unknown"
                },
                "processing_completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"Document processing completed successfully for {document.uuid}")

            return processing_results
            
        except Exception as e:
            logger.error(f"Document processing failed for {document.uuid}: {e}")
            
            # Update document status to failed
            self.update_status(
                document.uuid,
                DocumentStatus.FAILED,
                processing_completed_at=datetime.now(),
                errors=[str(e)]
            )
            
            return {
                "status": "error",
                "document_uuid": document.uuid,
                "error": str(e),
                "processing_completed_at": datetime.now().isoformat()
            }
    
    async def _prepare_source_for_processing(self, document: PatientDocument) -> Union[str, Dict[str, Any]]:
        """
        Prepare source for processing - return either file path or base64 dict
        
        Returns:
            Either a file path (str) or a dict with base64 content
        """
        if document.file_path:
            # File already exists at specified path
            if Path(document.file_path).exists():
                return document.file_path
            else:
                raise FileNotFoundError(f"File not found at path: {document.file_path}")
        
        elif document.file_content:
            # Return base64 content as dict for direct processing
            # File extension will be detected automatically by the OCR service
            return {
                "base64_content": document.file_content,
                "filename": document.filename or f"document_{document.uuid}"
            }
        
        else:
            raise ValueError("Document has neither file_path nor file_content")
    
    def delete_document(self, uuid: str) -> None:
        """
        Delete a document and cascade delete all related data:
        - All reports for this patient (if no other documents remain)
        - Each report's evaluations, ground truths, and generations
        """
        try:
            # Get document first to retrieve patient_id
            document = self.get_by_uuid(uuid)
            patient_id = document.patient_id
            
            # Delete the document
            self.repository.delete_by_uuid(uuid)
            logger.info(f"Deleted document {uuid}")
            
            # Check if this was the last document for the patient
            remaining_docs = self.repository.count_by_patient_id(patient_id)
            
            if remaining_docs == 0:
                # No more documents - cascade delete all patient data
                logger.info(f"No documents remaining for patient {patient_id}, cascading delete to reports...")
                
                # Import here to avoid circular imports
                from services.report_service import ReportService
                from repositories.report_repository import ReportRepository
                
                report_repo = ReportRepository()
                report_service = ReportService()
                
                # Get all report UUIDs for this patient
                report_uuids = report_repo.get_all_uuids_by_patient_id(patient_id)
                
                # Delete each report (which cascades to evaluations, ground truths, generations)
                for report_uuid in report_uuids:
                    try:
                        report_service.delete_report(report_uuid)
                        logger.info(f"Cascade deleted report {report_uuid} for patient {patient_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cascade delete report {report_uuid}: {e}")
                
                logger.info(f"Completed cascade delete for patient {patient_id}: {len(report_uuids)} reports deleted")
            else:
                logger.info(f"Patient {patient_id} still has {remaining_docs} documents, skipping cascade delete")
                
        except Exception as e:
            logger.error(f"Failed to delete document {uuid}: {e}")
            raise

    def update_patient_id_from_extraction(
        self,
        document_uuid: str,
        extracted_patient_id: str
    ) -> PatientDocument:
        """
        Update document's patient_id with extracted value.
        
        NOTE: We no longer use is_latest flag - use created_at/updated_at timestamps
        for finding the latest document. This is more scalable for bulk processing.
        
        This method:
        1. Updates this document's patient_id to extracted value
        2. Updates linked reports' patient_id
        
        Args:
            document_uuid: UUID of the document being updated
            extracted_patient_id: The extracted patient ID (e.g., NumdosGR)
            
        Returns:
            Updated PatientDocument
        """
        try:
            logger.info(f"Updating patient_id for document {document_uuid} to {extracted_patient_id}")
            
            # Update this document with extracted patient_id
            updated_doc = self.repository.update(
                document_uuid,
                {
                    "patient_id": extracted_patient_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            )
            logger.info(f"Updated document {document_uuid} with patient_id={extracted_patient_id}")
            
            # Step 3: Update linked reports (if any exist)
            try:
                from services.report_service import ReportService
                report_service = ReportService()
                
                # Update reports that might reference this document
                # Note: This assumes reports store document UUIDs in their metadata
                reports = report_service.repository.collection.find({
                    "$or": [
                        {"metadata.document_uuids": document_uuid},
                        {"patient_id": updated_doc.patient_id}  # Old patient_id
                    ]
                })
                
                updated_count = 0
                for report in reports:
                    try:
                        report_service.repository.update(
                            report["uuid"],
                            {"patient_id": extracted_patient_id}
                        )
                        updated_count += 1
                    except Exception as e:
                        logger.warning(f"Could not update report {report['uuid']}: {e}")
                
                if updated_count > 0:
                    logger.info(f"Updated patient_id for {updated_count} linked reports")
                    
            except Exception as e:
                logger.warning(f"Could not update linked reports: {e}")
            
            return updated_doc
            
        except Exception as e:
            logger.error(f"Failed to update patient_id for document {document_uuid}: {e}")
            raise DatabaseException(f"Patient ID update failed: {str(e)}")

