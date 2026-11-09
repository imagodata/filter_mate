# -*- coding: utf-8 -*-
"""The AGENT section of the accordion: a welcome, the conversation, and one line to ask.

The conversation is a plain text document styled by character formats, on purpose: what a
model writes can repeat what it read in a layer, and rich text would load the images and
follow the links it holds. Nothing here ever parses HTML.
"""
from __future__ import annotations

import time
from typing import Tuple

from qgis.PyQt.QtCore import QCoreApplication, QEvent, QSize, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QTabWidget, QTextEdit, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core.agent.open_data import KIND_CKAN, KIND_OPENDATASOFT, KIND_WFS
from ...core.agent.providers import PRESETS
from ...core.agent.sources import (
    KIND_MCP, KIND_STAC, MAX_CUSTOM, ORIGIN_COMMUNITY, ORIGIN_LOCAL, ORIGIN_OFFICIAL, ORIGIN_USER, all_sources, custom_from_json,
    custom_to_json, make_source,
)
from ..styles.mockup_design import FONT_FAMILY, render_icon, stylesheet_is_dark, tokens

PANEL_NAME = "AGENT"
THREAD_MIN_HEIGHT = 60  # the dock has to stay usable on small screens
BUTTON_SIZE = 26
ICON_SIZE = 16
PROGRESS_HEIGHT = 3
STATUS_MAX_HEIGHT = 48
_WELCOME_PAGE, _THREAD_PAGE, _HISTORY_PAGE = 0, 1, 2
_TURN_ROLE = Qt.ItemDataRole.UserRole

