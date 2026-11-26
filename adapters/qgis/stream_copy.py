# -*- coding: utf-8 -*-
"""Local copy of a web service layer over the visible map, and the way back to the service (2026-11-22).

A WFS, OGC API Features or ArcGIS Feature Service layer is copied to a GeoPackage; a WMS, WMTS or XYZ layer to a
GeoTIFF (red, green, blue, alpha, with overviews). The copy is read in a background task, bounded in pixels,
features and time (``APP.OPTIONS.STREAM_COPY``), then the layer reads it: same layer, same style, same filter.

The copy is kept in a folder next to the project (``<project>_filtermate_local``), in the QGIS profile when that
cannot be written. The project file keeps the address of the service, and the record of the copy
(``filtermate/local_copy``): it opens anywhere, with or without FilterMate, and opened with FilterMate the layer
finds its copy again when the file is there (:func:`reattach_project`).

The pure rules (what can be copied, names, folders, estimate, record) are ``filtermate_core.domain.stream_copy``.
"""
from __future__ import annotations

import datetime
import logging
import os
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from qgis.core import QgsTask

from ...core.domain import stream_copy as rules

logger = logging.getLogger(__name__)


def _tr(text: str) -> str:
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        translated = QCoreApplication.translate('StreamCopy', text)
        return translated if isinstance(translated, str) else text
    except ImportError:
        return text


# --- settings ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class CopyLimits:
    max_pixels: int = rules.DEFAULT_MAX_PIXELS
    max_features: int = rules.DEFAULT_MAX_FEATURES
    timeout_seconds: float = rules.DEFAULT_TIMEOUT_SECONDS


def copy_limits() -> CopyLimits:
    """``APP.OPTIONS.STREAM_COPY``: an unreadable value keeps its default, any other is brought within bounds."""
    try:
        from ...config.config import ENV_VARS, _get_option_value
        section = ENV_VARS.get('CONFIG_DATA', {}).get('APP', {}).get('OPTIONS', {}).get('STREAM_COPY', {}) or {}
    except Exception:
        section = {}

    def value(key):
        try:
            return _get_option_value(section.get(key), None)
        except Exception:
            return None

    return CopyLimits(
        int(rules.bounded_number(value('max_pixels'), rules.DEFAULT_MAX_PIXELS, rules.MIN_PIXELS, rules.MAX_PIXELS)),
        int(rules.bounded_number(value('max_features'), rules.DEFAULT_MAX_FEATURES, 1, 5_000_000)),
        rules.bounded_number(value('timeout_seconds'), rules.DEFAULT_TIMEOUT_SECONDS, 10, 86400))


# --- where ------------------------------------------------------------------------------------------------------

def _writable(folder: str) -> bool:
    """Whether ``folder`` can be written, or made in the nearest folder above it that exists: nothing is made here
    (a copy cancelled at its question leaves no empty folder next to the project)."""
    if os.path.isdir(folder):
        try:
            handle, probe = tempfile.mkstemp(prefix='.fm_write_', dir=folder)
            os.close(handle)
            os.remove(probe)
            return True
        except OSError:
            return False
    parent = os.path.dirname(os.path.abspath(folder))
    while parent and not os.path.isdir(parent):
        above = os.path.dirname(parent)
        if above == parent:
            return False
        parent = above
    return bool(parent) and os.access(parent, os.W_OK | os.X_OK)


def copy_folder(project=None) -> str:
    """Next to the project file, else in the QGIS profile; "" when neither can be written."""
    from qgis.core import QgsApplication, QgsProject
    project = project or QgsProject.instance()
    for folder in rules.folder_candidates(project.absoluteFilePath() or project.fileName(),
                                          QgsApplication.qgisSettingsDirPath()):
        if _writable(folder):
            return folder
    return ''


# --- the service, with or without its filter ----------------------------------------------------------------

# Providers whose filter QGIS writes in their source, as filter='...' (read in QGIS 3.44 on a WFS, 2026-11-22).
_FILTER_IN_SOURCE = ('wfs', 'oapif')


def stream_base(source: str, provider: str) -> str:
    """The source of a service without its filter: the filter is the layer's, kept apart (``LocalCopy.subset``)."""
    if (provider or '').lower() not in _FILTER_IN_SOURCE:
        return source
    from qgis.core import QgsDataSourceUri
    uri = QgsDataSourceUri(source)
    for key in ('filter', 'subset'):
        uri.removeParam(key)
    uri.setSql('')  # sql= is no parameter of QgsDataSourceUri: removeParam leaves it
    return uri.uri(False)


def same_service(current_source: str, current_provider: str, planned_source: str, planned_provider: str) -> bool:
    """Whether a layer still reads the service a copy was planned on: the same provider and endpoint, not another
    service of the same kind (audit of 2026-11-24: the copy of the former service was applied). A filter of the
    layer does not count: it is not in the endpoint. Without an endpoint on either side, the provider decides."""
    if (current_provider or '').lower() != (planned_provider or '').lower():
        return False
    from qgis.core import QgsDataSourceUri
    endpoint = QgsDataSourceUri(current_source or '').param('url') or ''
    planned = QgsDataSourceUri(planned_source or '').param('url') or ''
    return not endpoint or not planned or endpoint == planned


