"""Pure rules for a deliberately small subset of server attribute filters.

Only AND may be split. A partial OR or NOT must stay entirely local.
Provider syntax is selected from source_capability by the QGIS adapter.
"""
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Tuple

from ..domain.source_capability import ORACLE_IN_LIST_MAX, REMOTE_KEY_LIST_LIMIT
from .pk_formatter import QGIS_EXPRESSION, SQL, format_key_literal, is_null_value


class TranslationStatus(str, Enum):
    """Whether the whole predicate can be evaluated by the server."""

    FULL = 'FULL'
    PARTIAL = 'PARTIAL'
    NONE = 'NONE'


@dataclass(frozen=True)
class ServerTranslation:
    """Translation contract shared with the bounded remote materializer.

    Attributes:
        status: FULL only when no residual predicate remains.
        server_expression: Server predicate (OGC XML for WFS).
        local_expression: Original QGIS predicate requiring local evaluation.
        reason: Explanation of unsupported constructs, without source URIs.
        subset_expression: Input expected by the QGIS provider. WFS/OAPIF
            providers consume QGIS syntax and generate their protocol dialect.
    """

    status: TranslationStatus
    server_expression: str = ''
    local_expression: str = ''
    reason: str = ''
    subset_expression: str = ''


@dataclass(frozen=True)
class Node:
    """QGIS-independent expression tree populated by the adapter."""

    kind: str
    value: Any = None
    children: Tuple['Node', ...] = ()
    text: str = ''


class Unsupported(ValueError):
    """An expression cannot be sent without changing its meaning."""


class ServerFilterError(ValueError):
    """A server filter could not be applied completely and safely."""


def _render(node: Node, dialect: str, fields: Iterable[str], ilike_exact: bool) -> str:
    if node.kind == 'column':
        if node.value not in fields:
            raise Unsupported('Unknown field: {}'.format(node.value))
        return '"' + node.value.replace('"', '""') + '"'
    if node.kind == 'literal':
        value = node.value
        if is_null_value(value):
            return 'NULL'
        if isinstance(value, bool):
            # SQL boolean syntax is not portable to Oracle/MSSQL.
            raise Unsupported('Boolean literal semantics are not proven for this provider')
        if not isinstance(value, (str, int, float)) or isinstance(value, float) and not math.isfinite(value):
            raise Unsupported('Unsupported literal type')
        if dialect == 'oracle' and value == '':
            raise Unsupported('Oracle treats an empty string as NULL')
        if dialect == 'oracle' and isinstance(value, str) and not value.isascii():
            raise Unsupported('Oracle non-ASCII literals require a proven database character set')
        rendered = format_key_literal(value, isinstance(value, (int, float)),
                                      QGIS_EXPRESSION if dialect == 'wfs' else SQL)
        return 'N' + rendered if dialect == 'mssql' and isinstance(value, str) else rendered
    if node.kind == 'binary':
        op = node.value
        left, right = node.children
        if op in ('AND', 'OR'):
            return '({} {} {})'.format(_predicate(left, dialect, fields, ilike_exact), op,
                                      _predicate(right, dialect, fields, ilike_exact))
        if op not in ('=', '<>', '<', '>', '<=', '>=', 'LIKE', 'NOT LIKE', 'ILIKE', 'NOT ILIKE', 'IS', 'IS NOT'):
            raise Unsupported('Unsupported operator: {}'.format(op))
        if op in ('IS', 'IS NOT') and not (right.kind == 'literal' and is_null_value(right.value)):
            raise Unsupported('Only IS NULL and IS NOT NULL are portable')
        if any(child.kind not in ('column', 'literal') for child in (left, right)):
            raise Unsupported('Comparison operands must be fields or literals')
        if op in ('LIKE', 'NOT LIKE', 'ILIKE', 'NOT ILIKE') and dialect != 'wfs':
            if right.kind != 'literal' or not isinstance(right.value, str) or any(
                    char in right.value for char in ('\\', '[', ']')):
                raise Unsupported('LIKE pattern semantics are not portable')
        a = _render(left, dialect, fields, ilike_exact)
        b = _render(right, dialect, fields, ilike_exact)
        if op in ('ILIKE', 'NOT ILIKE') and dialect != 'wfs':
            if not ilike_exact:
                raise Unsupported('ILIKE requires proven case and collation semantics')
            return '(UPPER({}) {} UPPER({}))'.format(a, op.replace('ILIKE', 'LIKE'), b)
        return '({} {} {})'.format(a, op, b)
    if node.kind == 'in':
        if len(node.children) < 2:
            raise Unsupported('Empty IN list')
        if dialect == 'oracle' and len(node.children) - 1 > ORACLE_IN_LIST_MAX:
            raise Unsupported('Oracle IN list exceeds 1000 values')
        if any(child.kind != 'literal' for child in node.children[1:]):
            raise Unsupported('IN requires a list of literals')
        return '({} {}IN ({}))'.format(
            _render(node.children[0], dialect, fields, ilike_exact), 'NOT ' if node.value else '',
            ', '.join(_render(child, dialect, fields, ilike_exact) for child in node.children[1:]))
    if node.kind == 'unary' and node.value == 'NOT':
        return '(NOT {})'.format(_predicate(node.children[0], dialect, fields, ilike_exact))
    raise Unsupported('Unsupported expression: {}'.format(node.value or node.kind))


