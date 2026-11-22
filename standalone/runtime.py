# -*- coding: utf-8 -*-
"""Find a Python that has PyQGIS, and start the host in it (standard library only).

PyQGIS is not on PyPI: it comes with a QGIS install, a conda environment, or the runtime that
``filtermate setup`` installs. A *runtime* here is a command that starts such a Python. Every
candidate is tried for real (``_probe.py``) before it is used, so a wrong guess about where an
installer puts things costs a second, never a crash.

Order: the one named by ``FILTERMATE_QGIS_PYTHON``, the Python running the launcher, the
runtime of ``filtermate setup``, then the QGIS installs of the machine (newest first).
"""

import glob
import json
import os
import shutil
import subprocess  # nosec B404 - the launcher starts the Python of a QGIS install, its only purpose
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from . import paths

MIN_QGIS_INT = 32200
MIN_QGIS = "3.22"
ENV_OVERRIDE = "FILTERMATE_QGIS_PYTHON"

_HERE = os.path.dirname(os.path.abspath(__file__))
PROBE_SCRIPT = os.path.join(_HERE, "_probe.py")
BOOTSTRAP_SCRIPT = os.path.join(_HERE, "_bootstrap.py")


@dataclass
class Runtime:
    """A command that starts a Python expected to have PyQGIS.

    Attributes:
        kind: ``override``, ``current``, ``private``, ``install`` or ``conda``.
        command: The start of the command line (an executable, a ``.bat``, ``micromamba run ...``).
        label: What ``filtermate doctor`` shows.
        env: Variables that Python needs on top of the current environment.
        info: What the probe answered (``ok``, ``qgis``, ``qgis_int``, ``qt``, ``python``, or ``error``).
    """

    kind: str
    command: List[str]
    label: str
    env: Dict[str, str] = field(default_factory=dict)
    info: Dict[str, object] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return bool(self.info.get("ok")) and int(self.info.get("qgis_int") or 0) >= MIN_QGIS_INT

    @property
    def too_old(self) -> bool:
        return bool(self.info.get("ok")) and int(self.info.get("qgis_int") or 0) < MIN_QGIS_INT

    def describe(self) -> str:
        if self.usable:
            return f"QGIS {self.info.get('qgis')} (Qt {self.info.get('qt')}, Python {self.info.get('python')})"
        if self.too_old:
            return f"QGIS {self.info.get('qgis')}: older than {MIN_QGIS}"
        return str(self.info.get("error") or "not tried")


# --- candidates ---------------------------------------------------------------------------------------------------


def _override() -> List[Runtime]:
    value = os.environ.get(ENV_OVERRIDE, "").strip()
    return [Runtime("override", [value], f"{ENV_OVERRIDE}={value}")] if value else []


def _current() -> List[Runtime]:
    return [Runtime("current", [sys.executable], f"this Python ({sys.executable})")]


def private_runtime() -> Optional[Runtime]:
    """The runtime ``filtermate setup`` installed, None when there is none."""
    from . import provision
    return provision.installed_runtime()


def _windows_installs() -> List[Runtime]:
    roots = []
    for name in ("OSGEO4W_ROOT",):
        if os.environ.get(name):
            roots.append(os.environ[name])
    drive = os.environ.get("SystemDrive", "C:")
    roots += [drive + "\\OSGeo4W", drive + "\\OSGeo4W64"]
    for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            roots += sorted(glob.glob(os.path.join(base, "QGIS*")), reverse=True)
    found, seen = [], set()
    for root in roots:
        for script in sorted(glob.glob(os.path.join(root, "bin", "python-qgis*.bat"))):
            key = os.path.normcase(os.path.abspath(script))
            if key not in seen:
                seen.add(key)
                found.append(Runtime("install", [script], f"{root} ({os.path.basename(script)})"))
    return found


