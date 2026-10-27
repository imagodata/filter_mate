# -*- coding: utf-8 -*-
"""Read the geometry column out of a QGIS data source URI, without QGIS.

QGIS writes database layers (PostgreSQL, Spatialite, ...) as ``key=value``
pairs where the table carries its geometry column in parentheses::

    dbname='gis' key='id' srid=2154 table="public"."roads" (geom) sql=

:func:`geometry_column_from_uri` reproduces what
``QgsDataSourceUri(uri).geometryColumn()`` returns for such a string, tokenizing
as ``QgsDataSourceUri`` does: values quoted with ``'`` or ``"`` escape with a
backslash (a doubled quote is not an escape), an unquoted value ends at a
blank, ``sql=`` takes the rest of the string, the last ``table=`` wins.
``tests/unit/core/domain/test_datasource_uri.py`` holds the cases checked
against QGIS itself.
"""
from typing import Tuple

_BLANKS = ' \t\r\n'


def _skip_blanks(uri: str, i: int) -> int:
    while i < len(uri) and uri[i] in _BLANKS:
        i += 1
    return i


def _read_value(uri: str, i: int) -> Tuple[str, int]:
    """One value starting at ``i`` (quoted or bare) and the index after it and its blanks."""
    n = len(uri)
    if i < n and uri[i] in ('"', "'"):
        quote = uri[i]
        i += 1
        chars = []
        while i < n and uri[i] != quote:
            if uri[i] == '\\' and i + 1 < n:
                i += 1
            chars.append(uri[i])
            i += 1
        i += 1  # closing quote (or past the end)
        return ''.join(chars), _skip_blanks(uri, i)
    start = i
    while i < n and uri[i] not in _BLANKS:
        i += 1
    return uri[start:i], _skip_blanks(uri, i)


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
    if not uri:
        return ''
    column = ''
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
        if key == 'table':
            if value and i < n and uri[i] == '.':
                _, i = _read_value(uri, _skip_blanks(uri, i + 1))  # schema."table": the table itself
            column, i = _read_geometry_column(uri, i)
    return column


__all__ = ['geometry_column_from_uri']
