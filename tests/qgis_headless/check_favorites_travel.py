# -*- coding: utf-8 -*-
"""The favorites of a project travel with its .qgz to another computer (2026-11-24).

Each computer is a QGIS profile of its own (``--profiles-path``), so FilterMate has its own SQLite there. One QGIS run
per step, ``FM_ROLE`` saying which; the user's gestures: open the project, add a favorite, Ctrl+S.

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash /src/tests/qgis_headless/check_favorites_travel.sh

Roles: ``A1`` computer A makes the project, adds fav_A1, saves; ``B1`` computer B opens it; ``A2`` A opens it, adds
fav_A2, saves; ``B2`` B opens it, removes fav_A1, saves; ``A3`` A opens it; ``C`` a new computer opens it. Each prints
``FAVS <role> db=[...] qgz=[...]`` and PASS / FAIL lines.

Before (QGIS 3.44): the .qgz got fav_A1 only when A opened the project again, B never had fav_A2.

The project closed (2026-11-24): ``AX`` a new project, a favorite made there; ``AY`` the first project reopened
without it; ``AD`` a copy of the project opened with the panel closed, the panel opened again, a favorite added;
``AC`` Project > Close, a layer added, a favorite made; ``AT`` a new project from a template with layers (the .sh puts
the template in the profile; skipped where QGIS lists no template: QGIS 4.3 lists none headless); ``AF`` a project
that fails to read, a layer added, a favorite made; ``AZ`` the project opened at the end: none of those favorites in it.

Audit of 2026-11-24 (lot 1): ``AC2`` a copy of the project opened then closed without saving, reopened (the next sync
used to fail on UNIQUE constraint failed: fm_favorites.id and never healed), a favorite added, saved; ``AF5`` a favorite
added but not saved, F5 (the project is bound again), closed without saving, reopened (the favorite used to be
dropped as 'removed elsewhere').
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
from qgis.PyQt.QtWidgets import QAction, QMenu
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


def in_qgz(path=PROJECT_PATH):
    """The favorites the .qgz on disk carries, read by a project of its own."""
    other = QgsProject()
    if not other.read(path):
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
    "AZ": (["fav_A2"], ["fav_A2"]),  # after the roles of the project closed: none of their favorites
    "C": (["fav_A2"], ["fav_A2"]),
}


def report():
    db, qgz = in_db(), in_qgz()
    print(f"FAVS {ROLE} db={db} qgz={qgz}", flush=True)
    check("the favorites of this computer and of the project file", (db, qgz) == EXPECTED[ROLE],
          f"expected db={EXPECTED[ROLE][0]} qgz={EXPECTED[ROLE][1]}")


def clean_after_opening():
    """Information only: False since FilterMate no longer writes its id into a project with a file (True before,
    2026-11-24); the favorites write nothing when they did not change (unit tests)."""
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


def new_project_again():
    BEFORE_CLOSING["uuid"] = app().project_uuid
    iface.newProject(False)


def another_id_for_the_next_new_project():
    """2026-11-24 (review): every new project was bound to the most recent unsaved row, so the next one listed the
    favorite made in the first."""
    check("the next new project has an id of its own and none of the favorites of the one before",
          app().project_uuid not in (None, BEFORE_CLOSING["uuid"]) and in_db() == [],
          f"uuid={app().project_uuid} before={BEFORE_CLOSING['uuid']} favorites={in_db()}")


def after_new_project():
    badge = app().dockwidget.favorites_indicator_label.text()
    check("a project closed leaves no favorite of it", in_db() == [] and "1" not in badge and "2" not in badge,
          f"favorites={in_db()} badge={badge!r}")
    check("binding the new project leaves it clean", not QgsProject.instance().isDirty())


def plugin():
    return qgis.utils.plugins[PACKAGE]


def of_the_project_in_the_sqlite():
    """The favorites this computer's SQLite holds for travel.qgz, whatever FilterMate is bound to."""
    import sqlite3
    conn = sqlite3.connect(app().db_file_path)
    try:
        return sorted(row[0] for row in conn.execute(
            "SELECT f.name FROM fm_favorites f JOIN fm_projects p ON f.project_uuid = p.project_id "
            "WHERE p.project_name = 'travel.qgz'"))
    finally:
        conn.close()


def badge():
    return app().dockwidget.favorites_indicator_label.text()


DOCK_COPY = os.path.join(WORK, "dock.qgz")


def close_dock():
    shutil.copy(PROJECT_PATH, DOCK_COPY)
    app().dockwidget.close()
    check("the panel is closed", not plugin().pluginIsActive)


def open_copy():
    check("the copy opens with the panel closed", iface.addProject(DOCK_COPY))


