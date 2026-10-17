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

from .sql_quotes import IDENTIFIER_PLACEHOLDER, map_outside_quotes, mask_quoted, unmask_quoted

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


def _fix_structure(masked: str) -> str:
    """Phases 2 and 3 of :func:`sanitize_subset_string`, on masked text."""
    # ========================================================================
    # PHASE 2: Fix unbalanced parentheses
    # ========================================================================

    # Count parentheses and fix if unbalanced
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

    # PHASE 2.5 (v4.8.0) dropped every ``AND ( "field" )`` / ``OR ( "field" )``
    # as a display expression glued to a filter (PostgreSQL: "argument of AND
    # must be type boolean"). 2026-10-17: removed, it also dropped real
    # conditions on boolean columns (``AND ( "actif" )``) and the layer showed
    # more (AND) or fewer (OR) features without a word. Field-only display
    # expressions are refused upstream (process_qgis_expression) and a
    # standalone one by PHASE -1; a text column used as a condition now fails
    # visibly instead of silently changing the result.

    # ========================================================================
    # PHASE 3: Clean up whitespace and orphaned operators
    # ========================================================================

    masked = re.sub(r'\s+', ' ', masked).strip()
    masked = re.sub(r'\s+(AND|OR)\s*$', '', masked, flags=re.IGNORECASE)
    masked = re.sub(r'^\s*(AND|OR)\s+', '', masked, flags=re.IGNORECASE)

    # Remove duplicate AND/OR operators
    masked = re.sub(r'\s+AND\s+AND\s+', ' AND ', masked, flags=re.IGNORECASE)
    masked = re.sub(r'\s+OR\s+OR\s+', ' OR ', masked, flags=re.IGNORECASE)
    return masked


def sanitize_subset_string(subset_string: str) -> str:
    """
    Remove non-boolean display expressions and fix type casting issues in subset string.

    Display expressions like 'coalesce("field",'<NULL>')' or CASE expressions that
    return true/false are valid QGIS expressions but cause issues in SQL WHERE clauses.
    This function removes such expressions and fixes common type casting issues.

    Process:
    1. Normalize French SQL operators (ET/OU/NON → AND/OR/NOT)
    2. Remove non-boolean display expressions (coalesce, CASE)
    3. Fix unbalanced parentheses
    4. Clean up whitespace and orphaned operators

    Args:
        subset_string: The original subset string

    Returns:
        str: Sanitized subset string with non-boolean expressions removed
    """
    if not subset_string:
        return subset_string

    sanitized = subset_string

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
    if _is_standalone_display_expression(sanitized):
        logger.info(
            "FilterMate: Dropping non-boolean subset string "
            f"(display expression, not a filter): '{sanitized[:80]}...'"
        )
        return ''

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
    sanitized = map_outside_quotes(sanitized, _normalize_french_operators)

    # ========================================================================
    # PHASE 1: Remove non-boolean display expressions
    # ========================================================================

    # Pattern to match AND/OR followed by coalesce display expressions
    # CRITICAL: These patterns must match display expressions that return values, not booleans
    # Example: AND ( COALESCE( "LABEL", '<NULL>' ) ) - returns text, not boolean
    # Note: The outer ( ) wraps coalesce(...) with possible spaces
    #
    # FIX v2.5.13: Handle spaces INSIDE COALESCE( ... ) and around parentheses
    # Real-world example that FAILED: AND ( COALESCE( "LABEL", '<NULL>' ) )
    coalesce_patterns = [
        # Match coalesce with spaces everywhere: AND ( COALESCE( "field", '<NULL>' ) )
        # This handles the PostgreSQL-generated format with spaces
        r'(?:^|\s+)AND\s+\(\s*COALESCE\s*\(\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*COALESCE\s*\(\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
        # Match coalesce with quoted string containing special chars like '<NULL>'
        # Pattern: AND (coalesce("field",'<NULL>'))  - compact format
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\(\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\(\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
        # Match AND/OR followed by coalesce expression with nested content
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)',
        # Simpler patterns for common cases
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\([^)]+\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\([^)]+\)\s*\)',
        # Match table.field syntax
        r'(?:^|\s+)AND\s+\(\s*coalesce\s*\(\s*"[^"]+"\s*\.\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
        r'(?:^|\s+)OR\s+\(\s*coalesce\s*\(\s*"[^"]+"\s*\.\s*"[^"]+"\s*,\s*\'[^\']*\'\s*\)\s*\)',
    ]

    for pattern in coalesce_patterns:
        match = re.search(pattern, sanitized, re.IGNORECASE)
        if match:
            logger.info(
                "FilterMate: Removing invalid coalesce expression: "
                f"'{match.group()[:60]}...'"
            )
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

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

    match = re.search(select_case_pattern, sanitized, re.IGNORECASE | re.DOTALL)
    if match:
        logger.info(
            f"FilterMate: Removing SELECT CASE style expression: '{match.group()[:80]}...'"  # nosec B608
        )
        sanitized = re.sub(
            select_case_pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL
        )

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
        match = re.search(pattern, sanitized, re.IGNORECASE | re.DOTALL)
        if match:
            # Verify this is a display/style expression (returns true/false, not a comparison)
            matched_text = match.group()
            # Check if it's just "then true/false" without external comparison
            if re.search(r'\bTHEN\s+(true|false)\b', matched_text, re.IGNORECASE):
                logger.info(
                    "FilterMate: Removing invalid CASE/style expression: "
                    f"'{matched_text[:60]}...'"
                )
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

    # Remove standalone coalesce expressions at start
    # FIX v2.5.13: Handle spaces inside coalesce expressions
    standalone_coalesce = r'^\s*\(\s*coalesce\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\)\s*(?:AND|OR)?'
    if re.match(standalone_coalesce, sanitized, re.IGNORECASE):
        match = re.match(standalone_coalesce, sanitized, re.IGNORECASE)
        logger.info(f"FilterMate: Removing standalone coalesce: '{match.group()[:60]}...'")
        sanitized = re.sub(standalone_coalesce, '', sanitized, flags=re.IGNORECASE)

    # Phases 2 and 3 run on the text with its literals and identifiers masked
    # (2026-10-17): a ")" or a run of spaces inside 'b)' or 'Saint  Jean'
    # belongs to the value, so it is neither counted nor squeezed.
    sanitized = map_outside_quotes(sanitized, _fix_structure)

    if sanitized != subset_string:
        logger.info(
            f"FilterMate: Subset sanitized from '{subset_string[:80]}...' "
            f"to '{sanitized[:80]}...'"
        )

    return sanitized


