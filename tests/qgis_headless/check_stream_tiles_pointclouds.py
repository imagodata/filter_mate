# -*- coding: utf-8 -*-
"""Lot E: real tiles, snapshot lifecycle and bounded HTTP point cloud reads.

Run in qgis/qgis:ltr and :stable, QT_QPA_PLATFORM=offscreen. Set PATH to
PDAL 2.4+ for cloud checks. Public HTTPS probes require FM_STREAM_PUBLIC=1;
network unavailable means SKIP. JSON metrics can be saved with FM_STREAM_METRICS.
HTTP counters measure response body bytes, excluding headers/TLS overhead.
"""
import contextlib
import functools
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import sys
import tempfile
import threading
import time
import traceback
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', tempfile.mkdtemp(prefix='fm_stream_e_logs_'))
from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsExpression, QgsExpressionContext,
    QgsExpressionContextUtils, QgsFeature, QgsGeometry, QgsMapSettings, QgsProject,
    QgsRectangle, QgsVectorLayer, QgsVectorTileBasicRenderer, QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer, QgsWkbTypes, Qgis,
)

POLYGON = Qgis.GeometryType.Polygon if hasattr(Qgis, 'GeometryType') else QgsWkbTypes.PolygonGeometry

ROOT = Path(os.environ.get('FM_REPO', Path(__file__).resolve().parents[2]))
# Import the real adapters without starting the plugin/dock.
for part in ('', '.core', '.core.domain', '.core.filter', '.core.services', '.adapters', '.adapters.qgis',
             '.adapters.qgis.coverage_layers'):
    package = types.ModuleType('fm_stream_e' + part)
    package.__path__ = [str(ROOT.joinpath(*part.strip('.').split('.'))) if part else str(ROOT)]
    sys.modules[package.__name__] = package


def module(name):
    return importlib.import_module('fm_stream_e.' + name)


filters = module('adapters.qgis.coverage_layers.vector_tile_filters')
snapshots = module('adapters.qgis.coverage_layers.snapshots')
pdal = module('adapters.qgis.coverage_layers.pdal_cli')
LayerKind = module('core.domain.layer_kind').LayerKind
CrossFilterRequest = module('core.domain.cross_filter').CrossFilterRequest
TargetSpec = module('core.domain.cross_filter').TargetSpec
CrossFilterService = module('core.services.cross_filter_service').CrossFilterService
FixedGeometrySourceJob = module('adapters.qgis.coverage_layers.source_jobs').FixedGeometrySourceJob
cache = module('adapters.qgis.coverage_layers.cache')
results, metrics = [], []
app = QgsApplication([], False)
app.initQgis()
folder = Path(tempfile.mkdtemp(prefix='fm_stream_e_'))


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    results.append(status)
    print(f'{status} {name} {detail}', flush=True)


def skip(name, reason):
    print(f'SKIP {name}: {reason}', flush=True)


