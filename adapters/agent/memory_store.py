# -*- coding: utf-8 -*-
"""The memory of the agent in a file of the QGIS profile (``FilterMate/agent_memory.json``), read and written here.

One file a person can read, correct and copy to another machine (core/agent/memory.py says what it holds). A file that
cannot be read is never written: a hand edit gone wrong is not lost. A write holds a lock file, reads the file again,
makes its changes on that, then replaces the file in one move: two QGIS open on the same profile do not lose each
other's notes, and a write cut short leaves the file as it was.

Also here: the signature notes of a source are kept under, from a layer of QGIS.
"""
from __future__ import annotations

import contextlib
import logging
import os
import stat
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Iterator, List, Optional, Sequence, Tuple

from ...core.agent.memory import MAX_SIGNATURE_CHARS, Memory, UnreadableMemory, applied, dump, parse
from .skill_sources import user_folder

logger = logging.getLogger("FilterMate.agent")
FILE_NAME = "agent_memory.json"
MAX_FILE_BYTES = 1_000_000  # 500 notes of 300 characters weigh a fifth of it
# The providers whose signature (core/domain/layer_signature.py) comes from the data source itself: a table of a
# database, a layer of a file. For the others it is the name the user gave the layer: renamed, the layer would lose
# its notes, and two layers of the same name would share them. They have none for now (a raster, a point cloud, a web
# service: a note for every project serves them).
_SOURCE_PROVIDERS = frozenset({"postgres", "spatialite", "ogr"})
# What a signature made of a connection string or an address would hold: a user, a password, a token. Such a source
# gets no signature at all, so that none is ever written to the file.
_NOT_A_NAME = ("=", "@", "?", "&", ";", "://")
LOCK_SUFFIX = ".lock"
LOCK_WAIT_SECONDS = 2.0
LOCK_STALE_SECONDS = 30.0  # a QGIS that died while it wrote: its lock is taken over
TEMPORARY_PREFIX = ".agent_memory."


def memory_path() -> Optional[Path]:
    """``FilterMate/agent_memory.json`` of the QGIS profile, next to ``skills/``; None when the profile is unknown."""
    folder = user_folder()
    return folder.parent / FILE_NAME if folder is not None else None


