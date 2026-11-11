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
import time
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import faulthandler  # noqa: E402
faulthandler.enable()
os.environ.setdefault("FILTERMATE_LOG_DIR", tempfile.mkdtemp(prefix="fm_seg_logs_"))

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import (NULL, Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsGeometry, QgsPointXY, QgsProject,
                       QgsRasterLayer, QgsRectangle)
from qgis.gui import QgsMapCanvas, QgsMapToolPan
from qgis.PyQt.QtCore import QBuffer, QEventLoop, QIODevice, QSize, QT_VERSION_STR, QTimer
from qgis.PyQt.QtGui import QColor, QImage

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "fm_segmentation_check"
for part in ("", "core", "core.agent", "core.domain", "core.ports", "adapters", "adapters.agent", "adapters.public_api",
             "adapters.qgis", "adapters.qgis.coverage_layers",
             "ui", "ui.controllers", "ui.tools", "ui.widgets", "ui.widgets.coverage_panels",
             "processing", "processing.algorithms"):
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


def test_sam_confirmation(panel):
    """Nothing is installed without an answer, the question comes once, one answer installs the runtime then the model."""
    from qgis.PyQt.QtWidgets import QMessageBox
    original = QMessageBox.question
    answers, asked, runtime, model = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes,
                                      QMessageBox.StandardButton.Yes], [], [], []
    QMessageBox.question = lambda *args, **kwargs: asked.append(args) or answers.pop(0)
    panel.segmentRuntimeInstallRequested.connect(lambda: runtime.append(True))
    panel.segmentModelInstallRequested.connect(lambda: model.append(True))
    try:
        panel._target_buttons[panels.PICK_SIMILAR].setChecked(True)
        panel._runtime_asked = False
        panel.set_segmentation_readiness(False, False)
        panel._target_buttons[panels.PICK_OBJECT].setChecked(True)
        check("the first object target asks", len(asked) == 1, len(asked))
        check("a refusal installs nothing", runtime == [] and model == [])
        check("and the button stays", not panel._segment_install_button.isHidden() and panel._segment_install_button.isEnabled())
        check("the colour engine works meanwhile", panel.object_engine() == panels.ENGINE_COLOR and not panel._object_settings.isHidden())
        panel._target_buttons[panels.PICK_SIMILAR].setChecked(True)
        panel._target_buttons[panels.PICK_SIMILAR_OBJECTS].setChecked(True)
        check("the question is not repeated", len(asked) == 1, len(asked))
        panel._segment_install_button.click()
        check("the button asks again and a yes starts with the runtime", len(asked) == 2 and runtime == [True] and model == [],
              (len(asked), runtime, model))
        check("and it waits", not panel._segment_install_button.isEnabled())
        panel.set_segmentation_readiness(True, False)
        panel._segment_install_button.click()
        check("with the runtime there, a yes downloads the model", model == [True], model)
    finally:
        QMessageBox.question = original


def make_shapes(folder):
    """A clicked square, a square like it, a square nine times larger and a strip of the clicked area."""
    path = str(Path(folder) / "shapes.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 800, 800, 3, gdal.GDT_Byte)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(2154)
    ds.SetProjection(crs.ExportToWkt())
    ds.SetGeoTransform((600000.0, 0.5, 0, 6100400.0, 0, -0.5))
    for number in (1, 2, 3):
        array = np.full((800, 800), 30, dtype=np.uint8)
        for rows, cols in SHAPES.values():
            array[rows[0]:rows[1], cols[0]:cols[1]] = 230
        ds.GetRasterBand(number).WriteArray(array)
    ds = None
    layer = QgsRasterLayer(path, "Shapes", "gdal")
    assert layer.isValid()
    return layer


SHAPES = {"clicked": ((100, 160), (100, 160)), "alike": ((100, 158), (500, 562)),
          "large": ((450, 630), (80, 260)), "strip": ((450, 462), (500, 800))}


def shape_geometry(layer, name):
    (r0, r1), (c0, c1) = SHAPES[name]
    extent = layer.extent()
    return QgsGeometry.fromRect(QgsRectangle(extent.xMinimum() + c0 * 0.5, extent.yMaximum() - r1 * 0.5,
                                             extent.xMinimum() + c1 * 0.5, extent.yMaximum() - r0 * 0.5))


def ready_panel(layer):
    panel = panels.RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(layer))
    panel.set_segmentation_readiness(True, True)
    return panel


def install_model(model):
    segmentation.find_provider = lambda: model


