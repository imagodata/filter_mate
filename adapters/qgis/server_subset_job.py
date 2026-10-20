"""Prepare remote providers in a task, install them on the layer's thread.

QGIS's ArcGIS setSubsetString fetches object IDs synchronously. Moving only
the expression compiler off the UI thread does not avoid that request.
QGIS >= 3.32 can instead consume a preloaded provider in readLayerXml.
The existing layer stays untouched until its replacement is ready.
Where that transfer is not available (server_transfer_policy), a WFS
filter is set on the main thread if the QGIS setter survives a concurrent
read; anything else is refused.
"""
import json
import weakref
from contextlib import ExitStack

from qgis.core import (
    Qgis, QgsApplication, QgsDataProvider, QgsFeatureRequest, QgsMapLayer, QgsNetworkAccessManager, QgsProviderMetadata, QgsVectorLayer,
    QgsBlockingNetworkRequest, QgsDataSourceUri, QgsProject, QgsProviderRegistry,
    QgsReadWriteContext, QgsTask, QgsXmlUtils,
)
from qgis.PyQt.QtCore import QCoreApplication, QObject, QEventLoop, QThread, QTimer, Qt, QUrl, QUrlQuery, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.PyQt.QtXml import QDomDocument

from .server_filter_translation import ServerFilterError, _tr, prepare_server_subset
from ...core.filter.server_filter_state import ACTIVE_SERVER_FILTERS
from ...core.filter.server_transfer_policy import ASYNC, PRELOADED_PROVIDER_MIN, SYNC, transfer_mode  # noqa: F401
from .source_capability_probe import capability_for_layer

_ACTIVE = ACTIVE_SERVER_FILTERS


def transfer_mode_for_layer(layer):
    """ASYNC, SYNC or REFUSE for this layer's provider on the running QGIS."""
    declares_parallel = False
    flag = getattr(QgsProviderMetadata.ProviderCapability, 'ParallelCreateProvider', None)  # QGIS >= 3.32
    if flag is not None:
        metadata = QgsProviderRegistry.instance().providerMetadata(layer.providerType())
        declares_parallel = metadata is not None and bool(metadata.providerCapabilities() & flag)
    return transfer_mode(layer.providerType(), Qgis.QGIS_VERSION_INT, declares_parallel)


def cancel_pending_server_subset(layer):
    """A newer request, including clearing an empty layer, supersedes a job."""
    previous = _ACTIVE.get(layer.id())
    if previous is not None:
        if previous.committing:
            raise ServerFilterError(_tr('Server filter installation is in progress. Retry after it finishes.'))
        previous.cancel()


def _element(layer):
    """Serialize vector state without writeLayerXml's remote extent lookup."""
    document = QDomDocument()
    element = document.createElement('maplayer')
    document.appendChild(element)
    context = QgsReadWriteContext()
    if not layer.writeXml(element, document, context):
        raise ServerFilterError(_tr('Could not preserve the layer state.'))
    element.setAttribute('autoRefreshTime', str(layer.autoRefreshInterval()))
    element.setAttribute('autoRefreshEnabled', '1' if layer.hasAutoRefreshEnabled() else '0')
    if hasattr(layer, 'autoRefreshMode'):
        mode = layer.autoRefreshMode()
        for name in ('Disabled', 'RedrawOnly', 'ReloadData'):
            if mode == getattr(Qgis.AutoRefreshMode, name, None):
                element.setAttribute('autoRefreshMode', name)
                break
    element.setAttribute('refreshOnNotifyEnabled', '1' if layer.isRefreshOnNotifyEnabled() else '0')
    element.setAttribute('refreshOnNotifyMessage', layer.refreshOnNotifyMessage())
    if hasattr(layer, 'legendPlaceholderImage'):
        element.setAttribute('legendPlaceholderImage', layer.legendPlaceholderImage())
    for tag, value in (('id', layer.id()), ('layername', layer.name()), ('datasource', layer.source())):
        child = document.createElement(tag)
        child.appendChild(document.createTextNode(value))
        element.appendChild(child)
    srs = document.createElement('srs')
    layer.crs().writeXml(srs, document)
    element.appendChild(srs)
    metadata = document.createElement('resourceMetadata')
    layer.metadata().writeMetadataXml(metadata, document)
    element.appendChild(metadata)
    return document