def _predicate(node, dialect, fields, ilike_exact):
    if node.kind not in ('binary', 'in', 'unary'):
        raise Unsupported('A filter must be a predicate')
    return _render(node, dialect, fields, ilike_exact)


def _check_semantics(node, dialect, types, text_semantics_exact):
    pending = [node]
    in_values = 0
    while pending:
        part = pending.pop()
        pending.extend(part.children)
        if dialect == 'wfs' and ((part.kind == 'unary' and part.value == 'NOT') or
                                 (part.kind == 'binary' and part.value in ('<>', 'NOT LIKE', 'NOT ILIKE')) or
                                 (part.kind == 'in' and part.value)):
            raise Unsupported('WFS negation requires proven non-null field semantics')
        if part.kind == 'in':
            in_values += len(part.children) - 1
            if not part.children or part.children[0].kind != 'column':
                raise Unsupported('IN requires a field on the left')
            pairs = [(part.children[0], child) for child in part.children[1:]]
        elif part.kind == 'binary' and part.value not in ('AND', 'OR'):
            a, b = part.children
            if a.kind != 'column' and b.kind != 'column':
                if dialect == 'wfs' or any(child.kind != 'literal' or not isinstance(child.value, (int, float))
                                            for child in (a, b)):
                    raise Unsupported('A comparison must reference a field')
            if any(child.kind == 'literal' and is_null_value(child.value) for child in (a, b)) and (
                    part.value not in ('IS', 'IS NOT')):
                raise Unsupported('Use IS NULL or IS NOT NULL for null values')
            if part.value in ('LIKE', 'NOT LIKE', 'ILIKE', 'NOT ILIKE') and a.kind != 'column':
                raise Unsupported('LIKE requires a field on the left')
            pairs = [(a, b)]
        else:
            continue
        for a, b in pairs:
            for field, literal in ((a, b), (b, a)):
                if field.kind != 'column' or literal.kind != 'literal' or is_null_value(literal.value):
                    continue
                kind = types.get(field.value)
                value = literal.value
                if kind not in (None, 'text', 'numeric') or (kind == 'text' and not isinstance(value, str)) or (
                        kind == 'numeric' and not isinstance(value, (int, float))):
                    raise Unsupported('Field and literal types are not portable to the server')
                if isinstance(value, str):
                    if dialect in ('arcgis', 'mssql') and not text_semantics_exact:
                        raise Unsupported('Text comparison requires proven server case and collation semantics')
                    if part.kind == 'binary' and part.value in ('<', '>', '<=', '>='):
                        raise Unsupported('Text ordering depends on server collation')
            if a.kind == b.kind == 'column' and types.get(a.value) != types.get(b.value):
                raise Unsupported('Compared fields must have matching types')
            if a.kind == b.kind == 'column' and types.get(a.value) not in (None, 'text', 'numeric'):
                raise Unsupported('Compared field types are not portable to the server')
            if a.kind == b.kind == 'column' and types.get(a.value) == 'text':
                if dialect in ('mssql', 'arcgis') and not text_semantics_exact:
                    raise Unsupported('Text comparison requires proven server case and collation semantics')
                if part.kind == 'binary' and part.value in ('<', '>', '<=', '>='):
                    raise Unsupported('Text ordering depends on server collation')
    if dialect in ('wfs', 'arcgis') and in_values > REMOTE_KEY_LIST_LIMIT:
        raise Unsupported('Remote IN lists exceed the shared key-list limit')


