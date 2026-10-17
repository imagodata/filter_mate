"""
Quote-aware rewriting of SQL / QGIS expression text.

2026-10-17: the sanitizer, the combiners and the QGIS -> SQL converters
rewrote whole strings with regular expressions, so the text of a value or of a
column name was rewritten too: ``"libelle" = 'Plages, dunes et sable'`` became
``'Plages, dunes AND sable'``, ``'Case-Pilote'`` became ``' CASE -Pilote'`` and
``"buffer_m"`` became ``"ST_Buffer_m"``. The helpers below hide the quoted
parts behind placeholders while a rewrite runs, then put them back verbatim.

- ``'...'`` is a string literal, ``''`` inside it is an escaped quote.
- ``"..."`` is an identifier, ``""`` inside it is an escaped quote.
- An unterminated quote runs to the end of the text (kept verbatim).

Placeholders are made of control characters and digits only: no regular
expression of the callers matches them as a word, a keyword, a quote, a
parenthesis or whitespace.
"""

import re
from typing import Callable, List, Tuple

_LITERAL_OPEN, _LITERAL_CLOSE = '\x02', '\x03'
_IDENT_OPEN, _IDENT_CLOSE = '\x04', '\x05'

# A masked string literal / identifier, as it appears in masked text.
LITERAL_PLACEHOLDER = '\x02\\d+\x03'
IDENTIFIER_PLACEHOLDER = '\x04\\d+\x05'

_PLACEHOLDER_RE = re.compile('[\x02\x04](\\d+)[\x03\x05]')


def _quoted_end(text: str, start: int) -> int:
    """Index just past the quoted run opened at ``text[start]``."""
    quote = text[start]
    i = start + 1
    n = len(text)
    while i < n:
        if text[i] == quote:
            if i + 1 < n and text[i + 1] == quote:
                i += 2
                continue
            return i + 1
        i += 1
    return n


def mask_quoted(text: str, identifiers: bool = True) -> Tuple[str, List[str]]:
    """Replace string literals (and identifiers) by placeholders.

    Args:
        text: SQL or QGIS expression text.
        identifiers: Also mask ``"..."`` identifiers. When False they stay in
            the masked text, but a ``'`` inside one still does not open a
            literal.

    Returns:
        Tuple of (masked text, quoted parts); :func:`unmask_quoted` restores.
    """
    if not text or ("'" not in text and '"' not in text):
        return text, []
    out = []
    parts: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "'" or c == '"':
            end = _quoted_end(text, i)
            quoted = text[i:end]
            if c == '"' and not identifiers:
                out.append(quoted)
            else:
                opening, closing = (_LITERAL_OPEN, _LITERAL_CLOSE) if c == "'" else (_IDENT_OPEN, _IDENT_CLOSE)
                out.append(f'{opening}{len(parts)}{closing}')
                parts.append(quoted)
            i = end
            continue
        out.append(c)
        i += 1
    return ''.join(out), parts


def unmask_quoted(masked: str, parts: List[str]) -> str:
    """Put back the quoted parts hidden by :func:`mask_quoted`."""
    if not parts:
        return masked
    return _PLACEHOLDER_RE.sub(lambda m: parts[int(m.group(1))], masked)


def map_outside_quotes(text: str, transform: Callable[[str], str], identifiers: bool = True) -> str:
    """Apply ``transform`` to ``text`` with its quoted parts hidden.

    ``transform`` must keep the placeholders it is given (it may move or
    drop them, never edit them).
    """
    if not text:
        return text
    masked, parts = mask_quoted(text, identifiers)
    return unmask_quoted(transform(masked), parts)


# QGIS -> SQL rewrites shared by ExpressionService and the backends'
# converters. Both work on text masked by mask_quoted().

# A number literal: the only other side that gets a numeric cast.
_NUMBER_OPERAND = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![\w.])'


def map_geometry_length(masked: str, parts: List[str], geometry_column: str, function: str) -> str:
    """``length($geometry)`` / ``length("<geometry column>")`` -> ``<function>(...)``.

    2026-10-17: any other length() stays: in QGIS length(string) is its
    number of characters, ST_Length / GLength of a text is an error.
    ``parts`` are the quoted parts returned with ``masked``.
    """
    column = f'"{geometry_column}"'

    def _replace(match):
        argument = match.group(1)
        if argument.startswith('$') or parts[int(argument[1:-1])] == column:
            return f'{function}({argument})'
        return match.group(0)

    return re.sub(
        rf'\blength\s*\(\s*(\$geometry\b|\$geom\b|{IDENTIFIER_PLACEHOLDER})\s*\)',
        _replace, masked, flags=re.IGNORECASE,
    )


def cast_numeric_operands(masked: str, operators: tuple, cast: str) -> str:
    """Cast a column compared / combined with a NUMBER: ``"x" > 10`` -> ``"x"::numeric > 10``.

    2026-10-17: the cast was added whatever the other side, so
    ``"nature" <> 'Route'``, dates and now() comparisons failed in PostgreSQL
    (invalid input syntax for type numeric). ``<>`` / ``!=`` are never cast.
    ``cast`` is a replacement template on the column (group 1).
    """
    alternatives = '|'.join(re.escape(op) for op in ('<>', '!=') + tuple(operators))

    def _replace(match):
        if match.group(3) in ('<>', '!='):
            return match.group(0)
        return match.expand(cast) + match.group(2) + match.group(3) + match.group(4)

    return re.sub(
        rf'({IDENTIFIER_PLACEHOLDER})(\s*)({alternatives})(\s*)(?={_NUMBER_OPERAND})',
        _replace, masked,
    )
