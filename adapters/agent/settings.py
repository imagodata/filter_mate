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

from ...core.agent.agent_options import ProviderEntry
from ...core.agent.mcp_server import DEFAULT_PORT
from ...core.agent.permissions import DEFAULT_LEVEL, clean_rules, level_or_default
from ...core.agent.providers import PRESETS
from ...core.agent.providers.ollama_chat import native_base
from ...core.agent.providers.base import ProviderConfig
from ...core.agent.providers.effort import valid_effort

logger = logging.getLogger("FilterMate.agent")

_PREFIX = "filter_mate/agent/"
_METHOD = "Basic"
_KEY_FIELD = "password"
_AUTH_NAME = "FilterMate agent key"
_KEY_USER = "filtermate-agent"  # the user name FilterMate sets on the configurations it makes
DEFAULT_PRESET = "anthropic"
MAX_TOKENS = 16000


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentChat", text)


class KeyStoreError(RuntimeError):
    """The key could not be stored or read; the message is for the user."""


OLLAMA_PRESET = "ollama"


def target_of(preset: str, base_url: str) -> str:
    """The server a key and a consent are for."""
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
    # Families of tools (core/agent/families.py): the tools of a task offered once its skill is loaded. On by default
    # since lot A (the connectors come the same way); saved under its own key: the old one, "tool_families", held an
    # "off" that every saved profile carried without the user having chosen it.
    tool_families: bool = True
    # The notes kept from one project to the next (core/agent/memory.py) go with the requests. On by default: empty,
    # it sends nothing, and nothing enters it that the user did not write or accept (decided 2026-11-22).
    memory: bool = True
    # The requests of every project, kept on this computer for the tab "All projects" of the history
    # (core/agent/request_log.py). Off: nothing is recorded any more (audit of 2026-11-24: the log is in clear in
    # the settings of QGIS, with no way to turn it off).
    keep_request_history: bool = True

    @property
    def rules(self) -> dict:
        try:
            return clean_rules(json.loads(self.tool_rules or "{}"))
        except (ValueError, RecursionError):
            return {}

    @property
    def needs_key(self) -> bool:
        return self.preset != OLLAMA_PRESET

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


def sources_configured() -> bool:
    """Whether the Sources tab was ever saved (the ``enabled_sources`` key written).

    The REST/MCP source gate (``filtermate_api.source_gate``) only refuses unticked sources once the user
    configured them: until then the previous behavior (open data reachable) is kept, so existing setups keep
    working until they opt in.
    """
    try:
        return bool(QgsSettings().contains(_PREFIX + "enabled_sources"))
    except Exception:
        return False


def _port(value) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1024 <= port <= 65535 else DEFAULT_PORT


# Keys of the free quota (removed in 5.1): the token of its relay stays in a profile that used it.
_FORMER_KEYS = ("free_token", "free_token_target")


def _forget_former_keys(settings) -> None:
    for name in _FORMER_KEYS:
        if settings.contains(_PREFIX + name):
            settings.remove(_PREFIX + name)


def load_settings() -> AgentSettings:
    settings = QgsSettings()
    _forget_former_keys(settings)
    preset = str(settings.value(_PREFIX + "preset", DEFAULT_PRESET) or DEFAULT_PRESET)
    known = preset in PRESETS
    return AgentSettings(
        preset=preset if known else DEFAULT_PRESET,
        model=str(settings.value(_PREFIX + "model", "") or ""),
        # The address saved under a preset that is gone (the relay of the free quota) is not the one of Anthropic.
        base_url=str(settings.value(_PREFIX + "base_url", "") or "") if known else "",
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
        tool_rules=str(settings.value(_PREFIX + "tool_rules", "{}") or "{}"),
        tool_families=settings.value(_PREFIX + "offer_tools_by_task", True, type=bool),
        memory=settings.value(_PREFIX + "memory", True, type=bool),
        keep_request_history=settings.value(_PREFIX + "keep_request_history", True, type=bool))


def save_settings(values: AgentSettings) -> None:
    settings = QgsSettings()
    settings.setValue(_PREFIX + "preset", values.preset)
    settings.setValue(_PREFIX + "model", values.model)
    settings.setValue(_PREFIX + "base_url", values.base_url)
    settings.setValue(_PREFIX + "consent", values.consent)
    settings.setValue(_PREFIX + "send_values", values.send_values)
    settings.setValue(_PREFIX + "expert_python", values.expert_python)
    settings.setValue(_PREFIX + "local_filtering_only", values.local_filtering_only)
    settings.setValue(_PREFIX + "offer_tools_by_task", values.tool_families)
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
    settings.setValue(_PREFIX + "memory", values.memory)
    settings.setValue(_PREFIX + "keep_request_history", values.keep_request_history)


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
    config.setConfig("username", _KEY_USER)
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


