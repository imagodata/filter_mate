#!/usr/bin/env python3
"""Spike of a "Compare" mode: the state of a layer before a filter and after it, side by side, behind a swipe line.

Questions it answers, on the fixtures of tests/qgis_headless/make_fixtures.py, in a standalone QGIS:

1. Does a clone of a layer, kept out of the project, render with another state (a vector with another subset, a
   raster with another source, a point cloud with another subset) and leave the project as it was?
2. How long does each render take (the cost of drawing the "before" state once per extent)?
3. Can a canvas item draw the "before" image on one side of a swipe line, the canvas drawing the "after" state, and
   does the grabbed canvas show both sides?

Run (writes JSON lines and PNGs into the folder given):

    docker run --rm -v "$PWD:/src:ro" -v /tmp/out:/out -e QT_QPA_PLATFORM=offscreen qgis/qgis:stable \\
        python3 /src/scripts/spikes/compare_render.py /out
"""
import json
import os
import sys
import tempfile
import time

from qgis.core import (
    Qgis, QgsApplication, QgsMapRendererParallelJob, QgsMapSettings, QgsPointCloudLayer, QgsPointXY, QgsProject,
    QgsRasterLayer, QgsRectangle, QgsVectorLayer,
)

APP = QgsApplication([], True)
APP.initQgis()

from qgis.gui import QgsMapCanvas, QgsMapCanvasItem  # noqa: E402
from qgis.PyQt.QtCore import QRectF, QSize  # noqa: E402
from qgis.PyQt.QtGui import QColor, QImage, QPainter  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tests", "qgis_headless"))
import make_fixtures  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
SIZE = QSize(800, 600)
RESULTS = {"qgis": Qgis.QGIS_VERSION}


def report(key, value):
    RESULTS[key] = value
    print(json.dumps({key: value}), flush=True)


