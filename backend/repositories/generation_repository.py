from typing import Optional, List, Dict, Any
from pymongo.collection import Collection
from config.database import MongoDBConnection
from domain.entities.generation import GenerationLog
from utils.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class GenerationRepository:
    """Repository for writing generation logs to MongoDB."""

    def __init__(self):
        self.collection_name = "generations"

    def create(self, generation: GenerationLog) -> GenerationLog:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                collection.insert_one(generation.model_dump())
                logger.info(f"Created generation log with uuid: {generation.uuid} for patient: {generation.patient_id}")
                return generation
        except Exception as e:
            logger.error(f"Database error creating generation log {generation.uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: int = 1000, sort_desc: bool = True) -> List[GenerationLog]:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                query = filters or {}
                cursor = collection.find(query).limit(limit)
                sort_field = "timestamp_utc"
                cursor = cursor.sort(sort_field, -1 if sort_desc else 1)
                docs = [GenerationLog(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(docs)} generation logs")
                return docs
        except Exception as e:
            logger.error(f"Database error listing generation logs: {e}")
            raise DatabaseException(f"Database error: {e}")

    def distinct_values(self, field_name: str) -> List[Any]:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                values = collection.distinct(field_name)
                return [v for v in values if v is not None]
        except Exception as e:
            logger.error(f"Database error getting distinct values for {field_name}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def update(self, uuid: str, update_data: Dict[str, Any]) -> bool:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.update_one({"uuid": uuid}, {"$set": update_data})
                return result.matched_count > 0
        except Exception as e:
            logger.error(f"Database error updating generation {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_report_uuid(self, report_uuid: str) -> int:
        """Delete all generations that contain a specific report UUID. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                # The report.uuid is nested inside the report dict
                result = collection.delete_many({"report.uuid": report_uuid})
                logger.info(f"Deleted {result.deleted_count} generations for report {report_uuid}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting generations for report {report_uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_patient_id(self, patient_id: str) -> int:
        """Delete all generations for a specific patient. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"patient_id": patient_id})
                logger.info(f"Deleted {result.deleted_count} generations for patient {patient_id}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting generations for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")


