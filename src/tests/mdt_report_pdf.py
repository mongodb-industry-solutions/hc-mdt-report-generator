import json          
from reportlab.lib.pagesizes import letter, A4          
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak          
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle          
from reportlab.lib.units import inch          
from reportlab.lib.colors import HexColor          
from typing import Dict, List, Any, Union          
import os          
from datetime import datetime          
      
class JSONToPDFConverter:          
    """          
    A library to convert JSON data to nicely formatted PDF files.          
              
    The PDF will display entity names as headers with their corresponding values          
    formatted as readable text below.          
    """          
              
    def __init__(self, output_filename: str = None):          
        """          
        Initialize the converter.          
                  
        Args:          
            output_filename (str): Name of the output PDF file. If None, uses timestamp.          
        """          
        if output_filename is None:          
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")          
            output_filename = f"extracted_entities_{timestamp}.pdf"          
                  
        self.output_filename = output_filename          
        self.styles = self._create_styles()          
              
        # Predefined field order      
        self.FIELD_ORDER = [      
            "NumdosGR",      
            "Nom de naissance",      
            "Prénom",      
            "Sexe",      
            "Date de naissance",      
            "Antécédents familiaux",      
            "Adresse postale",      
            "Adresse électronique",      
            "Hôpital",      
            "Antécédents",      
            "Diagnostiqué le",      
            "Date de diagnostic",      
            "Localisation",      
            "Chimiothérapie(s) réalisée(s)",      
            "Type histologique",      
            "Radiothérapie réalisée",      
            "Métastases à distance",      
            "Chirurgie(s) réalisée(s)",      
            "État général (OMS)",      
            "Score G8",      
            "Antécédents personnels notables",      
            "Site demandeur",      
            "Spécialité(s) Sollicitée",      
            "Localisations du cancer",      
            "Commentaire tumeur primitive",      
            "Anomalie moléculaire",      
            "Métastatique",      
            "Site métastatique",      
            "CIM-O-3",      
            "Date de présentation",      
            "Motifs de présentation",      
            "Question asked to MDT Team",      
            "MDT Team Recommendation",      
            "Thérapie innovante",      
            "Traitement hors AMM",      
            "Inclusion dans un essai thérapeutique",      
            "Demande complément d'examen complémentaire",      
            "EVASAN"      
        ]      
              
        # Header mapping for each entity      
        self.ENTITY_HEADERS = {      
            # Nom section      
            "NumdosGR": "Nom",      
            "Nom de naissance": "Nom",      
            "Prénom": "Nom",      
            "Sexe": "Nom",      
            "Date de naissance": "Nom",      
            "Adresse postale": "Nom",      
            "Adresse électronique": "Nom",      
            "Hôpital": "Nom",      
            "Site demandeur": "Nom",      
                  
            # Rappel clinique section      
            "Antécédents": "Rappel clinique",      
            "Diagnostiqué le": "Rappel clinique",      
            "Date de diagnostic": "Rappel clinique",      
            "Localisation": "Rappel clinique",      
            "Chimiothérapie(s) réalisée(s)": "Rappel clinique",      
            "Types histologiques": "Rappel clinique",      
            "Radiothérapie réalisée": "Rappel clinique",      
            "Métastases à distance": "Rappel clinique",      
            "Chirurgie(s) réalisée(s)": "Rappel clinique",      
            "État général (OMS)": "Rappel clinique",      
            "Score G8": "Rappel clinique",      
            "Antécédents personnels notables": "Rappel clinique",      
            "Antécédents familiaux": "Rappel clinique",      
                  
            # Caracteristiques patients et tumorales section      
            "Spécialité(s) Sollicitée": "Caracteristiques patients et tumorales",      
            "Localisations du cancer": "Caracteristiques patients et tumorales",      
            "Commentaire tumeur primitive": "Caracteristiques patients et tumorales",      
            "Anomalie moléculaire": "Caracteristiques patients et tumorales",      
            "Métastatique": "Caracteristiques patients et tumorales",      
            "Site métastatique": "Caracteristiques patients et tumorales",      
            "CIM-O-3": "Caracteristiques patients et tumorales",      
                  
            # Motif de présentation section      
            "Date de présentation": "Motif de présentation",      
            "Motifs de présentation": "Motif de présentation",      
            "Question asked to MDT Team": "Reason for presentation",      
            
            # MDT Team conclusion section      
            "MDT Team Recommendation": "MDT Team Conclusion",      
            "Innovative Therapy": "MDT Team Conclusion",      
            "Off-label Treatment": "MDT Team Conclusion",
            "Inclusion dans un essai thérapeutique": "Conclusion RCP",      
            "Demande complément d'examen complémentaire": "Conclusion RCP",      
            "EVASAN": "Conclusion RCP"      
        }      
                  
    def _create_styles(self) -> Dict:          
        """Create custom styles for the PDF."""          
        styles = getSampleStyleSheet()          
                  
        # Custom styles          
        custom_styles = {          
            'title': ParagraphStyle(          
                'CustomTitle',          
                parent=styles['Heading1'],          
                fontSize=18,          
                textColor=HexColor('#2E4057'),          
                spaceAfter=20,          
                alignment=1,  # Center alignment          
                fontName='Helvetica-Bold'          
            ),      
            'page_header': ParagraphStyle(      
                'PageHeader',      
                parent=styles['Heading1'],      
                fontSize=16,      
                textColor=HexColor('#1976D2'),      
                spaceBefore=30,      
                spaceAfter=20,      
                fontName='Helvetica-Bold',      
                borderWidth=2,      
                borderColor=HexColor('#1976D2'),      
                backColor=HexColor('#E3F2FD'),      
                leftIndent=15,      
                rightIndent=15,      
                borderPadding=10,      
                alignment=1  # Center alignment      
            ),      
            'entity_header': ParagraphStyle(          
                'EntityHeader',          
                parent=styles['Heading2'],          
                fontSize=14,          
                textColor=HexColor('#1976D2'),          
                spaceBefore=15,          
                spaceAfter=8,          
                fontName='Helvetica-Bold',          
                borderWidth=1,          
                borderColor=HexColor('#E3F2FD'),          
                backColor=HexColor('#F8F9FA'),          
                leftIndent=10,          
                rightIndent=10,          
                borderPadding=5          
            ),          
            'entity_content': ParagraphStyle(          
                'EntityContent',          
                parent=styles['Normal'],          
                fontSize=11,          
                textColor=HexColor('#424242'),          
                spaceAfter=10,          
                leftIndent=20,          
                rightIndent=10,          
                leading=14,          
                fontName='Helvetica'          
            ),          
            'section_header': ParagraphStyle(          
                'SectionHeader',          
                parent=styles['Heading1'],          
                fontSize=16,          
                textColor=HexColor('#D32F2F'),          
                spaceBefore=25,          
                spaceAfter=15,          
                fontName='Helvetica-Bold',          
                borderWidth=2,          
                borderColor=HexColor('#D32F2F'),          
                alignment=1          
            ),          
            'not_found': ParagraphStyle(          
                'NotFound',          
                parent=styles['Normal'],          
                fontSize=10,          
                textColor=HexColor('#757575'),          
                fontStyle='italic',          
                leftIndent=20,          
                spaceAfter=5          
            )          
        }          
                  
        return custom_styles          
          
    def _reorder_entities(self, entities: List[Dict]) -> List[Dict]:      
        """      
        Reorder entities according to predefined field order while preserving original order.      
              
        Args:      
            entities (list): List of entity dictionaries      
                  
        Returns:      
            list: Reordered list of entities      
        """      
        if not entities:      
            return entities      
                  
        # Create a mapping of entity names to their data      
        entity_map = {}      
        original_order = []      
        unmatched_entities = []      
              
        for entity in entities:      
            if isinstance(entity, dict):      
                entity_name = entity.get('entity_name', 'Unknown Entity')      
                entity_map[entity_name] = entity      
                original_order.append(entity_name)      
              
        # First, add entities in predefined order (if they exist)      
        ordered_entities = []      
        processed_entities = set()      
              
        for field_name in self.FIELD_ORDER:      
            if field_name in entity_map:      
                ordered_entities.append(entity_map[field_name])      
                processed_entities.add(field_name)      
              
        # Then, add remaining entities in their original order      
        for entity_name in original_order:      
            if entity_name not in processed_entities:      
                unmatched_entities.append(entity_name)      
                ordered_entities.append(entity_map[entity_name])      
              
        # Print warnings for unmatched entities      
        if unmatched_entities:      
            print(f"⚠️  WARNING: The following entities were not found in the predefined order:")      
            for entity_name in unmatched_entities:      
                print(f"   - '{entity_name}'")      
            print(f"   These entities have been placed after the predefined ones, maintaining their original order.\n")      
              
        return ordered_entities      
              
    def _format_text(self, text: str) -> str:          
        """          
        Format text to be more readable by handling special characters and formatting.          
                  
        Args:          
            text (str): Raw text to format          
                      
        Returns:          
            str: Formatted text          
        """          
        if not isinstance(text, str):          
            text = str(text)          
                  
        # Replace common separators with line breaks for better readability          
        text = text.replace(', ', '<br/>')          
        text = text.replace('\n', '<br/>')          
                  
        # Handle special characters that might break XML          
        text = text.replace('&', '&amp;')          
        text = text.replace('<', '&lt;')          
        text = text.replace('>', '&gt;')          
        text = text.replace('"', '&quot;')          
        text = text.replace("'", '&apos;')          
                  
        # Re-add our intentional line breaks          
        text = text.replace('&lt;br/&gt;', '<br/>')          
                  
        return text          
              

    def _get_entity_value(self, entity: Dict[str, Any]) -> str:          
        """          
        Extract the appropriate value from an entity following the priority:          
        1. aggregated_value (but only if it's not a raw dict string)  
        2. value          
        3. values (list)          
                
        Args:          
            entity (dict): Entity dictionary          
                    
        Returns:          
            str: Formatted value text          
        """          
        # Priority 1: aggregated_value (but check if it's a valid processed value)         
        if 'aggregated_value' in entity and entity['aggregated_value']:  
            agg_val = str(entity['aggregated_value']).strip()  
            # Check if aggregated_value looks like a raw dictionary string  
            if not (agg_val.startswith("{'") or agg_val.startswith('{"')):  
                return self._format_text(agg_val)  
            # If it looks like a raw dict, skip it and try other methods  
                
        # Priority 2: value          
        if 'value' in entity and entity['value']:          
            return self._format_text(str(entity['value']))          
                
        # Priority 3: values (list)          
        if 'values' in entity and entity['values']:          
            values_text = []          
            
            for item in entity['values']:          
                if isinstance(item, dict) and 'value' in item:          
                    values_text.append(str(item['value']))          
                else:          
                    values_text.append(str(item))          
                    
            if values_text:          
                return self._format_text('<br/>'.join(values_text))          
                
        # Fallback: if aggregated_value exists but looks like raw dict, try to extract from it  
        if 'aggregated_value' in entity and entity['aggregated_value']:  
            agg_val = str(entity['aggregated_value']).strip()  
            if agg_val.startswith("{'") and "'value':" in agg_val:  
                # Try to extract the value from the string representation  
                try:  
                    # Simple regex to extract value from string like "{'value': 'C80.9', ...}"  
                    import re  
                    match = re.search(r"'value':\s*'([^']*)'", agg_val)  
                    if match:  
                        return self._format_text(match.group(1))  
                except:  
                    pass  
        
        return "No value available"          



    def _group_entities_by_header(self, entities: List[Dict]) -> Dict[str, List[Dict]]:  
        """  
        Group entities by their header sections based on ENTITY_HEADERS mapping.  
          
        Args:  
            entities (list): List of entity dictionaries  
              
        Returns:  
            dict: Dictionary with headers as keys and lists of entities as values  
        """  
        grouped_entities = {}  
          
        for entity in entities:  
            if isinstance(entity, dict):  
                entity_name = entity.get('entity_name', 'Unknown Entity')  
                header = self.ENTITY_HEADERS.get(entity_name, "Autres informations")  
                  
                if header not in grouped_entities:  
                    grouped_entities[header] = []  
                grouped_entities[header].append(entity)  
          
        return grouped_entities  
              
    def _process_entities_section(self, entities: List[Dict], story: List):          
        """          
        Process a section of entities and add them to the story, grouped by headers.          
                  
        Args:          
            entities (list): List of entity dictionaries          
            story (list): PDF story elements list          
        """          
        if not entities:          
            return          
              
        # Reorder entities according to predefined order      
        ordered_entities = self._reorder_entities(entities)      
          
        # Group entities by their headers  
        grouped_entities = self._group_entities_by_header(ordered_entities)  
          
        # Define the order of headers to appear in the PDF  
        header_order = [  
            "Nom",  
            "Rappel clinique",   
            "Caracteristiques patients et tumorales",  
            "Motif de présentation",  
            "Conclusion RCP",  
            "Autres informations"  
        ]  
          
        # Process each header group in order  
        for header in header_order:  
            if header in grouped_entities:  
                # Add page header  
                story.append(Paragraph(header, self.styles['page_header']))      
                story.append(Spacer(1, 15))  
                  
                # Process entities in this header group  
                for entity in grouped_entities[header]:  
                    entity_name = entity.get('entity_name', 'Unknown Entity')  
                      
                    # Add entity header          
                    story.append(Paragraph(entity_name, self.styles['entity_header']))          
                              
                    # Add entity content          
                    if 'entity_name' in entity:  # This is a found entity          
                        entity_value = self._get_entity_value(entity)          
                        story.append(Paragraph(entity_value, self.styles['entity_content']))          
                    else:  # This is a not found entity          
                        story.append(Paragraph("Not found in the documents", self.styles['not_found']))          
                              
                    story.append(Spacer(1, 8))  
                  
                # Add page break after each header section (except the last one)  
                if header != header_order[-1] and header_order.index(header) < len([h for h in header_order if h in grouped_entities]) - 1:  
                    story.append(PageBreak())  
              
    def convert_json_to_pdf(self, json_data: Union[str, Dict]) -> str:          
        """          
        Convert JSON data to a formatted PDF file.          
                  
        Args:          
            json_data (str or dict): JSON string or dictionary containing entity data          
                      
        Returns:          
            str: Path to the generated PDF file          
        """          
        # Parse JSON if string          
        if isinstance(json_data, str):          
            try:          
                data = json.loads(json_data)          
            except json.JSONDecodeError as e:          
                raise ValueError(f"Invalid JSON string: {e}")          
        else:          
            data = json_data          
                  
        # Create PDF document          
        doc = SimpleDocTemplate(          
            self.output_filename,          
            pagesize=A4,          
            rightMargin=72,          
            leftMargin=72,          
            topMargin=72,          
            bottomMargin=18          
        )          
                  
        # Build story          
        story = []          
                  
        # Add title          
        #story.append(Paragraph("Rapport de RCP", self.styles['title']))          
        story.append(Spacer(1, 20))          
                  
        # Collect all entities from all sections  
        all_entities = []  
          
        # Process all sections and collect entities  
        for section_key in ['first_match', 'multiple_match', 'aggregate_all_matches']:  
            if section_key in data:  
                section_data = data[section_key]  
                          
                # Process found entities          
                if 'found_entities' in section_data:          
                    entities_data = section_data['found_entities']          
                              
                    # Handle both list and dictionary formats          
                    if isinstance(entities_data, dict):          
                        # Convert numbered dictionary to list          
                        for key in sorted(entities_data.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):          
                            all_entities.append(entities_data[key])          
                    elif isinstance(entities_data, list):          
                        all_entities.extend(entities_data)          
                          
                # Process not found entities          
                if 'not_found_entities' in section_data:          
                    entities_data = section_data['not_found_entities']          
                              
                    # Handle both list and dictionary formats          
                    if isinstance(entities_data, dict):          
                        for key in sorted(entities_data.keys(), key=lambda x: int(x) if x.isdigit() else float('inf')):          
                            all_entities.append(entities_data[key])          
                    elif isinstance(entities_data, list):          
                        all_entities.extend(entities_data)          
  
        # Process all collected entities in one go  
        if all_entities:  
            self._process_entities_section(all_entities, story)  
                  
        # Build PDF          
        doc.build(story)          
                  
        return os.path.abspath(self.output_filename)          
          
