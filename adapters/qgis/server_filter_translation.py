"""Validate a QGIS attribute predicate before handing it to a server provider.

Parsing/OGC conversion is local. No capabilities requests, counts, feature
reads or provider clones occur here. WFS providers consume a QGIS expression
and choose the OGC/FES version negotiated when the layer was opened; the
portable QgsOgcUtils Python overload validates its representability first.
"""
from dataclasses import replace
from weakref import WeakKeyDictionary

try:
    from ...core.domain.source_capability import ServerFilter
    from ...core.filter.server_dialect import Node, ServerFilterError, ServerTranslation, TranslationStatus, Unsupported, translate_node
except ImportError:  # plugin root on sys.path in pure unit tests
    from core.domain.source_capability import ServerFilter
    from core.filter.server_dialect import Node, ServerFilterError, ServerTranslation, TranslationStatus, Unsupported, translate_node
from .source_capability_probe import capability_for_layer

_LAST_ERRORS = WeakKeyDictionary()


def last_server_filter_error(layer):
    """Last application failure for a live layer, cleared before each attempt."""
    return _LAST_ERRORS.get(layer, '')


def remember_server_filter_error(layer, message):
    """Keep a transient UI error, never a source URI or a config value."""
    if message:
        _LAST_ERRORS[layer] = message
    else:
        _LAST_ERRORS.pop(layer, None)


def _tr(text):
    from qgis.PyQt.QtCore import QCoreApplication
    result = QCoreApplication.translate('ServerFilterTranslation', text)
    return result if isinstance(result, str) else text


def _tree(node, depth=0, budget=None):
    """Copy the supported AST shapes; unknown nodes retain their source text."""
    from qgis.core import (
        QgsExpressionNodeBinaryOperator as Binary,
        QgsExpressionNodeColumnRef as Column,
        QgsExpressionNodeInOperator as In,
        QgsExpressionNodeLiteral as Literal,
        QgsExpressionNodeUnaryOperator as Unary,
    )
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    if depth > 64 or budget[0] < 0:
        raise Unsupported('Expression complexity limit exceeded')
    text = node.dump()

    def child(value):
        return _tree(value, depth + 1, budget)

    def enum(owner, scope, name):
        scoped = getattr(owner, scope, None)
        return getattr(scoped, name, getattr(owner, name, None))
    if isinstance(node, Column):
        return Node('column', node.name(), text=text)
    if isinstance(node, Literal):
        return Node('literal', node.value(), text=text)
    if isinstance(node, Binary):
        names = {'boAnd': 'AND', 'boOr': 'OR', 'boEQ': '=', 'boNE': '<>', 'boLT': '<', 'boGT': '>',
                 'boLE': '<=', 'boGE': '>=', 'boLike': 'LIKE', 'boNotLike': 'NOT LIKE',
                 'boILike': 'ILIKE', 'boNotILike': 'NOT ILIKE', 'boIs': 'IS', 'boIsNot': 'IS NOT'}
        for name, operator in names.items():
            if node.op() == enum(Binary, 'BinaryOperator', name):
                return Node('binary', operator, (child(node.opLeft()), child(node.opRight())), text)
    if isinstance(node, In):
        return Node('in', node.isNotIn(), (child(node.node()),) + tuple(child(n) for n in node.list().list()), text)
    if isinstance(node, Unary):
        if node.op() == enum(Unary, 'UnaryOperator', 'uoNot'):
            return Node('unary', 'NOT', (child(node.operand()),), text)
        if node.op() == enum(Unary, 'UnaryOperator', 'uoMinus'):
            operand = child(node.operand())
            if operand.kind == 'literal' and isinstance(operand.value, (int, float)):
                return Node('literal', -operand.value, text=text)
    return Node('unsupported', text, text=text)


