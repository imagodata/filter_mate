# -*- coding: utf-8 -*-
"""
Website contrast + theme-switch regression tests.

The feedback forms (Tally embeds with a transparent background) were
unreadable in dark mode, and several site-wide colours failed WCAG AA:
``--select-deep`` (#e0b400) and ``--rule`` (used for ``.step-number``) on a
light background. The site also had no manual theme switch.

These tests parse ``website/assets/fm.css`` variables and resolve the
foreground/background pairs the design actually uses, then check their
contrast ratios -- plus the JS/CSS wiring of the theme switch and the
Tally ``theme=`` parameter. stdlib only, no browser needed.
"""
import re
from pathlib import Path

import pytest

WEBSITE = Path(__file__).resolve().parent.parent / "website" / "assets"
CSS = (WEBSITE / "fm.css").read_text(encoding="utf-8")
FM_JS = (WEBSITE / "fm.js").read_text(encoding="utf-8")
FM_FORMS_JS = (WEBSITE / "fm-forms.js").read_text(encoding="utf-8")


def _block_vars(css, selector_pattern):
    """Return {var: value} for the first block matching selector_pattern."""
    match = re.search(selector_pattern + r"\s*\{([^}]*)\}", css)
    assert match, f"CSS block not found: {selector_pattern}"
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", match.group(1)))


def _resolve(value, variables):
    """Resolve one level of var(--x) references."""
    def _sub(match):
        return variables.get(match.group(1), match.group(0)).strip()
    return re.sub(r"var\(--([\w-]+)\)", _sub, value).strip()


def _channel(value):
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_color):
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def ratio(foreground, background):
    """WCAG contrast ratio of two #hex colours."""
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


LIGHT = _block_vars(CSS, r":root")
DARK = _block_vars(CSS, r":root\[data-theme=\"dark\"\]")

def _value(variables, name):
    """Resolve ``name`` (e.g. ``--text``) through one level of var() references."""
    key = name[2:] if name.startswith("--") else name
    return _resolve(variables[key].strip(), variables)


# (foreground variable, background variable, minimum ratio)
LIGHT_PAIRS = [
    ("--text", "--bg", 4.5),  # body text
    ("--text-2", "--bg", 4.5),  # secondary text, step numbers
    ("--link", "--bg", 4.5),  # links on page background
    ("--link", "--bg-2", 4.5),  # links on cards
    ("--qgis", "--bg", 4.5),  # section labels and kickers
    ("--select-deep", "--bg", 4.5),  # install counters, h2 numbers
    ("--icon-purple", "--bg", 4.5),  # roadmap feature icons
    ("--ink", "--select", 4.5),  # ink text on the yellow brand colour
    ("--on-ink", "--ink", 4.5),  # text over footage scrims
    ("--on-ink-2", "--ink", 4.5),  # secondary text over footage scrims
]
DARK_PAIRS = [
    ("--text", "--bg", 4.5),
    ("--text-2", "--bg", 4.5),
    ("--link", "--bg", 4.5),
    ("--qgis", "--bg", 4.5),
    ("--select-deep", "--bg", 4.5),
    ("--on-ink", "--ink", 4.5),
    ("--ink", "--select", 4.5),
]
# 36 px decorative SVG icons: WCAG non-text minimum is 3:1.
DARK_LARGE_GRAPHICS = [("--icon-purple", "--bg", 3.0)]


@pytest.mark.unit
@pytest.mark.parametrize("fg,bg,minimum", LIGHT_PAIRS)
def test_light_theme_contrast(fg, bg, minimum):
    fg_value, bg_value = _value(LIGHT, fg), _value(LIGHT, bg)
    assert ratio(fg_value, bg_value) >= minimum, f"{fg} on {bg}: {fg_value}/{bg_value}"


@pytest.mark.unit
@pytest.mark.parametrize("fg,bg,minimum", DARK_PAIRS + DARK_LARGE_GRAPHICS)
def test_dark_theme_contrast(fg, bg, minimum):
    merged = dict(LIGHT)
    merged.update(DARK)  # dark overrides win, the rest inherits light values
    fg_value, bg_value = _value(merged, fg), _value(merged, bg)
    assert ratio(fg_value, bg_value) >= minimum, f"dark {fg} on {bg}: {fg_value}/{bg_value}"


@pytest.mark.unit
def test_select_deep_has_per_theme_value():
    """The yellow accent cannot serve both themes: it must be dark on paper."""
    assert LIGHT["select-deep"].strip() != DARK["select-deep"].strip()
    assert ratio(_value(LIGHT, "--select-deep"), _value(LIGHT, "--bg")) >= 4.5


@pytest.mark.unit
def test_step_number_does_not_use_rule_colour():
    """``.step-number`` used ``--rule`` (≈1.4:1); it must use readable text."""
    match = re.search(r"\.step-number\s*\{([^}]*)\}", CSS)
    assert match and "var(--text-2)" in match.group(1)


@pytest.mark.unit
def test_tally_embeds_carry_site_theme():
    """Feedback forms: the embed URL sets theme= and the box keeps its colour."""
    assert "theme=' + theme" in FM_FORMS_JS or 'theme=" + theme' in FM_FORMS_JS \
        or "&theme=' + theme" in FM_FORMS_JS
    assert "data-tally-theme" in FM_FORMS_JS
    assert ".cloud-form[data-tally-theme" in CSS


@pytest.mark.unit
def test_theme_switch_wiring():
    """Nav switch: persisted choice, data-theme, no reload of answered forms."""
    assert "filtermate-theme" in FM_JS  # localStorage key
    assert "dataset.theme" in FM_JS  # drives CSS + footage + forms
    assert "theme-toggle" in FM_JS and ".theme-toggle" in CSS
    assert "aria-pressed" in FM_JS
    assert "prefers-color-scheme" in FM_JS  # OS fallback
    # Loaded Tally iframes keep their src (switching never wipes an answer).
    assert "if (!frame.getAttribute('src'))" in FM_JS
