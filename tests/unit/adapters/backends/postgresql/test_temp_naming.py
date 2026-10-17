# -*- coding: utf-8 -*-
"""
2026-10-17: one materialized view prefix, one temp schema.

- The MV path of filter_actions created ``fm_temp_mv_<name>`` but set the
  layer subset (and the index, CLUSTER, ANALYZE, the reset and unfilter
  drops) on ``mv_<name>``: "relation does not exist", the filter failed.
- prepare_postgresql_source_geom / build_spatial_join_query referenced
  ``mv_<name>_dump`` while MaterializedViewHandler creates
  ``fm_temp_mv_<name>_dump``.
- The task path used the ``filter_mate_temp`` schema, the v4 backend
  (mv_manager, backend.py, cleanup service, chain optimizer...)
  ``filtermate_temp``: the session cleanup of one never saw the MVs of the
  other. infrastructure.constants now holds the one schema; the old
  spelling is only read by the cleanups.
"""
import ast
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parents[5]
PKG = "fmtest_temp_naming"
PG_DIR = PLUGIN_ROOT / "adapters" / "backends" / "postgresql"


def _package(name, path=None):
    module = types.ModuleType(name)
    module.__path__ = [str(path)] if path else []
    sys.modules[name] = module
    return module


def _load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _sandbox():
    _package(PKG, PLUGIN_ROOT)
    _package(f"{PKG}.adapters", PLUGIN_ROOT / "adapters")
    _package(f"{PKG}.adapters.backends", PLUGIN_ROOT / "adapters" / "backends")
    _package(f"{PKG}.adapters.backends.postgresql", PG_DIR)
    _package(f"{PKG}.adapters.repositories")
    history = types.ModuleType(f"{PKG}.adapters.repositories.history_repository")
    repo = MagicMock()
    repo.return_value.get_last_entry.return_value = None
    history.HistoryRepository = repo
    sys.modules[history.__name__] = history
    _package(f"{PKG}.infrastructure", PLUGIN_ROOT / "infrastructure")
    _package(f"{PKG}.infrastructure.database")
    sql_utils = types.ModuleType(f"{PKG}.infrastructure.database.sql_utils")
    sql_utils.sanitize_sql_identifier = lambda name: name
    sys.modules[sql_utils.__name__] = sql_utils
    constants = _load(f"{PKG}.infrastructure.constants", PLUGIN_ROOT / "infrastructure" / "constants.py")
    actions = _load(f"{PKG}.adapters.backends.postgresql.filter_actions", PG_DIR / "filter_actions.py")
    executor = _load(f"{PKG}.adapters.backends.postgresql.filter_executor", PG_DIR / "filter_executor.py")
    schema_manager = _load(f"{PKG}.adapters.backends.postgresql.schema_manager", PG_DIR / "schema_manager.py")
    return constants, actions, executor, schema_manager


constants, actions, executor, schema_manager = _sandbox()


@pytest.fixture(scope="module", autouse=True)
def _drop_sandbox():
    yield
    for name in [n for n in sys.modules if n == PKG or n.startswith(PKG + ".")]:
        sys.modules.pop(name, None)


def _layer():
    layer = MagicMock()
    layer.name.return_value = "batiment"
    layer.featureCount.return_value = 10
    return layer


def _relations(sql):
    """``"schema"."name"`` relations of an SQL text."""
    import re
    return set(re.findall(r'"filter_mate_temp"\."([^"]+)"', sql))


def test_materialized_filter_subset_names_the_view_it_created():
    executed, queued = [], []
    actions.execute_filter_action_postgresql_materialized(
        layer=_layer(), sql_subset_string='SELECT "fid", "geom" FROM "ign"."batiment" WHERE TRUE',
        primary_key_name="fid", geom_key_name="geom", name="batiment_ab12", custom=False,
        cur=MagicMock(), conn=MagicMock(), seq_order=1,
        queue_subset_fn=lambda layer, subset: queued.append(subset),
        get_connection_fn=MagicMock(), ensure_stats_fn=MagicMock(), insert_history_fn=MagicMock(),
        get_session_name_fn=lambda name: f"s01_{name}",
        ensure_schema_fn=lambda connexion, schema: schema,
        execute_commands_fn=lambda connexion, commands: executed.extend(commands),
        create_simple_mv_fn=schema_manager.create_simple_materialized_view_sql,
        create_custom_mv_fn=MagicMock(),
        source_schema="ign", source_table="batiment", source_geom="geom",
        current_mv_schema=constants.DEFAULT_TEMP_SCHEMA, session_id="s01",
    )
    created = {"fm_temp_mv_s01_batiment_ab12"}
    assert _relations(" ".join(executed)) == created
    assert _relations(queued[0]) == created
    assert queued[0] == ('"fid" IN (SELECT "fm_temp_mv_s01_batiment_ab12"."fid" '
                         'FROM "filter_mate_temp"."fm_temp_mv_s01_batiment_ab12")')


