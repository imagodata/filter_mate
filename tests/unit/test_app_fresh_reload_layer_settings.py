# -*- coding: utf-8 -*-
"""
2026-11-24: a fresh reload starts the layers of the project from the defaults.

init_filterMate_db deletes the SQLite and puts FRESH_RELOAD_FLAG back to False before the layers are registered: the
add_layers task read False, registered every layer as new, and took the settings the project carries. The reset of
this opening is now remembered (_fresh_reload_pending), so the task skips the project's settings and clears the
variables of FilterMate. get_task_parameters is extracted with ast, like the other app tests.
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _method(name, **namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace.setdefault("logger", logging.getLogger("test"))
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace[name]


def _option(value, default):
    return value.get("value", default) if isinstance(value, dict) else (default if value is None else value)


def _app(flag, pending=None, loaded=False):
    app = SimpleNamespace(
        tasks_descriptions={"add_layers": "Adding"},
        dockwidget=SimpleNamespace(has_loaded_layers=loaded),
        CONFIG_DATA={"APP": {"OPTIONS": {"FRESH_RELOAD_FLAG": {"value": flag}}}},
        _build_layer_management_params=lambda layers, reset_flag: {"reset": reset_flag})
    if pending is not None:
        app._fresh_reload_pending = pending
    return app


@pytest.mark.unit
class TestFreshReloadReachesTheRegistration:

    def test_the_reset_remembered_by_the_database_init_reaches_the_task(self):
        get_task_parameters = _method("get_task_parameters", _get_option_value=_option)
        # the option is False again (init_filterMate_db wrote it back), the reset of this opening is remembered
        assert get_task_parameters(_app(False, pending=True), "add_layers", ["layer"]) == {"reset": True}

    def test_no_reset_otherwise(self):
        get_task_parameters = _method("get_task_parameters", _get_option_value=_option)
        assert get_task_parameters(_app(False, pending=False), "add_layers", ["layer"]) == {"reset": False}
        assert get_task_parameters(_app(False), "add_layers", ["layer"]) == {"reset": False}

    def test_not_once_layers_are_loaded(self):
        get_task_parameters = _method("get_task_parameters", _get_option_value=_option)
        assert get_task_parameters(_app(False, pending=True, loaded=True), "add_layers", ["layer"]) == {"reset": False}

    def test_init_filtermate_db_remembers_the_option_before_it_is_put_back(self):
        """init_filterMate_db reads FRESH_RELOAD_FLAG into _fresh_reload_pending before initialize_database."""
        source = ast.get_source_segment(_APP.read_text(encoding="utf-8"), next(
            node for cls in ast.parse(_APP.read_text(encoding="utf-8")).body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "init_filterMate_db"))
        assert source.index("self._fresh_reload_pending = True") < source.index("initialize_database(")

    def test_the_reset_is_used_once(self):
        """Layers removed then added later in the session keep their settings (review of 2026-11-24)."""
        get_task_parameters = _method("get_task_parameters", _get_option_value=_option)
        app = _app(False, pending=True)
        assert get_task_parameters(app, "add_layers", ["layer"]) == {"reset": True}
        assert app._fresh_reload_pending is False
        assert get_task_parameters(app, "add_layers", ["layer"]) == {"reset": False}
