# services/document_processor.py  
"""Document processing and chunking service."""  
  
import logging  
from typing import List, Dict, Any  
from domain.entities.ner_models import Document, DocumentChunk    
from config.ner_config import settings  
  
logger = logging.getLogger(__name__)  
  
class DocumentProcessor:  
    """Handles document chunking and preprocessing."""  
      
    def __init__(self,   
                 max_content_size: int = None,  
                 chunk_overlapping: int = None):  
        self.max_content_size = max_content_size or settings.max_content_size  
        self.chunk_overlapping = chunk_overlapping or settings.chunk_overlapping  
      
    def process_documents(self, raw_documents: List[Dict]) -> List[Document]:  
        """Convert raw document data to Document objects."""  
        documents = []  
          
        for raw_doc in raw_documents:  
            try:  
                # Convert raw chunks to DocumentChunk objects  
                chunks = []  
                for chunk_data in raw_doc.get("chunks", []):  
                    if isinstance(chunk_data, dict):  
                        chunk = DocumentChunk(  
                            content=chunk_data.get("content", ""),  
                            section_id=chunk_data.get("section_id", ""),  
                            category=chunk_data.get("category", "plain_text"),  
                            page_id=chunk_data.get("page_id"),  
                            metadata=chunk_data.get("metadata", {})  
                        )  
                    else:  
                        # Handle string chunks  
                        chunk = DocumentChunk(  
                            content=str(chunk_data),  
                            section_id="default",  
                            category="plain_text"  
                        )  
                    chunks.append(chunk)  
                  
                # Apply chunking if needed  
                processed_chunks = self._apply_smart_chunking(chunks)  
                  
                document = Document(  
                    chunks=processed_chunks,  
                    metadata=raw_doc.get("metadata", {})  
                )  
                  
                documents.append(document)  
                  
            except Exception as e:  
                logger.error(f"Failed to process document: {e}")  
                logger.debug(f"Problematic document: {raw_doc}")  
                continue  
          
        return documents  
      
    def _apply_smart_chunking(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:  
        """Apply intelligent chunking for oversized content."""  
        processed_chunks = []  
          
        for chunk in chunks:  
            if len(chunk.content) <= self.max_content_size:  
                processed_chunks.append(chunk)  
                continue  
              
            # Split large chunks  
            sub_chunks = self._split_large_chunk(chunk)  
            processed_chunks.extend(sub_chunks)  
          
        return processed_chunks  
      
    def _split_large_chunk(self, chunk: DocumentChunk) -> List[DocumentChunk]:  
        """Split a large chunk into smaller ones with overlap."""  
        sub_chunks = []  
        text = chunk.content  
        start = 0  
        chunk_num = 1  
          
        while start < len(text):  
            end = min(start + self.max_content_size, len(text))  
            chunk_content = text[start:end]  
              
            sub_chunk = DocumentChunk(  
                content=chunk_content,  
                section_id=f"{chunk.section_id}_part_{chunk_num}",  
                category=chunk.category,  
                page_id=chunk.page_id,  
                metadata={**chunk.metadata, "is_split": True, "part_number": chunk_num}  
            )  
              
            sub_chunks.append(sub_chunk)  
              
            if end >= len(text):  
                break  
                  
            # Apply overlap  
            start = max(0, end - self.chunk_overlapping)  
            chunk_num += 1  
          
        logger.debug(f"Split large chunk into {len(sub_chunks)} parts")  
        return sub_chunks  
