"""
PointCloudUIController - point cloud filter panel of the filtering tab.

Dormant until the current layer is a ``QgsPointCloudLayer`` (feature flag
``APP.OPTIONS.POINT_CLOUD.enabled``, QGIS 3.26 or newer). It then swaps the
vector filtering widgets for the point cloud panel and routes the dock's
action buttons (filter, unfilter, reset, undo, redo, export) to
``PointCloudFilterService`` instead of ``FilterEngineTask``.
"""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from .base_controller import BaseController

if TYPE_CHECKING:
    from filter_mate_dockwidget import FilterMateDockWidget

logger = logging.getLogger(__name__)

POINT_CLOUD_TASKS = ('filter', 'unfilter', 'reset', 'undo', 'redo', 'export')
SOURCE_ROW_LAYOUT_NAME = 'horizontalLayout_filtering_source_layer'
VALUES_LAYOUT_NAME = 'verticalLayout_filtering_values'
POINT_CLOUD_WIDGET_INDEX = 1
HIDDEN_DOCK_WIDGETS = ('widget_filtering_keys', 'checkBox_filtering_use_centroids_source_layer')


def _capability_is_point_cloud(layer: Any) -> bool:
    """True when the capability module recognizes the layer as a point cloud."""
    try:
        from ...adapters.qgis.point_cloud_capability import is_point_cloud_layer
    except ImportError:
        return False
    try:
        return bool(is_point_cloud_layer(layer))
    except Exception as e:
        logger.debug(f"[PC] capability check failed: {e}")
        return False


def _layer_is_valid(layer: Any) -> bool:
    """Validity check that never raises (deleted C++ object included)."""
    if layer is None:
        return False
    try:
        from ...infrastructure.utils import is_layer_valid
    except ImportError:
        is_layer_valid = None
    if is_layer_valid is not None:
        try:
            return bool(is_layer_valid(layer))
        except Exception:
            return False
    try:
        layer.id()
        return bool(layer.isValid())
    except (RuntimeError, AttributeError):
        return False


def _feedback() -> Tuple[Callable[..., None], Callable[..., None]]:
    """Return ``(show_info, show_warning)``, no-ops when the helpers are unavailable."""
    try:
        from ...infrastructure.feedback import show_info, show_warning
        return show_info, show_warning
    except ImportError:
        return (lambda *args, **kwargs: None), (lambda *args, **kwargs: None)


def _same_layer(first: Any, second: Any) -> bool:
    if first is second:
        return True
    if first is None or second is None:
        return False
    try:
        return first.id() == second.id()
    except (RuntimeError, AttributeError):
        return False


