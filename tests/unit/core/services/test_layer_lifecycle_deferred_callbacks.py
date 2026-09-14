# -*- coding: utf-8 -*-
"""
2026-09-14: opening another project while the panel was open left it empty.

handle_project_initialization() scheduled the add_layers registration through
``weakref.ref(manage_task_callback)``; the callback is the lambda FilterMateApp
passes as an argument, so the reference was dead as soon as the method
returned and the QTimer fired into nothing, while ``_loading_new_project`` had
already been raised. Reproduced in QGIS 4.2 (31.qgz → bdd.qgz: combo box empty,
Filter button disabled, flag stuck).
"""
import gc
import importlib.util
import os
import sys
import types
import weakref
from unittest.mock import MagicMock

import pytest


def _load_layer_lifecycle_service():
    """Load the real module under an ephemeral package chain so its
    ``from ...infrastructure`` imports resolve (same sandbox pattern as
    test_filter_config_builder.py; ``filter_mate.*`` stays untouched)."""
    plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))))
    root = "_lls_sandbox"
    chain = {
        root: plugin_root,
        f"{root}.core": os.path.join(plugin_root, "core"),
        f"{root}.core.services": os.path.join(plugin_root, "core", "services"),
        f"{root}.infrastructure": os.path.join(plugin_root, "infrastructure"),
        f"{root}.infrastructure.database": os.path.join(plugin_root, "infrastructure", "database"),
    }
    for name, dir_path in chain.items():
        pkg = types.ModuleType(name)
        pkg.__path__ = [dir_path]
        sys.modules[name] = pkg
        if "." in name:
            parent, _, leaf = name.rpartition(".")
            setattr(sys.modules[parent], leaf, pkg)
    qualname = f"{root}.core.services.layer_lifecycle_service"
    spec = importlib.util.spec_from_file_location(
        qualname, os.path.join(plugin_root, "core", "services", "layer_lifecycle_service.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = module
    spec.loader.exec_module(module)
    for name in chain:
        sys.modules.pop(name, None)
    return module


lls = _load_layer_lifecycle_service()


class _FakeTimer:
    """Captures QTimer.singleShot callbacks so the test fires them itself."""
    scheduled = []

    @classmethod
    def singleShot(cls, delay, callback):
        cls.scheduled.append((delay, callback))


def _service():
    service = lls.LayerLifecycleService.__new__(lls.LayerLifecycleService)
    service.filter_usable_layers = lambda layers, postgresql_available=True: list(layers)
    return service


def _app_and_callback():
    """An app whose add_layers entry point is reached through an argument lambda,
    exactly like FilterMateApp._handle_project_initialization does."""
    app = MagicMock()
    app.manage_task = MagicMock()
    return app, (lambda layers: app.manage_task('add_layers', layers))


@pytest.mark.unit
class TestHoldCallback:

    def test_lambda_survives_the_callers_frame(self):
        app = MagicMock()

        def schedule():
            return lls._hold_callback(lambda layers: app.manage_task('add_layers', layers))

        resolve = schedule()
        gc.collect()
        callback = resolve()
        assert callback is not None
        callback(['l1'])
        app.manage_task.assert_called_once_with('add_layers', ['l1'])

    def test_plain_weakref_to_the_same_lambda_is_already_dead(self):
        # The pre-2026-09-14 behaviour, kept as documentation of the failure.
        app = MagicMock()

        def schedule():
            return weakref.ref(lambda layers: app.manage_task('add_layers', layers))

        assert schedule()() is None

    def test_bound_method_dies_with_its_owner(self):
        class Owner:
            def manage_task(self, *args):
                return None

        owner = Owner()
        resolve = lls._hold_callback(owner.manage_task)
        assert resolve() is not None
        del owner
        gc.collect()
        assert resolve() is None


@pytest.mark.unit
class TestProjectInitializationRegistersTheNewLayers:

    @pytest.fixture(autouse=True)
    def _fake_timer(self, monkeypatch):
        _FakeTimer.scheduled = []
        monkeypatch.setattr(lls, "QTimer", _FakeTimer)
        qgs_project = MagicMock()
        qgs_project.instance.return_value = MagicMock(name="QgsProject.instance()")
        monkeypatch.setattr(lls, "QgsProject", qgs_project)
        monkeypatch.setattr(lls, "perf_mark_start", lambda name: None)

    def _run(self, service, app, callback, layers):
        project = MagicMock()
        project.mapLayers.return_value = {f"id{i}": layer for i, layer in enumerate(layers)}
        flags = {"loading": None, "initializing": []}
        dockwidget = MagicMock()
        dockwidget.widgets_initialized = True
        service.handle_project_initialization(
            task_name='project_read',
            is_initializing=False,
            is_loading=False,
            dockwidget=dockwidget,
            check_reset_flags_callback=lambda: None,
            set_initializing_flag_callback=lambda v: flags["initializing"].append(v),
            set_loading_flag_callback=lambda v: flags.__setitem__("loading", v),
            cancel_tasks_callback=lambda: None,
            init_env_vars_callback=lambda: None,
            get_project_callback=lambda: project,
            init_db_callback=lambda: None,
            manage_task_callback=callback,
            temp_schema='filtermate_temp',
            stability_constants={'PROJECT_LOAD_DELAY_MS': 2500},
        )
        return flags

    def test_add_layers_fires_after_the_project_load_delay(self):
        service = _service()
        app, callback = _app_and_callback()
        layers = [MagicMock(name="l1"), MagicMock(name="l2")]

        flags = self._run(service, app, callback, layers)
        del callback  # the app's frame is gone; only the scheduled closure remains
        gc.collect()

        assert flags["loading"] is True, "loading flag raised before the deferred registration"
        assert [d for d, _ in _FakeTimer.scheduled] == [2500]
        _FakeTimer.scheduled[0][1]()
        app.manage_task.assert_called_once()
        assert app.manage_task.call_args.args[0] == 'add_layers'
        assert list(app.manage_task.call_args.args[1]) == layers

    def test_no_usable_layer_lowers_the_loading_flag_immediately(self):
        service = _service()
        app, callback = _app_and_callback()

        flags = self._run(service, app, callback, [])

        assert flags["loading"] is False
        assert _FakeTimer.scheduled == []
        app.manage_task.assert_not_called()
