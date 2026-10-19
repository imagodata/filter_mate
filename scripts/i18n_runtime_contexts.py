# -*- coding: utf-8 -*-
"""Put in i18n/*.ts the strings the plugin translates through a helper, under the context it looks them up in.

pylupdate5 only understands ``self.tr("...")`` and ``translate("Context", "...")``. These call forms of
the plugin escape it:

- a helper ``def _tr(text): return QCoreApplication.translate('ServerFilterTranslation', text)``
  (module level, nested in a method, or imported under another name) called as ``_tr("...")``:
  the string is not extracted at all; named ``tr``, it is filed under ``@default``;
- a method ``def _tr(self, text): return self.dockwidget.tr(text)`` called as ``self._tr("...")``;
- an alias ``_tr = QCoreApplication.translate`` called as ``_tr("Context", "...")``;
- ``dw.tr("...")`` / ``self._dockwidget.tr("...")``: the string is filed under the receiver's text
  (``dw``), while PyQt looks it up under the class of the dock, ``FilterMateDockWidget``.

A name the calling function rebinds (``tr = context.tr``, a parameter) is not taken for the helper.
The FILTERING predicate labels stay out (see ``EXCLUDED_CONTEXTS``).

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
TWO_ARGS = object()
# Contexts left untranslated on purpose: the FILTERING predicate labels ("Intersect", "Are within"...)
# are matched as English text by core/domain/cross_filter.py; translating them breaks the predicates.
EXCLUDED_CONTEXTS = {'ComboboxPopulationManager'}
# Imported names worth resolving: the helpers are named tr, _tr, translate, _translate...
HELPER_NAME = re.compile(r'(^|_)(tr|translate)$')


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


def _is_text(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _helper_kind(function):
    """Context of a function or method that translates its text argument, TWO_ARGS, or None."""
    parameters = [argument.arg for argument in function.args.args if argument.arg not in ('self', 'cls')]
    if not parameters:
        return None
    for call in ast.walk(function):
        if not isinstance(call, ast.Call):
            continue
        name = getattr(call.func, 'attr', getattr(call.func, 'id', None))
        if name == 'translate' and len(call.args) >= 2:
            if _is_text(call.args[0]) and _is_name(call.args[1], parameters[0]):
                return call.args[0].value
            if len(parameters) >= 2 and _is_name(call.args[0], parameters[0]) and _is_name(call.args[1], parameters[1]):
                return TWO_ARGS
        if (name == 'tr' and isinstance(call.func, ast.Attribute) and call.args
                and RECEIVERS.get(ast.unparse(call.func.value)) and _is_name(call.args[0], parameters[0])):
            return RECEIVERS[ast.unparse(call.func.value)]
    return None


def _helpers(tree):
    """Functions and methods, at any depth, that translate their text argument: name -> context or TWO_ARGS.

    - ``def _tr(text): return QCoreApplication.translate('Ctx', text)``, also nested in a method;
    - ``def _tr(self, text): return self.dockwidget.tr(text)``: the dock's context;
    - ``_tr = QCoreApplication.translate`` / ``def _tr(context, text)``: the context is the first argument
      of each call. Names spelt ``translate`` / ``tr`` with two arguments are read by pylupdate5 itself.
    """
    found = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Attribute) and node.value.attr == 'translate'
                and node.targets[0].id != 'translate'):
            found[node.targets[0].id] = TWO_ARGS
        elif isinstance(node, ast.FunctionDef) and len(node.body) <= 6:  # a helper is a few lines
            kind = _helper_kind(node)
            if kind and not (kind == TWO_ARGS and node.name == 'translate'):
                found[node.name] = kind
    return found


class _Collector:
    def __init__(self):
        self._helper_cache = {}

    def remember(self, path, tree):
        """Helpers of a module already parsed (no second parse)."""
        self._helper_cache.setdefault(os.path.normpath(path), _helpers(tree))

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
            wanted = [alias for alias in node.names if HELPER_NAME.search(alias.name)]
            if not wanted:
                continue  # parse only the modules a translation helper may come from
            module = os.path.join(folder, *(node.module or '').split('.')) + '.py'
            helpers = self.helpers_of(module)
            for alias in wanted:
                if alias.name in helpers:
                    names[alias.asname or alias.name] = helpers[alias.name]
        return names


def _local_names(function):
    """Names a function binds itself (parameters, ``x = ...``): a call to them is not the module helper."""
    arguments = function.args
    names = {argument.arg for argument in arguments.args + arguments.kwonlyargs + arguments.posonlyargs}
    pending = list(function.body)
    while pending:  # its own body only: a nested function binds its own names
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Assign) and not (isinstance(node.value, ast.Attribute)
                                                 and node.value.attr == 'translate'):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        pending.extend(ast.iter_child_nodes(node))
    return names


def _calls(tree):
    """Every call of ``tree`` with the names its enclosing functions rebind."""
    stack = [(tree, frozenset())]
    while stack:
        node, shadowed = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call):
                yield child, shadowed
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stack.append((child, shadowed | _local_names(child)))
            else:
                stack.append((child, shadowed))


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
        collector.remember(path, tree)
        names = collector.names(path, tree)
        for call, shadowed in _calls(tree):
            if not call.args:
                continue
            kind = None
            if isinstance(call.func, ast.Name):
                kind = None if call.func.id in shadowed else names.get(call.func.id)
            elif isinstance(call.func, ast.Attribute) and call.func.attr == 'tr':
                kind = RECEIVERS.get(ast.unparse(call.func.value))
            elif isinstance(call.func, ast.Attribute) and _is_name(call.func.value, 'self'):
                kind = names.get(call.func.attr)  # a translating method: self._tr('...')
            if kind is TWO_ARGS:
                if len(call.args) >= 2 and _is_text(call.args[0]) and _is_text(call.args[1]):
                    context, text = call.args[0].value, call.args[1].value
                else:
                    continue
            elif kind and _is_text(call.args[0]):
                context, text = kind, call.args[0].value
            else:
                continue
            if context not in EXCLUDED_CONTEXTS:
                strings.add((context, text, relative, call.lineno))
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
