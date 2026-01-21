# src/config/database.py - Singleton connection pool pattern
import os
from typing import Any, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
from config.settings import settings
import logging
import urllib.parse

load_dotenv()

logger = logging.getLogger(__name__)

# ===== SINGLETON CONNECTION POOL =====
_mongo_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_database() -> Database:
    """Get a database instance using connection pooling (singleton).
    
    This function reuses a single MongoClient instance across all calls,
    avoiding the overhead of creating new connections for every request.
    """
    global _mongo_client, _database
    
    # Return cached connection if available
    if _database is not None:
        try:
            # Quick ping to verify connection is still alive
            _database.command('ping')
            return _database
        except Exception:
            # Connection lost, reset and reconnect
            logger.warning("MongoDB connection lost, reconnecting...")
            _mongo_client = None
            _database = None
    
    uri = os.getenv("MONGODB_URI", settings.mongodb_uri)
    db_name = os.getenv("MONGODB_DB", settings.mongodb_db)
    
    logger.info(f"Connecting to MongoDB: {uri}/{db_name}")
    
    try:
        _mongo_client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            maxPoolSize=10,        # Connection pool size
            minPoolSize=2,         # Keep 2 connections warm
            maxIdleTimeMS=30000,   # Close idle connections after 30s
            retryWrites=True
        )
        
        _database = _mongo_client[db_name]
        
        # Test connection once
        _database.command('ping')
        logger.info(f"✅ MongoDB connected: {db_name} (pooled)")
        
        return _database
        
    except ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server timeout: {e}")
        raise ConnectionFailure(f"Unable to connect to MongoDB server: {e}")
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected MongoDB connection error: {e}")
        raise ConnectionFailure(f"MongoDB connection error: {e}")


class MongoDBConnection:
    """Context manager for backward compatibility.
    
    This now uses the singleton connection pool instead of creating
    new connections each time.
    """
    def __init__(self, uri: str = None, db_name: str = None):
        # Just use the singleton - parameters are ignored for compatibility
        pass

    def __enter__(self) -> Database:
        return get_database()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Don't close - keep connection pooled
        pass


def test_connection() -> bool:
    """Test the MongoDB connection."""
    try:
        db = get_database()
        result = db.command('ping')
        logger.info(f"MongoDB connection test successful: {result}")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {e}")
        return False


def create_indexes() -> bool:
    """Create indexes on the database."""
    try:
        db = get_database()
        
        # Create users collection indexes for authentication
        if 'users' not in db.list_collection_names():
            db.create_collection('users')
        
        users_collection = db['users']
        
        # Username unique index
        users_collection.create_index(
            [("username", 1)],
            unique=True,
            background=True,
            name="username_unique_idx"
        )
        
        # Email unique index
        users_collection.create_index(
            [("email", 1)],
            unique=True,
            background=True,
            name="email_unique_idx"
        )
        
        # Additional indexes for patient documents
        if 'documents' not in db.list_collection_names():
            db.create_collection('documents')
        
        documents_collection = db['documents']
        
        # Patient ID index for fast queries
        documents_collection.create_index(
            [("patient_id", 1)],
            background=True,
            name="patient_id_idx"
        )
        
        # UUID unique index
        documents_collection.create_index(
            [("uuid", 1)],
            unique=True,
            background=True,
            name="uuid_unique_idx"
        )
        
        # Filename + patient_id index for duplicate checking
        documents_collection.create_index(
            [("patient_id", 1), ("filename", 1)],
            background=True,
            name="patient_filename_idx"
        )
        
        # Additional indexes for reports
        if 'reports' not in db.list_collection_names():
            db.create_collection('reports')
        
        reports_collection = db['reports']
        
        # Patient ID index
        reports_collection.create_index(
            [("patient_id", 1)],
            background=True,
            name="patient_id_idx"
        )
        
        # UUID unique index
        reports_collection.create_index(
            [("uuid", 1)],
            unique=True,
            background=True,
            name="uuid_unique_idx"
        )

        # Additional indexes for generations (Generations collection)
        if 'generations' not in db.list_collection_names():
            db.create_collection('generations')

        generations_collection = db['generations']

        # Patient ID index
        generations_collection.create_index(
            [("patient_id", 1)],
            background=True,
            name="patient_id_idx"
        )

        # Timestamp index for sorting
        generations_collection.create_index(
            [("timestamp_utc", 1)],
            background=True,
            name="timestamp_idx"
        )

        # UUID unique index
        generations_collection.create_index(
            [("uuid", 1)],
            unique=True,
            background=True,
            name="uuid_unique_idx"
        )
        
        logger.info("Database indexes creation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")
        return False
