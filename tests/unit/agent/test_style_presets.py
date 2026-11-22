# -*- coding: utf-8 -*-
"""Official styles made into QGIS styles: scales, variants, which table a layer is (core/agent/style_presets.py,
2026-11-22)."""
import json
import math
import os

import pytest

from core.agent import style_presets as presets

pytestmark = pytest.mark.unit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MANIFEST = os.path.join(ROOT, "resources", "styles", "manifest.json")


def test_a_zoom_range_is_the_scale_range_qgis_draws_its_tiles_with():
    minimum, maximum = presets.scale_range(14, -1)
    assert maximum == 0 and 45_000 < minimum < 50_000  # zoom 14 is 1:34,124, shown from zoom 13.5
    assert presets.scale_range(-1, -1) == (0, 0)
    minimum, maximum = presets.scale_range(2, 11)
    assert minimum > maximum > 0 and round(presets.scale_of_zoom(11.5)) == maximum


def test_the_zoom_of_a_tile_is_computed_from_the_scale_on_a_plain_layer():
    text = presets.zoom_free("scale_linear(@vector_tile_zoom,7,8,0,25.5) + @zoom_level")
    assert "@vector_tile_zoom" not in text and "@zoom_level" not in text and text.count("@map_scale") == 2


def test_oklab_round_trips_and_keeps_white_and_black():
    for colour in ((255, 255, 255), (0, 0, 0), (255, 109, 238), (39, 177, 62), (80, 104, 210)):
        assert all(abs(a - b) <= 1 for a, b in zip(presets.from_oklab(*presets.to_oklab(*colour)), colour))
    assert presets.to_oklab(255, 255, 255)[0] == pytest.approx(1.0, abs=1e-3)


def test_grey_is_grey_and_light_and_dark_is_inverted_with_its_hue():
    red, green, blue = presets.variant_rgb(39, 177, 62, "gris")
    assert max(red, green, blue) - min(red, green, blue) < 20
    assert presets.to_oklab(*presets.variant_rgb(0, 0, 0, "gris"))[0] == pytest.approx(0.35, abs=0.01)
    assert presets.to_oklab(*presets.variant_rgb(255, 255, 255, "sombre"))[0] < 0.15
    assert presets.to_oklab(*presets.variant_rgb(0, 0, 0, "sombre"))[0] > 0.9
    lightness, a, b = presets.to_oklab(80, 104, 210)  # the blue of a motorway of the BD TOPO
    _, a2, b2 = presets.to_oklab(*presets.variant_rgb(80, 104, 210, "sombre"))
    assert abs(math.atan2(b, a) - math.atan2(b2, a2)) < 0.1
    with pytest.raises(ValueError):
        presets.variant_rgb(1, 2, 3, "sepia")


def test_colours_as_qgis_writes_them_are_rewritten_plain():
    assert presets.recolor("255,255,255,255,rgb:1,1,1,1", "sombre").endswith(",255")
    assert presets.recolor("255,255,255,128", "gris").endswith(",128")
    assert presets.recolor("#ffffff", "gris") == presets.recolor("255,255,255,255", "gris")
    assert presets.recolor("solid", "gris") is None and presets.recolor("0,0,0,999", "gris") is None
    text = presets.recolor_expression("CASE WHEN x THEN color_rgba(255,0,0,128) ELSE '#ffffff' END", "sombre")
    assert "color_rgba(" in text and ",128)" in text and "#ffffff" not in text
    assert presets.recolor_expression("set_color_part(@symbol_color, 'alpha', 3)", "gris") == \
        "set_color_part(@symbol_color, 'alpha', 3)"


def test_a_table_is_named_by_its_layer_or_its_source():
    assert presets.names_table(["BDTOPO_V3:batiment"], "batiment")
    assert presets.names_table(["Bâtiment"], "batiment") and presets.names_table(["batiment_31"], "batiment")
    assert not presets.names_table(["batiments_remarquables"], "batiment")


def test_a_layer_fits_by_its_name_or_its_fields_never_without_the_fields_read():
    entry = {"geometry": "polygon", "required": ["usage_1"], "fields": ["usage_1", "nature", "hauteur", "etat"]}
    assert presets.fit("batiment", entry, ["batiment"], ["usage_1"], "polygon")
    assert presets.fit("batiment", entry, ["batiment"], ["nature"], "polygon") is None  # usage_1 missing
    assert presets.fit("batiment", entry, ["batiment"], ["usage_1"], "line") is None
    # usage_1 is read by the style and tells a building apart: enough, whatever the name.
    assert presets.fit("batiment", entry, ["mes données"], ["USAGE_1", "NATURE", "hauteur"], "polygon")
    roads = {"geometry": "line", "required": ["nature"], "fields": ["importance", "nombre_de_voies", "sens"]}
    assert presets.fit("troncon_de_route", roads, ["chemins"], ["nature"], "line") is None  # nature: any table
    assert presets.fit("troncon_de_route", roads, ["chemins"], ["nature", "importance", "sens"], "line")
    two = {"geometry": "polygon", "required": ["nature", "usage_1"]}
    assert presets.fit("batiment", two, ["x"], ["nature", "usage_1"], "polygon")


@pytest.mark.skipif(not os.path.exists(MANIFEST), reason="no manifest")
def test_the_manifest_holds_the_four_bd_topo_styles_and_an_osm_style_with_their_files():
    with open(MANIFEST, encoding="utf-8") as stream:
        manifest = json.load(stream)
    styles = manifest["presets"]
    for name in ("classique", "routier", "bati", "hydrographie"):
        assert f"ign/bdtopo/{name}" in styles
    assert any(key.startswith("osm/") for key in styles)
    for preset in styles.values():
        assert preset["licence"] and preset["attribution"] and preset["source"].startswith("https://")
        for table, entry in preset["tables"].items():
            assert entry["geometry"] in presets.GEOMETRIES
            assert os.path.exists(os.path.join(ROOT, "resources", "styles", entry["file"])), entry["file"]
    rows = presets.fitting(styles, ["batiment"], ["nature", "usage_1", "hauteur"], "polygon")
    assert ("ign/bdtopo/classique", "batiment") in rows
    rows = presets.fitting(styles, ["OSM highway (lines)"], ["osm_id", "name", "highway"], "line")
    assert rows and rows[0][0].startswith("osm/")
