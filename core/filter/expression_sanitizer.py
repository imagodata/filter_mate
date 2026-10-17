"""
Expression Sanitizer Module

EPIC-1 Phase E3: Extracted from modules/tasks/filter_task.py

Provides expression sanitization and optimization:
- Remove non-boolean display expressions (coalesce, CASE)
- Normalize French SQL operators (ET, OU, NON → AND, OR, NOT)
- Fix unbalanced parentheses
- Optimize duplicate IN clauses
- Clean up orphaned operators and whitespace

Used to clean expressions before applying as SQL WHERE clauses.

Author: FilterMate Team
Created: January 2026 (EPIC-1 Phase E3)
"""

import logging
import re
from typing import Optional

from .sql_quotes import IDENTIFIER_PLACEHOLDER, LITERAL_PLACEHOLDER, mask_quoted, unmask_quoted
from .sql_quotes import strip_outer_parens as _strip_outer_parens

logger = logging.getLogger('FilterMate.Core.Filter.Sanitizer')


# Display functions whose outer call produces a non-boolean value. When a
# subset string *is* one of these calls (no trailing boolean operator), the
# SQL backend rejects it at WHERE-clause evaluation. Kept here — not in
# validation_utils — because the sanitizer is the only boundary that must
# keep stripping them even when upstream validation lets them through (e.g.
# the <NULL> placeholder false-positive in is_filter_expression).
_DISPLAY_FUNCTION_PREFIXES = (
    'COALESCE(',
    'CONCAT(',
    'FORMAT(',
    'FORMAT_DATE(',
    'FORMAT_NUMBER(',
    'TO_STRING(',
    'UPPER(',
    'LOWER(',
    'TRIM(',
    'SUBSTR(',
    'REPLACE(',
    'SUM(',
    'COUNT(',
    'AVG(',
    'MIN(',
    'MAX(',
    'ARRAY_AGG(',
    'AGGREGATE(',
    'RELATION_AGGREGATE(',
)

# Top-level boolean operators. If any of these appear *outside* string
# literals and outside balanced parentheses, the expression IS a filter
# (e.g. `COALESCE("a", '') = 'x'`) and must be preserved.
_TOPLEVEL_BOOLEAN_MARKERS = (
    '=', '!=', '<>', '>', '<', '>=', '<=',
    ' IN ', ' IN(', ' NOT IN ',
    ' LIKE ', ' ILIKE ', ' SIMILAR TO ',
    ' IS NULL', ' IS NOT NULL',
    ' AND ', ' OR ',
    ' BETWEEN ',
)


