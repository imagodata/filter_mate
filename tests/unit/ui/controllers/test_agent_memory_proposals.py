import sys
from types import SimpleNamespace

import pytest

from .test_agent_chat_lifecycle import FakeSignal, _PKG, controller, ctrl_module, dock

pytestmark = pytest.mark.unit


class Card:
    def __init__(self, text, editable):
        self.value = text
        self.done = False
        self.can_undo = False
        self.chosen = FakeSignal()
        self.undo_requested = FakeSignal()
        self.text = SimpleNamespace(isReadOnly=lambda: not editable)

    def objectName(self):
        return "memory"

    def current_text(self):
        return self.value

    def finish(self, result, can_undo=False):
        self.done = True
        self.result = result
        self.can_undo = can_undo


@pytest.fixture
def memory_setup(ctrl_module, controller, monkeypatch):
    memory = sys.modules[f"{_PKG}.core.agent.memory"]
    state = SimpleNamespace(memory=memory.Memory(), cards=[], writes=0, notes=[])
    monkeypatch.setattr(ctrl_module, "read_memory", lambda: state.memory)

    def change(changes):
        state.memory = memory.applied(state.memory, changes, today="2026-11-26")
        state.writes += 1
        return state.memory

    def card(_texts, text, editable, _buttons, _notes):
        result = Card(text, editable)
        state.cards.append(result)
        return result

    def write_notes(notes):
        state.notes = list(notes)

    monkeypatch.setattr(ctrl_module, "change_memory", change)
    monkeypatch.setattr(ctrl_module, "read_notes", lambda: list(state.notes))
    monkeypatch.setattr(ctrl_module, "write_notes", write_notes)
    monkeypatch.setattr(ctrl_module, "project_sources", lambda *args: ([], ""))
    monkeypatch.setattr(controller, "_read_project", lambda: ([], [], {}))
    monkeypatch.setattr(controller, "_show_agent", lambda: None)
    monkeypatch.setattr(controller, "_memory_first_note", lambda: "")
    controller.panel.add_memory_card.side_effect = card
    return state, memory


def test_proposing_writes_nothing_until_the_user_keeps_it(controller, memory_setup):
    state, _memory = memory_setup
    answer = controller._add_note_tool({"scope": "user", "text": "RD = route départementale"})
    assert answer["proposed"] and state.writes == 0 and state.memory.notes == ()
    card = state.cards[0]
    card.chosen.emit("user", "RD = route départementale")
    assert card.done and card.can_undo
    assert state.memory.notes[0].text == "RD = route départementale"
    card.undo_requested.emit()
    assert state.memory.notes == () and not card.can_undo


def test_the_current_request_recalls_an_older_shared_fact(controller, memory_setup):
    state, memory = memory_setup
    state.memory, _note = memory.added(state.memory, "MRO = zone de mutualisation. " + "a" * 260)
    for rank in range(20):
        state.memory, _note = memory.added(state.memory, f"Other fact {rank}: " + "b" * 280)
    controller._last_request = "Affiche les MRO"
    sent = controller._project_context(full=True)
    assert "- m1: MRO = zone de mutualisation" in sent
    assert state.writes == 0


def test_a_shared_memory_change_from_another_session_is_sent_in_the_next_context(controller, memory_setup):
    state, memory = memory_setup
    state.memory, _note = memory.added(state.memory, "First fact")
    state.memory, _note = memory.added(state.memory, "Second fact")
    assert "First fact" in controller._project_context(full=True)
    controller._context_memory.sent()
    controller._seen = {}
    state.memory = memory.removed(state.memory, "m1")  # another session edited the shared file
    sent = controller._project_context(full=False)
    assert "Second fact" in sent and "First fact" not in sent
    assert "replaces earlier memory blocks" in sent


def test_user_only_memory_does_not_inspect_layer_sources(controller, ctrl_module, memory_setup, monkeypatch):
    state, memory = memory_setup
    state.memory, _note = memory.added(state.memory, "Answer in metres")

    def no_sources(*args):
        pytest.fail("Shared user notes do not need any layer source lookup")

    monkeypatch.setattr(ctrl_module, "project_sources", no_sources)
    assert "Answer in metres" in controller._memory_part(([], [], {}))


def test_a_declined_note_is_not_proposed_again_unless_the_user_undoes_the_choice(controller, memory_setup):
    state, _memory = memory_setup
    arguments = {"scope": "user", "text": "RD = route départementale"}
    controller._add_note_tool(arguments)
    card = state.cards[0]
    card.chosen.emit("decline", "")
    assert controller._add_note_tool(arguments)["declined_before"]
    card.undo_requested.emit()
    assert state.memory.declined == ()
    assert controller._add_note_tool(arguments)["proposed"]


def test_pending_proposals_are_deduplicated_and_bounded(controller, ctrl_module, memory_setup):
    state, _memory = memory_setup
    assert controller._add_note_tool({"scope": "user", "text": "first"})["proposed"]
    assert controller._add_note_tool({"scope": "user", "text": "FIRST"})["proposed_already"]
    controller._add_note_tool({"scope": "user", "text": "second"})
    with pytest.raises(ctrl_module.ToolFailure, match="2 notes"):
        controller._add_note_tool({"scope": "user", "text": "third"})
    assert len(state.cards) == 2


