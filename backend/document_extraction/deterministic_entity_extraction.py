# entities_config.py  
from datetime import datetime  
import re  
  
ENTITY_MAPPINGS = {  
    # XPath mappings for direct XML extraction  
    "xpath_mappings": {  
        # Patient Identification  
        "NumdosGR": "//patientRole/id/@extension",  
        "patient_id_root": "//patientRole/id/@root",  
          
        # Hospital/Institution  
        "Hopital": "//representedCustodianOrganization/name/text()",  
        "institution_id": "//representedCustodianOrganization/id/@root",  
          
        # Medical Codes  
        "CIM-O-3": "//codeCim10/text()",  
        "diagnostic_principal": "//diagnosticPrincipal/codeCim10/text()",  
        "diagnostic_relie": "//diagnosticRelie/codeCim10/text()",  
        "diagnostic_significatif": "//diagnosticSignificatif/codeCim10/text()",  
          
        # Medical Acts  
        "actes_medicaux": "//codeActe/text()",  
        "actes_phases": "//codePhase/text()",  
        "actes_activites": "//codeActivite/text()",  
        "actes_quantites": "//quantite/text()",  
          
        # Dates  
        "dates_realisation": "//dateRealisation/text()",  
        "dates_entree": "//entree/date/text()",  
        "dates_sortie": "//sortie/date/text()",  
        "date_production": "//dateHeureProduction/text()",  
          
        # Medical Units  
        "unite_medicale": "//uniteMedicale/code/text()",  
        "mode_entree": "//entree/@mode",  
        "mode_sortie": "//sortie/@mode",  
          
        # Document metadata  
        "periode_debut": "//periodeExercice/@dateDebut",  
        "periode_fin": "//periodeExercice/@dateFin",  
        "version_pmsi": "//evenementsPMSI/@version"  
    },  
      
    # ICD-10 code mappings with detailed information  
    "icd_mappings": {  
        # Cancer codes (C00-C97)  
        "C051": {  
            "location": "Palais dur",   
            "type": "Cancer",  
            "category": "Tumeur maligne",  
            "system": "Digestif",  
            "localisation_anatomique": "Cavité buccale"  
        },  
        "C052": {  
            "location": "Voile du palais",   
            "type": "Cancer",  
            "category": "Tumeur maligne",  
            "system": "Digestif"  
        },  
          
        # Treatment/Follow-up codes (Z00-Z99)  
        "Z5101": {  
            "type": "Radiothérapie",   
            "category": "Traitement",  
            "description": "Séance de radiothérapie",  
            "frequency": "Répétable"  
        },  
        "Z511": {  
            "type": "Chimiothérapie",   
            "category": "Traitement",  
            "description": "Séance de chimiothérapie pour tumeur",  
            "frequency": "Répétable"  
        },  
        "Z5100": {  
            "type": "Chimiothérapie",   
            "category": "Préparation traitement",  
            "description": "Préparation chimiothérapie"  
        },  
          
        # Complications/Comorbidities  
        "M720": {  
            "type": "Trouble fibroblastique",  
            "category": "Complication",  
            "system": "Musculo-squelettique"  
        },  
        "F171": {  
            "type": "Troubles mentaux liés au tabac",  
            "category": "Comorbidité",  
            "system": "Psychiatrique"  
        },  
        "F10240": {  
            "type": "Dépendance alcool avec intoxication",  
            "category": "Comorbidité",  
            "system": "Psychiatrique"  
        },  
        "F10241": {  
            "type": "Dépendance alcool avec delirium",  
            "category": "Comorbidité",  
            "system": "Psychiatrique"  
        },  
        "G408": {  
            "type": "Autres épilepsies",  
            "category": "Comorbidité",  
            "system": "Neurologique"  
        },  
        "H920": {  
            "type": "Otalgie",  
            "category": "Symptôme",  
            "system": "ORL"  
        },  
        "R633": {  
            "type": "Difficultés d'alimentation",  
            "category": "Symptôme",  
            "system": "Digestif"  
        },  
        "R13": {  
            "type": "Aphagie et dysphagie",  
            "category": "Symptôme",  
            "system": "Digestif"  
        },  
        "K132": {  
            "type": "Lésions muqueuse buccale",  
            "category": "Complication",  
            "system": "Digestif"  
        }  
    },  
      
    # Medical acts mappings (CCAM codes)  
    "act_mappings": {  
        "ZZNL050": {  
            "description": "Séance de radiothérapie",  
            "type": "Radiothérapie",  
            "category": "Traitement",  
            "specialty": "Oncologie radiothérapie"  
        },  
        "GEQE013": {  
            "description": "Consultation spécialisée",  
            "type": "Consultation",  
            "category": "Consultation",  
            "specialty": "Médecine générale"  
        },  
        "YYYY128": {  
            "description": "Supplément de surveillance",  
            "type": "Surveillance",  
            "category": "Monitoring"  
        },  
        "ZZMP015": {  
            "description": "Supplément pharmacie",  
            "type": "Pharmacie",  
            "category": "Médicament"  
        },  
        "ZZMP017": {  
            "description": "Supplément pharmacie spécialisée",  
            "type": "Pharmacie",  
            "category": "Médicament"  
        },  
        "ZZMK024": {  
            "description": "Supplément biologie",  
            "type": "Biologie",  
            "category": "Examens"  
        }  
    },  
      
    # Medical units mappings  
    "unit_mappings": {  
        "RTE": {  
            "name": "Radiothérapie",  
            "type": "Service technique",  
            "specialty": "Oncologie radiothérapie"  
        },  
        "IEL": {  
            "name": "Hospitalisation",  
            "type": "Service d'hospitalisation",  
            "specialty": "Oncologie médicale"  
        },  
        "PCA": {  
            "name": "Plateau technique",  
            "type": "Service technique",  
            "specialty": "Chirurgie"  
        }  
    },  
      
    # Field validation rules  
    "validation_rules": {  
        "NumdosGR": {  
            "pattern": r"GR-[\w-]+",  
            "required": True,  
            "description": "Identifiant patient unique"  
        },  
        "dates": {  
            "pattern": r"\d{4}-\d{2}-\d{2}",  
            "format": "%Y-%m-%d",  
            "required": False  
        },  
        "icd_codes": {  
            "pattern": r"[A-Z]\d{2,4}",  
            "required": True,  
            "validate_against": "icd_mappings"  
        }  
    }  
}  
  
