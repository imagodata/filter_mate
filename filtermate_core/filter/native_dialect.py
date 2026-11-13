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
  double precision as QGIS runs it (``numeric`` is exact); ``ILIKE`` folds
  case by the locale of the database, so it is written ``SIMILAR TO`` with a
  class per letter (as for SQLite below), for ASCII patterns only;
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
  with the type of the first two). Where the caller knows that LIKE keeps
  the case (``case_sensitive_like``: GDAL 3.1+ without OGR_SQL_LIKE_AS_ILIKE,
  data read as UTF-8), outside any NOT: ``=`` to a text without wildcard is
  written LIKE, IN on such texts as LIKEs joined by OR (up to
  ``OGR_LIKE_LIST_MAX``), LIKE without ``_`` and ILIKE with ASCII letters
  other than k and s as they are, each run of ``%`` as one (a trailing
  ``%%`` drops features in OGR SQL).

Everywhere: the sign of a value that is not a literal is not written (QGIS
reads -NULL of an integer or real field as 0, the sources as NULL); SQLite
reads about one decimal literal in 4,000 one unit in the last place off, so
reals are written as an integer significand over a power of two. A text
constant that reads as a number (``'5'``, ``'0.3'``, ``'1e3'``, no space)
compared with a number is compared as a number, as QGIS compares it.

Variables (``@name``, ``var('name')``) are folded to the constant the caller
read in the global, project and layer scopes (``variables``): the subset is
written once and stays as written, as every FilterMate subset (a variable
changed afterwards does not filter again). A variable of the feature, the
map, the canvas, a layout or an atlas, or one the caller did not give, is
not written.

