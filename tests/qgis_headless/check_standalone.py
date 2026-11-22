# -*- coding: utf-8 -*-
"""FilterMate outside the QGIS application: the host window, its ``iface``, and the plugin in it.

Run by the standalone host itself, in a qgis/qgis image (no display needed):

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash -c \\
        'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm >/dev/null 2>&1; \\
         cp -r /src /tmp/copy; FM_FIXTURES=/tmp/fm FILTERMATE_HOME=/tmp/fmhome \\
         python3 /tmp/copy/standalone/_bootstrap.py --offscreen --size 1600x1000 \\
             --code /tmp/copy/tests/qgis_headless/check_standalone.py'

Prints one PASS / FAIL line per check and "N/M passed"; the exit code is 1 when a check failed.
The window is then closed as a user closes it: an exit code other than 0 or 1 is a crash on the way out.
The GUI smoke of the plugin runs in the same host with ``--no-plugin --code run_gui_smoke.py``.
"""
import json
import os
import tempfile
import time

import qgis.utils
from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QPoint, QSettings, Qt
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QDockWidget, QMenu, QToolBar
from qgis.utils import iface

PACKAGE = "filter_mate"
FIXTURES = os.environ.get("FM_FIXTURES", "/tmp/fm")
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if detail and not condition else ""), flush=True)
    return bool(condition)


