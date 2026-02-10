#!/usr/bin/env python3
"""
Source Filter Service - Pre-filters structured JSON data based on entity requirements.

This service enables targeted entity extraction by filtering the lCrs (patient reports)
array from structured JSON data before sending to the LLM. This significantly reduces
processing time and improves extraction accuracy by focusing on relevant report types.

Key Features:
- Filter by LIBNATCR (report type label)
- Filter by TITLE keywords (with OR logic using pipe separator)
- Filter by TEXTE content keywords (with OR logic using pipe separator)
- Temporal filtering with DEPTH parameter (most recent N reports)
- Focus section extraction (e.g., extract only "conclusion" section)
- Fallback filter support for secondary search strategies
- Deduplication of results across multiple filters

Example Usage:
    >>> from services.source_filter_service import SourceFilterService
    >>> from domain.entities.ner_models import SourceFilter
    >>> 
    >>> service = SourceFilterService()
    >>> 
    >>> # Filter for most recent RCP report
    >>> filters = [SourceFilter(libnatcr="RCP", depth=1)]
    >>> matching = service.filter_reports(lcrs_data, filters)

Author: ClarityGR Development Team
Created: 2024
Version: 1.0.0
"""

import re
import logging
from typing import List, Dict, Any, Optional

from domain.entities.ner_models import SourceFilter
from utils.json_field_mapper import get_field_mapper, JSONFieldMapper

logger = logging.getLogger(__name__)


