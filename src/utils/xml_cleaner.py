import re
from html import unescape


def extract_clinical_text(xml_content: str) -> str:
    """
    Extract essential text from clinical XML documents.
    Returns: title, date, author info, and cleaned text content.
    """
    result = []

    # Extract title
    title_match = re.search(r"<title>([^<]+)</title>", xml_content)
    if title_match:
        result.append(f"Title: {title_match.group(1)}")

    # Extract date/time
    time_match = re.search(r"<effectiveTime value=\"(\d+)", xml_content)
    if time_match:
        raw_date = time_match.group(1)
        # Format: YYYYMMDDHHMMSS -> YYYY-MM-DD HH:MM
        if len(raw_date) >= 12:
            formatted = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]} {raw_date[8:10]}:{raw_date[10:12]}"
            result.append(f"Date: {formatted}")

    # Extract author/department
    author_match = re.search(r"displayName=\"([^\"]+)\"", xml_content)
    if author_match:
        result.append(f"Department: {author_match.group(1)}")

    # Extract main text content from CDATA section
    cdata_match = re.search(r"<!\[CDATA\[(.*?)\]\]>", xml_content, re.DOTALL)
    if cdata_match:
        text = cdata_match.group(1)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)

        # Unescape HTML entities
        text = unescape(text)

        # Remove excessive spaces and trim
        text = " ".join(text.split())

        result.append("\nClinical Data:")
        result.append(text)

    return "\n".join(result)