def test_tool_flow(layer):
    QgsProject.instance().addMapLayer(layer)
    canvas = QgsMapCanvas()
    canvas.resize(QSize(600, 600))
    canvas.setDestinationCrs(layer.crs())
    canvas.setLayers([layer])
    canvas.setExtent(layer.extent())
    panel = ready_panel(layer)
    panel.set_pick_target(panels.PICK_OBJECT)
    model = BrightModel()
    install_model(model)
    host = Host(layer, panel, canvas)
    tool_controller = controllers.SegmentationController(host)
    tool_controller.activate()
    check("the tool goes on the map", tool_controller.on_map())

    extent = layer.extent()
    click = QgsPointXY(extent.xMinimum() + 250 * 0.5, extent.yMaximum() - 320 * 0.5)
    expected = QgsRectangle(extent.xMinimum() + SQUARE[2] * 0.5, extent.yMaximum() - SQUARE[1] * 0.5,
                            extent.xMinimum() + SQUARE[3] * 0.5, extent.yMaximum() - SQUARE[0] * 0.5)
    truth = QgsGeometry.fromRect(expected)

    def segment_iou(index=0):
        geometry = QgsGeometry.fromWkt(panel._segments[index])
        return geometry.intersection(truth).area() / geometry.combine(truth).area()

    tool_controller._on_point(click, True)
    check("a first click encodes in a task", spin(lambda: tool_controller._task is None and tool_controller.session_info() is not None))
    check("the model saw one window", model.embedded == 1, model.embedded)
    check("a click adds the object at once, no Enter", len(panel._segments) == 1 and panel.selection() is not None,
          len(panel._segments))
    check("the polygon lands on the bright square", segment_iou() > 0.97, round(segment_iou(), 4) if panel._segments else None)
    check("the panel state keeps it", criteria.RasterSelection.from_dict(panel.state()["pipette_selection"]).segments == tuple(panel._segments))

    session = tool_controller.session_info()
    tool_controller._on_point(QgsPointXY(click.x() + 2.0, click.y()), True, True)
    check("Shift+click redraws the last object", len(panel._segments) == 1 and len(session.points) == 2 and model.embedded == 1,
          (len(panel._segments), len(session.points)))
    tool_controller._on_point(QgsPointXY(click.x() + 4.0, click.y()), False)
    check("a right click trims it", len(panel._segments) == 1 and session.labels[-1] == 0, session.labels)
    tool_controller.clear()
    check("Escape removes the last object", panel._segments == [] and panel.selection() is None, len(panel._segments))
    tool_controller._on_point(click, False)
    check("a right click without an object starts nothing", panel._segments == [] and not session.has_prompts)
    tool_controller._on_point(QgsPointXY(extent.xMaximum() + 500.0, click.y()), True)
    check("a click off the raster encodes nothing", tool_controller._task is None and model.embedded == 1, model.embedded)

    tool_controller._on_point(click, True)
    tool_controller._on_point(QgsPointXY(click.x() + 6.0, click.y() + 6.0), True)
    check("the same object clicked twice is kept once", len(panel._segments) == 1, len(panel._segments))
    tool_controller._on_box(QgsRectangle(expected.xMinimum() - 5, expected.yMinimum() - 5, expected.xMaximum() + 5, expected.yMaximum() + 5))
    check("a box frames an object", len(panel._segments) == 1 and session.box is not None)

    # The object under the mouse, outlined before any click.
    tool_controller._on_hover(click)
    check("the object under the mouse is outlined", spin(lambda: tool_controller._outline is not None and tool_controller._outline.visible, 3000))
    hovered = tool_controller._outline.geometry() if tool_controller._outline is not None else None
    check("on the object", hovered is not None and hovered.intersects(QgsGeometry.fromPointXY(click)))
    tool_controller._on_point(click, True)
    check("a click hides that outline", not tool_controller._outline.visible)

    # Another QGIS tool takes the map: the prompts leave with it, the objects stay.
    other = QgsMapToolPan(canvas)
    canvas.setMapTool(other)
    check("another tool drops the prompts", not session.has_prompts and host.picker_states[-1] is False, host.picker_states[-3:])
    check("the objects stay", len(panel._segments) == 1)
    tool_controller.activate()
    check("the tool can come back", tool_controller.on_map())
    tool_controller.deactivate()
    check("the map goes back to the tool it replaced", canvas.mapTool() is other, canvas.mapTool())
    tool_controller.activate()
    tool_controller.drop()
    check("drop releases the map at once", canvas.mapTool() is other, canvas.mapTool())
    selection = panel.selection()

    # Panel: three targets, the engine, the objects of each engine, the state.
    check("three targets, Segment is gone", sorted(panel._target_buttons) == sorted(panels.PICK_TARGETS) and len(panels.PICK_TARGETS) == 3)
    check("SAM in use: its block shows, the colour settings hide",
          not panel._segment_widget.isHidden() and panel._object_settings.isHidden() and panel.object_engine() == panels.ENGINE_SAM)
    engines = []
    panel.engineChanged.connect(engines.append)
    panel._engine_combo.setCurrentIndex(panel._engine_combo.findData(panels.ENGINE_COLOR))
    check("the colour engine takes over", engines == [panels.ENGINE_COLOR] and not panel._object_settings.isHidden()
          and panel.selection() is None and panel._segments != [], engines)
    panel._engine_combo.setCurrentIndex(panel._engine_combo.findData(panels.ENGINE_SAM))
    check("SAM's objects come back with it", engines[-1] == panels.ENGINE_SAM and panel.selection() is not None)
    state = panel.state()
    panel._target_buttons[panels.PICK_SIMILAR].setChecked(True)
    check("similar pixels set the objects aside", panel.selection() is None and panel._segment_widget.isHidden())
    panel._target_buttons[panels.PICK_SIMILAR_OBJECTS].setChecked(True)
    check("they come back with an object target", panel.selection() is not None and not panel._similar_widget.isHidden())
    bands = panel._pipette_bands
    panel._pipette_bands = []
    check("no band selected, polygons still select", panels.build_raster_selection(panel.state()) is not None)
    panel._pipette_bands = bands
    panel.set_pick_target(panels.PICK_SIMILAR)
    panel.restore_state(state)
    check("the state brings the objects, the target and the engine back",
          panel.selection() is not None and panel.pick_target() == panels.PICK_OBJECT and panel.object_engine() == panels.ENGINE_SAM)
    old = dict(state, pipette_target="segment")
    old.pop("pipette_engine")
    panel.set_pick_target(panels.PICK_SIMILAR)
    panel.restore_state(old)
    check("a state of the Segment target opens on the clicked object", panel.pick_target() == panels.PICK_OBJECT and panel.selection() is not None)

    panel.set_segmentation_readiness(False, False)
    check("without SAM the objects wait, the colour engine works", panel.object_engine() == panels.ENGINE_COLOR
          and panel.selection() is None and len(panel._segments) == 1)
    check("and the panel offers SAM", not panel._segment_install_label.isHidden() and not panel._segment_install_button.isHidden()
          and "SAM" in panel._segment_install_button.text())
    test_sam_confirmation(panel)
    panel.set_segmentation_readiness(True, False, True)
    check("during a download the button waits", not panel._segment_install_button.isEnabled())
    panel.set_segmentation_readiness(False, False, False, True)
    check("while pip runs it says so", "background" in panel._segment_install_label.text() and not panel._segment_install_label.isHidden())
    panel.set_segmentation_readiness(True, True)
    check("installed: no button, SAM takes over", panel._segment_install_button.isHidden() and panel.object_engine() == panels.ENGINE_SAM)
    panel.offer_model_repair()
    check("damaged files can be repaired", not panel._segment_install_button.isHidden() and panel._segment_install_button.isEnabled())
    panel.set_segmentation_readiness(True, True)
    panel.restore_state(state)
    asked = []
    panel.segmentsLayerRequested.connect(lambda: asked.append(True))
    panel._segment_layer_button.click()
    check("To layer shows with SAM and asks for the layer", not panel._segment_layer_button.isHidden() and asked == [True])
    panel.clear_segments()
    check("clear forgets the objects", panel.selection() is None and panel._segments == [])
    check("and the buttons say so", not panel._segment_clear_button.isEnabled() and not panel._segment_layer_button.isEnabled())
    return selection


