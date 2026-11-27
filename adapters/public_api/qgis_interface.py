"""Typed access to the QGIS window and registered plugin docks, on the GUI thread."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from ...core.domain.layer_kind import LayerKind
from .gui_control import _canvas, _face, _window
from .operations import layer_kind, resolve_layer

ACTIONS = ('attributes', 'properties', 'show_panel', 'hide_panel', 'map_tool', 'previous_view', 'next_view')
MAP_TOOLS = {'pan': 'actionPan', 'zoom_in': 'actionZoomIn', 'zoom_out': 'actionZoomOut',
             'identify': 'actionIdentify'}
PROPERTY_PAGES = {'information': 'mOptsPage_Information', 'source': 'mOptsPage_Source',
                  'style': 'mOptsPage_Style', 'metadata': 'mOptsPage_Metadata'}
MAX_PANELS = 200


def _panels(face):
    from qgis.PyQt.QtWidgets import QDockWidget
    window = face.mainWindow()
    if window is None:
        return []
    # Discover objects each time: unloaded plugins and recreated docks must not leave stale C++ handles.
    return [dock for dock in window.findChildren(QDockWidget) if dock.parentWidget() is window]


def _panel_rows(docks):
    counts = Counter(dock.objectName() for dock in docks if dock.objectName())
    rows = []
    for dock in docks:
        identifier = dock.objectName()
        if not identifier or len(identifier) > 300:
            continue
        rows.append({'id': identifier, 'title': dock.windowTitle()[:200], 'visible': dock.isVisible(),
                     'enabled': dock.isEnabled(), 'available': counts[identifier] == 1,
                     'owner': 'registered QGIS or plugin panel'})
    return sorted(rows, key=lambda row: (row['id'], row['title']))


def qgis_capabilities(iface_obj: Any = None) -> Dict[str, Any]:
    """List available typed window actions and existing registered docks without opening anything."""
    from qgis.core import Qgis
    face = _face(iface_obj)
    if face is None:
        return {'available': False, 'schema_version': 1, 'qgis_version': Qgis.QGIS_VERSION,
                'actions': [], 'panels': [], 'map_tools': [],
                'reason': 'QGIS has no window here'}
    actions = []
    for action, method in (('attributes', 'showAttributeTable'), ('properties', 'showLayerProperties')):
        actions.append({'id': action, 'available': callable(getattr(face, method, None)),
                        'owner': 'QGIS', 'effect': 'open native layer interface', 'modal': action == 'properties'})
    canvas = face.mapCanvas()
    for action, method in (('previous_view', 'zoomToPreviousExtent'), ('next_view', 'zoomToNextExtent')):
        actions.append({'id': action, 'available': canvas is not None and callable(getattr(canvas, method, None)),
                        'owner': 'QGIS', 'effect': 'navigate map history'})
    tools = []
    for name, method in MAP_TOOLS.items():
        accessor = getattr(face, method, None)
        tool = accessor() if callable(accessor) else None
        tools.append({'id': name, 'available': tool is not None and tool.isEnabled()})
    docks = _panel_rows(_panels(face))
    for action in ('show_panel', 'hide_panel'):
        actions.append({'id': action, 'available': any(row['available'] and row['enabled'] for row in docks),
                        'owner': 'QGIS window', 'effect': 'change visibility of an existing dock'})
    actions.append({'id': 'map_tool', 'available': any(row['available'] for row in tools),
                    'owner': 'QGIS', 'effect': 'choose a map tool for the user'})
    return {'available': True, 'schema_version': 1, 'qgis_version': Qgis.QGIS_VERSION, 'actions': actions, 'map_tools': tools,
            'panels': docks[:MAX_PANELS], 'panels_truncated': len(docks) > MAX_PANELS,
            'scope': 'native window operations and existing registered panels; not arbitrary plugin execution'}


def control_qgis(action: str, layer: str = '', panel: str = '', tool: str = '', page: str = 'information',
                 expression: str = '', iface_obj: Any = None) -> Dict[str, Any]:
    """Perform one known window operation. No arbitrary QAction, method name or Python is accepted."""
    if action not in ACTIONS:
        raise ValueError(f"action is one of {', '.join(ACTIONS)}")
    supplied = {name for name, value in {'layer': layer, 'panel': panel, 'tool': tool, 'expression': expression}.items()
                if value}
    allowed = {'attributes': {'layer', 'expression'}, 'properties': {'layer'},
               'show_panel': {'panel'}, 'hide_panel': {'panel'}, 'map_tool': {'tool'}}.get(action, set())
    if supplied - allowed or page != 'information' and action != 'properties':
        raise ValueError(f'unused arguments for action {action!r}')
    face = _window(iface_obj)
    if action in ('attributes', 'properties'):
        found = resolve_layer(layer)
        if found is None:
            raise ValueError(f'layer {layer!r} not found')
        layer_id, layer_name = found.id(), found.name()
        if action == 'attributes':
            if layer_kind(found) is not LayerKind.VECTOR:
                raise ValueError('an attribute table needs a vector layer')
            from .introspection import _checked_expression
            checked = _checked_expression(found, expression) if expression.strip() else ''
            opener = getattr(face, 'showAttributeTable', None)
            if not callable(opener):
                raise ValueError('this QGIS cannot open an attribute table')
            dialog = opener(found, checked)
            if dialog is None:
                raise ValueError('the attribute table could not be opened')
            dialog.show()
            dialog.raise_()
            return {'action': action, 'layer_id': layer_id, 'layer': layer_name, 'opened': True,
                    'table_expression': checked, 'layer_filter_changed': False}
        if page not in PROPERTY_PAGES:
            raise ValueError(f"page is one of {', '.join(PROPERTY_PAGES)}")
        opener = getattr(face, 'showLayerProperties', None)
        if not callable(opener):
            raise ValueError('this QGIS cannot open layer properties')
        opener(found, PROPERTY_PAGES[page])
        # QGIS uses a native modal dialog. Returning means the request was handled, not that it is still visible.
        return {'action': action, 'layer_id': layer_id, 'layer': layer_name, 'page': page,
                'requested': True, 'interaction': 'native dialog controlled by the user'}
    if action in ('show_panel', 'hide_panel'):
        matches = [dock for dock in _panels(face) if dock.objectName() == panel and panel]
        if len(matches) != 1:
            raise ValueError('panel id is missing, unavailable or ambiguous: use qgis_capabilities for current ids')
        dock = matches[0]
        if not dock.isEnabled():
            raise ValueError('this panel is disabled')
        if action == 'show_panel':
            dock.show()
            dock.raise_()
        else:
            dock.hide()
        return {'action': action, 'panel': panel, 'title': dock.windowTitle(), 'visible': dock.isVisible()}
    if action == 'map_tool':
        if tool not in MAP_TOOLS:
            raise ValueError(f"tool is one of {', '.join(MAP_TOOLS)}")
        accessor = getattr(face, MAP_TOOLS[tool], None)
        command = accessor() if callable(accessor) else None
        if command is None or not command.isEnabled():
            raise ValueError('this map tool is unavailable or disabled')
        command.trigger()
        return {'action': action, 'tool': tool, 'requested': True}
    from ..qgis.navigation import stop_navigation
    canvas = _canvas(face)
    stop_navigation(canvas)
    method = 'zoomToPreviousExtent' if action == 'previous_view' else 'zoomToNextExtent'
    callback = getattr(canvas, method, None)
    if not callable(callback):
        raise ValueError('this QGIS cannot navigate map history')
    callback()
    return {'action': action, 'extent_wkt': canvas.extent().asWktPolygon(), 'scale': canvas.scale()}


def chat_handlers(schedule_properties=None):
    from ...core.agent.tool_executor import ToolFailure

    def guarded(callback, allowed):
        def run(arguments):
            if set(arguments) - allowed:
                raise ToolFailure('unexpected QGIS interface argument')
            try:
                return callback(**arguments)
            except (ValueError, RuntimeError) as exc:
                raise ToolFailure(str(exc)) from None
        return run

    def control(**arguments):
        if arguments.get('action') == 'properties' and schedule_properties is not None:
            # Validate now, retain values only, and resolve the layer again after the turn commits.
            layer = resolve_layer(arguments.get('layer', ''))
            if layer is None:
                raise ValueError('layer not found')
            page = arguments.get('page', 'information')
            if page not in PROPERTY_PAGES or any(arguments.get(key) for key in ('panel', 'tool', 'expression')):
                raise ValueError('invalid properties arguments')
            face = _window()
            if not callable(getattr(face, 'showLayerProperties', None)):
                raise ValueError('this QGIS cannot open layer properties')
            identifier, name = layer.id(), layer.name()
            schedule_properties(lambda: control_qgis('properties', layer=identifier, page=page))
            return {'action': 'properties', 'layer_id': identifier, 'layer': name, 'page': page,
                    'scheduled': True, 'when': 'after this request finishes successfully'}
        return control_qgis(**arguments)

    return {'qgis_capabilities': guarded(qgis_capabilities, set()),
            'control_qgis': guarded(control, {'action', 'layer', 'panel', 'tool', 'page', 'expression'})}
