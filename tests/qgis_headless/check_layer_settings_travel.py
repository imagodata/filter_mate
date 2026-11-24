# -*- coding: utf-8 -*-
"""The FilterMate settings of a layer travel with the .qgz to another computer (2026-11-24).

Each computer is a QGIS profile of its own (``--profiles-path``), so FilterMate has its own SQLite there. One QGIS run
per step, ``FM_ROLE`` saying which; the user's gestures: open the project, set the layer in the panel, Ctrl+S.

    docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash /src/tests/qgis_headless/check_layer_settings_travel.sh

Roles: ``A1`` computer A makes the project (layers parcelles and routes), sets parcelles (the field shown in single
selection, a custom expression, the linking button off, routes as a layer to filter), saves; ``B1`` computer B opens
it, finds them without a question (no setting of its own), sets another field and the linking button on (EXPLORING)
and a geometric predicate (FILTERING), saves; ``A2`` A opens it (its SQLite still has its own settings): the question is asked once
(captures of the dialog in light and dark themes when ``FM_SHOTS`` names a folder), A answers FILTERING only and
"Do not ask again": A keeps its EXPLORING, takes B's FILTERING, and its Ctrl+S leaves B's EXPLORING in the .qgz; ``A3``
A opens it again: no question, the same answer; ``C`` a new computer opens it: no question, B's settings. Each prints
``SETTINGS <role> ...`` and PASS / FAIL lines.

The linking button is clicked as the user does (its ``toggled`` signal, LayerPropertyController); the other settings
go through ``set_layer_options``, which saves them as the panel does (``settingLayerVariable``).

Before (QGIS 3.44): B got the defaults (its SQLite knew nothing of the project, and the project was not read), and A
found its own settings again.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import traceback

from qgis.core import (QgsApplication, QgsFeature, QgsGeometry, QgsProject, QgsRectangle, QgsSettings,
                       QgsVectorFileWriter, QgsVectorLayer)
from qgis.PyQt.QtCore import QTimer
from qgis.utils import iface
import qgis.utils

ROLE = os.environ["FM_ROLE"]
WORK = os.environ.get("FM_WORK", "/work")
PROJECT_PATH = os.path.join(WORK, "settings.qgz")
REPO = os.environ.get("FM_REPO", "/src")
PACKAGE = "filter_mate"
EXCLUDED = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts',
            'knowledge', 'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
FAILED = []
QTimer.singleShot(5 * 60 * 1000, lambda: (print("FAIL watchdog", flush=True), os._exit(2)))
qgis.utils.showException = lambda *a, **k: print("   [Python exception]", a[1] if len(a) > 1 else a, flush=True)

KEYS = (("exploring", "single_selection_expression"), ("exploring", "custom_selection_expression"),
        ("exploring", "is_linking"), ("filtering", "has_layers_to_filter"), ("filtering", "layers_to_filter"),
        ("filtering", "has_geometric_predicates"), ("filtering", "geometric_predicates"))
SET_BY_A = {"single_selection_expression": '"nom"', "custom_selection_expression": '"rank" > 10', "is_linking": False,
            "has_layers_to_filter": True, "layers_to_filter": ["routes"], "has_geometric_predicates": False,
            "geometric_predicates": []}
SET_BY_B = dict(SET_BY_A, single_selection_expression='"rank"', is_linking=True, has_geometric_predicates=True,
                geometric_predicates=["Intersect"])
MIXED = dict(SET_BY_B, single_selection_expression='"nom"', is_linking=False)  # A's EXPLORING, B's FILTERING
LEGACY = dict(MIXED, custom_selection_expression='"rank" < 5')
# (in the panel, in the .qgz) at the end
EXPECTED = {"A1": (SET_BY_A, SET_BY_A), "B1": (SET_BY_B, SET_BY_B), "A2": (MIXED, SET_BY_B), "A3": (MIXED, SET_BY_B),
            "C": (SET_BY_B, SET_BY_B), "A4": (MIXED, MIXED), "L": (LEGACY, LEGACY)}
OPENED = {"B1": SET_BY_A, "A2": MIXED, "A3": MIXED, "C": SET_BY_B, "A4": MIXED, "L": LEGACY}  # once open (answered)
SHOTS = os.environ.get("FM_SHOTS", "")


def check(label, condition, detail=""):
    if not condition:
        FAILED.append(label)
    print(f"{'PASS' if condition else 'FAIL'} {ROLE} {label}" + (f" ({detail})" if detail else ""), flush=True)


def app():
    return qgis.utils.plugins[PACKAGE].app


def dock():
    return app().dockwidget


def layer_named(name, project=None):
    found = (project or QgsProject.instance()).mapLayersByName(name)
    return found[0] if found else None


def readable(values, project=None):
    """Layer ids by name, for the report."""
    project = project or QgsProject.instance()
    shown = dict(values)
    if isinstance(shown.get("layers_to_filter"), list):
        shown["layers_to_filter"] = [getattr(project.mapLayer(i), "name", lambda: i)() for i in shown["layers_to_filter"]]
    return shown


def in_panel():
    layer = layer_named("parcelles")
    props = app().PROJECT_LAYERS.get(layer.id()) if layer is not None else None
    if not props:
        return None
    return readable({key: props[group].get(key) for group, key in KEYS})


def stored(layer, group, key):
    value = layer.customProperty(f"variableValues/filterMate_{group}_{key}")
    if isinstance(value, str) and value.startswith("["):
        value = json.loads(value)
    return value


def in_qgz():
    """The settings the .qgz on disk carries for parcelles, read by a project of its own."""
    other = QgsProject()
    if not other.read(PROJECT_PATH):
        return None
    layer = layer_named("parcelles", other)
    return readable({key: stored(layer, group, key) for group, key in KEYS}, other)


def in_sqlite():
    """What the SQLite of this computer has for parcelles (any project), before the project is opened."""
    path = os.path.join(QgsApplication.qgisSettingsDirPath(), "FilterMate", "filterMate_db.sqlite")
    if not os.path.exists(path):
        return {}
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT layer_id, meta_key, meta_value FROM fm_project_layers_properties "
                            "WHERE meta_type = 'exploring' AND meta_key IN ('single_selection_expression', "
                            "'is_linking')").fetchall()
    return {key: value for layer_id, key, value in rows if layer_id.startswith("parcelles")}


def report_sqlite():
    print(f"INFO {ROLE} SQLite of this computer before the opening: {in_sqlite()}", flush=True)


MARKS = []  # each time FilterMate marked the project modified for a setting of a layer (settings_written)


def count_marks():
    """From now on, count what layer_settings.settings_written marks."""
    from filter_mate.infrastructure.utils import layer_settings
    original = layer_settings.settings_written

    def counted(*args, **kwargs):
        marked = original(*args, **kwargs)
        if marked:
            MARKS.append(1)
        return marked
    layer_settings.settings_written = counted


def no_marks(what):
    def step():
        check(f"nothing marked modified by the settings ({what})", not MARKS, f"{len(MARKS)} mark(s)")
        print(f"INFO {ROLE} project modified after {what}: {QgsProject.instance().isDirty()}", flush=True)
        MARKS.clear()
    step.__name__ = f"no_marks_{what.replace(' ', '_')}"
    return step


def show(name):
    def step():
        dock().current_layer_changed(layer_named(name), manual_change=True)
    step.__name__ = f"show_{name}"
    return step


def filter_parcelles():
    app().manage_task('filter')


def report_opened():
    panel = in_panel()
    print(f"SETTINGS {ROLE} opened panel={panel}", flush=True)
    check("the panel has the settings the project carries", panel == OPENED[ROLE], f"expected {OPENED[ROLE]}")


def _same(one, other):
    if isinstance(one, (bool, int, float)) and isinstance(other, (bool, int, float)):
        return float(one) == float(other)  # the SQLite gives 1 for a bool the registration wrote
    return one == other


def mirror(groups=("exploring", "filtering")):
    """What the SQLite of this computer keeps for parcelles is what its variables hold (the project saves the
    variables), for ``groups`` (a group kept at the question is this computer's in the SQLite and the others' in the
    project); what the panel holds and was not saved (no SQLite row either) is said, not checked."""
    from filter_mate.infrastructure.utils.type_utils import return_typed_value
    layer = layer_named("parcelles")
    props = app().PROJECT_LAYERS.get(layer.id())
    path = os.path.join(QgsApplication.qgisSettingsDirPath(), "FilterMate", "filterMate_db.sqlite")
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT meta_type, meta_key, meta_value FROM fm_project_layers_properties WHERE "
                            "fk_project = ? AND layer_id = ? AND meta_type IN ('exploring', 'filtering')",
                            (str(app().project_uuid), layer.id())).fetchall()
    rows = [row for row in rows if row[0] in groups]
    apart = [f"{group}.{key}: sqlite={text!r} variable={stored(layer, group, key)!r}" for group, key, text in rows
             if not _same(return_typed_value(text, 'load')[0], stored(layer, group, key))]
    check(f"the {len(rows)} settings this computer saved are in the variables of the layer", rows and not apart,
          "; ".join(apart))
    unsaved = [f"{group}.{key}: panel={value!r} variable={stored(layer, group, key)!r}"
               for group in ("exploring", "filtering") for key, value in props[group].items()
               if not _same(value, stored(layer, group, key))]
    if unsaved:
        print(f"INFO {ROLE} held by the panel only (not saved by FilterMate): {'; '.join(unsaved)}", flush=True)


def mirror_of(groups):
    def step():
        mirror(groups)
    step.__name__ = f"mirror_{'_'.join(groups)}"
    return step


def report():
    panel, qgz = in_panel(), in_qgz()
    print(f"SETTINGS {ROLE} panel={panel} qgz={qgz}", flush=True)
    check("the settings of the panel and of the project file", (panel, qgz) == EXPECTED[ROLE],
          f"expected panel={EXPECTED[ROLE][0]} qgz={EXPECTED[ROLE][1]}")


DIALOG = "FilterMateLayerSettingsDialog"


def the_question():
    from qgis.PyQt.QtWidgets import QApplication
    return next((widget for widget in QApplication.topLevelWidgets()
                 if widget.objectName() == DIALOG and widget.isVisible()), None)


def no_question():
    check("no question about the settings of the layers", the_question() is None)


def _shot(dialog, theme):
    if not SHOTS:
        return
    from qgis.PyQt.QtWidgets import QApplication
    try:
        QgsApplication.setUITheme(theme)
    except Exception as exc:  # the theme of QGIS could not be set: the capture shows the one in use
        print(f"INFO {ROLE} theme {theme} not set: {exc}", flush=True)
    for _ in range(5):
        QApplication.processEvents()
    name = "dark" if theme != "default" else "light"
    path = os.path.join(SHOTS, f"layer_settings_dialog_{os.environ.get('FM_IMAGE', 'qgis')}_{name}.png")
    check(f"the dialog is captured ({name})", dialog.grab().save(path), path)


def answer(groups, remember):
    def step():
        from qgis.PyQt.QtWidgets import QCheckBox, QPushButton
        dialog = the_question()
        check("the question is asked once for the project", dialog is not None)
        if dialog is None:
            return
        print(f"INFO {ROLE} question: {dialog.windowTitle()!r} groups="
              f"{[box.objectName() for box in dialog.findChildren(QCheckBox) if box.objectName() != 'remember']}",
              flush=True)
        _shot(dialog, "default")  # the theme in use first
        _shot(dialog, "Night Mapping")
        if SHOTS:
            QgsApplication.setUITheme("default")
        for name in ("exploring", "filtering"):
            box = dialog.findChild(QCheckBox, name)
            if box is not None:
                box.setChecked(name in groups)
        dialog.findChild(QCheckBox, "remember").setChecked(remember)
        dialog.findChild(QPushButton, "apply").click()
    step.__name__ = f"answer_{'_'.join(groups) or 'none'}{'_remembered' if remember else ''}"
    return step


def start_plugin():
    settings = QgsSettings()
    settings.setValue('FilterMate/whats_new_seen', 99)
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the run
    iface.mainWindow().resize(1600, 1000)
    iface.mainWindow().show()
    settings.setValue('qgis/digitizing/validate_geometries', 0)  # FilterMate asks about it otherwise
    plugins = os.path.join(tempfile.mkdtemp(prefix='fm_settings_'), 'plugins')
    shutil.copytree(REPO, os.path.join(plugins, PACKAGE), ignore=shutil.ignore_patterns(*EXCLUDED))
    sys.path.insert(0, plugins)
    qgis.utils.plugin_paths.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    check("the plugin starts", qgis.utils.loadPlugin(PACKAGE) and qgis.utils.startPlugin(PACKAGE))
    qgis.utils.plugins[PACKAGE].run()


def _layer_file(name, fields, attributes, geometry):
    memory = QgsVectorLayer(f"Polygon?crs=EPSG:2154&{fields}", name, "memory")
    features = []
    for index in range(30):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(geometry(index))
        feature.setAttributes(attributes(index))
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName, options.layerName = "GPKG", name
    path = os.path.join(WORK, f"{name}.gpkg")
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    return QgsVectorLayer(f"{path}|layername={name}", name, "ogr")


def make_project():
    parcelles = _layer_file("parcelles", "field=nom:string&field=rank:integer", lambda i: [f"p{i}", i],
                            lambda i: QgsGeometry.fromRect(QgsRectangle(i * 20, 0, i * 20 + 10, 10)))
    routes = _layer_file("routes", "field=code:string", lambda i: [f"r{i}"],
                         lambda i: QgsGeometry.fromRect(QgsRectangle(i * 20, 5, i * 20 + 30, 7)))
    QgsProject.instance().addMapLayers([parcelles, routes])
    check("the project is saved for the first time", QgsProject.instance().write(PROJECT_PATH))


def open_project():
    check("the project opens", iface.addProject(PROJECT_PATH))


def show_parcelles():
    dock().current_layer_changed(layer_named("parcelles"), manual_change=True)


def click_linking(checked):
    """The linking button of EXPLORING, as the user clicks it."""
    def step():
        button = dock().pushButton_checkable_exploring_linking_widgets
        print(f"INFO {ROLE} linking button before: {button.isChecked()}", flush=True)
        if button.isChecked() == checked:  # the click would turn it the other way: set it through the options
            set_options({"exploring": {"is_linking": checked}})()
        else:
            button.click()
    step.__name__ = f"click_linking_{checked}"
    return step


def set_options(change):
    def step():
        from filter_mate.adapters.public_api.panel_options import set_layer_options
        change_ids = json.loads(json.dumps(change))
        targets = change_ids.get("filtering", {}).get("layers_to_filter")
        if targets:
            change_ids["filtering"]["layers_to_filter"] = [layer_named(name).id() for name in targets]
        result = set_layer_options(dock(), [dict(layer="parcelles", **change_ids)])
        check(f"set {sorted(k for group in change.values() for k in group)}", bool(result.get("changed")), result)
    step.__name__ = "set_options"
    return step


def inject_legacy():
    """What 5.1.2 left in a saved project: a change under the legacy name beside the right one, no version mark, and
    FilterMate's names among the variables of QGIS, before one of the user."""
    other = QgsProject()
    check("the project is read without QGIS's panel", other.read(PROJECT_PATH))
    for name in ("parcelles", "routes"):
        layer_named(name, other).removeCustomProperty("filterMate/settings_version")
    layer = layer_named("parcelles", other)
    layer.setCustomProperty("variableValues/exploring_custom_selection_expression", '"rank" < 5')
    layer.setCustomProperty("variableValues/infos_layer_name", "parcelles")
    layer.setCustomProperty("variableNames", ["filterMate_exploring_is_linking", "exploring_custom_selection_expression",
                                              "my_var"])
    layer.setCustomProperty("variableValues", ["hello"])
    check("the legacy names are written into the project", other.write(PROJECT_PATH))


