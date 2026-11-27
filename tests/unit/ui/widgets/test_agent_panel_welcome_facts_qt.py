# -*- coding: utf-8 -*-
"""The welcome of AGENT follows the project, on real Qt widgets (PyQt5, offscreen): its requests are true of the state
that ``facts_provider`` reads, drawn again when that changes (a set nobody saw, or a seen one that no longer fits) and
not otherwise, and the link that reconfigures FilterMate is there with or without a model (2026-11-20).

Loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt
for the other tests), and ``qgis.core`` mocked. Skipped without PyQt5 (run it in a qgis/qgis image).
"""
import importlib
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui, QtTest  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_panel_welcome_facts_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets, "qgis.PyQt.QtNetwork": MagicMock(), "qgis.PyQt.QtXml": MagicMock()}
    if "qgis.core" not in sys.modules:
        qt["qgis.core"] = MagicMock()
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".adapters", _ROOT / "adapters"), (".adapters.agent", _ROOT / "adapters" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        return (app, importlib.import_module(f"{_PKG}.ui.widgets.agent_panel"),
                importlib.import_module(f"{_PKG}.core.agent.example_prompts"))
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, panel_module, ex = _load()
CATALOG = {example.key: example for example in ex.CATALOG}


@pytest.fixture(autouse=True)
def _own_settings(tmp_path):
    """Settings of the test alone: the keys of the set seen last, and the locale (none of a country)."""
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, str(tmp_path))
    QtCore.QSettings().setValue("locale/userLocale", "en_US")
    QtCore.QSettings().remove("filter_mate/agent/last_examples")
    yield
    QtCore.QSettings().clear()


def facts(**given):
    values = dict(known=True, layers=0, tiles=0, vectors=0, rasters=0, point_clouds=0, active="", selected=0,
                  filtered=0, remote=0)
    values.update(given)
    values.setdefault("selected_local", values["selected"])
    if values["rasters"]:
        values.setdefault("elevations", values["rasters"])
        values.setdefault("active_elevation", values["active"] == "raster")
    values["layers"] = max(values["layers"], values["vectors"] + values["rasters"] + values["point_clouds"])
    return ex.Facts(**values)


class Project:
    """What the controller reads, here a value the test changes; counts the readings."""

    def __init__(self, state=None):
        self.state = state if state is not None else facts()
        self.reads = 0

    def __call__(self):
        self.reads += 1
        return self.state


def _panel(project, ready=True):
    panel = panel_module.AgentPanel()
    panel.facts_provider = project
    panel.set_ready(ready, "Test")
    panel.resize(380, 700)
    panel.show()
    panel.shuffle_examples()
    return panel


def _needs_hold(panel, state):
    tokens = state.tokens()
    return all(set(CATALOG[key].needs) <= tokens for key in panel.example_keys)


def _shown_texts(panel):
    return [button.request() for button in panel.example_buttons if not button.isHidden()]


def test_a_panel_without_a_reader_offers_the_neutral_requests():
    panel = panel_module.AgentPanel()
    panel.set_ready(True)
    assert len(panel.example_keys) == ex.SHOWN
    assert not any(CATALOG[key].needs for key in panel.example_keys)


def test_an_empty_project_offers_ways_to_bring_data_in():
    panel = _panel(Project(facts()))
    assert len(panel.example_keys) == ex.SHOWN
    assert all(CATALOG[key].group == ex.DATA for key in panel.example_keys)
    assert all(panel_module.example_text(key, panel._examples_facts, panel.example_places[key]) in _shown_texts(panel)
               for key in panel.example_keys)


def test_layers_changing_the_project_draw_the_requests_again():
    project = Project(facts())
    panel = _panel(project)
    empty = panel.example_keys
    project.state = facts(rasters=1, active="raster")
    panel.refresh_examples()
    assert panel.example_keys != empty and _needs_hold(panel, project.state)
    assert any({"active_raster", "active_elevation"} & set(CATALOG[key].needs) for key in panel.example_keys)
    project.state = facts(rasters=1, vectors=1, active="vector", selected=2)
    panel.refresh_examples()
    assert _needs_hold(panel, project.state)
    assert any({"selection", "local_selection"} & set(CATALOG[key].needs) for key in panel.example_keys)


def test_nothing_is_drawn_again_while_the_state_stays_as_drawn_for():
    project = Project(facts(vectors=1, active="vector"))
    panel = _panel(project)
    keys = panel.example_keys
    for _ in range(20):
        panel.refresh_examples()
    project.state = facts(vectors=1, active="vector", selected=1)  # another signature
    panel.refresh_examples()
    drawn = panel.example_keys
    project.state = facts(vectors=1, active="vector", selected=9)  # one more feature: the same signature
    panel.refresh_examples()
    panel.refresh_examples()
    assert panel.example_keys == drawn and drawn != keys