def translate(expression, dialect, fields):
    """Translate a string and retain residual AND predicates for lot B.

    Args:
        expression: QGIS attribute predicate, not a native SQL SELECT.
        dialect: wfs, oapif, arcgis, mssql, oracle or hana.
        fields: QgsFields, or an iterable of field names.

    Returns:
        ServerTranslation. Only FULL may be applied without materialization.
    """
    from qgis.core import QgsExpression
    if len(expression) > 65536 or dialect != 'wfs' and '\\' in expression:
        return ServerTranslation(TranslationStatus.NONE, local_expression=expression,
                                 reason=_tr('The expression is too large or contains ambiguous SQL backslash escapes.'))
    parsed = QgsExpression(expression)
    if parsed.hasParserError() or parsed.rootNode() is None:
        return ServerTranslation(TranslationStatus.NONE, local_expression=expression,
                                 reason=_tr('Invalid attribute expression.'))
    types = {}
    for field in fields:
        if isinstance(field, str):
            types[field] = None
            continue
        name = field.typeName().lower()
        if field.isNumeric():
            kind = 'numeric'
        elif 'date' in name or 'time' in name:
            kind = 'date'
        elif name in ('char', 'nchar', 'character', 'national character') or name.startswith(('char(', 'nchar(')):
            kind = 'padded_text'
        elif any(token in name for token in ('string', 'text', 'char')):
            kind = 'text'
        else:
            kind = 'other'
        types[field.name()] = kind
    try:
        result = translate_node(_tree(parsed.rootNode()), dialect, types)
    except (Unsupported, RecursionError):
        return ServerTranslation(TranslationStatus.NONE, local_expression=expression,
                                 reason=_tr('The expression is too complex to translate safely.'))
    if dialect == 'wfs' and result.server_expression:
        from qgis.core import QgsOgcUtils
        from qgis.PyQt.QtXml import QDomDocument
        document = QDomDocument()
        try:
            element = QgsOgcUtils.expressionToOgcFilter(QgsExpression(result.server_expression), document)
            if isinstance(element, tuple):
                element = element[0]
            if element.isNull():
                raise ValueError('OGC compilation failed')
            document.appendChild(element)
        except (ValueError, TypeError, RuntimeError):
            return ServerTranslation(TranslationStatus.NONE, local_expression=expression,
                                     reason=_tr('QGIS cannot translate this predicate to an OGC filter.'))
        result = replace(result, server_expression=document.toString(-1))
    return result


def dialect_for_layer(layer):
    """Select a dialect using the shared source classification, without IO."""
    capability = capability_for_layer(layer)
    if capability is None:
        return None
    if capability.server_filter is ServerFilter.OGC_FILTER:
        # OGR's WFS driver consumes OGR SQL, not the QGIS WFS expression
        # dialect. Until its translation is proven it must fail closed.
        return 'wfs' if capability.provider_key == 'wfs' else 'unsupported'
    if capability.server_filter is ServerFilter.CQL2:
        return 'oapif'
    if capability.provider_key == 'arcgisfeatureserver':
        return 'arcgis'
    if capability.provider_key in ('mssql', 'oracle', 'hana'):
        return capability.provider_key
    if capability.provider_key == 'ogr' and not capability.counts_cheaply and not capability.is_remote:
        source = layer.source().lstrip().strip('"').strip("'").upper()
        if source.startswith('MSSQL:'):
            return 'mssql'
        if source.startswith('OCI:'):
            return 'oracle'
        return 'unsupported'
    if not capability.counts_cheaply and not capability.is_remote:
        return 'unsupported'
    if capability.is_remote_service:
        return 'unsupported'
    return None


