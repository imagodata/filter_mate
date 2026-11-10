# -*- coding: utf-8 -*-
"""The conversation of the AGENT section, drawn as the mockup draws it.

Requests in a tinted bubble on the right, each change in a card (what, expression, kept / total, Undo), the
steps of a request while it runs, the answer as text. Every label is plain text: what a model writes can
repeat what it read in a layer, and nothing of it is ever interpreted as HTML.
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional

from qgis.PyQt.QtCore import QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QFont, QFontMetrics
from qgis.PyQt.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

BUBBLE_SHARE = 0.88  # of the width of the thread
DONE_COLOR = {"light": "#146a55", "dark": "#4fd1b0"}
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
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self.setText(QFontMetrics(self.font()).elidedText(self._full, Qt.TextElideMode.ElideRight, max(self.width(), 10)))


class _Item:
    """One line of the thread, and what it says in plain text."""

    def __init__(self, widget: QWidget, plain: str, kind: str) -> None:
        self.widget = widget
        self.plain = plain
        self.kind = kind


class ChangeCard(QFrame):
    """A change: ✓ or ✗, what, the expression, what was kept, and Undo while it is the last step."""

    def __init__(self, text: str, succeeded: bool, detail: str, count: str, palette: dict, dark: bool,
                 on_undo: Callable[[], None], parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("frame_agent_card")
        self.setStyleSheet(
            f"QFrame#frame_agent_card {{ background: {palette['fm_group']}; border: 1px solid {palette['fm_group_border']};"
            f" border-radius: 6px; }} QFrame#frame_agent_card QLabel {{ background: transparent; border: none; }}")
        mark = _plain_label("✓" if succeeded else "✗", self, wrap=False)
        color = DONE_COLOR["dark" if dark else "light"] if succeeded else palette["fm_danger"]
        mark.setStyleSheet(f"color: {color}; font-weight: 600;")
        mark.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = _plain_label(text, self)
        title.setStyleSheet("font-size: 12px;" if succeeded else f"font-size: 12px; color: {palette['fm_danger']};")
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        column.addWidget(title)
        if detail:
            expression = ElidedLabel(detail, self)
            mono = QFont("monospace")
            mono.setStyleHint(QFont.StyleHint.Monospace)
            expression.setFont(mono)
            expression.setStyleSheet(f"font-size: 11px; color: {palette['fm_text_muted']};")
            column.addWidget(expression)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        row.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(column, 1)
        if count:
            kept = _plain_label(count, self, wrap=False)
            kept.setStyleSheet(f"font-size: 11px; color: {palette['fm_text_muted']};")
            row.addWidget(kept, 0, Qt.AlignmentFlag.AlignTop)
        self.undo_button = QPushButton(_tr("Undo"), self)
        self.undo_button.setObjectName("pushButton_agent_card_undo")
        self.undo_button.setFlat(True)
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.setStyleSheet(
            f"QPushButton {{ color: {palette['fm_accent']}; background: none; border: none; padding: 0;"
            f" font-size: 11px; min-height: 0; }} QPushButton:hover {{ text-decoration: underline; }}")
        self.undo_button.clicked.connect(on_undo)
        self.undo_button.setVisible(False)
        row.addWidget(self.undo_button, 0, Qt.AlignmentFlag.AlignTop)


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
        self.setWidget(self._content)
        self.refresh_look()

    # --- what the panel asks ---------------------------------------------------------

    def refresh_look(self) -> None:
        palette = self._palette_of()
        sheet = (
            f"QScrollArea#scrollArea_agent_thread {{ background: {palette['fm_list']}; border: 1px solid "
            f"{palette['fm_group_border']}; border-radius: 6px; }} QWidget#widget_agent_thread {{ background: "
            f"{palette['fm_list']}; }}")
        if sheet != self.styleSheet():
            self.setStyleSheet(sheet)

    def is_empty(self) -> bool:
        return not self._items

    def toPlainText(self) -> str:  # noqa: N802 - the name of the QTextEdit it replaced
        return "\n".join(item.plain for item in self._items)

    def clear(self) -> None:
        for item in self._items:
            self._drop(item.widget)
        self._items = []
        self._answer = None
        self._answer_raw = ""
        self._step_cards = []

    def end_answer(self) -> None:
        self._answer = None
        self._answer_raw = ""

    def add_user(self, text: str) -> None:
        palette = self._palette_of()
        row = QWidget(self._content)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        bubble = _plain_label(text, row)
        bubble.setObjectName("label_agent_request")
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setStyleSheet(
            f"QLabel#label_agent_request {{ background: {palette['fm_active']}; color: {palette['fm_text']};"
            " border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom-left-radius: 10px;"
            " border-bottom-right-radius: 2px; padding: 6px 10px; }")
        layout.addWidget(bubble)
        self._fit_bubble(bubble)
        self._step_cards = []  # a new turn: the cards of the previous one are no longer its last step
        self._refresh_undo()
        self._append(_Item(row, text, "user"))
        self.end_answer()

    def begin_step(self) -> None:
        """A change made outside a turn of the chat (another application) starts a step of its own."""
        self._step_cards = []
        self._refresh_undo()

    def add_card(self, text: str, succeeded: bool, detail: str, count: str) -> None:
        card = ChangeCard(text, succeeded, detail, count, self._palette_of(), self._is_dark(), self._on_undo,
                          self._content)
        if succeeded:
            self._step_cards.append(card)
        mark = "✓" if succeeded else "✗"
        plain = f"{mark} {text}" + (f"  ·  {count}" if count else "") + (f"\n   {detail}" if detail else "")
        self._append(_Item(card, plain, "card"))
        self._refresh_undo()
        self.end_answer()

    def add_note(self, text: str) -> None:
        palette = self._palette_of()
        label = _plain_label(text, self._content)
        label.setStyleSheet(f"font-size: 12px; color: {palette['fm_text_muted']};")
        self._append(_Item(label, text, "note"))
        self.end_answer()

    def add_text(self, text: str) -> None:
        """More of the answer being written: one label per answer, its Markdown marks taken out."""
        self._answer_raw += text
        if self._answer is None:
            label = _plain_label("", self._content)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setStyleSheet("font-size: 13px;")
            self._answer = _Item(label, "", "text")
            self._append(self._answer)
        shown = plain_markdown(self._answer_raw).strip("\n")
        self._answer.widget.setText(shown)
        self._answer.plain = self._answer_raw
        self._follow_end()

    def add_step(self, text: str) -> None:
        """A step of the running request; the previous one is marked done."""
        self.finish_steps()
        palette = self._palette_of()
        label = _plain_label(f"◌  {text}…", self._content)
        label.setStyleSheet(f"font-size: 12px; color: {palette['fm_accent']};")
        self._append(_Item(label, "", "step"))

    def finish_steps(self, succeeded: bool = True) -> None:
        palette = self._palette_of()
        for item in self._items:
            if item.kind == "step":
                label = item.widget
                text = label.text().lstrip("◌ ").rstrip("…")
                label.setText(("✓  " if succeeded else "✗  ") + text)
                label.setStyleSheet(f"font-size: 12px; color: {palette['fm_text_muted']};")
                item.kind = "step_done"

    def clear_steps(self) -> None:
        """The request is over: its steps give way to its cards and its answer."""
        for item in [item for item in self._items if item.kind in ("step", "step_done")]:
            self._drop(item.widget)
            self._items.remove(item)

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
        self._layout.insertWidget(self._layout.count() - 1, item.widget)
        if at_end:
            self._follow_end()

    def _follow_end(self) -> None:
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def _fit_bubble(self, bubble: QLabel) -> None:
        bubble.setMaximumWidth(max(80, int(self.viewport().width() * BUBBLE_SHARE)))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        for item in self._items:
            if item.kind == "user":
                bubble = item.widget.findChild(QLabel, "label_agent_request")
                if bubble is not None:
                    self._fit_bubble(bubble)
