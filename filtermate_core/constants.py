# -*- coding: utf-8 -*-
"""Constants the core's SQL generation relies on.

``infrastructure.constants`` re-exports them for the plugin.
"""

# Schema that holds FilterMate's temporary objects (materialized views, temp tables) in PostgreSQL.
DEFAULT_TEMP_SCHEMA = 'filter_mate_temp'

__all__ = ['DEFAULT_TEMP_SCHEMA']
