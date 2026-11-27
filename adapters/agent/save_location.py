# -*- coding: utf-8 -*-
"""Suggest one folder for a project and its agent layers; only successful saves remember a choice."""
from __future__ import annotations

import os
import re

LAST_PROJECT_FOLDER = "filter_mate/agent/project_folder"


def _existing_folder(path):
    return os.path.normpath(path) if isinstance(path, str) and os.path.isabs(path) and os.path.isdir(path) else ""


def _local_data_folder(project):
    from qgis.core import QgsApplication, QgsProviderRegistry
    from qgis.PyQt.QtCore import QDir, QUrl

    excluded = [os.path.normcase(os.path.realpath(path))
                for path in (QDir.tempPath(), QgsApplication.qgisSettingsDirPath()) if path]
    folders = set()
    for layer in project.mapLayers().values():
        try:
            parts = QgsProviderRegistry.instance().decodeUri(layer.providerType(), layer.source()) or {}
            path = parts.get("path") or layer.source().split("|", 1)[0]
            if not isinstance(path, str) or path.startswith("/vsi"):
                continue
            if QUrl(path).isLocalFile():
                path = QUrl(path).toLocalFile()
            if not os.path.isabs(path):
                path = project.pathResolver().readPath(path)
            if not os.path.isabs(path) or not os.path.isfile(path):
                continue
            folder = os.path.dirname(os.path.realpath(path))
            normalized = os.path.normcase(folder)
            if any(os.path.commonpath((normalized, root)) == root for root in excluded
                   if os.path.splitdrive(normalized)[0] == os.path.splitdrive(root)[0]):
                continue
            if os.access(folder, os.W_OK):
                folders.add(folder)
        except (ValueError, TypeError, RuntimeError):
            continue  # a provider URI need not describe a local file
    try:
        folder = os.path.commonpath(sorted(folders)) if folders else ""
    except ValueError:  # layers on different Windows drives
        return ""
    return folder if folder and os.path.dirname(folder) != folder and os.access(folder, os.W_OK) else ""


def _project_stem(title):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")[:100].rstrip(" .") or "project"
    if name.lower().endswith((".qgz", ".qgs")):
        name = name[:-4].rstrip(" .") or "project"
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]", name.split(".")[0].rstrip(), re.IGNORECASE):
        name = "project_" + name
    return name


def suggested_project_path(project, layers=()):
    from qgis.core import QgsSettings
    from qgis.PyQt.QtCore import QDir, QStandardPaths

    current = project.fileName()
    if current and os.path.isabs(current) and current.lower().endswith((".qgz", ".qgs")) \
            and _existing_folder(os.path.dirname(current)):
        return os.path.normpath(current)
    folder = (_existing_folder(project.homePath()) or _local_data_folder(project)
              or _existing_folder(QgsSettings().value(LAST_PROJECT_FOLDER, "", type=str))
              or _existing_folder(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
              or QDir.homePath())
    names = sorted((layer.name() for layer in layers if layer.name().strip()), key=str.casefold)
    stem = _project_stem(project.title().strip() or (names[0] if names else "project"))
    path = os.path.join(folder, stem + ".qgz")
    number = 2
    while os.path.lexists(path):
        path = os.path.join(folder, f"{stem}_{number}.qgz")
        number += 1
    return path


def remember_project_folder(path):
    from qgis.core import QgsSettings

    folder = _existing_folder(os.path.dirname(path))
    if folder:
        QgsSettings().setValue(LAST_PROJECT_FOLDER, folder)
