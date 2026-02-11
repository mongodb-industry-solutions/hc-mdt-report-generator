#!/usr/bin/env python3
"""
MongoDB Cluster Setup Script for ClarityGR
Creates necessary collections and indexes for the application.
"""

import os
import sys
from pymongo import MongoClient, IndexModel
from pymongo.errors import ConnectionFailure, CollectionInvalid
from datetime import datetime
import logging

# Add backend to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from config.settings import settings
except ImportError as e:
    print(f"Error importing settings: {e}")
    print("Make sure you're running this from the project root with activated venv")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_collections_and_indexes():
    """Create all necessary collections and indexes for ClarityGR"""
    
    # Connect to MongoDB
    try:
        client = MongoClient(settings.mongodb_uri)
        # Test connection
        client.admin.command('ping')
        logger.info(f"✅ Connected to MongoDB cluster successfully")
        
        db = client[settings.mongodb_db]
        logger.info(f"✅ Using database: {settings.mongodb_db}")
        
    except ConnectionFailure as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        return False
    
    collections_config = {
        'documents': {
            'description': 'Patient documents and processing status',
            'indexes': [
                IndexModel([('patient_id', 1)]),
                IndexModel([('uuid', 1)], unique=True),
                IndexModel([('filename', 1), ('patient_id', 1)]),
                IndexModel([('upload_timestamp', -1)]),
                IndexModel([('status', 1)]),
                IndexModel([('is_latest', 1)])
            ]
        },
        'reports': {
            'description': 'Generated MDT reports',
            'indexes': [
                IndexModel([('uuid', 1)], unique=True),
                IndexModel([('patient_id', 1)]),
                IndexModel([('created_at', -1)]),
                IndexModel([('status', 1)]),
                IndexModel([('title', 1)])
            ]
        },
        'generations': {
            'description': 'Processing logs and observability data',
            'indexes': [
                IndexModel([('timestamp', -1)]),
                IndexModel([('patient_id', 1)]),
                IndexModel([('generation_type', 1)]),
                IndexModel([('report_uuid', 1)])
            ]
        },
        'entity_templates': {
            'description': 'NER entity definitions and templates',
            'indexes': [
                IndexModel([('template_id', 1)], unique=True),
                IndexModel([('is_active', 1)]),
                IndexModel([('created_at', -1)])
            ]
        },
        'users': {
            'description': 'User accounts (if authentication enabled)',
            'indexes': [
                IndexModel([('email', 1)], unique=True),
                IndexModel([('username', 1)], unique=True),
                IndexModel([('created_at', -1)])
            ]
        },
        'blacklisted_tokens': {
            'description': 'Security token management',
            'indexes': [
                IndexModel([('token_hash', 1)], unique=True),
                IndexModel([('expires_at', 1)], expireAfterSeconds=0)
            ]
        }
    }
    
    # Create collections and indexes
    created_collections = []
    for collection_name, config in collections_config.items():
        try:
            # Check if collection exists
            if collection_name in db.list_collection_names():
                logger.info(f"📁 Collection '{collection_name}' already exists")
            else:
                # Create collection
                db.create_collection(collection_name)
                logger.info(f"✅ Created collection: {collection_name}")
                
            created_collections.append(collection_name)
            
            # Create indexes
            collection = db[collection_name]
            if config['indexes']:
                try:
                    result = collection.create_indexes(config['indexes'])
                    logger.info(f"📝 Created {len(result)} indexes for {collection_name}")
                except Exception as e:
                    logger.warning(f"⚠️  Some indexes for {collection_name} may already exist: {e}")
                    
        except CollectionInvalid:
            logger.info(f"📁 Collection '{collection_name}' already exists")
        except Exception as e:
            logger.error(f"❌ Error creating collection {collection_name}: {e}")
            return False
    
    # Add initial entity template
    add_default_template(db)
    
    client.close()
    logger.info(f"🎉 MongoDB setup complete! Created/verified {len(created_collections)} collections")
    return True

def add_default_template(db):
    """Add default entity template if none exists"""
    templates_collection = db['entity_templates']
    
    if templates_collection.count_documents({}) == 0:
        logger.info("📝 Adding default entity template...")
        
        # Load default template from file
        template_file = os.path.join(os.path.dirname(__file__), 'templates', 'new_entities_no_filter_template.json')
        
        if os.path.exists(template_file):
            import json
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # Add metadata
            template_doc = {
                'template_id': f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'name': 'Default ClarityGR Template',
                'description': 'Default entity extraction template for medical documents',
                'is_active': True,
                'created_at': datetime.utcnow(),
                'template_data': template_data
            }
            
            result = templates_collection.insert_one(template_doc)
            logger.info(f"✅ Added default template with ID: {template_doc['template_id']}")
        else:
            logger.warning(f"⚠️  Template file not found: {template_file}")
    else:
        logger.info("📋 Entity templates already exist, skipping default template creation")

if __name__ == "__main__":
    print("🔧 Setting up MongoDB cluster for ClarityGR...")
    # print(f"📍 Target database: {settings.mongodb_db}")
    # print(f"🔗 MongoDB URI: {settings.mongodb_uri[:50]}...")
    print()
    
    success = create_collections_and_indexes()
    
    if success:
        print()
        print("🎉 MongoDB cluster setup completed successfully!")
        print("💡 Next steps:")
        print("   1. Install Python dependencies: pip install -r backend/requirements.txt")
        print("   2. Start backend: cd backend && python main.py")
        print("   3. Install frontend deps: cd frontend && npm install")
        print("   4. Start frontend: cd frontend && npm run dev")
    else:
        print("❌ MongoDB setup failed. Please check your connection string and try again.")
        sys.exit(1)