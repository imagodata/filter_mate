# -*- coding: utf-8 -*-
"""The settings of the agent, and its API key in the authentication database of QGIS.

The key is never written in a settings or configuration file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Tuple

from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsSettings
from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent.providers import PRESETS
from ...core.agent.providers.base import ProviderConfig

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


def target_of(preset: str, base_url: str) -> str:
    """The server a key and a consent are for."""
    return base_url.strip().rstrip("/") or PRESETS[preset][1]


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

    @property
    def needs_key(self) -> bool:
        return self.preset != "ollama"

    @property
    def target(self) -> str:
        return target_of(self.preset, self.base_url)

    @property
    def has_consent(self) -> bool:
        return self.consent and self.consent_target == self.target

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
        key_target=str(settings.value(_PREFIX + "key_target", "") or ""))


def save_settings(values: AgentSettings) -> None:
    settings = QgsSettings()
    settings.setValue(_PREFIX + "preset", values.preset)
    settings.setValue(_PREFIX + "model", values.model)
    settings.setValue(_PREFIX + "base_url", values.base_url)
    settings.setValue(_PREFIX + "consent", values.consent)
    settings.setValue(_PREFIX + "send_values", values.send_values)
    settings.setValue(_PREFIX + "enabled_sources", json.dumps(list(values.enabled_sources)))
    settings.setValue(_PREFIX + "custom_sources", values.custom_sources)
    settings.setValue(_PREFIX + "authcfg", values.authcfg)
    settings.setValue(_PREFIX + "consent_target", values.consent_target)
    settings.setValue(_PREFIX + "key_target", values.key_target)


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
    return ProviderConfig(kind=kind, model=values.model, base_url=values.base_url or base_url, api_key=key or "",
                          max_tokens=MAX_TOKENS)