class PointCloudUIController(BaseController):
    """Controller of the point cloud filter panel."""

    def __init__(self, dockwidget: 'FilterMateDockWidget', filter_service: Any = None, signal_manager: Any = None) -> None:
        """
        Initialize the controller.

        Args:
            dockwidget: Main dockwidget reference.
            filter_service: Vector filter service (unused, kept for the registry signature).
            signal_manager: Optional signal manager.
        """
        super().__init__(dockwidget, filter_service, signal_manager)
        self._widget: Any = None
        self._active_layer: Any = None
        self._saved_visibility: Dict[Any, bool] = {}
        self._saved_layers_to_filter_checked: Optional[bool] = None
        self._service: Any = None
        self._subset_slot: Optional[Callable[[], None]] = None

    # === Lifecycle ===

    def setup(self) -> None:
        """Register the controller; the panel is built lazily on first use.

        Building and inserting a Qt widget into the vector layout even when
        the feature flag is off (or before it is ever toggled on in this
        session) has no upside: the panel is created on the first point
        cloud layer selection instead, see ``_ensure_widget``.
        """
        logger.debug("PointCloudUIController setup complete (panel deferred)")

    def _ensure_widget(self) -> Any:
        """Create the panel and insert it under the source layer row, once."""
        if self._widget is not None:
            return self._widget
        dw = self.dockwidget
        try:
            from ..widgets.point_cloud_filter_widget import PointCloudFilterWidget
            widget = PointCloudFilterWidget(dw)
        except Exception as e:
            logger.warning(f"[PC] point cloud filter panel unavailable: {e}")
            return None
        layout = getattr(dw, VALUES_LAYOUT_NAME, None)
        if layout is not None:
            try:
                layout.insertWidget(POINT_CLOUD_WIDGET_INDEX, widget)
            except Exception as e:
                logger.warning(f"[PC] panel not inserted in {VALUES_LAYOUT_NAME}: {e}")
        try:
            widget.setVisible(False)
        except Exception as e:
            logger.debug(f"[PC] panel initial visibility not set: {e}")
        self._widget = widget
        self._ensure_service()
        logger.debug("PointCloudUIController panel created")
        return widget

    def teardown(self) -> None:
        """Restore the vector widgets, remove the panel and drop the connections."""
        self.deactivate()
        widget, self._widget = self._widget, None
        if widget is not None:
            layout = getattr(self.dockwidget, VALUES_LAYOUT_NAME, None)
            try:
                if layout is not None:
                    layout.removeWidget(widget)
                widget.deleteLater()
            except Exception as e:
                logger.debug(f"[PC] panel removal failed: {e}")
        self._service = None
        self._disconnect_all_signals()

    @property
    def active_layer(self) -> Any:
        """Point cloud layer the panel is bound to, or None."""
        return self._active_layer

    @property
    def widget(self) -> Any:
        """The ``PointCloudFilterWidget`` instance, or None when unavailable."""
        return self._widget

    # === Layer change ===

    def is_point_cloud(self, layer: Any) -> bool:
        """True when the layer is a filterable point cloud (flag on, QGIS 3.26+)."""
        return layer is not None and _capability_is_point_cloud(layer)

    def on_current_layer_changed(self, layer: Any) -> bool:
        """
        Take over the layer change when the new layer is a point cloud.

        Args:
            layer: New current layer.

        Returns:
            True when the change was handled here (the vector chain must stop).
        """
        if self.is_point_cloud(layer):
            if self._ensure_widget() is None:
                logger.warning("[PC] point cloud layer selected but the panel is unavailable")
                return False
            self.activate(layer)
            return True
        if self._active_layer is not None:
            self.deactivate()
        return False

    def activate(self, layer: Any) -> None:
        """
        Bind the panel to the point cloud layer and hide the vector widgets.

        Args:
            layer: Point cloud layer.
        """
        dw = self.dockwidget
        if self._active_layer is not None and not _same_layer(self._active_layer, layer):
            self._disconnect_subset_signal()
        self._disconnect_previous_vector_selection(dw, layer)
        try:
            dw.current_layer = layer
        except Exception as e:
            logger.warning(f"[PC] current_layer not updated: {e}")
        self._populate_panel(layer)
        if self._active_layer is None:
            self._save_visibility()
        self._apply_point_cloud_layout()
        self._sync_layer_combo(layer)
        self._call(getattr(dw, 'currentLayerChanged', None), 'emit')
        self._update_undo_redo_buttons()
        self._connect_subset_signal(layer)
        self._active_layer = layer
        logger.info(f"[PC] point cloud layer active: {self._layer_name(layer)}")

    @staticmethod
    def _disconnect_previous_vector_selection(dw: Any, incoming_layer: Any) -> None:
        """Disconnect the outgoing vector layer's ``selectionChanged``.

        ``current_layer_changed`` returns as soon as this controller takes
        over, so ``_validate_and_prepare_layer`` (which normally does this
        disconnect) never runs when switching from a vector layer to a point
        cloud: without this, the old layer keeps a dangling connection to
        ``on_layer_selection_changed``.
        """
        old_layer = getattr(dw, 'current_layer', None)
        if old_layer is None or _same_layer(old_layer, incoming_layer):
            return
        if getattr(dw, 'current_layer_selection_connection', None) is None:
            return
        try:
            old_layer.selectionChanged.disconnect(dw.on_layer_selection_changed)
        except (TypeError, RuntimeError, AttributeError) as e:
            logger.debug(f"[PC] previous layer selectionChanged not disconnected: {e}")
        dw.current_layer_selection_connection = None

    def deactivate(self) -> None:
        """Restore the vector widgets and unbind the panel."""
        if self._active_layer is None and not self._saved_visibility:
            return
        self._disconnect_subset_signal()
        self._restore_visibility()
        self._call(self._widget, 'setVisible', False)
        dw = self.dockwidget
        self._call(getattr(dw, 'frame_exploring', None), 'setEnabled', True)
        button = getattr(dw, 'pushButton_checkable_filtering_layers_to_filter', None)
        if button is not None:
            self._call(button, 'setEnabled', True)
            if self._saved_layers_to_filter_checked is not None:
                try:
                    button.blockSignals(True)
                    button.setChecked(self._saved_layers_to_filter_checked)
                except Exception as e:
                    logger.debug(f"[PC] layers_to_filter button state not restored: {e}")
                finally:
                    try:
                        button.blockSignals(False)
                    except Exception:
                        pass
        self._saved_layers_to_filter_checked = None
        self._active_layer = None
        logger.debug("[PC] point cloud panel deactivated")

    # === Tasks ===

    def handle_task(self, task_name: str) -> bool:
        """
        Run a dock action on the active point cloud layer.

        Args:
            task_name: 'filter', 'unfilter', 'reset', 'undo', 'redo' or 'export'.

        Returns:
            True when the task was handled here (the vector task path must stop).
        """
        layer = self._active_layer
        if layer is None:
            return False
        if task_name not in POINT_CLOUD_TASKS:
            # A point cloud is active: let the vector engine run on it would
            # crash on the first vector-only API call, so this is swallowed
            # here rather than falling through.
            logger.warning(f"[PC] unknown task '{task_name}' on the active point cloud layer, ignored")
            return True
        if not _layer_is_valid(layer):
            logger.warning("[PC] the active point cloud layer is gone, panel released")
            self._release_deleted_layer(layer)
            return False
        if not _same_layer(getattr(self.dockwidget, 'current_layer', None), layer):
            logger.warning("[PC] the dock's current layer is no longer the point cloud, panel released")
            self.deactivate()
            return False
        try:
            self._run_task(task_name, layer)
        except Exception as e:
            logger.error(f"[PC] task '{task_name}' failed: {e}", exc_info=True)
            _, show_warning = _feedback()
            show_warning(self.tr("Point cloud task failed: {0}").format(e))
        return True

    def _run_task(self, task_name: str, layer: Any) -> None:
        show_info, show_warning = _feedback()
        if task_name in ('undo', 'redo'):
            self._handle_undo_redo(task_name)
            return
        if task_name == 'export':
            show_warning(self.tr("Export is not available for point cloud layers yet"))
            return
        service = self._ensure_service()
        if service is None or self._widget is None:
            show_warning(self.tr("Point cloud filtering is not available"))
            return
        if task_name == 'filter':
            criteria = self._widget.criteria()
            if getattr(criteria, 'is_empty', False):
                show_warning(self.tr("Select at least one point cloud criterion (classification, elevation, intensity or return number)"))
                return
            result = service.apply(layer, criteria)
        elif task_name == 'unfilter':
            result = service.clear(layer)
        else:
            self._widget.reset()
            result = service.clear(layer)
        self._after_subset_change(layer, result)

    def _handle_undo_redo(self, task_name: str) -> None:
        app = getattr(self.dockwidget, 'app', None)
        if app is None:
            logger.warning(f"[PC] {task_name} ignored: app not attached to the dockwidget")
            return
        handler = app.handle_undo if task_name == 'undo' else app.handle_redo
        handler()
        self._update_undo_redo_buttons()
        self._refresh_current_subset_label()

    def _after_subset_change(self, layer: Any, result: Any) -> None:
        dw = self.dockwidget
        app = getattr(dw, 'app', None)
        self._refresh_point_cloud_canvas(layer, app)
        self._mark_subset_state(layer, bool(result.subset_string) if result.success else None)
        self._update_undo_redo_buttons()
        self._refresh_current_subset_label()
        show_info, show_warning = _feedback()
        if not result.success:
            show_warning(self.tr("The point cloud filter could not be applied: {0}").format(result.message or result.subset_string))
        elif result.subset_string:
            show_info(self.tr("Point cloud filter applied: {0}").format(result.subset_string))
        else:
            show_info(self.tr("Point cloud filter cleared"))

    @staticmethod
    def _refresh_point_cloud_canvas(layer: Any, app: Any) -> None:
        """Repaint the layer and the map canvas.

        ``FilterMateApp._refresh_layers_and_canvas`` goes through
        ``LayerRefreshManager``, which reads ``layer.featureCount()`` and
        raises on a point cloud, so the canvas refresh is done directly here.
        """
        try:
            layer.triggerRepaint()
        except Exception as e:
            logger.debug(f"[PC] layer repaint failed: {e}")
        iface = getattr(app, 'iface', None)
        try:
            if iface is not None:
                iface.mapCanvas().refresh()
        except Exception as e:
            logger.debug(f"[PC] canvas refresh failed: {e}")

    def _mark_subset_state(self, layer: Any, is_subset: Optional[bool]) -> None:
        if is_subset is None:
            return
        try:
            self.dockwidget.PROJECT_LAYERS[layer.id()]["infos"]["is_already_subset"] = is_subset
        except (AttributeError, KeyError, TypeError, RuntimeError):
            pass

    def _release_deleted_layer(self, layer: Any) -> None:
        self.deactivate()
        dw = self.dockwidget
        if getattr(dw, 'current_layer', None) is layer:
            try:
                dw.current_layer = None
            except Exception as e:
                logger.debug(f"[PC] current_layer not cleared: {e}")

    # === Service ===

    def _ensure_service(self) -> Any:
        """Create the service once and keep its history bound to ``app.history_manager``."""
        history = getattr(getattr(self.dockwidget, 'app', None), 'history_manager', None)
        if self._service is None:
            try:
                from ...adapters.qgis.point_cloud_layer_adapter import apply_point_cloud_subset, get_point_cloud_subset
                from ...core.services.point_cloud_filter_service import PointCloudFilterService
            except ImportError as e:
                logger.warning(f"[PC] point cloud filter service unavailable: {e}")
                return None
            self._service = PointCloudFilterService(apply_point_cloud_subset, get_point_cloud_subset, history_service=history)
        elif history is not None and getattr(self._service, 'history_service', None) is not history:
            try:
                self._service.history_service = history
            except AttributeError:
                pass
        return self._service

    # === Panel ===

    def _populate_panel(self, layer: Any) -> None:
        try:
            from ...adapters.qgis.point_cloud_layer_adapter import read_point_cloud_summary
            summary = read_point_cloud_summary(layer)
        except Exception as e:
            logger.warning(f"[PC] summary unavailable: {e}")
            return
        try:
            self._widget.populate(summary)
        except Exception as e:
            logger.warning(f"[PC] panel population failed: {e}")

    def _refresh_current_subset_label(self) -> None:
        if self._widget is None or self._active_layer is None:
            return
        service = self._ensure_service()
        if service is None:
            return
        try:
            self._widget.set_current_subset(service.current_subset(self._active_layer))
        except Exception as e:
            logger.debug(f"[PC] current filter label not refreshed: {e}")

    def _on_subset_changed(self) -> None:
        self._refresh_current_subset_label()

    # === Dock layout ===

    def _vector_value_widgets(self) -> List[Any]:
        dw = self.dockwidget
        layout = getattr(dw, VALUES_LAYOUT_NAME, None)
        source_row = getattr(dw, SOURCE_ROW_LAYOUT_NAME, None)
        return self._collect_layout_widgets(layout, source_row)

    def _collect_layout_widgets(self, layout: Any, skipped_layout: Any = None) -> List[Any]:
        widgets: List[Any] = []
        if layout is None:
            return widgets
        try:
            count = int(layout.count())
        except Exception:
            return widgets
        for index in range(count):
            item = layout.itemAt(index)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                if widget is not self._widget:
                    widgets.append(widget)
                continue
            sub_layout = item.layout()
            if sub_layout is None or sub_layout is skipped_layout:
                continue
            try:
                if sub_layout.objectName() == SOURCE_ROW_LAYOUT_NAME:
                    continue
            except Exception:
                pass
            widgets.extend(self._collect_layout_widgets(sub_layout, skipped_layout))
        return widgets

    def _save_visibility(self) -> None:
        dw = self.dockwidget
        targets = [getattr(dw, name, None) for name in HIDDEN_DOCK_WIDGETS]
        targets.extend(self._vector_value_widgets())
        self._saved_visibility = {}
        for widget in targets:
            if widget is None:
                continue
            try:
                self._saved_visibility[widget] = not widget.isHidden()
            except Exception:
                self._saved_visibility[widget] = True

    def _apply_point_cloud_layout(self) -> None:
        dw = self.dockwidget
        for widget in self._saved_visibility:
            self._call(widget, 'setVisible', False)
        self._call(self._widget, 'setVisible', True)
        self._call(getattr(dw, 'frame_exploring', None), 'setEnabled', False)
        button = getattr(dw, 'pushButton_checkable_filtering_layers_to_filter', None)
        if button is not None:
            # setChecked() alone would emit toggled -> layer_property_changed ->
            # setLayerVariableEvent -> settingLayerVariable.emit(QgsVectorLayer, ...)
            # with dw.current_layer already a point cloud: a sip TypeError.
            try:
                self._saved_layers_to_filter_checked = bool(button.isChecked())
            except Exception:
                self._saved_layers_to_filter_checked = None
            try:
                button.blockSignals(True)
                button.setChecked(False)
            except Exception as e:
                logger.debug(f"[PC] layers_to_filter button not unchecked: {e}")
            finally:
                try:
                    button.blockSignals(False)
                except Exception:
                    pass
            self._call(button, 'setEnabled', False)

    def _restore_visibility(self) -> None:
        saved, self._saved_visibility = self._saved_visibility, {}
        for widget, visible in saved.items():
            self._call(widget, 'setVisible', visible)

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
        except Exception as e:
            logger.debug(f"[PC] layer combo not synchronized: {e}")

    def _update_undo_redo_buttons(self) -> None:
        self._call(getattr(self.dockwidget, 'app', None), 'update_undo_redo_buttons')

    # === Layer signal ===

    def _connect_subset_signal(self, layer: Any) -> None:
        if self._subset_slot is not None:
            return
        signal = getattr(layer, 'subsetStringChanged', None)
        if signal is None:
            return
        slot = self._on_subset_changed
        try:
            signal.connect(slot)
            self._subset_slot = slot
        except (TypeError, RuntimeError) as e:
            logger.debug(f"[PC] subsetStringChanged not connected: {e}")

    def _disconnect_subset_signal(self) -> None:
        layer, slot = self._active_layer, self._subset_slot
        self._subset_slot = None
        if layer is None or slot is None:
            return
        try:
            layer.subsetStringChanged.disconnect(slot)
        except (TypeError, RuntimeError, AttributeError) as e:
            logger.debug(f"[PC] subsetStringChanged not disconnected: {e}")

    # === Helpers ===

    @staticmethod
    def _call(target: Any, method: str, *args: Any) -> None:
        """Call ``target.method(*args)`` and log instead of raising."""
        if target is None:
            return
        try:
            func = getattr(target, method, None)
        except Exception as e:
            logger.debug(f"[PC] {method} unavailable: {e}")
            return
        if func is None:
            return
        try:
            func(*args)
        except Exception as e:
            logger.debug(f"[PC] {method} failed: {e}")

    @staticmethod
    def _layer_name(layer: Any) -> str:
        try:
            return layer.name()
        except (RuntimeError, AttributeError):
            return "?"