def _strip_toplevel_string_literals(expr: str) -> str:
    """Replace single-quoted literals with placeholders so characters inside
    them (notably '<', '>', '=') don't fool the top-level-operator scan."""
    out = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == "'":
            # skip until the closing quote (handle '' as an escape)
            i += 1
            while i < n:
                if expr[i] == "'":
                    # doubled '' is an escape, not a terminator
                    if i + 1 < n and expr[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append("''")
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _strip_for_op_scan(expr: str) -> str:
    """Scrub literals AND SQL comments for top-level operator analysis.

    Used only by :func:`_has_toplevel_boolean_operator`. Comment-stripping
    closes a smuggling vector where ``NOT(1=1) -- AND foo = 1`` would
    otherwise expose a ``AND`` token that a quote-only scrub leaves visible.

    NOT used by :func:`_is_balanced_boolean_function_call` — there we
    *want* trailing comments / chained statements to remain visible after
    the closing paren so the call is correctly disqualified as
    "not a single function call".
    """
    out = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == "'":
            i += 1
            while i < n:
                if expr[i] == "'":
                    if i + 1 < n and expr[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append("''")
            continue
        if c == '-' and i + 1 < n and expr[i + 1] == '-':
            i += 2
            while i < n and expr[i] not in ('\n', '\r'):
                i += 1
            out.append(' ')
            continue
        if c == '/' and i + 1 < n and expr[i + 1] == '*':
            i += 2
            while i < n - 1:
                if expr[i] == '*' and expr[i + 1] == '/':
                    i += 2
                    break
                i += 1
            else:
                i = n
            out.append(' ')
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _has_toplevel_boolean_operator(expr: str) -> bool:
    """True if expr contains a boolean operator at parenthesis-depth 0,
    ignoring characters inside single-quoted string literals.
    """
    stripped = _strip_for_op_scan(expr)
    upper = stripped.upper()

    depth = 0
    toplevel_chars = []
    # Build a depth-0 only projection, replacing nested content with spaces
    # (so the substring scan below only sees the outer skeleton).
    for ch in upper:
        if ch == '(':
            depth += 1
            toplevel_chars.append(' ')
        elif ch == ')':
            depth -= 1
            toplevel_chars.append(' ')
        else:
            toplevel_chars.append(ch if depth == 0 else ' ')
    toplevel = ''.join(toplevel_chars)

    # P1-SAN-WS (audit 2026-04-29): collapse all whitespace runs to a
    # single ASCII space so markers like ' AND ' / ' IN ' match against
    # tab- or `\v`/`\f`-separated input. Without this, a legitimate
    # filter ``field\tAND\tvalue`` survived as a "display expression"
    # and got dropped.
    toplevel = re.sub(r'\s+', ' ', toplevel)

    for marker in _TOPLEVEL_BOOLEAN_MARKERS:
        if marker in toplevel:
            return True
    return False


_FUNCTION_CALL_RE = re.compile(r'^[A-Z_][A-Z0-9_]*\s*\(')

# Function/keyword calls whose return type IS boolean and which therefore form
# a valid standalone WHERE body. The generic `_FUNCTION_CALL_RE` rule below
# would otherwise wipe these — `EXISTS(...)` is exactly the shape FilterMate
# pushes to target layers in chain filters, `NOT(...)` is a plain unary
# boolean operator, and the ST_* predicates are exactly what the spatialite /
# postgresql cascades emit on target layers (e.g. ``ST_Intersects(geom, ...)``).
# Without this short-circuit, target-layer subsets get sanitized to '' and the
# cascade silently drops every downstream filter — same regression class as
# the 2026-04-27 EXISTS/NOT wipe; ST_* added 2026-04-29 after spatialite
# cascade reproduced it on a fully-spatialite project.
_BOOLEAN_FUNCTION_RE = re.compile(
    r'^(EXISTS|NOT|ST_INTERSECTS|ST_CONTAINS|ST_WITHIN|ST_TOUCHES|ST_OVERLAPS'
    r'|ST_CROSSES|ST_DISJOINT|ST_EQUALS|ST_DWITHIN|ST_COVERS|ST_COVEREDBY'
    r'|ST_3DINTERSECTS|ST_3DDISJOINT|ST_3DDWITHIN)\s*\('
)


def _is_balanced_boolean_function_call(expr: str) -> bool:
    """True if ``expr`` is *exactly* a single ``EXISTS(...)`` or ``NOT(...)``
    call with balanced parentheses and nothing trailing.

    S3 hardening (2026-04-29): :data:`_BOOLEAN_FUNCTION_RE` only checks that
    the expression *starts* with ``EXISTS(`` or ``NOT(``. A payload like
    ``NOT(1=1); DROP TABLE x; --`` matches the regex and was therefore
    short-circuited as a "preserved boolean function", letting the chained
    statement survive the sanitizer. This helper validates that the matching
    closing paren ends the string (whitespace excluded), so chained
    statements / DDL keywords / comments after the close are caught by the
    downstream display-expression rules instead.

    String literals are scrubbed first so embedded ``)`` or ``;`` inside
    ``'...'`` don't break the depth counter.
    """
    if not _BOOLEAN_FUNCTION_RE.match(expr.upper()):
        return False

    scrubbed = _strip_toplevel_string_literals(expr)
    open_idx = scrubbed.find('(')
    if open_idx == -1:
        return False

    depth = 0
    for i in range(open_idx, len(scrubbed)):
        ch = scrubbed[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                # Matching close found. Anything past it (after whitespace)
                # disqualifies the expression as a single boolean call.
                return scrubbed[i + 1:].strip() == ''
    # Unbalanced parens — not a clean call.
    return False


def _is_standalone_display_expression(expr: str) -> bool:
    """True if `expr` is a display function call / field reference with no
    outer boolean operator — i.e. it cannot be used as a SQL WHERE clause.

    M2 hardening (2026-04-27): primary detection is "no top-level boolean
    operator". The known-prefix list (``_DISPLAY_FUNCTION_PREFIXES``) is now a
    confidence booster, not the trigger — any future QGIS display function
    name slips through the denylist otherwise.
    """
    if not expr or not expr.strip():
        return False

    stripped = expr.strip()
    upper = stripped.upper()

    # Boolean literals and a bare boolean column ref are valid WHERE bodies.
    if upper in ('TRUE', 'FALSE'):
        return False

    # A subset that already exposes a boolean operator at depth 0 is by
    # definition usable as WHERE — leave it alone.
    if _has_toplevel_boolean_operator(stripped):
        return False

    # From here on, we know there is NO top-level boolean operator. Decide
    # whether the expression nonetheless looks like something the backend
    # will reject (field ref / function call) versus a literal we'd rather
    # leave to the backend.

    # Field-only reference: "field" or "table"."field" with nothing else.
    if stripped.startswith('"') and stripped.endswith('"'):
        inner = stripped[1:-1]
        if '"' not in inner or inner.replace('"."', '').replace('"', '') == inner.replace('"."', '').replace('"', ''):
            return True

    # Boolean-returning function calls (EXISTS, NOT) ARE valid WHERE bodies
    # even though they look like a single function call with no top-level
    # boolean operator. Must short-circuit before the generic call rule
    # below — but only when the call is balanced and self-contained, so
    # chained payloads like ``NOT(1=1); DROP TABLE x; --`` (S3) fall
    # through to the generic display-expression drop instead.
    if _is_balanced_boolean_function_call(stripped):
        return False

    # Known display function prefix (fast-path / explicit confidence).
    for prefix in _DISPLAY_FUNCTION_PREFIXES:
        if upper.startswith(prefix):
            return True

    # Generic function call FOO(...): any IDENTIFIER( without a top-level
    # boolean operator can't be a WHERE body. Catches future QGIS display
    # functions that aren't in the prefix list.
    if _FUNCTION_CALL_RE.match(upper):
        return True

    return False


# Translated operators, upper case and between whitespace, rewritten on text
# whose literals and identifiers are masked (see sanitize_subset_string).
_FRENCH_OPERATORS = (
    (re.compile(r'\s+ET\s+NON\s+'), ' AND NOT '),
    (re.compile(r'\s+ET\s+'), ' AND '),
    (re.compile(r'\s+OU\s+'), ' OR '),
    (re.compile(r'\s+NON\s+'), ' NOT '),
)


def _normalize_french_operators(masked: str) -> str:
    for pattern, replacement in _FRENCH_OPERATORS:
        if pattern.search(masked):
            logger.info(
                f"FilterMate: Normalizing French operator '{pattern.pattern}' to '{replacement}'"
            )
            masked = pattern.sub(replacement, masked)
    return masked


_IDENT = IDENTIFIER_PLACEHOLDER
_LITERAL = LITERAL_PLACEHOLDER


def _remove_display_expressions(masked: str) -> str:
    """PHASE 1 of :func:`sanitize_subset_string`, on masked text."""
    # Pattern to match AND/OR followed by coalesce display expressions
    # CRITICAL: These patterns must match display expressions that return values, not booleans
    # Example: AND ( COALESCE( "LABEL", '<NULL>' ) ) - returns text, not boolean
    # Note: The outer ( ) wraps coalesce(...) with possible spaces
    #
    # FIX v2.5.13: Handle spaces INSIDE COALESCE( ... ) and around parentheses
    # Real-world example that FAILED: AND ( COALESCE( "LABEL", '<NULL>' ) )
    #
    # 2026-10-17: the text is masked, "field" and '<NULL>' are placeholders
    # (a ')' or 'AND (coalesce(' inside a value no longer matches).
    coalesce_patterns = [
        # Match coalesce with spaces everywhere: AND ( COALESCE( "field", '<NULL>' ) )
        # This handles the PostgreSQL-generated format with spaces
        rf'(?:^|\s+)AND\s+\(\s*COALESCE\s*\(\s*{_IDENT}\s*,\s*{_LITERAL}\s*\)\s*\)',
        rf'(?:^|\s+)OR\s+\(\s*COALESCE\s*\(\s*{_IDENT}\s*,\s*{_LITERAL}\s*\)\s*\)',
        # Match AND/OR followed by coalesce expression with nested content
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)',
        # Simpler patterns for common cases
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\([^)]+\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\([^)]+\)\s*\)',
        # Match table.field syntax
        rf'(?:^|\s+)AND\s+\(\s*coalesce\s*\(\s*{_IDENT}\s*\.\s*{_IDENT}\s*,\s*{_LITERAL}\s*\)\s*\)',
        rf'(?:^|\s+)OR\s+\(\s*coalesce\s*\(\s*{_IDENT}\s*\.\s*{_IDENT}\s*,\s*{_LITERAL}\s*\)\s*\)',
    ]

    for pattern in coalesce_patterns:
        match = re.search(pattern, masked, re.IGNORECASE)
        if match:
            logger.info("FilterMate: Removing invalid coalesce expression")
            masked = re.sub(pattern, '', masked, flags=re.IGNORECASE)

    # Pattern to match AND/OR followed by CASE expressions that just return true/false
    # These are style/display expressions, not filter conditions
    # Match: AND ( case when ... end ) OR AND ( SELECT CASE when ... end )
    # with multiple closing parentheses (malformed)
    #
    # CRITICAL FIX v2.5.10: Improved patterns to handle multi-line CASE expressions
    # like those from rule-based symbology:
    #   AND ( SELECT CASE
    #     WHEN 'AV' = left("table"."field", 2) THEN true
    #     WHEN 'PL' = left("table"."field", 2) THEN true
    #     ...
    #   end )

    # IMPROVED PATTERN: Match AND ( SELECT CASE ... WHEN ... THEN true/false ... end )
    # This pattern is more robust for multi-line expressions from QGIS rule-based symbology
    select_case_pattern = (
        r'\s*AND\s+\(\s*SELECT\s+CASE\s+'
        r'(?:WHEN\s+.+?THEN\s+(?:true|false)\s*)+'
        r'\s*(?:ELSE\s+.+?)?\s*end\s*\)'
    )

    if re.search(select_case_pattern, masked, re.IGNORECASE | re.DOTALL):
        logger.info("FilterMate: Removing SELECT CASE style expression")
        masked = re.sub(select_case_pattern, '', masked, flags=re.IGNORECASE | re.DOTALL)

    # Also check for simpler CASE patterns without SELECT
    case_patterns = [
        # Standard CASE expression with true/false returns
        (r'\s*AND\s+\(\s*CASE\s+(?:WHEN\s+.+?THEN\s+(?:true|false)\s*)+'
         r'(?:ELSE\s+.+?)?\s*END\s*\)+'),
        (r'\s*OR\s+\(\s*CASE\s+(?:WHEN\s+.+?THEN\s+(?:true|false)\s*)+'
         r'(?:ELSE\s+.+?)?\s*END\s*\)+'),
        # SELECT CASE expression (from rule-based styles) - backup pattern
        r'\s*AND\s+\(\s*SELECT\s+CASE\s+.+?\s+END\s*\)+',
        r'\s*OR\s+\(\s*SELECT\s+CASE\s+.+?\s+END\s*\)+',
    ]

    for pattern in case_patterns:
        match = re.search(pattern, masked, re.IGNORECASE | re.DOTALL)
        # Verify this is a display/style expression (returns true/false, not a comparison)
        if match and re.search(r'\bTHEN\s+(true|false)\b', match.group(), re.IGNORECASE):
            logger.info("FilterMate: Removing invalid CASE/style expression")
            masked = re.sub(pattern, '', masked, flags=re.IGNORECASE | re.DOTALL)

    # Remove standalone coalesce expressions at start
    # FIX v2.5.13: Handle spaces inside coalesce expressions
    standalone_coalesce = r'^\s*\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)\s*(?:AND|OR)?'
    if re.match(standalone_coalesce, masked, re.IGNORECASE):
        logger.info("FilterMate: Removing standalone coalesce")
        masked = re.sub(standalone_coalesce, '', masked, flags=re.IGNORECASE)
    return masked


