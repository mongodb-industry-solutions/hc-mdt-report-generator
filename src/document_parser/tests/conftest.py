import pytest  
import os  
import tempfile  
from pathlib import Path  
import sys  
  
# Add the parent directory to sys.path so we can import our module  
sys.path.insert(0, str(Path(__file__).parent.parent))  
  
@pytest.fixture  
def temp_text_file():  
    """Create a temporary text file for testing"""  
    content = """# Test Document  
This is a test paragraph.  
  
## Section 2  
More content here.  
- Item 1  
- Item 2  
"""  
    # Use delete=False and manual cleanup to ensure file persists during test  
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:  
        f.write(content)  
        f.flush()  # Ensure content is written to disk  
        temp_path = f.name  
      
    yield temp_path  
      
    # Clean up after test  
    try:  
        os.unlink(temp_path)  
    except FileNotFoundError:  
        pass  # File already deleted, no problem  
  
@pytest.fixture  
def sample_test_data():  
    """Sample test data for various tests"""  
    return {  
        "text_content": "Sample text content for testing",  
        "metadata": {"test": "value"},  
        "document_elements": []  
    }  