def _provider_document(document, provider, extent):
    result = document.cloneNode(True).toDocument()
    element = result.documentElement()
    datasource = element.firstChildElement('datasource')
    replacement = result.createElement('datasource')
    replacement.appendChild(result.createTextNode(provider.dataSourceUri()))
    element.replaceChild(replacement, datasource)
    element.appendChild(QgsXmlUtils.writeRectangle(extent, result))
    return result


class _PrepareTask(QgsTask):
    def __init__(self, job, source, provider_key, subset, transform_context, destination_thread, read_flags):
        super().__init__(_tr('Preparing server attribute filter'), QgsTask.Flag.CanCancel)
        self.job = job
        self.source = source
        self.provider_key = provider_key
        self.subset = subset
        self.options = QgsDataProvider.ProviderOptions()
        self.options.transformContext = transform_context
        self.destination_thread = destination_thread
        self.read_flags = read_flags
        self.providers = [None, None]
        self.extents = [None, None]
        self.backup_valid = False
        self.failed = False
        self.urls = []

    def _reply(self, reply):
        """Notice transport errors; protocol bodies use explicit validation."""
        try:
            self.urls.append(reply.request().url())
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.failed = True
        except (AttributeError, RuntimeError):
            self.failed = True

    def forget_responses(self):
        """Drop this task's responses from QGIS's HTTP cache after a refusal.

        Providers read through QgsBlockingNetworkRequest, which prefers the
        cache: a transient error kept there would refuse the same filter
        again once the server has recovered. Main thread, after run(). Not
        after a cancellation: it saw no verdict, and removing an entry that
        another job is downloading leaves a truncated body in the cache.
        """
        cache = QgsNetworkAccessManager.instance().cache()
        if cache is not None:
            for url in self.urls:
                cache.remove(url)

    def _validate_arcgis(self):
        """Check the server's verdict, since AFS swallows object-ID errors.

        A bounded JSON count response is read only in this worker. Credentials
        and HTTP headers go through the same native QGIS auth machinery.
        forceRefresh: QgsBlockingNetworkRequest otherwise prefers QGIS's HTTP
        cache, which keeps a response without cache headers, so an earlier
        answer could mask a rejection (or keep a transient error).
        """
        uri = QgsDataSourceUri(self.source)
        if uri.param('urlprefix'):
            return False  # An opaque proxy rewrite cannot be reproduced safely.
        url = QUrl(uri.param('url'))
        url.setPath(url.path().rstrip('/') + '/query')
        query = QUrlQuery(url)
        for key, value in (('f', 'json'), ('where', self.subset.strip() or '1=1'), ('returnCountOnly', 'true')):
            query.removeAllQueryItems(key)
            query.addQueryItem(key, value)
        url.setQuery(query)
        request = QNetworkRequest(url)
        uri.httpHeaders().updateNetworkRequest(request)
        blocking = QgsBlockingNetworkRequest()
        blocking.setAuthCfg(uri.authConfigId())
        if blocking.get(request, True) != QgsBlockingNetworkRequest.ErrorCode.NoError:
            return False
        payload = json.loads(bytes(blocking.reply().content()).decode('utf-8'))
        count = payload.get('count') if isinstance(payload, dict) else None
        return isinstance(count, int) and not isinstance(count, bool) and count >= 0 and not payload.get('error')

    def run(self):
        manager = QgsNetworkAccessManager.instance()
        manager.finished.connect(self._reply, Qt.ConnectionType.DirectConnection)
        try:
            # Prepare the candidate first, with its filter in the URI where
            # supported. A broken old subset must not prevent unfiltering.
            for index in (1, 0):
                if self.isCanceled():
                    return False
                self.failed = False
                source = self.source
                key = self.provider_key.lower()
                if index == 1 and key in ('wfs', 'arcgisfeatureserver', 'mssql', 'oracle', 'hana'):
                    uri = QgsDataSourceUri(source)
                    if key == 'wfs':
                        uri.setSql('')
                        uri.removeParam('filter')
                        if self.subset:
                            uri.setParam('filter', self.subset)
                    else:
                        uri.setSql(self.subset)
                    source = uri.uri(False)
                provider = QgsProviderRegistry.instance().createProvider(self.provider_key, source, self.options, self.read_flags)
                self.providers[index] = provider
                valid = provider is not None and provider.isValid()
                if index == 1 and valid:
                    valid = bool(provider.setSubsetString(self.subset, False))
                if index == 1 and self.provider_key.lower() == 'arcgisfeatureserver' and not self._validate_arcgis():
                    return False
                if index == 1 and valid and key == 'wfs':
                    request = QgsFeatureRequest().setLimit(2).setNoAttributes()
                    iterator = provider.getFeatures(request)
                    next(iterator, None)
                    iterator.close()
                    QCoreApplication.processEvents()  # this worker's error slots
                valid = valid and not provider.hasErrors() and not self.failed
                if not valid:
                    if index == 0 and self.job.allow_missing_backup:
                        continue
                    return False
                self.extents[index] = provider.extent()
                if index == 0:
                    self.backup_valid = True
                if self.failed:
                    if index == 0 and self.job.allow_missing_backup:
                        self.backup_valid = False
                        continue
                    return False
            return not self.isCanceled()
        except Exception:  # nosec B110 - provider exceptions may contain credentials
            return False
        finally:
            manager.finished.disconnect(self._reply)
            for provider in self.providers:
                # Push from the owning worker; never pull a live QObject
                # from another thread on the main thread.
                if provider is not None:
                    provider.moveToThread(self.destination_thread)

    def finished(self, success):
        self.job._prepared(self, success)


