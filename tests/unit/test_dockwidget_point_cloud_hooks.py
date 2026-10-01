# -*- coding: utf-8 -*-
"""
Point cloud hooks of the dock widget and the controller integration (WP-F).

The point cloud path must never enter the vector chain (typed
``pyqtSignal(QgsVectorLayer, ...)`` signals, ``FilterEngineTask``): the dock
widget delegates a point cloud layer change and a task before any vector
validation, and the integration exposes the two delegations. Checked with ast,
the modules are never imported.
"""
import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_DOCKWIDGET = _ROOT / "filter_mate_dockwidget.py"
_INTEGRATION = _ROOT / "ui" / "controllers" / "integration.py"
_CONTROLLERS_INIT = _ROOT / "ui" / "controllers" / "__init__.py"
_PRO = _ROOT / "i18n" / "FilterMate.pro"


def _method(path, class_name, method_name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        if class_name and cls.name != class_name:
            continue
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == method_name:
                return node
    raise AssertionError(f"{method_name} not found in {path.name}")


def _calls(node, attribute):
    """Call nodes ``<expr>.<attribute>(...)`` inside ``node``."""
    return [sub for sub in ast.walk(node)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == attribute]


def _first_statement_line(func):
    body = func.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]
    return body[0].lineno, body[0]


def _returning_if_with_call(func, attribute):
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        if not _calls(node.test, attribute):
            continue
        assert len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None, \
            f"the {attribute} hook must be a bare 'return'"
        return node
    raise AssertionError(f"no 'if ... {attribute}(...): return' in {func.name}")


@pytest.mark.unit
class TestDockwidgetHooks:

    def test_current_layer_changed_delegates_before_the_vector_update(self):
        func = _method(_DOCKWIDGET, "FilterMateDockWidget", "current_layer_changed")
        hook = _returning_if_with_call(func, "delegate_point_cloud_layer_change")
        call = _calls(hook.test, "delegate_point_cloud_layer_change")[0]
        assert [ast.unparse(arg) for arg in call.args] == ["layer"]

        updating = [node for node in ast.walk(func)
                    if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "self._updating_current_layer"
                    and isinstance(node.value, ast.Constant) and node.value.value is True]
        assert updating, "self._updating_current_layer = True not found"
        id_check = [node for node in ast.walk(func) if isinstance(node, ast.Try) and "layer.id()" in ast.unparse(node)]
        assert id_check, "the deleted-layer check (layer.id()) not found"
        assert id_check[0].lineno < hook.lineno < updating[0].lineno

    def test_launch_task_event_delegates_first(self):
        func = _method(_DOCKWIDGET, "FilterMateDockWidget", "launchTaskEvent")
        hook = _returning_if_with_call(func, "delegate_point_cloud_task")
        call = _calls(hook.test, "delegate_point_cloud_task")[0]
        assert [ast.unparse(arg) for arg in call.args] == ["task_name"]
        first_line, first = _first_statement_line(func)
        assert first is hook, "the point cloud delegation must be the first statement of launchTaskEvent"

    def test_validate_and_prepare_layer_tolerates_a_layer_without_selection_signal(self):
        func = _method(_DOCKWIDGET, "FilterMateDockWidget", "_validate_and_prepare_layer")
        handlers = [node for node in ast.walk(func) if isinstance(node, ast.Try)
                    and _calls(node, "disconnect") and "selectionChanged" in ast.unparse(node)]
        assert handlers, "selectionChanged.disconnect try block not found"
        caught = set()
        for handler in handlers[0].handlers:
            caught.update(name.id for name in ast.walk(handler.type) if isinstance(name, ast.Name))
        assert {"TypeError", "RuntimeError", "AttributeError"} <= caught

    def test_icon_map_knows_the_point_cloud_geometry_type(self):
        func = _method(_DOCKWIDGET, "FilterMateDockWidget", "icon_per_geometry_type")
        icon_map = next(node.value for node in ast.walk(func)
                        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "icon_map")
        keys = {key.value for key in icon_map.keys if isinstance(key, ast.Constant)}
        assert "GeometryType.PointCloud" in keys
        value = icon_map.values[[key.value for key in icon_map.keys].index("GeometryType.PointCloud")]
        assert "iconPointCloud" in ast.unparse(value) and "iconDefault" in ast.unparse(value)


@pytest.mark.unit
class TestControllerIntegration:

    def test_delegations_exist_and_fail_closed(self):
        for name, method in (("delegate_point_cloud_layer_change", "on_current_layer_changed"),
                             ("delegate_point_cloud_task", "handle_task")):
            func = _method(_INTEGRATION, "ControllerIntegration", name)
            assert _calls(func, method), f"{name} must call {method}"
            assert any(isinstance(node, ast.Try) for node in ast.walk(func)), f"{name} must catch exceptions"
            returns = [node.value for node in ast.walk(func) if isinstance(node, ast.Return)]
            assert any(isinstance(value, ast.Constant) and value.value is False for value in returns), f"{name} must return False"

    def test_controller_is_created_registered_validated_and_cleared(self):
        created = _method(_INTEGRATION, "ControllerIntegration", "_create_controllers")
        assert _calls(created, "__call__") == [] and "PointCloudUIController(" in ast.unparse(created)
        registered = ast.unparse(_method(_INTEGRATION, "ControllerIntegration", "_register_controllers"))
        assert "'point_cloud_ui'" in registered and "self._point_cloud_ui_controller" in registered
        validated = ast.unparse(_method(_INTEGRATION, "ControllerIntegration", "validate_controllers"))
        assert "('point_cloud_ui', self._point_cloud_ui_controller)" in validated
        reset_pattern = re.compile(r"self\._point_cloud_ui_controller(?::[^=]+)?\s*=\s*None")
        for method in ("teardown", "_cleanup_on_error", "__init__"):
            assert reset_pattern.search(ast.unparse(_method(_INTEGRATION, "ControllerIntegration", method))), method
        assert "self._point_cloud_ui_controller" in ast.unparse(_method(_INTEGRATION, "ControllerIntegration", "point_cloud_ui_controller"))

    def test_controller_package_exports_the_controller(self):
        tree = ast.parse(_CONTROLLERS_INIT.read_text(encoding="utf-8"))
        imported = {alias.name for node in tree.body if isinstance(node, ast.ImportFrom) for alias in node.names}
        exported = next(
            {element.value for element in node.value.elts}
            for node in tree.body if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "__all__")
        assert "PointCloudUIController" in imported
        assert "PointCloudUIController" in exported


@pytest.mark.unit
def test_translation_project_lists_the_new_sources():
    sources = _PRO.read_text(encoding="utf-8")
    assert "../ui/controllers/point_cloud_ui_controller.py" in sources
    assert "../ui/widgets/point_cloud_filter_widget.py" in sources
    for line in sources.splitlines():
        if line.strip().endswith("searchable_view.py \\") or line.strip().endswith("integration.py \\"):
            continue
    assert (_ROOT / "ui" / "controllers" / "point_cloud_ui_controller.py").exists()
    assert (_ROOT / "ui" / "widgets" / "point_cloud_filter_widget.py").exists()
