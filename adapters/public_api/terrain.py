# -*- coding: utf-8 -*-
"""Terrain for the agent: the elevation of an area brought in as a raster, contour lines drawn from a raster.

Main thread only, plain dicts out. What reads (the tiles of an elevation model over the network, the pixels of a
raster) runs in a worker thread while the event loop turns: QGIS stays alive and the Stop of the chat ends it. GDAL is
called in this process, with values this module builds: no command line, no text of a model in it. Each layer made is
added to the project, so undoing the turn of the chat removes it (``adapters/agent/turn_effects.py``).
"""
from __future__ import annotations

import logging
import math
import os
import shutil
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ...core.agent.elevation import (
    MAX_CONTOUR_PIXELS, MAX_PIXELS, ElevationSource, contour_problem, is_index, known, metric_grid, resolution_for,
    tile_url, tiles_for, utm_authid,
)
from ...core.agent.open_data import KIND_ELEVATION, megabytes, resolve_platform
from ...core.domain.layer_kind import LayerKind
from ..agent.bounded_http import STOPPED as HTTP_STOPPED, HttpFailure, fetch_together, on_abort
from .operations import layer_kind, resolve_layer, running

logger = logging.getLogger('FilterMate.Terrain')

TILE_TIMEOUT_MS = 20_000
READ_TIMEOUT_S = 240.0  # what one reading may last, whatever the network does
STOPPED = 'stopped'
_TOO_LONG = 'too long'
_MISSING = (403, 404)  # no tile there: open sea
_HTTP_OPTIONS = {
    'GDAL_HTTP_TIMEOUT': '60', 'GDAL_HTTP_CONNECTTIMEOUT': '15', 'GDAL_HTTP_LOW_SPEED_TIME': '20',
    'GDAL_HTTP_LOW_SPEED_LIMIT': '100', 'GDAL_HTTP_MAX_RETRY': '2', 'GDAL_HTTP_RETRY_DELAY': '1',
    # One file is asked, by its name: no listing of its folder, no file beside it.
    'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif',
    'GDAL_HTTP_USERAGENT': 'FilterMate-QGIS-plugin',
}
ELEVATION_FIELD = 'elevation'
INDEX_FIELD = 'is_index'
# A closed contour shorter than this many pixels is a bump or a pit of the size of a building: in a surface model
# they speckle every flat town. Measured on Lyon (2026-11-15, every 25 m): three contours in four, an eighth of
# their length.
SPECK_PIXELS = 10
CONTOUR_COLOR = '#7a5230'
CONTOUR_WIDTH = 0.2
INDEX_WIDTH = 0.5
_DSM_NOTE = ("a surface model: buildings and trees are in it, so a dense town or a forest stands above its ground; "
             "heights are metres above the EGM2008 geoid")


def _in_background(label: str, work: Callable[[Callable[[], str]], Any]) -> Any:
    """What ``work(ended)`` returns, run in a worker thread while the event loop turns.

    ``ended()`` answers "" while the work may go on, and why it must end once the user pressed Stop or it lasted too
    long: the work asks it often (the progress callbacks of GDAL) and gives up. Meanwhile the other operations of
    FilterMate are refused (``operations.busy_reason``).

    Raises:
        ValueError: Stopped, too long, or what the work raised as one.
    """
    from qgis.PyQt.QtCore import QEventLoop, QThread, QTimer
    stop = threading.Event()
    started = time.monotonic()
    outcome: Dict[str, Any] = {}

    def ended() -> str:
        if stop.is_set():
            return STOPPED
        return _TOO_LONG if time.monotonic() - started > READ_TIMEOUT_S else ''

    class Worker(QThread):
        def run(self):  # noqa: D102 - the thread
            try:
                outcome['result'] = work(ended)
            except BaseException as exc:  # noqa: BLE001 - raised again on the main thread
                outcome['error'] = exc

    worker = Worker()
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(lambda: loop.quit() if worker.isFinished() else None)
    forget = on_abort(stop.set)
    try:
        with running(label):
            worker.start()
            timer.start()
            while not worker.isFinished():
                loop.exec()
    finally:
        timer.stop()
        forget()
        stop.set()  # a loop left another way (QGIS closing): the work ends at its next step
        worker.wait()
    error = outcome.get('error')
    if isinstance(error, ValueError):
        raise error
    if error is not None:
        logger.error("%s failed: %r", label, error)
        raise ValueError(f"unexpected {type(error).__name__} (details in the FilterMate log)")
    return outcome.get('result')


