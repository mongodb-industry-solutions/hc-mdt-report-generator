import json  
from datetime import datetime  
import html  
import re  
  
def format_text_content(text):  
    """  
    Format text content by converting markdown-like formatting to HTML  
    and improving readability  
    """  
    if not text or not isinstance(text, str):  
        return html.escape(str(text))  
      
    # Start with HTML-escaped text  
    formatted = html.escape(text)  
      
    # Convert markdown-style formatting to HTML  
      
    # Bold text (**text** or __text__)  
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)  
    formatted = re.sub(r'__(.*?)__', r'<strong>\1</strong>', formatted)  
      
    # Italic text (*text* or _text_)  
    formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)  
    formatted = re.sub(r'_(.*?)_', r'<em>\1</em>', formatted)  
      
    # Convert numbered lists (1. 2. 3. etc.)  
    lines = formatted.split('\n')  
    formatted_lines = []  
    in_list = False  
      
    for line in lines:  
        line = line.strip()  
          
        # Check for numbered list items  
        if re.match(r'^\d+\.\s+\*\*.*?\*\*.*?:', line):  
            if not in_list:  
                formatted_lines.append('<ol class="main-list">')  
                in_list = True  
            # Extract the main heading and content  
            match = re.match(r'^(\d+)\.\s+(.*)$', line)  
            if match:  
                formatted_lines.append(f'<li class="main-item">{match.group(2)}</li>')  
        # Check for sub-items starting with dash  
        elif line.startswith('- ') and in_list:  
            formatted_lines.append(f'<ul class="sub-list"><li class="sub-item">{line[2:]}</li></ul>')  
        # Regular numbered items  
        elif re.match(r'^\d+\.\s+', line):  
            if not in_list:  
                formatted_lines.append('<ol class="main-list">')  
                in_list = True  
            content = re.sub(r'^\d+\.\s+', '', line)  
            formatted_lines.append(f'<li class="main-item">{content}</li>')  
        # Bullet points  
        elif line.startswith('- '):  
            if in_list:  
                formatted_lines.append('</ol>')  
                in_list = False  
            if not any('sub-list' in prev_line for prev_line in formatted_lines[-3:]):  
                formatted_lines.append('<ul class="bullet-list">')  
            formatted_lines.append(f'<li class="bullet-item">{line[2:]}</li>')  
        # Regular lines  
        else:  
            if in_list and line:  
                formatted_lines.append('</ol>')  
                in_list = False  
            if line:  # Only add non-empty lines  
                formatted_lines.append(f'<p class="text-line">{line}</p>')  
      
    # Close any open lists  
    if in_list:  
        formatted_lines.append('</ol>')  
      
    # Join and clean up  
    formatted = '\n'.join(formatted_lines)  
      
    # Convert line breaks to proper paragraphs for remaining content  
    formatted = re.sub(r'\n\s*\n', '</p><p class="text-line">', formatted)  
      
    # Clean up extra spaces and formatting  
    formatted = re.sub(r'\s+', ' ', formatted)  
    formatted = formatted.strip()  
      
    return formatted  
  
def parse_json_to_html(json_data):  
    """  
    Parse JSON data and convert it to a nicely formatted HTML document.  
      
    Args:  
        json_data: JSON string or dict containing entity extraction results  
          
    Returns:  
        str: HTML document as a string  
    """  
      
    try:  
        # Parse JSON data  
        if isinstance(json_data, str):  
            data = json.loads(json_data)  
        else:  
            data = json_data  
          
        # Validate data structure  
        if not isinstance(data, dict):  
            raise ValueError("Invalid data structure: expected dictionary")  
          
        # Generate content sections  
        content_sections = []  
          
        for section_name, section_data in data.items():  
            try:  
                section_html = generate_section_html(section_name, section_data)  
                if section_html:  
                    content_sections.append(section_html)  
            except Exception as e:  
                # Log error but continue processing other sections  
                error_section = f'<div class="error-section">Error processing section "{section_name}": {html.escape(str(e))}</div>'  
                content_sections.append(error_section)  
          
        # Combine all sections  
        final_content = '\n'.join(content_sections)  
          
        # Use simple string replacement instead of Template  
        html_template = get_html_template()  
          
        return html_template.replace('{{CONTENT}}', final_content).replace('{{TIMESTAMP}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  
          
    except Exception as e:  
        # Return error HTML if parsing fails completely  
        return generate_error_html(f"Failed to parse JSON data: {str(e)}")  
  
def sanitize_id(text):  
    """Sanitize text to be safe for use as HTML ID and JavaScript function parameter"""  
    # Remove or replace problematic characters  
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(text))  
    # Ensure it starts with a letter  
    if sanitized and not sanitized[0].isalpha():  
        sanitized = 'id_' + sanitized  
    return sanitized  
  