def test_features_algorithm(layer):
    """filtermate:segment_from_features with the stub model: a footprint and a point on the bright square."""
    from qgis.core import (QgsCoordinateTransform, QgsFeature, QgsProcessingContext, QgsProcessingFeedback,
                           QgsVectorLayer)
    module = importlib.import_module(PACKAGE + ".processing.algorithms.segmentation_algorithm")
    model = BrightModel()
    install_model(model)
    ready = segmentation.model_state
    segmentation.model_state = lambda: segmentation.ModelState(True, True)
    extent = layer.extent()
    truth = QgsGeometry.fromRect(QgsRectangle(extent.xMinimum() + SQUARE[2] * 0.5, extent.yMaximum() - SQUARE[1] * 0.5,
                                              extent.xMinimum() + SQUARE[3] * 0.5, extent.yMaximum() - SQUARE[0] * 0.5))
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    to_wgs84 = QgsCoordinateTransform(layer.crs(), wgs84, QgsProject.instance())

    def guide(kind, geometries, extra=""):
        guides = QgsVectorLayer(f"{kind}?crs=EPSG:4326&field=name:string{extra}", kind, "memory")
        features = []
        for name, geometry in geometries:
            geometry = QgsGeometry(geometry)
            geometry.transform(to_wgs84)
            feature = QgsFeature(guides.fields())
            feature.setAttributes([name] + [7] * (guides.fields().count() - 1))
            feature.setGeometry(geometry)
            features.append(feature)
        guides.dataProvider().addFeatures(features)
        return guides

    def run(guides):
        algorithm = module.SegmentFromFeaturesAlgorithm().create()
        context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
        context.setProject(QgsProject.instance())
        results, ok = algorithm.run({"RASTER": layer, "FEATURES": guides, "OUTPUT": "memory:"}, context, feedback)
        return (context.takeResultLayer(results["OUTPUT"]) if ok else None), feedback

    try:
        footprint = QgsGeometry.fromRect(truth.boundingBox().buffered(-3.0))  # a footprint a little off the roof
        off = QgsGeometry.fromRect(QgsRectangle(extent.xMaximum() + 50, extent.yMaximum() + 50,
                                                extent.xMaximum() + 60, extent.yMaximum() + 60))
        drawn, feedback = run(guide("Polygon", [("roof", footprint), ("away", off)]))
        rows = [(f["name"], f["sam_score"], f["sam_iou"], f.geometry()) for f in drawn.getFeatures()] if drawn else []
        check("the algorithm draws one object per footprint on the raster, the one off it skipped",
              [r[0] for r in rows] == ["roof"], [r[:3] for r in rows])
        if rows:
            check("on the bright square, in the CRS of the raster",
                  segmentation.overlap(rows[0][3], truth) > 0.97 and drawn.crs() == layer.crs(),
                  (round(segmentation.overlap(rows[0][3], truth), 3), drawn.crs().authid()))
            check("with the score and the overlap with the footprint", rows[0][1] == 0.9 and 0.8 < rows[0][2] < 1.0, rows[0][1:3])
        drawn, _ = run(guide("Point", [("pond", truth.centroid())]))
        rows = [(f["name"], f["sam_iou"]) for f in drawn.getFeatures()] if drawn else []
        check("a point is a click: its object, no overlap", len(rows) == 1 and rows[0][1] in (None, NULL), rows)
        check("one window for the two runs each", model.embedded == 2, model.embedded)
        segmentation.model_state = lambda: segmentation.ModelState(True, False)
        drawn, feedback = run(guide("Point", [("pond", truth.centroid())]))
        check("without SAM the algorithm says how to install it", drawn is None)
        segmentation.model_state = lambda: segmentation.ModelState(True, True)

        centre = truth.centroid().asPoint()
        away = QgsPointXY(extent.xMaximum() + 500, extent.yMaximum() + 500)
        several = QgsGeometry.fromMultiPointXY([away, centre, QgsPointXY(centre.x() + 1, centre.y())])
        drawn, _ = run(guide("MultiPoint", [("pond", several)]))
        rows = [f.geometry() for f in drawn.getFeatures()] if drawn else []
        check("a multipoint whose first point is off the raster is drawn from the others",
              len(rows) == 1 and segmentation.overlap(rows[0], truth) > 0.97, len(rows))

        drawn, _ = run(guide("Polygon", [("roof", footprint)], "&field=sam_score:integer&field=SAM_IOU:double"))
        rows = list(drawn.getFeatures()) if drawn else []
        names = drawn.fields().names() if drawn else []
        check("source fields named like the outputs give way to them, any case",
              names == ["name", "sam_score", "sam_iou"] and rows and rows[0]["sam_score"] == 0.9, names)

        bowtie = QgsGeometry.fromWkt("POLYGON(({0} {1}, {2} {3}, {2} {1}, {0} {3}, {0} {1}))".format(
            *[round(v, 3) for v in (truth.boundingBox().xMinimum() + 2, truth.boundingBox().yMinimum() + 2,
                                     truth.boundingBox().xMaximum() - 2, truth.boundingBox().yMaximum() - 2)]))
        tiny = QgsGeometry.fromRect(QgsRectangle(centre.x(), centre.y(), centre.x() + 0.2, centre.y() + 0.2))
        drawn, _ = run(guide("Polygon", [("bowtie", bowtie), ("tiny", tiny)]))
        rows = {f["name"]: f["sam_iou"] for f in drawn.getFeatures()} if drawn else {}
        check("an invalid footprint is compared once made valid, one under a pixel is prompted by its point",
              set(rows) == {"bowtie", "tiny"} and rows["bowtie"] > 0.3, rows)

        # In the background, as the toolbox runs it: a task of the pool, the window drawn in its thread.
        from qgis.core import QgsProcessingAlgRunnerTask
        algorithm = module.SegmentFromFeaturesAlgorithm().create()
        context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
        context.setProject(QgsProject.instance())
        guides = guide("Polygon", [("roof", footprint)])  # held: the task reads it from its thread
        task = QgsProcessingAlgRunnerTask(algorithm, {"RASTER": layer, "FEATURES": guides, "OUTPUT": "memory:"},
                                          context, feedback)
        done = []
        task.executed.connect(lambda ok, results: done.append((ok, results)))
        QgsApplication.taskManager().addTask(task)
        finished = spin(lambda: done, 60000)
        drawn = context.takeResultLayer(done[0][1]["OUTPUT"]) if finished and done[0][0] else None
        check("in a background task too", drawn is not None and drawn.featureCount() == 1, done)

        # As a step of a model run in the background: the step is prepared on the thread of the model.
        from qgis.core import (QgsProcessingModelAlgorithm, QgsProcessingModelChildAlgorithm,
                               QgsProcessingModelChildParameterSource, QgsProcessingModelOutput,
                               QgsProcessingModelParameter, QgsProcessingParameterFeatureSource,
                               QgsProcessingParameterRasterLayer, QgsProcessingProvider)

        class Provider(QgsProcessingProvider):
            def loadAlgorithms(self):
                self.addAlgorithm(module.SegmentFromFeaturesAlgorithm())

            def id(self):
                return "filtermate"

            def name(self):
                return "FilterMate"

        provider = Provider()
        QgsApplication.processingRegistry().addProvider(provider)
        model = QgsProcessingModelAlgorithm("objects", "checks")
        model.addModelParameter(QgsProcessingParameterRasterLayer("ortho", "ortho"), QgsProcessingModelParameter("ortho"))
        model.addModelParameter(QgsProcessingParameterFeatureSource("guides", "guides"), QgsProcessingModelParameter("guides"))
        child = QgsProcessingModelChildAlgorithm("filtermate:segment_from_features")
        child.setChildId("sam")
        child.addParameterSources("RASTER", [QgsProcessingModelChildParameterSource.fromModelParameter("ortho")])
        child.addParameterSources("FEATURES", [QgsProcessingModelChildParameterSource.fromModelParameter("guides")])
        output = QgsProcessingModelOutput("objects", "objects")
        output.setChildOutputName("OUTPUT")
        child.setModelOutputs({"objects": output})
        model.addChildAlgorithm(child)
        context, feedback = QgsProcessingContext(), QgsProcessingFeedback()
        context.setProject(QgsProject.instance())
        task = QgsProcessingAlgRunnerTask(model, {"ortho": layer, "guides": guides, "sam:objects": "memory:"}, context, feedback)
        done = []
        task.executed.connect(lambda ok, results: done.append((ok, results)))
        QgsApplication.taskManager().addTask(task)
        finished = spin(lambda: done, 60000)
        output_id = next((value for key, value in (done[0][1] if done else {}).items() if "objects" in key), None)
        drawn = context.takeResultLayer(output_id) if finished and done[0][0] and output_id else None
        check("as a step of a model run in the background", drawn is not None and drawn.featureCount() == 1,
              (done, feedback.textLog()[-300:] if hasattr(feedback, "textLog") else ""))
        QgsApplication.processingRegistry().removeProvider(provider)
    finally:
        segmentation.model_state = ready


