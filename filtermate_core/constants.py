# -*- coding: utf-8 -*-
"""Constants the core's SQL generation relies on.

``infrastructure.constants`` defines the same values for the plugin (importing
them from here breaks the tests that load it as a top-level package);
tests/unit/adapters/backends/postgresql/test_temp_naming.py checks they agree.
"""

# Schema that holds FilterMate's temporary objects (materialized views, temp tables) in PostgreSQL.
DEFAULT_TEMP_SCHEMA = 'filter_mate_temp'

# Prefix of the pre-computed buffer tables of dynamic buffers (in the source table's schema).
TABLE_PREFIX_BUFFER = 'fm_temp_buf_'

__all__ = ['DEFAULT_TEMP_SCHEMA', 'TABLE_PREFIX_BUFFER']
