# -*- coding: utf-8 -*-
"""
A GeoPackage read by GDAL accepts a subset its SQL cannot run (a function it does
not have): setSubsetString returns True, the provider keeps no error and the layer
reads no feature (measured in QGIS 3.22, 3.44 and 4.3, 2026-11-18). The filter was
reported as a success. safe_set_subset_string now prepares the statement first, on
a connection of its own, and refuses the subset with SQLite's own words; the layer
is not touched. Only a subset that holds what a source may lack (a function, the
table of a subquery, a column given with its table) is prepared.

The real behaviour (eight kinds of files, three versions of QGIS) is measured by a
probe in Docker; these tests hold the logic with a stand-in for ``osgeo.gdal``.

Module tested: infrastructure.database.sql_utils
"""
import sys
import types

import pytest

from infrastructure.database import sql_utils


class _Provider:
    def __init__(self, storage):
        self._storage = storage

    def storageType(self):
        return self._storage

    def errors(self):
        return []


class _Layer:
    """A layer that, like the ogr provider on a GeoPackage, accepts any subset."""

    def __init__(self, storage='GPKG', provider_type='ogr', subset=''):
        self._provider = _Provider(storage)
        self._provider_type = provider_type
        self._subset = subset
        self.calls = []

    def name(self):
        return 'zones'

    def providerType(self):
        return self._provider_type

    def source(self):
        return '/data/zones.gpkg|layername=zones'

    def isValid(self):
        return True

    def dataProvider(self):
        return self._provider

    def fields(self):
        return []

    def featureCount(self):
        return 5

    def subsetString(self):
        return self._subset

    def setSubsetString(self, expression):
        self.calls.append(expression)
        self._subset = expression
        return True


class _Dataset:
    def __init__(self, gdal):
        self._gdal = gdal

    def GetLayerCount(self):
        return len(self._gdal.tables)

    def GetLayer(self, index):
        name = self._gdal.tables[index]
        return types.SimpleNamespace(GetName=lambda: name)

    def ExecuteSQL(self, statement):
        self._gdal.statements.append(statement)
        error = next((text for word, text in self._gdal.failures.items() if word in statement), '')
        self._gdal.last_error = error
        if error and self._gdal.exceptions:
            raise RuntimeError(error)
        return None if error else object()

    def ReleaseResultSet(self, rows):
        self._gdal.released += 1


@pytest.fixture
def gdal(monkeypatch):
    """A stand-in for osgeo.gdal: ExecuteSQL fails as SQLite does on the words of ``failures``."""
    module = types.SimpleNamespace(
        OF_VECTOR=4, OF_READONLY=0, tables=['zones'], statements=[], opened=[], released=0, last_error='',
        exceptions=False, missing=False, handlers=[], options={'SQLITE_BUSY_TIMEOUT': '5000'}, waits=[],
        failures={'bounds_width': 'In ExecuteSQL(): sqlite3_prepare_v2(EXPLAIN SELECT 1 FROM "zones" m WHERE '
                                  'bounds_width("geom") > 2): no such function: bounds_width',
                  'locked': 'database is locked'})

    def open_ex(filename, flags, allowed_drivers=None, open_options=None):
        module.opened.append((filename, tuple(allowed_drivers or ()), tuple(open_options or ())))
        module.waits.append(module.options.get('SQLITE_BUSY_TIMEOUT'))
        return None if module.missing else _Dataset(module)

    module.OpenEx = open_ex
    module.PushErrorHandler = module.handlers.append
    module.PopErrorHandler = module.handlers.pop
    module.GetThreadLocalConfigOption = lambda key, default=None: module.options.get(key, default)
    module.SetThreadLocalConfigOption = lambda key, value: module.options.__setitem__(key, value)
    module.ErrorReset = lambda: setattr(module, 'last_error', '')
    module.GetLastErrorMsg = lambda: module.last_error
    osgeo = types.ModuleType('osgeo')
    osgeo.gdal = module
    monkeypatch.setitem(sys.modules, 'osgeo', osgeo)
    monkeypatch.setitem(sys.modules, 'osgeo.gdal', module)
    monkeypatch.setattr(sql_utils, '_sql_file_table', lambda layer: ('/data/zones.gpkg', 'zones', None, ['A=B']))
    return module


