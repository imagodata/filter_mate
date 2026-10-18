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
import re
import sys
import warnings
from urllib.parse import quote
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsPointXY,
    QgsRasterBandStats,
    QgsRasterDataProvider,
    QgsRasterLayer,
    QgsRectangle,
)

from ....core.domain.raster_filter_criteria import (
    DERIVATIVE_BOUNDS,
    RasterDerivative,
    RasterSelection,
    RasterSelectionMode,
)
from .terrain import derive, ground_cell_size

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
    is_alpha: bool = False  # 2026-10-17: transparency band (colour interpretation), not a colour


def is_alpha_band(provider, band: int) -> bool:
    """Whether ``band`` is the alpha (transparency) band, by its colour interpretation.

    2026-10-17: QGIS names the bands of a GeoTIFF "Band 1" ... "Band 4", so
    the name says nothing: an RGBA orthophoto was taken for RGB + infrared
    and the NDVI preset read the alpha band as infrared. Same test as
    snapshots._sync_alpha_band: ``Qgis.RasterColorInterpretation.AlphaBand``
    (QGIS 3.30+), the value 6 of ``QgsRaster.AlphaBand`` before.
    """
    try:
        interpretation = getattr(Qgis, 'RasterColorInterpretation', None)
        alpha_value = interpretation.AlphaBand if interpretation is not None else 6
        return provider.colorInterpretation(band) == alpha_value
    except Exception as exc:
        logger.debug(f"[FM5] colour interpretation of band {band} unreadable: {exc}")
        return False


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
    # Bands the renderer draws in each colour, ``{"R": 1, "G": 2, "B": 3}`` for a multiband
    # colour renderer, ``{"gray": n}`` for a single band one: the default colour roles of the panel.
    renderer_bands: Dict[str, int] = field(default_factory=dict)

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


def renderer_bands(layer: QgsRasterLayer) -> Dict[str, int]:
    """Bands the renderer draws: ``{"R", "G", "B"}`` of a multiband colour renderer, ``{"gray"}`` of a grey one.

    2026-10-18: the roles of the bands of an orthophoto (which one is red, which one is the
    near infrared) were guessed from their count and the user had to correct an IRC image
    by hand; the renderer already knows them.
    """
    renderer = layer.renderer()
    if renderer is None:
        return {}
    try:
        if renderer.type() == 'multibandcolor':
            bands = {'R': int(renderer.redBand()), 'G': int(renderer.greenBand()), 'B': int(renderer.blueBand())}
            return {role: band for role, band in bands.items() if band >= 1}
        if renderer.type() == 'singlebandgray':
            return {'gray': int(renderer.grayBand())}
    except Exception as exc:
        logger.debug(f"[FM5] renderer bands unreadable: {exc}")
    return {}


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
        bands.append(RasterBandInfo(number, layer.bandName(number), _data_type_name(provider.dataType(number)), nodata,
                                    is_alpha=is_alpha_band(provider, number)))
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
        renderer_bands=renderer_bands(layer),
    )


def _all_stats():
    stat = getattr(Qgis, 'RasterBandStatistic', None)
    if stat is not None:
        return stat.Min | stat.Max | stat.Mean | stat.StdDev
    stats = QgsRasterBandStats.Stats
    return stats.Min | stats.Max | stats.Mean | stats.StdDev


# The bindings flag every ``stats`` argument of bandStatistics() as the deprecated int
# overload, a real Qgis.RasterBandStatistics included (QGIS 3.44 and 4.2). Leaving
# ``stats`` out computes every statistic and gives another range (8-252 instead of
# 10-243 on an RGB ortho), so the call is kept and the false warning silenced here only.
warnings.filterwarnings('ignore', message=r'QgsRasterInterface\.bandStatistics\(\) is deprecated',
                        category=DeprecationWarning, module=__name__)


def band_statistics(provider, band: int, extent: QgsRectangle, sample_size: int):
    """Minimum, maximum, mean and standard deviation of ``band`` over ``extent``."""
    return provider.bandStatistics(band, _all_stats(), extent, sample_size)


def band_range(layer: QgsRasterLayer, band: int, sample_size: int = 250000) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """``(minimum, maximum, mean)`` of a band, estimated on ``sample_size`` pixels."""
    try:
        stats = band_statistics(layer.dataProvider(), band, layer.extent(), sample_size)
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
        fmt = QgsRaster.IdentifyFormat.IdentifyFormatValue
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
    except Exception as exc:
        logger.debug(f"[FM5] source NoData not applied: {exc}")
    try:
        for user_range in provider.userNoDataValues(band) or []:
            array[(array >= user_range.min()) & (array <= user_range.max())] = np.nan
    except Exception as exc:
        logger.debug(f"[FM5] user NoData ranges not applied: {exc}")
    return array


def crs_kind(crs) -> str:
    """``"geographic"`` (degrees), ``"mercator"`` (EPSG:3857) or ``"projected"``: how a cell size reaches the ground."""
    try:
        if crs.isGeographic():
            return 'geographic'
        if crs.authid() in ('EPSG:3857', 'EPSG:900913'):
            return 'mercator'
    except Exception as exc:
        logger.debug(f"[FM5] CRS kind unknown, read as projected: {exc}")
    return 'projected'


def derived_array(array, derivative: RasterDerivative, extent: QgsRectangle, kind):
    """``derivative`` of a band grid read over ``extent`` (the grid shape gives the cell size).

    Args:
        array: Band read by :func:`read_band_array`.
        derivative: Quantity to compute; ``VALUE`` returns ``array``.
        extent: Extent covered by ``array``, in the layer CRS.
        kind: :func:`crs_kind` of the layer CRS (degrees and Web Mercator cells are converted to metres);
            True / False are read as geographic / projected.
    """
    if not derivative.is_terrain:
        return array
    height, width = array.shape
    return derive(array, derivative, *grid_ground_size(extent, width, height, kind))


def grid_ground_size(extent: QgsRectangle, width: int, height: int, kind) -> Tuple[float, float]:
    """Ground size ``(x, y)`` of the cells of a ``width`` x ``height`` grid over ``extent`` (see :func:`derived_array`).

    Degrees and Web Mercator metres are converted at the latitude of the centre of ``extent``.
    """
    if isinstance(kind, bool):
        kind = 'geographic' if kind else 'projected'
    centre = (extent.yMinimum() + extent.yMaximum()) / 2.0
    if kind == 'mercator':  # northing -> latitude
        latitude = math.degrees(2.0 * math.atan(math.exp(centre / 6378137.0)) - math.pi / 2.0)
    else:
        latitude = centre if kind == 'geographic' else 0.0
    return ground_cell_size(extent.width() / width, extent.height() / height,
                            kind == 'geographic', latitude, mercator=kind == 'mercator')


_PICKED_DERIVATIVES = (RasterDerivative.SLOPE_DEGREES, RasterDerivative.SLOPE_PERCENT, RasterDerivative.ASPECT,
                       RasterDerivative.HILLSHADE, RasterDerivative.ROUGHNESS)


def terrain_values_at(layer: QgsRasterLayer, point: QgsPointXY, band: int) -> Dict[RasterDerivative, Optional[float]]:
    """Slope, aspect, hillshade and roughness of the pixel under ``point`` (layer CRS), the band read as a DTM.

    Read on the 3 x 3 pixels around it at the native resolution; a pixel on the border
    uses the window moved inside the raster. Empty when the point is outside the layer,
    the raster is smaller than 3 x 3 pixels or the band cannot be read; a value is None
    where it is undefined (NoData around, flat pixel has no aspect).
    """
    import math
    extent = layer.extent()
    width, height = layer.width(), layer.height()
    if width < 3 or height < 3 or not extent.contains(point):
        return {}
    size_x, size_y = extent.width() / width, extent.height() / height
    col = min(width - 1, max(0, int((point.x() - extent.xMinimum()) / size_x)))
    row = min(height - 1, max(0, int((extent.yMaximum() - point.y()) / size_y)))
    first_col = min(max(col - 1, 0), width - 3)
    first_row = min(max(row - 1, 0), height - 3)
    window = QgsRectangle(extent.xMinimum() + first_col * size_x, extent.yMaximum() - (first_row + 3) * size_y,
                          extent.xMinimum() + (first_col + 3) * size_x, extent.yMaximum() - first_row * size_y)
    try:
        array = read_band_array(layer.dataProvider(), band, window, 3, 3)
    except Exception as exc:
        logger.debug(f"[FM5] terrain values not read: {exc}")
        return {}
    kind = crs_kind(layer.crs())
    values: Dict[RasterDerivative, Optional[float]] = {}
    for derivative in _PICKED_DERIVATIVES:
        result = derived_array(array, derivative, window, kind)[row - first_row, col - first_col]
        values[derivative] = float(result) if math.isfinite(result) else None
    return values


