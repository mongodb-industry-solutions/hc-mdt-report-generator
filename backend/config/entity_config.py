import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone
import uuid

from config.database import MongoDBConnection

logger = logging.getLogger(__name__)

COLLECTION = "EntityConfig"
DOC_ID = "gr_entities_definition"

# Template collection - now stores one document per template
TEMPLATES_COLLECTION = "EntityTemplates"


def load_from_db() -> Optional[Dict[str, Any]]:
    try:
        with MongoDBConnection() as db:
            doc = db[COLLECTION].find_one({"_id": DOC_ID})
            if doc and isinstance(doc.get("config"), dict):
                return doc["config"]
    except Exception as e:
        logger.warning(f"Could not load entity config from DB: {e}")
    return None


def save_to_db(config: Dict[str, Any]) -> None:
    with MongoDBConnection() as db:
        db[COLLECTION].replace_one(
            {"_id": DOC_ID},
            {"_id": DOC_ID, "config": config},
            upsert=True,
        )
    logger.info("Entity config saved to MongoDB; file baseline no longer used at runtime.")


def load_from_file() -> Dict[str, Any]:
    entity_def_path = Path(__file__).parent.parent.parent / "gr_entities_definition.json"
    with open(entity_def_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_effective_config() -> Tuple[Dict[str, Any], str]:
    cfg = load_from_db()
    if cfg is not None:
        return cfg, "db"
    cfg = load_from_file()
    return cfg, "file"


def seed_if_missing() -> bool:
    """Seed MongoDB from file if missing. Returns True if seeded."""
    try:
        with MongoDBConnection() as db:
            exists = db[COLLECTION].find_one({"_id": DOC_ID})
            if exists:
                return False
        cfg = load_from_file()
        save_to_db(cfg)
        logger.info("Seeded EntityConfig from file baseline.")
        return True
    except Exception as e:
        logger.error(f"Failed seeding EntityConfig: {e}")
        return False


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight validation for entity configuration and sections."""
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "summary": {},
    }
    try:
        entities = config.get("entities", [])
        sections = config.get("sections", [])
        
        # Validate entities structure
        if not isinstance(entities, list):
            result["valid"] = False
            result["errors"].append("Field 'entities' must be a list.")
            return result
            
        # Validate sections structure if present
        if sections and not isinstance(sections, list):
            result["valid"] = False
            result["errors"].append("Field 'sections' must be a list.")
            return result
            
        # Collect section IDs for validation
        section_ids = set()
        if sections:
            for section in sections:
                if not isinstance(section, dict):
                    result["warnings"].append("Section item is not an object; skipping validation.")
                    continue
                section_id = section.get("id", "")
                if not section_id:
                    result["valid"] = False
                    result["errors"].append("Section missing required 'id' field.")
                elif section_id in section_ids:
                    result["valid"] = False
                    result["errors"].append(f"Duplicate section ID: {section_id}")
                else:
                    section_ids.add(section_id)
        
        # Validate entities
        names = []
        dupes = []
        by_processing = {"first_match": 0, "multiple_match": 0, "aggregate_all_matches": 0}
        section_ref_errors = []
        
        for ent in entities:
            if not isinstance(ent, dict):
                result["warnings"].append("Entity item is not an object; skipping classification.")
                continue
            name = ent.get("name", "")
            if name in names:
                dupes.append(name)
            else:
                names.append(name)
            p = ent.get("processing_type", "")
            if p in by_processing:
                by_processing[p] += 1
                
            # Validate section reference if present
            section_id = ent.get("section_id")
            if section_id and sections and section_id not in section_ids:
                section_ref_errors.append(f"Entity '{name}' references unknown section_id: {section_id}")
                
        if dupes:
            result["valid"] = False
            result["errors"].append(f"Duplicate entity names found: {sorted(set(dupes))}")
            
        if section_ref_errors:
            result["valid"] = False
            result["errors"].extend(section_ref_errors)
            
        result["summary"] = {
            "total_entities": len(entities),
            "total_sections": len(sections),
            "by_processing_type": by_processing
        }
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Validation error: {e}")
    return result


# ============================================================================
# Template Management Functions (One Document Per Template Schema)
# ============================================================================

def get_all_templates() -> Dict[str, Any]:
    """
    Get all templates from the database.
    
    Returns:
        Dict with 'active_template_id' and 'templates' list.
    """
    try:
        with MongoDBConnection() as db:
            # Find all template documents (exclude legacy config document if exists)
            templates = list(db[TEMPLATES_COLLECTION].find(
                {"is_active": {"$exists": True}}
            ))
            
            # Find the active template
            active_template = None
            template_list = []
            
            for template in templates:
                template_id = template.get("_id")
                template_data = {
                    "id": template_id,
                    "name": template.get("name", ""),
                    "description": template.get("description", ""),
                    "is_active": template.get("is_active", False),
                    "admin_template": template.get("admin_template", False),
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", []),
                    "sections": template.get("sections", [])  # NEW: Include sections
                }
                template_list.append(template_data)
                
                if template.get("is_active"):
                    active_template = template_id
            
            return {
                "active_template_id": active_template,
                "templates": template_list
            }
    except Exception as e:
        logger.error(f"Error loading templates: {e}")
    return {"active_template_id": None, "templates": []}


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific template by ID."""
    try:
        with MongoDBConnection() as db:
            template = db[TEMPLATES_COLLECTION].find_one({"_id": template_id})
            if template:
                return {
                    "id": template.get("_id"),
                    "name": template.get("name", ""),
                    "description": template.get("description", ""),
                    "is_active": template.get("is_active", False),
                    "admin_template": template.get("admin_template", False),
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", []),
                    "sections": template.get("sections", [])  # NEW: Include sections
                }
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
    return None


def get_active_template() -> Tuple[Optional[Dict[str, Any]], str]:
    """Get the currently active template."""
    try:
        with MongoDBConnection() as db:
            template = db[TEMPLATES_COLLECTION].find_one({"is_active": True})
            if template:
                return {
                    "id": template.get("_id"),
                    "name": template.get("name", ""),
                    "description": template.get("description", ""),
                    "is_active": True,
                    "admin_template": template.get("admin_template", False),
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", []),
                    "sections": template.get("sections", [])  # NEW: Include sections
                }, "db"
    except Exception as e:
        logger.error(f"Error getting active template: {e}")
    
    # Fallback to file if no active template
    cfg = load_from_file()
    return {"entities": cfg.get("entities", [])}, "file"


def create_template(
    name: str, 
    description: str = "", 
    entities: List[Dict] = None,
    sections: List[Dict] = None,  # NEW: Add sections parameter
    set_active: bool = False,
    admin_template: bool = False
) -> str:
    """
    Create a new template. Returns the new template ID.
    
    Args:
        name: Template name
        description: Template description
        entities: List of entity definitions
        sections: List of section configurations  # NEW
        set_active: If True, set this template as active (deactivates others)
        admin_template: If True, marks template as admin template (protected from deletion)
    """
    template_id = f"template_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    
    new_template = {
        "_id": template_id,
        "name": name,
        "description": description,
        "is_active": set_active,
        "admin_template": admin_template,
        "created_at": now,
        "updated_at": now,
        "version": "1.0.0",
        "entities": entities or [],
        "sections": sections or []  # NEW: Include sections
    }
    
    with MongoDBConnection() as db:
        # If setting as active, deactivate all other templates first
        if set_active:
            db[TEMPLATES_COLLECTION].update_many(
                {"is_active": True},
                {"$set": {"is_active": False}}
            )
        
        # Insert the new template
        db[TEMPLATES_COLLECTION].insert_one(new_template)
    
    logger.info(f"Created template: {template_id} - {name} (active={set_active})")
    return template_id


def update_template(template_id: str, updates: Dict[str, Any]) -> bool:
    """Update an existing template."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Build the update document
    update_doc = {}
    for key, value in updates.items():
        if key not in ["_id", "id"]:  # Don't allow changing the ID
            update_doc[key] = value
    update_doc["updated_at"] = now
    
    with MongoDBConnection() as db:
        result = db[TEMPLATES_COLLECTION].update_one(
            {"_id": template_id},
            {"$set": update_doc}
        )
    
    logger.info(f"Updated template: {template_id}, modified_count={result.modified_count}")
    return result.modified_count > 0


def delete_template(template_id: str) -> bool:
    """Delete a template. Cannot delete if it's the active template or an admin template."""
    template = get_template_by_id(template_id)
    
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    if template.get("is_active"):
        raise ValueError("Cannot delete the active template. Switch to another template first.")
    
    if template.get("admin_template"):
        raise ValueError("Cannot delete admin template. Admin templates are protected from deletion.")
    
    with MongoDBConnection() as db:
        result = db[TEMPLATES_COLLECTION].delete_one({"_id": template_id})
    
    logger.info(f"Deleted template: {template_id}")
    return result.deleted_count > 0


def set_active_template(template_id: str) -> bool:
    """Set which template should be used for extraction."""
    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    with MongoDBConnection() as db:
        # Deactivate all templates
        db[TEMPLATES_COLLECTION].update_many(
            {"is_active": True},
            {"$set": {"is_active": False}}
        )
        
        # Activate the specified template
        result = db[TEMPLATES_COLLECTION].update_one(
            {"_id": template_id},
            {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    logger.info(f"Set active template to: {template_id} - {template.get('name')}")
    return result.modified_count > 0


def migrate_legacy_config() -> str:
    """Migrate the old single-config system to template-based system."""
    # Check if already have templates in new format
    all_data = get_all_templates()
    if all_data.get("templates"):
        logger.info("Templates already exist in new format, skipping migration")
        return "already_migrated"
    
    # Load from old structure
    old_config = load_from_db()
    if not old_config:
        old_config = load_from_file()
    
    # Create default template and set as active
    template_id = create_template(
        name="Default Template",
        description="Migrated from original configuration",
        entities=old_config.get("entities", []),
        set_active=True
    )
    
    logger.info("Successfully migrated to template-based system")
    return template_id


def migrate_sections_to_templates() -> Dict[str, Any]:
    """
    Migrate report_grouping_config.json section mappings to template-based sections.
    Updates all existing templates with section configurations.
    """
    result = {
        "success": False,
        "sections_created": 0,
        "templates_updated": 0,
        "entities_mapped": 0,
        "errors": []
    }
    
    try:
        # Read the report_grouping_config.json file
        frontend_config_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "config" / "report_grouping_config.json"
        
        if not frontend_config_path.exists():
            result["errors"].append("report_grouping_config.json file not found")
            return result
            
        with open(frontend_config_path, "r", encoding="utf-8") as f:
            entity_to_section_map = json.load(f)
        
        # Extract unique sections and create section configurations
        unique_sections = sorted(set(entity_to_section_map.values()))
        
        # Define section colors and order (based on current UI colors)
        section_config_map = {
            "Patient Information": {"color": "#2563eb", "order": 1},  # Blue
            "Clinical Summary": {"color": "#059669", "order": 2},  # Green  
            "General Health and Functional Status": {"color": "#0d9488", "order": 3},  # Teal
            "Laboratory and Exploration Results": {"color": "#0891b2", "order": 4},  # Cyan
            "Medical Diagnoses": {"color": "#e11d48", "order": 5},  # Rose
            "Psychological and Social Factors": {"color": "#4338ca", "order": 6},  # Indigo
            "Patient and Tumor Characteristics": {"color": "#7c3aed", "order": 7},  # Purple
            "Presentation Reason": {"color": "#ea580c", "order": 8},  # Orange
            "MDT Recommendation (EXPERIMENTAL - Medical validation required)": {"color": "#f59e0b", "order": 9},  # Amber
            "DRAFT System Recommendation": {"color": "#dc2626", "order": 10}  # Red
        }
        
        # Create section configurations
        sections = []
        for idx, section_name in enumerate(unique_sections):
            section_id = section_name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("--", "-")
            # Handle special cases for cleaner IDs
            section_id = section_id.replace("experimental---medical-validation-required", "experimental")
            
            section_config = section_config_map.get(section_name, {
                "color": "#6b7280",  # Default gray
                "order": 100 + idx  # Keep original order for unknown sections
            })
            
            sections.append({
                "id": section_id,
                "name": section_name,
                "description": f"Section for {section_name.lower()}",
                "color": section_config["color"],
                "order": section_config["order"]
            })
        
        result["sections_created"] = len(sections)
        
        # Get all existing templates
        templates_data = get_all_templates()
        templates = templates_data.get("templates", [])
        
        if not templates:
            result["errors"].append("No templates found to update")
            return result
        
        # Update each template with sections and entity mappings
        with MongoDBConnection() as db:
            for template in templates:
                template_id = template["id"]
                entities = template.get("entities", [])
                
                # Add section_id to entities based on mapping
                entities_updated = 0
                for entity in entities:
                    entity_name = entity.get("name", "")
                    if entity_name in entity_to_section_map:
                        target_section_name = entity_to_section_map[entity_name]
                        # Find the corresponding section_id
                        for section in sections:
                            if section["name"] == target_section_name:
                                entity["section_id"] = section["id"]
                                entities_updated += 1
                                break
                
                # Update the template
                now = datetime.now(timezone.utc).isoformat()
                update_result = db[TEMPLATES_COLLECTION].update_one(
                    {"_id": template_id},
                    {"$set": {
                        "sections": sections,
                        "entities": entities,
                        "updated_at": now
                    }}
                )
                
                if update_result.modified_count > 0:
                    result["templates_updated"] += 1
                    result["entities_mapped"] += entities_updated
                    logger.info(f"Updated template {template_id} with {len(sections)} sections and {entities_updated} entity mappings")
        
        result["success"] = True
        logger.info(f"Section migration completed successfully: {result['templates_updated']} templates updated, {result['sections_created']} sections created")
        
    except Exception as e:
        result["errors"].append(f"Migration error: {str(e)}")
        logger.error(f"Section migration failed: {e}")
    
    return result
