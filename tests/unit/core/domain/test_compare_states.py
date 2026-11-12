# -*- coding: utf-8 -*-
"""States before a filter operation for the Compare mode (core/domain/compare_states.py)."""
from types import SimpleNamespace

import pytest

from core.domain.compare_states import BeforeState, from_cross_operation, from_history_entry

pytestmark = pytest.mark.unit


def snapshot(layer_id, source="/data/a.tif", provider="gdal", subset=""):
    return SimpleNamespace(layer_id=layer_id, source=source, provider=provider, subset=subset)


def test_a_vector_filter_gives_the_former_subsets():
    entry = SimpleNamespace(previous_filters=(("a", '"pop" > 10'), ("b", None), ("a", "later")))
    assert from_history_entry(entry) == [BeforeState("a", '"pop" > 10'), BeforeState("b", "")]
    assert from_history_entry(SimpleNamespace()) == []


def test_a_cross_operation_gives_the_snapshots_before():
    operation = SimpleNamespace(changes=(
        (snapshot("v", "/d/v.gpkg", "ogr", '"x" = 1'), snapshot("v", "/d/v.gpkg", "ogr", '"x" = 2')),
        (snapshot("r", "/d/dem.tif"), snapshot("r", "/tmp/fm/dem_clip.tif")),
        (snapshot("v", "/d/v.gpkg", "ogr", "second"), snapshot("v", "/d/v.gpkg", "ogr", "third")),
    ))
    states = from_cross_operation(operation)
    assert states == [BeforeState("v", '"x" = 1'), BeforeState("r", "", "/d/dem.tif", "gdal")]
    assert not states[0].other_source and states[1].other_source
    assert from_cross_operation(SimpleNamespace(changes=None)) == []
