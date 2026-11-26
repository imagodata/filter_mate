# -*- coding: utf-8 -*-
"""The charts of the chat: the tools show_chart, run_chart_code, export_chart and add_chart_to_layout, the buttons
of a chart card, and the charts of the print layouts kept drawn from their layers.

Main thread. A chart of show_chart is drawn in Python (``core/agent/chart_render.py``) on every QGIS; only the d3 code
of the expert mode (run_chart_code) needs the page of QtWebEngine (QGIS 4). The charts of a conversation are kept here
by id (``MAX_KEPT``) with the data they were drawn with: a card draws its chart again at its width, a save or an
export shows what the card shows, light for paper, at the size asked. A chart put in a layout is drawn again from its
layer when the filter of that layer changes; never one drawn by code, and never code a project holds.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication, QObject, QTimer

from ...adapters.agent import chart_renderer
from ...adapters.public_api import charts as layout_charts
from ...core.agent import chart_render
from ...core.agent.charts import (
    FORMATS, MAX_KEPT, Chart, ChartError, ChartRequest, chart_spec, page_html, parse_request, rows_data, sanitize_svg,
    summary,
)
from ...core.agent.infographics import (
    InfographicRequest,
    compose_infographic,
    infographic_page,
    parse_infographic,
    svg_size,
)
from ...core.agent.tool_executor import ToolFailure, WithImages

logger = logging.getLogger("FilterMate.agent")

SYNC_DELAY_MS = 600  # a filter set on several layers at once draws each chart once
MAX_REDRAWN = 12  # charts of layouts drawn again after one change of filters
REDRAW_BUDGET_S = 4.0  # and for so long at most in one round: QGIS waits meanwhile; the others in the next round
MISSING = "Code charts need QtWebEngine, which this QGIS does not have (QGIS 4 has it): show_chart draws the kinds."
INFOGRAPHIC_FORMATS = ("html",) + FORMATS


class Infographic:
    """An infographic of the conversation: kept charts stacked into one SVG, always light for paper."""

    def __init__(self, infographic_id: str, request: InfographicRequest, chart_ids: List[str], svg: str,
                 width: int, height: int) -> None:
        self.infographic_id = infographic_id
        self.request = request
        self.chart_ids = chart_ids
        self.svg = svg
        self.width = width
        self.height = height


RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{number}" for number in range(1, 10)} | {
    f"LPT{number}" for number in range(1, 10)}


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


def _labels() -> Tuple[str, str, str]:
    """The words a chart writes: the bar of the others, an empty value, the axis of a count."""
    return _tr("Others"), _tr("(empty)"), _tr("Features")


def _spec(request: ChartRequest, data: List[Dict[str, Any]], meta: Dict[str, Any], theme: str) -> Dict[str, Any]:
    others, _, count = _labels()
    return chart_spec(request, data, theme, x_type=meta.get("x_type", ""), others=others,
                      count_label=count if request.kind == "histogram" else "")


def read(request: ChartRequest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The data of ``request``: its layer as filtered now, or its rows."""
    others, empty, _ = _labels()
    if request.layer:
        return layout_charts.read_data(request, others, empty)
    return rows_data(request, others, empty)


def template_svg(request: ChartRequest, data: List[Dict[str, Any]], meta: Dict[str, Any], theme: str,
                 width: Optional[int] = None, height: Optional[int] = None) -> Tuple[str, List[chart_render.Mark]]:
    """A chart of a kind drawn in Python, at the size of its request or at ``width`` x ``height`` (a card); cleaned
    as an SVG of a page is: nothing reaches QtSvg that was not checked. Its marks with it."""
    started = time.perf_counter()
    svg, marks = chart_render.render(_spec(request, data, meta, theme), width, height)
    svg = sanitize_svg(svg)
    logger.debug("Agent chart %s drawn in %.1f ms (%d marks)", request.kind, (time.perf_counter() - started) * 1000,
                 len(marks))
    return svg, marks


