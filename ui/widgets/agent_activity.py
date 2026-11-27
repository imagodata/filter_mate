"""The agent's persistent network mark, static at rest and animated for visible work or dictation."""
from qgis.PyQt.QtCore import QByteArray, QCoreApplication, Qt
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QStyle, QStyleOptionFocusRect, QToolButton

from ..styles.mockup_design import AGENT_ACTIVITY_STYLES, STATIC_AGENT_PHASES, agent_activity_svg, tokens

PHASE_LABELS = {
    'idle': 'Ready for a message', 'complete': 'Finished — ready for a message',
    'thinking': 'Thinking', 'reading': 'Reading data', 'working': 'Working',
    'fetching': 'Fetching data', 'responding': 'Writing the response',
    'waiting': 'Waiting', 'retry': 'Retrying', 'stopping': 'Stopped or stopping',
    'drafting': 'You are writing a message', 'queued': 'Messages are queued',
    'error': 'The request needs your attention', 'searching': 'Searching for data',
    'processing': 'Processing data', 'editing': 'Editing a layer', 'exporting': 'Exporting files',
    'designing': 'Designing the map', 'navigating': 'Navigating in QGIS',
    'confirming': 'Waiting for your confirmation', 'listening': 'Recording your voice',
    'transcribing': 'Transcribing your recording',
}


class AgentActivityIcon(QToolButton):
    """Own a renderer per indicator; replacing its document stops animation on Qt 5 as well as Qt 6."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('widget_agent_activity')
        self.setFixedSize(32, 32)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAccessibleName(QCoreApplication.translate('AgentPanel', 'More actions'))
        self._working = False
        self._phase = 'idle'
        self._interaction = ''
        self._dark = False
        self._hovered = False
        self._document_state = None
        try:
            from qgis.PyQt.QtSvg import QSvgRenderer
        except ImportError:
            self._renderer = None  # QtSvg is optional, as for the other icons of the panel.
            self.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
        else:
            self._renderer = QSvgRenderer(self)
            self._renderer.setFramesPerSecond(20)
            self._renderer.repaintNeeded.connect(self.update)
        self._sync_animation()

    def set_working(self, working):
        if working and not self._working:
            self._phase = 'thinking'
        elif not working and self._working:
            self._phase = 'complete'
        self._working = bool(working)
        self._sync_animation()

    @property
    def phase(self):
        return self._phase

    def set_phase(self, phase):
        self._phase = phase if phase in AGENT_ACTIVITY_STYLES else 'thinking'
        self._sync_animation()

    @property
    def display_phase(self):
        return self._phase if self._working else self._interaction or self._phase

    def set_interaction(self, interaction):
        self._interaction = interaction if interaction in ('drafting', 'queued', 'confirming', 'listening', 'transcribing') else ''
        self._sync_animation()

    def refresh_look(self, dark):
        self._dark = bool(dark)
        self._sync_animation()

    def _sync_animation(self):
        phase = self.display_phase
        label = QCoreApplication.translate('AgentActivity', PHASE_LABELS[phase])
        self.setToolTip(label + '\n' + self.accessibleName())
        self.setAccessibleDescription(label)
        if self._renderer is None:
            return
        active = self._working or self._interaction in ('listening', 'transcribing')
        state = (self._dark, active and self.isVisible() and phase not in STATIC_AGENT_PHASES, phase, self._hovered)
        if state == self._document_state:
            return
        self._document_state = state
        self._renderer.load(QByteArray(agent_activity_svg(tokens(self._dark)['fm_icon'], state[1], phase,
                                                        hovered=self._hovered).encode('utf-8')))
        self.update()

    def enterEvent(self, event):  # noqa: N802 - Qt virtual
        super().enterEvent(event)
        self._hovered = True
        self._sync_animation()

    def leaveEvent(self, event):  # noqa: N802 - Qt virtual
        super().leaveEvent(event)
        self._hovered = False
        self._sync_animation()

    def showEvent(self, event):  # noqa: N802 - Qt virtual
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):  # noqa: N802 - Qt virtual
        super().hideEvent(event)
        self._hovered = False
        self._sync_animation()

    def paintEvent(self, event):  # noqa: N802 - Qt virtual
        if self._renderer is None:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        self._renderer.render(painter)
        if self.hasFocus():
            focus = QStyleOptionFocusRect()
            focus.initFrom(self)
            focus.rect = self.rect().adjusted(1, 1, -1, -1)
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_FrameFocusRect, focus, painter, self)
        painter.end()
