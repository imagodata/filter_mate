"""Real QGIS raster interactions and numeric expressions, using local synthetic data.

Run with QT_QPA_PLATFORM=offscreen and QGIS Python bindings. Set
FILTERMATE_TEST_OUTPUT to export a screenshot of the real raster panel.
"""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import traceback
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from osgeo import gdal, osr
from qgis.core import Qgis, QgsApplication, QgsPointXY, QgsRasterLayer
from qgis.PyQt.QtCore import QEvent, QEventLoop, QTimer, QTranslator, QT_VERSION_STR

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "fm_raster_interactions"
for part in ("", "core", "core.domain", "adapters", "adapters.qgis", "adapters.qgis.coverage_layers",
             "ui", "ui.controllers", "ui.widgets", "ui.widgets.coverage_panels"):
    module = types.ModuleType(PACKAGE + ("." + part if part else ""))
    module.__path__ = [str(ROOT / part.replace(".", "/"))]
    sys.modules[module.__name__] = module

app = QgsApplication([], False)
app.initQgis()
print(f"QGIS {Qgis.QGIS_VERSION}, Qt {QT_VERSION_STR}", flush=True)
translation = os.environ.get("FILTERMATE_TEST_TRANSLATION")
if translation:
    translator = QTranslator()
    assert translator.load(translation), "French translation could not be loaded"
    app.installTranslator(translator)
adapter = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.raster_adapter")
ui = importlib.import_module(PACKAGE + ".ui.widgets.coverage_panels.raster_exploring_panel")


def make_layer(folder):
    path = str(Path(folder) / "spectral.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 32, 24, 4, gdal.GDT_Float32)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(3857)
    ds.SetProjection(crs.ExportToWkt())
    ds.SetGeoTransform((0, 1, 0, 24, 0, -1))
    red = np.tile(np.arange(1, 33, dtype="float32"), (24, 1))
    arrays = [red.copy(), red + 10, red + 20, 34 - red]
    arrays[0][0, 0] = arrays[3][0, 1] = -9999
    for number, array in enumerate(arrays, 1):
        band = ds.GetRasterBand(number)
        band.SetNoDataValue(-9999)
        band.WriteArray(array)
        band.SetColorInterpretation(gdal.GCI_Undefined)
    ds = None
    layer = QgsRasterLayer(path, "Spectral image", "gdal")
    assert layer.isValid()
    return layer


def panel_for(layer):
    panel = ui.RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(layer))
    if layer.bandCount() >= 4:
        panel._roles = ui.roles_from_layout("rgbn", [1, 2, 3, 4])
    panel.set_band_spans({1: 31, 2: 31, 3: 31, 4: 31})

    def histogram(_band=None):
        band = panel.current_band()
        expression = panel.current_quantity_expression()
        derivative = panel.current_derivative()
        if expression:
            result = adapter.expression_histogram(layer, expression)
        elif derivative.is_terrain:
            result = adapter.derivative_histogram(layer, band, derivative)
        else:
            result = adapter.band_histogram(layer, band)
        panel.set_histogram(band, *result, derivative, expression=expression)

    panel.bandChanged.connect(histogram)
    histogram()
    return panel


def check_numeric_quantity(layer):
    expression = ui.spectral_quantity("ndvi_vegetation", "rgbn", "Spectral_image")
    counts, low, high = adapter.expression_histogram(layer, expression)
    assert sum(counts) == 32 * 24 - 2
    assert low < 0 < high
    assert adapter.expression_value_at(layer, expression, QgsPointXY(16.5, 22.5)) == 0
    assert adapter.expression_value_at(layer, expression, QgsPointXY(0.5, 23.5)) is None
    panel = panel_for(layer)
    panel._use_quantity(expression)
    panel._min_spin.setValue(0.25)
    panel._max_spin.setValue(0.75)
    assert panel.histogram_range() == (0.25, 0.75)
    assert panel._expression_edit.toPlainText() == panel.selection().expression
    assert panel._histogram.range() == (0.25, 0.75)
    saved = panel.state()
    restored = panel_for(layer)
    restored.restore_state(saved)
    restored.set_histogram(1, counts, low, high, expression=expression)
    assert restored.histogram_range() == (0.25, 0.75)
    assert (restored._min_spin.value(), restored._max_spin.value()) == (0.25, 0.75)
    panel._use_quantiles(0.25, 0.75)
    selected_low, selected_high = panel.histogram_range()
    assert low < selected_low < selected_high < high
    assert panel._expression_edit.toPlainText() == panel.selection().expression
    output = os.environ.get("FILTERMATE_TEST_OUTPUT")
    if output:
        panel.resize(560, 850)
        panel.show()
        app.processEvents()
        assert panel.grab().save(str(Path(output) / "raster-derived-value.png"))
    restored.deleteLater()
    panel.deleteLater()


