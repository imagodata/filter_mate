# -*- coding: utf-8 -*-
"""
Opening psycopg2 connections without the multi-second stalls (PERF 2026-09-12).

Measured on a real project: every filter spent 21 s (then exactly the
``connect_timeout`` once one was set) inside ``psycopg2.connect()`` for a
server that answered in milliseconds as soon as the first attempt gave up.
Two libpq behaviours produce precisely that signature:

- the host resolves to an IPv6 address that drops packets and an IPv4 one
  that works; libpq tries the addresses in ``getaddrinfo`` order and only
  moves on after a full TCP connect timeout;
- ``gssencmode=prefer`` (the default) negotiates GSSAPI encryption first,
  which on Windows can hang on the SSPI/Kerberos lookup before libpq retries
  without it.

:func:`pg_connect_with_fallback` makes a first, fast attempt (IPv4
``hostaddr`` when the host resolves to one, ``gssencmode=disable``, short
timeout) and falls back to the caller's plain parameters when that fails, so
no working configuration is ever refused. Each attempt is logged with its
duration (``⏱ pg_layer_connect``) so the log tells which path was taken.
"""

import ipaddress
import logging
import socket
import time
from typing import Any, Dict, Optional

from .postgresql_support import psycopg2

logger = logging.getLogger('FilterMate.Database.PgConnect')

FAST_CONNECT_TIMEOUT_SECONDS = 5
PLAIN_CONNECT_TIMEOUT_SECONDS = 15

_HOSTADDR_CACHE: Dict[str, Optional[str]] = {}


def clear_hostaddr_cache() -> None:
    """Forget resolved addresses (tests, network change)."""
    _HOSTADDR_CACHE.clear()


def resolve_pg_hostaddr(host: Optional[str]) -> Optional[str]:
    """
    Return the IPv4 literal to pass as ``hostaddr`` for ``host``, or None.

    Only returns an address when the host name resolves to BOTH an IPv6 and an
    IPv4 address: that is the configuration where libpq may waste a full
    connect timeout on the IPv6 one. Literal addresses, socket directories,
    multi-host lists and IPv4-only names are left to libpq untouched. Results
    are cached per host for the session.
    """
    if not host or host.startswith('/') or ',' in host:
        return None
    if host in _HOSTADDR_CACHE:
        return _HOSTADDR_CACHE[host]

    result = None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except (socket.gaierror, OSError, UnicodeError) as e:
            logger.debug(f"getaddrinfo({host}) failed: {e}")
            infos = []
        ipv4 = [info[4][0] for info in infos if info[0] == socket.AF_INET]
        ipv6 = [info[4][0] for info in infos if info[0] == socket.AF_INET6]
        if ipv4 and ipv6:
            logger.info(f"PostgreSQL host '{host}' resolves to IPv6 {ipv6[0]} and IPv4 {ipv4[0]}: connecting through IPv4 first")
            result = ipv4[0]

    _HOSTADDR_CACHE[host] = result
    return result


