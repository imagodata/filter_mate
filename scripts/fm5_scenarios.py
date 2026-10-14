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
sys.path.append(os.path.join(os.environ.get('QGIS_PREFIX_PATH', ''), 'python', 'plugins'))  # processing

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

# The plugin config is not loaded headless: turn the FilterMate 5 flags on.
from filter_mate.config.config import ENV_VARS  # noqa: E402
_options = ENV_VARS.setdefault('CONFIG_DATA', {}).setdefault('APP', {}).setdefault('OPTIONS', {})
_options.setdefault('RASTER', {})['enabled'] = {'value': True}
_options.setdefault('POINT_CLOUD', {})['enabled'] = {'value': True}
OUT = os.path.join(DATA, 'out', 'scenarios')
os.makedirs(OUT, exist_ok=True)
cache.set_cache_root(os.path.join(DATA, 'out', 'cache'))

results = []
_PROVIDER = None
# SQLite (GeoPackage) cannot write through \\wsl.localhost: exports go to the Windows temp folder.
EXPORTS = (os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'fm5', 'exports') if os.name == 'nt'
           else os.path.join(OUT, 'exports'))


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


# --- 10. reopening a project replays the stored clips ---------------------
def s10_replay_on_reopen():
    from filter_mate.core.services.cross_filter_service import replay_project_filters
    request = CrossFilterRequest(bat.id(), LayerKind.VECTOR,
                                 targets=(TargetSpec(mnt.id(), LayerKind.RASTER), TargetSpec(lhd.id(), LayerKind.POINT_CLOUD)),
                                 predicates=('Disjoint',), buffer_value=2.0)
    run('V->R+P disjoint before save', request, VectorSourceJob(bat, first5))
    kept_points = lhd.pointCount()
    check('disjoint keeps the outside points', 0 < kept_points < 25111931, f"{kept_points} points")
    path = os.path.join(OUT, 'fm5_replay.qgs') if os.name != 'nt' else os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'fm5', 'fm5_replay.qgs')
    project.write(path)
    project.clear()
    registry().restore_all(project)
    project.read(path)
    reopened_mnt = project.mapLayersByName('mnt')[0]
    reopened_lhd = project.mapLayersByName('lhd')[0]
    check('reopened layers on original sources', reopened_mnt.source().endswith('mnt_1m.tif') and reopened_lhd.source() == TILE)
    queued = replay_project_filters(service, synchronous=True)
    check('stored clips replayed', queued == 2 and reopened_mnt.source().endswith('.vrt') and reopened_lhd.source().endswith('.copc.laz'),
          f"queued={queued} mnt={reopened_mnt.source()[-20:]} lhd={reopened_lhd.source()[-30:]}")
    check('replayed point count identical', reopened_lhd.pointCount() == kept_points, f"{reopened_lhd.pointCount()} vs {kept_points}")
    registry().restore_all(project)


# --- 11. favorites keep raster / point cloud clips --------------------------
def s11_favorites():
    from filter_mate.adapters.qgis.coverage_layers import favorites_bridge
    cur_bat = project.mapLayersByName('batiment')[0]
    cur_mnt = project.mapLayersByName('mnt')[0]
    cur_lhd = project.mapLayersByName('lhd')[0]
    feats = list(cur_bat.getFeatures(QgsFeatureRequest().setLimit(5)))
    request = CrossFilterRequest(cur_bat.id(), LayerKind.VECTOR,
                                 targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER), TargetSpec(cur_lhd.id(), LayerKind.POINT_CLOUD)),
                                 predicates=('Intersect',), buffer_value=2.0)
    run('V->R+P for favorite', request, VectorSourceJob(cur_bat, feats))
    cur_lhd.setSubsetString('Classification = 6')
    expected = cur_lhd.pointCount()
    entries = favorites_bridge.capture(project)
    check('favorite captures raster + point cloud', len(entries) == 2, str([e['layer_name'] for e in entries]))
    service.unfilter(cur_bat.id(), [cur_mnt.id(), cur_lhd.id()], {cur_mnt.id(): LayerKind.RASTER, cur_lhd.id(): LayerKind.POINT_CLOUD})
    check('unfiltered before applying the favorite', cur_mnt.source().endswith('mnt_1m.tif') and cur_lhd.source() == TILE)
    handled = favorites_bridge.apply(entries, service, project, synchronous=True)
    check('favorite re-applies the clips', handled == 2 and cur_mnt.source().endswith('.vrt') and cur_lhd.source().endswith('.copc.laz')
          and cur_lhd.subsetString() == 'Classification = 6', f"handled={handled} subset={cur_lhd.subsetString()}")
    check('favorite point count identical', cur_lhd.pointCount() == expected, f"{cur_lhd.pointCount()} vs {expected}")
    registry().restore_all(project)