def bound_with_the_panel_closed():
    check("the project opened with the panel closed is bound", in_db() == ["fav_A2"] and app().favorites_manager.is_bound,
          f"favorites={in_db()} uuid={app().project_uuid}")


def reopen_dock():
    plugin().run()


def listed_when_the_panel_opens_again():
    check("its favorites are listed when the panel opens again", in_db() == ["fav_A2"] and "1" in badge(),
          f"favorites={in_db()} badge={badge()!r}")


def save_copy():
    iface.actionSaveProject().trigger()
    check("a favorite added lands in the project opened with the panel closed",
          in_qgz(DOCK_COPY) == ["fav_A2", "made with the panel reopened"] and in_qgz() == ["fav_A2"]
          and of_the_project_in_the_sqlite() == ["fav_A2"],
          f"copy={in_qgz(DOCK_COPY)} project={in_qgz()} sqlite of the project={of_the_project_in_the_sqlite()}")


def close_project():
    BEFORE_CLOSING["uuid"] = app().project_uuid
    iface.mainWindow().findChild(QAction, "mActionCloseProject").trigger()


def after_closing():
    check("Project > Close leaves no favorite of the project", in_db() == [] and "1" not in badge(),
          f"favorites={in_db()} badge={badge()!r} uuid={app().project_uuid}")


def report_after_closing():
    check("a favorite made after Project > Close and a layer added is not the closed project's",
          in_db() == ["made after closing"] and app().project_uuid not in (None, BEFORE_CLOSING["uuid"])
          and in_qgz() == ["fav_A2"] and of_the_project_in_the_sqlite() == ["fav_A2"],
          f"favorites={in_db()} uuid={app().project_uuid} qgz={in_qgz()} sqlite={of_the_project_in_the_sqlite()}")


TEMPLATE = {}


def from_template():
    BEFORE_CLOSING["uuid"] = app().project_uuid
    menu = iface.mainWindow().findChild(QMenu, "mProjectFromTemplateMenu")
    if menu is not None:
        menu.aboutToShow.emit()  # QGIS 4 may list the templates when the menu opens
    actions = [action for action in (menu.actions() if menu is not None else []) if action.text().startswith("travel")]
    TEMPLATE["listed"] = bool(actions)
    if not actions:
        print(f"INFO {ROLE} no template listed by this QGIS (menu={menu is not None}): role skipped", flush=True)
        return
    actions[0].trigger()


def after_template():
    if not TEMPLATE["listed"]:
        return
    check("a new project from a template has no file", QgsProject.instance().fileName() == "",
          QgsProject.instance().fileName())
    check("it has an id of its own, not the template project's",
          app().project_uuid not in (None, BEFORE_CLOSING["uuid"]), f"uuid={app().project_uuid}")
    check("it starts with the template's favorites", in_db() == ["fav_A2"], f"favorites={in_db()}")
    print(f"INFO {ROLE} dirty after the template: {QgsProject.instance().isDirty()}", flush=True)


def report_template():
    if not TEMPLATE["listed"]:
        return
    check("a favorite made from the template is not the template project's",
          in_db() == ["fav_A2", "made from the template"] and of_the_project_in_the_sqlite() == ["fav_A2"]
          and in_qgz() == ["fav_A2"], f"favorites={in_db()} sqlite={of_the_project_in_the_sqlite()} qgz={in_qgz()}")


def add_if_template(name):
    step = add(name)

    def maybe():
        if TEMPLATE["listed"]:
            step()
    maybe.__name__ = f"add_{name.replace(' ', '_')}"
    return maybe


COPY2 = os.path.join(WORK, "copy2.qgz")


def open_copy_unsaved():
    """Audit of 2026-11-24 #1: a copy of the project (Save As), opened then closed without saving."""
    shutil.copy(PROJECT_PATH, COPY2)
    check("the copy opens", iface.addProject(COPY2))
    check("the copy lists the favorites", in_db() == ["fav_A2"], f"favorites={in_db()}")


def close_without_saving():
    iface.newProject(False)  # no prompt: the changes not saved are dropped


def reopen_copy():
    check("the copy reopens", iface.addProject(COPY2))


def report_copy_reopened():
    db, qgz = in_db(), in_qgz(COPY2)
    print(f"FAVS {ROLE} db={db} qgz={qgz}", flush=True)
    check("a copy closed without saving syncs cleanly at the next opening", db == ["fav_A2"], f"db={db}")
    check("the copy on disk still carries the original ids", qgz == ["fav_A2"], f"qgz={qgz}")