def test_objects_layer(layer):
    extent = layer.extent()
    x, y = extent.xMinimum(), extent.yMinimum()
    first = QgsGeometry.fromRect(QgsRectangle(x + 10, y + 10, x + 20, y + 30)).asWkt()
    second = QgsGeometry.fromRect(QgsRectangle(x + 50, y + 50, x + 54, y + 55)).asWkt()
    objects, skipped = segmentation.objects_layer([first, "POLYGON((", second], layer.crs(), "ortho objects",
                                                  lambda geometry: geometry.area())
    features = list(objects.getFeatures())
    check("one feature per object, the unreadable one counted", len(features) == 2 and skipped == 1, (len(features), skipped))
    check("in the CRS of the raster", objects.crs() == layer.crs(), objects.crs().authid())
    check("multipolygons", all(feature.geometry().isMultipart() for feature in features))
    check("numbered, with their area", [feature.attributes() for feature in features] == [[1, 200.0], [2, 20.0]],
          [feature.attributes() for feature in features])
    custom = QgsCoordinateReferenceSystem.fromProj("+proj=tmerc +lat_0=42 +lon_0=2 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m")
    objects, _ = segmentation.objects_layer([first], custom, "custom", None)
    check("a CRS without authid is kept, no area without a measure",
          objects.crs() == custom and [f.attributes() for f in objects.getFeatures()] == [[1, None]],
          (objects.crs().toProj(), [f.attributes() for f in objects.getFeatures()]))

    # The controller adds the layer to the project, outlined, with the area on the ellipsoid.
    coverage = importlib.import_module(PACKAGE + ".ui.controllers.coverage_mode_controller")
    messages = []
    bar = types.SimpleNamespace(pushSuccess=lambda *a: messages.append(("ok",) + a),
                                pushWarning=lambda *a: messages.append(("warning",) + a))
    host = types.SimpleNamespace(_active_layer=layer, _raster_panel=types.SimpleNamespace(_segments=[first, second]),
                                 tr=lambda text: text, _iface=lambda: types.SimpleNamespace(messageBar=lambda: bar))
    host._ground_area = coverage.CoverageModeController._ground_area
    before = set(QgsProject.instance().mapLayers())
    coverage.CoverageModeController._on_segments_layer_requested(host)
    added = [QgsProject.instance().mapLayer(i) for i in set(QgsProject.instance().mapLayers()) - before]
    check("the controller adds one layer of the objects", len(added) == 1 and added[0].featureCount() == 2
          and added[0].name() == f"{layer.name()} objects", [a.name() for a in added])
    if added:
        areas = [f["area_m2"] for f in added[0].getFeatures()]
        check("areas in square metres on the ellipsoid", abs(areas[0] - 200.0) < 2 and abs(areas[1] - 20.0) < 0.5, areas)
        symbol = added[0].renderer().symbol()
        check("outlined, the raster stays visible", symbol.color().alpha() == 0, symbol.color().name())
        QgsProject.instance().removeMapLayer(added[0].id())
    check("and says so", messages and messages[-1][0] == "ok" and "2" in messages[-1][2], messages)
    host._raster_panel._segments = ["POLYGON(("]
    coverage.CoverageModeController._on_segments_layer_requested(host)
    check("nothing readable: a warning, no layer", messages[-1][0] == "warning" and set(QgsProject.instance().mapLayers()) == before,
          messages[-1])


