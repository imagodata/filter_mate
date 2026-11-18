# -*- coding: utf-8 -*-
"""
The setup and the tour in the AGENT thread, with no model (ui/controllers/setup_wizard.py, welcome_tour.py): what
Apply moves besides the settings, what the link puts back, and what the tour tells.

Both controllers are loaded by path under a private package: ``core`` is the real one, the thread, the settings and
the panels of the sections are stand-ins.
"""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_setup_and_tour_test"
DETACHABLE = ("agent", "filtering", "exporting", "configuration")


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeCard:
    def __init__(self, lines=()):
        self.answered, self.declined = FakeSignal(), FakeSignal()
        self.apply_requested, self.cancel_requested = FakeSignal(), FakeSignal()
        self.lines, self.done, self.accepted = list(lines), False, None

    def finish(self, accepted):
        if not self.done:
            self.done, self.accepted = True, accepted


class FakePanel:
    """The thread: what was said, in order."""

    def __init__(self):
        self.said, self.links, self.cards, self.questions = [], {}, [], []

    def add_note(self, text):
        self.said.append(("note", text))

    def add_text(self, text):
        self.said.append(("text", text))

    def end_answer(self):
        self.said.append(("end", ""))

    def add_link(self, label, on_click):
        self.said.append(("link", label))
        self.links[label] = on_click

    def add_settings_card(self, texts, lines, reason):
        self.cards.append(FakeCard(lines))
        return self.cards[-1]

    def add_question_card(self, texts, questions, free_other=True):
        self.questions.append(list(questions))
        self.cards.append(FakeCard())
        return self.cards[-1]


# What "In panels of QGIS" gives: AGENT in its own panel, the sections of the lower stack together.
TAKEN_OUT = (("agent",), ("filtering", "exporting", "configuration"))


class FakePanels:
    """The sections that can go to panels of QGIS (ui/layout/section_panels.SectionPanels): the panels with their
    sections, and what is kept for the next time: the panels of now, and each section that was apart and is turned
    off (not ``present``)."""

    def __init__(self, apart=(), present=DETACHABLE, groups=None):
        self.panels = [list(group) for group in groups] if groups is not None else [[key] for key in apart]
        self.present = list(present)
        self.kept = [tuple(group) for group in self.panels]

    def detached(self):
        return tuple(key for key in DETACHABLE if any(key in group for group in self.panels))

    def groups(self):
        return tuple(tuple(group) for group in self.panels)

    def kept_apart(self):
        return tuple(self.kept)

    def keep_apart(self, groups):
        self.kept = [(group,) if isinstance(group, str) else tuple(group) for group in groups]

    def _remember(self):
        apart = set(self.detached())
        absent = [key for group in self.kept for key in group if key not in apart and key not in self.present]
        self.kept = [tuple(group) for group in self.panels] + [(key,) for key in absent]

    def can_detach(self, key):
        return key in self.present and key not in self.detached()

    def detach(self, key, remember=True):
        if not self.can_detach(key):
            return False
        self.panels.append([key])
        if remember:
            self._remember()
        return True

    def attach(self, key, remember=True):
        if key not in self.detached():
            return False
        self.panels = [group for group in ([name for name in group if name != key] for group in self.panels) if group]
        if remember:
            self._remember()
        return True

    def detach_all(self):
        """AGENT in its own panel, the lower sections together (open_smart)."""
        left = []
        for key in DETACHABLE:
            if not self.can_detach(key):
                continue
            lower = next((group for group in self.panels if key != "agent" and group != ["agent"]), None)
            if lower is not None:
                lower.append(key)
            else:
                self.panels.append([key])
            left.append(key)
        self._remember()
        return left

    def attach_all(self, remember=True):
        for key in self.detached():
            self.attach(key, remember)
        if remember:
            self.kept = []

    def arrange(self, groups, remember=True):
        before = self.groups()
        self.panels = [group for group in ([key for key in group if key in self.present] for group in groups) if group]
        if remember:
            self._remember()
        return self.groups() != before

    def section_turned(self, key, on):
        """What the dock does when a setting turns a section off or on (dock_chrome.apply_section_options)."""
        if on and key not in self.present:
            self.present.append(key)
            if any(key in group for group in self.kept):
                self.detach(key, remember=False)
        elif not on and key in self.present:
            self.attach(key, remember=False)  # back in the dock, kept as apart for the day it returns
            self.present.remove(key)


