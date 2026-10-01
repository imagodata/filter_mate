# -*- coding: utf-8 -*-
"""
Point cloud support (WP-E): the app and the layer combo must go through the
capability helpers (get_filterable_layer_types / get_current_layer_combo_filters)
instead of hard-coding QgsVectorLayer, and safe_set_subset_string must not call
featureCount() directly. Methods are extracted from filter_mate_app.py with ast,
like the other app tests, so the plugin module itself is never imported.
"""
import ast
import types
import weakref
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APP = _ROOT / "filter_mate_app.py"
_CONFIG_MANAGER = _ROOT / "ui" / "managers" / "configuration_manager.py"
_SQL_UTILS = _ROOT / "infrastructure" / "database" / "sql_utils.py"

_CAPABILITY_MODULE = "adapters.qgis.point_cloud_capability"


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _first_class(tree):
    return next(node for node in tree.body if isinstance(node, ast.ClassDef))


def _class_named(tree, name):
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)


def _method(cls, name):
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _function(tree, name):
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _called_names(node):
    return {n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def _isinstance_type_args(node):
    return [
        ast.unparse(n.args[1]) for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "isinstance" and len(n.args) == 2
    ]


def _attribute_names(node):
    return {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def _extract(names, namespace):
    cls = _first_class(_parse(_APP))
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(_APP), "exec"), namespace)
    return namespace


class _Vector:
    def __init__(self, layer_id="v1", valid=True):
        self._id = layer_id
        self._valid = valid

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return self._valid


class _PointCloud:
    def __init__(self, layer_id="pc1", valid=True):
        self._id = layer_id
        self._valid = valid

    def id(self):
        return self._id

    def name(self):
        return self._id

    def isValid(self):
        return self._valid


@pytest.mark.unit
class TestAppStaticGuards:

    def test_capability_import_is_guarded_with_fallbacks(self):
        tree = _parse(_APP)
        guarded = [
            node for node in tree.body if isinstance(node, ast.Try)
            and any(isinstance(s, ast.ImportFrom) and s.module == _CAPABILITY_MODULE and s.level == 1 for s in node.body)
        ]
        assert len(guarded) == 1
        imported = {alias.name for s in guarded[0].body if isinstance(s, ast.ImportFrom) for alias in s.names}
        assert {"get_filterable_layer_types", "get_current_layer_combo_filters"} <= imported
        handler = guarded[0].handlers[0]
        assert ast.unparse(handler.type) == "ImportError"
        fallbacks = {s.name for s in handler.body if isinstance(s, ast.FunctionDef)}
        assert fallbacks == {"get_filterable_layer_types", "get_current_layer_combo_filters"}

    def test_filter_usable_layers_fallback_uses_filterable_types(self):
        method = _method(_first_class(_parse(_APP)), "_filter_usable_layers")
        assert "get_filterable_layer_types" in _called_names(method)
        assert "QgsVectorLayer" not in _isinstance_type_args(method)

    def test_refresh_ui_with_layers_uses_capability_helpers(self):
        method = _method(_first_class(_parse(_APP)), "_refresh_ui_with_layers")
        called = _called_names(method)
        assert "get_current_layer_combo_filters" in called
        assert "get_filterable_layer_types" in called
        assert "QgsVectorLayer" not in _isinstance_type_args(method)
        assert "QgsMapLayerProxyModel.Filter.HasGeometry" in ast.unparse(method)

    def test_first_class_is_still_the_app(self):
        assert _first_class(_parse(_APP)).name == "FilterMateApp"


@pytest.mark.unit
class TestConfigurationManagerStaticGuards:

    def test_filtering_combo_uses_capability_with_fallbacks(self):
        method = _method(_class_named(_parse(_CONFIG_MANAGER), "ConfigurationManager"), "setup_filtering_tab_widgets")
        imports = [
            node for node in ast.walk(method)
            if isinstance(node, ast.ImportFrom) and node.module == _CAPABILITY_MODULE and node.level == 3
        ]
        assert len(imports) == 1
        assert {alias.name for alias in imports[0].names} == {"get_current_layer_combo_filters"}
        guarded = [
            node for node in ast.walk(method) if isinstance(node, ast.Try)
            and any(isinstance(s, ast.ImportFrom) and s.module == _CAPABILITY_MODULE for s in node.body)
        ]
        assert len(guarded) == 1
        assert "get_current_layer_combo_filters" in _called_names(method)
        source = ast.unparse(method)
        assert "QgsMapLayerProxyModel.Filter.HasGeometry" in source
        assert "QgsMapLayerProxyModel.Filter.VectorLayer" in source


