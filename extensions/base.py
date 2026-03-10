# -*- coding: utf-8 -*-
"""
Base Extension Class for FilterMate Extension System.

All FilterMate extensions must inherit from BaseExtension and implement
the required lifecycle methods. Extensions are optional modules that
add functionality without modifying the core plugin.

Lifecycle:
    1. __init__()          - Extension instantiated (no QGIS deps yet)
    2. check_dependencies() - Verify required packages are available
    3. initialize(iface)   - Set up services, adapters, register actions
    4. create_ui(toolbar)  - Add toolbar buttons and menu entries
    5. teardown()          - Cleanup on plugin unload

Thread safety: Extensions run on the main thread unless they use QgsTask.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger('FilterMate.Extensions')


class ExtensionState(Enum):
    """Extension lifecycle state."""
    UNLOADED = "unloaded"
    DEPENDENCIES_CHECKED = "dependencies_checked"
    INITIALIZED = "initialized"
    UI_CREATED = "ui_created"
    ERROR = "error"
    TORN_DOWN = "torn_down"


@dataclass(frozen=True)
class ExtensionMetadata:
    """Metadata describing an extension."""
    id: str
    name: str
    version: str
    description: str
    author: str = ""
    min_qgis_version: str = "3.28"
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    icon_name: str = ""


class BaseExtension(ABC):
    """
    Abstract base class for FilterMate extensions.

    Extensions add optional functionality to FilterMate without
    modifying core code. They follow the hexagonal architecture:
    - Services go in the extension's own namespace
    - Ports/adapters follow the same pattern as core FilterMate
    - UI integrates via toolbar actions and dialogs

    Subclasses must implement:
        - metadata (property)
        - check_dependencies()
        - initialize(iface)
        - teardown()

    Optional overrides:
        - create_ui(toolbar, menu)
        - get_service(name)
        - on_project_loaded()
        - on_project_closed()
    """

    def __init__(self):
        self._state = ExtensionState.UNLOADED
        self._error_message: Optional[str] = None
        self._services: Dict[str, Any] = {}
        self._actions: list = []

    @property
    @abstractmethod
    def metadata(self) -> ExtensionMetadata:
        """Return extension metadata."""
        ...

    @property
    def state(self) -> ExtensionState:
        """Current extension state."""
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        """Error message if state is ERROR."""
        return self._error_message

    def is_available(self) -> bool:
        """Check if extension dependencies are met and it can be used."""
        if self._state == ExtensionState.UNLOADED:
            try:
                available = self.check_dependencies()
                if available:
                    self._state = ExtensionState.DEPENDENCIES_CHECKED
                return available
            except Exception as e:
                self._state = ExtensionState.ERROR
                self._error_message = str(e)
                return False
        return self._state not in (ExtensionState.ERROR, ExtensionState.TORN_DOWN)

    @abstractmethod
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are available.

        Returns True if all required packages can be imported.
        Should NOT raise exceptions — return False instead.
        """
        ...

    @abstractmethod
    def initialize(self, iface: Any) -> None:
        """
        Initialize extension services and adapters.

        Called after check_dependencies() returns True.
        Set up services, create adapters, register with DI container.

        Args:
            iface: QGIS interface instance
        """
        ...

    def create_ui(self, toolbar: Any, menu_name: str) -> List[Any]:
        """
        Create UI elements (toolbar buttons, menu entries).

        Override to add toolbar actions. Return list of QActions created.

        Args:
            toolbar: QGIS toolbar to add actions to
            menu_name: Menu name for menu entries

        Returns:
            List of QAction instances created
        """
        return []

    @abstractmethod
    def teardown(self) -> None:
        """
        Cleanup extension resources.

        Called when FilterMate plugin is unloaded.
        Must release all resources, disconnect signals, remove UI elements.
        """
        ...

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a named service from this extension.

        Args:
            name: Service name (e.g., 'push', 'credentials', 'adapter')

        Returns:
            Service instance or None if not found
        """
        return self._services.get(name)

    def register_service(self, name: str, service: Any) -> None:
        """Register a service by name."""
        self._services[name] = service

    def on_project_loaded(self) -> None:
        """Called when a QGIS project is loaded. Override if needed."""
        pass

    def on_project_closed(self) -> None:
        """Called when a QGIS project is closed. Override if needed."""
        pass

    def _set_state(self, state: ExtensionState) -> None:
        """Update extension state."""
        self._state = state
        logger.debug(
            "Extension '%s' state: %s", self.metadata.id, state.value
        )

    def _set_error(self, message: str) -> None:
        """Set extension to error state."""
        self._state = ExtensionState.ERROR
        self._error_message = message
        logger.error(
            "Extension '%s' error: %s", self.metadata.id, message
        )
