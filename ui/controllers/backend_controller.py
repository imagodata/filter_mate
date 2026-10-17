"""
Backend Controller for FilterMate.

Manages the backend indicator widget and selection menu.
Extracted from filter_mate_dockwidget.py (lines 1612-1966, 2945-3100, 12503-12650).

Story: MIG-071
Phase: 6 - God Class DockWidget Migration
"""

from typing import TYPE_CHECKING, Optional, List, Tuple, Dict
import logging

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QMenu, QLabel
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsVectorLayer

from .base_controller import BaseController
from ...infrastructure.database.sql_utils import sanitize_sql_identifier

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget

logger = logging.getLogger(__name__)


# Backend display configuration - v4.0: Softer "mousse" colors
BACKEND_STYLES = {
    'postgresql': {
        'text': 'PostgreSQL',
        'color': 'white',
        'background': '#58d68d',  # Softer green
        'icon': '🐘',
        'tooltip': 'Backend: PostgreSQL (High Performance)'
    },
    'spatialite': {
        'text': 'Spatialite',
        'color': 'white',
        'background': '#bb8fce',  # Softer purple
        'icon': '💾',
        'tooltip': 'Backend: Spatialite (Good Performance)'
    },
    'spatialite_fallback': {
        'text': 'Spatialite*',
        'color': 'white',
        'background': '#a569bd',  # Softer dark purple
        'icon': '💾',
        'tooltip': 'Backend: Spatialite → OGR fallback\n(Complex geometry handled by OGR)'
    },
    'ogr': {
        'text': 'OGR',
        'color': 'white',
        'background': '#5dade2',  # Softer blue
        'icon': '📁',
        'tooltip': 'Backend: OGR (Universal)'
    },
    'ogr_fallback': {
        'text': 'OGR*',
        'color': 'white',
        'background': '#f0b27a',  # Softer orange
        'icon': '📁',
        'tooltip': 'Backend: OGR (Fallback - Connection unavailable)'
    },
    'postgresql_fallback': {
        'text': 'PostgreSQL*',
        'color': 'white',
        'background': '#45b39d',  # Softer teal green
        'icon': '🐘',
        'tooltip': 'Backend: PostgreSQL → OGR fallback'
    },
    'unknown': {
        'text': '...',
        'color': '#7f8c8d',
        'background': '#f4f6f6',  # Softer light gray
        'icon': '❓',
        'tooltip': 'Backend: Unknown'
    }
}


