# -*- coding: utf-8 -*-
"""The agent tells how many features a filtered GeoPackage keeps, in a real (headless) QGIS. Run inside a qgis/qgis
image:

    docker run --rm --init -e DBUS_SESSION_BUS_ADDRESS=disabled: -v "$PWD":/src:ro qgis/qgis:stable \\
        python3 /src/tests/qgis_headless/check_gpkg_feature_count.py

2026-11-14: ``featureCount()`` of the commune layer of the BD TOPO (a GeoPackage without ``gpkg_ogr_contents``)
answered 930 under ``"population" > 20000``, which keeps 7, and the agent showed "930 / 930". QGIS counts such a
table without its filter, and from QGIS 3.26 any GeoPackage table of 100 000 features or more
(``QgsOgrLayer::GetApproxFeatureCount``). The files are built here to reproduce both. With FM_BDTOPO (the path of a
BD TOPO GeoPackage in the container), its commune and batiment layers are checked too.

Prints one PASS / FAIL line per check, INFO lines for what QGIS itself counts; exits with 1 when one failed.
"""
import json
import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from osgeo import gdal, ogr, osr  # noqa: E402
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer  # noqa: E402

gdal.UseExceptions()
RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {detail}" if not condition else ""))


def make_gpkg(path, table, count, contents=True, delete=None):
    """``count`` points, ``population`` = fid * 100, ``usage`` 'Industriel' one fid in 100 and ``nom`` École, école,
    ECOLE or Ecole; written by GDAL, without ``gpkg_ogr_contents`` when ``contents`` is False (the BD TOPO has
    none)."""
    options = [] if contents else ["ADD_GPKG_OGR_CONTENTS=NO"]
    dataset = ogr.GetDriverByName("GPKG").CreateDataSource(path, options=options)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    layer = dataset.CreateLayer(table, srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("population", ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("usage", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("nom", ogr.OFTString))
    layer.StartTransaction()
    definition = layer.GetLayerDefn()
    for fid in range(1, count + 1):
        feature = ogr.Feature(definition)
        feature.SetField("population", fid * 100)
        feature.SetField("usage", "Industriel" if fid % 100 == 0 else "Résidentiel")
        feature.SetField("nom", ("École", "école", "ECOLE", "Ecole")[fid % 4])
        feature.SetGeometry(ogr.CreateGeometryFromWkt(f"POINT ({600000 + fid % 1000} {6200000 + fid // 1000})"))
        layer.CreateFeature(feature)
    layer.CommitTransaction()
    if delete:
        dataset.ExecuteSQL(f'DELETE FROM "{table}" WHERE {delete}')
    dataset = None
    return f"{path}|layername={table}"


def main(work):
    from filter_mate.adapters.public_api import introspection
    from filter_mate.core.agent.messages import ToolCallPart
    from filter_mate.core.agent.tool_catalog import chat_tools
    from filter_mate.core.agent.tool_executor import ToolExecutor
    from filter_mate.filtermate_api.agent_tools import build_handlers
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor

    project = QgsProject.instance()

    class PublicApi:  # the plugin applies a filter as setSubsetString does
        @staticmethod
        def apply_filter(layer_name, filter_expr, source_plugin):
            layer = project.mapLayer(layer_name) or (project.mapLayersByName(layer_name) or [None])[0]
            return layer is not None and layer.setSubsetString(filter_expr)

        @staticmethod
        def get_active_filters():
            return {layer.name(): layer.subsetString() for layer in project.mapLayers().values()
                    if isinstance(layer, QgsVectorLayer) and layer.subsetString()}

    executor = ToolExecutor(chat_tools(), build_handlers(QGISFilterMateAccessor(PublicApi(), None),
                                                         os.path.join(work, "exports")))

    def tool(name, **arguments):
        result = executor.execute(ToolCallPart("c", name, arguments))
        return result.is_error, (result.content if result.is_error else json.loads(result.content))

    def add(source, name):
        layer = QgsVectorLayer(source, name, "ogr")
        assert layer.isValid(), source
        project.addMapLayer(layer)
        return layer

    def listed(name):
        error, content = tool("list_layers")
        rows = [] if error else [row for row in content["layers"] if row["name"] == name]
        return rows[0]["feature_count"] if rows else None

    # --- a GeoPackage without gpkg_ogr_contents, below 100 000 features (the communes of the BD TOPO)
    commune = add(make_gpkg(os.path.join(work, "no_contents.gpkg"), "commune", 930, contents=False), "commune")
    error, answer = tool("apply_filter", layer_name="commune", expression='"population" > 92300')
    print(f"INFO no gpkg_ogr_contents, 930 features, 7 kept: QGIS featureCount() {commune.featureCount()}")
    check("apply_filter: 7 kept out of 930", not error and (answer.get("feature_count"), answer.get("total_count"))
          == (7, 930), answer)
    check("describe_layer: 7", introspection.describe_layer(commune.id())["feature_count"] == 7)
    from filter_mate.adapters.qgis import source_capability_probe as probe
    # the number the dock tells after a filter (message bar, history of the source layer)
    check("the dock tells 7, its limits keep the count of QGIS",
          probe.shown_feature_count_or_none(commune) == 7 and probe.feature_count_or_none(commune) == commune.featureCount(),
          f"shown {probe.shown_feature_count_or_none(commune)}, limit {probe.feature_count_or_none(commune)}")
    check("list_layers: 7", listed("commune") == 7, listed("commune"))
    preview = introspection.preview_filter(commune.id(), '"population" <= 1000')
    check("preview_filter: 10", preview["valid"] and preview["feature_count"] == 10, preview)
    error, answer = tool("apply_filter", layer_name="commune", expression='"population" > 1000000')
    check("apply_filter: nothing kept is told", not error and answer.get("feature_count") == 0 and "warning" in answer,
          answer)
    # GDAL reads FROM "commune" m: the layer shows nothing, so no number either; the trial says what it said before.
    commune.setSubsetString('"commune".fid < 5')
    count = introspection.describe_layer(commune.id())["feature_count"]
    check("a subset GDAL cannot read: no number", count == -1, count)
    preview = introspection.preview_filter(commune.id(), '"commune".fid < 5')
    check("preview_filter of a subset GDAL cannot read: no number", preview.get("feature_count", -1) == -1, preview)
    commune.setSubsetString('"population" > 92300')
    try:
        from filter_mate.adapters.qgis import feature_count
    except ImportError:  # before the fix: featureCount() is all there is
        feature_count = None
    budget = getattr(feature_count, "COUNT_BUDGET", None)
    if feature_count is not None:
        feature_count.COUNT_BUDGET = 0
        feature_count._CACHE.clear()  # counted above
    try:
        count = introspection.describe_layer(commune.id())["feature_count"]
        check("not counted in time: no number rather than 930", count == -1, count)
    finally:
        if feature_count is not None:
            feature_count.COUNT_BUDGET = budget
    # One rule: the number told is the number of features QGIS reads, or there is none.
    for subset, strict in (("\"nom\" LIKE 'é%'", True), ("lower(\"nom\") = 'école'", True),
                           ('ST_MinX("geom") > 600500', True), ("fid < 10 LIMIT 3", True),
                           ("fid < 10 ORDER BY fid LIMIT 2", True), ("1 GROUP BY nom", True),
                           ("fid < 10 GROUP BY fid", True), ("m.fid < 3", True), ("fid = 1; SELECT 2", False),
                           ("fid < 0 UNION ALL SELECT 42 ORDER BY 1 DESC", False),
                           ("fid < 5 UNION ALL SELECT * FROM commune", False)):
        applied = commune.setSubsetString(subset)
        read = sum(1 for _ in commune.getFeatures())
        count = introspection.describe_layer(commune.id())["feature_count"]
        told = count == read if strict else count in (read, -1)
        check(f"{subset}: what QGIS reads or no number", applied and told, (applied, count, read))
    # A query of its own: no number, whatever QGIS makes of it (3.22 reads it as a filter).
    for subset in ("SELECT * FROM commune WHERE fid < 5", "  SELECT * FROM commune WHERE fid < 5",
                   "WITH c AS (SELECT * FROM commune WHERE fid < 4) SELECT * FROM c"):
        commune.setSubsetString(subset)
        count = introspection.describe_layer(commune.id())["feature_count"]
        check(f"{subset.strip()[:30]}: no number", count == -1, (count, sum(1 for _ in commune.getFeatures())))
    commune.setSubsetString('"population" > 92300')
    # A file of one layer opened by its path alone: QGIS opens its only table.
    alone = add(os.path.join(work, "no_contents.gpkg"), "commune_alone")
    alone.setSubsetString('"population" > 92300')
    count = introspection.describe_layer(alone.id())["feature_count"]
    check("a file opened without a layer name: 7", count == 7, (alone.source(), count))

    # --- a corrupted geometry in the first row: QGIS reads the features, so does the count
    source = make_gpkg(os.path.join(work, "corrupt.gpkg"), "t", 10)
    dataset = ogr.Open(os.path.join(work, "corrupt.gpkg"), 1)
    dataset.ExecuteSQL("UPDATE t SET geom = X'47500003E61000000102' WHERE fid = 1")
    dataset = None
    corrupt = add(source, "corrupt")
    corrupt.setSubsetString('"population" >= 0')
    read = sum(1 for _ in corrupt.getFeatures())
    count = introspection.describe_layer(corrupt.id())["feature_count"]
    check("a corrupted first geometry: what QGIS reads", count == read, (count, read))
    preview = introspection.preview_filter(corrupt.id(), "fid < 5")
    check("a corrupted first geometry: the trial is valid", preview["valid"], preview)

    # --- a file locked by another connection: not waited for, no number
    import sqlite3
    locked = add(make_gpkg(os.path.join(work, "locked.gpkg"), "t", 10), "locked")
    locked.setSubsetString('"population" > 300')
    holder = sqlite3.connect(os.path.join(work, "locked.gpkg"), isolation_level=None, timeout=0)
    holder.execute("BEGIN EXCLUSIVE")
    started = time.perf_counter()
    count = introspection.describe_layer(locked.id())["feature_count"]
    seconds = time.perf_counter() - started
    holder.execute("ROLLBACK")
    holder.close()
    print(f"INFO a file locked by another connection: {count} in {seconds:.2f} s")
    check("a file locked by another connection: no number or what QGIS reads", count in (-1, 7), count)

    # --- a GeoPackage written by GDAL (gpkg_ogr_contents), 100 000 features or more
    big = add(make_gpkg(os.path.join(work, "big.gpkg"), "batiment", 120_000), "batiment")
    error, answer = tool("apply_filter", layer_name="batiment", expression="\"usage\" = 'Industriel'")
    print(f"INFO gpkg_ogr_contents, 120 000 features, 1 200 kept: QGIS featureCount() {big.featureCount()}")
    check("apply_filter: 1 200 kept out of 120 000", not error and (answer.get("feature_count"),
          answer.get("total_count")) == (1200, 120_000), answer)
    limit = introspection.MAX_STAT_FEATURES
    introspection.MAX_STAT_FEATURES = 100_000  # the table is above, the filter below
    try:
        statistics = introspection.layer_statistics(big.id(), "population")
        check("layer_statistics reads a filtered layer of a big table", statistics["statistics"]["count"] == 1200,
              statistics)
    except ValueError as exc:
        check("layer_statistics reads a filtered layer of a big table", False, exc)
    finally:
        introspection.MAX_STAT_FEATURES = limit
    # A filter slow on each feature: the clock stops the reading, the main thread waits about the budget (the count
    # alone: describe_layer asks QGIS for the extent too, which reads every feature).
    try:
        from filter_mate.adapters.qgis.feature_count import exact_feature_count
    except ImportError:
        exact_feature_count = None
    if exact_feature_count is not None:
        big.setSubsetString('(SELECT COUNT(*) FROM "batiment" a WHERE a.fid BETWEEN m.fid AND m.fid + 5000) > 0')
        started = time.perf_counter()
        count = exact_feature_count(big)
        seconds = time.perf_counter() - started
        print(f"INFO a filter slow on each feature: {count} in {seconds:.2f} s")
        check("a filter slow on each feature: stopped near the budget", count in (None, 120_000) and seconds < 1.5,
              (count, seconds))

    # --- no gpkg_ogr_contents, 100 000 features or more, holes in the fids: QGIS says MAX(fid) - MIN(fid) + 1
    holes = add(make_gpkg(os.path.join(work, "holes.gpkg"), "troncon", 150_000, contents=False,
                          delete="fid % 5 = 0 AND fid <= 100000"), "troncon")
    print(f"INFO no gpkg_ogr_contents, 130 000 features, fids 1 to 150 000: QGIS featureCount() {holes.featureCount()}")
    count = introspection.describe_layer(holes.id())["feature_count"]
    # Left as it was: without a subset the count of QGIS is kept (feature_count.py says so).
    check("describe_layer of a table without filter: what QGIS says", count == holes.featureCount(), count)

    # --- a small GeoPackage written by GDAL: QGIS was right, it stays right
    small = add(make_gpkg(os.path.join(work, "estavar.gpkg"), "bati", 918), "bati")
    error, answer = tool("apply_filter", layer_name="bati", expression='"population" <= 3700')
    check("control: 37 kept out of 918", not error and (answer.get("feature_count"), answer.get("total_count"))
          == (37, 918) and small.featureCount() == 37, answer)

    bdtopo = os.environ.get("FM_BDTOPO")
    if bdtopo:
        for name, expression, expected in (("commune", '"population" > 20000', 7),
                                           ("batiment", "\"usage_1\" = 'Industriel'", 8257)):
            layer = add(f"{bdtopo}|layername={name}", f"bd_{name}")
            layer.setSubsetString(expression)
            started = time.perf_counter()
            count = introspection.describe_layer(layer.id())["feature_count"]
            seconds = time.perf_counter() - started
            print(f"INFO BD TOPO {name}: QGIS featureCount() {layer.featureCount()}, describe_layer {count} "
                  f"in {seconds:.2f} s")
            check(f"BD TOPO {name}: {expected} or no number", count in (expected, -1), count)


if __name__ == "__main__":
    app = QgsApplication([], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, GDAL {gdal.__version__}")
    work = tempfile.mkdtemp()
    try:
        main(work)
    finally:
        QgsProject.instance().removeAllMapLayers()
        shutil.rmtree(work, ignore_errors=True)
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    # A normal end: QGIS must close without a crash (exit code 0 or 1, not 139).
    app.exitQgis()
    sys.exit(1 if failed else 0)
