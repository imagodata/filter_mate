# -*- coding: utf-8 -*-
"""A PostgreSQL source layer receives the expression already combined, once.

2026-10-17: ExpressionFacadeHandler.apply_filter_and_update_subset queues
``(source, expression)`` with the expression already combined with the old
subset by the operator the user chose, then builds ``SELECT ... WHERE
<expression>`` for the history / materialized-view step. The direct step,
execute_filter_action_postgresql_direct, extracted that WHERE and combined it
AGAIN with the layer's current subset, with AND hard-coded, and queued a
second request that was applied last:

- OR: ``(old) AND ((old) OR (new))`` = old alone;
- combination unchecked (replace): ``(old) AND (new)`` instead of new.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PKG = "fmtest_pg_actions_pkg"


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


OLD = '"nature" = \'Route\''


@pytest.mark.parametrize("combined", [
    f'( {OLD} ) OR ( "importance" = \'1\' )',          # OR, combined upstream
    '"importance" = \'1\'',                             # combination unchecked: replace
    f'( {OLD} ) AND NOT ( "importance" = \'1\' )',
])
def test_direct_filter_applies_the_expression_combined_upstream(actions, combined):
    layer = MagicMock()
    layer.subsetString.return_value = OLD   # the queued request is not applied yet
    queued = []
    select = f'SELECT "t"."fid", "t"."geom" FROM "public"."t" WHERE {combined}'  # nosec B608 - test data

    assert actions.execute_filter_action_postgresql_direct(
        layer=layer, sql_subset_string=select, primary_key_name="fid", cur=MagicMock(), conn=MagicMock(),
        seq_order=1, queue_subset_fn=lambda lyr, expression: queued.append(expression),
        get_connection_fn=MagicMock(), ensure_stats_fn=MagicMock(),
        extract_where_fn=lambda sql: sql[sql.index(' WHERE '):],
        insert_history_fn=MagicMock(), source_schema="public", source_table="t", source_geom="geom",
    ) is True

    assert queued == [combined]
