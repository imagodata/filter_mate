# -*- coding: utf-8 -*-
"""FilterMate 5 design: pure helpers of ui/layout/mockup_layout.py."""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_mockup_layout_test"


def _load():
    for name, path in (("", _ROOT), (".ui", _ROOT / "ui"), (".ui.layout", _ROOT / "ui" / "layout"),
                       (".ui.styles", _ROOT / "ui" / "styles")):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.layout.mockup_layout")


layout = _load()


GAP = layout.GAP_ITEM


def test_rail_plan_gaps_above_between_and_below():
    assert layout.rail_plan([True, True, True]) == [GAP, 0, GAP, 1, GAP, 2, GAP]


def test_rail_plan_hidden_buttons_get_no_gap():
    # Tracking and linking hidden for a raster: the three shown buttons stay evenly spread.
    assert layout.rail_plan([True, False, True, False, True]) == [GAP, 0, 1, GAP, 2, 3, GAP, 4, GAP]


def test_rail_plan_all_hidden():
    assert layout.rail_plan([False, False]) == [0, 1]
    assert layout.rail_plan([]) == []


def _rail(*names):
    return [names[index] for index in layout.rail_rank(list(names))]


def test_rail_order_is_shared_by_the_three_layer_kinds():
    zoom, eye, identify = 'pushButton_exploring_zoom', 'pushButton_checkable_exploring_selecting', 'pushButton_exploring_identify'
    more, reset = 'pushButton_exploring_{}_more', 'pushButton_exploring_reset_layer_properties'
    tool = 'pushButton_checkable_exploring_{}'
    # layout order of the dock: the .ui buttons, then the kind tools inserted after the link button
    vector = _rail(identify, zoom, eye, tool.format('tracking'), tool.format('linking_widgets'),
                   tool.format('vector_zone'), more.format('vector'), reset)
    assert vector == [zoom, eye, identify, tool.format('tracking'), tool.format('vector_zone'),
                      tool.format('linking_widgets'), more.format('vector'), reset]
    raster = _rail(zoom, eye, tool.format('raster_pipette'), tool.format('raster_detector'),
                   tool.format('raster_similar'), tool.format('raster_link'), more.format('raster'), reset)
    assert raster == [zoom, eye, tool.format('raster_pipette'), tool.format('raster_detector'),
                      tool.format('raster_similar'), tool.format('raster_link'), more.format('raster'), reset]
    cloud = _rail(identify, zoom, eye, tool.format('point_cloud_object'), tool.format('point_cloud_value_pipette'),
                  tool.format('point_cloud_zone'), more.format('point_cloud'), reset)
    assert cloud == [zoom, eye, identify, tool.format('point_cloud_object'), tool.format('point_cloud_value_pipette'),
                     tool.format('point_cloud_zone'), more.format('point_cloud'), reset]


def test_rail_order_keeps_an_unlisted_button_before_the_menus():
    names = ['pushButton_exploring_reset_layer_properties', 'pushButton_new_tool', 'pushButton_exploring_zoom',
             'pushButton_exploring_vector_more']
    assert _rail(*names) == ['pushButton_exploring_zoom', 'pushButton_new_tool', 'pushButton_exploring_vector_more',
                             'pushButton_exploring_reset_layer_properties']


class _Rail:
    def __init__(self, minimum, hint):
        self._minimum, self._hint = minimum, hint

    def minimumWidth(self):
        return self._minimum

    def minimumSizeHint(self):
        return types.SimpleNamespace(width=lambda: self._hint)


def test_rail_width_keeps_the_minimum_of_the_display_profile():
    """36 px buttons in a 56 px rail: a 36 px scroll area cut the rail and its centred icons."""
    assert layout.rail_width(_Rail(56, 36)) == 56


def test_rail_width_keeps_the_buttons_of_a_narrower_profile():
    assert layout.rail_width(_Rail(32, 36)) == 36


def test_rail_floor_is_the_buttons_plus_one_gap_around_each():
    # Eight 36 px tools (vector rail, 2026-10-18): 288 + 9 gaps of 6 = 342, the height under which they overlap.
    assert layout.rail_floor([36] * 8, 6) == 342
    assert layout.rail_floor([34, 34], 8) == 92
    assert layout.rail_floor([], 6) == 0


def test_compact_height_keeps_the_natural_size_when_the_band_has_room():
    assert layout.compact_height(350, 8, 6, 36) == 36
    assert layout.compact_height(260, 6, 6, 36) == 36  # the six vector buttons of before: 258 px


def test_compact_height_shares_a_short_band_between_the_buttons():
    # Eight tools in a 260 px band: (260 - 54) // 8 = 25 px, one gap around each, no overlap.
    assert layout.compact_height(260, 8, 6, 36) == 25
    assert layout.rail_floor([25] * 8, 6) <= 260
    assert layout.compact_height(100, 8, 6, 36) == layout.COMPACT_BUTTON_MIN
    assert layout.compact_height(260, 0, 6, 36) == 36


