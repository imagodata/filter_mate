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
    plan(settings, [{"path": path, "value": value} for web in wizard.WEB_VALUES.values()
                    for path, value in web.items()], by_user=True)


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
    assert wizard.next_step([wizard.FEATURES, wizard.LOOK], values, answers) is None
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
    assert asked[wizard.PG_TIMEOUT] == 180.0 and asked[wizard.WFS_TIMEOUT] == 120
    assert wizard.FILTERING_ON not in asked  # already on


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
