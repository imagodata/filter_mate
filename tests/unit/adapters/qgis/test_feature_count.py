# -*- coding: utf-8 -*-
"""The count of a filtered GeoPackage layer is exact or not told (``adapters/qgis/feature_count.py``).

2026-11-14: on the BD TOPO of the IGN (no ``gpkg_ogr_contents`` table), ``featureCount()`` of the commune layer
answered 930 with the filter ``"population" > 20000``, which keeps 7: QGIS counts such a table without its filter.
The agent showed "Filter on commune · 930 / 930". Such a layer is now counted by reading it with GDAL, as QGIS does,
within a time budget. GDAL is replaced here by a fake one (the unit tests run without it); what GDAL and QGIS read is
checked in ``tests/qgis_headless/check_gpkg_feature_count.py``.
"""
import importlib.util
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "feature_count.py"


@pytest.fixture
def counts():
    spec = importlib.util.spec_from_file_location("fm_feature_count_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gpkg(tmp_path):
    path = tmp_path / "bd topo #1.gpkg"
    path.write_bytes(b"x")
    return str(path)


class _Layer:
    def __init__(self, source, subset="", count=930, provider="ogr", storage="GPKG", modified=False):
        self._source, self._subset, self._count = source, subset, count
        self._provider, self._storage, self._modified = provider, storage, modified

    def providerType(self):
        return self._provider

    def dataProvider(self):
        return types.SimpleNamespace(storageType=lambda: self._storage)

    def source(self):
        return self._source + (f"|subset={self._subset}" if self._subset else "")

    def subsetString(self):
        return self._subset

    def isModified(self):
        return self._modified

    def featureCount(self):
        return self._count


class _FakeGdal:
    """What feature_count.py asks of GDAL: a layer of ``features`` features, an error at the end when ``fails``."""
    OF_VECTOR, OF_READONLY, CE_Failure = 4, 0, 3

    def __init__(self, features=7, fails=False, raises=False):
        self.features, self.fails, self.raises = features, fails, raises
        self.opened, self.filters, self.ignored, self.options, self.option_log = [], [], [], {}, []
        self.error = 0

    def PushErrorHandler(self, name):
        pass

    def PopErrorHandler(self):
        pass

    def ErrorReset(self):
        self.error = 0

    def GetLastErrorType(self):
        return self.error

    def GetThreadLocalConfigOption(self, name, default):
        return self.options.get(name, default)

    def SetThreadLocalConfigOption(self, name, value):
        self.option_log.append(value)
        self.options[name] = value

    def OpenEx(self, path, flags, allowed_drivers):
        self.opened.append((path, allowed_drivers))
        return self

    def GetLayerByName(self, name):
        self.layer_asked = name
        return self

    def GetLayer(self, index):
        self.layer_asked = index
        return self

    def SetAttributeFilter(self, subset):
        self.filters.append(subset)
        self.left = self.features
        return 0

    def GetLayerDefn(self):
        names = ("population", "nom")
        field = lambda i: types.SimpleNamespace(GetName=lambda: names[i])  # noqa: E731
        return types.SimpleNamespace(GetFieldCount=lambda: 2, GetFieldDefn=field, GetGeomFieldCount=lambda: 1,
                                     GetGeomFieldDefn=lambda i: types.SimpleNamespace(GetName=lambda: "geom"))

    def SetIgnoredFields(self, names):
        self.ignored = names
        return 0

    def GetNextFeature(self):
        if self.raises:
            raise RuntimeError("failed to prepare SQL")
        if self.left == 0:
            if self.fails:
                self.error = self.CE_Failure
            return None
        self.left -= 1
        return object()


@pytest.fixture
def fake_gdal(monkeypatch):
    gdal = _FakeGdal()
    package = types.ModuleType("osgeo")
    package.gdal = gdal
    monkeypatch.setitem(sys.modules, "osgeo", package)
    monkeypatch.setitem(sys.modules, "osgeo.gdal", gdal)
    return gdal


def test_a_filtered_geopackage_is_counted_by_reading_it(counts, gpkg, fake_gdal):
    layer = _Layer(f"{gpkg}|layername=commune", '"population" > 20000')  # QGIS answers 930, the whole table
    assert counts.exact_feature_count(layer) == 7
    assert fake_gdal.opened == [(gpkg, ["GPKG"])] and fake_gdal.layer_asked == "commune"
    assert fake_gdal.filters == ['"population" > 20000']
    # Only the key is read: every field and the geometry are left out.
    assert {"population", "nom", "geom", "OGR_GEOMETRY"} <= set(fake_gdal.ignored)
    # A locked file is not waited for, and the setting of the thread is given back.
    assert fake_gdal.option_log == ["0", None]


def test_featurecount_is_kept_without_a_subset_and_off_geopackage(counts, gpkg, fake_gdal):
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=batiment", count=930)) == 930
    # From 100 000 features QGIS may answer MAX(fid) - MIN(fid) + 1: the table is counted (test_feature_count_whole_table),
    # and a file that cannot be read gives no number rather than that one.
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=batiment", count=1_173_829)) is None
    assert counts.exact_feature_count(_Layer("/data/communes.shp", '"x" = 1', 12, storage="ESRI Shapefile")) == 12
    assert counts.exact_feature_count(_Layer("dbname='gis' table=\"commune\"", '"x" = 1', 7, "postgres")) == 7
    assert counts.exact_feature_count(_Layer("/data/communes.shp", count=-1, storage="ESRI Shapefile")) is None
    assert counts.exact_feature_count(_Layer("/data/communes.shp", count=-2, storage="ESRI Shapefile")) is None
    assert fake_gdal.opened == []


@pytest.mark.parametrize("source, subset", [
    ("{gpkg}|layername=commune|geometrytype=Point", "fid < 5"),
    ("/vsizip//data/x.zip/a.gpkg|layername=commune", "fid < 5"),
    ("/nowhere/x.gpkg|layername=commune", "fid < 5"),
    ("{gpkg}|layername=commune", "SELECT * FROM commune WHERE fid < 5"),
    ("{gpkg}|layername=commune", "  select * FROM commune"),
    ("{gpkg}|layername=commune", "\nWITH c AS (SELECT 1) SELECT * FROM c"),
    ("{gpkg}|layername=commune", "fid < 5 UNION ALL SELECT * FROM commune"),
    ("{gpkg}|layername=commune", "fid IN (SELECT fid FROM a INTERSECT SELECT fid FROM b)"),
    ("{gpkg}|layername=commune", "random() < 0"),
])
def test_what_is_not_counted(counts, gpkg, fake_gdal, source, subset):
    assert counts.exact_feature_count(_Layer(source.format(gpkg=gpkg), subset)) is None
    assert fake_gdal.opened == []


def test_a_layer_with_edits_not_saved_has_no_number(counts, gpkg, fake_gdal):
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=commune", "fid < 5", modified=True)) is None
    assert fake_gdal.opened == []


def test_source_parts(counts, gpkg):
    assert counts.source_parts(f"{gpkg}|layername=commune|subset=fid < 3") == (gpkg, "commune", 0)
    assert counts.source_parts(f"{gpkg}|layerid=2") == (gpkg, "", 2)
    assert counts.source_parts(gpkg) == (gpkg, "", 0)  # QGIS opens the first layer
    # The subset is the last option and its text cannot name another table.
    assert counts.source_parts(f"{gpkg}|layername=commune|subset='a|layername=other' = ''") == (gpkg, "commune", 0)
    assert counts.source_parts(f"{gpkg}|layerid=x")[0] is None


def test_a_layer_named_by_its_index(counts, gpkg, fake_gdal):
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layerid=2", "fid < 5")) == 7
    assert fake_gdal.layer_asked == 2


class _Clock:
    """A clock that moves ``step`` seconds each time it is read."""

    def __init__(self, step):
        self.now, self.step, self.reads = 0.0, step, 0

    def __call__(self):
        self.reads += 1
        self.now += self.step
        return self.now


def test_the_clock_is_read_at_the_first_feature_then_every_clock_every(counts, gpkg, fake_gdal, monkeypatch):
    fake_gdal.features = 10_000
    clock = _Clock(0.0)
    monkeypatch.setattr(counts, "_clock", clock)
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 0")) == 10_000
    assert clock.reads == 1 + 1 + 10_000 // counts.CLOCK_EVERY  # the deadline, the first feature, then every N


def test_past_the_budget_there_is_no_number(counts, gpkg, fake_gdal, monkeypatch):
    fake_gdal.features = 10_000
    monkeypatch.setattr(counts, "_clock", _Clock(0.3))  # 0.3 s at each look: past the budget at the fourth
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 0")) is None
    monkeypatch.setattr(counts, "_clock", _Clock(2.0))  # the first feature came after the budget
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 1")) is None
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 2"), budget=0) is None
    assert fake_gdal.option_log[-1] is None  # given back on the way out too


def test_a_failed_reading_has_no_number(counts, gpkg, fake_gdal):
    fake_gdal.fails = True
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", '"t".fid < 3')) is None
    fake_gdal.fails, fake_gdal.raises = False, True  # GDAL exceptions turned on elsewhere
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "m.fid < 3")) is None