def derivative_zone_statistics(layer: QgsRasterLayer, band: int, rect: QgsRectangle, derivative: RasterDerivative,
                               max_pixels: int = 250000):
    """``(minimum, maximum, mean, count)`` of a terrain derivative over ``rect`` (layer CRS); None without a valid pixel.

    The rectangle is read on its own pixels, so a pixel of its border sees an extrapolated
    neighbourhood. ``count`` is the number of valid pixels of the grid read.
    """
    import numpy as np
    extent = layer.extent()
    rect = rect.intersect(extent)
    if rect.isEmpty() or not layer.width() or not layer.height():
        return None
    native_x = max(1, int(round(rect.width() / (extent.width() / layer.width()))))
    native_y = max(1, int(round(rect.height() / (extent.height() / layer.height()))))
    width, height = _grid_for(rect, native_x, native_y, max_pixels)
    try:
        array = read_band_array(layer.dataProvider(), band, rect, width, height)
        values = derived_array(array, derivative, rect, crs_kind(layer.crs()))
    except Exception as exc:
        logger.debug(f"[FM5] derivative zone statistics failed: {exc}")
        return None
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    return float(values.min()), float(values.max()), float(values.mean()), int(values.size)


def derivative_histogram(layer: QgsRasterLayer, band: int, derivative: RasterDerivative, bins: int = 64,
                         max_pixels: int = 1000000) -> Tuple[List[int], float, float]:
    """Histogram of a terrain derivative of ``band``: ``(counts, minimum, maximum)``.

    Computed on the band read on at most ``max_pixels`` pixels. A coarser grid
    smooths the relief, so the slopes of a large raster are underestimated
    here; the filter itself reads up to its own (larger) pixel budget.
    Empty counts when the band cannot be read or has no valid pixel.
    """
    import numpy as np
    extent = layer.extent()
    width, height = _grid_for(extent, layer.width(), layer.height(), max_pixels)
    try:
        array = read_band_array(layer.dataProvider(), band, extent, width, height)
        values = derived_array(array, derivative, extent, crs_kind(layer.crs()))
    except Exception as exc:
        logger.debug(f"[FM5] derivative histogram failed: {exc}")
        return [], 0.0, 0.0
    values = values[np.isfinite(values)]
    if values.size == 0:
        return [], 0.0, 0.0
    low, high = DERIVATIVE_BOUNDS.get(derivative, (float(values.min()), float(values.max())))
    if derivative not in DERIVATIVE_BOUNDS:
        high = float(values.max())
    if not high > low:
        high = low + 1.0
    counts, _edges = np.histogram(values, bins=int(bins), range=(low, high))
    return [int(c) for c in counts], float(low), float(high)


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


def referenced_bands(expression: str, reference: str) -> List[int]:
    """Band numbers ``expression`` reads from the layer named ``reference`` (``"ortho@3"`` -> 3), sorted."""
    pattern = '"' + re.escape(reference) + r'@(\d+)"'
    return sorted({int(number) for number in re.findall(pattern, expression or '')})


def expression_mask(virtual_provider: QgsRasterDataProvider, provider: QgsRasterDataProvider, bands,
                    extent: QgsRectangle, width: int, height: int):
    """``(kept, valid)`` masks of a raster calculator expression over ``extent``, read on a ``width`` x ``height`` grid.

    ``virtual_provider`` is the virtual raster of :func:`selection_virtual_layer`
    (1 where the expression holds). It has no NoData: a NoData pixel of a band
    still gives 0 or 1 (``"ortho@3" != 5`` keeps the NoData edge of an
    orthophoto, QGIS 3.44 and 4.2). ``valid`` is therefore False where one of
    ``bands`` (the ones the expression reads, :func:`referenced_bands`) of
    ``provider`` has NoData, and such a pixel is never kept.
    """
    import numpy as np
    array = read_band_array(virtual_provider, 1, extent, width, height)
    valid = ~np.isnan(array)
    for band in bands:
        valid &= ~np.isnan(read_band_array(provider, band, extent, width, height))
    return valid & (array != 0), valid


@dataclass
class SelectionGeometryResult:
    geometry: object
    kept_pixels: int
    total_pixels: int
    cell_size: float
    truncated: bool = False  # object detection: an object went on past the largest window read
    objects: int = 0  # object detection: number of objects found under the clicks
    grid: Tuple[int, int] = (0, 0)  # (width, height) of the grid read
    tiles: int = 0
    coarse: bool = False  # the grid is coarser than the raster (over max_pixels)
    canceled: bool = False
    decimation: int = 1  # pixels per cell side (1: native resolution)
    smoothing: int = 0  # largest closing radius (cells) a tile needed to fit the vertex budget
    vertices: int = 0


# Below this many selected pixels the selection is polygonized without sieve.
SIEVE_MIN_KEPT_PIXELS = 10000
# The source geometry of a selection is read at the native resolution up to this
# many pixels; beyond, every 2nd, 4th... pixel (a power of two, like the overviews)
# until the grid fits (logged, and told to the user). 100 million pixels: 6 km2 of
# 25 cm orthophoto pixel for pixel, 25 km2 on cells of 50 cm (a 2 m x 2 m object
# is 16 cells). Measured (QGIS 4.2, 2026-10-18): a dense, speckled selection of 400
# million pixels took 141 s, 373 s with the majority smoothing; a quarter of that here.
SOURCE_MAX_PIXELS = 100000000
# A smaller limit is raised to this (a config value of 0 or 10 would be no grid at all).
SOURCE_MIN_PIXELS = 10000
# Vertices of the source geometry. It is stored (history, project) and every
# target goes through it: a GDAL cutline, a PDAL crop, prepared GEOS predicates.
# About 20 bytes of WKT per vertex: 4 MB at most. Under it, a selection is drawn
# pixel for pixel; a tile over its share (by area) is smoothed (see _fit_tile).
SOURCE_MAX_VERTICES = 200000
# Side of the tiles the source geometry is read by: about 4 million cells (32 MB
# per float64 band array, a few arrays at a time), few enough tiles for the union.
SOURCE_TILE_SIZE = 2048
# Closing radii (cells) tried, in order, on a tile with too many vertices.
_SMOOTHING_RADII = (1, 2, 4, 8, 16)
# Tolerances (cells) of the topology preserving simplification of a geometry still over the budget.
_SIMPLIFY_TOLERANCES = (1.0, 2.0, 4.0, 8.0)


def source_max_pixels(value) -> int:
    """``CROSS_FILTER.raster_source_max_pixels`` read from a config or API value.

    ``4e8``, ``"400 000 000"`` and ``400_000_000`` are read; nothing, 0 or an
    unreadable value is the default, a value below :data:`SOURCE_MIN_PIXELS` is raised to it.
    """
    if isinstance(value, dict):
        value = value.get('value')
    if isinstance(value, str):
        value = value.replace(' ', '').replace(' ', '').replace('_', '')
    try:
        number = int(float(value)) if not isinstance(value, bool) and value is not None else 0
    except (TypeError, ValueError, OverflowError):
        number = 0
    if number <= 0:
        return SOURCE_MAX_PIXELS
    return max(SOURCE_MIN_PIXELS, number)


