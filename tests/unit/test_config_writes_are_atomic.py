# -*- coding: utf-8 -*-
"""
Every writer of config.json goes through ``atomic_json_write``.

``open(path, 'w')`` truncates the file before anything is written: a crash or
a serialization error left half a config.json (and these writers used the
platform encoding). The writers below call ``atomic_json_write`` (temp file +
``os.replace``, UTF-8) and no longer open anything for writing.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_WRITERS = [
    "filter_mate_app.py",
    "adapters/variables_manager.py",
    "adapters/database_manager.py",
    "ui/managers/config_model_manager.py",
    "config/config.py",
]


def _write_opens(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
            if any(flag in str(mode) for flag in "wax+"):
                yield node.lineno


@pytest.mark.parametrize("path", _WRITERS)
def test_no_truncating_write_in_config_writers(path):
    tree = ast.parse((_ROOT / path).read_text(encoding="utf-8"))
    assert list(_write_opens(tree)) == [], f"{path}: open(..., 'w') on a config file"


@pytest.mark.parametrize("path", _WRITERS)
def test_config_writers_use_atomic_json_write(path):
    assert "atomic_json_write" in (_ROOT / path).read_text(encoding="utf-8")
