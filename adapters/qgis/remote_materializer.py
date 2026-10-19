"""Bounded remote-vector reads, performed only by a worker.

The public ``materialize`` function also runs inside an existing filter
task. ``RemoteMaterializationTask`` captures a feature-source snapshot on
the owner thread when a caller needs a standalone task. Neither path adds
a layer to the project or writes a scratch file.
"""

import math
import re
import threading
import time
from dataclasses import dataclass, replace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from qgis.core import QgsTask

from ...core.domain.materialization import (
    MaterializationLimits,
    MaterializationOutcome,
    collect_materialization,
)
from ...core.filter.pk_formatter import is_null_value
from ...core.optimization.config_provider import get_app_option_value
from .source_capability_probe import capture_network_manager, main_network_manager, stable_key_for_layer

_BBOX_PROVIDERS = frozenset(("wfs", "oapif", "arcgisfeatureserver"))
_PARTIAL_LAYERS = set()


def is_partial_source(layer):
    """Keep provenance across subset normalisation and sip wrapper recreation."""
    key = layer.id()
    if not layer.subsetString():
        _PARTIAL_LAYERS.discard(key)
        layer._filtermate_partial_subset = None
        return False
    return key in _PARTIAL_LAYERS or getattr(layer, "_filtermate_partial_subset", None) is not None


def mark_partial_result(layer, partial, expression):
    """Remember a partial source until a complete replacement or explicit reset."""
    key = layer.id()
    if partial:
        _PARTIAL_LAYERS.add(key)
        if getattr(layer, "_filtermate_partial_cleanup", None) is not _PARTIAL_LAYERS:
            layer.destroyed.connect(lambda *args, key=key, ids=_PARTIAL_LAYERS: ids.discard(key))
            layer._filtermate_partial_cleanup = _PARTIAL_LAYERS
    else:
        _PARTIAL_LAYERS.discard(key)
    layer._filtermate_partial_subset = expression if partial else None


def supports_reply_validation():
    """Require the native reply observer lifecycle, excluding old backports."""
    from qgis.core import Qgis, QgsNetworkAccessManager

    return Qgis.QGIS_VERSION_INT >= 32600 and hasattr(QgsNetworkAccessManager, "setReplyPreprocessor")


def supports_materialization(layer):
    """Whether this provider has an implemented bounded feature-read path."""
    provider = layer.dataProvider().name().lower()
    if provider in _BBOX_PROVIDERS:
        return supports_reply_validation()
    return provider == "memory"


capture_network_manager()


def materialization_limits(params=None):
    """Read validated APP.OPTIONS.REMOTE_MATERIALIZATION limits."""
    defaults = MaterializationLimits()
    try:
        return MaterializationLimits(
            max_features=get_app_option_value(params, "REMOTE_MATERIALIZATION", "max_features", defaults.max_features),
            timeout_seconds=get_app_option_value(
                params, "REMOTE_MATERIALIZATION", "timeout_seconds", defaults.timeout_seconds
            ),
        )
    except ValueError:
        # A malformed hand-edited option never disables a budget.
        return defaults


def require_worker():
    """Refuse remote reads before touching a provider on the GUI thread."""
    from qgis.PyQt.QtCore import QCoreApplication, QThread

    application = QCoreApplication.instance()
    if application is not None and QThread.currentThread() == application.thread():
        raise RuntimeError(
            QCoreApplication.translate("RemoteMaterializer", "Remote materialization requires a background task.")
        )


def bounded_rectangle(rect):
    """Copy a finite BBOX; enlarge degenerate point/line windows slightly.

    QGIS treats a null rectangle as no filter, which would read the entire
    service. Refuse it before getFeatures(), including NaN and infinity.
    """
    from qgis.core import QgsRectangle

    if rect is None or rect.isNull():
        raise ValueError("Remote reads require a useful bounding box")
    result = QgsRectangle(rect)
    coordinates = (result.xMinimum(), result.yMinimum(), result.xMaximum(), result.yMaximum())
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("Remote reads require a finite bounding box")
    if result.width() == 0 or result.height() == 0:
        result.grow(max(1e-8, max(abs(value) for value in coordinates) * 1e-12))
    return result


@dataclass
class _Snapshot:
    source: object
    key: object
    fields: object
    provider: str = ""
    uri: str = ""
    subset: str = ""
    crs: object = None