def stream_source_with(base: str, provider: str, subset: str) -> str:
    """The source a project file holds for the service filtered by ``subset``, as QGIS writes it itself."""
    if not subset or (provider or '').lower() not in _FILTER_IN_SOURCE:
        return base
    from qgis.core import QgsDataSourceUri
    uri = QgsDataSourceUri(base)
    uri.setParam('filter', subset)
    return uri.uri(False)


def _editing(layer) -> bool:
    try:
        return bool(getattr(layer, 'isEditable', lambda: False)())
    except RuntimeError:
        return False


def _opacity(layer) -> float:
    try:
        renderer = layer.renderer()
        return float(renderer.opacity()) if renderer is not None and hasattr(renderer, 'opacity') else -1.0
    except (RuntimeError, AttributeError, TypeError):
        return -1.0


# --- the record kept in the layer ----------------------------------------------------------------------------

def record_of(layer) -> Optional[rules.LocalCopy]:
    """The local copy ``layer`` reads now; None for a layer on its service, or whose source the user changed."""
    try:
        record = rules.LocalCopy.from_json(layer.customProperty(rules.PROPERTY))
        return record if record is not None and rules.is_copy_of(layer.source(), record) else None
    except RuntimeError:  # deleted by QGIS
        return None


def saved_record(layer) -> Optional[rules.LocalCopy]:
    """The copy a project file writes for ``layer``: the one it reads, or the one a filter of another layer clipped
    (its original source is the copy, in the registry of the derived sources)."""
    record = record_of(layer)
    if record is not None:
        return record
    try:
        stored = rules.LocalCopy.from_json(layer.customProperty(rules.PROPERTY))
    except RuntimeError:
        return None
    if stored is None:
        return None
    from .coverage_layers.snapshots import registry
    snapshot = registry().get(layer.id())
    return stored if snapshot is not None and rules.is_copy_of(snapshot.pristine_source, stored) else None


def can_copy(layer) -> bool:
    """A layer of a web service FilterMate copies, on its service now."""
    try:
        return bool(rules.copy_kind(layer.providerType())) and layer.isValid()
    except (RuntimeError, AttributeError):
        return False


def is_local_copy(layer) -> bool:
    return record_of(layer) is not None


# --- the plan: what will be read ------------------------------------------------------------------------------

@dataclass
class CopyPlan:
    """What a copy reads and writes; ``refusal`` says why it cannot be made ("" when it can)."""

    layer_id: str
    layer_name: str
    kind: str = ''
    refusal: str = ''
    source: str = ''
    provider: str = ''
    subset: str = ''
    crs: Any = None
    area: Any = None  # QgsRectangle, CRS of the layer: what is read (a web map: its grid, one cell of margin)
    requested: Any = None  # the area asked, kept in the record: Copy again starts from it, never from a grid
    columns: int = 0
    rows: int = 0
    resolution: float = 0.0
    estimate: Optional[rules.ImageEstimate] = None
    tiled: bool = False
    wkb_type: Any = None
    fields: Any = None
    folder: str = ''
    path: str = ''
    limits: CopyLimits = field(default_factory=CopyLimits)

    def summary(self) -> str:
        """What the user reads before the copy starts."""
        place = os.path.dirname(self.path)
        if self.kind == rules.KIND_IMAGE and self.estimate is not None:
            unit = _crs_unit(self.crs)
            return _tr("Copy of the visible map: {0} x {1} pixels, {2:.3g} {3} per pixel, {4} requests to the "
                       "service, {5:.0f} MB at most on disk.\n\nFolder: {6}").format(
                self.estimate.columns, self.estimate.rows, self.resolution, unit, self.estimate.requests,
                max(1.0, self.estimate.megabytes_at_most), place)
        most = f"{self.limits.max_features:,}".replace(",", "\u202f")
        return _tr("Copy of the features of the visible map, {0} at most.\n\nFolder: {1}").format(most, place)


def _crs_unit(crs) -> str:
    try:
        from qgis.core import QgsUnitTypes
        return QgsUnitTypes.toAbbreviatedString(crs.mapUnits()) or _tr('map units')
    except Exception:
        return _tr('map units')


def _is_tiled(source: str) -> bool:
    lowered = (source or '').lower()
    return 'type=xyz' in lowered or 'tilematrixset=' in lowered


def _area_in_layer_crs(layer, extent, extent_crs):
    from qgis.core import QgsCoordinateTransform, QgsCsException, QgsProject, QgsRectangle
    area = QgsRectangle(extent)
    if extent_crs is not None and extent_crs.isValid() and layer.crs().isValid() and extent_crs != layer.crs():
        try:
            area = QgsCoordinateTransform(extent_crs, layer.crs(), QgsProject.instance()).transformBoundingBox(area)
        except QgsCsException:
            return None
    return area if area.isFinite() and not area.isEmpty() else None


