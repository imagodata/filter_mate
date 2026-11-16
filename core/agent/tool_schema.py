# -*- coding: utf-8 -*-
"""The schema of a tool as a model reads it (token diet, lot 2, 2026-11-16).

The plugin checks every call against the whole schema of the catalog and takes its defaults from it
(``tool_executor``): what only guards an argument tells the model nothing and goes. A bound that guides a call stays
(review of lot 2): a length of 100 at most (the 12 characters of a header of ask_user, a name of 60), a number of
items when there are 20 at most (two to four options) and not merely the size of an enum, the schema of the values
of a map. An optional value (``anyOf`` a
type or null) is written as its type: a null still passes the check of the plugin. Ollama sent this form since
2026-11 (``providers/ollama_chat.wire_schema``); every provider sends it now.
"""
from __future__ import annotations

from typing import Any

# Keywords that only check an argument, or name a schema for a reader that is not the model: dropped, except a bound
# that guides (``_guides``).
_CHECKS_ONLY = frozenset({"maxLength", "minLength", "maxItems", "minItems", "additionalProperties", "title"})
# A length or a number of items this small is a rule the model must follow, not a guard against absurd input.
GUIDING_LENGTH = 100
GUIDING_ITEMS = 20
# Keywords whose value is a value, never a schema: read as they are.
_VALUES = frozenset({"default", "enum", "const", "examples", "required"})
# Keywords whose value maps names to schemas: a property is kept whatever its name (a connector may name one title).
_NAMED = frozenset({"properties", "patternProperties", "$defs", "definitions", "dependentSchemas", "dependencies",
                    "dependentRequired"})
# A bound this large only stops absurd numbers: it guides nothing.
_HUGE = 1_000_000


def _empty_default(value: Any) -> bool:
    return value is None or (isinstance(value, (str, list, dict)) and not value)


def _huge_bound(key: str, value: Any) -> bool:
    return (key in ("minimum", "maximum") and isinstance(value, (int, float)) and not isinstance(value, bool)
            and abs(value) >= _HUGE)


def _guides(key: str, value: Any, node: dict) -> bool:
    """``key: value`` of ``node`` is a bound the model must follow."""
    if key == "additionalProperties":
        return isinstance(value, dict)  # the schema of the values of a map; false only checks
    if key == "maxLength":
        return isinstance(value, int) and value <= GUIDING_LENGTH
    if key in ("maxItems", "minItems"):
        most = node.get("maxItems")
        items = node.get("items")
        choices = items.get("enum") if isinstance(items, dict) else None
        if isinstance(choices, list) and isinstance(most, int) and len(choices) <= most:
            return False  # as many as the choices: says nothing more
        return isinstance(most, int) and most <= GUIDING_ITEMS
    return False


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
        if _guides(key, value, node):
            light[key] = for_model(value) if isinstance(value, dict) else value
            continue
        if key in _CHECKS_ONLY or _huge_bound(key, value) or (key == "default" and _empty_default(value)):
            continue
        light[key] = value if key in _VALUES else for_model(value, names=key in _NAMED)
    options = light.get("anyOf")
    if isinstance(options, list) and len(options) == 2 and {"type": "null"} in options:
        other = next((option for option in options if option != {"type": "null"}), None)
        if isinstance(other, dict):
            return {**other, **{key: value for key, value in light.items() if key != "anyOf"}}
    return light
