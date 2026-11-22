# -*- coding: utf-8 -*-
"""The modes of the agent a user picks under the line of the chat: Ask, Plan, Act (2026-11-22).

Ask answers and reads, Plan writes the steps it would take and waits for the user's Go, Act does it. Ask and Plan run
at the advisor level whatever the Autonomy tab says (only the tools that read run: ``permissions.ADVISOR``); Act runs at
the level of the Autonomy tab. The mode of a request is told to the model in the context of the request, beside the
level, and only when it changes. Pure: no QGIS.
"""
from __future__ import annotations

from .permissions import ADVISOR

ASK = "ask"
PLAN = "plan"
ACT = "act"
MODES = (ASK, PLAN, ACT)
DEFAULT_MODE = ACT

_NOTES = {
    ASK: ("Mode chosen by the user for this request: Ask. Answer; read the project with the reading tools when the "
          "answer needs it; change nothing (every change is refused in this mode). When the user asks for a change, "
          "say how it would be done and that the Act mode does it."),
    PLAN: ("Mode chosen by the user for this request: Plan. Read what the plan needs with the reading tools, then "
           "write the plan and stop: a short numbered list of the steps, each with the tool it uses and the layers it "
           "changes, and what you will ask the user on the way. Change nothing (every change is refused in this mode). "
           "The user starts the plan with a Go button: it then runs in the Act mode, and you carry out these steps."),
}


def mode_or_default(mode) -> str:
    """``mode`` when it is one of ``MODES``, else ``DEFAULT_MODE`` (a value of an older or damaged setting)."""
    text = str(mode or "").strip().lower()
    return text if text in MODES else DEFAULT_MODE


def level_for(mode: str, level: str) -> str:
    """The level of autonomy a request of ``mode`` runs at: the advisor level for Ask and Plan, ``level`` for Act."""
    return ADVISOR if mode_or_default(mode) in (ASK, PLAN) else level


def mode_note(mode: str) -> str:
    """What the model is told of the mode of the request; "" for Act, the way it always worked."""
    return _NOTES.get(mode_or_default(mode), "")