def check_expression_histogram(layer):
    panel = panel_for(layer)
    panel._activate_mode(ui.RasterSelectionMode.EXPRESSION, emit=False)
    expression = '"Spectral_image@2" / 100'
    panel._expression_edit.setPlainText(expression)
    counts, low, high = adapter.expression_histogram(layer, expression)
    panel.set_histogram(1, counts, low, high, expression=expression)
    panel._expression_histogram.set_range(0.2, 0.3)
    panel._on_expression_histogram_changed(0.2, 0.3)
    assert panel.current_quantity_expression() == expression
    assert panel.histogram_range() == (0.2, 0.3)
    assert panel._expression_edit.toPlainText() == panel.selection().expression
    panel.deleteLater()


def check_disjoint_picks(layer):
    panel = panel_for(layer)
    panel._pipette_bands = [2]
    panel._tolerance_spin.setValue(0)
    panel.set_color_sample({1: 1, 2: 15})
    panel.set_color_sample({1: 2, 2: 35}, extend=True)
    selection = panel.selection()
    assert selection.band == 2
    assert selection.mode is ui.RasterSelectionMode.EXPRESSION, "separate picks must keep separate value intervals"
    mask = adapter.expression_array(layer, selection.expression)
    assert np.count_nonzero(mask) == 48, "intermediate values must stay unselected"
    panel.deleteLater()


def check_rendered_after_quantity(layer):
    panel = panel_for(layer)
    panel._use_quantity('"Spectral_image@2" / 100')
    panel.set_rendered_only(True)
    assert not panel._custom_quantity, "rendered colour picking must leave the numeric custom quantity"
    panel.set_color_sample({1: 10, 2: 20, 3: 30})
    assert panel.selection() is not None
    panel.deleteLater()


def check_reset(layer):
    panel = panel_for(layer)
    panel._similar_low_spin.setValue(0.25)
    panel._similar_high_spin.setValue(3)
    panel._similar_shape_check.setChecked(False)
    panel.reset()
    assert panel.similar_ratio() == ui.DEFAULT_SIMILAR_RATIO
    assert panel.similar_shape()
    panel.deleteLater()


def check_threshold_outside_sample(layer):
    panel = panel_for(layer)
    panel._use_quantity('"Spectral_image@2" / 100')
    panel._on_preset_chosen((0.8, None))
    assert panel.histogram_range() == (0.8, None)
    assert panel._min_spin.value() == 0.8, "displayed threshold must match the effective selection outside the sample range"
    panel.deleteLater()


def check_pending_formula_edit(layer):
    panel = panel_for(layer)
    panel._use_quantity('"Spectral_image@2" / 100')
    panel._quantity_edit.setPlainText('"Spectral_image@2" / 200')
    assert panel._quantity_debounce.isActive()
    panel._use_spectral_quantity("ndvi_vegetation")
    assert not panel._quantity_debounce.isActive()
    loop = QEventLoop()
    QTimer.singleShot(350, loop.quit)
    loop.exec()
    assert panel.histogram_range() == (0.3, None), "a delayed edit must not erase a subsequently chosen preset"
    panel.deleteLater()


def check_quantity_switch(layer):
    panel = panel_for(layer)
    panel.set_color_sample({1: 10, 2: 20, 3: 30, 4: 40})
    assert panel.selection() is not None
    index = panel._derivative_combo.findData(ui.RasterDerivative.SLOPE_DEGREES.value)
    panel._derivative_combo.setCurrentIndex(index)
    assert panel._picks == [] and panel.selection() is None
    panel.deleteLater()


