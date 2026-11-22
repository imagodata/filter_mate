# -*- coding: utf-8 -*-
"""The page of QtWebEngine that draws the d3 charts of the agent, kept hidden, and what is made of its SVG.

Main thread only. One page, made the first time a chart is drawn (QtWebEngine starts in about a second) and kept: each
chart loads its own HTML (``core/agent/charts.page_html``) and hands back its SVG, its look written on each element.
The page reaches nothing: an off-the-record profile, a Content-Security-Policy in the HTML, and an interceptor that
refuses every request but the page itself; no window, no storage, no clipboard. Code of the model (expert mode) that
never ends is stopped by a delay, and the page is dropped with it.

QtWebEngine is in the Python of QGIS 4 (PyQt6.QtWebEngineCore); QGIS 3 has only QtWebKit, too old for d3 7:
``available()`` is False there and the tools say so.
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
MAX_PIXELS = 40_000_000  # an export of 600 dpi of the largest chart is 10,000 x 7,500: no more


class ChartEngineMissing(RuntimeError):
    """No QtWebEngine in this QGIS."""


class ChartRenderError(RuntimeError):
    """The page drew no chart: the words are for the model."""


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
    """Load ``html`` in the hidden page and read its SVG back."""
    from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
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
        result = json.loads(state["result"] or "null") or {}
    except (TypeError, ValueError):
        result = {}
    errors = [str(item)[:300] for item in (result.get("errors") or [])][:5]
    errors += [item for item in page.console if item not in errors][:5 - len(errors)]
    svg = result.get("svg") or ""
    if not svg or "<svg" not in svg[:200]:
        raise ChartRenderError("no chart was drawn" + (": " + "; ".join(errors) if errors else ""))
    unsupported = result.get("unsupported") or []
    if unsupported:
        errors.append("not kept in the image: " + ", ".join(str(item) for item in unsupported)
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


def write(svg: str, path: str, file_format: str, dpi: int = 192) -> int:
    """Write the chart to ``path`` as png, jpg or svg; returns its size in bytes. ``dpi`` sets the pixels of an image
    (96: the size of the chart)."""
    import os
    if file_format == "svg":
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg)
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
