#!/usr/bin/env python3
"""The history of the project (ui/controllers/history_controller.py) in a real QGIS, on a dock made for the check.

The three histories listed newest first (a vector filter of the dock, a raster operation, a turn of the agent and its
steps, a filter undone), what Undo and Redo would take marked as the action bar chooses its history, the list kept
up to date while open, the map before a step compared (the image left of the line is the map of then) and pinned,
the tooltips of Undo and Redo.

    docker run --rm --init --network none -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_history_timeline.py
"""
import dataclasses
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer

APP = QgsApplication([], True)
APP.initQgis()

from qgis.gui import QgsMapCanvas, QgsMapToolPan  # noqa: E402
from qgis.PyQt.QtCore import QEvent, QPoint, QSize, pyqtSignal  # noqa: E402
from qgis.PyQt.QtGui import QColor, QContextMenuEvent, QImage, QPainter  # noqa: E402
from qgis.PyQt.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("FM_REPO") or HERE.parents[1])
sys.path.insert(0, str(HERE))


def _link_dir(target, source):
    """``target`` made a link to the folder ``source``: a symlink, or a junction on Windows (no privilege needed)."""
    try:
        target.symlink_to(source, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(source)], check=True, capture_output=True)


packages = Path(tempfile.mkdtemp(prefix="fm-history-"))
_link_dir(packages / "filter_mate", ROOT)
sys.path.insert(0, str(packages))

import make_fixtures  # noqa: E402

FAILURES = []
SIZE = QSize(800, 600)
RED, BLUE = QColor(220, 40, 40), QColor(40, 40, 220)
EAST = "\"name\" LIKE 'east%'"
EAST_A = "\"name\" = 'east_a'"


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f" -- {detail}" if not condition and detail else ""), flush=True)
    if not condition:
        FAILURES.append(name)


