from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
import logging

from config.entity_config import (
    get_effective_config,
    load_from_db,
    save_to_db,
    load_from_file,
    seed_if_missing,
    validate_config,
    # Template management functions
    get_all_templates,
    get_active_template,
    get_template_by_id,
    create_template,
    update_template,
    delete_template,
    set_active_template,
    migrate_legacy_config,
    migrate_sections_to_templates,  # NEW: Section migration function
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entity-config", tags=["Settings"])


@router.get("", status_code=200)
async def get_entity_config() -> Dict[str, Any]:
    cfg, source = get_effective_config()
    return {"success": True, "source": source, "config": cfg}


@router.put("", status_code=200)
async def put_entity_config(config: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    validation = validate_config(config)
    if not validation.get("valid"):
        raise HTTPException(status_code=400, detail={"message": "Invalid config", "validation": validation})
    try:
        save_to_db(config)
        return {"success": True, "validation": validation}
    except Exception as e:
        logger.error(f"Failed to save entity config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save entity config: {e}")


@router.post("/reset", status_code=200)
async def reset_from_file() -> Dict[str, Any]:
    try:
        cfg = load_from_file()
        validation = validate_config(cfg)
        if not validation.get("valid"):
            raise HTTPException(status_code=400, detail={"message": "Baseline file invalid", "validation": validation})
        save_to_db(cfg)
        return {"success": True, "message": "Reset from file baseline", "validation": validation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset from file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset from file: {e}")


@router.get("/validate", status_code=200)
async def validate_current() -> Dict[str, Any]:
    cfg = load_from_db()
    if cfg is None:
        cfg = load_from_file()
        source = "file"
    else:
        source = "db"
    return {"success": True, "source": source, "validation": validate_config(cfg)}


@router.post("/seed-if-missing", status_code=200)
async def seed_once() -> Dict[str, Any]:
    seeded = seed_if_missing()
    return {"success": True, "seeded": seeded}


# ============================================================================
# Template Management Endpoints
# ============================================================================

@router.get("/templates", status_code=200)
async def get_all_entity_templates() -> Dict[str, Any]:
    """Get all templates."""
    data = get_all_templates()
    return {"success": True, "data": data}


@router.get("/templates/active", status_code=200)
async def get_active_entity_template() -> Dict[str, Any]:
    """Get the currently active template."""
    template, source = get_active_template()
    return {"success": True, "source": source, "template": template}


@router.post("/templates", status_code=201)
async def create_entity_template(
    name: str = Body(...),
    description: str = Body(""),
    entities: List[Dict[str, Any]] = Body([]),
    sections: List[Dict[str, Any]] = Body([]),  # NEW: Add sections parameter
    admin_template: bool = Body(False)
) -> Dict[str, Any]:
    """Create a new template."""
    # Validate entities and sections structure
    validation = validate_config({"entities": entities, "sections": sections})
    if not validation.get("valid"):
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid template configuration", "validation": validation}
        )
    
    try:
        template_id = create_template(name, description, entities, sections, admin_template=admin_template)
        return {"success": True, "template_id": template_id, "validation": validation}
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {e}")


@router.get("/templates/{template_id}", status_code=200)
async def get_entity_template(template_id: str) -> Dict[str, Any]:
    """Get a specific template by ID."""
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, "template": template}


@router.put("/templates/{template_id}", status_code=200)
async def update_entity_template(
    template_id: str,
    updates: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Update an existing template."""
    # If entities or sections are being updated, validate them
    if "entities" in updates or "sections" in updates:
        # Get current template to merge with updates for validation
        current_template = get_template_by_id(template_id)
        if not current_template:
            raise HTTPException(status_code=404, detail="Template not found")
            
        validation_data = {
            "entities": updates.get("entities", current_template.get("entities", [])),
            "sections": updates.get("sections", current_template.get("sections", []))
        }
        validation = validate_config(validation_data)
        if not validation.get("valid"):
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid template configuration", "validation": validation}
            )
    
    try:
        success = update_template(template_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update template: {e}")


@router.delete("/templates/{template_id}", status_code=200)
async def delete_entity_template(template_id: str) -> Dict[str, Any]:
    """Delete a template."""
    try:
        success = delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {e}")


@router.post("/templates/{template_id}/activate", status_code=200)
async def activate_template(template_id: str) -> Dict[str, Any]:
    """Set a template as the active one for extraction."""
    try:
        set_active_template(template_id)
        return {"success": True, "active_template_id": template_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate template: {e}")


@router.post("/templates/migrate", status_code=200)
async def migrate_to_templates() -> Dict[str, Any]:
    """Migrate from old single-config to template-based system."""
    try:
        result = migrate_legacy_config()
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to migrate: {e}")


@router.post("/templates/migrate-sections", status_code=200)
async def migrate_sections() -> Dict[str, Any]:
    """Migrate report_grouping_config.json section mappings to template-based sections."""
    try:
        result = migrate_sections_to_templates()
        if result["success"]:
            return {"success": True, "result": result}
        else:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Section migration failed", "errors": result["errors"]}
            )
    except Exception as e:
        logger.error(f"Error during section migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to migrate sections: {e}")


@router.post("/templates/{template_id}/duplicate", status_code=201)
async def duplicate_template(
    template_id: str,
    new_name: str = Body(...)
) -> Dict[str, Any]:
    """Duplicate an existing template."""
    source_template = get_template_by_id(template_id)
    if not source_template:
        raise HTTPException(status_code=404, detail="Source template not found")
    
    try:
        new_template_id = create_template(
            name=new_name,
            description=f"Duplicated from {source_template.get('name')}",
            entities=source_template.get("entities", [])
        )
        return {"success": True, "template_id": new_template_id}
    except Exception as e:
        logger.error(f"Error duplicating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate template: {e}")


