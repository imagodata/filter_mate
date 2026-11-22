# -*- coding: utf-8 -*-
"""The attribute forms of vector layers and the relations of the project, for the agent.

A form is how QGIS shows the fields of a layer to whom edits it: an alias, a widget (a list of values, a lookup
table, a range, a calendar, a check box...), constraints, default values, fields read only. A relation links the
features of a child layer to those of a parent layer by a field: the form of a parent lists its children, and a
child picks its parent. Neither writes anything to the data: they are properties of the project, and undoing the turn
takes them back (``adapters/agent/turn_effects.py``, the effects "form" and "relation").

set_form is all or nothing: every entry is checked before the first change, and one refused changes nothing.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Set

from ...core.domain.layer_kind import LayerKind
from .fields_joins import _type
from .operations import busy_reason, layer_kind, resolve_layer

MAX_FIELDS = 50
MAX_VALUES = 500
MAX_TEXT = 200  # an alias, a label of a value, the text of a constraint
# The widgets as the tool names them, and as QGIS registers them; "default" lets QGIS choose.
WIDGETS = {"value_map": "ValueMap", "value_relation": "ValueRelation", "range": "Range", "date": "DateTime",
           "checkbox": "CheckBox", "text": "TextEdit", "hidden": "Hidden", "relation_reference": "RelationReference",
           "default": ""}
# The options of an entry that belong to some widgets only: given with another widget, they are refused (the model
# would believe they did something).
_OPTIONS = {"values": ("value_map",), "layer": ("value_relation", "relation_reference"), "key": ("value_relation",),
            "value": ("value_relation",), "min": ("range",), "max": ("range",), "step": ("range",),
            "format": ("date",), "multiline": ("text",)}
_STORED_DATE = {"date": "yyyy-MM-dd", "datetime": "yyyy-MM-dd HH:mm:ss"}
# What referencedColumns gives for an expression that may read any field (attribute(), @feature...).
_ALL_ATTRIBUTES = "#!allattributes!#"


def _vector(reference: str, role: str):
    layer = resolve_layer(str(reference or ""))
    if layer is None:
        raise ValueError(f"{role} {reference!r} not found")
    if layer_kind(layer) is not LayerKind.VECTOR:
        raise ValueError(f"'{layer.name()}' is not a vector layer or a table")
    return layer


def _kind(field) -> str:
    """integer, decimal, text, date, datetime, boolean or other: what a widget may go on."""
    kind = field.type()
    if kind == _type("boolean"):
        return "boolean"
    if kind == _type("date"):
        return "date"
    if kind == _type("datetime"):
        return "datetime"
    if kind == _type("text"):
        return "text"
    if field.isNumeric():
        return "decimal" if kind == _type("decimal") else "integer"
    return "other"


def _constraints():
    from qgis.core import QgsFieldConstraints
    return QgsFieldConstraints.Constraint, QgsFieldConstraints.ConstraintStrength


def _check_expression(layer, text: str, role: str) -> None:
    """Refuse an expression that does not parse, or that names a field ``layer`` does not have (a text written
    without its quotes reads as a field)."""
    from qgis.core import QgsExpression
    expression = QgsExpression(text)
    if expression.hasParserError():
        reason = expression.parserErrorString() or "it does not parse"
        raise ValueError(f"{role} {text!r} is no QGIS expression: {reason}")
    unknown = sorted(name for name in expression.referencedColumns()
                     if name and name != _ALL_ATTRIBUTES and layer.fields().lookupField(name) < 0)
    if unknown:
        raise ValueError(f"{role} {text!r} names {', '.join(repr(name) for name in unknown)}, no field of "
                         f"'{layer.name()}': a text is written in single quotes ('Toulouse')")


def _number(text: str, whole: bool) -> bool:
    try:
        value = float(text)
    except ValueError:
        return False
    return math.isfinite(value) and (not whole or value == int(value) and "." not in text and "e" not in text.lower())


def _value_map(field, kind: str, values: Any) -> Dict[str, Any]:
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_VALUES:
        raise ValueError(f"value_map takes values, 1 to {MAX_VALUES}: texts, or {{value, label}}")
    pairs: List[Dict[str, str]] = []
    labels: Set[str] = set()
    for item in values:
        value, label = (item.get("value"), item.get("label")) if isinstance(item, dict) else (item, None)
        text = "" if value is None or isinstance(value, (dict, list)) else str(value).strip()
        if not text:
            raise ValueError("a value of value_map is empty")
        if kind in ("integer", "decimal") and not _number(text, kind == "integer"):
            raise ValueError(f"{text!r} is no {kind} number, as the field {field.name()!r} holds")
        shown = str(label).strip() if label not in (None, "") else text
        if len(shown) > MAX_TEXT:
            raise ValueError(f"a label has {MAX_TEXT} characters at most")
        if shown in labels:
            raise ValueError(f"two values have the label {shown!r}")
        labels.add(shown)
        pairs.append({shown: text})
    return {"map": pairs}


def _value_relation(entry: Dict[str, Any]) -> Dict[str, Any]:
    if not entry.get("layer"):
        raise ValueError("value_relation needs layer, the lookup table (id or name), and its key field")
    lookup = _vector(entry["layer"], "lookup layer")
    names = []
    for role in ("key", "value"):
        name = str(entry.get(role) or entry.get("key") or "")
        if not name:
            raise ValueError(f"value_relation needs key, the field of '{lookup.name()}' that is stored")
        index = lookup.fields().lookupField(name)
        if index < 0:
            raise ValueError(f"'{lookup.name()}' has no field {name!r}")
        names.append(lookup.fields().at(index).name())
    return {"Layer": lookup.id(), "LayerName": lookup.name(), "LayerSource": lookup.publicSource(),
            "LayerProviderName": lookup.providerType(), "Key": names[0], "Value": names[1], "AllowNull": True,
            "OrderByValue": True, "AllowMulti": False, "FilterExpression": "", "UseCompleter": False,
            "NofColumns": 1}


def _range(kind: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    if kind not in ("integer", "decimal"):
        raise ValueError(f"range goes on a number field, this one holds {kind}")
    bounds = {key: entry.get(key) for key in ("min", "max", "step") if entry.get(key) is not None}
    for key, value in bounds.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} is a finite number")
        if kind == "integer" and value != int(value):
            raise ValueError(f"an integer field takes whole numbers: {key} {value}")
    if "min" in bounds and "max" in bounds and bounds["min"] > bounds["max"]:
        raise ValueError("min is above max")
    if bounds.get("step", 1) <= 0:
        raise ValueError("step is above 0")
    config: Dict[str, Any] = {"Style": "SpinBox", "AllowNull": True}
    for key, name in (("min", "Min"), ("max", "Max"), ("step", "Step")):
        if key in bounds:
            config[name] = int(bounds[key]) if kind == "integer" else float(bounds[key])
    if kind == "decimal" and "step" in bounds:
        decimals = f"{float(bounds['step']):.10f}".rstrip("0").split(".")[1]
        config["Precision"] = max(len(decimals), 1)
    return config


def _date(kind: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    if kind not in _STORED_DATE:
        raise ValueError(f"date goes on a date or datetime field, this one holds {kind}")
    shown = str(entry.get("format") or ("dd/MM/yyyy" if kind == "date" else "dd/MM/yyyy HH:mm")).strip()
    if len(shown) > 50 or not re.search(r"[yMdHhms]", shown):
        raise ValueError(f"format {shown!r} is no Qt date format (dd/MM/yyyy, yyyy-MM-dd HH:mm)")
    return {"field_format": _STORED_DATE[kind], "display_format": shown, "calendar_popup": True, "allow_null": True}


def _checkbox(kind: str) -> Dict[str, Any]:
    if kind == "boolean":
        return {"CheckedState": "", "UncheckedState": "", "TextDisplayMethod": 0}
    if kind == "integer":
        return {"CheckedState": "1", "UncheckedState": "0", "TextDisplayMethod": 0}
    raise ValueError(f"checkbox goes on a boolean or integer field, this one holds {kind}")


def _relation_reference(layer, index: int, entry: Dict[str, Any]) -> Dict[str, Any]:
    from qgis.core import QgsProject
    name = layer.fields().at(index).name()
    found = QgsProject.instance().relationManager().referencingRelations(layer, index)
    if entry.get("layer"):
        parent = _vector(entry["layer"], "parent layer")
        found = [relation for relation in found if relation.referencedLayerId() == parent.id()]
    if not found:
        raise ValueError(f"no relation of the project has {name!r} of '{layer.name()}' as its child field: add one "
                         "with relations first")
    if len(found) > 1:
        raise ValueError(f"{name!r} is the child field of several relations "
                         f"({', '.join(relation.name() for relation in found)}): give layer, the parent layer")
    relation = found[0]
    parent = relation.referencedLayer()
    return {"Relation": relation.id(), "AllowNULL": True, "ShowForm": False, "ShowOpenFormButton": True,
            "MapIdentification": False, "ReadOnly": False, "OrderByValue": True, "AllowAddFeatures": False,
            "ReferencedLayerId": relation.referencedLayerId(),
            "ReferencedLayerName": parent.name() if parent is not None else "",
            "ReferencedLayerDataSource": parent.publicSource() if parent is not None else "",
            "ReferencedLayerProviderKey": parent.providerType() if parent is not None else ""}


def _widget(layer, index: int, widget: str, entry: Dict[str, Any]):
    from qgis.core import QgsEditorWidgetSetup
    field = layer.fields().at(index)
    kind = _kind(field)
    if widget == "default":
        return QgsEditorWidgetSetup()
    if widget == "value_map":
        config = _value_map(field, kind, entry.get("values"))
    elif widget == "value_relation":
        config = _value_relation(entry)
    elif widget == "range":
        config = _range(kind, entry)
    elif widget == "date":
        config = _date(kind, entry)
    elif widget == "checkbox":
        config = _checkbox(kind)
    elif widget == "text":
        config = {"IsMultiline": bool(entry.get("multiline")), "UseHtml": False}
    elif widget == "hidden":
        config = {}
    else:
        config = _relation_reference(layer, index, entry)
    return QgsEditorWidgetSetup(WIDGETS[widget], config)


def _read_only(layer, index: int, read_only: bool) -> None:
    config = layer.editFormConfig()
    config.setReadOnly(index, read_only)
    layer.setEditFormConfig(config)


def _plan(layer, entry: Dict[str, Any], seen: Set[str]):
    """The changes of one entry, checked, as calls not made yet; and the names of what they change."""
    from qgis.core import QgsDefaultValue, QgsFieldConstraints
    if not isinstance(entry, dict):
        raise ValueError("an entry is an object with field")
    index = layer.fields().lookupField(str(entry.get("field") or ""))
    if index < 0:
        raise ValueError(f"'{layer.name()}' has no field {entry.get('field')!r}")
    field = layer.fields().at(index)
    name = field.name()
    if name in seen:
        raise ValueError("the field is given twice")
    seen.add(name)
    widget = entry.get("widget")
    if widget is not None and widget not in WIDGETS:
        raise ValueError(f"widget is one of {', '.join(WIDGETS)}")
    for option, owners in _OPTIONS.items():
        if entry.get(option) not in (None, "", []) and widget not in owners:
            raise ValueError(f"{option} goes with the widget {' or '.join(owners)}")
    calls: List[Callable[[], Any]] = []
    changed: List[str] = []
    if widget is not None:
        setup = _widget(layer, index, widget, entry)
        calls.append(lambda: layer.setEditorWidgetSetup(index, setup))
        changed.append(f"widget {widget}")
    alias = entry.get("alias")
    if alias is not None:
        alias = str(alias).strip()
        if len(alias) > MAX_TEXT:
            raise ValueError(f"an alias has {MAX_TEXT} characters at most")
        calls.append((lambda: layer.setFieldAlias(index, alias)) if alias else (lambda: layer.removeFieldAlias(index)))
        changed.append("alias")
    constraint, strength = _constraints()
    chosen = strength.ConstraintStrengthHard if entry.get("enforce") else strength.ConstraintStrengthSoft
    named = []
    current, origin = field.constraints(), QgsFieldConstraints.ConstraintOrigin
    for key, kind in (("not_null", constraint.ConstraintNotNull), ("unique", constraint.ConstraintUnique)):
        wanted = entry.get(key)
        if wanted is None:
            continue
        if not wanted and current.constraintOrigin(kind) == origin.ConstraintOriginProvider:
            raise ValueError(f"its source makes it {key.replace('_', ' ')}: the form cannot lift that")
        calls.append((lambda kind=kind: layer.setFieldConstraint(index, kind, chosen)) if wanted
                     else (lambda kind=kind: layer.removeFieldConstraint(index, kind)))
        changed.append(key if wanted else f"no {key}")
        named.extend([key] if wanted else [])
    expression, text = entry.get("expression"), str(entry.get("constraint_text") or "").strip()
    if len(text) > MAX_TEXT:
        raise ValueError(f"constraint_text has {MAX_TEXT} characters at most")
    if expression is not None and str(expression).strip():
        expression = str(expression).strip()
        _check_expression(layer, expression, "expression")
        calls.append(lambda: layer.setConstraintExpression(index, expression, text))
        calls.append(lambda: layer.setFieldConstraint(index, constraint.ConstraintExpression, chosen))
        changed.append("expression")
        named.append("expression")
    elif expression is not None:
        if text:
            raise ValueError("constraint_text goes with expression, the condition it explains")
        calls.append(lambda: layer.removeFieldConstraint(index, constraint.ConstraintExpression))
        calls.append(lambda: layer.setConstraintExpression(index, ""))
        changed.append("no expression")
    elif text:
        raise ValueError("constraint_text goes with expression, the condition it explains")
    if entry.get("enforce") is not None and not named:
        raise ValueError("enforce goes with not_null, unique or expression: the constraints it makes hard")
    default, on_update = entry.get("default"), entry.get("default_on_update")
    if default is not None:
        default = str(default).strip()
        if default:
            _check_expression(layer, default, "default")
        elif on_update:
            raise ValueError("default_on_update goes with default, the expression of the value")
        calls.append(lambda: layer.setDefaultValueDefinition(index, QgsDefaultValue(default, bool(on_update))))
        changed.append("default" if default else "no default")
    elif on_update is not None:
        kept = layer.defaultValueDefinition(index).expression()
        if not kept:
            raise ValueError("default_on_update goes with default, the expression of the value")
        calls.append(lambda: layer.setDefaultValueDefinition(index, QgsDefaultValue(kept, bool(on_update))))
        changed.append("default_on_update")
    editable = entry.get("editable")
    if editable is not None:
        calls.append(lambda: _read_only(layer, index, not editable))
        changed.append("editable" if editable else "read only")
    if not calls:
        raise ValueError("nothing to change: give a widget, an alias, constraints, a default or editable")
    return calls, {"field": name, "changed": changed}


def set_form(layer: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Set how the fields of a vector layer show in its attribute form, all or nothing: every entry of ``fields`` is
    checked before the first change.

    Raises:
        ValueError: A layer that is not a vector layer, an unknown field, a widget unsuited to its field, a lookup
            layer or field missing, an expression that does not parse; nothing changed then.
    """
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    target = _vector(layer, "layer")
    if not isinstance(fields, list) or not 1 <= len(fields) <= MAX_FIELDS:
        raise ValueError(f"fields takes 1 to {MAX_FIELDS} entries")
    plans, seen = [], set()
    for number, entry in enumerate(fields, 1):
        try:
            plans.append(_plan(target, entry, seen))
        except ValueError as exc:
            field = entry.get("field") if isinstance(entry, dict) else None
            raise ValueError(f"entry {number} ({field!r}): {exc}. Nothing was changed") from None
    for calls, _summary in plans:
        for call in calls:
            call()
    soft = any(entry.get("enforce") is not True and any(entry.get(key) for key in ("not_null", "unique", "expression"))
               for entry in fields)
    note = "The form of the layer: nothing is written to the data."
    if soft:
        note += " The constraints set without enforce are soft: the form warns but saves."
    return {"layer_name": target.name(), "fields": [summary for _calls, summary in plans], "note": note}