def test_a_set_that_was_seen_changes_only_what_the_state_changed():
    project = Project(facts(vectors=1, active="vector"))
    panel = _panel(project)
    panel._examples_seen = True  # as when it stayed on screen
    seen = panel.example_keys
    panel.refresh_examples()
    assert panel.example_keys == seen
    project.state = facts(vectors=1, filtered=1, active="vector")
    panel.refresh_examples()
    assert panel.example_keys != seen and _needs_hold(panel, project.state)
    assert any("filter" in CATALOG[key].needs for key in panel.example_keys)
    assert sum(1 for key in panel.example_keys if key in seen) >= 2  # the others stay, each where it was
    assert panel._examples_seen is False  # a set that is not the one seen counts again


def test_a_selection_made_and_unmade_leaves_the_requests_that_did_not_depend_on_it():
    project = Project(facts(vectors=2, active="vector"))
    panel = _panel(project)
    before = panel.example_keys
    project.state = facts(vectors=2, active="vector", selected=2)
    panel.refresh_examples()
    with_selection = panel.example_keys
    assert sum(a == b for a, b in zip(before, with_selection)) >= 2
    project.state = facts(vectors=2, active="vector")
    panel.refresh_examples()
    assert _needs_hold(panel, project.state)
    assert not any({"selection", "local_selection"} & set(CATALOG[key].needs) for key in panel.example_keys)
    assert sum(a == b for a, b in zip(with_selection, panel.example_keys)) >= 2


def test_a_project_opening_does_not_redraw_the_requests_until_it_settles():
    """2026-11-22: a set was drawn when the project was read, before its active layer was set, then again 300 ms later."""
    project = Project(facts())
    panel = _panel(project)
    empty = panel.example_keys
    panel.hold_examples()
    project.state = facts(vectors=1, active="")  # the layers are there, the active layer is not set yet
    panel.clear_thread()
    panel.clear_thread()
    assert panel.example_keys == empty  # nothing drawn for the instant in between
    project.state = facts(vectors=1, active="vector")  # the active layer is set
    QtTest.QTest.qWait(panel_module.FACTS_SETTLE_MS + 400)
    assert _needs_hold(panel, project.state)
    assert any({"active_vector", "active_local"} & set(CATALOG[key].needs) for key in panel.example_keys)
    assert sum(CATALOG[key].group == ex.PROJECT for key in panel.example_keys) == 3


def test_a_request_no_longer_true_is_hidden_while_the_project_opens():
    project = Project(facts(vectors=1, active="vector"))
    panel = _panel(project)
    keys = panel.example_keys
    panel.hold_examples()
    project.state = facts()  # the project went away
    panel.clear_thread()
    assert panel.example_keys == keys
    false_ones = [index for index, key in enumerate(keys) if CATALOG[key].needs]
    assert false_ones and all(panel.example_buttons[index].isHidden() for index in false_ones)


def test_nothing_is_read_after_the_controller_is_shut_down():
    project = Project(facts())
    panel = _panel(project)
    panel.facts_changed()
    reads = project.reads
    panel.stop_following()
    QtTest.QTest.qWait(panel_module.FACTS_SETTLE_MS + 300)
    assert project.reads == reads and panel.facts_provider is None
    panel.facts_changed()
    panel.refresh_examples()
    assert len(panel.example_keys) == ex.SHOWN  # still a panel with its requests, only neutral from now on


def test_a_set_nobody_saw_is_kept_when_the_thread_is_cleared_and_the_state_is_the_same():
    project = Project(facts(vectors=1, active="vector"))
    panel = _panel(project)
    keys = panel.example_keys
    panel.clear_thread()
    panel.clear_thread()
    assert panel.example_keys == keys  # the project closes, then the one read: not drawn for an instant that nobody saw


def test_the_welcome_coming_on_screen_reads_the_state_again():
    project = Project(facts())
    panel = _panel(project)
    empty = panel.example_keys
    project.state = facts(point_clouds=1, active="point_cloud")  # no signal came
    panel._examples_on_screen()
    assert panel.example_keys != empty and _needs_hold(panel, project.state)
    assert any({"point_cloud", "active_point_cloud"} & set(CATALOG[key].needs) for key in panel.example_keys)


def test_a_burst_of_changes_is_read_once():
    project = Project(facts())
    panel = _panel(project)
    project.state = facts(vectors=2, active="vector")
    reads = project.reads
    for _ in range(30):
        panel.facts_changed()
    assert project.reads == reads  # nothing read while the changes go on
    QtTest.QTest.qWait(panel_module.FACTS_SETTLE_MS + 400)
    assert _needs_hold(panel, project.state)
    assert project.reads - reads <= 4  # one refresh: its readings, not thirty


