"""Typed interface operations do not dispatch arbitrary methods or confuse titles with dock ids."""
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from .test_gui_control import _PKG, _Layer

interface = importlib.import_module(_PKG + '.adapters.public_api.qgis_interface')
ToolFailure = importlib.import_module(_PKG + '.core.agent.tool_executor').ToolFailure
pytestmark = pytest.mark.unit


class Dock:
    def __init__(self, name, title='Plugin panel', enabled=True):
        self.name, self.title, self.enabled, self.visible = name, title, enabled, False
        self.parent = None
        self.raised = 0

    def objectName(self):
        return self.name

    def windowTitle(self):
        return self.title

    def isVisible(self):
        return self.visible

    def isEnabled(self):
        return self.enabled

    def parentWidget(self):
        return self.parent

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def raise_(self):
        self.raised += 1


@pytest.fixture
def session(monkeypatch):
    docks = [Dock('ProcessingToolbox'), Dock('plugin.panel'), Dock('disabled', enabled=False), Dock('')]
    window = SimpleNamespace(findChildren=lambda kind: docks)
    for dock in docks:
        dock.parent = window
    command = SimpleNamespace(isEnabled=lambda: True, trigger=MagicMock())
    dialog = SimpleNamespace(show=MagicMock(), raise_=MagicMock())
    face = SimpleNamespace(mainWindow=lambda: window, mapCanvas=MagicMock(return_value=MagicMock()),
                           actionPan=lambda: command, showAttributeTable=MagicMock(return_value=dialog),
                           showLayerProperties=MagicMock())
    layer = _Layer()
    monkeypatch.setattr(interface, 'resolve_layer', lambda name: layer if name in ('communes', layer.id()) else None)
    monkeypatch.setattr(interface, 'layer_kind', lambda found: interface.LayerKind.VECTOR)
    monkeypatch.setattr(sys.modules[_PKG + '.adapters.public_api.introspection'], '_checked_expression',
                        lambda found, expression: expression)
    monkeypatch.setattr(sys.modules['qgis.core'], 'Qgis', SimpleNamespace(QGIS_VERSION='test'))
    return SimpleNamespace(docks=docks, window=window, face=face, command=command, dialog=dialog, layer=layer)


def test_capabilities_are_observational_and_report_ambiguous_disabled_and_unnamed_panels(session):
    session.docks.append(Dock('plugin.panel'))
    session.docks[-1].parent = session.window
    result = interface.qgis_capabilities(session.face)
    assert result['available']
    assert not any(row['id'] == '' for row in result['panels'])
    assert not any(row['available'] for row in result['panels'] if row['id'] == 'plugin.panel')
    assert next(row for row in result['panels'] if row['id'] == 'disabled')['enabled'] is False
    assert not any(dock.visible for dock in session.docks)
    session.command.trigger.assert_not_called()


def test_plugin_panels_use_live_ids_and_disappear_after_unload(session):
    assert interface.control_qgis('show_panel', panel='plugin.panel', iface_obj=session.face)['visible']
    assert session.docks[1].raised == 1
    assert not interface.control_qgis('hide_panel', panel='plugin.panel', iface_obj=session.face)['visible']
    session.docks.pop(1)
    with pytest.raises(ValueError, match='unavailable or ambiguous'):
        interface.control_qgis('show_panel', panel='plugin.panel', iface_obj=session.face)
    with pytest.raises(ValueError, match='unavailable or ambiguous'):
        interface.control_qgis('show_panel', panel='Plugin panel', iface_obj=session.face)


def test_nested_or_disabled_panels_are_not_controllable(session):
    session.docks[1].parent = object()
    with pytest.raises(ValueError, match='unavailable or ambiguous'):
        interface.control_qgis('show_panel', panel='plugin.panel', iface_obj=session.face)
    with pytest.raises(ValueError, match='disabled'):
        interface.control_qgis('show_panel', panel='disabled', iface_obj=session.face)


def test_attribute_table_filters_only_the_native_table(session):
    result = interface.control_qgis('attributes', layer='communes', expression='"pop" > 10', iface_obj=session.face)
    session.face.showAttributeTable.assert_called_once_with(session.layer, '"pop" > 10')
    assert result['opened'] and result['layer_filter_changed'] is False
    assert result['table_expression'] == '"pop" > 10'
    session.dialog.raise_.assert_called_once()


def test_properties_are_an_explicit_native_handoff(session):
    result = interface.control_qgis('properties', layer='communes', page='style', iface_obj=session.face)
    session.face.showLayerProperties.assert_called_once_with(session.layer, 'mOptsPage_Style')
    assert result['requested'] and 'opened' not in result
    with pytest.raises(ValueError, match='page is one of'):
        interface.control_qgis('properties', layer='communes', page='runPython', iface_obj=session.face)


def test_map_tools_are_a_fixed_safe_set(session):
    interface.control_qgis('map_tool', tool='pan', iface_obj=session.face)
    session.command.trigger.assert_called_once()
    with pytest.raises(ValueError, match='tool is one of'):
        interface.control_qgis('map_tool', tool='actionSaveProject', iface_obj=session.face)
    with pytest.raises(ValueError, match='action is one of'):
        interface.control_qgis('trigger', tool='actionSaveProject', iface_obj=session.face)


def test_no_window_is_reported_and_injected_interfaces_are_refused(monkeypatch):
    monkeypatch.setattr(interface, '_face', lambda obj: None)
    assert interface.qgis_capabilities()['available'] is False
    handlers = interface.chat_handlers()
    with pytest.raises(ToolFailure, match='unexpected QGIS interface argument'):
        handlers['control_qgis']({'action': 'show_panel', 'iface_obj': 'not allowed'})


def test_window_errors_are_tool_failures_and_unused_arguments_are_refused(session, monkeypatch):
    with pytest.raises(ValueError, match='unused arguments'):
        interface.control_qgis('map_tool', tool='pan', layer='communes', iface_obj=session.face)
    def unavailable(*args):
        raise ValueError('QGIS has no window here')
    monkeypatch.setattr(interface, '_window', unavailable)
    with pytest.raises(ToolFailure, match='no window'):
        interface.chat_handlers()['control_qgis']({'action': 'map_tool', 'tool': 'pan'})


def test_properties_can_be_scheduled_with_values_only_and_resolve_the_layer_again(session, monkeypatch):
    waiting = []
    monkeypatch.setattr(interface, '_window', lambda *args: session.face)
    handlers = interface.chat_handlers(waiting.append)
    answer = handlers['control_qgis']({'action': 'properties', 'layer': 'communes', 'page': 'metadata'})
    assert answer['scheduled'] and 'requested' not in answer
    session.face.showLayerProperties.assert_not_called()
    waiting.pop()()
    session.face.showLayerProperties.assert_called_once_with(session.layer, 'mOptsPage_Metadata')
    handlers['control_qgis']({'action': 'properties', 'layer': 'communes'})
    monkeypatch.setattr(interface, 'resolve_layer', lambda reference: None)
    with pytest.raises(ValueError, match='not found'):
        waiting.pop()()
