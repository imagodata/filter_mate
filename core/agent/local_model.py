# -*- coding: utf-8 -*-
"""Whether the model of the agent runs on this computer (2026-11-24): the welcome says so, as a reason to choose it."""
from __future__ import annotations

from urllib.parse import urlsplit

_LOCAL_HOSTS = ("localhost", "::1")


def runs_on_this_computer(preset: str, base_url: str = "") -> bool:
    """A model of Ollama at its usual address (http://localhost:11434) or at another local one.

    An Ollama reached at the address of another computer is not local: what it reads leaves this one. Every other
    preset is a service on the network.
    """
    if preset != "ollama":
        return False
    address = (base_url or "").strip()
    if not address:
        return True
    try:
        host = (urlsplit(address if "://" in address else f"http://{address}").hostname or "").lower()
    except ValueError:
        return False
    return host in _LOCAL_HOSTS or host.startswith("127.")
