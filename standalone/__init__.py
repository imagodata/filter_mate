# -*- coding: utf-8 -*-
"""FilterMate outside the QGIS application.

The dock of the plugin, unchanged, in a window of its own: a map, a layer panel, the QGIS
libraries as the engine. Nothing here is loaded by the plugin inside QGIS, and the plugin
zip does not ship this package.

Two halves, kept apart on purpose:

* ``cli``, ``runtime``, ``provision``, ``paths``: the launcher. Standard library only, so
  it runs in any Python, finds a Python that has PyQGIS (or installs one) and starts the
  host there.
* ``host``: the application itself. Imports ``qgis``; only ever imported by a Python that
  has it.
"""

import os

PACKAGE = "filter_mate"
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def version() -> str:
    """The version of FilterMate, read from ``metadata.txt`` ("" when unreadable)."""
    try:
        with open(os.path.join(PACKAGE_DIR, "metadata.txt"), encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""
