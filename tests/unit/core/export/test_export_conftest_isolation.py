# -*- coding: utf-8 -*-
"""The export conftest must not break the `from core....` imports of the other test directories (2026-11-26).

Its ``sys.modules['core']`` stub used to shadow the real package without a ``__path__``: any run collecting
this directory before ``tests/unit/agent`` failed at collection with ``ModuleNotFoundError: No module named
'core.agent'``. ``find_spec`` proves the fallthrough without importing anything.
"""
import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_core_stub_falls_through_to_the_real_package():
    assert importlib.util.find_spec("core.agent") is not None
