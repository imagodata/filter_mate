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

_QUOTED = r"'(?:[^'\\]|\\.)*'" + "|" + r'"(?:[^"\\]|\\.)*"'
_BARE = r"""[^\s,;&'")}\]]+"""

# Logs: key=value with any key that ends in password / passwd / pwd (password,
# sslpassword, PGPASSWORD, user_password, pwd...). The value is a quoted string
# (backslash escapes allowed) or a bare token.
_KEY_EQUALS = re.compile(
    r"(?P<key>\b[\w.\-]*(?:password|passwd|pwd))(?P<sep>\s*=\s*)(?P<val>" + _QUOTED + "|" + _BARE + ")",
    re.IGNORECASE,
)
# Logs: "password": "x" / 'password': 'x' (JSON, dict rendering). The key has to be quoted,
# so that prose such as "Missing password: please configure" is left alone.
_QUOTED_KEY_COLON = re.compile(
    r"""(?P<key>(["'])[\w.\-]*(?:password|passwd|pwd)\2)(?P<sep>\s*:\s*)(?P<val>""" + _QUOTED + ")",
    re.IGNORECASE,
)
# Saved data: only the libpq / QGIS URI form password='x', sslpassword='x', written with no
# space around "=" and not part of a longer name or quoted identifier. An expression such as
# "passwd" = 'abc' or passwd = 'abc' is data, not a connection string.
_URI_PASSWORD = re.compile(
    r"""(?<![\w"'.\-])(?P<key>(?:ssl)?password=)(?P<val>""" + _QUOTED + "|" + _BARE + ")",
    re.IGNORECASE,
)

# credentials in a URL: scheme://user:***@host (the *** part is masked)
_URL_CREDENTIALS = re.compile(r'(\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:)([^\s@/]+)(@)', re.IGNORECASE)

# Cheap pre-check: most messages have nothing to mask
_HINT = re.compile(r'passw|pwd|://', re.IGNORECASE)


def _mask_value(match: 're.Match') -> str:
    value = match.group('val')
    head = match.group('key') + match.group('sep') if 'sep' in match.groupdict() else match.group('key')
    if value[:1] in ('"', "'"):
        return f"{head}{value[0]}{_MASK}{value[0]}"
    return f"{head}{_MASK}"


def _mask_urls(text: str) -> str:
    return _URL_CREDENTIALS.sub(rf'\1{_MASK}\3', text)


def mask_sensitive_text(text: Any) -> Any:
    """Replace passwords found in a log text by ``***``.

    Handles ``key=value`` where the key ends in password / passwd / pwd (the
    PostgreSQL / QGIS ``password='x'`` form, ``PGPASSWORD=x``, ``user_password=x``,
    quoted or not, with escapes), dict / JSON renderings (``'password': 'x'``)
    and ``scheme://user:x@host`` URLs. The rest of the text is untouched, so a
    connection string stays useful for diagnostics. This one is meant for log
    lines; use :func:`mask_uri_secrets` for data that is saved.

    Args:
        text: Any value; non-strings are returned as is.

    Returns:
        The text without secrets (the same object when there was none).
    """
    if not isinstance(text, str) or not _HINT.search(text):
        return text
    masked = _KEY_EQUALS.sub(_mask_value, text)
    masked = _QUOTED_KEY_COLON.sub(_mask_value, masked)
    return _mask_urls(masked)


def mask_uri_secrets(text: Any) -> Any:
    """Replace the password of a connection string / URI found in a text by ``***``.

    Narrower than :func:`mask_sensitive_text`, for data that is saved
    (config.json, project settings): only ``password=`` / ``sslpassword=`` in
    the URI form and ``scheme://user:x@host`` URLs. An expression that merely
    mentions a column called ``passwd`` is not altered.

    Args:
        text: Any value; non-strings are returned as is.

    Returns:
        The text without the password (the same object when there was none).
    """
    if not isinstance(text, str) or not _HINT.search(text):
        return text
    return _mask_urls(_URI_PASSWORD.sub(_mask_value, text))


def scrub_secrets_in_place(data: Any) -> int:
    """Mask the connection passwords saved by an older version, in a JSON-like structure.

    Walks dicts and lists and applies :func:`mask_uri_secrets` to every string;
    an ``ACTIVE_POSTGRESQL`` entry (a connection at run time, never to be saved)
    that holds anything is emptied. Never logs a value.

    Args:
        data: Parsed config.json / project settings, modified in place.

    Returns:
        int: Number of values corrected (0 when there was nothing to mask).
    """
    corrections = 0

    def walk(node):
        nonlocal corrections
        items = node.items() if isinstance(node, dict) else enumerate(node)
        for key, value in list(items):
            if isinstance(node, dict) and key == 'ACTIVE_POSTGRESQL' and value not in (None, '', [], {}):
                node[key] = ''
                corrections += 1
            elif isinstance(value, str):
                masked = mask_uri_secrets(value)
                if masked != value:
                    node[key] = masked
                    corrections += 1
            elif isinstance(value, (dict, list)):
                walk(value)

    if isinstance(data, (dict, list)):
        walk(data)
    return corrections


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
