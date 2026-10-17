# -*- coding: utf-8 -*-
"""
Stable key of a layer - the field a key-list filter (``"key" IN (...)``) uses.

Shared by the layer registration (core.tasks.layer_management_task) and the
OGR backend (adapters.backends.ogr.expression_builder) since 2026-10-17.
Both used to fall back on "the first integer field", then "the first field":
on the Géoplateforme communes (WFS, no declared key) that was
``population``, so ``"population" IN (...)`` silently kept every commune
sharing a population with a selected one.

Order:

1. the key the provider declares;
2. a field whose name is a known unique key (``id``, ``gml_id``,
   ``cleabs``, ``objectid``, ``uuid``...); ``fid`` only on a local layer
   (a web service may expose a ``fid`` column that is not unique);
3. nothing else. The caller then uses the QGIS feature id on a local layer
   (:data:`FEATURE_ID_KEY`, ``fid`` in OGR SQL, ``$id`` in a QGIS
   expression) and refuses a key-list filter on a web service.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

# Known unique key names, by priority (compared case-insensitively).
KNOWN_KEY_NAMES = ('gml_id', 'cleabs', 'id', 'objectid', 'ogc_fid', 'gid', 'uuid', 'guid', 'pk', 'oid', 'rowid')
# Trusted on a local layer only.
LOCAL_ONLY_KEY_NAMES = ('fid',)
# Pseudo key: the QGIS feature id (not a field of the layer).
FEATURE_ID_KEY = 'fid'

DECLARED = 'declared'
NAMED = 'named'
FEATURE_ID = 'feature_id'
NONE = 'none'


@dataclass(frozen=True)
class KeyChoice:
    """The key a layer is filtered by.

    Attributes:
        name: Field name (``declared`` / ``named``), :data:`FEATURE_ID_KEY`
            (``feature_id``) or None (``none``: no reliable key).
        origin: ``declared``, ``named``, ``feature_id`` or ``none``.
    """

    name: Optional[str]
    origin: str

    @property
    def is_field(self) -> bool:
        """A real field of the layer."""
        return self.origin in (DECLARED, NAMED)


def choose_key(field_names: Sequence[str], declared: Iterable[str] = (), local: bool = True) -> KeyChoice:
    """Pick the stable key of a layer.

    Args:
        field_names: Field names of the layer, in order.
        declared: Key field names the provider declares (``primaryKeyAttributes``).
        local: True for a local layer (file, memory, database): ``fid`` is
            trusted and the QGIS feature id is the fallback.

    Returns:
        KeyChoice: never "the first integer field".
    """
    names = [name for name in field_names if isinstance(name, str)]
    for name in declared:
        if isinstance(name, str) and name in names:
            return KeyChoice(name, DECLARED)
    by_lower = {}
    for name in names:
        by_lower.setdefault(name.lower(), name)
    candidates = (LOCAL_ONLY_KEY_NAMES + KNOWN_KEY_NAMES) if local else KNOWN_KEY_NAMES
    for candidate in candidates:
        if candidate in by_lower:
            return KeyChoice(by_lower[candidate], NAMED)
    if local:
        return KeyChoice(FEATURE_ID_KEY, FEATURE_ID)
    return KeyChoice(None, NONE)


def is_feature_id_key(name: Optional[str], field_names: Sequence[str]) -> bool:
    """True when ``name`` is the pseudo key :data:`FEATURE_ID_KEY` (no field of that name)."""
    return bool(name) and name.lower() == FEATURE_ID_KEY and name not in field_names
