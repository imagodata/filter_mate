import os
import sqlite3
import subprocess
import sys
import time
import traceback

from qgis.PyQt.QtCore import Qt, QSettings, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDoubleSpinBox, QPushButton, QScrollArea
from qgis.core import QgsApplication, QgsCoordinateTransform, QgsProject, QgsRectangle
from qgis.utils import iface

DEMO_ROOT = os.environ.get("FILTERMATE_DEMO_ROOT", "/demo")
CAPTURE_ROOT = os.path.join(DEMO_ROOT, "video")
FRAME_DIRECTORY = os.path.join(CAPTURE_ROOT, "frames")
FINAL_VIDEO = os.environ.get(
    "FILTERMATE_VIDEO_OUTPUT",
    os.path.join(CAPTURE_ROOT, "Kathmandu_FilterMate_Walkthrough.mp4"),
)
CAPTIONS = os.path.join(CAPTURE_ROOT, "captions-en.srt")
SLOPE_MIN = float(os.environ.get("FILTERMATE_SLOPE_MIN", "18"))
SLOPE_MAX = float(os.environ.get("FILTERMATE_SLOPE_MAX", "24"))
BUFFER_METERS = float(os.environ.get("FILTERMATE_BUFFER_M", "150"))
LOG_PATH = os.path.join(CAPTURE_ROOT, "recording.log")
PLUGIN_ROOT = os.environ.get("FILTERMATE_PLUGIN_ROOT", "/tmp/qgisplugins")
FFMPEG_EXECUTABLE = os.environ.get("FILTERMATE_FFMPEG", "ffmpeg")
STATE = {"checks": 0, "started": None, "frame_timer": None, "plugin": None}


def schedule(delay, callback, *args):
    QTimer.singleShot(delay, lambda: invoke(callback, *args))


def invoke(callback, *args):
    try:
        callback(*args)
    except Exception:
        fail()


def log(message):
    elapsed = time.monotonic() - STATE["started"] if STATE["started"] else 0
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(f"{elapsed:05.1f}s {message}\n")


def layer(name):
    found = QgsProject.instance().mapLayersByName(name)
    if not found:
        raise RuntimeError(f"Missing layer: {name}")
    return found[0]


def set_source(dock, source):
    iface.setActiveLayer(source)
    dock.comboBox_filtering_current_layer.setLayer(source)
    QApplication.processEvents()


def zoom_to_layer(source, margin=1.25):
    canvas = iface.mapCanvas()
    extent = source.extent()
    destination_crs = canvas.mapSettings().destinationCrs()
    if source.crs() != destination_crs:
        transform = QgsCoordinateTransform(
            source.crs(), destination_crs, QgsProject.instance()
        )
        extent = transform.transformBoundingBox(extent)
    extent.scale(margin)
    canvas.setExtent(extent)
    canvas.refresh()


def zoom_to_filtered_layers(names, margin=1.6):
    canvas = iface.mapCanvas()
    destination_crs = canvas.mapSettings().destinationCrs()
    result_extent = None

    for name in names:
        source = layer(name)
        transform = None
        if source.crs() != destination_crs:
            transform = QgsCoordinateTransform(
                source.crs(), destination_crs, QgsProject.instance()
            )
        for feature in source.getFeatures():
            geometry = feature.geometry()
            if geometry.isEmpty():
                continue
            feature_extent = geometry.boundingBox()
            if transform is not None:
                feature_extent = transform.transformBoundingBox(feature_extent)
            if result_extent is None:
                result_extent = QgsRectangle(feature_extent)
            else:
                result_extent.combineExtentWith(feature_extent)

    if result_extent is None:
        raise RuntimeError(f"No geometries available to zoom to: {names}")
    if result_extent.width() <= 0 or result_extent.height() <= 0:
        result_extent.grow(max(result_extent.width(), result_extent.height(), 100.0))
    result_extent.scale(margin)
    canvas.setExtent(result_extent)
    canvas.refresh()
    QApplication.processEvents()


