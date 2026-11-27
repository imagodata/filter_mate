"""Owned cursor lifetimes and plugin-only cursor policy on real Qt widgets."""
import importlib

import pytest

from .widgets.test_agent_panel_ux_qt import QtCore, QtWidgets, _APP, _PKG, real_qt_icons  # noqa: F401

cursors = importlib.import_module(_PKG + '.ui.cursors')
Qt = QtCore.Qt
pytestmark = pytest.mark.unit


@pytest.fixture
def controls(real_qt_icons):
    root = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(root)
    button, edit = QtWidgets.QPushButton('Run', root), QtWidgets.QLineEdit(root)
    text, combo = QtWidgets.QPlainTextEdit(root), QtWidgets.QComboBox(root)
    drag = QtWidgets.QWidget(root)
    drag.setCursor(Qt.CursorShape.SizeHorCursor)
    for widget in (button, edit, text, combo, drag):
        layout.addWidget(widget)
    policy = cursors.install_cursor_policy(root)
    root.show()
    _APP.processEvents()
    yield root, policy, button, edit, text, combo, drag
    policy.close()
    root.close()
    root.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_buttons_text_and_special_controls_have_the_right_cursor(controls):
    root, policy, button, edit, text, combo, drag = controls
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    button.setEnabled(False)
    assert button.cursor().shape() == Qt.CursorShape.ArrowCursor
    button.setEnabled(True)
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert edit.cursor().shape() == Qt.CursorShape.IBeamCursor
    assert text.viewport().cursor().shape() == Qt.CursorShape.IBeamCursor
    assert combo.cursor().shape() == Qt.CursorShape.PointingHandCursor
    combo.setEditable(True)
    policy.apply(combo)
    assert combo.lineEdit().cursor().shape() == Qt.CursorShape.IBeamCursor
    assert drag.cursor().shape() == Qt.CursorShape.SizeHorCursor


def test_late_controls_are_covered_without_changing_other_windows(controls):
    root, policy, *_ = controls
    later = QtWidgets.QPushButton('Late', root)
    later.show()
    _APP.processEvents()
    assert later.cursor().shape() == Qt.CursorShape.PointingHandCursor
    foreign = QtWidgets.QPushButton('Other plugin')
    foreign.setCursor(Qt.CursorShape.CrossCursor)
    foreign.show()
    _APP.processEvents()
    assert foreign.cursor().shape() == Qt.CursorShape.CrossCursor
    foreign.close()
    foreign.deleteLater()


@pytest.mark.parametrize('reverse', [False, True])
def test_overlapping_cursors_can_finish_in_either_order(controls, reverse):
    button = controls[2]
    first = cursors.CursorLease([button])
    second = cursors.CursorLease([button], Qt.CursorShape.WaitCursor)
    assert button.cursor().shape() == Qt.CursorShape.WaitCursor
    if reverse:
        second.close()
        assert button.cursor().shape() == Qt.CursorShape.BusyCursor
        first.close()
    else:
        first.close()
        assert button.cursor().shape() == Qt.CursorShape.WaitCursor
        second.close()
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    first.close()
    second.close()


def test_another_owners_explicit_cursor_wins_and_inherited_cursors_follow_the_current_parent(controls):
    root, _, *rest = controls
    child = QtWidgets.QWidget(root)
    root.setCursor(Qt.CursorShape.CrossCursor)
    assert not child.testAttribute(Qt.WidgetAttribute.WA_SetCursor)
    lease = cursors.CursorLease([child])
    root.setCursor(Qt.CursorShape.SizeAllCursor)
    lease.close()
    assert not child.testAttribute(Qt.WidgetAttribute.WA_SetCursor)
    assert child.cursor().shape() == Qt.CursorShape.SizeAllCursor
    lease = cursors.CursorLease([child])
    child.setCursor(Qt.CursorShape.CrossCursor)
    lease.close()
    assert child.cursor().shape() == Qt.CursorShape.CrossCursor


def test_errors_and_plugin_busy_states_do_not_pop_another_plugins_global_override(controls):
    root, _, button, *_ = controls
    _APP.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        with pytest.raises(ValueError):
            with cursors.CursorLease([root, button]):
                assert _APP.overrideCursor().shape() == Qt.CursorShape.WaitCursor
                raise ValueError('failed read')
        assert _APP.overrideCursor().shape() == Qt.CursorShape.WaitCursor
        assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    finally:
        _APP.restoreOverrideCursor()


def test_busy_keys_are_idempotent_and_restore_the_latest_enabled_state(controls):
    button = controls[2]
    cursors.set_widget_busy(button, True)
    cursors.set_widget_busy(button, True)
    assert len(button._filtermate_cursor_state.leases) == 1
    button.setEnabled(False)
    assert button.cursor().shape() == Qt.CursorShape.BusyCursor
    cursors.set_cursor_intent(button, Qt.CursorShape.PointingHandCursor)  # a theme refresh during the operation
    assert button.cursor().shape() == Qt.CursorShape.BusyCursor
    cursors.set_widget_busy(button, False)
    assert button.cursor().shape() == Qt.CursorShape.ArrowCursor
    button.setEnabled(True)
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor


def test_compound_expression_loading_covers_children_and_restores_editor_intent(controls):
    root, _, _, edit, *_ = controls
    cursors.set_widget_busy(root, True)
    assert edit.cursor().shape() == Qt.CursorShape.BusyCursor
    cursors.set_widget_busy(root, False)
    assert edit.cursor().shape() == Qt.CursorShape.IBeamCursor


def test_plugin_dialogs_outside_the_dock_receive_the_policy(controls):
    root, policy, *_ = controls
    dialog_class = type('PluginDialog', (QtWidgets.QDialog,), {'__module__': _PKG + '.ui.dialogs.example'})
    dialog = dialog_class()
    button = QtWidgets.QPushButton('Apply', dialog)
    dialog.show()
    _APP.processEvents()
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    dialog.close()
    dialog.deleteLater()


def test_unload_restores_owned_cursors_and_completion_after_widget_deletion_is_safe(controls):
    root, policy, button, *_ = controls
    lease = cursors.CursorLease([button])
    policy.close()
    assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
    lease.close()
    orphan = QtWidgets.QPushButton('Removed', root)
    lease = cursors.CursorLease([orphan])
    orphan.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    lease.close()
