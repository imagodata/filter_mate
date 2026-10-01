# -*- coding: utf-8 -*-
"""
2026-09-18: point cloud layers (QgsPointCloudLayer) enter PROJECT_LAYERS through
a dedicated registration path that never touches the vector-only API
(fields(), primaryKeyAttributes(), sourceCrs(), featureCount(), ...).

Two kinds of checks:

* static (ast) — the method bodies of ``layer_management_task.py`` keep the
  dispatch order and never reference a vector-only name on the point cloud path;
* behavioural — the real ``LayersManagementEngineTask`` is loaded from its file
  under a private package chain (``_pcreg_sandbox``) whose infrastructure,
  capability and domain modules are stubs, and instantiated without ``__init__``
  (``QgsTask`` is swapped for a plain class during the load so ``__new__`` works).
  The capability (WP-C) and domain (WP-A) modules are test doubles written
  against the contract, so this file does not depend on their real code.
"""
import ast
import importlib.util
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_TASK = _PROJECT_ROOT / "core" / "tasks" / "layer_management_task.py"
_ROOT = "_pcreg_sandbox"

VECTOR_ONLY_API = frozenset({
    "fields", "geometryType", "wkbType", "featureCount", "sourceCrs",
    "primaryKeyAttributes", "getFeatures", "addExpressionField", "uniqueValues",
    "selectedFeatures", "selectByIds", "geometryColumn",
})
VECTOR_ONLY_HELPERS = frozenset({
    "search_primary_key_from_layer", "_build_new_layer_properties",
    "_migrate_legacy_geometry_field", "_create_spatial_index", "_detect_layer_metadata",
})

POINT_CLOUD_PROVIDER_TYPE = "pointcloud"
POINT_CLOUD_GEOMETRY_TYPE = "GeometryType.PointCloud"


# ---------------------------------------------------------------------------
# Test doubles for the WP-A domain contract
# ---------------------------------------------------------------------------

def _build_point_cloud_layer_properties(layer_id, layer_name, crs_authid, qgis_provider, default_is_linking=False):
    return {
        "infos": {
            "layer_geometry_type": POINT_CLOUD_GEOMETRY_TYPE,
            "layer_name": layer_name,
            "layer_table_name": layer_name,
            "layer_id": layer_id,
            "layer_schema": "",
            "is_already_subset": False,
            "layer_provider_type": POINT_CLOUD_PROVIDER_TYPE,
            "layer_crs_authid": crs_authid,
            "primary_key_name": "",
            "primary_key_idx": -1,
            "primary_key_type": "",
            "layer_geometry_field": "",
            "primary_key_is_numeric": False,
            "is_current_layer": False,
            "postgresql_connection_available": False,
            "psycopg2_connection_available": False,
            "point_cloud_provider": qgis_provider,
        },
        "exploring": {
            "is_changing_all_layer_properties": True,
            "is_tracking": False,
            "is_selecting": False,
            "is_linking": default_is_linking,
            "current_exploring_groupbox": "single_selection",
            "single_selection_expression": "",
            "multiple_selection_expression": "",
            "custom_selection_expression": "",
        },
        "filtering": {
            "has_layers_to_filter": False,
            "layers_to_filter": [],
            "has_combine_operator": False,
            "source_layer_combine_operator": "AND",
            "other_layers_combine_operator": "AND",
            "has_geometric_predicates": False,
            "geometric_predicates": [],
            "use_centroids_source_layer": False,
            "use_centroids_distant_layers": False,
            "has_buffer_value": False,
            "buffer_value": 0.0,
            "buffer_value_property": False,
            "buffer_value_expression": "",
            "has_buffer_type": False,
            "buffer_type": "Round",
            "buffer_segments": 5,
            "has_simplify_tolerance": False,
            "simplify_tolerance": 0.0,
        },
    }


def _ensure_point_cloud_layer_properties(layer_props, template):
    added = False
    for section, values in template.items():
        target = layer_props.setdefault(section, {})
        for key, value in values.items():
            if key not in target:
                target[key] = value
                added = True
    return added


# ---------------------------------------------------------------------------
# Fake layers
# ---------------------------------------------------------------------------

