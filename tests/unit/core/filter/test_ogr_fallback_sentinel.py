# -*- coding: utf-8 -*-
"""The OGR-fallback sentinel is a hand-over, never an expression (2026-10-16).

SpatialiteExpressionBuilder returns ``__USE_OGR_FALLBACK__`` for a source WKT
too large to inline (the 236 KB Toulouse river network), a
GeometryCollection or a dynamic buffer. The orchestrator passed it to
``apply_filter()``, which logged "SPATIALITE backend FAILED" before the OGR
fallback, and the legacy adapter's new-backend path would have written it
into the layer's subset string.
"""
import importlib.util
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[4]
ROOT = "filter_mate"
SENTINEL = "__USE_OGR_FALLBACK__"


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def _load(name, path, stubs):
    saved = {key: sys.modules.get(key) for key in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class _BackendError(Exception):
    pass


_ports = types.ModuleType(f"{ROOT}.core.ports")
_ports.get_backend_services = MagicMock()
_exceptions = types.ModuleType(f"{ROOT}.core.domain.exceptions")
_exceptions.BackendError = _BackendError
_constants = types.ModuleType(f"{ROOT}.infrastructure.constants")
_constants.PROVIDER_POSTGRES = "postgresql"
_constants.PROVIDER_SPATIALITE = "spatialite"
_constants.PROVIDER_OGR = "ogr"
_constants.PROVIDER_MEMORY = "memory"
_constants.QGIS_PROVIDER_POSTGRES = "postgres"

orchestrator_module = _load(
    f"{ROOT}.core.filter._fm_test_filter_orchestrator",
    PLUGIN_ROOT / "core" / "filter" / "filter_orchestrator.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.filter": _package(f"{ROOT}.core.filter"),
        f"{ROOT}.core.ports": _ports,
        f"{ROOT}.core.domain": _package(f"{ROOT}.core.domain"),
        f"{ROOT}.core.domain.exceptions": _exceptions,
        f"{ROOT}.infrastructure": _package(f"{ROOT}.infrastructure"),
        f"{ROOT}.infrastructure.constants": _constants,
    },
)
legacy_module = _load(
    f"{ROOT}.adapters.backends._fm_test_legacy_adapter",
    PLUGIN_ROOT / "adapters" / "backends" / "legacy_adapter.py",
    {},
)


def test_orchestrator_sentinel_matches_the_spatialite_builder():
    assert orchestrator_module.OGR_FALLBACK_SENTINEL == SENTINEL
    assert legacy_module._OGR_FALLBACK_SENTINEL == SENTINEL
    source = (PLUGIN_ROOT / "adapters" / "backends" / "spatialite" / "expression_builder.py").read_text(encoding="utf-8")
    assert f'USE_OGR_FALLBACK = "{SENTINEL}"' in source


def test_sentinel_goes_straight_to_the_ogr_fallback(monkeypatch, caplog):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {"ST_Crosses": "ST_Crosses"},
    )
    backend = MagicMock()
    backend.get_backend_name.return_value = "Spatialite"
    monkeypatch.setattr(orchestrator, "_select_backend", lambda layer, provider: (backend, "spatialite", "spatialite"))
    monkeypatch.setattr(orchestrator, "_clean_corrupted_subsets", lambda layer: None)
    fallback_calls = []

    def _fallback(**kwargs):
        fallback_calls.append(kwargs)
        return True

    monkeypatch.setattr(orchestrator, "_try_fallback_backend", _fallback)
    layer = MagicMock()
    layer.name.return_value = "troncon_de_route"
    builder = MagicMock()
    builder.build_backend_expression.return_value = SENTINEL

    with caplog.at_level(logging.WARNING):
        result = orchestrator.orchestrate_geometric_filter(
            layer=layer, layer_provider_type="spatialite", layer_props={"layer_name": "troncon_de_route"},
            source_geometries={"spatialite": "MULTILINESTRING((0 0, 1 1))", "ogr": MagicMock()},
            expression_builder=builder,
        )

    assert result is True
    backend.apply_filter.assert_not_called()
    assert len(fallback_calls) == 1 and fallback_calls[0]["requested"] is True
    assert not any("FAILED" in record.getMessage() for record in caplog.records)


def test_requested_fallback_is_logged_as_a_hand_over(monkeypatch, caplog):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={"actual_backends": {}}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {},
    )
    ogr_backend = MagicMock()
    ogr_backend.apply_filter.return_value = True
    monkeypatch.setattr(orchestrator_module.BackendFactory, "get_backend", lambda *args: ogr_backend)
    monkeypatch.setattr(orchestrator, "_determine_subset_strategy", lambda layer: (None, None))
    monkeypatch.setattr(orchestrator, "_collect_backend_warnings", lambda backend: None)
    builder = MagicMock()
    builder.build_backend_expression.return_value = '{"predicates": ["ST_Crosses"]}'
    layer = MagicMock()
    layer.name.return_value = "troncon_de_route"

    with caplog.at_level(logging.INFO):
        assert orchestrator._try_fallback_backend(
            layer=layer, layer_props={}, backend_name="spatialite",
            source_geometries={"ogr": MagicMock()}, expression_builder=builder, requested=True,
        ) is True

    messages = [record.getMessage() for record in caplog.records]
    assert any("hands the layer to the OGR backend" in m for m in messages)
    assert not any("failed" in m.lower() for m in messages)
    ogr_backend.apply_filter.assert_called_once()


