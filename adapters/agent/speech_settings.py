# -*- coding: utf-8 -*-
"""Microphone preferences, independent of the chat provider. Keys stay in QGIS' authentication database."""
import json
from dataclasses import asdict, fields, replace

from qgis.core import QgsSettings

from ...core.agent.speech import SpeechSettings, validate_settings
from .settings import delete_own_key, load_settings, read_key, store_key

KEY = 'filter_mate/agent/speech'


def load_speech_settings():
    try:
        raw = json.loads(str(QgsSettings().value(KEY, '{}') or '{}'))
        if not isinstance(raw, dict):
            return SpeechSettings()
        names = {field.name for field in fields(SpeechSettings)}
        values = {name: value for name, value in raw.items() if name in names
                  and (isinstance(value, str) if name != 'use_provider_key' else isinstance(value, bool))}
        result = SpeechSettings(**values)
        validate_settings(result)
        return result
    except (ValueError, TypeError, RecursionError):
        return SpeechSettings()


def speech_key(values):
    validate_settings(values)
    if values.use_provider_key:
        current = load_settings()
        if current.preset != values.service or current.target != values.target or not current.has_key:
            raise ValueError('The chat provider has no stored key for this transcription address.')
        return read_key(current.authcfg)
    if values.authcfg:
        if values.key_target != values.target:
            raise ValueError('The stored transcription key belongs to another service address.')
        return read_key(values.authcfg)
    return ''


def save_speech_settings(values, key='', *, forget_key=False):
    validate_settings(values)
    old = load_speech_settings()
    authcfg = old.authcfg if old.key_target == values.target else ''
    key_target = old.key_target if authcfg else ''
    if forget_key:
        authcfg, key_target = '', ''
    if values.service != 'local' and not (values.use_provider_key or key or authcfg):
        raise ValueError('This transcription service needs an API key.')
    if values.use_provider_key:
        speech_key(values)  # validate before changing or deleting any saved credential
    if '\r' in key or '\n' in key:
        raise ValueError('The API key contains an invalid character.')
    if key and not values.use_provider_key:
        authcfg = store_key(key, authcfg)
        key_target = values.target
    if values.use_provider_key:
        authcfg, key_target = '', ''
    wanted = replace(values, authcfg=authcfg, key_target=key_target)
    if forget_key and old.authcfg and old.authcfg != authcfg:
        delete_own_key(old.authcfg)
    QgsSettings().setValue(KEY, json.dumps(asdict(wanted), ensure_ascii=False))
    return wanted