def test_without_gdal_there_is_no_number(counts, gpkg, monkeypatch):
    monkeypatch.setitem(sys.modules, "osgeo", None)
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 3")) is None


def test_old_gdal_without_the_thread_setting_still_counts(counts, gpkg, fake_gdal, monkeypatch):
    monkeypatch.setattr(_FakeGdal, "SetThreadLocalConfigOption", None)
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 3")) == 7


def test_the_counts_of_a_file_as_it_is_are_kept(counts, gpkg, fake_gdal):
    layer = _Layer(f"{gpkg}|layername=commune", "fid < 8")
    assert counts.exact_feature_count(layer) == 7
    assert counts.exact_feature_count(layer, budget=0) == 7  # no budget needed: nothing read
    assert len(fake_gdal.opened) == 1
    os.utime(gpkg, ns=(1, 1))  # the file changed: read again
    fake_gdal.features = 5
    assert counts.exact_feature_count(layer) == 5
    with open(gpkg + "-wal", "wb") as wal:  # a write-ahead log appeared: read again
        wal.write(b"w")
    fake_gdal.features = 4
    assert counts.exact_feature_count(layer) == 4
    assert len(fake_gdal.opened) == 3


def test_no_number_is_kept_and_the_cache_is_bounded(counts, gpkg, fake_gdal, monkeypatch):
    fake_gdal.fails = True
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 3")) is None
    fake_gdal.fails = False
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 3")) == 7  # read again
    monkeypatch.setattr(counts, "CACHE_SIZE", 3)
    for number in range(10):
        counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", f"fid < {number}"))
    assert len(counts._CACHE) == 3


