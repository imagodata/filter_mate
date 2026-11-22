# -*- coding: utf-8 -*-
"""The local copy of a web service layer, as the user starts it: the button of the dock, the menu of the layers of
QGIS, EXPORTING and the agent all come here (2026-11-22).

One click: the copy is planned over the visible map (``adapters/qgis/stream_copy.plan_copy``), its cost is shown
before it starts (pixels, requests, size; or the most features), it runs in a background task the user can cancel,
and the layer reads its copy once it is written. A layer on its copy offers to go back to its service, or to copy
the same area again.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from qgis.PyQt.QtCore import QCoreApplication

logger = logging.getLogger(__name__)

_INSTANCE: List[Optional['StreamCopyActions']] = [None]


def get() -> Optional['StreamCopyActions']:
    """The actions of the running plugin; None before ``initGui`` or after ``unload``."""
    return _INSTANCE[0]


def _tr(text: str) -> str:
    return QCoreApplication.translate('StreamCopyActions', text)


def _feedback():
    from ...infrastructure.feedback import show_info, show_success, show_warning
    return show_info, show_success, show_warning


class StreamCopyActions:
    """Start, finish and undo local copies; one per plugin (no Qt object: the slots are plain callables)."""

    def __init__(self, iface, ask: Optional[Callable[[str, str, List[str]], int]] = None):
        self.iface = iface
        self._ask = ask or self._ask_with_box
        self._tasks: Dict[str, object] = {}  # layer id -> copy under way
        self._action = None
        self._listeners: List[Callable[[str], None]] = []  # told the id of a layer whose copy state changed
        self._marks: Dict[str, tuple] = {}  # layer id -> (node of the layer tree, indicator shown on it)

    # --- lifecycle --------------------------------------------------------------------------------------------

    def start(self) -> None:
        from ...adapters.qgis import stream_copy
        _INSTANCE[0] = self
        stream_copy.install()
        self._add_layer_menu_action()
        try:  # the plugin loaded again (an update, a reload): the layers it put back on their service read their copy
            stream_copy.reattach_project()
        except Exception as exc:
            logger.debug(f"FilterMate local copies not read again at start: {exc}")
        from qgis.core import QgsProject
        project = QgsProject.instance()
        # After the copies are found again (readProject of stream_copy runs first: connected before), and when a
        # layer comes in (a copy duplicated, a layer definition pasted).
        project.readProject.connect(self._refresh_marks_later)
        project.layersAdded.connect(self._refresh_marks_later)
        # A node moved or grouped is a new node of the layer tree, without the mark of the old one; and the old one
        # goes after the new one came (the dock may let the events run between the two: a refresh then marks the
        # old node, which is removed just after).
        root = project.layerTreeRoot()
        root.addedChildren.connect(self._refresh_marks_later)
        root.removedChildren.connect(self._refresh_marks_later)
        # Change Data Source of QGIS, Unfilter putting a web map back on its service: the mark follows the source.
        self._watched: Dict[str, object] = {}
        project.layersAdded.connect(self._watch_layers)
        self._watch_layers(project.mapLayers().values())
        self._stopped = False
        self.refresh_marks()

    def stop(self) -> None:
        """The copies under way end; the layers on their copy read their service, their record kept: a project
        written meanwhile, with FilterMate off, holds the service, and the copy is read again when it starts."""
        from qgis.core import QgsProject
        from ...adapters.qgis import stream_copy
        project = QgsProject.instance()
        for layer_id, task in list(self._tasks.items()):
            try:
                task.callback = None
                task.cancel()
            except RuntimeError:
                pass
            restore, layer = getattr(task, 'restore', None), project.mapLayer(layer_id)
            if restore is not None and layer is not None:  # Copy again cut short: the previous copy, read again
                stream_copy.back_to(layer, restore)
        self._tasks.clear()
        for layer in list(project.mapLayers().values()):
            try:
                record = stream_copy.record_of(layer)
                if record is not None:
                    # Its filter now, in the record that brings the copy back when FilterMate starts again.
                    current = layer.subsetString() if hasattr(layer, 'subsetString') else ''
                    layer.setCustomProperty(stream_copy.rules.PROPERTY, record.replaced(subset=current).to_json())
                    stream_copy.switch_to_stream(layer, keep_record=True)
            except Exception as exc:  # edits under way, a filter of another layer: it stays on its copy
                logger.info(f"FilterMate local copy of a layer left as it is at unload: {exc}")
        self._remove_layer_menu_action()
        self._stopped = True  # a refresh already queued does nothing
        root = project.layerTreeRoot()
        for signal in (project.readProject, project.layersAdded, root.addedChildren, root.removedChildren):
            try:
                signal.disconnect(self._refresh_marks_later)
            except (TypeError, RuntimeError):
                pass
        try:
            project.layersAdded.disconnect(self._watch_layers)
        except (TypeError, RuntimeError):
            pass
        for layer in list(getattr(self, '_watched', {}).values()):
            try:
                layer.dataSourceChanged.disconnect(self._refresh_marks_later)
            except (TypeError, RuntimeError, AttributeError):
                pass  # removed with its layer
        self._watched = {}
        self._clear_marks()
        stream_copy.uninstall()
        if _INSTANCE[0] is self:
            _INSTANCE[0] = None
        self._listeners.clear()

    def on_change(self, listener: Callable[[str], None]) -> None:
        """``listener(layer_id)`` when a copy starts, ends or is undone (the dock redraws its button)."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _changed(self, layer_id: str) -> None:
        self.refresh_marks()
        for listener in list(self._listeners):
            try:
                listener(layer_id)
            except Exception as exc:
                logger.debug(f"FilterMate local copy listener failed: {exc}")

    # --- the mark in the layer tree ----------------------------------------------------------------------------

    def _watch_layers(self, layers) -> None:
        """Refresh the marks when the source of a layer changes (once per layer)."""
        watched = getattr(self, '_watched', None)
        if watched is None:
            return
        for layer in layers or ():
            try:
                layer_id = layer.id()
                if layer_id in watched or not hasattr(layer, 'dataSourceChanged'):
                    continue
                layer.dataSourceChanged.connect(self._refresh_marks_later)
                watched[layer_id] = layer
            except (RuntimeError, TypeError):
                continue
        for layer_id, layer in list(watched.items()):  # those removed since: not held
            try:
                layer.id()
            except RuntimeError:
                watched.pop(layer_id, None)

    def _refresh_marks_later(self, *_args) -> None:
        try:
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(0, self.refresh_marks)
        except Exception:
            self.refresh_marks()

    def refresh_marks(self) -> None:
        """An indicator on every layer that reads its local copy, in the layer tree of QGIS: the icon of the copy, its
        date and state in its tooltip (a copy is never taken for the live service). Others lose theirs."""
        view = self._tree_view()
        if view is None or getattr(self, '_stopped', False):
            return
        from qgis.core import QgsProject
        from ...adapters.qgis import stream_copy
        try:
            from qgis.gui import QgsLayerTreeViewIndicator
        except ImportError:  # no layer tree view to mark
            return
        self._clear_marks(view)
        root = QgsProject.instance().layerTreeRoot()
        for layer in list(QgsProject.instance().mapLayers().values()):
            try:
                record = stream_copy.record_of(layer)
                node = root.findLayer(layer.id()) if record is not None else None
            except RuntimeError:
                continue
            if node is None:
                continue
            try:
                indicator = QgsLayerTreeViewIndicator(view)
                indicator.setIcon(_mark_icon())
                indicator.setToolTip(_tr("{0}. FilterMate reads this file in place of the web service: click the copy "
                                         "button of EXPLORING, or the menu of the layer, to go back.").format(
                    stream_copy.copy_text(record)))
                view.addIndicator(node, indicator)
                self._marks[layer.id()] = (node, indicator)
            except Exception as exc:  # one layer without its mark: the others keep theirs, the copy works the same
                logger.debug(f"FilterMate local copy mark not shown: {exc}")
                continue

    def _clear_marks(self, view=None) -> None:
        view = view or self._tree_view()
        for node, indicator in list(self._marks.values()):
            try:
                if view is not None:
                    view.removeIndicator(node, indicator)
            except (RuntimeError, AttributeError, TypeError):
                pass  # the node went with its layer
            try:
                indicator.deleteLater()  # a child of the view: removeIndicator does not delete it
            except (RuntimeError, AttributeError):
                pass
        self._marks.clear()

    def _tree_view(self):
        try:
            return self.iface.layerTreeView() if self.iface is not None else None
        except (AttributeError, RuntimeError):
            return None

    def mark_of(self, layer_id: str):
        """The indicator shown on a layer that reads its copy; None for another (checks)."""
        entry = self._marks.get(layer_id)
        return entry[1] if entry is not None else None

    # --- what a layer offers ------------------------------------------------------------------------------------

    def state_of(self, layer) -> str:
        """``copying``, ``copy`` (on its copy), ``stream`` (a service that can be copied) or "" (nothing to offer)."""
        from ...adapters.qgis import stream_copy
        if layer is None:
            return ''
        try:
            layer_id = layer.id()
        except RuntimeError:
            return ''
        if layer_id in self._tasks:
            return 'copying'
        if stream_copy.is_local_copy(layer):
            return 'copy'
        return 'stream' if stream_copy.can_copy(layer) else ''

    def tooltip_for(self, layer) -> str:
        from ...adapters.qgis import stream_copy
        state = self.state_of(layer)
        if state == 'copying':
            return _tr("Local copy under way: click to cancel it")
        if state == 'copy':
            record = stream_copy.record_of(layer)
            return _tr("{0}. Click to go back to the service or to copy the visible map again").format(
                stream_copy.copy_text(record)) if record is not None else ''
        if state == 'stream':
            return _tr("Local copy: keep what this web service shows over the visible map in a file of this "
                       "computer, and read the layer from it (faster, and without network)")
        return ''

    # --- one click ------------------------------------------------------------------------------------------------

    def trigger(self, layer) -> None:
        """What the button and the menu do: copy, cancel the copy under way, or offer the way back."""
        state = self.state_of(layer)
        if state == 'copying':
            task = self._tasks.get(layer.id())
            if task is not None:
                task.cancel()
        elif state == 'copy':
            self._offer_way_back(layer)
        elif state == 'stream':
            self.copy(layer)
        else:
            _feedback()[2](_tr("Only a layer of a web service (WFS, WMS, WMTS, XYZ tiles...) can be copied."))

    def copy(self, layer, confirm: bool = True, plan=None, on_done: Optional[Callable[[object], None]] = None,
             restore=None) -> str:
        """Plan the copy of ``layer`` over the visible map, say its cost, start it; returns the refusal or "".

        ``restore``: the copy the layer read before (Copy again), read again when this one is not made.
        """
        from ...adapters.qgis import stream_copy
        show_info, _show_success, show_warning = _feedback()

        def give_back(said: str) -> str:
            if restore is not None:
                stream_copy.back_to(layer, restore)
                self._changed(layer.id())
            return said

        if layer.id() in self._tasks:  # one copy of a layer at a time (the agent and the button alike)
            refusal = _tr("{0} is being copied already.").format(layer.name())
            show_warning(refusal)
            return refusal
        plan = plan or stream_copy.plan_copy(layer)
        if plan.refusal:
            show_warning(plan.refusal)
            return give_back(plan.refusal)
        if confirm:
            choice = self._ask(_tr("Local copy of {0}").format(layer.name()), plan.summary(), [_tr("Copy"), _tr("Cancel")])
            if choice != 0:
                return give_back(_tr("canceled"))
        from qgis.core import QgsApplication
        task = stream_copy.StreamCopyTask(plan, layer, lambda done: self._finished(done, on_done))
        task.restore = restore
        self._tasks[layer.id()] = task
        QgsApplication.taskManager().addTask(task)
        show_info(_tr("Copying {0} over the visible map… (cancel it from the button or the task bar)").format(
            layer.name()))
        self._changed(layer.id())
        return ''

    def _finished(self, task, on_done=None) -> None:
        from qgis.core import QgsProject
        from ...adapters.qgis import stream_copy
        _show_info, show_success, show_warning = _feedback()
        layer_id = task.plan.layer_id
        self._tasks.pop(layer_id, None)
        layer = QgsProject.instance().mapLayer(layer_id)
        result = task.result
        restore = getattr(task, 'restore', None)
        try:
            if layer is not None and not self._still_the_service(layer, task.plan):
                # Filtered by another layer, or its source changed, meanwhile: the copy no longer fits it.
                stream_copy.discard(result.record)
                show_warning(_tr("{0} changed during its copy (a filter of another layer, another source): the copy "
                                 "is not used. Copy it again.").format(layer.name()))
                return
            if result.record is None:
                if layer is not None and restore is not None:
                    stream_copy.back_to(layer, restore)
                show_warning(_tr("{0} was not copied: {1}.").format(task.plan.layer_name, result.error.rstrip('.'))
                             + (' ' + _tr("It reads its previous copy.") if restore is not None and layer is not None
                                else ''))
                return
            if layer is None:
                show_warning(_tr("{0} was removed during its copy: the file is kept in {1}.").format(
                    task.plan.layer_name, task.plan.folder))
                return
            try:
                notes = stream_copy.switch_to_copy(layer, result.record)
            except RuntimeError as exc:
                stream_copy.discard(result.record)
                if restore is not None:
                    stream_copy.back_to(layer, restore)
                show_warning(str(exc))
                return
            if restore is not None:
                stream_copy.discard(restore)  # replaced by the new copy: FilterMate's own file, not kept twice
            text = _tr("{0} now reads its local copy ({1}).").format(layer.name(), stream_copy.copy_text(result.record))
            if notes:
                show_warning(text + ' ' + ' '.join(notes))
            else:
                show_success(text)
        finally:
            self._changed(layer_id)
            if on_done is not None:
                try:
                    on_done(task)
                except Exception:
                    logger.exception("FilterMate local copy: on_done failed")

    @staticmethod
    def _still_the_service(layer, plan) -> bool:
        """Whether ``layer`` is still the service the copy was planned on (main thread, at its end)."""
        from ...adapters.qgis.coverage_layers.snapshots import registry
        try:
            return (not registry().is_derived(layer.id())
                    and layer.providerType().lower() == (plan.provider or '').lower())
        except RuntimeError:
            return False

    def back_to_stream(self, layer) -> bool:
        from ...adapters.qgis import stream_copy
        _show_info, show_success, show_warning = _feedback()
        try:
            notes = stream_copy.switch_to_stream(layer)
        except RuntimeError as exc:
            show_warning(str(exc))
            return False
        text = _tr("{0} reads its service again. Its copy is still in the folder of the copies.").format(layer.name())
        (show_warning if notes else show_success)(' '.join([text] + notes))
        self._changed(layer.id())
        return True

    def copy_again(self, layer) -> str:
        """A new copy of the area of the current one: the layer goes back to its service, then is copied; when the
        new copy is not made (cancelled, refused, failed) it reads its previous copy again."""
        from ...adapters.qgis import stream_copy
        try:
            plan, previous = stream_copy.recopy_plan(layer)
        except RuntimeError as exc:
            _feedback()[2](str(exc))
            return str(exc)
        if plan.refusal:  # recopy_plan put the layer back on its copy
            _feedback()[2](plan.refusal)
            self._changed(layer.id())
            return plan.refusal
        self._changed(layer.id())
        return self.copy(layer, plan=plan, restore=previous)

    def _offer_way_back(self, layer) -> None:
        from ...adapters.qgis import stream_copy
        record = stream_copy.record_of(layer)
        text = (stream_copy.copy_text(record) + '.\n\n' + _tr("The copy covers the area of the map when it was made. "
                                                              "Copy again reads the same area anew."))
        choice = self._ask(layer.name(), text, [_tr("Back to the service"), _tr("Copy again"), _tr("Cancel")])
        if choice == 0:
            self.back_to_stream(layer)
        elif choice == 1:
            self.copy_again(layer)

    def _ask_with_box(self, title: str, text: str, buttons: List[str]) -> int:
        """The index of the button pressed; the last one (Cancel) when the box is closed."""
        from qgis.PyQt.QtWidgets import QMessageBox
        parent = self.iface.mainWindow() if self.iface is not None else None
        box = QMessageBox(parent)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Question)
        made = [box.addButton(label, QMessageBox.ButtonRole.AcceptRole if index == 0 else (
            QMessageBox.ButtonRole.RejectRole if index == len(buttons) - 1 else QMessageBox.ButtonRole.ActionRole))
            for index, label in enumerate(buttons)]
        box.setDefaultButton(made[0])
        box.setEscapeButton(made[-1])
        box.exec()
        clicked = box.clickedButton()
        return made.index(clicked) if clicked in made else len(buttons) - 1

    # --- the menu of the layers of QGIS ------------------------------------------------------------------------

    def _add_layer_menu_action(self) -> None:
        """One entry in the menu of the layers of QGIS, on the layers of web services only; its text follows the
        layer it is shown for."""
        if self.iface is None or not hasattr(self.iface, 'addCustomActionForLayerType'):
            return
        from qgis.core import QgsProject
        try:
            from qgis.PyQt.QtGui import QAction
        except ImportError:  # QGIS < 3.34.2 (Qt5): QAction is in QtWidgets
            from qgis.PyQt.QtWidgets import QAction
        self._action = QAction(_tr("FilterMate: local copy of the visible map"), self.iface.mainWindow())
        self._action.triggered.connect(self._on_layer_menu)
        for layer_type in _layer_types():
            self.iface.addCustomActionForLayerType(self._action, '', layer_type, False)
        project = QgsProject.instance()
        self._register_layers(project.mapLayers().values())
        project.layersAdded.connect(self._register_layers)
        try:
            self.iface.layerTreeView().currentLayerChanged.connect(self._update_layer_menu_text)
        except (AttributeError, RuntimeError):
            pass

    def _remove_layer_menu_action(self) -> None:
        if self._action is None:
            return
        from qgis.core import QgsProject
        for signal, slot in ((QgsProject.instance().layersAdded, self._register_layers),):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        try:
            self.iface.layerTreeView().currentLayerChanged.disconnect(self._update_layer_menu_text)
        except (AttributeError, TypeError, RuntimeError):
            pass
        try:
            self.iface.removeCustomActionForLayerType(self._action)
        except (AttributeError, RuntimeError):
            pass
        self._action.deleteLater()
        self._action = None

    def _register_layers(self, layers) -> None:
        from ...adapters.qgis import stream_copy
        if self._action is None:
            return
        for layer in layers or ():
            try:
                if stream_copy.can_copy(layer) or stream_copy.is_local_copy(layer) or _was_a_stream(layer):
                    self.iface.addCustomActionForLayer(self._action, layer)
            except RuntimeError:
                continue

    def _update_layer_menu_text(self, layer) -> None:
        if self._action is None:
            return
        state = self.state_of(layer)
        self._action.setText({
            'copying': _tr("FilterMate: cancel the local copy"),
            'copy': _tr("FilterMate: local copy (back to the service, copy again)"),
        }.get(state, _tr("FilterMate: local copy of the visible map")))

    def _on_layer_menu(self) -> None:
        try:
            layer = self.iface.layerTreeView().currentLayer()
        except (AttributeError, RuntimeError):
            layer = None
        if layer is not None:
            self.trigger(layer)


