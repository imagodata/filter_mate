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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPalettedRasterRenderer, QgsPointCloudLayer,
    QgsPointXY, QgsProject, QgsRasterLayer, QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDate, QVariant

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

    project.removeAllMapLayers()
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    from filter_mate.adapters.public_api import introspection as module
    main(module)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