# --- 12. refiltering derived layers, OR operator, preview opacity ------------
def s12_refilter_and_operators():
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import (
        apply_selection_preview, band_range, clear_selection_preview, pixel_is_transparent)
    from filter_mate.core.domain.filter_state import LayerSnapshot  # noqa: F401
    cur_bat = project.mapLayersByName('batiment')[0]
    cur_mnt = project.mapLayersByName('mnt')[0]
    # (a) raster source filtered twice: the second selection reads the original pixels
    job = RasterSourceJob(cur_mnt, RasterSelection(band=1, minimum=1240.0, maximum=1270.0))
    job.apply(cur_mnt)
    job = RasterSourceJob(cur_mnt, RasterSelection(band=1, minimum=1300.0, maximum=1350.0))
    job.apply(cur_mnt)
    low, high, _ = band_range(cur_mnt, 1)
    check('raster source refiltered from the original', low is not None and low >= 1299.9 and high <= 1350.1,
          f"range after 2nd filter: {low} - {high}")
    registry().restore_all(project)
    # (b) AND of Intersect then Disjoint on a raster target keeps the first clip
    feats = list(cur_bat.getFeatures(QgsFeatureRequest().setLimit(5)))
    first = CrossFilterRequest(cur_bat.id(), LayerKind.VECTOR, targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER),),
                               predicates=('Intersect',), buffer_value=2.0)
    run('V->R intersect', first, VectorSourceJob(cur_bat, feats[:3]))
    second = CrossFilterRequest(cur_bat.id(), LayerKind.VECTOR, targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER),),
                                predicates=('Disjoint',), buffer_value=2.0, other_layers_combine_operator='AND')
    run('V->R disjoint AND', second, VectorSourceJob(cur_bat, feats[3:]))
    centroid = feats[0].geometry().centroid().asPoint()
    ext = cur_mnt.extent()
    check('AND keeps the first clip (inside kept)', not nodata_at(cur_mnt, centroid.x(), centroid.y()))
    check('AND keeps the first clip (outside still NoData)', nodata_at(cur_mnt, ext.xMinimum() + 0.5, ext.yMinimum() + 0.5))
    registry().restore_all(project)
    # (c) OR on a vector target tests the features hidden by the previous subset
    cur_bat.setSubsetString('"fid" = 1')
    request = CrossFilterRequest(cur_mnt.id(), LayerKind.RASTER, targets=(TargetSpec(cur_bat.id(), LayerKind.VECTOR),),
                                 predicates=('Intersect',), other_layers_combine_operator='OR')
    run('R->V OR', request, RasterSourceJob(cur_mnt, RasterSelection(band=1, minimum=1240.0, maximum=1270.0)))
    check('OR adds the features hidden by the previous subset', count(cur_bat) >= 5, f"{count(cur_bat)} buildings, subset={cur_bat.subsetString()[:60]}")
    cur_bat.setSubsetString('')
    registry().restore_all(project)
    # (d) preview: really transparent, and the user transparency comes back
    apply_selection_preview(cur_mnt, RasterSelection(band=1, minimum=1240.0, maximum=1270.0), 1189.0, 1359.0)
    pixels = cur_mnt.renderer().rasterTransparency().transparentSingleValuePixelList()
    check('preview pixels fully transparent', len(pixels) == 2 and all(pixel_is_transparent(p) for p in pixels))
    clear_selection_preview(cur_mnt)
    check('preview cleared', len(cur_mnt.renderer().rasterTransparency().transparentSingleValuePixelList()) == 0)