def _macos_installs(applications: str = "/Applications") -> List[Runtime]:
    """The Pythons of the QGIS bundles. Their layout changed across versions (``Contents/MacOS/bin/python3.x``,
    ``Contents/MacOS/python3``, a ``Python.framework``): every one found is a candidate, and the probe keeps those
    that import PyQGIS. A bundle whose Python does not (QGIS 4.2 was reported to fail so) leaves the conda
    runtime of ``filtermate setup``."""
    found = []
    folders = [applications, os.path.join(os.path.expanduser("~"), "Applications")]
    for bundle in sorted({b for folder in folders for b in glob.glob(os.path.join(folder, "QGIS*.app"))}, reverse=True):
        contents = os.path.join(bundle, "Contents")
        pythons = []
        for pattern in ("MacOS/bin/python3", "MacOS/bin/python3.[0-9]*", "MacOS/python3", "MacOS/python",
                        "Frameworks/Python.framework/Versions/*/bin/python3"):
            pythons += sorted(glob.glob(os.path.join(contents, pattern)), reverse=True)
        pythons = [python for python in pythons if os.path.isfile(python) and not python.endswith("-config")]
        if not pythons:
            continue
        resources = os.path.join(contents, "Resources")
        bindings = os.path.join(resources, "python")
        env = {"PYTHONPATH": os.pathsep.join([bindings, os.path.join(bindings, "plugins")]),
               "QGIS_PREFIX_PATH": os.path.join(contents, "MacOS")}
        plugins = os.path.join(contents, "PlugIns")
        if os.path.isdir(plugins):
            env["QT_PLUGIN_PATH"] = plugins
        for variable, folder in (("PROJ_DATA", "proj"), ("PROJ_LIB", "proj"), ("GDAL_DATA", "gdal")):
            if os.path.isdir(os.path.join(resources, folder)):
                env[variable] = os.path.join(resources, folder)
        found.append(Runtime("install", [pythons[0]], bundle, env))
    return found


def _same_python(first: str, second: str) -> bool:
    """True when two paths start the same interpreter *with the same packages*.

    Not ``realpath``: the Python of a virtual environment is a link to the system's, and is another
    Python all the same (it does not see the system's packages, PyQGIS among them).
    """
    return os.path.normcase(os.path.abspath(first)) == os.path.normcase(os.path.abspath(second))


def _base_python() -> List[Runtime]:
    """The Python a virtual environment was created from (pipx and venv hide its packages)."""
    base = getattr(sys, "_base_executable", "") or ""
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix) or not base or _same_python(base, sys.executable):
        return []
    return [Runtime("install", [base], f"the Python of this environment's base ({base})")]


def _posix_pythons() -> List[Runtime]:
    found, seen = [], [sys.executable] + [runtime.command[0] for runtime in _base_python()]
    for python in ("/usr/bin/python3", shutil.which("python3") or "", "/usr/local/bin/python3"):
        if python and os.path.exists(python) and not any(_same_python(python, known) for known in seen):
            seen.append(python)
            found.append(Runtime("install", [python], f"system Python ({python})"))
    return found


