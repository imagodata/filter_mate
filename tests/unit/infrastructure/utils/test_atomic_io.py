# -*- coding: utf-8 -*-
"""
config.json was written with ``open(path, 'w')``: truncated first, so a crash
or a serialization error left half a file, and the next start replaced it with
the default settings. ``atomic_json_write`` swaps a finished temp file in, and
``backup_corrupt_file`` keeps the user's file before any fallback to defaults.
"""
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "infrastructure" / "utils" / "atomic_io.py"


def _load():
    # by path: the infrastructure.utils package imports half of the plugin
    name = "fmtest_atomic_io"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, _PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


atomic_io = _load()
atomic_json_write = atomic_io.atomic_json_write
backup_corrupt_file = atomic_io.backup_corrupt_file


class TestAtomicJsonWrite:
    def test_writes_utf8_json(self, tmp_path):
        target = tmp_path / "config.json"
        atomic_json_write(str(target), {"langue": "Français", "n": [1, 2]})
        raw = target.read_bytes().decode("utf-8")
        assert "Français" in raw  # not escaped
        assert json.loads(raw) == {"langue": "Français", "n": [1, 2]}
        assert raw.startswith('{\n    "langue"')  # 4-space indent, like the old writers

    def test_creates_missing_directory(self, tmp_path):
        target = tmp_path / "FilterMate" / "config.json"
        atomic_json_write(str(target), {"a": 1})
        assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}

    def test_replaces_existing_file(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text('{"old": true}', encoding="utf-8")
        atomic_json_write(str(target), {"new": True})
        assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}

    def test_no_temp_file_left(self, tmp_path):
        atomic_json_write(str(tmp_path / "config.json"), {"a": 1})
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]

    def test_unserializable_data_leaves_the_file_untouched(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text('{"keep": 1}', encoding="utf-8")
        with pytest.raises(TypeError):
            atomic_json_write(str(target), {"connection": object()})
        assert json.loads(target.read_text(encoding="utf-8")) == {"keep": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]

    def test_failed_swap_leaves_the_file_untouched_and_no_temp(self, tmp_path, monkeypatch):
        target = tmp_path / "config.json"
        target.write_text('{"keep": 1}', encoding="utf-8")

        def boom(src, dst):
            raise OSError("disk full")

        monkeypatch.setattr(atomic_io.os, "replace", boom)
        with pytest.raises(OSError):
            atomic_json_write(str(target), {"new": 1})
        monkeypatch.undo()
        assert json.loads(target.read_text(encoding="utf-8")) == {"keep": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


class TestWindowsAndFilesystemDetails:
    def test_a_swap_refused_for_a_moment_is_retried(self, tmp_path, monkeypatch):
        target = tmp_path / "config.json"
        target.write_text('{"old": 1}', encoding="utf-8")
        real_replace = os.replace
        calls = []

        def flaky(src, dst):
            calls.append(src)
            if len(calls) <= 3:
                raise PermissionError("file in use")
            real_replace(src, dst)

        sleeps = []
        monkeypatch.setattr(atomic_io.os, "replace", flaky)
        monkeypatch.setattr(atomic_io.time, "sleep", sleeps.append)

        atomic_json_write(str(target), {"new": 1})

        assert len(calls) == 4 and sleeps == [0.05, 0.05, 0.05]
        monkeypatch.undo()
        assert json.loads(target.read_text(encoding="utf-8")) == {"new": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]

    def test_a_swap_refused_for_good_raises_after_five_attempts_and_cleans_up(self, tmp_path, monkeypatch):
        target = tmp_path / "config.json"
        target.write_text('{"old": 1}', encoding="utf-8")
        calls = []

        def locked(src, dst):
            calls.append(src)
            raise PermissionError("file in use")

        monkeypatch.setattr(atomic_io.os, "replace", locked)
        monkeypatch.setattr(atomic_io.time, "sleep", lambda seconds: None)

        with pytest.raises(PermissionError):
            atomic_json_write(str(target), {"new": 1})

        monkeypatch.undo()
        assert len(calls) == 5
        assert json.loads(target.read_text(encoding="utf-8")) == {"old": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["config.json"]

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_the_mode_of_the_replaced_file_is_kept(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text("{}", encoding="utf-8")
        os.chmod(target, 0o640)

        atomic_json_write(str(target), {"a": 1})

        assert stat.S_IMODE(os.stat(target).st_mode) == 0o640

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_a_new_file_is_readable_not_owner_only(self, tmp_path):
        target = tmp_path / "fresh.json"

        atomic_json_write(str(target), {"a": 1})

        assert stat.S_IMODE(os.stat(target).st_mode) == 0o644

    @pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks")
    def test_a_symbolic_link_is_followed_and_kept(self, tmp_path):
        real_dir = tmp_path / "dotfiles"
        real_dir.mkdir()
        real = real_dir / "config.json"
        real.write_text('{"old": 1}', encoding="utf-8")
        link = tmp_path / "config.json"
        try:
            os.symlink(real, link)
        except OSError:
            pytest.skip("symlinks not permitted")

        atomic_json_write(str(link), {"new": 1})

        assert os.path.islink(link)
        assert json.loads(real.read_text(encoding="utf-8")) == {"new": 1}
        assert sorted(p.name for p in tmp_path.iterdir()) == ["config.json", "dotfiles"]
        assert [p.name for p in real_dir.iterdir()] == ["config.json"]


class TestBackupCorruptFile:
    def test_copies_the_file_with_a_timestamp(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text("{ not json", encoding="utf-8")
        backup = backup_corrupt_file(str(target))
        assert backup is not None
        name = os.path.basename(backup)
        assert name.startswith("config.json.corrupt-")
        assert len(name) == len("config.json.corrupt-") + len("20260101-120000")
        assert open(backup, encoding="utf-8").read() == "{ not json"
        assert target.read_text(encoding="utf-8") == "{ not json"  # original kept for now

    def test_two_backups_in_the_same_second_do_not_overwrite_each_other(self, tmp_path, monkeypatch):
        target = tmp_path / "config.json"
        target.write_text("one", encoding="utf-8")
        first = backup_corrupt_file(str(target))
        target.write_text("two", encoding="utf-8")
        second = backup_corrupt_file(str(target))
        assert first != second
        assert open(first, encoding="utf-8").read() == "one"
        assert open(second, encoding="utf-8").read() == "two"

    def test_missing_file(self, tmp_path):
        assert backup_corrupt_file(str(tmp_path / "nope.json")) is None

    def test_the_same_broken_content_is_kept_once(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text("{ not json", encoding="utf-8")

        first = backup_corrupt_file(str(target))
        second = backup_corrupt_file(str(target))
        third = backup_corrupt_file(str(target))

        assert first == second == third
        assert len([p for p in tmp_path.iterdir() if ".corrupt-" in p.name]) == 1