class _Gdal:
    """GDAL in the thread that reads: its HTTP options and a quiet error handler, both of this thread alone."""

    def __init__(self, remote: bool) -> None:
        from osgeo import gdal
        self.gdal = gdal
        self._options = _HTTP_OPTIONS if remote else {}
        self._previous: Dict[str, Optional[str]] = {}

    def __enter__(self):
        for name, value in self._options.items():
            self._previous[name] = self.gdal.GetThreadLocalConfigOption(name)
            self.gdal.SetThreadLocalConfigOption(name, value)
        self.gdal.PushErrorHandler('CPLQuietErrorHandler')
        self.gdal.ErrorReset()
        return self.gdal

    def __exit__(self, *_: Any) -> None:
        self.gdal.PopErrorHandler()
        for name, value in self._previous.items():
            self.gdal.SetThreadLocalConfigOption(name, value)


def _said(gdal, exc: Optional[BaseException] = None) -> str:
    """What GDAL said of a failure, in one short line without the address read."""
    text = (str(exc) if exc is not None else '') or gdal.GetLastErrorMsg() or 'no reason given'
    return ' '.join(text.replace('/vsicurl/', '').split())[:300]


def _ended_error(reason: str) -> ValueError:
    return ValueError(STOPPED if reason == STOPPED else
                      f"it was not read in {int(READ_TIMEOUT_S)} s: ask for a smaller area or a coarser resolution")


def _canvas_crs():
    """The CRS of the map: of the canvas when QGIS has one here, of the project otherwise."""
    from qgis.core import QgsProject
    from .project_control import _iface
    iface = _iface()
    canvas = iface.mapCanvas() if iface is not None else None
    return canvas.mapSettings().destinationCrs() if canvas is not None else QgsProject.instance().crs()


def _area_in_degrees(extent_wkt: str, crs: str) -> List[float]:
    """``[west, south, east, north]`` of the area asked: a WKT in ``crs`` (the CRS of the map by default), or the
    visible map.

    Raises:
        ValueError: A WKT or a CRS that cannot be read, no map here, an area that is a point or off the globe.
    """
    from qgis.core import (
        QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCsException, QgsGeometry, QgsProject,
    )
    from .project_control import _canvas
    if (extent_wkt or '').strip():
        geometry = QgsGeometry.fromWkt(extent_wkt)
        if geometry.isNull() or geometry.isEmpty():
            raise ValueError("the WKT of the area could not be read")
        rect = geometry.boundingBox()
        source = QgsCoordinateReferenceSystem(crs) if (crs or '').strip() else _canvas_crs()
        if not source.isValid():
            raise ValueError(f"unknown CRS {crs!r}")
    else:
        try:
            canvas = _canvas()
        except ValueError:
            raise ValueError("give the area as extent_wkt with its crs: QGIS has no map here") from None
        rect, source = canvas.extent(), canvas.mapSettings().destinationCrs()
    if not all(math.isfinite(value) for value in (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())):
        raise ValueError("the area cannot be read")
    try:
        rect = QgsCoordinateTransform(source, QgsCoordinateReferenceSystem('EPSG:4326'), QgsProject.instance()) \
            .transformBoundingBox(rect)
    except QgsCsException:
        raise ValueError("this area cannot be expressed in longitude and latitude") from None
    bbox = [max(rect.xMinimum(), -180.0), max(rect.yMinimum(), -90.0), min(rect.xMaximum(), 180.0),
            min(rect.yMaximum(), 90.0)]
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise ValueError("the area is a point or a line: give an extent, such as the extent_wkt of find_place or of "
                         "map_context")
    return bbox


