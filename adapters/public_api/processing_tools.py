# -*- coding: utf-8 -*-
"""Processing for the agent: find an algorithm, read its parameters, run it on the layers of the project.

Main thread only, plain dicts out. What may run is decided by ``core/agent/processing_policy.py``. Output layers
use project memory where supported, or the user's chosen data folder, so undoing the turn of the chat removes them
and redoing it opens the file again. An algorithm that can run in the background does, while the event loop turns
and the user can press Stop; one that cannot (``FlagNoThreading``) holds QGIS until it ends.
"""
from __future__ import annotations

import logging
import math
import os
import re
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from ...core.agent.processing_policy import (
    COMMAND_PARAMETERS, FILE_DESTINATIONS, GIVEN_TYPES, INTERPOLATION_TYPES, LAYER_DESTINATIONS, LAYER_INPUTS,
    MEMORY_PROVIDERS, MULTI_LAYER_INPUTS,
    forced_values, matches, refusal,
)
from ...core.agent.sql_guard import processing_expression_problem
from ...core.domain.layer_kind import LayerKind
from .operations import _RUNNING, busy_reason, layer_kind, resolve_layer

logger = logging.getLogger('FilterMate.Processing')

MAX_FOUND = 50
MAX_SUMMARY_CHARS = 200
MAX_HELP_CHARS = 1500
MAX_TEXT_CHARS = 2000
MAX_MESSAGES = 10
MAX_OPTIONS = 60
RUNNING_LABEL = 'a Processing algorithm'
_NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
_CRS_SUFFIX = r'(?:\s*\[[A-Za-z]+:[A-Za-z0-9_.]+\])?'
_EXTENT = re.compile(rf'^\s*{_NUMBER}\s*,\s*{_NUMBER}\s*,\s*{_NUMBER}\s*,\s*{_NUMBER}{_CRS_SUFFIX}\s*$')
_POINT = re.compile(rf'^\s*{_NUMBER}\s*,\s*{_NUMBER}{_CRS_SUFFIX}\s*$')
_AUTHID = re.compile(r'^[A-Za-z]+:[A-Za-z0-9_.]+$')
_INTEGER = re.compile(r'^\s*-?\d+\s*$')
_ROW, _FIELD = '::|::', '::~::'  # how QGIS splits the inputs of an interpolation
_TAGS = re.compile(r'<[^>]+>')


# --- the registry ----------------------------------------------------------------------------------------------

def _registry():
    from qgis.core import QgsApplication
    return QgsApplication.processingRegistry()


def _flag(scope: str, new: str, old: str):
    """A flag of Qgis (3.36 and later) or of the old class enum (3.22 - 3.34)."""
    from qgis.core import Qgis
    found = getattr(getattr(Qgis, scope, None), new, None)
    if found is not None:
        return found
    from qgis.core import QgsProcessingAlgorithm, QgsProcessingParameterDefinition
    owner = QgsProcessingAlgorithm if scope == 'ProcessingAlgorithmFlag' else QgsProcessingParameterDefinition
    return getattr(getattr(owner, 'Flag', owner), old)


def _has(flags, flag) -> bool:
    try:
        return bool(flags & flag)
    except TypeError:
        return bool(int(flags) & int(flag))


def _optional(parameter) -> bool:
    return _has(parameter.flags(), _flag('ProcessingParameterFlag', 'Optional', 'FlagOptional'))


def _hidden(parameter) -> bool:
    return _has(parameter.flags(), _flag('ProcessingParameterFlag', 'Hidden', 'FlagHidden'))


def _described(algorithm) -> List[Tuple[str, str, bool]]:
    return [(item.name(), item.type(), _optional(item)) for item in algorithm.parameterDefinitions()]


def _is_model(algorithm) -> bool:
    return callable(getattr(algorithm, 'childAlgorithms', None))


def _children(algorithm):
    return {key: child for key, child in algorithm.childAlgorithms().items() if child.isActive()}


def _child_algorithm(child):
    return child.algorithm() or _registry().algorithmById(child.algorithmId())


def _model_source_kind(source, name):
    from qgis.core import Qgis, QgsProcessingModelChildParameterSource
    scope = getattr(Qgis, 'ProcessingModelChildParameterSource', QgsProcessingModelChildParameterSource)
    return source.source() == getattr(scope, name)