def test_a_reading_that_fails_is_the_neutral_set_and_raises_nothing():
    def broken():
        raise RuntimeError("wrapped C/C++ object of type QgsVectorLayer has been deleted")

    panel = _panel(broken)
    assert len(panel.example_keys) == ex.SHOWN and not any(CATALOG[key].needs for key in panel.example_keys)
    panel.facts_provider = lambda: "not a Facts"
    panel.refresh_examples()
    panel._examples_on_screen()
    panel.clear_thread()
    assert len(panel.example_keys) == ex.SHOWN


def test_the_link_to_reconfigure_is_there_with_a_model_and_the_button_of_the_setup_without():
    panel = _panel(Project(), ready=True)
    assert not panel.reconfigure_button.isHidden() and panel.setup_button.isHidden()
    assert panel.reconfigure_button.text() == panel_module._tr("Reconfigure FilterMate…")
    asked = []
    panel.setup_requested.connect(lambda: asked.append(True))
    panel.reconfigure_button.click()
    assert asked == [True]
    panel.set_ready(False)
    # Without a model the button that does the same stays as it was: no second one for the same thing.
    assert panel.reconfigure_button.isHidden() and not panel.setup_button.isHidden()
    panel.setup_button.click()
    assert asked == [True, True]
    assert not panel.tour_button.isHidden() and not panel.testers_button.isHidden()


def test_the_link_sits_under_the_requests_and_above_the_tour():
    panel = _panel(Project(), ready=True)
    last_request = max(button.geometry().bottom() for button in panel.example_buttons if not button.isHidden())
    assert panel.reconfigure_button.geometry().top() > last_request
    assert panel.reconfigure_button.geometry().bottom() <= panel.tour_button.geometry().top()


def test_other_ideas_changes_destinations_and_click_inserts_the_whole_bounded_request():
    panel = _panel(Project())
    before = [p.id for p in panel.example_places.values()]
    texts = _shown_texts(panel)
    panel.more_examples_button.click()
    assert _shown_texts(panel) != texts
    assert not set(before) & {p.id for p in panel.example_places.values()}
    assert panel.more_examples_button.isVisible()
    sent = []
    panel.send_requested.connect(lambda *args: sent.append(args))
    button = panel.example_buttons[0]
    button.click()
    assert panel.input.text() == button.request() and 'km' in panel.input.text()
    assert not sent
    place = panel.example_places[panel.example_keys[0]]
    assert place.label in button._summary and 'WGS 84' not in button._summary
    # An old timer for the same keys must not mark a changed request as already seen.
    panel._examples_seen = False
    panel._examples_still_there(panel.example_keys, tuple(texts))
    assert not panel._examples_seen
    panel._examples_still_there(panel.example_keys, tuple(b.request() for b in panel.example_buttons))
    assert set(QtCore.QSettings().value(panel_module._RECENT_PLACES)) >= {p.id for p in panel.example_places.values()}
    panel.set_ready(False)
    assert panel.more_examples_button.isHidden()


def test_layer_and_field_names_follow_the_active_layer_even_when_the_type_stays_the_same():
    project = Project(facts(vectors=2, active='vector', active_id='a', active_name='Buildings',
                            active_fields=(('usage', 'text'), ('height_m', 'numeric')), vector_names=('Buildings', 'Roads')))
    panel = _panel(project)
    panel._set_examples(('color_by', 'numeric_summary', 'labels', 'osm_cycle'), project.state)
    assert 'Buildings' in panel.example_buttons[0].request() and 'usage' in panel.example_buttons[0].request()
    assert 'height_m' in panel.example_buttons[1].request()
    assert 'Buildings' in panel.example_buttons[3].request() and not panel.example_places
    keys = panel.example_keys
    project.state = facts(vectors=2, active='vector', active_id='b', active_name='Roads',
                          active_fields=(('surface', 'text'), ('width_m', 'numeric')), vector_names=('Roads', 'Buildings'))
    panel.refresh_examples()
    assert panel.example_keys == keys
    assert 'Roads' in panel.example_buttons[0].request() and 'surface' in panel.example_buttons[0].request()
    assert 'width_m' in panel.example_buttons[1].request() and 'height_m' not in panel.example_buttons[1].request()
    project.state = facts(vectors=2, active='vector', active_id='b', active_name='Roads', active_fields=())
    panel.refresh_examples()
    assert not {'numeric_summary', 'labels', 'color_by'} & set(panel.example_keys)
