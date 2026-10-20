"""A deferred service filter must use only the selection requested by its click."""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

PATH = Path(__file__).resolve().parents[3] / 'filter_mate_dockwidget.py'


def _methods(*names, **namespace):
    tree = ast.parse(PATH.read_text())
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace


def _task():
    return SimpleNamespace(error=None, taskCompleted=MagicMock(), taskTerminated=MagicMock())


def _settled(task, signal='taskCompleted'):
    return getattr(task, signal).connect.call_args.args[0]


@pytest.fixture
def deferred():
    timer, warning = MagicMock(), MagicMock()
    namespace = _methods('_defer_remote_filter', '_follow_remote_filter', QTimer=timer, show_warning=warning)
    slot = SimpleNamespace(generation=1, task=_task())
    controller = SimpleNamespace(_remote_ui_revision=lambda: 'initial',
                                 _remote_selection_pending='requested',
                                 _remote_selection_result=None)
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, launchTaskEvent=MagicMock(),
                           tr=lambda text: text)
    dock._follow_remote_filter = MethodType(namespace['_follow_remote_filter'], dock)
    MethodType(namespace['_defer_remote_filter'], dock)(slot)
    return SimpleNamespace(dock=dock, controller=controller, slot=slot, timer=timer, warning=warning,
                           task=slot.task)


def run_queued(timer):
    """Run the callbacks queued with QTimer.singleShot(0, ...) so far."""
    calls = list(timer.singleShot.call_args_list)
    timer.singleShot.reset_mock()
    for call in calls:
        call.args[1]()


def test_completed_selection_resumes_filter(deferred):
    deferred.controller._remote_selection_result = ('requested', [], '"id" IN (1)')
    deferred.slot.task = None
    _settled(deferred.task)()
    run_queued(deferred.timer)
    deferred.dock.launchTaskEvent.assert_called_once_with(False, 'filter')
    assert deferred.dock._pending_remote_filter is None
    deferred.warning.assert_not_called()


@pytest.mark.parametrize('change', ['layer', 'cancelled', 'other selection', 'failure', 'dropped delivery'])
def test_a_filter_that_cannot_resume_says_so(deferred, change):
    """M11: a data change, a cancel from the task manager, a changed selection... never drop it silently."""
    signal = 'taskCompleted'
    deferred.slot.task = None
    if change == 'layer':
        deferred.controller._remote_selection_result = ('requested', [], '')
        deferred.dock.current_layer = object()
    elif change == 'cancelled':
        signal = 'taskTerminated'
    elif change == 'other selection':
        signal = 'taskTerminated'
        deferred.slot.task = _task()
        deferred.controller._remote_selection_pending = 'another selection'
    elif change == 'failure':
        signal = 'taskTerminated'
        deferred.task.error = RuntimeError('read failed')
    # 'dropped delivery': completed, but the delivery was rejected (changed UI / subset): no cached result
    _settled(deferred.task, signal)()
    run_queued(deferred.timer)
    deferred.dock.launchTaskEvent.assert_not_called()
    deferred.warning.assert_called_once()
    assert 'not launched' in deferred.warning.call_args.args[0]
    assert deferred.dock._pending_remote_filter is None


def test_a_filter_follows_an_equivalent_replacement_read(deferred):
    """M1: the read it waits for is replaced by one of the same selection (pick debounce)."""
    replacement = _task()
    deferred.slot.task = replacement
    _settled(deferred.task, 'taskTerminated')()
    run_queued(deferred.timer)
    deferred.warning.assert_not_called()
    deferred.dock.launchTaskEvent.assert_not_called()
    deferred.controller._remote_selection_result = ('requested', [], '"id" IN (5)')
    deferred.slot.task = None
    _settled(replacement)()
    run_queued(deferred.timer)
    deferred.dock.launchTaskEvent.assert_called_once_with(False, 'filter')
    deferred.warning.assert_not_called()


def test_a_newer_launch_drops_the_queued_filter_silently(deferred):
    deferred.dock._pending_remote_filter = None  # launchTaskEvent of another click / task
    deferred.controller._remote_selection_result = ('requested', [], '')
    _settled(deferred.task)()
    run_queued(deferred.timer)
    deferred.dock.launchTaskEvent.assert_not_called()
    deferred.warning.assert_not_called()


