# -*- coding: utf-8 -*-
"""The setup of FilterMate in the AGENT thread, with no model: cards of choices, then the settings before and after.

The steps and what each answer sets are plain Python (core/agent/setup_wizard.py); here are their words, the cards
of the thread, and what follows Apply. The change is applied as a card of the agent is (undoable, a step of the
history of its own), outside any request: nothing is sent to any provider.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent import setup_wizard as wizard
from ...core.agent.questions import Option, Question

logger = logging.getLogger("FilterMate")


def _tr(text: str) -> str:
    return QCoreApplication.translate("SetupWizard", text)


# The native names of the languages of the plugin, as a language chooser shows them.
LANGUAGE_NAMES = {"en": "English", "fr": "Français", "de": "Deutsch", "es": "Español", "it": "Italiano",
                  "nl": "Nederlands", "pt": "Português", "pl": "Polski", "zh": "中文", "ru": "Русский",
                  "id": "Bahasa Indonesia", "vi": "Tiếng Việt", "tr": "Türkçe", "hi": "हिन्दी", "fi": "Suomi",
                  "da": "Dansk", "sv": "Svenska", "nb": "Norsk bokmål", "sl": "Slovenščina", "tl": "Tagalog",
                  "am": "አማርኛ", "uz": "Oʻzbek"}


def _headers() -> Dict[str, str]:
    return {"sections": _tr("Sections"), "data": _tr("Data"), "size": _tr("Size"), "theme": _tr("Theme"),
            "profile": _tr("Panel"), "language": _tr("Language"), "action_bar": _tr("Buttons"),
            "after": _tr("Filtering"), "targets": _tr("Targets"), "groups": _tr("Groups"),
            "raster_format": _tr("Rasters"), "point_cloud_format": _tr("Clouds")}


def _questions() -> Dict[str, str]:
    return {
        "sections": _tr("Which sections of the panel do you use? EXPLORING is always there."),
        "data": _tr("Which data do you work with, besides vector layers?"),
        "size": _tr("How big are your layers, most of the time?"),
        "theme": _tr("Colours of the panel"),
        "profile": _tr("Size of the panel"),
        "language": _tr("Language of the panel"),
        "action_bar": _tr("Where the action buttons go (Filter, Export...)"),
        "after": _tr("When you filter"),
        "targets": _tr("A vector layer also filters these layers (cut to its features)"),
        "groups": _tr("When you export to a file, keep the groups of the layer tree"),
        "raster_format": _tr("Format of the rasters exported"),
        "point_cloud_format": _tr("Format of the point clouds exported"),
    }


def _labels(facts: wizard.ProjectFacts) -> Dict[str, Dict[str, tuple]]:
    """Per question, per choice: (label, description)."""

    def in_project(count: int) -> str:
        return _tr("{} in this project").format(count) if count else ""

    return {
        "sections": {
            "filtering": ("FILTERING", _tr("Filter layers by the features selected in EXPLORING. Off: the "
                                                "source layer is chosen at the top of EXPLORING.")),
            "exporting": ("EXPORTING", _tr("Export layers to files (GeoPackage, Shapefile, KML...), "
                                                "QFieldCloud.")),
            "agent": ("AGENT", _tr("Filter from a sentence, with a model you connect. Without a model it "
                                        "keeps this setup.")),
        },
        "data": {
            "rasters": (_tr("Rasters (images, DEMs)"), in_project(facts.rasters)),
            "point_clouds": (_tr("Point clouds (LiDAR)"), in_project(facts.point_clouds)),
            "postgres": (_tr("PostgreSQL / PostGIS"), in_project(facts.postgres)),
            "web": (_tr("Web services (WFS, WMS)"), in_project(facts.web)),
        },
        "size": {
            "small": (_tr("Small: under 10,000 features"), _tr("A shorter wait while you type an expression.")),
            "medium": (_tr("Medium: up to 100,000"), _tr("The usual settings.")),
            "large": (_tr("Large: 100,000 features or more"), _tr("Longer timeouts, fewer warnings.")),
            "keep": (_tr("Keep my settings"), ""),
        },
        "theme": {"auto": (_tr("As QGIS"), ""), "light": (_tr("Light"), ""), "dark": (_tr("Dark"), ""),
                  "default": (_tr("FilterMate"), "")},
        "profile": {"auto": (_tr("Fit to the screen"), ""), "compact": (_tr("Compact (small screen)"), ""),
                    "normal": (_tr("Normal"), ""), "hidpi": (_tr("Large (4K, Retina)"), "")},
        "language": {"auto": (_tr("As QGIS"), "")},
        "action_bar": {"bottom": (_tr("Bottom"), ""), "top": (_tr("Top"), ""), "left": (_tr("Left"), ""),
                       "right": (_tr("Right"), "")},
        "after": {"zoom": (_tr("Zoom to what is kept"), ""),
                  "history": (_tr("Keep the history of filters in the project"), ""),
                  "hints": (_tr("Show optimization tips"), ""),
                  "auto": (_tr("Let FilterMate choose the fastest way"), "")},
        "targets": {"rasters": (_tr("Rasters"), ""), "point_clouds": (_tr("Point clouds"), "")},
        "groups": {"gpkg": (_tr("In a GeoPackage"), ""), "kml": (_tr("In a KML"), "")},
        "raster_format": {"COG": (_tr("Cloud Optimized GeoTIFF"), ""), "GTiff": (_tr("GeoTIFF"), "")},
        "point_cloud_format": {"LAZ": (_tr("LAZ (compressed)"), ""), "LAS": (_tr("LAS"), ""),
                               "COPC": (_tr("COPC (cloud optimized)"), "")},
    }


def project_facts() -> wizard.ProjectFacts:
    """How many layers of each kind the open project holds; none when it cannot be read."""
    try:
        import qgis.core as core
        point_cloud_class = getattr(core, "QgsPointCloudLayer", None)  # QGIS 3.18 and later
        rasters = point_clouds = postgres = web = 0
        for layer in core.QgsProject.instance().mapLayers().values():
            provider = (layer.providerType() or "").lower()
            if provider in ("wms", "wfs", "oapif", "arcgismapserver", "arcgisfeatureserver", "wcs", "xyz"):
                web += 1
            elif provider in ("postgres", "postgresraster"):
                postgres += 1
            elif point_cloud_class is not None and isinstance(layer, point_cloud_class):
                point_clouds += 1
            elif isinstance(layer, core.QgsRasterLayer):
                rasters += 1
        return wizard.ProjectFacts(rasters=rasters, point_clouds=point_clouds, postgres=postgres, web=web)
    except Exception:
        logger.debug("Setup: the layers of the project were not counted", exc_info=True)
        return wizard.ProjectFacts()


class SetupWizard:
    """One setup at a time in the thread of ``chat`` (the AgentChatController): a card per step, then the change."""

    def __init__(self, chat: Any) -> None:
        self._chat = chat
        self._card = None  # the card waiting for an answer
        self._values: Dict[str, Any] = {}
        self._answers = wizard.Answers()
        self._done: List[str] = []
        self._facts = wizard.ProjectFacts()
        self._apply_card = None  # the card of the change, until Apply or Cancel
        self._applied: List[dict] = []  # the rows the last Apply set: what "put back" restores

    @property
    def running(self) -> bool:
        return self._card is not None

    def forget(self) -> None:
        """The thread was emptied: its cards went with it."""
        self._card = self._apply_card = None

    def start(self) -> None:
        from ...adapters.agent import plugin_settings
        self._close_card()
        self._values = plugin_settings.current_values(wizard.PATHS)
        self._answers, self._done = wizard.Answers(), []
        self._facts = project_facts()
        self._chat.panel.add_note(_tr("Set up FilterMate: a few choices, ticked as your settings are now. Nothing "
                                      "is sent anywhere, and nothing changes until you apply."))
        self._next()

    def _close_card(self) -> None:
        for card in (self._card, self._apply_card):
            if card is not None:
                try:
                    card.finish(False)
                except RuntimeError:  # it went with the thread
                    pass
        self._card = self._apply_card = None

    def _next(self) -> None:
        step = wizard.next_step(self._done, self._values, self._answers)
        if step is None:
            self._propose()
            return
        asks = wizard.step_questions(step, self._values, self._facts, self._answers)
        headers, texts, labels = _headers(), _questions(), _labels(self._facts)
        questions, keys_by_label = [], []
        for ask in asks:
            words = labels.get(ask.key, {})
            options, by_label = [], {}
            for choice in ask.choices:
                label, description = words.get(choice.key) or (self._other_label(ask.key, choice.key), "")
                options.append(Option(label, description, choice.selected))
                by_label[label] = choice.key
            questions.append(Question(headers[ask.key], texts[ask.key], tuple(options), ask.multi))
            keys_by_label.append((ask.key, by_label))
        more = wizard.next_step([*self._done, step], self._values, self._answers) is not None
        card_texts = {"answer": _tr("Next") if more else _tr("See the changes"),
                      "close": _tr("Stop the setup"), "other": "", "no_answer": _tr("Setup stopped.")}
        card = self._chat.panel.add_question_card(card_texts, questions, free_other=False)
        card.answered.connect(lambda chosen, step=step, keys=keys_by_label: self._answered(step, keys, chosen))
        card.declined.connect(self._declined)
        self._card = card

    @staticmethod
    def _other_label(question: str, key: str) -> str:
        if question == "language":
            return LANGUAGE_NAMES.get(key, key)
        return key

    def _answered(self, step: str, keys, chosen) -> None:
        self._card = None
        self._answers.record(step, {key: [by_label[label] for label in labels if label in by_label]
                                    for (key, by_label), (labels, _other) in zip(keys, chosen)})
        self._done.append(step)
        self._next()

    def _declined(self) -> None:
        self._card = None
        self._chat.panel.add_note(_tr("Setup stopped: nothing changed. Menu Vector > FilterMate starts it again."))

    def _propose(self) -> None:
        from ...adapters.agent import plugin_settings
        from ...core.agent.settings_reference import plan
        changes = wizard.changes(self._values, self._answers)
        try:
            rows = plan(plugin_settings.settings_rows(), changes, by_user=True) if changes else []
        except ValueError as exc:  # a setting of the setup missing from this configuration
            logger.warning(f"Setup: settings not planned: {exc}")
            self._chat.panel.add_note(_tr("These settings could not be prepared: change them in the configuration "
                                          "of the panel."))
            return
        rows = [row for row in rows if row["before"] != row["after"]]
        if not rows:
            self._chat.panel.add_note(_tr("Nothing to change: FilterMate already works this way."))
            self._follow_up()
            return
        texts = {"heading": _tr("Your settings of FilterMate"),
                 "note": _tr("They stay for every project; the link that follows puts them back as they were."),
                 "apply": _tr("Apply"), "cancel": _tr("Cancel"),
                 "accepted": _tr("Applied."), "declined": _tr("Not applied: nothing changed.")}
        card = self._chat.panel.add_settings_card(texts, self._chat._lines_of(rows), "")
        card.apply_requested.connect(lambda: self._apply(card, rows))
        card.cancel_requested.connect(lambda: self._cancel(card))
        self._apply_card = card
        self._chat._settings_cards.append(card)

    def _cancel(self, card) -> None:
        self._apply_card = None
        card.finish(False)

    def _apply(self, card, rows) -> None:
        """Apply clicked: the settings set as shown, by the user. Not a step of the agent: a model never undoes it,
        and the settings of the agent itself go back with the link that follows."""
        if self._chat.chat_busy():
            self._chat._say(QCoreApplication.translate("AgentChat", "Wait for the end of the request, then try "
                                                       "again."), error=True)
            return
        if not self._set(rows, "before", "after"):
            self._apply_card = None
            card.finish(False)
            return
        self._apply_card = None
        card.finish(True)
        self._applied = [dict(row) for row in rows]
        self._chat.panel.add_link(_tr("Put my settings back as they were"), self.revert)
        self._follow_up()

    def revert(self) -> bool:
        """The link after Apply: the settings the setup set put back, those changed since left as they are."""
        rows, self._applied = self._applied, []
        if not rows:
            return False
        if self._chat.chat_busy():
            self._applied = rows
            self._chat._say(QCoreApplication.translate("AgentChat", "Wait for the end of the request, then try "
                                                       "again."), error=True)
            return False
        if self._set(rows, "after", "before"):
            self._chat.panel.add_note(_tr("Settings put back as they were."))
            return True
        return False

    def _set(self, rows, was: str, to: str) -> bool:
        """Set each row from its ``was`` value to its ``to`` value; the rows changed since are left out (said)."""
        from ...adapters.agent import plugin_settings
        now = plugin_settings.current_values([row["path"] for row in rows])
        kept = [row for row in rows if now.get(row["path"]) == row[was]]
        if len(kept) < len(rows):
            self._chat.panel.add_note(_tr("Some of these settings changed since: they are left as they are."))
        if not kept:
            return False
        try:
            plugin_settings.apply_values({row["path"]: row[to] for row in kept})
        except RuntimeError as exc:  # the configuration was put back as it was
            logger.warning(f"Setup: settings not applied: {exc}")
            self._chat.panel.add_note(_tr("Nothing changed: the settings could not be applied."))
            return False
        return True

    @staticmethod
    def _where(path: str) -> str:
        """Where the configuration of the panel shows a setting."""
        from ...adapters.agent import plugin_settings
        from ...core.agent.settings_reference import get
        try:
            return str(get(plugin_settings.settings_rows(), path)["where"])
        except Exception:
            return path

    def _follow_up(self) -> None:
        """What comes after: where the source layer went, a model to connect or to refine the setup with."""
        sections = wizard.kept_sections(self._values, self._answers)
        panel = self._chat.panel
        if self._values.get(wizard.FILTERING_ON) is not False and "filtering" not in sections:
            panel.add_note(_tr("FILTERING is hidden: the source layer is chosen at the top of EXPLORING. To show "
                               "it again: this setup, or {}.").format(self._where(wizard.FILTERING_ON)))
        if self._values.get(wizard.AGENT_ON) is not False and "agent" not in sections:
            panel.add_note(_tr("The AGENT section goes after restarting QGIS. To bring it back: {}.").format(
                self._where(wizard.AGENT_ON)))
            return
        from ...adapters.agent.settings import load_settings
        if load_settings().ready:
            panel.add_link(_tr("Refine the setup with the agent"), self._chat.start_model_setup)
        else:
            panel.add_link(_tr("Connect a model to filter from a sentence"),
                           lambda: self._chat.open_settings(tab="provider"))
