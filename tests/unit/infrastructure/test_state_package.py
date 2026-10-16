# -*- coding: utf-8 -*-
"""infrastructure.state exported AtomicFlag and TemporaryFlag, absent from
flag_manager: importing the package raised ImportError."""
import importlib

import pytest


@pytest.mark.unit
def test_state_package_imports():
    state = importlib.import_module("infrastructure.state")

    for name in state.__all__:
        assert hasattr(state, name), name
    assert state.FlagManager is not None
