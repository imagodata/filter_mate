# -*- coding: utf-8 -*-
"""Put the Processing strings of i18n/*.ts back in the context the plugin looks them up in.

The FilterMate algorithms translate with ``QCoreApplication.translate("Processing", ...)``
behind their ``self.tr()``, but pylupdate5 files a ``self.tr()`` string under the name of the
class it is in (``FilterMateAlgorithm``, ``CrossFilterAlgorithm``...). After every pylupdate5
run the translations of the "Processing" context come back as vanished and the same strings
as unfinished under the class names. This script moves every message whose locations are all
in ``processing/`` into the "Processing" context (one message per source text, all its
locations kept) and takes the translation a vanished message of that context still holds.

Run it right after pylupdate5, before translating and compiling with lrelease::

    python3 scripts/i18n_processing_context.py i18n/FilterMate_*.ts
"""
import sys
import xml.etree.ElementTree as ET

CONTEXT = 'Processing'
SOURCE_PREFIX = '../processing/'


def _locations(message):
    return [location.get('filename', '') for location in message.findall('location')]


def _is_processing(message) -> bool:
    files = _locations(message)
    return bool(files) and all(name.startswith(SOURCE_PREFIX) for name in files)


def _context(root, name):
    """The context ``name``, made at its place among the others (pylupdate5 sorts them by name)."""
    contexts = root.findall('context')
    for context in contexts:
        if context.findtext('name') == name:
            return context
    context = ET.Element('context')
    ET.SubElement(context, 'name').text = name
    following = next((index for index, other in enumerate(list(root))
                      if other.tag == 'context' and other.findtext('name') > name), len(root))
    root.insert(following, context)
    return context


def fix(path: str) -> int:
    """Move the Processing messages of one .ts file; returns how many translations were taken back."""
    tree = ET.parse(path)
    root = tree.getroot()
    target = _context(root, CONTEXT)
    kept = {message.findtext('source'): message for message in target.findall('message')}
    restored = 0
    for context in list(root.findall('context')):
        name = context.findtext('name')
        if name == CONTEXT:
            continue
        messages = [message for message in context.findall('message') if _is_processing(message)]
        for message in messages:
            context.remove(message)
            source = message.findtext('source')
            previous = kept.get(source)
            if previous is not None:
                if previous.find('translation').get('type') not in ('vanished', 'obsolete'):
                    # Already moved from another class: one message, every location.
                    for location in message.findall('location'):
                        previous.insert(list(previous).index(previous.find('source')), location)
                    continue
                old = previous.find('translation')
                if old is not None and (old.text or '').strip():
                    translation = message.find('translation')
                    translation.text = old.text
                    translation.attrib.pop('type', None)
                    restored += 1
                # In its place: pylupdate5 keeps the order of the previous file, so does this script.
                target.insert(list(target).index(previous), message)
                target.remove(previous)
            else:
                target.append(message)
            kept[source] = message
        if not context.findall('message'):
            root.remove(context)
    write_ts(tree, path)
    return restored


def _escape(text: str, source: bool) -> str:
    """Escape as pylupdate5 does: ``"`` always, ``'`` only in an all-ASCII source text."""
    text = (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    if source and text.isascii():
        text = text.replace("'", '&apos;')
    return text


def write_ts(tree, path: str) -> None:
    """Write a .ts file in the layout of pylupdate5, so a run of this script only shows its own changes."""
    root = tree.getroot()
    attributes = ''.join(f' {key}="{_escape(value, False)}"' for key, value in root.attrib.items())
    lines = ['<?xml version="1.0" encoding="utf-8"?>', '<!DOCTYPE TS>', f'<TS{attributes}>']
    for context in root.findall('context'):
        lines += ['<context>', f'    <name>{_escape(context.findtext("name"), False)}</name>']
        for message in context.findall('message'):
            lines.append('    <message>')
            for location in message.findall('location'):
                lines.append(f'        <location filename="{_escape(location.get("filename"), False)}" '
                             f'line="{location.get("line")}"/>')
            lines.append(f'        <source>{_escape(message.findtext("source"), True)}</source>')
            translation = message.find('translation')
            kind = translation.get('type')
            opening = f'<translation type="{kind}">' if kind else '<translation>'
            lines.append(f'        {opening}{_escape(translation.text, False)}</translation>')
            lines.append('    </message>')
        lines.append('</context>')
    lines.append('</TS>')
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    for ts_path in sys.argv[1:]:
        print(f'{ts_path}: {fix(ts_path)} translation(s) taken back')