def _snapshot(layer):
    """Freeze a layer's data and stable-key choice without fetching rows."""
    from qgis.core import QgsVectorLayerFeatureSource

    if isinstance(layer, _Snapshot):
        return layer
    return _Snapshot(
        QgsVectorLayerFeatureSource(layer),
        stable_key_for_layer(layer, scan=False),
        layer.fields(),
        layer.dataProvider().name().lower(),
        layer.source(),
        layer.subsetString(),
        layer.crs(),
    )


def unfiltered_snapshot(layer):
    """Remove a subset without opening another provider or sampling features."""
    from qgis.core import QgsDataSourceUri

    snapshot = _snapshot(layer)
    uri = QgsDataSourceUri(snapshot.uri)
    for key in ("filter", "sql", "subset"):
        uri.removeParam(key)
    return replace(snapshot, uri=uri.uri(False), subset="")


def _bbox_source(snapshot, limits, bbox=True, rect=None):
    """Enable the WFS provider's server BBOX mode on a worker-owned copy.

    With the default WFS URI, a filterRect can be evaluated only against a
    cache populated by downloading the entire service. The provider needs
    restrictToRequestBBOX to send the rectangle to the actual server.
    """
    if snapshot.provider == "memory":
        return snapshot.source
    if snapshot.provider not in _BBOX_PROVIDERS:
        raise ValueError("This provider cannot guarantee bounded spatial reads")
    from qgis.core import QgsDataSourceUri, QgsVectorLayer

    uri = QgsDataSourceUri(snapshot.uri)
    if snapshot.provider == "oapif" and rect is not None:
        # OAPIF probes up to ten items for its field schema during provider
        # construction. Extra URL parameters also bound that preliminary read.
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext

        sample_rect = rect
        source_crs = snapshot.crs
        if source_crs.authid() not in ("EPSG:4326", "OGC:CRS84"):
            from ...infrastructure.utils.processing_context import captured_transform_context

            context = captured_transform_context() or QgsCoordinateTransformContext()
            transform = QgsCoordinateTransform(source_crs, QgsCoordinateReferenceSystem("OGC:CRS84"), context)
            sample_rect = transform.transformBoundingBox(rect)
        parts = urlsplit(uri.param("url"))
        query = list(parse_qsl(parts.query, keep_blank_values=True))
        if not any(key == "bbox" for key, value in query):
            query.append(
                (
                    "bbox",
                    ",".join(
                        format(value, ".17g")
                        for value in (
                            sample_rect.xMinimum(),
                            sample_rect.yMinimum(),
                            sample_rect.xMaximum(),
                            sample_rect.yMaximum(),
                        )
                    ),
                )
            )
        uri.setParam("url", urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)))
    if bbox and snapshot.provider in ("wfs", "oapif"):
        uri.removeParam("restrictToRequestBBOX")
        uri.setParam("restrictToRequestBBOX", "1")
    uri.removeParam("maxNumFeatures")
    uri.setParam("maxNumFeatures", str(limits.max_features + 1))
    provider = snapshot.provider.upper() if snapshot.provider in ("wfs", "oapif") else snapshot.provider
    clone = QgsVectorLayer(uri.uri(False), "filtermate_bounded_remote", provider)
    if not clone.isValid():
        raise ValueError("Remote provider copy is unavailable")
    if clone.fields().names() != snapshot.fields.names():
        raise ValueError("Remote provider schema changed during the copy")
    if clone.subsetString() != snapshot.subset and not clone.setSubsetString(snapshot.subset):
        raise ValueError("Remote provider subset is unavailable")
    clone.dataProvider().reloadData()
    return clone


def bounded_source_layer(layer, limits):
    """Preserve a filtered source subset while imposing the provider row cap."""
    require_worker()
    snapshot = _snapshot(layer)
    if snapshot.provider == "oapif" and snapshot.subset:
        # Without a spatial window or a proven FULL translation, a provider
        # client-side subset can hide its download cap. Never assume complete.
        raise ValueError("unverified_filter")
    return _bbox_source(snapshot, limits, bbox=False)


