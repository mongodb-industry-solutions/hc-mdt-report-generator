import os  
import json  
import re  
from pathlib import Path  
from datetime import datetime  
from typing import List, Dict, Optional  
import logging 
  
# Configure logging  
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  
  
content_tags = ['<text>', '<title>', '<value>', '<originalText>', '<caption>']  
  
def find_files(path: str, extensions: List[str]) -> List[str]:  
    """Find all files with specified extensions"""  
    found_files = []  
    path_obj = Path(path)  
    if not path_obj.exists():  
        raise FileNotFoundError(f"Path does not exist: {path}")  
    for ext in extensions:  
        ext = ext.lstrip('.')  
        found_files.extend(path_obj.rglob(f"*.{ext}"))  
    return [str(f) for f in sorted(found_files)]  
  
def read_file_content(file_path: str) -> str:  
    """Read file content as text"""  
    try:  
        with open(file_path, 'r', encoding='utf-8') as f:  
            return f.read()  
    except UnicodeDecodeError:  
        try:  
            with open(file_path, 'r', encoding='latin-1') as f:  
                return f.read()  
        except Exception as e:  
            logging.error(f"Could not read file {file_path}: {str(e)}")  
            return ""  
    except Exception as e:  
        logging.error(f"Error reading file {file_path}: {str(e)}")  
        return ""  
  

def detect_pmsi_document(content: str) -> bool:   
    """Detect if document is a PMSI document"""      
    # 🔧 QUICK TEST: Just look for the exact title string  
    return 'PMSI' in content  


  
def detect_mdt_document(content: str) -> bool:  
    """Detect if document is a MDT report"""  
    mdt_indicators = ['réunion de concertation pluridisciplinaire', 'concertation pluridisciplinaire']  
    content_lower = content.lower()  
    return any(indicator.lower() in content_lower for indicator in mdt_indicators)  



  
def extract_date_from_text(content: str) -> Optional[str]:      
    """Extract date from CDA content - supports multiple formats and locations"""      
    try:  
        # List of patterns to search for dates (in order of preference)  
        date_patterns = [  
            # Pattern 1: <effectiveTime value="YYYYMMDD..."/>  
            r'<effectiveTime[^>]*value=["\'](\d{8,14})[^"\']*["\']',  
              
            # Pattern 2: <author><time value="YYYYMMDD..."/>  
            r'<author>.*?<time[^>]*value=["\'](\d{8,14})[^"\']*["\']',  
              
            # Pattern 3: Any <time value="YYYYMMDD..."/>  
            r'<time[^>]*value=["\'](\d{8,14})[^"\']*["\']',  
              
            # Pattern 4: <dateRealisation>YYYY-MM-DD HH:MM:SS</dateRealisation>  
            r'<dateRealisation>(\d{4}-\d{2}-\d{2})',  
              
            # Pattern 5: <date>YYYY-MM-DD</date>  
            r'<date>(\d{4}-\d{2}-\d{2})</date>',  
              
            # Pattern 6: Any other date-like patterns  
            r'date[^>]*=["\'](\d{4}-\d{2}-\d{2})["\']',  
            r'value=["\'](\d{4}-\d{2}-\d{2})["\']'  
        ]  
          
        for pattern in date_patterns:  
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)  
            if matches:  
                raw_date = matches[0]  
                  
                # Convert different formats to YYYYMMDD  
                if len(raw_date) >= 14:  # YYYYMMDDHHMMSS format  
                    return raw_date[:8]  # Extract YYYYMMDD  
                elif len(raw_date) == 8:  # Already YYYYMMDD  
                    return raw_date  
                elif '-' in raw_date:  # YYYY-MM-DD format  
                    return raw_date.replace('-', '')  # Convert to YYYYMMDD  
                      
        # If no patterns match, try the old method as fallback  
        for tag in ['<effectiveTime', '<author>', '<time']:      
            pos = content.find(tag)      
            if pos != -1:      
                value_pos = content.find('value=', pos)      
                if value_pos != -1:      
                    quote_start = content.find('"', value_pos)      
                    if quote_start != -1:      
                        quote_end = content.find('"', quote_start + 1)      
                        if quote_end != -1:      
                            date_value = content[quote_start + 1:quote_end]      
                            # Handle long timestamps  
                            date_match = re.match(r'(\d{8,14})', date_value)  
                            if date_match:  
                                full_date = date_match.group(1)  
                                return full_date[:8] if len(full_date) > 8 else full_date  
                                  
        return None      
    except Exception as e:      
        logging.error(f"Error extracting date: {str(e)}")      
        return None  

  
def extract_document_id(content: str) -> Optional[str]:  
    """Extract document ID"""  
    try:  
        id_pos = content.find('<id ')  
        if id_pos != -1:  
            extension_pos = content.find('extension=', id_pos)  
            if extension_pos != -1:  
                quote_start = content.find('"', extension_pos)  
                if quote_start != -1:  
                    quote_end = content.find('"', quote_start + 1)  
                    if quote_end != -1:  
                        return content[quote_start + 1:quote_end]  
        return None  
    except Exception as e:  
        logging.error(f"Error extracting document ID: {str(e)}")  
        return None  
  
