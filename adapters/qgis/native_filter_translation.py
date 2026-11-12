"""QGIS attribute predicate to the native SQL of a database or file layer.

Reads the expression tree and the field types in QGIS, the writing itself is
``filtermate_core.filter.native_dialect`` (pure). The translation reads no
feature. A hybrid subset (:func:`subset_for_layer` with ``evaluate``) reads the
layer's features to let QGIS evaluate what is not translated; the layer is
never modified.
"""
import logging

try:
    from ...core.filter.server_dialect import TranslationStatus, Unsupported
    from ...filtermate_core.filter.native_dialect import (
        BOOL, INT, OGR_SQL, OTHER, POSTGRESQL, REAL, SQLITE, TEXT, NativeTranslation, hybrid_sql, key_reference,
        translate_native,
    )
    from ...filtermate_core.filter.pk_formatter import is_null_value
except ImportError:  # plugin root on sys.path in pure unit tests
    from core.filter.server_dialect import TranslationStatus, Unsupported
    from filtermate_core.filter.native_dialect import (
        BOOL, INT, OGR_SQL, OTHER, POSTGRESQL, REAL, SQLITE, TEXT, NativeTranslation, hybrid_sql, key_reference,
        translate_native,
    )
    from filtermate_core.filter.pk_formatter import is_null_value

logger = logging.getLogger('FilterMate.NativeFilterTranslation')

MAX_EXPRESSION_LENGTH = 65536

# Dialects whose writing was compared with QGIS itself on real layers
# (tests/qgis_headless/check_native_translation.py): only those replace the
# former conversion. PostgreSQL since 2026-11-12, checked on PostGIS in a UTF-8
# and in a C database (QGIS 4.2.3 and 3.44.15).
APPLIED_DIALECTS = (SQLITE, OGR_SQL, POSTGRESQL)

# A hybrid subset evaluates every feature of the layer in QGIS (Python loop, no
# cancellation): beyond this count, or when the count is unknown, the former
# conversion is kept.
HYBRID_MAX_FEATURES = 1_000_000

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
    return subset_for_layer(layer, expression)


def subset_for_layer(layer, expression, key_name=None, evaluate=False, negated=False):
    """The subset of ``layer`` for ``expression`` in its source's own language.

    Args:
        layer: Vector layer whose subset string is native SQL.
        expression: QGIS attribute predicate.
        key_name: Unique key field of the layer (a field of its source).
        evaluate: Whether a part left untranslated may be evaluated by QGIS
            and replaced by a list of keys. Only when the subset is neither
            negated (FALSE and NULL differ under NOT) nor read through another
            filter than the one it will be combined with by AND.
        negated: Whether the subset will be written under NOT (AND NOT). OGR
            SQL gives FALSE to TRUE AND NULL: a translation holding AND, OR or
            NOT is then left to the former conversion.

    Returns:
        The native SQL of the whole expression, else (``evaluate``, SQLite
        and PostgreSQL sources) a hybrid subset that keeps the same features, else None
        (former conversion). Never a subset the subset sanitizer would
        rewrite (safe_set_subset_string runs it on every subset).
    """
    try:
        if native_dialect_for_layer(layer) not in APPLIED_DIALECTS:
            return None
        result = translate_for_layer(layer, expression)
    except Exception as exc:  # catch-all: the former conversion stays the fallback
        logger.warning('Native translation failed, former conversion used: %s', exc)
        return None
    if result is None:
        return None
    if negated and result.composite and native_dialect_for_layer(layer) == OGR_SQL:
        logger.info('Native SQL left aside: OGR SQL would negate an AND / OR (TRUE AND NULL is FALSE there)')
        return None
    native_sql = result.sql
    if native_sql and not _survives_sanitizer(layer, native_sql):
        logger.info('Native SQL left aside, the subset sanitizer would rewrite it: %s', native_sql[:200])
        native_sql = ''
    if result.status == TranslationStatus.FULL and native_sql:
        return native_sql
    logger.debug('Not fully translated (%s): %s', result.status.value, result.reason)
    if not evaluate:
        return None
    try:
        subset = _hybrid_subset(layer, expression, result, native_sql, key_name)
    except Unsupported as exc:
        logger.info('No hybrid subset for %s: %s', layer.name(), exc)
        return None
    except Exception as exc:  # catch-all: the former conversion stays the fallback
        logger.warning('Hybrid subset failed, former conversion used: %s', exc)
        return None
    if not _survives_sanitizer(layer, subset):
        logger.info('Hybrid subset left aside, the subset sanitizer would rewrite it')
        return None
    return subset


