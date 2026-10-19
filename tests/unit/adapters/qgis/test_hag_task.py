# -*- coding: utf-8 -*-
"""Height above a DTM: the DTM is sampled at the point coordinates, without reprojection."""
import importlib.util
import pathlib
import sys

import pytest

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


try:
    from osgeo import osr  # noqa: F401
    HAS_GDAL = True
except ImportError:
    HAS_GDAL = False
# Two different CRS are told apart by GDAL (osr.IsSame); without it the task cannot tell and accepts.
needs_gdal = pytest.mark.skipif(not HAS_GDAL, reason="GDAL (osgeo) not installed")

fk = _fakes()
hag_task = fk.load("hag_task")
pdal_cli = fk.load("pdal_cli")
snapshots = fk.load("snapshots")
cache = fk.load("cache")

L93 = fk.FakeCrs('EPSG:2154')
L93_NGF = fk.FakeCrs('EPSG:5698', horizontal=L93)  # Lambert-93 + NGF-IGN69 height (LiDAR HD)
UTM31 = fk.FakeCrs('EPSG:32631')


class TestCrsMismatch:
    @pytest.mark.parametrize("cloud, dem", [(L93, L93), (L93_NGF, L93), (L93, L93_NGF)])
    def test_same_horizontal_crs(self, cloud, dem):
        assert hag_task.crs_mismatch(cloud, dem) == ''

    @needs_gdal
    def test_other_crs_is_named(self):
        message = hag_task.crs_mismatch(L93, UTM31)
        assert 'EPSG:32631' in message and 'EPSG:2154' in message and 'reproject' in message

    @needs_gdal
    def test_geographic_3d_cloud_with_a_2d_dtm(self):
        """EPSG:4979 (lat / lon / ellipsoidal height) and EPSG:4326 share X / Y."""
        assert hag_task.crs_mismatch(fk.FakeCrs('EPSG:4979'), fk.FakeCrs('EPSG:4326')) == ''

    def test_crs_gdal_cannot_read_is_not_refused(self):
        assert hag_task.crs_mismatch(fk.FakeCrs('USER:1', wkt='not a wkt'), fk.FakeCrs('USER:2', wkt='nor this')) == ''

    def test_unknown_crs_is_not_judged(self):
        assert hag_task.crs_mismatch(L93, fk.FakeCrs(valid=False)) == ''

    @needs_gdal
    def test_old_qgis_compound_crs_is_not_judged(self):
        """No horizontalCrs() before QGIS 3.38: a compound CRS cannot be told apart, PDAL is trusted."""
        class OldCrs(fk.FakeCrs):
            horizontalCrs = None

        compound = OldCrs('EPSG:5698', wkt='COMPD_CS["RGF93 / Lambert-93 + NGF-IGN69 height",PROJCS[...]]')
        assert hag_task.crs_mismatch(compound, OldCrs('EPSG:2154')) == ''
        assert hag_task.crs_mismatch(OldCrs('EPSG:2154'), OldCrs('EPSG:32631')) != ''


class Layer:
    def __init__(self, layer_id, crs, source):
        self._id, self._crs, self._source = layer_id, crs, source

    def id(self):
        return self._id

    def name(self):
        return self._id

    def crs(self):
        return self._crs

    def source(self):
        return self._source

    def extent(self):
        return fk.FakeRectangle(0, 0, 100, 100)

    def providerType(self):
        return 'copc'

    def subsetString(self):
        return ''

    def setSubsetString(self, subset):
        return True


class TestTask:
    @pytest.fixture
    def pipelines(self, monkeypatch, tmp_path):
        ran = []
        monkeypatch.setattr(hag_task, "QgsRectangle", fk.FakeRectangle)
        monkeypatch.setattr(hag_task, "QgsGeometry", fk.FakeGeometry)
        monkeypatch.setattr(pdal_cli, 'copc_unavailable_reason', lambda: '')
        monkeypatch.setattr(pdal_cli, 'run_pipeline', lambda stages, **kw: (ran.append(stages), (True, ''))[1])
        snapshots.registry()._derived.clear()
        cache.set_cache_root(str(tmp_path))
        yield ran
        cache.set_cache_root(None)

    @needs_gdal
    def test_dtm_in_another_crs_is_refused(self, pipelines):
        task = hag_task.HeightAboveGroundTask(Layer('cloud', L93, '/d/c.copc.laz'), Layer('dem', UTM31, '/d/dem.tif'))
        assert task.run() is False and 'reproject' in task.message
        assert pipelines == []

    def test_lidar_hd_with_a_lambert_93_dtm(self, pipelines):
        task = hag_task.HeightAboveGroundTask(Layer('cloud', L93_NGF, '/d/c.copc.laz'), Layer('dem', L93, '/d/dem.tif'))
        assert task.run() is True and len(pipelines) == 1

    def test_user_crs_written_as_wkt(self, pipelines):
        crs = fk.FakeCrs('USER:100002', wkt='PROJCS["local"]')
        task = hag_task.HeightAboveGroundTask(Layer('cloud', crs, '/d/c.copc.laz'), Layer('dem', crs, '/d/dem.tif'))
        assert task.run() is True
        assert pipelines[0][-1]['a_srs'] == 'PROJCS["local"]'
