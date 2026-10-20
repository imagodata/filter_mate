# -*- coding: utf-8 -*-
"""
scripts/publish_qgis.py validates the release archive (the 'Verify the ZIP' step of release.yml).

Checks: forbidden file types, size ceilings, mandatory metadata.txt keys (and the icon file),
Python 3.8 grammar and unscoped Qt enums in the Python files of the archive.
"""
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import publish_qgis  # noqa: E402

METADATA = """[general]
name=FilterMate
qgisMinimumVersion=3.22
description=d
about=a
version=5.0.0
author=x
email=x@example.org
repository=https://example.org/r
tracker=https://example.org/t
icon=icon.png
"""


def _build(tmp_path, extra=None, metadata=METADATA, init="def classFactory(iface):\n    return None\n"):
    path = tmp_path / "plugin.zip"
    files = {
        "filter_mate/metadata.txt": metadata,
        "filter_mate/__init__.py": init,
        "filter_mate/filter_mate.py": "x = 1\n",
        "filter_mate/icon.png": b"png",
    }
    files.update(extra or {})
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


pytestmark = pytest.mark.unit


def test_a_clean_archive_is_accepted(tmp_path):
    assert publish_qgis.validate(_build(tmp_path)) == "5.0.0"


@pytest.mark.parametrize("name", ["filter_mate/a.pyc", "filter_mate/x.log", "filter_mate/lib.so",
                                  "filter_mate/lib.dll", "filter_mate/tool.exe"])
def test_forbidden_file_types_are_refused(tmp_path, name):
    with pytest.raises(ValueError, match="forbidden file type"):
        publish_qgis.validate(_build(tmp_path, {name: b"x"}))


def test_a_missing_metadata_key_is_refused(tmp_path):
    with pytest.raises(ValueError, match='missing or empty "tracker"'):
        publish_qgis.validate(_build(tmp_path, metadata=METADATA.replace("tracker=https://example.org/t\n", "")))


def test_the_icon_must_be_shipped(tmp_path):
    path = _build(tmp_path, metadata=METADATA.replace("icon=icon.png", "icon=other.png"))
    with pytest.raises(ValueError, match='icon "other.png" is not in the archive'):
        publish_qgis.validate(path)


def test_size_ceilings(tmp_path, monkeypatch):
    path = _build(tmp_path, {"filter_mate/data.bin": b"0" * 4096})
    monkeypatch.setattr(publish_qgis, "MAX_ENTRY_BYTES", 1024)
    with pytest.raises(ValueError, match="file larger than"):
        publish_qgis.validate(path)
    monkeypatch.setattr(publish_qgis, "MAX_ENTRY_BYTES", 10 ** 9)
    monkeypatch.setattr(publish_qgis, "MAX_ARCHIVE_BYTES", 100)
    with pytest.raises(ValueError, match="Archive larger than"):
        publish_qgis.validate(path)


def test_unscoped_qt_enums_in_the_archive_are_refused(tmp_path):
    source = "from qgis.PyQt.QtWidgets import QSizePolicy as SP\nx = SP.Fixed\n"
    with pytest.raises(ValueError, match="filter_mate/ui.py:2 unscoped Qt enum QSizePolicy.Fixed"):
        publish_qgis.validate(_build(tmp_path, {"filter_mate/ui.py": source}))


def test_python_310_syntax_is_refused(tmp_path):
    source = "match x:\n    case 1:\n        pass\n"
    with pytest.raises(ValueError, match="filter_mate/m.py"):
        publish_qgis.validate(_build(tmp_path, {"filter_mate/m.py": source}))


def test_bandit_findings_are_problems_but_not_the_subprocess_import():
    report = {"results": [
        {"test_id": "B404", "filename": "filter_mate/a.py", "line_number": 1, "issue_text": "import subprocess"},
        {"test_id": "B314", "filename": "filter_mate/b.py", "line_number": 8, "issue_text": "xml parse"}]}
    assert publish_qgis.bandit_problems(report) == ["Bandit B314 filter_mate/b.py:8 xml parse"]
    assert publish_qgis.bandit_problems({}) == []


def test_detect_secrets_findings_are_problems():
    report = {"results": {"filter_mate/c.py": [{"type": "Secret Keyword", "line_number": 3}]}}
    assert publish_qgis.secrets_problems(report) == ["detect-secrets Secret Keyword filter_mate/c.py:3"]
    assert publish_qgis.secrets_problems({"results": {}}) == []


def test_security_findings_reject_the_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_qgis, "check_security", lambda archive: ["Bandit B603 filter_mate/x.py:1 call"])
    with pytest.raises(ValueError, match="Bandit B603"):
        publish_qgis.validate(_build(tmp_path), security=True)
    assert publish_qgis.validate(_build(tmp_path), security=False) == "5.0.0"
