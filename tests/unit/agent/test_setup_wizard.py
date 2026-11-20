# -*- coding: utf-8 -*-
"""The setup asked with cards, no model: the steps, what is ticked first, and the settings the answers ask."""
from __future__ import annotations

import pytest

from core.agent import setup_wizard as wizard
from core.agent.settings_reference import AGENT_SECTION, plan, read_settings


@pytest.fixture
def settings():
    return read_settings({})


@pytest.fixture
def values(settings):
    return {row.path: row.value for row in settings if row.path in wizard.PATHS}


def test_every_path_is_a_setting(values):
    assert set(wizard.PATHS) == set(values)


def test_the_choices_are_those_of_the_settings(settings):
    by_path = {row.path: row for row in settings}
    for path, keys in ((wizard.THEME, wizard.THEMES), (wizard.UI_PROFILE, wizard.PROFILES),
                       (wizard.LANGUAGE, wizard.LANGUAGES), (wizard.ACTION_BAR, wizard.ACTION_BARS),
                       (wizard.SECTION_HEADERS, wizard.HEADERS), (wizard.SECTION_HEIGHT, wizard.HEIGHTS),
                       (wizard.RASTER_FORMAT, wizard.RASTER_FORMATS),
                       (wizard.POINT_CLOUD_FORMAT, wizard.POINT_CLOUD_FORMATS)):
        assert set(keys) <= set(by_path[path].choices), path


def test_the_size_values_fit_the_bounds(settings):
    rows = plan(settings, [{"path": path, "value": value} for size in wizard.SIZE_VALUES.values()
                           for path, value in size.items()], by_user=True)
    assert rows
    plan(settings, [{"path": path, "value": value} for kind in (wizard.WEB_VALUES, wizard.POSTGRES_VALUES)
                    for values in kind.values() for path, value in values.items()], by_user=True)


def test_answering_as_ticked_changes_nothing(values):
    answers, done = wizard.Answers(), []
    step = wizard.next_step(done, values, answers)
    while step is not None:
        questions = wizard.step_questions(step, values, wizard.ProjectFacts(), answers)
        answers.record(step, {ask.key: [choice.key for choice in ask.choices if choice.selected]
                              for ask in questions})
        done.append(step)
        step = wizard.next_step(done, values, answers)
    assert done == list(wizard.STEPS)
    assert wizard.changes(values, answers) == []


def test_sections_turned_off_skip_their_step(values):
    answers = wizard.Answers()
    answers.record(wizard.FEATURES, {"sections": ["agent"], "data": [], "size": ["keep"]})
    assert wizard.next_step([wizard.FEATURES], values, answers) == wizard.LOOK
    assert wizard.next_step([wizard.FEATURES, wizard.LOOK], values, answers) == wizard.LAYOUT
    assert wizard.next_step([wizard.FEATURES, wizard.LOOK, wizard.LAYOUT], values, answers) == wizard.EXPLORING
    assert wizard.next_step([wizard.FEATURES, wizard.LOOK, wizard.LAYOUT, wizard.EXPLORING], values, answers) is None
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)}
    assert asked == {wizard.FILTERING_ON: False, wizard.EXPORTING_ON: False, wizard.RASTER_ON: False,
                     wizard.POINT_CLOUD_ON: False}


def test_the_user_may_turn_the_agent_off_a_model_may_not(settings, values):
    answers = wizard.Answers()
    answers.record(wizard.FEATURES, {"sections": ["filtering", "exporting"], "data": ["rasters", "point_clouds"],
                                     "size": ["keep"]})
    asked = wizard.changes(values, answers)
    assert asked == [{"path": wizard.AGENT_ON, "value": False}]
    assert wizard.AGENT_ON.startswith(AGENT_SECTION)
    with pytest.raises(ValueError):
        plan(settings, asked)
    rows = plan(settings, asked, by_user=True)
    assert rows[0]["before"] is True and rows[0]["after"] is False


def test_by_user_never_reaches_a_private_setting(settings):
    with pytest.raises(ValueError):
        plan(settings, [{"path": "APP.OPTIONS.CROSS_FILTER.pdal_path", "value": "/tmp/pdal"}], by_user=True)


