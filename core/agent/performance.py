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
_TIMING = re.compile(r"⏱\s*(?:\[FM5\]\s*)?(?P<operation>[^:]+?):\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s)\b\s*(?P<detail>.*)$")
_IN_SECONDS = re.compile(r"⏱\s*\[FM5\]\s*(?P<operation>.+?)\s+in\s+(?P<value>\d+(?:\.\d+)?)s\b\s*(?P<detail>.*)$")
_TIMEOUT = re.compile(r"time(?:d)? ?out|timeout|statement_timeout|canceling statement", re.I)
MAX_SLOWEST = 8
MAX_DETAIL = 160


def _timing(message: str) -> Optional[Dict[str, Any]]:
    match = _TIMING.search(message)
    if match:
        value = float(match["value"]) * (1 if match["unit"] == "ms" else 1000)
    else:
        match = _IN_SECONDS.search(message)
        if not match:
            return None
        value = float(match["value"]) * 1000
    return {"operation": match["operation"].strip(), "ms": round(value),
            "detail": match["detail"].strip(" ()")[:MAX_DETAIL]}


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
