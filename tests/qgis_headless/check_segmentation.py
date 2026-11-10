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
for part in ("", "core", "core.domain", "core.ports", "adapters", "adapters.qgis", "adapters.qgis.coverage_layers",
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
    test_similar_flow(folder)
    test_web_service()
    test_real_model()
    QgsProject.instance().removeAllMapLayers()

print(f"{len(failures)} failure(s)", flush=True)
app.exitQgis()
os._exit(1 if failures else 0)
