# -*- coding: utf-8 -*-
"""
Masking of secrets in FilterMate log messages.

QGIS writes ``password='...'`` in the source of a PostgreSQL layer that has no
authentication config, and several diagnostics log ``layer.source()`` or an
exception that quotes a connection string. :class:`SecretMaskingFilter` is
attached to every FilterMate handler, so the console and ``filtermate.log``
never carry a password whatever the call site logs.
"""

import logging
import re
from typing import Any

_MASK = '***'

# password=..., PASSWORD = '...', "password": "...", sslpassword=..., passwd=...
# The value is a quoted string (backslash escapes allowed) or a bare token.
_KEY_VALUE = re.compile(
    r"""(\b(?:ssl)?(?:password|passwd)["']?\s*[=:]\s*)"""
    r"""('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|[^\s,;&'")}\]]+)""",
    re.IGNORECASE,
)

# scheme://user:password@host
_URL_CREDENTIALS = re.compile(r'(\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:)([^\s@/]+)(@)', re.IGNORECASE)

# Cheap pre-check: most messages have nothing to mask
_HINT = re.compile(r'passw|passwd|://', re.IGNORECASE)


def _mask_value(match: 're.Match') -> str:
    value = match.group(2)
    if value[:1] in ('"', "'"):
        return f"{match.group(1)}{value[0]}{_MASK}{value[0]}"
    return f"{match.group(1)}{_MASK}"


def mask_sensitive_text(text: Any) -> Any:
    """Replace passwords found in a text by ``***``.

    Handles the PostgreSQL / QGIS ``password='x'`` form (quoted or not, with
    escapes), dict / JSON renderings (``'password': 'x'``) and
    ``scheme://user:x@host`` URLs. The rest of the text is untouched, so a
    connection string stays useful for diagnostics.

    Args:
        text: Any value; non-strings are returned as is.

    Returns:
        The text without secrets (the same object when there was none).
    """
    if not isinstance(text, str) or not _HINT.search(text):
        return text
    masked = _KEY_VALUE.sub(_mask_value, text)
    return _URL_CREDENTIALS.sub(rf'\1{_MASK}\3', masked)


class SecretMaskingFilter(logging.Filter):
    """Handler filter that masks passwords in the message and the traceback.

    It never rejects a record and never raises: a record that cannot be
    formatted is left for ``logging`` to report as usual.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
            masked = mask_sensitive_text(message)
            if masked is not message and masked != message:
                record.msg = masked
                record.args = None
            if record.exc_info and not record.exc_text:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.exc_text:
                record.exc_text = mask_sensitive_text(record.exc_text)
        except Exception:  # nosec B110 - logging must never fail because of the masking
            pass
        return True


def install_secret_masking(handler: logging.Handler) -> logging.Handler:
    """Attach a :class:`SecretMaskingFilter` to a handler (once).

    Args:
        handler: Any logging handler.

    Returns:
        The same handler, for chaining.
    """
    if not any(isinstance(f, SecretMaskingFilter) for f in handler.filters):
        handler.addFilter(SecretMaskingFilter())
    return handler
