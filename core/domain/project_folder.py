# -*- coding: utf-8 -*-
"""
Folder a project's relative paths and default exports point to.

PURE PYTHON module (no QGIS dependency).

``QgsProject.readPath('./')`` has no file to be relative to for an unsaved project and
returns ``'./'`` unchanged, which ``os.path.normpath`` turns into ``'.'``: the working
directory of QGIS (often its install folder), where nothing can be written. The code
compared the normalized value to ``'./'`` (never true), so the Desktop / home fallback
below never ran.
"""
import os
from typing import Mapping, Optional


def project_folder(read_path: str, windows: Optional[bool] = None, environ: Optional[Mapping[str, str]] = None) -> str:
    """Normalized folder of ``read_path`` (the result of ``QgsProject.readPath('./')``).

    An unsaved project (empty, ``'.'`` or ``'./'``) falls back to the Desktop folder on
    Windows and to the home folder elsewhere.
    """
    folder = os.path.normpath(read_path) if read_path else '.'
    if folder != '.':
        return folder
    environ = os.environ if environ is None else environ
    if windows is None:
        windows = os.name == 'nt'
    if windows and environ.get('USERPROFILE'):
        return os.path.normpath(os.path.join(environ['USERPROFILE'], 'Desktop'))
    if environ.get('HOME'):
        return os.path.normpath(environ['HOME'])
    return os.path.normpath(os.path.expanduser('~'))