def test_new_filter_click_invalidates_an_already_queued_resume(deferred):
    deferred.controller._remote_selection_result = ('requested', [], '')
    _settled(deferred.task)()
    tree = ast.parse(PATH.read_text())
    launcher = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'launchTaskEvent')
    # Execute the actual launcher prefix, stopping before its provider reads.
    # The initial docstring and point-cloud delegation are part of that prefix.
    stop = next(index for index, node in enumerate(launcher.body)
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Attribute)
                        and target.attr == '_pending_remote_filter' for target in node.targets))
    launcher.body = launcher.body[:stop + 1]
    namespace = {}
    exec(compile(ast.Module(body=[launcher], type_ignores=[]), str(PATH), 'exec'), namespace)
    deferred.dock._controller_integration = None
    MethodType(namespace['launchTaskEvent'], deferred.dock)(False, 'filter')
    run_queued(deferred.timer)
    deferred.dock.launchTaskEvent.assert_not_called()
    deferred.warning.assert_not_called()


def _launcher_prefix():
    """launchTaskEvent up to its service pre-check, then 'proceeds' instead of the task launch."""
    import builtins
    tree = ast.parse(PATH.read_text())
    launcher = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'launchTaskEvent')
    stop = next(index for index, node in enumerate(launcher.body)
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Attribute)
                        and target.attr == '_pending_remote_filter' for target in node.targets))
    launcher.body = launcher.body[:stop + 2] + ast.parse("return 'proceeds'").body
    original_import = builtins.__import__

    def import_capability(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: False)
        return original_import(module, globals, locals, fromlist, level)

    namespace = {'__builtins__': dict(vars(builtins), __import__=import_capability)}
    exec(compile(ast.Module(body=[launcher], type_ignores=[]), str(PATH), 'exec'), namespace)
    return namespace['launchTaskEvent']


@pytest.mark.parametrize('refused,waiting,expected', [
    (True, False, None),           # H2: refused selection, nothing launched
    (False, True, None),           # its read is in progress: deferred
    (False, False, 'proceeds'),    # final selection: launched now
])
def test_service_filter_launch_waits_only_for_its_own_selection(refused, waiting, expected):
    slot = SimpleNamespace(task=_task())   # a read may run for another (older) selection
    controller = SimpleNamespace(_selection_query=slot)

    def read():
        controller._remote_selection_refused = refused
        controller._remote_selection_waiting = waiting

    controller.get_current_features = MagicMock(side_effect=read)
    controller.remote_filter_refused = MagicMock(return_value=False)
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, _controller_integration=None,
                           _defer_remote_filter=MagicMock())
    assert MethodType(_launcher_prefix(), dock)(False, 'filter') == expected
    assert dock._defer_remote_filter.called is waiting


def test_flags_of_an_earlier_read_neither_refuse_nor_defer_a_filter():
    """get_current_features may return before _remote_features (widgets not ready): no stale verdict."""
    slot = SimpleNamespace(task=_task())
    controller = SimpleNamespace(get_current_features=MagicMock(), _remote_selection_refused=True,
                                 _remote_selection_waiting=True, _selection_query=slot,
                                 remote_filter_refused=MagicMock(return_value=False))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, _controller_integration=None,
                           _defer_remote_filter=MagicMock())
    assert MethodType(_launcher_prefix(), dock)(False, 'filter') == 'proceeds'
    dock._defer_remote_filter.assert_not_called()


@pytest.mark.parametrize('name', ['get_current_features', '_fallback_get_current_features'])
@pytest.mark.parametrize('controller_available', [True, False])
def test_empty_remote_selection_never_enters_legacy_synchronous_fallback(name, controller_available):
    import builtins
    tree = ast.parse(PATH.read_text())
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == name)
    original_import = builtins.__import__

    def import_capability(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: False)
        return original_import(module, globals, locals, fromlist, level)

    warning = MagicMock()
    namespace = {'__builtins__': dict(vars(builtins), __import__=import_capability), 'show_warning': warning}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    controller = SimpleNamespace(get_current_features=MagicMock(return_value=([], 'pending expression')))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller if controller_available else None,
                           _is_layer_valid=lambda: True, tr=lambda text: text,
                           _fallback_get_current_features=MagicMock(side_effect=AssertionError('GUI read')))
    expected = ([], 'pending expression') if controller_available else ([], '')
    assert MethodType(namespace[name], dock)() == expected
    assert warning.called is not controller_available
    dock._fallback_get_current_features.assert_not_called()


