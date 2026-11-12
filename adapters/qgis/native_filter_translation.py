"""QGIS attribute predicate to the native SQL of a database or file layer.

Reads the expression tree and the field types in QGIS, the writing itself is
``filtermate_core.filter.native_dialect`` (pure). No feature is read, nothing
is sent to the source, the layer is not modified.
"""
import logging

try:
    from ...core.filter.server_dialect import TranslationStatus, Unsupported
    from ...filtermate_core.filter.native_dialect import (
        BOOL, INT, OGR_SQL, OTHER, POSTGRESQL, REAL, SQLITE, TEXT, NativeTranslation, translate_native,
    )
except ImportError:  # plugin root on sys.path in pure unit tests
    from core.filter.server_dialect import TranslationStatus, Unsupported
    from filtermate_core.filter.native_dialect import (
        BOOL, INT, OGR_SQL, OTHER, POSTGRESQL, REAL, SQLITE, TEXT, NativeTranslation, translate_native,
    )

logger = logging.getLogger('FilterMate.NativeFilterTranslation')

MAX_EXPRESSION_LENGTH = 65536

# Dialects whose writing was compared with QGIS itself on real layers
# (tests/qgis_headless/check_native_translation.py): only those replace the
# former conversion. PostgreSQL joins them once the check has run on PostGIS.
APPLIED_DIALECTS = (SQLITE, OGR_SQL)

# OGR storages whose attribute filter is run by SQLite, and by the OGR SQL engine.
# Any other storage (a database or a service opened through OGR) is not translated.
_SQLITE_STORAGES = ('gpkg', 'sqlite')
_OGR_SQL_STORAGES = ('esri shapefile', 'mapinfo file', 'geojson', 'geojsonseq', 'flatgeobuf')

# QVariant.Type / QMetaType.Type ids (the same numbers in Qt 5 and Qt 6).
_BOOL_ID, _INT_IDS, _DOUBLE_ID, _STRING_ID = 1, (2, 3, 4, 5), 6, 10
_POSTGRES_TEXT = ('text', 'varchar')
_NOT_PLAIN_TEXT = ('json', 'jsonb')


def native_dialect_for_layer(layer):
    """``postgresql``, ``sqlite``, ``ogr_sql``, or None when the subset is not native SQL we write."""
    try:
        provider = (layer.providerType() or '').lower()
        if provider == 'postgres':
            return POSTGRESQL
        if provider == 'spatialite':
            return SQLITE
        if provider == 'ogr':
            storage = (layer.dataProvider().storageType() or '').lower()
            if storage in _SQLITE_STORAGES:
                return SQLITE
            if storage in _OGR_SQL_STORAGES:
                return OGR_SQL
    except Exception as exc:  # nosec B110 - deleted layer, provider without storage type
        logger.debug('No native dialect: %s', exc)
    return None


def _type_id(field):
    value = field.type()
    value = getattr(value, 'value', value)  # a Qt 6 enum
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def field_types(fields, dialect):
    """Type of each field for ``native_dialect``: int, real, text, bool or other."""
    types = {}
    for field in fields:
        type_id = _type_id(field)
        name = (field.typeName() or '').lower()
        if type_id in _INT_IDS:
            kind = INT
        elif type_id == _DOUBLE_ID:
            kind = REAL
        elif type_id == _BOOL_ID:
            kind = BOOL
        elif type_id == _STRING_ID and name not in _NOT_PLAIN_TEXT and (
                dialect != POSTGRESQL or name in _POSTGRES_TEXT):
            # PostgreSQL: char(n) is padded, citext ignores case, uuid / enum are not texts
            kind = TEXT
        else:
            kind = OTHER
        types[field.name()] = kind
    return types


def translate_for_layer(layer, expression):
    """Write ``expression`` for the data source of ``layer``.

    Args:
        layer: Vector layer whose subset string is native SQL.
        expression: QGIS attribute predicate.

    Returns:
        NativeTranslation, or None when the layer's subset is not a language
        written here (memory, delimited text, web services, other OGR storages).
    """
    dialect = native_dialect_for_layer(layer)
    if dialect is None:
        return None
    if not expression or len(expression) > MAX_EXPRESSION_LENGTH:
        return NativeTranslation(TranslationStatus.NONE, local_expression=expression or '',
                                 reason='Empty or too large expression')
    from qgis.core import QgsExpression
    from .server_filter_translation import _tree
    parsed = QgsExpression(expression)
    if parsed.hasParserError() or parsed.rootNode() is None:
        return NativeTranslation(TranslationStatus.NONE, local_expression=expression,
                                 reason='Invalid attribute expression')
    # Joined and virtual fields are unknown to the source.
    provider = layer.dataProvider()
    fields = provider.fields() if provider is not None else layer.fields()
    try:
        tree = _tree(parsed.rootNode(), extended=True)
    except (Unsupported, RecursionError):
        return NativeTranslation(TranslationStatus.NONE, local_expression=expression,
                                 reason='Expression complexity limit exceeded')
    return translate_native(tree, dialect, field_types(fields, dialect))


def native_subset(layer, expression):
    """The native SQL of the WHOLE expression, or None when any part is left to QGIS."""
    try:
        if native_dialect_for_layer(layer) not in APPLIED_DIALECTS:
            return None
        result = translate_for_layer(layer, expression)
    except Exception as exc:  # catch-all: the former conversion stays the fallback
        logger.warning('Native translation failed, former conversion used: %s', exc)
        return None
    if result is None:
        return None
    if result.status != TranslationStatus.FULL or not result.sql:
        logger.debug('Not fully translated (%s): %s', result.status.value, result.reason)
        return None
    return result.sql


__all__ = ['field_types', 'native_dialect_for_layer', 'native_subset', 'translate_for_layer']
