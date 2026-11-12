# -*- coding: utf-8 -*-
"""How a layer is drawn, for the agent: one symbol, categories, classes, a raster ramp, labels, opacity.

Main thread only, plain dicts out. The answer gives how many classes were made, never the values they hold: the
attribute values stay out of what the model reads, as ``describe_layer`` does. The chat captures the style of the
layer before the first change of a turn (``adapters/agent/turn_effects.py``), so undoing the turn brings it back.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional

from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.LayerStyle')

MAX_CATEGORIES = 100
MAX_CLASSES = 12
MAX_RAMPS_LISTED = 40
VECTOR_MODES = ('single', 'categorized', 'graduated')
RASTER_MODES = ('pseudocolor', 'gray')
METHODS = ('quantile', 'equal_interval', 'jenks', 'pretty', 'stddev')
DEFAULT_RAMPS = {'categorized': 'Spectral', 'graduated': 'Viridis', 'pseudocolor': 'Spectral'}


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
    style = QgsStyle.defaultStyle()
    names = list(style.colorRampNames())
    wanted = name or DEFAULT_RAMPS.get(mode, 'Spectral')
    found = next((item for item in names if item.casefold() == wanted.casefold()), None)
    if found is None:
        if name:
            raise ValueError(f"no color ramp {name!r}; some are: {', '.join(sorted(names)[:MAX_RAMPS_LISTED])}")
        found = names[0] if names else None
    ramp = style.colorRamp(found) if found else None
    if ramp is None:
        from qgis.core import QgsGradientColorRamp
        from qgis.PyQt.QtGui import QColor
        ramp, found = QgsGradientColorRamp(QColor('#fde725'), QColor('#440154')), 'gradient'
    if invert:
        ramp.invert()
    return ramp, found


def _field_index(layer, field: str, numeric: bool = False) -> int:
    index = layer.fields().lookupField(field or '')
    if index < 0:
        raise ValueError(f"'{layer.name()}' has no field {field!r} (describe_layer lists them)")
    if numeric and not layer.fields().at(index).isNumeric():
        raise ValueError(f"'{field}' is not a numeric field: graduated classes need numbers, use categorized")
    return index


def _symbol(layer, color=None):
    from qgis.core import QgsSymbol
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    if symbol is None:
        raise ValueError(f"'{layer.name()}' has no geometry to draw")
    if color is not None:
        symbol.setColor(color)
    return symbol


def _read_values_guard(layer, all_values: bool) -> None:
    """A classification reads the values of the layer on the main thread: never from a web service (each read is a
    download), and never more than the reads of layer_statistics when it reads every value (graduated classes).

    Raises:
        ValueError: A web service, or too many features shown.
    """
    from .introspection import MAX_STAT_FEATURES, _refuse_web_service
    _refuse_web_service(layer)
    count = layer.featureCount() if all_values else -1
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


def _graduated(layer, field: str, ramp, classes: int, method: str):
    from qgis import core
    index = _field_index(layer, field, numeric=True)
    _read_values_guard(layer, all_values=True)
    makers = {'quantile': 'QgsClassificationQuantile', 'equal_interval': 'QgsClassificationEqualInterval',
              'jenks': 'QgsClassificationJenks', 'pretty': 'QgsClassificationPrettyBreaks',
              'stddev': 'QgsClassificationStandardDeviation'}
    renderer = core.QgsGraduatedSymbolRenderer(layer.fields().at(index).name())
    renderer.setSourceSymbol(_symbol(layer))
    renderer.setSourceColorRamp(ramp)
    renderer.setClassificationMethod(getattr(core, makers[method])())
    renderer.updateClasses(layer, classes)
    made = len(renderer.ranges())
    if not made:
        raise ValueError(f"'{field}' has no value to make classes from")
    return renderer, made


def _band_range(layer, band: int, minimum: Optional[float], maximum: Optional[float]):
    """``(minimum, maximum)`` given, or read from the statistics of the band (not for a web service).

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
        raise ValueError(f"minimum ({low:g}) must be below maximum ({high:g}); band {band} of '{layer.name()}' "
                         f"ranges from {stats.minimumValue:g} to {stats.maximumValue:g}")
    return low, high