def _why_not(algorithm, ancestors=()) -> str:
    """Why the agent cannot run the algorithm; empty when it is available."""
    provider = algorithm.provider()
    if provider is not None and not provider.isActive():
        return f"provider '{provider.id()}' is not active in this QGIS"
    if algorithm.id() in ancestors or len(ancestors) >= 12:
        return 'its model dependencies contain a cycle or are nested too deeply'
    flags = algorithm.flags()
    deprecated = _has(flags, _flag('ProcessingAlgorithmFlag', 'Deprecated', 'FlagDeprecated'))
    hidden = _has(flags, _flag('ProcessingAlgorithmFlag', 'HideFromToolbox', 'FlagHideFromToolbox'))
    if hidden:
        return 'it is not offered in the Processing toolbox'
    reason = refusal(algorithm.id(), provider.id() if provider is not None else '', _described(algorithm), deprecated)
    if reason:
        return reason
    if _is_model(algorithm):
        for key, child in _children(algorithm).items():
            resolved = _child_algorithm(child)
            if resolved is None:
                return f"step '{key}' needs missing algorithm '{child.algorithmId()}'"
            reason = _why_not(resolved, ancestors + (algorithm.id(),))
            if not reason:
                reason = _model_sources_problem(child, resolved, algorithm)
            if reason:
                return f"step '{key}' ({child.algorithmId()}): {reason}"
    can_execute = getattr(algorithm, 'canExecute', None)
    if callable(can_execute):
        available = can_execute()
        if isinstance(available, tuple) and not available[0]:
            return str(available[1]) or 'its dependencies are not available'
        if available is False:
            return 'its dependencies are not available'
    return ''


def _model_sources_problem(child, algorithm, model):
    definitions = {item.name(): item for item in algorithm.parameterDefinitions()}
    checked = LAYER_INPUTS | MULTI_LAYER_INPUTS | INTERPOLATION_TYPES | {'extent', 'point', 'crs', 'expression'}
    variables = {'@' + item.name() for item in model.parameterDefinitions()}
    for name, sources in child.parameterSources().items():
        definition = definitions.get(name)
        if definition is None:
            return f"unknown parameter '{name}'"
        kind = definition.type()
        if kind in LAYER_DESTINATIONS | FILE_DESTINATIONS or name in forced_values(algorithm.id()):
            continue  # all destinations and forced values are replaced before running the model
        for source in sources:
            if _model_source_kind(source, 'StaticValue'):
                value = source.staticValue()
                if value in (None, '', []):
                    continue
                if name.upper() in COMMAND_PARAMETERS:
                    return f"'{name}' contains extra command-line options or SQL"
                try:
                    _value(definition, value)
                except ValueError as exc:
                    return str(exc)
            elif _model_source_kind(source, 'Expression') or _model_source_kind(source, 'ExpressionText'):
                if kind in checked or name.upper() in COMMAND_PARAMETERS:
                    return f"'{name}' must be wired to a model input or a child output"
                expression = source.expression() if _model_source_kind(source, 'Expression') else source.expressionText()
                expressions = ([expression] if _model_source_kind(source, 'Expression') else
                               re.findall(r'\[%\s*(.*?)\s*%\]', expression, re.DOTALL))
                problem = next((why for part in expressions
                                if (why := processing_expression_problem(part, variables=variables))), '')
                if problem:
                    return f"'{name}': {problem}"
            elif _model_source_kind(source, 'ModelParameter') and kind in checked:
                parent = model.parameterDefinition(source.parameterName())
                compatible = LAYER_INPUTS if kind in LAYER_INPUTS else {kind}
                if parent is None or parent.type() not in compatible:
                    return f"'{name}' must be connected to a model input of the same checked type"
            elif _model_source_kind(source, 'ChildOutput') and kind in checked:
                parent = model.childAlgorithms().get(source.outputChildId())
                parent_algorithm = _child_algorithm(parent) if parent is not None else None
                output = parent_algorithm.outputDefinition(source.outputName()) if parent_algorithm is not None else None
                layer_outputs = {'outputVector', 'outputRaster', 'outputLayer', 'outputPointCloud', 'outputMesh'}
                compatible = layer_outputs if kind in LAYER_INPUTS else {'outputMultilayers'} if kind in MULTI_LAYER_INPUTS else set()
                if output is None or output.type() not in compatible:
                    return f"'{name}' cannot take that child output as a checked parameter"
            elif kind not in GIVEN_TYPES or name.upper() in COMMAND_PARAMETERS:
                return f"'{name}' ({kind}) cannot be supplied by a model"
    return ''


def _needs_disk(algorithm) -> bool:
    if _is_model(algorithm):
        return any(_needs_disk(_child_algorithm(child)) for child in _children(algorithm).values())
    provider = algorithm.provider()
    kinds = {item.type() for item in algorithm.parameterDefinitions()}
    if 'pointCloudDestination' in kinds or provider is None:
        return True
    if provider.id() in MEMORY_PROVIDERS:
        return False
    non_file = getattr(provider, 'supportsNonFileBasedOutput', None)
    # The provider flag covers vector sinks. Foreign raster writers still need a shared filesystem path.
    return 'rasterDestination' in kinds or not (callable(non_file) and non_file())