class _FakePointCloudLayer:
    """A QgsPointCloudLayer look-alike: QgsMapLayer API only, no vector methods."""

    def __init__(self, layer_id="pc-1", name="nuage", provider="copc", crs_authid="EPSG:2154"):
        self._id = layer_id
        self._name = name
        self._provider = provider
        self._crs_authid = crs_authid

    def id(self):
        return self._id

    def name(self):
        return self._name

    def providerType(self):
        return self._provider

    def crs(self):
        crs = MagicMock()
        crs.authid.return_value = self._crs_authid
        return crs

    def isValid(self):
        return True

    def isSpatial(self):
        return True


class _StrictPointCloudLayer(_FakePointCloudLayer):
    """Fails loudly (not with a catchable AttributeError) on any vector-only call."""

    def __getattr__(self, name):
        if name in VECTOR_ONLY_API:
            raise AssertionError(f"vector-only API '{name}' called on a point cloud layer")
        raise AttributeError(name)


def _vector_layer(layer_id="vec-1", name="communes"):
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = name
    layer.isSpatial.return_value = True
    layer.providerType.return_value = "ogr"
    return layer


# ---------------------------------------------------------------------------
# Loading the real task module under a private, fully stubbed package chain
# ---------------------------------------------------------------------------

def _module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__path__ = []
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _load_task_module():
    stubs = {
        _ROOT: _module(_ROOT),
        f"{_ROOT}.core": _module(f"{_ROOT}.core"),
        f"{_ROOT}.core.tasks": _module(f"{_ROOT}.core.tasks"),
        f"{_ROOT}.core.domain": _module(f"{_ROOT}.core.domain"),
        f"{_ROOT}.core.domain.point_cloud_support": _module(
            f"{_ROOT}.core.domain.point_cloud_support",
            build_point_cloud_layer_properties=_build_point_cloud_layer_properties,
            ensure_point_cloud_layer_properties=_ensure_point_cloud_layer_properties,
        ),
        f"{_ROOT}.adapters": _module(f"{_ROOT}.adapters"),
        f"{_ROOT}.adapters.qgis": _module(f"{_ROOT}.adapters.qgis"),
        f"{_ROOT}.adapters.qgis.point_cloud_capability": _module(
            f"{_ROOT}.adapters.qgis.point_cloud_capability",
            get_filterable_layer_types=lambda: (MagicMock,),
            is_point_cloud_layer=lambda layer: False,
        ),
        f"{_ROOT}.config": _module(f"{_ROOT}.config"),
        f"{_ROOT}.config.config": _module(
            f"{_ROOT}.config.config",
            ENV_VARS={"PATH_ABSOLUTE_PROJECT": "/tmp/filtermate_pcreg", "PROJECT": None},  # nosec B108
        ),
        f"{_ROOT}.infrastructure": _module(f"{_ROOT}.infrastructure"),
        f"{_ROOT}.infrastructure.logging": _module(
            f"{_ROOT}.infrastructure.logging",
            setup_logger=lambda *args, **kwargs: logging.getLogger("pcreg_sandbox"),
            safe_log=MagicMock(),
        ),
        f"{_ROOT}.infrastructure.utils": _module(
            f"{_ROOT}.infrastructure.utils",
            get_datasource_connexion_from_layer=MagicMock(),
            detect_layer_provider_type=MagicMock(return_value="ogr"),
            get_best_display_field=MagicMock(return_value=""),
            get_source_table_name=MagicMock(return_value=""),
            geometry_type_to_string=MagicMock(return_value="GeometryType.Polygon"),
            safe_emit=MagicMock(),
            safe_set_layer_variables=MagicMock(),
            safe_set_layer_variables_batch=MagicMock(),
            is_qgis_alive=MagicMock(return_value=True),
        ),
        f"{_ROOT}.infrastructure.utils.type_utils": _module(
            f"{_ROOT}.infrastructure.utils.type_utils",
            can_cast=MagicMock(return_value=True),
            return_typed_value=lambda value, action=None: (value, type(value)),
        ),
        f"{_ROOT}.infrastructure.database": _module(f"{_ROOT}.infrastructure.database"),
        f"{_ROOT}.infrastructure.database.sql_utils": _module(
            f"{_ROOT}.infrastructure.database.sql_utils",
            sanitize_sql_identifier=lambda value: value,
        ),
        f"{_ROOT}.infrastructure.database.spatialite_support": _module(
            f"{_ROOT}.infrastructure.database.spatialite_support",
            safe_spatialite_connect=MagicMock(),
            sqlite_execute_with_retry=lambda fn, operation_name="": fn(),
            ensure_db_directory_exists=MagicMock(),
            MESSAGE_TASKS_CATEGORIES={},
        ),
        f"{_ROOT}.infrastructure.database.postgresql_support": _module(
            f"{_ROOT}.infrastructure.database.postgresql_support",
            psycopg2=None,
            PSYCOPG2_AVAILABLE=False,
            POSTGRESQL_AVAILABLE=False,
        ),
    }
    for name, mod in stubs.items():
        sys.modules[name] = mod

    class _PlainQgsTask:
        Flag = types.SimpleNamespace(CanCancel=1)

    qgis_core = sys.modules["qgis.core"]
    original_qgs_task = getattr(qgis_core, "QgsTask", None)
    qgis_core.QgsTask = _PlainQgsTask
    qualname = f"{_ROOT}.core.tasks.layer_management_task"
    try:
        spec = importlib.util.spec_from_file_location(qualname, str(_TASK))
        module = importlib.util.module_from_spec(spec)
        module.__package__ = f"{_ROOT}.core.tasks"
        sys.modules[qualname] = module
        spec.loader.exec_module(module)
    finally:
        qgis_core.QgsTask = original_qgs_task
        sys.modules.pop(qualname, None)
        for name in stubs:
            sys.modules.pop(name, None)
    return module