def plan_copy(layer, extent=None, extent_crs=None, screen_width: int = 0, project=None,
              with_folder: bool = True) -> CopyPlan:
    """What copying ``layer`` over ``extent`` (the visible map by default) would read and write. Main thread.

    Nothing is read from the service: the levels of a tile service are those its capabilities gave when the layer
    was opened. ``with_folder`` False: no folder of copies is chosen nor made (an export writes elsewhere).
    """
    from qgis.core import QgsRectangle
    plan = CopyPlan(layer.id(), layer.name())
    if is_local_copy(layer):
        plan.refusal = _tr("This layer already reads its local copy: go back to the service first, or copy it "
                           "again.")
        return plan
    plan.kind = rules.copy_kind(layer.providerType())
    if not plan.kind:
        plan.refusal = _tr("Only a layer of a web service (WFS, OGC API Features, ArcGIS Feature Service, WMS, WMTS, "
                           "XYZ tiles) can be copied.")
        return plan
    forbidden = rules.forbidden_by(layer.source())
    if forbidden:
        plan.refusal = _tr("The terms of {0} forbid keeping its tiles: this layer is not copied. Another basemap "
                           "can be (IGN, Carto, OpenTopoMap...).").format(forbidden)
        return plan
    if not layer.isValid():
        plan.refusal = _tr("This layer cannot be read from its service now.")
        return plan
    from .coverage_layers.snapshots import registry
    if registry().is_derived(layer.id()):
        plan.refusal = _tr("This layer is filtered by another layer: unfilter it, then copy it.")
        return plan
    if _editing(layer) and with_folder:
        plan.refusal = _tr("This layer is being edited: save or discard the edits, then copy it.")
        return plan
    if extent is None:
        try:
            from qgis.utils import iface
            canvas = iface.mapCanvas()
            extent, extent_crs = canvas.extent(), canvas.mapSettings().destinationCrs()
            screen_width = screen_width or canvas.width()
        except Exception:
            plan.refusal = _tr("The visible map could not be read.")
            return plan
    area = _area_in_layer_crs(layer, extent, extent_crs)
    if area is None:
        plan.refusal = _tr("The visible map cannot be expressed in the coordinates of this layer.")
        return plan
    plan.requested = area
    plan.limits = copy_limits()
    plan.provider, plan.crs = layer.providerType(), layer.crs()
    plan.source = stream_base(layer.source(), plan.provider)
    if plan.kind == rules.KIND_IMAGE:
        from .coverage_layers.raster_materialization import web_map_grid
        full = QgsRectangle(layer.extent())
        try:
            native = [float(level) for level in layer.dataProvider().nativeResolutions()]
        except Exception:
            native = []
        screen = area.width() / screen_width if screen_width else 0.0
        plan.tiled = _is_tiled(plan.source)
        try:
            (x_min, y_min, x_max, y_max), plan.columns, plan.rows, plan.resolution = web_map_grid(
                (full.xMinimum(), full.yMinimum(), full.xMaximum(), full.yMaximum()),
                (area.xMinimum(), area.yMinimum(), area.xMaximum(), area.yMaximum()),
                plan.limits.max_pixels, rules.finest_resolutions(native, screen))
        except ValueError:
            plan.refusal = _tr("The visible map is outside what this service draws.")
            return plan
        plan.area = QgsRectangle(x_min, y_min, x_max, y_max)
        plan.estimate = rules.image_estimate(plan.columns, plan.rows, plan.resolution, plan.tiled)
    else:
        from .remote_materializer import supports_materialization
        if not supports_materialization(layer):
            plan.refusal = _tr("This version of QGIS cannot check what a service answers while it is read: update "
                               "QGIS to 3.26 or later to copy it.")
            return plan
        plan.area = area
        plan.subset = layer.subsetString()
        plan.wkb_type, plan.fields = layer.wkbType(), layer.fields()
    if not with_folder:
        return plan
    plan.folder = copy_folder(project)
    if not plan.folder:
        plan.refusal = _tr("No folder can be written for the copy: neither next to the project nor in the QGIS "
                           "profile.")
        return plan
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    # Two copies planned in the same second, of layers whose names read alike (Bâti, B_ti): never one file.
    plan.path = rules.free_path(os.path.join(plan.folder, rules.file_name(layer.name(), plan.kind, stamp)),
                                lambda path: os.path.exists(path) or path in _RESERVED)
    return plan


_RESERVED = set()  # the files of the copies under way


# --- the copy ---------------------------------------------------------------------------------------------------

@dataclass
class CopyResult:
    record: Optional[rules.LocalCopy] = None
    error: str = ''
    notes: List[str] = field(default_factory=list)


