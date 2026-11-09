# -*- coding: utf-8 -*-
"""
Combo boxes and spin boxes of the dock answer the wheel only once they have the focus.

The groups of the dock scroll. A wheel turned over them while a list or a number passed under the
pointer changed it, without a click: the feature picked in the single selection, which is the source
geometry of the next filter, moved from 2 to 5 that way. The event now goes on to the parent, which
scrolls.
"""
from qgis.PyQt.QtCore import QEvent, QObject
from qgis.PyQt.QtWidgets import QAbstractSpinBox, QApplication, QComboBox

_GUARDED = 'fm_wheel_guarded'


def has_focus_within(widget, focus_widget) -> bool:
    """``focus_widget`` is ``widget`` or inside it (the line edit of an editable combo box)."""
    return focus_widget is not None and (focus_widget is widget or widget.isAncestorOf(focus_widget))


class _WheelNeedsFocus(QObject):
    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() == QEvent.Type.Wheel and not has_focus_within(watched, QApplication.focusWidget()):
            event.ignore()  # the parent gets it: Qt hands an ignored wheel event on
            return True
        return False


def guard_input_wheel(root) -> None:
    """Install the guard on the inputs under ``root``, once each (new ones need another call)."""
    guard = root.findChild(_WheelNeedsFocus)
    if guard is None:
        guard = _WheelNeedsFocus(root)
    for input_class in (QComboBox, QAbstractSpinBox):
        for widget in root.findChildren(input_class):
            if not widget.property(_GUARDED):
                widget.installEventFilter(guard)
                widget.setProperty(_GUARDED, True)
