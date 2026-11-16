# -*- coding: utf-8 -*-
"""How FilterMate works, in the AGENT thread, with no model: a paragraph per section, how the sections go to their
own panels of QGIS, are grouped and merged back, where the buttons are, and links that do it.

What is told and in which order is plain Python (core/agent/tour.py); here are the words, and what the links do.
Nothing is sent to any provider and nothing is kept in the conversation: a model never reads it.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent import tour

logger = logging.getLogger("FilterMate")


def _tr(text: str) -> str:
    return QCoreApplication.translate("WelcomeTour", text)


def title() -> str:
    """The name of the tour: on the welcome of AGENT, in its menu, in Vector > FilterMate, after the setup."""
    return _tr("How FilterMate works")


def _texts(off: str) -> Dict[str, str]:
    return {
        "intro": _tr("How FilterMate works, section by section. No AI model is needed to read this, and nothing "
                     "is sent anywhere."),
        "exploring": _tr("EXPLORING holds the current layer and what you pick in it: features of a vector layer, a "
                         "range of values or classes of a raster, classes or heights of a point cloud. The other "
                         "sections work on what it selects."),
        "filtering": _tr("FILTERING filters the layers you tick by that selection: those that intersect it, lie "
                         "within a distance of it... Filter applies, Undo and Redo walk the history, Compare shows "
                         "the map before and after, Unfilter removes the filters."),
        "exporting": _tr("EXPORTING writes the layers as they are filtered: GeoPackage, Shapefile, KML, GeoTIFF, "
                         "LAZ..."),
        "agent": _tr("AGENT does the same from a sentence, and more (styles, labels, data to bring in), with a "
                     "model you connect: your own API key, or Ollama on this computer. Each request can be undone."),
        "configuration": _tr("CONFIGURATION lists every setting. Set up FilterMate asks the main ones with a few "
                             "choices, and shows each setting before and after."),
        "off": _tr("Turned off in your settings: {}. Set up FilterMate brings a section back.").format(off),
        "panels": _tr("A section can leave this panel. Right-click the header of AGENT, FILTERING, EXPORTING or "
                      "CONFIGURATION, then choose to open it in its own panel: it becomes a panel of QGIS, to drag "
                      "beside the map, to tab with the Layers panel or to float on another screen. EXPLORING stays "
                      "here: it holds the layer the other sections work on."),
        "groups": _tr("Right-click the title of such a panel to group it with another one, as tabs, or to merge "
                      "it back into FilterMate. Closing it merges it back too. QGIS puts every panel back where "
                      "you left it."),
        "buttons": _tr("The buttons act in their own section: Filter, Undo, Redo, Compare and Unfilter with "
                       "FILTERING, Export with EXPORTING. A section in its own panel takes its buttons with it; the "
                       "setup can also show them under each section."),
    }


def _links() -> Dict[str, str]:
    return {
        # The words of the menu of a section header (ui/layout/section_panels.py): one translation for both.
        "detach_all": QCoreApplication.translate("SectionPanels", "Open every section in its own panel"),
        "attach_all": QCoreApplication.translate("SectionPanels", "Merge every section back into FilterMate"),
        "setup": _tr("Set up FilterMate"),
        "connect": _tr("Connect a model"),
    }


class WelcomeTour:
    """The tour, in the thread of ``chat`` (the AgentChatController)."""

    def __init__(self, chat: Any) -> None:
        self._chat = chat

    def _dock(self) -> Any:
        return getattr(self._chat, "_parent_widget", None)

    def _panels(self) -> Any:
        return getattr(self._dock(), "_fm_panels", None)

    def facts(self) -> tour.DockFacts:
        """What the panel shows now; a panel that cannot be read shows everything, in one piece."""
        from ...adapters.agent.settings import load_settings
        sections = getattr(self._dock(), "_fm_sections", None)
        shown = getattr(sections, "section_shown", None)
        off, apart, can_move = (), (), False
        panels = self._panels()
        try:
            if callable(shown):
                off = tuple(key for key in tour.MAY_BE_OFF if shown(key) is False)
            if panels is not None:
                apart = tuple(panels.detached())
                can_move = any(panels.can_detach(key) for key in tour.SECTIONS)
        except Exception:
            logger.debug("Tour: the sections of the panel were not read", exc_info=True)
        try:
            ready = bool(load_settings().ready)
        except Exception:
            ready = False
        return tour.DockFacts(off=off, panels=panels is not None, apart=apart, can_move=can_move, model_ready=ready)

    def show(self) -> bool:
        """Tell it in the thread. False while a request runs: its answer is being written there."""
        chat = self._chat
        if chat.chat_busy():
            chat._say(QCoreApplication.translate("AgentChat", "Wait for the end of the request, then try again."),
                      error=True)
            return False
        facts = self.facts()
        texts = _texts(", ".join(key.upper() for key in facts.off))
        labels = _links()
        runs: Dict[str, Callable[[], Any]] = {
            "detach_all": lambda: self._move(apart=True), "attach_all": lambda: self._move(apart=False),
            "setup": chat.start_setup, "connect": lambda: chat.open_settings(tab="provider"),
        }
        panel = chat.panel
        for kind, key in tour.steps(facts):
            if kind == tour.LINK:
                panel.add_link(labels[key], runs[key])
            else:
                panel.add_text(texts[key])
                panel.end_answer()  # each paragraph on its own
        return True

    def _move(self, apart: bool) -> bool:
        """Every section in its own panel, or all back in FilterMate; AGENT, where this is read, stays in view."""
        panels = self._panels()
        if panels is None:
            return False
        try:
            if apart:
                panels.detach_all()
            else:
                panels.attach_all()
        except Exception:
            logger.exception("Tour: the sections could not be moved")
            return False
        chat = self._chat
        show = getattr(chat, "_show_agent", None)
        if callable(show):
            show()
        return True
