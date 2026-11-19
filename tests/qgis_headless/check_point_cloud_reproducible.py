# -*- coding: utf-8 -*-
"""A filter whose source is a point cloud rewritten by PDAL gives the same footprint at every run.

2026-11-19: the same height above ground filter kept 82 to 85 road sections
from one run to the next. writers.copc samples the coarse levels of the
octree at random, from points that readers.copc hands over in the order its
threads finish; the footprint is read at the level of detail of its
resolution (pdal_cli.copc_writer, read_stages).

The height above ground runs through ``HeightAboveGroundTask.run`` and the
footprint through ``PointCloudSourceJob`` (the code of the plugin), FM_PC_RUNS
times (3 by default); every run must give the same footprint.

Needs the PDAL command line tool (2.4+): the ``fm-video`` image has one.

    docker run --rm -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen fm-video \
        python3 /src/tests/qgis_headless/check_point_cloud_reproducible.py

Without FM_PC_DATA the cloud and the DTM are synthetic (built once per run
of the check). FM_PC_DATA=<folder> reads the data of the site videos
(estavar_village.copc.laz, mnt_village.tif, estavar.gpkg) and also prints the
counts of the ``pruning`` and ``heights`` scenes (scripts/site_videos.py).
"""
import hashlib
import importlib
import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('FILTERMATE_LOG_DIR', tempfile.mkdtemp(prefix='fm_pc_repro_logs_'))
from qgis.core import QgsApplication, QgsRasterLayer, QgsVectorLayer  # noqa: E402

ROOT = Path(os.environ.get('FM_REPO') or Path(__file__).resolve().parents[2])
# Import the real adapters without starting the plugin/dock.
for part in ('', '.core', '.core.domain', '.core.filter', '.core.services', '.adapters', '.adapters.qgis',
             '.adapters.qgis.coverage_layers'):
    package = types.ModuleType('fm_pc_repro' + part)
    package.__path__ = [str(ROOT.joinpath(*part.strip('.').split('.'))) if part else str(ROOT)]
    sys.modules[package.__name__] = package


def module(name):
    return importlib.import_module('fm_pc_repro.' + name)


app = QgsApplication([], False)
app.initQgis()
pdal_cli = module('adapters.qgis.coverage_layers.pdal_cli')
hag_task = module('adapters.qgis.coverage_layers.hag_task')
source_jobs = module('adapters.qgis.coverage_layers.source_jobs')
footprint = module('adapters.qgis.coverage_layers.point_cloud_footprint')
cache = module('adapters.qgis.coverage_layers.cache')
results = []
folder = Path(tempfile.mkdtemp(prefix='fm_pc_repro_'))
cache.set_cache_root(str(folder / 'cache'))

# (scene, selection, buffer in metres, target layer, minimum share of a target covered; 0 = intersects)
SCENES = [('pruning', 'Classification = 5 AND HeightAboveGround >= 8', 3.0, 'troncon_de_route', 0.0),
          ('heights', 'Classification = 6 AND HeightAboveGround >= 7', 0.0, 'batiment', 0.5)]