def _identity(algorithm):
    provider = algorithm.provider()
    return {'provider': provider.id() if provider is not None else '',
            'provider_name': provider.name() if provider is not None else '',
            'is_model': _is_model(algorithm), 'requires_disk': _needs_disk(algorithm)}


def _plain(text: str, size: int) -> str:
    text = ' '.join(_TAGS.sub(' ', text or '').split())
    return text if len(text) <= size else text[:size] + '…'


def _algorithm(algorithm_id: str):
    """The algorithm a model may run.

    Raises:
        ValueError: Unknown, or refused (the reason says why).
    """
    algorithm = _registry().algorithmById(str(algorithm_id or ''))
    if algorithm is None:
        raise ValueError(f"no Processing algorithm {algorithm_id!r}: find_algorithms gives the ids")
    reason = _why_not(algorithm)
    if reason:
        raise ValueError(f"'{algorithm.id()}' cannot be run by the agent: {reason}")
    return algorithm


def find_algorithms(query: str, limit: int = 20) -> Dict[str, Any]:
    """The algorithms a model may run whose id, name, group or tags hold every word of ``query``."""
    limit = max(1, min(int(limit), MAX_FOUND))
    found: List[Dict[str, Any]] = []
    total = 0
    for algorithm in sorted(_registry().algorithms(), key=lambda item: item.id()):
        provider = algorithm.provider()
        if not matches(query, [algorithm.id(), algorithm.displayName(), algorithm.group(), ' '.join(algorithm.tags()),
                               provider.name() if provider is not None else '', 'model modèle' if _is_model(algorithm) else '']):
            continue
        if _why_not(algorithm):
            continue
        total += 1
        if len(found) < limit:
            summary = algorithm.shortDescription() or algorithm.shortHelpString()
            found.append({'id': algorithm.id(), 'name': algorithm.displayName(), 'group': algorithm.group(),
                          'summary': _plain(summary, MAX_SUMMARY_CHARS), **_identity(algorithm)})
    answer: Dict[str, Any] = {'query': query, 'algorithms': found, 'total': total}
    if not _registry().algorithms():
        answer['note'] = 'Processing is not available in this QGIS (the Processing plugin may be turned off).'
    elif total > limit:
        answer['note'] = 'More algorithms match: add a word to the query.'
    return answer


# --- reading the parameters --------------------------------------------------------------------------------------

def _json(value: Any) -> Any:
    """A default value or a result as JSON; None for what has no plain form."""
    if value is None or isinstance(value, bool) or isinstance(value, int) or isinstance(value, str):
        return value[:MAX_TEXT_CHARS] if isinstance(value, str) else value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in list(value)[:MAX_OPTIONS]]
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in list(value.items())[:MAX_OPTIONS]}
    is_null = getattr(value, 'isNull', None)
    if callable(is_null):
        try:
            if is_null():
                return None
        except TypeError:
            pass
    return None


def _parameter(definition) -> Dict[str, Any]:
    kind = definition.type()
    row: Dict[str, Any] = {'name': definition.name(), 'type': kind, 'description': definition.description(),
                           'optional': _optional(definition)}
    if kind in LAYER_DESTINATIONS:
        row['destination'] = ('FilterMate chooses its storage and adds the layer to the project; pass false to skip '
                              'it when it is optional')
        row['created_by_default'] = bool(definition.createByDefault())
        return row
    default = _json(definition.defaultValue())
    if default not in (None, '', []):
        row['default'] = default
    options = getattr(definition, 'options', None)
    if kind == 'enum' and callable(options):
        row['options'] = list(options())[:MAX_OPTIONS]
        row['multiple'] = bool(definition.allowMultiple())
    for name, key in (('parentLayerParameterName', 'parent'), ('allowMultiple', 'multiple')):
        getter = getattr(definition, name, None)
        if callable(getter) and key not in row:
            value = getter()
            if value:
                row[key] = value
    for name in ('minimum', 'maximum'):
        getter = getattr(definition, name, None)
        if callable(getter):
            value = getter()
            if isinstance(value, (int, float)) and math.isfinite(value) and abs(value) < 1e15:
                row[name] = value
    if kind in ('source', 'vector'):
        row['value'] = 'a layer of the project (name or id); {"layer": ..., "selected_only": true} for its selection' \
            if kind == 'source' else 'a layer of the project (name or id)'
    elif kind in LAYER_INPUTS:
        row['value'] = 'a layer of the project (name or id)'
    elif kind in MULTI_LAYER_INPUTS:
        row['value'] = 'a list of layers of the project'
    elif kind == 'extent':
        row['value'] = ('[xmin, ymin, xmax, ymax] in the project CRS, "xmin,xmax,ymin,ymax [EPSG:2154]" (note the '
                        'order of the text), or a layer of the project')
    elif kind == 'point':
        row['value'] = '"x,y [EPSG:2154]"'
    elif kind == 'crs':
        row['value'] = '"EPSG:2154", or a layer of the project for its CRS'
    elif kind == 'expression':
        row['value'] = 'a QGIS expression (plain conditions and computations; functions outside a list are refused)'
    elif kind in INTERPOLATION_TYPES:
        row['value'] = ('one row per input, joined by "::|::": "layer::~::value source::~::field index::~::source type", '
                        'the layer a vector layer of the project (name or id), value source 0 a field (its index from '
                        '0), 1 the Z or 2 the M of the geometries (field index -1), source type 0 points, 1 structure '
                        'lines, 2 break lines; e.g. "points::~::0::~::3::~::0"')
    return row


