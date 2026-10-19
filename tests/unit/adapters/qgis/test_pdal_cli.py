# -*- coding: utf-8 -*-
"""pdal command line tool: version detection and the COPC writer gate (writers.copc needs PDAL 2.4)."""
import importlib.util
import pathlib
import subprocess

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "coverage_layers" / "pdal_cli.py"


def _load():
    spec = importlib.util.spec_from_file_location("fm_pdal_cli_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pdal_cli = _load()


@pytest.mark.parametrize('source, reader', [
    ('https://example.test/cloud.copc.laz?signature=secret#part', 'readers.copc'),
    ('https://example.test/ept.json?token=secret', 'readers.ept'),
])
def test_signed_remote_reader(source, reader):
    assert pdal_cli.reader_for(source) == reader


@pytest.mark.parametrize('source', ['https://example.test/ept.json', 'https://example.test/a.copc.laz'])
def test_remote_reads_require_bounds(fake_pdal, source):
    with pytest.raises(ValueError, match='extent'):
        pdal_cli.read_stages(source)


def test_ept_bounds_are_on_reader_and_crop_is_exact(fake_pdal):
    polygon = 'POLYGON((0 0,10 0,0 10,0 0))'
    stages = pdal_cli.read_stages('https://example.test/ept.json', (0, 0, 10, 10), polygon)
    assert stages[0]['bounds'] == '([0,10],[0,10])'
    assert stages[-1].get('polygon') == polygon


def test_old_remote_reader_refused_without_disclosing_url(fake_pdal):
    fake_pdal['out'] = BANNER.format('2.3.0')
    with pytest.raises(ValueError, match='2.4') as error:
        pdal_cli.read_stages('https://example.test/ept.json?token=secret', (0, 0, 1, 1))
    assert 'secret' not in str(error.value)


@pytest.mark.parametrize('bounds', [(0, 0, float('nan'), 1), (1, 0, 0, 1), (0, 0, 0, 1)])
def test_invalid_bounds_refused(fake_pdal, bounds):
    with pytest.raises(ValueError, match='extent'):
        pdal_cli.read_stages('https://example.test/ept.json', bounds)

BANNER = "-" * 80 + "\npdal {} (git-version: Release)\n" + "-" * 80 + "\n"


@pytest.fixture
def fake_pdal(monkeypatch):
    """Point find_pdal at a fake executable whose ``--version`` prints ``state['out']``."""
    state = {'exe': '/opt/pdal/bin/pdal', 'out': BANNER.format('2.6.3'), 'calls': 0, 'raise': None}

    def run(argv, **kwargs):
        state['calls'] += 1
        assert argv == [state['exe'], '--version']
        assert kwargs.get('errors') == 'replace'  # a non UTF-8 banner never raises
        assert kwargs.get('timeout', 99) <= 5  # read on the main thread at worst
        if state['raise'] is not None:
            raise state['raise']
        return subprocess.CompletedProcess(argv, 0, stdout=state['out'], stderr='')

    pdal_cli.reset_cache()
    monkeypatch.setattr(pdal_cli, 'find_pdal', lambda: state['exe'])
    monkeypatch.setattr(pdal_cli, 'reader_has_polygon', lambda reader: False)
    monkeypatch.setattr(pdal_cli.subprocess, 'run', run)
    yield state
    pdal_cli.reset_cache()


@pytest.mark.parametrize("text, expected", [
    ('2.6.3', (2, 6, 3)),
    ('2.3.0', (2, 3, 0)),
    ('2.4', (2, 4, 0)),
    ('3.0.0-dev', (3, 0, 0)),
])
def test_version_parsed_from_banner(fake_pdal, text, expected):
    fake_pdal['out'] = BANNER.format(text)
    assert pdal_cli.version() == expected


@pytest.mark.parametrize("text, supported", [('2.3.0', False), ('2.4.0', True), ('2.6.3', True), ('3.0.0', True)])
def test_copc_writer_needs_pdal_2_4(fake_pdal, text, supported):
    fake_pdal['out'] = BANNER.format(text)
    assert pdal_cli.supports_copc() is supported
    assert (pdal_cli.copc_unavailable_reason() == '') is supported


def test_old_pdal_reason_names_the_version(fake_pdal):
    fake_pdal['out'] = BANNER.format('2.3.0')
    assert '2.3.0' in pdal_cli.copc_unavailable_reason()


def test_unreadable_version_is_trusted(fake_pdal):
    """A pdal that answers oddly keeps the previous behavior: try it, report its error if it fails."""
    fake_pdal['out'] = 'something else\n'
    assert pdal_cli.version() is None
    assert pdal_cli.supports_copc() is True


@pytest.mark.parametrize("error", [OSError('exec format error'), subprocess.TimeoutExpired('pdal', 5)])
def test_pdal_that_cannot_run_is_not_used(fake_pdal, error):
    """Its pipelines would fail the same way: the QGIS exporter does the clip instead."""
    fake_pdal['raise'] = error
    assert pdal_cli.version() is None
    assert pdal_cli.supports_copc() is False
    assert pdal_cli.copc_unavailable_reason().startswith('pdal could not be run')
    pdal_cli.supports_copc()
    assert fake_pdal['calls'] == 1  # the failure is cached too


def test_warm_up_reads_the_version_in_the_background(fake_pdal):
    thread = pdal_cli.warm_up()
    thread.join(5)
    assert fake_pdal['calls'] == 1
    assert pdal_cli.warm_up() is None  # already known
    assert pdal_cli.version() == (2, 6, 3)
    assert fake_pdal['calls'] == 1


def test_version_asked_once_per_executable(fake_pdal):
    pdal_cli.version()
    pdal_cli.version()
    assert fake_pdal['calls'] == 1
    fake_pdal['exe'] = '/usr/bin/pdal'
    pdal_cli.version()
    assert fake_pdal['calls'] == 2


def test_no_pdal(monkeypatch):
    pdal_cli.reset_cache()
    monkeypatch.setattr(pdal_cli, 'find_pdal', lambda: None)
    assert pdal_cli.version() is None
    assert pdal_cli.supports_copc() is False
    assert pdal_cli.copc_unavailable_reason() == 'pdal not found'


class _Process:
    returncode = 0

    def communicate(self, timeout=None):
        return 'Ã©tÃ©', ''


def test_pipeline_output_read_as_utf8(monkeypatch):
    """PDAL writes UTF-8: the Windows locale codec (cp1252) cannot decode every byte of it."""
    seen = {}

    def popen(argv, **kwargs):
        seen.update(kwargs)
        return _Process()

    monkeypatch.setattr(pdal_cli, 'find_pdal', lambda: '/opt/pdal/bin/pdal')
    monkeypatch.setattr(pdal_cli.subprocess, 'Popen', popen)
    assert pdal_cli.run_pipeline([{"type": "readers.las", "filename": "été.las"}]) == (True, '')
    assert seen.get('encoding') == 'utf-8' and seen.get('errors') == 'replace'


class _Crs:
    def __init__(self, authid, wkt='PROJCS["x"]'):
        self._authid, self._wkt = authid, wkt

    def authid(self):
        return self._authid

    def toWkt(self):
        return self._wkt


@pytest.mark.parametrize("authid, expected", [
    ('EPSG:2154', 'EPSG:2154'),
    ('IGNF:LAMB93', 'IGNF:LAMB93'),
    ('ESRI:102110', 'ESRI:102110'),
    ('USER:100000', 'PROJCS["x"]'),  # a user CRS of this QGIS profile: PROJ does not know it
    ('', 'PROJCS["x"]'),
])
def test_writer_srs(authid, expected):
    assert pdal_cli.srs_for(_Crs(authid)) == expected


def test_arbiter_error_without_url_scheme_is_redacted(monkeypatch):
    class FailedProcess:
        returncode = 1
        def communicate(self, timeout=None):
            return '', "Could not read from 'example.test/ept.json?token=secret'"
    monkeypatch.setattr(pdal_cli, 'find_pdal', lambda: '/opt/pdal/bin/pdal')
    monkeypatch.setattr(pdal_cli.subprocess, 'Popen', lambda *args, **kw: FailedProcess())
    ok, message = pdal_cli.run_pipeline([{'type': 'readers.ept',
                                         'filename': 'https://example.test/ept.json?token=secret'}])
    assert not ok
    assert 'secret' not in message and 'example.test' not in message
