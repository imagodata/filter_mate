"""QGIS attribute predicate to the native SQL of a layer's own data source.

The subset string of a database or file layer is read by its source, not by
QGIS: PostgreSQL, SQLite (GeoPackage, SpatiaLite) or the OGR SQL engine
(Shapefile, other files). This module writes a QGIS predicate in one of those
languages from its syntax tree (:class:`server_dialect.Node`, filled by the
QGIS adapter), and only where the source gives the answer QGIS gives:

- operands are typed: a comparison is written when both sides are numbers or
  both are texts. QGIS converts a text holding a number, SQL engines do not
  agree on it, so a mixed comparison stays untranslated;
- QGIS compares numbers in double precision, ``=`` / ``<>`` with a tolerance
  of 4 DBL_EPSILON (``qgsDoubleNear``): the equality of a real is written with
  that tolerance, IN on reals and integer literals beyond 2^53 are not written;
- text ordering (``<``, ``>``) follows a collation: never written;
- PostgreSQL: ``/`` is a float division in QGIS and NULL on a zero divisor
  (PostgreSQL truncates integers and raises), an arithmetic on reals is run in
  double precision as QGIS runs it (``numeric`` is exact);
- SQLite: a column may declare a collation (NOCASE, RTRIM), so the equality
  of texts is written ``COLLATE BINARY``; ``LIKE`` ignores the case of ASCII
  letters and follows a pragma, so LIKE and ILIKE are both written with
  ``GLOB`` (ILIKE with a class per letter, ``k`` also matching the Kelvin sign
  and ``s`` the long s, as the case-insensitive regular expression of QGIS
  does), for ASCII patterns only;
- OGR SQL: the equality of texts ignores case, ``CASE`` does not exist: text
  comparisons, LIKE, CASE and functions stay untranslated; a division is
  written for a literal divisor only (an integer division truncates, a zero
  divisor gives a number where QGIS gives NULL); ``TRUE AND NULL`` is FALSE
  there, not NULL, so a NOT over an AND is not written; BETWEEN takes literal
  bounds of the type of its value only (the engine reads the third operand
  with the type of the first two).

Known limits, not detected: an integer arithmetic that overflows 64 bits
(QGIS wraps, SQLite turns to a real), integer field values beyond 2^53
(compared exactly by the source), data values that do not match the declared
type of a SQLite column, and NaN produced from infinite field values.

Only a top-level AND is split. What cannot be written is returned as QGIS
text (``local_expression``), never dropped: the caller keeps its former path
(evaluation by QGIS, list of keys) for a PARTIAL or NONE result.
"""
import math
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Tuple

from .pk_formatter import is_null_value
from .server_dialect import Node, TranslationStatus, Unsupported

POSTGRESQL = 'postgresql'
SQLITE = 'sqlite'
OGR_SQL = 'ogr_sql'
DIALECTS = (POSTGRESQL, SQLITE, OGR_SQL)

# Types of a value. A field of another type (date, char(n), citext, json...)
# is 'other': it can only be tested with IS NULL.
INT, REAL, TEXT, BOOL, NULL, OTHER = 'int', 'real', 'text', 'bool', 'null', 'other'
_NUMERIC = (INT, REAL)

_COMPARISONS = ('=', '<>', '<', '>', '<=', '>=')
_LIKES = ('LIKE', 'NOT LIKE', 'ILIKE', 'NOT ILIKE')
_ARITHMETIC = ('+', '-', '*', '/')
_MAX_DEPTH = 64

# qgsDoubleNear( diff, 0.0 ): diff > -eps && diff <= eps
_EPSILON = 4 * sys.float_info.epsilon
# The largest integer a double holds exactly.
_EXACT_INTEGER = 2 ** 53
# Identifier spellings that OGR SQL does not read, or that the subset
# sanitizer reads as a comment (it does not skip quoted identifiers).
_IDENTIFIER_REFUSED = ('"', '\\', '--', '/*', '*/')
# Other cases of k and s in a Unicode case-insensitive regular expression.
_OTHER_CASES = {'k': 'K', 's': 'ſ'}


@dataclass(frozen=True)
class NativeTranslation:
    """A predicate written for the data source.

    Attributes:
        status: FULL when ``sql`` alone is the whole predicate.
        sql: Native predicate of the translated AND operands ('' when none).
        local_expression: QGIS text of the operands left untranslated.
        reason: Why they were left (first reason of each, deduplicated).
    """

    status: TranslationStatus
    sql: str = ''
    local_expression: str = ''
    reason: str = ''


