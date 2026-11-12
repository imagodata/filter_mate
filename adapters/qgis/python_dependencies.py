# -*- coding: utf-8 -*-
"""Python packages FilterMate installs for itself, once the user agreed.

They are declared by the ``python_dependencies`` key of ``metadata.txt`` (the
``plugin_dependencies`` key of QGIS only names other QGIS plugins). A package this
Python already finds is left alone. A missing one goes to a folder of the QGIS
profile, one per Python version, at the end of ``sys.path``: nothing is written
to the Python of QGIS, and what QGIS ships (numpy) keeps priority.

At launch only the folder is put on ``sys.path``: nothing is downloaded before the
user confirms, which the raster panel asks at the first click on its Segment target.

``--target`` makes pip ignore what this Python has: numpy is pinned to the version QGIS
imports (:func:`numpy_requirement`), and a package of the folder whose files are not all
there (an install cut short) is installed again over it (:func:`is_intact`, ``--upgrade``).
"""
import csv
import importlib
import importlib.util
import logging
import os
import re
import subprocess  # nosec B404 - pip of the Python of QGIS, fixed argv
import sys
import tempfile
import time
from typing import Any, Callable, List, Optional, Sequence

from qgis.core import QgsTask
from qgis.PyQt.QtCore import QCoreApplication

logger = logging.getLogger(__name__)

METADATA_KEY = 'python_dependencies'
TIMEOUT_SECONDS = 900
POLL_SECONDS = 0.2
OUTPUT_TAIL = 2000

_task: Any = None
_failed = False
_listeners: List[Callable[[], None]] = []
_intact: dict = {}  # package -> is_intact, until the next install


def declared_packages(metadata_path: Optional[str] = None) -> List[str]:
    """The packages of the ``python_dependencies`` key, comma separated (the pip name is also the import name)."""
    path = metadata_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'metadata.txt')
    with open(path, encoding='utf-8') as stream:
        for line in stream:
            key, separator, value = line.partition('=')
            if separator and key.strip() == METADATA_KEY:
                return [name.strip() for name in value.split(',') if name.strip()]
    return []


def target_directory() -> str:
    """Where the packages go: in the QGIS profile, per Python version (compiled packages depend on it)."""
    from qgis.core import QgsApplication
    version = f'py{sys.version_info[0]}{sys.version_info[1]}'
    return os.path.join(QgsApplication.qgisSettingsDirPath(), 'filtermate', 'python', version)


def activate(directory: str) -> None:
    """Make the packages of ``directory`` importable, after those of QGIS."""
    os.makedirs(directory, exist_ok=True)
    if directory not in sys.path:
        sys.path.append(directory)
    importlib.invalidate_caches()


def activate_installed() -> None:
    """At launch: what an earlier session installed becomes importable. Installs nothing, never raises."""
    try:
        directory = target_directory()
        if os.path.isdir(directory):
            activate(directory)
    except Exception as exc:
        logger.debug(f"[FM5] Python dependencies folder not activated: {exc}")