def the_variable_of_the_user_is_right():
    from qgis.core import QgsExpressionContextUtils
    scope = QgsExpressionContextUtils.layerScope(layer_named("parcelles"))
    check("the variable of the user has its value", scope.variable("my_var") == "hello",
          {name: scope.variable(name) for name in scope.variableNames() if not name.startswith("layer")
           and not name.startswith("_")})


def the_version_is_saved():
    other = QgsProject()
    other.read(PROJECT_PATH)
    check("the layers of the .qgz say this version wrote their settings",
          all(layer_named(name, other).customProperty("filterMate/settings_version") == 2
              for name in ("parcelles", "routes")))


def an_empty_list_survives_the_qgz():
    """routes has no layer to filter: its empty list is in the .qgz as such (not None, as a list stored as such)."""
    other = QgsProject()
    other.read(PROJECT_PATH)
    stored_value = layer_named("routes", other).customProperty("variableValues/filterMate_filtering_layers_to_filter")
    check("an empty list survives the .qgz", stored_value == "[]", repr(stored_value))


def no_legacy_left():
    other = QgsProject()
    other.read(PROJECT_PATH)
    keys = [key for key in layer_named("parcelles", other).customPropertyKeys()
            if key.startswith("variableValues/") and not key.startswith("variableValues/filterMate_")]
    check("the .qgz has no legacy name left", not keys, keys)