_TOPLEVEL_TOKEN_RE = re.compile(r'\(|\)|\b(?:AND|OR|BETWEEN|CASE)\b', re.IGNORECASE)
_IN_CLAUSE_RE = re.compile(
    rf'^{IDENTIFIER_PLACEHOLDER}(?:\s*\.\s*{IDENTIFIER_PLACEHOLDER})?\s+IN\s*\(',
    re.IGNORECASE,
)


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


def _strip_outer_parens(masked: str) -> str:
    """``( x )`` -> ``x`` while the outer parentheses enclose the whole text."""
    text = masked.strip()
    while text.startswith('(') and text.endswith(')'):
        depth = 0
        for i, char in enumerate(text):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and i < len(text) - 1:
                    return text
        text = text[1:-1].strip()
    return text


def _is_in_clause(masked: str) -> bool:
    """``"field" IN (...)`` / ``"t"."field" IN (...)`` and nothing after the list."""
    match = _IN_CLAUSE_RE.match(masked)
    if not match:
        return False
    depth = 0
    for i in range(match.end() - 1, len(masked)):
        if masked[i] == '(':
            depth += 1
        elif masked[i] == ')':
            depth -= 1
            if depth == 0:
                return masked[i + 1:].strip() == ''
    return False


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


def _comparison_key(masked: str, parts: list) -> str:
    """Text of a term with spacing and keyword case normalized (quoted parts verbatim)."""
    text = re.sub(r'\s+', ' ', masked).strip()
    text = re.sub(r'\s*([(),])\s*', r'\1', text).upper()
    return unmask_quoted(text, parts)


def optimize_duplicate_in_clauses(expression: str) -> str:
    """
    Remove duplicate IN clauses from an expression.

    OPTIMIZATION v2.5.13: Multi-step filtering generates duplicate clauses like:
    (A AND fid IN (1,2,3)) AND (fid IN (1,2,3)) AND (fid IN (1,2,3))

    2026-10-17: only an operand of the top-level AND chain that is the SAME
    ``"field" IN (...)`` clause as an operand already kept (spacing and keyword
    case aside, values compared verbatim) is removed: ``X AND X`` is ``X``.
    It used to keep the first IN clause of each FIELD, so
    ``("fid" IN (1,2,3)) AND ("fid" IN (2,3))`` lost its second condition, and
    parentheses or spaces inside values were miscounted / squeezed.

    Args:
        expression: SQL expression potentially containing duplicate IN clauses

    Returns:
        str: Optimized expression with duplicate IN clauses removed
    """
    if not expression:
        return expression

    masked, parts = mask_quoted(expression)
    pieces = _split_toplevel_and(masked)
    if not pieces or len(pieces) <= 1:
        return expression  # No duplicates possible

    kept = []
    seen = set()
    for piece in pieces:
        term = _strip_outer_parens(piece)
        key = _comparison_key(term, parts)
        if _is_in_clause(term) and key in seen:
            logger.debug(f"FilterMate: Removed duplicate clause {unmask_quoted(term, parts)[:60]}")
            continue
        kept.append(piece)
        seen.update(_comparison_key(flat, parts) for flat in _flat_conjuncts(piece))

    if len(kept) == len(pieces):
        return expression

    result = unmask_quoted(' AND '.join(kept), parts)

    # Log optimization results
    savings = len(expression) - len(result)
    pct = 100 * savings / len(expression)
    logger.info(
        f"FilterMate: OPTIMIZATION - Removed {len(pieces) - len(kept)} duplicate IN clauses, "
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