def test_features_to_read_never_says_fewer(counts, gpkg, fake_gdal):
    fake_gdal.fails = True
    # Not counted: what QGIS says, the count of the whole table.
    assert counts.features_to_read(_Layer(f"{gpkg}|layername=commune", "fid < 5")) == 930
    assert counts.features_to_read(_Layer("/data/x.shp", count=-1, storage="ESRI Shapefile")) == -1


class _Batches:
    """An Arrow stream of the fake layer: batches of ``size`` features, None at the end."""

    def __init__(self, gdal, size):
        self.gdal, self.size = gdal, size

    def GetNextRecordBatch(self):
        if self.gdal.raises:
            raise RuntimeError("failed to prepare SQL")
        if self.gdal.left == 0:
            if self.gdal.fails:
                self.gdal.error = self.gdal.CE_Failure
            return None
        length = min(self.size, self.gdal.left)
        self.gdal.left -= length
        self.gdal.batches += 1
        return types.SimpleNamespace(GetLength=lambda: length)


@pytest.fixture
def arrow_gdal(fake_gdal, monkeypatch):
    """The fake GDAL, of a version that reads by batches."""
    fake_gdal.batches, fake_gdal.features_read = 0, 0
    fake_gdal.VersionInfo = lambda name: "3120200"
    fake_gdal.ResetReading = lambda: setattr(fake_gdal, "left", fake_gdal.features)
    fake_gdal.GetArrowStream = lambda options: (fake_gdal.stream_options.append(options) or
                                                _Batches(fake_gdal, int(options[0].split("=")[1])))
    fake_gdal.stream_options = []
    read = fake_gdal.GetNextFeature

    def counted():
        fake_gdal.features_read += 1
        return read()
    fake_gdal.GetNextFeature = counted
    return fake_gdal


def test_a_plain_filter_is_read_by_batches(counts, gpkg, arrow_gdal):
    """2026-11-14: 270 000 features took 0.31 s feature after feature from Python, 0.03 s by batches."""
    arrow_gdal.features = 10_000
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", '"population" > 100')) == 10_000
    assert arrow_gdal.batches == 5 and arrow_gdal.features_read == 0
    assert arrow_gdal.stream_options == [[f"MAX_FEATURES_IN_BATCH={counts.ARROW_BATCH}"]]
    assert arrow_gdal.ignored  # the fields and the geometry are still left out of the reading


@pytest.mark.parametrize("subset", [
    "fid < 10 LIMIT 3", "fid < 10 ORDER BY fid LIMIT 2", "1 GROUP BY nom", "fid < 10 group by fid",
    '(SELECT COUNT(*) FROM "t" a WHERE a.fid = m.fid) > 0', "fid < 5 offset 2", "fid = 1; ", "fid = 1 -- x",
    "fid = 1 /* x */", "\"nom\" = 'limit 3'", "fid IN (1, 2) HAVING 1", "fid < 5 WINDOW w AS ()",
])
def test_more_than_a_condition_is_read_feature_after_feature(counts, gpkg, arrow_gdal, subset):
    """By batches GDAL leaves LIMIT, ORDER BY and GROUP BY out, and counts more than QGIS reads."""
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", subset)) == 7
    assert arrow_gdal.batches == 0 and arrow_gdal.features_read == 8  # the seven, and the end


