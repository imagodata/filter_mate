# -*- coding: utf-8 -*-
"""Put in i18n/*.ts the strings the plugin translates through a helper, under the context it looks them up in.

pylupdate5 only understands ``self.tr("...")`` and ``translate("Context", "...")``. Three call forms of
the plugin escape it:

- a module helper ``def _tr(text): return QCoreApplication.translate('ServerFilterTranslation', text)``
  called as ``_tr("...")`` (or imported under another name): the string is not extracted at all;
- the same helper named ``tr``: the string is filed under ``@default``;
- ``dw.tr("...")`` / ``self._dockwidget.tr("...")``: the string is filed under the receiver's text
  (``dw``), while PyQt looks it up under the class of the dock, ``FilterMateDockWidget``.

This script reads the sources of FilterMate.pro with ``ast``, files every such string under its
runtime context (taking back the translation an obsolete message of that context still holds) and
removes the misfiled copies. pylupdate5 marks these messages obsolete again on its next run, as it
cannot see them: run this script after it, every time::

    pylupdate5 FilterMate.pro   (in i18n/)
    python3 scripts/i18n_processing_context.py i18n/FilterMate_*.ts
    python3 scripts/i18n_runtime_contexts.py i18n/FilterMate_*.ts
"""
import ast
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n_processing_context import _context, write_ts  # noqa: E402

DOCK_CONTEXT = 'FilterMateDockWidget'
# Receivers of ``.tr()`` that are the dock widget: pylupdate5 names the context after the receiver text.
RECEIVERS = {'dw': DOCK_CONTEXT, 'self._dockwidget': DOCK_CONTEXT, 'self.dockwidget': DOCK_CONTEXT}
# Contexts pylupdate5 makes up for these calls: their copies of a collected string are removed.
MISFILED = {'@default'} | set(RECEIVERS)
OBSOLETE = ('obsolete', 'vanished')


def _sources(pro_path):
    with open(pro_path, encoding='utf-8') as handle:
        text = handle.read()
    block = text.split('SOURCES', 1)[1].split('TRANSLATIONS', 1)[0]
    return re.findall(r'\.\./[^\s\\]+\.py', block)


def _parse(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return ast.parse(handle.read(), path)
    except (OSError, SyntaxError) as exc:
        print(f'{path}: not read ({exc})', file=sys.stderr)
        return None


def _helpers(tree):
    """Module functions ``f(text)`` that return ``QCoreApplication.translate('Context', text)``: name -> context."""
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.args.args:
            continue
        parameter = node.args.args[0].arg
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and len(call.args) >= 2
                    and getattr(call.func, 'attr', getattr(call.func, 'id', None)) == 'translate'
                    and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)
                    and isinstance(call.args[1], ast.Name) and call.args[1].id == parameter):
                found[node.name] = call.args[0].value
                break
    return found


class _Collector:
    def __init__(self):
        self._helper_cache = {}

    def helpers_of(self, path):
        path = os.path.normpath(path)
        if path not in self._helper_cache:
            tree = _parse(path) if os.path.exists(path) else None
            self._helper_cache[path] = _helpers(tree) if tree is not None else {}
        return self._helper_cache[path]

    def names(self, path, tree):
        """Local name -> context of every helper defined in or imported into ``path``."""
        names = dict(self.helpers_of(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            folder = os.path.dirname(path)
            for _ in range(node.level - 1):
                folder = os.path.dirname(folder)
            module = os.path.join(folder, *(node.module or '').split('.')) + '.py'
            helpers = self.helpers_of(module)
            for alias in node.names:
                if alias.name in helpers:
                    names[alias.asname or alias.name] = helpers[alias.name]
        return names


def collect(pro_path):
    """Every (context, source text, .ts file name, line) translated through a helper or a dock receiver."""
    base = os.path.dirname(os.path.abspath(pro_path))
    collector = _Collector()
    strings = set()
    for relative in _sources(pro_path):
        path = os.path.normpath(os.path.join(base, relative))
        tree = _parse(path)
        if tree is None:
            continue
        names = collector.names(path, tree)
        for call in ast.walk(tree):
            if not (isinstance(call, ast.Call) and call.args and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)):
                continue
            context = None
            if isinstance(call.func, ast.Name):
                context = names.get(call.func.id)
            elif isinstance(call.func, ast.Attribute) and call.func.attr == 'tr':
                context = RECEIVERS.get(ast.unparse(call.func.value))
            if context:
                strings.add((context, call.args[0].value, relative, call.lineno))
    return sorted(strings)


def _location(message, filename, line):
    location = ET.Element('location', {'filename': filename, 'line': str(line)})
    message.insert(list(message).index(message.find('source')), location)


def fix(ts_path, strings):
    """File ``strings`` (from :func:`collect`) under their context in one .ts file; returns how many moved."""
    tree = ET.parse(ts_path)
    root = tree.getroot()
    wanted = {}
    for context, text, filename, line in strings:
        wanted.setdefault((context, text), []).append((filename, line))
    files_of = {}
    for (_, text), locations in wanted.items():
        files_of.setdefault(text, set()).update(filename for filename, _ in locations)

    carried = {}
    for context in list(root.findall('context')):
        if context.findtext('name') not in MISFILED:
            continue
        for message in list(context.findall('message')):
            text = message.findtext('source')
            files = {location.get('filename') for location in message.findall('location')}
            if text in files_of and files and files <= files_of[text]:
                translation = message.find('translation')
                if translation.get('type') not in OBSOLETE + ('unfinished',) and (translation.text or '').strip():
                    carried[text] = translation.text
                context.remove(message)
        if not context.findall('message'):
            root.remove(context)

    moved = 0
    for (name, text), locations in wanted.items():
        target = _context(root, name)
        message = next((m for m in target.findall('message') if m.findtext('source') == text), None)
        if message is None:
            message = ET.SubElement(target, 'message')
            ET.SubElement(message, 'source').text = text
            ET.SubElement(message, 'translation', {'type': 'unfinished'})
        translation = message.find('translation')
        if translation.get('type') in OBSOLETE:
            # pylupdate5 dropped the helper locations: they are the current ones
            for location in message.findall('location'):
                message.remove(location)
        present = {(location.get('filename'), location.get('line')) for location in message.findall('location')}
        for filename, line in sorted(locations):
            if (filename, str(line)) not in present:
                _location(message, filename, line)
        if translation.get('type') in OBSOLETE + ('unfinished',):
            text_kept = translation.text if translation.get('type') in OBSOLETE else None
            text_kept = text_kept if (text_kept or '').strip() else carried.get(text)
            translation.text = text_kept
            if (text_kept or '').strip():
                translation.attrib.pop('type', None)
            else:
                translation.set('type', 'unfinished')
        moved += 1
    write_ts(tree, ts_path)
    return moved


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        found = collect(os.path.join(os.path.dirname(paths[0]), 'FilterMate.pro'))
        for ts_path in paths:
            print(f'{ts_path}: {fix(ts_path, found)} helper string(s) in their runtime context')