class ServerSubsetJob(QObject):
    """Cancelable remote preparation with a final result, never a queued success.

    Construct/start on the layer's owning main thread. ``finished`` reports
    the completed installation, or an error with no delayed mutation after
    cancellation, timeout, source change, project removal or layer deletion.
    """

    finished = pyqtSignal(bool, str)

    def __init__(self, layer, expression, timeout_ms=30000, *, trusted_restore=False):
        super().__init__()
        if QThread.currentThread() != layer.thread():
            raise ServerFilterError(_tr('Server filter installation must start on the layer thread.'))
        subset = expression if trusted_restore else prepare_server_subset(layer, expression)
        self.layer_ref = weakref.ref(layer)
        self.layer_id = layer.id()
        self.before_source = layer.source()
        self.before_subset = layer.subsetString()
        self.project_owned = QgsProject.instance().mapLayer(self.layer_id) is layer
        self.read_extent_from_xml = layer.readExtentFromXml()
        self.refresh_interval = layer.autoRefreshInterval()
        self.refresh_enabled = layer.hasAutoRefreshEnabled()
        self.refresh_mode = layer.autoRefreshMode() if hasattr(layer, 'autoRefreshMode') else None
        self.notify_enabled = layer.isRefreshOnNotifyEnabled()
        self.refresh_paused = False
        self.subset = subset
        self.allow_missing_backup = not subset.strip() or trusted_restore or not layer.isValid()
        self.done = False
        self.committing = False
        self.success = False
        self.message = ''
        self.task = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(timeout_ms)
        self.timer.timeout.connect(self.cancel)

    def start(self):
        layer = self.layer_ref()
        if Qgis.QGIS_VERSION_INT < PRELOADED_PROVIDER_MIN:
            raise ServerFilterError(_tr('Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.'))
        if QThread.currentThread() != layer.thread() or layer.thread() != QgsApplication.instance().thread():
            raise ServerFilterError(_tr('Server filter installation must start on the layer thread.'))
        if layer.isEditable():
            raise ServerFilterError(_tr('Finish editing the layer before applying a server filter.'))
        from ..public_api.operations import _background_tasks_running
        if _background_tasks_running():
            raise ServerFilterError(_tr('A FilterMate task is still reading layers. Retry after it finishes.'))
        if transfer_mode_for_layer(layer) != ASYNC:
            raise ServerFilterError(_tr('This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.'))
        if layer.auxiliaryLayer() is not None:
            raise ServerFilterError(_tr('A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.'))
        for join in layer.vectorJoins():
            joined = join.joinLayer()
            capability = capability_for_layer(joined) if joined is not None else None
            if capability is not None and not capability.counts_cheaply:
                raise ServerFilterError(_tr('A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.'))
        if self.layer_id in _ACTIVE:
            raise ServerFilterError(_tr('A server filter is already being prepared for this layer.'))
        snapshot = _element(layer)
        read_flags = QgsVectorLayer.providerReadFlags(snapshot.documentElement(), QgsMapLayer.ReadFlags())
        self.task = _PrepareTask(self, self.before_source, layer.providerType(), self.subset,
                                 layer.transformContext(), layer.thread(), read_flags)
        layer.setAutoRefreshEnabled(False)
        layer.setRefreshOnNotifyEnabled(False)
        self.refresh_paused = True
        _ACTIVE[self.layer_id] = self
        self.timer.start()
        QgsApplication.taskManager().addTask(self.task)
        return self

    def _complete(self, success, message=''):
        if self.done:
            return
        self.timer.stop()
        layer = self.layer_ref()
        if self.refresh_paused and layer is not None:
            try:
                layer.setAutoRefreshInterval(self.refresh_interval)
                if self.refresh_mode is not None:
                    layer.setAutoRefreshMode(self.refresh_mode)
                else:
                    layer.setAutoRefreshEnabled(self.refresh_enabled)
                layer.setRefreshOnNotifyEnabled(self.notify_enabled)
            except RuntimeError:
                pass  # Deleted while preparing; the task never owned it.
        self.done, self.success, self.message = True, success, message
        if _ACTIVE.get(self.layer_id) is self:
            _ACTIVE.pop(self.layer_id)
        self.finished.emit(success, message)

    def cancel(self):
        if self.done:
            return
        if self.committing:
            return  # Installation is local and atomic; report its final result.
        if self.task is not None:
            self.task.cancel()
        self._complete(False, _tr('Server filter canceled or timed out. The previous filter is unchanged.'))

    def _prepared(self, task, success):
        consumed = set()
        guards = ExitStack()
        try:
            if not success and not task.isCanceled():
                task.forget_responses()
            if self.done:
                return
            if not success:
                message = _tr('Server filter canceled or timed out. The previous filter is unchanged.') if task.isCanceled() else _tr(
                    'The server rejected the filter or could not be reached. The previous filter is unchanged.')
                self._complete(False, message)
                return
            layer = self.layer_ref()
            if layer is None or layer.source() != self.before_source or layer.subsetString() != self.before_subset or (
                    self.project_owned and QgsProject.instance().mapLayer(self.layer_id) is not layer) or layer.isEditable():
                self._complete(False, _tr('The layer changed while preparing its filter. The prepared result was discarded.'))
                return
            self.committing = True
            self.timer.stop()
            # A picker may have been reattached by a layer/UI change while
            # the responsive wait processed events. Detach it again for the
            # atomic provider replacement, without holding a worker lock.
            from ...infrastructure.database.sql_utils import feature_picker_guard
            guards.enter_context(feature_picker_guard(layer))
            document = _element(layer)
            original, candidate = task.providers
            old_document = _provider_document(document, original, task.extents[0]) if task.backup_valid else None
            new_document = _provider_document(document, candidate, task.extents[1])
            flags = QgsMapLayer.ReadFlag.FlagReadExtentFromXml
            context = QgsReadWriteContext()
            consumed.add(1)
            try:
                installed = layer.readLayerXml(new_document.documentElement(), context, flags, candidate)
            except Exception:  # nosec B110 - recover with the prepared original
                installed = False
            if not installed or not layer.isValid() or layer.subsetString().strip() != self.subset.strip():
                if old_document is None:
                    self._complete(False, _tr('Server filter installation failed. The previous provider was already invalid and could not be restored.'))
                    return
                consumed.add(0)
                try:
                    restored = layer.readLayerXml(old_document.documentElement(), context, flags, original)
                except Exception:  # nosec B110 - report a failed rollback explicitly
                    restored = False
                if not restored or not layer.isValid():
                    self._complete(False, _tr('Server filter installation failed and the previous provider could not be restored.'))
                    return
                layer.resolveReferences(QgsProject.instance())
                layer.setReadExtentFromXml(self.read_extent_from_xml)
                layer.setExtent(task.extents[0])
                layer.removeSelection()
                layer.dataChanged.emit()
                self._complete(False, _tr('Server filter installation failed. The previous provider was restored.'))
                return
            layer.resolveReferences(QgsProject.instance())
            layer.setReadExtentFromXml(self.read_extent_from_xml)
            layer.setExtent(task.extents[1])
            layer.removeSelection()
            layer.dataChanged.emit()
            layer.subsetStringChanged.emit()
            layer.triggerRepaint()
            self._complete(True)
        except RuntimeError:  # layer deleted while the task was running
            self._complete(False, _tr('The layer is no longer available. The prepared filter was discarded.'))
        except Exception:  # nosec B110 - no provider exception/URI in logs
            self._complete(False, _tr('Could not install the prepared server filter.'))
        finally:
            try:
                guards.close()
            finally:
                for index, provider in enumerate(task.providers):
                    if provider is not None and index not in consumed:
                        provider.deleteLater()
                task.providers = []