def _decimation(width: int, height: int, max_pixels: int) -> int:
    """Smallest power of two ``k`` whose grid of ``k`` x ``k`` pixel cells holds ``max_pixels`` cells at most."""
    k = 1
    while max_pixels and math.ceil(width / k) * math.ceil(height / k) > max_pixels:
        k *= 2
    return k


def gdal_cell_reader(source: str, provider: Optional[QgsRasterDataProvider] = None):
    """``read(band, col, row, cols, rows, k)``: cells of ``k`` x ``k`` pixels of a GDAL file, NaN for NoData.

    Over the pixel limit, the QGIS provider resamples a window to the size asked
    for on its own and takes a pixel up to 3 pixels off the cell, differently
    for a tile and for the whole raster (measured on QGIS 3.44 and 4.2, with
    overviews or not). Here a cell is one pixel of the overview whose factor
    divides ``k``, indexed in that overview (GDAL alone maps a window to an
    overview of ``ceil(width / f)`` pixels by its scale, which drifts), or of
    the band itself: the same pixels from any tile. Opened in the thread that
    reads; None when ``source`` does not open. ``provider`` gives the user NoData ranges.
    """
    from osgeo import gdal
    try:
        dataset = gdal.OpenEx(source, gdal.OF_RASTER | gdal.OF_READONLY)
        plain = gdal.OpenEx(source, gdal.OF_RASTER | gdal.OF_READONLY, open_options=['OVERVIEW_LEVEL=NONE'])
    except RuntimeError as exc:  # gdal.UseExceptions() set by another plugin
        logger.debug(f"[FM5] '{source}' not opened by GDAL: {exc}")
        return None
    if dataset is None or plain is None:
        return None

    def cells_band(band: int, k: int):
        """``(gdal band, factor)``: the overview of the largest factor dividing ``k``, else the band (no overview)."""
        base = dataset.GetRasterBand(band)
        best, factor = plain.GetRasterBand(band), 1
        for index in range(base.GetOverviewCount()):
            overview = base.GetOverview(index)
            ratio = base.XSize / float(overview.XSize) if overview is not None and overview.XSize else 0.0
            f = int(round(ratio))
            if f > factor and abs(ratio - f) < 0.5 and k % f == 0:
                best, factor = overview, f
        return best, factor

    def read(band: int, col: int, row: int, cols: int, rows: int, k: int):
        import numpy as np
        source_band, factor = cells_band(band, k)
        step = k // factor
        array = source_band.ReadAsArray(col * step, row * step, cols * step, rows * step, buf_xsize=cols,
                                        buf_ysize=rows, resample_alg=gdal.GRIORA_NearestNeighbour)
        if array is None:
            raise RuntimeError(f"GDAL could not read band {band} of '{source}'")
        array = array.astype('float64')
        nodata = dataset.GetRasterBand(band).GetNoDataValue()
        if nodata is not None and (provider is None or provider.useSourceNoDataValue(band)):
            array[array == nodata] = np.nan
        if provider is not None:
            for user_range in provider.userNoDataValues(band) or []:
                array[(array >= user_range.min()) & (array <= user_range.max())] = np.nan
        return array

    read.datasets = (dataset, plain)  # open as long as the reader lives
    return read


def _tiles(width: int, height: int, size: int):
    """``(row, col, rows, cols)`` of the tiles covering a ``width`` x ``height`` grid, row by row."""
    size = max(1, int(size))
    for row in range(0, height, size):
        for col in range(0, width, size):
            yield row, col, min(size, height - row), min(size, width - col)


def mask_corners(mask) -> int:
    """Vertices GDAL Polygonize draws for ``mask`` (4-connected patches): its corners.

    A lattice point is a corner when 1 or 3 of its 4 cells are set, two corners
    (one per patch) when 2 diagonal ones are; ring closing points are not counted.
    """
    import numpy as np
    grid = np.pad(mask != 0, 1).astype(np.int8)
    a, b, c, d = grid[:-1, :-1], grid[:-1, 1:], grid[1:, :-1], grid[1:, 1:]
    total = a + b + c + d
    return int(np.count_nonzero((total == 1) | (total == 3)) + 2 * np.count_nonzero((total == 2) & (a == d)))


