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
        self.mistral_client = None  
        self.is_initialized = False  # Add this line!  
        # Updated supported formats based on Mistral OCR capabilities              
        self.supported_formats = {'.pdf', '.pptx', '.docx', '.txt', '.md', '.csv',               
                                '.png', '.jpg', '.jpeg', '.avif', '.xml', '.hl7'}                  
                          
    async def initialize(self):                      
        """Initialize database and Mistral client connections with detailed error reporting"""      
        if self.is_initialized:      
            logger.info("Parser already initialized")      
            return      
                  
        logger.info("🔧 Starting parser initialization...")      
        initialization_errors = []      
              
        try:                      
            # Check for Mistral API key first      
            api_key = os.environ.get("MISTRAL_API_KEY")      
            logger.info(f"🔑 MISTRAL_API_KEY status: {'SET' if api_key else 'NOT SET'}")      
                  
            if not api_key:                  
                error_msg = "MISTRAL_API_KEY environment variable is required but not set"      
                logger.error(f"❌ {error_msg}")      
                initialization_errors.append(error_msg)      
            else:      
                logger.info(f"✅ MISTRAL_API_KEY found (length: {len(api_key)})")      
                      
                # Try to import and initialize Mistral client      
                try:      
                    logger.info("📦 Importing Mistral client...")      
                    from mistralai import Mistral      
                          
                    logger.info("🚀 Initializing Mistral client...")      
                    self.mistral_client = Mistral(api_key=api_key)      
                    logger.info("✅ Mistral client initialized successfully")      
                          
                except ImportError as e:      
                    error_msg = f"Failed to import Mistral library: {e}"      
                    logger.error(f"❌ {error_msg}")      
                    initialization_errors.append(error_msg)      
                except Exception as e:      
                    error_msg = f"Failed to initialize Mistral client: {e}"      
                    logger.error(f"❌ {error_msg}")      
                    logger.error(f"❌ Full error: {traceback.format_exc()}")      
                    initialization_errors.append(error_msg)      
                  
                      
            # Try to initialize mistral chunking      
            try:      
                logger.info("📝 Testing mistral chunking import...")      
                import universal_document_parser  
                mistral_file = "universal_document_parser/mistral_chunking.py"  
                print(f"File exists: {os.path.exists(mistral_file)}")  
                from mistral_chunking import mistral_chunk_text  
                logger.info("✅ Mistral chunking available")  
            except ImportError as e:      
                error_msg = f"Mistral chunking not available: {e}"      
                logger.warning(f"⚠️  {error_msg}")      
                initialization_errors.append(error_msg)      
                              
            self.is_initialized = True      
            logger.info(f"🎉 Parser initialization completed with {len(initialization_errors)} warnings/errors")      
                  
            if initialization_errors:      
                logger.warning("⚠️  Initialization warnings/errors:")      
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
        """Determine if file is supported by Mistral OCR"""              
        suffix = Path(file_path).suffix.lower()              
        return suffix in {'.png', '.jpeg', '.jpg', '.avif', '.pdf', '.pptx', '.docx'}              
                  
    async def _extract_text_content(self, file_path: str) -> str:                  
        """Extract text content from plain text files"""                  
        try:                  
            with open(file_path, 'r', encoding='utf-8') as file:                  
                return file.read()                  
        except UnicodeDecodeError:                  
            with open(file_path, 'r', encoding='latin-1') as file:                  
                return file.read()                  
                  
    async def _perform_ocr(self, file_path: str) -> str:                  
        """Perform OCR using mistral-ocr-latest model with detailed error reporting"""  
        logger.info(f"🔍 Starting OCR for: {file_path}")  
          
        try:  
            # Check if Mistral client is available  
            if self.mistral_client is None:  
                error_msg = "Mistral client is not initialized - cannot perform OCR"  
                logger.error(f"❌ {error_msg}")  
                raise ValueError(error_msg)  
              
            if not self._is_ocr_supported(file_path):              
                error_msg = f"File format not supported by OCR: {Path(file_path).suffix}"  
                logger.error(f"❌ {error_msg}")  
                raise ValueError(error_msg)  
              
            # Check if file exists  
            if not os.path.exists(file_path):  
                error_msg = f"File does not exist: {file_path}"  
                logger.error(f"❌ {error_msg}")  
                raise FileNotFoundError(error_msg)  
                              
            # Check file size (Mistral limit is 50MB)              
            file_size = os.path.getsize(file_path)  
            logger.info(f"📊 File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")  
              
            if file_size > 50 * 1024 * 1024:  # 50MB in bytes              
                logger.warning(f"⚠️  File size ({file_size} bytes) exceeds 50MB, using upload method")              
                return await self._perform_ocr_with_upload(file_path)              
                          
            # Get file extension to determine document type              
            file_extension = Path(file_path).suffix.lower()              
            logger.info(f"📄 Processing {file_extension} file")  
                          
            # Encode file to base64              
            logger.info("🔄 Encoding file to base64...")  
            base64_content = self._encode_file_to_base64(file_path)  
            logger.info(f"✅ File encoded (base64 length: {len(base64_content)})")  
                          
            # Determine document type and create data URL              
            if file_extension in {'.png', '.jpeg', '.jpg', '.avif'}:              
                mime_type = self._get_image_mime_type(file_extension)              
                document_type = "image_url"              
                data_url = f"data:{mime_type};base64,{base64_content}"              
            elif file_extension in {'.pdf', '.pptx', '.docx'}:              
                mime_type = self._get_document_mime_type(file_extension)              
                document_type = "document_url"              
                data_url = f"data:{mime_type};base64,{base64_content}"              
            else:              
                error_msg = f"Unsupported file format: {file_extension}"  
                logger.error(f"❌ {error_msg}")  
                raise ValueError(error_msg)  
              
            logger.info(f"🎯 Document type: {document_type}, MIME: {mime_type}")  
                          
            # Call Mistral OCR API              
            logger.info("🚀 Calling Mistral OCR API...")  
            ocr_result = await self._call_mistral_ocr(document_type, data_url)  
            logger.info(f"✅ OCR completed, extracted {len(ocr_result)} characters")  
            return ocr_result              
                          
        except Exception as e:                  
            error_msg = f"OCR processing failed for {file_path}: {e}"  
            logger.error(f"❌ {error_msg}")  
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")  
            raise Exception(error_msg)  
              
    def _encode_file_to_base64(self, file_path: str) -> str:              
        """Encode file to base64 string"""              
        try:              
            with open(file_path, 'rb') as file:              
                return base64.b64encode(file.read()).decode('utf-8')              
        except FileNotFoundError:              
            logger.error(f"File not found: {file_path}")              
            raise              
        except Exception as e:              
            logger.error(f"Error encoding file {file_path}: {e}")              
            raise              
              
    def _get_image_mime_type(self, extension: str) -> str:              
        """Get MIME type for image files"""              
        mime_types = {              
            '.png': 'image/png',              
            '.jpeg': 'image/jpeg',              
            '.jpg': 'image/jpeg',              
            '.avif': 'image/avif'              
        }              
        return mime_types.get(extension, 'image/jpeg')              
              
    def _get_document_mime_type(self, extension: str) -> str:              
        """Get MIME type for document files"""              
        mime_types = {              
            '.pdf': 'application/pdf',              
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',              
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'              
        }              
        return mime_types.get(extension, 'application/pdf')              
                  
    async def _call_mistral_ocr(self, document_type: str, data_url: str) -> str:          
        """Call Mistral OCR API with detailed logging"""          
        try:  
            logger.info(f"📡 Preparing Mistral OCR call (type: {document_type})")  
              
            # Verify mistral client  
            if self.mistral_client is None:  
                raise ValueError("Mistral client is None - not properly initialized")  
              
            if not hasattr(self.mistral_client, 'ocr'):  
                raise ValueError("Mistral client does not have 'ocr' attribute")  
                  
            logger.info("✅ Mistral client and OCR attribute verified")  
                  
            # Create document object based on type          
            if document_type == "image_url":          
                document = {          
                    "type": "image_url",          
                    "image_url": data_url          
                }          
            else:  # document_url          
                document = {          
                    "type": "document_url",           
                    "document_url": data_url          
                }          
              
            logger.info(f"📄 Document object created: {document_type}")  
                    
            # Call Mistral OCR API (note: this is synchronous, so we wrap it)          
            def _sync_ocr_call():  
                logger.info("🔄 Making synchronous OCR call...")  
                try:  
                    result = self.mistral_client.ocr.process(          
                        model="mistral-ocr-latest",          
                        document=document,          
                        include_image_base64=True          
                    )  
                    logger.info("✅ OCR API call completed")  
                    return result  
                except Exception as e:  
                    logger.error(f"❌ OCR API call failed: {e}")  
                    logger.error(f"❌ OCR call traceback: {traceback.format_exc()}")  
                    raise  
                    
            # Import and create the executor properly          
            import concurrent.futures  
            logger.info("🔄 Running OCR in thread pool...")  
              
            with concurrent.futures.ThreadPoolExecutor() as executor:          
                ocr_response = await asyncio.get_event_loop().run_in_executor(          
                    executor, _sync_ocr_call          
                )          
              
            logger.info(f"✅ OCR response received: {type(ocr_response)}")  
                    
            # Extract clean text from the response          
            extracted_text = ""          
                    
            # Extract from pages (this is what Mistral returns)          
            if hasattr(ocr_response, 'pages') and ocr_response.pages:  
                logger.info(f"📄 Processing {len(ocr_response.pages)} pages")  
                page_texts = []          
                for i, page in enumerate(ocr_response.pages):          
                    if hasattr(page, 'markdown') and page.markdown:  
                        page_texts.append(page.markdown)  
                        logger.info(f"✅ Page {i+1}: {len(page.markdown)} characters")  
                    else:  
                        logger.warning(f"⚠️  Page {i+1}: no markdown content")  
                extracted_text = '\n\n'.join(page_texts)          
                        
            # Fallback extraction methods          
            elif hasattr(ocr_response, 'text') and ocr_response.text:  
                logger.info("📄 Using response.text")  
                extracted_text = ocr_response.text          
            elif hasattr(ocr_response, 'content') and ocr_response.content:  
                logger.info("📄 Using response.content")  
                extracted_text = ocr_response.content          
            else:          
                # Log what we got and return string representation  
                logger.warning(f"⚠️  Unexpected OCR response structure: {type(ocr_response)}")  
                logger.warning(f"⚠️  Available attributes: {dir(ocr_response)}")  
                extracted_text = str(ocr_response)          
                    
            logger.info(f"✅ OCR extracted {len(extracted_text)} characters")          
            return extracted_text          
                    
        except Exception as e:          
            error_msg = f"Mistral OCR API call failed: {e}"  
            logger.error(f"❌ {error_msg}")  
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")  
            raise Exception(error_msg)  
        
    # ... (keeping all your other methods as they are)  
      
    def _structure_content(self, raw_content: str):          
        """Structure content into logical document elements with improved logic"""          
        try:      
            from .mistral_chunking import mistral_chunk_text      
            formatted_text = mistral_chunk_text(raw_content)        
            return formatted_text          
        except ImportError:      
            logger.warning("Mistral chunking not available, using raw content")      
            return raw_content      
        except Exception as e:      
            logger.error(f"Mistral chunking failed: {e}")      
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
          
        logger.info(f"🚀 Starting document parsing for document ID: {document_id}")  
          
        # Auto-initialize if not already done  
        if not self.is_initialized:  
            logger.info("🔧 Parser not initialized, initializing now...")  
            try:  
                await self.initialize()  
            except Exception as e:  
                error_msg = f"Parser initialization failed: {e}"  
                logger.error(f"❌ {error_msg}")  
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
                          
            # Extract content              
            if self._is_plain_text(file_path):              
                raw_content = await self._extract_text_content(file_path)              
            else:              
                raw_content = await self._perform_ocr(file_path)              
                          
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
                "raw_ocr": raw_content,                 
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
