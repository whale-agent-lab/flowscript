"""Small JSON Schema subset used by the validation MVP.

The runtime passes the full schema to the model. This module validates the
keywords needed by the demo without adding a jsonschema dependency.
"""

from __future__ import annotations

from datetime import date
from typing import Any


class SchemaValidationError(ValueError):
    pass


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if expected:
        _validate_type(instance, expected, path)

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path} must be one of {schema['enum']!r}")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in instance]
        if missing:
            raise SchemaValidationError(f"{path} is missing required fields: {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(instance) - set(properties))
            if unknown:
                raise SchemaValidationError(f"{path} has undeclared fields: {unknown}")
        for name, value in instance.items():
            if name in properties:
                validate(value, properties[name], f"{path}.{name}")

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaValidationError(f"{path} has too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaValidationError(f"{path} has too many items")
        if schema.get("uniqueItems"):
            rendered = [repr(item) for item in instance]
            if len(rendered) != len(set(rendered)):
                raise SchemaValidationError(f"{path} must contain unique items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                validate(item, item_schema, f"{path}[{index}]")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise SchemaValidationError(f"{path} is too short")
        if schema.get("format") == "date":
            try:
                date.fromisoformat(instance)
            except ValueError as exc:
                raise SchemaValidationError(f"{path} must use YYYY-MM-DD") from exc

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"{path} is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"{path} is above maximum")


def _validate_type(instance: Any, expected: str, path: str) -> None:
    checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }
    if expected not in checks:
        raise SchemaValidationError(f"{path} uses unsupported schema type: {expected}")
    if not checks[expected](instance):
        raise SchemaValidationError(f"{path} must be {expected}, got {type(instance).__name__}")
