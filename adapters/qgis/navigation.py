"""Short map transitions shared by agent, filtering and exploration; manual navigation always wins."""
import math

_TRANSITION = None


def transition_duration():
    try:
        from ...config.config import ENV_VARS, _get_option_value
        options = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('EXPLORATION', {})
        return max(0, min(600, int(_get_option_value(options.get('zoom_transition_ms'), 220))))
    except (ImportError, AttributeError, TypeError, ValueError):
        return 220


def stop_navigation(canvas):
    transition = getattr(canvas, '_filtermate_transition', None)
    if getattr(transition, '_filtermate_zoom_transition', False) is True:
        transition.cancel()


def _transition_class():
    global _TRANSITION
    if _TRANSITION is not None:
        return _TRANSITION
    from qgis.PyQt.QtCore import QObject, QEvent, QEasingCurve, QTimeLine, pyqtSignal
    from qgis.core import QgsProject, QgsRectangle

    class ExtentTransition(QObject):
        completed = pyqtSignal()
        _filtermate_zoom_transition = True

        def __init__(self, canvas, target, duration, feature_margin):
            super().__init__(canvas)
            self.canvas, self.target = canvas, QgsRectangle(target)
            self.start = QgsRectangle(canvas.extent())
            self.done, self.cancelled, self.writing = False, False, False
            self.history_written = False
            self.feature_margin = feature_margin
            self.timeline = QTimeLine(duration, self)
            self.timeline.setUpdateInterval(33)
            self.timeline.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.timeline.valueChanged.connect(self.frame)
            self.timeline.finished.connect(self.finish)
            canvas.extentsChanged.connect(self.external_change)
            canvas.destinationCrsChanged.connect(self.cancel)
            canvas.rotationChanged.connect(self.cancel)
            QgsProject.instance().cleared.connect(self.cancel)
            self.viewport = canvas.viewport()
            canvas.installEventFilter(self)
            self.viewport.installEventFilter(self)

        def frame(self, fraction):
            if self.done or fraction <= 0:
                return
            a, b, t = self.start, self.target, float(fraction)
            x = a.center().x() + (b.center().x() - a.center().x()) * t
            y = a.center().y() + (b.center().y() - a.center().y()) * t
            width = math.exp(math.log(a.width()) * (1-t) + math.log(b.width()) * t)
            height = math.exp(math.log(a.height()) * (1-t) + math.log(b.height()) * t)
            extent = QgsRectangle(x-width/2, y-height/2, x+width/2, y+height/2)
            self.writing = True
            try:
                if self.history_written:
                    # Replace the preceding animation frame in QGIS' native zoom history.
                    # Freeze and block signals only for the synchronous rewind, so no old frame
                    # renders and Back returns to the view before this navigation in one click.
                    blocked, frozen = self.canvas.blockSignals(True), self.canvas.isFrozen()
                    self.canvas.freeze(True)
                    try:
                        self.canvas.zoomToPreviousExtent()
                    finally:
                        self.canvas.freeze(frozen)
                        self.canvas.blockSignals(blocked)
                before = QgsRectangle(self.canvas.mapSettings().extent())
                if self.feature_margin:
                    self.canvas.setExtent(extent, True)
                else:
                    self.canvas.setExtent(extent)
                self.history_written = before != self.canvas.mapSettings().extent()
                self.canvas.refresh()
            finally:
                self.writing = False

        def external_change(self):
            if not self.writing:
                self.cancel()

        def eventFilter(self, watched, event):  # noqa: N802 - Qt name
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.Wheel, QEvent.Type.KeyPress,
                                QEvent.Type.TouchBegin):
                self.cancel()
            return False  # the user's event still reaches the map tool

        def finish(self):
            if not self.done:
                self.frame(1.0)
                self.end()

        def cancel(self):
            if not self.done:
                self.cancelled = True
                self.end()

        def end(self):
            self.done = True
            self.timeline.stop()
            self.canvas.removeEventFilter(self)
            self.viewport.removeEventFilter(self)
            if getattr(self.canvas, '_filtermate_transition', None) is self:
                self.canvas._filtermate_transition = None
            self.completed.emit()
            self.deleteLater()

    _TRANSITION = ExtentTransition
    return _TRANSITION


def navigate_extent(canvas, extent, *, feature_margin=False, wait=False, duration_ms=None):
    """Apply an extent with optional motion. A synchronous caller receives the actual final/manual view.

    Hidden/headless canvases and disabled transitions keep the immediate QGIS behavior. For feature
    zooms use QGIS' 5% margin. A second request cancels the first without restoring its old target.
    """
    from qgis.core import QgsRectangle
    from qgis.gui import QgsMapCanvas
    stop_navigation(canvas)
    duration = transition_duration() if duration_ms is None else max(0, min(600, int(duration_ms)))
    try:
        native = isinstance(canvas, QgsMapCanvas) and canvas.isVisible()
    except TypeError:  # lightweight API hosts without a native canvas
        native = False
    target = QgsRectangle(extent)
    start = canvas.extent() if native else None
    usable = native and not canvas.scaleLocked() and not canvas.isFrozen() and canvas.renderFlag() and all(
        math.isfinite(value) and value > 0 for value in (
        start.width(), start.height(), target.width(), target.height()))
    # Avoid a flight across the entire geographic map when crossing the date line.
    crosses_date_line = usable and canvas.mapSettings().destinationCrs().isGeographic() and abs(
        start.center().x() - target.center().x()) > 180
    if not duration or not usable or crosses_date_line:
        if feature_margin:
            canvas.zoomToFeatureExtent(extent)
        else:
            canvas.setExtent(extent)
            canvas.refresh()
        return True
    if feature_margin:
        target.scale(1.05)
    transition = _transition_class()(canvas, target, duration, feature_margin)
    canvas._filtermate_transition = transition
    if not wait:
        transition.timeline.start()
        return True
    from qgis.PyQt.QtCore import QEventLoop
    from ..agent.bounded_http import on_abort
    loop = QEventLoop()
    transition.completed.connect(loop.quit)
    canvas.destroyed.connect(loop.quit)
    forget = on_abort(transition.cancel)
    try:
        transition.timeline.start()
        if not transition.done:
            loop.exec()
        return not transition.cancelled
    finally:
        forget()