_MARK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
             'stroke="#2f7d6d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M12 3v11M7.5 9.5L12 14l4.5-4.5"/><path d="M4 15v4.5h16V15"/></svg>')
_ICON = []


def _mark_icon():
    """The icon of the copy (the tray of the button of the rail), drawn once."""
    if not _ICON:
        from qgis.PyQt.QtCore import QByteArray, Qt
        from qgis.PyQt.QtGui import QIcon, QPainter, QPixmap
        from qgis.PyQt.QtSvg import QSvgRenderer
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        QSvgRenderer(QByteArray(_MARK_SVG.encode('utf-8'))).render(painter)
        painter.end()
        _ICON.append(QIcon(pixmap))
    return _ICON[0]


def _was_a_stream(layer) -> bool:
    """A layer whose record names a service (its copy is found again just after it is added)."""
    from ...core.domain.stream_copy import PROPERTY, copy_kind, LocalCopy
    try:
        record = LocalCopy.from_json(layer.customProperty(PROPERTY))
    except RuntimeError:
        return False
    return record is not None and bool(copy_kind(record.stream_provider))


def _layer_types():
    try:
        from qgis.core import Qgis
        return (Qgis.LayerType.Vector, Qgis.LayerType.Raster)
    except AttributeError:  # before QGIS 3.30
        from qgis.core import QgsMapLayerType
        return (QgsMapLayerType.VectorLayer, QgsMapLayerType.RasterLayer)
