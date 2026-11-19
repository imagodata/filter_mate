# -*- coding: utf-8 -*-
"""
2026-11-18: no style sheet of the plugin uses a property Qt does not know.

Qt prints "Unknown property box-shadow" for each widget the rule applies to, and QGIS 4.3 shows every such
message in its message bar (critical, tag "Qt"). ``box-shadow``, ``transform``, ``cursor``, ``text-overflow`` and
``overflow`` came from the web; Qt ignored them, so dropping them changes nothing on screen.
"""
import re
from pathlib import Path

import pytest

STYLES = Path(__file__).resolve().parents[2] / "resources" / "styles"
# Checked in QGIS 3.44 and 4.3 on a QPushButton: each of these prints "Unknown property" (opacity, line-height,
# letter-spacing and text-transform do not, so they are not listed).
WEB_ONLY = ("box-shadow", "text-shadow", "transform", "transition", "animation", "cursor", "text-overflow",
            "overflow", "overflow-x", "overflow-y", "display", "flex", "gap", "filter", "pointer-events",
            "user-select")


def _declarations(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"\{[A-Za-z_]\w*\}", "x", text)  # a placeholder of the template ({color_accent}) is no brace
    for body in re.findall(r"\{([^{}]*)\}", text):
        for declaration in body.split(";"):
            name = declaration.split(":", 1)[0].strip().lower()
            if declaration.strip() and ":" in declaration:
                yield name


@pytest.mark.unit
@pytest.mark.parametrize("path", sorted(STYLES.glob("*.qss")), ids=lambda path: path.name)
def test_style_sheet_has_no_web_only_property(path):
    """The rules with a placeholder count too (a test that skipped them saw 2 ``cursor`` of 6 and no ``box-shadow``)."""
    used = sorted({name for name in _declarations(path.read_text(encoding="utf-8")) if name in WEB_ONLY})
    assert not used, f"{path.name} uses properties Qt does not know: {used}"


@pytest.mark.unit
@pytest.mark.parametrize("name", WEB_ONLY)
def test_the_scan_finds_each_property_in_a_rule_with_a_placeholder(name):
    sheet = f"/* {name}: 1; */\n#dock QPushButton:hover {{\n    color: {{color_accent}};\n    {name}: 0 0 2px {{color_2}};\n}}"
    assert name in set(_declarations(sheet))
