# -*- coding: utf-8 -*-
"""The postures of the agent the user picks under the line of the chat (S1): one axis, three positions.

Ask/Plan/Act (``modes``) and the Autonomy tab (``permissions``) made two axes the user had to cross:
nobody knew why a confirmation was asked. A posture is one choice that sets both at once:

- ``RESPOND`` (Répondre): answers and reads, changes nothing (Ask at the advisor level);
- ``PROPOSE`` (Proposer): shows each change before applying it, even an allowed tool;
- ``ACT`` (Agir): follows the level and the tool rules saved in the settings.

Pure: no QGIS. The legacy mode strings (``ask``/``plan``/``act``) are still what the settings
store, so an older version reads the same key: ``posture_from_mode`` migrates them on load.
"""
from __future__ import annotations

from .modes import ACT as MODE_ACT
from .modes import ASK, PLAN
from .permissions import ADVISOR, CAREFUL

RESPOND = "respond"
PROPOSE = "propose"
ACT = "act"
POSTURES = (RESPOND, PROPOSE, ACT)
DEFAULT_POSTURE = ACT

PROPOSE_NOTE = ("Posture chosen by the user for this request: Propose. Read what the request needs, describe each "
                "change before calling its tool, and let the confirmation card ask the user for each action. "
                "A refusal changes nothing: respect it and do not try another tool to do the same thing. "
                "Do not wait for a separate Go: each change is approved separately before it runs.")

# The legacy mode each posture runs the request with (core/agent/modes.py).
_POSTURE_MODES = {RESPOND: ASK, PROPOSE: PLAN, ACT: MODE_ACT}

# The level of autonomy a posture runs at; None means the saved level of the Autonomy tab.
# Respond reads only (advisor); Propose shows each change before applying it (careful);
# Act keeps what the user chose in the settings.
_POSTURE_LEVELS = {RESPOND: ADVISOR, PROPOSE: CAREFUL, ACT: None}


def posture_or_default(posture) -> str:
    """``posture`` when it is one of ``POSTURES``, else ``DEFAULT_POSTURE``."""
    text = str(posture or "").strip().lower()
    return text if text in POSTURES else DEFAULT_POSTURE


def posture_from_mode(mode) -> str:
    """The posture a saved legacy mode (``ask``/``plan``/``act``) migrates to on load."""
    from .modes import mode_or_default

    return {ASK: RESPOND, PLAN: PROPOSE, MODE_ACT: ACT}[mode_or_default(mode)]


def posture_to_mode(posture: str) -> str:
    """The legacy mode a posture runs the request with (``modes``)."""
    return _POSTURE_MODES[posture_or_default(posture)]


def posture_level(posture: str):
    """The level of autonomy a posture runs at, or None for the saved level (Act)."""
    return _POSTURE_LEVELS[posture_or_default(posture)]


def is_posture(value) -> bool:
    """Whether ``value`` unambiguously names a posture (``respond``/``propose``).

    ``act`` names both the posture and the legacy mode, with the same behavior either way,
    so callers map it through ``posture_or_default`` without needing this check.
    """
    return str(value or "").strip().lower() in (RESPOND, PROPOSE)