def _fix_parentheses(masked: str) -> str:
    """PHASE 2: drop trailing ')' that close nothing (counted outside quotes)."""
    open_count = masked.count('(')
    close_count = masked.count(')')

    if close_count > open_count:
        # Remove excess closing parentheses from the end
        excess = close_count - open_count
        # Remove trailing )))) patterns
        trailing_parens = re.search(r'\)+\s*$', masked)
        if trailing_parens:
            parens_at_end = len(trailing_parens.group().strip())
            if parens_at_end >= excess:
                masked = re.sub(r'\){' + str(excess) + r'}\s*$', '', masked)
                logger.info(f"FilterMate: Removed {excess} excess closing parentheses")
    return masked


# ``( "field" )`` / ``( "t"."field" )`` / ``( "field"::type )``, group 1 = the
# placeholder index of the field.
_FIELD_TERM = rf'\(\s*(?:{_IDENT}\s*\.\s*)?\x04(\d+)\x05(?:\s*::\s*\w+)?\s*\)'
_FIELD_TERM_AFTER_OPERATOR_RE = re.compile(
    rf'\s+(?:AND|OR)\s+{_FIELD_TERM}(?=\s*(?:\)|$|(?:AND|OR)\b))', re.IGNORECASE)
_FIELD_TERM_BEFORE_OPERATOR_RE = re.compile(
    rf'(?:(?<=\()|^)\s*{_FIELD_TERM}\s+(?:AND|OR)\s+', re.IGNORECASE)


