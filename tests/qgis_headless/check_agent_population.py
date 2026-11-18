# -*- coding: utf-8 -*-
"""The population tool of the agent in a real (headless) QGIS: the people of an area brought in as a raster.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_population.py

Without the network: the grid is a VRT over a GeoTIFF on the grid of the real one, served by parts by a server of
this machine, with people where the check put them, so that every total is known. With FM_NET=1 the real grid is
read too: the people of Lyon and of Pune. Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy  # noqa: E402
from osgeo import gdal, osr  # noqa: E402
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsFeature, QgsGeometry, QgsProject, QgsRasterLayer, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QTimer  # noqa: E402

RESULTS = []
LYON = "POLYGON((4.77 45.70, 4.90 45.70, 4.90 45.81, 4.77 45.81, 4.77 45.70))"
GRID = "/hrsl-cogs/hrsl_general/hrsl_general-latest.vrt"
TILE = "/hrsl-cogs/hrsl_general/lyon.tif"
# Where people live in the grid of the check: two towns of 1 person per pixel of the source, inside Lyon.
TOWNS = ((4.80, 45.72, 4.83, 45.75), (4.85, 45.77, 4.88, 45.79))


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:500]}" if not condition else ""), flush=True)


def refused(function, *args, **kwargs):
    """The message of the ValueError ``function`` raises, "" when it raises none."""
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def make_grid(work, source):
    """A GeoTIFF on the grid of ``source`` over 4.6-5.1 E, 45.6-45.9 N, NaN but in TOWNS, its VRT; the bytes of both
    and the people it holds."""
    left, top = source.origin
    step = source.step
    column = int((4.6 - left) / step)
    row = int((top - 45.9) / step)
    width, height = int(0.5 / step), int(0.3 / step)
    west, north = left + column * step, top - row * step
    values = numpy.full((height, width), numpy.nan, dtype="float64")
    for town_west, town_south, town_east, town_north in TOWNS:
        values[int((north - town_north) / step):int((north - town_south) / step),
               int((town_west - west) / step):int((town_east - west) / step)] = 1.0
    path = os.path.join(work, "lyon.tif")
    dataset = gdal.GetDriverByName("GTiff").Create(path, width, height, 1, gdal.GDT_Float64,
                                                   ["TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256", "COMPRESS=DEFLATE"])
    dataset.SetGeoTransform((west, step, 0.0, north, 0.0, -step))
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(4326)
    dataset.SetProjection(reference.ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(float("nan"))
    band.WriteArray(values)
    dataset = None
    vrt = os.path.join(work, "grid.vrt")
    gdal.BuildVRT(vrt, [path])  # names lyon.tif beside it, as the real one names its tiles
    with open(vrt, encoding="utf-8") as stream:
        text = stream.read()
    assert '<SourceFilename relativeToVRT="1">lyon.tif</SourceFilename>' in text, text
    with open(path, "rb") as stream:
        tiff = stream.read()
    return {GRID: text.encode("utf-8"), TILE: tiff}, float(numpy.nansum(values))


def moved(vrt_text):
    """The VRT with its corner half a pixel away: every total read on it would be wrong."""
    start = vrt_text.index("<GeoTransform>") + len("<GeoTransform>")
    end = vrt_text.index("</GeoTransform>")
    values = [float(value) for value in vrt_text[start:end].split(",")]
    values[0] += values[1] / 2
    return vrt_text[:start] + ", ".join(repr(value) for value in values) + vrt_text[end:]


def serve(files, delay):
    """A bucket on this machine: ``files`` by parts, a 404 for the others; what was asked."""
    asked = []

    class Bucket(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def answer(self, body):
            asked.append((self.command, self.path, self.headers.get("Range", "")))
            if delay[0]:
                time.sleep(delay[0])
            data = files.get(self.path)
            if data is None:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            wanted = self.headers.get("Range", "")
            if wanted.startswith("bytes="):
                first, _, last = wanted[6:].partition("-")
                start = int(first or 0)
                end = min(int(last) if last else len(data) - 1, len(data) - 1)
                part = data[start:end + 1]
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            else:
                part = data
                self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(part)))
            self.end_headers()
            if body:
                try:
                    self.wfile.write(part)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the reading was stopped

        def do_GET(self):
            self.answer(True)

        def do_HEAD(self):
            self.answer(False)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Bucket)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, asked


def local_source(port):
    from filter_mate.core.agent import population
    real = population.SOURCES[0]
    return population.PopulationSource(real.id, real.title, f"http://127.0.0.1:{port}", real.path, real.origin,
                                       real.step, real.attribution, real.note)


def check_population(project, work):
    from filter_mate.adapters.agent import bounded_http
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import operations
    from filter_mate.adapters.public_api import population as adapter
    from filter_mate.core.agent import population
    from filter_mate.core.agent.messages import ToolCallPart

    real = population.SOURCES[0]
    files, people = make_grid(work, real)
    delay = [0.0]
    server, asked = serve(files, delay)
    local = local_source(server.server_address[1])
    adapter.known = lambda identifier: local if (identifier or "").strip().lower() == real.id else None
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")

    def written():
        return {name for name in (os.listdir(root) if os.path.isdir(root) else []) if name.startswith("population-")}

    data = QgsVectorLayer("Point?crs=EPSG:4326", "data", "memory")
    project.addMapLayer(data)
    basemap = QgsRasterLayer("type=xyz&url=http://127.0.0.1:9/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0", "fond", "wms")
    project.addMapLayer(basemap, False)
    project.layerTreeRoot().addLayer(basemap)
    try:
        already = written()
        recorder = EffectsRecorder()
        recorder.before_call(ToolCallPart("p1", "add_population", {"extent_wkt": LYON}))
        made = adapter.add_population(extent_wkt=LYON, crs="EPSG:4326")
        recorder.after_call()
        layer = project.mapLayer(made["layer_id"])
        step = real.step * 3
        check("population: a raster on the grid of the source, by blocks of 3 x 3 pixels by default",
              layer.isValid() and layer.providerType() == "gdal" and made["crs_authid"] == "EPSG:4326"
              and layer.crs().authid() == "EPSG:4326" and abs(layer.rasterUnitsPerPixelX() - step) < 1e-12
              and (made["width"], made["height"]) == (layer.width(), layer.height()) == (157, 133)
              and made["resolution"] == "about 65 x 93 m", made)
        check("population: the total is every person of the area, exactly", made["total"] == people
              and made["maximum"] == 9.0, (made, people))
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check("population: under the data, above the basemap", order == [data.id(), layer.id(), basemap.id()], order)
        check("population: named after its pixels, with its attribution and what it is",
              made["name"] == "Population (65 x 93 m)" and layer.metadata().rights() == [real.attribution]
              and made["attribution"] == real.attribution and "census" in made["note"] and "zonalstatisticsfb" in made["note"],
              made)
        kept = written() - already
        check("population: one file kept in the QGIS profile", len(kept) == 1 and os.path.isfile(layer.source())
              and os.path.basename(os.path.dirname(layer.source())) in kept, layer.source())
        ranges = [wanted for command, path, wanted in asked if command == "GET" and path == TILE]
        check("population: the grid is read by parts, never whole", ranges and not [wanted for wanted in ranges if not wanted],
              ranges[:5])
        check("population: drawn", layer.dataProvider().bandStatistics(1).maximumValue == 9.0)
        # The people of a polygon, in another CRS: what the skill says to run.
        sys.path.append("/usr/share/qgis/python/plugins")
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
        zones = QgsVectorLayer("Polygon?crs=EPSG:32631", "zones", "memory")
        whole, first = QgsFeature(), QgsFeature()
        whole.setGeometry(QgsGeometry.fromWkt("POLYGON((620000 5060000, 650000 5060000, 650000 5080000, "
                                              "620000 5080000, 620000 5060000))"))
        first.setGeometry(QgsGeometry.fromWkt("POLYGON((4.79 45.71, 4.84 45.71, 4.84 45.76, 4.79 45.76, 4.79 45.71))"))
        zones.dataProvider().addFeatures([whole])
        counted = processing.run("native:zonalstatisticsfb", {
            "INPUT": zones, "INPUT_RASTER": layer, "RASTER_BAND": 1, "COLUMN_PREFIX": "pop_", "STATISTICS": [1],
            "OUTPUT": "memory:"})["OUTPUT"]
        sums = [feature["pop_sum"] for feature in counted.getFeatures()]
        check("population: native:zonalstatisticsfb sums it in a polygon of another CRS", sums == [people], sums)
        json.dumps(made)
        effects = recorder.finish()
        apply_effects(effects, undo=True)
        check("population: undoing the turn removes the layer", project.mapLayer(made["layer_id"]) is None)
        apply_effects(effects, undo=False)
        back = [found for found in project.mapLayers().values() if found.name() == made["name"]]
        check("population: redoing opens its file again", len(back) == 1 and back[0].isValid())
        project.removeMapLayer(back[0].id())

        for resolution, factor in ((30, 1), (1000, 32)):
            other = adapter.add_population(extent_wkt=LYON, crs="EPSG:4326", resolution=resolution, name="Habitants")
            shown = project.mapLayer(other["layer_id"])
            check(f"population: at {resolution} m, {factor} x {factor} pixels of the source, and the same total",
                  other["total"] == people and other["name"] == "Habitants"
                  and abs(shown.rasterUnitsPerPixelX() - real.step * factor) < 1e-12, other)
            project.removeMapLayer(other["layer_id"])
        # A rectangle that cuts through a town: the total is the people of the area asked, whatever the pixels written
        # (2026-11-18: the sum of the blocks around it, 1.8 to 40 times its surface, with nothing said).
        cut = "POLYGON((4.8105 45.7305, 4.8205 45.7305, 4.8205 45.7405, 4.8105 45.7405, 4.8105 45.7305))"
        cut_bounds = population.snapped(real, (4.8105, 45.7305, 4.8205, 45.7405), 1)
        expected = round((cut_bounds[2] - cut_bounds[0]) / real.step) * round((cut_bounds[3] - cut_bounds[1]) / real.step)
        for resolution in (30, 100, 1000, 10000):
            exact = adapter.add_population(extent_wkt=cut, crs="EPSG:4326", resolution=resolution)
            shown = gdal.Open(project.mapLayer(exact["layer_id"]).source())
            held = float(numpy.nansum(shown.GetRasterBand(1).ReadAsArray()))
            shown = None
            wide = resolution > 100  # blocks of more than 3 pixels: the layer is a good deal wider than the area
            check(f"population: a rectangle in a town, at {resolution} m: the total is the people of the area asked",
                  exact["total"] == expected and exact["asked_km2"] < 1.5 and exact["summed_km2"] < 1.5
                  and (held > expected * 1.5 if wide else held >= expected)
                  and (not wide or "whatever the resolution" in exact["note"]) and "finer" not in exact["note"]
                  and "inside the area" not in exact["note"], (exact, expected, held))
            project.removeMapLayer(exact["layer_id"])
        # The second reading, for the total, fails: the layer is written, its own sum is the total and it is said so.
        second = adapter._sum_pixels

        def broken(*_arguments):
            raise ValueError("the population grid could not be read from its server: boom")
        adapter._sum_pixels = broken
        try:
            after = adapter.add_population(extent_wkt=cut, crs="EPSG:4326", resolution=1000)
        finally:
            adapter._sum_pixels = second
        shown = gdal.Open(project.mapLayer(after["layer_id"]).source())
        held = float(numpy.nansum(shown.GetRasterBand(1).ReadAsArray()))
        shown = None
        check("population: a second reading that fails leaves the total of the layer, said so, and the layer is kept",
              after["total"] == held and "sum of the whole layer" in after["note"]
              and after["summed_km2"] > after["asked_km2"] * 2 and project.mapLayer(after["layer_id"]) is not None, after)
        project.removeMapLayer(after["layer_id"])
        fits = adapter.exact_total_fits
        adapter.exact_total_fits = lambda *_arguments: False  # an area too large to be summed on the pixels of the source
        try:
            rough = adapter.add_population(extent_wkt=cut, crs="EPSG:4326", resolution=1000)
        finally:
            adapter.exact_total_fits = fits
        shown = gdal.Open(project.mapLayer(rough["layer_id"]).source())
        held = float(numpy.nansum(shown.GetRasterBand(1).ReadAsArray()))
        shown = None
        check("population: when the pixels of the source do not fit in a call, the total is the layer's, and the surface "
              "summed and the note say so", rough["total"] == held and rough["summed_km2"] > rough["asked_km2"] * 2
              and "sum of the whole layer" in rough["note"] and len(rough["summed_bounds"]) == 4, rough)
        project.removeMapLayer(rough["layer_id"])
        lambert = adapter.add_population(extent_wkt="POLYGON((838000 6515000, 848000 6515000, 848000 6525000, "
                                                    "838000 6525000, 838000 6515000))", crs="EPSG:2154")
        check("population: an area given in another CRS", lambert["total"] > 0 and lambert["crs_authid"] == "EPSG:4326",
              lambert)
        project.removeMapLayer(lambert["layer_id"])

        count, files_kept = len(project.mapLayers()), written()
        for label, arguments, needle in (
                ("an area too large", {"extent_wkt": "POLYGON((-5 42, 8 42, 8 51, -5 51, -5 42))", "crs": "EPSG:4326"},
                 "50,000 at most"),
                ("a point", {"extent_wkt": "POINT(4.84 45.76)", "crs": "EPSG:4326"}, "a point or a line"),
                ("a CRS written as a definition", {"extent_wkt": LYON, "crs": "+proj=longlat +nadgrids=https://x.org/g"},
                 "unknown CRS"),
                ("a resolution that is no size", {"extent_wkt": LYON, "crs": "EPSG:4326", "resolution": -5},
                 "size in metres"),
                ("an area where nobody lives",
                 {"extent_wkt": "POLYGON((4.95 45.82, 5.0 45.82, 5.0 45.86, 4.95 45.86, 4.95 45.82))", "crs": "EPSG:4326"},
                 "no people"),
                ("an area the grid does not cover, never said empty",
                 {"extent_wkt": "POLYGON((10 10, 10.1 10, 10.1 10.1, 10 10.1, 10 10))", "crs": "EPSG:4326"},
                 "does not cover this area")):
            said = refused(adapter.add_population, **arguments)
            check(f"refused: {label}, nothing added nor kept", needle in said and len(project.mapLayers()) == count
                  and written() == files_kept, said)
        for label, platform, needle in (("a platform of another kind", "copernicus_dem", "holds no population"),
                                        ("a platform that is not of the list", "worldpop", "not a population source")):
            said = refused(adapter.add_population, platform, LYON, "EPSG:4326")
            check(f"refused: {label}", needle in said, said)

        # Half of the area out of the grid (east of 5.1): its people are not counted, and that is said.
        half = adapter.add_population(extent_wkt="POLYGON((4.85 45.70, 5.35 45.70, 5.35 45.81, 4.85 45.81, 4.85 45.70))",
                                      crs="EPSG:4326")
        check("population: the share of an area out of the grid is said", "% of the area is outside the grid" in half["note"]
              and 40 <= int(half["note"].split("about ")[-1].split(" %")[0]) <= 60, half["note"])
        project.removeMapLayer(half["layer_id"])
        files_kept = written()
        # A grid that is not what the module counts on is refused before a pixel is read.
        for label, change, needle in (
                ("a VRT that names a file of this machine",
                 lambda text: text.replace('relativeToVRT="1">lyon.tif', 'relativeToVRT="0">/etc/hostname'),
                 "not its own"),
                ("a VRT that names an address", lambda text: text.replace(
                    'relativeToVRT="1">lyon.tif', 'relativeToVRT="1">/vsicurl/http://127.0.0.1:9/a.tif'), "not its own"),
                ("a grid whose pixels moved", lambda text: moved(text), "changed its pixels")):
            sound = files[GRID]
            files[GRID] = change(sound.decode("utf-8")).encode("utf-8")
            gdal.VSICurlClearCache()
            said = refused(adapter.add_population, extent_wkt=LYON, crs="EPSG:4326")
            files[GRID] = sound
            check(f"refused: {label}, nothing added nor kept", needle in said and len(project.mapLayers()) == count
                  and written() == files_kept, said)
        gdal.VSICurlClearCache()

        delay[0] = 1.5
        busy = []
        stop = QTimer()
        stop.setSingleShot(True)
        stop.timeout.connect(lambda: (busy.append(operations.busy_reason()), bounded_http.abort_active()))
        stop.start(300)
        started = time.monotonic()
        gdal.VSICurlClearCache()
        said = refused(adapter.add_population, extent_wkt=LYON, crs="EPSG:4326")
        waited = time.monotonic() - started
        stop.stop()
        delay[0] = 0.0
        check("server: Stop ends the reading, nothing added nor kept", said == "stopped" and waited < 8
              and len(project.mapLayers()) == count and written() == files_kept, (said, round(waited, 1)))
        check("server: FilterMate is busy during the reading, and free again after the Stop",
              busy and "add_population" in busy[0] and operations.busy_reason() == "", (busy, operations.busy_reason()))
        check("server: the Test of the Sources tab", adapter.check_population(real.id)["status"] == 200)
        missing = dict(files)
        files.pop(GRID)
        gdal.VSICurlClearCache()
        said = refused(adapter.add_population, extent_wkt=LYON, crs="EPSG:4326")
        files.update(missing)
        check("server: a grid that is not there is said so, without its address",
              "could not be read from its server" in said and "127.0.0.1" not in said and written() == files_kept, said)
        server.shutdown()
        server.server_close()
        gdal.VSICurlClearCache()
        said = refused(adapter.check_population, real.id)
        check("server: one that does not answer fails its Test", "could not be read" in said, said)
    finally:
        adapter.known = population.known
        project.removeAllMapLayers()
        for name in written():
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def check_density(project):
    """A density computed by the agent on a layer in degrees: $area is in square metres, on the ellipsoid."""
    from filter_mate.adapters.public_api import fields_joins
    zones = QgsVectorLayer("Polygon?crs=EPSG:4326&field=pop_sum:double", "zones_degres", "memory")
    feature = QgsFeature(zones.fields())
    feature.setGeometry(QgsGeometry.fromWkt("POLYGON((4.8 45.7, 4.9 45.7, 4.9 45.8, 4.8 45.8, 4.8 45.7))"))
    feature["pop_sum"] = 87_600.0
    zones.dataProvider().addFeatures([feature])
    project.addMapLayer(zones)
    try:
        answer = fields_joins.add_field(zones.id(), "density", "decimal", formula='"pop_sum" / ($area / 1000000)')
        density = next(zones.getFeatures())["density"]
        # 0.1 x 0.1 degree at 45.75 N: about 77.8 x 11.1 km = 86.8 km2, so about 1,009 people per km2.
        check("density: $area is in square metres on a layer in degrees", answer.get("computed") == 1
              and 990 < density < 1030, (answer, density))
        fields_joins.add_field(zones.id(), "perimeter_km", "decimal", formula="$perimeter / 1000")
        check("density: $perimeter in metres too", 37 < next(zones.getFeatures())["perimeter_km"] < 40)
    finally:
        zones.rollBack()
        project.removeMapLayer(zones.id())


def check_tools(project, work):
    """The chat tool, on the real accessor: what a model sends, and what it reads back."""
    from filter_mate.adapters.public_api import population as adapter
    from filter_mate.core.agent import population
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor

    class PublicApi:
        @staticmethod
        def get_active_filters():
            return {}

    real = population.SOURCES[0]
    files, people = make_grid(work, real)
    server, _asked = serve(files, [0.0])
    local = local_source(server.server_address[1])
    adapter.known = lambda identifier: local if (identifier or "").strip().lower() == real.id else None
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    accessor = QGISFilterMateAccessor(PublicApi(), None)

    def tools(platforms):
        executor = ToolExecutor(chat_tools(), build_handlers(accessor, os.path.join(work, "exports"), platforms=platforms))

        def tool(tool_name, /, **arguments):
            result = executor.execute(ToolCallPart("c", tool_name, arguments))
            return result.is_error, result.content
        return tool

    try:
        gdal.VSICurlClearCache()
        tool = tools(["meta_population"])
        error, content = tool("add_population", extent_wkt=LYON, crs="EPSG:4326", name="Habitants")
        made = {} if error else json.loads(content)
        check("tool add_population", not error and made["name"] == "Habitants" and made["total"] == people
              and made["platform"] == "meta_population", content)
        check("tool add_population: the address of the server is not in the answer", "127.0.0.1" not in content, content)
        error, content = tool("set_layer_style", layer="Habitants", mode="pseudocolor", ramp="Magma", cut=2)
        check("tool set_layer_style: a ramp over the people", not error and json.loads(content)["mode"] == "pseudocolor",
              content)
        error, content = tool("add_population", extent_wkt=LYON, crs="EPSG:4326", platform="copernicus_dem")
        check("tool add_population: a source that is not ticked", error and "not enabled" in content, content)
        error, content = tools([])("add_population", extent_wkt=LYON, crs="EPSG:4326")
        check("tool add_population: refused when no population source is ticked", error and "not enabled" in content,
              content)
        error, content = tool("add_population", extent_wkt=LYON, crs="EPSG:4326", resolution=5)
        check("tool add_population: a resolution finer than the source is refused by the schema", error, content)
    finally:
        adapter.known = population.known
        server.shutdown()
        server.server_close()
        project.removeAllMapLayers()
        for name in (os.listdir(root) if os.path.isdir(root) else []):
            if name.startswith("population-"):
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def check_live(project):
    """The real grid: the people of Lyon, of Pune."""
    from filter_mate.adapters.public_api import population as adapter

    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    gdal.VSICurlClearCache()
    for label, wkt, resolution, low, high in (
            ("Lyon", LYON, None, 600_000, 1_200_000),
            ("Pune", "POLYGON((73.75 18.43, 73.98 18.43, 73.98 18.63, 73.75 18.63, 73.75 18.43))", 1000,
             4_000_000, 8_000_000)):
        started = time.monotonic()
        try:
            made = adapter.add_population(extent_wkt=wkt, crs="EPSG:4326", resolution=resolution)
        except ValueError as exc:
            check(f"live: the people of {label}", False, exc)
            continue
        seconds = time.monotonic() - started
        check(f"live: the people of {label}", low < made["total"] < high, made)
        print(f"INFO live: {made['total']:,} people in {label}, {made['width']} x {made['height']} pixels of "
              f"{made['resolution']}, read in {seconds:.1f} s", flush=True)
    said = refused(adapter.add_population, extent_wkt="POLYGON((116.2 39.8, 116.6 39.8, 116.6 40.1, 116.2 40.1, 116.2 39.8))",
                   crs="EPSG:4326")
    check("live: Beijing, out of the grid, is said not covered, never empty", "does not cover" in said, said)
    project.removeAllMapLayers()
    for name in (os.listdir(root) if os.path.isdir(root) else []):
        if name.startswith("population-"):
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}, GDAL {gdal.__version__}", flush=True)
    work = tempfile.mkdtemp()
    project = QgsProject.instance()
    check_population(project, work)
    check_density(project)
    check_tools(project, work)
    if os.environ.get("FM_NET") == "1":
        check_live(project)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
