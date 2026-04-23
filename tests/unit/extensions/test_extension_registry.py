# -*- coding: utf-8 -*-
"""
Tests for the FilterMate extension registry and base extension class.
"""

from unittest.mock import MagicMock, patch

import pytest

from extensions.base import (
    BaseExtension,
    ExtensionMetadata,
    ExtensionState,
)
from extensions.registry import (
    ExtensionRegistry,
    reset_extension_registry,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

class DummyExtension(BaseExtension):
    """Minimal extension for testing."""

    def __init__(self, available=True):
        super().__init__()
        self._available = available

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id="dummy",
            name="Dummy Extension",
            version="1.0.0",
            description="Test extension",
        )

    def check_dependencies(self) -> bool:
        return self._available

    def initialize(self, iface) -> None:
        self.register_service('test', {'initialized': True})

    def create_ui(self, toolbar, menu_name):
        action = MagicMock()
        self._actions.append(action)
        return [action]

    def teardown(self) -> None:
        self._services.clear()


class FailingExtension(BaseExtension):
    """Extension that fails during initialization."""

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id="failing",
            name="Failing Extension",
            version="0.1.0",
            description="Always fails",
        )

    def check_dependencies(self) -> bool:
        return True

    def initialize(self, iface) -> None:
        raise RuntimeError("Intentional init failure")

    def teardown(self) -> None:
        pass


class UnavailableExtension(BaseExtension):
    """Extension whose dependencies are not met."""

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id="unavailable",
            name="Unavailable Extension",
            version="1.0.0",
            description="Missing deps",
            dependencies=["nonexistent_package"],
        )

    def check_dependencies(self) -> bool:
        return False

    def initialize(self, iface) -> None:
        pass

    def teardown(self) -> None:
        pass


@pytest.fixture
def registry():
    """Fresh extension registry for each test."""
    reg = ExtensionRegistry()
    yield reg
    reg.teardown_all()


@pytest.fixture(autouse=True)
def clean_global_registry():
    """Reset global registry between tests."""
    yield
    reset_extension_registry()


# ---------------------------------------------------------------------------
# BaseExtension tests
# ---------------------------------------------------------------------------

class TestBaseExtension:
    """Tests for BaseExtension lifecycle."""

    def test_initial_state_is_unloaded(self):
        ext = DummyExtension()
        assert ext.state == ExtensionState.UNLOADED

    def test_is_available_checks_dependencies(self):
        ext = DummyExtension(available=True)
        assert ext.is_available() is True
        assert ext.state == ExtensionState.DEPENDENCIES_CHECKED

    def test_is_available_returns_false_when_deps_missing(self):
        ext = DummyExtension(available=False)
        assert ext.is_available() is False

    def test_is_available_sets_error_on_exception(self):
        ext = DummyExtension()
        ext.check_dependencies = MagicMock(side_effect=ImportError("boom"))
        assert ext.is_available() is False
        assert ext.state == ExtensionState.ERROR
        assert "boom" in ext.error_message

    def test_register_and_get_service(self):
        ext = DummyExtension()
        ext.register_service('foo', {'bar': 42})
        assert ext.get_service('foo') == {'bar': 42}
        assert ext.get_service('nonexistent') is None

    def test_metadata_returns_expected_values(self):
        ext = DummyExtension()
        m = ext.metadata
        assert m.id == "dummy"
        assert m.name == "Dummy Extension"
        assert m.version == "1.0.0"


# ---------------------------------------------------------------------------
# ExtensionRegistry tests
# ---------------------------------------------------------------------------

