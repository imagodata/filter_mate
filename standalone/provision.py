# -*- coding: utf-8 -*-
"""A QGIS runtime of FilterMate's own, for a machine that has no QGIS (standard library only).

``filtermate setup`` downloads micromamba (one file, checked against its published SHA-256)
and creates a conda-forge environment holding QGIS, all under the application's folder: no
administrator rights, nothing outside that folder, removed with ``filtermate setup --remove``.
"""

import hashlib
import http.client
import os
import platform
import shutil
import stat
import subprocess  # nosec B404 - runs the micromamba this module just downloaded and checked
import sys
import urllib.request
from typing import Callable, List, Optional

from . import paths

RELEASES = "https://github.com/mamba-org/micromamba-releases/releases/latest/download/"
CHANNEL = "conda-forge"
# draco: QGIS 4.2.3 of conda-forge links libdraco.so.9, which draco 1.5.9 no longer has (November 2026); the
# probe after the install says it when a pin like this one is needed again. qgis 3.44 is not offered: it is
# solved with Python 3.14, for which conda-forge has no PyQt5.
PACKAGES = ("qgis>=4.2", "draco<1.5.9")
# Free space asked before starting: the environment and the package cache beside it.
NEEDED_BYTES = 8 * 1024 ** 3
# conda-forge mirrors stall now and then (a package below 30 bytes/s for a minute ends micromamba).
ATTEMPTS = 3


class ProvisionError(RuntimeError):
    """The runtime could not be installed; the message says why, for the user."""


def platform_tag() -> Optional[str]:
    """The micromamba build for this machine, None when there is none."""
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if os.name == "nt":
        return "win-arm64" if arm else "win-64" if machine in ("amd64", "x86_64") else None
    if sys.platform == "darwin":
        return "osx-arm64" if arm else "osx-64" if machine == "x86_64" else None
    if sys.platform.startswith("linux"):
        return {"x86_64": "linux-64", "amd64": "linux-64", "aarch64": "linux-aarch64", "arm64": "linux-aarch64",
                "ppc64le": "linux-ppc64le"}.get(machine)
    return None


MARKER = ".filtermate-runtime"  # written first by setup: `setup --remove` deletes only a folder that has it


def marker_path() -> str:
    return os.path.join(paths.runtime_dir(), MARKER)


def micromamba_path() -> str:
    return os.path.join(paths.runtime_dir(), "bin", "micromamba.exe" if os.name == "nt" else "micromamba")


def packages_cache() -> str:
    """Where micromamba downloads and unpacks the packages.

    Under the runtime, except on Windows: micromamba nests each package under
    ``pkgs\\https\\conda.anaconda.org\\conda-forge\\win-64\\<package>``, and the deepest files of
    QGIS then pass the 260 characters Windows allows when long paths are off (its default):
    the unpacking fails ("the directory is not empty"). The cache goes in a short folder of
    the user's local data there, emptied after the install and deleted with the runtime.
    """
    if os.name == "nt" and not os.environ.get("FILTERMATE_HOME"):
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "fmpk")
    if os.name == "nt":  # a folder the user chose (often another disk, for the room): kept short within it
        return os.path.join(paths.user_data_dir(), "pk")
    return os.path.join(root_prefix(), "pkgs")


def micromamba_environment() -> dict:
    """The environment of every micromamba command: its package cache (see ``packages_cache``)."""
    env = dict(os.environ)
    env["CONDA_PKGS_DIRS"] = packages_cache()
    env["MAMBA_PKGS_DIRS"] = packages_cache()
    return env


def root_prefix() -> str:
    return os.path.join(paths.runtime_dir(), "root")


def environment_dir() -> str:
    return os.path.join(paths.runtime_dir(), "envs", "qgis")


def environment_python() -> str:
    env = environment_dir()
    return os.path.join(env, "python.exe") if os.name == "nt" else os.path.join(env, "bin", "python")


