"""show_warning(message, title='FilterMate'): the streaming warnings passed (title, message).

infrastructure.feedback.show_warning pushes ``(title, message)`` to the QGIS
message bar: swapped, the bar showed "<long text>: Selection". Every call of
the modules below must give the message first (review of #193).
"""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FILES = ('ui/controllers/exploring_controller.py', 'adapters/qgis/async_query.py', 'ui/widgets/custom_widgets.py')
TITLES = {'FilterMate', 'Selection', 'Zoom', 'Values', 'Read failed', 'Expression Evaluation', 'Filter',
          'FilterMate - Identify'}


def _text(node):
    """The literal text of a string, a tr() / translate() call or its .format(): None when unknown."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call):
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr == 'format':
            return _text(function.value)
        if isinstance(function, ast.Attribute) and function.attr in ('tr', 'translate') and node.args:
            return _text(node.args[-1])
    if isinstance(node, ast.IfExp):
        return _text(node.body)
    return None


def _calls(path):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'show_warning'
                and node.args):
            yield node


@pytest.mark.parametrize('path', FILES)
def test_warnings_give_their_message_first(path):
    swapped = []
    for call in _calls(path):
        first = _text(call.args[0])
        second = _text(call.args[1]) if len(call.args) > 1 else None
        if first in TITLES or (second is not None and second not in TITLES):
            swapped.append('{}:{} show_warning({!r}, {!r})'.format(path, call.lineno, first, second))
    assert not swapped, '\n'.join(swapped)


def test_the_fallback_has_the_feedback_signature():
    tree = ast.parse((ROOT / FILES[0]).read_text(encoding='utf-8'))
    fallback = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'show_warning')
    assert [arg.arg for arg in fallback.args.args] == ['message', 'title']
