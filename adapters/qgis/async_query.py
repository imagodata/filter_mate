"""Cancellable reads from a layer snapshot; delivery always runs on the GUI thread."""
import logging
import time

from qgis.core import QgsFeedback, QgsTask, QgsVectorLayerFeatureSource

logger = logging.getLogger(__name__)


class UnsafeExpressionError(ValueError):
    """A source expression would access live project objects from a worker."""


class SnapshotQueryTask(QgsTask):
    """Run a read against an independent snapshot, never against the live layer."""

    REQUEST_TIMEOUT_MS = 30000

    def __init__(self, description, layer, compute, deliver):
        super().__init__(description, QgsTask.Flag.CanCancel)
        fields = layer.fields()
        self._unsafe_virtual_fields = False
        for index in range(len(fields)):
            expression = layer.expressionField(index)
            if isinstance(expression, str) and expression and not remote_expression_is_safe(expression, fields):
                self._unsafe_virtual_fields = True
                break
        self.source = QgsVectorLayerFeatureSource(layer)
        self.feedback = QgsFeedback()
        self.compute = compute
        self.deliver = deliver
        self.result = None
        self.error = None
        self.setDependentLayers([layer])

    def features(self, request, source=None):
        """Read with feedback, a provider timeout, and worker-owned iterator cleanup.

        Cancellation is cooperative: Python feedback cannot interrupt every
        blocked provider fetch, and some providers renew or ignore timeouts.
        Request a timeout and reject slow returns instead of presenting a
        potentially partial extent or selection as complete.
        """
        if self.isCanceled():
            return
        request.setFeedback(self.feedback)
        request.setTimeout(self.REQUEST_TIMEOUT_MS)
        started = time.monotonic()
        iterator = (self.source if source is None else source).getFeatures(request)
        try:
            for feature in iterator:
                if self.isCanceled():
                    return
                # A valid matching feature may arrive after a long client-side
                # expression scan. Its latency alone is not a provider timeout.
                yield feature
                started = time.monotonic()
            if not self.isCanceled() and time.monotonic() - started >= self.REQUEST_TIMEOUT_MS / 1000 * 0.9:
                raise TimeoutError('Feature fetch timed out')
        finally:
            iterator.close()

    def cancel(self):
        self.feedback.cancel()
        super().cancel()

    def run(self):
        try:
            if self.isCanceled():
                return False
            if self._unsafe_virtual_fields:
                raise UnsafeExpressionError('Unsafe virtual field expression')
            self.result = self.compute(self)
            return not self.isCanceled()
        except Exception as exc:
            self.error = exc
            return False

    def finished(self, success):
        try:
            if success and not self.isCanceled():
                self.deliver(self.result)
            elif self.error is not None:
                logger.warning("Snapshot query failed (%s)", type(self.error).__name__)
        except Exception as exc:
            self.error = exc
            logger.warning("Snapshot delivery failed (%s)", type(exc).__name__)
        finally:
            self.deliver = None
            self.compute = None


def collect_extent(task, request):
    """Return the exact extent, including points, without a preliminary count."""
    from qgis.core import QgsRectangle
    extent = None
    for feature in task.features(request):
        if feature.hasGeometry() and not feature.geometry().isEmpty():
            bbox = feature.geometry().boundingBox()
            if extent is None:
                extent = QgsRectangle(bbox)
            else:
                extent.combineExtentWith(bbox)
    return extent


class QuerySlot:
    """Own one generation of a UI read, cancelling the previous one."""

    def __init__(self):
        self.generation = 0
        self.task = None
        self.loading = None

    def cancel(self, *args, reset_loading=True):
        self.generation += 1
        if self.task is not None:
            self.task.cancel()
            self.task = None
        if self.loading is not None and reset_loading:
            try:
                self.loading(False)
            except RuntimeError:
                pass
            self.loading = None

    def replace(self, task, keep_loading=False):
        self.cancel(reset_loading=not keep_loading)
        self.task = task
        return self.generation

    def accepts(self, generation):
        return self.generation == generation


def submit_query(owner, attribute, layer, description, compute, deliver, loading=None, dependencies=None):
    """Submit a guarded read, bound to the owner and layer lifetimes.

    `loading` receives False on success, error or cancellation, but an older
    generation can never clear the loading state of a newer request.
    """
    from qgis.core import QgsApplication
    slot = getattr(owner, attribute, None)
    if slot is None:
        slot = QuerySlot()
        setattr(owner, attribute, slot)
        destroyed = getattr(owner, 'destroyed', None)
        if destroyed is not None:
            destroyed.connect(slot.cancel)
    fingerprint = (layer.id(), layer.source(), layer.subsetString())

    def complete(result):
        if not slot.accepts(generation):
            return
        try:
            if fingerprint != (layer.id(), layer.source(), layer.subsetString()):
                return
            deliver(result)
        except RuntimeError:
            # The C++ owner / layer may have been destroyed while delivery was queued.
            return

    task = SnapshotQueryTask(description, layer, compute, complete)
    dependent_layers = list(dependencies) if dependencies is not None else [layer]
    task.setDependentLayers(dependent_layers)
    # Replacing the same UI read keeps its loading lease. Re-polishing the
    # widget twice per keystroke (idle -> busy) both flickers and blocks Qt.
    keep_loading = loading is not None and slot.loading == loading
    generation = slot.replace(task, keep_loading=keep_loading)
    slot.loading = loading
    connections = []

    def invalidate(*args):
        if slot.accepts(generation):
            slot.cancel()

    for dependent in dependent_layers:
        for name in ('willBeDeleted', 'subsetStringChanged', 'dataChanged', 'geometryChanged',
                     'updatedFields', 'crsChanged', 'dataSourceChanged'):
            signal = getattr(dependent, name, None)
            if signal is not None:
                signal.connect(invalidate)
                connections.append((signal, invalidate))

    def settled():
        for signal, callback in connections:
            try:
                signal.disconnect(callback)
            except (RuntimeError, TypeError):
                pass
        if slot.accepts(generation):
            slot.task = None
            slot.loading = None
            if loading is not None:
                loading(False)
            if task.error is not None:
                from qgis.PyQt.QtCore import QCoreApplication
                from ...infrastructure.feedback import show_warning
                if isinstance(task.error, UnsafeExpressionError):
                    message = QCoreApplication.translate('FilterMate', 'This expression cannot be evaluated safely for a service.')
                else:
                    message = QCoreApplication.translate('FilterMate', 'The service could not be read. Please retry.')
                show_warning(QCoreApplication.translate('FilterMate', 'Read failed'), message)

    task.taskCompleted.connect(settled)
    task.taskTerminated.connect(settled)
    if loading is not None and not keep_loading:
        loading(True)
    QgsApplication.taskManager().addTask(task)
    return task


