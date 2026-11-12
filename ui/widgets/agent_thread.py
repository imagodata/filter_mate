# -*- coding: utf-8 -*-
"""The conversation of the AGENT section, drawn as the mockup draws it.

Requests in a tinted bubble on the right, each change in a card (what, expression, kept / total, Undo), the
steps of a request while it runs, the answer as text. Every label is plain text: what a model writes can
repeat what it read in a layer, and nothing of it is ever interpreted as HTML.
"""
from __future__ import annotations

import html
import re
from typing import Callable, List, Optional, Sequence

from qgis.PyQt.QtCore import QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QFont, QFontMetrics
from qgis.PyQt.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

BUBBLE_SHARE = 0.88  # of the width of the thread
ANSWER_DELAY_MS = 80  # the answer being written is drawn again at most so often, whatever the number of fragments
ANSWER_CHARS_PER_MS = 40  # and less often as it grows: drawing it costs as much as its length
DONE_COLOR = {"light": "#146a55", "dark": "#4fd1b0"}
# Background, border, title of an error card (mockup: Error board).
ERROR_COLORS = {"light": ("#fdf3f3", "#f0c2c2", "#8c1d1d"), "dark": ("#3a2224", "#6b3236", "#f2b8b8")}
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_BULLET = re.compile(r"^(\s*)[-*+]\s+")
_EMPHASIS = re.compile(r"(\*\*|__)(.+?)\1")
_CODE = re.compile(r"`([^`\n]+)`")


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


def plain_markdown(text: str) -> str:
    """What a model writes in Markdown, as plain text: no ``**``, bullets as ``•``, no heading marks."""
    lines = []
    for line in text.split("\n"):
        line = _HEADING.sub("", line)
        line = _BULLET.sub(lambda match: f"{match.group(1)}• ", line)
        line = _EMPHASIS.sub(lambda match: match.group(2), line)
        lines.append(_CODE.sub(lambda match: match.group(1), line))
    return "\n".join(lines)


def strong_markup(text: str, strong: Sequence[str]) -> str:
    """``text`` as rich text whose only markup is the bold of the ``strong`` names: everything else is escaped."""
    names = sorted({name for name in strong if name and name in text}, key=len, reverse=True)
    if not names:
        return html.escape(text)
    # Whole names only: a layer called "a" must not put every "a" of the sentence in bold.
    pattern = re.compile("|".join(rf"(?<!\w){re.escape(name)}(?!\w)" for name in names))
    out, start = [], 0
    for match in pattern.finditer(text):
        out.append(html.escape(text[start:match.start()]))
        out.append(f"<b>{html.escape(match.group(0))}</b>")
        start = match.end()
    out.append(html.escape(text[start:]))
    return "".join(out)


def plain_tooltip(text: str) -> str:
    """``text`` as a tooltip shows it word for word: a tooltip starting with a known tag is taken for rich text (an
    image it names is loaded); escaped in a paragraph that keeps spaces and line breaks, nothing of it is read."""
    return f'<p style="white-space: pre-wrap;">{html.escape(text)}</p>' if text else ""


def _plain_label(text: str, parent: QWidget, wrap: bool = True) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    label.setText(text)
    return label


class ElidedLabel(QLabel):
    """One line, cut with … to the width it gets; the whole text in its tooltip."""

    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self._full = text
        self.setToolTip(plain_tooltip(text))
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self.setText(QFontMetrics(self.font()).elidedText(self._full, Qt.TextElideMode.ElideRight, max(self.width(), 10)))


def _sheet(widget: QWidget, text: str) -> None:
    """A style sheet set only when it changes: setting it again repolishes the widget."""
    if widget.styleSheet() != text:
        widget.setStyleSheet(text)


Look = Callable[[dict, bool], None]