def _local_predicate(expression, fields):
    from qgis.core import QgsExpression, QgsExpressionContext

    if callable(expression):
        return expression
    if not expression:
        return lambda feature: True
    from .async_query import remote_expression_is_safe

    if not remote_expression_is_safe(expression, fields):
        raise ValueError("Local expression requires an external context")
    # Let QGIS perform its own three-valued boolean conversion. Python's
    # bool('0') / bool('false') would silently select the wrong rows.
    parsed = QgsExpression("({}) AND TRUE".format(expression))
    context = QgsExpressionContext()
    context.setFields(fields)
    if parsed.hasParserError() or not parsed.prepare(context):
        raise ValueError("Invalid local expression")

    def matches(feature):
        context.setFeature(feature)
        value = parsed.evaluate(context)
        if parsed.hasEvalError():
            raise ValueError("Local expression evaluation failed")
        return not is_null_value(value) and bool(value)

    return matches


def read_bounded_features(source, request, limits, feedback, consume, key, source_uri=None):
    """Copy each provider feature before local evaluation, with cooperative I/O cancellation.

    A watchdog cancels the provider feedback during a blocking network read.
    Providers that do not honor QgsFeedback may finish their current request;
    the elapsed-time check still prevents a late result being called complete.
    """
    from qgis.core import Qgis, QgsApplication, QgsDataSourceUri, QgsFeature, QgsFeedback, QgsNetworkAccessManager
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

    require_worker()
    own_feedback = QgsFeedback()
    stop = threading.Event()
    closing = threading.Event()
    deadline = time.monotonic() + limits.timeout_seconds

    def cancelled():
        return bool(feedback is not None and feedback.isCanceled())

    if cancelled():
        return MaterializationOutcome(reason="cancelled")

    def watch():
        while not stop.wait(0.025):
            if cancelled() or time.monotonic() >= deadline:
                own_feedback.cancel()
                return

    request.setLimit(limits.max_features + 1)
    request.setFeedback(own_feedback)
    request.setTimeout(max(1, int(limits.timeout_seconds * 1000)))
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    iterator = None
    network_failed = []
    provider_warnings = []
    network = QgsNetworkAccessManager.instance()
    uri = source_uri or (source.source() if hasattr(source, "source") else "")
    url = QgsDataSourceUri(uri).param("url") if uri else ""
    endpoint = urlsplit(url or uri)

    def belongs(request):
        verb = request.attribute(QNetworkRequest.Attribute.CustomVerbAttribute)
        if verb == "OPTIONS" or verb == b"OPTIONS":
            return False  # optional OAPIF capability discovery, not a feature read
        remote = urlsplit(request.url().toString())
        return bool(
            endpoint.hostname
            and remote.scheme == endpoint.scheme
            and remote.netloc == endpoint.netloc
            and (remote.path == endpoint.path or remote.path.startswith(endpoint.path.rstrip("/") + "/"))
        )

    def finished(reply):
        if (
            belongs(reply.request())
            and reply.error() != QNetworkReply.NetworkError.NoError
            and not (
                reply.error() == QNetworkReply.NetworkError.OperationCanceledError
                and (closing.is_set() or time.monotonic() >= deadline)
            )
        ):
            network_failed.append(True)

    # QGIS forwards downloader-thread replies to the main NAM as well. The
    # owner-thread manager catches requests made directly by this iterator;
    # iterator validity and cancellation remain independent checks.
    network.finished.connect(finished, Qt.ConnectionType.DirectConnection)
    main_network = main_network_manager()
    if main_network is network:
        main_network = None
    if main_network is not None:
        main_network.finished.connect(finished, Qt.ConnectionType.DirectConnection)
    # Since QGIS 3.26 this callback runs on the actual downloader thread,
    # before the first byte. It catches Qt6 WFS errors even if the provider
    # has not yet delivered its queued error signal to its owning thread.
    preprocessor = None
    if hasattr(QgsNetworkAccessManager, "setReplyPreprocessor"):

        def inspect_reply(request, reply):
            if not belongs(request):
                return

            tail = [b""]

            def error(code):
                if code != QNetworkReply.NetworkError.NoError and not (
                    code == QNetworkReply.NetworkError.OperationCanceledError
                    and (closing.is_set() or time.monotonic() >= deadline)
                ):
                    network_failed.append(True)

            def inspect_body():
                # Peek without consuming the provider's stream. ExceptionReport
                # responses often use HTTP 200 and never emit errorOccurred.
                try:
                    prefix = bytes(reply.peek(65536))
                except RuntimeError:
                    # A downloader can destroy its reply during cancellation.
                    # Do not let a Python slot exception escape through Qt.
                    if not closing.is_set() and time.monotonic() < deadline:
                        network_failed.append(True)
                    return
                prefix = tail[0] + prefix
                tail[0] = prefix[-256:]
                if re.search(rb"<(?:\w+:)?(?:ServiceExceptionReport|ExceptionReport)\b", prefix) or re.match(
                    rb'\s*\{\s*"error"\s*:', prefix
                ):
                    network_failed.append(True)

            reply.readyRead.connect(inspect_body, Qt.ConnectionType.DirectConnection)
            if hasattr(reply, "errorOccurred"):
                reply.errorOccurred.connect(error, Qt.ConnectionType.DirectConnection)
            else:  # Qt < 5.15: errorOccurred was named error
                reply.finished.connect(lambda: error(reply.error()), Qt.ConnectionType.DirectConnection)

        preprocessor = QgsNetworkAccessManager.setReplyPreprocessor(inspect_reply)
    message_log = QgsApplication.messageLog()

    def provider_message(message, tag, level):
        if tag.lower() == "oapif" and "OPTIONS" in message:
            return  # an unsupported optional HTTP verb does not invalidate GET /items
        if tag.lower() in ("wfs", "oapif", "arcgisfeatureserver") and level in (
            Qgis.MessageLevel.Warning,
            Qgis.MessageLevel.Critical,
        ):
            provider_warnings.append(True)

    message_log.messageReceived.connect(provider_message, Qt.ConnectionType.DirectConnection)
    provider = source.dataProvider() if hasattr(source, "dataProvider") else None

    def provider_error(*args):
        if not closing.is_set():
            network_failed.append(True)

    if provider is not None:
        provider.raiseError.connect(provider_error, Qt.ConnectionType.DirectConnection)
    try:
        iterator = source.getFeatures(request)
        if not iterator.isValid():
            return MaterializationOutcome(reason="read_error")

        def copied_features():
            try:
                for feature in iterator:
                    yield QgsFeature(feature)
            finally:
                closing.set()
                iterator.close()

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return MaterializationOutcome(reason="timeout")
        outcome = collect_materialization(
            copied_features(), key, consume, replace(limits, timeout_seconds=remaining), cancelled
        )
        if cancelled():
            return MaterializationOutcome(fetched=outcome.fetched, reason="cancelled")
        if outcome.reason not in ("", "feature_limit", "timeout"):
            return outcome
        if network_failed:
            return MaterializationOutcome(fetched=outcome.fetched, reason="read_error")
        if provider_warnings and outcome.reason not in ("feature_limit", "timeout"):
            return MaterializationOutcome(fetched=outcome.fetched, reason="read_error")
        if time.monotonic() >= deadline:
            return MaterializationOutcome(outcome.keys, False, outcome.fetched, "timeout")
        return outcome
    except Exception:
        return MaterializationOutcome(reason="read_error")
    finally:
        stop.set()
        watcher.join(timeout=0.1)
        if iterator is not None:
            iterator.close()
        network.finished.disconnect(finished)
        if main_network is not None:
            main_network.finished.disconnect(finished)
        if preprocessor is not None:
            QgsNetworkAccessManager.removeReplyPreprocessor(preprocessor)
        message_log.messageReceived.disconnect(provider_message)
        if provider is not None:
            provider.raiseError.disconnect(provider_error)


