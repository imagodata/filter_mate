"""Real QGIS rendered capture and colour selection checks, no public network.

Run: QT_QPA_PLATFORM=offscreen python3 tests/qgis_headless/check_rendered_raster.py
"""
import importlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
import types
import threading
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from osgeo import gdal, osr
from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsMapSettings,
    QgsRasterLayer, QgsRectangle, QgsSingleBandColorDataRenderer,
)
from qgis.PyQt.QtCore import QBuffer, QIODevice, QEventLoop, QSize, QTimer
from qgis.PyQt.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parents[2]
for part in ('', 'core', 'core.domain', 'adapters', 'adapters.qgis',
             'adapters.qgis.coverage_layers', 'ui', 'ui.widgets', 'ui.widgets.coverage_panels'):
    module = types.ModuleType('fm_render_test' + ('.' + part if part else ''))
    module.__path__ = [str(ROOT / part.replace('.', '/'))]
    sys.modules[module.__name__] = module

app = QgsApplication([], False)
app.initQgis()
rendered = importlib.import_module('fm_render_test.adapters.qgis.coverage_layers.rendered_raster')
adapter = importlib.import_module('fm_render_test.adapters.qgis.coverage_layers.raster_adapter')
panel_module = importlib.import_module('fm_render_test.ui.widgets.coverage_panels.raster_exploring_panel')


def run_task(task):
    loop = QEventLoop()
    outcomes = []
    heartbeat = []
    old_callback = task.callback

    def done(completed, success):
        outcomes.append(success)
        accepted = old_callback(completed, success)
        loop.quit()
        return accepted

    task.callback = done
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: heartbeat.append(True))
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(30000)
    timer.start()
    app.taskManager().addTask(task)
    loop.exec()
    timer.stop()
    timeout.stop()
    assert outcomes, 'task did not finish within 30 seconds'
    assert heartbeat, 'GUI event loop did not run during capture'
    return outcomes[0]