def is_available(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        return False


def is_intact(package: str) -> bool:
    """False when ``package`` lies in the folder of FilterMate with some of its files missing: an install cut short.

    ``find_spec`` finds such a package, so it was taken as installed and never repaired (and pip skips
    a folder already there without ``--upgrade``). Its files are compared with those pip recorded
    (the RECORD of its distribution), without importing it: its native library loads in a worker.
    A package found elsewhere (the Python of QGIS), or that cannot be judged, counts as intact.
    """
    if package not in _intact:
        try:
            _intact[package] = _files_present(package)
        except Exception as exc:  # no profile (a bare qgis_process), unreadable metadata: not judged
            logger.debug(f"[FM5] {package} not checked: {exc}")
            return True
    return _intact[package]


def _files_present(package: str) -> bool:
    from importlib import metadata
    spec = importlib.util.find_spec(package)
    if spec is None:
        return True  # missing, not damaged
    folder = os.path.normcase(os.path.realpath(target_directory()))
    locations = list(spec.submodule_search_locations or ()) or ([spec.origin] if spec.origin else [])
    if not any(os.path.normcase(os.path.realpath(location)).startswith(folder + os.sep) for location in locations):
        return True
    name = re.sub(r'[-_.]+', '-', package).lower()
    distribution = next((found for found in metadata.distributions(path=[folder])
                         if re.sub(r'[-_.]+', '-', found.metadata['Name'] or '').lower() == name), None)
    record = distribution.read_text('RECORD') if distribution is not None else None
    if not record:
        return False  # its folder without the record of its files
    # Read here: Distribution.files leaves out the files that are missing (Python 3.12). The files of its own folder
    # only (a script recorded as ../../bin/... is moved elsewhere by --target), compiled ones aside.
    paths = [row[0].replace('\\', '/') for row in csv.reader(record.splitlines()) if row]
    own = [path for path in paths if path.split('/')[0] == package and not path.endswith('.pyc')]
    return all(os.path.exists(distribution.locate_file(path)) for path in own)


def missing_packages(packages: Sequence[str]) -> List[str]:
    """Those ``packages`` this Python does not find, or finds in the folder of FilterMate with files missing."""
    return [package for package in packages if not is_available(package) or not is_intact(package)]


def numpy_requirement() -> List[str]:
    """``['numpy==<the version QGIS imports>']``; nothing when it cannot be told (a development build).

    ``--target`` makes pip ignore the installed packages: it resolved numpy afresh (a numpy 2 for the newest
    onnxruntime) into the folder of FilterMate, while QGIS imports its own numpy first, and an onnxruntime
    built for another numpy does not load. Pinned to the numpy of QGIS, pip picks an onnxruntime that runs
    with it, or says that none does.
    """
    try:
        import numpy
        version = str(numpy.__version__).split('+')[0]  # a local build (1.26.4+mkl) is that release
    except Exception:  # noqa: BLE001 - no numpy: nothing to keep
        return []
    return [f'numpy=={version}'] if re.fullmatch(r'\d+(\.\d+)+', version) else []


def pip_command(python: str, directory: str, packages: Sequence[str], upgrade: bool = False,
                requirements: Sequence[str] = ()) -> List[str]:
    """pip installing ``packages`` into ``directory``.

    Args:
        upgrade: Replace what the folder already holds (pip skips a folder already there otherwise).
        requirements: Pins kept by the resolver (:func:`numpy_requirement`).
    """
    return ([python, '-m', 'pip', 'install', '--target', directory, '--only-binary=:all:', '--no-input',
             '--disable-pip-version-check', '--no-warn-script-location'] + (['--upgrade'] if upgrade else [])
            + list(requirements) + list(packages))


def manual_command() -> str:
    """The pip command to run by hand when the install from the panel failed: into the same folder, numpy kept."""
    from .coverage_layers.sam_model import install_command
    return install_command(target_directory(), numpy_requirement())


class PipInstallTask(QgsTask):
    """Run pip off the main thread.

    Args:
        callback: ``callback(task, success)`` on the main thread; ``task.error`` says why it failed.
        proxy: URL of the proxy QGIS uses, None for the one of the system.
    """

    def __init__(self, command: Sequence[str], packages: Sequence[str], callback: Any, proxy: Optional[str] = None) -> None:
        super().__init__(QCoreApplication.translate('PipInstallTask', 'FilterMate: installing {0}').format(', '.join(packages)),
                         QgsTask.Flag.CanCancel)
        self.command, self.packages, self.callback, self.proxy = list(command), list(packages), callback, proxy
        self.error = ''

    def _environment(self) -> dict:
        environment = dict(os.environ)
        if self.proxy:  # not on the command line: it may hold a password
            environment['HTTP_PROXY'] = environment['HTTPS_PROXY'] = self.proxy
        return environment

    def run(self) -> bool:
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        try:
            with tempfile.TemporaryFile() as output:
                process = subprocess.Popen(self.command, stdout=output, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,  # nosec B603 - fixed argv
                                           env=self._environment(), **options)
                deadline = time.monotonic() + TIMEOUT_SECONDS
                while process.poll() is None:
                    if self.isCanceled() or time.monotonic() > deadline:
                        process.kill()
                        process.wait()
                        self.error = '' if self.isCanceled() else 'pip took too long'
                        return False
                    time.sleep(POLL_SECONDS)
                output.seek(0)
                text = output.read().decode('utf-8', 'replace')
            if process.returncode != 0:
                self.error = text[-OUTPUT_TAIL:].strip() or f'pip exited with code {process.returncode}'
                return False
            importlib.invalidate_caches()
            return True
        except Exception as exc:  # no pip, no such Python: told in the log, the panel shows the command
            self.error = str(exc) or type(exc).__name__
            return False

    def finished(self, result: bool) -> None:
        global _task
        _task = None
        _intact.clear()  # judged again on the files written
        callback, self.callback = self.callback, None
        listeners = list(_listeners)
        _listeners.clear()
        if callback is not None:
            self._notify(lambda: callback(self, bool(result)))
        for listener in listeners:
            self._notify(listener)

    @staticmethod
    def _notify(call: Callable[[], None]) -> None:
        """One failing listener must not leave the others, nor the panel, waiting."""
        try:
            call()
        except Exception as exc:
            logger.warning(f"[FM5] end of the Python dependencies install not notified: {exc}", exc_info=True)


def installing() -> bool:
    return _task is not None


def install_failed() -> bool:
    """The last install of this session did not succeed (a cancel is no failure)."""
    return _failed


def notify_when_done(listener: Callable[[], None]) -> None:
    """Call ``listener`` on the main thread when the running install ends (nothing without one)."""
    if _task is not None:
        _listeners.append(listener)


def install_missing(on_installed: Optional[Callable[[Sequence[str]], None]] = None) -> None:
    """Install in the background what ``metadata.txt`` declares and this Python lacks, the user having agreed. Never raises."""
    global _task, _failed
    try:
        if _task is not None:
            return
        _failed = False
        directory = target_directory()
        activate(directory)
        _intact.clear()  # the user asks now: the files as they are now
        packages = missing_packages(declared_packages())
        if not packages:
            return
        # Something of an earlier install is there, complete or cut short: replaced, not skipped.
        upgrade = bool(os.listdir(directory))
        from .coverage_layers.sam_model import python_executable
        from .coverage_layers.segmentation import qgis_proxy_url
        python = python_executable()
        if not os.path.isfile(python):
            logger.warning(f"[FM5] {packages} not installed: the Python of QGIS was not found")
            _failed = True
            return

        def done(task: Any, success: bool) -> None:
            global _failed
            _failed = not success and bool(task.error)
            if success:
                logger.info(f"[FM5] installed {task.packages} into {directory}")
                if on_installed is not None:
                    on_installed(task.packages)
            elif task.error:
                logger.warning(f"[FM5] {task.packages} not installed: {task.error}")

        from qgis.core import QgsApplication
        _task = PipInstallTask(pip_command(python, directory, packages, upgrade, numpy_requirement()), packages, done,
                               qgis_proxy_url())
        QgsApplication.taskManager().addTask(_task)
    except Exception as exc:
        _failed = True
        logger.warning(f"[FM5] Python dependencies not checked: {exc}", exc_info=True)


def cancel() -> None:
    """The plugin is unloaded: pip stops, and the callback of the task hears nobody."""
    global _task
    task, _task = _task, None
    _listeners.clear()
    if task is not None:
        task.callback = None
        try:
            task.cancel()
        except RuntimeError:
            pass  # already finished and deleted
