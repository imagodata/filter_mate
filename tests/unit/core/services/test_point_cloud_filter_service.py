# -*- coding: utf-8 -*-
"""
PointCloudFilterService (WP-F): subset application through injected callables
and history entries the existing undo/redo handler can restore.

The service is loaded by path under a private synthetic package so the domain
module (WP-A) is stubbed, never the real one: these tests do not depend on
core.domain.point_cloud_filter_criteria.
"""
import importlib.util
import pathlib
import sys
import types
from dataclasses import dataclass

import pytest

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_pc_service_test"


@dataclass(frozen=True)
class _Result:
    success: bool
    subset_string: str
    previous_subset: str = ""
    message: str = ""


class _Criteria:
    def __init__(self, subset):
        self._subset = subset

    def to_subset_string(self):
        return self._subset

    @property
    def is_empty(self):
        return not self._subset


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    module.__package__ = name
    sys.modules[name] = module
    return module


def _load_service_module():
    for name in (_PKG, f"{_PKG}.core", f"{_PKG}.core.services", f"{_PKG}.core.domain"):
        _package(name)
    domain = types.ModuleType(f"{_PKG}.core.domain.point_cloud_filter_criteria")
    domain.PointCloudFilterResult = _Result
    domain.PointCloudFilterCriteria = _Criteria
    sys.modules[domain.__name__] = domain

    name = f"{_PKG}.core.services.point_cloud_filter_service"
    path = _PROJECT_ROOT / "core" / "services" / "point_cloud_filter_service.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    module.__package__ = f"{_PKG}.core.services"
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_service_module = _load_service_module()
PointCloudFilterService = _service_module.PointCloudFilterService


class _Layer:
    def __init__(self, layer_id="pc1", subset=""):
        self._id = layer_id
        self.subset = subset

    def id(self):
        return self._id


class _LayerHistory:
    def __init__(self, layer_id, parent):
        self.layer_id = layer_id
        self._parent = parent

    def push_state(self, expression, feature_count, description="", metadata=None):
        self._parent.pushed.append({
            "layer_id": self.layer_id,
            "expression": expression,
            "feature_count": feature_count,
            "description": description,
            "metadata": dict(metadata or {}),
        })


class _HistoryService:
    def __init__(self):
        self.pushed = []

    def get_or_create_history(self, layer_id):
        return _LayerHistory(layer_id, self)

    def get_history_for_layer(self, layer_id):
        return [entry for entry in self.pushed if entry["layer_id"] == layer_id]


class _Backend:
    """Records the subset writes; ``accept`` controls the provider answer."""

    def __init__(self, accept=True):
        self.accept = accept
        self.writes = []

    def apply(self, layer, subset):
        self.writes.append((layer.id(), subset))
        if isinstance(self.accept, Exception):
            raise self.accept
        if self.accept:
            layer.subset = subset
        return self.accept

    def read(self, layer):
        return layer.subset


def _service(accept=True, history=None):
    backend = _Backend(accept)
    return PointCloudFilterService(backend.apply, backend.read, history_service=history), backend