class Server(BaseHTTPRequestHandler):
    """SQLite MVT, static files with ranges, and a counted public HTTPS relay."""
    transferred = 0
    public_base = ''
    generation = 0
    public_budget = 128 * 1024 * 1024

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.serve(False)

    def do_GET(self):
        self.serve(True)

    def serve(self, body):
        generation = type(self).generation
        path = urlsplit(self.path).path
        try:
            headers, status = {}, 200
            if path.startswith('/public/'):
                if type(self).transferred >= type(self).public_budget:
                    self.send_error(503)
                    return
                request = Request(urljoin(type(self).public_base, path[len('/public/'):]))
                if self.headers.get('Range'):
                    request.add_header('Range', self.headers['Range'])
                with urlopen(request, timeout=20) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
                    if len(data) > 32 * 1024 * 1024:
                        raise RuntimeError('public response exceeds the measurement budget')
                    status = response.status
                    headers = {key: response.headers[key] for key in ('Content-Range', 'Content-Encoding')
                               if response.headers.get(key)}
            elif path.startswith('/tiles/'):
                z, x, y = map(int, path[len('/tiles/'):-len('.pbf')].split('/'))
                with sqlite3.connect(str(folder / 'tiles.mbtiles')) as db:
                    row = db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',
                                     (z, x, (1 << z) - y - 1)).fetchone()
                if row is None:
                    self.send_error(404)
                    return
                data = row[0]
                if data[:2] == b'\x1f\x8b':
                    headers['Content-Encoding'] = 'gzip'
            else:
                source = folder / path.lstrip('/')
                if not source.is_file():
                    self.send_error(404)
                    return
                length = source.stat().st_size
                start, end = 0, length - 1
                if self.headers.get('Range'):
                    first, last = self.headers['Range'][len('bytes='):].split('-')
                    start, end = int(first), min(int(last) if last else end, end)
                    status = 206
                    headers['Content-Range'] = f'bytes {start}-{end}/{length}'
                with source.open('rb') as stream:
                    stream.seek(start)
                    data = stream.read(end - start + 1)
            self.send_response(status)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Accept-Ranges', 'bytes')
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            if body:
                self.wfile.write(data)
                if generation == type(self).generation:
                    type(self).transferred += len(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send_error(502)


class FixtureHTTPServer(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


server = FixtureHTTPServer(('127.0.0.1', 0), Server)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{server.server_port}'


def tile_fixture():
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    dataset = ogr.GetDriverByName('MVT').CreateDataSource(str(folder / 'tiles.mbtiles'),
                                                       options=['FORMAT=MBTILES', 'MINZOOM=0', 'MAXZOOM=2'])
    layer = dataset.CreateLayer('objects', srs, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn('kind', ogr.OFTString))
    for kind, x in [('keep', -6000000), ('drop', 3000000)]:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('kind', kind)
        feature.SetGeometry(ogr.CreateGeometryFromWkt(
            f'POLYGON(({x} 1000000,{x+1000000} 1000000,{x+1000000} 2000000,{x} 2000000,{x} 1000000))'))
        layer.CreateFeature(feature)
    dataset = None


def tile_checks():
    tile_fixture()
    project = QgsProject.instance()
    local = QgsVectorTileLayer(f'type=mbtiles&url={folder / "tiles.mbtiles"}', 'local tiles')
    check('MBTiles fixture opens', local.isValid())
    layer = QgsVectorTileLayer(f'type=xyz&url={base}/tiles/{{z}}/{{x}}/{{y}}.pbf&zmin=0&zmax=2', 'HTTP tiles')
    project.addMapLayer(layer)
    renderer = QgsVectorTileBasicRenderer()
    style = QgsVectorTileBasicRendererStyle('objects', 'objects', POLYGON)
    from qgis.core import QgsFillSymbol, QgsProperty
    symbol = QgsFillSymbol.createSimple({'color': '255,0,0,255'})
    symbol.dataDefinedProperties().setProperty(9999, QgsProperty.fromExpression('2'))
    style.setSymbol(symbol)
    style.setFilterExpression('"kind" IS NOT NULL')
    renderer.setStyles([style])
    layer.setRenderer(renderer)
    original = filters.style_xml(layer)
    before = snapshots.take_snapshot(layer, LayerKind.VECTOR_TILE)
    layer.setCustomProperty('user/note', 'preserve me')
    after = filters.apply_filter(layer, '"kind" = \'keep\'')
    check('attribute rule retained', 'IS NOT NULL' in layer.renderer().styles()[0].filterExpression())
    from qgis.core import QgsMapRendererSequentialJob
    from qgis.PyQt.QtCore import QSize
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
    settings.setExtent(QgsRectangle(-20037508, -20037508, 20037508, 20037508))
    settings.setOutputSize(QSize(512, 512))
    job = QgsMapRendererSequentialJob(settings)
    job.start(); job.waitForFinished()
    check('HTTP tiles fetched from MBTiles', Server.transferred > 0)
    image = job.renderedImage()
    red = sum(image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 100
              for y in range(512) for x in range(512))
    check('attribute filter renders visible objects', red > 0, f'red_pixels={red}')
    snapshots.restore_snapshot(layer, before)
    check('undo restores exact original style', filters.style_xml(layer) == original)
    restored_styles = layer.renderer().styles()
    check('unnamed symbol property survives filter and undo',
          restored_styles[0].symbol().dataDefinedProperties().property(9999).expressionString() == '2')
    snapshots.restore_snapshot(layer, after)
    request = CrossFilterRequest('fixed', LayerKind.OTHER, (TargetSpec(layer.id(), LayerKind.VECTOR_TILE),),
                                 predicates=('Intersect',), other_layers_combine_operator='AND')
    selection = QgsGeometry.fromRect(QgsRectangle(-7000000, 0, -4000000, 3000000))
    source = FixedGeometrySourceJob(layer, selection.asWkt())
    service = CrossFilterService()
    task = service.run(request, source, synchronous=True)
    check('spatial cross filter succeeds', bool(task.outcomes) and task.outcomes[0].success,
          str([o.message for o in task.outcomes]))
    check('spatial filter enters undo history', service.history.can_undo('fixed'))
    filtered_xml = filters.style_xml(layer)
    check('tile snapshot excludes custom properties', 'filtermate/derived' not in filtered_xml)
    check('cross service Undo restores tile', layer.id() in service.undo('fixed'))
    check('cross service Redo restores tile', layer.id() in service.redo('fixed') and filters.style_xml(layer) == filtered_xml)
    check('tile Undo preserves user properties', layer.customProperty('user/note') == 'preserve me')
    expression = layer.renderer().styles()[0].filterExpression()
    context = QgsExpressionContext()
    context.appendScope(QgsExpressionContextUtils.mapSettingsScope(settings))
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt('POINT(-5500000 1500000)'))
    context.setFeature(feature)
    spatial_only = task.target_jobs[0].expression
    parsed = QgsExpression(spatial_only)
    check('spatial expression parses', not parsed.hasParserError(), parsed.parserErrorString())
    check('spatial geometry evaluated in map CRS', parsed.evaluate(context) == True, repr(parsed.evaluate(context)) + parsed.evalErrorString())
    check('attribute and spatial filters combined', 'intersects' in expression and "'keep'" in expression)
    settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    settings.setExtent(QgsRectangle(-180, -85, 180, 85))
    job = QgsMapRendererSequentialJob(settings); job.start(); job.waitForFinished()
    image = job.renderedImage()
    red = sum(image.pixelColor(x, y).red() > 200 and image.pixelColor(x, y).green() < 100
              for y in range(512) for x in range(512))
    check('spatial tile filter renders after map CRS change', red > 0, f'red_pixels={red}')
    from qgis.core import QgsVectorTileBasicLabeling, QgsVectorTileBasicLabelingStyle, QgsPalLayerSettings
    labeling = QgsVectorTileBasicLabeling()
    label_style = QgsVectorTileBasicLabelingStyle()
    label_style.setLayerName('objects')
    label_style.setGeometryType(POLYGON)
    label_settings = QgsPalLayerSettings(); label_settings.fieldName = 'kind'
    label_style.setLabelSettings(label_settings)
    labeling.setStyles([label_style]); layer.setLabeling(labeling)
    if hasattr(layer, 'setLabelsEnabled'):
        layer.setLabelsEnabled(True)
    # Reset the base so this scenario includes real labeling in its original style.
    snapshots.registry().forget(layer.id()); layer.removeCustomProperty(snapshots.DERIVED_PROPERTY)
    original = filters.style_xml(layer)
    filters.apply_filter(layer, 'FALSE')
    check('labeling filtered too', layer.labeling().styles()[0].filterExpression() == 'FALSE')
    from qgis.PyQt.QtWidgets import QComboBox
    from qgis.gui import QgsCheckableComboBox
    combo = QgsCheckableComboBox()
    filters.append_targets(combo, project, [layer.id()])
    check('target list has tile badge', combo.count() == 1 and 'Vector tiles' in combo.itemText(0))
    project.addMapLayer(local)
    local.renderer = lambda: types.SimpleNamespace(type=lambda: 'external')
    favorite = module('adapters.qgis.coverage_layers.favorites_bridge').capture()
    del local.renderer
    project.removeMapLayer(local.id())
    check('favorite captures tile style', any(e['kind'] == 'vector_tile' for e in favorite))
    project_path = str(folder / 'tiles.qgs')
    project.setFileName(project_path)
    check('filtered project saves', project.write())
    tile_id = layer.id()
    snapshots.registry().restore_all(project)
    check('unload restores original style', filters.style_xml(layer) == original)
    project.clear()
    check('project reloads', project.read(project_path))
    layer = project.mapLayer(tile_id)
    check('reloaded filter is retained', layer.renderer().styles()[0].filterExpression().endswith('(FALSE\n)'))
    snapshots.registry().forget(layer.id())  # simulate plugin activation after project load
    current = snapshots.take_snapshot(layer, LayerKind.VECTOR_TILE)
    snapshots.restore_snapshot(layer, snapshots.base_snapshot(current))
    check('unfilter after reload restores original style', filters.style_xml(layer) == original)
    restored_styles = layer.renderer().styles()
    check('unnamed symbol property survives project reload',
          restored_styles[0].symbol().dataDefinedProperties().property(9999).expressionString() == '2')
    filters.apply_filter(layer, 'TRUE')
    changed = layer.renderer().clone()
    styles = changed.styles(); styles[0].setFilterExpression('FALSE'); changed.setStyles(styles)
    layer.setRenderer(changed)
    user_style = filters.style_xml(layer)
    current = snapshots.take_snapshot(layer, LayerKind.VECTOR_TILE)
    snapshots.restore_snapshot(layer, snapshots.base_snapshot(current))
    check('a user-edited tile style becomes the new base', filters.style_xml(layer) == user_style)
    project.clear(); combo.deleteLater()



def public_tile_checks():
    if os.environ.get('FM_STREAM_PUBLIC') != '1':
        skip('IGN vector plan', 'set FM_STREAM_PUBLIC=1')
        return
    style_url = 'https://data.geopf.fr/annexes/ressources/vectorTiles/styles/PLAN.IGN/standard.json'
    try:
        with urlopen(style_url, timeout=20) as response:
            style = json.load(response)
        x = int((1.44 + 180) / 360 * 16384)
        y = int((1 - math.asinh(math.tan(math.radians(43.6))) / math.pi) / 2 * 16384)
        tile_url = f'https://data.geopf.fr/tms/1.0.0/PLAN.IGN/14/{x}/{y}.pbf'
        with urlopen(tile_url, timeout=20) as response:
            raw = response.read()
    except Exception as exc:
        skip('IGN vector plan', type(exc).__name__)
        return
    from qgis.core import QgsMapBoxGlStyleConverter
    converter = QgsMapBoxGlStyleConverter()
    converter.convert(style)
    renderer = converter.renderer()
    check('IGN tile and basic style available', bool(raw) and renderer is not None)
    if renderer is None:
        return
    project = QgsProject.instance()
    layer = QgsVectorTileLayer('type=xyz&url=https://data.geopf.fr/tms/1.0.0/PLAN.IGN/{z}/{x}/{y}.pbf&zmin=0&zmax=18', 'IGN plan')
    layer.setRenderer(renderer.clone())
    labeling = converter.labeling()
    if labeling is not None:
        layer.setLabeling(labeling.clone())
    project.addMapLayer(layer)
    original = filters.style_xml(layer)
    filters.apply_filter(layer, '"symbo" IS NOT NULL')
    job_class = module('adapters.qgis.coverage_layers.vector_tile_target').VectorTileTargetJob
    job = job_class(layer, 'AND')
    area = QgsGeometry.fromRect(QgsRectangle(155000, 5390000, 165000, 5410000))
    job.compute(area, layer.crs(), project.transformContext(),
                CrossFilterRequest('fixed', LayerKind.OTHER), lambda: False)
    state = job.apply(layer)
    check('IGN attribute then spatial filter', state is not None and 'intersects' in layer.renderer().styles()[0].filterExpression())
    snapshots.restore_snapshot(layer, snapshots.base_snapshot(state))
    restored_xml = filters.style_xml(layer)
    if restored_xml != original:
        import difflib
        for line in list(difflib.unified_diff(original.replace('><', '>\n<').splitlines(),
                                             restored_xml.replace('><', '>\n<').splitlines()))[:20]:
            print('STYLE_DIFF ' + line[:500], flush=True)
    check('IGN Unfilter restores exact original style', filters.style_xml(layer) == original)
    project_path = str(folder / 'ign.qgs'); project.setFileName(project_path)
    check('IGN project saves after Unfilter', project.write())
    tile_id = layer.id(); project.clear()
    check('IGN project reloads after Unfilter', project.read(project_path))
    layer = project.mapLayer(tile_id)
    check('IGN original style intact after project reload', filters.style_xml(layer) == original)
    project.clear()


def cloud_fixture():
    import numpy as np
    root = folder / 'ept'
    (root / 'ept-data').mkdir(parents=True)
    (root / 'ept-hierarchy').mkdir()
    schema = [{'name': axis, 'type': 'floating', 'size': 8} for axis in 'XYZ']
    dtype = np.dtype([(axis, '<f8') for axis in 'XYZ'])
    rng = np.random.default_rng(7)
    hierarchy = {'0-0-0-0': 100}
    np.array([(float(i), float(i), 20.) for i in range(100)], dtype=dtype).tofile(root / 'ept-data/0-0-0-0.bin')
    for x in range(2):
        for y in range(2):
            for z in range(2):
                name = f'1-{x}-{y}-{z}'
                points = np.empty(20000, dtype=dtype)
                for axis, offset in zip('XYZ', (x, y, z)):
                    points[axis] = rng.uniform(offset * 1000 + 5, (offset + 1) * 1000 - 5, len(points))
                points.tofile(root / f'ept-data/{name}.bin')
                hierarchy[name] = len(points)
    (root / 'ept-hierarchy/0-0-0-0.json').write_text(json.dumps(hierarchy))
    (root / 'ept.json').write_text(json.dumps({
        'bounds': [0, 0, 0, 2000, 2000, 2000], 'boundsConforming': [0, 0, 0, 2000, 2000, 2000],
        'dataType': 'binary', 'hierarchyType': 'json', 'points': sum(hierarchy.values()),
        'schema': schema, 'span': 128, 'srs': {'authority': 'EPSG', 'horizontal': '3857'}, 'version': '1.0.0'}))
    ok, message = pdal.run_pipeline([{'type': 'readers.ept', 'filename': str(root / 'ept.json')},
                                     {'type': 'writers.copc', 'filename': str(folder / 'cloud.copc.laz')}])
    check('COPC fixture written', ok, message)
    dem = gdal.GetDriverByName('GTiff').Create(str(folder / 'dem.tif'), 200, 200, 1, gdal.GDT_Float32)
    dem.SetGeoTransform((0, 10, 0, 2000, 0, -10))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(3857); dem.SetProjection(srs.ExportToWkt())
    dem.GetRasterBand(1).Fill(0); dem = None


def measure(name, source, bounds, hag=False, baseline=False):
    polygon = f'POLYGON(({bounds[0]} {bounds[1]},{bounds[2]} {bounds[1]},{bounds[2]} {bounds[3]},' \
              f'{bounds[0]} {bounds[3]},{bounds[0]} {bounds[1]}))'
    if baseline:
        reader = {'type': pdal.reader_for(source), 'filename': source}
        stages = [reader]
        if not hag:
            if reader['type'] == 'readers.copc':
                reader['polygon'] = polygon  # PR #172 baseline already pushed COPC clipping down
            else:
                stages.append({'type': 'filters.crop', 'polygon': polygon})
    else:
        stages = pdal.read_stages(source, bounds, polygon)
    if hag:
        stages.append({'type': 'filters.hag_dem', 'raster': str(folder / 'dem.tif')})
    if source.startswith(base + '/public/'):
        dem = gdal.GetDriverByName('GTiff').Create(str(folder / 'dem.tif'), 100, 100, 1, gdal.GDT_Float32)
        dem.SetGeoTransform((bounds[0], (bounds[2]-bounds[0])/100, 0, bounds[3], 0, -(bounds[3]-bounds[1])/100))
        srs = osr.SpatialReference(); srs.ImportFromEPSG(2992 if name == 'Autzen' else 3857)
        dem.SetProjection(srs.ExportToWkt()); dem.GetRasterBand(1).Fill(0); dem = None
    out = folder / 'measured.copc.laz'
    stages.append({'type': 'writers.copc', 'filename': str(out)})
    Server.generation += 1
    Server.transferred = 0
    started = time.perf_counter()
    ok, message = pdal.run_pipeline(stages, timeout=90)
    elapsed = time.perf_counter() - started
    metric = dict(name=name, baseline=baseline, hag=hag, bytes=Server.transferred, seconds=round(elapsed, 3), success=ok)
    metrics.append(metric)
    print('METRIC ' + json.dumps(metric), flush=True)
    return ok, message, metric


def cloud_checks():
    if not pdal.supports_copc():
        skip('point clouds', pdal.copc_unavailable_reason())
        return
    cloud_fixture()
    for name, source in [('EPT', base + '/ept/ept.json'), ('COPC', base + '/cloud.copc.laz')]:
        for hag in (False, True):
            old_ok, old_message, old = measure(name, source, (10, 10, 900, 900), hag, True)
            ok, message, new = measure(name, source, (10, 10, 900, 900), hag)
            check(f'{name} {"HAG" if hag else "clip"} bounded read', old_ok and ok, old_message or message)
            check(f'{name} {"HAG" if hag else "clip"} byte budget', new['bytes'] <= old['bytes'],
                  f'{old["bytes"]} -> {new["bytes"]}')
    from qgis.core import QgsRasterLayer
    cloud = module('adapters.qgis.coverage_layers.point_cloud_footprint').open_point_cloud(
        base + '/cloud.copc.laz', 'remote HAG', 'copc')
    QgsProject.instance().addMapLayer(cloud)
    dem = QgsRasterLayer(str(folder / 'dem.tif'), 'DTM')
    zone = QgsGeometry.fromRect(QgsRectangle(10, 10, 900, 900))
    hag_class = module('adapters.qgis.coverage_layers.hag_task').HeightAboveGroundTask
    transferred = Server.transferred
    hag_task = hag_class(cloud, dem, zone=zone)
    check('HAG preparation does not read remote points', transferred == Server.transferred)
    check('HAG task uses drawn zone', hag_task.extent == zone.boundingBox())
    ok = hag_task.run()
    check('real HAG task runs', ok, hag_task.message)
    if ok:
        hag_task.finished(True)
        state = snapshots.take_snapshot(cloud, LayerKind.POINT_CLOUD)
        check('bounded HAG records recoverable source', state.bounded_enrichment)
        from fm_stream_e.adapters.qgis.coverage_layers.target_appliers import make_job
        widen = make_job(cloud, LayerKind.POINT_CLOUD, 'OR')
        widen.compute(zone, cloud.crs(), QgsProject.instance().transformContext(),
                      CrossFilterRequest('fixed', LayerKind.OTHER), lambda: False)
        check('bounded HAG refuses misleading OR', not widen.outcome.success and 'Unfilter' in widen.outcome.message)
        cache.settle(widen.outputs); widen.release()
        snapshots.restore_snapshot(cloud, snapshots.base_snapshot(state))
        check('Unfilter after HAG restores complete remote cloud', cloud.source() == base + '/cloud.copc.laz')
    QgsProject.instance().clear()
    if os.environ.get('FM_STREAM_PUBLIC') != '1':
        skip('USGS 3DEP / Autzen HTTPS', 'set FM_STREAM_PUBLIC=1 to enable public measurements')
        return
    for name, source, bounds in [
        ('USGS 3DEP', 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/IA_FullState/ept.json',
         (-10425172, 5164495, -10424972, 5164695)),
        ('Autzen', 'https://s3.amazonaws.com/hobu-lidar/autzen-classified.copc.laz', (636000, 849000, 636100, 849100)),
    ]:
        try:
            with urlopen(Request(source, headers={'Range': 'bytes=0-1023'}), timeout=15) as response:
                response.read(1024)
        except Exception as exc:
            skip(name, type(exc).__name__)
            continue
        # Public datasets are enormous. Run only bounded reads; a full baseline
        # requires an explicit separate measurement budget, never an automatic CI download.
        Server.public_base = source.rsplit('/', 1)[0] + '/'
        relay = base + '/public/' + source.rsplit('/', 1)[-1]
        for hag in (False, True):
            Server.public_budget = 32 * 1024 * 1024 if name == 'USGS 3DEP' else 128 * 1024 * 1024
            before_ok, before_message, old = measure(name, relay, bounds, hag, True)
            if not before_ok:
                skip(name + ' baseline completion', 'measurement stopped at the public byte/time budget; bytes are a lower bound')
            Server.public_budget = 128 * 1024 * 1024
            ok, message, new = measure(name, relay, bounds, hag)
            if not ok and any(term in message for term in ('Could not read', 'timeout', 'HTTP', 'Failed to read')):
                skip(name + ' HTTPS useful area', 'network read failed: ' + message[:180])
            else:
                check(name + (' HAG' if hag else ' clip') + ' HTTPS useful area', ok, message)
            if before_ok:
                check(name + ' HTTPS byte budget', new['bytes'] <= old['bytes'])


try:
    tile_checks()
    public_tile_checks()
    if os.environ.get('FM_STREAM_CLOUD_SKIP') != '1':
        cloud_checks()
except Exception:
    traceback.print_exc()
    check('unhandled exception', False)
finally:
    if os.environ.get('FM_STREAM_METRICS'):
        Path(os.environ['FM_STREAM_METRICS']).write_text(json.dumps(metrics, indent=2))
    snapshots.registry().restore_all()
    snapshots.registry().uninstall()
    QgsProject.instance().clear()
    server.shutdown(); server.server_close()
    print(f'{results.count("PASS")} passed, {results.count("FAIL")} failed', flush=True)
    # QGIS providers can hold background objects until process exit.
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(1 if 'FAIL' in results else 0)
