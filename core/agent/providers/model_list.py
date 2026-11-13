# -*- coding: utf-8 -*-
"""The chat models a provider lists, and where to get a key for each: pure reading, no Qt.

Anthropic, Mistral and OpenAI answer ``GET {base}/models`` with ``{"data": [{"id": ...}]}``, the list holding
embedding, speech and image models too; Ollama answers its own ``/api/tags`` (see ``ollama_chat.installed_models``).
"""
from __future__ import annotations

import json
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


def listing_url(kind: str, base_url: str) -> str:
    """Where the provider of ``kind`` at ``base_url`` (the address of its chat requests) lists its models."""
    base = base_url.rstrip("/")
    if kind == "ollama":
        return tags_url(base)
    if kind == "anthropic":
        return f"{base}/v1/models?limit={ANTHROPIC_PAGE_SIZE}"
    return f"{base}/models"


def models_from_listing(kind: str, data: bytes) -> Tuple[str, ...]:
    """The chat models of the answer of a list of models, in its order, at most ``MAX_LISTED_MODELS``.

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
    names = []
    for entry in entries if isinstance(entries, list) else ():
        name = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name.strip() or name in names:
            continue
        capabilities = entry.get("capabilities")  # Mistral says which models complete a chat
        if isinstance(capabilities, dict) and capabilities.get("completion_chat") is False:
            continue
        if any(word in name.lower() for word in _NOT_CHAT):
            continue
        names.append(name)
        if len(names) >= MAX_LISTED_MODELS:
            break
    return tuple(names)
