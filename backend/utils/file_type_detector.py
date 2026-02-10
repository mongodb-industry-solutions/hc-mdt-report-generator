"""
File Type Detector Utility

Centralized utility for detecting file types from various input formats.
Eliminates code duplication across services.
"""

import base64
import logging
from typing import Union

logger = logging.getLogger(__name__)


def detect_file_type_from_base64(base64_content: str) -> str:
    """
    Detect file type from base64 content using magic bytes
    
    Args:
        base64_content: Base64 encoded content
        
    Returns:
        Detected file extension (e.g., '.pdf', '.png', '.txt')
    """
    try:
        # Decode base64 to get binary content
        binary_content = base64.b64decode(base64_content)
        
        # Use the binary detection method
        return detect_file_type_from_bytes(binary_content)
        
    except Exception as e:
        logger.error(f"Error detecting file type from base64 content: {e}")
        return '.bin'


def detect_file_type_from_bytes(binary_content: bytes) -> str:
    """
    Detect file type from binary content using magic bytes
    
    Args:
        binary_content: Raw binary content
        
    Returns:
        Detected file extension (e.g., '.pdf', '.png', '.txt')
    """
    try:
        # Check for magic bytes (file signatures)
        if len(binary_content) < 4:
            return '.bin'  # Too short to detect
        
        # PDF signature: %PDF
        if binary_content.startswith(b'%PDF'):
            return '.pdf'
        
        # PNG signature: \x89PNG\r\n\x1a\n
        if binary_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return '.png'
        
        # JPEG signature: \xff\xd8\xff
        if binary_content.startswith(b'\xff\xd8\xff'):
            return '.jpg'
        
        # AVIF signature: \x00\x00\x00\x20ftypavif
        if binary_content.startswith(b'\x00\x00\x00\x20ftypavif'):
            return '.avif'
        
        # Office Open XML (DOCX, PPTX) signature: PK\x03\x04
        if binary_content.startswith(b'PK\x03\x04'):
            # Check for specific Office file types
            if b'word/' in binary_content[:1000]:
                return '.docx'
            elif b'ppt/' in binary_content[:1000]:
                return '.pptx'
            elif b'xl/' in binary_content[:1000]:
                return '.xlsx'
            else:
                return '.docx'  # Default to DOCX for PK files
        
        # Check for XML content first (before generic text detection)
        try:
            text_content = binary_content.decode('utf-8')
            if text_content.strip().startswith('<?xml') or text_content.strip().startswith('<'):
                return '.xml'
        except UnicodeDecodeError:
            pass
        
        # Check for JSON content
        try:
            text_content = binary_content.decode('utf-8')
            if text_content.strip().startswith('{') or text_content.strip().startswith('['):
                return '.json'
        except UnicodeDecodeError:
            pass
        
        # Check for HTML content
        try:
            text_content = binary_content.decode('utf-8')
            if text_content.strip().startswith('<html') or text_content.strip().startswith('<!DOCTYPE'):
                return '.html'
        except UnicodeDecodeError:
            pass
        
        # Check for CSV content (simple heuristic)
        try:
            text_content = binary_content.decode('utf-8')
            lines = text_content.split('\n')
            if len(lines) > 1 and ',' in lines[0] and len(lines[0].split(',')) > 2:
                return '.csv'
        except UnicodeDecodeError:
            pass
        
        # Check for Markdown content
        try:
            text_content = binary_content.decode('utf-8')
            if any(marker in text_content for marker in ['# ', '## ', '### ', '* ', '- ', '```']):
                return '.md'
        except UnicodeDecodeError:
            pass
        
        # Check if it's likely plain text (UTF-8 or ASCII) - do this last
        try:
            text_content = binary_content.decode('utf-8')
            # If it decodes as UTF-8 and contains mostly printable characters, it's likely text
            printable_ratio = sum(1 for c in text_content if c.isprintable() or c.isspace()) / len(text_content)
            if printable_ratio > 0.8:  # 80% printable characters
                return '.txt'
        except UnicodeDecodeError:
            pass
        
        logger.warning("Could not detect file type from content, returning .bin")
        return '.bin'
        
    except Exception as e:
        logger.error(f"Error detecting file type from binary content: {e}")
        return '.bin'


def detect_file_type_from_content(content: Union[str, bytes]) -> str:
    """
    Detect file type from content (string or bytes)
    
    Args:
        content: Content as string or bytes
        
    Returns:
        Detected file extension (e.g., '.pdf', '.png', '.txt')
    """
    if isinstance(content, str):
        # If it's a string, try to detect if it's base64
        try:
            # Try to decode as base64
            binary_content = base64.b64decode(content)
            return detect_file_type_from_bytes(binary_content)
        except Exception:
            # If it's not base64, treat as plain text
            return '.txt'
    elif isinstance(content, bytes):
        return detect_file_type_from_bytes(content)
    else:
        logger.error(f"Unsupported content type: {type(content)}")
        return '.bin' 