def queue_union_zoom(layers, canvas, expected_token=None, grow_by=0):
    """Compute a filtered union in canvas CRS without GUI-thread provider reads."""
    from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsProject, QgsRectangle
    from ..auto_zoom import current_subset_change_token
    layers = list(layers)
    context = QgsProject.instance().transformContext()
    target_crs = canvas.mapSettings().destinationCrs()
    snapshots = []
    for layer in layers:
        snapshots.append((QgsVectorLayerFeatureSource(layer),
                          QgsCoordinateTransform(layer.crs(), target_crs, context),
                          (layer.id(), layer.source(), layer.subsetString())))
    request = QgsFeatureRequest().setNoAttributes()

    def compute(task):
        union = None
        for source, transform, fingerprint in snapshots:
            if task.isCanceled():
                return None
            extent = None
            for feature in task.features(request, source):
                if feature.hasGeometry() and not feature.geometry().isEmpty():
                    bbox = feature.geometry().boundingBox()
                    if extent is None:
                        extent = QgsRectangle(bbox)
                    else:
                        extent.combineExtentWith(bbox)
            if extent is not None:
                if grow_by > 0:
                    extent.grow(grow_by)
                extent = transform.transformBoundingBox(extent)
                if union is None:
                    union = extent
                else:
                    union.combineExtentWith(extent)
        return union

    def deliver(extent):
        if expected_token is not None and current_subset_change_token() > expected_token:
            return
        if canvas.mapSettings().destinationCrs() != target_crs:
            return
        for layer, (_, _, fingerprint) in zip(layers, snapshots):
            if fingerprint != (layer.id(), layer.source(), layer.subsetString()):
                return
        if extent is not None:
            canvas.zoomToFeatureExtent(extent)
        canvas.refresh()

    from qgis.PyQt.QtCore import QCoreApplication
    task = submit_query(canvas, '_filtermate_union_zoom', layers[0],
                        QCoreApplication.translate('FilterMate', 'Loading filtered extent…'), compute, deliver, dependencies=layers)
    # Extra layers are snapshotted too; validate their fingerprints at delivery.
    return task


# Functions below operate on feature values / geometry only. Layer / project
# functions (aggregate, get_feature, relation_aggregate, eval...) may dereference
# live GUI QObjects, even if the expression context itself has been copied.
_SAFE_FUNCTIONS = frozenset((
    'coalesce', 'if', 'nullif', 'concat', 'lower', 'upper', 'title', 'trim', 'ltrim', 'rtrim',
    'length', 'substr', 'replace', 'regexp_replace', 'regexp_match', 'regexp_substr',
    'to_string', 'to_int', 'to_real', 'to_date', 'to_datetime', 'to_time', 'format', 'format_number',
    'abs', 'round', 'floor', 'ceil', 'sqrt', 'pow', 'exp', 'ln', 'log', 'log10', 'min', 'max',
    'year', 'month', 'day', 'hour', 'minute', 'second', 'make_date', 'make_datetime',
    'intersects', 'contains', 'within', 'touches', 'crosses', 'overlaps', 'disjoint',
    'geom_from_wkt', 'geom_from_gml', 'make_point', 'make_point_m', 'buffer', 'centroid',
    'area', 'perimeter', 'distance', 'x', 'y', 'bounds', 'bounds_width', 'bounds_height',
    '$id', '$geometry', '$area', '$length', '$perimeter', '$x', '$y',
))


def remote_expression_is_safe(expression, fields=None):
    """Whether a worker expression can run without accessing live project objects."""
    from qgis.core import QgsExpression
    if fields is not None and fields.indexOf(expression) >= 0:
        return True
    expr = QgsExpression(expression)
    if fields is not None and any(fields.lookupField(name) < 0 for name in expr.referencedColumns()):
        return False
    return (not expr.hasParserError() and not expr.referencedVariables()
            and set(expr.referencedFunctions()).issubset(_SAFE_FUNCTIONS))


def collect_unique_values(task, request, field_index, limit, scan_limit=10000, seconds=10):
    """Return bounded distinct values and an explicit partial-result flag."""
    scan_limit = max(limit + 1, scan_limit)
    request.setLimit(scan_limit + 1)
    values = set()
    partial = False
    started = time.monotonic()
    for scanned, feature in enumerate(task.features(request), 1):
        if scanned > scan_limit or time.monotonic() - started > seconds:
            partial = True
            break
        value = feature[field_index]
        if value is not None:
            values.add(str(value))
        if len(values) > limit:
            partial = True
            break
    return sorted(values)[:limit], partial
