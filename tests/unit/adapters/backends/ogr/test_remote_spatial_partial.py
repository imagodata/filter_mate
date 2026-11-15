# -*- coding: utf-8 -*-
"""A partial web service read never writes ``(old) AND NOT (keys)`` (dock, lot B).

2026-10-20: ``apply_remote_spatial_filter`` applied ``(previous filter) AND
NOT (partial keys)`` when the feature or time budget was reached. The
matching features never read were not in the list, so the filter kept
features it had to exclude. The public API refuses that case (#200,
``VectorTargetJob``); the dock now does the same, with the same message.
"""
import importlib.util
import os
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_PKG = "filter_mate"
_EXECUTOR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "adapters", "backends", "ogr", "filter_executor.py"))


def _load_executor():
    """filter_executor.py under a private name; its lazy imports resolve to the stubs below."""
    # A private name in the real package: never replaces filter_executor in sys.modules.
    spec = importlib.util.spec_from_file_location(f"{_PKG}.adapters.backends.ogr._remote_partial_executor", _EXECUTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


executor = _load_executor()


class Outcome(SimpleNamespace):
    pass


class _Geometry:
    """The few QgsGeometry calls of the remote path (a non-empty, valid union)."""

    def __init__(self, other=None):
        pass

    def isEmpty(self):
        return False

    def isGeosValid(self):
        return True

    def boundingBox(self):
        return "bbox"

    def constGet(self):
        return self

    @staticmethod
    def createGeometryEngine(geometry):
        tests = ("intersects", "within", "isEqual", "touches", "overlaps", "contains", "crosses", "relate")
        return SimpleNamespace(prepareGeometry=lambda: None, **{name: lambda other: True for name in tests})


class _Builder:
    """OGRExpressionBuilder's helpers used by apply_remote_spatial_filter (same combine rule)."""

    def __init__(self, queued):
        self.task_params = {"_subset_queue_callback": lambda layer, subset: queued.append(subset)}
        self.user_warnings = []
        self.last_error = ""
        self._feedback = None
        self.remote_materialization_outcome = None

    def _key_list_refusal(self, layer, count=None):
        return ""

    def _source_geometry(self, source, buffer_value, buffer_expression):
        return _Geometry()

    def _unfiltered_target(self, layer, old_subset=None, combine_operator=None):
        return layer

    def _transform_context(self):
        return None

    def _get_primary_key(self, layer):
        return "id"

    def _build_fid_filter_with_values(self, layer, keys, primary_key):
        return '"{}" IN ({})'.format(primary_key, ", ".join(str(key) for key in keys))

    def _is_geometric_filter(self, subset):
        return "intersects(" in (subset or "").lower()

    def _keeps_old_subset(self, old_subset, combine_operator):
        # 2026-11-12: a spatial filter is combined under AND / OR, replaced under AND NOT only
        if not old_subset or not combine_operator:
            return False
        return not (combine_operator == "AND NOT" and self._is_geometric_filter(old_subset))

    def _listed_keys(self, layer, old_subset, combine_operator, key_count, through_old=False, complement=False):
        return key_count

    def _final_subset(self, layer, old_subset, combine_operator, key_filter, through_old, complement):
        return self._combine_with_old_subset(old_subset, combine_operator, key_filter)

    def _combine_with_old_subset(self, old_subset, combine_operator, new_filter):
        if self._keeps_old_subset(old_subset, combine_operator):
            return f"({old_subset}) {combine_operator} ({new_filter})"
        if combine_operator == "AND NOT":  # no filter, or a spatial one replaced (the builder's rule)
            return f"NOT (\n{new_filter}\n)"
        return new_filter


@pytest.fixture
def remote(monkeypatch):
    """Stubs for lot B's materializer, the capability probe and Qt's translate."""
    state = SimpleNamespace(outcome=None, marked=[])
    for name in ("adapters", "adapters.qgis", "adapters.backends", "adapters.backends.ogr"):
        if f"{_PKG}.{name}" not in sys.modules:
            package = types.ModuleType(f"{_PKG}.{name}")
            package.__path__ = []
            monkeypatch.setitem(sys.modules, package.__name__, package)
    materializer = types.ModuleType(f"{_PKG}.adapters.qgis.remote_materializer")
    materializer.require_worker = lambda: None
    materializer.materialization_limits = lambda params=None: "limits"
    materializer.materialize = lambda target, rect, server, matches, limits, feedback: state.outcome
    materializer.mark_partial_result = lambda layer, partial, final: state.marked.append((partial, final))
    monkeypatch.setitem(sys.modules, materializer.__name__, materializer)
    probe = types.ModuleType(f"{_PKG}.adapters.qgis.source_capability_probe")
    probe.capability_for_layer = lambda layer: SimpleNamespace(provider_key="wfs")
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
    builder_module = types.ModuleType(f"{_PKG}.adapters.backends.ogr.expression_builder")
    builder_module.COVERED_BY_PATTERNS = builder_module.COVERS_PATTERNS = ()
    builder_module._de9im_any = lambda matrix, patterns: False
    monkeypatch.setitem(sys.modules, builder_module.__name__, builder_module)
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsGeometry", _Geometry, raising=False)
    monkeypatch.setattr(core, "QgsCoordinateTransform", lambda *args: None, raising=False)
    monkeypatch.setattr(sys.modules["qgis.PyQt.QtCore"], "QCoreApplication",
                        SimpleNamespace(translate=lambda context, text: text), raising=False)
    return state


def _apply(state, outcome, old_subset, operator):
    queued = []
    builder = _Builder(queued)
    crs = object()
    layer = SimpleNamespace(crs=lambda: crs, subsetString=lambda: "")
    source = SimpleNamespace(crs=lambda: crs)
    state.outcome = outcome
    result = executor.apply_remote_spatial_filter(builder, layer, source, ["intersects"], None, None, False,
                                                  old_subset, operator)
    return result, queued, builder


PARTIAL = Outcome(keys=(1,), complete=False, fetched=20001, reason="feature_limit")


def test_and_not_with_a_previous_filter_refuses_a_partial_result(remote):
    applied, queued, builder = _apply(remote, PARTIAL, '"nature" = 2', "AND NOT")
    assert applied is False
    assert queued == [] and remote.marked == []
    assert builder.last_error == ("Partial result: the remote feature limit was reached. AND NOT would keep "
                                  "the features not read; the previous filter is kept.")
    assert builder.last_error in builder.user_warnings


def test_the_time_budget_is_refused_alike(remote):
    outcome = Outcome(keys=(1, 2), complete=False, fetched=40, reason="timeout")
    applied, queued, builder = _apply(remote, outcome, '"nature" = 2', "AND NOT")
    assert applied is False and queued == []
    assert builder.last_error.startswith("Partial result: the remote time limit was reached. AND NOT")


@pytest.mark.parametrize("old_subset", [None, ""])
def test_and_not_without_a_filter_refuses_a_partial_result(remote, old_subset):
    """2026-11-12: no filter yet, AND NOT writes NOT (keys): the matching features never read would stay,
    as with (old) AND NOT (keys). The partial keys used to be listed (the opposite of AND NOT)."""
    applied, queued, builder = _apply(remote, PARTIAL, old_subset, "AND NOT")
    assert applied is False and queued == []
    assert builder.last_error.endswith("AND NOT would keep the features not read; the previous filter is kept.")


def test_and_not_that_replaces_a_spatial_filter_refuses_a_partial_result(remote):
    """2026-11-12 (review): a previous spatial filter is replaced, and AND NOT then writes NOT (keys): partial
    keys would keep the features never read. It used to write the partial keys themselves (the opposite)."""
    old_subset = 'intersects($geometry, geom_from_wkt(\'POINT(0 0)\'))'
    applied, queued, builder = _apply(remote, PARTIAL, old_subset, "AND NOT")
    assert applied is False and queued == []
    assert builder.last_error.endswith("AND NOT would keep the features not read; the previous filter is kept.")


def test_and_not_on_an_ogc_api_target_without_filter_is_refused(remote, monkeypatch):
    """2026-11-12 (review): an OGC API Features target wrote the keys themselves under AND NOT (no NOT can be
    proved there), as an operator other than AND already was with a previous filter."""
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.source_capability_probe"], "capability_for_layer",
                        lambda layer: SimpleNamespace(provider_key="oapif"))
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.remote_materializer"], "unfiltered_snapshot",
                        lambda layer: layer, raising=False)
    original = _Builder.__init__

    def init(self, queued):
        original(self, queued)
        self.task_params["_remote_subset_validator"] = lambda layer, expression: True  # the server takes it

    monkeypatch.setattr(_Builder, "__init__", init)
    outcome = Outcome(keys=(1, 3), complete=True, fetched=3, reason="")
    applied, queued, builder = _apply(remote, outcome, None, "AND NOT")
    assert applied is False and queued == []
    assert builder.last_error.startswith("The service filter cannot be proved complete")


