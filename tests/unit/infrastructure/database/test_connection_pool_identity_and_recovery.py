"""Pool identity, ownership and recovery after a database outage (audit F4/F5)."""
import importlib.util
import sys
import threading
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
DB = Path(__file__).resolve().parents[4] / 'infrastructure' / 'database'
PACKAGE = 'fm_pool_recovery_test'


def _load():
    if PACKAGE + '.connection_pool' in sys.modules:
        return sys.modules[PACKAGE + '.connection_pool']
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(DB)]
    sys.modules[PACKAGE] = package
    support = types.ModuleType(PACKAGE + '.postgresql_support')
    support.POSTGRESQL_AVAILABLE = True
    support.psycopg2 = None
    sys.modules[support.__name__] = support
    spec = importlib.util.spec_from_file_location(PACKAGE + '.connection_pool', DB / 'connection_pool.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Connection:
    def __init__(self, user):
        self.user, self.closed = user, False

    def close(self):
        self.closed = True

    def rollback(self):
        pass

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql):
        assert sql == 'SELECT 1'


@pytest.fixture
def pools(monkeypatch):
    module = _load()
    made = []

    def connect(kwargs, label):
        connection = Connection(kwargs['user'])
        made.append(connection)
        return connection

    monkeypatch.setattr(module, 'pg_connect_with_fallback', connect)
    original = module.PostgreSQLConnectionPool

    class Pool(original):
        def __init__(self, **kwargs):
            super().__init__(**kwargs, min_connections=1, max_connections=2, enable_health_check=False)

    monkeypatch.setattr(module, 'PostgreSQLConnectionPool', Pool)
    manager = object.__new__(module.PostgreSQLPoolManager)
    manager._initialized = False
    manager.__init__()
    yield module, manager, made
    manager.close_all_pools()


def test_accounts_tls_and_rotated_passwords_have_distinct_pools(pools):
    _, manager, _ = pools
    first = manager.get_pool('db', '5432', 'gis', 'admin', 'old-secret', 'disable')
    same = manager.get_pool('db', '5432', 'gis', 'admin', 'old-secret', 'disable')
    reader = manager.get_pool('db', '5432', 'gis', 'reader', 'old-secret', 'disable')
    tls = manager.get_pool('db', '5432', 'gis', 'admin', 'old-secret', 'verify-full')
    rotated = manager.get_pool('db', '5432', 'gis', 'admin', 'new-secret', 'disable')
    assert first is same
    assert len({id(pool) for pool in (first, reader, tls, rotated)}) == 4
    assert all('secret' not in key for key in manager._pools)
    with pytest.raises(ValueError, match='Credentials required'):
        manager.get_pool('db', '5432', 'gis')


def test_connections_are_returned_to_their_exact_owner(pools):
    _, manager, _ = pools
    admin = manager.get_connection('db', '5432', 'gis', 'admin', 'a')
    reader = manager.get_connection('db', '5432', 'gis', 'reader', 'b')
    manager.release_connection(reader, 'db', '5432', 'gis')
    manager.release_connection(admin, 'db', '5432', 'gis')
    assert manager.get_connection('db', '5432', 'gis', 'reader', 'b') is reader
    assert manager.get_connection('db', '5432', 'gis', 'admin', 'a') is admin
    manager.release_connection(admin, 'db', '5432', 'gis')
    manager.release_connection(reader, 'db', '5432', 'gis')
    assert not manager._borrowed


def test_missing_identity_never_inherits_the_only_existing_accounts_credentials(pools):
    _, manager, _ = pools
    manager.get_pool('db', '5432', 'gis', 'admin', 'a', 'disable')
    with pytest.raises(ValueError, match='Credentials required'):
        manager.get_connection('db', '5432', 'gis')


def test_endpoint_close_closes_every_identity_and_late_returns(pools):
    _, manager, _ = pools
    admin = manager.get_connection('db', '5432', 'gis', 'admin', 'a')
    reader = manager.get_connection('db', '5432', 'gis', 'reader', 'b')
    manager.close_pool('db', '5432', 'gis')
    assert not manager._pools
    manager.release_connection(admin, 'db', '5432', 'gis')
    manager.release_connection(reader, 'db', '5432', 'gis')
    assert admin.closed and reader.closed and not manager._borrowed


def test_unknown_connection_is_closed_instead_of_entering_a_different_pool(pools):
    _, manager, _ = pools
    manager.get_pool('db', '5432', 'gis', 'reader', 'b')
    unknown = Connection('admin')
    manager.release_connection(unknown, 'db', '5432', 'gis')
    assert unknown.closed


def test_health_refill_stops_after_the_first_failed_connection(pools, monkeypatch):
    module, manager, _ = pools
    pool = manager.get_pool('db', '5432', 'gis', 'reader', 'b')
    pool._close_connection(pool._pool.get_nowait())
    attempts = []

    def unavailable(kwargs, label):
        attempts.append(label)
        raise OSError('database unavailable')

    monkeypatch.setattr(module, 'pg_connect_with_fallback', unavailable)
    pool._perform_health_check()
    assert len(attempts) == 1
    assert pool._pending_connections == 0 and pool._active_connections == 0
    pool.shutdown()  # must not wait on a lock retained by recovery


def test_network_connection_does_not_hold_lock_and_shutdown_stays_responsive(pools, monkeypatch):
    module, manager, _ = pools
    pool = manager.get_pool('db', '5432', 'gis', 'reader', 'b')
    pool._close_connection(pool._pool.get_nowait())
    entered, resume = threading.Event(), threading.Event()
    result = []

    def slow(kwargs, label):
        entered.set()
        assert resume.wait(2)
        connection = Connection(kwargs['user'])
        result.append(connection)
        return connection

    monkeypatch.setattr(module, 'pg_connect_with_fallback', slow)
    worker = threading.Thread(target=pool._perform_health_check)
    worker.start()
    try:
        assert entered.wait(2)
        assert pool._lock.acquire(timeout=0.2)
        pool._lock.release()
        pool.shutdown()
    finally:
        resume.set()
        worker.join(2)
    assert not worker.is_alive()
    assert result[0].closed and pool._active_connections == 0


def test_concurrent_connection_attempts_reserve_the_maximum_capacity(pools, monkeypatch):
    module, manager, _ = pools
    pool = manager.get_pool('db', '5432', 'gis', 'reader', 'b')
    entered, resume = threading.Event(), threading.Event()
    result = []

    def slow(kwargs, label):
        entered.set()
        assert resume.wait(2)
        return Connection(kwargs['user'])

    monkeypatch.setattr(module, 'pg_connect_with_fallback', slow)
    worker = threading.Thread(target=lambda: result.append(pool._create_connection()))
    worker.start()
    try:
        assert entered.wait(2)
        # One idle connection and one opening: no third connection is allowed.
        assert pool._create_connection() is None
    finally:
        resume.set()
        worker.join(2)
    assert len(result) == 1 and pool._active_connections == 2
    pool.release_connection(result[0])
