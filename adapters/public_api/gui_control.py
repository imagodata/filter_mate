# -*- coding: utf-8 -*-
"""What the user watches while the agent works: the designer, the highlights, the active layer, messages.

Main thread only, plain dicts out. These change what QGIS shows, not what the project holds: like ``zoom_to``
(``adapters/public_api/project_control.py``) no undo point is taken for them, and without a QGIS window they
raise ``ValueError`` instead. ``open_layout`` only opens the designer: the layout itself is made, read, changed
and exported by ``adapters/public_api/layouts.py``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.GuiControl')

MAX_FLASH = 500  # features flashing at once: more is a selection (select_features) or a zoom (zoom_to)
MAX_MESSAGE = 500  # characters of a message in the bar of QGIS
MESSAGE_LEVELS = ("info", "success", "warning", "critical")
ATLAS_ACTIONS = ("first", "previous", "next", "last")


def _face(iface_obj: Any = None) -> Any:
    """The QGIS interface, or None without a window (headless, another application)."""
    if iface_obj is not None:
        return iface_obj
    try:
        from qgis.utils import iface
    except ImportError:
        return None
    return iface


def _window(iface_obj: Any = None) -> Any:
    """The QGIS interface, or a refused call without a window."""
    face = _face(iface_obj)
    if face is None:
        raise ValueError("QGIS has no window here: this only runs with QGIS open")
    return face


def _canvas(face: Any) -> Any:
    """The map canvas, or a refused call without one."""
    canvas = face.mapCanvas() if face is not None else None
    if canvas is None:
        raise ValueError("QGIS has no map canvas here (no window)")
    return canvas


def _print_layout(name: str) -> Any:
    """The print layout ``name`` of the project, or a refused call (unknown, or a report)."""
    from qgis.core import QgsProject
    from .layouts import layout_names
    layout = QgsProject.instance().layoutManager().layoutByName(str(name or ""))
    if layout is None or type(layout).__name__ == "QgsReport":
        names = layout_names()
        raise ValueError(f"no print layout {name!r} in the project"
                         + (f": {', '.join(names)}" if names else "")
                         + (" (reports are not print layouts)" if layout is not None else ""))
    return layout


def open_layout(name: str, iface_obj: Any = None) -> Dict[str, Any]:
    """Open a print layout of the project in the layout designer of QGIS, in front.

    The layout keeps what it holds: opening it changes nothing of the project, so undoing the turn of the chat
    leaves it open. An already open layout is brought forward, not opened twice.
    """
    layout = _print_layout(name)
    face = _window(iface_obj)
    opener = getattr(face, "openLayoutDesigner", None)
    if not callable(opener):
        raise ValueError("this QGIS cannot open a layout designer")
    try:
        opener(layout)
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"the layout {layout.name()!r} could not be opened ({exc})") from None
    return {"name": layout.name(), "opened": True}


def flash_features(layer: str, expression: str, limit: int = MAX_FLASH,
                   iface_obj: Any = None) -> Dict[str, Any]:
    """Flash the features of a vector layer matching a QGIS expression (not SQL), selecting nothing.

    Only plain conditions, as ``select_features`` accepts them: an empty result, an unknown layer or a bad
    expression is refused. At most ``limit`` features flash (more is a selection or a zoom instead).
    """
    from qgis.core import QgsFeatureRequest
    found = resolve_layer(layer)
    if found is None:
        raise ValueError(f"layer {layer!r} not found")
    if layer_kind(found) is not LayerKind.VECTOR:
        raise ValueError(f"'{found.name()}' is not a vector layer")
    if not (expression or "").strip():
        raise ValueError("an expression is needed: the features to flash")
    from .introspection import _checked_expression
    checked = _checked_expression(found, expression)
    try:
        limit = max(1, min(int(limit), MAX_FLASH))
    except (TypeError, ValueError):
        limit = MAX_FLASH
    request = QgsFeatureRequest().setFilterExpression(checked).setNoAttributes().setLimit(limit + 1)
    try:
        found_features = [feature.id() for feature in found.getFeatures(request)]
    except (RuntimeError, AttributeError) as exc:
        raise ValueError(f"'{found.name()}' could not be read ({exc})") from None
    if not found_features:
        raise ValueError(f"no feature of '{found.name()}' matches {expression!r}")
    truncated = len(found_features) > limit
    shown = found_features[:limit]
    canvas = _canvas(_window(iface_obj))
    flash = getattr(canvas, "flashFeatureIds", None)
    if not callable(flash):
        raise ValueError("this QGIS cannot flash features: select_features shows them instead")
    try:
        flash(found, shown)
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"'{found.name()}' could not flash ({exc})") from None
    answer: Dict[str, Any] = {"layer": found.name(), "flashed": len(shown)}
    if truncated:
        answer["note"] = f"the first {limit} of more: narrow the expression, or select them instead"
    return answer


def set_active_layer(layer: str, reveal: bool = True, iface_obj: Any = None) -> Dict[str, Any]:
    """Make a layer of the project the active one; ``reveal`` also shows it in the layer tree, unfolded.

    The project is unchanged (the active layer is where the window looks, not what it holds): undoing the turn
    of the chat leaves it active.
    """
    found = resolve_layer(layer)
    if found is None:
        raise ValueError(f"layer {layer!r} not found")
    face = _window(iface_obj)
    setter = getattr(face, "setActiveLayer", None)
    if not callable(setter):
        raise ValueError("this QGIS cannot set the active layer")
    try:
        if setter(found) is False:
            raise ValueError(f"'{found.name()}' could not be made active")
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"'{found.name()}' could not be made active ({exc})") from None
    revealed = _reveal(face, found) if reveal else False
    return {"layer": found.name(), "active": True, "revealed": revealed}


def _reveal(face: Any, layer: Any) -> bool:
    """The layer current in the tree, its groups unfolded, scrolled into view; False when the view cannot."""
    try:
        view = face.layerTreeView()
    except (RuntimeError, AttributeError):
        return False
    if view is None:
        return False
    # A link must also work when the Layers dock was closed or behind a tabbed dock.
    try:
        from qgis.PyQt.QtWidgets import QDockWidget
        parent = view.parentWidget()
        while parent is not None:
            if isinstance(parent, QDockWidget):
                parent.show()
                parent.raise_()
                break
            parent = parent.parentWidget()
    except (RuntimeError, AttributeError, TypeError):
        pass
    try:
        view.setCurrentLayer(layer)
    except (RuntimeError, AttributeError, TypeError):
        return False
    try:
        from qgis.core import QgsProject
        node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        model = view.model()
        # QgsLayerTreeView uses a proxy model: its own node2index maps to the view's indexes.
        # Source-model indexes do not expand or scroll the real QGIS tree.
        indexer = getattr(view, "node2index", None)
        if not callable(indexer):
            indexer = getattr(model, "node2index", None)
        if node is None or not callable(indexer):
            return True  # current, but the tree cannot unfold or scroll to it
        chain: List[Any] = []
        parent = node.parent()
        while parent is not None and parent.parent() is not None:
            chain.append(parent)
            parent = parent.parent()
        for group in reversed(chain):
            try:
                view.setExpanded(indexer(group), True)
            except (RuntimeError, AttributeError, TypeError):
                pass
        try:
            view.scrollTo(indexer(node))
        except (RuntimeError, AttributeError, TypeError):
            return False
    except (RuntimeError, AttributeError):
        return True
    return True


def show_message(text: str, level: str = "info", duration: int = 5,
                 iface_obj: Any = None) -> Dict[str, Any]:
    """Show a message in the bar of QGIS, as FilterMate does for its own warnings.

    ``level`` is info, success, warning or critical; ``duration`` 1 to 60 seconds. The message is shown, never
    clicked through: for a question with choices, ask_user asks it in the thread instead.
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("a message is needed")
    if len(text) > MAX_MESSAGE:
        raise ValueError(f"a message has at most {MAX_MESSAGE} characters")
    kind = str(level or "info").lower()
    if kind not in MESSAGE_LEVELS:
        raise ValueError(f"level is one of {', '.join(MESSAGE_LEVELS)}")
    try:
        seconds = max(1, min(int(duration), 60))
    except (TypeError, ValueError):
        seconds = 5
    face = _window(iface_obj)
    bar = face.messageBar() if hasattr(face, "messageBar") else None
    if bar is None:
        raise ValueError("QGIS has no message bar here (no window)")
    from qgis.core import Qgis
    levels = getattr(Qgis, "MessageLevel", Qgis)
    qgis_level = {"info": levels.Info, "success": levels.Success,
                  "warning": levels.Warning, "critical": levels.Critical}[kind]
    try:
        bar.pushMessage("FilterMate", text, qgis_level, seconds)
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"the message could not be shown ({exc})") from None
    return {"shown": True, "level": kind}


