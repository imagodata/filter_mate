# -*- coding: utf-8 -*-
"""Which buttons of the EXPLORING rail the user hides, per kind of layer (core/domain/exploring_tools.py)."""
import json
from pathlib import Path

import pytest

from core.domain import exploring_tools as tools

pytestmark = pytest.mark.unit

DEFAULT = json.loads((Path(__file__).resolve().parents[4] / "config" / "config.default.json").read_text(encoding="utf-8"))
SECTION = DEFAULT["APP"]["DOCKWIDGET"]["EXPLORING_TOOLS"]


class TestTheSettingsOfTheSchema:
    def test_one_setting_per_kind_empty_by_default(self):
        for kind, path in tools.SETTING_PATHS.items():
            assert path == f"APP.DOCKWIDGET.EXPLORING_TOOLS.{kind}_hidden"
            assert SECTION[f"{kind}_hidden"]["value"] == ""

    def test_the_names_the_schema_allows_are_the_buttons_that_can_be_hidden(self):
        """The agent and the setup check a text against ``names`` (core/agent/settings_reference.py): it must hold
        every button of the rail but the locked ones, in the order of the rail."""
        for kind in tools.KINDS:
            expected = [name for name in tools.tools_of(kind) if name not in tools.LOCKED]
            assert SECTION[f"{kind}_hidden"]["names"] == expected

    def test_every_kind_has_the_locked_button(self):
        for kind in tools.KINDS:
            assert tools.LOCKED <= set(tools.tools_of(kind))


class TestReadingASetting:
    @pytest.mark.parametrize("raw", [None, "", "  ", 3, 1.5, True, {}, {"zoom": 1}, object(), [], [1, None],
                                     "nothing, here", "zoom2", ",,;"])
    def test_a_value_with_no_name_to_read_hides_nothing(self, raw):
        for kind in tools.KINDS:
            assert tools.hidden_for(kind, raw) == frozenset()
            assert tools.shown_for(kind, raw) == tools.tools_of(kind)

    def test_names_are_read_in_text_in_a_list_and_in_any_case(self):
        assert tools.hidden_for("vector", "zoom, identify") == {"zoom", "identify"}
        assert tools.hidden_for("vector", " Zoom ;IDENTIFY\nfollow") == {"zoom", "identify", "follow"}
        assert tools.hidden_for("vector", ["zoom", " Reset "]) == {"zoom", "reset"}
        assert tools.hidden_for("point_cloud", "value-pipette, value pipette") == {"value_pipette"}

    def test_a_name_of_another_kind_hides_nothing_here(self):
        assert tools.hidden_for("vector", "pipette, detector") == frozenset()
        assert tools.hidden_for("raster", "pipette, identify") == {"pipette"}
        assert tools.hidden_for("point_cloud", "follow, link, pipette, object") == {"object"}

    def test_a_kind_that_is_not_one_has_no_tool(self):
        assert tools.hidden_for("table", "zoom") == frozenset() and tools.shown_for("table", "zoom") == ()

    @pytest.mark.parametrize("kind", tools.KINDS)
    def test_the_locked_button_is_never_hidden(self, kind):
        assert tools.hidden_for(kind, "more") == frozenset()
        every = ", ".join(tools.tools_of(kind))
        assert tools.shown_for(kind, every) == ("more",)  # never an empty rail
        assert "more" not in tools.format_hidden(kind, tools.tools_of(kind))

    def test_the_shown_buttons_keep_the_order_of_the_rail(self):
        assert tools.shown_for("raster", "preview, pipette") == ("zoom", "detector", "similar", "link", "more", "reset")


class TestWritingASetting:
    def test_the_text_lists_the_names_in_the_order_of_the_rail(self):
        assert tools.format_hidden("vector", {"reset", "zoom", "identify"}) == "zoom, identify, reset"
        assert tools.format_hidden("vector", set()) == ""

    def test_the_text_of_the_shown_ones_is_the_text_of_the_others(self):
        assert tools.setting_from_shown("vector", tools.tools_of("vector")) == ""
        assert tools.setting_from_shown("raster", ["zoom", "pipette", "more", "reset"]) == \
            "preview, detector, similar, link"
        assert tools.setting_from_shown("point_cloud", []) == ", ".join(
            name for name in tools.tools_of("point_cloud") if name != "more")

    def test_what_is_written_reads_back_the_same(self):
        for kind in tools.KINDS:
            hidden = {name for index, name in enumerate(tools.tools_of(kind)) if index % 2 == 0} - tools.LOCKED
            assert tools.hidden_for(kind, tools.format_hidden(kind, hidden)) == hidden


class TestReadingAConfiguration:
    @staticmethod
    def _config(value):
        return {"APP": {"DOCKWIDGET": {"EXPLORING_TOOLS": {"raster_hidden": value}}}}

    def test_a_wrapped_leaf_and_a_raw_one_are_read(self):
        assert tools.hidden_in_config(self._config({"value": "zoom"}), "raster") == {"zoom"}
        assert tools.hidden_in_config(self._config("zoom"), "raster") == {"zoom"}

    @pytest.mark.parametrize("config", [None, {}, "x", [], {"APP": None}, {"APP": {"DOCKWIDGET": []}},
                                        {"APP": {"DOCKWIDGET": {"EXPLORING_TOOLS": {"raster_hidden": {}}}}}])
    def test_a_configuration_without_the_setting_hides_nothing(self, config):
        assert tools.hidden_in_config(config, "raster") == frozenset()

    def test_the_defaults_hide_nothing(self):
        for kind in tools.KINDS:
            assert tools.hidden_in_config(DEFAULT, kind) == frozenset()