def extract_title(content: str) -> Optional[str]:  
    """Extract title"""  
    try:  
        title_start = content.find('<title>')  
        if title_start != -1:  
            title_start += len('<title>')  
            title_end = content.find('</title>', title_start)  
            if title_end != -1:  
                return content[title_start:title_end].strip()  
        return None  
    except Exception as e:  
        logging.error(f"Error extracting title: {str(e)}")  
        return None  
  
def extract_content_by_tags(content: str) -> Dict[str, str]:  
    """Extract content based on configured tags"""  
    extracted = {}  
    for tag in content_tags:  
        try:  
            tag_name = tag.strip('<>')  
            start_tag = f'<{tag_name}>'  
            end_tag = f'</{tag_name}>'  
              
            start_pos = content.find(start_tag)  
            if start_pos != -1:  
                start_pos += len(start_tag)  
                end_pos = content.find(end_tag, start_pos)  
                if end_pos != -1:  
                    tag_content = content[start_pos:end_pos].strip()  
                      
                    # Handle CDATA sections  
                    if '<![CDATA[' in tag_content:  
                        cdata_start = tag_content.find('<![CDATA[') + len('<![CDATA[')  
                        cdata_end = tag_content.find(']]>')  
                        if cdata_end != -1:  
                            tag_content = tag_content[cdata_start:cdata_end]  
                      
                    tag_content = re.sub(r'\s+', ' ', tag_content)  
                    extracted[tag_name] = tag_content  
        except Exception as e:  
            logging.error(f"Error extracting content for tag {tag}: {str(e)}")  
    return extracted  
  
def is_date_in_range(doc_date: str, start_date: str, end_date: str) -> bool:  
    """Check if document date is within specified range"""  
    if not doc_date:  
        return False  
    try:  
        doc_dt = datetime.strptime(doc_date, '%Y%m%d')  
        start_dt = datetime.strptime(start_date, '%Y%m%d')  
        end_dt = datetime.strptime(end_date, '%Y%m%d')  
        return start_dt <= doc_dt <= end_dt  
    except ValueError:  
        logging.error(f"Invalid date format: {doc_date}")  
        return False  
  


# Add this import at the top  
from .pmsi_handler import process_pmsi_document  
  
def remove_html_tags(text):  
    """Remove HTML tags from text using string operations"""  
    # Remove specific tags we see in the text  
    tags_to_remove = ['<h3>', '</h3>', '<br/>', '<br>', '<b>', '</b>', '<u>', '</u>']  
      
    for tag in tags_to_remove:  
        text = text.replace(tag, '')  
      
    # Clean up extra spaces and newlines  
    return ' '.join(text.split())  



def process_single_file(file_path: str, download_folder: str = None) -> Optional[Dict]:      
    """Process a single CDA file"""      
    try:      
        content = read_file_content(file_path)      
        if not content:      
            return None      
              
        # Extract basic fields      
        document_id = extract_document_id(content)      
        title = extract_title(content)      
        date_raw = extract_date_from_text(content)      
              
        # Format date      
        date_formatted = None      
        if date_raw:      
            try:      
                date_obj = datetime.strptime(date_raw, '%Y%m%d')      
                date_formatted = date_obj.strftime('%Y-%m-%d')      
            except ValueError:      
                date_formatted = date_raw      
              
        # Document type detection          
        is_mdt = detect_mdt_document(content)          
        is_pmsi = detect_pmsi_document(content)          
              
                  
        # Extract configurable content          
        extracted_content = extract_content_by_tags(content)    

        if extracted_content['text']:
            extracted_content['text'] = remove_html_tags(extracted_content['text']) 


                  
        # 🏥 CALL PMSI HANDLER IF PMSI DOCUMENT FOUND          
        pmsi_result = ""        
        if is_pmsi:          
            pmsi_result = process_pmsi_document(content)          
              
            # 🔧 FIX: Add PMSI content to extracted_content if it exists  
            if pmsi_result and pmsi_result.strip():  # Check if not empty/None  
                extracted_content['text'] = pmsi_result  
                  
        result = {          
            'file_path': file_path,          
            'extraction_success': True,          
            'document_id': document_id,          
            'title': title,          
            'date': date_formatted,          
            'date_raw': date_raw,          
            'MDT': is_mdt,          
            'PMSI': is_pmsi,   # 🔧 FIX: Now boolean instead of string!      
            'content': extracted_content,          
            'has_pdfs': False          
        }          

        return result      
              
    except Exception as e:      
        logging.error(f"Error processing file {file_path}: {str(e)}")      
        return {      
            'file_path': file_path,      
            'extraction_success': False,      
            'error': str(e),      
            'MDT': False      
        }      
