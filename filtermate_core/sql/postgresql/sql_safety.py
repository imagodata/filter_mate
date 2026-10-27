"""Defense-in-depth SQL safety guards for the PostgreSQL backend.

The upstream expression sanitizer (``core.filter.expression_sanitizer``) is the
first line: it normalises QGIS-flavoured expressions into PG-friendly SQL and
strips display-only function calls. It is intentionally best-effort string
surgery, not a parser — and the audit on 2026-04-29 (S3) confirmed at least one
``NOT(...)`` short-circuit bypass.

This module backs that up with a strict deny-list applied immediately before
``cursor.execute()``. Any payload that survives the sanitizer but contains a
chained statement, a SQL comment, a DDL/DML keyword, or a known PostgreSQL
escalation function is refused with :class:`SqlInjectionAttempt`.

The guards work on tokens *outside* string literals and quoted identifiers, so
a legitimate column called ``delete_at`` or a literal ``'DROP'`` does not trip
the rules.
"""
from __future__ import annotations

import re


class SqlInjectionAttempt(ValueError):
    """Raised when a WHERE clause or identifier fails defense-in-depth checks."""

    def __init__(self, reason: str, payload: str) -> None:
        super().__init__(f"Refusing PostgreSQL execution: {reason}")
        self.reason = reason
        self.payload = payload


# Identifier shape PostgreSQL accepts as an unquoted name. Anything outside
# this set forces explicit quoting at the call site — but for the columns we
# embed in f-strings (pk, table) we refuse exotic shapes outright instead of
# trusting our manual quoting to escape internal double-quotes correctly.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


# DDL/DML keywords that have no business appearing inside a row-level WHERE
# expression. Listed as standalone tokens (\b…\b) so column names like
# ``insert_date`` or ``deleted_at`` survive — but only after the placeholder
# pass below has scrubbed quoted identifiers.
_DANGEROUS_KEYWORDS_RE = re.compile(
    r"\b(?:DROP|DELETE|INSERT|UPDATE|ALTER|TRUNCATE|GRANT|REVOKE|"
    r"EXEC|EXECUTE|CREATE|COPY|VACUUM|MERGE|CALL|REINDEX|CLUSTER|LOCK)\b",
    re.IGNORECASE,
)


# PostgreSQL functions that read filesystem/network state or sleep — typical
# blind-injection / data-exfiltration primitives. The boundary is the opening
# parenthesis so column names that happen to match (extremely unlikely) are
# tolerated.
_DANGEROUS_FUNCTIONS_RE = re.compile(
    r"\b(pg_sleep|pg_read_file|pg_read_binary_file|pg_ls_dir|pg_stat_file|"
    r"pg_logfile_rotate|pg_reload_conf|dblink|dblink_exec|dblink_connect|"
    r"lo_import|lo_export|lo_get|lo_put|copy_from_program)\s*\(",
    re.IGNORECASE,
)


def _scrub_quoted(expr: str) -> str:
    """Replace single-quoted literals and double-quoted identifiers with placeholders.

    Both quoting styles use the doubled-quote escape (``''`` and ``""``). After
    this pass the string still parses the same way (length preserved), but any
    substring matching ``'…'`` or ``"…"`` becomes inert ``""``/``''`` blocks
    so subsequent regex scans don't see attacker-controlled content there.
    """
    out: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == "'" or c == '"':
            quote = c
            out.append(quote)
            i += 1
            while i < n:
                if expr[i] == quote:
                    # Doubled quote = literal escape, not a terminator.
                    if i + 1 < n and expr[i + 1] == quote:
                        i += 2
                        continue
                    out.append(quote)
                    i += 1
                    break
                # Replace the inside character with a neutral marker.
                out.append("X")
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def validate_identifier(name: str, *, kind: str = "identifier") -> str:
    """Refuse identifiers that don't match a plain ``[A-Za-z_][A-Za-z0-9_]*`` shape.

    Returns the name unchanged on success so this can be used inline. Names
    coming from QGIS layer metadata are normally clean; an exotic value is a
    strong signal of tampering and we'd rather fail loudly than rely on the
    f-string ``"…"`` escape (which doesn't even handle internal double-quotes).
    """
    if not isinstance(name, str) or not _SAFE_IDENTIFIER_RE.match(name):
        raise SqlInjectionAttempt(
            f"{kind} {name!r} fails the [A-Za-z_][A-Za-z0-9_]{{0,62}} shape",
            payload=str(name),
        )
    return name


def validate_where_clause(where_sql: str) -> None:
    """Reject WHERE clauses that look like injection attempts.

    Checks (in order, after scrubbing quoted regions):

    1. ``;`` outside string literals — chained statements.
    2. ``--`` outside string literals — line comments used to truncate the
       sanitizer's tail.
    3. ``/*`` or ``*/`` outside string literals — block comments, same idea.
    4. DDL/DML keywords as standalone tokens.
    5. Known PostgreSQL escalation functions (filesystem, network, sleep).

    An empty/whitespace ``where_sql`` is allowed — the caller decides what to
    do with it (PG will reject syntactically). Validation cost is a few regex
    scans on small strings; negligible vs. the round-trip to PG.

    Raises:
        SqlInjectionAttempt: when any rule triggers. The original payload is
            attached for logging/debug.
    """
    if not where_sql or not where_sql.strip():
        return

    scrubbed = _scrub_quoted(where_sql)

    if ";" in scrubbed:
        raise SqlInjectionAttempt(
            "statement separator ';' outside string literal",
            payload=where_sql,
        )

    if "--" in scrubbed:
        raise SqlInjectionAttempt(
            "SQL line comment '--' outside string literal",
            payload=where_sql,
        )

    if "/*" in scrubbed or "*/" in scrubbed:
        raise SqlInjectionAttempt(
            "SQL block comment outside string literal",
            payload=where_sql,
        )

    match = _DANGEROUS_KEYWORDS_RE.search(scrubbed)
    if match is not None:
        raise SqlInjectionAttempt(
            f"DDL/DML keyword {match.group(0).upper()!r} as standalone token",
            payload=where_sql,
        )

    match = _DANGEROUS_FUNCTIONS_RE.search(scrubbed)
    if match is not None:
        raise SqlInjectionAttempt(
            f"forbidden PostgreSQL function {match.group(1).lower()!r}",
            payload=where_sql,
        )