with tempfile.TemporaryDirectory(prefix='fm_rendered_') as folder:
    for width, height, limit, edge_limit in ((1, 1000000000, 1, 2048),
                                            (1000000000, 1, 1, 2048), (10000000, 1, 1, 2048),
                                            (1, 10000000, 3, 32), (800, 600, 1000, 64)):
        bw, bh = rendered.bounded_size(width, height, limit, edge_limit)
        assert bw * bh <= limit and max(bw, bh) <= edge_limit
    print('PASS strict pixel budgets for extremely narrow extents', flush=True)
    source = str(Path(folder) / 'rgb.tif')
    ds = gdal.GetDriverByName('GTiff').Create(source, 32, 16, 3, gdal.GDT_Byte)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(3857)
    ds.SetProjection(crs.ExportToWkt())
    ds.SetGeoTransform((0, 10, 0, 160, 0, -10))
    for band, color in enumerate((20, 80, 140), 1):
        ds.GetRasterBand(band).WriteArray(np.full((16, 32), color, dtype=np.uint8))
    ds = None
    layer = QgsRasterLayer(source, 'Original image', 'gdal')
    assert layer.isValid()
    settings = QgsMapSettings()
    settings.setDestinationCrs(layer.crs())
    settings.setExtent(layer.extent())
    settings.setOutputSize(QSize(800, 400))
    settings.setLayers([layer])
    # Isolate session storage and avoid modifying any user's profile.
    rendered.cache._session_dir = folder
    task = rendered.RenderedRasterTask(source, 'gdal', layer.renderer().clone(),
                                      settings, layer.crs(), lambda *_: True,
                                      max_pixels=1000, max_size=64)
    assert not task.path  # no provider reads or writes in construction
    assert run_task(task), task.error
    ds = gdal.Open(task.path)
    assert ds.RasterCount == 3
    assert ds.RasterXSize * ds.RasterYSize <= 1000
    assert max(ds.RasterXSize, ds.RasterYSize) <= 64
    assert abs(task.settings.scale() / settings.scale() - 1) < 0.01
    assert [int(ds.GetRasterBand(i).ReadAsArray()[5, 5]) for i in (1, 2, 3)] == [20, 80, 140]
    assert ds.GetGeoTransform()[1] > 0 and ds.GetGeoTransform()[5] < 0
    ds = None
    print('PASS async bounded raw RGB GeoTIFF, CRS, scale and GUI heartbeat', flush=True)

    # A real WMS summary exposes a single ARGB band: the panel must still
    # build RGB expressions against the three-band local snapshot.
    summary = adapter.read_raster_summary(layer)
    summary.bands = summary.bands[:1]
    panel = panel_module.RasterExploringPanel()
    panel.set_summary(summary)
    panel.set_reference('Original image')
    panel.set_rendered_only(True)
    panel.set_stream_notice('Additional sample notice')
    assert 'Additional sample notice' in panel._stream_notice.text()
    assert panel._bands_group.isHidden() and panel._range_group.isHidden()
    assert panel._expression_group.isHidden() and not panel._tolerance_spin.isHidden()
    panel.set_color_sample({1: 20, 2: 80, 3: 140})
    first = panel.selection()
    assert first is not None and first.mode.value == 'expression'
    assert all('@' + str(i) in first.expression for i in (1, 2, 3)), first.expression
    panel.set_color_sample({1: 50, 2: 90, 3: 150}, extend=True)
    assert len(panel._picks) == 2
    before = panel.selection().expression
    panel._tolerance_spin.setValue(20)
    assert panel.selection().expression != before
    saved = panel.state()
    saved['pipette_bands'] = [1]  # obsolete ARGB state must not reduce RGB sampling
    panel.restore_state(saved)
    assert panel.pipette_bands() == [1, 2, 3]
    panel.reset()
    panel.set_color_sample({1: 20, 2: 80, 3: 140})
    assert panel.selection().mode.value == 'expression'
    dem = adapter.RasterSummary(layer_id='dem', layer_name='DEM', provider='gdal',
                                crs_authid='EPSG:3857', width=32, height=16,
                                pixel_size_x=10, pixel_size_y=10,
                                bands=[adapter.RasterBandInfo(1, 'Elevation', 'Float32', None)])
    panel.set_summary(dem)  # Controller adopts the next summary before changing mode.
    panel.set_rendered_only(False)
    assert not panel._bands_group.isHidden() and panel._range_group.isEnabled()
    assert panel.selection() is None
    assert panel.pipette_bands() == [1] and len(panel._band_rows) == 1
    panel.set_color_sample({1: 100})
    assert panel.selection().mode.value == 'range'
    print('PASS single ARGB summary, RGB selection, Ctrl+click, tolerance, reset and numeric mode restoration', flush=True)

    rejected = rendered.RenderedRasterTask(source, 'gdal', layer.renderer().clone(),
                                          settings, layer.crs(), lambda *_: False)
    assert run_task(rejected)
    assert not Path(rejected.path).exists()
    assert not Path(rejected.path + '.msk').exists()
    print('PASS superseded successful capture cleanup', flush=True)

    canceled = rendered.RenderedRasterTask(source, 'gdal', layer.renderer().clone(),
                                          settings, layer.crs(), lambda *_: False)
    canceled.cancel()
    assert not canceled.run()
    canceled.finished(False)
    assert not canceled.path
    print('PASS cancellation before provider open', flush=True)

    # A different canvas CRS still produces a snapshot in the layer CRS.
    settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    settings.setExtent(QgsRectangle(0, 0, 0.002, 0.001))
    transformed = rendered.RenderedRasterTask(source, 'gdal', layer.renderer().clone(),
                                             settings, layer.crs(), lambda *_: False)
    assert transformed.settings.destinationCrs() == layer.crs()
    assert 200 < transformed.extent.width() < 250
    print('PASS canvas extent transformed to original layer CRS', flush=True)

    tile = QImage(256, 256, QImage.Format.Format_RGBA8888)
    tile.fill(QColor(20, 80, 140))
    for x in range(128, 256):
        for y in range(256):
            tile.setPixelColor(x, y, QColor(200, 210, 220))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    tile.save(buffer, 'PNG')
    png = bytes(buffer.data())
    requests = []

    class TileHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            time.sleep(0.1)  # GUI heartbeat must survive network latency.
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.end_headers()
            self.wfile.write(png)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), TileHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    uri = ('type=xyz&url=http://127.0.0.1:' + str(server.server_port) +
           '/{z}/{x}/{y}.png&zmin=0&zmax=0&crs=EPSG:3857')
    settings.setDestinationCrs(layer.crs())
    edge = 20037508.342789244
    settings.setExtent(QgsRectangle(-edge, -edge, edge, edge))
    settings.setOutputSize(QSize(256, 256))
    xyz = rendered.RenderedRasterTask(uri, 'wms', QgsSingleBandColorDataRenderer(None, 1),
                                     settings, layer.crs(), lambda *_: True, max_pixels=4096)
    assert run_task(xyz), xyz.error
    server.shutdown()
    server.server_close()
    assert requests
    local = QgsRasterLayer(xyz.path, 'XYZ colors', 'gdal')
    assert local.isValid() and local.bandCount() >= 3
    assert gdal.Open(xyz.path).RasterCount == 3
    panel.set_summary(adapter.read_raster_summary(local))
    panel.set_reference(adapter.raster_reference(local))
    panel.set_rendered_only(True)
    panel.set_color_sample({1: 20, 2: 80, 3: 140})
    selection = panel.selection()
    virtual = adapter.selection_virtual_layer(local, selection)
    assert virtual and virtual.isValid()
    result = adapter.selection_geometry(virtual.dataProvider(), selection, local.extent(),
                                       local.width(), local.height(), local.crs().toWkt(),
                                       nodata_provider=local.dataProvider(), nodata_bands=[1, 2, 3])
    assert not result.geometry.isEmpty()
    assert 0.4 < result.geometry.area() / (local.extent().width() * local.extent().height()) < 0.6
    print('PASS local XYZ service, async HTTP, RGB pipette expression and cross-filter polygon', flush=True)
    # Release providers while datasets still exist, and before QGIS shutdown.
    panel.close()
    del panel, virtual, local, transformed, canceled, rejected, xyz, task, layer
    settings.setLayers([])
    import gc
    gc.collect()

app.exitQgis()