def apply_server_subset_wait(layer, subset, timeout_ms=30000, *, trusted_restore=False):
    """Compatibility bool API: await a worker with a responsive Qt event loop.

    New async consumers can use ServerSubsetJob directly. Existing task,
    REST/MCP and Processing callers receive the final completed result.
    """
    loop = QEventLoop()
    layer_name = layer.name()
    job = ServerSubsetJob(layer, subset, timeout_ms, trusted_restore=trusted_restore)
    job.finished.connect(loop.quit)
    try:
        job.start()
    except ServerFilterError as exc:
        raise ServerFilterError('{}: {}'.format(layer_name, exc)) from None
    if not job.done:
        loop.exec()
    if not job.success:
        raise ServerFilterError('{}: {}'.format(layer_name, job.message))
    return True


def apply_server_subset_sync(layer, subset):
    """Set a validated WFS subset on the main thread, as FilterMate 4 did.

    For the SYNC transfer mode only: ``subset`` is already a FULL
    translation, an empty string or an exact history snapshot. The WFS
    setter sends no request (features download when read), so the freeze
    is the setter itself. A False return, an invalid layer, an exception,
    a new provider error or a WFS warning logged by the setter restores the
    previous subset. A service rejecting the filter in its GetFeature
    response is only seen when features are read: an empty layer, as
    before 5.0.
    """
    name = layer.name()
    main = QgsApplication.instance().thread()
    if QThread.currentThread() != layer.thread() or layer.thread() != main:
        raise ServerFilterError('{}: {}'.format(name, _tr('Server filter installation must start on the layer thread.')))
    if layer.isEditable():
        raise ServerFilterError('{}: {}'.format(name, _tr('Finish editing the layer before applying a server filter.')))
    if not layer.isValid():
        # QGIS only stores a subset for an invalid layer and returns False.
        raise ServerFilterError('{}: {}'.format(name, _tr(
            'Server filter installation failed. The previous provider was already invalid and could not be restored.')))
    from ..public_api.operations import _background_tasks_running
    if _background_tasks_running():
        raise ServerFilterError('{}: {}'.format(name, _tr('A FilterMate task is still reading layers. Retry after it finishes.')))
    from ...infrastructure.database.sql_utils import feature_picker_guard
    before = layer.subsetString()
    provider = layer.dataProvider()
    errors = len(provider.errors()) if provider is not None else 0
    warnings = []

    def logged(message, tag, level):
        # The setter logs on the main thread; downloads of other layers log
        # on their own threads and say nothing about this filter.
        if QThread.currentThread() == main and tag.lower() == 'wfs' and level in (
                Qgis.MessageLevel.Warning, Qgis.MessageLevel.Critical):
            warnings.append(True)

    log = QgsApplication.messageLog()
    with feature_picker_guard(layer):
        log.messageReceived.connect(logged, Qt.ConnectionType.DirectConnection)
        try:
            accepted = layer.setSubsetString(subset)
            provider = layer.dataProvider()
            if accepted and layer.isValid() and layer.subsetString().strip() == subset.strip() and not warnings and (
                    provider is None or len(provider.errors()) <= errors):
                layer.removeSelection()  # as the asynchronous path: ids can change (3.28+)
                return True
        except Exception:  # nosec B110 - provider details may contain credentials
            pass
        finally:
            log.messageReceived.disconnect(logged)
        try:
            if layer.subsetString() != before or not layer.isValid():
                if not layer.setSubsetString(before) or not layer.isValid():
                    raise ValueError('Restoration rejected')
        except Exception:  # nosec B110 - report the failure without a source URI
            raise ServerFilterError(_tr('{0}: the provider rejected the filter and restoration failed.').format(name)) from None
    raise ServerFilterError(_tr('{0}: the provider rejected the attribute filter. The previous filter was restored.').format(name))
