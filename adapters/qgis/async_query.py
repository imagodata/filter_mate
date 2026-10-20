"""Cancellable reads from a layer snapshot; delivery always runs on the GUI thread."""
import logging
import time

from qgis.core import QgsFeedback, QgsTask, QgsVectorLayerFeatureSource

logger = logging.getLogger(__name__)


class UnsafeExpressionError(ValueError):
    """A source expression would access live project objects from a worker."""


class UnsafeVirtualFieldError(UnsafeExpressionError):
    """A virtual field the request evaluates would access live project objects from a worker."""


def _task_flags():
    """Cancellable, closed without a prompt and hidden from the task bar where the QGIS version allows.

    CancelWithoutPrompt keeps a pending read from blocking the QGIS exit
    dialog; Hidden (QGIS 3.26+) keeps keystroke reads out of the task bar:
    the dock shows its own loading state.
    """
    flags = QgsTask.Flag.CanCancel
    for name in ('CancelWithoutPrompt', 'Hidden'):
        flag = getattr(QgsTask.Flag, name, None)
        if flag is not None:
            flags = flags | flag
    return flags


class SnapshotQueryTask(QgsTask):
    """Run a read against an independent snapshot, never against the live layer."""

    REQUEST_TIMEOUT_MS = 30000
    WFS_EXPRESSION_TIMEOUT_MS = 120000

    def __init__(self, description, layer, compute, deliver):
        super().__init__(description, _task_flags())
        self._provider_key = layer.providerType().lower()
        self._fields = layer.fields()
        # Only a request that evaluates one of them is refused (see features()).
        self._unsafe_virtual_fields = unsafe_virtual_fields(layer)
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
        if source is None and request_reads_fields(request, self._unsafe_virtual_fields, self._fields):
            raise UnsafeVirtualFieldError('Unsafe virtual field expression')
        request.setFeedback(self.feedback)
        timeout = self.REQUEST_TIMEOUT_MS
        if self._provider_key == 'wfs' and request.filterExpression() is not None:
            # WFS request expressions can filter downloaded pages locally.
            # The first matching feature may require scanning the whole source.
            timeout = self.WFS_EXPRESSION_TIMEOUT_MS
        request.setTimeout(timeout)
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
            if not self.isCanceled() and time.monotonic() - started >= timeout / 1000 * 0.9:
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
                if isinstance(task.error, UnsafeVirtualFieldError):
                    message = refusal_message(VIRTUAL_FIELD)
                elif isinstance(task.error, UnsafeExpressionError):
                    message = refusal_message(UNSAFE)
                else:
                    message = QCoreApplication.translate('FilterMate', 'The service could not be read. Please retry.')
                show_warning(message, QCoreApplication.translate('FilterMate', 'Read failed'))

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