def _grid_crs(target_crs: str, bbox: Sequence[float]):
    """The CRS the elevation is written in: the one asked, the one of the project when it keeps distances in metres,
    else the UTM zone of the area.

    Raises:
        ValueError: A CRS asked that QGIS does not know, or that is not in metres.
    """
    from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsUnitTypes

    def in_metres(crs) -> bool:
        return (crs.isValid() and not crs.isGeographic()
                and crs.mapUnits() == QgsUnitTypes.DistanceUnit.DistanceMeters)

    text = (target_crs or '').strip()
    if text:
        asked = QgsCoordinateReferenceSystem(f"EPSG:{text}" if text.isdigit() else text)
        if not asked.isValid():
            raise ValueError(f"{text!r} is no CRS QGIS knows: give an authid such as EPSG:2154 or EPSG:32631")
        if not in_metres(asked):
            raise ValueError(f"{asked.authid() or text} is not in metres: elevation is written on a grid in metres "
                             "(a UTM zone, a national grid), which slopes, shading and contours need; leave "
                             "target_crs out for the UTM zone of the area")
        return asked
    project = QgsProject.instance().crs()
    if metric_grid(project.authid(), not project.isGeographic(), in_metres(project)):
        return project
    return QgsCoordinateReferenceSystem(utm_authid((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0))


def _grid(bbox: Sequence[float], crs, resolution: float) -> Tuple[Tuple[float, float, float, float], int, int]:
    """The bounds of the area in ``crs``, on whole pixels of ``resolution``, and its size in pixels.

    Raises:
        ValueError: An area that cannot be shown in this CRS, or a grid too large once there.
    """
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCsException, QgsProject, QgsRectangle
    try:
        rect = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), crs, QgsProject.instance()) \
            .transformBoundingBox(QgsRectangle(bbox[0], bbox[1], bbox[2], bbox[3]))
    except QgsCsException:
        raise ValueError(f"this area cannot be shown in {crs.authid() or 'this CRS'}") from None
    bounds = (math.floor(rect.xMinimum() / resolution) * resolution, math.floor(rect.yMinimum() / resolution) * resolution,
              math.ceil(rect.xMaximum() / resolution) * resolution, math.ceil(rect.yMaximum() / resolution) * resolution)
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError(f"this area cannot be shown in {crs.authid() or 'this CRS'}")
    width = int(round((bounds[2] - bounds[0]) / resolution))
    height = int(round((bounds[3] - bounds[1]) / resolution))
    if width < 2 or height < 2:
        raise ValueError(f"the area is smaller than two pixels of {resolution:g} m: ask for a larger one")
    if width * height > 2 * MAX_PIXELS:  # a CRS used far from where it is made for stretches the area
        raise ValueError(f"in {crs.authid() or 'this CRS'} this area makes a grid of {width} x {height} pixels: leave "
                         "target_crs out, or ask for a coarser resolution")
    return bounds, width, height


def _tiles_there(source: ElevationSource, tiles: Sequence[Tuple[int, int]]) -> List[str]:
    """The addresses of the tiles of ``tiles`` the server has: none over open sea.

    Raises:
        ValueError: The server did not answer, or answered with an error.
    """
    urls = [tile_url(source, latitude, longitude) for latitude, longitude in tiles]
    replies = fetch_together([{'url': url, 'headers': {'Range': 'bytes=0-0'}, 'headers_only': True,
                               'timeout_ms': TILE_TIMEOUT_MS} for url in urls])
    found = []
    for url, reply in zip(urls, replies):
        if isinstance(reply, HttpFailure):
            if str(reply) == HTTP_STOPPED:
                raise ValueError(STOPPED)
            raise ValueError(f"the server of {source.title} did not answer: {reply}")
        if reply.status in (200, 206):
            found.append(url)
        elif reply.status not in _MISSING:
            raise ValueError(f"the server of {source.title} answered with an error ({reply.status})")
    return found


