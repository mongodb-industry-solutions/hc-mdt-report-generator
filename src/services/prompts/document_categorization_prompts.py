"""
Document Categorization Prompts

Contains prompts used for categorizing medical documents into predefined categories.

Version: 1.0.0
Created: 2024-12-17
Last Updated: 2024-12-17

Changelog:
- 1.0.0: Initial version with centralized prompts
"""

from .prompt_config import get_prompt_version

# System prompt for document categorization
SYSTEM_PROMPT = """You are an expert medical document classifier specializing in French healthcare documentation. 
Your task is to accurately categorize medical documents based on their content and structure."""

# Document categorization prompt
DOCUMENT_CATEGORIZATION_PROMPT = """Analyze the following medical document and categorize it into one of the predefined categories.

DOCUMENT CATEGORIES:
1. Documents administratifs de codage (PMSI/T2A) - Administrative coding documents for hospital billing and activity classification
2. Comptes rendus opératoires - Surgical reports and operative notes
3. Comptes rendus d'hospitalisation/séjour - Hospitalization and stay reports
4. Comptes rendus d'imagerie médicale - Medical imaging reports (X-rays, CT scans, MRIs, etc.)
5. Comptes rendus de consultation - Consultation reports and outpatient visit notes
6. Documents de prescription - Prescription documents and medication orders
7. Résultats d'examens biologiques - Biological test results and laboratory reports
8. Courriers de liaison/correspondance médicale - Medical correspondence and liaison letters

DOCUMENT TEXT:
{content}

TASK:
Based on the content, structure, and medical terminology in the document, determine which category best describes this document. Consider:
- The type of medical information presented
- The document's purpose and context
- Medical terminology and procedures mentioned
- The format and structure of the document

RESPONSE FORMAT:
<CATEGORY>exact_category_name_from_list_above</CATEGORY>
<CONFIDENCE>high/medium/low</CONFIDENCE>
<REASONING>brief explanation of why this category was chosen</REASONING>

Examples:
- For a surgical report: <CATEGORY>Comptes rendus opératoires</CATEGORY>
- For a CT scan report: <CATEGORY>Comptes rendus d'imagerie médicale</CATEGORY>
- For a blood test result: <CATEGORY>Résultats d'examens biologiques</CATEGORY>
""" 