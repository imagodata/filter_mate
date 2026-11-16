# -*- coding: utf-8 -*-
"""The options of the agent turned on or off from the agent itself: the sources and connectors ticked, the MCP
server of the plugin, the provider among those set up (2026-11-16).

Plain Python. The menu of the AGENT panel and the tools of the chat change them the same way
(ui/controllers/agent_chat_controller.py, apply_agent_options). Turning off only narrows what the agent reaches;
turning on widens it, and is asked to the user (core/agent/permissions.py). A key, the consent to send data to a
provider, the autonomy and the rules of the tools are never changed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .sources import Source, source_group

MAX_PROVIDERS = 8


@dataclass(frozen=True)
class ProviderEntry:
    """A provider set up by the user: its key stays in the authentication database of QGIS (``authcfg``)."""

    preset: str
    model: str
    base_url: str
    authcfg: str = ""
    consent_target: str = ""
    key_target: str = ""

    @property
    def label(self) -> str:
        return f"{self.preset} · {self.model}"

    def same(self, other: "ProviderEntry") -> bool:
        return (self.preset, self.model, self.base_url) == (other.preset, other.model, other.base_url)


@dataclass(frozen=True)
class Change:
    """What to change: sources to tick and to untick, the MCP server (None: unchanged), another provider."""

    sources_on: Tuple[str, ...] = ()
    sources_off: Tuple[str, ...] = ()
    mcp_server: Optional[bool] = None
    provider: Optional[ProviderEntry] = None


def remember(entries: Sequence[ProviderEntry], entry: ProviderEntry, keep: int = MAX_PROVIDERS) -> Tuple[ProviderEntry, ...]:
    """``entry`` first, then the others (an older copy of it left out), ``keep`` at most."""
    return ((entry,) + tuple(other for other in entries if not other.same(entry)))[:keep]


def forget(entries: Sequence[ProviderEntry], entry: ProviderEntry) -> Tuple[ProviderEntry, ...]:
    return tuple(other for other in entries if not other.same(entry))


def options_view(sources: Sequence[Source], enabled_ids: Sequence[str], providers: Sequence[ProviderEntry],
                 current: ProviderEntry, mcp_on: bool) -> Dict[str, Any]:
    """What agent_options answers."""
    on = set(enabled_ids)
    return {"provider": current.label, "providers": [entry.label for entry in providers],
            "sources": [{"id": source.id, "title": source.title, "group": source_group(source), "on": source.id in on}
                        for source in sources],
            "mcp_server": mcp_on}


def _known(sources: Sequence[Source], ids: Sequence[str]) -> List[str]:
    names = {source.id for source in sources}
    missing = [source_id for source_id in ids if source_id not in names]
    if missing:
        raise ValueError(f"No source {', '.join(missing)}: use the ids agent_options lists.")
    return list(dict.fromkeys(ids))


def plan_off(sources: Sequence[Source], enabled_ids: Sequence[str], ids: Sequence[str],
             mcp_server: Optional[bool]) -> Tuple[Change, Dict[str, Any]]:
    """The sources to untick among ``ids`` (those ticked) and the MCP server to stop (``False``)."""
    if mcp_server not in (None, False):
        raise ValueError("mcp_server: false to stop the MCP server here; turn_on_agent_options starts it.")
    wanted = _known(sources, ids)
    off = tuple(source_id for source_id in wanted if source_id in enabled_ids)
    answer: Dict[str, Any] = {"turned_off": list(off), "already": [source_id for source_id in wanted if source_id not in off]}
    if mcp_server is False:
        answer["mcp_server"] = False
    return Change(sources_off=off, mcp_server=mcp_server), answer


def plan_on(sources: Sequence[Source], enabled_ids: Sequence[str], ids: Sequence[str], mcp_server: Optional[bool],
            provider_label: str, providers: Sequence[ProviderEntry],
            current: ProviderEntry) -> Tuple[Change, Dict[str, Any]]:
    """The sources to tick among ``ids`` (those not ticked), the MCP server to start (``True``), a provider among
    those set up to switch to (``provider_label``)."""
    if mcp_server not in (None, True):
        raise ValueError("mcp_server: true to start the MCP server here; turn_off_agent_options stops it.")
    wanted = _known(sources, ids)
    on = tuple(source_id for source_id in wanted if source_id not in enabled_ids)
    answer: Dict[str, Any] = {"turned_on": list(on), "already": [source_id for source_id in wanted if source_id not in on]}
    provider = None
    if provider_label:
        provider = next((entry for entry in providers if entry.label == provider_label), None)
        if provider is None:
            raise ValueError(f"No provider {provider_label} set up: the user adds one in the Provider tab of the agent "
                             "settings (its key and consent are theirs to give).")
        if provider.same(current):
            provider = None
            answer["already"].append(provider_label)
        else:
            answer["provider"] = provider_label
    if mcp_server is True:
        answer["mcp_server"] = True
    return Change(sources_on=on, mcp_server=mcp_server, provider=provider), answer


def apply_change(enabled_ids: Tuple[str, ...], change: Change) -> Tuple[str, ...]:
    """The ids ticked once ``change`` is made: their order kept, the new ones at the end."""
    kept = tuple(source_id for source_id in enabled_ids if source_id not in change.sources_off)
    return kept + tuple(source_id for source_id in change.sources_on if source_id not in kept)