def describe_algorithm(algorithm_id: str) -> Dict[str, Any]:
    """What an algorithm does, its parameters and its outputs.

    Raises:
        ValueError: Unknown, or refused.
    """
    algorithm = _algorithm(algorithm_id)
    parameters, left_out = [], []
    forced = forced_values(algorithm.id())
    for definition in algorithm.parameterDefinitions():
        if _hidden(definition) or definition.name() in forced:
            continue
        if definition.name().upper() in COMMAND_PARAMETERS:
            left_out.append(definition.name())
            continue
        if definition.type() not in GIVEN_TYPES and definition.type() not in LAYER_DESTINATIONS:
            left_out.append(definition.name())
            continue
        parameters.append(_parameter(definition))
    outputs = [{'name': item.name(), 'type': item.type(), 'description': item.description()}
               for item in algorithm.outputDefinitions()]
    answer: Dict[str, Any] = {
        'id': algorithm.id(), 'name': algorithm.displayName(), 'group': algorithm.group(),
        'help': _plain(algorithm.shortHelpString() or algorithm.shortDescription(), MAX_HELP_CHARS),
        'parameters': parameters, 'outputs': outputs,
        **_identity(algorithm),
    }
    if _is_model(algorithm):
        answer['steps'] = [{'id': key, 'algorithm_id': child.algorithmId()}
                           for key, child in _children(algorithm).items()]
    if left_out:
        answer['left_out'] = left_out
        answer['note'] = ('The parameters in left_out (files, folders, connections, types the agent cannot give) '
                          'cannot be given: they stay unset.')
    if answer['requires_disk']:
        answer['storage_note'] = ('This provider needs files. Use Save project and layers in the agent menu to '
                                  'choose their folder before running it.')
    return answer


# --- running -----------------------------------------------------------------------------------------------------

def _project_layer(reference: Any, name: str):
    """The project layer ``reference`` names; never a path, a URI or a URL, which QGIS would open.

    Raises:
        ValueError: Not a layer of the project.
    """
    layer = resolve_layer(reference) if isinstance(reference, str) and reference else None
    if layer is None:
        raise ValueError(f"{name}: {reference!r} is not a layer of the project (list_layers gives their names)")
    return layer


def _interpolation_data(name: str, value: Any) -> str:
    """The inputs of an interpolation written again, each source the id of a vector layer of the project.

    QGIS opens each source from its text (``QgsProcessingUtils.variantToSource``), a path or a URL included.

    Raises:
        ValueError: A row that is not four fields, a field after the source that is not an integer or out of its
            range (value source and source type 0 to 2, field index -1 to the last field), a source that is not a
            vector layer of the project.
    """
    rows = value.split(_ROW) if isinstance(value, str) and value.strip() else [None]
    written = []
    for row in rows:
        fields = row.split(_FIELD) if row is not None else []
        if len(fields) != 4 or not all(_INTEGER.match(item) for item in fields[1:]):
            raise ValueError(f'{name}: rows "layer::~::value source::~::field index::~::source type" joined by "::|::",'
                             ' the last three integers (describe_algorithm says which)')
        layer = _project_layer(fields[0], name)
        if layer_kind(layer) is not LayerKind.VECTOR:
            raise ValueError(f"{name}: '{layer.name()}' is not a vector layer")
        if _ROW in layer.id() or _FIELD in layer.id():  # an id of a project file, written by anyone
            raise ValueError(f"{name}: the id of '{layer.name()}' cannot be written in a row")
        source, field, kind = (int(item) for item in fields[1:])
        if not 0 <= source <= 2:
            raise ValueError(f"{name}: the value source is 0 (a field), 1 (the Z) or 2 (the M), not {source}")
        if not 0 <= kind <= 2:
            raise ValueError(f"{name}: the source type is 0 (points), 1 (structure lines) or 2 (break lines), not {kind}")
        if not -1 <= field < layer.fields().count():
            raise ValueError(f"{name}: the field index of '{layer.name()}' is -1 or 0 to {layer.fields().count() - 1}, "
                             f"not {field}")
        written.append(_FIELD.join([layer.id(), str(source), str(field), str(kind)]))
    return _ROW.join(written)


