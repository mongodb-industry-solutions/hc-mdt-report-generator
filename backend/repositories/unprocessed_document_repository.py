"""
Unprocessed Document Repository

Handles MongoDB operations for the unprocessed_documents collection.
These documents are pre-populated by external EHR systems.
"""

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from config.database import MongoDBConnection
from domain.entities.unprocessed_document import UnprocessedDocument
from utils.exceptions import NotFoundException, DatabaseException
import logging

logger = logging.getLogger(__name__)


class UnprocessedDocumentRepository:
    """
    Repository for accessing unprocessed documents in MongoDB.
    
    Collection: unprocessed_documents
    Source: External EHR systems
    """
    
    def __init__(self):
        self.collection_name = "unprocessed_documents"
    
    def get_by_id(self, doc_id: str) -> UnprocessedDocument:
        """Get unprocessed document by its EHR ID (_id)"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"_id": doc_id})
                if not doc:
                    raise NotFoundException(f"Unprocessed document with id {doc_id} not found.")
                logger.info(f"Retrieved unprocessed document with id: {doc_id}")
                return UnprocessedDocument(**doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error retrieving unprocessed document {doc_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_patient_id(
        self, 
        patient_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[UnprocessedDocument]:
        """Get unprocessed documents for a specific patient with pagination"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({"patient_id": patient_id}).skip(skip).limit(limit)
                documents = [UnprocessedDocument(**doc) for doc in cursor]
                logger.info(f"Retrieved {len(documents)} unprocessed documents for patient {patient_id}")
                return documents
        except Exception as e:
            logger.error(f"Database error retrieving unprocessed documents for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def count_by_patient_id(self, patient_id: str) -> int:
        """Count unprocessed documents for a specific patient"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                count = collection.count_documents({"patient_id": patient_id})
                logger.info(f"Counted {count} unprocessed documents for patient {patient_id}")
                return count
        except Exception as e:
            logger.error(f"Database error counting unprocessed documents for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_all_patient_ids(self) -> List[str]:
        """Get distinct patient IDs that have unprocessed documents"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                patient_ids = collection.distinct("patient_id")
                logger.info(f"Found {len(patient_ids)} patients with unprocessed documents")
                return patient_ids
        except Exception as e:
            logger.error(f"Database error getting patient IDs: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_counts_by_patient(self) -> Dict[str, int]:
        """Get document counts grouped by patient ID"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                pipeline = [
                    {"$group": {"_id": "$patient_id", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                results = list(collection.aggregate(pipeline))
                counts = {item["_id"]: item["count"] for item in results}
                logger.info(f"Retrieved document counts for {len(counts)} patients")
                return counts
        except Exception as e:
            logger.error(f"Database error getting patient document counts: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_many_by_ids(self, doc_ids: List[str]) -> List[UnprocessedDocument]:
        """Get multiple unprocessed documents by their IDs"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({"_id": {"$in": doc_ids}})
                documents = [UnprocessedDocument(**doc) for doc in cursor]
                logger.info(f"Retrieved {len(documents)} unprocessed documents by IDs")
                return documents
        except Exception as e:
            logger.error(f"Database error retrieving documents by IDs: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_id(self, doc_id: str) -> bool:
        """Delete an unprocessed document by ID (after processing)"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_one({"_id": doc_id})
                if result.deleted_count == 0:
                    logger.warning(f"No unprocessed document found to delete with id: {doc_id}")
                    return False
                logger.info(f"Deleted unprocessed document with id: {doc_id}")
                return True
        except Exception as e:
            logger.error(f"Database error deleting unprocessed document {doc_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_many_by_ids(self, doc_ids: List[str]) -> int:
        """Delete multiple unprocessed documents by IDs (after batch processing)"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"_id": {"$in": doc_ids}})
                logger.info(f"Deleted {result.deleted_count} unprocessed documents")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting documents by IDs: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def exists(self, doc_id: str) -> bool:
        """Check if an unprocessed document exists"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                count = collection.count_documents({"_id": doc_id}, limit=1)
                return count > 0
        except Exception as e:
            logger.error(f"Database error checking document existence {doc_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_total_count(self) -> int:
        """Get total count of all unprocessed documents"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                count = collection.count_documents({})
                logger.info(f"Total unprocessed documents: {count}")
                return count
        except Exception as e:
            logger.error(f"Database error counting all documents: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def search_by_filename(
        self, 
        patient_id: str, 
        filename_pattern: str, 
        limit: int = 20
    ) -> List[UnprocessedDocument]:
        """Search unprocessed documents by filename pattern (regex)"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({
                    "patient_id": patient_id,
                    "file_name": {"$regex": filename_pattern, "$options": "i"}
                }).limit(limit)
                documents = [UnprocessedDocument(**doc) for doc in cursor]
                logger.info(f"Found {len(documents)} documents matching pattern '{filename_pattern}'")
                return documents
        except Exception as e:
            logger.error(f"Database error searching by filename: {e}")
            raise DatabaseException(f"Database error: {e}")