def _class(kind: str) -> str:
    return 'number' if kind in _NUMERIC else kind


class _Writer:
    """Writes one AND operand; raises :class:`Unsupported` on anything unproven."""

    def __init__(self, dialect: str, types: Dict[str, Optional[str]]):
        self.dialect = dialect
        self.types = types
        self.ands = 0  # AND written so far, user's or ours (OGR SQL: no NOT over one)

    # -- values -----------------------------------------------------------------

    def value(self, node: Node, depth: int = 0) -> Tuple[str, str]:
        """``(sql, type)`` of a node read as a value."""
        if depth > _MAX_DEPTH:
            raise Unsupported('Expression complexity limit exceeded')
        kind = node.kind
        if kind == 'column':
            return self._column(node.value)
        if kind == 'literal':
            return self._literal(node.value)
        if kind == 'unary' and node.value == '-':
            sql, type_ = self.value(node.children[0], depth + 1)
            if type_ not in _NUMERIC:
                raise Unsupported('The sign of a value that is not a number')
            # never "--", a comment in SQL
            return ('(- {})' if sql.startswith('-') else '(-{})').format(sql), type_
        if kind == 'binary' and node.value in _ARITHMETIC:
            return self._arithmetic(node, depth)
        if kind == 'binary' and node.value == '||':
            return self._concat(node, depth)
        if kind == 'condition':
            return self._case(node, depth)
        if kind == 'function':
            return self._function(node, depth)
        raise Unsupported('Not translated: {}'.format(node.text or node.value or kind))

    def _column(self, name) -> Tuple[str, str]:
        if not isinstance(name, str) or name not in self.types:
            raise Unsupported('Not a field of the data source: {}'.format(name))
        if any(part in name for part in _IDENTIFIER_REFUSED) or any(ord(char) < 32 for char in name):
            raise Unsupported('A field name that cannot be written safely: {}'.format(name))
        return '"' + name + '"', self.types[name] or OTHER

    def _literal(self, value) -> Tuple[str, str]:
        if is_null_value(value):
            return 'NULL', NULL
        if isinstance(value, bool):
            if self.dialect != POSTGRESQL:
                raise Unsupported('A boolean literal has no portable writing')
            return ('TRUE' if value else 'FALSE'), BOOL
        if isinstance(value, int):
            if abs(value) > _EXACT_INTEGER:
                raise Unsupported('An integer beyond 2^53: QGIS compares it in double precision')
            return str(value), INT
        if isinstance(value, float):
            if not math.isfinite(value):
                raise Unsupported('A number that is not finite')
            if self.dialect == OGR_SQL:
                # no exponent: 1e-05 is written 0.00001
                written = format(Decimal(repr(value)), 'f')
                return (written if '.' in written else written + '.0'), REAL
            return repr(value), REAL
        if isinstance(value, str):
            if '\x00' in value:
                raise Unsupported('A text holding a NUL character')
            if '\\' in value:
                # OGR SQL reads \' as a quote, PostgreSQL may (standard_conforming_strings),
                # and the subset sanitizer reads it as a QGIS escape.
                raise Unsupported('A backslash in a text is read differently downstream')
            return "'" + value.replace("'", "''") + "'", TEXT
        raise Unsupported('A literal of an unknown type')

    def _arithmetic(self, node: Node, depth: int) -> Tuple[str, str]:
        operator = node.value
        (left, left_type), (right, right_type) = (self.value(child, depth + 1) for child in node.children)
        if left_type not in _NUMERIC or right_type not in _NUMERIC:
            raise Unsupported('Arithmetic on values that are not numbers')
        if operator == '/':
            # QGIS: always a float division, NULL when the divisor is 0.
            if self.dialect == POSTGRESQL:
                return '(CAST({} AS double precision) / NULLIF({}, 0))'.format(left, right), REAL
            if self.dialect == SQLITE:
                return '(CAST({} AS REAL) / {})'.format(left, right), REAL
            # OGR SQL truncates integers and gives a number, not NULL, on a zero
            # divisor: written for a literal divisor other than 0, as a real.
            divisor = node.children[1].value if node.children[1].kind == 'literal' else None
            if isinstance(divisor, (int, float)) and not isinstance(divisor, bool) and divisor != 0:
                return '({} / {})'.format(left, self._literal(float(divisor))[0]), REAL
            raise Unsupported('A division by a value that may be 0 is not NULL in OGR SQL')
        if left_type == INT and right_type == INT:
            return '({} {} {})'.format(left, operator, right), INT
        if self.dialect == POSTGRESQL:
            # numeric arithmetic is exact, QGIS computes in double precision
            left = 'CAST({} AS double precision)'.format(left)
        return '({} {} {})'.format(left, operator, right), REAL

    def _concat(self, node: Node, depth: int) -> Tuple[str, str]:
        if self.dialect == OGR_SQL:
            raise Unsupported('Text concatenation is not written in OGR SQL')
        parts = [self.value(child, depth + 1) for child in node.children]
        if any(type_ != TEXT for _, type_ in parts):
            raise Unsupported('Concatenation of values that are not texts')
        return '({} || {})'.format(parts[0][0], parts[1][0]), TEXT

    def _merged_type(self, types) -> str:
        known = [type_ for type_ in types if type_ != NULL]
        if not known:
            raise Unsupported('Only NULL values')
        classes = {_class(type_) for type_ in known}
        if len(classes) != 1 or classes == {OTHER}:
            raise Unsupported('Values of different types')
        if classes == {'number'}:
            return INT if all(type_ == INT for type_ in known) else REAL
        return known[0]

    def _case(self, node: Node, depth: int) -> Tuple[str, str]:
        if self.dialect == OGR_SQL:
            raise Unsupported('CASE does not exist in OGR SQL')
        children = list(node.children)
        otherwise = children.pop() if node.value else None
        if not children or len(children) % 2:
            raise Unsupported('A CASE without a complete WHEN ... THEN')
        parts, types = [], []
        for index in range(0, len(children), 2):
            then, then_type = self.value(children[index + 1], depth + 1)
            parts.append('WHEN {} THEN {}'.format(self.predicate(children[index], depth + 1), then))
            types.append(then_type)
        if otherwise is not None:
            other, other_type = self.value(otherwise, depth + 1)
            parts.append('ELSE {}'.format(other))
            types.append(other_type)
        return '(CASE {} END)'.format(' '.join(parts)), self._merged_type(types)

    def _function(self, node: Node, depth: int) -> Tuple[str, str]:
        name = str(node.value).lower()
        if self.dialect == OGR_SQL:
            raise Unsupported('Functions are not written in OGR SQL: {}'.format(name))
        count = len(node.children)
        if name == 'if' and count == 3:
            # if(c, a, b): b when c is false or NULL, as CASE ... ELSE
            return self._case(Node('condition', True, node.children, node.text), depth)
        arguments = [self.value(child, depth + 1) for child in node.children]
        types = [type_ for _, type_ in arguments]
        text = ', '.join(sql for sql, _ in arguments)
        if name == 'coalesce' and count >= 2:  # SQLite refuses COALESCE(x)
            return 'COALESCE({})'.format(text), self._merged_type(types)
        if name == 'abs' and count == 1 and types[0] in _NUMERIC:
            # a double in QGIS (no overflow on the smallest integer)
            real = 'double precision' if self.dialect == POSTGRESQL else 'REAL'
            return '{}(CAST({} AS {}))'.format(name, text, real), REAL
        if name in ('lower', 'upper') and count == 1 and types[0] == TEXT and self.dialect == POSTGRESQL:
            # SQLite folds ASCII letters only
            return '{}({})'.format(name, text), TEXT
        if name in ('floor', 'ceil') and count == 1 and types[0] in _NUMERIC and self.dialect == POSTGRESQL:
            return '{}(CAST({} AS double precision))'.format(name, text), REAL
        # length(): QGIS counts UTF-16 code units, the sources count characters.
        raise Unsupported('Function not translated: {}'.format(name))

    # -- predicates -------------------------------------------------------------

    def predicate(self, node: Node, depth: int = 0) -> str:
        """SQL of a node read as a condition."""
        if depth > _MAX_DEPTH:
            raise Unsupported('Expression complexity limit exceeded')
        kind = node.kind
        if kind == 'binary':
            operator = node.value
            if operator in ('AND', 'OR'):
                if operator == 'AND':
                    self.ands += 1
                return '({} {} {})'.format(self.predicate(node.children[0], depth + 1), operator,
                                          self.predicate(node.children[1], depth + 1))
            if operator in ('IS', 'IS NOT'):
                return self._is_null(node, depth)
            if operator in _COMPARISONS:
                return self._comparison(node, depth)
            if operator in _LIKES:
                return self._like(node, depth)
        if kind == 'unary' and node.value == 'NOT':
            before = self.ands
            operand = self.predicate(node.children[0], depth + 1)
            if self.dialect == OGR_SQL and self.ands != before:
                raise Unsupported('OGR SQL gives FALSE to TRUE AND NULL, so a NOT over an AND would keep it')
            return '(NOT {})'.format(operand)
        if kind == 'in':
            return self._in(node, depth)
        if kind == 'between':
            return self._between(node, depth)
        raise Unsupported('Not a condition that can be written: {}'.format(node.text or node.value or kind))

    def _is_null(self, node: Node, depth: int) -> str:
        left, right = node.children
        if right.kind != 'literal' or not is_null_value(right.value):
            raise Unsupported('Only IS NULL and IS NOT NULL are written')
        sql, _ = self.value(left, depth + 1)
        return '({} {} NULL)'.format(sql, node.value)

    def _comparable(self, left_type: str, right_type: str, ordering: bool) -> None:
        if NULL in (left_type, right_type):
            raise Unsupported('Use IS NULL or IS NOT NULL for null values')
        kind = _class(left_type)
        if kind != _class(right_type) or kind == OTHER:
            raise Unsupported('Compared values are not of the same type (QGIS converts them, the source may not)')
        if kind == TEXT:
            if ordering:
                raise Unsupported('Text ordering depends on the collation of the data source')
            if self.dialect == OGR_SQL:
                raise Unsupported('OGR SQL compares texts without their case')
        if kind == BOOL and ordering:
            raise Unsupported('Ordering of booleans')

    def _binary_text(self, sql: str, type_: str) -> str:
        """SQLite: the left operand of a text equality, whatever the column's collation."""
        return sql + ' COLLATE BINARY' if self.dialect == SQLITE and type_ == TEXT else sql

    def _comparison(self, node: Node, depth: int) -> str:
        (left, left_type), (right, right_type) = (self.value(child, depth + 1) for child in node.children)
        operator = node.value
        self._comparable(left_type, right_type, operator not in ('=', '<>'))
        if operator in ('=', '<>') and REAL in (left_type, right_type):
            # qgsDoubleNear on the difference, as QGIS compares
            difference, _ = self._arithmetic(Node('binary', '-', node.children, node.text), depth)
            epsilon = self._literal(_EPSILON)[0]
            if operator == '=':
                self.ands += 1
                return '({0} > -{1} AND {0} <= {1})'.format(difference, epsilon)
            return '({0} <= -{1} OR {0} > {1})'.format(difference, epsilon)
        return '({} {} {})'.format(self._binary_text(left, left_type), operator, right)

    def _in(self, node: Node, depth: int) -> str:
        if len(node.children) < 2:
            raise Unsupported('Empty IN list')
        left, left_type = self.value(node.children[0], depth + 1)
        items = []
        for child in node.children[1:]:
            if child.kind != 'literal':
                raise Unsupported('IN requires a list of literals')
            sql, type_ = self.value(child, depth + 1)
            self._comparable(left_type, type_, False)
            if REAL in (left_type, type_):
                raise Unsupported('IN on real numbers: QGIS compares them with a tolerance')
            items.append(sql)
        return '({} {}IN ({}))'.format(self._binary_text(left, left_type), 'NOT ' if node.value else '',
                                      ', '.join(items))

    def _between(self, node: Node, depth: int) -> str:
        value_node, low_node, high_node = node.children
        sql, type_ = self.value(value_node, depth + 1)
        if type_ not in _NUMERIC:
            raise Unsupported('BETWEEN is written for numbers only')
        bounds = []
        for bound in (low_node, high_node):
            if self.dialect == OGR_SQL:
                if bound.kind != 'literal':
                    raise Unsupported('OGR SQL reads a BETWEEN bound with the type of the first two operands')
                written, bound_type = self._literal(bound.value)
                if bound_type == REAL and type_ == INT:
                    raise Unsupported('OGR SQL reads a BETWEEN bound with the type of the first two operands')
                if bound_type == INT and type_ == REAL:
                    written = self._literal(float(bound.value))[0]
            else:
                written, bound_type = self.value(bound, depth + 1)
            if bound_type not in _NUMERIC:
                raise Unsupported('BETWEEN is written for numbers only')
            bounds.append(written)
        return '({} {}BETWEEN {} AND {})'.format(sql, 'NOT ' if node.value else '', *bounds)

    def _like(self, node: Node, depth: int) -> str:
        left_node, right_node = node.children
        if right_node.kind != 'literal' or not isinstance(right_node.value, str):
            raise Unsupported('LIKE requires a text pattern')
        left, left_type = self.value(left_node, depth + 1)
        if left_type != TEXT:
            raise Unsupported('LIKE on a value that is not a text')
        pattern = right_node.value
        negated = node.value.startswith('NOT ')
        insensitive = node.value.endswith('ILIKE')
        if self.dialect == POSTGRESQL:
            right, _ = self._literal(pattern)  # refuses a backslash: no escape to translate
            return '({} {} {})'.format(left, node.value, right)
        if self.dialect == SQLITE:
            if not pattern.isascii() or '\\' in pattern:
                raise Unsupported('A LIKE pattern that is not ASCII or holds an escape')
            if any(char in pattern for char in '*?['):
                raise Unsupported('A LIKE pattern holding GLOB wildcards')
            glob = []
            for char in pattern:
                if char == '%':
                    glob.append('*')
                elif char == '_':
                    glob.append('?')
                elif insensitive and char.isalpha():
                    lower = char.lower()
                    glob.append('[' + lower + lower.upper() + _OTHER_CASES.get(lower, '') + ']')
                else:
                    glob.append(char)
            written = '{} GLOB {}'.format(left, self._literal(''.join(glob))[0])
            return '(NOT ({}))'.format(written) if negated else '({})'.format(written)
        raise Unsupported('LIKE is not the same in OGR SQL')


