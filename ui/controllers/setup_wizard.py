# -*- coding: utf-8 -*-
"""The setup of FilterMate in the AGENT thread, with no model: cards of choices, then the settings before and after.

The steps and what each answer sets are plain Python (core/agent/setup_wizard.py); here are their words, the cards
of the thread, and what follows Apply. The setup applies its settings itself, outside any request and outside the
history of the agent (a model never undoes them): a link puts them back. Nothing is sent to any provider.

One answer is not a setting: where the sections go, all in the FilterMate panel or each in its own panel of QGIS
(ui/layout/section_panels.py). It shows on the same card, moves with Apply, and comes back with the same link.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any, Dict, List, Optional

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
            "profile": _tr("Panel"), "language": _tr("Language"), "panels": _tr("Layout"),
            "headers": _tr("Headers"),
            "action_bar": _tr("Buttons"),
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
        "panels": _tr("Where the sections go"),
        "headers": _tr("How the panel lists its sections"),
        "action_bar": _tr("Where the action buttons go (Filter, Export...)"),
        "after": _tr("When you filter"),
        "targets": _tr("A vector layer also filters these layers (cut to its features)"),
        "groups": _tr("When you export to a file, keep the groups of the layer tree"),
        "raster_format": _tr("Format of the rasters exported"),
        "point_cloud_format": _tr("Format of the point clouds exported"),
    }


def _labels(facts: wizard.ProjectFacts, stacked: bool = False) -> Dict[str, Dict[str, tuple]]:
    """Per question, per choice: (label, description). ``stacked``: the panel lists its sections by headers, not
    by rails, which the words of the default layout follow."""

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
        "panels": {
            wizard.IN_DOCK: (_tr("All in the FilterMate panel"),
                             _tr("A click on a header opens its section.") if stacked
                             else _tr("The default: one panel, where a click in a rail opens a section.")),
            wizard.IN_PANELS: (_tr("Each in its own panel of QGIS"),
                               _tr("AGENT, FILTERING, EXPORTING and CONFIGURATION beside the map, as tabs or "
                                   "floating; EXPLORING stays in FilterMate. A right-click on the title of a panel "
                                   "groups it with another one or merges it back.")),
            wizard.AS_NOW: (_tr("As they are now"), _tr("Some sections are in their own panel.")),
        },
        "headers": {
            "rail": (_tr("A rail of chips"), _tr("The default: one row per stack, where a click on a chip opens "
                                                 "its section and a chip is dragged to another place.")),
            "stacked": (_tr("Headers, one above the other"), _tr("The name of each section on its own line.")),
        },
        "action_bar": {"bottom": (_tr("Bottom"), ""), "top": (_tr("Top"), ""), "left": (_tr("Left"), ""),
                       "right": (_tr("Right"), ""),
                       "sections": (_tr("Under each section"), _tr("Each section shows its own buttons while it "
                                                                   "is open."))},
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


def wait_for_chat(chat: Any) -> bool:
    """A request runs, or another application is changing the project: said, and nothing is to be done now."""
    if chat.chat_busy():
        chat._say(QCoreApplication.translate("AgentChat", "Wait for the end of the request, then try again."),
                  error=True)
        return True
    if getattr(getattr(chat, "_mcp", None), "busy", False):
        chat._say(QCoreApplication.translate("AgentChat", "Another application is changing the project: try "
                                             "again in a moment."))
        return True
    return False


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
        # What each Apply changed, the last one last: {"rows": the settings set, "moved": where the sections were
        # before it moved them ({"apart", "kept"}; None: it moved none), "done": put back}. Each has its own link.
        self._changes: List[dict] = []

    @property
    def running(self) -> bool:
        return self._card is not None

    def forget(self) -> None:
        """The thread was emptied: its cards went with it."""
        self._card = self._apply_card = None

    def offer_back_again(self) -> None:
        """The thread was emptied for another project: the settings are those of every project, so the link that
        puts back what the last setup changed comes back in it. One link: those of earlier setups would all read
        the same, and what they set was set again since."""
        change = next((item for item in reversed(self._changes) if not item["done"]), None)
        if change is not None:
            self._add_back_link(change)

    def _add_back_link(self, change: dict) -> None:
        self._chat.panel.add_link(_tr("Put my settings back as they were"), lambda: self.revert(change))

    def _wait(self) -> bool:
        return wait_for_chat(self._chat)

    def start(self) -> None:
        from ...adapters.agent import plugin_settings
        self._close_card()
        self._values = plugin_settings.current_values(wizard.PATHS)
        self._answers, self._done = wizard.Answers(), []
        self._facts = replace(project_facts(), layout=self._layout_now())
        self._chat.panel.add_note(_tr("Set up FilterMate: a few choices, ticked as your settings are now. Nothing "
                                      "is sent anywhere, and nothing changes until you apply."))
        self._next()

    def _panels(self) -> Any:
        """The sections of the panel that can go to their own panels (ui/layout/section_panels.py); None without."""
        return getattr(getattr(self._chat, "_parent_widget", None), "_fm_panels", None)

    def _layout_now(self) -> str:
        """Where the sections are: all in the panel, all apart, or some of each; "" when none can move."""
        panels = self._panels()
        if panels is None:
            return ""
        try:
            from ..layout.section_panels import DETACHABLE
            apart = panels.detached()
            movable = any(panels.can_detach(key) for key in DETACHABLE)
        except Exception:
            logger.debug("Setup: the panels of the sections were not read", exc_info=True)
            return ""
        if not apart:
            return wizard.IN_DOCK if movable else ""
        return wizard.AS_NOW if movable else wizard.IN_PANELS

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
        sections = getattr(getattr(self._chat, "_parent_widget", None), "_fm_sections", None)
        headers, texts = _headers(), _questions()
        labels = _labels(self._facts, bool(getattr(sections, "stacked", False)))
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
        layout = wizard.layout_wanted(self._facts, self._answers)
        try:
            rows = plan(plugin_settings.settings_rows(), changes, by_user=True) if changes else []
        except ValueError as exc:  # a setting of the setup missing from this configuration
            logger.warning(f"Setup: settings not planned: {exc}")
            self._chat.panel.add_note(_tr("These settings could not be prepared: change them in the configuration "
                                          "of the panel."))
            return
        rows = [row for row in rows if row["before"] != row["after"]]
        if not rows and layout is None:
            self._chat.panel.add_note(_tr("Nothing to change: FilterMate already works this way."))
            self._follow_up()
            return
        texts = {"heading": _tr("Your settings of FilterMate"),
                 "note": _tr("They stay for every project; the link that follows puts them back as they were."),
                 "apply": _tr("Apply"), "cancel": _tr("Cancel"),
                 "accepted": _tr("Applied."), "declined": _tr("Not applied: nothing changed.")}
        lines = self._chat._lines_of(rows)
        if layout == wizard.IN_PANELS:
            lines.append(_tr("Sections: each in its own panel of QGIS (applied at once)"))
        elif layout == wizard.IN_DOCK:
            lines.append(_tr("Sections: all back in the FilterMate panel (applied at once)"))
        card = self._chat.panel.add_settings_card(texts, lines, "")
        card.apply_requested.connect(lambda: self._apply(card, rows, layout))
        card.cancel_requested.connect(lambda: self._cancel(card))
        self._apply_card = card
        self._chat._settings_cards.append(card)

    def _cancel(self, card) -> None:
        self._apply_card = None
        card.finish(False)

    def _apply(self, card, rows, layout: Optional[str] = None) -> None:
        """Apply clicked: the settings set as shown, by the user, then the sections moved. Not a step of the agent:
        a model never undoes it, and the settings of the agent itself go back with the link that follows."""
        if self._wait():
            return
        # Where the sections are, read first: a setting that turns a section off brings it back from its panel.
        before = self._sections_now() if layout is not None else None
        applied = self._set(rows, "before", "after") if rows else []
        if applied is None:  # the settings could not be applied (said): nothing else is done
            self._apply_card = None
            card.finish(False)
            return
        # The settings first: a section they turn off shows nowhere, a section they turn on can leave the panel.
        moved = self._move_sections(layout, before) if before is not None else None
        self._apply_card = None
        if not applied and moved is None:
            card.finish(False)
            return
        card.finish(True)
        change = {"rows": [dict(row) for row in applied], "moved": moved, "done": False}
        self._changes.append(change)
        self._add_back_link(change)
        self._follow_up(apart=layout == wizard.IN_PANELS and moved is not None)

    def revert(self, change: Optional[dict] = None) -> bool:
        """The link after Apply: the sections back where they were, the settings that Apply set put back, those
        changed since left as they are. Each link puts back its own Apply (the last one when none is named): the
        link of a first setup used to put back what a second one had set."""
        if change is None:
            change = next((item for item in reversed(self._changes) if not item["done"]), None)
        if change is None:
            return False
        if change["done"]:
            self._chat.panel.add_note(_tr("These settings were already put back."))
            return False
        if self._wait():
            return False
        rows, moved = change["rows"], change["moved"]
        # The settings first, as Apply did: a section they turn on again can go back to its panel.
        done = bool(rows) and bool(self._set(rows, "after", "before"))
        if moved is not None:
            done = self._restore_sections(moved) or done
        change["done"] = True  # once it was tried to its end: a link that failed half way can be clicked again
        if done:
            self._chat.panel.add_note(_tr("Settings put back as they were."))
        return done

    def _sections_now(self) -> Optional[dict]:
        """Where the sections are: those in their own panel, and those kept as apart for the next time (one that
        is turned off goes back to its panel the day it is turned on). None when they cannot move."""
        panels = self._panels()
        if panels is None:
            return None
        try:
            kept = getattr(panels, "kept_apart", None)
            apart = tuple(panels.detached())
            return {"apart": apart, "kept": tuple(kept()) if callable(kept) else apart}
        except Exception:
            logger.debug("Setup: the panels of the sections were not read", exc_info=True)
            return None

    def _move_sections(self, layout: str, before: dict) -> Optional[dict]:
        """Every section in its own panel, or all back in FilterMate. ``before`` (where they were when Apply was
        clicked) to put them back; None when nothing moved and nothing kept as apart changed."""
        panels = self._panels()
        if panels is None:
            return None
        try:
            if layout == wizard.IN_PANELS:
                panels.detach_all()
            else:
                panels.attach_all()
        except Exception:
            logger.exception("Setup: the sections could not be moved")
            return None
        self._keep_thread_in_view()
        return before if self._sections_now() != before else None

    def _restore_sections(self, before: dict) -> bool:
        """The sections apart as they were before Apply, and what was kept as apart then; True when it changed."""
        panels = self._panels()
        if panels is None:
            return False
        now = self._sections_now()
        try:
            for key in panels.detached():
                if key not in before["apart"]:
                    panels.attach(key)
            for key in before["apart"]:
                if key not in panels.detached():
                    panels.detach(key)
            keep = getattr(panels, "keep_apart", None)
            if callable(keep):  # a section turned off meanwhile is not kept as apart unless it was
                keep(before["kept"])
        except Exception:
            logger.exception("Setup: the sections could not be put back")
        self._keep_thread_in_view()
        return self._sections_now() != now

    def _keep_thread_in_view(self) -> None:
        """AGENT moved with the others: its thread, where the setup goes on, comes forward, once Qt has laid
        the panels out (a panel that just moved still reads as where it was)."""
        show = getattr(self._chat, "_show_agent_soon", None) or getattr(self._chat, "_show_agent", None)
        if callable(show):
            try:
                show()
            except Exception:
                logger.debug("Setup: the AGENT section was not brought forward", exc_info=True)

    def _set(self, rows, was: str, to: str) -> Optional[List[dict]]:
        """Set each row from its ``was`` value to its ``to`` value; the rows changed since are left out (said).
        The rows set (none when they all changed since); None when they could not be applied (said too)."""
        from ...adapters.agent import plugin_settings
        now = plugin_settings.current_values([row["path"] for row in rows])
        kept = [row for row in rows if now.get(row["path"]) == row[was]]
        if len(kept) < len(rows):
            self._chat.panel.add_note(_tr("Some of these settings changed since: they are left as they are."))
        if not kept:
            return []
        try:
            plugin_settings.apply_values({row["path"]: row[to] for row in kept})
        except RuntimeError as exc:  # the configuration was put back as it was
            logger.warning(f"Setup: settings not applied: {exc}")
            self._chat.panel.add_note(_tr("Nothing changed: the settings could not be applied."))
            return None
        return kept

    @staticmethod
    def _where(path: str) -> str:
        """Where the configuration of the panel shows a setting."""
        from ...adapters.agent import plugin_settings
        from ...core.agent.settings_reference import get
        try:
            return str(get(plugin_settings.settings_rows(), path)["where"])
        except Exception:
            return path

    def _follow_up(self, apart: bool = False) -> None:
        """What comes after: where the sections and the source layer went, how FilterMate works, a model to
        connect or to refine the setup with."""
        from .welcome_tour import title as tour_title
        sections = wizard.kept_sections(self._values, self._answers)
        panel = self._chat.panel
        if apart:
            panel.add_note(_tr("Each section is in its own panel of QGIS: drag one by its title, right-click the "
                               "title to group it with another one, as tabs, or to merge it back into FilterMate."))
        if self._values.get(wizard.FILTERING_ON) is not False and "filtering" not in sections:
            panel.add_note(_tr("FILTERING is hidden: the source layer is chosen at the top of EXPLORING. To show "
                               "it again: this setup, or {}.").format(self._where(wizard.FILTERING_ON)))
        if self._values.get(wizard.AGENT_ON) is not False and "agent" not in sections:
            panel.add_note(_tr("The AGENT section goes after restarting QGIS. To bring it back: {}.").format(
                self._where(wizard.AGENT_ON)))
            panel.add_link(tour_title(), self._chat.show_tour)
            return
        panel.add_link(tour_title(), self._chat.show_tour)
        from ...adapters.agent.settings import load_settings
        if load_settings().ready:
            panel.add_link(_tr("Refine the setup with the agent"), self._chat.start_model_setup)
        else:
            panel.add_link(_tr("Connect a model to filter from a sentence"),
                           lambda: self._chat.open_settings(tab="provider"))