# Functions below operate on the values / geometry of the evaluated feature only
# (QGIS 3.22 to 4.2 names, aliases resolve to these). Layer / project / style /
# file functions (aggregate, get_feature, overlay_*, represent_value, eval,
# layer_property, is_selected, ramp_color...) may dereference live GUI QObjects
# from a worker, even if the expression context itself has been copied; a name
# unknown here (a newer or a Python function) is refused. Not file_name /
# file_path / base_file_name / file_suffix either: since QGIS 3.30 a text
# argument may name a layer, looked up in the project on the main thread.
_SAFE_FUNCTIONS = frozenset((
    # Conditionals
    'coalesce', 'if', 'nullif', 'try', 'regexp_match',
    # Math
    'abs', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'clamp', 'cos', 'degrees', 'exp', 'floor', 'ln',
    'log', 'log10', 'max', 'min', 'pi', 'radians', 'rand', 'randf', 'round', 'scale_exp',
    'scale_exponential', 'scale_linear', 'scale_polynomial', 'scale_cubic_bezier', 'sin', 'sqrt', 'tan',
    # String
    'ascii', 'char', 'concat', 'concat_ws', 'format', 'format_date', 'format_number', 'left', 'length',
    'lower', 'lpad', 'ltrim', 'regexp_replace', 'regexp_substr', 'repeat', 'replace', 'right', 'rpad',
    'rtrim', 'strpos', 'substr', 'substr_count', 'title', 'trim', 'unaccent', 'upper', 'wordwrap',
    # Conversions
    'from_base64', 'hash', 'md5', 'sha256', 'to_base64', 'to_bool', 'to_date', 'to_datetime',
    'to_decimal', 'to_dm', 'to_dms', 'to_int', 'to_interval', 'to_real', 'to_string', 'to_time',
    'extract_degrees', 'extract_minutes', 'extract_seconds',
    # Date and time
    'age', 'convert_timezone', 'datetime_from_epoch', 'day', 'day_of_week', 'epoch', 'get_timezone',
    'hour', 'make_date', 'make_datetime', 'make_interval', 'make_time', 'minute', 'month', 'now',
    'second', 'set_timezone', 'timezone_from_id', 'timezone_id', 'week', 'year',
    # Fuzzy matching
    'hamming_distance', 'levenshtein', 'longest_common_substring', 'soundex',
    # Arrays
    'array', 'array_all', 'array_append', 'array_cat', 'array_contains', 'array_count', 'array_distinct',
    'array_filter', 'array_find', 'array_first', 'array_foreach', 'array_get', 'array_insert',
    'array_intersect', 'array_last', 'array_length', 'array_majority', 'array_max', 'array_mean',
    'array_median', 'array_min', 'array_minority', 'array_prepend', 'array_prioritize',
    'array_remove_all', 'array_remove_at', 'array_replace', 'array_reverse', 'array_slice', 'array_sort',
    'array_sum', 'array_to_string', 'generate_series', 'geometries_to_array', 'regexp_matches',
    'string_to_array',
    # Maps
    'from_json', 'hstore_to_map', 'map', 'map_akeys', 'map_avals', 'map_concat', 'map_delete', 'map_exist',
    'map_get', 'map_insert', 'map_prefix_keys', 'map_to_hstore', 'map_to_html_dl', 'map_to_html_table',
    'to_json', 'url_encode',
    # Colors built from values (not ramp_color / project_color: style and project lookups)
    'color_cmyk', 'color_cmyka', 'color_cmykf', 'color_grayscale_average', 'color_hsl', 'color_hsla',
    'color_hslf', 'color_hsv', 'color_hsva', 'color_hsvf', 'color_mix', 'color_mix_rgb', 'color_part',
    'color_rgb', 'color_rgba', 'color_rgbf', 'create_ramp', 'darker', 'lighter', 'set_color_part',
    # The evaluated feature
    '$id', '$currentfeature', 'attribute', 'attributes', 'feature_id', 'uuid',
    # Geometry (not overlay_*: other layers; not exif_geotag / magnetic_*: files and models)
    '$area', '$geometry', '$length', '$perimeter', '$x', '$x_at', '$y', '$y_at', '$z',
    'affine_transform', 'angle_at_vertex', 'apply_dash_pattern', 'area', 'azimuth', 'bearing',
    'boundary', 'bounds', 'bounds_height', 'bounds_width', 'buffer', 'buffer_by_m', 'centroid',
    'close_line', 'closest_point', 'collect_geometries', 'combine', 'concave_hull', 'contains',
    'convex_hull', 'crosses', 'densify_by_count', 'densify_by_distance', 'difference', 'disjoint',
    'distance', 'distance_to_vertex', 'end_point', 'equals', 'equals_exact', 'equals_fuzzy',
    'equals_topological', 'exterior_ring', 'extend', 'extrude', 'flip_coordinates', 'force_polygon_ccw',
    'force_polygon_cw', 'force_rhr', 'geom_from_gml', 'geom_from_wkb', 'geom_from_wkt', 'geom_to_wkb',
    'geom_to_wkt', 'geometry', 'geometry_n', 'geometry_type', 'hausdorff_distance', 'inclination',
    'interior_ring_n', 'intersection', 'intersects', 'intersects_bbox', 'is_closed', 'is_empty',
    'is_empty_or_null', 'is_multipart', 'is_valid', 'length3D', 'line_interpolate_angle',
    'line_interpolate_point', 'line_interpolate_point_by_m', 'line_locate_m', 'line_locate_point',
    'line_merge', 'line_substring', 'm', 'm_at', 'm_max', 'm_min', 'main_angle', 'make_circle',
    'make_ellipse', 'make_line', 'make_point', 'make_point_m', 'make_polygon', 'make_rectangle_3points',
    'make_regular_polygon', 'make_square', 'make_triangle', 'make_valid', 'minimal_circle',
    'nodes_to_points', 'num_geometries', 'num_interior_rings', 'num_points', 'num_rings', 'offset_curve',
    'order_parts', 'oriented_bbox', 'overlaps', 'perimeter', 'point_n', 'point_on_surface',
    'pole_of_inaccessibility', 'project', 'relate', 'reverse', 'rotate', 'roundness', 'scale',
    'segments_to_lines', 'shared_paths', 'shortest_line', 'simplify', 'simplify_vw', 'single_sided_buffer',
    'sinuosity', 'smooth', 'square_wave', 'square_wave_randomized', 'start_point', 'straight_distance_2d',
    'sym_difference', 'tapered_buffer', 'touches', 'transform', 'translate', 'triangular_wave',
    'triangular_wave_randomized', 'union', 'wave', 'wave_randomized', 'wedge_buffer', 'within', 'x',
    'x_at', 'x_max', 'x_min', 'y', 'y_at', 'y_max', 'y_min', 'z', 'z_at', 'z_max', 'z_min',
))