PRESET_LABELS = {"anthropic": "Claude (Anthropic)", "mistral": "Mistral", "openai": "OpenAI", "ollama": "Ollama (local)"}
# Only what can be named without going stale: the user can type any model.
MODEL_SUGGESTIONS = {"anthropic": ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")}
EXAMPLES = (
    "Which layers are in this project?",
    "Keep the buildings taller than 15 m",
    "Filter the roads inside the selected feature",
)


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


class AgentInput(QLineEdit):
    """One line, with the previous requests on the arrows and Escape to stop."""

    escape_pressed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history = []
        self._position = 0
        self._draft = ""

    def forget(self) -> None:
        self._history, self._position, self._draft = [], 0, ""

    def remember(self, text: str) -> None:
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._position = len(self._history)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt name
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
        elif key == Qt.Key.Key_Up and self._position > 0:
            if self._position == len(self._history):
                self._draft = self.text()
            self._position -= 1
            self.setText(self._history[self._position])
        elif key == Qt.Key.Key_Down and self._position < len(self._history):
            self._position += 1
            self.setText(self._history[self._position] if self._position < len(self._history) else self._draft)
        else:
            super().keyPressEvent(event)


def ask_plain(parent, title: str, text: str) -> bool:
    """A yes / no question whose text is never read as rich text: it quotes what a model wrote."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    answer = box.exec()
    box.deleteLater()
    return answer == QMessageBox.StandardButton.Yes


class AgentPanel(QFrame):
    """Widgets only: the controller decides what happens."""

    send_requested = pyqtSignal(str)
    stop_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    new_conversation_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    history_requested = pyqtSignal()
    resend_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(PANEL_NAME)
        self._working = False
        self._in_answer = False
        self._ready = False
        self.setStyleSheet(
            # Its own sheet wins over the rules of the accordion, which size every tool button as a section tab.
            f"QToolButton {{ min-width: {BUTTON_SIZE}px; max-width: {BUTTON_SIZE}px; min-height: {BUTTON_SIZE}px; "
            f"max-height: {BUTTON_SIZE}px; padding: 0; margin: 0; }}"
            "QToolButton::menu-indicator { image: none; }"
            f"QTextEdit, QListWidget {{ font-family: '{FONT_FAMILY}', sans-serif; }}"
            "QPushButton#pushButton_agent_example { text-align: left; padding: 4px 8px; }")

        self.stack = QStackedWidget(self)
        welcome = QScrollArea(self)  # it must not make the section taller than a small screen allows
        welcome.setFrameShape(QFrame.Shape.NoFrame)
        welcome.setWidgetResizable(True)
        welcome.setMinimumHeight(THREAD_MIN_HEIGHT)
        welcome.setWidget(self._build_welcome())
        self.stack.addWidget(welcome)
        self.thread = QTextEdit(self)
        self.thread.setObjectName("textEdit_agent_thread")
        self.thread.setReadOnly(True)
        self.thread.setAcceptRichText(False)  # nothing is pasted or parsed as HTML; text is inserted as text
        self.thread.setMinimumHeight(THREAD_MIN_HEIGHT)
        self.stack.addWidget(self.thread)
        self.stack.addWidget(self._build_history())
        # The accordion gives the section a fixed height: the pages take what is left above the input, never
        # more (a stacked widget otherwise asks for the tallest of its pages, the hidden ones included).
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.stack.setMinimumHeight(THREAD_MIN_HEIGHT)

        self.progress = QProgressBar(self)
        self.progress.setObjectName("progressBar_agent")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(PROGRESS_HEIGHT)
        self.progress.setVisible(False)

        self.status = QLabel(self)
        self.status.setObjectName("label_agent_status")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)  # it can quote a provider or a model
        # A wrapping label reports a tall minimum at its narrowest: it must not push the input out of the section.
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.status.setMaximumHeight(STATUS_MAX_HEIGHT)
        self.fix_button = QPushButton(_tr("Open the settings"), self)
        self.fix_button.setObjectName("pushButton_agent_fix")
        self.fix_button.setVisible(False)
        self.fix_button.clicked.connect(self.settings_requested)
        self.undo_button = QPushButton(_tr("Undo this turn"), self)
        self.undo_button.setObjectName("pushButton_agent_undo")
        self.undo_button.clicked.connect(self.undo_requested)
        self.set_can_undo(False)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(4)
        actions.addWidget(self.status, 1)
        actions.addWidget(self.fix_button)
        actions.addWidget(self.undo_button)

        self.input = AgentInput(self)
        self.input.setObjectName("lineEdit_agent_input")
        self.input.setPlaceholderText(_tr("Ask the agent to filter your layers"))
        self.input.returnPressed.connect(self._on_send)
        self.input.escape_pressed.connect(self._on_escape)

        self.send_button = QToolButton(self)
        self.send_button.setObjectName("toolButton_agent_send")
        self.send_button.setAutoRaise(True)
        self.send_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.send_button.clicked.connect(self._on_send_or_stop)

        self.more_button = QToolButton(self)
        self.more_button.setObjectName("toolButton_agent_more")
        self.more_button.setAutoRaise(True)
        self.more_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.more_button.setToolTip(_tr("More"))
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.more_button)
        self.history_action = menu.addAction(_tr("History…"))
        self.history_action.triggered.connect(self.history_requested)
        self.new_action = menu.addAction(_tr("New conversation"))
        self.new_action.triggered.connect(self.new_conversation_requested)
        self.settings_action = menu.addAction(_tr("Agent settings"))
        self.settings_action.triggered.connect(self.settings_requested)
        self.more_button.setMenu(menu)

        ask = QHBoxLayout()
        ask.setContentsMargins(0, 0, 0, 0)
        ask.setSpacing(2)
        ask.addWidget(self.input, 1)
        ask.addWidget(self.send_button)
        ask.addWidget(self.more_button)

        self.destination = QLabel(self)
        self.destination.setObjectName("label_agent_destination")
        self.destination.setTextFormat(Qt.TextFormat.PlainText)
        self.destination.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.destination.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.progress)
        layout.addLayout(actions)
        layout.addLayout(ask)
        layout.addWidget(self.destination)
        self.set_working(False)
        self._refresh_look()

    def _build_history(self) -> QWidget:
        """The turns of this project: what was asked, what changed, applied or undone."""
        page = QWidget(self)
        self.back_button = QToolButton(page)
        self.back_button.setObjectName("toolButton_agent_back")
        self.back_button.setAutoRaise(True)
        self.back_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.back_button.setToolTip(_tr("Back to the conversation"))
        self.back_button.clicked.connect(self.show_thread)
        title = QLabel(_tr("History"), page)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        self.history_count = QLabel(page)
        self.history_count.setObjectName("label_agent_history_count")
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        header.addWidget(self.back_button)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.history_count)

        self.history_list = QListWidget(page)
        self.history_list.setObjectName("listWidget_agent_history")
        self.history_list.setWordWrap(True)
        self.history_list.itemSelectionChanged.connect(self._on_turn_selected)

        self.history_undo_button = QPushButton(_tr("Undo the last"), page)
        self.history_undo_button.setObjectName("pushButton_agent_history_undo")
        self.history_undo_button.clicked.connect(self.undo_requested)
        self.history_redo_button = QPushButton(_tr("Redo"), page)
        self.history_redo_button.setObjectName("pushButton_agent_history_redo")
        self.history_redo_button.clicked.connect(self.redo_requested)
        self.resend_button = QPushButton(_tr("Send again"), page)
        self.resend_button.setObjectName("pushButton_agent_resend")
        self.resend_button.setEnabled(False)
        self.resend_button.clicked.connect(self._resend_selected)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)
        buttons.addWidget(self.history_undo_button)
        buttons.addWidget(self.history_redo_button)
        buttons.addStretch(1)
        buttons.addWidget(self.resend_button)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(self.history_list, 1)
        layout.addLayout(buttons)
        return page

    def show_history(self) -> None:
        self.stack.setCurrentIndex(_HISTORY_PAGE)

    def show_thread(self) -> None:
        self.stack.setCurrentIndex(_THREAD_PAGE if not self.thread.document().isEmpty() else _WELCOME_PAGE)

    @property
    def history_shown(self) -> bool:
        return self.stack.currentIndex() == _HISTORY_PAGE

    def set_history(self, turns, can_undo: bool, can_redo: bool) -> None:
        """``turns``: dicts with time, request, layers, applied; oldest first."""
        palette = tokens(self._dark())
        self.history_list.clear()
        for turn in turns:
            when = time.strftime("%H:%M", time.localtime(turn.get("time") or 0))
            layers = ", ".join(turn.get("layers") or ()) or _tr("no change")
            state = _tr("applied") if turn.get("applied") else _tr("undone")
            item = QListWidgetItem(f"{when}  {turn.get('request') or _tr('(no request)')}\n{layers} · {state}")
            item.setData(_TURN_ROLE, turn.get("request") or "")
            if not turn.get("applied"):
                item.setForeground(QColor(palette["fm_text_muted"]))
            self.history_list.addItem(item)
        self.history_list.scrollToBottom()
        self.history_count.setText(_tr("{} turn(s)").format(len(turns)))
        self.history_count.setStyleSheet(f"color: {palette['fm_text_muted']};")
        self.history_undo_button.setEnabled(can_undo and not self._working)
        self.history_redo_button.setEnabled(can_redo and not self._working)
        self._on_turn_selected()

    def _on_turn_selected(self) -> None:
        self.resend_button.setEnabled(bool(self.history_list.selectedItems()) and not self._working)

    def _resend_selected(self) -> None:
        items = self.history_list.selectedItems()
        if items and not self._working:
            self.resend_requested.emit(str(items[0].data(_TURN_ROLE) or ""))

    def _build_welcome(self) -> QWidget:
        page = QWidget(self)
        self.welcome_title = QLabel(page)
        self.welcome_title.setObjectName("label_agent_welcome")
        self.welcome_title.setWordWrap(True)
        font = self.welcome_title.font()
        font.setBold(True)
        self.welcome_title.setFont(font)
        self.welcome_text = QLabel(page)
        self.welcome_text.setWordWrap(True)
        self.configure_button = QPushButton(_tr("Set up the agent"), page)
        self.configure_button.setObjectName("pushButton_agent_configure")
        self.configure_button.clicked.connect(self.settings_requested)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.welcome_title)
        layout.addWidget(self.welcome_text)
        layout.addWidget(self.configure_button)
        self.example_buttons = []
        for example in EXAMPLES:
            text = _tr(example)
            button = QPushButton(text, page)
            button.setObjectName("pushButton_agent_example")
            button.clicked.connect(lambda _checked=False, value=text: self.use_example(value))
            layout.addWidget(button)
            self.example_buttons.append(button)
        layout.addStretch(1)
        self.set_ready(False)
        return page

    # --- look -----------------------------------------------------------------

    def _dark(self) -> bool:
        dark = stylesheet_is_dark(self)
        if dark is None:
            dark = self.palette().window().color().lightness() < 128
        return bool(dark)

    def _refresh_look(self) -> None:
        """Icons and colors of the current theme."""
        dark = self._dark()
        muted = tokens(dark)["fm_text_muted"]
        self.destination.setStyleSheet(f"color: {muted};")
        self.welcome_text.setStyleSheet(f"color: {muted};")
        send = render_icon("agent_stop" if self._working else "agent_send", dark)
        if send is not None:
            self.send_button.setIcon(send)
        more = render_icon("more", dark)
        if more is not None:
            self.more_button.setIcon(more)
        back = render_icon("undo", dark)
        if back is not None:
            self.back_button.setIcon(back)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange) and hasattr(self, "more_button"):
            self._refresh_look()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        self._refresh_look()
        self.input.setFocus()

    # --- state ----------------------------------------------------------------

    def set_ready(self, ready: bool, destination: str = "") -> None:
        """Whether a provider is set up; ``destination`` says where the requests go."""
        self._ready = ready
        if ready:
            self.welcome_title.setText(_tr("What do you want to filter?"))
            self.welcome_text.setText(_tr("Describe it in your own words. Each filter can be undone."))
        else:
            self.welcome_title.setText(_tr("Filter your layers from a sentence"))
            self.welcome_text.setText(_tr("Connect an AI provider to start. Nothing is sent before you agree."))
        self.configure_button.setVisible(not ready)
        for button in self.example_buttons if hasattr(self, "example_buttons") else ():
            button.setVisible(ready)
        if hasattr(self, "destination"):
            self.destination.setText(_tr("Sent to: {}").format(destination) if ready and destination else "")
            self.destination.setVisible(bool(ready and destination))

    def use_example(self, text: str) -> None:
        self.input.setText(text)
        self.input.setFocus()

    def set_working(self, working: bool) -> None:
        """While the agent works the next request can be typed, and the button stops it."""
        self._working = working
        self.progress.setVisible(working)
        self.more_button.setEnabled(not working)
        self.history_undo_button.setEnabled(self.history_undo_button.isEnabled() and not working)
        self.history_redo_button.setEnabled(self.history_redo_button.isEnabled() and not working)
        self._on_turn_selected()
        self.send_button.setToolTip(_tr("Stop (Esc)") if working else _tr("Send (Enter)"))
        self._refresh_look()

    def set_can_undo(self, possible: bool) -> None:
        self.undo_button.setEnabled(possible)
        self.undo_button.setVisible(possible)

    def set_status(self, text: str, error: bool = False, offer_settings: bool = False) -> None:
        danger = tokens(self._dark())["fm_danger"]
        self.status.setStyleSheet(f"color: {danger};" if error else "")
        self.status.setText(text)
        self.fix_button.setVisible(offer_settings)

    def _on_send(self) -> None:
        text = self.input.text().strip()
        if text and not self._working:
            self.send_requested.emit(text)

    def _on_send_or_stop(self) -> None:
        if self._working:
            self.stop_requested.emit()
        else:
            self._on_send()

    def _on_escape(self) -> None:
        if self._working:
            self.stop_requested.emit()

    def clear_input(self) -> None:
        self.input.clear()

    def clear_thread(self) -> None:
        self.thread.clear()
        self._in_answer = False
        self.set_status("")
        self.stack.setCurrentIndex(_WELCOME_PAGE)

    def end_answer(self) -> None:
        """What comes next starts on its own line."""
        self._in_answer = False

    # --- the conversation -------------------------------------------------------

    def _write(self, text: str, new_block: bool, color: str = "", bold: bool = False, background: str = "",
               right: bool = False) -> None:
        """Always through ``insertText``: the text is never interpreted."""
        if not self.history_shown:
            self.stack.setCurrentIndex(_THREAD_PAGE)
        bar = self.thread.verticalScrollBar()
        stick = bar.value() >= bar.maximum()
        cursor = QTextCursor(self.thread.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if new_block:
            if not self.thread.document().isEmpty():
                cursor.insertBlock()
            block = QTextBlockFormat()
            block.setTopMargin(4)
            if background:
                block.setBackground(QColor(background))
            if right:
                block.setAlignment(Qt.AlignmentFlag.AlignRight)
            cursor.setBlockFormat(block)
        characters = QTextCharFormat()
        if color:
            characters.setForeground(QColor(color))
        if bold:
            font = QFont()
            font.setBold(True)
            characters.setFont(font)
        cursor.insertText(text, characters)
        if stick:
            bar.setValue(bar.maximum())

    def add_user(self, text: str) -> None:
        """A request of the user, on a tinted band, on the right."""
        self.input.remember(text)
        self._write(text, True, bold=True, background=tokens(self._dark())["fm_active"], right=True)
        self._in_answer = False

    def add_action(self, text: str, succeeded: bool = True, detail: str = "", count: str = "") -> None:
        """Something the agent changed, or failed to change; ``count`` is what it kept (``12 / 586``)."""
        palette = tokens(self._dark())
        mark = "✓" if succeeded else "✗"
        line = f"{mark} {text}" + (f"  ·  {count}" if count else "")
        self._write(line, True, color=palette["fm_text_muted"] if succeeded else palette["fm_danger"])
        if detail:
            self._write(f"   {detail}", True, color=palette["fm_text_muted"])
        self._in_answer = False

    def add_note(self, text: str) -> None:
        """A remark of the panel itself, muted."""
        self._write(text, True, color=tokens(self._dark())["fm_text_muted"])
        self._in_answer = False

    def add_text(self, text: str) -> None:
        """More of the answer being written."""
        self._write(text, not self._in_answer)
        self._in_answer = True


class AgentSettingsDialog(QDialog):
    """Provider, model, key and what may leave this machine."""

    def __init__(self, values, target_of, parent=None, tester=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_tr("FilterMate agent"))
        self._tester = tester
        self._values = values
        self._target_of = target_of
        self.forget_key = False
        self.preset = QComboBox(self)
        for name in PRESETS:
            self.preset.addItem(PRESET_LABELS.get(name, name), name)
        self.preset.setCurrentIndex(max(self.preset.findData(values.preset), 0))
        self.model = QComboBox(self)
        self.model.setEditable(True)
        self.base_url = QLineEdit(values.base_url, self)
        self.key_label = QLabel(_tr("API key"), self)
        self.key = QLineEdit(self)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.forget_button = QPushButton(_tr("Remove the stored key"), self)
        self.forget_button.setObjectName("pushButton_agent_forget_key")
        self.forget_button.clicked.connect(self._on_forget)
        self.send_values = QCheckBox(_tr("Allow attribute values to be sent"), self)
        self.send_values.setChecked(values.send_values)
        notice = QLabel(_tr(
            "The agent sends your request, the names of your layers and fields, your filter expressions and the "
            "results of its tools to the provider chosen here, under that provider's terms. Without the option "
            "below, the agent does not read the values of your fields; values already written in your filters and "
            "favorites are still sent. The conversation is kept on this computer for each project, until you start "
            "a new one."), self)
        notice.setWordWrap(True)
        self.consent = QCheckBox(_tr("I agree to send this data to this provider"), self)
        self.preset.currentIndexChanged.connect(self._on_preset)
        self.base_url.textChanged.connect(self._on_destination)
        self._on_preset()
        self.model.setEditText(values.model)

        form = QFormLayout()
        form.addRow(_tr("Provider"), self.preset)
        form.addRow(_tr("Model"), self.model)
        form.addRow(self.key_label, self.key)
        form.addRow("", self.forget_button)
        form.addRow(_tr("Address"), self.base_url)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        general = QWidget(self)
        general_layout = QVBoxLayout(general)
        general_layout.addLayout(form)
        general_layout.addWidget(notice)
        general_layout.addWidget(self.send_values)
        general_layout.addWidget(self.consent)
        general_layout.addStretch(1)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(general, _tr("Provider"))
        self.tabs.addTab(self._build_sources(values), _tr("Sources"))
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

    def _build_sources(self, values) -> QWidget:
        """Platforms and connectors, each one the user's choice: nothing is on by default."""
        self._custom = custom_from_json(values.custom_sources)
        page = QWidget(self)
        hint = QLabel(_tr("The agent can search the sources ticked here. Your searches, and what the agent passes to a "
                          "connector, are sent to them; a layer added from them is read from their servers."), page)
        hint.setWordWrap(True)
        self.sources_tree = QTreeWidget(page)
        self.sources_tree.setObjectName("treeWidget_agent_sources")
        self.sources_tree.setHeaderHidden(True)
        self.sources_tree.setRootIsDecorated(False)
        self.sources_tree.currentItemChanged.connect(lambda *_: self._on_source_selected())
        self.test_button = QPushButton(_tr("Test"), page)
        self.test_button.clicked.connect(self._on_test_source)
        self.remove_button = QPushButton(_tr("Remove"), page)
        self.remove_button.clicked.connect(self._on_remove_source)
        self.source_result = QLabel(page)
        self.source_result.setTextFormat(Qt.TextFormat.PlainText)
        self.source_result.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.source_result, 1)
        row.addWidget(self.test_button)
        row.addWidget(self.remove_button)
        self.new_address = QLineEdit(page)
        self.new_address.setPlaceholderText(_tr("https://... or a portal address"))
        self.new_kind = QComboBox(page)
        for kind, label in ((KIND_MCP, _tr("MCP connector")), (KIND_OPENDATASOFT, "Opendatasoft"), (KIND_CKAN, "CKAN"),
                            (KIND_WFS, "WFS"), (KIND_STAC, "STAC")):
            self.new_kind.addItem(label, kind)
        self.add_button = QPushButton(_tr("Add"), page)
        self.add_button.clicked.connect(self._on_add_source)
        add_row = QHBoxLayout()
        add_row.addWidget(self.new_address, 1)
        add_row.addWidget(self.new_kind)
        add_row.addWidget(self.add_button)
        layout = QVBoxLayout(page)
        layout.addWidget(hint)
        layout.addWidget(self.sources_tree, 1)
        layout.addLayout(row)
        layout.addLayout(add_row)
        self._fill_sources(set(values.enabled_sources))
        return page

    def _source_item(self, parent, source, checked: bool) -> None:
        origin = {ORIGIN_OFFICIAL: _tr("official"), ORIGIN_COMMUNITY: _tr("community"), ORIGIN_LOCAL: _tr("this computer"),
                  ORIGIN_USER: _tr("added by you")}.get(source.origin, "")
        item = QTreeWidgetItem(parent, [f"{source.title}  ·  {origin}"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setData(0, _TURN_ROLE, source.id)
        item.setToolTip(0, f"{source.note}\n{source.address}".strip())

    def _fill_sources(self, enabled_ids) -> None:
        self.sources_tree.clear()
        groups = ((_tr("Open data platforms"), lambda source: source.kind not in (KIND_MCP, KIND_STAC)),
                  (_tr("Satellite imagery"), lambda source: source.kind == KIND_STAC),
                  (_tr("MCP connectors"), lambda source: source.kind == KIND_MCP))
        for title, belongs in groups:
            group = QTreeWidgetItem(self.sources_tree, [title])
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            group.setFont(0, font)
            for source in all_sources(self._custom):
                if belongs(source):
                    self._source_item(group, source, source.id in enabled_ids)
        self.sources_tree.expandAll()
        self._on_source_selected()

    def _checked_ids(self) -> Tuple[str, ...]:
        ids = []
        root = self.sources_tree.invisibleRootItem()
        for row in range(root.childCount()):
            group = root.child(row)
            for index in range(group.childCount()):
                if group.child(index).checkState(0) == Qt.CheckState.Checked:
                    ids.append(str(group.child(index).data(0, _TURN_ROLE)))
        return tuple(ids)

    def _selected_source(self):
        item = self.sources_tree.currentItem()
        identifier = item.data(0, _TURN_ROLE) if item is not None else None
        return next((source for source in all_sources(self._custom) if source.id == identifier), None)

    def _on_source_selected(self) -> None:
        source = self._selected_source()
        self.test_button.setEnabled(source is not None and self._tester is not None)
        self.remove_button.setEnabled(source is not None and source in self._custom)
        self.source_result.setText(source.note if source is not None else "")

    def _on_test_source(self) -> None:
        source = self._selected_source()
        if source is not None and self._tester is not None:
            self.source_result.setText(_tr("Testing…"))
            QCoreApplication.processEvents()
            self.source_result.setText(self._tester(source))

    def _on_add_source(self) -> None:
        try:
            source = make_source(self.new_address.text(), self.new_kind.currentData())
        except ValueError as exc:
            self.source_result.setText(str(exc))
            return
        if source.id not in [other.id for other in all_sources(self._custom)]:
            if len(self._custom) >= MAX_CUSTOM:
                self.source_result.setText(_tr("Too many sources added: remove one first."))
                return
            self._custom.append(source)
        checked = set(self._checked_ids()) | {source.id}
        self.new_address.clear()
        self._fill_sources(checked)

    def _on_remove_source(self) -> None:
        source = self._selected_source()
        if source is not None and source in self._custom:
            self._custom.remove(source)
            self._fill_sources(set(self._checked_ids()) - {source.id})

    def chosen_sources(self) -> Tuple[str, ...]:
        return self._checked_ids()

    def chosen_custom_sources(self) -> str:
        return custom_to_json(self._custom)

    def _on_preset(self, _index: int = 0) -> None:
        """What depends on the provider: its models, its address, whether it needs a key."""
        name = self.preset.currentData()
        typed = self.model.currentText()
        self.model.clear()
        self.model.addItems(MODEL_SUGGESTIONS.get(name, ()))
        self.model.setEditText(typed if name not in MODEL_SUGGESTIONS or typed else "")
        self.base_url.setPlaceholderText(PRESETS[name][1])
        local = name == "ollama"
        self.key_label.setVisible(not local)
        self.key.setVisible(not local)
        self._on_destination()

    def _on_destination(self, _text: str = "") -> None:
        """A key and a consent are for one server: another one starts without them."""
        target = self.chosen_target()
        stored = bool(self._values.authcfg) and self._values.key_target == target and not self.forget_key
        self.key.setPlaceholderText(_tr("Stored: leave empty to keep it") if stored else "")
        self.forget_button.setVisible(stored and self.key.isVisibleTo(self))
        self.consent.setChecked(self._values.consent and self._values.consent_target == target)

    def _on_forget(self) -> None:
        self.forget_key = True
        self._on_destination()

    def chosen_target(self) -> str:
        return self._target_of(self.preset.currentData(), self.base_url.text())

    def chosen_preset(self) -> str:
        return self.preset.currentData()

    def chosen_model(self) -> str:
        return self.model.currentText().strip()
