# -*- coding: utf-8 -*-
"""New fields and joins of vector layers, for the agent.

A field is added in the edit buffer, as a feature edit (``feature_edits.py``): one command of the undo stack, nothing
saved, and its values may be computed by a QGIS expression right away. A join is a property of the project (the
fields of another layer shown beside each feature): nothing is written either, and undoing the turn removes it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...core.domain.layer_kind import LayerKind
from .feature_edits import IN_BUFFER, _abandon, _editable_layer, _start_editing, update_features
from .operations import busy_reason, layer_kind, resolve_layer

FIELD_TYPES = ("integer", "integer64", "decimal", "text", "date", "datetime", "boolean")
MAX_FIELD_NAME = 63  # what a shapefile or PostgreSQL would cut or refuse beyond
MAX_TEXT_LENGTH = 10_000


def _type(kind: str):
    """The type of a new field, in the form the QgsField of this QGIS takes (QMetaType from 3.38, QVariant before)."""
    from qgis.core import Qgis
    names = {"integer": "Int", "integer64": "LongLong", "decimal": "Double", "text": "QString", "date": "QDate",
             "datetime": "QDateTime", "boolean": "Bool"}
    if Qgis.QGIS_VERSION_INT >= 33800:
        from qgis.PyQt.QtCore import QMetaType
        return getattr(QMetaType.Type, names[kind])
    from qgis.PyQt.QtCore import QVariant
    return getattr(QVariant, {"QString": "String", "QDate": "Date", "QDateTime": "DateTime"}.get(names[kind],
                                                                                                 names[kind]))


def add_field(layer: str, name: str, field_type: str = "text", length: int = 0, formula: str = "") -> Dict[str, Any]:
    """Add a field to a vector layer in its edit buffer; ``formula`` (a QGIS expression) fills it on every feature.

    Raises:
        ValueError: A layer that cannot be edited, a name taken or too long, an unknown type, a refused formula.
    """
    from qgis.core import QgsField
    text = str(name or "").strip()
    if not text or len(text) > MAX_FIELD_NAME:
        raise ValueError(f"a field name has 1 to {MAX_FIELD_NAME} characters")
    if field_type not in FIELD_TYPES:
        raise ValueError(f"type is one of {', '.join(FIELD_TYPES)}")
    if not 0 <= int(length) <= MAX_TEXT_LENGTH:
        raise ValueError(f"length is 0 (the default of the source) to {MAX_TEXT_LENGTH}")
    found = _editable_layer(layer, "AddAttributes")
    if found.fields().lookupField(text) >= 0:
        raise ValueError(f"'{found.name()}' already has a field {text!r}")
    field = QgsField(text, _type(field_type))
    if length and field_type == "text":
        field.setLength(int(length))
    # 2026-11-12: in editing mode only now, and out of it again when the field is refused
    opened = _start_editing(found, f"add field {text}")
    if not found.addAttribute(field):
        _abandon(found, opened)
        raise ValueError(f"the field {text!r} could not be added to '{found.name()}'")
    found.endEditCommand()
    answer: Dict[str, Any] = {'layer_name': found.name(), 'field': text, 'type': field_type, 'computed': 0,
                              'editing': True, 'unsaved': True, 'note': IN_BUFFER}
    if formula:
        try:
            computed = update_features(found.id(), formulas={text: formula}, expression="true")
        except ValueError as exc:
            # The field stays, empty: the model is told why its values are missing, and may try another formula.
            answer['formula_error'] = str(exc)
        else:
            answer['computed'] = computed.get('changed', 0)
    return answer


def _vector(reference: str, role: str):
    layer = resolve_layer(str(reference or ""))
    if layer is None:
        raise ValueError(f"{role} {reference!r} not found")
    if layer_kind(layer) is not LayerKind.VECTOR:
        raise ValueError(f"'{layer.name()}' is not a vector layer: only vector layers are joined")
    return layer


def join_specs(layer) -> List[Dict[str, Any]]:
    """The joins of a layer, as plain dicts that bring them back."""
    specs = []
    for join in layer.vectorJoins():
        subset = join.joinFieldNamesSubset()
        specs.append({'join_layer_id': join.joinLayerId(), 'join_field': join.joinFieldName(),
                      'target_field': join.targetFieldName(), 'prefix': join.prefix(),
                      'fields': list(subset) if subset is not None else None})
    return specs


def add_join(layer, spec: Dict[str, Any]) -> bool:
    from qgis.core import QgsProject, QgsVectorLayerJoinInfo
    other = QgsProject.instance().mapLayer(spec['join_layer_id'])
    if other is None:
        return False
    info = QgsVectorLayerJoinInfo()
    info.setJoinLayer(other)
    info.setJoinFieldName(spec['join_field'])
    info.setTargetFieldName(spec['target_field'])
    info.setUsingMemoryCache(True)
    info.setPrefix(spec.get('prefix') or '')
    if spec.get('fields') is not None:
        info.setJoinFieldNamesSubset(list(spec['fields']))
    return bool(layer.addJoin(info))


def join_layers(layer: str, join_layer: str, target_field: str, join_field: str,
                fields: Optional[List[str]] = None, prefix: Optional[str] = None) -> Dict[str, Any]:
    """Show the fields of ``join_layer`` beside the features of ``layer`` whose ``target_field`` equals its
    ``join_field``; nothing is written to either source.

    Raises:
        ValueError: Unknown layers or fields, a layer joined to itself or already joined to that layer.
    """
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    target, other = _vector(layer, "layer"), _vector(join_layer, "join layer")
    if target.id() == other.id():
        raise ValueError("a layer is not joined to itself")
    if any(join.joinLayerId() == other.id() for join in target.vectorJoins()):
        raise ValueError(f"'{target.name()}' is already joined to '{other.name()}'")
    if target.fields().lookupField(target_field) < 0:
        raise ValueError(f"'{target.name()}' has no field {target_field!r}")
    if other.fields().lookupField(join_field) < 0:
        raise ValueError(f"'{other.name()}' has no field {join_field!r}")
    unknown = [name for name in (fields or []) if other.fields().lookupField(name) < 0]
    if unknown:
        raise ValueError(f"'{other.name()}' has no field {', '.join(repr(name) for name in unknown)}")
    chosen = [name for name in (fields or []) if name != join_field] or None
    spec = {'join_layer_id': other.id(), 'join_field': join_field, 'target_field': target_field,
            'prefix': f"{other.name()}_" if prefix is None else prefix, 'fields': chosen}
    before = {item.name() for item in target.fields()}
    if not add_join(target, spec):
        raise ValueError(f"'{other.name()}' could not be joined to '{target.name()}'")
    added = [item.name() for item in target.fields() if item.name() not in before]
    return {'layer_name': target.name(), 'join_layer': other.name(), 'fields_added': added,
            'note': 'A join of the project: the fields show beside each feature, nothing is written to the data.'}


def remove_join(layer, join_layer_id: str) -> bool:
    return bool(layer.removeJoin(join_layer_id))
