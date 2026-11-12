# -*- coding: utf-8 -*-
"""Queuing the new subset of the source records it for the distant filters (2026-11-12).

See tests/unit/core/filter/test_source_filter_after_task.py: the source layer
keeps its previous subset until finished(); ExpressionBuilder reads this record.
Loaded by path under the conftest's mocked ``filter_mate`` tree.
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_TASKS_DIR = Path(__file__).resolve().parents[4] / "core" / "tasks"
NEW = '"src"."fid" IN (7, 8)'


@pytest.fixture
def facade_module():
    name = "filter_mate.core.tasks.expression_facade_handler"
    spec = importlib.util.spec_from_file_location(name, _TASKS_DIR / "expression_facade_handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


def test_queuing_the_source_subset_records_it_for_the_distant_filters(facade_module):
    task = MagicMock()
    task.param_source_provider_type = "ogr"   # not PostgreSQL: no history step here
    task._pending_subset_requests = []
    task.task_parameters = {}

    assert facade_module.ExpressionFacadeHandler(task).apply_filter_and_update_subset(NEW) is True

    assert task._pending_subset_requests == [(task.source_layer, NEW)]
    assert task.task_parameters["source_subset_after_task"] == NEW