# Why a worker cannot run an expression (see expression_refusal / refusal_message).
SYNTAX = 'syntax'
UNSAFE = 'unsafe'
VIRTUAL_FIELD = 'virtual_field'
# QgsFeatureRequest::ALL_ATTRIBUTES, in referencedColumns() of attributes() / $currentfeature.
_ALL_ATTRIBUTES = '#!allattributes!#'


def expression_refusal(expression, fields=None):
    """Why a worker cannot evaluate ``expression``: None (it can), SYNTAX or UNSAFE.

    SYNTAX: a parser error or a field the layer does not have. UNSAFE: a
    function outside _SAFE_FUNCTIONS or a variable (a worker has no project
    / layer scope to read it from).
    """
    from qgis.core import QgsExpression
    if fields is not None and fields.indexOf(expression) >= 0:
        return None
    expr = QgsExpression(expression)
    if expr.hasParserError():
        return SYNTAX
    if expr.referencedVariables() or not set(expr.referencedFunctions()).issubset(_SAFE_FUNCTIONS):
        return UNSAFE
    if fields is not None and any(fields.lookupField(name) < 0 for name in expr.referencedColumns()
                                  if name != _ALL_ATTRIBUTES):
        return SYNTAX
    return None


def remote_expression_is_safe(expression, fields=None):
    """Whether a worker expression can run without accessing live project objects."""
    return expression_refusal(expression, fields) is None


def refusal_message(reason):
    """The translated message of a refusal reason (SYNTAX, UNSAFE or VIRTUAL_FIELD)."""
    from qgis.PyQt.QtCore import QCoreApplication
    if reason == SYNTAX:
        return QCoreApplication.translate(
            'FilterMate', 'The expression is not valid for this layer. Check its syntax and field names.')
    if reason == VIRTUAL_FIELD:
        return QCoreApplication.translate(
            'FilterMate', 'A virtual field of this layer cannot be evaluated safely for a service.')
    return QCoreApplication.translate('FilterMate', 'This expression cannot be evaluated safely for a service.')


