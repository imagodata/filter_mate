# -*- coding: utf-8 -*-
"""The options of FilterMate's panels read and set as the panel does (adapters/public_api/panel_options.py).

The module is loaded for real under a synthetic package; the dock is a stand-in with what the module touches, the
layers plain objects, and the few reads of QGIS (vector or not, an expression, a CRS, the formats, the project file)
are replaced per test.
"""
import importlib
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_panel_options_test"


def _load():
    for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                       (".core.domain", _ROOT / "core" / "domain"), (".adapters", _ROOT / "adapters"),
                       (".adapters.public_api", _ROOT / "adapters" / "public_api")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.public_api.panel_options")


panel_options = _load()


class _Layer:
    def __init__(self, layer_id, name, vector=True):
        self._id, self._name, self.vector = layer_id, name, vector

    def id(self):
        return self._id

    def name(self):
        return self._name


COMMUNES, ROUTES, MNT = _Layer("communes_a1", "communes"), _Layer("routes_c3", "routes"), _Layer("mnt_f6", "mnt", False)


def _props():
    return {"exploring": {"single_selection_expression": '"fid"', "multiple_selection_expression": '"fid"',
                          "custom_selection_expression": '"fid"', "current_exploring_groupbox": "single_selection",
                          "is_tracking": False, "is_linking": False, "is_selecting": False},
            "filtering": {"has_layers_to_filter": False, "layers_to_filter": [], "has_buffer_value": False,
                          "buffer_value": 0.0}}


@pytest.fixture
def project():
    layers = {layer.id(): layer for layer in (COMMUNES, ROUTES, MNT)}
    return SimpleNamespace(mapLayers=lambda: dict(layers), mapLayer=layers.get)


@pytest.fixture
def dock():
    exporting = {"HAS_LAYERS_TO_EXPORT": False, "LAYERS_TO_EXPORT": [], "HAS_DATATYPE_TO_EXPORT": False,
                 "DATATYPE_TO_EXPORT": "GPKG", "BATCH_ZIP": False}
    calls = MagicMock()
    has = {key: {"WIDGET": MagicMock()} for key in ("HAS_LAYERS_TO_EXPORT", "HAS_PROJECTION_TO_EXPORT",
                                                     "HAS_STYLES_TO_EXPORT", "HAS_DATATYPE_TO_EXPORT",
                                                     "HAS_OUTPUT_FOLDER_TO_EXPORT", "HAS_ZIP_TO_EXPORT")}
    dock = SimpleNamespace(
        calls=calls, widgets={"EXPORTING": has},
        current_layer_changed=calls.current_layer_changed, resettingLayerVariable=MagicMock(),
        exporting_populate_combobox=calls.exporting_populate_combobox,
        widgets_initialized=True, current_layer=None,
        PROJECT_LAYERS={COMMUNES.id(): _props(), ROUTES.id(): _props()},
        settingLayerVariable=MagicMock(), _synchronize_layer_widgets=MagicMock(),
        _reset_exploring_button_states=MagicMock(), _reset_filtering_button_states=MagicMock(),
        project_props={"EXPORTING": exporting}, CONFIG_DATA={"CURRENT_PROJECT": {"EXPORTING": exporting}},
        setProjectVariablesEvent=calls.setProjectVariablesEvent, set_exporting_properties=calls.set_exporting_properties)
    return dock


@pytest.fixture(autouse=True)
def qgis_reads(monkeypatch):
    monkeypatch.setattr(panel_options, "_is_vector", lambda layer: layer.vector)
    monkeypatch.setattr(panel_options, "_is_listed_target", lambda layer: False)
    monkeypatch.setattr(panel_options, "_expression_problem",
                        lambda layer, text: "unknown field nmo" if "nmo" in text else "")
    monkeypatch.setattr(panel_options, "_crs_problem", lambda value: "")
    monkeypatch.setattr(panel_options, "_driver_map", lambda: {"GPKG": "GPKG", "GEOJSON": "GeoJSON", "JSON": "GeoJSON",
                                                               "SHP": "ESRI Shapefile"})
    monkeypatch.setattr(panel_options, "_field_names", lambda layer: ["fid", "nom", "insee"])
    monkeypatch.setattr(panel_options, "_project_saved", lambda: True)


