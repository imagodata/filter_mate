# -*- coding: utf-8 -*-
"""design_style: a finished style for a vector layer, made from a validated palette, and list_palettes.

Main thread only, plain dicts out. Where set_layer_style draws what it is told, design_style composes: the colours of
a palette by the job they do (``core/agent/palettes.py``), checked for the readers who see colours differently, one
symbol or categories or classes, a look per kind of geometry (a polygon flat, outlined or hatched; a line with a
casing like a road, a halo or dashes; a point as a dot, an icon of the SVG library of QGIS in the colour of its
category, or an icon on a badge), in the variant of the map it goes on (light, dark, print, discreet). Undone with the
turn like set_layer_style (its style XML: Symbology, Labeling, Rendering).
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from ...core.agent import palettes as palette_engine
from .layer_style import _geometry, _layer, _read_values_guard, _refresh

logger = logging.getLogger("FilterMate.agent")

MODES = ("single", "categorized", "graduated")
LOOKS = {"polygon": ("flat", "outlined", "hatched"), "line": ("flat", "casing", "halo", "dashed"),
         "point": ("flat", "icon", "badge")}
METHODS = ("quantile", "equal_interval", "jenks", "pretty")
DEFAULT_LIMIT, MAX_LIMIT = 8, 12
MAX_CLASSES = 9
LINE_WIDTH, POINT_SIZE = 0.66, 3.2  # millimetres
MAX_ICONS_LISTED = 12


def _mm():
    from qgis.core import Qgis, QgsUnitTypes
    unit = getattr(getattr(Qgis, "RenderUnit", None), "Millimeters", None)
    return unit if unit is not None else QgsUnitTypes.RenderMillimeters


def _qcolor(text: str, alpha: float = 1.0):
    from qgis.PyQt.QtGui import QColor
    color = QColor(text)
    color.setAlphaF(max(0.0, min(1.0, alpha)))
    return color


def _qt(scope: str, name: str):
    """A member of a Qt enum: in its scope (Qt 6) or on Qt (Qt 5)."""
    from qgis.PyQt.QtCore import Qt
    return getattr(getattr(Qt, scope, Qt), name)


# --- the icons of the SVG library of QGIS --------------------------------------------------------------------------

def _svg_files() -> List[str]:
    from qgis.core import QgsApplication
    found = []
    for folder in QgsApplication.svgPaths():
        for root, _, files in os.walk(folder):
            found.extend(os.path.join(root, name) for name in files if name.lower().endswith(".svg"))
    return found


def find_icon(keyword: str) -> str:
    """The SVG of the library of QGIS whose name holds ``keyword`` (fill colour as a parameter first)."""
    words = [word for word in str(keyword or "").lower().replace("-", " ").replace("_", " ").split() if word]
    if not words:
        raise ValueError("icon is a word of the name of an SVG of QGIS: school, hospital, tree, bus...")
    matches = [path for path in _svg_files()
               if all(word in os.path.basename(path).lower().replace("_", " ") for word in words)]
    if not matches:
        sample = sorted({os.path.splitext(os.path.basename(path))[0] for path in _svg_files()})[:MAX_ICONS_LISTED]
        raise ValueError(f"no icon named like {keyword!r} in the SVG library of QGIS; some are: {', '.join(sample)}")

    def colourable(path: str) -> bool:
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                return "param(fill)" in handle.read()
        except OSError:
            return False

    matches.sort(key=lambda path: (not colourable(path), len(os.path.basename(path))))
    return matches[0]


# --- symbols -------------------------------------------------------------------------------------------------------

MIN_LINE_CONTRAST = 1.8  # a thin line or a hatch against the background of the map


def legible(color: str, background: str) -> str:
    """``color`` for a thin mark: its own hue, darker on a light map (lighter on a dark one) until it stands out of
    the background (the yellow of Okabe and Ito as hatches on white: contrast 1.32)."""
    if palette_engine.contrast(color, background) >= MIN_LINE_CONTRAST:
        return color
    lightness, chroma, hue = palette_engine.to_oklch(color)
    darker = palette_engine.to_oklab(background)[0] > 0.5
    for _ in range(40):
        lightness += -0.03 if darker else 0.03
        candidate = palette_engine.from_oklch(max(0.0, min(1.0, lightness)), chroma, hue)
        if palette_engine.contrast(candidate, background) >= MIN_LINE_CONTRAST:
            return candidate
    return candidate


def _symbol(geometry: str, look: str, color: str, variant: str, icon: str = "", size: Optional[float] = None):
    """A symbol of ``look`` in ``color``; a line of two parts (casing, halo) draws its under part on pass 0."""
    from qgis import core
    background = palette_engine.DARK_BACKGROUND if variant == "dark" else palette_engine.LIGHT_BACKGROUND
    edge = palette_engine.outline_of(color, variant)
    thin = legible(color, background)  # what a hatch or a single thin line is drawn in
    if geometry == "polygon":
        symbol = core.QgsFillSymbol()
        symbol.deleteSymbolLayer(0)
        if look == "hatched":
            hatch = core.QgsLinePatternFillSymbolLayer()
            hatch.setLineAngle(45.0)
            hatch.setDistance(1.6)
            hatch.setDistanceUnit(_mm())
            hatch.setColor(_qcolor(thin))
            if hatch.subSymbol() is not None:
                hatch.subSymbol().setWidth(0.3)
                hatch.subSymbol().setColor(_qcolor(thin))
            symbol.appendSymbolLayer(hatch)
            outline = core.QgsSimpleFillSymbolLayer()
            outline.setBrushStyle(_qt("BrushStyle", "NoBrush"))
            outline.setStrokeColor(_qcolor(thin))
            outline.setStrokeWidth(0.4)
            symbol.appendSymbolLayer(outline)
            return symbol
        fill = core.QgsSimpleFillSymbolLayer()
        if look == "outlined":
            fill.setColor(_qcolor(palette_engine.tint_of(color, 0.55), 0.9))
            fill.setStrokeColor(_qcolor(color))
            fill.setStrokeWidth(0.6)
        else:
            fill.setColor(_qcolor(color))
            fill.setStrokeColor(_qcolor(edge, 0.8))
            fill.setStrokeWidth(0.2)
        fill.setStrokeWidthUnit(_mm())
        symbol.appendSymbolLayer(fill)
        return symbol
    if geometry == "line":
        width = size or LINE_WIDTH
        symbol = core.QgsLineSymbol()
        symbol.deleteSymbolLayer(0)
        if look in ("casing", "halo"):
            under = core.QgsSimpleLineSymbolLayer(_qcolor(edge if look == "casing" else background, 0.95),
                                                  width + (0.8 if look == "casing" else 1.2))
            under.setRenderingPass(0)
            under.setPenCapStyle(_qt("PenCapStyle", "RoundCap"))
            symbol.appendSymbolLayer(under)
        top = core.QgsSimpleLineSymbolLayer(_qcolor(palette_engine.tint_of(color, 0.25) if look == "casing"
                                                    else color if look == "halo" else thin), width)
        top.setRenderingPass(1)
        if look == "dashed":
            top.setPenStyle(_qt("PenStyle", "DashLine"))
        symbol.appendSymbolLayer(top)
        return symbol
    size = size or POINT_SIZE
    symbol = core.QgsMarkerSymbol()
    symbol.deleteSymbolLayer(0)
    if look in ("icon", "badge"):
        path = find_icon(icon or "")
        if look == "badge":
            dot = core.QgsSimpleMarkerSymbolLayer()
            dot.setSize(size * 1.6)
            dot.setColor(_qcolor(color))
            dot.setStrokeColor(_qcolor(background))
            dot.setStrokeWidth(0.3)
            symbol.appendSymbolLayer(dot)
        svg = core.QgsSvgMarkerSymbolLayer(path, size * (1.0 if look == "badge" else 1.4))
        svg.setFillColor(_qcolor(background if look == "badge" else color))
        svg.setStrokeColor(_qcolor(edge if look == "icon" else background))
        svg.setStrokeWidth(0.0)
        symbol.appendSymbolLayer(svg)
        return symbol
    dot = core.QgsSimpleMarkerSymbolLayer()
    dot.setSize(size)
    dot.setColor(_qcolor(color))
    dot.setStrokeColor(_qcolor(background))  # a ring of the background: dots that overlap stay apart
    dot.setStrokeWidth(0.4)
    symbol.appendSymbolLayer(dot)
    return symbol


# --- values --------------------------------------------------------------------------------------------------------

def _plain(value: Any) -> Any:
    if value is None or (hasattr(value, "isNull") and callable(value.isNull) and value.isNull()):
        return None
    return value


def _category_values(layer, index: int, limit: int) -> Tuple[List[Any], bool]:
    """The values to give a colour (``limit`` at most: the most frequent), in a stable order (sorted: a filter that
    takes one away does not repaint the others), and whether others are left for the grey of the rest."""
    from .introspection import MAX_STAT_FEATURES
    values = [_plain(value) for value in layer.uniqueValues(index, limit + 1)]
    values = [value for value in values if value is not None]
    if not values:
        raise ValueError("the field has no value to make categories from")
    others = len(values) > limit
    if others:  # which ones are the most frequent: one pass, within the reads of layer_statistics
        from qgis.core import QgsFeatureRequest
        counts: Dict[Any, int] = {}
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setSubsetOfAttributes([index]) \
            .setLimit(MAX_STAT_FEATURES)
        for feature in layer.getFeatures(request):
            value = _plain(feature.attribute(index))
            if value is not None:
                counts[value] = counts.get(value, 0) + 1
        values = [value for value, _ in sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[:limit]]
    values.sort(key=lambda value: (isinstance(value, str), value if isinstance(value, (int, float)) else str(value)))
    return values, others


# --- the tool ------------------------------------------------------------------------------------------------------

def design_style(layer: str, mode: str = "single", field: str = "", palette: str = "", look: str = "flat",
                 icon: str = "", variant: str = "light", classes: int = 5, method: str = "quantile",
                 limit: int = DEFAULT_LIMIT, reverse: bool = False, size: Optional[float] = None,
                 opacity: Optional[float] = None, color: str = "") -> Dict[str, Any]:
    """Compose a style for a vector layer from a validated palette; what was made and what the palette check says.

    Raises:
        ValueError: An unknown layer, mode, look, palette, icon or field, a field with nothing to show.
    """
    from qgis import core
    found = _layer(layer)
    if not isinstance(found, core.QgsVectorLayer):
        raise ValueError(f"'{found.name()}' is not a vector layer: design_style draws vectors")
    geometry = _geometry(found)
    if not geometry:
        raise ValueError(f"'{found.name()}' has no geometry to draw")
    if mode not in MODES:
        raise ValueError(f"mode is one of {', '.join(MODES)}")
    if look not in LOOKS[geometry]:
        raise ValueError(f"a {geometry} layer takes the looks {', '.join(LOOKS[geometry])}")
    if look in ("icon", "badge") and not icon:
        raise ValueError("look icon or badge needs icon: a word of the name of an SVG of QGIS (school, tree, bus...)")
    if variant not in palette_engine.VARIANTS:
        raise ValueError(f"variant is one of {', '.join(palette_engine.VARIANTS)}")
    if not 1 <= int(limit) <= MAX_LIMIT:
        raise ValueError(f"limit goes from 1 to {MAX_LIMIT}")
    if not 2 <= int(classes) <= MAX_CLASSES:
        raise ValueError(f"classes goes from 2 to {MAX_CLASSES}")
    if method not in METHODS:
        raise ValueError(f"method is one of {', '.join(METHODS)}")
    if size is not None and not (isinstance(size, (int, float)) and math.isfinite(size) and 0 < size <= 20):
        raise ValueError("size goes up to 20 millimetres, above zero")
    if opacity is not None and not 0 <= float(opacity) <= 1:
        raise ValueError("opacity goes from 0 to 1")
    marks = "fill" if geometry == "polygon" and look != "hatched" else ("line" if geometry != "point" else "point")
    background = palette_engine.DARK_BACKGROUND if variant == "dark" else palette_engine.LIGHT_BACKGROUND
    note = ""
    try:
        if mode == "single":
            if color:
                colors = [palette_engine.from_oklab(palette_engine.to_oklab(color))]
                chosen = None
                role = "single"
            else:
                colors, chosen, _ = palette_engine.colors_for("categorical", 1, palette, variant)
                role = "categorical"
            renderer = core.QgsSingleSymbolRenderer(_symbol(geometry, look, colors[0], variant, icon, size))
            made = {"mode": mode}
        elif mode == "categorized":
            index = found.fields().lookupField(field or "")
            if index < 0:
                raise ValueError(f"'{found.name()}' has no field {field!r} (describe_layer lists them)")
            _read_values_guard(found, all_values=False)
            values, others = _category_values(found, index, int(limit))
            colors, chosen, note = palette_engine.colors_for("categorical", len(values), palette, variant, reverse)
            role = chosen.role
            colors = colors + [palette_engine.others_color(variant)] * (len(values) - len(colors))
            categories = [core.QgsRendererCategory(value, _symbol(geometry, look, tint, variant, icon, size),
                                                   str(value)) for value, tint in zip(values, colors)]
            if others:  # the rest, in one grey: a category of no value is "all the other values"
                categories.append(core.QgsRendererCategory("", _symbol(geometry, look,
                                                                       palette_engine.others_color(variant),
                                                                       variant, icon, size), "Others"))
            renderer = core.QgsCategorizedSymbolRenderer(found.fields().at(index).name(), categories)
            made = {"mode": mode, "field": found.fields().at(index).name(), "categories": len(values),
                    "others": others}
        else:
            index = found.fields().lookupField(field or "")
            if index < 0 or not found.fields().at(index).isNumeric():
                raise ValueError(f"'{field}' is no numeric field of '{found.name()}': graduated classes need numbers")
            _read_values_guard(found, all_values=True)
            chosen = palette_engine.palette(palette, "") if palette else palette_engine.palette("", "sequential")
            if chosen.role not in ("sequential", "diverging"):
                raise ValueError(f"{chosen.name} is {chosen.role}: graduated classes take a sequential or diverging "
                                 "palette (list_palettes)")
            role = chosen.role
            makers = {"quantile": "QgsClassificationQuantile", "equal_interval": "QgsClassificationEqualInterval",
                      "jenks": "QgsClassificationJenks", "pretty": "QgsClassificationPrettyBreaks"}
            renderer = core.QgsGraduatedSymbolRenderer(found.fields().at(index).name())
            renderer.setSourceSymbol(_symbol(geometry, look, "#888888", variant, icon, size))
            renderer.setClassificationMethod(getattr(core, makers[method])())
            renderer.updateClasses(found, int(classes))
            ranges = renderer.ranges()
            if not ranges:
                raise ValueError(f"'{field}' has no value to make classes from")
            colors, chosen, _ = palette_engine.colors_for(role, len(ranges), chosen.name, variant, reverse)
            for position, tint in enumerate(colors):
                renderer.updateRangeSymbol(position, _symbol(geometry, look, tint, variant, icon, size))
            made = {"mode": mode, "field": found.fields().at(index).name(), "classes": len(ranges),
                    "method": method}
    except palette_engine.PaletteError as exc:
        raise ValueError(str(exc)) from None
    if geometry == "line" and look in ("casing", "halo"):
        renderer.setUsingSymbolLevels(True)  # every casing under every line: roads join at crossings
    found.setRenderer(renderer)
    if opacity is not None:
        found.setOpacity(float(opacity))
    _refresh(found)
    # The colours of the palette only: the grey of the others, repeated when the palette is short, is no category.
    judged = [tint for tint in colors if tint != palette_engine.others_color(variant)] or colors
    thin_marks = (geometry == "polygon" and look == "hatched") or (geometry == "line" and look in ("flat", "dashed"))
    drawn = [legible(tint, background) for tint in judged] if thin_marks else judged
    checked = palette_engine.validate(drawn, role if role != "single" else "categorical", background, marks)
    answer: Dict[str, Any] = {"layer_name": found.name(), **made, "look": look, "variant": variant,
                              "palette": chosen.name if chosen is not None else "given color", "colors": colors}
    if chosen is not None and chosen.licence.startswith("Apache"):
        answer["credit"] = chosen.source
    if look in ("icon", "badge"):
        answer["icon"] = os.path.splitext(os.path.basename(find_icon(icon)))[0]
    if checked["problems"]:
        answer["problems"] = checked["problems"]
    if drawn != judged:
        darkened = "darker" if background == palette_engine.LIGHT_BACKGROUND else "lighter"
        changed = sum(a != b for a, b in zip(drawn, judged))
        note = (note + " " if note else "") + (f"{changed} colour(s) drawn {darkened} in their own hue so that thin "
                                               "lines stand out of the background")
    if note:
        answer["note"] = note
    return answer


def list_palettes(role: str = "") -> Dict[str, Any]:
    """The palettes of a role, or all, with their colours, source, licence and what the check of colours says."""
    if role and role not in palette_engine.ROLES:
        raise ValueError(f"role is one of {', '.join(palette_engine.ROLES)}")
    rows = palette_engine.describe(role)
    return {"palettes": [{"name": row["name"], "role": row["role"], "colors": row["colors"],
                          "source": row["source"], "licence": row["licence"],
                          "problems": row["checked"].get("problems", [])} for row in rows],
            "defaults": palette_engine.DEFAULT_PALETTE}
