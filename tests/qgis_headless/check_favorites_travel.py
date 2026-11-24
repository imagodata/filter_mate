# -*- coding: utf-8 -*-
"""The favorites of a project travel with its .qgz to another computer (2026-11-24).

Each computer is a QGIS profile of its own (``--profiles-path``), so FilterMate has its own SQLite there. One QGIS run
per step, ``FM_ROLE`` saying which; the user's gestures: open the project, add a favorite, Ctrl+S.

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash /src/tests/qgis_headless/check_favorites_travel.sh

Roles: ``A1`` computer A makes the project, adds fav_A1, saves; ``B1`` computer B opens it; ``A2`` A opens it, adds
fav_A2, saves; ``B2`` B opens it, removes fav_A1, saves; ``A3`` A opens it; ``C`` a new computer opens it. Each prints
``FAVS <role> db=[...] qgz=[...]`` and PASS / FAIL lines.

Before (QGIS 3.44): the .qgz got fav_A1 only when A opened the project again, B never had fav_A2.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsRectangle, QgsSettings, QgsVectorFileWriter, QgsVectorLayer
from qgis.PyQt.QtCore import QTimer
from qgis.utils import iface
import qgis.utils

ROLE = os.environ["FM_ROLE"]
WORK = os.environ.get("FM_WORK", "/work")
PROJECT_PATH = os.path.join(WORK, "travel.qgz")
REPO = os.environ.get("FM_REPO", "/src")
PACKAGE = "filter_mate"
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
FAILED = []
QTimer.singleShot(5 * 60 * 1000, lambda: (print("FAIL watchdog", flush=True), os._exit(2)))
qgis.utils.showException = lambda *a, **k: print("   [Python exception]", a[1] if len(a) > 1 else a, flush=True)


def check(label, condition, detail=""):
    if not condition:
        FAILED.append(label)
    print(f"{'PASS' if condition else 'FAIL'} {ROLE} {label}" + (f" ({detail})" if detail else ""), flush=True)


def app():
    return qgis.utils.plugins[PACKAGE].app


def in_db():
    return sorted(favorite.name for favorite in app().favorites_manager.get_all_favorites())


def in_qgz():
    """The favorites the .qgz on disk carries, read by a project of its own."""
    other = QgsProject()
    if not other.read(PROJECT_PATH):
        return None
    data, _ok = other.readEntry("FilterMate", "favorites_backup", "")
    return sorted(favorite.get("name") for favorite in json.loads(data).get("favorites", [])) if data else []


EXPECTED = {  # what the SQLite of the computer and the .qgz on disk hold at the end of each role
    "A1": (["fav_A1"], ["fav_A1"]),
    "B1": (["fav_A1"], ["fav_A1"]),
    "A2": (["fav_A1", "fav_A2"], ["fav_A1", "fav_A2"]),
    "B2": (["fav_A2"], ["fav_A2"]),
    "A3": (["fav_A2"], ["fav_A2"]),
    "AY": (["fav_A2"], ["fav_A2"]),  # after the whole sequence: the project holds fav_A2
    "C": (["fav_A2"], ["fav_A2"]),
}


def report():
    db, qgz = in_db(), in_qgz()
    print(f"FAVS {ROLE} db={db} qgz={qgz}", flush=True)
    check("the favorites of this computer and of the project file", (db, qgz) == EXPECTED[ROLE],
          f"expected db={EXPECTED[ROLE][0]} qgz={EXPECTED[ROLE][1]}")


def clean_after_opening():
    """Information only: main leaves the project dirty at the opening too (FilterMate writes its project and layer
    variables then, 2026-11-24); the favorites write nothing when they did not change (unit tests)."""
    print(f"INFO {ROLE} dirty after the opening: {QgsProject.instance().isDirty()}", flush=True)


def remove(name):
    def step():
        favorite = next((f for f in app().favorites_manager.get_all_favorites() if f.name == name), None)
        check(f"{name} is removed", favorite is not None and app().favorites_manager.remove_favorite(favorite.id))
    return step


def start_plugin():
    settings = QgsSettings()
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    settings.setValue('qgis/digitizing/validate_geometries', 0)  # FilterMate asks about it otherwise
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_fav_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    check("the plugin starts", qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE))
    qgis.utils.plugins[PACKAGE].run()


def make_project():
    memory = QgsVectorLayer("Polygon?crs=EPSG:2154&field=rank:integer", "m", "memory")
    features = []
    for index in range(50):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(index * 20, 0, index * 20 + 10, 10)))
        feature.setAttributes([index])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName, options.layerName = "GPKG", "parcelles"
    path = os.path.join(WORK, "data.gpkg")
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    QgsProject.instance().addMapLayer(QgsVectorLayer(f"{path}|layername=parcelles", "parcelles", "ogr"))
    check("the project is saved for the first time", QgsProject.instance().write(PROJECT_PATH))


def open_project():
    check("the project opens", iface.addProject(PROJECT_PATH))


def add(name):
    def step():
        check(f"{name} is added", app().favorites_manager.add_favorite(
            name, f'"rank" < {len(name)}', layer_name="parcelles", layer_provider="ogr") is not None)
    return step


def ctrl_s():
    iface.actionSaveProject().trigger()
    check("Ctrl+S leaves the project saved", not QgsProject.instance().isDirty())


BEFORE_CLOSING = {}


def new_project():
    BEFORE_CLOSING["qgz"] = in_qgz()
    BEFORE_CLOSING["db"] = in_db()
    iface.newProject(False)


def add_a_layer():
    layer = QgsVectorLayer(f"{os.path.join(WORK, 'data.gpkg')}|layername=parcelles", "parcelles", "ogr")
    QgsProject.instance().addMapLayer(layer)
    print(f"INFO layer added, valid={layer.isValid()}", flush=True)


def report_closed():
    check("a favorite made in the new project stays in it, not in the project closed",
          in_db() == ["made in the new project"] and in_qgz() == BEFORE_CLOSING["qgz"],
          f"favorites={in_db()} qgz={in_qgz()} (before closing {BEFORE_CLOSING['qgz']})")


def after_new_project():
    badge = app().dockwidget.favorites_indicator_label.text()
    check("a project closed leaves no favorite of it", in_db() == [] and "1" not in badge and "2" not in badge,
          f"favorites={in_db()} badge={badge!r}")
    check("binding the new project leaves it clean", not QgsProject.instance().isDirty())


STEPS = {
    "A1": [(start_plugin, 8), (make_project, 6), (add("fav_A1"), 1), (ctrl_s, 3), (report, 0)],
    "B1": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "A2": [(start_plugin, 8), (open_project, 12), (add("fav_A2"), 1), (ctrl_s, 3), (report, 0)],
    "B2": [(start_plugin, 8), (open_project, 12), (remove("fav_A1"), 1), (ctrl_s, 3), (report, 0)],
    "A3": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "C": [(start_plugin, 8), (open_project, 12), (clean_after_opening, 0), (report, 0)],
    "AX": [(start_plugin, 8), (open_project, 12), (new_project, 6), (after_new_project, 1),
           (add_a_layer, 12), (add("made in the new project"), 1), (report_closed, 0)],
    "AY": [(start_plugin, 8), (open_project, 12), (report, 0)],
}[ROLE]


def run(index=0):
    if index == len(STEPS):
        os._exit(1 if FAILED else 0)
    function, wait = STEPS[index]
    print(f"  step {ROLE} {getattr(function, '__name__', function)}", flush=True)
    try:
        function()
    except Exception:
        traceback.print_exc()
        FAILED.append(function.__name__)
    QTimer.singleShot(int(wait * 1000), lambda: run(index + 1))


def close_modal():
    """A modal dialog left open would block the run: say which, and close it."""
    from qgis.PyQt.QtWidgets import QApplication
    modal = QApplication.activeModalWidget()
    if modal is not None:
        print(f"  modal closed: {modal.windowTitle()!r} {type(modal).__name__}", flush=True)
        modal.reject() if hasattr(modal, "reject") else modal.close()


MODALS = QTimer()
MODALS.timeout.connect(close_modal)
MODALS.start(1000)
QTimer.singleShot(2000, run)
