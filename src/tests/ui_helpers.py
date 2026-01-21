import streamlit as st  
from typing import List, Dict, Any  
import time    



def generate_error_html(error_message: str) -> str:  
    """Generate HTML for error cases"""  
    return f"""  
    <!DOCTYPE html>  
    <html>  
    <head>  
        <title>Processing Error</title>  
        <style>  
            body {{ font-family: Arial, sans-serif; margin: 20px; }}  
            .error {{ background: #fff5f5; border: 1px solid #feb2b2; color: #c53030; padding: 20px; border-radius: 8px; }}  
        </style>  
    </head>  
    <body>  
        <div class="error">  
            <h2>❌ Processing Error</h2>  
            <p>{error_message}</p>  
        </div>  
    </body>  
    </html>  
    """  




import json  
import html  
from datetime import datetime  
  
def json_to_pdf(json_data) -> bytes:  
    """Convert JSON data directly to PDF, showing only essential entity information"""  
    try:  
        from playwright.sync_api import sync_playwright  
          
        # Parse JSON if it's a string  
        if isinstance(json_data, str):  
            data = json.loads(json_data)  
        else:  
            data = json_data  
          
        # Generate clean HTML content  
        html_content = generate_clean_html(data)  
          
        with sync_playwright() as p:  
            browser = p.chromium.launch(headless=True)  
            page = browser.new_page()  
            page.set_content(html_content)  
            page.wait_for_load_state('networkidle')  
              
            # Generate PDF  
            pdf_bytes = page.pdf(  
                format='A4',  
                margin={  
                    'top': '0.75in',  
                    'right': '0.75in',  
                    'bottom': '0.75in',  
                    'left': '0.75in'  
                },  
                print_background=True  
            )  
              
            browser.close()  
            return pdf_bytes  
              
    except ImportError:  
        print("playwright not installed. Run: pip install playwright && playwright install")  
        return None  
    except Exception as e:  
        print(f"Error converting to PDF: {str(e)}")  
        return None  
  
def generate_clean_html(data):  
    """Generate clean HTML focusing only on entity names and their primary values"""  
      
    # Handle both list and dict formats  
    if isinstance(data, list):  
        entities = data  
    else:  
        entities = []  
        for section_name, section_data in data.items():  
            if isinstance(section_data, dict) and 'found_entities' in section_data:  
                entities.extend(section_data['found_entities'])  
      
    # Generate entity cards  
    entity_cards = []  
    for entity in entities:  
        if isinstance(entity, dict) and 'entity_name' in entity:  
            card_html = generate_entity_card(entity)  
            entity_cards.append(card_html)  
      
    # Create complete HTML  
    content = '\n'.join(entity_cards)  
      
    html_template = f'''<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <meta name="viewport" content="width=device-width, initial-scale=1.0">  
    <title>MDT Report</title>  
    <style>  
        body {{  
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;  
            line-height: 1.4;  
            color: #333;  
            max-width: 1000px;  
            margin: 0 auto;  
            padding: 20px;  
            background-color: #f8f9fa;  
        }}  
          
        .container {{  
            background-color: white;  
            border-radius: 8px;  
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);  
            padding: 30px;  
        }}  
          
        h1 {{  
            color: #2c3e50;  
            border-bottom: 3px solid #3498db;  
            padding-bottom: 15px;  
            margin-bottom: 30px;  
            font-size: 28px;  
        }}  
          
        .entity-card {{  
            margin-bottom: 25px;  
            border: 1px solid #e0e0e0;  
            border-radius: 8px;  
            overflow: hidden;  
            background-color: #ffffff;  
        }}  
          
        .entity-header {{  
            background: linear-gradient(135deg, #3498db, #2980b9);  
            color: white;  
            padding: 15px 20px;  
            font-weight: 600;  
            font-size: 16px;  
        }}  
          
        .entity-content {{  
            padding: 20px;  
        }}  
          
        .primary-value {{  
            background-color: #f8f9fa;  
            border-left: 4px solid #28a745;  
            padding: 15px;  
            margin-bottom: 15px;  
            border-radius: 4px;  
        }}  
          
        .aggregated-label {{  
            color: #28a745;  
            font-weight: 600;  
            font-size: 14px;  
            margin-bottom: 8px;  
        }}  
          
        .values-label {{  
            color: #6c757d;  
            font-weight: 600;  
            font-size: 14px;  
            margin-bottom: 8px;  
        }}  
          
        .value-text {{  
            font-size: 14px;  
            line-height: 1.6;  
            color: #2c3e50;  
        }}  
          
        .value-list {{  
            max-height: 300px;  
            overflow-y: auto;  
            border: 1px solid #e9ecef;  
            border-radius: 4px;  
            background-color: #ffffff;  
        }}  
          
        .value-item {{  
            padding: 10px 15px;  
            border-bottom: 1px solid #f1f3f4;  
        }}  
          
        .value-item:last-child {{  
            border-bottom: none;  
        }}  
          
        .value-item:nth-child(even) {{  
            background-color: #f8f9fa;  
        }}  
          
        .no-value {{  
            color: #6c757d;  
            font-style: italic;  
            padding: 15px;  
            text-align: center;  
            background-color: #f8f9fa;  
            border-radius: 4px;  
        }}  
          
        .timestamp {{  
            text-align: right;  
            font-size: 12px;  
            color: #6c757d;  
            margin-top: 30px;  
            padding-top: 15px;  
            border-top: 1px solid #e9ecef;  
        }}  
          
        .value-count {{  
            background-color: #dc3545;  
            color: white;  
            border-radius: 12px;  
            padding: 2px 8px;  
            font-size: 12px;  
            font-weight: 500;  
            margin-left: 10px;  
        }}  
    </style>  
</head>  
<body>  
    <div class="container">  
        <h1>📋 Medical Report</h1>  
        {content}  
        <div class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>  
    </div>  
</body>  
</html>'''  
      
    return html_template  
  
