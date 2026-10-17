# -*- coding: utf-8 -*-
"""
Writing config.json from the extension framework.

``BaseExtension._persist_config`` and ``ExtensionRegistry._persist_config`` write
the live CONFIG_DATA back to disk. That dictionary can hold runtime objects (a
psycopg2 connection, a QGIS object), so it is made JSON-safe first, and the file
is swapped in atomically: a failure leaves the previous config.json untouched.

The plugin's ``atomic_json_write`` is used when the extensions run inside the
plugin; a small equivalent keeps them importable (and testable) on their own.
"""

import json
import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def json_safe(obj: Any, _seen: Any = None) -> Any:
    """Copy of ``obj`` that ``json`` can serialise (what cannot be becomes None).

    Connection objects (anything with a ``cursor()``), QGIS objects, sets and the like
    are replaced by None, dict keys by strings, and cycles are cut. ``obj`` is not
    modified.
    """
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    seen = _seen if _seen is not None else set()
    if isinstance(obj, (dict, list, tuple)):
        if id(obj) in seen:
            return None
        seen = seen | {id(obj)}
        if isinstance(obj, dict):
            return {(k if isinstance(k, str) else str(k)): json_safe(v, seen) for k, v in obj.items()}
        return [json_safe(item, seen) for item in obj]
    return None


def _atomic_write(path: str, data: Any, indent: int) -> None:
    """Fallback of ``infrastructure.utils.atomic_io.atomic_json_write`` (temp file + replace)."""
    text = json.dumps(data, indent=indent, ensure_ascii=False)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".fm_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def write_config_json(path: str, data: Any, indent: int = 2) -> bool:
    """Write ``data`` to config.json: JSON-safe, UTF-8, atomically.

    Args:
        path: The config.json to replace.
        data: Live configuration (may hold non-JSON runtime objects).
        indent: JSON indentation.

    Returns:
        bool: True when written; False (with a warning) when not, the previous
        file being left as it was.
    """
    try:
        try:
            from ..infrastructure.utils.atomic_io import atomic_json_write
        except Exception:  # not running inside the plugin
            atomic_json_write = None
        safe = json_safe(data)
        if atomic_json_write is not None:
            atomic_json_write(path, safe, indent=indent)
        else:
            _atomic_write(path, safe, indent)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("Could not persist config.json: %s", exc)
        return False