def wait(condition, seconds=10.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        QgsApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def grab(canvas):
    image = QImage(canvas.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    canvas.render(painter)
    painter.end()
    return image


def count(image, colour, box=None):
    """Sampled pixels near ``colour`` (the fill of the squares), in ``box`` (x0, y0, x1, y1) or the whole image."""
    x0, y0, x1, y1 = box or (10, 10, image.width() - 10, image.height() - 10)
    found = 0
    for y in range(int(y0), int(y1), 6):
        for x in range(int(x0), int(x1), 6):
            pixel = image.pixelColor(x, y)
            if (abs(pixel.red() - colour.red()) < 30 and abs(pixel.green() - colour.green()) < 30
                    and abs(pixel.blue() - colour.blue()) < 30):
                found += 1
    return found


def grey(image, box):
    """Sampled pixels of ``box`` drawn by the DEM (neither white nor coloured)."""
    x0, y0, x1, y1 = box
    found = 0
    for y in range(int(y0), int(y1), 4):
        for x in range(int(x0), int(x1), 4):
            pixel = image.pixelColor(x, y)
            if pixel.rgb() != QColor("white").rgb() and abs(pixel.red() - pixel.blue()) < 12:
                found += 1
    return found


def east_half(source, target):
    """A copy of the DEM with its west half in NoData: the DEM clipped, as a raster operation leaves it."""
    from osgeo import gdal
    dataset = gdal.Translate(target, source)
    band = dataset.GetRasterBand(1)
    values = band.ReadAsArray()
    values[:, :values.shape[1] // 2] = band.GetNoDataValue()
    band.WriteArray(values)
    dataset = None
    return target


def recolour(layer, colour):
    layer.renderer().symbol().setColor(colour)
    layer.triggerRepaint()
    layer.emitStyleChanged()


def drawn(canvas):
    done = []

    def on_drawn():
        done.append(True)
    canvas.mapCanvasRefreshed.connect(on_drawn)
    canvas.refresh()
    ok = wait(lambda: bool(done) and not canvas.isDrawing(), 15)
    canvas.mapCanvasRefreshed.disconnect(on_drawn)
    return ok


class Dock(QWidget):
    """The part of the dock the history needs: the action bar, the canvas, the current layer, the app."""

    undoRedoStateRequested = pyqtSignal()
    currentLayerChanged = pyqtSignal()

    def __init__(self, canvas, history, layer):
        super().__init__()
        layout = QHBoxLayout(self)
        for name in ("pushButton_action_filter", "pushButton_action_undo_filter", "pushButton_action_redo_filter"):
            button = QPushButton(name[19:], self)
            setattr(self, name, button)
            layout.addWidget(button)
        self.pushButton_checkable_filtering_layers_to_filter = QPushButton("targets", self)
        self.pushButton_checkable_filtering_layers_to_filter.setCheckable(True)
        self.iface = SimpleNamespace(mapCanvas=lambda: canvas)
        self.current_layer = layer
        self.PROJECT_LAYERS = {layer.id(): {}}
        self.tabTools_current_index = 0
        self.filter_mate_app = SimpleNamespace(history_manager=history, _undo_redo_handler=object())
        self.agent_open = False
        self._agent_chat = SimpleNamespace(undo_state=lambda: {"can_undo": True, "can_redo": False})

    def agent_has_focus(self):
        return self.agent_open

    def get_layers_to_filter(self):
        return []


def main():
    from filter_mate.adapters.agent.turn_checkpoint import HISTORY_KEY
    from filter_mate.adapters.agent.turn_effects import _style
    from filter_mate.adapters.public_api.operations import _api_service
    from filter_mate.core.domain.filter_state import CrossOperation, LayerSnapshot
    from filter_mate.core.domain.history_timeline import KIND_AGENT, KIND_COVERAGE, KIND_STEP, KIND_VECTOR
    from filter_mate.core.services.cross_filter_service import get_cross_filter_service
    from filter_mate.core.services.history_service import HistoryEntry, HistoryService
    from filter_mate.ui.controllers.compare_controller import CompareController
    from filter_mate.ui.controllers.history_controller import COLUMN_MARK, COLUMN_WHAT, HistoryController

    project = QgsProject.instance()
    folder = tempfile.mkdtemp()
    fixtures = make_fixtures.make_all(folder)
    zones = QgsVectorLayer(fixtures["zones"] + "|layername=zones", "zones", "ogr")
    dem = QgsRasterLayer(fixtures["dem"], "dem", "gdal")
    project.addMapLayers([zones, dem])
    canvas = QgsMapCanvas()
    canvas.resize(SIZE)
    canvas.setDestinationCrs(zones.crs())
    canvas.setCanvasColor(QColor("white"))
    canvas.setLayers([zones, dem])
    canvas.setExtent(dem.extent())
    canvas.show()
    canvas.setMapTool(QgsMapToolPan(canvas))

    # 10:00 a vector filter of the dock: every square -> those of the east.
    history = HistoryService()

    def entry(seconds, expression, previous, description):
        made = HistoryEntry.create(expression, [zones.id()], [(zones.id(), previous)], description)
        return dataclasses.replace(made, timestamp=datetime.fromtimestamp(seconds))
    base = time.time() - 3600
    recolour(zones, RED)
    red = _style(zones)
    zones.setSubsetString(EAST)
    history.push(entry(base, EAST, "", "East squares"))
    # 10:10 a raster operation: the DEM clipped to its east half.
    clipped = east_half(fixtures["dem"], os.path.join(folder, "dem_east.tif"))
    dem_before = LayerSnapshot(dem.id(), "raster", source=dem.source(), provider="gdal")
    dem.setDataSource(clipped, "dem", "gdal")
    dem_after = LayerSnapshot(dem.id(), "raster", source=dem.source(), provider="gdal")
    coverage = get_cross_filter_service().history
    coverage.push(CrossOperation(dem.id(), ((dem_before, dem_after),), description="Clip the DEM",
                                 timestamp=base + 600))
    # 10:20 a turn of the agent in two steps: zones blue, then east_a alone.
    recolour(zones, BLUE)
    blue = _style(zones)
    east_snapshot = LayerSnapshot(zones.id(), "vector", subset=EAST)
    zones.setSubsetString(EAST_A)
    style = ("style", zones.id(), red, blue, "zones")
    _api_service().history.push(CrossOperation(
        HISTORY_KEY, ((east_snapshot, LayerSnapshot(zones.id(), "vector", subset=EAST_A)),),
        description="Blue squares, east_a alone", timestamp=base + 1200,
        steps=(("Paint the squares blue", ()), ("Keep east_a", (east_snapshot,))),
        step_effects=((style,), ()), effects=(style,), started=base + 1100, step_times=(base + 1100, base + 1150)))
    # 10:30 a vector filter undone: never on the map.
    history.push(entry(base + 1800, "\"name\" = 'west_a'", EAST_A, "West square"))
    history.undo()
    drawn(canvas)
    now = grab(canvas)
    to_screen = canvas.getCoordinateTransform()
    corner, far = to_screen.transform(700250, 6599350), to_screen.transform(700400, 6599050)
    west = (corner.x(), corner.y(), far.x(), far.y())  # a part of the west of the DEM without squares
    check("the map now: blue east_a, the DEM clipped", count(now, BLUE) > 0 and count(now, RED) == 0
          and grey(now, west) == 0, (count(now, BLUE), count(now, RED), grey(now, west)))

    dock = Dock(canvas, history, zones)
    dock.pushButton_action_undo_filter.setToolTip("Undo the last filter")  # what the .ui says
    dock.pushButton_action_redo_filter.setToolTip("Redo the last filter")
    dock.show()
    integration = SimpleNamespace(coverage_controller=SimpleNamespace(
        active_layer=None, service=get_cross_filter_service(), _linked_runs={}, _linked_redo={},
        _run_is_next=lambda run, operation: False))
    compare = CompareController(dock, integration)
    controller = HistoryController(dock, integration, compare)
    said = []
    compare._say = controller._say = said.append
    undo, redo = dock.pushButton_action_undo_filter, dock.pushButton_action_redo_filter

    # The three histories in one list, newest first, the steps under their turn.
    items = controller.read()
    check("three histories, newest first, the steps under their turn",
          [(item.kind, item.label, item.applied) for item in items] == [
              (KIND_VECTOR, "West square", False), (KIND_AGENT, "Blue squares, east_a alone", True),
              (KIND_STEP, "Paint the squares blue", True), (KIND_STEP, "Keep east_a", True),
              (KIND_COVERAGE, "Clip the DEM", True), (KIND_VECTOR, "East squares", True)],
          [(item.kind, item.label, item.applied) for item in items])

    # Right-click on Undo, disabled: the panel all the same, never modal.
    undo.setEnabled(False)
    QApplication.sendEvent(undo, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(4, 4),
                                                   undo.mapToGlobal(QPoint(4, 4))))
    QgsApplication.processEvents()
    panel = controller.panel
    check("right-click on Undo, disabled: the panel opens", panel is not None and panel.isVisible())
    tree = panel.tree
    rows = [tree.topLevelItem(index) for index in range(tree.topLevelItemCount())]
    texts = [row.text(COLUMN_WHAT) for row in rows]
    marks = {row.text(COLUMN_WHAT): row.text(COLUMN_MARK) for row in rows}
    check("the panel lists the four, newest first", texts == [
        "West square", "Blue squares, east_a alone", "Clip the DEM", "East squares"], texts)
    check("the steps of the turn are under it", rows[1].childCount() == 2
          and [rows[1].child(i).text(COLUMN_WHAT) for i in range(2)] == ["Paint the squares blue", "Keep east_a"])
    check("Undo and Redo of the vector filters marked", marks == {
        "West square": "Redo", "Blue squares, east_a alone": "", "Clip the DEM": "", "East squares": "Undo"}, marks)
    check("a filter undone in italics", rows[0].font(COLUMN_WHAT).italic() and not rows[3].font(COLUMN_WHAT).italic()
          and rows[3].font(COLUMN_WHAT).bold())
    check("the header counts what can be undone and redone", panel.counts.text() == "3 to undo · 1 to redo",
          panel.counts.text())
    check("the step Undo would undo is selected, Compare and Pin available",
          panel.selected() is not None and panel.selected().label == "East squares"
          and panel.compare_button.isEnabled() and panel.pin_button.isEnabled())
    tree.setCurrentItem(rows[0])
    check("a filter undone: neither Compare nor Pin", not panel.compare_button.isEnabled()
          and not panel.pin_button.isEnabled() and panel.note.isVisible())

    # The history Undo reads, chosen as the action bar chooses it.
    dock.agent_open = True
    controller.refresh()
    marks = {tree.topLevelItem(i).text(COLUMN_WHAT): tree.topLevelItem(i).text(COLUMN_MARK)
             for i in range(tree.topLevelItemCount())}
    check("AGENT open: the turn of the agent is what Undo takes", marks["Blue squares, east_a alone"] == "Undo"
          and marks["East squares"] == "" and marks["West square"] == "", marks)
    dock.agent_open = False
    integration.coverage_controller.active_layer = dem
    controller.refresh()
    marks = {tree.topLevelItem(i).text(COLUMN_WHAT): tree.topLevelItem(i).text(COLUMN_MARK)
             for i in range(tree.topLevelItemCount())}
    check("a raster current: its operation is what Undo takes", marks["Clip the DEM"] == "Undo"
          and marks["East squares"] == "", marks)
    integration.coverage_controller.active_layer = None
    controller.refresh()

    def compare_at(label):
        """Select the item ``label``, compare: the map left of the line everywhere, then right of it."""
        controller.open(undo)
        for index in range(controller.panel.tree.topLevelItemCount()):
            row = controller.panel.tree.topLevelItem(index)
            for found in [row] + [row.child(i) for i in range(row.childCount())]:
                if found.text(COLUMN_WHAT) == label:
                    controller.panel.tree.setCurrentItem(found)
        said.clear()
        renders = compare.session.renders if compare.session is not None else 0
        count_drawn = controller.compare_selected()
        session = compare.session
        ok = count_drawn > 0 and wait(lambda: session.renders > renders and not session.item.busy, 15)
        if not ok:
            return False, now, now, ()
        session.item.set_fraction(1.0)
        QgsApplication.processEvents()
        left = grab(canvas)
        session.item.set_fraction(0.0)
        QgsApplication.processEvents()
        right = grab(canvas)
        labels = session.item.labels
        if os.environ.get("FM_HISTORY_OUT"):
            left.save(os.path.join(os.environ["FM_HISTORY_OUT"], f"before_{label[:12]}.png"))
        compare.stop()
        return ok, left, right, labels

    ok, left, right, labels = compare_at("East squares")
    check("compare before the old vector filter: every square red, the DEM whole", ok and count(left, RED)
          > count(now, BLUE) and count(left, BLUE) == 0 and grey(left, west) > 0
          and labels == ("Before: East squares", "Now") and not controller.panel.isVisible(),
          (ok, count(left, RED), count(left, BLUE), grey(left, west), labels))
    check("compare: right of the line, the map now", abs(count(right, BLUE) - count(now, BLUE)) <= 2
          and count(right, RED) == 0 and grey(right, west) == 0, (count(right, BLUE), count(right, RED)))
    every_square = count(left, RED)
    ok, left, right, labels = compare_at("Clip the DEM")
    check("compare before the raster operation: the DEM whole, the east squares red", ok and grey(left, west) > 0
          and 0 < count(left, RED) < every_square and count(left, BLUE) == 0,
          (ok, grey(left, west), count(left, RED), every_square))
    east_red = count(left, RED)
    ok, left, right, labels = compare_at("Blue squares, east_a alone")
    check("compare before the turn of the agent: its style and filter undone, the DEM still clipped",
          ok and abs(count(left, RED) - east_red) <= 2 and count(left, BLUE) == 0 and grey(left, west) == 0,
          (ok, count(left, RED), east_red, count(left, BLUE), grey(left, west)))
    ok, left, right, labels = compare_at("Keep east_a")
    check("compare before a step of the agent: the east squares, blue as the first step left them",
          ok and count(left, BLUE) > count(now, BLUE) and count(left, RED) == 0
          and labels[0] == "Before: Keep east_a", (ok, count(left, BLUE), count(now, BLUE), count(left, RED), labels))

    # Pin the map before the raster operation: the map now, the DEM and the squares as they were then.
    controller.open(undo)
    controller.panel.tree.setCurrentItem(controller.panel.tree.topLevelItem(2))
    said.clear()
    state = controller.pin_selected()
    check("pin the map before a step: pinned at its time, said", state is not None and compare.pinned is state
          and abs(state.taken_at - (base + 600)) < 1 and said == [
              "The map before this step is pinned: Compare shows it left of the line."], said)
    compare.button.click()
    session = compare.session
    rendered = wait(lambda: session.active and session.renders > 0 and not session.item.busy, 15)
    session.item.set_fraction(1.0)
    QgsApplication.processEvents()
    left = grab(canvas)
    check("the pin compared: the DEM whole and the east squares red left of the line",
          rendered and grey(left, west) > 0 and abs(count(left, RED) - east_red) <= 2 and count(left, BLUE) == 0
          and session.item.labels[0].startswith("Pinned "), (rendered, grey(left, west), count(left, RED),
                                                             session.item.labels))
    compare.button.click()
    compare.unpin()
    controller.open(undo)
    turn_row = controller.panel.tree.topLevelItem(1)
    controller.panel.tree.setCurrentItem(turn_row.child(1))  # Keep east_a
    state = controller.pin_selected()
    check("pin the map before a step of the agent: pinned when that step began", state is not None
          and abs(state.taken_at - (base + 1150)) < 1, state.taken_at if state is not None else None)
    compare.unpin()
    from filter_mate.core.domain.compare_states import BeforeMap
    check("a pin of no known time: no hour shown, never 01:00", compare._labels(BeforeMap(pinned_at=0.0))
          == ("Pinned", "Now"))

    # The tooltips of Undo and Redo say what they would do, in which history.
    undo.setEnabled(True)
    redo.setEnabled(True)
    controller.schedule_refresh()
    wait(lambda: "East squares" in undo.toolTip(), 2)
    check("Undo names the vector filter, its history, how far, the right-click", undo.toolTip().split("\n") == [
        "Undo: East squares", "History: vector filters of the dock", "Steps to undo: 1",
        "Right-click: the history of the project"], undo.toolTip())
    check("Redo names the filter undone", redo.toolTip().startswith("Redo: West square\n"), redo.toolTip())
    integration.coverage_controller.active_layer = dem
    controller.refresh()
    check("a raster current: Undo names its operation and its history", undo.toolTip().startswith(
        "Undo: Clip the DEM\nHistory: raster / point cloud filters of dem\nSteps to undo: 1"), undo.toolTip())
    integration.coverage_controller.active_layer = None
    dock.agent_open = True
    controller.refresh()
    check("AGENT open: Undo names the turn", undo.toolTip().startswith(
        "Undo: Blue squares, east_a alone\nHistory: turns of the agent"), undo.toolTip())
    dock.agent_open = False
    dock.setEnabled(False)  # the dock off for a moment (a task): the buttons with it, their next step all the same
    controller.refresh()
    dock.setEnabled(True)
    check("the dock off for a moment: Undo and Redo still say what they would do",
          undo.toolTip().startswith("Undo: East squares\n") and redo.toolTip().startswith("Redo: West square\n"),
          (undo.toolTip(), redo.toolTip()))
    dock.tabTools_current_index = 1  # another section open: Undo and Redo walk nothing
    controller.refresh()
    dock.tabTools_current_index = 0
    check("another section open: nothing to do", redo.toolTip().split("\n") == [
        "Nothing to redo.", "Right-click: the history of the project"], redo.toolTip())
    controller.refresh()

    # Open, the list follows the history: a filter done, the dock asks for the state of Undo / Redo.
    controller.open(redo)
    history.push(entry(time.time(), "\"name\" = 'east_b'", EAST_A, "East b"))
    dock.undoRedoStateRequested.emit()
    QgsApplication.processEvents()
    tree = controller.panel.tree
    check("open, a new filter is listed first, Undo would take it", tree.topLevelItem(0).text(COLUMN_WHAT) == "East b"
          and tree.topLevelItem(0).text(COLUMN_MARK) == "Undo" and controller.panel.counts.text() == "4 to undo · 0 to redo",
          (tree.topLevelItem(0).text(COLUMN_WHAT), controller.panel.counts.text()))

    # A step that changed nothing the map can draw (a note of the agent): nothing compared, said.
    _api_service().history.push(CrossOperation(HISTORY_KEY, (), description="Take a note", effects=(
        ("notes", "", [], ["a note"]),)))
    controller.refresh()
    tree.setCurrentItem(tree.topLevelItem(0))
    said.clear()
    check("compare before a step with nothing to draw: off, said", tree.topLevelItem(0).text(COLUMN_WHAT)
          == "Take a note" and controller.compare_selected() == 0 and not compare.button.isChecked()
          and said == ["Nothing to compare: nothing this step changed can be drawn."], said)

    # A vector filter and the raster operation it ran with (recorded first: its task ended first): one step.
    clip_with = CrossOperation(zones.id(), ((dem_before, dem_after),), description="cross filter from zones",
                               timestamp=time.time())
    coverage.push(clip_with)
    history.push(entry(time.time() + 5, "\"name\" = 'east_a'", "\"name\" = 'east_b'", "East a again"))
    integration.coverage_controller._linked_runs = {zones.id(): [SimpleNamespace(op_id=clip_with.op_id)]}
    items = controller.read()
    by_label = {item.label: item for item in items}
    from filter_mate.core.domain.history_timeline import map_before
    before = map_before(items, by_label["East a again"])
    check("a vector filter and its raster operation: one step, the map before undoes both",
          by_label["cross filter from zones"].time == by_label["East a again"].time
          and {state.layer_id: (state.subset, state.source) for state in before.states}
          == {zones.id(): ("\"name\" = 'east_b'", ""), dem.id(): ("", fixtures["dem"])},
          [(state.layer_id, state.subset, state.source) for state in before.states])
    integration.coverage_controller._linked_runs = {}

    # Open, a refill keeps the look and the place of the list.
    controller.open(undo)
    restyled = []
    controller.panel.setStyleSheet = lambda sheet: restyled.append(sheet)
    controller.refresh()
    check("a refill while open does not set the look again", not restyled and controller.panel.isVisible())
    del controller.panel.setStyleSheet
    controller.close_panel()

    # From the menu of Compare.
    texts = [action.text() for action in compare.menu.actions()]
    check("Compare: History… in its menu", texts == ["Pin the current state", "Remove the pin", "", "History…"], texts)
    controller.history_action.trigger()
    check("History… opens the panel", controller.panel.isVisible())
    controller.close_panel()

    # Torn down: no right-click, no entry in the menu.
    controller.teardown()
    QApplication.sendEvent(undo, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(4, 4),
                                                   undo.mapToGlobal(QPoint(4, 4))))
    QgsApplication.processEvents()
    check("torn down: no panel, no entry left in the menu of Compare", not controller.panel.isVisible()
          and [action.text() for action in compare.menu.actions()] == ["Pin the current state", "Remove the pin"])
    check("torn down: the tooltips of the .ui again", undo.toolTip() == "Undo the last filter"
          and redo.toolTip() == "Redo the last filter", (undo.toolTip(), redo.toolTip()))

    # A setup that fails half way leaves nothing behind: no event filter on the buttons, no entry in the menu.
    class Refusing:
        def connect(self, slot):
            raise RuntimeError("refused")
    broken = Dock(canvas, history, zones)
    broken_compare = CompareController(broken, integration)
    broken.currentLayerChanged = Refusing()  # connected after the event filters and the menu entry
    try:
        HistoryController(broken, integration, broken_compare)
        raised = False
    except RuntimeError:
        raised = True
    button = broken.pushButton_action_undo_filter
    QApplication.sendEvent(button, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(4, 4),
                                                     button.mapToGlobal(QPoint(4, 4))))
    QgsApplication.processEvents()
    check("a setup failed half way is undone", raised and [action.text() for action in broken_compare.menu.actions()]
          == ["Pin the current state", "Remove the pin"] and not any(
              isinstance(child, QWidget) and child.objectName() == "frame_fm_history" and child.isVisible()
              for child in broken.findChildren(QWidget)))
    broken_compare.teardown()
    compare.teardown()
    QgsApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    print(f"{'ALL PASSED' if not FAILURES else str(len(FAILURES)) + ' FAILED'}", flush=True)
    os._exit(1 if FAILURES else 0)


main()