class StreamCopyTask(QgsTask):
    """Read the service over the area of the plan into the file of the plan; ``callback(task)`` on the main thread."""

    def __init__(self, plan: CopyPlan, layer, callback: Optional[Callable[['StreamCopyTask'], None]] = None) -> None:
        super().__init__(_tr("FilterMate: local copy of {0}").format(plan.layer_name), QgsTask.Flag.CanCancel)
        from .source_capability_probe import capture_network_manager
        capture_network_manager()  # the tiles QGIS asks in a thread of its own are heard on the main thread
        self.plan = plan
        self.callback = callback
        self.restore: Optional[rules.LocalCopy] = None  # the copy to read again when this one does not end well
        self.result = CopyResult()
        if plan.path:
            _RESERVED.add(plan.path)
        self._stop = threading.Event()
        self._feedback = None
        self._snapshot = None
        if plan.kind == rules.KIND_FEATURES:
            from qgis.core import QgsFeedback
            from .remote_materializer import unfiltered_snapshot
            self._feedback = QgsFeedback()
            # The whole service over the area, not only what its filter keeps: the filter is put back on the copy.
            self._snapshot = unfiltered_snapshot(layer)

    def cancel(self) -> None:
        self._stop.set()
        if self._feedback is not None:
            self._feedback.cancel()
        super().cancel()

    def _canceled(self) -> bool:
        return self._stop.is_set() or self.isCanceled()

    def run(self) -> bool:
        try:
            if self.plan.kind == rules.KIND_IMAGE:
                self.result.record = self._copy_image()
            else:
                self.result.record = self._copy_features()
            return self.result.record is not None
        except Exception as exc:  # the message is ours (no provider text: it may hold a key)
            self.result.error = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else _tr(
                "the copy failed ({0})").format(type(exc).__name__)
            logger.info("FilterMate local copy of '%s' failed: %s", self.plan.layer_name, exc, exc_info=True)
            _remove(self.plan.path)
            return False
        finally:
            self._snapshot = None

    def _record(self, **values) -> rules.LocalCopy:
        area = self.plan.requested or self.plan.area  # the area asked: each Copy again would grow by the margin
        crs = (self.plan.crs.authid() or self.plan.crs.toWkt()) if self.plan.crs is not None else ''
        return rules.LocalCopy(
            kind=self.plan.kind, stream_source=self.plan.source, stream_provider=self.plan.provider,
            path=self.plan.path, extent=(area.xMinimum(), area.yMinimum(), area.xMaximum(), area.yMaximum()), crs=crs,
            captured=datetime.datetime.now().isoformat(timespec='seconds'), subset=self.plan.subset, **values)

    def _copy_image(self) -> rules.LocalCopy:
        from .coverage_layers.raster_materialization import materialize_web_map
        from .coverage_layers.target_appliers import _ProviderLayer
        plan = self.plan
        base = _ProviderLayer.open(plan.provider, plan.source, plan.layer_name)
        if not base.isValid():
            raise RuntimeError(_tr("the service could not be opened"))
        os.makedirs(plan.folder, exist_ok=True)
        self.setProgress(1)
        path, unread = materialize_web_map(base, plan.area, plan.columns, plan.rows, self._canceled,
                                           timeout=plan.limits.timeout_seconds, destination=plan.path,
                                           max_budget=rules.MAX_PIXELS)
        self.setProgress(90)
        _build_overviews(path)
        notes = (_tr("{0} request(s) of the service were not answered: the image may have holes.").format(unread),) \
            if unread else ()
        return self._record(complete=not unread, resolution=plan.resolution, holes=unread, notes=notes)

    def _copy_features(self) -> rules.LocalCopy:
        from qgis.core import (QgsCoordinateTransformContext, QgsFeatureRequest, QgsFields, QgsVectorFileWriter)
        from ...core.domain.materialization import MaterializationLimits
        from .remote_materializer import _bbox_source, bounded_rectangle, read_bounded_features
        plan = self.plan
        snapshot = self._snapshot
        rect = bounded_rectangle(plan.area)
        limits = MaterializationLimits(max_features=plan.limits.max_features,
                                       timeout_seconds=float(plan.limits.timeout_seconds))
        os.makedirs(plan.folder, exist_ok=True)
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.layerName = os.path.splitext(os.path.basename(plan.path))[0]
        names = [name.lower() for name in snapshot.fields.names()]
        layer_options = []
        if 'fid' in names:  # a field of the service named fid would clash with the key of the GeoPackage
            layer_options.append('FID=fm_fid')
        if 'geom' in names:  # nor one named geom with its geometry column
            layer_options.append('GEOMETRY_NAME=fm_geom')
        if layer_options:
            options.layerOptions = layer_options
        writer = QgsVectorFileWriter.create(plan.path, QgsFields(snapshot.fields), plan.wkb_type, plan.crs,
                                            QgsCoordinateTransformContext(), options)
        if writer is None or writer.hasError() != QgsVectorFileWriter.WriterError.NoError:
            message = writer.errorMessage() if writer is not None else ''
            writer = None
            raise RuntimeError(_tr("the GeoPackage could not be written: {0}").format(message[:200]))
        # collect_materialization swallows what keep raises: a refused addFeature is flagged here instead, and read
        # once the read ended (audit of 2026-11-24: a full disk accused the service).
        written = [0]
        unwritten = []
        total = max(1, plan.limits.max_features)

        def keep(feature) -> bool:
            if writer.addFeature(feature):
                written[0] += 1
                if written[0] % 500 == 0:
                    self.setProgress(min(99.0, 100.0 * written[0] / total))
            else:
                unwritten.append(True)
            return False  # nothing to collect: the feature is in the file

        try:
            outcome = read_bounded_features(
                None, QgsFeatureRequest().setFilterRect(rect), limits, self._feedback, keep, key=lambda feature: None,
                source_uri=snapshot.uri, source_factory=lambda: _bbox_source(snapshot, limits, rect=rect),
                provider_key=snapshot.provider)
        finally:
            writer = None  # flushed and closed here, in this thread
        if outcome.reason == 'cancelled' or self._canceled():
            raise RuntimeError(_tr("the copy was canceled"))
        if unwritten:
            # The service answered: the disk (full, unwritable) is at fault, not it (audit of 2026-11-24).
            raise RuntimeError(_tr("the local copy could not be written (the disk may be full): nothing was kept"))
        if outcome.reason == 'unverified_filter' and not written[0]:
            # Nothing arrived and the read could not be verified: a cut answer reads the same as no feature.
            raise RuntimeError(_tr("the service gave no feature over the visible map, or its answer could not be "
                                   "read: nothing was kept"))
        if outcome.reason not in ('', 'feature_limit', 'timeout', 'unverified_filter'):
            raise RuntimeError(_tr("the service could not be read to the end: nothing was kept"))
        notes = []
        if outcome.reason == 'feature_limit':
            notes.append(_tr("The visible map holds more than {0} features: only the first {0} were copied. Zoom in, "
                             "or raise STREAM_COPY > max_features.").format(plan.limits.max_features))
        elif outcome.reason == 'timeout':
            notes.append(_tr("The service was read for {0:.0f} s, the most allowed: the copy holds {1} features and "
                             "is not complete.").format(plan.limits.timeout_seconds, written[0]))
        complete = outcome.reason in ('', 'unverified_filter')
        told = outcome.announced
        if told is not None and written[0] < told and complete:
            # The service said it holds more than it gave (audit of 2026-11-24: 50 rows read of 5 000
            # announced, called complete): the copy is kept, but not called complete.
            complete = False
            notes.append(_tr("The service announced {0} features but only {1} were read: the copy is not "
                             "complete.").format(told, written[0]))
        return self._record(complete=complete, features=written[0], notes=tuple(notes))

    def finished(self, result: bool) -> None:  # main thread
        _RESERVED.discard(self.plan.path)
        if result and self._stop.is_set():  # cancelled after the read ended (overviews): cancelled all the same
            result, self.result.record = False, None
        if not result:
            self.result.error = self.result.error or _tr("the copy was canceled")
            _remove(self.plan.path)
        if self.callback is None:
            if result:  # the plugin stopped meanwhile: nobody reads this copy
                _remove(self.plan.path)
            return
        try:
            self.callback(self)
        except Exception:
            logger.exception("FilterMate local copy: the end of the copy was not handled")


