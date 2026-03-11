from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import os
import httpx

from config.mistral_config import set_mistral_mode, get_current_mode
from config.settings import settings
from config.ner_config import settings as ner_settings, update_ner_settings
from config.database import MongoDBConnection

# Setup logging
logger = logging.getLogger(__name__)

# Router for settings management
router = APIRouter(
    prefix="/settings",
    
    tags=["settings"],
)

class LLMModelUpdateRequest(BaseModel):
    """Request model for updating LLM model settings"""
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class LLMModelConfig(BaseModel):
    """Model representing an LLM configuration entry"""
    id: str
    name: str
    provider: str
    apiKeyRequired: bool = False
    description: Optional[str] = None
    isDefault: bool = False
    endpointType: str = "api"
    base_url: Optional[str] = None
    enabled: bool = True
    instance: Optional[str] = None

class LLMModelAddRequest(BaseModel):
    """Request body to add a new LLM model configuration"""
    model: LLMModelConfig

class LLMModelEditRequest(BaseModel):
    """Request body to edit an existing LLM model configuration matched by id and name"""
    match_id: str
    match_name: str
    updated: LLMModelConfig
    
class EnvVarUpdateRequest(BaseModel):
    """Request model for updating environment variables"""
    key: str
    value: str
    
class GptOpenUrlUpdateRequest(BaseModel):
    """Request model for updating GPT-Open base URL"""
    base_url: str
    
class NERConfigUpdateRequest(BaseModel):
    """Request model for updating NER configuration"""
    max_entities_per_batch: Optional[int] = None
    max_content_size: Optional[int] = None
    chunk_overlapping: Optional[int] = None
    max_concurrent_requests: Optional[int] = None
    aggregation_batch_size: Optional[int] = None

class MasterDeleteRequest(BaseModel):
    phrase: str


# Define available models at module level - empty by default
# Users add their own models via UI or Sync Ollama button
# Models are persisted to MongoDB LLMConfig collection
available_models = []

# --------------------------
# MongoDB storage utilities
# --------------------------

def _load_models_from_db() -> Optional[List[Dict[str, Any]]]:
    try:
        with MongoDBConnection() as db:
            collection = db["LLMConfig"]
            doc = collection.find_one({"_id": "llm_models"})
        if doc and isinstance(doc.get("models"), list) and len(doc["models"]) > 0:
            return doc["models"]
        return None
    except Exception as e:
        logger.warning(f"Could not load LLM models from MongoDB, falling back to static list: {e}")
        return None


def _save_models_to_db(models: List[Dict[str, Any]]) -> None:
    try:
        with MongoDBConnection() as db:
            collection = db["LLMConfig"]
            collection.replace_one(
                {"_id": "llm_models"},
                {"_id": "llm_models", "models": models},
                upsert=True,
            )
        logger.info("LLM models saved to MongoDB (LLMConfig). Static JSON will no longer be used.")
    except Exception as e:
        logger.error(f"Failed to save LLM models to MongoDB: {e}")
        raise


def _get_effective_models() -> List[Dict[str, Any]]:
    models_from_db = _load_models_from_db()
    if models_from_db is not None:
        return models_from_db
    return available_models

@router.get("/llm-models", status_code=200)
async def get_llm_models() -> dict:
    """
    Get all available LLM models and current settings
    """
    # Load from MongoDB if present, otherwise fall back to static list
    effective_models = _get_effective_models()
    # Only expose models that are enabled
    enabled_models = [m for m in effective_models if m.get("enabled", True)]

    # Get current settings
    current_settings = {
        "mode": "api",
        "model": "gpt-oss-20b",
        "has_api_key": False
    }
    
    return {
        "models": enabled_models,
        "current_settings": current_settings
    }


@router.get("/demo-mode", status_code=200)
async def get_demo_mode() -> dict:
    """
    Get demo mode status from environment variable
    """
    demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    return {"demo_mode": demo_mode}


@router.post("/llm-models", status_code=201)
async def add_llm_model(request: LLMModelAddRequest = Body(...)) -> dict:
    """
    Add a new LLM model configuration. After adding, the entire models list is saved to MongoDB.
    """
    try:
        models = list(_get_effective_models())

        # Append the new model; allow duplicate ids with different names
        models.append(request.model.dict())

        # Persist full list to MongoDB so we stop using static JSON
        _save_models_to_db(models)

        return {"success": True, "models": [m for m in models if m.get("enabled", True)]}
    except Exception as e:
        logger.error(f"Error adding LLM model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding LLM model: {str(e)}")


