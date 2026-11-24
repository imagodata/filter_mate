# -*- coding: utf-8 -*-
"""What a model writes in Markdown, as the rich text of a QLabel whose only markup is ours (2026-11-24).

The text of a model is not trusted: every character of it is escaped, and only the marks read here become tags of
our own. Bold, italics, code, headings, lists, simple tables and fenced code are drawn; a link ``[text](url)``
shows its text and its address, never as something to click (a model must not lead the user to a page). The names of
the layers of the project become links ``layer:<rank>`` the thread turns into a click on that layer.

Pure Python, no Qt: the thread gives the colors and the names.
"""
from __future__ import annotations

import html
import re
from typing import Callable, Dict, List, Optional, Sequence

LAYER_SCHEME = "layer:"
MIN_NAME = 3  # a shorter layer name ("a", "zo") would link every word that happens to be it
# Qt gives a paragraph 12 px above and below: the thread spaces its items itself.
_P = '<p style="margin-top: 0px; margin-bottom: 6px;">'

_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d{1,4})[.)]\s+(.*)$")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_CODE = re.compile(r"`([^`\n]+)`")
_STRONG = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
_EMPHASIS = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])|(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])")
_LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")

Breakable = Callable[[str], str]


def _no_break(text: str) -> str:
    return text


class _Inline:
    """The marks inside a line: code, bold, italics, links, and the names of the layers."""

    def __init__(self, names: Sequence[str], colors: Dict[str, str], breakable: Breakable) -> None:
        self._rank = {name: rank for rank, name in enumerate(names) if len(name.strip()) >= MIN_NAME}
        self._names = sorted(self._rank, key=len, reverse=True)
        self._colors = colors
        self._breakable = breakable
        self._pattern = (re.compile("|".join(rf"(?<!\w){re.escape(name)}(?!\w)" for name in self._names))
                         if self._names else None)

    def layer_link(self, name: str, shown: str) -> str:
        return (f'<a href="{LAYER_SCHEME}{self._rank[name]}" style="color: {self._colors.get("accent", "")};'
                f' text-decoration: none;">{shown}</a>')

    def _text(self, text: str) -> str:
        """Plain text: escaped, its long words breakable, the names of the layers as links."""
        if self._pattern is None:
            return html.escape(self._breakable(text))
        out, start = [], 0
        for match in self._pattern.finditer(text):
            out.append(html.escape(self._breakable(text[start:match.start()])))
            out.append(self.layer_link(match.group(0), html.escape(self._breakable(match.group(0)))))
            start = match.end()
        out.append(html.escape(self._breakable(text[start:])))
        return "".join(out)

    def _code(self, content: str) -> str:
        shown = (f'<span style="font-family: monospace; background-color: {self._colors.get("code_bg", "")};">'
                 f"{html.escape(self._breakable(content))}</span>")
        return self.layer_link(content, shown) if content in self._rank else shown

    def render(self, text: str) -> str:
        """``text`` with its marks drawn, the code first: nothing inside a code span is read as a mark."""
        out, start = [], 0
        for match in _CODE.finditer(text):
            out.append(self._marks(text[start:match.start()]))
            out.append(self._code(match.group(1)))
            start = match.end()
        out.append(self._marks(text[start:]))
        return "".join(out)

    def _marks(self, text: str) -> str:
        if not text:
            return ""
        found = []
        for pattern in (_LINK, _STRONG, _EMPHASIS):
            match = pattern.search(text)
            if match is not None:
                found.append((match.start(), pattern, match))
        if not found:
            return self._text(text)
        _start, pattern, match = min(found, key=lambda entry: entry[0])
        before, after = text[:match.start()], text[match.end():]
        if pattern is _LINK:
            # The text and its address, side by side, both as text: nothing a model writes is clicked through.
            inner = f"{self._marks(match.group(1))} ({self._text(match.group(2))})"
        elif pattern is _STRONG:
            inner = f"<b>{self._marks(match.group(2))}</b>"
        else:
            inner = f"<i>{self._marks(match.group(1) or match.group(2))}</i>"
        return self._text(before) + inner + self._marks(after)


def _cells(row: str) -> List[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def answer_html(text: str, names: Sequence[str] = (), colors: Optional[Dict[str, str]] = None,
                breakable: Breakable = _no_break) -> str:
    """The rich text of an answer: every character of ``text`` escaped, only its Markdown marks drawn.

    Args:
        text: What the model wrote (untrusted).
        names: The names of the layers of the project; a name of the text links to ``layer:<its rank here>``.
        colors: ``accent`` (the links), ``code_bg`` (code), ``rule`` (the lines of a table).
        breakable: Gives a long word places to wrap (the thread's ``breakable``), applied before escaping.
    """
    colors = dict(colors or {})
    inline = _Inline(list(names), colors, breakable)
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: List[str] = []
    paragraph: List[str] = []
    items: List[str] = []
    list_tag = ""

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(_P + "<br/>".join(inline.render(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if items:
            blocks.append(f'<{list_tag} style="margin-top: 0px; margin-bottom: 6px; -qt-list-indent: 1;">'
                          + "".join(f"<li>{item}</li>" for item in items) + f"</{list_tag}>")
            items.clear()
        list_tag = ""

    def flush() -> None:
        flush_paragraph()
        flush_list()

    index = 0
    while index < len(lines):
        line = lines[index]
        if _FENCE.match(line):
            flush()
            code = []
            index += 1
            while index < len(lines) and not _FENCE.match(lines[index]):
                code.append(lines[index])
                index += 1
            index += 1  # the closing fence (or the end)
            blocks.append(f'<p style="margin-top: 0px; margin-bottom: 6px; font-family: monospace; white-space:'
                          f' pre-wrap; background-color: {colors.get("code_bg", "")};">{html.escape(breakable(chr(10).join(code)))}</p>')
            continue
        if (_TABLE_ROW.match(line) and index + 1 < len(lines) and _TABLE_RULE.match(lines[index + 1])
                and "|" in lines[index + 1]):
            flush()
            header = _cells(line)
            index += 2
            rows = []
            while index < len(lines) and _TABLE_ROW.match(lines[index]):
                rows.append(_cells(lines[index]))
                index += 1
            rule = colors.get("rule", "")
            cell = f'style="padding: 2px 8px 2px 0px; border-bottom: 1px solid {rule};"'
            head = "".join(f"<th align=\"left\" {cell}>{inline.render(value)}</th>" for value in header)
            body = "".join("<tr>" + "".join(f"<td {cell}>{inline.render(value)}</td>"
                                            for value in (row + [""] * (len(header) - len(row)))[:len(header)])
                           + "</tr>" for row in rows)
            blocks.append(f'<table cellspacing="0" cellpadding="0" style="border-collapse: collapse; margin-bottom: 6px;">'
                          f"<tr>{head}</tr>{body}</table>")
            continue
        heading = _HEADING.match(line)
        bullet = _BULLET.match(line) if not _RULE.match(line) else None
        numbered = _NUMBERED.match(line)
        if not line.strip():
            flush()
        elif _RULE.match(line):
            flush()
        elif heading:
            flush()
            blocks.append(f"{_P}<b>{inline.render(heading.group(1))}</b></p>")
        elif bullet or numbered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            items.append(inline.render(bullet.group(1) if bullet else numbered.group(2)))
        elif items and line.startswith((" ", "\t")):
            items[-1] += "<br/>" + inline.render(line.strip())  # the next line of the same item
        else:
            flush_list()
            paragraph.append(line)
        index += 1
    flush()
    return "".join(blocks)


def layer_of_link(link: str, names: Sequence[str]) -> str:
    """The name a ``layer:<rank>`` link of ``answer_html`` stands for, given the same ``names``; "" otherwise."""
    if not link.startswith(LAYER_SCHEME):
        return ""
    try:
        rank = int(link[len(LAYER_SCHEME):])
    except ValueError:
        return ""
    return names[rank] if 0 <= rank < len(names) else ""