def test_agent_objects(layer):
    """The objects for the agent: those of the dock read and summed up, SAM run from a guide layer as a tool."""
    from qgis.core import QgsFeature, QgsVectorLayer
    drawn = importlib.import_module(PACKAGE + ".adapters.public_api.drawn_objects")
    effects = importlib.import_module(PACKAGE + ".adapters.agent.turn_effects")
    coverage = importlib.import_module(PACKAGE + ".ui.controllers.coverage_mode_controller")
    kinds = importlib.import_module(PACKAGE + ".core.domain.layer_kind")
    project = QgsProject.instance()
    if project.mapLayer(layer.id()) is None:
        project.addMapLayer(layer)
    extent = layer.extent()
    x, y = extent.xMinimum(), extent.yMinimum()
    first = QgsGeometry.fromRect(QgsRectangle(x + 10, y + 10, x + 20, y + 30)).asWkt()
    second = QgsGeometry.fromRect(QgsRectangle(x + 50, y + 50, x + 54, y + 55)).asWkt()

    # The dock: the raster shown from its panel, the others from the state kept when they were left.
    host = types.SimpleNamespace(
        _panel_states={layer.id(): {"pipette_segments": ["stale"]}, "left": {"pipette_segments": [first]},
                       "nothing": {"pipette_segments": []}, "no state": None},
        _active_layer=layer, _raster_panel=types.SimpleNamespace(_segments=[first, second]),
        _kind=kinds.LayerKind.RASTER)
    panel = ready_panel(layer)
    panel.set_pick_target(panels.PICK_OBJECT)
    panel.add_segments([first, second])
    sam_state = dict(panel.state())
    host = types.SimpleNamespace(
        _panel_states={layer.id(): {"pipette_segments": ["stale"]}, "left": sam_state,
                       "colour": dict(sam_state, pipette_engine=panels.ENGINE_COLOR),
                       "pixels": dict(sam_state, pipette_target=panels.PICK_SIMILAR), "no state": None},
        _active_layer=layer, _raster_panel=panel, _kind=kinds.LayerKind.RASTER)
    found = coverage.CoverageModeController.drawn_objects(host)
    check("the dock tells the objects that select: the panel shown first, then the states kept with SAM",
          found == {layer.id(): [first, second], "left": [first, second]}, found)
    panel._engine_combo.setCurrentIndex(panel._engine_combo.findData(panels.ENGINE_COLOR))
    found = coverage.CoverageModeController.drawn_objects(host)
    check("with the colour engine the objects wait in the panel and are not offered",
          panel.object_engine() == panels.ENGINE_COLOR and layer.id() not in found, found)
    panel._engine_combo.setCurrentIndex(panel._engine_combo.findData(panels.ENGINE_SAM))
    host._active_layer = QgsRasterLayer(layer.source(), "another", "gdal")
    found = coverage.CoverageModeController.drawn_objects(host)
    check("a panel that shows another raster lends it nothing", host._active_layer.id() not in found, found)
    host._active_layer = layer
    rows = drawn.summarize_drawn({layer.id(): [first, second, "POLYGON(("], "left": [first]})
    check("map_context sums them up for each raster of the project",
          len(rows) == 1 and rows[0]["count"] == 2 and rows[0]["name"] == layer.name(), rows)
    if rows:
        box = QgsGeometry.fromWkt(rows[0]["extent_wkt"]).boundingBox()
        check("with their area on the ground and their extent",
              abs(rows[0]["area_m2"] - 220.0) < 3 and abs(box.width() - 44) < 1e-6 and abs(box.height() - 45) < 1e-6,
              (rows[0]["area_m2"], box.toString()))

    # segment_objects: filtermate:segment_from_features run on the main thread, its layer added to the project.
    model = BrightModel()
    install_model(model)
    ready = segmentation.model_state
    segmentation.model_state = lambda: segmentation.ModelState(True, True)
    truth = QgsGeometry.fromRect(QgsRectangle(extent.xMinimum() + SQUARE[2] * 0.5, extent.yMaximum() - SQUARE[1] * 0.5,
                                              extent.xMinimum() + SQUARE[3] * 0.5, extent.yMaximum() - SQUARE[0] * 0.5))
    guides = QgsVectorLayer("Polygon?crs=EPSG:2154&field=name:string", "footprints", "memory")
    features = []
    for name, geometry in (("roof", QgsGeometry.fromRect(truth.boundingBox().buffered(-3.0))),
                           ("away", QgsGeometry.fromRect(QgsRectangle(extent.xMaximum() + 50, extent.yMaximum() + 50,
                                                                      extent.xMaximum() + 60, extent.yMaximum() + 60)))):
        feature = QgsFeature(guides.fields())
        feature.setAttributes([name])
        feature.setGeometry(geometry)
        features.append(feature)
    guides.dataProvider().addFeatures(features)
    lines = QgsVectorLayer("LineString?crs=EPSG:2154", "roads", "memory")
    project.addMapLayers([guides, lines])
    added = []
    try:
        before = set(project.mapLayers())
        answer = drawn.segment_objects(layer.name(), "footprints", selected_only=True)
        added = [project.mapLayer(i) for i in set(project.mapLayers()) - before]
        check("no selection: every footprint is a guide, the one off the raster without object",
              answer["guide_features"] == 2 and answer["drawn"] == 1 and answer["without_object"] == 1
              and not answer["stopped_early"], answer)
        check("one layer added, named after the guide, in the CRS of the raster",
              len(added) == 1 and added[0].name() == "footprints (SAM)" and added[0].crs() == layer.crs()
              and answer["layer"]["layer_id"] == added[0].id(), [a.name() for a in added])
        if added:
            feature = next(added[0].getFeatures())
            check("the object on the bright square, with the attributes of its footprint",
                  feature["name"] == "roof" and segmentation.overlap(feature.geometry(), truth) > 0.97,
                  (feature["name"], round(segmentation.overlap(feature.geometry(), truth), 3)))
            check("outlined, the raster stays visible", added[0].renderer().symbol().color().alpha() == 0)
        check("the score and the overlap summed up", answer.get("sam_score", {}).get("median") == 0.9
              and 0.8 < answer.get("sam_iou", {}).get("median", 0) < 1.0 and answer["sam_iou"]["below_half"] == 0,
              (answer.get("sam_score"), answer.get("sam_iou")))
        guides.selectByIds([next(f.id() for f in guides.getFeatures() if f["name"] == "roof")])
        answer = drawn.segment_objects(layer.id(), guides.id(), name="toits")
        added += [project.mapLayer(answer["layer"]["layer_id"])]
        check("the selection only, by layer ids, under the name asked",
              answer["guide_features"] == 1 and answer["drawn"] == 1 and answer["layer"]["name"] == "toits", answer)

        def refused(fragment, *args, **kwargs):
            try:
                drawn.segment_objects(*args, **kwargs)
            except ValueError as exc:
                return fragment in str(exc), str(exc)
            return False, "not refused"

        guides.removeSelection()

        # The time allowed: the run stops between two windows, and a run that drew them all is not "stopped".
        class SlowModel(BrightModel):
            def __init__(self, delay, fail=""):
                super().__init__()
                self.delay, self.fail, self.running = delay, fail, []

            def embed(self, rgb):
                self.running.append(list(operations._RUNNING))
                time.sleep(self.delay)
                if self.fail:
                    raise RuntimeError(self.fail)
                return super().embed(rgb)

        operations = importlib.import_module(PACKAGE + ".adapters.public_api.operations")
        large = QgsFeature(guides.fields())
        large.setAttributes(["field"])
        large.setGeometry(QgsGeometry.fromRect(QgsRectangle(x + 20, y + 20, x + 380, y + 380)))  # a window of its own
        guides.dataProvider().addFeatures([large])
        guides.selectByIds([f.id() for f in guides.getFeatures() if f["name"] in ("roof", "field")])
        slow = SlowModel(0.6)
        install_model(slow)
        budget = drawn.BUDGET_SECONDS
        drawn.BUDGET_SECONDS = 0.3
        try:
            answer = drawn.segment_objects(layer.name(), "footprints")
            added += [project.mapLayer(answer["layer"]["layer_id"])]
            check("past the time allowed the run stops between two windows, and says so",
                  slow.embedded == 1 and answer["drawn"] == 1 and answer["stopped_early"] and answer["guide_features"] == 2,
                  (slow.embedded, answer))
            check("other operations are refused while it runs, not after",
                  slow.running == [["segment_objects"]] and operations._RUNNING == [], (slow.running, operations._RUNNING))
            guides.selectByIds([next(f.id() for f in guides.getFeatures() if f["name"] == "roof")])
            answer = drawn.segment_objects(layer.name(), "footprints")
            added += [project.mapLayer(answer["layer"]["layer_id"])]
            check("a run that drew every window past the time allowed was not stopped",
                  answer["drawn"] == 1 and not answer["stopped_early"], answer)
            install_model(SlowModel(0.0, fail="/home/user/QGIS/profiles/default/filtermate/models/encoder.onnx: bad file"))
            ok, message = refused("no window of the raster could be drawn", layer.name(), "footprints")
            check("an error is told in general words, its path stays in the log", ok and "/home" not in message, message)
        finally:
            drawn.BUDGET_SECONDS = budget
            install_model(model)
            guides.removeSelection()
            guides.dataProvider().deleteFeatures([f.id() for f in guides.getFeatures() if f["name"] == "field"])

        check("more guide features than the limit: refused, select fewer",
              *refused("at most 1 are taken", layer.name(), "footprints", limit=1))
        check("a line frames no object", *refused("neither points nor polygons", layer.name(), "roads"))
        check("the guide as raster: refused", *refused("is not a raster layer", "footprints", "footprints"))
        check("an unknown raster: refused", *refused("not found", "ghost", "footprints"))
        budget = drawn.BUDGET_SECONDS
        drawn.BUDGET_SECONDS = 0.0
        try:
            check("the time allowed spent before any window: nothing drawn, and said so",
                  *refused("ran out before an object was drawn", layer.name(), "footprints"))
        finally:
            drawn.BUDGET_SECONDS = budget
        segmentation.model_state = lambda: segmentation.ModelState(True, False)
        check("without SAM: what to tell the user", *refused("installs it from the FilterMate dock", layer.name(), "footprints"))
        segmentation.model_state = lambda: segmentation.ModelState(True, True)

        # Undo of a turn: the layer, a file, is taken away and Redo opens it again with its objects.
        recorder = effects.EffectsRecorder()
        recorder.before_call(types.SimpleNamespace(name="segment_objects", arguments={}))
        answer = drawn.segment_objects(layer.name(), "footprints")
        made = answer["layer"]["layer_id"]
        check("the objects are a file, not a memory layer", project.mapLayer(made).providerType() == "ogr"
              and project.mapLayer(made).source().lower().split("|")[0].endswith(".gpkg"), project.mapLayer(made).source())
        recorded = recorder.finish()
        check("the turn records the layer added, with its definition",
              [(e[0], e[1]) for e in recorded] == [("added", made)] and recorded[0][2], [e[:2] for e in recorded])
        done, left = effects.apply_effects(recorded, undo=True)
        check("undo removes it", project.mapLayer(made) is None and done == ["footprints (SAM)"], (done, left))
        done, left = effects.apply_effects(recorded, undo=False)
        back = project.mapLayer(made)
        check("redo opens it again, objects and style", back is not None and back.featureCount() == 1 and not left
              and back.renderer().symbol().color().alpha() == 0, (done, left))
        # A layer held in memory would come back empty: the turn says it cannot.
        memory = QgsVectorLayer("Polygon?crs=EPSG:2154", "scratch", "memory")
        memory_id = memory.id()  # the layer object is deleted by the undo below
        recorder.before_call(types.SimpleNamespace(name="segment_objects", arguments={}))
        project.addMapLayer(memory)
        recorded = recorder.finish()
        check("a memory layer is recorded without a definition",
              [(e[0], e[1], e[2]) for e in recorded] == [("added", memory_id, "")], [e[:3] for e in recorded])
        effects.apply_effects(recorded, undo=True)
        done, left = effects.apply_effects(recorded, undo=False)
        check("and redo says it cannot come back", left == ["scratch"] and project.mapLayer(memory_id) is None, (done, left))
    finally:
        segmentation.model_state = ready
        for item in added:
            if item is not None and project.mapLayer(item.id()) is not None:
                project.removeMapLayer(item.id())
        project.removeMapLayers([guides.id(), lines.id()])