def _strip_outer_parentheses(sql: str) -> str:
    """``(a = 1)`` -> ``a = 1`` when the first parenthesis closes at the end."""
    if not (sql.startswith('(') and sql.endswith(')')):
        return sql
    depth, quote = 0, ''
    for index, char in enumerate(sql):
        if quote:
            if char == quote:
                quote = ''
        elif char in ('"', "'"):
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0 and index != len(sql) - 1:
                return sql
    return sql[1:-1]


def translate_native(node: Node, dialect: str, types: Dict[str, Optional[str]]) -> NativeTranslation:
    """Write a QGIS predicate for a data source, splitting a top-level AND only.

    Args:
        node: Tree from the QGIS adapter, each node keeping its QGIS text.
        dialect: ``postgresql``, ``sqlite`` or ``ogr_sql``.
        types: Type of each field of the data source, by exact name: ``int``,
            ``real``, ``text``, ``bool`` or ``other`` (None reads as other).

    Returns:
        NativeTranslation; nothing is dropped, the untranslated operands are
        returned as QGIS text.
    """
    if dialect not in DIALECTS:
        return NativeTranslation(TranslationStatus.NONE, local_expression=node.text,
                                 reason='Unknown dialect: {}'.format(dialect))
    written, local, reasons = [], [], []

    def visit(part: Node) -> None:
        if part.kind == 'binary' and part.value == 'AND':
            for child in part.children:
                visit(child)
            return
        try:
            written.append(_Writer(dialect, types).predicate(part))
        except Unsupported as exc:
            local.append('(' + part.text + ')')
            reasons.append(str(exc))

    try:
        visit(node)
    except RecursionError:
        return NativeTranslation(TranslationStatus.NONE, local_expression=node.text,
                                 reason='Expression complexity limit exceeded')
    status = TranslationStatus.PARTIAL if written and local else (
        TranslationStatus.NONE if local else TranslationStatus.FULL)
    sql = _strip_outer_parentheses(written[0]) if len(written) == 1 else ' AND '.join(written)
    return NativeTranslation(status, sql, ' AND '.join(local), '; '.join(dict.fromkeys(reasons)))


__all__ = ['DIALECTS', 'NativeTranslation', 'OGR_SQL', 'POSTGRESQL', 'SQLITE', 'translate_native',
           'INT', 'REAL', 'TEXT', 'BOOL', 'OTHER']
