#!/usr/bin/env python3
"""Add one message, translated, to a context of every ``i18n/FilterMate_*.ts``, in the layout pylupdate5 writes.

For a message or two between two full passes (pylupdate5 on Windows, then the context scripts): the
message goes after an existing one of the same context, with a location, and is ``type`` finished.
The next full pass puts every location right. Run lrelease afterwards, in the qgis/qgis Docker image
(``lrelease i18n/FilterMate_*.ts``): Windows QGIS has no lrelease.

    python3 scripts/i18n_add_message.py messages.json

``messages.json``: ``[{"context", "after", "source", "file", "line", "translations": {"fr": ...}}]``,
``after`` the source of the message it follows, ``translations`` keyed by the suffix of the file
(``fr`` for FilterMate_fr.ts). A context absent from the .ts is created, in the order of the names, when
``after`` is null; its next message names the first one in ``after``. Every .ts must have a translation, and a message already there is left alone.
"""
import glob
import json
import os
import re
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _xml(text: str) -> str:
    """Text as pylupdate5 writes it in a .ts: &, < and > escaped, double quotes as &quot;."""
    return escape(text).replace('"', "&quot;")


def add(path: str, message: dict, translation: str) -> bool:
    """Insert ``message`` in the .ts at ``path``; False when it is already there."""
    with open(path, encoding="utf-8") as stream:
        text = stream.read()
    context = re.search(r"<context>\n    <name>" + re.escape(message["context"]) + r"</name>\n(.*?)</context>", text, re.S)
    if context is None and message.get("after") is None:
        return _add_context(path, text, message, translation)
    if context is None:
        raise ValueError(f"{path}: no context {message['context']}")
    body = context.group(1)
    if f"<source>{_xml(message['source'])}</source>" in body:
        return False
    anchor = re.search(r"    <message>\n(?:(?!    </message>).)*?<source>" + re.escape(_xml(message["after"]))
                       + r"</source>.*?    </message>\n", body, re.S)
    if anchor is None:
        raise ValueError(f"{path}: no message {message['after']!r} in {message['context']}")
    entry = _entry(message, translation)
    at = context.start(1) + anchor.end()
    with open(path, "w", encoding="utf-8", newline="") as stream:
        stream.write(text[:at] + entry + text[at:])
    return True


def _entry(message: dict, translation: str) -> str:
    """One <message> as pylupdate5 writes it."""
    return ("    <message>\n"
            f"        <location filename=\"../{message['file']}\" line=\"{message['line']}\"/>\n"
            f"        <source>{_xml(message['source'])}</source>\n"
            f"        <translation>{_xml(translation)}</translation>\n"
            "    </message>\n")


def _add_context(path: str, text: str, message: dict, translation: str) -> bool:
    """Create the context of ``message`` before the first context whose name sorts after it, as pylupdate5 orders them."""
    block = f"<context>\n    <name>{_xml(message['context'])}</name>\n" + _entry(message, translation) + "</context>\n"
    at = None
    for found in re.finditer(r"<context>\n    <name>(.*?)</name>\n", text):
        if found.group(1) > message["context"]:
            at = found.start()
            break
    if at is None:
        at = text.rindex("</TS>")
    with open(path, "w", encoding="utf-8", newline="") as stream:
        stream.write(text[:at] + block + text[at:])
    return True


def main(argv) -> int:
    with open(argv[1], encoding="utf-8") as stream:
        messages = json.load(stream)
    paths = sorted(glob.glob(os.path.join(ROOT, "i18n", "FilterMate_*.ts")))
    for message in messages:
        missing = [os.path.basename(path) for path in paths
                   if os.path.basename(path)[len("FilterMate_"):-len(".ts")] not in message["translations"]]
        if missing:
            raise SystemExit(f"{message['source']!r}: no translation for {', '.join(missing)}")
        added = sum(add(path, message, message["translations"][os.path.basename(path)[len("FilterMate_"):-len(".ts")]])
                    for path in paths)
        print(f"{message['source']!r}: added to {added} of {len(paths)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