@pytest.mark.unit
class TestApply:

    def test_applies_the_subset_and_records_history(self):
        history = _HistoryService()
        service, backend = _service(history=history)
        layer = _Layer()

        result = service.apply(layer, _Criteria("Classification IN (2, 6)"))

        assert result == _Result(True, "Classification IN (2, 6)", "", "")
        assert backend.writes == [("pc1", "Classification IN (2, 6)")]
        assert layer.subset == "Classification IN (2, 6)"
        assert history.pushed == [{
            "layer_id": "pc1",
            "expression": "Classification IN (2, 6)",
            "feature_count": -1,
            "description": "Point cloud filter: Classification IN (2, 6)",
            "metadata": {"backend": "pointcloud", "operation": "filter", "layer_count": 1},
        }]

    def test_description_is_truncated_to_sixty_characters(self):
        history = _HistoryService()
        service, _ = _service(history=history)
        subset = "Z >= 0 AND " * 12

        service.apply(_Layer(), _Criteria(subset))

        assert history.pushed[-1]["description"] == f"Point cloud filter: {subset[:60]}"

    def test_combines_with_the_existing_subset_when_asked(self):
        service, backend = _service()
        layer = _Layer(subset="Classification = 2")

        result = service.apply(layer, _Criteria("Z >= 10"), combine_with_existing=True)

        assert result.subset_string == "(Classification = 2) AND (Z >= 10)"
        assert result.previous_subset == "Classification = 2"
        assert backend.writes == [("pc1", "(Classification = 2) AND (Z >= 10)")]

    def test_replaces_the_existing_subset_by_default(self):
        service, backend = _service()
        layer = _Layer(subset="Classification = 2")

        result = service.apply(layer, _Criteria("Z >= 10"))

        assert result.subset_string == "Z >= 10"
        assert result.previous_subset == "Classification = 2"
        assert backend.writes == [("pc1", "Z >= 10")]

    def test_combine_without_previous_subset_uses_the_new_one_alone(self):
        service, _ = _service()

        result = service.apply(_Layer(), _Criteria("Z >= 10"), combine_with_existing=True)

        assert result.subset_string == "Z >= 10"

    def test_initial_state_is_recorded_before_the_first_filter_of_a_filtered_layer(self):
        history = _HistoryService()
        service, _ = _service(history=history)

        service.apply(_Layer(subset="Classification = 2"), _Criteria("Z >= 10"))

        assert [entry["expression"] for entry in history.pushed] == ["Classification = 2", "Z >= 10"]
        assert history.pushed[0]["description"] == "Initial state (before first filter)"
        assert history.pushed[0]["metadata"]["operation"] == "initial"

    def test_no_initial_state_when_the_layer_was_unfiltered(self):
        history = _HistoryService()
        service, _ = _service(history=history)

        service.apply(_Layer(), _Criteria("Z >= 10"))

        assert [entry["expression"] for entry in history.pushed] == ["Z >= 10"]

    def test_no_initial_state_when_the_layer_already_has_history(self):
        history = _HistoryService()
        service, _ = _service(history=history)
        layer = _Layer()

        service.apply(layer, _Criteria("Z >= 10"))
        service.apply(layer, _Criteria("Z >= 20"))

        assert [entry["expression"] for entry in history.pushed] == ["Z >= 10", "Z >= 20"]

    def test_rejected_subset_gives_a_failed_result_without_history(self):
        history = _HistoryService()
        service, backend = _service(accept=False, history=history)
        layer = _Layer(subset="Z >= 1")

        result = service.apply(layer, _Criteria("Z >= 10"))

        assert result.success is False
        assert result.subset_string == "Z >= 10"
        assert result.previous_subset == "Z >= 1"
        assert result.message
        assert layer.subset == "Z >= 1"
        assert history.pushed == []

    def test_writer_exception_gives_a_failed_result(self):
        service, _ = _service(accept=RuntimeError("provider gone"))

        result = service.apply(_Layer(), _Criteria("Z >= 10"))

        assert result.success is False
        assert "provider gone" in result.message

    def test_history_failure_does_not_break_the_result(self):
        class _BrokenHistory:
            def get_or_create_history(self, layer_id):
                raise RuntimeError("no history")

            def get_history_for_layer(self, layer_id):
                return []

        service, _ = _service(history=_BrokenHistory())

        result = service.apply(_Layer(), _Criteria("Z >= 10"))

        assert result.success is True

    def test_without_history_service(self):
        service, backend = _service(history=None)

        result = service.apply(_Layer(), _Criteria("Z >= 10"))

        assert result.success is True
        assert backend.writes == [("pc1", "Z >= 10")]


@pytest.mark.unit
class TestClear:

    def test_clears_the_subset_and_records_an_unfilter_entry(self):
        history = _HistoryService()
        service, backend = _service(history=history)
        layer = _Layer(subset="Z >= 10")

        result = service.clear(layer)

        assert result == _Result(True, "", "Z >= 10", "")
        assert backend.writes == [("pc1", "")]
        assert layer.subset == ""
        assert [entry["expression"] for entry in history.pushed] == ["Z >= 10", ""]
        assert history.pushed[-1]["metadata"] == {"backend": "pointcloud", "operation": "unfilter", "layer_count": 1}
        assert history.pushed[-1]["description"] == "Point cloud filter cleared"

    def test_rejected_clear_is_reported(self):
        service, _ = _service(accept=False)

        result = service.clear(_Layer(subset="Z >= 10"))

        assert result.success is False
        assert result.previous_subset == "Z >= 10"


@pytest.mark.unit
class TestCurrentSubset:

    def test_returns_the_reader_value(self):
        service, _ = _service()
        assert service.current_subset(_Layer(subset="Z >= 10")) == "Z >= 10"

    def test_none_becomes_empty_string(self):
        service = PointCloudFilterService(lambda layer, subset: True, lambda layer: None)
        assert service.current_subset(_Layer()) == ""

    def test_reader_exception_becomes_empty_string(self):
        def reader(layer):
            raise RuntimeError("deleted")

        service = PointCloudFilterService(lambda layer, subset: True, reader)
        assert service.current_subset(_Layer()) == ""


@pytest.mark.unit
class TestHistoryBinding:

    def test_history_service_can_be_bound_later(self):
        service, _ = _service(history=None)
        history = _HistoryService()
        assert service.history_service is None

        service.history_service = history
        service.apply(_Layer(), _Criteria("Z >= 10"))

        assert service.history_service is history
        assert len(history.pushed) == 1
