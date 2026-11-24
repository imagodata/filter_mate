# -*- coding: utf-8 -*-
"""
The question asked at the opening of a project whose layer settings differ from this computer's (2026-11-24).

The registration of the layers (LayersManagementEngineTask) leaves this computer's value for a setting of the project
that differs from it, and says which (``settings_to_ask``). Here, on the main thread once the registration ended, the
user is asked once for the whole project which groups to take (LayerSettingsDialog); the answer may be remembered for
this project on this computer. A group taken goes to the panel and the SQLite (the project has it already: nothing is
written there, the project stays unmodified); a group kept is left everywhere: the project keeps the settings of the
others, and gets this computer's only when the user changes one in the panel.

Each group is settled once per opening of a project: by the answer of this opening, or by the one remembered for that
group. A difference that comes later (another registration) follows that answer without a question; only a group never
asked is asked, after the question open if one is.

Two steps rather than a question before the task: the registration needs the SQLite, read in the worker, to know
whether anything differs, and a modal question must never wait inside the task or in the middle of its creation.
"""

import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional

try:
    from ..core.domain.project_layer_settings import (
        LAYER_ID_LISTS, answer_decisions, answer_text, asked_groups, merged_asks, present_layers, settings_to_apply,
        without_groups)
    from ..config.config import _get_option_bool
    from ..infrastructure.utils.layer_settings import load
except ImportError:  # loaded outside the plugin package (unit tests: they give ``load`` and ``_get_option_bool``)
    from core.domain.project_layer_settings import (
        LAYER_ID_LISTS, answer_decisions, answer_text, asked_groups, merged_asks, present_layers, settings_to_apply,
        without_groups)
    load = None
    _get_option_bool = None

logger = logging.getLogger('FilterMate.LayerSettingsQuestion')

ANSWERS_GROUP = "FilterMate/layer_settings_answers"  # QgsSettings of this computer, one key per project


