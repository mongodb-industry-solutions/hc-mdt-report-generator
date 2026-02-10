"""
Document Chunking Service

Handles intelligent chunking of medical documents using Mistral AI for semantic understanding.
Splits long documents into meaningful, coherent chunks while preserving medical context.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from services.base.llm import a_generate
from dotenv import load_dotenv
from services.prompts.document_chunking_prompts import SYSTEM_PROMPT, create_chunking_prompt

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a structured document chunk"""
    content: str
    category: str
    page_id: int
    section_id: int
    merge: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary format"""
        return {
            "content": self.content,
            "category": self.category,
            "page_id": self.page_id,
            "section_id": self.section_id,
            "merge": self.merge
        }


class DocumentChunkingService:
    """
    Service for intelligently chunking medical documents using Mistral AI.
    
    This service splits long OCR'ed text into meaningful, comprehensive chunks
    while preserving medical context and maintaining logical document structure.
    """
    
    def __init__(self):
        self.mistral_client = None
        self.model = "gpt-open"
        self.system_prompt = SYSTEM_PROMPT
        # Add option to disable Mistral chunking for debugging
        self.use_mistral_chunking = os.environ.get("USE_MISTRAL_CHUNKING", "true").lower() == "true"
    
    async def initialize(self) -> None:
        """No-op initialize retained for compatibility"""
        logger.info("Chunking service initialized (no-op)")
    
    async def chunk_document(self, text: str, max_chunk_size: int = 4000, 
                           overlap: int = 0) -> List[DocumentChunk]:
        """
        Chunk a document into meaningful segments.
        
        Args:
            text: The full document text to chunk
            max_chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of DocumentChunk objects with semantic understanding
        """
        # Check if chunking is needed for this document
        if not self._needs_chunking(text, max_chunk_size):
            logger.info(f"Document is short ({len(text)} chars), skipping chunking")
            return [DocumentChunk(
                content=text.strip(),
                category="document",
                page_id=0,
                section_id=0,
                merge=False
            )]
        
        # First split into basic chunks by size
        basic_chunks = self._chunk_text_by_size(text, max_chunk_size, overlap)
        logger.info(f"Split text into {len(basic_chunks)} basic chunks")
        
        # Check if Mistral chunking is enabled
        if not self.use_mistral_chunking:
            logger.info("Mistral chunking disabled, using simple chunking")
            return self._simple_chunk_fallback(text, max_chunk_size, overlap)
        
        # Initialize Mistral client if needed
        if not self.mistral_client:
            await self.initialize()
        
        try:
            # Try to process with LLM for semantic understanding
            logger.info("Attempting LLM-based chunking...")
            return await self._process_chunks_with_mistral(basic_chunks)
        except Exception as e:
            logger.warning(f"Mistral chunking failed: {e}. Falling back to simple chunking.")
            # Fallback to simple chunking without AI
            return self._simple_chunk_fallback(text, max_chunk_size, overlap)
    
    async def _process_chunks_with_mistral(self, basic_chunks: List[str]) -> List[DocumentChunk]:
        """Process chunks using LLM for semantic understanding"""
        processed_chunks = []
        previous_chunk_xml = None
        section_id = 0
        
        for i, chunk_text in enumerate(basic_chunks):
            logger.info(f"Processing chunk {i+1}/{len(basic_chunks)} with Mistral")
            logger.info(f"Chunk {i+1} length: {len(chunk_text)} characters")
            
            try:
                # Skip empty chunks
                if not chunk_text.strip():
                    logger.warning(f"Skipping empty chunk {i+1}")
                    continue
                
                # Limit chunk size for Mistral (avoid very large prompts)
                if len(chunk_text) > 3000:
                    logger.warning(f"Chunk {i+1} too large ({len(chunk_text)} chars), truncating to 3000")
                    chunk_text = chunk_text[:3000] + "..."
                
                # Build prompt for Mistral
                prompt = self._build_chunking_prompt(previous_chunk_xml, chunk_text)
                logger.debug(f"Built prompt for chunk {i+1}, total prompt length: {len(prompt)}")
                
                # Get semantic chunking via unified LLM
                logger.info(f"Calling LLM for chunk {i+1}...")
                mistral_response = await self._invoke_mistral(prompt)
                logger.info(f"Received response for chunk {i+1}")
                
                # ADD DEBUG: Check if model responded
                if not mistral_response:
                    logger.warning(f"Empty response from Mistral for chunk {i+1}")
                    # Fallback to simple chunk for this iteration
                    chunk_obj = DocumentChunk(
                        content=chunk_text.strip(),
                        category="unknown",
                        page_id=i,
                        section_id=section_id,
                        merge=False
                    )
                    processed_chunks.append(chunk_obj)
                    section_id += 1
                    continue
                
                # Parse response and extract chunks
                chunk_objects = self._parse_mistral_chunking_response(
                    mistral_response, i, section_id
                )
                
                # If no chunks were parsed, create a simple one
                if not chunk_objects:
                    logger.warning(f"No chunks parsed from LLM response for chunk {i+1}")
                    chunk_obj = DocumentChunk(
                        content=chunk_text.strip(),
                        category="unknown",
                        page_id=i,
                        section_id=section_id,
                        merge=False
                    )
                    processed_chunks.append(chunk_obj)
                    section_id += 1
                    continue
                
                # Handle merging logic
                for chunk_obj in chunk_objects:
                    if chunk_obj.merge and processed_chunks:
                        # Merge with previous chunk
                        self._merge_with_previous_chunk(processed_chunks, chunk_obj)
                        section_id -= 1  # Adjust section ID since we merged
                    else:
                        # Add as new chunk
                        processed_chunks.append(chunk_obj)
                    
                    section_id += 1
                
                # Store last chunk XML for next iteration
                if chunk_objects:
                    previous_chunk_xml = self._chunk_to_xml(chunk_objects[-1])
                    
            except Exception as e:
                logger.warning(f"Error processing chunk {i+1} with LLM: {e}")
                # Fallback to simple chunk for this iteration
                chunk_obj = DocumentChunk(
                    content=chunk_text.strip(),
                    category="unknown",
                    page_id=i,
                    section_id=section_id,
                    merge=False
                )
                processed_chunks.append(chunk_obj)
                section_id += 1
        
        logger.info(f"Successfully processed chunks into {len(processed_chunks)} semantic chunks")
        return processed_chunks
    
    def _simple_chunk_fallback(self, text: str, max_chunk_size: int, overlap: int) -> List[DocumentChunk]:
        """Fallback simple chunking without AI when Mistral fails"""
        logger.info("Using simple chunking fallback")
        
        basic_chunks = self._chunk_text_by_size(text, max_chunk_size, overlap)
        processed_chunks = []
        
        for i, chunk_text in enumerate(basic_chunks):
            chunk_obj = DocumentChunk(
                content=chunk_text.strip(),
                category="text",  # Generic category
                page_id=i,
                section_id=i,
                merge=False
            )
            processed_chunks.append(chunk_obj)
        
        logger.info(f"Created {len(processed_chunks)} simple chunks")
        return processed_chunks
    
    def _chunk_text_by_size(self, text: str, max_chunk_size: int, overlap: int) -> List[str]:
        """Split text into chunks by size with optional overlap"""
        if max_chunk_size <= overlap:
            raise ValueError("max_chunk_size must be greater than overlap")
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + max_chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            
            # If we've reached the end, break
            if end == text_length:
                break
            
            start = end - overlap
        
        return chunks
    
    def _build_chunking_prompt(self, previous_chunk_xml: Optional[str], raw_text: str) -> str:
        """Build the prompt for LLM chunking"""
        return create_chunking_prompt(previous_chunk_xml, raw_text)
    
    async def _invoke_mistral(self, prompt: str) -> str:
        """Call unified LLM for chunking (no timeout/retry)"""
        import os
        provider = os.environ.get("LLM_PROVIDER", "bedrock").lower()
        
        try:
            logger.info(f"Calling LLM ({provider}) with prompt length: {len(prompt)}")
            
            if provider == "bedrock":
                logger.info("Using Bedrock client for document chunking")
                from infrastructure.llm.bedrock_client import AsyncBedrockClient
                
                async with AsyncBedrockClient() as bedrock_client:
                    content = await bedrock_client.invoke_bedrock_async_robust(
                        self.system_prompt,
                        prompt,
                        timeout_override=120,
                    )
            else:
                # Fallback to GPT-Open for backward compatibility
                logger.info(f"Using {provider} provider for document chunking")
                content = await a_generate(
                    prompt=prompt,
                    system=self.system_prompt,
                    max_tokens=4000,
                    temperature=0.1,
                    provider="gpt_open",
                )
            
            logger.info(f"LLM response received, length: {len(content) if content else 0}")
            return content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            logger.error(f"Prompt preview: {prompt[:200]}..." if len(prompt) > 200 else f"Full prompt: {prompt}")
            raise
    
    def _parse_mistral_chunking_response(self, response: str, page_id: int, 
                                       base_section_id: int) -> List[DocumentChunk]:
        """Parse Mistral's chunking response into DocumentChunk objects"""
        chunks = []
        
        logger.debug(f"Parsing Mistral response: {response[:200]}...")
        
        # Extract chunks XML
        chunks_xml = self._extract_from_xml_tags(response, "CHUNKS")
        if not chunks_xml:
            logger.warning("No CHUNKS XML found in Mistral response")
            logger.debug(f"Full response was: {response}")
            return chunks
        
        # Parse individual chunks
        section_id = base_section_id
        chunk_start = 0
        
        while True:
            chunk_xml = self._extract_from_xml_tags(chunks_xml[chunk_start:], "CHUNK")
            if not chunk_xml:
                break
            
            # Extract chunk fields
            content = self._extract_from_xml_tags(chunk_xml, "CONTENT") or ""
            category = self._extract_from_xml_tags(chunk_xml, "CATEGORY") or "unknown"
            merge_str = self._extract_from_xml_tags(chunk_xml, "MERGE") or "FALSE"
            merge = merge_str.strip().upper() == "TRUE"
            
            # Validate content is not empty
            if not content.strip():
                logger.warning(f"Empty content in chunk, skipping")
                chunk_start = chunks_xml.find("</CHUNK>", chunk_start) + len("</CHUNK>")
                if chunk_start >= len(chunks_xml):
                    break
                continue
            
            # Create chunk object
            chunk = DocumentChunk(
                content=content.strip(),
                category=category.strip(),
                page_id=page_id,
                section_id=section_id,
                merge=merge
            )
            chunks.append(chunk)
            
            logger.debug(f"Parsed chunk: category='{chunk.category}', content_length={len(chunk.content)}, merge={chunk.merge}")
            
            section_id += 1
            
            # Find next chunk
            chunk_start = chunks_xml.find("</CHUNK>", chunk_start) + len("</CHUNK>")
            if chunk_start >= len(chunks_xml):
                break
        
        logger.info(f"Successfully parsed {len(chunks)} chunks from Mistral response")
        return chunks
    
    def _extract_from_xml_tags(self, text: str, tag_name: str) -> Optional[str]:
        """Extract text between XML tags"""
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"
        
        start_index = text.find(start_tag)
        if start_index == -1:
            return None
        
        start_index += len(start_tag)
        end_index = text.find(end_tag, start_index)
        
        if end_index == -1:
            return None
        
        return text[start_index:end_index]
    
    def _merge_with_previous_chunk(self, processed_chunks: List[DocumentChunk], 
                                 new_chunk: DocumentChunk) -> None:
        """Merge new chunk with the previous one"""
        if not processed_chunks:
            return
        
        previous_chunk = processed_chunks[-1]
        
        # Check if previous chunk content is contained in new chunk
        if new_chunk.content.startswith(previous_chunk.content.strip()):
            # Replace previous chunk content with new content
            previous_chunk.content = new_chunk.content
        else:
            # Concatenate the contents
            previous_chunk.content += " " + new_chunk.content
        
        # Update category if needed
        if new_chunk.category != "unknown":
            previous_chunk.category = new_chunk.category
        
        logger.debug(f"Merged chunk with previous - new length: {len(previous_chunk.content)}")
    
    def _chunk_to_xml(self, chunk: DocumentChunk) -> str:
        """Convert chunk to XML format for next iteration"""
        return f"""<CONTENT>{chunk.content}</CONTENT>
<CATEGORY>{chunk.category}</CATEGORY>
<MERGE>{str(chunk.merge).upper()}</MERGE>"""
    
    def get_chunk_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """Get statistics about the chunking results"""
        if not chunks:
            return {"total_chunks": 0}
        
        total_chars = sum(len(chunk.content) for chunk in chunks)
        categories = {}
        
        for chunk in chunks:
            categories[chunk.category] = categories.get(chunk.category, 0) + 1
        
        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "average_chunk_size": total_chars // len(chunks),
            "categories": categories,
            "merge_count": sum(1 for chunk in chunks if chunk.merge)
        }
    
    def _needs_chunking(self, text: str, max_chunk_size: int) -> bool:
        """
        Determine if a document needs chunking based on its length and content.
        
        Args:
            text: The document text
            max_chunk_size: Maximum chunk size in characters
            
        Returns:
            True if chunking is needed, False otherwise
        """
        # If document is shorter than max_chunk_size, no chunking needed
        if len(text) <= max_chunk_size:
            return False
        
        # If document is only slightly longer, still no chunking needed
        # (e.g., 10% buffer)
        if len(text) <= max_chunk_size * 1.1:
            return False
        
        # Check for natural break points (headers, sections)
        # If document has clear structure, chunking might be beneficial
        has_structure = any(marker in text.lower() for marker in [
            'conclusion', 'résumé', 'résultats', 'méthode', 'introduction',
            'discussion', 'tableau', 'figure', 'annexe'
        ])
        
        # For documents with clear structure, chunking is beneficial
        if has_structure and len(text) > max_chunk_size * 1.2:
            return True
        
        # For very long documents, always chunk
        if len(text) > max_chunk_size * 2:
            return True
        
        return False