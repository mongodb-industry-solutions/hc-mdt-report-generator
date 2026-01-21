"""
Document Extractor Prompts

Contains prompts used for extracting structured data from medical documents.
Each category has its own specialized prompt for extracting structured information.
"""

# Base system prompt for document extraction
SYSTEM_PROMPT = """You are an expert medical document analyzer specializing in French healthcare documentation.
Your task is to extract structured information from medical documents according to specific JSON schemas.
Always respond with valid JSON format only."""

# Common base JSON structure for all document types
BASE_JSON_STRUCTURE = """{{
  "metadata": {{
    "type_document": "{document_type}",
    "date_redaction": "YYYY-MM-DD",
    "redacteur": {{
      "nom": "string",
      "fonction": "string",
      "service": "string",
      "etablissement": "string"
    }}
  }},
  "patient": {{
    "identifiant": "string",
    "age": "number",
    "sexe": "M/F",
    "date_naissance": "YYYY-MM-DD ou null si anonymisé"
  }}
}}"""

# Common instructions for all document types
COMMON_INSTRUCTIONS = """INSTRUCTIONS:
- Extrayez toutes les informations disponibles dans le document
- Utilisez null pour les champs non trouvés
- Respectez strictement le format JSON fourni
- Pour les dates, utilisez le format YYYY-MM-DD
- Pour les heures, utilisez le format HH:MM
- Les listes vides doivent être représentées par []
- Les valeurs booléennes doivent être true/false, si vous ne les trouvez pas, utilisez null
- N'inventez JAMAIS des informations qui ne sont pas dans le document

RÉPONSE: Fournissez uniquement le JSON valide sans texte supplémentaire."""

# Hospitalization report specific JSON structure
HOSPITALIZATION_JSON_EXTENSION = """  "sejour": {{
    "dates": {{
      "entree": "YYYY-MM-DD",
      "sortie": "YYYY-MM-DD",
      "duree_jours": "number"
    }},
    "service": "string",
    "motif_hospitalisation": "string",
    "provenance": "string",
    "mode_sortie": "string",
    "destination_sortie": "string"
  }},
  "antecedents": {{
    "medicaux": [
      {{
        "pathologie": "string",
        "date": "YYYY ou null",
        "statut": "string"
      }}
    ],
    "chirurgicaux": [
      {{
        "intervention": "string",
        "date": "YYYY ou null"
      }}
    ],
    "familiaux": [
      {{
        "pathologie": "string",
        "lien_parente": "string",
        "age_survenue": "number ou null"
      }}
    ],
    "allergies": ["string"],
    "habitus": {{
      "tabac": "jamais/ancien/actuel",
      "alcool": "string",
      "autres": "string"
    }}
  }},
  "histoire_maladie": {{
    "chronologie": [
      {{
        "date": "YYYY-MM-DD",
        "evenement": "string",
        "details": "string"
      }}
    ],
    "symptomes_admission": ["string"],
    "evolution_recente": "string"
  }},
  "examens_cliniques": {{
    "entree": {{
      "etat_general": "string",
      "constantes": {{
        "poids": "number",
        "taille": "number",
        "temperature": "number",
        "tension_arterielle": "string",
        "frequence_cardiaque": "number",
        "saturation_o2": "number",
        "glasgow": "number ou null"
      }},
      "systemes": {{
        "cardiovasculaire": "string",
        "pulmonaire": "string",
        "abdominal": "string",
        "neurologique": "string",
        "autres": "string"
      }}
    }},
    "evolution": "string"
  }},
  "examens_complementaires": {{
    "biologie": [
      {{
        "date": "YYYY-MM-DD",
        "type": "string",
        "resultats": [
          {{
            "parametre": "string",
            "valeur": "string",
            "unite": "string",
            "norme": "string ou null",
            "interpretation": "normal/anormal/pathologique"
          }}
        ]
      }}
    ],
    "imagerie": [
      {{
        "date": "YYYY-MM-DD",
        "type": "string",
        "indication": "string",
        "resultats": "string",
        "conclusion": "string"
      }}
    ],
    "microbiologie": [
      {{
        "date": "YYYY-MM-DD",
        "type": "string",
        "germe": "string ou null",
        "antibiogramme": "string ou null"
      }}
    ],
    "autres": [
      {{
        "date": "YYYY-MM-DD",
        "type": "string",
        "resultats": "string"
      }}
    ]
  }},
  "diagnostics": {{
    "principal": "string",
    "secondaires": ["string"],
    "codes_cim10": ["string"],
    "evolution_diagnostique": "string"
  }},
  "traitements": {{
    "a_l_entree": [
      {{
        "medicament": "string",
        "posologie": "string",
        "indication": "string"
      }}
    ],
    "durant_sejour": [
      {{
        "medicament": "string",
        "posologie": "string",
        "indication": "string",
        "duree": "string",
        "modalite": "IV/PO/SC/IM"
      }}
    ],
    "de_sortie": [
      {{
        "medicament": "string",
        "posologie": "string",
        "duree": "string",
        "indication": "string",
        "modifications": "string"
      }}
    ],
    "non_medicamenteux": [
      {{
        "type": "string",
        "details": "string"
      }}
    ]
  }},
  "evolution_hospitalisation": {{
    "resume_global": "string",
    "complications": [
      {{
        "type": "string",
        "date": "YYYY-MM-DD",
        "prise_en_charge": "string"
      }}
    ],
    "procedures_interventions": [
      {{
        "date": "YYYY-MM-DD",
        "type": "string",
        "indication": "string",
        "operateur": "string ou null"
      }}
    ]
  }},
  "suivi_preconise": {{
    "surveillance": {{
      "frequence": "string",
      "parametres": ["string"],
      "duree": "string"
    }},
    "rendez_vous": [
      {{
        "specialite": "string",
        "delai": "string",
        "objectif": "string",
        "date_programmee": "YYYY-MM-DD ou null"
      }}
    ],
    "examens_controle": [
      {{
        "type": "string",
        "delai": "string",
        "indication": "string"
      }}
    ],
    "consignes_particulieres": ["string"]
  }},
  "informations_patient": {{
    "diagnostic_communique": "boolean",
    "pronostic_communique": "boolean",
    "informations_donnees": ["string"],
    "education_therapeutique": "string ou null"
  }},
  "aspects_sociaux": {{
    "autonomie": "string",
    "aide_domicile": "boolean",
    "personne_confiance": "boolean",
    "directives_anticipees": "boolean",
    "besoins_identifies": ["string"]
  }},
  "coordination_soins": {{
    "medecin_traitant": {{
      "nom": "string ou null",
      "coordonnees": "string ou null"
    }},
    "diffusion": ["string"],
    "transmissions_importantes": ["string"]
  }},
  "qualite_soins": {{
    "evenements_indesirables": "boolean",
    "infections_nosocomiales": "boolean",
    "germes_multiresistants": "boolean",
    "dispositifs_implantes": "boolean",
    "transfusions": "boolean"
  }}"""