def test_current_layer_is_saved_and_shown(dock, project):
    dock.current_layer = COMMUNES
    answer = panel_options.set_layer_options(
        dock, [{"layer": "communes", "exploring": {"single_selection_expression": '"nom"'}}], project=project)
    assert dock.PROJECT_LAYERS[COMMUNES.id()]["exploring"]["single_selection_expression"] == '"nom"'
    dock.settingLayerVariable.emit.assert_called_once_with(COMMUNES, [("exploring", "single_selection_expression")])
    dock.current_layer_changed.assert_called_once_with(COMMUNES, manual_change=True)
    dock._reset_filtering_button_states.assert_not_called()  # it empties the predicates and the buffer
    assert answer == {"changed": [{"layer_name": "communes", "exploring": {"single_selection_expression": '"nom"'}}],
                      "shown_in_panel": True}


def test_other_layer_is_saved_not_shown(dock, project):
    dock.current_layer = ROUTES
    answer = panel_options.set_layer_options(dock, [{"layer": "communes", "exploring": {"is_tracking": True}}],
                                             project=project)
    dock.settingLayerVariable.emit.assert_called_once_with(COMMUNES, [("exploring", "is_tracking")])
    dock.current_layer_changed.assert_not_called()
    assert answer["shown_in_panel"] is False


def test_nothing_written_when_one_layer_is_wrong(dock, project):
    with pytest.raises(ValueError, match="communes: custom_selection_expression: unknown field nmo"):
        panel_options.set_layer_options(
            dock, [{"layer": "routes", "exploring": {"is_tracking": True}},
                   {"layer": "communes", "exploring": {"custom_selection_expression": '"nmo"'}}], project=project)
    dock.settingLayerVariable.emit.assert_not_called()
    assert dock.PROJECT_LAYERS[ROUTES.id()]["exploring"]["is_tracking"] is False


@pytest.mark.parametrize("layers, message", [
    ([], "one layer at least"),
    ([{"layer": "communes"}] * 51, "at most 50 layers"),
    ([{"layer": "nowhere", "exploring": {"is_tracking": True}}], "No layer nowhere"),
    ([{"layer": "mnt", "exploring": {"is_tracking": True}}], "mnt: only a vector layer has these options"),
])
def test_refused_calls(dock, project, layers, message):
    with pytest.raises(ValueError, match=message):
        panel_options.set_layer_options(dock, layers, project=project)


def test_a_layer_the_panel_has_not_read(dock, project):
    del dock.PROJECT_LAYERS[ROUTES.id()]
    with pytest.raises(ValueError, match="FilterMate has not read routes yet"):
        panel_options.layer_options(dock, "routes", project=project)


def test_a_raster_target_the_panel_lists_is_accepted_and_kept(dock, project, monkeypatch):
    """layer_options names the raster the panel keeps among the targets; giving the list back must not refuse it."""
    monkeypatch.setattr(panel_options, "_is_listed_target", lambda layer: layer is MNT)
    dock.PROJECT_LAYERS[COMMUNES.id()]["filtering"]["layers_to_filter"] = [ROUTES.id(), MNT.id()]
    seen = panel_options.layer_options(dock, "communes", project=project)["filtering"]["layers_to_filter"]
    assert seen == ["routes", "mnt"]
    answer = panel_options.set_layer_options(
        dock, [{"layer": "communes", "filtering": {"layers_to_filter": seen}}], project=project)
    assert dock.PROJECT_LAYERS[COMMUNES.id()]["filtering"]["layers_to_filter"] == [ROUTES.id(), MNT.id()]
    assert answer["changed"][0]["filtering"]["layers_to_filter"] == ["routes", "mnt"]


def test_a_raster_the_panel_does_not_list_is_still_refused(dock, project):
    with pytest.raises(ValueError, match="communes: layers_to_filter: mnt is not a vector layer"):
        panel_options.set_layer_options(
            dock, [{"layer": "communes", "filtering": {"layers_to_filter": ["routes", "mnt"]}}], project=project)
    assert dock.PROJECT_LAYERS[COMMUNES.id()]["filtering"]["layers_to_filter"] == []


