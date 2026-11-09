# -*- coding: utf-8 -*-
"""Segmentation tool of the raster EXPLORING panel: prompts, encoded window, preview, validated objects.

Owned by :class:`CoverageModeController`, which puts it on and off the map like the
pixel picker (rules R1 to R5 of ``selection_modes``).
"""
import logging
from typing import Any, List, Optional, Tuple

from qgis.PyQt.QtCore import QCoreApplication

logger = logging.getLogger(__name__)


class SegmentationController:
    """Drive one object at a time on the active raster."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self.tool: Any = None
        self._outline: Any = None
        self._session: Any = None
        self._session_layer = ''
        self._task: Any = None
        self._generation = 0
        self._previous_tool: Any = None
        self._pending: List[Tuple[str, Any, bool]] = []  # prompts waiting for the window being encoded

    @staticmethod
    def tr(text: str) -> str:
        return QCoreApplication.translate('SegmentationController', text)

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
            self.tool.validateRequested.connect(self.validate)
            self.tool.clearRequested.connect(self.clear)
            self.tool.activated.connect(lambda: self._host._show_picker_state(True))
            self.tool.deactivated.connect(self._on_tool_left)
        if canvas.mapTool() is not self.tool:
            self._previous_tool = canvas.mapTool()
            canvas.setMapTool(self.tool)

    def _on_tool_left(self) -> None:
        """The tool left the map (another QGIS tool too): its markers went, the prompts go with them."""
        self.cancel()
        self._host._show_picker_state(False)

    def deactivate(self) -> None:
        """Give the map back to the tool this one replaced and forget the object being drawn."""
        self.cancel()
        if self.tool is not None:
            previous, self._previous_tool = self._previous_tool, None
            self._host._release_map_tool(self.tool, previous)

    def on_map(self) -> bool:
        return self._host._tool_on_map(self.tool)

    def drop(self) -> None:
        """Take the tool off the map now, then delete it (made again on demand), as the other pickers on a layer change."""
        self.deactivate()
        self._session, self._session_layer = None, ''
        tool, self.tool = self.tool, None
        if tool is not None:
            try:
                tool.deleteLater()
            except RuntimeError:
                pass  # already deleted (QGIS closing)

    def cancel(self) -> None:
        """Forget the prompts and any window being encoded; a validated object stays."""
        self._generation += 1
        self._pending = []
        task, self._task = self._task, None
        if task is not None:
            try:
                task.cancel()
            except RuntimeError:
                pass  # already finished and deleted
        if self._session is not None:
            self._session.clear()
        self._hide_preview()

    # === Prompts ===

    def _transform(self) -> Any:
        """Map CRS to the CRS of the active layer."""
        from qgis.core import QgsCoordinateTransform, QgsProject
        settings = self._host._iface().mapCanvas().mapSettings()
        return QgsCoordinateTransform(settings.destinationCrs(), self._host._active_layer.crs(), QgsProject.instance())

    def _refuse(self, exc: Exception) -> None:
        """A prompt that cannot be read (off the domain of the CRS, a layer deleted, a sample not ready)."""
        logger.debug(f"[FM5] segmentation prompt refused: {exc}")
        self._pending = []
        self._status(self.tr("This point cannot be used on this layer"))

    def _on_point(self, point: Any, positive: bool) -> None:
        if self._host._active_layer is None:
            return
        try:
            accepted = self._prompt('point', self._transform().transform(point), positive)
        except Exception as exc:  # QgsCsException is no RuntimeError
            self._refuse(exc)
            return
        if accepted and self.tool is not None:
            self.tool.add_marker(point, positive)

    def _on_box(self, rectangle: Any) -> None:
        if self._host._active_layer is None:
            return
        try:
            self._prompt('box', self._transform().transformBoundingBox(rectangle), True)
        except Exception as exc:  # QgsCsException is no RuntimeError
            self._refuse(exc)

    def _prompt(self, kind: str, value: Any, positive: bool) -> bool:
        """Take a prompt of the layer CRS; False when it is refused."""
        from ...adapters.qgis.coverage_layers.segmentation import find_provider
        layer = self._host._active_layer
        session = self._session if self._session_layer == layer.id() else None
        center = value if kind == 'point' else value.center()
        if not layer.extent().contains(center):
            self._status(self.tr("Click inside the raster"))
            return False
        if self._task is not None:
            self._pending.append((kind, value, positive))
            return True
        if session is not None and session.has_prompts:
            if not session.window.contains(center.x(), center.y()):
                self._status(self.tr("This point is outside the window being segmented: validate or clear the object first"))
                return False
            if not self._apply(session, kind, value, positive):
                self._status(self.tr("This box is too small"))
                return False
            self._predict(session)
            return True
        if not positive:
            self._status(self.tr("Start with a left click on the object, or draw a box"))
            return False
        model = find_provider()
        if model is None:
            self._status(self.tr("The segmentation plugin is not ready"))
            return False
        source, provider_key, native = self._window_source(layer)
        try:
            window = self._plan(layer, center, native, model)
        except ValueError as exc:
            logger.debug(f"[FM5] segmentation window not planned: {exc}")
            self._status(self.tr("This raster cannot be segmented"))
            return False
        if session is not None and session.window.cell == window.cell and session.window.contains(center.x(), center.y()):
            if not self._apply(session, kind, value, positive):
                self._status(self.tr("This box is too small"))
                return False
            self._predict(session)
            return True
        self._pending = [(kind, value, positive)]
        self._encode(layer, window, model, source, provider_key)
        return True

    @staticmethod
    def _apply(session: Any, kind: str, value: Any, positive: bool) -> bool:
        if kind == 'point':
            return session.add_point(value.x(), value.y(), positive)
        return session.set_box(value.xMinimum(), value.yMinimum(), value.xMaximum(), value.yMaximum())

    # === Encoding the window ===

    def _window_source(self, layer: Any) -> Tuple[str, str, float]:
        """``(source, provider, native cell)`` to draw: a service is rendered itself, it has no pixels of its own.

        Its local sample only covers what was visible when it was taken, and its size says nothing of
        the coverage; a raster filtered by FilterMate is read from its original source.
        """
        from ...adapters.qgis.coverage_layers.raster_materialization import raster_reads_remotely
        if raster_reads_remotely(layer.providerType(), layer.source()) or not self._host._raster_capability(layer).has_raw_values:
            return layer.source(), layer.providerType(), 0.0
        base = self._host._base_raster(layer)
        extent = base.extent()
        native = max(extent.width() / base.width(), extent.height() / base.height()) if base.width() > 0 and base.height() > 0 else 0.0
        return base.source(), base.providerType(), native

    def _plan(self, layer: Any, center: Any, native: float, model: Any) -> Any:
        from ...adapters.qgis.coverage_layers.segmentation import plan_window
        settings = self._host._iface().mapCanvas().mapSettings()
        visible = self._transform().transformBoundingBox(settings.visibleExtent())
        extent = layer.extent()
        return plan_window(center.x(), center.y(), (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
                           native, min(visible.width(), visible.height()), int(model.input_size))

    def _encode(self, layer: Any, window: Any, model: Any, source: str, provider_key: str) -> None:
        from qgis.core import QgsApplication, QgsProject
        from ...adapters.qgis.coverage_layers.segmentation import SegmentationEmbedTask
        self._generation += 1
        renderer = layer.renderer().clone() if layer.renderer() is not None else None
        task = SegmentationEmbedTask(source, provider_key, renderer, layer.crs(), window, model,
                                     self._embedded(self._generation, layer.id(), window, model),
                                     QgsProject.instance().transformContext())
        self._task = task
        self._status(self.tr("Preparing the segmentation of this area…"))
        QgsApplication.taskManager().addTask(task)

    def _embedded(self, generation: int, layer_id: str, window: Any, model: Any) -> Any:
        def finish(task: Any, success: bool) -> None:
            if generation != self._generation or getattr(self._host, '_torn_down', False):
                return  # the layer or the object changed while the window was encoded
            self._task = None
            if not success or task.embedding is None:
                self._pending = []
                self._hide_preview()
                self._status(self.tr("The segmentation of this area failed: {0}").format(task.error or self.tr("canceled")))
                return
            from ...adapters.qgis.coverage_layers.segmentation import SegmentationSession
            session = SegmentationSession(model, window, task.embedding)
            self._session, self._session_layer = session, layer_id
            pending, self._pending = self._pending, []
            accepted = [self._apply(session, kind, value, positive) for kind, value, positive in pending]
            if not all(accepted) and self.tool is not None:
                self.tool.clear_markers()  # the map moved while the area was prepared: a marker would lie
            self._predict(session)
        return finish

    # === Result ===

    def _predict(self, session: Any) -> None:
        if not session.has_prompts:
            self._status(self.tr("Click on an object in the area prepared"))
            self._hide_preview()
            return
        try:
            session.predict()
            geometry = self._geometry(session)
        except Exception as exc:  # third party model
            session.mask = None  # Enter must not validate the result of earlier prompts
            logger.warning(f"[FM5] segmentation failed: {exc}", exc_info=True)
            self._hide_outline()
            self._status(self.tr("The segmentation of this area failed: {0}").format(exc))
            return
        if geometry is None or geometry.isEmpty():
            session.mask = None
            self._hide_outline()
            self._status(self.tr("No object found: add a point or draw a box"))
            return
        self._status(self.tr("Left click adds to the object, right click removes, Enter validates"))
        self._show_preview(geometry)

    def _geometry(self, session: Any) -> Any:
        """Polygons of the session inside the raster: a window can run past its edge, where nothing was drawn."""
        from qgis.core import QgsGeometry
        geometry = session.geometry()
        if geometry is None or geometry.isEmpty():
            return geometry
        return geometry.intersection(QgsGeometry.fromRect(self._host._active_layer.extent()))

    def _show_preview(self, geometry: Any) -> None:
        iface = self._host._iface()
        canvas = iface.mapCanvas() if iface is not None else None
        if canvas is None:
            return
        if self._outline is None:
            from ...adapters.qgis.coverage_layers.preview_overlay import ObjectOutline
            self._outline = ObjectOutline(canvas)
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
        """The object drawn becomes part of the selection (the panel emits it)."""
        session = self._session
        if session is None or not session.has_prompts or session.mask is None:
            self._status(self.tr("Click an object first"))
            return
        try:
            geometry = self._geometry(session)
        except Exception as exc:  # a mask GEOS cannot polygonize
            logger.warning(f"[FM5] segmented object not validated: {exc}", exc_info=True)
            self._status(self.tr("The segmentation of this area failed: {0}").format(exc))
            return
        if geometry is None or geometry.isEmpty():
            self._status(self.tr("No object found: add a point or draw a box"))
            return
        wkt = geometry.asWkt()
        session.clear()
        self._hide_preview()
        self._status('')
        self._host._call(self._host._raster_panel, 'add_segment', wkt)

    def clear(self) -> None:
        """Escape: forget the object being drawn, the validated ones stay."""
        self.cancel()
        self._status('')

    def session_info(self) -> Optional[Any]:
        """The encoded window, for the tests."""
        return self._session