def _module(monkeypatch, name, **attrs):
    module = types.ModuleType(f"{_PKG}{name}")
    module.__path__ = []
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return module


def _load(monkeypatch, name, rel):
    spec = importlib.util.spec_from_file_location(f"{_PKG}.{name}", _ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def world(monkeypatch):
    """The two controllers, with the settings of config.default.json in a store of the test."""
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.QCoreApplication = types.SimpleNamespace(translate=lambda context, text: text)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", qtcore)
    _module(monkeypatch, "")
    core = types.ModuleType(f"{_PKG}.core")
    core.__path__ = [str(_ROOT / "core")]  # pure Python: the real modules
    monkeypatch.setitem(sys.modules, core.__name__, core)
    for name in (".adapters", ".adapters.agent", ".ui", ".ui.controllers", ".ui.layout"):
        _module(monkeypatch, name)
    _module(monkeypatch, ".ui.layout.section_panels", DETACHABLE=DETACHABLE)
    reference = importlib.import_module(f"{_PKG}.core.agent.settings_reference")
    state = types.SimpleNamespace(config={}, ready=False, applied=[], fail=False, on_apply=lambda values: None)

    def rows():
        return reference.read_settings(state.config)

    def apply_values(values):
        if state.fail:
            raise RuntimeError("the configuration was put back as it was")
        state.applied.append(dict(values))
        state.on_apply(values)
        for path, value in values.items():
            node = state.config
            *parents, leaf = path.split(".")
            for part in parents:
                node = node.setdefault(part, {})
            node[leaf] = value
        return list(values)

    _module(monkeypatch, ".adapters.agent.plugin_settings", settings_rows=rows, apply_values=apply_values,
            current_values=lambda paths: {row.path: row.value for row in rows() if row.path in set(paths)})
    _module(monkeypatch, ".adapters.agent.settings",
            load_settings=lambda: types.SimpleNamespace(ready=state.ready))
    state.tour = _load(monkeypatch, "ui.controllers.welcome_tour", "ui/controllers/welcome_tour.py")
    state.setup = _load(monkeypatch, "ui.controllers.setup_wizard", "ui/controllers/setup_wizard.py")
    state.wizard = importlib.import_module(f"{_PKG}.core.agent.setup_wizard")
    return state


@pytest.fixture
def chat(world):
    """The AgentChatController, as much of it as the setup and the tour use."""
    panel = FakePanel()
    dock = types.SimpleNamespace(_fm_panels=FakePanels(), _fm_sections=types.SimpleNamespace(
        section_shown=lambda key: True, top_rail=object()))
    chat = types.SimpleNamespace(panel=panel, _parent_widget=dock, _settings_cards=[], busy=False, status=[],
                                 shown=[], started=[], opened=[])
    chat.chat_busy = lambda: chat.busy
    chat._say = lambda text, error=False: chat.status.append(text)
    chat._lines_of = lambda rows, left_out=(): [f"{row['path']}: {row['before']} → {row['after']}" for row in rows]
    chat._show_agent = lambda: chat.shown.append("agent")
    chat._show_agent_soon = chat._show_agent  # the controller waits for Qt to lay the panels out
    chat.start_setup = lambda: chat.started.append("setup") or True
    chat.start_model_setup = lambda: True
    chat.open_settings = lambda tab="": chat.opened.append(tab) or True
    chat.show_tour = lambda: world.tour.WelcomeTour(chat).show()
    return chat


def _answer(world, chat, untick=(), pick=(), tick=()):
    """Answer the card that waits as it is ticked, but for ``untick`` and ``tick`` (labels) and ``pick`` ((header,
    label))."""
    setup = chat.wizard
    questions = chat.panel.questions[-1]
    chosen = []
    for question in questions:
        labels = [option.label for option in question.options
                  if (option.selected or option.label in tick) and option.label not in untick]
        for header, label in pick:
            if question.header == header:
                labels = [label]
        chosen.append((labels, ""))
    setup._card.answered.emit(chosen)


def _run(world, chat, untick=(), pick=(), tick=()):
    """The setup from its first card to the card of the changes; that card, None when nothing is to change."""
    chat.wizard = world.setup.SetupWizard(chat)
    chat.wizard.start()
    while chat.wizard.running:
        _answer(world, chat, untick, pick, tick)
    cards = [card for card in chat.panel.cards if card.lines]  # the cards of questions have no line
    return cards[-1] if cards else None


# --- the setup: where the sections go -------------------------------------------------------------------------------


def test_the_layout_is_asked_with_the_buttons_ticked_as_it_is(world, chat):
    chat.wizard = world.setup.SetupWizard(chat)
    chat.wizard.start()
    _answer(world, chat)  # features
    _answer(world, chat)  # look
    layout = chat.panel.questions[-1]
    assert [question.header for question in layout] == ["Layout", "Headers", "Rows", "Buttons"]
    assert [option.label for option in layout[1].options if option.selected] == ["A rail of chips"]
    assert [option.label for option in layout[2].options if option.selected] == ["Packed at the top"]
    assert [option.label for option in layout[0].options if option.selected] == ["All in the FilterMate panel"]
    assert len(layout[0].options) == 2  # nothing apart: "As they are now" is not a choice


def test_answering_as_ticked_changes_nothing_and_moves_nothing(world, chat):
    assert _run(world, chat) is None
    assert ("note", "Nothing to change: FilterMate already works this way.") in chat.panel.said
    assert chat._parent_widget._fm_panels.detached() == () and world.applied == []
    assert ("link", "How FilterMate works") in chat.panel.said  # the setup ends on how it works, either way


def test_apply_moves_the_sections_and_the_link_puts_them_back(world, chat):
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS")])
    assert card.lines == ["Sections: in panels of QGIS (applied at once)"]
    assert panels.detached() == ()  # nothing moves until Apply

    card.apply_requested.emit()
    assert card.done and card.accepted is True
    assert panels.detached() == DETACHABLE and world.applied == []  # no setting was changed
    assert chat.shown == ["agent"]  # AGENT moved too: its thread comes forward
    assert any(kind == "note" and "to group them" in text for kind, text in chat.panel.said)

    assert chat.wizard.revert() is True
    assert panels.detached() == ()
    assert chat.wizard.revert() is False  # put back once


def test_a_link_that_failed_is_not_marked_as_done(world, chat):
    """Put back failed ("Nothing changed"): the change stayed set, and the link said it was put back already."""
    card = _run(world, chat, pick=[("Buttons", "Top")])
    card.apply_requested.emit()
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "top"}
    world.fail = True
    assert chat.wizard.revert() is False
    assert ("note", "Nothing changed: the settings could not be applied.") in chat.panel.said
    chat.panel.said.clear()
    world.fail = False
    assert chat.wizard.revert() is True  # the same link, tried again
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "bottom"}
    assert ("note", "These settings were already put back.") not in chat.panel.said
    assert chat.wizard.revert() is False  # put back once


