# -*- coding: utf-8 -*-
"""The AGENT section of the accordion: a welcome, the conversation, and one line to ask.

The conversation is a plain text document styled by character formats, on purpose: what a
model writes can repeat what it read in a layer, and rich text would load the images and
follow the links it holds. Nothing here ever parses HTML.
"""
from __future__ import annotations

import time
from typing import Sequence, Tuple

from qgis.PyQt.QtCore import QCoreApplication, QEvent, QSize, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu,
    QButtonGroup, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
    QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .agent_thread import DONE_COLOR, AgentThread, ElidedLabel, plain_tooltip
from .agent_widgets_strip import WidgetsStrip
from ...core.agent.mcp_server import EXTERNAL_MARK, claude_code_command, claude_desktop_config, client_config, new_token, server_url
from ...core.agent.open_data import KIND_CKAN, KIND_OPENDATASOFT, KIND_WFS
from ...core.agent.permissions import ADVISOR, AUTONOMOUS, CAREFUL, LEVELS, STANDARD, level_or_default
from ...core.agent.providers import FREE_MODEL, FREE_PRESET, PRESETS
from ...core.agent.sources import (
    KIND_MCP, KIND_STAC, MAX_CUSTOM, ORIGIN_COMMUNITY, ORIGIN_LOCAL, ORIGIN_OFFICIAL, ORIGIN_USER, all_sources, custom_from_json,
    custom_to_json, make_source,
)
from ..styles.mockup_design import FONT_FAMILY, plugin_is_dark, render_icon, tokens
from ..styles.theme_manager import OWN_STYLE_PROPERTY

PANEL_NAME = "AGENT"
INPUT_HEIGHT = 32
THREAD_MIN_HEIGHT = 60  # the dock has to stay usable on small screens
BUTTON_SIZE = 26
ICON_SIZE = 16
PROGRESS_HEIGHT = 3
STATUS_MAX_HEIGHT = 48
WELCOME_ICON_SIZE = 36
_WELCOME_PAGE, _THREAD_PAGE, _HISTORY_PAGE = 0, 1, 2
_TURN_ROLE = Qt.ItemDataRole.UserRole
_STEP_ROLE = Qt.ItemDataRole.UserRole + 1

