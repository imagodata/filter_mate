# -*- coding: utf-8 -*-
"""Editing the features of a vector layer, for the agent: in the edit buffer of QGIS, never saved.

The layer is put in editing mode and each call is one command of its undo stack, named after the agent, as a user's
edit would be. Nothing is written to the data source: the user reviews the changes on the map and in the attribute
table, then saves them (Save Layer Edits) or discards them. The chat keeps the index of the undo stack before its
first edit of a turn (``adapters/agent/turn_effects.py``), so undoing the turn steps back over its commands, as long
as the user has not saved or edited the layer since.

Values are converted to the type of their field first: QGIS would accept "abc" in an integer field and only fail
when the user saves. Formulas and the expressions that choose features go through the guard of Processing formulas.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from ...core.agent.sql_guard import processing_expression_problem
from ...core.domain.layer_kind import LayerKind
from .operations import busy_reason, layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.FeatureEdits')

MAX_CHANGED = 100_000
MAX_ADDED = 100
COMMAND_PREFIX = 'FilterMate agent: '
IN_BUFFER = ('The changes are in the edit buffer of the layer, not saved: the user saves them (Save Layer Edits) '
             'or discards them.')


def _editable_layer(reference: str, capability: str):
    """The vector layer, when its source allows ``capability``; put in editing mode by ``_start_editing``.

    2026-11-12: it put the layer in editing mode at once, so an edit refused afterwards (unknown field, bad WKT,
    nothing selected) left the layer in editing mode, with a transaction open in a transaction group.

    Raises:
        ValueError: Absent, not vector, read-only, its source does not allow it, or FilterMate is busy.
    """
    from qgis.core import QgsVectorDataProvider
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    layer = resolve_layer(reference)
    if layer is None:
        raise ValueError(f"layer {reference!r} not found")
    if layer_kind(layer) is not LayerKind.VECTOR:
        raise ValueError(f"'{layer.name()}' is not a vector layer: only features are edited")
    if not layer.isValid():
        raise ValueError(f"'{layer.name()}' is not available: its data source could not be opened")
    if layer.readOnly():
        raise ValueError(f"'{layer.name()}' is read-only in this project")
    flags = getattr(QgsVectorDataProvider, 'Capability', QgsVectorDataProvider)
    if not (layer.dataProvider().capabilities() & getattr(flags, capability)):
        raise ValueError(f"the data source of '{layer.name()}' does not allow this edit")
    return layer


def _start_editing(layer, text: str) -> bool:
    """Put ``layer`` in editing mode if it is not, and begin the edit command ``text``.

    Returns:
        bool: True when this call put the layer in editing mode (``_abandon`` then leaves it).

    Raises:
        ValueError: QGIS refused the editing mode.
    """
    opened = False
    if not layer.isEditable():
        if not layer.startEditing():
            raise ValueError(f"'{layer.name()}' could not be put in editing mode")
        opened = True
    layer.beginEditCommand(COMMAND_PREFIX + text[:120])
    return opened


def _abandon(layer, opened: bool) -> None:
    """Revert the edit command in progress; leave the editing mode this edit entered.

    2026-11-12: an edit failing half-way (some features added or deleted, then False) kept its changes in the
    buffer while an error was returned. The buffer of a layer the user was already editing keeps all but this
    command: only the editing mode this edit opened is rolled back (empty by then).
    """
    layer.destroyEditCommand()
    if opened:
        layer.rollBack()


def _checked(expression: str, layer) -> str:
    from qgis.core import QgsExpression
    problem = processing_expression_problem(expression)
    if problem:
        raise ValueError(f"this expression cannot be used: {problem}")
    parsed = QgsExpression(expression)
    if parsed.hasParserError():
        raise ValueError(f"invalid QGIS expression: {parsed.parserErrorString()}")
    known = {item.name().lower() for item in layer.fields()}
    from ...core.agent.sql_guard import quoted_identifiers
    unknown = sorted({name for name in quoted_identifiers(expression) if name.lower() not in known})
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)}")
    return expression


def _chosen_ids(layer, expression: str, selected_only: bool) -> List[int]:
    """The features an edit applies to: the selection, those matching ``expression``, or both.

    Raises:
        ValueError: Neither given (an edit of every feature is asked for explicitly with expression "true"), nothing
            selected, or more than ``MAX_CHANGED``.
    """
    from qgis.core import QgsFeatureRequest
    if not expression and not selected_only:
        raise ValueError('say which features: an expression, or selected_only (use the expression true for all)')
    request = QgsFeatureRequest().setNoAttributes()
    request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
    if selected_only:
        if not layer.selectedFeatureCount():
            raise ValueError(f"no feature is selected on '{layer.name()}'")
        request.setFilterFids(layer.selectedFeatureIds())
    if expression:
        request.setFilterExpression(_checked(expression, layer))
    ids = []
    for feature in layer.getFeatures(request):
        ids.append(feature.id())
        if len(ids) > MAX_CHANGED:
            raise ValueError(f"more than {MAX_CHANGED} features would change: narrow the expression")
    return ids


def _field(layer, name: str) -> int:
    """Index of a field the agent may write: of the data source, and not its key.

    Raises:
        ValueError: Unknown, joined or virtual, or a primary key.
    """
    index = layer.fields().lookupField(name or '')
    if index < 0:
        raise ValueError(f"'{layer.name()}' has no field {name!r} (describe_layer lists them)")
    origin = layer.fields().fieldOrigin(index)
    # 1 provider, 3 added while editing (2 join, 4 expression); an int in 3.22, an enum of Qgis later.
    if int(getattr(origin, 'value', origin)) not in (1, 3):
        raise ValueError(f"'{name}' is a joined or virtual field: it is not stored in this layer")
    if index in layer.primaryKeyAttributes():
        raise ValueError(f"'{name}' is the key of the layer: it is not changed")
    return index


def _converted(layer, index: int, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        raise ValueError(f"{layer.fields().at(index).name()}: a value is a number, a text, true or false, or null")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{layer.fields().at(index).name()}: not a finite number")
    try:
        return layer.fields().at(index).convertCompatible(value)
    except ValueError as exc:
        raise ValueError(f"{layer.fields().at(index).name()}: {exc}") from None


def _answer(layer, **counts) -> Dict[str, Any]:
    editing = bool(layer.isEditable())
    return {'layer_name': layer.name(), **counts, 'editing': editing, 'unsaved': editing and layer.isModified(),
            'note': IN_BUFFER}


def update_features(layer: str, values: Optional[Dict[str, Any]] = None, formulas: Optional[Dict[str, str]] = None,
                    expression: str = '', selected_only: bool = False) -> Dict[str, Any]:
    """Set fields of the features chosen by ``expression`` and/or the selection, in the edit buffer.

    Args:
        values: ``{field: value}``, each converted to the type of its field.
        formulas: ``{field: QGIS expression}`` computed on each feature ("pop" * 2, $area / 10000).

    Raises:
        ValueError: A layer or field that cannot be edited, a value of the wrong type, a refused expression.
    """
    from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeatureRequest
    values, formulas = dict(values or {}), dict(formulas or {})
    if not values and not formulas:
        raise ValueError('give values or formulas: the fields to set')
    found = _editable_layer(layer, 'ChangeAttributeValues')
    literal = {_field(found, name): (name, value) for name, value in values.items()}
    literal = {index: _converted(found, index, value) for index, (_name, value) in literal.items()}
    computed = {}
    for name, formula in formulas.items():
        expression_object = QgsExpression(_checked(str(formula), found))
        computed[_field(found, name)] = expression_object
    if set(literal) & set(computed):
        raise ValueError('a field is given both a value and a formula')
    ids = _chosen_ids(found, expression, selected_only)
    if not ids:
        return _answer(found, changed=0)
    context = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(found))
    for expression_object in computed.values():
        expression_object.prepare(context)
    changed = 0
    opened = _start_editing(found, f"set {', '.join(list(values) + list(formulas))}")
    try:
        features = found.getFeatures(QgsFeatureRequest().setFilterFids(ids)) if computed else []
        rows = {feature.id(): feature for feature in features}
        for fid in ids:
            change = dict(literal)
            if computed:
                context.setFeature(rows[fid])
                for index, expression_object in computed.items():
                    result = expression_object.evaluate(context)
                    if expression_object.hasEvalError():
                        raise ValueError(f"{found.fields().at(index).name()}: {expression_object.evalErrorString()}")
                    change[index] = _converted(found, index, result)
            if found.changeAttributeValues(fid, change):
                changed += 1
    except Exception:
        _abandon(found, opened)
        raise
    found.endEditCommand()
    return _answer(found, changed=changed)


def delete_features(layer: str, expression: str = '', selected_only: bool = False) -> Dict[str, Any]:
    """Delete the features chosen by ``expression`` and/or the selection, in the edit buffer.

    Raises:
        ValueError: A layer that cannot be edited, a refused expression, nothing chosen.
    """
    found = _editable_layer(layer, 'DeleteFeatures')
    ids = _chosen_ids(found, expression, selected_only)
    if not ids:
        return _answer(found, deleted=0)
    opened = _start_editing(found, f"delete {len(ids)} feature(s)")
    if not found.deleteFeatures(ids):
        _abandon(found, opened)  # none deleted: some could have been
        raise ValueError(f"the features of '{found.name()}' could not be deleted")
    found.endEditCommand()
    return _answer(found, deleted=len(ids))


def add_features(layer: str, features: List[Dict[str, Any]], crs: str = '') -> Dict[str, Any]:
    """Add features from WKT geometries and attributes, in the edit buffer.

    Args:
        features: ``[{"wkt": ..., "attributes": {field: value}}]``, ``MAX_ADDED`` at most.
        crs: CRS of the WKT, the CRS of the layer by default.

    Raises:
        ValueError: A layer that cannot be edited, a bad geometry or CRS, a geometry of another type or with more
            parts than the layer holds, a bad value.
    """
    from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsProject,
                           QgsWkbTypes)
    if not features:
        raise ValueError('no feature to add')
    if len(features) > MAX_ADDED:
        raise ValueError(f"{MAX_ADDED} features at most in one call")
    found = _editable_layer(layer, 'AddFeatures')
    source_crs = QgsCoordinateReferenceSystem(crs) if crs else found.crs()
    if not source_crs.isValid():
        raise ValueError(f"unknown CRS {crs!r}")
    transform = QgsCoordinateTransform(source_crs, found.crs(), QgsProject.instance())
    wanted = QgsWkbTypes.geometryType(found.wkbType())
    made = []
    for number, item in enumerate(features, 1):
        geometry = QgsGeometry.fromWkt(str(item.get('wkt') or ''))
        if geometry.isNull():
            raise ValueError(f"feature {number}: not a WKT geometry")
        if QgsWkbTypes.geometryType(geometry.wkbType()) != wanted:
            raise ValueError(f"feature {number}: '{found.name()}' holds {QgsWkbTypes.geometryDisplayString(wanted)} "
                             "geometries")
        if source_crs != found.crs():
            try:
                geometry.transform(transform)
            except Exception:  # QgsCsException: outside the domain of one of the CRS
                raise ValueError(f"feature {number}: its coordinates do not fit the CRS {source_crs.authid()}") from None
        # 2026-11-12: the type of the layer: multi or single part, Z and M added (0) or dropped. A multi-part
        # geometry used to be stored as such in a single-part layer, and Z / M were left as given.
        coerced = geometry.coerceToType(found.wkbType())
        if len(coerced) > 1:
            raise ValueError(f"feature {number}: '{found.name()}' holds single-part geometries, this one has "
                             f"{len(coerced)} parts: add each part as a feature")
        if not coerced or coerced[0].isNull():
            raise ValueError(f"feature {number}: cannot be stored as {QgsWkbTypes.displayString(found.wkbType())}")
        geometry = coerced[0]
        feature = QgsFeature(found.fields())
        feature.setGeometry(geometry)
        for name, value in (item.get('attributes') or {}).items():
            index = _field(found, name)
            feature.setAttribute(index, _converted(found, index, value))
        made.append(feature)
    opened = _start_editing(found, f"add {len(made)} feature(s)")
    if not found.addFeatures(made):
        _abandon(found, opened)  # none added: some could have been
        raise ValueError(f"the features could not be added to '{found.name()}'")
    found.endEditCommand()
    return _answer(found, added=len(made))


def edit_state(layer) -> Dict[str, Any]:
    """Whether a layer is being edited and holds unsaved changes."""
    editable = bool(layer.isEditable()) if hasattr(layer, 'isEditable') else False
    return {'editing': editable, 'unsaved': bool(editable and layer.isModified())}