def remember_answers_option(config_data: Any) -> bool:
    """APP.OPTIONS.LAYER_SETTINGS.remember_answers (on when absent): off, the remembered answers are forgotten."""
    try:
        option = config_data["APP"]["OPTIONS"]["LAYER_SETTINGS"]["remember_answers"]
    except (KeyError, TypeError):
        return True
    return bool(_get_option_bool(option, True))


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
    """Asks once per project and group, applies the answers, remembers them when asked to."""

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
        self._decided: Dict[str, bool] = {}  # the groups settled in this opening: {group: apply}
        self._scheduled = False
        self._dialog = None
        self.generation = 0  # one per project read or cleared: the registrations of a project of before are left
        self._watched = None
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
            self._watched = project
        except Exception as exc:  # no QGIS project here (some tests)
            logger.debug(f"Layer settings question: project signals not watched: {exc}")

    def teardown(self) -> None:
        """The plugin unloads: no question any more, the project's signals released."""
        self.forget()
        project, self._watched = self._watched, None
        if project is None:
            return
        for signal in (project.cleared, project.readProject):
            try:
                signal.disconnect(self.forget)
            except (TypeError, RuntimeError):  # not connected, or the project is gone
                pass

    # --- Remembered answers ------------------------------------------------------------------------------------------

    @staticmethod
    def _answer_key(key: str) -> str:
        return f"{ANSWERS_GROUP}/{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}"

    def remembered(self, key: str) -> Dict[str, bool]:
        """``{group: apply}`` remembered for the project ``key`` on this computer (a group absent is asked)."""
        if not key:
            return {}
        if not remember_answers_option(self._get_config()):
            self.forget_answers()
            return {}
        return answer_decisions(self._qgs_settings().value(self._answer_key(key), None))

    def remember(self, key: str, decisions: Dict[str, bool]) -> None:
        """Keep the answers given for ``decisions``' groups, with those of the groups asked before."""
        if key and remember_answers_option(self._get_config()):
            kept = dict(self.remembered(key), **decisions)
            self._qgs_settings().setValue(self._answer_key(key), answer_text(kept))

    def forget_answers(self) -> None:
        """Every remembered answer of this computer (the option turned off)."""
        self._qgs_settings().remove(ANSWERS_GROUP)

    # --- The question ------------------------------------------------------------------------------------------------

    def receive(self, asks: Dict, generation: Optional[int] = None) -> None:
        """What a registration found different; settled on the next turn of the event loop.

        Args:
            asks: ``{layer_id: {group: {key: (mine, project's)}}}``.
            generation: :attr:`generation` when the registration was made: a project read or cleared since, they
                belong to another project and are left.
        """
        if not asks or (generation is not None and generation != self.generation):
            return
        self._pending = merged_asks(self._pending, asks)
        if not self._scheduled and self._dialog is None:
            self._scheduled = True
            self._later(self._settle)

    def forget(self, *_args) -> None:
        """Another project: nothing of the project of before is asked nor applied."""
        self.generation += 1
        self._pending, self._decided = {}, {}
        dialog, self._dialog = self._dialog, None
        if dialog is not None:
            try:
                dialog.reject()
                if hasattr(dialog, "deleteLater"):
                    dialog.deleteLater()
            except RuntimeError:  # already deleted
                pass

    def _settle(self) -> None:
        """Apply what an answer of this opening or a remembered one settles; ask about the other groups."""
        self._scheduled = False
        if self._dialog is not None:  # asked after the question open
            return
        groups = asked_groups(self._pending)
        if not groups:
            self._pending = {}
            return
        key = project_key(self._qgs_project())
        known = dict(self.remembered(key), **self._decided)
        settled = {group: known[group] for group in groups if group in known}
        if settled:
            logger.info(f"Layer settings of the project: settled by an answer given before {settled}")
            self._apply(settled)
        unsettled = [group for group in groups if group not in settled]
        if unsettled:
            self._open(unsettled, key)

    def _open(self, groups: List[str], key: str) -> None:
        parent = self._get_dock()
        if parent is None:
            try:
                from qgis.utils import iface
                parent = iface.mainWindow()
            except Exception:  # catch-all safety net: a dialog without parent
                parent = None
        can_remember = remember_answers_option(self._get_config())
        if self._make_dialog is not None:
            dialog = self._make_dialog(groups, can_remember, parent)
        else:
            from ..ui.dialogs.layer_settings_dialog import LayerSettingsDialog
            dialog = LayerSettingsDialog(groups, can_remember, parent)
        self._dialog = dialog
        dialog.finished.connect(lambda _result, dialog=dialog, key=key, groups=groups:
                                self._answered(dialog, key, groups))
        destroyed = getattr(dialog, "destroyed", None)
        if destroyed is not None:  # its parent (the dock) deleted while it was open: no question open any more
            destroyed.connect(lambda *_args, dialog_id=id(dialog): self._gone(dialog_id))
        dialog.open()  # window modal, the event loop goes on (the registration, the panel)

    def _gone(self, dialog_id: int) -> None:
        if self._dialog is not None and id(self._dialog) == dialog_id:
            self._dialog = None

    def _answered(self, dialog: Any, key: str, groups: List[str]) -> None:
        if self._dialog is not dialog:  # another project meanwhile: forget() closed it
            return
        self._dialog = None
        taken = dialog.chosen_groups()
        remembered = dialog.remember()
        if hasattr(dialog, "deleteLater"):
            dialog.deleteLater()
        decisions = {group: group in taken for group in groups}  # only the groups shown are settled
        self._decided.update(decisions)
        if remembered:
            self.remember(key, decisions)
        logger.info(f"Layer settings of the project: {decisions}" + (" (remembered)" if remembered else ""))
        self._apply(decisions)
        if self._pending:  # a group found while the question was open, never asked
            self._scheduled = True
            self._later(self._settle)

    def _apply(self, decisions: Dict[str, bool]) -> Dict:
        """Put the project's settings of the groups applied in the panel and the SQLite; a group kept is left.

        Returns:
            What was applied, ``{layer_id: {group: {key: value}}}``.
        """
        settled = self._pending
        self._pending = without_groups(settled, decisions)
        project = self._qgs_project()
        try:
            layer_ids = set(project.mapLayers().keys())
        except Exception:  # catch-all safety net: the lists of layers as they are
            layer_ids = None
        held = self._get_project_layers() or {}
        chosen = settings_to_apply(settled, [group for group, apply in decisions.items() if apply], held, load,
                                   layer_ids)
        dock = self._get_dock()
        for layer_id, by_group in chosen.items():
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            keys = []
            for group, values in by_group.items():
                held[layer_id].setdefault(group, {}).update(values)
                keys += [(group, key) for key in values]
            # The project's values as stored: the variables hold them already, nothing is written there (the SQLite
            # takes them); then the panel leaves out the layers the project does not have, in memory only
            self._save_variables(layer, keys)
            if layer_ids is not None:
                for group, values in by_group.items():
                    for key in values:
                        if key in LAYER_ID_LISTS:
                            held[layer_id][group][key] = present_layers(held[layer_id][group][key], layer_ids)
            current = getattr(dock, "current_layer", None)
            try:
                if current is not None and current.id() == layer_id:
                    dock.current_layer_changed(layer, manual_change=True)  # the panel shows them
            except RuntimeError:  # the layer of the panel was deleted meanwhile
                pass
        return chosen


__all__ = ['LAYER_ID_LISTS', 'LayerSettingsQuestion', 'project_key', 'remember_answers_option']
