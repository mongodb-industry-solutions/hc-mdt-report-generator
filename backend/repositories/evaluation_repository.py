"""
Evaluation Repository - CRUD operations for evaluations collection.

Uses timestamps (created_at) for finding latest records instead of is_latest flag.
This approach is more scalable for bulk processing.
"""

from typing import List, Optional
from pymongo.collection import Collection
from pymongo import DESCENDING
from config.database import MongoDBConnection
from domain.entities.evaluation import Evaluation
from utils.exceptions import NotFoundException, DatabaseException
import logging

logger = logging.getLogger(__name__)


class EvaluationRepository:
    """
    Repository for accessing evaluations in MongoDB.
    Collection: evaluations
    """
    
    def __init__(self):
        self.collection_name = "evaluations"
    
    def _ensure_indexes(self, collection: Collection) -> None:
        """Create indexes for efficient queries."""
        # Index for finding evaluations by patient_id (sorted by created_at for latest)
        collection.create_index([("patient_id", 1), ("created_at", -1)])
        # Index for finding evaluations by report_uuid
        collection.create_index([("report_uuid", 1), ("created_at", -1)])
        # Index for finding evaluations by ground_truth_uuid
        collection.create_index([("ground_truth_uuid", 1)])
        # Index for finding evaluation by uuid
        collection.create_index("uuid", unique=True)
    
    def get_by_uuid(self, uuid: str) -> Evaluation:
        """Get an evaluation by its UUID."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"uuid": uuid})
                if not doc:
                    raise NotFoundException(f"Evaluation with uuid {uuid} not found.")
                # logger.info(f"Retrieved evaluation with uuid: {uuid}")
                return Evaluation(**doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error retrieving evaluation {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_latest_by_patient(self, patient_id: str) -> Optional[Evaluation]:
        """Get the most recent evaluation for a patient."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one(
                    {"patient_id": patient_id, "status": "COMPLETED"},
                    sort=[("created_at", DESCENDING)]
                )
                if doc:
                    # logger.info(f"Retrieved latest evaluation for patient {patient_id}")
                    return Evaluation(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error getting latest eval for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_latest_by_report(self, report_uuid: str) -> Optional[Evaluation]:
        """Get the most recent evaluation for a specific report."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one(
                    {"report_uuid": report_uuid},
                    sort=[("created_at", DESCENDING)]
                )
                if doc:
                    # logger.info(f"Retrieved latest evaluation for report {report_uuid}")
                    return Evaluation(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error getting latest eval for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_patient(self, patient_id: str, limit: int = 50) -> List[Evaluation]:
        """Get all evaluations for a patient, sorted by created_at (newest first)."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find(
                    {"patient_id": patient_id}
                ).sort("created_at", DESCENDING).limit(limit)
                evaluations = [Evaluation(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(evaluations)} evaluations for patient {patient_id}")
                return evaluations
        except Exception as e:
            logger.error(f"Database error retrieving evals for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_report(self, report_uuid: str, limit: int = 50) -> List[Evaluation]:
        """Get all evaluations for a report, sorted by created_at (newest first)."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find(
                    {"report_uuid": report_uuid}
                ).sort("created_at", DESCENDING).limit(limit)
                evaluations = [Evaluation(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(evaluations)} evaluations for report {report_uuid}")
                return evaluations
        except Exception as e:
            logger.error(f"Database error retrieving evals for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_by_ground_truth(self, ground_truth_uuid: str) -> List[Evaluation]:
        """Get all evaluations that used a specific ground truth."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find(
                    {"ground_truth_uuid": ground_truth_uuid}
                ).sort("created_at", DESCENDING)
                evaluations = [Evaluation(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(evaluations)} evaluations for GT {ground_truth_uuid}")
                return evaluations
        except Exception as e:
            logger.error(f"Database error retrieving evals for GT {ground_truth_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def create(self, evaluation: Evaluation) -> Evaluation:
        """Create a new evaluation record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                self._ensure_indexes(collection)
                collection.insert_one(evaluation.model_dump())
                logger.info(f"Created evaluation {evaluation.uuid} for report {evaluation.report_uuid}")
                return evaluation
        except Exception as e:
            logger.error(f"Database error creating evaluation: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def update(self, uuid: str, update_data: dict) -> Evaluation:
        """Update an evaluation record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                
                existing_doc = collection.find_one({"uuid": uuid})
                if not existing_doc:
                    raise NotFoundException(f"Evaluation with uuid {uuid} not found.")
                
                collection.update_one(
                    {"uuid": uuid},
                    {"$set": update_data}
                )
                
                updated_doc = collection.find_one({"uuid": uuid})
                logger.info(f"Updated evaluation {uuid}")
                return Evaluation(**updated_doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error updating evaluation {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete(self, uuid: str) -> bool:
        """Delete an evaluation record."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_one({"uuid": uuid})
                if result.deleted_count == 0:
                    raise NotFoundException(f"Evaluation with uuid {uuid} not found.")
                logger.info(f"Deleted evaluation {uuid}")
                return True
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error deleting evaluation {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_report_uuid(self, report_uuid: str) -> int:
        """Delete all evaluations for a specific report. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"report_uuid": report_uuid})
                logger.info(f"Deleted {result.deleted_count} evaluations for report {report_uuid}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting evaluations for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_patient_id(self, patient_id: str) -> int:
        """Delete all evaluations for a specific patient. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"patient_id": patient_id})
                logger.info(f"Deleted {result.deleted_count} evaluations for patient {patient_id}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting evaluations for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")