def test_reset_drops_the_view_the_filter_created():
    executed = []
    actions.execute_reset_action_postgresql(
        layer=_layer(), name="batiment_ab12", cur=MagicMock(), conn=MagicMock(),
        queue_subset_fn=MagicMock(), get_connection_fn=MagicMock(),
        execute_commands_fn=lambda connexion, commands: executed.extend(commands),
        get_session_name_fn=lambda name: f"s01_{name}", delete_history_fn=MagicMock(),
        current_mv_schema=constants.DEFAULT_TEMP_SCHEMA,
    )
    assert _relations(" ".join(executed)) == {"fm_temp_mv_s01_batiment_ab12", "fm_temp_mv_s01_batiment_ab12_dump"}


def test_unfilter_recreates_and_references_the_same_view():
    executed, queued = [], []
    entry = MagicMock(subset_string='SELECT "fid", "geom" FROM "ign"."batiment" WHERE "nature" = 1')
    actions.HistoryRepository.return_value.get_last_entry.return_value = entry
    try:
        actions.execute_unfilter_action_postgresql(
            layer=_layer(), primary_key_name="fid", geom_key_name="geom", name="batiment_ab12",
            cur=MagicMock(), conn=MagicMock(), last_subset_id="1",
            queue_subset_fn=lambda layer, subset: queued.append(subset), get_connection_fn=MagicMock(),
            execute_commands_fn=lambda connexion, commands: executed.extend(commands),
            get_session_name_fn=lambda name: f"s01_{name}",
            create_simple_mv_fn=schema_manager.create_simple_materialized_view_sql,
            current_mv_schema=constants.DEFAULT_TEMP_SCHEMA,
        )
    finally:
        actions.HistoryRepository.return_value.get_last_entry.return_value = None
    assert _relations(" ".join(executed)) == {"fm_temp_mv_s01_batiment_ab12"}
    assert _relations(queued[0]) == {"fm_temp_mv_s01_batiment_ab12"}


def test_new_view_names_still_count_as_filtermate_views():
    combine, reason = actions.should_combine_filters(
        '"fid" IN (SELECT "fm_temp_mv_s01_x"."fid" FROM "filter_mate_temp"."fm_temp_mv_s01_x")'
    )
    assert combine is False and "materialized view" in reason


def test_buffer_expression_source_reads_the_dump_view_handler_creates():
    geom, mv_name = executor.prepare_postgresql_source_geom(
        source_table="demand_points", source_schema="ref", source_geom="geom",
        buffer_expression='"homecount" * 2', session_id="s01",
        mv_schema=constants.DEFAULT_TEMP_SCHEMA, source_feature_count=50000,
    )
    assert mv_name == "s01_demand_points_buffer_expr"
    # MaterializedViewHandler: CREATE MATERIALIZED VIEW "<schema>"."fm_temp_mv_<mv_name>_dump"
    assert geom == '"filter_mate_temp"."fm_temp_mv_s01_demand_points_buffer_expr_dump"."geom"'


def test_one_temp_schema_constant():
    assert constants.DEFAULT_TEMP_SCHEMA == "filter_mate_temp"
    assert "filtermate_temp" in constants.LEGACY_TEMP_SCHEMAS
    assert constants.TABLE_PREFIX_MATERIALIZED == "fm_temp_mv_"


_SCANNED = ("adapters", "core", "infrastructure", "config", "ui", "extensions")
# backend_controller cleans both spellings on purpose (owned by another change)
_ALLOWED = {
    PLUGIN_ROOT / "infrastructure" / "constants.py",
    PLUGIN_ROOT / "ui" / "controllers" / "backend_controller.py",
}


def test_no_module_hard_codes_the_legacy_schema():
    offenders = []
    for top in _SCANNED:
        for path in (PLUGIN_ROOT / top).rglob("*.py"):
            if path in _ALLOWED:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value == "filtermate_temp":
                    offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{node.lineno}")
    assert offenders == []


def test_v4_backend_modules_use_the_constant():
    # source text check: these classes are not importable outside QGIS
    for relative, needle in [
        ("adapters/backends/postgresql/mv_manager.py", "MV_SCHEMA = DEFAULT_TEMP_SCHEMA"),
        ("adapters/backends/postgresql/filter_chain_optimizer.py", "MV_SCHEMA = DEFAULT_TEMP_SCHEMA"),
        ("adapters/backends/postgresql/cleanup.py", "DEFAULT_SCHEMA = DEFAULT_TEMP_SCHEMA"),
        ("core/services/postgres_session_manager.py", "DEFAULT_SCHEMA = DEFAULT_TEMP_SCHEMA"),
        ("core/optimization/combined_query_optimizer.py", "FILTERMATE_MV_SCHEMA = DEFAULT_TEMP_SCHEMA"),
    ]:
        assert needle in (PLUGIN_ROOT / relative).read_text(encoding="utf-8"), relative
