# -*- coding: utf-8 -*-
"""What the timings FilterMate logs say: the ``⏱`` lines of its log file, summed up for diagnose_performance.

Plain Python: the caller reads the end of the log and gives its lines.
"""
from __future__ import annotations

import re
from statistics import median
from typing import Any, Dict, Iterable, List, Optional

# 2026-11-11 10:42:03 - FilterMate.Perf - INFO - ⏱ layer_change: 122 ms (batiment (GPKG))
_LINE = re.compile(r"^(?P<time>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) - (?P<logger>\S+) - (?P<level>[A-Z]+) - (?P<message>.*)$")
_MARK = re.compile(r"⏱\s*(?:\[FM5\]\s*)?")
_IN_SECONDS = re.compile(r"^(?P<operation>[^:]+?)\s+in\s+(?P<value>\d+(?:\.\d+)?)s\b\s*(?P<detail>.*)$")
_DURATION = re.compile(r"(?<![\w.])(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s)\b")
# A query cut short, not a setting that names a timeout.
_TIMEOUT = re.compile(r"timed out|time out|canceling statement|timeout expired|statement timeout", re.I)
# Connection details logged with some timings (pg_layer_connect): never sent to a provider.
_SECRET = re.compile(r"\b(host|hostaddr|service|dbname|user|password|port|sslmode)=('[^']*'|\S+)", re.I)
MAX_SLOWEST = 8
MAX_DETAIL = 160
# An operation is a short name (layer_change, pg_layer_connect): a longer one is not a timing of FilterMate but text
# someone else wrote into the log, which this summary would hand to the model (2026-11-13).
MAX_OPERATION = 60


def _timing(message: str) -> Optional[Dict[str, Any]]:
    """``⏱ operation: 12 ms (detail)``, ``⏱ operation: connection 12 ms, ...`` or ``⏱ [FM5] operation in 1.2s ...``."""
    # At the start of the message, as FilterMate logs its timings (logger.info(f"⏱ ...")): a mark in the middle of
    # another message is text someone else wrote, the name of a layer or a skill left out (2026-11-13)
    mark = _MARK.match(message)
    if not mark:
        return None
    text = message[mark.end():]
    match = _IN_SECONDS.match(text)
    if match:
        operation, value, detail = match["operation"], float(match["value"]) * 1000, match["detail"]
    else:
        operation, _colon, rest = text.partition(":")
        duration = _DURATION.search(rest) if _colon else None
        if duration is None:
            return None
        value = float(duration["value"]) * (1 if duration["unit"] == "ms" else 1000)
        detail = (rest[:duration.start()] + rest[duration.end():]).strip(" ,")
    operation, detail = operation.strip(), detail.strip()
    if not operation or len(operation) > MAX_OPERATION:
        return None
    if detail.startswith("(") and detail.endswith(")"):
        detail = detail[1:-1]  # one pair: "(batiment (GPKG))" keeps its own
    detail = _SECRET.sub(lambda found: f"{found[1]}=…", detail)
    return {"operation": operation, "ms": round(value), "detail": detail[:MAX_DETAIL]}


def summary(lines: Iterable[str], max_entries: int = 200) -> Dict[str, Any]:
    """Timings by operation (count, median, max, last), the slowest ones, and the timeouts and errors logged."""
    timings: List[Dict[str, Any]] = []
    timeouts = errors = 0
    first = last = ""
    for raw in lines:
        match = _LINE.match(raw.rstrip("\n"))
        if not match:
            continue
        first, last = first or match["time"], match["time"]
        message, level = match["message"], match["level"]
        if level in ("ERROR", "CRITICAL"):
            errors += 1
        if level in ("WARNING", "ERROR", "CRITICAL") and _TIMEOUT.search(message):
            timeouts += 1
        if "⏱" in message:
            entry = _timing(message)
            if entry is not None:
                entry["time"] = match["time"]
                timings.append(entry)
    timings = timings[-max_entries:]
    by_operation: Dict[str, List[Dict[str, Any]]] = {}
    for entry in timings:
        by_operation.setdefault(entry["operation"], []).append(entry)
    operations = [{"operation": name, "count": len(entries), "median_ms": round(median(e["ms"] for e in entries)),
                   "max_ms": max(e["ms"] for e in entries), "last_ms": entries[-1]["ms"], "last_at": entries[-1]["time"]}
                  for name, entries in by_operation.items()]
    operations.sort(key=lambda row: -row["max_ms"])
    slowest = sorted(timings, key=lambda entry: -entry["ms"])[:MAX_SLOWEST]
    answer: Dict[str, Any] = {"timings": len(timings), "operations": operations, "slowest": slowest,
                              "timeouts_logged": timeouts, "errors_logged": errors}
    if first:
        answer["log_from"], answer["log_to"] = first, last
    if not timings:
        answer["hint"] = "No timing logged yet: ask the user to run the slow filter once, then call this again."
    return answer
