import logging      
from typing import Dict      
from datetime import datetime     
    
import xml.etree.ElementTree as ET      
import csv      
  


def process_pmsi_document(content: str) -> str:          
    """          
    Process PMSI document - called every time a PMSI doc is found, returns a plain version of the document with CCAM mapping          
    """          
          
    # Load CCAM mappings          
    ccam_mappings = {}          
    try:          
        with open('CCAM_V7810.csv', 'r', encoding='utf-8') as f:          
            reader = csv.DictReader(f)          
            for row in reader:          
                ccam_mappings[row['CODE']] = row['DESCRIPTION']          
        print(f"Loaded {len(ccam_mappings)} CCAM codes")          
    except FileNotFoundError:          
        print("CCAM file not found, will show codes only")          
              
    # Parse the XML content  
    root = ET.fromstring(content)          
      
    # 🔧 FIX: Define namespace  
    namespace = {'ns': 'urn:hl7-org:v3'}  
              
    # Extract all events - USE NAMESPACE          
    events = []          
              
    for event in root.findall('.//ns:evenementPMSI', namespace):          
        # Get basic info - SAFE EXTRACTION WITH NAMESPACE  
        venue_elem = event.find('ns:venue', namespace)      
        venue = venue_elem.attrib if venue_elem is not None else {}      
              
        rss_elem = event.find('.//ns:identifiantRSS/ns:emetteur', namespace)      
        rss_id = rss_elem.text if rss_elem is not None else "N/A"      
                  
        # Get dates - SAFE EXTRACTION WITH NAMESPACE  
        entree_elem = event.find('.//ns:entree/ns:date', namespace)      
        entree = entree_elem.text if entree_elem is not None else "N/A"      
              
        sortie_elem = event.find('.//ns:sortie/ns:date', namespace)      
        sortie = sortie_elem.text if sortie_elem is not None else "N/A"      
                  
        # Get diagnostics - SAFE EXTRACTION WITH NAMESPACE  
        diag_principal_elem = event.find('.//ns:diagnosticPrincipal/ns:codeCim10', namespace)      
        diag_principal = diag_principal_elem.text if diag_principal_elem is not None else "N/A"      
              
        diag_relie_elem = event.find('.//ns:diagnosticRelie/ns:codeCim10', namespace)      
        diag_relie = diag_relie_elem.text if diag_relie_elem is not None else "N/A"      
              
        diag_significatif_elem = event.find('.//ns:diagnosticSignificatif/ns:codeCim10', namespace)      
        diag_significatif = diag_significatif_elem.text if diag_significatif_elem is not None else "N/A"      
                  
        # Get acts with descriptions - SAFE EXTRACTION WITH NAMESPACE  
        acts = []          
        for acte in event.findall('.//ns:acte/ns:CCAM', namespace):          
            code_elem = acte.find('ns:codeActe', namespace)      
            code = code_elem.text if code_elem is not None else "N/A"      
                  
            date_elem = acte.find('ns:dateRealisation', namespace)      
            date = date_elem.text if date_elem is not None else "N/A"      
                  
            qty_elem = acte.find('ns:quantite', namespace)      
            qty = qty_elem.text if qty_elem is not None else "N/A"      
                  
            description = ccam_mappings.get(code, "Description not found") if code != "N/A" else "N/A"      
                      
            acts.append({          
                'code': code,          
                'description': description,          
                'date': date,          
                'quantite': qty          
            })          
                  
        # Build simple dict          
        events.append({          
            'rss_id': rss_id,          
            'entree': entree,          
            'sortie': sortie,          
            'etat': venue.get('etat', 'N/A'),          
            'facturable': venue.get('facturable', 'N/A'),          
            'diagnostic_principal': diag_principal,          
            'diagnostic_relie': diag_relie,          
            'diagnostic_significatif': diag_significatif,          
            'actes': acts          
        })          
      
    print(f"🔍 DEBUG: Found {len(events)} events after namespace fix")  
              
    # Build YAML-like output string      
    output_lines = []      
    for i, event in enumerate(events, 1):          
        output_lines.append(f"Event {i}:")          
        output_lines.append(f"  rss_id: {event['rss_id']}")          
        output_lines.append(f"  entree: {event['entree']}")          
        output_lines.append(f"  sortie: {event['sortie']}")          
        output_lines.append(f"  etat: {event['etat']}")          
        output_lines.append(f"  facturable: {event['facturable']}")          
        output_lines.append(f"  diagnostic_principal: {event['diagnostic_principal']}")          
        output_lines.append(f"  diagnostic_relie: {event['diagnostic_relie']}")          
        output_lines.append(f"  diagnostic_significatif: {event['diagnostic_significatif']}")          
        output_lines.append(f"  actes: {len(event['actes'])} act(s)")          
        for acte in event['actes']:          
            output_lines.append(f"    - code: {acte['code']}")          
            output_lines.append(f"      description: {acte['description']}")          
            output_lines.append(f"      date: {acte['date']}")          
            output_lines.append(f"      quantite: {acte['quantite']}")          
        output_lines.append("")  # Empty line between events      
    
    response = "\n".join(output_lines)      
    return response  
