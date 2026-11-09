# -*- coding: utf-8 -*-
"""Whether a direct PostgreSQL driver is importable.

Mirrors ``infrastructure.database.postgresql_support.PSYCOPG2_AVAILABLE`` for the
core's strategies, without the QGIS-provider fallback that module also reports.
"""

try:
    import psycopg2  # noqa: F401
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

__all__ = ['PSYCOPG2_AVAILABLE']
