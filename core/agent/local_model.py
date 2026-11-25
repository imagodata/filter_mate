# -*- coding: utf-8 -*-
"""Whether the model of the agent runs on this computer (2026-11-24): the welcome says so, as a reason to choose it."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

_CLOUD_MODEL_RE = re.compile(r"(^|[^a-z0-9])cloud([^a-z0-9]|$)", re.IGNORECASE)


def runs_on_this_computer(preset: str, base_url: str = "", model: str = "") -> bool:
    """A model of Ollama at its usual address (http://localhost:11434) or at another local one.

    An Ollama reached at the address of another computer is not local: what it reads leaves this one. A cloud
    model served through a local Ollama is not local either: the banner promises nothing is sent to an AI
    service, so it fails closed (audit of 2026-11-24). Every other preset is a service on the network.
    """
    if preset != "ollama":
        return False
    if model and _CLOUD_MODEL_RE.search(model):
        return False
    address = (base_url or "").strip()
    if not address:
        return True
    try:
        host = (urlsplit(address if "://" in address else f"http://{address}").hostname or "")
    except ValueError:
        return False
    host = host.lower().rstrip(".")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False  # not an IP literal at all ("127.0.0.1.evil.example" failed open before)
