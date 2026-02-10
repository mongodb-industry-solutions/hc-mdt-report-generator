"""
Ground Truth OCR Service

Handles OCR extraction from ground truth PDF files.
Supports multiple OCR engines: Mistral OCR, EasyOCR, and AWS Bedrock (Textract + Bedrock).
"""

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)

OCREngine = Literal["bedrock", "easyocr", "mistral"]


class GTOCRService:
    """
    Service for extracting text from ground truth PDF files.
    
    Supports:
    - Bedrock OCR: AWS Textract + Bedrock, enterprise-grade (primary choice)
    - EasyOCR: Local, faster, no API costs  
    - Mistral OCR: Cloud-based, higher quality (secondary choice)
    """

    def __init__(self):
        self._easyocr_reader = None
        self._mistral_processor = None
        self._aws_ocr_processor = None

    async def extract_text(
        self,
        pdf_content: bytes,
        ocr_engine: OCREngine = "bedrock",
        languages: list = None
    ) -> Tuple[str, int]:
        """
        Extract text from PDF using specified OCR engine.
        
        Args:
            pdf_content: PDF file content as bytes
            ocr_engine: OCR engine to use ("bedrock", "easyocr", or "mistral")
            languages: List of language codes (default: ["fr", "en"])
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        if languages is None:
            languages = ["fr", "en"]

        if ocr_engine == "bedrock":
            return await self._extract_with_bedrock(pdf_content)
        elif ocr_engine == "easyocr":
            return await self._extract_with_easyocr(pdf_content, languages)
        elif ocr_engine == "mistral":
            return await self._extract_with_mistral(pdf_content)
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

    async def _extract_with_bedrock(self, pdf_content: bytes) -> Tuple[str, int]:
        """
        Extract text using AWS hybrid OCR (Textract + Bedrock).
        
        For PDFs, converts pages to images first for better Textract compatibility.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            import fitz  # PyMuPDF
            from services.processors.ocr_processor import OCRProcessor
            
            if self._aws_ocr_processor is None:
                self._aws_ocr_processor = OCRProcessor()
                await self._aws_ocr_processor.initialize()
            
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(pdf_doc)
            
            logger.info(f"🔍 Processing {page_count} pages with AWS Textract (PDF→Images)")
            
            all_text = []
            
            # Process each page as an image for better Textract compatibility
            for page_num in range(page_count):
                try:
                    page = pdf_doc[page_num]
                    
                    # Convert page to high-res image
                    mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR quality
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # Convert to base64
                    img_base64 = base64.b64encode(img_data).decode("utf-8")
                    
                    # Process with Textract via base64 (as PNG image)
                    page_text = await self._aws_ocr_processor.process_base64(img_base64, ".png")
                    
                    if page_text.strip():
                        all_text.append(f"--- Page {page_num + 1} ---\n{page_text.strip()}")
                    
                    logger.debug(f"✅ Page {page_num + 1}/{page_count} processed: {len(page_text)} chars")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process page {page_num + 1}: {e}")
                    all_text.append(f"--- Page {page_num + 1} ---\n[OCR failed for this page]")
            
            pdf_doc.close()
            
            # Combine all page texts
            extracted_text = "\n\n".join(all_text)
            
            logger.info(f"🎯 AWS Bedrock OCR extracted {len(extracted_text)} characters from {page_count} pages")
            return extracted_text, page_count
            
        except ImportError as e:
            logger.error(f"Missing dependency for PDF processing: {e}")
            raise ImportError(
                "AWS Bedrock OCR requires PyMuPDF for PDF processing. "
                "Install with: pip install pymupdf"
            )
        except Exception as e:
            logger.error(f"AWS Bedrock OCR extraction failed: {e}")
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


