"""Native regression checks for the deep audit; only disposable data is written."""
import importlib
import json
import os
import pathlib
import sys
import tempfile
import types

os.environ['FILTERMATE_LOG_DIR'] = '/tmp/filtermate-audit-logs'
from osgeo import gdal, osr
import numpy as np
from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsFeature,
                       QgsGeometry, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG = 'audit_native_filtermate'
for parts in ('', 'core', 'core.domain', 'core.services', 'core.export', 'core.filter',
              'adapters', 'adapters.qgis', 'adapters.qgis.coverage_layers', 'adapters.public_api',
              'infrastructure', 'infrastructure.database', 'infrastructure.utils', 'config'):
    name = PKG + ('.' + parts if parts else '')
    module = types.ModuleType(name)
    module.__path__ = [str(ROOT.joinpath(*parts.split('.'))) if parts else str(ROOT)]
    sys.modules[name] = module


def load(name):
    return importlib.import_module(PKG + '.' + name)


app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()
ops = load('adapters.public_api.operations')
service_mod = load('core.services.cross_filter_service')
jobs = load('adapters.qgis.coverage_layers.source_jobs')
cross = load('core.domain.cross_filter')
kind = load('core.domain.layer_kind').LayerKind
exporters = load('adapters.qgis.coverage_layers.exporters')
guard = load('core.export.target_guard')
cache = load('adapters.qgis.coverage_layers.cache')
results = []
folder = pathlib.Path(tempfile.mkdtemp(prefix='filtermate_native_audit_'))
cache.set_cache_root(str(folder / 'cache'))


def raster(path, value=1):
    dataset = gdal.GetDriverByName('GTiff').Create(str(path), 8, 8, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((700000, 1, 0, 6600000, 0, -1))
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(2154)
    dataset.SetProjection(crs.ExportToWkt())
    dataset.GetRasterBand(1).SetNoDataValue(-9999)
    dataset.GetRasterBand(1).Fill(value)
    dataset = None


def valid_pixels(path):
    dataset = gdal.Open(str(path))
    band = dataset.GetRasterBand(1)
    return int(np.count_nonzero(band.ReadAsArray() != band.GetNoDataValue()))


def vector():
    layer = QgsVectorLayer('Point?crs=epsg:2154&field=id:integer', 'target', 'memory')
    features = []
    for i, (x, y) in enumerate(((700001, 6599999), (700006, 6599994), (700003, 6599997)), 1):
        feature = QgsFeature(layer.fields())
        feature['id'] = i
        feature.setGeometry(QgsGeometry.fromWkt(f'POINT({x} {y})'))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    return layer


area = QgsGeometry.fromRect(QgsRectangle(700000, 6599996, 700004, 6600000))
crs = QgsCoordinateReferenceSystem('EPSG:2154')

# F1: perform an actual in-place raster clip, then export over the original.
path = folder / 'dem.tif'
raster(path)
before = valid_pixels(path)
layer = QgsRasterLayer(str(path), 'dem', 'gdal')
project.addMapLayer(layer)
report = ops.cross_filter_by_geometry(area, crs, [layer], project=project)
assert report.done, report
assert layer.source() != str(path), layer.source()
exported = ops.export_layers([layer], str(folder), raster_format='GTiff', project=project)
after = valid_pixels(path)
assert not exported.done and exported.failed and before == after == 64, (exported, before, after)
results.append({'finding': 'F1', 'native': True, 'original_valid_pixels_before': before,
                'original_valid_pixels_after_export': after, 'unsafe_export_refused': True})
service_mod.release_coverage_layers()
project.clear()
cache.set_cache_root(str(folder / 'cache2'))

# F3: GDAL writes privately and leaves a layer with the old staging name intact.
output = folder / 'export.tif'
staging = pathlib.Path(str(output) + '.staging.tif')
raster(staging, 7)
other = QgsRasterLayer(str(staging), 'another_loaded_raster', 'gdal')
project.addMapLayer(other)
source_path = folder / 'input.tif'
raster(source_path, 3)
source = QgsRasterLayer(str(source_path), 'input', 'gdal')
project.addMapLayer(source)
assert guard.ProjectSources(project).layer_using(str(staging)) == 'another_loaded_raster'
assert ops._output_file(str(output), guard.ProjectSources(project)) == str(output)
result = exporters.RasterExportJob(source, str(output)).run()
assert result.success and staging.exists(), result
assert np.all(gdal.Open(str(staging)).ReadAsArray() == 7)
results.append({'finding': 'F3', 'native': True, 'loaded_staging_source_preserved': True})
project.clear()

# F7: real memory provider and feature source, then actual task apply and Undo.
target = vector()
project.addMapLayer(target)
initial = '"id" >= 1'
newer = '"id" >= 3'
assert target.setSubsetString(initial)
request = cross.CrossFilterRequest(target.id(), kind.OTHER, (cross.TargetSpec(target.id(), kind.VECTOR),),
                                    predicates=('Intersect',), other_layers_combine_operator='AND')
service = service_mod.CrossFilterService()
task = service.build_task(request, jobs.FixedGeometrySourceJob(target, area.asWkt()), project=project)
assert task.run() and task.target_jobs[0].outcome.success
assert target.setSubsetString(newer)
task.apply_results(True)
applied = target.subsetString()
service.undo(target.id(), project=project)
undone = target.subsetString()
assert applied == undone == newer and not task.changes, (applied, undone)
results.append({'finding': 'F7', 'native': True, 'newer_subset_preserved': True,
                'applied_subset': applied, 'after_undo': undone})
project.clear()

# F6: compute and apply in the explicit project, even with an empty singleton.
other_project = QgsProject()
target = vector()
other_project.addMapLayer(target)
request = cross.CrossFilterRequest(target.id(), kind.OTHER, (cross.TargetSpec(target.id(), kind.VECTOR),),
                                    predicates=('Intersect',))
service = service_mod.CrossFilterService()
task = service.build_task(request, jobs.FixedGeometrySourceJob(target, area.asWkt()), project=other_project)
assert len(task.target_jobs) == 1 and task.run() and task.target_jobs[0].outcome.success
task.apply_results(True)
assert task.outcomes[0].success and task.changes
assert target.subsetString() and target.featureCount() == 2
results.append({'finding': 'F6', 'native': True, 'prepared_in_explicit_project': True,
                'explicit_target_filtered': True})

service_mod.release_coverage_layers()
other_project.clear()
project.clear()
print('NATIVE_AUDIT_RESULT ' + json.dumps({'qgis': Qgis.QGIS_VERSION, 'gdal': gdal.VersionInfo('--version'),
                                        'results': results}), flush=True)
# Exit after cleanup: no long-lived QGIS Python wrapper may outlive QgsApplication.
os._exit(0)
