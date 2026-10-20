# -*- coding: utf-8 -*-
"""
The bounded memory copy of a remote source survives a provider wrapper that PyQt invalidated.

PyQt invalidates the wrapper of a C++-created QObject from a destroyed() notification queued to the
main thread and keyed by address: a memory provider created in a worker where a deleted object lived
can lose its fresh wrapper while alive ("wrapped C/C++ object of type QgsVectorDataProvider has been
deleted"). sip checks the wrapper before the call, so the call did not run and the layer hands a usable
wrapper again (check_stream_vector_spatial.py on qgis/qgis:latest, about 2.5 % of the runs, #207).
"""
import sys
from unittest.mock import MagicMock

import pytest

from tests.unit.adapters.backends.ogr.test_worker_leaves_project_alone import _executor

pytestmark = pytest.mark.unit

DELETED = RuntimeError("wrapped C/C++ object of type QgsVectorDataProvider has been deleted")


class _Provider:
    def __init__(self):
        self.attributes, self.features = [], []


class _Wrapper:
    """One Python wrapper of the provider; PyQt may invalidate it between its creation and a call."""

    def __init__(self, memory):
        self.memory, self.dead = memory, False

    def _call(self, step):
        if self.dead or self.memory.kill(step):
            self.dead = True
            raise DELETED  # sip checks the wrapper first: the C++ method never ran

    def addAttributes(self, fields):
        self._call('addAttributes')
        self.memory.real.attributes.extend(fields)
        return True

    def addFeatures(self, features):
        self._call('addFeatures')
        self.memory.real.features.extend(features)
        return True, features


class _Memory:
    """A memory layer: each dataProvider() call hands a new wrapper of the same provider."""

    def __init__(self, dead_for):
        self.real = _Provider()
        self.dead_for = dict(dead_for)

    def kill(self, step):
        if self.dead_for.get(step, 0) > 0:
            self.dead_for[step] -= 1
            return True
        return False

    def dataProvider(self):
        return _Wrapper(self)

    def setCrs(self, crs): pass
    def updateFields(self): pass
    def updateExtents(self): pass


@pytest.fixture
def module(monkeypatch):
    executor = _executor()
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsFeature", lambda feature: feature, raising=False)
    monkeypatch.setattr(core, "QgsWkbTypes", MagicMock(), raising=False)
    return executor, core


def _source():
    source = MagicMock()
    source.fields.return_value = ["id", "name"]
    return source


@pytest.mark.parametrize("dead_for", [{"addAttributes": 1}, {"addFeatures": 1}, {"addAttributes": 2, "addFeatures": 2}])
def test_an_invalidated_provider_wrapper_is_asked_again(module, monkeypatch, dead_for):
    executor, core = module
    memory = _Memory(dead_for)
    monkeypatch.setattr(core, "QgsVectorLayer", lambda *args: memory, raising=False)

    copy = executor._memory_source(_source(), ["f1", "f2"])

    assert copy is memory
    assert memory.real.attributes == ["id", "name"]  # added once: a dead wrapper never runs the call
    assert memory.real.features == ["f1", "f2"]


def test_a_provider_that_stays_invalid_is_a_read_error(module, monkeypatch):
    executor, core = module
    memory = _Memory({"addAttributes": 10})
    monkeypatch.setattr(core, "QgsVectorLayer", lambda *args: memory, raising=False)

    with pytest.raises((RuntimeError, ValueError)):
        executor._memory_source(_source(), ["f1"])
    assert memory.real.features == []