def delete_own_key(authcfg: str) -> bool:
    """Delete ``authcfg`` when it is a configuration FilterMate made for a key (its name, its method and the user
    name it sets); True when it went.

    Raises:
        KeyStoreError: The database is locked or unavailable.
    """
    if not authcfg:
        return False
    manager = _auth_manager()
    listed = manager.availableAuthMethodConfigs().get(authcfg)
    if listed is None or listed.name() != _AUTH_NAME or listed.method() != _METHOD:
        return False  # the user's own configuration, or one of another plugin: not ours to delete
    config = QgsAuthMethodConfig()
    result = manager.loadAuthenticationConfig(authcfg, config, True)
    loaded, config = (result[0], result[1]) if isinstance(result, tuple) else (result, config)
    if not loaded or config.config("username") != _KEY_USER:
        return False
    return bool(manager.removeAuthenticationConfig(authcfg))


def provider_config(values: AgentSettings, key: Optional[str]) -> ProviderConfig:
    kind, base_url = PRESETS[values.preset]
    return ProviderConfig(kind=kind, model=values.model, base_url=values.base_url or base_url, api_key=key or "",
                          max_tokens=MAX_TOKENS, effort=read_effort(values) or None)


def _effort_key(values: AgentSettings) -> str:
    target = target_of(values.preset, getattr(values, 'base_url', ''))
    return json.dumps([values.preset, target, values.model], separators=(',', ':'))


def _effort_preferences() -> dict:
    try:
        value = json.loads(str(QgsSettings().value(_PREFIX + 'effort_by_model', '{}') or '{}'))
        return value if isinstance(value, dict) else {}
    except (ValueError, RecursionError):
        return {}


def read_effort(values: AgentSettings) -> str:
    """The effort chosen for this model and server, independent of other provider settings."""
    return valid_effort(values.preset, values.model, _effort_preferences().get(_effort_key(values), ''))


def write_effort(values: AgentSettings, effort: str) -> None:
    """Keep a supported choice, or remove it to restore the provider default."""
    if effort and valid_effort(values.preset, values.model, effort) != effort:
        raise ValueError('Unsupported reasoning effort for this model')
    preferences = _effort_preferences()
    key = _effort_key(values)
    if effort:
        preferences[key] = effort
    else:
        preferences.pop(key, None)
    QgsSettings().setValue(_PREFIX + 'effort_by_model', json.dumps(preferences, ensure_ascii=False))


# --- The providers the user set up (2026-11-16): the menu of the AGENT panel and the agent switch between them ------

def current_provider(values: AgentSettings) -> ProviderEntry:
    return ProviderEntry(values.preset, values.model, values.base_url, values.authcfg, values.consent_target,
                         values.key_target)


def read_providers() -> Tuple[ProviderEntry, ...]:
    """The providers set up, the latest first; none when what is saved cannot be read."""
    try:
        rows = json.loads(str(QgsSettings().value(_PREFIX + "providers", "[]") or "[]"))
        return tuple(ProviderEntry(str(row["preset"]), str(row["model"]), str(row.get("base_url", "")),
                                   str(row.get("authcfg", "")), str(row.get("consent_target", "")),
                                   str(row.get("key_target", ""))) for row in rows)
    except (ValueError, TypeError, KeyError, AttributeError):
        return ()


def write_providers(entries) -> None:
    QgsSettings().setValue(_PREFIX + "providers", json.dumps(
        [{"preset": entry.preset, "model": entry.model, "base_url": entry.base_url, "authcfg": entry.authcfg,
          "consent_target": entry.consent_target, "key_target": entry.key_target} for entry in entries]))


def read_mode() -> str:
    """The mode of the agent picked under the line of the chat (core/agent/modes.py), Act by default."""
    from ...core.agent.modes import mode_or_default
    return mode_or_default(QgsSettings().value(_PREFIX + "mode", ""))


def write_mode(mode: str) -> None:
    from ...core.agent.modes import mode_or_default
    QgsSettings().setValue(_PREFIX + "mode", mode_or_default(mode))


def read_designer_mode() -> bool:
    return QgsSettings().value(_PREFIX + 'designer_mode', False, type=bool) is True


def write_designer_mode(enabled: bool) -> None:
    QgsSettings().setValue(_PREFIX + 'designer_mode', bool(enabled))
