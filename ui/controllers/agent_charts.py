# -*- coding: utf-8 -*-
"""The d3 charts of the chat: the tools show_chart, export_chart and add_chart_to_layout, the buttons of a chart card,
and the charts of the print layouts kept drawn from their layers.

Main thread. The charts of a conversation are kept here by id (``MAX_KEPT``), with their request: an export or a layout
draws them again, light, for paper; the chat shows them in the theme of the panel.
"""
from __future__ import annotations

import logging
import os
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QObject, QTimer

from ...adapters.agent import chart_renderer
from ...adapters.public_api import charts as layout_charts
from ...core.agent.charts import (
    FORMATS, MAX_KEPT, Chart, ChartError, ChartRequest, chart_spec, page_html, parse_request, rows_data, summary,
)
from ...core.agent.tool_executor import ToolFailure, WithImages

logger = logging.getLogger("FilterMate.agent")

SYNC_DELAY_MS = 600  # a filter set on several layers at once draws each chart once
MISSING = ("Charts need QtWebEngine, which this QGIS does not have (QGIS 4 has it): for bars or a histogram that "
           "follow the filters, create_widget kind chart.")


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


def _labels() -> Tuple[str, str, str]:
    """The words a chart writes: the bar of the others, an empty value, the axis of a count."""
    return _tr("Others"), _tr("(empty)"), _tr("Features")


