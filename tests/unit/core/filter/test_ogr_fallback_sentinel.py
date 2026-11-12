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
    source = (PLUGIN_ROOT / "filtermate_core" / "sql" / "spatialite" / "expression_builder.py").read_text(encoding="utf-8")  # 2026-10-28: the host-free core
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


def test_hybrid_attribute_subsets_are_not_taken_for_spatial_key_lists():
    """A hybrid attribute filter (native_dialect.hybrid_sql) stays an attribute filter, 2026-11-12.

    Read as the key list of a previous spatial step, it would be replaced by
    the next spatial filter instead of being combined with it.
    """
    from filtermate_core.filter.native_dialect import hybrid_sql
    for subset in (hybrid_sql('', [2, 5], None, '"fid"', True),
                   hybrid_sql('"fid" IN (1, 2, 3)', [1, 2], [3], '"fid"', True),
                   hybrid_sql('', ['a1'], None, '"code"', False)):
        for pk in ('fid', 'code'):
            assert orchestrator_module.FilterOrchestrator._is_key_list_subset(_layer(subset, pk), subset) is False


@pytest.mark.parametrize("subset, operator, expected", [
    ('"cleabs" IN (\'TRON1\')', None, ('"cleabs" IN (\'TRON1\')', None)),    # no operator: replaced
    ('"cleabs" IN (\'TRON1\')', "AND", ('"cleabs" IN (\'TRON1\')', "AND")),  # 2026-11-12: combined
    ('"nature" = \'Route\'', "AND", ('"nature" = \'Route\'', "AND")),        # attribute: combined
    ('ST_Intersects("geom", X)', None, (None, None)),                      # no operator: replaced
    ('ST_Intersects("geom", X)', "AND", ('ST_Intersects("geom", X)', "AND")),  # 2026-11-12: combined
])
def test_subset_strategy_treats_every_key_list_as_spatial(monkeypatch, subset, operator, expected):
    orchestrator = orchestrator_module.FilterOrchestrator(
        task_parameters={}, subset_queue_callback=MagicMock(), parent_task=MagicMock(),
        get_predicates_callback=lambda: {},
    )
    monkeypatch.setattr(orchestrator, "_get_combine_operator", lambda: operator)
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


@pytest.mark.parametrize("subset", [
    "coalesce(\"nom\",'')='route'",                   # the native SQLite translation writes COALESCE("nom", '')
    "COALESCE(\"nom\", '') = 'route' AND \"a\" > 1",
    "CASE WHEN \"a\" > 1 THEN true ELSE false END",
    "(\"a\" = 1 AND TRUE)",
])
def test_a_filter_that_looks_like_a_style_is_combined(subset):
    """2026-11-12: the style patterns matched these real filters, which were replaced without a word."""
    orchestrator = _orchestrator_with_operator("AND")
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (subset, "AND")


@pytest.mark.parametrize("subset", ["coalesce(\"nom\", '')", "COALESCE(\"nom\", 'sans nom')"])
def test_a_display_expression_is_still_replaced(subset):
    orchestrator = _orchestrator_with_operator("AND")
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (None, None)


@pytest.mark.parametrize("subset", [
    "\"actif\"",                                   # a boolean column
    "starts_with(\"nom\", 'Rue')",
    "regexp_match(\"nom\", '^A')",
    "instr(\"nom\", 'x')",
    "array_contains(\"tags\", 'route')",
    "coalesce(\"actif\", false)",
])
def test_a_boolean_function_or_column_is_combined(subset):
    """2026-11-12 (review): any call or column without a comparison was taken for a style and replaced in silence;
    only what the old patterns named AND returns no boolean (coalesce(field, 'text')) is a style now."""
    orchestrator = _orchestrator_with_operator("AND")
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (subset, "AND")


