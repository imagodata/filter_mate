# -*- coding: utf-8 -*-
"""No success message after filters a provider refused (FilterResultHandler.handle_task_completion).

2026-11-16: the PostgreSQL server gone, the 9 unfilters were refused and the warning said
"Filter not applied, previous filter kept", then "🐘 PostgreSQL: Successfully removed filters from
9 layer(s)" and "All filters cleared - ? features visible in main layer" came after it.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PKG = "fm_filter_result_refused_test"


def _load():
    """Load adapters/filter_result_handler.py inside a package, so its relative imports resolve."""
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".infrastructure", _ROOT / "infrastructure"),
                       (".config", _ROOT / "config")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.filter_result_handler")


@pytest.fixture
def handler(monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "_feature_count_or_none", lambda layer: None)
    handler = module.FilterResultHandler()
    for name in ("_determine_backend", "_show_task_completion_message", "_update_backend_indicator",
                 "_handle_auto_zoom", "_sync_project_layers", "_restore_current_layer",
                 "_refresh_ui_after_filtering", "_invalidate_expression_cache"):
        monkeypatch.setattr(handler, name, MagicMock())
    handler._determine_backend.return_value = ("postgresql", False)
    return handler


def _params(failures):
    return {"infos": {"layer_provider_type": "postgresql"}, "task": {"layers": []}, "_apply_failures": failures}


def test_refused_filters_give_no_success_message(handler):
    handler.handle_task_completion("unfilter", MagicMock(), _params(["Cables · Wyre: connection lost"]))
    handler._show_task_completion_message.assert_not_called()


def test_applied_filters_give_the_success_message(handler):
    handler.handle_task_completion("unfilter", MagicMock(), _params([]))
    handler._show_task_completion_message.assert_called_once()
