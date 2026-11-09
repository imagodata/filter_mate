# -*- coding: utf-8 -*-
"""SQL identifier hygiene shared by the backends.

``sanitize_sql_identifier`` moved from ``infrastructure/database/sql_utils.py``
(2026-10-27), which re-exports it.
"""
import re


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifier (table name, column name, schema name).

    Removes or replaces dangerous characters that could lead to SQL injection
    or syntax errors.

    Args:
        identifier: Raw SQL identifier (table, column, schema name)

    Returns:
        str: Sanitized identifier safe for SQL queries

    Examples:
        >>> sanitize_sql_identifier("my_table")
        'my_table'
        >>> sanitize_sql_identifier("table; DROP TABLE users;")
        'table_DROP_TABLE_users'
        >>> sanitize_sql_identifier("schema.table")
        'schema.table'
    """
    if not identifier:
        return ""

    # Remove dangerous characters, keep only alphanumeric, underscore, dot, quotes
    # Allow dots for schema.table notation
    # Allow double quotes for PostgreSQL quoted identifiers
    sanitized = re.sub(r'[^\w\.\"]', '_', str(identifier))

    # Remove leading/trailing underscores added by sanitization
    sanitized = sanitized.strip('_')

    return sanitized


__all__ = ['sanitize_sql_identifier']
