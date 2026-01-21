#!/usr/bin/env python3
"""
Upload Jane Doe's complete medical history through the API.
This script uploads all documents in chronological order to test the complete workflow.
"""

import asyncio
import base64
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
PATIENT_ID = "jane-doe"

# Document timeline in chronological order
DOCUMENTS = [
    {
        "filename": "2022-03-15_initial_consultation.txt",
        "type": "consultation",
        "date": "2022-03-15",
        "description": "Initial consultation for benign dyspepsia"
    },
    {
        "filename": "2022-03-20_blood_test.csv",
        "type": "lab_report",
        "date": "2022-03-20",
        "description": "Blood test results - normal values"
    },
    {
        "filename": "2022-04-10_endoscopy_report.txt",
        "type": "imaging",
        "date": "2022-04-10",
        "description": "Endoscopy report - normal findings"
    },
    {
        "filename": "2022-04-30_follow_up_consultation.txt",
        "type": "consultation",
        "date": "2022-04-30",
        "description": "Follow-up consultation - benign case concluded"
    },
    {
        "filename": "2024-11-15_new_symptoms_consultation.txt",
        "type": "consultation",
        "date": "2024-11-15",
        "description": "New symptoms consultation - dysphagia"
    },
    {
        "filename": "2024-11-18_blood_test_abnormal.csv",
        "type": "lab_report",
        "date": "2024-11-18",
        "description": "Blood test results - abnormal values"
    },
    {
        "filename": "2024-11-20_ct_scan_report.txt",
        "type": "imaging",
        "date": "2024-11-20",
        "description": "CT scan report - esophageal mass"
    },
    {
        "filename": "2024-11-25_endoscopy_with_biopsy.txt",
        "type": "imaging",
        "date": "2024-11-25",
        "description": "Endoscopy with biopsy - suspicious mass"
    },
    {
        "filename": "2024-11-28_pathology_report.json",
        "type": "diagnosis",
        "date": "2024-11-28",
        "description": "Pathology report - adenocarcinoma confirmed"
    },
    {
        "filename": "2024-12-02_oncology_consultation.txt",
        "type": "treatment_plan",
        "date": "2024-12-02",
        "description": "Oncology consultation - treatment plan"
    }
]

def encode_file_to_base64(file_path: str) -> str:
    """Encode file to base64"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def upload_document(doc_info: Dict[str, Any]) -> str:
    """Upload a document and return the document UUID"""
    file_path = Path(__file__).parent / doc_info["filename"]
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return None
    
    print(f"\n📄 Uploading: {doc_info['filename']}")
    print(f"   Type: {doc_info['type']}")
    print(f"   Date: {doc_info['date']}")
    print(f"   Description: {doc_info['description']}")
    
    # Encode file content
    base64_content = encode_file_to_base64(file_path)
    
    # Prepare upload request
    upload_data = {
        "type": doc_info["type"],
        "source": "medical_history",
        "status": "queued",
        "notes": f"Jane Doe medical history - {doc_info['description']} ({doc_info['date']})",
        "filename": doc_info["filename"],
        "file": base64_content
    }
    
    # Upload document
    try:
        response = requests.post(
            f"{BASE_URL}/patients/{PATIENT_ID}/document",
            json=upload_data,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   UUID: {result['uuid']}")
            print(f"   Status: {result['status']}")
            return result['uuid']
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def check_document_status(document_uuid: str) -> str:
    """Check document processing status"""
    try:
        response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}")
        if response.status_code == 200:
            result = response.json()
            return result['status']
        else:
            return "unknown"
    except:
        return "unknown"

def wait_for_processing(document_uuid: str, timeout: int = 120) -> str:
    """Wait for document processing to complete"""
    print(f"⏳ Waiting for processing...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = check_document_status(document_uuid)
        print(f"   Status: {status}")
        
        if status in ["done", "failed"]:
            return status
        
        time.sleep(5)
    
    return "timeout"

def get_processing_results(document_uuid: str):
    """Get processing results for a document"""
    print(f"📊 Getting results for {document_uuid}")
    
    # Get OCR results
    try:
        ocr_response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}/ocr")
        if ocr_response.status_code == 200:
            ocr_data = ocr_response.json()
            print(f"✅ OCR: {ocr_data.get('character_count', 'N/A')} chars")
        else:
            print(f"❌ OCR not available: {ocr_response.status_code}")
    except Exception as e:
        print(f"❌ OCR error: {e}")
    
    # Get normalization results
    try:
        norm_response = requests.get(f"{BASE_URL}/patients/{PATIENT_ID}/document/{document_uuid}/")
        if norm_response.status_code == 200:
            norm_data = norm_response.json()
            print(f"✅ Normalization: {norm_data.get('normalization_status', 'N/A')}")
            print(f"   Original: {norm_data.get('original_character_count', 'N/A')} chars")
            print(f"   Normalized: {norm_data.get('normalized_character_count', 'N/A')} chars")
        else:
            print(f"❌ Normalization not available: {norm_response.status_code}")
    except Exception as e:
        print(f"❌ Normalization error: {e}")

async def upload_jane_doe_history():
    """Upload Jane Doe's complete medical history"""
    print("🚀 Starting Jane Doe medical history upload")
    print("=" * 60)
    
    uploaded_documents = []
    
    # Upload documents in chronological order
    for doc_info in DOCUMENTS:
        document_uuid = upload_document(doc_info)
        
        if document_uuid:
            uploaded_documents.append({
                "uuid": document_uuid,
                "info": doc_info
            })
            
            # Wait for processing
            final_status = wait_for_processing(document_uuid)
            
            if final_status == "done":
                print(f"✅ Processing completed successfully")
                get_processing_results(document_uuid)
            elif final_status == "failed":
                print(f"❌ Processing failed")
            else:
                print(f"⚠️ Processing timeout")
            
            print("-" * 40)
        else:
            print(f"❌ Failed to upload {doc_info['filename']}")
            print("-" * 40)
    
    # Summary
    print("\n📋 UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total documents: {len(DOCUMENTS)}")
    print(f"Successfully uploaded: {len(uploaded_documents)}")
    
    for doc in uploaded_documents:
        print(f"✅ {doc['info']['filename']} - {doc['uuid']}")
    
    print("\n🏁 Jane Doe medical history upload completed!")

if __name__ == "__main__":
    asyncio.run(upload_jane_doe_history()) 