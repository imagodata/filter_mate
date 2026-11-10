# -*- coding: utf-8 -*-
"""The objects drawn with SAM are a raster selection of the MCP tools (2026-11-10)."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp")
pytest.importorskip("fastapi")

from pydantic import ValidationError  # noqa: E402

from filtermate_api.mcp.server import RasterSelection  # noqa: E402

SQUARE = "POLYGON((0 0,1 0,1 1,0 1,0 0))"


def test_segments_are_accepted():
    selection = RasterSelection(segments=[SQUARE])
    assert selection.segments == [SQUARE] and selection.mode == "range"


@pytest.mark.parametrize("fields", [
    {"segments": ["POINT(0 0)"]},
    {"segments": [SQUARE], "minimum": 1.0},
    {"segments": [SQUARE], "classes": [6]},
    {"segments": [SQUARE], "expression": "\"a@1\" > 1"},
    {"segments": [SQUARE], "derivative": "slope_percent"},
])
def test_invalid_segments_are_refused(fields):
    with pytest.raises(ValidationError):
        RasterSelection(**fields)


def test_the_objects_of_the_dock_are_a_selection_of_their_own():
    assert RasterSelection(dock_objects=True).dock_objects is True
    for fields in ({"segments": [SQUARE]}, {"minimum": 1.0}, {"classes": [6]}, {"derivative": "aspect"}):
        with pytest.raises(ValidationError):
            RasterSelection(dock_objects=True, **fields)
