#!/usr/bin/env python3
"""
Verify Jane Doe's documents in the database.
This script checks that all documents are properly stored and processed.
"""

import requests
import json
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://localhost:8000"
PATIENT_ID = "jane-doe"

def get_all_patient_documents() -> List[Dict[str, Any]]:
    """Get all documents for Jane Doe"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/documents")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
        return []

def get_document_details(document_uuid: str) -> Dict[str, Any]:
    """Get detailed information about a specific document"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}")
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"❌ Error getting document details: {e}")
        return {}

def get_document_ocr(document_uuid: str) -> Dict[str, Any]:
    """Get OCR results for a document"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}/ocr")
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"❌ Error getting OCR results: {e}")
        return {}

def get_document_normalization(document_uuid: str) -> Dict[str, Any]:
    """Get normalization results for a document"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}/")
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"❌ Error getting normalization results: {e}")
        return {}

def analyze_medical_entities(document_uuid: str) -> List[Dict[str, Any]]:
    """Analyze medical entities in a document"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}/entities")
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"❌ Error getting entities: {e}")
        return []

def print_document_summary(doc: Dict[str, Any]):
    """Print a summary of a document"""
    print(f"\n📄 Document: {doc.get('filename', 'Unknown')}")
    print(f"   UUID: {doc.get('uuid', 'Unknown')}")
    print(f"   Type: {doc.get('type', 'Unknown')}")
    print(f"   Status: {doc.get('status', 'Unknown')}")
    print(f"   Created: {doc.get('created_at', 'Unknown')}")
    print(f"   Updated: {doc.get('updated_at', 'Unknown')}")

def print_processing_details(document_uuid: str):
    """Print detailed processing information for a document"""
    print(f"\n🔍 Processing Details for {document_uuid}")
    print("-" * 50)
    
    # Get document details
    details = get_document_details(document_uuid)
    if details:
        print(f"📋 Basic Info:")
        print(f"   Patient ID: {details.get('patient_id', 'N/A')}")
        print(f"   Source: {details.get('source', 'N/A')}")
        print(f"   Notes: {details.get('notes', 'N/A')}")
    
    # Get OCR results
    ocr_data = get_document_ocr(document_uuid)
    if ocr_data:
        print(f"\n📝 OCR Results:")
        print(f"   Character Count: {ocr_data.get('character_count', 'N/A')}")
        print(f"   Word Count: {ocr_data.get('word_count', 'N/A')}")
        print(f"   Processing Time: {ocr_data.get('processing_time', 'N/A')}s")
    
    # Get normalization results
    norm_data = get_document_normalization(document_uuid)
    if norm_data:
        print(f"\n🔄 Normalization Results:")
        print(f"   Status: {norm_data.get('normalization_status', 'N/A')}")
        print(f"   Original Chars: {norm_data.get('original_character_count', 'N/A')}")
        print(f"   Normalized Chars: {norm_data.get('normalized_character_count', 'N/A')}")
        print(f"   Processing Time: {norm_data.get('normalization_processing_time', 'N/A')}s")
    
    # Get medical entities
    entities = analyze_medical_entities(document_uuid)
    if entities:
        print(f"\n🏥 Medical Entities ({len(entities)} found):")
        for entity in entities[:10]:  # Show first 10 entities
            print(f"   • {entity.get('entity_type', 'Unknown')}: {entity.get('text', 'Unknown')}")
        if len(entities) > 10:
            print(f"   ... and {len(entities) - 10} more entities")

def verify_jane_doe_database():
    """Verify Jane Doe's complete database"""
    print("🔍 Verifying Jane Doe's medical database")
    print("=" * 60)
    
    # Get all documents
    response = get_all_patient_documents()
    if not response:
        print("❌ No documents found for Jane Doe")
        return
    documents = response["items"] if isinstance(response, dict) and "items" in response else response
    print(f"📊 Found {len(documents)} documents for Jane Doe")
    # Sort documents by creation date
    documents = list(documents)
    documents.sort(key=lambda x: x.get('created_at', ''))
    
    # Print summary for each document
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. ", end="")
        print_document_summary(doc)
    
    # Detailed analysis of each document
    print(f"\n🔬 DETAILED ANALYSIS")
    print("=" * 60)
    
    total_entities = 0
    total_ocr_chars = 0
    total_norm_chars = 0
    
    for doc in documents:
        document_uuid = doc.get('uuid')
        if document_uuid:
            print_processing_details(document_uuid)
            
            # Collect statistics
            ocr_data = get_document_ocr(document_uuid)
            norm_data = get_document_normalization(document_uuid)
            entities = analyze_medical_entities(document_uuid)
            
            total_ocr_chars += ocr_data.get('character_count', 0)
            total_norm_chars += norm_data.get('normalized_character_count', 0)
            total_entities += len(entities)
    
    # Final statistics
    print(f"\n📈 DATABASE STATISTICS")
    print("=" * 60)
    print(f"Total Documents: {len(documents)}")
    print(f"Total OCR Characters: {total_ocr_chars:,}")
    print(f"Total Normalized Characters: {total_norm_chars:,}")
    print(f"Total Medical Entities: {total_entities}")
    
    # Document types breakdown
    doc_types = {}
    for doc in documents:
        doc_type = doc.get('type', 'unknown')
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    print(f"\n📋 Document Types:")
    for doc_type, count in doc_types.items():
        print(f"   {doc_type}: {count}")
    
    # Status breakdown
    statuses = {}
    for doc in documents:
        status = doc.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\n📊 Processing Status:")
    for status, count in statuses.items():
        print(f"   {status}: {count}")
    
    print(f"\n✅ Database verification completed!")

if __name__ == "__main__":
    verify_jane_doe_database() 