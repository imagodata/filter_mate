# -*- coding: utf-8 -*-
"""
Raster layer adapter: what EXPLORING shows and how a raster selection becomes
a source geometry.

* :func:`read_raster_summary` - bands, data type, resolution, NoData, classes.
* :func:`band_range` / :func:`band_histogram` - statistics for the range widget.
* :func:`identify_values` - values of every band at a map point (pixel picker).
* :func:`selection_geometry` - polygons of the pixels kept by a :class:`RasterSelection`.
* :func:`apply_selection_preview` / :func:`clear_selection_preview` - live mask in the renderer.
* :func:`selection_virtual_uri` - virtual raster keeping the selected pixels only (source filter).
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsPointXY,
    QgsRasterBandStats,
    QgsRasterDataProvider,
    QgsRasterLayer,
    QgsRectangle,
)

from ....core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode

logger = logging.getLogger(__name__)

DEFAULT_NODATA = -9999.0

# Qgis.DataType name -> numpy dtype
_NUMPY_TYPES = {
    'Byte': 'uint8', 'Int8': 'int8', 'UInt16': 'uint16', 'Int16': 'int16',
    'UInt32': 'uint32', 'Int32': 'int32', 'Float32': 'float32', 'Float64': 'float64',
}


def _data_type_name(data_type) -> str:
    name = getattr(data_type, 'name', None)
    if isinstance(name, str):
        return name
    mapping = {1: 'Byte', 2: 'UInt16', 3: 'Int16', 4: 'UInt32', 5: 'Int32', 6: 'Float32', 7: 'Float64', 14: 'Int8'}
    try:
        return mapping.get(int(data_type), 'Unknown')
    except (TypeError, ValueError):
        return 'Unknown'


@dataclass
class RasterBandInfo:
    number: int
    name: str
    data_type: str
    nodata: Optional[float]


@dataclass
class RasterSummary:
    """What the raster EXPLORING panel needs to know about a layer."""

    layer_id: str
    layer_name: str
    provider: str
    crs_authid: str
    width: int
    height: int
    pixel_size_x: float
    pixel_size_y: float
    bands: List[RasterBandInfo] = field(default_factory=list)
    classes: List[Tuple[float, str, str]] = field(default_factory=list)  # (value, label, color hex)
    renderer_type: str = ''

    @property
    def is_categorical(self) -> bool:
        return bool(self.classes)

    def band(self, number: int) -> Optional[RasterBandInfo]:
        for info in self.bands:
            if info.number == number:
                return info
        return None


def _renderer_classes(layer: QgsRasterLayer) -> List[Tuple[float, str, str]]:
    renderer = layer.renderer()
    if renderer is None:
        return []
    classes = []
    try:
        if renderer.type() == 'paletted':
            for item in renderer.classes():
                classes.append((float(item.value), item.label or str(item.value), item.color.name()))
    except Exception as exc:
        logger.debug(f"[FM5] paletted classes unreadable: {exc}")
    return classes


def read_raster_summary(layer: QgsRasterLayer) -> RasterSummary:
    """Read the layer description shown by the raster EXPLORING panel."""
    provider = layer.dataProvider()
    bands = []
    for number in range(1, layer.bandCount() + 1):
        nodata = None
        try:
            if provider.sourceHasNoDataValue(number) and provider.useSourceNoDataValue(number):
                nodata = float(provider.sourceNoDataValue(number))
        except Exception:
            nodata = None
        bands.append(RasterBandInfo(number, layer.bandName(number), _data_type_name(provider.dataType(number)), nodata))
    width, height = layer.width(), layer.height()
    extent = layer.extent()
    return RasterSummary(
        layer_id=layer.id(),
        layer_name=layer.name(),
        provider=layer.providerType(),
        crs_authid=layer.crs().authid(),
        width=width,
        height=height,
        pixel_size_x=extent.width() / width if width else 0.0,
        pixel_size_y=extent.height() / height if height else 0.0,
        bands=bands,
        classes=_renderer_classes(layer),
        renderer_type=layer.renderer().type() if layer.renderer() is not None else '',
    )


def _all_stats():
    stat = getattr(Qgis, 'RasterBandStatistic', None)
    if stat is not None:
        return stat.Min | stat.Max | stat.Mean | stat.StdDev
    return QgsRasterBandStats.Min | QgsRasterBandStats.Max | QgsRasterBandStats.Mean | QgsRasterBandStats.StdDev


def band_range(layer: QgsRasterLayer, band: int, sample_size: int = 250000) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """``(minimum, maximum, mean)`` of a band, estimated on ``sample_size`` pixels."""
    try:
        stats = layer.dataProvider().bandStatistics(band, _all_stats(), layer.extent(), sample_size)
    except Exception as exc:
        logger.debug(f"[FM5] band statistics failed: {exc}")
        return None, None, None
    if stats.minimumValue > stats.maximumValue:
        return None, None, None
    return float(stats.minimumValue), float(stats.maximumValue), float(stats.mean)


def band_histogram(layer: QgsRasterLayer, band: int, bins: int = 64, minimum: Optional[float] = None,
                   maximum: Optional[float] = None, sample_size: int = 250000) -> Tuple[List[int], float, float]:
    """Histogram of a band: ``(counts, minimum, maximum)``; empty counts when unavailable."""
    if minimum is None or maximum is None:
        low, high, _ = band_range(layer, band, sample_size)
        minimum = low if minimum is None else minimum
        maximum = high if maximum is None else maximum
    if minimum is None or maximum is None or not maximum > minimum:
        return [], minimum or 0.0, maximum or 0.0
    try:
        histogram = layer.dataProvider().histogram(band, int(bins), float(minimum), float(maximum), layer.extent(), sample_size)
        counts = [int(v) for v in histogram.histogramVector]
    except Exception as exc:
        logger.debug(f"[FM5] histogram failed: {exc}")
        return [], minimum, maximum
    return counts, float(minimum), float(maximum)


def identify_values(layer: QgsRasterLayer, point: QgsPointXY) -> Dict[int, Optional[float]]:
    """Value of every band at ``point`` (layer CRS); None for NoData or outside."""
    try:
        fmt = Qgis.RasterIdentifyFormat.Value
    except AttributeError:
        from qgis.core import QgsRaster
        fmt = QgsRaster.IdentifyFormatValue
    result = layer.dataProvider().identify(point, fmt)
    values: Dict[int, Optional[float]] = {}
    if not result.isValid():
        return values
    for band, value in result.results().items():
        try:
            values[int(band)] = None if value is None else float(value)
        except (TypeError, ValueError):
            values[int(band)] = None
    return values


def _grid_for(layer_extent: QgsRectangle, width: int, height: int, max_pixels: int) -> Tuple[int, int]:
    """Grid size to read: native size, or a coarser one above ``max_pixels``."""
    width, height = max(1, int(width)), max(1, int(height))
    if max_pixels and width * height > max_pixels:
        factor = math.sqrt((width * height) / float(max_pixels))
        width = max(1, int(width / factor))
        height = max(1, int(height / factor))
    return width, height


def read_band_array(provider: QgsRasterDataProvider, band: int, extent: QgsRectangle, width: int, height: int):
    """Read a band as a float64 numpy array with NaN for NoData."""
    import numpy as np
    block = provider.block(band, extent, width, height)
    dtype = _NUMPY_TYPES.get(_data_type_name(block.dataType()))
    if dtype is None:
        raise ValueError(f"unsupported raster data type {block.dataType()}")
    raw = bytes(block.data())
    array = np.frombuffer(raw, dtype=dtype, count=width * height).reshape((height, width)).astype('float64')
    try:
        if block.hasNoDataValue():
            array[array == float(block.noDataValue())] = np.nan
    except Exception:
        pass
    try:
        for user_range in provider.userNoDataValues(band) or []:
            array[(array >= user_range.min()) & (array <= user_range.max())] = np.nan
    except Exception:
        pass
    return array


def selection_mask(array, selection: RasterSelection):
    """Boolean numpy mask of the pixels kept by a RANGE or CLASSES selection."""
    import numpy as np
    valid = ~np.isnan(array)
    if selection.mode is RasterSelectionMode.RANGE:
        keep = valid.copy()
        if selection.minimum is not None:
            keep &= array >= selection.minimum
        if selection.maximum is not None:
            keep &= array <= selection.maximum
        return keep
    if selection.mode is RasterSelectionMode.CLASSES:
        values = np.round(np.where(valid, array, -1e300))
        return valid & np.isin(values, sorted(selection.classes))
    raise ValueError("expression selections are evaluated through a virtual raster")


@dataclass
class SelectionGeometryResult:
    geometry: object
    kept_pixels: int
    total_pixels: int
    cell_size: float


def selection_geometry(provider: QgsRasterDataProvider, selection: RasterSelection, extent: QgsRectangle,
                       native_width: int, native_height: int, crs_wkt: str, max_pixels: int = 4000000,
                       sieve_pixels: int = 4) -> SelectionGeometryResult:
    """Polygons of the pixels kept by ``selection`` (call from a task with a cloned provider).

    For an EXPRESSION selection, pass the provider of the virtual raster built by
    :func:`selection_virtual_layer` (its band 1 is 1 where selected).
    """
    import numpy as np
    from .geometry_tools import mask_to_geometry
    width, height = _grid_for(extent, native_width, native_height, max_pixels)
    if selection.mode is RasterSelectionMode.EXPRESSION:
        array = read_band_array(provider, 1, extent, width, height)
        mask = ~np.isnan(array) & (array != 0)
    else:
        array = read_band_array(provider, selection.band, extent, width, height)
        mask = selection_mask(array, selection)
    cell_x = extent.width() / width
    cell_y = extent.height() / height
    geotransform = (extent.xMinimum(), cell_x, 0.0, extent.yMaximum(), 0.0, -cell_y)
    geometry = mask_to_geometry(mask, geotransform, crs_wkt, sieve_pixels=sieve_pixels, simplify_tolerance=min(cell_x, cell_y) * 0.5)
    return SelectionGeometryResult(geometry, int(mask.sum()), int(mask.size), max(cell_x, cell_y))


# --- virtual rasters -------------------------------------------------------

def _virtual_parameters(layer: QgsRasterLayer, formula: str, reference: str):
    params = QgsRasterDataProvider.VirtualRasterParameters()
    params.crs = layer.crs()
    params.extent = layer.extent()
    params.width = layer.width()
    params.height = layer.height()
    params.formula = formula
    entry = QgsRasterDataProvider.VirtualRasterInputLayers()
    entry.name = reference
    entry.uri = layer.source()
    entry.provider = layer.providerType()
    params.rInputLayers = [entry]
    return params


def raster_reference(layer: QgsRasterLayer) -> str:
    """Name used for ``layer`` in raster calculator formulas."""
    name = ''.join(c if c.isalnum() or c == '_' else '_' for c in layer.name()) or 'raster'
    return name


def selection_virtual_layer(layer: QgsRasterLayer, selection: RasterSelection) -> Optional[QgsRasterLayer]:
    """Virtual raster equal to 1 where ``selection`` keeps the pixel, 0 elsewhere (main thread)."""
    reference = raster_reference(layer)
    formula = selection.to_calc_formula(reference)
    uri = QgsRasterDataProvider.encodeVirtualRasterProviderUri(_virtual_parameters(layer, formula, reference))
    virtual = QgsRasterLayer(uri, f"{layer.name()}_selection", 'virtualraster')
    return virtual if virtual.isValid() else None


def selection_virtual_uri(layer_source: str, layer_provider: str, layer: QgsRasterLayer, selection: RasterSelection,
                          nodata: float = DEFAULT_NODATA) -> Tuple[str, float]:
    """URI of a virtual raster keeping the selected pixels of band ``selection.band`` (others = ``nodata``).

    Args:
        layer_source: Source to read (the original one when the layer is already derived).
        layer_provider: Provider of ``layer_source``.
        layer: Layer giving CRS, extent and size.
        selection: Pixels to keep.
        nodata: Value written elsewhere (set as user NoData on the derived layer).

    Returns:
        ``(uri, nodata)``.
    """
    reference = raster_reference(layer)
    condition = selection.to_calc_formula(reference)
    value = f'"{reference}@{selection.band}"'
    formula = f"if ( {condition}, {value}, {nodata} )"
    params = _virtual_parameters(layer, formula, reference)
    params.rInputLayers[0].uri = layer_source
    params.rInputLayers[0].provider = layer_provider
    return QgsRasterDataProvider.encodeVirtualRasterProviderUri(params), nodata


def set_user_nodata(layer: QgsRasterLayer, nodata: Optional[float]) -> None:
    """Declare (or clear) a user NoData value on band 1 of ``layer``."""
    from qgis.core import QgsRasterRange
    provider = layer.dataProvider()
    for band in range(1, layer.bandCount() + 1):
        provider.setUserNoDataValue(band, [QgsRasterRange(nodata, nodata)] if nodata is not None else [])


# --- live preview of a selection (EXPLORING) -------------------------------

_PREVIEW_PROPERTY = 'filtermate/preview_transparency'


def apply_selection_preview(layer: QgsRasterLayer, selection: RasterSelection,
                            data_min: Optional[float], data_max: Optional[float]) -> bool:
    """Make the pixels outside a RANGE / CLASSES selection transparent in the renderer.

    The previous transparency settings are kept on the layer and restored by
    :func:`clear_selection_preview`. Only single band renderers are touched.
    """
    from qgis.core import QgsRasterTransparency
    renderer = layer.renderer()
    if renderer is None or selection.is_empty or selection.mode is RasterSelectionMode.EXPRESSION:
        return False
    if layer.customProperty(_PREVIEW_PROPERTY) is None:
        previous = renderer.rasterTransparency()
        layer.setCustomProperty(_PREVIEW_PROPERTY, _transparency_to_list(previous))
    transparency = QgsRasterTransparency()
    pixels = []
    pixel_cls = QgsRasterTransparency.TransparentSingleValuePixel
    low = -1e300 if data_min is None else data_min - 1
    high = 1e300 if data_max is None else data_max + 1
    if selection.mode is RasterSelectionMode.RANGE:
        if selection.minimum is not None:
            pixels.append(pixel_cls(low, selection.minimum, 100.0, True, False))
        if selection.maximum is not None:
            pixels.append(pixel_cls(selection.maximum, high, 100.0, False, True))
    else:
        kept = sorted(selection.classes)
        previous_value = low
        for value in kept:
            pixels.append(pixel_cls(previous_value, value, 100.0, True, False))
            previous_value = value
        pixels.append(pixel_cls(previous_value, high, 100.0, False, True))
    transparency.setTransparentSingleValuePixelList(pixels)
    renderer.setRasterTransparency(transparency)
    layer.triggerRepaint()
    return True


def _transparency_to_list(transparency) -> list:
    if transparency is None:
        return []
    items = []
    try:
        for pixel in transparency.transparentSingleValuePixelList():
            items.append([pixel.min, pixel.max, pixel.percentTransparent, pixel.includeMinimum, pixel.includeMaximum])
    except Exception:
        return []
    return items


def clear_selection_preview(layer: QgsRasterLayer) -> bool:
    """Restore the transparency saved by :func:`apply_selection_preview`."""
    from qgis.core import QgsRasterTransparency
    saved = layer.customProperty(_PREVIEW_PROPERTY)
    if saved is None:
        return False
    renderer = layer.renderer()
    if renderer is not None:
        transparency = QgsRasterTransparency()
        pixel_cls = QgsRasterTransparency.TransparentSingleValuePixel
        pixels = []
        for item in saved or []:
            try:
                pixels.append(pixel_cls(float(item[0]), float(item[1]), float(item[2]), bool(item[3]), bool(item[4])))
            except (TypeError, ValueError, IndexError):
                continue
        transparency.setTransparentSingleValuePixelList(pixels)
        renderer.setRasterTransparency(transparency)
        layer.triggerRepaint()
    layer.removeCustomProperty(_PREVIEW_PROPERTY)
    return True
