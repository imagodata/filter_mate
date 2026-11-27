"""Explicit skill commands at the beginning of a user request, never inside prose or a file path."""
from __future__ import annotations

import re
from typing import Optional

_COMMAND = re.compile(r'\A\s*/([a-z][a-z0-9-]{0,99})(?=\s|\Z)', re.IGNORECASE)
_PREFIX = re.compile(r'\A\s*/([a-z0-9-]{0,100})\Z', re.IGNORECASE)


def requested_skill(text: str) -> Optional[str]:
    match = _COMMAND.match(text)
    return match.group(1).lower() if match else None


def completion_prefix(before_cursor: str) -> Optional[str]:
    match = _PREFIX.match(before_cursor)
    return match.group(1).lower() if match else None