def test_the_link_puts_back_the_sections_that_were_apart_only(world, chat):
    panels = chat._parent_widget._fm_panels = FakePanels(apart=("filtering",))
    chat.wizard = world.setup.SetupWizard(chat)
    chat.wizard.start()
    _answer(world, chat)
    _answer(world, chat)
    layout = chat.panel.questions[-1][0]
    assert [option.label for option in layout.options if option.selected] == ["As they are now"]
    while chat.wizard.running:
        _answer(world, chat, pick=[("Layout", "All in the FilterMate panel")])
    card = [card for card in chat.panel.cards if card.lines][-1]
    assert card.lines == ["Sections: all back in the FilterMate panel (applied at once)"]
    card.apply_requested.emit()
    assert panels.detached() == ()
    assert chat.wizard.revert() is True
    assert panels.detached() == ("filtering",)


def test_the_link_puts_the_panels_back_with_the_sections_they_shared(world, chat):
    """A panel holds several sections: the link gives each one its panel again, not a panel of its own."""
    together = (("agent",), ("exporting", "filtering"))
    panels = chat._parent_widget._fm_panels = FakePanels(groups=together)
    chat.wizard = world.setup.SetupWizard(chat)
    chat.wizard.start()
    while chat.wizard.running:
        _answer(world, chat, pick=[("Layout", "All in the FilterMate panel")])
    card = [card for card in chat.panel.cards if card.lines][-1]
    card.apply_requested.emit()
    assert panels.groups() == () and panels.kept_apart() == ()
    assert chat.wizard.revert() is True
    assert panels.groups() == together and panels.kept_apart() == together