def _enum_value(definition, value: Any) -> Any:
    """An index, or an option given by its text or the start of it ("Integer" for "Integer (32 bit)")."""
    options = [str(item).casefold() for item in definition.options()]

    def one(item: Any) -> Any:
        if isinstance(item, str) and not item.strip().lstrip('-').isdigit():
            wanted = item.strip().casefold()
            if wanted in options:
                return options.index(wanted)
            starting = [index for index, option in enumerate(options) if option.startswith(wanted + ' (')]
            if len(starting) != 1:
                starting = [index for index, option in enumerate(options) if option.startswith(wanted)]
            if len(starting) != 1:
                raise ValueError(f"{definition.name()}: {item!r} is not one of its options "
                                 f"({'; '.join(definition.options()[:MAX_OPTIONS])})")
            return starting[0]
        return item
    return [one(item) for item in value] if isinstance(value, list) else one(value)


def _value(definition, value: Any) -> Any:
    """What QGIS takes for ``value`` of this parameter.

    Raises:
        ValueError: A value this parameter cannot be given by a model.
    """
    from qgis.core import QgsProcessingFeatureSourceDefinition
    kind, name = definition.type(), definition.name()
    if kind not in GIVEN_TYPES:  # a file, a connection, a PROJ operation, a type not known here
        raise ValueError(f"{name} ({kind}) cannot be given: it stays unset")
    if isinstance(value, dict) and kind != 'source':
        raise ValueError(f"{name}: an object is only taken by a source layer, as {{\"layer\": ..., \"selected_only\": true}}")
    if kind == 'source' and isinstance(value, dict):
        unknown = set(value) - {'layer', 'selected_only'}
        if unknown:
            raise ValueError(f"{name}: unknown keys {sorted(unknown)}")
        layer = _project_layer(value.get('layer'), name)
        if value.get('selected_only'):
            if not layer.selectedFeatureCount():
                raise ValueError(f"{name}: no feature is selected on '{layer.name()}'")
            return QgsProcessingFeatureSourceDefinition(layer.id(), True)
        return layer.id()
    if kind in LAYER_INPUTS:
        return _project_layer(value, name).id()
    if kind in MULTI_LAYER_INPUTS:
        if not isinstance(value, list):
            raise ValueError(f"{name}: a list of layers")
        return [_project_layer(item, name).id() for item in value]
    if kind == 'extent':
        if isinstance(value, list) and len(value) == 4:
            xmin, ymin, xmax, ymax = value
            return f"{xmin},{xmax},{ymin},{ymax}"
        if isinstance(value, str) and _EXTENT.match(value):
            return value
        return _project_layer(value, name).id()
    if kind == 'point':
        if isinstance(value, list) and len(value) == 2:
            return f"{value[0]},{value[1]}"
        if isinstance(value, str) and _POINT.match(value):
            return value
        raise ValueError(f'{name}: a point is "x,y" or "x,y [EPSG:4326]"')
    if kind == 'crs':
        if isinstance(value, str) and (_AUTHID.match(value) or value == 'ProjectCrs'):
            return value
        return _project_layer(value, name).crs().authid()
    if kind == 'expression':
        from qgis.core import Qgis
        expression_type = getattr(definition, 'expressionType', None)
        qgis_type = getattr(getattr(Qgis, 'ExpressionType', None), 'Qgis', None)
        plain_qgis = True
        if callable(expression_type) and qgis_type is not None:
            # 3.32 and later: raster calculator and point cloud expressions have their own parser, with no function
            # that reads a file or the environment.
            plain_qgis = expression_type() == qgis_type
        if plain_qgis and isinstance(value, str) and value.strip():
            problem = processing_expression_problem(value)
            if problem:
                raise ValueError(f"{name}: this expression cannot be used: {problem}")
        return value
    if kind == 'enum':
        return _enum_value(definition, value)
    if kind in INTERPOLATION_TYPES:
        return _interpolation_data(name, value)
    if isinstance(value, (dict,)):
        raise ValueError(f"{name}: an object is not taken here")
    return value  # PLAIN_TYPES: numbers, texts, fields...


