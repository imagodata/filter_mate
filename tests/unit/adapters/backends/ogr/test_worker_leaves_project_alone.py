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


class _Engine:
    """A prepared source geometry: the target names it relates to, by predicate."""

    def __init__(self, relations):
        self.relations = relations  # {"intersects": {...}, "within": {...}, ...} target names

    def _test(self, name):
        return lambda geometry: geometry in self.relations.get(name, set())

    def __getattr__(self, name):
        if name in ("intersects", "within", "contains", "isEqual", "touches", "overlaps", "crosses"):
            return self._test(name)
        raise AttributeError(name)

    def prepareGeometry(self):
        pass


class _Feature:
    def __init__(self, fid, geometry):
        self._fid, self._geometry = fid, geometry

    def id(self):
        return self._fid

    def hasGeometry(self):
        return True

    def geometry(self):
        return types.SimpleNamespace(constGet=lambda: self._geometry, isEmpty=lambda: False,
                                     boundingBox=lambda: self._geometry, engine_key=self._geometry)


def _feature_by_feature(monkeypatch, source_relations, target_names, predicates):
    """Source features (their relations to the targets), target features named after their geometry."""
    sources = [_Feature(index, f"src{index}") for index in range(len(source_relations))]
    engines = {f"src{index}": _Engine(relations) for index, relations in enumerate(source_relations)}

    class _Index:
        def __init__(self):
            self.ids = []

        def addFeature(self, feature):
            self.ids.append(feature.id())

        def intersects(self, bbox):
            return list(self.ids)  # every source is a candidate: the engines decide

    qgis_core = sys.modules["qgis.core"]
    monkeypatch.setattr(qgis_core, "QgsSpatialIndex", _Index, raising=False)
    monkeypatch.setattr(qgis_core, "QgsFeatureRequest", MagicMock(), raising=False)
    monkeypatch.setattr(qgis_core, "QgsGeometry",
                        types.SimpleNamespace(createGeometryEngine=lambda geometry: engines[geometry]), raising=False)
    builder = _builder().OGRExpressionBuilder(task_params={"_processing_settings": {"transform_context": "ctx"}})
    builder._feedback = None
    source = MagicMock()
    source.getFeatures.return_value = iter(sources)
    target = MagicMock()
    target.getFeatures.return_value = iter([_Feature(index + 100, name) for index, name in enumerate(target_names)])
    project = MagicMock()
    selected = builder._select_feature_by_feature(target, source, predicates)
    project.assert_not_called()
    return selected


def test_the_fallback_tests_each_target_against_the_sources_without_selecting(monkeypatch):
    selected = _feature_by_feature(
        monkeypatch,
        # the target within the source <=> the source contains the target (union path directions)
        [{"intersects": {"a", "b"}, "contains": {"a"}}, {"intersects": {"c"}, "contains": set()}],
        ["a", "b", "c", "d"], ["within"])
    assert selected == [100]  # only "a" is within a source feature


def test_the_fallback_intersects_and_disjoint(monkeypatch):
    relations = [{"intersects": {"a"}}, {"intersects": {"c"}}]
    assert _feature_by_feature(monkeypatch, relations, ["a", "b", "c"], ["intersects"]) == [100, 102]
    assert _feature_by_feature(monkeypatch, relations, ["a", "b", "c"], ["disjoint"]) == [101]


def test_the_fallback_reads_no_selection_and_opens_no_layer():
    source = (PLUGIN_ROOT / "adapters" / "backends" / "ogr" / "expression_builder.py").read_text(encoding="utf-8")
    body = source[source.index("    def apply_filter("):source.index("    def _unfiltered_target(")]
    assert "processing.run(" not in body and "selectedFeatureIds" not in body and "removeSelection" not in body
    assert "_select_feature_by_feature(target, source_layer, names)" in body


def test_the_transform_context_is_the_one_captured_on_the_main_thread():
    builder = _builder().OGRExpressionBuilder(task_params={"_processing_settings": {"transform_context": "ctx"}})
    assert builder._transform_context() == "ctx"
