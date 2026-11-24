# -*- coding: utf-8 -*-
"""
Read-only widgets of the favorites manager summary.

A value the user can select is shown as it is stored: a long expression wraps
inside a read-only text view (it is never altered with invisible characters),
so what is copied pastes unchanged into the QGIS expression editor.
"""

try:
    from qgis.PyQt.QtCore import QEvent, Qt
    from qgis.PyQt.QtGui import QFont, QTextCursor, QTextOption
    from qgis.PyQt.QtWidgets import QFrame, QLabel, QPlainTextEdit
    HAS_QGIS = True
except ImportError:  # no QGIS: the dialog module is not built either
    HAS_QGIS = False
    QEvent = Qt = None
    QFont = QTextCursor = QTextOption = None
    QFrame = QLabel = QPlainTextEdit = object

# An expression longer than this many wrapped lines scrolls inside its own view.
EXPRESSION_MAX_LINES = 6


class ExpressionView(QPlainTextEdit):
    """Frameless read-only view of an expression: wrapped anywhere, mono font, fits its text.

    The height follows the number of wrapped lines up to ``max_lines``, then the view
    scrolls vertically. The width never grows with the text.
    """

    def __init__(self, text: str, mono_family: str, max_lines: int = EXPRESSION_MAX_LINES, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryFilter")
        self._max_lines = max(1, max_lines)
        font = QFont(mono_family)
        font.setStyleHint(QFont.StyleHint.Monospace)  # a mono face when the family is missing
        self.setFont(font)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setPlainText(text)
        self._fit_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_height()  # the wrapped line count depends on the width

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fit_height()  # the stylesheet font arrives after the first layout

    def _fit_height(self) -> None:
        """Height of the wrapped text, at most ``max_lines`` lines.

        Read from the cursor rectangles of the first and last characters: asking for
        them makes the plain text document lay its text out (it is lazy otherwise),
        so the numbers are the ones painted, whatever font the system falls back to.
        """
        self.ensurePolished()  # the line height is the one of the styled font
        self.verticalScrollBar().setValue(0)
        document = self.document()
        self.cursorRect(QTextCursor(document))  # lays the first block out
        last_cursor = QTextCursor(document)
        last_cursor.movePosition(QTextCursor.MoveOperation.End)
        last = self.cursorRect(last_cursor)
        margin = document.documentMargin()
        # Distance between two painted lines (the height of a line can be larger than that)
        layout = document.firstBlock().layout()
        if layout.lineCount() > 1:
            pitch = layout.lineAt(1).y() - layout.lineAt(0).y()
        else:
            pitch = layout.lineAt(0).height()
        pitch = max(pitch, 1.0)
        content = last.y() + last.height() + margin
        # Capped: end on a line boundary, so no sliver of the next line shows under the last one
        capped = self._max_lines * pitch + margin
        self.setFixedHeight(int(capped) if content > capped else int(content) + 2)


def text_value(text: str) -> "QLabel":
    """Selectable, word-wrapped plain-text label; the text is not altered."""
    label = QLabel(text)
    label.setObjectName("summaryValue")
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label
