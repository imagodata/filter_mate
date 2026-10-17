# -*- coding: utf-8 -*-
"""
2026-10-17: the OGR backend, run by the filter task's worker, leaves the project alone.

- The memory source layer prepared for the OGR backend was added to the
  project (``addMapLayer``) from the worker thread, "to prevent its garbage
  collection": the project's layersAdded / willBeRemoved signals then fired
  in the worker, and a reset removed the layers from it.
- The select-by-location fallback selected in the project's target layer
  itself (worker thread, user selection wiped by the removeSelection()).
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[5]
ROOT = "filter_mate"


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load(relative, name, extra_stubs):
    stubs = {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.database": _package(f"{ROOT}.infrastructure.database"),
        f"{ROOT}.adapters": _package(f"{ROOT}.adapters"),
        f"{ROOT}.adapters.backends": _package(f"{ROOT}.adapters.backends"),
        f"{ROOT}.adapters.backends.ogr": _package(f"{ROOT}.adapters.backends.ogr"),
    }
    stubs.update(extra_stubs)
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(f"{ROOT}.adapters.backends.ogr.{name}", PLUGIN_ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class _Port:
    def __init__(self, task_params):
        self.task_params = task_params
        self.warnings = []

    def log_debug(self, msg): pass
    def log_info(self, msg): pass
    def log_warning(self, msg): self.warnings.append(msg)
    def log_error(self, msg): pass


def _sql_utils():
    module = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
    module.safe_set_subset_string = MagicMock(return_value=True)
    return module


def _executor():
    return _load("adapters/backends/ogr/filter_executor.py", "_fm_test_worker_filter_executor", {
        f"{ROOT}.infrastructure.database.sql_utils": _sql_utils(),
    })


def _builder():
    port = types.ModuleType(f"{ROOT}.core.ports.geometric_filter_port")
    port.GeometricFilterPort = _Port
    return _load("adapters/backends/ogr/expression_builder.py", "_fm_test_worker_expression_builder", {
        f"{ROOT}.core.ports": _package(f"{ROOT}.core.ports"),
        f"{ROOT}.core.ports.geometric_filter_port": port,
        f"{ROOT}.infrastructure.database.sql_utils": _sql_utils(),
    })


@pytest.fixture
def project(monkeypatch):
    project = MagicMock()
    qgis_core = sys.modules["qgis.core"]
    monkeypatch.setattr(qgis_core, "QgsProject", MagicMock(instance=MagicMock(return_value=project)), raising=False)
    return project


def _memory_layer():
    layer = MagicMock()
    layer.isValid.return_value = True
    layer.providerType.return_value = "memory"
    layer.id.return_value = "source_filtered_1"
    return layer


def test_the_prepared_memory_source_is_not_added_to_the_project(project, monkeypatch):
    executor = _executor()
    memory = _memory_layer()
    monkeypatch.setattr(executor, "determine_source_mode", lambda context: ("SUBSET", None))
    monkeypatch.setattr(executor, "validate_ogr_result_layer", lambda layer: (True, ""), raising=False)
    context = executor.OGRSourceContext(source_layer=MagicMock(), copy_filtered_layer_to_memory=lambda *a: memory)
    assert executor.prepare_ogr_source_geom(context) is memory  # the task keeps this reference
    project.addMapLayer.assert_not_called()
    assert executor._temp_layer_registry == []  # nothing for a reset to remove from the worker
    memory.setCustomProperty.assert_called_once_with('filterMate/internal_temp', True)


def test_the_selection_is_made_in_a_second_layer(monkeypatch):
    builder = _builder().OGRExpressionBuilder(task_params={})
    created = []

    def second_layer(uri, name, provider):
        copy = MagicMock()
        copy.isValid.return_value = True
        copy.subsetString.return_value = '"kind" = 2'
        copy.args = (uri, name, provider)
        created.append(copy)
        return copy

    monkeypatch.setattr(sys.modules["qgis.core"], "QgsVectorLayer", second_layer, raising=False)
    roads = MagicMock()
    roads.providerType.return_value = "ogr"
    roads.source.return_value = '/data/roads.gpkg|layername=roads|subset="kind" = 2'
    roads.subsetString.return_value = '"kind" = 2'
    roads.name.return_value = "roads"
    selection_layer = builder._selection_layer(roads, roads)
    assert selection_layer is created[0] and selection_layer is not roads
    assert created[0].args == ('/data/roads.gpkg|layername=roads|subset="kind" = 2', "roads (selection)", "ogr")
    assert selection_layer in builder._temp_layers_keep_alive


def test_a_second_layer_already_read_is_used_as_is():
    builder = _builder().OGRExpressionBuilder(task_params={})
    clone, roads = MagicMock(), MagicMock()
    assert builder._selection_layer(clone, roads) is clone


def test_a_memory_target_keeps_its_own_selection():
    builder = _builder().OGRExpressionBuilder(task_params={})
    scratch = MagicMock()
    scratch.providerType.return_value = "memory"
    scratch.name.return_value = "scratch"
    assert builder._selection_layer(scratch, scratch) is scratch
    assert builder.warnings


def test_the_fallback_reads_the_selection_of_the_second_layer():
    source = (PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py").read_text(encoding="utf-8")
    fallback = source[source.index("'native:selectbylocation',"):]
    fallback = fallback[:fallback.index("self.log_info(")]
    assert "'INPUT': selection_layer" in fallback
    assert "selection_layer.selectedFeatureIds()" in fallback and "target.selectedFeatureIds()" not in fallback
