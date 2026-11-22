# -*- coding: utf-8 -*-
"""Palettes measured, not eyeballed (core/agent/palettes.py, 2026-11-22)."""
import pytest

from core.agent import palettes
from core.agent.palettes import PaletteError

pytestmark = pytest.mark.unit


def test_colours_go_to_oklab_and_back():
    for color in ("#2a78d6", "#000000", "#ffffff", "#e34948", "#00224e"):
        assert palettes.from_oklab(palettes.to_oklab(color)) == color
    assert palettes.delta_e("#2a78d6", "#2a78d6") == 0.0
    assert round(palettes.contrast("#ffffff", "#000000"), 1) == 21.0


def test_the_palette_of_filtermate_measures_as_its_charter_says():
    checked = palettes.validate(list(palettes.PALETTES["filtermate"].colors), "categorical")
    assert checked["min_delta_e_cvd"] == pytest.approx(9.1, abs=0.2) and checked["min_delta_e"] >= 19
    assert checked["problems"] == []


def test_a_palette_some_readers_cannot_read_is_told():
    checked = palettes.validate(list(palettes.PALETTES["set2"].colors), "categorical")
    assert any("protan" in problem or "deutan" in problem for problem in checked["problems"])
    assert palettes.validate(list(palettes.PALETTES["okabe_ito"].colors), "categorical")["problems"] == []


def test_ramps_rise_evenly_and_turn_over_for_a_dark_map():
    light, chosen, _ = palettes.colors_for("sequential", 5, "blues")
    lightness = [palettes.to_oklab(color)[0] for color in light]
    assert all(b < a for a, b in zip(lightness, lightness[1:])) and chosen.name == "blues"
    dark, _, _ = palettes.colors_for("sequential", 5, "viridis", variant="dark")
    assert dark == palettes.colors_for("sequential", 5, "viridis")[0][::-1]
    diverging, _, _ = palettes.colors_for("diverging", 5, "rdbu", variant="dark")
    assert diverging[2] == palettes.DARK_NEUTRAL


def test_variants_change_the_colours_and_keep_their_hue():
    base, _, _ = palettes.colors_for("categorical", 4)
    for variant in ("print", "discreet"):
        made, _, _ = palettes.colors_for("categorical", 4, variant=variant)
        assert made != base
        assert abs(palettes.to_oklch(made[0])[2] - palettes.to_oklch(base[0])[2]) < 8
    dark, _, _ = palettes.colors_for("categorical", 3, "filtermate", variant="dark")
    assert dark == list(palettes.PALETTES["filtermate"].dark[:3])


def test_more_categories_than_colours_say_so():
    colors, _, note = palettes.colors_for("categorical", 10, "okabe_ito")
    assert len(colors) == 7 and "grey" in note


def test_thin_marks_against_the_background_are_measured():
    checked = palettes.validate(["#F0E442", "#0072B2"], "categorical", marks="line")
    assert checked["min_contrast"] < 1.5 and any("background" in problem for problem in checked["problems"])


def test_what_a_palette_refuses():
    with pytest.raises(PaletteError):
        palettes.palette("rainbow")
    with pytest.raises(PaletteError, match="sequential"):
        palettes.palette("set2", "sequential")
    with pytest.raises(PaletteError):
        palettes.colors_for("categorical", 3, variant="neon")
    with pytest.raises(PaletteError):
        palettes.hex_to_rgb("blue")


def test_every_palette_is_described_with_its_source_and_licence():
    rows = palettes.describe()
    assert {row["role"] for row in rows} == set(palettes.ROLES)
    assert all(row["source"] and row["licence"] for row in rows)