def _destination_path(definition, disk=False) -> str:
    from ..agent.data_store import new_path, store_for
    extension = definition.defaultFileExtension() or ('tif' if definition.type() == 'rasterDestination' else 'gpkg')
    name = re.sub(r'[^\w. -]', '_', definition.name().lower()).strip('. ') or 'output'
    if disk or definition.type() == 'pointCloudDestination':
        return store_for().disk_path(f"{name}.{extension}")
    return new_path(f"{name}.{extension}")


def _parameters(algorithm, given: Dict[str, Any], disk=False) -> Tuple[Dict[str, Any], List[Any]]:
    """The values of the run and the layer destinations made: ``[(definition, path)]``.

    Raises:
        ValueError: An unknown parameter, or a value that cannot be given.
    """
    definitions = {item.name(): item for item in algorithm.parameterDefinitions()}
    unknown = sorted(set(given) - set(definitions))
    if unknown:
        raise ValueError(f"unknown parameter(s) {', '.join(unknown)}: describe_algorithm lists them")
    values: Dict[str, Any] = {}
    made: List[Any] = []
    for name, definition in definitions.items():
        kind = definition.type()
        if kind in LAYER_DESTINATIONS:
            wanted = given.get(name)
            if wanted is not None and not isinstance(wanted, bool):
                raise ValueError(f"{name} is an output: FilterMate stores it in memory; pass true or false")
            if wanted is False and not _optional(definition):
                raise ValueError(f"{name} is a required output: it cannot be skipped")
            if wanted is True or (wanted is None and (not _optional(definition) or definition.createByDefault())):
                path = _destination_path(definition, disk=True) if disk else _destination_path(definition)
                values[name] = path
                # Models rebuild destination definitions when children change or run. Keep an owned copy, not
                # a borrowed C++ pointer (a dangling definition can crash older QGIS after a nested model).
                made.append((definition.clone(), path))
            continue
        if kind in FILE_DESTINATIONS:
            values[name] = None  # optional (refusal() leaves out the rest): no file is written
            continue
        if name.upper() in COMMAND_PARAMETERS:
            if given.get(name) not in (None, '', []):
                raise ValueError(f"{name}: extra command-line options or SQL cannot be supplied")
            values[name] = None
            continue
        if name in given and given[name] is not None:
            values[name] = _value(definition, given[name])
        elif kind in LAYER_INPUTS | MULTI_LAYER_INPUTS | INTERPOLATION_TYPES:
            default = definition.defaultValue()
            if default not in (None, '', []):
                # A registered model can contain a stored file path as a default. Defaults obey the input rule too.
                values[name] = _value(definition, default)
    values.update(forced_values(algorithm.id()))  # whatever was given: see processing_policy.FORCED
    return values, made


def _prepare_model_outputs(model, disk):
    """Give internal outputs managed paths too: TEMPORARY_OUTPUT would use QGIS' global temp folder."""
    from qgis.core import QgsProcessingModelChildParameterSource as Source
    paths = []
    for child in _children(model).values():
        algorithm = _child_algorithm(child)
        if _is_model(algorithm):
            paths.extend(_prepare_model_outputs(algorithm, disk))
        for definition in algorithm.parameterDefinitions():
            name, kind = definition.name(), definition.type()
            if kind in LAYER_DESTINATIONS:
                # An exposed model output takes precedence over this source at execution time.
                # Context-owned vector sinks also flush correctly between children in older QGIS versions.
                value = 'memory:' if kind == 'sink' and not disk else _destination_path(definition, disk=disk)
                if value != 'memory:':
                    paths.append(value)
            elif kind in FILE_DESTINATIONS or name.upper() in COMMAND_PARAMETERS:
                value = None
            elif name in forced_values(algorithm.id()):
                value = forced_values(algorithm.id())[name]
            else:
                continue
            child.addParameterSources(name, [Source.fromStaticValue(value)])
        model.setChildAlgorithm(child)
    return paths