def _remove(path: str) -> None:
    for suffix in ('', '-wal', '-shm', '.aux.xml', '.ovr', '.msk'):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


def _build_overviews(path: str) -> None:
    """Overviews inside the GeoTIFF, so that the copy draws fast when the map is zoomed out (best effort)."""
    try:
        from osgeo import gdal
    except ImportError:
        return
    dataset = None
    try:
        gdal.SetThreadLocalConfigOption('COMPRESS_OVERVIEW', 'LZW')
        dataset = gdal.Open(path, gdal.GA_Update)
        if dataset is None:
            return
        size, factors, factor = max(dataset.RasterXSize, dataset.RasterYSize), [], 2
        while size / factor >= 256 and len(factors) < 10:
            factors.append(factor)
            factor *= 2
        if factors:
            dataset.BuildOverviews('AVERAGE', factors)
    except Exception as exc:
        logger.debug(f"FilterMate local copy: no overviews for {path}: {exc}")
    finally:
        dataset = None
        try:
            gdal.SetThreadLocalConfigOption('COMPRESS_OVERVIEW', None)
        except Exception as exc:  # a cleanup: the overviews are written or not
            logger.debug(f"FilterMate local copy: COMPRESS_OVERVIEW not reset: {exc}")


# --- switching ----------------------------------------------------------------------------------------------------

def _copy_source(record: rules.LocalCopy) -> Tuple[str, str]:
    if record.kind == rules.KIND_IMAGE:
        return record.path, 'gdal'
    return f"{record.path}|layername={os.path.splitext(os.path.basename(record.path))[0]}", 'ogr'


def switch_to_copy(layer, record: rules.LocalCopy, subset: Optional[str] = None,
                   look_of_record: bool = False) -> List[str]:
    """``layer`` reads its copy now, with its style and its filter (``subset``, its own when None); returns what the
    user should know.

    ``look_of_record``: the opacity of the record, not of the layer (a project just read: the renderer the project
    wrote is the one of the copy, which the provider of the service does not take, and QGIS made a new one).

    Raises:
        RuntimeError: Edits under way, or a copy that cannot be opened: the layer stays on its service.
    """
    from .coverage_layers.snapshots import swap_source
    if _editing(layer):
        raise RuntimeError(_tr("{0} is being edited: it stays on its service. Save or discard the edits, then copy "
                               "it again.").format(layer.name()))
    if subset is None:
        subset = layer.subsetString() if hasattr(layer, 'subsetString') else ''
    # A web map opened offline is invalid: its renderer, if any, is a default one, not the user's.
    opacity = _opacity(layer) if layer.isValid() and not look_of_record else -1.0
    source, provider = _copy_source(record)
    if not swap_source(layer, source, provider):
        raise RuntimeError(_tr("the copy could not be opened: the layer still reads its service"))
    if opacity < 0 <= record.opacity:  # a web map opened offline: no renderer had the opacity to carry
        opacity = record.opacity
    if opacity >= 0 and record.kind == rules.KIND_IMAGE:
        try:
            layer.renderer().setOpacity(opacity)
        except (AttributeError, RuntimeError):
            pass
    notes = list(record.notes)
    if subset and hasattr(layer, 'setSubsetString') and layer.subsetString() != subset:
        if not layer.setSubsetString(subset):
            notes.append(_tr("Its filter could not be put on the copy (the GeoPackage reads another language): "
                             "filter it again."))
    layer.setCustomProperty(rules.PROPERTY, record.replaced(opacity=opacity).to_json())
    _MISSING.discard(layer.id())
    install()
    layer.triggerRepaint()
    return notes