def test_similar_flow(folder):
    """Similar objects with SAM: the colour proposes, the model redraws, the area and the shape judge."""
    layer = make_shapes(folder)
    QgsProject.instance().addMapLayer(layer)
    canvas = QgsMapCanvas()
    canvas.resize(QSize(600, 600))
    canvas.setDestinationCrs(layer.crs())
    canvas.setLayers([layer])
    canvas.setExtent(layer.extent())
    panel = ready_panel(layer)
    panel.set_pick_target(panels.PICK_SIMILAR_OBJECTS)
    model = BrightModel()
    install_model(model)
    host = Host(layer, panel, canvas)
    reference = shape_geometry(layer, "clicked")
    criterion = panel.criterion_at({1: 230.0, 2: 230.0, 3: 230.0})
    check("the panel reads a criterion without touching its picks", criterion is not None and panel._picks == [])
    points = segmentation.similar_candidate_points(layer, criterion, reference, layer.extent())
    check("the colour proposes the other patches", len(points) >= 2, points)
    host._similar_candidates = lambda lay, ref, visible: segmentation.similar_candidate_points(lay, criterion, ref, visible)
    controller = controllers.SegmentationController(host)
    controller.activate()

    def names():
        return sorted(max(SHAPES, key=lambda name: segmentation.overlap(QgsGeometry.fromWkt(wkt), shape_geometry(layer, name)))
                      for wkt in panel._segments)

    # Clicks while the area is being prepared: each is an object of its own.
    panel.set_pick_target(panels.PICK_OBJECT)
    controller._on_point(reference.centroid().asPoint(), True)
    controller._on_point(shape_geometry(layer, "alike").centroid().asPoint(), True)
    check("two clicks during the preparation give two objects",
          spin(lambda: controller._task is None and len(panel._segments) >= 2, 30000) and names() == ["alike", "clicked"], names())
    controller._session = None  # the next click prepares an area again
    controller._on_point(shape_geometry(layer, "large").centroid().asPoint(), True)
    controller.clear()
    check("Escape during the preparation only cancels that click", controller._task is None and names() == ["alike", "clicked"],
          (names(), panel._segment_status.text()))
    controller.clear()
    check("then Escape removes the last object", names() == ["clicked"], names())
    panel.clear_segments()
    controller.clear()
    check("Clear then Escape removes nothing more", panel._segments == [])
    controller._on_point(reference.centroid().asPoint(), True)
    spin(lambda: controller._task is None and len(panel._segments) == 1, 30000)
    controller._on_point(reference.centroid().asPoint(), True, True)
    check("Shift+click after Clear redraws the new object", names() == ["clicked"], names())
    panel.clear_segments()

    # G: the next of the three masks SAM proposes (a stub: a quarter, the object, the whole window).
    class ThreeMasks(BrightModel):
        def predict_masks(self, embedding, points, labels, box):
            bright = embedding[:, :, 0] > 128
            column, row = (int(value) for value in points[0])
            part = np.zeros_like(bright)
            part[row - 10:row + 10, column - 10:column + 10] = True  # a part of the clicked object, around the click
            return [part & bright, bright, np.ones_like(bright)], [0.5, 0.9, 0.4]

    three = ThreeMasks()
    install_model(three)
    controller._session = None
    panel.set_pick_target(panels.PICK_OBJECT)
    controller._on_point(reference.centroid().asPoint(), True)
    spin(lambda: controller._task is None and len(panel._segments) == 1, 30000)
    first = QgsGeometry.fromWkt(panel._segments[0]).area()
    controller.cycle()
    second = QgsGeometry.fromWkt(panel._segments[0]).area() if panel._segments else 0
    controller.cycle()
    third = QgsGeometry.fromWkt(panel._segments[0]).area() if panel._segments else 0
    check("G redraws the last object at the next granularity, then wraps to the smallest",
          len(panel._segments) == 1 and second > first and 0 < third < first, (first, second, third))
    check("and says which one", "1" in panel._segment_status.text() and "3" in panel._segment_status.text(), panel._segment_status.text())
    panel.clear_segments()
    install_model(model)
    controller._session = None

    def names_of(wkts):
        return sorted(max(SHAPES, key=lambda name: segmentation.overlap(QgsGeometry.fromWkt(wkt), shape_geometry(layer, name)))
                      for wkt in wkts)

    def search():
        controller._on_point(reference.centroid().asPoint(), True)
        return spin(lambda: controller._task is None and controller._search is None and len(panel._segments) >= 1, 60000)

    alike = shape_geometry(layer, "alike").centroid().asPoint()
    panel.set_pick_target(panels.PICK_SIMILAR_OBJECTS)
    check("the clicked object is drawn and the search runs", search(), panel._segment_status.text())
    proposed = names_of([wkt for wkt, _reference in controller._proposals])
    check("the alike square is proposed", "alike" in proposed, proposed)
    check("the large square and the strip are not", "large" not in proposed and "strip" not in proposed, proposed)
    check("proposals stay out of the selection until kept", names() == ["clicked"] and not panel._proposal_widget.isHidden())
    check("the status counts them", "1 " in panel._segment_status.text(), panel._segment_status.text())
    controller._on_point(alike, False)
    check("a right click on a proposal rejects it", controller.proposal_count() == 0 and names() == ["clicked"]
          and panel._proposal_widget.isHidden())
    controller.clear()
    check("Escape removes the clicked object", panel._segments == [])
    search()
    controller._on_point(alike, True)
    check("a click on a proposal keeps it", names() == ["alike", "clicked"] and controller.proposal_count() == 0, names())
    controller.clear()
    check("Escape removes the clicked object with the objects kept from its search", panel._segments == [], names())
    panel._similar_shape_check.setChecked(False)
    search()
    controller.validate()
    check("Enter keeps every proposal; without the shape the strip joins", "strip" in names() and "large" not in names(), names())
    controller.clear()
    search()
    controller.clear()
    check("Escape rejects every proposal", controller.proposal_count() == 0 and names() == ["clicked"], names())
    panel.clear_segments()
    controller.drop()
    QgsProject.instance().removeMapLayer(layer.id())


