# -*- coding: utf-8 -*-
"""Tests of the pure readable text of a favorite (no QGIS runtime)."""

from __future__ import annotations

from core.domain.favorites_manager import FilterFavorite
from ui.dialogs import favorite_summary as fs


def tr(s):
    return s


def _full():
    return FilterFavorite(
        name="Parcelles A > 20 m²",
        expression="\"type\" = 'A' AND \"surface\" > 20",
        layer_name="parcelles",
        remote_layers={
            "ogr::troncon": {
                "expression": "1=1", "feature_count": 12, "layer_id": "l1",
                "display_name": "troncon_de_route", "provider": "ogr",
            },
            "ogr::batiment": {
                "expression": "1=1", "feature_count": 5, "layer_id": "l2",
                "display_name": "batiment", "provider": "ogr",
            },
        },
        spatial_config={
            "geometric_predicates": ["Intersect", "Within"],
            "has_geometric_predicates": True,
            "buffer_value": 25.0,
        },
        tags=["urbanisme", "PLU"],
    )


def test_full_favorite():
    rows = fs.summary_rows(_full(), tr)
    assert [label for label, _ in rows] == ["Filter", "Then", "Spatial", "Tags"]
    by = dict(rows)
    assert by["Filter"].startswith("parcelles : ")
    assert "troncon_de_route (12)" in by["Then"]
    assert "batiment (5)" in by["Then"]
    assert "25" in by["Spatial"]
    assert "25.0" not in by["Spatial"]
    assert "Intersect" in by["Spatial"] and "Within" in by["Spatial"]
    assert by["Tags"] == "urbanisme, PLU"


def test_bare_favorite():
    fav = FilterFavorite(name="x", expression="\"a\" = 1", layer_name="l")
    rows = fs.summary_rows(fav, tr)
    assert [label for label, _ in rows] == ["Filter"]


def test_remote_name_falls_back_to_key_after_separator():
    fav = FilterFavorite(
        name="x", expression="1=1", layer_name="l",
        remote_layers={"ogr::batiment": {"feature_count": 3}},
    )
    assert "batiment (3)" in dict(fs.summary_rows(fav, tr))["Then"]


def test_legacy_values():
    assert fs.date_text("") == "-"
    assert fs.date_text(None) == "-"
    assert fs.date_text("not a date") == "-"
    assert fs.date_text("2026-11-24T10:30:00") == "24/11/2026"

    fav = _full()
    fav.spatial_config = {"geometric_predicates": ["Intersect"], "buffer_value": 0}
    assert "buffer" not in dict(fs.summary_rows(fav, tr))["Spatial"]
    fav.spatial_config = {"geometric_predicates": ["Intersect"]}
    assert "buffer" not in dict(fs.summary_rows(fav, tr))["Spatial"]
    fav.spatial_config = {"geometric_predicates": ["Strange"]}
    assert dict(fs.summary_rows(fav, tr))["Spatial"] == "Strange"
    fav.spatial_config = None
    assert "Spatial" not in dict(fs.summary_rows(fav, tr))


def test_real_predicate_keys_have_labels():
    for key in ("Intersect", "Contain", "Disjoint", "Equal", "Touch", "Overlap",
                "Are within", "Cross"):
        assert key in fs.PREDICATE_LABELS


def test_use_text():
    assert fs.use_text(0, None, tr) == "Never used"
    assert fs.use_text(1, "2026-11-24T10:00:00", tr) == "Used 1 time"
    assert fs.use_text(3, None, tr) == "Used 3 times"


def test_scope_badge():
    assert fs.scope_badge(True, tr) == "Global · this computer"
    assert fs.scope_badge(False, tr) == "Project · shared"


def test_one_remote_layer_is_not_plural():
    fav = FilterFavorite(
        name="x", expression="1=1", layer_name="l",
        remote_layers={"ogr::batiment": {"feature_count": 3}},
    )
    assert dict(fs.summary_rows(fav, tr))["Then"].startswith("1 layer : ")
    assert dict(fs.summary_rows(_full(), tr))["Then"].startswith("2 layers : ")