def _conda_environments() -> List[Runtime]:
    """The conda environments this user created: conda and mamba list them in one file."""
    prefixes = []
    if os.environ.get("CONDA_PREFIX"):
        prefixes.append(os.environ["CONDA_PREFIX"])
    try:
        with open(os.path.join(os.path.expanduser("~"), ".conda", "environments.txt"), encoding="utf-8") as handle:
            prefixes += [line.strip() for line in handle if line.strip()]
    except OSError:
        pass
    found, seen = [], [sys.executable]
    from . import provision
    own = os.path.normcase(os.path.abspath(provision.environment_dir()))
    # FilterMate's own runtime is registered with conda too: it is tried as such, with micromamba (``private``).
    prefixes = [prefix for prefix in prefixes if os.path.normcase(os.path.abspath(prefix)) != own]
    for prefix in prefixes:
        if os.name == "nt":
            python = os.path.join(prefix, "python.exe")
            library = os.path.join(prefix, "Library")
            bindings = os.path.join(library, "python")
            env = {"QGIS_PREFIX_PATH": library,
                   "QT_PLUGIN_PATH": os.pathsep.join([os.path.join(library, "plugins"), os.path.join(library, "qtplugins")]),
                   "PYTHONPATH": os.pathsep.join([bindings, os.path.join(bindings, "plugins")]),
                   "PATH": os.pathsep.join([prefix, os.path.join(library, "bin"), os.environ.get("PATH", "")])}
            has_qgis = os.path.isdir(os.path.join(library, "python", "qgis")) or bool(
                glob.glob(os.path.join(prefix, "Lib", "site-packages", "qgis")))
        else:
            python = os.path.join(prefix, "bin", "python")
            # What the activation script of the qgis package sets: the python is started without activation.
            bindings = os.path.join(prefix, "share", "qgis", "python")
            env = {"QGIS_PREFIX_PATH": prefix, "QT_PLUGIN_PATH": os.path.join(prefix, "plugins"),
                   "PYTHONPATH": os.pathsep.join([bindings, os.path.join(bindings, "plugins")]),
                   "PATH": os.pathsep.join([os.path.join(prefix, "bin"), os.environ.get("PATH", "")])}
            has_qgis = bool(glob.glob(os.path.join(prefix, "lib", "python3*", "site-packages", "qgis"))) or \
                os.path.isdir(os.path.join(prefix, "share", "qgis", "python", "qgis"))
        if has_qgis and os.path.exists(python) and not any(_same_python(python, known) for known in seen):
            seen.append(python)
            found.append(Runtime("conda", [python], f"conda environment ({prefix})", env))
    return found


def candidates() -> List[Runtime]:
    """Every place worth trying, in the order of preference. Costs a few file lookups, starts nothing."""
    found = _override() + _current()
    private = private_runtime()
    if private is not None:
        found.append(private)
    found += _base_python()
    if os.name == "nt":
        found += _windows_installs()
    elif sys.platform == "darwin":
        found += _macos_installs() + _posix_pythons()
    else:
        found += _posix_pythons()
    found += _conda_environments()
    return found


# --- trying one ---------------------------------------------------------------------------------------------------


# Variables that tie a process to one environment. Those that point into the launcher's own environment (its
# virtual environment, the conda environment active in its shell) would point the QGIS of another install at the
# wrong PROJ database, Qt plugins or Python packages. Those that point elsewhere are kept: a QGIS built from source,
# the qgis/qgis images and the OSGeo4W shell find PyQGIS through PYTHONPATH.
ALWAYS_DROPPED = ("PYTHONHOME", "VIRTUAL_ENV", "__PYVENV_LAUNCHER__", "PYTHONSTARTUP")
PATH_LISTS = ("PYTHONPATH", "QT_PLUGIN_PATH", "GDAL_DRIVER_PATH")
SINGLE_PATHS = ("QGIS_PREFIX_PATH", "PROJ_DATA", "PROJ_LIB", "GDAL_DATA", "CONDA_PREFIX")


def _launcher_roots() -> List[str]:
    """The folders of the launcher's own environment: its virtual environment, the active conda environment."""
    roots = []
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        roots.append(sys.prefix)
    if os.environ.get("CONDA_PREFIX"):
        roots.append(os.environ["CONDA_PREFIX"])
    return [os.path.normcase(os.path.abspath(root)) for root in roots]


def _inside(path: str, roots: List[str]) -> bool:
    path = os.path.normcase(os.path.abspath(path)) if path else ""
    return any(path == root or path.startswith(root + os.sep) for root in roots)


# Exit code of the host when its Python has no PyQGIS any more (the runtime was uninstalled since it was chosen).
EXIT_NO_QGIS = 86
# What the other Python runs: the script and the arguments come through the environment, never through the command
# line, which a ``.bat`` hands to cmd.exe (``&``, ``%VAR%`` and ``^`` in a file name or a folder would be read as
# commands, variables or escapes there).
LOADER = ("import json, os, runpy, sys; script = os.environ.pop('FILTERMATE_SCRIPT'); "
          "sys.argv = [script] + json.loads(os.environ.pop('FILTERMATE_SCRIPT_ARGS', '[]')); "
          "runpy.run_path(script, run_name='__main__')")