PRESET_LABELS = {FREE_PRESET: "FilterMate (free quota)", "anthropic": "Claude (Anthropic)", "mistral": "Mistral", "openai": "OpenAI", "ollama": "Ollama (local)"}
# Only what can be named without going stale: the user can type any model.
MODEL_SUGGESTIONS = {"anthropic": ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")}


MAX_RECIPE_STEPS_SHOWN = 12  # steps listed in the menu of a recipe


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


def preset_label(name: str) -> str:
    """The name of a provider preset as the settings show it, in the language of QGIS."""
    translated = {FREE_PRESET: _tr("FilterMate (free quota)"), "ollama": _tr("Ollama (local)")}
    return translated.get(name) or PRESET_LABELS.get(name, name)


def examples() -> Tuple[str, ...]:
    """The requests offered on an empty conversation (mockup: Ready board), in the language of QGIS."""
    return (_tr("Which layers are in this project?"), _tr("Keep the buildings taller than 15 m"),
            _tr("Filter the roads inside the selected feature"), _tr("Add the municipalities from data.gouv.fr"))


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
    box.show()
    box.raise_()  # the question can come from another application, the one in front
    box.activateWindow()
    answer = box.exec()
    box.deleteLater()
    return answer == QMessageBox.StandardButton.Yes


def ask_code(parent, title: str, text: str, code: str) -> bool:
    """Yes or no on code written by a model: the whole code is shown, as plain text, and No is the default."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(720, 520)
    layout = QVBoxLayout(dialog)
    label = QLabel(dialog)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setText(text)
    view = QPlainTextEdit(dialog)
    view.setReadOnly(True)
    view.setPlainText(code)
    mono = QFont("monospace")
    mono.setStyleHint(QFont.StyleHint.Monospace)
    view.setFont(mono)
    view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No, dialog)
    buttons.button(QDialogButtonBox.StandardButton.No).setDefault(True)
    buttons.button(QDialogButtonBox.StandardButton.No).setFocus()
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(label)
    layout.addWidget(view, 1)
    layout.addWidget(buttons)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    answer = dialog.exec()
    dialog.deleteLater()
    return answer == QDialog.DialogCode.Accepted


ANSWER_NO, ANSWER_ONCE, ANSWER_CONVERSATION = "no", "once", "conversation"


def ask_with_conversation(parent, title: str, text: str) -> str:
    """Like ``ask_plain``, with a third answer: yes, and do not ask again in this conversation."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(text)
    always = box.addButton(_tr("Yes for this conversation"), QMessageBox.ButtonRole.AcceptRole)
    always.setToolTip(_tr("This action runs without asking again until you start a new conversation, open another "
                          "project or change the level of autonomy."))
    box.addButton(QMessageBox.StandardButton.Yes)
    no = box.addButton(QMessageBox.StandardButton.No)
    box.setDefaultButton(no)
    box.show()
    box.raise_()
    box.activateWindow()
    box.exec()
    clicked = box.clickedButton()
    answer = ANSWER_NO
    if clicked is always:
        answer = ANSWER_CONVERSATION
    elif clicked is not None and box.standardButton(clicked) == QMessageBox.StandardButton.Yes:
        answer = ANSWER_ONCE
    box.deleteLater()
    return answer


def level_label(level: str) -> str:
    return {
        ADVISOR: _tr("Advisor: reads and explains, changes nothing"),
        CAREFUL: _tr("Careful: asks before every change"),
        STANDARD: _tr("Standard: asks before what cannot be undone"),
        AUTONOMOUS: _tr("Autonomous: asks only before the outside world"),
    }[level_or_default(level)]


def level_short(level: str) -> str:
    """For the head of the section, next to the model."""
    return {ADVISOR: _tr("Advisor"), CAREFUL: _tr("Careful"), STANDARD: _tr("Standard"),
            AUTONOMOUS: _tr("Autonomous")}[level_or_default(level)]


def level_detail(level: str) -> str:
    return {
        ADVISOR: _tr("The agent reads your layers and answers. For a change, it tells you the steps instead of making "
                     "it."),
        CAREFUL: _tr("Moving the map, showing layers and selecting features run alone. Filters, styles, new layers, "
                     "edits and everything else are shown to you first."),
        STANDARD: _tr("Filters, styles, Processing, layouts and edits in the edit buffer run at once and are undone with "
                      "the turn. Exports, removals, deletions, the network and connectors are asked first."),
        AUTONOMOUS: _tr("Exports into the export folder, layer removals and deletions run without a question too, and "
                        "not all of them can be undone. The network, connectors and code are still asked first."),
    }[level_or_default(level)]


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
    step_undo_requested = pyqtSignal(int)
    recipe_save_requested = pyqtSignal()
    recipe_run_requested = pyqtSignal(str)
    recipe_remove_requested = pyqtSignal(str)

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
            "")

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("stackedWidget_agent")
        welcome = QScrollArea(self)  # it must not make the section taller than a small screen allows
        welcome.setObjectName("scrollArea_agent_welcome")
        welcome.setFrameShape(QFrame.Shape.NoFrame)
        welcome.setWidgetResizable(True)
        welcome.setMinimumHeight(THREAD_MIN_HEIGHT)
        welcome.setWidget(self._build_welcome())
        self.stack.addWidget(welcome)
        self.thread = AgentThread(lambda: tokens(self._dark()), self._dark, self.undo_requested.emit, self)
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
        self.status.setVisible(False)  # only while it says something: the input sits right under the thread
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
        self.input.setPlaceholderText(_tr("Ask for a filter…"))
        self.input.returnPressed.connect(self._on_send)
        self.input.escape_pressed.connect(self._on_escape)

        self.send_button = QToolButton(self)
        self.send_button.setObjectName("toolButton_agent_send")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.send_button.clicked.connect(self._on_send_or_stop)

        self.more_button = QToolButton(self)
        self.more_button.setObjectName("toolButton_agent_more")
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.more_button.setToolTip(_tr("More"))
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.more_button)
        self.history_action = menu.addAction(_tr("History…"))
        self.history_action.triggered.connect(self.history_requested)
        # Recipes: the changes of a request kept in the project, run again without the model.
        self.recipes_menu = menu.addMenu(_tr("Recipes"))
        self.recipes_menu.setObjectName("menu_agent_recipes")
        self._recipes = []
        self._can_save_recipe = False
        self.set_recipes([], False)
        self.new_action = menu.addAction(_tr("New conversation"))
        self.new_action.triggered.connect(self.new_conversation_requested)
        self.settings_action = menu.addAction(_tr("Agent settings"))
        self.settings_action.triggered.connect(self.settings_requested)
        self.more_button.setMenu(menu)

        ask = QHBoxLayout()
        ask.setContentsMargins(0, 0, 0, 0)
        ask.setSpacing(6)
        ask.addWidget(self.input, 1)
        ask.addWidget(self.send_button)
        ask.addWidget(self.more_button)

        self.destination = QLabel(self)
        self.destination.setObjectName("label_agent_destination")
        self.destination.setTextFormat(Qt.TextFormat.PlainText)
        self.destination.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.destination.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.progress)  # a thin bar under the header while the agent works (mockup)
        layout.addWidget(self.stack, 1)
        # The widgets the agent made for the user: they stay in view while the conversation scrolls.
        self.widgets_strip = WidgetsStrip(self)
        layout.addWidget(self.widgets_strip)
        layout.addLayout(actions)
        layout.addLayout(ask)
        layout.addWidget(self.destination)
        self.set_ready(False)
        self.set_working(False)
        self._refresh_look()

    def _build_history(self) -> QWidget:
        """The turns of this project: what was asked, what changed, applied or undone."""
        page = QFrame(self)
        page.setObjectName("frame_agent_history")
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
        header_bar = QWidget(page)
        header_bar.setObjectName("widget_agent_history_header")
        header = QHBoxLayout(header_bar)
        header.setContentsMargins(8, 6, 10, 6)
        header.setSpacing(8)
        header.addWidget(self.back_button)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.history_count)

        self.history_list = QListWidget(page)
        self.history_list.setObjectName("listWidget_agent_history")
        self.history_list.setWordWrap(True)
        self.history_list.setFrameShape(QFrame.Shape.NoFrame)
        self.history_list.itemSelectionChanged.connect(self._on_turn_selected)

        self.history_undo_button = QPushButton(_tr("Undo the last"), page)
        self.history_undo_button.setObjectName("pushButton_agent_history_undo")
        self.history_undo_button.clicked.connect(self.undo_requested)
        self.history_redo_button = QPushButton(_tr("Redo"), page)
        self.history_redo_button.setObjectName("pushButton_agent_history_redo")
        self.history_redo_button.clicked.connect(self.redo_requested)
        self.step_button = QPushButton(_tr("Undo back to here"), page)
        self.step_button.setObjectName("pushButton_agent_history_step")
        self.step_button.setToolTip(_tr("The layers as they were before this step of the last request"))
        self.step_button.setEnabled(False)
        self.step_button.clicked.connect(self._undo_to_selected_step)
        self.resend_button = QPushButton(_tr("Send again"), page)
        self.resend_button.setObjectName("pushButton_agent_resend")
        self.resend_button.setFlat(True)
        self.resend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_button.setEnabled(False)
        self.resend_button.clicked.connect(self._resend_selected)
        footer = QWidget(page)
        footer.setObjectName("widget_agent_history_footer")
        buttons = QHBoxLayout(footer)
        buttons.setContentsMargins(10, 8, 10, 8)
        buttons.setSpacing(6)
        buttons.addWidget(self.history_undo_button)
        buttons.addWidget(self.history_redo_button)
        buttons.addStretch(1)
        buttons.addWidget(self.step_button)
        buttons.addWidget(self.resend_button)

        self.step_button.setVisible(False)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(header_bar)
        layout.addWidget(self.history_list, 1)
        layout.addWidget(footer)
        return page

    def show_history(self) -> None:
        self.stack.setCurrentIndex(_HISTORY_PAGE)

    def show_thread(self) -> None:
        self.stack.setCurrentIndex(_THREAD_PAGE if not self.thread.is_empty() else _WELCOME_PAGE)

    @property
    def history_shown(self) -> bool:
        return self.stack.currentIndex() == _HISTORY_PAGE

    def set_history(self, turns, can_undo: bool, can_redo: bool) -> None:
        """``turns``: dicts with time, request, layers, applied; oldest first."""
        dark = self._dark()
        palette = tokens(dark)
        self.history_list.clear()
        last_applied = max((index for index, turn in enumerate(turns) if turn.get("applied")), default=-1)
        for position, turn in enumerate(turns):
            when = time.strftime("%H:%M", time.localtime(turn.get("time") or 0))
            layers = ", ".join(turn.get("layers") or ())
            request = turn.get("request") or _tr("(no request)")
            # A turn that changed nothing has nothing to undo: no state (mockup: History board).
            state = "" if not layers else (_tr("applied") if turn.get("applied") else _tr("undone"))
            item = QListWidgetItem()
            item.setData(_TURN_ROLE, turn.get("request") or "")
            item.setToolTip(plain_tooltip(f"{when}  {request}\n{layers or _tr('no change')}"
                                          + (f" · {state}" if state else "")))
            self._history_row(item, when, request, layers or _tr("no change"), state, bool(turn.get("applied")),
                              palette, dark)
            if position == last_applied:  # the steps of the last request can be undone one by one
                for number, label in enumerate(turn.get("steps") or ()):
                    step = QListWidgetItem()
                    step.setData(_TURN_ROLE, "")
                    step.setData(_STEP_ROLE, number)
                    step.setToolTip(plain_tooltip(label))
                    self._history_row(step, "", f"{number + 1}. {label}", "", "", True, palette, dark, step=True)
        self.history_list.scrollToBottom()
        self.history_count.setText(_tr("this project · {} turn(s)").format(len(turns)))
        self.history_count.setStyleSheet(f"color: {palette['fm_text_muted']};")
        self.history_undo_button.setEnabled(can_undo and not self._working)
        self.history_redo_button.setEnabled(can_redo and not self._working)
        self._on_turn_selected()

    def _history_row(self, item: QListWidgetItem, when: str, request: str, layers: str, state: str, applied: bool,
                     palette: dict, dark: bool, step: bool = False) -> None:
        """One line of the history: time, request, what it changed, applied or undone; an undone one is dimmed."""
        muted = palette["fm_text_muted"]
        row = QWidget(self.history_list)
        row.setObjectName("widget_agent_history_row")
        row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # the list keeps the selection
        layout = QHBoxLayout(row)
        layout.setContentsMargins(24 if step else 10, 6 if step else 8, 10, 6 if step else 8)
        layout.setSpacing(10)
        if when:
            time_label = QLabel(when, row)
            time_label.setStyleSheet(f"font-size: 11px; color: {muted};")
            layout.addWidget(time_label, 0, Qt.AlignmentFlag.AlignTop)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        title = ElidedLabel(request, row)
        title.setStyleSheet(f"font-size: {12 if step else 13}px; color: {palette['fm_text'] if applied and not step else muted};")
        column.addWidget(title)
        if layers:
            sub = ElidedLabel(layers, row)
            sub.setStyleSheet(f"font-size: 11px; color: {muted};")
            column.addWidget(sub)
        layout.addLayout(column, 1)
        if state:
            state_label = QLabel(state, row)
            state_label.setStyleSheet(f"font-size: 11px; color: {DONE_COLOR['dark' if dark else 'light'] if applied else muted};")
            layout.addWidget(state_label, 0, Qt.AlignmentFlag.AlignTop)
        for label in row.findChildren(QLabel):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.history_list.addItem(item)
        item.setSizeHint(row.sizeHint())
        self.history_list.setItemWidget(item, row)

    def _on_turn_selected(self) -> None:
        items = self.history_list.selectedItems()
        step = items[0].data(_STEP_ROLE) if items else None
        typed_here = (bool(items) and step is None and bool(items[0].data(_TURN_ROLE))
                      and not str(items[0].data(_TURN_ROLE) or "").startswith(EXTERNAL_MARK))
        self.resend_button.setEnabled(typed_here and not self._working)
        self.step_button.setEnabled(step is not None and not self._working)
        self.step_button.setVisible(step is not None)  # only on a step: the footer is the mockup's otherwise

    def _undo_to_selected_step(self) -> None:
        items = self.history_list.selectedItems()
        step = items[0].data(_STEP_ROLE) if items else None
        if step is not None and not self._working:
            self.step_undo_requested.emit(int(step))

    def _resend_selected(self) -> None:
        items = self.history_list.selectedItems()
        if items and not self._working:
            self.resend_requested.emit(str(items[0].data(_TURN_ROLE) or ""))

    def _build_welcome(self) -> QWidget:
        page = QWidget(self)
        self.welcome_icon = QLabel(page)
        self.welcome_icon.setObjectName("label_agent_welcome_icon")
        self.welcome_icon.setFixedSize(WELCOME_ICON_SIZE, WELCOME_ICON_SIZE)
        self.welcome_title = QLabel(page)
        self.welcome_title.setObjectName("label_agent_welcome")
        self.welcome_title.setWordWrap(True)
        font = self.welcome_title.font()
        font.setBold(True)
        self.welcome_title.setFont(font)
        self.welcome_text = QLabel(page)
        self.welcome_text.setObjectName("label_agent_welcome_text")
        self.welcome_text.setWordWrap(True)
        self.welcome_note = QLabel(_tr("It needs an AI provider: the free quota of FilterMate, your own key, or a local "
                                       "model. Nothing is sent before you agree."), page)
        self.welcome_note.setObjectName("label_agent_welcome_note")
        self.welcome_note.setWordWrap(True)
        self.configure_button = QPushButton(_tr("Connect a provider"), page)
        self.configure_button.setObjectName("pushButton_agent_configure")
        self.configure_button.clicked.connect(self.settings_requested)
        self.try_label = QLabel(_tr("TRY"), page)
        self.try_label.setObjectName("label_agent_try")
        page.setObjectName("widget_agent_welcome")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.welcome_icon)
        layout.addWidget(self.welcome_title)
        layout.addWidget(self.welcome_text)
        layout.addWidget(self.welcome_note)
        layout.addWidget(self.configure_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(4)
        layout.addWidget(self.try_label)
        self.example_buttons = []
        for text in examples():
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
        # The theme of the dock (its sheet, then its icon manager) before the palette, which can be the other
        # theme: QGIS may run a dark system palette under the light FilterMate theme, and the reverse.
        return bool(plugin_is_dark(self))

    def _refresh_look(self) -> None:
        """Icons and colors of the current theme, as the mockup draws them."""
        dark = self._dark()
        palette = tokens(dark)
        if hasattr(self, "widgets_strip"):
            self.widgets_strip.refresh_look()
        muted = palette["fm_text_muted"]
        self.destination.setStyleSheet(f"color: {muted};")
        send_color = palette["fm_danger"] if self._working else palette["fm_accent"]
        sheet = (
            # The dock pads every frame by 6 px: the panel and its pages sit on the edges of the section headers.
            f"QFrame#{PANEL_NAME}, QStackedWidget#stackedWidget_agent {{ padding: 0px; margin: 0px; border: none;"
            " background: transparent; }"
            # Its own sheet wins over the rules of the accordion, which size every tool button as a section tab.
            f"QToolButton {{ min-width: {BUTTON_SIZE}px; max-width: {BUTTON_SIZE}px; min-height: {BUTTON_SIZE}px; "
            f"max-height: {BUTTON_SIZE}px; padding: 0; margin: 0; }}"
            "QToolButton::menu-indicator { image: none; }"
            f"QListWidget {{ font-family: '{FONT_FAMILY}', sans-serif; }}"
            f"QLineEdit#lineEdit_agent_input {{ min-height: {INPUT_HEIGHT - 2}px; max-height: {INPUT_HEIGHT}px;"
            f" border: 1px solid {palette['fm_field_border']}; border-radius: 6px; padding: 0 10px;"
            f" background: {palette['fm_field']}; color: {palette['fm_text']}; }}"
            f"QLineEdit#lineEdit_agent_input:focus {{ border-color: {palette['fm_accent']}; }}"
            f"QToolButton#toolButton_agent_send {{ min-width: {INPUT_HEIGHT}px; max-width: {INPUT_HEIGHT}px;"
            f" min-height: {INPUT_HEIGHT}px; max-height: {INPUT_HEIGHT}px; border: none; border-radius: 6px;"
            f" background: {send_color}; }}"
            f"QToolButton#toolButton_agent_more {{ min-width: {INPUT_HEIGHT - 2}px; max-width: {INPUT_HEIGHT - 2}px;"
            f" min-height: {INPUT_HEIGHT - 2}px; max-height: {INPUT_HEIGHT - 2}px; border: 1px solid"
            f" {palette['fm_field_border']}; border-radius: 6px; background: {palette['fm_field']}; }}"
            f"QToolButton#toolButton_agent_more:disabled {{ background: {palette['fm_group']}; }}"
            # The frame alone paints the background: a viewport or a page with one of its own squares the corners.
            "QScrollArea#scrollArea_agent_welcome > QWidget#qt_scrollarea_viewport, QWidget#widget_agent_welcome"
            " { background: transparent; }"
            f"QScrollArea#scrollArea_agent_welcome {{ background: {palette['fm_list']}; border: 1px solid"
            f" {palette['fm_group_border']}; border-radius: 6px; }}"
            f"QLabel#label_agent_welcome {{ font-size: 14px; font-weight: 600; color: {palette['fm_text']}; }}"
            f"QLabel#label_agent_welcome_text {{ font-size: 12px; color: {muted}; }}"
            f"QLabel#label_agent_try {{ font-size: 11px; font-weight: 600; color: {muted}; letter-spacing: 1px; }}"
            f"QPushButton#pushButton_agent_example {{ text-align: left; padding: 8px 10px; font-size: 13px;"
            f" border: 1px solid {palette['fm_group_border']}; border-radius: 6px; background: {palette['fm_group']};"
            f" color: {palette['fm_text']}; }}"
            f"QPushButton#pushButton_agent_example:hover {{ border-color: {palette['fm_active_border']}; }}"
            f"QPushButton#pushButton_agent_configure {{ padding: 8px 16px; font-weight: 500; border: none;"
            f" border-radius: 6px; background: {palette['fm_accent']}; color: {palette['fm_accent_text']}; }}"
            f"QLabel#label_agent_welcome_note {{ font-size: 12px; color: {muted}; border: none; border-left: 2px solid"
            f" {palette['fm_group_border']}; padding: 0 0 0 10px; }}"
            f"QFrame#frame_agent_history {{ background: {palette['fm_list']}; border: 1px solid"
            f" {palette['fm_group_border']}; border-radius: 6px; }}"
            f"QWidget#widget_agent_history_header {{ background: transparent; border: none; border-bottom: 1px solid"
            f" {palette['fm_group_border']}; }}"
            f"QWidget#widget_agent_history_footer {{ background: {palette['fm_group']}; border: none; border-top: 1px solid"
            f" {palette['fm_group_border']}; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }}"
            "QListWidget#listWidget_agent_history { background: transparent; border: none; outline: 0; }"
            f"QListWidget#listWidget_agent_history::item {{ border-bottom: 1px solid {palette['fm_group']}; }}"
            f"QListWidget#listWidget_agent_history::item:selected {{ background: {palette['fm_active']}; }}"
            f"QFrame#frame_agent_history QPushButton {{ font-size: 12px; min-height: 0; padding: 4px 10px; }}"
            f"QPushButton#pushButton_agent_resend {{ color: {palette['fm_accent']}; background: transparent; border: none; }}"
            f"QPushButton#pushButton_agent_resend:disabled {{ color: {muted}; }}")
        if sheet != self.styleSheet() and not getattr(self, "_styling", False):
            self._styling = True  # a new sheet is itself a style change: it must not come back here
            try:
                self.setStyleSheet(sheet)
            finally:
                self._styling = False
        self.thread.refresh_look()
        send = render_icon("agent_stop" if self._working else "agent_send", dark, palette["fm_accent_text"])
        if send is not None:
            self.send_button.setIcon(send)
        more = render_icon("more", dark)
        if more is not None:
            self.more_button.setIcon(more)
        back = render_icon("undo", dark)
        if back is not None:
            self.back_button.setIcon(back)
        welcome = render_icon("agent", dark, palette["fm_accent"])
        if welcome is not None:
            self.welcome_icon.setPixmap(welcome.pixmap(WELCOME_ICON_SIZE, WELCOME_ICON_SIZE))

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().changeEvent(event)
        if (event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange) and hasattr(self, "more_button")
                and not getattr(self, "_styling", False)):
            self._refresh_look()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        self._refresh_look()
        self.input.setFocus()

    # --- state ----------------------------------------------------------------

    def set_recipes(self, recipes, can_save: bool) -> None:
        """The recipes of the project in the menu, each with its steps in view before it runs; save the last request."""
        self._recipes, self._can_save_recipe = list(recipes), bool(can_save)
        menu = self.recipes_menu
        for submenu in getattr(self, "_recipe_menus", ()):  # clear() leaves the submenus alive: they would pile up
            submenu.deleteLater()
        self._recipe_menus, self.recipe_actions, self.recipe_lines = [], {}, {}
        menu.clear()
        self.save_recipe_action = menu.addAction(_tr("Save the last request as a recipe…"))
        self.save_recipe_action.setEnabled(self._can_save_recipe)
        self.save_recipe_action.triggered.connect(self.recipe_save_requested)
        if not self._recipes:
            empty = menu.addAction(_tr("No recipe in this project yet"))
            empty.setEnabled(False)
            return
        menu.addSeparator()
        for recipe in self._recipes:
            # "&" would make a shortcut of the next letter; the name comes from the project file.
            entry = menu.addMenu(_tr("{} ({} steps)").format(recipe["name"], len(recipe["steps"])).replace("&", "&&"))
            self._recipe_menus.append(entry)
            for number, step in enumerate(recipe["steps"][:MAX_RECIPE_STEPS_SHOWN], 1):
                line = entry.addAction(f"{number}. {step['label']}".replace("&", "&&"))
                line.setEnabled(False)  # what it will do, read before Run
                self.recipe_lines.setdefault(recipe["id"], []).append(line)
            if len(recipe["steps"]) > MAX_RECIPE_STEPS_SHOWN:
                more = entry.addAction(f"(+{len(recipe['steps']) - MAX_RECIPE_STEPS_SHOWN})")
                more.setEnabled(False)
            entry.addSeparator()
            run = entry.addAction(_tr("Run without the model"))
            run.triggered.connect(lambda _checked=False, recipe_id=recipe["id"]: self.recipe_run_requested.emit(recipe_id))
            remove = entry.addAction(_tr("Remove"))
            remove.triggered.connect(
                lambda _checked=False, recipe_id=recipe["id"]: self.recipe_remove_requested.emit(recipe_id))
            self.recipe_actions[recipe["id"]] = (run, remove)

    @property
    def recipes(self):
        return list(self._recipes)

    def set_ready(self, ready: bool, destination: str = "") -> None:
        """Whether a provider is set up; ``destination`` says where the requests go."""
        self._ready = ready
        if ready:
            self.welcome_title.setText(_tr("What do you want to filter?"))
            self.welcome_text.setText(_tr("Describe it in your own words. The agent reads the project, tries the filter, "
                                          "then applies it. Each turn can be undone."))
        else:
            self.welcome_title.setText(_tr("Filter your layers from a sentence"))
            self.welcome_text.setText(_tr("The agent reads the layers of your project, writes the filters and applies "
                                          "them. Each turn can be undone."))
        self.welcome_icon.setVisible(not ready)
        self.welcome_note.setVisible(not ready)
        self.configure_button.setVisible(not ready)
        # Nothing can be asked before a provider is set up (mockup: Welcome board); the menu still opens the settings.
        if hasattr(self, "send_button"):
            self.input.setEnabled(ready)
            self.input.setPlaceholderText(_tr("Ask for a filter…") if ready else _tr("Connect a provider to start"))
            self.send_button.setEnabled(ready or self._working)
        if hasattr(self, "try_label"):
            self.try_label.setVisible(ready)
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
        self.send_button.setEnabled(self._ready or working)
        self.thread.set_hint(_tr("You can already type the next request.") if working else "")
        self._refresh_look()

    def set_can_undo(self, possible: bool) -> None:
        """Undo sits on the cards of the last step (mockup); the button below only when no card can hold it."""
        on_cards = self.thread.set_undo_possible(possible)
        self.undo_button.setEnabled(possible)
        self.undo_button.setVisible(possible and not on_cards)
        self._undo_possible = possible

    def undo_offered(self) -> bool:
        return getattr(self, "_undo_possible", False)

    def set_status(self, text: str, error: bool = False, offer_settings: bool = False) -> None:
        danger = tokens(self._dark())["fm_danger"]
        self.status.setStyleSheet(f"color: {danger};" if error else "")
        self.status.setText(text)
        self.status.setVisible(bool(text))
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
        self.set_can_undo(False)
        self._in_answer = False
        self.set_status("")
        self.stack.setCurrentIndex(_WELCOME_PAGE)

    def end_answer(self) -> None:
        """What comes next starts on its own line."""
        self._in_answer = False
        self.thread.end_answer()

    # --- the conversation -------------------------------------------------------

    def _show_conversation(self) -> None:
        if not self.history_shown:
            self.stack.setCurrentIndex(_THREAD_PAGE)

    def add_user(self, text: str) -> None:
        """A request of the user, in a tinted bubble on the right."""
        self.input.remember(text)
        self._show_conversation()
        self.thread.add_user(text)
        self._in_answer = False

    def add_action(self, text: str, succeeded: bool = True, detail: str = "", count: str = "",
                   strong: Sequence[str] = ()) -> None:
        """Something the agent changed, or failed to change, in a card; ``count`` is what it kept (``12 / 586``).

        ``strong``: the layer names of ``text``, shown in bold.
        """
        self._show_conversation()
        self.thread.add_card(text, succeeded, detail, count, strong)
        self._in_answer = False

    def show_error(self, title: str, detail: str = "", offer_settings: bool = False) -> None:
        """A request that failed, as a card in the thread (mockup: Error board)."""
        self._show_conversation()
        self.thread.add_error(title, detail, _tr("Open the settings") if offer_settings else "",
                              self.settings_requested.emit if offer_settings else None)
        self._in_answer = False

    def begin_step(self) -> None:
        self.thread.begin_step()

    def add_note(self, text: str) -> None:
        """A remark of the panel itself, muted."""
        self._show_conversation()
        self.thread.add_note(text)
        self._in_answer = False

    def add_text(self, text: str) -> None:
        """More of the answer being written."""
        self._show_conversation()
        self.thread.add_text(text)
        self._in_answer = True

    def add_step(self, text: str) -> None:
        """What the running request is doing now."""
        self._show_conversation()
        self.thread.add_step(text)

    def finish_steps(self, succeeded: bool = True) -> None:
        self.thread.finish_steps(succeeded)

    def clear_steps(self) -> None:
        self.thread.clear_steps()


