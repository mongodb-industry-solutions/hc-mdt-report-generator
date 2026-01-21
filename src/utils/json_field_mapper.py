#!/usr/bin/env python3
"""
Dynamic JSON field mapping for handling varying JSON structures.

Maps internal field names to actual field names in source JSON.
This allows the application to work with JSON documents that may have
different field naming conventions while using consistent internal names.

Example:
    Some JSON may use 'LIBNATCR' while others use 'CR_NAT' for report type.
    This mapper handles both transparently.

Configuration:
    Field mappings can be customized via environment variables:
    - JSON_FIELD_LIBNATCR=LIBNATCR,CR_NAT,NATUREDOCT
    - JSON_FIELD_CR_DATE=CR_DATE,DATEACTE,DATE
    - etc.
    
Author: ClarityGR Development Team
Created: 2024
Version: 1.0.0
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class JSONFieldMapper:
    """
    Maps internal field names to actual JSON field names dynamically.
    
    Supports:
    - Environment variable configuration
    - Multiple fallback field names (checked in order)
    - Default mappings as baseline
    
    Thread Safety:
        This service is stateless after initialization and thread-safe.
    """
    
    # Default field mappings (internal_name -> [possible_json_fields])
    # Order matters: first match wins
    DEFAULT_MAPPINGS: Dict[str, List[str]] = {
        'LIBNATCR': ['LIBNATCR', 'CR_NAT', 'NATUREDOCT', 'TYPE_CR', 'report_type'],
        'CR_DATE': ['CR_DATE', 'DATEACTE', 'DATE', 'CR_DATE2', 'created_at'],
        'TITLE': ['TITLE', 'CR_TITRE', 'OBJET', 'RESUME'],
        'TEXTE': ['TEXTE', 'CR_TEXTE', 'TEXTEF', 'CONTENU', 'TEXT'],
        'SERVICE': ['SERVICE', 'SERVICE2', 'CR_SERVICE'],
        'ID': ['ID', 'CLECR', 'UID', 'CR_NUMINT'],
        'MEDECIN': ['CR_MEDRESP', 'MEDECIN', 'MEDRESP'],
    }
    
    def __init__(self):
        """Initialize field mapper with mappings from environment or defaults."""
        self._mappings = self._load_mappings()
        logger.debug(f"JSONFieldMapper initialized with {len(self._mappings)} field mappings")
    
    def _load_mappings(self) -> Dict[str, List[str]]:
        """
        Load field mappings from environment variables or use defaults.
        
        Environment variable format:
            JSON_FIELD_<INTERNAL_NAME>=field1,field2,field3
            
        Example:
            JSON_FIELD_LIBNATCR=LIBNATCR,CR_NAT,NATUREDOCT
        """
        mappings = {}
        
        for internal_name, defaults in self.DEFAULT_MAPPINGS.items():
            env_key = f"JSON_FIELD_{internal_name}"
            env_value = os.environ.get(env_key)
            
            if env_value:
                # Parse comma-separated field names from env
                fields = [f.strip() for f in env_value.split(',') if f.strip()]
                if fields:
                    mappings[internal_name] = fields
                    logger.debug(f"Loaded mapping from env: {internal_name} -> {fields}")
                else:
                    mappings[internal_name] = defaults
            else:
                mappings[internal_name] = defaults
        
        return mappings
    
    def get_value(
        self, 
        data: Dict[str, Any], 
        internal_field: str, 
        default: Any = ''
    ) -> Any:
        """
        Get value from data using field mapping with fallbacks.
        
        Tries each possible field name in order until a non-empty value is found.
        
        Args:
            data: Source dictionary (e.g., lCr item or document metadata)
            internal_field: Internal field name (e.g., 'LIBNATCR')
            default: Default value if not found
            
        Returns:
            Value from first matching field, or default
        """
        if not isinstance(data, dict):
            return default
        
        possible_fields = self._mappings.get(internal_field, [internal_field])
        
        for field in possible_fields:
            value = data.get(field)
            if value is not None and value != '':
                return value
        
        return default
    
    def get_text_content(self, data: Dict[str, Any]) -> str:
        """
        Get text content from lCr using TEXTE field mapping.
        
        Args:
            data: lCr dictionary
            
        Returns:
            Text content string
        """
        return str(self.get_value(data, 'TEXTE', '') or '')
    
    def get_report_type(self, data: Dict[str, Any]) -> str:
        """
        Get report type (LIBNATCR) from lCr or document metadata.
        
        Args:
            data: lCr dictionary or document metadata
            
        Returns:
            Report type string (defaults to 'Unknown' if not found)
        """
        value = self.get_value(data, 'LIBNATCR', '')
        return str(value) if value else 'Unknown'
    
    def get_date(self, data: Dict[str, Any]) -> str:
        """
        Get date (CR_DATE) from lCr or document metadata.
        
        Args:
            data: lCr dictionary or document metadata
            
        Returns:
            Date string (may be in various formats)
        """
        return str(self.get_value(data, 'CR_DATE', '') or '')
    
    def get_title(self, data: Dict[str, Any]) -> str:
        """
        Get title from lCr or document metadata.
        
        Args:
            data: lCr dictionary or document metadata
            
        Returns:
            Title string
        """
        return str(self.get_value(data, 'TITLE', '') or '')
    
    def get_service(self, data: Dict[str, Any]) -> str:
        """
        Get service from lCr or document metadata.
        
        Args:
            data: lCr dictionary or document metadata
            
        Returns:
            Service string
        """
        return str(self.get_value(data, 'SERVICE', '') or '')
    
    def get_id(self, data: Dict[str, Any]) -> str:
        """
        Get unique ID from lCr or document metadata.
        
        Args:
            data: lCr dictionary or document metadata
            
        Returns:
            ID string
        """
        return str(self.get_value(data, 'ID', '') or '')
    
    def get_mappings(self) -> Dict[str, List[str]]:
        """
        Get a copy of the current field mappings.
        
        Returns:
            Dictionary of internal field names to possible JSON field names
        """
        return dict(self._mappings)


# Singleton instance for easy import
_field_mapper: Optional[JSONFieldMapper] = None


def get_field_mapper() -> JSONFieldMapper:
    """
    Get or create singleton field mapper instance.
    
    Returns:
        JSONFieldMapper singleton instance
    """
    global _field_mapper
    if _field_mapper is None:
        _field_mapper = JSONFieldMapper()
    return _field_mapper


def reset_field_mapper() -> None:
    """
    Reset the singleton field mapper instance.
    
    Useful for testing or when environment variables change.
    """
    global _field_mapper
    _field_mapper = None