def _box_count(mask, radius: int, outside: int):
    """Set cells in the ``(2 radius + 1)`` square around each cell; ``outside`` is the value beyond the grid."""
    import numpy as np
    size = 2 * radius + 1
    padded = np.pad(mask.astype(np.int32), radius, constant_values=outside)
    sums = np.pad(padded.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return sums[size:, size:] - sums[:-size, size:] - sums[size:, :-size] + sums[:-size, :-size]


def closing(mask, radius: int):
    """Morphological closing by a square of side ``2 radius + 1``: gaps narrower than it are filled.

    Never drops a set cell (outside the grid counts as set for the erosion): an
    isolated patch stays as it is, nearby patches merge into one smooth area.
    """
    dilated = _box_count(mask, radius, 0) > 0
    return _box_count(dilated, radius, 1) == (2 * radius + 1) ** 2


def majority(mask, radius: int):
    """Cells set in at least half of the ``(2 radius + 1)`` square around them, plus the patches far from those.

    A dense, speckled selection becomes the areas where it dominates, about as
    large as it was; a set cell more than ``2 radius`` cells away from such an
    area (an isolated pool, a sparse speckle) is kept as it is.
    """
    import numpy as np
    inside = _box_count(np.ones(mask.shape, dtype=bool), radius, 0)
    dominant = 2 * _box_count(mask, radius, 0) >= inside
    near = _box_count(dominant, 2 * radius, 0) > 0
    return dominant | (mask & ~near)


def _fit_tile(window, core, sieve_pixels: int, allowance: float):
    """``(mask, radius)``: the core of ``window`` sieved, smoothed by the least that fits ``allowance`` vertices.

    The tile keeps its pixels when they fit. Otherwise it is a dense, speckled
    selection (vegetation, a noisy slope), smoothed by a growing :func:`majority`
    (the areas where it dominates; an isolated object stays), then, for a
    speckle sparse everywhere, by a growing :func:`closing` (its patches merge).
    The steps lose vertices in that order: the least one that fits is found by
    bisection (4 tries instead of 10), the strongest kept when none fits.
    """
    from .geometry_tools import sieve_mask
    steps = [(None, 0)] + [(majority, radius) for radius in _SMOOTHING_RADII]
    steps += [(closing, radius) for radius in _SMOOTHING_RADII]
    tried = {}

    def fits(index):
        if index not in tried:
            smooth, radius = steps[index]
            mask = smooth(window, radius) if smooth is not None else window
            if sieve_pixels > 1:
                mask = sieve_mask(mask, sieve_pixels)
            tried[index] = (mask[core], mask_corners(mask[core]) <= allowance)
        return tried[index][1]

    low, high = 0, len(steps) - 1
    if not fits(low):
        low += 1
        while low < high:
            middle = (low + high) // 2
            if fits(middle):
                high = middle
            else:
                low = middle + 1
        fits(low)
    return tried[low][0], steps[low][1]


def _selection_mask_over(provider: QgsRasterDataProvider, selection: RasterSelection, extent: QgsRectangle,
                         width: int, height: int, crs_wkt: str):
    """Boolean grid (height, width) of the pixels ``selection`` keeps over ``extent``.

    For an EXPRESSION selection, ``provider`` is the one of the virtual raster
    built by :func:`selection_virtual_layer` (its band 1 is 1 where selected).
    """
    import numpy as np
    if selection.mode is RasterSelectionMode.EXPRESSION:
        array = read_band_array(provider, 1, extent, width, height)
        return ~np.isnan(array) & (array != 0)
    array = read_band_array(provider, selection.band, extent, width, height)
    if selection.derivative.is_terrain:
        kind = crs_kind(QgsCoordinateReferenceSystem.fromWkt(crs_wkt))
        array = derived_array(array, selection.derivative, extent, kind)
    return selection_mask(array, selection)


def selection_geometry(provider: QgsRasterDataProvider, selection: RasterSelection, extent: QgsRectangle,
                       native_width: int, native_height: int, crs_wkt: str, max_pixels: int = SOURCE_MAX_PIXELS,
                       sieve_pixels: int = 4, nodata_provider: Optional[QgsRasterDataProvider] = None,
                       nodata_bands=(), is_canceled=None, progress=None, tile_size: int = SOURCE_TILE_SIZE,
                       max_vertices: int = SOURCE_MAX_VERTICES, provider_for=None,
                       cell_reader=None) -> SelectionGeometryResult:
    """Polygons of the pixels kept by ``selection`` (call from a task with cloned providers).

    The raster is read tile by tile at its native resolution, or every ``k``
    pixels beyond ``max_pixels`` (``k`` a power of two, like the overviews; the
    last ``k - 1`` pixels of a side are left out). Over the limit, a band of a
    GDAL file is read through ``cell_reader`` (:func:`gdal_cell_reader`), the
    same pixels from a tile or the whole raster; an expression goes through its
    virtual raster, which QGIS resamples by window: a cell may then take a pixel
    of its neighbour near a tile edge. Each tile
    is polygonized in cell coordinates, where the edges two tiles share are the
    same integers, and the union is moved to the map at the end. A tile is
    read with a margin: a slope needs the neighbours of its edge pixels, the
    sieve and the smoothing the patches crossing its edge.

    The geometry holds about ``max_vertices`` vertices at most: a tile over its
    share (by area) is smoothed (:func:`_fit_tile`), and a geometry still over
    the budget is simplified, keeping its patches.

    For an EXPRESSION selection, pass the provider of the virtual raster built by
    :func:`selection_virtual_layer` (its band 1 is 1 where selected), and the
    provider of the raster it reads as ``nodata_provider`` with the bands the
    expression reads (:func:`expression_mask`): their NoData pixels are dropped.
    A selection with seeds keeps the objects under them (:func:`object_geometry`,
    ``provider_for``), read in windows around the clicks.

    Args:
        is_canceled: Callable checked between tiles; a canceled read returns an
            empty geometry with ``canceled`` set.
        progress: Callable receiving the progress in percent.
    """
    from .geometry_tools import make_valid, merge_tile_polygons, pixel_to_map, polygonize_mask
    if selection.seeds:
        return object_geometry(provider, selection, extent, native_width, native_height, crs_wkt,
                               provider_for=provider_for)
    native_x, native_y = extent.width() / native_width, extent.height() / native_height
    k = _decimation(native_width, native_height, max_pixels)
    # Whole cells only: a window running past the raster is resampled by QGIS to fit, off
    # the cells (measured). Over the limit, the last k - 1 pixels of a side are left out.
    width, height = max(1, native_width // k), max(1, native_height // k)
    cell_x, cell_y = native_x * k, native_y * k
    coarse = k > 1
    if coarse:
        logger.info(f"⏱ [FM5] raster selection: {native_width} x {native_height} pixels, over the limit of "
                    f"{max_pixels}: read every {k} pixels, cells of {max(cell_x, cell_y):g} map units "
                    f"(CROSS_FILTER.raster_source_max_pixels)")
        # Each cell already stands for several pixels: only lone cells are speckle.
        sieve_pixels = min(sieve_pixels, 2)
    expression = selection.mode is RasterSelectionMode.EXPRESSION
    ground = None
    if not expression and selection.derivative.is_terrain:
        ground = grid_ground_size(QgsRectangle(extent.xMinimum(), extent.yMaximum() - height * cell_y,
                                               extent.xMinimum() + width * cell_x, extent.yMaximum()),
                                  width, height, crs_kind(QgsCoordinateReferenceSystem.fromWkt(crs_wkt)))
    sieving = bool(sieve_pixels and sieve_pixels > 1)
    # Cells within the sieve size and three times the largest smoothing radius of
    # a tile must be right (majority, then its neighbourhood); the outer ring of a derivative is not.
    margin = (int(sieve_pixels) if sieving else 0) + 1 + 3 * _SMOOTHING_RADII[-1]
    tiles = list(_tiles(width, height, tile_size))
    # (inner, edge) polygons with the sieve and without; the latter while they may be the result.
    sieved, plain, keep_plain = ([], []), ([], []), True
    kept, smoothing = 0, 0
    for number, (row, col, rows, cols) in enumerate(tiles):
        if is_canceled is not None and is_canceled():
            return SelectionGeometryResult(QgsGeometry(), kept, width * height, max(cell_x, cell_y), grid=(width, height),
                                           tiles=len(tiles), coarse=coarse, canceled=True, decimation=k)
        top, left = max(0, row - margin), max(0, col - margin)
        bottom, right = min(height, row + rows + margin), min(width, col + cols + margin)
        window = QgsRectangle(extent.xMinimum() + left * cell_x, extent.yMaximum() - bottom * cell_y,
                              extent.xMinimum() + right * cell_x, extent.yMaximum() - top * cell_y)
        if expression:
            mask, _valid = expression_mask(provider, nodata_provider, nodata_bands if nodata_provider is not None else (),
                                           window, right - left, bottom - top)
        else:
            if coarse and cell_reader is not None:
                array = cell_reader(selection.band, left, top, right - left, bottom - top, k)
            else:
                array = read_band_array(provider, selection.band, window, right - left, bottom - top)
            if ground is not None:
                array = derive(array, selection.derivative, *ground)
            mask = selection_mask(array, selection)
        if mask.any():
            core = (slice(row - top, row - top + rows), slice(col - left, col - left + cols))
            kept += int(mask[core].sum())
            allowance = max_vertices * (rows * cols) / float(width * height)
            # Cell coordinates: the edges two tiles share are the same integers.
            cells = (float(col), 1.0, 0.0, float(row), 0.0, 1.0)
            # Edges shared with another tile (not the border of the raster).
            shared = (col if col > 0 else None, col + cols if col + cols < width else None,
                      row if row > 0 else None, row + rows if row + rows < height else None)
            if sieving:
                fitted, radius = _fit_tile(mask, core, sieve_pixels, allowance)
                smoothing = max(smoothing, radius)
                _sort_tile_polygons(polygonize_mask(fitted, cells), shared, sieved)
            if keep_plain:
                fitted, radius = _fit_tile(mask, core, 0, allowance)
                _sort_tile_polygons(polygonize_mask(fitted, cells), shared, plain)
                # Both conditions only grow: the unsieved polygons can no longer be the result.
                if sieving and kept >= SIEVE_MIN_KEPT_PIXELS and (sieved[0] or sieved[1]):
                    keep_plain, plain = False, ([], [])
                else:
                    smoothing = max(smoothing, radius)
        if progress is not None:
            progress(85.0 * (number + 1) / len(tiles))
    # The sieve removes the speckle of a large selection, which would make
    # countless polygons. A small one (a rare class, a narrow range) is kept as
    # it is, and the sieve never empties a selection.
    geometry = merge_tile_polygons(*(plain if keep_plain else sieved))
    geometry = _within_budget(geometry, max_vertices)
    if progress is not None:
        progress(95.0)
    geometry = make_valid(pixel_to_map(geometry, (extent.xMinimum(), cell_x, 0.0, extent.yMaximum(), 0.0, -cell_y)))
    if progress is not None:
        progress(100.0)
    vertices = geometry.constGet().nCoordinates() if not geometry.isEmpty() else 0
    return SelectionGeometryResult(geometry, kept, width * height, max(cell_x, cell_y), grid=(width, height),
                                   tiles=len(tiles), coarse=coarse, decimation=k, smoothing=smoothing, vertices=vertices)


def _within_budget(geometry, max_vertices: int, cell: float = 1.0):
    """``geometry`` simplified, keeping its patches, until it holds ``max_vertices`` vertices.

    ``cell``: size of a cell in the units of ``geometry`` (1 in cell coordinates).

    The tiles already fit their share: this only catches what the smoothing
    cannot merge (many isolated patches). Deterministic; logged when it stays over.
    """
    from .geometry_tools import make_valid
    if geometry.isEmpty() or geometry.constGet().nCoordinates() <= max_vertices:
        return geometry
    for tolerance in _SIMPLIFY_TOLERANCES:
        simplified = geometry.simplify(tolerance * cell)  # topology preserving: no patch collapses
        if simplified is not None and not simplified.isEmpty():
            geometry = make_valid(simplified)
        if geometry.constGet().nCoordinates() <= max_vertices:
            return geometry
    logger.info(f"⏱ [FM5] raster selection: {geometry.constGet().nCoordinates()} vertices left over the budget of "
                f"{max_vertices} (isolated patches are kept)")
    return geometry


def _sort_tile_polygons(polygons, shared, into) -> None:
    """Append ``polygons`` (cell coordinates) to ``into[1]`` when they touch a ``shared`` edge, ``into[0]`` otherwise.

    ``shared``: ``(left, right, top, bottom)`` cell coordinate of each tile edge
    shared with another tile, None for the border of the raster.
    """
    left, right, top, bottom = shared
    for polygon in polygons:
        box = polygon.boundingBox()
        on_edge = (box.xMinimum() == left or box.xMaximum() == right
                   or box.yMinimum() == top or box.yMaximum() == bottom)
        into[1 if on_edge else 0].append(polygon)


# --- object detection (pipette) --------------------------------------------

# Half side, in native pixels, of the first window read around a click: 257 x 257
# pixels, 64 m on a 25 cm orthophoto, which holds a pool or a house.
OBJECT_WINDOW_START = 128
# Largest half side: a 1025 x 1025 window, 256 m on a 25 cm orthophoto. Read on the
# main thread at each click: a patch that runs over a field (a tolerance too wide)
# takes 4 s at 2049 x 2049 on QGIS 4.2, 1 to 2 s here; it is cut and the panel says so.
OBJECT_WINDOW_MAX = 512
# The window grows four times at each step: 257, then 1025 pixels; two reads at most.
OBJECT_WINDOW_GROWTH = 4


def flood_fill(mask, seeds):
    """Cells of ``mask`` 4-connected to one of ``seeds`` (``(row, col)``), as a boolean grid.

    A scanline fill: each run of a row is filled at once and gives one seed per
    run of the rows above and below, so the work follows the number of runs, not
    of pixels. 4-connected: two patches touching by a corner stay apart (a pool
    and the lawn beside it). A seed outside the grid or on a dropped cell fills nothing.
    """
    import numpy as np
    mask = np.asarray(mask, dtype=bool)
    rows, cols = mask.shape
    filled = np.zeros_like(mask)
    stack = [(int(row), int(col)) for row, col in seeds if 0 <= row < rows and 0 <= col < cols]
    while stack:
        row, col = stack.pop()
        if not mask[row, col] or filled[row, col]:
            continue
        line = mask[row]
        stops = np.flatnonzero(~line[:col])
        left = int(stops[-1]) + 1 if stops.size else 0
        stops = np.flatnonzero(~line[col:])
        right = col + int(stops[0]) if stops.size else cols
        filled[row, left:right] = True
        for other in (row - 1, row + 1):
            if 0 <= other < rows:
                free = mask[other, left:right] & ~filled[other, left:right]
                if free.any():
                    starts = np.flatnonzero(free & ~np.concatenate(([False], free[:-1])))
                    stack.extend((other, left + int(start)) for start in starts)
    return filled


def fill_holes(region):
    """``region`` with its holes filled: the cells it encloses (a ladder, a reflection in a pool)."""
    import numpy as np
    region = np.asarray(region, dtype=bool)
    rows, cols = region.shape
    border = [(0, col) for col in range(cols)] + [(rows - 1, col) for col in range(cols)]
    border += [(row, 0) for row in range(rows)] + [(row, cols - 1) for row in range(rows)]
    outside = flood_fill(~region, border)
    return ~outside


def _object_window(extent: QgsRectangle, native_width: int, native_height: int, x: float, y: float, half: int):
    """Window of native pixels around ``(x, y)``: ``(rectangle, (col0, row0, col1, row1), (row, col))``.

    ``(row, col)`` is the clicked pixel in the window; None when the point is off the raster
    (its right and bottom edges belong to the last pixel, as for identify).
    """
    size_x, size_y = extent.width() / native_width, extent.height() / native_height
    if not (extent.xMinimum() <= x <= extent.xMaximum() and extent.yMinimum() <= y <= extent.yMaximum()):
        return None
    col = min(native_width - 1, int(math.floor((x - extent.xMinimum()) / size_x)))
    row = min(native_height - 1, int(math.floor((extent.yMaximum() - y) / size_y)))
    col0, col1 = max(0, col - half), min(native_width, col + half + 1)
    row0, row1 = max(0, row - half), min(native_height, row + half + 1)
    return _pixel_rectangle(extent, size_x, size_y, col0, row0, col1, row1), (col0, row0, col1, row1), (row - row0, col - col0)


def _pixel_rectangle(extent: QgsRectangle, size_x: float, size_y: float, col0: int, row0: int, col1: int, row1: int):
    return QgsRectangle(extent.xMinimum() + col0 * size_x, extent.yMaximum() - row1 * size_y,
                        extent.xMinimum() + col1 * size_x, extent.yMaximum() - row0 * size_y)


def _window_mask(provider, selection: RasterSelection, extent: QgsRectangle, size_x: float, size_y: float,
                 bounds: Tuple[int, int, int, int], native_width: int, native_height: int, crs_wkt: str):
    """Mask of ``selection`` over the window ``bounds``; a slope... is read with one more pixel around.

    Without it the pixels of the window border would see an extrapolated neighbourhood
    and could drop out of the range, stopping the patch one pixel short of the side.
    """
    col0, row0, col1, row1 = bounds
    if not selection.derivative.is_terrain:
        rectangle = _pixel_rectangle(extent, size_x, size_y, col0, row0, col1, row1)
        return _selection_mask_over(provider, selection, rectangle, col1 - col0, row1 - row0, crs_wkt)
    pad_col0, pad_row0 = max(0, col0 - 1), max(0, row0 - 1)
    pad_col1, pad_row1 = min(native_width, col1 + 1), min(native_height, row1 + 1)
    rectangle = _pixel_rectangle(extent, size_x, size_y, pad_col0, pad_row0, pad_col1, pad_row1)
    mask = _selection_mask_over(provider, selection, rectangle, pad_col1 - pad_col0, pad_row1 - pad_row0, crs_wkt)
    return mask[row0 - pad_row0:row0 - pad_row0 + row1 - row0, col0 - pad_col0:col0 - pad_col0 + col1 - col0]


def object_parts(selection: RasterSelection) -> List[Tuple[RasterSelection, Tuple[float, float]]]:
    """``(criterion, seed)`` of each object: its own criterion, else the one of the selection for every seed."""
    if selection.objects:
        return [(item, item.seeds[0]) for item in selection.objects]
    return [(selection, seed) for seed in selection.seeds]


def object_geometry(provider: QgsRasterDataProvider, selection: RasterSelection, extent: QgsRectangle,
                    native_width: int, native_height: int, crs_wkt: str, start: int = OBJECT_WINDOW_START,
                    limit: int = OBJECT_WINDOW_MAX, provider_for=None) -> SelectionGeometryResult:
    """Outline of the objects under the seeds of ``selection``: the patch of kept pixels each click falls in.

    Read at the native resolution in a window around each click, grown while
    the patch touches a side of the window that is not the raster edge, up to
    ``limit``: a patch still larger is cut at the window (``truncated``). The
    holes of an object are filled. A click on a dropped pixel gives no object, a
    click inside an object already found adds nothing.

    Args:
        provider_for: ``criterion -> provider`` for the objects of their own
            criterion (an expression is read through its own virtual raster);
            None: ``provider`` for every object.
    """
    import numpy as np
    from .geometry_tools import mask_to_geometry, union_geometries
    total = int(native_width) * int(native_height)
    if native_width <= 0 or native_height <= 0 or extent.width() <= 0 or extent.height() <= 0:
        return SelectionGeometryResult(QgsGeometry(), 0, max(0, total), 0.0)
    size_x, size_y = extent.width() / native_width, extent.height() / native_height
    geometries, kept, truncated = [], 0, False
    for criterion, (x, y) in object_parts(selection):
        if _inside_any(geometries, x, y):
            continue  # a second click on the same pool
        source = provider
        if provider_for is not None:
            source = provider_for(criterion)
            if source is None:
                continue  # its expression was refused by the raster calculator
        half = max(1, int(start))
        while True:
            window = _object_window(extent, native_width, native_height, x, y, half)
            if window is None:
                break
            _rectangle, bounds, (row, col) = window
            col0, row0, col1, row1 = bounds
            mask = _window_mask(source, criterion, extent, size_x, size_y, bounds, native_width, native_height, crs_wkt)
            region = flood_fill(mask, [(row, col)])
            if not region.any():
                break
            touches = ((row0 > 0 and region[0].any()) or (row1 < native_height and region[-1].any())
                       or (col0 > 0 and region[:, 0].any()) or (col1 < native_width and region[:, -1].any()))
            if touches and half < limit:
                half = min(limit, half * OBJECT_WINDOW_GROWTH)
                continue
            truncated = truncated or touches
            region = fill_holes(region)
            geotransform = (extent.xMinimum() + col0 * size_x, size_x, 0.0, extent.yMaximum() - row0 * size_y, 0.0, -size_y)
            geometry = mask_to_geometry(region, geotransform, crs_wkt, simplify_tolerance=min(size_x, size_y) * 0.5)
            if geometry is not None and not geometry.isEmpty():
                geometries.append(geometry)
                kept += int(np.count_nonzero(region))
            break
    if truncated:
        logger.info(f"[FM5] object detection: an object is larger than {2 * limit + 1} pixels, cut at the window read")
    geometry = union_geometries(geometries) if geometries else QgsGeometry()
    # Bounded like the tiled selection (a patch running over a field has a long outline).
    geometry = _within_budget(geometry, SOURCE_MAX_VERTICES, min(size_x, size_y))
    return SelectionGeometryResult(geometry, kept, total, max(size_x, size_y), truncated, len(geometries))


def _inside_any(geometries, x: float, y: float) -> bool:
    """Whether ``(x, y)`` falls in one of ``geometries`` (an object already found)."""
    for geometry in geometries:
        try:
            if geometry.contains(QgsPointXY(x, y)):
                return True
        except Exception:  # noqa: BLE001 - a geometry that cannot tell is not a hit
            continue
    return False


def object_virtual_layers(layer: QgsRasterLayer, selection: RasterSelection, source: Optional[str] = None,
                          provider: Optional[str] = None) -> Dict[str, Optional[QgsRasterLayer]]:
    """Virtual raster of each object expression of ``selection`` (main thread), by expression; None when refused."""
    layers: Dict[str, Optional[QgsRasterLayer]] = {}
    for criterion, _seed in object_parts(selection):
        if criterion.mode is RasterSelectionMode.EXPRESSION and criterion.expression not in layers:
            layers[criterion.expression] = selection_virtual_layer(layer, criterion, source, provider)
    return layers


def layer_object_geometry(layer: QgsRasterLayer, selection: RasterSelection) -> SelectionGeometryResult:
    """:func:`object_geometry` read from ``layer`` itself (main thread: the pipette shows what it detects)."""
    virtuals = object_virtual_layers(layer, selection)  # kept alive while their providers are read
    base = layer.dataProvider()

    def provider_for(criterion):
        if criterion.mode is not RasterSelectionMode.EXPRESSION:
            return base
        virtual = virtuals.get(criterion.expression)
        return virtual.dataProvider() if virtual is not None else None

    return object_geometry(base, selection, layer.extent(), layer.width(), layer.height(), layer.crs().toWkt(),
                           provider_for=provider_for)


# --- virtual rasters -------------------------------------------------------

def _virtual_parameters(layer: QgsRasterLayer, formula: str, reference: str,
                        source: Optional[str] = None, provider: Optional[str] = None):
    """Virtual raster parameters reading ``source`` (default: the layer's current source).

    The input entry is filled BEFORE it is put in ``rInputLayers``: sip returns
    a copy of that list, so editing ``params.rInputLayers[0]`` afterwards does
    nothing (verified on QGIS 4.2).
    """
    params = QgsRasterDataProvider.VirtualRasterParameters()
    params.crs = layer.crs()
    params.extent = layer.extent()
    params.width = layer.width()
    params.height = layer.height()
    params.formula = formula
    entry = QgsRasterDataProvider.VirtualRasterInputLayers()
    entry.name = reference
    entry.uri = source if source else layer.source()
    entry.provider = provider if provider else layer.providerType()
    params.rInputLayers = [entry]
    return params


_EMPTY_CRS = '%3Fcrs%26'


def _encode_virtual_uri(params) -> str:
    """``encodeVirtualRasterProviderUri`` that keeps a CRS without authority id.

    A custom CRS (a GeoTIFF whose WKT matches no EPSG code) is written ``crs=``
    empty, and the virtual raster provider refuses the URI: its WKT is written
    instead, encoded once (verified on QGIS 4.2).
    """
    uri = QgsRasterDataProvider.encodeVirtualRasterProviderUri(params)
    crs = params.crs
    if crs.isValid() and not crs.authid() and uri.startswith(_EMPTY_CRS):
        uri = '%3Fcrs%3D' + quote(crs.toWkt(), safe='') + '%26' + uri[len(_EMPTY_CRS):]
    return uri


def raster_reference(layer: QgsRasterLayer) -> str:
    """Name used for ``layer`` in raster calculator formulas."""
    name = ''.join(c if c.isalnum() or c == '_' else '_' for c in layer.name()) or 'raster'
    return name


def selection_virtual_layer(layer: QgsRasterLayer, selection: RasterSelection,
                            source: Optional[str] = None, provider: Optional[str] = None) -> Optional[QgsRasterLayer]:
    """Virtual raster equal to 1 where ``selection`` keeps the pixel, 0 elsewhere (main thread)."""
    reference = raster_reference(layer)
    formula = selection.to_calc_formula(reference)
    uri = _encode_virtual_uri(_virtual_parameters(layer, formula, reference, source, provider))
    virtual = QgsRasterLayer(uri, f"{layer.name()}_selection", 'virtualraster')
    return virtual if virtual.isValid() else None


def selection_virtual_uri(layer_source: str, layer_provider: str, layer: QgsRasterLayer, selection: RasterSelection,
                          nodata: float = DEFAULT_NODATA) -> Tuple[str, Optional[float]]:
    """URI of a virtual raster keeping the selected pixels of band ``selection.band``.

    The formula is ``value / (condition)``: a pixel outside the selection is a
    division by zero, i.e. NaN, which statistics and renderers skip. A value
    written instead (``if(cond, value, -9999)``) is NOT seen as NoData by the
    virtual raster provider, even with a user NoData range (verified on QGIS 4.2).

    Args:
        layer_source: Source to read (the original one when the layer is already derived).
        layer_provider: Provider of ``layer_source``.
        layer: Layer giving CRS, extent and size.
        selection: Pixels to keep.
        nodata: Unused, kept for compatibility.

    Returns:
        ``(uri, None)``: no NoData value to declare.
    """
    reference = raster_reference(layer)
    condition = selection.to_calc_formula(reference)
    value = f'"{reference}@{selection.band}"'
    formula = f"{value} / ( {condition} )"
    params = _virtual_parameters(layer, formula, reference, layer_source, layer_provider)
    return _encode_virtual_uri(params), None


def set_user_nodata(layer: QgsRasterLayer, nodata: Optional[float]) -> None:
    """Declare (or clear) a user NoData value on band 1 of ``layer``."""
    from qgis.core import QgsRasterRange
    provider = layer.dataProvider()
    for band in range(1, layer.bandCount() + 1):
        provider.setUserNoDataValue(band, [QgsRasterRange(nodata, nodata)] if nodata is not None else [])


# --- live preview of a selection (EXPLORING) -------------------------------

_PREVIEW_PROPERTY = 'filtermate/preview_transparency'


def _transparent_pixel(low: float, high: float, include_min: bool, include_max: bool):
    """A fully transparent value range, for both TransparentSingleValuePixel APIs.

    QGIS >= 3.30 takes an *opacity* in [0, 1]; older versions a *percent
    transparent* in [0, 100] (set as an attribute, the old struct has no
    5-argument constructor).
    """
    from qgis.core import QgsRasterTransparency
    pixel_cls = QgsRasterTransparency.TransparentSingleValuePixel
    try:
        pixel = pixel_cls(float(low), float(high), 0.0, bool(include_min), bool(include_max))
        if hasattr(pixel, 'opacity'):
            return pixel
    except TypeError:
        pixel = pixel_cls()
    pixel.min = float(low)
    pixel.max = float(high)
    if hasattr(pixel, 'opacity'):
        pixel.opacity = 0.0
    else:
        pixel.percentTransparent = 100.0
    if hasattr(pixel, 'includeMinimum'):
        pixel.includeMinimum = bool(include_min)
        pixel.includeMaximum = bool(include_max)
    return pixel


def pixel_is_transparent(pixel) -> bool:
    """True for a fully transparent range (either API)."""
    if hasattr(pixel, 'opacity'):
        return float(pixel.opacity) <= 0.0
    return float(getattr(pixel, 'percentTransparent', 0.0)) >= 100.0


def _bound_step(value: float) -> float:
    """Gap left between a kept value and a transparent range whose bounds are inclusive.

    Above the absolute tolerance QGIS compares bounds with (4 double
    epsilons, about 8.9e-16) and below the relative spacing of Float32
    pixel values (about 6e-8), small values (0.001, 1e-5) included.
    """
    return max(abs(value) * 1e-12, 1e-14)


def preview_ranges(selection: RasterSelection, exclusive_bounds: bool = True) -> List[Tuple[float, float, bool, bool]]:
    """Value ranges a RANGE / CLASSES preview makes transparent: ``(low, high, include_low, include_high)``.

    No kept value may fall in one. A range bound next to a kept value is
    exclusive; ``exclusive_bounds`` False (QGIS < 3.30: no ``includeMinimum``
    / ``includeMaximum``, ranges inclusive on both sides) moves it off the
    kept value instead. A class keeps the values that round to it, like the
    filter (:func:`selection_mask`): the gaps between classes start and end
    at half values, which an integer pixel never takes. The outer ranges are
    unbounded: band statistics are sampled and miss pixels.
    """
    low, high = -sys.float_info.max, sys.float_info.max
    gaps = []
    if selection.mode is RasterSelectionMode.RANGE:
        if selection.minimum is not None:
            gaps.append((low, selection.minimum, True, False))
        if selection.maximum is not None:
            gaps.append((selection.maximum, high, False, True))
    elif selection.mode is RasterSelectionMode.CLASSES:
        start, include_start = low, True
        for value in sorted(selection.classes):
            gaps.append((start, value - 0.5, include_start, False))
            start, include_start = value + 0.5, False
        gaps.append((start, high, include_start, True))
    ranges = []
    for start, end, include_start, include_end in gaps:
        if not exclusive_bounds:
            if not include_start:
                start += _bound_step(start)
            if not include_end:
                end -= _bound_step(end)
            include_start = include_end = True
        if start < end or (start == end and include_start and include_end):
            ranges.append((start, end, include_start, include_end))
    return ranges


def apply_selection_preview(layer: QgsRasterLayer, selection: RasterSelection,
                            data_min: Optional[float] = None, data_max: Optional[float] = None) -> bool:
    """Make the pixels outside a RANGE / CLASSES selection transparent in the renderer.

    The previous transparency settings are kept on the layer and restored by
    :func:`clear_selection_preview`; meanwhile they still apply to the kept
    pixels. A selection the preview cannot show (empty, raster calculator
    expression) shows every pixel again. ``data_min`` / ``data_max`` are no
    longer used (the outer ranges are unbounded), kept for callers.
    """
    from qgis.core import QgsRasterTransparency
    renderer = layer.renderer()
    if (renderer is None or selection.is_empty or selection.mode is RasterSelectionMode.EXPRESSION
            or selection.derivative.is_terrain):
        # A derivative has no transparency ranges: the renderer only knows the pixel values.
        clear_selection_preview(layer)
        return False
    saved = layer.customProperty(_PREVIEW_PROPERTY)
    if saved is None:
        saved = _transparency_to_list(renderer.rasterTransparency())
        layer.setCustomProperty(_PREVIEW_PROPERTY, saved)
    transparency = QgsRasterTransparency()
    exclusive = hasattr(_transparent_pixel(0.0, 0.0, True, True), 'includeMinimum')  # QGIS >= 3.30
    pixels = [_transparent_pixel(*gap) for gap in preview_ranges(selection, exclusive)]
    # QGIS uses the first range holding a value: the preview first (hidden is hidden), then the
    # ranges of the user, which keep applying to the kept pixels (a NoData-like value stays transparent).
    transparency.setTransparentSingleValuePixelList(pixels + _pixels_from_list(saved))
    renderer.setRasterTransparency(transparency)
    layer.triggerRepaint()
    return True


def _transparency_to_list(transparency) -> list:
    """Serializable copy of the single value pixel list (both APIs)."""
    if transparency is None:
        return []
    items = []
    try:
        for pixel in transparency.transparentSingleValuePixelList():
            if hasattr(pixel, 'opacity'):
                level = ['opacity', float(pixel.opacity)]
            else:
                level = ['percent', float(pixel.percentTransparent)]
            items.append([float(pixel.min), float(pixel.max), level[0], level[1],
                          bool(getattr(pixel, 'includeMinimum', True)), bool(getattr(pixel, 'includeMaximum', True))])
    except Exception as exc:
        logger.debug(f"[FM5] raster transparency not saved: {exc}")
        return []
    return items


def _pixels_from_list(saved) -> list:
    """Pixels of a :func:`_transparency_to_list` copy (either API)."""
    pixels = []
    for item in saved or []:
        try:
            low, high, kind, level, include_min, include_max = item
            pixel = _transparent_pixel(low, high, include_min, include_max)
            if hasattr(pixel, 'opacity'):
                pixel.opacity = float(level) if kind == 'opacity' else 1.0 - float(level) / 100.0
            else:
                pixel.percentTransparent = float(level) if kind == 'percent' else (1.0 - float(level)) * 100.0
            pixels.append(pixel)
        except (TypeError, ValueError):
            continue
    return pixels


def clear_selection_preview(layer: QgsRasterLayer) -> bool:
    """Restore the transparency saved by :func:`apply_selection_preview`."""
    from qgis.core import QgsRasterTransparency
    saved = layer.customProperty(_PREVIEW_PROPERTY)
    if saved is None:
        return False
    renderer = layer.renderer()
    if renderer is not None:
        transparency = QgsRasterTransparency()
        transparency.setTransparentSingleValuePixelList(_pixels_from_list(saved))
        renderer.setRasterTransparency(transparency)
        layer.triggerRepaint()
    layer.removeCustomProperty(_PREVIEW_PROPERTY)
    return True


# === EXPLORING tools: zoom to the selected range, range linked to the style ===

def mask_bounds(mask) -> Optional[Tuple[int, int, int, int]]:
    """``(first_row, last_row, first_col, last_col)`` of the True cells, None when there is none."""
    import numpy as np
    rows = np.flatnonzero(np.any(mask, axis=1))
    if rows.size == 0:
        return None
    cols = np.flatnonzero(np.any(mask, axis=0))
    return int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])