def preview_atlas(layout: str, action: str = "next", preview: bool = True,
                  iface_obj: Any = None) -> Dict[str, Any]:
    """Turn a page of the atlas preview of a print layout: first, previous, next or last feature.

    ``preview`` also turns the atlas preview on in the designer showing the layout, so the user sees the page
    change there; a QGIS window is required even without an open designer. The atlas
    itself is unchanged (set_atlas sets it): undoing the turn of the chat leaves the page where it is. Answers
    the page turned to (1-based) and the pages of the atlas.
    """
    target = _print_layout(layout)
    atlas = target.atlas() if hasattr(target, "atlas") else None
    if atlas is None or not atlas.enabled() or atlas.coverageLayer() is None:
        raise ValueError(f"the layout {target.name()!r} has no atlas: set_atlas first")
    move_name = str(action or "next").lower()
    if move_name not in ATLAS_ACTIONS:
        raise ValueError(f"action is one of {', '.join(ATLAS_ACTIONS)}")
    face = _window(iface_obj)
    previous_page = max(0, int(atlas.currentFeatureNumber()))
    try:
        count = int(atlas.updateFeatures())
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"the atlas of {target.name()!r} could not be read ({exc})") from None
    if count <= 0:
        raise ValueError("the atlas has no page: its coverage layer, as filtered now, keeps no feature")
    page = {"first": 0, "previous": previous_page - 1, "next": previous_page + 1, "last": count - 1}[move_name]
    if not 0 <= page < count:
        atlas.seekTo(min(previous_page, count - 1))
        raise ValueError(f"the atlas has no {move_name} page from page {previous_page + 1} of {count}")
    shown = _enable_preview(face, target) if preview else False
    try:
        turned = bool(atlas.seekTo(page))
    except (RuntimeError, AttributeError, TypeError) as exc:
        raise ValueError(f"the atlas of {target.name()!r} could not turn {move_name} ({exc})") from None
    if not turned:
        raise ValueError(f"the atlas has no {move_name} page from page {atlas.currentFeatureNumber() + 1} of {count}")
    try:
        target.refresh()
    except (RuntimeError, AttributeError):
        pass
    return {"layout": target.name(), "action": move_name, "page": atlas.currentFeatureNumber() + 1,
            "pages": count, "preview": shown}


