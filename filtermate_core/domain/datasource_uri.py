# -*- coding: utf-8 -*-
"""Read the table and geometry column out of a QGIS data source URI, without QGIS.

QGIS writes database layers (PostgreSQL, Spatialite, ...) as ``key=value``
pairs where the table carries its geometry column in parentheses::

    dbname='gis' key='id' srid=2154 table="public"."roads" (geom) sql=

:func:`table_from_uri` reproduces what ``QgsDataSourceUri(uri)`` returns from
``schema()``, ``table()`` and ``geometryColumn()`` for such a string,
tokenizing as ``QgsDataSourceUri`` does: values quoted with ``'`` or ``"``
escape with a backslash (a doubled quote is not an escape), an unquoted value
ends at a blank, a ``.`` after the first value makes it the schema, ``sql=``
takes the rest of the string, the last ``table=`` wins.
``tests/unit/core/domain/test_datasource_uri.py`` holds the cases checked
against QGIS itself (3.44 and 4.3 answer the same).
"""
from typing import NamedTuple, Tuple


class UriTable(NamedTuple):
    """``schema()``, ``table()`` and ``geometryColumn()`` of a URI; ``''`` for what it does not name."""
    schema: str
    table: str
    geometry_column: str


_BLANKS = ' \t\r\n'


def _skip_blanks(uri: str, i: int) -> int:
    while i < len(uri) and uri[i] in _BLANKS:
        i += 1
    return i


def _read_value(uri: str, i: int) -> Tuple[str, int]:
    """One value starting at ``i`` (quoted or bare) and the index after it and its blanks.

    As ``QgsDataSourceUri::getValue``: a backslash escapes the delimiter and
    itself (a bare value: ``'`` and itself) and stays before any other
    character; a backslash ending the string is dropped.
    """
    n = len(uri)
    quote = uri[i] if i < n and uri[i] in ('"', "'") else None
    escapable = (quote, '\\') if quote else ("'", '\\')
    if quote:
        i += 1
    chars = []
    while i < n:
        c = uri[i]
        if c == '\\':
            if i + 1 >= n:
                i += 1  # a final backslash is dropped
                break
            if uri[i + 1] in escapable:
                chars.append(uri[i + 1])
                i += 2
                continue
            chars.append(c)  # kept before any other character
            i += 1
            continue
        if quote and c == quote:
            i += 1  # the closing quote
            break
        if not quote and c in _BLANKS:
            break
        chars.append(c)
        i += 1
    return ''.join(chars), _skip_blanks(uri, i)


def _read_geometry_column(uri: str, i: int) -> Tuple[str, int]:
    """The ``(column)`` after a table, if any: QGIS unescapes ``\\)`` and ``\\\\``.

    Without a closing parenthesis QGIS keeps the rest of the string as the column.
    """
    n = len(uri)
    if i >= n or uri[i] != '(':
        return '', i
    i += 1
    start = i
    while i < n and uri[i] != ')':
        if uri[i] == '\\':
            i += 1
        i += 1
    column = uri[start:min(i, n)].replace('\\)', ')').replace('\\\\', '\\')
    return column, _skip_blanks(uri, i + 1)


def geometry_column_from_uri(uri: str) -> str:
    """Geometry column named by a QGIS data source URI, ``''`` when it names none.

    File URIs (``/data/x.gpkg|layername=roads``) and service URIs (WFS, ...)
    name none; a ``|geometryname=`` part is an OGR option, not read here.

    Args:
        uri: Data source URI as ``QgsDataProvider.dataSourceUri()`` returns it.

    Returns:
        str: The column, or ``''``.
    """
    return table_from_uri(uri).geometry_column


def table_from_uri(uri: str) -> UriTable:
    """Schema, table and geometry column named by the ``table=`` part of a QGIS URI.

    The schema is the ``schema=`` key or the ``"schema".`` part of ``table=``,
    whichever comes last; a ``table=`` without a schema keeps the one before.

    Args:
        uri: Data source URI as ``QgsDataProvider.dataSourceUri()`` returns it.

    Returns:
        UriTable: ``('', '', '')`` for a URI without ``table=`` (files, services) or None.

    Raises:
        TypeError: for anything but a string or None, as ``QgsDataSourceUri``
            (the callers' fallbacks rely on it).
    """
    schema = table = column = ''
    if uri is None:
        return UriTable(schema, table, column)
    if not isinstance(uri, str):
        raise TypeError(f"a data source URI is a string, not {type(uri).__name__}")
    if not uri:
        return UriTable(schema, table, column)
    n = len(uri)
    i = _skip_blanks(uri, 0)
    while i < n:
        if uri[i] == '=':
            i = _skip_blanks(uri, i + 1)  # a value without a key: QGIS skips the '='
            continue
        start = i
        while i < n and uri[i] != '=' and uri[i] not in _BLANKS:
            i += 1
        key = uri[start:i]
        i = _skip_blanks(uri, i)
        if i >= n or uri[i] != '=':
            continue  # a word without '=': ignored
        i = _skip_blanks(uri, i + 1)
        if key == 'sql':
            break  # the filter takes the rest of the string
        value, i = _read_value(uri, i)
        if key == 'schema':
            schema = value
        elif key == 'table':
            table = value
            if i < n and uri[i] == '.':
                # schema."table", also with an empty schema (""."roads")
                schema = value
                table, i = _read_value(uri, _skip_blanks(uri, i + 1))
            column, i = _read_geometry_column(uri, i)
    return UriTable(schema, table, column)


__all__ = ['UriTable', 'geometry_column_from_uri', 'table_from_uri']