def materialize_translation(layer, rect, translation, limits=None, feedback=None):
    """Connect lot A's FULL/PARTIAL/NONE verdict to one bounded worker read.

    Args:
        layer: Worker-owned service layer.
        rect: Explicit useful extent in the layer CRS; never inferred globally.
        translation: ServerTranslation from the QGIS AST adapter.
        limits: Optional materialization budgets.
        feedback: Optional cancellation source.

    Returns:
        MaterializationOutcome including any exact local residual predicate.
    """
    return materialize(layer, rect, translation.subset_expression,
                       translation.local_expression, limits, feedback)


def materialize(layer, rect, server_expression, local_expression, limits=None, feedback=None):
    """Return stable keys from an exact local filter inside a bounded server BBOX.

    Args:
        layer: Worker-owned vector layer or a captured feature-source snapshot.
        rect: Useful extent in the layer CRS (required even for attribute filters).
        server_expression: Provider-compatible QGIS request expression, or empty.
            The caller must have verified its translation before supplying it.
        local_expression: Exact QGIS expression or callable accepting a copied feature.
        limits: MaterializationLimits, defaulting to 20,000 rows / 90 seconds.
        feedback: Optional QgsFeedback cancellation source.

    Returns:
        MaterializationOutcome. Refusal and errors never contain provider text.
    """
    from qgis.core import QgsFeatureRequest

    require_worker()
    if feedback is not None and feedback.isCanceled():
        return MaterializationOutcome(reason="cancelled")
    started = time.monotonic()
    try:
        rect = bounded_rectangle(rect)
    except ValueError:
        return MaterializationOutcome(reason="invalid_extent")
    snapshot = _snapshot(layer)
    if snapshot.provider in _BBOX_PROVIDERS:
        if not supports_reply_validation():
            # The older provider can report a delayed HTTP-200 exception as
            # complete exhaustion. Its copied NAM notification has no body.
            return MaterializationOutcome(reason="unverified_filter")
    if not snapshot.key.is_field:
        return MaterializationOutcome(reason="no_stable_key")
    limits = limits or MaterializationLimits()
    request = QgsFeatureRequest().setFilterRect(rect)
    try:
        matches = _local_predicate(local_expression, snapshot.fields)
        if snapshot.provider == "oapif" and snapshot.subset:
            subset_matches = _local_predicate(snapshot.subset, snapshot.fields)
            exact_matches = matches
            matches = lambda feature: subset_matches(feature) and exact_matches(feature)
            snapshot = unfiltered_snapshot(layer)
    except ValueError:
        return MaterializationOutcome(reason="invalid_expression")

    def key(feature):
        value = feature[snapshot.key.name]
        if is_null_value(value):
            raise ValueError("Missing stable key")
        return value

    try:
        source = _bbox_source(snapshot, limits, rect=rect)
    except ValueError:
        return MaterializationOutcome(reason="read_error")
    if server_expression:
        if hasattr(source, "setSubsetString"):
            subset = (
                "({}) AND ({})".format(snapshot.subset, server_expression) if snapshot.subset else server_expression
            )
            if not source.setSubsetString(subset) or not source.isValid():
                return MaterializationOutcome(reason="invalid_expression")
        else:
            return MaterializationOutcome(reason="invalid_expression")
    remaining = limits.timeout_seconds - (time.monotonic() - started)
    if remaining <= 0:
        return MaterializationOutcome(reason="timeout")
    return read_bounded_features(
        source, request, replace(limits, timeout_seconds=remaining), feedback, matches, key, source_uri=snapshot.uri
    )