def _enable_preview(iface_obj: Any, layout: Any) -> bool:
    """The atlas preview on in the designer showing ``layout``; False without a window or such a designer."""
    face = _face(iface_obj)
    if face is None:
        return False
    try:
        designers = face.openLayoutDesigners()
    except (RuntimeError, AttributeError):
        return False
    for designer in designers or []:
        try:
            shown = designer.layout() if callable(getattr(designer, "layout", None)) else None
        except (RuntimeError, AttributeError):
            continue
        if shown is not layout:
            continue
        enabler = getattr(designer, "setAtlasPreviewEnabled", None)
        if not callable(enabler):
            return False
        try:
            enabler(True)
        except (RuntimeError, AttributeError, TypeError):
            return False
        return True
    return False


def chat_handlers() -> Dict[str, Any]:
    """Dispatch the chat-only window tools, translating refusals for the agent executor."""
    from ...core.agent.tool_executor import ToolFailure

    def guarded(callback):
        def run(arguments):
            try:
                return callback(arguments)
            except ValueError as exc:
                raise ToolFailure(str(exc)) from None
        return run

    return {
        "open_layout": guarded(lambda arguments: open_layout(arguments["name"])),
        "flash_features": guarded(lambda arguments: flash_features(
            arguments["layer"], arguments["expression"], limit=arguments.get("limit", MAX_FLASH))),
        "set_active_layer": guarded(lambda arguments: set_active_layer(
            arguments["layer"], reveal=arguments.get("reveal", True))),
        "show_message": guarded(lambda arguments: show_message(
            arguments["text"], level=arguments.get("level", "info"), duration=arguments.get("duration", 5))),
        "preview_atlas": guarded(lambda arguments: preview_atlas(
            arguments["layout"], action=arguments.get("action", "next"), preview=arguments.get("preview", True))),
    }