def test_legacy_adapter_never_applies_the_sentinel(monkeypatch):
    adapter = legacy_module.LegacySpatialiteAdapter.__new__(legacy_module.LegacySpatialiteAdapter)
    adapter.task_params = {}
    adapter._use_new_backend = True
    adapter._new_backend = MagicMock()
    adapter._legacy_backend = MagicMock()

    def _explode(*args):
        raise AssertionError("the sentinel reached a subset string")

    monkeypatch.setattr(adapter, "_apply_filter_new", _explode)
    assert adapter.apply_filter(MagicMock(), SENTINEL) is False
    adapter._legacy_backend.apply_filter.assert_not_called()


# ---------------------------------------------------------------------------
# 2026-10-17 follow-up
# ---------------------------------------------------------------------------

expression_builder_module = _load(
    f"{ROOT}.core.filter._fm_test_expression_builder",
    PLUGIN_ROOT / "core" / "filter" / "expression_builder.py",
    {
        ROOT: _package(ROOT),
        f"{ROOT}.core": _package(f"{ROOT}.core"),
        f"{ROOT}.core.filter": _package(f"{ROOT}.core.filter"),
    },
)


def test_real_expression_builder_passes_the_sentinel_and_the_relay_is_info(monkeypatch, caplog):
    """The real ExpressionBuilder → orchestrator path: an INFO hand-over, no apply_filter, no WARNING."""
    backend = MagicMock()
    backend.get_backend_name.return_value = "Spatialite"
    backend.build_expression.return_value = SENTINEL
    builder = expression_builder_module.ExpressionBuilder(
        task_parameters={"task": {"features": []}}, source_layer=None,
        current_predicates={"ST_Crosses": "ST_Crosses"},
    )
    monkeypatch.setattr(builder, "_prepare_source_filter", lambda backend_name: None)
    assert builder.build_backend_expression(backend, {"layer_name": "t"}, "MULTILINESTRING((0 0, 1 1))") == SENTINEL

    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={"actual_backends": {}}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {"ST_Crosses": "ST_Crosses"},
    )
    monkeypatch.setattr(orchestrator, "_select_backend", lambda layer, provider: (backend, "spatialite", "spatialite"))
    monkeypatch.setattr(orchestrator, "_clean_corrupted_subsets", lambda layer: None)
    monkeypatch.setattr(orchestrator, "_determine_subset_strategy", lambda layer: (None, None))
    monkeypatch.setattr(orchestrator, "_collect_backend_warnings", lambda backend: None)
    ogr_backend = MagicMock()
    ogr_backend.get_backend_name.return_value = "OGR"
    ogr_backend.build_expression.return_value = '{"predicates": ["ST_Crosses"]}'
    ogr_backend.apply_filter.return_value = True
    monkeypatch.setattr(orchestrator_module.BackendFactory, "get_backend", lambda *args: ogr_backend)
    layer = MagicMock()
    layer.name.return_value = "troncon_de_route"
    with caplog.at_level(logging.INFO):
        assert orchestrator.orchestrate_geometric_filter(
            layer=layer, layer_provider_type="spatialite", layer_props={"layer_name": "troncon_de_route"},
            source_geometries={"spatialite": "MULTILINESTRING((0 0, 1 1))", "ogr": MagicMock()},
            expression_builder=builder,
        ) is True
    backend.apply_filter.assert_not_called()
    ogr_backend.apply_filter.assert_called_once()
    relay = [r for r in caplog.records if "hands the layer to the OGR backend" in r.getMessage()]
    assert relay and all(r.levelno == logging.INFO for r in relay)
    assert not any(r.levelno >= logging.WARNING and "fail" in r.getMessage().lower() for r in caplog.records)


def test_backend_expression_builder_returns_the_sentinel():
    source = (PLUGIN_ROOT / "core" / "services" / "backend_expression_builder.py").read_text(encoding="utf-8")
    start = source.index('if expression == "__USE_OGR_FALLBACK__":')
    block = source[start:source.index("if not expression:", start)]
    assert "return expression" in block and "return None" not in block


def _layer(subset, pk="fid"):
    layer = MagicMock()
    layer.subsetString.return_value = subset
    layer.name.return_value = "t"
    layer.primaryKeyAttributes.return_value = [0]
    layer.fields.return_value.at.return_value.name.return_value = pk
    return layer