def test_large_layers_with_web_services(values):
    answers = wizard.Answers()
    answers.record(wizard.FEATURES, {"sections": ["filtering", "exporting", "agent"],
                                     "data": ["rasters", "point_clouds", "web"], "size": ["large"]})
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)}
    assert asked[wizard.WFS_TIMEOUT] == 120
    assert wizard.PG_TIMEOUT not in asked  # PostgreSQL not ticked: its timeout is left as it is
    assert wizard.FILTERING_ON not in asked  # already on
    answers.record(wizard.FEATURES, {"sections": ["filtering", "exporting", "agent"],
                                     "data": ["postgres"], "size": ["large"]})
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)}
    assert asked[wizard.PG_TIMEOUT] == 180.0 and wizard.WFS_TIMEOUT not in asked


def test_a_question_not_asked_changes_nothing(values):
    """Point clouds left out: their target switch and their export format are not asked, and stay."""
    answers = wizard.Answers()
    answers.record(wizard.FEATURES, {"sections": ["filtering", "exporting", "agent"], "data": ["rasters"],
                                     "size": ["keep"]})
    questions = wizard.step_questions(wizard.FILTERING, values, wizard.ProjectFacts(), answers)
    targets = [ask for ask in questions if ask.key == "targets"][0]
    assert [choice.key for choice in targets.choices] == ["rasters"]
    exporting = wizard.step_questions(wizard.EXPORTING, values, wizard.ProjectFacts(), answers)
    assert "point_cloud_format" not in [ask.key for ask in exporting]
    answers.record(wizard.FILTERING, {"after": ["zoom", "history", "hints", "auto"], "targets": []})
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)}
    assert asked == {wizard.POINT_CLOUD_ON: False, wizard.RASTER_TARGETS: False}


def test_a_value_set_elsewhere_is_offered_ticked(values):
    current = dict(values, **{wizard.LANGUAGE: "de"})
    language = [ask for ask in wizard.step_questions(wizard.LOOK, current, wizard.ProjectFacts(), wizard.Answers())
                if ask.key == "language"][0]
    assert [choice.key for choice in language.choices if choice.selected] == ["de"]


def test_the_project_ticks_its_kinds_of_data(values):
    facts = wizard.ProjectFacts(postgres=2, web=1)
    data = wizard.step_questions(wizard.FEATURES, values, facts, wizard.Answers())[1]
    assert {choice.key for choice in data.choices if choice.selected} == {"rasters", "point_clouds", "postgres", "web"}


def test_same_number_and_switch():
    assert wizard._same(60, 60.0)
    assert not wizard._same(True, 1)


def _answer_as_ticked(values):
    answers, done = wizard.Answers(), []
    step = wizard.next_step(done, values, answers)
    while step is not None:
        questions = wizard.step_questions(step, values, wizard.ProjectFacts(), answers)
        answers.record(step, {ask.key: [choice.key for choice in ask.choices if choice.selected]
                              for ask in questions})
        done.append(step)
        step = wizard.next_step(done, values, answers)
    return answers


VALUES = [1, 0, None, "maybe", "true", "false", True, False, "", " Off ", 0.0, 2, "yes"]


@pytest.mark.parametrize("written", VALUES, ids=repr)
def test_answering_without_touching_changes_nothing_whatever_config_json_holds(values, written):
    """config.json edited by hand: a switch read as on by the plugin is ticked, one read as off is not, and the
    answers as ticked write nothing."""
    for path in wizard.SWITCHES:
        values[path] = written
    answers = _answer_as_ticked(values)
    assert wizard.changes(values, answers) == []
    for path, name in ((wizard.FILTERING_ON, "filtering"), (wizard.EXPORTING_ON, "exporting"),
                       (wizard.AGENT_ON, "agent")):
        assert (name in answers.get(wizard.FEATURES, "sections")) is wizard.read_switch(path, written)


def test_a_section_written_as_false_text_is_off(values):
    values[wizard.EXPORTING_ON] = "false"
    assert wizard.kept_sections(values, wizard.Answers()) == {"filtering", "agent"}
    assert wizard.changes(values, _answer_as_ticked(values)) == []