Geometric functions (``geometry``: the source's geometry column) are
written where the source returns QGIS's own double, compared bit for bit on
real layers (QGIS 4.2.3 / 3.44.15, PostGIS 3.4, GDAL 3.10 / 3.12):

- ``x_min`` / ``x_max`` / ``y_min`` / ``y_max`` of ``$geometry``: PostGIS
  ``ST_XMin``... on point and line layers (arcs included; the box of a
  curved polygon holds every ring in PostGIS, the shell only in QGIS);
  GeoPackage ``ST_MinX``... (GDAL's own functions, the blob header's
  envelope) on point layers only (GDAL's envelope of a polygon holds a ring
  outside the shell, of an arc differs in the last bits);
- ``x`` / ``y`` / ``$x`` / ``$y`` on a PostGIS point layer (a generic column
  read as points also holds multipoints: centroid / first point, and QGIS's
  0 for an empty multipoint).

QGIS gives NaN for an empty geometry and stops the evaluation with an error
at its first use (the feature is not kept, measured), the source gives NULL:
the same through comparisons, arithmetic, BETWEEN, NOT and a top-level AND,
so a geometric value is not written under OR, CASE / if, an AND under NOT,
IS NULL or coalesce (SQL goes on past the NULL). Left to QGIS: ``area`` (QGIS sums the ring
in another order: 2,000 polygons of 2,000 differ in the last bits),
``length`` / ``perimeter`` (arcs differ, and a PostGIS layer typed as lines
reads arcs from a generic column), ``num_points`` (compound curves, empty
points), ``$area`` / ``$length`` / ``$perimeter`` (ellipsoid and units of
the project), and everything on OGR SQL.

Known limits, not detected: an integer arithmetic that overflows 64 bits
(QGIS wraps, SQLite turns to a real), integer field values beyond 2^53
(compared exactly by the source), data values that do not match the declared
type of a SQLite column, and NaN produced from infinite field values.

Only a top-level AND is split. What cannot be written is returned as QGIS
text (``local_expression``), never dropped. For a PARTIAL or NONE result on
a SQLite source the caller may let QGIS evaluate the expression and list keys
(:func:`hybrid_sql`); otherwise it keeps its former path.
"""
import math
import re
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
# sanitizer misreads (it does not skip every quoted identifier: -- and /*
# read as comments, an apostrophe as the start of a literal).
_IDENTIFIER_REFUSED = ('"', "'", '\\', '--', '/*', '*/')
# Other cases of k and s in a Unicode case-insensitive regular expression.
_OTHER_CASES = {'k': 'K', 's': 'ſ'}

# A text QGIS reads as a number (QString::toDouble, C locale), written in the
# plainest form only: ASCII digits, no space, no leading or trailing point.
# The first QGIS whose geometric functions were compared with the sources (3.44 and 4.x were measured). Before
# 3.34 the rectangle of an empty geometry is 0,0,0,0: the bounds of an empty line, polygon or collection are 0
# in QGIS, where the source answers NULL, and ``x_min($geometry) < 100`` would keep in QGIS a feature the source
# leaves out.
GEOMETRY_MIN_QGIS = 33400
_INTEGER_TEXT = re.compile(r'[+-]?[0-9]+')
_NUMBER_TEXT = re.compile(r'[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?')

# Variables that depend on the feature, the map, the canvas, a layout, an
# atlas, a symbol, a form or the time of evaluation. None of them is in the
# global, project and layer scopes the adapter reads (where QGIS also marks
# its variables static or not): refused here too, whatever the caller gives.
_DYNAMIC_VARIABLES = frozenset((
    'row_number', 'geometry', 'feature', 'id', 'parent', 'element', 'value', 'layer', 'layers', 'layer_ids',
    'zoom_level', 'vector_tile_zoom', 'scale_value', 'snapping_results', 'form_mode', 'notification_message',
    'feature_count', 'counter', 'now', 'today'))
_DYNAMIC_PREFIXES = ('_', 'map_', 'canvas_', 'atlas_', 'layout_', 'symbol_', 'geometry_', 'cluster_', 'item_',
                     'grid_', 'frame_', 'current_', 'parent_', 'animation_', 'algorithm_', 'model_', 'processing_',
                     'mesh_', 'chart_', 'legend_', 'plot_', 'fullextent_', 'user_cursor', 'layer_cursor', 'now_',
                     'time_', 'utc_')
# Functions whose arguments the writer reads: variables are folded there only.
_FOLDED_THROUGH = ('if', 'coalesce', 'abs', 'floor', 'ceil')

# Geometry sources whose functions were compared with QGIS.
POSTGIS = 'postgis'
GEOPACKAGE = 'gpkg'
# QGIS function -> PostGIS, GeoPackage (GDAL's own SQL functions) function
_BOUNDS = {'x_min': ('ST_XMin', 'ST_MinX'), 'x_max': ('ST_XMax', 'ST_MaxX'),
           'y_min': ('ST_YMin', 'ST_MinY'), 'y_max': ('ST_YMax', 'ST_MaxY')}
_COORDINATES = ('x', 'y', '$x', '$y')
# NaN in QGIS for an empty geometry, NULL in the source
_GEOMETRY_VALUES = frozenset(_BOUNDS) | frozenset(_COORDINATES)
_NOT_WRITTEN_GEOMETRY = {
    'area': 'QGIS sums the area of a ring in another order than the source (the last bits differ)',
    'length': 'the length of an arc differs in the last bits, and a PostGIS layer of lines may read arcs',
    'perimeter': 'the length of an arc differs in the last bits, and a PostGIS layer of polygons may read arcs',
    'num_points': 'compound curves and empty points are counted differently',
    '$area': 'ellipsoidal and in the units of the project',
    '$length': 'ellipsoidal and in the units of the project',
    '$perimeter': 'ellipsoidal and in the units of the project',
}


@dataclass(frozen=True)
class NativeTranslation:
    """A predicate written for the data source.

    Attributes:
        status: FULL when ``sql`` alone is the whole predicate.
        sql: Native predicate of the translated AND operands ('' when none).
        local_expression: QGIS text of the operands left untranslated.
        reason: Why they were left (first reason of each, deduplicated).
        native_expression: QGIS text of the translated operands (same
            features as ``sql``), for an evaluation by QGIS.
        native_columns: Fields the translated operands read.
        predicate: Whether the expression is a condition (comparison,
            AND / OR / NOT, IN, BETWEEN, LIKE, IS): its value is TRUE,
            FALSE or NULL, never a number or a text read as a boolean.
        composite: Whether ``sql`` holds AND, OR or NOT (the user's, or the
            tolerance of a real's equality). OGR SQL gives FALSE to TRUE AND
            NULL: such a subset must not be negated there.
        geometric: Whether ``sql`` holds a coordinate of the geometry: NULL
            in the source where QGIS stops on the NaN of an empty geometry.
            Holding AND, OR or NOT too, it must not be negated (``NOT (NULL
            AND FALSE)`` is TRUE, QGIS keeps nothing). Under the OR of a
            combination with an old subset it is not refused: FilterMate
            combines kept sets (``old OR NULL`` keeps the old features, as the
            union of both filters does, where QGIS evaluating ``old OR new``
            stops on the NaN when ``old`` is FALSE or NULL: not kept either).
        native_exact: Whether ``native_expression`` gives back every number
            of ``sql``: QGIS's ``node.dump()`` writes 1e-30 as 0. When it does
            not, QGIS must not evaluate that text for the native part.
    """

    status: TranslationStatus
    sql: str = ''
    local_expression: str = ''
    reason: str = ''
    native_expression: str = ''
    native_columns: frozenset = frozenset()
    predicate: bool = False
    composite: bool = False
    geometric: bool = False
    native_exact: bool = True


@dataclass(frozen=True)
class NativeGeometry:
    """The geometry column of a source whose geometric functions are written.

    Attributes:
        column: Name of the geometry column.
        kind: QGIS geometry type of the layer: ``point``, ``line`` or ``polygon``.
        source: ``postgis``, or ``gpkg`` (a GeoPackage read by GDAL).
        curved: Whether the layer's geometry type is curved.
    """

    column: str
    kind: str
    source: str
    curved: bool = False


def _class(kind: str) -> str:
    return 'number' if kind in _NUMERIC else kind


def _safe_identifier(name) -> bool:
    return (isinstance(name, str) and bool(name) and not any(part in name for part in _IDENTIFIER_REFUSED)
            and not any(ord(char) < 32 for char in name))


def _is_geometry(node: Node) -> bool:
    """``$geometry``: the geometry of the feature."""
    return node.kind == 'function' and str(node.value).lower() == '$geometry' and not node.children


def _holds_geometry_value(node: Node) -> bool:
    """Whether a value may be NaN in QGIS where the source gives NULL (an empty geometry)."""
    if node.kind == 'function' and str(node.value).lower() in _GEOMETRY_VALUES:
        return True
    return any(_holds_geometry_value(child) for child in node.children)


def _number_from_text(node: Node, other_type: str) -> Node:
    """A text constant compared with a number, as QGIS compares them: as a number.

    QGIS compares two values as numbers when they are not both texts and both
    read as numbers (``"pop" > '5'``, a project variable holding 5 is the text
    '5'). Only the plainest writings are converted; any other text is left
    as it is (and the comparison of a text with a number is not written).
    """
    if other_type not in _NUMERIC or node.kind != 'literal' or not isinstance(node.value, str):
        return node
    if _INTEGER_TEXT.fullmatch(node.value):
        try:
            return Node('literal', int(node.value), (), node.text)
        except ValueError:
            # Python 3.11 and later read no integer of more than 4,300 digits: left as the text it is, which is
            # not written against a number (the error left the translation, with every other part of the predicate)
            return node
    if _NUMBER_TEXT.fullmatch(node.value):
        value = float(node.value)
        if value == 0 and any(digit in '123456789' for digit in re.split('[eE]', node.value)[0]):
            # an underflow: QString::toDouble fails and QGIS compares the texts ('1' > '1e-400' is
            # FALSE, measured); a subnormal ('3e-324') is read as a number
            return node
        return Node('literal', value, (), node.text)
    return node


def _is_constant_variable(name: str, variables) -> bool:
    if name not in variables or name in _DYNAMIC_VARIABLES or name.startswith(_DYNAMIC_PREFIXES):
        return False
    value = variables[name]
    return is_null_value(value) or isinstance(value, (bool, int, float, str))


def _fold_variables(node: Node, variables) -> Node:
    """Replace each variable known as a constant by a literal of its value (QGIS text kept).

    Not inside a function the writer does not read (``with_variable``,
    ``aggregate``... give a variable another value there).
    """
    if node.kind == 'function':
        name = str(node.value).lower()
        if name == 'var':
            argument = node.children[0] if len(node.children) == 1 else None
            if (argument is not None and argument.kind == 'literal' and isinstance(argument.value, str)
                    and _is_constant_variable(argument.value, variables)):
                return Node('literal', variables[argument.value], (), node.text)
            return node
        if name not in _FOLDED_THROUGH:
            return node
    if not node.children:
        return node
    children = tuple(_fold_variables(child, variables) for child in node.children)
    if all(new is old for new, old in zip(children, node.children)):
        return node
    return Node(node.kind, node.value, children, node.text)


class _Writer:
    """Writes one AND operand; raises :class:`Unsupported` on anything unproven."""

    def __init__(self, dialect: str, types: Dict[str, Optional[str]], case_sensitive_like: bool = False,
                 geometry: Optional[NativeGeometry] = None):
        self.dialect = dialect
        self.types = types
        self.geometry = geometry
        self.ands = 0  # AND written so far, user's or ours (OGR SQL: no NOT over one)
        self.connectives = 0  # AND, OR, NOT written so far
        self.columns = set()
        # OGR SQL: texts compared with LIKE, outside any NOT only
        self.case_sensitive_like = case_sensitive_like and dialect == OGR_SQL
        self.negations = 0  # NOT around the node being written
        # OR, CASE / if, or AND under a NOT around the node: SQL goes on past a NULL there where QGIS stops
        # on an evaluation error (a geometric value of an empty geometry)
        self.alternatives = 0
        self.geometric = False  # a coordinate of the geometry written

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
            if node.children[0].kind != 'literal':
                # QGIS: -NULL of an integer / real field is 0 (its value read as a
                # number), the sources give NULL
                raise Unsupported('The sign of a value that may be NULL')
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
        self.columns.add(name)
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
            if self.dialect == SQLITE:
                return _sqlite_real(value), REAL
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
        self.alternatives += 1
        for index in range(0, len(children), 2):
            then, then_type = self.value(children[index + 1], depth + 1)
            parts.append('WHEN {} THEN {}'.format(self.predicate(children[index], depth + 1), then))
            types.append(then_type)
        if otherwise is not None:
            other, other_type = self.value(otherwise, depth + 1)
            parts.append('ELSE {}'.format(other))
            types.append(other_type)
        self.alternatives -= 1
        return '(CASE {} END)'.format(' '.join(parts)), self._merged_type(types)

    def _function(self, node: Node, depth: int) -> Tuple[str, str]:
        name = str(node.value).lower()
        if name == 'var':  # the variables known as constants are literals already
            raise Unsupported('A variable that is not a constant of QGIS, the project or the layer: {}'.format(
                node.text))
        if self.dialect == OGR_SQL:
            raise Unsupported('Functions are not written in OGR SQL: {}'.format(name))
        count = len(node.children)
        if name in _GEOMETRY_VALUES:
            return self._geometry_value(name, node)
        if name in _NOT_WRITTEN_GEOMETRY:
            raise Unsupported('Geometric function not translated, {}: {}'.format(_NOT_WRITTEN_GEOMETRY[name], name))
        if name == 'if' and count == 3:
            # if(c, a, b): b when c is false or NULL, as CASE ... ELSE
            return self._case(Node('condition', True, node.children, node.text), depth)
        arguments = [self.value(child, depth + 1) for child in node.children]
        types = [type_ for _, type_ in arguments]
        text = ', '.join(sql for sql, _ in arguments)
        if name == 'coalesce' and count >= 2:  # SQLite refuses COALESCE(x)
            if any(_holds_geometry_value(child) for child in node.children):
                raise Unsupported('coalesce of a geometric value: NaN in QGIS for an empty geometry, '
                                  'NULL in the source')
            return 'COALESCE({})'.format(text), self._merged_type(types)
        if name == 'abs' and count == 1 and types[0] in _NUMERIC:
            # a double in QGIS (no overflow on the smallest integer)
            real = 'double precision' if self.dialect == POSTGRESQL else 'REAL'
            return '{}(CAST({} AS {}))'.format(name, text, real), REAL
        if name in ('floor', 'ceil') and count == 1 and types[0] in _NUMERIC and self.dialect == POSTGRESQL:
            return '{}(CAST({} AS double precision))'.format(name, text), REAL
        # length(): QGIS counts UTF-16 code units, the sources count characters.
        # lower() / upper(): Unicode in QGIS, ASCII letters only in SQLite, the locale of the database in
        # PostgreSQL (a C database leaves 'É' as it is, a UTF-8 one folds 'İ' to 'i').
        raise Unsupported('Function not translated: {}'.format(name))

    def _geometry_value(self, name: str, node: Node) -> Tuple[str, str]:
        """A coordinate of ``$geometry``, a double equal to QGIS's (compared bit for bit on real layers).

        Empty geometry: QGIS gives NaN and stops the evaluation with an error
        at its first use (the feature is not kept), the source gives NULL.
        Measured the same (not kept) through comparisons, arithmetic, abs,
        BETWEEN, NOT and a top-level AND; not through OR (``NULL OR TRUE``),
        CASE / if (``WHEN NULL`` takes ELSE), an AND under NOT (``NULL AND
        FALSE`` is FALSE in SQL where QGIS stops), IS NULL and coalesce.
        """
        if self.alternatives:
            raise Unsupported('A geometric value under OR, CASE or a negated AND: QGIS stops on an empty '
                              'geometry, the source goes on with NULL')
        self.geometric = True
        geometry = self.geometry
        if name.startswith('$'):
            if node.children:
                raise Unsupported('Not a geometric function of the feature: {}'.format(node.text))
        elif len(node.children) != 1 or not _is_geometry(node.children[0]):
            raise Unsupported('A geometric function written for $geometry only: {}'.format(node.text))
        if geometry is None:
            raise Unsupported('No geometry column written for this source: {}'.format(name))
        if not _safe_identifier(geometry.column):
            raise Unsupported('A geometry column name that cannot be written safely: {}'.format(geometry.column))
        column = '"' + geometry.column + '"'
        if geometry.source == POSTGIS:
            shape = 'CAST({} AS geometry)'.format(column)  # a geography column as QGIS reads it (planar)
        elif geometry.source == GEOPACKAGE:
            shape = column
        else:
            raise Unsupported('Geometric functions are not written for this source: {}'.format(geometry.source))
        if name in _BOUNDS:
            if geometry.source == POSTGIS:
                # The box of a CURVEPOLYGON / MULTISURFACE holds every ring in PostGIS, QGIS's bounding box
                # the shell's only (a hole outside: 30 against 10), and a generic column read as polygons
                # holds them whatever the layer's type: points and lines only (arcs measured exact).
                if geometry.kind == 'polygon':
                    raise Unsupported('{} of a PostGIS layer of polygons (curved ones bound every ring)'.format(name))
                return '{}({})'.format(_BOUNDS[name][0], shape), REAL
            # ST_MinX... read the envelope of the GeoPackage blob header: GDAL's envelope of a polygon holds a
            # ring outside the shell, of an arc differs in the last bits (430 arcs of 500), and a layer of
            # lines may store either. Points only: no arithmetic there. A header written wrong by another
            # tool than GDAL is not detected.
            if geometry.kind != 'point' or geometry.curved:
                raise Unsupported('{} of a GeoPackage layer written for points only'.format(name))
            return '{}({})'.format(_BOUNDS[name][1], shape), REAL
        # x / y: centroid, $x / $y: first point ($x of an empty multipoint: 0 in QGIS 3.44.15, a crash of
        # QGIS 4.2.3; written 0). A PostGIS layer of points read from a generic column
        # also holds multipoints; QGIS gives 0 for an empty multipoint, NaN when a part is empty.
        if geometry.source != POSTGIS or geometry.kind != 'point':
            raise Unsupported('{} written for a PostGIS layer of points only'.format(name))
        axis = 'ST_X' if name.endswith('x') else 'ST_Y'
        empty = "WHEN ST_IsEmpty({0}) AND ST_GeometryType({0}) <> 'ST_Point' THEN CAST(0 AS double precision)"
        if name.startswith('$'):
            rest = 'ELSE {1}(ST_GeometryN({0}, 1))'
        else:
            rest = 'WHEN ST_NumGeometries({0}) = ST_NPoints({0}) THEN {1}(ST_Centroid({0}))'
        return ('(CASE ' + empty + ' ' + rest + ' END)').format(shape, axis), REAL

    # -- predicates -------------------------------------------------------------

    def predicate(self, node: Node, depth: int = 0) -> str:
        """SQL of a node read as a condition."""
        if depth > _MAX_DEPTH:
            raise Unsupported('Expression complexity limit exceeded')
        kind = node.kind
        if kind == 'binary':
            operator = node.value
            if operator in ('AND', 'OR'):
                self.connectives += 1
                if operator == 'AND':
                    self.ands += 1
                alternative = operator == 'OR' or self.negations > 0
                self.alternatives += alternative
                written = '({} {} {})'.format(self.predicate(node.children[0], depth + 1), operator,
                                              self.predicate(node.children[1], depth + 1))
                self.alternatives -= alternative
                return written
            if operator in ('IS', 'IS NOT'):
                return self._is_null(node, depth)
            if operator in _COMPARISONS:
                return self._comparison(node, depth)
            if operator in _LIKES:
                return self._like(node, depth)
        if kind == 'unary' and node.value == 'NOT':
            before = self.ands
            self.connectives += 1
            self.negations += 1
            operand = self.predicate(node.children[0], depth + 1)
            self.negations -= 1
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
        if _holds_geometry_value(left):
            raise Unsupported('IS NULL of a geometric value: NaN in QGIS for an empty geometry, NULL in the source')
        sql, _ = self.value(left, depth + 1)
        return '({} {} NULL)'.format(sql, node.value)

    def _comparable(self, left_type: str, right_type: str, ordering: bool, as_like: bool = False) -> None:
        """Raise unless the two values compare in the source as in QGIS.

        ``as_like``: OGR SQL may compare the texts with LIKE (=, IN, not their
        negations); the caller still checks the literal.
        """
        if NULL in (left_type, right_type):
            raise Unsupported('Use IS NULL or IS NOT NULL for null values')
        kind = _class(left_type)
        if kind != _class(right_type) or kind == OTHER:
            raise Unsupported('Compared values are not of the same type (QGIS converts them, the source may not)')
        if kind == TEXT:
            if ordering:
                raise Unsupported('Text ordering depends on the collation of the data source')
            if self.dialect == OGR_SQL and not (as_like and self._texts_as_like()):
                raise Unsupported('OGR SQL compares texts without their case')
        if kind == BOOL and ordering:
            raise Unsupported('Ordering of booleans')

    def _texts_as_like(self) -> bool:
        """OGR SQL: whether texts may be compared with a case-sensitive LIKE here (outside any NOT)."""
        return self.case_sensitive_like and not self.negations

    def _ogr_text_match(self, left: str, literal: Node) -> str:
        """OGR SQL: ``left LIKE 'text'``, QGIS's text equality (= and IN ignore case in OGR SQL)."""
        value = literal.value if literal.kind == 'literal' else None
        if not isinstance(value, str) or '%' in value or '_' in value:
            raise Unsupported('OGR SQL compares texts without their case (LIKE only for a text without % or _)')
        return '{} LIKE {}'.format(left, self._literal(value)[0])

    def _binary_text(self, sql: str, type_: str) -> str:
        """SQLite: the left operand of a text equality, whatever the column's collation."""
        return sql + ' COLLATE BINARY' if self.dialect == SQLITE and type_ == TEXT else sql

    def _comparison(self, node: Node, depth: int) -> str:
        (left, left_type), (right, right_type) = (self.value(child, depth + 1) for child in node.children)
        numbers = (_number_from_text(node.children[0], right_type), _number_from_text(node.children[1], left_type))
        if any(new is not old for new, old in zip(numbers, node.children)):
            node = Node('binary', node.value, numbers, node.text)
            (left, left_type), (right, right_type) = (self.value(child, depth + 1) for child in node.children)
        operator = node.value
        self._comparable(left_type, right_type, operator not in ('=', '<>'), as_like=operator == '=')
        if self.dialect == OGR_SQL and left_type == TEXT:
            if node.children[1].kind == 'literal':
                return '({})'.format(self._ogr_text_match(left, node.children[1]))
            return '({})'.format(self._ogr_text_match(right, node.children[0]))
        if operator in ('=', '<>') and REAL in (left_type, right_type):
            # qgsDoubleNear on the difference, as QGIS compares
            difference, _ = self._arithmetic(Node('binary', '-', node.children, node.text), depth)
            epsilon = self._literal(_EPSILON)[0]
            self.connectives += 1
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
            self._comparable(left_type, type_, False, as_like=not node.value)
            if REAL in (left_type, type_):
                raise Unsupported('IN on real numbers: QGIS compares them with a tolerance')
            items.append(sql)
        if self.dialect == OGR_SQL and left_type == TEXT:
            if len(items) > OGR_LIKE_LIST_MAX:
                raise Unsupported('IN on more than {} texts: OGR SQL compares them without their case'.format(
                    OGR_LIKE_LIST_MAX))
            if len(items) > 1:
                self.connectives += 1
            return '({})'.format(' OR '.join(self._ogr_text_match(left, child) for child in node.children[1:]))
        return '({} {}IN ({}))'.format(self._binary_text(left, left_type), 'NOT ' if node.value else '',
                                      ', '.join(items))

    def _between(self, node: Node, depth: int) -> str:
        value_node, low_node, high_node = node.children
        sql, type_ = self.value(value_node, depth + 1)
        if type_ not in _NUMERIC:
            raise Unsupported('BETWEEN is written for numbers only')
        bounds = []
        for bound in (low_node, high_node):
            if _holds_geometry_value(bound):
                # a hidden AND: 20 NOT BETWEEN NULL AND 10 is TRUE, QGIS stops on the NaN of an empty geometry
                raise Unsupported('A geometric value as a BETWEEN bound: QGIS stops on an empty geometry, the '
                                  'source goes on with NULL')
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
            if not insensitive:
                right, _ = self._literal(pattern)  # refuses a backslash: no escape to translate
                return '({} {} {})'.format(left, node.value, right)
            # ILIKE folds case by the locale of the database ('ſ' is not 's', 'İ' is 'i' in UTF-8):
            # QGIS's own case-insensitive match is written as SIMILAR TO with a class per letter.
            if not pattern.isascii() or '\\' in pattern:
                raise Unsupported('An ILIKE pattern that is not ASCII or holds an escape')
            if any(char in pattern for char in '|*+?{}()[]'):
                raise Unsupported('An ILIKE pattern holding SIMILAR TO metacharacters')
            similar = ''.join(
                '[' + char.lower() + char.upper() + _OTHER_CASES.get(char.lower(), '') + ']'
                if char.isalpha() else char for char in pattern)
            right, _ = self._literal(similar)
            return '({} {}SIMILAR TO {})'.format(left, 'NOT ' if negated else '', right)
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
            return '({} {}GLOB {})'.format(left, 'NOT ' if negated else '', self._literal(''.join(glob))[0])
        if negated or not self._texts_as_like():
            raise Unsupported('LIKE is not the same in OGR SQL')
        # _ matches one byte, not one character, where the data is not read as UTF-8 (MapInfo,
        # measured); ILIKE folds ASCII letters but neither to the Kelvin sign nor to the long s.
        if '\\' in pattern or '_' in pattern:
            raise Unsupported('An OGR SQL LIKE pattern holding _ or an escape')
        if insensitive and (not pattern.isascii() or any(char in pattern for char in 'kKsS')):
            raise Unsupported('An OGR SQL ILIKE pattern that is not ASCII or holds k or s')
        # QGIS reads each % as .*; OGR SQL drops a text that ends where a trailing %% starts
        # ('Route' LIKE 'Route%%', '' LIKE '%%'): one % per run, the same pattern in QGIS.
        return '({} {} {})'.format(left, node.value, self._literal(re.sub('%+', '%', pattern))[0])


def _sqlite_real(value: float) -> str:
    """A real as SQLite reads it exactly: an integer significand over a power of two.

    SQLite reads about one decimal literal in 4,000 one unit in the last place
    off (3.45: ``-737867.403628`` -> ``-737867.4036280001``); an integer below
    2^53 and a power of two are read exactly, and so is their quotient.
    """
    if value.is_integer() and abs(value) < 2 ** 63:
        return 'CAST({} AS REAL)'.format(int(value))  # an integer a double holds: read exactly
    fraction, exponent = math.frexp(value)
    significand, exponent = int(fraction * (1 << 53)), exponent - 53
    while significand % 2 == 0:
        significand //= 2
        exponent += 1
    if exponent >= 0:
        raise Unsupported('A real beyond the range written exactly for SQLite')
    if -exponent <= 62:
        return '(CAST({} AS REAL) / {})'.format(significand, 1 << -exponent)
    if -exponent <= 124:
        return '(CAST({} AS REAL) / {} / {})'.format(significand, 1 << 62, 1 << (-exponent - 62))
    raise Unsupported('A real beyond the range written exactly for SQLite')


def _is_predicate(node: Node) -> bool:
    """Whether a condition is the root: its value is TRUE, FALSE or NULL."""
    if node.kind in ('in', 'between'):
        return True
    if node.kind == 'unary':
        return node.value == 'NOT'
    return node.kind == 'binary' and node.value in ('AND', 'OR', 'IS', 'IS NOT') + _COMPARISONS + _LIKES


def _strip_outer_parentheses(sql: str) -> str:
    """``(a = 1)`` -> ``a = 1`` when the first parenthesis closes at the end.

    Kept when the inside starts with a function or a keyword: the subset
    sanitizer reads ``COALESCE(...) GLOB ...`` as a display expression.
    """
    if not (sql.startswith('(') and sql.endswith(')')) or sql[1:2].isalpha():
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


def _dump_round_trips(node: Node) -> bool:
    """Whether the QGIS text of each number of a tree reads back as the number.

    ``node.dump()`` writes a real with 17 decimals at most (1e-30 is '0',
    -1e-30 '- 0', measured in 4.2.3 and 3.44.15).
    """
    stack = [node]
    while stack:
        current = stack.pop()
        value = current.value
        if current.kind == 'literal' and isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                if float(current.text.replace(' ', '')) != value:
                    return False
            except (ValueError, OverflowError):
                return False
        stack.extend(current.children)
    return True


def referenced_variables(node: Node) -> frozenset:
    """Names of the variables a tree reads by a literal name (``@name``, ``var('name')``)."""
    names, stack = set(), [node]
    while stack:
        current = stack.pop()
        if (current.kind == 'function' and str(current.value).lower() == 'var' and len(current.children) == 1
                and current.children[0].kind == 'literal' and isinstance(current.children[0].value, str)):
            names.add(current.children[0].value)
        stack.extend(current.children)
    return frozenset(names)


def uses_geometry(node: Node) -> bool:
    """Whether a tree holds a geometric function this module may write (it then needs ``geometry``)."""
    stack = [node]
    while stack:
        current = stack.pop()
        if current.kind == 'function' and str(current.value).lower() in _GEOMETRY_VALUES:
            return True
        stack.extend(current.children)
    return False


def translate_native(node: Node, dialect: str, types: Dict[str, Optional[str]],
                     case_sensitive_like: bool = False, variables: Optional[Dict[str, object]] = None,
                     geometry: Optional[NativeGeometry] = None) -> NativeTranslation:
    """Write a QGIS predicate for a data source, splitting a top-level AND only.

    Args:
        node: Tree from the QGIS adapter, each node keeping its QGIS text.
        dialect: ``postgresql``, ``sqlite`` or ``ogr_sql``.
        types: Type of each field of the data source, by exact name: ``int``,
            ``real``, ``text``, ``bool`` or ``other`` (None reads as other).
        case_sensitive_like: OGR SQL only: the source's LIKE keeps the case
            and ``_`` matches one character (GDAL 3.1+ without
            OGR_SQL_LIKE_AS_ILIKE, data read as UTF-8). Texts compared with
            =, IN, LIKE or ILIKE outside any NOT are then written with LIKE.
            The subset must not be negated by the caller (AND NOT).
        variables: Values of the variables that are constants where the
            filter is applied (global, project and layer scopes, static in
            QGIS), by exact name. Folded into the subset, which does not
            follow a later change of the variable.
        geometry: The source's geometry column, for the geometric functions
            written natively; None writes none.

    Returns:
        NativeTranslation; nothing is dropped, the untranslated operands are
        returned as QGIS text.
    """
    if dialect not in DIALECTS:
        return NativeTranslation(TranslationStatus.NONE, local_expression=node.text,
                                 reason='Unknown dialect: {}'.format(dialect))
    written, native, local, reasons, columns = [], [], [], [], set()
    connectives, geometric, exact = [0], [False], [True]

    def visit(part: Node) -> None:
        if part.kind == 'binary' and part.value == 'AND':
            for child in part.children:
                visit(child)
            return
        try:
            writer = _Writer(dialect, types, case_sensitive_like, geometry)
            original, part = part, _fold_variables(part, variables or {})
            written.append(writer.predicate(part))
            native.append('(' + part.text + ')')
            columns.update(writer.columns)
            connectives[0] += writer.connectives
            geometric[0] = geometric[0] or writer.geometric
            exact[0] = exact[0] and _dump_round_trips(original)
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
    return NativeTranslation(status, sql, ' AND '.join(local), '; '.join(dict.fromkeys(reasons)),
                             ' AND '.join(native), frozenset(columns), _is_predicate(node),
                             connectives[0] > 0 or len(written) > 1, geometric[0],
                             exact[0])


# Hybrid subsets are written for SQLite only. OGR SQL (GDAL 3.13) refuses an
# IN list beyond ~5,000 values, tests it value by value on every row at every
# read (no index, even on FID), compares text keys without case and names a
# field "fid" rather than the feature id when the layer has one.
HYBRID_MAX_KEYS = 100_000

# OGR SQL: IN on texts is written as LIKEs joined by OR up to this many values,
# left to the former conversion beyond. Measured with GDAL 3.10 on a
# 200,000-row Shapefile: one LIKE costs what = costs, each other LIKE adds
# about 0.035 s to every read (10 values: 0.39 s, IN: 0.095 s).
OGR_LIKE_LIST_MAX = 10


def key_reference(name: str) -> str:
    """The key column of a hybrid subset (SQLite, PostgreSQL)."""
    if not name or any(part in name for part in _IDENTIFIER_REFUSED) or any(ord(char) < 32 for char in name):
        raise Unsupported('A key name that cannot be written safely: {}'.format(name))
    return '"' + name + '"'


def hybrid_sql(native_sql: str, passing, failing, key: str, numeric: bool, dialect: str = SQLITE) -> str:
    """Subset of a PARTIAL / NONE translation from the keys QGIS evaluated (SQLite, PostgreSQL).

    The subset keeps the same features as the expression (a TRUE / not TRUE
    filter: it must not be negated, where FALSE and NULL differ). A list
    starts with ``key IS NOT NULL AND``: the filter orchestrator reads a subset
    that starts with ``key IN (`` as the key list of a previous spatial step,
    which a new spatial filter replaces instead of combining with it.

    Args:
        native_sql: ``sql`` of the translation ('' for NONE).
        passing: Keys of the features the whole expression keeps.
        failing: Keys of the features the native part keeps and the whole
            expression does not; None when there is no native part.
        key: :func:`key_reference` of the key column, unique and never NULL.
        numeric: Whether the key values are numbers. A SQLite text key is
            compared ``COLLATE BINARY``, whatever the column's collation; a
            PostgreSQL one as it is (a deterministic collation compares bytes,
            and a COLLATE would refuse a uuid key and leave its index unused).
        dialect: ``sqlite`` or ``postgresql``.

    Returns:
        The native part alone when nothing else excludes a feature, else the
        shorter of ``(native) AND NOT (key IN (failing))`` and
        ``key IN (passing)``; a contradiction when nothing is kept.
    """
    from .pk_formatter import SQL, format_key_literal

    def listed(values) -> str:
        if len(values) > HYBRID_MAX_KEYS:
            raise Unsupported('{} keys, more than the {} listed in a subset'.format(len(values), HYBRID_MAX_KEYS))
        literals = []
        for value in values:
            if is_null_value(value):
                raise Unsupported('A NULL key cannot be listed')
            literals.append(format_key_literal(value, numeric, SQL))
        return ', '.join(literals)

    if dialect not in (SQLITE, POSTGRESQL):
        raise Unsupported('Hybrid subsets are written for SQLite and PostgreSQL only')
    column = key if numeric or dialect == POSTGRESQL else key + ' COLLATE BINARY'
    if native_sql and failing is not None:
        if not failing:
            return native_sql
        if len(failing) < len(passing):
            return '{} IS NOT NULL AND ({}) AND NOT ({} IN ({}))'.format(key, native_sql, column, listed(failing))
    if not passing:
        return '{0} <> {0}'.format(key)  # FALSE or NULL on every row
    return '{} IS NOT NULL AND {} IN ({})'.format(key, column, listed(passing))


__all__ = ['DIALECTS', 'NativeTranslation', 'OGR_SQL', 'POSTGRESQL', 'SQLITE', 'translate_native',
           'HYBRID_MAX_KEYS', 'hybrid_sql', 'key_reference', 'INT', 'REAL', 'TEXT', 'BOOL', 'OTHER',
           'OGR_LIKE_LIST_MAX', 'NativeGeometry', 'POSTGIS', 'GEOPACKAGE', 'referenced_variables',
           'uses_geometry']
