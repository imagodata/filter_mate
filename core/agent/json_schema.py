# -*- coding: utf-8 -*-
"""The part of JSON Schema the tool catalog uses, to check what a model sends.

The plugin has no dependency (no pydantic, no jsonschema inside QGIS), and a
model's arguments are untrusted input. Unknown keywords are ignored.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

_MAX_REPORTED = 10
_MAX_EXACT_INT = 2 ** 53  # a float beyond this is not a meaningful integer


def _finite_float(value: Any) -> bool:
    return isinstance(value, float) and math.isfinite(value)


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if isinstance(value, bool):  # bool is an int in Python, never a number in JSON
        return False
    if expected == "integer":
        return isinstance(value, int) or (_finite_float(value) and value.is_integer() and abs(value) <= _MAX_EXACT_INT)
    if expected == "number":
        return isinstance(value, int) or _finite_float(value)
    return True


def _check(value: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            attempt: List[str] = []
            _check(value, option, path, attempt)
            if not attempt:
                break
        else:
            kinds = [option.get("type", "?") for option in schema["anyOf"]]
            errors.append(f"{path}: expected one of {kinds}")
            return

    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(value, option) for option in options):
            errors.append(f"{path}: expected {'/'.join(options)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: too long (at most {schema['maxLength']} characters)")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):  # isfinite overflows on a huge int
            errors.append(f"{path}: not a finite number")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below the minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above the maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: must be below {schema['exclusiveMaximum']}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} item(s)")
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                _check(item, items, f"{path}[{index}]", errors)
    elif isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", ()):
            if name not in value:
                errors.append(f"{path}.{name}: required")
        extra = schema.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                _check(item, properties[name], f"{path}.{name}", errors)
            elif extra is False:
                errors.append(f"{path}.{name}: unknown argument")
            elif isinstance(extra, dict):
                _check(item, extra, f"{path}.{name}", errors)


def validate(value: Any, schema: Dict[str, Any]) -> List[str]:
    """Problems of ``value`` against ``schema``, the first ones only; empty when it is valid."""
    errors: List[str] = []
    _check(value, schema, "$", errors)
    return errors[:_MAX_REPORTED]
