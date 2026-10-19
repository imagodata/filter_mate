"""Budgets and explicit outcomes for in-memory copies of remote vectors.

This module owns no QGIS objects and never formats a key literal.
"""

import math
import time
from dataclasses import dataclass
from typing import Any, Tuple

from .source_capability import REMOTE_KEY_LIST_LIMIT


@dataclass(frozen=True)
class MaterializationLimits:
    """Maximum rows read, total elapsed seconds and keys sent to a service."""

    max_features: int = 20000
    timeout_seconds: float = 90.0
    key_limit: int = REMOTE_KEY_LIST_LIMIT

    def __post_init__(self):
        for value in (self.max_features, self.key_limit):
            if type(value) is not int or value <= 0:
                raise ValueError("Materialization limits must be positive integers")
        if self.key_limit > REMOTE_KEY_LIST_LIMIT:
            raise ValueError("Materialization cannot increase the remote key-list limit")
        value = self.timeout_seconds
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("Materialization timeout must be finite and positive")


@dataclass(frozen=True)
class MaterializationOutcome:
    """Exact keys for the rows examined; ``complete`` only on clean exhaustion.

    ``feature_limit`` and ``timeout`` may carry partial keys. Cancellation,
    errors and key overflow carry no keys and must never change a subset.
    """

    keys: Tuple[Any, ...] = ()
    complete: bool = False
    fetched: int = 0
    reason: str = ""


def collect_materialization(features, key, matches, limits, is_cancelled=lambda: False, clock=time.monotonic):
    """Evaluate copied features under a shared read and evaluation budget.

    Args:
        features: Closable iterator of independent feature copies.
        key: Stable key extractor, raising on an unusable key.
        matches: Exact local predicate; exceptions refuse the entire result.
        limits: Validated materialization limits.
        is_cancelled: Cancellation callback, checked before and after reads.
        clock: Monotonic seconds (injectable for tests).

    Returns:
        MaterializationOutcome with a machine-readable, credential-free reason.
    """
    deadline = clock() + limits.timeout_seconds
    keys = dict()
    fetched = 0

    def outcome(reason=""):
        discard = reason not in ("", "feature_limit", "timeout")
        return MaterializationOutcome(() if discard else tuple(keys), not reason, fetched, reason)

    def stop_reason():
        if is_cancelled():
            return "cancelled"
        return "timeout" if clock() >= deadline else ""

    try:
        while True:
            reason = stop_reason()
            if reason:
                return outcome(reason)
            try:
                feature = next(features)
            except StopIteration:
                return outcome(stop_reason())
            fetched += 1
            reason = stop_reason()
            if reason:
                return outcome(reason)
            if fetched > limits.max_features:
                return outcome("feature_limit")
            if matches(feature):
                value = key(feature)
                if value is None:
                    return outcome("invalid_key")
                keys[value] = None
                if len(keys) > limits.key_limit:
                    return outcome("key_limit")
            reason = stop_reason()
            if reason:
                return outcome(reason)
    except Exception:
        # Never expose provider exceptions: they can contain credentials.
        return outcome("read_error")
    finally:
        close = getattr(features, "close", None)
        if close is not None:
            close()
