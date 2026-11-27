# -*- coding: utf-8 -*-
"""The AGENT section of the accordion: a welcome, the conversation, and one line to ask.

The conversation is a plain text document styled by character formats, on purpose: what a
model writes can repeat what it read in a layer, and rich text would load the images and
follow the links it holds. Nothing here ever parses HTML.
"""
from __future__ import annotations

import html
import re
import time
from typing import Callable, List, Optional, Sequence, Tuple

from qgis.PyQt.QtCore import (
    QByteArray, QCoreApplication, QEvent, QLocale, QModelIndex, QPoint, QSettings, QSize, QStringListModel, Qt, QTimer,
    QUrl, pyqtSignal,
)
from qgis.PyQt.QtGui import QColor, QDesktopServices, QFont, QTextCursor, QTextOption
try:
    from qgis.PyQt.QtGui import QActionGroup
except ImportError:  # Qt5 keeps actions in QtWidgets
    from qgis.PyQt.QtWidgets import QActionGroup
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu,
    QButtonGroup, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QStyle,
    QTabBar, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .agent_thread import DONE_COLOR, AgentThread, ElidedLabel, plain_tooltip
from .agent_activity import AgentActivityIcon
from .agent_widgets_strip import WidgetsStrip
from ...core.agent.example_prompts import (
    CATALOG as EXAMPLE_CATALOG, Facts, SHOWN as EXAMPLES_SHOWN, adjust as adjust_examples, pick as pick_examples,
)
from ...core.agent.mentions import mention_rows
from ...core.agent.modes import ACT, ASK, PLAN
from ...core.agent.postures import ACT as POSTURE_ACT
from ...core.agent.postures import PROPOSE, RESPOND, posture_from_mode, posture_or_default, posture_to_mode
from ...core.agent.request_log import short as short_request
from ...core.agent.memory import (
    ADD, EDIT, MAX_NOTES, MAX_SOURCE_NOTES, MAX_USER_NOTES, REMOVE, SCOPE_SOURCE, SCOPE_USER, Memory, Note,
    chosen as memory_chosen,
)
from ...core.agent.mcp_server import EXTERNAL_MARK, claude_code_command, claude_desktop_config, client_config, new_token, server_url
from ...core.agent.open_data import (
    KIND_CKAN, KIND_GEOCODER, KIND_OPENDATASOFT, KIND_OVERPASS, KIND_WFS, KIND_WMS,
    KIND_WMTS, KIND_XYZ,
)
from ...core.agent.permissions import ADVISOR, AUTONOMOUS, CAREFUL, LEVELS, STANDARD, level_or_default
from ...core.agent.project_notes import MAX_NOTE_CHARS
from ...core.agent.providers import PRESETS
from ...core.agent.providers.base import check_base_url, without_credentials, without_key
from ...core.agent.providers.model_list import KEY_PAGES
from ...core.agent.providers.ollama_chat import (
    OLLAMA_DOWNLOAD_PAGE, RECOMMENDED_LOCAL_MODEL, PullError, canonical_model, installed_models, pull_body, pull_progress, pull_url,
    tags_url,
)
from ...core.agent.sources import (
    KIND_MCP, KIND_STAC, MAX_CUSTOM, ORIGIN_COMMUNITY, ORIGIN_LOCAL, ORIGIN_OFFICIAL, ORIGIN_USER, SOURCE_GROUPS, all_sources,
    custom_from_json, source_group,
    custom_to_json, make_source,
)
from ..styles.mockup_design import FONT_FAMILY, plugin_is_dark, render_icon, tokens
from ..styles.theme_manager import OWN_STYLE_PROPERTY

PANEL_NAME = "AGENT"
INPUT_HEIGHT = 32
_MENTION = re.compile(r"(?:^|(?<=\s))@([^\s@]*)$")  # "@" at the start of a word, and what follows it
THREAD_MIN_HEIGHT = 60  # the dock has to stay usable on small screens
BUTTON_SIZE = 26
ICON_SIZE = 16
ACTION_BUTTON_SIZE = 30
ACTION_ICON_SIZE = 18
PROGRESS_HEIGHT = 3
STATUS_MAX_HEIGHT = 48
WELCOME_ICON_SIZE = 36
_WELCOME_PAGE, _THREAD_PAGE, _HISTORY_PAGE = 0, 1, 2
_TURN_ROLE = Qt.ItemDataRole.UserRole
_STEP_ROLE = Qt.ItemDataRole.UserRole + 1
_RANK_ROLE = Qt.ItemDataRole.UserRole + 2  # the rank of the turn applied in the history of the agent (a step: its turn)
# The tabs of the history (2026-11-24): the turns of the open project, the requests of every project.
HISTORY_PROJECT, HISTORY_ALL = 0, 1

PRESET_LABELS = {"anthropic": "Claude (Anthropic)", "mistral": "Mistral", "openai": "OpenAI", "ollama": "Ollama (local)"}
# Only what can be named without going stale: the user can type any model.
MODEL_SUGGESTIONS = {"anthropic": ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"),
                     "mistral": ("mistral-small-latest", "mistral-medium-latest", "mistral-large-latest")}
OLLAMA_TAGS_TIMEOUT_MS = 2000  # a local server answers at once; a missing one must not hold the dialog
OLLAMA_TAGS_MAX_BYTES = 1_000_000  # the list of the installed models: a few KB
OLLAMA_PULL_IDLE_MS = 60_000  # a download has no total timeout (several GB): only a silence of this long ends it
OLLAMA_PULL_MAX_LINE = 1_000_000  # a line of progress is a few hundred bytes: more is not Ollama
PULL_PERMILLE = 1000  # the progress bar of a download counts in thousandths: a size in bytes overflows its int


MAX_RECIPE_STEPS_SHOWN = 12  # steps listed in the menu of a recipe
# The entries of the feedback menu: the form, and its words in Vector > FilterMate (context FilterMate, translated).
FEEDBACK_ENTRIES = (("usage", "Give your opinion"), ("feature", "Suggest a feature"),
                    ("testers", "Test the experimental features"), ("services", "Training and services"))
_LAST_EXAMPLES = "filter_mate/agent/last_examples"  # the keys of the requests seen last on the welcome
_FOLLOWUP_MODE = "filter_mate/agent/followup_mode"
EXAMPLES_SEEN_MS = 1500  # on screen this long, a set of requests counts as seen
FACTS_SETTLE_MS = 300  # a burst of changes of the project (layers loading) is read once, after it


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentPanel", text)


class _MultiSelectMenu(QMenu):
    """Keep independent checkboxes open; commands and exclusive choices follow normal menu behavior."""

    @staticmethod
    def _can_toggle(action) -> bool:
        if action is None or not action.isEnabled() or not action.isCheckable() or action.menu() is not None:
            return False
        group = action.actionGroup()
        return group is None or not group.isExclusive()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt name
        action = self.actionAt(event.pos())
        if event.button() == Qt.MouseButton.LeftButton and self._can_toggle(action):
            action.trigger()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt name
        action = self.activeAction()
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._can_toggle(action):
            if not event.isAutoRepeat():
                action.trigger()
            event.accept()
            return
        super().keyPressEvent(event)


def _belongs_to_another(model: str, preset: str) -> bool:
    """Is ``model`` a model of a provider other than ``preset``, one the dialog knows (suggested, or a Claude name)?"""
    if not model:
        return False
    if any(model in names for name, names in MODEL_SUGGESTIONS.items() if name != preset):
        return True
    return model.startswith("claude-") and preset != "anthropic"


def _size_text(size: int) -> str:
    """A size in bytes as a person reads it: 3.4 GB, 820 MB."""
    return f"{size / 1e9:.1f} GB" if size >= 1e9 else f"{size / 1e6:.0f} MB"


def preset_label(name: str) -> str:
    """The name of a provider preset as the settings show it, in the language of QGIS."""
    translated = {"ollama": _tr("Ollama (local)")}
    return translated.get(name) or PRESET_LABELS.get(name, name)


def example_text(key: str) -> str:
    """A request of the welcome (core/agent/example_prompts.py), in the language of QGIS; "" for an unknown key."""
    texts = {
        "layers": _tr("Which layers are in this project?"),
        "fields": _tr("Describe the fields of the active layer"),
        "lidar_describe": _tr("What does the point cloud contain?"),
        "tall_buildings": _tr("Keep the buildings taller than 15 m"),
        "roads_inside": _tr("Filter the roads inside the selected feature"),
        "sel_other_layers": _tr("Filter the other layers by the selection"),
        "sel_radius": _tr("Keep what lies within 500 m of the selection"),
        "cross_near": _tr("Keep what lies within 100 m of another layer"),
        "zoom_selection": _tr("Zoom to the selected features"),
        "zoom_filtered": _tr("Zoom to the features the filter keeps"),
        "sel_attributes": _tr("Show the attributes of the selected features"),
        "sel_stats": _tr("Count the selected features by category"),
        "stats_active": _tr("Count the active layer's features by type"),
        "filter_state": _tr("Which layers are filtered, and what is kept?"),
        "clear_all": _tr("Clear all the filters"),
        "visible": _tr("Keep only the features visible on the map"),
        "color_by": _tr("Color the active layer by its main field"),
        "raster_ramp": _tr("Color the active raster with a ramp"),
        "labels": _tr("Label the active layer with its names"),
        "export_gpkg": _tr("Export the filtered layers to a GeoPackage"),
        "export_active": _tr("Export the active layer to GeoJSON"),
        "export_remote": _tr("Save the remote layers to a GeoPackage"),
        "lidar_export": _tr("Export the LiDAR points to LAZ"),
        "slope": _tr("Map the slope of the active raster"),
        "hillshade": _tr("Add a shaded relief from the active raster"),
        "contours": _tr("Draw contour lines from the active raster"),
        "raster_stats": _tr("Give the min, max and mean of the raster"),
        "slope_filter": _tr("Keep the features on slopes over 15 %"),
        "zonal": _tr("Add the mean of the raster to each polygon"),
        "lidar_ground": _tr("Keep only the ground points of the cloud"),
        "lidar_inside": _tr("Keep the LiDAR points inside the selection"),
        "join": _tr("Join two layers by a common field"),
        "buffer_zone": _tr("Draw a 100 m zone around the active layer"),
        "pick_on_map": _tr("Let me pick features on the map"),
        "slider_histogram": _tr("A slider over a number field's histogram"),
        "raster_pipette": _tr("Arm the pipette on this raster"),
        "layout": _tr("Make a print layout of this map"),
        "relief": _tr("Make a relief map of this area with contours"),
        "elevation_view": _tr("Add the elevation of the map view"),
        "people_selected": _tr("How many people live in the selected area?"),
        "population_grid": _tr("Add a population grid of the map view"),
        "osm_cafes": _tr("Add the cafés here from OpenStreetMap"),
        "osm_cycle": _tr("Add the cycle paths of the map view"),
        "osm_trees": _tr("Add the trees and hedges of this area"),
        "dark_basemap": _tr("Put a dark basemap under my layers"),
        "add_basemap": _tr("Add a basemap to start the map"),
        "sentinel": _tr("Find a cloud-free Sentinel-2 image here"),
        "zoom_park": _tr("Zoom to Central Park in New York"),
        "ods_toilets": _tr("Search Opendatasoft for public toilets"),
        "eurostat": _tr("Find unemployment by region on Eurostat"),
        "fr_communes": _tr("Add the municipalities from data.gouv.fr"),
        "fr_bikes": _tr("Find bike-share stations on data.gouv.fr"),
        "fr_buildings": _tr("Add the IGN buildings of the map view"),
        "fr_photos_1950": _tr("Add the 1950s aerial photos of this area"),
        "fr_flood": _tr("Add the flood zones of this area"),
        "fr_clay": _tr("Add the clay shrink-swell hazard map"),
        "fr_town_hall": _tr("Zoom to the town hall of Toulouse"),
        "gb_flood": _tr("Find flood risk data on data.gov.uk"),
        "ca_parks": _tr("Find park data on open.canada.ca"),
        "au_bushfire": _tr("Find bushfire data on data.gov.au"),
        "de_charging": _tr("Search GovData for charging stations"),
        "it_schools": _tr("Search dati.gov.it for school buildings"),
        "nl_bike_parking": _tr("Search data.overheid.nl for bike parking"),
        "jp_shelters": _tr("Search G-Spatial for evacuation shelters"),
        "br_municipalities": _tr("Add the municipalities of Brazil from IBGE"),
        "pl_municipalities": _tr("Add the municipalities of Poland from PRG"),
    }
    return texts.get(key, "")


def qgis_locale() -> str:
    """The locale of QGIS (``fr_FR``, ``en_GB``), else of the system: it chooses the requests about a country."""
    return str(QSettings().value("locale/userLocale", "") or "") or QLocale().name()


def example_needs(key: str) -> Tuple[str, ...]:
    """What a request of the welcome supposes of the project (core/agent/example_prompts.py)."""
    return next((example.needs for example in EXAMPLE_CATALOG if example.key == key), ())


def examples(previous: Sequence[str] = (), facts: Optional[Facts] = None) -> Tuple[Tuple[str, str], ...]:
    """``(key, text)`` of the requests offered on an empty conversation (mockup: Ready board), drawn again each time,
    all true of ``facts`` (the project now; unknown: only those that suppose nothing), none of ``previous`` when the
    catalog allows it."""
    return tuple((key, example_text(key)) for key in pick_examples(qgis_locale(), previous, facts=facts))


class _WelcomePage(QWidget):
    """The welcome of AGENT, which says when it comes on screen: its requests then count as seen."""

    shown = pyqtSignal()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        self.shown.emit()


class ExampleButton(QPushButton):
    """A request of the welcome on one line, cut with … to the width of the dock (a translation can be longer than
    the panel is wide, and a button wide as its text would widen the dock); the whole request in its tooltip, and
    in the input line when clicked."""

    _PADDING = 24  # the 10 px of the style sheet on each side, its border, and a margin

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._request = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def request(self) -> str:
        return self._request

    def set_request(self, text: str) -> None:
        self._request = text
        self.setToolTip(plain_tooltip(text))
        self.setAccessibleName(text)  # the whole request, not the cut one
        self._elide()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:  # the style sheet of the theme sets the font after the text
            self._elide()

    def _elide(self) -> None:
        room = max(self.width() - self._PADDING, 10)
        # "&" doubled: a button reads it as the mark of a shortcut and hides it.
        self.setText(self.fontMetrics().elidedText(self._request, Qt.TextElideMode.ElideRight, room).replace("&", "&&"))


