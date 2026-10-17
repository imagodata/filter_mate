# -*- coding: utf-8 -*-
"""
Names of the temporary objects FilterMate creates, and safe cleanup of them.

The "Clear Temp Tables" menu used to remove everything matching
``LIKE 'fm_temp_%' OR LIKE 'mv_%'``. In SQL LIKE the underscore is a wildcard
and the match ignores the case, so ``mvt_reseau`` or ``MVoies`` (user layers
in the source GeoPackage) were dropped with FilterMate's own tables. The
rules below are exact and case-sensitive, and they describe only what the
plugin really generates:

Spatialite / GeoPackage (``fm_temp_<session>_<layer>``, legacy
``mv_<session>_<layer>``): the session id is the 8 hexadecimal digits made by
``FilterMateApp`` (md5 truncated).

PostgreSQL: ``fm_temp_mv_*`` / ``fm_temp_src_*`` / ``fm_temp_chain_*``
(materialized views) and ``fm_temp_buf_*`` / ``fm_temp_tbl_*`` /
``fm_temp_src_*`` (tables) anywhere; the older ``fm_mv_*``,
``filtermate_mv_*`` and ``fm_buf_*`` only inside FilterMate's own schemas.

This module only depends on the standard library.
"""

import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger('FilterMate.Infrastructure.Database.TempObjects')

# Spatialite / GeoPackage -----------------------------------------------------

_SESSION_ID_PATTERN = r'[0-9a-f]{8}'
_SPATIALITE_PREFIXES = ('fm_temp_', 'mv_')
_SPATIALITE_TEMP_RE = re.compile(
    r'^(?:fm_temp_|mv_)' + _SESSION_ID_PATTERN + r'_\w+$')

# Tables that register a user layer: never touched, whatever their name.
_GPKG_REGISTRY_TABLES = (
    ('gpkg_contents', 'table_name'),
    ('gpkg_geometry_columns', 'table_name'),
)


def is_filtermate_spatialite_temp_table(name: str, session_id: Optional[str] = None) -> bool:
    """Tell whether a table name is one FilterMate generates.

    The match is exact and case-sensitive. Without ``session_id`` the name
    must carry an 8-digit hexadecimal session id; with one, the id is compared
    literally (it is never used as a LIKE or glob pattern).

    Args:
        name: Table name from ``sqlite_master``.
        session_id: Restrict the match to this session.

    Returns:
        bool: True for ``fm_temp_<session>_<rest>`` and ``mv_<session>_<rest>``.
    """
    if not name or not isinstance(name, str):
        return False
    if session_id:
        if not re.fullmatch(r'\w+', session_id):
            return False
        return any(
            name.startswith(f"{prefix}{session_id}_")
            and re.fullmatch(r'\w+', name[len(prefix) + len(session_id) + 1:] or '')
            for prefix in _SPATIALITE_PREFIXES)
    return _SPATIALITE_TEMP_RE.match(name) is not None


