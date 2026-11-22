# -*- coding: utf-8 -*-
"""``filtermate setup``: a QGIS runtime of FilterMate's own, installed through micromamba.

Nothing is downloaded here: the network functions are replaced. The real install is checked in
a container (see docs/STANDALONE.md).
"""
from __future__ import annotations

import hashlib
import os
import platform
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT)) if str(_ROOT) not in sys.path else None
from standalone import paths, provision, runtime  # noqa: E402


@pytest.fixture(autouse=True)
def _own_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FILTERMATE_HOME", str(tmp_path / "home"))


@pytest.mark.parametrize("os_name, system, machine, expected", [
    ("posix", "linux", "x86_64", "linux-64"),
    ("posix", "linux", "aarch64", "linux-aarch64"),
    ("posix", "darwin", "arm64", "osx-arm64"),
    ("posix", "darwin", "x86_64", "osx-64"),
    ("nt", "win32", "AMD64", "win-64"),
    ("nt", "win32", "ARM64", "win-arm64"),
    ("posix", "linux", "mips", None),
    ("posix", "freebsd14", "amd64", None),
])
def test_the_micromamba_build_follows_the_machine(monkeypatch, os_name, system, machine, expected):
    monkeypatch.setattr(os, "name", os_name)
    monkeypatch.setattr(sys, "platform", system)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    assert provision.platform_tag() == expected


def _fake_network(monkeypatch, payload: bytes, published_digest: str):
    def download(url, target, log):
        assert url.startswith(provision.RELEASES + "micromamba-")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        Path(target).write_bytes(payload)

    monkeypatch.setattr(provision, "_download", download)
    monkeypatch.setattr(provision, "_read_url", lambda url: published_digest + "\n")
    monkeypatch.setattr(provision, "platform_tag", lambda: "linux-64")


def test_micromamba_is_kept_when_its_digest_matches(monkeypatch):
    payload = b"#!/bin/sh\necho micromamba\n"
    _fake_network(monkeypatch, payload, hashlib.sha256(payload).hexdigest())
    path = provision.fetch_micromamba(log=lambda _: None)
    assert path == provision.micromamba_path() and Path(path).read_bytes() == payload
    if os.name != "nt":
        assert os.access(path, os.X_OK)
    assert not os.path.exists(path + ".new")


def test_micromamba_is_thrown_away_when_its_digest_differs(monkeypatch):
    _fake_network(monkeypatch, b"tampered", hashlib.sha256(b"original").hexdigest())
    with pytest.raises(provision.ProvisionError, match="SHA-256"):
        provision.fetch_micromamba(log=lambda _: None)
    assert not os.path.exists(provision.micromamba_path())
    assert not os.path.exists(provision.micromamba_path() + ".new")


def test_a_published_digest_that_is_not_a_digest_is_refused(monkeypatch):
    _fake_network(monkeypatch, b"x", "<html>not found</html>")
    with pytest.raises(provision.ProvisionError):
        provision.fetch_micromamba(log=lambda _: None)
    assert not os.path.exists(provision.micromamba_path())


def test_a_machine_without_a_micromamba_build_is_told_to_install_qgis(monkeypatch):
    monkeypatch.setattr(provision, "platform_tag", lambda: None)
    with pytest.raises(provision.ProvisionError, match="Install QGIS"):
        provision.fetch_micromamba(log=lambda _: None)


def test_only_https_is_downloaded(tmp_path):
    with pytest.raises(provision.ProvisionError, match="Refusing"):
        provision._download("http://example.org/micromamba", str(tmp_path / "x"), lambda _: None)
    with pytest.raises(provision.ProvisionError, match="Refusing"):
        provision._read_url("file:///etc/passwd")


def test_the_environment_is_created_in_the_application_folder_from_conda_forge_only():
    command = provision.create_command("/bin/micromamba")
    assert command[:3] == ["/bin/micromamba", "create", "--yes"]
    assert command[command.index("-p") + 1] == provision.environment_dir()
    assert command[command.index("-r") + 1] == provision.root_prefix()
    assert "--override-channels" in command and command[command.index("-c") + 1] == "conda-forge"
    assert any(package.startswith("qgis") for package in command[command.index("conda-forge") + 1:])
    assert provision.environment_dir().startswith(paths.user_data_dir())