def test_every_section_taken_out_shares_two_panels(world, chat):
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS")])
    card.apply_requested.emit()
    assert panels.groups() == TAKEN_OUT  # AGENT in its own panel, the lower sections together


def test_settings_and_sections_go_on_one_card_and_come_back_together(world, chat):
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS"), ("Buttons", "Under each section")])
    assert len(card.lines) == 2 and card.lines[0].startswith(world.wizard.ACTION_BAR)
    card.apply_requested.emit()
    assert world.applied == [{world.wizard.ACTION_BAR: "sections"}] and panels.detached() == DETACHABLE
    assert chat.wizard.revert() is True
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "bottom"} and panels.detached() == ()


def test_a_setting_changed_since_does_not_keep_the_sections_from_moving(world, chat):
    """The row is left as it is (and said); the sections still go where Apply was asked to put them."""
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS"), ("Buttons", "Top")])
    world.config.setdefault("APP", {}).setdefault("DOCKWIDGET", {})["ACTION_BAR_POSITION"] = "left"  # meanwhile
    card.apply_requested.emit()
    assert card.accepted is True and panels.detached() == DETACHABLE and world.applied == []
    assert ("note", "Some of these settings changed since: they are left as they are.") in chat.panel.said


def test_nothing_applied_and_nothing_moved_closes_the_card_as_not_applied(world, chat):
    card = _run(world, chat, pick=[("Buttons", "Top")])
    world.config.setdefault("APP", {}).setdefault("DOCKWIDGET", {})["ACTION_BAR_POSITION"] = "left"
    card.apply_requested.emit()
    assert card.accepted is False and chat.wizard.revert() is False
    assert ("link", "Put my settings back as they were") not in chat.panel.said


def test_apply_waits_for_the_end_of_a_request(world, chat):
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS")])
    chat.busy = True
    card.apply_requested.emit()
    assert not card.done and panels.detached() == () and "Wait" in chat.status[-1]


def test_each_link_puts_back_its_own_apply(world, chat):
    """2026-11-16, review: the link of a first setup put back what a second one had set, and the second did nothing."""
    first = _run(world, chat, pick=[("Buttons", "Top")])
    first.apply_requested.emit()
    first_link = chat.panel.links["Put my settings back as they were"]
    second = _run(world, chat, pick=[("Buttons", "Left")])
    second.apply_requested.emit()
    second_link = chat.panel.links["Put my settings back as they were"]
    assert world.applied == [{world.wizard.ACTION_BAR: "top"}, {world.wizard.ACTION_BAR: "left"}]

    first_link()  # top -> bottom was asked back, but the setting is "left" now: left as it is, and said
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "left"}
    assert ("note", "Some of these settings changed since: they are left as they are.") in chat.panel.said
    second_link()
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "top"}  # what the second Apply had found
    second_link()
    assert chat.panel.said[-1] == ("note", "These settings were already put back.")
    assert len(world.applied) == 3


def test_the_link_comes_back_in_the_thread_of_another_project(world, chat):
    card = _run(world, chat, pick=[("Buttons", "Top")])
    card.apply_requested.emit()
    chat.panel.said.clear()
    chat.panel.links.clear()
    chat.wizard.forget()  # another project: the thread was emptied
    chat.wizard.offer_back_again()
    assert chat.panel.said == [("link", "Put my settings back as they were")]
    chat.panel.links["Put my settings back as they were"]()
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "bottom"}
    chat.panel.said.clear()
    chat.wizard.offer_back_again()
    assert chat.panel.said == []  # put back: nothing left to offer