@pytest.fixture
def reasons(monkeypatch):
    kept = {}
    monkeypatch.setattr(sql_utils, '_remember_refusal', lambda layer, reason: kept.__setitem__(id(layer), reason))
    return kept


def test_a_subset_the_source_cannot_run_is_refused_before_it_is_set(gdal, reasons):
    layer = _Layer(subset='"fid" IN (1, 2, 3)')

    assert sql_utils.safe_set_subset_string(layer, 'bounds_width("geom") > 2') is False

    assert layer.calls == []  # the layer is not touched: its former subset stays
    assert layer.subsetString() == '"fid" IN (1, 2, 3)'
    assert reasons[id(layer)] == 'no such function: bounds_width'
    assert gdal.statements == ['EXPLAIN SELECT 1 FROM "zones" m WHERE bounds_width("geom") > 2']
    assert gdal.opened == [('/data/zones.gpkg', ('GPKG', 'SQLite'), ('A=B',))]
    # a locked file is not waited for, GDAL's errors stay out of the log; both as they were afterwards
    assert gdal.waits == ['0'] and gdal.options['SQLITE_BUSY_TIMEOUT'] == '5000' and gdal.handlers == []


def test_the_refusal_reads_the_error_gdal_raises_too(gdal, reasons):
    gdal.exceptions = True  # gdal.UseExceptions(), turned on by another plugin
    layer = _Layer()

    assert sql_utils.safe_set_subset_string(layer, 'bounds_width("geom") > 2') is False
    assert reasons[id(layer)] == 'no such function: bounds_width'


def test_a_subset_the_source_runs_is_set_and_the_former_reason_forgotten(gdal, reasons):
    layer = _Layer()
    reasons[id(layer)] = 'no such function: bounds_width'

    assert sql_utils.safe_set_subset_string(layer, 'ST_MinX("geom") > 2') is True

    assert layer.calls == ['ST_MinX("geom") > 2']
    assert reasons[id(layer)] == ''
    assert gdal.released == 1 and gdal.handlers == []


def test_the_former_reason_is_forgotten_when_the_subset_is_removed(gdal, reasons):
    layer = _Layer(subset='"pop" > 2')
    reasons[id(layer)] = 'no such function: bounds_width'

    assert sql_utils.safe_set_subset_string(layer, '') is True

    assert reasons[id(layer)] == ''
    assert gdal.statements == []  # nothing to prepare


def test_an_error_that_is_not_about_the_sql_is_left_to_the_provider(gdal, reasons):
    layer = _Layer()

    assert sql_utils.safe_set_subset_string(layer, 'abs("locked") = 1') is True
    assert layer.calls == ['abs("locked") = 1']
    assert gdal.options['SQLITE_BUSY_TIMEOUT'] == '5000' and gdal.handlers == []


def test_a_file_that_cannot_be_opened_is_left_to_the_provider(gdal, reasons):
    gdal.missing = True
    layer = _Layer()

    assert sql_utils.safe_set_subset_string(layer, 'bounds_width("geom") > 2') is True
    assert layer.calls == ['bounds_width("geom") > 2']


@pytest.mark.parametrize('storage, provider_type', [('ESRI Shapefile', 'ogr'), ('GPKG', 'spatialite'), (None, 'ogr')])
def test_other_sources_are_not_prepared(gdal, reasons, storage, provider_type):
    layer = _Layer(storage=storage, provider_type=provider_type)

    assert sql_utils.safe_set_subset_string(layer, 'bounds_width("geom") > 2') is True
    assert gdal.opened == []
    assert id(layer) not in reasons


@pytest.mark.parametrize('subset', [
    ' select * from zones where bounds_width("geom") > 2',
    'WITH k AS (SELECT 1) SELECT * FROM zones WHERE bounds_width("geom") > 2',
])
def test_a_subset_that_is_a_whole_statement_is_not_prepared(gdal, subset):
    assert sql_utils._unrunnable_subset(_Layer(), subset) is None
    assert gdal.opened == []


