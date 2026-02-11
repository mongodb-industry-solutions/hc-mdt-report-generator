"""
Document Chunking Prompts

Contains prompts used for intelligently chunking medical documents using AI.
These prompts guide the LLM to split long text into meaningful, comprehensive chunks
while preserving medical context and maintaining logical document structure.
"""

# System prompt for document chunking
SYSTEM_PROMPT = """You are a text chunking expert. Your job is to split raw text into comprehensive chunks of related information."""

# Main chunking prompt template
DOCUMENT_CHUNKING_PROMPT = """You are a text chunking assistant.

TASK: Split text into MEANINGFUL, COMPREHENSIVE CHUNKS, of 100 to 500 words.

RULES:
1. Keep related content together (lists, paragraphs, technical specs)
2. Each chunk = one COMPLETE idea/section
3. Copy text exactly - preserve all data as it appears in the TEXT TO PROCESS.
4. Keep headers with their content
5. If new text seems to be a continuation of the previous chunk (same CATEGORY), ignore the previous chunk and add in tags <MERGE>TRUE</MERGE>
6. Make sure ALL TEXT in TEXT TO PROCESS is included in the chunks in your output, including headers, subtitles, etc.

##EXAMPLE - MERGING

PREVIOUS CHUNK:
<CONTENT>ELECTRODE ATRIALE. Biotronik SOLIA S 53cm implantée. Le seuil de stimulation est</CONTENT>
<CATEGORY>CARDIAC DEVICE IMPLANTATION</CATEGORY>
<MERGE>FALSE</MERGE>

NEW TEXT: "de 0,6 Volts pour 0,4 ms. L'impédance est de 525 Ohms."

OUTPUT:
<CHUNK>
<CONTENT>de 0,6 Volts pour 0,4 ms. L'impédance est de 525 Ohms.</CONTENT>
<CATEGORY>CARDIAC DEVICE IMPLANTATION</CATEGORY>
<MERGE>TRUE</MERGE>
</CHUNK>

##YOUR TASK NOW:

PREVIOUS CHUNK:
{previous_chunk_xml}

TEXT TO PROCESS:
"{raw_text}"

Please process the TEXT TO PROCESS above. If it's a continuation of the PREVIOUS CHUNK (same category), use <MERGE>TRUE</MERGE>. Otherwise, create new chunks as needed.

##OUTPUT FORMAT

<CHUNKS>
<CHUNK>
<CONTENT>exact text substring from TEXT TO PROCESS</CONTENT>
<CATEGORY>WHAT IS THE CONTENT ABOUT</CATEGORY>
<MERGE>TRUE/FALSE</MERGE>
</CHUNK>
</CHUNKS>"""

def create_chunking_prompt(previous_chunk_xml: str = None, raw_text: str = "") -> str:
    """
    Create a formatted prompt for document chunking.
    
    Args:
        previous_chunk_xml: XML of the previous chunk for context, or None if first chunk
        raw_text: The raw text to be chunked
        
    Returns:
        Formatted prompt string
    """
    return DOCUMENT_CHUNKING_PROMPT.format(
        previous_chunk_xml=previous_chunk_xml if previous_chunk_xml else "None",
        raw_text=raw_text
    ) 