def _disk_inputs(algorithm, values, context):
    """External programs cannot read this process' /vsimem or memory layers. Export snapshots in the chosen folder.

    The project layers, their filters and their selections keep their state. Copies belong to the context, not
    to the project. Each vector snapshot honours the source filter and, when requested, its selection.
    """
    from qgis.core import (QgsProcessingFeatureSourceDefinition, QgsRasterFileWriter, QgsRasterPipe,
                           QgsVectorFileWriter, QgsVectorLayer, QgsRasterLayer)
    from ..agent.data_store import store_for
    store, copies = store_for(), {}

    def copy(reference):
        selected = isinstance(reference, QgsProcessingFeatureSourceDefinition) and reference.selectedFeaturesOnly
        original = reference.source.staticValue() if isinstance(reference, QgsProcessingFeatureSourceDefinition) else reference
        layer = context.getMapLayer(original)
        if layer is None:
            raise ValueError(f"Processing input {original!r} is no longer available")
        key = layer.id(), selected
        if key in copies:
            return copies[key]
        kind = layer_kind(layer)
        if kind is LayerKind.VECTOR:
            path = store.disk_path('input.gpkg')
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.onlySelectedFeatures = bool(selected)
            error = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, context.transformContext(), options)
            if error[0] != QgsVectorFileWriter.WriterError.NoError:
                raise ValueError(f"the input '{layer.name()}' could not be copied for this provider: {error[1]}")
            snapshot = QgsVectorLayer(path, layer.name(), 'ogr')
        elif kind is LayerKind.RASTER:
            # Already durable GDAL sources can be read by the external process without a second copy.
            source = layer.source().split('|', 1)[0]
            if layer.providerType() == 'gdal' and os.path.isfile(source):
                return source
            path = store.disk_path('input.tif')
            writer = QgsRasterFileWriter(path)
            pipe = QgsRasterPipe()
            if not pipe.set(layer.dataProvider().clone()):
                raise ValueError(f"the input '{layer.name()}' could not be read")
            error = writer.writeRaster(pipe, layer.width(), layer.height(), layer.extent(), layer.crs(),
                                       context.transformContext())
            if int(error) != 0:
                raise ValueError(f"the input '{layer.name()}' could not be copied for this provider ({error})")
            snapshot = QgsRasterLayer(path, layer.name(), 'gdal')
        else:
            return layer.id()  # point clouds and meshes already have file-backed providers
        if not snapshot.isValid():
            raise ValueError(f"the copied input '{layer.name()}' could not be opened")
        context.temporaryLayerStore().addMapLayer(snapshot)
        copies[key] = snapshot.source()
        return snapshot.source()

    for definition in algorithm.parameterDefinitions():
        name, kind = definition.name(), definition.type()
        if name not in values or values[name] is None:
            continue
        if kind in LAYER_INPUTS:
            values[name] = copy(values[name])
        elif kind in MULTI_LAYER_INPUTS:
            values[name] = [copy(value) for value in values[name]]


def _feedback_class():
    from qgis.core import QgsProcessingFeedback
    from qgis.PyQt.QtCore import pyqtSignal

    class Feedback(QgsProcessingFeedback):
        """Keeps the errors and warnings of the run: they say why it failed."""

        cancel_requested = pyqtSignal()

        def __init__(self) -> None:
            super().__init__()
            self.messages: List[str] = []
            self.cancel_requested.connect(self.cancel)

        def request_cancel(self):
            self.cancel_requested.emit()

        def reportError(self, error, fatalError=False):  # noqa: N802 - Qt name
            self.messages.append(str(error))
            super().reportError(error, fatalError)

        def pushWarning(self, warning):  # noqa: N802 - Qt name
            self.messages.append(str(warning))
            super().pushWarning(warning)
    return Feedback


@contextmanager
def _working_folder(folder):
    """Keep Python/provider subprocess scratch files in the same explicitly chosen workspace.

    The busy guard prevents concurrent agent runs. Restore process settings even after a stop or provider error.
    Providers using QGIS' utilities receive the folder through the Processing context as well.
    """
    if not folder:
        yield
        return
    previous = {key: os.environ.get(key) for key in ('TMPDIR', 'TMP', 'TEMP')}
    previous_python = tempfile.tempdir
    try:
        for key in previous:
            os.environ[key] = folder
        tempfile.tempdir = folder
        yield
    finally:
        tempfile.tempdir = previous_python
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _run(algorithm, values: Dict[str, Any], context, feedback) -> Tuple[bool, Dict[str, Any]]:
    """Run, in a task while the event loop turns, or here for an algorithm that cannot leave the main thread."""
    from qgis.core import QgsApplication, QgsProcessingAlgRunnerTask
    from qgis.PyQt.QtCore import QEventLoop
    from ..agent.bounded_http import on_abort
    if _has(algorithm.flags(), _flag('ProcessingAlgorithmFlag', 'NoThreading', 'FlagNoThreading')):
        results, ok = algorithm.run(values, context, feedback)
        return bool(ok), dict(results or {})
    done: Dict[str, Any] = {}
    loop = QEventLoop()
    task = QgsProcessingAlgRunnerTask(algorithm, values, context, feedback)

    def executed(ok, results) -> None:
        done.update(ok=bool(ok), results=dict(results or {}))
        loop.quit()
    task.executed.connect(executed)
    forget = on_abort(feedback.cancel)
    try:
        QgsApplication.taskManager().addTask(task)
        if not done:
            loop.exec()
    finally:
        forget()
    return done.get('ok', False), done.get('results', {})


