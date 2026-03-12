"""              
Universal Document Parser MCP Server Tool              
A tool that receives any document and parses it into a standardized JSON structure.              
"""              
              
import json              
import uuid              
import base64              
import logging              
from typing import Dict, List, Any, Optional, Union              
from pathlib import Path              
from datetime import datetime              
import asyncio              
import os              
import re      
import traceback  
  
# Configure logging with more detail  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  
)              
logger = logging.getLogger(__name__)              
  
class DocumentElement:              
    """Represents a structured document element"""              
    def __init__(self, element_type: str, content: Any, start_char: int,               
                 end_char: int, page: int, metadata: Optional[Dict] = None):              
        self.type = element_type              
        self.content = content              
        self.start_char = start_char              
        self.end_char = end_char              
        self.page = page              
        self.metadata = metadata or {}              
              
    def to_dict(self) -> Dict[str, Any]:              
        result = {              
            "type": self.type,              
            "content": self.content,              
            "start_char": self.start_char,              
            "end_char": self.end_char,              
            "page": self.page              
        }              
        if self.metadata:              
            result["metadata"] = self.metadata              
        return result              
              
              
class UniversalDocumentParser:                  
    """Main parser class for handling document processing"""                  
                      
    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/",                   
                 db_name: str = "document_parser"):                  
        self.mongodb_uri = mongodb_uri                  
        self.db_name = db_name                  
        self.client = None                  
        self.db = None                  
        self.is_initialized = False  # Add this line!  
        # Supported text file formats              
        self.supported_formats = {'.txt', '.md', '.csv', '.xml', '.hl7'}                  
                          
    async def initialize(self):                      
        """Initialize database connections"""      
        if self.is_initialized:      
            return      
                  
        initialization_errors = []                      
              
        try:                      
            if initialization_errors:      
                logger.warning("Initialization warnings/errors:")      
                for i, error in enumerate(initialization_errors, 1):      
                    logger.warning(f"   {i}. {error}")      
                          
        except Exception as e:                      
            error_msg = f"Critical initialization failure: {e}"      
            logger.error(f"💥 {error_msg}")      
            logger.error(f"💥 Full traceback: {traceback.format_exc()}")      
            initialization_errors.append(error_msg)      
            raise Exception(f"Parser initialization failed: {'; '.join(initialization_errors)}")      
                  
    def _is_plain_text(self, file_path: str) -> bool:                  
        """Determine if file is plain text"""                  
        return Path(file_path).suffix.lower() in {'.txt', '.md', '.csv','.xml','.hl7'}                  
              
    def _is_ocr_supported(self, file_path: str) -> bool:              
        """OCR support has been removed - only text files are supported"""              
        return False              
                  
    async def _extract_text_content(self, file_path: str) -> str:                  
        """Extract text content from plain text files"""                  
        try:                  
            with open(file_path, 'r', encoding='utf-8') as file:                  
                return file.read()                  
        except UnicodeDecodeError:                  
            with open(file_path, 'r', encoding='latin-1') as file:                  
                return file.read()                  
        
    # ... (keeping all your other methods as they are)  
      
    def _structure_content(self, raw_content: str):          
        """Structure content into logical document elements"""          
        # Basic content structuring - advanced chunking has been removed
        return raw_content      

      
    def _extract_metadata(self, file_path: str, content: str) -> Dict[str, Any]:              
        """Extract document metadata"""              
        file_info = Path(file_path)              
                      
        return {              
            "title": file_info.stem,              
            "filename": file_info.name,              
            "file_type": file_info.suffix,              
            "file_size": file_info.stat().st_size if file_info.exists() else 0,              
            "created_at": datetime.now().isoformat(),              
            "character_count": len(content),              
            "word_count": len(content.split()),              
            "author": None,              
            "subject": None,              
            "keywords": []              
        }              
              
    async def parse_document(self, source_document: Union[str, Dict], bypass_formatting: bool = False) -> Dict[str, Any]:               
        """Main parsing function with auto-initialization"""              
        errors = []              
        document_id = str(uuid.uuid4())  
          
        # Auto-initialize if not already done  
        if not self.is_initialized:  
            try:  
                await self.initialize()  
            except Exception as e:  
                error_msg = f"Parser initialization failed: {e}"  
                logger.error(f"{error_msg}")  
                errors.append(error_msg)  
                return {              
                    "document_id": document_id,              
                    "status": "error",              
                    "result": {              
                        "parsed_document": None,              
                        "plain_text": "",              
                        "errors": errors              
                    }              
                }      
                      
        try:              
            # Handle input (file path or base64 content)              
            if isinstance(source_document, str):              
                file_path = source_document              
                            
            # Validate file format              
            if not any(file_path.lower().endswith(fmt) for fmt in self.supported_formats):              
                raise ValueError(f"Unsupported file format: {Path(file_path).suffix}")              
                          
            # Extract content - only text files are supported              
            if self._is_plain_text(file_path):              
                raw_content = await self._extract_text_content(file_path)              
            else:              
                raise ValueError(f"File type {Path(file_path).suffix} requires OCR, which has been removed. Only text files (.txt, .md, .csv, .xml, .hl7) are supported.")              
                          
            # Structure content using improved logic or bypass formatting  
            if bypass_formatting:  
                document_elements = raw_content  # Use plain text as-is  
                logger.info("🔄 Bypassing formatting - using raw content")  
            else:  
                document_elements = self._structure_content(raw_content)  
      
                          
            # Generate metadata              
            metadata = self._extract_metadata(file_path, raw_content)              
                                                
            # Prepare result              
            result = {    
                "parsed_document": {              
                    "metadata": metadata,              
                    "document_elements":  document_elements           
                },    
                "plain_text": raw_content,              
                "errors": errors              
            }              
                                    
                          
            return {              
                "document_id": document_id,              
                "status": "success",              
                "result": result              
            }              
                          
        except Exception as e:              
            error_msg = f"Document parsing failed: {str(e)}"              
            logger.error(error_msg)              
            errors.append(error_msg)              
                          
            return {              
                "document_id": document_id,              
                "status": "error",              
                "result": {              
                    "parsed_document": None,              
                    "plain_text": "",              
                    "errors": errors              
                }              
            }              
     
              
