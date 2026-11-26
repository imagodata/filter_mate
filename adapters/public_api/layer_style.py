# -*- coding: utf-8 -*-
"""How a layer is drawn, for the agent: one symbol, categories, classes, rules, proportional symbols, a heatmap,
clusters, dots, 2.5D blocks, a raster ramp or a hillshade, labels, opacity and blending.

Main thread only, plain dicts out. The answer gives how many classes were made, never the values they hold: the
attribute values stay out of what the model reads, as ``describe_layer`` does. The chat captures the style of the
layer before the first change of a turn (``adapters/agent/turn_effects.py``), so undoing the turn brings it back.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional

from ...core.agent.sql_guard import expression_problem, processing_expression_problem
from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.LayerStyle')

MAX_CATEGORIES = 100
MAX_CLASSES = 12
MAX_RAMPS_LISTED = 40
POINT_MODES = ('heatmap', 'point_cluster', 'point_displacement')  # for a layer of points alone
POLYGON_MODES = ('dot_density', '2.5d')  # for a layer of polygons alone
VECTOR_MODES = ('single', 'categorized', 'graduated', 'rules', 'proportional') + POINT_MODES + POLYGON_MODES
MAX_RULES = 20
RASTER_MODES = ('pseudocolor', 'gray', 'hillshade')
KEEP = 'keep'  # the drawing as it is: the opacity and the blending alone change
# How a layer mixes with what is drawn under it. multiply darkens (a hillshade over colors, colors over a
# photograph); screen lightens; overlay and soft_light keep the lights and the shadows of what is under.
BLENDS = {'normal': 'SourceOver', 'multiply': 'Multiply', 'screen': 'Screen', 'overlay': 'Overlay',
          'darken': 'Darken', 'lighten': 'Lighten', 'soft_light': 'SoftLight', 'hard_light': 'HardLight'}
MAX_WIDTH = 20.0  # millimetres: a line, an outline, the size of a point
MAX_CUT = 49.0  # percent of the values left out at each end of a raster stretch
# Where labels go, by the geometries each placement is for, and its name in QgsPalLayerSettings.Placement.
LABEL_PLACEMENTS = {'auto': ((), ''), 'curved': (('line',), 'Curved'), 'parallel': (('line',), 'Line'),
                    'horizontal': (('line', 'polygon'), 'Horizontal'), 'centroid': (('polygon',), 'OverPoint'),
                    'free': (('polygon',), 'Free'), 'around': (('point', 'polygon'), 'AroundPoint'),
                    'perimeter': (('polygon',), 'PerimeterCurved')}
# Ramps of FilterMate, beside those of QGIS: the first color, stops (where, color), the last color. Terrain is the
# hypsometric tints of a relief map, from the green of the low ground to the pale rock of the summits; the style of
# QGIS holds none that reads as heights.
# The summits are a pale rock, not white: stretched over the heights of one town, white reads as a haze over its
# hills (seen on Lyon, 2026-11-15).
OWN_RAMPS = {'terrain': ('Terrain', '#3f8f4f', ((0.2, '#a9cc7a'), (0.42, '#f3e7a9'), (0.64, '#d0a468'),
                                              (0.84, '#9a6b4c')), '#e3d5c2')}
_DEGREES_Z_FACTOR = 1.0 / 111_320.0  # heights in metres over a grid in degrees
METHODS = ('quantile', 'equal_interval', 'jenks', 'pretty', 'stddev')
DEFAULT_RAMPS = {'categorized': 'Spectral', 'graduated': 'Viridis', 'pseudocolor': 'Spectral', 'heatmap': 'YlOrRd'}
# Millimetres on the map, when the call gives no width: the radius of a heatmap, how close points are gathered, the
# largest proportional symbol (a line: its widest), a dot.
HEAT_RADIUS = 10.0
POINT_DISTANCE = 3.0
LARGEST_SYMBOL = 10.0
WIDEST_LINE = 4.0
DOT_SIZE = 0.6
DOTS_IN_LARGEST = 100  # dot_density with no per_dot: about this many dots in the polygon of the largest value
MAX_DOTS = 2000  # in one polygon: more freezes the drawing of each one
# The renderers a cluster or a displacement can keep for the points they leave apart, and the mode each one is.
KEPT_INSIDE = {'singleSymbol': 'single', 'categorizedSymbol': 'categorized', 'graduatedSymbol': 'graduated',
               'RuleRenderer': 'rules'}


def _layer(reference: str):
    """The project layer; ValueError when it is absent or its source could not be opened."""
    layer = resolve_layer(reference)
    if layer is None:
        raise ValueError(f"layer {reference!r} not found")
    if not layer.isValid():
        raise ValueError(f"'{layer.name()}' is not available: its data source could not be opened")
    return layer


def _color(text: str):
    from qgis.PyQt.QtGui import QColor
    color = QColor(str(text))
    if not text or not color.isValid():
        raise ValueError(f"{text!r} is not a color: give #rrggbb or a name such as red")
    return color


def _ramp(name: str, mode: str, invert: bool):
    from qgis.core import QgsStyle
    own = OWN_RAMPS.get((name or '').strip().casefold())
    if own is not None:
        from qgis.core import QgsGradientColorRamp, QgsGradientStop
        from qgis.PyQt.QtGui import QColor
        title, first, stops, last = own
        ramp = QgsGradientColorRamp(QColor(first), QColor(last), False,
                                    [QgsGradientStop(offset, QColor(color)) for offset, color in stops])
        if invert:
            ramp.invert()
        return ramp, title
    style = QgsStyle.defaultStyle()
    names = list(style.colorRampNames())
    wanted = name or DEFAULT_RAMPS.get(mode, 'Spectral')
    found = next((item for item in names if item.casefold() == wanted.casefold()), None)
    if found is None:
        if name:
            listed = sorted(names)[:MAX_RAMPS_LISTED] + [title for title, *_ in OWN_RAMPS.values()]
            raise ValueError(f"no color ramp {name!r}; some are: {', '.join(listed)}")
        found = names[0] if names else None
    ramp = style.colorRamp(found) if found else None
    if ramp is None:
        from qgis.core import QgsGradientColorRamp
        from qgis.PyQt.QtGui import QColor
        ramp, found = QgsGradientColorRamp(QColor('#fde725'), QColor('#440154')), 'gradient'
    if invert:
        ramp.invert()
    return ramp, found


def _field_index(layer, field: str, numeric: bool = False,
                 need: str = 'graduated classes need numbers, use categorized') -> int:
    index = layer.fields().lookupField(field or '')
    if index < 0:
        raise ValueError(f"'{layer.name()}' has no field {field!r} (describe_layer lists them)")
    if numeric and not layer.fields().at(index).isNumeric():
        raise ValueError(f"'{field}' is not a numeric field: {need}")
    return index


def _field_name(layer, field: str) -> str:
    """The name of ``field`` as the layer spells it; "" for none."""
    return layer.fields().at(_field_index(layer, field)).name() if field else ''


def _geometry(layer) -> str:
    """point, line or polygon; "" for a table."""
    from qgis.core import QgsWkbTypes
    kind = QgsWkbTypes.geometryType(layer.wkbType())
    types = QgsWkbTypes.GeometryType
    for name, member in (('point', types.PointGeometry), ('line', types.LineGeometry),
                         ('polygon', types.PolygonGeometry)):
        if kind == member:
            return name
    return ''


def _enum(owner, scope: str, name: str, legacy: str = ''):
    """A member of an enum of QGIS, reached through its scope (QGIS 4) or on its class (QGIS 3), where it may have
    another name (``legacy``: PropertyPointCount in 3.22)."""
    member = getattr(getattr(owner, scope, None), name, None)
    return member if member is not None else getattr(owner, legacy or name)


def _millimetres():
    from qgis.core import Qgis, QgsUnitTypes
    unit = getattr(getattr(Qgis, 'RenderUnit', None), 'Millimeters', None)
    return unit if unit is not None else QgsUnitTypes.RenderUnit.RenderMillimeters


def _width(value: Any) -> Optional[float]:
    """A width in millimetres a model gave; None when it gave none."""
    if value is None:
        return None
    try:
        width = float(value)
    except (TypeError, ValueError):
        raise ValueError('width is a number of millimetres') from None
    if not math.isfinite(width) or not 0 < width <= MAX_WIDTH:
        raise ValueError(f'width goes up to {MAX_WIDTH:g} millimetres, above zero')
    return width


def _symbol(layer, color=None, width: Optional[float] = None):
    """The default symbol of the geometry of ``layer``, in ``color``; ``width`` (millimetres) is the width of a
    line, of the outline of a polygon, or the size of a point."""
    from qgis.core import QgsSymbol
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    if symbol is None:
        raise ValueError(f"'{layer.name()}' has no geometry to draw")
    if color is not None:
        symbol.setColor(color)
    if width is not None:
        if hasattr(symbol, 'setWidth'):  # a line
            symbol.setWidth(width)
        elif hasattr(symbol, 'setSize'):  # a point
            symbol.setSize(width)
        else:  # a polygon: its outline
            for index in range(symbol.symbolLayerCount()):
                part = symbol.symbolLayer(index)
                if hasattr(part, 'setStrokeWidth'):
                    part.setStrokeWidth(width)
    return symbol


def _read_values_guard(layer, all_values: bool) -> None:
    """A classification reads the values of the layer on the main thread: never from a web service (each read is a
    download), and never more than the reads of layer_statistics when it reads every value (graduated classes).

    Raises:
        ValueError: A web service, or too many features shown.
    """
    from ..qgis.feature_count import features_to_read
    from .introspection import MAX_STAT_FEATURES, _refuse_web_service
    _refuse_web_service(layer)
    count = features_to_read(layer) if all_values else -1
    if isinstance(count, int) and count > MAX_STAT_FEATURES:
        raise ValueError(f"'{layer.name()}' shows more than {MAX_STAT_FEATURES} features and graduated classes read "
                         "every value: filter it first, or draw it with categories or one symbol")


def _categorized(layer, field: str, ramp):
    from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory
    index = _field_index(layer, field)
    _read_values_guard(layer, all_values=False)
    values = list(layer.uniqueValues(index, MAX_CATEGORIES + 2))
    plain = sorted((value for value in values if value is not None and not (hasattr(value, 'isNull') and value.isNull())),
                   key=lambda item: (isinstance(item, str), str(item) if not isinstance(item, (int, float)) else item))
    if len(plain) > MAX_CATEGORIES:
        raise ValueError(f"'{field}' takes more than {MAX_CATEGORIES} values: use graduated classes, or another field")
    if not plain:
        raise ValueError(f"'{field}' has no value to make categories from")
    categories = []
    for position, value in enumerate(plain):
        symbol = _symbol(layer, ramp.color(position / max(len(plain) - 1, 1)))
        categories.append(QgsRendererCategory(value, symbol, str(value)))
    return QgsCategorizedSymbolRenderer(layer.fields().at(index).name(), categories), len(categories)


def _graduated(layer, field: str, ramp, classes: int, method: str, center: Optional[float] = None):
    """Graduated classes; ``center`` makes them diverge from it: the middle color of the ramp at ``center``, the
    classes on each side darker as they go away from it."""
    from qgis import core
    index = _field_index(layer, field, numeric=True)
    _read_values_guard(layer, all_values=True)
    makers = {'quantile': 'QgsClassificationQuantile', 'equal_interval': 'QgsClassificationEqualInterval',
              'jenks': 'QgsClassificationJenks', 'pretty': 'QgsClassificationPrettyBreaks',
              'stddev': 'QgsClassificationStandardDeviation'}
    renderer = core.QgsGraduatedSymbolRenderer(layer.fields().at(index).name())
    renderer.setSourceSymbol(_symbol(layer))
    renderer.setSourceColorRamp(ramp)
    classification = getattr(core, makers[method])()
    if center is not None:
        if not math.isfinite(float(center)):
            raise ValueError('center must be a finite number')
        if classification.symmetricModeAvailable():
            # A limit of the classes at the center, as many classes on each side of it.
            classification.setSymmetricMode(True, float(center), False)
    renderer.setClassificationMethod(classification)
    renderer.updateClasses(layer, classes)
    made = len(renderer.ranges())
    if not made:
        raise ValueError(f"'{field}' has no value to make classes from")
    if center is not None:
        _diverge(renderer, float(center))
    return renderer, made


def _diverge(renderer, center: float) -> None:
    """Color the classes by their rank away from ``center``: the class that holds it takes the middle of the ramp,
    the first class on each side the next step, and so on. The side with fewer classes stops short of the end of the
    ramp, so a step means the same gap from the center on both sides, whatever the classes the method made.

    Quantiles or natural breaks may make a class across the center: it takes the middle color.
    """
    ramp = renderer.sourceColorRamp()  # the renderer owns the ramp it was given
    ranges = renderer.ranges()
    below = [number for number, item in enumerate(ranges) if item.upperValue() <= center]
    above = [number for number, item in enumerate(ranges) if item.lowerValue() >= center and number not in below]
    across = [number for number in range(len(ranges)) if number not in below and number not in above]
    steps = max(len(below), len(above), 1)
    positions = {number: 0.5 for number in across}
    positions.update({number: 0.5 - 0.5 * (len(below) - rank) / steps for rank, number in enumerate(below)})
    positions.update({number: 0.5 + 0.5 * (rank + 1) / steps for rank, number in enumerate(above)})
    for number, item in enumerate(ranges):
        symbol = item.symbol().clone()
        symbol.setColor(ramp.color(positions[number]))
        renderer.updateRangeSymbol(number, symbol)


def _band_range(layer, band: int, minimum: Optional[float], maximum: Optional[float], cut: Optional[float] = None,
                share_values: bool = True):
    """``(minimum, maximum)`` given, or read from the statistics of the band (not for a web service).

    ``share_values`` False: a refusal does not tell the range read from the band (a value of the raster).

    ``cut``: percent of the values left out at each end for a bound that is not given (2: from the 2nd to the
    98th percentile), so that a few extreme pixels do not flatten the colors of all the others.

    2026-11-12: a bound given must be a finite number, and the minimum below the maximum (NaN, Infinity and an
    inverted range were applied as given).
    """
    for name, value in (('minimum', minimum), ('maximum', maximum)):
        if value is not None and not math.isfinite(float(value)):
            raise ValueError(f"{name} must be a finite number")
    if minimum is not None and maximum is not None:
        if float(minimum) >= float(maximum):
            raise ValueError(f"minimum ({minimum}) must be below maximum ({maximum})")
        return float(minimum), float(maximum)
    from .introspection import _is_web_service
    if _is_web_service(layer):
        raise ValueError(f"'{layer.name()}' is a web service: give minimum and maximum, it is not read to find them")
    if cut is not None:
        if not math.isfinite(float(cut)) or not 0 < float(cut) <= MAX_CUT:
            raise ValueError(f'cut is a percentage left out at each end, above 0 and up to {MAX_CUT:g}')
        share = float(cut) / 100.0
        low, high = layer.dataProvider().cumulativeCut(band, share, 1.0 - share, layer.extent(), 250000)
        low = low if minimum is None else float(minimum)
        high = high if maximum is None else float(maximum)
        if not (math.isfinite(low) and math.isfinite(high)) or low >= high:
            raise ValueError(f"band {band} of '{layer.name()}' has no range of values to stretch")
        return low, high
    from qgis.core import Qgis, QgsRasterBandStats
    # One enum value: 3.40 and later warn on an int, which a union of two of them is.
    flags = getattr(getattr(Qgis, 'RasterBandStatistic', None), 'All', None)
    if flags is None:
        flags = QgsRasterBandStats.Stats.Min | QgsRasterBandStats.Stats.Max
    stats = layer.dataProvider().bandStatistics(band, flags, layer.extent(), 250000)
    low = stats.minimumValue if minimum is None else float(minimum)
    high = stats.maximumValue if maximum is None else float(maximum)
    if not (math.isfinite(low) and math.isfinite(high)):
        raise ValueError(f"band {band} of '{layer.name()}' has no range of values to stretch")
    if low >= high:
        if minimum is None and maximum is None:
            raise ValueError(f"band {band} of '{layer.name()}' has no range of values to stretch")
        if not share_values:
            # Which bound is out, and by how much, would tell the range of the band a bit at a time.
            raise ValueError(f"the range given cannot be applied to band {band} of '{layer.name()}'. The user shares no "
                             "values, so the range read from the band is not told: give both minimum and maximum, or "
                             "neither")
        raise ValueError(f"minimum ({low:g}) must be below maximum ({high:g}); band {band} of '{layer.name()}' "
                         f"ranges from {stats.minimumValue:g} to {stats.maximumValue:g}")
    return low, high


def _hillshade(layer, band: int, azimuth: float, altitude: float, z_factor: Optional[float], multidirectional: bool):
    """A shaded relief drawn from the elevations of ``band``, as lit from ``azimuth`` at ``altitude``.

    Raises:
        ValueError: A light that is no direction, or a factor that is no number above zero.
    """
    from qgis.core import QgsHillshadeRenderer
    for name, value, top in (('azimuth', azimuth, 360.0), ('altitude', altitude, 90.0)):
        if not math.isfinite(float(value)) or not 0 <= float(value) <= top:
            raise ValueError(f'{name} goes from 0 to {top:g} degrees')
    if z_factor is None:
        # Elevations in metres over a grid in degrees: without this every slope is a cliff, and the relief black.
        z_factor = _DEGREES_Z_FACTOR if layer.crs().isGeographic() else 1.0
    if not math.isfinite(float(z_factor)) or not 0 < float(z_factor) <= 1000:
        raise ValueError('z_factor is above 0: 1 for elevations in the units of the grid, more to deepen the relief')
    renderer = QgsHillshadeRenderer(layer.dataProvider(), band, float(azimuth), float(altitude))
    renderer.setZFactor(float(z_factor))
    renderer.setMultiDirectional(bool(multidirectional))
    return renderer, float(z_factor)


def _smooth_zoom(layer) -> None:
    """Draw a raster zoomed in by blending its pixels, not as squares.

    A hillshade is shaded pixel by pixel: on the map of a town, where a pixel of 30 m covers several of the screen,
    every slope showed as steps (seen on Lyon, 2026-11-15).
    """
    try:
        from qgis.core import QgsBilinearRasterResampler, QgsCubicRasterResampler
        resample = layer.resampleFilter()
        if resample is not None:
            resample.setZoomedInResampler(QgsCubicRasterResampler())
            resample.setZoomedOutResampler(QgsBilinearRasterResampler())
    except (ImportError, AttributeError, RuntimeError):
        logger.debug("raster resampling not set", exc_info=True)  # drawn as squares, as before


def _told_range(low: float, high: float, minimum: Optional[float], maximum: Optional[float],
                share_values: bool) -> Dict[str, Any]:
    """The bounds of a stretch a model is told. The user who shares no values (the setting "Allow attribute values to
    be sent") is not told what was read from the band, the extremes or the percentiles of its pixels: only a bound the
    model gave itself comes back."""
    if share_values:
        return {'minimum': low, 'maximum': high}
    return {'minimum': low if minimum is not None else None, 'maximum': high if maximum is not None else None}


def _raster_renderer(layer, mode: str, band: int, ramp_name: str, invert: bool, minimum, maximum,
                     cut: Optional[float] = None, discrete: bool = False, classes: int = 5,
                     share_values: bool = True):
    from qgis.core import (
        QgsColorRampShader, QgsContrastEnhancement, QgsSingleBandGrayRenderer, QgsSingleBandPseudoColorRenderer,
    )
    low, high = _band_range(layer, band, minimum, maximum, cut, share_values)
    provider = layer.dataProvider()
    if mode == 'gray':
        renderer = QgsSingleBandGrayRenderer(provider, band)
        contrast = QgsContrastEnhancement(provider.dataType(band))
        algorithm = getattr(QgsContrastEnhancement, 'ContrastEnhancementAlgorithm', QgsContrastEnhancement)
        contrast.setContrastEnhancementAlgorithm(algorithm.StretchToMinimumMaximum)
        contrast.setMinimumValue(low)
        contrast.setMaximumValue(high)
        renderer.setContrastEnhancement(contrast)
        return renderer, '', low, high
    ramp, ramp_used = _ramp(ramp_name, mode, invert)
    renderer = QgsSingleBandPseudoColorRenderer(provider, band)
    renderer.setClassificationMin(low)
    renderer.setClassificationMax(high)
    if discrete:
        # Flat steps of equal height, as a hypsometric map: the shader takes the ramp, a new one each time.
        renderer.createShader(ramp, QgsColorRampShader.Type.Discrete, QgsColorRampShader.ClassificationMode.EqualInterval,
                              max(2, min(int(classes), MAX_CLASSES)))
    else:
        renderer.createShader(ramp)
    return renderer, ramp_used, low, high


def _refresh(layer) -> None:
    layer.triggerRepaint()
    layer.emitStyleChanged()
    try:
        from qgis.utils import iface
        view = iface.layerTreeView() if iface is not None else None
        if view is not None:
            view.refreshLayerSymbology(layer.id())
    except (ImportError, AttributeError, RuntimeError):
        pass


# A style is evaluated for every feature at every drawing, and kept in the project: what can make a text or a geometry
# of any size (rpad("nom", 2000000000, 'x')) would freeze or crash QGIS each time the project opens.
_HEAVY = re.compile(r"\b(rpad|lpad|repeat|format_number|buffer)\s*\(", re.IGNORECASE)
_LONG_NUMBER = re.compile(r"\d{10,}")


def _too_heavy(text: str) -> str:
    """Why an expression is not kept in a style; "" when it can be."""
    found = _HEAVY.search(text)
    if found:
        return f"{found.group(1).lower()} is not used in a style: it is computed for every feature at every drawing"
    if _LONG_NUMBER.search(text):
        return "a number of ten digits or more is not used in a style"
    return ""


def _expression(layer, text: str, problem) -> str:
    """An expression a model wrote, checked: a plain one of the list accepted, that QGIS parses, on fields of the layer.

    Raises:
        ValueError: With the reason.
    """
    from qgis.core import QgsExpression, QgsFeatureRequest
    text = (text or '').strip()
    refused = problem(text) or _too_heavy(text)
    if refused:
        raise ValueError(f"this expression is refused: {refused}")
    parsed = QgsExpression(text)
    if parsed.hasParserError():
        raise ValueError(f"this is no QGIS expression: {parsed.parserErrorString()[:200]}")
    unknown = sorted(name for name in parsed.referencedColumns()
                     if name != QgsFeatureRequest.ALL_ATTRIBUTES and layer.fields().lookupField(name) < 0)
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)[:200]}")
    return text


def _rule_based(layer, rules: Optional[List[Dict[str, Any]]]):
    """A renderer with one symbol per condition; a rule with no condition draws every other feature."""
    from qgis.core import QgsRuleBasedRenderer
    if not rules:
        raise ValueError('rules is a list of {expression, color, label, width}')
    if len(rules) > MAX_RULES:
        raise ValueError(f'{MAX_RULES} rules at most')
    root = QgsRuleBasedRenderer.Rule(None)
    others = 0
    before: List[str] = []
    for number, rule in enumerate(rules, 1):
        if not isinstance(rule, dict) or not rule.get('color'):
            raise ValueError(f'rule {number} has no color')
        symbol = _symbol(layer, _color(str(rule['color'])), _width(rule.get('width')))
        condition = str(rule.get('expression') or '').strip()
        label = str(rule.get('label') or '')[:100]
        if condition:
            condition = _expression(layer, condition, expression_problem)
            # QGIS draws a feature with every rule it matches, one symbol over the other. Thresholds written one
            # after the other ("pop" > 1000, then "pop" > 10000) would stack: a feature is drawn by the first rule
            # it matches, so each rule leaves out what the rules before it took.
            taken = ''.join(f' AND NOT coalesce(({earlier}), false)' for earlier in before)
            before.append(condition)
            child = QgsRuleBasedRenderer.Rule(symbol, 0, 0, f'({condition}){taken}' if taken else condition,
                                              label or condition[:100])
        else:
            others += 1
            child = QgsRuleBasedRenderer.Rule(symbol, 0, 0, 'ELSE', label or 'Others', '', True)
        root.appendChild(child)
    if others > 1:
        raise ValueError('one rule at most has no expression: it draws every other feature')
    return QgsRuleBasedRenderer(root), len(rules)


def _only_for(layer, mode: str, geometry: str) -> None:
    if _geometry(layer) != geometry:
        raise ValueError(f"the mode {mode} is for a layer of {geometry}s: '{layer.name()}' has none")


def _positive_range(layer, field: str, mode: str):
    """``(field name, its largest value)`` for a mode that sizes or counts by a field: zero or more, some above zero.

    Raises:
        ValueError: An unknown or text field, a web service, a value below zero, no value above zero.
    """
    index = _field_index(layer, field, numeric=True, need=f'{mode} needs numbers (a count, an amount)')
    _read_values_guard(layer, all_values=False)
    try:
        low, top = float(layer.minimumValue(index)), float(layer.maximumValue(index))
    except (TypeError, ValueError):
        low = top = math.nan
    if not (math.isfinite(low) and math.isfinite(top)) or top <= 0:
        raise ValueError(f"'{field}' has no value above zero to draw {mode} from")
    if low < 0:
        raise ValueError(f"'{field}' holds values below zero, which {mode} cannot draw: use graduated with a center")
    return layer.fields().at(index).name(), top


def _heatmap(layer, field: str, ramp, radius: Optional[float]):
    """The density of the points, as a heat of colors; ``field`` weighs each point."""
    from qgis.core import QgsExpression, QgsGradientColorRamp, QgsGradientStop, QgsHeatmapRenderer
    from qgis.PyQt.QtGui import QColor
    _only_for(layer, 'heatmap', 'point')
    renderer = QgsHeatmapRenderer()
    if field:
        index = _field_index(layer, field, numeric=True, need='a heatmap weighs points by numbers')
        renderer.setWeightExpression(QgsExpression.quotedColumnRef(layer.fields().at(index).name()))
    # The heat paints its lowest value over the whole map: the ramp starts transparent, or it hides every layer under.
    clear = QColor(ramp.color(0.0))
    clear.setAlpha(0)
    renderer.setColorRamp(QgsGradientColorRamp(clear, QColor(ramp.color(1.0)), False, [
        QgsGradientStop(step / 10, QColor(ramp.color(step / 10))) for step in range(1, 10)]))
    renderer.setRadius(radius or HEAT_RADIUS)
    renderer.setRadiusUnit(_millimetres())
    return renderer


def _point_distance(layer, mode: str, color, distance: Optional[float]):
    """Points close together on the map gathered in one symbol that counts them (point_cluster), or spread around
    their place (point_displacement). The points apart keep how they were drawn (categories, one symbol...).

    Returns:
        The renderer, and the mode the points apart are drawn with.
    """
    from qgis.core import QgsPointClusterRenderer, QgsPointDisplacementRenderer, QgsSingleSymbolRenderer
    _only_for(layer, mode, 'point')
    current = layer.renderer()
    inner = current.embeddedRenderer() if current is not None and current.type() in (
        'pointCluster', 'pointDisplacement') else current
    if inner is not None and inner.type() in KEPT_INSIDE:
        inner = inner.clone()
    else:  # a heatmap, nothing: one symbol
        inner = QgsSingleSymbolRenderer(_symbol(layer, color))
    kept = KEPT_INSIDE[inner.type()]
    renderer = QgsPointClusterRenderer() if mode == 'point_cluster' else QgsPointDisplacementRenderer()
    renderer.setTolerance(distance or POINT_DISTANCE)
    renderer.setToleranceUnit(_millimetres())
    renderer.setEmbeddedRenderer(inner)
    if mode == 'point_cluster' and color is not None:
        # The disc only: the count is written over it by a second layer of the symbol, in its own color.
        renderer.clusterSymbol().symbolLayer(0).setColor(color)
    return renderer, kept


def _proportional(layer, field: str, color, largest: Optional[float]):
    """One symbol whose size follows ``field``: a circle whose area is in proportion to the value (on the point, or
    inside each polygon), or a line whose width is. The largest value takes ``largest`` millimetres, zero none.

    The largest symbols are drawn first, the small ones over them; over polygons, every outline before any circle.
    """
    from qgis.core import (
        QgsCentroidFillSymbolLayer, QgsDataDefinedSizeLegend, QgsExpression, QgsFeatureRequest, QgsFillSymbol,
        QgsMarkerSymbol, QgsProperty, QgsSingleSymbolRenderer, QgsSizeScaleTransformer,
    )
    geometry = _geometry(layer)
    name, top = _positive_range(layer, field, 'proportional')
    color = color if color is not None else _color('#e6550d')
    line = geometry == 'line'
    largest = largest or (WIDEST_LINE if line else LARGEST_SYMBOL)
    scale = _enum(QgsSizeScaleTransformer, 'ScaleType', 'Linear' if line else 'Flannery')
    # Flannery: the area of a circle grows a bit faster than the value, as the eye reads areas short.
    size = QgsProperty.fromField(name)
    size.setTransformer(QgsSizeScaleTransformer(scale, 0.0, top, 0.0, largest, 0.0, 1.0 if line else 0.57))
    if line:
        symbol = _symbol(layer, color)
        symbol.setDataDefinedWidth(size)
    else:
        marker = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': color.name(), 'outline_color': 'white',
                                               'outline_width': '0.2'})
        marker.setOpacity(0.85)  # where circles overlap, the edge of the one under shows
        marker.setDataDefinedSize(size)
        if geometry == 'point':
            symbol = marker
        elif geometry == 'polygon':
            symbol = QgsFillSymbol.createSimple({'color': '#f2f2f2', 'outline_color': '#9e9e9e',
                                                 'outline_width': '0.2'})
            centre = QgsCentroidFillSymbolLayer()
            centre.setPointOnSurface(True)  # inside the polygon, whatever its shape
            centre.setPointOnAllParts(False)
            centre.setSubSymbol(marker)
            centre.setRenderingPass(1)
            symbol.appendSymbolLayer(centre)
        else:
            raise ValueError(f"'{layer.name()}' has no geometry to draw")
    renderer = QgsSingleSymbolRenderer(symbol)
    renderer.setOrderBy(QgsFeatureRequest.OrderBy([QgsFeatureRequest.OrderByClause(QgsExpression.quotedColumnRef(name),
                                                                                   False)]))
    renderer.setOrderByEnabled(True)
    if geometry == 'polygon':
        renderer.setUsingSymbolLevels(True)
    if geometry == 'point':
        legend = QgsDataDefinedSizeLegend()
        legend.setLegendType(_enum(QgsDataDefinedSizeLegend, 'LegendType', 'LegendCollapsed'))
        renderer.setDataDefinedSizeLegend(legend)
    return renderer


def _number(value: float) -> str:
    """``value`` as an expression writes it: no exponent."""
    return format(value, '.15f').rstrip('0').rstrip('.') or '0'


def _nice(value: float) -> float:
    """1, 2 or 5 times a power of ten, the nearest at or above ``value``."""
    power = 10.0 ** math.floor(math.log10(value))
    return next(step * power for step in (1, 2, 5, 10) if step * power >= value * (1 - 1e-9))


def _dot_density(layer, field: str, color, per_dot: Optional[float], dot: Optional[float],
               share_values: bool = True):
    """Dots spread at random in each polygon, one for every ``per_dot`` of ``field``: a count shown over areas of
    any size. The dots keep their places from one drawing to the next.

    Returns:
        The renderer, and how much of the field one dot stands for.
    """
    from qgis.core import (
        QgsExpression, QgsFillSymbol, QgsMarkerSymbol, QgsProperty, QgsRandomMarkerFillSymbolLayer,
        QgsSingleSymbolRenderer, QgsSymbolLayer,
    )
    _only_for(layer, 'dot_density', 'polygon')
    name, top = _positive_range(layer, field, 'dot_density')
    if per_dot is None:
        per_dot = _nice(top / DOTS_IN_LARGEST)
    elif not math.isfinite(float(per_dot)) or float(per_dot) <= 0:
        raise ValueError('per_dot is how much of the field one dot stands for, above zero')
    per_dot = float(per_dot)
    if float(_number(per_dot)) <= 0:  # 1e-18 was written 0 in the expression: no dot drawn (2026-11-22, review)
        raise ValueError('per_dot is too small to be written: give a larger one')
    if top / per_dot > MAX_DOTS and share_values:
        # Shared only: the refusal is an oracle on the largest value (audit of 2026-11-24: dichotomy). Unshared,
        # the expression below caps at MAX_DOTS anyway, and the answer says to give per_dot.
        raise ValueError(f"one dot for {per_dot:g} puts more than {MAX_DOTS} dots in a polygon: give a larger per_dot")
    count = QgsProperty.fromExpression(
        f"max(0, min(floor(coalesce({QgsExpression.quotedColumnRef(name)}, 0) / {_number(per_dot)}), {MAX_DOTS}))")
    dots = QgsRandomMarkerFillSymbolLayer()
    dots.setSeed(1)  # the same places at each drawing: dots that move at each pan read as noise
    dots.setClipPoints(True)
    dots.setSubSymbol(QgsMarkerSymbol.createSimple({
        'name': 'circle', 'color': (color.name() if color is not None else '#252525'), 'outline_style': 'no',
        'size': f'{dot or DOT_SIZE:g}'}))
    dots.setDataDefinedProperty(_enum(QgsSymbolLayer, 'Property', 'PointCount', 'PropertyPointCount'), count)
    symbol = QgsFillSymbol.createSimple({'color': '#f7f7f7', 'outline_color': '#9e9e9e', 'outline_width': '0.2'})
    symbol.appendSymbolLayer(dots)
    return QgsSingleSymbolRenderer(symbol), per_dot


def _blocks(layer, field: str, color, factor: Optional[float]):
    """Polygons raised as blocks seen from the side (the 2.5D renderer of QGIS), ``field`` their height.

    QGIS reads the height and the angle from variables of the layer, which a style does not keep: an undo would
    leave them, and a redo find others. Written into the expressions of the symbol, they go with the style.
    """
    from qgis.core import Qgs25DRenderer, QgsExpression, QgsFeatureRequest, QgsReadWriteContext, QgsRenderContext
    from qgis.PyQt.QtXml import QDomDocument
    _only_for(layer, '2.5d', 'polygon')
    if factor is not None and (not math.isfinite(float(factor)) or float(factor) <= 0):
        raise ValueError('z_factor is above 0: how much the heights are stretched')
    height = '10'  # the default height of QGIS, in the units of the layer
    if field:
        index = _field_index(layer, field, numeric=True, need='2.5d raises polygons by numbers (a height)')
        height = f"coalesce({QgsExpression.quotedColumnRef(layer.fields().at(index).name())}, 0)"
    stretch = float(factor or 1.0) * (_DEGREES_Z_FACTOR if layer.crs().isGeographic() else 1.0)

    raised = f'(({height}) * {_number(stretch)})'

    def written(text: str) -> str:
        text = re.sub(r'eval\(\s*@qgis_25d_height\s*\)', lambda _match: raised, text)
        return re.sub(r'eval\(\s*@qgis_25d_angle\s*\)|@qgis_25d_angle\b', '70', text)

    renderer = Qgs25DRenderer()
    if color is not None:
        renderer.setRoofColor(color)
    for symbol in renderer.symbols(QgsRenderContext()):  # the walls and the roof
        for number in range(symbol.symbolLayerCount()):
            part = symbol.symbolLayer(number)
            if hasattr(part, 'geometryExpression'):
                part.setGeometryExpression(written(part.geometryExpression()))
    # The walls farthest from the eye first: an order by the angle too.
    renderer.setOrderBy(QgsFeatureRequest.OrderBy([
        QgsFeatureRequest.OrderByClause(written(clause.expression().expression()), clause.ascending(),
                                        clause.nullsFirst()) for clause in renderer.orderBy().list()]))
    document = QDomDocument('style')
    document.appendChild(renderer.save(document, QgsReadWriteContext()))
    if '@qgis_25d' in document.toString():
        raise ValueError('2.5d cannot be drawn by this version of QGIS from FilterMate: style it in QGIS')
    return renderer


def _drawn_by_its_service(layer) -> bool:
    """Whether a raster is an image its service draws (WMS, WMTS, XYZ): no band value to read."""
    try:
        from ..qgis.source_capability_probe import capability_for_layer
        capability = capability_for_layer(layer)
    except Exception:  # noqa: BLE001 - a layer that cannot say is styled as before
        return False
    return capability is not None and not capability.has_raw_values


def _blend_mode(name: str):
    """The composition mode of Qt a blending is; ValueError for one that is not of the list."""
    from qgis.PyQt.QtGui import QPainter
    if name not in BLENDS:
        raise ValueError(f"blend is one of {', '.join(BLENDS)}")
    return getattr(QPainter.CompositionMode, 'CompositionMode_' + BLENDS[name])


def set_layer_style(layer: str, mode: str, field: str = '', color: str = '', ramp: str = '', classes: int = 5,
                    method: str = 'quantile', invert: bool = False, opacity: Optional[float] = None, band: int = 1,
                    minimum: Optional[float] = None, maximum: Optional[float] = None,
                    rules: Optional[List[Dict[str, Any]]] = None, width: Optional[float] = None, blend: str = '',
                    cut: Optional[float] = None, discrete: bool = False, azimuth: float = 315.0,
                    altitude: float = 45.0, z_factor: Optional[float] = None,
                    multidirectional: bool = False, share_values: bool = True, per_dot: Optional[float] = None,
                    center: Optional[float] = None) -> Dict[str, Any]:
    """Draw a layer anew; what was made, without the values of its classes.

    ``share_values`` False: the range read from a raster (extremes, percentiles) is not told, nor in a refusal, as
    ``contour_lines`` does not tell its heights; nor how much a dot stands for when the call did not give it (read
    from the largest value of the field).

    ``width`` (millimetres) is also the radius of a heatmap, how close points are gathered (point_cluster,
    point_displacement), the largest proportional symbol and the size of a dot; ``z_factor`` stretches the heights
    of 2.5d; ``center`` makes graduated classes diverge from it.

    Raises:
        ValueError: An unknown layer, mode, field, color, ramp or blending, a field with too many values, a raster
            with no range to stretch.
    """
    found = _layer(layer)
    kind = layer_kind(found)
    if opacity is not None and not 0 <= float(opacity) <= 1:
        raise ValueError('opacity goes from 0 (invisible) to 1 (opaque)')
    blending = _blend_mode(blend) if blend else None
    answer: Dict[str, Any] = {'layer_name': found.name(), 'mode': mode}
    if mode == KEEP:
        # Only the opacity and the blending: the way the layer is drawn (its categories, the colors of an
        # orthophoto) stays.
        if opacity is None and blending is None:
            raise ValueError("the mode keep changes the opacity and the blending alone: give opacity or blend")
        if kind not in (LayerKind.VECTOR, LayerKind.RASTER):
            raise ValueError(f"'{found.name()}' is a {kind.value} layer: only vector and raster layers are styled here")
    elif kind is LayerKind.VECTOR:
        if mode not in VECTOR_MODES:
            raise ValueError(f"a vector layer takes the modes {', '.join(VECTOR_MODES + (KEEP,))}")
        from qgis.core import QgsSingleSymbolRenderer
        if mode == 'single':
            renderer = QgsSingleSymbolRenderer(_symbol(found, _color(color) if color else None, _width(width)))
        elif mode == 'heatmap':
            color_ramp, answer['ramp'] = _ramp(ramp, mode, invert)
            renderer = _heatmap(found, field, color_ramp, _width(width))
            answer['field'] = _field_name(found, field)
        elif mode in ('point_cluster', 'point_displacement'):
            renderer, kept = _point_distance(found, mode, _color(color) if color else None, _width(width))
            answer['note'] = f"the points apart keep their style ({kept})"
        elif mode == 'proportional':
            renderer = _proportional(found, field, _color(color) if color else None, _width(width))
            answer['field'] = _field_name(found, field)
        elif mode == 'dot_density':
            given = per_dot is not None
            renderer, told = _dot_density(found, field, _color(color) if color else None, per_dot, _width(width),
                                           share_values)
            answer['field'] = _field_name(found, field)
            if given or share_values:
                answer['per_dot'] = told
            else:
                answer['note'] = ("one dot stands for a share of the largest value, not told: the user shares no "
                                  "values. Give per_dot to choose it")
        elif mode == '2.5d':
            renderer = _blocks(found, field, _color(color) if color else None, z_factor)
            answer['field'] = _field_name(found, field)
        elif mode == 'categorized':
            color_ramp, answer['ramp'] = _ramp(ramp, mode, invert)
            renderer, answer['classes'] = _categorized(found, field, color_ramp)
            answer['field'] = renderer.classAttribute()
        elif mode == 'rules':
            renderer, answer['classes'] = _rule_based(found, rules)
        else:
            if method not in METHODS:
                raise ValueError(f"method is one of {', '.join(METHODS)}")
            classes = max(2, min(int(classes), MAX_CLASSES))
            color_ramp, answer['ramp'] = _ramp(ramp, mode, invert)
            renderer, answer['classes'] = _graduated(found, field, color_ramp, classes, method, center)
            answer.update({'field': renderer.classAttribute(), 'method': method})
        found.setRenderer(renderer)
    elif kind is LayerKind.RASTER:
        if mode not in RASTER_MODES:
            raise ValueError(f"a raster layer takes the modes {', '.join(RASTER_MODES + (KEEP,))}")
        if _drawn_by_its_service(found):
            # A WMS, a WMTS, tiles: an image already in colors, with no value to stretch (bounds given used to be
            # applied to it, and the image went wrong).
            raise ValueError(f"'{found.name()}' is an image drawn by its service: only its opacity and its blending "
                             f"can change (mode keep)")
        band = int(band)
        if not 1 <= band <= found.bandCount():
            raise ValueError(f"'{found.name()}' has bands 1 to {found.bandCount()}")
        if mode == 'hillshade':
            renderer, factor = _hillshade(found, band, azimuth, altitude, z_factor, multidirectional)
            found.setRenderer(renderer)
            _smooth_zoom(found)
            answer.update({'band': band, 'azimuth': float(azimuth), 'altitude': float(altitude), 'z_factor': factor})
        else:
            renderer, ramp_used, low, high = _raster_renderer(found, mode, band, ramp, invert, minimum, maximum,
                                                              cut, bool(discrete), classes, bool(share_values))
            found.setRenderer(renderer)
            answer.update({'band': band, **_told_range(low, high, minimum, maximum, bool(share_values))})
            if not share_values and (minimum is None or maximum is None):
                answer['note'] = ("minimum and maximum are not told: the user shares no values. The style is applied "
                                  "with the range read from the band, so there is no need to call again for it")
            if ramp_used:
                answer['ramp'] = ramp_used
            if discrete and mode == 'pseudocolor':
                answer['classes'] = max(2, min(int(classes), MAX_CLASSES))
    else:
        raise ValueError(f"'{found.name()}' is a {kind.value} layer: only vector and raster layers are styled here")
    if opacity is not None:
        found.setOpacity(float(opacity))
        answer['opacity'] = float(opacity)
    if blending is not None:
        found.setBlendMode(blending)
        answer['blend'] = blend
    _refresh(found)
    return answer


def _place_labels(layer, settings, placement: str) -> None:
    """Where the labels go. Lines: along each line following its curve, straight along it, or flat beside it.
    Polygons: on the inside point, flat, anywhere inside, around it, or along its outline. Points: around each one.

    Raises:
        ValueError: A placement that is none, or one asked of a layer that has none of its geometries.
    """
    from qgis.core import QgsPalLayerSettings
    if placement not in LABEL_PLACEMENTS:
        raise ValueError(f"placement is one of {', '.join(LABEL_PLACEMENTS)}")
    if placement == 'auto':
        return
    geometries, name = LABEL_PLACEMENTS[placement]
    if _geometry(layer) not in geometries:
        kinds = ' or '.join({'point': 'points', 'line': 'lines', 'polygon': 'polygons'}[kind] for kind in geometries)
        raise ValueError(f"placement {placement} is for a layer of {kinds}: '{layer.name()}' has none")
    settings.placement = getattr(QgsPalLayerSettings.Placement, name)
    if placement != 'curved':
        return
    try:
        # On the line itself, as the heights of contours are written: the name of the flag moved with the versions.
        from qgis.core import QgsLabeling
        flags = getattr(QgsLabeling, 'LinePlacementFlag', QgsLabeling)
        settings.lineSettings().setPlacementFlags(QgsLabeling.LinePlacementFlags(flags.OnLine))
    except (ImportError, AttributeError, TypeError):
        try:
            from qgis.core import Qgis
            settings.lineSettings().setPlacementFlags(Qgis.LabelLinePlacementFlag.OnLine)
        except (AttributeError, TypeError):
            logger.debug("labels on the line: flag not set in this QGIS", exc_info=True)  # above the line, then


def _font(text, family: str, bold: bool, italic: bool) -> None:
    """The family of the labels, bold, italic.

    Raises:
        ValueError: A family not installed: QGIS would write with another one without a word.
    """
    from qgis.PyQt.QtGui import QFontDatabase
    font = text.font()
    if family:
        try:
            families = list(QFontDatabase.families())  # Qt 6: static
        except TypeError:
            families = list(QFontDatabase().families())
        found = next((name for name in families if name.casefold() == family.strip().casefold()), None)
        if found is None:
            raise ValueError(f"no font {family[:100]!r} on this computer; some are: {', '.join(sorted(families)[:30])}")
        font.setFamily(found)
    font.setBold(bool(bold))
    font.setItalic(bool(italic))
    text.setFont(font)
    if hasattr(text, 'setForcedBold'):  # QGIS 3.26 and later: the style named in the format wins over the font
        text.setForcedBold(bool(bold))
        text.setForcedItalic(bool(italic))


def _background(text, color: str, opacity: Optional[float]) -> None:
    """A box with round corners behind the text, a little larger than it."""
    from qgis.core import QgsTextBackgroundSettings
    from qgis.PyQt.QtCore import QSizeF
    if opacity is not None and not 0 <= float(opacity) <= 1:
        raise ValueError('background_opacity goes from 0 (invisible) to 1 (opaque)')
    box = QgsTextBackgroundSettings()
    box.setEnabled(True)
    box.setType(_enum(QgsTextBackgroundSettings, 'ShapeType', 'ShapeRectangle'))
    box.setSizeType(_enum(QgsTextBackgroundSettings, 'SizeType', 'SizeBuffer'))
    box.setSize(QSizeF(1.0, 0.5))
    box.setSizeUnit(_millimetres())
    box.setRadii(QSizeF(0.5, 0.5))
    box.setRadiiUnit(_millimetres())
    box.setFillColor(_color(color))
    box.setStrokeWidth(0.0)
    box.setOpacity(1.0 if opacity is None else float(opacity))
    text.setBackground(box)


def _scale(name: str, value: Optional[float]) -> float:
    """The denominator of a scale a call gave; 0.0 (no limit) for none."""
    if value is None:
        return 0.0
    if not 1 <= float(value) <= 1e9:
        raise ValueError(f'{name} is the denominator of a scale: 50000 for 1:50 000')
    return float(value)


def set_labels(layer: str, field: str = '', enabled: bool = True, size: Optional[float] = None, color: str = '',
               buffer: bool = True, expression: str = '', visible_from_scale: Optional[float] = None,
               placement: str = 'auto', visible_to_scale: Optional[float] = None, background: str = '',
               background_opacity: Optional[float] = None, callouts: bool = False, font: str = '',
               bold: bool = False, italic: bool = False, wrap: Optional[int] = None, priority: Optional[int] = None,
               obstacle: Optional[bool] = None) -> Dict[str, Any]:
    """Label the features of a vector layer with a field or an expression, or turn its labels off.

    ``visible_from_scale``: the labels show when the map is at least that close (50000 for 1:50 000 and closer);
    ``visible_to_scale``: they hide when it is closer than that.
    ``placement``: for lines, ``curved`` writes each label on its line, following it (the heights of contours, the
    names of rivers), ``parallel`` straight along it, ``horizontal`` flat beside it; for polygons ``centroid``,
    ``horizontal``, ``free``, ``around`` or ``perimeter``; for points ``around``; ``auto`` leaves the choice to QGIS.
    ``background``: a box of that color behind the text. ``callouts``: a line from a label moved away to its
    feature. ``wrap``: characters per line at most. ``priority``: 0 to 10, the labels of a higher one are placed
    first. ``obstacle`` False: other labels may cover the features of the layer (None: as QGIS does, they may not).

    Raises:
        ValueError: Not a vector layer, an unknown field or font, an expression refused, a bad size, scale, color,
            placement, wrap or priority.
    """
    from qgis.core import QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
    found = _layer(layer)
    if layer_kind(found) is not LayerKind.VECTOR:
        raise ValueError(f"'{found.name()}' is not a vector layer: only features have labels")
    if not enabled:
        found.setLabelsEnabled(False)
        _refresh(found)
        return {'layer_name': found.name(), 'labels': False}
    if field and expression:
        raise ValueError('give a field or an expression, not both')
    settings = QgsPalLayerSettings()
    if expression:
        settings.fieldName = _expression(found, expression, processing_expression_problem)
        settings.isExpression = True
    else:
        settings.fieldName = found.fields().at(_field_index(found, field)).name()
        settings.isExpression = False
    _place_labels(found, settings, placement or 'auto')
    if visible_from_scale is not None or visible_to_scale is not None:
        farthest = _scale('visible_from_scale', visible_from_scale)
        closest = _scale('visible_to_scale', visible_to_scale)
        if farthest and closest >= farthest:
            raise ValueError('visible_to_scale is the closest scale the labels show at: below visible_from_scale')
        settings.scaleVisibility = True
        settings.minimumScale = farthest  # the farthest scale the labels show at
        settings.maximumScale = closest
    if wrap is not None:
        if not 5 <= int(wrap) <= 200:
            raise ValueError('wrap goes from 5 to 200 characters per line')
        settings.autoWrapLength = int(wrap)
    if priority is not None:
        if not 0 <= int(priority) <= 10:
            raise ValueError('priority goes from 0 to 10')
        settings.priority = int(priority)
    if obstacle is not None:
        settings.obstacleSettings().setIsObstacle(bool(obstacle))
    if callouts:
        from qgis.core import QgsSimpleLineCallout
        callout = QgsSimpleLineCallout()
        callout.setEnabled(True)
        settings.setCallout(callout)
    text = QgsTextFormat()
    if size is not None:
        if not 4 <= float(size) <= 72:
            raise ValueError('size goes from 4 to 72 points')
        text.setSize(float(size))
    if color:
        text.setColor(_color(color))
    if font or bold or italic:
        _font(text, font, bold, italic)
    if buffer:
        halo = QgsTextBufferSettings()
        halo.setEnabled(True)
        halo.setSize(1.0)
        text.setBuffer(halo)
    if background:
        _background(text, background, background_opacity)
    settings.setFormat(text)
    found.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    found.setLabelsEnabled(True)
    _refresh(found)
    return {'layer_name': found.name(), 'labels': True, 'field': '' if expression else settings.fieldName,
            'expression': settings.fieldName if expression else '',
            'visible_from_scale': float(visible_from_scale) if visible_from_scale is not None else None,
            'placement': placement or 'auto'}