# --- 13. Processing algorithm ---------------------------------------------------
def s13_processing():
    import processing  # noqa: F401 - QGIS plugin
    from processing.core.Processing import Processing
    from filter_mate.processing.provider import FilterMateProcessingProvider
    Processing.initialize()
    registry_ = QgsApplication.processingRegistry()
    existing = registry_.providerById('filtermate')
    if existing is not None:  # another FilterMate (installed plugin) must not shadow the tested one
        registry_.removeProvider(existing)
    # Keep a Python reference, like the plugin does: otherwise the Python
    # subclasses are garbage collected and the algorithms lose their methods.
    global _PROVIDER
    _PROVIDER = FilterMateProcessingProvider()
    registry_.addProvider(_PROVIDER)
    cur_bat = project.mapLayersByName('batiment')[0]
    cur_mnt = project.mapLayersByName('mnt')[0]
    cur_lhd = project.mapLayersByName('lhd')[0]
    cur_par = project.mapLayersByName('parcelle')[0]
    cur_bat.selectByIds([f.id() for f in cur_bat.getFeatures(QgsFeatureRequest().setLimit(5))])
    result = processing.run('filtermate:cross_filter', {
        'SOURCE': cur_bat, 'SELECTED_ONLY': True, 'TARGETS': [cur_mnt, cur_lhd, cur_par],
        'PREDICATES': [0], 'BUFFER': 2.0, 'COVERAGE': 0.0, 'OPERATOR': 0})
    check('processing cross_filter: 3 targets', len(result['LAYERS_FILTERED']) == 3 and not result['LAYERS_FAILED'], str(result))
    check('processing clipped raster + cloud', cur_mnt.source().endswith('.vrt') and cur_lhd.source().endswith('.copc.laz'))
    # The 5 buildings may touch no parcel: an empty result (1 = 0) is a valid filter too.
    check('processing filtered parcels', cur_par.subsetString().startswith('"fid" IN') or cur_par.subsetString() == '1 = 0',
          cur_par.subsetString()[:50])
    cur_par.setSubsetString('')
    cur_bat.removeSelection()
    registry().restore_all(project)


# --- 14. a raster source selection is replayed on project reopen ------------
def s14_raster_selection_replay():
    from filter_mate.adapters.qgis.coverage_layers.raster_adapter import band_range
    from filter_mate.core.services.cross_filter_service import replay_project_filters
    cur_mnt = project.mapLayersByName('mnt')[0]
    RasterSourceJob(cur_mnt, RasterSelection(band=1, minimum=1300.0, maximum=1350.0)).apply(cur_mnt)
    path = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'fm5', 'fm5_selection.qgs') if os.name == 'nt' else os.path.join(OUT, 'fm5_selection.qgs')
    project.write(path)
    project.clear()
    registry().restore_all(project)
    project.read(path)
    reopened = project.mapLayersByName('mnt')[0]
    check('selection: reopened on the original tif', reopened.providerType() == 'gdal' and reopened.source().endswith('mnt_1m.tif'))
    replay_project_filters(service, synchronous=True)
    low, high, _ = band_range(reopened, 1)
    check('selection replayed (virtual raster, same range)', reopened.providerType() == 'virtualraster'
          and low is not None and low >= 1299.9 and high <= 1350.1, f"{reopened.providerType()} {low}-{high}")
    registry().restore_all(project)


# --- 15. REST API accessor ------------------------------------------------------
def s15_rest_api_accessor():
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    import types
    accessor = QGISFilterMateAccessor(public_api=types.SimpleNamespace(get_active_filters=lambda: {}), plugin=None)
    kinds = {layer.name: layer.layer_kind for layer in accessor.list_layers()}
    check('API lists layer kinds', kinds.get('mnt') == 'raster' and kinds.get('lhd') == 'point_cloud' and kinds.get('batiment') == 'vector',
          str(kinds))
    cur_bat = project.mapLayersByName('batiment')[0]
    cur_bat.selectByIds([f.id() for f in cur_bat.getFeatures(QgsFeatureRequest().setLimit(5))])
    result = accessor.cross_filter('batiment', ['mnt', 'lhd', 'ghost'], ['Intersect'], buffer=2.0)
    check('API cross_filter', result is not None and sorted(result.filtered) == ['lhd', 'mnt'] and 'ghost' in result.failed,
          str(result))
    marked = {layer.name: layer.has_active_filter for layer in accessor.list_layers()}
    check('API marks clipped layers as filtered', marked.get('mnt') and marked.get('lhd'), str(marked))
    cur_bat.removeSelection()
    registry().restore_all(project)


# --- 16. undo never overwrites a layer changed by another source ---------------
def s16_undo_keeps_newer_changes():
    from filter_mate.adapters.qgis.coverage_layers.snapshots import take_snapshot
    cur_bat = project.mapLayersByName('batiment')[0]
    cur_mnt = project.mapLayersByName('mnt')[0]
    cur_lhd = project.mapLayersByName('lhd')[0]
    feats = list(cur_bat.getFeatures(QgsFeatureRequest().setLimit(5)))
    run('V->R (source batiment)', CrossFilterRequest(cur_bat.id(), LayerKind.VECTOR,
        targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER),), predicates=('Intersect',), buffer_value=2.0),
        VectorSourceJob(cur_bat, feats))
    first_clip = cur_mnt.source()
    before = take_snapshot(cur_lhd, LayerKind.POINT_CLOUD)
    cur_lhd.setSubsetString('Classification = 5')
    run('P->R (source lhd)', CrossFilterRequest(cur_lhd.id(), LayerKind.POINT_CLOUD,
        targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER),), predicates=('Intersect',)),
        PointCloudSourceJob(cur_lhd, 2.0, before=before))
    second_clip = cur_mnt.source()
    service.undo(cur_bat.id())
    check('second source changed the raster', second_clip != first_clip)
    check('undo of the older source leaves the newer clip', cur_mnt.source() == second_clip and 'mnt' in service.last_skipped,
          f"skipped={service.last_skipped}")
    service.undo(cur_lhd.id())
    check('undo of the newer source goes back to the first clip', cur_mnt.source() == first_clip and cur_lhd.subsetString() == '')
    registry().restore_all(project)


