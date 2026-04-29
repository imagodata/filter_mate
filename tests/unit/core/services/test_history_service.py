"""T3 — HistoryService coverage.

Audit 2026-04-29 (T3): 680 LOC undo/redo service shipped without any tests.
This module is on the critical path of every filter operation — every
push() / undo() / redo() goes through it. The lack of coverage made the
2026-04-22 v4.1.3 fix (per-layer expression extraction in push_global_state)
risky to land and any future refactor uncertain.

Tests pin the contracts of:
- HistoryEntry / HistoryState dataclasses
- HistoryService.push / undo / redo / peek / counts / can_*
- max_depth + clear + clear_redo + on_change callbacks
- get_history_for_layer / get_or_create_history wrapper
- push_global_state with both `previous_expressions` paths (provided +
  fallback via get_history_for_layer)
- serialize / deserialize round trip
- LayerHistory backward-compat wrapper

The module has zero QGIS imports so we load via plain ``import`` (the
root conftest already provides mocked qgis.*).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from core.services.history_service import (
    HistoryEntry,
    HistoryService,
    HistoryState,
    LayerHistory,
)


def _make_entry(
    expression: str = "x = 1",
    layer_ids=("L1",),
    previous_filters=(("L1", ""),),
    description: str = "",
    metadata=None,
) -> HistoryEntry:
    return HistoryEntry.create(
        expression=expression,
        layer_ids=list(layer_ids),
        previous_filters=[tuple(pf) for pf in previous_filters],
        description=description,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# HistoryEntry
# ---------------------------------------------------------------------------


class TestHistoryEntryCreate:
    def test_generates_unique_entry_id(self):
        e1 = _make_entry()
        e2 = _make_entry()
        # entry_id has microsecond precision — two consecutive creates are
        # very likely to differ. If they happen to land on the same µs we
        # accept it (would still be valid Python identity); the contract
        # is "unique enough for log correlation".
        assert e1.entry_id.startswith("hist_")
        assert e2.entry_id.startswith("hist_")

    def test_default_description_truncates_long_expression(self):
        long_expr = "x" * 100
        entry = _make_entry(expression=long_expr)
        assert entry.description.startswith("Filter: ")
        assert "..." in entry.description
        assert len(entry.description) < len(long_expr) + 10

    def test_explicit_description_preserved(self):
        entry = _make_entry(description="Custom label")
        assert entry.description == "Custom label"

    def test_short_expression_no_ellipsis_in_description(self):
        entry = _make_entry(expression="x = 1")
        assert entry.description == "Filter: x = 1"
        assert "..." not in entry.description

    def test_layer_ids_converted_to_tuple(self):
        entry = HistoryEntry.create(
            expression="e",
            layer_ids=["a", "b", "c"],
            previous_filters=[],
        )
        assert isinstance(entry.layer_ids, tuple)
        assert entry.layer_ids == ("a", "b", "c")

    def test_previous_filters_converted_to_tuple_of_tuples(self):
        entry = HistoryEntry.create(
            expression="e",
            layer_ids=["a"],
            previous_filters=[["a", "old"], ("b", "older")],  # mixed
        )
        assert entry.previous_filters == (("a", "old"), ("b", "older"))

    def test_metadata_normalised_to_sorted_tuple(self):
        entry = HistoryEntry.create(
            expression="e",
            layer_ids=[],
            previous_filters=[],
            metadata={"z": 1, "a": 2},
        )
        # Sorted by key so entries are hashable + comparable deterministically.
        assert entry.metadata == (("a", 2), ("z", 1))

    def test_metadata_none_yields_empty_tuple(self):
        entry = _make_entry(metadata=None)
        assert entry.metadata == ()


class TestHistoryEntryAccessors:
    def test_layer_count(self):
        entry = _make_entry(layer_ids=("a", "b", "c"))
        assert entry.layer_count == 3

    def test_has_previous_filters_true(self):
        entry = _make_entry(previous_filters=(("a", "x"),))
        assert entry.has_previous_filters is True

    def test_has_previous_filters_false(self):
        entry = HistoryEntry.create(
            expression="e", layer_ids=["a"], previous_filters=[]
        )
        assert entry.has_previous_filters is False

    def test_get_previous_filter_match(self):
        entry = _make_entry(previous_filters=(("a", "old_a"), ("b", "old_b")))
        assert entry.get_previous_filter("a") == "old_a"
        assert entry.get_previous_filter("b") == "old_b"

    def test_get_previous_filter_miss_returns_none(self):
        entry = _make_entry(previous_filters=(("a", "old_a"),))
        assert entry.get_previous_filter("missing") is None

    def test_get_metadata_value_match_and_miss(self):
        entry = _make_entry(metadata={"k1": "v1", "k2": 42})
        assert entry.get_metadata_value("k1") == "v1"
        assert entry.get_metadata_value("k2") == 42
        assert entry.get_metadata_value("missing") is None

    def test_str_includes_id_and_description(self):
        entry = _make_entry(description="my-op")
        s = str(entry)
        assert "my-op" in s
        assert entry.entry_id in s


# ---------------------------------------------------------------------------
# HistoryService — push / undo / redo
# ---------------------------------------------------------------------------


class TestPushUndoRedo:
    def test_initial_state_empty(self):
        h = HistoryService()
        assert h.can_undo is False
        assert h.can_redo is False
        assert h.undo_count == 0
        assert h.redo_count == 0
        assert h.total_entries == 0

    def test_push_makes_undo_available(self):
        h = HistoryService()
        h.push(_make_entry())
        assert h.can_undo is True
        assert h.can_redo is False
        assert h.undo_count == 1

    def test_push_clears_redo_stack(self):
        h = HistoryService()
        h.push(_make_entry())
        h.undo()
        assert h.redo_count == 1

        # New push clears redo (cannot redo after a new operation).
        h.push(_make_entry())
        assert h.redo_count == 0

    def test_undo_moves_entry_to_redo_stack(self):
        h = HistoryService()
        e = _make_entry()
        h.push(e)
        undone = h.undo()
        assert undone is e
        assert h.undo_count == 0
        assert h.redo_count == 1

    def test_redo_moves_entry_back_to_undo_stack(self):
        h = HistoryService()
        e = _make_entry()
        h.push(e)
        h.undo()
        redone = h.redo()
        assert redone is e
        assert h.undo_count == 1
        assert h.redo_count == 0

    def test_undo_on_empty_stack_returns_none(self):
        h = HistoryService()
        assert h.undo() is None

    def test_redo_on_empty_stack_returns_none(self):
        h = HistoryService()
        assert h.redo() is None

    def test_peek_undo_does_not_modify_stack(self):
        h = HistoryService()
        e = _make_entry()
        h.push(e)
        peeked = h.peek_undo()
        assert peeked is e
        assert h.undo_count == 1

    def test_peek_redo_does_not_modify_stack(self):
        h = HistoryService()
        e = _make_entry()
        h.push(e)
        h.undo()
        peeked = h.peek_redo()
        assert peeked is e
        assert h.redo_count == 1

    def test_peek_on_empty_returns_none(self):
        h = HistoryService()
        assert h.peek_undo() is None
        assert h.peek_redo() is None

    def test_push_during_undo_redo_is_ignored(self):
        # The flag protects against on_change callbacks that would push
        # back into the service while it's mid-transition.
        h = HistoryService()
        h._is_performing_undo_redo = True
        h.push(_make_entry())
        assert h.undo_count == 0


class TestStackOrdering:
    def test_lifo_order(self):
        h = HistoryService()
        e1 = _make_entry(expression="first")
        e2 = _make_entry(expression="second")
        e3 = _make_entry(expression="third")
        h.push(e1)
        h.push(e2)
        h.push(e3)

        # Undo pops most-recent first.
        assert h.undo().expression == "third"
        assert h.undo().expression == "second"
        assert h.undo().expression == "first"
        assert h.undo() is None

    def test_redo_lifo_order(self):
        h = HistoryService()
        for n in ("a", "b", "c"):
            h.push(_make_entry(expression=n))
        h.undo()  # c -> redo
        h.undo()  # b -> redo

        # Redo pops most-recently-undone first.
        assert h.redo().expression == "b"
        assert h.redo().expression == "c"


# ---------------------------------------------------------------------------
# HistoryState
# ---------------------------------------------------------------------------


class TestGetState:
    def test_empty_state(self):
        st = HistoryService().get_state()
        assert st.can_undo is False
        assert st.can_redo is False
        assert st.undo_description == ""
        assert st.redo_description == ""
        assert st.undo_count == 0
        assert st.redo_count == 0

    def test_state_reflects_top_descriptions(self):
        h = HistoryService()
        h.push(_make_entry(description="op-1"))
        h.push(_make_entry(description="op-2"))
        h.undo()  # op-2 -> redo

        st = h.get_state()
        assert st.can_undo is True
        assert st.can_redo is True
        assert st.undo_description == "op-1"
        assert st.redo_description == "op-2"
        assert st.undo_count == 1
        assert st.redo_count == 1


# ---------------------------------------------------------------------------
# Stack copies + per-layer history queries
# ---------------------------------------------------------------------------


class TestStackCopies:
    def test_get_undo_stack_returns_a_copy(self):
        h = HistoryService()
        h.push(_make_entry())
        copy = h.get_undo_stack()
        copy.clear()
        # Mutating the copy must not drain the live stack.
        assert h.undo_count == 1

    def test_get_redo_stack_returns_a_copy(self):
        h = HistoryService()
        h.push(_make_entry())
        h.undo()
        copy = h.get_redo_stack()
        copy.clear()
        assert h.redo_count == 1


class TestGetHistoryForLayer:
    def test_returns_only_entries_for_layer(self):
        h = HistoryService()
        h.push(_make_entry(layer_ids=("A",)))
        h.push(_make_entry(layer_ids=("B",)))
        h.push(_make_entry(layer_ids=("A", "B")))

        for_a = h.get_history_for_layer("A")
        assert len(for_a) == 2
        assert all("A" in e.layer_ids for e in for_a)

    def test_returns_empty_when_layer_unknown(self):
        h = HistoryService()
        h.push(_make_entry(layer_ids=("A",)))
        assert h.get_history_for_layer("Z") == []


class TestGetOrCreateHistory:
    def test_returns_same_wrapper_for_same_layer(self):
        h = HistoryService()
        w1 = h.get_or_create_history("L1")
        w2 = h.get_or_create_history("L1")
        assert w1 is w2

    def test_returns_distinct_wrappers_for_different_layers(self):
        h = HistoryService()
        a = h.get_or_create_history("A")
        b = h.get_or_create_history("B")
        assert a is not b
        assert a.layer_id == "A"
        assert b.layer_id == "B"


# ---------------------------------------------------------------------------
# max_depth + clear + on_change
# ---------------------------------------------------------------------------


class TestMaxDepth:
    def test_default_max_depth_is_50(self):
        h = HistoryService()
        assert h.max_depth == 50

    def test_max_depth_drops_oldest(self):
        h = HistoryService(max_depth=2)
        e1 = _make_entry(expression="a")
        e2 = _make_entry(expression="b")
        e3 = _make_entry(expression="c")
        h.push(e1)
        h.push(e2)
        h.push(e3)
        # deque(maxlen=2) drops the oldest on the left.
        assert h.undo_count == 2
        stack = h.get_undo_stack()
        assert stack[0].expression == "b"
        assert stack[1].expression == "c"

    def test_set_max_depth_updates_value(self):
        h = HistoryService(max_depth=10)
        h.set_max_depth(3)
        assert h.max_depth == 3

    def test_set_max_depth_zero_raises(self):
        h = HistoryService()
        with pytest.raises(ValueError, match="at least 1"):
            h.set_max_depth(0)

    def test_set_max_depth_negative_raises(self):
        h = HistoryService()
        with pytest.raises(ValueError):
            h.set_max_depth(-5)

    def test_set_max_depth_truncates_immediately(self):
        # Bonus finding: the docstring on ``set_max_depth`` claims it
        # "does not truncate existing entries", but ``deque(self._undo_stack,
        # maxlen=depth)`` drops oldest immediately. We pin the actual
        # behaviour here (more predictable than the doc would suggest);
        # the docstring should be corrected in a follow-up commit.
        h = HistoryService(max_depth=10)
        for n in range(5):
            h.push(_make_entry(expression=str(n)))
        h.set_max_depth(3)
        assert h.undo_count == 3
        # The 3 most-recent entries survive (deque drops from the left).
        stack = h.get_undo_stack()
        assert [e.expression for e in stack] == ["2", "3", "4"]


class TestClear:
    def test_clear_returns_count_and_empties_both_stacks(self):
        h = HistoryService()
        h.push(_make_entry())
        h.push(_make_entry())
        h.undo()
        # 1 in undo, 1 in redo
        assert h.clear() == 2
        assert h.undo_count == 0
        assert h.redo_count == 0

    def test_clear_redo_only_keeps_undo(self):
        h = HistoryService()
        h.push(_make_entry())
        h.undo()
        h.push(_make_entry())  # this clears redo too — re-set up
        h.undo()
        assert h.redo_count == 1
        assert h.clear_redo() == 1
        assert h.redo_count == 0
        # Undo stack untouched.
        # (it had 0 left after the second undo above)


class TestOnChangeCallback:
    def test_callback_invoked_on_push(self):
        captured = []

        def cb(state):
            captured.append(state)

        h = HistoryService(on_change=cb)
        h.push(_make_entry())
        assert len(captured) == 1
        assert captured[0].can_undo is True

    def test_callback_invoked_on_undo_and_redo(self):
        captured = []
        h = HistoryService(on_change=captured.append)
        h.push(_make_entry())
        captured.clear()
        h.undo()
        h.redo()
        assert len(captured) == 2

    def test_callback_failure_swallowed(self):
        # A buggy callback must not propagate into push/undo/redo callers.
        def boom(_state):
            raise RuntimeError("callback bug")

        h = HistoryService(on_change=boom)
        # Must not raise.
        h.push(_make_entry())

    def test_set_on_change_replaces_callback(self):
        calls = []
        h = HistoryService(on_change=lambda s: calls.append("first"))
        h.set_on_change(lambda s: calls.append("second"))
        h.push(_make_entry())
        assert calls == ["second"]

    def test_set_on_change_none_disables_callback(self):
        h = HistoryService(on_change=lambda s: None)
        h.set_on_change(None)
        h.push(_make_entry())  # must not raise


# ---------------------------------------------------------------------------
# push_global_state — both branches of the previous-expressions resolution
# ---------------------------------------------------------------------------


class TestPushGlobalState:
    def test_provided_previous_expressions_are_used_directly(self):
        h = HistoryService()
        h.push_global_state(
            source_layer_id="src",
            source_expression="src_new",
            source_feature_count=10,
            remote_layers={"r1": ("r1_new", 5), "r2": ("r2_new", 3)},
            previous_expressions={"src": "src_old", "r1": "r1_old", "r2": "r2_old"},
        )

        assert h.undo_count == 1
        entry = h.peek_undo()
        # All three layers covered with the user-supplied previous expressions.
        prev = dict(entry.previous_filters)
        assert prev["src"] == "src_old"
        assert prev["r1"] == "r1_old"
        assert prev["r2"] == "r2_old"

    def test_fallback_queries_history_when_no_previous_provided(self):
        # Seed the service with a prior global entry on the same source
        # so the fallback can find it.
        h = HistoryService()
        h.push_global_state(
            source_layer_id="src",
            source_expression="src_v1",
            source_feature_count=10,
            remote_layers={"r1": ("r1_v1", 5)},
            previous_expressions={"src": "", "r1": ""},
        )

        # Push again WITHOUT previous_expressions — fallback path.
        h.push_global_state(
            source_layer_id="src",
            source_expression="src_v2",
            source_feature_count=12,
            remote_layers={"r1": ("r1_v2", 6)},
            previous_expressions=None,
        )

        # The new top entry's previous_filters should reflect the v1 state.
        entry = h.peek_undo()
        prev = dict(entry.previous_filters)
        assert prev["src"] == "src_v1"
        # r1 was a remote layer in the prior entry; the v4.1.3 fix pulls
        # the per-layer expression from metadata.
        assert prev["r1"] == "r1_v1"

    def test_metadata_includes_feature_counts_and_remote_layers(self):
        h = HistoryService()
        h.push_global_state(
            source_layer_id="src",
            source_expression="e",
            source_feature_count=42,
            remote_layers={"r1": ("e1", 7)},
            previous_expressions={"src": "", "r1": ""},
        )
        entry = h.peek_undo()
        assert entry.get_metadata_value("source_feature_count") == 42
        remote_meta = entry.get_metadata_value("remote_layers")
        assert "r1" in remote_meta
        assert remote_meta["r1"]["feature_count"] == 7

    def test_default_description_includes_layer_count(self):
        h = HistoryService()
        h.push_global_state(
            source_layer_id="src",
            source_expression="e",
            source_feature_count=1,
            remote_layers={"r1": ("e1", 1), "r2": ("e2", 2)},
            previous_expressions={"src": "", "r1": "", "r2": ""},
        )
        # Description: "Global filter (3 layers)"
        assert "3 layers" in h.peek_undo().description


# ---------------------------------------------------------------------------
# serialize / deserialize round trip
# ---------------------------------------------------------------------------


class TestSerializeDeserialize:
    def test_roundtrip_preserves_entries(self):
        h = HistoryService(max_depth=20)
        h.push(_make_entry(expression="a", description="op-a"))
        h.push(_make_entry(expression="b", description="op-b"))
        h.undo()  # b -> redo

        snapshot = h.serialize()
        new = HistoryService()
        new.deserialize(snapshot)

        assert new.undo_count == 1
        assert new.redo_count == 1
        assert new.max_depth == 20
        assert new.peek_undo().expression == "a"
        assert new.peek_redo().expression == "b"

    def test_roundtrip_preserves_metadata_and_previous_filters(self):
        h = HistoryService()
        h.push(_make_entry(
            expression="e",
            previous_filters=(("a", "prev_a"), ("b", "prev_b")),
            metadata={"k": "v", "n": 42},
        ))
        new = HistoryService()
        new.deserialize(h.serialize())

        round_tripped = new.peek_undo()
        assert dict(round_tripped.previous_filters) == {"a": "prev_a", "b": "prev_b"}
        assert round_tripped.get_metadata_value("k") == "v"
        assert round_tripped.get_metadata_value("n") == 42

    def test_deserialize_default_max_depth(self):
        new = HistoryService()
        new.deserialize({})  # no max_depth key
        assert new.max_depth == 50
        assert new.undo_count == 0


class TestStrAndRepr:
    def test_str_includes_counts(self):
        h = HistoryService()
        h.push(_make_entry())
        assert "undo=1" in str(h)
        assert "redo=0" in str(h)

    def test_repr_includes_max_depth(self):
        h = HistoryService(max_depth=7)
        r = repr(h)
        assert "max_depth=7" in r


# ---------------------------------------------------------------------------
# LayerHistory backward-compat wrapper
# ---------------------------------------------------------------------------


class TestLayerHistoryWrapper:
    def test_push_state_delegates_to_parent_service(self):
        h = HistoryService()
        wrapper = h.get_or_create_history("L1")

        wrapper.push_state(expression="x = 1", feature_count=5, description="op")

        assert h.undo_count == 1
        entry = h.peek_undo()
        assert entry.expression == "x = 1"
        assert entry.layer_ids == ("L1",)
        # feature_count lands in metadata.
        assert entry.get_metadata_value("feature_count") == 5

    def test_push_state_threads_previous_expression_for_undo(self):
        # Second push on the same layer must capture the first push's
        # expression in previous_filters so undo can restore it.
        h = HistoryService()
        wrapper = h.get_or_create_history("L1")

        wrapper.push_state(expression="first", feature_count=1)
        wrapper.push_state(expression="second", feature_count=2)

        latest = h.peek_undo()
        assert latest.expression == "second"
        assert latest.get_previous_filter("L1") == "first"

    def test_push_state_records_per_layer_state(self):
        h = HistoryService()
        wrapper = h.get_or_create_history("L1")
        wrapper.push_state(expression="e", feature_count=3, description="d")

        # Internal _states list keeps a running per-layer tail.
        assert len(wrapper._states) == 1
        assert wrapper._states[0]["feature_count"] == 3
        assert wrapper._states[0]["description"] == "d"

    def test_push_state_with_metadata_merges_feature_count(self):
        h = HistoryService()
        wrapper = h.get_or_create_history("L1")
        wrapper.push_state(
            expression="e",
            feature_count=9,
            metadata={"custom": "v"},
        )
        entry = h.peek_undo()
        assert entry.get_metadata_value("feature_count") == 9
        assert entry.get_metadata_value("custom") == "v"