@router.put("/llm-models", status_code=200)
async def edit_llm_model(request: LLMModelEditRequest = Body(...)) -> dict:
    """
    Edit an existing LLM model matched by id and name. Saves the entire list to MongoDB on success.
    """
    try:
        models = list(_get_effective_models())
        updated_model = request.updated.dict()

        found = False
        for idx, model in enumerate(models):
            if model.get("id") == request.match_id and model.get("name") == request.match_name:
                models[idx] = updated_model
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="Model to edit not found")

        _save_models_to_db(models)
        return {"success": True, "models": [m for m in models if m.get("enabled", True)]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing LLM model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error editing LLM model: {str(e)}")

@router.post("/llm-model", status_code=200)
async def update_llm_model(
    request: LLMModelUpdateRequest = Body(...)
) -> dict:
    """
    Update the current LLM model settings
    """
    model_id = request.model_id
    api_key = request.api_key
    base_url = request.base_url
    
    logger.info(f"Received update request for model ID: {model_id}")
    # We need to handle the case where frontend sends 'gpt-oss-20b-ec2', which needs to be mapped back to 'gpt-oss-20b'
    if model_id == "gpt-oss-20b-ec2":
        logger.info("Mapping model ID 'gpt-oss-20b-ec2' to 'gpt-oss-20b'")
        model_id = "gpt-oss-20b"
    
    try:
        logger.info(f"Updating LLM model to: {model_id}")
        
        # Find the selected model in the effective models list (DB or static)
        selected_model = None
        for model in _get_effective_models():
            if model["id"] == model_id:
                selected_model = model
                break
                
        if not selected_model:
            logger.error(f"Unknown model ID: {model_id}")
            raise HTTPException(status_code=400, detail=f"Unknown model ID: {model_id}")
        
        # Handle model selection based on provider
        provider = selected_model.get("provider", "").lower()
        
        if provider == "mistral api":
            # Mistral API model
            logger.info(f"Setting Mistral API model: {model_id}")
            
            # Ensure API mode is enabled
            set_mistral_mode("api")
            
            # Update the model in settings
            settings.mistral_model = model_id
            
            # Update API key if provided
            if api_key:
                logger.info("Updating Mistral API key")
                settings.mistral_api_key = api_key
                # Update environment variable for runtime
                os.environ["MISTRAL_API_KEY"] = api_key
            
            # Route backend to use Mistral client explicitly
            os.environ["LLM_PROVIDER"] = "mistral"
            os.environ["LLM_MODEL"] = model_id
            logger.info(f"✅ LLM_PROVIDER set to 'mistral', LLM_MODEL set to {model_id}")

            # Optionally keep GPT_OPEN_MODEL/Base URL aligned for UI introspection, though not used in Mistral path
            if base_url:
                os.environ["GPT_OPEN_BASE_URL"] = base_url
            settings.gpt_open_model = model_id
            
        elif provider == "openai":
            # OpenAI model
            logger.info(f"Setting OpenAI model: {model_id}")
            
            # Configure to use gpt_open.py
            os.environ["LLM_PROVIDER"] = "openai"
            os.environ["LLM_MODEL"] = model_id
            
            # Get model-specific base URL from model definition
            model_base_url = selected_model.get("base_url")
            
            # Use the explicit base_url from request if provided, otherwise use the model-specific one
            selected_base_url = base_url or model_base_url
            
            if selected_base_url:
                logger.info(f"Updating GPT Open base URL to: {selected_base_url}")
                settings.gpt_open_base_url = selected_base_url
                # Update environment variable for runtime
                os.environ["GPT_OPEN_BASE_URL"] = selected_base_url
                logger.info(f"✅ Base URL set to {selected_base_url}")
            
            # Update API key if provided
            if api_key:
                logger.info("Updating OpenAI API key")
                os.environ["OPENAI_API_KEY"] = api_key
                logger.info("✅ OpenAI API key has been set in the environment")
            
            # Set default model to be used. If the target is an Ollama host (common port 11434),
            # use the Ollama tag format with a colon so the client routes to /api/generate.
            model_for_client = model_id
            try:
                if model_id == "gpt-oss-20b" and selected_base_url and ("11434" in selected_base_url):
                    model_for_client = "gpt-oss:20b"
                    logger.info("Mapping model 'gpt-oss-20b' to Ollama tag 'gpt-oss:20b' based on base URL")
            except Exception:
                pass

            settings.gpt_open_model = model_for_client
            # Also update environment variable
            os.environ["GPT_OPEN_MODEL"] = model_for_client
            
        elif provider == "ollama":
            # Ollama provider: reuse GPT-Open client path by setting base URL and model
            logger.info(f"Setting Ollama model (via GPT-Open client path): {model_id}")
            selected_base_url = base_url or selected_model.get("base_url")
            if selected_base_url:
                settings.gpt_open_base_url = selected_base_url
                os.environ["GPT_OPEN_BASE_URL"] = selected_base_url
                logger.info(f"✅ GPT_OPEN_BASE_URL set to {selected_base_url}")

            # Update default model to ollama tag (e.g., 'mistral-small:22b')
            settings.gpt_open_model = model_id
            os.environ["GPT_OPEN_MODEL"] = model_id
            logger.info(f"✅ GPT_OPEN_MODEL set to {model_id}")

            # Ensure provider is set to gpt_open so key checks don't use Mistral path
            os.environ["LLM_PROVIDER"] = "gpt_open"
            os.environ["LLM_MODEL"] = model_id
            logger.info("✅ LLM_PROVIDER set to 'gpt_open'")

        else:
            # Provider not supported
            logger.error(f"Unsupported provider: {provider} for model ID: {model_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported provider: {provider} for model ID: {model_id}"
            )
        
        # Return success response
        return {
            "success": True,
            "message": f"LLM model updated to {model_id}",
            "current_mode": get_current_mode()
        }
        
    except Exception as e:
        logger.error(f"Error updating LLM model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating LLM model: {str(e)}"
        )
        
@router.post("/set-env-var", status_code=200)
async def set_environment_variable(
    request: EnvVarUpdateRequest = Body(...)
) -> dict:
    """
    Set an environment variable directly
    """
    try:
        key = request.key
        value = request.value
        
        # Safety check - only allow specific environment variables to be set
        allowed_keys = [
            "MISTRAL_API_KEY",
            "OPENAI_API_KEY",
            "MISTRAL_MODEL"
        ]
        
        if key not in allowed_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Not allowed to set environment variable: {key}"
            )
            
        # Set the environment variable
        logger.info(f"Setting environment variable {key}")
        os.environ[key] = value
        
        # If this is the Mistral API key, also update settings
        if key == "MISTRAL_API_KEY":
            settings.mistral_api_key = value
            logger.info(f"Updated settings.mistral_api_key with value from direct API call")
        
        return {
            "success": True,
            "message": f"Environment variable {key} set successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting environment variable: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error setting environment variable: {str(e)}"
        )
        
