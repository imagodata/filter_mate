# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: psycopg2 connections open with a fast attempt (IPv4 hostaddr
when the host is dual-stack, gssencmode=disable, short timeout) and fall back
to the caller's plain parameters.

The module is loaded in a private package so its ``.postgresql_support``
import resolves without the shared filter_mate aliases; psycopg2 itself is
replaced by a recording fake.
"""

import importlib.util
import socket
import sys
import types
from pathlib import Path

import pytest

_DB_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "database"
_PKG = "fmtest_pg_connect_pkg"


def _load():
    name = f"{_PKG}.pg_connect"
    if name in sys.modules:
        return sys.modules[name]
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(_DB_DIR)]
    pkg.__package__ = _PKG
    sys.modules[_PKG] = pkg
    support = types.ModuleType(f"{_PKG}.postgresql_support")
    support.psycopg2 = None
    support.POSTGRESQL_AVAILABLE = False
    support.PSYCOPG2_AVAILABLE = False
    sys.modules[support.__name__] = support
    spec = importlib.util.spec_from_file_location(name, _DB_DIR / "pg_connect.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakePsycopg2:
    """Records connect() calls; fails the attempts whose index is in ``fail``."""

    def __init__(self, fail=()):
        self.calls = []
        self.fail = set(fail)

    def connect(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) - 1 in self.fail:
            raise RuntimeError(f"attempt {len(self.calls)} refused")
        return {"connected_with": kwargs}


def _addrinfo(*families_and_addrs):
    return [(family, socket.SOCK_STREAM, 6, '', (addr, 5432)) for family, addr in families_and_addrs]


@pytest.fixture
def pg(monkeypatch):
    module = _load()
    module.clear_hostaddr_cache()
    yield module
    module.clear_hostaddr_cache()


@pytest.mark.unit
class TestResolveHostaddr:

    def test_dual_stack_host_returns_ipv4(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo",
                            lambda *a, **k: _addrinfo((socket.AF_INET6, "2001:db8::1"), (socket.AF_INET, "192.0.2.10")))
        assert pg.resolve_pg_hostaddr("db.example.org") == "192.0.2.10"

    def test_ipv4_only_host_is_left_to_libpq(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _addrinfo((socket.AF_INET, "192.0.2.10")))
        assert pg.resolve_pg_hostaddr("db.example.org") is None

    def test_literals_sockets_and_lists_are_untouched(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not resolve")))
        assert pg.resolve_pg_hostaddr("192.0.2.10") is None
        assert pg.resolve_pg_hostaddr("::1") is None
        assert pg.resolve_pg_hostaddr("/var/run/postgresql") is None
        assert pg.resolve_pg_hostaddr("a.example.org,b.example.org") is None
        assert pg.resolve_pg_hostaddr("") is None
        assert pg.resolve_pg_hostaddr(None) is None

    def test_resolution_failure_is_cached_as_none(self, pg, monkeypatch):
        calls = []

        def failing(*a, **k):
            calls.append(a)
            raise socket.gaierror("no such host")

        monkeypatch.setattr(socket, "getaddrinfo", failing)
        assert pg.resolve_pg_hostaddr("nope.example.org") is None
        assert pg.resolve_pg_hostaddr("nope.example.org") is None
        assert len(calls) == 1


@pytest.mark.unit
class TestConnectWithFallback:

    def test_fast_attempt_parameters(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo",
                            lambda *a, **k: _addrinfo((socket.AF_INET6, "2001:db8::1"), (socket.AF_INET, "192.0.2.10")))
        fake = FakePsycopg2()
        monkeypatch.setattr(pg, "psycopg2", fake)

        conn = pg.pg_connect_with_fallback({"host": "db.example.org", "port": "5432", "database": "bd", "user": "u", "password": "p"}, "layer 'commune'")

        assert conn["connected_with"] is fake.calls[0]
        assert len(fake.calls) == 1
        first = fake.calls[0]
        assert first["hostaddr"] == "192.0.2.10"
        assert first["host"] == "db.example.org"          # kept for SSL / auth
        assert first["gssencmode"] == "disable"
        assert first["connect_timeout"] == pg.FAST_CONNECT_TIMEOUT_SECONDS

    def test_falls_back_to_plain_parameters(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo",
                            lambda *a, **k: _addrinfo((socket.AF_INET6, "2001:db8::1"), (socket.AF_INET, "192.0.2.10")))
        fake = FakePsycopg2(fail={0})
        monkeypatch.setattr(pg, "psycopg2", fake)

        conn = pg.pg_connect_with_fallback({"host": "db.example.org", "database": "bd"})

        assert len(fake.calls) == 2
        plain = fake.calls[1]
        assert "hostaddr" not in plain and "gssencmode" not in plain
        assert plain["connect_timeout"] == pg.PLAIN_CONNECT_TIMEOUT_SECONDS
        assert conn["connected_with"] is plain

    def test_caller_options_win(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _addrinfo((socket.AF_INET, "192.0.2.10")))
        fake = FakePsycopg2()
        monkeypatch.setattr(pg, "psycopg2", fake)

        pg.pg_connect_with_fallback({"host": "db.example.org", "connect_timeout": 2, "gssencmode": "require"})

        assert fake.calls[0]["connect_timeout"] == 2
        assert fake.calls[0]["gssencmode"] == "require"
        assert "hostaddr" not in fake.calls[0]
        # fast and plain are identical here: a single attempt is made
        assert len(fake.calls) == 1

    def test_every_attempt_failing_raises_last_error(self, pg, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _addrinfo((socket.AF_INET, "192.0.2.10")))
        fake = FakePsycopg2(fail={0, 1})
        monkeypatch.setattr(pg, "psycopg2", fake)
        with pytest.raises(RuntimeError, match="refused"):
            pg.pg_connect_with_fallback({"host": "db.example.org"})

    def test_without_psycopg2(self, pg, monkeypatch):
        monkeypatch.setattr(pg, "psycopg2", None)
        with pytest.raises(RuntimeError, match="psycopg2"):
            pg.pg_connect_with_fallback({"host": "x"})
