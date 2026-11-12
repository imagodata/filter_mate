# -*- coding: utf-8 -*-
"""SAM on the map, for the object targets of the raster EXPLORING panel (clicked object, similar objects).

Owned by :class:`CoverageModeController`, which puts it on and off the map like the
pixel picker (rules R1 to R5 of ``selection_modes``) whenever an object target uses
the SAM engine.

Gestures: a click adds an object at once, Shift+click extends the last object, a right
click trims it, a box frames a new one, Escape removes the last object (or the last
search of similar objects). Moving the mouse over the area already prepared outlines
the object under it before any click. Each object is a polygon of the panel
(``RasterSelection.segments``): a filter replays it without the model.
"""
import logging
from typing import Any, List, Optional, Tuple

from qgis.PyQt.QtCore import QCoreApplication

logger = logging.getLogger(__name__)

# The outline under the mouse follows once the mouse rests this long (a prompt costs 35 to 100 ms).
HOVER_DELAY_MS = 120


class SegmentationController:
    """Draw objects with SAM on the active raster, one prompt at a time."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self.tool: Any = None
        self._outline: Any = None  # the object under the mouse (dashed)
        self._session: Any = None
        self._session_layer = ''
        self._task: Any = None  # the window being encoded
        self._search: Any = None  # the similar objects being drawn
        self._download: Any = None
        self._generation = 0
        self._previous_tool: Any = None
        # Prompts waiting for the window being encoded: (kind, value, positive, extend).
        self._pending: List[Tuple[str, Any, bool, bool]] = []
        # Every task started, until its callback: forgetting one dropped the last Python reference, and QGIS 3.22,
        # which leaves it to Python, deleted it while it ran (2026-11-10, the Escape of a click being prepared).
        self._running: List[Any] = []
        # The objects are followed by their polygon (WKT), not their index: the panel may clear or reset them.
        self._current: Optional[str] = None  # the object the prompts of the session draw
        self._groups: List[List[str]] = []  # the objects of each gesture (a click, a search), for Escape
        self._extending = False  # the prompts of the session redraw the current object
        self._hover_timer: Any = None
        self._hover_point: Any = None
        # Similar objects found, not yet in the selection: (WKT, reference WKT); kept or rejected by the user.
        self._proposals: List[Tuple[str, str]] = []
        self._proposal_outline: Any = None
        # The keep / reject decisions on the proposals of the last search, and the features they are sorted by.
        self._sorting: Optional[dict] = None

    @staticmethod
    def tr(text: str) -> str:
        return QCoreApplication.translate('SegmentationController', text)

    @staticmethod
    def _stop(task: Any) -> None:
        """Cancel a task QGIS says runs; any other gives up as it starts (``task.stopped``), its callback ignored.

        QGIS 3.22 deletes a queued task canceled while the thread pool already holds its runnable:
        the run that follows reads a deleted object and QGIS crashes (2026-11-10, the Escape of a click
        whose area was not prepared yet; later that day a task deleted for want of a Python reference was
        found behind that Escape, see ``_running``, and this rule stayed). A queued task is therefore not
        canceled but flagged: its run() reads the flag first and between its windows, instead of drawing
        a search nobody waits for (some 20 s of CPU). A status that cannot be read counts as not running.
        """
        try:
            if hasattr(task, 'stopped'):
                task.stopped = True
            if not hasattr(task, 'status'):
                task.cancel()  # not a QgsTask (a stand-in): nothing queued to protect
                return
            from qgis.core import QgsTask
            statuses = getattr(QgsTask, 'TaskStatus', None)
            running = getattr(statuses, 'Running', None) if statuses is not None else None
            if running is None:
                running = getattr(QgsTask, 'Running', None)
            status = task.status() if hasattr(task, 'status') else running
            if running is None or status != running:
                return
            task.cancel()
        except RuntimeError:
            pass  # already finished and deleted

    # === The tool on the map ===

    def activate(self) -> None:
        iface = self._host._iface()
        if iface is None:
            return
        canvas = iface.mapCanvas()
        if self.tool is None:
            from ..tools.segmentation_tool import SegmentationTool
            self.tool = SegmentationTool(canvas)
            self.tool.pointPicked.connect(self._on_point)
            self.tool.boxDrawn.connect(self._on_box)
            self.tool.hovered.connect(self._on_hover)
            self.tool.validateRequested.connect(self.validate)
            self.tool.clearRequested.connect(self.clear)
            self.tool.cycleRequested.connect(self.cycle)
            self.tool.activated.connect(lambda: self._host._show_picker_state(True))
            self.tool.deactivated.connect(self._on_tool_left)
        if canvas.mapTool() is not self.tool:
            self._previous_tool = canvas.mapTool()
            canvas.setMapTool(self.tool)
        self._status(self.tr("Click an object, or draw a box around it"))

    def _on_tool_left(self) -> None:
        """The tool left the map (another QGIS tool too, a reset of the panel): its markers went, the prompts and
        the proposals go with them (Keep all would add objects whose clicked object may be gone)."""
        self.cancel()
        self._set_proposals([])
        self._host._show_picker_state(False)

    def deactivate(self) -> None:
        """Give the map back to the tool this one replaced and forget the prompts and proposals; the objects stay."""
        self.cancel()
        self._set_proposals([])
        if self.tool is not None:
            previous, self._previous_tool = self._previous_tool, None
            self._host._release_map_tool(self.tool, previous)

    def on_map(self) -> bool:
        return self._host._tool_on_map(self.tool)

    def drop(self) -> None:
        """Take the tool off the map now, then delete it (made again on demand), as the other pickers on a layer change."""
        self.deactivate()
        self._session, self._session_layer = None, ''
        self._groups, self._current = [], None
        self._set_proposals([])
        # Out of the scene of the map: hidden, the outlines and the markers of the tool stayed there, two more
        # outlines at each reload of the plugin and the markers of a tool at each change of layer.
        for name in ('_outline', '_proposal_outline'):
            outline = getattr(self, name)
            setattr(self, name, None)
            if outline is not None:
                outline.remove()
        tool, self.tool = self.tool, None
        if tool is not None:
            try:
                tool.remove_items()
                tool.deleteLater()
            except RuntimeError:
                pass  # already deleted (QGIS closing)

    def cancel(self) -> None:
        """Forget the prompts, the window being encoded and the search running; the objects stay."""
        self._generation += 1
        self._pending = []
        for name in ('_task', '_search'):  # their callbacks return at once (the generation moved on)
            task = getattr(self, name)
            setattr(self, name, None)
            if task is not None:
                self._stop(task)
        if self._hover_timer is not None:
            self._hover_timer.stop()
        if self._session is not None:
            self._session.clear()
        self._current, self._extending = None, False
        self._hide_preview()

    # === Gestures ===

    def _transform(self) -> Any:
        """Map CRS to the CRS of the active layer."""
        from qgis.core import QgsCoordinateTransform, QgsProject
        settings = self._host._iface().mapCanvas().mapSettings()
        return QgsCoordinateTransform(settings.destinationCrs(), self._host._active_layer.crs(), QgsProject.instance())

    def _refuse(self, exc: Exception) -> None:
        """A prompt that cannot be read (off the domain of the CRS, a layer deleted, a sample not ready); the queued ones stay."""
        logger.debug(f"[FM5] segmentation prompt refused: {exc}")
        self._status(self.tr("This point cannot be used on this layer"))

    def _index(self, wkt: Optional[str]) -> int:
        """Index of an object in the panel; -1 when it is no longer there (cleared, another layer)."""
        panel = self._host._raster_panel
        if not wkt or panel is None or not hasattr(panel, 'index_of_segment'):
            return -1
        return panel.index_of_segment(wkt)

    def _has_current(self) -> bool:
        return self._index(self._current) >= 0

    def _on_point(self, point: Any, positive: bool, extend: bool = False) -> None:
        """A click: a new object; Shift+click (``extend``) or a right click (not ``positive``) redraw the last one."""
        if self._host._active_layer is None:
            return
        if self._proposals and not extend and self._decide_proposal(point, positive):
            return
        refine = extend or not positive
        if refine and not self._has_current():
            if not positive:
                self._status(self.tr("A right click trims the last object: click an object first"))
                return
            refine = False  # Shift+click without an object: a new one
        try:
            accepted = self._prompt('point', self._transform().transform(point), positive, refine)
        except Exception as exc:  # QgsCsException is no RuntimeError
            self._refuse(exc)
            return
        if accepted and self.tool is not None:
            if not refine:
                self.tool.clear_markers()
            self.tool.add_marker(point, positive)

    def _on_box(self, rectangle: Any) -> None:
        if self._host._active_layer is None:
            return
        try:
            if self._prompt('box', self._transform().transformBoundingBox(rectangle), True, False) and self.tool is not None:
                self.tool.clear_markers()
        except Exception as exc:  # QgsCsException is no RuntimeError
            self._refuse(exc)

    def _prompt(self, kind: str, value: Any, positive: bool, refine: bool) -> bool:
        """Take a prompt of the layer CRS; False when it is refused.

        Args:
            refine: The prompt redraws the current object (Shift+click, right click), it does not start one.
        """
        from ...adapters.qgis.coverage_layers.segmentation import find_provider
        layer = self._host._active_layer
        session = self._session if self._session_layer == layer.id() else None
        center = value if kind == 'point' else value.center()
        if not layer.extent().contains(center):
            self._status(self.tr("Click inside the raster"))
            return False
        if self._task is not None:
            self._pending.append((kind, value, positive, refine))
            return True
        if refine:
            if session is None or not session.has_prompts or not session.window.contains(center.x(), center.y()):
                self._status(self.tr("This point is outside the area of the last object: click it as a new object"))
                return False
            self._stop_search()  # it compares with the object being redrawn
            self._extending = True
            if not self._apply(session, kind, value, positive):
                self._status(self.tr("This box is too small"))
                return False
            self._predict(session)
            return True
        model = find_provider()
        if model is None:
            self._status(self._missing_model_text())
            return False
        source, provider_key, native, alpha = self._window_source(layer)
        try:
            window = self._plan(layer, center, native, model)
        except ValueError as exc:
            logger.debug(f"[FM5] segmentation window not planned: {exc}")
            self._status(self.tr("This raster cannot be segmented"))
            return False
        self._current, self._extending = None, False
        self._stop_search()  # its objects would join the new object's group
        if session is not None and session.window.cell == window.cell and self._serves(session.window, window, kind, value, layer):
            session.clear()
            if not self._apply(session, kind, value, positive):
                self._status(self.tr("This box is too small"))
                return False
            self._predict(session)
            return True
        self._pending = [(kind, value, positive, False)]
        self._encode(layer, window, model, source, provider_key, alpha)
        return True

    @staticmethod
    def _serves(encoded: Any, planned: Any, kind: str, value: Any, layer: Any) -> bool:
        """Whether the window already encoded serves a new prompt, rather than ``planned`` around it.

        A click must lie well inside it (``segmentation.well_inside``, as the candidates of the similar
        objects): at a few pixels from its edge, the object around it was cut. A box must lie in it whole,
        or ``set_box`` cuts it. The edges of the raster are no edges of an object; the same window serves.
        """
        from ...adapters.qgis.coverage_layers.segmentation import well_inside
        if (encoded.x_min, encoded.y_max) == (planned.x_min, planned.y_max):
            return True
        extent = layer.extent()
        raster = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
        if kind == 'point':
            return well_inside(encoded, value.x(), value.y(), raster)
        return (well_inside(encoded, value.xMinimum(), value.yMinimum(), raster, 0)
                and well_inside(encoded, value.xMaximum(), value.yMaximum(), raster, 0))

    @staticmethod
    def _apply(session: Any, kind: str, value: Any, positive: bool) -> bool:
        if kind == 'point':
            return session.add_point(value.x(), value.y(), positive)
        return session.set_box(value.xMinimum(), value.yMinimum(), value.xMaximum(), value.yMaximum())

    # === The object under the mouse ===

    def _on_hover(self, point: Any) -> None:
        """Outline the object under the mouse once it rests, inside the area already prepared."""
        if self._session is None or self._task is not None or self._search is not None or self._host._active_layer is None:
            return
        if self._session_layer != self._host._active_layer.id():
            return
        self._hover_point = point
        if self._hover_timer is None:
            from qgis.PyQt.QtCore import QTimer
            self._hover_timer = QTimer()
            self._hover_timer.setSingleShot(True)
            self._hover_timer.setInterval(HOVER_DELAY_MS)
            self._hover_timer.timeout.connect(self._show_hovered)
        self._hover_timer.start()

    def _show_hovered(self) -> None:
        layer, session, point = self._host._active_layer, self._session, self._hover_point
        if layer is None or session is None or point is None or self._task is not None or getattr(self._host, '_torn_down', False):
            return
        from ...adapters.qgis.coverage_layers.segmentation import point_geometry
        try:
            where = self._transform().transform(point)
            geometry = point_geometry(session.provider, session.embedding, session.window, where.x(), where.y(),
                                      layer.crs().toWkt())
        except Exception as exc:  # off the window, a model failure: no outline, the click still works
            logger.debug(f"[FM5] object under the mouse not drawn: {exc}")
            geometry = None
        if geometry is None or geometry.isEmpty():
            self._hide_outline()
            return
        self._show_outline(geometry)

    # === Encoding the window ===

    def _window_source(self, layer: Any) -> Tuple[str, str, float, Optional[int]]:
        """``(source, provider, native cell, alpha band)`` to draw: a service is rendered itself, it has no pixels of its own.

        Its local sample only covers what was visible when it was taken, and its size says nothing of
        the coverage; a raster filtered by FilterMate is read from its original source, with the alpha
        band of that source (:meth:`_original_alpha_band`; None: the renderer keeps its own).
        """
        from ...adapters.qgis.coverage_layers.raster_materialization import raster_reads_remotely
        if raster_reads_remotely(layer.providerType(), layer.source()) or not self._host._raster_capability(layer).has_raw_values:
            return layer.source(), layer.providerType(), 0.0, None
        base = self._host._base_raster(layer)
        extent = base.extent()
        native = max(extent.width() / base.width(), extent.height() / base.height()) if base.width() > 0 and base.height() > 0 else 0.0
        return base.source(), base.providerType(), native, self._original_alpha_band(layer, base)

    @staticmethod
    def _original_alpha_band(layer: Any, base: Any) -> Optional[int]:
        """The alpha band the renderer of ``layer`` reads on its original source ``base``; None when ``base`` is the layer.

        A raster filtered by FilterMate shows a derived source with an alpha band of FilterMate's (the
        VRT of an integer raster without NoData), which its renderer reads (``snapshots._sync_alpha_band``).
        The original source has no such band: that block is invalid and the window was drawn black. The
        band of the original source is the one the layer had there, else the one QGIS chose for it.
        """
        if base is layer:
            return None
        from ...adapters.qgis.coverage_layers.snapshots import registry
        alpha = registry().original_alpha_band(layer.id())
        if alpha is None:  # not known (a project of an older version)
            renderer = base.renderer()
            alpha = renderer.alphaBand() if renderer is not None and hasattr(renderer, 'alphaBand') else -1
        return alpha

    def _visible_extent(self) -> Any:
        """The visible map, in the CRS of the layer; the extent of the layer when the map shows more than that CRS covers.

        A map zoomed out on the world cannot be reprojected in the CRS of a local raster (QgsCsException,
        no RuntimeError): it raised in the callback of the encoding (a virtual method of C++) and after an
        object was added (whose click was then said unusable). The whole raster is then in view.
        """
        settings = self._host._iface().mapCanvas().mapSettings()
        try:
            return self._transform().transformBoundingBox(settings.visibleExtent())
        except Exception as exc:  # QgsCsException is no RuntimeError
            logger.debug(f"[FM5] visible map not in the CRS of the layer, its extent used: {exc}")
            return self._host._active_layer.extent()

    def _plan(self, layer: Any, center: Any, native: float, model: Any) -> Any:
        from ...adapters.qgis.coverage_layers.segmentation import plan_window
        visible = self._visible_extent()
        extent = layer.extent()
        return plan_window(center.x(), center.y(), (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                           native, min(visible.width(), visible.height()), int(model.input_size))

    def _encode(self, layer: Any, window: Any, model: Any, source: str, provider_key: str,
                alpha: Optional[int] = None) -> None:
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.segmentation import SegmentationEmbedTask, raster_look
        self._generation += 1
        self._hide_outline()
        task = SegmentationEmbedTask(source, provider_key, None, layer.crs(), window, model,
                                     self._embedded(self._generation, layer.id(), window, model),
                                     look=raster_look(layer, alpha))
        self._task = task
        self._running.append(task)
        self._status(self.tr("Preparing the segmentation of this area…"))
        QgsApplication.taskManager().addTask(task)

    def _embedded(self, generation: int, layer_id: str, window: Any, model: Any) -> Any:
        def finish(task: Any, success: bool) -> None:
            self._release(task)
            if generation != self._generation or getattr(self._host, '_torn_down', False):
                return  # the layer or the object changed while the window was encoded
            self._task = None
            if not success or task.embedding is None:
                self._pending = []
                self._hide_preview()
                self._status(self.tr("The segmentation of this area failed: {0}").format(task.error or self.tr("canceled")))
                if getattr(task, 'model_damaged', False):
                    self._host._call(self._host._raster_panel, 'offer_model_repair')
                return
            from ...adapters.qgis.coverage_layers.segmentation import SegmentationSession
            session = SegmentationSession(model, window, task.embedding)
            self._session, self._session_layer = session, layer_id
            pending, self._pending = self._pending, []
            self._current, self._extending = None, False
            lost = 0
            for kind, value, positive, refine in pending:
                if not refine or not session.has_prompts:
                    session.clear()  # each click queued while the area was prepared is an object of its own
                    self._current, self._extending = None, False
                else:
                    self._extending = True
                if self._apply(session, kind, value, positive):
                    self._predict(session)
                else:
                    lost += 1
            if lost:
                self._status(self.tr("{0} click(s) fell outside the area prepared: click them again").format(lost))
        return finish

    # === The model ===

    @staticmethod
    def model_state() -> Any:
        from ...adapters.qgis.coverage_layers.segmentation import model_state
        return model_state()

    def _missing_model_text(self) -> str:
        from ...adapters.qgis.python_dependencies import manual_command
        state = self.model_state()
        if state.installing_runtime:
            return self.tr("onnxruntime is being installed, click again in a moment")
        if not state.runtime and state.runtime_failed:
            return self.tr("onnxruntime is missing: run {0}, then restart QGIS").format(manual_command())
        if not state.runtime:
            return self.tr("Install onnxruntime first, with the button below")
        if self.downloading():
            return self.tr("The segmentation model is being downloaded, click again once it is installed")
        if not state.installed:
            return self.tr("Install the segmentation model first (button below)")
        return self.tr("The segmentation model could not be loaded (see the FilterMate log)")

    def _refresh_readiness(self) -> None:
        state = self.model_state()
        self._host._call(self._host._raster_panel, 'set_segmentation_readiness', state.runtime, state.installed, self.downloading(), state.installing_runtime, state.runtime_failed)

    def install_model(self) -> None:
        """Download the model files (the panel asked the user first); one download at a time."""
        if self._download is not None:
            return
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.segmentation import ModelDownloadTask, model_directory
        task = ModelDownloadTask(model_directory(), self._downloaded)
        self._download = task
        task.progressChanged.connect(self._on_download_progress)
        self._status(self.tr("Downloading the segmentation model… {0} %").format(0))
        QgsApplication.taskManager().addTask(task)
        self._refresh_readiness()

    def _on_download_progress(self, progress: float) -> None:
        if self._download is not None and not getattr(self._host, '_torn_down', False):
            self._status(self.tr("Downloading the segmentation model… {0} %").format(int(progress)))

    def _downloaded(self, task: Any, success: bool) -> None:
        self._download = None
        if getattr(self._host, '_torn_down', False):
            return
        self._refresh_readiness()
        if success:
            ready = self.model_state().ready
            self._status(self.tr("Model installed: left click on an object, or draw a box") if ready else self._missing_model_text())
        elif task.error:
            self._status(self.tr("The model could not be downloaded: {0}").format(task.error))
        else:
            self._status(self.tr("Download canceled"))

    def downloading(self) -> bool:
        return self._download is not None

    def cancel_download(self) -> None:
        """The dock goes away (the callback of the task then returns at once)."""
        task, self._download = self._download, None
        if task is not None:
            self._stop(task)

    # === Result ===

    def _predict(self, session: Any) -> None:
        """Ask SAM for the object of the prompts and put it in the panel: a new object, or the current one redrawn."""
        if not session.has_prompts:
            self._status(self.tr("Click on an object in the area prepared"))
            return
        try:
            session.predict()
            geometry = self._geometry(session)
        except Exception as exc:  # third party model
            session.mask = None
            logger.warning(f"[FM5] segmentation failed: {exc}", exc_info=True)
            self._status(self.tr("The segmentation of this area failed: {0}").format(exc))
            return
        if geometry is None or geometry.isEmpty():
            session.mask = None
            if self._extending and session.points:
                session.points.pop()  # this prompt emptied the object: the next ones start from the object before it
                session.labels.pop()
            elif not self._extending:
                session.clear()
            self._status(self.tr("No object found: add a point or draw a box"))
            return
        self._hide_outline()
        self._commit(geometry)

    def _commit(self, geometry: Any) -> None:
        panel = self._host._raster_panel
        if panel is None or not hasattr(panel, 'segment_count'):
            return
        wkt = geometry.asWkt()
        index = self._index(self._current)
        if self._extending and index >= 0:
            panel.replace_segment(index, wkt)
            for group in self._groups:
                group[:] = [wkt if member == self._current else member for member in group]
            self._current = wkt
            self._status(self.tr("Shift+click extends the object, right click trims it, G changes its granularity"))
            return
        if self._index(wkt) >= 0:
            self._current = wkt  # the very same polygon was already there: it is the one refined next
            return
        panel.add_segment(wkt)
        self._current = wkt
        self._groups.append([wkt])
        if hasattr(panel, 'pick_target') and panel.pick_target() == 'similar_objects':
            self._search_similar(geometry)
        else:
            self._status(self.tr("Shift+click extends the object, right click trims it, G changes its granularity"))

    def _geometry(self, session: Any) -> Any:
        """The object of the session inside the raster: a window can run past its edge, where nothing was drawn.

        Only the parts of the mask under a positive point (or in the box) are kept: SAM may
        return detached specks, and an object made of them would cover its neighbours.
        """
        from qgis.core import QgsGeometry, QgsPointXY
        from ...adapters.qgis.coverage_layers.raster_adapter import geometry_parts
        geometry = session.geometry()
        if geometry is None or geometry.isEmpty():
            return geometry
        window = session.window
        anchors = [QgsGeometry.fromPointXY(QgsPointXY(*window.to_map(column, row)))
                   for (column, row), label in zip(session.points, session.labels) if label]
        if session.box is not None:
            c0, r0, c1, r1 = session.box
            anchors.append(QgsGeometry.fromRect(window.rectangle_of(c0, r0, c1, r1)))
        parts = geometry_parts(geometry)
        held = [part for part in parts if any(part.intersects(anchor) for anchor in anchors)]
        if held and len(held) < len(parts):
            geometry = QgsGeometry.unaryUnion(held)
        return geometry.intersection(QgsGeometry.fromRect(self._host._active_layer.extent()))

    def _release(self, task: Any) -> None:
        """The task ended (its callback runs): it may go."""
        self._running = [other for other in self._running if other is not task]

    # === Similar objects ===

    def _search_similar(self, reference: Any) -> None:
        """Propose to SAM the colour patches near the clicked object, then the places whose features look like it,
        and keep the objects like it (a task)."""
        from qgis.core import QgsApplication
        from ...adapters.qgis.coverage_layers.segmentation import (
            SimilarObjectsTask, feature_candidate_points, find_provider, pooled_features, raster_look,
        )
        layer, session, panel = self._host._active_layer, self._session, self._host._raster_panel
        model = find_provider()
        if layer is None or session is None or model is None or panel is None:
            return
        if not self._host._raster_capability(layer).has_raw_values:
            self._status(self.tr("Similar objects need the values of the raster: this layer is only drawn"))
            return
        reference_features = pooled_features(session.embedding, session.mask)
        visible = self._visible_extent()
        try:
            points = self._host._similar_candidates(layer, reference, visible)
        except Exception as exc:  # a raster that cannot be read: the clicked object stays
            logger.warning(f"[FM5] similar objects not proposed: {exc}", exc_info=True)
            points = []
        try:  # the colour patches first, as measured: their objects are drawn before the others
            points = list(points) + feature_candidate_points(session.embedding, session.window, reference_features,
                                                             visible, reference)
        except Exception as exc:  # the colour candidates are enough to search
            logger.warning(f"[FM5] candidates from the features not found: {exc}", exc_info=True)
        if not points:
            self._status(self.tr("No patch of this colour nearby to compare with the object"))
            return
        self._stop_search()  # one search at a time (several clicks may have been queued)
        source, provider_key, _native, alpha = self._window_source(layer)
        extent = layer.extent()
        self._generation += 1
        task = SimilarObjectsTask(source, provider_key, None, layer.crs(), model,
                                  (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                                  session.window.cell, points, reference.asWkt(), panel.similar_ratio(),
                                  panel.similar_shape(), self._searched(self._generation, layer.id(), reference.asWkt()),
                                  existing=list(panel._segments), reference_features=reference_features,
                                  click_window=session.window, click_embedding=session.embedding,
                                  look=raster_look(layer, alpha))
        self._search = task
        self._running.append(task)
        task.progressChanged.connect(lambda progress: self._on_search_progress(task, progress))
        self._status(self.tr("Drawing the similar objects: {0} candidates…").format(len(points)))
        QgsApplication.taskManager().addTask(task)

    def _stop_search(self) -> None:
        task, self._search = self._search, None
        if task is not None:
            self._generation += 1  # its callback returns at once
            self._stop(task)

    def _on_search_progress(self, task: Any, progress: float) -> None:
        if self._search is task and not getattr(self._host, '_torn_down', False):
            self._status(self.tr("Drawing the similar objects… {0} %").format(int(progress)))

    def _searched(self, generation: int, layer_id: str, reference_wkt: str) -> Any:
        def finish(task: Any, success: bool) -> None:
            self._release(task)
            if generation != self._generation or getattr(self._host, '_torn_down', False):
                return
            self._search = None
            layer, panel = self._host._active_layer, self._host._raster_panel
            if layer is None or layer.id() != layer_id or panel is None:
                return
            if self._index(reference_wkt) < 0:
                return  # the clicked object was cleared or redrawn meanwhile: its search no longer applies
            if not success:
                if task.error:
                    self._status(self.tr("The similar objects could not be drawn: {0}").format(task.error))
                    if getattr(task, 'model_damaged', False):
                        self._host._call(panel, 'offer_model_repair')
                return
            new = [wkt for wkt in task.wkts if self._index(wkt) < 0]
            self._set_proposals([(wkt, reference_wkt) for wkt in new])
            self._start_sorting(task, new)
            if new:
                self._status(self.tr("{0} similar objects proposed among {1} candidates: click one to keep it, right click "
                                     "to reject it, Enter keeps them all, Escape rejects them all").format(len(new), task.examined))
            else:
                self._status(self.tr("No similar object found among {0} candidates").format(task.examined))
        return finish

    # === Proposals ===

    def proposal_count(self) -> int:
        return len(self._proposals)

    def _set_proposals(self, proposals: List[Tuple[str, str]]) -> None:
        """Show the proposals (dashed), or hide them; the panel shows how many there are."""
        from qgis.core import QgsGeometry
        self._proposals = list(proposals)
        self._host._call(self._host._raster_panel, 'set_proposal_count', len(self._proposals))
        if not self._proposals:
            self._sorting = None  # nothing left to sort: the next search starts afresh
            if self._proposal_outline is not None:
                self._proposal_outline.hide()
            return
        iface = self._host._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        layer = self._host._active_layer
        if canvas is None or layer is None:
            return
        if self._proposal_outline is None:
            from ...adapters.qgis.coverage_layers.preview_overlay import ObjectOutline
            self._proposal_outline = ObjectOutline(canvas, hover=True)
        geometries = [QgsGeometry.fromWkt(wkt) for wkt, _reference in self._proposals]
        self._proposal_outline.show(QgsGeometry.unaryUnion(geometries), layer)

    def _start_sorting(self, task: Any, wkts: List[str]) -> None:
        """The proposals of a search, ready to be sorted by the decisions the user makes on them."""
        features = getattr(task, 'features', None) or {}
        reference = getattr(task, 'reference_features', None)
        self._sorting = {'features': {wkt: features.get(wkt) for wkt in wkts}, 'decisions': 0,
                         'kept': [reference] if reference is not None else [], 'rejected': []}

    def _sorted_out(self, wkt: str, keep: bool, rest: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Note the decision on ``wkt``; the proposals of ``rest`` that now look like the rejected ones (taken away).

        From :data:`SORT_AFTER_DECISIONS` decisions on, a proposal closer, by its encoder features, to
        the rejected ones than to the kept ones and the clicked object goes (measured on the 25 cm
        Cerdagne orthophoto, 2026-11-11).
        """
        from ...adapters.qgis.coverage_layers.segmentation import SORT_AFTER_DECISIONS, closer_to_rejected
        sorting = self._sorting
        if sorting is None:
            return []
        sorting['decisions'] += 1
        features = sorting['features'].get(wkt)
        if features is not None:
            sorting['kept' if keep else 'rejected'].append(features)
        if sorting['decisions'] < SORT_AFTER_DECISIONS:
            return []
        return [item for item in rest
                if closer_to_rejected(sorting['features'].get(item[0]), sorting['kept'], sorting['rejected'])]

    def _decide_proposal(self, point: Any, keep: bool) -> bool:
        """A click on a proposal keeps it, a right click rejects it; False when the click is on none.

        Once enough proposals are decided, those that look like the rejected ones are taken away too.
        """
        from qgis.core import QgsGeometry, QgsPointXY
        try:
            where = QgsGeometry.fromPointXY(QgsPointXY(self._transform().transform(point)))
        except Exception:  # off the domain of the CRS: not on a proposal
            return False
        for index, (wkt, reference) in enumerate(self._proposals):
            if QgsGeometry.fromWkt(wkt).contains(where):
                rest = self._proposals[:index] + self._proposals[index + 1:]
                if keep:
                    self._accept([(wkt, reference)])
                try:
                    hidden = self._sorted_out(wkt, keep, rest)
                except Exception as exc:  # sorting is a help: the decision itself is made
                    logger.warning(f"[FM5] proposals not sorted: {exc}", exc_info=True)
                    hidden = []
                rest = [item for item in rest if item not in hidden]
                self._set_proposals(rest)
                message = ((self.tr("Object kept") if keep else self.tr("Proposal rejected"))
                           + (self.tr(": {0} proposals left").format(len(rest)) if rest else ""))
                if hidden:
                    message += " " + self.tr("({0} taken away: they look like the rejected ones)").format(len(hidden))
                self._status(message)
                return True
        return False

    def _accept(self, proposals: List[Tuple[str, str]]) -> int:
        panel = self._host._raster_panel
        if panel is None or not proposals:
            return 0
        wkts = [wkt for wkt, _reference in proposals if self._index(wkt) < 0]
        added = panel.add_segments(wkts) if wkts else 0
        for wkt, reference in proposals:
            for group in reversed(self._groups):
                if reference in group:
                    group.append(wkt)  # Escape removes the clicked object with the objects kept from its search
                    break
        return added

    def accept_proposals(self) -> None:
        """Enter or the panel: every proposal joins the selection."""
        if not self._proposals:
            return
        added = self._accept(self._proposals)
        self._set_proposals([])
        self._status(self.tr("{0} similar objects kept").format(added))

    def reject_proposals(self) -> None:
        """Escape or the panel: the proposals go, the selection is unchanged."""
        if not self._proposals:
            return
        self._set_proposals([])
        self._status(self.tr("Proposals rejected"))

    # === Outline and status ===

    def _show_outline(self, geometry: Any) -> None:
        iface = self._host._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        if canvas is None:
            return
        if self._outline is None:
            from ...adapters.qgis.coverage_layers.preview_overlay import ObjectOutline
            self._outline = ObjectOutline(canvas, hover=True)
        self._outline.show(geometry, self._host._active_layer)

    def _hide_outline(self) -> None:
        if self._outline is not None:
            self._outline.hide()

    def _hide_preview(self) -> None:
        self._hide_outline()
        if self.tool is not None:
            try:
                self.tool.clear_markers()
            except RuntimeError:
                pass  # deleted with the canvas

    def _status(self, text: str) -> None:
        self._host._call(self._host._raster_panel, 'set_segmentation_status', text)

    def validate(self) -> None:
        """Enter: keep the proposals; otherwise nothing to validate, a click already added the object."""
        if self._proposals:
            self.accept_proposals()
            return
        self._current, self._extending = None, False
        if self._session is not None:
            self._session.clear()
        if self.tool is not None:
            self.tool.clear_markers()
        self._status(self.tr("Click the next object"))

    def clear(self) -> None:
        """Escape: stop what runs (a click being prepared, a search); otherwise remove the last object or search."""
        if self._task is not None or self._pending or self._search is not None:
            searching = self._search is not None
            self.cancel()
            self._status(self.tr("Search stopped") if searching else self.tr("Click canceled"))
            return
        if self._proposals:
            self.reject_proposals()
            return
        self.cancel()
        panel = self._host._raster_panel
        if panel is None or not hasattr(panel, 'remove_segment_wkts'):
            return
        while self._groups:
            if panel.remove_segment_wkts(self._groups.pop()):
                self._status(self.tr("Last object removed"))
                return
        self._status('')

    def cycle(self) -> None:
        """G: the last object takes the next mask SAM proposed for it (a part, the object, a group)."""
        session = self._session
        if session is None or not session.has_prompts or self._task is not None or not self._has_current():
            self._status(self.tr("Click an object first"))
            return
        if not session.cycle():
            self._status(self.tr("SAM proposed a single outline for this object"))
            return
        try:
            geometry = self._geometry(session)
        except Exception as exc:  # a mask GEOS cannot polygonize
            logger.warning(f"[FM5] granularity not drawn: {exc}", exc_info=True)
            return
        if geometry is None or geometry.isEmpty():
            self._status(self.tr("No object at this granularity: press G again"))
            return
        self._stop_search()  # it compared with the former outline
        self._extending = True
        self._commit(geometry)
        rank, count = session.granularity()
        self._status(self.tr("Granularity {0} of {1}: G for the next one").format(rank, count))

    def session_info(self) -> Optional[Any]:
        """The encoded window, for the tests."""
        return self._session
