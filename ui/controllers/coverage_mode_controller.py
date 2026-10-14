"""
CoverageModeController - raster and point cloud layers in the dock (FilterMate 5).

EXPLORING selects on the source layer, FILTERING relates it to the targets:

* When the current layer is a raster or a point cloud, the vector groups of
  EXPLORING are hidden and replaced by the panel of that kind (pixel value,
  value range, classes, expression / classes, attribute ranges, height above
  a DTM, expression). FILTERING keeps all its widgets (layers to filter,
  combine operators, predicates, buffer); a "minimum coverage" box is added
  next to the predicates. The dock's buttons (filter, unfilter, reset, undo,
  redo, export) run :class:`CrossFilterService` instead of the vector engine.
* When the current layer is a vector, raster and point cloud layers checked
  in "layers to filter" are taken out of the vector task and clipped by the
  same source geometry (EXPLORING selection + buffer) once the vector task is
  launched; Undo / Redo / Unfilter follow.

Replaces ``PointCloudUIController`` (FilterMate 4.10 experimental panel, which
lived in FILTERING and disabled EXPLORING).
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .base_controller import BaseController

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget

logger = logging.getLogger(__name__)

COVERAGE_TASKS = ('filter', 'unfilter', 'reset', 'undo', 'redo', 'export')
VECTOR_EXPLORING_GROUPS = (
    'mGroupBox_exploring_single_selection',
    'mGroupBox_exploring_multiple_selection',
    'mGroupBox_exploring_custom_selection',
)
EXPLORING_BUTTONS = (
    'pushButton_exploring_identify',
    'pushButton_exploring_zoom',
    'pushButton_checkable_exploring_selecting',
    'pushButton_checkable_exploring_tracking',
    'pushButton_checkable_exploring_linking_widgets',
    'pushButton_exploring_reset_layer_properties',
)
COVERAGE_SPIN_NAME = 'mQgsSpinBox_filtering_coverage_min'
MAX_SOURCE_FEATURES = 100000


def _kind_of(layer: Any):
    from ...core.domain.layer_kind import LayerKind
    try:
        from ...adapters.qgis.point_cloud_capability import get_layer_kind
        return get_layer_kind(layer)
    except Exception as exc:
        logger.debug(f"[FM5] layer kind unavailable: {exc}")
        return LayerKind.OTHER


def _feedback():
    try:
        from ...infrastructure.feedback import show_info, show_warning
        return show_info, show_warning
    except ImportError:
        return (lambda *a, **k: None), (lambda *a, **k: None)


def _same_layer(first: Any, second: Any) -> bool:
    if first is second:
        return True
    if first is None or second is None:
        return False
    try:
        return first.id() == second.id()
    except (RuntimeError, AttributeError):
        return False


def _option(key: str, default):
    try:
        from ...config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


class CoverageModeController(BaseController):
    """Raster / point cloud source mode of the dock, and coverage targets of vector sources."""

    def __init__(self, dockwidget: 'FilterMateDockWidget', filter_service: Any = None, signal_manager: Any = None) -> None:
        super().__init__(dockwidget, filter_service, signal_manager)
        self._active_layer: Any = None
        self._kind: Any = None
        self._host: Any = None
        self._raster_panel: Any = None
        self._pc_panel: Any = None
        self._coverage_spin: Any = None
        self._saved_visibility: Dict[Any, bool] = {}
        self._saved_tooltips: Dict[str, str] = {}
        self._saved_enabled: Dict[str, bool] = {}
        self._panel_states: Dict[str, dict] = {}
        self._pixel_tool: Any = None
        self._previous_map_tool: Any = None
        self._preview_base_subset: Optional[str] = None
        self._preview_active = False
        self._histogram_cache: Dict[Tuple[str, int], Tuple[list, float, float]] = {}
        self._button_slots: List[Tuple[Any, Any]] = []
        # Vector sources: one flag per vector filter run, True when it also clipped coverage targets.
        self._linked_runs: Dict[str, List[bool]] = {}
        self._linked_redo: Dict[str, List[bool]] = {}
        self._running_task: Any = None

    # === Lifecycle ===

    def setup(self) -> None:
        """Panels are built on the first raster / point cloud layer; stored clips are replayed."""
        try:
            from qgis.core import QgsProject
            from qgis.PyQt.QtCore import QTimer
            project = QgsProject.instance()
            project.readProject.connect(self._on_project_read)
            project.cleared.connect(self._on_project_cleared)
            project.layersWillBeRemoved.connect(self._on_layers_removed)
            self._project_signal_connected = True
            QTimer.singleShot(1500, self.replay_stored_filters)
        except Exception as exc:
            logger.debug(f"[FM5] stored filters replay not scheduled: {exc}")
        logger.debug("CoverageModeController setup complete (panels deferred)")

    def _on_project_cleared(self) -> None:
        """A new / closed project: histories and links refer to layers that are gone."""
        self.service.history.clear()
        self._linked_runs.clear()
        self._linked_redo.clear()
        self._panel_states.clear()
        self._histogram_cache.clear()

    def _on_layers_removed(self, layer_ids) -> None:
        for layer_id in layer_ids or []:
            self.service.history.forget_layer(layer_id)
            self._linked_runs.pop(layer_id, None)
            self._linked_redo.pop(layer_id, None)
            self._panel_states.pop(layer_id, None)

    def _on_project_read(self, *_args) -> None:
        try:
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(1500, self.replay_stored_filters)
        except Exception as exc:
            logger.debug(f"[FM5] stored filters replay not scheduled: {exc}")

    def replay_stored_filters(self) -> int:
        """Clip again the raster / point cloud layers whose filter was saved in the project."""
        if getattr(self, '_torn_down', False):
            return 0
        try:
            from ...core.services.cross_filter_service import replay_project_filters
            count = replay_project_filters(self.service)
        except Exception as exc:
            logger.warning(f"[FM5] stored raster / point cloud filters not replayed: {exc}")
            return 0
        if count:
            show_info, _ = _feedback()
            show_info(self.tr("Restoring the filter of {0} raster / point cloud layer(s)…").format(count))
        return count

    def teardown(self) -> None:
        self._torn_down = True
        self.deactivate()
        if getattr(self, '_project_signal_connected', False):
            try:
                from qgis.core import QgsProject
                project = QgsProject.instance()
                for signal, slot in ((project.readProject, self._on_project_read),
                                     (project.cleared, self._on_project_cleared),
                                     (project.layersWillBeRemoved, self._on_layers_removed)):
                    try:
                        signal.disconnect(slot)
                    except (TypeError, RuntimeError):
                        pass
            except Exception:
                pass
            self._project_signal_connected = False
        try:
            self.service.cancel_all()
        except Exception:
            pass
        for widget_name in ('_host', '_coverage_spin'):
            widget = getattr(self, widget_name)
            setattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except Exception:
                    pass
        self._raster_panel = None
        self._pc_panel = None
        self._running_task = None
        self._export_task = None
        self._hag_task = None
        self._base_keepalive = None
        self._histogram_cache.clear()

    @property
    def active_layer(self) -> Any:
        return self._active_layer

    @property
    def active_kind(self) -> Any:
        return self._kind

    @property
    def service(self):
        from ...core.services.cross_filter_service import get_cross_filter_service
        return get_cross_filter_service()

    # === Layer change ===

    def is_coverage(self, layer: Any) -> bool:
        kind = _kind_of(layer)
        return getattr(kind, 'is_coverage', False)

    def on_current_layer_changed(self, layer: Any) -> bool:
        """Take over the layer change for a raster or point cloud layer.

        Returns:
            True when handled here (the vector chain must stop).
        """
        kind = _kind_of(layer)
        if getattr(kind, 'is_coverage', False):
            if not self._ensure_host():
                logger.warning("[FM5] coverage layer selected but the panels are unavailable")
                return False
            self.activate(layer, kind)
            return True
        if self._active_layer is not None:
            self.deactivate()
        return False

    def activate(self, layer: Any, kind: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        dw = self.dockwidget
        if self._active_layer is not None and not _same_layer(self._active_layer, layer):
            self._leave_layer()
        self._disconnect_previous_vector_selection(dw, layer)
        try:
            dw.current_layer = layer
        except Exception as exc:
            logger.warning(f"[FM5] current_layer not updated: {exc}")
        first_activation = self._active_layer is None
        self._active_layer = layer
        self._kind = kind
        if first_activation:
            self._save_dock_state()
        self._apply_layout(kind)
        self._show_kind_badge(layer, kind)
        if kind is LayerKind.RASTER:
            self._populate_raster(layer)
        else:
            self._populate_point_cloud(layer)
        self._restore_panel_state(layer)
        self._sync_layer_combo(layer)
        self._populate_filtering_targets(layer)
        self._load_coverage_min(layer)
        self._call(getattr(dw, 'currentLayerChanged', None), 'emit')
        self.update_undo_redo_buttons()
        logger.info(f"[FM5] {kind.value} layer active: {self._layer_name(layer)}")

    def deactivate(self) -> None:
        self._base_keepalive = None
        if self._active_layer is None and not self._saved_visibility:
            return
        self._leave_layer()
        self._restore_dock_state()
        self._call(self._host, 'setVisible', False)
        self._call(self._coverage_spin, 'setVisible', False)
        self._active_layer = None
        self._kind = None
        logger.debug("[FM5] coverage mode deactivated")

    def _leave_layer(self) -> None:
        """Save the panel input of the outgoing layer and drop its live previews."""
        layer = self._active_layer
        if layer is None:
            return
        self._deactivate_pixel_tool()
        try:
            self._panel_states[layer.id()] = self._current_panel().state() if self._current_panel() is not None else {}
        except Exception as exc:
            logger.debug(f"[FM5] panel state not saved: {exc}")
        self._stop_preview(layer)

    @staticmethod
    def _disconnect_previous_vector_selection(dw: Any, incoming_layer: Any) -> None:
        old_layer = getattr(dw, 'current_layer', None)
        if old_layer is None or _same_layer(old_layer, incoming_layer):
            return
        if getattr(dw, 'current_layer_selection_connection', None) is None:
            return
        try:
            old_layer.selectionChanged.disconnect(dw.on_layer_selection_changed)
        except (TypeError, RuntimeError, AttributeError) as exc:
            logger.debug(f"[FM5] previous selectionChanged not disconnected: {exc}")
        dw.current_layer_selection_connection = None

    # === Dock layout ===

    def _insert_in_exploring(self, host) -> bool:
        """Put the coverage panels right after the vector groups, in the layout holding them.

        The groups sit in ``verticalLayout_exploring_tabs_content``, itself nested
        in a grid: the layout is found by search, never assumed (an index of -1
        passed to ``QGridLayout.getItemPosition`` crashes Qt).
        """
        dw = self.dockwidget
        first = getattr(dw, VECTOR_EXPLORING_GROUPS[0], None)
        last = getattr(dw, VECTOR_EXPLORING_GROUPS[-1], None) or first
        if first is None:
            return False
        layout = getattr(dw, 'verticalLayout_exploring_tabs_content', None)
        if layout is None or layout.indexOf(last) < 0:
            layout = self._find_parent_layout(last)
        if layout is None:
            return False
        index = layout.indexOf(last)
        if index < 0:
            return False
        try:
            if hasattr(layout, 'insertWidget'):
                layout.insertWidget(index + 1, host)
            else:
                row, col, row_span, col_span = layout.getItemPosition(index)
                layout.addWidget(host, row + row_span, col, 1, max(1, col_span))
            return True
        except Exception as exc:
            logger.warning(f"[FM5] coverage panel insertion failed: {exc}")
            return False

    def _ensure_host(self) -> bool:
        if self._host is not None:
            return True
        try:
            from qgis.PyQt.QtWidgets import QStackedWidget
            from ..widgets.coverage_panels.raster_exploring_panel import RasterExploringPanel
            from ..widgets.coverage_panels.point_cloud_exploring_panel import PointCloudExploringPanel
        except Exception as exc:
            logger.warning(f"[FM5] coverage panels unavailable: {exc}")
            return False
        host = QStackedWidget()
        host.setObjectName('stackedWidget_exploring_coverage')
        self._raster_panel = RasterExploringPanel(host)
        self._pc_panel = PointCloudExploringPanel(host)
        host.addWidget(self._raster_panel)
        host.addWidget(self._pc_panel)
        if not self._insert_in_exploring(host):
            logger.warning("[FM5] coverage panel not inserted in EXPLORING")
        host.setVisible(False)
        self._host = host
        self._connect_panels()
        self._ensure_coverage_spin()
        return True

    def _ensure_coverage_spin(self) -> None:
        """Add the "minimum coverage" box next to the geometric predicates combo."""
        dw = self.dockwidget
        combo = getattr(dw, 'comboBox_filtering_geometric_predicates', None)
        if combo is None or self._coverage_spin is not None:
            return
        try:
            from qgis.gui import QgsSpinBox
        except ImportError:
            from qgis.PyQt.QtWidgets import QSpinBox as QgsSpinBox
        spin = QgsSpinBox()
        spin.setObjectName(COVERAGE_SPIN_NAME)
        spin.setRange(0, 100)
        spin.setSuffix(' %')
        spin.setPrefix(self.tr('cov. ≥ '))
        spin.setToolTip(self.tr("Minimum share of a polygon target inside the source geometry (0 = any overlap). "
                                "Used when the source is a raster or a point cloud."))
        spin.setVisible(False)
        spin.valueChanged.connect(self._on_coverage_min_changed)
        parent_layout = self._find_parent_layout(combo)
        if parent_layout is not None:
            parent_layout.insertWidget(parent_layout.indexOf(combo) + 1, spin)
        self._coverage_spin = spin

    @staticmethod
    def _find_parent_layout(widget):
        parent = widget.parentWidget()
        if parent is None:
            return None

        def search(layout):
            if layout is None:
                return None
            if layout.indexOf(widget) >= 0:
                return layout
            for i in range(layout.count()):
                child = layout.itemAt(i).layout()
                found = search(child)
                if found is not None:
                    return found
            return None
        return search(parent.layout())

    def _save_dock_state(self) -> None:
        dw = self.dockwidget
        self._saved_visibility = {}
        for name in VECTOR_EXPLORING_GROUPS:
            widget = getattr(dw, name, None)
            if widget is not None:
                self._saved_visibility[widget] = not widget.isHidden()
        badge = getattr(dw, 'backend_indicator_label', None)
        self._saved_badge = (badge.text(), badge.toolTip(), badge.styleSheet()) if badge is not None else None
        self._saved_tooltips = {}
        self._saved_enabled = {}
        for name in EXPLORING_BUTTONS:
            button = getattr(dw, name, None)
            if button is not None:
                self._saved_tooltips[name] = button.toolTip()
                self._saved_enabled[name] = button.isEnabled()

    def _restore_dock_state(self) -> None:
        dw = self.dockwidget
        saved, self._saved_visibility = self._saved_visibility, {}
        for widget, visible in saved.items():
            self._call(widget, 'setVisible', visible)
        for name, tooltip in self._saved_tooltips.items():
            button = getattr(dw, name, None)
            self._call(button, 'setToolTip', tooltip)
            self._call(button, 'setEnabled', self._saved_enabled.get(name, True))
        self._saved_tooltips = {}
        self._saved_enabled = {}
        badge = getattr(dw, 'backend_indicator_label', None)
        saved_badge, self._saved_badge = getattr(self, '_saved_badge', None), None
        if badge is not None and saved_badge is not None:
            self._call(badge, 'setText', saved_badge[0])
            self._call(badge, 'setToolTip', saved_badge[1])
            self._call(badge, 'setStyleSheet', saved_badge[2])

    def _show_kind_badge(self, layer: Any, kind: Any) -> None:
        """Show "Raster · gdal" / "Point cloud · copc" in the backend badge."""
        from ...core.domain.layer_kind import LayerKind
        badge = getattr(self.dockwidget, 'backend_indicator_label', None)
        if badge is None:
            return
        label = self.tr("Raster") if kind is LayerKind.RASTER else self.tr("Point cloud")
        try:
            provider = layer.providerType()
        except Exception:
            provider = ''
        color = '#c98a1d' if kind is LayerKind.RASTER else '#1f9e84'
        name = badge.objectName() or 'label_backend_indicator'
        self._call(badge, 'setText', f"{label} · {provider}" if provider else label)
        self._call(badge, 'setToolTip', self.tr("{0} layer: selection in EXPLORING, relation in FILTERING").format(label))
        self._call(badge, 'setStyleSheet', f"QLabel#{name}{{background:{color};color:white;border-radius:3px;padding:3px 10px;font-weight:600;}}")

    def _apply_layout(self, kind: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        dw = self.dockwidget
        for widget in self._saved_visibility:
            self._call(widget, 'setVisible', False)
        self._call(getattr(dw, 'frame_exploring', None), 'setEnabled', True)
        if self._host is not None:
            self._host.setCurrentWidget(self._raster_panel if kind is LayerKind.RASTER else self._pc_panel)
            self._host.setVisible(True)
        self._call(self._coverage_spin, 'setVisible', True)
        tips = {
            LayerKind.RASTER: {
                'pushButton_exploring_identify': self.tr("Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)"),
                'pushButton_exploring_zoom': self.tr("Zoom to the layer"),
                'pushButton_checkable_exploring_selecting': self.tr("Preview: hide the pixels outside the selection"),
                'pushButton_checkable_exploring_tracking': self.tr("Not used for raster layers"),
                'pushButton_checkable_exploring_linking_widgets': self.tr("Not used for raster layers"),
                'pushButton_exploring_reset_layer_properties': self.tr("Reset the raster selection"),
            },
            LayerKind.POINT_CLOUD: {
                'pushButton_exploring_identify': self.tr("Identify points on the map"),
                'pushButton_exploring_zoom': self.tr("Zoom to the layer"),
                'pushButton_checkable_exploring_selecting': self.tr("Live preview: show only the points kept by the selection"),
                'pushButton_checkable_exploring_tracking': self.tr("Not used for point cloud layers"),
                'pushButton_checkable_exploring_linking_widgets': self.tr("Not used for point cloud layers"),
                'pushButton_exploring_reset_layer_properties': self.tr("Reset the point cloud criteria"),
            },
        }.get(kind, {})
        for name, tip in tips.items():
            button = getattr(dw, name, None)
            self._call(button, 'setToolTip', tip)
            if name in ('pushButton_checkable_exploring_tracking', 'pushButton_checkable_exploring_linking_widgets'):
                self._call(button, 'setEnabled', False)
            else:
                self._call(button, 'setEnabled', True)
        selecting = getattr(dw, 'pushButton_checkable_exploring_selecting', None)
        if selecting is not None:
            try:
                selecting.blockSignals(True)
                selecting.setChecked(False)
            finally:
                selecting.blockSignals(False)

    def _current_panel(self):
        from ...core.domain.layer_kind import LayerKind
        if self._kind is LayerKind.RASTER:
            return self._raster_panel
        if self._kind is LayerKind.POINT_CLOUD:
            return self._pc_panel
        return None

    def _restore_panel_state(self, layer: Any) -> None:
        state = self._panel_states.get(layer.id())
        panel = self._current_panel()
        if state and panel is not None:
            try:
                panel.restore_state(state)
            except Exception as exc:
                logger.debug(f"[FM5] panel state not restored: {exc}")

    def _sync_layer_combo(self, layer: Any) -> None:
        combo = getattr(self.dockwidget, 'comboBox_filtering_current_layer', None)
        if combo is None:
            return
        try:
            if _same_layer(combo.currentLayer(), layer):
                return
            combo.blockSignals(True)
            try:
                combo.setLayer(layer)
            finally:
                combo.blockSignals(False)
        except Exception as exc:
            logger.debug(f"[FM5] layer combo not synchronized: {exc}")

    def _populate_filtering_targets(self, layer: Any) -> None:
        dw = self.dockwidget
        populate = getattr(dw, 'filtering_populate_layers_chekableCombobox', None) or \
            getattr(dw, 'filtering_populate_layers_checkable_combobox', None)
        if populate is not None:
            try:
                populate(layer)
                return
            except Exception as exc:
                logger.debug(f"[FM5] layers to filter not repopulated by the dock: {exc}")
        integration = getattr(dw, '_controller_integration', None)
        try:
            if integration is not None and integration.filtering_controller is not None:
                integration.filtering_controller.populate_layers_checkable_combobox(layer)
        except Exception as exc:
            logger.debug(f"[FM5] layers to filter not repopulated: {exc}")

    # === Panels ===

    def _connect_panels(self) -> None:
        raster, pc = self._raster_panel, self._pc_panel
        raster.bandChanged.connect(self._on_raster_band_changed)
        raster.selectionChanged.connect(self._on_raster_selection_changed)
        raster.previewToggled.connect(self._on_raster_preview_toggled)
        pc.criteriaChanged.connect(self._on_point_cloud_criteria_changed)

    def _populate_raster(self, layer: Any) -> None:
        try:
            from ...adapters.qgis.coverage_layers.raster_adapter import raster_reference, read_raster_summary
            summary = read_raster_summary(layer)
            self._raster_panel.set_summary(summary)
            self._raster_panel.set_reference(raster_reference(layer))
            self._refresh_histogram(layer, self._raster_panel.current_band())
        except Exception as exc:
            logger.warning(f"[FM5] raster panel not populated: {exc}", exc_info=True)

    def _refresh_histogram(self, layer: Any, band: int) -> None:
        from ...adapters.qgis.coverage_layers.raster_adapter import band_histogram
        key = (layer.source(), int(band))
        cached = self._histogram_cache.get(key)
        if cached is None:
            cached = band_histogram(self._base_raster(layer), band, bins=64)
            self._histogram_cache[key] = cached
        counts, minimum, maximum = cached
        self._raster_panel.set_histogram(band, counts, minimum, maximum)
        self._update_kept_ratio()

    def _base_raster(self, layer: Any):
        """The original raster when the layer shows a FilterMate derived source."""
        from ...adapters.qgis.coverage_layers.snapshots import registry
        snapshot = registry().get(layer.id())
        if snapshot is None:
            return layer
        from qgis.core import QgsRasterLayer
        base = QgsRasterLayer(snapshot.original_source, layer.name(), snapshot.original_provider)
        self._base_keepalive = base
        return base if base.isValid() else layer

    def _on_raster_band_changed(self, band: int) -> None:
        if self._active_layer is not None:
            try:
                self._refresh_histogram(self._active_layer, band)
            except Exception as exc:
                logger.debug(f"[FM5] histogram not refreshed: {exc}")

    def _update_kept_ratio(self) -> None:
        panel, layer = self._raster_panel, self._active_layer
        if panel is None or layer is None:
            return
        selection = panel.selection()
        cached = self._histogram_cache.get((layer.source(), panel.current_band()))
        if selection is None or cached is None or not cached[0]:
            panel.set_kept_ratio(None)
            return
        counts, minimum, maximum = cached
        total = float(sum(counts)) or 1.0
        width = (maximum - minimum) / len(counts) if counts else 1.0
        kept = 0
        from ...core.domain.raster_filter_criteria import RasterSelectionMode
        if selection.mode is RasterSelectionMode.EXPRESSION:
            panel.set_kept_ratio(None)
            return
        for index, count in enumerate(counts):
            centre = minimum + (index + 0.5) * width
            try:
                if selection.keeps(centre):
                    kept += count
            except ValueError:
                pass
        panel.set_kept_ratio(kept / total)

    def _on_raster_selection_changed(self) -> None:
        self._update_kept_ratio()
        panel = self._raster_panel
        selection = panel.selection() if panel is not None else None
        from ...core.domain.raster_filter_criteria import RasterSelectionMode
        if selection is not None and selection.mode is RasterSelectionMode.EXPRESSION:
            self._validate_raster_expression(selection.expression)
        if panel is not None and (panel.preview_enabled() or self._preview_active):
            self._apply_raster_preview()

    def _validate_raster_expression(self, expression: str) -> None:
        try:
            from qgis.analysis import QgsRasterCalcNode
            error = ''
            node = QgsRasterCalcNode.parseRasterCalcString(expression, error)
            ok = node is not None
            self._raster_panel.set_expression_status(ok, '' if ok else self.tr("Invalid raster calculator expression"))
        except Exception as exc:
            logger.debug(f"[FM5] raster expression not validated: {exc}")

    def _on_raster_preview_toggled(self, enabled: bool) -> None:
        selecting = getattr(self.dockwidget, 'pushButton_checkable_exploring_selecting', None)
        if selecting is not None and selecting.isChecked() != enabled:
            try:
                selecting.blockSignals(True)
                selecting.setChecked(enabled)
            finally:
                selecting.blockSignals(False)
        self._preview_active = bool(enabled)
        if enabled:
            self._apply_raster_preview()
        elif self._active_layer is not None:
            self._stop_preview(self._active_layer)

    def _apply_raster_preview(self) -> None:
        layer, panel = self._active_layer, self._raster_panel
        if layer is None or panel is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import apply_selection_preview
        selection = panel.selection()
        cached = self._histogram_cache.get((layer.source(), panel.current_band()))
        low, high = (cached[1], cached[2]) if cached else (None, None)
        if selection is not None:
            apply_selection_preview(layer, selection, low, high)

    def _populate_point_cloud(self, layer: Any) -> None:
        try:
            from ...adapters.qgis.point_cloud_layer_adapter import read_point_cloud_summary
            from ...adapters.qgis.coverage_layers import pdal_cli
            summary = read_point_cloud_summary(layer)
            self._pc_panel.populate(summary)
            self._pc_panel.set_current_subset(layer.subsetString())
            self._pc_panel.set_point_counts(None, getattr(summary, 'point_count', None))
            available = pdal_cli.is_available()
            self._pc_panel.set_hag_available(
                available, '' if available else self.tr("PDAL was not found: the height above a DTM needs the pdal executable"))
        except Exception as exc:
            logger.warning(f"[FM5] point cloud panel not populated: {exc}", exc_info=True)

    def _on_point_cloud_criteria_changed(self) -> None:
        selecting = getattr(self.dockwidget, 'pushButton_checkable_exploring_selecting', None)
        if selecting is not None and selecting.isChecked():
            self._apply_point_cloud_preview()

    def _apply_point_cloud_preview(self) -> None:
        layer, panel = self._active_layer, self._pc_panel
        if layer is None or panel is None:
            return
        from ...core.domain.cross_filter import combine_subset
        if self._preview_base_subset is None:
            self._preview_base_subset = layer.subsetString()
        expression = self._point_cloud_expression(include_hag=False)
        subset = combine_subset(self._preview_base_subset, expression, 'AND') if expression else self._preview_base_subset
        if not layer.setSubsetString(subset or ''):
            logger.debug(f"[FM5] preview expression rejected: {subset}")
        self._refresh_canvas(layer)

    def _stop_preview(self, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        try:
            if self._kind is LayerKind.RASTER:
                from ...adapters.qgis.coverage_layers.raster_adapter import clear_selection_preview
                clear_selection_preview(layer)
            elif self._preview_base_subset is not None:
                layer.setSubsetString(self._preview_base_subset)
        except Exception as exc:
            logger.debug(f"[FM5] preview not cleared: {exc}")
        self._preview_base_subset = None
        self._preview_active = False

    def _point_cloud_expression(self, include_hag: bool = True) -> str:
        panel = self._pc_panel
        if panel is None:
            return ''
        if include_hag:
            return (panel.expression() or '').strip()
        try:
            from ..widgets.coverage_panels.point_cloud_exploring_panel import build_point_cloud_expression
            return (build_point_cloud_expression(panel.state(), hag_available=False) or '').strip()
        except Exception as exc:
            logger.debug(f"[FM5] expression without height above ground unavailable: {exc}")
            return

    # === Exploring buttons ===

    def handle_exploring_action(self, action: str, checked: Optional[bool] = None) -> bool:
        """Run an EXPLORING button for the active coverage layer.

        Args:
            action: ``identify``, ``zoom``, ``select``, ``deselect`` or ``reset``.

        Returns:
            True when handled (the vector handler must stop).
        """
        from ...core.domain.layer_kind import LayerKind
        layer = self._active_layer
        if layer is None:
            return False
        try:
            if action == 'identify':
                if self._kind is LayerKind.RASTER:
                    self._toggle_pixel_tool()
                else:
                    self._identify_point_cloud()
            elif action == 'zoom':
                self._zoom_to(layer)
            elif action in ('select', 'deselect'):
                enabled = action == 'select'
                if self._kind is LayerKind.RASTER:
                    self._on_raster_preview_toggled(enabled)
                elif enabled:
                    self._apply_point_cloud_preview()
                else:
                    self._stop_preview(layer)
                    self._refresh_canvas(layer)
            elif action == 'backend':
                pass
            elif action == 'reset':
                self._stop_preview(layer)
                panel = self._current_panel()
                if panel is not None:
                    panel.reset()
                self._panel_states.pop(layer.id(), None)
        except Exception as exc:
            logger.warning(f"[FM5] exploring action '{action}' failed: {exc}", exc_info=True)
        return True

    def _iface(self):
        app = self._app()
        iface = getattr(app, 'iface', None) or getattr(self.dockwidget, 'iface', None)
        if iface is None:
            try:
                from qgis.utils import iface as qgis_iface
                iface = qgis_iface
            except ImportError:
                iface = None
        return iface

    def _zoom_to(self, layer: Any) -> None:
        iface = self._iface()
        if iface is None:
            return
        from qgis.core import QgsCoordinateTransform, QgsProject
        canvas = iface.mapCanvas()
        extent = layer.extent()
        try:
            transform = QgsCoordinateTransform(layer.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
            extent = transform.transformBoundingBox(extent)
        except Exception:
            pass
        canvas.setExtent(extent)
        canvas.refresh()

    def _identify_point_cloud(self) -> None:
        iface = self._iface()
        if iface is None:
            return
        try:
            iface.setActiveLayer(self._active_layer)
            iface.actionIdentify().trigger()
        except Exception as exc:
            logger.debug(f"[FM5] identify tool not activated: {exc}")

    def _toggle_pixel_tool(self) -> None:
        iface = self._iface()
        if iface is None:
            return
        canvas = iface.mapCanvas()
        if self._pixel_tool is not None and canvas.mapTool() is self._pixel_tool:
            self._deactivate_pixel_tool()
            return
        from ..tools.pixel_picker_tool import PixelPickerTool
        if self._pixel_tool is None:
            self._pixel_tool = PixelPickerTool(canvas)
            self._pixel_tool.picked.connect(self._on_pixel_picked)
        self._previous_map_tool = canvas.mapTool()
        canvas.setMapTool(self._pixel_tool)

    def _deactivate_pixel_tool(self) -> None:
        iface = self._iface()
        if iface is None or self._pixel_tool is None:
            return
        canvas = iface.mapCanvas()
        if canvas.mapTool() is self._pixel_tool:
            if self._previous_map_tool is not None:
                canvas.setMapTool(self._previous_map_tool)
            else:
                canvas.unsetMapTool(self._pixel_tool)
        self._previous_map_tool = None

    def _on_pixel_picked(self, point: Any, extend: bool) -> None:
        layer = self._active_layer
        if layer is None or self._raster_panel is None:
            return
        from qgis.core import QgsCoordinateTransform, QgsProject
        from ...adapters.qgis.coverage_layers.raster_adapter import identify_values
        iface = self._iface()
        try:
            transform = QgsCoordinateTransform(iface.mapCanvas().mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
            layer_point = transform.transform(point)
        except Exception:
            layer_point = point
        values = identify_values(self._base_raster(layer), layer_point)
        self._raster_panel.set_pixel_values(layer_point.x(), layer_point.y(), values, extend)

    # === FILTERING request ===

    def _filtering_settings(self) -> dict:
        """Read the FILTERING widgets exactly as the vector engine does."""
        dw = self.dockwidget

        def checked(name, default=False):
            widget = getattr(dw, name, None)
            try:
                return bool(widget.isChecked()) if widget is not None else default
            except Exception:
                return default

        predicates: List[str] = []
        if checked('pushButton_checkable_filtering_geometric_predicates'):
            combo = getattr(dw, 'comboBox_filtering_geometric_predicates', None)
            try:
                predicates = list(combo.checkedItems()) if combo is not None else []
            except Exception:
                predicates = []
        buffer_value = 0.0
        if checked('pushButton_checkable_filtering_buffer_value'):
            spin = getattr(dw, 'mQgsDoubleSpinBox_filtering_buffer_value', None)
            buffer_value = float(spin.value()) if spin is not None else 0.0
        segments, buffer_type = 5, 'Round'
        if checked('pushButton_checkable_filtering_buffer_type'):
            seg = getattr(dw, 'mQgsSpinBox_filtering_buffer_segments', None)
            typ = getattr(dw, 'comboBox_filtering_buffer_type', None)
            segments = int(seg.value()) if seg is not None else 5
            buffer_type = typ.currentText() if typ is not None else 'Round'
        source_op = other_op = None
        if checked('pushButton_checkable_filtering_current_layer_combine_operator'):
            to_operator = getattr(dw, '_index_to_combine_operator', None)
            for name, attr in (('comboBox_filtering_source_layer_combine_operator', 'source'),
                               ('comboBox_filtering_other_layers_combine_operator', 'other')):
                combo = getattr(dw, name, None)
                if combo is None:
                    continue
                value = None
                try:
                    value = to_operator(combo.currentIndex()) if to_operator is not None else combo.currentText()
                except Exception:
                    value = combo.currentText()
                if attr == 'source':
                    source_op = value or None
                else:
                    other_op = value or None
        targets: List[str] = []
        if checked('pushButton_checkable_filtering_layers_to_filter'):
            try:
                targets = list(dw.get_layers_to_filter() or [])
            except Exception:
                targets = []
        coverage = float(self._coverage_spin.value()) if self._coverage_spin is not None else 0.0
        return dict(predicates=tuple(predicates), buffer_value=buffer_value, buffer_segments=segments,
                    buffer_type=buffer_type, source_operator=source_op, other_operator=other_op,
                    targets=targets, coverage_min=coverage)

    def _target_specs(self, layer_ids, exclude_id: str = ''):
        from qgis.core import QgsProject
        from ...core.domain.cross_filter import TargetSpec
        specs = []
        for layer_id in layer_ids or []:
            if layer_id == exclude_id:
                continue
            layer = QgsProject.instance().mapLayer(layer_id)
            kind = _kind_of(layer)
            if layer is not None and kind.value != 'other':
                specs.append(TargetSpec(layer_id, kind))
        return specs

    def _build_request(self, source: Any, kind: Any, settings: dict, targets) -> Any:
        from ...core.domain.cross_filter import CrossFilterRequest
        return CrossFilterRequest(
            source_layer_id=source.id(), source_kind=kind, targets=tuple(targets),
            predicates=settings['predicates'], buffer_value=settings['buffer_value'],
            buffer_segments=settings['buffer_segments'], buffer_type=settings['buffer_type'],
            coverage_min=settings['coverage_min'], other_layers_combine_operator=settings['other_operator'])

    def _on_coverage_min_changed(self, value: int) -> None:
        layer = self._active_layer
        if layer is None:
            return
        try:
            self.dockwidget.PROJECT_LAYERS[layer.id()]['filtering']['coverage_min'] = int(value)
        except (KeyError, TypeError, AttributeError):
            pass

    def _load_coverage_min(self, layer: Any) -> None:
        if self._coverage_spin is None:
            return
        try:
            value = int(self.dockwidget.PROJECT_LAYERS[layer.id()]['filtering'].get('coverage_min', 0))
        except (KeyError, TypeError, AttributeError, ValueError):
            value = 0
        self._coverage_spin.blockSignals(True)
        self._coverage_spin.setValue(value)
        self._coverage_spin.blockSignals(False)

    # === Dock actions (coverage source) ===

    def handle_task(self, task_name: str) -> bool:
        """Run a dock action when the current layer is a raster or a point cloud."""
        layer = self._active_layer
        if layer is None:
            return False
        if not _same_layer(getattr(self.dockwidget, 'current_layer', None), layer):
            self.deactivate()
            return False
        if task_name not in COVERAGE_TASKS:
            logger.warning(f"[FM5] unknown task '{task_name}' on a coverage layer, ignored")
            return True
        if task_name == 'export':
            exporting = self._layers_checked_for_export()
            if exporting:
                return False  # the EXPORTING tab handles vector, raster and point cloud layers alike
        if task_name != 'export' and self.is_running():
            _, show_warning = _feedback()
            show_warning(self.tr("A FilterMate task is still running: wait for it to finish"))
            return True
        try:
            if task_name == 'filter':
                self._run_filter(layer)
            elif task_name in ('unfilter', 'reset'):
                self._run_unfilter(layer, reset=task_name == 'reset')
            elif task_name == 'undo':
                self._finish_restore(self.service.undo(layer.id()))
            elif task_name == 'redo':
                self._finish_restore(self.service.redo(layer.id()))
            elif task_name == 'export':
                self._run_export([layer.id()])
        except Exception as exc:
            logger.error(f"[FM5] task '{task_name}' failed: {exc}", exc_info=True)
            _, show_warning = _feedback()
            show_warning(self.tr("FilterMate task failed: {0}").format(exc))
        return True

    def is_running(self) -> bool:
        task = self._running_task
        if task is None:
            return False
        try:
            from qgis.core import QgsTask
            return task.status() in (QgsTask.TaskStatus.Queued, QgsTask.TaskStatus.OnHold, QgsTask.TaskStatus.Running)
        except Exception:
            return False

    def _layers_checked_for_export(self) -> List[str]:
        try:
            return list(self.dockwidget.get_layers_to_export() or [])
        except Exception:
            return []

    def _run_filter(self, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        from ...core.domain.cross_filter import combine_subset
        from ...core.domain.filter_state import CrossOperation
        from ...adapters.qgis.coverage_layers.snapshots import registry, take_snapshot
        show_info, show_warning = _feedback()
        settings = self._filtering_settings()
        targets = self._target_specs(settings['targets'], exclude_id=layer.id())
        request = self._build_request(layer, self._kind, settings, targets)
        registry().install()
        self._stop_preview(layer)
        if self._kind is LayerKind.RASTER:
            selection = self._raster_panel.selection()
            if selection is None:
                show_warning(self.tr("Select pixels first: a value range, classes or a raster expression"))
                return
            from ...adapters.qgis.coverage_layers.source_jobs import RasterSourceJob
            source_job = RasterSourceJob(layer, selection, int(_option('raster_selection_max_pixels', 4000000)))
            if not targets:
                before = source_job.before
                after = source_job.apply(layer)
                if after is not None:
                    self.service.history.push(CrossOperation(layer.id(), ((before, after),), 'raster selection'))
                self._after_run(layer, [], self.tr("Raster filtered: {0}").format(selection.describe()))
                return
        else:
            expression = self._point_cloud_expression()
            hag = self._pc_panel.hag_settings() if self._pc_panel is not None else None
            if hag is not None and 'HeightAboveGround' not in self._point_cloud_attributes(layer):
                self._prepare_height_above_ground(layer, hag, lambda: self._run_filter(layer))
                return
            before = take_snapshot(layer, LayerKind.POINT_CLOUD)
            source_op = settings['source_operator']
            if expression:
                subset = combine_subset(before.subset, expression, source_op)
                if not layer.setSubsetString(subset):
                    show_warning(self.tr("The point cloud expression was rejected: {0}").format(subset))
                    return
            elif not targets:
                show_warning(self.tr("Select points first: classes, attribute ranges or an expression"))
                return
            siblings = self._apply_to_sibling_tiles(layer, expression, source_op) if self._pc_panel.apply_to_tiles() else []
            if not targets:
                after = take_snapshot(layer, LayerKind.POINT_CLOUD)
                changes = (((before, after),) if not after.same_state(before) else ()) + tuple(siblings)
                if changes:
                    self.service.history.push(CrossOperation(layer.id(), changes, 'point cloud selection'))
                self._after_run(layer, [], self.tr("Point cloud filtered: {0}").format(layer.subsetString()))
                return
            from ...adapters.qgis.coverage_layers.source_jobs import PointCloudSourceJob
            if siblings:
                self.service.history.push(CrossOperation(layer.id(), tuple(siblings), 'point cloud tiles'))
            source_job = PointCloudSourceJob(layer, float(_option('point_cloud_footprint_resolution', 2.0)), before=before)
        self._start_task(request, source_job)

    def _point_cloud_attributes(self, layer: Any) -> List[str]:
        try:
            return [attribute.name() for attribute in layer.attributes().attributes()]
        except Exception:
            return []

    def _apply_to_sibling_tiles(self, layer: Any, expression: str, operator: Optional[str]) -> list:
        """Apply the same selection to the point clouds of the same folder (LiDAR HD tiles).

        The folder is the one of the ORIGINAL source (a derived layer lives in
        the cache). Returns the (before, after) snapshots for the history.
        """
        import os
        from qgis.core import QgsProject
        from ...core.domain.cross_filter import combine_subset
        from ...core.domain.layer_kind import LayerKind
        from ...adapters.qgis.coverage_layers.snapshots import take_snapshot
        if not expression:
            return []
        try:
            folder = os.path.dirname(take_snapshot(layer, LayerKind.POINT_CLOUD).pristine_source)
        except Exception:
            return []
        changes = []
        for other in QgsProject.instance().mapLayers().values():
            if other.id() == layer.id() or _kind_of(other) is not LayerKind.POINT_CLOUD:
                continue
            try:
                before = take_snapshot(other, LayerKind.POINT_CLOUD)
                if os.path.dirname(before.pristine_source) != folder:
                    continue
                if other.setSubsetString(combine_subset(other.subsetString(), expression, operator)):
                    other.triggerRepaint()
                    changes.append((before, take_snapshot(other, LayerKind.POINT_CLOUD)))
            except Exception as exc:
                logger.debug(f"[FM5] sibling tile '{other.name()}' not filtered: {exc}")
        return changes

    def _start_task(self, request: Any, source_job: Any) -> None:
        show_info, _ = _feedback()
        dw = self.dockwidget
        layer_name = source_job.layer_name
        self._set_busy(True)

        def done(task, result):
            if getattr(self, '_torn_down', False):
                return
            self._set_busy(False)
            self._running_task = None
            layer = self._map_layer(source_job.layer_id)
            if not result:
                # Nothing was applied: put back the point cloud selection subset
                # set before the task, so the source is not left filtered
                # without a history entry.
                self._rollback_source(source_job, layer)
                _, show_warning = _feedback()
                show_warning(self.tr("Filter not applied: {0}").format(task.error or self.tr("canceled")))
                self._after_run(layer, [], '')
                return
            failures = [o for o in task.outcomes if not o.success]
            parts = [self.tr("{0} target(s) filtered").format(len(task.outcomes) - len(failures))]
            if failures:
                parts.append(self.tr("{0} failed: {1}").format(len(failures), '; '.join(f.message for f in failures if f.message)[:300]))
            self._after_run(layer, task.outcomes, ' — '.join(parts))

        try:
            self._running_task = self.service.run(request, source_job, on_done=done)
        except Exception:
            self._set_busy(False)
            self._rollback_source(source_job, self._map_layer(source_job.layer_id))
            raise
        show_info(self.tr("FilterMate: filtering from '{0}'…").format(layer_name))
        try:
            dw.launchingTask  # noqa: B018 - presence check only
        except AttributeError:
            pass

    @staticmethod
    def _rollback_source(source_job: Any, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        if layer is None or getattr(source_job, 'kind', None) is not LayerKind.POINT_CLOUD:
            return
        try:
            from ...adapters.qgis.coverage_layers.snapshots import restore_snapshot
            restore_snapshot(layer, source_job.before)
        except Exception as exc:
            logger.warning(f"[FM5] point cloud selection not rolled back: {exc}")

    def _set_busy(self, busy: bool) -> None:
        button = getattr(self.dockwidget, 'pushButton_action_filter', None)
        self._call(button, 'setEnabled', not busy)

    def _after_run(self, layer: Any, outcomes, message: str) -> None:
        show_info, _ = _feedback()
        self._refresh_canvas(layer)
        self._refresh_counts(layer)
        self.update_undo_redo_buttons()
        if message:
            show_info(message)

    def _refresh_counts(self, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        if layer is None:
            return
        try:
            if self._kind is LayerKind.POINT_CLOUD and self._pc_panel is not None:
                self._pc_panel.set_current_subset(layer.subsetString())
        except Exception:
            pass

    def _run_unfilter(self, layer: Any, reset: bool) -> None:
        settings = self._filtering_settings()
        ids = [layer.id()] + [t.layer_id for t in self._target_specs(settings['targets'], exclude_id=layer.id())]
        kinds = {layer_id: _kind_of(self._map_layer(layer_id)) for layer_id in ids}
        self._stop_preview(layer)
        restored = self.service.unfilter(layer.id(), ids, kinds)
        if reset:
            panel = self._current_panel()
            if panel is not None:
                panel.reset()
            self._panel_states.pop(layer.id(), None)
        self._finish_restore(restored)

    def _finish_restore(self, layer_ids: List[str]) -> None:
        show_info, _ = _feedback()
        for layer_id in layer_ids or []:
            self._refresh_canvas(self._map_layer(layer_id))
        self._refresh_counts(self._active_layer)
        self.update_undo_redo_buttons()
        show_info(self.tr("{0} layer(s) restored").format(len(layer_ids or [])))

    # === Export ===

    def _run_export(self, layer_ids: List[str], folder: Optional[str] = None, crs: Any = None) -> Any:
        """Export coverage layers as they are filtered, in a background task.

        Returns:
            The started task (None when nothing is exported).
        """
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers import exporters
        from ...core.domain.layer_kind import LayerKind
        show_info, show_warning = _feedback()
        if folder is None:
            folder = self._ask_folder()
            if not folder:
                return None
        jobs = []
        for layer_id in layer_ids:
            layer = self._map_layer(layer_id)
            kind = _kind_of(layer)
            if layer is None:
                continue
            try:
                if kind is LayerKind.RASTER:
                    fmt = str(_option('raster_export_format', 'COG'))
                    jobs.append(exporters.RasterExportJob(layer, exporters.output_path(folder, layer.name(), '.tif'), fmt, crs))
                elif kind is LayerKind.POINT_CLOUD:
                    fmt = str(_option('point_cloud_export_format', 'LAZ'))
                    extension = exporters.POINT_CLOUD_FORMATS.get(fmt, '.laz')
                    jobs.append(exporters.PointCloudExportJob(layer, exporters.output_path(folder, layer.name(), extension), fmt, crs))
            except Exception as exc:
                show_warning(self.tr("'{0}' not exported: {1}").format(layer.name(), exc))
        if not jobs:
            return None

        def done(results):
            written = [r.path for r in results if r.success]
            failed = [f"{r.path}: {r.message}" for r in results if not r.success]
            if written:
                show_info(self.tr("Exported: {0}").format(', '.join(written)))
            if failed:
                show_warning(self.tr("Export failed: {0}").format('; '.join(failed)))
            self.last_export_results = results
            self._export_task = None

        task = exporters.make_export_task(jobs, done)
        self._export_task = task
        QgsApplication.taskManager().addTask(task)
        show_info(self.tr("Exporting {0} layer(s)…").format(len(jobs)))
        return task

    def _ask_folder(self) -> str:
        try:
            from qgis.PyQt.QtWidgets import QFileDialog
            return QFileDialog.getExistingDirectory(self.dockwidget, self.tr("Export folder"))
        except Exception:
            return ''

    # === Vector source with coverage targets ===

    def split_coverage_targets(self, layer_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Split target ids into (vector ids, coverage ids)."""
        vector_ids, coverage_ids = [], []
        for layer_id in layer_ids or []:
            if self.is_coverage(self._map_layer(layer_id)):
                coverage_ids.append(layer_id)
            else:
                vector_ids.append(layer_id)
        return vector_ids, coverage_ids

    def run_vector_source_task(self, task_name: str, source: Any, coverage_ids: List[str]) -> None:
        """Mirror a vector task on the raster / point cloud targets of the vector source."""
        if source is None:
            return
        source_id = source.id()
        try:
            if task_name == 'filter':
                runs = self._linked_runs.setdefault(source_id, [])
                runs.append(False)  # set to True once the cross task really changed a layer
                self._linked_redo[source_id] = []
                if coverage_ids and self._vector_engine_filters_targets():
                    self._run_vector_source_filter(source, coverage_ids, run_index=len(runs) - 1)
            elif task_name in ('unfilter', 'reset'):
                # Same history rules as the vector engine: Unfilter records
                # nothing (a later Undo goes back to before the last filter, for
                # every layer), Reset clears the history.
                if coverage_ids:
                    kinds = {i: _kind_of(self._map_layer(i)) for i in coverage_ids}
                    self._finish_restore(self.service.unfilter(source_id, coverage_ids, kinds, record=False))
                if task_name == 'reset':
                    self._linked_runs[source_id] = []
                    self._linked_redo[source_id] = []
                    self.service.history.clear_source(source_id)
            elif task_name == 'undo':
                runs = self._linked_runs.get(source_id) or []
                if runs:
                    linked = runs.pop()
                    self._linked_redo.setdefault(source_id, []).append(linked)
                    if linked:
                        self._finish_restore(self.service.undo(source_id))
            elif task_name == 'redo':
                redo = self._linked_redo.get(source_id) or []
                if redo:
                    linked = redo.pop()
                    self._linked_runs.setdefault(source_id, []).append(linked)
                    if linked:
                        self._finish_restore(self.service.redo(source_id))
        except Exception as exc:
            logger.warning(f"[FM5] coverage targets of '{self._layer_name(source)}' not processed: {exc}", exc_info=True)

    def _vector_engine_filters_targets(self) -> bool:
        """The vector engine only filters distant layers when both buttons are on."""
        dw = self.dockwidget
        for name in ('pushButton_checkable_filtering_layers_to_filter', 'pushButton_checkable_filtering_geometric_predicates'):
            button = getattr(dw, name, None)
            try:
                if button is not None and not button.isChecked():
                    return False
            except Exception:
                return False
        return True

    def _run_vector_source_filter(self, source: Any, coverage_ids: List[str], run_index: Optional[int] = None) -> bool:
        _, show_warning = _feedback()
        features = self._vector_source_features(source)
        if not features:
            show_warning(self.tr("Raster / point cloud targets skipped: no source feature selected in EXPLORING"))
            return False
        from ...core.domain.layer_kind import LayerKind
        from ...adapters.qgis.coverage_layers.source_jobs import VectorSourceJob
        from ...adapters.qgis.coverage_layers.snapshots import registry
        settings = self._filtering_settings()
        targets = self._target_specs(coverage_ids, exclude_id=source.id())
        if not targets:
            return False
        registry().install()
        request = self._build_request(source, LayerKind.VECTOR, settings, targets)
        job = VectorSourceJob(source, features)

        source_id = source.id()

        def done(task, result):
            if getattr(self, '_torn_down', False):
                return
            runs = self._linked_runs.get(source_id) or []
            if task.changes and run_index is not None and run_index < len(runs):
                runs[run_index] = True
            if not result:
                message = self.tr("Raster / point cloud targets not filtered: {0}").format(task.error or self.tr("canceled"))
            else:
                failures = [o for o in task.outcomes if not o.success]
                message = self.tr("{0} raster / point cloud target(s) filtered").format(len(task.outcomes) - len(failures))
                if failures:
                    message += ' — ' + '; '.join(f.message for f in failures if f.message)[:300]
            self._after_run(self._map_layer(source_id), task.outcomes, message)

        self.service.run(request, job, on_done=done)
        return True

    def _vector_source_features(self, source: Any) -> list:
        """Features of the EXPLORING selection, with geometry."""
        from qgis.core import QgsExpression, QgsFeature, QgsFeatureRequest
        dw = self.dockwidget
        features, expression = [], ''
        try:
            features, expression = dw.get_current_features()
        except Exception as exc:
            logger.debug(f"[FM5] EXPLORING features unavailable: {exc}")
        with_geometry = [f for f in (features or []) if isinstance(f, QgsFeature) and f.hasGeometry()]
        if with_geometry:
            return with_geometry
        ids = [f.id() if isinstance(f, QgsFeature) else f for f in (features or [])]
        request = None
        if ids and all(isinstance(i, int) for i in ids):
            request = QgsFeatureRequest().setFilterFids(ids)
        elif expression:
            request = QgsFeatureRequest(QgsExpression(expression))
        if request is None:
            return []
        request.setLimit(MAX_SOURCE_FEATURES)
        return [f for f in source.getFeatures(request) if f.hasGeometry()]

    def export_coverage_layers(self, layer_ids: List[str], folder: Optional[str], crs: Any = None) -> Any:
        """Export the raster / point cloud layers checked in EXPORTING (asks for a folder when None)."""
        return self._run_export(layer_ids, folder or None, crs)

    # === Undo / redo buttons ===

    def can_undo(self) -> bool:
        layer = self._active_layer
        return layer is not None and self.service.can_undo(layer.id())

    def can_redo(self) -> bool:
        layer = self._active_layer
        return layer is not None and self.service.can_redo(layer.id())

    def update_undo_redo_buttons(self) -> None:
        if self._active_layer is None:
            self._call(self._app(), 'update_undo_redo_buttons')
            return
        dw = self.dockwidget
        self._call(getattr(dw, 'pushButton_action_undo_filter', None), 'setEnabled', self.can_undo())
        self._call(getattr(dw, 'pushButton_action_redo_filter', None), 'setEnabled', self.can_redo())

    # === Height above ground ===

    def _prepare_height_above_ground(self, layer: Any, hag: Tuple[str, float], then) -> None:
        """Derive the point cloud with a HeightAboveGround dimension (PDAL), then continue."""
        from ...adapters.qgis.coverage_layers.hag_task import HeightAboveGroundTask
        from qgis.core import QgsApplication
        show_info, show_warning = _feedback()
        dem = self._map_layer(hag[0])
        if dem is None:
            show_warning(self.tr("Choose the DTM raster used for the height above ground"))
            return
        task = HeightAboveGroundTask(layer, dem)

        def finished(ok, message):
            self._hag_task = None
            self._set_busy(False)
            if not ok:
                show_warning(self.tr("Height above ground not computed: {0}").format(message))
                return
            if task.after is not None:
                from ...core.domain.filter_state import CrossOperation
                self.service.history.push(CrossOperation(layer.id(), ((task.before, task.after),), 'height above ground'))
            self._populate_point_cloud(layer)
            then()

        task.done.connect(finished)
        self._hag_task = task
        self._set_busy(True)
        QgsApplication.taskManager().addTask(task)
        show_info(self.tr("Computing the height above '{0}' with PDAL…").format(dem.name()))

    # === Helpers ===

    def _app(self) -> Any:
        dw = self.dockwidget
        return getattr(dw, 'filter_mate_app', None) or getattr(dw, 'app', None)

    @staticmethod
    def _map_layer(layer_id: str):
        try:
            from qgis.core import QgsProject
            return QgsProject.instance().mapLayer(layer_id)
        except Exception:
            return None

    def _refresh_canvas(self, layer: Any) -> None:
        if layer is not None:
            self._call(layer, 'triggerRepaint')
        iface = self._iface()
        try:
            if iface is not None:
                iface.mapCanvas().refresh()
        except Exception:
            pass

    @staticmethod
    def _call(target: Any, method: str, *args: Any) -> None:
        if target is None:
            return
        try:
            func = getattr(target, method, None)
        except Exception:
            return
        if func is None:
            return
        try:
            func(*args)
        except Exception as exc:
            logger.debug(f"[FM5] {method} failed: {exc}")

    @staticmethod
    def _layer_name(layer: Any) -> str:
        try:
            return layer.name()
        except (RuntimeError, AttributeError):
            return "?"
