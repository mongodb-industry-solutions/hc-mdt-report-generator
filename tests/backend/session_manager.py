import streamlit as st  
import os  
import time  
import pickle  
  


def initialize_session_state():  
    """Initialize session state variables for resilience"""  
    if 'processing_results' not in st.session_state:  
        st.session_state.processing_results = None  
    if 'html_result' not in st.session_state:  
        st.session_state.html_result = None  
    if 'processing_stats' not in st.session_state:  
        st.session_state.processing_stats = None  
    if 'uploaded_files_cache' not in st.session_state:  
        st.session_state.uploaded_files_cache = None  
    if 'processing_complete' not in st.session_state:  
        st.session_state.processing_complete = False  
    if 'processing_logs' not in st.session_state:  
        st.session_state.processing_logs = []
    if 'extraction_result' not in st.session_state:
        st.session_state.extraction_result = []




def cache_uploaded_files(uploaded_files):  
    """Cache uploaded files data to session state"""  
    if uploaded_files:  
        # Store file info and content  
        cached_files = []  
        for file in uploaded_files:  
            cached_files.append({  
                'name': file.name,  
                'size': file.size,  
                'content': file.getvalue()  # Store the actual file content  
            })  
        st.session_state.uploaded_files_cache = cached_files  
        return cached_files  
    return None  
  
def save_session_to_disk():  
    """Save session state to disk for persistence"""  
    try:  
        session_data = {  
            'processing_results': st.session_state.get('processing_results'),  
            'html_result': st.session_state.get('html_result'),  
            'processing_stats': st.session_state.get('processing_stats'),  
            'uploaded_files_cache': st.session_state.get('uploaded_files_cache'),  
            'processing_complete': st.session_state.get('processing_complete', False),  
            'processing_logs': st.session_state.get('processing_logs', []),  
            'timestamp': time.time()  
        }  
          
        with open('session_backup.pkl', 'wb') as f:  
            pickle.dump(session_data, f)  
        return True  
    except Exception as e:  
        st.warning(f"Could not save session: {e}")  
        return False  
  
def load_session_from_disk():  
    """Load session state from disk"""  
    if os.path.exists('session_backup.pkl'):  
        try:  
            with open('session_backup.pkl', 'rb') as f:  
                session_data = pickle.load(f)  
              
            # Check if session is not too old (24 hours)  
            if time.time() - session_data.get('timestamp', 0) < 86400:  
                for key, value in session_data.items():  
                    if key != 'timestamp':  
                        st.session_state[key] = value  
                return True  
            else:  
                os.remove('session_backup.pkl')  # Remove old session  
                return False  
        except Exception as e:  
            st.warning(f"Could not load previous session: {e}")  
            return False  
    return False  
  
def clear_all_state():  
    """Clear all session state and disk backup"""  
    st.session_state.processing_results = None  
    st.session_state.html_result = None  
    st.session_state.processing_stats = None  
    st.session_state.uploaded_files_cache = None  
    st.session_state.processing_complete = False  
    st.session_state.processing_logs = []  
      
    # Remove disk backup  
    if os.path.exists('session_backup.pkl'):  
        try:  
            os.remove('session_backup.pkl')  
        except:  
            pass  