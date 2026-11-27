"""Cursor intent and owned busy states for FilterMate widgets; never alter QGIS' override stack."""
import weakref

_STATE_CLASS = None
_POLICY_CLASS = None


def _state(widget):
    state = getattr(widget, '_filtermate_cursor_state', None)
    return state if getattr(state, '_filtermate_cursor_state_marker', False) is True else None


def _state_class():
    global _STATE_CLASS
    if _STATE_CLASS is not None:
        return _STATE_CLASS
    from qgis.PyQt.QtCore import QObject, QEvent, Qt
    from qgis.PyQt.QtGui import QCursor

    class CursorState(QObject):
        _filtermate_cursor_state_marker = True

        def __init__(self, widget):
            super().__init__(widget)
            self.widget = weakref.ref(widget)
            self.baseline = (widget.testAttribute(Qt.WidgetAttribute.WA_SetCursor), QCursor(widget.cursor()))
            self.leases = {}
            self.writing, self.external = False, False
            widget.installEventFilter(self)

        def eventFilter(self, watched, event):  # noqa: N802 - Qt name
            if event.type() == QEvent.Type.CursorChange and not self.writing and self.leases:
                self.external = True  # a map tool, user or another owner changed this widget's cursor
            return False

        def acquire(self, token, shape):
            widget = self.widget()
            if self.external:
                self.leases.clear()  # an older busy request must not regain ownership after a newer one ends
                self.baseline = (widget.testAttribute(Qt.WidgetAttribute.WA_SetCursor), QCursor(widget.cursor()))
                self.external = False
            self.leases[token] = QCursor(shape)
            self._write(self.leases[token])

        def _write(self, cursor):
            self.writing = True
            try:
                widget = self.widget()
                widget.unsetCursor() if cursor is None else widget.setCursor(cursor)
            finally:
                self.writing = False

        def release(self, token):
            if token not in self.leases:
                return
            self.leases.pop(token)
            if self.leases:
                if not self.external:
                    self._write(next(reversed(self.leases.values())))
                return
            widget = self.widget()
            if not self.external:
                explicit, cursor = self.baseline
                self._write(cursor if explicit else None)
            widget.removeEventFilter(self)
            widget._filtermate_cursor_state = None
            self.deleteLater()

    _STATE_CLASS = CursorState
    return _STATE_CLASS


class CursorLease:
    """A widget-scoped busy cursor, safe for overlapping operations and out-of-order completion."""

    def __init__(self, widgets=(), shape=None):
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QWidget
        self.handles = []
        shape = Qt.CursorShape.BusyCursor if shape is None else shape
        for widget in widgets:
            try:
                native = isinstance(widget, QWidget)
            except TypeError:  # lightweight hosts without Qt widgets
                native = False
            if not native:
                continue
            state = _state(widget)
            if state is None:
                state = _state_class()(widget)
                widget._filtermate_cursor_state = state
            token = object()
            state.acquire(token, shape)
            self.handles.append((widget, token))  # retain the Python wrapper until restoration; Qt still owns deletion

    def close(self):
        handles, self.handles = self.handles, []
        for widget, token in handles:
            try:
                state = _state(widget)
                if state is not None:
                    state.release(token)
            except RuntimeError:  # the owning widget was deleted while its operation ended
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def set_cursor_intent(widget, shape):
    """Set the normal cursor while preserving an active, owned busy cursor."""
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtGui import QCursor
    if not widget.isEnabled():
        shape = Qt.CursorShape.ArrowCursor
    state = _state(widget)
    if state is not None and state.leases:
        if not state.external:
            state.baseline = (True, QCursor(shape))
    else:
        widget.setCursor(QCursor(shape))


def set_widget_busy(widget, active, key='expression'):
    leases = getattr(widget, '_filtermate_busy_leases', None)
    if not isinstance(leases, dict):
        leases = {}
        widget._filtermate_busy_leases = leases
    if active and key not in leases:
        from qgis.PyQt.QtWidgets import QWidget
        leases[key] = CursorLease([widget, *widget.findChildren(QWidget)])
    elif not active:
        lease = leases.pop(key, None)
        if lease is not None:
            lease.close()


def install_cursor_policy(root):
    """Cover existing/dynamic plugin controls and plugin dialogs, preserving native map/resize cursors."""
    global _POLICY_CLASS
    from qgis.PyQt.QtCore import QObject, QEvent, Qt
    from qgis.PyQt.QtWidgets import (QApplication, QAbstractButton, QComboBox, QLabel, QLineEdit,
                                    QPlainTextEdit, QTextEdit, QWidget)
    try:
        if not isinstance(root, QWidget):
            return None
    except TypeError:
        return None
    current = getattr(root, '_filtermate_cursor_policy', None)
    if current is not None and current.active:
        return current
    if _POLICY_CLASS is None:
        class CursorPolicy(QObject):
            def __init__(self, owner):
                super().__init__(owner)
                self.root = weakref.ref(owner)
                self.package = __name__.rsplit('.ui.', 1)[0]
                self.active = True
                QApplication.instance().installEventFilter(self)

            def owns(self, widget):
                owner = self.root()
                while widget is not None:
                    if widget is owner or type(widget).__module__.startswith(self.package + '.'):
                        return True
                    widget = widget.parentWidget()
                return False

            def apply(self, widget):
                if not self.active or not isinstance(widget, QWidget) or not self.owns(widget):
                    return
                if isinstance(widget, QAbstractButton):
                    shape = Qt.CursorShape.PointingHandCursor if widget.isEnabled() else Qt.CursorShape.ArrowCursor
                elif isinstance(widget, QLineEdit):
                    shape = Qt.CursorShape.IBeamCursor if widget.isEnabled() else Qt.CursorShape.ArrowCursor
                elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
                    self.apply_text_viewport(widget)
                    return
                elif isinstance(widget, QComboBox):
                    shape = (Qt.CursorShape.PointingHandCursor if widget.isEnabled() and not widget.isEditable()
                             else Qt.CursorShape.ArrowCursor)
                elif isinstance(widget, QLabel) and '<a ' in widget.text().lower() and bool(
                        widget.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByMouse):
                    shape = Qt.CursorShape.PointingHandCursor if widget.isEnabled() else Qt.CursorShape.ArrowCursor
                else:
                    return  # sliders, drag handles, splitters and map tools keep their native cursors
                set_cursor_intent(widget, shape)

            @staticmethod
            def apply_text_viewport(widget):
                set_cursor_intent(widget.viewport(), Qt.CursorShape.IBeamCursor if widget.isEnabled()
                                  else Qt.CursorShape.ArrowCursor)

            def eventFilter(self, watched, event):  # noqa: N802 - Qt name
                if event.type() in (QEvent.Type.Show, QEvent.Type.EnabledChange, QEvent.Type.Enter, QEvent.Type.StyleChange):
                    self.apply(watched)
                elif event.type() == QEvent.Type.ChildPolished:
                    self.apply(event.child())
                return False

            def close(self):
                if not self.active:
                    return
                self.active = False
                application = QApplication.instance()
                if application is not None:
                    application.removeEventFilter(self)
                    for widget in application.allWidgets():
                        if self.owns(widget):
                            state = _state(widget)
                            if state is not None:
                                for token in list(state.leases):
                                    state.release(token)
                self.deleteLater()

        _POLICY_CLASS = CursorPolicy
    policy = _POLICY_CLASS(root)
    root._filtermate_cursor_policy = policy
    policy.apply(root)
    for widget in root.findChildren(QWidget):
        policy.apply(widget)
    return policy