def prepare_server_subset(layer, expression, *, rect=None, limits=None, feedback=None):
    """Return validated provider input without modifying the layer.

    An explicit rect opts a worker caller into a bounded local fallback.
    Without one, PARTIAL/NONE retain the existing clear refusal. A partial
    copy is refused here because this API cannot return a warning outcome.
    """
    if rect is not None:
        from .remote_materializer import require_worker
        from qgis.PyQt.QtCore import QThread
        try:
            require_worker()
        except RuntimeError as exc:
            raise ServerFilterError(str(exc)) from None
        if layer.thread() != QThread.currentThread():
            raise ServerFilterError(_tr('A server layer can only be modified on its owning thread.'))
    dialect = dialect_for_layer(layer)
    if dialect is None or not expression or not expression.strip():
        return expression
    # Joined and virtual fields cannot be evaluated by the source provider.
    provider = layer.dataProvider() if hasattr(layer, 'dataProvider') else None
    fields = provider.fields() if provider is not None else layer.fields()
    result = translate(expression, dialect, fields)
    if result.status != TranslationStatus.FULL:
        if rect is not None:
            from .remote_materializer import materialize_translation, unfiltered_snapshot
            from ..backends.ogr.filter_executor import _remote_message
            from ...core.filter.pk_formatter import QGIS_EXPRESSION, format_key_literal
            from .source_capability_probe import stable_key_for_layer
            if dialect not in ('wfs', 'arcgis'):
                # These providers cannot accept a proven final key filter.
                # Standalone materialization still exposes bounded OAPIF keys.
                raise ServerFilterError(_remote_message('unverified_filter'))
            outcome = materialize_translation(unfiltered_snapshot(layer), rect, result, limits, feedback)
            if not outcome.complete:
                raise ServerFilterError(_remote_message(outcome.reason))
            key = stable_key_for_layer(layer, scan=False)
            if not key.is_field:
                raise ServerFilterError(_remote_message('no_stable_key'))
            index = fields.indexFromName(key.name)
            if index < 0:
                raise ServerFilterError(_remote_message('no_stable_key'))
            name = '"' + key.name.replace('"', '""') + '"'
            subset = '{} IN ({})'.format(name, ', '.join(
                format_key_literal(value, fields.at(index).isNumeric(), QGIS_EXPRESSION)
                for value in outcome.keys
            )) if outcome.keys else '1 = 0'
            verified = translate(subset, dialect, fields)
            if verified.status != TranslationStatus.FULL:
                raise ServerFilterError(_remote_message('unverified_filter'))
            return verified.subset_expression
        raise ServerFilterError(_tr(
            '{0}: the attribute filter cannot run entirely on the server. '
            'Unsupported part: {1}. {2} The previous filter is unchanged.'
        ).format(layer.name(), result.local_expression, result.reason))
    return result.subset_expression


def apply_server_subset(layer, expression, *, _trusted_restore=False):
    """Apply a prevalidated remote subset and restore the old one on failure.

    Must be called on the layer's owning thread. This method performs no
    feature reads/counts and does not probe a service for filter support.
    """
    subset = expression if _trusted_restore else prepare_server_subset(layer, expression)
    before = layer.subsetString()
    from qgis.core import QgsApplication, QgsVectorLayer
    from qgis.PyQt.QtCore import QThread
    if isinstance(QgsVectorLayer, type) and isinstance(layer, QgsVectorLayer):
        if QThread.currentThread() == QgsApplication.instance().thread():
            from .server_subset_job import (
                SYNC, apply_server_subset_sync, apply_server_subset_wait, cancel_pending_server_subset,
                transfer_mode_for_layer,
            )
            cancel_pending_server_subset(layer)
            if subset == before and layer.isValid():
                return True
            if transfer_mode_for_layer(layer) == SYNC:
                return apply_server_subset_sync(layer, subset)
            return apply_server_subset_wait(layer, expression, trusted_restore=_trusted_restore)
        if QThread.currentThread() != layer.thread():
            raise ServerFilterError(_tr('A server layer can only be modified on its owning thread.'))
    if subset == before and layer.isValid():
        return True
    try:
        accepted = layer.setSubsetString(subset)
        if accepted and layer.isValid():
            return True
    except Exception:  # nosec B110 - provider details may contain credentials
        pass
    try:
        if layer.subsetString() != before or not layer.isValid():
            if not layer.setSubsetString(before) or not layer.isValid():
                raise ValueError('Restoration rejected')
    except Exception:  # nosec B110 - report the failure without a source URI
        raise ServerFilterError(_tr('{0}: the provider rejected the filter and restoration failed.').format(layer.name()))
    raise ServerFilterError(_tr('{0}: the provider rejected the attribute filter. The previous filter was restored.').format(layer.name()))


def restore_server_subset(layer, accepted_subset):
    """Replay an exact provider-accepted history snapshot without reparsing it.

    Only undo/redo calls this. Favorites, REST, MCP and user expressions use
    the validating application path, even when they resemble native SQL.
    """
    return apply_server_subset(layer, accepted_subset, _trusted_restore=True)
