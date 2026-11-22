# -*- coding: utf-8 -*-
"""Official styles of data producers (IGN's BD TOPO, OpenStreetMap), made into QGIS styles for data layers.

Plain Python, no QGIS. ``scripts/build_style_presets.py`` converts the MapLibre styles of the producers into QML files
(``resources/styles``) and a manifest; this module holds what both the script and the plugin need:

* the scale range of a web-mercator zoom range (the convention QGIS draws vector tiles with: the scale of zoom 0 is
  559 082 264 at the equator, a zoom level is shown from half a level before it to half a level after it);
* the expression a zoom of the style is computed with on a plain layer, from the scale of the map;
* the variants of a style, computed from its colours in OKLab: ``gris`` (desaturated and lighter, a discreet
  background) and ``sombre`` (for a dark background: lightness inverted, hues kept);
* which tables of a preset fit a layer: by the name of its table, or by its fields.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

Z0_SCALE = 559_082_264.0287178  # the scale of web-mercator zoom 0 at the equator (256 px tiles, 0.28 mm pixels)
# The zoom of the map on a plain layer, from its scale: what @vector_tile_zoom is on a vector tile layer.
ZOOM_EXPRESSION = f"log(2, {Z0_SCALE} / @map_scale)"
ZOOM_VARIABLES = ("@vector_tile_zoom", "@zoom_level")
VARIANTS = {
    "gris": "grey and lighter, a discreet background under other data",
    "sombre": "for a dark background: light lines and texts, dark areas, hues kept",
}
GEOMETRIES = ("point", "line", "polygon")
# A table fits a layer by its fields when the layer has this share of the fields that tell the table apart.
FIELD_SHARE = 0.6


def scale_of_zoom(zoom: float) -> float:
    """The scale denominator of a web-mercator zoom level."""
    return Z0_SCALE / (2.0 ** zoom)


def scale_range(min_zoom: int, max_zoom: int) -> Tuple[float, float]:
    """(minimum scale, maximum scale) of QGIS for the zoom levels ``min_zoom`` to ``max_zoom`` (both shown; -1: no
    bound): the minimum scale is the most zoomed out one (the largest denominator), 0 for no bound."""
    minimum = scale_of_zoom(min_zoom - 0.5) if min_zoom is not None and min_zoom > 0 else 0.0
    maximum = scale_of_zoom(max_zoom + 0.5) if max_zoom is not None and max_zoom >= 0 else 0.0
    return round(minimum), round(maximum)


def zoom_free(expression: str) -> str:
    """``expression`` with the zoom of a vector tile layer computed from the scale of the map instead."""
    for variable in ZOOM_VARIABLES:
        expression = re.sub(re.escape(variable) + r"\b", f"({ZOOM_EXPRESSION})", expression)
    return expression


# ---------------------------------------------------------------------------------------------------------------------
# Colours, in OKLab (Björn Ottosson, 2020): a lightness that reads as the eye sees it, hues that stay hues.
# ---------------------------------------------------------------------------------------------------------------------

def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _gamma(channel: float) -> float:
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def to_oklab(red: int, green: int, blue: int) -> Tuple[float, float, float]:
    """OKLab (L 0-1, a, b) of an sRGB colour (0-255)."""
    r, g, b = (_linear(value / 255.0) for value in (red, green, blue))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def _from_oklab_linear(lightness: float, a: float, b: float) -> Tuple[float, float, float]:
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def from_oklab(lightness: float, a: float, b: float) -> Tuple[int, int, int]:
    """The sRGB colour (0-255) of an OKLab colour; out of gauge, its chroma is reduced until it fits (hue and
    lightness kept)."""
    lightness = min(1.0, max(0.0, lightness))
    low, high = 0.0, 1.0
    linear = _from_oklab_linear(lightness, a, b)
    if any(channel < -1e-6 or channel > 1 + 1e-6 for channel in linear):
        for _ in range(24):  # bisect the share of the chroma kept
            middle = (low + high) / 2
            trial = _from_oklab_linear(lightness, a * middle, b * middle)
            if all(-1e-6 <= channel <= 1 + 1e-6 for channel in trial):
                low = middle
            else:
                high = middle
        linear = _from_oklab_linear(lightness, a * low, b * low)
    return tuple(int(round(255 * _gamma(min(1.0, max(0.0, channel))))) for channel in linear)  # type: ignore


def variant_rgb(red: int, green: int, blue: int, variant: str) -> Tuple[int, int, int]:
    """A colour of a style in its variant.

    ``gris``: a tenth of its chroma, its lightness raised into 0.35-0.95 (dark lines and texts become mid grey, pale
    areas stay pale). ``sombre``: lightness inverted into 0.10-0.92 (white areas become near black, black texts
    near white), hue and chroma kept as far as the gauge allows.

    Raises:
        ValueError: An unknown variant.
    """
    lightness, a, b = to_oklab(red, green, blue)
    if variant == "gris":
        return from_oklab(0.35 + 0.60 * lightness, a * 0.1, b * 0.1)
    if variant == "sombre":
        return from_oklab(0.10 + 0.82 * (1.0 - lightness), a, b)
    raise ValueError(f"variant is one of {', '.join(VARIANTS)}")


_HEX = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")
_QGIS_COLOR = re.compile(r"\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(\d{1,3})\s*)?(?:,.*)?$")


def recolor(text: str, variant: str) -> Optional[str]:
    """A colour as QGIS writes it (``r,g,b,a``, with or without the ``rgb:`` part of QGIS 3.40+, or ``#rrggbb``) in
    ``variant``, written ``r,g,b,a`` (read by every QGIS since 3.0); None when ``text`` is not a colour."""
    found = _HEX.match(text.strip())
    if found:
        value = found.group(1)
        red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        alpha = int(found.group(2), 16) if found.group(2) else 255
    else:
        found = _QGIS_COLOR.match(text)
        if not found:
            return None
        red, green, blue = (int(found.group(index)) for index in (1, 2, 3))
        alpha = int(found.group(4)) if found.group(4) is not None else 255
        if max(red, green, blue, alpha) > 255:
            return None
    red, green, blue = variant_rgb(red, green, blue, variant)
    return f"{red},{green},{blue},{alpha}"


_RGBA_CALL = re.compile(r"\bcolor_rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(,\s*[\d.]+\s*)?\)", re.I)
_QUOTED = re.compile(r"'(#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?|\d{1,3},\d{1,3},\d{1,3}(?:,\d{1,3})?)'")


def recolor_expression(expression: str, variant: str) -> str:
    """The colours written in an expression of a colour (``color_rgba(r, g, b, a)``, ``'#rrggbb'``, ``'r,g,b,a'``)
    in ``variant``; the rest as it is (``@symbol_color`` follows the colour of the symbol by itself)."""
    def call(found):
        red, green, blue = variant_rgb(*(min(255, int(found.group(index))) for index in (1, 2, 3)), variant)
        alpha = found.group(4) or ""
        name = "color_rgba" if alpha else "color_rgb"
        return f"{name}({red},{green},{blue}{alpha})"

    def quoted(found):
        changed = recolor(found.group(1), variant)
        return f"'{changed}'" if changed else found.group(0)
    return _QUOTED.sub(quoted, _RGBA_CALL.sub(call, expression))


# ---------------------------------------------------------------------------------------------------------------------
# Which table of a preset a layer is.
# ---------------------------------------------------------------------------------------------------------------------

def normalized(name: str) -> str:
    """A name of layer or table as compared: lower case, no accents, words joined by ``_``."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def names_table(names: Iterable[str], table: str) -> bool:
    """Whether one of ``names`` (a layer name, the table of its source) is ``table``: the same, or ending with it
    after a ``_`` (``BDTOPO_V3:batiment``, ``bdtopo_batiment``), or a name the table starts (``batiment_31``)."""
    for name in names:
        text = normalized(name)
        if text and (text == table or text.endswith("_" + table) or re.fullmatch(re.escape(table) + r"_\d+", text)):
            return True
    return False


def missing_fields(required: Sequence[str], fields: Iterable[str]) -> List[str]:
    """The required fields a layer lacks, compared whatever their case (QGIS finds a field so in an expression)."""
    present = {str(field).casefold() for field in fields}
    return [field for field in required if field.casefold() not in present]


def fit(table: str, entry: Mapping[str, Any], names: Sequence[str], fields: Sequence[str],
        geometry: str) -> Optional[Tuple[int, float, int]]:
    """How well the table ``table`` of a preset fits a layer, as a key to sort by (best last); None when it does not.

    A layer fits when its geometry is that of the table, it has every field the style reads, and either it is named
    as the table (its name or the table of its source), or the style reads a field that tells the table apart
    (``usage_1``: a building of the BD TOPO; ``highway``: roads of OpenStreetMap), or the layer has most of those
    fields, or the style reads two fields or more of it.
    """
    if geometry and entry.get("geometry") and geometry != entry["geometry"]:
        return None
    required = list(entry.get("required") or ())
    if missing_fields(required, fields):
        return None
    named = names_table(names, table) if entry.get("by_name", True) else False
    signature = [field.casefold() for field in entry.get("fields") or ()]
    present = {str(field).casefold() for field in fields}
    share = (sum(1 for field in signature if field in present) / len(signature)) if signature else 0.0
    distinctive = any(field.casefold() in signature for field in required)
    if not (named or distinctive or share >= FIELD_SHARE or len(required) >= 2):
        return None
    return int(named), share, len(required)


def fitting(presets: Mapping[str, Mapping[str, Any]], names: Sequence[str], fields: Sequence[str],
            geometry: str) -> List[Tuple[str, str]]:
    """(preset id, table) of every table of ``presets`` that fits a layer, best first."""
    found = []
    for preset_id, preset in presets.items():
        for table, entry in (preset.get("tables") or {}).items():
            key = fit(table, entry, names, fields, geometry)
            if key is not None:
                found.append((key, preset_id, table))
    found.sort(key=lambda row: (-row[0][0], -row[0][1], -row[0][2], row[1], row[2]))
    return [(preset_id, table) for _key, preset_id, table in found]


def scale_words(scale: float) -> str:
    """``1:34,124`` for a scale denominator."""
    return f"1:{int(round(scale)):,}"
