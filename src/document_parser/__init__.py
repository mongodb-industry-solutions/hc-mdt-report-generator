# In universal_document_parser/__init__.py  
from .universal_document_parser import UniversalDocumentParser  
  
# Try to import mistral chunking, but make it optional  
try:  
    from .mistral_chunking import mistral_chunk_text  
    __all__ = ['UniversalDocumentParser', 'mistral_chunk_text']  
except ImportError:  
    __all__ = ['UniversalDocumentParser']  
