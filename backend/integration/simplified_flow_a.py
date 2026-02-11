"""
Medical Document Processing Service
File: src/services/medical_document_processor.py

A production-ready service for processing medical documents including:
- Document extraction from various formats (XML, HL7, PDF)
- Document parsing and text extraction
- Named Entity Recognition (NER) for medical entities
- Results export in JSON and PDF formats

"""

import asyncio
import json
import os
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

# Import your existing modules
from document_extraction.cda_utils import process_files
from document_parser.universal_document_parser import UniversalDocumentParser
from entity_extraction.ner_classifier import extract_entities_workflow
from tests.mdt_report_pdf import create_pdf_from_json


@dataclass
class ProcessingConfig:
    """Configuration class for document processing parameters."""
    data_path: str
    patient_id: str
    download_folder: str
    start_date: str = "20200101"
    end_date: str = "20231231"
    extensions: List[str] = None
    auto_mdt_filter: bool = True
    mdt_days_offset: int = 10
    entity_config_path: Optional[str] = None
    max_concurrent_parses: int = 5
    timeout_seconds: int = 300
    
    def __post_init__(self):
        """Validate and set defaults after initialization."""
        if self.extensions is None:
            self.extensions = ['.xml', '.hl7', '.pdf']
        
        # Validate paths
        if not os.path.exists(self.data_path):
            raise ValueError(f"Data path does not exist: {self.data_path}")
        
        # Create download folder if it doesn't exist
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessingMetrics:
    """Metrics collected during processing."""
    start_time: float
    end_time: Optional[float] = None
    documents_found: int = 0
    documents_processed: int = 0
    pdf_files_parsed: int = 0
    parsing_errors: int = 0
    entities_extracted: int = 0
    total_processing_time: Optional[float] = None
    
    def complete(self):
        """Mark processing as complete and calculate total time."""
        self.end_time = time.time()
        self.total_processing_time = self.end_time - self.start_time


