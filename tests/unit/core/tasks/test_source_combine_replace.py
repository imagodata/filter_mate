"""The source layer filter replaces the old subset when the combine option is off.

2026-09-14: FilterEngineTask._get_attribute_executor passed
``param_source_layer_combine_operator or 'AND'`` to AttributeFilterExecutor, so
the source layer kept every previous subset (AND) even with the combine button
unchecked, while targets already replaced theirs through get_combine_operator().
The executor now receives get_source_combine_operator(): None means REPLACE
(see tests/unit/core/filter/test_expression_combiner.py for the combiner side).
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_TASKS_DIR = Path(__file__).resolve().parents[4] / "core" / "tasks"


@pytest.fixture
def facade_cls():
    # Loaded by path under the conftest's mocked ``filter_mate`` tree so the
    # module's relative imports (infrastructure, config, ports) resolve.
    name = "filter_mate.core.tasks.expression_facade_handler"
    spec = importlib.util.spec_from_file_location(
        name, _TASKS_DIR / "expression_facade_handler.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module.ExpressionFacadeHandler
    finally:
        sys.modules.pop(name, None)


def test_source_operator_is_none_when_combine_option_off(facade_cls):
    task = MagicMock()
    task.has_combine_operator = False
    task.param_source_layer_combine_operator = 'AND'

    assert facade_cls(task).get_source_combine_operator() is None


def test_source_operator_kept_when_combine_option_on(facade_cls):
    task = MagicMock()
    task.has_combine_operator = True
    task.param_source_layer_combine_operator = 'OR'

    assert facade_cls(task).get_source_combine_operator() == 'OR'


def test_filter_task_wires_source_operator_getter():
    source = (_TASKS_DIR / "filter_task.py").read_text(encoding="utf-8")
    start = source.index("def _get_attribute_executor(self):")
    body = source[start:source.index("def _get_spatial_executor(self):")]

    assert "combine_operator=self._get_source_combine_operator()" in body
    assert "combine_operator=self.param_source_layer_combine_operator or 'AND'" not in body


@pytest.mark.parametrize("operator, expected", [
    ("AND NOT", 'NOT ( "class" = \'major\' )'),   # 2026-11-12: it kept only what it was asked to remove
    ("AND", '"class" = \'major\''),
    ("OR", '"class" = \'major\''),
    (None, '"class" = \'major\''),
])
def test_source_without_filter_and_not_takes_the_selection_out_of_the_layer(facade_cls, operator, expected):
    task = MagicMock()
    task._get_attribute_executor.return_value = MagicMock(old_subset='', combine_operator=operator)

    assert facade_cls(task).combine_with_old_subset('"class" = \'major\'') == expected
    task._get_attribute_executor.return_value.combine_with_old_subset.assert_not_called()


def test_source_with_a_filter_is_combined_by_the_executor(facade_cls):
    task = MagicMock()
    executor = MagicMock(old_subset='"a" = 1', combine_operator="AND NOT")
    executor.combine_with_old_subset.return_value = '( "a" = 1 ) AND NOT ( "b" = 2 )'
    task._get_attribute_executor.return_value = executor

    assert facade_cls(task).combine_with_old_subset('"b" = 2') == '( "a" = 1 ) AND NOT ( "b" = 2 )'
