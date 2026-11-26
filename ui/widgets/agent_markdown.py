# -*- coding: utf-8 -*-
"""What a model writes in Markdown, as the rich text of a QLabel whose only markup is ours (2026-11-24).

The text of a model is not trusted: every character of it is escaped, and only the marks read here become tags of
our own. Links to project layers use stable ids, and web links open only after a click. No other URI scheme
becomes a link. Plain layer names are linked only when they identify one layer unambiguously.

Pure Python, no Qt: the thread gives the colors and the names.
"""
from __future__ import annotations

import functools
import html
import re
import os
from collections import Counter
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import quote, unquote, urlsplit
from urllib.request import url2pathname

LAYER_SCHEME = "layer:"
LAYER_ID = "layer:id/"
OUTPUT_ID = "output:id/"
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
_CODE = re.compile(r"`([^`\n]{1,500})`")
_WEB = re.compile(r'https?://[^\s<>"`]+', re.IGNORECASE)
# One pass over a line, the marks bounded in length: an opener without its closer is given up after MARK_SPAN
# characters, so a long line costs its length times MARK_SPAN at most (unbounded, ``"*.shp **ok** " * 500`` took
# seconds of the main thread, 2026-11-24 review).
MARK_SPAN = 300
_MARKS = re.compile(
    r"\[(?P<text>[^\]\n]{1,%(n)d})\]\((?P<url><[^>\n]{1,%(n)d}>|[^)\s]{1,%(n)d})\)"
    # Bold is ** only: __init__ or __main__ is a name a model writes, not bold.
    r"|(?<![\w*])\*\*(?=\S)(?P<strong>.{1,%(n)d}?)(?<=\S)\*\*(?![\w*])"
    r"|(?<![\w*])\*(?=[^\s*])(?P<em1>.{1,%(n)d}?)(?<=[^\s*])\*(?![\w*])"
    r"|(?<![\w_])_(?=[^\s_])(?P<em2>.{1,%(n)d}?)(?<=[^\s_])_(?![\w_])" % {"n": MARK_SPAN})
MAX_DEPTH = 2  # a mark inside a mark is drawn; deeper, the text is plain (no recursion on a hostile line)
MAX_COLUMNS = 3  # a wider table cannot wrap in the dock: its rows are written as lines "header: value"

Breakable = Callable[[str], str]


class LayerReference(NamedTuple):
    layer_id: str
    name: str
    group: str = ""


class FileReference(NamedTuple):
    path: str
    name: str
    is_dir: bool = False
    aliases: Tuple[str, ...] = ()


def output_href(path: str) -> str:
    return OUTPUT_ID + quote(path, safe='')


def file_reference(link: str, files: Sequence[FileReference]) -> Optional[FileReference]:
    """Only files and folders actually registered by the application can become local hyperlinks."""
    if link.startswith(OUTPUT_ID):
        target = unquote(link[len(OUTPUT_ID):])
        return next((file for file in files if file.path == target), None)
    if link.startswith('file:'):
        try:
            url = urlsplit(link)
        except ValueError:
            return None
        if url.query or url.fragment:
            return None
        path = '//' + url.netloc + url.path if url.netloc and url.netloc.lower() != 'localhost' else url.path
        target = os.path.normcase(os.path.normpath(url2pathname(path)))
        return next((file for file in files if os.path.normcase(os.path.normpath(file.path)) == target), None)
    folder_only = link.startswith('folder:')
    target = unquote(link.split(':', 1)[1] if link.startswith(('output:', 'folder:')) else link)
    matching = [file for file in files if (not folder_only or file.is_dir)
                and target in (file.name, file.path, *file.aliases)]
    return matching[0] if len(matching) == 1 else None


def anchor_html(target: str, shown: str, accent: str = '') -> str:
    """A trusted, already validated target and escaped label, in the theme's link style."""
    return (f'<a href="{html.escape(target, quote=True)}" style="color: {accent};'
            f' text-decoration: underline;">{shown}</a>')


def layer_href(layer_id: str) -> str:
    return LAYER_ID + quote(layer_id, safe='')


def web_url(value: str) -> str:
    """A navigable HTTP(S) URL; local files, application schemes and control characters stay plain text."""
    if not isinstance(value, str) or len(value) > 8192 or any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname or parsed.username is not None \
                or parsed.password is not None or '\\' in value:
            return ""
        parsed.port  # validate an explicitly given port
    except ValueError:
        return ""
    return value


def layer_reference(link: str, layers: Sequence[LayerReference]) -> Optional[LayerReference]:
    """Resolve only to a layer known when the link was drawn, never by the current tree order."""
    if not link.startswith(LAYER_SCHEME):
        return None
    target = unquote(link[len(LAYER_ID):] if link.startswith(LAYER_ID) else link[len(LAYER_SCHEME):])
    by_id = next((layer for layer in layers if layer.layer_id == target), None)
    if by_id is not None:
        return by_id
    if link.startswith(LAYER_ID):
        return None  # a removed id never falls back to a similarly named layer
    matching = [layer for layer in layers if layer.name.casefold() == target.casefold()]
    return matching[0] if len(matching) == 1 else None


