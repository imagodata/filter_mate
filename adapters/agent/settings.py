# -*- coding: utf-8 -*-
"""The settings of the agent, and its API key in the authentication database of QGIS.

The key is never written in a settings or configuration file.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsSettings
from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent.mcp_server import DEFAULT_PORT
from ...core.agent.permissions import DEFAULT_LEVEL, clean_rules, level_or_default
from ...core.agent.providers import FREE_PRESET, FREE_QUOTA_URL, PRESETS
from ...core.agent.providers.ollama_chat import native_base
from ...core.agent.providers.base import ProviderConfig

logger = logging.getLogger("FilterMate.agent")

_PREFIX = "filter_mate/agent/"
_METHOD = "Basic"
_KEY_FIELD = "password"
_AUTH_NAME = "FilterMate agent key"
DEFAULT_PRESET = "anthropic"
MAX_TOKENS = 16000


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentChat", text)


class KeyStoreError(RuntimeError):
    """The key could not be stored or read; the message is for the user."""


def free_quota_url() -> str:
    """Where the free quota is, "" when none is offered. ``APP.OPTIONS.AGENT.free_quota_url`` overrides the release."""
    override = ""
    try:
        from ...config import config
        section = config.ENV_VARS.get("CONFIG_DATA", {}).get("APP", {}).get("OPTIONS", {}).get("AGENT", {})
        override = str(config._get_option_value(section.get("free_quota_url"), "") or "").strip()
    except Exception:  # the free quota is an offer, not a dependency
        logger.debug("free_quota_url unreadable", exc_info=True)
    return (override or FREE_QUOTA_URL).rstrip("/")


OLLAMA_PRESET = "ollama"


def target_of(preset: str, base_url: str) -> str:
    """The server a key and a consent are for."""
    if preset == FREE_PRESET:
        return free_quota_url()
    target = base_url.strip().rstrip("/") or PRESETS[preset][1]
    # The same Ollama server, through its own API or its OpenAI-compatible one (the usual address up to 5.1).
    return native_base(target) if preset == OLLAMA_PRESET else target


@dataclass(frozen=True)
class AgentSettings:
    """What the user chose. ``base_url`` empty means the usual address of the preset."""

    preset: str = DEFAULT_PRESET
    model: str = ""
    base_url: str = ""
    consent: bool = False
    send_values: bool = True
    # Sources the agent may use (core.agent.sources) and the ones the user added, as JSON. None enabled by default.
    enabled_sources: Tuple[str, ...] = ()
    custom_sources: str = "[]"
    authcfg: str = ""
    # Where the consent was given and the key was typed for: neither follows a change of provider.
    consent_target: str = ""
    key_target: str = ""
    # The MCP server of the plugin: off until the user turns it on. The token is not the paid key of a provider: it is
    # copied in the configuration of the client anyway, and reading it must not ask for the master password at startup.
    mcp_enabled: bool = False
    mcp_port: int = DEFAULT_PORT
    mcp_token: str = field(default="", repr=False)
    # Expert mode: the agent may run Python code in QGIS, shown in full and confirmed at each run. Off by default.
    expert_python: bool = False
    # How far the agent of the chat goes alone (core.agent.permissions); "standard" asks before files and the network.
    autonomy: str = DEFAULT_LEVEL
    # Only the filtering tools for a model of Ollama (core.agent.tool_catalog.FILTERING_TOOLS), for a slow computer.
    local_filtering_only: bool = False
    # Exceptions of the Tools tab, as JSON {tool: "ask" | "allow" | "never"}: they override the level for that tool.
    tool_rules: str = "{}"

    @property
    def rules(self) -> dict:
        try:
            return clean_rules(json.loads(self.tool_rules or "{}"))
        except (ValueError, RecursionError):
            return {}

    @property
    def needs_key(self) -> bool:
        return self.preset not in ("ollama", FREE_PRESET)

    @property
    def target(self) -> str:
        return target_of(self.preset, self.base_url)

    @property
    def has_consent(self) -> bool:
        stored = native_base(self.consent_target) if self.preset == OLLAMA_PRESET else self.consent_target
        return self.consent and bool(self.target) and stored == self.target

    @property
    def has_key(self) -> bool:
        return bool(self.authcfg) and self.key_target == self.target

    @property
    def ready(self) -> bool:
        """Complete enough to send a request (the key itself is only read when one is sent)."""
        return self.has_consent and bool(self.model) and (self.has_key or not self.needs_key)


def _enabled_sources(settings) -> Tuple[str, ...]:
    raw = settings.value(_PREFIX + "enabled_sources", "")
    if not raw:  # the single switch of the first version
        return ("datagouv", "opendatasoft") if settings.value(_PREFIX + "open_data", False, type=bool) else ()
    try:
        value = json.loads(str(raw))
    except (ValueError, RecursionError):
        return ()
    return tuple(str(item) for item in value) if isinstance(value, list) else ()


def _port(value) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1024 <= port <= 65535 else DEFAULT_PORT


def load_settings() -> AgentSettings:
    settings = QgsSettings()
    preset = str(settings.value(_PREFIX + "preset", DEFAULT_PRESET) or DEFAULT_PRESET)
    return AgentSettings(
        preset=preset if preset in PRESETS else DEFAULT_PRESET,
        model=str(settings.value(_PREFIX + "model", "") or ""),
        base_url=str(settings.value(_PREFIX + "base_url", "") or ""),
        consent=settings.value(_PREFIX + "consent", False, type=bool),
        send_values=settings.value(_PREFIX + "send_values", True, type=bool),
        enabled_sources=_enabled_sources(settings),
        custom_sources=str(settings.value(_PREFIX + "custom_sources", "[]") or "[]"),
        authcfg=str(settings.value(_PREFIX + "authcfg", "") or ""),
        consent_target=str(settings.value(_PREFIX + "consent_target", "") or ""),
        key_target=str(settings.value(_PREFIX + "key_target", "") or ""),
        mcp_enabled=settings.value(_PREFIX + "mcp_enabled", False, type=bool),
        mcp_port=_port(settings.value(_PREFIX + "mcp_port", DEFAULT_PORT)),
        mcp_token=str(settings.value(_PREFIX + "mcp_token", "") or ""),
        expert_python=settings.value(_PREFIX + "expert_python", False, type=bool),
        local_filtering_only=settings.value(_PREFIX + "local_filtering_only", False, type=bool),
        autonomy=level_or_default(str(settings.value(_PREFIX + "autonomy", DEFAULT_LEVEL) or "")),
        tool_rules=str(settings.value(_PREFIX + "tool_rules", "{}") or "{}"))


def save_settings(values: AgentSettings) -> None:
    settings = QgsSettings()
    settings.setValue(_PREFIX + "preset", values.preset)
    settings.setValue(_PREFIX + "model", values.model)
    settings.setValue(_PREFIX + "base_url", values.base_url)
    settings.setValue(_PREFIX + "consent", values.consent)
    settings.setValue(_PREFIX + "send_values", values.send_values)
    settings.setValue(_PREFIX + "expert_python", values.expert_python)
    settings.setValue(_PREFIX + "local_filtering_only", values.local_filtering_only)
    settings.setValue(_PREFIX + "enabled_sources", json.dumps(list(values.enabled_sources)))
    settings.setValue(_PREFIX + "custom_sources", values.custom_sources)
    settings.setValue(_PREFIX + "authcfg", values.authcfg)
    settings.setValue(_PREFIX + "consent_target", values.consent_target)
    settings.setValue(_PREFIX + "key_target", values.key_target)
    settings.setValue(_PREFIX + "mcp_enabled", values.mcp_enabled)
    settings.setValue(_PREFIX + "mcp_port", values.mcp_port)
    settings.setValue(_PREFIX + "mcp_token", values.mcp_token)
    settings.setValue(_PREFIX + "autonomy", level_or_default(values.autonomy))
    settings.setValue(_PREFIX + "tool_rules", json.dumps(values.rules, sort_keys=True))


def _auth_manager():
    manager = QgsApplication.authManager()
    if manager is None or manager.isDisabled():
        raise KeyStoreError(_tr("The QGIS authentication database is not available."))
    if not manager.setMasterPassword(True):
        raise KeyStoreError(_tr("The QGIS master password is needed to use the stored key."))
    return manager


def store_key(key: str, authcfg: str = "") -> str:
    """Store ``key``, replacing the one of ``authcfg`` if any; the id to keep in the settings.

    Raises:
        KeyStoreError: With the reason.
    """
    manager = _auth_manager()
    config = QgsAuthMethodConfig(_METHOD)
    config.setName(_AUTH_NAME)
    config.setConfig("username", "filtermate-agent")
    config.setConfig(_KEY_FIELD, key)
    if authcfg and authcfg in manager.configIds():
        config.setId(authcfg)
        result = manager.updateAuthenticationConfig(config)
        if result is False or (isinstance(result, tuple) and not result[0]):
            raise KeyStoreError(_tr("The key could not be stored."))
        return authcfg
    result = manager.storeAuthenticationConfig(config)
    stored = result[1] if isinstance(result, tuple) and len(result) > 1 else config
    ok = result[0] if isinstance(result, tuple) else result
    if not ok or not stored.id():
        raise KeyStoreError(_tr("The key could not be stored."))
    return stored.id()


def read_key(authcfg: str) -> str:
    """The stored key, "" when there is none.

    Raises:
        KeyStoreError: The database is locked or unavailable.
    """
    if not authcfg:
        return ""
    manager = _auth_manager()
    if authcfg not in manager.configIds():
        return ""
    config = QgsAuthMethodConfig()
    result = manager.loadAuthenticationConfig(authcfg, config, True)
    if isinstance(result, tuple):
        ok, config = result[0], result[1]
    else:
        ok = result
    if not ok:
        raise KeyStoreError(_tr("The stored key could not be read."))
    return config.config(_KEY_FIELD)


def delete_key(authcfg: str) -> None:
    if authcfg:
        manager = _auth_manager()
        if authcfg in manager.configIds():
            manager.removeAuthenticationConfig(authcfg)


def provider_config(values: AgentSettings, key: Optional[str]) -> ProviderConfig:
    kind, base_url = PRESETS[values.preset]
    if values.preset == FREE_PRESET:
        url = free_quota_url()
        if not url:  # an empty address means the official API to a provider, which must never see this token
            raise ValueError(_tr("The free quota is not available."))
        return ProviderConfig(kind=kind, model=values.model, base_url=url, api_key=key or "", max_tokens=MAX_TOKENS)
    return ProviderConfig(kind=kind, model=values.model, base_url=values.base_url or base_url, api_key=key or "",
                          max_tokens=MAX_TOKENS)