@pytest.mark.parametrize("operator, expected", [
    ("AND", '("nature" = 2) AND ("id" IN (1))'),
    ("OR", '("nature" = 2) OR ("id" IN (1))'),
    (None, '"id" IN (1)'),
])
def test_other_operators_still_apply_a_partial_result_with_its_warning(remote, operator, expected):
    applied, queued, builder = _apply(remote, PARTIAL, '"nature" = 2', operator)
    assert applied is True and queued == [expected]
    assert remote.marked == [(True, expected)]


def test_a_complete_result_still_writes_and_not(remote):
    outcome = Outcome(keys=(1, 3), complete=True, fetched=3, reason="")
    applied, queued, builder = _apply(remote, outcome, '"nature" = 2', "AND NOT")
    assert applied is True
    assert queued == ['("nature" = 2) AND NOT ("id" IN (1, 3))']
    assert remote.marked == [(False, queued[0])]


def test_a_complete_result_without_a_filter_writes_not(remote):
    """2026-11-12: AND NOT on a target without a filter takes the keys out of the whole layer."""
    outcome = Outcome(keys=(1, 3), complete=True, fetched=3, reason="")
    applied, queued, builder = _apply(remote, outcome, None, "AND NOT")
    assert applied is True
    assert queued == ['NOT (\n"id" IN (1, 3)\n)']