class AgentSettingsDialog(QDialog):
    """Provider, model, key and what may leave this machine."""

    def __init__(self, values, target_of, parent=None, tester=None, free_available=False, mcp_error="",
                 project_layers=(), tools=()) -> None:
        super().__init__(parent)
        # (name, title, risk class) of the tools of the chat, for the exceptions of the Tools tab.
        self._tools = list(tools)
        # (layer id, name, protected) of the open project, for the protected layers of the Autonomy tab.
        self._project_layers = list(project_layers)
        self.setProperty(OWN_STYLE_PROPERTY, True)  # styled as the mockup draws it: the dock must not reset it
        self.setWindowTitle(_tr("FilterMate agent"))
        self._tester = tester
        self._values = values
        self._target_of = target_of
        self.forget_key = False
        self.preset = QComboBox(self)
        for name in sorted(PRESETS, key=lambda item: item != FREE_PRESET):  # the free quota first, when there is one
            if name != FREE_PRESET or free_available:
                self.preset.addItem(preset_label(name), name)
        # A first use starts on what needs no key; a free quota that went away falls back on the first provider.
        first_use = free_available and not values.model
        self.preset.setCurrentIndex(max(self.preset.findData(FREE_PRESET if first_use else values.preset), 0))
        self.model_label = QLabel(_tr("Model"), self)
        self.model = QComboBox(self)
        self.model.setEditable(True)
        self.base_url = QLineEdit(values.base_url, self)
        self.address_label = QLabel(_tr("Address"), self)
        self.free_notice = QLabel(_tr(
            "A few free requests a month, through the relay of FilterMate to Claude (Anthropic), under the terms of "
            "Anthropic. The relay counts what is spent and keeps no conversation. When it is used up, choose a provider "
            "and enter your own API key."), self)
        self.free_notice.setWordWrap(True)
        self.free_notice.setObjectName("label_agent_settings_note")
        self.key_label = QLabel(_tr("API key"), self)
        self.key = QLineEdit(self)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.forget_button = QPushButton(_tr("Remove"), self)
        self.forget_button.setObjectName("pushButton_agent_forget_key")
        self.forget_button.setToolTip(_tr("Remove the stored key"))
        self.forget_button.clicked.connect(self._on_forget)
        self.key_note = QLabel(_tr("The key is kept in the authentication database of QGIS, never in a settings file. "
                                   "It is only sent to this address."), self)
        self.key_note.setObjectName("label_agent_settings_note")
        self.key_note.setWordWrap(True)
        self.local_filtering_only = QCheckBox(_tr("Only the tools that filter, for a slow computer"), self)
        self.local_filtering_only.setObjectName("checkBox_agent_local_filtering_only")
        self.local_filtering_only.setChecked(values.local_filtering_only)
        self.local_filtering_only.setToolTip(_tr(
            "Ticked, the local model gets only the tools that read and filter the project: about half as much to read "
            "at each request. Measured with qwen3.5:4b, every tool answered as well, or better."))
        self.send_values = QCheckBox(_tr("Allow attribute values to be sent"), self)
        self.send_values.setChecked(values.send_values)
        values_note = QLabel(_tr("Without it, the agent does not read the values of your fields. Those already written "
                                 "in your filters and favorites are still sent."), self)
        values_note.setObjectName("label_agent_settings_sub")
        values_note.setWordWrap(True)
        self.expert_python = QCheckBox(_tr("Expert: let the agent run Python code in QGIS"), self)
        self.expert_python.setObjectName("checkBox_agent_expert_python")
        self.expert_python.setChecked(values.expert_python)
        expert_note = QLabel(_tr("Each run shows you the whole code and asks you first. The code runs with your rights: "
                                 "it can change your data and your files, and undoing the turn does not take it back. "
                                 "For those who read Python."), self)
        expert_note.setObjectName("label_agent_settings_sub")
        expert_note.setWordWrap(True)
        self._expert_note = expert_note  # shown in the Autonomy tab, with the levels
        leaving = QLabel(_tr("WHAT LEAVES THIS MACHINE"), self)
        leaving.setObjectName("label_agent_settings_heading")
        notice = QLabel(_tr(
            "Your request, the names of your layers and fields, your filter expressions and the results of the tools "
            "of the agent, to this provider and under its terms. The conversation is kept on this computer for each "
            "project, until you start a new one."), self)
        notice.setWordWrap(True)
        self.consent = QCheckBox(self)
        consent_note = QLabel(_tr("Choosing another provider or address asks for this agreement again."), self)
        consent_note.setObjectName("label_agent_consent_note")
        consent_note.setWordWrap(True)
        consent_box = QFrame(self)
        consent_box.setObjectName("frame_agent_consent")
        consent_layout = QVBoxLayout(consent_box)
        consent_layout.setContentsMargins(10, 8, 10, 8)
        consent_layout.setSpacing(2)
        consent_layout.addWidget(self.consent)
        consent_layout.addWidget(consent_note)
        self.preset.currentIndexChanged.connect(self._on_preset)
        self.base_url.textChanged.connect(self._on_destination)
        self._on_preset()
        self.model.setEditText(values.model)

        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(6)
        key_row.addWidget(self.key, 1)
        key_row.addWidget(self.forget_button)
        form = QFormLayout()
        form.addRow(_tr("Provider"), self.preset)
        form.addRow(self.model_label, self.model)
        form.addRow(self.key_label, key_row)
        form.addRow(self.address_label, self.base_url)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("pushButton_agent_settings_save")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        line = QFrame(self)
        line.setObjectName("frame_agent_settings_line")
        line.setFixedHeight(1)
        general = QWidget(self)
        general_layout = QVBoxLayout(general)
        general_layout.setSpacing(10)
        general_layout.addLayout(form)
        general_layout.addWidget(self.key_note)
        general_layout.addWidget(self.local_filtering_only)
        general_layout.addWidget(self.free_notice)
        general_layout.addWidget(line)
        general_layout.addWidget(leaving)
        general_layout.addWidget(notice)
        general_layout.addWidget(self.send_values)
        general_layout.addWidget(values_note)
        general_layout.addWidget(consent_box)
        general_layout.addStretch(1)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(general, _tr("Provider"))
        self.tabs.addTab(self._build_sources(values), _tr("Sources"))
        self.tabs.addTab(self._build_autonomy(values), _tr("Autonomy"))
        if self._tools:
            self.tabs.addTab(self._build_tools(values), _tr("Tools"))
        self.tabs.addTab(self._build_applications(values), _tr("Other applications"))
        if mcp_error:
            self.mcp_result.setText(_tr("The MCP server could not start: {}").format(mcp_error))
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)
        self._style_dialog()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        # As a child of the dock, its sheet is set again once shown: polished earlier, it may not apply.
        QTimer.singleShot(0, self._style_dialog)

    def _style_dialog(self) -> None:
        """The look of the mockup (Settings and Sources boards), in the colors of the theme of QGIS."""
        dark = self.palette().window().color().lightness() < 128
        palette = tokens(dark)
        muted = palette["fm_text_muted"]
        sheet = (
            f"QLabel#label_agent_settings_note {{ font-size: 11px; color: {muted}; border: none; border-left: 2px solid"
            f" {palette['fm_group_border']}; padding: 0 0 0 10px; }}"
            f"QLabel#label_agent_settings_sub {{ font-size: 11px; color: {muted}; padding-left: 24px; }}"
            f"QLabel#label_agent_settings_heading {{ font-size: 12px; font-weight: 600; color: {muted};"
            " letter-spacing: 1px; }"
            f"QFrame#frame_agent_settings_line {{ background: {palette['fm_group_border']}; border: none; }}"
            f"QFrame#frame_agent_consent {{ border: 1px solid {palette['fm_active_border']}; border-radius: 6px;"
            f" background: {palette['fm_active']}; }}"
            "QFrame#frame_agent_consent QCheckBox { font-weight: 500; }"
            f"QLabel#label_agent_consent_note {{ font-size: 11px; color: {palette['fm_accent']}; padding-left: 24px;"
            " background: transparent; }"
            f"QPushButton#pushButton_agent_settings_save, QPushButton#pushButton_agent_add_source {{ font-weight: 500;"
            f" border: none; border-radius: 6px; padding: 5px 16px; background: {palette['fm_accent']};"
            f" color: {palette['fm_accent_text']}; }}")
        self.setStyleSheet("")  # the same text again would not polish anew
        self.setStyleSheet(sheet)

    def _build_autonomy(self, values) -> QWidget:
        """How far the agent of the chat goes alone (core.agent.permissions)."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(4)
        self.autonomy = QButtonGroup(page)
        chosen = level_or_default(getattr(values, "autonomy", STANDARD))
        for level in LEVELS:
            button = QRadioButton(level_label(level), page)
            button.setObjectName(f"radioButton_agent_autonomy_{level}")
            button.setProperty("level", level)
            button.setChecked(level == chosen)
            self.autonomy.addButton(button)
            detail = QLabel(level_detail(level), page)
            detail.setObjectName("label_agent_settings_sub")
            detail.setWordWrap(True)
            layout.addWidget(button)
            layout.addWidget(detail)
            layout.addSpacing(6)
        note = QLabel(_tr('When the agent asks, "Yes for this conversation" lets that action run without asking '
                          "again, until a new conversation, another project or another level. Python code of the expert "
                          "mode is asked at every run. Other applications (MCP) are always asked as at the Standard "
                          "level."), page)
        note.setObjectName("label_agent_settings_note")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addSpacing(10)
        layout.addWidget(self.expert_python)
        layout.addWidget(self._expert_note)
        layout.addSpacing(10)
        protected_title = QLabel(_tr("LAYERS PROTECTED FROM THE AGENT (THIS PROJECT)"), page)
        protected_title.setObjectName("label_agent_settings_heading")
        self.protected_layers = QListWidget(page)
        self.protected_layers.setObjectName("listWidget_agent_protected_layers")
        self.protected_layers.setMaximumHeight(140)
        for layer_id, name, protected in self._project_layers:
            item = QListWidgetItem(name, self.protected_layers)
            item.setData(Qt.ItemDataRole.UserRole, layer_id)
            item.setToolTip(plain_tooltip(layer_id))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if protected else Qt.CheckState.Unchecked)
        protected_note = QLabel(_tr("The agent reads them and uses them as a source, but never changes them: no "
                                    "filter, style, edit, field, join, new name or removal, whatever the level, in a "
                                    "recipe too, and for other applications. Kept in the project."), page)
        protected_note.setObjectName("label_agent_settings_sub")
        protected_note.setWordWrap(True)
        for widget in (protected_title, self.protected_layers, protected_note):
            widget.setVisible(bool(self._project_layers))
            layout.addWidget(widget)
        layout.addStretch(1)
        return page

    def _build_tools(self, values) -> QWidget:
        """Exceptions by tool: always ask, always allow or never, instead of what the level says."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        hint = QLabel(_tr("By default each tool follows the level of the Autonomy tab. An exception holds for that "
                          "tool alone: Never also hides it from the agent and refuses it in recipes and to other "
                          "applications; Always allow does not go past the Advisor level, and Python code is still "
                          "read and confirmed at every run."), page)
        hint.setObjectName("label_agent_settings_note")
        hint.setWordWrap(True)
        rules = getattr(values, "rules", {}) or {}
        self.tool_rules = QTreeWidget(page)
        self.tool_rules.setObjectName("treeWidget_agent_tool_rules")
        self.tool_rules.setColumnCount(3)
        self.tool_rules.setHeaderLabels([_tr("Tool"), _tr("Kind"), _tr("Rule")])
        self.tool_rules.setRootIsDecorated(False)
        self._rule_boxes = {}
        kinds = {0: _tr("reads"), 1: _tr("view"), 2: _tr("project"), 3: _tr("edit buffer"), 4: _tr("irreversible"),
                 5: _tr("outside")}
        choices = [("", _tr("As the level says")), ("ask", _tr("Always ask")), ("allow", _tr("Always allow")),
                   ("never", _tr("Never"))]
        for name, title, risk in sorted(self._tools, key=lambda row: (row[2], row[1].lower())):
            item = QTreeWidgetItem(self.tool_rules, [title, kinds.get(risk, ""), ""])
            item.setToolTip(0, name)
            box = QComboBox(self.tool_rules)
            for value, label in choices:
                if value == "allow" and name == "run_pyqgis":
                    continue  # code is confirmed at every run
                box.addItem(label, value)
            box.setCurrentIndex(max(box.findData(rules.get(name, "")), 0))
            self.tool_rules.setItemWidget(item, 2, box)
            self._rule_boxes[name] = box
        self.tool_rules.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(hint)
        layout.addWidget(self.tool_rules, 1)
        return page

    def chosen_tool_rules(self) -> dict:
        """The exceptions chosen, without the tools left as the level says."""
        return {name: box.currentData() for name, box in getattr(self, "_rule_boxes", {}).items() if box.currentData()}

    def chosen_protected(self):
        """The ids of the layers ticked as protected."""
        return [self.protected_layers.item(row).data(Qt.ItemDataRole.UserRole)
                for row in range(self.protected_layers.count())
                if self.protected_layers.item(row).checkState() == Qt.CheckState.Checked]

    def chosen_autonomy(self) -> str:
        button = self.autonomy.checkedButton()
        return level_or_default(button.property("level") if button is not None else STANDARD)

    def _build_applications(self, values) -> QWidget:
        """The MCP server of the plugin: off by default, and only ever reachable from this computer."""
        self._mcp_token = values.mcp_token
        page = QWidget(self)
        hint = QLabel(_tr("Claude Code or another MCP client on this computer can then filter your layers, once FilterMate "
                          "has been opened, under the rules of this panel: the same sources, the same confirmations, and "
                          "filters can be undone here. That application sends what it reads to its own AI provider."), page)
        hint.setWordWrap(True)
        self.mcp_enabled = QCheckBox(_tr("Let other applications on this computer drive FilterMate (MCP server)"), page)
        self.mcp_enabled.setChecked(values.mcp_enabled)
        self.mcp_enabled.toggled.connect(self._on_mcp_toggled)
        self.mcp_port = QSpinBox(page)
        self.mcp_port.setRange(1024, 65535)
        self.mcp_port.setValue(values.mcp_port)
        self.mcp_address = QLabel(page)
        self.mcp_address.setTextFormat(Qt.TextFormat.PlainText)
        self.mcp_address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.mcp_port.valueChanged.connect(self._refresh_mcp_address)
        self.copy_config_button = QPushButton(_tr("Copy the configuration"), page)
        self.copy_config_button.setObjectName("pushButton_agent_mcp_copy_config")
        self.copy_config_button.clicked.connect(lambda: self._copy_mcp(client_config))
        self.copy_desktop_button = QPushButton(_tr("Copy for Claude Desktop"), page)
        self.copy_desktop_button.setObjectName("pushButton_agent_mcp_copy_desktop")
        self.copy_desktop_button.setToolTip(_tr("Through mcp-remote, which needs Node.js: Claude Desktop starts local servers "
                                                "as programs."))
        self.copy_desktop_button.clicked.connect(lambda: self._copy_mcp(claude_desktop_config))
        self.copy_command_button = QPushButton(_tr("Copy the Claude Code command"), page)
        self.copy_command_button.setObjectName("pushButton_agent_mcp_copy_command")
        self.copy_command_button.clicked.connect(lambda: self._copy_mcp(claude_code_command))
        self.new_token_button = QPushButton(_tr("New access token"), page)
        self.new_token_button.setObjectName("pushButton_agent_mcp_new_token")
        self.new_token_button.setToolTip(_tr("Applications already set up will have to be set up again."))
        self.new_token_button.clicked.connect(self._on_new_mcp_token)
        self.mcp_result = QLabel(page)
        self.mcp_result.setTextFormat(Qt.TextFormat.PlainText)
        self.mcp_result.setWordWrap(True)
        form = QFormLayout()
        form.addRow(_tr("Port"), self.mcp_port)
        form.addRow(_tr("Address"), self.mcp_address)
        row = QHBoxLayout()
        row.addWidget(self.copy_config_button)
        row.addWidget(self.copy_desktop_button)
        row.addWidget(self.copy_command_button)
        row.addWidget(self.new_token_button)
        row.addStretch(1)
        layout = QVBoxLayout(page)
        layout.addWidget(hint)
        layout.addWidget(self.mcp_enabled)
        layout.addLayout(form)
        layout.addLayout(row)
        layout.addWidget(self.mcp_result)
        layout.addStretch(1)
        self._refresh_mcp_address()
        self._on_mcp_toggled(values.mcp_enabled)
        return page

    def _refresh_mcp_address(self, _value: int = 0) -> None:
        self.mcp_address.setText(server_url(self.mcp_port.value()))

    def _on_mcp_toggled(self, on: bool) -> None:
        if on and not self._mcp_token:
            self._mcp_token = new_token()
        for widget in (self.mcp_port, self.copy_config_button, self.copy_desktop_button, self.copy_command_button,
                       self.new_token_button):
            widget.setEnabled(on)

    def _on_new_mcp_token(self) -> None:
        self._mcp_token = new_token()
        self.mcp_result.setText(_tr("New token: it applies once these settings are saved."))

    def _copy_mcp(self, text_for) -> None:
        QApplication.clipboard().setText(text_for(self.mcp_port.value(), self._mcp_token))
        self.mcp_result.setText(_tr("Copied, with the access token: keep it to yourself. Save these settings for it to apply."))

    def chosen_mcp_token(self) -> str:
        return self._mcp_token

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
        self.sources_tree.setColumnCount(2)  # the name, and where it comes from on the right (mockup: Sources board)
        self.sources_tree.header().setStretchLastSection(False)
        self.sources_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sources_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
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
        self.add_button.setObjectName("pushButton_agent_add_source")
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
        item = QTreeWidgetItem(parent, [source.title, origin])
        dark = self.palette().window().color().lightness() < 128
        palette = tokens(dark)
        color = {ORIGIN_OFFICIAL: DONE_COLOR["dark" if dark else "light"], ORIGIN_LOCAL: palette["fm_accent"]}.get(
            source.origin, palette["fm_text_muted"])
        item.setForeground(1, QColor(color))
        item.setTextAlignment(1, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
        small = item.font(1)
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        item.setFont(1, small)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setData(0, _TURN_ROLE, source.id)
        item.setToolTip(0, plain_tooltip(f"{source.note}\n{source.address}".strip()))

    def _fill_sources(self, enabled_ids) -> None:
        self.sources_tree.clear()
        groups = ((_tr("Open data platforms"), lambda source: source.kind not in (KIND_MCP, KIND_STAC)),
                  (_tr("Satellite imagery"), lambda source: source.kind == KIND_STAC),
                  (_tr("MCP connectors"), lambda source: source.kind == KIND_MCP))
        for title, belongs in groups:
            group = QTreeWidgetItem(self.sources_tree, [title.upper()])
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            font.setPointSizeF(max(font.pointSizeF() - 1, 7))
            group.setFont(0, font)
            group.setForeground(0, QColor(tokens(self.palette().window().color().lightness() < 128)["fm_text_muted"]))
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
        free = name == FREE_PRESET
        no_key = free or name == "ollama"
        self.local_filtering_only.setVisible(name == "ollama")
        self.key_label.setVisible(not no_key)
        self.key.setVisible(not no_key)
        self.key_note.setVisible(not no_key)
        for widget in (self.model_label, self.model, self.address_label, self.base_url):
            widget.setVisible(not free)
        self.free_notice.setVisible(free)
        self._on_destination()

    def _on_destination(self, _text: str = "") -> None:
        """A key and a consent are for one server: another one starts without them."""
        target = self.chosen_target()
        stored = bool(self._values.authcfg) and self._values.key_target == target and not self.forget_key
        self.key.setPlaceholderText(_tr("Stored: leave empty to keep it") if stored else "")
        self.forget_button.setVisible(stored and self.key.isVisibleTo(self))
        stored_target = self._values.consent_target
        if self.preset.currentData() == "ollama":  # an Ollama address saved with /v1, up to 5.1, is the same server
            stored_target = self._target_of("ollama", stored_target) if stored_target else ""
        self.consent.setChecked(self._values.consent and stored_target == target)
        name = preset_label(self.preset.currentData()) if self.preset.currentData() else self.preset.currentText()
        self.consent.setText(_tr("I agree to send this data to {}").format(name))

    def _on_forget(self) -> None:
        self.forget_key = True
        self._on_destination()

    def chosen_target(self) -> str:
        return self._target_of(self.preset.currentData(), self.base_url.text())

    def chosen_preset(self) -> str:
        return self.preset.currentData()

    def chosen_model(self) -> str:
        return FREE_MODEL if self.preset.currentData() == FREE_PRESET else self.model.currentText().strip()