def unsafe_virtual_fields(layer):
    """Names of the virtual fields a worker cannot evaluate, with the virtual fields that use them."""
    from qgis.core import QgsExpression
    fields = layer.fields()
    referenced = {}
    unsafe = set()
    for index in range(len(fields)):
        expression = layer.expressionField(index)
        if not isinstance(expression, str) or not expression:
            continue
        name = fields.at(index).name()
        if expression_refusal(expression, fields) is not None:
            unsafe.add(name)
        else:
            referenced[name] = set(QgsExpression(expression).referencedColumns())
    # A reference reads the field QgsFields.lookupField resolves (exact name, then case, then alias).
    unsafe_indexes = {fields.lookupField(name) for name in unsafe}
    grown = True
    while grown:
        grown = False
        for name, columns in referenced.items():
            if name not in unsafe and unsafe and (_ALL_ATTRIBUTES in columns or unsafe_indexes
                                                  & {fields.lookupField(column) for column in columns}):
                unsafe.add(name)
                unsafe_indexes.add(fields.lookupField(name))
                grown = True
    return unsafe


def _has_flag(flags, flag):
    try:
        return bool(flags & flag)
    except TypeError:
        return bool(int(flags) & int(flag))


def request_reads_fields(request, names, fields):
    """Whether ``request`` makes the layer iterator evaluate one of the fields ``names``.

    All attributes without SubsetOfAttributes; otherwise the requested ones,
    plus those of the filter expression and of the order.
    """
    if not names:
        return False
    from qgis.core import QgsFeatureRequest
    if not _has_flag(request.flags(), QgsFeatureRequest.Flag.SubsetOfAttributes):
        return True
    indexes = {fields.lookupField(name) for name in names} - {-1}
    if indexes & set(request.subsetOfAttributes()):
        return True
    columns = set()
    expression = request.filterExpression()
    if expression is not None:
        columns |= set(expression.referencedColumns())
    columns |= set(request.orderBy().usedAttributes())
    # A reference reads the field QgsFields.lookupField resolves (exact name, then case, then alias).
    return _ALL_ATTRIBUTES in columns or bool(indexes & {fields.lookupField(column) for column in columns})


def read_refusal(layer, request):
    """Why a worker cannot run ``request`` on ``layer`` (SYNTAX, UNSAFE, VIRTUAL_FIELD), None if it can."""
    fields = layer.fields()
    expression = request.filterExpression()
    if expression is not None:
        reason = expression_refusal(expression.expression(), fields)
        if reason is not None:
            return reason
    if request_reads_fields(request, unsafe_virtual_fields(layer), fields):
        return VIRTUAL_FIELD
    return None


def read_now(layer, compute):
    """Run ``compute`` with an ImmediateRead of ``layer``: ``(True, result)``, ``(False, None)`` on error.

    The error is logged and shown (read failed), as a task's error is: a read
    on the GUI thread never raises into the Qt slot that asked for it.
    """
    try:
        return True, compute(ImmediateRead(layer))
    except Exception as exc:
        from qgis.PyQt.QtCore import QCoreApplication
        from ...infrastructure.feedback import show_warning
        logger.warning("Read on the GUI thread failed (%s): %s", type(exc).__name__, exc)
        show_warning(QCoreApplication.translate('FilterMate', 'The service could not be read. Please retry.'),
                     QCoreApplication.translate('FilterMate', 'Read failed'))
        return False, None


class ImmediateRead:
    """The task interface over the live layer, on the calling thread.

    Used for a source that is no web service (network database, remote file)
    when a worker cannot evaluate its expression: it is read the way it was
    before 5.1, on the GUI thread, instead of being refused.
    """

    def __init__(self, layer):
        self._layer = layer

    @staticmethod
    def isCanceled():
        return False

    def features(self, request, source=None):
        return iter((self._layer if source is None else source).getFeatures(request))


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