task_mod = _load_task_module()


def _task(existing=None, default_is_linking=True):
    cls = task_mod.LayersManagementEngineTask
    task = cls.__new__(cls)
    task.project_layers = {}
    task.CONFIG_DATA = {"CURRENT_PROJECT": {"OPTIONS": {"LAYERS": {"LAYER_PROPERTIES_COUNT": 0}}}}
    task._deferred_layer_variables = []
    task._deferred_warnings = []
    task.reset_all = False
    task.layers = []
    task.task_action = "add_layers"
    task.setProgress = lambda value: None
    task.isCanceled = lambda: False
    task._load_existing_layer_properties = MagicMock(return_value=existing if existing is not None else {})
    task.insert_properties_to_spatialite = MagicMock()
    task._get_default_is_linking = MagicMock(return_value=default_is_linking)
    task.return_typped_value = lambda value, action=None: (value, type(value))
    task.save_variables_from_layer = MagicMock()
    task.save_style_from_layer_id = MagicMock()
    for helper in VECTOR_ONLY_HELPERS:
        setattr(task, helper, MagicMock(side_effect=AssertionError(f"{helper} reached for a point cloud layer")))
    return task


@pytest.fixture
def point_cloud_enabled(monkeypatch):
    monkeypatch.setattr(task_mod, "get_filterable_layer_types", lambda: (task_mod.QgsVectorLayer, _FakePointCloudLayer))
    monkeypatch.setattr(task_mod, "is_point_cloud_layer", lambda layer: isinstance(layer, _FakePointCloudLayer))


@pytest.fixture
def point_cloud_disabled(monkeypatch):
    monkeypatch.setattr(task_mod, "get_filterable_layer_types", lambda: (task_mod.QgsVectorLayer,))
    monkeypatch.setattr(task_mod, "is_point_cloud_layer", lambda layer: False)


