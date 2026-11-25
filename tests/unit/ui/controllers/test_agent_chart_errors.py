# -*- coding: utf-8 -*-
"""Errors of the expert chart mode told without their words (audit of 2026-11-24, lot 4).

``run_chart_code`` runs code the model wrote: ``throw new Error(JSON.stringify(data))`` came back whole to the
model although the user does not share values. The real ``AgentCharts`` is loaded under a private package (real
``core`` modules, stubbed Qt and renderer); ``draw`` is replaced by a throw with the values in its words.
"""
import importlib.util
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_PKG = "fm_agent_chart_errors_test"
_ROOT = pathlib.Path(__file__).resolve().parents[4]

LEAK = 'no chart was drawn: Error: [{"nom": "secret-village", "pop": 12345}]'


class _StubQtCore(types.ModuleType):
    class QObject:
        def __init__(self, parent=None):
            pass

    class QTimer:
        def __init__(self, parent=None):
            self.timeout = SimpleNamespace(connect=lambda slot: None)

        def setSingleShot(self, single):
            pass

        def setInterval(self, ms):
            pass

    QCoreApplication = MagicMock()


def _module(monkeypatch, name, **attrs):
    module = types.ModuleType(f"{_PKG}.{name}")
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    parent, _, child = module.__name__.rpartition(".")
    if parent in sys.modules:
        monkeypatch.setattr(sys.modules[parent], child, module, raising=False)
    return module


class ChartRenderError(Exception):
    pass


@pytest.fixture
def charts_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", _StubQtCore("qgis.PyQt.QtCore"))
    root = types.ModuleType(_PKG)
    root.__path__ = [str(_ROOT)]
    monkeypatch.setitem(sys.modules, _PKG, root)
    for name, path in ((".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".ui", _ROOT / "ui"), (".ui.controllers", _ROOT / "ui" / "controllers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    _module(monkeypatch, "adapters.agent.chart_renderer", available=lambda: True,
            ChartRenderError=ChartRenderError, image=MagicMock(), drop_page=lambda: None)
    _module(monkeypatch, "adapters.public_api.charts")
    spec = importlib.util.spec_from_file_location(
        f"{_PKG}.ui.controllers.agent_charts", _ROOT / "ui" / "controllers" / "agent_charts.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def _charts(module):
    return module.AgentCharts(lambda: False, None)


def test_run_chart_code_error_hides_the_values_when_not_shared(charts_module, monkeypatch):
    charts = _charts(charts_module)
    charts.chart = lambda chart_id: SimpleNamespace(request=SimpleNamespace(), data=[], meta={}, chart_id="1")

    def draw(*args, **kwargs):
        raise ChartRenderError(LEAK)

    monkeypatch.setattr(charts_module, "draw", draw)
    with pytest.raises(charts_module.ToolFailure) as failure:
        charts.run_chart_code({"chart_id": "1", "code": "throw new Error(JSON.stringify(data))"}, False)
    assert "secret-village" not in str(failure.value) and "12345" not in str(failure.value)


def test_run_chart_code_error_kept_whole_when_shared(charts_module, monkeypatch):
    charts = _charts(charts_module)
    charts.chart = lambda chart_id: SimpleNamespace(request=SimpleNamespace(), data=[], meta={}, chart_id="1")

    def draw(*args, **kwargs):
        raise ChartRenderError(LEAK)

    monkeypatch.setattr(charts_module, "draw", draw)
    with pytest.raises(charts_module.ToolFailure) as failure:
        charts.run_chart_code({"chart_id": "1", "code": "x"}, True)
    assert str(failure.value) == LEAK


def test_show_chart_error_hides_the_values_when_not_shared(charts_module, monkeypatch):
    charts = _charts(charts_module)
    monkeypatch.setattr(charts_module, "parse_request", lambda arguments: SimpleNamespace())

    def draw(*args, **kwargs):
        raise ChartRenderError(LEAK)

    monkeypatch.setattr(charts_module, "draw", draw)
    with pytest.raises(charts_module.ToolFailure) as failure:
        charts.show_chart({}, False)
    assert "secret-village" not in str(failure.value)