@pytest.mark.parametrize("operator", ["AND", "OR", "AND NOT", None])
def test_a_target_without_filter_gets_the_operator(operator):
    """2026-11-12: (None, operator), so that AND NOT writes NOT (new) on a target without a filter."""
    orchestrator = _orchestrator_with_operator(operator)
    assert orchestrator._determine_subset_strategy(_layer('')) == (None, operator)


@pytest.mark.parametrize("subset, expected", [
    ('NOT ( "fid" IN (1, 2) )', ('NOT ( "fid" IN (1, 2) )', "AND NOT")),   # keys: combined, old minus new
    ('"fid" IN (1, 2)', ('"fid" IN (1, 2)', "AND NOT")),
    ('NOT ($id IN (1, 2))', ('NOT ($id IN (1, 2))', "AND NOT")),
    ('ST_Intersects("geom", X)', (None, "AND NOT")),                    # spatial: replaced, then NOT (new)
    ('NOT ( EXISTS (SELECT 1 FROM "s" AS __source WHERE ST_Intersects(a, b)) )', (None, "AND NOT")),
    ("coalesce(\"nom\", '')", (None, "AND NOT")),                        # style: replaced, then NOT (new)
])
def test_and_not_after_a_previous_spatial_step_still_excludes(subset, expected):
    """2026-11-12 (review): the replaced filters went with no operator, and the builders wrote the new selection
    itself: a second AND NOT kept what it was asked to remove."""
    orchestrator = _orchestrator_with_operator("AND NOT")
    assert orchestrator._determine_subset_strategy(_layer(subset)) == expected


# ---------------------------------------------------------------------------
# 2026-11-12 (user decision): a new geometric filter combines with the subset of
# a previous spatial step under OR and AND (it replaced it: OR and AND then kept
# the new selection only). No operator still replaces; AND NOT is unchanged
# (above); a style expression is still replaced.
# ---------------------------------------------------------------------------

_PREVIOUS_SPATIAL_SUBSETS = [
    '"fid" IN (1, 2)',                                                     # OGR / SQLite key list
    '"fid" IN (SELECT value FROM json_each(\'[1,2]\'))',
    'ST_Intersects("geom", X)',
    'EXISTS (SELECT 1 FROM "public"."fm_temp_buf_s_0123" AS __buffer '
    'WHERE ST_Intersects("t"."geom", __buffer.buffered_geom))',           # PostgreSQL buffer table
    '("t"."geom" && (SELECT ST_Extent(__source."geom") FROM "public"."s" AS __source)) AND '
    'EXISTS (SELECT 1 FROM "public"."s" AS __source WHERE ST_Intersects("t"."geom", __source."geom"))',
    'ROWID IN (SELECT id FROM "rtree_t_geom" WHERE minx <= 1.0) AND '
    'Intersects("geom", GeomFromText(\'POINT(0 0)\', 2154)) = 1',          # GeoPackage, inline
    '(EXISTS (SELECT 1 FROM "s" AS __source WHERE ST_Intersects(a, b))) OR '
    '(EXISTS (SELECT 1 FROM "s" AS __source WHERE ST_Intersects(a, c)))',  # already combined
]


@pytest.mark.parametrize("operator", ["OR", "AND"])
@pytest.mark.parametrize("subset", _PREVIOUS_SPATIAL_SUBSETS)
def test_previous_spatial_filter_is_combined_under_or_and_and(subset, operator):
    orchestrator = _orchestrator_with_operator(operator)
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (subset, operator)


@pytest.mark.parametrize("subset", _PREVIOUS_SPATIAL_SUBSETS)
def test_previous_spatial_filter_is_replaced_without_operator(subset):
    orchestrator = _orchestrator_with_operator(None)
    old_subset, operator = orchestrator._determine_subset_strategy(_layer(subset))
    assert operator is None
    assert old_subset in (None, subset)   # a key list is kept for no combination ("fid" IN: (old, None))