def dirty_after_a_change():
    """A setting changed after a save makes the project modified (QGIS then asks to save it at closing)."""
    check("a change after Ctrl+S leaves the project modified", QgsProject.instance().isDirty())


def ctrl_s():
    iface.actionSaveProject().trigger()
    check("Ctrl+S leaves the project saved", not QgsProject.instance().isDirty())


A_SETTINGS = {"exploring": {"single_selection_expression": '"nom"', "custom_selection_expression": '"rank" > 10'},
              "filtering": {"has_layers_to_filter": True, "layers_to_filter": ["routes"]}}
QUIET = [(show("routes"), 3), (show("parcelles"), 3), (filter_parcelles, 8),
         (no_marks("a change of layer and a filter"), 0)]
STEPS = {
    "A1": [(start_plugin, 8), (make_project, 10), (show_parcelles, 3), (click_linking(False), 2),
           (set_options(A_SETTINGS), 2), (mirror, 0), (ctrl_s, 3), (report, 0), (an_empty_list_survives_the_qgz, 0)],
    "B1": [(start_plugin, 8), (report_sqlite, 0), (open_project, 12), (no_question, 0), (report_opened, 0),
           (mirror, 0), (show_parcelles, 3), (set_options({"exploring": {"single_selection_expression": '"rank"'}}), 2),
           (click_linking(True), 2),
           (set_options({"filtering": {"has_geometric_predicates": True, "geometric_predicates": ["Intersect"]}}), 2),
           (mirror, 0), (ctrl_s, 3), (report, 0)],
    # A opens it: its own settings differ from the project's, the question; FILTERING only, remembered
    "A2": [(start_plugin, 8), (count_marks, 0), (report_sqlite, 0), (open_project, 12),
           (answer(["filtering"], True), 4), (report_opened, 0), (no_marks("the opening and the answer"), 0),
           (mirror_of(("filtering",)), 0), (ctrl_s, 3), (report, 0)] + QUIET,
    # A opens it again: no question, the answer remembered
    "A3": [(start_plugin, 8), (count_marks, 0), (open_project, 12), (no_question, 0), (report_opened, 0),
           (no_marks("the opening"), 0), (mirror_of(("filtering",)), 0), (report, 0)],
    "C": [(start_plugin, 8), (count_marks, 0), (open_project, 12), (no_question, 0), (report_opened, 0),
          (no_marks("the opening"), 0), (mirror, 0), (report, 0)] + QUIET,
    # A opens it once 5.1.2 wrote an older value under the legacy name: its SQLite wins, into the project, no question
    "A4": [(inject_legacy, 0), (start_plugin, 8), (open_project, 12), (no_question, 0), (report_opened, 0),
           (mirror, 0), (the_variable_of_the_user_is_right, 0), (ctrl_s, 3), (report, 0), (no_legacy_left, 0),
           (the_version_is_saved, 0)],
    # A new computer opens it: the value under the legacy name is the latest the user chose
    "L": [(inject_legacy, 0), (start_plugin, 8), (open_project, 12), (no_question, 0), (report_opened, 0), (mirror, 0),
          (the_variable_of_the_user_is_right, 0), (ctrl_s, 3), (report, 0), (no_legacy_left, 0), (show_parcelles, 3),
          (set_options({"exploring": {"custom_selection_expression": '"rank" < 6'}}), 2), (dirty_after_a_change, 0)],
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
        FAILED.append(getattr(function, '__name__', str(function)))
    QTimer.singleShot(int(wait * 1000), lambda: run(index + 1))


def close_modal():
    """A modal dialog left open would block the run: say which, and close it. The question about the settings of the
    layers is left open: the steps answer it, or say it was asked when it should not have been."""
    from qgis.PyQt.QtWidgets import QApplication
    modal = QApplication.activeModalWidget()
    if modal is not None and modal.objectName() != DIALOG:
        print(f"  modal closed: {modal.windowTitle()!r} {type(modal).__name__}", flush=True)
        modal.reject() if hasattr(modal, "reject") else modal.close()


MODALS = QTimer()
MODALS.timeout.connect(close_modal)
MODALS.start(1000)
QTimer.singleShot(2000, run)
