# -*- coding: utf-8 -*-
"""set_project_crs refuses a definition naming a grid by its address or its file (2026-11-24), and never answers
an empty CRS for a CRS of its own (a PROJ: string suggest_crs made has no authid).

Same harness as test_project_control_open_data.py: the module loads for real, QGIS stays mocked, the resolver is a
stand-in.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_project_control_crs_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.agent", _ROOT / "adapters" / "agent"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        return importlib.import_module(f"{_PKG}.adapters.public_api.project_control")
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


project_control = _load()


@pytest.fixture(autouse=True)
def no_layer(monkeypatch):
    monkeypatch.setattr(project_control, "resolve_layer", lambda reference: None)


class _Crs:
    """A CRS of its own: valid, but with neither an authid nor a description."""

    def __init__(self, definition=""):
        self.definition = definition

    def isValid(self):
        return True

    def authid(self):
        return ""

    def description(self):
        return ""

    def isGeographic(self):
        return False

    def mapUnits(self):
        return 0


class _Project:
    def crs(self):
        return _Crs()

    def setCrs(self, crs):
        self.kept = crs


@pytest.fixture(autouse=True)
def fake_qgis(monkeypatch):
    core = sys.modules["qgis.core"]
    monkeypatch.setattr(core, "QgsCoordinateReferenceSystem", _Crs, raising=False)
    monkeypatch.setattr(core, "QgsProject", type("P", (), {"instance": staticmethod(lambda: _Project())}),
                        raising=False)
    monkeypatch.setattr(core, "QgsUnitTypes", type("U", (), {"toString": staticmethod(lambda units: "metres")}),
                        raising=False)


@pytest.mark.parametrize("definition", [
    "+proj=pipeline +step +grids=/vsicurl/https://grids.example.com/fr.gsb +step +proj=unitconvert",
    "+proj=tmerc +nadgrids=/usr/share/proj/fr_ign.gsb +units=m",
    r"+proj=tmerc +nadgrids=C:\grids\fr_ign.gsb +units=m",
    "+proj=tmerc +geoidgrids=/data/fr.gtx +units=m",
    r"GEOGCS[\"GCS\",DATUM[\"D\",SPHEROID[\"S\",1,0]],PRIMEM[\"G\",0],UNIT[\"d\",0.0174533],"
    r"REMARK[\"file \\\\share\\grids\\x.gsb\"]]",
    "BOUNDCRS[SOURCECRS[GEOGCS[\"G\"]],TARGETCRS[GEOGCS[\"G\"]],"
    "ABRIDGEDTRANSFORMATION[\"t\",METHOD[\"m\"],PARAMETERFILE[\"/data/x.gsb\"]]]",
    "BOUNDCRS[SOURCECRS[GEOGCS[\"G\"]],TARGETCRS[GEOGCS[\"G\"]],"
    "ABRIDGEDTRANSFORMATION[\"t\",METHOD[\"m\"],PARAMETERFILE[\"https://grids.example.com/x.gsb\"]]]",
])
def test_a_definition_naming_a_grid_is_refused(definition):
    with pytest.raises(ValueError, match="address or its file"):
        project_control.set_project_crs(definition)


@pytest.mark.parametrize("definition", [
    # A bare "= /" outside a grid parameter is descriptive text, not a grid (2026-11-26: refused before).
    # Plain quotes (no backslash): what a real WKT definition carries.
    'GEOGCS["G",DATUM["D",SPHEROID["S",1,0]],PRIMEM["G",0],UNIT["d",0.0174533],'
    'REMARK["scale = /25000"]]',
    # Search-path grids name no file and download nothing.
    "+proj=tmerc +nadgrids=@conus,@alaska +units=m",
    'BOUNDCRS[SOURCECRS[GEOGCS["G"]],TARGETCRS[GEOGCS["G"]],'
    'ABRIDGEDTRANSFORMATION["t",METHOD["m"],PARAMETERFILE["x.gsb"]]]',
])
def test_a_definition_without_a_grid_address_or_file_passes_the_gate(definition):
    assert project_control.set_project_crs(definition)["crs"]


def test_a_plain_proj_string_without_a_grid_passes_the_gate():
    answer = project_control.set_project_crs("+proj=tmerc +lat_0=0 +lon_0=3 +k=1 +x_0=500000 +ellps=GRS80 +units=m")
    assert answer["crs"]  # whatever the mock says: the gate did not refuse it


def test_a_crs_of_its_own_comes_back_named_never_empty():
    asked = "+proj=aea +lat_1=46 +lat_2=49 +ellps=GRS80 +units=m"
    assert project_control.set_project_crs(asked)["crs"] == asked
