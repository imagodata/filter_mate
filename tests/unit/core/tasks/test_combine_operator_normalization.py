"""Translated combine operators are normalized to operators the combiners accept.

2026-10-17: normalize_sql_operator mapped NON / NICHT / NO / NÃO (and NOT)
to 'NOT'. The combiners write ``( old ) <operator> ( new )``, so the layer
received ``( old ) NOT ( new )``: a syntax error on every backend. The
negated combination FilterMate offers is AND NOT.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_TASKS_DIR = Path(__file__).resolve().parents[4] / "core" / "tasks"


@pytest.fixture
def facade():
    # Loaded by path under the conftest's mocked ``filter_mate`` tree (see
    # test_source_combine_replace.py).
    name = "filter_mate.core.tasks.expression_facade_handler"
    spec = importlib.util.spec_from_file_location(name, _TASKS_DIR / "expression_facade_handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module.ExpressionFacadeHandler(MagicMock())
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("operator, expected", [
    ("NON", "AND NOT"),
    ("NICHT", "AND NOT"),
    ("NO", "AND NOT"),
    ("NÃO", "AND NOT"),
    ("NOT", "AND NOT"),
    ("not", "AND NOT"),
    ("ET NON", "AND NOT"),
    ("AND NOT", "AND NOT"),
    ("ET", "AND"),
    ("OU", "OR"),
    ("or", "OR"),
    (" and ", "AND"),
])
def test_operator_is_one_the_combiners_accept(facade, operator, expected):
    assert facade.normalize_sql_operator(operator) == expected


@pytest.mark.parametrize("operator", [None, ""])
def test_no_operator_stays_none(facade, operator):
    assert facade.normalize_sql_operator(operator) is None