def connect_kwargs_from_uri(source_uri, user: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Return the ``psycopg2.connect`` keywords of a PostgreSQL ``QgsDataSourceUri``.

    2026-11-12: the ``service`` of a layer read through ``pg_service.conf`` was
    left out, so libpq opened its defaults (localhost, the OS user): no
    connection, or another database. libpq fills from the service only the
    keywords not given, and an empty one counts as given (psycopg2 drops only
    ``None``): empty values are left out. The rest follows
    ``QgsDataSourceUri::connectionInfo()``: with a service, neither host nor
    port (the service's); a password only with a user; no ``sslmode=prefer``
    (the default of QGIS and of libpq, it would hide the service's own).

    Args:
        source_uri: QgsDataSourceUri of the layer
        user, password: Credentials of an authentication configuration, which
            replace the URI's when not empty (an empty user name, as a PKI or
            OAuth2 configuration gives, keeps the URI's, as QGIS does)

    Returns:
        Keywords for :func:`pg_connect_with_fallback`
    """
    ssl_mode = source_uri.sslMode()
    service = source_uri.service()
    user = user or source_uri.username()
    kwargs = {
        'service': service,
        'host': None if service else source_uri.host(),
        'port': None if service else source_uri.port(),
        'dbname': source_uri.database(),
        'user': user,
        'password': (password or source_uri.password()) if user else None,
        'sslmode': source_uri.encodeSslMode(ssl_mode) if ssl_mode is not None else None,
    }
    if kwargs['sslmode'] == 'prefer':
        kwargs['sslmode'] = None
    return {key: value for key, value in kwargs.items() if value is not None and value != ''}


def connection_identity(source_uri, authcfg: Optional[str] = None) -> tuple:
    """
    Return a hashable key of the database and identity a layer connects to, without password.

    2026-11-12: a cache keyed on ``host:port:database`` gave every layer read
    through a pg_service.conf service the key ``"::"``: the result of the
    first one was used for the layers of another service.
    """
    kwargs = connect_kwargs_from_uri(source_uri)
    kwargs.pop('password', None)
    return (authcfg or '',) + tuple(sorted(kwargs.items()))


def build_connect_attempts(connect_kwargs: Dict[str, Any]):
    """Return the ordered list of ``(label, kwargs)`` attempts for :func:`pg_connect_with_fallback`."""
    if connect_kwargs.get('service'):
        # 2026-11-12: the host is in pg_service.conf (no hostaddr to resolve) and a
        # forced gssencmode=disable would override the service's own (GSS encryption
        # required there dropped without a word): one attempt, only bounded in time
        service = dict(connect_kwargs)
        service.setdefault('connect_timeout', PLAIN_CONNECT_TIMEOUT_SECONDS)
        return [('service', service)]

    fast = dict(connect_kwargs)
    fast.setdefault('connect_timeout', FAST_CONNECT_TIMEOUT_SECONDS)
    fast.setdefault('gssencmode', 'disable')
    hostaddr = resolve_pg_hostaddr(fast.get('host'))
    if hostaddr and 'hostaddr' not in fast:
        fast['hostaddr'] = hostaddr

    plain = dict(connect_kwargs)
    plain.setdefault('connect_timeout', PLAIN_CONNECT_TIMEOUT_SECONDS)

    attempts = [('fast', fast)]
    if plain != fast:
        attempts.append(('plain', plain))
    return attempts


def pg_connect_with_fallback(connect_kwargs: Dict[str, Any], log_label: str = ''):
    """
    Open a psycopg2 connection: fast attempt first, plain parameters as fallback.

    Args:
        connect_kwargs: psycopg2.connect keyword arguments (host, port, dbname
            or database, user, password, sslmode, ...)
        log_label: Short context for the log line (layer or pool name)

    Returns:
        An open psycopg2 connection.

    Raises:
        The last exception when every attempt failed.
    """
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")

    last_error: Optional[Exception] = None
    for label, kwargs in build_connect_attempts(connect_kwargs):
        started = time.perf_counter()
        try:
            connection = psycopg2.connect(**kwargs)
        except Exception as e:  # psycopg2.OperationalError, invalid option on old libpq, ...
            last_error = e
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            logger.warning(f"PostgreSQL connect ({label}) failed after {elapsed_ms:.0f} ms: {e}")
            continue
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        suffix = f", {log_label}" if log_label else ""
        logger.info(
            f"⏱ pg_layer_connect: {elapsed_ms:.0f} ms ({label}, service={kwargs.get('service', '-')}, "
            f"host={kwargs.get('host')}, "
            f"hostaddr={kwargs.get('hostaddr', '-')}, gssencmode={kwargs.get('gssencmode', 'prefer')}{suffix})"
        )
        return connection

    assert last_error is not None  # nosec B101 - loop always runs at least once
    raise last_error


__all__ = [
    'FAST_CONNECT_TIMEOUT_SECONDS',
    'PLAIN_CONNECT_TIMEOUT_SECONDS',
    'build_connect_attempts',
    'clear_hostaddr_cache',
    'connect_kwargs_from_uri',
    'connection_identity',
    'pg_connect_with_fallback',
    'resolve_pg_hostaddr',
]
