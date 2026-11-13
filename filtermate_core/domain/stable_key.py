# -*- coding: utf-8 -*-
"""
Stable key of a layer - the field a key-list filter (``"key" IN (...)``) uses.

Shared by the layer registration (core.tasks.layer_management_task), the
OGR backend (adapters.backends.ogr.expression_builder), the cross filter of
coverage targets and the key-list recognition of the orchestrator since
2026-10-17. They used to fall back on "the first integer field", then "the
first field": on the Géoplateforme communes (WFS, no declared key) that was
``population``, so ``"population" IN (...)`` silently kept every commune
sharing a population with a selected one.

Order:

1. the key the provider declares, when it is ONE field (2026-11-13: of a
   composite key, ``(id, year)`` of a partitioned table, the first field was
   taken for a unique key, so ``"id" IN (...)`` kept every year of a selected
   id). A composite key is no key list: PostgreSQL rows are keyed by their
   ``ctid`` (:func:`single_declared_key`), the other layers go on below;
2. a field named like a key:

   - on a local layer (file, memory, virtual...): ``id``, ``gml_id``,
     ``cleabs``, ``objectid``, ``gid``, ``ogc_fid``, ``fid``, ``*_id``,
     ``id_*``, ``uuid*``, ``guid*``..., kept ONLY when its values are proven
     unique and never NULL (``is_unique``, run in a task, never on the main
     thread);
   - on a web service / remote file: the known unique names only
     (``gml_id``, ``cleabs``, ``id``, ``objectid``...), trusted without a
     scan (proving it would download the layer); never ``fid``, never a
     pattern;

3. nothing else. A local layer is then keyed by its QGIS feature id
   (:data:`FEATURE_ID_KEY`, written ``fid`` in OGR SQL, ``$id`` in a QGIS
   expression); a web service gets no key list at all.

The QGIS feature id of a Shapefile, an OGR CSV or a delimited text layer is
its row number: it is renumbered when the file is edited (a deleted row
shifts the next ones), so a key list built on it is only valid until the
next edit of the file. GeoPackage / database feature ids are stable.

This is a PURE PYTHON module with NO QGIS dependencies.
"""
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

# Known unique key names, by priority (compared case-insensitively).
KNOWN_KEY_NAMES = ('gml_id', 'cleabs', 'id', 'objectid', 'ogc_fid', 'gid', 'uuid', 'guid', 'pk', 'oid', 'rowid')
# Named like a key on a local layer only (and proven unique there).
LOCAL_ONLY_KEY_NAMES = ('fid',)
# Pseudo key: the QGIS feature id. Not a field name (a WFS may have a real, unreliable "fid").
FEATURE_ID_KEY = '$id'
# The pseudo key name stored before 2026-10-17 by the OGR backend's fallback: a "fid" that is
# no field of the layer still means the feature id.
LEGACY_FEATURE_ID_KEY = 'fid'

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


def looks_like_key_name(name: str) -> bool:
    """Named like a key: a known name, ``fid``, ``*_id``, ``id_*``, ``uuid*``, ``guid*``."""
    lower = (name or '').lower()
    return (lower in KNOWN_KEY_NAMES or lower in LOCAL_ONLY_KEY_NAMES or lower.endswith('_id')
            or lower.startswith(('id_', 'uuid', 'guid')))


def key_candidates(field_names: Sequence[str], local: bool = True) -> List[str]:
    """Field names that may be the key, by priority (known names, then ``fid``, then patterns)."""
    names = [name for name in field_names if isinstance(name, str)]
    by_lower = {}
    for name in names:
        by_lower.setdefault(name.lower(), name)
    ordered = [by_lower[known] for known in KNOWN_KEY_NAMES if known in by_lower]
    if local:
        ordered += [by_lower[name] for name in LOCAL_ONLY_KEY_NAMES if name in by_lower]
        ordered += [name for name in names if looks_like_key_name(name) and name not in ordered]
    return ordered


POSTGRESQL_ROW_KEY = 'ctid'  # the row id of PostgreSQL: unique while the row is not updated


def single_declared_key(indexes: Iterable[int], fields, provider_type: str = '') -> Optional[str]:
    """The name of the key the provider declares when it is one field.

    2026-11-13: callers took the first field of the key, of a composite key too (``(id, year)`` of a partitioned
    table), and wrote ``"id" IN (...)``: every year of a selected id was kept. A composite key gives
    :data:`POSTGRESQL_ROW_KEY` on PostgreSQL, None elsewhere (the caller goes on with its own search).

    Args:
        indexes: ``primaryKeyAttributes()`` of the layer, or ``pkAttributeIndexes()`` of its provider.
        fields: The fields of the layer (``QgsFields``, read by ``[index]``).
        provider_type: ``providerType()`` of the layer.

    Raises:
        IndexError: The one index is past the fields.
    """
    try:
        indexes = [int(index) for index in (indexes or ())]
    except (TypeError, ValueError):
        return None
    if len(indexes) > 1:
        return POSTGRESQL_ROW_KEY if str(provider_type).lower() == 'postgres' else None
    if not indexes or indexes[0] < 0:
        return None
    # An index past the fields (a column removed meanwhile) raises as the callers' fields()[index] did: a clear
    # error, never another key chosen in silence.
    field = fields[indexes[0]]  # QgsFields raises IndexError past its fields
    name = field.name()
    return name if isinstance(name, str) and name else None


def choose_key(field_names: Sequence[str], declared: Iterable[str] = (), local: bool = True,
               is_unique: Optional[Callable[[str], Optional[bool]]] = None) -> KeyChoice:
    """Pick the stable key of a layer.

    Args:
        field_names: Field names of the layer, in order.
        declared: Key field names the provider declares (``primaryKeyAttributes``).
        local: True for a local layer: names are checked by ``is_unique`` and
            the QGIS feature id is the fallback. False for a web service or a
            remote file: known unique names are trusted, no fallback.
        is_unique: ``name -> True`` (unique, no NULL), ``False`` or ``None``
            (unknown: not proven). Without it, a local layer keeps its
            declared key or its feature id.

    Returns:
        KeyChoice: never "the first integer field".
    """
    names = [name for name in field_names if isinstance(name, str)]
    declared = [name for name in declared if isinstance(name, str) and name in names]
    if len(declared) == 1:  # a composite key: none of its fields alone is a key
        return KeyChoice(declared[0], DECLARED)
    for name in key_candidates(names, local):
        if not local:
            return KeyChoice(name, NAMED)
        if is_unique is not None and is_unique(name) is True:
            return KeyChoice(name, NAMED)
    if local:
        return KeyChoice(FEATURE_ID_KEY, FEATURE_ID)
    return KeyChoice(None, NONE)


def is_feature_id_key(name: Optional[str], field_names: Sequence[str]) -> bool:
    """True for the pseudo key: :data:`FEATURE_ID_KEY`, or a legacy ``fid`` that is no field."""
    if not name:
        return False
    if name == FEATURE_ID_KEY:
        return True
    return name.lower() == LEGACY_FEATURE_ID_KEY and name not in field_names
