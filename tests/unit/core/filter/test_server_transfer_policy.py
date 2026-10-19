"""How a server attribute filter reaches its provider, per QGIS version (no QGIS imports)."""
import pytest

from core.filter.server_transfer_policy import ASYNC, PRELOADED_PROVIDER_MIN, REFUSE, SYNC, transfer_mode

# 5.0.0 only allowed the 3.44 and 4.2 branches: 3.32, 3.34, 3.40, 4.0 and
# every later release refused WFS / ArcGIS attribute filters, and QGIS < 3.32
# refused them all. Versions proven by tests/qgis_headless/check_stream_versions.py:
PROVEN = [33203, 33405, 33601, 34015, 34415, 40003, 40203, 40300]
FUTURE = [40400, 50000]
BEFORE = [32216, 32815, 33000, 33199]


@pytest.mark.parametrize('version', PROVEN + FUTURE)
@pytest.mark.parametrize('provider', ['wfs', 'WFS', 'arcgisfeatureserver'])
def test_web_providers_transfer_asynchronously_wherever_qgis_has_the_api(provider, version):
    assert transfer_mode(provider, version, False) == ASYNC


@pytest.mark.parametrize('version', BEFORE)
def test_wfs_falls_back_to_the_main_thread_setter_before_qgis_332(version):
    assert transfer_mode('wfs', version, False) == SYNC
    assert transfer_mode('WFS', version, False) == SYNC


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


@pytest.mark.parametrize('provider', ['mssql', 'oracle', 'hana', 'oapif', 'OAPIF', 'ogr', 'postgres', '', None])
@pytest.mark.parametrize('version', BEFORE + PROVEN + FUTURE)
def test_other_providers_keep_their_behaviour(provider, version):
    # Asynchronous only when the provider declares ParallelCreateProvider;
    # never a main-thread fallback (database connections, unproven CQL2).
    assert transfer_mode(provider, version, False) == REFUSE