@router.post("/gpt-open-url", status_code=200)
async def update_gpt_open_url(
    request: GptOpenUrlUpdateRequest = Body(...)
) -> dict:
    """
    Update the GPT-Open base URL
    """
    try:
        base_url = request.base_url
        
        # Validate URL format (basic check)
        if not base_url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="Base URL must start with http:// or https://"
            )
            
        # Update the setting
        logger.info(f"Updating GPT-Open base URL to: {base_url}")
        settings.gpt_open_base_url = base_url
        
        # Also update environment variable for runtime
        os.environ["GPT_OPEN_BASE_URL"] = base_url
        
        return {
            "success": True,
            "message": "GPT-Open base URL updated successfully",
            "current_url": base_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating GPT-Open base URL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating GPT-Open base URL: {str(e)}"
        )
        
@router.post("/master-delete", status_code=200)
async def master_delete_all(request: MasterDeleteRequest = Body(...)) -> dict:
    """
    Danger: Delete all reports and uploaded documents from MongoDB.
    Requires exact confirmation phrase: "delete all".
    """
    try:
        if (request.phrase or "").strip().lower() != "delete all":
            raise HTTPException(status_code=400, detail="Confirmation phrase mismatch")

        with MongoDBConnection() as db:
            reports = db["reports"]
            documents = db["documents"]
            rep_result = reports.delete_many({})
            doc_result = documents.delete_many({})
        logger.warning(f"MASTER DELETE executed: reports={rep_result.deleted_count}, documents={doc_result.deleted_count}")
        return {
            "success": True,
            "deleted": {
                "reports": rep_result.deleted_count,
                "documents": doc_result.deleted_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during master delete: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during master delete: {str(e)}")
        
@router.get("/ner-config", status_code=200)
async def get_ner_config() -> dict:
    """
    Get the current NER configuration
    """
    try:
        # Get current NER settings
        config = {
            "max_entities_per_batch": ner_settings.max_entities_per_batch,
            "max_content_size": ner_settings.max_content_size,
            "chunk_overlapping": ner_settings.chunk_overlapping,
            "max_concurrent_requests": ner_settings.max_concurrent_requests,
            "aggregation_batch_size": ner_settings.aggregation_batch_size
        }
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"Error getting NER configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting NER configuration: {str(e)}"
        )
        
@router.post("/ner-config", status_code=200)
async def update_ner_config(
    request: NERConfigUpdateRequest = Body(...)
) -> dict:
    """
    Update the NER configuration
    """
    try:
        # Create a dictionary with only the provided values
        config_updates = {}
        
        if request.max_entities_per_batch is not None:
            config_updates["max_entities_per_batch"] = request.max_entities_per_batch
            
        if request.max_content_size is not None:
            config_updates["max_content_size"] = request.max_content_size
            
        if request.chunk_overlapping is not None:
            config_updates["chunk_overlapping"] = request.chunk_overlapping
            
        if request.max_concurrent_requests is not None:
            config_updates["max_concurrent_requests"] = request.max_concurrent_requests
            
        if request.aggregation_batch_size is not None:
            config_updates["aggregation_batch_size"] = request.aggregation_batch_size
            
        # Update NER settings
        if config_updates:
            logger.info(f"Updating NER configuration: {config_updates}")
            update_ner_settings(config_updates)
            
        # Get the updated configuration
        updated_config = {
            "max_entities_per_batch": ner_settings.max_entities_per_batch,
            "max_content_size": ner_settings.max_content_size,
            "chunk_overlapping": ner_settings.chunk_overlapping,
            "max_concurrent_requests": ner_settings.max_concurrent_requests,
            "aggregation_batch_size": ner_settings.aggregation_batch_size
        }
        
        return {
            "success": True,
            "message": "NER configuration updated successfully",
            "config": updated_config
        }
        
    except Exception as e:
        logger.error(f"Error updating NER configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating NER configuration: {str(e)}"
        )
