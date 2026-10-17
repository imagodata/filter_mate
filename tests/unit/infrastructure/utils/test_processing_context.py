# -*- coding: utf-8 -*-
"""
2026-10-17 (review): worker Processing contexts carry the user's settings.

A bare ``QgsProcessingContext()`` in a worker lost the invalid geometry check of
the Processing options, the project's transform context and ellipsoid. The
settings are captured on the main thread (from the context Processing builds)
and copied into a fresh context per worker call.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]


class _Context:
    def __init__(self):
        self.calls = {}

    def setTransformContext(self, value):
        self.calls['transform'] = value

    def setInvalidGeometryCheck(self, value):
        self.calls['invalid'] = value

    def setEllipsoid(self, value):
        self.calls['ellipsoid'] = value

    def setExpressionContext(self, value):
        self.calls['expression'] = value


@pytest.fixture
def module(monkeypatch):
    core = types.SimpleNamespace(QgsProcessingContext=_Context, QgsExpressionContext=lambda other=None: ("copy", other))
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    template = MagicMock()
    template.transformContext.return_value = "project datums"
    template.invalidGeometryCheck.return_value = 2
    template.ellipsoid.return_value = "EPSG:7019"
    template.expressionContext.return_value = "project scope"
    dataobjects = types.SimpleNamespace(createContext=MagicMock(return_value=template))
    processing = types.ModuleType("processing")
    processing.__path__ = []
    tools = types.ModuleType("processing.tools")
    tools.__path__ = []
    tools.dataobjects = dataobjects
    monkeypatch.setitem(sys.modules, "processing", processing)
    monkeypatch.setitem(sys.modules, "processing.tools", tools)
    monkeypatch.setitem(sys.modules, "processing.tools.dataobjects", dataobjects)
    spec = importlib.util.spec_from_file_location("fm_test_processing_context",
                                                  ROOT / "infrastructure" / "utils" / "processing_context.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded._dataobjects = dataobjects
    return loaded


def test_the_worker_context_carries_the_settings_captured_on_the_main_thread(module):
    settings = module.capture_processing_settings()
    module._dataobjects.createContext.assert_called_once_with()  # Processing's own context, main thread
    context = module.worker_processing_context()
    assert context.calls == {'transform': "project datums", 'invalid': 2, 'ellipsoid': "EPSG:7019",
                             'expression': ("copy", ("copy", "project scope"))}
    assert module.captured_transform_context() == "project datums"
    assert module.worker_processing_context(settings) is not context  # one context per call


def test_without_a_capture_the_context_is_bare(module):
    assert module.worker_processing_context().calls == {}
    assert module.captured_transform_context() is None