# --- where the sections go: asked with the buttons, moved by the panel, never a setting ------------------------------


def test_the_layout_step_asks_the_panels_and_the_buttons(values):
    facts = wizard.ProjectFacts(layout=wizard.IN_DOCK)
    look = wizard.step_questions(wizard.LOOK, values, facts, wizard.Answers())
    assert [ask.key for ask in look] == ["theme", "profile", "language"]
    layout = wizard.step_questions(wizard.LAYOUT, values, facts, wizard.Answers())
    assert [ask.key for ask in layout] == ["panels", "headers", "height", "action_bar"]
    panels = layout[0]
    assert [choice.key for choice in panels.choices] == list(wizard.LAYOUTS) and not panels.multi
    assert [choice.key for choice in panels.choices if choice.selected] == [wizard.IN_DOCK]


def test_sections_that_cannot_move_are_not_asked(values):
    """A panel without sections to move (a dock of an older layout): the buttons alone."""
    layout = wizard.step_questions(wizard.LAYOUT, values, wizard.ProjectFacts(), wizard.Answers())
    assert [ask.key for ask in layout] == ["headers", "height", "action_bar"]


def test_some_sections_apart_is_a_choice_of_its_own_ticked(values):
    facts = wizard.ProjectFacts(layout=wizard.AS_NOW)
    panels = wizard.step_questions(wizard.LAYOUT, values, facts, wizard.Answers())[0]
    assert [choice.key for choice in panels.choices] == [wizard.IN_DOCK, wizard.IN_PANELS, wizard.AS_NOW]
    assert [choice.key for choice in panels.choices if choice.selected] == [wizard.AS_NOW]


@pytest.mark.parametrize("now, chosen, wanted", [
    (wizard.IN_DOCK, wizard.IN_DOCK, None),  # as it is
    (wizard.IN_DOCK, wizard.IN_PANELS, wizard.IN_PANELS),
    (wizard.IN_PANELS, wizard.IN_DOCK, wizard.IN_DOCK),
    (wizard.AS_NOW, wizard.AS_NOW, None),  # left as they are
    (wizard.AS_NOW, wizard.IN_PANELS, wizard.IN_PANELS),
    (wizard.AS_NOW, wizard.IN_DOCK, wizard.IN_DOCK),
])
def test_the_sections_move_only_when_the_answer_is_another_layout(now, chosen, wanted):
    answers = wizard.Answers()
    answers.record(wizard.LAYOUT, {"panels": [chosen], "action_bar": ["bottom"]})
    assert wizard.layout_wanted(wizard.ProjectFacts(layout=now), answers) == wanted


def test_a_layout_not_asked_moves_nothing():
    answers = wizard.Answers()
    assert wizard.layout_wanted(wizard.ProjectFacts(layout=wizard.IN_DOCK), answers) is None
    answers.record(wizard.LAYOUT, {"action_bar": ["sections"]})
    assert wizard.layout_wanted(wizard.ProjectFacts(), answers) is None


def test_the_layout_is_never_a_setting(values):
    """QGIS keeps the place of its panels: the answer changes no setting, the buttons asked with it do."""
    answers = wizard.Answers()
    answers.record(wizard.LAYOUT, {"panels": [wizard.IN_PANELS], "action_bar": ["sections"]})
    assert wizard.changes(values, answers) == [{"path": wizard.ACTION_BAR, "value": "sections"}]


# --- how the panel lists its sections: the rails (the default) or the headers stacked ------------------------------


def test_the_rails_are_ticked_and_the_headers_stacked_are_a_choice(values):
    headers = [ask for ask in wizard.step_questions(wizard.LAYOUT, values, wizard.ProjectFacts(), wizard.Answers())
               if ask.key == "headers"][0]
    assert [choice.key for choice in headers.choices] == ["rail", "stacked"] and not headers.multi
    assert [choice.key for choice in headers.choices if choice.selected] == ["rail"]
    answers = wizard.Answers()
    answers.record(wizard.LAYOUT, {"headers": ["stacked"], "action_bar": ["bottom"]})
    assert wizard.changes(values, answers) == [{"path": wizard.SECTION_HEADERS, "value": "stacked"}]
    answers.record(wizard.LAYOUT, {"headers": ["rail"], "action_bar": ["bottom"]})
    assert wizard.changes(values, answers) == []  # the default: nothing changes


