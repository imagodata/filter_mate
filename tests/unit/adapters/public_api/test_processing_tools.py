# -*- coding: utf-8 -*-
"""How the parameters of a Processing algorithm reach QGIS (``adapters.public_api.processing_tools``).

The module is loaded for real under a synthetic package (its relative imports reach ``core`` and ``adapters``);
QGIS stays mocked by the root conftest, layers and parameter definitions are small stand-ins.
"""
import importlib
import pathlib
import sys
import types
import os
import tempfile
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_processing_tools_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".core.services", _ROOT / "core" / "services"),
                       (".adapters", _ROOT / "adapters"), (".adapters.public_api", _ROOT / "adapters" / "public_api"),
                       (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", _ROOT / "adapters" / "qgis" / "coverage_layers")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return (importlib.import_module(f"{_PKG}.adapters.public_api.processing_tools"),
            importlib.import_module(f"{_PKG}.core.domain.layer_kind").LayerKind)


tools, LayerKind = _load()
OPTIONAL, HIDDEN = 8, 2


def layer(layer_id, name, kind, fields=3):
    return SimpleNamespace(id=lambda: layer_id, name=lambda: name, kind=kind,
                           fields=lambda: SimpleNamespace(count=lambda: fields))


@pytest.fixture
def project(monkeypatch):
    """Two vector layers and a raster; a path, a URI or a URL is no layer of the project."""
    layers = {"points": layer("points_1a2b", "points", LayerKind.VECTOR),
              "lines": layer("lines_3c4d", "lines", LayerKind.VECTOR),
              "mnt": layer("mnt_5e6f", "mnt", LayerKind.RASTER)}
    by_id = {item.id(): item for item in layers.values()}
    monkeypatch.setattr(tools, "resolve_layer", lambda reference: by_id.get(reference) or layers.get(reference))
    monkeypatch.setattr(tools, "layer_kind", lambda item: item.kind, raising=False)
    monkeypatch.setattr(tools, "_flag", lambda scope, new, old: {"Optional": OPTIONAL, "Hidden": HIDDEN}.get(new, 0))
    return layers


def definition(name, kind, optional=False):
    return SimpleNamespace(name=lambda: name, type=lambda: kind, description=lambda: name.lower(),
                           flags=lambda: OPTIONAL if optional else 0, defaultValue=lambda: None,
                           createByDefault=lambda: True, defaultFileExtension=lambda: "tif",
                           clone=lambda: definition(name, kind, optional))


INTERPOLATION = definition("INTERPOLATION_DATA", "idw_interpolation_data")


class TestInterpolationRows:
    def test_each_source_becomes_the_id_of_a_vector_layer_of_the_project(self, project):
        value = "points::~::0::~::2::~::0::|::lines_3c4d::~:: 1 ::~::-1::~::1"
        assert tools._value(INTERPOLATION, value) == \
            "points_1a2b::~::0::~::2::~::0::|::lines_3c4d::~::1::~::-1::~::1"

    @pytest.mark.parametrize("value", [
        "/vsicurl/http://example.com/a.shp::~::0::~::0::~::0",  # QGIS would open it (variantToSource)
        "/home/user/secret.gpkg|layername=a::~::0::~::0::~::0",
        "points::~::0::~::0::~::0::|::/etc/passwd::~::0::~::0::~::0",  # a second row, smuggled
    ])
    def test_a_path_or_a_url_is_never_a_source(self, project, value):
        with pytest.raises(ValueError, match="not a layer of the project"):
            tools._value(INTERPOLATION, value)

    @pytest.mark.parametrize("value, message", [
        ("mnt::~::0::~::0::~::0", "not a vector layer"),
        ("points::~::0::~::0", "rows"),
        ("points::~::0::~::0::~::0::~::x", "rows"),
        ("points::~::attribute::~::0::~::0", "rows"),
        ("points::~::0.5::~::0::~::0", "rows"),
        ("points::~::3::~::0::~::0", "value source"),  # 0 a field, 1 the Z, 2 the M
        ("points::~::-1::~::0::~::0", "value source"),
        ("points::~::0::~::0::~::3", "source type"),  # 0 points, 1 structure lines, 2 break lines
        ("points::~::0::~::3::~::0", "field index"),  # points has 3 fields: 0 to 2, or -1
        ("points::~::0::~::-2::~::0", "field index"),
        ("", "rows"),
        (["points", 0, 0, 0], "rows"),
    ])
    def test_anything_else_is_refused(self, project, value, message):
        with pytest.raises(ValueError, match=message):
            tools._value(INTERPOLATION, value)

    def test_a_layer_id_holding_a_separator_is_refused(self, project, monkeypatch):
        odd = layer("a::|::b", "odd", LayerKind.VECTOR)  # ids come from the project file, written by anyone
        monkeypatch.setattr(tools, "resolve_layer", lambda reference: odd)
        with pytest.raises(ValueError, match="cannot be written"):
            tools._value(INTERPOLATION, "odd::~::0::~::0::~::0")