def wait(condition, seconds=30.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        QgsApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def render(layer, extent):
    """The layer alone, drawn on a white image of SIZE; (image, seconds)."""
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(layer.crs())
    settings.setExtent(extent)
    settings.setOutputSize(SIZE)
    settings.setBackgroundColor(QColor("white"))
    job = QgsMapRendererParallelJob(settings)
    started = time.perf_counter()
    job.start()
    job.waitForFinished()
    return job.renderedImage(), round(time.perf_counter() - started, 4)


def differing_pixels(first, second):
    """How many pixels differ between two images of the same size (sampled every 4 pixels)."""
    count = 0
    for y in range(0, first.height(), 4):
        for x in range(0, first.width(), 4):
            if first.pixel(x, y) != second.pixel(x, y):
                count += 1
    return count


def swipe_composite(before, after, fraction):
    """Before on the left of the line, after on its right: what the canvas should show."""
    image = QImage(after)
    painter = QPainter(image)
    painter.drawImage(QRectF(0, 0, image.width() * fraction, image.height()), before,
                      QRectF(0, 0, before.width() * fraction, before.height()))
    painter.end()
    return image


class SwipeItem(QgsMapCanvasItem):
    """The "before" image over its map extent, clipped to the left of the swipe line (as _MaskItem, with a clip)."""

    def __init__(self, canvas, image, extent, fraction):
        super().__init__(canvas)
        self._image, self._extent, self._fraction = image, QgsRectangle(extent), fraction
        self._size = QRectF()
        self.setZValue(5)
        self.updatePosition()

    def boundingRect(self):  # noqa: N802 - Qt override
        return self._size

    def updatePosition(self):  # noqa: N802 - Qt override
        top_left = self.toCanvasCoordinates(QgsPointXY(self._extent.xMinimum(), self._extent.yMaximum()))
        bottom_right = self.toCanvasCoordinates(QgsPointXY(self._extent.xMaximum(), self._extent.yMinimum()))
        self.prepareGeometryChange()
        self._size = QRectF(0.0, 0.0, bottom_right.x() - top_left.x(), bottom_right.y() - top_left.y())
        self.setPos(top_left)

    def paint(self, painter, *_args):
        painter.save()
        painter.setClipRect(QRectF(0, 0, self._size.width() * self._fraction, self._size.height()))
        painter.drawImage(self._size, self._image)
        painter.restore()


def compare(name, after, before, extent):
    """Render both states, check they differ, compose the swipe, save the images."""
    after_image, after_seconds = render(after, extent)
    before_image, before_seconds = render(before, extent)
    composite = swipe_composite(before_image, after_image, 0.5)
    for label, image in (("after", after_image), ("before", before_image), ("swipe", composite)):
        image.save(os.path.join(OUT, f"{name}_{label}.png"))
    report(name, {"after_s": after_seconds, "before_s": before_seconds,
                  "differing_samples": differing_pixels(after_image, before_image),
                  "before_in_project": before.id() in QgsProject.instance().mapLayers()})
    return after_image, before_image, composite


def main():
    project = QgsProject.instance()
    fixtures = make_fixtures.make_all(tempfile.mkdtemp())

    # 1. Vector: the layer of the project filtered "after", its clone "before" with the former subset.
    zones = QgsVectorLayer(fixtures["zones"] + "|layername=zones", "zones", "ogr")
    project.addMapLayer(zones)
    zones.setSubsetString("\"name\" = 'east_a'")
    layers_before = set(project.mapLayers())
    zones_before = zones.clone()
    zones_before.setSubsetString("\"name\" LIKE 'east%'")
    extent = zones_before.extent()
    extent.grow(extent.width() * 0.05)
    after_image, before_image, composite = compare("vector", zones, zones_before, extent)
    report("project_untouched_by_clone", set(project.mapLayers()) == layers_before)

    # 3. Canvas: it draws "after", the item the "before" image left of the line; the grab must show both.
    canvas = QgsMapCanvas()
    canvas.resize(SIZE)
    canvas.setDestinationCrs(zones.crs())
    canvas.setCanvasColor(QColor("white"))
    canvas.setLayers([zones])
    canvas.setExtent(extent)
    canvas.show()
    refreshed = []
    canvas.mapCanvasRefreshed.connect(lambda: refreshed.append(True))
    canvas.refresh()
    drawn = wait(lambda: bool(refreshed) and not canvas.isDrawing(), 15)
    # The images drawn for the item are made at the extent the canvas really shows (its aspect may differ).
    after_image, _seconds = render(zones, canvas.extent())
    before_image, before_seconds = render(zones_before, canvas.extent())
    started = time.perf_counter()
    item = SwipeItem(canvas, before_image, canvas.extent(), 0.5)
    canvas.scene().update()
    QgsApplication.processEvents()
    grab = QImage(canvas.size(), QImage.Format.Format_ARGB32)
    grab.fill(QColor("white"))
    painter = QPainter(grab)
    canvas.render(painter)
    painter.end()
    paint_seconds = round(time.perf_counter() - started, 4)
    grab.save(os.path.join(OUT, "canvas_swipe.png"))
    white = QColor("white").rgb()
    left = [0, 0]
    right = [0, 0]  # [samples where the expected image draws something, of them matching]
    for y in range(10, grab.height() - 10, 4):
        for x in range(10, grab.width() - 10, 4):
            fx, fy = x * before_image.width() // grab.width(), y * before_image.height() // grab.height()
            expected = before_image if x < grab.width() * 0.5 else after_image
            colour = expected.pixelColor(fx, fy).rgb()
            if colour == white:
                continue
            tally = left if x < grab.width() * 0.5 else right
            tally[0] += 1
            tally[1] += grab.pixelColor(x, y).rgb() == colour
    report("canvas_item", {"canvas_drawn": drawn, "grab_size": [grab.width(), grab.height()],
                           "left_drawn_samples": left[0], "left_matching_before": left[1],
                           "right_drawn_samples": right[0], "right_matching_after": right[1],
                           "before_render_s": before_seconds, "item_paint_s": paint_seconds})
    canvas.scene().removeItem(item)

    # 1. Raster: "after" is a derived source (the DEM clipped to a zone, as a raster filter writes it), "before" the
    # source it replaced; the clone of the layer takes the former source.
    from osgeo import gdal
    clipped = os.path.join(tempfile.mkdtemp(), "dem_clipped.tif")
    gdal.Warp(clipped, fixtures["dem"], cutlineDSName=fixtures["zones"], cutlineLayer="zones",
              cutlineWhere="name = 'east_a'", cropToCutline=False, dstNodata=-9999)
    dem_after = QgsRasterLayer(clipped, "dem", "gdal")
    project.addMapLayer(dem_after)
    dem_before = dem_after.clone()
    dem_before.setDataSource(fixtures["dem"], "dem", "gdal")
    compare("raster", dem_after, dem_before, dem_before.extent())

    # 1. Point cloud: "after" with a subset (a point cloud filter of FilterMate), "before" its clone without it.
    cloud = QgsPointCloudLayer(fixtures["las"], "cloud", "pdal")
    if not cloud.isValid():
        report("point_cloud", {"valid": False, "error": cloud.error().summary()[:200]})
    else:
        project.addMapLayer(cloud)
        provider = cloud.dataProvider()
        provider.generateIndex()
        indexed = wait(lambda: provider.indexingState() == provider.PointCloudIndexGenerationState.Indexed, 120)
        report("point_cloud_indexed", indexed)
        # The index is a COPC file beside the LAS; the layer opened on the LAS keeps drawing its extent only until it
        # reloads. Open the COPC, as FilterMate works on its point clouds.
        copc = os.path.splitext(fixtures["las"])[0] + ".copc.laz"
        if os.path.exists(copc) and hasattr(QgsPointCloudLayer, "setSubsetString"):
            project.removeMapLayer(cloud.id())
            cloud = QgsPointCloudLayer(copc, "cloud", "copc")
            project.addMapLayer(cloud)
            cloud_before = cloud.clone()
            cloud.setSubsetString('"Classification" = 2')
            wait(lambda: False, 1)  # let the nodes of the index load
            compare("point_cloud", cloud, cloud_before, cloud_before.extent())
        else:
            report("point_cloud", {"copc": os.path.exists(copc), "subset_supported": hasattr(cloud, "setSubsetString")})

    with open(os.path.join(OUT, f"results_{Qgis.QGIS_VERSION_INT}.json"), "w", encoding="utf-8") as stream:
        json.dump(RESULTS, stream, indent=1)
    print("SPIKE DONE", flush=True)
    os._exit(0)


main()