class TestExtensionRegistry:
    """Tests for ExtensionRegistry."""

    def test_register_extension(self, registry):
        ext = DummyExtension()
        registry.register(ext)
        assert registry.get_extension("dummy") is ext

    def test_get_nonexistent_extension_returns_none(self, registry):
        assert registry.get_extension("nonexistent") is None

    def test_get_available_extensions(self, registry):
        available = DummyExtension(available=True)
        unavailable = UnavailableExtension()

        registry.register(available)
        registry.register(unavailable)

        result = registry.get_available_extensions()
        assert available in result
        assert unavailable not in result

    def test_initialize_all(self, registry):
        ext = DummyExtension()
        registry.register(ext)

        iface = MagicMock()
        results = registry.initialize_all(iface)

        assert results["dummy"] is True
        assert ext.state == ExtensionState.INITIALIZED
        assert ext.get_service('test') == {'initialized': True}

    def test_initialize_unavailable_extension_returns_false(self, registry):
        ext = UnavailableExtension()
        registry.register(ext)

        iface = MagicMock()
        results = registry.initialize_all(iface)

        assert results["unavailable"] is False

    def test_initialize_failing_extension_sets_error(self, registry):
        ext = FailingExtension()
        registry.register(ext)

        iface = MagicMock()
        results = registry.initialize_all(iface)

        assert results["failing"] is False
        assert ext.state == ExtensionState.ERROR
        assert "Intentional init failure" in ext.error_message

    def test_create_all_ui(self, registry):
        ext = DummyExtension()
        registry.register(ext)
        registry.initialize_all(MagicMock())

        toolbar = MagicMock()
        ui_results = registry.create_all_ui(toolbar, "TestMenu")

        assert "dummy" in ui_results
        assert len(ui_results["dummy"]) == 1
        assert ext.state == ExtensionState.UI_CREATED

    def test_teardown_all(self, registry):
        ext = DummyExtension()
        registry.register(ext)
        registry.initialize_all(MagicMock())

        registry.teardown_all()

        assert ext.state == ExtensionState.TORN_DOWN
        assert registry.get_extension("dummy") is None

    def test_teardown_reverse_order(self, registry):
        """Extensions should be torn down in reverse load order."""
        teardown_order = []

        class OrderedExt(DummyExtension):
            def __init__(self, ext_id):
                super().__init__()
                self._ext_id = ext_id

            @property
            def metadata(self):
                return ExtensionMetadata(
                    id=self._ext_id, name=self._ext_id,
                    version="1.0", description=""
                )

            def teardown(self):
                teardown_order.append(self._ext_id)

        ext_a = OrderedExt("a")
        ext_b = OrderedExt("b")
        ext_c = OrderedExt("c")

        registry.register(ext_a)
        registry.register(ext_b)
        registry.register(ext_c)
        registry.initialize_all(MagicMock())

        registry.teardown_all()
        assert teardown_order == ["c", "b", "a"]

    def test_notify_project_loaded(self, registry):
        ext = DummyExtension()
        ext.on_project_loaded = MagicMock()
        registry.register(ext)
        registry.initialize_all(MagicMock())

        registry.notify_project_loaded()
        ext.on_project_loaded.assert_called_once()

    def test_notify_project_closed(self, registry):
        ext = DummyExtension()
        ext.on_project_closed = MagicMock()
        registry.register(ext)
        registry.initialize_all(MagicMock())

        registry.notify_project_closed()
        ext.on_project_closed.assert_called_once()

    def test_status_summary(self, registry):
        ext = DummyExtension()
        registry.register(ext)
        registry.initialize_all(MagicMock())

        summary = registry.get_status_summary()
        assert "dummy" in summary
        assert summary["dummy"]["state"] == "initialized"
        assert summary["dummy"]["available"] is True
        assert summary["dummy"]["version"] == "1.0.0"

    def test_initialize_continues_after_failure(self, registry):
        """One extension crashing during init must not prevent others from initializing."""
        class OkExt(DummyExtension):
            @property
            def metadata(self):
                return ExtensionMetadata(
                    id="ok", name="Ok", version="1.0", description=""
                )

        failing = FailingExtension()
        ok = OkExt()

        registry.register(failing)
        registry.register(ok)

        results = registry.initialize_all(MagicMock())

        assert results["failing"] is False
        assert results["ok"] is True
        assert failing.state == ExtensionState.ERROR
        assert ok.state == ExtensionState.INITIALIZED

    def test_register_duplicate_id_replaces_and_keeps_order(self, registry):
        """Registering a second extension with the same ID replaces in place."""
        ext_a = DummyExtension()
        ext_b = DummyExtension()

        registry.register(ext_a)
        registry.register(ext_b)

        assert registry.get_extension("dummy") is ext_b
        # load order should not duplicate the ID
        assert registry._load_order.count("dummy") == 1

    def test_teardown_skips_errored_extensions(self, registry):
        """Extensions in ERROR state must not have teardown() called."""
        teardown_calls = []

        class TrackingFailing(FailingExtension):
            def teardown(self):
                teardown_calls.append("failing")

        class TrackingOk(DummyExtension):
            @property
            def metadata(self):
                return ExtensionMetadata(
                    id="ok", name="Ok", version="1.0", description=""
                )
            def teardown(self):
                teardown_calls.append("ok")
                super().teardown()

        failing = TrackingFailing()
        ok = TrackingOk()
        registry.register(failing)
        registry.register(ok)
        registry.initialize_all(MagicMock())

        registry.teardown_all()

        # Only the successfully-initialized extension gets torn down
        assert teardown_calls == ["ok"]
        assert failing.state == ExtensionState.ERROR  # unchanged

    def test_teardown_swallows_exception_in_one_extension(self, registry):
        """An exception in one teardown() must not prevent others from running."""
        teardown_calls = []

        class RaisingTeardown(DummyExtension):
            @property
            def metadata(self):
                return ExtensionMetadata(
                    id="raiser", name="Raiser", version="1.0", description=""
                )
            def teardown(self):
                teardown_calls.append("raiser")
                raise RuntimeError("teardown boom")

        class OkTeardown(DummyExtension):
            @property
            def metadata(self):
                return ExtensionMetadata(
                    id="survivor", name="Survivor", version="1.0", description=""
                )
            def teardown(self):
                teardown_calls.append("survivor")

        raiser = RaisingTeardown()
        survivor = OkTeardown()
        registry.register(raiser)
        registry.register(survivor)
        registry.initialize_all(MagicMock())

        # Must not propagate — teardown order is reverse, so survivor first then raiser
        registry.teardown_all()
        assert teardown_calls == ["survivor", "raiser"]

    def test_create_ui_skips_non_initialized_extensions(self, registry):
        """Extensions not in INITIALIZED state must be skipped by create_all_ui."""
        failing = FailingExtension()
        ok = DummyExtension()

        registry.register(failing)
        registry.register(ok)
        registry.initialize_all(MagicMock())

        ui_results = registry.create_all_ui(MagicMock(), "TestMenu")

        assert "dummy" in ui_results
        # failing extension is in ERROR state, so create_ui wasn't called and no entry was recorded
        assert "failing" not in ui_results

    def test_teardown_all_after_unavailable_extension(self, registry):
        """Extensions skipped at init (unavailable) must not raise on teardown."""
        unavailable = UnavailableExtension()
        ok = DummyExtension()

        registry.register(unavailable)
        registry.register(ok)
        registry.initialize_all(MagicMock())

        # Should not raise
        registry.teardown_all()
        assert ok.state == ExtensionState.TORN_DOWN