class ProcessingError(Exception):
    """Custom exception for processing errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        super().__init__(message)
        self.error_code = error_code or "PROCESSING_ERROR"
        self.details = details or {}


class MedicalDocumentProcessor:
    """
    Production-ready medical document processing service.
    
    This service provides a complete pipeline for processing medical documents:
    1. Document extraction from various sources
    2. PDF document parsing and text extraction
    3. Named Entity Recognition for medical entities
    4. Results export in multiple formats
    
    Features:
    - Comprehensive error handling and logging
    - Configurable processing parameters
    - Async processing for improved performance
    - Detailed metrics and monitoring
    - Production-ready exception handling
    
    Example:
        ```python
        config = ProcessingConfig(
            data_path="/path/to/documents",
            patient_id="patient-123",
            download_folder="/path/to/output"
        )
        
        processor = MedicalDocumentProcessor(config)
        results = await processor.process()
        ```
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None, logger_name: str = None):
        """
        Initialize the medical document processor.
        
        Args:
            config: Processing configuration. If None, must be provided to process()
            logger_name: Custom logger name for this instance
            
        Raises:
            ProcessingError: If configuration is invalid
        """
        self.config = config
        self.logger = self._setup_logger(logger_name or __name__)
        self.metrics = ProcessingMetrics(start_time=time.time())
        
        # Initialize components
        self.parser = None  # Lazy initialization
        self.entity_config = None
        
        # Processing state
        self._processing_id = None
        self._is_processing = False
        
        self.logger.info(f"Initialized MedicalDocumentProcessor")
        
    def _setup_logger(self, name: str) -> logging.Logger:
        """
        Set up structured logging for the processor.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Only configure if no handlers exist (avoid duplicate handlers)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Create console handler with formatting
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            
        return logger
    
    @contextmanager
    def _processing_context(self, processing_id: str):
        """
        Context manager for processing operations.
        
        Args:
            processing_id: Unique identifier for this processing session
        """
        self._processing_id = processing_id
        self._is_processing = True
        self.logger.info(f"Starting processing session: {processing_id}")
        
        try:
            yield
        except Exception as e:
            self.logger.error(f"Processing session {processing_id} failed: {str(e)}")
            raise
        finally:
            self._is_processing = False
            self.logger.info(f"Completed processing session: {processing_id}")
    
    def _load_entity_config(self, config_path: Optional[str] = None) -> str:
        """
        Load entity configuration from file with robust error handling.
        
        Args:
            config_path: Path to entity configuration JSON file
            
        Returns:
            Entity configuration as JSON string
            
        Raises:
            ProcessingError: If critical configuration loading fails
        """
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 'entity_extraction', 
                'gr_entities_definition.json'
            )
        
        try:
            config_path = Path(config_path).resolve()
            
            if not config_path.exists():
                self.logger.warning(f"Entity config file not found: {config_path}")
                return json.dumps({"entities": []})
            
            with open(config_path, 'r', encoding='utf-8') as f:
                entity_data = f.read()
                
            # Validate JSON format
            json.loads(entity_data)  # This will raise JSONDecodeError if invalid
            
            entity_count = len(json.loads(entity_data).get("entities", []))
            self.logger.info(f"Loaded entity configuration: {entity_count} entities from {config_path}")
            
            return entity_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in entity config file {config_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "INVALID_CONFIG", {"config_path": str(config_path)})
            
        except Exception as e:
            self.logger.warning(f"Could not load entity config from {config_path}: {str(e)}. Using empty config.")
            return json.dumps({"entities": []})
    
    async def process(self, config: Optional[ProcessingConfig] = None) -> Dict[str, Any]:
        """
        Process medical documents for a patient with comprehensive error handling.
        
        Args:
            config: Processing configuration. If None, uses instance config
            
        Returns:
            Dictionary containing processing results and metrics
            
        Raises:
            ProcessingError: If processing fails critically
            ValueError: If configuration is invalid
        """
        # Use provided config or instance config
        if config:
            self.config = config
        elif not self.config:
            raise ValueError("No configuration provided. Set config during initialization or pass to process()")
        
        # Generate unique processing ID
        processing_id = f"proc_{int(time.time())}_{self.config.patient_id[:8]}"
        
        with self._processing_context(processing_id):
            try:
                self.logger.info(f"Starting processing for patient: {self.config.patient_id}")
                self.logger.info(f"Configuration: {asdict(self.config)}")
                
                # Initialize components if needed
                await self._initialize_components()
                
                # Reset metrics
                self.metrics = ProcessingMetrics(start_time=time.time())
                
                # Step 1: Extract documents
                extraction_result = await self._extract_documents()
                
                # Step 2: Parse PDF documents
                parsing_results = await self._parse_documents(
                    extraction_result.get('downloaded_pdf_files', [])
                )
                
                # Step 3: Prepare documents for NER
                chunked_docs = self._prepare_documents_for_ner(
                    extraction_result, parsing_results
                )
                
                # Step 4: Extract entities
                ner_results = await self._extract_entities(chunked_docs)
                
                # Complete metrics
                self.metrics.complete()
                
                # Create final results
                results = self._create_results(
                    extraction_result, parsing_results, ner_results, chunked_docs
                )
                
                self.logger.info(f"Processing completed successfully in {self.metrics.total_processing_time:.2f}s")
                self.logger.info(f"Processed {self.metrics.documents_processed} documents, "
                               f"extracted {self.metrics.entities_extracted} entities")
                
                return results
                
            except ProcessingError:
                # Re-raise processing errors as-is
                raise
                
            except Exception as e:
                error_msg = f"Unexpected error during processing: {str(e)}"
                self.logger.error(error_msg)
                self.logger.debug(f"Full traceback: {traceback.format_exc()}")
                
                raise ProcessingError(
                    error_msg, 
                    "UNEXPECTED_ERROR", 
                    {"traceback": traceback.format_exc()}
                )
    
    async def _initialize_components(self):
        """Initialize processing components lazily."""
        if not self.parser:
            self.logger.debug("Initializing document parser")
            self.parser = UniversalDocumentParser()
            
        if not self.entity_config:
            self.logger.debug("Loading entity configuration")
            self.entity_config = self._load_entity_config(self.config.entity_config_path)
    
    async def _extract_documents(self) -> Dict[str, Any]:
        """
        Extract documents with timeout and error handling.
        
        Returns:
            Document extraction results
            
        Raises:
            ProcessingError: If extraction fails
        """
        self.logger.info("Starting document extraction")
        
        try:
            extraction_result = await asyncio.wait_for(
                asyncio.to_thread(
                    process_files,
                    path=self.config.data_path,
                    extensions=self.config.extensions,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    patient_id=self.config.patient_id,
                    download_folder=self.config.download_folder,
                    auto_mdt_filter=self.config.auto_mdt_filter,
                    mdt_days_offset=self.config.mdt_days_offset
                ),
                timeout=self.config.timeout_seconds
            )
            
            # Update metrics
            self.metrics.documents_found = len(extraction_result.get('documents', []))
            self.metrics.documents_processed = len(extraction_result.get('documents', []))
            
            self.logger.info(f"Document extraction completed: {self.metrics.documents_found} documents found")
            
            return extraction_result
            
        except asyncio.TimeoutError:
            error_msg = f"Document extraction timed out after {self.config.timeout_seconds}s"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "EXTRACTION_TIMEOUT")
            
        except Exception as e:
            error_msg = f"Document extraction failed: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "EXTRACTION_FAILED", {"original_error": str(e)})
    
    async def _parse_documents(self, pdf_files: List[str]) -> List[Dict]:
        """
        Parse PDF documents with concurrency control and error handling.
        
        Args:
            pdf_files: List of PDF file paths to parse
            
        Returns:
            List of parsing results
        """
        if not pdf_files:
            self.logger.info("No PDF files to parse")
            return []
        
        self.logger.info(f"Starting PDF parsing: {len(pdf_files)} files")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent_parses)
        
        async def parse_single_document(pdf_path: str) -> Dict:
            """Parse a single PDF document with error handling."""
            async with semaphore:
                try:
                    filename = os.path.basename(pdf_path)
                    self.logger.debug(f"Parsing PDF: {filename}")
                    
                    parsed_doc = await asyncio.wait_for(
                        self.parser.parse_document(
                            source_document=pdf_path,
                            bypass_formatting=True
                        ),
                        timeout=60  # Per-document timeout
                    )
                    
                    self.metrics.pdf_files_parsed += 1
                    self.logger.debug(f"Successfully parsed: {filename}")
                    return parsed_doc
                    
                except asyncio.TimeoutError:
                    error_msg = f"Parsing timeout for {os.path.basename(pdf_path)}"
                    self.logger.warning(error_msg)
                    self.metrics.parsing_errors += 1
                    return {
                        'status': 'error',
                        'error': error_msg,
                        'file_path': pdf_path,
                        'error_code': 'PARSE_TIMEOUT'
                    }
                    
                except Exception as e:
                    error_msg = f"Parsing failed for {os.path.basename(pdf_path)}: {str(e)}"
                    self.logger.warning(error_msg)
                    self.metrics.parsing_errors += 1
                    return {
                        'status': 'error',
                        'error': str(e),
                        'file_path': pdf_path,
                        'error_code': 'PARSE_FAILED'
                    }
        
        # Parse all documents concurrently
        parsing_tasks = [parse_single_document(pdf_path) for pdf_path in pdf_files]
        parsing_results = await asyncio.gather(*parsing_tasks, return_exceptions=False)
        
        success_count = len([r for r in parsing_results if r.get('status') != 'error'])
        self.logger.info(f"PDF parsing completed: {success_count}/{len(pdf_files)} successful, "
                        f"{self.metrics.parsing_errors} errors")
        
        return parsing_results
    
    def _prepare_documents_for_ner(
        self, 
        extraction_result: Dict, 
        parsing_results: List[Dict]
    ) -> List[Dict]:
        """
        Prepare documents for NER processing with enhanced error handling.
        
        Args:
            extraction_result: Results from document extraction
            parsing_results: Results from PDF parsing
            
        Returns:
            List of documents prepared for NER processing
        """
        self.logger.info("Preparing documents for entity extraction")
        
        try:
            documents = extraction_result.get('documents', [])
            
            # Create mapping of parsed documents
            parsed_map = {}
            for parsed_doc in parsing_results:
                if parsed_doc.get('status') == 'success':
                    try:
                        parsed_content = parsed_doc.get('result', {}).get('parsed_document', {})
                        filename = parsed_content.get('metadata', {}).get('filename', '')
                        if filename:
                            parsed_map[filename] = parsed_content
                    except Exception as e:
                        self.logger.warning(f"Error processing parsed document: {str(e)}")
                        continue
            
            chunked_docs = []
            
            for i, doc in enumerate(documents):
                try:
                    # Extract text content from both sources
                    text_content = self._extract_text_content(doc, parsed_map)
                    
                    if not text_content.strip():
                        self.logger.debug(f"Skipping document {i+1}: no text content")
                        continue
                    
                    # Create chunks
                    chunks = self._create_chunks(text_content)
                    
                    # Create NER document structure
                    ner_doc = {
                        "metadata": {
                            "patient_id": self.config.patient_id,
                            "document_id": doc.get("document_id", f"doc_{i+1}"),
                            "document_type": doc.get("title", "Unknown"),
                            "date": doc.get("date", ""),
                            "filename": os.path.basename(doc.get("file_path", "")),
                            "file_path": doc.get("file_path", ""),
                            "extraction_success": doc.get("extraction_success", False),
                            "parsing_success": os.path.basename(doc.get("file_path", "")) in parsed_map,
                            "MDT": doc.get("MDT", False),
                            "PMSI": doc.get("PMSI", False),
                            "chunk_count": len(chunks)
                        },
                        "chunks": chunks
                    }
                    chunked_docs.append(ner_doc)
                    
                except Exception as e:
                    self.logger.warning(f"Error preparing document {i+1} for NER: {str(e)}")
                    continue
            
            self.logger.info(f"Prepared {len(chunked_docs)} documents for NER processing")
            return chunked_docs
            
        except Exception as e:
            error_msg = f"Failed to prepare documents for NER: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "NER_PREPARATION_FAILED")
    
    def _extract_text_content(self, doc: Dict, parsed_map: Dict) -> str:
        """
        Extract text content from document and parsed data with error handling.
        
        Args:
            doc: Document metadata
            parsed_map: Mapping of parsed document content
            
        Returns:
            Extracted text content
        """
        text_content = ""
        
        try:
            # Get text from original content (XML/HL7 documents)
            if doc.get('content', {}).get('text'):
                text_content += doc['content']['text'] + "\n\n"
            
            # Get text from parsed content (PDF documents)
            filename = os.path.basename(doc.get("file_path", ""))
            if filename in parsed_map:
                parsed_elements = parsed_map[filename].get('document_elements', '')
                if parsed_elements:
                    text_content += parsed_elements + "\n\n"
                    
        except Exception as e:
            self.logger.warning(f"Error extracting text content: {str(e)}")
        
        return text_content.strip()
    
    def _create_chunks(self, text_content: str) -> List[Dict]:
        """
        Create text chunks for processing with improved chunking strategy.
        
        Args:
            text_content: Raw text content
            
        Returns:
            List of text chunks with metadata
        """
        if not text_content:
            return []
        
        # Split by double newlines first, then by single newlines if chunks are too large
        raw_chunks = [chunk.strip() for chunk in text_content.split('\n\n') if chunk.strip()]
        
        # If no chunks from double newlines, try single newlines
        if not raw_chunks or len(raw_chunks) == 1:
            raw_chunks = [chunk.strip() for chunk in text_content.split('\n') if chunk.strip()]
        
        # If still no chunks, use the entire content
        if not raw_chunks:
            raw_chunks = [text_content.strip()]
        
        # Create formatted chunks with size limits
        max_chunk_size = 4000  # Reasonable size for NER processing
        formatted_chunks = []
        
        for i, chunk_text in enumerate(raw_chunks):
            # Split large chunks
            if len(chunk_text) > max_chunk_size:
                # Split by sentences if possible
                sentences = chunk_text.split('. ')
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) > max_chunk_size and current_chunk:
                        formatted_chunks.append({
                            "content": current_chunk.strip(),
                            "section_id": f"section_{len(formatted_chunks)+1}",
                            "page_id": len(formatted_chunks) + 1,
                            "category": "medical_document",
                            "chunk_size": len(current_chunk)
                        })
                        current_chunk = sentence
                    else:
                        current_chunk += (". " if current_chunk else "") + sentence
                
                # Add remaining content
                if current_chunk:
                    formatted_chunks.append({
                        "content": current_chunk.strip(),
                        "section_id": f"section_{len(formatted_chunks)+1}",
                        "page_id": len(formatted_chunks) + 1,
                        "category": "medical_document",
                        "chunk_size": len(current_chunk)
                    })
            else:
                formatted_chunks.append({
                    "content": chunk_text,
                    "section_id": f"section_{i+1}",
                    "page_id": i + 1,
                    "category": "medical_document",
                    "chunk_size": len(chunk_text)
                })
        
        return formatted_chunks
    
    async def _extract_entities(self, chunked_docs: List[Dict]) -> Dict[str, Any]:
        """
        Extract entities with comprehensive error handling.
        
        Args:
            chunked_docs: Documents prepared for NER
            
        Returns:
            NER extraction results
            
        Raises:
            ProcessingError: If entity extraction fails
        """
        if not chunked_docs:
            self.logger.warning("No documents available for entity extraction")
            return {"entities": [], "message": "No documents to process"}
        
        self.logger.info(f"Starting entity extraction on {len(chunked_docs)} documents")
        
        try:
            # Extract entities with timeout
            ner_results = await asyncio.wait_for(
                asyncio.to_thread(
                    extract_entities_workflow,
                    json_data=self.entity_config,
                    chunked_docs=chunked_docs
                ),
                timeout=self.config.timeout_seconds * 2  # Double timeout for NER
            )
            
            # Update metrics
            if isinstance(ner_results, dict) and 'entities' in ner_results:
                entities = ner_results['entities']
                self.metrics.entities_extracted = len(entities) if isinstance(entities, list) else 0
            
            self.logger.info(f"Entity extraction completed: {self.metrics.entities_extracted} entities extracted")
            
            return ner_results
            
        except asyncio.TimeoutError:
            error_msg = f"Entity extraction timed out after {self.config.timeout_seconds * 2}s"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "NER_TIMEOUT")
            
        except Exception as e:
            error_msg = f"Entity extraction failed: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"NER error traceback: {traceback.format_exc()}")
            raise ProcessingError(error_msg, "NER_FAILED", {"original_error": str(e)})
    
    def _create_results(
        self, 
        extraction_result: Dict, 
        parsing_results: List[Dict], 
        ner_results: Dict,
        chunked_docs: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create comprehensive results dictionary.
        
        Args:
            extraction_result: Document extraction results
            parsing_results: PDF parsing results
            ner_results: Entity extraction results
            chunked_docs: Processed documents
            
        Returns:
            Complete results dictionary
        """
        summary = {
            'processing_id': self._processing_id,
            'patient_id': self.config.patient_id,
            'total_documents': self.metrics.documents_found,
            'processed_documents': self.metrics.documents_processed,
            'pdf_documents': len(extraction_result.get('downloaded_pdf_files', [])),
            'parsed_documents': self.metrics.pdf_files_parsed,
            'parsing_errors': self.metrics.parsing_errors,
            'entities_extracted': self.metrics.entities_extracted,
            'processing_time_seconds': self.metrics.total_processing_time,
            'extraction_summary': extraction_result.get('summary', {}),
            'processing_timestamp': datetime.now().isoformat(),
            'config': asdict(self.config)
        }
        
        return {
            'status': 'success',
            'summary': summary,
            'metrics': asdict(self.metrics),
            'extraction': extraction_result,
            'parsing': parsing_results,
            'entities': ner_results,
            'processed_documents': chunked_docs
        }
    
    def save_results(
        self, 
        results: Dict, 
        output_path: Union[str, Path], 
        format: str = 'json'
    ) -> str:
        """
        Save processing results to file with comprehensive error handling.
        
        Args:
            results: Processing results dictionary
            output_path: Output file path
            format: Output format ('json' or 'pdf')
            
        Returns:
            Path to saved file
            
        Raises:
            ProcessingError: If saving fails
            ValueError: If format is unsupported
        """
        output_path = Path(output_path)
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                
                self.logger.info(f"Results saved to JSON: {output_path}")
                return str(output_path)
                
            elif format.lower() == 'pdf':
                if not results.get('entities'):
                    raise ValueError("No entity data available for PDF generation")
                
                pdf_path = create_pdf_from_json(results['entities'], str(output_path))
                self.logger.info(f"PDF report saved to: {pdf_path}")
                return pdf_path
                
            else:
                raise ValueError(f"Unsupported format: {format}. Supported: json, pdf")
                
        except Exception as e:
            error_msg = f"Failed to save results to {output_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg, "SAVE_FAILED", {"output_path": str(output_path)})
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current processing status and metrics.
        
        Returns:
            Status dictionary with current metrics
        """
        return {
            'is_processing': self._is_processing,
            'processing_id': self._processing_id,
            'metrics': asdict(self.metrics),
            'config': asdict(self.config) if self.config else None
        }


# Convenience functions for simple usage
async def process_patient_documents(
    data_path: str,
    patient_id: str,
    download_folder: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to process documents for a single patient.
    
    Args:
        data_path: Path to source documents
        patient_id: Target patient ID
        download_folder: Path for processed files
        **kwargs: Additional configuration options
        
    Returns:
        Processing results dictionary
        
    Raises:
        ProcessingError: If processing fails
        ValueError: If required parameters are missing
    """
    config = ProcessingConfig(
        data_path=data_path,
        patient_id=patient_id,
        download_folder=download_folder,
        **kwargs
    )
    
    processor = MedicalDocumentProcessor(config)
    return await processor.process()


def create_processor_from_dict(config_dict: Dict[str, Any]) -> MedicalDocumentProcessor:
    """
    Create processor from configuration dictionary.
    
    Args:
        config_dict: Configuration parameters as dictionary
        
    Returns:
        Initialized MedicalDocumentProcessor instance
    """
    config = ProcessingConfig(**config_dict)
    return MedicalDocumentProcessor(config)
