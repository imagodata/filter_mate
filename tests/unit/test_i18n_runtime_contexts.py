# -*- coding: utf-8 -*-
"""
scripts/i18n_runtime_contexts.py files the helper-translated strings under their runtime context.

pylupdate5 misses ``_tr('...')`` (a module helper around QCoreApplication.translate), files a bare
``tr('...')`` helper call under ``@default`` and a ``dw.tr('...')`` call under ``dw``, while the
plugin looks them up under the helper's context or the dock's class: such strings were never
translated (lots A to E of the streaming sources, October 2026).
"""
import importlib.util
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "i18n_runtime_contexts.py"


def _script():
    spec = importlib.util.spec_from_file_location("fm_test_i18n_runtime_contexts", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.0" language="fr">
<context>
    <name>@default</name>
    <message>
        <location filename="../pkg/other.py" line="3"/>
        <source>Kept elsewhere</source>
        <translation>Gardé ailleurs</translation>
    </message>
    <message>
        <location filename="../pkg/helper.py" line="12"/>
        <source>Tile</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>HelperCtx</name>
    <message>
        <location filename="../pkg/helper.py" line="40"/>
        <source>Hello</source>
        <translation type="obsolete">Bonjour</translation>
    </message>
    <message>
        <location filename="../pkg/helper.py" line="41"/>
        <source>Gone</source>
        <translation type="obsolete">Parti</translation>
    </message>
</context>
<context>
    <name>dw</name>
    <message>
        <location filename="../pkg/dock_user.py" line="2"/>
        <source>Dock text</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>self._dockwidget</name>
    <message>
        <location filename="../pkg/dock_user.py" line="3"/>
        <source>Other</source>
        <translation type="unfinished"></translation>
    </message>
</context>
</TS>
"""


@pytest.fixture
def tree(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "helper.py").write_text(textwrap.dedent("""\
        from qgis.PyQt.QtCore import QCoreApplication


        def _tr(text):
            return QCoreApplication.translate('HelperCtx', text)


        def tr(text):
            translated = QCoreApplication.translate('TileCtx', text)
            return translated if isinstance(translated, str) else text

        LABEL = tr('Tile')
        GREETING = _tr('Hello')
        """), encoding="utf-8")
    (pkg / "user.py").write_text(textwrap.dedent("""\
        from .helper import _tr as message


        def warn():
            return message(
                'Imported '
                'text')
        """), encoding="utf-8")
    (pkg / "dock_user.py").write_text("def show(dw, self):\n    dw.tr('Dock text')\n    self._dockwidget.tr('Other')\n",
                                       encoding="utf-8")
    i18n = tmp_path / "i18n"
    i18n.mkdir()
    (i18n / "FilterMate.pro").write_text(
        "SOURCES = \\\n    ../pkg/helper.py \\\n    ../pkg/user.py \\\n    ../pkg/dock_user.py\n\nTRANSLATIONS = \\\n"
        "    FilterMate_fr.ts\n", encoding="utf-8")
    (i18n / "FilterMate_fr.ts").write_text(TS, encoding="utf-8")
    return tmp_path


def _messages(path):
    root = ET.parse(path).getroot()
    found = {}
    for context in root.findall("context"):
        for message in context.findall("message"):
            translation = message.find("translation")
            found[(context.findtext("name"), message.findtext("source"))] = (
                translation.get("type"), translation.text,
                [(location.get("filename"), location.get("line")) for location in message.findall("location")])
    return found


def test_helper_strings_reach_their_runtime_context(tree):
    module = _script()
    ts = tree / "i18n" / "FilterMate_fr.ts"
    module.fix(str(ts), module.collect(str(tree / "i18n" / "FilterMate.pro")))
    messages = _messages(ts)

    # _tr('Hello'): revived with its old translation, at its current line
    assert messages[("HelperCtx", "Hello")] == (None, "Bonjour", [("../pkg/helper.py", "13")])
    # imported under another name, implicit concatenation
    assert messages[("HelperCtx", "Imported text")][0] == "unfinished"
    assert messages[("HelperCtx", "Imported text")][2] == [("../pkg/user.py", "5")]
    # a string no longer in the code stays obsolete
    assert messages[("HelperCtx", "Gone")][0] == "obsolete"
    # bare tr() helper: out of @default, into its own context; the other @default string stays
    assert ("@default", "Tile") not in messages
    assert messages[("TileCtx", "Tile")][0] == "unfinished"
    assert messages[("@default", "Kept elsewhere")] == (None, "Gardé ailleurs", [("../pkg/other.py", "3")])
    # receiver contexts: the class PyQt looks them up under
    assert messages[("FilterMateDockWidget", "Dock text")][0] == "unfinished"
    assert messages[("FilterMateDockWidget", "Other")][0] == "unfinished"
    assert not any(context in ("dw", "self._dockwidget") for context, _ in messages)


def test_second_run_changes_nothing(tree):
    module = _script()
    ts = tree / "i18n" / "FilterMate_fr.ts"
    strings = module.collect(str(tree / "i18n" / "FilterMate.pro"))
    module.fix(str(ts), strings)
    first = ts.read_text(encoding="utf-8")
    module.fix(str(ts), strings)
    assert ts.read_text(encoding="utf-8") == first


def test_direct_translate_location_is_kept(tree):
    """``translate('HelperCtx', 'Hello')`` elsewhere: pylupdate5's location stays next to the helper's."""
    module = _script()
    ts = tree / "i18n" / "FilterMate_fr.ts"
    ts.write_text(TS.replace('<location filename="../pkg/helper.py" line="40"/>\n        <source>Hello</source>\n'
                             '        <translation type="obsolete">Bonjour</translation>',
                             '<location filename="../pkg/direct.py" line="7"/>\n        <source>Hello</source>\n'
                             '        <translation>Bonjour</translation>'), encoding="utf-8")
    module.fix(str(ts), module.collect(str(tree / "i18n" / "FilterMate.pro")))
    assert _messages(ts)[("HelperCtx", "Hello")] == (
        None, "Bonjour", [("../pkg/direct.py", "7"), ("../pkg/helper.py", "13")])


def test_translated_message_keeps_its_translation_when_moved(tree):
    module = _script()
    ts = tree / "i18n" / "FilterMate_fr.ts"
    ts.write_text(TS.replace('<source>Dock text</source>\n        <translation type="unfinished"></translation>',
                             '<source>Dock text</source>\n        <translation>Texte du dock</translation>'),
                  encoding="utf-8")
    module.fix(str(ts), module.collect(str(tree / "i18n" / "FilterMate.pro")))
    assert _messages(ts)[("FilterMateDockWidget", "Dock text")][:2] == (None, "Texte du dock")