class FeatureModel(BrightModel):
    """Bright pixels as objects, and encoder features that say how bright each 16 x 16 cell is."""

    def embed(self, rgb):
        super().embed(rgb)
        share = (rgb[:, :, 0] > 128).astype(np.float32).reshape(64, 16, 64, 16).mean(axis=(1, 3))
        return {'image': rgb, 'image_embed': np.stack([share, 1.0 - share])[None]}

    def predict(self, embedding, points, labels, box):
        return super().predict(embedding['image'], points, labels, box)


def test_feature_candidates_and_sorting(folder):
    """2026-11-11: candidates where the features look like the clicked object's, and proposals sorted by keep / reject."""
    layer = make_shapes(folder)
    QgsProject.instance().addMapLayer(layer)
    canvas = QgsMapCanvas()
    canvas.resize(QSize(600, 600))
    canvas.setDestinationCrs(layer.crs())
    canvas.setLayers([layer])
    canvas.setExtent(layer.extent())
    panel = ready_panel(layer)
    model = FeatureModel()
    install_model(model)
    reference = shape_geometry(layer, "clicked")
    extent = layer.extent()
    window = segmentation.plan_window(reference.centroid().asPoint().x(), reference.centroid().asPoint().y(),
                                      (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                                      0.5, extent.width(), 1024)
    from qgis.core import QgsMapSettings
    settings = QgsMapSettings()
    settings.setDestinationCrs(layer.crs())
    embedding = model.embed(segmentation.image_to_rgb(segmentation.render_window(settings, layer, window, lambda: False)))
    centre = reference.centroid().asPoint()
    mask = model.predict(embedding, [window.to_pixel(centre.x(), centre.y())], [1], None)[0]
    clicked_features = segmentation.pooled_features(embedding, mask)
    points = segmentation.feature_candidate_points(embedding, window, clicked_features, extent, reference)

    def shape_of(x, y):
        where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
        return next((name for name in SHAPES
                     if QgsGeometry.fromRect(shape_geometry(layer, name).boundingBox().buffered(1.0)).contains(where)), None)
    found = [shape_of(px, py) for px, py in points]
    check("the features point at the other bright shapes, the clicked one left out",
          "alike" in found and "clicked" not in found and len(points) <= segmentation.SIMILAR_FEATURE_CANDIDATES, found)
    check("outside the visible map, none",
          segmentation.feature_candidate_points(embedding, window, clicked_features, shape_geometry(layer, "clicked").boundingBox(),
                                                reference) == [])
    check("a stub encoder has no features to read", segmentation.feature_candidate_points(
        np.zeros((1024, 1024, 3), dtype=np.uint8), window, clicked_features, extent, reference) == [])

    # The controller proposes them even when no colour patch does.
    host = Host(layer, panel, canvas)
    host._similar_candidates = lambda lay, ref, visible: []
    controller = controllers.SegmentationController(host)
    controller.activate()
    panel.set_pick_target(panels.PICK_SIMILAR_OBJECTS)
    controller._on_point(reference.centroid().asPoint(), True)
    spin(lambda: controller._task is None and controller._search is None and len(panel._segments) >= 1, 60000)
    inside = [QgsGeometry.fromWkt(wkt).pointOnSurface().asPoint() for wkt, _reference in controller._proposals]
    proposed = [shape_of(point.x(), point.y()) for point in inside]
    check("without colour candidates, the features still find the alike square", "alike" in proposed, proposed)
    check("each proposal keeps its features for the sorting",
          controller._sorting is not None and all(controller._sorting['features'].get(wkt) is not None
                                                  for wkt, _reference in controller._proposals), controller._sorting)
    controller.reject_proposals()

    # Keep / reject: from the third decision, the proposals like the rejected ones go.
    x, y = extent.xMinimum(), extent.yMinimum()
    squares = [QgsGeometry.fromRect(QgsRectangle(x + 20 * i, y + 5, x + 20 * i + 10, y + 15)).asWkt() for i in range(6)]
    vectors = [[0.0, 1.0], [1.0, 0.0], [0.1, 1.0], [0.0, 1.0], [1.0, 0.1], [0.05, 1.0]]
    reference_wkt = reference.asWkt()
    controller._set_proposals([(wkt, reference_wkt) for wkt in squares])
    controller._sorting = {'features': dict(zip(squares, vectors)), 'decisions': 0, 'kept': [[1.0, 0.0]], 'rejected': []}

    def decide(index, keep):
        centre = QgsGeometry.fromWkt(squares[index]).centroid().asPoint()
        return controller._decide_proposal(centre, keep)
    decide(0, False)
    decide(1, True)
    check("before the third decision nothing else goes", controller.proposal_count() == 4)
    decide(2, False)
    left = [squares.index(wkt) for wkt, _reference in controller._proposals]
    check("after it, the proposals closer to the rejected ones go, the others stay", left == [4], left)
    check("and the status says why", "taken away" in panel._segment_status.text(), panel._segment_status.text())
    decide(4, True)
    check("the last one kept, the sorting is forgotten", controller.proposal_count() == 0 and controller._sorting is None)
    panel.clear_segments()
    controller.drop()
    QgsProject.instance().removeMapLayer(layer.id())


def test_agent_similar_objects(folder):
    """2026-11-11: the agent finds the objects like an example, by the features alone, as a layer."""
    from qgis.core import QgsFeature, QgsVectorLayer
    drawn = importlib.import_module(PACKAGE + ".adapters.public_api.drawn_objects")
    layer = make_shapes(folder)
    project = QgsProject.instance()
    project.addMapLayer(layer)
    install_model(FeatureModel())
    ready = segmentation.model_state
    segmentation.model_state = lambda: segmentation.ModelState(True, True)
    clicked = shape_geometry(layer, "clicked")
    everywhere = layer.extent().asWktPolygon()
    points = QgsVectorLayer("Point?crs=EPSG:2154", "examples", "memory")
    features = []
    for name in ("clicked", "alike"):
        feature = QgsFeature(points.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(shape_geometry(layer, name).centroid().asPoint()))
        features.append(feature)
    points.dataProvider().addFeatures(features)
    project.addMapLayer(points)
    added = []

    def names_of(answer):
        found = project.mapLayer(answer["layer"]["layer_id"]) if answer.get("layer") else None
        if found is None:
            return []
        added.append(found)
        return sorted(max(SHAPES, key=lambda name: segmentation.overlap(f.geometry(), shape_geometry(layer, name)))
                      for f in found.getFeatures())

    def refused(fragment, **kwargs):
        try:
            drawn.similar_objects(layer.id(), **kwargs)
        except ValueError as exc:
            return fragment in str(exc), str(exc)
        return False, "not refused"
    try:
        answer = drawn.similar_objects(layer.id(), use_dock_object=True, dock_objects={layer.id(): [clicked.asWkt()]},
                                       extent_wkt=everywhere)
        found = names_of(answer)
        check("like the object drawn in the dock: the alike square, not the large one nor the strip",
              found == ["alike"] and answer["objects"] == 1 and answer["windows"] == 1 and not answer["stopped_early"],
              (found, answer))
        written = project.mapLayer(answer["layer"]["layer_id"]) if answer.get("layer") else None
        row = next(written.getFeatures()) if written is not None else None
        check("a file with the appearance and the area of each object",
              written is not None and written.providerType() == "ogr" and row["appearance"] >= drawn.SIMILAR_APPEARANCE_MIN
              and 800 < row["area_m2"] < 1000 and written.crs() == layer.crs(),
              (written and written.source(), row and row.attributes()))
        check("and the example as SAM drew it", answer["example"]["sam_score"] == 0.9 and 800 < answer["example"]["area_m2"] < 1000,
              answer["example"])
        points.selectByIds([next(f.id() for f in points.getFeatures())])
        # The east half: the alike square and the strip, not the large square, whose uniform cells would fill the
        # 40 candidates of the window first (the best 40 peaks of the features, as measured).
        extent = layer.extent()
        east = QgsRectangle(extent.xMinimum() + 200, extent.yMinimum(), extent.xMaximum(), extent.yMaximum()).asWktPolygon()
        answer = drawn.similar_objects(layer.name(), example_layer="examples", extent_wkt=east, same_shape=False)
        found = names_of(answer)
        check("a selected point as example; without the shape the strip of the same area joins",
              found == ["alike", "strip"], found)
        found = names_of(drawn.similar_objects(layer.name(), example_layer="examples", extent_wkt=east))
        check("with the shape it does not", found == ["alike"], found)
        check("outside the extent given, nothing (and no layer)", drawn.similar_objects(
            layer.id(), example_layer="examples", extent_wkt=clicked.boundingBox().asWktPolygon())["layer"] is None)
        check("no example: refused", *refused("give an example"))
        points.selectAll()
        check("two features selected: refused", *refused("select exactly the one example", example_layer="examples"))
        check("nothing drawn in the dock: refused", *refused("no object is drawn", use_dock_object=True, dock_objects={}))
        check("an example and the dock: refused",
              *refused("not both", example_layer="examples", use_dock_object=True, dock_objects={}))
        limit = drawn.MAX_SEARCH_WINDOWS
        drawn.MAX_SEARCH_WINDOWS = 0
        try:
            check("an area of more windows than allowed: refused",
                  *refused("give a smaller extent", use_dock_object=True, dock_objects={layer.id(): [clicked.asWkt()]},
                           extent_wkt=everywhere))
        finally:
            drawn.MAX_SEARCH_WINDOWS = limit
        segmentation.model_state = lambda: segmentation.ModelState(True, False)
        check("without SAM: what to tell the user",
              *refused("installs it from the FilterMate dock", use_dock_object=True, dock_objects={layer.id(): [clicked.asWkt()]}))
    finally:
        segmentation.model_state = ready
        for item in added:
            if project.mapLayer(item.id()) is not None:
                project.removeMapLayer(item.id())
        project.removeMapLayers([points.id(), layer.id()])

    # The windows over a large area: the example's first, then nearest first, overlapping, none twice.
    first = segmentation.SegmentationWindow(0.0, 1024.0, 1.0, 1024)
    windows = drawn.search_windows(first, QgsRectangle(0, 0, 3000, 2000), (0.0, 0.0, 3000.0, 2000.0), 1.0, 1024)
    keys = [(w.x_min, w.y_max) for w in windows]
    check("search windows: the example's first, each once, the area covered",
          keys[0] == (0.0, 1024.0) and len(keys) == len(set(keys))
          and max(w.x_min + w.side for w in windows) >= 3000 and min(w.y_max - w.side for w in windows) <= 0, keys)


def test_map_images(folder):
    """2026-11-11: the images of the MCP server of the plugin, the map and the contact sheets of objects."""
    import base64
    from qgis.core import QgsFeature, QgsVectorLayer
    images = importlib.import_module(PACKAGE + ".adapters.public_api.map_images")
    executor = importlib.import_module(PACKAGE + ".core.agent.tool_executor")
    layer = make_shapes(folder)
    project = QgsProject.instance()
    project.addMapLayer(layer)

    def polygons(name, shapes):
        made = QgsVectorLayer("Polygon?crs=EPSG:2154&field=name:string", name, "memory")
        features = []
        for shape in shapes:
            feature = QgsFeature(made.fields())
            feature.setAttributes([shape])
            feature.setGeometry(shape_geometry(layer, shape))
            features.append(feature)
        made.dataProvider().addFeatures(features)
        project.addMapLayer(made)
        return made
    objects, examples = polygons("found", ["alike", "large", "strip"]), polygons("example", ["clicked", "alike"])

    def decoded(data):
        image = QImage()
        image.loadFromData(base64.b64decode(data), "JPEG")
        return image
    try:
        examples.selectByIds([next(f.id() for f in examples.getFeatures() if f["name"] == "clicked")])
        data, info = images.contact_sheet(layer.id(), objects.name(), example_layer=examples.id(), tile=120)
        sheet = decoded(data)
        check("a contact sheet: tile E then one tile per object, numbered with its feature id",
              (sheet.width(), sheet.height()) == (480, 120) and [t["tile"] for t in info["tiles"]] == [1, 2, 3]
              and info["example_fid"] is not None and len({t["fid"] for t in info["tiles"]}) == 3, (sheet.size(), info))
        centre = QColor(sheet.pixel(120 + 60, 60))  # tile 1: the alike square, in the middle of its tile
        check("each object in the middle of its tile", centre.red() > 180 and centre.green() > 180, centre.name())
        red = sum(1 for x in range(0, 480, 2) for y in range(0, 120, 2)
                  if QColor(sheet.pixel(x, y)).red() > 180 and QColor(sheet.pixel(x, y)).green() < 90)
        check("outlined in red", red > 20, red)
        examples.removeSelection()
        try:
            images.contact_sheet(layer.id(), objects.name(), example_layer=examples.id())
            refused = False
        except ValueError as exc:
            refused = "select the one example" in str(exc)
        check("an example layer without its one selection: refused", refused)
        objects.selectByIds([next(f.id() for f in objects.getFeatures() if f["name"] == "strip")])
        data, info = images.contact_sheet(layer.name(), objects.id())
        check("the selected objects only, no example tile",
              decoded(data).width() == 160 and len(info["tiles"]) == 1 and info["example_fid"] is None, info)
        data, info = images.map_image(layer.extent().asWktPolygon(), "EPSG:2154", 400)
        drawn = decoded(data)
        check("an image of the map without a map window: the layers checked, the extent given",
              (drawn.width(), drawn.height()) == (400, 400) and info["crs"] == "EPSG:2154", (drawn.size(), info))
        handlers = images.handlers()
        answer = handlers["contact_sheet"]({"raster": layer.id(), "layer": objects.id()})
        check("the handler answers the image beside the JSON",
              isinstance(answer, executor.WithImages) and answer.images[0][0] == "image/jpeg", type(answer).__name__)
        try:
            handlers["contact_sheet"]({"raster": "ghost", "layer": objects.id()})
            told = False
        except executor.ToolFailure as exc:
            told = "not found" in str(exc)
        check("a refusal is told to the client", told)
    finally:
        project.removeMapLayers([objects.id(), examples.id(), layer.id()])


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
    test_objects_layer(raster)
    test_features_algorithm(raster)
    test_agent_objects(raster)
    test_similar_flow(folder)
    test_feature_candidates_and_sorting(folder)
    test_agent_similar_objects(folder)
    test_map_images(folder)
    test_web_service()
    test_real_model()
    QgsProject.instance().removeAllMapLayers()

print(f"{len(failures)} failure(s)", flush=True)
app.exitQgis()
os._exit(1 if failures else 0)
