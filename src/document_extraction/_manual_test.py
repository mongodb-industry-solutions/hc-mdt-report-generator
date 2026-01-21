import json  
from cda_utils import process_files, get_document_types_summary, get_skipped_files_summary  
  
def main():  

    ################ GR Document Extracting Tool (../src/document_extraction/cda_utils.process_files)

    # Define the patient ID you want to process  
    target_patient_id = "GR-AutresK-QUAL-20246000be8a04c5831890a8520772d2741035511e5bcf3bda1c57db384728ad26d7"  
      
    # Process files  
    results = process_files(  
        path='../../../test_data/POCIAMONGO',  #<--grab the .zip, unzippid and stored out of git folder for testing purposes
        extensions=['xml', 'hl7', 'pdf'],  
        start_date='20200101',  
        end_date='20231231',  
        patient_id=target_patient_id,  
        download_folder='/Users/chris.beltran/code/ClarityGR/emulated_container_fs' #write full path here, do not use relative notation
    )  
      
    # Save results to JSON  
    with open('cda_extraction_results.json', 'w', encoding='utf-8') as f:  
        json.dump(results, f, indent=2, ensure_ascii=False)  
      
    # Print summary  
    print(f"\nSummary:")  
    print(f"Patient ID: {results['patient_id']}")  
    print(f"Files found: {results['summary']['total_files_found']}")  
    print(f"Documents processed: {results['summary']['documents_processed']}")  
    print(f"Files skipped: {results['summary']['files_skipped']}")  
    pmsi_docs_count = len([d for d in results['documents'] if d.get('PMSI', False)])  
    print(f"PMSI documents: {pmsi_docs_count}")  
      
    # Get document types breakdown  
    doc_types = get_document_types_summary(results['documents'])  
    print(f"Document types breakdown: {doc_types['document_types']}")  
      
    # After processing, show PMSI-specific results  
    pmsi_docs = [d for d in results['documents'] if d.get('PMSI', False)]  
    if pmsi_docs:  
        print(f"\n🏥 PMSI ANALYSIS:")  
        print(f"PMSI documents found: {len(pmsi_docs)}")  
      





if __name__ == "__main__":  
    main()  