# MCP Server Setup              
try:  
    from mcp import types              
    from mcp.server import Server              
    from mcp.server.stdio import stdio_server     
  
    app = Server("universal-doc-parser")              
    parser = UniversalDocumentParser()              
                  
    @app.list_tools()                  
    async def list_tools() -> List[types.Tool]:                  
        """List available tools"""                  
        return [                  
            types.Tool(                  
                name="parse_document",                  
                description="Parse any document into structured JSON format",                  
                inputSchema={                  
                    "type": "object",                  
                    "properties": {                  
                        "source_document": {                  
                            "type": "string",                  
                            "description": "Path to the document to parse"                  
                        },  
                        "bypass_formatting": {  
                            "type": "boolean",  
                            "description": "If true, skip formatting and return plain text",  
                            "default": False  
                        }  
                    },                  
                    "required": ["source_document"]                  
                }                  
            )                  
        ]  
            
                  
    @app.call_tool()                  
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:                  
        """Handle tool calls"""                  
        if name != "parse_document":                  
            raise ValueError(f"Unknown tool: {name}")                  
                        
        source_document = arguments.get("source_document")                  
        if not source_document:                  
            raise ValueError("source_document is required")  
            
        bypass_formatting = arguments.get("bypass_formatting", False)  # Add this line  
                        
        # Initialize parser if not already done                  
        if not parser.is_initialized:                  
            await parser.initialize()                  
                        
        # Parse document with bypass flag                  
        result = await parser.parse_document(source_document, bypass_formatting)  # Update this line  
                        
        return [                  
            types.TextContent(                  
                type="text",                  
                text=json.dumps(result, indent=2)                  
            )                  
        ]  

                  
    async def main():              
        """Main entry point"""              
        async with stdio_server() as streams:              
            await app.run(*streams)              
                  
    if __name__ == "__main__":              
        asyncio.run(main())      
  
except ImportError:  
    # MCP not available, just provide the parser class  
    logger.warning("MCP server components not available - only parser class is available")  