def read_memory(path: Optional[Path] = None) -> Memory:
    """The memory the file holds; an empty one when there is no file yet.

    Raises:
        UnreadableMemory: The file cannot be read as a memory. It is left as it is.
    """
    path = path if path is not None else memory_path()
    if path is None or not path.exists():
        return Memory()
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise UnreadableMemory("it is larger than 1 MB")
        stored = path.read_text(encoding="utf-8-sig")  # a text editor of Windows may add the mark
    except (OSError, UnicodeDecodeError) as exc:
        raise UnreadableMemory(str(exc)) from None
    return parse(stored)


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Hold ``<path>.lock`` while the file is read and replaced: another QGIS of the same profile waits its turn.

    Raises:
        OSError: Another QGIS still writes after ``LOCK_WAIT_SECONDS``.
    """
    lock = path.with_name(path.name + LOCK_SUFFIX)
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            os.close(os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > LOCK_STALE_SECONDS:
                    lock.unlink()
                    continue
            except OSError:  # released meanwhile
                continue
            if time.monotonic() >= deadline:
                raise OSError("another QGIS is writing the memory: try again") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _sweep(folder: Path) -> None:
    """Remove the temporary files a write cut short left in ``folder`` (older than the stale lock)."""
    try:
        for entry in folder.iterdir():
            if entry.name.startswith(TEMPORARY_PREFIX) and entry.name.endswith(".tmp") \
                    and time.time() - entry.stat().st_mtime > LOCK_STALE_SECONDS:
                entry.unlink()
    except OSError:
        logger.debug("Agent: temporary files of the memory not swept", exc_info=True)


def change_memory(changes: Sequence[Sequence[Any]], path: Optional[Path] = None, today: str = "") -> Memory:
    """Make ``changes`` (``core.agent.memory.applied``) on the file as it is now, and write it; the memory after.

    The file a link points to is written, the link stays; a file that was there keeps its permissions.

    Raises:
        UnreadableMemory: The file cannot be read: nothing is written.
        ValueError: A change that cannot be made: nothing is written.
        OSError: The file could not be written; the one before is still there.
    """
    path = path if path is not None else memory_path()
    if path is None:
        raise OSError("the folder of FilterMate in the QGIS profile is not known")
    path = Path(os.path.realpath(str(path)))  # through a link, to the file itself
    path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(path):
        before = read_memory(path)
        memory = applied(before, changes, today or date.today().isoformat())
        if memory == before:
            return memory
        _sweep(path.parent)
        handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=TEMPORARY_PREFIX, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(dump(memory))
                stream.flush()
                os.fsync(stream.fileno())  # on the disk before it takes the place of the file
            if path.exists():
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
    return memory


_processing_folder: Optional[str] = None  # read once: it does not change in a session of QGIS


def _scratch_folders() -> Tuple[str, str]:
    """``(the temporary folder of Processing as QGIS names it, the temporary folder of the system)``, each as written
    on this machine; "" for the first outside QGIS."""
    global _processing_folder
    if _processing_folder is None:
        try:
            from qgis.core import QgsProcessingUtils
            folder = QgsProcessingUtils.tempFolder()
            _processing_folder = os.path.normcase(os.path.abspath(folder)) if isinstance(folder, str) and folder else ""
        except Exception:  # outside QGIS
            logger.debug("Agent: temporary folder of Processing not read", exc_info=True)
            _processing_folder = ""
    return _processing_folder, os.path.normcase(os.path.abspath(tempfile.gettempdir()))


def _inside(folder: str, path: str) -> bool:
    return bool(folder) and (path == folder or path.startswith(folder.rstrip(os.sep) + os.sep))


def _temporary(source: str) -> bool:
    """Is ``source`` an output of an algorithm, gone with the session: a file of the temporary folder of Processing
    (the one QGIS names, or a ``processing_...`` folder of the temporary folder of the system). A file the user keeps
    in the temporary folder itself is theirs.

    The paths are compared as they are written: the disk is not asked (this runs on the main thread with each request,
    and a share that no longer answers would hold QGIS)."""
    path = (source or "").split("|", 1)[0]
    if not path:
        return False
    path = os.path.normcase(os.path.abspath(path))
    processing, system = _scratch_folders()
    if _inside(processing, path):
        return True
    if not _inside(system, path):
        return False
    inside = os.path.dirname(path)[len(system):].split(os.sep)
    return any(part.startswith("processing_") for part in inside)


def source_signature(layer: Any, derived: Any = None) -> str:
    """The signature notes are kept under for ``layer`` (that of the favorites, core/domain/layer_signature.py); ""
    for a layer whose source is not told again in another project: held in memory, made by FilterMate
    (``derived``, the registry of its clipped layers) or by an algorithm of Processing in its temporary folder, of a
    provider whose signature is only the name of the layer, or whose source is a connection string or an address
    (it may hold a user, a password, a token: nothing of it is kept)."""
    try:
        provider = (layer.providerType() or "").lower()
        if provider not in _SOURCE_PROVIDERS or (derived is not None and derived.get(layer.id()) is not None):
            return ""
        source = layer.source() or ""
        if provider == "ogr" and (any(mark in source.split("|", 1)[0] for mark in _NOT_A_NAME)
                                  or _connection_string(source)):
            return ""
        if _temporary(source):
            return ""
        from ...core.domain.layer_signature import LayerSignature
        signature = " ".join(LayerSignature.compute(layer).split())
    except Exception:  # a layer deleted meanwhile, or a provider that does not answer
        logger.debug("Agent: no signature for a layer", exc_info=True)
        return ""
    name = signature.split("::", 1)[1] if "::" in signature else ""
    if not name or name == "?" or len(signature) > MAX_SIGNATURE_CHARS or any(mark in name for mark in _NOT_A_NAME):
        return ""
    return signature


def _connection_string(source: str) -> bool:
    """Is the source of an OGR layer a connection to a server (``MySQL:db,user=...``, ``PG:...``, ``ODBC:...``) rather
    than a file: a word and a colon at its start that is not the letter of a Windows drive."""
    head = source.split("|", 1)[0]
    prefix, colon, _rest = head.partition(":")
    return bool(colon) and len(prefix) > 1 and prefix.isalnum() and not head.startswith("/")


def project_sources(layer_ids: Optional[Sequence[str]] = None, active_id: str = "",
                    project: Any = None) -> Tuple[List[Tuple[str, str]], str]:
    """``(signature, name)`` of the layers of the project and the signature of the active one, as
    ``core.agent.memory.chosen`` takes them: in the order of ``layer_ids`` (every layer, by name, without it)."""
    if project is None:
        from qgis.core import QgsProject
        project = QgsProject.instance()
    try:
        from ..qgis.coverage_layers.snapshots import registry
        derived = registry()
    except Exception:  # outside QGIS, or before the registry exists
        derived = None
    if layer_ids is None:
        layers = sorted(project.mapLayers().values(), key=lambda layer: layer.name().lower())
    else:
        layers = [layer for layer in (project.mapLayer(str(layer_id)) for layer_id in layer_ids) if layer is not None]
    sources, active = [], ""
    for layer in layers:
        try:
            signature = source_signature(layer, derived)
            sources.append((signature, layer.name()))
            if active_id and layer.id() == active_id:
                active = signature
        except (RuntimeError, AttributeError):  # a layer deleted meanwhile
            continue
    return sources, active