# Convenience function for quick usage          
def create_pdf_from_json(json_data: Union[str, Dict], output_filename: str = None) -> str:          
    """          
    Convenience function to quickly create a PDF from JSON data.          
              
    Args:          
        json_data (str or dict): JSON string or dictionary containing entity data          
        output_filename (str): Name of the output PDF file          
                  
    Returns:          
        str: Path to the generated PDF file          
    """          
    converter = JSONToPDFConverter(output_filename)          
    return converter.convert_json_to_pdf(json_data)          
          
# Example usage          
if __name__ == "__main__":          
    # Sample JSON data (your provided example)          
    sample_json = """{          
        "first_match": {          
            "found_entities": {          
                "0": {          
                    "entity_name": "NumdosGR",          
                    "value": "14H06677, 19H10116",          
                    "metadata": {          
                        "filename": "GR-AutresK-QUAL-20246000be8a04c5831890a8520772d2741035511e5bcf3bda1c57db384728ad26d7_mbiolims.xml",          
                        "created_at": "",          
                        "section_id": "section_1",          
                        "page_id": 1          
                    }          
                },          
                "1": {          
                    "entity_name": "Site demandeur",          
                    "value": "CRB Recherche ancillaire",          
                    "metadata": {          
                        "filename": "GR-AutresK-QUAL-20246000be8a04c5831890a8520772d2741035511e5bcf3bda1c57db384728ad26d7_mbiolims.xml",          
                        "created_at": "",          
                        "section_id": "section_1",          
                        "page_id": 1          
                    }          
                }          
            },          
            "not_found_entities": {          
                "0": {          
                    "entity_name": "Nom de naissance"          
                },          
                "1": {          
                    "entity_name": "Adresse postale"          
                }          
            }          
        }          
    }"""          
              
    # Create PDF          
    try:          
        pdf_path = create_pdf_from_json(sample_json, "example_entities.pdf")          
        print(f"PDF created successfully: {pdf_path}")          
    except Exception as e:          
        print(f"Error creating PDF: {e}")  