def translate_node(node: Node, dialect: str, fields: Iterable[str], ilike_exact: bool = False,
                   text_semantics_exact: bool = False) -> ServerTranslation:
    """Translate a predicate, splitting top-level AND only.

    Args:
        node: Tree from the QGIS adapter, retaining original text.
        dialect: wfs, arcgis, mssql, oracle, hana or oapif.
        fields: Actual field names, compared exactly.
        ilike_exact: True only with evidence that UPPER has the same case
            semantics as QGIS. Never inferred from a provider name.
        text_semantics_exact: Evidence for SQL Server/ArcGIS text comparison
            semantics. Without it, text predicates remain local.

    Returns:
        ServerTranslation with no silently discarded residual expression.
    """
    types = fields if isinstance(fields, dict) else {}
    fields = frozenset(fields)
    server, local, reasons = [], [], []

    def visit(part):
        if part.kind == 'binary' and part.value == 'AND':
            for child in part.children:
                visit(child)
            return
        try:
            if dialect == 'oapif':
                raise Unsupported('This provider does not expose a complete CQL2 translation verdict')
            if dialect not in ('wfs', 'arcgis', 'mssql', 'oracle', 'hana'):
                raise Unsupported('Unsupported server dialect')
            if dialect == 'wfs' and fields and part.kind == 'binary' and part.value == '=' and all(
                    child.kind == 'literal' and type(child.value) in (int, float) and
                    (not isinstance(child.value, float) or math.isfinite(child.value)) for child in part.children):
                # OGC literal-only predicates are not portable. Key-list
                # empty/all sentinels can use a field tautology/contradiction.
                marker = Node('column', sorted(fields)[0])
                null = Node('literal', None)
                part = Node('binary', 'OR' if part.children[0].value == part.children[1].value else 'AND',
                            (Node('binary', 'IS', (marker, null)), Node('binary', 'IS NOT', (marker, null))), part.text)
            _check_semantics(part, dialect, types, text_semantics_exact)
            server.append(_predicate(part, dialect, fields, ilike_exact))
        except Unsupported as exc:
            local.append('(' + part.text + ')')
            reasons.append(str(exc))

    pending, in_values = [node], 0
    while pending:
        part = pending.pop()
        pending.extend(part.children)
        if part.kind == 'in':
            in_values += len(part.children) - 1
    if dialect in ('wfs', 'arcgis') and in_values > REMOTE_KEY_LIST_LIMIT:
        return ServerTranslation(TranslationStatus.NONE, local_expression=node.text,
                                 reason='Remote IN lists exceed the shared key-list limit')
    try:
        visit(node)
    except RecursionError:
        return ServerTranslation(TranslationStatus.NONE, local_expression=node.text,
                                 reason='Expression complexity limit exceeded')
    status = TranslationStatus.PARTIAL if server and local else (
        TranslationStatus.NONE if local else TranslationStatus.FULL)
    expression = ' AND '.join(server)
    return ServerTranslation(status, expression, ' AND '.join(local), '; '.join(dict.fromkeys(reasons)), expression)
