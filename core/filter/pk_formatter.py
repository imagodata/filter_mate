"""
Primary Key Formatter Module

EPIC-1 Phase E3: Extracted from modules/tasks/filter_task.py

Provides formatting utilities for primary key values in SQL expressions.
Handles both numeric and text-based primary keys (UUID, varchar, etc.).

Critical fixes:
- v2.8.5: UUID fields must be quoted with single quotes in SQL
- Supports fid, ctid, and custom primary keys
- 2026-10-17: the ONE formatter of key literals. Every key list (OGR,
  SpatiaLite, PostgreSQL materialized views, feature collectors) goes
  through :func:`format_key_literal`: a value is written unquoted only
  when it is a number, anything else is an SQL string literal with its
  quotes doubled (``repr(fid)`` wrote ``"L'Isle-Jourdain"``, an
  identifier, and ``f"'{v}'"`` let a quote end the literal). The field
  type decides before the values: a text key made of digits (``'01001'``)
  stays quoted.

Author: FilterMate Team
Created: January 2026 (EPIC-1 Phase E3)
"""

import logging
import math
import re
from typing import Any, Iterable, List, Optional

try:
    from qgis.core import QgsVectorLayer
except ImportError:
    QgsVectorLayer = None

logger = logging.getLogger('FilterMate.Core.Filter.PKFormatter')

# Names a key field is assumed numeric by when neither its type nor its values are known.
COMMON_NUMERIC_PK_NAMES = ('id', 'fid', 'gid', 'pk', 'ogc_fid', 'objectid', 'oid', 'rowid')

# An integer as SQL writes it: no leading zero ('01001' is a text code), optional minus sign.
_CANONICAL_INT_RE = re.compile(r'-?(?:0|[1-9][0-9]*)\Z')
# A number as SQL writes it (a numeric key read as text, '1.0'); a leading zero stays text.
_SQL_NUMBER_RE = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')


# Dialects of a key literal: SQL (OGR SQL, SQLite / GeoPackage, PostgreSQL...) doubles the
# quotes only; a QGIS expression (memory / delimited text / WFS / OGC API Features subsets,
# exploring expressions) also reads a backslash as an escape: 'b\c' there is "b" + "c".
SQL = 'sql'
QGIS_EXPRESSION = 'qgis'


def sql_string_literal(value: Any) -> str:
    """``value`` as an SQL string literal: ``L'Isle`` -> ``'L''Isle'``."""
    return "'" + str(value).replace("'", "''") + "'"


def qgis_string_literal(value: Any) -> str:
    r"""``value`` as a QGIS expression string literal (``QgsExpression.quotedString``).

    Quotes doubled, backslash, newline and tab escaped: ``b\c`` -> ``'b\\c'``.
    """
    text = str(value).replace("'", "''").replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')
    return "'" + text + "'"


def is_null_value(value: Any) -> bool:
    """None, or a null Qt value: QGIS 3 / PyQt5 gives a NULL attribute as a null ``QVariant``.

    Duck-typed (``isNull()``) so this module stays free of Qt; a null
    ``QDate`` is NULL too.
    """
    if value is None:
        return True
    if isinstance(value, (str, bytes, int, float)):
        return False
    is_null = getattr(value, 'isNull', None)
    if callable(is_null):
        try:
            return bool(is_null())
        except Exception:  # nosec B110 - not a Qt value
            return False
    return False


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_canonical_int_text(value: Any) -> bool:
    return isinstance(value, str) and bool(_CANONICAL_INT_RE.match(value))


def key_values_look_numeric(values: Iterable[Any]) -> bool:
    """Whether EVERY value (None aside) is a number or an integer written as text.

    ``'01001'`` is not: written unquoted it would become 1001. Booleans
    count as numbers (written ``True`` / ``False``, as before).
    """
    seen = False
    for value in values:
        if is_null_value(value):
            continue
        if not (isinstance(value, (int, float)) or _is_canonical_int_text(value)):
            return False
        seen = True
    return seen


def key_field(layer: Any, pk_field: Optional[str]) -> Any:
    """The ``QgsField`` named ``pk_field`` in ``layer``, None when unknown."""
    if layer is None or not pk_field:
        return None
    try:
        fields = layer.fields()
        index = fields.indexOf(pk_field)
        if isinstance(index, int) and index >= 0:
            return fields[index]
    except Exception as e:  # nosec B110 - schema unavailable (deleted layer, mock): decided by the values
        logger.debug(f"Could not read the field of '{pk_field}': {e}")
    return None


