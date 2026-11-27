# -*- coding: utf-8 -*-
"""The user's choice to keep agent geodata, independent of model permissions and autonomy."""
from __future__ import annotations

import logging
import os

from ...adapters.agent import data_store
from ...adapters.agent.save_location import remember_project_folder, suggested_project_path

logger = logging.getLogger("FilterMate.AgentData")


def _tr(text):
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("AgentData", text)


class AgentDataController:
    def __init__(self, host):
        from qgis.core import QgsProject
        self.host = host
        self.project = QgsProject.instance()
        self._offered = set()
        self._saving = False
        self._unsaved = False
        self._generation = 0
        self._connections = []
        for name, slot in (("writeProject", self._before_write), ("projectSaved", self._after_write),
                           ("cleared", self._reset)):
            signal = getattr(self.project, name, None)
            if signal is not None:
                signal.connect(slot)
                self._connections.append((signal, slot))

    def close(self):
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._connections.clear()
        # The panel unloading must not remove data still read by the open project.

    def _reset(self, *_):
        self._generation += 1
        self._offered.clear()
        self._unsaved = False

    def offer(self):
        layers = data_store.pending_layers(self.project)
        new = {(layer.id(), layer.source()) for layer in layers} - self._offered
        if not new:
            return
        self._offered.update(new)
        texts = {"chip": _tr("Data"), "heading": _tr("Keep this work?"),
                 "yes": _tr("Save project and layers…"), "no": _tr("Continue in memory"),
                 "allowed": _tr("Choose where to save the project and its layers."),
                 "refused": _tr("The data stay in memory until this project is closed."),
                 "layers": [layer.name() for layer in layers[:5]]}
        path = suggested_project_path(self.project, layers)
        description = _tr(
            "Downloaded data and results are held in memory. Save the project together with its layers to "
            "keep them after closing QGIS.")
        description += "\n\n" + _tr("Suggested project: {}").format(path)
        description += "\n" + _tr("Project and layers folder: {}").format(os.path.dirname(path))
        card = self.host.panel.add_confirm_card(texts, description, False)
        generation = self._generation
        card.answered.connect(lambda answer: self.save() if answer == "once" and generation == self._generation
                              else None)

    def save(self):
        from qgis.PyQt.QtWidgets import QFileDialog
        if self._busy():
            self.host.panel.set_status(_tr("Wait for the current request to finish before saving its data."))
            return False
        path, _ = QFileDialog.getSaveFileName(
            self.host.panel, _tr("Save project and layers"),
            suggested_project_path(self.project, data_store.pending_layers(self.project)),
            _tr("QGIS project (*.qgz *.qgs)"))
        if not path:
            return False
        if not path.lower().endswith((".qgz", ".qgs")):
            path += ".qgz"
        self._saving = True
        self._unsaved = False
        try:
            folder = data_store.persist(self.project, path)
        except Exception as exc:
            logger.exception("The project and agent data could not be saved")
            self.host.panel.show_error(_tr("The project and its layers could not be saved."), str(exc), False)
            return False
        finally:
            self._saving = False
        remember_project_folder(path)
        self.host.panel.add_note(_tr("Project and layers saved: {}").format(path))
        outputs = getattr(self.host, '_outputs', None)
        if outputs is not None:
            outputs.show(path)
            if folder:
                outputs.show(folder, _tr('Project data'))
            self.host._save_transcript()
        return True

    def _busy(self):
        bridge = getattr(self.host, '_mcp', None)
        checkpoint = getattr(self.host, '_checkpoint', None)
        return self.host.chat_busy() or (bridge is not None and bridge.busy) or \
            (checkpoint is not None and bool(checkpoint.busy()))

    def _before_write(self, document):
        """Native QGIS Save also offers to make transient data durable before its XML goes to disk."""
        from qgis.PyQt.QtWidgets import QMessageBox
        if self._saving or not data_store.pending_layers(self.project):
            return
        path = self.project.fileName()
        if not path or not path.lower().endswith((".qgz", ".qgs")):
            return
        self._unsaved = True
        if self._busy():
            return  # never rebind providers while a tool is using them
        answer = QMessageBox.question(self.host.panel, _tr("Save project and layers"), _tr(
            "Save the downloaded data and results beside this project?\n{}\n\n"
            "If you choose No, these data stay in memory and will be lost when the project closes.").format(path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._saving = True
        try:
            data_store.persist(self.project, path, write_project=False)
            # QGIS already assembled the XML. Replace layer elements with their new durable sources and state.
            from qgis.core import QgsReadWriteContext
            context = QgsReadWriteContext()
            context.setPathResolver(self.project.pathResolver())
            nodes = document.elementsByTagName("maplayer")
            for index in range(nodes.count()):
                element = nodes.at(index).toElement()
                layer = self.project.mapLayer(element.firstChildElement("id").text())
                if layer is not None and layer.customProperty(data_store.PERSISTENT_PROPERTY, False):
                    replacement = document.createElement("maplayer")
                    layer.writeLayerXml(replacement, document, context)
                    from ...adapters.qgis.coverage_layers.snapshots import registry
                    registry()._on_write_map_layer(lambda: self.project, layer, replacement, document)
                    from ...adapters.qgis.stream_copy import rewrite_saved_layer
                    rewrite_saved_layer(self.project, layer, replacement, document)
                    element.parentNode().replaceChild(replacement, element)
                    # QGIS also stores sources on nodes of the layer tree.
                    tree = document.elementsByTagName("layer-tree-layer")
                    for rank in range(tree.count()):
                        node = tree.at(rank).toElement()
                        if node.attribute("id") == layer.id():
                            node.setAttribute("source", replacement.firstChildElement("datasource").text())
            self._unsaved = False
        except Exception as exc:
            logger.exception("Agent data were not made durable during QGIS Save")
            QMessageBox.warning(self.host.panel, _tr("Data still in memory"), str(exc))
        finally:
            self._saving = False

    def _after_write(self, *_):
        if self._unsaved:
            from qgis.PyQt.QtCore import QTimer
            generation = self._generation
            QTimer.singleShot(0, lambda: self.project.setDirty(True) if generation == self._generation else None)
        elif not self._saving:
            remember_project_folder(self.project.fileName())
