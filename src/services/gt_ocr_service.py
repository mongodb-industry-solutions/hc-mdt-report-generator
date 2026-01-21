"""
Ground Truth OCR Service

Handles OCR extraction from ground truth PDF files.
Supports multiple OCR engines: Mistral OCR and EasyOCR.
"""

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)

OCREngine = Literal["mistral", "easyocr"]


class GTOCRService:
    """
    Service for extracting text from ground truth PDF files.
    
    Supports:
    - Mistral OCR: Cloud-based, higher quality
    - EasyOCR: Local, faster, no API costs
    """

    def __init__(self):
        self._easyocr_reader = None
        self._mistral_processor = None

    async def extract_text(
        self,
        pdf_content: bytes,
        ocr_engine: OCREngine = "easyocr",
        languages: list = None
    ) -> Tuple[str, int]:
        """
        Extract text from PDF using specified OCR engine.
        
        Args:
            pdf_content: PDF file content as bytes
            ocr_engine: OCR engine to use ("mistral" or "easyocr")
            languages: List of language codes (default: ["fr", "en"])
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        if languages is None:
            languages = ["fr", "en"]

        if ocr_engine == "mistral":
            return await self._extract_with_mistral(pdf_content)
        elif ocr_engine == "easyocr":
            return await self._extract_with_easyocr(pdf_content, languages)
        else:
            raise ValueError(f"Unsupported OCR engine: {ocr_engine}")

    async def _extract_with_mistral(self, pdf_content: bytes) -> Tuple[str, int]:
        """
        Extract text using Mistral OCR API.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            from services.processors.ocr_processor import OCRProcessor
            
            if self._mistral_processor is None:
                self._mistral_processor = OCRProcessor()
                await self._mistral_processor.initialize()
            
            # Convert PDF bytes to base64
            pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")
            
            # Process using Mistral OCR
            extracted_text = await self._mistral_processor.process_base64(pdf_base64, ".pdf")
            
            # Estimate page count from PDF
            page_count = self._estimate_page_count(pdf_content)
            
            logger.info(f"Mistral OCR extracted {len(extracted_text)} characters from {page_count} pages")
            return extracted_text, page_count
            
        except Exception as e:
            logger.error(f"Mistral OCR extraction failed: {e}")
            raise

    async def _extract_with_easyocr(
        self,
        pdf_content: bytes,
        languages: list
    ) -> Tuple[str, int]:
        """
        Extract text using EasyOCR (local).
        
        Args:
            pdf_content: PDF file content as bytes
            languages: List of language codes
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            import fitz  # PyMuPDF
            
            # Initialize EasyOCR reader lazily
            if self._easyocr_reader is None:
                import easyocr
                # GPU enabled if OLLAMA_NUM_GPU > 0 (reuse existing GPU setting)
                gpu_enabled = int(os.environ.get("OLLAMA_NUM_GPU", "0")) > 0
                self._easyocr_reader = easyocr.Reader(languages, gpu=gpu_enabled)
                logger.info(f"EasyOCR reader initialized with languages: {languages}, GPU: {gpu_enabled}")
            
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(pdf_doc)
            
            all_text = []
            
            for page_num in range(page_count):
                page = pdf_doc[page_num]
                
                # Convert page to image (higher resolution for better OCR)
                mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # OCR the image
                results = self._easyocr_reader.readtext(img_data)
                
                # Extract text from results
                page_text = "\n".join([result[1] for result in results])
                all_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
                
                logger.debug(f"EasyOCR processed page {page_num + 1}/{page_count}")
            
            pdf_doc.close()
            
            extracted_text = "\n\n".join(all_text)
            logger.info(f"EasyOCR extracted {len(extracted_text)} characters from {page_count} pages")
            
            return extracted_text, page_count
            
        except ImportError as e:
            logger.error(f"EasyOCR dependencies not installed: {e}")
            raise ImportError(
                "EasyOCR requires additional dependencies. "
                "Install with: pip install easyocr pymupdf"
            )
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            raise

    def _estimate_page_count(self, pdf_content: bytes) -> int:
        """
        Estimate page count from PDF content.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Estimated page count
        """
        try:
            import fitz
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(pdf_doc)
            pdf_doc.close()
            return page_count
        except Exception:
            # Fallback: estimate from file size (rough approximation)
            # Assume ~50KB per page for scanned documents
            return max(1, len(pdf_content) // 50000)


