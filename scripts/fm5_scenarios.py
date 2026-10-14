# -*- coding: utf-8 -*-
"""
FilterMate 5 - cross filter scenarios in a real QGIS (headless).

Runs every source -> target combination (vector, raster, point cloud), the
exports and the project-file guard on real data, and prints a PASS / FAIL
table with timings. Not a pytest module: run it with the QGIS Python, e.g.

    "C:\\Program Files\\QGIS 4.2.3\\bin\\python-qgis.bat" fm5_scenarios.py <data_dir> <gpkg> <tile> [<tile2>]

Data used during development (14/10/2026): LiDAR HD tile
LHD_FXX_0616_6153 (Cerdagne, 25.1 M points), a 1 m DTM and a 2 m class
raster derived from it with PDAL, BD TOPO buildings / roads and cadastral
parcels downloaded from the IGN WFS for the same square kilometre.
"""
import os
import sys
import time
import traceback

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointCloudLayer,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

app = QgsApplication([], False)
app.initQgis()

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))  # parent of the plugin folder

from filter_mate.adapters.qgis.coverage_layers import cache, exporters, pdal_cli  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.snapshots import registry  # noqa: E402
from filter_mate.adapters.qgis.coverage_layers.source_jobs import (  # noqa: E402
    PointCloudSourceJob, RasterSourceJob, VectorSourceJob)
from filter_mate.adapters.qgis.coverage_layers.target_appliers import PointCloudTargetJob  # noqa: E402
from filter_mate.core.domain.cross_filter import CrossFilterRequest, TargetSpec  # noqa: E402
from filter_mate.core.domain.layer_kind import LayerKind  # noqa: E402
from filter_mate.core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode  # noqa: E402
from filter_mate.core.services.cross_filter_service import CrossFilterService  # noqa: E402

DATA, GPKG, TILE = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = os.path.join(DATA, 'out', 'scenarios')
os.makedirs(OUT, exist_ok=True)
cache.set_cache_root(os.path.join(DATA, 'out', 'cache'))

results = []


