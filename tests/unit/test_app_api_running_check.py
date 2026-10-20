# -*- coding: utf-8 -*-
"""
Freeze 2026-10-20: the first Filter click compiled adapters/public_api/operations.py
(about 1 100 lines) on the GUI thread only to read its ``_RUNNING`` list. Under a
loaded host the click then blocked the GUI for seconds (check_stream_ui_async on
qgis/qgis:3.34). No API operation can run before the API has loaded that module,
so the check reads it only when it is already loaded. The helper is extracted
from filter_mate_app.py with ast, like the other app tests, so the plugin module
itself is never imported.
"""
import ast
import sys
import types
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"
_PKG = "fm_api_running_test"
_OPERATIONS = _PKG + ".adapters.public_api.operations"


def _tree():
    return ast.parse(_APP.read_text(encoding="utf-8"))


def _helper():
    node = next(node for node in _tree().body
                if isinstance(node, ast.FunctionDef) and node.name == "_api_operation_running")
    namespace = {"__package__": _PKG, "__name__": _PKG + ".filter_mate_app", "sys": sys}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace["_api_operation_running"]


class _RecordingFinder:
    """Records every import of the test package (none must happen)."""

    def __init__(self):
        self.names = []

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] == _PKG:
            self.names.append(name)
        return None


@pytest.mark.unit
class TestApiOperationRunning:

    def test_api_not_loaded_is_not_running_and_is_not_imported(self, monkeypatch):
        monkeypatch.delitem(sys.modules, _OPERATIONS, raising=False)
        finder = _RecordingFinder()
        monkeypatch.setattr(sys, "meta_path", [finder] + sys.meta_path)

        assert _helper()() is False
        assert finder.names == []
        assert _OPERATIONS not in sys.modules

    def test_loaded_api_reports_its_running_operation(self, monkeypatch):
        operations = types.ModuleType(_OPERATIONS)
        operations._RUNNING = ["cross_filter"]
        monkeypatch.setitem(sys.modules, _OPERATIONS, operations)
        running = _helper()

        assert running() is True
        operations._RUNNING.clear()
        assert running() is False

    def test_task_guards_never_import_the_api_module(self):
        """manage_task and _execute_filter_task (the Filter click) ask the helper, never the module."""
        tree = _tree()
        helper = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef) and node.name == "_api_operation_running")
        inside_helper = {id(node) for node in ast.walk(helper)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = (getattr(node, "module", None) or "") + "." + ".".join(alias.name for alias in node.names)
                assert "operations" not in imported.split(".") or "public_api" not in imported, ast.unparse(node)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in inside_helper:
                assert "public_api.operations" not in node.value, node.value  # importlib / __import__ by name
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
        for name in ("manage_task", "_execute_filter_task"):
            method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
            gates = [node for node in ast.walk(method) if isinstance(node, ast.If)
                     and any(isinstance(call, ast.Call) and getattr(call.func, "id", None) == "_api_operation_running"
                             for call in ast.walk(node.test))]
            assert gates and all(isinstance(node.body[-1], ast.Return) for node in gates), name
