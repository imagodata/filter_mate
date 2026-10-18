# -*- coding: utf-8 -*-
"""
FilterMate 5 dock additions (mockup): layer card, kind tools and source
geometry line - the pure text builders of ``coverage_dock_extras`` and the
zone statistics of the raster panel.

Loaded by path under a private synthetic package, like the coverage widget
tests: the real domain modules are used, Qt / QGIS resolve to the root mocks.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_cov_extras_test"


def _load_modules():
    for name, path in (
        ("", _ROOT),
        (".core", _ROOT / "core"),
        (".core.domain", _ROOT / "core" / "domain"),
        (".ui", _ROOT / "ui"),
        (".ui.controllers", _ROOT / "ui" / "controllers"),
        (".ui.widgets", _ROOT / "ui" / "widgets"),
        (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels"),
    ):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        sys.modules[_PKG + name] = package
    return (
        importlib.import_module(f"{_PKG}.ui.controllers.coverage_dock_extras"),
        importlib.import_module(f"{_PKG}.ui.widgets.coverage_panels.raster_exploring_panel"),
    )


extras, raster = _load_modules()


class TestNumbers:
    def test_trailing_zeros_are_dropped(self):
        assert extras.format_number(1.0) == "1"
        assert extras.format_number(0.5) == "0.5"
        assert extras.format_number(141.84) == "141.84"
        assert extras.format_number(-99999.0, 3) == "-99999"

    def test_rounding_to_zero_has_no_sign(self):
        assert extras.format_number(-0.001) == "0"

    def test_invalid_values_give_an_empty_text(self):
        assert extras.format_number(None) == ""
        assert extras.format_number(float("nan")) == ""
        assert extras.format_number("abc") == ""


class TestPixelSize:
    def test_square_pixel(self):
        assert extras.pixel_size_text(1.0, 1.0, "m") == "1 m"

    def test_rectangular_pixel(self):
        assert extras.pixel_size_text(0.5, 0.25, "m") == "0.5 × 0.25 m"
        assert extras.pixel_size_text(0.125, 0.125, "m") == "0.125 m"

    def test_geographic_pixel_keeps_six_decimals(self):
        assert extras.pixel_size_text(0.000278, 0.000278, "°") == "0.000278 °"

    def test_unknown_size(self):
        assert extras.pixel_size_text(0.0, 1.0, "m") == ""
        assert extras.pixel_size_text(None, 1.0) == ""

    def test_no_unit(self):
        assert extras.pixel_size_text(5.0, 5.0) == "5"


class TestRasterCard:
    def test_single_band_dtm(self):
        text = extras.raster_card_text([("Float32", -99999.0)], 1.0, 1.0, "m")
        assert text == "1 band · Float32 · 1 m · NoData -99999"

    def test_rgb_without_nodata(self):
        text = extras.raster_card_text([("Byte", None)] * 3, 0.2, 0.2, "m")
        assert text == "3 bands · Byte · 0.2 m"

    def test_mixed_data_types(self):
        text = extras.raster_card_text([("Byte", None), ("Float32", None)], 1.0, 1.0)
        assert text == "2 bands · Byte / Float32 · 1"

    def test_translation_function_is_used(self):
        text = extras.raster_card_text([("Byte", None)], 1.0, 1.0, "m", translate=lambda t: t.replace("band", "bande"))
        assert text.startswith("1 bande")


class TestPointCloudCard:
    def test_count_and_elevation(self):
        assert extras.point_cloud_card_text(38_400_000, (141.8, 318.7)) == "38.4 M points · Z 141.8 → 318.7"

    def test_unknown_count(self):
        assert extras.point_cloud_card_text(-1, (0.0, 12.5)) == "Z 0 → 12.5"

    def test_nothing_known(self):
        assert extras.point_cloud_card_text(None, None) == ""


class TestTools:
    def test_raster_rail_adds_the_pipette_the_detector_the_style_link_and_more(self):
        # Zoom, preview and reset are the shared buttons; the pipette and the object detector are the two
        # tools of the PIPETTE group, the style link the tool of VALUE RANGE; hover and statistics live in
        # the "more" menu (seven buttons, like the point cloud rail).
        assert extras.tools_for("raster") == ["pushButton_checkable_exploring_raster_pipette",
                                              "pushButton_checkable_exploring_raster_detector",
                                              "pushButton_checkable_exploring_raster_similar",
                                              "pushButton_checkable_exploring_raster_link",
                                              "pushButton_exploring_raster_more"]

    def test_the_three_pipette_targets_have_a_button(self):
        assert set(extras.CoverageDockExtras.PIPETTE_BUTTONS) == {"similar", "object", "similar_objects"}
        assert extras.ICON_SIMILAR.strip().startswith("<")

    def test_point_cloud_rail_adds_the_detector_the_value_pipette_the_zone_and_more(self):
        # 2026-10-18: Identify is the class pipette and the object detector the other tool of CLASSES; the value
        # pipette and the zone are the tools of ATTRIBUTES; profile and 3D view are in the "more" menu.
        assert extras.tools_for("point_cloud") == ["pushButton_checkable_exploring_point_cloud_object",
                                                   "pushButton_checkable_exploring_point_cloud_value_pipette",
                                                   "pushButton_checkable_exploring_point_cloud_zone",
                                                   "pushButton_exploring_point_cloud_more"]

    def test_the_rails_have_about_the_same_size(self):
        shared_raster = 3  # zoom, preview, reset (Identify hidden)
        shared_point_cloud = 4  # identify (class pipette), zoom, preview, reset
        shared_vector = 6  # identify, zoom, select, track, link, reset
        raster = shared_raster + len(extras.tools_for("raster"))
        point_cloud = shared_point_cloud + len(extras.tools_for("point_cloud"))
        vector = shared_vector + len(extras.tools_for("vector"))
        assert raster == 8 and point_cloud == 8 and vector == 8

    def test_detector_has_its_own_icon(self):
        assert extras.ICON_DETECTOR.strip().startswith("<") and extras.ICON_DETECTOR != extras.ICON_PIPETTE

    def test_vector_rail_adds_the_similar_features_tool_and_more(self):
        # 2026-10-18: the similar features tool (single / multiple selections) and the "more" menu
        # (the QGIS selection tools and actions).
        assert extras.tools_for("vector") == ["pushButton_checkable_exploring_vector_similar",
                                              "pushButton_exploring_vector_more"]

    def test_the_vector_menu_runs_the_qgis_selection_tools(self):
        assert [key for key, _names in extras.VECTOR_SELECT_TOOLS] == ["rectangle", "polygon", "freehand", "radius"]
        for _key, names in extras.VECTOR_SELECT_TOOLS:
            assert all(name.startswith("mActionSelect") for name in names)

    def test_names_match_the_dock_style_selectors(self):
        for kind in ("raster", "point_cloud", "vector"):
            for name in extras.tools_for(kind):
                assert name.startswith(("pushButton_exploring_", "pushButton_checkable_exploring_"))

    def test_every_tool_has_an_icon(self):
        assert all(body.strip().startswith("<") for body in (extras.ICON_HOVER, extras.ICON_ZONE, extras.ICON_LINK_STYLE,
                                                            extras.ICON_PIPETTE, extras.ICON_PROFILE, extras.ICON_3D,
                                                            extras.ICON_VALUE_PIPETTE, extras.ICON_PC_ZONE, extras.ICON_MORE))


class TestZone:
    def test_pixel_estimate(self):
        assert extras.zone_pixel_estimate(100.0, 50.0, 1.0, 1.0) == 5000
        assert extras.zone_pixel_estimate(100.0, 50.0, 0.0, 1.0) is None

    def test_statistics_text(self):
        text = raster.format_zone_statistics(198.4, 251.07, 221.3, 12450, 3)
        assert text == "min 198.400 · max 251.070 · mean 221.300 · 12450 px"

    def test_integer_band_mean_keeps_one_decimal(self):
        assert raster.format_zone_statistics(2.0, 9.0, 4.25, None, 0) == "min 2 · max 9 · mean 4.2"

    def test_empty_zone(self):
        assert raster.format_zone_statistics(None, None, None, 0, 3) == ""


def test_svg_document_carries_the_color():
    document = extras._svg_document(extras.ICON_3D, "#e0e0e0")
    assert 'stroke="#e0e0e0"' in document and document.endswith("</svg>")


def test_3d_action_tries_the_qgis_4_name_first():
    assert extras.ACTION_NEW_3D_VIEW[0] == "mActionNew3DMapCanvas"
    assert "mActionNew3DMapView" in extras.ACTION_NEW_3D_VIEW
    assert extras.ACTION_ELEVATION_PROFILE == ("mActionElevationProfile",)


def test_float32_nodata_is_short():
    text = extras.raster_card_text([("Float32", -3.4028234663852886e38)], 1.0, 1.0, "m")
    assert text.endswith("NoData -3.40282e+38")


def test_nan_nodata_is_left_out():
    assert "NoData" not in extras.raster_card_text([("Float32", float("nan"))], 1.0, 1.0, "m")


class TestVectorCard:
    def test_geometry_and_count(self):
        assert extras.vector_card_text("Line", 12438) == "Line · 12 438 features"

    def test_unknown_count(self):
        assert extras.vector_card_text("Polygon", -1) == "Polygon"
        assert extras.vector_card_text("", None) == ""

    def test_card_html_escapes_and_colors(self):
        html = extras.card_html("a<b", "Vector", "Line", "#6fb1f0", square=False)
        assert "a&lt;b" in html and "#6fb1f0" in html and "●" in html and "Vector · Line" in html
        assert "■" in extras.card_html("mnt", "Raster", "", "#f0b35a", square=True)


# ---------------------------------------------------------------------------
# Dock additions with a fake controller (audit fixes)
# ---------------------------------------------------------------------------

class FakeLayer:
    def __init__(self, layer_id, provider="ogr", subset="", source=None):
        self._id, self._provider, self._subset = layer_id, provider, subset
        self._source = source or f"/data/{layer_id}.tif"
        self.counted = 0

    def id(self):
        return self._id

    def name(self):
        return self._id

    def source(self):
        return self._source

    def providerType(self):
        return self._provider

    def subsetString(self):
        return self._subset

    def featureCount(self):
        self.counted += 1
        return 12

    def geometryType(self):
        return 0


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        self.slots.remove(slot)


class FakeButton:
    """Checkable button: ``setChecked`` runs the toggled slot like Qt."""

    def __init__(self, slot):
        self.checked, self.slot = False, slot

    def isChecked(self):
        return self.checked

    def setChecked(self, checked):
        if checked != self.checked:
            self.checked = checked
            self.slot(checked)

    def setVisible(self, _visible):
        pass

    def setParent(self, _parent):
        pass

    def deleteLater(self):
        pass


class FakePanel:
    def __init__(self):
        self.selectionChanged = FakeSignal()
        self.hover = []

    def selection(self):
        return None

    def _data_bounds(self):
        return 0.0, 10.0

    def current_band(self):
        return 1

    def current_derivative(self):
        return types.SimpleNamespace(is_terrain=False, value="value")

    def set_hover_value(self, x, y, value=None, derived=None):
        self.hover.append(value)


class FakeController:
    def __init__(self, layers):
        self.layers = layers
        self.active_layer = None
        self._raster_panel = FakePanel()
        self.dockwidget = types.SimpleNamespace()
        self.based = []

    def _map_layer(self, layer_id):
        return self.layers.get(layer_id)

    def _iface(self):
        return None

    def _base_raster(self, layer):
        self.based.append(layer.source())
        return layer


@pytest.fixture
def dock_extras(monkeypatch):
    """A CoverageDockExtras on a fake controller; the raster adapter is a recording stub."""
    for name in (".adapters", ".adapters.qgis", ".adapters.qgis.coverage_layers"):
        package = types.ModuleType(_PKG + name)
        package.__path__ = []
        monkeypatch.setitem(sys.modules, _PKG + name, package)
    adapter = types.ModuleType(f"{_PKG}.adapters.qgis.coverage_layers.raster_adapter")
    adapter.calls = []
    adapter.link_range_to_style = lambda layer, band, low, high: adapter.calls.append(("link", layer.id())) or True
    adapter.unlink_range_from_style = lambda layer: adapter.calls.append(("unlink", layer.id())) or True
    adapter.forget_linked_styles = lambda ids=None: adapter.calls.append(("forget", ids))
    adapter.unlink_all_styles = lambda project=None: adapter.calls.append(("unlink_all",)) or 0
    adapter.identify_values = lambda layer, point: {1: 3.0}
    monkeypatch.setitem(sys.modules, adapter.__name__, adapter)
    monkeypatch.setattr(extras.CoverageDockExtras, "_refresh_icons", lambda self: None)
    monkeypatch.setattr(extras.CoverageDockExtras, "_set_kind_icons", lambda self, kind: None)
    layers = {lid: FakeLayer(lid) for lid in ("r1", "r2")}
    controller = FakeController(layers)
    dock = extras.CoverageDockExtras(controller)
    link = FakeButton(dock._on_link_toggled)
    dock._tools = {"pushButton_checkable_exploring_raster_link": link}
    return types.SimpleNamespace(dock=dock, controller=controller, adapter=adapter, layers=layers, link=link)


class FakeDockButton(FakeButton):
    """A dock button with an enabled state and a tooltip."""

    def __init__(self, slot=lambda checked: None, tip="Link"):
        super().__init__(slot)
        self.enabled, self.tip, self.blocked = True, tip, False

    def blockSignals(self, block):
        self.blocked = block

    def setChecked(self, checked):
        if checked != self.checked:
            self.checked = checked
            if not self.blocked:
                self.slot(checked)

    def setEnabled(self, enabled):
        self.enabled = enabled

    def isEnabled(self):
        return self.enabled

    def setToolTip(self, tip):
        self.tip = tip

    def toolTip(self):
        return self.tip


class TestVectorToolsFollowTheGroup:
    """R1 on the vector rail: Link and the similar features tool belong to the single / multiple selections."""

    def _dock(self, dock_extras):
        dock = dock_extras.dock
        dock.tr = lambda text, *_args: text  # the QObject stub of the tests has no translation
        link = FakeDockButton(tip="Link the single and multiple selections")
        dock.dockwidget.pushButton_checkable_exploring_linking_widgets = link
        stopped = []
        dock._stop_vector_similar_tool = lambda: stopped.append(True)
        dock._start_vector_similar_tool = lambda: None
        dock.dockwidget.pushButton_checkable_exploring_selecting = FakeDockButton()
        similar = FakeDockButton(dock._on_vector_similar_toggled)
        dock._tools["pushButton_checkable_exploring_vector_similar"] = similar
        return dock, link, similar, stopped

    def test_custom_selection_disables_link_and_keeps_its_check(self, dock_extras):
        dock, link, similar, _stopped = self._dock(dock_extras)
        link.checked = True
        dock.sync_vector_tools("custom_selection")
        assert not link.isEnabled() and link.isChecked()
        assert "single and multiple" in link.toolTip() and "active group" in link.toolTip()
        assert not similar.isEnabled()

    def test_single_and_multiple_give_the_tools_back_with_their_tooltip(self, dock_extras):
        dock, link, similar, _stopped = self._dock(dock_extras)
        dock.sync_vector_tools("custom_selection")
        dock.sync_vector_tools("multiple_selection")
        assert link.isEnabled() and link.toolTip() == "Link the single and multiple selections"
        assert similar.isEnabled()
        dock.sync_vector_tools("single_selection")
        assert link.isEnabled() and similar.isEnabled()

    def test_custom_selection_takes_the_similar_tool_off_the_map(self, dock_extras):
        dock, _link, similar, stopped = self._dock(dock_extras)
        similar.setChecked(True)
        assert dock.dockwidget.pushButton_checkable_exploring_selecting.isChecked()  # R2: the mode goes on
        dock.sync_vector_tools("custom_selection")
        assert not similar.isChecked() and stopped == [True]

    def test_qgis_dropping_the_tool_releases_the_button_only(self, dock_extras):
        dock, _link, similar, stopped = self._dock(dock_extras)
        similar.setChecked(True)
        dock._on_vector_similar_tool_deactivated()
        assert not similar.isChecked() and stopped == []  # R5: no stop (QGIS already took the tool)


class TestRangeLinkedToStyle:
    """Constat 4: the style is given back to the raster that was linked, never to the next one."""

    def _link_r1(self, env):
        env.controller.active_layer = env.layers["r1"]
        env.dock.show_for(env.layers["r1"], "raster")
        env.link.setChecked(True)
        assert ("link", "r1") in env.adapter.calls

    def test_a_colour_selection_keeps_the_stretch(self, dock_extras):
        env = dock_extras
        env.controller._raster_panel.selection = lambda: types.SimpleNamespace(mode=types.SimpleNamespace(value="expression"))
        env.controller.active_layer = env.layers["r1"]
        env.dock.show_for(env.layers["r1"], "raster")
        env.link.setChecked(True)
        assert not [c for c in env.adapter.calls if c[0] == "link"]

    def test_an_empty_pipette_keeps_the_stretch(self, dock_extras):
        env = dock_extras
        env.controller._raster_panel.active_mode = lambda: types.SimpleNamespace(value="pipette")
        env.controller.active_layer = env.layers["r1"]
        env.dock.show_for(env.layers["r1"], "raster")
        env.link.setChecked(True)
        assert not [c for c in env.adapter.calls if c[0] == "link"]

    def test_switching_raster_unlinks_the_outgoing_one(self, dock_extras):
        self._link_r1(dock_extras)
        dock_extras.controller.active_layer = dock_extras.layers["r2"]  # the controller moves first
        dock_extras.dock.show_for(dock_extras.layers["r2"], "raster")
        assert [c for c in dock_extras.adapter.calls if c[0] == "unlink"] == [("unlink", "r1")]
        assert not dock_extras.link.isChecked()

    def test_switching_to_a_vector_unlinks_the_raster(self, dock_extras):
        self._link_r1(dock_extras)
        dock_extras.controller.active_layer = None  # deactivated before show_vector
        dock_extras.dock.show_vector(None)
        assert [c for c in dock_extras.adapter.calls if c[0] == "unlink"] == [("unlink", "r1")]

    def test_removed_layer_style_is_forgotten_not_restored(self, dock_extras):
        self._link_r1(dock_extras)
        dock_extras.dock.forget_layers(["r1"])
        assert ("forget", ["r1"]) in dock_extras.adapter.calls
        assert not [c for c in dock_extras.adapter.calls if c[0] == "unlink"]
        assert not dock_extras.link.isChecked()

    def test_removed_layer_card_is_hidden(self, dock_extras):
        shown = []
        dock_extras.dock._card = types.SimpleNamespace(setVisible=shown.append)
        dock_extras.dock.show_vector(None)  # the raster shown was removed: no vector layer to describe yet
        assert shown == [False]

    def test_closed_project_forgets_every_style(self, dock_extras):
        self._link_r1(dock_extras)
        dock_extras.dock.forget_layers(None)
        assert ("forget", None) in dock_extras.adapter.calls and dock_extras.dock._linked_layer_id is None

    def test_teardown_gives_every_style_back(self, dock_extras):
        self._link_r1(dock_extras)
        dock_extras.controller.active_layer = None  # the controller deactivates before the additions
        dock_extras.dock.teardown()
        assert ("unlink", "r1") in dock_extras.adapter.calls and ("unlink_all",) in dock_extras.adapter.calls


class TestVectorCardCount:
    """Constat 13: no count(*) on the main thread for a database / web layer or a filtered one."""

    def test_cheap_counts(self):
        assert extras.feature_count_is_cheap("ogr", "")
        assert not extras.feature_count_is_cheap("ogr", '"zone" = 3')
        assert not extras.feature_count_is_cheap("postgres", "")
        assert not extras.feature_count_is_cheap("wfs", "")

    def test_web_providers_are_matched_whatever_their_case(self):
        """QGIS names them 'WFS' and 'OAPIF': the lower-case list used to let them count on the main thread."""
        for provider in ("WFS", "OAPIF", "oapif", "ArcGISFeatureServer", "sensorthings", "MSSQL"):
            assert not extras.feature_count_is_cheap(provider, ""), provider

    def test_card_counts_local_unfiltered_layers_only(self, dock_extras, monkeypatch):
        monkeypatch.setattr(sys.modules["qgis.core"], "QgsWkbTypes",
                            types.SimpleNamespace(geometryDisplayString=lambda geometry_type: "Polygon"), raising=False)
        dock_extras.dock.tr = lambda text: text
        layers = (FakeLayer("pg", "postgres"), FakeLayer("gpkg", "ogr", subset='EXISTS (SELECT 1)'), FakeLayer("shp"))
        texts = [dock_extras.dock._vector_meta(layer) for layer in layers]
        assert [layer.counted for layer in layers] == [0, 0, 1]
        assert texts == ["Polygon", "Polygon", "Polygon · 12 features"]


def test_value_under_the_cursor_reads_the_new_source_after_a_filter(dock_extras):
    """Constat 17: the raster opened for the hover follows a source change of the layer."""
    env = dock_extras
    layer = env.layers["r1"]
    env.controller.active_layer = layer
    env.dock._hover_point = types.SimpleNamespace(x=lambda: 1.0, y=lambda: 2.0)
    env.dock._read_hover_value()
    env.dock._read_hover_value()
    layer._source = "/cache/r1_cut.vrt"
    env.dock._read_hover_value()
    assert env.controller.based == ["/data/r1.tif", "/cache/r1_cut.vrt"]


class TestPointCloudObjectDetector:
    """2026-10-18: the object detector of CLASSES shares the class picker; its button follows the picker mode."""

    def _rail(self, env):
        calls = []
        env.controller._on_object_pick_toggled = lambda on: calls.append(("detector", on))
        env.controller._on_class_pick_toggled = lambda on, mode="class": calls.append(("picker", on))
        identify = FakeDockButton()
        identify.setDown = lambda down: setattr(identify, "down", down)
        identify.isCheckable = lambda: False
        identify.down = False
        env.controller.dockwidget = types.SimpleNamespace(pushButton_exploring_identify=identify)
        detector = FakeDockButton(env.dock._on_pc_object_toggled)
        value = FakeDockButton(env.dock._on_value_pipette_toggled)
        env.controller._on_value_pick_toggled = lambda on: calls.append(("value", on))
        env.dock._tools[extras.PC_OBJECT_BUTTON] = detector
        env.dock._tools["pushButton_checkable_exploring_point_cloud_value_pipette"] = value
        return identify, detector, value, calls

    def test_button_puts_the_detector_on(self, dock_extras):
        _identify, detector, _value, calls = self._rail(dock_extras)
        detector.setChecked(True)
        detector.setChecked(False)
        assert calls == [("detector", True), ("detector", False)]

    @pytest.mark.parametrize("mode, down", [("class", (True, False, False)), ("value", (False, False, True)),
                                            ("object", (False, True, False)), ("similar", (False, True, False))])
    def test_one_button_down_for_the_picker_mode(self, dock_extras, mode, down):
        identify, detector, value, calls = self._rail(dock_extras)
        dock_extras.dock.set_class_pipette_checked(True, mode)
        assert (identify.down, detector.isChecked(), value.isChecked()) == down
        assert calls == []  # signals blocked: the picker is not toggled back
        dock_extras.dock.set_class_pipette_checked(False, mode)
        assert (identify.down, detector.isChecked(), value.isChecked()) == (False, False, False)

    def test_leaving_the_layer_takes_the_detector_off(self, dock_extras):
        _identify, detector, _value, calls = self._rail(dock_extras)
        detector.setChecked(True)
        dock_extras.dock.leave()
        assert calls == [("detector", True), ("detector", False)] and not detector.isChecked()

    def test_detector_follows_the_classes_of_the_layer(self, dock_extras, monkeypatch):
        identify, detector, _value, _calls = self._rail(dock_extras)
        dock_extras.dock.tr = lambda text, *_args: text
        detector.tip = "Object detector: click the map"
        adapter = types.ModuleType(f"{_PKG}.adapters.qgis.point_cloud_layer_adapter")
        adapter.may_have_classes = lambda layer: False
        monkeypatch.setitem(sys.modules, adapter.__name__, adapter)
        dock_extras.dock._class_pipette_tip = "Class pipette"
        dock_extras.dock._class_pipette_enabled(FakeLayer("p1"))
        assert not detector.isEnabled() and "no Classification" in detector.toolTip()
        adapter.may_have_classes = lambda layer: True
        dock_extras.dock._class_pipette_enabled(FakeLayer("p1"))
        assert detector.isEnabled() and detector.toolTip() == "Object detector: click the map"


class TestClassPipette:
    def _pipette(self, env):
        calls = []
        env.controller._on_class_pick_toggled = calls.append
        pipette = FakeButton(env.dock._on_class_pipette_toggled)
        env.dock._tools["pushButton_checkable_exploring_point_cloud_pipette"] = pipette
        return pipette, calls

    def test_button_drives_the_class_picker(self, dock_extras):
        pipette, calls = self._pipette(dock_extras)
        pipette.setChecked(True)
        pipette.setChecked(False)
        assert calls == [True, False]

    def test_leaving_the_layer_takes_the_picker_off_the_map(self, dock_extras):
        pipette, calls = self._pipette(dock_extras)
        pipette.setChecked(True)
        dock_extras.dock.leave()
        assert calls == [True, False] and not pipette.isChecked()


# ---------------------------------------------------------------------------
# Selection strip between EXPLORING and FILTERING
# ---------------------------------------------------------------------------

class FakeStrip:
    def __init__(self):
        self.content = None

    def set_content(self, kind, caption, value, tooltip=""):
        self.content = (kind, caption, value)


class FakeHost:
    def __init__(self):
        self.visible = None

    def setVisible(self, visible):
        self.visible = visible


class FakeFeature:
    def __init__(self, valid):
        self.valid = valid

    def isValid(self):
        return self.valid


def _widget(**methods):
    return types.SimpleNamespace(**{name: (lambda value=value: value) for name, value in methods.items()})


@pytest.fixture
def strip_env(dock_extras, monkeypatch):
    env = dock_extras
    monkeypatch.setattr(extras.CoverageDockExtras, "tr", lambda self, text: text, raising=False)
    env.dock._strip, env.dock._strip_host = FakeStrip(), FakeHost()
    env.controller.dockwidget = types.SimpleNamespace(
        current_layer=FakeLayer("v1"), current_exploring_groupbox="multiple_selection",
        widgets={"EXPLORING": {
            "SINGLE_SELECTION_FEATURES": {"WIDGET": _widget(feature=FakeFeature(True))},
            "MULTIPLE_SELECTION_FEATURES": {"WIDGET": _widget(checkedItems=[["a"], ["b"], ["c"]])},
            "CUSTOM_SELECTION_EXPRESSION": {"WIDGET": _widget(expression='"type" = 2')},
        }})
    return env


class TestSelectionStrip:
    def test_multiple_selection_counts_the_checked_features(self, strip_env):
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content == ("vector", "Selection → source geometry", "3 feature(s)")
        assert strip_env.dock._strip_host.visible is True

    def test_single_selection_reads_its_picker(self, strip_env):
        dw = strip_env.controller.dockwidget
        dw.current_exploring_groupbox = "single_selection"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "1 feature(s)"
        dw.widgets["EXPLORING"]["SINGLE_SELECTION_FEATURES"]["WIDGET"] = _widget(feature=FakeFeature(False))
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "no feature selected"

    def test_custom_selection_uses_the_last_evaluation(self, strip_env):
        dw = strip_env.controller.dockwidget
        dw.current_exploring_groupbox = "custom_selection"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "expression"
        strip_env.dock.note_vector_selection("v1", "custom_selection", 42)
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "42 feature(s)"

    def test_removed_layer_forgets_its_counts(self, strip_env, monkeypatch):
        strip_env.dock.note_vector_selection("v1", "custom_selection", 42)
        strip_env.dock.forget_layers(["v1"])
        assert strip_env.dock._vector_counts == {}

    def test_no_current_layer_hides_the_strip(self, strip_env):
        strip_env.controller.dockwidget.current_layer = None
        strip_env.dock._update_strip()
        assert strip_env.dock._strip_host.visible is False

    def test_raster_strip_follows_the_panel(self, strip_env):
        panel = strip_env.controller._raster_panel
        panel.selection = lambda: types.SimpleNamespace(mode=types.SimpleNamespace(value="range"), minimum=200.0,
                                                        maximum=260.0, derivative=None)
        panel.kept_ratio = lambda: 0.389
        strip_env.dock._strip_kind = "raster"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content == ("raster", "Selection → source geometry", "200 – 260 · 38.9 %")

    def test_point_cloud_strip_counts_the_checked_classes(self, strip_env):
        strip_env.controller._pc_panel = types.SimpleNamespace(
            class_point_counts=lambda: (18_900_000, 38_400_000), point_counts=lambda: (None, 38_400_000),
            expression=lambda: "Classification IN (2, 6)", hag_settings=lambda: None)
        strip_env.dock._strip_kind = "point_cloud"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content == ("point_cloud", "Kept points", "18.9 M / 38.4 M (49.2 %)")

    def test_point_cloud_strip_shows_the_detected_objects(self, strip_env):
        strip_env.controller._pc_panel = types.SimpleNamespace(
            class_point_counts=lambda: (None, None), point_counts=lambda: (None, 38_400_000),
            expression=lambda: "Classification = 6 AND X >= 1 AND X <= 2 AND Y >= 3 AND Y <= 4",
            hag_settings=lambda: None, detected_objects=lambda: (3, 1250.0, False))
        strip_env.dock._strip_kind = "point_cloud"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "3 object(s) · 1250 m²"

    def test_point_cloud_strip_shows_uncounted_criteria(self, strip_env):
        strip_env.controller._pc_panel = types.SimpleNamespace(
            class_point_counts=lambda: (None, None), point_counts=lambda: (None, 38_400_000),
            expression=lambda: "Z >= 200", hag_settings=lambda: None)
        strip_env.dock._strip_kind = "point_cloud"
        strip_env.dock._update_strip()
        assert strip_env.dock._strip.content[2] == "Z >= 200"


def test_removed_raster_gives_the_strip_back_to_the_vector_colours(strip_env):
    dock = strip_env.dock
    dock._layer_id, dock._strip_kind = "r1", "raster"
    dock.forget_layers(["r1"])
    assert dock._strip_kind == "vector"