def _warp(urls: Sequence[str], path: str, crs_text: str, bounds: Sequence[float], resolution: float,
          ended: Callable[[], str]) -> Dict[str, Any]:
    """Read the part of the tiles the grid needs and write it at ``path``; its statistics. Worker thread."""
    with _Gdal(remote=True) as gdal:
        def progress(_done, _message, _data) -> int:
            return 0 if ended() else 1
        try:
            dataset = gdal.Warp(
                path, ['/vsicurl/' + url for url in urls], format='GTiff', dstSRS=crs_text, xRes=resolution,
                yRes=resolution, outputBounds=tuple(bounds), resampleAlg='bilinear', outputType=gdal.GDT_Float32,
                creationOptions=['COMPRESS=DEFLATE', 'PREDICTOR=3', 'TILED=YES'], callback=progress)
        except RuntimeError as exc:  # GDAL raises when the application turned its exceptions on
            dataset, failure = None, _said(gdal, exc)
        else:
            failure = '' if dataset is not None else _said(gdal)
        reason = ended()
        if reason:
            dataset = None
            raise _ended_error(reason)
        if dataset is None:
            raise ValueError(f"the elevation could not be read from its server: {failure}")
        try:
            minimum, maximum, mean, _deviation = dataset.GetRasterBand(1).ComputeStatistics(False)
        except RuntimeError:
            minimum = maximum = mean = float('nan')
        answer = {'width': dataset.RasterXSize, 'height': dataset.RasterYSize, 'minimum': minimum, 'maximum': maximum,
                  'mean': mean}
        dataset.FlushCache()
        dataset = None  # closes the file before QGIS opens it
        return answer


def _under_the_data(project, layer) -> None:
    """Put ``layer`` in the tree above the web images at the bottom, under everything else: elevation is a background
    for the data, and must not sit under an opaque basemap."""
    from .layer_style import _drawn_by_its_service
    root = project.layerTreeRoot()
    children = root.children()
    index = len(children)
    for child in reversed(children):
        node_layer = child.layer() if hasattr(child, 'layer') else None
        if node_layer is None or not _drawn_by_its_service(node_layer):
            break
        index -= 1
    project.addMapLayer(layer, False)
    root.insertLayer(index, layer)


def _rounded(value: float, digits: int = 1) -> Optional[float]:
    return round(float(value), digits) if isinstance(value, (int, float)) and math.isfinite(value) else None