# ---------------------------------------------------------------------------
# Behavioural tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAddPointCloudLayer:

    def test_new_point_cloud_layer_is_registered_from_the_template(self, point_cloud_enabled):
        task = _task(default_is_linking=False)
        layer = _FakePointCloudLayer()

        assert task.add_project_layer(layer) is True

        props = task.project_layers["pc-1"]
        infos = props["infos"]
        assert infos["layer_provider_type"] == POINT_CLOUD_PROVIDER_TYPE
        assert infos["layer_geometry_type"] == POINT_CLOUD_GEOMETRY_TYPE
        assert infos["layer_id"] == "pc-1"
        assert infos["layer_name"] == "nuage"
        assert infos["layer_crs_authid"] == "EPSG:2154"
        assert infos["point_cloud_provider"] == "copc"
        assert "spatial_index_pending" not in infos
        assert props["exploring"]["is_linking"] is False
        task.insert_properties_to_spatialite.assert_called_once_with("pc-1", props)
        assert task.CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]["LAYERS"]["LAYER_PROPERTIES_COUNT"] == (
            len(props["infos"]) + len(props["exploring"]) + len(props["filtering"]))
        assert ("pc-1", "filterMate_infos_layer_provider_type", POINT_CLOUD_PROVIDER_TYPE) in task._deferred_layer_variables
        assert ("pc-1", "filterMate_exploring_is_linking", False) in task._deferred_layer_variables
        assert task._deferred_warnings == []

    def test_known_point_cloud_layer_is_completed_without_insert(self, point_cloud_enabled):
        existing = {
            "infos": {"layer_provider_type": POINT_CLOUD_PROVIDER_TYPE, "layer_name": "ancien nom"},
            "exploring": {"is_linking": True},
            "filtering": {},
        }
        task = _task(existing=existing)
        task.CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]["LAYERS"]["LAYER_PROPERTIES_COUNT"] = 44

        assert task.add_project_layer(_FakePointCloudLayer()) is True

        props = task.project_layers["pc-1"]
        assert props["infos"] is existing["infos"]
        assert props["infos"]["layer_name"] == "ancien nom"
        assert props["infos"]["layer_id"] == "pc-1"
        assert props["infos"]["layer_geometry_type"] == POINT_CLOUD_GEOMETRY_TYPE
        assert props["exploring"]["is_linking"] is True
        assert props["filtering"]["buffer_type"] == "Round"
        task.insert_properties_to_spatialite.assert_not_called()
        assert task._deferred_layer_variables == []
        assert task.CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]["LAYERS"]["LAYER_PROPERTIES_COUNT"] == 44

    def test_point_cloud_path_never_calls_the_vector_api(self, point_cloud_enabled):
        task = _task()
        assert task.add_project_layer(_StrictPointCloudLayer()) is True
        for helper in VECTOR_ONLY_HELPERS:
            getattr(task, helper).assert_not_called()

    def test_crs_failure_is_tolerated(self, point_cloud_enabled):
        task = _task()
        layer = _FakePointCloudLayer()
        layer.crs = MagicMock(side_effect=RuntimeError("wrapped C/C++ object deleted"))

        assert task.add_project_layer(layer) is True
        assert task.project_layers["pc-1"]["infos"]["layer_crs_authid"] == ""

    def test_missing_domain_template_skips_the_layer(self, point_cloud_enabled, monkeypatch):
        monkeypatch.setattr(task_mod, "build_point_cloud_layer_properties", lambda *args, **kwargs: {})
        task = _task()

        assert task.add_project_layer(_FakePointCloudLayer()) is False
        assert task.project_layers == {}
        task.insert_properties_to_spatialite.assert_not_called()


@pytest.mark.unit
class TestFeatureFlagOff:

    def test_point_cloud_is_skipped_like_a_non_spatial_layer(self, point_cloud_disabled):
        task = _task()
        assert task.add_project_layer(_FakePointCloudLayer()) is False
        assert task.project_layers == {}
        task.insert_properties_to_spatialite.assert_not_called()
        task._load_existing_layer_properties.assert_not_called()

    def test_vector_layers_still_take_the_vector_path(self, point_cloud_disabled):
        task = _task()
        task.search_primary_key_from_layer = MagicMock(return_value=False)
        layer = _vector_layer()
        assert isinstance(layer, task_mod.QgsVectorLayer)

        assert task.add_project_layer(layer) is False
        task._load_existing_layer_properties.assert_called_once_with(layer)
        task.search_primary_key_from_layer.assert_called_once_with(layer)