class BackendController(BaseController):
    """
    Controller for backend indicator management.

    Handles:
    - Backend indicator display and styling
    - Backend selection menu
    - Backend switching per layer
    - Optimization settings
    - PostgreSQL maintenance options

    Signals:
        backend_changed: Emitted when backend is switched
        reload_requested: Emitted when user wants to reload layers

    Example:
        controller = BackendController(dockwidget)
        controller.setup()

        # React to backend changes
        controller.backend_changed.connect(on_backend_changed)
    """

    backend_changed = pyqtSignal(str, str)  # (layer_id, backend_name)
    reload_requested = pyqtSignal()

    def __init__(self, dockwidget: 'FilterMateDockWidget') -> None:
        """
        Initialize the backend controller.

        Args:
            dockwidget: Main dockwidget reference
        """
        super().__init__(dockwidget)
        self._forced_backends: Dict[str, str] = {}
        self._current_provider_type: Optional[str] = None
        self._current_postgresql_available: Optional[bool] = None
        self._indicator_label: Optional[QLabel] = None
        self._initialized: bool = False
        # Optimization settings
        self._optimization_enabled: bool = True
        self._centroid_auto_enabled: bool = True
        self._optimization_ask_before: bool = True

    def _tr(self, text: str) -> str:
        """Translate text using dockwidget's tr() if available."""
        if self.dockwidget and hasattr(self.dockwidget, 'tr'):
            return self.dockwidget.tr(text)
        return text

    @property
    def forced_backends(self) -> Dict[str, str]:
        """Get dictionary of forced backends by layer ID."""
        return self._forced_backends

    def setup(self) -> None:
        """
        Setup backend indicator widget.

        Finds and configures the backend indicator label from dockwidget.
        """
        self._find_indicator_label()
        self._sync_with_dockwidget()
        self._initialized = True
        logger.debug("BackendController setup complete")

    def teardown(self) -> None:
        """Clean up resources."""
        self._forced_backends.clear()
        super().teardown()

    def on_tab_activated(self) -> None:
        """Handle tab activation."""
        super().on_tab_activated()
        # Refresh indicator for current layer
        if self.dockwidget.current_layer:
            self.update_for_layer(self.dockwidget.current_layer)

    def on_tab_deactivated(self) -> None:
        """Handle tab deactivation."""
        super().on_tab_deactivated()

    # === Public API ===

    def update_for_layer(
        self,
        layer: QgsVectorLayer,
        postgresql_connection_available: Optional[bool] = None,
        actual_backend: Optional[str] = None
    ) -> None:
        """
        Update indicator for current layer.

        Args:
            layer: Current QgsVectorLayer
            postgresql_connection_available: Whether PostgreSQL connection is available
            actual_backend: Forced backend name, if any
        """
        if not layer or not layer.isValid():
            self._update_indicator_display('unknown')
            return

        provider_type = layer.providerType()
        self._current_provider_type = provider_type
        self._current_postgresql_available = postgresql_connection_available

        # Determine actual backend type
        backend_type = self._detect_backend_for_layer(
            layer, postgresql_connection_available, actual_backend
        )

        # Check if forced
        is_forced = (actual_backend is not None) or (layer.id() in self._forced_backends)

        self._update_indicator_display(backend_type, is_forced, layer)

    def get_available_backends_for_layer(
        self,
        layer: QgsVectorLayer
    ) -> List[Tuple[str, str, str]]:
        """
        Get list of available backends for the given layer.

        Args:
            layer: QgsVectorLayer to check

        Returns:
            List of tuples: (backend_type, backend_name, backend_icon)
        """
        from ...adapters.backends import POSTGRESQL_AVAILABLE

        available = []
        provider_type = layer.providerType()

        # PostgreSQL backend (only for postgres layers with psycopg2 available)
        if provider_type == 'postgres':
            try:
                if POSTGRESQL_AVAILABLE:
                    available.append(('postgresql', 'PostgreSQL', '🐘'))
            except ImportError:
                pass

        # Spatialite backend (for spatialite layers and some OGR layers)
        if provider_type in ['spatialite', 'ogr']:
            source = layer.source()
            if 'gpkg' in source.lower() or 'sqlite' in source.lower() or provider_type == 'spatialite':
                available.append(('spatialite', 'Spatialite', '💾'))

        # OGR backend (always available as fallback)
        available.append(('ogr', 'OGR', '📁'))

        # Remove current backend to show only alternatives (keep at least one)
        if len(available) > 1:
            current_backend = self.get_current_backend(layer)
            available = [b for b in available if b[0] != current_backend]

        return available

    def get_current_backend(self, layer: QgsVectorLayer) -> str:
        """
        Get the current backend for a layer.

        Args:
            layer: Layer to check

        Returns:
            Backend type string ('postgresql', 'spatialite', 'ogr')
        """
        # Check forced backend first
        if layer.id() in self._forced_backends:
            return self._forced_backends[layer.id()]

        # Auto-detection
        return self._detect_backend_for_layer(layer, self._current_postgresql_available)

    def set_forced_backend(
        self,
        layer_id: str,
        backend_type: Optional[str]
    ) -> None:
        """
        Force a specific backend for a layer.

        Args:
            layer_id: Layer ID
            backend_type: Backend type to force, or None for auto
        """
        if backend_type is None:
            if layer_id in self._forced_backends:
                del self._forced_backends[layer_id]
                logger.debug(f"Removed forced backend for layer {layer_id}")
        else:
            self._forced_backends[layer_id] = backend_type
            logger.debug(f"Forced backend {backend_type} for layer {layer_id}")

        # Sync with dockwidget
        if hasattr(self.dockwidget, 'forced_backends'):
            self.dockwidget.forced_backends = self._forced_backends.copy()

        # Update indicator display if this is the current layer
        current_layer = self.dockwidget.current_layer
        if current_layer and current_layer.id() == layer_id:
            display_backend = backend_type if backend_type else self._detect_backend_for_layer(
                current_layer, self._current_postgresql_available
            )
            self._update_indicator_display(display_backend, is_forced=(backend_type is not None), layer=current_layer)

        self.backend_changed.emit(layer_id, backend_type or 'auto')

    def force_backend_for_all_layers(self, backend_type: str) -> int:
        """
        Force a specific backend for all layers in the project.

        Args:
            backend_type: Backend type to force

        Returns:
            Number of layers updated
        """
        from qgis.core import QgsProject

        project = QgsProject.instance()
        layers = project.mapLayers().values()

        count = 0
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.set_forced_backend(layer.id(), backend_type)
                count += 1

        logger.debug(f"Forced {backend_type} backend for {count} layers")
        return count

    def auto_select_optimal_backends(self) -> int:
        """
        Auto-select optimal backend for each layer based on characteristics.

        v4.0 Sprint 1: Full implementation migrated from dockwidget.

        Analyzes each layer's characteristics and sets the most appropriate backend:
        - PostgreSQL for large server-side datasets
        - Spatialite for SQLite/GeoPackage with > 5000 features
        - OGR for small datasets and file-based formats

        Returns:
            Number of layers optimized
        """
        from qgis.core import QgsProject

        project = QgsProject.instance()
        layers = project.mapLayers().values()

        optimized_count = 0
        skipped_count = 0
        backend_stats = {'postgresql': 0, 'spatialite': 0, 'ogr': 0, 'auto': 0}

        logger.info("=" * 60)
        logger.debug("AUTO-SELECTING OPTIMAL BACKENDS FOR ALL LAYERS")
        logger.info("=" * 60)

        for layer in layers:
            # Skip non-vector layers
            if not isinstance(layer, QgsVectorLayer):
                continue

            if not layer.isValid():
                skipped_count += 1
                continue

            layer_name = layer.name()
            logger.info(f"\nAnalyzing layer: {layer_name}")

            # Get optimal backend for this layer
            optimal_backend = self._get_optimal_backend_for_layer(layer)

            if optimal_backend:
                # Verify backend supports layer
                if self._verify_backend_supports_layer(layer, optimal_backend):
                    self.set_forced_backend(layer.id(), optimal_backend)
                    backend_stats[optimal_backend] += 1
                    optimized_count += 1
                    logger.info(f"  ✓ Set backend to: {optimal_backend.upper()}")
                else:
                    backend_stats['auto'] += 1
                    logger.info(f"  ⚠ Backend {optimal_backend.upper()} not compatible - using auto")
            else:
                backend_stats['auto'] += 1
                logger.info("  → Using auto-selection")

        logger.info("\n" + "=" * 60)
        logger.info("AUTO-SELECTION COMPLETE")
        logger.info(f"Optimized: {optimized_count} layers")
        logger.info(f"Skipped: {skipped_count} invalid layers")
        logger.info("Backend distribution:")
        for backend, count in backend_stats.items():
            if count > 0:
                logger.info(f"  - {backend.upper()}: {count} layer(s)")
        logger.info("=" * 60)

        # Emit signal with summary (requires 2 args: layer_id, backend_type)
        self.backend_changed.emit("batch_optimization", f"Optimized {optimized_count} layers")

        return optimized_count

    def _get_optimal_backend_for_layer(self, layer: QgsVectorLayer) -> Optional[str]:
        """
        Determine optimal backend for a layer based on characteristics.

        Args:
            layer: QgsVectorLayer instance

        Returns:
            Optimal backend ('postgresql', 'spatialite', 'ogr') or None for auto
        """
        try:
            from ...adapters.backends import POSTGRESQL_AVAILABLE
            from ...infrastructure.utils import detect_layer_provider_type
        except ImportError:
            logger.warning("Could not import backend detection functions")
            return None

        if not layer or not layer.isValid():
            return None

        provider_type = detect_layer_provider_type(layer)
        feature_count = layer.featureCount()
        source = layer.source().lower()

        logger.debug(f"  Provider: {provider_type}, Features: {feature_count:,}")
        logger.debug(f"  PostgreSQL available: {POSTGRESQL_AVAILABLE}")

        # PostgreSQL layers - ALWAYS use PostgreSQL backend (v4.1.4)
        # FIX v4.1.4: QGIS native API (setSubsetString) works without psycopg2
        # Never fallback to OGR for PostgreSQL layers
        if provider_type == 'postgresql':
            if not POSTGRESQL_AVAILABLE:
                logger.debug("  → PostgreSQL (QGIS native API) - psycopg2 not available for advanced features")
            else:
                logger.debug(f"  → PostgreSQL ({feature_count:,} features) - Full backend")
            return 'postgresql'

        # SQLite/Spatialite layers
        elif provider_type == 'spatialite':
            if feature_count > 5000:
                logger.debug(f"  → SQLite ({feature_count}) - Spatialite R-tree optimal")
                return 'spatialite'
            else:
                logger.debug(f"  → Small SQLite ({feature_count}) - OGR sufficient")
                return 'ogr'

        # OGR layers
        elif provider_type == 'ogr':
            if 'gpkg' in source or 'sqlite' in source:
                if feature_count > 5000:
                    logger.debug(f"  → GeoPackage ({feature_count}) - Spatialite optimal")
                    return 'spatialite'
                else:
                    logger.debug(f"  → Small GeoPackage ({feature_count}) - OGR sufficient")
                    return 'ogr'

            logger.debug(f"  → OGR format ({feature_count}) - OGR sufficient")
            return 'ogr'

        logger.debug(f"  → Unknown provider '{provider_type}' - auto-selection")
        return None

    def _verify_backend_supports_layer(self, layer: QgsVectorLayer, backend: str) -> bool:
        """
        Verify that a backend can actually process the layer.

        Args:
            layer: Layer to check
            backend: Backend type to verify

        Returns:
            True if backend supports this layer
        """
        try:
            from ...infrastructure.utils import detect_layer_provider_type, POSTGRESQL_AVAILABLE
        except ImportError:
            return True  # Assume compatible if can't check

        provider_type = detect_layer_provider_type(layer)

        if backend == 'postgresql':
            # PostgreSQL backend only for PostgreSQL layers
            return provider_type == 'postgresql' and POSTGRESQL_AVAILABLE
        elif backend == 'spatialite':
            # Spatialite works with SQLite and GeoPackage
            source = layer.source().lower()
            return provider_type == 'spatialite' or 'gpkg' in source or 'sqlite' in source
        elif backend == 'ogr':
            # OGR is universal fallback
            return True

        return False

    def handle_indicator_clicked(self) -> None:
        """
        Handle click on backend indicator.

        Shows backend selection menu or triggers reload if no layers.
        """

        # Lazy initialization fallback. Once set up, read the dock state again:
        # setup() now runs when the dock is built, before the optimization
        # settings are restored (the first click used to read them here).
        if not self._initialized:
            self.setup()
        else:
            self._sync_with_dockwidget()

        # Check if in waiting state (no layers)
        if self._indicator_label:
            text = self._indicator_label.text()
            if text in ('...', '⟳'):
                logger.info("Backend indicator clicked in waiting state - requesting reload")
                self.reload_requested.emit()
                return

        current_layer = self.dockwidget.current_layer
        if not current_layer:
            self.reload_requested.emit()
            return

        self._show_backend_menu(current_layer)

    # === Private Methods ===

    def _find_indicator_label(self) -> None:
        """Find the backend indicator label in dockwidget."""
        if hasattr(self.dockwidget, 'backend_indicator_label') and self.dockwidget.backend_indicator_label:
            self._indicator_label = self.dockwidget.backend_indicator_label
            logger.debug(f"BackendController: Found indicator label: {self._indicator_label}")
        else:
            logger.debug("BackendController: backend_indicator_label not found in dockwidget")

    def _sync_with_dockwidget(self) -> None:
        """Sync state with dockwidget attributes."""
        # Sync forced backends
        if hasattr(self.dockwidget, 'forced_backends'):
            self._forced_backends = self.dockwidget.forced_backends.copy()

        # Sync optimization settings
        for attr in ('_optimization_enabled', '_centroid_auto_enabled', '_optimization_ask_before'):
            if hasattr(self.dockwidget, attr):
                setattr(self, attr, getattr(self.dockwidget, attr))

    def _detect_backend_for_layer(
        self,
        layer: QgsVectorLayer,
        postgresql_available: Optional[bool] = None,
        forced_backend: Optional[str] = None
    ) -> str:
        """
        Detect which backend should be used for a layer.

        Args:
            layer: Layer to analyze
            postgresql_available: PostgreSQL connection status
            forced_backend: Explicitly forced backend

        Returns:
            Backend type string
        """
        # Check forced backend
        if forced_backend:
            return forced_backend.lower()

        if layer.id() in self._forced_backends:
            return self._forced_backends[layer.id()].lower()

        # Auto-detection
        # FIX v4.1.4 (2026-01-21): PostgreSQL layers ALWAYS use PostgreSQL backend.
        # QGIS native API (setSubsetString) works without psycopg2.
        provider_type = layer.providerType()

        # PostgreSQL layers ALWAYS use PostgreSQL backend
        if provider_type == 'postgres':
            return 'postgresql'
        elif provider_type == 'spatialite':
            return 'spatialite'
        elif provider_type == 'ogr':
            # Check for GeoPackage/SQLite with Spatialite support
            source = layer.source().split('|')[0]
            if source.lower().endswith(('.gpkg', '.sqlite')):
                return 'spatialite'
            return 'ogr'
        else:
            return 'unknown'

    def _update_indicator_display(
        self,
        backend_type: str,
        is_forced: bool = False,
        layer: Optional[QgsVectorLayer] = None
    ) -> None:
        """
        Update the visual display of the backend indicator.

        Args:
            backend_type: Backend type to display
            is_forced: Whether backend is forced by user
            layer: Current layer for context
        """
        # Try to find indicator label if not set
        if not self._indicator_label:
            self._find_indicator_label()

        # Still no indicator label? Try direct access to dockwidget's label
        if not self._indicator_label:
            if hasattr(self.dockwidget, 'backend_indicator_label') and self.dockwidget.backend_indicator_label:
                self._indicator_label = self.dockwidget.backend_indicator_label
                logger.debug("Found backend_indicator_label via direct dockwidget access")
            else:
                logger.warning("BackendController: _indicator_label not found, cannot update display")
                return

        style = BACKEND_STYLES.get(backend_type, BACKEND_STYLES['unknown'])

        # Build text with forced indicator
        text = style['text']
        if is_forced:
            text = f"{text}⚡"

        # FilterMate 5 design: the badge names the layer kind first ("Vector · Spatialite"),
        # in the vector color of the mockup; the backend stays in the text and the tooltip.
        from ..styles.mockup_design import KIND_COLORS, badge_stylesheet, vector_badge_text
        # Context FilterMateDockWidget (_tr uses the dock): the dock declares tr("Vector").
        self._indicator_label.setText(vector_badge_text(text, self._tr("Vector")))
        # A fallback backend keeps its warning color (the "*" alone is easy to miss); "..." is neutral.
        if backend_type.endswith('_fallback'):
            badge_color = style['background']
        elif backend_type == 'unknown':
            badge_color = '#bdbdbd'
        else:
            badge_color = KIND_COLORS['vector']
        self._indicator_label.setStyleSheet(badge_stylesheet('label_backend_indicator', badge_color))

        # Build tooltip with context
        tooltip = style['tooltip']
        # Raster / point cloud layers have no featureCount() (FilterMate 5).
        if layer and isinstance(layer, QgsVectorLayer):
            feature_count = layer.featureCount()
            tooltip += f"\nLayer: {layer.name()} ({feature_count:,} features)"
        if is_forced:
            tooltip += "\n⚡ Manually forced"

        self._indicator_label.setToolTip(tooltip)

    def _refresh_indicator_for_current_layer(self) -> None:
        """
        Refresh the backend indicator for the current layer.

        This method ensures the indicator is updated after batch operations
        (like force_backend_for_all_layers or auto_select_optimal_backends).
        """
        current_layer = self.dockwidget.current_layer
        if not current_layer or not current_layer.isValid():
            return

        # Get the backend for current layer (may have been changed by batch operation)
        backend_type = self._detect_backend_for_layer(
            current_layer, self._current_postgresql_available
        )

        # Check if forced
        is_forced = current_layer.id() in self._forced_backends

        # Update the display
        self._update_indicator_display(backend_type, is_forced, current_layer)
        logger.debug(f"Refreshed indicator for layer {current_layer.name()}: {backend_type} (forced: {is_forced})")

    def _show_backend_menu(self, layer: QgsVectorLayer) -> None:
        """
        Show the backend selection menu.

        Args:
            layer: Current layer for backend selection
        """
        from ...infrastructure.feedback import show_info, show_success, show_warning

        available = self.get_available_backends_for_layer(layer)

        if not available:
            show_warning("FilterMate", self._tr("No alternative backends available for this layer"))
            return

        menu = QMenu(self.dockwidget)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # Header
        header = menu.addAction(self._tr("Select Backend:"))
        header.setEnabled(False)
        menu.addSeparator()

        # Available backends
        current_forced = self._forced_backends.get(layer.id())
        for backend_type, backend_name, backend_icon in available:
            action_text = f"{backend_icon} {backend_name}"
            if current_forced == backend_type:
                action_text += " ✓"
            action = menu.addAction(action_text)
            action.setData(backend_type)

        menu.addSeparator()

        # Auto option
        auto_action = menu.addAction("⚙️ " + self._tr("Auto (Default)"))
        auto_action.setData(None)
        if not current_forced:
            auto_action.setText(auto_action.text() + " ✓")

        menu.addSeparator()

        # Auto-select all
        auto_all_action = menu.addAction("🎯 " + self._tr("Auto-select Optimal for All Layers"))
        auto_all_action.setData('__AUTO_ALL__')

        # Force all
        current_backend = self.get_current_backend(layer)
        force_all_action = menu.addAction("🔒 " + self._tr("Force {0} for All Layers").format(current_backend.upper()))
        force_all_action.setData('__FORCE_ALL__')

        menu.addSeparator()

        # Cleanup Temp Tables submenu
        cleanup_menu = menu.addMenu("🧹 " + self._tr("Clear Temp Tables"))

        # Project cleanup
        project_cleanup_action = cleanup_menu.addAction(self._tr("📁 Current Project"))
        project_cleanup_action.setData('__CLEANUP_PROJECT__')
        project_cleanup_action.setToolTip(self._tr("Clear temporary tables for the current project only"))

        # Global cleanup
        global_cleanup_action = cleanup_menu.addAction(self._tr("🌐 All Projects (Global)"))
        global_cleanup_action.setData('__CLEANUP_GLOBAL__')
        global_cleanup_action.setToolTip(self._tr("Clear ALL FilterMate temporary tables from all databases"))

        # Show menu
        selected_action = menu.exec(QCursor.pos())

        if selected_action:
            data = selected_action.data()

            if data == '__AUTO_ALL__':
                count = self.auto_select_optimal_backends()
                show_success("FilterMate", self._tr("Auto-selected backends for {0} layer(s)").format(count))
                # Update indicator for current layer after batch operation
                self._refresh_indicator_for_current_layer()
            elif data == '__FORCE_ALL__':
                count = self.force_backend_for_all_layers(current_backend)
                show_success("FilterMate", self._tr("Forced {0} backend for {1} layer(s)").format(current_backend.upper(), count))
                # Update indicator for current layer after batch operation
                self._refresh_indicator_for_current_layer()
            elif data == '__CLEANUP_PROJECT__':
                count = self.cleanup_temp_tables_project()
                if count > 0:
                    show_success("FilterMate", self._tr("Cleared {0} temporary table(s) for current project").format(count))
                else:
                    show_info("FilterMate", self._tr("No temporary tables found for current project"))
            elif data == '__CLEANUP_GLOBAL__':
                # Lists the objects and asks before anything is dropped
                self.run_global_cleanup_with_confirmation()
            else:
                self.set_forced_backend(layer.id(), data)
                if data:
                    self.update_for_layer(layer, actual_backend=data)
                    show_success("FilterMate", self._tr("Backend forced to {0} for '{1}'").format(data.upper(), layer.name()))
                else:
                    self.update_for_layer(layer)
                    show_info("FilterMate", self._tr("Backend set to Auto for '{0}'").format(layer.name()))

    # === Optimization Settings ===

    @property
    def optimization_enabled(self) -> bool:
        """Whether auto-optimization is enabled."""
        return self._optimization_enabled

    @optimization_enabled.setter
    def optimization_enabled(self, value: bool) -> None:
        """Set optimization enabled state."""
        self._optimization_enabled = value
        if hasattr(self.dockwidget, '_optimization_enabled'):
            self.dockwidget._optimization_enabled = value

    @property
    def centroid_auto_enabled(self) -> bool:
        """Whether centroid auto-detection is enabled."""
        return self._centroid_auto_enabled

    @centroid_auto_enabled.setter
    def centroid_auto_enabled(self, value: bool) -> None:
        """Set centroid auto-detection enabled state."""
        self._centroid_auto_enabled = value
        if hasattr(self.dockwidget, '_centroid_auto_enabled'):
            self.dockwidget._centroid_auto_enabled = value

    def toggle_optimization_enabled(self) -> bool:
        """Toggle optimization enabled state."""
        self.optimization_enabled = not self.optimization_enabled
        return self.optimization_enabled

    def toggle_centroid_auto(self) -> bool:
        """Toggle centroid auto-detection."""
        self.centroid_auto_enabled = not self.centroid_auto_enabled
        return self.centroid_auto_enabled

    # ========================================
    # POSTGRESQL MAINTENANCE METHODS (Sprint 13)
    # ========================================

    def get_pg_session_context(self):
        """
        Get PostgreSQL session context for maintenance operations.

        v4.0 Sprint 13: Migrated from dockwidget._get_pg_session_context()
        v4.3.8 (2026-01-23): Also search QGIS project layers for connection

        Returns:
            tuple: (app, session_id, schema, connexion)
        """
        from ...adapters.backends import POSTGRESQL_AVAILABLE
        if not POSTGRESQL_AVAILABLE:
            return None, None, None, None

        try:
            from ...infrastructure.utils.layer_utils import get_datasource_connexion_from_layer
        except ImportError:
            from ...infrastructure.utils.layer_utils import get_datasource_connexion_from_layer

        # Get app reference
        app = getattr(self.dockwidget, '_app_ref', None)
        if not app:
            parent = self.dockwidget.parent()
            while parent:
                if hasattr(parent, 'session_id'):
                    app = parent
                    break
                parent = parent.parent() if hasattr(parent, 'parent') else None

        session_id = getattr(app, 'session_id', None) if app else None
        schema = getattr(app, 'app_postgresql_temp_schema', 'filter_mate_temp') if app else 'filter_mate_temp'

        # Find a PostgreSQL connection
        connexion = None

        # 1. First try PROJECT_LAYERS (registered layers)
        project_layers = getattr(app, 'PROJECT_LAYERS', {}) if app else {}
        for layer_info in project_layers.values():
            layer = layer_info.get('layer')
            if layer and layer.isValid() and layer.providerType() == 'postgres':
                connexion, _ = get_datasource_connexion_from_layer(layer)
                if connexion:
                    break

        # 2. FIX v4.3.8: If no connection found, search ALL QGIS project layers
        # This handles cases where PostgreSQL layers exist but aren't in PROJECT_LAYERS
        if not connexion:
            from qgis.core import QgsProject
            for layer in QgsProject.instance().mapLayers().values():
                if hasattr(layer, 'providerType') and layer.providerType() == 'postgres':
                    if layer.isValid():
                        connexion, _ = get_datasource_connexion_from_layer(layer)
                        if connexion:
                            logger.debug(f"Got PostgreSQL connection from QGIS layer: {layer.name()}")
                            break

        return app, session_id, schema, connexion

    @property
    def pg_auto_cleanup_enabled(self) -> bool:
        """Whether PostgreSQL auto-cleanup is enabled."""
        return getattr(self, '_pg_auto_cleanup_enabled', True)

    @pg_auto_cleanup_enabled.setter
    def pg_auto_cleanup_enabled(self, value: bool) -> None:
        """Set PostgreSQL auto-cleanup enabled state."""
        self._pg_auto_cleanup_enabled = value
        if hasattr(self.dockwidget, '_pg_auto_cleanup_enabled'):
            self.dockwidget._pg_auto_cleanup_enabled = value

    def toggle_pg_auto_cleanup(self) -> bool:
        """
        Toggle PostgreSQL auto-cleanup.

        v4.0 Sprint 13: Migrated from dockwidget._toggle_pg_auto_cleanup()

        Returns:
            bool: New state of pg_auto_cleanup
        """
        self.pg_auto_cleanup_enabled = not self.pg_auto_cleanup_enabled
        return self.pg_auto_cleanup_enabled

    def cleanup_postgresql_session_views(self) -> bool:
        """
        Cleanup PostgreSQL materialized views for current session.

        v4.0 Sprint 13: Migrated from dockwidget._cleanup_postgresql_session_views()

        Returns:
            bool: True if cleanup successful
        """
        app, session_id, schema, connexion = self.get_pg_session_context()

        if not connexion:
            logger.warning("cleanup_postgresql_session_views: No PostgreSQL connection available")
            return False

        if not session_id:
            logger.warning("cleanup_postgresql_session_views: Session ID not available")
            return False

        try:
            with connexion.cursor() as cursor:
                # Find views for this session (unified fm_temp_* prefix v4.4.4)
                # Also check legacy mv_ prefix for backward compatibility
                cursor.execute(
                    """SELECT matviewname FROM pg_matviews
                       WHERE schemaname = %s
                       AND (matviewname LIKE %s OR matviewname LIKE %s)""",
                    (schema, f"fm_temp_mv_{session_id}_%", f"mv_{session_id}_%")
                )
                views = [v[0] for v in cursor.fetchall()]

                if not views:
                    logger.info(f"No views found for session {session_id[:8]}")
                    return True

                # Drop each view
                safe_schema = sanitize_sql_identifier(schema)
                for view in views:
                    try:
                        safe_view = sanitize_sql_identifier(view)
                        cursor.execute(f'DROP MATERIALIZED VIEW IF EXISTS "{safe_schema}"."{safe_view}" CASCADE;')
                    except Exception as e:
                        logger.warning(f"Failed to drop view {view}: {e}")

                connexion.commit()
                logger.info(f"Cleaned up {len(views)} view(s) for session {session_id[:8]}")
                return True

        except Exception as e:
            logger.error(f"Error cleaning PostgreSQL session views: {e}")
            return False
        finally:
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    def list_postgresql_schema_objects(self) -> Optional[List[Tuple[str, str, str]]]:
        """
        List the objects that dropping FilterMate's PostgreSQL schema would remove.

        Nothing is modified. Used to ask the user before the schema is dropped.

        Returns:
            list: ``(kind, schema, name)`` tuples, or None when there is no
            connection, the schema does not exist or it is not a FilterMate
            schema.
        """
        from ...infrastructure.database.temp_objects import PG_TEMP_SCHEMAS

        app, session_id, schema, connexion = self.get_pg_session_context()
        if not connexion or schema not in PG_TEMP_SCHEMAS:
            return None
        try:
            with connexion.cursor() as cursor:
                objects, foreign = self._pg_schema_content(cursor, schema)
                return [] if foreign else objects
        except Exception as e:
            logger.error(f"Error listing PostgreSQL schema objects: {e}")
            return None
        finally:
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    @staticmethod
    def _pg_schema_content(cursor, schema: str):
        """Split the relations of a schema into FilterMate's and foreign ones.

        Returns:
            tuple: ``(filtermate_objects, foreign_names)`` where the first list
            holds ``(kind, schema, name)`` and the second the names of anything
            FilterMate did not create (user tables, plain views, ...).
        """
        from ...infrastructure.database.temp_objects import is_filtermate_pg_temp_object

        cursor.execute(
            """SELECT c.relname, c.relkind
               FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'f')""",
            (schema,)
        )
        objects, foreign = [], []
        for name, relkind in cursor.fetchall():
            kind = {'m': 'matview', 'r': 'table'}.get(relkind)
            if kind and is_filtermate_pg_temp_object(kind, schema, name):
                objects.append((kind, schema, name))
            else:
                foreign.append(name)
        return objects, foreign

    @staticmethod
    def _drop_pg_temp_objects(connexion, cursor, objects) -> int:
        """Drop FilterMate temporary PostgreSQL objects, never with CASCADE.

        Every object is validated again. A materialized view may depend on
        another one (``..._dump``): a refused drop is retried after the others
        (a few passes). What still cannot be dropped is left in place and
        logged, instead of being cascaded onto objects FilterMate did not
        create.

        Args:
            connexion: psycopg2 connection (commit / rollback per object).
            cursor: Cursor of that connection.
            objects: ``(kind, schema, name)`` tuples.

        Returns:
            int: Number of objects dropped.
        """
        from ...infrastructure.database.temp_objects import is_filtermate_pg_temp_object

        pending = [o for o in objects if is_filtermate_pg_temp_object(*o)]
        dropped = 0
        for _pass in range(4):
            if not pending:
                break
            still_pending = []
            for kind, obj_schema, name in pending:
                statement = 'DROP MATERIALIZED VIEW' if kind == 'matview' else 'DROP TABLE'
                try:
                    cursor.execute(
                        f'{statement} IF EXISTS "{sanitize_sql_identifier(obj_schema)}"."{sanitize_sql_identifier(name)}";'  # nosec B608
                    )
                    connexion.commit()
                    dropped += 1
                    logger.debug(f"Dropped {kind}: {obj_schema}.{name}")
                except Exception as e:
                    try:
                        connexion.rollback()
                    except Exception:  # nosec B110 - best-effort rollback
                        pass
                    still_pending.append((kind, obj_schema, name))
                    logger.debug(f"Could not drop {kind} {obj_schema}.{name} yet: {e}")
            if len(still_pending) == len(pending):
                break  # no progress: remaining ones have outside dependents
            pending = still_pending
        for kind, obj_schema, name in pending:
            logger.warning(f"Left in place (dependent objects): {kind} {obj_schema}.{name}")
        return dropped

    def cleanup_postgresql_schema_if_empty(self, force: bool = False) -> bool:
        """
        Drop PostgreSQL schema if no other sessions are using it.

        v4.0 Sprint 13: Migrated from dockwidget._cleanup_postgresql_schema_if_empty()

        Only FilterMate's own schemas can be dropped, and only when every
        relation they hold is a FilterMate temporary object: the schema is
        emptied object by object and then dropped without CASCADE, so a user
        table (or the ``public`` schema) is never lost.

        Args:
            force: If True, skip confirmation for views from other sessions

        Returns:
            bool: True if cleanup successful or schema doesn't exist
        """
        from ...infrastructure.database.temp_objects import PG_TEMP_SCHEMAS

        app, session_id, schema, connexion = self.get_pg_session_context()

        if not connexion:
            logger.warning("cleanup_postgresql_schema_if_empty: No PostgreSQL connection available")
            return False

        if schema not in PG_TEMP_SCHEMAS:
            logger.warning(f"Refusing to drop schema '{schema}': it is not a FilterMate temporary schema")
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass
            return False

        try:
            with connexion.cursor() as cursor:
                # Check if schema exists
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                    (schema,)
                )
                if cursor.fetchone()[0] == 0:
                    logger.info(f"Schema '{schema}' does not exist")
                    return True

                objects, foreign = self._pg_schema_content(cursor, schema)
                if foreign:
                    logger.warning(
                        f"Schema '{schema}' holds {len(foreign)} object(s) FilterMate did not create "
                        f"({', '.join(sorted(foreign)[:5])}): not dropped"
                    )
                    return False

                # Check for views from other sessions (handle both new and legacy prefixes)
                views = [name for kind, _s, name in objects if kind == 'matview']
                other_views = [v for v in views if not (
                    session_id and (
                        v.startswith(f"fm_temp_mv_{session_id}_") or
                        v.startswith(f"mv_{session_id}_")
                    )
                )]

                if other_views and not force:
                    logger.warning(f"Schema '{schema}' has {len(other_views)} view(s) from other sessions")
                    return False

                # Empty the schema (FilterMate objects only), then drop it: no CASCADE
                self._drop_pg_temp_objects(connexion, cursor, objects)
                safe_schema = sanitize_sql_identifier(schema)
                cursor.execute(f'DROP SCHEMA IF EXISTS "{safe_schema}";')
                connexion.commit()
                logger.info(f"Schema '{schema}' dropped successfully")
                return True

        except Exception as e:
            logger.error(f"Error cleaning PostgreSQL schema: {e}")
            try:
                connexion.rollback()
            except Exception:  # nosec B110 - best-effort rollback
                pass
            return False
        finally:
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    def get_postgresql_session_info(self) -> dict:
        """
        Get PostgreSQL session information.

        v4.0 Sprint 13: Migrated from dockwidget._show_postgresql_session_info()

        Returns:
            dict: Session information with keys: session_id, schema, auto_cleanup,
                  schema_exists, our_views_count, total_views_count, connection_available
        """
        app, session_id, schema, connexion = self.get_pg_session_context()

        info = {
            'session_id': session_id,
            'schema': schema,
            'auto_cleanup': self.pg_auto_cleanup_enabled,
            'connection_available': connexion is not None,
            'schema_exists': False,
            'our_views_count': 0,
            'total_views_count': 0
        }

        if connexion:
            try:
                with connexion.cursor() as cursor:
                    # Count our views (both new and legacy prefixes)
                    if session_id:
                        cursor.execute(
                            """SELECT COUNT(*) FROM pg_matviews
                               WHERE schemaname = %s
                               AND (matviewname LIKE %s OR matviewname LIKE %s)""",
                            (schema, f"fm_temp_mv_{session_id}_%", f"mv_{session_id}_%")
                        )
                        info['our_views_count'] = cursor.fetchone()[0]

                    # Count total views
                    cursor.execute(
                        "SELECT COUNT(*) FROM pg_matviews WHERE schemaname = %s",
                        (schema,)
                    )
                    info['total_views_count'] = cursor.fetchone()[0]

                    # Check schema exists
                    cursor.execute(
                        "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                        (schema,)
                    )
                    info['schema_exists'] = cursor.fetchone()[0] > 0

            except Exception as e:
                info['error'] = str(e)[:50]
                logger.warning(f"Error getting PostgreSQL session info: {e}")
            finally:
                try:
                    connexion.close()
                except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                    pass

        return info

    # ========================================
    # TEMP TABLE CLEANUP METHODS (v4.0)
    # ========================================

    def cleanup_temp_tables_project(self) -> int:
        """
        Clean up temporary tables for the current project only.

        Cleans both PostgreSQL materialized views and Spatialite temp tables
        associated with the current session/project.

        Returns:
            int: Total number of tables cleaned up
        """
        total_count = 0

        # 1. Clean PostgreSQL views for current session
        pg_count = self._cleanup_postgresql_current_session()
        total_count += pg_count

        # 2. Clean Spatialite temp tables for current project databases
        spatialite_count = self._cleanup_spatialite_project_tables()
        total_count += spatialite_count

        logger.info(f"Project cleanup complete: {total_count} table(s) removed "
                   f"(PostgreSQL: {pg_count}, Spatialite: {spatialite_count})")
        return total_count

    def collect_global_cleanup_candidates(self) -> Dict[str, object]:
        """
        List what the global cleanup would remove, without removing anything.

        Only names FilterMate generates are listed (exact, case-sensitive
        match, tables registered as GeoPackage layers excluded).

        Returns:
            dict: ``{'spatialite': {db_path: [table, ...]}, 'postgresql':
            [(kind, schema, name), ...]}``; empty containers when nothing is found.
        """
        from ...infrastructure.database.temp_objects import list_filtermate_temp_tables

        spatialite = {}
        for db_path in self._spatialite_project_databases():
            tables = list_filtermate_temp_tables(db_path)
            if tables:
                spatialite[db_path] = tables
        return {
            'spatialite': spatialite,
            'postgresql': self._list_postgresql_temp_objects(),
        }

    @staticmethod
    def format_cleanup_candidates(candidates: Dict[str, object]) -> List[str]:
        """One display line per object of :meth:`collect_global_cleanup_candidates`."""
        lines = []
        for kind, schema, name in candidates.get('postgresql', []):
            lines.append(f"PostgreSQL: {schema}.{name} ({kind})")
        for db_path, tables in sorted(candidates.get('spatialite', {}).items()):
            for table in tables:
                lines.append(f"{db_path}: {table}")
        return lines

    def _confirm_global_cleanup(self, candidates: Dict[str, object]) -> bool:
        """Ask the user to confirm the global cleanup, listing the objects.

        Args:
            candidates: Result of :meth:`collect_global_cleanup_candidates`.

        Returns:
            bool: True only when the user explicitly accepts ("No" is the default).
        """
        from qgis.PyQt.QtWidgets import QMessageBox

        lines = self.format_cleanup_candidates(candidates)
        shown = lines[:12]
        text = self._tr(
            "FilterMate will permanently delete {0} temporary table(s) / view(s) "
            "from the databases of the project and of the PostgreSQL connection:"
        ).format(len(lines)) + "\n\n" + "\n".join(shown)
        if len(lines) > len(shown):
            text += "\n" + self._tr("... and {0} more (see details)").format(len(lines) - len(shown))
        text += "\n\n" + self._tr("Your own tables and layers are not touched. Continue?")

        box = QMessageBox(self.dockwidget)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self._tr("Clear all FilterMate temporary tables"))
        box.setText(text)
        box.setDetailedText("\n".join(lines))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    def run_global_cleanup_with_confirmation(self) -> None:
        """Menu action "Clear Temp Tables > All Projects (Global)".

        Lists what would go, asks the user, and only then deletes it.
        """
        from ...infrastructure.feedback import show_info, show_success

        candidates = self.collect_global_cleanup_candidates()
        if not self.format_cleanup_candidates(candidates):
            show_info("FilterMate", self._tr("No temporary tables found"))
            return
        if not self._confirm_global_cleanup(candidates):
            show_info("FilterMate", self._tr("Cleanup cancelled"))
            return
        count = self.cleanup_temp_tables_global(candidates)
        if count > 0:
            show_success("FilterMate", self._tr("Cleared {0} temporary table(s) globally").format(count))
        else:
            show_info("FilterMate", self._tr("No temporary tables found"))

    def cleanup_temp_tables_global(self, candidates: Optional[Dict[str, object]] = None) -> int:
        """
        Clean up ALL FilterMate temporary tables globally.

        Cleans all FilterMate temp tables from:
        - PostgreSQL: the materialized views / tables FilterMate generates
        - Spatialite / GeoPackage: ``fm_temp_<session>_*`` and legacy
          ``mv_<session>_*`` tables of the databases of the project

        Nothing else is dropped: no user table, no layer registered in a
        GeoPackage, no CASCADE. This method does not ask anything; the menu
        action asks first (:meth:`run_global_cleanup_with_confirmation`).

        Args:
            candidates: Result of :meth:`collect_global_cleanup_candidates` the
                user confirmed (default: collected now). Each name is
                validated again before it is dropped.

        Returns:
            int: Total number of tables cleaned up
        """
        if candidates is None:
            candidates = self.collect_global_cleanup_candidates()
        total_count = 0

        # 1. Clean PostgreSQL objects
        pg_count = self._cleanup_postgresql_all_sessions(candidates.get('postgresql'))
        total_count += pg_count

        # 2. Clean Spatialite / GeoPackage temp tables
        spatialite_count = self._cleanup_spatialite_all_tables(candidates.get('spatialite'))
        total_count += spatialite_count

        logger.info(f"Global cleanup complete: {total_count} table(s) removed "
                   f"(PostgreSQL: {pg_count}, Spatialite: {spatialite_count})")
        return total_count

    def _cleanup_postgresql_current_session(self) -> int:
        """
        Clean PostgreSQL materialized views for current session only.

        Returns:
            int: Number of views dropped
        """
        app, session_id, schema, connexion = self.get_pg_session_context()

        if not connexion or not session_id:
            logger.debug("No PostgreSQL connection or session_id for current session cleanup")
            return 0

        try:
            with connexion.cursor() as cursor:
                # Find views for this session only (unified fm_temp_* prefix v4.4.4)
                # Also check legacy mv_ prefix for backward compatibility
                cursor.execute(
                    """SELECT matviewname FROM pg_matviews
                       WHERE schemaname = %s
                       AND (matviewname LIKE %s OR matviewname LIKE %s)""",
                    (schema, f"fm_temp_mv_{session_id}_%", f"mv_{session_id}_%")
                )
                views = [v[0] for v in cursor.fetchall()]

                if not views:
                    logger.debug(f"No PostgreSQL views found for session {session_id[:8]}")
                    return 0

                count = 0
                safe_schema = sanitize_sql_identifier(schema)
                for view in views:
                    try:
                        safe_view = sanitize_sql_identifier(view)
                        cursor.execute(f'DROP MATERIALIZED VIEW IF EXISTS "{safe_schema}"."{safe_view}" CASCADE;')
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to drop PostgreSQL view {view}: {e}")

                connexion.commit()
                logger.info(f"PostgreSQL session cleanup: {count} view(s) dropped for session {session_id[:8]}")
                return count

        except Exception as e:
            logger.error(f"Error in PostgreSQL session cleanup: {e}")
            return 0
        finally:
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    @staticmethod
    def _find_postgresql_temp_objects(cursor) -> List[Tuple[str, str, str]]:
        """Materialized views and tables FilterMate generated, in any schema.

        The SQL only pre-selects with exact prefixes (underscores escaped,
        PostgreSQL LIKE is case-sensitive); each row is then checked again by
        :func:`is_filtermate_pg_temp_object`.

        Returns:
            list: ``(kind, schema, name)``, dependents (``..._dump``) first.
        """
        from ...infrastructure.database.temp_objects import (
            is_filtermate_pg_temp_object, pg_temp_object_like_patterns)

        found = []
        for kind, sql in (
            ('matview', """SELECT schemaname, matviewname FROM pg_matviews
                           WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                           AND matviewname LIKE ANY (%s)"""),
            ('table', """SELECT schemaname, tablename FROM pg_tables
                         WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                         AND tablename LIKE ANY (%s)"""),
        ):
            cursor.execute(sql, (pg_temp_object_like_patterns(kind),))
            for schema, name in cursor.fetchall():
                if is_filtermate_pg_temp_object(kind, schema, name):
                    found.append((kind, schema, name))
        found.sort(key=lambda o: (o[1], -len(o[2]), o[2]))
        return found

    def _list_postgresql_temp_objects(self) -> List[Tuple[str, str, str]]:
        """Read-only list of the PostgreSQL objects the global cleanup would drop."""
        app, session_id, schema, connexion = self.get_pg_session_context()
        if not connexion:
            return []
        try:
            with connexion.cursor() as cursor:
                return self._find_postgresql_temp_objects(cursor)
        except Exception as e:
            logger.error(f"Error listing PostgreSQL temporary objects: {e}")
            return []
        finally:
            try:
                connexion.rollback()
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    def _cleanup_postgresql_all_sessions(self, objects=None) -> int:
        """
        Clean the PostgreSQL materialized views AND tables created by FilterMate.

        FilterMate's names (see ``infrastructure/database/temp_objects.py``):
        - fm_temp_mv_*, fm_temp_src_*, fm_temp_chain_* (materialized views)
        - fm_temp_buf_*, fm_temp_tbl_*, fm_temp_src_* (tables)
        - legacy fm_mv_*, filtermate_mv_*, fm_buf_* inside FilterMate's schemas

        Nothing is dropped with CASCADE, and nothing outside those names
        (a user table called ``filtermate_catalog``, say) is ever touched.

        Args:
            objects: ``(kind, schema, name)`` list the user confirmed (default:
                looked up now).

        Returns:
            int: Total number of objects dropped
        """
        from ...infrastructure.database.temp_objects import PG_TEMP_SCHEMAS

        app, session_id, schema, connexion = self.get_pg_session_context()

        if not connexion:
            logger.warning("No PostgreSQL connection available for global cleanup")
            return 0

        try:
            with connexion.cursor() as cursor:
                if objects is None:
                    objects = self._find_postgresql_temp_objects(cursor)
                if not objects:
                    return 0
                logger.info(f"Found {len(objects)} FilterMate PostgreSQL object(s) to clean")
                total_count = self._drop_pg_temp_objects(connexion, cursor, objects)

                # Remove FilterMate's own schemas when they are now empty. No
                # CASCADE: a schema that still holds something is kept.
                for temp_schema in PG_TEMP_SCHEMAS:
                    try:
                        safe_schema = sanitize_sql_identifier(temp_schema)
                        cursor.execute(f'DROP SCHEMA IF EXISTS "{safe_schema}";')
                        connexion.commit()
                        logger.debug(f"Dropped empty schema: {temp_schema}")
                    except Exception as e:
                        connexion.rollback()
                        logger.debug(f"Schema {temp_schema} kept: {e}")

                logger.info(f"PostgreSQL global cleanup: {total_count} object(s) dropped")
                return total_count

        except Exception as e:
            logger.error(f"Error in PostgreSQL global cleanup: {e}")
            return 0
        finally:
            try:
                connexion.close()
            except Exception:  # nosec B110 - best-effort connection close, safe to ignore
                pass

    @staticmethod
    def _spatialite_project_databases() -> List[str]:
        """Source databases (.gpkg / .sqlite / .db) of the project's vector layers."""
        from qgis.core import QgsProject

        db_paths = set()
        for layer in QgsProject.instance().mapLayers().values():
            if hasattr(layer, 'providerType') and layer.providerType() in ('spatialite', 'ogr'):
                source = layer.source().split('|')[0]
                if source.lower().endswith(('.gpkg', '.sqlite', '.db')):
                    db_paths.add(source)
        return sorted(db_paths)

    def _cleanup_spatialite_project_tables(self) -> int:
        """Clean Spatialite temp tables for current project databases."""
        # Get session_id from app
        app = getattr(self.dockwidget, '_app_ref', None)
        session_id = getattr(app, 'session_id', None) if app else None

        if not session_id:
            logger.debug("No session_id available for Spatialite project cleanup")
            return 0

        total_count = 0
        for db_path in self._spatialite_project_databases():
            total_count += self._cleanup_spatialite_db(db_path, session_id)
        return total_count

    def _cleanup_spatialite_all_tables(self, candidates: Optional[Dict[str, List[str]]] = None) -> int:
        """Clean ALL FilterMate temp tables from the Spatialite databases of the project.

        Args:
            candidates: ``{db_path: [table, ...]}`` the user confirmed (default:
                everything FilterMate generated in the project's databases).
                Names are validated again by the drop.

        Returns:
            int: Number of tables dropped
        """
        if candidates is None:
            candidates = {db: None for db in self._spatialite_project_databases()}

        total_count = 0
        for db_path, tables in candidates.items():
            total_count += self._cleanup_spatialite_db(db_path, session_id=None, tables=tables)
        return total_count

    def _cleanup_spatialite_db(self, db_path: str, session_id: str = None, tables=None) -> int:
        """
        Clean FilterMate temp tables from a specific Spatialite database.

        Only ``fm_temp_<session>_*`` and legacy ``mv_<session>_*`` tables go
        (exact, case-sensitive match; a table registered in ``gpkg_contents``
        is never dropped). ``mvt_reseau`` or ``MVoies`` are user tables.

        Args:
            db_path: Path to the SQLite/GeoPackage database
            session_id: If provided, only clean tables for this session.
                       If None, clean the tables of every session.
            tables: Optional explicit list of candidates (re-validated).

        Returns:
            int: Number of tables cleaned up
        """
        import os
        from ...infrastructure.database.temp_objects import drop_filtermate_temp_tables

        if not db_path or not os.path.exists(db_path):
            return 0

        count = len(drop_filtermate_temp_tables(db_path, session_id=session_id, tables=tables))
        if count > 0:
            db_name = os.path.basename(db_path)
            scope = f"session {session_id[:8]}" if session_id else "all sessions"
            logger.info(f"Spatialite cleanup ({db_name}): {count} table(s) for {scope}")
        return count
