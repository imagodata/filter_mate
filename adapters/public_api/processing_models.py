# -*- coding: utf-8 -*-
"""Build drafts and open QGIS' own model designer. Creating/opening never writes a model file.

The designer asks where to save; its Save in project action is also available. Models saved outside QGIS'
profile are registered for this project session, so find/describe/run_algorithm can reuse them immediately.
"""
from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, Optional

from . import processing_tools as tools
from ...core.agent.processing_policy import LAYER_DESTINATIONS, LAYER_INPUTS, MULTI_LAYER_INPUTS, forced_values

_EDITORS = []
_SESSION_PROVIDER = None
_IDENTIFIER = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,79}$')
MAX_STEPS = 30
logger = logging.getLogger('FilterMate.ProcessingModels')


def _identifier(value, label):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f'{label}: use a name starting with a letter, then letters, digits or underscores')
    return value


def build_model(definition: Dict[str, Any]):
    """A declarative chain: inputs clone a step's parameter; bindings reference inputs or earlier outputs.

    Model creation never executes a child. No source code, file location or session layer id is embedded.
    """
    from qgis.core import (QgsProcessingModelAlgorithm, QgsProcessingModelChildAlgorithm,
                           QgsProcessingModelChildParameterSource as Source, QgsProcessingModelOutput,
                           QgsProcessingModelParameter)
    from qgis.PyQt.QtCore import QPointF
    if not isinstance(definition, dict) or set(definition) - {'name', 'group', 'inputs', 'steps', 'outputs'}:
        raise ValueError('definition takes name, group, inputs, steps and outputs')
    steps, inputs, outputs = (definition.get(key, []) for key in ('steps', 'inputs', 'outputs'))
    if (not all(isinstance(value, list) for value in (steps, inputs, outputs))
            or not 1 <= len(steps) <= MAX_STEPS or len(inputs) > 60 or not 1 <= len(outputs) <= 30):
        raise ValueError('a model needs 1 to 30 steps, at most 60 inputs and 1 to 30 outputs')
    model = QgsProcessingModelAlgorithm()
    model.setName(_identifier(definition.get('name'), 'model name'))
    model.setGroup(str(definition.get('group') or 'FilterMate')[:120])
    algorithms = {}
    for step in steps:
        if not isinstance(step, dict) or set(step) - {'id', 'algorithm_id', 'parameters'}:
            raise ValueError('each step takes id, algorithm_id and parameters')
        key = _identifier(step.get('id'), 'step id')
        if key in algorithms:
            raise ValueError(f'duplicate step {key!r}')
        algorithms[key] = tools._algorithm(step.get('algorithm_id'))

    input_names, cloned = set(), []
    for item in inputs:
        if not isinstance(item, dict) or set(item) - {'name', 'step', 'parameter', 'description', 'default'}:
            raise ValueError('each input takes name, step, parameter, description and optional default')
        name = _identifier(item.get('name'), 'input name')
        algorithm = algorithms.get(item.get('step'))
        original = algorithm.parameterDefinition(item.get('parameter', '')) if algorithm is not None else None
        if name in input_names or original is None or original.type() in LAYER_DESTINATIONS:
            raise ValueError(f'input {name!r} must reference a distinct, existing input parameter of a step')
        if original.type() not in tools.GIVEN_TYPES or original.name().upper() in tools.COMMAND_PARAMETERS:
            raise ValueError(f'input {name!r}: this parameter type cannot be exposed')
        parameter = original.clone()
        parameter.setName(name)
        parameter.setDescription(str(item.get('description') or name)[:200])
        default = item.get('default', original.defaultValue())
        if parameter.type() in LAYER_INPUTS | MULTI_LAYER_INPUTS | tools.INTERPOLATION_TYPES:
            if item.get('default') not in (None, '', []):
                raise ValueError(f'input {name!r}: layers are chosen when the model runs; no layer id or path default')
            default = None
        elif default is not None:
            default = tools._value(original, default)
        parameter.setDefaultValue(default)
        component = QgsProcessingModelParameter()
        component.setParameterName(name)
        component.setPosition(QPointF(100 + (len(input_names) % 4) * 240, 80 + (len(input_names) // 4) * 100))
        model.addModelParameter(parameter, component)
        cloned.append((parameter, item.get('step')))
        input_names.add(name)
    # A field/distance parameter's parent must name the cloned model input, not a parameter inside its child.
    bindings = {(item.get('step'), item.get('parameter')): item['name'] for item in inputs}
    for parameter, key in cloned:
        getter, setter = getattr(parameter, 'parentLayerParameterName', None), getattr(parameter, 'setParentLayerParameterName', None)
        if callable(getter) and callable(setter) and getter():
            setter(bindings.get((key, getter()), ''))

    previous, children = set(), {}
    for index, step in enumerate(steps):
        key, algorithm = step['id'], algorithms[step['id']]
        child = QgsProcessingModelChildAlgorithm(algorithm.id())
        child.setChildId(key)
        child.setDescription(algorithm.displayName())
        child.setPosition(QPointF(320 + (index % 3) * 280, 320 + (index // 3) * 160))
        parameters = step.get('parameters', {})
        if not isinstance(parameters, dict):
            raise ValueError(f'{key}: parameters must be an object')
        for name, value in parameters.items():
            parameter = algorithm.parameterDefinition(name)
            if parameter is None or parameter.type() in LAYER_DESTINATIONS:
                raise ValueError(f'{key}: {name!r} is not an input parameter; use outputs for final layers')
            if isinstance(value, dict) and set(value) == {'input'}:
                if value['input'] not in input_names:
                    raise ValueError(f'{key}: unknown model input {value["input"]!r}')
                source = Source.fromModelParameter(value['input'])
            elif isinstance(value, dict) and set(value) == {'step', 'output'}:
                parent = algorithms.get(value['step'])
                if value['step'] not in previous or parent is None or parent.outputDefinition(value['output']) is None:
                    raise ValueError(f'{key}: a connection must name an output of an earlier step')
                source = Source.fromChildOutput(value['step'], value['output'])
            else:
                if parameter.type() in LAYER_INPUTS | MULTI_LAYER_INPUTS | tools.INTERPOLATION_TYPES:
                    raise ValueError(f'{key}.{name}: wire a model input or an earlier step; never embed a session layer')
                if name.upper() in tools.COMMAND_PARAMETERS:
                    raise ValueError(f'{key}.{name}: extra command-line options or SQL cannot be supplied')
                source = Source.fromStaticValue(tools._value(parameter, value))
            child.addParameterSources(name, [source])
        for parameter in algorithm.parameterDefinitions():
            name, kind = parameter.name(), parameter.type()
            if name in parameters or name in forced_values(algorithm.id()) or kind not in tools.GIVEN_TYPES:
                continue
            if name.upper() in tools.COMMAND_PARAMETERS:
                continue
            default = tools._json(parameter.defaultValue())
            if default is not None:
                # Older QGIS model validation requires explicit sources even for mandatory parameters with defaults.
                child.addParameterSources(name, [Source.fromStaticValue(tools._value(parameter, default))])
        for name, value in forced_values(algorithm.id()).items():
            child.addParameterSources(name, [Source.fromStaticValue(value)])
        # Unexposed intermediate outputs are redirected to managed storage by run_algorithm, not saved here.
        for parameter in algorithm.parameterDefinitions():
            if parameter.type() in LAYER_DESTINATIONS:
                child.addParameterSources(parameter.name(), [Source.fromStaticValue('TEMPORARY_OUTPUT')])
        children[key] = child
        previous.add(key)
    output_names = set()
    for item in outputs:
        if not isinstance(item, dict) or set(item) - {'name', 'step', 'output', 'description'}:
            raise ValueError('each output takes name, step, output and optional description')
        name = _identifier(item.get('name'), 'output name')
        key, parameter = item.get('step'), item.get('output')
        algorithm = algorithms.get(key)
        destination = algorithm.parameterDefinition(parameter or '') if algorithm is not None else None
        if name in output_names or destination is None or destination.type() not in LAYER_DESTINATIONS:
            raise ValueError(f'output {name!r} must name a distinct layer destination of a step')
        output = QgsProcessingModelOutput()
        output.setName(name)
        output.setDescription(str(item.get('description') or name)[:200])
        output.setChildId(key)
        output.setChildOutputName(parameter)
        child = children[key]
        made = child.modelOutputs()
        made[name] = output
        child.setModelOutputs(made)
        output_names.add(name)
    for child in children.values():
        model.addChildAlgorithm(child)
    model.updateDestinationParameters()
    valid, issues = model.validate()
    if not valid:
        raise ValueError('invalid model: ' + '; '.join(str(issue) for issue in issues))
    for child in tools._children(model).values():
        reason = tools._model_sources_problem(child, tools._child_algorithm(child), model)
        if reason:
            raise ValueError('invalid model: ' + reason)
    return model


def _register_saved(model):
    """A file the user saved outside the profile is still available through the registry for this session."""
    global _SESSION_PROVIDER
    from qgis.core import QgsProcessingProvider, QgsProject
    registry = tools._registry()
    if _SESSION_PROVIDER is None:
        class SavedModels(QgsProcessingProvider):
            def __init__(self):
                super().__init__()
                self.models = {}

            def id(self):
                return 'filtermate_models'

            def name(self):
                return 'FilterMate models'

            def loadAlgorithms(self):
                for template in self.models.values():
                    self.addAlgorithm(template.create())

        _SESSION_PROVIDER = SavedModels()
        registry.addProvider(_SESSION_PROVIDER)

        def clear():
            global _SESSION_PROVIDER
            if _SESSION_PROVIDER is not None:
                registry.removeProvider(_SESSION_PROVIDER.id())
                _SESSION_PROVIDER = None
            try:
                QgsProject.instance().cleared.disconnect(clear)
            except (RuntimeError, TypeError):
                pass
        QgsProject.instance().cleared.connect(clear)
    clone = model.create()
    clone.setSourceFilePath(model.sourceFilePath())
    _SESSION_PROVIDER.models[clone.name()] = clone
    _SESSION_PROVIDER.refreshAlgorithms()


def open_model(algorithm_id: str = '', definition: Optional[Dict[str, Any]] = None, *, on_saved=None,
               iface_obj=None) -> Dict[str, Any]:
    """Open an existing model, a declarative draft, or a blank designer. Saving is a user action in the designer."""
    from qgis.core import QgsProject
    from qgis.PyQt.QtWidgets import QFileDialog
    from .gui_control import _window
    face = _window(iface_obj)
    if algorithm_id and definition is not None:
        raise ValueError('choose either an existing algorithm_id or a new definition')
    if algorithm_id:
        template = tools._registry().algorithmById(algorithm_id)
        if template is None or not tools._is_model(template):
            raise ValueError(f'{algorithm_id!r} is not a registered Processing model; find_algorithms with model lists them')
        model = template.create()
    else:
        model = build_model(definition) if definition is not None else None
    try:
        from processing.modeler.ModelerDialog import ModelerDialog
    except ImportError:
        # QGIS 4.4 moved the complete designer into C++, with iface.openModelDesigner.
        from qgis.gui import QgisInterface
        if not callable(getattr(QgisInterface, 'openModelDesigner', None)):
            raise ValueError('the QGIS Processing plugin must be enabled to open the model designer') from None
        return _open_native_model(model, face, on_saved)

    class Designer(ModelerDialog):
        # Use QGIS' editor and Save in project, but never default a model file to its profile models directory.
        def saveModel(self, saveAs):
            if saveAs or not self.model().sourceFilePath():
                folder = QgsProject.instance().homePath() or os.path.expanduser('~')
                path, _ = QFileDialog.getSaveFileName(self, self.tr('Save Model'),
                    os.path.join(folder, (self.model().name() or 'model') + '.model3'),
                    self.tr('Processing models (*.model3)'))
                if not path:
                    return False
                if not path.lower().endswith('.model3'):
                    path += '.model3'
                    if os.path.exists(path):
                        self.messageBar().pushWarning(self.tr('Save Model'),
                            self.tr('This model file already exists. Choose its full name to confirm overwriting.'))
                        return False
                self.model().setSourceFilePath(path)
            return super().saveModel(False)

    if model is not None:
        model.setSourceFilePath('')  # editing a template is a draft; Save asks for a destination
    editor = Designer(model, face.mainWindow())
    return _show_editor(editor, on_saved, 'update_model')


def _open_native_model(model, face, on_saved):
    from qgis.core import QgsProject
    from qgis.gui import QgsModelDesignerDialog
    from qgis.PyQt.QtGui import QAction
    from qgis.PyQt.QtWidgets import QFileDialog
    if model is not None:
        model.setSourceFilePath('')
    opener = getattr(face, 'openModelDesigner', None)
    if callable(opener):
        editor = opener(model)
    else:
        editor = QgsModelDesignerDialog(face.mainWindow())
        if model is not None:
            editor.setModel(model)
    if editor is None:
        raise ValueError('this QGIS could not open the model designer')

    def save(save_as=False):
        current = editor.model()
        valid, issues = current.validate()
        if not valid:
            editor.messageBar().pushWarning(editor.tr('Save Model'), '; '.join(str(issue) for issue in issues))
            return False
        path = current.sourceFilePath()
        if save_as or not path:
            folder = QgsProject.instance().homePath() or os.path.expanduser('~')
            path, _ = QFileDialog.getSaveFileName(editor, editor.tr('Save Model'),
                os.path.join(folder, (current.name() or 'model') + '.model3'),
                editor.tr('Processing models (*.model3)'))
            if not path:
                return False
            if not path.lower().endswith('.model3'):
                path += '.model3'
                if os.path.exists(path):
                    editor.messageBar().pushWarning(editor.tr('Save Model'), editor.tr('This model file already exists.'))
                    return False
        if not current.toFile(path):
            editor.messageBar().pushWarning(editor.tr('Save Model'), editor.tr('The model could not be saved.'))
            return False
        # loadModel marks the native document clean; QGIS 4.4 keeps its dirty flag private.
        editor.loadModel(path)
        editor.modelUpdated.emit()
        return True
    editor.saveModel = save
    for name, save_as in (('mActionSave', False), ('mActionSaveAs', True)):
        action = editor.findChild(QAction, name)
        if action is not None:
            action.triggered.disconnect()
            action.triggered.connect(lambda _checked=False, save_as=save_as: save(save_as))
    return _show_editor(editor, on_saved, 'modelUpdated')


def _show_editor(editor, on_saved, signal):

    def saved():
        try:
            path = editor.model().sourceFilePath()
            if path and os.path.isfile(path):
                _register_saved(editor.model())
                if on_saved is not None:
                    on_saved(path)
        except Exception:
            # A designer can outlive the panel/plugin. No exception may escape a Qt save signal.
            logger.exception('The saved model could not be registered or linked in the agent panel')
    getattr(editor, signal).connect(saved)
    _EDITORS.append(editor)
    editor.destroyed.connect(lambda *_: _EDITORS.remove(editor) if editor in _EDITORS else None)
    editor.show()
    editor.raise_()
    editor.activateWindow()
    return {'opened': True, 'name': editor.model().displayName(), 'saved': False,
            'note': 'Draft in the QGIS model designer. Save asks for a .model3 location; Save in project embeds it.'}


def chat_handlers(on_saved=None):
    from ...core.agent.tool_executor import ToolFailure

    def run(arguments):
        try:
            return open_model(arguments.get('algorithm_id', ''), arguments.get('definition'), on_saved=on_saved)
        except ValueError as exc:
            raise ToolFailure(str(exc)) from None
    return {'open_model': run}