def test_apply_and_put_back_wait_for_another_application(world, chat):
    card = _run(world, chat, pick=[("Buttons", "Top")])
    chat._mcp = types.SimpleNamespace(busy=True)
    card.apply_requested.emit()
    assert not card.done and world.applied == [] and "Another application" in chat.status[-1]
    chat._mcp.busy = False
    card.apply_requested.emit()
    chat._mcp.busy = True
    assert chat.wizard.revert() is False and len(world.applied) == 1
    chat._mcp.busy = False
    assert chat.wizard.revert() is True


def _follow_filtering(world, chat):
    """The panels follow FILTERING turned on or off by a setting, as the dock does."""
    panels = chat._parent_widget._fm_panels
    world.on_apply = lambda values: (panels.section_turned("filtering", values[world.wizard.FILTERING_ON])
                                     if world.wizard.FILTERING_ON in values else None)
    return panels


def test_the_link_puts_back_a_section_that_apply_turned_off_and_merged(world, chat):
    """2026-11-16, review: FILTERING alone in its panel, turned off and merged by one Apply. Where the sections
    were was read after the setting had brought FILTERING back: the link then left it in the dock."""
    chat._parent_widget._fm_panels = FakePanels(apart=("filtering",))
    panels = _follow_filtering(world, chat)
    card = _run(world, chat, untick=("FILTERING",), pick=[("Layout", "All in the FilterMate panel")])
    card.apply_requested.emit()
    assert card.accepted is True and panels.detached() == () and panels.kept_apart() == ()

    assert chat.wizard.revert() is True
    assert world.config["APP"]["OPTIONS"]["FILTERING"]["enabled"] is True
    assert panels.detached() == ("filtering",) and panels.kept_apart() == (("filtering",),)


def test_the_link_does_not_leave_a_section_kept_as_apart(world, chat):
    """2026-11-16, review: FILTERING off and nothing apart; the setup turns it on with every section out of
    FilterMate; the link turns it off again. It stayed kept as apart: alone in a panel the day it was turned on."""
    world.config = {"APP": {"OPTIONS": {"FILTERING": {"enabled": False}}}}
    chat._parent_widget._fm_panels = FakePanels(present=[key for key in DETACHABLE if key != "filtering"])
    panels = _follow_filtering(world, chat)
    card = _run(world, chat, tick=("FILTERING",), pick=[("Layout", "In panels of QGIS")])
    card.apply_requested.emit()
    assert panels.detached() == DETACHABLE and panels.kept_apart() == TAKEN_OUT

    assert chat.wizard.revert() is True
    assert panels.detached() == () and panels.kept_apart() == ()
    panels.section_turned("filtering", True)  # turned on another day: in the dock, as before the setup
    assert panels.detached() == ()


def test_settings_that_cannot_be_applied_move_nothing(world, chat):
    """The card read "Applied." under "Nothing changed: the settings could not be applied."."""
    panels = chat._parent_widget._fm_panels
    card = _run(world, chat, pick=[("Layout", "In panels of QGIS"), ("Buttons", "Top")])
    world.fail = True
    card.apply_requested.emit()
    assert card.accepted is False and panels.detached() == ()
    assert ("note", "Nothing changed: the settings could not be applied.") in chat.panel.said
    assert ("link", "Put my settings back as they were") not in chat.panel.said


def test_one_link_comes_back_after_several_setups(world, chat):
    for place in ("Top", "Left"):
        _run(world, chat, pick=[("Buttons", place)]).apply_requested.emit()
    chat.panel.said.clear()
    chat.wizard.forget()
    chat.wizard.offer_back_again()
    assert chat.panel.said == [("link", "Put my settings back as they were")]  # the last setup's
    chat.panel.links["Put my settings back as they were"]()
    assert world.applied[-1] == {world.wizard.ACTION_BAR: "top"}