def test_an_older_gdal_reads_feature_after_feature(counts, gpkg, arrow_gdal):
    arrow_gdal.VersionInfo = lambda name: "3080400"  # it has batches, never compared with the features here
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 8")) == 7
    assert arrow_gdal.batches == 0 and arrow_gdal.features_read == 8
    arrow_gdal.VersionInfo = lambda name: "not a number"
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 9")) == 7 and arrow_gdal.batches == 0


def test_no_batches_for_this_layer_falls_back_on_the_features(counts, gpkg, arrow_gdal):
    arrow_gdal.GetArrowStream = lambda options: None
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid < 8")) == 7
    assert arrow_gdal.features_read == 8


def test_batches_keep_the_budget_and_the_failures(counts, gpkg, arrow_gdal, monkeypatch):
    arrow_gdal.features = 10_000
    monkeypatch.setattr(counts, "_clock", _Clock(0.3))  # 0.3 s at each look: past the budget at the fourth
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 0")) is None
    assert arrow_gdal.batches == 4  # stopped there, of five: not read to the end
    monkeypatch.setattr(counts, "_clock", _Clock(0.0))
    arrow_gdal.fails = True
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 1")) is None
    arrow_gdal.fails, arrow_gdal.raises = False, True  # GDAL exceptions turned on elsewhere
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=t", "fid > 2")) is None
    assert arrow_gdal.option_log[-1] is None  # the setting of the thread is given back


def test_a_count_made_on_a_trial_copy_is_kept_for_the_layer_once_filtered(counts, gpkg, fake_gdal):
    """Setting a filter makes QGIS rewrite the header of the file (3.28 and later): the count of the copy, made
    for the file as it was, was read again, and again by who asked next."""
    trial = _Layer(f"{gpkg}|layername=commune", "fid < 8")
    assert counts.exact_feature_count(trial) == 7
    counts.note_trial(trial, 7)
    os.utime(gpkg, ns=(1, 1))  # what setting the filter does to the file
    layer = _Layer(f"{gpkg}|layername=commune", "fid < 8")
    counts.adopt_trial(layer)
    fake_gdal.features = 99  # read again, it would say so
    assert counts.exact_feature_count(layer) == 7 and len(fake_gdal.opened) == 1
    # Once only: the next change of the file is read.
    os.utime(gpkg, ns=(2, 2))
    counts.adopt_trial(layer)
    assert counts.exact_feature_count(layer) == 99


def test_a_trial_is_adopted_for_its_own_filter_and_table_and_not_for_long(counts, gpkg, fake_gdal, monkeypatch):
    clock = _Clock(0.0)
    monkeypatch.setattr(counts, "_clock", clock)
    counts.note_trial(_Layer(f"{gpkg}|layername=commune", "fid < 8"), 7)
    fake_gdal.features = 3
    os.utime(gpkg, ns=(1, 1))
    counts.adopt_trial(_Layer(f"{gpkg}|layername=commune", "fid < 9"))  # another filter
    counts.adopt_trial(_Layer(f"{gpkg}|layername=troncon", "fid < 8"))  # another table
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=commune", "fid < 9")) == 3
    clock.now += counts.TRIAL_WINDOW + 1  # too long ago: anything may have changed the file since
    os.utime(gpkg, ns=(2, 2))
    counts.adopt_trial(_Layer(f"{gpkg}|layername=commune", "fid < 8"))
    assert counts.exact_feature_count(_Layer(f"{gpkg}|layername=commune", "fid < 8")) == 3


def test_nothing_is_noted_for_what_is_not_counted_here(counts, gpkg, fake_gdal):
    counts.note_trial(_Layer("/data/communes.shp", '"x" = 1', 12, storage="ESRI Shapefile"), 12)
    counts.note_trial(_Layer(f"{gpkg}|layername=commune"), 930)  # no filter
    counts.note_trial(_Layer(f"{gpkg}|layername=commune", "fid < 8", modified=True), 7)
    counts.note_trial(_Layer(f"{gpkg}|layername=commune", "fid < 8"), -1)
    counts.note_trial(_Layer(f"{gpkg}|layername=commune", "SELECT * FROM commune"), 7)
    assert not counts._TRIALS
    for number in range(counts.TRIALS_KEPT + 5):
        counts.note_trial(_Layer(f"{gpkg}|layername=commune", f"fid < {number + 2}"), number)
    assert len(counts._TRIALS) == counts.TRIALS_KEPT