def installed_runtime():
    """The installed runtime as a ``runtime.Runtime``, None when ``setup`` has not run (or not to the end)."""
    from .runtime import Runtime
    if not (os.path.exists(micromamba_path()) and os.path.exists(environment_python())):
        return None
    # What the activation script of the qgis package sets, which `micromamba run` does not run.
    prefix = environment_dir()
    base = os.path.join(prefix, "Library") if os.name == "nt" else prefix  # conda-forge puts QGIS under Library on Windows
    python = os.path.join(base, "python")
    if os.name != "nt":
        python = os.path.join(prefix, "share", "qgis", "python")
    plugins = [os.path.join(base, "plugins")] + ([os.path.join(base, "qtplugins")] if os.name == "nt" else [])
    env = {"QGIS_PREFIX_PATH": base,
           "PYTHONPATH": os.pathsep.join([python, os.path.join(python, "plugins")]),
           "QT_PLUGIN_PATH": os.pathsep.join(plugins)}
    command = [micromamba_path(), "run", "-r", root_prefix(), "-p", environment_dir(), "python"]
    return Runtime("private", command, f"FilterMate's own runtime ({environment_dir()})", env)


def _download(url: str, target: str, log: Callable[[str], None]) -> None:
    if not url.startswith("https://"):
        raise ProvisionError(f"Refusing to download from {url}")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    partial = target + ".part"
    try:
        with urllib.request.urlopen(url, timeout=120) as response, open(partial, "wb") as out:  # nosec B310 - https only
            total = int(response.headers.get("Content-Length") or 0)
            done, shown = 0, -1
            while True:
                block = response.read(1 << 16)
                if not block:
                    break
                out.write(block)
                done += len(block)
                percent = (done * 100 // total) if total else 0
                if total and percent // 20 != shown:
                    shown = percent // 20
                    log(f"  {percent} %")
        os.replace(partial, target)
    except (OSError, http.client.HTTPException) as error:  # IncompleteRead is no OSError
        try:
            os.remove(partial)
        except OSError:
            pass
        raise ProvisionError(f"Download failed ({url}): {error}") from error


def _read_url(url: str) -> str:
    if not url.startswith("https://"):
        raise ProvisionError(f"Refusing to download from {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:  # nosec B310 - https only
            return response.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as error:
        raise ProvisionError(f"Download failed ({url}): {error}") from error


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_micromamba(log: Callable[[str], None] = print) -> str:
    """Download micromamba for this machine, check its digest, return its path."""
    tag = platform_tag()
    if tag is None:
        raise ProvisionError(
            f"No micromamba build for this machine ({sys.platform}, {platform.machine()}). "
            "Install QGIS, then start FilterMate again.")
    target = micromamba_path()
    if os.path.exists(target):
        return target
    log(f"Downloading micromamba ({tag})...")
    staged = target + ".new"
    _download(RELEASES + f"micromamba-{tag}", staged, log)
    try:
        words = _read_url(RELEASES + f"micromamba-{tag}.sha256").split()
        expected = words[0].strip().lower() if words else ""
        if len(expected) != 64 or _sha256(staged) != expected:
            raise ProvisionError("The micromamba download does not match its published SHA-256: nothing was installed.")
    except BaseException:
        try:
            os.remove(staged)
        except OSError:
            pass
        raise
    if os.name != "nt":
        os.chmod(staged, os.stat(staged).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.replace(staged, target)
    return target


def create_command(micromamba: str, packages=PACKAGES) -> List[str]:
    return [micromamba, "create", "--yes", "-r", root_prefix(), "-p", environment_dir(),
            "--override-channels", "-c", CHANNEL, *packages]


def free_bytes() -> int:
    folder = paths.runtime_dir()
    while not os.path.isdir(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            return 0
        folder = parent
    return shutil.disk_usage(folder).free


def install(log: Callable[[str], None] = print, packages=PACKAGES):
    """Install the runtime and return it, tried. Raises ``ProvisionError`` with a message for the user."""
    from . import runtime as runtime_module
    if free_bytes() < NEEDED_BYTES:
        raise ProvisionError(
            f"Not enough free space in {paths.runtime_dir()}: {free_bytes() / 1024 ** 3:.1f} GB free, "
            f"about {NEEDED_BYTES // 1024 ** 3} GB needed. Set FILTERMATE_HOME to a folder on another disk.")
    folder = paths.runtime_dir()
    if os.path.isdir(folder) and os.listdir(folder) and not os.path.exists(marker_path()):
        raise ProvisionError(f"{folder} exists and was not made by FilterMate: nothing was installed there. "
                             "Set FILTERMATE_HOME to another folder.")
    os.makedirs(folder, exist_ok=True)
    with open(marker_path(), "w", encoding="utf-8") as handle:
        handle.write("The QGIS runtime of FilterMate (filtermate setup). `filtermate setup --remove` deletes this folder.\n")
    micromamba = fetch_micromamba(log)
    log(f"Installing QGIS from {CHANNEL} into {environment_dir()} (several minutes)...")
    code = 1
    for attempt in range(1, ATTEMPTS + 1):
        if os.path.isdir(environment_dir()):
            shutil.rmtree(environment_dir())  # an install that stopped halfway
        try:
            # nosec B603 - the micromamba checked above, a fixed argument list
            code = subprocess.call(create_command(micromamba, packages), env=micromamba_environment())  # nosec B603
        except OSError as error:
            raise ProvisionError(f"micromamba did not start: {error}") from error
        if code == 0:
            break
        if attempt < ATTEMPTS:
            # Packages already downloaded stay in the cache: the next attempt fetches only what is missing.
            log(f"micromamba ended with code {code} (a download that stalled?): trying again ({attempt + 1}/{ATTEMPTS})...")
    if code != 0:
        if os.path.isdir(environment_dir()):
            shutil.rmtree(environment_dir())
        raise ProvisionError(f"micromamba ended with code {code} after {ATTEMPTS} attempts: the runtime is not installed. "
                             "Run `filtermate setup` again later: what was downloaded is kept.")
    installed = installed_runtime()
    if installed is None:
        raise ProvisionError("micromamba ended without error, but the runtime has no Python.")
    runtime_module.probe(installed)
    if not installed.usable:
        raise ProvisionError(f"The runtime is installed but does not start: {installed.describe()}")
    # The package cache is as large as the environment and only useful for a reinstall.
    try:
        subprocess.call([micromamba, "clean", "--all", "--yes", "-r", root_prefix()],  # nosec B603
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=micromamba_environment())
    except OSError:
        pass
    _remove_cache_outside()
    runtime_module.forget_cache()
    return installed


def remove() -> bool:
    """Delete the runtime folder. True when there was one."""
    from . import runtime as runtime_module
    folder = paths.runtime_dir()
    if not os.path.isdir(folder):
        return False
    if not os.path.exists(marker_path()):
        raise ProvisionError(f"{folder} was not made by `filtermate setup`: it is left alone.")
    runtime_module.forget_cache()
    _remove_cache_outside()
    failed = []
    shutil.rmtree(folder, onerror=lambda _function, path, _info: failed.append(path))
    if failed:
        raise ProvisionError(f"{len(failed)} files of {folder} could not be deleted (FilterMate still running?), "
                             f"for instance {failed[0]}. Close it and run `filtermate setup --remove` again.")
    return True


def _remove_cache_outside():
    """The package cache, when it lives outside the runtime folder (Windows): only what micromamba put there."""
    cache = packages_cache()
    inside = os.path.normcase(os.path.abspath(cache)).startswith(os.path.normcase(os.path.abspath(paths.runtime_dir())))
    if inside or not os.path.isdir(cache):
        return
    if any(name not in ("https", "cache", "urls", "urls.txt", "magic_file", "pkgs_dirs.txt") and not name.endswith(
            (".conda", ".tar.bz2", ".json")) and not os.path.isdir(os.path.join(cache, name)) for name in os.listdir(cache)):
        return  # not a cache of micromamba alone: left as it is
    shutil.rmtree(cache, ignore_errors=True)


def installed_size() -> int:
    total = 0
    for root, _dirs, files in os.walk(paths.runtime_dir()):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total