def test_an_undo_never_removes_a_note_edited_since_the_click(controller, memory_setup):
    state, memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "original"})
    card = state.cards[0]
    card.chosen.emit("user", "original")
    state.memory = memory.edited(state.memory, "m1", "corrected elsewhere")
    card.undo_requested.emit()
    assert state.memory.notes[0].text == "corrected elsewhere"


def test_an_existing_note_is_never_claimed_by_the_card_undo(controller, memory_setup):
    state, memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "original"})
    state.memory, _note = memory.added(state.memory, "corrected elsewhere")
    state.cards[0].chosen.emit("user", "corrected elsewhere")
    assert not state.cards[0].can_undo and len(state.memory.notes) == 1


def test_write_failure_keeps_the_card_available_for_another_try(controller, ctrl_module, memory_setup, monkeypatch):
    state, _memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "original"})
    card = state.cards[0]
    change = ctrl_module.change_memory

    def fail(_changes):
        raise OSError("disk full")

    monkeypatch.setattr(ctrl_module, "change_memory", fail)
    card.chosen.emit("user", "original")
    assert not card.done and not state.memory.notes
    monkeypatch.setattr(ctrl_module, "change_memory", change)
    card.chosen.emit("user", "original")
    assert card.done and len(state.memory.notes) == 1


def test_the_generation_of_a_closed_project_blocks_pending_and_completed_card_callbacks(controller, memory_setup):
    state, _memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "kept"})
    kept = state.cards[0]
    kept.chosen.emit("user", "kept")
    controller._add_note_tool({"scope": "user", "text": "pending"})
    pending = state.cards[1]
    controller._reset_view()
    pending.chosen.emit("project", "pending")
    kept.undo_requested.emit()
    assert [note.text for note in state.memory.notes] == ["kept"] and state.notes == []


def test_stop_leaves_unanswered_notes_without_persisting_a_refusal(controller, memory_setup):
    state, _memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "original"})
    controller._on_stop()
    assert state.cards[0].done and state.writes == 0 and state.memory.declined == ()


def test_a_note_corrected_on_the_card_keeps_its_value_sharing_restriction(controller, memory_setup):
    state, memory = memory_setup
    controller._add_note_tool({"scope": "user", "text": "attribute = 42"})
    state.cards[0].chosen.emit("user", "attribute = 42 (corrected)")
    assert state.memory.notes[0].with_values
    assert memory.chosen(state.memory, share_values=False).user == ()


def test_forgetting_is_a_proposal_and_undo_restores_the_exact_note(controller, memory_setup):
    state, memory = memory_setup
    state.memory, note = memory.added(state.memory, "original", with_values=True, today="2026-11-01")
    assert controller._remove_note_tool({"memory": note.id})["proposed"]
    card = state.cards[0]
    assert state.memory.notes == (note,) and state.writes == 0
    card.chosen.emit("forget", note.text)
    assert state.memory.notes == ()
    card.undo_requested.emit()
    assert state.memory.notes == (note,)


def test_a_changed_note_is_never_forgotten_from_a_stale_card(controller, memory_setup):
    state, memory = memory_setup
    state.memory, note = memory.added(state.memory, "original")
    controller._remove_note_tool({"memory": note.id})
    state.memory = memory.edited(state.memory, note.id, "updated")
    state.cards[0].chosen.emit("forget", note.text)
    assert state.memory.notes[0].text == "updated" and state.writes == 0


def test_only_a_memory_note_sent_with_this_project_can_be_proposed_for_forgetting(controller, ctrl_module, memory_setup):
    state, memory = memory_setup
    state.memory, note = memory.added(state.memory, "source fact", "source", "another-source")
    with pytest.raises(ctrl_module.ToolFailure, match="among those sent"):
        controller._remove_note_tool({"memory": note.id})
    assert not state.cards


def test_a_note_omitted_by_the_context_budget_cannot_be_guessed_and_forgotten(controller, ctrl_module, memory_setup):
    state, memory = memory_setup
    for rank in range(25):
        state.memory, note = memory.added(state.memory, f"{rank} " + "fact " * 50)
    sent = controller._memory_part(([], [], {}))
    note = next(note for note in state.memory.notes if f"- {note.id}: " not in sent)
    with pytest.raises(ctrl_module.ToolFailure, match="among those sent"):
        controller._remove_note_tool({"memory": note.id})
    assert not state.cards


def test_project_only_choice_and_undo_leave_other_project_notes_in_place(controller, memory_setup):
    state, _memory = memory_setup
    state.notes = ["existing"]
    controller._add_note_tool({"scope": "user", "text": "proposal"})
    card = state.cards[0]
    card.chosen.emit("project", "proposal")
    state.notes.append("written later")
    card.undo_requested.emit()
    assert state.notes == ["existing", "written later"] and not state.memory.notes