# --- 16. Processing algorithms of FilterMate 5 ------------------------------------
def _layers(*names):
    return [project.mapLayersByName(name)[0] for name in names]


def _fresh(folder):
    import shutil
    shutil.rmtree(folder, ignore_errors=True)
    return folder


def _clear(*layers_):
    from filter_mate.adapters.public_api import operations
    operations.clear_filters(list(layers_))
    registry().restore_all(project)


def s17_processing_algorithms():
    import processing  # noqa: F401 - QGIS plugin
    cur_bat, cur_mnt, cur_lhd, cur_lhd_b, cur_par, cur_routes = _layers(
        'batiment', 'mnt', 'lhd', 'lhd_b', 'parcelle', 'troncon_de_route')
    algorithms = {a.id() for a in QgsApplication.processingRegistry().providerById('filtermate').algorithms()}
    expected = {'filtermate:cross_filter_from_raster', 'filtermate:cross_filter_from_point_cloud',
                'filtermate:cross_filter_from_geometry', 'filtermate:filter_point_cloud', 'filtermate:clear_filters',
                'filtermate:apply_favorite', 'filtermate:export_filtered_layers', 'filtermate:extraction_par_emprise',
                'filtermate:vegetation_pres_des_lignes', 'filtermate:parcelles_en_pente_faible',
                'filtermate:batiments_absents_du_lidar'}
    check('processing: algorithms and models registered', expected <= algorithms, str(sorted(expected - algorithms)))
    if not expected <= algorithms:  # diagnostics
        provider = QgsApplication.processingRegistry().providerById('filtermate')
        print('   provider', provider, type(provider), sorted(algorithms), flush=True)
        for alg_id in sorted(expected - algorithms)[:3]:
            found = QgsApplication.processingRegistry().algorithmById(alg_id)
            print('   ', alg_id, found, type(found), flush=True)

    result = processing.run('filtermate:cross_filter_from_raster', {
        'SOURCE': cur_mnt, 'BAND': 1, 'MODE': 0, 'MINIMUM': 1240, 'MAXIMUM': 1270,
        'TARGETS': [cur_par, cur_bat], 'PREDICATES': [0], 'COVERAGE': 50, 'OPERATOR': 0})
    check('processing R->V: OUTPUT lists the targets', set(result['OUTPUT']) == {cur_par.id(), cur_bat.id()}, str(result))
    check('processing R->V: parcels filtered, source untouched',
          (cur_par.subsetString().startswith('"fid" IN') or cur_par.subsetString() == '1 = 0')
          and cur_mnt.providerType() == 'gdal', cur_par.subsetString()[:40])
    result = processing.run('filtermate:clear_filters', {'LAYERS': [cur_par, cur_bat, cur_mnt]})
    check('processing clear_filters', cur_par.subsetString() == '' and cur_bat.subsetString() == ''
          and set(result['OUTPUT']) == {cur_par.id(), cur_bat.id()}, str(result['OUTPUT']))

    result = processing.run('filtermate:cross_filter_from_raster', {
        'SOURCE': cur_mnt, 'MODE': 0, 'MINIMUM': 1300, 'FILTER_SOURCE': True, 'TARGETS': [], 'PREDICATES': [0]})
    check('processing raster source only (FILTER_SOURCE)', cur_mnt.providerType() == 'virtualraster'
          and result['OUTPUT'] == [cur_mnt.id()], cur_mnt.providerType())
    _clear(cur_mnt)
    try:
        processing.run('filtermate:cross_filter_from_raster', {'SOURCE': cur_mnt, 'MODE': 0, 'TARGETS': [cur_par]})
        check('processing raster range without bounds is refused', False)
    except Exception as exc:
        check('processing raster range without bounds is refused', 'minimum' in str(exc), str(exc)[:80])

    result = processing.run('filtermate:cross_filter_from_point_cloud', {
        'SOURCE': cur_lhd, 'CLASSES': '6', 'TARGETS': [cur_bat], 'PREDICATES': [2], 'OPERATOR': 0})
    kept = count(cur_bat)
    check('processing P->V disjoint (OUTPUT = targets only)', 0 < kept < 134
          and cur_lhd.subsetString() == 'Classification = 6' and result['OUTPUT'] == [cur_bat.id()],
          f"{kept} buildings, subset={cur_lhd.subsetString()}")
    _clear(cur_bat, cur_lhd)
    check('processing P->V cleared', count(cur_bat) == 134 and cur_lhd.subsetString() == '')
    from filter_mate.adapters.public_api import operations
    report = operations.cross_filter(cur_lhd, ['ghost_layer'], point_cloud_criteria='Classification = 6')
    check('unknown targets are refused, point cloud source untouched',
          report.error == 'no filterable target layer' and cur_lhd.subsetString() == '', report.error)

    extent = cur_mnt.extent()
    quarter = (f"{extent.xMinimum()},{extent.xMinimum() + extent.width() / 2},"
               f"{extent.yMinimum()},{extent.yMinimum() + extent.height() / 2} [EPSG:2154]")
    result = processing.run('filtermate:cross_filter_from_geometry', {
        'EXTENT': quarter, 'TARGETS': [cur_mnt, cur_lhd_b, cur_routes], 'PREDICATES': [0]})
    check('processing geometry -> R+P+V', cur_mnt.source().endswith('.vrt') and cur_lhd_b.source().endswith('.copc.laz')
          and len(result['OUTPUT']) == 3 and 0 < count(cur_routes), f"{result['LAYERS_FILTERED']} {count(cur_routes)} routes")
    _clear(cur_mnt, cur_lhd_b, cur_routes)

    result = processing.run('filtermate:filter_point_cloud', {'LAYERS': [cur_lhd, cur_lhd_b], 'CLASSES': '2', 'Z_MIN': 1000})
    check('processing filter_point_cloud on 2 tiles', cur_lhd.subsetString() == 'Classification = 2 AND Z >= 1000'
          and cur_lhd_b.subsetString() == cur_lhd.subsetString() and len(result['OUTPUT']) == 2, cur_lhd.subsetString())
    _clear(cur_lhd, cur_lhd_b)

    cur_bat.selectByIds([f.id() for f in cur_bat.getFeatures(QgsFeatureRequest().setLimit(5))])
    filtered = processing.run('filtermate:cross_filter', {
        'SOURCE': cur_bat, 'SELECTED_ONLY': True, 'TARGETS': [cur_mnt, cur_lhd, cur_par], 'PREDICATES': [0],
        'BUFFER': 2.0, 'COVERAGE': 0.0, 'OPERATOR': 0})
    check('processing cross_filter OUTPUT', len(filtered['OUTPUT']) == 3, str(filtered['LAYERS_FILTERED']))
    folder = _fresh(os.path.join(EXPORTS, 'export_processing'))
    started = time.perf_counter()
    exported = processing.run('filtermate:export_filtered_layers', {
        'LAYERS': filtered['OUTPUT'], 'VECTOR_FORMAT': 0, 'RASTER_FORMAT': 0, 'POINT_CLOUD_FORMAT': 0,
        'OUTPUT_FOLDER': folder})
    files = exported['OUTPUT_FILES']
    check('processing export: 3 files written', len(files) == 3 and all(os.path.exists(f) for f in files),
          f"{[os.path.basename(f) for f in files]} {time.perf_counter() - started:.1f}s")
    gpkg = [f for f in files if f.endswith('.gpkg')]
    if gpkg:
        written = QgsVectorLayer(gpkg[0], 'w', 'ogr')
        check('processing export: GPKG holds the filtered parcels only', count(written) == count(cur_par),
              f"{count(written)} vs {count(cur_par)}")
    laz = [f for f in files if f.endswith('.laz')]
    if laz:
        written_pc = QgsPointCloudLayer(laz[0], 'w', 'pdal')
        check('processing export: LAZ holds the clipped points', written_pc.pointCount() == cur_lhd.pointCount(),
              f"{written_pc.pointCount()} vs {cur_lhd.pointCount()}")
    temporary = processing.run('filtermate:export_filtered_layers', {
        'LAYERS': [cur_par], 'OUTPUT_FOLDER': 'TEMPORARY_OUTPUT'})
    check('processing export to a temporary folder', os.path.isabs(temporary['OUTPUT_FOLDER'])
          and 'TEMPORARY_OUTPUT' not in temporary['OUTPUT_FOLDER'] and len(temporary['OUTPUT_FILES']) == 1,
          temporary['OUTPUT_FOLDER'])
    cur_bat.removeSelection()
    cur_par.setSubsetString('')
    registry().restore_all(project)


