# -*- coding: utf-8 -*-
"""Local copy of a web service layer, in a real (headless) QGIS, with no network.

    docker run --rm --network none -v "$PWD:/src:ro" qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_stream_copy.py

2026-11-22. A layer of tiles, of a WMS or of a WFS is copied over an area to a file next to the project, and reads it;
the project file keeps the service and finds the copy again when it is read; the layer goes back to its service.
The servers are those of check_stream_extent_clip.py (a WFS 2.0 of 5000 points, a tile server whose tiles say their
level and place by their color, a WMS).

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile
import threading
import time
import zipfile
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import check_stream_extent_clip as fixture  # noqa: E402  (the servers and the plugin link)
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsProject, QgsRasterLayer, QgsRectangle,
)

RESULTS = fixture.RESULTS
check = fixture.check
CRS = QgsCoordinateReferenceSystem("EPSG:3857")


def wait_for(condition, seconds=120.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QgsApplication.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


def copy(actions, layer, area, width=800):
    """Plan the copy of ``layer`` over ``area`` (EPSG:3857), run it to its end; the task."""
    from filter_mate.adapters.qgis import stream_copy
    plan = stream_copy.plan_copy(layer, area, CRS, width)
    if plan.refusal:
        return plan, None
    done = []
    refusal = actions.copy(layer, confirm=False, plan=plan, on_done=done.append)
    if refusal:
        plan.refusal = refusal
        return plan, None
    wait_for(lambda: bool(done), plan.limits.timeout_seconds + 30)
    return plan, (done[0] if done else None)


def project_xml(path):
    with zipfile.ZipFile(path) as archive:
        name = next(name for name in archive.namelist() if name.endswith(".qgs"))
        return archive.read(name).decode("utf-8")


def check_tiles(actions, folder, port):
    from filter_mate.adapters.qgis import stream_copy
    from filter_mate.core.domain import stream_copy as rules
    project = QgsProject.instance()
    uri = f"type=xyz&url=http://127.0.0.1:{port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14&crs=EPSG:3857"
    layer = QgsRasterLayer(uri, "Fond de tuiles", "wms")
    project.addMapLayer(layer)
    layer.renderer().setOpacity(0.6)
    stream_source = layer.source()
    check("tiles: the layer opens and can be copied", layer.isValid() and stream_copy.can_copy(layer),
          layer.isValid())
    area = QgsRectangle(100000, 100000, 300000, 250000)  # 200 km by 150 km
    del fixture.TILES[:]
    plan, task = copy(actions, layer, area)
    check("tiles: planned within the budget, at a level of the service, with its estimate",
          not plan.refusal and plan.columns * plan.rows <= 1_000_000 and plan.estimate is not None
          and plan.estimate.requests > 0 and plan.tiled, (plan.refusal, plan.columns, plan.rows))
    record = stream_copy.record_of(layer)
    copies = os.path.join(folder, "etude_filtermate_local")
    check("tiles: the layer reads its copy, a GeoTIFF next to the project, with its opacity",
          task is not None and record is not None and layer.providerType() == "gdal"
          and os.path.dirname(layer.source()) == copies and layer.source().endswith(".tif")
          and abs(layer.renderer().opacity() - 0.6) < 1e-6,
          (task.result.error if task else None, layer.providerType(), layer.source()))
    from osgeo import gdal
    dataset = gdal.Open(layer.source())
    check("tiles: the copy has the grid of the plan, four bands and overviews",
          dataset is not None and (dataset.RasterXSize, dataset.RasterYSize) == (plan.columns, plan.rows)
          and dataset.RasterCount == 4 and dataset.GetRasterBand(1).GetOverviewCount() > 0,
          dataset and (dataset.RasterXSize, dataset.RasterYSize, dataset.RasterCount))
    dataset = None
    levels = sorted({z for _name, z, _x, _y in fixture.TILES})
    check("tiles: one level only was asked, and complete", len(levels) == 1 and record is not None and record.complete
          and not record.holes, (levels, record))

    path = os.path.join(folder, "etude.qgz")
    check("tiles: the project is written", project.write(path))
    xml = project_xml(path)
    check("tiles: the project file holds the service, not the copy, and the copy relative to the project",
          "etude_filtermate_local" not in xml.split(rules.PROPERTY)[0].split("<customproperties")[0]
          and "127.0.0.1" in xml and "./etude_filtermate_local/" in xml, xml[:300])
    check("tiles: the layer still reads its copy after the save", stream_copy.is_local_copy(layer))

    layer_id = layer.id()
    project.clear()
    check("tiles: the project is read again", project.read(path))
    wait_for(lambda: project.mapLayer(layer_id) is not None, 5)
    again = project.mapLayer(layer_id)
    check("tiles: read again, the layer finds its copy", again is not None and stream_copy.is_local_copy(again)
          and again.providerType() == "gdal", again and (again.providerType(), again.source()))
    if again is None:
        return
    copied = again.source()
    check("tiles: back to the service, the file is kept", actions.back_to_stream(again)
          and again.providerType() == "wms" and not stream_copy.is_local_copy(again)
          and again.customProperty(rules.PROPERTY) is None and os.path.isfile(copied),
          (again.providerType(), again.source()[:120]))
    check("tiles: back on the service, the layer draws it", again.isValid() and "127.0.0.1" in again.source()
          and (again.source() == stream_source or "tiles" in again.source()))


def check_refusals(actions, port):
    from filter_mate.adapters.qgis import stream_copy
    project = QgsProject.instance()
    osm = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0",
                         "OSM", "wms")
    project.addMapLayer(osm)
    plan = stream_copy.plan_copy(osm, QgsRectangle(0, 0, 1000, 1000), CRS, 800)
    check("OpenStreetMap tiles: refused, its terms named", "OpenStreetMap" in plan.refusal, plan.refusal)
    holes = QgsRasterLayer(f"type=xyz&url=http://127.0.0.1:{port}/holes/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
                           "&crs=EPSG:3857", "Trous", "wms")
    project.addMapLayer(holes)
    _plan, task = copy(actions, holes, QgsRectangle(100000, 100000, 300000, 250000))
    record = stream_copy.record_of(holes)
    check("tiles with holes: copied, said incomplete with the holes counted",
          record is not None and not record.complete and record.holes > 0 and record.notes,
          (task and task.result.error, record))
    dead = QgsRasterLayer(f"type=xyz&url=http://127.0.0.1:{port}/dead/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
                          "&crs=EPSG:3857", "Mort", "wms")
    project.addMapLayer(dead)
    plan, task = copy(actions, dead, QgsRectangle(100000, 100000, 300000, 250000))
    check("a dead service: nothing copied, the layer on its service, no file left",
          task is not None and task.result.record is None and dead.providerType() == "wms"
          and not os.path.exists(plan.path), (task and task.result.error, plan.path))
    wms = QgsRasterLayer(f"crs=EPSG:3857&format=image/png&layers=plan&styles=&url=http://127.0.0.1:{port}/wms",
                         "WMS", "wms")
    project.addMapLayer(wms)
    del fixture.MAPS[:]
    plan, task = copy(actions, wms, QgsRectangle(-50000, -50000, 50000, 50000), width=500)
    check("WMS: copied at twice the detail of the screen, in blocks the writer asks",
          task is not None and task.result.record is not None and abs(plan.resolution - 100.0) < 1.0
          and wms.providerType() == "gdal" and len(fixture.MAPS) >= 1,
          (plan.refusal, task and task.result.error, plan.resolution, len(fixture.MAPS)))


def check_export(port):
    """EXPORTING and export_layers write a web map as it draws over the visible map; the layer stays on its service."""
    from osgeo import gdal
    from qgis.utils import iface
    from filter_mate.adapters.qgis.coverage_layers import exporters
    project = QgsProject.instance()
    tiles = QgsRasterLayer(f"type=xyz&url=http://127.0.0.1:{port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
                           "&crs=EPSG:3857", "Tuiles export", "wms")
    project.addMapLayer(tiles)
    folder = tempfile.mkdtemp()
    if iface is None:
        # No map here: the job is planned over an area of the map, as the dock does with the visible one.
        from filter_mate.adapters.qgis import stream_copy
        plan = stream_copy.plan_copy(tiles, QgsRectangle(100000, 100000, 300000, 250000), CRS, 800, with_folder=False)
        job = exporters.WebMapExportJob(tiles, os.path.join(folder, "tuiles.tif"), "COG", plan=plan)
    else:
        job = exporters.raster_export_job(tiles, os.path.join(folder, "tuiles.tif"), "COG")
    done = []
    task = exporters.make_export_task([job], done.extend)
    QgsApplication.taskManager().addTask(task)
    wait_for(lambda: bool(done), 120)
    result = done[0] if done else None
    dataset = gdal.Open(os.path.join(folder, "tuiles.tif")) if result and result.success else None
    check("export task: a web map written as a COG of the plan, the layer still on its service",
          dataset is not None and (dataset.RasterXSize, dataset.RasterYSize) == (job.plan.columns, job.plan.rows)
          and dataset.RasterCount == 4 and tiles.providerType() == "wms" and "still image" in result.message,
          result)
    dataset = None
    direct = job.run(None)  # from the main thread, as export_layers runs it: a worker reads, the loop turns
    check("export from the main thread: the service read off it, the file written", direct.success, direct)
    from filter_mate.adapters.qgis.point_cloud_capability import is_untargetable_raster
    arcgis = QgsRasterLayer("url=https://example.org/arcgis/rest/services/x/MapServer layer=0", "ArcGIS", "arcgismapserver")
    check("an ArcGIS MapServer is still not exported, a web map of tiles is offered",
          not is_untargetable_raster(tiles) and (not arcgis.isValid() or is_untargetable_raster(arcgis)))
    project.removeMapLayer(tiles.id())


def check_agent_tool(port):
    """local_copy as the agent and the REST API call it: over an area, then back; refusals said as errors."""
    from filter_mate.adapters.public_api import stream_copy as tool
    project = QgsProject.instance()
    tiles = QgsRasterLayer(f"type=xyz&url=http://127.0.0.1:{port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
                           "&crs=EPSG:3857", "Tuiles agent", "wms")
    project.addMapLayer(tiles)
    area = "POLYGON((100000 100000, 300000 100000, 300000 250000, 100000 250000, 100000 100000))"
    try:
        answer = tool.local_copy("Tuiles agent", extent_wkt=area, crs="EPSG:3857")
    except ValueError as exc:
        answer = {"error": str(exc)}
    check("agent tool: the layer copied over the area, the answer says what it reads now",
          answer.get("reads") == "local copy" and answer.get("kind") == "image" and answer.get("file", "").endswith(".tif")
          and tiles.providerType() == "gdal", answer)
    try:
        again = tool.local_copy("Tuiles agent", extent_wkt=area, crs="EPSG:3857")
    except ValueError as exc:
        again = {"error": str(exc)}
    check("agent tool: a layer already on its copy is refused with what to do", "action again" in again.get("error", ""),
          again)
    from filter_mate.adapters.qgis import stream_copy
    first = stream_copy.record_of(tiles)
    try:
        renewed = tool.local_copy("Tuiles agent", action="again")
    except ValueError as exc:
        renewed = {"error": str(exc)}
    second = stream_copy.record_of(tiles)
    check("agent tool: again copies the same area anew, at the same detail, the previous file removed",
          renewed.get("reads") == "local copy" and second is not None and first is not None
          and second.path != first.path and not os.path.exists(first.path)
          and abs(second.resolution - first.resolution) <= first.resolution * 0.02
          and tuple(round(v) for v in second.extent) == tuple(round(v) for v in first.extent), renewed)
    back = tool.local_copy("Tuiles agent", action="back")
    check("agent tool: back to the service", back.get("reads") == "service" and tiles.providerType() == "wms", back)
    try:
        tool.local_copy("Tuiles inconnues")
        unknown = ""
    except ValueError as exc:
        unknown = str(exc)
    check("agent tool: an unknown layer is refused", "not found" in unknown, unknown)
    project.removeMapLayer(tiles.id())


def check_wfs(actions, folder):
    from filter_mate.adapters.qgis import stream_copy
    from filter_mate.adapters.qgis.remote_materializer import supports_reply_validation
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.WfsHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    project = QgsProject.instance()
    layer = fixture.wfs_layer(server.server_port, "keyed")
    check("WFS: the layer opens", layer.isValid())
    if not supports_reply_validation():
        plan = stream_copy.plan_copy(layer, QgsRectangle(-5, -5, 405, 205), CRS, 800)
        check("WFS on a QGIS that cannot check a service: refused with its reason", "3.26" in plan.refusal,
              plan.refusal)
        server.shutdown()
        return
    layer.setSubsetString('"num" < 3000')
    area = QgsRectangle(-5, -5, 405, 205)  # 41 x 21 points
    expected = fixture.inside(-5, -5, 405, 205)
    plan, task = copy(actions, layer, area)
    record = stream_copy.record_of(layer)
    check("WFS: the layer reads a GeoPackage next to the project, every feature of the area in it",
          task is not None and record is not None and layer.providerType() == "ogr" and ".gpkg" in layer.source()
          and record.features == len(expected) and record.complete,
          (task and task.result.error, layer.providerType(), record))
    check("WFS: its filter is on the copy", layer.subsetString() == '"num" < 3000'
          and sorted(f["num"] for f in layer.getFeatures()) == [n for n in expected if n < 3000],
          layer.subsetString())
    path = os.path.join(folder, "etude.qgz")
    project.write(path)
    xml = project_xml(path)
    check("WFS: the project file holds the service", f"127.0.0.1:{server.server_port}/wfs" in xml
          and "<provider" in xml and ".gpkg|" not in xml.split("<customproperties")[0], xml[:200])
    check("WFS: back to the service, with its filter", actions.back_to_stream(layer) and layer.providerType() == "WFS"
          and layer.subsetString() == '"num" < 3000', (layer.providerType(), layer.subsetString()))

    # The review of 22 November: the filter set on the copy is the one the project keeps, the one taken off is gone
    # on the service too, and a layer being edited keeps its source.
    copy(actions, layer, area)
    layer.setSubsetString('"num" < 1000')
    project.write(path)
    xml = project_xml(path)
    layer_id = layer.id()
    project.clear()
    project.read(path)
    again = project.mapLayer(layer_id)
    check("WFS: the filter set on the copy is the one the project keeps, and the one read again",
          again is not None and stream_copy.is_local_copy(again) and again.subsetString() == '"num" < 1000'
          and "&quot;num&quot; &lt; 1000" in xml, again and (again.providerType(), again.subsetString()))
    layer = again
    layer.setSubsetString("")
    check("WFS: a filter taken off the copy stays off on the service", actions.back_to_stream(layer)
          and layer.providerType() == "WFS" and layer.subsetString() == "", layer.subsetString())
    copy(actions, layer, area)
    layer.startEditing()
    refused = not actions.back_to_stream(layer)
    check("WFS: a copy being edited does not go back to its service (its edits would go to another provider)",
          refused and stream_copy.is_local_copy(layer), layer.providerType())
    layer.rollBack()
    actions.back_to_stream(layer)

    from filter_mate.config.config import ENV_VARS
    options = ENV_VARS["CONFIG_DATA"]["APP"]["OPTIONS"]
    options["STREAM_COPY"]["max_features"] = {"value": 100}
    _plan, task = copy(actions, layer, area)
    record = stream_copy.record_of(layer)
    check("WFS past the most features: the first ones copied, said incomplete",
          record is not None and record.features == 100 and not record.complete and record.notes,
          (task and task.result.error, record))
    options["STREAM_COPY"]["max_features"] = {"value": 200000}
    server.shutdown()


def check_review(actions, folder, port, server):
    """What the review of 22 November found on web maps: Copy again cancelled or past the budget, a copy clipped by
    another layer, the opacity of a web map opened offline."""
    from qgis.core import QgsGeometry
    from filter_mate.adapters.public_api import operations
    from filter_mate.adapters.qgis import stream_copy
    project = QgsProject.instance()
    wms = QgsRasterLayer(f"crs=EPSG:3857&format=image/png&layers=plan&styles=&url=http://127.0.0.1:{port}/wms",
                         "WMS revu", "wms")
    project.addMapLayer(wms)
    copy(actions, wms, QgsRectangle(-50000, -50000, 50000, 50000), width=500)
    first = stream_copy.record_of(wms)
    actions._ask = lambda title, text, buttons: len(buttons) - 1  # Cancel at the cost of the new copy
    actions.copy_again(wms)
    check("Copy again, cancelled: the layer reads its previous copy", stream_copy.is_local_copy(wms)
          and stream_copy.record_of(wms).path == first.path, wms.providerType())
    actions._ask = lambda title, text, buttons: 0
    done = []
    actions.copy_again(wms)
    task = actions._tasks.get(wms.id())
    if task is not None:
        task.callback = (lambda inner: lambda ended: (inner(ended), done.append(ended)))(task.callback)
    wait_for(lambda: bool(done) or wms.id() not in actions._tasks, 90)
    second = stream_copy.record_of(wms)
    check("Copy again of a WMS: the detail of the first copy, the previous file removed",
          second is not None and abs(second.resolution - first.resolution) <= first.resolution * 0.02
          and not os.path.exists(first.path), (first.resolution, second and second.resolution))

    tiles = QgsRasterLayer(f"type=xyz&url=http://127.0.0.1:{port}/tiles/{{z}}/{{x}}/{{y}}.png&zmin=0&zmax=14"
                           "&crs=EPSG:3857", "Tuiles revues", "wms")
    project.addMapLayer(tiles)
    copy(actions, tiles, QgsRectangle(100000, 100000, 300000, 250000))
    tiles.renderer().setOpacity(0.4)
    triangle = QgsGeometry.fromWkt("POLYGON((120000 120000, 280000 120000, 200000 240000, 120000 120000))")
    report = operations.cross_filter_by_geometry(triangle, CRS, [tiles.id()])
    path = os.path.join(folder, "etude.qgz")
    project.write(path)
    xml = project_xml(path)
    from xml.etree import ElementTree
    written = next((element for element in ElementTree.fromstring(xml).iter("maplayer")
                    if element.findtext("id") == tiles.id()), None)
    datasource = written.findtext("datasource") if written is not None else ""
    check("a copy clipped by another layer: the project holds its service, not the copy nor the clip",
          not report.error and "127.0.0.1" in datasource and ".tif" not in datasource and ".vrt" not in datasource,
          (report.error, datasource[-160:]))
    layer_id = tiles.id()
    server.shutdown()  # offline from here: the service of the web maps no longer answers
    project.clear()
    project.read(path)
    again = project.mapLayer(layer_id)
    check("offline, read again: the layer reads its copy with its opacity",
          again is not None and stream_copy.is_local_copy(again) and again.renderer() is not None
          and abs(again.renderer().opacity() - 0.4) < 1e-6,
          again and (again.providerType(), again.renderer() and again.renderer().opacity()))


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    from filter_mate.config.config import ENV_VARS
    from filter_mate.ui.controllers.stream_copy_actions import StreamCopyActions
    options = ENV_VARS.setdefault("CONFIG_DATA", {}).setdefault("APP", {}).setdefault("OPTIONS", {})
    options["STREAM_COPY"] = {"max_pixels": {"value": 1000000}, "max_features": {"value": 200000},
                              "timeout_seconds": {"value": 60}}
    options.setdefault("RASTER", {})["enabled"] = {"value": True}  # a copy clipped by another layer (check_review)
    from filter_mate.adapters.qgis.coverage_layers import cache
    cache.set_cache_root(tempfile.mkdtemp())
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.MapHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    folder = tempfile.mkdtemp()
    project = QgsProject.instance()
    project.setFileName(os.path.join(folder, "etude.qgz"))
    actions = StreamCopyActions(None)
    actions.start()
    check_tiles(actions, folder, server.server_port)
    project.setFileName(os.path.join(folder, "etude.qgz"))
    check_refusals(actions, server.server_port)
    check_export(server.server_port)
    check_agent_tool(server.server_port)
    check_wfs(actions, folder)
    project.setFileName(os.path.join(folder, "etude.qgz"))
    check_review(actions, folder, server.server_port, server)  # shuts the map server down: last
    actions.stop()


if __name__ == "__main__":
    import logging
    logging.raiseExceptions = False
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    fixture._link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if failed else 0)