def add_elevation(platform: str = 'copernicus_dem', extent_wkt: str = '', crs: str = '',
                  resolution: Optional[float] = None, target_crs: str = '', name: str = '',
                  extra_domains: str = '') -> Dict[str, Any]:
    """Add the elevation of an area as a raster layer, read from an elevation model the user allowed.

    Only the part of each tile the area needs is read, warped on a grid in metres and written as one GeoTIFF in the
    QGIS profile, where the project finds it again. The layer goes under the data, above the web basemaps.

    Raises:
        ValueError: Not an elevation source, an area that cannot be read or is too large, no elevation there, a
            server that does not answer, stopped; the message says which.
    """
    from qgis.core import QgsApplication, QgsProject, QgsRasterLayer
    try:
        kind, _base = resolve_platform(platform, extra_domains)
    except ValueError:
        raise ValueError(f"{platform!r} is not an elevation source of the list") from None
    source = known(platform)
    if kind != KIND_ELEVATION or source is None:
        raise ValueError(f"{platform} holds no elevation model")
    bbox = _area_in_degrees(extent_wkt, crs)
    tiles = tiles_for(bbox)
    size, coarser = resolution_for(bbox, resolution, source.resolution)
    grid_crs = _grid_crs(target_crs, bbox)
    bounds, width, height = _grid(bbox, grid_crs, size)
    urls = _tiles_there(source, tiles)
    if not urls:
        raise ValueError(f"{source.title} has no elevation over this area: it is open sea, or off the model")
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), 'filtermate', 'open_data')
    folder = ''
    kept = False
    try:
        os.makedirs(root, exist_ok=True)
        folder = tempfile.mkdtemp(prefix='elevation-', dir=root)
        path = os.path.join(folder, f"{source.id}_{size:g}m.tif")
        crs_text = grid_crs.authid() or grid_crs.toWkt()
        read = _in_background('add_elevation', lambda ended: _warp(urls, path, crs_text, bounds, size, ended))
        title = (name or '').strip()[:200] or f"Elevation ({source.title.split(' (')[0]} {size:g} m)"
        layer = QgsRasterLayer(path, title, 'gdal')
        if not layer.isValid():
            del layer  # nothing more is read from an invalid layer
            raise ValueError("the elevation was read from its server but QGIS cannot open the file written")
        metadata = layer.metadata()
        metadata.setRights([source.attribution])
        layer.setMetadata(metadata)
        _under_the_data(QgsProject.instance(), layer)
        kept = True
    except OSError:
        raise ValueError("the elevation could not be written in the QGIS profile folder") from None
    finally:
        if folder and not kept:
            shutil.rmtree(folder, ignore_errors=True)
    notes = [note for note in (coarser, _DSM_NOTE) if note]
    if len(urls) < len(tiles):
        notes.append("part of the area is open sea, written at 0 m")
    return {'layer_id': layer.id(), 'name': layer.name(), 'platform': platform, 'crs_authid': grid_crs.authid(),
            'resolution': size, 'width': read['width'], 'height': read['height'],
            'minimum': _rounded(read['minimum']), 'maximum': _rounded(read['maximum']), 'mean': _rounded(read['mean']),
            'size': megabytes(os.path.getsize(path)) if os.path.isfile(path) else '',
            'attribution': source.attribution, 'note': '; '.join(notes)}


def check_elevation(platform: str, extra_domains: str = '') -> Dict[str, Any]:
    """Ask an elevation source the user allowed for the start of one of its tiles (the Test of the Sources tab).

    Raises:
        ValueError: Not an elevation source, or its server did not answer with a tile.
    """
    try:
        kind, _base = resolve_platform(platform, extra_domains)
    except ValueError:
        raise ValueError(f"{platform!r} is not an elevation source of the list") from None
    source = known(platform)
    if kind != KIND_ELEVATION or source is None:
        raise ValueError(f"{platform} holds no elevation model")
    if not _tiles_there(source, [(45, 4)]):  # Lyon: land in every model of the list
        raise ValueError(f"the server of {source.title} answers, but not with its tiles")
    return {'platform': platform, 'status': 200}


