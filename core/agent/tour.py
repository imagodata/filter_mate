# -*- coding: utf-8 -*-
"""How FilterMate works, told in the AGENT thread with no model: what each section does, how a section leaves the
panel for its own panel of QGIS, is grouped with another one and comes back, and where the buttons are.

Plain Python, no QGIS: from what the panel shows now (``DockFacts``), the paragraphs to say and the links to offer,
in the order they come. The words are in ui/controllers/welcome_tour.py. Nothing here is read by a model nor sent
anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

SECTIONS = ("exploring", "filtering", "exporting", "agent", "configuration")
MAY_BE_OFF = ("filtering", "exporting")  # APP.OPTIONS.<SECTION>.enabled; without AGENT there is no thread to tell it in
TEXT, LINK = "text", "link"


@dataclass(frozen=True)
class DockFacts:
    """What the panel shows now."""

    off: Tuple[str, ...] = ()  # the sections turned off, among MAY_BE_OFF
    # Each stack lists its sections in a rail of chips (ui/widgets/section_rail.py); False with the headers stacked
    # one above the other (APP.DOCKWIDGET.SECTION_HEADERS), which is told with the word "header".
    rail: bool = False
    panels: bool = False  # a section can be shown in its own panel of QGIS (ui/layout/section_panels.py)
    apart: Tuple[str, ...] = ()  # the sections that are in their own panel
    can_move: bool = False  # one more section can leave the panel
    model_ready: bool = False  # a provider is connected


def steps(facts: DockFacts) -> List[Tuple[str, str]]:
    """``(kind, key)`` in the order told: ``TEXT`` a paragraph, ``LINK`` a button that does what was just said.

    A section turned off is not described: one line names those that are, and the setup that brings them back.
    The links move the sections only when there is something to move."""
    told: List[Tuple[str, str]] = [(TEXT, "intro")]
    if facts.rail:
        told.append((TEXT, "rail"))
    told += [(TEXT, key) for key in SECTIONS if key not in facts.off]
    if any(key in MAY_BE_OFF for key in facts.off):
        told.append((TEXT, "off"))
    if facts.panels:
        told += [(TEXT, "panels" if facts.rail else "panels_headers"),
                 (TEXT, "groups" if facts.rail else "groups_headers")]
        if facts.can_move:
            told.append((LINK, "detach_all"))
        if facts.apart:
            told.append((LINK, "attach_all"))
    told += [(TEXT, "buttons"), (LINK, "setup")]
    if not facts.model_ready:
        told.append((LINK, "connect"))
    return told
