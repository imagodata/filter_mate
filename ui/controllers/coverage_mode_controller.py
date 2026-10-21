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
import math
from collections import OrderedDict
from contextlib import contextmanager
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
HISTOGRAM_CACHE_SIZE = 32
# Grids of the preview veil (an expression read, a slope computed): the last few, switching layers re-reads none.
SURFACE_CACHE_SIZE = 4
# An expression not read yet is read once the input settles (a read takes about half a second).
EXPRESSION_READ_DELAY_MS = 400
# What a click of the point cloud picker does: check its class, write a condition on a value, select the
# object under it or every object like it (the object detector, CLASSES).
PC_PICK_MODES = ('class', 'value', 'object', 'similar')
PC_OBJECT_MODES = ('object', 'similar')
# Footprints of a whole class read for the similar objects: a ratio edited reads none again.
PC_FOOTPRINT_CACHE_SIZE = 4
# Decimals of the WKT of the point cloud objects: 1e-9 degree in a geographic CRS (the vertices are
# on the cells, whole metres in a projected one: no trailing digit is written).
WKT_PRECISION = 9


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


@contextmanager
def _wait_cursor():
    """The busy cursor while a read runs on the main thread (none without a Qt application)."""
    try:
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    except Exception:
        QApplication = None
    try:
        yield
    finally:
        if QApplication is not None:
            QApplication.restoreOverrideCursor()


def _detects_objects(selection: Any) -> bool:
    """A selection of the pipette in object detection: the patches under its clicks only."""
    return bool(getattr(selection, 'seeds', ()))


def _is_expression(selection: Any) -> bool:
    """A raster calculator expression selection: a colour of the pipette, a spectral preset, a typed one."""
    return getattr(getattr(selection, 'mode', None), 'value', '') == 'expression'


def _option(key: str, default):
    try:
        from ...config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('CROSS_FILTER', {})
        return _get_option_value(section.get(key), default)
    except Exception:
        return default


