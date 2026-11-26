# -*- coding: utf-8 -*-
"""The page of QtWebEngine that draws the d3 code of the agent (run_chart_code), kept hidden, and what is made of the
SVG of a chart (an image, a file, a PDF).

Main thread only. The kinds of show_chart are drawn in Python (``core/agent/chart_render.py``); the page draws only
code of the expert mode. One page, made the first time code is drawn (QtWebEngine starts in about a second) and kept:
each run loads its own HTML (``core/agent/charts.page_html``) and hands back its SVG, its look written on each element.
The page reaches nothing: an off-the-record profile, a Content-Security-Policy in the HTML, and an interceptor that
refuses every request but the page itself; no window, no storage, no clipboard. Code of the model (expert mode) that
never ends is stopped by a delay, and the page is dropped with it.

QtWebEngine is in the Python of QGIS 4 (PyQt6.QtWebEngineCore); QGIS 3 has only QtWebKit, too old for d3 7:
``available()`` is False there and run_chart_code is not offered.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger("FilterMate.agent")

LOAD_TIMEOUT_MS = 15000  # the first load starts QtWebEngine
READ_TIMEOUT_MS = 5000
ALLOWED_SCHEMES = ("data", "about")
JPEG_QUALITY = 92
# 160 MB of image in memory at most: 600 dpi of a chart of 640 x 400 is 4,000 x 2,500 (10 M); the largest chart
# (1,600 x 1,200) is refused beyond about 400 dpi, with the words to lower it.
MAX_PIXELS = 40_000_000


class ChartEngineMissing(RuntimeError):
    """No QtWebEngine in this QGIS."""


class ChartRenderError(RuntimeError):
    """The page drew no chart: the words are for the model."""


class ChartBusy(ChartRenderError):
    """Another chart is being drawn: the page is one, and its wait lets other events run (a timer, a reply)."""


@dataclass
class Rendered:
    svg: str
    errors: List[str] = field(default_factory=list)


_engine: Optional[str] = None  # "" when checked and missing


def available() -> bool:
    """Whether QtWebEngine can be used from Python here (QGIS 4)."""
    global _engine
    if _engine is None:
        try:
            from qgis.PyQt.QtWebEngineCore import QWebEnginePage  # noqa: F401
            _engine = "ok"
        except Exception:  # ImportError, or a QGIS 3 shim that has no such module
            _engine = ""
    return _engine == "ok"


def _wait(loop) -> None:
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QThread
    application = QCoreApplication.instance()
    if application is not None and QThread.currentThread() is application.thread():
        loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)  # a click must not start a tool meanwhile
    else:
        loop.exec()


class _Page:
    """The hidden page and its profile; dropped when a chart did not end."""

    def __init__(self) -> None:
        from qgis.PyQt.QtWebEngineCore import (QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
                                               QWebEngineUrlRequestInterceptor)

        class Interceptor(QWebEngineUrlRequestInterceptor):
            def interceptRequest(self, info) -> None:  # noqa: N802 (Qt)
                if info.requestUrl().scheme() not in ALLOWED_SCHEMES:
                    logger.info("A chart asked for %s: refused", info.requestUrl().scheme())
                    info.block(True)

        class Page(QWebEnginePage):
            def __init__(self, profile, errors) -> None:
                super().__init__(profile)
                self._errors = errors

            def javaScriptConsoleMessage(self, level, message, line, source) -> None:  # noqa: N802 (Qt)
                if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel and len(self._errors) < 5:
                    self._errors.append(f"{message} (line {line})"[:300])

            def acceptNavigationRequest(self, url, kind, main_frame) -> bool:  # noqa: N802 (Qt)
                return url.scheme() in ALLOWED_SCHEMES

            def createWindow(self, kind):  # noqa: N802 (Qt)
                return None

        self.console: List[str] = []
        self.profile = QWebEngineProfile()  # no name: off the record, nothing written on the disk
        self.interceptor = Interceptor(self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.page = Page(self.profile, self.console)
        settings = self.page.settings()
        attribute = QWebEngineSettings.WebAttribute
        for name, value in (("LocalContentCanAccessRemoteUrls", False), ("LocalContentCanAccessFileUrls", False),
                            ("LocalStorageEnabled", False), ("JavascriptCanOpenWindows", False),
                            ("JavascriptCanAccessClipboard", False), ("JavascriptCanPaste", False),
                            ("PluginsEnabled", False), ("WebGLEnabled", False), ("Accelerated2dCanvasEnabled", False),
                            ("AutoLoadImages", True), ("JavascriptEnabled", True)):
            if hasattr(attribute, name):
                settings.setAttribute(getattr(attribute, name), value)

    def drop(self) -> None:
        try:
            self.page.deleteLater()
            self.profile.deleteLater()
        except RuntimeError:
            pass


_page: Optional[_Page] = None
_busy = False


def busy() -> bool:
    return _busy


def _the_page() -> _Page:
    global _page
    if not available():
        raise ChartEngineMissing("QtWebEngine is not in this QGIS")
    if _page is None:
        _page = _Page()
    return _page


def drop_page() -> None:
    """Free the page (the plugin unloads)."""
    global _page
    if _page is not None:
        _page.drop()
        _page = None


def render(html: str) -> Rendered:
    """Load ``html`` in the hidden page and read its SVG back, cleaned (``sanitize_svg``). One at a time: the wait
    lets timers and replies run, and a second chart loaded meanwhile would replace the first in the one page
    (2026-11-22 review: the chart of a layout drawn again by its timer came back as the chart of the chat)."""
    global _busy
    if _busy:
        raise ChartBusy("another chart is being drawn: call again in a moment")
    _busy = True
    try:
        return _render(html)
    finally:
        _busy = False


def _render(html: str) -> Rendered:
    from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
    from ...core.agent.charts import ChartError, sanitize_svg
    page = _the_page()
    page.console.clear()
    loop = QEventLoop()
    state: dict = {}

    def loaded(ok: bool) -> None:
        state["loaded"] = ok
        loop.quit()

    page.page.loadFinished.connect(loaded)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    try:
        page.page.setHtml(html, QUrl("about:blank"))
        timer.start(LOAD_TIMEOUT_MS)
        _wait(loop)
    finally:
        timer.stop()
        try:
            page.page.loadFinished.disconnect(loaded)
        except (TypeError, RuntimeError):
            pass
    if "loaded" not in state:
        _drop_stuck()
        raise ChartRenderError("the chart did not end in time (a loop that never ends?)")
    if not state["loaded"]:
        raise ChartRenderError("the page of the chart could not be loaded")

    def read(value: Any) -> None:
        state["result"] = value
        loop.quit()

    page.page.runJavaScript("window.FMCharts ? FMCharts.result() : null", read)
    timer.start(READ_TIMEOUT_MS)
    _wait(loop)
    timer.stop()
    if "result" not in state:
        _drop_stuck()
        raise ChartRenderError("the chart did not end in time (a loop that never ends?)")
    try:
        result = json.loads(state["result"]) if isinstance(state["result"], str) else {}
    except ValueError:
        result = {}
    if not isinstance(result, dict):  # code of the model may have replaced FMCharts.result
        result = {}
    listed = result.get("errors") if isinstance(result.get("errors"), list) else []
    errors = [str(item)[:300] for item in listed][:5]
    errors += [item for item in page.console if item not in errors][:5 - len(errors)]
    svg = result.get("svg") if isinstance(result.get("svg"), str) else ""
    if not svg or "<svg" not in svg[:200]:
        raise ChartRenderError("no chart was drawn" + (": " + "; ".join(errors) if errors else ""))
    try:
        svg = sanitize_svg(svg)
    except ChartError as exc:
        raise ChartRenderError(str(exc)) from None
    svg_renderer(svg)  # QtSvg must read it: ChartRenderError otherwise
    unsupported = result.get("unsupported") if isinstance(result.get("unsupported"), list) else []
    if unsupported:
        errors.append("left out of the chart: " + ", ".join(str(item)[:40] for item in unsupported[:3])
                      + " (draw with SVG shapes and text only)")
    return Rendered(svg, errors)


def _drop_stuck() -> None:
    global _page
    logger.warning("A chart did not end in time: its page is dropped")
    if _page is not None:
        _page.drop()
        _page = None


# --- what is made of the SVG ---------------------------------------------------------------------------------------

def svg_renderer(svg: str):
    from qgis.PyQt.QtCore import QByteArray
    from qgis.PyQt.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ChartRenderError("the SVG of the chart could not be read")
    return renderer


def image(svg: str, scale: float = 1.0, background: Optional[str] = None):
    """The chart as a QImage, ``scale`` times its size in pixels; transparent unless ``background``."""
    from qgis.PyQt.QtCore import QSize, Qt
    from qgis.PyQt.QtGui import QColor, QImage, QPainter
    renderer = svg_renderer(svg)
    size = renderer.defaultSize()
    width, height = max(1, round(size.width() * scale)), max(1, round(size.height() * scale))
    if width * height > MAX_PIXELS:
        raise ChartRenderError("the image would be too large: a lower resolution")
    picture = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
    picture.fill(QColor(background) if background else QColor(Qt.GlobalColor.transparent))
    painter = QPainter(picture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    renderer.render(painter)
    painter.end()
    return picture


def write(svg: str, path: str, file_format: str, dpi: int = 192, title: str = "") -> int:
    """Write the chart to ``path`` as png, jpg, svg or pdf; returns its size in bytes. ``dpi`` sets the pixels of an
    image (96: the size of the chart); a PDF is drawn in vectors, one page the size of the chart."""
    import os
    if file_format not in ("png", "jpg", "svg", "pdf"):
        raise ChartRenderError("format is one of png, jpg, svg, pdf")
    if isinstance(dpi, bool) or not isinstance(dpi, int) or not 48 <= dpi <= 600:
        raise ChartRenderError("dpi is a whole number from 48 to 600")
    if file_format == "svg":
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg)
    elif file_format == "pdf":
        _write_pdf(svg, path, title)
    else:
        scale = max(0.5, min(dpi, 600) / 96.0)
        # A JPEG has no transparency: white under it, as on paper.
        picture = image(svg, scale, "#ffffff" if file_format == "jpg" else None)
        dots_per_metre = round(dpi / 0.0254)
        picture.setDotsPerMeterX(dots_per_metre)
        picture.setDotsPerMeterY(dots_per_metre)
        jpeg = file_format == "jpg"
        if not picture.save(path, "JPG" if jpeg else "PNG", JPEG_QUALITY if jpeg else -1):
            raise ChartRenderError("the image could not be written")
    return os.path.getsize(path)


def _write_pdf(svg: str, path: str, title: str) -> None:
    """One page of the size of the chart (a pixel of the chart is 0.75 point, as at 96 dpi), no margin; the shapes
    and the text stay vectors (QPdfWriter, in QtGui on Qt 5 and Qt 6: no QPrinter)."""
    from qgis.PyQt.QtCore import QMarginsF, QRectF, QSizeF
    from qgis.PyQt.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter
    renderer = svg_renderer(svg)
    size = renderer.defaultSize()
    writer = QPdfWriter(path)
    writer.setCreator("FilterMate")
    if title:
        writer.setTitle(title)
    writer.setResolution(96)
    page = QPageSize(QSizeF(size.width() * 0.75, size.height() * 0.75), QPageSize.Unit.Point, "",
                     QPageSize.SizeMatchPolicy.ExactMatch)
    writer.setPageLayout(QPageLayout(page, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)))
    painter = QPainter()
    if not painter.begin(writer):
        raise ChartRenderError("the PDF could not be written")
    try:
        renderer.render(painter, QRectF(0, 0, writer.width(), writer.height()))
    finally:
        painter.end()