def s18_apply_favorite_headless():
    """A favorite saved in the project file is applied without the plugin (qgis_process case)."""
    import json
    import processing  # noqa: F401
    from filter_mate.adapters.qgis.coverage_layers import favorites_bridge
    cur_bat, cur_mnt, cur_lhd = _layers('batiment', 'mnt', 'lhd')
    feats = list(cur_bat.getFeatures(QgsFeatureRequest().setLimit(5)))
    request = CrossFilterRequest(cur_bat.id(), LayerKind.VECTOR, targets=(TargetSpec(cur_mnt.id(), LayerKind.RASTER),
                                                                         TargetSpec(cur_lhd.id(), LayerKind.POINT_CLOUD)),
                                 predicates=('Intersect',), buffer_value=2.0)
    run('V->R for favorite', request, VectorSourceJob(cur_bat, feats))
    coverage = favorites_bridge.capture(project)
    registry().restore_all(project)
    favorite = {'id': 'fav-fm5-test', 'name': 'Petits identifiants', 'expression': '"fid" < 50',
                'layer_name': 'batiment', 'spatial_config': {'coverage_layers': coverage}}
    project.writeEntry('FilterMate', 'favorites_backup', json.dumps({'favorites': [favorite]}))
    # qgis_process has no dock options: the point cloud option off must not break the favorite.
    _options['POINT_CLOUD']['enabled'] = {'value': False}
    try:
        result = processing.run('filtermate:apply_favorite', {'FAVORITE': 'petits identifiants'})
    finally:
        _options['POINT_CLOUD']['enabled'] = {'value': True}
    check('processing apply_favorite (project backup, point cloud option off)', cur_bat.subsetString() == '"fid" < 50'
          and cur_mnt.source().endswith('.vrt') and cur_lhd.source().endswith('.copc.laz')
          and set(result['OUTPUT']) == {cur_bat.id(), cur_mnt.id(), cur_lhd.id()},
          f"subset={cur_bat.subsetString()} mnt={cur_mnt.source()[-12:]} lhd={cur_lhd.source()[-12:]}")
    try:
        processing.run('filtermate:apply_favorite', {'FAVORITE': 'inconnu'})
        check('processing unknown favorite is refused', False)
    except Exception as exc:
        check('processing unknown favorite is refused', 'not found' in str(exc), str(exc)[:60])
    cur_bat.setSubsetString('')
    project.removeEntry('FilterMate', 'favorites_backup')
    registry().restore_all(project)


