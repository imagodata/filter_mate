"""QGIS adapter for the :class:`IFeedback` port.

A1 hardening (audit 2026-04-29): the domain (``core/filter/result_processor.py``)
used to import ``iface`` directly at module level. This adapter provides the
QGIS-side implementation so the domain only depends on the abstract port.

The adapter is wired in :meth:`FilterMate.__init__` via
:func:`core.ports.qgis_port.set_feedback_adapter`.
"""
from __future__ import annotations

import logging

from qgis.core import Qgis
from qgis.utils import iface

from ...core.ports.qgis_port import IFeedback, MessageLevel

logger = logging.getLogger("filter_mate")


_LEVEL_MAP: dict[MessageLevel, "Qgis.MessageLevel"] = {
    MessageLevel.INFO: Qgis.Info,
    MessageLevel.WARNING: Qgis.Warning,
    MessageLevel.CRITICAL: Qgis.Critical,
    MessageLevel.SUCCESS: Qgis.Success,
}


class QgisMessageBarFeedback(IFeedback):
    """Push messages onto QGIS' message bar via ``iface.messageBar()``.

    The progress / cancellation methods of :class:`IFeedback` are no-ops here:
    callers that need progress hook into a :class:`QgsTask`'s native
    ``QgsFeedback`` instead. This adapter only covers the user-notification
    side of the port.
    """

    def push_message(
        self,
        title: str,
        message: str,
        level: MessageLevel = MessageLevel.INFO,
    ) -> None:
        bar = iface.messageBar() if iface is not None else None
        if bar is None:
            # Headless / iface not yet ready — log and move on instead of
            # crashing the worker. Same fallback as the legacy code.
            logger.warning("[%s] %s: %s", level.name, title, message)
            return

        qgis_level = _LEVEL_MAP.get(level, Qgis.Info)
        bar.pushMessage(title, message, level=qgis_level)

    def set_progress(self, value: float) -> None:
        # No-op: no progress UI is owned by this adapter.
        return

    def is_canceled(self) -> bool:
        # No-op: cancellation flows through the active QgsTask's QgsFeedback.
        return False

    def set_progress_text(self, text: str) -> None:
        # No-op: progress text is owned by the active QgsTask.
        return