def _drop_text_field_terms(masked: str, parts: list, text_fields) -> str:
    """PHASE 2.5: drop an operand ``( "field" )`` of an AND / OR chain when field is a TEXT column.

    FIX v4.8.0 (2026-01-25): a display expression (the layer's display field)
    glued to a filter: PostgreSQL refuses it ("argument of AND must be type
    boolean, not type character varying"). 2026-10-17: only an operand that is
    exactly a parenthesized column, outside quotes, and only a column the
    caller knows to be text (``text_fields``, lower-case names): v4.8.0
    dropped every one, so a real condition on a boolean column
    (``AND ( "actif" )``) disappeared and the layer silently showed more (AND)
    or fewer (OR) features. Without ``text_fields`` nothing is dropped.
    """
    if not text_fields or '\x04' not in masked:
        return masked

    def _drop(match):
        name = parts[int(match.group(1))][1:-1].replace('""', '"').lower()
        if name not in text_fields:
            return match.group(0)
        logger.info(f"FilterMate: Removing non-boolean field expression ( \"{name}\" ) (text column)")
        return ''

    masked = _FIELD_TERM_AFTER_OPERATOR_RE.sub(_drop, masked)
    return _FIELD_TERM_BEFORE_OPERATOR_RE.sub(_drop, masked)


