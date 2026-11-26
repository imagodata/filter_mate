# -*- coding: utf-8 -*-
"""Local output navigation, populated from actual successful exports and user-selected save destinations."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from ..widgets.agent_markdown import FileReference

EXPORT_FOLDERS = {'export_layers': 'export', 'export_layout': 'layouts', 'export_chart': 'charts',
                  'export_infographic': 'infographics', 'export_settings_profile': ''}
logger = logging.getLogger('FilterMate.AgentOutputs')


def exported_paths(tool: str, arguments: dict, answer: dict, export_root):
    """Existing output paths under the tool's export folder, without creating or changing anything."""
    if tool not in EXPORT_FOLDERS:
        return []
    from ...filtermate_api.export_root import resolve_export_folder
    root = Path(export_root).resolve()
    subfolder = arguments.get('subfolder') or EXPORT_FOLDERS[tool]
    try:
        folder = resolve_export_folder(root, subfolder) if subfolder else root
    except ValueError:
        return []
    raw = []
    package = answer.get('package')
    if isinstance(package, str) and package:
        raw.append(package)
    if not arguments.get('zip'):
        for key in ('outputs', 'styles'):
            values = answer.get(key)
            if isinstance(values, dict):
                raw.extend(path for path in values.values() if isinstance(path, str))
    for key in ('path', 'file'):
        if isinstance(answer.get(key), str) and answer[key]:
            raw.append(answer[key])
    found = []
    for relative in raw:
        path = (folder / relative).resolve()
        if path != folder and folder not in path.parents:
            continue
        if path.exists() and path not in found:
            found.append(path)
    # Image/SVG layout exports have one file per page; atlas exports already give their output directory.
    count = answer.get('files')
    if tool == 'export_layout' and isinstance(count, int) and 1 < count <= 200 and found and found[0].is_file():
        first = found[0]
        for page in range(2, count + 1):
            path = first.with_name(f'{first.stem}_{page}{first.suffix}')
            if path.is_file() and path not in found:
                found.append(path)
    return found


class AgentOutputsController:
    def __init__(self, host):
        self.host = host
        self._files = {}
        host.panel.thread.file_references = lambda: tuple(self._files.values())
        host.panel.thread.on_file = self.open

    def clear(self):
        self._files.clear()

    def show(self, path: str, name: str = '', *, record: bool = True, restore: bool = False,
             is_dir: bool = False) -> bool:
        if not isinstance(path, str) or not os.path.isabs(path) or path.startswith('/vsimem/'):
            return False
        path = os.path.normpath(path)
        if not restore and not os.path.exists(path):
            return False
        is_dir = os.path.isdir(path) or (restore and is_dir)
        name = name or os.path.basename(path) or path
        aliases = tuple(dict.fromkeys((os.path.basename(path), name.replace('\\', '/'), path.replace('\\', '/'))))
        self._files[path] = FileReference(path, name, is_dir, aliases)
        if not is_dir:
            folder = os.path.dirname(path)
            self._files[folder] = FileReference(folder, os.path.basename(folder) or folder, True)
        self.host.panel.add_output(path, name, is_dir)
        if record:
            # Local paths stay in the local transcript. recap() never sends output entries to the model.
            self.host._record('output', name, detail=path, count='folder' if is_dir else '')
        return True

    def from_result(self, call, result, *, record: bool = True):
        if result.is_error or call.name not in EXPORT_FOLDERS:
            return
        try:
            answer = json.loads(result.content)
        except (ValueError, TypeError):
            return
        if not isinstance(answer, dict):
            return
        from ...filtermate_api.config import _default_export_root
        try:
            root = Path(_default_export_root()).resolve()
            for path in exported_paths(call.name, call.arguments, answer, root):
                self.show(str(path), str(path.relative_to(root)), record=record)
        except (OSError, ValueError, RuntimeError):
            # An export succeeded: a navigation link must never turn its result into a failed tool call.
            logger.debug('An exported output could not be linked', exc_info=True)

    def open(self, path: str):
        from qgis.PyQt.QtCore import QCoreApplication, QUrl
        from qgis.PyQt.QtGui import QDesktopServices
        if path not in self._files:
            return
        if not os.path.exists(path):
            self.host.panel.set_status(QCoreApplication.translate('AgentPanel', 'This output is no longer available: {}')
                                       .format(os.path.basename(path)))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.host.panel.set_status(QCoreApplication.translate('AgentPanel', 'This output could not be opened: {}')
                                       .format(os.path.basename(path)))
