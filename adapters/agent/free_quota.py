# -*- coding: utf-8 -*-
"""The access token of the free quota: asked for once, kept for that relay.

Not the secret a provider key is: it is worth a small monthly quota and can be replaced by asking again. It is kept in
the settings so that trying the agent never asks for the master password of QGIS.
"""
from __future__ import annotations

import json

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent.providers.base import check_base_url
from .bounded_http import HttpFailure, fetch

_STORED_AT = "filter_mate/agent/free_token"
_STORED_FOR = "filter_mate/agent/free_token_target"
_PREFIX = "fmq1."
MAX_TOKEN = 300
MAX_ANSWER = 4096
TIMEOUT_MS = 20_000


class FreeQuotaError(RuntimeError):
    """No token could be had; the message is for the user."""


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentChat", text)


def forget_token() -> None:
    settings = QgsSettings()
    settings.remove(_STORED_AT)
    settings.remove(_STORED_FOR)


def _ask(url: str) -> str:
    try:
        reply = fetch(f"{url}/v1/register", body=b"{}", headers={"Content-Type": "application/json"}, max_bytes=MAX_ANSWER,
                      timeout_ms=TIMEOUT_MS)
    except HttpFailure as exc:
        raise FreeQuotaError(_tr("The free quota could not be reached: {}").format(exc)) from None
    if reply.status == 429:
        raise FreeQuotaError(_tr("Too many new accounts from this address today: try again tomorrow, or enter your own API key."))
    if reply.status != 200:
        raise FreeQuotaError(_tr("The free quota is unavailable for now."))
    try:
        token = json.loads(bytes(reply.content).decode("utf-8")).get("token")
    except (ValueError, AttributeError, RecursionError):
        token = None
    if not isinstance(token, str) or not token.startswith(_PREFIX) or len(token) > MAX_TOKEN or not token.isascii():
        raise FreeQuotaError(_tr("The free quota is unavailable for now."))
    return token


def token_for(url: str) -> str:
    """The token of this relay, asked for on first use.

    Raises:
        FreeQuotaError: With the reason.
        ValueError: The address would send a token in clear.
    """
    settings = QgsSettings()
    stored = str(settings.value(_STORED_AT, "") or "")
    if stored and str(settings.value(_STORED_FOR, "") or "") == url:
        return stored
    check_base_url(url, "a token")  # refused in clear over a network, as the requests that would follow are
    token = _ask(url)
    settings.setValue(_STORED_AT, token)
    settings.setValue(_STORED_FOR, url)
    return token