def check(name, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    results.append(status)
    print(f'{status} {name} {detail}', flush=True)


def synthetic_data():
    """A cloud of 3 million points on 1 km (trees of class 5, roofs of class 6, ground) and a flat DTM at 100 m."""
    import numpy as np
    from osgeo import gdal, osr
    rng = np.random.default_rng(7)
    count = 3000000
    x = rng.uniform(0, 1000, count)
    y = rng.uniform(0, 1000, count)
    classification = rng.choice([2, 5, 6], count, p=[0.5, 0.3, 0.2])
    height = np.where(classification == 2, 0.0, rng.uniform(0, 20, count))
    gps_time = rng.uniform(0, 1000, count)
    text = folder / 'cloud.txt'
    np.savetxt(text, np.column_stack([x, y, 100 + height, classification, gps_time]), fmt='%.2f,%.2f,%.2f,%d,%.6f',
               header='X,Y,Z,Classification,GpsTime', comments='')
    cloud = folder / 'cloud.copc.laz'
    ok, message = pdal_cli.run_pipeline([{'type': 'readers.text', 'filename': str(text)},
                                         {'type': 'writers.copc', 'filename': str(cloud), 'a_srs': 'EPSG:2154'}])
    text.unlink()
    if not ok:
        raise RuntimeError(message)
    dtm = folder / 'dtm.tif'
    raster = gdal.GetDriverByName('GTiff').Create(str(dtm), 200, 200, 1, gdal.GDT_Float32)
    raster.SetGeoTransform((-10, 5.1, 0, 1010, 0, -5.1))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(2154)
    raster.SetProjection(srs.ExportToWkt())
    raster.GetRasterBand(1).Fill(100.0)
    raster = None
    return cloud, dtm, None


def counts(source, gpkg):
    """Targets kept by the source geometry of each scene (the predicate of the scenes, not the plugin's engine)."""
    found = {}
    for scene, _selection, _buffer, target, share in SCENES:
        geometry = source[scene]
        layer = QgsVectorLayer(f'{gpkg}|layername={target}', target, 'ogr')
        kept = 0
        for feature in layer.getFeatures():
            shape = feature.geometry()
            if not shape.intersects(geometry):
                continue
            if share and shape.intersection(geometry).area() < share * shape.area():
                continue
            kept += 1
        found[scene] = kept
    return found


def one_run(index, cloud, dtm, gpkg):
    layer = footprint.open_point_cloud(str(cloud), 'lhd', 'copc')
    dem = QgsRasterLayer(str(dtm), 'mnt')
    started = time.perf_counter()
    task = hag_task.HeightAboveGroundTask(layer, dem)
    if not task.run():
        raise RuntimeError(f'height above ground: {task.message}')
    hag_seconds = time.perf_counter() - started
    enriched = footprint.open_point_cloud(task.output, 'lhd', 'copc')
    digests, geometries = {}, {}
    for scene, selection, buffer, _target, _share in SCENES:
        job = source_jobs.PointCloudSourceJob(enriched, 2.0, selection=selection)
        request = SimpleNamespace(buffer_value=buffer, buffer_segments=5, buffer_type='Round')
        geometry = job.compute(request, lambda: False)
        if job.message:
            raise RuntimeError(f'{scene}: {job.message}')
        geometries[scene] = geometry
        digests[scene] = (job.details.get('points_read'), hashlib.md5(bytes(geometry.asWkb())).hexdigest()[:12])
        job.release()
    line = {'run': index, 'hag_s': round(hag_seconds, 1), 'footprints': digests}
    if gpkg is not None:
        line['counts'] = counts(geometries, gpkg)
    print('run ' + json.dumps(line), flush=True)
    os.remove(task.output)
    return digests, line.get('counts')


def main():
    if not pdal_cli.supports_copc():
        print(f'SKIP point cloud reproducibility: {pdal_cli.copc_unavailable_reason()}', flush=True)
        return 0
    data = os.environ.get('FM_PC_DATA')
    if data:
        cloud, dtm, gpkg = (Path(data) / 'estavar_village.copc.laz', Path(data) / 'mnt_village.tif',
                            Path(data) / 'estavar.gpkg')
    else:
        cloud, dtm, gpkg = synthetic_data()
    runs = [one_run(i, cloud, dtm, gpkg) for i in range(int(os.environ.get('FM_PC_RUNS', '3')))]
    for scene, *_ in SCENES:
        seen = {digests[scene] for digests, _ in runs}
        check(f'{scene}: same footprint at every run', len(seen) == 1, f'{sorted(seen)}')
    if gpkg is not None:
        for scene, *_ in SCENES:
            seen = [found[scene] for _, found in runs]
            check(f'{scene}: same count at every run', len(set(seen)) == 1, f'{seen}')
    stages = pdal_cli.read_stages(str(cloud))
    check('local COPC read by one thread', stages[0].get('threads') == 1, json.dumps(stages[0]))
    print(f"pdal {'.'.join(map(str, pdal_cli.version() or ()))}", flush=True)
    return 1 if 'FAIL' in results else 0


if __name__ == '__main__':
    try:
        code = main()
    finally:
        cache.set_cache_root(None)
    app.exitQgis()
    sys.exit(code)
