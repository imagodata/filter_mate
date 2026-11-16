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
    assert wizard.next_step([wizard.FEATURES, wizard.LOOK, wizard.LAYOUT], values, answers) is None
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


# --- where the sections go: asked with the buttons, moved by the panel, never a setting ------------------------------


def test_the_layout_step_asks_the_panels_and_the_buttons(values):
    facts = wizard.ProjectFacts(layout=wizard.IN_DOCK)
    look = wizard.step_questions(wizard.LOOK, values, facts, wizard.Answers())
    assert [ask.key for ask in look] == ["theme", "profile", "language"]
    layout = wizard.step_questions(wizard.LAYOUT, values, facts, wizard.Answers())
    assert [ask.key for ask in layout] == ["panels", "action_bar"]
    panels = layout[0]
    assert [choice.key for choice in panels.choices] == list(wizard.LAYOUTS) and not panels.multi
    assert [choice.key for choice in panels.choices if choice.selected] == [wizard.IN_DOCK]


def test_sections_that_cannot_move_are_not_asked(values):
    """A panel without sections to move (a dock of an older layout): the buttons alone."""
    layout = wizard.step_questions(wizard.LAYOUT, values, wizard.ProjectFacts(), wizard.Answers())
    assert [ask.key for ask in layout] == ["action_bar"]


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
