# -*- coding: utf-8 -*-
"""LLM providers of the agent: one adapter per wire format, chosen by :func:`create_provider`."""
from __future__ import annotations

from .anthropic_messages import AnthropicProvider
from .base import Provider, ProviderConfig
from .openai_chat import OpenAIChatProvider

KIND_ANTHROPIC = "anthropic"
KIND_OPENAI_COMPATIBLE = "openai_compatible"

# Where each known service lives. The model is always the user's choice.
PRESETS = {
    "anthropic": (KIND_ANTHROPIC, "https://api.anthropic.com"),
    "mistral": (KIND_OPENAI_COMPATIBLE, "https://api.mistral.ai/v1"),
    "openai": (KIND_OPENAI_COMPATIBLE, "https://api.openai.com/v1"),
    "ollama": (KIND_OPENAI_COMPATIBLE, "http://localhost:11434/v1"),
}


def create_provider(config: ProviderConfig) -> Provider:
    """The adapter for ``config.kind``.

    Raises:
        ValueError: Unknown kind, no model, or a base URL that is refused.
    """
    if not config.model:
        raise ValueError("no model chosen")
    if config.kind == KIND_ANTHROPIC:
        return AnthropicProvider(config)
    if config.kind == KIND_OPENAI_COMPATIBLE:
        return OpenAIChatProvider(config)
    raise ValueError(f"unknown provider kind {config.kind!r}")
