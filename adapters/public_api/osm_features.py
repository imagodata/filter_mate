# -*- coding: utf-8 -*-
"""OpenStreetMap features for the agent: what carries the tags asked in an area, brought in as layers.

Main thread only, plain dicts out. The query is written by ``core/agent/osm.py`` from tags checked one by one, sent
to an Overpass server the user allowed, and its answer (OpenStreetMap XML) is held in memory, bounded in
size and in time and ended by Stop. GDAL reads it in a worker thread and the features that carry one of the
tags are kept in a GeoPackage in project memory, one layer per kind of geometry. Each layer made is added to the
project, so undoing the turn of the chat removes it (``adapters/agent/turn_effects.py``).
"""
from __future__ import annotations

import logging
import io
import os
from typing import Any, Callable, Dict, List, Sequence
from urllib.parse import quote

from ...core.agent.open_data import KIND_OVERPASS, megabytes, resolve_platform
from ..agent import data_store
from ...core.agent.osm import (
    ANOTHER as _ANOTHER, ATTRIBUTION, GEOMETRIES, LAYER_KINDS, MAX_BYTES, OSM_TYPES, Tag, area_problem, closed_way_is_area,
    columns, cut_problem, default_name, gdal_config, layer_title, matches, overpass_query, read_tags, remark_problem,
    status_problem, status_refusal, way_tags,
)
from ...core.agent.elevation import quiet_message
from ..agent.bounded_http import STOPPED as HTTP_STOPPED, TOO_LARGE, TOO_LONG, HttpFailure, fetch
from .operations import running
from .terrain import STOPPED, _Gdal, _area_in_degrees, _attempt, _ended_error, _in_background

logger = logging.getLogger('FilterMate.OsmFeatures')

REQUEST_TIMEOUT_MS = 90_000  # the server may think for 60 s, then sends its answer
CHECK_TIMEOUT_MS = 20_000
_ORDER = ('polygons', 'lines', 'points')  # added in this order: the points end on top, the areas under the lines
_FORM = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/osm3s+xml, application/xml'}
_NOT_WRITTEN = "the features could not be held in memory"
_TEMPORARY = "the answer could not be held in memory"


def _server(platform: str, extra_domains: str) -> str:
    """The address of an Overpass server the user allowed.

    Raises:
        ValueError: Not a platform of the list, or one of another kind.
    """
    try:
        kind, base = resolve_platform(platform, extra_domains)
    except ValueError:
        raise ValueError(f"{platform!r} is not an OpenStreetMap server of the list") from None
    if kind != KIND_OVERPASS:
        raise ValueError(f"{platform} is not an OpenStreetMap (Overpass) server")
    return base


def _ask(platform: str, url: str, query: str, path: str) -> None:
    """Send ``query`` to the server and copy its answer to ``path``.

    Raises:
        ValueError: Stopped, no answer, an error, an answer too large or cut short; the message names the platform as
            the model did, never its address.
    """
    received = [0]
    virtual = data_store.is_memory(path)
    with (data_store.store_for().writer(path) if virtual else open(path, 'wb')) as out:
        def keep(chunk: bytes) -> None:
            (out if virtual else out.write)(chunk)
            received[0] += len(chunk)
        try:
            reply = fetch(url, body=b'data=' + quote(query, safe='').encode('ascii'), headers=_FORM,
                          max_bytes=MAX_BYTES, timeout_ms=REQUEST_TIMEOUT_MS, sink=keep, decompress_freely=True)
        except HttpFailure as exc:
            if str(exc) == HTTP_STOPPED:
                raise ValueError(STOPPED) from None
            if str(exc) == TOO_LARGE:
                raise ValueError(f"the answer of {platform} weighs more than {megabytes(MAX_BYTES)}: ask for a smaller "
                                 "area, or for fewer tags") from None
            if str(exc) == TOO_LONG:
                raise ValueError(f"{platform} had not finished after {REQUEST_TIMEOUT_MS // 1000} s: ask for a smaller "
                                 f"area, or {_ANOTHER}") from None
            if 'written to disk' in str(exc):  # a full disk is no fault of the server
                raise ValueError(_TEMPORARY) from None
            raise ValueError(f"{platform} did not answer: {exc}; {_ANOTHER}") from None
    if status_problem(reply.status):
        raise ValueError(status_refusal(platform, reply.status))
    with (io.BytesIO(data_store.read_bytes(path)) if virtual else open(path, 'rb')) as stream:
        head = stream.read(600)
        stream.seek(max(0, received[0] - 4000))
        tail = stream.read()
    if b'<osm' not in head:
        raise ValueError(f"{platform} answered with something that is not OpenStreetMap data; {_ANOTHER}")
    problem = remark_problem(tail) or cut_problem(tail)
    if problem:
        raise ValueError(f"{platform}: {problem}")