def generate_entity_card(entity):  
    """Generate HTML card for a single entity"""  
      
    entity_name = html.escape(entity.get('entity_name', 'Unknown Entity'))  
      
    # Check if we have aggregated value  
    if 'aggregated_value' in entity and entity['aggregated_value']:  
        # Show aggregated value as primary  
        aggregated_value = clean_and_format_text(entity['aggregated_value'])  
        content = f'''  
        <div class="primary-value">  
            <div class="aggregated-label">📊 Aggregated Summary</div>  
            <div class="value-text">{aggregated_value}</div>  
        </div>  
        '''  
          
        # Optionally show count of individual values  
        values = entity.get('values', [])  
        if values and len(values) > 1:  
            content += f'<div class="values-label">📈 Based on {len(values)} individual entries</div>'  
              
    elif 'values' in entity and entity['values']:  
        # Show list of values  
        values = entity['values']  
        if len(values) == 1:  
            # Single value - show prominently  
            value_text = clean_and_format_text(values[0].get('value', 'No value'))  
            content = f'''  
            <div class="primary-value">  
                <div class="value-text">{value_text}</div>  
            </div>  
            '''  
        else:  
            # Multiple values - show in list  
            value_items = []  
            for i, value_item in enumerate(values[:10]):  # Limit to first 10 values  
                value_text = clean_and_format_text(value_item.get('value', 'No value'))  
                value_items.append(f'<div class="value-item">{value_text}</div>')  
              
            remaining = len(values) - 10  
            if remaining > 0:  
                value_items.append(f'<div class="value-item"><em>... and {remaining} more entries</em></div>')  
              
            content = f'''  
            <div class="values-label">📋 Multiple Values ({len(values)} total)</div>  
            <div class="value-list">  
                {''.join(value_items)}  
            </div>  
            '''  
              
    elif 'value' in entity:  
        # Single value field  
        value_text = clean_and_format_text(entity['value'])  
        content = f'''  
        <div class="primary-value">  
            <div class="value-text">{value_text}</div>  
        </div>  
        '''  
    else:  
        # No value available  
        content = '<div class="no-value">No value data available</div>'  
      
    # Count total values for display  
    value_count = 0  
    if 'values' in entity:  
        value_count = len(entity['values'])  
    elif 'value' in entity:  
        value_count = 1  
      
    count_display = f'<span class="value-count">{value_count}</span>' if value_count > 0 else ''  
      
    return f'''  
    <div class="entity-card">  
        <div class="entity-header">  
            {entity_name}  
            {count_display}  
        </div>  
        <div class="entity-content">  
            {content}  
        </div>  
    </div>  
    '''  
  
def clean_and_format_text(text):  
    """Clean and format text for better readability"""  
    if not text:  
        return "No content"  
      
    # Convert to string and escape HTML  
    text = html.escape(str(text))  
      
    # Limit length for very long texts  
    if len(text) > 1000:  
        text = text[:997] + "..."  
      
    # Basic formatting - convert line breaks to proper spacing  
    text = text.replace('\n', '<br>')  
      
    return text  
  

def display_results(parsing_results: List[Dict[str, Any]], html_result: str,  
                   successful_parses: int, total_chars: int, total_words: int, output_json):  
    """Display the processing results in Streamlit"""  
      
    st.markdown("---")  
    st.subheader("📊 Results Summary")  
      
    # Display metrics  
    col1, col2, col3, col4 = st.columns(4)  
    with col1:  
        st.metric("Documents Processed", f"{successful_parses}/{len(parsing_results)}")  
    with col2:  
        st.metric("Total Characters", f"{total_chars:,}")  
    with col3:  
        st.metric("Total Words", f"{total_words:,}")  
    with col4:  
        st.metric("Success Rate", f"{(successful_parses/len(parsing_results)*100):.1f}%")  
      
    # Display detailed results  
    if html_result:  
        st.subheader("📄 MDT Report Results")  
        st.components.v1.html(html_result, height=600, scrolling=True)  
          
        # Download buttons with unique keys to prevent conflicts  
        timestamp = int(time.time())  
        col1, col2 = st.columns(2)  
          
        with col1:  
            st.download_button(  
                label="💾 Download HTML Report",  
                data=html_result,  
                file_name=f"mdt_report_{time.strftime('%Y%m%d_%H%M%S')}.html",  
                mime="text/html",  
                key=f"html_download_{timestamp}"  
            )  
          
        with col2:  
            if st.button("📄 Generate PDF", key=f"pdf_gen_{timestamp}"):  
                with st.spinner("Converting to PDF..."):  
                    print(parsing_results)
                    pdf_bytes = json_to_pdf( output_json  )  
                    if pdf_bytes:  
                        st.download_button(  
                            label="💾 Download PDF Report",  
                            data=pdf_bytes,  
                            file_name=f"mdt_report_{time.strftime('%Y%m%d_%H%M%S')}.pdf",  
                            mime="application/pdf",  
                            key=f"pdf_download_{timestamp}"  
                        )  
    else:  
        st.warning("⚠️ No MDT report generated")  