# Helper functions for entity processing  
class EntityProcessor:  
    @staticmethod  
    def normalize_icd_code(code):  
        """Normalize ICD code format"""  
        if not code:  
            return None  
        return code.upper().strip()  
      
    @staticmethod  
    def parse_date(date_str):  
        """Parse date string to datetime object"""  
        if not date_str:  
            return None  
              
        # Handle different date formats  
        formats = [  
            "%Y-%m-%d %H:%M:%S",  
            "%Y-%m-%d",  
            "%Y%m%d%H%M%S%z",  
        ]  
          
        for fmt in formats:  
            try:  
                return datetime.strptime(date_str.split('+')[0], fmt)  
            except ValueError:  
                continue  
        return None  
      
    @staticmethod  
    def categorize_diagnosis(icd_code):  
        """Categorize diagnosis based on ICD code"""  
        if not icd_code:  
            return "Unknown"  
              
        code = icd_code.upper()  
        if code.startswith('C'):  
            return "Cancer"  
        elif code.startswith('Z'):  
            return "Traitement/Suivi"  
        elif code.startswith('F'):  
            return "Troubles psychiatriques"  
        elif code.startswith('M'):  
            return "Système musculo-squelettique"  
        else:  
            return "Autre"  
      
    @staticmethod  
    def validate_entity(entity_type, value):  
        """Validate entity value against rules"""  
        rules = ENTITY_MAPPINGS.get("validation_rules", {}).get(entity_type, {})  
          
        if rules.get("required") and not value:  
            return False, "Required field is missing"  
              
        pattern = rules.get("pattern")  
        if pattern and value:  
            if not re.match(pattern, str(value)):  
                return False, f"Value doesn't match pattern: {pattern}"  
          
        return True, "Valid"  
  
# Entity extraction priorities (for conflicting data)  
EXTRACTION_PRIORITIES = {  
    "diagnostic_principal": 1,  
    "diagnostic_relie": 2,  
    "diagnostic_significatif": 3  
}  
  
# Output format templates  
OUTPUT_TEMPLATES = {  
    "mongodb": {  
        "patient_identification": {  
            "numdos_gr": None,  
            "hopital": None,  
            "institution_id": None  
        },  
        "medical_information": {  
            "diagnostics": [],  
            "treatments": [],  
            "dates": [],  
            "medical_units": []  
        },  
        "metadata": {  
            "extraction_date": None,  
            "source_document": None,  
            "validation_status": None  
        }  
    },  
      
    "json_flat": {  
        "patient_id": None,  
        "hospital": None,  
        "primary_diagnosis": None,  
        "treatment_dates": [],  
        "medical_acts": []  
    }  
}  