def _as_point(shape, kind: str):
    """A point for a feature of any kind: itself, the middle of a line, a point inside an area."""
    if kind == 'points':
        return shape.Clone()
    if kind == 'lines':
        several = shape.GetGeometryName().upper().startswith('MULTI')
        parts = [shape.GetGeometryRef(index) for index in range(shape.GetGeometryCount())] if several else [shape]
        longest = max(parts, key=lambda part: part.Length(), default=None)
        return longest.Value(longest.Length() / 2.0) if longest is not None else None
    return shape.PointOnSurface()


def _quietly(call: Callable[[], Any]) -> Any:
    """What ``call`` returns; None when GDAL raises, which it does once another plugin turned its exceptions on."""
    try:
        return call()
    except RuntimeError:
        return None


def _convert(osm_path: str, config_path: str, gpkg_path: str, tags: Sequence[Tag], geometry: str,
             ended: Callable[[], str]) -> Dict[str, int]:
    """Write to a new GeoPackage the features of an OpenStreetMap file that carry one of ``tags``, one layer per
    kind of geometry; how many of each kind. Worker thread.

    Raises:
        ValueError: A file GDAL cannot read, or cannot read to its end (cut, or no XML): what was read before is
            a part of what was asked, never given as the whole. Or layers that cannot be written.
    """
    # The OSM driver's node index and SQLite geometry index must never spill into an OS temp directory.
    # Its temporary files use GDAL's virtual filesystem as well, in the private asset folder.
    options = {'CPL_TMPDIR': os.path.dirname(osm_path), 'OSM_MAX_TMPFILE_SIZE': '0'} \
        if data_store.is_memory(osm_path) else {}
    with _Gdal(options=options) as gdal:
        from osgeo import ogr, osr
        source = target = answer = feature = origin = definition = shape = row = out = made = None
        layers: Dict[str, Any] = {}
        pending = False
        try:
            source, failure = _attempt(gdal, lambda: gdal.OpenEx(
                osm_path, gdal.OF_VECTOR, open_options=[f"CONFIG_FILE={config_path}", 'INTERLEAVED_READING=YES']))
            if source is None:
                raise ValueError(f"the answer of the server could not be read: {failure}")
            target = ogr.GetDriverByName('GPKG').CreateDataSource(gpkg_path)
            if target is None:
                raise ValueError("the layers could not be written")
            reference = osr.SpatialReference()
            reference.ImportFromEPSG(4326)
            if hasattr(reference, 'SetAxisMappingStrategy'):
                reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)  # longitude first, as the file gives
            kept = columns(tags)
            written = ['osm_id', 'osm_type'] + kept + ['other_tags']
            shapes = {'points': ogr.wkbPoint, 'lines': ogr.wkbMultiLineString, 'polygons': ogr.wkbMultiPolygon}
            filled: Dict[str, Dict[str, int]] = {}
            counts = {kind: 0 for kind in shapes}

            def layer_of(kind: str):
                if kind not in layers:
                    new = target.CreateLayer(kind, reference, shapes[kind])
                    # The values are written by the place of their column: a column that could not be made would
                    # put every value after it in the wrong one.
                    if new is None or any(new.CreateField(ogr.FieldDefn(name, ogr.OFTString)) for name in written):
                        raise ValueError(_NOT_WRITTEN)
                    layers[kind], filled[kind] = new, {name: 0 for name in kept + ['other_tags']}
                return layers[kind]

            target.StartTransaction()
            pending = True
            read = 0
            while True:
                gdal.ErrorReset()
                try:
                    answer = source.GetNextFeature()
                    # Asked after every feature, not only after the last: GDAL tells that it could not read
                    # further on a call that still gives a feature, then gives those it had read and ends without
                    # a word (2026-11-15: a file broken at its node 29 990 gave 29 990 features and no error at
                    # its end). Measured that day in GDAL 3.4 and 3.12: a whole answer of 150 000 points, of
                    # 130 000 buildings or of shapes that are none (a bow tie, a ring left open) tells no error.
                    failure = gdal.GetLastErrorMsg() if gdal.GetLastErrorType() >= gdal.CE_Failure else ''
                except RuntimeError as exc:  # GDAL raises instead, once another plugin turned its exceptions on
                    failure = str(exc) or 'error'
                if failure:
                    raise ValueError("the answer of the server could not be read to its end: " + quiet_message(failure))
                feature, origin = (answer[0], answer[1]) if isinstance(answer, (list, tuple)) else (answer, None)
                if feature is None:
                    break
                read += 1
                reason = ended() if read % 200 == 0 else ''
                if reason:
                    raise _ended_error(reason)
                kind = LAYER_KINDS.get(origin.GetName() if origin is not None else '')
                shape = feature.GetGeometryRef()
                if kind is None or shape is None:
                    continue
                definition = feature.GetDefnRef()
                values = {name: feature.GetField(name) for name in kept + ['other_tags']
                          if definition.GetFieldIndex(name) >= 0}
                if not matches(tags, values):
                    continue
                if (geometry != 'lines' and kind == 'lines' and origin.GetName() == 'lines'
                        and _is_closed_ring(ogr, shape) and closed_way_is_area(way_tags(values, tags))):
                    # GDAL draws a closed way as an area from a whole key; power=substation, railway=platform or
                    # man_made=wastewater_plant are areas for some values of their key only: said here, by OSM's rules.
                    # Not when lines are asked: a hedge or a wall that closes comes back as the line it is mapped.
                    shape, kind = ogr.ForceToPolygon(shape.Clone()), 'polygons'
                where = 'points' if geometry == 'points' else kind
                if geometry in ('lines', 'polygons') and kind != geometry:
                    continue
                if where == 'points':
                    shape = _quietly(lambda: _as_point(shape, kind))  # no point inside an area that is none
                elif kind == 'lines':
                    shape = ogr.ForceToMultiLineString(shape.Clone())
                elif kind == 'polygons':
                    shape = ogr.ForceToMultiPolygon(shape.Clone())
                if shape is None or shape.IsEmpty():
                    continue  # an area OpenStreetMap holds with a shape that is none: nothing to draw
                out = layer_of(where)
                row = ogr.Feature(out.GetLayerDefn())
                way = feature.GetField('osm_way_id') if definition.GetFieldIndex('osm_way_id') >= 0 else None
                row.SetField(0, str(way or feature.GetField('osm_id') or ''))
                row.SetField(1, 'way' if way else OSM_TYPES.get(origin.GetName(), 'relation'))
                for name, value in values.items():
                    if value not in (None, ''):
                        row.SetField(written.index(name), str(value))
                        filled[where][name] += 1
                row.SetGeometry(shape)
                if out.CreateFeature(row):  # a full disk: a layer shorter than what was counted is not given
                    raise ValueError(_NOT_WRITTEN)
                counts[where] += 1
            if target.CommitTransaction():
                raise ValueError(_NOT_WRITTEN)
            pending = False
            # A column no feature fills says nothing: a layer of buildings keeps no empty column of hospitals. From
            # the last one: taking a column out moves those after it.
            for kind, made in layers.items():
                for position in range(len(written) - 1, 1, -1):
                    name = written[position]
                    if name != 'name' and not filled[kind][name]:
                        reason = ended()
                        if reason:
                            raise _ended_error(reason)
                        _quietly(lambda: made.DeleteField(position))  # a column that stays is only empty
            return counts
        except RuntimeError as exc:  # GDAL with its exceptions on: what is left to raise here is a write
            logger.warning("add_osm_features: %s", quiet_message(str(exc)))
            raise ValueError(_NOT_WRITTEN) from None
        finally:
            if pending:
                _quietly(target.RollbackTransaction)
            # Closed here on every way out, while GDAL is still quiet: the answer and the GeoPackage are removed
            # right after a failure, and a file still held open cannot be removed on Windows. Every name that
            # holds a feature or a layer is let go: a layer keeps its file open.
            answer = feature = origin = definition = shape = row = out = made = None
            layers.clear()
            target = None
            source = None