@pytest.mark.unit
class TestManageProjectLayers:

    def _recording_add(self, task, geometry_types):
        reached = []

        def fake_add(layer):
            reached.append(layer)
            task.project_layers[layer.id()] = {
                "infos": {"layer_geometry_type": geometry_types[layer.id()], "layer_name": layer.name()},
                "exploring": {},
                "filtering": {},
            }
            return True

        task.add_project_layer = fake_add
        return reached

    def test_both_kinds_are_registered_and_sorted(self, point_cloud_enabled):
        task = _task()
        pc = _FakePointCloudLayer(layer_id="pc-1", name="nuage")
        vec = _vector_layer(layer_id="vec-1", name="communes")
        task.layers = [vec, pc, "not-a-layer-object"]
        reached = self._recording_add(task, {"pc-1": POINT_CLOUD_GEOMETRY_TYPE, "vec-1": "GeometryType.Polygon"})

        assert task.manage_project_layers() is True
        assert reached == [vec, pc]
        assert list(task.project_layers) == ["pc-1", "vec-1"]

    def test_point_clouds_are_ignored_when_the_flag_is_off(self, point_cloud_disabled):
        task = _task()
        pc = _FakePointCloudLayer()
        vec = _vector_layer()
        task.layers = [pc, vec]
        reached = self._recording_add(task, {"vec-1": "GeometryType.Polygon"})

        assert task.manage_project_layers() is True
        assert reached == [vec]
        assert list(task.project_layers) == ["vec-1"]

    def test_already_registered_point_cloud_is_not_added_twice(self, point_cloud_enabled):
        task = _task()
        pc = _FakePointCloudLayer()
        task.project_layers["pc-1"] = {"infos": {"layer_geometry_type": POINT_CLOUD_GEOMETRY_TYPE, "layer_name": "nuage"}}
        task.layers = [pc]
        reached = self._recording_add(task, {})

        assert task.manage_project_layers() is True
        assert reached == []

    def test_remove_layers_reaches_point_clouds(self, point_cloud_enabled):
        task = _task()
        task.task_action = "remove_layers"
        pc = _FakePointCloudLayer()
        task.project_layers["pc-1"] = {"infos": {"layer_geometry_type": POINT_CLOUD_GEOMETRY_TYPE, "layer_name": "nuage"}}
        task.layers = [pc]

        assert task.manage_project_layers() is True
        assert task.project_layers == {}
        task.save_variables_from_layer.assert_called_once_with("pc-1")
        task.save_style_from_layer_id.assert_called_once_with("pc-1")


@pytest.mark.unit
class TestRemoveProjectLayer:

    def test_point_cloud_object_is_accepted(self, point_cloud_enabled):
        task = _task()
        task.project_layers["pc-1"] = {"infos": {}}
        assert task.remove_project_layer(_FakePointCloudLayer()) is True
        assert "pc-1" not in task.project_layers

    def test_layer_id_string_still_works(self, point_cloud_enabled):
        task = _task()
        task.project_layers["pc-1"] = {"infos": {}}
        assert task.remove_project_layer("pc-1") is True
        assert task.project_layers == {}
        assert task.remove_project_layer("pc-1") is True

    def test_unknown_objects_are_rejected(self, point_cloud_enabled):
        task = _task()
        assert task.remove_project_layer(object()) is False

    def test_point_cloud_object_is_rejected_when_the_flag_is_off(self, point_cloud_disabled):
        task = _task()
        task.project_layers["pc-1"] = {"infos": {}}
        assert task.remove_project_layer(_FakePointCloudLayer()) is False
        assert "pc-1" in task.project_layers


# ---------------------------------------------------------------------------
# Static (ast) guards
# ---------------------------------------------------------------------------

def _tree():
    return ast.parse(_TASK.read_text(encoding="utf-8"))


