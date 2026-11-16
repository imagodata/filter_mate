# -*- coding: utf-8 -*-
"""
2026-11-16 (review of the agent undo): a layer added then removed within the 500 ms of the layersAdded batch (the
undo of an agent turn that a layer refused takes back the layers it had just brought back) stayed in the batch, and
was read once deleted. Methods extracted from filter_mate_app.py with ast (see test_app_layer_store_slots).
"""
import ast
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _extract(names, namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _Layer:
    def __init__(self, layer_id, deleted=False):
        self._id, self.deleted = layer_id, deleted

    def id(self):
        if self.deleted:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        return self._id

    def providerType(self):  # noqa: N802 - Qt name
        if self.deleted:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        return "ogr"


def _app(in_project):
    project = MagicMock()
    project.mapLayer.side_effect = lambda layer_id: object() if layer_id in in_project else None
    qgs_project = types.SimpleNamespace(instance=lambda: project)
    ns = _extract(["_still_in_project", "_process_pending_added_layers"],
                  {"is_sip_deleted": lambda layer: layer.deleted, "QgsProject": qgs_project, "logger": MagicMock()})
    app = types.SimpleNamespace(manage_task=MagicMock(), _filter_usable_layers=MagicMock(return_value=[]))
    app._still_in_project = ns["_still_in_project"]
    app._process_pending_added_layers = types.MethodType(ns["_process_pending_added_layers"], app)
    return app


@pytest.mark.unit
def test_a_layer_deleted_or_removed_before_the_batch_is_left_out():
    alive, deleted, removed = _Layer("alive"), _Layer("deleted", deleted=True), _Layer("removed")
    app = _app({"alive"})
    assert app._still_in_project(alive)
    assert not app._still_in_project(deleted)
    assert not app._still_in_project(removed)
    assert not app._still_in_project(None)


@pytest.mark.unit
def test_a_batch_of_layers_all_gone_is_not_read():
    app = _app(set())
    app._pending_added_layers = [_Layer("deleted", deleted=True), _Layer("removed")]
    app._process_pending_added_layers()  # reading a deleted layer would raise
    assert app._pending_added_layers == []
    app._filter_usable_layers.assert_not_called()
    app.manage_task.assert_not_called()