def draw(request: ChartRequest, theme: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """``request`` drawn: its SVG, its data, what to say of it, the errors of its page."""
    others, empty, count = _labels()
    if request.layer:
        data, meta = layout_charts.read_data(request, others, empty)
    else:
        data, meta = rows_data(request, others, empty)
    spec = chart_spec(request, data, theme, x_type=meta.get("x_type", ""), others=others,
                      count_label=count if request.kind == "histogram" else "")
    rendered = chart_renderer.render(page_html(spec, request.code))
    return rendered.svg, data, meta, rendered.errors


def _aspect(svg_text: str) -> float:
    renderer = chart_renderer.svg_renderer(svg_text)
    size = renderer.defaultSize()
    return size.height() / size.width() if size.width() > 0 else 0.625


def _unique(folder: str, stem: str, extension: str) -> str:
    path = os.path.join(folder, f"{stem}.{extension}")
    number = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{stem}_{number}.{extension}")
        number += 1
    return path


def file_stem(text: str) -> str:
    """A name of file from a title: letters, digits, dashes and underscores, 60 at most."""
    kept = "".join(char if char.isalnum() or char in "-_" else "_" for char in text.strip())
    kept = "_".join(part for part in kept.split("_") if part)
    return kept[:60] or "chart"


class AgentCharts(QObject):
    """The charts of the conversation and the charts of the layouts."""

    def __init__(self, is_dark: Callable[[], bool], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._is_dark = is_dark
        self._charts: Dict[str, Chart] = {}
        self._next = 1
        self.pending: Optional[Chart] = None  # drawn by show_chart, shown as a card when the tool ends
        self._layers_due: set = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SYNC_DELAY_MS)
        self._timer.timeout.connect(self._redraw_due)
        self._watched: Dict[str, Any] = {}

    # --- the tools ------------------------------------------------------------------------------------------

    def show_chart(self, arguments: Dict[str, Any], expert: bool, share_values: bool):
        if not chart_renderer.available():
            raise ToolFailure(MISSING)
        try:
            request = parse_request(arguments, expert=expert)
            theme = "dark" if self._is_dark() else "light"
            svg, data, meta, errors = draw(request, theme)
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(str(exc)) from None
        if request.layer and meta.get("layer_id"):
            request = replace(request, layer=meta["layer_id"])  # by id from now on: a layer renamed stays its chart
        chart = Chart(f"c{self._next}", request, svg, theme, meta)
        self._next += 1
        self._charts[chart.chart_id] = chart
        for old in list(self._charts)[:-MAX_KEPT]:
            del self._charts[old]
        self.pending = chart
        answer = summary(chart, data, share_values)
        if errors:
            answer["errors"] = errors
        if request.code:
            # The model sees what its code drew: an error of layout is not an error of JavaScript.
            from ...adapters.public_api.map_images import jpeg_base64
            picture = chart_renderer.image(svg, 1.0, "#ffffff" if theme == "light" else "#1a1a19")
            return WithImages(answer, (("image/jpeg", jpeg_base64(picture)),))
        return answer

    def chart(self, chart_id: str) -> Chart:
        chart = self._charts.get(str(chart_id or ""))
        if chart is None:
            known = ", ".join(self._charts) or "none yet"
            raise ToolFailure(f"no chart {chart_id!r} in this conversation (charts: {known}): show_chart first")
        return chart

    def light_svg(self, chart: Chart) -> str:
        """The chart drawn light, for paper; drawn again from its layer as filtered now."""
        if chart.theme == "light" and not chart.request.layer:
            return chart.svg
        try:
            svg, _, _, _ = draw(chart.request, "light")
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(str(exc)) from None
        return svg

    def export_chart(self, arguments: Dict[str, Any], export_root: str) -> Dict[str, Any]:
        from ...filtermate_api.export_root import ExportRootError, prepare_export_root, resolve_export_folder
        if not chart_renderer.available():
            raise ToolFailure(MISSING)
        chart = self.chart(arguments.get("chart_id", ""))
        file_format = arguments.get("format") or "png"
        if file_format not in FORMATS:
            raise ToolFailure(f"format is one of {', '.join(FORMATS)}")
        try:
            folder = resolve_export_folder(prepare_export_root(export_root), arguments.get("subfolder") or "charts")
        except ExportRootError as exc:
            logger.error("Agent chart export refused: %s (%s)", exc, export_root)
            raise ToolFailure("The export folder is not available.") from None
        except ValueError:
            raise ToolFailure("Invalid subfolder.") from None
        os.makedirs(folder, exist_ok=True)
        path = _unique(str(folder), file_stem(arguments.get("name") or chart.request.title or chart.chart_id),
                       file_format)
        try:
            size = chart_renderer.write(self.light_svg(chart), path, file_format, int(arguments.get("dpi") or 192))
        except (OSError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(f"the chart could not be written: {exc}") from None
        return {"path": os.path.relpath(path, str(folder)), "bytes": size, "format": file_format}

    def add_to_layout(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not chart_renderer.available():
            raise ToolFailure(MISSING)
        chart = self.chart(arguments.get("chart_id", ""))
        svg = self.light_svg(chart)
        try:
            answer = layout_charts.add_to_layout(arguments.get("layout", ""), svg, chart.request.as_arguments(),
                                                 _aspect(svg), x=arguments.get("x"), y=arguments.get("y"),
                                                 width=arguments.get("width"))
        except ChartError as exc:
            raise ToolFailure(str(exc)) from None
        self.watch_layers()
        answer.pop("uuid", None)
        answer["follows_filter"] = bool(chart.request.layer)
        return answer

    # --- the buttons of a card (the user's own action: no question) -------------------------------------------

    def save_as(self, chart_id: str, path: str) -> None:
        chart = self.chart(chart_id)
        extension = os.path.splitext(path)[1].lower().lstrip(".")
        file_format = "jpg" if extension in ("jpg", "jpeg") else extension
        if file_format not in FORMATS:
            file_format, path = "png", path + ".png"
        chart_renderer.write(self.light_svg(chart), path, file_format, 192)

    def put_in_layout(self, chart_id: str, layout_name: str) -> Dict[str, Any]:
        return self.add_to_layout({"chart_id": chart_id, "layout": layout_name})

    # --- the charts of the layouts, drawn again when the filter of their layer changes -------------------------

    def watch_layers(self) -> None:
        """Follow the filter of every layer a chart of a layout is drawn from (called when the project or its
        layouts change)."""
        try:
            wanted = set(layout_charts.layer_ids_of_charts())
        except Exception:  # a project closing
            logger.debug("Charts of the layouts not listed", exc_info=True)
            return
        project = QgsProject.instance()
        for layer_id in list(self._watched):
            if layer_id not in wanted or project.mapLayer(layer_id) is None:
                self._unwatch(layer_id)
        for layer_id in wanted - set(self._watched):
            layer = project.mapLayer(layer_id)
            if isinstance(layer, QgsVectorLayer):
                slot = (lambda layer_id=layer_id: self._filter_changed(layer_id))
                layer.subsetStringChanged.connect(slot)
                self._watched[layer_id] = (layer, slot)

    def _unwatch(self, layer_id: str) -> None:
        layer, slot = self._watched.pop(layer_id)
        try:
            layer.subsetStringChanged.disconnect(slot)
        except (TypeError, RuntimeError):
            pass

    def unwatch_all(self) -> None:
        for layer_id in list(self._watched):
            self._unwatch(layer_id)
        self._timer.stop()

    def _filter_changed(self, layer_id: str) -> None:
        self._layers_due.add(layer_id)
        self._timer.start()

    def _redraw_due(self) -> None:
        due, self._layers_due = self._layers_due, set()
        if not chart_renderer.available():
            return
        for layer_id in due:
            for item, arguments in list(layout_charts.chart_items(layer_id)):
                try:
                    request = parse_request(arguments, expert=bool(arguments.get("code")))
                    svg, _, _, _ = draw(request, "light")
                except (ChartError, chart_renderer.ChartRenderError) as exc:
                    # Nothing left to draw (a filter that keeps nothing): the last drawing stays.
                    logger.info("A chart of a layout was not drawn again: %s", exc)
                    continue
                except Exception:
                    logger.warning("A chart of a layout was not drawn again", exc_info=True)
                    continue
                layout_charts.set_chart_svg(item, svg)

    def redraw_layer(self, layer_id: str) -> None:
        """Draw the charts of ``layer_id`` again now (tests, and a filter set while the timer waits)."""
        self._layers_due.add(layer_id)
        self._redraw_due()