# -- relations of the project ----------------------------------------------------------------------------------------


def _strengths():
    """The strengths of a relation, in the enum of this QGIS (Qgis.RelationshipStrength from 3.28)."""
    from qgis.core import Qgis, QgsRelation
    kinds = getattr(Qgis, "RelationshipStrength", None) or QgsRelation.RelationStrength
    return {"association": kinds.Association, "composition": kinds.Composition}


def _row(relation) -> Dict[str, Any]:
    parent, child = relation.referencedLayer(), relation.referencingLayer()
    strength = "composition" if relation.strength() == _strengths()["composition"] else "association"
    return {"id": relation.id(), "name": relation.name(),
            "parent": parent.name() if parent is not None else relation.referencedLayerId(),
            "child": child.name() if child is not None else relation.referencingLayerId(),
            "fields": [{"parent": referenced, "child": referencing}
                       for referencing, referenced in relation.fieldPairs().items()],
            "strength": strength}


def _find_relation(manager, reference: str):
    relation = manager.relation(reference) if reference else None
    if relation is not None and relation.isValid():
        return relation
    named = [item for item in manager.relations().values() if item.name() == reference]
    if not named:
        raise ValueError(f"no relation {reference!r} in the project (relations with action list names them)")
    if len(named) > 1:
        ids = ", ".join(item.id() for item in named)
        raise ValueError(f"several relations are named {reference!r}: give its id ({ids})")
    return named[0]


