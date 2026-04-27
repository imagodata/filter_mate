# -*- coding: utf-8 -*-
"""
Lightweight JSON Schema validator for favorites bundles.

We intentionally avoid depending on the ``jsonschema`` package (not part
of QGIS's bundled Python). This module performs the structural checks we
care about for interop — enough to warn users about malformed bundles
without forcing a new dependency.

Full-strength validation is available by ``pip install jsonschema`` and
calling :func:`validate_with_jsonschema` instead of :func:`validate`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Tuple

logger = logging.getLogger('FilterMate.FavoritesSharing.Validator')

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema', 'favorites-v3.schema.json')


def validate(data: Any) -> Tuple[bool, List[str]]:
    """Structural validation of a favorites bundle.

    Returns ``(ok, errors)``. Errors list is empty when ok.

    This is deliberately permissive — the goal is to catch obvious
    corruption and to let the real loader do graceful fallback on edge
    cases (e.g., unexpected extra fields are fine, not errors).
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["top-level value must be an object"]

    schema = data.get('schema')
    if schema is not None and schema != 'filter_mate.favorites':
        errors.append(f"schema must be 'filter_mate.favorites' (got {schema!r})")

    schema_version = data.get('schema_version')
    if schema_version is not None:
        if not isinstance(schema_version, int) or schema_version < 1:
            errors.append(f"schema_version must be a positive int (got {schema_version!r})")
        elif schema_version > 3:
            # Future schema — warn, don't reject. Loader uses _extra to
            # survive unknown keys.
            logger.info(f"Bundle declares schema_version={schema_version}; falling back to v3 reader.")

    favorites = data.get('favorites')
    if favorites is None:
        errors.append("missing 'favorites' list")
    elif not isinstance(favorites, list):
        errors.append("'favorites' must be a list")
    else:
        for i, fav in enumerate(favorites):
            fav_errors = _validate_favorite(fav, i)
            errors.extend(fav_errors)

    collection = data.get('collection')
    if collection is not None and not isinstance(collection, dict):
        errors.append("'collection' must be an object when present")

    return (len(errors) == 0), errors


def _validate_favorite(fav: Any, index: int) -> List[str]:
    errors: List[str] = []
    prefix = f"favorites[{index}]"

    if not isinstance(fav, dict):
        return [f"{prefix}: must be an object"]

    name = fav.get('name')
    if not name or not isinstance(name, str):
        errors.append(f"{prefix}: 'name' is required and must be a non-empty string")

    expression = fav.get('expression')
    if expression is None:
        errors.append(f"{prefix}: 'expression' is required")
    elif not isinstance(expression, str):
        errors.append(f"{prefix}: 'expression' must be a string")

    tags = fav.get('tags')
    if tags is not None and not isinstance(tags, list):
        errors.append(f"{prefix}: 'tags' must be a list when present")
    elif isinstance(tags, list):
        for t in tags:
            if not isinstance(t, str):
                errors.append(f"{prefix}: every tag must be a string")
                break

    use_count = fav.get('use_count')
    if use_count is not None and (not isinstance(use_count, int) or use_count < 0):
        errors.append(f"{prefix}: 'use_count' must be a non-negative int")

    remote = fav.get('remote_layers')
    if remote is not None and not isinstance(remote, dict):
        errors.append(f"{prefix}: 'remote_layers' must be an object or null")

    spatial = fav.get('spatial_config')
    if spatial is not None and not isinstance(spatial, dict):
        errors.append(f"{prefix}: 'spatial_config' must be an object or null")

    return errors


def validate_with_jsonschema(data: Any) -> Tuple[bool, List[str]]:
    """Full JSON-Schema validation against favorites-v3.schema.json.

    Requires the ``jsonschema`` package; falls back to :func:`validate`
    when it's missing. Returns the same ``(ok, errors)`` tuple.
    """
    try:
        import jsonschema  # type: ignore
    except ImportError:
        logger.debug("jsonschema not installed — using lightweight validator")
        return validate(data)

    try:
        import json
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f"Cannot load favorites schema: {e}")
        return validate(data)

    validator = jsonschema.Draft202012Validator(schema)
    errors = [
        f"{'.'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]
    return (len(errors) == 0), errors
