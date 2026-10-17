# -*- coding: utf-8 -*-
"""
init_env_vars(): a config.json that cannot be read is kept.

A corrupt (or structureless) config.json used to be replaced by the default
settings in memory, and the very next save (or the APP_SQLITE_PATH sync of
the same init) wrote them over the user's file: every setting lost, no way
back. The file is now copied to ``config.json.corrupt-<timestamp>`` first, and
every write of config.json goes through ``atomic_json_write``.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def config_module(monkeypatch, tmp_path):
    """config/config.py with the QGIS surface stubbed and the real atomic_io."""
    for name in ("qgis", "qgis.core", "filter_mate", "filter_mate.core", "filter_mate.core.optimization",
                 "filter_mate.core.optimization.config_provider"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, MagicMock())
    atomic_io = _load_by_path("fmtest_cfg_atomic_io", _ROOT / "infrastructure" / "utils" / "atomic_io.py")
    for name in ("filter_mate.infrastructure", "filter_mate.infrastructure.utils"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, "filter_mate.infrastructure.utils.atomic_io", atomic_io)

    module = _load_by_path("fmtest_cfg_config", _ROOT / "config" / "config.py")
    profile = tmp_path / "profile"
    profile.mkdir()
    monkeypatch.setattr(module, "QgsApplication", types.SimpleNamespace(qgisSettingsDirPath=lambda: str(profile)))
    project = types.SimpleNamespace(readPath=lambda path: str(tmp_path) + "/")
    monkeypatch.setattr(module, "QgsProject", types.SimpleNamespace(instance=lambda: project))
    monkeypatch.setattr(module, "ENV_VARS", {})
    module.profile_config = profile / "FilterMate" / "config.json"
    return module


def _run(module, text):
    module.profile_config.parent.mkdir(parents=True, exist_ok=True)
    module.profile_config.write_text(text, encoding="utf-8")
    module.init_env_vars()
    return sorted(p.name for p in module.profile_config.parent.iterdir())


def test_corrupt_json_is_copied_before_the_defaults_replace_it(config_module):
    names = _run(config_module, '{"APP": {"DOCKWIDGET": {"LANGUAGE": {"value": "fr"')  # truncated
    backups = [n for n in names if n.startswith("config.json.corrupt-")]
    assert len(backups) == 1
    backup = config_module.profile_config.parent / backups[0]
    assert backup.read_text(encoding="utf-8") == '{"APP": {"DOCKWIDGET": {"LANGUAGE": {"value": "fr"'
    # the active file is valid again and no temp file is left behind
    assert isinstance(json.loads(config_module.profile_config.read_text(encoding="utf-8")), dict)
    assert not [n for n in names if n.endswith(".tmp")]


def test_valid_json_missing_sections_is_completed_not_backed_up(config_module):
    """_migrate_config fills the missing sections of a readable file: it stays the user's file."""
    names = _run(config_module, '{"something": "else"}')
    assert not [n for n in names if ".corrupt-" in n]
    assert json.loads(config_module.profile_config.read_text(encoding="utf-8"))["something"] == "else"


def test_a_healthy_config_is_not_backed_up(config_module):
    default = (_ROOT / "config" / "config.default.json").read_text(encoding="utf-8")
    names = _run(config_module, default)
    assert not [n for n in names if ".corrupt-" in n]


def test_a_missing_config_is_created_without_backup(config_module):
    config_module.init_env_vars()
    names = sorted(p.name for p in config_module.profile_config.parent.iterdir())
    assert "config.json" in names
    assert not [n for n in names if ".corrupt-" in n]