def relation_layers(reference: str) -> List[str]:
    """The ids of the parent and child layers of the relation ``reference`` (an id or a name); [] when unknown."""
    from qgis.core import QgsProject
    try:
        relation = _find_relation(QgsProject.instance().relationManager(), str(reference or ""))
    except ValueError:
        return []
    return [relation.referencedLayerId(), relation.referencingLayerId()]


def _add(manager, name: str, parent_layer: str, parent_field: str, child_layer: str, child_field: str,
         strength: str) -> Dict[str, Any]:
    from qgis.core import QgsProject, QgsRelation, QgsRelationContext
    if strength not in ("association", "composition"):
        raise ValueError("strength is association or composition")
    parent, child = _vector(parent_layer, "parent layer"), _vector(child_layer, "child layer")
    fields = []
    for layer, field, role in ((parent, parent_field, "parent_field"), (child, child_field, "child_field")):
        index = layer.fields().lookupField(str(field or ""))
        if index < 0:
            raise ValueError(f"{role}: '{layer.name()}' has no field {field!r}")
        fields.append(layer.fields().at(index))
    for relation in manager.relations().values():
        if relation.referencedLayerId() == parent.id() and relation.referencingLayerId() == child.id() \
                and relation.fieldPairs() == {fields[1].name(): fields[0].name()}:
            raise ValueError(f"'{child.name()}' is already linked to '{parent.name()}' by these fields: "
                             f"{relation.name()} ({relation.id()})")
    name = str(name or "").strip() or f"{child.name()} of {parent.name()}"
    if len(name) > MAX_TEXT:
        raise ValueError(f"a name has {MAX_TEXT} characters at most")
    if any(relation.name() == name for relation in manager.relations().values()):
        raise ValueError(f"a relation is already named {name!r}")
    project = QgsProject.instance()
    relation = QgsRelation(QgsRelationContext(project))
    relation.setName(name)
    relation.setReferencingLayer(child.id())
    relation.setReferencedLayer(parent.id())
    relation.addFieldPair(fields[1].name(), fields[0].name())
    relation.setStrength(_strengths()[strength])
    relation.generateId()
    base, number = relation.id(), 2
    while relation.id() in manager.relations():
        relation.setId(f"{base}_{number}")
        number += 1
    if not relation.isValid():
        raise ValueError(f"QGIS refuses this relation: {getattr(relation, 'validationError', str)() or 'invalid'}")
    manager.addRelation(relation)
    added = manager.relation(relation.id())
    if not added.isValid():
        raise ValueError("QGIS did not keep the relation")
    note = (f"The form of '{parent.name()}' lists its '{child.name()}' features; set_form with widget "
            f"relation_reference on {fields[1].name()!r} of '{child.name()}' lets each one pick its parent.")
    if strength == "composition":
        note += " Composition: deleting a parent feature deletes its children, and copying it copies them."
    if fields[0].isNumeric() != fields[1].isNumeric():
        note += (f" Warning: {fields[0].name()!r} and {fields[1].name()!r} are not of the same type (a number and a "
                 "text): the children may not be found.")
    return {"action": "add", "relation": _row(added), "note": note}