def service_keeps_subset(subset: str) -> bool:
    """Whether a filter set on the local copy can go back on the service.

    A filter written for the GeoPackage of the copy (``json_each``, a ``fid`` list, SQLite constructs) is not
    QGIS and the service does not read it: put back as it is, the layer reads everything with the filter text
    still displayed (audit of 2026-11-24). Only what parses as QGIS goes back; the rest is filtered again.
    Pure apart from the QGIS parse (the bench reads it in QGIS).
    """
    if not subset:
        return True
    try:
        from qgis.core import QgsExpression
        return bool(QgsExpression(subset).isValid())
    except (RuntimeError, AttributeError):
        return False


PROFILE_COPY_MAX_AGE_DAYS = 30
_COPY_GRACE_SECONDS = 60.0  # a file being written is not pruned, even unreferenced
_COPY_EXTENSIONS = (".gpkg", ".tif", ".tiff", ".vrt", ".ovr", ".aux.xml", ".qmd", ".qlr", ".qml")


def _is_managed_copy_name(name: str) -> bool:
    """Whether the prune may touch this file: only what a copy is made of, never a foreign file."""
    return (name or "").lower().endswith(_COPY_EXTENSIONS)


def _delete_copy_files(path: str) -> None:
    """Remove a copy and its sidecars (.ovr, .aux.xml, .qmd, after the full name as GDAL writes them); failures
    are logged, never raised."""
    for candidate in [path] + ([path + suffix for suffix in (".ovr", ".aux.xml", ".qmd")] if path else []):
        try:
            if candidate and os.path.isfile(candidate):
                os.remove(candidate)
        except OSError as exc:
            logger.warning(f"FilterMate local copy: {candidate} not removed: {exc}")


def prune_copies(project=None) -> int:
    """Delete the copies no layer reads any more; returns how many files went.

    The rule, decided with the user (audit of 2026-11-24): a copy is deleted when its layer goes back to its
    service; what is left (layer removed, copy interrupted, snapshot restored) is pruned when a project opens.
    In the folder of the project, what no layer of the project references goes; in the profile, what no loaded
    layer references and older than ``PROFILE_COPY_MAX_AGE_DAYS`` goes (a missing copy falls back to its
    service, so nothing is lost). Files written less than a minute ago are never touched.
    """
    from qgis.core import QgsApplication, QgsProject
    project = project or QgsProject.instance()
    referenced = set()
    for layer in list(project.mapLayers().values()):
        try:
            record = record_of(layer)
        except Exception:
            continue
        if record is not None and record.path:
            referenced.add(os.path.normcase(os.path.abspath(record.path)))
            stem, _extension = os.path.splitext(os.path.abspath(record.path))
            referenced.add(os.path.normcase(stem))
    now = 0.0
    try:
        import time
        now = time.time()
    except Exception:
        pass

    def _stale(path: str, folder: str, by_age: bool) -> bool:
        key = os.path.normcase(os.path.abspath(path))
        if key in referenced or os.path.normcase(os.path.splitext(key)[0]) in referenced:
            return False
        if now and now - os.path.getmtime(path) < _COPY_GRACE_SECONDS:
            return False
        if not by_age:
            return True
        try:
            age_days = (now - os.path.getmtime(path)) / 86400.0 if now else 0.0
        except OSError:
            return False
        return age_days > PROFILE_COPY_MAX_AGE_DAYS

    def _prune_folder(folder: str, by_age: bool) -> int:
        gone = 0
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return 0
        for name in names:
            if not _is_managed_copy_name(name):
                continue
            path = os.path.join(folder, name)
            try:
                if not os.path.isfile(path) or not _stale(path, folder, by_age):
                    continue
                os.remove(path)
                gone += 1
            except OSError as exc:
                logger.warning(f"FilterMate local copy: {path} not pruned: {exc}")
        return gone

    deleted = 0
    try:
        folder = copy_folder(project)
    except Exception:
        folder = ""
    if folder:
        deleted += _prune_folder(folder, by_age=False)
    try:
        root = os.path.join(QgsApplication.qgisSettingsDirPath(), *rules.PROFILE_PARTS)
    except Exception:
        root = ""
    if root:
        try:
            tags = sorted(os.listdir(root))
        except OSError:
            tags = []
        for tag in tags:
            tag_dir = os.path.join(root, tag)
            if os.path.isdir(tag_dir):
                deleted += _prune_folder(tag_dir, by_age=True)
                try:
                    if not os.listdir(tag_dir):
                        os.rmdir(tag_dir)
                except OSError:
                    pass
    if deleted:
        logger.info(f"FilterMate local copies: {deleted} file(s) no layer reads pruned")
    return deleted