class AgentInput(QPlainTextEdit):
    """The line to ask (2026-11-24: several lines). It grows with what is typed, up to MAX_LINES; Enter sends,
    Ctrl+Enter pushes into a running request, Shift+Enter goes to the line; the arrows give the previous requests
    from its first and last line; Escape stops;
    "@" offers the layers of the project and writes the name chosen.

    The API of the QLineEdit it replaced is kept (``text``, ``setText``, ``insert``, ``returnPressed``): the panel,
    the benches and the takes of the site use it.
    """

    escape_pressed = pyqtSignal()
    returnPressed = pyqtSignal()  # noqa: N815 - the name of the QLineEdit signal it replaces
    push_pressed = pyqtSignal()
    alternate_send_pressed = pyqtSignal()
    MAX_LINES = 5

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history = []
        self._position = 0
        self._draft = ""
        # (id, name, qualifier) of the layers, for "@" rows that tell homonyms apart; the panel sets it.
        self.layer_rows: Callable[[], Sequence[tuple]] = lambda: ()
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(2)
        self._names_model = QStringListModel(self)
        self.completer = QCompleter(self._names_model, self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._mention_rows: list = []  # (label shown, text written) of the "@" popup, in its order
        self.completer.activated[QModelIndex].connect(self._insert_row)
        self.textChanged.connect(self._fit)
        self._fit()

    # --- the API of the QLineEdit ------------------------------------------------

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt name
        self.setPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def insert(self, text: str) -> None:
        self.insertPlainText(text)

    def forget(self) -> None:
        self._history, self._position, self._draft = [], 0, ""

    def remember(self, text: str) -> None:
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._position = len(self._history)

    # --- height ------------------------------------------------------------------

    def _fit(self) -> None:
        """As tall as its lines, MAX_LINES at most (then it scrolls), never less than one line of the panel."""
        lines = max(1, int(self.document().size().height()))
        shown = min(lines, self.MAX_LINES)
        # What the frame, its padding and the margins of the document take, read rather than guessed: the sheet
        # and the style of each platform differ.
        chrome = max(0, self.height() - self.viewport().height())
        needed = shown * self.fontMetrics().lineSpacing() + int(2 * self.document().documentMargin()) + chrome + 2
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if lines > self.MAX_LINES
                                        else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        height = max(INPUT_HEIGHT, needed)
        if height != self.height():
            self.setFixedHeight(height)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self._fit()  # a narrower line wraps into more lines

    # --- keys --------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt name
        key = event.key()
        popup = self.completer.popup()
        if popup.isVisible() and key in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab,
                                         Qt.Key.Key_Backtab):
            event.ignore()  # the completer takes them: the name chosen, or the list closed
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if (event.modifiers() & Qt.KeyboardModifier.ControlModifier
                    and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.alternate_send_pressed.emit()
            elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.insertPlainText("\n")
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.push_pressed.emit()
            else:
                self.returnPressed.emit()
            return
        cursor = self.textCursor()
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
        elif key == Qt.Key.Key_Up and self._position > 0 and self._on_first_line(cursor):
            if self._position == len(self._history):
                self._draft = self.text()
            self._position -= 1
            self.setText(self._history[self._position])
        elif key == Qt.Key.Key_Down and self._position < len(self._history) and self._on_last_line(cursor):
            self._position += 1
            self.setText(self._history[self._position] if self._position < len(self._history) else self._draft)
        else:
            super().keyPressEvent(event)
            self._offer_names()

    @staticmethod
    def _on_first_line(cursor: QTextCursor) -> bool:
        probe = QTextCursor(cursor)
        return not probe.movePosition(QTextCursor.MoveOperation.Up)

    @staticmethod
    def _on_last_line(cursor: QTextCursor) -> bool:
        probe = QTextCursor(cursor)
        return not probe.movePosition(QTextCursor.MoveOperation.Down)

    # --- "@" and the layers ----------------------------------------------------------

    def _typed_mention(self) -> Optional[str]:
        """What follows the "@" being typed at the cursor, None when the cursor is not in such a word."""
        cursor = self.textCursor()
        before = cursor.block().text()[:cursor.positionInBlock()]
        match = _MENTION.search(before)
        return match.group(1) if match else None

    def _offer_names(self) -> None:
        typed = self._typed_mention()
        if typed is None:
            self.completer.popup().hide()
            return
        try:
            rows = mention_rows(self.layer_rows())
        except Exception:  # a project closing
            rows = []
        if not rows:
            self.completer.popup().hide()
            return
        self._mention_rows = rows
        self._names_model.setStringList([label for label, _insert in rows])
        self.completer.setCompletionPrefix(typed)
        if self.completer.completionCount() == 0:
            self.completer.popup().hide()
            return
        rect = self.cursorRect()
        rect.setWidth(max(160, self.completer.popup().sizeHintForColumn(0)
                          + self.completer.popup().verticalScrollBar().sizeHint().width()))
        self.completer.complete(rect)

    def _insert_row(self, index: QModelIndex) -> None:
        """The "@..." typed becomes the row chosen: a name, or the id of one layer among homonyms."""
        if not index.isValid():
            return
        # QCompleter emits an index of its filtered completion model, whose row is not the row of
        # _mention_rows: choosing the first "tron..." completion inserted the first layer, "batiment".
        selected = index.data(Qt.ItemDataRole.DisplayRole)
        for label, inserted in self._mention_rows:
            if label == selected:
                self._insert_name(inserted)
                return

    def _insert_name(self, name: str) -> None:
        """The "@..." typed becomes the name chosen, as the model reads it."""
        typed = self._typed_mention()
        cursor = self.textCursor()
        if typed is not None:
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(typed) + 1)
        cursor.insertText(name)
        self.setTextCursor(cursor)


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
    """Yes or no on code written by a model, or on a skill from elsewhere: the whole text is shown, as plain text,
    and No is the default.

    Every line is wrapped, a word too long too: what comes after thousands of spaces, or a line of 300 characters,
    was off to the right of the view, read by the model and not by the user (2026-11-13)."""
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
    view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    view.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
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


def source_group_titles() -> List[Tuple[str, str]]:
    """The groups of the sources (core/agent/sources.py, source_group) with their titles, in their order: the Sources
    tab of the settings and the menu of the panel."""
    titles = {"open_data": _tr("Open data platforms"), "imagery": _tr("Satellite imagery"),
              "basemaps": _tr("Basemaps"), "places": _tr("Place search"), "databases": _tr("Databases of QGIS"),
              "connectors": _tr("MCP connectors")}
    return [(key, titles[key]) for key in SOURCE_GROUPS]