def draw(request: ChartRequest, theme: str, data: Optional[List[Dict[str, Any]]] = None,
         meta: Optional[Dict[str, Any]] = None, code: str = ""
         ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """``request`` drawn (with ``data`` when given, else read now): its SVG, its data, what to say of it, the errors
    of its page (code only: a kind is drawn in Python)."""
    if data is None:
        data, meta = read(request)
    meta = meta or {}
    if not code:
        return template_svg(request, data, meta, theme)[0], data, meta, []
    rendered = chart_renderer.render(page_html(_spec(request, data, meta, theme), code))
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
    """A name of file from a title: letters, digits, dashes and underscores, 60 at most; never a name Windows keeps
    for a device (CON, NUL, COM1...)."""
    kept = "".join(char if char.isalnum() or char in "-_" else "_" for char in str(text).strip())
    kept = "_".join(part for part in kept.split("_") if part)[:60] or "chart"
    return f"chart_{kept}" if kept.split(".")[0].upper() in RESERVED else kept


def _plain_errors(errors: List[str]) -> List[str]:
    """Errors of a page told without their words, to a user who does not share values: a script may write the values
    of the data in an error (2026-11-22, second review: the words before a colon still held them)."""
    return [f"{len(errors)} error(s) in the page; their words are not sent, the values of the data are not shared"]


class AgentCharts(QObject):
    """The charts of the conversation and the charts of the layouts."""

    def __init__(self, is_dark: Callable[[], bool], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._is_dark = is_dark
        self._charts: Dict[str, Chart] = {}
        self._next = 1
        self.pending: Optional[Chart] = None  # drawn by show_chart or run_chart_code, shown as a card at its end
        self._infographics: Dict[str, Infographic] = {}
        self._next_infographic = 1
        self.pending_infographic: Optional[Infographic] = None  # stacked by show_infographic, shown as a card
        self._items_due: List[Tuple[str, str]] = []  # (layout name, uuid) of charts of layouts to draw again
        self._redrawing = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SYNC_DELAY_MS)
        self._timer.timeout.connect(self._redraw_due)
        self._watched: Dict[str, Any] = {}

    def forget(self) -> None:
        """A new conversation, another project: the ids of the charts start again."""
        self._charts = {}
        self._next = 1
        self.pending = None
        self._infographics = {}
        self._next_infographic = 1
        self.pending_infographic = None

    def _keep(self, request: ChartRequest, svg: str, theme: str, meta: Dict[str, Any], data: List[Dict[str, Any]],
              code: str = "") -> Chart:
        chart = Chart(f"c{self._next}", request, svg, theme, meta, list(data), code)
        self._next += 1
        self._charts[chart.chart_id] = chart
        for old in list(self._charts)[:-MAX_KEPT]:
            del self._charts[old]
        self.pending = chart
        return chart

    # --- the tools ------------------------------------------------------------------------------------------

    def show_chart(self, arguments: Dict[str, Any], share_values: bool):
        try:
            request = parse_request(arguments)
            theme = "dark" if self._is_dark() else "light"
            svg, data, meta, errors = draw(request, theme)
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(str(exc) if share_values else _plain_errors([str(exc)])[0]) from None
        if request.layer and meta.get("layer_id"):
            request = replace(request, layer=meta["layer_id"])  # by id from now on: a layer renamed stays its chart
        chart = self._keep(request, svg, theme, meta, data)
        answer = summary(chart, data, share_values)
        if errors:
            answer["errors"] = errors if share_values else _plain_errors(errors)
        return answer

    def run_chart_code(self, arguments: Dict[str, Any], share_values: bool):
        """d3 code of the agent over the data of a chart of this conversation (expert mode, asked at each run)."""
        if not chart_renderer.available():
            raise ToolFailure(MISSING)
        source = self.chart(arguments.get("chart_id", ""))
        code = arguments.get("code") or ""
        if not isinstance(code, str) or not code.strip():
            raise ToolFailure("code is the body of function(d3, svg, data, width, height, palette)")
        # Drawn light whatever the theme: a chart of code is never drawn again without asking, and it goes to paper.
        theme = "light"
        try:
            svg, data, meta, errors = draw(source.request, theme, source.data, source.meta, code)
            picture = chart_renderer.image(svg, 1.0, "#ffffff") if share_values else None
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            # The code of the model may have thrown the values of the data (throw new
            # Error(JSON.stringify(data))): told whole, they reach the model although the user does not share
            # them (audit of 2026-11-24). As for the errors field below: count, not words.
            raise ToolFailure(str(exc) if share_values else _plain_errors([str(exc)])[0]) from None
        finally:
            # A page the code ran in may have opened a connection (WebRTC from a frame of its own): it goes with it.
            chart_renderer.drop_page()
        chart = self._keep(source.request, svg, theme, dict(meta, drawn_from=source.chart_id), data, code)
        answer = summary(chart, data, False)
        answer["drawn_from"] = source.chart_id
        if errors:
            answer["errors"] = errors if share_values else _plain_errors(errors)
        if picture is None:  # an image of the chart shows its values: not sent to a user who does not share them
            return answer
        # The model sees what its code drew: an error of layout is not an error of JavaScript.
        from ...adapters.public_api.map_images import jpeg_base64
        return WithImages(answer, (("image/jpeg", jpeg_base64(picture)),))

    def chart(self, chart_id: str) -> Chart:
        chart = self._charts.get(str(chart_id or ""))
        if chart is None:
            known = ", ".join(self._charts) or "none yet"
            raise ToolFailure(f"no chart {chart_id!r} in this conversation (charts: {known}): show_chart first")
        return chart

    def paper_svg(self, chart: Chart) -> str:
        """The chart as the card shows it, drawn light for paper at the size asked: its data as drawn, never read
        again. A chart of code is kept as drawn (its code is not run again without asking)."""
        if chart.code:
            return chart.svg
        try:
            svg, _, _, _ = draw(chart.request, "light", chart.data, chart.meta)
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(str(exc)) from None
        return svg

    def export_chart(self, arguments: Dict[str, Any], export_root: str) -> Dict[str, Any]:
        from ...filtermate_api.export_root import ExportRootError, prepare_export_root, resolve_export_folder
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
            size = chart_renderer.write(self.paper_svg(chart), path, file_format, int(arguments.get("dpi") or 192),
                                        title=chart.request.title)
        except (OSError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(f"the chart could not be written: {exc}") from None
        return {"path": os.path.relpath(path, str(folder)), "bytes": size, "format": file_format}

    def infographic(self, infographic_id: str) -> Infographic:
        infographic = self._infographics.get(str(infographic_id or ""))
        if infographic is None:
            known = ", ".join(self._infographics) or "none yet"
            raise ToolFailure(f"no infographic {infographic_id!r} in this conversation (infographics: {known}): "
                              "show_infographic first")
        return infographic

    def show_infographic(self, arguments: Dict[str, Any], share_values: bool):
        """Stack charts of this conversation into one infographic, drawn light: what the card shows."""
        try:
            request = parse_infographic(arguments)
            svgs = [self.paper_svg(self.chart(chart_id)) for chart_id in request.chart_ids]
            svg = compose_infographic(request, svgs)
            width, height = svg_size(svg)
        except (ChartError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(str(exc) if share_values else _plain_errors([str(exc)])[0]) from None
        infographic = Infographic(f"i{self._next_infographic}", request, list(request.chart_ids),
                                  svg, width, height)
        self._next_infographic += 1
        self._infographics[infographic.infographic_id] = infographic
        for old in list(self._infographics)[:-MAX_KEPT]:
            del self._infographics[old]
        self.pending_infographic = infographic
        return {"infographic_id": infographic.infographic_id, "title": request.title,
                "charts": list(request.chart_ids), "caption": request.caption, "source": request.source,
                "width": width, "height": height}

    def export_infographic(self, arguments: Dict[str, Any], export_root: str) -> Dict[str, Any]:
        """An infographic as a standalone HTML page (offline), or as PNG, JPG, SVG or vector PDF."""
        from ...filtermate_api.export_root import ExportRootError, prepare_export_root, resolve_export_folder
        infographic = self.infographic(arguments.get("infographic_id", ""))
        file_format = arguments.get("format") or "html"
        if file_format not in INFOGRAPHIC_FORMATS:
            raise ToolFailure(f"format is one of {', '.join(INFOGRAPHIC_FORMATS)}")
        try:
            folder = resolve_export_folder(prepare_export_root(export_root),
                                           arguments.get("subfolder") or "infographics")
        except ExportRootError as exc:
            logger.error("Agent infographic export refused: %s (%s)", exc, export_root)
            raise ToolFailure("The export folder is not available.") from None
        except ValueError:
            raise ToolFailure("Invalid subfolder.") from None
        os.makedirs(folder, exist_ok=True)
        request = infographic.request
        path = _unique(str(folder), file_stem(arguments.get("name") or request.title
                                              or infographic.infographic_id), file_format)
        try:
            if file_format == "html":
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(infographic_page(request.title, infographic.svg, request.caption,
                                                  request.source))
                size = os.path.getsize(path)
            else:
                size = chart_renderer.write(infographic.svg, path, file_format, int(arguments.get("dpi") or 192),
                                            title=request.title)
        except (OSError, chart_renderer.ChartRenderError) as exc:
            raise ToolFailure(f"the infographic could not be written: {exc}") from None
        return {"path": os.path.relpath(path, str(folder)), "bytes": size, "format": file_format}

    def add_to_layout(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """A chart of a layer is drawn from its layer as filtered now, and again when that filter changes; a chart of
        rows or of code is put as it is."""
        chart = self.chart(arguments.get("chart_id", ""))
        follows = bool(chart.request.layer) and not chart.code
        if follows:
            try:
                svg, _, _, _ = draw(chart.request, "light")
            except (ChartError, chart_renderer.ChartRenderError) as exc:
                raise ToolFailure(str(exc)) from None
            kept = chart.request.as_arguments()
        else:
            svg = self.paper_svg(chart)
            kept = {"kind": chart.request.kind, "title": chart.request.title}  # never its code, never redrawn
        try:
            answer = layout_charts.add_to_layout(arguments.get("layout", ""), svg, kept, _aspect(svg),
                                                 x=arguments.get("x"), y=arguments.get("y"),
                                                 width=arguments.get("width"))
        except ChartError as exc:
            raise ToolFailure(str(exc)) from None
        self.watch_layers()
        answer.pop("uuid", None)
        answer["follows_filter"] = follows
        return answer

    # --- the buttons of a card (the user's own action: no question) -------------------------------------------

    def save_as(self, chart_id: str, path: str) -> None:
        chart = self.chart(chart_id)
        extension = os.path.splitext(path)[1].lower().lstrip(".")
        file_format = "jpg" if extension in ("jpg", "jpeg") else extension
        if file_format not in FORMATS:
            file_format, path = "png", path + ".png"
        chart_renderer.write(self.paper_svg(chart), path, file_format, 192, title=chart.request.title)

    def card_drawing(self, chart: Chart) -> Optional[Callable[[int, int], Tuple[str, List[chart_render.Mark]]]]:
        """What draws ``chart`` again at the size of its card, in the theme of the dock then; None for a chart of
        code, never run again without asking (its card scales the drawing it has)."""
        if chart.code:
            return None

        def drawn(width: int, height: int) -> Tuple[str, List[chart_render.Mark]]:
            theme = "dark" if self._is_dark() else "light"
            return template_svg(chart.request, chart.data, chart.meta, theme, width, height)
        return drawn

    def put_in_layout(self, chart_id: str, layout_name: str) -> Dict[str, Any]:
        return self.add_to_layout({"chart_id": chart_id, "layout": layout_name})

    def save_infographic_as(self, infographic_id: str, path: str) -> None:
        """PNG, JPG or SVG of an infographic card: where the user chooses (HTML stays a tool)."""
        infographic = self.infographic(infographic_id)
        extension = os.path.splitext(path)[1].lower().lstrip(".")
        file_format = "jpg" if extension in ("jpg", "jpeg") else extension
        if file_format not in FORMATS:
            file_format, path = "png", path + ".png"
        chart_renderer.write(infographic.svg, path, file_format, 192, title=infographic.request.title)

    # --- the charts of the layouts, drawn again when the filter of their layer changes -------------------------

    def watch_layers(self) -> None:
        """Follow the filter of every layer a chart of a layout is drawn from (called when the project, its layers or
        its layouts change, and after an undo or a redo)."""
        try:
            wanted = set(layout_charts.layer_ids_of_charts())
        except Exception:  # a project closing, an item of a project that holds anything
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
        self._items_due = []

    def _filter_changed(self, layer_id: str) -> None:
        try:
            items = [(item.layout().name(), item.uuid()) for item, _ in layout_charts.chart_items(layer_id)]
        except Exception:  # a project closing
            logger.debug("Charts of a layer not listed", exc_info=True)
            return
        self._items_due += [item for item in items if item not in self._items_due]
        self._timer.start()

    def _redraw_due(self) -> None:
        """Draw again the charts of layouts whose layer changed, a few at a time: what one round does not reach
        waits for the next one, after QGIS has had its events (2026-11-22, second review: the rest stayed stale)."""
        if self._redrawing:
            self._timer.start()
            return
        self._redrawing = True
        started, drawn = time.monotonic(), 0
        try:
            while self._items_due:
                if drawn >= MAX_REDRAWN or time.monotonic() - started > REDRAW_BUDGET_S:
                    self._timer.start()
                    return
                layout_name, uuid = self._items_due.pop(0)
                item = layout_charts.find_item(layout_name, uuid)
                if item is None:
                    continue
                try:
                    arguments = json.loads(str(item.customProperty(layout_charts.PROPERTY) or "null"))
                    if not isinstance(arguments, dict) or "code" in arguments:  # code a project holds: never run
                        continue
                    svg, _, _, _ = draw(parse_request(arguments), "light")
                    layout_charts.set_chart_svg(item, svg)
                    drawn += 1
                except (ChartError, ValueError) as exc:
                    # Nothing left to draw (a filter that keeps nothing): the last drawing stays.
                    logger.info("A chart of a layout was not drawn again: %s", exc)
                except Exception:  # an item deleted meanwhile, a project closing
                    logger.warning("A chart of a layout was not drawn again", exc_info=True)
        finally:
            self._redrawing = False

    def redraw_layer(self, layer_id: str) -> None:
        """Draw the charts of ``layer_id`` again now (tests)."""
        self._filter_changed(layer_id)
        self._timer.stop()
        self._redraw_due()
