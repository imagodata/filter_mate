# -*- coding: utf-8 -*-
"""The local copy of a web service layer for the agent, the REST API and the MCP server (2026-11-22).

``local_copy`` copies a WFS, WMS, WMTS or XYZ layer over the visible map (or an area) to a file next to the project
and makes the layer read it, or puts it back on its service. It goes through the copies of the dock
(``ui/controllers/stream_copy_actions``), so that the button of the rail and the menu of the layers see the copy
under way, and waits for its end while the event loop turns; Stop cancels it.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from ..agent.bounded_http import on_abort
from .operations import busy_reason, resolve_layer, running

ACTIONS = ('copy', 'back', 'again')


def _actions():
    from ...ui.controllers.stream_copy_actions import get
    actions = get()
    if actions is None:
        raise ValueError("the local copies are not available: FilterMate is not started in QGIS")
    return actions


def _answer(layer, record, notes=()) -> Dict[str, Any]:
    from ...adapters.qgis.stream_copy import copy_text
    answer: Dict[str, Any] = {'layer_id': layer.id(), 'name': layer.name(), 'reads': 'service'}
    if record is not None:
        # The name of its folder only: the path of the user's home does not go to the provider of the model.
        answer.update({'reads': 'local copy', 'kind': record.kind, 'file': os.path.basename(record.path),
                       'folder': os.path.basename(os.path.dirname(record.path)), 'complete': record.complete,
                       'summary': copy_text(record)})
        if record.kind == 'features':
            answer['feature_count'] = record.features
        else:
            answer['resolution'] = record.resolution
            answer['holes'] = record.holes
    if notes:
        answer['notes'] = list(notes)
    return answer


def plan_for(layer, extent_wkt: str = '', crs: str = ''):
    """The plan of the copy of ``layer`` (a project layer) over ``extent_wkt`` in ``crs``, the visible map when
    empty; what the question of the chat shows before the copy. Nothing is read from the service.

    Raises:
        ValueError: ``extent_wkt`` or ``crs`` cannot be read.
    """
    from ...adapters.qgis import stream_copy
    extent = extent_crs = None
    if (extent_wkt or '').strip():
        from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry
        geometry = QgsGeometry.fromWkt(extent_wkt)
        if geometry is None or geometry.isEmpty():
            raise ValueError("extent_wkt is not a geometry")
        extent = geometry.boundingBox()
        extent_crs = QgsCoordinateReferenceSystem(crs) if crs else None
        if extent_crs is None:
            from qgis.utils import iface
            extent_crs = iface.mapCanvas().mapSettings().destinationCrs()
        if not extent_crs.isValid():
            raise ValueError(f"unknown CRS {crs!r}")
    # An area given: a WMS is drawn at most at twice the detail of a map 1000 pixels wide over it.
    return stream_copy.plan_copy(layer, extent, extent_crs, 1000 if extent is not None else 0)


def local_copy(layer: str, action: str = 'copy', extent_wkt: str = '', crs: str = '') -> Dict[str, Any]:
    """Copy ``layer`` (a web service) over the visible map, or ``extent_wkt``, and make it read the copy; with
    ``action`` back, make it read its service again (the file stays); with ``action`` again, copy the area of its
    copy anew at the same detail (the previous file replaced; read again when the new copy is not made).

    Raises:
        ValueError: An unknown layer, a layer that is no web service, a copy refused (terms of the server, nothing
            in the area, too old a QGIS) or failed; the message says why.
    """
    from ...adapters.qgis import stream_copy
    action = (action or 'copy').strip().lower()
    if action not in ACTIONS:
        raise ValueError(f"action is one of {', '.join(ACTIONS)}")
    found = resolve_layer(layer)
    if found is None:
        raise ValueError(f"layer {layer!r} not found")
    if action != 'copy' and (extent_wkt or '').strip():
        raise ValueError(f"extent_wkt is for action copy: action {action} keeps the area of the copy")
    actions = _actions()
    if action == 'back':
        try:
            notes = stream_copy.switch_to_stream(found)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from None
        actions._changed(found.id())
        return _answer(found, None, notes)
    busy = busy_reason()
    if busy:
        raise ValueError(busy)
    previous = None
    if action == 'again':
        if not stream_copy.is_local_copy(found):
            raise ValueError(f"'{found.name()}' does not read a local copy: call local_copy with action copy")
        try:
            plan, previous = stream_copy.recopy_plan(found)  # on its service now, or on its copy again if refused
        except RuntimeError as exc:
            raise ValueError(str(exc)) from None
        actions._changed(found.id())
    elif stream_copy.is_local_copy(found):
        raise ValueError(f"'{found.name()}' already reads its local copy: call local_copy with action again to copy "
                         "the same area anew, or back to read its service")
    else:
        plan = plan_for(found, extent_wkt, crs)
    if plan.refusal:
        raise ValueError(plan.refusal)
    from qgis.PyQt.QtCore import QEventLoop, QTimer
    done = []
    with running('local_copy'):
        refusal = actions.copy(found, confirm=False, plan=plan, on_done=done.append, restore=previous)
        if refusal:
            raise ValueError(refusal)
        found_id = found.id()
        task = actions._tasks.get(found_id)
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(100)
        # Its end, or the plugin stopped meanwhile (its copies cancelled without a word: no end to wait for).
        timer.timeout.connect(lambda: loop.quit() if done or found_id not in actions._tasks or _get() is not actions
                              else None)
        forget = on_abort(lambda: _cancel(task))
        try:
            timer.start()
            if not done:
                loop.exec()
        finally:
            timer.stop()
            forget()
    ended = done[0] if done else None
    try:
        name = found.name()
    except RuntimeError:  # removed meanwhile (the project closed)
        raise ValueError(f"{layer!r} was removed during its copy") from None
    if ended is None or ended.result.record is None:
        error = ended.result.error if ended is not None else 'FilterMate stopped during the copy'
        raise ValueError(f"'{name}' was not copied: {error}")
    record = stream_copy.record_of(found)
    if record is None:
        raise ValueError(f"'{name}' was copied to {os.path.basename(ended.plan.path)} but does not read it")
    return _answer(found, record)


def _get():
    from ...ui.controllers.stream_copy_actions import get
    return get()


def _cancel(task) -> None:
    try:
        if task is not None:
            task.cancel()
    except RuntimeError:  # deleted with its end
        pass