def _add_output(definition, path: str, name: str) -> Optional[Dict[str, Any]]:
    """The layer at ``path``, added to the project; None when it could not be opened (an empty output)."""
    from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
    kind = definition.type()
    if kind == 'rasterDestination':
        layer, layer_kind = QgsRasterLayer(path, name), 'raster'
    elif kind == 'pointCloudDestination':
        from qgis.core import QgsPointCloudLayer
        provider = 'copc' if path.lower().endswith('.copc.laz') else 'pdal'
        layer, layer_kind = QgsPointCloudLayer(path, name, provider), 'point_cloud'
    else:
        layer, layer_kind = QgsVectorLayer(path, name, 'ogr'), 'vector'
    if not layer.isValid():
        return None
    QgsProject.instance().addMapLayer(layer)
    row: Dict[str, Any] = {'output': definition.name(), 'layer_id': layer.id(), 'name': layer.name(),
                           'layer_kind': layer_kind}
    if layer_kind == 'vector':
        row['feature_count'] = layer.featureCount()
    return row


def _values(algorithm, results: Dict[str, Any], made_names) -> Dict[str, Any]:
    """The outputs that are values (numbers, text), not layers or paths."""
    paths = ('outputHtml', 'outputFile', 'outputFolder', 'outputLayer', 'outputVector', 'outputRaster',
             'outputMultilayers', 'outputPointCloud', 'outputVectorTile')
    kinds = {item.name(): item.type() for item in algorithm.outputDefinitions()}
    answer: Dict[str, Any] = {}
    for name, value in results.items():
        if name in made_names or kinds.get(name) in paths or name not in kinds:
            continue
        plain = _json(value)
        if plain is not None:
            answer[name] = plain
    return answer


def run_algorithm(algorithm_id: str, parameters: Optional[Dict[str, Any]] = None,
                  names: Optional[Dict[str, str]] = None, share_values: bool = True) -> Dict[str, Any]:
    """Run an algorithm on the layers of the project; the layers it makes are added to the project.

    Args:
        names: Name of the layer made by each output, by output name; the algorithm's name by default.
        share_values: False leaves the values the algorithm answers (statistics) out of the answer.

    Raises:
        ValueError: Refused, a bad parameter, busy, or the algorithm failed (with what it said).
    """
    from qgis.core import QgsProcessingContext, QgsProject
    reason = busy_reason()
    if reason:
        raise ValueError(reason)
    algorithm = _algorithm(algorithm_id).create()
    given = dict(parameters or {})
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    disk = _needs_disk(algorithm)
    if disk:
        if not callable(getattr(context, 'setTemporaryFolder', None)):
            raise ValueError('this provider needs QGIS 3.32 or later to keep its working files in your chosen folder')
        from ..agent.data_store import store_for
        folder = os.path.dirname(store_for().disk_path('processing'))
        context.setTemporaryFolder(folder)
    values, made = _parameters(algorithm, given, disk=disk)
    output_paths = [path for _definition, path in made]
    if _is_model(algorithm):
        output_paths.extend(_prepare_model_outputs(algorithm, disk))
    if disk:
        _disk_inputs(algorithm, values, context)
    feedback = _feedback_class()()
    from ..agent.data_store import store_for
    with store_for().native_outputs(output_paths, feedback):
        ok, message = algorithm.checkParameterValues(values, context)
        if not ok:
            raise ValueError(f"invalid parameters: {message}")
        _RUNNING.append(RUNNING_LABEL)
        try:
            with _working_folder(folder if disk else ''):
                ok, results = _run(algorithm, values, context, feedback)
        finally:
            if RUNNING_LABEL in _RUNNING:
                _RUNNING.remove(RUNNING_LABEL)
        if feedback.isCanceled():
            raise ValueError('stopped')
        if not ok:
            said = '; '.join(feedback.messages[-3:])
            raise ValueError(f"the algorithm failed{': ' + said if said else ''}")
    names = names or {}
    layers, skipped = [], []
    single = len(made) == 1
    for definition, path in made:
        produced = results.get(definition.name()) or path
        if not isinstance(produced, str):
            produced = path
        name = names.get(definition.name()) or (algorithm.displayName() if single else
                                                f"{definition.description()} ({algorithm.displayName()})")
        row = _add_output(definition, produced, str(name)[:200])
        (layers.append(row) if row is not None else skipped.append(definition.name()))
    answer: Dict[str, Any] = {'algorithm': algorithm.id(), 'name': algorithm.displayName(), 'layers': layers}
    if skipped:
        answer['not_made'] = skipped  # an output the algorithm left empty, or did not write
    if share_values:
        found = _values(algorithm, results, {definition.name() for definition, _ in made})
        if found:
            answer['values'] = found
    if feedback.messages:
        answer['messages'] = [_plain(item, 300) for item in feedback.messages[-MAX_MESSAGES:]]
    return answer