def test_layer_options_name_the_layers_to_filter(dock, project):
    dock.PROJECT_LAYERS[COMMUNES.id()]["filtering"]["layers_to_filter"] = [ROUTES.id()]
    answer = panel_options.layer_options(dock, "communes", project=project)
    assert answer["filtering"]["layers_to_filter"] == ["routes"]
    assert "is_selecting" not in answer["exploring"] and answer["layer_id"] == COMMUNES.id()
    assert answer["choices"]["combine_operators"] == ["AND", "AND NOT", "OR"]


def test_export_options_are_saved_and_shown(dock, project, tmp_path):
    answer = panel_options.set_export_options(
        dock, {"layers_to_export": ["communes"], "output_folder_to_export": str(tmp_path)}, project=project)
    exporting = dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"]
    assert exporting["LAYERS_TO_EXPORT"] == [COMMUNES.id()] and exporting["HAS_OUTPUT_FOLDER_TO_EXPORT"] is True
    assert exporting is dock.project_props["EXPORTING"]
    names = [call[0] for call in dock.calls.mock_calls]
    assert names == ["exporting_populate_combobox", "set_exporting_properties", "setProjectVariablesEvent"]
    dock.widgets["EXPORTING"]["HAS_LAYERS_TO_EXPORT"]["WIDGET"].setChecked.assert_called_with(True)
    dock.widgets["EXPORTING"]["HAS_OUTPUT_FOLDER_TO_EXPORT"]["WIDGET"].setChecked.assert_called_with(True)
    assert answer["changed"]["output_folder_to_export"] == str(tmp_path) and answer["saved"] is True


def test_export_folder_must_exist(dock, project, tmp_path):
    with pytest.raises(ValueError, match="output_folder_to_export: no such folder"):
        panel_options.set_export_options(dock, {"output_folder_to_export": str(tmp_path / "nope")}, project=project)
    dock.setProjectVariablesEvent.assert_not_called()


def test_export_options_say_when_not_saved(dock, project, monkeypatch):
    monkeypatch.setattr(panel_options, "_project_saved", lambda: False)
    answer = panel_options.set_export_options(dock, {"batch_zip": True}, project=project)
    assert answer["saved"] is False and "once the project is saved" in answer["note"]


def test_export_options_read_with_names(dock, project):
    dock.project_props["EXPORTING"]["LAYERS_TO_EXPORT"] = [ROUTES.id()]
    answer = panel_options.export_options(dock, project=project)
    assert answer["layers_to_export"] == ["routes"] and answer["datatype_to_export"] == "GPKG"
    assert answer["formats"] == ["ESRI Shapefile", "GPKG", "GeoJSON"] and answer["saved"] is True


def test_no_panel():
    assert "Open the FilterMate panel first" in panel_options.dock_problem(None)
    assert "Open the FilterMate panel first" in panel_options.dock_problem(SimpleNamespace(widgets_initialized=False))
    with pytest.raises(ValueError, match="Open the FilterMate panel first"):
        panel_options.export_options(None)


# --- what the turn keeps to undo them (adapters/agent/turn_effects.py) ------------------------------------------------

def test_layer_state_keeps_only_the_options_an_agent_sets(dock):
    dock.PROJECT_LAYERS[COMMUNES.id()]["filtering"]["layers_to_filter"] = [ROUTES.id()]
    state = panel_options.layer_state(dock, COMMUNES.id())
    assert "is_selecting" not in state["exploring"] and state["filtering"]["layers_to_filter"] == [ROUTES.id()]
    assert panel_options.layer_state(dock, "gone") is None and panel_options.layer_state(None, COMMUNES.id()) is None


def _undo_of(before, after):
    from core.agent.panel_options import state_change
    return state_change(before, after)[0]


def test_layer_state_restored_as_the_panel_saves_it(dock, project):
    before = panel_options.layer_state(dock, COMMUNES.id())
    dock.current_layer = COMMUNES
    panel_options.set_layer_options(dock, [{"layer": "communes", "exploring": {"single_selection_expression": '"nom"'}}],
                                    project=project)
    dock.settingLayerVariable.emit.reset_mock()
    dock.current_layer_changed.reset_mock()
    undo = _undo_of(before, panel_options.layer_state(dock, COMMUNES.id()))
    assert panel_options.restore_layer_state(dock, COMMUNES.id(), undo, project=project) is True
    assert dock.PROJECT_LAYERS[COMMUNES.id()]["exploring"]["single_selection_expression"] == '"fid"'
    dock.settingLayerVariable.emit.assert_called_once_with(COMMUNES, [("exploring", "single_selection_expression")])
    dock.current_layer_changed.assert_called_once_with(COMMUNES, manual_change=True)
    assert panel_options.restore_layer_state(dock, "gone", undo, project=project) is False