def child_environment(runtime: Runtime, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """The environment of a process started in ``runtime``: the launcher's, without what ties it to another install."""
    env = dict(os.environ)
    if runtime.kind != "current":
        roots = _launcher_roots()
        for name in ALWAYS_DROPPED:
            env.pop(name, None)
        for name in SINGLE_PATHS:
            if name in env and _inside(env[name], roots):
                env.pop(name)
        if roots and "CONDA_PREFIX" not in env:
            env.pop("CONDA_DEFAULT_ENV", None)
        for name in PATH_LISTS:
            if name in env:
                kept = [entry for entry in env[name].split(os.pathsep) if entry and not _inside(entry, roots)]
                if kept:
                    env[name] = os.pathsep.join(kept)
                else:
                    env.pop(name)
    for name, value in runtime.env.items():
        if name in PATH_LISTS and env.get(name):
            value = value + os.pathsep + env[name]  # the runtime's own entries first
        env[name] = value
    env.update(extra or {})
    return env


def script_command(runtime: Runtime, script: str, arguments: Optional[List[str]] = None):
    """The command and the environment that run ``script`` with ``arguments`` in the Python of ``runtime``."""
    env = {"FILTERMATE_SCRIPT": script, "FILTERMATE_SCRIPT_ARGS": json.dumps(list(arguments or []))}
    return runtime.command + ["-c", LOADER], env


def _run(command: List[str], env: Dict[str, str], timeout: float):
    """Run ``command``, its output captured; on a timeout, the whole tree is ended (a ``.bat`` or ``micromamba run``
    starts the Python as a child, which would keep the pipes open). Returns (code, stdout, stderr), code None on a
    timeout."""
    options = {}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True
    # nosec B603 - a Python found on this machine, a fixed argument list
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,  # nosec B603
                               env=env, **options)
    try:
        out, err = process.communicate(timeout=timeout)
        code = process.returncode
    except subprocess.TimeoutExpired:
        _end_tree(process)
        try:
            out, err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
        code = None
    return code, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def _end_tree(process) -> None:
    try:
        if os.name == "nt":
            # nosec B603 B607 - taskkill of Windows on a process this module started
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, timeout=30)  # nosec
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        process.kill()
    except OSError:
        pass


def probe(runtime: Runtime, timeout: float = 180.0) -> Runtime:
    """Start the Python of ``runtime`` and record what it has in ``runtime.info``."""
    command, extra = script_command(runtime, PROBE_SCRIPT)
    extra["QT_QPA_PLATFORM"] = "offscreen"
    try:
        code, out, err = _run(command, child_environment(runtime, extra), timeout)
    except FileNotFoundError:
        runtime.info = {"ok": False, "error": "not found"}
        return runtime
    except OSError as error:
        runtime.info = {"ok": False, "error": str(error)}
        return runtime
    if code is None:
        runtime.info = {"ok": False, "error": f"no answer after {int(timeout)} s"}
        return runtime
    for line in out.splitlines():
        if line.startswith("FM_RUNTIME "):
            try:
                runtime.info = json.loads(line[len("FM_RUNTIME "):])
            except ValueError:
                continue
            if not runtime.info.get("ok"):
                runtime.info["error"] = _short(str(runtime.info.get("error") or "no PyQGIS"))
            return runtime
    tail = (err or out).strip().splitlines()
    runtime.info = {"ok": False, "error": _short(tail[-1]) if tail else f"exit code {code}"}
    return runtime


