# -*- coding: utf-8 -*-
"""What a model writes in Markdown, as the rich text of a QLabel whose only markup is ours (2026-11-24).

The text of a model is not trusted: every character of it is escaped, and only the marks read here become tags of
our own. Links to project layers use stable ids, and web links open only after a click. No other URI scheme
becomes a link. Plain layer names are linked only when they identify one layer unambiguously.

Pure Python, no Qt: the thread gives the colors and the names.
"""
from __future__ import annotations

import functools
import heapq
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

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST = re.compile(r"^( *)(?:([-*+])|(\d{1,4})[.)])([ \t]+)(.*)$")
_QUOTE = re.compile(r"^ {0,3}>[ \t]?(.*)$")
_TASK = re.compile(r"^\[([ xX])\]\s+(.*)$")
_TABLE_RULE = re.compile(r":?-{2,}:?")
_RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_CODE = re.compile(r"(?<!`)(`{1,8})(?!`)([^\n]{1,2000}?)(?<!`)\1(?!`)")
_WEB = re.compile(r'https?://[^\s<>"`]+', re.IGNORECASE)
# One pass over a line, the marks bounded in length: an opener without its closer is given up after MARK_SPAN
# characters, so a long line costs its length times MARK_SPAN at most (unbounded, ``"*.shp **ok** " * 500`` took
# seconds of the main thread, 2026-11-24 review).
MARK_SPAN = 300
_LINK_SOURCE = (r"\[(?P<text>[^\]\n]{1,%(n)d})\]\((?P<url><[^>\n]{1,%(n)d}>|[^)\s]{1,%(n)d})\)"
                % {"n": MARK_SPAN})
_LINK = re.compile(_LINK_SOURCE)
_MARKS = re.compile(
    _LINK_SOURCE +
    # Bold is ** only: __init__ or __main__ is a name a model writes, not bold.
    r"|(?<![\w*])\*\*(?=\S)(?P<strong>.{1,%(n)d}?)(?<=\S)\*\*(?![\w*])"
    r"|(?<![\w*])\*(?=[^\s*])(?P<em1>.{1,%(n)d}?)(?<=[^\s*])\*(?![\w*])"
    r"|(?<![\w_])_(?=[^\s_])(?P<em2>.{1,%(n)d}?)(?<=[^\s_])_(?![\w_])"
    r"|(?<!~)~~(?=\S)(?P<strike>.{1,%(n)d}?)(?<=\S)~~(?!~)" % {"n": MARK_SPAN})
MAX_DEPTH = 2  # a mark inside a mark is drawn; deeper, the text is plain (no recursion on a hostile line)
MAX_COLUMNS = 8
MAX_BLOCK_DEPTH = 6
MIN_COLUMN_WIDTH = 88

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
                 layers: Sequence[LayerReference] = (), files: Sequence[FileReference] = (),
                 allow_links: bool = True) -> None:
        self._allow_links = allow_links
        self._label_inline = None
        self._names = tuple(names)
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
        if not self._allow_links:
            return html.escape(self._breakable(text))
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
        if not self._allow_links:
            return shown
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
        for match in heapq.merge(_CODE.finditer(text), _LINK.finditer(text), key=lambda found: found.start()):
            if match.start() < start:
                continue
            out.append(self._marks(text[start:match.start()]))
            if match.re is _LINK:
                parsed = _link_target(text, match)
                end = parsed[1] if parsed else match.end()
                out.append(self._marks(text[match.start():end]))
                start = end
                continue
            code = match.group(2)
            if code.startswith(' ') and code.endswith(' ') and code.strip():
                code = code[1:-1]
            out.append(self._code(code))
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
                if self._allow_links and (reference is not None or file is not None or web_url(target)):
                    if self._label_inline is None:
                        self._label_inline = _Inline((), self._colors, self._breakable, allow_links=False)
                    out.append(self._anchor(target, self._label_inline.render(label)))
                else:
                    out.append(f"{html.escape(self._breakable(label))} ({html.escape(self._breakable(target))})")
            elif match.group("strong") is not None:
                out.append(f"<b>{self._marks(match.group('strong'), depth + 1)}</b>")
            elif match.group('strike') is not None:
                out.append(f"<s>{self._marks(match.group('strike'), depth + 1)}</s>")
            else:
                out.append(f"<i>{self._marks(match.group('em1') or match.group('em2'), depth + 1)}</i>")
            start = end
        out.append(self._text(text[start:]))
        return "".join(out)