def test_export_state_restored(dock, project):
    before = {"EXPORTING": panel_options.export_state(dock)}
    panel_options.set_export_options(dock, {"datatype_to_export": "GeoJSON"}, project=project)
    dock.calls.reset_mock()
    undo = _undo_of(before, {"EXPORTING": panel_options.export_state(dock)})
    assert panel_options.restore_export_state(dock, undo) is True
    assert dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"]["DATATYPE_TO_EXPORT"] == "GPKG"
    assert dock.CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"]["HAS_DATATYPE_TO_EXPORT"] is False
    assert [call[0] for call in dock.calls.mock_calls][-1] == "setProjectVariablesEvent"
    assert panel_options.export_state(None) is None and panel_options.restore_export_state(None, undo) is False


def test_a_restored_state_is_the_one_kept(dock, project):
    before = panel_options.layer_state(dock, COMMUNES.id())
    panel_options.set_layer_options(dock, [{"layer": "communes", "filtering": {"geometric_predicates": ["Intersect"]}}],
                                    project=project)
    undo = _undo_of(before, panel_options.layer_state(dock, COMMUNES.id()))
    panel_options.restore_layer_state(dock, COMMUNES.id(), undo, project=project)
    assert panel_options.layer_state(dock, COMMUNES.id()) == before
    dock.resettingLayerVariable.emit.assert_called_once_with(
        COMMUNES, [("filtering", "geometric_predicates"), ("filtering", "has_geometric_predicates")])


def test_nothing_to_save_emits_nothing(dock, project):
    """An empty list of keys tells FilterMate to save every option of the layer."""
    panel_options.restore_layer_state(dock, COMMUNES.id(), {"values": {}, "absent": []}, project=project)
    dock.settingLayerVariable.emit.assert_not_called()


def test_the_answer_is_what_the_panel_keeps(dock, project):
    """The panel resets a group whose box is unticked: the answer says what it holds, not what was asked."""
    def panel_resets_datatype():
        dock.project_props["EXPORTING"]["DATATYPE_TO_EXPORT"] = "GPKG"
    dock.set_exporting_properties = panel_resets_datatype
    answer = panel_options.set_export_options(dock, {"datatype_to_export": "GeoJSON", "has_datatype_to_export": False},
                                              project=project)
    assert answer["changed"]["datatype_to_export"] == "GPKG"


@pytest.mark.parametrize("value, stored", [("SHP", "ESRI Shapefile"), ("geojson", "GeoJSON"), ("GPKG", "GPKG")])
def test_formats_are_stored_as_the_panel_names_them(dock, project, value, stored):
    panel_options.set_export_options(dock, {"datatype_to_export": value}, project=project)
    assert dock.project_props["EXPORTING"]["DATATYPE_TO_EXPORT"] == stored


@pytest.mark.parametrize("value", ["DXF", ["GPKG"], {"a": 1}, 3])
def test_a_wrong_format_is_refused_not_crashed(dock, project, value):
    with pytest.raises(ValueError, match="datatype_to_export"):
        panel_options.set_export_options(dock, {"datatype_to_export": value}, project=project)


def test_single_and_multiple_selection_take_a_field(dock, project):
    """2026-11-16, review: the panel puts back its key field when either is not a field of the layer."""
    with pytest.raises(ValueError, match="single_selection_expression: a field of the layer"):
        panel_options.set_layer_options(
            dock, [{"layer": "communes", "exploring": {"single_selection_expression": '"nom" || "insee"'}}],
            project=project)
    panel_options.set_layer_options(dock, [{"layer": "communes", "exploring": {
        "multiple_selection_expression": "insee", "custom_selection_expression": '"nom" || \' (\' || "insee" || \')\''}}],
        project=project)
    assert dock.PROJECT_LAYERS[COMMUNES.id()]["exploring"]["multiple_selection_expression"] == "insee"