def selection_extent(layer: QgsRasterLayer, selection: RasterSelection, max_pixels: int = 262144) -> Optional[QgsRectangle]:
    """Extent (layer CRS) of the pixels kept by a RANGE / CLASSES selection, read on a coarse grid.

    None when no pixel is kept or the selection is an expression.
    """
    if selection is None or selection.is_empty or selection.mode is RasterSelectionMode.EXPRESSION:
        return None
    extent = layer.extent()
    if selection.derivative.is_terrain:
        max_pixels = max(max_pixels, 1000000)  # the grid of the histogram: a slope depends on the pixel size
    width, height = _grid_for(extent, layer.width(), layer.height(), max_pixels)
    array = read_band_array(layer.dataProvider(), selection.band, extent, width, height)
    array = derived_array(array, selection.derivative, extent, crs_kind(layer.crs()))
    bounds = mask_bounds(selection_mask(array, selection))
    if bounds is None:
        return None
    first_row, last_row, first_col, last_col = bounds
    size_x, size_y = extent.width() / width, extent.height() / height
    return QgsRectangle(extent.xMinimum() + first_col * size_x, extent.yMaximum() - (last_row + 1) * size_y,
                        extent.xMinimum() + (last_col + 1) * size_x, extent.yMaximum() - first_row * size_y)


