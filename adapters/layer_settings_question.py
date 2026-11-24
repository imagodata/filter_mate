# -*- coding: utf-8 -*-
"""
The question asked at the opening of a project whose layer settings differ from this computer's (2026-11-24).

The registration of the layers (LayersManagementEngineTask) leaves this computer's value for a setting of the project
that differs from it, and says which (``settings_to_ask``). Here, on the main thread once the registration ended, the
user is asked once for the whole project which groups to take (LayerSettingsDialog); the answer may be remembered for
this project on this computer. A group taken goes to the panel and the SQLite (the project has it already: nothing is
written there, the project stays unmodified); a group kept is left everywhere: the project keeps the settings of the
others, and gets this computer's only when the user changes one in the panel.

Two steps rather than a question before the task: the registration needs the SQLite, read in the worker, to know
whether anything differs, and a modal question must never wait inside the task or in the middle of its creation.
"""

import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional

try:
    from ..core.domain.project_layer_settings import (
        answer_groups, answer_text, asked_groups, merged_asks, settings_to_apply)
    from ..infrastructure.utils.layer_settings import load
except ImportError:  # loaded outside the plugin package (unit tests: they give ``load``)
    from core.domain.project_layer_settings import answer_groups, answer_text, asked_groups, merged_asks, settings_to_apply
    load = None

logger = logging.getLogger('FilterMate.LayerSettingsQuestion')

ANSWERS_GROUP = "FilterMate/layer_settings_answers"  # QgsSettings of this computer, one key per project


def remember_answers_option(config_data: Any) -> bool:
    """APP.OPTIONS.LAYER_SETTINGS.remember_answers (on when absent): off, the remembered answers are forgotten."""
    try:
        option = config_data["APP"]["OPTIONS"]["LAYER_SETTINGS"]["remember_answers"]
    except (KeyError, TypeError):
        return True
    value = option.get("value", True) if isinstance(option, dict) else option
    return bool(value)


def project_key(project: Any) -> str:
    """What names a project on this computer: its file, or its URI for a project stored in a database.

    Not the uuid FilterMate writes into the project (filterMate_db_project_uuid): each computer writes its own there,
    so it changes when another computer saves the project. A project moved is asked about again.
    """
    try:
        return project.fileName() or ""
    except (RuntimeError, AttributeError):
        return ""