# Surgical report specific JSON structure
SURGICAL_JSON_EXTENSION = """  "intervention": {{
    "nom": "string",
    "type": "string",
    "urgence": "boolean",
    "duree": "string",
    "chirurgien": "string",
    "service": "string",
    "date_operation": "YYYY-MM-DD"
  }}"""

# Imaging report specific JSON structure
IMAGING_JSON_EXTENSION = """  "examen": {{
    "type": "string",
    "indication": "string",
    "technique": "string",
    "resultats": "string",
    "conclusion": "string",
    "radiologue": "string",
    "date_examen": "YYYY-MM-DD"
  }}"""

# Consultation report specific JSON structure
CONSULTATION_JSON_EXTENSION = """  "consultation": {{
    "motif": "string",
    "examen_clinique": "string",
    "diagnostic": "string",
    "traitement": "string",
    "medecin": "string",
    "specialite": "string",
    "date_consultation": "YYYY-MM-DD"
  }}"""

# Lab results specific JSON structure
LAB_JSON_EXTENSION = """  "resultats": [
    {{
      "parametre": "string",
      "valeur": "string",
      "unite": "string",
      "norme": "string",
      "interpretation": "normal/anormal"
    }}
  ],
  "laboratoire": "string",
  "date_prelevement": "YYYY-MM-DD" """

# Prescription specific JSON structure
PRESCRIPTION_JSON_EXTENSION = """  "prescriptions": [
    {{
      "medicament": "string",
      "posologie": "string",
      "duree": "string",
      "indication": "string"
    }}
  ],
  "prescripteur": "string",
  "date_prescription": "YYYY-MM-DD" """

# Administrative coding specific JSON structure
ADMINISTRATIVE_JSON_EXTENSION = """  "codage": {{
    "diagnostic_principal": "string",
    "diagnostics_associes": ["string"],
    "actes": ["string"],
    "ghm": "string",
    "codeur": "string",
    "date_codage": "YYYY-MM-DD"
  }}"""

# Correspondence specific JSON structure
CORRESPONDENCE_JSON_EXTENSION = """  "correspondance": {{
    "objet": "string",
    "contenu": "string",
    "recommandations": ["string"],
    "suivi": "string",
    "expediteur": "string",
    "destinataire": "string",
    "date_redaction": "YYYY-MM-DD"
  }}"""

# Function to build complete JSON structure
def build_json_structure(document_type: str, extension: str) -> str:
    """Build complete JSON structure by combining base and extension"""
    base = BASE_JSON_STRUCTURE.format(document_type=document_type)
    # Remove the closing braces from base and add extension
    base_without_closing = base.rstrip('}}')
    return f"{base_without_closing},\n{extension}\n}}"

# Hospitalization report extraction prompt
HOSPITALIZATION_REPORT_PROMPT = """Analysez le compte rendu d'hospitalisation français fourni et extrayez les informations selon la structure JSON suivante. Pour chaque champ, si l'information n'est pas disponible, utilisez null.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Surgical report extraction prompt
SURGICAL_REPORT_PROMPT = """Analysez le compte rendu opératoire français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Imaging report extraction prompt
IMAGING_REPORT_PROMPT = """Analysez le compte rendu d'imagerie médicale français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Consultation report extraction prompt
CONSULTATION_REPORT_PROMPT = """Analysez le compte rendu de consultation français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Lab results extraction prompt
LAB_RESULTS_PROMPT = """Analysez les résultats d'examens biologiques français fournis et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Prescription extraction prompt
PRESCRIPTION_PROMPT = """Analysez le document de prescription français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Administrative coding extraction prompt
ADMINISTRATIVE_CODING_PROMPT = """Analysez le document administratif de codage français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}"""

# Correspondence extraction prompt
CORRESPONDENCE_PROMPT = """Analysez le courrier de liaison/correspondance médicale français fourni et extrayez les informations selon la structure JSON suivante.

DOCUMENT TEXT:
{content}

STRUCTURE JSON REQUISE:
{json_structure}

{common_instructions}""" 