def _clean_operators(masked: str) -> str:
    """PHASE 3: whitespace and orphaned operators (outside quotes)."""
    masked = re.sub(r'\s+', ' ', masked).strip()
    masked = re.sub(r'\s+(AND|OR)\s*$', '', masked, flags=re.IGNORECASE)
    masked = re.sub(r'^\s*(AND|OR)\s+', '', masked, flags=re.IGNORECASE)

    # Remove duplicate AND/OR operators
    masked = re.sub(r'\s+AND\s+AND\s+', ' AND ', masked, flags=re.IGNORECASE)
    masked = re.sub(r'\s+OR\s+OR\s+', ' OR ', masked, flags=re.IGNORECASE)
    return masked


def sanitize_subset_string(subset_string: str, text_fields=None) -> str:
    """
    Remove non-boolean display expressions and fix type casting issues in subset string.

    Display expressions like 'coalesce("field",'<NULL>')' or CASE expressions that
    return true/false are valid QGIS expressions but cause issues in SQL WHERE clauses.
    This function removes such expressions and fixes common type casting issues.

    Process:
    1. Normalize French SQL operators (ET/OU/NON → AND/OR/NOT)
    2. Remove non-boolean display expressions (coalesce, CASE)
    3. Fix unbalanced parentheses
    4. Drop ``( "text column" )`` operands (when ``text_fields`` is given)
    5. Clean up whitespace and orphaned operators

    2026-10-17: every phase after -1 runs on the text with its string
    literals, identifiers and comments masked (sql_quotes): a value such as
    'Plages, dunes et sable', 'b)' or 'Saint  Jean' is never rewritten.

    Args:
        subset_string: The original subset string
        text_fields: Lower-case names of the layer's text columns, if known
            (safe_set_subset_string passes them)

    Returns:
        str: Sanitized subset string with non-boolean expressions removed
    """
    if not subset_string:
        return subset_string

    # ========================================================================
    # PHASE -1: Reject standalone display expressions
    # ========================================================================
    # FIX 2026-04-23: the AND/OR-prefixed coalesce/CASE patterns below only
    # strip display expressions that are *glued onto* a boolean filter. When
    # the WHOLE subset is a display expression (e.g. the favorite stored the
    # layer's displayExpression by mistake, or QGIS left a sticky invalid
    # subset after a prior rejected setSubsetString call), it reaches
    # PostgreSQL as `WHERE COALESCE(...)` → "argument of WHERE must be type
    # boolean, not type character varying".
    #
    # We detect this by checking whether the expression starts with a known
    # display function and *does not* contain a top-level boolean operator
    # after the outer function call. A direct prefix check avoids the
    # is_filter_expression() false positive where '<' inside a '<NULL>'
    # placeholder is mistaken for a comparison operator.
    if _is_standalone_display_expression(subset_string):
        logger.info(
            "FilterMate: Dropping non-boolean subset string "
            f"(display expression, not a filter): '{subset_string[:80]}...'"
        )
        return ''

    masked, parts = mask_quoted(subset_string)

    # ========================================================================
    # PHASE 0: Normalize French SQL operators to English
    # ========================================================================
    # QGIS expressions support French operators (ET, OU, NON) but PostgreSQL
    # only understands English operators (AND, OR, NOT). This normalization
    # ensures compatibility with all SQL backends.
    #
    # FIX v2.5.12: Handle French operators that cause SQL syntax errors like:
    # "syntax error at or near 'ET'"
    #
    # 2026-10-17: outside string literals and identifiers only, and upper case
    # only. Case-insensitive on the whole string, it turned the value
    # 'Plages, dunes et sable' into 'Plages, dunes AND sable' (0 features),
    # and an unquoted lower-case column named "ou" into OR. The translated
    # operators FilterMate stored were upper case (normalize_sql_operator).
    masked = _normalize_french_operators(masked)

    # PHASE 1: Remove non-boolean display expressions
    masked = _remove_display_expressions(masked)

    # PHASE 2: Fix unbalanced parentheses
    masked = _fix_parentheses(masked)

    # PHASE 2.5: Remove ( "text column" ) operands
    masked = _drop_text_field_terms(masked, parts, text_fields)

    # PHASE 3: Clean up whitespace and orphaned operators
    masked = _clean_operators(masked)

    sanitized = unmask_quoted(masked, parts)
    if sanitized != subset_string:
        logger.info(
            f"FilterMate: Subset sanitized from '{subset_string[:80]}...' "
            f"to '{sanitized[:80]}...'"
        )

    return sanitized