def s19_models():
    import processing  # noqa: F401
    cur_bat, cur_mnt, cur_lhd, cur_par, cur_routes = _layers('batiment', 'mnt', 'lhd', 'parcelle', 'troncon_de_route')
    reg = QgsApplication.processingRegistry()

    def destination(model_id):
        return reg.algorithmById(model_id).destinationParameterDefinitions()[0].name()

    def files_in(folder):
        return sorted(f for f in os.listdir(folder) if not f.endswith('.aux.xml')) if os.path.isdir(folder) else []

    cur_bat.selectByIds([f.id() for f in cur_bat.getFeatures(QgsFeatureRequest().setLimit(5))])
    folder = _fresh(os.path.join(EXPORTS, 'model_extraction'))
    started = time.perf_counter()
    processing.run('filtermate:extraction_par_emprise', {
        'emprise': cur_bat, 'selection_seule': True, 'couches': [cur_mnt, cur_lhd, cur_par], 'tampon': 2.0,
        destination('filtermate:extraction_par_emprise'): folder})
    check('model extraction_par_emprise', files_in(folder) == ['lhd.laz', 'mnt.tif', 'parcelle.gpkg'],
          f"{files_in(folder)} {time.perf_counter() - started:.1f}s")
    cur_bat.removeSelection()
    _clear(cur_mnt, cur_lhd, cur_par)

    folder = _fresh(os.path.join(EXPORTS, 'model_pente'))
    started = time.perf_counter()
    processing.run('filtermate:parcelles_en_pente_faible', {
        'mnt': cur_mnt, 'pente_max': 15.0, 'cibles': [cur_par], 'couverture': 50.0,
        destination('filtermate:parcelles_en_pente_faible'): folder})
    kept = count(cur_par)
    check('model parcelles_en_pente_faible', files_in(folder) == ['parcelle.gpkg']
          and cur_par.subsetString() != '' and cur_mnt.providerType() == 'gdal',
          f"{kept} parcels {cur_par.subsetString()[:30]} {time.perf_counter() - started:.1f}s")
    _clear(cur_par)

    folder = _fresh(os.path.join(EXPORTS, 'model_vegetation'))
    started = time.perf_counter()
    processing.run('filtermate:vegetation_pres_des_lignes', {
        'lignes': cur_routes, 'nuages': [cur_lhd], 'classes': '4,5', 'couloir': 10.0,
        destination('filtermate:vegetation_pres_des_lignes'): folder})
    check('model vegetation_pres_des_lignes', files_in(folder) == ['lhd.copc.laz'] and cur_lhd.source().endswith('.copc.laz')
          and cur_lhd.subsetString() == 'Classification IN (4, 5)',
          f"{files_in(folder)} {cur_lhd.subsetString()} {time.perf_counter() - started:.1f}s")
    _clear(cur_lhd)

    folder = _fresh(os.path.join(EXPORTS, 'model_batiments'))
    processing.run('filtermate:batiments_absents_du_lidar', {
        'nuage': cur_lhd, 'classes': '6', 'batiments': [cur_bat],
        destination('filtermate:batiments_absents_du_lidar'): folder})
    written = QgsVectorLayer(os.path.join(folder, 'batiment.gpkg'), 'w', 'ogr')
    check('model batiments_absents_du_lidar (buildings only, not the cloud)', files_in(folder) == ['batiment.gpkg']
          and count(written) == count(cur_bat) < 134, f"{files_in(folder)} {count(written)} written, {count(cur_bat)} filtered")
    _clear(cur_bat, cur_lhd)


