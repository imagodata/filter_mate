"""Bounded remote reads never describe a truncated result as complete."""

import math

import pytest

from core.domain.materialization import MaterializationLimits, collect_materialization

pytestmark = pytest.mark.unit


def collect(rows, **kwargs):
    return collect_materialization(
        iter(rows), lambda row: row, lambda row: row % 2 == 0, kwargs.pop("limits", MaterializationLimits()), **kwargs
    )


def test_exhaustion_is_complete_and_filters_exactly():
    outcome = collect([1, 2, 3, 4])
    assert outcome.complete and outcome.keys == (2, 4) and outcome.fetched == 4
    assert outcome.reason == ""


def test_limit_requires_lookahead_and_reports_partial():
    limits = MaterializationLimits(max_features=2)
    assert collect([1, 2], limits=limits).complete
    outcome = collect([1, 2, 3], limits=limits)
    assert not outcome.complete and outcome.reason == "feature_limit"
    assert outcome.keys == (2,) and outcome.fetched == 3


def test_key_limit_refuses_instead_of_keeping_the_first_500():
    outcome = collect(range(1002))
    assert not outcome.complete and outcome.reason == "key_limit" and not outcome.keys


def test_duplicate_keys_are_not_counted_twice():
    assert collect([2] * 600).keys == (2,)
    assert collect([2] * 600).complete


def test_cancellation_discards_keys_and_closes_the_iterator():
    closed = []

    def rows():
        try:
            yield 2
            yield 4
        finally:
            closed.append(True)

    calls = iter([False, False, True])
    outcome = collect_materialization(
        rows(), lambda row: row, lambda row: True, MaterializationLimits(), lambda: next(calls, True)
    )
    assert outcome.reason == "cancelled" and not outcome.keys and not outcome.complete
    assert closed


def test_deadline_checks_after_blocking_fetch():
    ticks = iter([0, 0, 100])
    outcome = collect([2], clock=lambda: next(ticks, 100))
    assert not outcome.complete and outcome.reason == "timeout" and not outcome.keys


def test_read_errors_discard_all_keys():
    def rows():
        yield 2
        raise RuntimeError("secret URI must never become a user message")

    outcome = collect_materialization(rows(), lambda row: row, lambda row: True, MaterializationLimits())
    assert outcome.reason == "read_error" and not outcome.keys and not outcome.complete


@pytest.mark.parametrize("value", [0, -1, True, math.inf, math.nan, "20"])
def test_invalid_feature_limits_are_rejected(value):
    with pytest.raises(ValueError):
        MaterializationLimits(max_features=value)


@pytest.mark.parametrize("value", [0, -1, True, math.inf, math.nan, "90"])
def test_invalid_deadlines_are_rejected(value):
    with pytest.raises(ValueError):
        MaterializationLimits(timeout_seconds=value)


def test_key_budget_cannot_exceed_the_shared_server_limit():
    with pytest.raises(ValueError):
        MaterializationLimits(key_limit=501)
