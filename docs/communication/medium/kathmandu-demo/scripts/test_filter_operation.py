import os
import sys
import traceback

from qgis.PyQt.QtCore import Qt, QSettings, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDoubleSpinBox, QPushButton
from qgis.core import QgsApplication, QgsProject
from qgis.utils import iface

LOG_PATH = "/demo/filter-validation.log"
PLUGIN_ROOT = os.environ.get("FILTERMATE_PLUGIN_ROOT", "/tmp/qgisplugins")
STATE = {"checks": 0}


def log(message):
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


def layer(name):
    found = QgsProject.instance().mapLayersByName(name)
    if not found:
        raise RuntimeError(f"Missing layer: {name}")
    return found[0]


def log_features():
    roads = layer("OSM roads")
    log(
        "roads subset={!r}, feature_count={}, selected={}".format(
            roads.subsetString(), roads.featureCount(), roads.selectedFeatureCount()
        )
    )
    log(
        "active tasks={}".format(
            QgsApplication.taskManager().countActiveTasks()
        )
    )


def exit_process():
    os._exit(0)


def configure_and_filter():
    try:
        import qgis.utils

        QSettings().setValue("locale/userLocale", "en")
        qgis.utils.plugin_paths.insert(0, PLUGIN_ROOT)
        sys.path.insert(0, PLUGIN_ROOT)
        qgis.utils.updateAvailablePlugins()
        if not qgis.utils.loadPlugin("filter_mate"):
            raise RuntimeError("Could not load FilterMate")
        if not qgis.utils.startPlugin("filter_mate"):
            raise RuntimeError("Could not start FilterMate")

        plugin = qgis.utils.plugins["filter_mate"]
        plugin._show_whats_new = lambda: True
        plugin._show_discord_welcome = lambda: None
        plugin.run()
        STATE["plugin"] = plugin
        dock = plugin.app.dockwidget
        slope = layer("SRTM slope (%)")
        iface.setActiveLayer(slope)
        QTimer.singleShot(1500, lambda: configure_raster_filter(plugin, slope))
    except Exception:
        log(traceback.format_exc())
        QTimer.singleShot(3000, exit_process)


def configure_raster_filter(plugin, slope):
    try:
        dock = plugin.app.dockwidget
        dock.comboBox_filtering_current_layer.setLayer(slope)
        bounds = {}
        for control in dock.findChildren(QDoubleSpinBox):
            tip = control.toolTip()
            if "Lowest value kept" in tip:
                bounds["min"] = control
            elif "Highest value kept" in tip:
                bounds["max"] = control
        if set(bounds) != {"min", "max"}:
            raise RuntimeError("Could not find raster value-range controls")
        bounds["min"].setValue(20)
        bounds["max"].setValue(24)
        log("raster range set to {}..{}".format(
            bounds["min"].value(), bounds["max"].value()
        ))

        target_button = dock.pushButton_checkable_filtering_layers_to_filter
        target_button.setChecked(True)
        targets = dock.checkableComboBoxLayer_filtering_layers_to_filter
        found_target = False
        for index in range(targets.model().rowCount()):
            item = targets.model().item(index)
            log(f"target option={item.text()!r}")
            if "OSM roads" in item.text():
                item.setCheckState(Qt.CheckState.Checked)
                found_target = True
        if not found_target:
            raise RuntimeError("OSM roads is not available as a filter target")
        targets.checkedItemsChangedEvent()

        predicate_button = dock.pushButton_checkable_filtering_geometric_predicates
        predicate_button.setChecked(True)
        predicates = dock.comboBox_filtering_geometric_predicates
        found_predicate = False
        for index in range(predicates.model().rowCount()):
            item = predicates.model().item(index)
            log(f"predicate option={item.text()!r}")
            if "intersect" in item.text().lower():
                item.setCheckState(Qt.CheckState.Checked)
                found_predicate = True
        if not found_predicate:
            raise RuntimeError("Intersect is not available")

        log("source=" + dock.comboBox_filtering_current_layer.currentLayer().name())
        log_features()
        dock.pushButton_action_filter.click()
        log("filter button clicked")
        QTimer.singleShot(1000, wait_for_filter)
    except Exception:
        log(traceback.format_exc())
        QTimer.singleShot(3000, exit_process)


def wait_for_filter():
    STATE["checks"] += 1
    log_features()
    if QgsApplication.taskManager().countActiveTasks() and STATE["checks"] < 60:
        QTimer.singleShot(1000, wait_for_filter)
        return
    if STATE["phase"] == "raster":
        log("raster-to-road filter completed")
        QTimer.singleShot(
            1800, lambda: configure_school_filter(STATE["plugin"])
        )
    else:
        schools = layer("OSM schools")
        log(
            "schools subset={!r}, feature_count={}, selected={}".format(
                schools.subsetString(),
                schools.featureCount(),
                schools.selectedFeatureCount(),
            )
        )
        configure_export(STATE["plugin"])


def set_filter_targets(dock, names):
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