def _contours(source: str, band_number: int, path: str, interval: float, index_interval: Optional[float],
              min_length: Optional[float], remote: bool, ended: Callable[[], str]) -> Dict[str, Any]:
    """Draw the contour lines of a band into a new GeoPackage at ``path``; how many, and between which heights.
    ``min_length``: closed contours shorter than this are left out (None: ``SPECK_PIXELS`` pixels; 0: none).
    Worker thread."""
    with _Gdal(remote=remote) as gdal:
        from osgeo import ogr, osr
        try:
            dataset = gdal.Open(source)
        except RuntimeError as exc:
            dataset, failure = None, _said(gdal, exc)
        else:
            failure = '' if dataset is not None else _said(gdal)
        if dataset is None:
            raise ValueError(f"the raster could not be read: {failure}")
        band = dataset.GetRasterBand(band_number)
        reference = None
        if dataset.GetProjection():
            reference = osr.SpatialReference()
            reference.ImportFromWkt(dataset.GetProjection())
        vector = ogr.GetDriverByName('GPKG').CreateDataSource(path)
        if vector is None:
            raise ValueError("the contour layer could not be written")
        lines = vector.CreateLayer('contours', reference, ogr.wkbLineString)
        lines.CreateField(ogr.FieldDefn(ELEVATION_FIELD, ogr.OFTReal))
        lines.CreateField(ogr.FieldDefn(INDEX_FIELD, ogr.OFTInteger))
        options = [f"LEVEL_INTERVAL={interval!r}", 'LEVEL_BASE=0', 'ELEV_FIELD=0']
        nodata = band.GetNoDataValue()
        if nodata is not None and math.isfinite(nodata):
            options.append(f"NODATA={nodata!r}")

        def progress(_done, _message, _data) -> int:
            return 0 if ended() else 1
        try:
            code = gdal.ContourGenerateEx(band, lines, options=options, callback=progress)
        except RuntimeError as exc:
            code, failure = 1, _said(gdal, exc)
        else:
            failure = _said(gdal) if code else ''
        reason = ended()
        if reason:
            vector = None
            raise _ended_error(reason)
        if code:
            vector = None
            raise ValueError(f"the contours could not be drawn: {failure}")
        if min_length is None:
            transform = dataset.GetGeoTransform()
            min_length = SPECK_PIXELS * max(abs(transform[1]), abs(transform[5]))
        count = index_count = 0
        specks: List[int] = []  # removed once the reading is over: a layer is not changed under its own cursor
        lowest, highest = float('inf'), float('-inf')
        lines.StartTransaction()
        lines.ResetReading()
        for feature in lines:
            shape = feature.GetGeometryRef()
            if min_length > 0 and shape is not None and shape.Length() < min_length and shape.IsRing():
                specks.append(feature.GetFID())
                continue
            height = feature.GetField(ELEVATION_FIELD)
            flag = int(index_interval is not None and is_index(height, index_interval))
            feature.SetField(INDEX_FIELD, flag)
            lines.SetFeature(feature)
            count += 1
            index_count += flag
            lowest, highest = min(lowest, height), max(highest, height)
            reason = ended() if count % 2000 == 0 else ''
            if reason:
                lines.RollbackTransaction()
                vector = None
                raise _ended_error(reason)
        for fid in specks:
            lines.DeleteFeature(fid)
        lines.CommitTransaction()
        vector = None  # closes the file before QGIS opens it
        dataset = None
        return {'count': count, 'index_count': index_count, 'left_out': len(specks),
                'minimum': lowest if count else None, 'maximum': highest if count else None}


def _contour_style(layer, with_index: bool) -> None:
    """Thin brown lines, the index contours thicker: what a contour layer looks like before anyone styles it."""
    from qgis.core import QgsRuleBasedRenderer, QgsSingleSymbolRenderer
    from .layer_style import _color, _symbol
    if not with_index:
        layer.setRenderer(QgsSingleSymbolRenderer(_symbol(layer, _color(CONTOUR_COLOR), CONTOUR_WIDTH)))
        return
    root = QgsRuleBasedRenderer.Rule(None)
    root.appendChild(QgsRuleBasedRenderer.Rule(_symbol(layer, _color(CONTOUR_COLOR), INDEX_WIDTH), 0, 0,
                                               f'"{INDEX_FIELD}" = 1', 'Index contours'))
    root.appendChild(QgsRuleBasedRenderer.Rule(_symbol(layer, _color(CONTOUR_COLOR), CONTOUR_WIDTH), 0, 0, 'ELSE',
                                               'Contours', '', True))
    layer.setRenderer(QgsRuleBasedRenderer(root))


