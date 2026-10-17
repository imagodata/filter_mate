# -*- coding: utf-8 -*-
"""Names under which the FilterMate plugin package is imported in this process.

Inside QGIS the API is ``<plugin folder>.filtermate_api`` (the folder is not always ``filter_mate``:
a GitHub zip gives ``filter_mate-main``); launched by uvicorn it is the top-level ``filtermate_api``,
and the plugin, if QGIS imported it, sits in ``sys.modules`` under its own folder name.
"""
import sys
from typing import List


def plugin_package_names() -> List[str]:
    """Candidate root packages of the plugin, most certain first (empty when it is not imported)."""
    names: List[str] = []
    if __package__ and "." in __package__:
        names.append(__package__.rsplit(".", 1)[0])
    for module_name in list(sys.modules):
        root, dot, rest = module_name.partition(".")
        if dot and rest == "filtermate_api" and root not in names:
            names.append(root)
    return names
