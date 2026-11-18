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
WEB_ONLY = ("box-shadow", "text-shadow", "transform", "transition", "animation", "cursor", "text-overflow",
            "overflow", "overflow-x", "overflow-y", "display", "flex", "gap", "opacity", "filter",
            "pointer-events", "user-select", "line-height", "letter-spacing", "text-transform")


def _declarations(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    for body in re.findall(r"\{([^{}]*)\}", text):
        for declaration in body.split(";"):
            name = declaration.split(":", 1)[0].strip().lower()
            if declaration.strip() and ":" in declaration:
                yield name


@pytest.mark.unit
@pytest.mark.parametrize("path", sorted(STYLES.glob("*.qss")), ids=lambda path: path.name)
def test_style_sheet_has_no_web_only_property(path):
    used = sorted({name for name in _declarations(path.read_text(encoding="utf-8")) if name in WEB_ONLY})
    assert not used, f"{path.name} uses properties Qt does not know: {used}"
