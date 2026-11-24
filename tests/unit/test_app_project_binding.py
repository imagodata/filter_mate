# -*- coding: utf-8 -*-
"""
2026-11-24 (review): FilterMateApp is bound to the project on screen, or to none.

A project closed (QgsProject.cleared) unbinds the app (unbind_project); the next project is bound once QGIS has read
or created it (filter_mate.py), or when something needs its database first (ensure_project_bound): a favorite added
(FavoritesService), layers registered (add_layers), the panel opened again. Binding keeps a new project with no file
clean; the dirty flag of a project opened from a file is not touched (its reconciled favorites must be saved). The
methods are extracted from filter_mate_app.py with ast, like the other app tests.
"""
import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_APP = Path(__file__).resolve().parents[2] / "filter_mate_app.py"


def _method(name, **namespace):
    tree = ast.parse(_APP.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FilterMateApp")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace.setdefault("logger", logging.getLogger("test"))
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace[name]


class Project:
    def __init__(self, file_name="", dirty=False):
        self.file_name, self.dirty, self.set_dirty = file_name, dirty, []

    def fileName(self):  # noqa: N802 - the QGIS name
        return self.file_name

    def isDirty(self):  # noqa: N802 - the QGIS name
        return self.dirty

    def setDirty(self, dirty=True):  # noqa: N802 - the QGIS name
        self.dirty = dirty
        self.set_dirty.append(dirty)


def _app(project):
    app = SimpleNamespace(PROJECT=project, project_uuid=None, favorites_manager=SimpleNamespace(is_bound=False))

    def init():  # writing the id of the project in it makes it dirty
        app.project_uuid = "bound"
        app.favorites_manager.is_bound = True
        project.dirty = True

    app.init_filterMate_db = init
    app.bind_current_project = lambda: _method("bind_current_project")(app)
    return app


class TestBindCurrentProject:

    def test_a_new_project_nobody_changed_stays_clean(self):
        project = Project()
        _method("bind_current_project")(_app(project))
        assert project.set_dirty == [False]

    def test_an_opened_project_keeps_what_the_binding_wrote(self):
        """sync_with_project wrote the favorites reconciled with this computer: the next save must carry them."""
        project = Project("/work/travel.qgz")
        _method("bind_current_project")(_app(project))
        assert project.set_dirty == [] and project.dirty

    def test_a_new_project_already_changed_stays_changed(self):
        project = Project(dirty=True)
        _method("bind_current_project")(_app(project))
        assert project.set_dirty == []

    def test_a_failed_binding_is_logged_not_raised(self):
        app = _app(Project())
        app.init_filterMate_db = MagicMock(side_effect=RuntimeError("locked"))
        _method("bind_current_project")(app)  # a timer slot: no Python error dialog


class TestEnsureProjectBound:

    def test_binds_when_nothing_is_bound(self):
        app = _app(Project())
        assert _method("ensure_project_bound")(app) is True and app.project_uuid == "bound"

    def test_nothing_when_bound(self):
        app = _app(Project())
        app.project_uuid, app.favorites_manager.is_bound = "already", True
        app.init_filterMate_db = MagicMock()
        assert _method("ensure_project_bound")(app) is True
        app.init_filterMate_db.assert_not_called()

    def test_binds_when_the_favorites_were_let_go(self):
        """FavoritesService._on_project_cleared lets go of the favorites even when the app kept an id."""
        app = _app(Project())
        app.project_uuid = "stale"
        _method("ensure_project_bound")(app)
        assert app.project_uuid == "bound"

    def test_false_when_nothing_could_be_bound(self):
        app = _app(Project())
        app.init_filterMate_db = MagicMock()
        assert _method("ensure_project_bound")(app) is False


def test_unbind_project_resets_the_app_and_the_database_manager():
    app = SimpleNamespace(project_uuid="closed", _database_manager=SimpleNamespace(project_uuid="closed"),
                          _fresh_reload_pending=True, _binding_failed=True)
    _method("unbind_project")(app)
    assert app.project_uuid is None and app._database_manager.project_uuid is None
    # a fresh reload this project did not use is not the next project's; the next project is tried again
    assert app._fresh_reload_pending is False and app._binding_failed is False


def test_a_database_that_cannot_be_opened_is_not_tried_at_each_favorite():
    """initialize_database failed: not tried again (nor its error shown again) at each favorite, layer added or
    opening of the panel, until the project changes."""
    app = _app(Project())
    calls = []
    app.init_filterMate_db = lambda: calls.append(1)  # binds nothing
    ensure = _method("ensure_project_bound")
    assert ensure(app) is False and ensure(app) is False
    assert calls == [1]
    app._database_manager = None
    _method("unbind_project")(app)  # the next project (QgsProject.cleared)
    ensure(app)
    assert calls == [1, 1]


class TestFreshReloadSurvivesASecondBinding:
    """A second init_filterMate_db (the option already put back to False) set _fresh_reload_pending to False."""

    def _init(self, app, flag):
        app.CONFIG_DATA = {"APP": {"OPTIONS": {"FRESH_RELOAD_FLAG": {"value": flag}}}}
        _method("init_filterMate_db", os=__import__("os"), ENV_VARS={"CONFIG_JSON_PATH": "x"},
                _get_option_value=lambda value, default: value.get("value", default))(app)

    def _app(self):
        project = MagicMock()
        project.absoluteFilePath.return_value = "/work/travel.qgz"
        project.absolutePath.return_value = "/work"
        manager = MagicMock()
        manager.initialize_database.side_effect = lambda config_data, **_: (False, config_data)
        return SimpleNamespace(PROJECT=project, _database_manager=manager)

    def test_the_reset_of_this_opening_is_kept(self):
        app = self._app()
        self._init(app, True)
        assert app._fresh_reload_pending is True
        self._init(app, False)  # bound again: the option is False now
        assert app._fresh_reload_pending is True

    def test_no_reset_no_flag(self):
        app = self._app()
        self._init(app, False)
        assert getattr(app, "_fresh_reload_pending", False) is False


def test_the_panel_opened_again_binds_the_project():
    """Opened again after a project was opened or closed with the panel closed (FilterMateApp.run)."""
    run = _method("run", HEXAGONAL_AVAILABLE=True)
    app = MagicMock()
    app._app_initializer.initialize_application.return_value = True
    run(app)
    app.ensure_project_bound.assert_called_once_with()
    first = MagicMock(dockwidget=None)
    first._app_initializer.initialize_application.return_value = True
    run(first)
    first.ensure_project_bound.assert_not_called()  # the first run binds in init_filterMate_db


def test_layers_registered_bind_the_project_first():
    """Project > Close, then a layer added: its settings go under the project on screen (manage_task add_layers)."""
    order = []
    app = MagicMock(_unloading=False, _removing_all_layers=False, _initializing_project=False, _pending_add_layers_tasks=0,
                    dockwidget=None,
                    tasks_descriptions={"add_layers": "Adding"})
    app.ensure_project_bound.side_effect = lambda: order.append("bind")
    app._task_orchestrator.dispatch_task.side_effect = lambda *a: order.append("dispatch")
    manage_task = _method("manage_task", _api_operation_running=lambda: False, perf_elapsed_ms=lambda name: 1,
                          perf_mark_start=lambda name: None, STABILITY_CONSTANTS={})
    manage_task(app, "add_layers", ["layer"])
    assert order == ["bind", "dispatch"]


def test_the_plugin_unloaded_releases_the_favorites():
    app = MagicMock(_unloading=False, _canvas_frozen_token=None)
    _method("cleanup", HEXAGONAL_AVAILABLE=False, POSTGRESQL_AVAILABLE=False)(app)
    app.favorites_manager.teardown.assert_called_once_with()
