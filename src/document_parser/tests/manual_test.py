#!/usr/bin/env python3  
"""  
Manual testing script for the Document Parser  
Run with: python manual_test.py  
"""  
import asyncio  
import os  
import tempfile  
from pathlib import Path  
  
async def test_basic_functionality():  
    """Basic functionality test"""  
    from universal_document_parser import UniversalDocumentParser  
      
    # You can set a mock API key for basic testing  
    os.environ.setdefault("MISTRAL_API_KEY", "test-key")  
      
    parser = UniversalDocumentParser()  
      
    # Test format detection  
    print("Testing format detection...")  
    assert parser._is_plain_text("test.txt")  
    assert parser._is_ocr_supported("test.pdf")  
    print("✓ Format detection works")  
      
    # Test with a text file  
    print("Testing text file parsing...")  
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:  
        f.write("# Test Document\nThis is test content.")  
        temp_path = f.name  
      
    try:  
        content = await parser._extract_text_content(temp_path)  
        assert "Test Document" in content  
        print("✓ Text extraction works")  
          
        metadata = parser._extract_metadata(temp_path, content)  
        assert metadata["file_type"] == ".txt"  
        print("✓ Metadata extraction works")  
          
    finally:  
        os.unlink(temp_path)  
      
    print("All basic tests passed!")  
  
if __name__ == "__main__":  
    asyncio.run(test_basic_functionality())  
