#!/usr/bin/env python3
"""Compare mode (adapters/qgis/compare_swipe.py) in a real QGIS: before left of the swipe line, after on its right.

    docker run --rm -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen qgis/qgis:stable \\
        python3 /src/tests/qgis_headless/check_compare.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer

APP = QgsApplication([], True)
APP.initQgis()

from qgis.gui import QgsMapCanvas, QgsMapMouseEvent, QgsMapToolPan, QgsMapToolZoom  # noqa: E402
from qgis.PyQt.QtCore import QEvent, QPoint, QSize, Qt  # noqa: E402
from qgis.PyQt.QtGui import QColor, QImage, QPainter  # noqa: E402

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

    tool = session.tool
    count = session.start([BeforeState(zones.id(), "\"name\" LIKE 'west%'")], {zones.id(): zones})
    check("compared again while on: the same tool, the tool before kept", count == 1 and session.tool is tool
          and canvas.mapTool() is tool)

    session.stop()
    check("stopped: the tool there before, no item, no clone", canvas.mapTool() is pan and session.item is None
          and not session.clones and not any(isinstance(i, SwipeItem) for i in canvas.scene().items()))
    check("stopped: the project as it was", set(project.mapLayers()) == layers_before)

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

    print(f"{'ALL PASSED' if not FAILURES else str(len(FAILURES)) + ' FAILED'}", flush=True)
    os._exit(1 if FAILURES else 0)


main()