def generate_section_html(section_name, section_data):  
    """Generate HTML for a single section."""  
      
    if not isinstance(section_data, dict):  
        return f'<div class="error-section">Invalid section data for "{section_name}"</div>'  
      
    section_html = f'<h2>{html.escape(section_name.replace("_", " ").title())}</h2>'  
      
    # Process found entities  
    if 'found_entities' in section_data and isinstance(section_data['found_entities'], list):  
        section_html += '<div class="entity-section">'  
          
        for i, entity in enumerate(section_data['found_entities']):  
            try:  
                entity_html = generate_entity_html(entity, section_name, i)  
                section_html += entity_html  
            except Exception as e:  
                error_html = f'<div class="entity-error">Error processing entity {i}: {html.escape(str(e))}</div>'  
                section_html += error_html  
          
        section_html += '</div>'  
      
    # Process not found entities  
    if 'not_found_entities' in section_data and isinstance(section_data['not_found_entities'], list):  
        if section_data['not_found_entities']:  
            section_html += '<div class="not-found">'  
            section_html += '<div class="not-found-header">Entities Not Found</div>'  
              
            for entity in section_data['not_found_entities']:  
                entity_name = entity.get('entity_name', 'Unknown') if isinstance(entity, dict) else str(entity)  
                section_html += f'<div>• {html.escape(entity_name)}</div>'  
              
            section_html += '</div>'  
      
    return section_html  
  
def generate_entity_html(entity, section_name, index):  
    """Generate HTML for a single entity."""  
      
    if not isinstance(entity, dict):  
        return f'<div class="entity-error">Invalid entity data at index {index}</div>'  
      
    # Create safe IDs  
    safe_section_name = sanitize_id(section_name)  
    entity_id = f"{safe_section_name}_entity_{index}"  
    entity_name = html.escape(entity.get('entity_name', 'Unknown Entity'))  
      
    # Count values safely  
    value_count = calculate_value_count(entity)  
      
    # Start entity card - use proper event handler  
    entity_html = f'''  
    <div class="entity-card">  
        <div class="entity-header" onclick="toggleEntity('{entity_id}')">  
            <span>{entity_name}</span>  
            <div>  
                <span class="value-count">{value_count}</span>  
                <button class="toggle-btn" type="button">Show Details</button>  
            </div>  
        </div>  
        <div class="entity-content" id="{entity_id}">  
    '''  
      
    # Handle different entity value types  
    if 'aggregated_value' in entity:  
        entity_html += generate_aggregated_value_html(entity, entity_id)  
    elif 'values' in entity and isinstance(entity['values'], list):  
        entity_html += generate_multiple_values_html(entity, entity_id)  
    elif 'value' in entity:  
        entity_html += generate_single_value_html(entity, entity_id)  
    else:  
        entity_html += '<div class="no-value">No value data available</div>'  
      
    entity_html += '</div></div>'  
      
    return entity_html  
  
def calculate_value_count(entity):  
    """Safely calculate the number of values in an entity."""  
    try:  
        if 'value' in entity:  
            return 1  
        elif 'values' in entity and isinstance(entity['values'], list):  
            return len(entity['values'])  
        elif 'aggregated_value' in entity:  
            values = entity.get('values', [])  
            return len(values) if isinstance(values, list) else 1  
        else:  
            return 0  
    except:  
        return 0  
  
