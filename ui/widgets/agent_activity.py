"""The agent's network mark, animated only while its activity indicator is visible."""
from qgis.PyQt.QtCore import QByteArray, Qt
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QWidget

from ..styles.mockup_design import agent_activity_svg, tokens


class AgentActivityIcon(QWidget):
    """Own a renderer per indicator; replacing its document stops animation on Qt 5 as well as Qt 6."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('widget_agent_activity')
        self.setFixedSize(24, 24)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._working = False
        self._dark = False
        self._document_state = None
        try:
            from qgis.PyQt.QtSvg import QSvgRenderer
        except ImportError:
            self._renderer = None  # QtSvg is optional, as for the other icons of the panel.
        else:
            self._renderer = QSvgRenderer(self)
            self._renderer.setFramesPerSecond(20)
            self._renderer.repaintNeeded.connect(self.update)
        self.hide()
        self._sync_animation()

    def set_working(self, working):
        self._working = bool(working)
        self.setVisible(self._working and self._renderer is not None)
        self._sync_animation()

    def refresh_look(self, dark):
        self._dark = bool(dark)
        self._sync_animation()

    def _sync_animation(self):
        if self._renderer is None:
            return
        state = (self._dark, self._working and self.isVisible())
        if state == self._document_state:
            return
        self._document_state = state
        self._renderer.load(QByteArray(agent_activity_svg(tokens(self._dark)['fm_icon'], state[1]).encode('utf-8')))
        self.update()

    def showEvent(self, event):  # noqa: N802 - Qt virtual
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):  # noqa: N802 - Qt virtual
        super().hideEvent(event)
        self._sync_animation()

    def paintEvent(self, event):  # noqa: N802 - Qt virtual
        if self._renderer is not None:
            painter = QPainter(self)
            self._renderer.render(painter)
            painter.end()