# --- cut by the extent of the source (2026-11-15) -------------------------------------------------------------------

TOO_MANY = Outcome(keys=(), complete=False, fetched=600, reason="key_limit")
BY_EXTENT = "Cut by the extent of the source"
BOX = "intersects_bbox($geometry, geom_from_wkt('POLYGON((10 20, 30 20, 30 40.5, 10 40.5, 10 20))'))"


@pytest.fixture
def extent(remote, monkeypatch):
    """A WFS, which takes a filter by extent, and a source whose rectangle is 10 20, 30 40.5."""
    import core.domain.source_capability as capability  # the executor asks it under the package of the plugin
    for name in ("core", "core.domain"):
        if f"{_PKG}.{name}" not in sys.modules:
            package = types.ModuleType(f"{_PKG}.{name}")
            package.__path__ = []
            monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(sys.modules, f"{_PKG}.core.domain.source_capability", capability)
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.source_capability_probe"], "capability_for_layer",
                        lambda layer: capability.classify("WFS", "url='https://example.org/wfs' typename='a:b'"))
    box = SimpleNamespace(xMinimum=lambda: 10.0, yMinimum=lambda: 20.0, xMaximum=lambda: 30.0, yMaximum=lambda: 40.5)
    monkeypatch.setattr(_Geometry, "boundingBox", lambda self: box)
    return remote


@pytest.mark.parametrize("operator, old_subset, expected", [
    (None, None, BOX), ("AND", '"nature" = 2', f'("nature" = 2) AND ({BOX})'),
    ("OR", '"nature" = 2', f'("nature" = 2) OR ({BOX})'),
])
def test_more_keys_than_a_service_is_sent_cut_it_by_the_extent(extent, operator, old_subset, expected):
    """It was refused: "More than 500 keys would be sent to the service"."""
    applied, queued, builder = _apply(extent, TOO_MANY, old_subset, operator)
    assert applied is True and queued == [expected]
    assert extent.marked == [(False, expected)]  # nothing partial: the server answers every feature of the extent
    assert any(warning.startswith(BY_EXTENT) for warning in builder.user_warnings) and not builder.last_error
    assert builder.remote_materialization_outcome is None


def test_a_list_too_long_once_the_old_keys_are_counted_is_cut_by_the_extent_too(extent, monkeypatch):
    monkeypatch.setattr(_Builder, "_key_list_refusal",
                        lambda self, layer, count=None: "600 features to list" if count is not None else "")
    outcome = Outcome(keys=(1, 2), complete=True, fetched=2, reason="")
    applied, queued, builder = _apply(extent, outcome, None, None)
    assert applied is True and queued == [BOX]


def test_a_service_without_a_stable_key_is_cut_by_the_extent_and_nothing_is_read(extent, monkeypatch):
    monkeypatch.setattr(_Builder, "_key_list_refusal",
                        lambda self, layer, count=None: "no unique key field" if count is None else "")
    read = []
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.remote_materializer"], "materialize",
                        lambda *args: read.append(1))
    applied, queued, builder = _apply(extent, None, None, None)
    assert applied is True and queued == [BOX] and not read
    assert any(warning.startswith(BY_EXTENT) for warning in builder.user_warnings)