# Parentheses and words; only AND / OR / BETWEEN / CASE matter (matching every
# word is twice as fast as a keyword alternation on a 100,000-key list).
_TOPLEVEL_TOKEN_RE = re.compile(r'[()]|[A-Za-z_]\w*')
_CHAIN_WORDS = frozenset(('AND', 'OR', 'BETWEEN', 'CASE'))


def _split_toplevel_and(masked: str) -> Optional[list]:
    """Depth-0 AND operands of masked text, or None if it is not an AND chain.

    None when a depth-0 OR or a CASE appears: dropping an operand is only exact
    inside a plain conjunction. The AND of ``BETWEEN a AND b`` is not a split.
    """
    pieces = []
    depth = 0
    start = 0
    in_between = False
    for match in _TOPLEVEL_TOKEN_RE.finditer(masked):
        token = match.group().upper()
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token not in _CHAIN_WORDS:
            continue
        elif token == 'CASE':
            return None
        elif depth == 0:
            if token == 'OR':
                return None
            if token == 'BETWEEN':
                in_between = True
            elif in_between:
                in_between = False
            else:
                pieces.append(masked[start:match.start()].strip())
                start = match.end()
    pieces.append(masked[start:].strip())
    return pieces


def _flat_conjuncts(masked: str) -> list:
    """Operands of nested AND chains: ``(A AND B) AND C`` -> A, B, C."""
    term = _strip_outer_parens(masked)
    pieces = _split_toplevel_and(term)
    if not pieces or len(pieces) == 1:
        return [term]
    flat = []
    for piece in pieces:
        flat.extend(_flat_conjuncts(piece))
    return flat