@pytest.mark.parametrize("subset, pk, key_list", [
    ('"fid" IN (1, 2, 3)', "fid", True),
    ('fid IN (1, 2)', "fid", True),
    ('"fid" IN (SELECT value FROM json_each(\'[1,2]\'))', "fid", True),
    ('NOT ("fid" IN (SELECT value FROM json_each(\'[1,2]\')))', "fid", True),
    ('"cleabs" IN (\'TRON1\', \'TRON2\')', "cleabs", True),     # PostgreSQL / text primary key
    ('"ogc_fid" IN (4, 5)', "ogc_fid", True),
    ("1 = 0", "fid", True),
    ('"nature" IN (\'Route\', \'Chemin\')', "fid", False),       # a user filter, not a key list
    ('"importance" = 1', "fid", False),
])
def test_key_list_subsets_of_previous_spatial_steps(subset, pk, key_list):
    assert orchestrator_module.FilterOrchestrator._is_key_list_subset(_layer(subset, pk), subset) is key_list


@pytest.mark.parametrize("subset, expected", [
    ('"cleabs" IN (\'TRON1\')', ('"cleabs" IN (\'TRON1\')', None)),      # replaced, not combined
    ('"nature" = \'Route\'', ('"nature" = \'Route\'', "AND")),            # attribute: combined
    ('ST_Intersects("geom", X)', (None, None)),                          # spatial: replaced
])
def test_subset_strategy_treats_every_key_list_as_spatial(monkeypatch, subset, expected):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {},
    )
    monkeypatch.setattr(orchestrator, "_get_combine_operator", lambda: "AND")
    assert orchestrator._determine_subset_strategy(_layer(subset, "cleabs")) == expected


def test_backend_refusal_reaches_the_message_bar():
    task = types.SimpleNamespace(warning_messages=[])
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=task,
        get_predicates_callback=lambda: {},
    )
    backend = types.SimpleNamespace(user_warnings=["t: 6,000 keys... keeps its previous filter."])
    orchestrator._collect_backend_warnings(backend)
    assert task.warning_messages == ["t: 6,000 keys... keeps its previous filter."]
    assert backend.user_warnings == []


# ---------------------------------------------------------------------------
# 2026-10-17: the targets' combine operator
# ---------------------------------------------------------------------------
# _get_combine_operator was a placeholder reading task_parameters
# ['combine_operator'], a key nothing sets: every target was combined with
# AND, whatever the user chose (OR, AND NOT, or combination unchecked =
# replace). It now asks the task (ExpressionFacadeHandler.get_combine_operator:
# normalized, None when the option is off).

def _orchestrator_with_operator(operator):
    task = types.SimpleNamespace(_get_combine_operator=lambda: operator)
    return orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=task,
        get_predicates_callback=lambda: {},
    )


@pytest.mark.parametrize("operator", ["AND", "OR", "AND NOT", None])
def test_target_operator_is_the_tasks(operator):
    orchestrator = _orchestrator_with_operator(operator)
    assert orchestrator._get_combine_operator() == operator
    assert orchestrator._determine_subset_strategy(_layer('"nature" = \'Route\'')) == ('"nature" = \'Route\'', operator)
    assert orchestrator.task_parameters['_current_combine_operator'] == operator


@pytest.mark.parametrize("subset", ['"fid" IN (1, 2)', 'ST_Intersects("geom", X)'])
def test_previous_spatial_filter_is_still_replaced_whatever_the_operator(subset):
    orchestrator = _orchestrator_with_operator("OR")
    old_subset, operator = orchestrator._determine_subset_strategy(_layer(subset))
    assert operator is None


@pytest.fixture
def pg_adapter(monkeypatch):
    applied = []
    sql_utils = types.ModuleType(f"{ROOT}.infrastructure.database.sql_utils")
    sql_utils.safe_set_subset_string = lambda layer, expression: applied.append(expression) or True
    for name, module in (
        (ROOT, _package(ROOT)),
        (f"{ROOT}.infrastructure", _package(f"{ROOT}.infrastructure")),
        (f"{ROOT}.infrastructure.database", _package(f"{ROOT}.infrastructure.database")),
        (f"{ROOT}.infrastructure.database.sql_utils", sql_utils),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    adapter = legacy_module.LegacyPostgreSQLAdapter.__new__(legacy_module.LegacyPostgreSQLAdapter)
    adapter.task_params = {}
    adapter._use_new_backend = True
    adapter._new_backend = MagicMock()
    adapter._legacy_backend = MagicMock()
    return adapter, applied


@pytest.mark.parametrize("operator, expected", [
    ("AND", '("nature" = \'Route\') AND (EXISTS (x))'),
    ("OR", '("nature" = \'Route\') OR (EXISTS (x))'),
    ("AND NOT", '("nature" = \'Route\') AND NOT (EXISTS (x))'),
    (None, 'EXISTS (x)'),   # combination unchecked: replace (it was AND)
])
def test_postgresql_adapter_follows_the_operator(pg_adapter, operator, expected):
    adapter, applied = pg_adapter
    assert adapter.apply_filter(MagicMock(), 'EXISTS (x)', '"nature" = \'Route\'', operator) is True
    assert applied == [expected]
    adapter._legacy_backend.apply_filter.assert_not_called()