def set_targets(dock, names):
    combo = dock.checkableComboBoxLayer_filtering_layers_to_filter
    for index in range(combo.model().rowCount()):
        item = combo.model().item(index)
        item.setCheckState(
            Qt.CheckState.Checked
            if any(name in item.text() for name in names)
            else Qt.CheckState.Unchecked
        )
    combo.checkedItemsChangedEvent()


def set_intersect_only(dock):
    combo = dock.comboBox_filtering_geometric_predicates
    for index in range(combo.model().rowCount()):
        item = combo.model().item(index)
        item.setCheckState(
            Qt.CheckState.Checked
            if "intersect" in item.text().lower()
            else Qt.CheckState.Unchecked
        )


def align_panels(dock):
    splitter = dock.splitter_main
    total = sum(splitter.sizes())
    splitter.setSizes([total // 2, total - total // 2])
    QApplication.processEvents()
    log(
        "panels exploring={} filtering={} dock={}".format(
            dock.frame_exploring.geometry().getRect(),
            dock.frame_toolset.geometry().getRect(),
            dock.geometry().getRect(),
        )
    )


def center_widget(widget):
    """Scroll every parent QScrollArea so the widget sits mid-viewport."""
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            QApplication.processEvents()
            viewport = parent.viewport()
            top = widget.mapTo(parent.widget(), widget.rect().topLeft()).y()
            target = top + widget.height() // 2 - viewport.height() // 2
            bar = parent.verticalScrollBar()
            bar.setValue(max(bar.minimum(), min(bar.maximum(), target)))
            log(f"centered {widget.objectName()} scroll={bar.value()}/{bar.maximum()}")
        parent = parent.parentWidget()
    QApplication.processEvents()


def show_selection_mode(mode):
    dock = STATE["plugin"].app.dockwidget
    roads = layer("OSM roads")
    set_source(dock, roads)

    groups = {
        "single": dock.mGroupBox_exploring_single_selection,
        "multiple": dock.mGroupBox_exploring_multiple_selection,
        "expression": dock.mGroupBox_exploring_custom_selection,
    }
    for name, group in groups.items():
        group.setChecked(name == mode)
    center_widget(groups[mode])

    road_ids = [49, 168, 175, 274]
    roads.removeSelection()
    if mode == "single":
        roads.selectByIds([road_ids[0]])
        picker = dock.mFeaturePickerWidget_exploring_single_selection
        picker.setLayer(roads)
        picker.setFeature(road_ids[0])
    elif mode == "multiple":
        roads.selectByIds(road_ids)
        picker = (
            dock.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
        )
        picker.setCheckedFeatureIds(road_ids)
    else:
        expression = '"highway" IN (\'primary\', \'secondary\')'
        roads.selectByExpression(expression)
        dock.mFieldExpressionWidget_exploring_custom_selection.setExpression(
            expression
        )
    log(f"selection mode={mode}, selected={roads.selectedFeatureCount()}")
    iface.mapCanvas().refresh()


def show_map_buttons():
    dock = STATE["plugin"].app.dockwidget
    roads = layer("OSM roads")
    set_source(dock, roads)
    zoom_to_layer(roads)
    center_widget(dock.pushButton_exploring_zoom)
    dock.pushButton_exploring_zoom.click()
    dock.pushButton_exploring_identify.click()
    selecting = dock.pushButton_checkable_exploring_selecting
    if not selecting.isChecked():
        selecting.click()
    schedule(1800, zoom_to_layer, layer("SRTM slope (%)"), 1.1)
    log(
        "Exploring actions demonstrated: Zoom, Identify, Selecting preview; "
        "Tracking, Linking, More and Reset shown in the tool rail"
    )


def configure_raster_filter():
    try:
        dock = STATE["plugin"].app.dockwidget
        slope = layer("SRTM slope (%)")
        layer("OSM roads").removeSelection()
        selecting = dock.pushButton_checkable_exploring_selecting
        if selecting.isChecked():
            selecting.click()
        set_source(dock, slope)
        bounds = {}
        for control in dock.findChildren(QDoubleSpinBox):
            tip = control.toolTip()
            if "Lowest value kept" in tip:
                bounds["min"] = control
            elif "Highest value kept" in tip:
                bounds["max"] = control
        if set(bounds) != {"min", "max"}:
            raise RuntimeError("Could not find raster value-range controls")
        bounds["min"].setValue(SLOPE_MIN)
        bounds["max"].setValue(SLOPE_MAX)
        center_widget(bounds["min"])
        dock.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        set_targets(dock, ["OSM roads"])
        dock.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        set_intersect_only(dock)
        center_widget(dock.comboBox_filtering_geometric_predicates)
        zoom_to_layer(slope, 1.1)
        QApplication.processEvents()
        log(
            "raster source range={}, target=OSM roads, predicate=Intersect".format(
                (bounds["min"].value(), bounds["max"].value())
            )
        )
        schedule(2500, run_filter, dock, "raster")
    except Exception:
        fail()


def run_filter(dock, phase):
    STATE["phase"] = phase
    STATE["checks"] = 0
    dock.pushButton_action_filter.click()
    log(f"{phase} filter clicked")
    schedule(1000, wait_for_filter)


def wait_for_filter():
    STATE["checks"] += 1
    roads = layer("OSM roads")
    active_tasks = QgsApplication.taskManager().countActiveTasks()
    count = roads.featureCount()
    log(f"filter phase={STATE['phase']}, roads={count}, active_tasks={active_tasks}")
    if active_tasks or (STATE["phase"] == "raster" and not 0 < count < STATE["total_roads"]):
        if STATE["checks"] < 20:
            schedule(1000, wait_for_filter)
            return
        raise RuntimeError(f"{STATE['phase']} filter did not settle")

    if STATE["phase"] == "raster":
        zoom_to_filtered_layers(["OSM roads"], margin=1.6)
        log(f"raster-to-vector result: {count} roads; zoomed to filtered road geometries")
        schedule(4500, configure_school_filter)
    else:
        schools = layer("OSM schools")
        if not 0 < schools.featureCount() < STATE["total_schools"]:
            raise RuntimeError(
                f"Unexpected filtered school count: {schools.featureCount()}"
            )
        zoom_to_filtered_layers(["OSM roads", "OSM schools"], margin=1.6)
        log(f"vector-to-vector result: {count} roads and {schools.featureCount()} schools; zoomed to final features")
        schedule(4500, configure_export)


def configure_school_filter():
    try:
        dock = STATE["plugin"].app.dockwidget
        roads = layer("OSM roads")
        road_ids = [feature.id() for feature in roads.getFeatures()]
        if not road_ids:
            raise RuntimeError("No filtered roads to use as source")

        set_source(dock, roads)
        dock.mGroupBox_exploring_multiple_selection.setChecked(True)
        picker = (
            dock.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
        )
        picker.setCheckedFeatureIds(road_ids)
        dock.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        set_targets(dock, ["OSM schools"])
        dock.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        set_intersect_only(dock)
        dock.pushButton_checkable_filtering_buffer_value.setChecked(True)
        dock.mQgsDoubleSpinBox_filtering_buffer_value.setValue(BUFFER_METERS)
        center_widget(dock.mQgsDoubleSpinBox_filtering_buffer_value)
        log(
            f"vector source={len(road_ids)} filtered roads, target=OSM schools, "
            f"predicate=Intersect, buffer={BUFFER_METERS:g} m"
        )
        run_filter(dock, "vector")
    except Exception:
        fail()


def configure_export():
    try:
        dock = STATE["plugin"].app.dockwidget
        output_dir = os.path.join(DEMO_ROOT, "video-output")
        output_path = os.path.join(output_dir, "Kathmandu_final.gpkg")
        os.makedirs(output_dir, exist_ok=True)
        dock.toolBox_tabTools.setCurrentIndex(1)
        dock.pushButton_checkable_exporting_layers.setChecked(True)

        combo = dock.checkableComboBoxLayer_exporting_layers
        selected_layers = []
        for index in range(combo.model().rowCount()):
            item = combo.model().item(index)
            selected = any(name in item.text() for name in ("OSM roads", "OSM schools"))
            item.setCheckState(
                Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked
            )
            if selected:
                selected_layers.append(item.text())
        combo.checkedItemsChangedEvent()

        dock.pushButton_checkable_exporting_datatype.setChecked(True)
        format_index = dock.comboBox_exporting_datatype.findText(
            "GPKG", Qt.MatchFlag.MatchContains
        )
        if format_index < 0:
            raise RuntimeError("GeoPackage export is not available")
        dock.comboBox_exporting_datatype.setCurrentIndex(format_index)
        dock.pushButton_checkable_exporting_output_folder.setChecked(True)
        dock.lineEdit_exporting_output_folder.setText(output_path)
        dock.project_property_changed("has_output_folder_to_export", True)
        dock.project_property_changed("output_folder_to_export", output_path)
        dock.pushButton_checkable_exporting_styles.setChecked(True)
        log(f"export configured: {selected_layers}, {output_path}")
        STATE["checks"] = 0
        schedule(1200, export_now, dock)
    except Exception:
        fail()


def export_now(dock):
    dock.pushButton_action_export.click()
    log("export action clicked")
    schedule(1200, accept_export_recap)
    schedule(3000, wait_for_export)


def accept_export_recap():
    dock = STATE["plugin"].app.dockwidget
    dialog = getattr(dock, "_export_recap_dialog", None)
    if dialog is None:
        dialog = QApplication.activeModalWidget()
    if dialog is None:
        log("export recap dialog not shown")
        return
    buttons = [
        button
        for button in dialog.findChildren(QPushButton)
        if button.isVisible()
    ]
    log("export recap buttons=" + repr([button.text() for button in buttons]))
    confirm = next(
        (
            button
            for button in buttons
            if button.isDefault()
            or "export" in button.text().lower()
            or "confirm" in button.text().lower()
        ),
        buttons[-1] if buttons else None,
    )
    if confirm is None:
        raise RuntimeError("Could not find the export confirmation button")
    confirm.click()
    log("export recap confirmed")


def wait_for_export():
    output_path = os.path.join(
        DEMO_ROOT, "video-output", "Kathmandu_final.gpkg"
    )
    if not os.path.exists(output_path):
        STATE["checks"] += 1
        if STATE["checks"] >= 30:
            raise RuntimeError("GeoPackage export did not finish")
        schedule(1000, wait_for_export)
        return
    with sqlite3.connect(output_path) as connection:
        counts = {
            name: connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            for name in ("OSM roads", "OSM schools")
        }
    if not all(counts.values()):
        raise RuntimeError(f"Unexpected exported feature counts: {counts}")
    log(f"verified exported feature counts: {counts}")
    log("GeoPackage export created")
    schedule(5000, finish_recording)


def capture_frame():
    try:
        frame_path = os.path.join(
            FRAME_DIRECTORY, f"frame-{STATE['frame_index']:05d}.png"
        )
        if not iface.mainWindow().grab().save(frame_path, "PNG"):
            raise RuntimeError(f"Could not save QGIS frame: {frame_path}")
        STATE["frame_index"] += 1
        STATE["frame_timestamps"].append(time.monotonic() - STATE["started"])
    except Exception:
        fail()


def finish_recording():
    try:
        frame_timer = STATE.get("frame_timer")
        if frame_timer is not None:
            frame_timer.stop()
        capture_frame()
        frame_count = STATE["frame_index"]
        timestamps = STATE["frame_timestamps"]
        if frame_count < 2 or len(timestamps) != frame_count:
            raise RuntimeError("Not enough timestamped frames to encode the recording")
        log(f"QGIS window capture finished: {frame_count} frames")

        manifest_path = os.path.join(CAPTURE_ROOT, "frames.txt")
        manifest_lines = []
        for index in range(frame_count):
            frame_path = os.path.abspath(
                os.path.join(FRAME_DIRECTORY, f"frame-{index:05d}.png")
            ).replace("\\", "/")
            manifest_lines.append(f"file '{frame_path}'")
            if index + 1 < frame_count:
                duration = timestamps[index + 1] - timestamps[index]
            else:
                duration = 1.0
            manifest_lines.append(f"duration {max(duration, 0.001):.6f}")
        manifest_lines.append(f"file '{frame_path}'")
        with open(manifest_path, "w", encoding="utf-8") as manifest:
            manifest.write("\n".join(manifest_lines) + "\n")

        subtitle_path = os.path.basename(CAPTIONS)
        result = subprocess.run(
            [
                FFMPEG_EXECUTABLE,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                manifest_path,
                "-vf",
                (
                    f"fps=30,scale=1920:1080:flags=lanczos,"
                    f"subtitles={subtitle_path}:force_style="
                    "'FontName=Arial,FontSize=10,Outline=1,Shadow=1,"
                    "MarginV=32,Alignment=2'"
                ),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                FINAL_VIDEO,
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=CAPTURE_ROOT,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        for filename in os.listdir(FRAME_DIRECTORY):
            if filename.startswith("frame-") and filename.endswith(".png"):
                os.remove(os.path.join(FRAME_DIRECTORY, filename))
        os.rmdir(FRAME_DIRECTORY)
        os.remove(manifest_path)
        log(f"video with captions created: {FINAL_VIDEO}")
        os._exit(0)
    except Exception:
        fail()


def fail():
    log(traceback.format_exc())
    frame_timer = STATE.get("frame_timer")
    if frame_timer is not None:
        frame_timer.stop()
    os._exit(1)


def start_recording():
    try:
        STATE["started"] = time.monotonic()
        os.makedirs(FRAME_DIRECTORY, exist_ok=True)
        for filename in os.listdir(FRAME_DIRECTORY):
            if filename.startswith("frame-") and filename.endswith(".png"):
                os.remove(os.path.join(FRAME_DIRECTORY, filename))
        STATE["frame_index"] = 0
        STATE["frame_timestamps"] = []
        frame_timer = QTimer()
        frame_timer.setInterval(250)
        frame_timer.timeout.connect(capture_frame)
        STATE["frame_timer"] = frame_timer
        capture_frame()
        frame_timer.start()
        schedule(4000, show_selection_mode, "single")
        schedule(9000, show_selection_mode, "multiple")
        schedule(14000, show_selection_mode, "expression")
        schedule(20000, show_map_buttons)
        schedule(28000, configure_raster_filter)
        schedule(120000, finish_recording)
    except Exception:
        fail()


def start_demo():
    try:
        os.makedirs(CAPTURE_ROOT, exist_ok=True)
        with open(LOG_PATH, "w", encoding="utf-8") as log_file:
            log_file.write("Kathmandu FilterMate screen recording\n")

        import qgis.utils

        QSettings().setValue("locale/userLocale", "en")
        sys.dont_write_bytecode = True
        qgis.utils.plugin_paths.insert(0, PLUGIN_ROOT)
        sys.path.insert(0, PLUGIN_ROOT)
        qgis.utils.updateAvailablePlugins()
        if not qgis.utils.loadPlugin("filter_mate"):
            raise RuntimeError("Could not load FilterMate")
        plugin_metadata = os.path.join(PLUGIN_ROOT, "filter_mate", "metadata.txt")
        with open(plugin_metadata, encoding="utf-8") as metadata_file:
            version = next(
                line.partition("=")[2].strip()
                for line in metadata_file
                if line.startswith("version=")
            )
        log(f"loading FilterMate {version} from {PLUGIN_ROOT}")
        if not qgis.utils.startPlugin("filter_mate"):
            raise RuntimeError("Could not start FilterMate")

        plugin = qgis.utils.plugins["filter_mate"]
        plugin._show_whats_new = lambda: True
        plugin._show_discord_welcome = lambda: None
        plugin.run()
        iface.messageBar().clearWidgets()
        STATE["plugin"] = plugin

        main_window = iface.mainWindow()
        main_window.setGeometry(main_window.screen().availableGeometry())
        main_window.showNormal()
        main_window.raise_()
        main_window.activateWindow()
        dock = plugin.app.dockwidget
        dock.toolBox_tabTools.setCurrentIndex(0)
        set_source(dock, layer("SRTM slope (%)"))
        zoom_to_layer(layer("SRTM slope (%)"), 1.1)
        QApplication.processEvents()
        STATE["total_roads"] = layer("OSM roads").featureCount()
        STATE["total_schools"] = layer("OSM schools").featureCount()
        align_panels(dock)
        iface.mapCanvas().refresh()
        schedule(2500, start_recording)
    except Exception:
        fail()


schedule(5000, start_demo)
