# -*- coding: utf-8 -*-
"""Known reasoning controls; an unknown model keeps its provider's defaults.

Checked against the providers' documentation on 2026-11-26:
https://platform.claude.com/docs/en/build-with-claude/effort
https://developers.openai.com/api/docs/guides/reasoning
https://docs.mistral.ai/inference/conversations/reasoning
https://docs.ollama.com/capabilities/thinking

These are conservative options, not a claim that every compatible server accepts
the same controls. In particular, chat aliases and unknown local models are omitted.
"""
from __future__ import annotations

import re
from typing import Tuple

_COMMON = ('low', 'medium', 'high')
_CLAUDE_FULL = {
    'claude-haiku-5-5', 'claude-sonnet-5', 'claude-sonnet-5-5',
    'claude-opus-4-7', 'claude-opus-4-8', 'claude-opus-5', 'claude-opus-5-5',
    'claude-fable-5', 'claude-fable-5-1', 'claude-fable-5-2',
    'claude-mythos-5', 'claude-mythos-5-1', 'claude-mythos-5-2',
}
_CLAUDE_MAX = {'claude-opus-4-6', 'claude-sonnet-4-6', 'claude-mythos-preview'}


def effort_levels(preset: str, model: str) -> Tuple[str, ...]:
    """The selectable levels for this provider and model, without the default (empty string)."""
    name = str(model or '').strip().lower()
    if preset == 'anthropic':
        name = re.sub(r'-(?:\d{8}|latest)$', '', name)
        if name in _CLAUDE_FULL:
            return _COMMON + ('xhigh', 'max')
        if name in _CLAUDE_MAX:
            return _COMMON + ('max',)
        return _COMMON if name == 'claude-opus-4-5' else ()
    if preset == 'openai':
        name = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', name)
        if name in ('gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-5.1', 'gpt-5.2',
                    'gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano', 'gpt-5.5', 'gpt-5.6'):
            # The shared low/medium/high ladder avoids model-specific none,
            # minimal, pro-only and extra-high restrictions.
            return _COMMON
        return _COMMON if name in ('o1', 'o3', 'o3-mini', 'o4-mini') else ()
    if preset == 'mistral':
        if name in ('mistral-small-2603', 'mistral-small-latest', 'mistral-medium-3-5'):
            return ('none', 'high')
        if name in ('mistral-large-4', 'mistral-large-4-0'):
            return _COMMON
        if name in ('zai-glm-5-3', 'zai-glm-5-3-flash'):
            return ('low', 'high', 'max')
    if preset == 'ollama' and name.rsplit('/', 1)[-1].split(':', 1)[0] == 'gpt-oss':
        return _COMMON
    return ()


def valid_effort(preset: str, model: str, value: str) -> str:
    """A supported level, else the provider default; stale choices never reach a new model."""
    return value if isinstance(value, str) and value in effort_levels(preset, model) else ''
