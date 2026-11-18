# -*- coding: utf-8 -*-
"""The terrain tools of the agent in a real (headless) QGIS: elevation brought in, contours, hillshade, blending.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_terrain.py

Without the network: the tiles of the elevation model are served by a server of this machine that answers by parts,
as the real one does. With FM_NET=1 the real servers are asked too: the elevation of Lyon from Copernicus, and a tile
of every satellite basemap. Prints one PASS / FAIL line per check; exits with 1 when one failed.
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
    Qgis, QgsApplication, QgsColorRampShader, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry,
    QgsMapRendererSequentialJob,
    QgsMapSettings, QgsPalLayerSettings, QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QSize, QTimer  # noqa: E402
from qgis.PyQt.QtGui import QPainter  # noqa: E402

RESULTS = []
LYON = "POLYGON((4.78 45.70, 4.92 45.70, 4.92 45.80, 4.78 45.80, 4.78 45.70))"
TILE = "/Copernicus_DSM_COG_10_N45_00_E004_00_DEM/Copernicus_DSM_COG_10_N45_00_E004_00_DEM.tif"


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""), flush=True)


def refused(function, *args, **kwargs):
    """The message of the ValueError ``function`` raises, "" when it raises none."""
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def make_dem(path, epsg, origin, pixel, size=200, bands=1, slope=3.0, factor=1, nodata=False):
    """A cone: 500 at the middle, ``slope`` lower per pixel away from it (76 at the corners of 200 pixels).
    ``factor``: stored as whole numbers of 1/factor, with that scale. ``nodata``: every pixel is no data."""
    kind = gdal.GDT_Int16 if factor != 1 else gdal.GDT_Float32
    dataset = gdal.GetDriverByName("GTiff").Create(path, size, size, bands, kind)
    dataset.SetGeoTransform((origin[0], pixel, 0, origin[1], 0, -pixel))
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(epsg)
    dataset.SetProjection(reference.ExportToWkt())
    rows, columns = numpy.mgrid[0:size, 0:size]
    cone = (500 - numpy.hypot(columns - size / 2, rows - size / 2) * slope).astype("float32")
    for band in range(1, bands + 1):
        if factor != 1:
            dataset.GetRasterBand(band).WriteArray(numpy.round(cone * factor).astype("int16"))
            dataset.GetRasterBand(band).SetScale(1.0 / factor)
        elif nodata:
            dataset.GetRasterBand(band).SetNoDataValue(-9999)
            dataset.GetRasterBand(band).Fill(-9999)
        else:
            dataset.GetRasterBand(band).WriteArray(cone)
    dataset.FlushCache()
    del dataset


def colours(layers, extent, crs):
    """How many colours these layers draw over an extent: one means nothing was drawn."""
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(QgsCoordinateReferenceSystem(crs))
    settings.setExtent(extent)
    settings.setOutputSize(QSize(256, 256))
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    del job
    # The job ends its inner job by a deferred deletion: done here, while its layers are still there (a tool that
    # lets the event loop turn after they were removed would run it then, and QGIS crashed in the label engine).
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return len({image.pixel(x, y) for x in range(0, 256, 8) for y in range(0, 256, 8)})


def rules_of(layer):
    """``(condition, width, colour, is the rule of the others)`` of each rule of a layer drawn by rules.

    Read on a copy of the renderer, and nothing of it kept: QGIS 3.22 corrupts its heap when the wrappers of the
    rules or of the symbols of the renderer a layer holds are freed (seen on 2026-11-15, at the end of a function).
    """
    renderer = layer.renderer().clone()
    if renderer.type() != "RuleRenderer":
        return []
    return [(rule.filterExpression(), round(rule.symbol().width(), 3), rule.symbol().color().name(), rule.isElse())
            for rule in renderer.rootRule().children()]


def symbol_of(layer):
    """``(width or size, outline width, colour)`` of the one symbol of a layer, read on a copy of its renderer."""
    renderer = layer.renderer().clone()  # kept until the end: the symbol is its own
    symbol = renderer.symbol()
    size = symbol.width() if hasattr(symbol, "width") else symbol.size() if hasattr(symbol, "size") else None
    part = symbol.symbolLayer(0)
    outline = part.strokeWidth() if hasattr(part, "strokeWidth") else None
    return size, outline, symbol.color().name()


def raster_look(layer):
    """What a raster is drawn with, as plain values read on a copy of its renderer."""
    renderer = layer.renderer().clone()
    look = {"type": renderer.type()}
    if renderer.type() == "hillshade":
        look.update(azimuth=renderer.azimuth(), altitude=renderer.altitude(), z_factor=renderer.zFactor(),
                    multidirectional=renderer.multiDirectional())
    elif renderer.type() == "singlebandpseudocolor":
        shader = renderer.shader().rasterShaderFunction()
        # The bound of the shader: a copy of the renderer does not carry classificationMin (it reads nan).
        look.update(minimum=shader.minimumValue(), items=len(shader.colorRampItemList()),
                    discrete=shader.colorRampType() == QgsColorRampShader.Type.Discrete)
    return look


def check_contours(project, work):
    from filter_mate.adapters.public_api import terrain
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    path = os.path.join(work, "dem.tif")
    make_dem(path, 32631, (640000, 5070000), 30)
    dem = QgsRasterLayer(path, "dem")
    points = QgsVectorLayer("Point?crs=EPSG:32631&field=nom:string", "points", "memory")
    project.addMapLayers([dem, points])
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("t1", "contour_lines", {"layer": "dem"}))
    made = terrain.contour_lines("dem", 25, index_interval=100)
    recorder.after_call()
    layer = project.mapLayer(made["layer_id"])
    heights = sorted(feature["elevation"] for feature in layer.getFeatures())
    index = sorted(feature["elevation"] for feature in layer.getFeatures() if feature["is_index"] == 1)
    check("contours: a line layer in the CRS of the raster, one level every 25",
          layer.isValid() and layer.crs().authid() == "EPSG:32631" and made["crs_authid"] == "EPSG:32631"
          and made["feature_count"] == layer.featureCount() == len(heights) and set(heights) == set(range(100, 500, 25))
          and made["minimum"] == 100 and made["maximum"] == 475, (made, heights))
    # The cone ends in a ring of a few metres at 500: a bump smaller than ten pixels, left out and counted.
    check("contours: a closed contour of a few pixels is left out, and said so", made["left_out"] == 1, made)
    check("contours: the index contours are the multiples of 100", index and all(height % 100 == 0 for height in index)
          and made["index_count"] == len(index) and set(index) == {100, 200, 300, 400}
          and made["fields"] == ["elevation", "is_index"], (made, index))
    rules = rules_of(layer)
    check("contours: drawn thin, the index contours thicker", len(rules) == 2
          and rules[0][:2] == ('"is_index" = 1', terrain.INDEX_WIDTH) and rules[1][1] == terrain.CONTOUR_WIDTH
          and rules[1][3], rules)
    order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
    check("contours: on top of the project, named after the raster", order[0] == layer.id()
          and made["name"] == "Contours 25" and made["source_layer"] == "dem", (order, made))
    check("contours: drawn", colours([layer], dem.extent(), "EPSG:32631") > 1)
    json.dumps(made)
    effects = recorder.finish()
    apply_effects(effects, undo=True)
    check("contours: undoing the turn removes the layer", project.mapLayer(made["layer_id"]) is None)
    apply_effects(effects, undo=False)
    again = [found for found in project.mapLayers().values() if found.name() == "Contours 25"]
    check("contours: redoing brings it back with its lines", len(again) == 1 and again[0].featureCount() == len(heights),
          [found.name() for found in project.mapLayers().values()])
    project.removeMapLayer(again[0].id())

    plain = terrain.contour_lines("dem", 50, name="Courbes")
    layer = project.mapLayer(plain["layer_id"])
    check("contours: without an index interval, one symbol and no index contour",
          layer.renderer().type() == "singleSymbol" and symbol_of(layer)[0] == terrain.CONTOUR_WIDTH
          and plain["index_count"] == 0 and plain["index_interval"] is None
          and plain["name"] == "Courbes" and all(feature["is_index"] == 0 for feature in layer.getFeatures()), plain)
    project.removeMapLayer(layer.id())
    every = terrain.contour_lines("dem", 25, index_interval=100, min_length=0)
    check("contours: a minimum length of zero keeps every contour", every["left_out"] == 0
          and every["maximum"] == 500 and every["feature_count"] == made["feature_count"] + 1, every)
    project.removeMapLayer(every["layer_id"])
    wide = terrain.contour_lines("dem", 25, min_length=3000)
    check("contours: a minimum length asked leaves the smaller closed contours out, never the open ones",
          wide["left_out"] > 1 and wide["minimum"] == 100 and wide["feature_count"] < made["feature_count"], wide)
    project.removeMapLayer(wide["layer_id"])
    count = len(project.mapLayers())
    for label, call, needle in (
            ("a minimum length below zero", lambda: terrain.contour_lines("dem", 25, min_length=-1), "min_length"),
            ("an interval of zero", lambda: terrain.contour_lines("dem", 0), "above zero"),
            ("an index interval that is no multiple", lambda: terrain.contour_lines("dem", 25, index_interval=60), "multiple"),
            ("too many levels", lambda: terrain.contour_lines("dem", 0.5), "more than 500 levels"),
            ("an interval above the heights", lambda: terrain.contour_lines("dem", 1000), "no contour every 1000"),
            ("a vector layer", lambda: terrain.contour_lines("points", 25), "not a raster with elevation values"),
            ("a band it does not have", lambda: terrain.contour_lines("dem", 25, band=2), "bands 1 to 1"),
            ("an unknown layer", lambda: terrain.contour_lines("nope", 25), "not found")):
        said = refused(call)
        check(f"contours: {label} is refused, nothing added", needle in said and len(project.mapLayers()) == count, said)
    quiet = refused(terrain.contour_lines, "dem", 0.5, share_values=False)
    check("contours: a refusal names no height of the raster when its values are not shared",
          "more than 500 levels over the heights of this raster" in quiet and "between" not in quiet
          and "75" not in quiet, quiet)
    quiet = refused(terrain.contour_lines, "dem", 1000, share_values=False)
    check("contours: nor when no contour is found", quiet.startswith("no contour every 1000")
          and "between" not in quiet, quiet)
    hidden = terrain.contour_lines("dem", 50, share_values=False)
    check("contours: nor in the answer", hidden["minimum"] is None and hidden["maximum"] is None
          and hidden["feature_count"] > 3, hidden)
    project.removeMapLayer(hidden["layer_id"])
    # Whole numbers of tenths of metres, as many elevation files are stored: the heights are those QGIS shows.
    tenths = os.path.join(work, "tenths.tif")
    make_dem(tenths, 32631, (640000, 5070000), 30, factor=10)
    scaled = QgsRasterLayer(tenths, "tenths")
    project.addMapLayer(scaled)
    drawn = terrain.contour_lines("tenths", 25, index_interval=100)
    heights = {feature["elevation"] for feature in project.mapLayer(drawn["layer_id"]).getFeatures()}
    check("contours: a raster stored with a scale is read through it", heights == set(range(100, 500, 25))
          and drawn["minimum"] == 100 and drawn["maximum"] == 475 and drawn["index_count"] >= 4, (drawn, sorted(heights)))
    project.removeMapLayers([drawn["layer_id"], scaled.id()])
    empty = os.path.join(work, "empty.tif")
    make_dem(empty, 32631, (640000, 5070000), 30, nodata=True)
    nothing = QgsRasterLayer(empty, "empty")
    project.addMapLayer(nothing)
    said = refused(terrain.contour_lines, "empty", 25)
    check("contours: a raster with no value is said so", said == "the raster holds no value to draw contours from", said)
    project.removeMapLayer(nothing.id())
    limit = terrain.MAX_CONTOUR_PIXELS
    terrain.MAX_CONTOUR_PIXELS = 1000
    said = refused(terrain.contour_lines, "dem", 25)
    terrain.MAX_CONTOUR_PIXELS = limit
    check("contours: a raster too large is refused", "200 x 200 pixels" in said, said)
    return dem, points


def check_style(project, dem, points, work):
    from filter_mate.adapters.public_api import layer_style as style, terrain
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    modes = QPainter.CompositionMode
    dem.setBlendMode(modes.CompositionMode_Screen)  # not the default: an undo must bring this one back
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("s1", "set_layer_style", {"layer": "dem"}))
    before = dem.renderer().type()
    shaded = style.set_layer_style("dem", "hillshade", multidirectional=True, blend="multiply", opacity=0.4)
    check("style: a hillshade, lit from the north-west, multiplied over what is under",
          raster_look(dem) == {"type": "hillshade", "azimuth": 315, "altitude": 45, "z_factor": 1.0,
                               "multidirectional": True} and shaded["z_factor"] == 1.0
          and dem.blendMode() == modes.CompositionMode_Multiply and shaded["blend"] == "multiply"
          and abs(dem.opacity() - 0.4) < 1e-6 and (shaded["azimuth"], shaded["altitude"]) == (315.0, 45.0), shaded)
    check("style: the hillshade is drawn", colours([dem], dem.extent(), "EPSG:32631") > 8)
    check("style: a hillshade is blended between its pixels when the map is closer than they are",
          dem.resampleFilter().zoomedInResampler() is not None
          and dem.resampleFilter().zoomedInResampler().type() == "cubic", dem.resampleFilter().zoomedInResampler())
    kept = style.set_layer_style("dem", "keep", blend="overlay")
    check("style: the blending alone changes with keep", dem.renderer().type() == "hillshade"
          and dem.blendMode() == modes.CompositionMode_Overlay and abs(dem.opacity() - 0.4) < 1e-6
          and kept == {"layer_name": "dem", "mode": "keep", "blend": "overlay"}, kept)
    effects = recorder.finish()
    apply_effects(effects, undo=True)
    check("style: undoing the turn brings the renderer, the opacity and the blending back",
          dem.renderer().type() == before and dem.blendMode() == modes.CompositionMode_Screen
          and abs(dem.opacity() - 1.0) < 1e-6, (dem.renderer().type(), dem.blendMode(), dem.opacity()))
    apply_effects(effects, undo=False)
    check("style: redoing draws the hillshade again, blended as the turn left it",
          dem.renderer().type() == "hillshade" and dem.blendMode() == modes.CompositionMode_Overlay)
    style.set_layer_style("dem", "keep", blend="normal")
    check("style: normal covers again", dem.blendMode() == modes.CompositionMode_SourceOver)
    for label, arguments, needle in (
            ("keep with nothing to change", {"mode": "keep"}, "give opacity or blend"),
            ("an unknown blending", {"mode": "keep", "blend": "burn"}, "blend is one of"),
            ("a light under the horizon", {"mode": "hillshade", "altitude": 120}, "altitude goes from 0 to 90"),
            ("a z factor of zero", {"mode": "hillshade", "z_factor": 0}, "z_factor is above 0"),
            ("a cut of half the values", {"mode": "pseudocolor", "cut": 50}, "cut is a percentage"),
            ("a band it does not have", {"mode": "hillshade", "band": 3}, "bands 1 to 1")):
        said = refused(style.set_layer_style, "dem", **arguments)
        check(f"style: {label} is refused", needle in said, said)

    whole = style.set_layer_style("dem", "pseudocolor", ramp="Spectral", invert=True)
    cut = style.set_layer_style("dem", "pseudocolor", ramp="Spectral", invert=True, cut=2)
    check("style: a cut leaves the extreme values out of the ramp",
          whole["minimum"] < cut["minimum"] < cut["maximum"] < whole["maximum"]
          and abs(raster_look(dem)["minimum"] - cut["minimum"]) < 1e-3, (raster_look(dem), whole, cut))
    floor = style.set_layer_style("dem", "pseudocolor", minimum=0, cut=2)
    check("style: a bound given is kept, the other is cut", floor["minimum"] == 0 and floor["maximum"] == cut["maximum"],
          floor)
    steps = style.set_layer_style("dem", "pseudocolor", ramp="Viridis", discrete=True, classes=8, cut=2)
    look = raster_look(dem)
    check("style: flat steps of colour", steps["classes"] == 8 and look["items"] == 8 and look["discrete"],
          (steps, look))
    continuous = style.set_layer_style("dem", "pseudocolor", ramp="Viridis")
    check("style: a continuous ramp tells no class", "classes" not in continuous
          and not raster_look(dem)["discrete"], continuous)
    tints = style.set_layer_style("dem", "pseudocolor", ramp="terrain", cut=2)
    check("style: the tints of a relief map, a ramp of FilterMate", tints["ramp"] == "Terrain"
          and raster_look(dem)["items"] >= 6 and colours([dem], dem.extent(), "EPSG:32631") > 8, (tints, raster_look(dem)))
    said = refused(style.set_layer_style, "dem", "pseudocolor", ramp="nope")
    check("style: an unknown ramp is refused, Terrain among those named", "Terrain" in said and "Viridis" in said, said)
    gray = style.set_layer_style("dem", "gray", cut=5)
    check("style: a gray stretch takes a cut too", gray["minimum"] > whole["minimum"], gray)

    degrees = os.path.join(work, "degrees.tif")
    make_dem(degrees, 4326, (4.0, 46.0), 0.0003)
    geographic = QgsRasterLayer(degrees, "degrees")
    project.addMapLayer(geographic)
    flat = style.set_layer_style("degrees", "hillshade")
    check("style: heights in metres over a grid in degrees are scaled", abs(flat["z_factor"] - 1 / 111320) < 1e-9
          and colours([geographic], geographic.extent(), "EPSG:4326") > 8, flat)
    project.removeMapLayer(geographic.id())

    contours = project.mapLayer(terrain.contour_lines("dem", 25, index_interval=100)["layer_id"])
    ruled = style.set_layer_style(contours.id(), "rules", rules=[
        {"expression": '"is_index" = 1', "color": "#5b3a1e", "label": "100 m", "width": 0.6},
        {"color": "#a67c52", "label": "25 m", "width": 0.15}])
    rules = rules_of(contours)
    check("style: a width per rule", ruled["classes"] == 2 and [rule[1:3] for rule in rules]
          == [(0.6, "#5b3a1e"), (0.15, "#a67c52")], rules)
    style.set_layer_style(contours.id(), "single", color="black", width=1.2)
    check("style: the width of one symbol, a line", symbol_of(contours)[0] == 1.2, symbol_of(contours))
    style.set_layer_style("points", "single", color="red", width=4)
    check("style: the width of a point is its size", symbol_of(points)[0] == 4, symbol_of(points))
    polygons = QgsVectorLayer("Polygon?crs=EPSG:32631", "polygons", "memory")
    project.addMapLayer(polygons)
    style.set_layer_style("polygons", "single", color="green", width=0.8)
    check("style: the width of a polygon is its outline", symbol_of(polygons)[1] == 0.8, symbol_of(polygons))
    project.removeMapLayer(polygons.id())
    said = refused(style.set_layer_style, contours.id(), "rules", rules=[{"color": "red", "width": 50}])
    check("style: a width out of range is refused", "width goes up to 20" in said, said)
    style.set_layer_style(contours.id(), "keep", blend="multiply")
    check("style: a vector layer blends too", contours.blendMode() == modes.CompositionMode_Multiply)

    labels = style.set_labels(contours.id(), expression="if(\"is_index\" = 1, \"elevation\", '')", placement="curved",
                              size=7)
    settings = contours.labeling().settings()
    check("labels: on the lines, following them", labels["placement"] == "curved" and contours.labelsEnabled()
          and settings.placement == QgsPalLayerSettings.Placement.Curved and settings.isExpression, labels)
    check("labels: drawn with the contours", colours([contours], dem.extent(), "EPSG:32631") > 1)
    flat = style.set_labels(contours.id(), field="elevation", placement="horizontal")
    check("labels: flat beside the lines", flat["placement"] == "horizontal"
          and contours.labeling().settings().placement == QgsPalLayerSettings.Placement.Horizontal, flat)
    said = refused(style.set_labels, "points", field="nom", placement="curved")
    check("labels: a placement along lines is refused on points", "layer of lines" in said, said)
    said = refused(style.set_labels, contours.id(), field="elevation", placement="diagonal")
    check("labels: an unknown placement is refused", "placement is one of" in said, said)
    usual = style.set_labels("points", field="nom")
    check("labels: the usual placement is left to QGIS", usual["placement"] == "auto", usual)
    return contours


def check_duplicate(project, dem, contours):
    from filter_mate.adapters.public_api import layer_style as style, project_control
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    style.set_layer_style("dem", "pseudocolor", ramp="Spectral", invert=True, cut=2, opacity=0.6)
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("d1", "duplicate_layer", {"layer": "dem"}))
    copy = project_control.duplicate_layer("dem", name="Ombrage")
    recorder.after_call()
    layer = project.mapLayer(copy["layer_id"])
    order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
    check("duplicate: a second layer on the same file, just above the first", layer.isValid() and layer.id() != dem.id()
          and layer.source() == dem.source() and copy["name"] == "Ombrage" and copy["layer_kind"] == "raster"
          and order.index(layer.id()) + 1 == order.index(dem.id()), (copy, order))
    check("duplicate: it keeps the style of the first", layer.renderer().type() == "singlebandpseudocolor"
          and abs(layer.opacity() - 0.6) < 1e-6)
    recorder.before_call(ToolCallPart("d2", "set_layer_style", {"layer": layer.id()}))
    style.set_layer_style(layer.id(), "hillshade", multidirectional=True, blend="multiply", opacity=0.35)
    recorder.after_call()
    check("duplicate: each layer is drawn its own way", layer.renderer().type() == "hillshade"
          and dem.renderer().type() == "singlebandpseudocolor"
          and colours([dem, layer], dem.extent(), "EPSG:32631") > 8)
    effects = recorder.finish()
    apply_effects(effects, undo=True)
    check("duplicate: undoing the turn removes the copy and leaves the first as it was",
          project.mapLayer(copy["layer_id"]) is None and dem.renderer().type() == "singlebandpseudocolor")
    contours.setSubsetString('"is_index" = 1')
    twin = project.mapLayer(project_control.duplicate_layer(contours.id())["layer_id"])
    check("duplicate: a vector layer keeps its filter, named as a copy", twin.subsetString() == '"is_index" = 1'
          and twin.featureCount() == contours.featureCount() and twin.name() == contours.name() + " (copy)",
          (twin.name(), twin.subsetString()))
    contours.setSubsetString("")
    project.removeMapLayer(twin.id())
    memory = QgsVectorLayer("Point?crs=EPSG:32631&field=nom:string", "memory", "memory")
    feature = QgsFeature(memory.fields())
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(641000, 5069000)))
    feature.setAttributes(["a"])
    memory.dataProvider().addFeatures([feature])
    project.addMapLayer(memory)
    held = project.mapLayer(project_control.duplicate_layer("memory")["layer_id"])
    check("duplicate: a layer held in memory gets its features", held.featureCount() == 1)
    project.removeMapLayers([held.id(), memory.id()])
    said = refused(project_control.duplicate_layer, "nope")
    check("duplicate: an unknown layer is refused", "not found" in said, said)


def serve_tiles(tiles, delay, stall=None):
    """A bucket on this machine: the tiles of ``tiles`` by parts, a 404 for the others; what was asked.
    ``stall`` set: a part asked is begun, then nothing more comes (a server gone mute), until it is cleared."""
    asked = []

    class Bucket(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def answer(self, body):
            asked.append((self.command, self.path, self.headers.get("Range", "")))
            if delay[0]:
                time.sleep(delay[0])
            data = tiles.get(self.path)
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
            self.send_header("Content-Type", "image/tiff")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(part)))
            self.end_headers()
            if body:
                try:
                    if stall is not None and stall.is_set() and wanted != "bytes=0-0":
                        self.wfile.write(part[:50])
                        self.wfile.flush()
                        while stall.is_set():
                            time.sleep(0.2)
                        return
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


def check_elevation(project, work):
    from filter_mate.adapters.agent import bounded_http
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import project_control, terrain
    from filter_mate.core.agent import elevation
    from filter_mate.core.agent.messages import ToolCallPart

    # One square degree at 3 arc seconds, the cone over it (245 m at its corners): N45 E004, where Lyon is.
    tile = os.path.join(work, "tile.tif")
    make_dem(tile, 4326, (4.0, 46.0), 1.0 / 1200, size=1200, slope=0.3)
    with open(tile, "rb") as handle:
        tiles = {TILE: handle.read()}
    delay = [0.0]
    stall = threading.Event()
    server, asked = serve_tiles(tiles, delay, stall)
    real = elevation.SOURCES[0]
    local = elevation.ElevationSource(real.id, real.title, f"http://127.0.0.1:{server.server_address[1]}",
                                      real.resolution, real.attribution, real.note)
    terrain.known = lambda identifier: local if (identifier or "").strip().lower() == real.id else None
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")

    def written():
        return {name for name in (os.listdir(root) if os.path.isdir(root) else []) if name.startswith("elevation-")}

    data = QgsVectorLayer("Point?crs=EPSG:4326", "data", "memory")
    project.addMapLayer(data)
    basemap = QgsRasterLayer("type=xyz&url=http://127.0.0.1:9/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0", "fond", "wms")
    project.addMapLayer(basemap, False)
    project.layerTreeRoot().addLayer(basemap)
    try:
        already = written()
        recorder = EffectsRecorder()
        recorder.before_call(ToolCallPart("e1", "add_elevation", {"extent_wkt": LYON}))
        made = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
        recorder.after_call()
        layer = project.mapLayer(made["layer_id"])
        check("elevation: a raster in the UTM zone of the area, at the 30 m of the source",
              layer.isValid() and layer.providerType() == "gdal" and made["crs_authid"] == "EPSG:32631"
              and layer.crs().authid() == "EPSG:32631" and made["resolution"] == 30.0
              and abs(layer.rasterUnitsPerPixelX() - 30) < 1e-6 and (made["width"], made["height"]) == (layer.width(), layer.height())
              and 350 < made["width"] < 400 and 360 < made["height"] < 400, made)
        check("elevation: the heights of the area are told", made["minimum"] is not None
              and 245 < made["minimum"] < made["mean"] < made["maximum"] < 500, made)
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check("elevation: under the data, above the basemap", order == [data.id(), layer.id(), basemap.id()], order)
        check("elevation: named after its source, with its attribution and what it is",
              made["name"] == "Elevation (Copernicus DEM 30 m)" and layer.metadata().rights() == [real.attribution]
              and made["attribution"] == real.attribution and "surface model" in made["note"], made)
        kept = written() - already
        folder = os.path.dirname(layer.source())
        check("elevation: one file kept in the QGIS profile", len(kept) == 1 and os.path.basename(folder) in kept
              and os.path.isfile(layer.source()) and layer.source().endswith("copernicus_dem_30m.tif"), layer.source())
        ranges = [wanted for command, path, wanted in asked if command == "GET" and path == TILE]
        whole = [wanted for wanted in ranges if not wanted]
        check("elevation: the tile is read by parts, never whole", ranges and not whole, ranges[:5])
        check("elevation: drawn", colours([layer], layer.extent(), "EPSG:32631") > 8)
        json.dumps(made)
        effects = recorder.finish()
        apply_effects(effects, undo=True)
        check("elevation: undoing the turn removes the layer", project.mapLayer(made["layer_id"]) is None)
        apply_effects(effects, undo=False)
        back = [found for found in project.mapLayers().values() if found.name() == made["name"]]
        check("elevation: redoing opens its file again", len(back) == 1 and back[0].isValid())
        project.removeMapLayer(back[0].id())

        project.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
        lambert = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326", resolution=90, name="MNT")
        check("elevation: on the CRS of the project when it is in metres, at the resolution asked",
              lambert["crs_authid"] == "EPSG:2154" and lambert["resolution"] == 90.0 and lambert["name"] == "MNT"
              and 110 < lambert["width"] < 140, lambert)
        project.removeMapLayer(lambert["layer_id"])
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        mercator = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
        check("elevation: not on Web Mercator, whose metres are not those of the ground",
              mercator["crs_authid"] == "EPSG:32631", mercator)
        project.removeMapLayer(mercator["layer_id"])
        # Projections that are metric but not conformal: the same grid as Web Mercator, the UTM zone of the area
        # (2026-11-18: Equal Earth, Plate Carree, Mollweide and LAEA were kept, their bounds covering the area).
        for authid in ("EPSG:8857", "EPSG:4087", "ESRI:54001", "ESRI:54009", "EPSG:3035"):
            crs = QgsCoordinateReferenceSystem(authid)
            project.setCrs(crs)
            distorted = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
            check(f"elevation: not on {authid} ({terrain._projection_method(crs)}), which distorts slopes",
                  crs.isValid() and distorted["crs_authid"] == "EPSG:32631", distorted)
            project.removeMapLayer(distorted["layer_id"])
        for authid in ("EPSG:32631", "EPSG:2154", "EPSG:27700", "EPSG:3031"):
            check(f"elevation: {authid} keeps the angles ({terrain._projection_method(QgsCoordinateReferenceSystem(authid))})",
                  terrain.metric_grid(terrain._projection_method(QgsCoordinateReferenceSystem(authid)), True, True))
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        asked_3857 = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326", target_crs="EPSG:3857")
        check("elevation: a CRS in metres asked is followed", asked_3857["crs_authid"] == "EPSG:3857", asked_3857)
        project.removeMapLayer(asked_3857["layer_id"])
        in_lambert = terrain.add_elevation(
            extent_wkt="POLYGON((838000 6515000, 848000 6515000, 848000 6525000, 838000 6525000, 838000 6515000))",
            crs="EPSG:2154", target_crs="2154")
        # 10 km at 30 m, and what its bounds gain when they go through longitude and latitude.
        check("elevation: an area given in another CRS", in_lambert["crs_authid"] == "EPSG:2154"
              and 333 <= in_lambert["width"] < 365, in_lambert)
        project.removeMapLayer(in_lambert["layer_id"])
        coast = terrain.add_elevation(extent_wkt="POLYGON((4.9 45.7, 5.1 45.7, 5.1 45.8, 4.9 45.8, 4.9 45.7))",
                                      crs="4326")
        coast_layer = project.mapLayer(coast["layer_id"])
        coast_set = gdal.Open(coast_layer.source())  # kept: a band outlives nothing of its dataset
        coast_band = coast_set.GetRasterBand(1)
        check("elevation: a tile the source does not have is no data, said so and left out of the figures",
              "open sea" in coast["note"] and "leaves out" in coast["note"] and "no data" in coast["note"]
              and coast_band.GetNoDataValue() == -9999.0 and coast["minimum"] > 200, (coast, coast_band.GetNoDataValue()))
        project.removeMapLayer(coast["layer_id"])
        # An area on the south edge of a tile: its rectangle in UTM 31N reaches the square below (2026-11-18: 2.5 % of
        # the grid was written at 0 m, in the corners, and nothing was said).
        edge = "POLYGON((4.3 45.0, 4.7 45.0, 4.7 45.3, 4.3 45.3, 4.3 45.0))"
        south_tile = os.path.join(work, "south.tif")
        make_dem(south_tile, 4326, (4.0, 45.0), 1.0 / 1200, size=1200, slope=0.3)
        with open(south_tile, "rb") as handle:
            tiles[TILE.replace("N45", "N44")] = handle.read()

        def holes(made_edge):
            opened = gdal.Open(project.mapLayer(made_edge["layer_id"]).source())
            band = opened.GetRasterBand(1)
            values = band.ReadAsArray()
            return int((values == 0).sum()), int((values == band.GetNoDataValue()).sum()), values.size

        whole_edge = terrain.add_elevation(extent_wkt=edge, crs="EPSG:4326")
        zero, empty, pixels = holes(whole_edge)
        check("elevation: the corners of the grid come from the squares they fall in, no 0 m and no hole",
              zero == 0 and empty == 0 and "no data" not in whole_edge["note"] and whole_edge["minimum"] > 200,
              (zero, empty, pixels, whole_edge))
        project.removeMapLayer(whole_edge["layer_id"])
        del tiles[TILE.replace("N45", "N44")]
        gdal.VSICurlClearCache()
        part_edge = terrain.add_elevation(extent_wkt=edge, crs="EPSG:4326")
        zero, empty, pixels = holes(part_edge)
        check("elevation: a corner no square covers is no data (never 0 m), said so, and not in the figures",
              zero == 0 and 0 < empty < pixels // 10 and "no data" in part_edge["note"] and part_edge["minimum"] > 200,
              (zero, empty, pixels, part_edge))
        project.removeMapLayer(part_edge["layer_id"])
        # A CRS the user defined (an authid of QGIS alone, which GDAL refuses) is given to GDAL as a WKT.
        registry = QgsApplication.coordinateReferenceSystemRegistry()
        custom = QgsCoordinateReferenceSystem.fromProj("+proj=tmerc +lat_0=0 +lon_0=4.8 +k=0.9996 +x_0=500000 +y_0=0 "
                                                       "+ellps=WGS84 +units=m +no_defs")
        added = registry.addUserCrs(custom, "FilterMate test CRS") if hasattr(registry, "addUserCrs") else -1
        user = QgsCoordinateReferenceSystem(f"USER:{added}") if added > 0 else QgsCoordinateReferenceSystem()
        if user.isValid() and user.authid().startswith("USER:"):
            project.setCrs(user)
            in_user = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
            check("elevation: a project in a CRS of the user is written in it, not refused as unreadable",
                  in_user["crs_authid"] == user.authid() and in_user["width"] > 300 and in_user["minimum"] > 200, in_user)
            project.removeMapLayer(in_user["layer_id"])
            project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
            registry.removeUserCrs(added)
        else:
            print(f"INFO no CRS of the user in this QGIS ({user.authid()!r}): that check is skipped", flush=True)
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:27700"))
        british = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
        check("elevation: not on the grid of another country, which stretches the ground",
              british["crs_authid"] == "EPSG:32631", british)
        project.removeMapLayer(british["layer_id"])
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        # A group of basemaps at the bottom of the tree is a background too: the elevation goes above it.
        other = QgsRasterLayer("type=xyz&url=http://127.0.0.1:9/b/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0", "photo", "wms")
        project.addMapLayer(other, False)
        project.layerTreeRoot().addGroup("Fonds").addLayer(other)
        grouped = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check("elevation: above a group of basemaps too",
              order == [data.id(), grouped["layer_id"], basemap.id(), other.id()], order)
        project.removeMapLayers([grouped["layer_id"], other.id()])
        project.layerTreeRoot().removeChildNode(project.layerTreeRoot().findGroup("Fonds"))

        count, files = len(project.mapLayers()), written()
        for label, arguments, needle in (
                ("open sea", {"extent_wkt": "POLYGON((10 10, 10.1 10, 10.1 10.1, 10 10.1, 10 10))", "crs": "EPSG:4326"},
                 "has no tile there"),
                ("an area too large", {"extent_wkt": "POLYGON((0 40, 9 40, 9 49, 0 49, 0 40))", "crs": "EPSG:4326"},
                 "16 at most"),
                ("a point", {"extent_wkt": "POINT(4.84 45.76)", "crs": "EPSG:4326"}, "a point or a line"),
                ("a WKT that is none", {"extent_wkt": "POLYGON((", "crs": "EPSG:4326"}, "could not be read"),
                ("an unknown CRS", {"extent_wkt": LYON, "crs": "EPSG:999999"}, "unknown CRS"),
                ("a CRS written as a definition, which can name a grid by its address",
                 {"extent_wkt": LYON, "crs": "+proj=longlat +nadgrids=https://example.org/g.tif"}, "unknown CRS"),
                ("a definition to write in", {"extent_wkt": LYON, "crs": "EPSG:4326", "target_crs": "+proj=utm +zone=31"},
                 "unknown CRS"),
                ("a CRS in degrees to write in", {"extent_wkt": LYON, "crs": "EPSG:4326", "target_crs": "EPSG:4326"},
                 "not in metres"),
                ("a resolution too fine for the area",
                 {"extent_wkt": "POLYGON((4 44, 7 44, 7 46.9, 4 46.9, 4 44))", "crs": "EPSG:4326", "resolution": 30},
                 "or more"),
                ("no area and no map", {}, "QGIS has no map here"),
                ("a platform that holds no elevation", {"platform": "datagouv", "extent_wkt": LYON, "crs": "EPSG:4326"},
                 "holds no elevation"),
                ("a platform that is not of the list", {"platform": "srtm", "extent_wkt": LYON, "crs": "EPSG:4326"},
                 "not an elevation source")):
            said = refused(terrain.add_elevation, **arguments)
            check(f"elevation: {label} is refused, nothing added nor kept", needle in said
                  and len(project.mapLayers()) == count and written() == files, said)

        # A grid that holds no data at all (a tile read for a corner the grid never touches) is refused as before, not
        # added as a layer of min 0 and max 0 (the statistics of a band of no data are [0, 0, 0] with an error).
        every_pixel = terrain._empty_pixels
        terrain._empty_pixels = lambda dataset: dataset.RasterXSize * dataset.RasterYSize
        try:
            said = refused(terrain.add_elevation, extent_wkt=LYON, crs="EPSG:4326")
        finally:
            terrain._empty_pixels = every_pixel
        check("elevation: a grid with no data at all is refused as no tile, nothing added nor kept",
              "has no tile there" in said and len(project.mapLayers()) == count and written() == files, said)
        from filter_mate.adapters.public_api import operations
        delay[0] = 0.4
        # While the source is asked which tiles it has, then while the tile is read.
        for label, after in (("the question to the source", 150), ("the reading", 700)):
            gdal.VSICurlClearCache()  # what GDAL read of the tile above would answer without the network
            busy = []
            stop = QTimer()
            stop.setSingleShot(True)
            stop.timeout.connect(lambda: (busy.append(operations.busy_reason()), bounded_http.abort_active()))
            stop.start(after)
            started = time.monotonic()
            said = refused(terrain.add_elevation, extent_wkt=LYON, crs="EPSG:4326")
            stop.stop()
            check(f"elevation: Stop ends {label}, nothing added nor kept", said == "stopped"
                  and len(project.mapLayers()) == count and written() == files and time.monotonic() - started < 20,
                  (said, round(time.monotonic() - started, 1)))
            check(f"elevation: FilterMate is busy during {label}, and free again after the Stop",
                  busy and "add_elevation" in busy[0] and operations.busy_reason() == "", (busy, operations.busy_reason()))
        delay[0] = 0.0
        # A server gone mute in the middle of a tile: GDAL gives it up after 8 s, and Stop is heard then.
        gdal.VSICurlClearCache()
        stall.set()
        stop = QTimer()
        stop.setSingleShot(True)
        stop.timeout.connect(lambda: bounded_http.abort_active())
        stop.start(1000)
        started = time.monotonic()
        said = refused(terrain.add_elevation, extent_wkt=LYON, crs="EPSG:4326")
        waited = time.monotonic() - started
        stop.stop()
        stall.clear()
        check("elevation: Stop is heard within seconds of a server gone mute, nothing added nor kept",
              said == "stopped" and waited < 15 and len(project.mapLayers()) == count and written() == files,
              (said, round(waited, 1)))
        print(f"INFO a Stop pressed 1 s into a tile that stalls is answered after {waited:.1f} s", flush=True)
        # A tile the server has, but that is no image: said as it is, without its address.
        whole = tiles[TILE]
        tiles[TILE] = b"<html>503 Slow Down</html>" * 200
        gdal.VSICurlClearCache()
        said = refused(terrain.add_elevation, extent_wkt=LYON, crs="EPSG:4326")
        check("elevation: a tile that cannot be read is said so, without its address",
              said.startswith("a tile of the elevation could not be read from its server") and "127.0.0.1" not in said
              and "http" not in said and "TypeError" not in said and len(project.mapLayers()) == count
              and written() == files, said)
        tiles[TILE] = whole
        gdal.VSICurlClearCache()
        # A raster of the user read from a server, at an address that does not end with .tif.
        with open(os.path.join(work, "dem.tif"), "rb") as handle:
            tiles["/user/dem.tiff"] = handle.read()
        address = f"http://127.0.0.1:{server.server_address[1]}/user/dem.tiff"
        distant = QgsRasterLayer("/vsicurl/" + address, "distant", "gdal")
        project.addMapLayer(distant)
        far = terrain.contour_lines("distant", 25) if distant.isValid() else {}
        check("contours: from a raster read from a server", far.get("feature_count", 0) > 5 and far["minimum"] == 100, far)
        project.removeMapLayer(far.get("layer_id", ""))
        del tiles["/user/dem.tiff"]
        gdal.VSICurlClearCache()
        said = refused(terrain.contour_lines, "distant", 25)
        check("contours: a raster its server no longer gives is said so, without its address",
              said.startswith("the raster could not be read") and "127.0.0.1" not in said and "dem.tiff" not in said, said)
        project.removeMapLayer(distant.id())
        count = len(project.mapLayers())

        check("elevation: the Test of the Sources tab", terrain.check_elevation("copernicus_dem")["status"] == 200)
        tiles.clear()
        said = refused(terrain.check_elevation, "copernicus_dem")
        check("elevation: a source that has lost its tiles fails its Test", "not with its tiles" in said, said)
        server.shutdown()
        server.server_close()
        said = refused(terrain.add_elevation, extent_wkt=LYON, crs="EPSG:4326")
        check("elevation: a server that does not answer is said so", "did not answer" in said, said)
    finally:
        terrain.known = elevation.known
        project.setCrs(QgsCoordinateReferenceSystem())
        project.removeMapLayers([data.id(), basemap.id()])
        for name in written():
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)
    return project_control


def check_tools(project, work):
    """The chat tools, on the real accessor: what a model sends, and what it reads back."""
    from filter_mate.adapters.public_api import terrain
    from filter_mate.core.agent import elevation
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor

    class PublicApi:
        @staticmethod
        def get_active_filters():
            return {}

    tile = os.path.join(work, "tile.tif")
    with open(tile, "rb") as handle:
        server, _asked = serve_tiles({TILE: handle.read()}, [0.0])
    real = elevation.SOURCES[0]
    local = elevation.ElevationSource(real.id, real.title, f"http://127.0.0.1:{server.server_address[1]}",
                                      real.resolution, real.attribution, real.note)
    terrain.known = lambda identifier: local if (identifier or "").strip().lower() == real.id else None
    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    accessor = QGISFilterMateAccessor(PublicApi(), None)

    def tools(platforms, share_values=True):
        executor = ToolExecutor(chat_tools(), build_handlers(accessor, os.path.join(work, "exports"), platforms=platforms,
                                                             share_values=share_values))

        def tool(tool_name, /, **arguments):
            result = executor.execute(ToolCallPart("c", tool_name, arguments))
            return result.is_error, result.content
        return tool

    try:
        tool = tools(["copernicus_dem"])
        error, content = tool("add_elevation", extent_wkt=LYON, crs="EPSG:4326", name="Relief")
        made = {} if error else json.loads(content)
        check("tool add_elevation", not error and made["name"] == "Relief" and made["platform"] == "copernicus_dem"
              and made["crs_authid"] == "EPSG:32631" and made["resolution"] == 30.0, content)
        check("tool add_elevation: the address of the server is not in the answer", "127.0.0.1" not in content, content)
        error, content = tool("set_layer_style", layer="Relief", mode="pseudocolor", ramp="Spectral", invert=True, cut=2,
                              opacity=0.5)
        check("tool set_layer_style: a ramp over the cut range, half transparent", not error
              and json.loads(content)["opacity"] == 0.5 and "minimum" in json.loads(content), content)
        error, content = tool("duplicate_layer", layer="Relief", name="Ombrage")
        check("tool duplicate_layer", not error and json.loads(content)["name"] == "Ombrage", content)
        error, content = tool("set_layer_style", layer="Ombrage", mode="hillshade", multidirectional=True,
                              blend="multiply", opacity=0.3)
        answer = {} if error else json.loads(content)
        check("tool set_layer_style: a hillshade tells its light, no ramp nor range",
              not error and answer.get("blend") == "multiply" and answer.get("azimuth") == 315.0
              and not {"ramp", "minimum", "maximum", "field", "classes"} & set(answer), content)
        error, content = tool("contour_lines", layer="Relief", interval=5, index_interval=25)
        answer = {} if error else json.loads(content)
        check("tool contour_lines", not error and answer["feature_count"] > 3 and answer["index_count"] >= 1
              and answer["fields"] == ["elevation", "is_index"] and "minimum" in answer, content)
        error, content = tool("set_layer_style", layer=answer.get("name", ""), mode="rules", rules=[
            {"expression": '"is_index" = 1', "color": "#5b3a1e", "width": 0.6}, {"color": "#a67c52", "width": 0.2}])
        check("tool set_layer_style: rules with a width", not error and json.loads(content)["classes"] == 2, content)
        error, content = tool("set_layer_style", layer=answer.get("name", ""), mode="rules",
                              rules=[{"color": "red", "width": 0}])
        check("tool set_layer_style: a width of zero is refused by the schema", error and "$.rules" in content, content)
        error, content = tool("set_labels", layer=answer.get("name", ""), field="elevation", placement="curved")
        check("tool set_labels: along the lines", not error and json.loads(content)["placement"] == "curved", content)
        error, content = tool("contour_lines", layer="Relief", interval=25, index_interval=60)
        check("tool contour_lines: a refusal the model can act on", error and "multiple of interval" in content, content)
        # A layer the user protected: read (its contours), never copied, since a copy is edited in its place.
        from filter_mate.adapters.agent import protected_layers
        protected_layers.write_ids([project.mapLayersByName("Relief")[0].id()])
        try:
            layers = len(project.mapLayers())
            error, content = tool("duplicate_layer", layer="Relief", name="Copie")
            check("tool duplicate_layer: a protected layer is not copied", error and "protected" in content
                  and len(project.mapLayers()) == layers, content)
            error, content = tool("set_layer_style", layer="Relief", mode="keep", blend="multiply")
            check("tool set_layer_style: nor blended", error and "protected" in content, content)
            error, content = tool("contour_lines", layer="Relief", interval=10, name="Lues")
            check("tool contour_lines: a protected raster is read", not error and json.loads(content)["name"] == "Lues",
                  content)
        finally:
            protected_layers.write_ids([])
        error, content = tool("add_elevation", extent_wkt=LYON, crs="EPSG:4326", platform="datagouv")
        check("tool add_elevation: a platform that is not ticked", error and "not enabled" in content, content)
        error, content = tools([])("add_elevation", extent_wkt=LYON, crs="EPSG:4326")
        check("tool add_elevation: refused when no elevation source is ticked", error and "not enabled" in content, content)
        error, content = tools(["copernicus_dem"], share_values=False)("contour_lines", layer="Relief", interval=10)
        answer = {} if error else json.loads(content)
        check("tool contour_lines: without the values, the heights are not told", not error
              and "minimum" not in answer and "maximum" not in answer and answer["feature_count"] > 1, content)
        quiet = tools(["copernicus_dem"], share_values=False)
        error, content = quiet("set_layer_style", layer="Relief", mode="pseudocolor", ramp="Spectral", cut=2)
        answer = {} if error else json.loads(content)
        check("tool set_layer_style: without the values, the range read from the pixels is not told", not error
              and answer.get("mode") == "pseudocolor" and "minimum" not in answer and "maximum" not in answer, content)
        error, content = quiet("set_layer_style", layer="Relief", mode="gray", minimum=900000)
        check("tool set_layer_style: nor in a refusal", error and "must be below" in content
              and "ranges from" not in content, content)
        error, content = quiet("set_layer_style", layer="Relief", mode="gray", minimum=0, maximum=3000)
        answer = {} if error else json.loads(content)
        check("tool set_layer_style: a range the model gave comes back", not error and answer.get("minimum") == 0.0
              and answer.get("maximum") == 3000.0, content)
    finally:
        terrain.known = elevation.known
        server.shutdown()
        server.server_close()
        project.removeAllMapLayers()
        for name in (os.listdir(root) if os.path.isdir(root) else []):
            if name.startswith("elevation-"):
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def check_live(project):
    """The real servers: the elevation of Lyon, and the satellite basemap over it."""
    from filter_mate.adapters.public_api import project_control, terrain

    root = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    started = time.monotonic()
    try:
        made = terrain.add_elevation(extent_wkt=LYON, crs="EPSG:4326")
    except ValueError as exc:
        check("live: the elevation of Lyon from Copernicus", False, exc)
        return
    seconds = time.monotonic() - started
    layer = project.mapLayer(made["layer_id"])
    check("live: the elevation of Lyon from Copernicus, 30 m, UTM 31N", layer.isValid() and made["crs_authid"] == "EPSG:32631"
          and made["resolution"] == 30.0 and 350 < made["width"] < 400, made)
    # The Saone at about 160 m, Fourviere and the Monts d'Or above 300 m.
    check("live: heights of Lyon", 140 < made["minimum"] < 180 and 280 < made["maximum"] < 700, made)
    print(f"INFO live: {made['width']} x {made['height']} pixels, {made['size']}, read in {seconds:.1f} s", flush=True)
    contours = terrain.contour_lines(made["layer_id"], 25, index_interval=100)
    check("live: contours every 25 m, index contours at 100 m", contours["feature_count"] > 50
          and 1 <= contours["index_count"] < contours["feature_count"], contours)
    print(f"INFO live: {contours['feature_count']} contours, {contours['index_count']} index contours", flush=True)
    try:
        summary = project_control.add_basemap("google_satellite")
        basemap = project.mapLayer(summary["layer_id"])
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check("live: Google Satellite is added under the layers", basemap.isValid() and order[-1] == basemap.id()
              and basemap.metadata().rights() == ["© Google"], (summary, order))
        check("live: Google Satellite draws Lyon", colours([basemap], layer.extent(), "EPSG:32631") > 8)
    except ValueError as exc:
        check("live: Google Satellite is added under the layers", False, exc)
    project.removeAllMapLayers()
    for name in (os.listdir(root) if os.path.isdir(root) else []):
        if name.startswith("elevation-"):
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def main():
    print(f"QGIS {Qgis.QGIS_VERSION}, GDAL {gdal.__version__}", flush=True)
    work = tempfile.mkdtemp()
    project = QgsProject.instance()
    dem, points = check_contours(project, work)
    contours = check_style(project, dem, points, work)
    check_duplicate(project, dem, contours)
    project.removeAllMapLayers()
    check_elevation(project, work)
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
