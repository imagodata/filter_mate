# -*- coding: utf-8 -*-
"""Public API: a web service SOURCE is read bounded in the task, as in the dock (2026-10-20).

``operations._source_job`` read a WFS source with ``list(layer.getFeatures())``
on the main thread: the whole service when nothing was selected, and a copy
cut by the provider's download limit was taken for the whole source. The
dock's rule (lot B, ``filter_executor.copy_remote_source``) now applies:
selected or filtered, copied by lot B's bounded reader in the task, an
incomplete copy refused.
"""
import concurrent.futures
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_api_remote_source_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.domain", _ROOT / "core" / "domain"),
                       (".core.services", _ROOT / "core" / "services"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return (importlib.import_module(f"{_PKG}.adapters.public_api.operations"),
            importlib.import_module(f"{_PKG}.adapters.qgis.coverage_layers.source_jobs"))


operations, source_jobs = _load()
LayerKind = importlib.import_module(f"{_PKG}.core.domain.layer_kind").LayerKind
config = importlib.import_module(f"{_PKG}.config.config")


class _Geometry:
    def __init__(self, name=""):
        self.name = name

    def isEmpty(self):
        return not self.name


class _Feature:
    def __init__(self, fid):
        self._fid = fid

    def id(self):
        return self._fid

    def hasGeometry(self):
        return True

    def geometry(self):
        return _Geometry(f"g{self._fid}")


class _Layer:
    """A WFS layer: any feature read is a failure (never on the main thread)."""

    def __init__(self, subset="", selected=()):
        self._subset, self._selected = subset, list(selected)
        self.getFeatures = MagicMock(side_effect=AssertionError("service read on the main thread"))
        self.getSelectedFeatures = MagicMock(side_effect=AssertionError("service read on the main thread"))

    def id(self):
        return "communes"

    def name(self):
        return "communes"

    def crs(self):
        return "EPSG:4326"

    def providerType(self):
        return "WFS"

    def source(self):
        return "url='https://example.invalid/wfs' typename='communes'"

    def subsetString(self):
        return self._subset

    def isValid(self):
        return True

    def selectedFeatureCount(self):
        return len(self._selected)

    def selectedFeatureIds(self):
        return list(self._selected)


class _Remote:
    """Lot B's remote_materializer as the source job calls it, recording each read."""

    def __init__(self):
        self.partial = set()
        self.supported = True
        self.rows = [1, 2, 3]
        self.reason = ""
        self.reads = []

    def module(self, name):
        module = types.ModuleType(name)
        module._snapshot = lambda layer: SimpleNamespace(source="feature source", uri=layer.source(), provider="wfs")
        module.is_partial_source = lambda layer: layer.id() in self.partial
        module.supports_materialization = lambda layer: self.supported
        module.materialization_limits = lambda params=None: ("limits", params)
        module.bounded_source_layer = lambda snapshot, limits: "bounded clone"
        module.read_bounded_features = self.read
        return module

    def read(self, source, request, limits, feedback, consume, key, source_uri=None, source_factory=None,
             provider_key=None):
        import threading
        assert threading.current_thread() is not threading.main_thread()
        reader = source if source_factory is None else source_factory()
        self.reads.append((reader, request.fids, limits, provider_key))
        if feedback.isCanceled():
            return SimpleNamespace(complete=False, reason="cancelled")
        for fid in self.rows:
            assert consume(_Feature(fid)) is False  # never a key sent to a service
        return SimpleNamespace(complete=not self.reason, reason=self.reason)


class _Request:
    def __init__(self):
        self.fids = None

    def setFilterFids(self, fids):
        self.fids = list(fids)


@pytest.fixture
def remote(monkeypatch):
    stand_in = _Remote()
    module = stand_in.module(f"{_PKG}.adapters.qgis.remote_materializer")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    for name in ("adapters.backends", "adapters.backends.ogr"):
        package = types.ModuleType(f"{_PKG}.{name}")
        package.__path__ = []
        monkeypatch.setitem(sys.modules, package.__name__, package)
    executor = types.ModuleType(f"{_PKG}.adapters.backends.ogr.filter_executor")
    executor._remote_message = lambda reason: f"dock: {reason}"
    monkeypatch.setitem(sys.modules, executor.__name__, executor)
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsFeatureRequest", _Request, raising=False)
    monkeypatch.setattr(source_jobs, "take_snapshot", lambda layer, kind: SimpleNamespace(subset=layer.subsetString()))
    monkeypatch.setattr(source_jobs, "QgsGeometry", lambda geometry=None: geometry or _Geometry())
    monkeypatch.setattr(source_jobs, "QgsCoordinateReferenceSystem", lambda crs=None: crs)
    monkeypatch.setattr(source_jobs, "union_geometries",
                        lambda geometries: _Geometry("+".join(g.name for g in geometries)))
    return stand_in


def _source_job(layer, selected_only=True):
    return operations._source_job(layer, LayerKind.VECTOR, operations.OperationReport(), selected_only, None,
                                  None, None, False, None, None)


def _compute(job, canceled=False):
    request = SimpleNamespace(buffer_value=0.0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(job.compute, request, lambda: canceled, False).result()


@pytest.mark.parametrize("selected_only", [True, False])
def test_neither_selected_nor_filtered_is_refused_before_any_read(remote, selected_only):
    layer = _Layer()
    with pytest.raises(ValueError, match="dock: unbounded_source"):
        _source_job(layer, selected_only)
    assert not remote.reads


def test_filtered_source_is_read_bounded_in_the_task(remote):
    layer = _Layer(subset='"code_dep" = \'31\'')
    job = _source_job(layer)
    assert isinstance(job, source_jobs.RemoteVectorSourceJob) and not remote.reads
    geometry = _compute(job)
    # The filtered rows, capped by the provider, within the user's budgets (as the dock).
    assert remote.reads == [("bounded clone", None, ("limits", config.ENV_VARS), "wfs")]
    assert remote.reads[0][2][1] is config.ENV_VARS
    assert geometry.name == "g1+g2+g3" and not job.message
    assert job.details["features"] == 3 and job._snapshot is None


def test_selected_features_are_read_by_id_from_the_snapshot(remote):
    remote.rows = [4, 9]
    job = _source_job(_Layer(subset='"code_dep" = \'31\'', selected=(4, 9)))
    assert _compute(job).name == "g4+g9"
    assert remote.reads == [("feature source", [4, 9], ("limits", config.ENV_VARS), "wfs")]


def test_selection_ignored_when_not_selected_only(remote):
    job = _source_job(_Layer(subset='"code_dep" = \'31\'', selected=(4,)), selected_only=False)
    _compute(job)
    assert remote.reads[0][:2] == ("bounded clone", None)


def test_unfiltered_service_with_a_selection_is_read_by_id(remote):
    remote.rows = [7]
    job = _source_job(_Layer(selected=(7,)))
    assert _compute(job).name == "g7"


@pytest.mark.parametrize("reason", ["feature_limit", "timeout"])
def test_a_partial_copy_is_never_taken_for_the_whole_source(remote, reason):
    remote.reason = reason
    job = _source_job(_Layer(subset='"code_dep" = \'31\''))
    assert _compute(job).isEmpty()
    assert job.message == f"dock: {reason} dock: incomplete_source"


def test_a_missing_selected_feature_is_refused(remote):
    remote.rows = [4]
    job = _source_job(_Layer(selected=(4, 9)))
    assert _compute(job).isEmpty() and job.message == "dock: incomplete_source"


@pytest.mark.parametrize("reason", ["read_error", "unverified_filter", "key_limit"])
def test_read_failures_are_refused(remote, reason):
    remote.reason = reason
    job = _source_job(_Layer(subset="x"))
    assert _compute(job).isEmpty() and job.message.startswith(f"dock: {reason}")


def test_cancel_reports_canceled(remote):
    job = _source_job(_Layer(subset="x"))
    assert _compute(job, canceled=True).isEmpty() and job.message == "canceled"


def test_a_partial_source_is_refused_on_the_main_thread(remote):
    remote.partial.add("communes")
    with pytest.raises(ValueError, match="dock: incomplete_source"):
        _source_job(_Layer(subset="x"))
    assert not remote.reads


def test_an_invalid_service_layer_is_refused_as_a_read_error(remote):
    """Review: its missing provider raised AttributeError out of cross_filter (only ValueError is reported)."""
    layer = _Layer(subset="x")
    layer.isValid = lambda: False
    with pytest.raises(ValueError, match="dock: read_error"):
        _source_job(layer)
    assert not remote.reads


def test_an_unverifiable_service_is_refused(remote):
    remote.supported = False
    with pytest.raises(ValueError, match="dock: unverified_filter"):
        _source_job(_Layer(subset="x"))


def test_cross_filter_reports_the_refusal(remote, monkeypatch):
    monkeypatch.setattr(operations, "_background_tasks_running", lambda: False)
    monkeypatch.setattr(operations, "layer_kind", lambda layer: LayerKind.VECTOR)
    layer = _Layer()
    project = MagicMock()
    project.mapLayer.return_value = layer
    target = MagicMock()
    monkeypatch.setattr(operations, "_project_targets", lambda targets, project, exclude, report: ([target], []))
    monkeypatch.setattr(operations, "_install_registry", lambda project: None)
    monkeypatch.setattr(operations, "_api_service", lambda: MagicMock())
    report = operations.cross_filter(layer, ["parcelles"], project=project)
    assert report.error == "dock: unbounded_source" and not report.done
    assert not remote.reads


def test_a_local_vector_source_is_read_as_before(remote, monkeypatch):
    layer = _Layer()
    layer.providerType = lambda: "ogr"
    layer.source = lambda: "/data/communes.gpkg|layername=communes"
    layer.getFeatures = MagicMock(return_value=iter([_Feature(1)]))
    job = _source_job(layer)
    assert type(job) is source_jobs.VectorSourceJob and layer.getFeatures.called