def _cells(row: str) -> List[str]:
    """Split table cells, preserving escaped pipes and pipes inside matching code spans."""
    row = row.strip()
    cells, content = [], []
    ticks = 0
    last_separator = -1
    index = 0
    while index < len(row):
        char = row[index]
        if char == '\\':
            end = index
            while end < len(row) and row[end] == '\\':
                end += 1
            count = end - index
            if end < len(row) and row[end] == '|' and count % 2:
                content.append('\\' * (count - 1) + '|')
                index = end + 1
                continue
            content.append(row[index:end])
            index = end
            continue
        if char == '`':
            end = index + 1
            while end < len(row) and row[end] == '`':
                end += 1
            length = end - index
            if not ticks:
                ticks = length
            elif ticks == length:
                ticks = 0
            content.append(row[index:end])
            index = end
            continue
        if char == '|' and not ticks:
            cells.append(''.join(content).strip())
            content.clear()
            last_separator = index
        else:
            content.append(char)
        index += 1
    cells.append(''.join(content).strip())
    if row.startswith('|'):
        cells.pop(0)
    if last_separator == len(row) - 1 and cells and not cells[-1]:
        cells.pop()
    return [cell.strip() for cell in cells]


def table_columns(width: Optional[int] = None) -> int:
    """How many columns fit without making the conversation wider than its viewport."""
    return MAX_COLUMNS if width is None else max(1, min(MAX_COLUMNS, width // MIN_COLUMN_WIDTH))


def _expand_indent(line: str) -> str:
    prefix = len(line) - len(line.lstrip(' \t'))
    return line[:prefix].expandtabs(4) + line[prefix:]


def _table_header(line: str, rule: str):
    if '|' not in line or '|' not in rule:
        return None
    header, cells = _cells(line), _cells(rule)
    if len(header) != len(cells) or not cells or not all(_TABLE_RULE.fullmatch(cell) for cell in cells):
        return None
    align = ['center' if cell.startswith(':') and cell.endswith(':') else
             'right' if cell.endswith(':') else 'left' for cell in cells]
    return header, align


class _Blocks:
    def __init__(self, inline: _Inline, colors: Dict[str, str], width: Optional[int]) -> None:
        self.inline, self.colors, self.width = inline, colors, width

    def _code(self, lines: List[str], language: str = '') -> str:
        label = ''
        if language:
            label = ('<p style="margin-top: 4px; margin-bottom: 2px; font-size: 10px; color: '
                     + self.colors.get('muted', '') + ';">' + html.escape(language[:32]) + '</p>')
        return (label + '<pre style="margin-top: 0px; margin-bottom: 8px; font-family: monospace; '
                'white-space: pre-wrap; background-color: ' + self.colors.get('code_bg', '') + ';">'
                + html.escape(self.inline._breakable('\n'.join(lines))) + '</pre>')

    def _table(self, header: List[str], align: List[str], rows: List[List[str]]) -> str:
        columns = max([len(header)] + [len(row) for row in rows])
        header += [''] * (columns - len(header))
        align += ['left'] * (columns - len(align))
        rows = [row + [''] * (columns - len(row)) for row in rows]
        stacked = columns > table_columns(self.width)
        cell_width = (self.width or MIN_COLUMN_WIDTH * columns) // (2 if stacked else columns)
        chunk = max(4, min(18, cell_width // 10 - 1)) if self.width is not None else 24
        # A long path must wrap inside its cell, rather than setting the minimum width of the whole table.
        def wrap(text):
            return re.sub(r'[^\s\u200b]{' + str(chunk + 1) + r',}',
                          lambda match: '\u200b'.join(match[0][at:at + chunk]
                                                     for at in range(0, len(match[0]), chunk)),
                          self.inline._breakable(text))
        cells = _Inline(self.inline._names, self.colors, wrap, self.inline._layers, self.inline._files)
        rule = self.colors.get('rule', '')
        border = f'style="border-bottom: 1px solid {rule};"'
        opening = ('<table width="100%" cellspacing="0" cellpadding="5" '
                   'style="border-collapse: collapse; margin-top: 2px; margin-bottom: 10px;">')
        background = self.colors.get('table_header', self.colors.get('code_bg', ''))
        if stacked:
            cards = []
            for row in rows or [[''] * columns]:
                content = ''.join((f'<tr bgcolor="{background}">' if index == 0 else '<tr>')
                                  + f'<th width="32%" align="left" {border}>{cells.render(name)}</th>'
                                  f'<td align="{alignment}" {border}>{cells.render(value)}</td></tr>'
                                  for index, (name, value, alignment) in enumerate(zip(header, row, align))
                                  if name or value)
                cards.append(opening + content + '</table>')
            return ''.join(cards)
        head = ''.join(f'<th align="{alignment}" {border}>{cells.render(value)}</th>'
                       for value, alignment in zip(header, align))
        body = []
        for index, row in enumerate(rows):
            alternate = self.colors.get('table_alt', self.colors.get('code_bg', '')) if index % 2 else ''
            shade = f' bgcolor="{alternate}"' if alternate else ''
            body.append('<tr' + shade + '>' + ''.join(
                f'<td align="{alignment}" {border}>{cells.render(value)}</td>'
                for value, alignment in zip(row, align)) + '</tr>')
        return opening + f'<tr bgcolor="{background}">{head}</tr>' + ''.join(body) + '</table>'

    def _list(self, lines: List[str], start: int, depth: int):
        first = _LIST.match(_expand_indent(lines[start]))
        indent = len(first[1])
        tag = 'ul' if first[2] else 'ol'
        number = int(first[3]) if first[3] else 1
        index, items, tasks = start, [], []
        while index < len(lines):
            match = _LIST.match(_expand_indent(lines[index]))
            if not match or len(match[1]) != indent or ('ul' if match[2] else 'ol') != tag:
                break
            content_indent = match.start(5)
            task = _TASK.match(match[5]) if tag == 'ul' else None
            text = match[5]
            if task:
                text = ('☑ ' if task[1].lower() == 'x' else '☐ ') + task[2]
            tasks.append(bool(task))
            body = [text]
            index += 1
            while index < len(lines):
                line = _expand_indent(lines[index])
                if not line.strip():
                    following = index + 1
                    while following < len(lines) and not lines[following].strip():
                        following += 1
                    if following == len(lines):
                        index = following
                        break
                    later = _expand_indent(lines[following])
                    if len(later) - len(later.lstrip()) <= indent:
                        next_item = _LIST.match(later)
                        if next_item and len(next_item[1]) == indent:
                            index = following
                        break
                    body.append('')
                    index = following
                    continue
                spaces = len(line) - len(line.lstrip(' '))
                if spaces <= indent:
                    break
                body.append(line[min(spaces, content_indent):])
                index += 1
            rendered = self.render(body, depth + 1)
            if rendered.startswith(_P):
                end = rendered.find('</p>')
                rendered = rendered[len(_P):end] + rendered[end + 4:]
            items.append('<li>' + rendered + '</li>')
        first_number = f' start="{number}"' if tag == 'ol' and number != 1 else ''
        bullets = ' list-style-type: none;' if all(tasks) else ''
        return (f'<{tag}{first_number} style="margin-top: 0px; margin-bottom: 6px; '
                f'-qt-list-indent: {depth + 1};{bullets}">' + ''.join(items) + f'</{tag}>', index)

    def render(self, lines: List[str], depth: int = 0) -> str:
        if depth >= MAX_BLOCK_DEPTH:
            return _P + '<br/>'.join(self.inline.render(line) for line in lines) + '</p>'
        blocks, paragraph = [], []

        def flush():
            if paragraph:
                blocks.append(_P + '<br/>'.join(self.inline.render(line) for line in paragraph) + '</p>')
                paragraph.clear()

        index = 0
        while index < len(lines):
            raw = lines[index]
            line = _expand_indent(raw)
            fence = _FENCE.match(line)
            if fence and not (fence[1][0] == '`' and '`' in fence[2]):
                flush()
                marker, length = fence[1][0], len(fence[1])
                code = []
                index += 1
                while index < len(lines):
                    closing = _expand_indent(lines[index])
                    stripped = closing.lstrip(' ')
                    run = len(stripped) - len(stripped.lstrip(marker))
                    if len(closing) - len(stripped) <= 3 and run >= length and not stripped[run:].strip():
                        index += 1
                        break
                    code.append(lines[index])
                    index += 1
                language = fence[2].strip().split()[0] if fence[2].strip() else ''
                blocks.append(self._code(code, language))
                continue
            if _LIST.match(line) and not _RULE.match(line):
                flush()
                listed, index = self._list(lines, index, depth)
                blocks.append(listed)
                continue
            table = _table_header(line, lines[index + 1]) if index + 1 < len(lines) else None
            if table:
                flush()
                header, align = table
                rows = []
                index += 2
                while index < len(lines) and lines[index].strip():
                    row = _expand_indent(lines[index])
                    if any(pattern.match(row) for pattern in (_FENCE, _HEADING, _QUOTE, _LIST, _RULE)):
                        break
                    rows.append(_cells(lines[index]))
                    index += 1
                blocks.append(self._table(header, align, rows))
                continue
            quote = _QUOTE.match(line)
            if quote:
                flush()
                quoted = []
                while index < len(lines):
                    quote = _QUOTE.match(_expand_indent(lines[index]))
                    if not quote:
                        break
                    quoted.append(quote[1])
                    index += 1
                blocks.append('<blockquote style="margin-top: 2px; margin-bottom: 8px; margin-left: 12px; '
                              'margin-right: 0px; color: ' + self.colors.get('muted', '') + ';">'
                              + self.render(quoted, depth + 1) + '</blockquote>')
                continue
            if _RULE.match(line):
                flush()
                blocks.append('<hr/>')
            elif _HEADING.match(line):
                flush()
                heading = _HEADING.match(line)
                size = (18, 16, 14, 13, 13, 13)[len(heading[1]) - 1]
                blocks.append(f'<p style="margin-top: 8px; margin-bottom: 6px; font-size: {size}px;">'
                              f'<b>{self.inline.render(heading[2])}</b></p>')
            elif line.startswith('    ') and not paragraph:
                code = []
                while index < len(lines):
                    indented = _expand_indent(lines[index])
                    if indented.strip() and not indented.startswith('    '):
                        break
                    code.append(indented[4:] if indented.strip() else '')
                    index += 1
                blocks.append(self._code(code))
                continue
            elif not line.strip():
                flush()
            else:
                paragraph.append(raw)
            index += 1
        flush()
        return ''.join(blocks)


def answer_html(text: str, names: Sequence[str] = (), colors: Optional[Dict[str, str]] = None,
                breakable: Breakable = _no_break, *, layers: Sequence[LayerReference] = (),
                files: Sequence[FileReference] = (), width: Optional[int] = None) -> str:
    """Escaped Markdown for Qt rich text, with tables adapted to the available width in pixels.

    Layer and output targets are supplied by the application. Only validated links become anchors;
    nested lists/quotes are bounded and code never interprets markup or fetches resources.
    """
    colors = dict(colors or {})
    inline = _Inline(list(names), colors, breakable, layers, files)
    return _Blocks(inline, colors, width).render(text.replace('\r\n', '\n').replace('\r', '\n').split('\n'))


def layer_of_link(link: str, names: Sequence[str]) -> str:
    """The name a ``layer:<rank>`` link of ``answer_html`` stands for, given the same ``names``; "" otherwise."""
    if not link.startswith(LAYER_SCHEME):
        return ""
    try:
        rank = int(link[len(LAYER_SCHEME):])
    except ValueError:
        return ""
    return names[rank] if 0 <= rank < len(names) else ""