class TestTypesNotKnownAsSafe:
    def test_a_value_of_an_unknown_type_is_refused(self, project):
        grid = "+proj=pipeline +step +proj=hgridshift +grids=/vsicurl/http://example.com/g.tif"
        with pytest.raises(ValueError, match="cannot be given"):
            tools._value(definition("OPERATION", "coordinateoperation", optional=True), grid)

    def test_a_plain_value_passes_as_given(self, project):
        assert tools._value(definition("DISTANCE", "distance"), 12.5) == 12.5

    def test_an_optional_unknown_parameter_stays_unset(self, project):
        algorithm = SimpleNamespace(id=lambda: "native:reprojectlayer", parameterDefinitions=lambda: [
            definition("INPUT", "source"), definition("OPERATION", "coordinateoperation", optional=True)])
        values, made = tools._parameters(algorithm, {"INPUT": "points"})
        assert values == {"INPUT": "points_1a2b"} and made == []
        with pytest.raises(ValueError, match="cannot be given"):
            tools._parameters(algorithm, {"INPUT": "points", "OPERATION": "+proj=noop"})

    def test_describe_leaves_it_out_and_tells_how_to_write_the_rows(self, project, monkeypatch):
        algorithm = SimpleNamespace(
            id=lambda: "qgis:idwinterpolation", displayName=lambda: "IDW", group=lambda: "Interpolation",
            shortHelpString=lambda: "", shortDescription=lambda: "", flags=lambda: 0,
            provider=lambda: SimpleNamespace(id=lambda: "qgis", name=lambda: 'QGIS', isActive=lambda: True), outputDefinitions=lambda: [],
            parameterDefinitions=lambda: [INTERPOLATION, definition("OPERATION", "coordinateoperation", optional=True),
                                          definition("OUTPUT", "rasterDestination")])
        monkeypatch.setattr(tools, "_registry", lambda: SimpleNamespace(algorithmById=lambda _id: algorithm))
        answer = tools.describe_algorithm("qgis:idwinterpolation")
        assert [row["name"] for row in answer["parameters"]] == ["INTERPOLATION_DATA", "OUTPUT"]
        assert "::|::" in answer["parameters"][0]["value"] and answer["left_out"] == ["OPERATION"]


class TestValuesSetByFilterMate:
    """native:mergevectorlayers writes the source of each layer in its output unless ADD_SOURCE_FIELDS is off."""

    @staticmethod
    def _merge():
        definitions = [definition("LAYERS", "multilayer"), definition("ADD_SOURCE_FIELDS", "boolean", optional=True),
                       definition("OUTPUT", "sink")]
        return SimpleNamespace(
            id=lambda: "native:mergevectorlayers", displayName=lambda: "Merge", group=lambda: "Vector general",
            shortHelpString=lambda: "", shortDescription=lambda: "", flags=lambda: 0,
            provider=lambda: SimpleNamespace(id=lambda: "native", name=lambda: 'QGIS', isActive=lambda: True), outputDefinitions=lambda: [],
            parameterDefinitions=lambda: definitions)

    @pytest.mark.parametrize("given", [{"LAYERS": ["points"]}, {"LAYERS": ["points"], "ADD_SOURCE_FIELDS": True}])
    def test_the_source_fields_are_off_whatever_the_model_gives(self, project, monkeypatch, given):
        monkeypatch.setattr(tools, "_destination_path", lambda item: "/tmp/output.gpkg")
        values, _made = tools._parameters(self._merge(), given)
        assert values["ADD_SOURCE_FIELDS"] is False

    def test_describe_does_not_offer_what_the_model_cannot_set(self, project, monkeypatch):
        monkeypatch.setattr(tools, "_registry", lambda: SimpleNamespace(algorithmById=lambda _id: self._merge()))
        answer = tools.describe_algorithm("native:mergevectorlayers")
        assert [row["name"] for row in answer["parameters"]] == ["LAYERS", "OUTPUT"]


def test_stored_model_layer_defaults_cannot_open_a_file(project):
    source = definition('INPUT', 'source')
    source.defaultValue = lambda: '/private/not_a_project_layer.gpkg'
    algorithm = SimpleNamespace(id=lambda: 'model:example', parameterDefinitions=lambda: [source])
    with pytest.raises(ValueError, match='not a layer of the project'):
        tools._parameters(algorithm, {})


def test_extra_command_line_options_are_never_forwarded(project):
    algorithm = SimpleNamespace(id=lambda: 'gdal:example', parameterDefinitions=lambda: [
        definition('EXTRA', 'string', optional=True)])
    with pytest.raises(ValueError, match='command-line'):
        tools._parameters(algorithm, {'EXTRA': '-sql dangerous'})
    assert tools._parameters(algorithm, {})[0] == {'EXTRA': None}


def test_inactive_and_unavailable_providers_are_not_executable(project):
    provider = SimpleNamespace(id=lambda: 'custom', isActive=lambda: False)
    algorithm = SimpleNamespace(id=lambda: 'custom:example', provider=lambda: provider, flags=lambda: 0,
                                parameterDefinitions=lambda: [definition('OUTPUT', 'sink')])
    assert 'not active' in tools._why_not(algorithm)
    provider.isActive = lambda: True
    algorithm.canExecute = lambda: (False, 'Missing external executable')
    assert tools._why_not(algorithm) == 'Missing external executable'


def test_provider_scratch_environment_is_restored_after_failure(tmp_path):
    previous = {key: os.environ.get(key) for key in ('TMPDIR', 'TMP', 'TEMP')}
    previous_python = tempfile.tempdir
    with pytest.raises(RuntimeError, match='provider failure'):
        with tools._working_folder(str(tmp_path)):
            assert tempfile.gettempdir() == str(tmp_path)
            assert all(os.environ[key] == str(tmp_path) for key in previous)
            raise RuntimeError('provider failure')
    assert tempfile.tempdir == previous_python
    assert {key: os.environ.get(key) for key in previous} == previous
