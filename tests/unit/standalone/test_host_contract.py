# -*- coding: utf-8 -*-
"""The standalone host gives the plugin every part of ``iface`` it calls, and the pip package
ships every folder of the plugin.

Static checks: they read the sources, so they run without QGIS and fail the day the plugin calls
a method of ``iface`` the standalone interface does not have, or gains a folder the wheel forgets.
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]

# Folders that are not the plugin (or are the host itself).
NOT_PLUGIN = {"tests", "scripts", "website", "docs", "knowledge", "dist", "build", "logs", "standalone", "_bmad",
              "_bmad-output", "reports", "research_notes"}
# Scripts written for the QGIS application that also run in the standalone host.
BENCHES = ("tests/qgis_headless/run_gui_smoke.py", "tests/qgis_headless/check_standalone.py")

_CALL = re.compile(r"\biface\.([A-Za-z_]\w*)\(")
_SIGNAL = re.compile(r"\biface\.([A-Za-z_]\w*)\.(?:connect|disconnect|emit)\(")


def _interface_members():
    tree = ast.parse((_ROOT / "standalone" / "host" / "interface.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "StandaloneInterface")
    members = set()
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members.add(node.name)
        elif isinstance(node, ast.Assign):
            members.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return members


def _plugin_sources():
    for path in _ROOT.rglob("*.py"):
        relative = path.relative_to(_ROOT)
        if relative.parts[0] in NOT_PLUGIN or relative.parts[0].startswith(".") or "__pycache__" in relative.parts:
            continue
        yield relative, path.read_text(encoding="utf-8", errors="replace")
    for name in BENCHES:
        yield Path(name), (_ROOT / name).read_text(encoding="utf-8")


def test_every_iface_method_the_plugin_calls_exists_in_the_standalone_interface():
    members = _interface_members()
    missing = {}
    for relative, source in _plugin_sources():
        for name in set(_CALL.findall(source)) | set(_SIGNAL.findall(source)):
            if name not in members:
                missing.setdefault(name, []).append(str(relative))
    assert not missing, (
        "the plugin calls iface methods the standalone host does not have "
        f"(add them to standalone/host/interface.py): {missing}")


def test_the_interface_has_the_methods_the_plugin_is_known_to_need():
    """A floor under the scan above: were its pattern to stop matching, these would still be asked for."""
    members = _interface_members()
    for name in ("mainWindow", "mapCanvas", "messageBar", "activeLayer", "setActiveLayer", "layerTreeView",
                 "addDockWidget", "removeDockWidget", "addToolBar", "addPluginToVectorMenu", "removePluginVectorMenu",
                 "removeToolBarIcon", "actionPan", "actionSelectRectangle", "actionSelectPolygon", "actionIdentify",
                 "openFeatureForm", "projectRead", "newProjectCreated", "newProject", "addProject"):
        assert name in members, name


# --- the pip package ----------------------------------------------------------------------------------------------


def _pyproject():
    tomllib = pytest.importorskip("tomllib")
    return tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _tracked_top_level():
    try:
        done = subprocess.run(["git", "ls-files"], cwd=_ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git is not available")
    if done.returncode != 0 or not done.stdout.strip():
        pytest.skip("not a git checkout")
    return {line.split("/")[0] for line in done.stdout.splitlines() if line}


# Tracked at the root and deliberately left out of the wheel.
NOT_IN_WHEEL = {
    ".claude", ".dockerignore", ".flake8", ".gitattributes", ".github", ".gitignore", ".mcp.json", ".serena", ".vscode", "CLAUDE.md",
    "CONTRIBUTING.md", "_bmad", "_bmad-output", "docs", "knowledge", "logs", "pyproject.toml", "pytest.ini",
    "requirements-api.txt", "requirements-mcp.txt", "requirements-test-api.txt", "requirements-test.txt", "scripts",
    "setup.cfg", "tests", "website", "reports", "research_notes",
}


def test_every_folder_of_the_plugin_is_in_the_wheel():
    wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
    included = {entry.strip("/").split("/")[0] for entry in wheel["include"]}
    forgotten = sorted(_tracked_top_level() - included - NOT_IN_WHEEL)
    assert not forgotten, (
        f"{forgotten}: tracked at the root, neither in the wheel (pyproject.toml, include) nor listed as left out "
        "(NOT_IN_WHEEL in this test). A new package of the plugin missing from the wheel breaks `pip install filtermate`.")
    assert wheel["sources"] == {"": "filter_mate"}, "the plugin must be importable as filter_mate"


def test_the_wheel_does_not_follow_gitignore():
    """`.gitignore` has `memory/` (agent notes): it matched adapters/backends/memory/ and the wheel lost the module."""
    assert _pyproject()["tool"]["hatch"]["build"]["ignore-vcs"] is True
    assert (_ROOT / "adapters" / "backends" / "memory" / "backend.py").is_file()


def test_the_command_of_the_package_exists():
    target = _pyproject()["project"]["scripts"]["filtermate"]
    assert target == "filter_mate.standalone.cli:main"
    tree = ast.parse((_ROOT / "standalone" / "cli.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)


def test_the_version_of_the_package_is_the_version_of_the_plugin():
    version = _pyproject()["tool"]["hatch"]["version"]
    assert version["path"] == "metadata.txt"
    found = re.search(version["pattern"], (_ROOT / "metadata.txt").read_text(encoding="utf-8"), re.MULTILINE)
    assert found and re.fullmatch(r"\d+\.\d+\.\d+.*", found.group("version"))


def test_the_package_needs_nothing_from_pypi_to_start():
    assert _pyproject()["project"]["dependencies"] == []


def test_the_plugin_zip_ships_neither_the_host_nor_the_package_file():
    """plugins.qgis.org scans every file of the zip; the launcher downloads and starts programs, by design."""
    script = (_ROOT / "scripts" / "prepare_plugin_zip.sh").read_text(encoding="utf-8")
    assert "--exclude='/standalone'" in script and "--exclude='/standalone/**'" in script
    assert "--exclude='/pyproject.toml'" in script


def test_nothing_of_the_plugin_imports_the_host():
    """The dependency goes one way: inside QGIS, the plugin must load without standalone/."""
    offenders = []
    for relative, source in _plugin_sources():
        if str(relative) in BENCHES:
            continue
        if re.search(r"^\s*(from|import)\s+(\.+)?standalone\b|from\s+\.+\s+import\s+standalone\b", source, re.MULTILINE):
            offenders.append(str(relative))
    assert not offenders, offenders
