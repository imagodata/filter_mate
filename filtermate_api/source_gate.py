# -*- coding: utf-8 -*-
"""The Sources tab of the agent settings, enforced on the REST API.

The chat does not offer the tools of the sources the user did not tick; the REST API (and through it the MCP
server) reached Overpass, Copernicus and Meta anyway (audit of 2026-11-24, decided with the user: align). These
endpoints refuse with 403 when no source of their kind is ticked. The ``check_*`` probes stay open: the Sources
tab tests a server before it is ticked.
"""
from __future__ import annotations

import logging
from typing import Optional, Set

logger = logging.getLogger("FilterMate.SourceGate")


def refused_for(kinds: Set[str], required_kind: str, label: str) -> Optional[str]:
    """Why this platform family is not allowed, None when a source of its kind is ticked. Pure (unit tests)."""
    if required_kind in kinds:
        return None
    return (f"No {label} source is ticked in the Sources tab of the agent settings: "
            f"tick one there first.")


def open_data_refusal(required_kind: str, label: str) -> Optional[str]:
    """``refused_for`` on the kinds the user ticked; None too when the settings cannot be read (logged).

    Unreadable settings must not brick the API: the gate is a consent of the user, and an unreadable one is
    the same process failing, not a refusal.
    """
    try:
        try:
            from ..adapters.agent.settings import load_settings
        except ImportError:
            from adapters.agent.settings import load_settings
        try:
            from ..core.agent.sources import all_sources, custom_from_json, enabled
        except ImportError:
            from core.agent.sources import all_sources, custom_from_json, enabled
        values = load_settings()
        kinds = {source.kind for source in enabled(all_sources(custom_from_json(values.custom_sources)),
                                                   values.enabled_sources)}
    except Exception as exc:
        logger.warning(f"Ticked sources unreadable, open data allowed: {exc}")
        return None
    return refused_for(kinds, required_kind, label)
