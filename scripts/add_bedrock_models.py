#!/usr/bin/env python3
"""
Add AWS Bedrock models to the LLM models database

This script adds the available AWS Bedrock models to the database so they
appear in the frontend model selection dropdown.
"""

import os
import sys
import asyncio
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config.database import MongoDBConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define AWS Bedrock models that should be available in the UI
BEDROCK_MODELS = [
    {
        "id": "claude-3-haiku",
        "name": "Claude 3 Haiku",
        "provider": "bedrock",
        "apiKeyRequired": False,  # Uses AWS credentials instead
        "description": "Anthropic's Claude 3 Haiku model via AWS Bedrock - fast and cost-effective",
        "isDefault": True,  # Set as default since we migrated to Bedrock
        "endpointType": "api",
        "base_url": "",  # Not needed for Bedrock
        "enabled": True,
        "instance": "anthropic.claude-3-haiku-20240307-v1:0"
    },
    {
        "id": "claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "provider": "bedrock",
        "apiKeyRequired": False,
        "description": "Anthropic's Claude 3 Sonnet model via AWS Bedrock - balanced performance",
        "isDefault": False,
        "endpointType": "api",
        "base_url": "",
        "enabled": True,
        "instance": "anthropic.claude-3-sonnet-20240229-v1:0"
    },
    {
        "id": "claude-3-opus",
        "name": "Claude 3 Opus",
        "provider": "bedrock",
        "apiKeyRequired": False,
        "description": "Anthropic's Claude 3 Opus model via AWS Bedrock - highest capability",
        "isDefault": False,
        "endpointType": "api",
        "base_url": "",
        "enabled": True,
        "instance": "anthropic.claude-3-opus-20240229-v1:0"
    }
]

def _load_models_from_db():
    """Load existing models from MongoDB"""
    try:
        with MongoDBConnection() as db:
            collection = db["LLMConfig"]
            doc = collection.find_one({"_id": "llm_models"})
        if doc and isinstance(doc.get("models"), list):
            return doc["models"]
        return []
    except Exception as e:
        logger.warning(f"Could not load LLM models from MongoDB: {e}")
        return []

def _save_models_to_db(models):
    """Save models to MongoDB"""
    try:
        with MongoDBConnection() as db:
            collection = db["LLMConfig"]
            collection.replace_one(
                {"_id": "llm_models"},
                {"_id": "llm_models", "models": models},
                upsert=True,
            )
        logger.info("LLM models saved to MongoDB (LLMConfig)")
    except Exception as e:
        logger.error(f"Failed to save LLM models to MongoDB: {e}")
        raise

def add_bedrock_models():
    """Add AWS Bedrock models to the database if they don't already exist"""
    logger.info("🚀 Adding AWS Bedrock models to the database...")
    
    # Load existing models
    existing_models = _load_models_from_db()
    logger.info(f"📚 Found {len(existing_models)} existing models in database")
    
    # Check which Bedrock models already exist
    existing_bedrock_ids = set()
    for model in existing_models:
        if model.get("provider") == "bedrock":
            existing_bedrock_ids.add(model.get("id"))
    
    # Add new Bedrock models
    models_added = 0
    for bedrock_model in BEDROCK_MODELS:
        if bedrock_model["id"] not in existing_bedrock_ids:
            existing_models.append(bedrock_model)
            models_added += 1
            logger.info(f"✅ Added: {bedrock_model['name']} ({bedrock_model['id']})")
        else:
            logger.info(f"⏭️  Skipped: {bedrock_model['name']} (already exists)")
    
    if models_added > 0:
        # Save updated models list
        _save_models_to_db(existing_models)
        logger.info(f"🎉 Successfully added {models_added} new AWS Bedrock models!")
        
        # Show summary of all Bedrock models
        logger.info("\n📋 All AWS Bedrock models now available:")
        for model in existing_models:
            if model.get("provider") == "bedrock":
                default_indicator = " (DEFAULT)" if model.get("isDefault") else ""
                logger.info(f"   • {model['name']}{default_indicator}")
    else:
        logger.info("✨ No new models to add - all AWS Bedrock models already exist")

def main():
    """Main entry point"""
    try:
        add_bedrock_models()
        logger.info("\n✅ Script completed successfully!")
        logger.info("💡 The AWS Bedrock models should now appear in the frontend dropdown.")
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()