def test_favorite_features_never_outlive_the_call_on_a_service():
    """H3: kept, they were used later by a filter of another layer (another CRS, another selection)."""
    import builtins
    tree = ast.parse(PATH.read_text())
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == 'get_current_features')
    original_import = builtins.__import__

    def import_capability(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: False)
        return original_import(module, globals, locals, fromlist, level)

    namespace = {'__builtins__': dict(vars(builtins), __import__=import_capability), 'show_warning': MagicMock(),
                 'logger': MagicMock()}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    restored = [MagicMock()]
    controller = SimpleNamespace(get_current_features=MagicMock(return_value=([], '')))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, tr=lambda text: text,
                           _restored_task_features=restored)
    assert MethodType(namespace['get_current_features'], dock)() == ([], '')
    assert dock._restored_task_features is None


def test_service_identify_flashes_through_the_controller_without_reading_the_layer():
    """M4: flashFeatureIds read the service again on the GUI thread; the read geometries are flashed instead."""
    import builtins
    tree = ast.parse(PATH.read_text())
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == 'exploring_identify_clicked')
    original_import = builtins.__import__

    def import_capability(module, globals=None, locals=None, fromlist=(), level=0):
        if module.endswith('source_capability_probe'):
            return SimpleNamespace(counts_cheaply=lambda layer: False)
        return original_import(module, globals, locals, fromlist, level)

    namespace = {'__builtins__': dict(vars(builtins), __import__=import_capability), 'logger': MagicMock()}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    controller = SimpleNamespace(identify_remote_selection=MagicMock())
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, _coverage_action=lambda name: False,
                           _is_layer_valid=lambda: True, iface=MagicMock(),
                           get_current_features=MagicMock(side_effect=AssertionError('read')),
                           _fallback_get_current_features=MagicMock(side_effect=AssertionError('read')))
    MethodType(namespace['exploring_identify_clicked'], dock)()
    controller.identify_remote_selection.assert_called_once_with()
    dock.iface.mapCanvas.return_value.flashFeatureIds.assert_not_called()


def test_a_service_filter_without_a_key_it_can_send_is_refused_at_launch():
    """H2: refused (message in remote_filter_refused), no task, nothing deferred."""
    slot = SimpleNamespace(task=_task())
    controller = SimpleNamespace(get_current_features=MagicMock(), _selection_query=slot,
                                 remote_filter_refused=MagicMock(return_value=True))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, _controller_integration=None,
                           _defer_remote_filter=MagicMock())
    assert MethodType(_launcher_prefix(), dock)(False, 'filter') is None
    dock._defer_remote_filter.assert_not_called()
    controller.get_current_features.assert_not_called()   # refused before any read


def test_a_service_filter_whose_read_selection_has_null_keys_is_refused_at_launch():
    slot = SimpleNamespace(task=None)
    controller = SimpleNamespace(get_current_features=MagicMock(), _selection_query=slot,
                                 remote_filter_refused=MagicMock(side_effect=lambda read=False: read))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller, _controller_integration=None,
                           _defer_remote_filter=MagicMock())
    assert MethodType(_launcher_prefix(), dock)(False, 'filter') is None
    controller.get_current_features.assert_called_once_with()


def test_a_filter_replayed_without_launch_rechecks_the_service_keys():
    """The task builder (manage_task retries without launchTaskEvent) refuses the same selection."""
    import sys
    import types
    path = Path(__file__).resolve().parents[3] / 'adapters' / 'task_builder.py'
    tree = ast.parse(path.read_text())
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == 'get_and_validate_features')
    core = types.ModuleType('qgis.core')
    core.QgsMessageLog, core.Qgis = MagicMock(), MagicMock()
    utils = types.ModuleType('qgis.utils')
    utils.iface = MagicMock()
    saved = {name: sys.modules.get(name) for name in ('qgis.core', 'qgis.utils')}
    sys.modules.update({'qgis.core': core, 'qgis.utils': utils})
    try:
        namespace = {'logger': MagicMock(), 'QCoreApplication': MagicMock()}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        controller = SimpleNamespace(remote_filter_blocked=MagicMock(return_value=True))
        dock = SimpleNamespace(get_current_features=lambda: ([MagicMock()], '"id" IN (NULL)'),
                               _exploring_ctrl=controller, current_exploring_groupbox='single_selection')
        with pytest.raises(ValueError):
            MethodType(namespace['get_and_validate_features'], SimpleNamespace(_dockwidget=dock))('filter')
        controller.remote_filter_blocked.assert_called_once_with()
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
