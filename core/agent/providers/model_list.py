# -*- coding: utf-8 -*-
"""The chat models a provider lists, and where to get a key for each: pure reading, no Qt.

Anthropic, Mistral and OpenAI answer ``GET {base}/models`` with ``{"data": [{"id": ...}]}``, the list holding
embedding, speech and image models too; Ollama answers its own ``/api/tags`` (see ``ollama_chat.installed_models``).
"""
from __future__ import annotations

import json
import unicodedata
from typing import Dict, Tuple

from .ollama_chat import MAX_LISTED_MODELS, installed_models, tags_url

# The page of each service where an API key is created. Checked on 2026-11-13: Anthropic's console moved to
# platform.claude.com; OpenAI's answers 403 to a script (its bot protection), Mistral's asks to sign in first.
KEY_PAGES: Dict[str, str] = {
    "anthropic": "https://platform.claude.com/settings/keys",
    "mistral": "https://console.mistral.ai/api-keys",
    "openai": "https://platform.openai.com/api-keys",
}

# Parts of an id that tell a model which does not chat.
_NOT_CHAT = ("embed", "tts", "whisper", "dall-e", "moderation", "image", "audio", "transcribe", "realtime", "search")
ANTHROPIC_PAGE_SIZE = 100  # its list gives 20 models unless asked for more
MAX_ID_LENGTH = 200  # a longer id is not the name of a model


def listing_url(kind: str, base_url: str) -> str:
    """Where the provider of ``kind`` at ``base_url`` (the address of its chat requests) lists its models."""
    base = base_url.rstrip("/")
    if kind == "ollama":
        return tags_url(base)
    if kind == "anthropic":
        return f"{base}/v1/models?limit={ANTHROPIC_PAGE_SIZE}"
    return f"{base}/models"


def _is_model_id(name: object) -> bool:
    """A name a model can have: some text, of a sane length, with no control character (it ends in a combo box)."""
    return (isinstance(name, str) and bool(name.strip()) and len(name) <= MAX_ID_LENGTH
            and not any(unicodedata.category(char) == "Cc" for char in name))


def _created(entry: dict) -> float:
    """The sort key of an entry: the newest first, those without a date (a number of seconds) after, in their order."""
    created = entry.get("created")
    return -created if isinstance(created, (int, float)) and not isinstance(created, bool) else 1


def models_from_listing(kind: str, data: bytes) -> Tuple[str, ...]:
    """The chat models of the answer of a list of models, newest first when it dates them, at most ``MAX_LISTED_MODELS``.

    OpenAI and Mistral do not sort their list: the newest models are put first, before the cap cuts the list. Without
    dates (Anthropic lists the newest first already), the order of the server is kept.

    Never raises: whatever a server answers (HTML, a list, bad bytes) is an empty list.

    Args:
        kind: The kind of the provider (``anthropic``, ``openai_compatible`` or ``ollama``).
        data: The body of the answer.
    """
    try:
        payload = json.loads(bytes(data).decode("utf-8"))
    except (ValueError, RecursionError, TypeError):
        return ()
    if kind == "ollama":
        return tuple(installed_models(payload))
    entries = payload.get("data") if isinstance(payload, dict) else None
    chosen: Dict[str, dict] = {}
    for entry in entries if isinstance(entries, list) else ():
        name = entry.get("id") if isinstance(entry, dict) else None
        if not _is_model_id(name) or name in chosen:
            continue
        capabilities = entry.get("capabilities")  # Mistral says which models complete a chat, and call functions
        if isinstance(capabilities, dict) and (capabilities.get("completion_chat") is False
                                               or capabilities.get("function_calling") is False):
            continue
        if any(word in name.lower() for word in _NOT_CHAT):
            continue
        chosen[name] = entry
    return tuple(sorted(chosen, key=lambda name: _created(chosen[name])))[:MAX_LISTED_MODELS]