def rescale_values(values: List[float], old_min: float, old_max: float, low: float, high: float) -> List[float]:
    """Values moved linearly from ``[old_min, old_max]`` to ``[low, high]`` (colour ramp stops)."""
    span = old_max - old_min
    if span == 0:
        return [low + (high - low) * index / max(1, len(values) - 1) for index in range(len(values))]
    return [low + (value - old_min) / span * (high - low) for value in values]


_LINKED_RENDERERS: Dict[str, object] = {}  # layer id -> copy of the style before the link
_STRETCHED: Dict[str, int] = {}  # layer id -> address of the renderer the link stretched
_SAVE_HOOKED: List[object] = []  # projects whose writeMapLayer writes the original style back


def _address(renderer) -> int:
    """Identity of the C++ renderer behind a wrapper (a style set from the style panel is another one)."""
    try:
        from qgis.PyQt import sip
        return int(sip.unwrapinstance(renderer))
    except Exception:
        return id(renderer)


def _renderer_band(renderer) -> Optional[int]:
    """Band a single band style reads; None when the renderer does not tell."""
    for name in ('inputBand', 'grayBand', 'band'):
        method = getattr(renderer, name, None)
        if callable(method):
            try:
                return int(method())
            except (TypeError, ValueError, RuntimeError):
                continue  # not a band number on this renderer: try the next accessor
    return None