def test_a_configuration_without_the_setting_is_not_asked(values):
    older = {path: value for path, value in values.items() if path not in (wizard.SECTION_HEADERS,
                                                                           wizard.SECTION_HEIGHT)}
    layout = wizard.step_questions(wizard.LAYOUT, older, wizard.ProjectFacts(), wizard.Answers())
    assert [ask.key for ask in layout] == ["action_bar"]


def test_answering_without_touching_changes_nothing_when_config_json_holds_no_switch(values):
    for path in wizard.SWITCHES:
        values.pop(path, None)
    assert wizard.changes(values, _answer_as_ticked(values)) == []


# --- how the rows of FILTERING / EXPORTING use the height: packed at the top (the default) or spread ---------------


def test_the_rows_fill_by_default_and_fit_is_a_choice(values):
    height = [ask for ask in wizard.step_questions(wizard.LAYOUT, values, wizard.ProjectFacts(), wizard.Answers())
              if ask.key == "height"][0]
    assert [choice.key for choice in height.choices] == ["fill", "fit"] and not height.multi
    assert [choice.key for choice in height.choices if choice.selected] == ["fill"]  # as until 5.1.1
    answers = wizard.Answers()
    answers.record(wizard.LAYOUT, {"height": ["fit"], "action_bar": ["bottom"]})
    assert wizard.changes(values, answers) == [{"path": wizard.SECTION_HEIGHT, "value": "fit"}]
    answers.record(wizard.LAYOUT, {"height": ["fill"], "action_bar": ["bottom"]})
    assert wizard.changes(values, answers) == []  # the default: nothing changes


def test_the_height_of_the_rows_is_applied_at_once(settings):
    from core.agent.settings_reference import EFFECT_NOW, LIVE
    assert wizard.SECTION_HEIGHT in LIVE
    rows = plan(settings, [{"path": wizard.SECTION_HEIGHT, "value": "fill"}], by_user=True)
    assert rows and rows[0]["effect"] == EFFECT_NOW


# --- the tools of the EXPLORING rail, one question per kind of layer ---------------------------------------------------

TOOLS = wizard.TOOL_SETTINGS


def _tools_step(values, data, answers=None):
    answers = answers or wizard.Answers()
    answers.record(wizard.FEATURES, {"sections": ["filtering", "exporting", "agent"], "data": data, "size": ["keep"]})
    return answers, wizard.step_questions(wizard.EXPLORING, values, wizard.ProjectFacts(), answers)


def test_the_tools_step_comes_after_the_layout_and_before_the_sections_it_precedes_in_the_panel():
    assert wizard.STEPS.index(wizard.EXPLORING) == wizard.STEPS.index(wizard.LAYOUT) + 1
    assert wizard.STEPS.index(wizard.EXPLORING) < wizard.STEPS.index(wizard.FILTERING)


def test_the_settings_of_the_tools_are_read_by_the_setup(values):
    assert set(TOOLS.values()) <= set(wizard.PATHS) and set(TOOLS.values()) <= set(values)


def test_vector_layers_are_always_asked_the_other_kinds_when_their_data_is_ticked(values):
    _answers, questions = _tools_step(values, ["rasters", "point_clouds"])
    assert [ask.key for ask in questions] == ["tools_vector", "tools_raster", "tools_point_cloud"]
    assert [ask.key for ask in _tools_step(values, ["rasters"])[1]] == ["tools_vector", "tools_raster"]
    assert [ask.key for ask in _tools_step(values, ["point_clouds"])[1]] == ["tools_vector", "tools_point_cloud"]
    assert [ask.key for ask in _tools_step(values, [])[1]] == ["tools_vector"]  # turned off in FEATURES: not asked


def test_a_kind_of_data_left_as_it_is_is_asked_as_the_settings_say(values):
    values = dict(values, **{wizard.RASTER_ON: False, wizard.POINT_CLOUD_ON: True})
    questions = wizard.step_questions(wizard.EXPLORING, values, wizard.ProjectFacts(), wizard.Answers())
    assert [ask.key for ask in questions] == ["tools_vector", "tools_point_cloud"]