def generate_aggregated_value_html(entity, entity_id):  
    """Generate HTML for entities with aggregated values."""  
      
    formatted_value = format_text_content(str(entity['aggregated_value']))  
      
    html_parts = [f'''  
    <div class="main-value aggregated-value">  
        <strong>Aggregated Value:</strong><br>  
        <div class="formatted-content">  
            {formatted_value}  
        </div>  
    </div>  
    ''']  
      
    # Show individual values if available  
    if 'values' in entity and isinstance(entity['values'], list):  
        html_parts.append("<h4>Individual Values:</h4>")  
        for j, value_item in enumerate(entity['values']):  
            value_html = generate_value_item_html(value_item, entity_id, j)  
            html_parts.append(value_html)  
      
    return ''.join(html_parts)  
  
def generate_multiple_values_html(entity, entity_id):  
    """Generate HTML for entities with multiple values."""  
      
    html_parts = []  
    for j, value_item in enumerate(entity['values']):  
        value_html = generate_value_item_html(value_item, entity_id, j)  
        html_parts.append(value_html)  
      
    return ''.join(html_parts)  
  
def generate_single_value_html(entity, entity_id):  
    """Generate HTML for entities with a single value."""  
      
    metadata_id = f"{entity_id}_metadata"  
    metadata_html = format_metadata_safe(entity.get('metadata', {}))  
    formatted_value = format_text_content(str(entity['value']))  
      
    return f'''  
    <div class="main-value">  
        <div class="formatted-content">  
            {formatted_value}  
        </div>  
    </div>  
    <button class="show-metadata-btn" onclick="toggleMetadata('{metadata_id}')" type="button">Show Metadata</button>  
    <div class="metadata" id="{metadata_id}">  
        {metadata_html}  
    </div>  
    '''  
  
def generate_value_item_html(value_item, entity_id, index):  
    """Generate HTML for a single value item."""  
      
    if not isinstance(value_item, dict):  
        return f'<div class="entity-value">Invalid value data</div>'  
      
    metadata_id = f"{entity_id}_metadata_{index}"  
    formatted_value = format_text_content(str(value_item.get('value', 'No value')))  
    metadata_html = format_metadata_safe(value_item.get('metadata', {}))  
      
    return f'''  
    <div class="entity-value">  
        <div class="formatted-content">  
            {formatted_value}  
        </div>  
        <button class="show-metadata-btn" onclick="toggleMetadata('{metadata_id}')" type="button">Show Metadata</button>  
        <div class="metadata" id="{metadata_id}">  
            {metadata_html}  
        </div>  
    </div>  
    '''  
  
def format_metadata_safe(metadata):  
    """Format metadata dictionary into HTML with error handling."""  
      
    if not isinstance(metadata, dict):  
        return f'<div class="metadata-item">Invalid metadata: {html.escape(str(metadata))}</div>'  
      
    if not metadata:  
        return '<div class="metadata-item">No metadata available</div>'  
      
    html_parts = []  
    for key, value in metadata.items():  
        try:  
            key_display = html.escape(str(key).replace("_", " ").title())  
              
            if key == 'created_at':  
                # Format datetime safely  
                try:  
                    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))  
                    value_display = dt.strftime('%Y-%m-%d %H:%M:%S')  
                except:  
                    value_display = html.escape(str(value))  
            else:  
                value_display = html.escape(str(value))  
              
            html_parts.append(f'<div class="metadata-item"><strong>{key_display}:</strong> {value_display}</div>')  
              
        except Exception as e:  
            html_parts.append(f'<div class="metadata-item">Error formatting {key}: {html.escape(str(e))}</div>')  
      
    return ''.join(html_parts)  
  
