# -*- coding: utf-8 -*-
"""A PostgreSQL source layer is filtered without a psycopg2 connection of its own.

2026-11-12 (Zones MRO -> 8 layers, Intersect): QGIS reads the layer with its own
connection (pg_service.conf, password asked at opening and not saved, authcfg
other than Basic...) while psycopg2 cannot open one from the layer's URI. The
direct filter step asked for that connection only to refresh the table
statistics, outside its ``try``: the exception of get_connection_fn aborted the
task once the source subset was queued, so the source layer was filtered and
the distant layers never were ("Task failed"). The reset step only drops a
materialized view with it and failed the same way.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_pg_noconn_pkg"
_SELECT = ('SELECT "zone_mro"."id", "zone_mro"."geom" FROM "public"."zone_mro" '  # nosec B608 - test data
           'WHERE "zone_mro"."id" IN (\'8d59e33a\')')


def _module(name, path=None, **attrs):
    module = types.ModuleType(name)
    if path is not None:
        module.__path__ = [str(path)]
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


@pytest.fixture(scope="module")
def actions():
    _module(_PKG, _ROOT)
    _module(f"{_PKG}.adapters", _ROOT / "adapters")
    _module(f"{_PKG}.adapters.repositories")
    _module(f"{_PKG}.adapters.repositories.history_repository", HistoryRepository=MagicMock())
    _module(f"{_PKG}.adapters.backends", _ROOT / "adapters" / "backends")
    _module(f"{_PKG}.adapters.backends.postgresql", _ROOT / "adapters" / "backends" / "postgresql")
    name = f"{_PKG}.adapters.backends.postgresql.filter_actions"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "adapters" / "backends" / "postgresql" / "filter_actions.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


def _no_connection():
    # FilterEngineTask._get_valid_postgresql_connection when psycopg2 cannot connect
    raise Exception("No valid PostgreSQL connection available: could not obtain a connection from the layer.")


def _layer():
    layer = MagicMock()
    layer.name.return_value = "Zones MRO"
    layer.id.return_value = "zone_mro_layer"
    layer.featureCount.return_value = 12
    return layer


def test_the_direct_filter_goes_on_without_a_psycopg2_connection(actions):
    queued, history = [], []
    ensure_stats = MagicMock()

    assert actions.execute_filter_action_postgresql_direct(
        layer=_layer(), sql_subset_string=_SELECT, primary_key_name="id", cur=MagicMock(), conn=MagicMock(),
        seq_order=1, queue_subset_fn=lambda lyr, expression: queued.append(expression),
        get_connection_fn=_no_connection, ensure_stats_fn=ensure_stats,
        extract_where_fn=lambda sql: sql[sql.index(' WHERE '):],
        insert_history_fn=lambda *args: history.append(args),
        source_schema="public", source_table="zone_mro", source_geom="geom",
    ) is True

    assert queued == ['"zone_mro"."id" IN (\'8d59e33a\')']
    assert len(history) == 1
    ensure_stats.assert_not_called()


def test_the_direct_filter_still_refreshes_the_statistics_with_a_connection(actions):
    connection = MagicMock()
    ensure_stats = MagicMock()

    assert actions.execute_filter_action_postgresql_direct(
        layer=_layer(), sql_subset_string=_SELECT, primary_key_name="id", cur=MagicMock(), conn=MagicMock(),
        seq_order=1, queue_subset_fn=MagicMock(), get_connection_fn=lambda: connection,
        ensure_stats_fn=ensure_stats, extract_where_fn=lambda sql: sql[sql.index(' WHERE '):],
        insert_history_fn=MagicMock(), source_schema="public", source_table="zone_mro", source_geom="geom",
    ) is True

    ensure_stats.assert_called_once_with(connection, "public", "zone_mro", "geom")


def test_a_large_source_is_filtered_directly_without_a_psycopg2_connection(actions):
    """A materialized view needs the connection: without it the filter is direct."""
    layer = _layer()
    layer.featureCount.return_value = actions.MATERIALIZED_VIEW_THRESHOLD + 1
    queued, execute_commands = [], MagicMock()

    assert actions.execute_filter_action_postgresql(
        layer=layer, sql_subset_string=_SELECT, primary_key_name="id", geom_key_name="geom",
        name="zone_mro_layer", custom=False, cur=MagicMock(), conn=MagicMock(), seq_order=1,
        queue_subset_fn=lambda lyr, expression: queued.append(expression),
        get_connection_fn=_no_connection, ensure_stats_fn=MagicMock(),
        extract_where_fn=lambda sql: sql[sql.index(' WHERE '):], insert_history_fn=MagicMock(),
        get_session_name_fn=lambda name: name, ensure_schema_fn=MagicMock(),
        execute_commands_fn=execute_commands, create_simple_mv_fn=MagicMock(return_value="CREATE"),
        create_custom_mv_fn=MagicMock(), source_schema="public", source_table="zone_mro", source_geom="geom",
    ) is True

    assert queued == ['"zone_mro"."id" IN (\'8d59e33a\')']
    execute_commands.assert_not_called()


def test_the_reset_clears_the_filter_without_a_psycopg2_connection(actions):
    queued = []
    execute_commands = MagicMock()

    assert actions.execute_reset_action_postgresql(
        layer=_layer(), name="zone_mro_layer", cur=MagicMock(), conn=MagicMock(),
        queue_subset_fn=lambda lyr, expression: queued.append(expression),
        get_connection_fn=_no_connection, execute_commands_fn=execute_commands,
        get_session_name_fn=lambda name: name, project_uuid="project",
    ) is True

    assert queued == ['']
    execute_commands.assert_not_called()