def test_the_choices_are_the_buttons_that_can_be_hidden_all_ticked_by_default(values):
    for ask in _tools_step(values, ["rasters", "point_clouds"])[1]:
        kind = ask.key[len("tools_"):]
        assert ask.multi and "more" not in [choice.key for choice in ask.choices]
        assert [choice.key for choice in ask.choices] == [name for name in wizard.exploring_tools.tools_of(kind)
                                                         if name != "more"]
        assert all(choice.selected for choice in ask.choices)


def test_the_buttons_shown_now_are_ticked(values):
    values = dict(values, **{TOOLS["vector"]: "identify, follow", TOOLS["raster"]: "similar"})
    _answers, questions = _tools_step(values, ["rasters"])
    assert [c.key for c in questions[0].choices if not c.selected] == ["identify", "follow"]
    assert [c.key for c in questions[1].choices if not c.selected] == ["similar"]


@pytest.mark.parametrize("written", ["", None, 3, "foo", "identify,follow", "Follow ; identify", "more, zoom2", ["zoom"]],
                         ids=repr)
def test_answering_as_ticked_changes_nothing_whatever_the_setting_holds(values, written):
    """Hand-written order, case, a name that no button has: the buttons hidden are the same, nothing is written."""
    values = {**values, **{path: written for path in TOOLS.values()}}
    answers = _answer_as_ticked(values)
    assert wizard.changes(values, answers) == []


def test_unticking_a_tool_writes_the_setting_of_its_kind_only(values):
    answers, _questions = _tools_step(values, ["rasters", "point_clouds"])
    answers.record(wizard.EXPLORING, {"tools_vector": ["zoom", "sync", "follow", "zone", "link", "reset"],
                                      "tools_raster": [c.key for c in _tools_step(values, ["rasters"])[1][1].choices],
                                      "tools_point_cloud": [c.key for c in _tools_step(values, ["point_clouds"])[1][1].choices]})
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)
             if change["path"] in TOOLS.values()}
    assert asked == {TOOLS["vector"]: "identify"}


def test_unticking_everything_hides_every_button_but_the_locked_one(values):
    answers, _questions = _tools_step(values, [])
    answers.record(wizard.EXPLORING, {"tools_vector": []})
    asked = {change["path"]: change["value"] for change in wizard.changes(values, answers)}
    assert asked[TOOLS["vector"]] == "zoom, sync, identify, follow, zone, link, reset"


def test_ticking_a_tool_again_empties_the_setting(values):
    values = dict(values, **{TOOLS["vector"]: "zoom, reset"})
    answers, _questions = _tools_step(values, [])
    answers.record(wizard.EXPLORING, {"tools_vector": ["zoom", "sync", "identify", "follow", "zone", "link", "reset"]})
    assert [c for c in wizard.changes(values, answers) if c["path"] in TOOLS.values()] == [
        {"path": TOOLS["vector"], "value": ""}]


def test_a_kind_not_asked_changes_nothing_even_when_hidden_tools_are_set(values):
    """Rasters turned off in FEATURES: their question is not asked, what the setting holds stays."""
    values = dict(values, **{TOOLS["raster"]: "zoom"})
    answers, questions = _tools_step(values, [])
    answers.record(wizard.EXPLORING, {ask.key: [c.key for c in ask.choices] for ask in questions})
    assert [change for change in wizard.changes(values, answers) if change["path"] == TOOLS["raster"]] == []


def test_the_answers_are_checked_as_the_agent_checks_a_setting(settings, values):
    answers, _questions = _tools_step(values, ["rasters", "point_clouds"])
    answers.record(wizard.EXPLORING, {"tools_vector": ["zoom"], "tools_raster": ["zoom"], "tools_point_cloud": []})
    rows = plan(settings, wizard.changes(values, answers), by_user=True)
    by_path = {row["path"]: row for row in rows}
    assert by_path[TOOLS["raster"]]["after"] == "preview, pipette, detector, similar, link, reset"
    assert all(by_path[path]["effect"] == "now" for path in TOOLS.values())