def report_copy_saved():
    db, copy, qgz = in_db(), in_qgz(COPY2), in_qgz()
    print(f"FAVS {ROLE} db={db} copy={copy} qgz={qgz}", flush=True)
    check("a favorite added after the healing lands in the copy",
          db == ["fav_A2", "made in the copy"] and copy == ["fav_A2", "made in the copy"], f"db={db} copy={copy}")
    check("the original project is untouched", qgz == ["fav_A2"], f"qgz={qgz}")


def reload_layers():
    """Audit of 2026-11-24 #2: F5 binds the project again (the sync must not take the mirrored-but-unsaved
    favorites for the file's)."""
    app().force_reload_layers()
    print(f"INFO {ROLE} layers reloaded, favorites={in_db()}", flush=True)


def report_after_f5():
    db, qgz = in_db(), in_qgz()
    print(f"FAVS {ROLE} db={db} qgz={qgz}", flush=True)
    check("an unsaved favorite survives F5 and a close without saving",
          db == ["fav_A2", "made before F5"] and qgz == ["fav_A2"], f"db={db} qgz={qgz}")


BROKEN = os.path.join(WORK, "broken.qgs")  # a .qgz that fails to unzip takes another path in QGIS


def open_broken():
    BEFORE_CLOSING["uuid"] = app().project_uuid
    with open(BROKEN, "w") as handle:
        handle.write("not a project")
    check("a project that fails to read is refused", not iface.addProject(BROKEN))


def after_broken():
    print(f"INFO {ROLE} after the failed read: file={QgsProject.instance().fileName()!r} uuid={app().project_uuid}",
          flush=True)
    check("a project that failed to read shows no favorite of the project before", in_db() == [],
          f"favorites={in_db()}")


def bound_by_the_layer_added():
    """No signal of a project follows a failed read: the registration of the layer binds the project (add_layers)."""
    check("a layer added after a failed read binds the project on screen", app().project_uuid is not None
          and app().project_uuid != BEFORE_CLOSING["uuid"], f"uuid={app().project_uuid}")


def report_broken():
    check("a favorite made after a failed read is not the project before's",
          in_db() == ["made after a failed read"] and app().project_uuid not in (None, BEFORE_CLOSING["uuid"])
          and of_the_project_in_the_sqlite() == ["fav_A2"] and in_qgz() == ["fav_A2"],
          f"favorites={in_db()} uuid={app().project_uuid} sqlite={of_the_project_in_the_sqlite()} qgz={in_qgz()}")


STEPS = {
    "A1": [(start_plugin, 8), (make_project, 6), (add("fav_A1"), 1), (ctrl_s, 3), (report, 0)],
    "B1": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "A2": [(start_plugin, 8), (open_project, 12), (add("fav_A2"), 1), (ctrl_s, 3), (report, 0)],
    "B2": [(start_plugin, 8), (open_project, 12), (remove("fav_A1"), 1), (ctrl_s, 3), (report, 0)],
    "A3": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "C": [(start_plugin, 8), (open_project, 12), (clean_after_opening, 0), (report, 0)],
    "AX": [(start_plugin, 8), (open_project, 12), (new_project, 6), (after_new_project, 1),
           (add_a_layer, 12), (add("made in the new project"), 1), (report_closed, 0), (new_project_again, 6),
           (another_id_for_the_next_new_project, 0)],
    "AY": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "AD": [(start_plugin, 8), (close_dock, 2), (open_copy, 12), (bound_with_the_panel_closed, 0), (reopen_dock, 6),
           (listed_when_the_panel_opens_again, 0), (add("made with the panel reopened"), 1), (save_copy, 3)],
    "AC": [(start_plugin, 8), (open_project, 12), (close_project, 6), (after_closing, 0), (add_a_layer, 12),
           (add("made after closing"), 1), (report_after_closing, 0)],
    "AT": [(start_plugin, 8), (open_project, 12), (from_template, 12), (after_template, 0),
           (add_if_template("made from the template"), 1), (report_template, 0)],
    "AF": [(start_plugin, 8), (open_project, 12), (open_broken, 6), (after_broken, 0), (add_a_layer, 12),
           (bound_by_the_layer_added, 0), (add("made after a failed read"), 1), (report_broken, 0)],
    "AZ": [(start_plugin, 8), (open_project, 12), (report, 0)],
    "AC2": [(start_plugin, 8), (open_copy_unsaved, 12), (close_without_saving, 6), (reopen_copy, 12),
            (report_copy_reopened, 0), (add("made in the copy"), 1), (ctrl_s, 3), (report_copy_saved, 0)],
    "AF5": [(start_plugin, 8), (open_project, 12), (add("made before F5"), 1), (reload_layers, 12),
            (close_without_saving, 6), (open_project, 12), (report_after_f5, 0)],
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