def _raster_renderer(layer, mode: str, band: int, ramp_name: str, invert: bool, minimum, maximum):
    from qgis.core import QgsContrastEnhancement, QgsSingleBandGrayRenderer, QgsSingleBandPseudoColorRenderer
    if not 1 <= band <= layer.bandCount():
        raise ValueError(f"'{layer.name()}' has bands 1 to {layer.bandCount()}")
    low, high = _band_range(layer, band, minimum, maximum)
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


def set_layer_style(layer: str, mode: str, field: str = '', color: str = '', ramp: str = '', classes: int = 5,
                    method: str = 'quantile', invert: bool = False, opacity: Optional[float] = None, band: int = 1,
                    minimum: Optional[float] = None, maximum: Optional[float] = None) -> Dict[str, Any]:
    """Draw a layer anew; what was made, without the values of its classes.

    Raises:
        ValueError: An unknown layer, mode, field, color or ramp, a field with too many values, a raster with no
            range to stretch.
    """
    found = _layer(layer)
    kind = layer_kind(found)
    if opacity is not None and not 0 <= float(opacity) <= 1:
        raise ValueError('opacity goes from 0 (invisible) to 1 (opaque)')
    answer: Dict[str, Any] = {'layer_name': found.name(), 'mode': mode}
    if kind is LayerKind.VECTOR:
        if mode not in VECTOR_MODES:
            raise ValueError(f"a vector layer takes the modes {', '.join(VECTOR_MODES)}")
        from qgis.core import QgsSingleSymbolRenderer
        if mode == 'single':
            renderer = QgsSingleSymbolRenderer(_symbol(found, _color(color) if color else None))
        elif mode == 'categorized':
            color_ramp, answer['ramp'] = _ramp(ramp, mode, invert)
            renderer, answer['classes'] = _categorized(found, field, color_ramp)
            answer['field'] = renderer.classAttribute()
        else:
            if method not in METHODS:
                raise ValueError(f"method is one of {', '.join(METHODS)}")
            classes = max(2, min(int(classes), MAX_CLASSES))
            color_ramp, answer['ramp'] = _ramp(ramp, mode, invert)
            renderer, answer['classes'] = _graduated(found, field, color_ramp, classes, method)
            answer.update({'field': renderer.classAttribute(), 'method': method})
        found.setRenderer(renderer)
    elif kind is LayerKind.RASTER:
        if mode not in RASTER_MODES:
            raise ValueError(f"a raster layer takes the modes {', '.join(RASTER_MODES)}")
        renderer, ramp_used, low, high = _raster_renderer(found, mode, int(band), ramp, invert, minimum, maximum)
        found.setRenderer(renderer)
        answer.update({'band': int(band), 'minimum': low, 'maximum': high})
        if ramp_used:
            answer['ramp'] = ramp_used
    else:
        raise ValueError(f"'{found.name()}' is a {kind.value} layer: only vector and raster layers are styled here")
    if opacity is not None:
        found.setOpacity(float(opacity))
        answer['opacity'] = float(opacity)
    _refresh(found)
    return answer


def set_labels(layer: str, field: str = '', enabled: bool = True, size: Optional[float] = None, color: str = '',
               buffer: bool = True) -> Dict[str, Any]:
    """Label the features of a vector layer with a field, or turn its labels off.

    Raises:
        ValueError: Not a vector layer, an unknown field, a bad size or color.
    """
    from qgis.core import QgsPalLayerSettings, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
    found = _layer(layer)
    if layer_kind(found) is not LayerKind.VECTOR:
        raise ValueError(f"'{found.name()}' is not a vector layer: only features have labels")
    if not enabled:
        found.setLabelsEnabled(False)
        _refresh(found)
        return {'layer_name': found.name(), 'labels': False}
    index = _field_index(found, field)
    settings = QgsPalLayerSettings()
    settings.fieldName = found.fields().at(index).name()
    settings.isExpression = False
    text = QgsTextFormat()
    if size is not None:
        if not 4 <= float(size) <= 72:
            raise ValueError('size goes from 4 to 72 points')
        text.setSize(float(size))
    if color:
        text.setColor(_color(color))
    if buffer:
        halo = QgsTextBufferSettings()
        halo.setEnabled(True)
        halo.setSize(1.0)
        text.setBuffer(halo)
    settings.setFormat(text)
    found.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    found.setLabelsEnabled(True)
    _refresh(found)
    return {'layer_name': found.name(), 'labels': True, 'field': settings.fieldName}