def format_key_literal(value: Any, numeric: bool, dialect: str = SQL) -> str:
    """One key value as an SQL literal (``dialect`` QGIS_EXPRESSION: a QGIS expression literal).

    Numeric keys are written unquoted only when the value is a number (an
    integral float as an integer) or a number written as text (``'12'``,
    ``'1.5'``); any other value - text, a code with a
    leading zero, a value that would inject SQL - is a quoted literal, which
    SQL compares with a numeric column as well. None (or a null QVariant) is
    ``NULL`` (matches nothing in an IN list).
    """
    if is_null_value(value):
        return 'NULL'
    if numeric:
        if isinstance(value, (bool, int)):
            return str(value)
        if isinstance(value, float) and math.isfinite(value):
            return str(int(value)) if value.is_integer() else repr(value)
        if isinstance(value, str) and _SQL_NUMBER_RE.match(value):
            return value
    return qgis_string_literal(value) if dialect == QGIS_EXPRESSION else sql_string_literal(value)


def is_pk_numeric(
    layer: 'QgsVectorLayer',
    pk_field: str,
    sample_values: Optional[List] = None
) -> bool:
    """
    Check if the primary key field is numeric.

    CRITICAL FIX v2.8.5: UUID fields and other text-based PKs must be quoted in SQL.
    2026-10-17: the field TYPE decides first; the values only decide without a
    schema, all of them (the first ten used to, before the schema: ``'01001'``
    was read as a number). A text field whose values are real numbers (a
    PostgreSQL integer read through OGR as text, v4.0.9) is still numeric.

    Args:
        layer: QgsVectorLayer to check
        pk_field: Primary key field name
        sample_values: Optional PK values for value-based detection

    Returns:
        bool: True if PK is numeric (int, bigint, etc.), False if text (UUID, varchar, etc.)
    """
    field = key_field(layer, pk_field)
    if field is not None:
        try:
            if field.isNumeric():
                logger.debug(f"PK '{pk_field}' detected as numeric from schema")
                return True
            values = [v for v in (sample_values or []) if not is_null_value(v)]
            numeric = bool(values) and all(_is_number(v) for v in values)
            logger.debug(f"PK '{pk_field}' detected as {'numeric' if numeric else 'text'} (text field)")
            return numeric
        except Exception as e:  # nosec B110 - falls back to the values below
            logger.debug(f"Could not determine PK type from schema: {e}")

    if sample_values:
        return key_values_look_numeric(sample_values)

    # Nothing known: numeric, the most common case (common names: id, fid, gid...)
    return True


def format_pk_values_for_sql(
    values: List,
    is_numeric: Optional[bool] = None,
    layer: Optional['QgsVectorLayer'] = None,
    pk_field: Optional[str] = None,
    dialect: str = SQL
) -> str:
    """
    Format primary key values for SQL IN clause.

    CRITICAL FIX v2.8.5: UUID fields must be quoted with single quotes in SQL.
    2026-10-17: every value goes through :func:`format_key_literal`.

    Examples:
        - Numeric: IN (1, 2, 3)
        - UUID/Text: IN ('7b2e1a3e-b812-4d51-bf33-7f0cd0271ef3', ...)

    Args:
        values: List of primary key values
        is_numeric: Whether PK is numeric (optional, auto-detected if None)
        layer: QgsVectorLayer to check PK type (optional, for auto-detection)
        pk_field: Primary key field name (optional, for auto-detection)
        dialect: SQL (default) or QGIS_EXPRESSION (backslashes escaped)

    Returns:
        str: Comma-separated values formatted for SQL IN clause
    """
    if not values:
        return ''

    if is_numeric is None:
        if layer and pk_field:
            is_numeric = is_pk_numeric(layer, pk_field, sample_values=values)
        else:
            is_numeric = key_values_look_numeric(values)
            logger.debug(f"PK type detected from values: {'numeric' if is_numeric else 'text'}")

    return ', '.join(format_key_literal(v, is_numeric, dialect) for v in values)
