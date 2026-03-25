# -*- coding: utf-8 -*-
"""
Tests for the FilterMate extension registry and base extension class.
"""

from unittest.mock import MagicMock, patch

import pytest

from filter_mate.extensions.base import (
    BaseExtension,
    ExtensionMetadata,
    ExtensionState,
)
from filter_mate.extensions.registry import (
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