def contour_lines(layer: str, interval: float, index_interval: Optional[float] = None, band: int = 1,
                  name: str = '', min_length: Optional[float] = None) -> Dict[str, Any]:
    """Draw the contour lines of a raster of the project (an elevation model) as a new line layer.

    Each line has ``elevation`` (the height of its level) and ``is_index`` (1 for an index contour, a whole number
    of times ``index_interval``; 0 otherwise). The layer is a temporary GeoPackage added on top of the project,
    drawn in thin brown lines with the index contours thicker. Closed contours shorter than ``min_length`` (ten
    pixels of the raster by default; 0 keeps every line) are left out: the bumps of the size of a building.

    Raises:
        ValueError: Not a raster with values, a band it does not have, a raster too large, intervals that make no
            sense or too many levels, no contour between its heights, stopped.
    """
    from qgis.core import Qgis, QgsProcessingUtils, QgsProject, QgsRasterBandStats, QgsVectorLayer
    from .layer_style import _drawn_by_its_service
    found = resolve_layer(layer)
    if found is None:
        raise ValueError(f"layer {layer!r} not found")
    if not found.isValid():
        raise ValueError(f"'{found.name()}' is not available: its data source could not be opened")
    if layer_kind(found) is not LayerKind.RASTER or found.providerType() != 'gdal' or _drawn_by_its_service(found):
        raise ValueError(f"'{found.name()}' is not a raster with elevation values: contours are drawn from a raster "
                         "file (add_elevation brings one in)")
    band = int(band)
    if not 1 <= band <= found.bandCount():
        raise ValueError(f"'{found.name()}' has bands 1 to {found.bandCount()}")
    interval = float(interval)
    index_interval = float(index_interval) if index_interval is not None else None
    if min_length is not None and (not math.isfinite(float(min_length)) or float(min_length) < 0):
        raise ValueError("min_length is a length in the units of the raster, 0 to keep every contour")
    min_length = float(min_length) if min_length is not None else None
    if found.width() * found.height() > MAX_CONTOUR_PIXELS:
        raise ValueError(f"'{found.name()}' holds {found.width()} x {found.height()} pixels, more than the "
                         f"{MAX_CONTOUR_PIXELS // 1_000_000} million contours are drawn from: bring in a smaller "
                         "area (add_elevation) or a coarser raster")
    flags = getattr(getattr(Qgis, 'RasterBandStatistic', None), 'All', None)
    if flags is None:
        flags = QgsRasterBandStats.Stats.Min | QgsRasterBandStats.Stats.Max
    source = found.dataProvider().dataSourceUri()
    remote = source.lower().startswith(('/vsicurl/', 'http://', 'https://'))
    if remote:
        lowest = highest = float('nan')  # not read twice over the network: the levels are counted as they are made
    else:
        stats = found.dataProvider().bandStatistics(band, flags, found.extent(), 250000)
        lowest, highest = stats.minimumValue, stats.maximumValue
    problem = contour_problem(lowest, highest, interval, index_interval)
    if problem:
        raise ValueError(problem)
    path = QgsProcessingUtils.generateTempFilename('contours.gpkg')
    made = _in_background('contour_lines', lambda ended: _contours(source, band, path, interval, index_interval,
                                                                   min_length, remote, ended))
    if not made['count']:
        between = f" between {lowest:g} and {highest:g}" if math.isfinite(lowest) and math.isfinite(highest) else ''
        only_specks = (f" but {made['left_out']} closed ones too short to be kept (min_length 0 keeps them)"
                       if made['left_out'] else '')
        raise ValueError(f"no contour every {interval:g}{between}{only_specks}: ask for a smaller interval")
    title = (name or '').strip()[:200] or f"Contours {interval:g}"
    contours = QgsVectorLayer(path + '|layername=contours', title, 'ogr')
    if not contours.isValid():
        del contours
        raise ValueError("the contours were drawn but QGIS cannot open the layer written")
    _contour_style(contours, index_interval is not None)
    QgsProject.instance().addMapLayer(contours)
    return {'layer_id': contours.id(), 'name': contours.name(), 'source_layer': found.name(),
            'crs_authid': contours.crs().authid(), 'feature_count': made['count'], 'interval': interval,
            'index_interval': index_interval, 'index_count': made['index_count'], 'left_out': made['left_out'],
            'minimum': made['minimum'], 'maximum': made['maximum'], 'fields': [ELEVATION_FIELD, INDEX_FIELD]}
