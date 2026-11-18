# -*- coding: utf-8 -*-
"""Population for the agent: the people of an area brought in as a raster of people per pixel.

Main thread only, plain dicts out. The grid of the source is read by parts over the network in a worker thread
(``terrain._in_background``): QGIS stays alive and the Stop of the chat ends it. It is read on the grid of the source
and made coarser by whole blocks of pixels, summed, so that every total stays exact (``core/agent/population.py``).
GDAL is called in this process with values this module builds: no command line, no text of a model in it. The layer
made is added to the project, so undoing the turn of the chat removes it (``adapters/agent/turn_effects.py``).
"""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any, Callable, Dict, Optional, Sequence

from ...core.agent.elevation import quiet_message
from ...core.agent.open_data import KIND_POPULATION, megabytes, resolve_platform
from ...core.agent.population import (
    MAX_VRT_BYTES, NOT_COVERED, PopulationSource, area_problem, covered_rects, covered_share, exact_total_fits,
    extent_note, grid_for, grid_url, known, on_the_grid, resolution_label, snapped, vrt_geotransform,
)
from ...core.agent.osm import area_km2
from .operations import running
from .terrain import STOPPED, _Gdal, _area_in_degrees, _attempt, _ended_error, _in_background, _under_the_data

CRS = 'EPSG:4326'  # the grid of the source: a pixel written is a block of its pixels, never a part of one
_NOTE = ("total is the people of the rectangle around the area, not of a boundary: for the people inside "
         "polygons (a town, districts, an area around places), run_algorithm native:zonalstatisticsfb on them with "
         "this layer and STATISTICS [1] (sum). People estimated from a census and the buildings seen on satellite "
         "images (2015 to 2020 by country): say so before a number is taken as a census")
_MIN_GDAL = 3010000  # resampleAlg=sum: GDAL 3.1
_STRIP_PIXELS = 4_000_000  # what is summed at a time on the pixels of the source: 16 MB


def _population_source(platform: str, extra_domains: str) -> PopulationSource:
    try:
        kind, _base = resolve_platform(platform, extra_domains)
    except ValueError:
        raise ValueError(f"{platform!r} is not a population source of the list") from None
    source = known(platform)
    if kind != KIND_POPULATION or source is None:
        raise ValueError(f"{platform} holds no population grid")
    return source


def _vrt_text(gdal, url: str) -> str:
    """The text of the VRT at ``url``, read as a file: GDAL 3.4 opens every file a VRT names to write its text
    back (2026-11-15: 150 s for Lyon, 237 files over the network, against 3 s).

    Raises:
        ValueError: Its server did not answer with it, or with more than a VRT weighs.
    """
    gdal.ErrorReset()
    handle = gdal.VSIFOpenL('/vsicurl/' + url, 'rb')
    if handle is None:
        raise ValueError("the population grid could not be read from its server: "
                         + (quiet_message(gdal.GetLastErrorMsg()) or 'no answer'))
    try:
        data = gdal.VSIFReadL(1, MAX_VRT_BYTES + 1, handle) or b''
    finally:
        gdal.VSIFCloseL(handle)
    if not data:  # GDAL 3.4 opens an address its server answers 404 to, and reads nothing of it
        raise ValueError("the population grid could not be read from its server: "
                         + (quiet_message(gdal.GetLastErrorMsg()) or 'no answer'))
    if len(data) > MAX_VRT_BYTES:
        raise ValueError("the population grid sent by its server cannot be read as one")
    return data.decode('utf-8', 'replace')


def _grid_problem(gdal, url: str, source: PopulationSource, bounds: Sequence[float]) -> float:
    """The share of ``bounds`` the files of the grid fill, once its pixels are those this module counts on.

    Raises:
        ValueError: No answer, a grid whose pixels moved (every total would be wrong without a word), or a VRT that
            names a file that is not its own.
    """
    text = _vrt_text(gdal, url)
    left, step, _skew, top, _skew2, minus = vrt_geotransform(text)
    if not on_the_grid(source, left, top, step, minus):
        raise ValueError("the population grid has changed its pixels on its server: FilterMate must be updated to "
                         "read it")
    return covered_share(covered_rects(text), (left, top), step, bounds)


