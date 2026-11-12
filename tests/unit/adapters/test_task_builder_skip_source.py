# -*- coding: utf-8 -*-
"""A custom selection filters the source layer unless it is a bare field (TaskParameterBuilder).

2026-11-12: the former test searched a list of operators holding ' LIKE ' but not
' ILIKE ': a custom selection ``"nom" ILIKE 'x'`` was taken for a display field
and the source layer was never filtered (seen on PostGIS, every backend alike).
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from core.filter import sql_quotes

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_NAME = 'filter_mate.adapters.task_builder'


@pytest.fixture
def builder(monkeypatch):
    """The real module, loaded from its file (other tests leave a mock under its name)."""
    for package, path in (('filter_mate', _ROOT), ('filter_mate.adapters', _ROOT / 'adapters'),
                          ('filter_mate.core', _ROOT / 'core'), ('filter_mate.core.filter', _ROOT / 'core' / 'filter')):
        if not isinstance(sys.modules.get(package), types.ModuleType) or not hasattr(sys.modules[package], '__path__'):
            stub = types.ModuleType(package)
            stub.__path__ = [str(path)]
            monkeypatch.setitem(sys.modules, package, stub)
    monkeypatch.setitem(sys.modules, 'filter_mate.core.filter.sql_quotes', sql_quotes)
    spec = importlib.util.spec_from_file_location(_NAME, _ROOT / 'adapters' / 'task_builder.py')
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, _NAME, module)
    spec.loader.exec_module(module)
    dockwidget = MagicMock()
    dockwidget.current_exploring_groupbox = 'custom_selection'
    return module.TaskParameterBuilder(dockwidget, {})


@pytest.mark.parametrize('expression', [
    '"nom" ILIKE \'saint\'',
    '"nom" NOT ILIKE \'r%\'',
    '"nom" LIKE \'R%\'',
    '"nom" ~ \'^R\'',
    '"pop" > 5',
    '"code" IN (1, 2)',
])
def test_a_filter_expression_filters_the_source(builder, expression):
    parameters = {'task': {'features': [object()]}}
    assert builder.determine_skip_source_filter('filter', parameters, expression) is False


@pytest.mark.parametrize('expression', ['"nom"', 'coalesce("nom", \'OR\')', '"importance"'])
def test_a_display_field_does_not_filter_the_source(builder, expression):
    parameters = {'task': {'features': [object()]}}
    assert builder.determine_skip_source_filter('filter', parameters, expression) is True
