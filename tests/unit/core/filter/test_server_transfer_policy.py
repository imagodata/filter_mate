"""How a server attribute filter reaches its provider, per QGIS version (no QGIS imports)."""
import pytest

from core.filter.server_transfer_policy import (
    ASYNC, MAX_TIMEOUT_SECONDS, PRELOADED_PROVIDER_MIN, REFUSE, SYNC, WFS_SETTER_SAFE_MIN, server_filter_timeout_ms,
    transfer_mode,
)

# 5.0.0 only allowed the 3.44 and 4.2 branches: 3.32, 3.34, 3.40, 4.0 and
# every later release refused WFS / ArcGIS attribute filters, and QGIS < 3.32
# refused them all. Versions proven by tests/qgis_headless/check_stream_versions.py:
PROVEN = [33203, 33405, 33601, 34015, 34415, 40003, 40203, 40300]
FUTURE = [40400, 50000]
SETTER_SAFE = [32403, 32601, 32815, 33000, 33199]  # WFS setter survives a concurrent read
SETTER_UNSAFE = [32200, 32216]  # QGIS 3.22 corrupts the heap: refused, as in 5.0
BEFORE = SETTER_UNSAFE + SETTER_SAFE


@pytest.mark.parametrize('version', PROVEN + FUTURE)
@pytest.mark.parametrize('provider', ['wfs', 'WFS', 'arcgisfeatureserver'])
def test_web_providers_transfer_asynchronously_wherever_qgis_has_the_api(provider, version):
    assert transfer_mode(provider, version, False) == ASYNC


@pytest.mark.parametrize('version', SETTER_SAFE)
def test_wfs_falls_back_to_the_main_thread_setter_before_qgis_332(version):
    assert transfer_mode('wfs', version, False) == SYNC
    assert transfer_mode('WFS', version, False) == SYNC


@pytest.mark.parametrize('version', SETTER_UNSAFE)
def test_wfs_is_refused_where_its_setter_corrupts_running_reads(version):
    assert transfer_mode('wfs', version, False) == REFUSE
    assert transfer_mode('wfs', WFS_SETTER_SAFE_MIN - 1, False) == REFUSE
    assert transfer_mode('wfs', WFS_SETTER_SAFE_MIN, False) == SYNC


@pytest.mark.parametrize('version', BEFORE)
def test_arcgis_is_refused_before_qgis_332_since_its_setter_fetches_object_ids(version):
    assert transfer_mode('arcgisfeatureserver', version, False) == REFUSE


def test_threshold_is_the_preloaded_provider_api():
    assert PRELOADED_PROVIDER_MIN == 33200
    assert transfer_mode('wfs', PRELOADED_PROVIDER_MIN - 1, False) == SYNC
    assert transfer_mode('wfs', PRELOADED_PROVIDER_MIN, False) == ASYNC


def test_declared_parallel_creation_still_needs_the_preloaded_provider_api():
    assert transfer_mode('postgres', PRELOADED_PROVIDER_MIN, True) == ASYNC
    assert transfer_mode('postgres', PRELOADED_PROVIDER_MIN - 1, True) == REFUSE
    assert transfer_mode('arcgisfeatureserver', PRELOADED_PROVIDER_MIN - 1, True) == REFUSE
    assert transfer_mode('wfs', PRELOADED_PROVIDER_MIN - 1, True) == SYNC
    assert WFS_SETTER_SAFE_MIN < PRELOADED_PROVIDER_MIN


@pytest.mark.parametrize('provider', ['mssql', 'oracle', 'hana', 'oapif', 'OAPIF', 'ogr', 'postgres', '', None])
@pytest.mark.parametrize('version', BEFORE + PROVEN + FUTURE)
def test_other_providers_keep_their_behaviour(provider, version):
    # Asynchronous only when the provider declares ParallelCreateProvider;
    # never a main-thread fallback (database connections, unproven CQL2).
    assert transfer_mode(provider, version, False) == REFUSE


# --- server filter timeout (2026-10-20) ---------------------------------------
# A fixed 30 s: the public Géoplateforme WFS sometimes answered later, the
# filter was canceled and had to be retried.

def _config(**values):
    """APP.OPTIONS.SERVER_FILTER as config.default.json writes it."""
    return {key: {'value': value, 'description': '...'} for key, value in values.items()}


@pytest.mark.parametrize('provider', ['wfs', 'WFS', 'oapif', 'OAPIF'])
def test_web_feature_services_wait_sixty_seconds_by_default(provider):
    assert server_filter_timeout_ms(provider) == 60000
    assert server_filter_timeout_ms(provider, {}) == 60000
    assert server_filter_timeout_ms(provider, _config(timeout_seconds=5)) == 60000


@pytest.mark.parametrize('provider', ['arcgisfeatureserver', 'mssql', 'oracle', 'hana', 'postgres', '', None])
def test_other_providers_wait_thirty_seconds_by_default(provider):
    assert server_filter_timeout_ms(provider) == 30000
    assert server_filter_timeout_ms(provider, _config(wfs_timeout_seconds=5)) == 30000


def test_both_delays_are_configurable():
    params = _config(wfs_timeout_seconds=90, timeout_seconds=12.5)
    assert server_filter_timeout_ms('WFS', params) == 90000
    assert server_filter_timeout_ms('arcgisfeatureserver', params) == 12500
    # A plain value (no {"value": ...} wrapper), as a hand-edited file may hold.
    assert server_filter_timeout_ms('wfs', {'wfs_timeout_seconds': 120}) == 120000
    assert server_filter_timeout_ms('wfs', _config(wfs_timeout_seconds=MAX_TIMEOUT_SECONDS)) == 600000
    assert server_filter_timeout_ms('wfs', _config(wfs_timeout_seconds=1)) == 1000


@pytest.mark.parametrize('value', [0, -5, 0.5, MAX_TIMEOUT_SECONDS + 1, 1e12, float('inf'), float('nan'),
                                   True, False, '60', None, [60], {'nested': 1}])
def test_a_malformed_value_keeps_the_bounded_default(value):
    assert server_filter_timeout_ms('wfs', _config(wfs_timeout_seconds=value)) == 60000
    assert server_filter_timeout_ms('arcgisfeatureserver', _config(timeout_seconds=value)) == 30000


@pytest.mark.parametrize('section', [None, 'off', 42, [], {'wfs_timeout_seconds': {'description': 'no value'}}])
def test_a_malformed_section_keeps_the_defaults(section):
    assert server_filter_timeout_ms('wfs', section) == 60000
    assert server_filter_timeout_ms('mssql', section) == 30000