def _remove(manager, reference: str) -> Dict[str, Any]:
    if not reference:
        raise ValueError("remove needs name, the id or the name of the relation")
    relation = _find_relation(manager, reference)
    row = _row(relation)
    child = relation.referencingLayer()
    setups = [(field.name(), child.editorWidgetSetup(index)) for index, field in enumerate(child.fields())] \
        if child is not None else []
    widgets = [name for name, setup in setups
               if setup.type() == "RelationReference" and setup.config().get("Relation") == relation.id()]
    manager.removeRelation(relation.id())
    answer = {"action": "remove", "removed": row, "relations": len(manager.relations())}
    if widgets:
        answer["note"] = (f"{', '.join(widgets)} of '{child.name()}' still show a relation_reference to it: give them "
                          "another widget with set_form")
    return answer


def relations(action: str, name: str = "", parent_layer: str = "", parent_field: str = "", child_layer: str = "",
              child_field: str = "", strength: str = "association") -> Dict[str, Any]:
    """The relations of the project: list them, add one (a child layer linked to a parent layer by a field), or
    remove one by its id or name. Nothing is written to the data.

    Raises:
        ValueError: An unknown action, layer, field or relation, a link already there, a name taken.
    """
    from qgis.core import QgsProject
    manager = QgsProject.instance().relationManager()
    if action == "list":
        return {"action": "list", "relations": [_row(relation) for relation in manager.relations().values()]}
    if action not in ("add", "remove"):
        raise ValueError("action is list, add or remove")
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    if action == "add":
        return _add(manager, name, parent_layer, parent_field, child_layer, child_field, strength)
    return _remove(manager, str(name or "").strip())
