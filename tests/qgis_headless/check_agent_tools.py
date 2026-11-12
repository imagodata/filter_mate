# -*- coding: utf-8 -*-
"""The read tools of the agent on real layers, in a real (headless) QGIS. Run inside a qgis/qgis image:

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_tools.py

With FM_FIXTURES (the folder of make_fixtures.py), a point cloud is checked too.
Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPalettedRasterRenderer, QgsPointCloudLayer,
    QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDate, QVariant


def _link(source, target):
    """A link to the plugin folder: a symlink, or a junction on Windows (no privilege needed)."""
    try:
        os.symlink(source, target)
    except OSError:
        if os.name != "nt":
            raise
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", target, source], check=True, capture_output=True)


try:
    from osgeo import gdal
except ImportError:
    gdal = None

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""))


def make_vector(path, driver):
    fields = QgsFields()
    fields.append(QgsField("nom", QVariant.String))
    fields.append(QgsField("pop", QVariant.Int))
    fields.append(QgsField("taux", QVariant.Double))
    if driver == "GPKG":
        fields.append(QgsField("creation", QVariant.Date))
    memory = QgsVectorLayer("Point?crs=EPSG:2154", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    features = []
    for index in range(1, 61):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(650000 + index, 6860000)))
        name = "Saint-%02d" % index if index % 2 else "Muret-%02d" % index
        values = [name, index * 100, index / 4.0]
        if driver == "GPKG":
            values.append(QDate(2020, 1, min(index, 28)))
        if index == 60:
            values[0] = None
        feature.setAttributes(values)
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = driver
    context = QgsProject.instance().transformContext()
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, context, options)


def make_raster(path):
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(path, 8, 8, 2, gdal.GDT_Byte)
    dataset.SetGeoTransform((650000, 25, 0, 6860000, 0, -25))
    dataset.SetProjection('EPSG:2154')
    dataset.GetRasterBand(1).Fill(1)
    dataset.GetRasterBand(2).Fill(2)
    dataset.FlushCache()
    del dataset


def check_map_details(introspection, project, gpkg, shp, plain):
    """Where a layer sits in the tree, its extent, how it is drawn, its joins and relations."""
    from qgis.core import (
        QgsCategorizedSymbolRenderer, QgsPalLayerSettings, QgsRelation, QgsRendererCategory, QgsSymbol,
        QgsVectorLayerJoinInfo, QgsVectorLayerSimpleLabeling,
    )
    check("describe: at the root, visible, nothing joined", (plain["visible"], plain["group"], plain["joins"],
                                                             plain["relations"]) == (True, "", [], []), plain)
    check("describe: extent in the layer CRS", plain["extent"] == [650001.0, 6860000.0, 650060.0, 6860000.0],
          plain["extent"])
    check("describe: single symbol, no label", plain["style"] == {"renderer": "singleSymbol"}, plain["style"])
    root = project.layerTreeRoot()
    places = introspection.tree_places()
    check("tree: both layers, ranked", sorted(rank for rank, _, _ in places.values()) == [0, 1] and
          set(places) == {gpkg.id(), shp.id()}, places)

    outer = root.addGroup("Fonds")
    inner = outer.addGroup("Admin")
    node = root.findLayer(gpkg.id())
    inner.addChildNode(node.clone())
    root.removeChildNode(node)
    outer.setItemVisibilityChecked(False)
    renderer = QgsCategorizedSymbolRenderer("nom", [
        QgsRendererCategory(name, QgsSymbol.defaultSymbol(gpkg.geometryType()), name) for name in ("Saint-01", "Muret-02")])
    previous = gpkg.renderer().clone()
    gpkg.setRenderer(renderer)
    settings = QgsPalLayerSettings()
    settings.fieldName = "nom"
    gpkg.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    gpkg.setLabelsEnabled(True)
    gpkg.setOpacity(0.5)
    gpkg.setScaleBasedVisibility(True)
    gpkg.setMinimumScale(50000)
    gpkg.setMaximumScale(1000)
    join = QgsVectorLayerJoinInfo()
    join.setJoinLayer(shp)
    join.setJoinFieldName("nom")
    join.setTargetFieldName("nom")
    join.setPrefix("r_")
    gpkg.addJoin(join)
    relation = QgsRelation()
    relation.setId("communes_routes")
    relation.setName("routes des communes")
    relation.setReferencingLayer(shp.id())
    relation.setReferencedLayer(gpkg.id())
    relation.addFieldPair("pop", "taux")
    project.relationManager().addRelation(relation)

    details = introspection.describe_layer("communes")
    check("describe: its groups, hidden with them", (details["group"], details["visible"]) == ("Fonds / Admin", False),
          details)
    check("describe: categorized on a field, labelled, scales", details["style"] == {
        "renderer": "categorizedSymbol", "field": "nom", "classes": 2, "labels": "nom", "opacity": 0.5,
        "min_scale": 50000.0, "max_scale": 1000.0}, details["style"])
    check("describe: no attribute value in the style", "Saint-01" not in json.dumps(details["style"]))
    check("describe: the join", details["joins"] == [
        {"layer": "routes", "field": "nom", "target_field": "nom", "prefix": "r_"}], details["joins"])
    check("describe: parent of a relation", details["relations"] == [{
        "name": "routes des communes", "role": "parent", "layer": "routes",
        "fields": [{"field": "taux", "other_field": "pop"}]}], details["relations"])
    child = introspection.describe_layer("routes")["relations"]
    check("describe: child of a relation", child == [{
        "name": "routes des communes", "role": "child", "layer": "communes",
        "fields": [{"field": "pop", "other_field": "taux"}]}], child)
    places = introspection.tree_places()
    check("tree: order of the tree, groups and visibility", (places[shp.id()], places[gpkg.id()]) ==
          ((0, "", True), (1, "Fonds / Admin", False)), places)
    json.dumps(details)

    # the rest of the checks runs on the layers as they were
    project.relationManager().removeRelation("communes_routes")
    gpkg.removeJoin(shp.id())
    gpkg.setRenderer(previous)
    gpkg.setLabelsEnabled(False)
    gpkg.setOpacity(1.0)
    gpkg.setScaleBasedVisibility(False)
    outer.setItemVisibilityChecked(True)


def refused(function, *args, **kwargs):
    """The message of the ValueError ``function`` raises, "" when it raises none."""
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        return str(exc) or "refused"
    return ""


def check_reading(introspection, project, gpkg, work):
    """Statistics, a sample of features and what lies at a point, on real layers."""
    stats = introspection.layer_statistics("communes", "pop")
    check("statistics of a number", (stats["feature_count"], stats["statistics"]) == (60, {
        "count": 60, "nulls": 0, "minimum": 100, "maximum": 6000, "sum": 183000.0, "mean": 3050.0,
        "stdev": stats["statistics"].get("stdev")}) and 1740 < stats["statistics"]["stdev"] < 1750, stats)
    text = introspection.layer_statistics("communes", "nom")["statistics"]
    check("statistics of a text: count, nulls, distinct", (text["count"], text["nulls"], text["distinct"]) == (59, 1, 59)
          and "sum" not in text, text)
    counted = introspection.layer_statistics("communes")
    check("no field: features are counted", counted["feature_count"] == 60 and "statistics" not in counted, counted)
    check("an unknown field is None", introspection.layer_statistics("communes", "nope") is None
          and introspection.layer_statistics("communes", "pop", group_by="nope") is None
          and introspection.layer_statistics("nope", "pop") is None)
    check("a field and a measure are refused", refused(introspection.layer_statistics, "communes", "pop", measure="area"))
    check("points have no length", "length" in refused(introspection.layer_statistics, "communes", measure="length"))
    check("nothing selected is said", "selected" in refused(introspection.layer_statistics, "communes", "pop",
                                                           selected_only=True))
    gpkg.selectByExpression('"pop" <= 300')
    chosen = introspection.layer_statistics("communes", "pop", selected_only=True)
    check("statistics of the selection", (chosen["feature_count"], chosen["statistics"]["sum"]) == (3, 600.0), chosen)
    gpkg.removeSelection()
    gpkg.setSubsetString('"pop" > 5000')
    filtered = introspection.layer_statistics("communes", "pop")
    check("the filter of the layer applies", (filtered["feature_count"], filtered["statistics"]["minimum"]) == (10, 5100),
          filtered)
    gpkg.setSubsetString("")
    many = introspection.layer_statistics("communes", group_by="pop", limit=5)
    check("groups are bounded", (len(many["groups"]), many["groups_total"], many["truncated"]) == (5, 60, True)
          and "statistics" not in many and many["groups"][0]["feature_count"] == 1, many)
    json.dumps(stats), json.dumps(many)

    zones = QgsVectorLayer("Polygon?crs=EPSG:2154&field=zone:string&field=hab:integer", "zones", "memory")
    features = []
    for index, (zone, people) in enumerate((("a", 10), ("a", 30), ("b", 5))):
        feature = QgsFeature(zones.fields())
        x = 650000 + index * 200
        feature.setGeometry(QgsGeometry.fromWkt(f"POLYGON(({x} 6860000, {x + 100} 6860000, {x + 100} 6860100, "
                                                f"{x} 6860100, {x} 6860000))"))
        feature.setAttributes([zone, people])
        features.append(feature)
    zones.dataProvider().addFeatures(features)
    project.addMapLayer(zones)
    area = introspection.layer_statistics("zones", measure="area", group_by="zone")
    groups = {row["value"]: row for row in area["groups"]}
    check("areas in square metres, by group", area["unit"] == "m2" and abs(area["statistics"]["sum"] - 30000) < 300
          and abs(groups["a"]["sum"] - 20000) < 200 and groups["a"]["feature_count"] == 2
          and [row["value"] for row in area["groups"]] == ["a", "b"], area)
    length = introspection.layer_statistics("zones", measure="length")
    check("perimeters in metres", length["unit"] == "m" and abs(length["statistics"]["sum"] - 1200) < 12, length)
    by_zone = introspection.layer_statistics("zones", "hab", group_by="zone")
    groups = {row["value"]: row for row in by_zone["groups"]}
    check("a field summed by group", (groups["a"]["sum"], groups["a"]["mean"], groups["b"]["sum"]) == (40.0, 20.0, 5.0),
          by_zone)
    json.dumps(area)

    sample = introspection.sample_features("communes", limit=2)
    check("sample: two rows, more exist", len(sample["features"]) == 2 and sample["truncated"] and
          set(sample["features"][0]["attributes"]) >= {"nom", "pop", "taux", "creation"} and
          "geometry" not in sample["features"][0] and sample["crs_authid"] == "EPSG:2154", sample)
    only = introspection.sample_features("communes", limit=1, fields=["nom"], geometry=True)["features"][0]
    check("sample: chosen fields, where the geometry is", list(only["attributes"]) == ["nom"] and
          only["geometry"]["centroid"] == [650001.0, 6860000.0] and "Point" in only["geometry"]["type"], only)
    matching = introspection.sample_features("communes", expression='"pop" > 5800')
    check("sample: by expression", sorted(row["attributes"]["pop"] for row in matching["features"]) == [5900, 6000]
          and not matching["truncated"], matching)
    check("sample: dates are text", sample["features"][0]["attributes"]["creation"] == "2020-01-01", sample)
    for bad in ("env('HOME') = 'x'", '"inconnu" > 3', '"pop" >'):
        check(f"sample refuses {bad!r}", refused(introspection.sample_features, "communes", expression=bad))
    check("sample: an unknown field is refused", "nope" in refused(introspection.sample_features, "communes",
                                                                  fields=["nope"]))
    check("sample: nothing selected is said", refused(introspection.sample_features, "communes", selected_only=True))
    check("sample: absent is None", introspection.sample_features("nope") is None)
    json.dumps(sample), json.dumps(only)

    hit = introspection.identify_at(650001, 6860000, crs="EPSG:2154", tolerance=0.4)
    names = {row["layer_name"]: row for row in hit["layers"]}
    check("identify: every visible layer with something there", list(names) == ["zones", "routes", "communes"] and
          [row["attributes"]["pop"] for row in names["communes"]["features"]] == [100] and hit["skipped"] == [], hit)
    wide = introspection.identify_at(650003, 6860000, crs="EPSG:2154", tolerance=2.5, layers=["communes"], limit=3)
    check("identify: tolerance and limit", [row["layer_name"] for row in wide["layers"]] == ["communes"] and
          len(wide["layers"][0]["features"]) == 3 and wide["layers"][0]["truncated"], wide)
    inside = introspection.identify_at(650050, 6860050, crs="EPSG:2154")
    check("identify: a polygon under the point, without tolerance",
          [(row["layer_name"], row["features"][0]["attributes"]["zone"]) for row in inside["layers"]] == [("zones", "a")]
          and inside["tolerance"] == 0, inside)
    check("identify: nothing there", introspection.identify_at(100, 100, crs="EPSG:2154")["layers"] == [])
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform
    to_degrees = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:2154"),
                                        QgsCoordinateReferenceSystem("EPSG:4326"), project)
    lonlat = to_degrees.transform(QgsPointXY(650050, 6860050))
    other = introspection.identify_at(lonlat.x(), lonlat.y(), crs="EPSG:4326")
    check("identify: a point given in another CRS", [row["layer_name"] for row in other["layers"]] == ["zones"] and
          other["crs"] == "EPSG:4326", other)
    check("identify: an unknown CRS is refused", refused(introspection.identify_at, 1, 1, crs="EPSG:999999999"))
    check("identify: an unknown layer is refused", refused(introspection.identify_at, 1, 1, layers=["nope"]))
    check("identify: out of range is refused", refused(introspection.identify_at, 1e12, 1))
    project.layerTreeRoot().findLayer(zones.id()).setItemVisibilityChecked(False)
    check("identify: a hidden layer is not read", introspection.identify_at(650050, 6860050, crs="EPSG:2154")["layers"] == [])
    if gdal is not None:
        raster_path = os.path.join(work, "identify.tif")
        make_raster(raster_path)
        raster = QgsRasterLayer(raster_path, "bandes")
        project.addMapLayer(raster)
        values = introspection.identify_at(650010, 6859990, crs="EPSG:2154", layers=["bandes"])
        check("identify: the values of a raster", values["layers"] == [{
            "layer_name": "bandes", "layer_kind": "raster",
            "values": [{"band": 1, "value": 1.0}, {"band": 2, "value": 2.0}]}], values)
        check("identify: outside the raster, nothing", introspection.identify_at(
            10, 10, crs="EPSG:2154", layers=["bandes"])["layers"] == [])
        check("a raster has no features to sample", refused(introspection.sample_features, "bandes")
              and refused(introspection.layer_statistics, "bandes"))
        project.removeMapLayer(raster.id())
    json.dumps(hit)
    project.removeMapLayer(zones.id())


def check_style(project, gpkg, work):
    """set_layer_style / set_labels on real layers, and the style an undo of the turn brings back."""
    from filter_mate.adapters.public_api import layer_style as style
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("s1", "set_layer_style", {"layer": "communes"}))
    recorder.before_call(ToolCallPart("s2", "set_labels", {"layer": gpkg.id()}))
    first = gpkg.renderer().type()
    made = style.set_layer_style("communes", "graduated", field="pop", classes=4, method="equal_interval",
                                 ramp="reds", opacity=0.7)
    check("style: graduated classes on a field", (made["classes"], made["field"], made["ramp"], made["method"]) ==
          (4, "pop", "Reds", "equal_interval") and gpkg.renderer().type() == "graduatedSymbol"
          and abs(gpkg.opacity() - 0.7) < 1e-6, made)
    check("style: no class value in the answer", "100" not in json.dumps(made) and "6000" not in json.dumps(made), made)
    categories = style.set_layer_style("communes", "categorized", field="nom")
    limit = style.MAX_CATEGORIES
    style.MAX_CATEGORIES = 50  # pop takes 60 values
    too_many = refused(style.set_layer_style, "communes", "categorized", field="pop")
    style.MAX_CATEGORIES = limit
    check("style: categories of a text field, too many values refused, NULL left out",
          "more than 50" in too_many and categories["classes"] == 59, (too_many, categories))
    single = style.set_layer_style("communes", "single", color="#00ff00")
    check("style: one symbol of a color", gpkg.renderer().type() == "singleSymbol" and
          gpkg.renderer().symbol().color().name() == "#00ff00", single)
    labels = style.set_labels("communes", "nom", size=9, color="navy")
    check("style: labels on a field", labels == {"layer_name": "communes", "labels": True, "field": "nom"}
          and gpkg.labelsEnabled() and gpkg.labeling().settings().fieldName == "nom", labels)
    for call, label in ((lambda: style.set_layer_style("communes", "graduated", field="nom"), "graduated on text"),
                        (lambda: style.set_layer_style("communes", "single", color="url(x)"), "a bad color"),
                        (lambda: style.set_layer_style("communes", "categorized", field="nom", ramp="nope"), "a bad ramp"),
                        (lambda: style.set_layer_style("communes", "pseudocolor"), "a raster mode"),
                        (lambda: style.set_labels("communes", "nope"), "labels on no field")):
        check(f"style: refuses {label}", refused(call))
    effects = recorder.finish()
    check("style: the turn keeps the style before it", [effect[0] for effect in effects] == ["style"], effects)
    done, left = apply_effects(effects, undo=True)
    check("style: undo brings the symbol, the labels and the opacity back", done == ["communes"] and not left and
          gpkg.renderer().type() == first and not gpkg.labelsEnabled() and gpkg.opacity() == 1.0,
          (gpkg.renderer().type(), gpkg.labelsEnabled(), gpkg.opacity()))
    apply_effects(effects, undo=False)
    check("style: redo applies it again", gpkg.renderer().type() == "singleSymbol" and gpkg.labelsEnabled())
    apply_effects(effects, undo=True)
    if gdal is not None:
        path = os.path.join(work, "style.tif")
        make_raster(path)
        raster = QgsRasterLayer(path, "bandes_style")
        project.addMapLayer(raster)
        check("style: a band with one value has no range", "no range" in refused(
            style.set_layer_style, "bandes_style", "pseudocolor"))
        ramp = style.set_layer_style("bandes_style", "pseudocolor", band=2, minimum=0, maximum=10, ramp="Viridis")
        check("style: a raster ramp over a given range", raster.renderer().type() == "singlebandpseudocolor" and
              (ramp["band"], ramp["minimum"], ramp["maximum"]) == (2, 0.0, 10.0), ramp)
        gray = style.set_layer_style("bandes_style", "gray", minimum=0, maximum=4)
        check("style: a gray stretch", raster.renderer().type() == "singlebandgray", gray)
        check("style: a raster has no labels nor categories", refused(style.set_labels, "bandes_style", "x")
              and refused(style.set_layer_style, "bandes_style", "categorized", field="x"))
        project.removeMapLayer(raster.id())
    # Graduated classes read every value of the layer on the main thread: the cap of layer_statistics, lowered here.
    from filter_mate.adapters.public_api import introspection as _introspection
    kept_renderer = gpkg.renderer().clone()  # put back below: the layouts checked next draw its legend
    kept_cap = _introspection.MAX_STAT_FEATURES
    _introspection.MAX_STAT_FEATURES = 10
    try:
        message = refused(lambda: style.set_layer_style("communes", "graduated", field="pop"))
        check("style: graduated classes refused past the features read", "more than 10 features" in message, message)
        categories = style.set_layer_style("communes", "categorized", field="nom")
        check("style: categories still made, they read distinct values only", categories["classes"] > 10, categories)
    finally:
        _introspection.MAX_STAT_FEATURES = kept_cap
    # While FilterMate filters, a style or a layout from the agent (or REST, or MCP) waits: refused, nothing changed.
    from filter_mate.adapters.public_api import operations as _operations
    from filter_mate.filtermate_api.main_thread import QGISBusy
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    renderer_before = gpkg.renderer().type()
    _operations._RUNNING.append("a filter")
    try:
        for label, call in (("a style", lambda: QGISFilterMateAccessor._style("set_layer_style", "communes", "single")),
                            ("a layout", lambda: QGISFilterMateAccessor._layouts("create_layout", "Occupé"))):
            try:
                call()
                busy = ""
            except QGISBusy as exc:
                busy = str(exc)
            check(f"style: {label} refused while FilterMate is busy", "a filter" in busy, busy)
    finally:
        _operations._RUNNING.clear()
    check("style: nothing changed while busy", gpkg.renderer().type() == renderer_before and
          project.layoutManager().layoutByName("Occupé") is None)
    gpkg.setRenderer(kept_renderer)


def check_edits(project, work):
    """update / delete / add_features on a real GeoPackage, in the edit buffer, and the undo of the turn."""
    from filter_mate.adapters.public_api import feature_edits as edits
    from filter_mate.adapters.public_api.introspection import describe_layer
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    path = os.path.join(work, "edits.gpkg")
    make_vector(path, "GPKG")
    layer = QgsVectorLayer(path, "edits", "ogr")
    project.addMapLayer(layer)
    before = sorted(feature["pop"] for feature in layer.getFeatures())
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("e1", "update_features", {"layer": "edits"}))
    changed = edits.update_features("edits", values={"nom": "Ville", "taux": "2.5"}, expression='"pop" <= 300')
    check("edit: values on the chosen features, in the buffer", changed["changed"] == 3 and changed["unsaved"] and
          layer.isEditable() and sorted(f["nom"] for f in layer.getFeatures() if f["pop"] <= 300) == ["Ville"] * 3
          and {f["taux"] for f in layer.getFeatures() if f["pop"] <= 300} == {2.5}, changed)
    formula = edits.update_features("edits", formulas={"pop": '"pop" * 2'}, expression='"pop" > 5800')
    check("edit: a formula on each feature", formula["changed"] == 2 and
          sorted(f["pop"] for f in layer.getFeatures())[-2:] == [11800, 12000], formula)
    for call, label in ((lambda: edits.update_features("edits", values={"pop": "abc"}, expression="true"), "a text in a number"),
                        (lambda: edits.update_features("edits", values={"fid": 9}, expression="true"), "the key"),
                        (lambda: edits.update_features("edits", values={"nope": 1}, expression="true"), "no field"),
                        (lambda: edits.update_features("edits", values={"pop": 1}), "no choice of features"),
                        (lambda: edits.update_features("edits", formulas={"nom": "env('HOME')"}, expression="true"),
                         "a formula reading the environment"),
                        (lambda: edits.update_features("edits", values={"pop": 1}, expression="file_exists('/etc')"),
                         "an expression reading the disk"),
                        (lambda: edits.update_features("edits", values={"pop": 1}, selected_only=True), "no selection")):
        check(f"edit: refuses {label}", refused(call))
    check("edit: a refused edit changes nothing", sorted(f["pop"] for f in layer.getFeatures())[-1] == 12000)
    recorder.before_call(ToolCallPart("e2", "delete_features", {"layer": "edits"}))
    deleted = edits.delete_features("edits", expression='"pop" = 100')
    check("edit: delete in the buffer", deleted["deleted"] == 1 and layer.featureCount() == 59, deleted)
    recorder.before_call(ToolCallPart("e3", "add_features", {"layer": "edits"}))
    added = edits.add_features("edits", [{"wkt": "POINT(1.44 43.6)", "attributes": {"nom": "Puits", "pop": 7}}],
                               crs="EPSG:4326")
    new = [f for f in layer.getFeatures() if f["nom"] == "Puits"]
    check("edit: add from WKT in another CRS", added["added"] == 1 and len(new) == 1 and
          new[0].geometry().asPoint().x() > 500000, (added, new[0].geometry().asWkt() if new else None))
    check("edit: refuses a line in a point layer", "Point" in refused(
        edits.add_features, "edits", [{"wkt": "LINESTRING(0 0, 1 1)"}]))
    check("edit: refuses a bad WKT", refused(edits.add_features, "edits", [{"wkt": "POINT(abc)"}]))
    details = describe_layer("edits")
    check("edit: describe_layer says it is edited, not saved", details["editing"] and details["unsaved"], details)
    check("edit: nothing is written to the file", sorted(f["pop"] for f in QgsVectorLayer(path, "x", "ogr").getFeatures())
          == before)
    effects = recorder.finish()
    check("edit: the turn keeps its commands", [effect[0] for effect in effects] == ["edits"] and
          (effects[0][2], effects[0][3]) == (0, 4), effects)
    done, left = apply_effects(effects, undo=True)
    check("edit: undo steps back over them", done == ["edits"] and not left and not layer.isModified() and
          sorted(f["pop"] for f in layer.getFeatures()) == before, (done, left))
    apply_effects(effects, undo=False)
    check("edit: redo applies them again", layer.featureCount() == 60 and layer.isModified())
    layer.beginEditCommand("user")
    layer.changeAttributeValue(next(layer.getFeatures()).id(), 2, 1)
    layer.endEditCommand()
    done, left = apply_effects(effects, undo=True)
    check("edit: after an edit of the user, the turn is left as it is", left == ["edits"] and layer.isModified(),
          (done, left))
    layer.rollBack()
    project.removeMapLayer(layer.id())


def check_layouts(project, work):
    """create_layout / export_layout on real layers, and the layout an undo of the turn removes."""
    from filter_mate.adapters.public_api import layouts
    from filter_mate.adapters.public_api.introspection import map_context
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("l1", "create_layout", {"name": "Carte des communes"}))
    made = layouts.create_layout("Carte des communes", title="Communes de plus de 1000 habitants", page="A3",
                                 orientation="portrait", extent_layer="communes")
    layout = project.layoutManager().layoutByName("Carte des communes")
    check("layout: added with its items", layout is not None and made["items"] == [
        "map", "title", "legend", "scale_bar", "north_arrow"] and made["extent_from"] == "layer", made)
    page = layout.pageCollection().page(0).pageSize() if layout is not None else None
    check("layout: A3 portrait", page is not None and (round(page.width()), round(page.height())) == (297, 420),
          (page.width(), page.height()) if page is not None else None)
    plain = layouts.create_layout("Sans décor", layers=["routes"], legend=False, scale_bar=False, north_arrow=False,
                                  extent=[650000, 6859990, 650070, 6860010])
    check("layout: chosen layers, given extent, no decoration", plain["items"] == ["map"] and
          plain["extent_from"] == "given" and plain["layers"] == ["routes"], plain)
    for call, label in ((lambda: layouts.create_layout("Carte des communes"), "a name taken"),
                        (lambda: layouts.create_layout(" "), "no name"),
                        (lambda: layouts.create_layout("x", layers=["nope"]), "an unknown layer"),
                        (lambda: layouts.create_layout("x", page="B0"), "an unknown page"),
                        (lambda: layouts.create_layout("x", extent=[1, 1, 1, 1]), "an empty extent")):
        check(f"layout: refuses {label}", refused(call))
    check("layout: map_context lists them", {"Carte des communes", "Sans décor"} <= set(map_context()["layouts"]),
          map_context()["layouts"])
    folder = os.path.join(work, "layouts_out")
    os.makedirs(folder, exist_ok=True)
    pdf = layouts.export_layout("Carte des communes", folder, "pdf", dpi=96)
    png = layouts.export_layout("Sans décor", folder, "png", dpi=96)
    from qgis.core import QgsLayoutItemLegend
    if layout is not None:  # its size is only known once drawn: after the export
        sheet = layout.pageCollection().page(0).sceneBoundingRect()
        outside = [item.__class__.__name__ for item in layout.items()
                   if hasattr(item, "sceneBoundingRect") and isinstance(item, QgsLayoutItemLegend)
                   and not sheet.contains(item.sceneBoundingRect())]
        check("layout: the legend stays on the page", not outside, outside)
    check("layout: exported as PDF and PNG", pdf["bytes"] > 1000 and png["bytes"] > 1000 and
          os.path.dirname(pdf["path"]) == folder and pdf["path"].endswith(".pdf") and
          open(pdf["path"], "rb").read(4) == b"%PDF" and open(png["path"], "rb").read(4) == b"\x89PNG", (pdf, png))
    for call, label in ((lambda: layouts.export_layout("nope", folder), "an unknown layout"),
                        (lambda: layouts.export_layout("Sans décor", folder, "svg"), "a format"),
                        (lambda: layouts.export_layout("Sans décor", folder, "png", dpi=5000), "a resolution")):
        check(f"layout: export refuses {label}", refused(call))
    effects = recorder.finish()
    check("layout: the turn keeps the layouts it made", sorted(effect[4] for effect in effects) ==
          ["Carte des communes", "Sans décor"], [effect[0] for effect in effects])
    done, left = apply_effects(effects, undo=True)
    check("layout: undo removes them", not left and project.layoutManager().layoutByName("Sans décor") is None and
          project.layoutManager().layoutByName("Carte des communes") is None, (done, left))
    done, left = apply_effects(effects, undo=False)
    back = project.layoutManager().layoutByName("Carte des communes")
    check("layout: redo brings them back with their items", not left and back is not None and
          len([item for item in back.items() if item.__class__.__name__.startswith("QgsLayoutItem")]) >= 5,
          (done, left))
    for layout in list(project.layoutManager().printLayouts()):
        project.layoutManager().removeLayout(layout)


def check_project_crs(project):
    """set_project_crs by authid, code or layer, its refusals, and the CRS an undo of the turn brings back."""
    from filter_mate.adapters.public_api import project_control
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    from qgis.core import QgsCoordinateReferenceSystem
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "set_project_crs", {"crs": "EPSG:2154"}))
    lambert = project_control.set_project_crs("EPSG:2154")
    check("crs: by authid", project.crs().authid() == "EPSG:2154" and lambert["previous"] == "EPSG:4326" and
          lambert["units"] and lambert["geographic"] is False, lambert)
    check("crs: by EPSG code alone", project_control.set_project_crs("3857")["crs"] == "EPSG:3857")
    check("crs: from a layer", project_control.set_project_crs("communes")["crs"] == "EPSG:2154")
    for bad in ("Lambert", "EPSG:999999999", ""):
        check(f"crs: refuses {bad!r}", refused(project_control.set_project_crs, bad) and
              project.crs().authid() == "EPSG:2154")
    effects = recorder.finish()
    check("crs: the turn keeps the CRS before", [effect[:2] for effect in effects] == [("project_crs", "")] and
          effects[0][2:] == ("EPSG:4326", "EPSG:2154"), effects)
    apply_effects(effects, undo=True)
    check("crs: undo brings it back", project.crs().authid() == "EPSG:4326", project.crs().authid())
    apply_effects(effects, undo=False)
    check("crs: redo sets it again", project.crs().authid() == "EPSG:2154", project.crs().authid())
    own = QgsCoordinateReferenceSystem.fromProj("+proj=tmerc +lat_0=0 +lon_0=3 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m")
    check("crs: a CRS of its own comes back by its WKT", project_control.crs_from_definition(
        project_control.crs_definition(own)).isValid())


def check_favorite_layers(project):
    """The layers a favorite would change, found as applying it finds them: what the protected layers check."""
    from filter_mate.adapters.public_api.operations import favorite_layers
    from filter_mate.core.domain.favorites_manager import FilterFavorite
    communes, routes = project.mapLayersByName("communes")[0], project.mapLayersByName("routes")[0]
    favorite = FilterFavorite(id="fav-1", name="Deux couches", expression='"pop" > 100', layer_name="communes",
                              layer_id=communes.id(),
                              remote_layers={"routes": {"layer_id": routes.id(), "display_name": "routes",
                                                        "expression": '"type" = 1'}})

    class Service:
        def get_favorite(self, favorite_id):
            return favorite if favorite_id == "fav-1" else None

        def get_favorite_by_name(self, name):
            return favorite if name == favorite.name else None

        def get_all_favorites(self):
            return [favorite]

    found = favorite_layers("fav-1", service=Service(), project=project)
    check("favorite: its layer and its remote layer", sorted(layer.id() for layer in found) ==
          sorted([communes.id(), routes.id()]), [layer.name() for layer in found])
    check("favorite: by name too", len(favorite_layers("Deux couches", service=Service(), project=project)) == 2)
    check("favorite: unknown, no layer", favorite_layers("nope", service=Service(), project=project) == [])
    check("favorite: nothing changed by reading it", communes.subsetString() == "" and routes.subsetString() == "",
          (communes.subsetString(), routes.subsetString()))


def check_tree_more(project):
    """group_layers above a layer, a group renamed, bookmarks, and what an undo of the turn brings back."""
    from filter_mate.adapters.public_api import layer_tree
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    root = project.layerTreeRoot()

    def names():
        return [(node.name(), layer_tree.group_path(node)) for node in root.findLayers()]

    start = names()
    groups = sorted(group.name() for group in root.findGroups(True))
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "group_layers", {"layers": ["communes"], "above": "routes"}))
    layer_tree.group_layers(["routes"], "Fond")
    moved = layer_tree.group_layers(["communes"], above="routes")
    check("above: in the group of the layer, just over it", moved["group"] == "Fond" and
          [name for name, path in names() if path == "Fond"] == ["communes", "routes"], names())
    check("above: a layer not in the tree, refused", refused(layer_tree.group_layers, ["communes"], above="nope"))
    recorder.before_call(ToolCallPart("c2", "rename_layer", {"layer": "Fond", "name": "Référence", "group": True}))
    renamed = layer_tree.rename_layer("Fond", "Référence", group=True)
    check("group: renamed", renamed["previous"] == "Fond" and root.findGroup("Référence") is not None and
          root.findGroup("Fond") is None, renamed)
    check("group: unknown, refused", refused(layer_tree.rename_layer, "nope", "x", True))
    check("group: a name with /, refused", refused(layer_tree.rename_layer, "Référence", "a/b", True))
    recorder.before_call(ToolCallPart("c3", "bookmark", {"action": "add", "name": "Centre"}))
    added = layer_tree.bookmark("add", "Centre", extent_wkt="POLYGON((650000 6860000, 651000 6860000, "
                                                            "651000 6861000, 650000 6861000, 650000 6860000))")
    check("bookmark: added from an extent", added["bookmarks"] == ["Centre"] and not added["replaced"], added)
    check("bookmark: added again replaces it", layer_tree.bookmark("add", "Centre", extent_wkt="POINT(1 2)")["replaced"]
          and layer_tree.bookmark("list")["bookmarks"] == ["Centre"])
    check("bookmark: unknown, refused", refused(layer_tree.bookmark, "zoom", "nope"))
    check("bookmark: no window to zoom in, refused", refused(layer_tree.bookmark, "zoom", "Centre"))
    effects = recorder.finish()
    check("tree, group and bookmark: kept by the turn", sorted(effect[0] for effect in effects) ==
          ["bookmarks", "tree"], [effect[0] for effect in effects])
    apply_effects(effects, undo=True)
    check("undo: layers back, the group gone, no bookmark", names() == start and
          sorted(group.name() for group in root.findGroups(True)) == groups and
          layer_tree.bookmark("list")["bookmarks"] == [], (names(), start))
    apply_effects(effects, undo=False)
    check("redo: the renamed group and the bookmark again", root.findGroup("Référence") is not None and
          layer_tree.bookmark("list")["bookmarks"] == ["Centre"])
    apply_effects(effects, undo=True)


def check_fields_joins(project):
    """add_field (in the edit buffer, filled by a formula) and join_layers, and what an undo of the turn takes back."""
    from filter_mate.adapters.public_api import fields_joins
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    communes = project.mapLayersByName("communes")[0]
    table = QgsVectorLayer("NoGeometry?field=nom:string&field=region:string", "regions", "memory")
    rows = []
    for feature in communes.getFeatures():
        row = QgsFeature(table.fields())
        row.setAttributes([feature["nom"], "Occitanie"])
        rows.append(row)
    table.dataProvider().addFeatures(rows)
    project.addMapLayer(table)
    fields_before = [field.name() for field in communes.fields()]
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "add_field", {"layer": "communes", "name": "double_pop"}))
    added = fields_joins.add_field("communes", "double_pop", "integer64", formula='"pop" * 2')
    values = {feature["pop"] * 2 == feature["double_pop"] for feature in communes.getFeatures()}
    check("field: added in the edit buffer and filled", added["computed"] == 60 and values == {True} and
          communes.isEditable() and communes.isModified(), added)
    check("field: a name taken, refused", refused(fields_joins.add_field, "communes", "pop", "integer"))
    check("field: an unknown type, refused", refused(fields_joins.add_field, "communes", "z", "float"))
    bad = fields_joins.add_field("communes", "vide", "text", formula='"nope" || 1')
    check("field: a refused formula leaves it empty and says why", bad["computed"] == 0 and "nope" in bad.get(
        "formula_error", ""), bad)
    recorder.before_call(ToolCallPart("c2", "join_layers", {"layer": "communes"}))
    joined = fields_joins.join_layers("communes", "regions", "nom", "nom", fields=["region"])
    # A commune without a name matches no row: QGIS 4.3 no longer joins NULL to NULL, as SQL does not.
    named = [feature for feature in communes.getFeatures() if feature["nom"] not in (None, "") and
             str(feature["nom"]) != "NULL"]
    check("join: the fields of the table beside each feature", joined["fields_added"] == ["regions_region"] and
          named and {feature["regions_region"] for feature in named} == {"Occitanie"}, joined)
    check("join: twice, refused", refused(fields_joins.join_layers, "communes", "regions", "nom", "nom"))
    check("join: to itself, refused", refused(fields_joins.join_layers, "communes", "communes", "nom", "nom"))
    check("join: an unknown field, refused", refused(fields_joins.join_layers, "communes", "regions", "nope", "nom"))
    effects = recorder.finish()
    check("field and join: kept by the turn", sorted(effect[0] for effect in effects) == ["edits", "join"],
          [effect[0] for effect in effects])
    apply_effects(effects, undo=True)
    check("field and join: undo removes them", [field.name() for field in communes.fields()] == fields_before and
          not communes.vectorJoins(), [field.name() for field in communes.fields()])
    apply_effects(effects, undo=False)
    check("field and join: redo brings them back", "double_pop" in communes.fields().names() and
          len(communes.vectorJoins()) == 1, communes.fields().names())
    apply_effects(effects, undo=True)
    communes.rollBack()
    project.removeMapLayer(table.id())


def check_tree_same_names(project):
    """Groups of the same name at two depths: a path names the group at its own level, never one deeper."""
    from filter_mate.adapters.public_api import layer_tree
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    root = project.layerTreeRoot()
    nested = root.insertGroup(0, "A").addGroup("Roads")  # first in the tree: findGroup("Roads") finds it
    top = root.addGroup("Roads")
    routes = project.mapLayersByName("routes")[0]
    start = layer_tree.group_path(root.findLayer(routes.id()))
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "group_layers", {"layers": ["routes"], "group": "Roads"}))
    answer = layer_tree.group_layers(["routes"], "Roads")
    node = root.findLayer(routes.id())
    check("same names: the group at the top is used, none made", answer["groups_made"] == [] and
          node.parent() is top and not nested.children(), (answer, layer_tree.group_path(node)))
    check("same names: the deeper one is reached by its path", layer_tree.group_layers(["routes"], "A/Roads")["moved"]
          and root.findLayer(routes.id()).parent() is nested)
    layer_tree.group_layers(["routes"], "Roads")
    effects = recorder.finish()
    apply_effects(effects, undo=True)
    check("same names: undo puts the layer back, both groups kept", layer_tree.group_path(
        root.findLayer(routes.id())) == start and root.findGroup("A") is not None and
        layer_tree.child_group(root, "Roads") is not None, layer_tree.group_path(root.findLayer(routes.id())))
    for group in (root.findGroup("A"), layer_tree.child_group(root, "Roads")):
        if group is not None:
            group.parent().removeChildNode(group)


def check_layer_tree(project):
    """group_layers, rename_layer and map_theme on the real layer tree, and what an undo of the turn brings back."""
    from filter_mate.adapters.public_api import layer_tree
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.core.agent.messages import ToolCallPart
    root = project.layerTreeRoot()

    def places():
        return [(node.name(), layer_tree.group_path(node), node.itemVisibilityChecked()) for node in root.findLayers()]

    start = places()
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c1", "group_layers", {"layers": ["routes", "communes"], "group": "Base/Admin"}))
    answer = layer_tree.group_layers(["routes", "communes", "nope"], "Base/Admin")
    check("tree: layers put in a group made for them", answer["groups_made"] == ["Base", "Base/Admin"] and
          answer["moved"] == ["routes", "communes"] and answer["not_found"] == ["nope"], answer)
    check("tree: in the order given, checked as before", [row[:2] for row in places()] ==
          [("routes", "Base/Admin"), ("communes", "Base/Admin")] and all(row[2] for row in places()), places())
    check("tree: no layer, refused", refused(layer_tree.group_layers, ["nope"], "X") and root.findGroup("X") is None)
    check("tree: too deep, refused", refused(layer_tree.group_layers, ["routes"], "a/b/c/d/e/f"))
    recorder.before_call(ToolCallPart("c2", "rename_layer", {"layer": "routes", "name": "Routes 31"}))
    renamed = layer_tree.rename_layer("routes", "Routes 31")
    check("rename: a layer", renamed["previous"] == "routes" and project.mapLayersByName("Routes 31"), renamed)
    check("rename: empty, refused", refused(layer_tree.rename_layer, "communes", "  "))
    effects = recorder.finish()
    check("tree: the turn keeps the tree and the name", sorted(effect[0] for effect in effects) == ["layer_name", "tree"],
          [effect[0] for effect in effects])
    apply_effects(effects, undo=True)
    check("tree: undo puts the layers back and removes the groups made", places() == start and
          root.findGroup("Base") is None and project.mapLayersByName("routes"), (places(), start))
    apply_effects(effects, undo=False)
    check("tree: redo makes them again", [row[1] for row in places()] == ["Base/Admin", "Base/Admin"] and
          project.mapLayersByName("Routes 31"), places())
    apply_effects(effects, undo=True)

    communes = project.mapLayersByName("communes")[0]
    root.findLayer(communes.id()).setItemVisibilityChecked(False)
    saved = layer_tree.map_theme("save", "Sans communes")
    check("theme: saved from the map now", saved["themes"] == ["Sans communes"] and not saved["replaced"], saved)
    check("theme: saved again replaces it", layer_tree.map_theme("save", "Sans communes")["replaced"])
    root.findLayer(communes.id()).setItemVisibilityChecked(True)
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("c3", "map_theme", {"action": "apply", "name": "Sans communes"}))
    layer_tree.map_theme("apply", "Sans communes")
    check("theme: applied hides the layer", not root.findLayer(communes.id()).itemVisibilityChecked())
    recorder.before_call(ToolCallPart("c4", "map_theme", {"action": "remove", "name": "Sans communes"}))
    check("theme: removed", layer_tree.map_theme("remove", "Sans communes")["themes"] == [])
    check("theme: unknown, refused", refused(layer_tree.map_theme, "apply", "nope"))
    check("theme: an action it does not know, refused", refused(layer_tree.map_theme, "erase", "x"))
    effects = recorder.finish()
    apply_effects(effects, undo=True)
    check("theme: undo shows the layer again and brings the theme back",
          root.findLayer(communes.id()).itemVisibilityChecked() and layer_tree.theme_names() == ["Sans communes"],
          [effect[0] for effect in effects])
    layer_tree.map_theme("remove", "Sans communes")


def check_processing(project, gpkg):
    """find / describe / run_algorithm on real layers: what may run, how its layers come, Stop."""
    try:
        sys.path.append(os.path.join(QgsApplication.pkgDataPath(), "python", "plugins"))
        from processing.core.Processing import Processing
        Processing.initialize()
    except ImportError:
        check("processing: the plugin is there", False)
        return
    from qgis.PyQt.QtCore import QTimer
    from filter_mate.adapters.public_api import processing_tools as tools
    from filter_mate.adapters.public_api import operations
    from filter_mate.adapters.agent.bounded_http import abort_active

    found = tools.find_algorithms("buffer")
    check("processing: buffer is found", "native:buffer" in [row["id"] for row in found["algorithms"]], found)
    listed = {row["id"] for row in tools.find_algorithms("a", limit=50)["algorithms"]}
    everything = set()
    for word in ("select", "sql", "truncate", "import", "download", "upload", "style", "projection", "index", "package"):
        everything |= {row["id"] for row in tools.find_algorithms(word, limit=50)["algorithms"]}
    leaked = sorted(item for item in everything | listed if item.split(":")[0] not in ("native", "qgis")
                    or any(word in item for word in ("selectby", "executesql", "truncate", "importinto", "download",
                                                    "setstyle", "definecurrentprojection", "createspatialindex",
                                                    "package", "python")))
    check("processing: nothing that acts in place, runs code or leaves QGIS is listed", not leaked, leaked)
    described = tools.describe_algorithm("native:buffer")
    names = [row["name"] for row in described["parameters"]]
    check("processing: describe", names[0] == "INPUT" and "OUTPUT" in names and "destination" in
          described["parameters"][names.index("OUTPUT")], described)
    for algorithm in ("native:truncatetable", "qgis:executesql", "native:selectbyexpression", "gdal:buffervectors",
                      "native:package", "nope:nope"):
        check(f"processing: {algorithm} is refused", refused(tools.describe_algorithm, algorithm)
              and refused(tools.run_algorithm, algorithm, {}))

    before = set(project.mapLayers())
    made = tools.run_algorithm("native:buffer", {"INPUT": "communes", "DISTANCE": 10})
    added = set(project.mapLayers()) - before
    layer = project.mapLayer(made["layers"][0]["layer_id"]) if made["layers"] else None
    check("processing: one layer added, from a temporary GeoPackage", len(added) == 1 and layer is not None
          and layer.providerType() == "ogr" and ".gpkg" in layer.source() and made["layers"][0]["feature_count"] == 60
          and layer.name() == "Buffer", made)
    check("processing: the input is untouched", gpkg.featureCount() == 60 and gpkg.subsetString() == "")
    gpkg.selectByExpression('"pop" <= 300')
    chosen = tools.run_algorithm("native:buffer", {"INPUT": {"layer": "communes", "selected_only": True}},
                                 names={"OUTPUT": "zone choisie"})
    check("processing: the selection, a chosen name", chosen["layers"][0]["feature_count"] == 3 and
          chosen["layers"][0]["name"] == "zone choisie", chosen)
    gpkg.removeSelection()
    calc = tools.run_algorithm("native:fieldcalculator", {"INPUT": "communes", "FIELD_NAME": "double",
                                                          "FIELD_TYPE": "Integer", "FORMULA": '"pop" * 2'})
    out = project.mapLayer(calc["layers"][0]["layer_id"])
    check("processing: a formula, an option given by its text", out is not None and
          sorted(feature["double"] for feature in out.getFeatures())[:2] == [200, 400], calc)
    for parameters, label in (({"INPUT": gpkg.source(), "DISTANCE": 1}, "a path as input"),
                              ({"INPUT": "https://example.org/a.geojson"}, "a URL as input"),
                              ({"INPUT": "communes", "OUTPUT": "/tmp/out.gpkg"}, "a path as output"),
                              ({"INPUT": "communes", "NOPE": 1}, "an unknown parameter"),
                              ({"INPUT": "communes", "DISTANCE": "abc"}, "a bad value"),
                              ({"INPUT": {"layer": "communes", "selected_only": True}}, "an empty selection")):
        check(f"processing: refuses {label}", refused(tools.run_algorithm, "native:buffer", parameters))
    check("processing: refuses a formula that reads the environment", "env" in refused(
        tools.run_algorithm, "native:fieldcalculator", {"INPUT": "communes", "FIELD_NAME": "h", "FORMULA": "env('HOME')"}))
    check("processing: refuses an extent that names a file", refused(
        tools.run_algorithm, "native:extractbyextent", {"INPUT": "communes", "EXTENT": gpkg.source()}))
    clipped = tools.run_algorithm("native:extractbyextent", {"INPUT": "communes",
                                                             "EXTENT": [650000.5, 6859999, 650010.5, 6860001]})
    check("processing: an extent as four numbers", clipped["layers"][0]["feature_count"] == 10, clipped)
    stats_id = "native:basicstatisticsforfields" if tools._registry().algorithmById(
        "native:basicstatisticsforfields") else "qgis:basicstatisticsforfields"
    stats = tools.run_algorithm(stats_id, {"INPUT_LAYER": "communes", "FIELD_NAME": "pop"})
    check("processing: the values an algorithm answers", stats.get("values", {}).get("SUM") == 183000.0, stats)
    quiet = tools.run_algorithm(stats_id, {"INPUT_LAYER": "communes", "FIELD_NAME": "pop"}, share_values=False)
    check("processing: values left out when they are not shared", "values" not in quiet, quiet)

    operations._RUNNING.append("something")
    check("processing: refused while FilterMate is busy", "already running" in refused(
        tools.run_algorithm, "native:buffer", {"INPUT": "communes"}))
    operations._RUNNING.clear()
    seen = {}
    QTimer.singleShot(0, lambda: seen.update(busy=operations.busy_reason()))
    tools.run_algorithm("native:buffer", {"INPUT": "communes", "DISTANCE": 1, "SEGMENTS": 50})
    check("processing: busy while it runs, free after", "Processing" in seen.get("busy", "") and
          not operations.busy_reason(), seen)
    count = len(project.mapLayers())
    QTimer.singleShot(300, abort_active)
    stopped = refused(tools.run_algorithm, "native:randompointsinextent", {
        "EXTENT": "0,100000,0,100000 [EPSG:2154]", "POINTS_NUMBER": 3000000, "MIN_DISTANCE": 0,
        "TARGET_CRS": "EPSG:2154"})
    check("processing: Stop ends a long algorithm, nothing added", stopped == "stopped" and
          len(project.mapLayers()) == count and not operations.busy_reason(), stopped)
    for layer_id in set(project.mapLayers()) - before:
        project.removeMapLayer(layer_id)


def main(introspection):
    work = tempfile.mkdtemp()
    project = QgsProject.instance()
    gpkg_path = os.path.join(work, "communes.gpkg")
    shp_path = os.path.join(work, "routes.shp")
    make_vector(gpkg_path, "GPKG")
    make_vector(shp_path, "ESRI Shapefile")
    gpkg = QgsVectorLayer(gpkg_path, "communes", "ogr")
    shp = QgsVectorLayer(shp_path, "routes", "ogr")
    project.addMapLayers([gpkg, shp])
    check("fixtures valid", gpkg.isValid() and shp.isValid() and gpkg.featureCount() == 60)

    # --- describe_layer
    details = introspection.describe_layer("communes")
    names = [item["name"] for item in details["fields"]]
    check("describe by name: fields", {"nom", "pop", "taux", "creation"} <= set(names), names)
    check("describe: kind, crs, count", (details["layer_kind"], details["crs_authid"], details["feature_count"]) ==
          ("vector", "EPSG:2154", 60), details)
    check("describe: geometry type", "Point" in details["geometry_type"], details["geometry_type"])
    check("describe by id", introspection.describe_layer(gpkg.id())["name"] == "communes")
    check("describe: absent is None", introspection.describe_layer("nope") is None)
    json.dumps(details)
    check_map_details(introspection, project, gpkg, shp, details)
    check_reading(introspection, project, gpkg, work)
    check_processing(project, gpkg)
    check_style(project, gpkg, work)
    check_edits(project, work)
    check_layouts(project, work)
    check_project_crs(project)
    check_tree_same_names(project)
    check_layer_tree(project)
    check_fields_joins(project)
    check_tree_more(project)
    check_favorite_layers(project)

    if gdal is not None:
        raster_path = os.path.join(work, "occupation.tif")
        make_raster(raster_path)
        raster = QgsRasterLayer(raster_path, "occupation", "gdal")
        project.addMapLayer(raster)
        classes = [QgsPalettedRasterRenderer.Class(1, label="Foret"), QgsPalettedRasterRenderer.Class(2, label="Eau")]
        raster.setRenderer(QgsPalettedRasterRenderer(raster.dataProvider(), 1, classes))
        info = introspection.describe_layer("occupation")
        check("raster: kind and bands", info["layer_kind"] == "raster" and len(info["bands"]) == 2, info)
        check("raster: palette on its band only", info["bands"][0].get("classes") == [
            {"value": 1, "label": "Foret"}, {"value": 2, "label": "Eau"}] and "classes" not in info["bands"][1], info)
        check("raster: pixel size", info["pixel_size"] == 25, info)
        json.dumps(info)
        try:
            introspection.field_values("occupation", "x")
            check("raster has no field values", False)
        except ValueError:
            check("raster has no field values", True)
        try:
            introspection.preview_filter("occupation", "1=1")
            check("raster cannot be previewed", False)
        except ValueError:
            check("raster cannot be previewed", True)

    fixtures = os.environ.get("FM_FIXTURES", "")
    ept = os.path.join(fixtures, "cloud_ept", "ept.json")
    if fixtures and os.path.exists(ept):
        cloud = QgsPointCloudLayer(ept, "lidar", "ept")
        if cloud.isValid():
            project.addMapLayer(cloud)
            info = introspection.describe_layer("lidar")
            if info["layer_kind"] == "other":  # the plugin does not handle point clouds on this version
                print("SKIP point cloud: not supported by FilterMate on this version")
            else:
                check("point cloud: kind and attributes", info["layer_kind"] == "point_cloud" and {
                    "Z", "Classification"} <= set(info["attributes"]), info)
                check("point cloud: point count", info["feature_count"] > 0, info)
                json.dumps(info)
        else:
            print("SKIP point cloud: no EPT provider in this build")

    # --- field_values
    values = introspection.field_values("communes", "nom", limit=200)
    check("text values, NULL left out", len(values["values"]) == 59 and None not in values["values"], values)
    check("not truncated when all fit", values["truncated"] is False)
    limited = introspection.field_values("communes", "nom", limit=10)
    check("limit and truncated flag", len(limited["values"]) == 10 and limited["truncated"] is True, limited)
    found = introspection.field_values("communes", "nom", search="saint", limit=200)
    check("search ignores case", found["values"] and all("Saint" in value for value in found["values"]), found)
    numeric = introspection.field_values("communes", "pop", limit=5)
    check("numeric min and max", (numeric["minimum"], numeric["maximum"]) == (100, 6000), numeric)
    dates = introspection.field_values("communes", "creation", limit=3)
    check("dates in ISO", dates["values"][0] == "2020-01-01" and dates["minimum"] == "2020-01-01", dates)
    json.dumps([values, numeric, dates])
    check("unknown field is None", introspection.field_values("communes", "nope") is None)
    gpkg.setSubsetString('"pop" <= 300')
    filtered = introspection.field_values("communes", "pop", limit=50)
    check("the current filter applies", filtered["values"] == [100, 200, 300], filtered)
    gpkg.setSubsetString("")

    # --- preview_filter
    for layer, label in ((gpkg, "gpkg"), (shp, "shapefile")):
        name = layer.name()
        layer.setSubsetString('"pop" = 100')
        preview = introspection.preview_filter(name, '"pop" > 1000')
        check(f"{label}: preview count", preview["valid"] is True and preview["feature_count"] == 50, preview)
        read = sum(1 for _ in layer.getFeatures())
        check(f"{label}: the layer is untouched", layer.subsetString() == '"pop" = 100' and read == 1,
              (layer.subsetString(), read, layer.featureCount()))
        layer.setSubsetString("")
        none = introspection.preview_filter(name, '"pop" > 999999')
        check(f"{label}: valid and empty is not an error", none["valid"] is True and none["feature_count"] == 0, none)
        for bad in ('"pop" >', '"inexistant" = 1', '"pop" > > 1'):
            broken = introspection.preview_filter(name, bad)
            check(f"{label}: invalid {bad!r}", broken["valid"] is False and broken["error"], broken)
    check("preview: absent is None", introspection.preview_filter("nope", "1=1") is None)
    check("no preview layer left in the project", len(project.mapLayersByName("filtermate_preview")) == 0)

    for attack in ("$a$'$a$ IS NULL; DROP TABLE x; --'", "E'\\'' IS NULL; DROP TABLE x; --'", "pg_sleep(1) IS NULL"):
        try:
            introspection.preview_filter("communes", attack)
            check(f"preview refuses {attack!r}", False)
        except ValueError:
            check(f"preview refuses {attack!r}", True)

    # Virtual fields exist for QGIS only: the SQL of the source cannot test them.
    virtual_index = gpkg.addExpressionField('"pop" * 2', QgsField("double_pop", QVariant.Int))
    fields = {item["name"]: item["filterable"] for item in introspection.describe_layer("communes")["fields"]}
    check("virtual field is not filterable", fields["double_pop"] is False and fields["pop"] is True, fields)
    virtual = introspection.preview_filter("communes", '"double_pop" > 15')
    check("virtual field is refused by preview", virtual["valid"] is False and "double_pop" in virtual["error"], virtual)
    gpkg.removeExpressionField(virtual_index)

    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=a:integer", "memoire", "memory")
    project.addMapLayer(memory)
    try:
        introspection.preview_filter("memoire", '"a" > 1')
        check("memory layer cannot be previewed", False)
    except ValueError:
        check("memory layer cannot be previewed", True)

    # Same name on two kinds: apply_filter takes the vector one, so everything must.
    if gdal is not None:
        twin = QgsRasterLayer(raster_path, "communes", "gdal")
        project.addMapLayer(twin)
        check("same name: the vector layer is described", introspection.describe_layer("communes")["layer_kind"] == "vector")
        check("same name: the vector layer is tried",
              introspection.preview_filter("communes", '"pop" > 1000')["feature_count"] == 50)
        check("same name: the raster by its id", introspection.describe_layer(twin.id())["layer_kind"] == "raster")
        project.removeMapLayer(twin.id())

    # Reading a broken point cloud crashes QGIS: it must be refused before.
    broken_cloud = QgsPointCloudLayer(os.path.join(work, "absent.copc.laz"), "broken", "copc")
    project.addMapLayers([broken_cloud], False)
    if project.mapLayer(broken_cloud.id()) is not None:
        try:
            introspection.describe_layer("broken")
            check("broken point cloud is refused", False)
        except ValueError:
            check("broken point cloud is refused", True)
        project.removeMapLayer(broken_cloud.id())

    # --- map_context, without a window
    gpkg.selectByExpression('"pop" <= 200')
    context = introspection.map_context()
    check("no canvas: available is False", context["available"] is False, context)
    check("selections are listed", context["selections"] == [
        {"layer_id": gpkg.id(), "name": "communes", "selected_count": 2}], context)
    json.dumps(context)

    # --- the chat tools, on the real accessor
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor

    class PublicApi:
        @staticmethod
        def get_active_filters():  # what list_layers asks the plugin
            return {}

    accessor = QGISFilterMateAccessor(PublicApi(), None)
    executor = ToolExecutor(chat_tools(), build_handlers(accessor, os.path.join(work, "exports")))

    def tool(name, **arguments):
        result = executor.execute(ToolCallPart("c", name, arguments))
        return result.is_error, result.content

    error, content = tool("describe_layer", layer="communes")
    check("tool describe_layer", not error and json.loads(content)["name"] == "communes", content)
    error, content = tool("field_values", layer="communes", field="pop", limit=3)
    check("tool field_values", not error and len(json.loads(content)["values"]) == 3, content)
    error, content = tool("preview_filter", layer_name="communes", expression='"pop" > 1000')
    check("tool preview_filter", not error and json.loads(content)["feature_count"] == 50, content)
    error, content = tool("preview_filter", layer_name="communes", expression="1=1; DROP TABLE x")
    check("tool refuses a second statement", error and "WHERE" in content, content)
    error, content = tool("describe_layer", layer=gpkg.id())
    check("tool accepts an id", not error and json.loads(content)["name"] == "communes", content)
    filtered_before = gpkg.subsetString()
    error, content = tool("apply_filter", layer_name="communes", expression='"pop" >')
    check("tool: invalid filter is not applied", error and "invalid" in content and gpkg.subsetString() == filtered_before,
          content)
    error, content = tool("describe_layer", layer="nope")
    check("tool: layer not found", error and content == "Layer not found.", content)
    error, content = tool("map_context")
    check("tool map_context", not error and json.loads(content)["available"] is False, content)
    error, content = tool("list_layers")
    rows = {} if error else {row["name"]: (rank, row["group"], row["visible"])
                             for rank, row in enumerate(json.loads(content)["layers"])}
    check("tool list_layers: order of the tree, groups", not error and rows["routes"][0] < rows["communes"][0] and
          rows["communes"][1:] == ("Fonds / Admin", True) and rows["routes"][1:] == ("", True), content)
    error, content = tool("layer_statistics", layer="communes", field="pop")
    check("tool layer_statistics", not error and json.loads(content)["statistics"]["sum"] == 183000.0, content)
    error, content = tool("layer_statistics", layer="communes", measure="area")
    check("tool layer_statistics: a refusal the model can read", error and "polygons" in content, content)
    error, content = tool("layer_statistics", layer="communes", field="nope")
    check("tool layer_statistics: field not found", error and content == "Layer or field not found.", content)
    error, content = tool("sample_features", layer="communes", limit=1, fields=["nom", "pop"])
    check("tool sample_features", not error and json.loads(content)["features"][0]["attributes"] ==
          {"nom": "Saint-01", "pop": 100}, content)
    error, content = tool("sample_features", layer="communes", expression="env('HOME') = 'x'")
    check("tool sample_features refuses a function outside the list", error and "expression" in content, content)
    error, content = tool("identify_at", x=650002, y=6860000, crs="EPSG:2154", tolerance=0.4, layers=["routes"])
    check("tool identify_at", not error and json.loads(content)["layers"][0]["features"][0]["attributes"]["pop"] == 200,
          content)

    # --- driving QGIS (adapters.public_api.project_control), without a window
    from filter_mate.adapters.public_api import project_control

    selected = project_control.select_features("communes", '"pop" <= 300')
    check("select by expression", selected["selected_count"] == 3 and gpkg.selectedFeatureCount() == 3, selected)
    check("select adds", project_control.select_features("communes", '"pop" = 400', add=True)["selected_count"] == 4)
    check("select clears", project_control.select_features("communes", clear=True)["selected_count"] == 0)
    for bad in ('"pop" >', 'DROP TABLE x', '"inconnu" > 3', "file_exists('/etc/passwd')", "\"pop\" <= ascii(env('HOME'))",
                "sqlite_fetch_and_increment('/tmp/x.sqlite','t','id','k','a',map('s','1'))>0"):
        try:
            project_control.select_features("communes", bad)
            check(f"bad expression refused {bad!r}", False)
        except ValueError:
            check(f"bad expression refused {bad!r}", True)
    try:
        project_control.zoom_to("communes")
        check("zoom without a window is refused", False)
    except ValueError:
        check("zoom without a window is refused", True)
    project_control.select_features("communes", '"pop" = 100')
    try:
        project_control.select_features("communes", '"inconnu" > 3')
    except ValueError:
        pass
    check("a refused expression keeps the selection", gpkg.selectedFeatureCount() == 1, gpkg.selectedFeatureCount())
    check("geometry functions are accepted", project_control.select_features("communes", "area($geometry) >= 0")["layer_name"] == "communes")
    project_control.select_features("communes", clear=True)
    hidden = project_control.set_layers_visibility(["communes", "nope"], False)
    node = project.layerTreeRoot().findLayer(gpkg.id())
    check("visibility", hidden["done"] == ["communes"] and hidden["failed"] == {"nope": "layer not found"} and
          node is not None and not node.isVisible(), hidden)
    project_control.set_layers_visibility([gpkg.id()], True)
    check("visible again", node.isVisible())

    added = project_control.add_layer(gpkg_path, name="communes_bis")
    check("add a local layer", added["name"] == "communes_bis" and added["feature_count"] == 60 and
          len(project.mapLayersByName("communes_bis")) == 1, added)
    for source, label in (("http://example.org/a.geojson", "http"), ("/vsicurl/http://x/a.gpkg", "vsicurl http"),
                          (os.path.join(work, "absent.gpkg"), "absent file"), ("PG:host=127.0.0.1 dbname=x", "PG"),
                          ("//127.0.0.1/share/x.gpkg", "UNC"), ("CSV:/etc/passwd", "CSV prefix"), ("/etc/passwd", "no data file"),
                          ("type=xyz&u%72l=http%3A%2F%2F127.0.0.1%2F", "obscured URI"),
                          ("<GDAL_WMS><ServerUrl>http://127.0.0.1/</ServerUrl></GDAL_WMS>", "inline XML")):
        try:
            project_control.add_layer(source)
            check(f"add refuses {label}", False)
        except ValueError:
            check(f"add refuses {label}", True)
    removed = project_control.remove_layers(["communes_bis", "nope"])
    check("remove", removed["done"] == ["communes_bis"] and not project.mapLayersByName("communes_bis"), removed)

    # --- open data, against a platform on this machine
    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            seen.append(self.path)
            if self.path.startswith("/api/1/datasets/"):
                body = json.dumps({"data": [{"id": "ae", "title": "Communes", "organization": {"name": "IGN"},
                                             "page": "https://www.data.gouv.fr/datasets/ae", "resources": [
                                                 {"title": "GeoJSON", "format": "geojson", "url": "https://static.data.gouv.fr/c.geojson"},
                                                 {"title": "Doc", "format": "pdf", "url": "https://static.data.gouv.fr/d.pdf"}]}]})
            else:
                body = "not json"
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    local = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        found = project_control.search_open_data("communes", platform=local, extra_domains=f"{local}:datagouv")
        check("open data: datasets and geo resources only", found["count"] == 1 and
              [r["format"] for r in found["datasets"][0]["resources"]] == ["geojson"], found)
        check("open data: the query went to the platform", seen and "q=communes" in seen[0], seen)
        try:
            project_control.search_open_data("x", platform=local)
            check("open data: a platform not allowed is refused", False)
        except ValueError:
            check("open data: a platform not allowed is refused", True)
        check("open data: nothing was sent to it", len(seen) == 1, seen)
        try:
            project_control.search_open_data("x", platform=local, extra_domains=f"{local}:ckan")
            check("open data: a non-JSON answer is an error", False)
        except ValueError:
            check("open data: a non-JSON answer is an error", True)
        try:
            project_control.search_open_data("x", platform="http://127.0.0.1:9", extra_domains="http://127.0.0.1:9:datagouv")
            check("open data: unreachable is an error", False)
        except ValueError:
            check("open data: unreachable is an error", True)
    finally:
        server.shutdown()
        server.server_close()

    check_remote_files(project_control, project, work)
    project.removeAllMapLayers()
    shutil.rmtree(work, ignore_errors=True)


def check_remote_files(project_control, project, work):
    """add_layer on public URLs whose transport is sent to a server on this machine, answering as real portals do.

    An Opendatasoft export (what data.gouv.fr lists for a harvested portal) is made on request: no size, no parts,
    an address that ends with the name of a format. GDAL cannot read it where it is.
    """
    from filter_mate.adapters.agent import bounded_http
    from qgis.PyQt.QtCore import QTimer

    for driver, name in (("ESRI Shapefile", "served.shp"), ("GeoJSON", "served.geojson"), ("CSV", "served.csv")):
        make_vector(os.path.join(work, name), driver)
    with zipfile.ZipFile(os.path.join(work, "served.zip"), "w") as archive:
        for extension in ("shp", "shx", "dbf", "prj", "cpg"):
            if os.path.exists(os.path.join(work, "served." + extension)):
                archive.write(os.path.join(work, "served." + extension), "export/communes." + extension)
    with zipfile.ZipFile(os.path.join(work, "notes.zip"), "w") as archive:
        archive.writestr("lisez-moi.txt", "rien")
    with zipfile.ZipFile(os.path.join(work, "bomb.zip"), "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("communes.geojson", b" " * (3 * 1024 * 1024))  # a few KB that unpack to 3 MB

    def served(name):
        with open(os.path.join(work, name), "rb") as handle:
            return handle.read()

    exports = {"/exports/shp": ("served.zip", "communes-test.zip", "application/zip"),
               "/exports/csv": ("served.csv", "communes-test.csv", "text/csv"),
               "/exports/geojson": ("served.geojson", "communes-test.geojson", "application/json")}
    public = "https://fm-test.example.org"
    asked = []

    class Portal(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def start(self, status, headers):
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()

        def stream(self, pieces):
            for piece in pieces:
                self.wfile.write(b"%x\r\n" % len(piece) + piece + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")

        def whole(self, data, content_type="application/octet-stream"):
            self.start(200, {"Content-Type": content_type, "Content-Length": str(len(data))})
            self.wfile.write(data)

        def do_GET(self):
            route = self.path.split("?", 1)[0]
            asked.append(route)
            try:
                self.route(route)
            except OSError:  # the probe leaves once it has the headers
                self.close_connection = True

        def route(self, route):
            if route in exports:
                name, sent_name, content_type = exports[route]
                data = served(name)
                self.start(200, {"Content-Type": content_type + "; charset=utf-8", "Transfer-Encoding": "chunked",
                                 "Content-Disposition": f'attachment; filename="{sent_name}"'})
                self.stream(data[start:start + 4096] for start in range(0, len(data), 4096))
            elif route == "/moved":
                self.start(302, {"Location": public + "/exports/geojson", "Content-Length": "0"})
            elif route == "/missing.geojson":
                self.start(404, {"Content-Length": "0"})
            elif route == "/page.geojson":
                self.whole(b"<html>sign in</html>", "text/html; charset=utf-8")
            elif route == "/huge.geojson":
                self.start(200, {"Content-Type": "application/geo+json", "Content-Length": str(10 * 1024 ** 3)})
                self.close_connection = True
            elif route == "/endless.geojson":
                self.start(200, {"Content-Type": "application/geo+json", "Transfer-Encoding": "chunked"})
                self.stream(b"x" * 65536 for _ in range(32))
            elif route == "/slow.geojson":
                self.start(200, {"Content-Type": "application/geo+json", "Transfer-Encoding": "chunked"})
                self.stream(time.sleep(pause) or b"{" for pause in (0, 4))
            elif route == "/cut-stream.geojson":  # an export cut while it is made, as a portal would
                self.start(200, {"Content-Type": "application/geo+json", "Transfer-Encoding": "chunked"})
                self.wfile.write(b"1000\r\n" + b"{" * 100)
                self.close_connection = True
            elif route == "/captcha.geojson":  # the first byte is a file, the file a web page
                if self.headers.get("Range"):
                    self.start(200, {"Content-Type": "application/geo+json", "Transfer-Encoding": "chunked"})
                    self.stream([b"{"])
                else:
                    self.whole(b"<html>are you a robot?</html>", "text/html")
            elif route == "/bomb.zip":
                self.whole(served("bomb.zip"), "application/zip")
            elif route == "/cut.geojson":
                self.start(200, {"Content-Type": "application/geo+json", "Content-Length": "5000"})
                self.wfile.write(b"{" * 100)
                self.close_connection = True
            elif route == "/empty.zip":
                self.whole(b"", "application/zip")
            elif route == "/broken.zip":
                self.whole(b"not a zip", "application/zip")
            elif route == "/notes.zip":
                self.whole(served("notes.zip"), "application/zip")
            elif route == "/parts.gpkg":  # a static file server: the first byte, and the size
                self.start(206, {"Content-Type": "application/geopackage+sqlite3", "Content-Length": "1",
                                 "Content-Range": "bytes 0-0/98304"})
                self.wfile.write(b"S")
            else:
                self.start(404, {"Content-Length": "0"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Portal)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    local = f"http://127.0.0.1:{server.server_address[1]}"
    real_fetch = project_control.fetch
    project_control.fetch = lambda url, **options: real_fetch(url.replace(public, local), **options)
    copies = os.path.join(QgsApplication.qgisSettingsDirPath(), "filtermate", "open_data")
    limits = project_control.MAX_DOWNLOAD, project_control.DOWNLOAD_TIMEOUT_MS

    def copied():
        return {os.path.join(folder, name) for folder, _, names in os.walk(copies) for name in names}

    already = copied()  # a profile that is not the one of a container keeps what it has

    def kept():
        return sorted(os.path.basename(path) for path in copied() - already)

    def refused(label, route, needle):
        before = kept()
        try:
            project_control.add_layer(public + route)
            check(f"remote: {label}", False, "a layer was added")
        except ValueError as exc:
            check(f"remote: {label}", needle in str(exc) and kept() == before, f"{exc} / {kept()}")

    try:
        added = project_control.add_layer(public + "/exports/shp")
        source = project.mapLayer(added["layer_id"]).source().replace("\\", "/")
        check("remote: a zipped shapefile made on request is copied, then read in its archive",
              added["feature_count"] == 60 and added["name"] == "communes-test" and source.startswith("/vsizip/")
              and source.endswith("communes-test.zip/export/communes.shp") and "/filtermate/open_data/" in source,
              f"{added} {source}")
        added = project_control.add_layer(public + "/exports/csv?use_labels=true", name="table")
        check("remote: a CSV export", added["feature_count"] == 60 and added["name"] == "table", added)
        added = project_control.add_layer(public + "/exports/geojson")
        check("remote: a GeoJSON export", added["feature_count"] == 60 and added["name"] == "communes-test", added)
        added = project_control.add_layer(public + "/moved", name="moved")
        check("remote: a redirect is followed to the file", added["feature_count"] == 60, added)
        added = project_control.add_layer(public + "/exports/geojson", name="again")
        check("remote: the same file again, while a layer reads the first copy", added["feature_count"] == 60, added)
        check("remote: one copy per download, nothing half written", kept() == [
            "communes-test.csv", "communes-test.geojson", "communes-test.geojson", "communes-test.geojson",
            "communes-test.zip"], kept())
        check("remote: the first request asks for one byte, the copy for the file",
              asked.count("/exports/shp") == 2 and asked.count("/exports/csv") == 2, asked)
        first = project.mapLayersByName("communes-test")
        first = next(layer for layer in first if layer.source().startswith("/vsizip/"))
        zipped = first.source()[len("/vsizip/"):].split(".zip/", 1)[0] + ".zip"
        try:
            project_control.add_layer(public + "/exports/shp", kind="raster")
            check("remote: the same link as a raster is refused", False)
        except ValueError as exc:
            check("remote: the same link as a raster is refused", "holds no raster layer" in str(exc), exc)
        first.setSubsetString('"pop" > 100')  # the provider opens the file again
        check("remote: a failure never removes the copy another layer reads",
              os.path.isfile(zipped) and first.isValid() and first.featureCount() == 59,
              f"{zipped} {first.isValid()} {first.featureCount()}")
        first.setSubsetString("")

        refused("an error of the server is said with its status", "/missing.geojson", "(404)")
        refused("a web page is not data", "/page.geojson", "web page")
        asked.clear()
        refused("a file known to be too large is not started", "/huge.geojson", "10240 MB")
        check("remote: only its size was asked", asked == ["/huge.geojson"], asked)
        project_control.MAX_DOWNLOAD = 256 * 1024
        refused("a file of no known size stops at the limit", "/endless.geojson", "weighs more than the 0.2 MB")
        project_control.MAX_DOWNLOAD = limits[0]
        project_control.DOWNLOAD_TIMEOUT_MS = 1500
        refused("a server too slow is said so", "/slow.geojson", "too slow")
        project_control.DOWNLOAD_TIMEOUT_MS = limits[1]
        QTimer.singleShot(1500, bounded_http.abort_active)
        refused("Stop ends a download", "/slow.geojson", "stopped")
        refused("a file cut before its end is not a shorter layer", "/cut.geojson", "lost before the end")
        refused("an export cut while it is made is not a shorter layer", "/cut-stream.geojson", "lost before the end")
        refused("a web page sent for the file is said so", "/captcha.geojson", "web page instead of the file")
        unzipped = project_control.MAX_UNZIPPED
        project_control.MAX_UNZIPPED = 1024 * 1024
        refused("an archive that would unpack to too much is not read", "/bomb.zip", "would unpack to more than 1.0 MB")
        project_control.MAX_UNZIPPED = unzipped
        refused("an empty file", "/empty.zip", "empty file")
        refused("a zip that is none", "/broken.zip", "not a zip archive")
        refused("an archive with no layer is said so and not kept", "/notes.zip", "holds no vector layer")
        asked.clear()
        refused("a file its server gives by parts is left where it is", "/parts.gpkg", "where it is")
        check("remote: it was not copied", asked == ["/parts.gpkg"], asked)
    finally:
        project_control.fetch = real_fetch
        project_control.MAX_DOWNLOAD, project_control.DOWNLOAD_TIMEOUT_MS = limits
        server.shutdown()
        server.server_close()
        project.removeAllMapLayers()
        for path in copied() - already:
            shutil.rmtree(os.path.dirname(path), ignore_errors=True)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    _link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    from filter_mate.adapters.public_api import introspection as module
    main(module)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