def _quote(identifier: str) -> str:
    """Quote an SQLite identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def _open_readonly(db_path: str) -> sqlite3.Connection:
    """Open an SQLite file without any possibility to write to it."""
    uri = Path(os.path.abspath(db_path)).as_uri() + '?mode=ro'
    return sqlite3.connect(uri, uri=True, timeout=5)


def _registered_layer_tables(cur) -> set:
    """Tables registered as layers (GeoPackage registries), if any."""
    registered = set()
    for registry, column in _GPKG_REGISTRY_TABLES:
        try:
            registered.update(
                row[0] for row in cur.execute(f'SELECT {column} FROM {registry}'))
        except sqlite3.Error:
            continue  # not a GeoPackage, or no such registry
    return registered


def list_filtermate_temp_tables(db_path: str, session_id: Optional[str] = None) -> List[str]:
    """List FilterMate temporary tables of a SQLite / GeoPackage file.

    The file is opened read-only. Tables registered in ``gpkg_contents`` or
    ``gpkg_geometry_columns`` are user layers and are never returned.

    Args:
        db_path: Path of the database.
        session_id: Only the tables of this session.

    Returns:
        list: Table names (empty when the file is missing or unreadable).
    """
    if not db_path or not os.path.isfile(db_path):
        return []
    try:
        conn = _open_readonly(db_path)
    except sqlite3.Error as e:
        logger.debug(f"Cannot open {db_path}: {e}")
        return []
    try:
        cur = conn.cursor()
        registered = _registered_layer_tables(cur)
        names = [row[0] for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        return sorted(
            n for n in names
            if is_filtermate_spatialite_temp_table(n, session_id) and n not in registered)
    except sqlite3.Error as e:
        logger.debug(f"Cannot list temp tables of {db_path}: {e}")
        return []
    finally:
        conn.close()


def _index_tables_of(cur, table: str) -> List[str]:
    """R-tree virtual tables (``idx_<table>_<geom>``) created for a temp table."""
    head = f"idx_{table}_"
    found = []
    for name, sql in cur.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table'"):
        if name.startswith(head) and sql and sql.lstrip().upper().startswith('CREATE VIRTUAL') \
                and 'rtree' in sql.lower():
            found.append(name)
    return found


def drop_filtermate_temp_tables(
    db_path: str,
    session_id: Optional[str] = None,
    tables: Optional[Iterable[str]] = None,
) -> List[str]:
    """Drop FilterMate temporary tables (and their R-tree index) from a file.

    Every name is validated again here, even when ``tables`` comes from
    :func:`list_filtermate_temp_tables`: a name that is not a generated one,
    or that is registered as a layer, is skipped. Each table is dropped in its
    own transaction.

    Args:
        db_path: Path of the database.
        session_id: Only the tables of this session.
        tables: Explicit candidates (default: everything listed).

    Returns:
        list: Names of the tables actually dropped.
    """
    if not db_path or not os.path.isfile(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    except sqlite3.Error as e:
        logger.error(f"Cannot open {db_path}: {e}")
        return []
    dropped: List[str] = []
    try:
        cur = conn.cursor()
        registered = _registered_layer_tables(cur)
        existing = {row[0] for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        candidates = list(tables) if tables is not None else sorted(existing)
        for table in candidates:
            if (table not in existing or table in registered
                    or not is_filtermate_spatialite_temp_table(table, session_id)):
                continue
            try:
                cur.execute('BEGIN')
                for index_table in _index_tables_of(cur, table):
                    cur.execute(f'DROP TABLE IF EXISTS {_quote(index_table)}')
                cur.execute(f'DROP TABLE IF EXISTS {_quote(table)}')  # nosec B608 - name validated above
                _forget_spatialite_geometry(cur, table)
                cur.execute('COMMIT')
                dropped.append(table)
            except sqlite3.Error as e:
                logger.warning(f"Error dropping temp table {table}: {e}")
                try:
                    cur.execute('ROLLBACK')
                except sqlite3.Error:  # nosec B110 - no transaction left to roll back
                    pass
    except sqlite3.Error as e:
        logger.error(f"Error cleaning temp tables of {db_path}: {e}")
    finally:
        conn.close()
    return dropped


def _forget_spatialite_geometry(cur, table: str) -> None:
    """Remove the Spatialite ``geometry_columns`` row of a dropped table."""
    try:
        cur.execute('DELETE FROM geometry_columns WHERE f_table_name = ?', (table.lower(),))
    except sqlite3.Error:  # nosec B110 - not a Spatialite database
        pass


# PostgreSQL ---------------------------------------------------------------

#: Schemas FilterMate creates for its own objects.
PG_TEMP_SCHEMAS = ('filtermate_temp', 'filter_mate_temp')

#: Prefixes valid in any schema, by object kind.
_PG_PREFIXES = {
    'matview': ('fm_temp_mv_', 'fm_temp_src_', 'fm_temp_chain_'),
    'table': ('fm_temp_buf_', 'fm_temp_tbl_', 'fm_temp_src_'),
}
#: Older prefixes, honoured only inside PG_TEMP_SCHEMAS.
_PG_LEGACY_PREFIXES = {
    'matview': ('fm_mv_', 'filtermate_mv_'),
    'table': ('fm_buf_',),
}


def is_filtermate_pg_temp_object(kind: str, schema: str, name: str) -> bool:
    """Tell whether a PostgreSQL object is one FilterMate created.

    Args:
        kind: ``'matview'`` or ``'table'``.
        schema: Schema of the object.
        name: Object name.

    Returns:
        bool: True when the name carries one of FilterMate's prefixes
        (exactly, case-sensitively) followed by something, the legacy
        prefixes counting only inside FilterMate's own schemas.
    """
    if kind not in _PG_PREFIXES or not name or not isinstance(name, str):
        return False
    prefixes = _PG_PREFIXES[kind]
    if schema in PG_TEMP_SCHEMAS:
        prefixes = prefixes + _PG_LEGACY_PREFIXES[kind]
    return any(
        name.startswith(prefix) and re.fullmatch(r'\w+', name[len(prefix):] or '')
        for prefix in prefixes)


def pg_temp_object_like_patterns(kind: str) -> List[str]:
    """LIKE patterns (backslash-escaped underscores) to pre-select objects in SQL.

    They only narrow the query; :func:`is_filtermate_pg_temp_object` takes the
    decision. PostgreSQL's LIKE is case-sensitive.

    Args:
        kind: ``'matview'`` or ``'table'``.

    Returns:
        list: Patterns such as ``fm\\_temp\\_mv\\_%``.
    """
    prefixes = _PG_PREFIXES.get(kind, ()) + _PG_LEGACY_PREFIXES.get(kind, ())
    return [prefix.replace('_', '\\_') + '%' for prefix in prefixes]