def _link_target(text: str, match):
    """Find the outer closing parenthesis, bounded even when URL parentheses are nested."""
    target = match.group('url')
    if target.startswith('<') and target.endswith('>'):
        return target[1:-1], match.end()
    start, depth = match.start('url'), 0
    for end in range(start, min(len(text), start + MARK_SPAN + 1)):
        char = text[end]
        if char.isspace():
            break
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                return text[start:end], end + 1
            depth -= 1
    return None


def _no_break(text: str) -> str:
    return text


@functools.lru_cache(maxsize=8)
def _names_pattern(names: Tuple[str, ...]) -> Optional["re.Pattern"]:
    """The whole names, longest first, as one pattern: built once per list of layers, not at each drawing."""
    return re.compile("|".join(rf"(?<!\w){re.escape(name)}(?!\w)" for name in names), re.IGNORECASE) if names else None


class _Inline:
    """The marks inside a line: code, bold, italics, links, and the names of the layers."""

    def __init__(self, names: Sequence[str], colors: Dict[str, str], breakable: Breakable,
                 layers: Sequence[LayerReference] = (), files: Sequence[FileReference] = ()) -> None:
        self._layers = tuple(layers)
        self._files = tuple(files)
        self._rank = {}
        matching_names = {}
        self._targets = {}
        for rank, name in enumerate(names):
            if len(name.strip()) >= MIN_NAME:
                self._rank.setdefault(name.casefold(), rank)
                self._targets.setdefault(name.casefold(), f'{LAYER_SCHEME}{rank}')
                matching_names.setdefault(name.casefold(), name)
        if layers:
            self._rank.clear()
            self._targets.clear()
            counts = Counter(layer.name.casefold() for layer in layers)
            matching_names.clear()
            for rank, layer in enumerate(layers):
                name = layer.name.casefold()
                if len(layer.name.strip()) >= MIN_NAME and counts[name] == 1:
                    self._rank[name] = rank
                    self._targets[name] = LAYER_ID + quote(layer.layer_id, safe='')
                    matching_names[name] = layer.name
        file_names = {}
        for file in files:
            for name in (file.path, *file.aliases, *((file.name,) if not file.is_dir else ())):
                if len(name.strip()) >= MIN_NAME:
                    file_names.setdefault(name.casefold(), []).append(file)
        for name, matches in file_names.items():
            paths = {file.path for file in matches}
            if len(paths) == 1 and name not in self._targets:
                self._targets[name] = output_href(matches[0].path)
                matching_names[name] = name
        self._colors = colors
        self._breakable = breakable
        self._matching_names = matching_names
        self._pattern = _names_pattern(tuple(sorted(matching_names.values(), key=len, reverse=True)))

    def layer_link(self, name: str, shown: str) -> str:
        target = self._targets.get(name.casefold())
        if target is None:  # Unicode case-insensitive matches such as İ/i do not have the same casefold.
            matching = [self._targets[key] for key, value in self._matching_names.items()
                        if re.fullmatch(re.escape(value), name, re.IGNORECASE)]
            target = matching[0] if len(matching) == 1 else None
        return self._anchor(target, shown) if target else shown

    def _anchor(self, target: str, shown: str) -> str:
        return anchor_html(target, shown, self._colors.get('accent', ''))

    def _text(self, text: str) -> str:
        """Plain text: escaped, its long words breakable, the names of the layers as links."""
        out, start = [], 0
        for match in _WEB.finditer(text):
            target = match.group().rstrip('.,;:!?')
            extra = {close: target.count(close) - target.count(opening)
                     for close, opening in ((')', '('), (']', '['), ('}', '{'))}
            end = len(target)
            while end and target[end - 1] in extra and extra[target[end - 1]] > 0:
                extra[target[end - 1]] -= 1
                end -= 1
            target = target[:end]
            out.append(self._layer_text(text[start:match.start()]))
            shown = html.escape(self._breakable(target))
            out.append(self._anchor(target, shown) if web_url(target) else shown)
            start = match.start() + len(target)
        out.append(self._layer_text(text[start:]))
        return ''.join(out)

    def _layer_text(self, text: str) -> str:
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
        reference = layer_reference(LAYER_SCHEME + quote(content, safe=''), self._layers)
        if reference is not None:
            return self._anchor(LAYER_ID + quote(reference.layer_id, safe=''), shown)
        file = file_reference(content, self._files)
        if file is not None:
            return self._anchor(output_href(file.path), shown)
        return self.layer_link(content, shown) if content.casefold() in self._rank else shown

    def render(self, text: str) -> str:
        """``text`` with its marks drawn, the code first: nothing inside a code span is read as a mark."""
        out, start = [], 0
        for match in _CODE.finditer(text):
            out.append(self._marks(text[start:match.start()]))
            out.append(self._code(match.group(1)))
            start = match.end()
        out.append(self._marks(text[start:]))
        return "".join(out)

    def _marks(self, text: str, depth: int = 0) -> str:
        if not text:
            return ""
        if depth >= MAX_DEPTH:
            return self._text(text)
        out, start = [], 0
        for match in _MARKS.finditer(text):
            if match.start() < start:
                continue
            out.append(self._text(text[start:match.start()]))
            end = match.end()
            if match.group("text") is not None:
                parsed = _link_target(text, match)
                if parsed is None:
                    out.append(html.escape(self._breakable(match.group())))
                    start = end
                    continue
                target, end = parsed
                label = match.group('text')
                reference = layer_reference(target, self._layers)
                file = file_reference(target, self._files)
                if reference is not None:
                    target = LAYER_ID + quote(reference.layer_id, safe='')
                elif file is not None:
                    target = output_href(file.path)
                if reference is not None or file is not None or web_url(target):
                    # The label is escaped as a whole: never nest auto-links inside an explicit link.
                    out.append(self._anchor(target, html.escape(self._breakable(label))))
                else:
                    out.append(f"{html.escape(self._breakable(label))} ({html.escape(self._breakable(target))})")
            elif match.group("strong") is not None:
                out.append(f"<b>{self._marks(match.group('strong'), depth + 1)}</b>")
            else:
                out.append(f"<i>{self._marks(match.group('em1') or match.group('em2'), depth + 1)}</i>")
            start = end
        out.append(self._text(text[start:]))
        return "".join(out)