def _is_closed_ring(ogr, shape) -> bool:
    """Whether ``shape`` is a line of four points or more that ends where it starts: a closed way."""
    if ogr.GT_Flatten(shape.GetGeometryType()) != ogr.wkbLineString:
        return False
    count = shape.GetPointCount()
    return count >= 4 and shape.GetPoint_2D(0) == shape.GetPoint_2D(count - 1)


def _add(path: str, kind: str, title: str):
    """The layer ``kind`` of the GeoPackage at ``path``, added on top of the project; None when it cannot be opened."""
    from qgis.core import QgsProject, QgsVectorLayer
    layer = QgsVectorLayer(f"{path}|layername={kind}", title, 'ogr')
    if not layer.isValid():
        return None
    metadata = layer.metadata()
    metadata.setRights([ATTRIBUTION])
    layer.setMetadata(metadata)
    project = QgsProject.instance()
    project.addMapLayer(layer, False)
    project.layerTreeRoot().insertLayer(0, layer)
    return layer


def add_osm_features(platform: str, tags: List[Dict[str, Any]], extent_wkt: str = '', crs: str = '',
                     geometry: str = 'as_mapped', name: str = '', extra_domains: str = '') -> Dict[str, Any]:
    """Add the OpenStreetMap features that carry one of ``tags`` in an area, read from an Overpass server the user
    allowed.

    ``geometry``: ``as_mapped`` makes a layer per kind of geometry OpenStreetMap holds them in (points, lines,
    polygons); ``points`` makes one layer of points (a point inside each area, the middle of each line): to count, to
    measure distances, for a heatmap; ``lines`` or ``polygons`` keeps that kind alone. The layers are kept in a
    GeoPackage in project memory, in longitude and latitude, each with ``osm_id``, ``osm_type``, ``name``, a column
    per key asked, and the other tags together.

    Raises:
        ValueError: Not an OpenStreetMap server, tags or an area that cannot be read, an area too large, a server
            that does not answer or stops short, no feature with these tags, stopped; the message says which.
    """
    url = _server(platform, extra_domains)
    asked = read_tags(tags)
    if geometry not in GEOMETRIES:
        raise ValueError(f"geometry is one of {', '.join(GEOMETRIES)}")
    bbox = _area_in_degrees(extent_wkt, crs)
    problem = area_problem(bbox)
    if problem:
        raise ValueError(problem)
    answer = config = path = ''
    kept = False
    made: List[Dict[str, Any]] = []
    unwritten = _TEMPORARY  # what a full disk is said as: by the folder that could not be written
    try:
        with running('add_osm_features'):
            answer = data_store.new_path('answer.osm')
            _ask(platform, url, overpass_query(asked, bbox), answer)
            config = data_store.new_path('osmconf.ini')
            with data_store.store_for().writer(config) as write:
                write(gdal_config(asked).encode('utf-8'))
            unwritten = _NOT_WRITTEN
            path = data_store.new_path('openstreetmap.gpkg')
            counts = _in_background('add_osm_features',
                                    lambda ended: _convert(answer, config, path, asked, geometry, ended))
        found = [kind for kind in _ORDER if counts.get(kind)]
        if not found:
            only = '' if geometry in ('as_mapped', 'points') else f" as {geometry}"
            raise ValueError(f"no feature with these tags in this area{only}: check the key and the value as "
                             "OpenStreetMap writes them (amenity=hospital, building, highway=primary), or ask for a "
                             "larger area")
        title = (name or '').strip()[:180] or default_name(asked)
        for kind in found:
            layer = _add(path, kind, layer_title(title, kind, len(found) > 1))
            if layer is None:
                raise ValueError("the features were read but QGIS cannot open the layer written")
            made.append({'layer_id': layer.id(), 'name': layer.name(), 'geometry': kind,
                         'feature_count': counts[kind],
                         'fields': [field.name() for field in layer.fields() if field.name() != 'fid']})
        kept = True
    except OSError:
        raise ValueError(unwritten) from None
    finally:
        for temporary in (answer, config):
            if temporary:
                data_store.discard(temporary)
        if path and not kept:
            _forget(path, made)
    made.reverse()  # as the layer tree shows them, top first
    return {'platform': platform, 'tags': [tag.shown() for tag in asked], 'layers': made,
            'feature_count': sum(row['feature_count'] for row in made), 'crs_authid': 'EPSG:4326',
            'attribution': ATTRIBUTION,
            'note': ("data of OpenStreetMap as its contributors mapped it: complete in some places, sparse in others; "
                     "say so before a count is taken as a census")}


