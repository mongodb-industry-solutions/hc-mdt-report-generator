#!/usr/bin/env python3
"""
Simple test script for test-en-doc.json entity extraction

Run this from the project root with:
python scripts/simple_test_en_doc.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_entity_extraction():
    """Test entity extraction on test-en-doc.json"""
    
    try:
        # Import after path setup
        from document_extraction.test_en_doc_processor import TestEnDocProcessor
        
        # Path to test file
        test_file = project_root / "data" / "test-en-doc.json"
        
        if not test_file.exists():
            logger.error(f"Test file not found: {test_file}")
            return
        
        logger.info("🔍 Processing test-en-doc.json...")
        
        # Create processor and analyze the file
        processor = TestEnDocProcessor()
        
        # Step 1: Process the file format
        processed_data = processor.process_test_en_doc_file(str(test_file))
        patient_id = processed_data.get('pat', {}).get('NUMDOS', 'UNKNOWN')
        lcrs_count = len(processed_data.get('lCrs', []))
        
        logger.info(f"✅ Processed file: Patient {patient_id}, {lcrs_count} clinical reports")
        
        # Step 2: Analyze potential entities
        entity_suggestions = processor.get_entity_mapping_suggestions(str(test_file))
        
        logger.info("📊 Entity Analysis Results:")
        for entity_name, suggestions in entity_suggestions.items():
            logger.info(f"   {entity_name}: {', '.join(suggestions[:3])}")  # Show first 3 suggestions
        
        # Step 3: Show document structure for NER
        logger.info("📋 Document Structure for NER:")
        for i, lcr in enumerate(processed_data.get('lCrs', [])[:3]):  # Show first 3
            title = lcr.get('TITLE', 'No title')
            libnatcr = lcr.get('LIBNATCR', 'Unknown type')
            text_length = len(lcr.get('TEXTE', ''))
            logger.info(f"   Report {i+1}: {title} ({libnatcr}) - {text_length} chars")
        
        # Step 4: Extract key clinical information
        logger.info("🏥 Key Clinical Information Found:")
        extract_key_clinical_info(processed_data.get('lCrs', []))
        
        logger.info("✅ Test completed! The file format is compatible with the MDT system.")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure to run this from the project root directory")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def extract_key_clinical_info(lcrs):
    """Extract and display key clinical information from the documents"""
    
    clinical_info = {
        'diagnoses': [],
        'procedures': [],
        'treatments': [],
        'assessments': [],
        'dates': []
    }
    
    for lcr in lcrs:
        text = lcr.get('TEXTE', '').lower()
        title = lcr.get('TITLE', '')
        date = lcr.get('CR_DATE', '')
        
        # Extract diagnosis information
        if 'adenocarcinoma' in text:
            clinical_info['diagnoses'].append(f"Colorectal adenocarcinoma ({date})")
        
        # Extract procedures
        if 'hemicolectomy' in text:
            clinical_info['procedures'].append(f"Left hemicolectomy ({date})")
        if 'colonoscopy' in text:
            clinical_info['procedures'].append(f"Colonoscopy with biopsy ({date})")
        
        # Extract treatments
        if 'folfox' in text:
            clinical_info['treatments'].append(f"FOLFOX chemotherapy ({date})")
        if 'adjuvant' in text:
            clinical_info['treatments'].append(f"Adjuvant chemotherapy discussed ({date})")
        
        # Extract assessments
        if 'ct scan' in text or 'ct' in title.lower():
            if 'no evidence' in text:
                clinical_info['assessments'].append(f"CT scan - no metastases ({date})")
            else:
                clinical_info['assessments'].append(f"CT scan performed ({date})")
        
        if 'performance status' in text:
            clinical_info['assessments'].append(f"WHO performance status documented ({date})")
        
        if date:
            clinical_info['dates'].append(date)
    
    # Display findings
    for category, items in clinical_info.items():
        if items:
            logger.info(f"   {category.title()}: {len(items)} found")
            for item in items[:2]:  # Show first 2 items
                logger.info(f"     - {item}")

def show_sample_content(lcrs):
    """Show sample content from each document type"""
    
    logger.info("📄 Sample Document Content:")
    
    for lcr in lcrs[:3]:  # Show first 3 documents
        title = lcr.get('TITLE', 'Untitled')
        text = lcr.get('TEXTE', '')
        
        # Show first 200 characters
        preview = text[:200] + "..." if len(text) > 200 else text
        logger.info(f"   {title}:")
        logger.info(f"     {preview}")

if __name__ == "__main__":
    asyncio.run(test_entity_extraction())