_PLACEHOLDER_INDEX_RE = re.compile('([\x02\x04\x06])\\d+')


def _shape_key(masked: str) -> str:
    """A term with spacing and keyword case normalized, its quoted parts reduced to their kind.

    Equal comparison keys imply equal shapes: the (costly) comparison keys are
    only computed for terms of the same shape.
    """
    # str methods, not re.sub with a callback: a key list has 100,000 commas
    text = ' '.join(masked.split())
    for spaced, tight in ((' (', '('), ('( ', '('), (' )', ')'), (') ', ')'), (' ,', ','), (', ', ',')):
        text = text.replace(spaced, tight)
    return _PLACEHOLDER_INDEX_RE.sub(r'\1', text.upper())


def _comparison_key(masked: str, parts) -> str:
    """Text of a term with spacing and keyword case normalized (quoted parts verbatim)."""
    text = ' '.join(masked.split())
    for spaced, tight in ((' (', '('), ('( ', '('), (' )', ')'), (') ', ')'), (' ,', ','), (', ', ',')):
        text = text.replace(spaced, tight)
    return unmask_quoted(text.upper(), parts)


def optimize_duplicate_in_clauses(expression: str) -> str:
    """
    Remove duplicate conditions from an AND chain.

    OPTIMIZATION v2.5.13: Multi-step filtering generates duplicate clauses like:
    (A AND fid IN (1,2,3)) AND (fid IN (1,2,3)) AND (fid IN (1,2,3))

    2026-10-17: an operand of the top-level AND chain is removed only when it
    is the SAME condition as an operand already kept, nested AND chains
    included (spacing and keyword case aside, values compared verbatim):
    ``X AND X`` is ``X``, so ``((B AND A) AND A)`` gives ``(B AND A)``. It used
    to keep the first IN clause of each FIELD, so
    ``("fid" IN (1,2,3)) AND ("fid" IN (2,3))`` lost its second condition, and
    parentheses or spaces inside values were miscounted / squeezed. Nothing
    is removed around a depth-0 OR or a CASE.

    Args:
        expression: SQL expression potentially containing duplicate conditions

    Returns:
        str: Optimized expression with duplicate conditions removed
    """
    if not expression:
        return expression

    masked, parts = mask_quoted(expression)
    pieces = _split_toplevel_and(_strip_outer_parens(masked))
    if not pieces or len(pieces) <= 1:
        return expression  # No duplicates possible

    kept = []
    seen = {}  # shape key -> masked terms already kept with that shape
    for piece in pieces:
        term = _strip_outer_parens(piece)
        shape = _shape_key(term)
        candidates = seen.get(shape, ())
        if candidates and _comparison_key(term, parts) in {_comparison_key(other, parts) for other in candidates}:
            logger.debug(f"FilterMate: Removed duplicate condition {unmask_quoted(piece, parts)[:60]}")
            continue
        kept.append(piece)
        # a term without AND is its only conjunct (no second scan of a key list)
        flats = _flat_conjuncts(term) if 'AND' in term.upper() else [term]
        for flat in flats:
            seen.setdefault(shape if flat == term else _shape_key(flat), []).append(flat)

    if len(kept) == len(pieces):
        return expression

    result = unmask_quoted(' AND '.join(kept), parts)

    # Log optimization results
    savings = len(expression) - len(result)
    pct = 100 * savings / len(expression)
    logger.info(
        f"FilterMate: OPTIMIZATION - Removed {len(pieces) - len(kept)} duplicate conditions, "
        f"{savings} bytes ({pct:.1f}% reduction)"
    )

    return result