def test_install_stops_before_downloading_when_the_disk_is_full(monkeypatch):
    monkeypatch.setattr(provision, "free_bytes", lambda: 1024 ** 3)
    monkeypatch.setattr(provision, "fetch_micromamba", lambda log=print: pytest.fail("no download on a full disk"))
    with pytest.raises(provision.ProvisionError, match="FILTERMATE_HOME"):
        provision.install(log=lambda _: None)


def test_install_tries_again_then_reports_a_micromamba_that_keeps_failing(monkeypatch):
    calls = []
    monkeypatch.setattr(provision, "free_bytes", lambda: provision.NEEDED_BYTES * 2)
    monkeypatch.setattr(provision, "fetch_micromamba", lambda log=print: "/bin/false-micromamba")

    def failing(command, *args, **kwargs):
        calls.append(command)
        os.makedirs(provision.environment_dir(), exist_ok=True)  # what a stalled download leaves behind
        return 1

    monkeypatch.setattr(provision.subprocess, "call", failing)
    with pytest.raises(provision.ProvisionError, match="code 1 after 3 attempts"):
        provision.install(log=lambda _: None)
    assert len(calls) == provision.ATTEMPTS
    assert not os.path.exists(provision.environment_dir()), "no half environment is left for the runtime search"


def test_install_goes_on_when_a_second_attempt_succeeds(monkeypatch):
    calls = []
    monkeypatch.setattr(provision, "free_bytes", lambda: provision.NEEDED_BYTES * 2)
    monkeypatch.setattr(provision, "fetch_micromamba", lambda log=print: provision.micromamba_path())

    def second_time_lucky(command, *args, **kwargs):
        calls.append(command)
        if command[1] != "create":
            return 0  # the cleaning of the cache
        if len(calls) == 1:
            return 1
        os.makedirs(os.path.dirname(provision.environment_python()), exist_ok=True)
        Path(provision.environment_python()).write_text("", encoding="utf-8")
        os.makedirs(os.path.dirname(provision.micromamba_path()), exist_ok=True)
        Path(provision.micromamba_path()).write_text("", encoding="utf-8")
        return 0

    monkeypatch.setattr(provision.subprocess, "call", second_time_lucky)
    monkeypatch.setattr(runtime, "probe", lambda found, timeout=180.0: setattr(found, "info", {
        "ok": True, "qgis": "3.44.1", "qgis_int": 34401}) or found)
    installed = provision.install(log=lambda _: None)
    assert installed.kind == "private" and installed.usable
    assert [command[1] for command in calls] == ["create", "create", "clean"]


def test_no_runtime_is_reported_until_setup_ran_to_the_end():
    assert provision.installed_runtime() is None
    os.makedirs(os.path.dirname(provision.micromamba_path()))
    Path(provision.micromamba_path()).write_text("", encoding="utf-8")
    assert provision.installed_runtime() is None, "micromamba alone is an install that stopped halfway"
    os.makedirs(os.path.dirname(provision.environment_python()))
    Path(provision.environment_python()).write_text("", encoding="utf-8")
    installed = provision.installed_runtime()
    assert installed.kind == "private"
    assert installed.command[:2] == [provision.micromamba_path(), "run"] and installed.command[-1] == "python"
    assert provision.environment_dir() in installed.command
    assert installed.env["PYTHONPATH"].split(os.pathsep)[0].startswith(provision.environment_dir())
    assert installed.env["QGIS_PREFIX_PATH"].startswith(provision.environment_dir())
    assert any(candidate.kind == "private" for candidate in runtime.candidates())


def test_remove_deletes_the_runtime_folder_and_nothing_else():
    os.makedirs(provision.environment_dir())
    profile = Path(paths.profile_dir())
    profile.mkdir(parents=True)
    (profile / "settings.ini").write_text("kept", encoding="utf-8")
    assert provision.remove() is True
    assert not os.path.exists(paths.runtime_dir())
    assert (profile / "settings.ini").read_text(encoding="utf-8") == "kept"
    assert provision.remove() is False
