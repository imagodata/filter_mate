# -*- coding: utf-8 -*-
"""The schema of a tool as a model reads it (token diet, lot 2, 2026-11-16).

The plugin checks every call against the whole schema of the catalog and takes its defaults from it
(``tool_executor``): what only checks an argument tells the model nothing and goes. An optional value (``anyOf`` a
type or null) is written as its type: a null still passes the check of the plugin. Ollama sent this form since
2026-11 (``providers/ollama_chat.wire_schema``); every provider sends it now.
"""
from __future__ import annotations

from typing import Any

# Keywords that only check an argument, or name a schema for a reader that is not the model.
_CHECKS_ONLY = frozenset({"maxLength", "minLength", "maxItems", "minItems", "additionalProperties", "title"})
# Keywords whose value is a value, never a schema: read as they are.
_VALUES = frozenset({"default", "enum", "const", "examples", "required"})
# Keywords whose value maps names to schemas: a property is kept whatever its name (a connector may name one title).
_NAMED = frozenset({"properties", "patternProperties", "$defs", "definitions"})
# A bound this large only stops absurd numbers: it guides nothing.
_HUGE = 1_000_000


def _empty_default(value: Any) -> bool:
    return value is None or (isinstance(value, (str, list, dict)) and not value)


def _huge_bound(key: str, value: Any) -> bool:
    return (key in ("minimum", "maximum") and isinstance(value, (int, float)) and not isinstance(value, bool)
            and abs(value) >= _HUGE)


def for_model(node: Any, names: bool = False) -> Any:
    """``node`` without what only checks an argument, empty defaults and huge bounds; a new object, ``node`` unchanged.

    ``names``: ``node`` maps the names of properties to their schemas.
    """
    if isinstance(node, list):
        return [for_model(item) for item in node]
    if not isinstance(node, dict):
        return node
    if names:
        return {key: for_model(value) for key, value in node.items()}
    light = {}
    for key, value in node.items():
        if key in _CHECKS_ONLY or _huge_bound(key, value) or (key == "default" and _empty_default(value)):
            continue
        light[key] = value if key in _VALUES else for_model(value, names=key in _NAMED)
    options = light.get("anyOf")
    if isinstance(options, list) and len(options) == 2 and {"type": "null"} in options:
        other = next((option for option in options if option != {"type": "null"}), None)
        if isinstance(other, dict):
            return {**other, **{key: value for key, value in light.items() if key != "anyOf"}}
    return light
