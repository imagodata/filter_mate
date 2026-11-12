# -*- coding: utf-8 -*-
"""2026-11-12: a layout export creates its sub-folder and never overwrites a file.

The sub-folder below the export root was never created (``export_layers`` creates it), so a new sub-folder made
the export fail; and a file of the same name was overwritten.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_layout_export_test"


def _load():
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    operations = types.ModuleType(f"{_PKG}.adapters.public_api.operations")
    operations.resolve_layer = lambda *args: None
    sys.modules[operations.__name__] = operations
    return importlib.import_module(f"{_PKG}.adapters.public_api.layouts")


layouts = _load()


class _Exporter:
    """Writes the file QgsLayoutExporter would write."""

    written = []

    class PdfExportSettings:
        dpi = 0

    class ImageExportSettings:
        dpi = 0

    def __init__(self, layout):
        self.layout = layout

    def exportToPdf(self, path, settings):
        pathlib.Path(path).write_bytes(b"%PDF new")
        type(self).written.append(path)
        return 0

    exportToImage = exportToPdf

    def errorMessage(self):
        return ""


@pytest.fixture(autouse=True)
def qgis(monkeypatch):
    core = sys.modules["qgis.core"]
    layout = SimpleNamespace(name=lambda: "Carte A4")
    manager = SimpleNamespace(layoutByName=lambda name: layout if name == "Carte A4" else None, printLayouts=lambda: [])
    monkeypatch.setattr(core, "QgsProject", SimpleNamespace(instance=lambda: SimpleNamespace(
        layoutManager=lambda: manager)), raising=False)
    monkeypatch.setattr(core, "QgsLayoutExporter", _Exporter, raising=False)
    _Exporter.written = []


def test_a_new_sub_folder_is_created(tmp_path):
    folder = tmp_path / "root" / "layouts" / "2026"
    answer = layouts.export_layout("Carte A4", str(folder))
    assert pathlib.Path(answer["path"]) == folder / "Carte A4.pdf"
    assert (folder / "Carte A4.pdf").read_bytes() == b"%PDF new"


def test_an_existing_file_is_kept(tmp_path):
    (tmp_path / "Carte A4.pdf").write_bytes(b"%PDF of the user")
    (tmp_path / "Carte A4_2.pdf").write_bytes(b"%PDF older export")
    answer = layouts.export_layout("Carte A4", str(tmp_path))
    assert pathlib.Path(answer["path"]).name == "Carte A4_3.pdf"
    assert (tmp_path / "Carte A4.pdf").read_bytes() == b"%PDF of the user"
    assert (tmp_path / "Carte A4_2.pdf").read_bytes() == b"%PDF older export"


def test_a_folder_that_cannot_be_made_is_refused(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    with pytest.raises(ValueError, match="could not be created"):
        layouts.export_layout("Carte A4", str(blocker / "layouts"))
    assert _Exporter.written == []