def configure_school_filter(plugin):
    try:
        dock = plugin.app.dockwidget
        roads = layer("OSM roads")
        road_ids = [feature.id() for feature in roads.getFeatures()]
        log(f"filtered road source ids={road_ids!r}")
        if not road_ids:
            raise RuntimeError("The first filter produced no roads")

        iface.setActiveLayer(roads)
        dock.comboBox_filtering_current_layer.setLayer(roads)
        dock.mGroupBox_exploring_multiple_selection.setChecked(True)
        picker = (
            dock.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
        )
        picker.setCheckedFeatureIds(road_ids)

        dock.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        set_filter_targets(dock, ["OSM schools"])
        dock.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        set_intersect_only(dock)
        dock.pushButton_checkable_filtering_buffer_value.setChecked(True)
        dock.mQgsDoubleSpinBox_filtering_buffer_value.setValue(500)
        log(
            "second source={}, selected roads={}, targets_enabled={}, "
            "predicates_enabled={}, buffer={} m".format(
                dock.comboBox_filtering_current_layer.currentLayer().name(),
                roads.selectedFeatureCount(),
                dock.pushButton_checkable_filtering_layers_to_filter.isChecked(),
                dock.pushButton_checkable_filtering_geometric_predicates.isChecked(),
                dock.mQgsDoubleSpinBox_filtering_buffer_value.value(),
            )
        )
        log_features()
        STATE["phase"] = "vector"
        STATE["checks"] = 0
        dock.pushButton_action_filter.click()
        log("second filter button clicked")
        QTimer.singleShot(1000, wait_for_filter)
    except Exception:
        log(traceback.format_exc())
        QTimer.singleShot(3000, exit_process)


def configure_export(plugin):
    try:
        dock = plugin.app.dockwidget
        export_dir = "/demo/exported"
        export_path = os.path.join(export_dir, "kathmandu-final.gpkg")
        os.makedirs(export_dir, exist_ok=True)
        dock.toolBox_tabTools.setCurrentIndex(1)
        dock.pushButton_checkable_exporting_layers.setChecked(True)
        layers = dock.checkableComboBoxLayer_exporting_layers
        selected_layers = []
        for index in range(layers.model().rowCount()):
            item = layers.model().item(index)
            selected = any(name in item.text() for name in ("OSM roads", "OSM schools"))
            item.setCheckState(
                Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked
            )
            if selected:
                selected_layers.append(item.text())
        layers.checkedItemsChangedEvent()
        dock.pushButton_checkable_exporting_datatype.setChecked(True)
        format_index = dock.comboBox_exporting_datatype.findText(
            "GPKG", Qt.MatchFlag.MatchContains
        )
        if format_index < 0:
            raise RuntimeError("GeoPackage export is not available")
        dock.comboBox_exporting_datatype.setCurrentIndex(format_index)
        dock.pushButton_checkable_exporting_output_folder.setChecked(True)
        dock.lineEdit_exporting_output_folder.setText(export_path)
        dock.project_property_changed("has_output_folder_to_export", True)
        dock.project_property_changed("output_folder_to_export", export_path)
        dock.pushButton_checkable_exporting_styles.setChecked(True)
        log(
            "export layers={}, format={}, folder={}".format(
                selected_layers,
                dock.comboBox_exporting_datatype.currentText(),
                dock.lineEdit_exporting_output_folder.text(),
            )
        )
        iface.mapCanvas().zoomToFullExtent()
        iface.mapCanvas().refresh()
        QTimer.singleShot(1800, lambda: export_now(dock))
    except Exception:
        log(traceback.format_exc())
        QTimer.singleShot(3000, exit_process)


def export_now(dock):
    try:
        iface.mapCanvas().waitWhileRendering()
        iface.messageBar().clearWidgets()
        iface.mainWindow().grab().save("/demo/captures/validated-filter-result.png")
        QTimer.singleShot(1200, accept_export_recap)
        dock.pushButton_action_export.click()
        log("export button clicked")
        QTimer.singleShot(2500, wait_for_export)
    except Exception:
        log(traceback.format_exc())
        QTimer.singleShot(3000, exit_process)


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
    if confirm is not None:
        confirm.click()
        log("export recap confirmed")


def wait_for_export():
    STATE["checks"] += 1
    active = QgsApplication.taskManager().countActiveTasks()
    files = sorted(os.listdir("/demo/exported"))
    output_exists = os.path.exists("/demo/exported/kathmandu-final.gpkg")
    log(
        f"export check {STATE['checks']}: active={active}, "
        f"output_exists={output_exists}, files={files}"
    )
    if (active or not output_exists) and STATE["checks"] < 45:
        QTimer.singleShot(1000, wait_for_export)
        return
    project = QgsProject.instance()
    project.setFileName("/demo/Kathmandu_FilterMate_Final.qgz")
    log("final project saved=" + str(project.write()))
    iface.mapCanvas().zoomToFullExtent()
    iface.mapCanvas().refresh()
    QTimer.singleShot(2000, capture_and_exit)


def capture_and_exit():
    iface.mapCanvas().waitWhileRendering()
    iface.messageBar().clearWidgets()
    iface.mainWindow().grab().save("/demo/captures/validated-filter-result.png")
    exit_process()


QTimer.singleShot(5000, configure_and_filter)
STATE["phase"] = "raster"
QTimer.singleShot(90000, exit_process)
