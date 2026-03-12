"""
Ground Truth Repository - CRUD operations for ground_truths collection.

Uses timestamps (created_at) for finding latest records instead of is_latest flag.
This approach is more scalable for bulk processing.
"""

from typing import List, Optional
from pymongo.collection import Collection
from pymongo import DESCENDING
from config.database import MongoDBConnection
from domain.entities.ground_truth import GroundTruth
from utils.exceptions import NotFoundException, DatabaseException
import logging

logger = logging.getLogger(__name__)


class GroundTruthRepository:
    """
    Repository for accessing ground truths in MongoDB.
    Collection: ground_truths
    """
    
    def __init__(self):
        self.collection_name = "ground_truths"
    
    def _ensure_indexes(self, collection: Collection) -> None:
        """Create indexes for efficient queries."""
        # Index for finding GT by patient_id (sorted by created_at for latest)
        collection.create_index([("patient_id", 1), ("created_at", -1)])
        # Index for finding GT by report_uuid
        collection.create_index([("report_uuid", 1), ("created_at", -1)])
        # Index for finding GT by uuid
        collection.create_index("uuid", unique=True)
    
    def get_by_uuid(self, uuid: str) -> GroundTruth:
        """Get a ground truth by its UUID."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"uuid": uuid})
                if not doc:
                    raise NotFoundException(f"GroundTruth with uuid {uuid} not found.")
                # logger.info(f"Retrieved ground truth with uuid: {uuid}")
                return GroundTruth(**doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error retrieving ground truth {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_latest_by_patient(self, patient_id: str) -> Optional[GroundTruth]:
        """Get the most recent ground truth for a patient."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one(
                    {"patient_id": patient_id},
                    sort=[("created_at", DESCENDING)]
                )
                if doc:
                    # logger.info(f"Retrieved latest ground truth for patient {patient_id}")
                    return GroundTruth(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error getting latest GT for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_latest_by_report(self, report_uuid: str) -> Optional[GroundTruth]:
        """Get the most recent ground truth for a specific report."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one(
                    {"report_uuid": report_uuid},
                    sort=[("created_at", DESCENDING)]
                )
                if doc:
                    # logger.info(f"Retrieved latest ground truth for report {report_uuid}")
                    return GroundTruth(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error getting latest GT for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_patient(self, patient_id: str, limit: int = 50) -> List[GroundTruth]:
        """Get all ground truths for a patient, sorted by created_at (newest first)."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find(
                    {"patient_id": patient_id}
                ).sort("created_at", DESCENDING).limit(limit)
                ground_truths = [GroundTruth(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(ground_truths)} ground truths for patient {patient_id}")
                return ground_truths
        except Exception as e:
            logger.error(f"Database error retrieving GTs for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_report(self, report_uuid: str, limit: int = 50) -> List[GroundTruth]:
        """Get all ground truths for a report, sorted by created_at (newest first)."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find(
                    {"report_uuid": report_uuid}
                ).sort("created_at", DESCENDING).limit(limit)
                ground_truths = [GroundTruth(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(ground_truths)} ground truths for report {report_uuid}")
                return ground_truths
        except Exception as e:
            logger.error(f"Database error retrieving GTs for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def create(self, ground_truth: GroundTruth) -> GroundTruth:
        """Create a new ground truth record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                self._ensure_indexes(collection)
                collection.insert_one(ground_truth.model_dump())
                logger.info(f"Created ground truth {ground_truth.uuid} for report {ground_truth.report_uuid}")
                return ground_truth
        except Exception as e:
            logger.error(f"Database error creating ground truth: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def update(self, uuid: str, update_data: dict) -> GroundTruth:
        """Update a ground truth record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                
                existing_doc = collection.find_one({"uuid": uuid})
                if not existing_doc:
                    raise NotFoundException(f"GroundTruth with uuid {uuid} not found.")
                
                collection.update_one(
                    {"uuid": uuid},
                    {"$set": update_data}
                )
                
                updated_doc = collection.find_one({"uuid": uuid})
                logger.info(f"Updated ground truth {uuid}")
                return GroundTruth(**updated_doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error updating ground truth {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete(self, uuid: str) -> bool:
        """Delete a ground truth record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_one({"uuid": uuid})
                if result.deleted_count == 0:
                    raise NotFoundException(f"GroundTruth with uuid {uuid} not found.")
                logger.info(f"Deleted ground truth {uuid}")
                return True
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error deleting ground truth {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_report_uuid(self, report_uuid: str) -> int:
        """Delete all ground truths for a specific report. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"report_uuid": report_uuid})
                logger.info(f"Deleted {result.deleted_count} ground truths for report {report_uuid}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting ground truths for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_patient_id(self, patient_id: str) -> int:
        """Delete all ground truths for a specific patient. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"patient_id": patient_id})
                logger.info(f"Deleted {result.deleted_count} ground truths for patient {patient_id}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting ground truths for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")