def test_spacing_scale_comes_from_the_design_tokens():
    from importlib import import_module
    spacing = import_module(f"{_PKG}.ui.styles.mockup_design").SPACING
    assert (layout.EDGE, layout.BLOCK, layout.GAP, layout.BAND) == (
        spacing['fm_edge'], spacing['fm_block'], spacing['fm_gap'], spacing['fm_band'])
    assert layout.SECTION_TAB_HEIGHT == layout.BAND
    assert layout.ROW_GAP == layout.FIELD_GAP == layout.GROUP_GAP == layout.RAIL_GAP == layout.GAP


def test_key_column_plan_rows_one_gap_apart():
    # Buttons 32 px, rows 32 px, 6 px apart: each button on its row, a 6 px spacer between two.
    rows = [(32, top, 32, True) for top in (0, 38, 76, 114)]
    assert layout.key_column_plan(rows) == ([0, 6, 6, 6], 0, 0)


def test_key_column_plan_ignores_where_the_buttons_were():
    """Absolute heights: a second pass gives the same plan (5.0 to 5.1.1 added deltas, one pass after the other,
    and ran out of passes with the last buttons 10 to 17 px off their rows)."""
    rows = [(32, 0, 32, True), (32, 102, 32, True), (32, 204, 32, True)]  # spread over a tall section
    assert layout.key_column_plan(rows) == ([0, 70, 70], 0, 0)
    assert layout.key_column_plan(rows) == layout.key_column_plan(rows)


def test_key_column_plan_buttons_taller_than_rows_get_a_lead_and_an_overflow():
    """EXPORTING in the compact profile: rows 28 px, buttons 32 px. The values column moves 2 px down (lead), and
    takes 2 px under its last row (overflow), so the first and the last button stay inside the rail band."""
    rows = [(32, top, 28, True) for top in (0, 34, 68)]
    spacers, lead, overflow = layout.key_column_plan(rows)
    assert (spacers, lead, overflow) == ([0, 2, 2], 2, 2)
    # With that lead applied (rows 2 px lower), the same plan: it does not grow pass after pass.
    assert layout.key_column_plan([(32, top + 2, 28, True) for top in (0, 34, 68)], lead_now=2) == (spacers, 2, 2)


def test_key_column_plan_hidden_buttons_and_rows():
    rows = [(32, 0, 32, True), (0, None, 0, True), (32, 38, 32, True), (32, None, 0, True), (32, 114, 32, True)]
    # A hidden button takes no room and no spacer; a shown button without a row keeps its place.
    assert layout.key_column_plan(rows) == ([0, 0, 6, 0, 12], 0, 0)


def test_key_column_plan_a_button_without_spacer_above_shifts_nothing():
    rows = [(32, 4, 32, False), (32, 42, 32, True)]
    assert layout.key_column_plan(rows) == ([0, 10], 0, 0)
    assert layout.key_column_plan([]) == ([], 0, 0)


def test_spacing_tokens_in_the_stylesheet():
    from importlib import import_module
    design = import_module(f"{_PKG}.ui.styles.mockup_design")
    band = design.SPACING['fm_band']
    out = design.apply_tokens("padding: {fm_band_padding} {fm_inset}; margin: {fm_gap} {fm_edge};", dark=True)
    assert out == f"padding: {band - 1}px {design.SPACING['fm_inset']}px; margin: " \
                  f"{design.SPACING['fm_gap']}px {design.SPACING['fm_edge']}px;"


def test_mockup_stylesheet_has_no_unknown_spacing_token():
    import re
    from importlib import import_module
    design = import_module(f"{_PKG}.ui.styles.mockup_design")
    qss = (_ROOT / "resources" / "styles" / "mockup.qss").read_text(encoding="utf-8")
    left = re.findall(r"\{fm_[a-z_]+\}", design.apply_tokens(qss, dark=False))
    assert left == []


def test_expanded_list_group_takes_the_free_height():
    assert layout.list_group_stretch(True) == (1, 0)
    assert layout.list_group_stretch(False) == (0, 1)


# --- APP.DOCKWIDGET.SECTION_HEIGHT: the rows of FILTERING / EXPORTING packed at the top, or spread -----------------


@pytest.mark.parametrize("config, expected", [
    ({}, "fit"),  # a configuration written before the setting
    (None, "fit"),
    ({"APP": {"DOCKWIDGET": {}}}, "fit"),
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": "fill"}}}}, "fill"),
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": " Fill "}}}}, "fill"),
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": "fill"}}}, "fill"),  # a bare value
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": "fit"}}}}, "fit"),
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": "tall"}}}}, "fit"),  # anything else: the default
    ({"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": 3}}}}, "fit"),
])
def test_section_height_reads_the_setting(config, expected):
    assert layout.section_height(config) == expected


def test_row_items_fit_has_no_stretch_fill_one_between_two_rows():
    assert layout.row_items(3, "fit") == [0, 1, 2]
    assert layout.row_items(3, "fill") == [0, None, 1, None, 2]
    assert layout.row_items(1, "fill") == [0]
    assert layout.row_items(0, "fill") == []


def test_scroll_bar_margin_only_beside_a_scroll_bar():
    assert layout.scroll_bar_margin(False) == 0
    assert layout.scroll_bar_margin(True) == layout.SCROLLBAR_MARGIN > 0


