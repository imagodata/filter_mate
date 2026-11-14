# -*- coding: utf-8 -*-
"""Tables of the PostgreSQL connections QGIS keeps: their names for the agent, and one of them as a layer.

A connection is the user's: its address and its credentials stay in QGIS. The agent is given the name of a
connection the user ticked, the names of its tables and their comments, never a row; a table it adds is opened by
QGIS with the source QGIS builds, for a table the connection really lists. Main thread only.
"""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List

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
    metadata = _metadata()
    if metadata is None:
        return []
    try:
        return sorted(str(name) for name in metadata.connections(False))
    except Exception:  # a list for the settings dialog: a broken entry must not keep it from opening
        logger.debug("database connections not read", exc_info=True)
        return []


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


def _tables(connection) -> List[Any]:
    """Every vector or attribute-only table of the connection, the schemas of the database itself left out.

    Raises:
        ValueError: The database did not answer; its message stays in the log (it names the server).
    """
    from qgis.core import QgsAbstractDatabaseProviderConnection, QgsProviderConnectionException
    wanted = (QgsAbstractDatabaseProviderConnection.TableFlag.Vector
              | QgsAbstractDatabaseProviderConnection.TableFlag.Aspatial)
    try:
        listed = connection.tables('', wanted)
    except QgsProviderConnectionException:
        logger.warning("database tables not listed", exc_info=True)
        raise ValueError("the database did not answer, or refused the connection (details in the FilterMate log)") from None
    return [table for table in listed if table.schema() not in SYSTEM_SCHEMAS]


def list_tables(name: str, search: str = '', limit: int = MAX_TABLES) -> Dict[str, Any]:
    """Tables of a connection whose schema, name or comment hold every word of ``search``: names only, no row.

    Raises:
        ValueError: No such connection, or a database that does not answer.
    """
    words = [word for word in _plain(search).split() if word]
    limit = max(1, min(int(limit), MAX_TABLES))
    found = []
    for table in _tables(_connection(name)):
        text = _plain(f"{table.schema()} {table.tableName()} {table.comment()}")
        if all(word in text for word in words):
            found.append({'schema': table.schema(), 'table': table.tableName(),
                          'geometry': bool(table.geometryColumn()), 'comment': " ".join(table.comment().split())[:MAX_TEXT]})
    found.sort(key=lambda row: (row['schema'], row['table']))
    return {'tables': found[:limit], 'count': len(found), 'truncated': len(found) > limit}


def add_table(name: str, schema: str, table: str, title: str = '') -> Any:
    """A table of a connection as a layer of the project; the source is built by QGIS for a table it lists.

    Raises:
        ValueError: No such connection or table, a database that does not answer, a table that does not open.
    """
    from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer
    connection = _connection(name)
    listed = next((item for item in _tables(connection) if item.schema() == schema and item.tableName() == table), None)
    if listed is None:
        raise ValueError(f"this connection lists no table {schema}.{table}: use the names list_database_tables gives")
    uri = QgsDataSourceUri(connection.uri())
    keys = list(listed.primaryKeyColumns() or [])
    uri.setDataSource(schema, table, listed.geometryColumn() or '', '', keys[0] if len(keys) == 1 else '')
    layer = QgsVectorLayer(uri.uri(False), (title or '').strip()[:80] or table, PROVIDER)
    if not layer.isValid():
        raise ValueError(f"{schema}.{table} could not be opened as a layer")  # nothing more is read from an invalid layer
    QgsProject.instance().addMapLayer(layer)
    return layer
