# -*- coding: utf-8 -*-
"""
Readable text of a favorite for the favorites manager.

Pure helpers: they take a ``FilterFavorite`` and a ``tr`` callable and return
plain strings, so they run (and are tested) without a QGIS runtime. Every
user-facing string goes through ``tr`` with an English source.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

try:  # QLocale is only used for the short date; absent or mocked in unit tests
    from qgis.PyQt.QtCore import QDate, QLocale
except Exception:  # pragma: no cover - qgis not importable at all
    QDate = QLocale = None

# Predicate keys FilterMate stores (core/domain/api_requests.py PREDICATES,
# ui/controllers/filtering_controller.py). "Within" is accepted as an alias of
# "Are within" for favorites written by hand or by older versions.
PREDICATE_LABELS: Dict[str, str] = {
    "Intersect": "Intersect",
    "Contain": "Contain",
    "Disjoint": "Disjoint",
    "Equal": "Equal",
    "Touch": "Touch",
    "Overlap": "Overlap",
    "Are within": "Within",
    "Within": "Within",
    "Cross": "Cross",
}

_SEP = " · "


def _format_number(value: float) -> str:
    """25.0 -> '25', 2.5 -> '2.5'."""
    return f"{value:g}"


def _filter_text(favorite) -> str:
    expression = (favorite.expression or "").strip()
    if not expression:
        return ""
    layer = (favorite.layer_name or "").strip()
    return f"{layer} : {expression}" if layer else expression


def _remote_name(key: str, payload) -> str:
    name = ""
    if isinstance(payload, dict):
        name = str(payload.get("display_name") or "").strip()
    if not name:
        name = str(key).split("::", 1)[-1]
    return name


def _remote_text(favorite, tr: Callable[[str], str]) -> str:
    remotes = favorite.remote_layers
    if not remotes or not isinstance(remotes, dict):
        return ""
    parts: List[str] = []
    for key, payload in remotes.items():
        name = _remote_name(key, payload)
        count = payload.get("feature_count") if isinstance(payload, dict) else None
        parts.append(f"{name} ({count})" if count is not None else name)
    if not parts:
        return ""
    head = tr("{0} layers").format(len(parts))
    return f"{head} : {_SEP.join(parts)}"


def _spatial_text(favorite, tr: Callable[[str], str]) -> str:
    config = favorite.spatial_config
    if not config or not isinstance(config, dict):
        return ""
    predicates = config.get("geometric_predicates") or []
    parts: List[str] = []
    if predicates:
        labels = [tr(PREDICATE_LABELS.get(str(p), str(p))) for p in predicates]
        parts.append(", ".join(labels))
    try:
        buffer_value = float(config.get("buffer_value") or 0)
    except (TypeError, ValueError):
        buffer_value = 0.0
    if buffer_value:
        parts.append(tr("buffer {0}").format(_format_number(buffer_value)))
    return _SEP.join(parts)


def summary_rows(favorite, tr: Callable[[str], str]) -> List[Tuple[str, str]]:
    """Ordered (label, text) rows describing a favorite; empty rows are left out."""
    candidates = [
        (tr("Filter"), _filter_text(favorite)),
        (tr("Then"), _remote_text(favorite, tr)),
        (tr("Spatial"), _spatial_text(favorite, tr)),
        (tr("Tags"), ", ".join(str(t) for t in (favorite.tags or []))),
    ]
    return [(label, text) for label, text in candidates if text]


def scope_badge(is_global: bool, tr: Callable[[str], str]) -> str:
    """Badge text of the favorite's scope."""
    if is_global:
        return tr("Global · this computer")
    return tr("Project · shared")


def use_text(use_count: int, last_used_at: Optional[str], tr: Callable[[str], str]) -> str:
    """'Never used' / 'Used 1 time' / 'Used N times'."""
    try:
        count = int(use_count or 0)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return tr("Never used")
    if count == 1:
        return tr("Used {0} time").format(count)
    return tr("Used {0} times").format(count)


def date_text(iso: Optional[str]) -> str:
    """Short date of an ISO timestamp; '-' when empty or unreadable.

    Uses the QLocale short format when QLocale is a real Qt class, else
    falls back to ``%d/%m/%Y``.
    """
    if not iso:
        return "-"
    try:
        moment = datetime.fromisoformat(str(iso).strip())
    except (TypeError, ValueError):
        return "-"
    if isinstance(QLocale, type) and isinstance(QDate, type):
        try:
            short = getattr(QLocale, "ShortFormat", None)
            if short is None:  # Qt6 scoped enum
                short = QLocale.FormatType.ShortFormat
            return QLocale().toString(QDate(moment.year, moment.month, moment.day), short)
        except Exception:
            pass
    return moment.strftime("%d/%m/%Y")