def _method(name):
    for cls in (n for n in _tree().body if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
    raise AssertionError(f"{name} not found in {_TASK.name}")


def _calls(node, func_name):
    return [
        n for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func_name
    ]


def _isinstance_second_args(node):
    return [call.args[1] for call in _calls(node, "isinstance") if len(call.args) == 2]


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


@pytest.mark.unit
class TestRegistrationGuardsAst:

    def test_add_project_layer_dispatches_point_clouds_before_any_isinstance(self):
        method = _method("add_project_layer")
        dispatch = _calls(method, "is_point_cloud_layer")
        assert len(dispatch) == 1
        checks = _calls(method, "isinstance")
        assert checks, "the vector guard must still exist"
        assert dispatch[0].lineno < min(call.lineno for call in checks)

        first = next(stmt for stmt in method.body if not isinstance(stmt, ast.Expr))
        assert isinstance(first, ast.If) and first.test is dispatch[0]
        assert len(first.body) == 1 and isinstance(first.body[0], ast.Return)
        returned = first.body[0].value
        assert isinstance(returned, ast.Call) and isinstance(returned.func, ast.Attribute)
        assert returned.func.attr == "_add_point_cloud_layer"

    def test_manage_project_layers_checks_filterable_types_resolved_once(self):
        method = _method("manage_project_layers")
        second_args = _isinstance_second_args(method)
        assert second_args, "isinstance guards expected"
        assert not any(_is_name(arg, "QgsVectorLayer") for arg in second_args)
        assert sum(1 for arg in second_args if _is_name(arg, "filterable_types")) == 2

        assignments = [
            n for n in ast.walk(method)
            if isinstance(n, ast.Assign) and any(_is_name(t, "filterable_types") for t in n.targets)
        ]
        assert len(assignments) == 1
        value = assignments[0].value
        # Accepts both `get_filterable_layer_types()` and the defensive
        # `get_filterable_layer_types() or (QgsVectorLayer,)` fallback (an
        # empty tuple would make every isinstance() check reject all layers).
        calls_in_value = [n for n in ast.walk(value) if isinstance(n, ast.Call)]
        assert any(_is_name(call.func, "get_filterable_layer_types") for call in calls_in_value)
        loops = [n for n in ast.walk(method) if isinstance(n, (ast.For, ast.While))]
        assert not any(assignments[0] in ast.walk(loop) for loop in loops)

    def test_add_point_cloud_layer_never_references_the_vector_api(self):
        method = _method("_add_point_cloud_layer")
        attributes = {n.attr for n in ast.walk(method) if isinstance(n, ast.Attribute)}
        assert not attributes & VECTOR_ONLY_API
        assert not attributes & VECTOR_ONLY_HELPERS
        constants = {n.value for n in ast.walk(method) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert "spatial_index_pending" not in constants
        for reused in ("_load_existing_layer_properties", "_set_layer_variables",
                       "insert_properties_to_spatialite", "_get_default_is_linking"):
            assert reused in attributes
        names = {n.id for n in ast.walk(method) if isinstance(n, ast.Name)}
        assert {"build_point_cloud_layer_properties", "ensure_point_cloud_layer_properties"} <= names

    def test_remove_project_layer_accepts_every_filterable_type(self):
        method = _method("remove_project_layer")
        second_args = _isinstance_second_args(method)
        assert not any(_is_name(arg, "QgsVectorLayer") for arg in second_args)
        # Accepts both `get_filterable_layer_types()` and the defensive
        # `get_filterable_layer_types() or (QgsVectorLayer,)` fallback.
        assert any(
            isinstance(call, ast.Call) and _is_name(call.func, "get_filterable_layer_types")
            for arg in second_args
            for call in ast.walk(arg) if isinstance(call, ast.Call)
        )

    def test_point_cloud_imports_are_guarded_with_fallbacks(self):
        expected = {"get_filterable_layer_types", "is_point_cloud_layer",
                    "build_point_cloud_layer_properties", "ensure_point_cloud_layer_properties"}
        for node in _tree().body:
            if not isinstance(node, ast.Try):
                continue
            imported = {}
            for stmt in node.body:
                if isinstance(stmt, ast.ImportFrom):
                    imported[(stmt.level, stmt.module)] = {alias.name for alias in stmt.names}
            if (3, "adapters.qgis.point_cloud_capability") not in imported:
                continue
            assert imported[(3, "adapters.qgis.point_cloud_capability")] == {"get_filterable_layer_types", "is_point_cloud_layer"}
            assert imported[(2, "domain.point_cloud_support")] == {"build_point_cloud_layer_properties", "ensure_point_cloud_layer_properties"}
            handler = node.handlers[0]
            assert _is_name(handler.type, "ImportError")
            defined = {stmt.name for stmt in handler.body if isinstance(stmt, ast.FunctionDef)}
            assert defined == expected
            return
        raise AssertionError("guarded point cloud imports not found")
