#!/usr/bin/env python3
"""
Script to add a new entity template to MongoDB.
Uses one-document-per-template schema with is_active field.

Usage:
    # List existing templates
    python add_template_to_mongodb.py --list

    # Add new template (without activating)
    python add_template_to_mongodb.py --add new_entities_template.json

    # Add new template AND set as active
    python add_template_to_mongodb.py --add new_entities_template.json --active

    # Set an existing template as active
    python add_template_to_mongodb.py --set-active template_xxxxxxxx

    # Show template details
    python add_template_to_mongodb.py --show template_xxxxxxxx

    # Delete a template
    python add_template_to_mongodb.py --delete template_xxxxxxxx
"""

import json
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables directly.")

# Collection name for templates
TEMPLATES_COLLECTION = "EntityTemplates"


def get_mongo_client():
    """Get MongoDB client from environment variables."""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "clarityGR")
    
    print(f"📦 Connecting to MongoDB: {mongo_uri}")
    print(f"📦 Database: {db_name}")
    
    client = MongoClient(mongo_uri)
    return client[db_name]


def load_template_from_file(filepath: str) -> dict:
    """Load template JSON from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_defaults(template_data: dict) -> dict:
    """Apply default values for optional fields."""
    # Default values matching backend behavior
    # NOTE: processing_type is NOT set here - backend defaults to aggregate_all_matches
    DEFAULTS = {
        "type": "string"  # Only type needs a default for the script
    }
    
    for entity in template_data.get("entities", []):
        # Apply defaults for missing optional fields
        for field, default_value in DEFAULTS.items():
            if field not in entity or not entity[field]:
                entity[field] = default_value
                print(f"   ℹ️ Applied default {field}='{default_value}' to entity '{entity.get('name', 'unnamed')}'")
    
    return template_data


def validate_template(template_data: dict) -> bool:
    """Validate that template has required fields."""
    errors = []
    
    if "entities" not in template_data:
        errors.append("Missing 'entities' array")
        return False
    
    # Only truly required fields (processing_type now has a default)
    required_entity_fields = ["name", "definition", "extraction_instructions"]
    valid_processing_types = ["first_match", "multiple_match", "aggregate_all_matches"]
    
    for i, entity in enumerate(template_data.get("entities", [])):
        for field in required_entity_fields:
            if field not in entity or not entity[field]:
                errors.append(f"Entity {i} ({entity.get('name', 'unnamed')}): missing '{field}'")
        
        # Validate processing_type if present (after defaults applied)
        if entity.get("processing_type") and entity.get("processing_type") not in valid_processing_types:
            errors.append(f"Entity {i} ({entity.get('name', 'unnamed')}): invalid processing_type '{entity.get('processing_type')}'")
        
        # Validate source_filters if present
        for sf in entity.get("source_filters", []):
            if "libnatcr" not in sf:
                errors.append(f"Entity {i} ({entity.get('name', 'unnamed')}): source_filter missing 'libnatcr'")
        
        for sf in entity.get("fallback_filters", []):
            if "libnatcr" not in sf:
                errors.append(f"Entity {i} ({entity.get('name', 'unnamed')}): fallback_filter missing 'libnatcr'")
    
    if errors:
        print("❌ Validation errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Template validation passed")
    return True


def add_template_to_mongodb(template_data: dict, set_as_active: bool = False):
    """
    Add a new template to MongoDB as its own document.
    
    Schema:
    {
        "_id": "template_xxxxxxxx",
        "name": "Template Name",
        "description": "Description",
        "is_active": true/false,
        "created_at": "ISO datetime",
        "updated_at": "ISO datetime",
        "version": "1.0.0",
        "entities": [...]
    }
    """
    # Apply defaults for optional fields first
    print("📝 Applying defaults for optional fields...")
    template_data = apply_defaults(template_data)
    
    # Validate template
    if not validate_template(template_data):
        print("❌ Template validation failed. Aborting.")
        return None
    
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    # Generate unique template ID
    template_id = f"template_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # If setting as active, deactivate all other templates first
    if set_as_active:
        result = collection.update_many(
            {"is_active": True},
            {"$set": {"is_active": False}}
        )
        if result.modified_count > 0:
            print(f"📝 Deactivated {result.modified_count} previously active template(s)")
    
    # Prepare template document
    template_doc = {
        "_id": template_id,
        "name": template_data.get("template_name", "New Template"),
        "description": template_data.get("template_description", ""),
        "is_active": set_as_active,
        "created_at": now,
        "updated_at": now,
        "version": "1.0.0",
        "entities": template_data.get("entities", [])
    }
    
    # Insert the new template document
    collection.insert_one(template_doc)
    print(f"✅ Created template: {template_id}")
    
    # Print summary
    print(f"\n📋 Template Summary:")
    print(f"   ID: {template_id}")
    print(f"   Name: {template_doc['name']}")
    print(f"   Entities: {len(template_doc['entities'])}")
    print(f"   Active: {set_as_active}")
    
    # Print entities with source filters
    print(f"\n📝 Entities with Source Filters:")
    for entity in template_doc['entities']:
        filters = entity.get('source_filters', [])
        fallbacks = entity.get('fallback_filters', [])
        filter_info = f"filters: {len(filters)}, fallbacks: {len(fallbacks)}" if filters or fallbacks else "no filters"
        print(f"   • {entity['name']} ({entity.get('processing_type', 'default')}) - {filter_info}")
    
    return template_id


def list_existing_templates():
    """List all existing templates in MongoDB."""
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    # Find all templates with is_active field (new schema)
    templates = list(collection.find({"is_active": {"$exists": True}}))
    
    if not templates:
        print("\n⚠️ No templates found in MongoDB.")
        return
    
    print(f"\n📚 Existing Templates ({len(templates)}):")
    print("-" * 60)
    
    for template in templates:
        is_active = "✓ ACTIVE" if template.get("is_active") else ""
        entity_count = len(template.get('entities', []))
        created = str(template.get('created_at', 'unknown'))[:10]
        
        print(f"   {template.get('_id')}")
        print(f"      Name: {template.get('name')}")
        print(f"      Entities: {entity_count}")
        print(f"      Created: {created}")
        if is_active:
            print(f"      Status: {is_active}")
        print()
    
    print("-" * 60)
    active_count = sum(1 for t in templates if t.get("is_active"))
    print(f"Total templates: {len(templates)}")
    print(f"Active: {active_count}")


def set_active_template(template_id: str):
    """Set a template as the active template."""
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    # Verify template exists
    template = collection.find_one({"_id": template_id})
    if not template:
        print(f"❌ Template not found: {template_id}")
        # List available templates
        templates = list(collection.find({"is_active": {"$exists": True}}, {"_id": 1, "name": 1}))
        if templates:
            print(f"   Available templates:")
            for t in templates:
                print(f"      - {t['_id']}: {t.get('name', 'unnamed')}")
        return
    
    # Check if already active
    if template.get("is_active"):
        print(f"⚠️ Template already active: {template_id}")
        return
    
    # Deactivate all templates
    collection.update_many(
        {"is_active": True},
        {"$set": {"is_active": False}}
    )
    
    # Activate the specified template
    result = collection.update_one(
        {"_id": template_id},
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Set active template to: {template_id} - {template.get('name')}")
    else:
        print(f"⚠️ Template not modified: {template_id}")


def delete_template(template_id: str):
    """Delete a template from MongoDB."""
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    # Find the template
    template = collection.find_one({"_id": template_id})
    
    if not template:
        print(f"❌ Template not found: {template_id}")
        return
    
    # Check if it's the active template
    if template.get("is_active"):
        print(f"⚠️ Cannot delete active template. Set another template as active first.")
        return
    
    result = collection.delete_one({"_id": template_id})
    
    if result.deleted_count > 0:
        print(f"✅ Deleted template: {template_id} - {template.get('name')}")
    else:
        print(f"❌ Failed to delete template: {template_id}")


def show_template_details(template_id: str):
    """Show detailed information about a specific template."""
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    template = collection.find_one({"_id": template_id})
    
    if template is None:
        print(f"❌ Template not found: {template_id}")
        return
    
    print(f"\n📋 Template Details: {template_id}")
    print("=" * 60)
    print(f"Name: {template.get('name')}")
    print(f"Description: {template.get('description', 'N/A')}")
    print(f"Created: {template.get('created_at', 'N/A')}")
    print(f"Updated: {template.get('updated_at', 'N/A')}")
    print(f"Version: {template.get('version', 'N/A')}")
    print(f"Active: {'Yes ✓' if template.get('is_active') else 'No'}")
    print(f"\nEntities ({len(template.get('entities', []))}):")
    print("-" * 60)
    
    for entity in template.get('entities', []):
        print(f"\n  📌 {entity['name']}")
        print(f"     Type: {entity.get('type', 'string')}")
        print(f"     Processing: {entity['processing_type']}")
        
        if entity.get('source_filters'):
            print(f"     Source Filters:")
            for sf in entity['source_filters']:
                filter_str = f"       - {sf['libnatcr']}"
                if sf.get('title_keyword'):
                    filter_str += f", title: '{sf['title_keyword']}'"
                if sf.get('content_keyword'):
                    filter_str += f", content: '{sf['content_keyword']}'"
                filter_str += f", depth: {sf.get('depth', 0)}"
                if sf.get('focus_section'):
                    filter_str += f", focus: '{sf['focus_section']}'"
                print(filter_str)
        
        if entity.get('fallback_filters'):
            print(f"     Fallback Filters:")
            for sf in entity['fallback_filters']:
                filter_str = f"       - {sf['libnatcr']}"
                if sf.get('title_keyword'):
                    filter_str += f", title: '{sf['title_keyword']}'"
                if sf.get('content_keyword'):
                    filter_str += f", content: '{sf['content_keyword']}'"
                filter_str += f", depth: {sf.get('depth', 0)}"
                print(filter_str)


def cleanup_legacy_documents():
    """Remove legacy embedded-array format documents if they exist."""
    db = get_mongo_client()
    collection = db[TEMPLATES_COLLECTION]
    
    # Find legacy document
    legacy_doc = collection.find_one({"_id": "entity_templates_config"})
    
    if legacy_doc:
        print(f"🔍 Found legacy document: entity_templates_config")
        print(f"   Templates in old format: {len(legacy_doc.get('templates', []))}")
        
        response = input("   Delete legacy document? (y/n): ").strip().lower()
        if response == 'y':
            collection.delete_one({"_id": "entity_templates_config"})
            print("✅ Deleted legacy document")
        else:
            print("⏭️ Kept legacy document")
    else:
        print("✅ No legacy documents found")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage entity templates in MongoDB (one-document-per-template schema)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python add_template_to_mongodb.py --list
  python add_template_to_mongodb.py --add new_entities_template.json
  python add_template_to_mongodb.py --add new_entities_template.json --active
  python add_template_to_mongodb.py --set-active template_abc12345
  python add_template_to_mongodb.py --show template_abc12345
  python add_template_to_mongodb.py --delete template_abc12345
  python add_template_to_mongodb.py --cleanup-legacy
        """
    )
    parser.add_argument("--add", type=str, metavar="FILE", help="Path to template JSON file to add")
    parser.add_argument("--active", action="store_true", help="Set added template as active")
    parser.add_argument("--list", action="store_true", help="List existing templates")
    parser.add_argument("--set-active", type=str, metavar="ID", help="Set a template ID as active")
    parser.add_argument("--show", type=str, metavar="ID", help="Show detailed info about a template")
    parser.add_argument("--delete", type=str, metavar="ID", help="Delete a template (cannot delete active template)")
    parser.add_argument("--cleanup-legacy", action="store_true", help="Remove legacy embedded-array format documents")
    
    args = parser.parse_args()
    
    if args.list:
        list_existing_templates()
    elif args.add:
        if not os.path.exists(args.add):
            print(f"❌ File not found: {args.add}")
            sys.exit(1)
        template_data = load_template_from_file(args.add)
        add_template_to_mongodb(template_data, set_as_active=args.active)
    elif args.set_active:
        set_active_template(args.set_active)
    elif args.show:
        show_template_details(args.show)
    elif args.delete:
        delete_template(args.delete)
    elif args.cleanup_legacy:
        cleanup_legacy_documents()
    else:
        # Default: show help and list templates
        parser.print_help()
        print("\n")
        list_existing_templates()
