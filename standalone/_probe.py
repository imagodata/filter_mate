# -*- coding: utf-8 -*-
"""Run by a candidate Python: says in one line whether it has PyQGIS, and which.

A file rather than ``python -c``: a path survives the quoting of a Windows ``.bat``.
"""
import json
import sys

try:
    from qgis.core import Qgis
    from qgis.PyQt.QtCore import QT_VERSION_STR
    import qgis.gui  # noqa: F401  the application needs the widgets, not only the core
except Exception as error:  # ImportError, or a library the loader does not find
    print("FM_RUNTIME " + json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"}))
    sys.exit(3)

print("FM_RUNTIME " + json.dumps({
    "ok": True,
    "qgis": Qgis.QGIS_VERSION,
    "qgis_int": int(Qgis.QGIS_VERSION_INT),
    "qt": QT_VERSION_STR,
    "python": "%d.%d.%d" % sys.version_info[:3],
    "executable": sys.executable,
}))
