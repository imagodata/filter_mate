# -*- coding: utf-8 -*-
"""
init_env_vars(): the config.json APP_SQLITE_PATH points to is migrated too.

A QGIS 4 profile whose config.json points (APP_SQLITE_PATH) at the QGIS 3
profile folder read and migrated its own file, then switched CONFIG_JSON_PATH
to the QGIS 3 config.json, which the Configuration tab reloads and saves. That
file, written before FilterMate 5, had no APP.OPTIONS.RASTER / POINT_CLOUD
section: one second after start both layer kinds were off, no raster or point
cloud was registered, and none could be a target (2026-10-18).
"""
import json

import pytest

from tests.unit import test_config_corrupt_backup as _corrupt_backup

pytestmark = pytest.mark.unit

config_module = _corrupt_backup.config_module  # same fixture: config.py with QGIS stubbed


def _old_config(language="fr"):
    """A 4.x config.json: no RASTER section, the experimental point cloud flag off."""
    return {
        "APP": {
            "DOCKWIDGET": {"LANGUAGE": {"value": language}},
            "OPTIONS": {"POINT_CLOUD": {"enabled": {"value": False}}},
        }
    }


def _setup(module, tmp_path, redirected_content):
    other_dir = tmp_path / "QGIS3" / "FilterMate"
    other_dir.parent.mkdir(parents=True)
    if redirected_content is not None:
        other_dir.mkdir()
        text = redirected_content if isinstance(redirected_content, str) else json.dumps(redirected_content)
        (other_dir / "config.json").write_text(text, encoding="utf-8")
    first = _old_config(language="en")
    first["APP"]["OPTIONS"]["APP_SQLITE_PATH"] = {"value": str(other_dir)}
    module.profile_config.parent.mkdir(parents=True, exist_ok=True)
    module.profile_config.write_text(json.dumps(first), encoding="utf-8")
    module.init_env_vars()
    return other_dir / "config.json"


def _enabled(data, section):
    return data["APP"]["OPTIONS"][section]["enabled"]["value"]


def test_the_redirected_config_is_the_one_used_and_it_is_migrated(config_module, tmp_path):
    redirected = _setup(config_module, tmp_path, _old_config(language="fr"))
    env = config_module.ENV_VARS
    assert env["CONFIG_JSON_PATH"] == str(redirected)
    data = env["CONFIG_DATA"]
    # the user's settings of that file are kept ...
    assert data["APP"]["DOCKWIDGET"]["LANGUAGE"]["value"] == "fr"
    # ... and the 5.0 layer kinds are on, in memory and on disk
    assert _enabled(data, "RASTER") is True and _enabled(data, "POINT_CLOUD") is True
    on_disk = json.loads(redirected.read_text(encoding="utf-8"))
    assert _enabled(on_disk, "RASTER") is True and _enabled(on_disk, "POINT_CLOUD") is True


def test_a_missing_redirected_config_is_created_from_the_one_read(config_module, tmp_path):
    redirected = _setup(config_module, tmp_path, None)
    assert config_module.ENV_VARS["CONFIG_JSON_PATH"] == str(redirected)
    on_disk = json.loads(redirected.read_text(encoding="utf-8"))
    assert on_disk["APP"]["DOCKWIDGET"]["LANGUAGE"]["value"] == "en"
    assert _enabled(on_disk, "RASTER") is True


def test_an_unreadable_redirected_config_is_kept_then_replaced(config_module, tmp_path):
    redirected = _setup(config_module, tmp_path, '{"APP": {')
    assert any(p.name.startswith("config.json.corrupt-") for p in redirected.parent.iterdir())
    on_disk = json.loads(redirected.read_text(encoding="utf-8"))
    assert _enabled(on_disk, "RASTER") is True


def test_load_migrated_config(config_module, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(_old_config()), encoding="utf-8")
    data = config_module.load_migrated_config(str(path))
    assert _enabled(data, "RASTER") is True and _enabled(data, "POINT_CLOUD") is True
    path.write_text("not json", encoding="utf-8")
    assert config_module.load_migrated_config(str(path)) is None
    path.write_text("{}", encoding="utf-8")
    assert config_module.load_migrated_config(str(path)) is None