class _Item:
    def __init__(self, name=None, stretch=False):
        self.name, self.stretch = name, stretch

    def spacerItem(self):  # noqa: N802 - Qt name
        return self if self.name is None else None


class _Column:
    """A QVBoxLayout of rows (names) and spacers (None)."""

    def __init__(self, entries):
        self.items = [_Item(entry) for entry in entries]
        self.spacing = self.margins = None
        self.invalidated = 0

    def entries(self):
        return [item.name if item.name is not None else ('stretch' if item.stretch else 'spacer')
                for item in self.items]

    def setSpacing(self, value):  # noqa: N802
        self.spacing = value

    def setContentsMargins(self, *margins):  # noqa: N802
        self.margins = margins

    def count(self):
        return len(self.items)

    def itemAt(self, index):  # noqa: N802
        return self.items[index]

    def takeAt(self, index):  # noqa: N802
        return self.items.pop(index)

    def insertStretch(self, index, stretch):  # noqa: N802
        assert stretch == 1
        self.items.insert(index, _Item(stretch=True))

    def invalidate(self):
        self.invalidated += 1


class _Policy:
    def __init__(self, vertical):
        self.vertical = vertical

    def verticalPolicy(self):  # noqa: N802
        return self.vertical

    def setVerticalPolicy(self, value):  # noqa: N802
        self.vertical = value


class _Page:
    def __init__(self):
        self.policy = _Policy('Preferred')

    def sizePolicy(self):  # noqa: N802
        return _Policy(self.policy.vertical)

    def setSizePolicy(self, policy):  # noqa: N802
        self.policy = policy

    def updateGeometry(self):  # noqa: N802
        pass


class _Aligner:
    resets = 0

    def reset(self):
        self.resets += 1


@pytest.fixture
def dock(monkeypatch):
    widgets = types.ModuleType("qgis.PyQt.QtWidgets")
    widgets.QSizePolicy = types.SimpleNamespace(Policy=types.SimpleNamespace(Preferred='Preferred', Maximum='Maximum'))
    for name, module in (("qgis", types.ModuleType("qgis")), ("qgis.PyQt", types.ModuleType("qgis.PyQt")),
                         ("qgis.PyQt.QtWidgets", widgets)):
        monkeypatch.setitem(sys.modules, name, module)
    properties = {}
    # The values columns as the .ui and the managers leave them: spacers between some rows, two in a row.
    return types.SimpleNamespace(
        CONFIG_DATA={},
        verticalLayout_filtering_values=_Column(['source', 'layers', None, None, 'operators', None, 'predicates',
                                                 None, 'buffer']),
        verticalLayout_exporting_values=_Column(['layers', None, 'crs', 'styles', None, 'format']),
        FILTERING=_Page(), EXPORTING=_Page(),
        _fm_aligner_filtering=_Aligner(), _fm_aligner_exporting=_Aligner(),
        setProperty=properties.__setitem__, property=properties.get)


def test_rows_fit_by_default_one_gap_apart_page_held_to_its_rows(dock):
    assert layout.lay_out_rows(dock)
    filtering, exporting = dock.verticalLayout_filtering_values, dock.verticalLayout_exporting_values
    assert filtering.entries() == ['source', 'layers', 'operators', 'predicates', 'buffer']
    assert exporting.entries() == ['layers', 'crs', 'styles', 'format']
    assert filtering.spacing == layout.ROW_GAP == layout.SPACING['fm_gap']
    assert filtering.margins == (0, 0, 0, 0)
    assert dock.FILTERING.policy.vertical == dock.EXPORTING.policy.vertical == 'Maximum'
    assert dock.property('fm_section_height') == 'fit'
    assert dock._fm_aligner_filtering.resets == dock._fm_aligner_exporting.resets == 1  # the buttons follow


def test_rows_fill_one_stretch_between_two_rows_and_back(dock):
    dock.CONFIG_DATA = {"APP": {"DOCKWIDGET": {"SECTION_HEIGHT": {"value": "fill"}}}}
    layout.lay_out_rows(dock)
    filtering = dock.verticalLayout_filtering_values
    assert filtering.entries() == ['source', 'stretch', 'layers', 'stretch', 'operators', 'stretch', 'predicates',
                                   'stretch', 'buffer']
    assert dock.FILTERING.policy.vertical == 'Preferred' and dock.property('fm_section_height') == 'fill'
    layout.lay_out_rows(dock)  # again (after the dimension managers): the same, no stretch added twice
    assert filtering.entries().count('stretch') == 4
    layout.lay_out_rows(dock, 'fit')  # the setting changed: the argument wins over the configuration
    assert filtering.entries() == ['source', 'layers', 'operators', 'predicates', 'buffer']
    assert dock.FILTERING.policy.vertical == 'Maximum' and dock.property('fm_section_height') == 'fit'


def test_rows_of_a_form_without_the_columns_are_left_alone(dock):
    bare = types.SimpleNamespace(CONFIG_DATA={}, setProperty=lambda *args: None)
    assert layout.lay_out_rows(bare) is False
