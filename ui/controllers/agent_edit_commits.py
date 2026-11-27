"""User-confirmed commits after agent buffer edits; never callable by the model."""
from __future__ import annotations

import logging

logger = logging.getLogger('FilterMate.AgentEditCommits')


def _tr(text):
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate('AgentEditCommits', text)


def _scope(project, layer):
    """All layers a native commit can affect, including transaction-group companions."""
    from qgis.core import Qgis
    if not hasattr(project, 'transactionMode'):
        # QGIS < 3.26 has no buffered groups. Automatic provider transactions still share their group.
        transaction = layer.dataProvider().transaction()
        if transaction is None:
            return (layer,)
        connection = getattr(transaction, 'connectionString', None)
        if connection is None:
            raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
        group = project.transactionGroup(layer.providerType(), connection())
        if group is None:
            raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
        members = tuple(sorted((item for item in group.layers() if item.isEditable()), key=lambda item: item.id()))
        if layer not in members:
            raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
        return members
    mode = project.transactionMode()
    if mode == Qgis.TransactionMode.BufferedGroups:
        group = project.editBufferGroup()
    elif mode == Qgis.TransactionMode.AutomaticGroups:
        transaction = layer.dataProvider().transaction()
        if transaction is None:
            return (layer,)
        group = project.transactionGroup(layer.providerType(), transaction.connectionString())
        if group is None:
            raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
    elif mode == Qgis.TransactionMode.Disabled:
        return (layer,)
    else:
        raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
    if group is None:
        raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
    members = tuple(sorted((item for item in group.layers() if item.isEditable()), key=lambda item: item.id()))
    if layer not in members:
        raise ValueError(_tr('The transaction group could not be verified. Use QGIS to save these edits.'))
    return members


def _state(project, layers):
    """A cheap revision check, complemented by layer signals while the confirmation is visible."""
    mode = project.transactionMode() if hasattr(project, 'transactionMode') else project.autoTransaction()
    rows = tuple((item.id(), item.source(), item.isEditable(), item.isModified(),
                  item.undoStack().index(), item.undoStack().count()) for item in layers)
    return mode, rows


class LayerEditCommits:
    def __init__(self, host, project, busy):
        self.host, self.project, self.busy = host, project, busy
        self._tickets = {}
        self._epoch = 0

    def close(self):
        self._epoch += 1
        for cancel in list(self._tickets.values()):
            cancel()

    def offer(self, edits):
        for layer_id, after in edits:
            layer = self.project.mapLayer(layer_id)
            if layer is None or not layer.isEditable() or not layer.isModified() or layer.undoStack().index() != after:
                continue
            try:
                layers = _scope(self.project, layer)
                key = tuple(item.id() for item in layers)
                if key in self._tickets:
                    continue
                self._offer(layer, layers, key)
            except (RuntimeError, ValueError) as exc:
                self.host.panel.show_error(_tr('Layer edits are still pending.'), str(exc), False)

    def _offer(self, layer, layers, key):
        state = _state(self.project, layers)
        generation = getattr(self.host, '_memory_generation', None)
        epoch = self._epoch
        texts = {'chip': _tr('Layer edits'), 'heading': _tr('Save the layer edits?'),
                 'yes': _tr('Save layer edits'), 'no': _tr('Keep pending'),
                 'allowed': _tr('Checking and saving the layer edits…'),
                 'refused': _tr('Edits remain pending unless saved or discarded in QGIS. A new edit needs a new confirmation.'),
                 'layers': [item.name() for item in layers],
                 'reversibility': _tr('Saved edits can no longer be undone from the agent chat.')}
        description = _tr('Save all pending changes to the data source, including any manual edits on the listed layers?')
        if len(layers) > 1:
            description += '\n\n' + _tr('These layers share a QGIS transaction. They are saved together.')
        if any(item.providerType() == 'memory' for item in layers):
            description += '\n\n' + _tr('A memory layer stays in memory after saving its edits. Save project and layers to keep it after closing QGIS.')
        card = self.host.panel.add_confirm_card(texts, description, False)
        connections, active = [], [True]

        def release(*_):
            if not active[0]:
                return False
            active[0] = False
            self._tickets.pop(key, None)
            for signal, slot in connections:
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
            connections.clear()
            return True

        def cancel(*_):
            if release():
                try:
                    card.finish('no')
                except RuntimeError:
                    pass

        def answered(answer):
            if not release() or answer != 'once':
                return
            try:
                if generation != getattr(self.host, '_memory_generation', None) or self.busy():
                    raise ValueError(_tr('The conversation changed or a request is running. Ask for a new confirmation.'))
                if any(self.project.mapLayer(item.id()) is not item for item in layers) or \
                        tuple(item.id() for item in _scope(self.project, layer)) != key or _state(self.project, layers) != state:
                    raise ValueError(_tr('The layers changed since this confirmation. Review them and ask again.'))
                from ...adapters.agent.protected_layers import read_ids
                if set(key) & set(read_ids(self.project, strict=True)):
                    raise ValueError(_tr('A listed layer is protected from the agent. Save its edits directly in QGIS.'))
                from ..cursors import CursorLease
                with self.host.panel.hold_queued(), CursorLease([self.host.panel]):
                    # project.commitChanges handles BufferedGroups as one native transaction.
                    # Older QGIS versions without grouped buffering commit the individual layer.
                    commit = getattr(self.project, 'commitChanges', None)
                    if commit is not None:
                        success, errors = commit(True, layer)
                    else:
                        success, errors = layer.commitChanges(), layer.commitErrors()
                if not success:
                    raise ValueError('\n'.join(str(error) for error in errors) or _tr('QGIS refused to save the edits.'))
            except (RuntimeError, ValueError) as exc:
                # A provider may already have completed some commit stages. Never roll back automatically.
                if epoch != self._epoch or generation != getattr(self.host, '_memory_generation', None):
                    return
                message = _tr('The layer edits were not fully saved. Review their state in QGIS.')
                try:
                    card.result.setText(message)
                    self.host.panel.show_error(message, str(exc), False)
                except RuntimeError:
                    logger.info('Layer commit feedback outlived its panel: %s', exc)
                return
            if epoch != self._epoch or generation != getattr(self.host, '_memory_generation', None):
                return
            try:
                names = ', '.join(item.name() for item in layers)
                message = _tr('Layer edits saved: {}').format(names)
                card.result.setText(message)
                self.host.panel.add_note(message)
                record = getattr(self.host, '_record', None)
                if record is not None:
                    record('note', message)
                save = getattr(self.host, '_save_transcript', None)
                if save is not None:
                    save()
                self.host._refresh_history()
            except Exception:
                logger.warning('Layer edits were saved but their feedback could not be updated', exc_info=True)

        self._tickets[key] = cancel
        for item in layers:
            for name in ('layerModified', 'editingStopped', 'dataSourceChanged', 'willBeDeleted'):
                signal = getattr(item, name, None)
                if signal is not None:
                    signal.connect(cancel)
                    connections.append((signal, cancel))
        card.answered.connect(answered)
        card.destroyed.connect(release)
