# -*- coding: utf-8 -*-
"""The filter task parameters carry the IS_SELECTING state of the dock (TaskParameterBuilder).

2026-11-13: the task selected the source features after every filter; it now does
so only when IS_SELECTING is on, read from the button when the task is built.
"""
import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from core.filter import sql_quotes

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_NAME = 'filter_mate.adapters.task_builder'


@pytest.fixture
def module(monkeypatch):
    """The real module, loaded from its file (other tests leave a mock under its name)."""
    for package, path in (('filter_mate', _ROOT), ('filter_mate.adapters', _ROOT / 'adapters'),
                          ('filter_mate.core', _ROOT / 'core'), ('filter_mate.core.filter', _ROOT / 'core' / 'filter')):
        if not isinstance(sys.modules.get(package), types.ModuleType) or not hasattr(sys.modules[package], '__path__'):
            stub = types.ModuleType(package)
            stub.__path__ = [str(path)]
            monkeypatch.setitem(sys.modules, package, stub)
    monkeypatch.setitem(sys.modules, 'filter_mate.core.filter.sql_quotes', sql_quotes)
    spec = importlib.util.spec_from_file_location(_NAME, _ROOT / 'adapters' / 'task_builder.py')
    loaded = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, _NAME, loaded)
    spec.loader.exec_module(loaded)
    return loaded


def _params(module, dockwidget, project_layers=None):
    builder = module.TaskParameterBuilder(dockwidget, project_layers or {})
    return builder.build_common_task_params(features=[], expression='', layers_to_filter=[])


@pytest.mark.parametrize('checked', [True, False])
def test_the_button_state_is_carried(module, checked):
    dockwidget = MagicMock()
    dockwidget.pushButton_checkable_exploring_selecting.isChecked.return_value = checked

    assert _params(module, dockwidget)['is_selecting'] is checked


@pytest.mark.parametrize('stored', [True, False])
def test_without_the_button_the_layer_settings_decide(module, stored):
    layer = MagicMock()
    layer.id.return_value = 'layer-1'
    dockwidget = types.SimpleNamespace(current_layer=layer, project_props={})
    project_layers = {'layer-1': {'exploring': {'is_selecting': stored}}}

    assert _params(module, dockwidget, project_layers)['is_selecting'] is stored


def test_without_a_dock_nothing_is_selected(module):
    assert _params(module, None)['is_selecting'] is False