def link_range_to_style(layer: QgsRasterLayer, band: int, low: float, high: float) -> bool:
    """Stretch the layer style over ``[low, high]``: grey contrast or pseudocolour ramp stops.

    The first call keeps a copy of the renderer, restored by :func:`unlink_range_from_style`
    and written in a saved project instead of the stretched one. A style changed by the user
    since (style panel) becomes the one kept. Returns False for a renderer that has no single
    band range (multiband, paletted, ...) or that reads another band than ``band``.
    """
    renderer = layer.renderer()
    if renderer is None or low is None or high is None or high <= low:
        return False
    kind = renderer.type()
    if kind not in ('singlebandgray', 'singlebandpseudocolor'):
        return False
    style_band = _renderer_band(renderer)
    if band is not None and style_band is not None and style_band != int(band):
        return False  # the range is in the units of another band
    if layer.id() not in _LINKED_RENDERERS or _STRETCHED.get(layer.id()) != _address(renderer):
        _LINKED_RENDERERS[layer.id()] = renderer.clone()
        _hook_project_save()
    try:
        if kind == 'singlebandgray':
            enhancement = renderer.contrastEnhancement()
            if enhancement is None:
                return False
            enhancement.setMinimumValue(low)
            enhancement.setMaximumValue(high)
        else:
            shader_function = renderer.shader().rasterShaderFunction() if renderer.shader() else None
            if shader_function is None:
                return False
            items = shader_function.colorRampItemList()
            old_min, old_max = shader_function.minimumValue(), shader_function.maximumValue()
            for item, value in zip(items, rescale_values([item.value for item in items], old_min, old_max, low, high)):
                item.value = value
            shader_function.setColorRampItemList(items)
            shader_function.setMinimumValue(low)
            shader_function.setMaximumValue(high)
            renderer.setClassificationMin(low)
            renderer.setClassificationMax(high)
    except Exception as exc:
        logger.debug(f"[FM5] range not linked to the style: {exc}")
        return False
    _STRETCHED[layer.id()] = _address(renderer)
    layer.triggerRepaint()
    return True


