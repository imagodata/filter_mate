# -*- coding: utf-8 -*-
"""Bounding box of a linear WKT geometry, without a geometry library.

A conservative reader: it answers only for well-formed POINT, LINESTRING,
POLYGON, their MULTI forms and GEOMETRYCOLLECTION of those (with Z, M or ZM),
and then gives what ``QgsGeometry.fromWkt(wkt).boundingBox()`` gives (checked
against QGIS 3.44 and 4.3 in tests/unit/core/domain/test_wkt_bounds.py).
Anything else (curves, whose box follows the arcs, EMPTY parts, EWKT, NaN or
infinite numbers, malformed text) answers None: the box feeds an R-tree
prefilter, and a box too small would drop features.
"""
import math
import re
from typing import List, Optional, Tuple

# Nesting of the coordinate lists: POINT (1 2), POLYGON ((...), (...)), ...
_LEVELS = {'POINT': 1, 'LINESTRING': 1, 'POLYGON': 2, 'MULTIPOINT': 2, 'MULTILINESTRING': 2, 'MULTIPOLYGON': 3}
_DIMENSIONS = frozenset(('Z', 'M', 'ZM'))
# ASCII only: QGIS and SpatiaLite read neither Unicode digits nor non-ASCII spaces.
_TOKEN = re.compile(r'\s*(?:([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)|([A-Za-z]+)|([(),]))', re.ASCII)


class _Unanswered(Exception):
    """The text is outside what this reader answers for."""


def _tokens(text: str) -> List[Tuple[str, object]]:
    tokens, position = [], 0
    text = text.rstrip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            raise _Unanswered()
        number, word, sep = match.groups()
        if number is not None:
            follower = text[match.end():match.end() + 1]
            if follower and (follower.isalnum() or follower == '.'):
                raise _Unanswered()  # 1.2.3, 1e5.5, 12abc: not one number
            value = float(number)
            if not math.isfinite(value):
                raise _Unanswered()
            tokens.append(('num', value))
        elif word is not None:
            tokens.append(('word', word.upper()))
        else:
            tokens.append(('sep', sep))
        position = match.end()
    return tokens


class _Reader:
    def __init__(self, tokens):
        self.tokens, self.i = tokens, 0
        self.xs: List[float] = []
        self.ys: List[float] = []

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def take(self, kind, value=None):
        token = self.peek()
        if token[0] != kind or (value is not None and token[1] != value):
            raise _Unanswered()
        self.i += 1
        return token[1]

    def coordinate(self):
        values = []
        while self.peek()[0] == 'num':
            values.append(self.take('num'))
        if not 2 <= len(values) <= 4:
            raise _Unanswered()
        self.xs.append(values[0])
        self.ys.append(values[1])

    def coordinate_list(self, level):
        self.take('sep', '(')
        while True:
            if level == 1:
                self.coordinate()
            else:
                self.coordinate_list(level - 1)
            if self.peek() == ('sep', ','):
                self.i += 1
                continue
            self.take('sep', ')')
            return

    def geometry(self):
        kind = self.take('word')
        if self.peek()[0] == 'word' and self.peek()[1] in _DIMENSIONS:
            self.i += 1
        if kind == 'GEOMETRYCOLLECTION':
            self.take('sep', '(')
            while True:
                self.geometry()
                if self.peek() == ('sep', ','):
                    self.i += 1
                    continue
                self.take('sep', ')')
                return
        if kind not in _LEVELS:
            raise _Unanswered()  # EMPTY, curves, surfaces, EWKT...
        level = _LEVELS[kind]
        if kind == 'MULTIPOINT' and self.tokens[self.i + 1:self.i + 2] != [('sep', '(')]:
            level = 1  # MULTIPOINT (1 2, 3 4)
        self.coordinate_list(level)


def wkt_bounds(wkt) -> Optional[Tuple[float, float, float, float]]:
    """``(xmin, ymin, xmax, ymax)`` of a linear WKT geometry, None when not answered (see module)."""
    if not isinstance(wkt, str) or not wkt.strip():
        return None
    try:
        reader = _Reader(_tokens(wkt))
        reader.geometry()
        if reader.i != len(reader.tokens):
            return None  # text after the geometry
    except (_Unanswered, IndexError, RecursionError):
        return None
    return (min(reader.xs), min(reader.ys), max(reader.xs), max(reader.ys))


__all__ = ['wkt_bounds']
