# -*- coding: utf-8 -*-
"""
Names of the temporary objects FilterMate creates, and safe cleanup of them.

The "Clear Temp Tables" menu used to remove everything matching
``LIKE 'fm_temp_%' OR LIKE 'mv_%'``. In SQL LIKE the underscore is a wildcard
and the match ignores the case, so ``mvt_reseau`` or ``MVoies`` (user layers
in the source GeoPackage) were dropped with FilterMate's own tables. The
rules below are exact and case-sensitive, and they describe only what the
plugin really generates:

Spatialite / GeoPackage (``fm_temp_<session>_<layer>``): the session id is the
8 hexadecimal digits made by ``FilterMateApp`` (md5 truncated). The legacy
``mv_<session>_<layer>`` name is NOT recognised in a user's file: nothing
creates it any more, and ``mv_20231231_bati`` is a perfectly valid user table
name (8 digits are valid hexadecimal).

PostgreSQL: ``fm_temp_mv_*`` / ``fm_temp_src_*`` / ``fm_temp_chain_*``
(materialized views) and ``fm_temp_buf_*`` / ``fm_temp_tbl_*`` /
``fm_temp_src_*`` (tables) anywhere, with any suffix (a buffer table carries
the name of its source table: ``fm_temp_buf_routes-2024_ab12cd34``); the older
``fm_mv_*``, ``filtermate_mv_*``, ``mv_<session>_*`` and ``fm_buf_*`` only
inside FilterMate's own schemas.

This module only depends on the standard library.
"""

import logging
import os
import re
import sqlite3
from typing import Iterable, List, Optional
from urllib.parse import quote

logger = logging.getLogger('FilterMate.Infrastructure.Database.TempObjects')

# Spatialite / GeoPackage -----------------------------------------------------

_SESSION_ID_PATTERN = r'[0-9a-f]{8}'
_SPATIALITE_TEMP_RE = re.compile(r'^fm_temp_' + _SESSION_ID_PATTERN + r'_\w+$')

# GeoPackage registries of user layers: a table listed there is never touched,
# whatever its name.
_GPKG_REGISTRY_TABLES = (
    ('gpkg_contents', 'table_name'),
    ('gpkg_geometry_columns', 'table_name'),
)