class _Item:
    """One line of the thread, what it says in plain text, and how it takes the colors of the theme.

    Every item draws itself again on a theme change: one drawn before the dock had its theme (a conversation
    restored when a project opens) must not keep the colors of the other one.
    """

    def __init__(self, widget: QWidget, plain: str, kind: str, look: Optional[Look] = None) -> None:
        self.widget = widget
        self.plain = plain
        self.kind = kind
        self.look = look


class ChangeCard(QFrame):
    """A change: ✓ or ✗, what, the expression, what was kept, and Undo while it is the last step."""

    def __init__(self, text: str, succeeded: bool, detail: str, count: str, palette: dict, dark: bool,
                 on_undo: Callable[[], None], parent: QWidget, strong: Sequence[str] = ()) -> None:
        super().__init__(parent)
        self.setObjectName("frame_agent_card")
        self._succeeded = succeeded
        self._mark = mark = _plain_label("✓" if succeeded else "✗", self, wrap=False)
        mark.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._title = title = _plain_label(text, self)
        if strong:  # the layer names in bold, the rest escaped: a name can hold anything
            title.setTextFormat(Qt.TextFormat.RichText)
            title.setText(strong_markup(text, strong))
        self._muted: List[QLabel] = []
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        column.addWidget(title)
        if detail:
            expression = ElidedLabel(detail, self)
            mono = QFont("monospace")
            mono.setStyleHint(QFont.StyleHint.Monospace)
            expression.setFont(mono)
            self._muted.append(expression)
            column.addWidget(expression)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        row.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(column, 1)
        if count:
            kept = _plain_label(count, self, wrap=False)
            self._muted.append(kept)
            row.addWidget(kept, 0, Qt.AlignmentFlag.AlignTop)
        self.undo_button = QPushButton(_tr("Undo"), self)
        self.undo_button.setObjectName("pushButton_agent_card_undo")
        self.undo_button.setFlat(True)
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.clicked.connect(on_undo)
        self.undo_button.setVisible(False)
        row.addWidget(self.undo_button, 0, Qt.AlignmentFlag.AlignTop)
        self.restyle(palette, dark)

    def restyle(self, palette: dict, dark: bool) -> None:
        """The colors of the theme; every text has its own, so none falls back on a palette of the other theme."""
        _sheet(self, f"QFrame#frame_agent_card {{ background: {palette['fm_group']}; border: 1px solid"
                     f" {palette['fm_group_border']}; border-radius: 6px; }} QFrame#frame_agent_card QLabel"
                     " { background: transparent; border: none; padding: 0px; }")
        mark = DONE_COLOR["dark" if dark else "light"] if self._succeeded else palette["fm_danger"]
        _sheet(self._mark, f"color: {mark}; font-weight: 600;")
        _sheet(self._title, f"font-size: 12px; color: {palette['fm_text'] if self._succeeded else palette['fm_danger']};")
        for label in self._muted:
            _sheet(label, f"font-size: 11px; color: {palette['fm_text_muted']};")
        _sheet(self.undo_button, f"QPushButton {{ color: {palette['fm_accent']}; background: none; border: none;"
                                 " padding: 0; font-size: 11px; min-height: 0; } QPushButton:hover"
                                 " { text-decoration: underline; }")


