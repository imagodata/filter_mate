# -*- coding: utf-8 -*-
"""The MCP connectors the user enabled, as entries of ``load_skill`` named ``connector-<id of the source>``.

The chat lists them next to the skills; loading one asks the user the first time, then offers its tools (the
families of tools do the same for ours). No Qt here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple
from urllib.parse import urlsplit

from .skills import CONNECTOR_PREFIX, MAX_DESCRIPTION, MAX_TITLE, hidden_character
from .sources import Source

PREFIX = CONNECTOR_PREFIX
# A source the user added keeps no note: this one stands for it, so the model sees where the entry comes from.
USER_ADDED = "a connector the user added"


@dataclass(frozen=True)
class ConnectorEntry:
    name: str
    line: str
    source: Source


def entry_name(source: Source) -> str:
    return PREFIX + source.id


def _bounded(text: str, limit: int) -> str:
    """``text`` as one item of the list of load_skill: ``;`` parts the items, so it becomes ``,``."""
    return text.replace(";", ",").strip()[:limit]


def _title(source: Source) -> str:
    """The title the user gave, unless one of its characters does not show: the host of the address stands for it."""
    if not source.title.strip() or hidden_character(source.title) is not None:
        try:
            host = urlsplit(source.address).hostname
        except ValueError:
            host = None
        return host or source.id
    return source.title


def entry_line(source: Source) -> str:
    """``"<title>: <note>"``, as the description of load_skill lists the entry; bounded like a skill's."""
    note = _bounded(source.note, MAX_DESCRIPTION) if source.note.strip() else USER_ADDED
    return f"{_bounded(_title(source), MAX_TITLE)}: {note}"


def connector_entries(sources: Iterable[Source]) -> Tuple[ConnectorEntry, ...]:
    """The connectors among ``sources``, in the order given (the platforms are not entries)."""
    return tuple(ConnectorEntry(entry_name(source), entry_line(source), source)
                 for source in sources if source.is_connector)
