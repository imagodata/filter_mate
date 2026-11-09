"""Real QGIS segmentation: the rendered window, the tool, the panel, the replayed polygons.

docker run --rm --network none -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \
    python3 /src/tests/qgis_headless/check_segmentation.py

With FM_SAM_MODELS (the ONNX files), FM_SAM_ORTHO and FM_SAM_BUILDINGS, and onnxruntime installed, it also
runs the real model on the orthophoto. The stub model finds the bright pixels of the rendered image: a
polygon in the right place proves the window reached the model and came back on the map.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FILTERMATE_LOG_DIR", tempfile.mkdtemp(prefix="fm_seg_logs_"))

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import (Qgis, QgsApplication, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsRectangle)
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.PyQt.QtCore import QBuffer, QEventLoop, QIODevice, QSize, QT_VERSION_STR, QTimer
from qgis.PyQt.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "fm_segmentation_check"
for part in ("", "core", "core.domain", "core.ports", "adapters", "adapters.qgis", "adapters.qgis.coverage_layers",
             "ui", "ui.controllers", "ui.tools", "ui.widgets", "ui.widgets.coverage_panels"):
    module = types.ModuleType(PACKAGE + ("." + part if part else ""))
    module.__path__ = [str(ROOT / part.replace(".", "/"))]
    sys.modules[module.__name__] = module

app = QgsApplication([], True)
app.initQgis()
print(f"QGIS {Qgis.QGIS_VERSION}, Qt {QT_VERSION_STR}", flush=True)
adapter = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.raster_adapter")
segmentation = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.segmentation")
jobs = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.source_jobs")
criteria = importlib.import_module(PACKAGE + ".core.domain.raster_filter_criteria")
panels = importlib.import_module(PACKAGE + ".ui.widgets.coverage_panels.raster_exploring_panel")
controllers = importlib.import_module(PACKAGE + ".ui.controllers.segmentation_controller")

failures = []


def check(name, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + name + (f" : {detail}" if detail != "" else ""), flush=True)
    if not condition:
        failures.append(name)


def spin(until, timeout=60000):
    loop, timer = QEventLoop(), QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: loop.quit() if until() else None)
    timer.start()
    QTimer.singleShot(timeout, loop.quit)
    loop.exec()
    timer.stop()
    return until()


SQUARE = (240, 400, 200, 300)  # rows then columns of the bright square, in pixels of the raster


def make_raster(folder):
    path = str(Path(folder) / "ortho.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 800, 800, 3, gdal.GDT_Byte)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(2154)
    ds.SetProjection(crs.ExportToWkt())
    ds.SetGeoTransform((600000.0, 0.5, 0, 6100400.0, 0, -0.5))
    for number in (1, 2, 3):
        array = np.full((800, 800), 30, dtype=np.uint8)
        array[SQUARE[0]:SQUARE[1], SQUARE[2]:SQUARE[3]] = 230
        ds.GetRasterBand(number).WriteArray(array)
    ds = None
    layer = QgsRasterLayer(path, "Ortho", "gdal")
    assert layer.isValid()
    return layer


class BrightModel:
    """Finds the bright pixels of the image it was given."""

    input_size = 1024

    def __init__(self):
        self.embedded = 0

    def embed(self, rgb):
        assert rgb.shape == (1024, 1024, 3) and rgb.dtype == np.uint8
        self.embedded += 1
        return rgb

    def predict(self, embedding, points, labels, box):
        assert len(points) == len(labels)
        return embedding[:, :, 0] > 128, 0.9


class Host:
    """The little of CoverageModeController the segmentation controller uses."""

    def __init__(self, layer, panel, canvas):
        self._active_layer, self._raster_panel, self._canvas = layer, panel, canvas
        self._torn_down = False
        self.picker_states = []

    def _iface(self):
        return types.SimpleNamespace(mapCanvas=lambda: self._canvas)

    def _base_raster(self, layer):
        return layer

    @staticmethod
    def _raster_capability(_layer):
        return types.SimpleNamespace(has_raw_values=True)

    @staticmethod
    def _call(target, method, *args):
        getattr(target, method)(*args)

    def _tool_on_map(self, tool):
        return tool is not None and self._canvas.mapTool() is tool

    def _release_map_tool(self, tool, previous):
        if self._canvas.mapTool() is not tool:
            return
        if previous is not None:
            self._canvas.setMapTool(previous)
        else:
            self._canvas.unsetMapTool(tool)

    def _show_picker_state(self, active):
        self.picker_states.append(active)


def test_tool_flow(layer):
    QgsProject.instance().addMapLayer(layer)
    canvas = QgsMapCanvas()
    canvas.resize(QSize(600, 600))
    canvas.setDestinationCrs(layer.crs())
    canvas.setLayers([layer])
    canvas.setExtent(layer.extent())
    panel = panels.RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(layer))
    model = BrightModel()
    segmentation.find_provider = lambda: model
    controllers_segmentation = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.segmentation")
    controllers_segmentation.find_provider = lambda: model
    host = Host(layer, panel, canvas)
    tool_controller = controllers.SegmentationController(host)
    tool_controller.activate()
    check("the tool goes on the map", tool_controller.on_map())

    extent = layer.extent()
    click = QgsPointXY(extent.xMinimum() + 250 * 0.5, extent.yMaximum() - 320 * 0.5)
    tool_controller._on_point(click, True)
    check("a first click encodes in a task", spin(lambda: tool_controller._task is None and tool_controller.session_info() is not None))
    check("the model saw one window", model.embedded == 1, model.embedded)
    session = tool_controller.session_info()
    check("the click is a pixel of the window", session is not None and session.points[0][0] > 0 and session.window.contains(click.x(), click.y()))
    geometry = session.geometry()
    expected = QgsRectangle(extent.xMinimum() + SQUARE[2] * 0.5, extent.yMaximum() - SQUARE[1] * 0.5,
                            extent.xMinimum() + SQUARE[3] * 0.5, extent.yMaximum() - SQUARE[0] * 0.5)
    truth = QgsGeometry.fromRect(expected)
    iou = geometry.intersection(truth).area() / geometry.combine(truth).area()
    check("the polygon lands on the bright square", iou > 0.97, round(iou, 4))

    tool_controller._on_point(QgsPointXY(click.x() + 2.0, click.y()), False)
    check("a second click reuses the window", model.embedded == 1 and len(session.points) == 2, model.embedded)
    tool_controller.validate()
    selection = panel.selection()
    check("validate adds the object to the panel", selection is not None and len(selection.segments) == 1)
    check("the panel state keeps it", criteria.RasterSelection.from_dict(panel.state()["pipette_selection"]).segments == selection.segments)
    tool_controller._on_point(click, True)
    check("the prompts were reset", len(session.points) == 1)
    tool_controller.clear()
    check("escape leaves the validated object", panel.selection() is not None and not session.has_prompts)

    # Refused prompts, then a right click alone, then a click outside the raster.
    tool_controller._on_point(QgsPointXY(click.x(), click.y()), False)
    check("a right click cannot start an object", not session.has_prompts)
    tool_controller._on_point(QgsPointXY(extent.xMaximum() + 500.0, click.y()), True)
    check("a click off the raster encodes nothing", tool_controller._task is None and model.embedded == 1, model.embedded)

    # Another QGIS tool takes the map: the prompts leave with it.
    tool_controller._on_point(click, True)
    check("a new object started", session.has_prompts)
    other = QgsMapToolPan(canvas)
    canvas.setMapTool(other)
    check("another tool drops the prompts", not session.has_prompts and host.picker_states[-1] is False, host.picker_states[-3:])
    tool_controller.activate()
    check("the tool can come back", tool_controller.on_map())
    tool_controller.deactivate()
    check("the map goes back to the tool it replaced", canvas.mapTool() is other, canvas.mapTool())

    # A layer change deletes the tool: it must have left the map at once.
    tool_controller.activate()
    tool_controller.drop()
    check("drop releases the map at once", canvas.mapTool() is other, canvas.mapTool())

    # Panel: the target, the validated objects, the state.
    panel.set_segmentation_readiness(True, True)
    check("the target shows", not panel._target_buttons[panels.PICK_SEGMENT].isHidden())
    check("ready: nothing to install", panel._segment_install_label.isHidden() and panel._segment_install_button.isHidden())
    panel._target_buttons[panels.PICK_SEGMENT].setChecked(True)
    check("the segment widget shows", not panel._segment_widget.isHidden() and panel.pick_target() == panels.PICK_SEGMENT)
    check("the objects are selected", panel.selection() is not None and len(panel.selection().segments) == 1)
    state = panel.state()
    panel._target_buttons[panels.PICK_SIMILAR].setChecked(True)
    check("another target sets them aside", panel.selection() is None and panel._segments != [])
    panel._target_buttons[panels.PICK_SEGMENT].setChecked(True)
    check("they come back with the target", panel.selection() is not None)
    bands = panel._pipette_bands
    panel._pipette_bands = []
    check("no band selected, polygons still select", panels.build_raster_selection(panel.state()) is not None)
    panel._pipette_bands = bands
    panel.set_pick_target(panels.PICK_OBJECT)
    check("a rail tool leaves the target too", panel.selection() is None and panel._segment_widget.isHidden())
    panel.set_pick_target(panels.PICK_SIMILAR)
    panel.restore_state(state)
    check("the state brings the objects and the target back",
          panel.selection() is not None and panel.pick_target() == panels.PICK_SEGMENT and len(panel._segments) == 1)
    panel.set_segmentation_readiness(False, False)
    check("without the runtime and the model the target stays", not panel._target_buttons[panels.PICK_SEGMENT].isHidden()
          and panel.pick_target() == panels.PICK_SEGMENT)
    check("and says what to install", not panel._segment_install_label.isHidden() and not panel._segment_install_button.isHidden()
          and "onnxruntime" in panel._segment_install_label.text() and "62" in panel._segment_install_button.text())
    panel.set_segmentation_readiness(True, False)
    check("with the runtime only the download is offered", panel._segment_install_label.isHidden() and not panel._segment_install_button.isHidden())
    panel.set_segmentation_readiness(True, False, True)
    check("during a download the button waits", not panel._segment_install_button.isEnabled())
    panel.set_segmentation_readiness(False, False, False, True)
    check("while pip runs no command is shown", "background" in panel._segment_install_label.text()
          and not panel._segment_install_label.isHidden())
    panel.set_segmentation_readiness(True, True)
    check("installed: no button", panel._segment_install_button.isHidden())
    panel.offer_model_repair()
    check("damaged files can be repaired", not panel._segment_install_button.isHidden() and panel._segment_install_button.isEnabled())
    panel.set_segmentation_readiness(True, True)
    panel.restore_state(state)
    panel.clear_segments()
    check("clear forgets the objects", panel.selection() is None and panel._segments == [])
    check("and the button says so", not panel._segment_clear_button.isEnabled())
    return selection


class _TileHandler(BaseHTTPRequestHandler):
    """A web map where every tile is bright."""

    def do_GET(self):  # noqa: N802 - http.server interface
        image = QImage(256, 256, QImage.Format.Format_RGBA8888)
        image.fill(QColor(230, 230, 230, 255))
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        body = bytes(buffer.data())
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def test_web_service():
    """A service is rendered itself: no local sample, and a window sized by what the map shows."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TileHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/%7Bz%7D/%7Bx%7D/%7By%7D.png"
    layer = QgsRasterLayer(f"type=xyz&url={url}&zmax=19&zmin=0", "Web", "wms")
    check("the web layer opens", layer.isValid(), layer.error().summary() if not layer.isValid() else "")
    canvas = QgsMapCanvas()
    canvas.resize(QSize(600, 600))
    canvas.setDestinationCrs(layer.crs())
    center = QgsPointXY(240000.0, 5900000.0)
    canvas.setExtent(QgsRectangle(center.x() - 500.0, center.y() - 500.0, center.x() + 500.0, center.y() + 500.0))
    panel = panels.RasterExploringPanel()
    model = BrightModel()
    importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.segmentation").find_provider = lambda: model
    host = Host(layer, panel, canvas)
    host._raster_capability = staticmethod(lambda _layer: types.SimpleNamespace(has_raw_values=False))

    def no_sample(_layer):
        raise RuntimeError('Raster sample is not ready')

    host._base_raster = no_sample
    controller = controllers.SegmentationController(host)
    controller._on_point(center, True)
    check("the service is encoded without a local sample", spin(lambda: controller._task is None and controller.session_info() is not None),
          panel._segment_status.text())
    session = controller.session_info()
    if session is not None:
        check("the window follows what the map shows", 0.9 < session.window.cell < 1.3, session.window.cell)
        check("the model received the tiles", model.embedded == 1 and session.mask is not None and session.mask.any())
    server.shutdown()
    return None


