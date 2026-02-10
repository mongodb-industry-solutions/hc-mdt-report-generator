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
    """Lightweight validation for entity configuration."""
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "summary": {},
    }
    try:
        entities = config.get("entities", [])
        if not isinstance(entities, list):
            result["valid"] = False
            result["errors"].append("Field 'entities' must be a list.")
            return result
        names = []
        dupes = []
        by_processing = {"first_match": 0, "multiple_match": 0, "aggregate_all_matches": 0}
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
        if dupes:
            result["valid"] = False
            result["errors"].append(f"Duplicate entity names found: {sorted(set(dupes))}")
        result["summary"] = {
            "total_entities": len(entities),
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
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", [])
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
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", [])
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
                    "created_at": template.get("created_at", ""),
                    "updated_at": template.get("updated_at", ""),
                    "entities": template.get("entities", [])
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
    set_active: bool = False
) -> str:
    """
    Create a new template. Returns the new template ID.
    
    Args:
        name: Template name
        description: Template description
        entities: List of entity definitions
        set_active: If True, set this template as active (deactivates others)
    """
    template_id = f"template_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    
    new_template = {
        "_id": template_id,
        "name": name,
        "description": description,
        "is_active": set_active,
        "created_at": now,
        "updated_at": now,
        "version": "1.0.0",
        "entities": entities or []
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
    """Delete a template. Cannot delete if it's the active template."""
    template = get_template_by_id(template_id)
    
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    if template.get("is_active"):
        raise ValueError("Cannot delete the active template. Switch to another template first.")
    
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