class SourceFilterService:
    """
    Filters structured patient data (lCrs) based on entity-specific source requirements.
    
    This service implements the clinical search logic that clinicians use when
    looking for specific information in a patient's medical record:
    
    1. LIBNATCR filtering: Select by report type (e.g., "CR Radio", "RCP")
    2. TITLE keyword filtering: Refine by title content (e.g., "NUCLEAIRE")
    3. TEXTE content filtering: Search within report body
    4. DEPTH temporal filtering: Get N most recent matching reports
    5. Focus section extraction: Extract specific sections (e.g., "conclusion")
    
    Uses JSONFieldMapper for dynamic field access to handle varying JSON structures.
    
    Thread Safety:
        This service is stateless and thread-safe.
    """
    
    def __init__(self):
        """Initialize the SourceFilterService with a field mapper."""
        self.field_mapper: JSONFieldMapper = get_field_mapper()
    
    def filter_reports(
        self, 
        lcrs: List[Dict[str, Any]], 
        filters: List[SourceFilter]
    ) -> List[Dict[str, Any]]:
        """
        Filter and return reports matching any of the provided filters (OR logic).
        
        Each SourceFilter is applied independently, and results are combined
        with deduplication. Reports are sorted by date (most recent first)
        before applying the DEPTH limit.
        
        Args:
            lcrs: List of report dictionaries from structured JSON (lCrs array).
                 Each report should have fields: LIBNATCR, TITLE, TEXTE/CR_TEXTE, CR_DATE
                 
            filters: List of SourceFilter configurations. Multiple filters use OR logic.
            
        Returns:
            Filtered list of matching reports, deduplicated and sorted by date.
            Empty list if no matches found.
            
        Example:
            >>> filters = [
            ...     SourceFilter(libnatcr="CR Anatomopathologie", depth=0),
            ...     SourceFilter(libnatcr="RCP", depth=1)
            ... ]
            >>> matching = service.filter_reports(lcrs, filters)
        """
        if not filters:
            logger.debug("No filters provided, returning all reports")
            return lcrs
        
        if not lcrs:
            logger.debug("No lCrs data provided")
            return []
        
        all_matching = []
        
        for source_filter in filters:
            matching = self._apply_single_filter(lcrs, source_filter)
            all_matching.extend(matching)
            logger.debug(
                f"Filter LIBNATCR='{source_filter.libnatcr}' matched {len(matching)} reports"
            )
        
        # Deduplicate while preserving order
        seen = set()
        deduplicated = []
        for report in all_matching:
            report_id = self._get_report_id(report)
            if report_id not in seen:
                seen.add(report_id)
                deduplicated.append(report)
        
        logger.info(
            f"📋 Filtered {len(lcrs)} reports → {len(deduplicated)} matching "
            f"(using {len(filters)} filter(s))"
        )
        return deduplicated
    
    def _apply_single_filter(
        self, 
        lcrs: List[Dict[str, Any]], 
        source_filter: SourceFilter
    ) -> List[Dict[str, Any]]:
        """
        Apply a single SourceFilter to the reports.
        
        Processing order:
        1. Filter by LIBNATCR (required)
        2. Filter by TITLE keyword (optional)
        3. Filter by TEXTE content keyword (optional)
        4. Sort by CR_DATE descending (most recent first)
        5. Apply DEPTH limit
        
        Args:
            lcrs: List of report dictionaries
            source_filter: Single SourceFilter configuration
            
        Returns:
            List of matching reports after all filters applied
        """
        matching = []
        
        for report in lcrs:
            if not isinstance(report, dict):
                continue
                
            # 1. Filter by LIBNATCR (required - case insensitive match)
            # Use dynamic field mapping for flexible JSON structure support
            report_libnatcr = self.field_mapper.get_report_type(report).strip().upper()
            filter_libnatcr = source_filter.libnatcr.strip().upper() if source_filter.libnatcr else ''
            if report_libnatcr != filter_libnatcr:
                continue
            
            # 2. Filter by TITLE keyword (optional - case insensitive)
            if source_filter.title_keyword:
                title = self.field_mapper.get_title(report).upper()
                keywords = [kw.strip() for kw in source_filter.title_keyword.upper().split('|')]
                if not any(kw in title for kw in keywords if kw):
                    continue
            
            # 3. Filter by content keyword in TEXTE (optional - case insensitive)
            if source_filter.content_keyword:
                # Use dynamic field mapping to check text content
                texte = self.field_mapper.get_text_content(report).upper()
                keywords = [kw.strip() for kw in source_filter.content_keyword.upper().split('|')]
                if not any(kw in texte for kw in keywords if kw):
                    continue
            
            matching.append(report)
        
        # Sort by date (most recent first)
        # Use dynamic field mapping for date field
        matching.sort(key=lambda r: self.field_mapper.get_date(r), reverse=True)
        
        # Apply DEPTH limit (temporal filtering)
        if source_filter.depth > 0:
            # Positive depth: most recent N documents
            original_count = len(matching)
            matching = matching[:source_filter.depth]
            logger.debug(
                f"Applied depth={source_filter.depth} (newest): {original_count} → {len(matching)} reports"
            )
        elif source_filter.depth < 0:
            # Negative depth: oldest N documents
            original_count = len(matching)
            matching = matching[source_filter.depth:]  # Python slicing: [-3:] gives last 3 items
            logger.debug(
                f"Applied depth={source_filter.depth} (oldest): {original_count} → {len(matching)} reports"
            )
        
        return matching
    
    def _get_report_id(self, report: Dict[str, Any]) -> str:
        """
        Get unique identifier for a report for deduplication.
        
        Uses dynamic field mapping to find ID fields across different JSON structures.
        Falls back to date + libnatcr combination if no ID field found.
        
        Args:
            report: Report dictionary
            
        Returns:
            Unique string identifier for the report
        """
        # Use dynamic field mapping to get ID
        report_id = self.field_mapper.get_id(report)
        if report_id:
            return report_id
        
        # Fallback: use date + libnatcr + noordre for uniqueness
        cr_date = self.field_mapper.get_date(report)
        libnatcr = self.field_mapper.get_report_type(report)
        return f"{cr_date}_{libnatcr}_{report.get('NOORDRE', '')}"
    
    def extract_focused_content(
        self, 
        report: Dict[str, Any], 
        focus_section: Optional[str] = None
    ) -> str:
        """
        Extract content with optional focus on specific section.
        
        If focus_section is specified, attempts to extract that section
        from the report text. If the section is not found, returns the
        full report text as fallback.
        
        Common focus sections in French medical reports:
        - "conclusion" / "CONCLUSION"
        - "résultat" / "RESULTAT"
        - "diagnostic" / "DIAGNOSTIC"
        - "interprétation" / "INTERPRETATION"
        
        Args:
            report: Report dictionary containing TEXTE or CR_TEXTE field
            focus_section: Optional section name to focus on (case insensitive)
            
        Returns:
            Extracted text content (section or full text)
        """
        # Get the text content from the report
        texte = str(report.get('CR_TEXTE', '') or report.get('TEXTE', '') or '')
        
        if not texte.strip():
            return ''
        
        if not focus_section:
            return texte
        
        # Try to extract the specific section
        focus_upper = focus_section.upper().strip()
        
        # Common section header patterns in French medical reports
        patterns = [
            # Pattern: SECTION : content (until next section or end)
            rf'(?:^|\n)\s*{focus_upper}\s*[:\-]?\s*(.*?)(?=\n\s*[A-Z][A-Z\s]*[:\-]|\n\n\n|\Z)',
            # Pattern: SECTION followed by content until double newline
            rf'{focus_upper}\s*[:\-]?\s*(.*?)(?:\n\n|\Z)',
            # Simpler pattern: section header and everything after
            rf'{focus_upper}\s*[:\-]?\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texte, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    logger.debug(
                        f"Extracted '{focus_section}' section: {len(extracted)} chars"
                    )
                    return extracted
        
        logger.debug(
            f"Section '{focus_section}' not found in report, using full text"
        )
        return texte
    
    def get_report_metadata(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a report for tracking and logging.
        
        Uses dynamic field mapping for flexible JSON structure support.
        
        Args:
            report: Report dictionary
            
        Returns:
            Dictionary with key metadata fields
        """
        return {
            'id': self._get_report_id(report),
            'date': self.field_mapper.get_date(report),
            'libnatcr': self.field_mapper.get_report_type(report),
            'title': self.field_mapper.get_title(report),
            'service': self.field_mapper.get_service(report),
            'medecin': self.field_mapper.get_value(report, 'MEDECIN', ''),
        }
    
    def get_available_libnatcr_values(self, lcrs: List[Dict[str, Any]]) -> List[str]:
        """
        Get all unique LIBNATCR values from the reports.
        
        Uses dynamic field mapping for flexible JSON structure support.
        Useful for building UI dropdowns or validation.
        
        Args:
            lcrs: List of report dictionaries
            
        Returns:
            Sorted list of unique LIBNATCR values
        """
        values = set()
        for report in lcrs:
            if isinstance(report, dict):
                libnatcr = self.field_mapper.get_report_type(report)
                if libnatcr and libnatcr != 'Unknown':
                    values.add(str(libnatcr).strip())
        return sorted(values)

    def filter_documents(
        self,
        documents: List[Any],  # List[Document] - using Any to avoid circular import
        filters: List[SourceFilter]
    ) -> List[Any]:
        """
        Filter Document objects based on their metadata using source filters.
        
        This is the new approach for "1 lCr = 1 Document" architecture where
        each Document has lCr-specific metadata (LIBNATCR, CR_DATE, TITLE, etc.)
        directly in its metadata, enabling direct filtering without needing
        to access the original lCrs array.
        
        Args:
            documents: List of Document objects with lCr metadata
            filters: List of SourceFilter configurations. Multiple filters use OR logic.
            
        Returns:
            Filtered list of matching Document objects, deduplicated and sorted by date.
        """
        if not filters:
            logger.debug("No filters provided, returning all documents")
            return documents
        
        if not documents:
            logger.debug("No documents provided")
            return []
        
        all_matching = []
        
        for source_filter in filters:
            matching = self._apply_filter_to_documents(documents, source_filter)
            all_matching.extend(matching)
            logger.debug(
                f"Filter LIBNATCR='{source_filter.libnatcr}' matched {len(matching)} documents"
            )
        
        # Deduplicate while preserving order
        seen = set()
        deduplicated = []
        for doc in all_matching:
            doc_id = self._get_document_id(doc)
            if doc_id not in seen:
                seen.add(doc_id)
                deduplicated.append(doc)
        
        logger.info(
            f"📋 Filtered {len(documents)} documents → {len(deduplicated)} matching "
            f"(using {len(filters)} filter(s))"
        )
        return deduplicated
    
    def _apply_filter_to_documents(
        self,
        documents: List[Any],
        source_filter: SourceFilter
    ) -> List[Any]:
        """
        Apply a single SourceFilter to Document objects.
        
        Uses Document.metadata for filtering with dynamic field mapping
        for flexible JSON structure support.
        
        Processing order:
        1. Filter by LIBNATCR (required)
        2. Filter by TITLE keyword (optional)
        3. Filter by content keyword in chunks (optional)
        4. Sort by created_at/CR_DATE descending (most recent first)
        5. Apply DEPTH limit
        
        Args:
            documents: List of Document objects
            source_filter: Single SourceFilter configuration
            
        Returns:
            List of matching Document objects
        """
        matching = []
        
        for doc in documents:
            try:
                metadata = getattr(doc, 'metadata', {}) or {}
                
                # 1. Filter by LIBNATCR (required - case insensitive match)
                # Use dynamic field mapping for flexible structure support
                doc_libnatcr = self.field_mapper.get_report_type(metadata).strip().upper()
                filter_libnatcr = source_filter.libnatcr.strip().upper() if source_filter.libnatcr else ''
                if doc_libnatcr != filter_libnatcr:
                    continue
                
                # 2. Filter by TITLE keyword (optional - case insensitive)
                if source_filter.title_keyword:
                    title = self.field_mapper.get_title(metadata).upper()
                    keywords = [kw.strip() for kw in source_filter.title_keyword.upper().split('|')]
                    if not any(kw in title for kw in keywords if kw):
                        continue
                
                # 3. Filter by content keyword in chunks (optional - case insensitive)
                if source_filter.content_keyword:
                    chunks = getattr(doc, 'chunks', []) or []
                    content = ''
                    for chunk in chunks:
                        chunk_content = getattr(chunk, 'content', '') if hasattr(chunk, 'content') else chunk.get('content', '')
                        content += str(chunk_content).upper() + ' '
                    
                    keywords = [kw.strip() for kw in source_filter.content_keyword.upper().split('|')]
                    if not any(kw in content for kw in keywords if kw):
                        continue
                
                matching.append(doc)
                
            except Exception as e:
                logger.warning(f"Error filtering document: {e}")
                continue
        
        # Sort by date (most recent first)
        # Use dynamic field mapping for date field
        def get_date(doc):
            metadata = getattr(doc, 'metadata', {}) or {}
            return self.field_mapper.get_date(metadata)
        
        matching.sort(key=get_date, reverse=True)
        
        # Apply DEPTH limit (temporal filtering)
        if source_filter.depth > 0:
            # Positive depth: most recent N documents
            original_count = len(matching)
            matching = matching[:source_filter.depth]
            logger.debug(
                f"Applied depth={source_filter.depth} (newest): {original_count} → {len(matching)} documents"
            )
        elif source_filter.depth < 0:
            # Negative depth: oldest N documents
            original_count = len(matching)
            matching = matching[source_filter.depth:]  # Python slicing: [-3:] gives last 3 items
            logger.debug(
                f"Applied depth={source_filter.depth} (oldest): {original_count} → {len(matching)} documents"
            )
        
        return matching
    
    def _get_document_id(self, doc: Any) -> str:
        """
        Get unique identifier for a Document for deduplication.
        
        Uses dynamic field mapping for flexible JSON structure support.
        
        Args:
            doc: Document object
            
        Returns:
            Unique string identifier
        """
        try:
            metadata = getattr(doc, 'metadata', {}) or {}
            
            # Try document_id first
            doc_id = metadata.get('document_id')
            if doc_id:
                return str(doc_id)
            
            # Fallback to combination of filename + lcr_index or date + libnatcr
            filename = metadata.get('filename', '')
            lcr_index = metadata.get('lcr_index')
            if lcr_index is not None:
                return f"{filename}_lcr_{lcr_index}"
            
            # Last resort - use dynamic field mapping
            cr_date = self.field_mapper.get_date(metadata)
            libnatcr = self.field_mapper.get_report_type(metadata)
            return f"{cr_date}_{libnatcr}_{filename}"
        except Exception:
            return str(id(doc))