class RemoteMaterializationTask(QgsTask):
    """Standalone materialization; results are consumed on the owner thread."""

    def __init__(self, layer, rect, server_expression="", local_expression="", limits=None):
        from qgis.PyQt.QtCore import QCoreApplication
        from qgis.core import QgsFeedback

        super().__init__(
            QCoreApplication.translate("RemoteMaterializer", "Filtering a bounded remote copy"), QgsTask.Flag.CanCancel
        )
        capture_network_manager()
        self._source = _snapshot(layer)
        try:
            self._rect = bounded_rectangle(rect)
        except ValueError:
            self._rect = None
        self._server_expression = server_expression
        self._local_expression = local_expression
        self._limits = limits or MaterializationLimits()
        self._feedback = QgsFeedback()
        self.outcome = (
            MaterializationOutcome(reason="invalid_extent") if self._rect is None else MaterializationOutcome()
        )

    def run(self):
        try:
            if self._rect is None:
                return False
            self.outcome = materialize(
                self._source, self._rect, self._server_expression, self._local_expression, self._limits, self._feedback
            )
            return self.outcome.complete or (
                bool(self.outcome.keys) and self.outcome.reason in ("feature_limit", "timeout")
            )
        except Exception:
            self.outcome = MaterializationOutcome(reason="read_error")
            return False
        finally:
            self._source = None
            self._local_expression = None

    def cancel(self):
        self._feedback.cancel()
        self.outcome = MaterializationOutcome(reason="cancelled")
        super().cancel()
