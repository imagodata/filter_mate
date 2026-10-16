# -*- coding: utf-8 -*-
"""
ConfigMigration.auto_migrate_if_needed reported a migration on every start
((True, []) with nothing migrated): FilterMate.initGui then showed
"Configuration updated to latest version" each time QGIS started.
"""
import pytest

from infrastructure.config.config_migration import ConfigMigration


@pytest.mark.unit
class TestAutoMigrateIfNeeded:

    def test_nothing_to_migrate_is_not_reported_as_a_migration(self):
        assert ConfigMigration().auto_migrate_if_needed() == (False, [])

    def test_a_migration_that_ran_is_reported(self, monkeypatch):
        migrator = ConfigMigration()
        monkeypatch.setattr(migrator, "_needs_migration", lambda: True)

        assert migrator.auto_migrate_if_needed() == (True, [])

    def test_a_failed_migration_is_not_reported_as_done(self, monkeypatch):
        migrator = ConfigMigration()
        monkeypatch.setattr(migrator, "_needs_migration", lambda: True)
        monkeypatch.setattr(migrator, "_migrate_config", lambda: (_ for _ in ()).throw(OSError("read-only")))

        performed, warnings = migrator.auto_migrate_if_needed()

        assert performed is False
        assert warnings == ["Migration error: read-only"]
