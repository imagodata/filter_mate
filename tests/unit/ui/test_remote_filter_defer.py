"""A deferred service filter must use only the selection requested by its click."""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

PATH = Path(__file__).resolve().parents[3] / 'filter_mate_dockwidget.py'


@pytest.fixture
def deferred():
    tree = ast.parse(PATH.read_text())
    node = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == '_defer_remote_filter')
    timer = MagicMock()
    namespace = {'QTimer': timer}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(PATH), 'exec'), namespace)
    slot = SimpleNamespace(generation=1, accepts=lambda generation: generation == slot.generation,
                           task=SimpleNamespace(error=None, taskCompleted=MagicMock()))
    controller = SimpleNamespace(_remote_ui_revision=lambda: 'initial',
                                 _remote_selection_pending='requested',
                                 _remote_selection_result=('requested', []))
    dock = SimpleNamespace(current_layer=object(), _exploring_ctrl=controller,
                           launchTaskEvent=MagicMock())
    MethodType(namespace['_defer_remote_filter'], dock)(slot)
    completed = slot.task.taskCompleted.connect.call_args.args[0]
    return dock, controller, slot, timer, completed


def finish(timer, completed):
    completed()
    if timer.singleShot.called:
        timer.singleShot.call_args.args[1]()


def test_completed_selection_resumes_filter(deferred):
    dock, _, _, timer, completed = deferred
    finish(timer, completed)
    dock.launchTaskEvent.assert_called_once_with(False, 'filter')
    assert dock._pending_remote_filter is None


@pytest.mark.parametrize('change', ['layer', 'expression', 'generation', 'cancel', 'cache', 'failure'])
def test_stale_or_failed_selection_cannot_resume_filter(deferred, change):
    dock, controller, slot, timer, completed = deferred
    if change == 'layer':
        dock.current_layer = object()
    elif change == 'expression':
        controller._remote_ui_revision = lambda: 'edited'
    elif change == 'generation':
        slot.generation += 1
    elif change == 'cancel':
        dock._pending_remote_filter = None
    elif change == 'cache':
        controller._remote_selection_result = ('another request', [])
    else:
        slot.task.error = RuntimeError('read failed')
    finish(timer, completed)
    dock.launchTaskEvent.assert_not_called()