def test_the_links_of_the_tour_wait_for_the_end_of_a_request(world, chat):
    panels = chat._parent_widget._fm_panels
    world.tour.WelcomeTour(chat).show()
    chat.busy = True
    chat.panel.links["Take every section out of FilterMate"]()
    assert panels.detached() == () and "Wait" in chat.status[-1]


def test_a_panel_without_sections_to_move_asks_the_buttons_alone(world, chat):
    chat._parent_widget._fm_panels = None
    chat.wizard = world.setup.SetupWizard(chat)
    chat.wizard.start()
    _answer(world, chat)
    _answer(world, chat)
    assert [question.header for question in chat.panel.questions[-1]] == ["Headers", "Rows", "Buttons"]


# --- the tour ----------------------------------------------------------------------------------------------------------


def test_the_tour_tells_each_section_then_offers_what_it_said(world, chat):
    assert world.tour.WelcomeTour(chat).show() is True
    said = chat.panel.said
    texts = [text for kind, text in said if kind == "text"]
    assert texts[1].startswith("The panel has two stacks, each with a rail")
    assert [text.split()[0] for text in texts[2:7]] == ["EXPLORING", "FILTERING", "EXPORTING", "AGENT",
                                                        "CONFIGURATION"]
    assert any(text.startswith("By default every section is in this panel") for text in texts)
    assert said.count(("end", "")) == len(texts)  # each paragraph on its own
    assert [text for kind, text in said if kind == "link"] == [
        "Take every section out of FilterMate", "Set up FilterMate", "Connect a model"]


def test_the_links_of_the_tour_do_what_they_say(world, chat):
    panels = chat._parent_widget._fm_panels
    world.tour.WelcomeTour(chat).show()
    chat.panel.links["Take every section out of FilterMate"]()
    assert panels.detached() == DETACHABLE and chat.shown == ["agent"]
    chat.panel.links["Set up FilterMate"]()
    chat.panel.links["Connect a model"]()
    assert chat.started == ["setup"] and chat.opened == ["provider"]

    chat.panel.said.clear()
    world.tour.WelcomeTour(chat).show()  # told again with every section apart: the link brings them back
    links = [text for kind, text in chat.panel.said if kind == "link"]
    assert links[0] == "Merge every section back into FilterMate"
    chat.panel.links[links[0]]()
    assert panels.detached() == ()


def test_the_tour_names_a_section_turned_off(world, chat):
    chat._parent_widget._fm_sections.section_shown = lambda key: key != "filtering"
    world.tour.WelcomeTour(chat).show()
    texts = [text for kind, text in chat.panel.said if kind == "text"]
    assert not any(text.startswith("FILTERING ") for text in texts)
    assert any(text.startswith("Turned off in your settings: FILTERING.") for text in texts)


def test_the_headers_stacked_are_a_setting_of_the_setup(world, chat):
    card = _run(world, chat, pick=[("Headers", "Headers, one above the other")])
    assert len(card.lines) == 1 and card.lines[0].startswith(world.wizard.SECTION_HEADERS)
    card.apply_requested.emit()
    assert world.applied == [{world.wizard.SECTION_HEADERS: "stacked"}]
    assert chat.wizard.revert() is True
    assert world.applied[-1] == {world.wizard.SECTION_HEADERS: "rail"}


def test_with_the_headers_stacked_the_tour_speaks_of_headers(world, chat):
    chat._parent_widget._fm_sections.stacked = True
    world.tour.WelcomeTour(chat).show()
    texts = [text for kind, text in chat.panel.said if kind == "text"]
    assert not any("rail" in text for text in texts)
    assert any("Right-click its header" in text for text in texts)
    assert any("Right-click the header of a section, or the title of a panel" in text for text in texts)


def test_the_tour_waits_for_the_end_of_a_request(world, chat):
    chat.busy = True
    assert world.tour.WelcomeTour(chat).show() is False
    assert chat.panel.said == [] and "Wait" in chat.status[-1]


def test_a_model_connected_is_not_offered_by_the_tour(world, chat):
    world.ready = True
    world.tour.WelcomeTour(chat).show()
    assert ("link", "Connect a model") not in chat.panel.said
