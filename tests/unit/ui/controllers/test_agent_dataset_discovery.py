"""The chat offers dataset guidance without enabling a network tool."""
from types import SimpleNamespace

import pytest

from .test_agent_chat_lifecycle import _module, controller, ctrl_module, dock  # noqa: F401

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('catalogue_disabled', [False, True])
def test_dataset_guidance_without_sources_respects_the_catalogue_tool_rule(
        ctrl_module, controller, monkeypatch, catalogue_disabled):
    monkeypatch.setattr(controller, '_accessor', lambda: SimpleNamespace(configured_domains=lambda: {}))
    monkeypatch.setattr(ctrl_module, 'qgis_databases', lambda: ())
    monkeypatch.setattr(ctrl_module, '_holds_web_service_layers', lambda: False)
    _module(monkeypatch, '.adapters.agent.chart_renderer', available=lambda: False)
    _module(monkeypatch, '.adapters.public_api.gui_control', chat_handlers=lambda: {})
    values = SimpleNamespace(**vars(ctrl_module.load_settings()))
    values.enabled_sources = []
    values.rules = {'agent_options': 'never'} if catalogue_disabled else {}
    tools, _handlers, _connectors = controller.tools_and_handlers(values)
    names = {tool.name for tool in tools}
    assert not {'search_open_data', 'search_imagery', 'add_service_layer'} & names
    loader = next(tool for tool in tools if tool.name == 'load_skill')
    assert ('datasets' in loader.input_schema['properties']['name']['enum']) is (not catalogue_disabled)


@pytest.mark.parametrize('web_enabled, forbidden', [(False, False), (True, False), (True, True)])
def test_web_search_never_grants_dataset_download_access(ctrl_module, controller, monkeypatch, web_enabled, forbidden):
    monkeypatch.setattr(controller, '_accessor', lambda: SimpleNamespace(configured_domains=lambda: {}))
    monkeypatch.setattr(ctrl_module, 'qgis_databases', lambda: ())
    monkeypatch.setattr(ctrl_module, '_holds_web_service_layers', lambda: False)
    _module(monkeypatch, '.adapters.agent.chart_renderer', available=lambda: False)
    _module(monkeypatch, '.adapters.public_api.gui_control', chat_handlers=lambda: {})
    calls = []
    def handlers(*args, **kwargs):
        calls.append(kwargs)
        return {}
    monkeypatch.setattr(ctrl_module, 'build_handlers', handlers)
    values = SimpleNamespace(**vars(ctrl_module.load_settings()))
    values.enabled_sources = ['web_search'] if web_enabled else []
    values.rules = {'search_data_sources': 'never'} if forbidden else {}
    tools, _, _ = controller.tools_and_handlers(values)
    names = {tool.name for tool in tools}
    assert ('search_data_sources' in names) is (web_enabled and not forbidden)
    assert not {'search_open_data', 'add_service_layer'} & names
    assert calls[-1]['allow_remote_sources'] is False
