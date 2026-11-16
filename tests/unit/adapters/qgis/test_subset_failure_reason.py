# -*- coding: utf-8 -*-
"""Why a provider refused a subset string when it gives no reason itself.

2026-11-16: the PostgreSQL server of a project became unreachable; the unfilter of 9 layers failed
with "finished() ✗ FAILED: Cables · Wyre - " and the message bar listed the layers with no reason.
QgsPostgresProvider had added "no result buffer" to its errors(): QgsPostgresConn got no result at all.
"""
import importlib.util
import pathlib
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "subset_failure_reason.py"


def _load():
    spec = importlib.util.spec_from_file_location("fm_subset_failure_reason_test", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sfr():
    return _load()


def _reason(sfr, **kwargs):
    values = dict(layer_error='', server_error='', provider_errors=[], postgres=True)
    values.update(kwargs)
    return sfr.failure_reason(translate=lambda text: text, **values)


class TestFailureReason:
    def test_no_result_on_postgres_is_a_lost_connection(self, sfr):
        assert _reason(sfr, provider_errors=['no result buffer']) == sfr.CONNECTION_LOST

    def test_no_result_in_the_language_of_qgis(self, sfr):
        reason = _reason(sfr, provider_errors=['aucun tampon de résultat'],
                         no_result_texts=('no result buffer', 'aucun tampon de résultat'))
        assert reason == sfr.CONNECTION_LOST

    def test_no_result_elsewhere_is_no_reason(self, sfr):
        assert _reason(sfr, provider_errors=['no result buffer'], postgres=False) == sfr.NO_REASON

    @pytest.mark.parametrize("message", [
        'server closed the connection unexpectedly',
        'could not connect to server: Connection timed out',
        'SSL SYSCALL error: EOF detected',
        'FATAL:  terminating connection due to administrator command',
    ])
    def test_the_libpq_connection_messages_are_recognised(self, sfr, message):
        assert _reason(sfr, provider_errors=[message]) == sfr.CONNECTION_LOST

    def test_a_refused_login_is_not_a_lost_connection(self, sfr):
        message = 'connection to server at "db" (10.0.0.1), port 5432 failed: FATAL:  password authentication failed'
        assert _reason(sfr, provider_errors=[message]) == message

    def test_a_filter_value_in_the_query_is_not_read_as_a_marker(self, sfr):
        error = ('ERROR:  column "kode" does not exist\n'
                 'LINE 1: SELECT * FROM "t" WHERE "etat" = \'server closed the connection\'')
        assert _reason(sfr, provider_errors=[error]) == 'ERROR:  column "kode" does not exist'

    def test_a_web_service_refusal_is_not_a_database_connection(self, sfr):
        error = 'Download of features failed: Connection refused'
        assert _reason(sfr, provider_errors=[error], postgres=False) == error

    def test_nothing_said_anywhere_gives_the_generic_reason(self, sfr):
        assert _reason(sfr) == sfr.NO_REASON

    def test_the_layer_error_comes_before_the_guesses(self, sfr):
        assert _reason(sfr, layer_error='Invalid layer', provider_errors=['no result buffer']) == 'Invalid layer'

    def test_the_web_service_error_comes_first(self, sfr):
        assert _reason(sfr, server_error='WFS refused', layer_error='Invalid layer') == 'WFS refused'

    def test_a_long_provider_error_is_cut(self, sfr):
        assert len(_reason(sfr, provider_errors=['x' * 2000])) <= 300

    def test_secrets_of_an_url_are_masked(self, sfr):
        error = 'Error transferring https://h/arcgis/query?where=1&token=ABC123&f=json - server replied: Forbidden'
        reason = _reason(sfr, provider_errors=[error], postgres=False)
        assert 'ABC123' not in reason and 'token=***' in reason


class TestWatch:
    """The watch never breaks the apply loop, whatever QGIS offers."""

    def _layer(self, provider='postgres'):
        layer = MagicMock()
        layer.error.return_value = None
        layer.providerType.return_value = provider
        return layer

    def test_new_provider_errors_only(self, sfr):
        layer = self._layer()
        provider = layer.dataProvider.return_value
        provider.errors.return_value = ['ERROR:  old error']
        with sfr.SubsetFailureWatch(layer) as watch:
            provider.errors.return_value = ['ERROR:  old error', 'no result buffer']
        assert watch.reason() == sfr.CONNECTION_LOST

    def test_a_layer_without_provider(self, sfr):
        layer = self._layer()
        layer.dataProvider.return_value = None
        with sfr.SubsetFailureWatch(layer) as watch:
            pass
        assert watch.reason() == sfr.NO_REASON

    def test_the_translated_texts_are_the_constants(self, sfr, monkeypatch):
        """The literal strings of _translate (extracted by pylupdate5) are the constants word for word."""
        import sys
        import types
        seen = []
        core = types.SimpleNamespace(QCoreApplication=types.SimpleNamespace(
            translate=lambda context, text: seen.append((context, text)) or text))
        monkeypatch.setitem(sys.modules, 'qgis', types.SimpleNamespace(PyQt=types.SimpleNamespace(QtCore=core)))
        monkeypatch.setitem(sys.modules, 'qgis.PyQt', types.SimpleNamespace(QtCore=core))
        monkeypatch.setitem(sys.modules, 'qgis.PyQt.QtCore', core)
        sfr._translate(sfr.CONNECTION_LOST)
        sfr._translate(sfr.NO_REASON)
        assert seen == [('SubsetFailureReason', sfr.CONNECTION_LOST), ('SubsetFailureReason', sfr.NO_REASON)]
