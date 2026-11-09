# -*- coding: utf-8 -*-
"""Names FilterMate gives its PostgreSQL objects.

``session_token`` moved from ``adapters/backends/postgresql/cleanup.py``
(2026-10-27), which re-exports it: the expression builder names the buffer
tables with it and the cleanup finds them by it.
"""
import re


def session_token(session_id) -> str:
    """``session_id`` reduced to ``[0-9a-z]{1,12}``, as buffer table names carry it."""
    token = re.sub(r'[^0-9a-z]', '', str(session_id or '').lower())[:12]
    return token or 'nosession'


__all__ = ['session_token']