def extract_spatial_clauses_for_exists(filter_expr: str, source_table: Optional[str] = None) -> Optional[str]:
    """
    Extract only spatial clauses (ST_Intersects, etc.) from a filter expression.

    EPIC-1 Phase E7.5: Extracted from filter_task.py _extract_spatial_clauses_for_exists.

    CRITICAL FIX v2.5.11: For EXISTS subqueries in PostgreSQL, we must include
    the source layer's spatial filter to ensure we only consider filtered features.
    However, we must EXCLUDE:
    - Style-based rules (SELECT CASE ... THEN true/false)
    - Attribute-only filters (without spatial predicates)
    - coalesce display expressions

    This ensures the EXISTS query sees the same filtered source as QGIS.

    Args:
        filter_expr: The source layer's current subsetString
        source_table: Source table name for reference replacement (unused, kept for API)

    Returns:
        str: Extracted spatial clauses only, or None if no spatial predicates found
    """
    if not filter_expr:
        return None

    # List of spatial predicates to extract
    SPATIAL_PREDICATES = [
        'ST_Intersects', 'ST_Contains', 'ST_Within', 'ST_Touches',
        'ST_Overlaps', 'ST_Crosses', 'ST_Disjoint', 'ST_Equals',
        'ST_DWithin', 'ST_Covers', 'ST_CoveredBy'
    ]

    # Check if filter contains any spatial predicates
    filter_upper = filter_expr.upper()
    has_spatial = any(pred.upper() in filter_upper for pred in SPATIAL_PREDICATES)

    if not has_spatial:
        logger.debug("extract_spatial_clauses: No spatial predicates in filter")
        return None

    # First, remove style-based expressions (SELECT CASE ... THEN true/false)
    cleaned = filter_expr

    # Pattern for SELECT CASE style rules (multi-line support)
    select_case_pattern = r'\s*AND\s+\(\s*SELECT\s+CASE\s+(?:WHEN\s+.+?THEN\s+(?:true|false)\s*)+\s*(?:ELSE\s+.+?)?\s*end\s*\)'
    cleaned = re.sub(select_case_pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

    # Pattern for simple CASE style rules
    case_pattern = r'\s*AND\s+\(\s*CASE\s+(?:WHEN\s+.+?THEN\s+(?:true|false)\s*)+(?:ELSE\s+.+?)?\s*END\s*\)+'
    cleaned = re.sub(case_pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

    # Remove coalesce display expressions
    # FIX v2.5.13: Handle spaces inside COALESCE( ... )
    coalesce_pattern = r'\s*(?:AND|OR)\s+\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)'
    cleaned = re.sub(coalesce_pattern, '', cleaned, flags=re.IGNORECASE)

    # Clean up whitespace and operators
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'\s+(AND|OR)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\s*(AND|OR)\s+', '', cleaned, flags=re.IGNORECASE)

    # Remove outer parentheses if present
    while cleaned.startswith('(') and cleaned.endswith(')'):
        # Check if these are matching outer parens
        depth = 0
        is_outer = True
        for i, char in enumerate(cleaned):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and i < len(cleaned) - 1:
                    is_outer = False
                    break
        if is_outer and depth == 0:
            cleaned = cleaned[1:-1].strip()
        else:
            break

    # Verify cleaned expression still contains spatial predicates
    cleaned_upper = cleaned.upper()
    has_spatial_after_clean = any(pred.upper() in cleaned_upper for pred in SPATIAL_PREDICATES)

    if not has_spatial_after_clean:
        logger.debug("extract_spatial_clauses: Spatial predicates removed during cleaning")
        return None

    # Validate parentheses are balanced
    if cleaned.count('(') != cleaned.count(')'):
        logger.warning("extract_spatial_clauses: Unbalanced parentheses after extraction")
        return None

    logger.info(f"extract_spatial_clauses: Extracted spatial filter: '{cleaned[:100]}...'")
    return cleaned


_WELL_FORMED_EXISTS = re.compile(
    r'EXISTS\s*\(\s*SELECT\s+.+?\s+FROM\s+.+?\s+AS\s+__source\s+WHERE\s+.+\)',
    re.IGNORECASE | re.DOTALL,
)


def contains_well_formed_exists(subset_string: Optional[str]) -> bool:
    """True when ``subset_string`` holds a complete ``EXISTS (SELECT ... AS __source WHERE ...)`` block.

    2026-09-13: used by the corrupted-subset cleaner. The PostgreSQL builder
    may put the source envelope prefilter in front of the EXISTS
    (``("t"."geom" && (SELECT ... AS __source WHERE ...)) AND EXISTS (...)``),
    so the block is searched anywhere, not only at the start.
    """
    if not subset_string:
        return False
    return bool(_WELL_FORMED_EXISTS.search(subset_string))
