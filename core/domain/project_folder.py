# -*- coding: utf-8 -*-
"""
Folder a project's relative paths and default exports point to.

No QGIS import at module level (the Desktop lookup imports Qt lazily).

``QgsProject.readPath('./')`` has no file to be relative to for an unsaved project and
returns ``'./'`` unchanged, which ``os.path.normpath`` turns into ``'.'``: the working
directory of QGIS (often its install folder), where nothing can be written. The code
compared the normalized value to ``'./'`` (never true), so the Desktop / home fallback
below never ran.
"""
import os
from typing import Mapping, Optional


def desktop_location() -> str:
    """The user's Desktop folder as Qt reports it ('' when unknown).

    ``QStandardPaths`` follows a Desktop redirected by OneDrive or by the system language,
    where ``<home>/Desktop`` may not exist.
    """
    try:
        from qgis.PyQt.QtCore import QStandardPaths
        location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    except Exception:  # nosec B110 - no Qt (unit tests, headless tools): the home folder is used
        return ''
    return location if isinstance(location, str) else ''


def project_folder(read_path: str, windows: Optional[bool] = None, environ: Optional[Mapping[str, str]] = None,
                   desktop: Optional[str] = None) -> str:
    """Normalized folder of ``read_path`` (the result of ``QgsProject.readPath('./')``).

    An unsaved project (empty, ``'.'`` or ``'./'``) falls back to the Desktop folder on
    Windows (``desktop``, default :func:`desktop_location`; only when it exists, a
    folder is never created) and to the home folder elsewhere.
    """
    folder = os.path.normpath(read_path) if read_path else '.'
    if folder != '.':
        return folder
    environ = os.environ if environ is None else environ
    if windows is None:
        windows = os.name == 'nt'
    if windows:
        candidate = desktop_location() if desktop is None else desktop
        if candidate and os.path.isdir(candidate):
            return os.path.normpath(candidate)
        if environ.get('USERPROFILE'):
            return os.path.normpath(environ['USERPROFILE'])
    if environ.get('HOME'):
        return os.path.normpath(environ['HOME'])
    return os.path.normpath(os.path.expanduser('~'))