def check_object_modes(folder):
    path = str(Path(folder) / "objects.tif")
    scene = np.zeros((60, 80), dtype="uint8")
    scene[4:12, 4:12] = scene[4:12, 22:30] = 10  # two small pools
    scene[20:32, 4:16] = 10  # a large pool, outside the pool reference's area ratios
    scene[20:32, 25:37] = scene[38:50, 25:37] = 20  # two large roofs
    scene[4:12, 12:20] = 20  # a small roof touching the first pool: still a separate object
    ds = gdal.GetDriverByName("GTiff").Create(path, 80, 60, 1, gdal.GDT_Byte)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(3857)
    ds.SetProjection(crs.ExportToWkt())
    ds.SetGeoTransform((0, 1, 0, 60, 0, -1))
    ds.GetRasterBand(1).WriteArray(scene)
    ds = None
    layer = QgsRasterLayer(path, "Objects", "gdal")
    assert layer.isValid()
    panel = panel_for(layer)
    panel._tolerance_spin.setValue(0)
    panel._set_pick_target(ui.PICK_SIMILAR_OBJECTS)
    panel._similar_low_spin.setValue(0.9)
    panel._similar_high_spin.setValue(1.1)
    panel.set_color_sample({1: 10}, point=(8.5, 51.5))
    panel.set_color_sample({1: 20}, extend=True, point=(30.5, 33.5))
    result = adapter.layer_object_geometry(layer, panel.selection())
    assert result.objects == 4, f"expected two small pools and two large roofs, got {result.objects}"
    assert result.kept_pixels == 400 and result.geometry.area() == 400
    assert not result.geometry.contains(QgsPointXY(8.5, 34.5)), "a large pool must not inherit a roof's area reference"
    assert not result.geometry.contains(QgsPointXY(16.5, 51.5)), "an adjacent small roof must not inherit the pool's area reference"
    panel._set_pick_target(ui.PICK_OBJECT)
    panel._apply_picks()
    clicked = adapter.layer_object_geometry(layer, panel.selection())
    assert clicked.objects == 2 and clicked.geometry.area() == 208
    output = os.environ.get("FILTERMATE_TEST_OUTPUT")
    if output:
        panel._set_pick_target(ui.PICK_SIMILAR_OBJECTS)
        panel.show_detected_objects(result.objects, result.geometry.area())
        panel.resize(560, 850)
        panel.show()
        app.processEvents()
        assert panel.grab().save(str(Path(output) / "raster-similar-objects.png"))
    panel.deleteLater()