# The SpatiaLite inline form (Intersects(...), no ST_ name) is no geometric subset for the
# orchestrator: it goes with its operator, and the SpatiaLite / OGR builders replace it under
# AND NOT themselves (_is_geometric_filter), as before.
@pytest.mark.parametrize("subset", [s for s in _PREVIOUS_SPATIAL_SUBSETS if 'EXISTS' in s or 'ST_' in s])
def test_and_not_still_replaces_a_previous_geometric_filter(subset):
    orchestrator = _orchestrator_with_operator("AND NOT")
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (None, "AND NOT")


@pytest.mark.parametrize("operator", ["OR", "AND"])
@pytest.mark.parametrize("subset", ["coalesce(\"nom\", '')", "COALESCE(\"nom\", 'sans nom')"])
def test_a_display_expression_is_still_replaced_under_or_and_and(subset, operator):
    orchestrator = _orchestrator_with_operator(operator)
    assert orchestrator._determine_subset_strategy(_layer(subset)) == (None, None)


@pytest.mark.parametrize("operator, expected", [
    ("OR", '(EXISTS (old)) OR (EXISTS (x))'),
    ("AND", '(EXISTS (old)) AND (EXISTS (x))'),
    ("AND NOT", 'NOT (\nEXISTS (x)\n)'),
    (None, 'EXISTS (x)'),
])
def test_postgresql_adapter_combines_a_previous_geometric_filter(pg_adapter, operator, expected):
    """The orchestrator's strategy, then the PostgreSQL adapter: the subset that reaches the layer."""
    adapter, applied = pg_adapter
    orchestrator = _orchestrator_with_operator(operator)
    old_subset, combine = orchestrator._determine_subset_strategy(_layer('EXISTS (old)'))
    assert adapter.apply_filter(MagicMock(), 'EXISTS (x)', old_subset, combine) is True
    assert applied == [expected]


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


def test_postgresql_adapter_without_filter_writes_not_under_and_not(pg_adapter):
    """2026-11-12: AND NOT on a target without a filter takes the new selection out of the whole layer."""
    adapter, applied = pg_adapter
    assert adapter.apply_filter(MagicMock(), 'EXISTS (x)', None, 'AND NOT') is True
    assert adapter.apply_filter(MagicMock(), 'EXISTS (x)', None, 'AND') is True
    assert applied == ['NOT (\nEXISTS (x)\n)', 'EXISTS (x)']


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


@pytest.mark.parametrize("subset", ["$id IN (3, 7)", "NOT ($id IN (3, 7))", "($id IN (1))"])
def test_feature_id_lists_of_memory_layers_are_key_lists(subset):
    """2026-10-17: the OGR backend writes $id IN (...) on memory / delimited text layers."""
    assert orchestrator_module.FilterOrchestrator._is_key_list_subset(_layer(subset), subset) is True


@pytest.mark.parametrize("stable, subset, key_list", [
    ("cleabs", '"cleabs" IN (\'COMMUNE_1\')', True),     # web service key, not declared
    ("id", '"id" IN (4, 5)', True),                       # a proven unique id of a Shapefile
    (None, '"cleabs" IN (\'COMMUNE_1\')', False),        # not the layer's key: an attribute filter
])
def test_the_stable_key_list_is_a_key_list(monkeypatch, stable, subset, key_list):
    probe = types.ModuleType(f"{ROOT}.adapters.qgis.source_capability_probe")
    calls = []

    def stable_key_for_layer(layer, scan=True):
        calls.append(scan)
        return types.SimpleNamespace(name=stable, is_field=stable is not None)

    probe.stable_key_for_layer = stable_key_for_layer
    monkeypatch.setitem(sys.modules, probe.__name__, probe)
    layer = _layer(subset, pk="fid")
    assert orchestrator_module.FilterOrchestrator._is_key_list_subset(layer, subset) is key_list
    assert calls == [False], "cached verdicts only: no read of the layer here"
