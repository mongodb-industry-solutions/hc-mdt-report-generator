from typing import List, Optional
from pymongo.collection import Collection
from config.database import MongoDBConnection
from domain.entities.patient_document import PatientDocument
from utils.exceptions import NotFoundException, DatabaseException
import logging

logger = logging.getLogger(__name__)

class PatientDocumentRepository:
    """
    Repository for accessing patient documents in MongoDB.
    """
    def __init__(self):
        self.collection_name = "documents"

    def get_by_uuid(self, uuid: str) -> PatientDocument:
        """Get patient document by UUID"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"uuid": uuid})
                if not doc:
                    raise NotFoundException(f"Patient document with uuid {uuid} not found.")
                # logger.info(f"Retrieved patient document with uuid: {uuid}")
                return PatientDocument(**doc)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error retrieving patient document {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def get_by_patient_id(self, patient_id: str, skip: int = 0, limit: int = 10) -> List[PatientDocument]:
        """Get patient documents by patient ID with pagination"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({"patient_id": patient_id}).skip(skip).limit(limit)
                documents = [PatientDocument(**doc) for doc in cursor]
                logger.info(f"Retrieved {len(documents)} patient documents for patient {patient_id}")
                return documents
        except Exception as e:
            logger.error(f"Database error retrieving patient documents for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def count_by_patient_id(self, patient_id: str) -> int:
        """Count patient documents by patient ID"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                count = collection.count_documents({"patient_id": patient_id})
                logger.info(f"Counted {count} patient documents for patient {patient_id}")
                return count
        except Exception as e:
            logger.error(f"Database error counting patient documents for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def create(self, document: PatientDocument) -> PatientDocument:
        """Create a new patient document"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                collection.insert_one(document.model_dump())
                logger.info(f"Created patient document with uuid: {document.uuid}")
                return document
        except Exception as e:
            logger.error(f"Database error creating patient document {document.uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def find_existing_document(self, patient_id: str, filename: str) -> Optional[PatientDocument]:
        """Find an existing document with the same patient_id and filename"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"patient_id": patient_id, "filename": filename})
                if doc:
                    logger.info(f"Found existing document with filename: {filename} for patient: {patient_id}")
                    return PatientDocument(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error finding existing document for patient {patient_id} with filename {filename}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def get_by_filename(self, patient_id: str, filename: str) -> Optional[PatientDocument]:
        """Get patient document by filename for a specific patient"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                doc = collection.find_one({"patient_id": patient_id, "filename": filename})
                if doc:
                    # logger.info(f"Retrieved document with filename: {filename} for patient: {patient_id}")
                    return PatientDocument(**doc)
                return None
        except Exception as e:
            logger.error(f"Database error retrieving document by filename {filename} for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def replace_document_content(self, uuid: str, new_content: dict) -> PatientDocument:
        """Replace an existing document's content while preserving its UUID and created_at"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                
                # Preserve certain fields from the original document
                original_doc = collection.find_one({"uuid": uuid})
                if not original_doc:
                    raise NotFoundException(f"Patient document with uuid {uuid} not found.")
                
                # Prepare update data - preserve UUID, created_at, but reset processing fields
                update_data = {
                    **new_content,
                    "uuid": uuid,  # Keep original UUID
                    "created_at": original_doc["created_at"],  # Keep original creation time
                    "updated_at": new_content.get("updated_at"),  # Use new update time
                    # Reset processing fields for reprocessing
                    "status": new_content.get("status", "queued"),
                    "processing_started_at": None,
                    "processing_completed_at": None,
                    "errors": [],
                    "parsed_document_uuid": None,
                    "document_category": None,
                    "document_type": None,
                    "categorization_completed_at": None,
                    "extracted_data": None,
                    "extraction_metadata": None,
                    "extraction_status": None,
                    "extraction_completed_at": None,
                    "ocr_text": None,
                    "ocr_metadata": None,
                    "ocr_completed_at": None,
                    "character_count": None,
                    "word_count": None
                }
                
                # Replace the entire document
                result = collection.replace_one(
                    {"uuid": uuid},
                    update_data
                )
                
                if result.matched_count == 0:
                    raise NotFoundException(f"Patient document with uuid {uuid} not found.")
                
                logger.info(f"Replaced content for patient document with uuid: {uuid}")
                return self.get_by_uuid(uuid)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error replacing document content {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def update(self, uuid: str, update_data: dict) -> PatientDocument:
        """Update a patient document"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.update_one(
                    {"uuid": uuid},
                    {"$set": update_data}
                )
                if result.matched_count == 0:
                    raise NotFoundException(f"Patient document with uuid {uuid} not found.")
                logger.info(f"Updated patient document with uuid: {uuid}")
                return self.get_by_uuid(uuid)
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error updating patient document {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def delete_by_uuid(self, uuid: str) -> None:
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.delete_one({"uuid": uuid})
                if result.deleted_count == 0:
                    raise NotFoundException(f"Patient document with uuid {uuid} not found.")
                logger.info(f"Deleted patient document with uuid: {uuid}")
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error deleting patient document {uuid}: {e}")
            raise DatabaseException(f"Database error: {e}")

    def update_many(self, filter_query: dict, update_data: dict) -> int:
        """Update multiple documents matching the filter"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                result = collection.update_many(
                    filter_query,
                    {"$set": update_data}
                )
                logger.info(f"Updated {result.modified_count} documents matching filter")
                return result.modified_count
        except Exception as e:
            logger.error(f"Database error updating multiple documents: {e}")
            raise DatabaseException(f"Database error: {e}")

    def find_by_patient_id_all(self, patient_id: str) -> List[PatientDocument]:
        """Get all documents for a patient (no pagination)"""
        try:
            with MongoDBConnection() as db:
                collection: Collection = db[self.collection_name]
                cursor = collection.find({"patient_id": patient_id})
                documents = [PatientDocument(**doc) for doc in cursor]
                # logger.info(f"Retrieved {len(documents)} documents for patient {patient_id}")
                return documents
        except Exception as e:
            logger.error(f"Database error retrieving all documents for patient {patient_id}: {e}")
            raise DatabaseException(f"Database error: {e}")
