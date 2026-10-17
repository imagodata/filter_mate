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
    """config/config.py with the QGIS surface stubbed and the real atomic_io, loaded as part of a throw-away package.

    config.py imports its helpers RELATIVELY (``..infrastructure.utils.atomic_io``): the package is a
    stand-in for the plugin folder, whatever its name.
    """
    for name in ("qgis", "qgis.core"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, MagicMock())
    pkg = "fmtest_cfg_pkg"
    for name, path in ((pkg, _ROOT), (f"{pkg}.config", _ROOT / "config"), (f"{pkg}.core", _ROOT / "core"),
                       (f"{pkg}.core.optimization", _ROOT / "core" / "optimization"),
                       (f"{pkg}.infrastructure", _ROOT / "infrastructure"),
                       (f"{pkg}.infrastructure.utils", _ROOT / "infrastructure" / "utils"),
                       (f"{pkg}.infrastructure.logging", _ROOT / "infrastructure" / "logging")):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        monkeypatch.setitem(sys.modules, name, package)
    provider = types.ModuleType(f"{pkg}.core.optimization.config_provider")
    provider.get_optimization_thresholds = MagicMock()
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    # the real helpers (the packages above are bare: their __init__ files import the whole plugin)
    for name, path in ((f"{pkg}.infrastructure.utils.atomic_io", _ROOT / "infrastructure" / "utils" / "atomic_io.py"),
                       (f"{pkg}.infrastructure.logging.redaction", _ROOT / "infrastructure" / "logging" / "redaction.py")):
        monkeypatch.setitem(sys.modules, name, _load_by_path(name, path))

    module = _load_by_path(f"{pkg}.config.config", _ROOT / "config" / "config.py")
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


def test_the_same_broken_file_is_kept_once_across_starts(config_module):
    broken = '{"APP": {"truncated'
    _run(config_module, broken)
    _run(config_module, broken)
    names = _run(config_module, broken)
    assert len([n for n in names if ".corrupt-" in n]) == 1


def test_a_missing_atomic_writer_does_not_stop_the_start(config_module, monkeypatch):
    """The import is protected: the file is then written directly and nothing is kept."""
    monkeypatch.setitem(sys.modules, "fmtest_cfg_pkg.infrastructure.utils.atomic_io", None)

    names = _run(config_module, '{"APP": {"truncated')

    assert not [n for n in names if ".corrupt-" in n]
    assert isinstance(json.loads(config_module.profile_config.read_text(encoding="utf-8")), dict)


def test_a_password_saved_by_an_older_version_is_masked_once(config_module):
    default = json.loads((_ROOT / "config" / "config.default.json").read_text(encoding="utf-8"))
    leaked = "dbname='gis' host=h user='bob' password='s3cret' table=\"public\".\"roads\" (geom)"
    default.setdefault("CURRENT_PROJECT", {}).setdefault("OPTIONS", {})["ACTIVE_POSTGRESQL"] = [leaked]
    default["CURRENT_PROJECT"]["OPTIONS"]["note"] = leaked
    config_module.QgsMessageLog.logMessage.reset_mock()

    _run(config_module, json.dumps(default))

    saved = config_module.profile_config.read_text(encoding="utf-8")
    assert "s3cret" not in saved
    options = json.loads(saved)["CURRENT_PROJECT"]["OPTIONS"]
    assert options["ACTIVE_POSTGRESQL"] == "" and "dbname='gis'" in options["note"]
    messages = [call.args[0] for call in config_module.QgsMessageLog.logMessage.call_args_list]
    assert any("2" in m and "password" in m.lower() and "masked" in m for m in messages)
    assert not any("s3cret" in m for m in messages)
    config_module.QgsMessageLog.logMessage.reset_mock()

    _run(config_module, saved)  # next start: nothing left to correct, nothing announced

    assert not any("masked" in call.args[0] for call in config_module.QgsMessageLog.logMessage.call_args_list)
