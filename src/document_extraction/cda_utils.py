from typing import List, Dict  
from datetime import datetime  
import logging 
import os  
import shutil  
import time

  
def get_document_types_summary(processed_docs: List[Dict]) -> Dict:  
    """Get summary of all document types"""  
    total = len(processed_docs)  
    mdt_count = len([d for d in processed_docs if d.get('MDT', False)])  
    pmsi_count = len([d for d in processed_docs if d.get('PMSI', False)])  
    other_count = total - mdt_count - pmsi_count  
      
    return {  
        'total_documents': total,  
        'document_types': {'MDT': mdt_count, 'PMSI': pmsi_count, 'Other': other_count},  
        'percentages': {  
            'MDT': (mdt_count / total * 100) if total > 0 else 0,  
            'PMSI': (pmsi_count / total * 100) if total > 0 else 0,  
            'Other': (other_count / total * 100) if total > 0 else 0  
        }  
    }  
  
def get_skipped_files_summary(validation_data: Dict) -> Dict:  
    """Get detailed summary of why files were skipped"""  
    skipped_files = validation_data.get('skipped_files', [])  
    summary = {'total_skipped': len(skipped_files), 'reasons': {}, 'details': []}  
      
    # Count by reason  
    for skipped in skipped_files:  
        reason = skipped.get('reason', 'unknown')  
        summary['reasons'][reason] = summary['reasons'].get(reason, 0) + 1  
      
    # Get examples for each reason  
    for reason in summary['reasons']:  
        examples = [s for s in skipped_files if s.get('reason') == reason][:5]  
        summary['details'].append({  
            'reason': reason,  
            'count': summary['reasons'][reason],  
            'examples': examples  
        })  
      
    return summary  



from datetime import datetime, timedelta  
from typing import Dict, List, Optional  
  
def filter_documents_by_latest_mdt(data: Dict, ndays_offset: int = 0) -> Dict:  
    """  
    Filter documents to include only those newer than or equal to the latest MDT date (minus offset),  
    plus always include the latest PMSI document regardless of date.  
      
    Args:  
        data: JSON data with documents  
        ndays_offset: Number of days to subtract from latest MDT date  
      
    Returns:  
        Filtered JSON with same structure but only relevant documents  
    """  
      
    # Get all documents  
    documents = data.get('documents', [])  
    if not documents:  
        return data  
      
    # Find latest MDT document  
    mdt_docs = [doc for doc in documents if doc.get('MDT', False)]  
    if not mdt_docs:  
        # No MDT found, return original data  
        return data  
      
    # Get the latest MDT by date  
    latest_mdt = max(mdt_docs, key=lambda x: x.get('date', '1900-01-01'))  
    latest_mdt_date = latest_mdt.get('date', '1900-01-01')  
      
    # Calculate cutoff date (latest MDT date minus offset)  
    mdt_datetime = datetime.strptime(latest_mdt_date, '%Y-%m-%d')  
    cutoff_datetime = mdt_datetime - timedelta(days=ndays_offset)  
    cutoff_date = cutoff_datetime.strftime('%Y-%m-%d')  
      
    # Find latest PMSI document  
    pmsi_docs = [doc for doc in documents if doc.get('PMSI', False)]  
    latest_pmsi = max(pmsi_docs, key=lambda x: x.get('date', '1900-01-01')) if pmsi_docs else None  
      
    # Filter documents: newer than or equal to cutoff date  
    filtered_docs = []  
      
    for doc in documents:  
        doc_date = doc.get('date', '1900-01-01')  
          
        # Include if date >= cutoff_date  
        if doc_date >= cutoff_date:  
            filtered_docs.append(doc)  
        # OR always include the latest PMSI document regardless of date  
        elif latest_pmsi and doc == latest_pmsi:  
            filtered_docs.append(doc)  
      
    # Remove duplicates (in case latest PMSI was already included)  
    seen = set()  
    unique_docs = []  
    for doc in filtered_docs:  
        doc_id = doc.get('file_path', '')  
        if doc_id not in seen:  
            seen.add(doc_id)  
            unique_docs.append(doc)  
      
    # Sort by date (newest first)  
    unique_docs.sort(key=lambda x: x.get('date', '1900-01-01'), reverse=True)  
      
    # Return filtered data with same structure  
    filtered_data = data.copy()  
    filtered_data['documents'] = unique_docs  
      
    # Update summary if it exists  
    if 'summary' in filtered_data:  
        filtered_data['summary']['documents_processed'] = len(unique_docs)  
        filtered_data['summary']['mdt_documents'] = len([d for d in unique_docs if d.get('MDT', False)])  
        filtered_data['summary']['pmsi_documents'] = len([d for d in unique_docs if d.get('PMSI', False)])  
      
    return filtered_data  
  