def s20_public_api():
    import types
    from filter_mate.adapters.public_api.filter_mate_public_api import FilterMatePublicAPI
    api = FilterMatePublicAPI(types.SimpleNamespace(plugin_dir=os.path.dirname(HERE)))
    events = []
    api.operation_completed.connect(lambda name, report: events.append((name, report['ok'])))
    cur_bat, cur_mnt, cur_lhd = _layers('batiment', 'mnt', 'lhd')
    cur_bat.selectByIds([f.id() for f in cur_bat.getFeatures(QgsFeatureRequest().setLimit(5))])
    report = api.cross_filter('batiment', ['mnt', 'lhd'], buffer=2.0)
    check('public API cross_filter', report['ok'] and sorted(report['done']) == ['lhd', 'mnt'], str(report)[:120])
    from filter_mate.core.services.cross_filter_service import get_cross_filter_service
    check('public API vector source kept out of the dock history', not get_cross_filter_service().can_undo(cur_bat.id()))
    report = api.cross_filter('mnt', ['batiment'])
    check('public API raster source needs a selection', not report['ok'] and 'selection' in report['error'], report['error'])
    report = api.filter_point_clouds(['lhd'], {'classes': [6]}, operator='AND')
    check('public API filter_point_clouds (AND on an empty subset)', report['ok']
          and cur_lhd.subsetString() == 'Classification = 6', cur_lhd.subsetString())
    state = {row['name']: row['kind'] for row in api.get_filter_state()}
    check('public API get_filter_state', state.get('mnt') == 'raster' and state.get('lhd') == 'point_cloud', str(state))
    folder = os.path.join(EXPORTS, 'export_public_api')
    report = api.export_layers(['mnt'], folder, raster_format='GTiff')
    check('public API export_layers', report['ok'] and os.path.exists(report['outputs'].get('mnt', '')), str(report['outputs']))
    report = api.clear_filters(['mnt', 'lhd', 'batiment'])
    check('public API clear_filters', report['ok'] and sorted(report['done']) == ['lhd', 'mnt']
          and cur_mnt.source().endswith('mnt_1m.tif') and cur_lhd.subsetString() == '', str(report))
    extent = cur_mnt.extent()
    wkt = (f"POLYGON(({extent.xMinimum()} {extent.yMinimum()}, {extent.xMinimum() + 200} {extent.yMinimum()}, "
           f"{extent.xMinimum() + 200} {extent.yMinimum() + 200}, {extent.xMinimum()} {extent.yMinimum() + 200}, "
           f"{extent.xMinimum()} {extent.yMinimum()}))")
    report = api.cross_filter_by_geometry(wkt, 'EPSG:2154', ['mnt'])
    check('public API cross_filter_by_geometry', report['ok'] and cur_mnt.source().endswith('.vrt'), str(report)[:100])
    report = api.cross_filter_by_geometry(wkt, 'EPSG:999999', ['mnt'])
    check('public API invalid CRS is an error report', not report['ok'] and 'CRS' in report['error'], report['error'])
    check('public API signals', len(events) == 7 and events[1] == ('cross_filter', False), str(events))
    cur_bat.removeSelection()
    _clear(cur_mnt)


