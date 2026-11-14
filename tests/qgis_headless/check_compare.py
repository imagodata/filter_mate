#!/usr/bin/env python3
"""Compare mode (adapters/qgis/compare_swipe.py) in a real QGIS: before left of the swipe line, after on its right.

The map before a filter, a style, a layer shown, hidden or added (a turn of the agent, a pin), the labels by the line,
the line fixed by a click (the map still zoomed by the wheel and panned by the middle button), and the button of the
action bar with its pin (ui/controllers/compare_controller.py) on a dock made for the check.

    docker run --rm --init --network none -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen qgis/qgis:stable \\
        python3 /src/tests/qgis_headless/check_compare.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer

APP = QgsApplication([], True)
APP.initQgis()

from qgis.gui import QgsMapCanvas, QgsMapMouseEvent, QgsMapToolPan, QgsMapToolZoom  # noqa: E402
from qgis.PyQt.QtCore import QEvent, QPoint, QPointF, QSize, Qt  # noqa: E402
from qgis.PyQt.QtGui import QColor, QImage, QMouseEvent, QPainter, QWheelEvent  # noqa: E402
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


packages = Path(tempfile.mkdtemp(prefix="fm-compare-"))
_link_dir(packages / "filter_mate", ROOT)
sys.path.insert(0, str(packages))

import make_fixtures  # noqa: E402
from filter_mate.adapters.qgis.compare_swipe import CompareSession, SwipeItem, SwipeTool  # noqa: E402
from filter_mate.core.domain.compare_states import BeforeState  # noqa: E402

FAILURES = []
SIZE = QSize(800, 600)


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


def coloured(image, x0, x1):
    """Sampled pixels of a band of columns that are neither white nor the line."""
    count = 0
    for y in range(10, image.height() - 10, 6):
        for x in range(x0, x1, 6):
            colour = image.pixelColor(x, y)
            if colour.rgb() != QColor("white").rgb() and colour.red() > colour.blue() + 40:  # the fill of the squares
                count += 1
    return count


def main():
    project = QgsProject.instance()
    fixtures = make_fixtures.make_all(tempfile.mkdtemp())
    zones = QgsVectorLayer(fixtures["zones"] + "|layername=zones", "zones", "ogr")
    project.addMapLayer(zones)
    zones.renderer().symbol().setColor(QColor(220, 40, 40))
    full = zones.extent()
    full.grow(full.width() * 0.05)
    zones.setSubsetString("\"name\" = 'east_a'")  # the filter as it is; before it, every square starting with east
    layers_before = set(project.mapLayers())

    canvas = QgsMapCanvas()
    canvas.resize(SIZE)
    canvas.setDestinationCrs(zones.crs())
    canvas.setCanvasColor(QColor("white"))
    canvas.setLayers([zones])
    canvas.setExtent(full)
    canvas.show()
    pan = QgsMapToolPan(canvas)
    canvas.setMapTool(pan)
    refreshed = []
    canvas.mapCanvasRefreshed.connect(lambda: refreshed.append(True))
    canvas.refresh()
    wait(lambda: bool(refreshed) and not canvas.isDrawing(), 10)
    after_only = grab(canvas)
    if os.environ.get('FM_COMPARE_OUT'):
        after_only.save(os.path.join(os.environ['FM_COMPARE_OUT'], 'after_only.png'))

    session = CompareSession(canvas)
    count = session.start([BeforeState(zones.id(), "\"name\" LIKE 'east%'")], {zones.id(): zones})
    check("one layer compared, its tool on the canvas", count == 1 and canvas.mapTool() is session.tool,
          (count, canvas.mapTool()))
    check("the clone stays out of the project", set(project.mapLayers()) == layers_before)
    rendered = wait(lambda: session.renders >= 1 and not session.item.busy, 10)
    check("the before image is rendered in the background", rendered)
    width = after_only.width()
    now = coloured(after_only, 10, width - 10)
    session.item.set_fraction(1.0)  # the line at the right edge: the state before everywhere
    QgsApplication.processEvents()
    before_everywhere = grab(canvas)
    session.item.set_fraction(0.0)  # at the left edge: the map as it is everywhere
    QgsApplication.processEvents()
    after_everywhere = grab(canvas)
    if os.environ.get("FM_COMPARE_OUT"):
        before_everywhere.save(os.path.join(os.environ["FM_COMPARE_OUT"], "before_everywhere.png"))
    check("the map as it is has a filtered layer to compare", now > 0, now)
    check("left of the line: the state before (more squares than now)",
          coloured(before_everywhere, 10, width - 10) > now, (now, coloured(before_everywhere, 10, width - 10)))
    check("right of the line: the map as it is", abs(coloured(after_everywhere, 10, width - 10) - now) <= 2,
          (now, coloured(after_everywhere, 10, width - 10)))

    move = QgsMapMouseEvent(canvas, QEvent.Type.MouseMove, QPoint(600, 300), Qt.MouseButton.NoButton,
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    session.tool.canvasMoveEvent(move)
    check("the line follows the mouse", abs(session.item.fraction - 0.75) < 0.01, session.item.fraction)

    renders = session.renders
    zoomed = QgsRectangle(full)
    zoomed.scale(0.5)
    canvas.setExtent(zoomed)
    canvas.refresh()
    check("a pan or a zoom renders the before image again", wait(lambda: session.renders > renders, 10),
          session.renders)

    check_fixed_line(canvas, session, full)

    tool = session.tool
    count = session.start([BeforeState(zones.id(), "\"name\" LIKE 'west%'")], {zones.id(): zones})
    check("compared again while on: the same tool, the tool before kept, the line still fixed", count == 1
          and session.tool is tool and canvas.mapTool() is tool and session.item.frozen)

    session.stop()
    check("stopped: the tool there before, no item, no clone", canvas.mapTool() is pan and session.item is None
          and not session.clones and not any(isinstance(i, SwipeItem) for i in canvas.scene().items()))
    check("stopped: the project as it was", set(project.mapLayers()) == layers_before)
    session.start([BeforeState(zones.id(), "\"name\" LIKE 'west%'")], {zones.id(): zones})
    check("compared again after a stop: the line follows the mouse again", session.active and not session.item.frozen)
    session.stop()

    # Another tool chosen while comparing: the comparison ends by itself and leaves that tool.
    ended = []
    session.ended.connect(lambda: ended.append(True))
    session.start([BeforeState(zones.id(), "")], {zones.id(): zones})
    zoom = QgsMapToolZoom(canvas, False)
    canvas.setMapTool(zoom)
    check("another tool chosen: the comparison ends, that tool stays", ended == [True] and not session.active
          and canvas.mapTool() is zoom and not any(isinstance(i, SwipeItem) for i in canvas.scene().items()))
    canvas.setMapTool(pan)

    # Started and stopped again and again (each refresh of the dock): no tool, no item, no render left behind.
    for _ in range(5):
        session.start([BeforeState(zones.id(), "")], {zones.id(): zones})
        session.stop()
    wait(lambda: not session._retired, 10)
    QgsApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QgsApplication.processEvents()
    tools = [child for child in canvas.children() if isinstance(child, SwipeTool)]
    check("five comparisons later: no swipe tool, item or render left", not tools and session._job is None
          and not session._retired and not any(isinstance(i, SwipeItem) for i in canvas.scene().items()),
          (len(tools), session._job, len(session._retired)))

    # A raster whose former source is gone (a derived file removed since): left out, nothing to compare.
    dem = QgsRasterLayer(fixtures["dem"], "dem", "gdal")
    project.addMapLayer(dem)
    count = session.start([BeforeState(dem.id(), "", os.path.join(tempfile.mkdtemp(), "gone.tif"), "gdal")],
                          {dem.id(): dem})
    check("a former source removed since: nothing compared, nothing shown", count == 0 and not session.active
          and canvas.mapTool() is pan)

    # A raster with its former source: compared.
    count = session.start([BeforeState(dem.id(), "", fixtures["dem"], "gdal")], {dem.id(): dem})
    check("a raster with its former source is compared", count == 1 and session.active)
    session.stop()
    project.removeMapLayer(dem.id())

    zones.setSubsetString("")
    check_map_before(project, canvas, fixtures, zones, session)
    check_reading(project, zones)
    check_button(project, canvas, fixtures, zones)

    print(f"{'ALL PASSED' if not FAILURES else str(len(FAILURES)) + ' FAILED'}", flush=True)
    os._exit(1 if FAILURES else 0)


def check_fixed_line(canvas, session, full):
    """A left click fixes the line where it is, another frees it; fixed, the wheel and the middle button still move the
    map, and the line stays where it was fixed."""
    item, tool = session.item, session.tool
    item.fixed_note = "line fixed"
    item.set_labels("Before", "Now")

    def release(x, button=Qt.MouseButton.LeftButton, pressed_at=-1):
        """A click at ``x`` (pressed there, or at ``pressed_at``: a drag); ``pressed_at`` None: a release alone."""
        if pressed_at is not None:
            tool.canvasPressEvent(QgsMapMouseEvent(
                canvas, QEvent.Type.MouseButtonPress, QPoint(x if pressed_at < 0 else pressed_at, 300), button,
                button, Qt.KeyboardModifier.NoModifier))
        tool.canvasReleaseEvent(QgsMapMouseEvent(canvas, QEvent.Type.MouseButtonRelease, QPoint(x, 300), button,
                                                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))

    def move(x):
        tool.canvasMoveEvent(QgsMapMouseEvent(canvas, QEvent.Type.MouseMove, QPoint(x, 300), Qt.MouseButton.NoButton,
                                              Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    check("a free line: no knob, the labels as given", not item.frozen and item.handle_rect().isEmpty()
          and item.shown_labels() == ("Before", "Now"))
    # A review of 2026-11-14: a release alone (a menu closed over the map, the second half of a double click) and the
    # end of a drag fixed or freed the line without the user meaning it.
    release(200, pressed_at=None)
    alone = item.frozen
    release(200, pressed_at=420)
    check("only a click made on the map fixes the line: not a release alone, not a drag", not alone and not item.frozen,
          (alone, item.frozen))
    release(200)
    check("a click fixes the line where it is", item.frozen and abs(item.fraction - 0.25) < 0.01, item.fraction)
    move(600)
    check("fixed: the line no longer follows the mouse", abs(item.fraction - 0.25) < 0.01, item.fraction)
    handle = item.handle_rect()
    check("fixed: the label on the right says so, the knob under the labels, inside the bounds",
          item.shown_labels() == ("Before", "Now · line fixed") and not handle.isEmpty()
          and handle.top() > item.label_rects()[1].bottom() and item.boundingRect().contains(handle),
          (item.shown_labels(), handle, item.label_rects()))
    QgsApplication.processEvents()
    image = grab(canvas)
    centre = handle.center() + item.pos()
    probe = image.pixelColor(int(centre.x()), int(centre.y()))
    check("fixed: a dark knob drawn on the line", probe.red() < 90 and probe.green() < 90 and probe.blue() < 90,
          probe.name())
    release(500, Qt.MouseButton.RightButton)
    check("fixed: a right click leaves it fixed", item.frozen and abs(item.fraction - 0.25) < 0.01)

    # The wheel zooms, the middle button pans: the canvas handles them before the tool.
    extent, renders = canvas.extent(), session.renders
    QApplication.sendEvent(canvas.viewport(), QWheelEvent(
        QPointF(400, 300), QPointF(canvas.viewport().mapToGlobal(QPoint(400, 300))), QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False))
    zoomed = canvas.extent()
    check("fixed: the wheel still zooms, the line stays", zoomed.width() < extent.width() * 0.99 and item.frozen
          and abs(item.fraction - 0.25) < 0.01, (extent.toString(), zoomed.toString()))
    check("fixed: the before image follows the zoom", wait(lambda: session.renders > renders and not item.busy, 10))
    viewport = canvas.viewport()
    for kind, x, button, buttons in ((QEvent.Type.MouseButtonPress, 400, Qt.MouseButton.MiddleButton,
                                      Qt.MouseButton.MiddleButton),
                                     (QEvent.Type.MouseMove, 460, Qt.MouseButton.NoButton, Qt.MouseButton.MiddleButton),
                                     (QEvent.Type.MouseButtonRelease, 460, Qt.MouseButton.MiddleButton,
                                      Qt.MouseButton.NoButton)):
        QApplication.sendEvent(viewport, QMouseEvent(kind, QPointF(x, 300), button, buttons,
                                                     Qt.KeyboardModifier.NoModifier))
        QgsApplication.processEvents()
    panned = canvas.extent()
    check("fixed: the middle button still pans, the line stays", abs(panned.center().x() - zoomed.center().x()) > 0
          and item.frozen and abs(item.fraction - 0.25) < 0.01, (zoomed.toString(), panned.toString()))
    canvas.setExtent(full)
    canvas.refresh()

    release(400)
    check("a second click frees the line, under the mouse", not item.frozen and abs(item.fraction - 0.5) < 0.01
          and item.handle_rect().isEmpty() and item.shown_labels() == ("Before", "Now"), item.fraction)
    move(600)
    check("freed: the line follows the mouse again", abs(item.fraction - 0.75) < 0.01, item.fraction)
    release(200)  # fixed again: a new comparison while on keeps it, a stop forgets it (main)


RED, BLUE, GREEN, YELLOW = QColor(220, 40, 40), QColor(40, 40, 220), QColor(40, 200, 40), QColor(240, 220, 0)


def count(image, colour):
    """Sampled pixels of ``image`` near ``colour`` (the fill of the squares of one layer)."""
    found = 0
    for y in range(10, image.height() - 10, 6):
        for x in range(10, image.width() - 10, 6):
            pixel = image.pixelColor(x, y)
            if (abs(pixel.red() - colour.red()) < 30 and abs(pixel.green() - colour.green()) < 30
                    and abs(pixel.blue() - colour.blue()) < 30):
                found += 1
    return found


def squares(fixtures, name, colour, subset=""):
    layer = QgsVectorLayer(fixtures["zones"] + "|layername=zones", name, "ogr")
    layer.renderer().symbol().setColor(colour)
    if subset:
        layer.setSubsetString(subset)
    return layer


def recolour(layer, colour):
    """A new colour, said as the layer properties of QGIS say it (styleChanged)."""
    layer.renderer().symbol().setColor(colour)
    layer.triggerRepaint()
    layer.emitStyleChanged()


def drawn(canvas):
    """The canvas drawn again after a change (the layer tree bridge sets its layers a moment later)."""
    done = []

    def on_drawn():
        done.append(True)
    canvas.mapCanvasRefreshed.connect(on_drawn)
    wait(lambda: False, 0.3)
    canvas.refresh()
    ok = wait(lambda: bool(done) and not canvas.isDrawing(), 15)
    canvas.mapCanvasRefreshed.disconnect(on_drawn)
    return ok


def sides(session, canvas):
    """The map left of the line everywhere (before), then right of it everywhere (now)."""
    session.item.set_fraction(1.0)
    QgsApplication.processEvents()
    before = grab(canvas)
    session.item.set_fraction(0.0)
    QgsApplication.processEvents()
    now = grab(canvas)
    session.item.set_fraction(0.5)
    if os.environ.get("FM_COMPARE_OUT"):
        before.save(os.path.join(os.environ["FM_COMPARE_OUT"], f"before_{session.renders}.png"))
        now.save(os.path.join(os.environ["FM_COMPARE_OUT"], f"now_{session.renders}.png"))
    return before, now


def rendered(session, renders):
    return wait(lambda: session.renders > renders and not session.item.busy, 15)


def check_map_before(project, canvas, fixtures, zones, session):
    """A pin and a turn of the agent: style, layers shown, hidden and added drawn as they were; the labels."""
    from qgis.gui import QgsLayerTreeMapCanvasBridge
    from filter_mate.adapters.agent.turn_effects import _style
    from filter_mate.adapters.qgis.compare_swipe import map_state
    from filter_mate.core.domain.compare_states import BeforeMap, map_from_operation, map_from_pin

    bridge = QgsLayerTreeMapCanvasBridge(project.layerTreeRoot(), canvas)
    blue = squares(fixtures, "blue", BLUE, "\"name\" LIKE 'west%'")
    project.addMapLayer(blue)
    recolour(zones, RED)
    zones.setSubsetString("\"name\" LIKE 'east%'")
    drawn(canvas)
    first = grab(canvas)
    check("pin: the map pinned shows the red and the blue squares", count(first, RED) > 0 and count(first, BLUE) > 0,
          (count(first, RED), count(first, BLUE)))
    pinned = map_state(canvas)
    check("pin: every layer read, drawn or not", [(layer.layer_id, layer.visible) for layer in pinned.layers]
          == [(blue.id(), True), (zones.id(), True)] and all(layer.style and layer.snapshot for layer in pinned.layers),
          [(layer.name, layer.visible) for layer in pinned.layers])
    red_style = next(layer.style for layer in pinned.layers if layer.layer_id == zones.id())

    # Since the pin: zones yellow, blue hidden, green added on top.
    recolour(zones, YELLOW)
    project.layerTreeRoot().findLayer(blue.id()).setItemVisibilityChecked(False)
    green = squares(fixtures, "green", GREEN, "\"name\" LIKE 'west%'")
    project.addMapLayer(green)
    drawn(canvas)
    before = map_from_pin(pinned, map_state(canvas))
    check("pin: zones restyled, blue hidden, green added", [state.layer_id for state in before.states] == [zones.id()]
          and before.states[0].style == red_style and before.states[0].subset is None and before.present == (blue.id(),)
          and before.absent == frozenset({green.id()}) and not before.missing, before)
    renders = session.renders
    compared = session.start(before, project.mapLayers(), keep=True, labels=("Pinned 10:00", "Now"))
    check("pin: three layers drawn otherwise", compared == 3 and session.active, compared)
    check("pin: the before image is rendered", rendered(session, renders))
    layers = session._before_layers()  # a clone has an id of its own: named
    order = [(layer.name(), layer is session.clones.get(zones.id())) for layer in layers]
    check("pin: blue back at its place in the tree, green left out, zones as its clone",
          order == [("blue", False), ("zones", True)]
          and [layer.id() for layer in project.layerTreeRoot().layerOrder()] == [green.id(), blue.id(), zones.id()],
          (order, [layer.name() for layer in project.layerTreeRoot().layerOrder()]))
    left, right = sides(session, canvas)
    check("pin: left of the line, the red and blue squares, no green", count(left, RED) > 0 and count(left, BLUE) > 0
          and count(left, GREEN) == 0 and count(left, YELLOW) == 0,
          (count(left, RED), count(left, BLUE), count(left, GREEN), count(left, YELLOW)))
    check("pin: right of the line, yellow and green, no blue", count(right, YELLOW) > 0 and count(right, GREEN) > 0
          and count(right, BLUE) == 0 and count(right, RED) == 0,
          (count(right, YELLOW), count(right, GREEN), count(right, BLUE), count(right, RED)))
    check("the clones stay out of the project", set(project.mapLayers()) == {zones.id(), blue.id(), green.id()})

    # The labels: on both sides of the line, at the top, following it.
    session.item.set_fraction(0.5)
    rect_left, rect_right = session.item.label_rects()
    line = session.item.boundingRect().width() * 0.5
    check("labels: before left of the line, now right of it", session.item.labels == ("Pinned 10:00", "Now")
          and rect_left.right() < line < rect_right.left() and rect_left.top() < 40 and rect_left.width() > 20,
          (rect_left, rect_right, line))
    session.item.set_fraction(0.3)
    moved = session.item.label_rects()[0]
    check("labels: they follow the line", abs((rect_left.right() - moved.right()) - line * 0.4) < 1.0,
          (rect_left, moved))
    session.item.set_fraction(0.5)
    QgsApplication.processEvents()
    image = grab(canvas)
    offset = session.item.pos()
    probe = image.pixelColor(int(rect_left.left() + offset.x() + 2), int(rect_left.center().y() + offset.y()))
    check("labels: a dark pill readable on a light map", probe.red() < 140 and probe.green() < 140, probe.name())
    session.item.set_fraction(0.01)  # the line at the left edge: the label before reaches out of the image
    bounds = session.item.boundingRect()
    rects = session.item.label_rects()
    check("labels: inside the bounds of the item, even out of its image", rects[0].left() < 0
          and all(bounds.contains(rect) for rect in rects), (bounds, rects))
    position = session.item.pos()
    session.item.setPos(position.x(), position.y() + 120)  # the map panned down since the image
    shifted = session.item.label_rects()[0]
    check("labels: at the top of the canvas when the item moved down", abs(shifted.top() + session.item.pos().y() - 8.0)
          < 0.5 and session.item.boundingRect().contains(shifted), (shifted, session.item.pos()))
    session.item.setPos(position)
    session.item.set_fraction(0.5)

    # Nothing differs: a pin waits, the line alone, no render.
    renders = session.renders
    compared = session.start(BeforeMap(pinned_at=1.0), project.mapLayers(), keep=True)
    check("pin with nothing changed: on, nothing rendered, the line drawn",
          compared == 0 and session.active and not session.item.busy and session._job is None
          and session.renders == renders, (compared, session.active, session.item.busy))
    compared = session.start(BeforeMap(), project.mapLayers())
    check("the last operation with nothing to draw: off", compared == 0 and not session.active)

    # A turn of the agent: its style effect, its layer shown and its layer added.
    turn = SimpleNamespace(changes=(), description="Restyle zones", effects=(
        ("style", zones.id(), red_style, _style(zones), "zones"), ("visibility", blue.id(), True, False),
        ("added", green.id(), "<qlr/>", ((), 0), "green"), ("removed", "gone", "<qlr/>", ((), 3), "parcels")))
    before = map_from_operation(turn)
    renders = session.renders
    compared = session.start(before, project.mapLayers(), labels=("Before: Restyle zones", "Now"))
    check("agent turn: style, shown and added layers compared, the removed one named",
          compared == 3 and before.missing == ("parcels",) and rendered(session, renders), compared)
    left, right = sides(session, canvas)
    check("agent turn: left of the line, red and blue, no green", count(left, RED) > 0 and count(left, BLUE) > 0
          and count(left, GREEN) == 0, (count(left, RED), count(left, BLUE), count(left, GREEN)))
    session.stop()
    project.removeMapLayer(green.id())
    project.layerTreeRoot().findLayer(blue.id()).setItemVisibilityChecked(True)
    recolour(zones, RED)
    drawn(canvas)
    STATE["bridge"], STATE["blue"] = bridge, blue


STATE = {}


def check_reading(project, zones):
    """Reading the map for a pin changes no layer; a vector layer pinned is drawn through its plain subset."""
    from qgis.core import QgsVectorTileLayer
    import filter_mate.adapters.qgis.compare_swipe as swipe
    from filter_mate.adapters.qgis.coverage_layers.snapshots import (DERIVED_PROPERTY, DerivedSourceRegistry,
                                                                     registry, take_snapshot)
    from filter_mate.adapters.qgis.coverage_layers.vector_tile_filters import style_xml
    from filter_mate.core.domain.compare_states import BeforeState
    from filter_mate.core.domain.filter_state import LayerSnapshot
    from filter_mate.core.domain.layer_kind import LayerKind

    tiles = QgsVectorTileLayer("type=xyz&url=file:///nowhere/{z}/{x}/{y}.pbf&zmin=0&zmax=14", "tiles")
    project.addMapLayer(tiles)
    xml = style_xml(tiles)
    # A state another session left on the layer (a copy of a filtered layer), its style not the one shown.
    other = xml.replace("<renderer ", "<renderer data-other=\"1\" ", 1)
    DerivedSourceRegistry().record(LayerSnapshot(tiles.id(), "vector_tile", source=tiles.source(),
                                                 provider=tiles.providerType(), renderer_xml=other,
                                                 original_renderer_xml=other, derived=True), tiles)
    stored = tiles.customProperty(DERIVED_PROPERTY)
    keys = sorted(tiles.customPropertyKeys())
    pinned = swipe.map_state()
    state = next(layer for layer in pinned.layers if layer.layer_id == tiles.id())
    check("pin: a vector tile layer read without being changed", style_xml(tiles) == xml
          and tiles.customProperty(DERIVED_PROPERTY) == stored and sorted(tiles.customPropertyKeys()) == keys
          and registry().get(tiles.id()) is None and state.snapshot is not None
          and state.snapshot.renderer_xml == xml, (bool(stored), registry().get(tiles.id())))
    try:  # the registry path, for the record: what the pin no longer does
        take_snapshot(tiles, LayerKind.VECTOR_TILE)
        print("INFO take_snapshot of the tiles changes them: "
              f"style={style_xml(tiles) != xml} property={tiles.customProperty(DERIVED_PROPERTY) != stored} "
              f"registry={registry().get(tiles.id()) is not None}", flush=True)
    except Exception as exc:
        print(f"INFO take_snapshot of the tiles raised {exc!r}", flush=True)
    registry().forget(tiles.id())
    project.removeMapLayer(tiles.id())

    # A vector layer pinned: its plain subset on the clone, never restore_snapshot (rewritten for its source).
    def refused(*_args, **_kwargs):
        raise AssertionError("restore_snapshot called")
    swipe.restore_snapshot, restore = refused, swipe.restore_snapshot
    snapshot = LayerSnapshot(zones.id(), "vector", subset="\"name\" = 'west_a'")
    clone = swipe.before_clone(zones, BeforeState(zones.id(), snapshot.subset, snapshot=snapshot))
    swipe.restore_snapshot = restore
    check("pin: a vector clone takes its subset directly", clone is not None
          and clone.subsetString() == "\"name\" = 'west_a'" and zones.subsetString() != clone.subsetString(),
          clone.subsetString() if clone is not None else None)


class Dock(QWidget):
    """The part of the dock the button needs: the action bar with Undo and Redo, the canvas of QGIS."""

    def __init__(self, canvas):
        super().__init__()
        layout = QHBoxLayout(self)
        for name in ("pushButton_action_filter", "pushButton_action_undo_filter", "pushButton_action_redo_filter"):
            button = QPushButton(name[19:], self)
            setattr(self, name, button)
            layout.addWidget(button)
        self.iface = SimpleNamespace(mapCanvas=lambda: canvas)
        self.current_layer = None


def check_button(project, canvas, fixtures, zones):
    """The button of the action bar: pinned from its menu (enabled or not), following the map, forgotten."""
    from filter_mate.ui.controllers.compare_controller import CompareController
    from qgis.PyQt.QtGui import QContextMenuEvent
    from qgis.PyQt.QtWidgets import QApplication

    dock = Dock(canvas)
    dock.pushButton_action_undo_filter.setEnabled(False)
    dock.show()
    controller = CompareController(dock)
    said = []
    controller._say = said.append
    changes = []  # pinChanged: whether a pin is there each time
    controller.pinChanged.connect(lambda: changes.append(controller.pinned is not None))
    button = dock.pushButton_action_compare
    unpinned_icon = button.icon().pixmap(32, 32).toImage()
    check("button: beside Redo, off without Undo nor pin", button.parentWidget() is dock and not button.isEnabled()
          and "Right-click" in button.toolTip(), button.toolTip())
    check("button: its tooltip says a click fixes the line",
          "Click on the map to fix the line, click again to free it." in button.toolTip().split("\n"), button.toolTip())

    # Right-click on the disabled button: its menu all the same (the bar opens it), never modal.
    point = QPoint(4, 4)
    QApplication.sendEvent(button, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, button.mapToGlobal(point)))
    QgsApplication.processEvents()
    check("button: right-click when disabled opens its menu", controller.menu.isVisible()
          and [action.text() for action in controller.menu.actions()] == ["Pin the current state", "Remove the pin"]
          and not controller.unpin_action.isEnabled())
    controller.pin_action.trigger()
    controller.menu.close()
    check("pin: kept, the button available and marked, its tooltip says when",
          controller.pinned is not None and button.isEnabled()
          and button.icon().pixmap(32, 32).toImage() != unpinned_icon and "pinned at" in button.toolTip()
          and any("pinned at" in text for text in said), (button.toolTip(), said))

    pan = QgsMapToolPan(canvas)
    canvas.setMapTool(pan)
    said.clear()
    button.click()
    session = controller.session
    check("pin: nothing changed, the comparison waits and says so", button.isChecked() and session.active
          and not session.item.busy and said == ["Nothing changed since the pin."], said)
    check("pin: labels pinned and now", session.item.labels[0].startswith("Pinned ") and session.item.labels[1] == "Now",
          session.item.labels)
    check("pin: a line fixed would say so on its right", session.item.fixed_note == "line fixed: click to free it",
          session.item.fixed_note)

    # A filter since: the comparison follows it, Filter does not end it.
    renders = session.renders
    dock.pushButton_action_filter.click()
    zones.setSubsetString("\"name\" = 'east_a'")
    drawn(canvas)
    check("pin: a filter since is drawn as pinned", wait(lambda: session.compared_layer_ids() == [zones.id()]
                                                         and session.renders > renders and not session.item.busy, 15)
          and button.isChecked(), (session.compared_layer_ids(), session.renders))
    left, right = sides(session, canvas)
    check("pin: more squares left of the line than right", count(left, RED) > count(right, RED) > 0,
          (count(left, RED), count(right, RED)))
    renders = session.renders
    drawn(canvas)
    wait(lambda: False, 0.5)
    check("pin: a map drawn again with the same differences renders nothing", session.renders == renders
          and not controller._follow_timer.isActive(), (renders, session.renders))

    # The map is read again only when something may have changed, its styles only for the layers that changed.
    import filter_mate.adapters.agent.turn_effects as turn_effects
    watch, reads, styles = controller._watch, [], []
    original_read, original_style = watch.read, turn_effects._style
    watch.read = lambda canvas=None: (reads.append(1), original_read(canvas))[1]
    turn_effects._style = lambda layer: (styles.append(layer.name()), original_style(layer))[1]
    drawn(canvas)
    canvas.setExtent(canvas.extent())
    drawn(canvas)
    wait(lambda: False, 0.5)
    check("watch: a pan or a refresh with nothing changed reads nothing", not reads and not watch.dirty, reads)
    renders = session.renders
    recolour(zones, YELLOW)
    deadline = time.time() + 1.0
    while time.time() < deadline:  # an animated symbol: the map drawn every 50 ms
        canvas.mapCanvasRefreshed.emit()
        wait(lambda: False, 0.05)
    read_while_drawn = len(reads)
    check("watch: read while the map is drawn every 50 ms (a throttle, not a debounce)", read_while_drawn >= 1,
          read_while_drawn)
    check("watch: only the style of the layer restyled is read again", styles == ["zones"], styles)
    check("watch: the new difference is drawn", wait(lambda: session.renders > renders and not session.item.busy, 10),
          session.renders)
    watch.read, turn_effects._style = original_read, original_style
    del watch.read
    recolour(zones, RED)
    drawn(canvas)
    wait(lambda: not watch.dirty and not controller._follow_timer.isActive(), 5)

    # The layers moved in the tree, the same differences: the image before is drawn again, in the new order.
    renders = session.renders
    root = project.layerTreeRoot()
    node = root.findLayer(zones.id())
    root.insertChildNode(0, node.clone())
    root.removeChildNode(node)
    drawn(canvas)
    check("watch: a layer moved in the tree draws the image before again", wait(lambda: session.renders > renders
                                                                              and not session.item.busy, 10)
          and [layer.id() for layer in root.layerOrder()][0] == zones.id(), session.renders)

    # Back as pinned: on, nothing to draw, said.
    said.clear()
    zones.setSubsetString("\"name\" LIKE 'east%'")
    drawn(canvas)
    check("pin: back as pinned, on and empty", wait(lambda: not session.compared_layer_ids(), 15) and session.active
          and said == ["Nothing changed since the pin."], said)

    # A layer removed since: named once, the comparison goes on.
    blue = STATE["blue"]
    said.clear()
    project.removeMapLayer(blue.id())
    drawn(canvas)
    wait(lambda: bool(said), 5)
    check("pin: a layer removed since is named, the comparison goes on",
          said == ["Not drawn as they were: blue"] and session.active and button.isChecked(), said)

    # Another map tool ends it; the pin stays.
    zoom = QgsMapToolZoom(canvas, False)
    canvas.setMapTool(zoom)
    check("pin: another map tool ends the comparison, the pin stays", not button.isChecked() and not session.active
          and controller.pinned is not None)
    canvas.setMapTool(pan)

    # The pin removed: without Undo, the button is off again.
    controller.unpin_action.trigger()
    check("unpin: no mark, unavailable without Undo", controller.pinned is None and not button.isEnabled()
          and button.icon().pixmap(32, 32).toImage() == unpinned_icon,
          (controller.pinned, button.isEnabled(), button.icon().pixmap(32, 32).toImage() == unpinned_icon))

    # Without a pin, what cannot be drawn is said once, not again at each refresh (a turn of the agent).
    from filter_mate.core.domain.compare_states import BeforeMap, BeforeState
    dock.pushButton_action_undo_filter.setEnabled(True)
    west = "\"name\" LIKE 'west%'"
    controller.last_operation = lambda: BeforeMap((BeforeState(zones.id(), west),), missing=("parcels",))
    said.clear()
    button.click()
    controller.refresh()
    controller.refresh()
    check("last operation: a removed layer named once, not at each refresh", button.isChecked() and session.active
          and said == ["Not drawn as they were: parcels"], said)
    button.click()
    controller.last_operation = lambda: BeforeMap(missing=("parcels",))
    said.clear()
    button.click()
    check("last operation that only removed a layer: named, not 'nothing to compare'", not button.isChecked()
          and said == ["Not drawn as they were: parcels"], said)
    del controller.last_operation
    dock.pushButton_action_undo_filter.setEnabled(False)

    # compare_with: a step given, the pin aside; it ends as the last operation does.
    said.clear()
    compared = controller.compare_with(BeforeMap((BeforeState(zones.id(), west),), unshown=(
        ("tree", "", ""), ("edits", zones.id(), "zones"))), labels=("Before: step 3", "Now"))
    check("compare_with: on with its labels, available without Undo, what it cannot draw named",
          compared == 1 and button.isChecked() and button.isEnabled() and session.item.labels == ("Before: step 3", "Now")
          and said == ["Not drawn as they were: layer tree, zones"], (compared, said, session.item.labels))
    dock.pushButton_action_filter.click()
    check("compare_with: Filter ends it, the button as Undo is", not session.active and not button.isChecked()
          and not button.isEnabled())

    # Failures are said: a pin not taken, a pinned map not read when starting or following.
    import filter_mate.ui.controllers.compare_controller as compare_module

    def unreadable(*_args):
        raise KeyError("unreadable")
    said.clear()
    compare_module.map_state, readable = unreadable, compare_module.map_state
    check("pin: a map that cannot be read is said, nothing pinned", controller.pin() is None
          and controller.pinned is None and said == ["The map could not be pinned."], said)
    compare_module.map_state = readable
    from filter_mate.adapters.qgis.compare_swipe import map_state
    state = map_state(canvas)
    controller.pin_state(state)
    check("pin_state: the state given is the pin", controller.pinned is state and button.isEnabled())
    controller.compare_with(BeforeMap((BeforeState(zones.id(), west),)), labels=("Before: step 3", "Now"))
    compared = controller.compare_pin()
    check("compare_pin: the pin compared instead of the step, as a click on the button", button.isChecked()
          and session.active and controller._given is None and session.item.labels[0].startswith("Pinned "),
          (compared, session.item.labels))
    controller.stop()
    said.clear()
    controller.before_map = unreadable
    button.click()
    check("pin: a map not read when starting stops, never 'nothing changed'", not button.isChecked()
          and not session.active and said == ["Compare stopped: the map could not be read."], said)
    del controller.before_map
    button.click()
    said.clear()
    watch.read = unreadable
    zones.setSubsetString(west)
    drawn(canvas)
    check("pin: a map not read while following stops the comparison and says so",
          wait(lambda: not session.active, 5) and not button.isChecked()
          and said == ["Compare stopped: the map could not be read."], said)
    del watch.read
    zones.setSubsetString("\"name\" LIKE 'east%'")

    # A new project forgets the pin.
    controller.pin()
    button.click()
    project.clear()
    QgsApplication.processEvents()
    check("a new project forgets the pin and ends the comparison", controller.pinned is None and not session.active
          and not button.isChecked() and not button.isEnabled())
    check("pinChanged: pinned, removed, pinned twice, forgotten with the project",
          changes == [True, False, True, True, False], changes)
    check("compare_pin without a pin: nothing", controller.compare_pin() == 0 and not session.active)
    controller.teardown()


main()