@pytest.mark.unit
class TestSqlUtilsStaticGuards:

    def test_safe_set_subset_string_never_calls_feature_count_directly(self):
        tree = _parse(_SQL_UTILS)
        function = _function(tree, "safe_set_subset_string")
        assert "featureCount" not in _attribute_names(function)
        assert "pointCount" not in _attribute_names(function)
        label_calls = [
            n for n in ast.walk(function)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_layer_count_label"
        ]
        assert len(label_calls) == 2

    def test_layer_count_label_is_defensive(self):
        function = _function(_parse(_SQL_UTILS), "_layer_count_label")
        assert any(isinstance(n, ast.Try) for n in ast.walk(function))
        assert {"featureCount", "pointCount"} <= _attribute_names(function)


def _filter_usable_layers(filterable_types):
    namespace = _extract(
        ["_filter_usable_layers"],
        {"get_filterable_layer_types": lambda: filterable_types,
         "is_layer_source_available": lambda layer: True,
         "POSTGRESQL_AVAILABLE": False, "logger": MagicMock()},
    )
    app = types.SimpleNamespace(_get_layer_lifecycle_service=lambda: None)
    app._filter_usable_layers = types.MethodType(namespace["_filter_usable_layers"], app)
    return app


@pytest.mark.unit
class TestFilterUsableLayersFallback:

    def test_point_cloud_is_kept_when_the_capability_lists_it(self):
        app = _filter_usable_layers((_Vector, _PointCloud))
        vector, cloud = _Vector(), _PointCloud()

        kept = app._filter_usable_layers([vector, cloud, _Vector(valid=False), object()])

        assert kept == [vector, cloud]

    def test_point_cloud_is_dropped_when_the_capability_is_vector_only(self):
        app = _filter_usable_layers((_Vector,))
        vector = _Vector()

        kept = app._filter_usable_layers([vector, _PointCloud()])

        assert kept == [vector]

    def test_service_path_is_untouched(self):
        app = _filter_usable_layers((_Vector,))
        service = MagicMock()
        app._get_layer_lifecycle_service = lambda: service

        result = app._filter_usable_layers(["anything"])

        service.filter_usable_layers.assert_called_once_with(["anything"], False)
        assert result is service.filter_usable_layers.return_value


def _refresh_app(combo_flags, filterable_types, active):
    proxy_model = MagicMock()
    namespace = _extract(
        ["_refresh_ui_with_layers"],
        {"QTimer": MagicMock(), "logger": MagicMock(), "weakref": weakref,
         "perf_mark_end": MagicMock(), "should_show_message": lambda category: False,
         "QCoreApplication": MagicMock(), "QgsMapLayerProxyModel": proxy_model,
         "get_current_layer_combo_filters": lambda: combo_flags,
         "get_filterable_layer_types": lambda: filterable_types},
    )
    app = types.SimpleNamespace(
        dockwidget=MagicMock(), PROJECT=MagicMock(), iface=MagicMock(),
        PROJECT_LAYERS={"pc1": {}, "v1": {}},
        _set_loading_flag=MagicMock(), _validate_postgres_layers_on_project_load=MagicMock(),
    )
    app.dockwidget.widgets_initialized = True
    app.iface.activeLayer.return_value = active
    app._refresh_ui_with_layers = types.MethodType(namespace["_refresh_ui_with_layers"], app)
    return app, proxy_model


@pytest.mark.unit
class TestRefreshUiWithLayers:

    def test_combo_gets_the_capability_flags_and_active_point_cloud_is_selected(self):
        cloud = _PointCloud()
        app, _ = _refresh_app(540, (_Vector, _PointCloud), cloud)

        app._refresh_ui_with_layers()

        app.dockwidget.comboBox_filtering_current_layer.setFilters.assert_called_once_with(540)
        app.dockwidget.current_layer_changed.assert_called_once_with(cloud)

    def test_combo_falls_back_to_has_geometry_when_the_capability_returns_none(self):
        vector = _Vector()
        app, proxy_model = _refresh_app(None, (_Vector,), vector)

        app._refresh_ui_with_layers()

        app.dockwidget.comboBox_filtering_current_layer.setFilters.assert_called_once_with(proxy_model.Filter.HasGeometry)
        app.dockwidget.current_layer_changed.assert_called_once_with(vector)

    def test_active_point_cloud_is_ignored_when_the_capability_is_vector_only(self):
        cloud = _PointCloud()
        app, _ = _refresh_app(None, (_Vector,), cloud)

        app._refresh_ui_with_layers()

        app.PROJECT.mapLayer.assert_called_once_with("pc1")
        app.dockwidget.current_layer_changed.assert_called_once_with(app.PROJECT.mapLayer.return_value)

    def test_combo_failure_is_non_fatal(self):
        vector = _Vector()
        app, _ = _refresh_app(540, (_Vector,), vector)
        app.dockwidget.comboBox_filtering_current_layer.setFilters.side_effect = TypeError("bad flags")

        app._refresh_ui_with_layers()

        app.dockwidget.current_layer_changed.assert_called_once_with(vector)