def check_constant_band(folder):
    path = str(Path(folder) / "constant.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 8, 8, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((0, 1, 0, 8, 0, -1))
    ds.GetRasterBand(1).WriteArray(np.full((8, 8), 7, dtype="uint8"))
    ds = None
    layer = QgsRasterLayer(path, "Constant", "gdal")
    counts, low, high = adapter.band_histogram(layer, 1)
    assert sum(counts) == 64 and low == high == 7


def check_async_controller(layer):
    controllers = importlib.import_module(PACKAGE + ".ui.controllers.coverage_mode_controller")
    statistics = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.raster_statistics_task")
    controller = controllers.CoverageModeController(None)
    panel = ui.RasterExploringPanel()
    panel.set_summary(adapter.read_raster_summary(layer))
    controller._active_layer, controller._raster_panel = layer, panel
    panel.bandChanged.connect(controller._on_raster_band_changed)
    panel.selectionChanged.connect(controller._on_raster_selection_changed)
    loop = QEventLoop()
    results, worker_threads, heartbeat = [], [], []
    complete = controller._raster_statistics_ready
    original_histogram = statistics.expression_histogram
    preview = importlib.import_module(PACKAGE + ".adapters.qgis.coverage_layers.preview_overlay")
    original_surface = preview.ExpressionSurface

    def read(*args, **kwargs):
        worker_threads.append(threading.current_thread() is threading.main_thread())
        return original_histogram(*args, **kwargs)

    def done(task, ok):
        assert threading.current_thread() is threading.main_thread()
        accepted = complete(task, ok)
        results.append((ok, accepted, task.materialize, task.sample_source))
        loop.quit()
        return accepted

    controller._raster_statistics_ready = done
    statistics.expression_histogram = read
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: heartbeat.append(True))
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    expression = ui.spectral_quantity("ndvi_vegetation", "rgbn", "Spectral_image")
    try:
        timer.start()
        timeout.start(15000)
        panel._use_quantity(expression)
        assert controller._raster_stats_task is not None
        assert not controller._raster_stats_task.materialize
        loop.exec()
        assert results == [(True, True, False, '')], results
        assert worker_threads == [False] and heartbeat, "the histogram must run off the GUI thread"
        assert Path(layer.source()).is_file(), "a local analysis must preserve its source file"
        key = controller._histogram_key(layer, 1, expression)
        assert sum(controller._histogram_cache[key][0]) == 766
        panel._on_preset_chosen((0.25, 0.75))
        assert len(worker_threads) == 1 and controller._raster_stats_task is None, "threshold edits must reuse the numeric histogram"
        panel._use_quantity('"Spectral_image@99"')
        assert controller._raster_stats_task is None and panel._quantity_status.text()
        panel._use_quantity('broken(')
        assert controller._raster_stats_task is None and panel._quantity_status.text()
        panel._quantity_edit.clear()
        panel._quantity_debounce.stop()
        panel._on_quantity_expression_changed()
        assert controller._raster_stats_task is None
        assert panel._histogram._counts == [], "clearing a formula must not show a raw band's old histogram"
        surface_threads, surfaces = [], []
        complete_surface = controller._raster_surface_ready

        def read_surface(*args, **kwargs):
            surface_threads.append(threading.current_thread() is threading.main_thread())
            return original_surface(*args, **kwargs)

        def surface_ready(task, ok):
            complete_surface(task, ok)
            surfaces.append((ok, task.surface))
            loop.quit()

        preview.ExpressionSurface = read_surface
        controller._raster_surface_ready = surface_ready
        panel._use_quantity(expression)
        panel._on_preset_chosen((0.25, 0.75))
        panel.set_preview_checked(True)
        heartbeat.clear()
        timeout.start(15000)
        controller._read_expression()
        assert controller._raster_surface_task is not None
        loop.exec()
        assert surface_threads == [False] and heartbeat, "preview grids must also be computed off the GUI thread"
        assert len(surfaces) == 1 and surfaces[0][0]
        assert surfaces[0][1].mask.sum() == 192
        assert abs(surfaces[0][1].kept_ratio - 192 / 766) < 1e-9
        assert len(controller._surfaces) == 1
    finally:
        timer.stop()
        timeout.stop()
        statistics.expression_histogram = original_histogram
        preview.ExpressionSurface = original_surface
        controller._cancel_raster_statistics()
        controller._cancel_raster_surface()
        panel.deleteLater()
        controller.deleteLater()


with tempfile.TemporaryDirectory(prefix="fm_raster_interactions_") as folder:
    layer = make_layer(folder)
    failures = []
    for name, check in (("numeric expressions, zero/NoData, histogram, presets and restoration", check_numeric_quantity),
                        ("expression histogram promotes its thresholds to a custom quantity", check_expression_histogram),
                        ("Ctrl+click keeps disjoint scalar samples", check_disjoint_picks),
                        ("rendered RGB selection after a custom quantity", check_rendered_after_quantity),
                        ("reset restores all object similarity defaults", check_reset),
                        ("threshold display stays faithful outside the sampled histogram", check_threshold_outside_sample),
                        ("a pending formula edit cannot erase the next spectral preset", check_pending_formula_edit),
                        ("changing quantity discards picks made on the previous quantity", check_quantity_switch),
                        ("object detection and per-reference similarity use real raster polygons", lambda _: check_object_modes(folder)),
                        ("constant raster bands retain their valid pixel count", lambda _: check_constant_band(folder)),
                        ("controller computes histograms off the GUI thread and validates formulas without reading", check_async_controller)):
        try:
            check(layer)
            print("PASS", name, flush=True)
        except Exception:
            failures.append(name)
            print("FAIL", name, flush=True)
            traceback.print_exc()
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    layer = None
    if failures:
        raise SystemExit(f"{len(failures)} raster interaction checks failed: {failures}")
    print("PASS all raster interaction checks", flush=True)