# Example usage:  
# filtered_data = filter_documents_by_latest_mdt(your_json_data, ndays_offset=30)  





def process_files(path: str, extensions: List[str], start_date: str, end_date: str, patient_id: str, download_folder: str = None, auto_mdt_filter: bool = True, mdt_days_offset: int = 10) -> Dict:  
    """Main processing function"""  
    from .cda_processor import find_files, read_file_content, extract_date_from_text, is_date_in_range, process_single_file  
      
    logging.info(f"Starting processing: {path}, extensions: {extensions}")  
    logging.info(f"Date range: {start_date} to {end_date}")  
    logging.info(f"Expected patient ID: {patient_id}")  
      
    # Find all files  
    files = find_files(path, extensions)  
    logging.info(f"Found {len(files)} files")  
      
    # Filter by date, patient, and process  
    processed_docs = []  
    validation_errors = []  
    skipped_files = []  
    pdf_stored_files = []
      
    for file_path in files:    
        if '.pdf' in file_path:
            # Check if patient_id is in filename and copy if so  
            if patient_id in file_path:  
                if download_folder:  
                    filename = os.path.basename(file_path)  
                    dest_path = os.path.join(download_folder, filename)  
                    shutil.copy2(file_path, download_folder)  
                    pdf_stored_files.append(dest_path)  
            continue  

        content = read_file_content(file_path)  
        if not content:  
            continue  
          
        # Extract date and check if patient ID is in content  
        doc_date = extract_date_from_text(content)  
          
        # Validate patient ID first - just check if it's IN the content  
        if patient_id not in content:  
            error_msg = f"Patient ID not found in {file_path}: expected '{patient_id}'"  
            logging.warning(error_msg)  
            validation_errors.append(error_msg)  
            skipped_files.append({  
                'file_path': file_path,  
                'expected_patient': patient_id,  
                'found_patient': 'not_found_in_content',  
                'reason': 'patient_id_not_in_content'  
            })  
            continue  
          
        # Then validate date range  
        if not is_date_in_range(doc_date, start_date, end_date):  
            logging.debug(f"Skipping {file_path} - date {doc_date} not in range")  
            skipped_files.append({  
                'file_path': file_path,  
                'date': doc_date,  
                'reason': 'date_out_of_range'  
            })  
            continue  
          
        # Process the file  
        logging.info(f"Processing: {file_path} (date: {doc_date})")  
        result = process_single_file(file_path, download_folder)  
          
        if result and result.get('extraction_success'):  
            processed_docs.append(result)  
        else:  
            logging.warning(f"Failed to process: {file_path}")  
            validation_errors.append(f"Failed to process: {file_path}")  
      
    # Sort by date (newest first)  
    def get_sort_date(doc):  
        date_raw = doc.get('date_raw')  
        if date_raw:  
            try:  
                return datetime.strptime(date_raw, '%Y%m%d')  
            except:  
                return datetime.min  
        return datetime.min  
      
    processed_docs.sort(key=get_sort_date, reverse=True)  
      
    # Create validation summary  
    validation = {  
        'valid': len(validation_errors) == 0,  
        'patient_id': patient_id,  
        'total_files_found': len(files),  
        'documents_processed': len(processed_docs),  
        'files_skipped': len(skipped_files),  
        'validation_errors': validation_errors,  
        'skipped_files': skipped_files  
    }  
      
    # Log validation results  
    if validation['valid']:  
        logging.info(f"✅ Successfully processed {len(processed_docs)} documents for patient: {patient_id}")  
    else:  
        logging.error(f"❌ Validation issues found: {len(validation_errors)} errors")  
        for error in validation_errors[:5]:  
            logging.error(f"   - {error}")  

      
    result =  {      
        'patient_id': patient_id,      
        'documents': processed_docs,
        'downloaded_pdf_files': pdf_stored_files,
        'summary': {      
            'total_files_found': len(files),      
            'documents_processed': len(processed_docs),      
            'files_skipped': len(skipped_files),      
            'mdt_documents': len([d for d in processed_docs if d.get('MDT', False)]),      
            # 🔧 FIX: Check if PMSI field has content, not if it's True  
            'pmsi_documents': len([d for d in processed_docs if d.get('PMSI', False) is True]),
            'date_range': {'start': start_date, 'end': end_date},      
            'processing_date': datetime.now().isoformat()      
        }     
    }  

    if auto_mdt_filter:
        result = filter_documents_by_latest_mdt(result, mdt_days_offset)


    return result
