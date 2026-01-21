"""  
Entity Extraction Module  
"""  
  
# Import the main function you're using in your orchestrator  
from .ner_classifier import extract_entities_workflow  
  
# If there are other functions you need from ner_classifier.py, add them here  
# Example (uncomment and adjust based on what actually exists):  
# from .ner_classifier import some_other_function_name  
  
# Make the imported functions available when importing the module  
__all__ = [  
    'extract_entities_workflow',  
    # Add other function names here as needed  
]  