def _forget(folder: str, made: Sequence[Dict[str, Any]]) -> None:
    """Take back what a call that failed midway left: the layers already added, then their file."""
    from qgis.core import QgsProject
    for row in made:
        QgsProject.instance().removeMapLayer(row['layer_id'])
    data_store.discard(folder)


def check_osm(platform: str, extra_domains: str = '') -> Dict[str, Any]:
    """Ask an Overpass server the user allowed for nothing at all (the Test of the Sources tab).

    Raises:
        ValueError: Not an OpenStreetMap server, or it did not answer as one.
    """
    url = _server(platform, extra_domains)
    with running('check_osm'):
        try:
            reply = fetch(url, body=b'data=' + quote('[out:xml][timeout:5];node(id:1);out ids;', safe='').encode('ascii'),
                          headers=_FORM, max_bytes=1024 * 1024, timeout_ms=CHECK_TIMEOUT_MS)
        except HttpFailure as exc:
            raise ValueError(f"{platform} did not answer: {exc}") from None
    problem = status_problem(reply.status)
    if problem:
        raise ValueError(f"{platform}: {problem}")
    if b'<osm' not in reply.content[:600]:
        raise ValueError(f"{platform} answers, but not as an Overpass server")
    return {'platform': platform, 'status': reply.status}
