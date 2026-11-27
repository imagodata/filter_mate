"""Bounded feature-id reads on worker snapshots, with a responsive synchronous tool API."""


def read_feature_ids(layer, expression, limit, *, protect_selection=False, timeout_ms=30000):
    return _read(layer, expression, limit, protect_selection=protect_selection, timeout_ms=timeout_ms)


def read_feature_geometries(layer, expression, limit):
    """Return ID/geometry value pairs, so flashing does not ask the live provider for geometries again."""
    return _read(layer, expression, limit, geometries=True)


def _read(layer, expression, limit, *, protect_selection=False, timeout_ms=30000, geometries=False):
    """Read at most ``limit`` IDs without iterating the live layer on the GUI thread.

    Changes to the source or selection invalidate the read. Timeout/Stop return without applying a
    partial selection, even if a provider is still winding down its canceled snapshot iterator.
    """
    from qgis.core import QgsApplication, QgsFeatureRequest, QgsGeometry, QgsProject
    from qgis.PyQt.QtCore import QEventLoop, QTimer
    from .async_query import SnapshotQueryTask, _watcher, worker_expression_context
    from ..agent.bounded_http import on_abort

    context = worker_expression_context(layer, expression)
    if context is None:
        raise ValueError('this expression cannot be evaluated safely on a layer snapshot')
    request = QgsFeatureRequest().setFilterExpression(expression).setExpressionContext(context)
    request.setNoAttributes().setLimit(limit)
    loop, timer = QEventLoop(), QTimer()
    state = {'settled': False, 'closed': False, 'reason': '', 'result': None}

    def compute(task):
        if not geometries:
            return [feature.id() for feature in task.features(request)]
        rows = []
        for feature in task.features(request):
            geometry = feature.geometry()
            rows.append((feature.id(), None if geometry.isNull() or geometry.isEmpty() else QgsGeometry(geometry)))
        return rows

    def deliver(ids):
        state['result'] = ids

    task = SnapshotQueryTask('FilterMate: reading matching feature IDs', layer, compute, deliver)

    def settled():
        state['settled'] = True
        if not state['closed']:
            loop.quit()

    def cancel(reason):
        if state['closed'] or state['settled']:
            return
        state['reason'] = reason
        task.cancel()
        loop.quit()

    watch = _watcher(lambda: cancel('the layer or its selection changed while it was being read; retry'))
    for name in ('willBeDeleted', 'subsetStringChanged', 'dataChanged', 'geometryChanged',
                 'updatedFields', 'crsChanged', 'dataSourceChanged') + (('selectionChanged',) if protect_selection else ()):
        signal = getattr(layer, name, None)
        if signal is not None:
            signal.connect(watch.changed)
    QgsProject.instance().cleared.connect(watch.changed)
    task.when_settled(settled)
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: cancel('feature read timed out; narrow the expression or retry'))
    forget_abort = on_abort(lambda: cancel('stopped'))
    try:
        QgsApplication.taskManager().addTask(task)
        timer.start(timeout_ms)
        if not state['settled'] and not state['reason']:
            loop.exec()
        if state['reason']:
            raise ValueError(state['reason'])
        if task.error is not None:
            raise ValueError(f'the layer could not be read: {task.error}')
        if state['result'] is None:
            raise ValueError('the feature read was canceled')
        return state['result']
    finally:
        state['closed'] = True
        timer.stop()
        forget_abort()
        watch.deleteLater()  # QObject destruction releases connections without dereferencing a deleted layer
