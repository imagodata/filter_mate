"""
Quote-aware rewriting of SQL / QGIS expression text.

2026-10-17: the sanitizer, the combiners and the QGIS -> SQL converters
rewrote whole strings with regular expressions, so the text of a value or of a
column name was rewritten too: ``"libelle" = 'Plages, dunes et sable'`` became
``'Plages, dunes AND sable'``, ``'Case-Pilote'`` became ``' CASE -Pilote'`` and
``"buffer_m"`` became ``"ST_Buffer_m"``. The helpers below hide the quoted
parts behind placeholders while a rewrite runs, then put them back verbatim.

- ``'...'`` is a string literal; ``''`` and ``\\'`` (QGIS) inside it are
  escaped quotes. ``$$...$$`` / ``$tag$...$tag$`` (PostgreSQL) is a literal too.
- ``"..."`` is an identifier, ``""`` inside it is an escaped quote.
- ``-- ...`` (to the end of the line, newline included) and ``/* ... */`` are
  comments: hidden like the rest, so nothing inside them is rewritten.
- An unterminated quote or comment runs to the end of the text (kept verbatim).

Placeholders are made of control characters and digits only: no regular
expression of the callers matches them as a word, a keyword, a quote, a
parenthesis or whitespace. Those control characters, when the text itself
contains them, are hidden too (restored verbatim, never read as placeholders).
"""

import re
from typing import Callable, List, Tuple

# A masked string literal / identifier, as it appears in masked text.
LITERAL_PLACEHOLDER = '\x02\\d+\x03'
IDENTIFIER_PLACEHOLDER = '\x04\\d+\x05'

_PLACEHOLDER_RE = re.compile('[\x02\x04\x06](\\d+)[\x03\x05\x07]')

# One quoted run per match, scanned by the regex engine (a Python loop per
# character cost ~0.1 s per MB of subset).
_QUOTED_RE = re.compile(
    r"""'(?:[^'\\]+|\\(?:.|\Z)|'')*(?:'|\Z)"""          # 'literal', '' and \' escapes
    r'''|"(?:[^"]+|"")*(?:"|\Z)'''                      # "identifier"
    r"""|\$(?P<tag>(?:[A-Za-z_]\w*)?)\$(?:.*?\$(?P=tag)\$|.*\Z)"""  # $$dollar quoted$$
    r"""|--[^\n]*\n?"""                                  # -- comment
    r"""|/\*(?:.*?\*/|.*\Z)"""                           # /* comment */
    r"""|[\x02-\x07]+""",                                # the placeholders' own characters
    re.DOTALL,
)
_MASKED_CHARS = ("'", '"', '$', '-', '/', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07')


def mask_quoted(text: str) -> Tuple[str, List[str]]:
    """Replace string literals, identifiers and comments by placeholders.

    Args:
        text: SQL or QGIS expression text.

    Returns:
        Tuple of (masked text, quoted parts); :func:`unmask_quoted` restores.
    """
    if not text or not any(char in text for char in _MASKED_CHARS):
        return text, []
    parts: List[str] = []

    def _hide(match):
        quoted = match.group()
        first = quoted[0]
        if first in ("'", '$'):
            opening, closing = '\x02', '\x03'
        elif first == '"':
            opening, closing = '\x04', '\x05'
        else:  # comment, stray control characters
            opening, closing = '\x06', '\x07'
        parts.append(quoted)
        return f'{opening}{len(parts) - 1}{closing}'

    return _QUOTED_RE.sub(_hide, text), parts


def unmask_quoted(masked: str, parts: List[str]) -> str:
    """Put back the quoted parts hidden by :func:`mask_quoted`."""
    if not parts:
        return masked
    return _PLACEHOLDER_RE.sub(lambda m: parts[int(m.group(1))], masked)


def map_outside_quotes(text: str, transform: Callable[[str], str]) -> str:
    """Apply ``transform`` to ``text`` with its quoted parts hidden.

    ``transform`` must keep the placeholders it is given (it may move or
    drop them, never edit them).
    """
    if not text:
        return text
    masked, parts = mask_quoted(text)
    return unmask_quoted(transform(masked), parts)


_COMPARISON_RE = re.compile(r'[=<>~@]|&&|\b(?:IN|LIKE|ILIKE|IS|BETWEEN|NOT|AND|OR|SIMILAR)\b', re.IGNORECASE)


def has_comparison_operator(expression: str) -> bool:
    """Whether ``expression`` holds a comparison / boolean operator outside quotes.

    2026-10-17: the callers tested ``'IN' in expression.upper()``, so
    ``"importance"``, ``"origine"`` or ``"ordre"`` (IN, OR in the name) passed
    for filters and ``( old ) AND ( "importance" )`` reached the provider.
    """
    masked, _ = mask_quoted(expression or '')
    return bool(_COMPARISON_RE.search(masked))


def qgis_literals_to_sql(parts: List[str]) -> List[str]:
    """QGIS string literals of ``parts`` written as SQL ones: ``\\'`` -> ``''``, ``\\\\`` -> ``\\``.

    For the QGIS -> SQL converters only (a QGIS expression may escape a quote
    with a backslash; SQL standard strings cannot).
    """
    def _convert(part):
        if not part.startswith("'") or '\\' not in part:
            return part
        return re.sub(r"\\(['\\])", lambda m: "''" if m.group(1) == "'" else '\\', part)

    return [_convert(part) for part in parts]


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
