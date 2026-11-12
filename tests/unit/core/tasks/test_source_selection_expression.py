# -*- coding: utf-8 -*-
"""2026-11-12 (review): the fallbacks that read the source features use the new selection, not the source filter.

When the dock sends no source feature, the SpatiaLite / OGR fallbacks read the source features from an expression.
They read the combined source filter: under AND NOT that is ``NOT (x)``, every feature when x keeps none (the only
case they run in), so the targets were filtered by the whole source; and the QGIS expression of ``NOT (native)``
could not be found again (GLOB / CAST: "cannot be evaluated"). They now get x as the user wrote it (a QGIS
expression).
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def executor_module(monkeypatch):
    import importlib
    import sys
    import types
    package = "fmtest_selection_pkg"
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.services", _ROOT / "core" / "services")):
        module = types.ModuleType(package + name)
        module.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, package + name, module)
    ports = types.ModuleType(f"{package}.core.ports")
    ports.__path__ = []
    monkeypatch.setitem(sys.modules, ports.__name__, ports)
    qgis_port = types.ModuleType(f"{package}.core.ports.qgis_port")
    qgis_port.get_qgis_factory = MagicMock()
    monkeypatch.setitem(sys.modules, qgis_port.__name__, qgis_port)
    return importlib.import_module(f"{package}.core.services.source_layer_filter_executor")


def _context(module, old_subset=""):
    return module.FilterExecutionContext(
        task_parameters={"task": {"expression": '"class" = \'major\'', "features": []}},
        source_layer=MagicMock(), param_source_old_subset=old_subset, primary_key_name="fid",
        process_qgis_expression_callback=lambda expression: ('"class" GLOB \'major\'', None),
        combine_with_old_subset_callback=lambda expression: f"NOT (\n{expression}\n)",
        apply_filter_and_update_subset_callback=lambda expression: True,
        build_feature_id_expression_callback=lambda features: None,
    )


def test_the_selection_expression_is_the_qgis_expression_of_the_new_selection(executor_module):
    result = executor_module.SourceLayerFilterExecutor()._execute_standard_mode(
        _context(executor_module), '"class" = \'major\'', [])
    assert result.success
    assert result.expression == "NOT (\n\"class\" GLOB 'major'\n)"      # what the source layer gets
    assert result.selection_expression == '"class" = \'major\''      # what selects the source features


def test_no_selection_expression_for_the_feature_id_fallback(executor_module):
    context = _context(executor_module)
    context.process_qgis_expression_callback = lambda expression: (None, None)
    context.build_feature_id_expression_callback = lambda features: "fid IN (4)"
    result = executor_module.SourceLayerFilterExecutor()._execute_standard_mode(context, '"class" = 1', [MagicMock()])
    assert result.success and result.selection_expression is None


def test_the_source_geometry_preparation_reads_the_selection_first():
    source = (_ROOT / "core" / "tasks" / "filter_task.py").read_text(encoding="utf-8")
    for method in ("def prepare_spatialite_source_geom(self)", "def prepare_ogr_source_geom(self)"):
        body = source[source.index(method):]
        body = body[:body.index("\n    def ", 10)]
        assert "expression=self._source_selection_qgis_expression()" in body, method
    helper = source[source.index("def _source_selection_qgis_expression(self)"):]
    helper = helper[:helper.index("\n    def ", 10)]
    assert helper.index("source_selection_expression") < helper.index("source_qgis_expression")
