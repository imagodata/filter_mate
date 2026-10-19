# -*- coding: utf-8 -*-
"""gdal.Warp wrapper of the raster targets: the cutline WKT also works on GDAL < 3.9 (no ``cutlineWKT``)."""
import importlib.util
import pathlib
import struct

import pytest

gdal = pytest.importorskip("osgeo.gdal")

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "coverage_layers" / "gdal_warp.py"


def _load():
    spec = importlib.util.spec_from_file_location("fm_gdal_warp_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


warp = _load()

EPSG_2154 = ('PROJCS["RGF93 / Lambert-93",GEOGCS["RGF93",DATUM["Reseau_Geodesique_Francais_1993",'
             'SPHEROID["GRS 1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
             'PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],'
             'PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],'
             'PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],'
             'PARAMETER["false_northing",6600000],UNIT["metre",1]]')
# 10 x 10 pixels of 1 m, origin (1000, 2010); the cutline keeps the west half.
WEST_HALF = "POLYGON ((1000 2000,1005 2000,1005 2010,1000 2010,1000 2000))"


@pytest.fixture
def raster(tmp_path):
    path = str(tmp_path / "dem.tif")
    dataset = gdal.GetDriverByName('GTiff').Create(path, 10, 10, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((1000, 1, 0, 2010, 0, -1))
    dataset.SetProjection(EPSG_2154)
    dataset.GetRasterBand(1).Fill(42.0)
    dataset = None
    return path


def _kept_columns(path):
    dataset = gdal.Open(path)  # kept alive while its band is read
    data = dataset.GetRasterBand(1).ReadRaster(0, 5, 10, 1, buf_type=gdal.GDT_Float32)
    return [value == 42.0 for value in struct.unpack('10f', data)]


def _old_gdal(monkeypatch, native=False):
    """Pretend to be GDAL < 3.9: WarpOptions takes neither cutlineWKT nor cutlineSRS."""
    if native:
        return
    real = gdal.WarpOptions

    def old_options(*args, **kwargs):
        for name in ('cutlineWKT', 'cutlineSRS'):
            if name in kwargs:
                raise TypeError(f"WarpOptions() got an unexpected keyword argument '{name}'")
        return real(*args, **kwargs)

    monkeypatch.setattr(gdal, 'WarpOptions', old_options)
    monkeypatch.setattr(warp, 'warp_option_supported', lambda name: name not in ('cutlineWKT', 'cutlineSRS'))


@pytest.mark.parametrize("native", [True, False], ids=["cutlineWKT", "GDAL<3.9 fallback"])
def test_cutline_clips_the_same_way(monkeypatch, raster, tmp_path, native):
    if native and not warp.warp_option_supported('cutlineWKT'):
        pytest.skip("this GDAL has no cutlineWKT")
    _old_gdal(monkeypatch, native)
    out = str(tmp_path / "clip.vrt")
    dataset = warp.gdal_warp(out, raster, format='VRT', cutlineWKT=WEST_HALF, cutlineSRS=EPSG_2154,
                             cropToCutline=False, dstNodata=-9999.0)
    dataset = None  # noqa: F841 - flush the VRT
    assert _kept_columns(out) == [True] * 5 + [False] * 5


def test_fallback_leaves_no_temporary_cutline(monkeypatch, raster, tmp_path):
    """The cutline is copied into the VRT: the in-memory file is gone and the VRT still clips."""
    _old_gdal(monkeypatch)
    out = str(tmp_path / "clip.vrt")
    warp.gdal_warp(out, raster, format='VRT', cutlineWKT=WEST_HALF, cutlineSRS=EPSG_2154, dstNodata=-9999.0)
    listing = gdal.ReadDir('/vsimem/') or []
    assert not [name for name in listing if name.startswith('fm5_cutline_')]
    assert _kept_columns(out)[:5] == [True] * 5


def test_fallback_cleans_up_after_a_failure(monkeypatch, tmp_path):
    _old_gdal(monkeypatch)
    with pytest.raises(RuntimeError):
        warp.gdal_warp(str(tmp_path / "x.vrt"), str(tmp_path / "missing.tif"), format='VRT',
                       cutlineWKT=WEST_HALF, cutlineSRS=EPSG_2154)
    listing = gdal.ReadDir('/vsimem/') or []
    assert not [name for name in listing if name.startswith('fm5_cutline_')]


def test_bad_cutline_wkt_is_reported(monkeypatch, raster, tmp_path):
    _old_gdal(monkeypatch)
    with pytest.raises(RuntimeError, match="cutline"):
        warp.gdal_warp(str(tmp_path / "x.vrt"), raster, format='VRT', cutlineWKT="NOT WKT", cutlineSRS=EPSG_2154)


@pytest.mark.parametrize("native", [True, False], ids=["cutlineWKT", "GDAL<3.9 fallback"])
@pytest.mark.parametrize("cutline", [
    # make_valid / intersection results: polygon + a dangling line or point
    "GEOMETRYCOLLECTION (POLYGON ((1000 2000,1005 2000,1005 2010,1000 2010,1000 2000)),LINESTRING (1005 2000,1010 2010))",
    "GEOMETRYCOLLECTION (MULTIPOLYGON (((1000 2000,1005 2000,1005 2010,1000 2010,1000 2000))),POINT (1008 2005))",
    "POLYGON Z ((1000 2000 5,1005 2000 5,1005 2010 5,1000 2010 5,1000 2000 5))",
    "CURVEPOLYGON (COMPOUNDCURVE ((1000 2000,1005 2000,1005 2010,1000 2010,1000 2000)))",
], ids=["collection+line", "collection+point", "polygonZ", "curvepolygon"])
def test_cutline_keeps_the_polygonal_parts(monkeypatch, raster, tmp_path, native, cutline):
    if native and not warp.warp_option_supported('cutlineWKT'):
        pytest.skip("this GDAL has no cutlineWKT")
    _old_gdal(monkeypatch, native)
    out = str(tmp_path / "clip.vrt")
    warp.gdal_warp(out, raster, format='VRT', cutlineWKT=cutline, cutlineSRS=EPSG_2154, dstNodata=-9999.0)
    assert _kept_columns(out) == [True] * 5 + [False] * 5


def test_cutline_without_polygon_is_reported(raster, tmp_path):
    with pytest.raises(RuntimeError, match="no area"):
        warp.gdal_warp(str(tmp_path / "x.vrt"), raster, format='VRT',
                       cutlineWKT="LINESTRING (1000 2000,1010 2010)", cutlineSRS=EPSG_2154)


@pytest.fixture
def global_exceptions():
    """Another plugin turned GDAL / OGR exceptions on for the whole process."""
    from osgeo import ogr
    gdal_before, ogr_before = gdal.GetUseExceptions(), ogr.GetUseExceptions()
    gdal.UseExceptions()
    ogr.UseExceptions()
    yield
    if not gdal_before:
        gdal.DontUseExceptions()
    if not ogr_before:
        ogr.DontUseExceptions()


def test_fallback_with_global_exceptions(monkeypatch, raster, tmp_path, global_exceptions):
    _old_gdal(monkeypatch)
    out = str(tmp_path / "clip.vrt")
    warp.gdal_warp(out, raster, format='VRT', cutlineWKT=WEST_HALF, cutlineSRS=EPSG_2154, dstNodata=-9999.0)
    assert _kept_columns(out) == [True] * 5 + [False] * 5
    assert not [name for name in gdal.ReadDir('/vsimem/') or [] if name.startswith('fm5_cutline_')]


def test_bad_wkt_with_global_exceptions_names_the_cutline(raster, tmp_path, global_exceptions):
    with pytest.raises(RuntimeError, match="cutline"):
        warp.gdal_warp(str(tmp_path / "x.vrt"), raster, format='VRT', cutlineWKT="NOT WKT", cutlineSRS=EPSG_2154)


def test_cleanup_failure_never_masks_the_result(monkeypatch, raster, tmp_path):
    _old_gdal(monkeypatch)

    def failing_unlink(path):
        raise RuntimeError("unknown error occurred")

    monkeypatch.setattr(gdal, 'Unlink', failing_unlink)
    out = str(tmp_path / "clip.vrt")
    assert warp.gdal_warp(out, raster, format='VRT', cutlineWKT=WEST_HALF, cutlineSRS=EPSG_2154,
                          dstNodata=-9999.0) is not None


@pytest.mark.parametrize("wkt, expected", [
    ("GEOMETRYCOLLECTION (POLYGON ((0 0,1 0,1 1,0 0)),LINESTRING (0 0,2 2))", "MULTIPOLYGON"),
    ("POLYGON ((0 0,1 0,1 1,0 0))", "POLYGON"),
    ("LINESTRING (0 0,2 2)", None),
])
def test_polygonal_wkt(wkt, expected):
    result = warp.polygonal_wkt(wkt)
    assert (result.split(' ')[0] if result else None) == expected


def test_null_warp_is_failure_even_with_exception_manager(monkeypatch):
    """A canceled/failed GDAL call must never look like a successful derived file."""
    from contextlib import nullcontext
    monkeypatch.setattr(gdal, 'ExceptionMgr', lambda **kwargs: nullcontext(), raising=False)
    monkeypatch.setattr(gdal, 'Warp', lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match='gdal.Warp failed'):
        warp.gdal_warp('unused.vrt', 'unused.tif', format='VRT')
