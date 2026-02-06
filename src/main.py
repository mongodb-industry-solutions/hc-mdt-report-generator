# Create a main.py that uses your original structure  
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from services.auth.jwt_service import jwt_service
from config.database import create_indexes  
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from controllers.report_controller import router as report_router  
from controllers.patient_document_controller import router as patient_document_router
#from controllers.auth_controller import router as auth_router
from controllers.security_controller import router as security_router
from controllers.settings_controller import router as settings_router
from controllers.observability_controller import router as observability_router
# Deprecated - evaluation is now per-report
# from controllers.evaluate_controller import router as evaluate_router
from controllers.ground_truth_controller import router as ground_truth_router
from utils.exceptions import ValidationException, NotFoundException, DatabaseException

from middleware.rate_limiter import rate_limit_general
import logging
import asyncio  
  
# Configure logging  
logging.basicConfig(  
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'  
)
logger = logging.getLogger(__name__)  
  
app = FastAPI(  
    title="ClarityGR - AI-Powered Medical Document Processing API",  
    description="""
    🏥 **ClarityGR** is an AI-powered platform for automated extraction and analysis of medical entities from clinical documents.
    
    ## Features
    - 📄 **Document Processing**: Upload and process medical documents (PDF, images, text)
    - 🧠 **AI Entity Extraction**: Extract structured medical entities using advanced NER
    - 📊 **MDT Report Generation**: Generate comprehensive multidisciplinary team reports
    - 🔍 **Real-time Processing**: Asynchronous document processing with status tracking
    
    ## Getting Started
    1. Upload a patient document using POST `/patients/{patient_id}/document`
    2. Check processing status with GET `/patients/{patient_id}/documents`
    3. Generate MDT reports with POST `/patients/{patient_id}/reports`
    """,  
    version="1.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "ClarityGR Support",
        "email": "support@claritygr.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[  
        {"name": "Health", "description": "Health check and system status endpoints"},
        {"name": "Root", "description": "Root API information"},
        {"name": "Reports", "description": "MDT report generation and management"},  
        {"name": "Patient Documents", "description": "Document upload, processing, and retrieval"},
        {"name": "Settings", "description": "Application settings management"}
    ],
    swagger_ui_parameters={
        "faviconHref": "/assets/medical-icon.svg"
    }  
)  
  
app.add_middleware(  
    CORSMiddleware,  
    allow_origins=settings.allowed_origins,  # Secure CORS configuration
    allow_credentials=settings.allow_credentials,  
    allow_methods=settings.allowed_methods,  
    allow_headers=settings.allowed_headers,
    max_age=settings.max_age,
)  

# General rate limiting middleware
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    # Skip rate limiting for health checks and system status
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    try:
        # Apply general rate limiting (except for auth endpoints which have their own)
        if not request.url.path.startswith("/auth/"):
            rate_limit_general(request)
        
        return await call_next(request)
    except HTTPException:
        # Rate limit exceeded - re-raise the exception
        raise

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response



# Health check endpoint
@app.get("/health", tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "ClarityGR API",
        "version": "1.0.0"
    }



# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "ClarityGR API",
        "docs": "/docs",
        "health": "/health"
    }

# Global exception handlers
@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "detail": str(exc)}
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc)}
    )

@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    return JSONResponse(
        status_code=500,
        content={"error": "Database Error", "detail": "An internal error occurred"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred"}
    )
  
#app.include_router(auth_router)
app.include_router(security_router)
app.include_router(report_router)
app.include_router(patient_document_router)
app.include_router(settings_router)
app.include_router(observability_router)
app.include_router(ground_truth_router)

from controllers.entity_config_controller import router as entity_config_router
app.include_router(entity_config_router)

# Serve React static files
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Serve UI public assets (including default favicon) for docs and other clients
ui_public_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ui/public"))
if os.path.isdir(ui_public_path):
    app.mount("/assets", StaticFiles(directory=ui_public_path), name="assets")

# Startup validation
@app.on_event("startup")
async def startup_validation():
    """Validate critical services on application startup"""
    global system_status
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting ClarityGR application...")
    
    try:
        # Validate Mistral API
        #logger.info("🔍 Validating critical services...")
        #mistral_result = await mistral_validator.validate_api_configuration()
        
        #system_status["mistral_api"] = {
        #    "valid": mistral_result["valid"],
        #    "error": mistral_result.get("error")
        #}
       # 
       # if not mistral_result["valid"]:
        #    logger.error(f"❌ CRITICAL: Mistral API validation failed: {mistral_result['error']}")
        #    logger.error("❌ Application will continue but AI features will be unavailable")
        #else:
        #    logger.info("✅ Mistral API validation passed")
        
        # Initialize database indexes for user authentication
        try:
            create_indexes()
            logger.info("✅ Database indexes created successfully")
        except Exception as e:
            logger.error(f"⚠️  Database index creation failed: {e}")
        
        # Seed EntityConfig from file if missing
        try:
            from config.entity_config import seed_if_missing
            if seed_if_missing():
                logger.info("✅ Seeded EntityConfig from file baseline")
            else:
                logger.info("EntityConfig already present in DB")
        except Exception as e:
            logger.error(f"⚠️  EntityConfig seeding failed: {e}")
        
        # Load JWT blacklisted tokens
        try:
            jwt_service.load_blacklisted_tokens()
            logger.info("✅ JWT blacklist loaded successfully")
        except Exception as e:
            logger.error(f"⚠️  JWT blacklist loading failed: {e}")
        
        # Initialize LLM clients for model warmup
        try:
      
            
            # Import the services that use Mistral clients
            from services.processors.ocr_processor import OCRProcessor
            from services.processors.text_normalizer import TextNormalizer
            from services.document_categorization_service import DocumentCategorizationService
            
            # Initialize key services to trigger model loading
            ocr_processor = OCRProcessor()
            text_normalizer = TextNormalizer() 
            doc_categorizer = DocumentCategorizationService()
            
            # Force initialization of their Mistral clients
            await ocr_processor.initialize()
            await text_normalizer.initialize()
            if hasattr(doc_categorizer, 'initialize'):
                await doc_categorizer.initialize()
            
        except Exception as e:
            logger.error("⚠️ AI features may not work properly")
        
        logger.info("✅ Application startup completed")
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Startup validation failed: {e}")
        # Don't fail startup completely, but mark as degraded  
  
if __name__ == "__main__":  
    import uvicorn  
    uvicorn.run(  
        "main:app",  
        host="0.0.0.0",  
        port=8000,  
        reload=True,  
        log_level="info"  
    )  