def get_html_template():  
    """Return the HTML template as a string with enhanced CSS for formatted content."""  
      
    return '''<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <meta name="viewport" content="width=device-width, initial-scale=1.0">  
    <title>MDT Report</title>  
    <style>  
        body {  
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;  
            line-height: 1.6;  
            color: #333;  
            max-width: 1200px;  
            margin: 0 auto;  
            padding: 20px;  
            background-color: #f5f5f5;  
        }  
          
        .container {  
            background-color: white;  
            border-radius: 8px;  
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);  
            padding: 30px;  
        }  
          
        h1 {  
            color: #2c3e50;  
            border-bottom: 3px solid #3498db;  
            padding-bottom: 10px;  
            margin-bottom: 30px;  
        }  
          
        h2 {  
            color: #34495e;  
            margin-top: 30px;  
            margin-bottom: 20px;  
            padding: 10px;  
            background-color: #ecf0f1;  
            border-left: 4px solid #3498db;  
        }  
          
        .entity-section {  
            margin-bottom: 30px;  
            border: 1px solid #ddd;  
            border-radius: 5px;  
            overflow: hidden;  
        }  
          
        .entity-card {  
            margin-bottom: 15px;  
            border: 1px solid #e0e0e0;  
            border-radius: 5px;  
            background-color: #fafafa;  
        }  
          
        .entity-header {  
            background-color: #3498db;  
            color: white;  
            padding: 15px;  
            font-weight: bold;  
            cursor: pointer;  
            display: flex;  
            justify-content: space-between;  
            align-items: center;  
        }  
          
        .entity-header:hover {  
            background-color: #2980b9;  
        }  
          
        .toggle-btn {  
            background: none;  
            border: none;  
            color: white;  
            font-size: 14px;  
            cursor: pointer;  
            padding: 5px 10px;  
            border-radius: 3px;  
            background-color: rgba(255,255,255,0.2);  
        }  
          
        .entity-content {  
            padding: 15px;  
            display: none;  
        }  
          
        .entity-content.show {  
            display: block;  
        }  
          
        .entity-value {  
            background-color: white;  
            border: 1px solid #ddd;  
            border-radius: 3px;  
            margin-bottom: 10px;  
            padding: 10px;  
        }  
          
        .main-value {  
            font-weight: bold;  
            color: #2c3e50;  
            margin-bottom: 10px;  
            padding: 15px;  
            background-color: #e8f4fd;  
            border-left: 4px solid #3498db;  
        }  
          
        .aggregated-value {  
            background-color: #e8f8f5;  
            border-left: 4px solid #27ae60;  
            font-weight: bold;  
        }  
          
        /* Formatted content styles */  
        .formatted-content {  
            margin-top: 10px;  
            line-height: 1.8;  
        }  
          
        .formatted-content .main-list {  
            margin: 15px 0;  
            padding-left: 20px;  
        }  
          
        .formatted-content .main-item {  
            margin-bottom: 15px;  
            padding: 8px;  
            background-color: rgba(52, 152, 219, 0.1);  
            border-left: 3px solid #3498db;  
            border-radius: 4px;  
        }  
          
        .formatted-content .sub-list {  
            margin: 8px 0 8px 20px;  
            padding-left: 15px;  
        }  
          
        .formatted-content .sub-item {  
            margin-bottom: 8px;  
            padding: 5px;  
            background-color: rgba(46, 204, 113, 0.1);  
            border-left: 2px solid #27ae60;  
            border-radius: 3px;  
        }  
          
        .formatted-content .bullet-list {  
            margin: 10px 0;  
            padding-left: 20px;  
        }  
          
        .formatted-content .bullet-item {  
            margin-bottom: 8px;  
            padding: 5px;  
        }  
          
        .formatted-content .text-line {  
            margin: 8px 0;  
            text-align: justify;  
        }  
          
        .formatted-content strong {  
            color: #2c3e50;  
            font-weight: 600;  
        }  
          
        .formatted-content em {  
            color: #34495e;  
            font-style: italic;  
        }  
          
        .metadata {  
            background-color: #f8f9fa;  
            border-top: 1px solid #e9ecef;  
            padding: 8px;  
            font-size: 12px;  
            color: #6c757d;  
            display: none;  
        }  
          
        .metadata.show {  
            display: block;  
        }  
          
        .metadata-item {  
            margin-bottom: 5px;  
        }  
          
        .not-found {  
            background-color: #fff3cd;  
            border: 1px solid #ffeaa7;  
            border-radius: 5px;  
            padding: 10px;  
            margin-bottom: 10px;  
        }  
          
        .not-found-header {  
            background-color: #f39c12;  
            color: white;  
            padding: 10px;  
            font-weight: bold;  
            margin: -10px -10px 10px -10px;  
        }  
          
        .value-count {  
            background-color: #e74c3c;  
            color: white;  
            border-radius: 50%;  
            padding: 2px 6px;  
            font-size: 12px;  
            margin-left: 10px;  
        }  
          
        .show-metadata-btn {  
            background-color: #6c757d;  
            color: white;  
            border: none;  
            padding: 3px 8px;  
            border-radius: 3px;  
            font-size: 11px;  
            cursor: pointer;  
            margin-top: 5px;  
        }  
          
        .show-metadata-btn:hover {  
            background-color: #5a6268;  
        }  
          
        .error-section {  
            background-color: #f8d7da;  
            color: #721c24;  
            border: 1px solid #f5c6cb;  
            border-radius: 5px;  
            padding: 10px;  
            margin: 10px 0;  
        }  
          
        .entity-error {  
            background-color: #f8d7da;  
            color: #721c24;  
            border: 1px solid #f5c6cb;  
            border-radius: 3px;  
            padding: 8px;  
            margin: 5px 0;  
        }  
          
        .no-value {  
            background-color: #fff3cd;  
            color: #856404;  
            border: 1px solid #ffeaa7;  
            border-radius: 3px;  
            padding: 8px;  
            margin: 5px 0;  
        }  
          
        .timestamp {  
            text-align: right;  
            font-size: 12px;  
            color: #6c757d;  
            margin-top: 20px;  
            padding-top: 10px;  
            border-top: 1px solid #e9ecef;  
        }  
    </style>  
</head>  
<body>  
    <div class="container">  
        <h1>MDT Report</h1>  
        {{CONTENT}}  
        <div class="timestamp">Generated on: {{TIMESTAMP}}</div>  
    </div>  
      
    <script>  
        function toggleEntity(entityId) {  
            try {  
                const content = document.getElementById(entityId);  
                const header = document.querySelector('[onclick*="' + entityId + '"]');  
                const btn = header ? header.querySelector('.toggle-btn') : null;  
                  
                if (content && btn) {  
                    if (content.classList.contains('show')) {  
                        content.classList.remove('show');  
                        btn.textContent = 'Show Details';  
                    } else {  
                        content.classList.add('show');  
                        btn.textContent = 'Hide Details';  
                    }  
                }  
            } catch (error) {  
                console.error('Error in toggleEntity:', error, 'EntityId:', entityId);  
            }  
        }  
          
        function toggleMetadata(metadataId) {  
            try {  
                const metadata = document.getElementById(metadataId);  
                const btn = document.querySelector('[onclick*="' + metadataId + '"]');  
                  
                if (metadata && btn) {  
                    if (metadata.classList.contains('show')) {  
                        metadata.classList.remove('show');  
                        btn.textContent = 'Show Metadata';  
                    } else {  
                        metadata.classList.add('show');  
                        btn.textContent = 'Hide Metadata';  
                    }  
                }  
            } catch (error) {  
                console.error('Error in toggleMetadata:', error, 'MetadataId:', metadataId);  
            }  
        }  
          
        // Debug function to check if functions are loaded  
        console.log('JavaScript functions loaded:', typeof toggleEntity, typeof toggleMetadata);  
    </script>  
</body>  
</html>'''  
  
