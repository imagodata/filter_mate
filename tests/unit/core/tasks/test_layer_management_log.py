# -*- coding: utf-8 -*-
"""
2026-11-18: the log of the layer management task says what was done, not what it was given.

The 5.1.1 log read "processing 12 layers", "11 layers in project_layers", then "12 layer(s) added": the
twelfth layer is a table without geometry, left out on purpose. The count of removals was
``len(project_layers) - len(layers)``, which means nothing. The task now tallies each layer it handled.
"""
from unittest.mock import MagicMock

import pytest

from tests.unit.core.tasks.test_point_cloud_registration_guards import _FakePointCloudLayer, _task, task_mod


def _layer(layer_id, name, spatial=True):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = name
    layer.isSpatial.return_value = spatial
    return layer


@pytest.fixture
def filterable(monkeypatch):
    monkeypatch.setattr(task_mod, "get_filterable_layer_types", lambda: (MagicMock, _FakePointCloudLayer))
    monkeypatch.setattr(task_mod, "is_point_cloud_layer", lambda layer: False)


def _register_spatial(task):
    """add_project_layer stand-in: registers a spatial layer, returns False for a table without geometry."""
    def add(layer):
        if not layer.isSpatial():
            return False
        task.project_layers[layer.id()] = {"infos": {"layer_name": layer.name()}}
        return True
    task.add_project_layer = add


@pytest.mark.unit
class TestLayersReport:

    def test_a_table_without_geometry_is_not_counted_as_added(self, filterable):
        task = _task()
        _register_spatial(task)
        task.layers = [_layer("a", "zones"), _layer("b", "pts"), _layer("t", "attributes", spatial=False)]

        assert task.manage_project_layers() is True

        report = task._layers_report()
        assert report.startswith("2 of 3 layer(s) registered")
        assert "'attributes'" in report and "left out" in report
        assert task.changed_layer_ids == ["a", "b"]

    def test_a_layer_already_registered_is_said_so(self, filterable):
        task = _task()
        _register_spatial(task)
        task.project_layers["a"] = {"infos": {"layer_name": "zones"}}
        task.layers = [_layer("a", "zones"), _layer("b", "pts")]

        task.manage_project_layers()

        assert task._layers_report() == "1 of 2 layer(s) registered; already registered: 1"

    def test_a_layer_of_another_kind_is_named(self, filterable):
        task = _task()
        _register_spatial(task)
        task.layers = ["a string is not a layer", _layer("b", "pts")]

        task.manage_project_layers()

        report = task._layers_report()
        assert report.startswith("1 of 2 layer(s) registered")
        assert "not a filterable type: 1" in report

    def test_removals_count_the_layers_removed_not_a_difference_of_lengths(self, filterable):
        task = _task()
        task.task_action = "remove_layers"
        task.project_layers = {"a": {"infos": {}}, "b": {"infos": {}}, "c": {"infos": {}}}
        task.remove_project_layer = lambda layer_id: bool(task.project_layers.pop(layer_id))
        task.layers = ["a", "zz"]  # QGIS hands ids; "zz" was never registered

        assert task.manage_project_layers() is True

        assert task._layers_report() == "1 of 2 layer(s) removed, 1 not registered"
        assert sorted(task.project_layers) == ["b", "c"]

    def test_the_names_of_the_layers_left_out_are_capped(self, filterable):
        task = _task()
        _register_spatial(task)
        task.layers = [_layer(str(index), f"table{index}", spatial=False) for index in range(8)]

        task.manage_project_layers()

        report = task._layers_report()
        assert report.startswith("0 of 8 layer(s) registered")
        assert "'table4'" in report and "'table5'" not in report and "..." in report
