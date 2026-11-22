# -*- coding: utf-8 -*-
"""The ``filtermate`` launcher: it must run in a Python that has neither QGIS nor Qt, find a
Python that has them, and start the host there.

No QGIS here: runtimes are stand-ins (this Python running a small script that answers as
``_probe.py`` does).
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_STANDALONE = _ROOT / "standalone"
LAUNCHER_FILES = ("__init__.py", "__main__.py", "cli.py", "runtime.py", "provision.py", "paths.py", "_bootstrap.py")
HOST_PACKAGES = ("qgis", "PyQt5", "PyQt6", "PySide6", "osgeo", "processing", "sip")

sys.path.insert(0, str(_ROOT)) if str(_ROOT) not in sys.path else None
from standalone import cli, paths, runtime  # noqa: E402


@pytest.fixture(autouse=True)
def _own_home(tmp_path, monkeypatch):
    """Every test gets an application folder of its own, and no override left from the shell."""
    monkeypatch.setenv("FILTERMATE_HOME", str(tmp_path / "home"))
    monkeypatch.delenv(runtime.ENV_OVERRIDE, raising=False)


def _answering(tmp_path, answer: dict, name="fake_python.py") -> list:
    """A command that answers the probe with ``answer``, whatever script it is given."""
    script = tmp_path / name
    script.write_text(f"print('noise before')\nprint('FM_RUNTIME ' + {json.dumps(json.dumps(answer))})\n", encoding="utf-8")
    return [sys.executable, str(script)]


def _usable(kind="install", number=34400, label="x") -> runtime.Runtime:
    return runtime.Runtime(kind, ["python-" + label], label, info={"ok": True, "qgis": str(number), "qgis_int": number})


# --- the launcher needs nothing but the standard library ----------------------------------------------------------


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0], node.lineno


@pytest.mark.parametrize("name", LAUNCHER_FILES)
def test_launcher_module_imports_only_the_standard_library(name):
    allowed_own = {"filter_mate"} if name == "_bootstrap.py" else set()  # it starts the host, lazily, by design
    foreign = [(module, line) for module, line in _imports(_STANDALONE / name)
               if module not in sys.stdlib_module_names and module not in allowed_own]
    assert not foreign, f"standalone/{name} imports {foreign}: the launcher must run in any Python"


def test_launcher_runs_where_qgis_and_qt_cannot_be_imported(tmp_path):
    code = (
        "import sys\n"
        f"blocked = {HOST_PACKAGES!r}\n"
        "class Block:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in blocked:\n"
        "            raise ImportError('blocked: ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        f"sys.path.insert(0, {str(_ROOT)!r})\n"
        "from standalone import cli, runtime, provision, paths\n"
        "sys.exit(cli.main(['version']))\n")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
                          env={**os.environ, "FILTERMATE_HOME": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("FilterMate ")


# --- trying a runtime ---------------------------------------------------------------------------------------------


def test_probe_reads_the_answer_of_a_python_that_has_qgis(tmp_path):
    command = _answering(tmp_path, {"ok": True, "qgis": "3.44.1", "qgis_int": 34401, "qt": "5.15.13", "python": "3.12.3"})
    tried = runtime.probe(runtime.Runtime("install", command, "fake"))
    assert tried.usable and not tried.too_old
    assert "3.44.1" in tried.describe() and "5.15.13" in tried.describe()


def test_probe_refuses_a_qgis_older_than_the_minimum(tmp_path):
    tried = runtime.probe(runtime.Runtime("install", _answering(tmp_path, {"ok": True, "qgis": "3.16.0", "qgis_int": 31600}), "old"))
    assert not tried.usable and tried.too_old
    assert runtime.MIN_QGIS in tried.describe()


def test_probe_reports_a_python_without_qgis(tmp_path):
    answer = {"ok": False, "error": "ModuleNotFoundError: No module named 'qgis'"}
    tried = runtime.probe(runtime.Runtime("install", _answering(tmp_path, answer), "bare"))
    assert not tried.usable
    assert "No module named" in tried.describe()


def test_probe_survives_a_command_that_does_not_exist(tmp_path):
    tried = runtime.probe(runtime.Runtime("install", [str(tmp_path / "no-such-python")], "missing"))
    assert not tried.usable and tried.describe() == "not found"


def test_probe_survives_a_command_that_answers_nothing(tmp_path):
    script = tmp_path / "silent.py"
    script.write_text("import sys\nsys.stderr.write('boom\\n')\nsys.exit(4)\n", encoding="utf-8")
    tried = runtime.probe(runtime.Runtime("install", [sys.executable, str(script)], "silent"))
    assert not tried.usable and tried.describe() == "boom"


def test_the_real_probe_script_says_this_python_has_no_qgis():
    """``_probe.py`` itself, in a fresh Python without QGIS: one line, exit code 3, no traceback."""
    done = subprocess.run([sys.executable, "-S", str(_STANDALONE / "_probe.py")], capture_output=True, text=True, timeout=60)
    lines = [line for line in done.stdout.splitlines() if line.startswith("FM_RUNTIME ")]
    if done.returncode == 0:  # this machine's Python has PyQGIS: the other branch of the probe
        assert json.loads(lines[0][11:])["ok"] is True
        return
    assert done.returncode == 3 and len(lines) == 1
    assert json.loads(lines[0][11:])["ok"] is False


# --- choosing one -------------------------------------------------------------------------------------------------


def test_choose_prefers_what_the_user_named_then_this_python_then_the_private_runtime():
    installs = [_usable("install", 34400, "a"), _usable("install", 40200, "b")]
    private, current, override = _usable("private", 34000, "p"), _usable("current", 33400, "c"), _usable("override", 32200, "o")
    assert runtime.choose(installs + [private, current, override]) is override
    assert runtime.choose(installs + [private, current]) is current
    assert runtime.choose(installs + [private]) is private


def test_choose_takes_the_newest_install_and_skips_what_does_not_work():
    old, new = _usable("install", 34400, "old"), _usable("conda", 40300, "new")
    broken = runtime.Runtime("install", ["x"], "broken", info={"ok": False, "error": "no"})
    too_old = _usable("install", 31600, "ancient")
    assert runtime.choose([old, broken, too_old, new]) is new
    assert runtime.choose([broken, too_old]) is None


def test_resolve_stops_at_the_first_preferred_runtime_and_remembers_it(tmp_path, monkeypatch):
    good = _answering(tmp_path, {"ok": True, "qgis": "3.44.0", "qgis_int": 34400, "qt": "5", "python": "3"})
    tried = []
    real_probe = runtime.probe

    def counting(candidate, timeout=180.0):
        tried.append(candidate.label)
        return real_probe(candidate, timeout)

    monkeypatch.setattr(runtime, "probe", counting)
    monkeypatch.setattr(runtime, "candidates", lambda: [
        runtime.Runtime("current", [str(tmp_path / "nope")], "current"),
        runtime.Runtime("private", good, "private"),
        runtime.Runtime("install", good, "install")])
    chosen = runtime.resolve()
    assert chosen.kind == "private" and tried == ["current", "private"]
    tried.clear()
    assert runtime.resolve().kind == "private" and tried == [], "the second launch reuses the answer"
    assert runtime.resolve(refresh=True).kind == "private" and tried == ["current", "private"]


def test_the_remembered_runtime_is_dropped_when_its_python_changes(tmp_path, monkeypatch):
    command = _answering(tmp_path, {"ok": True, "qgis": "3.44.0", "qgis_int": 34400})
    monkeypatch.setattr(runtime, "candidates", lambda: [runtime.Runtime("install", command, "install")])
    assert runtime.resolve() is not None and runtime._read_cache() is not None
    # The cache follows the first word of the command: here this Python, whose date does not change. A cache
    # written for another executable must not be reused.
    data = json.loads(Path(paths.runtime_cache_file()).read_text(encoding="utf-8"))
    data["stamp"] = data["stamp"] - 10
    Path(paths.runtime_cache_file()).write_text(json.dumps(data), encoding="utf-8")
    assert runtime._read_cache() is None


def test_the_remembered_runtime_is_dropped_when_the_user_names_another(tmp_path, monkeypatch):
    command = _answering(tmp_path, {"ok": True, "qgis": "3.44.0", "qgis_int": 34400})
    monkeypatch.setattr(runtime, "candidates", lambda: [runtime.Runtime("install", command, "install")])
    assert runtime.resolve() is not None
    monkeypatch.setenv(runtime.ENV_OVERRIDE, "/somewhere/python")
    assert runtime._read_cache() is None


def test_resolve_returns_none_on_a_machine_without_qgis(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "candidates", lambda: [runtime.Runtime("current", [str(tmp_path / "nope")], "current")])
    assert runtime.resolve() is None
    assert not os.path.exists(paths.runtime_cache_file())


# --- where it looks -----------------------------------------------------------------------------------------------


def test_a_virtual_environment_python_is_not_taken_for_the_python_it_links_to(tmp_path):
    target = tmp_path / "python3"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "venv-python"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("no symbolic links here")
    assert not runtime._same_python(str(link), str(target))
    assert runtime._same_python(str(target), str(tmp_path / "." / "python3"))


def test_windows_installs_are_found_by_their_python_qgis_script(tmp_path, monkeypatch):
    for folder, script in (("QGIS 3.44.8", "python-qgis-ltr.bat"), ("QGIS 4.2.3", "python-qgis.bat")):
        (tmp_path / folder / "bin").mkdir(parents=True)
        (tmp_path / folder / "bin" / script).write_text("", encoding="utf-8")
    (tmp_path / "QGIS 3.10" / "bin").mkdir(parents=True)  # an install without the script: not a candidate
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    for name in ("ProgramW6432", "ProgramFiles(x86)", "OSGEO4W_ROOT"):
        monkeypatch.delenv(name, raising=False)
    found = runtime._windows_installs()
    assert [os.path.basename(item.command[0]) for item in found] == ["python-qgis.bat", "python-qgis-ltr.bat"]
    assert all(item.kind == "install" for item in found)


def test_macos_bundles_get_the_environment_their_python_needs(tmp_path):
    contents = tmp_path / "QGIS.app" / "Contents"
    (contents / "MacOS" / "bin").mkdir(parents=True)
    (contents / "MacOS" / "bin" / "python3").write_text("", encoding="utf-8")
    (contents / "Resources" / "python").mkdir(parents=True)
    (contents / "Resources" / "proj").mkdir()
    (tmp_path / "QGIS-broken.app" / "Contents").mkdir(parents=True)  # no Python inside: skipped
    found = runtime._macos_installs(str(tmp_path))
    assert len(found) == 1
    assert found[0].env["PYTHONPATH"] == str(contents / "Resources" / "python")
    assert found[0].env["QGIS_PREFIX_PATH"] == str(contents / "MacOS")
    assert found[0].env["PROJ_DATA"] == str(contents / "Resources" / "proj") and "GDAL_DATA" not in found[0].env


def test_candidates_start_with_what_the_user_named(monkeypatch):
    monkeypatch.setenv(runtime.ENV_OVERRIDE, "/opt/qgis/python")
    found = runtime.candidates()
    assert found[0].kind == "override" and found[0].command == ["/opt/qgis/python"]
    assert found[1].kind == "current" and found[1].command == [sys.executable]


# --- starting the host --------------------------------------------------------------------------------------------


def test_the_host_is_started_by_the_bootstrap_file_with_the_arguments_of_the_user():
    command = runtime.host_command(runtime.Runtime("install", ["C:\\QGIS\\bin\\python-qgis.bat"], "w"), ["--lang", "fr", "a b.gpkg"])
    assert command == ["C:\\QGIS\\bin\\python-qgis.bat", runtime.BOOTSTRAP_SCRIPT, "--lang", "fr", "a b.gpkg"]
    assert os.path.isfile(runtime.BOOTSTRAP_SCRIPT) and os.path.isfile(runtime.PROBE_SCRIPT)


def test_another_python_does_not_inherit_the_virtual_environment_of_the_launcher(monkeypatch):
    monkeypatch.setenv("VIRTUAL_ENV", "/venv")
    monkeypatch.setenv("PYTHONHOME", "/venv")
    monkeypatch.setenv("PYTHONPATH", "/mine")
    other = runtime.Runtime("install", ["python"], "other", env={"PYTHONPATH": "/qgis/python", "QGIS_PREFIX_PATH": "/qgis"})
    env = runtime.child_environment(other)
    assert "VIRTUAL_ENV" not in env and "PYTHONHOME" not in env
    assert env["PYTHONPATH"] == "/qgis/python" + os.pathsep + "/mine" and env["QGIS_PREFIX_PATH"] == "/qgis"
    assert runtime.child_environment(runtime.Runtime("current", [sys.executable], "me"))["VIRTUAL_ENV"] == "/venv"


def test_launch_runs_the_host_in_the_runtime_and_returns_its_exit_code(tmp_path, monkeypatch):
    fake_bootstrap = tmp_path / "bootstrap.py"
    fake_bootstrap.write_text(
        "import json, sys\n"
        f"open({str(tmp_path / 'seen.json')!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        "sys.exit(7)\n", encoding="utf-8")
    monkeypatch.setattr(runtime, "BOOTSTRAP_SCRIPT", str(fake_bootstrap))
    code = runtime.launch(runtime.Runtime("install", [sys.executable], "fake"), ["--offscreen", "data.gpkg"])
    assert code == 7
    assert json.loads((tmp_path / "seen.json").read_text(encoding="utf-8")) == ["--offscreen", "data.gpkg"]


def test_launch_reports_a_runtime_that_vanished(tmp_path, capsys):
    code = runtime.launch(runtime.Runtime("install", [str(tmp_path / "gone")], "gone"), [])
    assert code == 1 and "cannot start" in capsys.readouterr().err


# --- the command --------------------------------------------------------------------------------------------------


def test_run_passes_everything_but_its_own_options_to_the_host(monkeypatch):
    seen = {}
    monkeypatch.setattr(runtime, "resolve", lambda refresh=False: seen.setdefault("refresh", refresh) and None or _usable())
    monkeypatch.setattr(runtime, "launch", lambda chosen, args: seen.setdefault("args", args) and 0 or 0)
    assert cli.main(["--refresh", "--runtime", "/q/python", "--lang", "fr", "parcels.gpkg"]) == 0
    assert seen["args"] == ["--lang", "fr", "parcels.gpkg"] and seen["refresh"] is True
    assert os.environ[runtime.ENV_OVERRIDE] == "/q/python"


def test_run_names_the_command_as_a_subcommand_too(monkeypatch):
    seen = {}
    monkeypatch.setattr(runtime, "resolve", lambda refresh=False: _usable())
    monkeypatch.setattr(runtime, "launch", lambda chosen, args: seen.setdefault("args", args) and 0 or 0)
    assert cli.main(["run", "--project", "town.qgz"]) == 0
    assert seen["args"] == ["--project", "town.qgz"]


def test_without_a_runtime_and_without_a_terminal_it_explains_and_installs_nothing(monkeypatch, capsys):
    from standalone import provision
    monkeypatch.setattr(runtime, "resolve", lambda refresh=False: None)
    monkeypatch.setattr(provision, "install", lambda **_: pytest.fail("nothing must be installed without a yes"))
    monkeypatch.setattr(sys, "stdin", None)
    assert cli.main([]) == 1
    message = capsys.readouterr().err
    assert "filtermate setup" in message and runtime.ENV_OVERRIDE in message and "qgis.org" in message


def test_doctor_lists_what_was_tried_and_what_is_used(monkeypatch, capsys):
    broken = runtime.Runtime("current", ["python"], "this Python", info={"ok": False, "error": "No module named 'qgis'"})
    good = runtime.Runtime("install", ["/usr/bin/python3"], "system Python",
                           info={"ok": True, "qgis": "3.44.1", "qgis_int": 34401, "qt": "5.15", "python": "3.12"})
    monkeypatch.setattr(runtime, "survey", lambda: [broken, good])
    assert cli.main(["doctor"]) == 0
    text = capsys.readouterr().out
    assert "-> ok  system Python" in text and "no  this Python" in text and "FilterMate starts with: system Python" in text
    monkeypatch.setattr(runtime, "survey", lambda: [broken])
    assert cli.main(["doctor"]) == 1
    assert "filtermate setup" in capsys.readouterr().out


def test_doctor_json_is_machine_readable(monkeypatch, capsys):
    good = runtime.Runtime("install", ["/usr/bin/python3"], "system Python", info={"ok": True, "qgis": "3.44.1", "qgis_int": 34401})
    monkeypatch.setattr(runtime, "survey", lambda: [good])
    assert cli.main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["chosen"] == ["/usr/bin/python3"] and data["runtimes"][0]["usable"] is True


def test_setup_asks_before_downloading_and_takes_no_for_an_answer(monkeypatch, capsys):
    from standalone import provision
    monkeypatch.setattr(provision, "installed_runtime", lambda: None)
    monkeypatch.setattr(provision, "install", lambda **_: pytest.fail("nothing must be installed without a yes"))
    monkeypatch.setattr(sys, "stdin", None)
    assert cli.main(["setup"]) == 1
    assert "Nothing installed" in capsys.readouterr().out


def test_version_reads_the_metadata_of_the_plugin(capsys):
    assert cli.main(["--version"]) == 0
    printed = capsys.readouterr().out.strip()
    expected = next(line.split("=", 1)[1].strip() for line in (_ROOT / "metadata.txt").read_text(encoding="utf-8").splitlines()
                    if line.startswith("version="))
    assert printed == f"FilterMate {expected}"


def test_the_application_folder_follows_the_platform_and_the_override(monkeypatch):
    monkeypatch.setenv("FILTERMATE_HOME", "/data/fm")
    assert paths.user_data_dir() == os.path.abspath("/data/fm")
    assert paths.profile_dir() == os.path.join(os.path.abspath("/data/fm"), "profile")
    monkeypatch.delenv("FILTERMATE_HOME")
    monkeypatch.setenv("XDG_DATA_HOME", "/xdg")
    if os.name != "nt" and sys.platform != "darwin":
        assert paths.user_data_dir() == os.path.join("/xdg", "filtermate")