def switch_to_stream(layer, keep_record: bool = False) -> List[str]:
    """``layer`` reads its service again; the file of the copy is left where it is. Returns notes.

    ``keep_record``: the record stays in the layer, so that the copy is read again (the plugin unloaded, then loaded
    again: :func:`reattach_project`)."""
    from .coverage_layers.snapshots import swap_source
    record = record_of(layer)
    if record is None:
        raise RuntimeError(_tr("This layer does not read a local copy."))
    from .coverage_layers.snapshots import registry
    if registry().is_derived(layer.id()):
        raise RuntimeError(_tr("This layer is filtered by another layer: unfilter it, then go back to its service."))
    if _editing(layer):
        raise RuntimeError(_tr("This layer is being edited: save or discard the edits, then go back to its service."))
    subset = layer.subsetString() if hasattr(layer, 'subsetString') else ''
    # The service without a filter of its own: the filter the layer has now goes on it, or none. A filter set
    # on the copy in the language of the copy (json_each, fid) does not go: the service would read everything
    # with the filter text still displayed (audit of 2026-11-24).
    if not service_keeps_subset(subset):
        subset = ''
        dropped = True
    else:
        dropped = False
    if not swap_source(layer, stream_base(record.stream_source, record.stream_provider), record.stream_provider):
        raise RuntimeError(_tr("The service could not be opened: the layer still reads its copy."))
    notes = []
    if dropped:
        # The existing string: from the layer's side the filter is not back on the service either way.
        notes.append(_tr("Its filter could not be put back on the service: filter it again."))
    if hasattr(layer, 'setSubsetString') and layer.subsetString() != subset:
        if not layer.setSubsetString(subset):
            notes.append(_tr("Its filter could not be put back on the service: filter it again."))
    if not keep_record:
        # The file is read by nothing any more: it goes now, not at the next opening (audit of 2026-11-24:
        # copies were never deleted). On unload (keep_record) it stays for the reattach.
        _delete_copy_files(record.path)
        layer.removeCustomProperty(rules.PROPERTY)
    layer.triggerRepaint()
    return notes


def copy_text(record: rules.LocalCopy) -> str:
    """One line for the dock and the messages: when, how much, how complete."""
    when = record.captured.replace('T', ' ')[:16]
    if record.kind == rules.KIND_FEATURES:
        text = _tr("Local copy of {0}: {1} features").format(when, record.features)
    else:
        text = _tr("Local copy of {0}: still image").format(when)
    return text + ('' if record.complete else _tr(" (incomplete)"))


# --- the project file ---------------------------------------------------------------------------------------

_HOOKED: List[Tuple[Any, Callable]] = []
# The layers whose copy was not found when their project was read (a drive not there that day): their record is
# kept in the project file, the copy is looked for again next time.
_MISSING = set()


def install(project=None) -> None:
    """Write the service, not the copy, in the project file; find the copies again when a project is read."""
    from qgis.core import QgsProject
    project = project or QgsProject.instance()
    if any(hooked is project for hooked, _slot in _HOOKED):
        return

    def written(layer, element, document, project=project):
        rewrite_saved_layer(project, layer, element, document)

    project.writeMapLayer.connect(written)
    project.readProject.connect(_on_read_project)
    _HOOKED.append((project, written))


def uninstall() -> None:
    for project, slot in list(_HOOKED):
        for signal, connected in ((getattr(project, 'writeMapLayer', None), slot),
                                  (getattr(project, 'readProject', None), _on_read_project)):
            try:
                signal.disconnect(connected)
            except (TypeError, RuntimeError, AttributeError):
                pass
    _HOOKED.clear()


def rewrite_saved_layer(project, layer, element, document) -> None:
    """The layer as written in the project file: its service, and the record of its copy with a relative path.

    Also called at the end of the hook of the derived sources (a copy clipped by another layer), so the service is
    written whichever hook runs last.
    """
    try:
        from .coverage_layers.snapshots import (
            _remove_custom_property, _set_custom_property, _set_text, _set_tree_layer_source)
        record = saved_record(layer)
        if record is None:
            if layer.customProperty(rules.PROPERTY) is not None and layer.id() not in _MISSING:
                # The record of a copy the layer no longer reads (its source changed since): not written, so that
                # opening the project never puts the layer back on that copy.
                layer.removeCustomProperty(rules.PROPERTY)
                _remove_custom_property(element, rules.PROPERTY)
            return
        subset = layer.subsetString() if hasattr(layer, 'subsetString') and record_of(layer) is not None else ''
        base = stream_base(record.stream_source, record.stream_provider)
        source = stream_source_with(base, record.stream_provider, subset)
        _set_text(element, document, 'datasource', source)
        _set_text(element, document, 'provider', record.stream_provider)
        _set_tree_layer_source(document, layer.id(), source, record.stream_provider)
        opacity = _opacity(layer) if record.kind == rules.KIND_IMAGE else -1.0
        current = record.replaced(subset=subset, opacity=opacity if opacity >= 0 else record.opacity)
        if record_of(layer) is not None:
            layer.setCustomProperty(rules.PROPERTY, current.to_json())  # the record in memory follows the layer
        stored = current.with_path(project.pathResolver().writePath(record.path))
        _set_custom_property(element, document, rules.PROPERTY, stored.to_json())
    except Exception as exc:
        logger.warning(f"FilterMate local copy of '{getattr(layer, 'id', lambda: '?')()}' not written as its "
                       f"service: {exc}")


def _on_read_project(*_args) -> None:
    try:
        _reattached, missing = reattach_project()
    except Exception as exc:
        logger.warning(f"FilterMate local copies not found again: {exc}")
        return
    if missing:
        try:
            from ...infrastructure.feedback import show_warning
            show_warning(_tr("The local copy of {0} was not found: these layers read their web service. Their copy "
                             "is looked for again the next time the project is opened.").format(", ".join(missing)))
        except Exception as exc:  # no message bar here: the log says it
            logger.debug(f"FilterMate local copies: missing ones not shown: {exc}")