class AgentPanel(QFrame):
    """Widgets only: the controller decides what happens."""

    send_requested = pyqtSignal(str)
    push_requested = pyqtSignal(str)
    queued_send_requested = pyqtSignal(str, str)
    queued_push_requested = pyqtSignal(str, str)
    mode_changed = pyqtSignal(str)  # Ask, Plan or Act, picked under the line (core/agent/modes.py)
    posture_changed = pyqtSignal(str)  # respond, propose or act (core/agent/postures.py)
    effort_changed = pyqtSignal(str)  # empty: provider default, otherwise a supported reasoning level
    stop_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    setup_requested = pyqtSignal()
    tour_requested = pyqtSignal()  # how FilterMate works, told in the thread (ui/controllers/welcome_tour.py)
    feedback_requested = pyqtSignal(str, str)  # a form of the feedback page of the site, and where it was clicked
    shown = pyqtSignal()  # the panel comes in view: its section opens, or the dock shows it
    new_conversation_requested = pyqtSignal()
    save_project_requested = pyqtSignal()
    microphone_requested = pyqtSignal()
    microphone_cancel_requested = pyqtSignal()
    microphone_settings_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    history_requested = pyqtSignal()
    # The options of the agent from the menu "⋯" (2026-11-16): the controller fills them when the menu opens.
    options_requested = pyqtSignal()
    source_toggled = pyqtSignal(str, bool)
    provider_chosen = pyqtSignal(str)  # the ``ident`` of the provider: the list may have changed since the menu opened
    provider_forgotten = pyqtSignal(str)
    mcp_toggled = pyqtSignal(bool)
    settings_tab_requested = pyqtSignal(str)
    resend_requested = pyqtSignal(str)
    history_clear_requested = pyqtSignal()  # the list of the tab "All projects" emptied
    step_undo_requested = pyqtSignal(int)
    compare_requested = pyqtSignal(int, int)  # the rank of a turn applied, its step (-1: the whole turn)
    card_compare_requested = pyqtSignal(object)  # the compare_key of a card of the thread (the controller set it)
    recipe_save_requested = pyqtSignal()
    recipe_run_requested = pyqtSignal(str)
    recipe_remove_requested = pyqtSignal(str)
    recipe_live_toggled = pyqtSignal(str, bool)
    layer_link_clicked = pyqtSignal(str)  # stable id of the layer clicked in an answer (legacy: its name)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(PANEL_NAME)
        self._working = False
        self._running_posture = ""
        self._followup_mode = str(QSettings().value(_FOLLOWUP_MODE, "push"))
        self._send_stops = False
        self._speech_state = 'idle'
        self._can_compare = False  # the dock has Compare and the history of the project
        self._in_answer = False
        self._ready = False
        # The state of QGIS and the project, read on the main thread by the controller (a ``Facts``); the requests of
        # the welcome follow it. None (a panel alone): unknown, and only requests that suppose nothing are offered.
        self.facts_provider: Optional[Callable[[], Facts]] = None
        self._examples_signature: Tuple[str, ...] = ()  # of the facts the requests on the welcome were drawn for
        self._examples_facts = Facts.unknown()  # the facts themselves
        self._hold = False  # a project is opening: the requests wait for it to settle
        self._facts_timer = QTimer(self)
        self._facts_timer.setSingleShot(True)
        self._facts_timer.setInterval(FACTS_SETTLE_MS)
        self._facts_timer.timeout.connect(self.refresh_examples)
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
        self.thread = AgentThread(lambda: tokens(self._dark()), self._dark, self.undo_requested.emit, self,
                                  self.card_compare_requested.emit)
        self.thread.setMinimumHeight(THREAD_MIN_HEIGHT)
        self.thread.on_layer = self.layer_link_clicked.emit
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
        # Redo beside Undo (S2): one action bar under the thread instead of Undo here and Redo in the history only.
        self.redo_button = QPushButton(_tr("Redo"), self)
        self.redo_button.setObjectName("pushButton_agent_redo")
        self.redo_button.setToolTip(_tr("Do again the turn Undone last"))
        self.redo_button.clicked.connect(self.redo_requested)
        self.set_can_undo(False)
        self.set_can_redo(False)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(4)
        self.activity_icon = AgentActivityIcon(self)
        actions.addWidget(self.activity_icon)
        actions.addWidget(self.status, 1)
        actions.addWidget(self.fix_button)
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)

        # A request sent while the agent works waits here, in view, and goes when the request under way ends
        # (2026-11-24: Enter did nothing then, and the text stayed in the line).
        self._queue = []
        self._queue_paused = False
        self.queue_row = QFrame(self)
        self.queue_row.setObjectName("frame_agent_queued")
        queue_layout = QHBoxLayout(self.queue_row)
        queue_layout.setContentsMargins(8, 3, 4, 3)
        queue_layout.setSpacing(6)
        self.queue_label = ElidedLabel("", self.queue_row)
        self.queue_label.setObjectName("label_agent_queued")
        self.queue_push = QPushButton(_tr("Send now"), self.queue_row)
        self.queue_push.setObjectName("pushButton_agent_queued_push")
        self.queue_push.setFlat(True)
        self.queue_push.setCursor(Qt.CursorShape.PointingHandCursor)
        self.queue_push.setToolTip(_tr("Send the first waiting message to the running agent"))
        self.queue_push.clicked.connect(self._push_queued)
        self.queue_cancel = QPushButton("\u2715", self.queue_row)
        self.queue_cancel.setObjectName("pushButton_agent_queued_cancel")
        self.queue_cancel.setFlat(True)
        self.queue_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.queue_cancel.setToolTip(_tr("Do not send it"))
        self.queue_cancel.clicked.connect(self.cancel_queued)
        queue_layout.addWidget(self.queue_label, 1)
        queue_layout.addWidget(self.queue_push)
        queue_layout.addWidget(self.queue_cancel)
        self.queue_row.setVisible(False)

        self.input = AgentInput(self)
        self.input.setObjectName("lineEdit_agent_input")
        self.input.setPlaceholderText(_tr("Ask for a filter…"))
        self.input.returnPressed.connect(self._on_send)
        self.input.push_pressed.connect(self._on_push)
        self.input.alternate_send_pressed.connect(lambda: self._on_send(alternate=True))
        self.input.layer_rows = lambda: self._layer_rows()  # (id, name, qualifier): the controller sets the layers
        self.mention_source: Callable[[], Sequence] = lambda: ()  # the controller sets it: the layers "@" offers
        self.input.escape_pressed.connect(self._on_escape)

        self.send_button = QToolButton(self)
        self.send_button.setObjectName("toolButton_agent_send")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.send_button.clicked.connect(self._on_send_or_stop)

        self.microphone_button = QToolButton(self)
        self.microphone_button.setObjectName('toolButton_agent_microphone')
        self.microphone_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.microphone_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.microphone_button.clicked.connect(self.microphone_requested)
        self.microphone_button.setToolTip(_tr('Dictate with the microphone'))
        self.microphone_button.setAccessibleName(_tr('Dictate with the microphone'))

        self.more_button = QToolButton(self)
        self.more_button.setObjectName("toolButton_agent_more")
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.more_button.setToolTip(_tr("More"))
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = _MultiSelectMenu(self.more_button)
        # Three groups (2026-11-24): the conversation, the agent, help. New conversation comes first, and is also a
        # link under the line once something was asked.
        self.new_action = menu.addAction(_tr("New conversation"))
        self.new_action.triggered.connect(self.new_conversation_requested)
        self.history_action = menu.addAction(_tr("History…"))
        self.history_action.triggered.connect(self.history_requested)
        self.save_project_action = menu.addAction(_tr("Save project and layers…"))
        self.save_project_action.triggered.connect(self.save_project_requested)
        # Recipes: the changes of a request kept in the project, run again without the model.
        self.recipes_menu = menu.addMenu(_tr("Recipes"))
        self.recipes_menu.setObjectName("menu_agent_recipes")
        self._recipes = []
        self._can_save_recipe = False
        self.set_recipes([], False)
        # Sources, model and the MCP server of the plugin, turned on or off without opening the settings.
        menu.addSeparator()
        self.sources_menu = menu.addMenu(_tr("Sources"))
        self.sources_menu.setObjectName("menu_agent_sources")
        self.models_menu = menu.addMenu(_tr("Model"))
        self.models_menu.setObjectName("menu_agent_models")
        self.mcp_action = menu.addAction(_tr("MCP server of the plugin"))
        self.mcp_action.setCheckable(True)
        self.mcp_action.triggered.connect(self.mcp_toggled)
        self._option_menus = []
        menu.aboutToShow.connect(self.options_requested)
        self.settings_action = menu.addAction(_tr("Agent settings"))
        self.settings_action.triggered.connect(self.settings_requested)
        self.microphone_settings_action = menu.addAction(_tr('Microphone settings…'))
        self.microphone_settings_action.triggered.connect(self.microphone_settings_requested)
        menu.addSeparator()
        self.setup_action = menu.addAction(_tr("Set up FilterMate…"))
        self.setup_action.triggered.connect(self.setup_requested)
        self.tour_action = menu.addAction(_tr("How FilterMate works"))
        self.tour_action.triggered.connect(self.tour_requested)
        # The forms of the feedback page of the site, as in Vector > FilterMate (infrastructure/feedback_forms.py).
        self.feedback_menu = menu.addMenu(_tr("Feedback"))
        self.feedback_menu.setObjectName("menu_agent_feedback")
        for form, words in FEEDBACK_ENTRIES:
            action = self.feedback_menu.addAction(QCoreApplication.translate("FilterMate", words))
            action.triggered.connect(lambda _checked=False, chosen=form: self.feedback_requested.emit(chosen, "agent-menu"))
        self.more_button.setMenu(menu)

        ask = QHBoxLayout()
        ask.setContentsMargins(0, 0, 0, 0)
        ask.setSpacing(6)
        ask.addWidget(self.input, 1)
        ask.addWidget(self.microphone_button, 0, Qt.AlignmentFlag.AlignBottom)
        ask.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignBottom)  # at the last line of a request that grew
        ask.addWidget(self.more_button, 0, Qt.AlignmentFlag.AlignBottom)

        self.speech_row = QFrame(self)
        self.speech_row.setObjectName('frame_agent_speech')
        speech_layout = QHBoxLayout(self.speech_row)
        speech_layout.setContentsMargins(2, 0, 0, 0)
        self.speech_label = ElidedLabel('', self.speech_row)
        self.speech_label.setObjectName('label_agent_speech')
        self.speech_label.setTextFormat(Qt.TextFormat.PlainText)
        self.speech_cancel = QPushButton(_tr('Cancel dictation'), self.speech_row)
        self.speech_cancel.setFlat(True)
        self.speech_cancel.clicked.connect(self.microphone_cancel_requested)
        speech_layout.addWidget(self.speech_label, 1)
        speech_layout.addWidget(self.speech_cancel)
        self.speech_row.setVisible(False)

        self.destination = ElidedLabel("", self)
        self.destination.setObjectName("label_agent_destination")
        self.destination.setTextFormat(Qt.TextFormat.PlainText)
        self.destination.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        destination_policy = self.destination.sizePolicy()
        destination_policy.setRetainSizeWhenHidden(True)  # keep the groups apart without a provider
        self.destination.setSizePolicy(destination_policy)
        self.destination.setVisible(False)

        # The mode of the agent (2026-11-22): Ask answers and changes nothing, Plan writes the steps and waits for Go,
        # Act does it. Under the line, always in view: the user knows what the next request will be allowed to do.
        self.mode_button = QToolButton(self)
        self.mode_button.setObjectName("toolButton_agent_mode")
        self.mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.mode_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        mode_menu = QMenu(self.mode_button)
        mode_menu.setObjectName("menu_agent_mode")
        self._mode_actions = {}
        for posture, label, words in (
                (RESPOND, _tr("Answer"), _tr("answers and reads, changes nothing")),
                (PROPOSE, _tr("Propose"), _tr("shows each change before applying it")),
                (POSTURE_ACT, _tr("Act"), _tr("follows the permissions saved in the settings"))):
            action = mode_menu.addAction(f"{label} \u2014 {words}")
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, chosen=posture: self._pick_mode(chosen))
            self._mode_actions[posture] = (action, label)
        self.mode_button.setMenu(mode_menu)
        self._mode = ""
        self._posture = ""
        self.set_mode(ACT)

        self.effort_button = QToolButton(self)
        self.effort_button.setObjectName("toolButton_agent_effort")
        self.effort_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.effort_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.effort_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.effort_button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        self.effort_button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        self.effort_button.setAccessibleName(_tr("Reasoning effort"))
        self._effort_levels, self._effort, self._effort_actions = (), "", {}
        self.set_effort_options((), "")

        self.followup_button = QToolButton(self)
        self.followup_button.setObjectName("toolButton_agent_followup")
        self.followup_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.followup_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.followup_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.followup_button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        self.followup_button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        self.followup_button.setAccessibleName(_tr("Messages sent while the agent works"))
        followup_menu = QMenu(self.followup_button)
        self._followup_actions = {}
        for mode, title in (("push", _tr("Push: guide the running request")),
                            ("queue", _tr("Queue: wait for the current request to finish"))):
            action = followup_menu.addAction(title)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, chosen=mode: self.set_followup_mode(chosen, persist=True))
            self._followup_actions[mode] = action
        self.followup_button.setMenu(followup_menu)

        settings_buttons = QHBoxLayout()
        settings_buttons.setContentsMargins(0, 0, 0, 0)
        settings_buttons.setSpacing(6)
        settings_buttons.addWidget(self.mode_button)
        settings_buttons.addWidget(self.effort_button)
        settings_buttons.addWidget(self.followup_button)
        # A new conversation in one click once something was asked (2026-11-24: it was in the menu "⋯" only).
        self.new_button = QPushButton(_tr("New conversation"), self)
        self.new_button.setObjectName("pushButton_agent_new")
        self.new_button.setFlat(True)
        self.new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_button.setToolTip(_tr("Start afresh: the agent forgets this conversation, the changes stay"))
        self.new_button.clicked.connect(self.new_conversation_requested)
        # History and Recipes out of the menu "⋯" (S2): what was done and what runs again without the model,
        # next to the new conversation, always in view.
        self.history_button = QPushButton(_tr("History"), self)
        self.history_button.setObjectName("pushButton_agent_history")
        self.history_button.setFlat(True)
        self.history_button.setCheckable(True)
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_button.setToolTip(_tr("What was asked, what changed, applied or undone"))
        self.history_button.clicked.connect(self.history_requested)
        self.recipes_button = QPushButton(_tr("Recipes \u25be"), self)
        self.recipes_button.setObjectName("pushButton_agent_recipes")
        self.recipes_button.setFlat(True)
        self.recipes_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recipes_button.setToolTip(_tr("Run again the changes of a request, without the model"))
        self.recipes_button.clicked.connect(self._popup_recipes)
        navigation_buttons = QHBoxLayout()
        navigation_buttons.setContentsMargins(0, 0, 0, 0)
        navigation_buttons.setSpacing(6)
        navigation_buttons.addWidget(self.history_button)
        navigation_buttons.addWidget(self.recipes_button)
        navigation_buttons.addWidget(self.new_button)

        # Three settings on the left, three actions on the right, with equal gaps inside each group.
        under = QHBoxLayout()
        under.setContentsMargins(0, 0, 0, 0)
        under.setSpacing(6)
        under.addLayout(settings_buttons)
        under.addWidget(self.destination, 1)
        under.addLayout(navigation_buttons)

        # Icon-only actions keep the input usable in a narrow dock. Their labels
        # stay in tooltips and accessible names, with the same actions in the menu.
        for button, title in ((self.history_button, _tr("History")),
                              (self.recipes_button, _tr("Recipes")),
                              (self.new_button, _tr("New conversation")),
                              (self.undo_button, _tr("Undo this turn")),
                              (self.redo_button, _tr("Redo")),
                              (self.history_undo_button, _tr("Undo the last")),
                              (self.history_redo_button, _tr("Redo")),
                              (self.step_button, _tr("Undo back to here")),
                              (self.compare_button, _tr("Compare")),
                              (self.resend_button, _tr("Send again")),
                              (self.clear_global_button, _tr("Empty the list"))):
            detail = button.toolTip()
            button.setToolTip(f"{title}\n{detail}" if detail and detail != title else title)
            button.setText("")
            button.setAccessibleName(title)
            button.setProperty("fm_agent_action", True)
            button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
            button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.setToolTip(_tr("More actions"))
        self.stack.currentChanged.connect(self._refresh_new_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.progress)  # a thin bar under the header while the agent works (mockup)
        layout.addWidget(self.stack, 1)
        # The widgets the agent made for the user: they stay in view while the conversation scrolls.
        self.widgets_strip = WidgetsStrip(self)
        layout.addWidget(self.widgets_strip)
        layout.addLayout(actions)
        layout.addWidget(self.queue_row)
        layout.addLayout(ask)
        layout.addWidget(self.speech_row)
        layout.addLayout(under)
        self.set_ready(False)
        self.set_followup_mode(self._followup_mode)
        self.set_working(False)
        self._setup_accessibility()
        self.input.textChanged.connect(self._refresh_send_action)
        self._refresh_look()

    def _setup_accessibility(self) -> None:
        """Names the controls for screen readers, and orders Tab from the line outward (S5)."""
        self.input.setAccessibleName(_tr("Request to the agent"))
        self.input.setAccessibleDescription(self.input.placeholderText())
        self.send_button.setAccessibleName(_tr("Send the request"))
        self.send_button.setAccessibleDescription(_tr("Enter sends in the selected mode. Esc stops. Ctrl+Shift+Enter uses the other mode."))
        self.more_button.setAccessibleName(_tr("More actions"))
        self.mode_button.setAccessibleName(_tr("What the agent may do"))
        self.history_button.setAccessibleName(_tr("Show the history"))
        self.recipes_button.setAccessibleName(_tr("Show the recipes"))
        self.new_button.setAccessibleName(_tr("Start a new conversation"))
        self.undo_button.setAccessibleName(_tr("Undo this turn"))
        self.redo_button.setAccessibleName(_tr("Redo the undone turn"))
        self.queue_cancel.setAccessibleName(_tr("Take the waiting requests back to the line"))
        self.setTabOrder(self.input, self.microphone_button)
        self.setTabOrder(self.microphone_button, self.send_button)
        self.setTabOrder(self.send_button, self.more_button)
        self.setTabOrder(self.more_button, self.mode_button)
        self.setTabOrder(self.mode_button, self.effort_button)
        self.setTabOrder(self.effort_button, self.followup_button)
        self.setTabOrder(self.followup_button, self.history_button)
        self.setTabOrder(self.history_button, self.recipes_button)
        self.setTabOrder(self.recipes_button, self.new_button)
        self.setTabOrder(self.new_button, self.undo_button)
        self.setTabOrder(self.undo_button, self.redo_button)
        self.setTabOrder(self.redo_button, self.queue_push)
        self.setTabOrder(self.queue_push, self.queue_cancel)

    def _layer_rows(self) -> list:
        """(id, name, group) of the layers "@" offers: the group tells layers of the same name apart."""
        try:
            layers = list(self.mention_source())
        except Exception:  # a project closing
            return []
        try:
            from qgis.core import QgsProject
            root = QgsProject.instance().layerTreeRoot()
        except Exception:  # without a tree every layer stands by its name
            root = None
        rows = []
        for layer in layers:
            try:
                qualifier = ""
                if root is not None:
                    node = root.findLayer(layer.id())
                    parent = node.parent() if node is not None else None
                    if parent is not None and parent is not root:
                        qualifier = parent.name() or ""
                rows.append((layer.id(), layer.name(), qualifier))
            except Exception:  # one unreadable layer hides no other
                import logging
                logging.getLogger(__name__).debug("Layer omitted from agent mentions: unreadable layer", exc_info=True)
                continue
        return rows

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

        # Two tabs: the turns of this project (undo, redo, compare act on them), and the requests of every project,
        # kept from one session to the next (send one again here, or empty the list).
        self.history_tabs = QTabBar(page)
        self.history_tabs.setObjectName("tabBar_agent_history")
        self.history_tabs.setDrawBase(False)
        self.history_tabs.setExpanding(False)
        self.history_tabs.addTab(_tr("This project"))
        self.history_tabs.addTab(_tr("All projects"))
        self.history_tabs.currentChanged.connect(self._on_history_tab)

        self.history_list = QListWidget(page)
        self.history_list.setObjectName("listWidget_agent_history")
        self.history_list.setWordWrap(True)
        self.history_list.setFrameShape(QFrame.Shape.NoFrame)
        self.history_list.itemSelectionChanged.connect(self._on_turn_selected)
        self.global_list = QListWidget(page)
        self.global_list.setObjectName("listWidget_agent_history_all")
        self.global_list.setWordWrap(True)
        self.global_list.setFrameShape(QFrame.Shape.NoFrame)
        self.global_list.itemSelectionChanged.connect(self._on_turn_selected)
        self.history_pages = QStackedWidget(page)
        self.history_pages.addWidget(self.history_list)
        self.history_pages.addWidget(self.global_list)
        self._project_count_text = ""
        self._global_count_text = ""

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
        self.compare_button = QPushButton(_tr("Compare"), page)
        self.compare_button.setObjectName("pushButton_agent_history_compare")
        self.compare_button.setToolTip(_tr("The map before this request or step left of a line, the map now on its "
                                           "right"))
        self.compare_button.setEnabled(False)
        self.compare_button.setVisible(False)  # until the dock says it can compare (set_can_compare)
        self.compare_button.clicked.connect(self._compare_selected)
        self.resend_button = QPushButton(_tr("Send again"), page)
        self.resend_button.setObjectName("pushButton_agent_resend")
        self.resend_button.setFlat(True)
        self.resend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_button.setEnabled(False)
        self.resend_button.clicked.connect(self._resend_selected)
        self.clear_global_button = QPushButton(_tr("Empty the list"), page)
        self.clear_global_button.setObjectName("pushButton_agent_history_clear")
        self.clear_global_button.setToolTip(_tr("Forget the requests of every project kept on this computer; the "
                                                "turns of the open project stay"))
        self.clear_global_button.setVisible(False)
        self.clear_global_button.clicked.connect(self.history_clear_requested)
        footer = QWidget(page)
        footer.setObjectName("widget_agent_history_footer")
        buttons = QHBoxLayout(footer)
        buttons.setContentsMargins(10, 8, 10, 8)
        buttons.setSpacing(6)
        buttons.addWidget(self.history_undo_button)
        buttons.addWidget(self.history_redo_button)
        buttons.addStretch(1)
        buttons.addWidget(self.compare_button)
        buttons.addWidget(self.step_button)
        buttons.addWidget(self.clear_global_button)
        buttons.addWidget(self.resend_button)

        self.step_button.setVisible(False)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(header_bar)
        layout.addWidget(self.history_tabs)
        layout.addWidget(self.history_pages, 1)
        layout.addWidget(footer)
        return page

    def _on_history_tab(self, index: int) -> None:
        """This project: its buttons; all projects: Send again and Empty the list."""
        self.history_pages.setCurrentIndex(index)
        project = index == HISTORY_PROJECT
        for button in (self.history_undo_button, self.history_redo_button):
            button.setVisible(project)
        self.clear_global_button.setVisible(not project)
        self.history_count.setText(self._project_count_text if project else self._global_count_text)
        self._on_turn_selected()

    def _current_history_list(self) -> QListWidget:
        return self.global_list if self.history_tabs.currentIndex() == HISTORY_ALL else self.history_list

    def set_global_history(self, entries, project_path: str = "") -> None:
        """``entries``: the requests of every project (core/agent/request_log.py), oldest first; those of the open
        project (``project_path``) say so."""
        dark = self._dark()
        palette = tokens(dark)
        self.global_list.clear()
        words = {"changed": "", "unchanged": _tr("no change"), "stopped": _tr("stopped"), "failed": _tr("failed")}
        for item_data in entries:
            moment = time.localtime(item_data.get("time") or 0)
            when = time.strftime("%d/%m %H:%M", moment)
            request = item_data.get("request") or _tr("(no request)")
            here = bool(project_path) and item_data.get("path") == project_path
            project = _tr("this project") if here else (item_data.get("project") or _tr("project never saved"))
            layers = ", ".join(item_data.get("layers") or ()) or words.get(item_data.get("outcome"), "")
            where = " · ".join(part for part in (project, layers) if part)
            shown = short_request(request)  # the row shows the first lines; "Send again" resends the whole request
            item = QListWidgetItem()
            item.setData(_TURN_ROLE, item_data.get("request") or "")
            item.setToolTip(plain_tooltip(f"{time.strftime('%Y-%m-%d %H:%M', moment)}  {shown}\n{where}"
                                          + (f"\n{item_data.get('path')}" if item_data.get("path") else "")))
            self._history_row(item, when, shown, where, "", True, palette, dark, target=self.global_list)
        self.global_list.scrollToBottom()
        self._global_count_text = _tr("all projects · {} request(s)").format(len(entries))
        if self.history_tabs.currentIndex() == HISTORY_ALL:
            self.history_count.setText(self._global_count_text)
        self._on_turn_selected()

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
            if turn.get("applied"):  # the turns applied come first, oldest first: the rank is the place in the list
                item.setData(_RANK_ROLE, position)
            item.setToolTip(plain_tooltip(f"{when}  {request}\n{layers or _tr('no change')}"
                                          + (f" · {state}" if state else "")))
            self._history_row(item, when, request, layers or _tr("no change"), state, bool(turn.get("applied")),
                              palette, dark)
            if position == last_applied:  # the steps of the last request can be undone one by one
                for number, label in enumerate(turn.get("steps") or ()):
                    step = QListWidgetItem()
                    step.setData(_TURN_ROLE, "")
                    step.setData(_STEP_ROLE, number)
                    step.setData(_RANK_ROLE, position)
                    step.setToolTip(plain_tooltip(label))
                    self._history_row(step, "", f"{number + 1}. {label}", "", "", True, palette, dark, step=True)
        self.history_list.scrollToBottom()
        self._project_count_text = _tr("this project · {} turn(s)").format(len(turns))
        if self.history_tabs.currentIndex() == HISTORY_PROJECT:
            self.history_count.setText(self._project_count_text)
        self.history_count.setStyleSheet(f"color: {palette['fm_text_muted']};")
        self.history_undo_button.setEnabled(can_undo and not self._working)
        self.history_redo_button.setEnabled(can_redo and not self._working)
        self._on_turn_selected()

    def _history_row(self, item: QListWidgetItem, when: str, request: str, layers: str, state: str, applied: bool,
                     palette: dict, dark: bool, step: bool = False, target: Optional[QListWidget] = None) -> None:
        """One line of the history: time, request, what it changed, applied or undone; an undone one is dimmed."""
        target = target if target is not None else self.history_list
        muted = palette["fm_text_muted"]
        row = QWidget(target)
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
        target.addItem(item)
        item.setSizeHint(row.sizeHint())
        target.setItemWidget(item, row)

    def _on_turn_selected(self) -> None:
        items = self._current_history_list().selectedItems()
        step = items[0].data(_STEP_ROLE) if items else None
        typed_here = (bool(items) and step is None and bool(items[0].data(_TURN_ROLE))
                      and not str(items[0].data(_TURN_ROLE) or "").startswith(EXTERNAL_MARK))
        self.resend_button.setEnabled(typed_here and not self._working)
        self.step_button.setEnabled(step is not None and not self._working)
        self.step_button.setVisible(step is not None)  # only on a step: the footer is the mockup's otherwise
        # A turn undone is no longer on the map; while the agent works, the map is changing under the comparison.
        rank = items[0].data(_RANK_ROLE) if items else None
        self.compare_button.setVisible(self._can_compare and self.history_tabs.currentIndex() == HISTORY_PROJECT)
        self.compare_button.setEnabled(rank is not None and not self._working)
        self.clear_global_button.setEnabled(self.global_list.count() > 0 and not self._working)

    def set_can_compare(self, possible: bool) -> None:
        """Offer Compare on the turns and steps, and on the cards of the thread: only when the dock has the history of
        the project."""
        self._can_compare = bool(possible)
        self._on_turn_selected()
        self.thread.set_compare_possible(self._can_compare and not self._working)

    def _compare_selected(self) -> None:
        items = self.history_list.selectedItems()
        rank = items[0].data(_RANK_ROLE) if items else None
        step = items[0].data(_STEP_ROLE) if items else None
        if rank is not None and not self._working:
            self.compare_requested.emit(int(rank), int(step) if step is not None else -1)

    def _undo_to_selected_step(self) -> None:
        items = self.history_list.selectedItems()
        step = items[0].data(_STEP_ROLE) if items else None
        if step is not None and not self._working:
            self.step_undo_requested.emit(int(step))

    def _resend_selected(self) -> None:
        items = self._current_history_list().selectedItems()
        if items and not self._working:
            self.resend_requested.emit(str(items[0].data(_TURN_ROLE) or ""))

    def _build_welcome(self) -> QWidget:
        page = _WelcomePage(self)
        page.shown.connect(self._examples_on_screen)
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
        self.welcome_note = QLabel(_tr("It needs an AI provider: your own API key, or a local model with Ollama. "
                                       "Nothing is sent before you agree."), page)
        self.welcome_note.setObjectName("label_agent_welcome_note")
        self.welcome_note.setWordWrap(True)
        self.configure_button = QPushButton(_tr("Connect a provider"), page)
        self.configure_button.setObjectName("pushButton_agent_configure")
        self.configure_button.clicked.connect(self.settings_requested)
        # The setup needs no model: cards of choices in the thread (ui/controllers/setup_wizard.py).
        self.setup_button = QPushButton(_tr("Set up FilterMate, no model needed"), page)
        self.setup_button.setObjectName("pushButton_agent_setup")
        self.setup_button.clicked.connect(self.setup_requested)
        # What each section does, the panels, the buttons: told in the thread, with or without a model.
        self.tour_button = QPushButton(_tr("How FilterMate works"), page)
        self.tour_button.setObjectName("pushButton_agent_tour")
        self.tour_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tour_button.clicked.connect(self.tour_requested)
        # AGENT is experimental: who uses it may want to try what comes next (the testers form of the site).
        # With a model the buttons above are hidden: the setup stays within reach, as a link under the requests.
        self.reconfigure_button = QPushButton(_tr("Reconfigure FilterMate…"), page)
        self.reconfigure_button.setObjectName("pushButton_agent_reconfigure")
        self.reconfigure_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reconfigure_button.clicked.connect(self.setup_requested)
        self.testers_button = QPushButton(_tr("Become a tester of the new features"), page)
        self.testers_button.setObjectName("pushButton_agent_testers")
        self.testers_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.testers_button.clicked.connect(lambda: self.feedback_requested.emit("testers", "agent-welcome"))
        # A model that runs on this computer is a reason to choose it: the welcome says so (2026-11-24).
        self.welcome_local = QLabel(_tr("The model runs on this computer: your project and your requests are not sent "
                                        "to an AI service."), page)
        self.welcome_local.setObjectName("label_agent_welcome_local")
        self.welcome_local.setWordWrap(True)
        self.welcome_local.setVisible(False)
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
        layout.addWidget(self.setup_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.welcome_local)
        layout.addSpacing(4)
        layout.addWidget(self.try_label)
        self.example_buttons = []
        self.example_keys = ()
        self._examples_seen = False
        for _index in range(EXAMPLES_SHOWN):
            button = ExampleButton(page)
            button.setObjectName("pushButton_agent_example")
            button.clicked.connect(lambda _checked=False, shown=button: self.use_example(shown.request()))
            layout.addWidget(button)
            self.example_buttons.append(button)
        self.shuffle_examples()
        layout.addWidget(self.reconfigure_button, 0, Qt.AlignmentFlag.AlignLeft)  # under what the welcome offers
        layout.addWidget(self.tour_button, 0, Qt.AlignmentFlag.AlignLeft)  # under what the welcome offers, either way
        layout.addWidget(self.testers_button, 0, Qt.AlignmentFlag.AlignLeft)
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
        stopping = self._working and not self.input.text().strip()
        send_color = palette["fm_danger"] if stopping else palette["fm_accent"]
        mic_color = palette['fm_danger'] if self._speech_state != 'idle' else palette['fm_text']
        sheet = (
            # The dock pads every frame by 6 px: the panel and its pages sit on the edges of the section headers.
            f"QFrame#{PANEL_NAME}, QStackedWidget#stackedWidget_agent {{ padding: 0px; margin: 0px; border: none;"
            " background: transparent; }"
            # Its own sheet wins over the rules of the accordion, which size every tool button as a section tab.
            f"QToolButton {{ min-width: {BUTTON_SIZE}px; max-width: {BUTTON_SIZE}px; min-height: {BUTTON_SIZE}px; "
            f"max-height: {BUTTON_SIZE}px; padding: 0; margin: 0; }}"
            "QToolButton::menu-indicator { image: none; }"
            f"QListWidget {{ font-family: '{FONT_FAMILY}', sans-serif; }}"
            # Several lines since 2026-11-24 (AgentInput sets its height): the object name of the line it was is kept.
            f"QPlainTextEdit#lineEdit_agent_input {{ border: 1px solid {palette['fm_field_border']}; border-radius: 6px;"
            f" padding: 2px 6px; background: {palette['fm_field']}; color: {palette['fm_text']}; }}"
            f"QPlainTextEdit#lineEdit_agent_input:focus {{ border-color: {palette['fm_accent']}; }}"
            f"QFrame#frame_agent_queued {{ background: {palette['fm_group']}; border: 1px dashed"
            f" {palette['fm_group_border']}; border-radius: 6px; }}"
            f"QLabel#label_agent_queued {{ font-size: 12px; color: {muted}; background: transparent; border: none; }}"
            f"QPushButton#pushButton_agent_queued_cancel {{ border: none; background: transparent; color: {muted};"
            " padding: 0 4px; min-height: 0; min-width: 0; }"
            f"QPushButton#pushButton_agent_queued_push {{ border: none; background: transparent;"
            f" color: {palette['fm_accent']}; padding: 0 4px; min-height: 0; min-width: 0; }}"
            f"QToolButton#toolButton_agent_send {{ min-width: {INPUT_HEIGHT}px; max-width: {INPUT_HEIGHT}px;"
            f" min-height: {INPUT_HEIGHT}px; max-height: {INPUT_HEIGHT}px; border: none; border-radius: 6px;"
            f" background: {send_color}; }}"
            f"QToolButton#toolButton_agent_more {{ min-width: {INPUT_HEIGHT - 2}px; max-width: {INPUT_HEIGHT - 2}px;"
            f" min-height: {INPUT_HEIGHT - 2}px; max-height: {INPUT_HEIGHT - 2}px; border: 1px solid"
            f" {palette['fm_field_border']}; border-radius: 6px; background: {palette['fm_field']}; }}"
            f"QToolButton#toolButton_agent_more:disabled {{ background: {palette['fm_group']}; }}"
            f"QToolButton#toolButton_agent_microphone {{ min-width: {INPUT_HEIGHT - 2}px; max-width: {INPUT_HEIGHT - 2}px;"
            f" min-height: {INPUT_HEIGHT - 2}px; max-height: {INPUT_HEIGHT - 2}px; border: 1px solid {mic_color};"
            f" border-radius: 6px; background: {palette['fm_field']}; }}"
            f"QToolButton#toolButton_agent_microphone:focus {{ border-color: {palette['fm_accent']}; }}"
            f"QLabel#label_agent_speech {{ color: {mic_color}; }}"
            "QToolButton#toolButton_agent_effort, QToolButton#toolButton_agent_followup {"
            f" min-width: {ACTION_BUTTON_SIZE}px; max-width: {ACTION_BUTTON_SIZE}px;"
            f" min-height: {ACTION_BUTTON_SIZE}px; max-height: {ACTION_BUTTON_SIZE}px; border: 1px solid transparent;"
            " border-radius: 6px; background: transparent; }"
            "QToolButton#toolButton_agent_effort:hover, QToolButton#toolButton_agent_followup:hover {"
            f" background: {palette['fm_hover']}; }}"
            "QToolButton#toolButton_agent_effort:focus, QToolButton#toolButton_agent_followup:focus {"
            f" border-color: {palette['fm_accent']}; }}"
            f"QToolButton#toolButton_agent_mode {{ min-width: 0; max-width: 240px; min-height: 20px;"
            f" max-height: 22px; padding: 0 8px; border: 1px solid {palette['fm_field_border']}; border-radius: 10px;"
            f" background: {palette['fm_field']}; color: {palette['fm_text']}; font-size: 11px; }}"
            f"QToolButton#toolButton_agent_mode:hover {{ border-color: {palette['fm_accent']}; }}"
            # Act changes the project: its chip is drawn in the accent; Answer and Propose, which change nothing
            # without being shown first, stay plain.
            + (f"QToolButton#toolButton_agent_mode {{ border-color: {palette['fm_accent']}; color: {palette['fm_accent']};"
               " font-weight: 600; }" if getattr(self, "_posture", POSTURE_ACT) == POSTURE_ACT else "") +
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
            f"QPushButton#pushButton_agent_setup {{ padding: 8px 16px; border: 1px solid {palette['fm_group_border']};"
            f" border-radius: 6px; background: {palette['fm_group']}; color: {palette['fm_text']}; }}"
            f"QPushButton#pushButton_agent_setup:hover {{ border-color: {palette['fm_active_border']}; }}"
            f"QFrame#{PANEL_NAME} QPushButton[fm_agent_action=\"true\"] {{ padding: 0; margin: 0; border: 1px solid transparent;"
            f" border-radius: 6px; background: transparent; min-width: {ACTION_BUTTON_SIZE}px;"
            f" max-width: {ACTION_BUTTON_SIZE}px; min-height: {ACTION_BUTTON_SIZE}px;"
            f" max-height: {ACTION_BUTTON_SIZE}px; }}"
            f"QFrame#{PANEL_NAME} QPushButton[fm_agent_action=\"true\"]:hover {{ background: {palette['fm_hover']};"
            f" border-color: {palette['fm_field_border']}; }}"
            f"QFrame#{PANEL_NAME} QPushButton[fm_agent_action=\"true\"]:checked {{ background: {palette['fm_active']};"
            f" border-color: {palette['fm_active_border']}; }}"
            f"QFrame#{PANEL_NAME} QPushButton[fm_agent_action=\"true\"]:focus {{ border-color: {palette['fm_accent']}; }}"
            f"QFrame#{PANEL_NAME} QPushButton[fm_agent_action=\"true\"]:disabled {{ background: transparent; border-color: transparent; }}"
            f"QPushButton#pushButton_agent_tour, QPushButton#pushButton_agent_testers,"
            f" QPushButton#pushButton_agent_reconfigure {{ padding: 4px 0; font-size: 12px;"
            f" font-weight: 500; border: none; background: transparent; color: {palette['fm_accent']}; text-align: left; }}"
            f"QPushButton#pushButton_agent_tour:hover, QPushButton#pushButton_agent_testers:hover,"
            f" QPushButton#pushButton_agent_reconfigure:hover {{ text-decoration: underline; }}"
            f"QLabel#label_agent_welcome_note {{ font-size: 12px; color: {muted}; border: none; border-left: 2px solid"
            f" {palette['fm_group_border']}; padding: 0 0 0 10px; }}"
            f"QLabel#label_agent_welcome_local {{ font-size: 12px; color: {muted}; border: none; border-left: 2px solid"
            f" {palette['fm_accent']}; padding: 0 0 0 10px; }}"
            f"QFrame#frame_agent_history {{ background: {palette['fm_list']}; border: 1px solid"
            f" {palette['fm_group_border']}; border-radius: 6px; }}"
            f"QWidget#widget_agent_history_header {{ background: transparent; border: none; border-bottom: 1px solid"
            f" {palette['fm_group_border']}; }}"
            f"QWidget#widget_agent_history_footer {{ background: {palette['fm_group']}; border: none; border-top: 1px solid"
            f" {palette['fm_group_border']}; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }}"
            "QListWidget#listWidget_agent_history, QListWidget#listWidget_agent_history_all { background: transparent;"
            " border: none; outline: 0; }"
            f"QListWidget#listWidget_agent_history::item, QListWidget#listWidget_agent_history_all::item {{"
            f" border-bottom: 1px solid {palette['fm_group']}; }}"
            f"QListWidget#listWidget_agent_history::item:selected, QListWidget#listWidget_agent_history_all::item:selected"
            f" {{ background: {palette['fm_active']}; }}"
            f"QTabBar#tabBar_agent_history {{ background: transparent; }}"
            f"QTabBar#tabBar_agent_history::tab {{ font-size: 12px; padding: 5px 12px; margin: 0; border: none;"
            f" border-bottom: 2px solid transparent; background: transparent; color: {muted}; }}"
            f"QTabBar#tabBar_agent_history::tab:selected {{ color: {palette['fm_text']}; border-bottom-color:"
            f" {palette['fm_accent']}; font-weight: 600; }}"
            f"QTabBar#tabBar_agent_history::tab:hover {{ color: {palette['fm_text']}; }}"
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
        send = render_icon("agent_stop" if stopping else "agent_send", dark, palette["fm_accent_text"])
        if send is not None:
            self.send_button.setIcon(send)
        microphone = render_icon('agent_microphone' if self._speech_state == 'idle' else 'agent_stop', dark, mic_color)
        if microphone is not None:
            self.microphone_button.setIcon(microphone)
        more = render_icon("more", dark)
        if more is not None:
            self.more_button.setIcon(more)
        self._refresh_action_icons(dark)
        back = render_icon("undo", dark)
        if back is not None:
            self.back_button.setIcon(back)
        welcome = render_icon("agent_network", dark, palette["fm_accent"])
        if welcome is not None:
            self.welcome_icon.setPixmap(welcome.pixmap(WELCOME_ICON_SIZE, WELCOME_ICON_SIZE))
        self.activity_icon.refresh_look(dark)

    def _refresh_action_icons(self, dark: bool) -> None:
        """One icon language for the toolbar, menus and recipe actions, in either theme."""
        if hasattr(self, "effort_button"):
            self._refresh_effort_button()
        if hasattr(self, "followup_button"):
            self._refresh_followup_button()
        for name, key, fallback in (
                ("history_button", "history", QStyle.StandardPixmap.SP_FileDialogDetailedView),
                ("recipes_button", "recipes", QStyle.StandardPixmap.SP_FileIcon),
                ("new_button", "new_conversation", QStyle.StandardPixmap.SP_FileDialogNewFolder),
                ("undo_button", "undo", QStyle.StandardPixmap.SP_ArrowBack),
                ("redo_button", "redo", QStyle.StandardPixmap.SP_ArrowForward)):
            button = getattr(self, name, None)
            if button is not None:
                icon = render_icon(key, dark)
                button.setIcon(icon if icon is not None else self.style().standardIcon(fallback))
        for name, key in (("new_action", "new_conversation"), ("history_action", "history"),
                          ("recipes_menu", "recipes"), ("sources_menu", "projection"),
                          ("models_menu", "agent"), ("mcp_action", "link"),
                          ("settings_action", "settings"), ("setup_action", "settings"),
                          ("tour_action", "help"), ("feedback_menu", "agent"),
                          ("save_recipe_action", "save"), ("history_undo_button", "undo"),
                          ("history_redo_button", "redo"), ("resend_button", "refresh"),
                          ("step_button", "undo"), ("compare_button", "compare"),
                          ("clear_global_button", "trash")):
            target = getattr(self, name, None)
            icon = render_icon(key, dark)
            if target is not None and icon is not None:
                target.setIcon(icon)
        for menu in getattr(self, "_recipe_menus", ()):
            icon = render_icon("recipes", dark)
            if icon is not None:
                menu.setIcon(icon)
        for run, remove in getattr(self, "recipe_actions", {}).values():
            for action, key in ((run, "play"), (remove, "trash")):
                icon = render_icon(key, dark)
                if icon is not None:
                    action.setIcon(icon)
        for action in getattr(self, "recipe_live", {}).values():
            icon = render_icon("refresh", dark)
            if icon is not None:
                action.setIcon(icon)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().changeEvent(event)
        if (event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange) and hasattr(self, "more_button")
                and not getattr(self, "_styling", False)):
            self._refresh_look()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        self._refresh_look()
        self.input.setFocus()
        self.shown.emit()

    # --- state ----------------------------------------------------------------

    @staticmethod
    def _effort_label(value: str) -> str:
        return {"": _tr("Automatic"), "none": _tr("Minimal"), "low": _tr("Low"),
                "medium": _tr("Medium"), "high": _tr("High"), "xhigh": _tr("Very high"),
                "max": _tr("Maximum")}.get(value, _tr("Automatic"))

    def set_effort_options(self, levels, current: str = "") -> None:
        """Show only this model's supported controls; opening the menu never changes its default."""
        known = {"none", "low", "medium", "high", "xhigh", "max"}
        self._effort_levels = tuple(dict.fromkeys(level for level in levels if level in known))
        self._effort = current if current in self._effort_levels else ""
        menu = QMenu(self.effort_button)
        menu.setObjectName("menu_agent_effort")
        self._effort_action_group = QActionGroup(menu)
        self._effort_action_group.setExclusive(True)
        self._effort_actions = {}
        for level in ("",) + self._effort_levels:
            action = menu.addAction(self._effort_label(level))
            action.setCheckable(True)
            self._effort_action_group.addAction(action)
            action.triggered.connect(lambda _checked=False, chosen=level: self._pick_effort(chosen))
            self._effort_actions[level] = action
        previous = self.effort_button.menu()
        self.effort_button.setMenu(menu)
        if previous is not None:
            previous.deleteLater()
        self.effort_button.setVisible(bool(self._effort_levels))
        self.effort_button.setEnabled(bool(self._effort_levels) and not self._working)
        self._refresh_effort_button()

    def _refresh_effort_button(self) -> None:
        for level, action in self._effort_actions.items():
            action.setChecked(level == self._effort)
        tooltip = _tr("Reasoning effort: {}").format(self._effort_label(self._effort))
        tooltip += "\n" + _tr("More effort can take longer and use more tokens.")
        self.effort_button.setToolTip(tooltip)
        self.effort_button.setAccessibleDescription(tooltip)
        dark = self._dark()
        color = tokens(dark)["fm_accent" if self._effort else "fm_icon"]
        icon = render_icon("effort", dark, color)
        self.effort_button.setIcon(icon if icon is not None else self.style().standardIcon(
            QStyle.StandardPixmap.SP_ComputerIcon))

    def _pick_effort(self, value: str) -> None:
        if self._working or (value and value not in self._effort_levels):
            self._refresh_effort_button()
            return
        before, self._effort = self._effort, value
        self._refresh_effort_button()
        if before != value:
            self.effort_changed.emit(value)

    def fill_options(self, groups, providers, mcp_on: bool) -> None:
        """The menu of the options: ``groups`` ``[(title, [(source id, name, ticked)])]``, ``providers`` ``[(label,
        current, ident)]``, the MCP server of the plugin on or not."""
        for submenu in self._option_menus:  # clear() leaves the submenus alive: they would pile up
            submenu.deleteLater()
        self._option_menus = []
        self.sources_menu.clear()
        for title, rows in groups:
            if not rows:
                continue
            submenu = _MultiSelectMenu(title.replace("&", "&&"), self.sources_menu)  # user/QGIS names
            self.sources_menu.addMenu(submenu)
            self._option_menus.append(submenu)
            for source_id, name, on in rows:
                action = submenu.addAction(name.replace("&", "&&"))
                action.setCheckable(True)
                action.setChecked(bool(on))
                action.triggered.connect(lambda checked, source_id=source_id: self.source_toggled.emit(source_id, checked))
        self.sources_menu.addSeparator()
        self.sources_menu.addAction(_tr("Source settings…")).triggered.connect(
            lambda: self.settings_tab_requested.emit("sources"))
        self.models_menu.clear()
        others = []
        for label, current, ident in providers:
            action = self.models_menu.addAction(label.replace("&", "&&"))
            action.setCheckable(True)
            action.setChecked(bool(current))
            if current:  # chosen again: it stays the one in use
                action.triggered.connect(lambda checked, action=action: action.setChecked(True))
            else:
                action.triggered.connect(lambda checked, ident=ident: self.provider_chosen.emit(ident))
                others.append((ident, label))
        if others:
            forget = self.models_menu.addMenu(_tr("Remove from the list"))
            self._option_menus.append(forget)
            for ident, label in others:
                forget.addAction(label.replace("&", "&&")).triggered.connect(
                    lambda checked=False, ident=ident: self.provider_forgotten.emit(ident))
        self.models_menu.addSeparator()
        self.models_menu.addAction(_tr("Other provider or model…")).triggered.connect(
            lambda: self.settings_tab_requested.emit("provider"))
        self.mcp_action.setChecked(bool(mcp_on))

    def set_recipes(self, recipes, can_save: bool) -> None:
        """The recipes of the project in the menu, each with its steps in view before it runs; save the last request."""
        recipes = list(recipes)
        same_entries = [(recipe["id"], recipe["name"], recipe["steps"]) for recipe in recipes] == [
            (recipe["id"], recipe["name"], recipe["steps"]) for recipe in self._recipes]
        self._recipes, self._can_save_recipe = recipes, bool(can_save)
        if same_entries and hasattr(self, "save_recipe_action"):
            # Toggling live refreshes recipes synchronously: keep the open submenu and its action alive.
            self.save_recipe_action.setEnabled(self._can_save_recipe)
            for recipe, entry in zip(self._recipes, self._recipe_menus):
                self._refresh_recipe_menu(recipe, entry)
            return
        menu = self.recipes_menu
        for submenu in getattr(self, "_recipe_menus", ()):  # clear() leaves the submenus alive: they would pile up
            submenu.deleteLater()
        self._recipe_menus, self.recipe_actions, self.recipe_lines, self.recipe_live = [], {}, {}, {}
        menu.clear()
        self.save_recipe_action = menu.addAction(_tr("Save the last request as a recipe…"))
        self.save_recipe_action.setEnabled(self._can_save_recipe)
        self.save_recipe_action.triggered.connect(self.recipe_save_requested)
        self._refresh_action_icons(self._dark())
        if not self._recipes:
            empty = menu.addAction(_tr("No recipe in this project yet"))
            empty.setEnabled(False)
            return
        menu.addSeparator()
        for recipe in self._recipes:
            entry = _MultiSelectMenu(menu)
            menu.addMenu(entry)
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
            live = entry.addAction(_tr("Run again when its source is saved"))
            live.setCheckable(True)
            live.toggled.connect(lambda on, recipe_id=recipe["id"]: self.recipe_live_toggled.emit(recipe_id, on))
            self.recipe_live[recipe["id"]] = live
            self._refresh_recipe_menu(recipe, entry)
            entry.setToolTipsVisible(True)
            remove = entry.addAction(_tr("Remove"))
            remove.triggered.connect(
                lambda _checked=False, recipe_id=recipe["id"]: self.recipe_remove_requested.emit(recipe_id))
            self.recipe_actions[recipe["id"]] = (run, remove)
        self._refresh_action_icons(self._dark())

    def _refresh_recipe_menu(self, recipe, menu) -> None:
        title = _tr("{} ({} steps)").format(recipe["name"], len(recipe["steps"]))
        if recipe.get("live"):
            title = _tr("{} · live").format(title)
        menu.setTitle(title.replace("&", "&&"))  # project names must not become shortcuts
        live = self.recipe_live[recipe["id"]]
        blocked = live.blockSignals(True)
        live.setChecked(bool(recipe.get("live")))
        live.blockSignals(blocked)
        problem = recipe.get("live_problem", "")
        live.setEnabled(not problem or bool(recipe.get("live")))
        live.setToolTip(_tr("Not possible: {}").format(problem) if problem else _tr(
            "The targets follow the source: each time the edits of a source layer of this recipe are saved, the "
            "recipe runs again by itself, as one turn you can undo."))

    @property
    def recipes(self):
        return list(self._recipes)

    def set_ready(self, ready: bool, destination: str = "", local: bool = False) -> None:
        """Whether a provider is set up; ``destination`` says where the requests go, ``local`` whether its model runs
        on this computer (core/agent/local_model.py)."""
        self._ready = ready
        if hasattr(self, "welcome_local"):
            self.welcome_local.setVisible(bool(ready and local))
        if ready:
            # What the agent does goes beyond filters (2026-11-24): open data, relief, styles, charts, layouts.
            self.welcome_title.setText(_tr("What should the agent do?"))
            self.welcome_text.setText(_tr("Filter, find open data, style or map: describe it in your own words. The "
                                          "agent reads the project and shows each step. Each turn can be undone."))
        else:
            self.welcome_title.setText(_tr("Filter your layers from a sentence"))
            self.welcome_text.setText(_tr("The agent reads the layers of your project, writes the filters and applies "
                                          "them. Each turn can be undone."))
        self.welcome_icon.setVisible(not ready)
        self.welcome_note.setVisible(not ready)
        self.configure_button.setVisible(not ready)
        self.setup_button.setVisible(not ready)
        self.reconfigure_button.setVisible(ready)  # without a model, the button above does the same
        # Nothing can be asked before a provider is set up (mockup: Welcome board); the menu still opens the settings.
        if hasattr(self, "send_button"):
            self.input.setEnabled(ready)
            self._refresh_placeholder()
            self.send_button.setEnabled((ready or self._working) and (self._speech_state == 'idle' or self._working))
            self.microphone_button.setEnabled(ready and not self._working)
        if hasattr(self, "try_label"):
            self.try_label.setVisible(ready)
        if hasattr(self, "example_buttons"):
            self._show_examples()
            if ready:
                self._examples_on_screen()  # the welcome may be there: its requests come in sight
        if hasattr(self, "destination"):
            text = _tr("Sent to: {}").format(destination) if ready and destination else ""
            self.destination.set_full_text(text)
            self.destination.setAccessibleName(text)
            self.destination.setVisible(bool(ready and destination))

    def _read_facts(self) -> Facts:
        """The state of QGIS and the project now; unknown when there is no reader or it fails (a layer destroyed, a
        project closing): the requests are then the neutral ones."""
        if self.facts_provider is None:
            return Facts.unknown()
        try:
            facts = self.facts_provider()
        except Exception:  # nothing may come out of a reading: the welcome must still draw
            return Facts.unknown()
        return facts if isinstance(facts, Facts) else Facts.unknown()

    def _seen_examples(self) -> List[str]:
        value = QSettings().value(_LAST_EXAMPLES, "")
        return [str(key) for key in (list(value) if isinstance(value, (list, tuple)) else str(value or "").split(","))]

    def _set_examples(self, keys: Sequence[str], facts: Facts) -> None:
        """Put these requests on the buttons, each in its place; a set that is not the one before counts as unseen."""
        keys = tuple(keys)
        if keys != self.example_keys:
            self._examples_seen = False
        self.example_keys = keys
        self._examples_facts = facts
        self._examples_signature = facts.signature()
        for index, button in enumerate(self.example_buttons):
            if index < len(keys):
                text = example_text(keys[index])
                if text != button.request():
                    button.set_request(text)
            button.setProperty("fm_example_drawn", index < len(keys))
        self._show_examples()

    def shuffle_examples(self) -> None:
        """Other requests on the welcome, true of the project now, none of the set seen last (kept across sessions of
        QGIS).

        A set nobody saw stays while the project stays as it was drawn for: the thread is cleared twice when QGIS
        starts or a project opens (the project closed, then the one read), and a conversation restored hides the
        welcome. Drawing then would count as seen a set that never was, and bring back the one seen before.

        While a project opens (``hold_examples``) nothing is drawn: the layer that will be active is not set yet, and
        the set would change 300 ms later. The requests that are no longer true are only hidden until then."""
        facts = self._read_facts()
        if self._hold:
            self._hide_false_examples(facts)
            return
        if self.example_keys and not self._examples_seen and facts.signature() == self._examples_signature:
            return
        self._examples_seen = False
        self._set_examples(tuple(key for key, _text in examples(self._seen_examples(), facts)), facts)

    def hold_examples(self) -> None:
        """A project is opening or closing: the requests are brought up to date once it has settled (the active layer
        is set after the project is read), not drawn again for the instant in between."""
        self._hold = True
        self._facts_timer.start()

    def stop_following(self) -> None:
        """The controller is shut down: nothing is read of the project any more, a change that was about to be read
        reads nothing."""
        self._facts_timer.stop()
        self._hold = False
        self.facts_provider = None

    def _hide_false_examples(self, facts: Facts) -> None:
        tokens = facts.tokens()
        for index, key in enumerate(self.example_keys):
            if index < len(self.example_buttons) and not set(example_needs(key)) <= tokens:
                self.example_buttons[index].setProperty("fm_example_drawn", False)
        self._show_examples()

    def facts_changed(self) -> None:
        """The project changed (a layer, the selection, a filter, the active layer): the requests are read again once
        the changes stop, so a burst of them (a project loading) is one reading."""
        self._facts_timer.start()

    def refresh_examples(self) -> None:
        """Bring the requests up to date when what they depend on changed since they were drawn; not otherwise, so a
        set the user is reading stays while the project stays as it is. Only the requests that are no longer true go,
        and one the change makes possible comes (``core/agent/example_prompts.py: adjust``): the others stay."""
        if not hasattr(self, "example_buttons"):
            return
        held, self._hold = self._hold, False
        facts = self._read_facts()
        if facts.signature() == self._examples_signature and not held:
            return
        self._adjust_examples(facts)
        if self._ready and self.isVisible() and self.stack.currentIndex() == _WELCOME_PAGE:
            self._examples_on_screen()

    def _adjust_examples(self, facts: Facts) -> None:
        if not self.example_keys:
            self.shuffle_examples()
            return
        keys = adjust_examples(qgis_locale(), self.example_keys, self._seen_examples(), self._examples_facts, facts)
        self._set_examples(keys, facts)

    def _examples_on_screen(self) -> None:
        """The welcome may be on screen: its requests are brought up to date if the project changed since (a signal
        can be missed, or come while the panel was hidden), and count as seen if they are still there in a moment. A
        set shown for an instant (the thread cleared for the project closed, then for the one read) is not."""
        facts = self._read_facts()
        if facts.signature() != self._examples_signature and not self._hold:
            self._adjust_examples(facts)
        if not self._examples_seen and self.example_keys:
            keys = self.example_keys
            QTimer.singleShot(EXAMPLES_SEEN_MS, lambda: self._examples_still_there(keys))

    def _examples_still_there(self, keys) -> None:
        try:
            there = (keys == self.example_keys and self._ready and self.isVisible()
                     and self.stack.currentIndex() == _WELCOME_PAGE)
        except RuntimeError:  # the panel is gone with its dock
            return
        if there and not self._examples_seen:
            self._examples_seen = True
            QSettings().setValue(_LAST_EXAMPLES, ",".join(keys))

    def _show_examples(self) -> None:
        for button in self.example_buttons:
            button.setVisible(bool(self._ready and button.property("fm_example_drawn")))

    def use_example(self, text: str) -> None:
        self.input.setText(text)
        self.input.setFocus()

    def set_mode(self, mode: str) -> None:
        """Show ``mode`` as the one picked, without telling anyone (the controller restores the saved one).

        Takes a posture (``respond``/``propose``/``act``) or a legacy mode (``ask``/``plan``/``act``,
        core/agent/postures.py): the chip shows the posture, ``mode()`` still reads the legacy mode.
        """
        text = str(mode or "").strip().lower()
        if text == ASK:
            posture = RESPOND
        elif text == PLAN:
            posture = PROPOSE
        else:
            posture = posture_or_default(text)
        self._posture = posture
        self._mode = posture_to_mode(posture)
        for each, (action, _label) in self._mode_actions.items():
            action.setChecked(each == self._posture)
        label = self._mode_actions[self._posture][1]
        self.mode_button.setText(f"{label} \u25be")
        self.mode_button.setToolTip(_tr("What the agent may do: Answer reads and changes nothing, Propose writes "
                                        "the steps and shows each change before applying it, Act follows the saved permissions."))
        self._refresh_placeholder()
        if hasattr(self, "thread"):
            self._refresh_followup_hint()
            self._refresh_look()  # the chip takes the color of its posture

    def _refresh_placeholder(self) -> None:
        """The line to ask says what the next request may do: the posture picked under it (2026-11-24)."""
        if not hasattr(self, "input"):
            return
        if not self._ready:
            self.input.setPlaceholderText(_tr("Connect a provider to start"))
            return
        self.input.setPlaceholderText({RESPOND: _tr("Ask a question about the project…"),
                                       PROPOSE: _tr("Describe what to plan…")}.get(
                                           self._posture, _tr("Ask the agent…")))
        if hasattr(self, "send_button"):  # screen readers hear what the line now takes (S5)
            self.input.setAccessibleDescription(self.input.placeholderText())

    def mode(self) -> str:
        return self._mode

    def posture(self) -> str:
        """The posture picked under the line (``respond``/``propose``/``act``, core/agent/postures.py)."""
        return self._posture or posture_from_mode(self._mode)

    def _pick_mode(self, mode: str) -> None:
        before = (self._posture, self._mode)
        self.set_mode(mode)  # also checks the action again when the one already picked is clicked
        if (self._posture, self._mode) != before:
            self.posture_changed.emit(self._posture)
            self.mode_changed.emit(self._mode)

    def set_speech_state(self, state: str, text: str = '') -> None:
        self._speech_state = state
        self.speech_row.setVisible(state != 'idle')
        self.speech_label.setText(text)
        title = {'recording': _tr('Stop recording and transcribe'),
                 'transcribing': _tr('Cancel transcription')}.get(state, _tr('Dictate with the microphone'))
        self.microphone_button.setToolTip(title)
        self.microphone_button.setAccessibleName(title)
        self.send_button.setEnabled((self._ready or self._working) and (state == 'idle' or self._working))
        self._refresh_look()

    def insert_transcription(self, text: str) -> None:
        """Insert plain text at the caret, preserving any selection, draft edits and the input undo history."""
        cursor = self.input.textCursor()
        cursor.clearSelection()
        previous, following = QTextCursor(cursor), QTextCursor(cursor)
        previous.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        following.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
        left = ' ' if previous.selectedText() and not previous.selectedText().isspace() else ''
        right = ' ' if following.selectedText() and not following.selectedText().isspace() else ''
        cursor.insertText(left + text + right)
        self.input.setTextCursor(cursor)
        self.input.setFocus()

    def set_activity_phase(self, phase: str) -> None:
        self.activity_icon.set_phase(phase)

    def activity_phase(self) -> str:
        return self.activity_icon.phase

    def set_running_posture(self, posture: str) -> None:
        self._running_posture = posture_or_default(posture)
        self._refresh_followup_hint()

    def set_working(self, working: bool) -> None:
        """While the agent works the next request can be typed, and the button stops it."""
        self._working = working
        self.activity_icon.set_working(working)
        if working and self._speech_state != 'idle':
            self.microphone_cancel_requested.emit()
        self.microphone_button.setEnabled(self._ready and not working)
        self.progress.setVisible(working)
        self.more_button.setEnabled(not working)
        self.effort_button.setEnabled(bool(self._effort_levels) and not working)
        self.history_undo_button.setEnabled(self.history_undo_button.isEnabled() and not working)
        self.history_redo_button.setEnabled(self.history_redo_button.isEnabled() and not working)
        if hasattr(self, "history_button"):
            self.redo_button.setEnabled(getattr(self, "_redo_possible", False) and not working)
            self.history_button.setEnabled(not working)
            self.recipes_button.setEnabled(not working)
        self._on_turn_selected()
        self.thread.set_compare_possible(self._can_compare and not working)  # the map changes under the comparison
        self._refresh_send_action()
        self.send_button.setEnabled((self._ready or working) and (self._speech_state == 'idle' or working))
        self._refresh_followup_hint()
        if not working and self._queue and not getattr(self, "_queue_paused", False):
            QTimer.singleShot(0, self._send_queued)  # once the engine let go of the request that ended
        self._refresh_new_button()
        self._refresh_look()

    def set_can_undo(self, possible: bool) -> None:
        """Undo sits on the cards of the last step (mockup); the button below only when no card can hold it."""
        on_cards = self.thread.set_undo_possible(possible)
        self.undo_button.setEnabled(possible)
        self.undo_button.setVisible(possible and not on_cards)
        self._undo_possible = possible

    def undo_offered(self) -> bool:
        return getattr(self, "_undo_possible", False)

    def set_can_redo(self, possible: bool) -> None:
        """Redo beside Undo: no card holds it, so the button shows whenever a turn waits to be done again."""
        self.redo_button.setEnabled(bool(possible) and not self._working)
        self.redo_button.setVisible(bool(possible))
        self._redo_possible = bool(possible)

    def set_status(self, text: str, error: bool = False, offer_settings: bool = False) -> None:
        danger = tokens(self._dark())["fm_danger"]
        self.status.setStyleSheet(f"color: {danger};" if error else "")
        self.status.setText(text)
        self.status.setVisible(bool(text))
        self.fix_button.setVisible(offer_settings)

    def set_followup_mode(self, mode: str, persist: bool = False) -> None:
        """Choose whether Enter steers the running exchange or queues the next one."""
        self._followup_mode = mode if mode in ("push", "queue") else "push"
        if persist:
            QSettings().setValue(_FOLLOWUP_MODE, self._followup_mode)
        self._refresh_followup_button()
        self._refresh_followup_hint()
        self._refresh_send_action()

    def _refresh_followup_button(self) -> None:
        dark = self._dark()
        for chosen, action in self._followup_actions.items():
            action.setChecked(chosen == self._followup_mode)
            icon = render_icon("agent_" + chosen, dark)
            fallback = (QStyle.StandardPixmap.SP_ArrowRight if chosen == "push" else
                        QStyle.StandardPixmap.SP_FileDialogListView)
            action.setIcon(icon if icon is not None else self.style().standardIcon(fallback))
        self.followup_button.setIcon(self._followup_actions[self._followup_mode].icon())
        title = (_tr("Push: guide the running request") if self._followup_mode == "push" else
                 _tr("Queue: wait for the current request to finish"))
        tooltip = title + "\n" + _tr("Messages during a run: Push or Queue. Ctrl+Shift+Enter uses the other mode.")
        self.followup_button.setToolTip(tooltip)
        self.followup_button.setAccessibleDescription(tooltip)

    def _refresh_followup_hint(self) -> None:
        running = getattr(self, '_running_posture', '')
        if self._working and running and running != self._posture:
            current = self._mode_actions[running][1]
            chosen = self._mode_actions[self._posture][1]
            self.thread.set_hint(_tr("Current request: {}. Next message: {}. It will wait for the current request.").format(current, chosen))
            return
        text = (_tr("Enter guides the running request. Ctrl+Shift+Enter queues a follow-up.")
                if self._followup_mode == "push" else
                _tr("Enter queues a follow-up. Ctrl+Shift+Enter guides the running request."))
        self.thread.set_hint(text if self._working else "")

    def _refresh_send_action(self) -> None:
        stopping = self._working and not self.input.text().strip()
        tooltip = (_tr("Stop (Esc)") if stopping else
                   _tr("Send to the running agent (Enter)") if self._working and self._followup_mode == "push" else
                   _tr("Queue the request (Enter)") if self._working else _tr("Send (Enter)"))
        self.send_button.setToolTip(tooltip)
        self.send_button.setAccessibleName(_tr("Stop the agent") if stopping else _tr("Send the request"))
        if stopping != self._send_stops:
            self._send_stops = stopping
            self._refresh_look()

    def _on_send(self, alternate: bool = False) -> None:
        if self._speech_state != 'idle':
            return  # dictation is always reviewed in the draft before it can be sent
        text = self.input.text().strip()
        if not text:
            return
        if self._working:
            pushing = self._followup_mode == "push"
            if pushing != alternate:
                self.push_requested.emit(text)
                return
            self._queue.append((text, self._posture))
            self.input.clear()
            self._refresh_queue_row()
            return
        self.send_requested.emit(text)

    def _on_push(self) -> None:
        """Ctrl+Enter sends normally when idle, and steers the active request while working."""
        if self._speech_state != 'idle':
            return
        text = self.input.text().strip()
        if not text:
            return
        if self._working:
            self.push_requested.emit(text)  # the controller clears the draft only once accepted
        else:
            self._on_send()

    @property
    def queued(self) -> str:
        return "\n".join(text for text, _posture in self._queue)

    def queue_message(self, text: str, posture: str, first: bool = False) -> None:
        entry = (text, posture_or_default(posture))
        if first:
            self._queue.insert(0, entry)
        else:
            self._queue.append(entry)
        self._refresh_queue_row()

    def _refresh_queue_row(self) -> None:
        """The pile waiting, numbered once there are several: the first line of each, in order."""
        queue = list(getattr(self, "_queue", ()))
        if not queue:
            self.queue_row.setVisible(False)
            return
        firsts = [" ".join(request.split()) for request, _posture in queue]
        if len(queue) == 1:
            self.queue_label.set_full_text(_tr("Next: {}").format(firsts[0]))
        else:
            shown = " · ".join(f"{number}. {first}" for number, first in enumerate(firsts, 1))
            self.queue_label.set_full_text(_tr("Next ({}): {}").format(len(queue), shown))
        self.queue_label.setToolTip(plain_tooltip("\n".join(f"{number}. {request}"
                                                            for number, (request, _posture) in enumerate(queue, 1))))
        self.queue_row.setVisible(True)

    def pause_queued(self) -> None:
        """Stop halts the agent: the requests waiting stay in view and do not go by themselves (the one stopped comes
        back in the line); ✕ puts them in the line."""
        if self._queue:
            self._queue_paused = True
            self.queue_cancel.setToolTip(_tr("Put them back in the line"))

    def cancel_queued(self) -> None:
        """The requests waiting go back to the line, after what is there, to be changed or sent later."""
        queue, self._queue = list(self._queue), []
        self._queue_paused = False
        self.queue_cancel.setToolTip(_tr("Do not send them"))
        self.queue_row.setVisible(False)
        if queue:
            typed = self.input.text().rstrip()
            back = "\n".join(text for text, _posture in queue)
            self.input.setText(f"{typed}\n{back}" if typed else back)

    def _send_queued(self) -> None:
        """The request under way ended: the first one waiting goes, from the line (the controller empties it once
        sent; refused, it stays there). What was typed meanwhile waits behind the pile, not in the bin (audit of
        2026-11-24: the waiting request overwrote the draft, and after a provider error the returned request too)."""
        if getattr(self, "_queue_paused", False):
            return  # stopped: they wait for the user
        if not self._queue or self._working:
            return
        text, posture = self._queue.pop(0)
        self._refresh_queue_row()
        self.queued_send_requested.emit(text, posture)

    def _push_queued(self) -> None:
        """Promote the first waiting message without replacing the draft typed meanwhile."""
        if not self._queue:
            return
        text, posture = self._queue.pop(0)
        self._refresh_queue_row()
        self.queued_push_requested.emit(text, posture)

    def restore_queued(self, text: str, posture: str) -> None:
        self._queue.insert(0, (text, posture))
        self.pause_queued()
        self._refresh_queue_row()

    def _on_send_or_stop(self) -> None:
        if self._working and not self.input.text().strip():
            self.pause_queued()
            self.stop_requested.emit()
        else:
            self._on_send()

    def _on_escape(self) -> None:
        if self._speech_state != 'idle':
            self.microphone_cancel_requested.emit()
            return
        if self._working:
            self.pause_queued()
            self.stop_requested.emit()

    def clear_input(self) -> None:
        self.input.clear()

    def clear_thread(self) -> None:
        if self._speech_state != 'idle':
            self.microphone_cancel_requested.emit()
        self._queue = []  # a new conversation, another project: what waited for the old one does not go
        self._queue_paused = False
        self.queue_row.setVisible(False)
        self.thread.clear()
        self.set_can_undo(False)
        self.set_can_redo(False)
        self._in_answer = False
        self.set_status("")
        if hasattr(self, "example_buttons"):
            self.shuffle_examples()  # a new conversation offers other requests
        self.stack.setCurrentIndex(_WELCOME_PAGE)
        self._refresh_new_button()
        if hasattr(self, "example_buttons"):
            self._examples_on_screen()  # the welcome may have been on screen already: no show event then

    def end_answer(self) -> None:
        """What comes next starts on its own line."""
        self._in_answer = False
        self.thread.end_answer()

    # --- the conversation -------------------------------------------------------

    def _show_conversation(self) -> None:
        if not self.history_shown:
            self.stack.setCurrentIndex(_THREAD_PAGE)
        self._refresh_new_button()

    def _refresh_new_button(self) -> None:
        """Keep navigation in place; a fresh conversation is offered once there is something to clear."""
        if hasattr(self, "new_button"):
            # The thread page is shown before its first line is added (_show_conversation).
            has_conversation = not self.thread.is_empty() or self.stack.currentIndex() == _THREAD_PAGE
            self.new_button.setEnabled(has_conversation and not self._working)
            self.new_action.setEnabled(has_conversation and not self._working)
            self.history_button.setChecked(self.history_shown)

    def _popup_recipes(self) -> None:
        """The Recipes menu under its link: the same menu as in "⋯", without opening it first."""
        try:
            self.recipes_menu.popup(self.recipes_button.mapToGlobal(QPoint(0, self.recipes_button.height())))
        except RuntimeError:  # the panel went with its dock
            pass

    def add_user(self, text: str) -> None:
        """A request of the user, in a tinted bubble on the right."""
        self.input.remember(text)
        self._show_conversation()
        self.thread.add_user(text)
        self._in_answer = False

    def add_action(self, text: str, succeeded: bool = True, detail: str = "", count: str = "",
                   strong: Sequence[str] = ()):
        """Something the agent changed, or failed to change, in a card (returned); ``count`` is what it kept
        (``12 / 586``).

        ``strong``: the layer names of ``text``, shown in bold.
        """
        self._show_conversation()
        card = self.thread.add_card(text, succeeded, detail, count, strong)
        self._in_answer = False
        return card

    def add_chart(self, title: str, svg: str, caption: str, on_save=None, on_layout=None):
        """A chart the agent drew (returned), with buttons to save it or put it in a print layout."""
        self._show_conversation()
        card = self.thread.add_chart(title, svg, caption, on_save, on_layout)
        self._in_answer = False
        return card

    def add_output(self, path: str, name: str, is_dir: bool = False) -> None:
        self._show_conversation()
        self.thread.add_output(path, name, is_dir)
        self._in_answer = False

    def show_error(self, title: str, detail: str = "", offer_settings: bool = False, action: str = "",
                   on_action=None) -> None:
        """A request that failed, as a card in the thread (mockup: Error board).

        Every error carries its recourse (S5): opening the settings, or ``action`` running ``on_action``
        (sending the returned request again), never bare text.
        """
        self._show_conversation()
        label = _tr("Open the settings") if offer_settings else action
        callback = self.settings_requested.emit if offer_settings else on_action
        self.thread.add_error(title, detail, label, callback)
        self._in_answer = False

    def begin_step(self) -> None:
        self.thread.begin_step()

    def add_settings_card(self, texts: dict, lines, reason: str):
        """A change of the settings of FilterMate asked in the thread, with Apply and Cancel (agent_thread)."""
        self._show_conversation()
        card = self.thread.add_settings_card(texts, lines, reason)
        self._in_answer = False
        return card

    def add_memory_card(self, texts: dict, text: str, editable: bool, buttons, notes=()):
        """A note the agent proposes to keep from one project to the next, or to forget (agent_thread.MemoryCard)."""
        self._show_conversation()
        card = self.thread.add_memory_card(texts, text, editable, buttons, notes)
        self._in_answer = False
        return card

    def add_question_card(self, texts: dict, questions, free_other: bool = True):
        """The questions of ask_user in the thread, with choices to click and a free Other (agent_thread).

        The thread is shown even from the history page: the turn waits for the answer.
        """
        self.stack.setCurrentIndex(_THREAD_PAGE)
        card = self.thread.add_question_card(texts, questions, free_other=free_other)
        self._in_answer = False
        return card

    def add_confirm_card(self, texts: dict, text: str, with_conversation: bool):
        """A question of the permissions in the thread (agent_thread.ConfirmCard), shown even from the history page:
        the turn waits for the answer."""
        self.stack.setCurrentIndex(_THREAD_PAGE)
        self._refresh_new_button()
        card = self.thread.add_confirm_card(texts, text, with_conversation)
        self._in_answer = False
        return card

    def add_link(self, label: str, on_click) -> None:
        """A button the agent puts in the thread: the user goes to a setting when they want."""
        self._show_conversation()
        self.thread.add_link(label, on_click)
        self._in_answer = False

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

    def __init__(self, values, target_of, parent=None, tester=None, mcp_error="",
                 project_layers=(), tools=(), provider_tester=None, databases=(), memory=None, memory_error="",
                 memory_sources=(), memory_active="", memory_file="") -> None:
        super().__init__(parent)
        # The notes kept from one project to the next (core/agent/memory.py), for the Memory tab: None with
        # ``memory_error`` when the file cannot be read. ``memory_sources``: (signature, name) of the layers of the open
        # project; ``memory_active``: the signature of the active one; ``memory_file``: where the notes are kept.
        self._memory_before = memory
        self._memory_error = str(memory_error or "")
        self._memory_sources = [(signature, name) for signature, name in memory_sources]
        self._memory_active = memory_active
        self._memory_file = str(memory_file or "")
        # The PostgreSQL connections of QGIS, as sources: read from QGIS, never added nor removed here.
        self._databases = tuple(databases)
        # (name, title, risk class) of the tools of the chat, for the exceptions of the Tools tab.
        self._tools = list(tools)
        # (layer id, name, protected) of the open project, for the protected layers of the Autonomy tab.
        self._project_layers = list(project_layers)
        self.setProperty(OWN_STYLE_PROPERTY, True)  # styled as the mockup draws it: the dock must not reset it
        self.setWindowTitle(_tr("FilterMate agent"))
        self._tester = tester
        # (preset, model, address, typed key) -> (it answers, what to say, the chat models it lists): the Test button.
        self._provider_tester = provider_tester
        self._testing = False  # a provider is being tested: the wait spins the event loop, a second click is ignored
        self._close_asked = None  # the result of a Save, a Cancel or an Esc that came during a test: done() waits for its end
        self._values = values
        self._target_of = target_of
        self.forget_key = False
        self.preset = QComboBox(self)
        for name in PRESETS:
            self.preset.addItem(preset_label(name), name)
        self.preset.setCurrentIndex(max(self.preset.findData(values.preset), 0))
        self.model_label = QLabel(_tr("Model"), self)
        self.model = QComboBox(self)
        self.model.setEditable(True)
        self.base_url = QLineEdit(values.base_url, self)
        self.address_label = QLabel(_tr("Address"), self)
        self.key_label = QLabel(_tr("API key"), self)
        self.key = QLineEdit(self)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.forget_button = QPushButton(_tr("Remove"), self)
        self.forget_button.setObjectName("pushButton_agent_forget_key")
        self.forget_button.setToolTip(_tr("Remove the stored key"))
        self.forget_button.clicked.connect(self._on_forget)
        self.key_link = QLabel(self)
        self.key_link.setObjectName("label_agent_key_link")
        self.key_link.setTextFormat(Qt.TextFormat.RichText)  # the one address is ours (KEY_PAGES), the text escaped
        self.key_link.setOpenExternalLinks(True)
        self.provider_test_button = QPushButton(_tr("Test"), self)
        self.provider_test_button.setObjectName("pushButton_agent_provider_test")
        self.provider_test_button.setToolTip(_tr("Send one short request to this provider, and list its models"))
        self.provider_test_button.setEnabled(provider_tester is not None)
        self.provider_test_button.clicked.connect(self._on_test_provider)
        # Ollama: where to install it when it does not answer, and a model to download when it lacks the one wanted.
        self.ollama_install_note = QLabel(self)
        self.ollama_install_note.setObjectName("label_agent_ollama_install")
        self.ollama_install_note.setTextFormat(Qt.TextFormat.RichText)  # the page is ours, the rest escaped
        self.ollama_install_note.setOpenExternalLinks(True)
        self.ollama_install_note.setWordWrap(True)
        self.ollama_refresh_button = QPushButton(_tr("Refresh"), self)
        self.ollama_refresh_button.setObjectName("pushButton_agent_ollama_refresh")
        self.ollama_refresh_button.setToolTip(_tr("Look for Ollama and the models it has installed"))
        self.ollama_refresh_button.clicked.connect(self._fetch_ollama_models)
        self.ollama_install_row = QWidget(self)
        install_layout = QHBoxLayout(self.ollama_install_row)
        install_layout.setContentsMargins(0, 0, 0, 0)
        install_layout.setSpacing(6)
        install_layout.addWidget(self.ollama_install_note, 1)
        install_layout.addWidget(self.ollama_refresh_button)
        self.ollama_download_button = QPushButton(_tr("Download"), self)
        self.ollama_download_button.setObjectName("pushButton_agent_ollama_download")
        self.ollama_download_button.setToolTip(_tr("Download this model into Ollama"))
        self.ollama_download_button.clicked.connect(self._on_download_model)
        self.ollama_progress = QProgressBar(self)
        self.ollama_progress.setObjectName("progressBar_agent_ollama_pull")
        self.ollama_progress.setTextVisible(False)
        self.ollama_cancel_button = QPushButton(_tr("Cancel"), self)
        self.ollama_cancel_button.setObjectName("pushButton_agent_ollama_cancel")
        self.ollama_cancel_button.clicked.connect(self._on_cancel_download)
        self.ollama_download_row = QWidget(self)
        download_layout = QHBoxLayout(self.ollama_download_row)
        download_layout.setContentsMargins(0, 0, 0, 0)
        download_layout.setSpacing(6)
        download_layout.addWidget(self.ollama_download_button)
        download_layout.addWidget(self.ollama_progress, 1)
        download_layout.addWidget(self.ollama_cancel_button)
        self._ollama_up = None  # None: not asked yet; False: no answer at the address; True: it lists its models
        self._ollama_installed = ()  # the chat models it listed
        self._pull_reply = None  # the download of a model, while it runs
        self._pull_model = ""
        self._pull_address = ""
        self._pull_buffer = bytearray()
        self._pull_end = None  # why it ended: "success", "failed", "cancelled", "silent" or "closing"
        self._pull_idle = QTimer(self)
        self._pull_idle.setSingleShot(True)
        self._pull_idle.setInterval(OLLAMA_PULL_IDLE_MS)
        self._pull_idle.timeout.connect(self._on_pull_idle)
        self.provider_result = QLabel(self)
        self.provider_result.setObjectName("label_agent_settings_note")
        self.provider_result.setTextFormat(Qt.TextFormat.PlainText)  # a provider words its errors: never read as HTML
        self.provider_result.setWordWrap(True)
        self.provider_result.setVisible(False)
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
        self._models_reply = None  # the request listing the models of Ollama, while it runs
        self._closing = False  # done() has begun: no new request (the address loses the focus while it hides)
        self._key_target = None  # the server the key field is for: another one starts with an empty field
        self.preset.currentIndexChanged.connect(self._on_preset)
        self.base_url.textChanged.connect(self._on_destination)
        self.base_url.editingFinished.connect(self._fetch_ollama_models)
        self._on_preset()
        self.model.setEditText(values.model)
        self.model.editTextChanged.connect(self._update_ollama_widgets)
        self._update_ollama_widgets()

        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(6)
        key_row.addWidget(self.key, 1)
        key_row.addWidget(self.forget_button)
        key_box = QVBoxLayout()
        key_box.setContentsMargins(0, 0, 0, 0)
        key_box.setSpacing(2)
        key_box.addLayout(key_row)
        key_box.addWidget(self.key_link)
        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)
        model_row.setSpacing(6)
        model_row.addWidget(self.model, 1)
        model_row.addWidget(self.provider_test_button)
        model_box = QVBoxLayout()
        model_box.setContentsMargins(0, 0, 0, 0)
        model_box.setSpacing(2)
        model_box.addLayout(model_row)
        model_box.addWidget(self.ollama_install_row)
        model_box.addWidget(self.ollama_download_row)
        model_box.addWidget(self.provider_result)
        form = QFormLayout()
        form.addRow(_tr("Provider"), self.preset)
        form.addRow(self.model_label, model_box)
        form.addRow(self.key_label, key_box)
        form.addRow(self.address_label, self.base_url)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setObjectName("pushButton_agent_settings_save")
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
        self.tool_families = QCheckBox(_tr("Offer only the tools a request needs (the agent adds the others)"), self)
        self.tool_families.setObjectName("checkBox_agent_tool_families")
        self.tool_families.setChecked(values.tool_families)
        self.tool_families.setToolTip(_tr(
            "Lighter requests: the tools that filter, read and show are always offered; the agent sees a one-line "
            "list of the others and adds those a request needs. Other applications always get every tool."))
        general_layout.addWidget(self.tool_families)
        general_layout.addWidget(line)
        general_layout.addWidget(leaving)
        general_layout.addWidget(notice)
        general_layout.addWidget(self.send_values)
        general_layout.addWidget(values_note)
        general_layout.addWidget(consent_box)
        general_layout.addStretch(1)
        self.tabs = QTabWidget(self)
        # Pages by key, for a link of the agent (show_settings_link) that opens one of them.
        self._tab_pages = {"provider": general}
        self.tabs.addTab(general, _tr("Provider"))
        self._tab_pages["sources"] = self._build_sources(values)
        self.tabs.addTab(self._tab_pages["sources"], _tr("Sources"))
        self._tab_pages["autonomy"] = self._build_autonomy(values)
        self.tabs.addTab(self._tab_pages["autonomy"], _tr("Autonomy"))
        if self._tools:
            self._tab_pages["tools"] = self._build_tools(values)
            self.tabs.addTab(self._tab_pages["tools"], _tr("Tools"))
        self._tab_pages["memory"] = self._build_memory(values)
        self.tabs.addTab(self._tab_pages["memory"], _tr("Memory"))
        self._tab_pages["other_applications"] = self._build_applications(values)
        self.tabs.addTab(self._tab_pages["other_applications"], _tr("Other applications"))
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
        self.tool_rules.setRootIsDecorated(True)
        self._rule_boxes = {}
        kinds = {0: _tr("reads"), 1: _tr("view"), 2: _tr("project"), 3: _tr("edit buffer"), 4: _tr("irreversible"),
                 5: _tr("outside")}
        # change_settings: asked like an irreversible change, but undone with the turn (words of the undo, translated)
        settings_kind = QCoreApplication.translate("AgentChat", "settings of FilterMate")
        choices = [("", _tr("As the level says")), ("ask", _tr("Always ask")), ("allow", _tr("Always allow")),
                   ("never", _tr("Never"))]
        for name, title, risk in sorted(self._tools, key=lambda row: (row[2], row[1].lower())):
            kind = settings_kind if name in ("change_settings", "apply_settings_profile") else kinds.get(risk, "")
            item = QTreeWidgetItem(self.tool_rules, [title, kind, ""])
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

    # --- the Memory tab: the notes kept from one project to the next (core/agent/memory.py) ------------------------

    def _build_memory(self, values) -> QWidget:
        """The notes for every project and for each source, written, corrected and removed here; saved with Save.

        The dialog works on a copy (``_memory_rows``) and gives the changes (``memory_changes``): they are made on the
        file as it is at that time, which another QGIS may have written meanwhile."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setSpacing(6)
        self.memory_enabled = QCheckBox(_tr("Keep notes from one project to the next"), page)
        self.memory_enabled.setObjectName("checkBox_agent_memory")
        self.memory_enabled.setChecked(bool(getattr(values, "memory", True)))
        self.keep_history = QCheckBox(_tr("Keep the requests of every project"), page)
        self.keep_history.setObjectName("checkBox_agent_keep_history")
        self.keep_history.setChecked(bool(getattr(values, "keep_request_history", True)))
        self.keep_history.setToolTip(_tr("The tab All projects of the history: what was asked, where and when, "
                                         "kept on this computer"))
        note = QLabel(_tr(
            "Notes you write here stay in a file of this computer (agent_memory.json, in the FilterMate folder of the "
            "QGIS profile). They are sent to your provider with a request: those for every project always, those of a "
            "layer when a layer of the same source is in the open project. Double-click a note to correct it."), page)
        note.setObjectName("label_agent_settings_sub")
        note.setWordWrap(True)
        self.memory_notes = QTreeWidget(page)
        self.memory_notes.setObjectName("treeWidget_agent_memory")
        self.memory_notes.setHeaderHidden(True)
        self.memory_notes.setRootIsDecorated(False)
        self.memory_notes.setWordWrap(True)
        self.memory_notes.setMinimumHeight(160)
        before = self._memory_before.notes if self._memory_before is not None else ()
        self._memory_rows = [{"id": row.id, "scope": row.scope, "signature": row.signature, "label": row.label,
                              "text": row.text, "with_values": row.with_values} for row in before]
        self.memory_place = QComboBox(page)
        self.memory_place.setObjectName("comboBox_agent_memory_place")
        self.memory_place.addItem(_tr("Every project"), "")
        seen = set()
        for signature, name in self._memory_sources:
            if signature and signature not in seen:  # a layer held in memory has no source to remember
                seen.add(signature)
                self.memory_place.addItem(name, signature)
                self.memory_place.setItemData(self.memory_place.count() - 1, plain_tooltip(signature),
                                              Qt.ItemDataRole.ToolTipRole)
        self.memory_text = QLineEdit(page)
        self.memory_text.setObjectName("lineEdit_agent_memory_text")
        self.memory_text.setMaxLength(MAX_NOTE_CHARS)
        self.memory_text.setPlaceholderText(_tr("A note, in one sentence"))
        self.memory_add = QPushButton(_tr("Add"), page)
        self.memory_add.setObjectName("pushButton_agent_memory_add")
        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)
        add_row.setSpacing(6)
        add_row.addWidget(self.memory_place)
        add_row.addWidget(self.memory_text, 1)
        add_row.addWidget(self.memory_add)
        self.memory_remove = QPushButton(_tr("Remove"), page)
        self.memory_remove.setObjectName("pushButton_agent_memory_remove")
        self.memory_forget_all = QPushButton(_tr("Forget everything"), page)
        self.memory_forget_all.setObjectName("pushButton_agent_memory_forget_all")
        self.memory_open = QPushButton(_tr("Open the file"), page)
        self.memory_open.setObjectName("pushButton_agent_memory_open")
        self.memory_open.setEnabled(bool(self._memory_file))
        self.memory_open.setToolTip(plain_tooltip(self._memory_file))
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(6)
        buttons.addWidget(self.memory_remove)
        buttons.addWidget(self.memory_forget_all)
        buttons.addStretch(1)
        buttons.addWidget(self.memory_open)
        self.memory_status = QLabel(page)
        self.memory_status.setObjectName("label_agent_settings_note")
        self.memory_status.setTextFormat(Qt.TextFormat.PlainText)  # it may quote why the file is not read
        self.memory_status.setWordWrap(True)
        layout.addWidget(self.memory_enabled)
        layout.addWidget(self.keep_history)
        layout.addWidget(note)
        layout.addWidget(self.memory_notes, 1)
        layout.addLayout(add_row)
        layout.addLayout(buttons)
        layout.addWidget(self.memory_status)
        self.memory_add.clicked.connect(self._on_memory_add)
        self.memory_text.returnPressed.connect(self._on_memory_add)
        self.memory_text.textChanged.connect(self._update_memory_buttons)
        self.memory_place.currentIndexChanged.connect(self._update_memory_buttons)
        self.memory_remove.clicked.connect(self._on_memory_remove)
        self.memory_forget_all.clicked.connect(self._on_memory_forget_all)
        self.memory_open.clicked.connect(self._on_memory_open)
        self.memory_notes.itemChanged.connect(self._on_memory_edited)
        self.memory_notes.itemSelectionChanged.connect(self._update_memory_buttons)
        self.send_values.toggled.connect(self._update_memory_status)
        self.memory_enabled.toggled.connect(self._update_memory_status)
        self._fill_memory()
        return page

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt name
        """Enter in the line of a note adds the note (``returnPressed``): it must not also reach the dialog, which
        would press Save and close with every setting."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.memory_text.hasFocus():
            event.accept()
            return
        super().keyPressEvent(event)

    @property
    def _memory_readable(self) -> bool:
        return self._memory_before is not None

    def _memory_place_full(self, signature: str) -> bool:
        there = sum(1 for row in self._memory_rows if row["signature"] == signature
                    and row["scope"] == (SCOPE_SOURCE if signature else SCOPE_USER))
        return there >= (MAX_SOURCE_NOTES if signature else MAX_USER_NOTES) or len(self._memory_rows) >= MAX_NOTES

    def _fill_memory(self) -> None:
        """The tree from the working copy: the notes for every project, then each source under its name."""
        tree = self.memory_notes
        tree.blockSignals(True)
        tree.clear()
        groups = {}
        # Every project first, then each source in the order its first note was written; a row keeps its rank.
        for rank, row in sorted(enumerate(self._memory_rows), key=lambda item: item[1]["scope"] != SCOPE_USER):
            key = row["signature"] if row["scope"] == SCOPE_SOURCE else ""
            parent = groups.get(key)
            if parent is None:
                title = _tr("Every project") if not key else f"{row['label'] or key} ({key})"
                parent = groups[key] = QTreeWidgetItem(tree, [title])
                parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
                font = parent.font(0)
                font.setBold(True)
                parent.setFont(0, font)
            item = QTreeWidgetItem(parent, [row["text"]])
            item.setData(0, Qt.ItemDataRole.UserRole, rank)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        tree.expandAll()
        tree.blockSignals(False)
        self._update_memory_buttons()
        self._update_memory_status()

    def _update_memory_buttons(self, *_args) -> None:
        readable = self._memory_readable
        signature = self.memory_place.currentData() or ""
        full = self._memory_place_full(signature)
        for widget in (self.memory_notes, self.memory_place, self.memory_text):
            widget.setEnabled(readable)
        self.memory_add.setEnabled(readable and not full and bool(self.memory_text.text().strip()))
        self.memory_add.setToolTip(_tr("This list is full: remove a note first.") if full else "")
        chosen_item = self.memory_notes.currentItem()
        self.memory_remove.setEnabled(readable and chosen_item is not None and chosen_item.parent() is not None)
        self.memory_forget_all.setEnabled(readable and bool(self._memory_rows))

    def _update_memory_status(self, *_args) -> None:
        """How many of the notes go with a request in the open project, as the chat chooses them."""
        if not self._memory_readable:
            self.memory_status.setText(_tr("The memory file cannot be read ({}). Correct it or remove it: nothing is "
                                           "written to it meanwhile.").format(self._memory_error))
            self.memory_status.setVisible(True)
            return
        notes = tuple(Note(id=row["id"] or f"new{rank}", scope=row["scope"], text=row["text"],
                           signature=row["signature"], label=row["label"], with_values=row["with_values"])
                      for rank, row in enumerate(self._memory_rows))
        selection = memory_chosen(Memory(notes=notes), self._memory_sources, self._memory_active,
                                  share_values=self.send_values.isChecked())
        text = _tr("Sent with this project: {} of {} notes.").format(selection.sent, len(notes))
        if selection.held_back:
            text += " " + _tr("{} not sent: they hold attribute values, which you do not share.").format(
                selection.held_back)
        self.memory_status.setText(text)
        # Unticked, none is sent: the count would say otherwise.
        self.memory_status.setVisible(bool(notes) and self.memory_enabled.isChecked())

    def _on_memory_add(self) -> None:
        text = " ".join(self.memory_text.text().split())[:MAX_NOTE_CHARS]
        signature = self.memory_place.currentData() or ""
        if not text or not self._memory_readable or self._memory_place_full(signature):
            return
        scope = SCOPE_SOURCE if signature else SCOPE_USER
        same = any(row["scope"] == scope and row["signature"] == signature and row["text"].casefold() == text.casefold()
                   for row in self._memory_rows)
        if not same:  # the same note at the same place is kept once
            self._memory_rows.append({"id": "", "scope": scope, "signature": signature,
                                      "label": self.memory_place.currentText() if signature else "", "text": text,
                                      "with_values": False})
        self.memory_text.clear()
        self._fill_memory()

    def _on_memory_edited(self, item, _column=0) -> None:
        rank = item.data(0, Qt.ItemDataRole.UserRole)
        if rank is None or not 0 <= rank < len(self._memory_rows):
            return
        row = self._memory_rows[rank]
        text = " ".join(item.text(0).split())[:MAX_NOTE_CHARS]
        twin = any(other is not row and other["scope"] == row["scope"] and other["signature"] == row["signature"]
                   and other["text"].casefold() == text.casefold() for other in self._memory_rows)
        if text and not twin and text != row["text"]:
            row["text"], row["with_values"] = text, False  # the user's own words now
        if item.text(0) != row["text"]:  # emptied, or the same as another note of its place: it comes back as it was
            # The item is corrected where it stands: the tree is not filled again from the signal of its own editor.
            self.memory_notes.blockSignals(True)
            item.setText(0, row["text"])
            self.memory_notes.blockSignals(False)
        self._update_memory_status()

    def _on_memory_remove(self) -> None:
        item = self.memory_notes.currentItem()
        rank = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if rank is not None and 0 <= rank < len(self._memory_rows):
            del self._memory_rows[rank]
            self._fill_memory()

    def _on_memory_forget_all(self) -> None:
        if self._memory_rows and ask_plain(self, self.windowTitle(),
                                           _tr("Forget every note kept from one project to the next?")):
            self._memory_rows = []
            self._fill_memory()

    def _on_memory_open(self) -> None:
        """The file in the application of the system for it, or its folder while no note is kept yet."""
        import os
        path = self._memory_file
        if path and not os.path.exists(path):
            path = os.path.dirname(path)
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def memory_changes(self) -> list:
        """What Save makes of the notes, as ``core.agent.memory.applied`` takes it: the notes removed, those whose text
        changed, those added. [] when the file could not be read, or nothing changed."""
        if not self._memory_readable:
            return []
        before = {note.id: note for note in self._memory_before.notes}
        kept = {row["id"] for row in self._memory_rows if row["id"]}
        changes = [(REMOVE, note_id) for note_id in before if note_id not in kept]
        changes += [(EDIT, row["id"], row["text"]) for row in self._memory_rows
                    if row["id"] in before and before[row["id"]].text != row["text"]]
        changes += [(ADD, row["scope"], row["signature"], row["label"], row["text"]) for row in self._memory_rows
                    if not row["id"]]
        return changes

    def select_tab(self, key: str) -> None:
        """Open the tab ``key`` (provider, sources, autonomy, tools, memory, other_applications); an unknown one is
        ignored."""
        page = self._tab_pages.get(key)
        if page is not None:
            self.tabs.setCurrentWidget(page)

    def tab_title(self, key: str) -> str:
        page = self._tab_pages.get(key)
        return self.tabs.tabText(self.tabs.indexOf(page)) if page is not None else ""

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
                            (KIND_WFS, "WFS"), (KIND_WMS, "WMS"), (KIND_WMTS, "WMTS"), (KIND_STAC, "STAC"), (KIND_XYZ, _tr("Basemap (XYZ)")),
                            (KIND_GEOCODER, _tr("Place search")), (KIND_OVERPASS, "OpenStreetMap (Overpass)")):
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
        groups = [(title, lambda source, key=key: source_group(source) == key) for key, title in source_group_titles()]
        for title, belongs in groups:
            group = QTreeWidgetItem(self.sources_tree, [title.upper()])
            group.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = group.font(0)
            font.setBold(True)
            font.setPointSizeF(max(font.pointSizeF() - 1, 7))
            group.setFont(0, font)
            group.setForeground(0, QColor(tokens(self.palette().window().color().lightness() < 128)["fm_text_muted"]))
            members = [source for source in self._listed() if belongs(source)]
            if not members and title == _tr("Databases of QGIS"):
                self.sources_tree.takeTopLevelItem(self.sources_tree.indexOfTopLevelItem(group))
                continue  # QGIS keeps no PostgreSQL connection: no empty group
            for source in members:
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
        return next((source for source in self._listed() if source.id == identifier), None)

    def _listed(self):
        """Every source of the tab: those of the plugin, those the user added, the databases of QGIS."""
        return all_sources(self._custom) + self._databases

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
        listed = {self.model.itemText(index) for index in range(self.model.count())}  # the former provider's list
        self.key.clear()  # typed for the former provider: it must not be sent to this one, nor stored for it
        self.model.clear()
        self.model.addItems(MODEL_SUGGESTIONS.get(name, ()))
        # The name of a model of another provider is not one of this one: Ollama would offer to download it.
        other = _belongs_to_another(typed.strip(), name) or (typed in listed and typed not in MODEL_SUGGESTIONS.get(name, ()))
        self.model.setEditText("" if other else typed)
        self.base_url.setPlaceholderText(PRESETS[name][1])
        no_key = name == "ollama"
        self.local_filtering_only.setVisible(name == "ollama")
        self.key_label.setVisible(not no_key)
        self.key.setVisible(not no_key)
        self.key_note.setVisible(not no_key)
        link = KEY_PAGES.get(name)
        self.key_link.setVisible(link is not None)
        if link is not None:
            # The text is translated, so it is escaped; the address is ours (KEY_PAGES).
            self.key_link.setText(f'<a href="{link}">{html.escape(_tr("Create a key"))}</a>')
        self._show_provider_result("")  # what the test said was about the former provider
        self._ollama_up, self._ollama_installed = None, ()  # what was known of Ollama was about another address
        self._update_ollama_widgets()
        self._on_destination()
        self._fetch_ollama_models()

    def _fetch_ollama_models(self) -> None:
        """List the models Ollama has installed, without waiting for it: the typed name stays, a missing server is
        said in the tooltip of the field."""
        if self._models_reply is not None:
            # Forgotten first: abort() says "finished" at once, and the reply must not be taken for the current one.
            reply, self._models_reply = self._models_reply, None
            reply.abort()
        if self._closing:
            return
        if self.preset.currentData() != "ollama":
            self.model.setToolTip("")
            return
        from qgis.core import QgsNetworkAccessManager
        from qgis.PyQt.QtNetwork import QNetworkRequest
        url = tags_url(self.base_url.text().strip() or PRESETS["ollama"][1])
        try:
            check_base_url(url, None)  # http(s) only: a file:// address typed here was read as it was
        except ValueError:
            self._forget_listed_models()
            self.model.setToolTip(_tr("Ollama did not list any model at {}: type the name of one.").format(
                without_credentials(self._ollama_address())))
            self._set_ollama_state(False, (), self._ollama_address())
            return
        request = QNetworkRequest(QUrl(url))
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(OLLAMA_TAGS_TIMEOUT_MS)
        reply = QgsNetworkAccessManager.instance().get(request)
        self._models_reply = reply
        # Qt keeps all of a reply until it is finished, and the timeout is one of silence: a server that never
        # stops sending is cut at the limit, not read for a minute.
        reply.downloadProgress.connect(
            lambda received, _total, answered=reply: answered.abort() if received > OLLAMA_TAGS_MAX_BYTES else None)
        reply.finished.connect(
            lambda answered=reply, address=self._ollama_address(): self._on_ollama_models(answered, address))

    def _ollama_address(self) -> str:
        """The address of Ollama as typed in the dialog (its default when empty), not the URL of one of its routes."""
        return self.base_url.text().strip().rstrip("/") or PRESETS["ollama"][1]

    def _show_provider_result(self, text: str) -> None:
        self.provider_result.setText(text)
        self.provider_result.setVisible(bool(text))

    def _on_test_provider(self) -> None:
        """Test: does this provider answer with this key and this model, and which chat models does it list?

        The tester waits for the provider, so the event loop runs: nothing else is started, and what comes back is
        dropped if the user chose another provider meanwhile. The key is typed here, and never shown."""
        if self._provider_tester is None or self._testing or self._closing or self._pull_reply is not None:
            return
        preset, model = self.preset.currentData(), self.model.currentText().strip()
        base_url, key = self.base_url.text().strip(), self.key.text().strip()
        if self.forget_key and not key and preset != "ollama":
            # The stored key was removed here: the tester would still read it, and say it answers.
            self._show_provider_result(_tr("Enter your API key first."))
            return
        self._testing = True
        self.provider_test_button.setEnabled(False)
        self._show_provider_result(_tr("Testing…"))
        QCoreApplication.processEvents()
        message, models = "", ()
        try:
            if self._close_asked is None:  # a close that came with that click: nothing is sent
                try:
                    _answers, message, models = self._provider_tester(preset, model, base_url, key)
                except Exception:  # a tester that fails is said, not raised from a slot
                    message, models = _tr("The test could not be made."), ()
        finally:
            self._testing = False
            self.provider_test_button.setEnabled(True)
        asked, self._close_asked = self._close_asked, None
        if asked is not None:  # Save, Cancel or Esc came meanwhile: it closes now
            self.done(asked)
            return
        if (self.preset.currentData(), self.base_url.text().strip(), self.key.text().strip()) != (preset, base_url, key):
            self._show_provider_result("")  # the answer is about another provider, address or key than the fields now
            return
        # A provider may echo what it was sent in its errors.
        self._show_provider_result(without_key(str(message), key))
        if models:
            typed = self.model.currentText()
            self.model.clear()
            self.model.addItems(models)
            self.model.setEditText(typed)

    def _forget_listed_models(self) -> None:
        """The models of a server listed before are not offered for one that lists none; the typed name stays."""
        typed = self.model.currentText()
        self.model.clear()
        self.model.setEditText(typed)

    def done(self, result) -> None:  # noqa: D401 - Qt name
        """Closed: a list of models still on its way must not reach a dialog that is gone.

        2026-11-13: the address loses the focus while super().done() hides the dialog, and editingFinished then
        sent a new request, answered once the dialog was deleted. None is sent once done() has begun.

        During a Test (the wait spins the event loop) it closes when the test ends: closed at once, the dialog would
        hide while the controller stays blocked in its event loop, a second dialog could be opened, and this one would save
        last. A Save during a download is refused: it would abort it and keep a model that is not there."""
        if self._testing:
            self._close_asked = result
            return
        if self._pull_reply is not None and result == QDialog.DialogCode.Accepted:
            return
        self._closing = True
        if self._models_reply is not None:
            reply, self._models_reply = self._models_reply, None
            reply.abort()
        self._end_pull("closing")  # Ollama keeps the part it got, and resumes it at the next download
        super().done(result)

    def _on_ollama_models(self, reply, address: str) -> None:
        if reply is not self._models_reply:  # replaced by a newer request, or the dialog moved on
            reply.deleteLater()
            return
        self._models_reply = None
        names, every_name, answers = [], [], False
        try:
            import json
            payload = json.loads(bytes(reply.read(OLLAMA_TAGS_MAX_BYTES) or b"").decode("utf-8", "replace") or "{}")
            names = installed_models(payload)
            every_name = installed_models(payload, limit=None)  # the list shown is cut; "is it installed?" is not
            answers = isinstance(payload, dict) and isinstance(payload.get("models"), list)  # Ollama says its models
        except Exception:  # whatever a server answers (read() gives None without a body): this is a slot
            names, every_name, answers = [], [], False
        finally:
            reply.deleteLater()
        if self.preset.currentData() != "ollama":
            return
        self._set_ollama_state(answers, every_name, address)
        if not names:
            self._forget_listed_models()
            if answers:  # Ollama is there and has no chat model: the one that fits a small GPU is proposed
                self.model.setToolTip(_tr("Ollama has no chat model yet: download one."))
                if not self.model.currentText().strip():
                    self.model.setEditText(RECOMMENDED_LOCAL_MODEL)
            else:
                self.model.setToolTip(_tr("Ollama did not list any model at {}: type the name of one.").format(
                    without_credentials(address)))
            return
        typed = self.model.currentText().strip()
        self.model.clear()
        self.model.addItems(names)
        self.model.setEditText(typed or names[0])
        self.model.setToolTip(_tr("Models installed in Ollama ({}).").format(len(names)))

    def _set_ollama_state(self, answers: bool, names, address: str) -> None:
        """What the last list said: Ollama answers or not, and which models it has. The note shows the address."""
        self._ollama_up, self._ollama_installed = bool(answers), tuple(names)
        text = html.escape(_tr("Ollama does not answer at {}: install it, start it, then Refresh.").format(
            without_credentials(address)))
        self.ollama_install_note.setText(
            f'{text} <a href="{OLLAMA_DOWNLOAD_PAGE}">{html.escape(_tr("Get Ollama"))}</a>')
        self._update_ollama_widgets()

    def _update_ollama_widgets(self, _text: str = "") -> None:
        """The install note and Refresh, the Download button, and the progress of a download: shown by what is known."""
        ollama = self.preset.currentData() == "ollama"
        pulling = self._pull_reply is not None
        wanted = self.model.currentText().strip()
        installed = {canonical_model(name) for name in self._ollama_installed}  # "llama3" is "llama3:latest"
        offer = (ollama and self._ollama_up is True and bool(wanted) and canonical_model(wanted) not in installed
                 and not pulling)
        self.ollama_install_row.setVisible(ollama and self._ollama_up is False and not pulling)
        self.ollama_download_button.setVisible(offer)
        self.ollama_progress.setVisible(ollama and pulling)
        self.ollama_cancel_button.setVisible(ollama and pulling)
        self.ollama_download_row.setVisible(offer or (ollama and pulling))

    # -- the download of a model into Ollama ---------------------------------------------------------------------

    def _on_download_model(self) -> None:
        """Download: ask first (several GB), then post to the Ollama of this dialog and follow the lines it streams."""
        model = self.model.currentText().strip()
        if (self._pull_reply is not None or self._testing or self._closing or self.preset.currentData() != "ollama"
                or not model):
            return  # a Test spins the event loop: a click let through must not start a download beside it
        url = pull_url(self.base_url.text().strip() or PRESETS["ollama"][1])
        try:
            check_base_url(url, None)  # the same address as the list, http(s) only
        except ValueError:
            self._show_provider_result(_tr("This address is not a web address."))
            return
        if not ask_plain(self, _tr("Download a model"), _tr(
                "Download {} into Ollama? A model weighs several GB: it takes a while, and the space on the disk of "
                "the computer that runs Ollama.").format(model)):
            return
        from qgis.core import QgsNetworkAccessManager
        from qgis.PyQt.QtNetwork import QNetworkRequest
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        # Only to the address typed here: a redirection is not followed.
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(OLLAMA_PULL_IDLE_MS)  # the silence limit, not a default that cuts a long download
        self._pull_model, self._pull_address, self._pull_end = model, self._ollama_address(), None
        self._pull_buffer = bytearray()
        reply = QgsNetworkAccessManager.instance().post(request, QByteArray(pull_body(model)))
        self._pull_reply = reply
        reply.readyRead.connect(self._on_pull_data)
        reply.finished.connect(lambda answered=reply: self._on_pull_finished(answered))
        self._pull_idle.start()
        self.ollama_progress.setRange(0, 0)  # busy until a size is known
        for widget in (self.preset, self.model, self.base_url, self.provider_test_button, self.save_button):
            widget.setEnabled(False)  # Save too: it would abort the download and keep a model that is not there
        self._show_provider_result(_tr("Downloading {}…").format(model))
        self._update_ollama_widgets()

    def _on_cancel_download(self) -> None:
        self._end_pull("cancelled", _tr("Download cancelled."))

    def _on_pull_idle(self) -> None:
        self._end_pull("silent", _tr("Ollama sent nothing for {} seconds: the download was stopped.").format(
            OLLAMA_PULL_IDLE_MS // 1000))

    def _end_pull(self, why: str, message: str = "") -> None:
        """Stop the download for ``why``; its reply finishes, and ``_on_pull_finished`` puts the dialog back."""
        reply = self._pull_reply
        if reply is None or self._pull_end is not None:
            return
        self._pull_end = why
        self._pull_idle.stop()
        if message:
            self._show_provider_result(message)
        reply.abort()

    def _on_pull_data(self) -> None:
        reply = self._pull_reply
        if reply is None or self._pull_end is not None:
            return
        self._pull_idle.start()
        self._feed_pull(bytes(reply.readAll()))

    def _feed_pull(self, data: bytes, last: bool = False) -> None:
        """Take what came of the stream: every complete line says where the download is."""
        self._pull_buffer.extend(data)
        *lines, rest = bytes(self._pull_buffer).split(b"\n")
        self._pull_buffer = bytearray(rest)
        if last and rest.strip():
            lines.append(rest)
            self._pull_buffer = bytearray()
        for line in lines:
            if self._pull_end is not None:
                return
            if not line.strip():
                continue
            try:
                progress = pull_progress(line)
            except PullError as exc:
                self._end_pull("failed", _tr("Ollama could not download {}: {}").format(
                    self._pull_model, exc.error.message))
                return
            if progress is not None:
                self._show_pull_progress(*progress)
        if len(self._pull_buffer) > OLLAMA_PULL_MAX_LINE:  # no end of line in a megabyte: not a stream of Ollama
            self._end_pull("failed", _tr("The answer of Ollama could not be read."))

    def _show_pull_progress(self, status: str, received: int, total: int) -> None:
        if status == "success":
            self._end_pull("success", _tr("{} is downloaded.").format(self._pull_model))
            return
        if total > 0:
            self.ollama_progress.setRange(0, PULL_PERMILLE)
            self.ollama_progress.setValue(received * PULL_PERMILLE // total)
            detail = _tr("{} of {}").format(_size_text(received), _size_text(total))
        else:
            self.ollama_progress.setRange(0, 0)
            detail = status
        self._show_provider_result(_tr("Downloading {}: {}").format(self._pull_model, detail))

    def _on_pull_finished(self, reply) -> None:
        if reply is not self._pull_reply:  # not the current download: forgotten
            reply.deleteLater()
            return
        from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
        if self._pull_end is None:  # it ended by itself: what is left of the stream may say why
            try:
                self._feed_pull(bytes(reply.readAll()), last=True)
            except Exception:  # whatever came: this is a slot
                self._pull_end = "failed"
                self._show_provider_result(_tr("The answer of Ollama could not be read."))
            if self._pull_end is None:
                self._pull_end = "failed"
                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    self._show_provider_result(_tr("The download ended before its end."))
                elif isinstance(status, int) and status >= 400:
                    self._show_provider_result(_tr("Ollama refused the download of {}.").format(self._pull_model))
                elif isinstance(status, int) and status >= 300:  # a redirection is not followed: not a download
                    self._show_provider_result(_tr("The download of {} failed.").format(self._pull_model))
                elif isinstance(status, int) and status > 0:  # answered, then the stream was cut
                    self._show_provider_result(_tr("The connection to Ollama was lost during the download of {}.")
                                               .format(self._pull_model))
                else:
                    self._show_provider_result(_tr("Ollama could not be reached at {}.").format(
                        without_credentials(self._pull_address)))
        self._pull_idle.stop()
        self._pull_reply = None
        self._pull_buffer = bytearray()
        reply.deleteLater()
        for widget in (self.preset, self.model, self.base_url, self.save_button):
            widget.setEnabled(True)
        self.provider_test_button.setEnabled(self._provider_tester is not None)
        if self._pull_end == "success" and not self._closing:
            self._ollama_installed += (self._pull_model,)  # installed, whatever the next list says
            self.model.setEditText(self._pull_model)
            self._fetch_ollama_models()  # the list now has it
        self._update_ollama_widgets()

    def _on_destination(self, _text: str = "") -> None:
        """A key and a consent are for one server: another one starts without them."""
        target = self.chosen_target()
        if self._key_target is not None and target != self._key_target:
            self.key.clear()  # typed for another server: it must not be sent to this one, nor stored for it
        self._key_target = target
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
        return self.model.currentText().strip()