# Spatialite metadata that keeps a row per geometry column
_SPATIALITE_METADATA_TABLES = (
    'geometry_columns', 'geometry_columns_statistics', 'geometry_columns_field_infos',
    'geometry_columns_time', 'geometry_columns_auth',
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
        bool: True for ``fm_temp_<session>_<rest>``.
    """
    if not name or not isinstance(name, str):
        return False
    if session_id:
        if not re.fullmatch(r'\w+', session_id):
            return False
        head = f"fm_temp_{session_id}_"
        return name.startswith(head) and re.fullmatch(r'\w+', name[len(head):] or '') is not None
    return _SPATIALITE_TEMP_RE.match(name) is not None


def _quote(identifier: str) -> str:
    """Quote an SQLite identifier."""
    return '"' + identifier.replace('"', '""') + '"'


_WINDOWS_DRIVE = re.compile(r'^[A-Za-z]:[\\/]')


def sqlite_readonly_uri(path: str) -> str:
    """``file:`` URI that opens ``path`` read-only with ``sqlite3.connect(uri=True)``.

    Handles the three shapes of path: POSIX (``file:///tmp/a.db``), Windows
    drive (``file:///C:/data/a.db``) and Windows UNC share, which SQLite wants
    with an empty authority and the two slashes of the share
    (``file:////server/share/a.db``). Special characters are percent-encoded.

    Args:
        path: Path of the database file.

    Returns:
        str: The URI, ending in ``?mode=ro``.
    """
    if _WINDOWS_DRIVE.match(path):
        return 'file:///' + quote(path.replace('\\', '/'), safe='/:') + '?mode=ro'
    if path.startswith('\\\\') or path.startswith('//'):
        share = path.replace('\\', '/').lstrip('/')
        return 'file:////' + quote(share, safe='/') + '?mode=ro'
    absolute = os.path.abspath(path)
    return 'file://' + quote(absolute, safe='/') + '?mode=ro'


def _open_readonly(db_path: str) -> sqlite3.Connection:
    """Open an SQLite file without any possibility to write to it."""
    return sqlite3.connect(sqlite_readonly_uri(db_path), uri=True, timeout=5)


def _registered_layer_tables(cur) -> set:
    """Tables registered as layers by the GeoPackage registries, if any."""
    registered = set()
    for registry, column in _GPKG_REGISTRY_TABLES:
        try:
            registered.update(
                row[0] for row in cur.execute(f'SELECT {column} FROM {registry}'))
        except sqlite3.Error:
            continue  # not a GeoPackage, or no such registry
    return registered


def _spatialite_declared_tables(cur) -> set:
    """Lower-cased names of the tables a native Spatialite database declares as layers."""
    try:
        return {str(row[0]).lower() for row in cur.execute('SELECT f_table_name FROM geometry_columns')}
    except sqlite3.Error:
        return set()


def _is_referenced(table: str, subsets: Iterable[str]) -> bool:
    """Whether a layer subset string names the table (whole identifier, quoted or not)."""
    pattern = re.compile(r'(?<![\w])' + re.escape(table) + r'(?![\w])')
    return any(pattern.search(subset) for subset in subsets if subset)


def _candidate_tables(cur, session_id: Optional[str], exclude_referenced_by: Iterable[str]) -> List[str]:
    """Generated temp tables of an open database, user layers and tables in use left out.

    Tables registered as layers are never candidates. A native Spatialite
    database declares a table in ``geometry_columns``; such a table is a
    candidate only when the exact id of the running session names it (the
    session id proves who made it), never in the all-sessions cleanup.
    """
    registered = _registered_layer_tables(cur)
    declared = _spatialite_declared_tables(cur)
    in_use = [s for s in exclude_referenced_by if s]
    names = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    return sorted(
        n for n in names
        if is_filtermate_spatialite_temp_table(n, session_id)
        and n not in registered
        and (session_id or n.lower() not in declared)
        and not (in_use and _is_referenced(n, in_use)))


def list_filtermate_temp_tables(
    db_path: str,
    session_id: Optional[str] = None,
    exclude_referenced_by: Iterable[str] = (),
) -> List[str]:
    """List FilterMate temporary tables of a SQLite / GeoPackage file.

    The file is opened read-only. Never returned: tables registered in
    ``gpkg_contents`` / ``gpkg_geometry_columns``, tables declared in
    Spatialite's ``geometry_columns`` (unless ``session_id`` names the
    running session), and tables named by one of ``exclude_referenced_by``
    (the subset strings of the project's layers: a layer is filtered through
    them right now).

    Args:
        db_path: Path of the database.
        session_id: Only the tables of this session.
        exclude_referenced_by: Subset strings of layers that are in use.

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
        return _candidate_tables(conn.cursor(), session_id, exclude_referenced_by)
    except sqlite3.Error as e:
        logger.debug(f"Cannot list temp tables of {db_path}: {e}")
        return []
    finally:
        conn.close()


def _load_spatialite(conn) -> bool:
    """Load mod_spatialite on a connection (best effort)."""
    try:
        conn.enable_load_extension(True)
    except (AttributeError, sqlite3.Error):
        return False
    for name in ('mod_spatialite', 'mod_spatialite.so', 'mod_spatialite.dll'):
        try:
            conn.load_extension(name)
            return True
        except sqlite3.Error:
            continue
    return False


def _drop_one(cur, table: str, native: bool, spatialite_loaded: bool) -> None:
    """Drop a temp table with its index and its Spatialite metadata (inside a transaction)."""
    geoms: List[str] = []
    if native:
        geoms = [row[0] for row in cur.execute(
            'SELECT f_geometry_column FROM geometry_columns WHERE lower(f_table_name) = lower(?)', (table,))]
        if spatialite_loaded:
            for geom in geoms:
                try:
                    cur.execute('SELECT DiscardGeometryColumn(?, ?)', (table, geom))
                except sqlite3.Error:  # nosec B110 - the manual metadata cleanup below covers it
                    pass
    # Only the index declared for this table's own geometry columns: a prefix match
    # ("idx_<table>_") would also take the index of "<table>_other".
    for geom in geoms:
        cur.execute(f'DROP TABLE IF EXISTS {_quote(f"idx_{table}_{geom}")}')
    cur.execute(f'DROP TABLE IF EXISTS {_quote(table)}')
    if native:
        for metadata in _SPATIALITE_METADATA_TABLES:
            try:
                cur.execute(f'DELETE FROM {metadata} WHERE lower(f_table_name) = lower(?)', (table,))
            except sqlite3.Error:  # nosec B110 - table absent in this Spatialite version
                pass


def drop_filtermate_temp_tables(
    db_path: str,
    session_id: Optional[str] = None,
    tables: Optional[Iterable[str]] = None,
    exclude_referenced_by: Iterable[str] = (),
) -> List[str]:
    """Drop FilterMate temporary tables (and their R-tree index) from a file.

    Every name is validated again here, even when ``tables`` comes from
    :func:`list_filtermate_temp_tables`: a name that is not a generated one,
    that is registered as a layer or that a layer subset still uses is
    skipped. Each table is dropped in its own transaction; in a native
    Spatialite database its index (``idx_<table>_<geometry>``, the exact one)
    and its rows in the ``geometry_columns*`` metadata go with it
    (``DiscardGeometryColumn`` when mod_spatialite loads, plain deletes
    otherwise).

    Args:
        db_path: Path of the database.
        session_id: Only the tables of this session.
        tables: Explicit candidates (default: everything listed).
        exclude_referenced_by: Subset strings of layers that are in use.

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
        candidates = _candidate_tables(cur, session_id, exclude_referenced_by)
        wanted = candidates if tables is None else [t for t in tables if t in set(candidates)]
        native = bool(wanted) and bool(
            cur.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'geometry_columns'").fetchone())
        spatialite_loaded = native and _load_spatialite(conn)
        for table in wanted:
            try:
                cur.execute('BEGIN')
                _drop_one(cur, table, native, spatialite_loaded)
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
_PG_LEGACY_SESSION_VIEW = re.compile(r'^mv_' + _SESSION_ID_PATTERN + r'_.+$')


def is_filtermate_pg_temp_object(kind: str, schema: str, name: str) -> bool:
    """Tell whether a PostgreSQL object is one FilterMate created.

    Args:
        kind: ``'matview'`` or ``'table'``.
        schema: Schema of the object.
        name: Object name.

    Returns:
        bool: True when the name carries one of FilterMate's prefixes
        (exactly, case-sensitively) followed by anything, the legacy
        prefixes (and ``mv_<session>_*`` views) counting only inside
        FilterMate's own schemas.
    """
    if kind not in _PG_PREFIXES or not name or not isinstance(name, str):
        return False
    in_own_schema = schema in PG_TEMP_SCHEMAS
    prefixes = _PG_PREFIXES[kind]
    if in_own_schema:
        prefixes = prefixes + _PG_LEGACY_PREFIXES[kind]
    if any(name.startswith(prefix) and len(name) > len(prefix) for prefix in prefixes):
        return True
    return in_own_schema and kind == 'matview' and _PG_LEGACY_SESSION_VIEW.match(name) is not None


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
    patterns = [prefix.replace('_', '\\_') + '%' for prefix in prefixes]
    if kind == 'matview':
        patterns.append('mv\\_%')  # mv_<session>_*, kept only inside FilterMate's schemas
    return patterns


# PostgreSQL cleanup helpers (psycopg2-style connection / cursor) --------------

def pg_quote_ident(name: str) -> str:
    """Quote a PostgreSQL identifier (double the quotes; never "sanitise" it).

    A name like ``routes-2024`` or ``Routes Nat`` must reach the server as it is.
    """
    return '"' + name.replace('"', '""') + '"'


def pg_find_temp_objects(cursor) -> list:
    """Materialized views and tables FilterMate generated, in any schema.

    The SQL only pre-selects with exact prefixes (underscores escaped, PostgreSQL
    LIKE is case-sensitive); each row is then checked again by
    :func:`is_filtermate_pg_temp_object`.

    Returns:
        list: ``(kind, schema, name)``, dependents (``..._dump``) first.
    """
    found = []
    for kind, sql in (
        ('matview', """SELECT schemaname, matviewname FROM pg_matviews
                       WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                       AND matviewname LIKE ANY (%s)"""),
        ('table', """SELECT schemaname, tablename FROM pg_tables
                     WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                     AND tablename LIKE ANY (%s)"""),
    ):
        cursor.execute(sql, (pg_temp_object_like_patterns(kind),))
        for schema, name in cursor.fetchall():
            if is_filtermate_pg_temp_object(kind, schema, name):
                found.append((kind, schema, name))
    found.sort(key=lambda o: (o[1], -len(o[2]), o[2]))
    return found


def pg_schema_content(cursor, schema: str):
    """Split the relations of a schema into FilterMate's and foreign ones.

    Returns:
        tuple: ``(filtermate_objects, foreign_names)``: ``(kind, schema, name)``
        tuples, and the names of anything FilterMate did not create (user
        tables, plain views, ...).
    """
    cursor.execute(
        """SELECT c.relname, c.relkind
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'f')""",
        (schema,)
    )
    objects, foreign = [], []
    for name, relkind in cursor.fetchall():
        kind = {'m': 'matview', 'r': 'table'}.get(relkind)
        if kind and is_filtermate_pg_temp_object(kind, schema, name):
            objects.append((kind, schema, name))
        else:
            foreign.append(name)
    return objects, foreign


def _pg_object_exists(cursor, schema: str, name: str) -> bool:
    cursor.execute("SELECT to_regclass(%s)", (f"{pg_quote_ident(schema)}.{pg_quote_ident(name)}",))
    row = cursor.fetchone()
    return bool(row) and row[0] is not None


def pg_drop_temp_objects(connexion, cursor, objects) -> list:
    """Drop FilterMate temporary PostgreSQL objects, never with CASCADE.

    Every object is validated again. A materialized view may depend on another
    one (``..._dump``): a refused drop is retried after the others (a few
    passes). What still cannot be dropped is left in place and logged, instead
    of being cascaded onto objects FilterMate did not create. An object counts
    as dropped only once the catalog no longer has it.

    Args:
        connexion: psycopg2 connection (commit / rollback per object).
        cursor: Cursor of that connection.
        objects: ``(kind, schema, name)`` tuples.

    Returns:
        list: The ``(kind, schema, name)`` tuples that are gone.
    """
    pending = [o for o in objects if is_filtermate_pg_temp_object(*o)]
    dropped = []
    for _pass in range(4):
        if not pending:
            break
        still_pending = []
        for kind, schema, name in pending:
            statement = 'DROP MATERIALIZED VIEW' if kind == 'matview' else 'DROP TABLE'
            try:
                cursor.execute(f'{statement} {pg_quote_ident(schema)}.{pg_quote_ident(name)}')  # nosec B608
                connexion.commit()
                if _pg_object_exists(cursor, schema, name):
                    still_pending.append((kind, schema, name))
                else:
                    dropped.append((kind, schema, name))
                    logger.debug(f"Dropped {kind}: {schema}.{name}")
            except Exception as e:
                try:
                    connexion.rollback()
                except Exception:  # nosec B110 - best-effort rollback
                    pass
                still_pending.append((kind, schema, name))
                logger.debug(f"Could not drop {kind} {schema}.{name} yet: {e}")
        if len(still_pending) == len(pending):
            break  # no progress: the remaining ones have outside dependents (or are gone already)
        pending = still_pending
    for kind, schema, name in pending:
        logger.warning(f"Left in place: {kind} {schema}.{name}")
    return dropped


def pg_drop_filtermate_schema(connexion, schema: str) -> dict:
    """Drop one of FilterMate's own schemas, only if everything in it is FilterMate's.

    The schema is emptied object by object and dropped without CASCADE, so a
    user table, a user view built on a FilterMate object, ``public`` or any
    other schema is never lost.

    Args:
        connexion: psycopg2 connection (committed here).
        schema: Schema to drop.

    Returns:
        dict: ``status`` (``'dropped'``, ``'absent'``, ``'not_filtermate_schema'``,
        ``'foreign'`` when it holds objects FilterMate did not create, ``'error'``),
        ``dropped`` (the objects removed) and ``foreign`` (names of the others).
    """
    result = {'status': 'error', 'dropped': [], 'foreign': []}
    if schema not in PG_TEMP_SCHEMAS:
        logger.warning(f"Refusing to drop schema '{schema}': it is not a FilterMate temporary schema")
        result['status'] = 'not_filtermate_schema'
        return result
    cursor = None
    try:
        cursor = connexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s", (schema,))
        if cursor.fetchone()[0] == 0:
            result['status'] = 'absent'
            return result
        objects, foreign = pg_schema_content(cursor, schema)
        if foreign:
            logger.warning(
                f"Schema '{schema}' holds {len(foreign)} object(s) FilterMate did not create "
                f"({', '.join(sorted(foreign)[:5])}): not dropped")
            result.update(status='foreign', foreign=sorted(foreign))
            return result
        result['dropped'] = pg_drop_temp_objects(connexion, cursor, objects)
        cursor.execute(f'DROP SCHEMA {pg_quote_ident(schema)}')
        connexion.commit()
        result['status'] = 'dropped'
        logger.info(f"Schema '{schema}' dropped")
    except Exception as e:
        logger.warning(f"Schema '{schema}' not dropped: {e}")
        try:
            connexion.rollback()
        except Exception:  # nosec B110 - best-effort rollback
            pass
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:  # nosec B110 - best-effort close
                pass
    return result