def _cells(row: str) -> List[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def answer_html(text: str, names: Sequence[str] = (), colors: Optional[Dict[str, str]] = None,
                breakable: Breakable = _no_break, *, layers: Sequence[LayerReference] = (),
                files: Sequence[FileReference] = ()) -> str:
    """The rich text of an answer: every character of ``text`` escaped, only its Markdown marks drawn.

    Args:
        text: What the model wrote (untrusted).
        names: The names of the layers of the project; a name of the text links to ``layer:<its rank here>``.
        layers: Stable layer ids, names and groups. When supplied, ids replace the legacy rank links.
        files: Registered output files/folders; arbitrary local paths in model text stay plain.
        colors: ``accent`` (the links), ``code_bg`` (code), ``rule`` (the lines of a table).
        breakable: Gives a long word places to wrap (the thread's ``breakable``), applied before escaping.
    """
    colors = dict(colors or {})
    inline = _Inline(list(names), colors, breakable, layers, files)
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: List[str] = []
    paragraph: List[str] = []
    items: List[str] = []
    list_tag = ""
    list_start = 1

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(_P + "<br/>".join(inline.render(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag, list_start
        if items:
            start = f' start="{list_start}"' if list_tag == "ol" and list_start != 1 else ""
            blocks.append(f'<{list_tag}{start} style="margin-top: 0px; margin-bottom: 6px; -qt-list-indent: 1;">'
                          + "".join(f"<li>{item}</li>" for item in items) + f"</{list_tag}>")
            items.clear()
        list_tag, list_start = "", 1

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
            width = max([len(header)] + [len(row) for row in rows])
            header = header + [""] * (width - len(header))  # a cell past the header is kept, not dropped
            rows = [row + [""] * (width - len(row)) for row in rows]
            if width > MAX_COLUMNS:  # too wide for the dock: one line per row, "header: value", that wraps
                for row in rows:
                    items.append(" · ".join(f"<b>{inline.render(name)}</b> {inline.render(value)}" if name
                                            else inline.render(value) for name, value in zip(header, row) if value))
                list_tag, list_start = "ul", 1
                flush_list()
                continue
            rule = colors.get("rule", "")
            cell = f'style="padding: 2px 8px 2px 0px; border-bottom: 1px solid {rule};"'
            head = "".join(f"<th align=\"left\" {cell}>{inline.render(value)}</th>" for value in header)
            body = "".join("<tr>" + "".join(f"<td {cell}>{inline.render(value)}</td>" for value in row) + "</tr>"
                           for row in rows)
            blocks.append(f'<table cellspacing="0" cellpadding="0" style="border-collapse: collapse; margin-bottom: 6px;">'
                          f"<tr>{head}</tr>{body}</table>")
            continue
        heading = _HEADING.match(line)
        bullet = _BULLET.match(line) if not _RULE.match(line) else None
        numbered = _NUMBERED.match(line)
        if not line.strip():
            flush_paragraph()
            following = next((later for later in lines[index + 1:] if later.strip()), "")
            # A list written with blank lines between its items stays one list (numbered on).
            if not (items and (_BULLET.match(following) or _NUMBERED.match(following)
                               or following.startswith((" ", "\t")))):
                flush_list()
        elif _RULE.match(line):
            flush()
            blocks.append("<hr/>")
        elif heading:
            flush()
            blocks.append(f"{_P}<b>{inline.render(heading.group(1))}</b></p>")
        elif bullet or numbered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            if not items and numbered:
                list_start = int(numbered.group(1))  # "3. x" alone is numbered 3
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
