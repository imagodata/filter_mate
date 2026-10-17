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
    for context in root.findall('context'):
        if context.findtext('name') == name:
            return context
    context = ET.SubElement(root, 'context')
    ET.SubElement(context, 'name').text = name
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
                target.remove(previous)
            target.append(message)
            kept[source] = message
        if not context.findall('message'):
            root.remove(context)
    ET.indent(tree, space='    ')
    body = ET.tostring(root, encoding='unicode')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body + '\n')
    return restored


if __name__ == '__main__':
    for ts_path in sys.argv[1:]:
        print(f'{ts_path}: {fix(ts_path)} translation(s) taken back')