def _survives_sanitizer(layer, sql):
    """Whether ``safe_set_subset_string`` would apply ``sql`` unchanged."""
    try:
        from ...core.filter import sanitize_subset_string
        from ...infrastructure.database.sql_utils import _text_field_names
    except ImportError:  # plugin root on sys.path in pure unit tests
        from core.filter import sanitize_subset_string
        from infrastructure.database.sql_utils import _text_field_names
    return sanitize_subset_string(sql, text_fields=_text_field_names(layer)) == sql


def _is_true(value):
    """``QVariant::toBool`` for the value of a condition (TRUE, FALSE or NULL)."""
    if is_null_value(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    raise Unsupported('A condition gave a value that is not a boolean')


def _hybrid_subset(layer, expression, result, native_sql, key_name):
    """Let QGIS evaluate the expression on each feature, then list keys (``native_dialect.hybrid_sql``).

    Every feature is read and evaluated locally: the provider's own compiled
    filter is not used, it may differ from QGIS (QGIS compiles = on reals
    without the tolerance it applies locally). The key is read on every
    feature: unique and never NULL, or no list.
    """
    from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsFeatureRequest
    from .source_capability_probe import feature_count_or_none
    dialect = native_dialect_for_layer(layer)
    if dialect not in (SQLITE, POSTGRESQL):  # OGR SQL: no index on a list, ~5,000 values at most
        raise Unsupported('Hybrid subsets are written for SQLite and PostgreSQL sources only')
    if not result.predicate:
        raise Unsupported('The expression is not a condition')
    if layer.isEditable():
        raise Unsupported('The layer is being edited: its subset cannot change')
    count = feature_count_or_none(layer)
    if count is None or count < 0 or count > HYBRID_MAX_FEATURES:
        raise Unsupported('{} features: unknown, or more than the {} evaluated in QGIS'.format(
            count, HYBRID_MAX_FEATURES))
    fields = layer.dataProvider().fields()
    index = fields.indexFromName(key_name) if key_name else -1
    if index < 0:
        raise Unsupported('No key field of the source: {}'.format(key_name))
    key = key_reference(key_name)
    numeric = fields.at(index).isNumeric()

    context = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
    whole = QgsExpression(expression)
    native = QgsExpression(result.native_expression) if native_sql else None
    for parsed in filter(None, (whole, native)):
        if parsed.hasParserError() or not parsed.prepare(context):
            raise Unsupported('QGIS cannot prepare the expression: {}'.format(parsed.parserErrorString()))
    if native is not None and set(native.referencedColumns()) != set(result.native_columns):
        # node.dump() writes the fields "null", "true", "false" unquoted: other values
        logger.info('Native part left aside: its QGIS text reads %s, not %s',
                    sorted(native.referencedColumns()), sorted(result.native_columns))
        native, native_sql = None, ''

    request = QgsFeatureRequest()
    if not any(parsed.needsGeometry() for parsed in filter(None, (whole, native))):
        request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
    names = set(whole.referencedColumns()) | (set(native.referencedColumns()) if native else set())
    if QgsFeatureRequest.ALL_ATTRIBUTES not in names:
        names.add(key_name)
        request.setSubsetOfAttributes(sorted(names), layer.fields())

    passing, failing, seen = [], ([] if native is not None else None), set()
    for feature in layer.getFeatures(request):
        value = feature[key_name]
        if is_null_value(value) or value in seen:
            raise Unsupported('The key {} is NULL or repeated'.format(key_name))
        seen.add(value)
        context.setFeature(feature)
        kept = _is_true(whole.evaluate(context))
        if whole.hasEvalError():
            raise Unsupported('QGIS cannot evaluate the expression: {}'.format(whole.evalErrorString()))
        in_native = True
        if native is not None:
            in_native = _is_true(native.evaluate(context))
            if native.hasEvalError():
                raise Unsupported('QGIS cannot evaluate the native part: {}'.format(native.evalErrorString()))
        if kept and not in_native:
            raise Unsupported('The native part rejects a feature the expression keeps')
        if kept:
            passing.append(value)
        elif failing is not None and in_native:
            failing.append(value)
    subset = hybrid_sql(native_sql, passing, failing, key, numeric, dialect)
    logger.info('Hybrid subset for %s: %d kept, %s excluded by QGIS from the native part (%s)', layer.name(),
                len(passing), 'no native part' if failing is None else len(failing), result.reason)
    return subset


__all__ = ['field_types', 'native_dialect_for_layer', 'native_subset', 'subset_for_layer', 'translate_for_layer']