def wait(condition, seconds=30.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        try:
            if condition():
                return True
        except Exception:
            pass
        time.sleep(0.01)
    return False


def _path(text):
    """A path as the system compares paths (Qt writes forward slashes on Windows)."""
    return os.path.normcase(os.path.normpath(text))


def tasks_idle():
    return not QgsApplication.taskManager().activeTasks()


def layer(name):
    found = QgsProject.instance().mapLayersByName(name)
    return found[0] if found else None


def main():
    QSettings().setValue("qgis/digitizing/validate_geometries", 0)  # FilterMate asks about it otherwise
    with open(os.path.join(FIXTURES, "manifest.json"), encoding="utf-8") as stream:
        manifest = json.load(stream)
    window = iface.mainWindow()
    project = QgsProject.instance()
    plugin = qgis.utils.plugins.get(PACKAGE)

    # --- the host ---------------------------------------------------------------------------------------------
    check("iface is the standalone interface", type(iface).__name__ == "StandaloneInterface")
    check("the window is shown", window.isVisible(), window.windowTitle())
    check("the map canvas carries the name QGIS saves its extent under", iface.mapCanvas().objectName() == "theMapCanvas")
    check("View > Panels has the name the plugin looks for", window.findChild(QMenu, "mPanelMenu") is not None)
    check("the layer panel is a dock named as in QGIS", window.findChild(QDockWidget, "Layers") is not None)
    profile = _path(os.environ["QGIS_CUSTOM_CONFIG_PATH"])
    check("the settings are kept in the application's own profile",
          _path(QSettings().fileName()).startswith(profile), QSettings().fileName())
    check("QGIS writes its profile there too",
          _path(QgsApplication.qgisSettingsDirPath()).startswith(profile), QgsApplication.qgisSettingsDirPath())
    check("Processing is initialised", QgsApplication.processingRegistry().algorithmById("native:buffer") is not None)

    # --- the plugin, loaded as QGIS loads it --------------------------------------------------------------------
    if not check("FilterMate is registered in qgis.utils.plugins", plugin is not None):
        return
    wait(lambda: plugin.app is not None and plugin.app.dockwidget is not None, 60)
    dock = plugin.app.dockwidget if plugin.app is not None else None
    if not check("the dock exists", dock is not None):
        return
    check("the dock is shown in the window", dock.isVisible() and dock.window() is window)
    check("the dock is on the right, as in QGIS",
          window.dockWidgetArea(dock) == Qt.DockWidgetArea.RightDockWidgetArea, str(window.dockWidgetArea(dock)))
    check("the dock is listed in View > Panels", dock.toggleViewAction() in window.findChild(QMenu, "mPanelMenu").actions())
    check("the plugin has its toolbar", any(bar.windowTitle() == "FilterMate" for bar in window.findChildren(QToolBar)),
          str([bar.windowTitle() for bar in window.findChildren(QToolBar)]))
    check("the plugin has its menu", any("FilterMate" in action.text() for action in window.menuBar().actions()),
          str([action.text() for action in window.menuBar().actions()]))
    check("the Processing provider of FilterMate is registered",
          QgsApplication.processingRegistry().providerById("filtermate") is not None)
    check("the configuration is in the application's profile",
          os.path.isfile(os.path.join(QgsApplication.qgisSettingsDirPath(), "FilterMate", "config.json")),
          QgsApplication.qgisSettingsDirPath())

    # --- data ---------------------------------------------------------------------------------------------------
    added = window.sources.open_paths([manifest["zones"], manifest["dem"]])
    zones, dem = layer("zones"), layer("dem")
    check("a GeoPackage and a GeoTIFF open from their paths", added == 2 and isinstance(zones, QgsVectorLayer)
          and isinstance(dem, QgsRasterLayer), f"added={added} layers={[item.name() for item in project.mapLayers().values()]}")
    if zones is None or dem is None:
        return
    check("the first layer gives the project its CRS", project.crs().authid() == "EPSG:2154", project.crs().authid())
    check("the map follows the project's CRS", iface.mapCanvas().mapSettings().destinationCrs().authid() == "EPSG:2154")
    wait(lambda: not iface.mapCanvas().extent().isEmpty() and iface.mapCanvas().extent().intersects(zones.extent()), 10)
    check("the map shows the data", iface.mapCanvas().extent().intersects(zones.extent()), iface.mapCanvas().extent().toString())
    check("a layer is current in the layer panel", iface.activeLayer() is not None)
    check("setActiveLayer changes the current layer", iface.setActiveLayer(dem) and iface.activeLayer() is dem)
    iface.setActiveLayer(zones)
    registered = wait(lambda: zones.id() in plugin.app.PROJECT_LAYERS and tasks_idle(), 60)
    check("FilterMate registered the layers", registered, str(list(getattr(plugin.app, "PROJECT_LAYERS", {}))))

    # --- a filter, through the plugin ---------------------------------------------------------------------------
    api = plugin.get_public_api()
    total = zones.featureCount()
    applied = api.apply_filter("zones", "\"name\" LIKE 'east%'", "check_standalone")
    wait(lambda: zones.subsetString() != "" and tasks_idle(), 30)
    check("a filter applied through FilterMate reaches the layer",
          bool(applied) and zones.featureCount() == 2, f"applied={applied} subset={zones.subsetString()!r} count={zones.featureCount()}")
    check("FilterMate reports the filter", "zones" in json.dumps(api.get_active_filters()), str(api.get_active_filters()))
    api.clear_filter("zones")
    wait(lambda: zones.subsetString() == "" and tasks_idle(), 30)
    check("clearing it gives every feature back", zones.featureCount() == total == 5, f"{zones.featureCount()} / {total}")

    # --- the map tools the libraries do not have ----------------------------------------------------------------
    canvas = iface.mapCanvas()
    canvas.setExtent(zones.extent())
    canvas.refresh()
    wait(tasks_idle, 5)
    iface.actionSelectRectangle().trigger()
    check("the select action sets its map tool", type(canvas.mapTool()).__name__ == "SelectTool", type(canvas.mapTool()).__name__)
    viewport = canvas.viewport()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(2, 2))
    QTest.mouseMove(viewport, QPoint(viewport.width() // 2, viewport.height() // 2))
    QTest.mouseMove(viewport, QPoint(viewport.width() - 3, viewport.height() - 3))
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                       QPoint(viewport.width() - 3, viewport.height() - 3))
    check("a rectangle drawn over the map selects the features of the current layer",
          zones.selectedFeatureCount() == 5, str(zones.selectedFeatureCount()))
    window.deselect_all()
    check("deselect all clears the selection", zones.selectedFeatureCount() == 0)
    iface.actionPan().trigger()
    check("the pan action gives the pan tool back", type(canvas.mapTool()).__name__ == "QgsMapToolPan")

    # --- windows of the host ------------------------------------------------------------------------------------
    table = iface.showAttributeTable(zones)
    wait(lambda: table is not None and table.isVisible(), 5)
    check("the attribute table opens", table is not None and table.isVisible())
    if table is not None:
        table.close()
    dialog = window.sources.show_dialog()
    wait(lambda: dialog.isVisible(), 5)
    screens = dialog._list.count()
    check("the source screens of QGIS are offered", screens >= 8, str(screens))
    check("the first one is a real source screen", type(dialog._stack.currentWidget()).__name__ != "QLabel",
          type(dialog._stack.currentWidget()).__name__)
    dialog.close()
    iface.messageBar().pushInfo("FilterMate", "check")
    check("the message bar takes messages", len(iface.messageBar().items()) >= 1)
    iface.messageBar().clearWidgets()

    # --- projects -----------------------------------------------------------------------------------------------
    events = []
    iface.projectRead.connect(lambda: events.append("read"))
    iface.newProjectCreated.connect(lambda: events.append("new"))
    api.apply_filter("zones", "\"name\" = 'west_a'", "check_standalone")
    wait(lambda: zones.featureCount() == 1 and tasks_idle(), 30)
    path = os.path.join(tempfile.mkdtemp(), "standalone.qgz")
    project.setFileName(path)
    check("the project is saved", window.save_project() and os.path.isfile(path))
    check("a new project empties the map and tells the plugin", iface.newProject() and not project.mapLayers()
          and events == ["new"], f"{events} layers={len(project.mapLayers())}")
    wait(tasks_idle, 30)
    check("the project opens again and tells the plugin", iface.addProject(path) and events == ["new", "read"], str(events))
    zones = layer("zones")
    check("its layers and its filter are back", zones is not None and layer("dem") is not None
          and zones.featureCount() == 1, f"subset={zones.subsetString() if zones else None!r}")
    wait(lambda: zones is not None and zones.id() in plugin.app.PROJECT_LAYERS and tasks_idle(), 60)
    check("FilterMate registered the layers of the opened project",
          zones is not None and zones.id() in plugin.app.PROJECT_LAYERS)
    wait(lambda: False, 4.0)  # the plugin refreshes its dock a moment after a project opens: let it, before closing
    project.setDirty(False)


if __name__ == "__main__":
    application = QgsApplication.instance()
    application.setQuitOnLastWindowClosed(False)
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    # Closing the window as a user does: the plugin is unloaded, nothing is asked, nothing is left behind.
    try:
        iface.mainWindow().close()
        wait(lambda: False, 1.0)
        check("closing the window unloads the plugin", PACKAGE not in qgis.utils.plugins)
        check("the window is closed", not iface.mainWindow().isVisible())
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    application.exit(1 if failed else 0)