def s21_rest_accessor_v5():
    import types
    from filter_mate.filtermate_api.qgis_accessor import QGISFilterMateAccessor
    accessor = QGISFilterMateAccessor(public_api=types.SimpleNamespace(get_active_filters=lambda: {}), plugin=None)
    cur_mnt, cur_par, cur_lhd = _layers('mnt', 'parcelle', 'lhd')
    result = accessor.cross_filter('mnt', ['parcelle', 'ghost'], ['Intersect'], coverage_min=50.0,
                                   raster_selection={'band': 1, 'mode': 'range', 'minimum': 1240, 'maximum': 1270})
    check('API raster source -> parcels', result is not None and result.filtered == ['parcelle'] and 'ghost' in result.failed,
          str(result))
    result = accessor.filter_point_clouds(['lhd'], {'classes': [6], 'z_min': 1000})
    check('API filter_point_clouds', result.done == ['lhd'] and cur_lhd.subsetString() == 'Classification = 6 AND Z >= 1000',
          cur_lhd.subsetString())
    state = {row.name for row in accessor.get_filter_state()}
    check('API filter state', {'parcelle', 'lhd'} <= state, str(state))
    result = accessor.export_layers(['parcelle', 'lhd'], os.path.join(EXPORTS, 'export_rest'), 'GeoJSON', 'COG', 'LAZ')
    check('API export_layers', sorted(result.done) == ['lhd', 'parcelle']
          and all(os.path.exists(path) for path in result.outputs.values()), str(result.outputs))
    result = accessor.clear_filters(['parcelle', 'lhd'])
    check('API clear_filters', sorted(result.done) == ['lhd', 'parcelle'] and cur_par.subsetString() == '', str(result))
    registry().restore_all(project)


def s22_qgis_process_loading():
    """qgis_process loads the plugin without iface and only calls initProcessing()."""
    import qgis.utils
    reg = QgsApplication.processingRegistry()
    existing = reg.providerById('filtermate')
    if existing is not None:
        reg.removeProvider(existing)
    package = os.path.basename(os.path.dirname(HERE))
    started = qgis.utils.startProcessingPlugin(package)
    provider = reg.providerById('filtermate')
    count_ = len(provider.algorithms()) if provider is not None else 0
    check('qgis_process: plugin starts without iface and registers its provider', started and count_ == 13,
          f"started={started} algorithms={count_}")


def s23_automation_followups():
    """Raster source alone in expression mode; raster export progress and cancellation."""
    import processing  # noqa: F401
    from qgis.core import QgsProcessingFeedback
    from filter_mate.adapters.public_api import operations
    cur_mnt = _layers('mnt')[0]
    result = processing.run('filtermate:cross_filter_from_raster', {
        'SOURCE': cur_mnt, 'MODE': 2, 'EXPRESSION': '"mnt@1" > 1300', 'FILTER_SOURCE': True, 'TARGETS': []})
    check('raster source alone, expression mode: masked', cur_mnt.source().endswith('.vrt')
          and result['OUTPUT'] == [cur_mnt.id()], cur_mnt.source()[-30:])
    _clear(cur_mnt)

    feedback = QgsProcessingFeedback()
    progress = []
    feedback.progressChanged.connect(progress.append)
    report = operations.export_layers([cur_mnt], _fresh(os.path.join(EXPORTS, 'progress')), raster_format='GTiff',
                                      feedback=feedback)
    check('raster export reports its progress', report.ok and any(0 < p < 100 for p in progress) and progress[-1] == 100,
          f"{len(progress)} values, last={progress[-1] if progress else None}")
    feedback = QgsProcessingFeedback()
    feedback.progressChanged.connect(lambda value: value > 5 and feedback.cancel())
    report = operations.export_layers([cur_mnt], _fresh(os.path.join(EXPORTS, 'cancel')), raster_format='GTiff',
                                      feedback=feedback)
    check('raster export stops on cancel', not report.ok and report.failed.get('mnt') == 'canceled', str(report.failed))


for scenario in (s0_predicates, s1_vector_to_raster, s2_vector_to_point_cloud, s3_raster_to_vector,
                 s4_raster_to_raster, s5_raster_to_point_cloud, s6_point_cloud_to_vector,
                 s7_point_cloud_to_raster, s8_point_cloud_to_point_cloud, s9_exports, s10_replay_on_reopen, s11_favorites,
                 s12_refilter_and_operators, s13_processing, s14_raster_selection_replay,
                 s15_rest_api_accessor, s16_undo_keeps_newer_changes, s17_processing_algorithms,
                 s18_apply_favorite_headless, s19_models, s20_public_api, s21_rest_accessor_v5,
                 s22_qgis_process_loading, s23_automation_followups):
    only = [name for name in os.environ.get('FM5_ONLY', '').split(',') if name]
    if only and not any(scenario.__name__.startswith(name + '_') for name in only):
        continue  # FM5_ONLY=s13,s16 runs a subset (quick iterations)
    print(f"--- {scenario.__name__}", flush=True)
    safe(scenario)

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("FAILED: " + "; ".join(failed))
cache.purge_session()