def test_and_not_is_never_cut_by_the_extent(extent, monkeypatch):
    """It would take away the features of the rectangle that do not match the source."""
    applied, queued, builder = _apply(extent, TOO_MANY, '"nature" = 2', "AND NOT")
    assert applied is False and queued == []
    assert builder.last_error.startswith("More than 500 keys would be sent")
    monkeypatch.setattr(_Builder, "_key_list_refusal",
                        lambda self, layer, count=None: "no unique key field" if count is None else "")
    applied, queued, builder = _apply(extent, None, None, "AND NOT")
    assert applied is False and queued == [] and builder.last_error == "no unique key field"


def test_disjoint_is_not_cut_by_extent(extent):
    """What lies outside the rectangle is a negation, which the validated WFS dialect does not write."""
    queued = []
    builder = _Builder(queued)
    crs = object()
    layer = SimpleNamespace(crs=lambda: crs, subsetString=lambda: "")
    extent.outcome = TOO_MANY
    applied = executor.apply_remote_spatial_filter(builder, layer, SimpleNamespace(crs=lambda: crs), ["disjoint"],
                                                   None, None, False, None, None)
    assert applied is False and queued == []
    assert builder.last_error.startswith("More than 500 keys would be sent")


@pytest.mark.parametrize("provider", ["oapif", "arcgisfeatureserver"])
def test_a_service_that_takes_no_filter_by_extent_is_refused_as_before(extent, monkeypatch, provider):
    from core.domain.source_capability import classify
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.source_capability_probe"], "capability_for_layer",
                        lambda layer: classify(provider, "url='https://example.org/x'"))
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.remote_materializer"], "unfiltered_snapshot",
                        lambda layer: layer, raising=False)
    applied, queued, builder = _apply(extent, TOO_MANY, None, None)
    assert applied is False and queued == []
    assert builder.last_error.startswith("More than 500 keys would be sent")



# A QGIS that cannot check what a service answers (before 3.26, or before 3.36 under Python 3.12) reads no service:
# the exact filter was refused there, and a WFS is now cut by the extent of the source, which needs no read.
UNVERIFIED = Outcome(keys=(), complete=False, fetched=0, reason="unverified_filter")


@pytest.mark.parametrize("operator, old_subset, expected", [
    (None, None, BOX), ("AND", '"nature" = 2', f'("nature" = 2) AND ({BOX})'),
])
def test_a_qgis_that_cannot_check_a_service_cuts_it_by_the_extent(extent, operator, old_subset, expected):
    """It was refused: "The service filter cannot be proved complete"."""
    applied, queued, builder = _apply(extent, UNVERIFIED, old_subset, operator)
    assert applied is True and queued == [expected] and not builder.last_error
    said = [warning for warning in builder.user_warnings if warning.startswith(BY_EXTENT)]
    assert len(said) == 1 and "this version of QGIS cannot check" in said[0] and "more than 500" not in said[0]
    assert builder.remote_materialization_outcome is None


def test_a_qgis_that_cannot_check_a_service_still_refuses_what_an_extent_cannot_say(extent):
    applied, queued, builder = _apply(extent, UNVERIFIED, '"nature" = 2', "AND NOT")
    assert applied is False and queued == []
    queued = []
    builder = _Builder(queued)
    crs = object()
    layer = SimpleNamespace(crs=lambda: crs, subsetString=lambda: "")
    extent.outcome = UNVERIFIED
    applied = executor.apply_remote_spatial_filter(builder, layer, SimpleNamespace(crs=lambda: crs), ["disjoint"],
                                                   None, None, False, None, None)
    assert applied is False and queued == []
    assert builder.last_error.startswith("The service filter cannot be proved complete")


@pytest.mark.parametrize("provider", ["oapif", "arcgisfeatureserver"])
def test_a_qgis_that_cannot_check_a_service_refuses_those_that_take_no_filter_by_extent(extent, monkeypatch, provider):
    from core.domain.source_capability import classify
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.source_capability_probe"], "capability_for_layer",
                        lambda layer: classify(provider, "url='https://example.org/x'"))
    monkeypatch.setattr(sys.modules[f"{_PKG}.adapters.qgis.remote_materializer"], "unfiltered_snapshot",
                        lambda layer: layer, raising=False)
    applied, queued, builder = _apply(extent, UNVERIFIED, None, None)
    assert applied is False and queued == []
    assert builder.last_error.startswith("The service filter cannot be proved complete")
