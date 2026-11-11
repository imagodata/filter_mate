# -*- coding: utf-8 -*-
"""Python code written by the model and run in QGIS: the expert mode of the chat, off by default.

The user turned it on in the settings, read the code in full in a dialog and said yes, each time
(``ui/controllers/agent_chat_controller.py``): only then does this run. The code runs on the main thread with the
rights of the user, can read and change anything QGIS and the account can, and is not undone with the turn. It is
written to the log before it runs. Nothing else of the plugin runs code a model wrote, and the MCP servers never
offer this (``chat_only``).
"""
from __future__ import annotations

import io
import logging
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Dict

logger = logging.getLogger("FilterMate.agent")

MAX_CODE_CHARS = 20_000
MAX_OUTPUT_CHARS = 6_000


def _tail(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT_CHARS else "…" + text[-MAX_OUTPUT_CHARS:]


def run_code(code: str, purpose: str = "") -> Dict[str, Any]:
    """Run ``code``; what it printed, the value it left in ``result``, or the error it raised.

    Raises:
        ValueError: No code, too long, or FilterMate busy with another operation.
    """
    from qgis.core import QgsProject
    from ..public_api.operations import busy_reason
    if not code or not code.strip():
        raise ValueError("no code to run")
    if len(code) > MAX_CODE_CHARS:
        raise ValueError(f"{MAX_CODE_CHARS} characters of code at most")
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    try:
        from qgis.utils import iface
    except ImportError:
        iface = None
    logger.warning("Agent expert mode, code confirmed by the user, run now (%s):\n%s", purpose[:200], code)
    namespace: Dict[str, Any] = {"__name__": "__filtermate_agent__", "iface": iface, "project": QgsProject.instance()}
    printed, errors = io.StringIO(), io.StringIO()
    error = None
    with redirect_stdout(printed), redirect_stderr(errors):
        try:
            compiled = compile(code, "<agent code>", "exec")
            # Expert mode: the user turned it on, read this code in full and confirmed this very run.
            exec(compiled, namespace)  # nosec B102
        except Exception:  # its own error, for the model to read and correct
            error = traceback.format_exc(limit=6)
    result = namespace.get("result")
    answer: Dict[str, Any] = {"ok": error is None, "printed": _tail(printed.getvalue())}
    if errors.getvalue():
        answer["stderr"] = _tail(errors.getvalue())
    if error is not None:
        answer["error"] = _tail(error)
    if result is not None:
        answer["result"] = _tail(repr(result))
    answer["note"] = "Not undone with the turn: what the code changed stays as it is."
    return answer