def reattach_project(project=None) -> Tuple[int, List[str]]:
    """The layers of a project just read that had a copy read it again; returns (count, names whose copy is gone).

    Runs before the derived filters are replayed (1.5 s after the project is read): a copy clipped by another layer
    is clipped again from its copy.
    """
    from qgis.core import QgsProject
    project = project or QgsProject.instance()
    reattached, missing = 0, []
    _MISSING.clear()
    for layer in list(project.mapLayers().values()):
        try:
            raw = layer.customProperty(rules.PROPERTY)
        except RuntimeError:
            continue
        stored = rules.LocalCopy.from_json(raw)
        if stored is None:
            continue
        record = stored.with_path(project.pathResolver().readPath(stored.path))
        if rules.is_copy_of(layer.source(), record):
            continue  # already on it
        if layer.providerType().lower() != record.stream_provider.lower():
            # The user changed its source since. (Its text alone proves nothing: QGIS 4 writes the source of a WMS
            # layer again in its own order.)
            layer.removeCustomProperty(rules.PROPERTY)
            continue
        if not os.path.isfile(record.path):
            missing.append(layer.name())
            _MISSING.add(layer.id())  # its record is kept: the copy is looked for again next time
            continue
        try:
            # Its filter as the project wrote it: in the source of a WFS (a project written with FilterMate off holds
            # the filter set then), in the record for a service that does not write it there.
            subset = layer.subsetString() if record.stream_provider.lower() in _FILTER_IN_SOURCE else record.subset
            switch_to_copy(layer, record, subset=subset, look_of_record=True)
            reattached += 1
        except RuntimeError:
            missing.append(layer.name())
            _MISSING.add(layer.id())
    if reattached or missing:
        logger.info(f"FilterMate local copies: {reattached} found again, missing for {missing}")
    try:
        prune_copies(project)
    except Exception as exc:
        logger.warning(f"FilterMate local copies not pruned: {exc}")
    return reattached, missing


def evict_service_cache() -> bool:
    """Forget what QGIS cached of the services, so that reading one again reads it anew.

    "Copy again" was served by the network cache of QGIS when the server sends no cache headers: no GetFeature
    went out and the old data came back with today's date (audit of 2026-11-24). The disk cache has no
    per-endpoint eviction, so the whole cache goes; a copy made again is an explicit read anew, worth it.
    Main thread (the copy task has not started yet).
    """
    try:
        from qgis.core import QgsNetworkAccessManager
        manager = QgsNetworkAccessManager.instance()
        cache = manager.cache() if manager is not None else None
    except (RuntimeError, AttributeError):
        return False
    if cache is None:
        return False
    try:
        cache.clear()
    except (RuntimeError, AttributeError):
        return False
    logger.info("FilterMate local copy: the network cache was forgotten before reading the service again")
    return True


def recopy_plan(layer) -> Tuple[CopyPlan, Optional[rules.LocalCopy]]:
    """The plan of a new copy of a layer on its copy, over the same area and, for a web map, the same detail; and
    the copy it read, to read again when the new one is not made (cancelled, refused, failed).

    The layer is on its service when the plan can be made (the plan reads the service as the layer opens it), on
    its copy again when it cannot.

    Raises:
        RuntimeError: The layer cannot go back to its service (edits, a filter of another layer).
    """
    record = record_of(layer)
    if record is None:
        return plan_copy(layer), None
    from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
    switch_to_stream(layer)
    crs = QgsCoordinateReferenceSystem(record.crs) if record.crs else layer.crs()
    area = QgsRectangle(*record.extent)
    # A WMS draws at any resolution: twice the detail of a screen as wide as the first copy gives its resolution.
    width = int(round(area.width() / (2 * record.resolution))) if record.resolution > 0 else 0
    plan = plan_copy(layer, area, crs, width)
    if plan.refusal:
        back_to(layer, record)
        return plan, record
    # After the plan read the service (snapshots, counts) and before the task does: the task must read the
    # service anew, not the cache.
    evict_service_cache()
    return plan, record


def discard(record: Optional[rules.LocalCopy], project=None) -> None:
    """Remove the file of a copy nothing reads (replaced by a new one, or made for a layer that changed); a file
    another layer of the project reads or names (Duplicate Layer copies the record) is kept."""
    if record is None or not record.path:
        return
    from qgis.core import QgsProject
    project = project or QgsProject.instance()
    for layer in project.mapLayers().values():
        try:
            other = rules.LocalCopy.from_json(layer.customProperty(rules.PROPERTY))
            if rules.is_copy_of(layer.source(), record) or (other is not None and rules.same_path(other.path, record.path)):
                return
        except RuntimeError:
            continue
    _remove(record.path)


def back_to(layer, record: rules.LocalCopy) -> None:
    """``layer`` reads ``record`` again (a new copy that was not made); a copy that cannot be opened leaves it on
    its service."""
    try:
        switch_to_copy(layer, record)
    except RuntimeError as exc:
        logger.warning(f"FilterMate local copy of '{layer.name()}' not read again: {exc}")


__all__ = ['CopyLimits', 'CopyPlan', 'CopyResult', 'StreamCopyTask', 'can_copy', 'copy_folder', 'copy_limits',
           'copy_text', 'install', 'is_local_copy', 'plan_copy', 'reattach_project', 'record_of', 'recopy_plan',
           'rewrite_saved_layer', 'switch_to_copy', 'switch_to_stream', 'uninstall']