def _short(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


# --- choosing -----------------------------------------------------------------------------------------------------


def _stamp(runtime: Runtime) -> float:
    executable = runtime.command[0]
    if not os.path.exists(executable):
        executable = shutil.which(executable) or executable  # an override given as a bare command name
    try:
        return os.path.getmtime(executable)
    except OSError:
        return 0.0


def _read_cache() -> Optional[Runtime]:
    try:
        with open(paths.runtime_cache_file(), encoding="utf-8") as handle:
            data = json.load(handle)
        runtime = Runtime(**data["runtime"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not runtime.usable or _stamp(runtime) != data.get("stamp") or not _stamp(runtime):
        return None
    # A cached choice must not outlive a change of what the user asked for, or of the launcher's own Python.
    if data.get("override", "") != os.environ.get(ENV_OVERRIDE, "").strip():
        return None
    if runtime.kind == "current" and runtime.command != [sys.executable]:
        return None
    return runtime


def _write_cache(runtime: Runtime) -> None:
    try:
        os.makedirs(os.path.dirname(paths.runtime_cache_file()), exist_ok=True)
        with open(paths.runtime_cache_file(), "w", encoding="utf-8") as handle:
            json.dump({"runtime": asdict(runtime), "stamp": _stamp(runtime),
                       "override": os.environ.get(ENV_OVERRIDE, "").strip()}, handle, indent=1)
    except OSError:
        pass  # a read-only home: the search simply runs again next time


def forget_cache() -> None:
    try:
        os.remove(paths.runtime_cache_file())
    except OSError:
        pass


def survey() -> List[Runtime]:
    """Every candidate, tried. For ``filtermate doctor``: slow (one process each)."""
    return [probe(runtime) for runtime in candidates()]


def choose(tried: List[Runtime]) -> Optional[Runtime]:
    """The runtime to use among tried ones: the first usable of the preferred kinds, else the newest install."""
    for kind in ("override", "current", "private"):
        for runtime in tried:
            if runtime.kind == kind and runtime.usable:
                return runtime
    rest = [runtime for runtime in tried if runtime.usable]
    return max(rest, key=lambda runtime: int(runtime.info.get("qgis_int") or 0)) if rest else None


last_override_failure: Optional[Runtime] = None  # set by resolve() when the runtime the user named does not start


def resolve(refresh: bool = False) -> Optional[Runtime]:
    """The runtime to start the host in, None when this machine has none.

    The answer of the last launch is reused while its Python has not changed. Otherwise the
    preferred kinds are tried one by one and the search stops at the first that works; the
    installs of the machine are all tried, to take the newest.
    """
    if not refresh:
        cached = _read_cache()
        if cached is not None:
            return cached
    found = candidates()
    global last_override_failure
    last_override_failure = None
    for kind in ("override", "current", "private"):
        for runtime in found:
            if runtime.kind == kind and probe(runtime).usable:
                _write_cache(runtime)
                return runtime
            if runtime.kind == "override":
                # What the user named does not start: say so rather than start another QGIS behind their back.
                last_override_failure = runtime
                return None
    chosen = choose([probe(runtime) for runtime in found if runtime.kind in ("install", "conda")])
    if chosen is not None:
        _write_cache(chosen)
    return chosen


# --- starting -----------------------------------------------------------------------------------------------------


def host_command(runtime: Runtime, host_args: List[str]):
    """The command and the extra environment that start the host in ``runtime``."""
    return script_command(runtime, BOOTSTRAP_SCRIPT, host_args)


def launch(runtime: Runtime, host_args: List[str]) -> int:
    """Run the host in ``runtime`` and return its exit code (``EXIT_NO_QGIS`` when that Python lost PyQGIS)."""
    if runtime.kind == "current":
        from . import _bootstrap
        return int(_bootstrap.main(list(host_args)) or 0)
    command, extra = host_command(runtime, host_args)
    try:
        # nosec B603 - same command as the probe, the arguments of the user passed in the environment
        code = subprocess.call(command, env=child_environment(runtime, extra))  # nosec B603
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        forget_cache()
        print(f"FilterMate: cannot start {runtime.label}: {error}", file=sys.stderr)
        return 1
    if code == EXIT_NO_QGIS:
        forget_cache()
    return code
