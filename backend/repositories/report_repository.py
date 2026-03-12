from typing import List, Optional
from pymongo.collection import Collection
from config.database import MongoDBConnection
from domain.entities.report import Report
from utils.exceptions import NotFoundException, DatabaseException
import logging

logger = logging.getLogger(__name__)

class ReportRepository:
    """
    Repository for accessing reports in MongoDB.
    """
    def __init__(self):
        self.collection_name = "reports"

    def get_by_uuid(self, uuid: str) -> Report:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"uuid": uuid})
                if not doc:
                    raise NotFoundException(f"Report with uuid {uuid} not found.")
                # logger.info(f"Retrieved report with uuid: {uuid}")
                return Report(**doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error retrieving report {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def get_by_patient_id(self, patient_id: str, skip: int = 0, limit: int = 10) -> List[Report]:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                # Sort by created_at descending so newest reports appear first
                cursor = collection.find({"patient_id": patient_id}).sort("created_at", -1).skip(skip).limit(limit)
                reports = [Report(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(reports)} reports for patient {patient_id}")
                return reports
        except Exception as e:
            logger.error(f"Database error retrieving reports for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def create(self, report: Report) -> Report:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                collection.insert_one(report.model_dump())
                logger.info(f"Created report with uuid: {report.uuid} for patient: {report.patient_id}")
                return report
        except Exception as e:
            logger.error(f"Database error creating report {report.uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def update(self, uuid: str, update_data: dict) -> Report:
        """
        Update a report with new data.
        
        Args:
            uuid: The report UUID to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated Report object
        """
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                
                # Ensure the report exists
                existing_doc = collection.find_one({"uuid": uuid})
                if not existing_doc:
                    raise NotFoundException(f"Report with uuid {uuid} not found.")
                
                # Perform the update
                result = collection.update_one(
                    {"uuid": uuid},
                    {"$set": update_data}
                )
                
                if result.matched_count == 0:
                    raise NotFoundException(f"Report with uuid {uuid} not found.")
                
                # Retrieve and return the updated document
                updated_doc = collection.find_one({"uuid": uuid})
                logger.info(f"Updated report with uuid: {uuid}")
                return Report(**updated_doc)
                
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error updating report {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}") 

    def delete_by_uuid(self, uuid: str) -> None:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_one({"uuid": uuid})
                if result.deleted_count == 0:
                    raise NotFoundException(f"Report with uuid {uuid} not found.")
                logger.info(f"Deleted report with uuid: {uuid}")
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error deleting report {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def delete_by_patient_id(self, patient_id: str) -> int:
        """Delete all reports for a specific patient. Returns count of deleted records."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_many({"patient_id": patient_id})
                logger.info(f"Deleted {result.deleted_count} reports for patient {patient_id}")
                return result.deleted_count
        except Exception as e:
            logger.error(f"Database error deleting reports for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
    
    def get_all_uuids_by_patient_id(self, patient_id: str) -> List[str]:
        """Get all report UUIDs for a patient (for cascading deletes)."""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({"patient_id": patient_id}, {"uuid": 1})
                return [doc["uuid"] for doc in cursor]
        except Exception as e:
            logger.error(f"Database error getting report UUIDs for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")