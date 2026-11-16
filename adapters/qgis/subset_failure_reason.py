# -*- coding: utf-8 -*-
"""Why a provider refused a subset string, when it gives no reason itself.

2026-11-16: the PostgreSQL server of a project became unreachable. The
unfilter of 9 layers failed, ``layer.error()`` was empty, and the log read
"finished() ✗ FAILED: Cables · Wyre - " while the message bar listed the
layers with no reason.

What the provider says: QgsPostgresProvider adds the error of its query to
``errors()``. When the connection is gone and its reset failed, QgsPostgresConn
gets no result at all and the error is QgsPostgresResult's "no result buffer"
(``QObject::tr``, so translated in a translated QGIS). No other failure of a
query gives no result, so on a ``postgres`` layer that error alone names a
lost connection, in any language. When the query does return an error, its
first line is shown, a lost connection recognised by the wording of libpq.
The message log is not read: it repeats the SQL of the query, and messages of
other layers reach it meanwhile.
"""
import re
from typing import Callable, List

CONNECTION_LOST = 'connection to the database server lost: check the network or the VPN, then reload the layers'
NO_REASON = 'the data provider refused the filter without giving a reason'

# The result QgsPostgresConn gives when it has none (QgsPostgresResult::PQresultErrorMessage)
_NO_RESULT = 'no result buffer'
# libpq wording of a connection that is gone, in the first line of an error (English libpq;
# a translated libpq still ends in "no result buffer" when the reset fails)
_CONNECTION_LOST_MARKERS = (
    'no connection to the server',
    'server closed the connection',
    'could not connect to server',
    'terminating connection',
    'ssl syscall error',
    'could not receive data from server',
    'could not send data to server',
)
# Secrets an error line can carry: an URL token or key (passwords: mask_sensitive_text)
_URL_SECRET = re.compile(r'(?i)\b((?:access_)?token|api_?key|key|sig|signature|secret)=([^&\s\'"]+)')
_MAX_REASON = 300


def _first_line(text: str) -> str:
    stripped = (text or '').strip()
    line = stripped.splitlines()[0].strip() if stripped else ''
    return line if len(line) <= _MAX_REASON else line[:_MAX_REASON - 1] + '…'


def _masked(text: str) -> str:
    text = _URL_SECRET.sub(lambda match: f'{match.group(1)}=***', text)
    try:
        from ...infrastructure.logging.redaction import mask_sensitive_text
    except (ImportError, ValueError):  # loaded outside the plugin package (unit tests)
        try:
            from infrastructure.logging.redaction import mask_sensitive_text
        except Exception:  # catch-all safety net: no redaction module, the URL secrets are masked
            return text
    return mask_sensitive_text(text)


def _says_connection_lost(lines: List[str], no_result) -> bool:
    return any(line.lower() in no_result or any(marker in line.lower() for marker in _CONNECTION_LOST_MARKERS)
               for line in lines)


def failure_reason(layer_error: str, server_error: str, provider_errors: List[str], postgres: bool,
                   translate: Callable[[str], str], no_result_texts=(_NO_RESULT,)) -> str:
    """One line saying why the filter was refused.

    Args:
        layer_error: ``layer.error().message()`` (often empty).
        server_error: What the web-service filter path remembered for the layer.
        provider_errors: Errors the provider added during the attempt.
        postgres: The layer is read by the ``postgres`` provider.
        translate: Translation of CONNECTION_LOST and NO_REASON.
        no_result_texts: "no result buffer" and its translation in the running QGIS.
    """
    if server_error:
        return server_error
    if layer_error and layer_error.strip():
        return _masked(_first_line(layer_error))
    no_result = {text.strip().lower() for text in no_result_texts if text}
    lines = [_first_line(error) for error in provider_errors]
    lines = [line for line in lines if line]
    if postgres and _says_connection_lost(lines, no_result):
        return translate(CONNECTION_LOST)
    for line in lines:
        if line.lower() not in no_result:
            return _masked(line)
    return translate(NO_REASON)


def _translate(text: str) -> str:
    """The two fixed reasons, translated (literal calls, so that pylupdate5 extracts them)."""
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        if text == CONNECTION_LOST:
            result = QCoreApplication.translate('SubsetFailureReason', 'connection to the database server lost: check the network or the VPN, then reload the layers')  # noqa: E501
        else:
            result = QCoreApplication.translate('SubsetFailureReason', 'the data provider refused the filter without giving a reason')  # noqa: E501
        return result if isinstance(result, str) else text
    except Exception:  # catch-all safety net: no Qt (unit tests), keep the English text
        return text


def _no_result_texts():
    texts = [_NO_RESULT]
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate('QObject', _NO_RESULT)
        if isinstance(translated, str):
            texts.append(translated)
    except Exception:  # nosec B110 - no Qt (unit tests): the English text only
        pass
    return tuple(texts)


def _provider_errors(layer) -> List[str]:
    try:
        provider = layer.dataProvider()
        if provider is None:
            return []
        return [error for error in list(provider.errors()) if isinstance(error, str)]
    except Exception:  # catch-all safety net: a deleted layer or provider says nothing
        return []


def provider_error_count(layer) -> int:
    """How many errors the provider of the layer holds (the start of a watch)."""
    return len(_provider_errors(layer))


def postgres_connection_lost(layer, errors_before: int) -> bool:
    """The errors a postgres provider added since ``errors_before`` say its connection is gone.

    2026-11-16: the diagnostics of a refused subset then skip what opens a connection again
    (retry after reloadData, feature count, psycopg2 probe): about 30 s per layer when the
    host no longer answers.
    """
    try:
        if layer.providerType() != 'postgres':
            return False
    except Exception:  # catch-all safety net: a deleted layer
        return False
    lines = [line for line in (_first_line(error) for error in _provider_errors(layer)[errors_before:]) if line]
    no_result = {text.strip().lower() for text in _no_result_texts() if text}
    return _says_connection_lost(lines, no_result)


class SubsetFailureWatch:
    """Keeps the errors the provider of a layer adds while its subset string is set.

    Never raises: with a deleted layer or without QGIS (unit tests) it falls
    back to the generic reason.
    """

    def __init__(self, layer):
        self._layer = layer
        self._before = 0

    def __enter__(self):
        self._before = len(_provider_errors(self._layer))
        return self

    def __exit__(self, *exc_info):
        return False

    def reason(self) -> str:
        """Why the filter was refused, from what the layer and its provider said."""
        layer_error = ''
        try:
            error = self._layer.error()
            if error is not None:
                layer_error = error.message() or ''
        except Exception:  # catch-all safety net: a deleted layer
            layer_error = ''
        server_error = ''
        try:
            from .server_filter_translation import last_server_filter_error
            server_error = last_server_filter_error(self._layer) or ''
        except Exception:  # catch-all safety net: loaded outside the plugin package (unit tests)
            server_error = ''
        try:
            postgres = self._layer.providerType() == 'postgres'
        except Exception:  # catch-all safety net: a deleted layer
            postgres = False
        return failure_reason(
            layer_error=layer_error if isinstance(layer_error, str) else '',
            server_error=server_error if isinstance(server_error, str) else '',
            provider_errors=_provider_errors(self._layer)[self._before:],
            postgres=postgres,
            translate=_translate,
            no_result_texts=_no_result_texts(),
        )