def _sum_pixels(gdal, url: str, bounds: Sequence[float], step: float, ended: Callable[[], str]) -> float:
    """The people of ``bounds`` (whole pixels of the source, ``step`` degrees), summed on those pixels as they are, by
    strips so that a large area is not held at once. Worker thread.

    Raises:
        ValueError: Stopped, too long, or a strip that cannot be read.
    """
    import numpy
    west, south, east, north = bounds
    width = max(1, int(round((east - west) / step)))
    height = max(1, int(round((north - south) / step)))
    rows = max(1, _STRIP_PIXELS // width)
    total = 0.0
    for first in range(0, height, rows):
        last = min(height, first + rows)
        strip = (west, north - last * step, east, north - first * step)
        dataset, failure = _attempt(gdal, lambda strip=strip: gdal.Warp(
            '', '/vsicurl/' + url, format='MEM', xRes=step, yRes=step, outputBounds=strip, resampleAlg='near',
            overviewLevel='NONE', outputType=gdal.GDT_Float32, dstNodata=float('nan'),
            callback=lambda _done, _message, _data: 0 if ended() else 1))
        reason = ended()
        if reason:
            raise _ended_error(reason)
        if dataset is None:
            raise ValueError(f"the population grid could not be read from its server: {failure}")
        try:
            values = dataset.GetRasterBand(1).ReadAsArray()
        except RuntimeError:  # GDAL raises once another plugin turned its exceptions on
            values = None
        dataset = None
        if values is None:
            raise ValueError("the population grid was read but its pixels cannot be")
        if numpy.isfinite(values).any():
            total += float(numpy.nansum(values, dtype='float64'))
    return total


def _read(url: str, path: str, bounds: Sequence[float], size: float, factor: int,
          ended: Callable[[], str], anyone: bool = True, source: Optional[PopulationSource] = None,
          count_bounds: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """Write the people of ``bounds`` to a GeoTIFF at ``path``, by pixels of ``size`` degrees (``factor`` x
    ``factor`` pixels of the source, summed); what it holds. Worker thread. ``anyone``: an area where nobody lives
    is refused (a grid that answers is enough for a Test). ``count_bounds``: the total is the people of these bounds,
    summed on the pixels of the source (the pixels written reach beyond the area asked, to whole blocks).

    Raises:
        ValueError: Stopped, too long, a grid that cannot be read, or no people at all in the area.
    """
    import numpy
    with _Gdal(tiles=True, extensions='.tif,.vrt') as gdal:
        dataset = None
        try:
            if int(gdal.VersionInfo()) < _MIN_GDAL:
                raise ValueError(f"the population needs GDAL 3.1 or later to sum pixels; this QGIS has GDAL "
                                 f"{gdal.__version__}")
            share = 1.0
            if source is not None:
                try:
                    share = _grid_problem(gdal, url, source, bounds)
                except RuntimeError as exc:  # GDAL raises once another plugin turned its exceptions on
                    raise ValueError("the population grid could not be read from its server: "
                                     + quiet_message(str(exc))) from None
                reason = ended()
                if reason:
                    raise _ended_error(reason)
                if share <= 0:
                    raise ValueError(NOT_COVERED)
            dataset, failure = _attempt(gdal, lambda: gdal.Warp(
                path, '/vsicurl/' + url, format='GTiff', xRes=size, yRes=size, outputBounds=tuple(bounds),
                # The pixels of the source as they are: its overviews are averages, never sums.
                resampleAlg='sum' if factor > 1 else 'near', overviewLevel='NONE', outputType=gdal.GDT_Float32,
                dstNodata=float('nan'), creationOptions=['COMPRESS=DEFLATE', 'PREDICTOR=3', 'TILED=YES'],
                callback=lambda _done, _message, _data: 0 if ended() else 1))
            reason = ended()  # a request cut by a Stop is a Stop, not a grid that cannot be read
            if reason:
                raise _ended_error(reason)
            if dataset is None:
                raise ValueError(f"the population grid could not be read from its server, or written here: {failure}")
            try:
                values = dataset.GetRasterBand(1).ReadAsArray()
            except RuntimeError:  # GDAL raises once another plugin turned its exceptions on
                values = None
            if values is None:
                raise ValueError("the population grid was read but its pixels cannot be")
            filled = bool(numpy.isfinite(values).any())
            total = float(numpy.nansum(values, dtype='float64')) if filled else 0.0
            maximum = float(numpy.nanmax(values)) if filled else 0.0
            exact = count_bounds is not None
            if exact and factor > 1:  # at the pixels of the source, the layer is already the people of the bounds
                try:
                    total = _sum_pixels(gdal, url, count_bounds, size / factor, ended)
                except ValueError:
                    # The layer is written: a second reading that fails or lasts too long leaves its own sum as the
                    # total, said as such, rather than losing it. A Stop is a Stop.
                    if ended() == STOPPED:
                        raise
                    exact = False
            if total <= 0 and anyone:
                raise ValueError("the population grid holds no people in this area (sea, or nobody lives there)")
            answer = {'width': dataset.RasterXSize, 'height': dataset.RasterYSize, 'total': total,
                      'maximum': maximum, 'covered': share, 'exact': exact}
            dataset.FlushCache()
            return answer
        finally:
            dataset = None  # closes the file before QGIS opens it, or before it is removed


def add_population(platform: str = 'meta_population', extent_wkt: str = '', crs: str = '',
                   resolution: Optional[float] = None, name: str = '', extra_domains: str = '') -> Dict[str, Any]:
    """Add the people of an area as a raster layer of people per pixel, read from a population grid the user
    allowed.

    ``resolution``: the size of a pixel in metres (default 100: the scale of a street; 1000 for a region); the finest
    is the source's. Written in EPSG:4326, on the grid of the source, as one GeoTIFF in the QGIS profile; the layer
    goes under the data, above the web basemaps.

    Raises:
        ValueError: Not a population source, an area that cannot be read or is too large, nobody there, a server
            that does not answer, stopped; the message says which.
    """
    from qgis.core import QgsApplication, QgsProject, QgsRasterLayer
    source = _population_source(platform, extra_domains)
    bbox = _area_in_degrees(extent_wkt, crs)
    problem = area_problem(bbox)
    if problem:
        raise ValueError(problem)
    factor, bounds, _width, _height, coarser = grid_for(source, bbox, resolution)
    # The pixels written are blocks of the grid of the source around the area: their sum is that of a larger
    # rectangle. The total is the people of the area asked, summed on the pixels of the source, when they fit in one
    # call; else it is that of the layer, and the answer gives the surface it covers.
    counted = tuple(snapped(source, bbox, 1)) if exact_total_fits(source, bbox) else None
    latitude = (bbox[1] + bbox[3]) / 2.0
    shown = resolution_label(source, factor, latitude)
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), 'filtermate', 'open_data')
    folder = ''
    kept = False
    try:
        with running('add_population'):  # from the first request: a call made meanwhile would run nested inside it
            os.makedirs(root, exist_ok=True)
            folder = tempfile.mkdtemp(prefix='population-', dir=root)
            path = os.path.join(folder, f"{source.id}_{factor}.tif")
            read = _in_background('add_population', lambda ended: _read(
                grid_url(source), path, bounds, source.step * factor, factor, ended, source=source,
                count_bounds=counted))
        title = (name or '').strip()[:200] or f"Population ({shown.replace('about ', '')})"
        layer = QgsRasterLayer(path, title, 'gdal')
        if not layer.isValid():
            del layer  # nothing more is read from an invalid layer
            raise ValueError("the population was read from its server but QGIS cannot open the file written")
        metadata = layer.metadata()
        metadata.setRights([source.attribution])
        layer.setMetadata(metadata)
        _under_the_data(QgsProject.instance(), layer)
        kept = True
    except OSError:
        raise ValueError("the population could not be written in the QGIS profile folder") from None
    finally:
        if folder and not kept:
            shutil.rmtree(folder, ignore_errors=True)
    summed = counted if read['exact'] else bounds
    return {'layer_id': layer.id(), 'name': layer.name(), 'platform': platform, 'crs_authid': CRS,
            'resolution': shown, 'width': read['width'], 'height': read['height'],
            'total': int(round(read['total'])), 'maximum': round(read['maximum'], 1),
            'size': megabytes(os.path.getsize(path)) if os.path.isfile(path) else '',
            'summed_bounds': [round(value, 6) for value in summed],
            'summed_km2': round(area_km2(summed), 2), 'asked_km2': round(area_km2(bbox), 2),
            'attribution': source.attribution,
            'note': '; '.join(note for note in (coarser, extent_note(source, bbox, bounds, factor, counted if read['exact'] else None),
                                                _outside(read), _NOTE) if note)}


def _outside(read: Dict[str, Any]) -> str:
    """What a model must know when a part of the area is out of the grid: its people are not counted."""
    share = read.get('covered', 1.0)
    if share >= 0.99:
        return ''
    return (f"about {100 * (1 - share):.0f} % of the area is outside the grid (a country it leaves out, or the "
            "sea): the people there are not counted")


def check_population(platform: str, extra_domains: str = '') -> Dict[str, Any]:
    """Ask a population source the user allowed for the people of a few pixels (the Test of the Sources tab).

    Raises:
        ValueError: Not a population source, or its server did not answer with its grid.
    """
    source = _population_source(platform, extra_domains)
    lyon = (4.835, 45.760, 4.840, 45.765)  # the centre of Lyon: people in every grid of the list
    factor, bounds, _width, _height, _note = grid_for(source, lyon, None)
    folder = tempfile.mkdtemp(prefix='filtermate-population-')
    try:
        with running('check_population'):
            _in_background('check_population', lambda ended: _read(
                grid_url(source), os.path.join(folder, 'check.tif'), bounds, source.step * factor, factor, ended,
                anyone=False, source=source))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return {'platform': platform, 'status': 200}
