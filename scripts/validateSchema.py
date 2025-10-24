import json
import os
from jsonschema import validate, Draft7Validator
from jsonschema.exceptions import ValidationError

SCHEMA_DIR = "./schema"

class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    pass

def validate_layout(layout_path: str):
    """
    Validate a layout JSON file against its schema version.
    
    Args:
        layout_path (str): Path to the layout JSON file.
    
    Returns:
        dict: The validated layout object.
    
    Raises:
        SchemaValidationError: If validation fails.
    """
    # Load layout JSON
    with open(layout_path, "r", encoding="utf-8") as f:
        layout = json.load(f)

    # Extract version (e.g. "1.0.0" -> "1_0")
    version = layout.get("version")
    if not version:
        raise SchemaValidationError("Layout JSON missing 'version' field")

    # Normalise version string to schema filename
    version_key = version.split(".")[0:2]  # take major.minor
    schema_filename = "_".join(version_key) + ".json"
    schema_path = os.path.join(SCHEMA_DIR, schema_filename)

    if not os.path.exists(schema_path):
        raise SchemaValidationError(f"No schema found for version {version} at {schema_path}")

    # Load schema
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Validate
    try:
        validate(instance=layout, schema=schema, cls=Draft7Validator)
    except ValidationError as e:
        raise SchemaValidationError(f"Validation failed: {e.message}")

    return layout