class LayerSettingsQuestion:
    """Asks once per project, applies the answer, remembers it when asked to."""

    def __init__(self, get_project_layers: Callable[[], Dict], save_variables: Callable[[Any, List], None],
                 get_dock: Callable[[], Any], get_config: Callable[[], Any], settings: Any = None,
                 project: Any = None, make_dialog: Optional[Callable] = None, schedule: Optional[Callable] = None):
        """Initialize.

        Args:
            get_project_layers: The settings the panel holds (PROJECT_LAYERS).
            save_variables: FilterMateApp.save_variables_from_layer (SQLite and layer variables).
            get_dock: The dock (parent of the dialog, the panel shown again), None without it.
            get_config: CONFIG_DATA.
            settings: QgsSettings (default a new one).
            project: QgsProject (default QgsProject.instance()).
            make_dialog: ``(groups, can_remember, parent) -> dialog`` (default LayerSettingsDialog).
            schedule: ``(callback) -> None`` on the next turn of the event loop (default QTimer.singleShot(0, ...)).
        """
        self._get_project_layers = get_project_layers
        self._save_variables = save_variables
        self._get_dock = get_dock
        self._get_config = get_config
        self._settings = settings
        self._project = project
        self._make_dialog = make_dialog
        self._schedule = schedule
        self._pending: Dict = {}
        self._scheduled = False
        self._dialog = None
        self._watch_project()

    # --- Qt and QGIS -----------------------------------------------------------------------------------------------

    def _qgs_project(self):
        if self._project is not None:
            return self._project
        from qgis.core import QgsProject
        return QgsProject.instance()

    def _qgs_settings(self):
        if self._settings is not None:
            return self._settings
        from qgis.core import QgsSettings
        return QgsSettings()

    def _later(self, callback: Callable) -> None:
        if self._schedule is not None:
            self._schedule(callback)
            return
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, callback)

    def _watch_project(self) -> None:
        """A project cleared or read drops what was found for the project of before (and its open question)."""
        try:
            project = self._qgs_project()
            project.cleared.connect(self.forget)
            project.readProject.connect(self.forget)
        except Exception as exc:  # no QGIS project here (some tests)
            logger.debug(f"Layer settings question: project signals not watched: {exc}")

    # --- Remembered answers ------------------------------------------------------------------------------------------

    @staticmethod
    def _answer_key(key: str) -> str:
        return f"{ANSWERS_GROUP}/{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}"

    def remembered(self, key: str) -> Optional[List[str]]:
        """The groups remembered for the project ``key`` on this computer; None when asked again."""
        if not key:
            return None
        if not remember_answers_option(self._get_config()):
            self.forget_answers()
            return None
        return answer_groups(self._qgs_settings().value(self._answer_key(key), None))

    def remember(self, key: str, groups: List[str]) -> None:
        if key and remember_answers_option(self._get_config()):
            self._qgs_settings().setValue(self._answer_key(key), answer_text(groups))

    def forget_answers(self) -> None:
        """Every remembered answer of this computer (the option turned off)."""
        settings = self._qgs_settings()
        settings.remove(ANSWERS_GROUP)

    # --- The question ------------------------------------------------------------------------------------------------

    def receive(self, asks: Dict) -> None:
        """What a registration found different; asked on the next turn of the event loop, once for all."""
        if not asks:
            return
        self._pending = merged_asks(self._pending, asks)
        if not self._scheduled and self._dialog is None:
            self._scheduled = True
            self._later(self._ask)

    def forget(self, *_args) -> None:
        """Another project: nothing of the project of before is asked nor applied."""
        self._pending = {}
        dialog, self._dialog = self._dialog, None
        if dialog is not None:
            try:
                dialog.reject()
            except RuntimeError:  # already deleted
                pass

    def _ask(self) -> None:
        self._scheduled = False
        groups = asked_groups(self._pending)
        if not groups:
            self._pending = {}
            return
        key = project_key(self._qgs_project())
        remembered = self.remembered(key)
        if remembered is not None:
            logger.info(f"Layer settings of the project: remembered answer {remembered or 'keep mine'}")
            self.apply(remembered)
            return
        dock = self._get_dock()
        parent = dock
        if parent is None:
            try:
                from qgis.utils import iface
                parent = iface.mainWindow()
            except Exception:  # catch-all safety net: a dialog without parent
                parent = None
        if self._make_dialog is not None:
            dialog = self._make_dialog(groups, remember_answers_option(self._get_config()), parent)
        else:
            from ..ui.dialogs.layer_settings_dialog import LayerSettingsDialog
            dialog = LayerSettingsDialog(groups, remember_answers_option(self._get_config()), parent)
        self._dialog = dialog
        dialog.finished.connect(lambda _result, dialog=dialog, key=key: self._answered(dialog, key))
        dialog.open()  # window modal, the event loop goes on (the registration, the panel)

    def _answered(self, dialog: Any, key: str) -> None:
        if self._dialog is not dialog:  # another project meanwhile: forget() closed it
            return
        self._dialog = None
        groups = dialog.chosen_groups()
        if dialog.remember():
            self.remember(key, groups)
        logger.info(f"Layer settings of the project: {groups or 'keep mine'}"
                    + (" (remembered)" if dialog.remember() else ""))
        self.apply(groups)

    def apply(self, groups: List[str]) -> Dict:
        """Put the project's settings of ``groups`` in the panel and the SQLite; the rest is left as it is.

        Returns:
            What was applied, ``{layer_id: {group: {key: value}}}``.
        """
        pending, self._pending = self._pending, {}
        held = self._get_project_layers() or {}
        chosen = settings_to_apply(pending, groups, held, load)
        project = self._qgs_project()
        dock = self._get_dock()
        for layer_id, by_group in chosen.items():
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            keys = []
            for group, values in by_group.items():
                held[layer_id].setdefault(group, {}).update(values)
                keys += [(group, key) for key in values]
            self._save_variables(layer, keys)  # the variables hold these values already: nothing written there
            current = getattr(dock, "current_layer", None)
            try:
                if current is not None and current.id() == layer_id:
                    dock.current_layer_changed(layer, manual_change=True)  # the panel shows them
            except RuntimeError:  # the layer of the panel was deleted meanwhile
                pass
        return chosen
