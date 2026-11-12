#!/usr/bin/env python3
"""Compare mode on real data: the cost of rendering the state before a filter, at 1920 x 1080.

Follows scripts/spikes/compare_render.py (the method). Each case renders the layer as it is filtered ("after") and a
clone of it in the state before ("before"), twice each (the second render is the one a user would wait for once the
data are in the caches of the system), and writes the seconds as JSON lines.

    python-qgis compare_real_data.py OUT BDTOPO_GPKG MNT_TIF COPC [COMMUNE]

BDTOPO_GPKG: a BD TOPO GeoPackage (layers batiment and commune); MNT_TIF: a DEM; COPC: a LiDAR HD tile.
"""
import json
import os
import sys
import tempfile
import time

from qgis.core import (
    Qgis, QgsApplication, QgsMapRendererParallelJob, QgsMapSettings, QgsPointCloudLayer, QgsProject, QgsRasterLayer,
    QgsRectangle, QgsVectorLayer,
)

APP = QgsApplication([], True)  # a GUI application: without it a render job draws nothing
APP.initQgis()

from qgis.PyQt.QtCore import QSize  # noqa: E402
from qgis.PyQt.QtGui import QColor  # noqa: E402

OUT, GPKG, MNT, COPC = sys.argv[1:5]
COMMUNE = sys.argv[5] if len(sys.argv) > 5 else "Toulouse"
SIZE = QSize(1920, 1080)
RESULTS = {"qgis": Qgis.QGIS_VERSION, "size": [SIZE.width(), SIZE.height()]}


def report(key, value):
    RESULTS[key] = value
    print(json.dumps({key: value}), flush=True)


def render(layer, extent):
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
    return job.renderedImage(), round(time.perf_counter() - started, 3)


def drawn(image):
    """Share of sampled pixels that are not the white background: a render that drew nothing measures nothing."""
    white = QColor("white").rgb()
    samples = hits = 0
    for y in range(0, image.height(), 8):
        for x in range(0, image.width(), 8):
            samples += 1
            hits += image.pixel(x, y) != white
    return round(hits / samples, 4)


def wait(seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        QgsApplication.processEvents()
        time.sleep(0.01)


def case(name, after, before, extent):
    """Render after and before twice each; keep the second, the one a user waits for, and what each drew."""
    timings = {}
    for label, layer in (("after", after), ("before", before)):
        image, first = render(layer, extent)
        image, second = render(layer, extent)
        image.save(os.path.join(OUT, f"real_{name}_{label}.png"))
        timings[label] = {"first_s": first, "second_s": second, "drawn": drawn(image)}
    report(name, timings)


def main():
    project = QgsProject.instance()

    # Buildings of a department (BD TOPO): after = the tall ones, before = all of them.
    communes = QgsVectorLayer(f"{GPKG}|layername=commune", "commune", "ogr")
    batiment = QgsVectorLayer(f"{GPKG}|layername=batiment", "batiment", "ogr")
    project.addMapLayers([communes, batiment])
    report("batiment_features", batiment.featureCount())
    # The style the BD TOPO GeoPackage carries shows the buildings from 1:25,000 only: measure them at every scale.
    batiment.setScaleBasedVisibility(False)
    commune_extent = next(communes.getFeatures(f"\"nom_officiel\" = '{COMMUNE}'")).geometry().boundingBox()
    before = batiment.clone()
    batiment.setSubsetString('"hauteur" > 15')
    case("batiment_commune", batiment, before, commune_extent)
    case("batiment_department", batiment, before, batiment.extent())

    # DEM: after = clipped to the centre quarter (a derived file, as a raster filter writes it), before = the source.
    from osgeo import gdal
    dem = QgsRasterLayer(MNT, "mnt", "gdal")
    box = dem.extent()
    quarter = QgsRectangle(box.xMinimum() + box.width() / 4, box.yMinimum() + box.height() / 4,
                           box.xMaximum() - box.width() / 4, box.yMaximum() - box.height() / 4)
    clipped = os.path.join(tempfile.mkdtemp(), "mnt_clip.tif")
    gdal.Translate(clipped, MNT, projWin=[quarter.xMinimum(), quarter.yMaximum(), quarter.xMaximum(), quarter.yMinimum()])
    dem_after = QgsRasterLayer(clipped, "mnt", "gdal")
    project.addMapLayer(dem_after)
    dem_before = dem_after.clone()
    dem_before.setDataSource(MNT, "mnt", "gdal")
    case("mnt", dem_after, dem_before, box)

    # LiDAR HD tile (COPC): after = the buildings (class 6), before = every point.
    cloud = QgsPointCloudLayer(COPC, "lidar", "copc")
    project.addMapLayer(cloud)
    report("lidar_points", cloud.pointCount())
    wait(5)  # the hierarchy of the COPC loads in the background: a render before draws its extent only
    cloud_before = cloud.clone()
    cloud.setSubsetString('"Classification" = 6')
    tile = cloud_before.extent()
    case("lidar_tile", cloud, cloud_before, tile)
    centre = QgsRectangle(tile.center().x() - 100, tile.center().y() - 60, tile.center().x() + 100, tile.center().y() + 60)
    case("lidar_200m", cloud, cloud_before, centre)

    with open(os.path.join(OUT, f"real_results_{Qgis.QGIS_VERSION_INT}.json"), "w", encoding="utf-8") as stream:
        json.dump(RESULTS, stream, indent=1)
    print("REAL DONE", flush=True)
    os._exit(0)


main()