def check(name, condition, detail=''):
    results.append((name, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'}  {name}  {detail}", flush=True)


project = QgsProject.instance()
bat = QgsVectorLayer(GPKG + '|layername=batiment', 'batiment', 'ogr')
routes = QgsVectorLayer(GPKG + '|layername=troncon_de_route', 'troncon_de_route', 'ogr')
parcelles = QgsVectorLayer(GPKG + '|layername=parcelle', 'parcelle', 'ogr')
mnt = QgsRasterLayer(os.path.join(DATA, 'mnt_1m.tif'), 'mnt', 'gdal')
classes = QgsRasterLayer(os.path.join(DATA, 'classes_2m.tif'), 'classes', 'gdal')
lhd = QgsPointCloudLayer(TILE, 'lhd', 'copc')
lhd_b = QgsPointCloudLayer(TILE, 'lhd_b', 'copc')
for layer in (bat, routes, parcelles, mnt, classes, lhd, lhd_b):
    project.addMapLayer(layer)
check('layers valid', all(l.isValid() for l in (bat, routes, parcelles, mnt, classes, lhd, lhd_b)),
      f"bat={bat.featureCount()} routes={routes.featureCount()} parcelles={parcelles.featureCount()} lhd={lhd.pointCount()}")
check('pdal available', pdal_cli.is_available(), pdal_cli.find_pdal() or '')
service = CrossFilterService()
registry().install(project)


def count(layer):
    """Feature count by iteration: in headless QGIS with several layers of one
    GeoPackage, OGR's COUNT(*) on a subset fails ("unable to open database
    file") and featureCount() returns -1, with or without FilterMate."""
    return sum(1 for _ in layer.getFeatures(QgsFeatureRequest().setNoAttributes().setFlags(QgsFeatureRequest.NoGeometry)))


def run(name, request, source_job):
    started = time.perf_counter()
    task = service.run(request, source_job, synchronous=True)
    elapsed = time.perf_counter() - started
    summary = ', '.join(f"{o.layer_id[:12]}:{'ok' if o.success else 'KO ' + o.message[:60]}:{o.kept_count}" for o in task.outcomes)
    print(f"   {name}: {elapsed:.1f}s source={source_job.details} {summary}", flush=True)
    return task


def nodata_at(layer, x, y):
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import identify_values
    values = identify_values(layer, QgsPointXY(x, y))
    return values.get(1) is None


def safe(fn):
    try:
        fn()
    except Exception as exc:
        traceback.print_exc()
        check(fn.__name__ + ' raised', False, str(exc))


# --- 0. predicate orientation ----------------------------------------------
def s0_predicates():
    from filter_mate.adapters.qgis.coverage_layers.geometry_tools import prepared_engine, target_matches
    square = QgsGeometry.fromWkt('POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))')
    small = QgsGeometry.fromWkt('POLYGON((2 2, 3 2, 3 3, 2 3, 2 2))')
    engine = prepared_engine(square)  # source = big square
    check('target within source', target_matches(engine, small, ['within']))
    check('target does not contain source', not target_matches(engine, small, ['contains']))
    engine_small = prepared_engine(small)  # source = small square
    check('target contains source', target_matches(engine_small, square, ['contains']))


# --- 1. V -> R -------------------------------------------------------------
first5 = list(bat.getFeatures(QgsFeatureRequest().setLimit(5)))


def s1_vector_to_raster():
    request = CrossFilterRequest(bat.id(), LayerKind.VECTOR, targets=(TargetSpec(mnt.id(), LayerKind.RASTER),),
                                 predicates=('Intersect',), buffer_value=2.0)
    task = run('V->R', request, VectorSourceJob(bat, first5))
    check('V->R derived VRT', mnt.source().endswith('.vrt') and mnt.isValid(), mnt.source()[-40:])
    centroid = first5[0].geometry().centroid().asPoint()
    ext = mnt.extent()
    check('V->R pixel kept inside', not nodata_at(mnt, centroid.x(), centroid.y()))
    check('V->R pixel NoData outside', nodata_at(mnt, ext.xMinimum() + 0.5, ext.yMinimum() + 0.5))
    service.undo(bat.id())
    check('V->R undo restores tif', mnt.source().endswith('mnt_1m.tif'))


# --- 2. V -> P (exact and bbox) --------------------------------------------
def s2_vector_to_point_cloud():
    request = CrossFilterRequest(bat.id(), LayerKind.VECTOR, targets=(TargetSpec(lhd.id(), LayerKind.POINT_CLOUD),),
                                 predicates=('Intersect',), buffer_value=1.0)
    run('V->P exact', request, VectorSourceJob(bat, first5))
    check('V->P derived copc', lhd.source().endswith('.copc.laz') and lhd.isValid(), f"points={lhd.pointCount()}")
    check('V->P fewer points', 0 < lhd.pointCount() < 25111931)
    service.undo(bat.id())
    check('V->P undo', lhd.source() == TILE and lhd.pointCount() == 25111931)
    job = PointCloudTargetJob(lhd, None, 'bbox')
    from filter_mate.adapters.qgis.coverage_layers.source_jobs import VectorSourceJob as V
    src = V(bat, first5)
    geom = src.compute(request, lambda: False)
    job.compute(geom, src.crs, project.transformContext(), request, lambda: False)
    after = job.apply(lhd)
    check('V->P bbox subset', after is not None and lhd.subsetString().startswith('(X >='), lhd.subsetString()[:60])
    lhd.setSubsetString('')


# --- 3. R -> V -------------------------------------------------------------
def s3_raster_to_vector():
    selection = RasterSelection(band=1, minimum=1240.0, maximum=1270.0)
    request = CrossFilterRequest(mnt.id(), LayerKind.RASTER,
                                 targets=(TargetSpec(parcelles.id(), LayerKind.VECTOR), TargetSpec(bat.id(), LayerKind.VECTOR)),
                                 predicates=('Intersect',), coverage_min=50.0)
    run('R->V', request, RasterSourceJob(mnt, selection))
    check('R->V parcel subset', parcelles.subsetString().startswith('"fid" IN') or parcelles.subsetString() == '1 = 0',
          f"{count(parcelles)} parcels, subset={parcelles.subsetString()[:50]}")
    check('R->V buildings subset', count(bat) < 134, f"{count(bat)} buildings")
    check('R->V source masked (virtual raster)', mnt.providerType() == 'virtualraster' and mnt.isValid())
    service.undo(mnt.id())
    check('R->V undo', parcelles.subsetString() == '' and count(bat) == 134 and mnt.providerType() == 'gdal')


# --- 4. R -> R -------------------------------------------------------------
def s4_raster_to_raster():
    selection = RasterSelection(band=1, mode=RasterSelectionMode.CLASSES, classes=frozenset({6}))
    request = CrossFilterRequest(classes.id(), LayerKind.RASTER, targets=(TargetSpec(mnt.id(), LayerKind.RASTER),),
                                 predicates=('Intersect',))
    task = run('R->R', request, RasterSourceJob(classes, selection))
    check('R->R target clipped', mnt.source().endswith('.vrt'), str(task.source_job.details))
    service.undo(classes.id())
    check('R->R undo', mnt.source().endswith('mnt_1m.tif') and classes.providerType() == 'gdal')


# --- 5. R -> P -------------------------------------------------------------
def s5_raster_to_point_cloud():
    selection = RasterSelection(band=1, minimum=1300.0)
    request = CrossFilterRequest(mnt.id(), LayerKind.RASTER, targets=(TargetSpec(lhd.id(), LayerKind.POINT_CLOUD),),
                                 predicates=('Are within',))
    run('R->P', request, RasterSourceJob(mnt, selection))
    check('R->P derived points', lhd.source().endswith('.copc.laz') and 0 < lhd.pointCount() < 25111931, f"{lhd.pointCount()} points")
    service.undo(mnt.id())
    check('R->P undo', lhd.source() == TILE)


# --- 6. P -> V -------------------------------------------------------------
def s6_point_cloud_to_vector():
    from filter_mate.adapters.qgis.coverage_layers.snapshots import take_snapshot
    before = take_snapshot(lhd, LayerKind.POINT_CLOUD)
    lhd.setSubsetString('Classification = 6')
    request = CrossFilterRequest(lhd.id(), LayerKind.POINT_CLOUD, targets=(TargetSpec(bat.id(), LayerKind.VECTOR),),
                                 predicates=('Intersect',), coverage_min=10.0)
    run('P->V', request, PointCloudSourceJob(lhd, 2.0, before=before))
    kept = count(bat)
    check('P->V buildings with class 6 points', 0 < kept <= 134, f"{kept} buildings")
    service.undo(lhd.id())
    check('P->V undo', count(bat) == 134 and lhd.subsetString() == '')
    before = take_snapshot(lhd, LayerKind.POINT_CLOUD)
    lhd.setSubsetString('Classification = 6')
    request = CrossFilterRequest(lhd.id(), LayerKind.POINT_CLOUD, targets=(TargetSpec(bat.id(), LayerKind.VECTOR),),
                                 predicates=('Disjoint',))
    run('P->V disjoint', request, PointCloudSourceJob(lhd, 2.0, before=before))
    # Coverage only applies to the inside predicates: Disjoint keeps the buildings
    # with no class 6 point at all, a subset of the complement of `kept`.
    check('P->V disjoint complements', 0 < count(bat) <= 134 - kept, f"{count(bat)} buildings without class 6")
    service.undo(lhd.id())


# --- 7. P -> R -------------------------------------------------------------
def s7_point_cloud_to_raster():
    from filter_mate.adapters.qgis.coverage_layers.snapshots import take_snapshot
    before = take_snapshot(lhd, LayerKind.POINT_CLOUD)
    lhd.setSubsetString('Classification = 5')
    request = CrossFilterRequest(lhd.id(), LayerKind.POINT_CLOUD, targets=(TargetSpec(mnt.id(), LayerKind.RASTER),),
                                 predicates=('Intersect',))
    run('P->R', request, PointCloudSourceJob(lhd, 2.0, before=before))
    check('P->R target clipped', mnt.source().endswith('.vrt'))
    service.undo(lhd.id())
    check('P->R undo', mnt.source().endswith('mnt_1m.tif'))


# --- 8. P -> P -------------------------------------------------------------
def s8_point_cloud_to_point_cloud():
    from filter_mate.adapters.qgis.coverage_layers.snapshots import take_snapshot
    before = take_snapshot(lhd, LayerKind.POINT_CLOUD)
    lhd.setSubsetString('Classification = 6')
    request = CrossFilterRequest(lhd.id(), LayerKind.POINT_CLOUD, targets=(TargetSpec(lhd_b.id(), LayerKind.POINT_CLOUD),),
                                 predicates=('Intersect',))
    run('P->P', request, PointCloudSourceJob(lhd, 2.0, before=before))
    check('P->P target clipped', lhd_b.source().endswith('.copc.laz') and 0 < lhd_b.pointCount() < 25111931, f"{lhd_b.pointCount()} points")
    service.undo(lhd.id())
    check('P->P undo', lhd_b.source() == TILE)


# --- 9. exports ------------------------------------------------------------
def s9_exports():
    request = CrossFilterRequest(bat.id(), LayerKind.VECTOR,
                                 targets=(TargetSpec(mnt.id(), LayerKind.RASTER), TargetSpec(lhd.id(), LayerKind.POINT_CLOUD)),
                                 predicates=('Intersect',), buffer_value=2.0)
    run('V->R+P for export', request, VectorSourceJob(bat, first5))
    started = time.perf_counter()
    result = exporters.export_raster(mnt, os.path.join(OUT, 'mnt_filtered_cog.tif'), 'COG')
    check('export raster COG', result.success and os.path.exists(result.path), f"{result.message} {time.perf_counter() - started:.1f}s")
    exported = QgsRasterLayer(result.path, 'exp', 'gdal')
    check('exported raster has NoData outside', exported.isValid() and nodata_at(exported, mnt.extent().xMinimum() + 0.5, mnt.extent().yMinimum() + 0.5))
    lhd.setSubsetString('Classification = 6')
    started = time.perf_counter()
    result = exporters.export_point_cloud(lhd, os.path.join(OUT, 'lhd_filtered.laz'), 'LAZ')
    exported_pc = QgsPointCloudLayer(result.path, 'exp', 'pdal') if result.success else None
    check('export point cloud LAZ', result.success, f"{result.message} {time.perf_counter() - started:.1f}s")
    if exported_pc is not None:
        check('exported LAZ count', 0 < exported_pc.pointCount() < lhd.pointCount() + 1, f"{exported_pc.pointCount()} points")
    result = exporters.export_point_cloud(lhd, os.path.join(OUT, 'lhd_filtered.copc.laz'), 'COPC')
    check('export point cloud COPC', result.success, result.message)
    lhd.setSubsetString('')
    # project file keeps the original sources
    path = os.path.join(os.environ.get('LOCALAPPDATA', OUT), 'Temp', 'fm5', 'fm5_scenarios.qgs') if os.name == 'nt' else os.path.join(OUT, 'fm5_scenarios.qgs')
    project.write(path)
    text = open(path, encoding='utf-8').read()
    import re
    datasources = re.findall(r'<datasource>(.*?)</datasource>', text)
    check('project keeps original sources', datasources and not any('session_' in d for d in datasources),
          'filtermate_derived' in text and 'marker present' or 'no marker')
    service.unfilter(bat.id(), [mnt.id(), lhd.id()], {mnt.id(): LayerKind.RASTER, lhd.id(): LayerKind.POINT_CLOUD})
    check('unfilter restores originals', mnt.source().endswith('mnt_1m.tif') and lhd.source() == TILE)
    service.undo(bat.id())
    check('undo of unfilter re-applies', mnt.source().endswith('.vrt'))
    restored = registry().restore_all(project)
    check('restore_all on unload', mnt.source().endswith('mnt_1m.tif') and lhd.source() == TILE, f"{restored} layers")


for scenario in (s0_predicates, s1_vector_to_raster, s2_vector_to_point_cloud, s3_raster_to_vector,
                 s4_raster_to_raster, s5_raster_to_point_cloud, s6_point_cloud_to_vector,
                 s7_point_cloud_to_raster, s8_point_cloud_to_point_cloud, s9_exports):
    print(f"--- {scenario.__name__}", flush=True)
    safe(scenario)

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("FAILED: " + "; ".join(failed))
cache.purge_session()
