# -*- coding: utf-8 -*-
"""Tables of the PostgreSQL connections QGIS keeps: their names for the agent, and one of them as a layer.

A connection is the user's: its address and its credentials stay in QGIS. The agent is given the name of a
connection the user ticked, the names of its tables and their comments, never a row; a table it adds is opened by
QGIS with the source QGIS builds, for a table the connection really lists. Main thread only.
"""
from __future__ import annotations

import hashlib
import logging
import unicodedata
from typing import Any, Dict, List, Tuple

logger = logging.getLogger('FilterMate.DatabaseTables')

PROVIDER = 'postgres'
MAX_TABLES = 50
MAX_TEXT = 200
# Schemas of the database itself: no table of the user is there.
SYSTEM_SCHEMAS = frozenset({'information_schema', 'pg_catalog', 'pg_toast', 'topology', 'tiger', 'tiger_data'})


def _plain(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(char)).lower()


def _metadata():
    from qgis.core import QgsProviderRegistry
    return QgsProviderRegistry.instance().providerMetadata(PROVIDER)


def connection_names() -> List[str]:
    """The PostgreSQL connections stored in QGIS, by name; none when QGIS has no such provider."""
    return [name for name, _target in connections()]


def connections() -> List[Tuple[str, str]]:
    """The PostgreSQL connections stored in QGIS: each name with a digest of what it connects to.

    The digest (server, port, database, user, service) lets a connection made again under the same name, to another
    server, be told from the one the user ticked. Nothing of it is the address: it is hashed here.
    """
    from qgis.core import QgsDataSourceUri
    metadata = _metadata()
    if metadata is None:
        return []
    try:
        stored = metadata.connections(False)
    except Exception:  # a list for the settings dialog: a broken entry must not keep it from opening
        logger.debug("database connections not read", exc_info=True)
        return []
    found = []
    for name in sorted(str(name) for name in stored):
        try:
            uri = QgsDataSourceUri(stored[name].uri())
            target = "|".join((uri.host(), uri.port(), uri.database(), uri.username(), uri.service()))
        except Exception:
            target = ""
        found.append((name, hashlib.blake2b(target.encode("utf-8"), digest_size=6).hexdigest()))
    return found


def _connection(name: str):
    """The stored connection of that exact name.

    Raises:
        ValueError: No such connection.
    """
    metadata = _metadata()
    found = metadata.connections(False).get(name) if metadata is not None else None
    if found is None:
        raise ValueError(f"QGIS has no PostgreSQL connection named {name!r}")
    return found


def _unreachable() -> ValueError:
    logger.warning("database not read", exc_info=True)
    return ValueError("the database did not answer, or refused the connection (details in the FilterMate log)")


def schemas(name: str) -> List[str]:
    """The schemas of a connection that can hold tables of the user: one light request, to know it answers.

    Raises:
        ValueError: No such connection, or a database that does not answer.
    """
    from qgis.core import QgsProviderConnectionException
    try:
        return sorted(schema for schema in _connection(name).schemas() if schema not in SYSTEM_SCHEMAS)
    except QgsProviderConnectionException:
        raise _unreachable() from None


def _tables(connection, schema: str = '') -> List[Any]:
    """The vector or attribute-only tables and views of a schema, or of every schema but those of the database itself.

    A table shows once per geometry column. Listing every schema reads the whole catalog of the database, on the
    main thread: a schema is given whenever it is known.

    Raises:
        ValueError: The database did not answer; its message stays in the log (it names the server).
    """
    from qgis.core import QgsAbstractDatabaseProviderConnection, QgsProviderConnectionException
    wanted = (QgsAbstractDatabaseProviderConnection.TableFlag.Vector
              | QgsAbstractDatabaseProviderConnection.TableFlag.Aspatial)
    if schema in SYSTEM_SCHEMAS:
        return []
    try:
        listed = connection.tables(schema, wanted)
    except QgsProviderConnectionException:
        raise _unreachable() from None
    return [table for table in listed if table.schema() not in SYSTEM_SCHEMAS]


def _is_view(table) -> bool:
    from qgis.core import QgsAbstractDatabaseProviderConnection
    flags = QgsAbstractDatabaseProviderConnection.TableFlag
    return bool(table.flags() & flags.View) or bool(table.flags() & flags.MaterializedView)


def _geometry_types(table) -> List[Any]:
    try:
        return list(table.geometryColumnTypes()) if table.geometryColumn() else []
    except Exception:
        return []


def list_tables(name: str, search: str = '', limit: int = MAX_TABLES, schema: str = '') -> Dict[str, Any]:
    """Tables of a connection whose schema, name or comment hold every word of ``search``: names only, no row.

    Raises:
        ValueError: No such connection, or a database that does not answer.
    """
    from qgis.core import QgsWkbTypes
    words = [word for word in _plain(search).split() if word]
    limit = max(1, min(int(limit), MAX_TABLES))
    found = []
    for table in _tables(_connection(name), (schema or '').strip()):
        text = _plain(f"{table.schema()} {table.tableName()} {table.comment()}")
        if all(word in text for word in words):
            row = {'schema': table.schema(), 'table': table.tableName(), 'kind': 'view' if _is_view(table) else 'table',
                   'geometry': bool(table.geometryColumn()), 'comment': " ".join(table.comment().split())[:MAX_TEXT]}
            if row['geometry']:
                row['geometry_column'] = table.geometryColumn()[:MAX_TEXT]
                row['geometry_types'] = [QgsWkbTypes.displayString(item.wkbType) for item in _geometry_types(table)][:8]
            found.append(row)
    found.sort(key=lambda row: (row['schema'], row['table'], row.get('geometry_column', '')))
    return {'tables': found[:limit], 'count': len(found), 'truncated': len(found) > limit}


def add_table(name: str, schema: str, table: str, title: str = '', geometry_column: str = '') -> Any:
    """A table or a view of a connection as a layer of the project; the source is built by QGIS for one it lists.

    A table with several geometry columns is drawn by the one named, else by its first. A column that holds several
    kinds of geometries is opened with the first kind QGIS found in it. A view has no key of its own: the first of
    the columns QGIS proposes that is not its geometry is taken.

    Raises:
        ValueError: No such connection or table, a database that does not answer, a table that does not open.
    """
    from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer
    connection = _connection(name)
    candidates = [item for item in _tables(connection, schema) if item.schema() == schema and item.tableName() == table]
    if not candidates:
        raise ValueError(f"this connection lists no table {schema}.{table}: use the names list_database_tables gives")
    listed = next((item for item in candidates if item.geometryColumn() == geometry_column), None) if geometry_column \
        else candidates[0]
    if listed is None:
        raise ValueError(f"{schema}.{table} has no geometry column {geometry_column!r}")
    geometry = listed.geometryColumn() or ''
    keys = [key for key in (listed.primaryKeyColumns() or []) if key != geometry]
    key = keys[0] if keys and (_is_view(listed) or len(keys) == 1) else ''
    uri = QgsDataSourceUri(connection.uri())
    uri.setDataSource(schema, table, geometry, '', key)
    kinds = _geometry_types(listed)
    if kinds:
        uri.setWkbType(kinds[0].wkbType)
        srid = kinds[0].crs.postgisSrid() if kinds[0].crs.isValid() else 0
        if srid:
            uri.setSrid(str(srid))
    layer = QgsVectorLayer(uri.uri(False), (title or '').strip()[:80] or table, PROVIDER)
    if not layer.isValid():
        raise ValueError(f"{schema}.{table} could not be opened as a layer")  # nothing more is read from an invalid layer
    QgsProject.instance().addMapLayer(layer)
    return layer
