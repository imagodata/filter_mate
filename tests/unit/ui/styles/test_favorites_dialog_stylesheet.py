# -*- coding: utf-8 -*-
"""Tests of the favorites manager stylesheet (theme tokens) and of its source (no emoji)."""

from __future__ import annotations

import re
from pathlib import Path

from ui.styles.favorites_styles import favorites_dialog_stylesheet
from ui.styles.mockup_design import TOKENS

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
_DIALOG_SOURCE = Path(__file__).resolve().parents[4] / "ui" / "dialogs" / "favorites_manager.py"
_EMOJI = "🔍 💾 🗑 📡 📤 👥 🌐 🔒 👤 🏷 ★ •".split()


def test_dark_and_light_differ():
    dark = favorites_dialog_stylesheet(True)
    light = favorites_dialog_stylesheet(False)
    assert dark != light
    assert TOKENS["dark"]["fm_bg"] in dark
    assert TOKENS["dark"]["fm_text"] in dark
    assert TOKENS["light"]["fm_bg"] in light


def test_no_literal_of_its_own():
    for name, dark in (("dark", True), ("light", False)):
        sheet = favorites_dialog_stylesheet(dark)
        allowed = {v.lower() for v in TOKENS[name].values()}
        found = {c.lower() for c in _HEX.findall(sheet)}
        assert found, "the stylesheet uses no color at all"
        assert found <= allowed, f"{name}: literals outside TOKENS: {sorted(found - allowed)}"
        assert "{fm_" not in sheet, "an unreplaced token placeholder is left"


def test_dialog_source_has_no_emoji():
    source = _DIALOG_SOURCE.read_text(encoding="utf-8")
    present = [e for e in _EMOJI if e in source]
    assert not present, f"emoji left in favorites_manager.py: {present}"