@pytest.mark.parametrize('subset, prepared', [
    ('"fid" IN (1, 2, 3)', False),
    ('"fid" IS NOT NULL AND "fid" IN (1, 2)', False),
    ('"pop" > 2.5 AND ("nom" = \'Parc (nord)\' OR "pop" < .5)', False),
    ('NOT ( "pop" > 1 )', False),
    ('("ratio" - 2) > -(CAST(1 AS REAL) / 1125899906842624)', False),
    ('"nom" COLLATE BINARY = \'f(x)\'', False),
    ('"pop" > 2 LIMIT 5', False),
    ('x_min("geom") > 2', True),
    ('ST_MinX ("geom") > 0', True),
    ('"fid" IN (SELECT id FROM rtree_z_geom WHERE minx <= 5)', True),
    ('"zones"."pop" > 2', True),
    ('m."pop" > 2', True),
    ('"nom" ~ \'^a\'', True),
    ('"nom" REGEXP \'^a\'', True),
    ('"nom" ilike \'a%\'', True),
    ('"pop" >', True),
    ('"pop" > 2 AND', True),
    ('"pop" > \'a', True),
    ('\'a"b\' = "nom" AND x_min("geom") > 2', True),
])
def test_only_what_a_source_may_lack_is_prepared(gdal, subset, prepared):
    assert sql_utils._may_not_run(subset) is prepared
    assert sql_utils._unrunnable_subset(_Layer(), subset) is None
    assert bool(gdal.opened) is prepared


def test_the_table_is_found_by_its_index_or_alone_in_its_file(gdal, monkeypatch):
    gdal.tables = ['other', 'my "zone"']
    monkeypatch.setattr(sql_utils, '_sql_file_table', lambda layer: ('/data/zones.gpkg', None, 1, []))
    assert sql_utils._unrunnable_subset(_Layer(), 'bounds_width("geom") > 2') == 'no such function: bounds_width'
    assert gdal.statements[-1] == 'EXPLAIN SELECT 1 FROM "my ""zone""" m WHERE bounds_width("geom") > 2'

    monkeypatch.setattr(sql_utils, '_sql_file_table', lambda layer: ('/data/zones.gpkg', '', None, []))
    count = len(gdal.statements)
    assert sql_utils._unrunnable_subset(_Layer(), 'bounds_width("geom") > 2') is None  # two tables, none named
    assert len(gdal.statements) == count


@pytest.mark.parametrize('message, reason', [
    ('sqlite3_prepare_v2(EXPLAIN SELECT 1 FROM "z" m WHERE f("geom") > 2) failed: no such function: f',
     'no such function: f'),
    ('no such column: m.nothere, in SELECT', 'no such column: m.nothere'),
    ('In ExecuteSQL(): sqlite3_prepare_v2(...): near ">": syntax error', 'near ">": syntax error'),
    ('In ExecuteSQL(): sqlite3_prepare_v2(...): incomplete input', 'incomplete input'),
    ('disk I/O error', None),
    ('database is locked', None),
])
def test_only_the_words_of_sqlite_about_the_statement_make_a_refusal(gdal, message, reason):
    gdal.failures = {'abs(': message}
    assert sql_utils._unrunnable_subset(_Layer(), 'abs("pop") > 2') == reason


@pytest.mark.parametrize('subset, left', [
    ('$length > 10', '$length'),
    ('"pop" > @seuil', '@seuil'),
    ('NOT ( $perimeter > 1 )', '$perimeter'),
])
def test_a_variable_or_a_function_of_qgis_left_in_the_subset_is_refused(gdal, reasons, subset, left):
    layer = _Layer(subset='"pop" > 0')

    assert sql_utils.safe_set_subset_string(layer, subset) is False

    assert layer.calls == [] and gdal.opened == []  # SQLite reads a parameter with no value: nothing to prepare
    assert reasons[id(layer)] == 'not known to the source: ' + left


def test_a_dollar_or_an_at_sign_in_a_text_is_not_a_variable(gdal, reasons):
    layer = _Layer()

    assert sql_utils.safe_set_subset_string(layer, '"nom" = \'$length @home\' AND "e-mail@" = 1') is True
    assert gdal.opened == []


def test_the_error_handler_is_taken_back_when_the_setting_of_the_wait_fails(gdal):
    def fails(key, value):
        raise RuntimeError('no such setting')

    gdal.SetThreadLocalConfigOption = fails
    assert sql_utils._unrunnable_subset(_Layer(), 'bounds_width("geom") > 2') is None
    assert gdal.handlers == []