class AgentThread(QScrollArea):
    """The thread: bubbles, cards, steps and text, oldest first; it follows the end while the reader is there."""

    def __init__(self, palette_of: Callable[[], dict], is_dark: Callable[[], bool], on_undo: Callable[[], None],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("scrollArea_agent_thread")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._palette_of = palette_of
        self._is_dark = is_dark
        self._on_undo = on_undo
        self._items: List[_Item] = []
        self._answer: Optional[_Item] = None
        self._answer_raw = ""
        self._step_cards: List[ChangeCard] = []  # the cards of the last step of the history
        self._undo_possible = False
        self._content = QWidget(self)
        self._content.setObjectName("widget_agent_thread")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)
        self._hint = QLabel(self._content)
        self._hint.setObjectName("label_agent_thread_hint")
        self._hint.setTextFormat(Qt.TextFormat.PlainText)
        self._hint.setWordWrap(True)
        self._hint.setVisible(False)
        self._layout.addWidget(self._hint)
        self.setWidget(self._content)
        # The scroll area sizes its widget from the size hints, which a wrapped label computes for a width of its
        # own: at the real width, the labels need more height than that. The content asks for it (see _fit_height).
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(0)
        self._fit_timer.timeout.connect(self._fit_height)
        # The answer arrives in fragments of a few characters: drawing it again for each one lays out all its text
        # each time, which grows with the answer. The fragments that come meanwhile are drawn at once (add_text).
        self._answer_timer = QTimer(self)
        self._answer_timer.setSingleShot(True)
        self._answer_timer.timeout.connect(self._show_answer)
        # Timers of the thread, not QTimer.singleShot: they never fire for a thread deleted meanwhile (unloading).
        self._end_timer = QTimer(self)
        self._end_timer.setSingleShot(True)
        self._end_timer.setInterval(0)
        self._end_timer.timeout.connect(self._scroll_to_end)
        self.refresh_look()

    # --- what the panel asks ---------------------------------------------------------

    def refresh_look(self) -> None:
        palette = self._palette_of()
        sheet = (
            f"QScrollArea#scrollArea_agent_thread {{ background: {palette['fm_list']}; border: 1px solid "
            f"{palette['fm_group_border']}; border-radius: 6px; }}"
            # The frame alone paints the background: a viewport or a content with one of its own is a square laid
            # over the rounded corners.
            " QScrollArea#scrollArea_agent_thread > QWidget#qt_scrollarea_viewport,"
            " QWidget#widget_agent_thread { background: transparent; }"
            " QWidget#widget_agent_thread QLabel { padding: 0px; }")
        _sheet(self, sheet)
        dark = self._is_dark()
        for item in self._items:
            if item.look is not None:
                try:
                    item.look(palette, dark)
                except RuntimeError:  # dropped meanwhile
                    pass
        _sheet(self._hint, f"font-size: 11px; color: {palette['fm_text_muted']};")

    def is_empty(self) -> bool:
        return not self._items

    def toPlainText(self) -> str:  # noqa: N802 - the name of the QTextEdit it replaced
        return "\n".join(item.plain for item in self._items)

    def clear(self) -> None:
        for item in self._items:
            self._drop(item.widget)
        self._items = []
        self._answer_timer.stop()
        self._answer = None
        self._answer_raw = ""
        self._step_cards = []
        self._fit_timer.start()

    def end_answer(self) -> None:
        if self._answer_timer.isActive():  # the answer as it ended, before what follows it
            self._show_answer()
        self._answer = None
        self._answer_raw = ""

    def add_user(self, text: str) -> None:
        row = QWidget(self._content)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        bubble = _plain_label(text, row)
        bubble.setObjectName("label_agent_request")
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        def look(palette: dict, _dark: bool) -> None:
            _sheet(bubble, f"QLabel#label_agent_request {{ background: {palette['fm_active']}; color: {palette['fm_text']};"
                           " border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom-left-radius:"
                           " 10px; border-bottom-right-radius: 2px; padding: 6px 10px; }")
        layout.addWidget(bubble)
        self._fit_bubble(bubble)
        self._step_cards = []  # a new turn: the cards of the previous one are no longer its last step
        self._refresh_undo()
        self._append(_Item(row, text, "user", look))
        self.end_answer()

    def begin_step(self) -> None:
        """A change made outside a turn of the chat (another application) starts a step of its own."""
        self._step_cards = []
        self._refresh_undo()

    def add_card(self, text: str, succeeded: bool, detail: str, count: str, strong: Sequence[str] = ()) -> None:
        card = ChangeCard(text, succeeded, detail, count, self._palette_of(), self._is_dark(), self._on_undo,
                          self._content, strong)
        if succeeded:
            self._step_cards.append(card)
        mark = "✓" if succeeded else "✗"
        plain = f"{mark} {text}" + (f"  ·  {count}" if count else "") + (f"\n   {detail}" if detail else "")
        self._append(_Item(card, plain, "card", card.restyle))
        self._refresh_undo()
        self.end_answer()

    def add_note(self, text: str) -> None:
        label = _plain_label(text, self._content)
        self._append(_Item(label, text, "note",
                           lambda palette, _dark: _sheet(label, f"font-size: 12px; color: {palette['fm_text_muted']};")))
        self.end_answer()

    def add_error(self, title: str, detail: str, action: str = "", on_action: Optional[Callable[[], None]] = None) -> None:
        """A request that failed: what went wrong, what to do, and a button to do it."""
        card = QFrame(self._content)
        card.setObjectName("frame_agent_error")
        mark = _plain_label("!", card, wrap=False)
        mark.setObjectName("label_agent_error_mark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(18, 18)
        heading = _plain_label(title, card)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        column.addWidget(heading)
        text = None
        if detail:
            text = _plain_label(detail, card)
            column.addWidget(text)
        button = None
        if action and on_action is not None:
            button = QPushButton(action, card)
            button.setObjectName("pushButton_agent_error_action")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(on_action)
            column.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(10)
        row.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(column, 1)

        def look(palette: dict, dark: bool) -> None:
            background, border, strong = ERROR_COLORS["dark" if dark else "light"]
            _sheet(card, f"QFrame#frame_agent_error {{ background: {background}; border: 1px solid {border};"
                         " border-radius: 6px; } QFrame#frame_agent_error QLabel { background: transparent;"
                         " border: none; padding: 0px; }")
            _sheet(mark, f"QLabel#label_agent_error_mark {{ color: {palette['fm_danger']}; border: 2px solid"
                         f" {palette['fm_danger']}; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 0; }}")
            _sheet(heading, f"font-weight: 600; color: {strong};")
            if text is not None:
                _sheet(text, f"font-size: 12px; color: {palette['fm_text_muted']};")
            if button is not None:
                _sheet(button, f"QPushButton#pushButton_agent_error_action {{ font-size: 12px; font-weight: 500;"
                               f" padding: 4px 12px; border: 1px solid {palette['fm_danger']}; border-radius: 6px;"
                               f" background: {palette['fm_list']}; color: {strong}; }}")
        self._append(_Item(card, f"! {title}" + (f"\n   {detail}" if detail else ""), "error", look))
        self.end_answer()

    def set_hint(self, text: str) -> None:
        """A muted line at the foot of the thread (while the agent works: the next request can be typed)."""
        self._hint.setText(text)
        _sheet(self._hint, f"font-size: 11px; color: {self._palette_of()['fm_text_muted']};")
        self._hint.setVisible(bool(text))
        self._fit_timer.start()

    def add_text(self, text: str) -> None:
        """More of the answer being written: one label per answer, its Markdown marks taken out.

        Drawn a moment later with the fragments that came meanwhile: within ANSWER_DELAY_MS, more as it grows (a
        tenth of a second for 4 000 characters, 0.3 s for 12 000), so that the panel keeps answering; at once when the
        answer ends.
        """
        self._answer_raw += text
        if self._answer is None:
            label = _plain_label("", self._content)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._answer = _Item(label, "", "text",
                                 lambda palette, _dark: _sheet(label, f"font-size: 13px; color: {palette['fm_text']};"))
            self._append(self._answer)
        self._answer.plain = self._answer_raw
        if not self._answer_timer.isActive():
            self._answer_timer.start(max(ANSWER_DELAY_MS, len(self._answer_raw) // ANSWER_CHARS_PER_MS))

    def _show_answer(self) -> None:
        self._answer_timer.stop()
        self._answer.widget.setText(plain_markdown(self._answer_raw).strip("\n"))
        self._fit_timer.start()
        self._follow_end()

    def add_step(self, text: str) -> None:
        """A step of the running request; the previous one is marked done."""
        self.finish_steps()
        label = _plain_label(f"◌  {text}…", self._content)
        item = _Item(label, "", "step")
        item.step_text = text  # type: ignore[attr-defined]
        item.look = lambda palette, dark: self._look_step(item, palette, dark)
        self._append(item)

    def _look_step(self, item: _Item, palette: dict, dark: bool) -> None:
        label = item.widget
        if item.kind == "step":
            _sheet(label, f"font-size: 12px; color: {palette['fm_accent']};")
            return
        succeeded = getattr(item, "step_ok", True)
        color = DONE_COLOR["dark" if dark else "light"] if succeeded else palette["fm_danger"]
        label.setTextFormat(Qt.TextFormat.RichText)  # only the mark is colored; the text is escaped
        label.setText(f'<span style="color: {color};">{"✓" if succeeded else "✗"}</span>&nbsp;&nbsp;'
                      f'{html.escape(getattr(item, "step_text", ""))}')
        _sheet(label, f"font-size: 12px; color: {palette['fm_text_muted']};")

    def finish_steps(self, succeeded: bool = True) -> None:
        palette, dark = self._palette_of(), self._is_dark()
        for item in self._items:
            if item.kind == "step":
                item.kind = "step_done"
                item.step_ok = succeeded  # type: ignore[attr-defined]
                self._look_step(item, palette, dark)

    def clear_steps(self) -> None:
        """The request is over: its steps give way to its cards and its answer."""
        for item in [item for item in self._items if item.kind in ("step", "step_done")]:
            self._drop(item.widget)
            self._items.remove(item)
        self._fit_timer.start()

    def set_undo_possible(self, possible: bool) -> bool:
        """Undo on the cards of the last step; False when no card can offer it."""
        self._undo_possible = possible
        self._refresh_undo()
        return bool(possible and self._step_cards)

    # --- inside ------------------------------------------------------------------

    @staticmethod
    def _drop(widget: QWidget) -> None:
        """Out of the thread at once (``deleteLater`` alone leaves it a child until the next event loop turn)."""
        widget.hide()
        widget.setParent(None)
        widget.deleteLater()

    def _refresh_undo(self) -> None:
        for item in self._items:
            if isinstance(item.widget, ChangeCard):
                item.widget.undo_button.setVisible(False)
        for card in self._step_cards:
            try:
                card.undo_button.setVisible(self._undo_possible)
            except RuntimeError:  # cleared meanwhile
                pass

    def _append(self, item: _Item) -> None:
        bar = self.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4
        self._items.append(item)
        if item.look is not None:
            item.look(self._palette_of(), self._is_dark())
        self._layout.insertWidget(self._layout.count() - 2, item.widget)  # above the stretch and the hint
        item.widget.ensurePolished()
        self._fit_timer.start()
        if at_end:
            self._follow_end()

    def _fit_height(self) -> None:
        """Room for every wrapped line at the width the thread has now."""
        bar = self.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4
        layout = self._content.layout()
        layout.invalidate()
        width = self.viewport().width()
        self._content.setMinimumHeight(layout.heightForWidth(width) if layout.hasHeightForWidth() else 0)
        if at_end:
            self._follow_end()

    def _follow_end(self) -> None:
        self._end_timer.start()

    def _scroll_to_end(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _fit_bubble(self, bubble: QLabel) -> None:
        bubble.setMaximumWidth(max(80, int(self.viewport().width() * BUBBLE_SHARE)))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self._fit_timer.start()
        for item in self._items:
            if item.kind == "user":
                bubble = item.widget.findChild(QLabel, "label_agent_request")
                if bubble is not None:
                    self._fit_bubble(bubble)