def _hook_project_save() -> None:
    from qgis.core import QgsProject
    project = QgsProject.instance()
    if any(hooked is project for hooked in _SAVE_HOOKED):
        return
    project.writeMapLayer.connect(_write_original_style)
    _SAVE_HOOKED.append(project)


def _unhook_project_save() -> None:
    while _SAVE_HOOKED:
        project = _SAVE_HOOKED.pop()
        try:
            project.writeMapLayer.disconnect(_write_original_style)
        except (TypeError, RuntimeError):
            pass


def _write_original_style(layer, element, document) -> None:
    """A saved project keeps the style of a linked raster as it was before the link.

    The written ``<rasterrenderer>`` is replaced by the kept copy; what other hooks or the
    selection preview put on it (alpha band, transparency) stays, as when unlinking.
    """
    try:
        saved = _LINKED_RENDERERS.get(layer.id())
        if saved is None or _STRETCHED.get(layer.id()) != _address(layer.renderer()):
            return  # not linked, or a style set by the user since: written as it is
        pipe = element.firstChildElement('pipe')
        written = pipe.firstChildElement('rasterrenderer')
        if written.isNull():
            return
        saved.writeXml(document, pipe)
        original = pipe.lastChildElement('rasterrenderer')
        if original.isNull() or original == written:
            return
        if written.hasAttribute('alphaBand'):
            original.setAttribute('alphaBand', written.attribute('alphaBand'))
        transparency = written.firstChildElement('rasterTransparency')
        if not transparency.isNull():
            previous = original.firstChildElement('rasterTransparency')
            if not previous.isNull():
                original.removeChild(previous)
            original.appendChild(transparency.cloneNode(True))
        pipe.insertBefore(original, written)
        pipe.removeChild(written)
    except Exception as exc:
        logger.warning(f"[FM5] original style of a linked raster not written in the project: {exc}")


def is_style_linked(layer: QgsRasterLayer) -> bool:
    return layer is not None and layer.id() in _LINKED_RENDERERS


def unlink_range_from_style(layer: QgsRasterLayer) -> bool:
    """Give the layer back the style it had before :func:`link_range_to_style`."""
    saved = _LINKED_RENDERERS.pop(layer.id(), None) if layer is not None else None
    stretched = _STRETCHED.pop(layer.id(), None) if layer is not None else None
    if saved is None:
        return False
    current = layer.renderer()
    if current is not None and stretched is not None and _address(current) != stretched:
        return False  # the user set another style since the link: it stays
    transparency = current.rasterTransparency() if current is not None else None
    restored = saved.clone()
    if transparency is not None:
        # The selection preview lives in the transparency: keep it on the restored style.
        from qgis.core import QgsRasterTransparency
        copy = QgsRasterTransparency()
        copy.setTransparentSingleValuePixelList(transparency.transparentSingleValuePixelList())
        restored.setRasterTransparency(copy)
    layer.setRenderer(restored)
    layer.triggerRepaint()
    return True


def forget_linked_styles(layer_ids=None) -> None:
    """Drop the styles saved for layers removed from the project (every one when ``layer_ids`` is None).

    Never restored: a layer opened again with the same id has its own style.
    """
    if layer_ids is None:
        _LINKED_RENDERERS.clear()
        _STRETCHED.clear()
        return
    for layer_id in layer_ids:
        _LINKED_RENDERERS.pop(layer_id, None)
        _STRETCHED.pop(layer_id, None)


def unlink_all_styles(project=None) -> int:
    """Give every linked raster of the project its style back (plugin unloaded); returns how many."""
    from qgis.core import QgsProject
    project = project or QgsProject.instance()
    restored = 0
    for layer_id in list(_LINKED_RENDERERS):
        layer = project.mapLayer(layer_id)
        try:
            if layer is not None and unlink_range_from_style(layer):
                restored += 1
        except RuntimeError:
            pass
        _LINKED_RENDERERS.pop(layer_id, None)
        _STRETCHED.pop(layer_id, None)
    _unhook_project_save()
    return restored