def generate_error_html(error_message):  
    """Generate HTML for error cases."""  
      
    return f'''<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <title>Processing Error</title>  
    <style>  
        body {{ font-family: Arial, sans-serif; margin: 20px; }}  
        .error {{   
            background: #f8d7da;   
            border: 1px solid #f5c6cb;   
            color: #721c24;   
            padding: 20px;   
            border-radius: 8px;   
        }}  
    </style>  
</head>  
<body>  
    <div class="error">  
        <h2>❌ Processing Error</h2>  
        <p>{html.escape(error_message)}</p>  
    </div>  
</body>  
</html>'''  
  
# Test function  
def test_html_generation():  
    """Test function with your JSON data"""  
      
    # Load your test.json file  
    try:  
        with open('test.json', 'r', encoding='utf-8') as f:  
            json_data = json.load(f)  
          
        print("🔄 Generating formatted HTML...")  
        html_content = parse_json_to_html(json_data)  
          
        with open('formatted_test_output.html', 'w', encoding='utf-8') as f:  
            f.write(html_content)  
          
        print("✅ Formatted HTML generated successfully!")  
        print("📄 Output saved to: formatted_test_output.html")  
        print(f"📊 HTML size: {len(html_content):,} characters")  
          
        return html_content  
          
    except Exception as e:  
        print(f"❌ Error: {e}")  
        import traceback  
        traceback.print_exc()  
  
if __name__ == "__main__":  
    test_html_generation()  