def test_replay(layer, selection):
    replayed = criteria.RasterSelection.from_dict(selection.to_dict())
    job = jobs.RasterSourceJob(layer, replayed, filter_source=False)
    request = types.SimpleNamespace(buffer_value=0.0, buffer_segments=5, buffer_type='Round', methods=())
    geometry = job.compute(request, lambda: False)
    check("a replay without any model gives the polygons", not geometry.isEmpty() and job.message == "", job.message)
    check("it counts the kept pixels", job.details.get("kept_pixels", 0) > 10000, job.details.get("kept_pixels"))
    clip = jobs.RasterSourceJob(layer, replayed, filter_source=True)
    check("the source is masked by a clip, not a formula", clip.clips_source)


def test_real_model():
    models, ortho, buildings = (os.environ.get(n) for n in ("FM_SAM_MODELS", "FM_SAM_ORTHO", "FM_SAM_BUILDINGS"))
    if not (models and ortho and buildings):
        print("skip real model (FM_SAM_MODELS, FM_SAM_ORTHO, FM_SAM_BUILDINGS)", flush=True)
        return
    SamOnnxProvider = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.sam_model").SamOnnxProvider
    provider = SamOnnxProvider(models)
    layer = QgsRasterLayer(ortho, "Ortho", "gdal")
    extent = layer.extent()
    source = ogr.Open(buildings)
    feature_layer = source.GetLayerByName("batiment")
    ious = []
    for feature in feature_layer:
        wkt = feature.GetGeometryRef().ExportToWkt()
        truth = QgsGeometry.fromWkt(wkt)
        if len(ious) >= 15 or not extent.contains(truth.boundingBox()):
            continue
        point = truth.poleOfInaccessibility(0.25)[0].asPoint()
        window = segmentation.plan_window(point.x(), point.y(), (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                                          extent.width() / layer.width(), 100.0, provider.input_size)
        results = []
        task = segmentation.SegmentationEmbedTask(layer.source(), "gdal", layer.renderer().clone(), layer.crs(), window, provider,
                                                  lambda t, ok: results.append((t, ok)))
        QgsApplication.taskManager().addTask(task)
        if not spin(lambda: results, 120000) or not results[0][1]:
            check("the real model encoded a window", False, results and results[0][0].error)
            return
        session = segmentation.SegmentationSession(provider, window, results[0][0].embedding)
        session.add_point(point.x(), point.y(), True)
        session.predict()
        geometry = session.geometry()
        ious.append(geometry.intersection(truth).area() / geometry.combine(truth).area() if geometry and not geometry.isEmpty() else 0.0)
    median = float(np.median(ious))
    check("real model through the QGIS rendering, same order as the benchmark", median > 0.5, f"median IoU {median:.3f} over {len(ious)}")


with tempfile.TemporaryDirectory() as folder:
    raster = make_raster(folder)
    validated = test_tool_flow(raster)
    test_replay(raster, validated)
    test_web_service()
    test_real_model()
    QgsProject.instance().removeAllMapLayers()

print(f"{len(failures)} failure(s)", flush=True)
app.exitQgis()
os._exit(1 if failures else 0)
