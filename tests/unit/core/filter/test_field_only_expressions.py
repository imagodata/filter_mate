# -*- coding: utf-8 -*-
"""A field-only expression is never used as a filter; the source keeps its geometry column.

2026-10-17 (review): AttributeFilterExecutor.process_qgis_expression and
SourceLayerFilterExecutor._analyze_expression rejected a field-only expression
only when ``'IN' / 'OR' / 'AND' / '=' ...`` did not appear in the UPPER-CASED
text, so ``"importance"`` (IN), ``"origine"`` (OR, IN), ``"ordre"`` (OR) or
``"insee_com"`` (IN) were used as filters and ``( old ) AND ( "importance" )``
reached the provider (PostgreSQL: "argument of AND must be type boolean").
The display-expression check (``has_comparison``) had the same substring
test. The QGIS -> SQL conversion also wrote ``$geometry`` as "geometry"
whatever the layer's geometry column.
"""
import importlib.util
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.filter.sql_quotes import has_comparison_operator

_ROOT = Path(__file__).resolve().parents[4]
_PKG = "fmtest_attr_exec_pkg"


class _FakeExpression:
    """QgsExpression.isField(): the root node is a single column reference."""

    def __init__(self, text=''):
        self.text = text

    def isField(self):
        return bool(re.fullmatch(r'\s*"(?:[^"]|"")+"\s*', self.text))

    def isValid(self):
        return True

    def isFieldEqualityExpression(self, text):
        return (False, None, None)


def _package(name, path=None, **attrs):
    module = types.ModuleType(name)
    if path is not None:
        module.__path__ = [str(path)]
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


@pytest.fixture(scope="module")
def executor_module():
    _package(_PKG, _ROOT)
    _package(f"{_PKG}.infrastructure")
    _package(f"{_PKG}.infrastructure.constants", PROVIDER_POSTGRES='postgresql', PROVIDER_SPATIALITE='spatialite')
    _package(f"{_PKG}.infrastructure.utils", safe_set_subset_string=MagicMock(return_value=True))
    for sub in ("core", "core/filter", "core/services", "core/domain", "core/tasks", "core/tasks/executors"):
        _package(f"{_PKG}." + sub.replace('/', '.'), _ROOT / sub)
    name = f"{_PKG}.core.tasks.executors.attribute_filter_executor"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "core" / "tasks" / "executors" / "attribute_filter_executor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.QgsExpression = _FakeExpression
    yield module
    for key in [key for key in sys.modules if key == _PKG or key.startswith(f"{_PKG}.")]:
        sys.modules.pop(key, None)


def _executor(module, provider='ogr', geometry_field=None):
    layer = MagicMock()
    layer.fields.return_value = []
    executor = module.AttributeFilterExecutor(layer=layer, provider_type=provider, primary_key='fid',
                                              geometry_field=geometry_field)
    return executor


@pytest.mark.parametrize("expression", ['"importance"', '"origine"', '"ordre"', '"insee_com"', '"categorie"'])
def test_field_only_expression_is_rejected(executor_module, expression):
    assert _executor(executor_module).process_qgis_expression(expression) == (None, None)


@pytest.mark.parametrize("expression", ['coalesce("origine", \'\')', 'upper("ordre")', "'IN OR AND = '"])
def test_display_expression_is_rejected(executor_module, expression):
    assert _executor(executor_module).process_qgis_expression(expression) == (None, None)


@pytest.mark.parametrize("expression", ['"importance" = \'1\'', '"ordre" IN (1, 2)', '"origine" IS NULL',
                                        'NOT "actif"', '"a" ~ \'x\''])
def test_filter_expression_is_kept(executor_module, expression):
    processed, _ = _executor(executor_module).process_qgis_expression(expression)
    assert processed == expression


@pytest.mark.parametrize("geometry_field, expected", [
    ("the_geom", 'ST_Area("the_geom") > 10'),
    (None, 'ST_Area("geometry") > 10'),   # URI unavailable (mock): the former default
])
def test_postgis_conversion_uses_the_layer_geometry_column(executor_module, geometry_field, expected):
    executor = _executor(executor_module, 'postgresql', geometry_field)
    assert executor.process_qgis_expression('$area > 10')[0] == expected


@pytest.mark.parametrize("text, expected", [
    ('"importance"', False),
    ('"a" = 1', True),
    ("'x = 1'", False),
    ('"x" in (1)', True),
    ('"ordre" is null', True),
    ('coalesce("origine", \'OR\')', False),
])
def test_has_comparison_operator(text, expected):
    assert has_comparison_operator(text) is expected


def test_source_analysis_uses_is_field_alone():
    source = (_ROOT / "core" / "services" / "source_layer_filter_executor.py").read_text(encoding="utf-8")
    start = source.index("def _analyze_expression(")
    body = source[start:source.index("skip_source_filter = ", start)]
    assert "is_simple_field = expr_adapter.is_field()" in body
    assert "op in task_expr_upper" not in body