class _LinkedRun:
    """One vector filter run of a source: ``op_id`` of the cross operation it recorded, None when none.

    Undo / Redo of the vector source only replay that operation when it is
    still the top of the source's cross history: a step forgotten since (a
    removed layer, the cache limit) never makes them undo another one.
    """

    __slots__ = ('op_id',)

    def __init__(self, op_id: Optional[int] = None) -> None:
        self.op_id = op_id


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
        self._class_tool: Any = None  # the point cloud class pipette (a picker in the point cloud colour)
        self._previous_class_map_tool: Any = None
        self._preview_base_subset: Optional[str] = None
        self._preview_active = False
        self._color_pick = False  # the pipette: a click on the map picks a colour to select
        self._mask_overlay = None  # veil of a terrain derivative or expression preview (canvas item)
        self._object_outline = None  # outline of the objects the pipette detected (rubber band)
        self._pc_pick_mode = 'class'  # what a click of the point cloud picker does: one of PC_PICK_MODES
        self._detected: Any = None  # (key, SelectionGeometryResult) of the last object detection
        # (layer id, source, filter, class) -> footprint of the class, for the similar point cloud objects
        self._pc_footprints: 'OrderedDict[tuple, Any]' = OrderedDict()
        self._pc_outline_wkt = ''  # the point cloud objects drawn by the outline ('' when it shows none)
        self._pc_reader: Any = None  # (key, private copy) the detector reads while a preview is applied
        # (source, layer name, expression) or (source, band, derivative) -> grid of the veil, None when unreadable
        self._surfaces: 'OrderedDict[tuple, Any]' = OrderedDict()
        self._expression_timer: Any = None  # reads an expression once the input settles
        self._crs_notice: Any = None  # (surface, canvas CRS) already told it does not fit the map
        self._histogram_cache: Dict[Tuple[str, int, str], Tuple[list, float, float]] = {}
        self._raster_stats_task: Any = None
        self._raster_band_display: Any = None
        self._raster_display_ranges: Dict[Tuple[str, int], tuple] = {}
        self._rendered_task: Any = None
        self._raster_sample: Any = None  # (layer identity, protected session TIFF, local layer)
        self._raster_surface_task: Any = None
        self._raster_sample_users: Dict[str, int] = {}
        self._retired_raster_samples: set = set()
        self._stats_watched: set = set()  # point cloud layer ids whose statistics signal is connected
        # layer id -> (layer, slot) of those connections: disconnected at teardown (2026-10-17)
        self._stats_slots: Dict[str, Tuple[Any, Any]] = {}
        self._button_slots: List[Tuple[Any, Any]] = []
        # Vector sources: one entry per vector filter run, with the cross operation it recorded (if any).
        self._linked_runs: Dict[str, List[_LinkedRun]] = {}
        self._linked_redo: Dict[str, List[_LinkedRun]] = {}
        self._running_task: Any = None
        self._export_task: Any = None
        self._hag_task: Any = None
        # A raster / point cloud picked before add_layers registered it: activated once it is
        # (the 'refresh' after the registration), unless another layer was picked meanwhile.
        self._awaiting_registration: Optional[str] = None
        self._tidy_pending = False
        self._cache_warned = False
        self._project_connected: set = set()  # names of the QgsProject signals connected by setup()
        self._vector_tasks: Dict[str, Any] = {}  # vector source id -> cross task clipping its coverage targets
        self._extras: Any = None  # CoverageDockExtras: layer card, kind tools, source geometry line

    # === Lifecycle ===

    def _project_slots(self):
        return (('readProject', self._on_project_read), ('cleared', self._on_project_cleared),
                ('layersWillBeRemoved', self._on_layers_removed))

    def setup(self) -> None:
        """Panels are built on the first raster / point cloud layer; stored clips are replayed.

        Safe to call again: each project signal is connected once (a failed
        connection is tried again), the replay and the PDAL probe run once.
        """
        if getattr(self, '_torn_down', False):
            return
        try:
            from qgis.core import QgsProject
            project = QgsProject.instance()
            for name, slot in self._project_slots():
                if name in self._project_connected:
                    continue
                try:
                    getattr(project, name).connect(slot)
                    self._project_connected.add(name)
                except Exception as exc:
                    logger.debug(f"[FM5] project signal {name} not connected: {exc}")
        except Exception as exc:
            logger.debug(f"[FM5] project signals not connected: {exc}")
        if getattr(self, '_setup_done', False):
            return
        self._setup_done = True
        try:
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(1500, self.replay_stored_filters)
        except Exception as exc:
            logger.debug(f"[FM5] stored filters replay not scheduled: {exc}")
        try:
            from ...adapters.qgis.coverage_layers import pdal_cli
            pdal_cli.warm_up()  # the point cloud panel then never waits for `pdal --version`
        except Exception as exc:
            logger.debug(f"[FM5] pdal version not read in the background: {exc}")
        logger.debug("CoverageModeController setup complete (panels deferred)")

    def _leave_removed_layers(self, layer_ids: Optional[List[str]]) -> None:
        """Layers removed (None: the project was closed): leave the mode of the active one, forget their styles.

        Never raises: the caller forgets the histories whatever happens here.
        """
        active, active_id = self._active_layer, self._active_id()
        removed = active is not None and (layer_ids is None or active_id is None or active_id in layer_ids)
        if removed or layer_ids is None:
            try:
                current = getattr(self.dockwidget, 'current_layer', None)
                if removed and (current is active or _same_layer(current, active)):
                    self.dockwidget.current_layer = None  # about to be deleted: Filter would read it
                # Before its input is forgotten: leaving the layer saves it again.
                self.deactivate()  # the pixel picker leaves the map, the panels go
            except Exception as exc:
                logger.warning(f"[FM5] coverage mode not left cleanly: {exc}", exc_info=True)
        if self._extras is not None:
            self._extras_call('forget_layers', layer_ids)
            if removed or layer_ids is None:
                self._extras_call('show_vector', None)  # vector buttons back, no raster tool, no stale card

    def _on_project_cleared(self) -> None:
        """A new / closed project: histories and links refer to layers that are gone."""
        from ...core.services.cross_filter_service import clear_histories
        self._leave_removed_layers(None)
        clear_histories()  # the dock's and the automation one
        self._linked_runs.clear()
        self._linked_redo.clear()
        self._panel_states.clear()
        self._histogram_cache.clear()
        self._raster_display_ranges.clear()
        self._surfaces.clear()
        self._detected = None
        self._pc_footprints.clear()
        self._pc_reader = None
        self._stats_watched.clear()  # the same ids come back with new layers when the project is opened again
        self._stats_slots.clear()  # their layers are gone
        self._schedule_cache_tidy()

    def _on_layers_removed(self, layer_ids) -> None:
        from ...core.services.cross_filter_service import forget_layer_everywhere
        layer_ids = list(layer_ids or [])
        self._leave_removed_layers(layer_ids)
        for layer_id in layer_ids:
            forget_layer_everywhere(layer_id)
            self._linked_runs.pop(layer_id, None)
            self._linked_redo.pop(layer_id, None)
            self._panel_states.pop(layer_id, None)
            self._stats_watched.discard(layer_id)
            self._stats_slots.pop(layer_id, None)
        for key in [key for key in self._pc_footprints if key[0] in layer_ids]:
            del self._pc_footprints[key]
        self._schedule_cache_tidy()  # runs once the layers are gone

    def _unlink_dropped_run(self, source_id: str, op_id: Optional[int]) -> None:
        """A cross operation of a vector source was forgotten: so is the run that recorded it."""
        for run in self._linked_runs.get(source_id) or []:
            if run.op_id is not None and run.op_id == op_id:
                run.op_id = None

    def _schedule_cache_tidy(self, delay_ms: int = 0) -> None:
        """Remove unused derived files soon (once no FilterMate task runs)."""
        if self._tidy_pending or getattr(self, '_torn_down', False):
            return
        try:
            from qgis.PyQt.QtCore import QTimer
            self._tidy_pending = True
            QTimer.singleShot(delay_ms, self._tidy_cache)
        except Exception as exc:
            self._tidy_pending = False
            logger.debug(f"[FM5] cache tidy not scheduled: {exc}")

    def _tidy_cache(self) -> None:
        self._tidy_pending = False
        if getattr(self, '_torn_down', False):
            return
        try:
            from ...core.services.cross_filter_service import tidy_cache
            report = tidy_cache()
        except Exception as exc:
            logger.warning(f"[FM5] cache not tidied: {exc}")
            return
        if report is None:
            self._schedule_cache_tidy(3000)  # a task may be writing a derived file
            return
        if report['dropped']:
            for service, step in report['dropped']:
                if service is self.service and step.from_undo:
                    self._unlink_dropped_run(step.operation.source_layer_id, step.operation.op_id)
            self.update_undo_redo_buttons()
        over = bool(report['limit']) and report['size'] > report['limit']
        if not over:
            self._cache_warned = False  # warn again next time the limit is reached
        elif not self._cache_warned:
            # Current filters alone are over the limit: only the user can free them.
            self._cache_warned = True
            _, show_warning = _feedback()
            show_warning(self.tr("The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the "
                                 "raster / point cloud layers you no longer need").format(
                f"{report['size'] / 1024 ** 3:.1f}", f"{report['limit'] / 1024 ** 3:.1f}"))

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
        if self._expression_timer is not None:
            try:
                self._expression_timer.stop()
            except RuntimeError:
                pass  # deleted with the dock
        self._surfaces.clear()
        self._raster_display_ranges.clear()
        self._hide_detected_objects()
        self._detected = None
        self._pc_footprints.clear()
        self._pc_reader = None
        if self._extras is not None:
            self._extras_call('teardown')
            self._extras = None
        if self._project_connected:
            try:
                from qgis.core import QgsProject
                project = QgsProject.instance()
                for name, slot in self._project_slots():
                    if name not in self._project_connected:
                        continue
                    try:
                        getattr(project, name).disconnect(slot)
                    except (TypeError, RuntimeError):
                        pass
            except Exception as exc:
                logger.debug(f"[FM5] project signals not disconnected: {exc}")
            self._project_connected.clear()
        try:
            self.service.cancel_all()
        except Exception as exc:
            logger.debug(f"[FM5] running tasks not canceled: {exc}")
        for task_name in ('_export_task', '_hag_task', '_raster_stats_task', '_rendered_task', '_raster_surface_task'):
            task = getattr(self, task_name, None)
            setattr(self, task_name, None)
            if task is not None:
                try:
                    task.cancel()  # its callback returns early once torn down
                except RuntimeError:
                    pass
        for widget_name in ('_host', '_coverage_spin'):
            widget = getattr(self, widget_name)
            setattr(self, widget_name, None)
            if widget is not None:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except Exception as exc:
                    logger.debug(f"[FM5] panel widget not released: {exc}")
        self._drop_map_tools()  # one QGIS could give back later would call a dead controller
        self._disconnect_point_cloud_statistics()
        self._raster_panel = None
        self._pc_panel = None
        self._running_task = None
        self._export_task = None
        self._hag_task = None
        self._base_keepalive = None
        self._release_raster_sample()
        self._histogram_cache.clear()

    @property
    def active_layer(self) -> Any:
        return self._active_layer

    def _active_id(self) -> Optional[str]:
        """Id of the active layer, None without one or once its C++ object is deleted."""
        try:
            return self._active_layer.id() if self._active_layer is not None else None
        except RuntimeError:
            return None

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

    def on_current_layer_changed(self, layer: Any, manual_change: bool = False) -> bool:
        """Take over the layer change for a raster or point cloud layer.

        Args:
            layer: The new current layer.
            manual_change: The user picked it (combo box): it replaces a layer waiting for
                its registration. An automatic change (the dock's refresh after add_layers)
                does not.

        Returns:
            True when handled here (the vector chain must stop): a raster /
            point cloud layer, or a layer the vector chain would refuse while
            one is shown.
        """
        kind = _kind_of(layer)
        if manual_change and self._layer_id(layer) != self._awaiting_registration:
            self._awaiting_registration = None  # the user picked another layer
        if getattr(kind, 'is_coverage', False):
            if not self._is_registered(layer):
                # 2026-10-17: picked before add_layers registered it (just added to the project):
                # the panel read properties the layer did not have yet. It is activated once the
                # dock has the registration (activate_awaited_layer); the current layer stays.
                self._awaiting_registration = self._layer_id(layer)
                logger.info(f"[FM5] {self._layer_name(layer)} not registered yet: shown once it is")
                return True
            if not self._ensure_host():
                logger.warning("[FM5] coverage layer selected but the panels are unavailable")
                return False
            self.activate(layer, kind)
            return True
        if not self._vector_chain_takes(layer, kind):
            # A web raster, a table without geometry, a vector not listed (yet): the vector chain
            # would make it the dock's current layer, then refuse it. With a raster / point cloud
            # shown, the chain stops here and that layer stays current; otherwise it decides.
            return self._active_layer is not None
        if self._active_layer is not None:
            self.deactivate()
        self._extras_call('show_vector', layer)
        return False

    @staticmethod
    def _layer_id(layer: Any) -> Optional[str]:
        try:
            return layer.id()
        except (RuntimeError, AttributeError):
            return None

    def _is_registered(self, layer: Any) -> bool:
        """True when ``layer`` is in the dock's PROJECT_LAYERS (add_layers registered it)."""
        layer_id = self._layer_id(layer)
        return layer_id is not None and layer_id in (getattr(self.dockwidget, 'PROJECT_LAYERS', None) or {})

    def activate_awaited_layer(self) -> bool:
        """The layer picked before its registration, now in the dock's PROJECT_LAYERS: shown.

        Called by the dock once it has the layers of an add_layers (get_project_layers_from_app),
        whatever layer the dock shows meanwhile.

        Returns:
            True when the awaited layer was activated.
        """
        layer_id = self._awaiting_registration
        if layer_id is None or layer_id not in (getattr(self.dockwidget, 'PROJECT_LAYERS', None) or {}):
            return False
        self._awaiting_registration = None
        try:
            from qgis.core import QgsProject
            layer = QgsProject.instance().mapLayer(layer_id)
        except Exception as exc:  # catch-all safety net: project unavailable
            logger.debug(f"[FM5] awaited layer not found: {exc}")
            return False
        if layer is None:
            return False
        # The user's pick, applied now: the automatic layer changes the dock deferred during the
        # registration (its refresh re-applied the vector layer) give way to it, as to any pick.
        import time
        try:
            self.dockwidget._user_layer_pick = (time.perf_counter(), layer_id)
        except AttributeError:
            pass
        return bool(self.on_current_layer_changed(layer, manual_change=True))

    def _vector_chain_takes(self, layer: Any, kind: Any) -> bool:
        """True when the dock's vector chain will make ``layer`` the current layer (a listed vector layer)."""
        from ...core.domain.layer_kind import LayerKind
        if kind is not LayerKind.VECTOR:
            return False
        try:
            return layer.id() in (getattr(self.dockwidget, 'PROJECT_LAYERS', None) or {})
        except (RuntimeError, AttributeError, TypeError):
            return False

    def activate(self, layer: Any, kind: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        dw = self.dockwidget
        # Activated again for the layer it shows (F5, a late layer change signal):
        # the input and the live preview stay as they are.
        again = self._active_layer is not None and _same_layer(self._active_layer, layer)
        if self._active_layer is not None and not again:
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
        self._apply_layout(kind, keep_preview=again)
        self._show_kind_badge(layer, kind)
        self._extras_call('show_for', layer, kind)
        if kind is LayerKind.RASTER:
            self._populate_raster(layer)
        else:
            self._populate_point_cloud(layer)
        if not again:
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
        self._cancel_raster_statistics()
        self._cancel_rendered_capture()
        self._cancel_raster_surface()
        self._release_raster_sample()
        layer = self._active_layer
        if layer is None:
            return
        # R3 (2026-10-18): the tool on the map leaves with the layer and comes back with it.
        pipette_on, target = self._color_pick and self._tool_on_map(self._pixel_tool), None
        if pipette_on and self._raster_panel is not None and hasattr(self._raster_panel, 'pick_target'):
            target = self._raster_panel.pick_target()
        class_pipette_on = self._tool_on_map(self._class_tool)
        self._deactivate_pixel_tool()
        self._deactivate_class_tool()
        # QGIS remembers the last tool before Pan / Zoom and gives it back: a picker of the outgoing
        # layer must not come back on the next one (the raster picker reading a point cloud).
        self._drop_map_tools()
        try:
            state = self._current_panel().state() if self._current_panel() is not None else {}
            if state:
                state['pipette_on'] = bool(pipette_on)
                if target is not None:
                    state['pipette_target'] = target
                state['class_pipette_on'] = bool(class_pipette_on)
                state['pc_tool'] = self._pc_pick_mode if class_pipette_on else ''
            self._panel_states[layer.id()] = state
        except Exception as exc:
            logger.debug(f"[FM5] panel state not saved: {exc}")
        self._stop_preview(layer)
        self._restore_raster_band_display(layer)
        self._hide_detected_objects()  # drawn again from the saved state when the layer comes back
        self._pc_reader = None  # the copy of the outgoing layer is not kept open

    @staticmethod
    def _disconnect_previous_vector_selection(dw: Any, incoming_layer: Any) -> None:
        old_layer = getattr(dw, 'current_layer', None)
        if old_layer is None or _same_layer(old_layer, incoming_layer):
            return
        # 2026-10-17: every connection, whatever the flag says (it skipped the disconnect
        # when unset, and one disconnect left a duplicate connection behind)
        if hasattr(dw, '_disconnect_layer_selection_signal'):
            dw._disconnect_layer_selection_signal(old_layer)
        else:
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
        try:
            # Same spacing scale as the vector groups (the panels are built after the dock layout).
            from ..layout.mockup_layout import fit_panel
            if host.layout() is not None:
                host.layout().setContentsMargins(0, 0, 0, 0)
            fit_panel(self._raster_panel)
            fit_panel(self._pc_panel)
        except Exception as exc:
            logger.debug(f"[FM5] coverage panel spacing skipped: {exc}")
        self._connect_panels()
        self._ensure_coverage_spin()
        self._extras_call('ensure', host)
        return True

    def _extras_call(self, method: str, *args) -> None:
        """Run a :class:`CoverageDockExtras` method; the dock additions never break the mode."""
        try:
            if self._extras is None:
                from .coverage_dock_extras import CoverageDockExtras
                self._extras = CoverageDockExtras(self)
            getattr(self._extras, method)(*args)
        except Exception as exc:
            logger.debug(f"[FM5] dock additions '{method}' failed: {exc}")

    def refresh_selection_strip(self) -> None:
        """The EXPLORING selection may have changed: the strip above FILTERING follows."""
        self._extras_call('schedule_strip')

    def sync_vector_tools(self, groupbox: Optional[str]) -> None:
        """The vector EXPLORING group changed: the rail tools tied to the groups follow (R1)."""
        self._extras_call('sync_vector_tools', groupbox)

    def note_exploring_selection(self, layer_id: str, groupbox: str, count: int) -> None:
        """Features of the vector EXPLORING selection, for the strip above FILTERING."""
        self._extras_call('note_vector_selection', layer_id, groupbox, count)

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
            index = parent_layout.indexOf(combo)
            from qgis.PyQt.QtWidgets import QBoxLayout, QHBoxLayout
            if isinstance(parent_layout, QBoxLayout) and parent_layout.direction() in (
                    QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.BottomToTop):
                # Same row as the predicates (mockup): a row below would shift FILTERING's
                # values column away from its buttons column.
                parent_layout.removeWidget(combo)
                row = QHBoxLayout()
                row.setSpacing(parent_layout.spacing())
                row.addWidget(combo, 1)
                row.addWidget(spin, 0)
                parent_layout.insertLayout(index, row)
            else:
                parent_layout.insertWidget(index + 1, spin)
        self._fit_coverage_spin(spin)
        self._coverage_spin = spin

    @staticmethod
    def _fit_coverage_spin(spin) -> None:
        """Keep the field wide enough for "cov. ≥ 100 %": its size hint ignores the stylesheet padding
        and the steppers drawn by mockup.qss, and the text came out clipped ("cov. ≥ 50 !"). Measured
        again whenever the font or the style changes (the dock font arrives after creation)."""
        from qgis.PyQt.QtCore import QEvent
        from qgis.PyQt.QtWidgets import QLineEdit
        editor = spin.findChild(QLineEdit)  # draws the text, with its own stylesheet font (monospace)

        def fit():
            try:
                metrics = (editor or spin).fontMetrics()
                text = f"{spin.prefix()}{spin.maximum()}{spin.suffix()}"
                width = metrics.horizontalAdvance(text) if hasattr(metrics, 'horizontalAdvance') else metrics.width(text)
                # Spin box padding 8 + 8, the inner editor's own QLineEdit padding 8 + 8, steppers 16 + gap 4,
                # frame / slack 12 (measured in QGIS 4.2: a 101 px editor showed 85 px of text).
                wanted = width + 16 + 16 + 20 + 12
                if spin.minimumWidth() != wanted:
                    spin.setMinimumWidth(wanted)
            except (AttributeError, RuntimeError, TypeError):
                pass

        events = (QEvent.Type.Show, QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.Polish)
        try:
            spin._fm_fit = _event_callback(spin, events, fit)
            for widget in (spin, editor):
                if widget is not None:
                    widget.installEventFilter(spin._fm_fit)
        except (AttributeError, RuntimeError, TypeError):
            pass
        fit()

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
        from ..styles.mockup_design import KIND_COLORS, badge_stylesheet
        color = KIND_COLORS['raster' if kind is LayerKind.RASTER else 'point_cloud']
        name = badge.objectName() or 'label_backend_indicator'
        self._call(badge, 'setText', f"{label} · {provider.upper() if len(provider) <= 4 else provider}" if provider else label)
        self._call(badge, 'setToolTip', self.tr("{0} layer: selection in EXPLORING, relation in FILTERING").format(label))
        self._call(badge, 'setStyleSheet', badge_stylesheet(name, color))

    def _only_page_sizes(self, page: Any) -> None:
        """The stack is as wide as its shown page only.

        A QStackedWidget's minimum width is the widest of its pages: the raster panel grown by its
        picks (chips, coordinates, zone statistics) made the point cloud panel 395 px wide in a
        358 px dock, with a sideways scroll (2026-10-18). The hidden page ignores its size.
        """
        try:
            from qgis.PyQt.QtWidgets import QSizePolicy
            for panel in (self._raster_panel, self._pc_panel):
                if panel is None:
                    continue
                policy = QSizePolicy.Policy.Preferred if panel is page else QSizePolicy.Policy.Ignored
                panel.setSizePolicy(policy, policy)
        except Exception as exc:
            logger.debug(f"[FM5] page size policies not set: {exc}")

    def _apply_layout(self, kind: Any, keep_preview: bool = False) -> None:
        from ...core.domain.layer_kind import LayerKind
        dw = self.dockwidget
        for widget in self._saved_visibility:
            self._call(widget, 'setVisible', False)
        self._call(getattr(dw, 'frame_exploring', None), 'setEnabled', True)
        if self._host is not None:
            page = self._raster_panel if kind is LayerKind.RASTER else self._pc_panel
            self._host.setCurrentWidget(page)
            self._only_page_sizes(page)
            self._host.setVisible(True)
        self._call(self._coverage_spin, 'setVisible', True)
        tips = {
            LayerKind.RASTER: {
                'pushButton_exploring_identify': self.tr("Not used for raster layers: the pipette reads the bands"),
                'pushButton_exploring_zoom': self.tr("Zoom to the selected pixels (to the layer when nothing is selected)"),
                'pushButton_checkable_exploring_selecting': self.tr("Preview: hide the pixels outside the selection "
                                                                    "(a white veil for a slope, aspect...)"),
                'pushButton_checkable_exploring_tracking': self.tr("Not used for raster layers"),
                'pushButton_checkable_exploring_linking_widgets': self.tr("Not used for raster layers"),
                'pushButton_exploring_reset_layer_properties': self.tr("Reset the raster selection"),
            },
            LayerKind.POINT_CLOUD: {
                'pushButton_exploring_identify': self.tr(
                    "Class pipette: click the map and the class of the points drawn there is checked. "
                    "Ctrl+click adds another one"),
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
            # 2026-10-18: the pixel picker left the raster rail (the pipette reads the bands); the Identify
            # button is hidden with tracking and linking on a raster, and is the class pipette on a point cloud.
            unused = name in ('pushButton_checkable_exploring_tracking', 'pushButton_checkable_exploring_linking_widgets') or (
                name == 'pushButton_exploring_identify' and kind is LayerKind.RASTER)
            self._call(button, 'setEnabled', not unused)
        if not keep_preview:
            self._set_selecting_checked(False)  # no preview on a layer just shown

    def _set_selecting_checked(self, checked: bool) -> None:
        """Check the preview button of the dock without running its handler."""
        selecting = getattr(self.dockwidget, 'pushButton_checkable_exploring_selecting', None)
        if selecting is None:
            return
        try:
            selecting.blockSignals(True)
            try:
                selecting.setChecked(bool(checked))
            finally:
                selecting.blockSignals(False)
        except RuntimeError:
            pass  # deleted (plugin closing)

    def _current_panel(self):
        from ...core.domain.layer_kind import LayerKind
        if self._kind is LayerKind.RASTER:
            return self._raster_panel
        if self._kind is LayerKind.POINT_CLOUD:
            return self._pc_panel
        return None

    def _restore_panel_state(self, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        state = self._panel_states.get(layer.id())
        panel = self._current_panel()
        if state and panel is not None:
            try:
                panel.restore_state(state)
                if self._kind is LayerKind.RASTER:
                    # The restored band / quantity may not be the one populated first.
                    try:
                        self._refresh_histogram(layer, panel.current_band())
                    except Exception as exc:
                        logger.debug(f"[FM5] histogram not refreshed after the restore: {exc}")
                    self._show_detected_objects()  # the outline left with the layer comes back with it
                    self._on_raster_display_changed()
                if self._kind is LayerKind.POINT_CLOUD:
                    if getattr(panel, 'objects_pending', lambda: False)():
                        self._refresh_point_cloud_objects()  # clicked objects never read (or a read failed)
                    else:
                        self._show_point_cloud_objects()  # the objects of the detector, as found then
                if self._kind is LayerKind.RASTER and state.get('preview'):
                    # The preview box comes back checked: so do the button and the mask on the map.
                    self._on_raster_preview_toggled(True)
                self._restore_tool(state)
            except Exception as exc:
                logger.debug(f"[FM5] panel state not restored: {exc}")

    def _restore_tool(self, state: Any) -> None:
        """R3: the pipette / detector or the class pipette that was on the map when the layer was left comes back."""
        from ...core.domain.layer_kind import LayerKind
        if not isinstance(state, dict):
            return
        if self._kind is LayerKind.RASTER and state.get('pipette_on'):
            target = state.get('pipette_target') or 'similar'
            self._on_color_pick_toggled(True, target)
        elif self._kind is LayerKind.POINT_CLOUD and state.get('class_pipette_on'):
            self._on_class_pick_toggled(True, state.get('pc_tool') or 'class')

    def _tool_on_map(self, tool: Any) -> bool:
        """Whether ``tool`` is the current map tool of the canvas."""
        if tool is None:
            return False
        iface = self._iface()
        if iface is None:
            return False
        try:
            return iface.mapCanvas().mapTool() is tool
        except RuntimeError:
            return False

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
                from qgis.core import QgsProject
                from ...adapters.qgis.coverage_layers.vector_tile_filters import append_targets
                widget = dw.widgets['FILTERING']['LAYERS_TO_FILTER']['WIDGET']
                selected = dw.PROJECT_LAYERS.get(layer.id(), {}).get('filtering', {}).get('layers_to_filter', [])
                append_targets(widget, QgsProject.instance(), selected)
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
        raster.displayChanged.connect(self._on_raster_display_changed)
        raster.selectionChanged.connect(self._on_raster_selection_changed)
        pc.criteriaChanged.connect(self._on_point_cloud_criteria_changed)
        if hasattr(raster, 'modeChosen'):
            raster.modeChosen.connect(self._on_raster_mode_chosen)
        if hasattr(pc, 'groupChosen'):
            pc.groupChosen.connect(self._on_point_cloud_group_chosen)
        if hasattr(pc, 'objectsChanged'):
            pc.objectsChanged.connect(self._refresh_point_cloud_objects)

    def _populate_raster(self, layer: Any) -> None:
        try:
            from ...adapters.qgis.coverage_layers.raster_adapter import raster_reference, read_raster_summary
            summary = read_raster_summary(layer)
            self._raster_panel.set_summary(summary)
            self._raster_panel.set_reference(raster_reference(layer))
            capability = self._raster_capability(layer)
            self._raster_panel.set_rendered_only(not capability.has_raw_values)
            if not capability.has_raw_values:
                self._request_rendered_capture(layer)
                return
            if self._raster_needs_sample(layer):
                self._raster_panel.set_stream_notice(self.tr(
                    "Preview and statistics use a bounded local sample of the visible extent; filtering reads the source."))
            else:
                self._raster_panel.set_stream_notice('')
            if capability.has_raw_values and not self._raster_needs_sample(layer):
                self._raster_panel.set_band_spans(self._band_spans(layer, len(summary.bands)))
            self._refresh_histogram(layer, self._raster_panel.current_band())
        except Exception as exc:
            logger.warning(f"[FM5] raster panel not populated: {exc}", exc_info=True)

    def _band_spans(self, layer: Any, band_count: int) -> Dict[int, float]:
        """Observed value range of the first four bands (the colour of an image), for the pipette tolerance."""
        from ...adapters.qgis.coverage_layers.raster_adapter import band_range
        spans = {}
        base = self._base_raster(layer)
        for band in range(1, min(band_count, 4) + 1):
            try:
                low, high, _mean = band_range(base, band)
            except Exception as exc:
                logger.debug(f"[FM5] band {band} range unread: {exc}")
                continue
            if low is not None and high is not None and high > low:
                spans[band] = high - low
        return spans

    def _refresh_histogram(self, layer: Any, band: int) -> None:
        capability = self._raster_capability(layer)
        if not capability.has_raw_values:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import band_histogram, derivative_histogram
        derivative = self._raster_panel.current_derivative()
        expression = self._quantity_expression()
        if not expression and self._uses_expression_histogram():
            self._cancel_raster_statistics()
            self._call(self._raster_panel, 'clear_expression_histogram')
            self._raster_panel.set_expression_status(True, '')
            self._raster_panel.set_kept_ratio(None)
            return
        key = self._histogram_key(layer, band, expression or derivative)
        pending = self._raster_stats_task
        identity = layer.id(), capability.provider_key, key
        if pending is not None and pending.identity != identity:
            self._cancel_raster_statistics()
        if expression and not self._validate_raster_expression(expression):
            self._raster_panel.set_histogram(band, [], 0.0, 0.0, derivative, expression=expression)
            self._raster_panel.set_kept_ratio(None)
            return
        cached = self._histogram_cache.get(key)
        if cached is None:
            if self._raster_needs_sample(layer) or expression:
                self._request_raster_statistics(layer, band, derivative, key)
                return
            if derivative.is_terrain:
                cached = derivative_histogram(self._base_raster(layer), band, derivative, bins=64)
            else:
                cached = band_histogram(self._base_raster(layer), band, bins=64)
            if cached[0]:  # statistics unavailable (yet): read them again next time
                self._histogram_cache[key] = cached
            while len(self._histogram_cache) > HISTOGRAM_CACHE_SIZE:
                del self._histogram_cache[next(iter(self._histogram_cache))]  # oldest first
        counts, minimum, maximum = cached
        if expression:
            self._raster_panel.set_histogram(band, counts, minimum, maximum, derivative, expression=expression)
            self._validate_raster_expression(expression)
        else:
            self._raster_panel.set_histogram(band, counts, minimum, maximum, derivative)
        self._update_kept_ratio()

    def _quantity_expression(self) -> str:
        panel = self._raster_panel
        value = panel.current_quantity_expression() if panel is not None and hasattr(panel, 'current_quantity_expression') else ''
        return value.strip() if isinstance(value, str) else ''

    def _uses_expression_histogram(self) -> bool:
        panel = self._raster_panel
        return panel is not None and hasattr(panel, 'histogram_uses_expression') and panel.histogram_uses_expression() is True

    @staticmethod
    def _raster_capability(layer):
        from ...adapters.qgis.source_capability_probe import capability_for_layer
        from ...core.domain.source_capability import classify
        try:
            from ...adapters.qgis.coverage_layers.snapshots import registry
            snapshot = registry().get(layer.id())
        except ImportError:
            snapshot = None
        if snapshot is not None and snapshot.original_source:
            return classify(getattr(snapshot, 'original_provider', '') or layer.providerType(),
                            snapshot.original_source, is_raster=True)
        return capability_for_layer(layer)

    def _raster_needs_sample(self, layer):
        capability = self._raster_capability(layer)
        return capability.is_remote or capability.provider_key == 'postgresraster'

    def _raster_identity(self, layer):
        return layer.id(), self._raster_capability(layer).provider_key, self._histogram_key(layer, 0)[0]

    def _release_raster_sample(self):
        sample, self._raster_sample = self._raster_sample, None
        if sample is not None:
            if self._raster_sample_users.get(sample[1], 0):
                self._retired_raster_samples.add(sample[1])
            else:
                from ...adapters.qgis.coverage_layers import cache
                cache.settle([sample[1]])
            for key in list(self._histogram_cache):
                if key[0] == sample[0][2]:
                    del self._histogram_cache[key]

    def _borrow_raster_sample(self, task, path):
        task.borrowed_sample = path
        if path:
            self._raster_sample_users[path] = self._raster_sample_users.get(path, 0) + 1

    def _return_raster_sample(self, task):
        path = getattr(task, 'borrowed_sample', '')
        if not isinstance(path, str) or not path:
            return
        task.borrowed_sample = ''
        count = self._raster_sample_users.get(path, 0) - 1
        if count > 0:
            self._raster_sample_users[path] = count
        else:
            self._raster_sample_users.pop(path, None)
            if path in self._retired_raster_samples:
                from ...adapters.qgis.coverage_layers import cache
                self._retired_raster_samples.discard(path)
                cache.settle([path])

    def _local_raster_sample(self, layer):
        sample = self._raster_sample
        if sample is not None and sample[0] == self._raster_identity(layer):
            return sample[2]
        return None

    def _accept_raster_sample(self, layer, path):
        from qgis.core import QgsRasterLayer
        sample = self._local_raster_sample(layer)
        if sample is not None and sample.source() == path:
            return True
        sample = QgsRasterLayer(path, layer.name(), 'gdal')
        if not sample.isValid():
            return False
        self._release_raster_sample()
        self._raster_sample = self._raster_identity(layer), path, sample
        return True

    def _cancel_rendered_capture(self):
        task, self._rendered_task = self._rendered_task, None
        if task is not None:
            task.cancel()

    def _request_rendered_capture(self, layer):
        if self._local_raster_sample(layer) is not None:
            return
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.rendered_raster import RenderedRasterTask
        identity = self._raster_identity(layer)
        if self._rendered_task is not None and self._rendered_task.identity == identity:
            return
        self._cancel_rendered_capture()
        iface = self._iface()
        if iface is None:
            return
        task = RenderedRasterTask(identity[2], identity[1], layer.renderer().clone(),
                                  iface.mapCanvas().mapSettings(), layer.crs(), self._rendered_capture_ready)
        task.identity = identity
        self._rendered_task = task
        self._raster_panel.set_stream_notice(self.tr("Preparing a bounded color snapshot of the visible extent…"))
        QgsApplication.taskManager().addTask(task)

    def _rendered_capture_ready(self, task, ok):
        if task is not self._rendered_task:
            return False
        self._rendered_task = None
        layer = self._active_layer
        if layer is None or self._raster_panel is None:
            return False
        if not ok or task.identity != self._raster_identity(layer):
            if not ok:
                _feedback()[1](self.tr("The color snapshot could not be prepared. Try a smaller visible extent."))
            return False
        if not self._accept_raster_sample(layer, task.path):
            return False
        self._raster_panel.set_stream_notice(self.tr("Color selection applies to the captured visible extent."))
        self._update_kept_ratio()
        if self._preview_wanted():
            self._apply_raster_preview()
        return True

    def _cancel_raster_statistics(self):
        task = self._raster_stats_task
        self._raster_stats_task = None
        if task is not None:
            task.cancel()

    def _request_raster_statistics(self, layer, band, derivative, key):
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.raster_statistics_task import RasterStatisticsTask
        identity = (layer.id(), self._raster_capability(layer).provider_key, key)
        pending = self._raster_stats_task
        display_bands = self._raster_panel.display_bands() or ()
        if pending is not None and pending.identity == identity and pending.display_bands == display_bands:
            return
        self._cancel_raster_statistics()
        materialize = self._raster_needs_sample(layer)
        sample = self._local_raster_sample(layer) if materialize else None
        task = RasterStatisticsTask(key[0], identity[1], band, derivative,
                                    layer.bandCount(), self._raster_statistics_ready,
                                    extent=self._raster_read_extent(layer) if materialize else None,
                                    max_pixels=self._raster_preview_pixel_limit(),
                                    sample_source=sample.source() if sample is not None else '',
                                    expression=self._quantity_expression(), layer_name=layer.name(), materialize=materialize,
                                    display_bands=display_bands)
        task.identity = identity
        self._raster_stats_task = task
        self._borrow_raster_sample(task, task.sample_source)
        if task.expression:
            self._raster_panel.set_histogram(band, [], 0.0, 0.0, derivative, expression=task.expression)
        else:
            self._raster_panel.set_histogram(band, [], 0.0, 0.0, derivative)
        self._raster_panel.set_kept_ratio(None)
        self._call(self._raster_panel, 'set_histogram_pending')
        QgsApplication.taskManager().addTask(task)

    def _raster_statistics_ready(self, task, ok):
        self._return_raster_sample(task)
        if task is not self._raster_stats_task:
            return False
        self._raster_stats_task = None
        layer, panel = self._active_layer, self._raster_panel
        if layer is None or panel is None:
            return False
        try:
            key = self._histogram_key(layer, panel.current_band(), self._quantity_expression() or panel.current_derivative())
            if (layer.id(), self._raster_capability(layer).provider_key, key) != task.identity:
                return False
        except RuntimeError:
            return False
        if not ok:
            if panel.display_bands():
                panel.set_display_status(self.tr("The selected bands could not be displayed."))
            if task.expression:
                message = (self.tr("Unknown raster layer or band in expression") if task.expression_error == 'bands' else
                           self.tr("Invalid raster calculator expression") if task.expression_error == 'syntax' else
                           self.tr("The raster histogram could not be calculated."))
                panel.set_expression_status(False, message)
            else:
                panel.set_stream_notice(self.tr("Raster sampling failed. Try a smaller visible extent."))
            return False
        if task.materialize and not self._accept_raster_sample(layer, task.sample_source):
            return False
        for band, bounds in task.ranges.items():
            self._raster_display_ranges[(key[0], band)] = bounds
        while len(self._raster_display_ranges) > HISTOGRAM_CACHE_SIZE * 4:
            del self._raster_display_ranges[next(iter(self._raster_display_ranges))]
        if task.histogram[0] or task.expression:
            self._histogram_cache[key] = task.histogram
            while len(self._histogram_cache) > HISTOGRAM_CACHE_SIZE:
                del self._histogram_cache[next(iter(self._histogram_cache))]
        if task.materialize:
            panel.set_band_spans(task.spans)
        if task.expression:
            panel.set_histogram(task.band, *task.histogram, task.derivative, expression=task.expression)
            self._validate_raster_expression(task.expression)
        else:
            panel.set_histogram(task.band, *task.histogram, task.derivative)
        self._update_kept_ratio()
        if panel.display_bands():
            self._on_raster_display_changed(request_statistics=False)
        if self._preview_wanted():
            self._apply_raster_preview()
        return True

    @staticmethod
    def _raster_preview_pixel_limit():
        from ...adapters.qgis.coverage_layers.raster_adapter import source_max_pixels
        return max(1, min(1000000, source_max_pixels(_option('raster_source_max_pixels', None))))

    def _raster_read_extent(self, layer):
        """Metadata only: view in layer CRS, intersected with the source."""
        from qgis.core import QgsCoordinateTransform, QgsProject, QgsRectangle
        extent = QgsRectangle(layer.extent())
        iface = self._iface()
        if iface is None:
            return extent
        canvas = iface.mapCanvas()
        transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
        view = transform.transformBoundingBox(canvas.extent())
        intersection = extent.intersect(view)
        return extent if intersection.isEmpty() else intersection

    def _base_raster(self, layer: Any):
        """The original raster when the layer shows a FilterMate derived source."""
        if self._raster_needs_sample(layer):
            sample = self._local_raster_sample(layer)
            if sample is None:
                raise RuntimeError('Raster sample is not ready')
            return sample
        from ...adapters.qgis.coverage_layers.snapshots import registry
        snapshot = registry().get(layer.id())
        if snapshot is None:
            return layer
        from qgis.core import QgsRasterLayer
        base = QgsRasterLayer(snapshot.original_source, layer.name(), snapshot.original_provider)
        self._base_keepalive = base
        return base if base.isValid() else layer

    @staticmethod
    def _histogram_key(layer: Any, band: int, derivative: Any = None) -> Tuple[str, int, str]:
        """Histograms are read on the original raster (see :meth:`_base_raster`): a filter keeps the key."""
        try:
            from ...adapters.qgis.coverage_layers.snapshots import registry
            snapshot = registry().get(layer.id())
        except Exception:
            snapshot = None
        source = snapshot.original_source if snapshot is not None and snapshot.original_source else layer.source()
        quantity = derivative if isinstance(derivative, str) else getattr(derivative, 'value', 'value')
        return source, int(band), quantity

    def _on_raster_band_changed(self, band: int) -> None:
        if self._active_layer is not None:
            try:
                self._refresh_histogram(self._active_layer, band)
            except Exception as exc:
                logger.debug(f"[FM5] histogram not refreshed: {exc}")

    def _release_raster_range_link(self) -> None:
        extras = self._extras
        if extras is not None:
            button = extras._tools.get('pushButton_checkable_exploring_raster_link')
            if button is not None and button.isChecked():
                button.setChecked(False)

    def _restore_raster_band_display(self, layer: Any) -> None:
        if self._raster_band_display is not None:
            self._release_raster_range_link()
            try:
                self._raster_band_display.restore(layer)
            except RuntimeError:
                pass  # QGIS already deleted the layer
            self._raster_band_display = None
            self._extras_call('_sync_derivative_tools')

    def _on_raster_display_changed(self, request_statistics: bool = True) -> None:
        """Display chosen bands using sampled worker statistics and retain the layer style."""
        layer, panel = self._active_layer, self._raster_panel
        if layer is None or panel is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import clear_selection_preview
        bands = panel.display_bands()
        if not bands:
            if self._raster_band_display is not None:
                clear_selection_preview(layer)
                self._restore_raster_band_display(layer)
                if self._preview_wanted():
                    self._apply_raster_preview()
            return
        source = self._histogram_key(layer, panel.current_band())[0]
        ranges = {band: self._raster_display_ranges[(source, band)] for band in bands
                  if (source, band) in self._raster_display_ranges}
        if any(band > 0 and band not in ranges for band in bands):
            if request_statistics:
                panel.set_display_status(self.tr("Preparing band display…"))
                quantity = self._quantity_expression() or panel.current_derivative()
                self._request_raster_statistics(layer, panel.current_band(), panel.current_derivative(),
                                                self._histogram_key(layer, panel.current_band(), quantity))
            else:
                self._restore_raster_band_display(layer)
                panel.set_display_status(self.tr("No valid pixels to display in the selected bands."))
            return
        self._release_raster_range_link()
        clear_selection_preview(layer)
        from ...adapters.qgis.coverage_layers.band_display import RasterBandDisplay
        if self._raster_band_display is None:
            self._raster_band_display = RasterBandDisplay()
        if self._raster_band_display.apply(layer, bands, ranges):
            panel.set_display_status('')
        else:
            panel.set_display_status(self.tr("The selected bands could not be displayed."))
        if self._preview_wanted():
            self._apply_raster_preview()

    def _update_kept_ratio(self) -> None:
        panel, layer = self._raster_panel, self._active_layer
        if panel is None or layer is None:
            return
        selection = panel.selection()
        if _detects_objects(selection):
            result = self._detected_result(layer, selection)
            total = getattr(result, 'total_pixels', 0)
            panel.set_kept_ratio(result.kept_pixels / total if result is not None and total else None)
            return
        quantity = self._quantity_expression()
        bounds = panel.histogram_range() if hasattr(panel, 'histogram_range') else None
        if selection is not None and quantity and isinstance(bounds, tuple) and len(bounds) == 2:
            cached = self._histogram_cache.get(self._histogram_key(layer, panel.current_band(), quantity))
            if cached is None or not sum(cached[0]):
                panel.set_kept_ratio(None)
                return
            counts, minimum, maximum = cached
            low, high = bounds
            step = (maximum - minimum) / len(counts)
            kept = sum(count for index, count in enumerate(counts)
                       if (low is None or minimum + (index + 0.5) * step >= low)
                       and (high is None or minimum + (index + 0.5) * step <= high))
            panel.set_kept_ratio(kept / sum(counts))
            return
        if selection is not None and _is_expression(selection):
            # A colour of the pipette, a spectral preset: no histogram tells, the expression is read, for
            # the preview only (half a second on this thread) and once the input settles.
            surface = self._selection_surface(layer, selection, read=False) if self._preview_wanted() else None
            panel.set_kept_ratio(surface.kept_ratio if surface is not None else None)
            return
        cached = self._histogram_cache.get(self._histogram_key(layer, panel.current_band(), panel.current_derivative()))
        if selection is None or cached is None or not cached[0]:
            panel.set_kept_ratio(None)
            return
        counts, minimum, maximum = cached
        total = float(sum(counts)) or 1.0
        width = (maximum - minimum) / len(counts) if counts else 1.0
        kept = 0
        for index, count in enumerate(counts):
            centre = minimum + (index + 0.5) * width
            try:
                if selection.keeps(centre):
                    kept += count
            except ValueError:
                pass
        panel.set_kept_ratio(kept / total)

    def _on_raster_selection_changed(self) -> None:
        if self._active_layer is not None and (self._quantity_expression() or self._uses_expression_histogram()
                                               or self._raster_stats_task is not None):
            self._refresh_histogram(self._active_layer, self._raster_panel.current_band())
        self._show_detected_objects()
        self._update_kept_ratio()
        panel = self._raster_panel
        selection = panel.selection() if panel is not None else None
        if selection is not None and _is_expression(selection):
            self._validate_raster_expression(selection.expression)
        if panel is not None and (panel.preview_enabled() or self._preview_active):
            self._apply_raster_preview()

    def _validate_raster_expression(self, expression: str) -> bool:
        try:
            from ...adapters.qgis.coverage_layers.raster_adapter import raster_expression_error, raster_reference
            layer = self._active_layer
            if layer is None:
                return True
            error = raster_expression_error(expression, raster_reference(layer), layer.bandCount())
            message = (self.tr("Unknown raster layer or band in expression") if error == 'bands' else
                       self.tr("Invalid raster calculator expression") if error else '')
            self._raster_panel.set_expression_status(not error, message)
            if not error and self._raster_stats_task is not None:
                self._call(self._raster_panel, 'set_histogram_pending')
            return not error
        except Exception as exc:
            logger.debug(f"[FM5] raster expression not validated: {exc}")
            return True

    def _on_raster_preview_toggled(self, enabled: bool) -> None:
        # The rail preview button is the only switch: the panel only keeps its state.
        self._set_selecting_checked(enabled)
        self._call(self._raster_panel, 'set_preview_checked', enabled)
        self._preview_active = bool(enabled)
        if enabled:
            self._apply_raster_preview()
        elif self._active_layer is not None:
            self._stop_preview(self._active_layer)
            self._update_kept_ratio()  # an expression is no longer read: its share is unknown again

    def _apply_raster_preview(self) -> None:
        layer, panel = self._active_layer, self._raster_panel
        if layer is None or panel is None:
            return
        from ...adapters.qgis.coverage_layers.raster_adapter import apply_selection_preview, clear_selection_preview
        selection = panel.selection()
        if _is_expression(selection) and not self._validate_raster_expression(selection.expression):
            clear_selection_preview(layer)
            self._hide_derivative_preview()
            return
        if _detects_objects(selection):
            # Detected objects: their outline is the preview, a veil would show every pixel of their colour.
            clear_selection_preview(layer)
            self._hide_derivative_preview()
            return
        display_bands = panel.display_bands()
        displayed_elsewhere = bool(display_bands and display_bands != (selection.band,)) if selection is not None else False
        if selection is not None and (selection.derivative.is_terrain or _is_expression(selection) or displayed_elsewhere):
            # Neither a slope nor a colour (several bands) is a value of the band the renderer makes transparent.
            clear_selection_preview(layer)  # a value preview left from before the quantity changed
            self._show_derivative_preview(layer, selection)
            return
        self._hide_derivative_preview()
        if selection is None:
            clear_selection_preview(layer)  # nothing selected: every pixel shows again
        else:
            apply_selection_preview(layer, selection)

    def _preview_wanted(self) -> bool:
        panel = self._raster_panel
        return panel is not None and bool(panel.preview_enabled() or self._preview_active)

    def _surface_key(self, layer: Any, selection: Any) -> tuple:
        source = self._histogram_key(layer, 0)[0]  # the original raster when the layer shows a derived one
        if self._raster_needs_sample(layer):
            sample = self._local_raster_sample(layer)
            source = sample.source() if sample is not None else source
        if _is_expression(selection):
            return source, layer.name(), selection.expression  # the name is the reference the expression reads
        return source, selection.band, selection.derivative

    def _selection_surface(self, layer: Any, selection: Any, read: bool = True) -> Any:
        """Grid of the original raster that veils ``selection``: a terrain derivative, or the
        pixels an expression keeps (colour pipette); None when unreadable.

        The last :data:`SURFACE_CACHE_SIZE` grids are kept. ``read`` False: an expression
        not read yet is not read now, a read is scheduled (:meth:`_read_expression`).
        """
        try:
            key = self._surface_key(layer, selection)
            pending = self._raster_surface_task
            if pending is not None:
                if pending.identity[1] != key:
                    self._cancel_raster_surface()
                elif key not in self._surfaces:
                    return None
            if key in self._surfaces:
                self._surfaces.move_to_end(key)
                return self._surfaces[key]
            if not read and not self._raster_needs_sample(layer):
                self._schedule_expression_read()
                return None
            self._request_raster_surface(layer, selection, key)
            return None
        except RuntimeError as exc:
            logger.debug(f"[FM5] selection not read for its preview, layer deleted: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"[FM5] selection not read for its preview: {exc}")
            surface = None  # kept as such: not read again at each input change
        self._surfaces[key] = surface
        while len(self._surfaces) > SURFACE_CACHE_SIZE:
            self._surfaces.popitem(last=False)
        return surface

    def _cancel_raster_surface(self):
        task, self._raster_surface_task = self._raster_surface_task, None
        if task is not None:
            task.cancel()

    def _request_raster_surface(self, layer, selection, key):
        sampled = self._raster_needs_sample(layer)
        sample = self._local_raster_sample(layer) if sampled else None
        if sampled and sample is None:
            return
        source = sample.source() if sample is not None else self._histogram_key(layer, 0)[0]
        provider = 'gdal' if sampled else self._raster_capability(layer).provider_key
        identity = self._raster_identity(layer), key, source
        if self._raster_surface_task is not None and self._raster_surface_task.identity == identity:
            return
        self._cancel_raster_surface()
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.raster_surface_task import RasterSurfaceTask
        task = RasterSurfaceTask(source, layer.name(), selection, self._raster_surface_ready, provider=provider)
        task.identity = identity
        self._borrow_raster_sample(task, sample.source() if sample is not None else '')
        self._raster_surface_task = task
        QgsApplication.taskManager().addTask(task)

    def _raster_surface_ready(self, task, ok):
        self._return_raster_sample(task)
        if task is not self._raster_surface_task:
            return
        self._raster_surface_task = None
        layer, panel = self._active_layer, self._raster_panel
        if layer is None or panel is None:
            return
        selection = panel.selection()
        sampled = self._raster_needs_sample(layer)
        sample = self._local_raster_sample(layer) if sampled else None
        if selection is None or (sampled and sample is None):
            return
        key = self._surface_key(layer, selection)
        source = sample.source() if sample is not None else self._histogram_key(layer, 0)[0]
        if (self._raster_identity(layer), key, source) != task.identity:
            return
        self._surfaces[key] = task.surface if ok else None
        while len(self._surfaces) > SURFACE_CACHE_SIZE:
            self._surfaces.popitem(last=False)
        if not ok:
            panel.set_stream_notice(self.tr("The raster preview could not be calculated."))
        self._update_kept_ratio()
        if self._preview_wanted():
            self._apply_raster_preview()

    def _schedule_expression_read(self) -> None:
        if self._expression_timer is None:
            from qgis.PyQt.QtCore import QTimer
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(EXPRESSION_READ_DELAY_MS)
            timer.timeout.connect(self._read_expression)
            self._expression_timer = timer
        self._expression_timer.start()  # restarted by each change: one read once the input settles

    def _expression_pending(self) -> bool:
        timer = self._expression_timer
        return self._raster_surface_task is not None or (timer is not None and bool(timer.isActive()))

    def _read_expression(self) -> None:
        """The input settled: read the expression of the panel, then show its share and its veil."""
        layer, panel = self._active_layer, self._raster_panel
        if getattr(self, '_torn_down', False) or layer is None or panel is None or not self._preview_wanted():
            return
        selection = panel.selection()
        if selection is None or not _is_expression(selection):
            return
        self._selection_surface(layer, selection)
        self._update_kept_ratio()
        self._apply_raster_preview()

    def _show_derivative_preview(self, layer: Any, selection: Any) -> None:
        """Veil the pixels a slope / aspect / ... or an expression selection drops (a canvas item, no layer is added)."""
        iface = self._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        if canvas is None:
            return
        try:
            from ...adapters.qgis.coverage_layers.preview_overlay import MaskOverlay, fits_canvas
            expression = _is_expression(selection)
            surface = self._selection_surface(layer, selection, read=not expression)
            if surface is None and expression and self._expression_pending():
                return  # the veil shown stays until the new expression is read
            veil = surface.veil(selection) if surface is not None else None
            if veil is None:
                self._hide_derivative_preview()
                return
            canvas_crs = canvas.mapSettings().destinationCrs()
            if not fits_canvas(surface, canvas_crs):
                self._hide_derivative_preview()
                notice = (surface, canvas_crs.authid() or canvas_crs.toWkt())
                if self._crs_notice is None or self._crs_notice[0] is not notice[0] or self._crs_notice[1] != notice[1]:
                    self._crs_notice = notice  # told once, not at each input change
                    crs = surface.crs_authid or surface.crs.description()
                    message = (self.tr("The preview of a slope or aspect needs the map in the CRS of the raster ({0})")
                               if selection.derivative.is_terrain else
                               self.tr("The preview of a color or an expression needs the map in the CRS of the raster ({0})"))
                    iface.messageBar().pushInfo("FilterMate", message.format(crs))
                return
            if self._mask_overlay is None:
                self._mask_overlay = MaskOverlay(canvas)
            self._mask_overlay.show(veil, surface.extent)
        except Exception as exc:
            logger.warning(f"[FM5] derivative preview failed: {exc}", exc_info=True)

    def _hide_derivative_preview(self) -> None:
        if self._mask_overlay is not None:
            self._mask_overlay.hide()

    # === Object detection (pipette) ===

    def _detected_result(self, layer: Any, selection: Any, read: bool = False) -> Any:
        """Objects under the clicks of ``selection`` (a SelectionGeometryResult), None when not read.

        ``read`` True reads them when they are not the last ones read: a window of
        native pixels around each click, on this thread (a click, a tolerance that settled).
        """
        try:
            key = (self._histogram_key(layer, 0)[0], layer.name(), selection)
        except RuntimeError:
            return None  # layer deleted
        if self._detected is not None and self._detected[0] == key:
            return self._detected[1]
        if not read:
            return None
        from ...adapters.qgis.coverage_layers.raster_adapter import layer_object_geometry
        try:
            from qgis.PyQt.QtCore import Qt
            from qgis.PyQt.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        except Exception:
            QApplication = None
        try:
            result = layer_object_geometry(self._base_raster(layer), selection)
        except RuntimeError as exc:
            logger.debug(f"[FM5] objects not detected, layer deleted: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"[FM5] object detection failed: {exc}", exc_info=True)
            return None  # not kept: the same selection is read again at its next change
        finally:
            if QApplication is not None:
                QApplication.restoreOverrideCursor()
        self._detected = (key, result)
        return result

    def _show_detected_objects(self) -> None:
        """Detect the objects under the pipette clicks, outline them and tell their number and area."""
        layer, panel = self._active_layer, self._raster_panel
        selection = panel.selection() if panel is not None else None
        if layer is None or not _detects_objects(selection):
            self._hide_detected_objects()
            return
        result = self._detected_result(layer, selection, read=True)
        if result is None:
            self._hide_detected_objects()
            self._call(panel, 'show_detected_objects', None)
            return
        geometry = result.geometry
        area = None
        if geometry is not None and not geometry.isEmpty():
            area = self._ground_area(geometry, layer)
        # The objects found, not the parts of their union: two touching objects are still two.
        self._call(panel, 'show_detected_objects', result.objects, area, result.truncated)
        self._update_kept_ratio()  # read now: a ratio asked before (a layer coming back) found none
        self._extras_call('schedule_strip')
        iface = self._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        if canvas is None:
            return
        try:
            if self._object_outline is None:
                from ...adapters.qgis.coverage_layers.preview_overlay import ObjectOutline
                self._object_outline = ObjectOutline(canvas)
            self._object_outline.show(geometry, layer)
        except Exception as exc:
            logger.warning(f"[FM5] detected objects not drawn: {exc}", exc_info=True)

    @staticmethod
    def _ground_area(geometry: Any, layer: Any) -> Optional[float]:
        """Area of ``geometry`` (layer CRS) in square metres, on the project ellipsoid; None when unknown."""
        try:
            from qgis.core import Qgis, QgsDistanceArea, QgsProject, QgsUnitTypes
            measure = QgsDistanceArea()
            project = QgsProject.instance()
            measure.setSourceCrs(layer.crs(), project.transformContext())
            measure.setEllipsoid(project.ellipsoid() or 'NONE')
            area_unit = getattr(Qgis, 'AreaUnit', None)
            square_metres = area_unit.SquareMeters if area_unit is not None else QgsUnitTypes.AreaUnit.AreaSquareMeters
            return float(measure.convertAreaMeasurement(measure.measureArea(geometry), square_metres))
        except Exception as exc:
            logger.debug(f"[FM5] area of the detected objects unknown: {exc}")
            return None

    def _hide_detected_objects(self) -> None:
        self._pc_outline_wkt = ''
        if self._object_outline is not None:
            self._object_outline.hide()

    def _populate_point_cloud(self, layer: Any, keep_kept: bool = False) -> None:
        try:
            from ...adapters.qgis.point_cloud_layer_adapter import read_point_cloud_summary
            from ...adapters.qgis.coverage_layers import pdal_cli
            self._watch_point_cloud_statistics(layer)
            kept = self._pc_panel.point_counts()[0] if keep_kept and hasattr(self._pc_panel, 'point_counts') else None
            summary = read_point_cloud_summary(layer)
            self._pc_panel.populate(summary)
            self._pc_panel.set_current_subset(layer.subsetString())
            self._pc_panel.set_point_counts(kept, getattr(summary, 'point_count', None))
            reason = pdal_cli.copc_unavailable_reason()
            if not reason:
                message = ''
            elif not pdal_cli.is_available():
                message = self.tr("PDAL was not found: the height above a DTM needs the pdal executable")
            elif pdal_cli.version() is not None:
                message = self.tr("PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later").format(
                    '.'.join(map(str, pdal_cli.version())))
            else:
                message = self.tr("PDAL could not be run, the height above a DTM is unavailable: {0}").format(reason)
            self._pc_panel.set_hag_available(not message, message)
        except Exception as exc:
            logger.warning(f"[FM5] point cloud panel not populated: {exc}", exc_info=True)

    def _watch_point_cloud_statistics(self, layer: Any) -> None:
        """Refresh the panel when QGIS finishes the statistics of the layer (computed in the background
        after loading: until then only some attributes, often Z alone, have a range)."""
        signal = getattr(layer, 'statisticsCalculationStateChanged', None)
        if signal is None or layer.id() in self._stats_watched:
            return
        layer_id = layer.id()
        slot = lambda *_args, lid=layer_id: self._on_point_cloud_statistics(lid)  # noqa: E731
        signal.connect(slot)
        self._stats_watched.add(layer_id)
        self._stats_slots[layer_id] = (layer, slot)

    def _disconnect_point_cloud_statistics(self) -> None:
        """Teardown: the point cloud layers outlive the controller; their statistics signal must not call it."""
        for layer, slot in list(self._stats_slots.values()):
            try:
                layer.statisticsCalculationStateChanged.disconnect(slot)
            except (TypeError, RuntimeError, AttributeError):  # not connected / layer deleted
                pass
        self._stats_slots.clear()
        self._stats_watched.clear()

    def _on_point_cloud_statistics(self, layer_id: str) -> None:
        from ...core.domain.layer_kind import LayerKind
        layer = self._active_layer
        try:
            if layer is None or self._kind is not LayerKind.POINT_CLOUD or layer.id() != layer_id or self._pc_panel is None:
                return
            state = layer.statisticsCalculationState() if hasattr(layer, 'statisticsCalculationState') else None
            calculated = getattr(getattr(type(layer), 'PointCloudStatisticsCalculationState', None), 'Calculated', None)
            if calculated is not None and state != calculated:
                return
        except RuntimeError:
            return  # layer deleted
        logger.debug(f"[FM5] point cloud statistics ready, panel refreshed: {self._layer_name(layer)}")
        self._populate_point_cloud(layer, keep_kept=True)

    def _on_point_cloud_criteria_changed(self) -> None:
        selecting = getattr(self.dockwidget, 'pushButton_checkable_exploring_selecting', None)
        if selecting is not None and selecting.isChecked():
            self._apply_point_cloud_preview()
        self._show_point_cloud_objects()  # the objects apply while CLASSES is the active group only

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
        """Drop the live preview of ``layer``; the preview button (and box) follow, unchecked.

        A button left checked would bring the preview back at the next input
        change, on top of a filter just applied or an undo.
        """
        from ...core.domain.layer_kind import LayerKind
        self._hide_derivative_preview()  # its grids stay cached: the same layer comes back without a read
        if self._expression_timer is not None:
            self._expression_timer.stop()
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
        self._set_selecting_checked(False)
        if self._kind is LayerKind.RASTER:
            self._call(self._raster_panel, 'set_preview_checked', False)

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
            action: ``identify``, ``zoom``, ``select``, ``deselect``, ``reset`` or ``refresh`` (badge back
                after a vector refresh of the dock).

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
                    pass  # 2026-10-18: no pixel picker on a raster any more, the pipette reads the bands
                else:
                    self._toggle_class_tool()  # 2026-10-18: the Identify button is the class pipette
            elif action == 'zoom':
                if self._kind is LayerKind.RASTER:
                    self._zoom_to_selection(layer)  # mockup: zoom on the extent of the selected range
                else:
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
            elif action == 'refresh':
                self._show_kind_badge(layer, self._kind)  # after a vector refresh of the dock (layers added)
            elif action == 'backend':
                pass
            elif action == 'reset':
                self._stop_preview(layer)
                panel = self._current_panel()
                if panel is not None:
                    panel.reset()  # does not emit: its outline goes here
                self._restore_raster_band_display(layer)
                self._hide_detected_objects()
                self._sync_object_pick_mode()  # the target is back to the clicked object
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
        except Exception as exc:
            logger.debug(f"[FM5] extent not reprojected to the canvas CRS: {exc}")
        canvas.setExtent(extent)
        canvas.refresh()

    def _zoom_to_selection(self, layer: Any) -> None:
        """Zoom on the pixels kept by the raster range / classes; the whole layer without one."""
        panel = self._raster_panel
        selection = panel.selection() if panel is not None else None
        extent = None
        try:
            from ...adapters.qgis.coverage_layers.raster_adapter import selection_extent
            if _detects_objects(selection):
                result = self._detected_result(layer, selection, read=True)
                geometry = result.geometry if result is not None else None
                extent = geometry.boundingBox() if geometry is not None and not geometry.isEmpty() else None
            else:
                extent = selection_extent(self._base_raster(layer), selection) if selection is not None else None
        except Exception as exc:
            logger.debug(f"[FM5] extent of the selected range not computed: {exc}")
        if extent is None or extent.isEmpty():
            self._zoom_to(layer)
            return
        iface = self._iface()
        if iface is None:
            return
        from qgis.core import QgsCoordinateTransform, QgsProject
        canvas = iface.mapCanvas()
        try:
            transform = QgsCoordinateTransform(layer.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
            extent = transform.transformBoundingBox(extent)
        except Exception as exc:
            logger.debug(f"[FM5] extent not reprojected to the canvas CRS: {exc}")
        extent.scale(1.05)  # a small margin around the selected pixels
        canvas.setExtent(extent)
        canvas.refresh()

    def _zone_geometry(self, panel: Any = None) -> Any:
        """The shape drawn with the Zone tool on the point cloud (or the raster ``panel``), layer CRS, None without one."""
        panel = panel if panel is not None else self._pc_panel
        wkt = panel.zone_wkt() if panel is not None and hasattr(panel, 'zone_wkt') else ''
        if not wkt:
            return None
        try:
            from qgis.core import QgsGeometry
            geometry = QgsGeometry.fromWkt(wkt)
            return geometry if geometry is not None and not geometry.isEmpty() else None
        except Exception as exc:
            logger.debug(f"[FM5] zone of the point cloud unreadable: {exc}")
            return None

    def _toggle_class_tool(self) -> None:
        """The Identify button of a point cloud: the class pipette goes on the map, or leaves it.

        With the picker on the map as the value pipette, the click switches it to the class pipette.
        """
        on_map = self._tool_on_map(self._class_tool)
        self._on_class_pick_toggled(not on_map or self._pc_pick_mode != 'class', 'class')

    def _identify_point_cloud(self) -> None:
        """QGIS identify tool on the point cloud (kept for the automation API; the rail uses the class pipette)."""
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
            self._pixel_tool.activated.connect(lambda: self._show_picker_state(True))
            self._pixel_tool.deactivated.connect(lambda: self._show_picker_state(False))
        self._previous_map_tool = canvas.mapTool()
        canvas.setMapTool(self._pixel_tool)

    def _on_color_pick_toggled(self, enabled: bool, target: Optional[str] = None) -> None:
        """The pipette or the object detector of the rail: the pixel picker goes on the map (or leaves it) with it.

        Args:
            enabled: Whether the tool goes on the map.
            target: ``'similar'`` (the pipette) or ``'object'`` (the detector); None keeps the target of the panel.
        """
        panel = self._raster_panel
        if self._active_layer is not None and not self._raster_capability(self._active_layer).has_raw_values:
            target = 'similar'
        if target is not None and panel is not None and hasattr(panel, 'set_pick_target'):
            panel.set_pick_target(target)
        if target is None and panel is not None and hasattr(panel, 'pick_target'):
            target = panel.pick_target()
        self._color_pick = bool(enabled)
        self._extras_call('set_pipette_checked', self._color_pick, target or 'similar')
        if panel is not None:
            panel.show_pipette_active(self._color_pick)
        iface = self._iface()
        if iface is None:
            return
        on_map = self._pixel_tool is not None and iface.mapCanvas().mapTool() is self._pixel_tool
        if enabled and not on_map:
            self._toggle_pixel_tool()
        elif not enabled and on_map:
            self._deactivate_pixel_tool()

    def _on_raster_mode_chosen(self, mode: str) -> None:
        """The user made a group of the raster panel the active one: the pipette follows the PIPETTE group."""
        wanted = mode == 'pipette'
        if wanted == self._color_pick:
            return
        self._on_color_pick_toggled(wanted)

    def _show_picker_state(self, active: bool) -> None:
        """The picker tool went on or left the map: the pipette / detector buttons and the BANDS block follow."""
        if not active and self._color_pick:
            self._color_pick = False  # the picker was dropped (another tool, the rail button): the pipette goes off
            self._extras_call('set_pipette_checked', False)
            if self._raster_panel is not None:
                self._raster_panel.show_pipette_active(False)
        try:
            if self._raster_panel is not None and hasattr(self._raster_panel, 'show_picker_active'):
                self._raster_panel.show_picker_active(bool(active))
        except RuntimeError:
            pass  # deleted (plugin closing)

    def _deactivate_pixel_tool(self) -> None:
        if self._pixel_tool is None:
            return
        previous, self._previous_map_tool = self._previous_map_tool, None
        self._release_map_tool(self._pixel_tool, previous)

    def _drop_map_tools(self) -> None:
        """Delete the pixel and class pickers (made again on demand); their destructor takes them off the
        canvas and out of the tool QGIS gives back after Pan / Zoom."""
        self._previous_map_tool = self._previous_class_map_tool = None
        for tool_name in ('_pixel_tool', '_class_tool'):
            tool = getattr(self, tool_name)
            setattr(self, tool_name, None)
            if tool is not None:
                try:
                    tool.deleteLater()
                except RuntimeError:
                    pass  # already deleted (QGIS closing)

    def _release_map_tool(self, tool: Any, previous: Any) -> None:
        """Take ``tool`` off the map and give the map back to the tool it replaced."""
        iface = self._iface()
        if iface is None:
            return
        try:
            canvas = iface.mapCanvas()
            if canvas.mapTool() is not tool:
                return
            if previous is not None:
                try:
                    canvas.setMapTool(previous)
                    return
                except RuntimeError:
                    pass  # the previous tool was deleted: no tool rather than the picker
            canvas.unsetMapTool(tool)
        except RuntimeError as exc:
            logger.debug(f"[FM5] picker not released: {exc}")  # canvas deleted (QGIS closing)

    # === Point cloud: class pipette ===

    def _on_class_pick_toggled(self, enabled: bool, mode: str = 'class') -> None:
        """The class pipette (Identify), the object detector or the value pipette of the rail: one picker in the
        point cloud colour.

        Args:
            enabled: Whether the picker goes on the map.
            mode: ``'class'`` (a click checks the class in CLASSES), ``'object'`` / ``'similar'`` (the object
                detector: a click selects the object under it, or every object like it, in CLASSES) or
                ``'value'`` (a click writes a condition on the attribute chosen in ATTRIBUTES).
        """
        iface = self._iface()
        if iface is None:
            return
        if not enabled:
            self._deactivate_class_tool()
            return
        self._pc_pick_mode = mode if mode in PC_PICK_MODES else 'class'
        canvas = iface.mapCanvas()
        if self._class_tool is not None and canvas.mapTool() is self._class_tool:
            self._extras_call('set_class_pipette_checked', True, self._pc_pick_mode)  # same tool, other button
            self._show_pc_pick_group()
            return
        if self._class_tool is None:
            from ..styles.mockup_design import KIND_COLORS
            from ..tools.pixel_picker_tool import PixelPickerTool
            self._class_tool = PixelPickerTool(canvas, KIND_COLORS['point_cloud'])
            self._class_tool.picked.connect(self._on_class_picked)
            # The rail button follows the map: up when another tool takes over, down when QGIS gives it back.
            self._class_tool.activated.connect(lambda: self._extras_call('set_class_pipette_checked', True, self._pc_pick_mode))
            self._class_tool.deactivated.connect(lambda: self._extras_call('set_class_pipette_checked', False, self._pc_pick_mode))
        self._previous_class_map_tool = canvas.mapTool()
        canvas.setMapTool(self._class_tool)
        self._show_pc_pick_group()

    def _show_pc_pick_group(self) -> None:
        """The group of the picker mode becomes the active one (R2)."""
        panel = self._pc_panel
        if panel is None:
            return
        if self._pc_pick_mode == 'value':
            self._call(panel, 'show_value_pipette_active')
        else:
            self._call(panel, 'show_class_pipette_active')

    def _on_value_pick_toggled(self, enabled: bool) -> None:
        """The value pipette of the rail (ATTRIBUTES)."""
        self._on_class_pick_toggled(enabled, 'value')

    def _on_object_pick_toggled(self, enabled: bool) -> None:
        """The object detector of the rail (CLASSES), in the target of the panel."""
        self._on_class_pick_toggled(enabled, self._object_pick_mode())

    def _object_pick_mode(self) -> str:
        """Picker mode of the target of the detector: ``'similar'`` for the similar objects, ``'object'`` otherwise."""
        panel = self._pc_panel
        target = panel.object_target() if panel is not None and hasattr(panel, 'object_target') else 'object'
        return 'similar' if target == 'similar_objects' else 'object'

    def _on_point_cloud_object_target(self, target: str) -> None:
        """A target of the detector chosen in the rail menus: the detector goes on the map in it (R4), the clicked
        objects are read again for it when it changed."""
        panel = self._pc_panel
        if panel is None or not hasattr(panel, 'set_object_target'):
            return
        changed = panel.set_object_target(target)
        # R4: a target chosen in the rail menus is the detector in that target, on the map, as the three
        # target buttons of the raster rail (the picker already there switches mode).
        self._on_class_pick_toggled(True, self._object_pick_mode())
        if changed:
            self._refresh_point_cloud_objects()

    def _on_point_cloud_group_chosen(self, group: str) -> None:
        """The user made a group of the point cloud panel the active one: its tool follows (R1).

        CLASSES arms the class pipette (the object detector stays if it is on), ATTRIBUTES the value
        pipette (the zone tool stays if it is on), EXPRESSION takes the picker off the map.
        """
        iface = self._iface()
        if iface is None:
            return
        on_map = self._class_tool is not None and iface.mapCanvas().mapTool() is self._class_tool
        if group == 'classes':
            if not on_map or self._pc_pick_mode not in ('class', *PC_OBJECT_MODES):
                self._on_class_pick_toggled(True, 'class')  # the tool's activated signal puts the rail button down
            self._extras_call('stop_zone_tool')
        elif group == 'ranges':
            if self._extras_zone_on():
                return  # the zone tool made the group active: keep it
            if not on_map or self._pc_pick_mode != 'value':
                self._on_class_pick_toggled(True, 'value')
        else:
            if on_map:
                self._deactivate_class_tool()
            self._extras_call('stop_zone_tool')

    def _extras_zone_on(self) -> bool:
        extras = self._extras
        try:
            return bool(extras is not None and extras.zone_tool_on())
        except Exception:
            return False

    def _deactivate_class_tool(self) -> None:
        if self._class_tool is None:
            return
        previous, self._previous_class_map_tool = self._previous_class_map_tool, None
        self._release_map_tool(self._class_tool, previous)

    def _on_class_picked(self, point: Any, extend: bool) -> None:
        """Check the class of the points under the click (Ctrl+click: added to the checked classes).

        As the value pipette, the click writes a condition on the chosen attribute instead.
        """
        from ...core.domain.layer_kind import LayerKind
        layer, panel, iface = self._active_layer, self._pc_panel, self._iface()
        if layer is None or panel is None or iface is None or self._kind is not LayerKind.POINT_CLOUD:
            return
        if self._pc_pick_mode == 'value':
            self._on_value_picked(point, extend)
            return
        if self._pc_pick_mode in PC_OBJECT_MODES:
            self._on_object_picked(point, extend)
            return
        from ...adapters.qgis.point_cloud_layer_adapter import class_at
        code = class_at(layer, iface.mapCanvas(), point)
        selecting = getattr(self.dockwidget, 'pushButton_checkable_exploring_selecting', None)
        previewed = selecting is not None and selecting.isChecked()
        hidden = self.tr("only the points drawn on the map can be picked: turn the preview off to pick a class it hides")
        if code is None:
            message = self.tr("No classified point under the click")
            if previewed:
                message = f"{message}: {hidden}"
        elif previewed and extend and code in panel.checked_class_codes():
            message = self.tr("Class {0} is already checked").format(code) + f": {hidden}"
        elif not panel.select_class(code, extend):
            message = self.tr("Class {0} is not in the class list of the layer").format(code)
        else:
            return
        try:
            iface.messageBar().pushInfo("FilterMate", message)
        except RuntimeError:
            pass  # message bar deleted (QGIS closing)

    def _on_value_picked(self, point: Any, extend: bool) -> None:
        """The value pipette: a condition ``attribute between v - d and v + d`` on the attribute of the panel."""
        layer, panel, iface = self._active_layer, self._pc_panel, self._iface()
        from ...adapters.qgis.point_cloud_layer_adapter import attribute_value, attributes_at
        attribute = panel.pick_attribute()
        attributes = attributes_at(layer, iface.mapCanvas(), point)
        value = attribute_value(attributes, attribute)
        if attributes is None:
            message = self.tr("No point drawn under the click")
        elif value is None:
            message = self.tr("This point has no {0}").format(attribute)
        elif not panel.add_value_condition(attribute, value, extend):
            message = self.tr("{0} cannot be used in a condition").format(attribute)
        else:
            return
        try:
            iface.messageBar().pushInfo("FilterMate", message)
        except RuntimeError:
            pass  # message bar deleted (QGIS closing)

    # === Point cloud: object detector ===

    def _on_object_picked(self, point: Any, extend: bool) -> None:
        """The object detector: the object of the class clicked under ``point`` (canvas CRS); Ctrl+click adds one.

        Each object keeps its class; a second click inside an object of the same class adds nothing.
        The objects are read once: the new one, or (the target changed) those clicked before.
        """
        panel, iface = self._pc_panel, self._iface()
        # The mode of the picker is the target (they only differ if the panel was restored apart from the tool).
        retargeted = panel.set_object_target('similar_objects' if self._pc_pick_mode == 'similar' else 'object')
        message, added = self._pick_point_cloud_object(self._active_layer, panel, iface.mapCanvas(), point, extend)
        if added or retargeted:
            self._refresh_point_cloud_objects()
        if message:
            self._push_info(message)

    def _pick_point_cloud_object(self, layer: Any, panel: Any, canvas: Any, point: Any, extend: bool) -> Tuple[str, bool]:
        """``(message, added)`` of a click of the detector: the object under it handed to the panel.

        The class is the one the class pipette reads (the points drawn there), the object the cluster
        of points of that class around the click (``point_cloud_objects.object_footprint``). While a
        preview is applied to the layer, both are read on a copy of the layer filtered on its own
        filter (:meth:`_object_reader`): the preview hides the other buildings.
        """
        from ...adapters.qgis.coverage_layers.point_cloud_objects import class_under, object_footprint
        from ...adapters.qgis.point_cloud_layer_adapter import class_at
        x, y, radius = self._layer_click(layer, canvas, point)
        try:
            with _wait_cursor():
                reader, on_map = self._object_reader(layer)
                code = class_at(layer, canvas, point) if on_map else class_under(reader, x, y, radius)
        except RuntimeError as exc:
            return self.tr("Object not read: {0}").format(exc), False
        if code is None:
            return self.tr("No classified point under the click"), False
        if extend and any(item['code'] == code and self._contains(item['wkt'], x, y) for item in panel.object_items()):
            return '', False  # a second click on the same building
        try:
            with _wait_cursor():
                found = object_footprint(reader, x, y, code, seed_radius=radius)
        except RuntimeError as exc:
            logger.debug(f"[FM5] point cloud object not read, layer deleted: {exc}")
            return '', False
        except Exception as exc:
            logger.warning(f"[FM5] point cloud object detection failed: {exc}", exc_info=True)
            return '', False
        geometry = found.geometry
        if found.message:
            return self.tr("Object not read: {0}").format(found.message), False
        if (geometry is None or geometry.isEmpty()) and found.truncated:
            return self.tr("Too many points around the click: the object could not be read"), False
        if geometry is None or geometry.isEmpty():
            return self.tr("No point of class {0} under the click: click on the object itself").format(code), False
        box = geometry.boundingBox()
        item = {"x": x, "y": y, "code": code, "wkt": geometry.asWkt(WKT_PRECISION), "truncated": found.truncated,
                "box": [box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()]}
        if panel.add_object(item, extend):
            return '', True
        return self.tr("Class {0} is not in the class list of the layer").format(code), False

    def _object_reader(self, layer: Any) -> Tuple[Any, bool]:
        """``(layer read, read on the map)`` for a click of the detector.

        The project layer itself (its class read on the map, as the class pipette), unless a preview is
        applied to it: then a private copy filtered on the filter the preview was put over (the one the
        similar objects are read through), opened once for the layer and that filter.

        Raises:
            RuntimeError: The copy cannot be read.
        """
        base = self._preview_base_subset
        if base is None or (layer.subsetString() or '') == (base or ''):
            return layer, True
        key = (layer.id(), layer.source(), layer.providerType(), base)
        if self._pc_reader is not None and self._pc_reader[0] == key:
            return self._pc_reader[1], False
        from ...adapters.qgis.coverage_layers.point_cloud_objects import base_copy
        copy = base_copy(layer, base)
        self._pc_reader = (key, copy)
        return copy, False

    def _sync_object_pick_mode(self) -> None:
        """The detector on the map follows the target of the panel (a reset brings it back to the clicked object)."""
        if self._pc_pick_mode in PC_OBJECT_MODES and self._tool_on_map(self._class_tool):
            mode = self._object_pick_mode()
            if mode != self._pc_pick_mode:
                self._pc_pick_mode = mode
                self._extras_call('set_class_pipette_checked', True, mode)

    def _push_info(self, message: str) -> None:
        iface = self._iface()
        try:
            if iface is not None:
                iface.messageBar().pushInfo("FilterMate", message)
        except RuntimeError:
            pass  # message bar deleted (QGIS closing)

    @staticmethod
    def _layer_click(layer: Any, canvas: Any, point: Any) -> Tuple[float, float, float]:
        """``(x, y, search radius)`` of a click in the CRS of ``layer``: the radius of the QGIS identify tool."""
        from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsProject
        try:
            from qgis.gui import QgsMapTool
            search = float(QgsMapTool.searchRadiusMU(canvas))
        except Exception:
            search = 0.0
        try:
            transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
            here = transform.transform(point)
            there = transform.transform(QgsPointXY(point.x() + search, point.y()))
            return here.x(), here.y(), math.hypot(there.x() - here.x(), there.y() - here.y())
        except Exception:
            return point.x(), point.y(), search

    @staticmethod
    def _contains(wkt: str, x: float, y: float) -> bool:
        """Whether the object of ``wkt`` holds ``(x, y)`` (same CRS)."""
        try:
            from qgis.core import QgsGeometry, QgsPointXY
            geometry = QgsGeometry.fromWkt(wkt) if wkt else None
            return bool(geometry is not None and not geometry.isEmpty() and geometry.contains(QgsPointXY(x, y)))
        except Exception:  # noqa: BLE001 - a geometry that cannot tell is not a hit
            return False

    def _refresh_point_cloud_objects(self) -> None:
        """Read what the clicked objects select (them, or the similar ones), hand it to the panel and outline it."""
        from ...core.domain.layer_kind import LayerKind
        layer, panel = self._active_layer, self._pc_panel
        if layer is None or panel is None or self._kind is not LayerKind.POINT_CLOUD or not hasattr(panel, 'object_items'):
            return
        items = panel.object_items()
        if not items:
            self._hide_detected_objects()  # dropped (the class list edited by hand)
            self._extras_call('schedule_strip')
            return
        try:
            from qgis.core import QgsGeometry
            from ...adapters.qgis.coverage_layers.geometry_tools import union_geometries
            shapes = [QgsGeometry.fromWkt(item['wkt']) for item in items]
            truncated = any(item['truncated'] for item in items)
            found = None
            if panel.object_target() == 'similar_objects':
                found = self._similar_point_cloud_objects(layer, items, shapes, panel.object_ratio())
            if found is None:  # the clicked objects (also when the similar ones could not be read)
                geometry = union_geometries([shape for shape in shapes if shape is not None and not shape.isEmpty()])
                boxes = [[item['code'], *item['box']] for item in items]
                count = len(items)
            else:
                geometry, boxes, count, cut = found
                truncated = truncated or cut
            empty = geometry is None or geometry.isEmpty()
            area = None if empty else self._ground_area(geometry, layer)
            panel.set_detected_objects('' if empty else geometry.asWkt(WKT_PRECISION), boxes, count, area, truncated)
        except RuntimeError as exc:
            logger.debug(f"[FM5] point cloud objects not read, layer deleted: {exc}")
            return
        except Exception as exc:
            logger.warning(f"[FM5] point cloud objects not read: {exc}", exc_info=True)
            return
        self._extras_call('schedule_strip')
        self._show_point_cloud_objects()

    def _similar_point_cloud_objects(self, layer: Any, items: List[dict], shapes: List[Any],
                                     ratio: Tuple[float, float]) -> Optional[tuple]:
        """``(geometry, boxes, count, truncated)`` of every object like the clicked ones, class by class; None when
        none could be read (said on the message bar), the clicked objects then stay the selection.

        Read through the filter of the layer, not its live preview (which keeps the clicked objects only).
        """
        from ...adapters.qgis.coverage_layers.geometry_tools import union_geometries
        from ...adapters.qgis.coverage_layers.point_cloud_objects import similar_objects_footprint
        base = self._preview_base_subset if self._preview_base_subset is not None else layer.subsetString()
        areas: Dict[int, List[float]] = {}
        for item, shape in zip(items, shapes):
            if shape is not None and not shape.isEmpty():
                areas.setdefault(item['code'], []).append(shape.area())  # layer units², as the footprint parts
        geometries, boxes, truncated = [], [], False
        try:
            with _wait_cursor():
                for code in sorted(areas):
                    found = similar_objects_footprint(layer, code, areas[code], ratio, base_subset=base,
                                                      footprint=self._class_footprint(layer, code, base))
                    truncated = truncated or found.truncated
                    if found.parts:
                        geometries.append(found.geometry)
                    for part in found.parts:
                        box = part.boundingBox()
                        boxes.append([code, box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()])
        except RuntimeError as exc:
            self._push_info(self.tr("Similar objects not read: {0}").format(exc))
            return None
        if not boxes:
            self._push_info(self.tr("No similar object within the area ratios: widen them"))
            return None
        return union_geometries(geometries), boxes, len(boxes), truncated

    def _class_footprint(self, layer: Any, code: int, base_subset: str) -> Any:
        """Footprint of a whole class of ``layer`` (``point_cloud_objects.class_footprint``), the last few kept."""
        key = (layer.id(), layer.source(), base_subset or '', int(code))
        cached = self._pc_footprints.get(key)
        if cached is not None:
            self._pc_footprints.move_to_end(key)
            return cached
        from ...adapters.qgis.coverage_layers.point_cloud_objects import class_footprint
        footprint = class_footprint(layer, code, base_subset)
        self._pc_footprints[key] = footprint
        while len(self._pc_footprints) > PC_FOOTPRINT_CACHE_SIZE:
            self._pc_footprints.popitem(last=False)
        return footprint

    def _show_point_cloud_objects(self) -> None:
        """Outline the objects of the detector while CLASSES is the active group (what the panel holds, no read)."""
        from ...core.domain.layer_kind import LayerKind
        layer, panel = self._active_layer, self._pc_panel
        if layer is None or panel is None or self._kind is not LayerKind.POINT_CLOUD:
            return  # a late signal of the point cloud panel: never the outline of a raster
        wkt = panel.object_zone_wkt() if hasattr(panel, 'object_zone_wkt') else ''
        if not wkt:
            if self._pc_outline_wkt:
                self._hide_detected_objects()
            return
        if wkt == self._pc_outline_wkt:
            return
        iface = self._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        if canvas is None:
            return
        try:
            from qgis.core import QgsGeometry
            if self._object_outline is None:
                from ...adapters.qgis.coverage_layers.preview_overlay import ObjectOutline
                self._object_outline = ObjectOutline(canvas)
            self._object_outline.show(QgsGeometry.fromWkt(wkt), layer)
            self._pc_outline_wkt = wkt
        except Exception as exc:
            logger.warning(f"[FM5] point cloud objects not drawn: {exc}", exc_info=True)

    def _on_pixel_picked(self, point: Any, extend: bool) -> None:
        from ...core.domain.layer_kind import LayerKind
        layer = self._active_layer
        if layer is None or self._raster_panel is None or self._kind is not LayerKind.RASTER:
            return
        from qgis.core import QgsCoordinateTransform, QgsProject
        from ...adapters.qgis.coverage_layers.raster_adapter import identify_values
        iface = self._iface()
        try:
            transform = QgsCoordinateTransform(iface.mapCanvas().mapSettings().destinationCrs(), layer.crs(), QgsProject.instance())
            layer_point = transform.transform(point)
        except Exception:
            layer_point = point
        try:
            base = self._base_raster(layer)
            if self._raster_needs_sample(layer) and not base.extent().contains(layer_point):
                self._cancel_raster_surface()
                self._release_raster_sample()
                self._raster_panel.reset()
                self._restore_raster_band_display(layer)
                if self._raster_capability(layer).has_raw_values:
                    self._refresh_histogram(layer, self._raster_panel.current_band())
                else:
                    self._request_rendered_capture(layer)
                self._push_info(self.tr("Preparing a sample for the new visible extent. Click again when it is ready."))
                return
            values = identify_values(base, layer_point)
            terrain = self._terrain_at(base, layer_point)
            quantity = self._quantity_expression()
            if quantity:
                from ...adapters.qgis.coverage_layers.raster_adapter import expression_value_at
                terrain['custom'] = expression_value_at(base, quantity, layer_point)
        except RuntimeError as exc:
            logger.debug(f"[FM5] pixel not read, layer deleted: {exc}")
            if self._raster_needs_sample(layer):
                self._push_info(self.tr("The local raster sample is still being prepared. Retry when it is ready."))
            return
        # With the colour pipette Ctrl+click adds a colour: it does not extend the range.
        self._raster_panel.set_pixel_values(layer_point.x(), layer_point.y(), values, extend and not self._color_pick, terrain)
        if self._color_pick:
            self._raster_panel.set_color_sample(values, extend, terrain, (layer_point.x(), layer_point.y()))

    def _terrain_at(self, base: Any, layer_point: Any) -> dict:
        """Slope, aspect... under ``layer_point`` while the range applies to one; empty otherwise."""
        panel = self._raster_panel
        if panel is None or not panel.current_derivative().is_terrain:
            return {}
        from ...adapters.qgis.coverage_layers.raster_adapter import terrain_values_at
        return terrain_values_at(base, layer_point, panel.current_band())

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
        get_centroids = getattr(self.dockwidget, 'get_centroid_target_ids', None)
        centroid_ids = set(get_centroids() or ()) if get_centroids is not None else set()
        specs = []
        for layer_id in layer_ids or []:
            if layer_id == exclude_id:
                continue
            layer = QgsProject.instance().mapLayer(layer_id)
            kind = _kind_of(layer)
            if layer is not None and kind.value != 'other':
                specs.append(TargetSpec(layer_id, kind, use_centroids=kind.value == 'vector' and layer_id in centroid_ids))
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
        try:
            from ...adapters.public_api.operations import busy_reason
            automation_busy = bool(busy_reason())
        except ImportError:
            automation_busy = False
        if automation_busy:
            _, show_warning = _feedback()
            show_warning(self.tr("A FilterMate task is still running: wait for it to finish"))
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
            elif task_name in ('undo', 'redo'):
                # The point cloud preview subset must go first: the history only
                # restores a layer still in the state it recorded.
                self._stop_preview(layer)
                step = self.service.undo if task_name == 'undo' else self.service.redo
                self._finish_restore(step(layer.id()))
            elif task_name == 'export':
                self._run_export([layer.id()])
        except Exception as exc:
            logger.error(f"[FM5] task '{task_name}' failed: {exc}", exc_info=True)
            _, show_warning = _feedback()
            show_warning(self.tr("FilterMate task failed: {0}").format(exc))
        return True

    def is_running(self) -> bool:
        """A cross filter or a height above ground computation of the dock is queued or running."""
        return self._task_active(self._running_task) or self._task_active(self._hag_task)

    @staticmethod
    def _task_active(task: Any) -> bool:
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

    def _run_filter(self, layer: Any, hag_tried: bool = False) -> None:
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
            # Read and bounded by the job (raster_adapter.source_max_pixels): "4e8", 0, text...
            if not self._raster_capability(layer).has_raw_values:
                sample = self._local_raster_sample(layer)
                if sample is None:
                    show_warning(self.tr("Prepare a color snapshot before filtering this rendered layer."))
                    return
                source_job = RasterSourceJob(layer, selection, _option('raster_source_max_pixels', None),
                                             analysis_source=(sample.source(), 'gdal'),
                                             zone=self._zone_geometry(self._raster_panel))
            else:
                source_job = RasterSourceJob(layer, selection, _option('raster_source_max_pixels', None),
                                             zone=self._zone_geometry(self._raster_panel))
            done_message = self.tr("Raster filtered: {0}").format(selection.describe())
            if not targets and not source_job.clips_source:
                # A virtual raster of the band: nothing to read, done here.
                before = source_job.before
                after = source_job.apply(layer)
                if after is not None:
                    self.service.history.push(CrossOperation(layer.id(), ((before, after),), 'raster selection'))
                self._after_run(layer, [], done_message)
                return
            if not targets:
                if source_job.clip_refusal:
                    # Nothing to filter: said before the pixels are read.
                    source_job.release()
                    show_warning(self.tr("Filter not applied: {0}").format(source_job.clip_refusal))
                    return
                # Masked by the polygons of the selection, read at the native resolution: in the task.
                self._start_task(request, source_job, done_message=done_message)
                return
        else:
            expression = self._point_cloud_expression()
            hag = self._pc_panel.hag_settings() if self._pc_panel is not None else None
            if hag is not None and 'HeightAboveGround' not in self._point_cloud_attributes(layer):
                if hag_tried:
                    # Computed, yet the derived point cloud shows no such dimension: never run PDAL in a loop.
                    show_warning(self.tr("Height above ground not computed: {0}").format(
                        "no HeightAboveGround dimension in the derived point cloud"))
                    return
                self._prepare_height_above_ground(layer, hag, lambda: self._run_filter(layer, hag_tried=True))
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
            siblings = []
            if self._pc_panel.apply_to_tiles():
                tiles = self._pc_panel.tiles_expression() if hasattr(self._pc_panel, 'tiles_expression') else expression
                if tiles != expression:
                    logger.info(f"[FM5] other tiles of the dataset: the boxes of the objects are in the coordinates of "
                                f"'{self._layer_name(layer)}', their classes go alone: {tiles}")
                siblings = self._apply_to_sibling_tiles(layer, tiles, source_op)
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
            source_job = PointCloudSourceJob(layer, float(_option('point_cloud_footprint_resolution', 2.0)), before=before,
                                             zone=self._zone_geometry())
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

    def _start_task(self, request: Any, source_job: Any, done_message: str = '') -> None:
        """Run the cross filter in a task; ``done_message`` is shown instead of the target count when there is none."""
        show_info, _ = _feedback()
        dw = self.dockwidget
        layer_name = source_job.layer_name
        self._set_busy(True)

        def done(task, result):
            self._return_raster_sample(task)
            if getattr(self, '_torn_down', False):
                return
            self._running_task = None
            self._set_busy(False)
            layer = self._map_layer(source_job.layer_id)
            if not result:
                # Nothing was applied: put back the point cloud selection subset
                # set before the task, so the source is not left filtered
                # without a history entry.
                if not getattr(task, 'source_conflict', False):
                    self._rollback_source(source_job, layer)
                _, show_warning = _feedback()
                show_warning(self.tr("Filter not applied: {0}").format(task.error or self.tr("canceled")))
                self._after_run(layer, [], '')
                return
            notes = self._source_notes(source_job)
            if done_message and not task.outcomes:
                if layer is None or not task.changes:
                    # Not applied: no pixel selected, a VRT that did not open, the layer removed meanwhile.
                    reason = getattr(source_job, 'message', '') or ('layer removed' if layer is None else 'nothing changed')
                    _, show_warning = _feedback()
                    show_warning(self.tr("Filter not applied: {0}").format(reason))
                    self._after_run(layer, [], '')
                    return
                self._after_run(layer, [], ' — '.join([done_message] + notes))
                return
            failures = [o for o in task.outcomes if not o.success]
            parts = [self.tr("{0} target(s) filtered").format(len(task.outcomes) - len(failures))] + notes
            sampled_targets = [o for o in task.outcomes if o.success and o.details.get('capture_resampled')]
            if sampled_targets:
                parts.append(self.tr("{0} raster target(s) resampled to the configured pixel limit").format(len(sampled_targets)))
            # A web service target read up to its budget: applied, its message (already translated) says so.
            partial = sorted({o.message for o in task.outcomes if o.success and o.details.get('partial') and o.message})
            parts.extend(partial)
            emptied = self._emptied_text(task.outcomes)
            if emptied:
                parts.append(emptied)
            if failures:
                parts.append(self.tr("{0} failed: {1}").format(len(failures), self._failure_text(failures)))
            self._after_run(layer, task.outcomes, ' — '.join(parts), warning=bool(failures or emptied or partial))

        try:
            self._running_task = self.service.run(request, source_job, on_done=done)
            analysis = getattr(source_job, '_analysis_source', None)
            if self._running_task is not None and analysis and isinstance(analysis[0], str):
                # Pin the rendered capture before the GUI can leave the layer.
                self._borrow_raster_sample(self._running_task, analysis[0])
        except Exception:
            self._set_busy(False)
            self._rollback_source(source_job, self._map_layer(source_job.layer_id))
            raise
        show_info(self.tr("FilterMate: filtering from '{0}'…").format(layer_name))
        try:
            dw.launchingTask  # noqa: B018 - presence check only
        except AttributeError:
            pass

    def _source_notes(self, source_job: Any) -> List[str]:
        """What the user should know about how a raster selection was read (once per task)."""
        details = getattr(source_job, 'details', None) or {}
        notes = []
        if details.get('rendered_colors'):
            notes.append(self.tr("color selection limited to the captured extent; colors depend on style and scale"))
        if details.get('capture_resampled'):
            notes.append(self.tr("raster source resampled to {0} cells within the pixel limit").format(details['capture_grid']))
        if details.get('decimation'):
            notes.append(self.tr("raster selection read every {0} pixels: over the pixel limit of the settings").format(
                details['decimation']))
        if details.get('smoothing') or details.get('blocks'):
            notes.append(self.tr("dense raster selection smoothed to keep its outline light"))
        return notes

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
        """Disable the Filter button while a task runs; enabled again once no other task of the dock runs."""
        button = getattr(self.dockwidget, 'pushButton_action_filter', None)
        self._call(button, 'setEnabled', not busy and not self.is_running())

    def _after_run(self, layer: Any, outcomes, message: str, warning: bool = False) -> None:
        show_info, show_warning = _feedback()
        self._refresh_canvas(layer)
        self._refresh_counts(layer)
        self.update_undo_redo_buttons()
        if message:
            (show_warning if warning else show_info)(message)
        self._schedule_cache_tidy()

    def _failure_text(self, failures) -> str:
        """``layer: reason`` for every failed target, cut to fit the message bar."""
        parts = []
        failed = self.tr('failed')  # out of the f-string: pylupdate5 does not read inside one
        for outcome in failures:
            layer = self._map_layer(outcome.layer_id)
            name = self._layer_name(layer) if layer is not None else outcome.layer_id
            parts.append(f"{name}: {outcome.message or failed}")
        return '; '.join(parts)[:300]

    def _emptied_text(self, outcomes) -> str:
        """Warning naming the targets left with nothing (``1 = 0``, no pixel, no point); '' when none."""
        names = []
        for outcome in outcomes or []:
            if outcome.success and getattr(outcome, 'emptied', False):
                layer = self._map_layer(outcome.layer_id)
                names.append(self._layer_name(layer) if layer is not None else outcome.layer_id)
        if not names:
            return ''
        return self.tr("{0} left empty, nothing matches the selection: {1}").format(
            len(names), ', '.join(names)[:300])

    def _refresh_counts(self, layer: Any) -> None:
        from ...core.domain.layer_kind import LayerKind
        if layer is None or not _same_layer(layer, self._active_layer):
            return  # a task of another layer ended: the panel shows the current one
        try:
            if self._kind is LayerKind.POINT_CLOUD and self._pc_panel is not None:
                self._pc_panel.set_current_subset(layer.subsetString())
        except Exception as exc:
            logger.debug(f"[FM5] point cloud subset not shown: {exc}")

    def _run_unfilter(self, layer: Any, reset: bool) -> None:
        settings = self._filtering_settings()
        ids = [layer.id()] + [t.layer_id for t in self._target_specs(settings['targets'], exclude_id=layer.id())]
        kinds = {layer_id: _kind_of(self._map_layer(layer_id)) for layer_id in ids}
        self._stop_preview(layer)
        restored = self.service.unfilter(layer.id(), ids, kinds)
        if reset:
            panel = self._current_panel()
            if panel is not None:
                panel.reset()  # does not emit: its outline goes here
            self._restore_raster_band_display(layer)
            self._hide_detected_objects()
            self._sync_object_pick_mode()
            self._panel_states.pop(layer.id(), None)
        self._finish_restore(restored)

    def _finish_restore(self, layer_ids: List[str]) -> None:
        show_info, show_warning = _feedback()
        skipped = list(getattr(self.service, 'last_skipped', []) or [])
        if skipped:
            show_warning(self.tr("Changed since, left as is: {0}").format(', '.join(skipped)))
            self.service.last_skipped = []
        for layer_id in layer_ids or []:
            self._refresh_canvas(self._map_layer(layer_id))
        self._refresh_counts(self._active_layer)
        self.update_undo_redo_buttons()
        show_info(self.tr("{0} layer(s) restored").format(len(layer_ids or [])))

    # === Export ===

    def _run_export(self, layer_ids: List[str], folder: Optional[str] = None, crs: Any = None,
                    zip_path: Optional[str] = None) -> Any:
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
            if getattr(self, '_torn_down', False):
                return
            written = [r.path for r in results if r.success]
            failed = [f"{r.path}: {r.message}" for r in results if not r.success]
            if zip_path and written:
                archive = self._zip_exports(zip_path, written)
                if archive:
                    written.append(archive)
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
            if getattr(_kind_of(self._map_layer(layer_id)), 'is_filter_target', False):
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
                run = _LinkedRun()  # gets its cross operation once the cross task really changed a layer
                self._linked_runs.setdefault(source_id, []).append(run)
                self._linked_redo[source_id] = []
                if coverage_ids and self._vector_engine_filters_targets():
                    self._run_vector_source_filter(source, coverage_ids, run=run)
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
                    self._schedule_cache_tidy()  # the forgotten steps kept derived files
            elif task_name == 'undo':
                runs = self._linked_runs.get(source_id) or []
                if runs:
                    run = runs.pop()
                    self._linked_redo.setdefault(source_id, []).append(run)
                    if self._run_is_next(run, self.service.history.peek_undo(source_id)):
                        self._finish_restore(self.service.undo(source_id))
            elif task_name == 'redo':
                redo = self._linked_redo.get(source_id) or []
                if redo:
                    run = redo.pop()
                    self._linked_runs.setdefault(source_id, []).append(run)
                    if self._run_is_next(run, self.service.history.peek_redo(source_id)):
                        self._finish_restore(self.service.redo(source_id))
        except Exception as exc:
            logger.warning(f"[FM5] coverage targets of '{self._layer_name(source)}' not processed: {exc}", exc_info=True)

    @staticmethod
    def _run_is_next(run: _LinkedRun, operation: Any) -> bool:
        """True when ``operation`` (top of the cross undo / redo stack) is the one ``run`` recorded.

        An operation forgotten since (removed layer, cache limit) leaves the
        run without its step: the next one belongs to an older run.
        """
        return run.op_id is not None and operation is not None and operation.op_id == run.op_id

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

    def _run_vector_source_filter(self, source: Any, coverage_ids: List[str], run: Optional[_LinkedRun] = None) -> bool:
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
            self._vector_task_over(source_id, task)
            if getattr(self, '_torn_down', False):
                return
            if task.changes and run is not None:
                if self._map_layer(source_id) is None:
                    # The source was removed (or the project closed) meanwhile: its history went with it.
                    self.service.history.clear_source(source_id)
                else:
                    # The service recorded the operation just before calling back: it is on top.
                    operation = self.service.history.peek_undo(source_id)
                    run.op_id = operation.op_id if operation is not None else None
            failures = [o for o in task.outcomes if not o.success]
            if not result:
                message = self.tr("Raster / point cloud targets not filtered: {0}").format(task.error or self.tr("canceled"))
            else:
                message = self.tr("{0} raster / point cloud target(s) filtered").format(len(task.outcomes) - len(failures))
                emptied = self._emptied_text(task.outcomes)
                if emptied:
                    message += ' — ' + emptied
                if failures:
                    message += ' — ' + self._failure_text(failures)
            self._after_run(self._map_layer(source_id), task.outcomes, message,
                            warning=not result or bool(failures) or bool(emptied))

        task = self.service.run(request, job, on_done=done)
        if task is not None:
            self._vector_tasks[source_id] = task
            for signal_name in ('taskCompleted', 'taskTerminated'):
                try:
                    # Also over when its callback failed before reaching done().
                    getattr(task, signal_name).connect(lambda t=task: self._vector_task_over(source_id, t))
                except (AttributeError, TypeError, RuntimeError):
                    pass
        return True

    def _vector_task_over(self, source_id: str, task: Any) -> None:
        if self._vector_tasks.get(source_id) is task:
            del self._vector_tasks[source_id]

    def vector_source_busy(self, source: Any) -> bool:
        """True, and the user is told to wait, while a cross task clips the coverage targets of ``source``.

        A Filter, Unfilter, Reset, Undo or Redo of the source meanwhile would
        pair its runs with the wrong cross operation (or none).
        """
        try:
            busy = source is not None and source.id() in self._vector_tasks
        except (RuntimeError, AttributeError):
            return False
        if busy:
            _, show_warning = _feedback()
            show_warning(self.tr("A FilterMate task is still running: wait for it to finish"))
        return busy

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
        from ...adapters.qgis.source_capability_probe import counts_cheaply
        if not counts_cheaply(source):
            # A source that does not count cheaply (web service...) is read in a task by
            # EXPLORING (the Filter waits for it): never again here, on the GUI thread.
            return []
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

    def export_coverage_layers(self, layer_ids: List[str], folder: Optional[str], crs: Any = None,
                               zip_path: Optional[str] = None) -> Any:
        """Export the raster / point cloud layers checked in EXPORTING (asks for a folder when None)."""
        return self._run_export(layer_ids, folder or None, crs, zip_path)

    @staticmethod
    def _zip_exports(zip_path: str, files: List[str]) -> str:
        """Archive the exported raster / point cloud files next to the vector zip.

        The vector export writes its own archive in another task: these files
        go to ``<name>_raster_lidar.zip`` instead of racing for the same file.
        """
        import os
        import zipfile
        base = zip_path[:-4] if zip_path.lower().endswith('.zip') else zip_path
        archive = f"{base}_raster_lidar.zip"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(archive)) or '.', exist_ok=True)
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as handle:
                for path in files:
                    if os.path.isfile(path):
                        handle.write(path, os.path.basename(path))
            return archive
        except OSError as exc:
            logger.warning(f"[FM5] raster / point cloud zip not written: {exc}")
            return ''

    # === Undo / redo buttons ===

    def can_undo(self) -> bool:
        layer_id = self._active_id()
        return layer_id is not None and self.service.can_undo(layer_id)

    def can_redo(self) -> bool:
        layer_id = self._active_id()
        return layer_id is not None and self.service.can_redo(layer_id)

    def update_undo_redo_buttons(self) -> None:
        if self._active_layer is None:
            self._call(self._app(), 'update_undo_redo_buttons')
            return
        dw = self.dockwidget
        # Same rule as FilterMateApp.update_undo_redo_buttons: Undo / Redo only on the FILTERING tab.
        on_filtering = getattr(dw, 'tabTools_current_index', 0) == 0
        self._call(getattr(dw, 'pushButton_action_undo_filter', None), 'setEnabled', on_filtering and self.can_undo())
        self._call(getattr(dw, 'pushButton_action_redo_filter', None), 'setEnabled', on_filtering and self.can_redo())

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
        task = HeightAboveGroundTask(layer, dem, zone=self._zone_geometry())

        def finished(ok, message):
            if getattr(self, '_torn_down', False):
                return
            self._hag_task = None
            self._set_busy(False)
            self._schedule_cache_tidy()
            if not ok:
                show_warning(self.tr("Height above ground not computed: {0}").format(message))
                return
            if message:
                show_info(message)
            if task.after is not None:
                from ...core.domain.filter_state import CrossOperation
                self.service.history.push(CrossOperation(layer.id(), ((task.before, task.after),), 'height above ground'))
            if not _same_layer(self._active_layer, layer):
                # Another layer was picked meanwhile: the panels and the kind are its own,
                # the filter of this one is not run (its height stays, undoable).
                self._refresh_canvas(layer)
                self.update_undo_redo_buttons()
                show_warning(self.tr("Filter not applied: {0}").format(self._layer_name(layer)))
                return
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
        except Exception as exc:
            logger.debug(f"[FM5] canvas not refreshed: {exc}")

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


def _event_callback(parent: Any, events: Tuple[Any, ...], callback: Any) -> Any:
    """Event filter (owned by ``parent``) running ``callback`` on the ``events`` of the widgets it watches.

    At module level and after the controller: a class nested in a controller method made
    pylupdate5 file the tr() strings that follow it under that class name, which the running
    plugin (context CoverageModeController) never looks up.
    """
    from qgis.PyQt.QtCore import QObject

    class _EventCallback(QObject):
        def eventFilter(self, watched, event):  # noqa: N802 - Qt override
            try:
                if event.type() in events:
                    callback()
            except RuntimeError:
                pass
            return False

    return _EventCallback(parent)