# ---------------------------------------------------------------------------
# Harmonized config API (BaseExtension.config_schema / get_config / set_config)
# ---------------------------------------------------------------------------


class SchemaExtension(BaseExtension):
    """Extension that declares a schema for config API tests."""

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id="schema_ext",
            name="Schema Ext",
            version="1.0.0",
            description="Exposes a config schema",
        )

    def config_schema(self):
        return {
            "endpoint": {
                "value": "https://default.example/api",
                "description": "API endpoint",
            },
            "timeout": {"value": 30, "min": 1, "max": 300},
            "enabled_flag": {"value": True, "choices": [True, False]},
        }

    def check_dependencies(self) -> bool:
        return True

    def initialize(self, iface) -> None:
        pass

    def teardown(self) -> None:
        pass


class TestConfigAPI:
    """Tests for the harmonized BaseExtension config surface."""

    @pytest.fixture
    def in_memory_config(self, tmp_path, monkeypatch):
        """Wire ENV_VARS to an in-memory CONFIG_DATA + tmp config.json."""
        from filter_mate.config import config as fm_config

        cfg_path = tmp_path / "config.json"
        cfg_data = {"EXTENSIONS": {}}
        original = dict(fm_config.ENV_VARS)
        fm_config.ENV_VARS["CONFIG_DATA"] = cfg_data
        fm_config.ENV_VARS["CONFIG_JSON_PATH"] = str(cfg_path)
        yield cfg_data, cfg_path
        fm_config.ENV_VARS.clear()
        fm_config.ENV_VARS.update(original)

    def test_full_schema_merges_common_keys(self):
        ext = SchemaExtension()
        schema = ext.full_config_schema()
        # Common keys injected automatically
        assert "enabled" in schema
        assert "dismiss_missing_deps_warning" in schema
        # Extension-specific keys preserved
        assert schema["endpoint"]["value"] == "https://default.example/api"
        assert schema["timeout"]["min"] == 1

    def test_get_config_falls_back_to_schema_default(self, in_memory_config):
        ext = SchemaExtension()
        # Key absent from CONFIG_DATA → schema default returned
        assert ext.get_config("endpoint") == "https://default.example/api"
        assert ext.get_config("timeout") == 30
        assert ext.is_enabled() is True
        assert ext.is_warning_dismissed() is False

    def test_set_config_persists_and_wraps(self, in_memory_config):
        cfg_data, cfg_path = in_memory_config
        ext = SchemaExtension()

        assert ext.set_config("endpoint", "https://custom.example/api") is True

        # In-memory update is wrapped ({"value": ..., "description": ...})
        stored = cfg_data["EXTENSIONS"]["schema_ext"]["endpoint"]
        assert isinstance(stored, dict)
        assert stored["value"] == "https://custom.example/api"
        assert stored["description"] == "API endpoint"

        # Persisted to disk
        import json
        on_disk = json.loads(cfg_path.read_text())
        assert on_disk["EXTENSIONS"]["schema_ext"]["endpoint"]["value"] == \
            "https://custom.example/api"

        # Round-trip through get_config
        assert ext.get_config("endpoint") == "https://custom.example/api"

    def test_set_enabled_and_dismiss_warning(self, in_memory_config):
        ext = SchemaExtension()
        assert ext.set_enabled(False) is True
        assert ext.is_enabled() is False
        assert ext.dismiss_warning() is True
        assert ext.is_warning_dismissed() is True

    def test_seed_default_config_inserts_missing_keys(self, in_memory_config):
        cfg_data, _ = in_memory_config
        ext = SchemaExtension()

        dirty = ext.seed_default_config()
        assert dirty is True

        seeded = cfg_data["EXTENSIONS"]["schema_ext"]
        for key in ("enabled", "dismiss_missing_deps_warning",
                    "endpoint", "timeout", "enabled_flag"):
            assert key in seeded
            assert "value" in seeded[key]

        # Idempotent — second call is a no-op
        dirty_again = ext.seed_default_config()
        assert dirty_again is False

    def test_seed_preserves_user_overrides(self, in_memory_config):
        cfg_data, _ = in_memory_config
        # User already customized the endpoint
        cfg_data["EXTENSIONS"]["schema_ext"] = {
            "endpoint": {"value": "https://user.example/api"},
        }

        ext = SchemaExtension()
        ext.seed_default_config()

        # User value preserved, missing keys added
        seeded = cfg_data["EXTENSIONS"]["schema_ext"]
        assert seeded["endpoint"]["value"] == "https://user.example/api"
        assert seeded["timeout"]["value"] == 30
        assert seeded["enabled"]["value"] is True

    def test_discover_extensions_auto_seeds(self, in_memory_config, registry):
        """Registry.discover_extensions() seeds schema keys on startup."""
        cfg_data, cfg_path = in_memory_config
        ext = SchemaExtension()
        registry.register(ext)

        # Simulate what discover_extensions does after loading a module
        if ext.seed_default_config():
            registry._persist_config()

        assert cfg_data["EXTENSIONS"]["schema_ext"]["endpoint"]["value"] == \
            "https://default.example/api"
        # Persisted
        import json
        on_disk = json.loads(cfg_path.read_text())
        assert on_disk["EXTENSIONS"]["schema_ext"]["timeout"]["value"] == 30
