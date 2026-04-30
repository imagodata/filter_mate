"""
Layer Exporter

v4.0 EPIC-1 Phase E1: Extracted from filter_task.py export methods

Handles layer export operations to various formats.

IMPORTANT: Export is INDEPENDENT from "exploring" and QGIS selection.
====================================================================

Export behavior:
- Uses QgsVectorFileWriter which respects the layer's subsetString (filter)
- WITH subset: exports only features matching the filter
- WITHOUT subset: exports all features in the layer
- Does NOT use QGIS selectedFeatures() - selection is ignored
- Does NOT reference current_layer from exploring tab

Original source: modules/tasks/filter_task.py lines 9551-10400 (~850 lines)
"""

import os
import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any

try:
    from qgis.core import (
        QgsVectorLayer,
        QgsVectorFileWriter,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsCoordinateTransformContext,
        QgsProject,
    )
    from qgis import processing
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    QgsVectorLayer = Any
    QgsVectorFileWriter = Any
    QgsCoordinateReferenceSystem = Any
    QgsCoordinateTransform = Any
    QgsCoordinateTransformContext = Any
    QgsProject = Any

logger = logging.getLogger('FilterMate.Export')

# Canonical mapping of uppercased OGR driver descriptions to file extensions.
# Covers both short aliases (SHP, TAB) and full OGR names (ESRI SHAPEFILE, MAPINFO FILE).
# Used by LayerExporter, BatchExporter, and ExportHandler for consistent extension resolution.
OGR_EXTENSION_MAP = {
    'GPKG': '.gpkg',
    'SHP': '.shp',
    'SHAPEFILE': '.shp',
    'ESRI SHAPEFILE': '.shp',
    'GEOJSON': '.geojson',
    'JSON': '.geojson',
    'GML': '.gml',
    'KML': '.kml',
    'LIBKML': '.kml',
    'CSV': '.csv',
    'XLSX': '.xlsx',
    'TAB': '.tab',
    'MAPINFO': '.tab',
    'MAPINFO FILE': '.tab',
    'DXF': '.dxf',
    'SQLITE': '.sqlite',
    # SpatiaLite uses .sqlite by QGIS/OGR convention; .spatialite is not
    # recognised by QGIS data-source loaders.
    'SPATIALITE': '.sqlite',
    'FLATGEOBUF': '.fgb',
    'ESRI FILEGDB': '.gdb',
    'OPENFILEGDB': '.gdb',
    'PGDUMP': '.sql',
}


def get_extension_for_format(datatype: str) -> str:
    """Return the file extension (with dot) for an OGR driver description.

    Handles both short aliases ('SHP') and full OGR names ('ESRI Shapefile').
    Falls back to '.{datatype_lower}' for unknown drivers.
    """
    ext = OGR_EXTENSION_MAP.get(datatype.upper())
    if ext:
        return ext
    # Fallback: use lowercased datatype as extension (only safe for single-word names)
    clean = datatype.strip().lower().replace(' ', '_')
    return f'.{clean}'


# Sidecar file extensions per format. Used by cleanup_partial_export() to
# remove orphan files when an export fails midway. Keys are uppercased OGR
# driver names; values are lists of extensions (with leading dot) that share
# the output's basename. The main file extension is included.
_FORMAT_SIDECARS = {
    'ESRI SHAPEFILE': ['.shp', '.dbf', '.shx', '.prj', '.cpg', '.qpj',
                       '.qix', '.qmd', '.sbn', '.sbx', '.fbn', '.fbx',
                       '.ain', '.aih', '.ixs', '.mxs', '.atx'],
    'MAPINFO FILE':   ['.tab', '.dat', '.id', '.map', '.ind', '.qmd'],
    'GPKG':           ['.gpkg', '.gpkg-journal', '.gpkg-wal', '.gpkg-shm'],
    'GEOJSON':        ['.geojson', '.json'],
    'GML':            ['.gml', '.xsd', '.gfs'],
    'KML':            ['.kml'],
    'LIBKML':         ['.kml'],
    'CSV':            ['.csv', '.csvt', '.prj'],
    'XLSX':           ['.xlsx'],
    'DXF':            ['.dxf'],
    'SQLITE':         ['.sqlite', '.sqlite-journal', '.sqlite-wal', '.sqlite-shm'],
    'SPATIALITE':     ['.sqlite', '.sqlite-journal', '.sqlite-wal', '.sqlite-shm'],
    'FLATGEOBUF':     ['.fgb'],
    'PGDUMP':         ['.sql'],
}


def cleanup_partial_export(output_path: str, datatype: str) -> int:
    """Delete a failed-export's main file and known sidecars sharing its basename.

    When ``QgsVectorFileWriter.writeAsVectorFormatV3`` (or streaming) fails
    midway through a write, partial output may be left on disk under the
    target path. The user then sees an export-failure dialog AND a
    same-named file/sidecars sitting in the output folder, with no way to
    tell from the filename whether the file is complete (audit Tier 3 §24).

    This helper removes the main output file plus all sibling files in the
    same directory whose basename matches and whose extension is in
    ``_FORMAT_SIDECARS[datatype]``. Files belonging to OTHER layers in the
    same directory are not touched (extension match is exact).

    Args:
        output_path: The intended path of the failed export (the path
            passed to the writer).
        datatype: OGR driver name (e.g. 'ESRI Shapefile', 'GPKG').

    Returns:
        Number of files actually removed.
    """
    parent_dir = os.path.dirname(output_path) or '.'
    if not os.path.isdir(parent_dir):
        return 0

    base = os.path.splitext(os.path.basename(output_path))[0]
    if not base:
        return 0

    extensions = _FORMAT_SIDECARS.get(datatype.upper())
    if not extensions:
        # Unknown datatype: only remove the exact target_path if it exists.
        # Don't glob unknown extensions — too easy to delete unrelated files.
        if os.path.isfile(output_path):
            try:
                os.remove(output_path)
                return 1
            except OSError as e:
                logger.warning(f"Cleanup failed for {output_path}: {e}")
        return 0

    removed = 0
    for ext in extensions:
        candidate = os.path.join(parent_dir, base + ext)
        if os.path.isfile(candidate):
            try:
                os.remove(candidate)
                removed += 1
                logger.debug(f"Cleaned up partial export sidecar: {candidate}")
            except OSError as e:
                logger.warning(f"Cleanup failed for {candidate}: {e}")
    if removed:
        logger.info(
            f"Cleaned up {removed} partial export file(s) for "
            f"failed write of {output_path}"
        )
    return removed


# Shapefile DBF allows only ASCII alphanumerics + underscore in field names,
# max 10 chars, must start with a letter. OGR truncates/mangles silently.
_DBF_VALID_FIELD = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,9}$')

# Geometry type buckets used to detect mixed-type layers that SHP can't store
# in a single file (Point/MultiPoint share a bucket; same for Line and Polygon
# variants — OGR coerces Single↔Multi automatically).
_GEOM_BUCKETS = {
    'Point': 'point', 'MultiPoint': 'point',
    'LineString': 'line', 'MultiLineString': 'line',
    'CircularString': 'line', 'CompoundCurve': 'line', 'MultiCurve': 'line',
    'Polygon': 'polygon', 'MultiPolygon': 'polygon',
    'CurvePolygon': 'polygon', 'MultiSurface': 'polygon',
}


def validate_shapefile_constraints(layer) -> List[str]:
    """Return human-readable warnings for SHP-specific constraints that OGR
    would otherwise apply silently:

    - DBF field-name limit (10 chars, ASCII alnum + underscore)
    - Single geometry-type per file (mixed types get coerced)

    Returns an empty list when the layer is SHP-clean. Warnings are surfaced
    via ``ExportResult.warnings`` — never fatal, since OGR can still produce
    a (degraded) shapefile.
    """
    warnings: List[str] = []

    try:
        fields = list(layer.fields())
    except Exception:
        fields = []

    long_fields = [f.name() for f in fields if len(f.name()) > 10]
    if long_fields:
        warnings.append(
            f"DBF will silently truncate field names >10 chars: {long_fields}. "
            f"Rename fields before export to keep them stable."
        )

    invalid_fields = [
        f.name() for f in fields
        if not _DBF_VALID_FIELD.match(f.name())
    ]
    # Subtract long_fields so the user doesn't get duplicate noise.
    invalid_only = [n for n in invalid_fields if n not in long_fields]
    if invalid_only:
        warnings.append(
            f"DBF requires ASCII letter-leading alphanumerics + underscore in "
            f"field names. OGR will mangle: {invalid_only}"
        )

    # Geometry homogeneity: SHP can hold one geometry type per file.
    try:
        wkb_type = layer.wkbType()
        from qgis.core import QgsWkbTypes
        type_name = QgsWkbTypes.displayString(wkb_type)
    except Exception:
        type_name = ''

    if type_name in ('Unknown', 'GeometryCollection', 'NoGeometry'):
        warnings.append(
            f"Layer geometry type '{type_name}' is not natively supported by "
            f"Shapefile — OGR may produce a degraded or empty file."
        )

    return warnings


class ExportFormat(Enum):
    """Supported export formats."""
    GPKG = "GPKG"
    SHAPEFILE = "ESRI Shapefile"
    GEOJSON = "GeoJSON"
    GML = "GML"
    KML = "KML"
    CSV = "CSV"
    XLSX = "XLSX"
    TAB = "MapInfo File"
    DXF = "DXF"
    SPATIALITE = "SpatiaLite"


@dataclass
class ExportConfig:
    """Configuration for layer export."""

    layers: List[str]
    """Layer names to export."""

    output_path: str
    """Output path (file or directory)."""

    datatype: str
    """Export format (GPKG, SHP, etc.)."""

    projection: Optional[QgsCoordinateReferenceSystem] = None
    """Target CRS or None to use layer's CRS."""

    style_format: Optional[str] = None
    """Style format (qml, sld, lyrx) or None."""

    save_styles: bool = False
    """Whether to save layer styles."""

    batch_mode: bool = False
    """Whether to export each layer to separate file."""

    batch_zip: bool = False
    """Whether to create zip archive."""


@dataclass
class ExportResult:
    """Result of export operation."""

    success: bool
    """Whether export succeeded."""

    exported_count: int = 0
    """Number of layers successfully exported."""

    failed_count: int = 0
    """Number of layers that failed to export."""

    output_path: Optional[str] = None
    """Path to exported file/directory."""

    error_message: Optional[str] = None
    """Error message if export failed."""

    warnings: List[str] = None
    """Non-fatal warnings during export."""

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class LayerExporter:
    """
    Exports QGIS vector layers to various formats.

    Supports:
    - Single layer export
    - Batch export to directory
    - GeoPackage multi-layer export
    - Style export (via StyleExporter)
    - CRS reprojection

    Example:
        exporter = LayerExporter(project)
        config = ExportConfig(
            layers=["layer1", "layer2"],
            output_path="/path/to/output.gpkg",
            datatype="GPKG",
            save_styles=True
        )
        result = exporter.export(config)
        if result.success:

    """

    # Format driver mapping (uppercased key → OGR driver name)
    DRIVER_MAP = {
        'GPKG': 'GPKG',
        'SHP': 'ESRI Shapefile',
        'SHAPEFILE': 'ESRI Shapefile',
        'ESRI SHAPEFILE': 'ESRI Shapefile',
        'GEOJSON': 'GeoJSON',
        'JSON': 'GeoJSON',
        'GML': 'GML',
        'KML': 'KML',
        'LIBKML': 'LIBKML',
        'CSV': 'CSV',
        'XLSX': 'XLSX',
        'TAB': 'MapInfo File',
        'MAPINFO': 'MapInfo File',
        'MAPINFO FILE': 'MapInfo File',
        'DXF': 'DXF',
        'SQLITE': 'SQLite',
        'SPATIALITE': 'SpatiaLite',
        'FLATGEOBUF': 'FlatGeobuf',
    }

    def __init__(self, project: Optional[QgsProject] = None):
        """
        Initialize layer exporter.

        Args:
            project: QgsProject instance or None to use current project
        """
        self.project = project or (QgsProject.instance() if QGIS_AVAILABLE else None)

    def export(self, config: ExportConfig) -> ExportResult:
        """
        Export layers according to configuration.

        Args:
            config: Export configuration

        Returns:
            ExportResult with export status and statistics
        """
        if not QGIS_AVAILABLE:
            return ExportResult(
                success=False,
                error_message="QGIS not available"
            )

        if not self.project:
            return ExportResult(
                success=False,
                error_message="No QGIS project available"
            )

        # Special handling for GPKG multi-layer export
        if config.datatype.upper() == 'GPKG' and not config.batch_mode:
            return self.export_to_gpkg(config.layers, config.output_path, config.save_styles)

        # Batch export (one file per layer)
        if config.batch_mode:
            return self.export_batch(config)

        # Single layer export
        if len(config.layers) == 1:
            return self.export_single_layer(
                config.layers[0],
                config.output_path,
                config.projection,
                config.datatype,
                config.style_format,
                config.save_styles
            )

        # Multiple layers to directory
        return self.export_multiple_to_directory(config)

    def export_single_layer(
        self,
        layer_name: str,
        output_path: str,
        projection: Optional[QgsCoordinateReferenceSystem],
        datatype: str,
        style_format: Optional[str],
        save_styles: bool
    ) -> ExportResult:
        """
        Export a single layer to file.

        Args:
            layer_name: Layer name to export
            output_path: Output file path
            projection: Target CRS or None to use layer's CRS
            datatype: Export format (e.g., 'SHP', 'GPKG')
            style_format: Style file format or None
            save_styles: Whether to save layer styles

        Returns:
            ExportResult with export status
        """
        # Get layer
        layer = self.get_layer_by_name(layer_name)
        if not layer:
            return ExportResult(
                success=False,
                error_message=f"Layer '{layer_name}' not found in project"
            )

        # Determine CRS
        current_projection = projection if projection else layer.sourceCrs()

        # Map datatype to QGIS driver
        driver_name = self.DRIVER_MAP.get(datatype.upper(), datatype)

        logger.debug(f"Exporting layer '{layer.name()}' to {output_path} (driver: {driver_name})")

        # Pre-flight: surface SHP-specific constraints (DBF field limits,
        # geometry type homogeneity) that OGR would otherwise apply silently.
        shp_warnings: List[str] = []
        if driver_name == 'ESRI Shapefile':
            shp_warnings = validate_shapefile_constraints(layer)
            for w in shp_warnings:
                logger.warning(f"SHP pre-flight ({layer.name()}): {w}")

        try:
            # writeAsVectorFormatV3 (QGIS 3.20+) — replaces deprecated writeAsVectorFormat
            # which is removed in QGIS 4.x. CRS reprojection is expressed via options.ct.
            transform_context = (
                QgsProject.instance().transformContext()
                if QgsProject.instance() is not None
                else QgsCoordinateTransformContext()
            )

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = driver_name
            options.fileEncoding = "UTF-8"

            # CSV needs explicit geometry layer-creation options, otherwise
            # OGR drops the geometry column silently. CREATE_CSVT writes a
            # `.csvt` sidecar with column types so re-import preserves them.
            if driver_name == 'CSV':
                options.layerOptions = [
                    'GEOMETRY=AS_WKT',
                    'CREATE_CSVT=YES',
                    'SEPARATOR=COMMA',
                ]

            source_crs = layer.sourceCrs()
            if (
                current_projection
                and current_projection.isValid()
                and source_crs.isValid()
                and current_projection != source_crs
            ):
                options.ct = QgsCoordinateTransform(
                    source_crs, current_projection, transform_context
                )

            error, error_msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_path,
                transform_context,
                options,
            )

            if error != QgsVectorFileWriter.NoError:
                msg = error_msg or "Unknown error"
                logger.error(f"Export failed for layer '{layer.name()}': {msg}")
                # Tier 3 fix: remove partial output so the user doesn't end
                # up with a corrupt-but-named file that looks complete.
                cleanup_partial_export(output_path, driver_name)
                return ExportResult(
                    success=False,
                    error_message=msg
                )

            # Save style if requested
            if save_styles and style_format:
                from .style_exporter import save_layer_style
                save_layer_style(layer, output_path, style_format, datatype)

            return ExportResult(
                success=True,
                exported_count=1,
                output_path=output_path,
                warnings=shp_warnings,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Export exception for layer '{layer.name()}': {error_msg}")
            # Same cleanup as the writer-error branch — exception during
            # write may have left a partial file too.
            try:
                cleanup_partial_export(output_path, driver_name)
            except Exception as cleanup_err:
                logger.debug(f"Cleanup-on-exception failed: {cleanup_err}")
            return ExportResult(
                success=False,
                error_message=error_msg
            )

    def export_to_gpkg(
        self,
        layer_names: List[str],
        output_path: str,
        save_styles: bool,
        target_crs: Optional[QgsCoordinateReferenceSystem] = None,
    ) -> ExportResult:
        """
        Export layers to GeoPackage format using QGIS processing.

        Args:
            layer_names: List of layer names to export
            output_path: Output GPKG file path
            save_styles: Whether to include layer styles
            target_crs: Optional reprojection CRS. ``qgis:package`` does not
                accept a CRS parameter, so when ``target_crs`` is set and
                differs from any layer's native CRS we fall back to manual
                per-layer ``writeAsVectorFormatV3`` with ``options.ct``.

        Returns:
            ExportResult with export status
        """
        logger.info(f"Exporting {len(layer_names)} layer(s) to GPKG: {output_path}")

        # Collect layer objects
        layer_objects = []
        for layer_item in layer_names:
            layer_name = layer_item['layer_name'] if isinstance(layer_item, dict) else layer_item
            layer = self.get_layer_by_name(layer_name)
            if layer:
                layer_objects.append(layer)

        if not layer_objects:
            return ExportResult(
                success=False,
                error_message="No valid layers found for GPKG export"
            )

        # If user picked a target CRS that differs from any layer's source
        # CRS, ``qgis:package`` would silently keep the source CRS. Fall back
        # to a manual writer loop so reprojection actually happens.
        needs_reprojection = (
            target_crs is not None
            and target_crs.isValid()
            and any(
                layer.sourceCrs().isValid() and layer.sourceCrs() != target_crs
                for layer in layer_objects
            )
        )

        if needs_reprojection:
            return self._export_to_gpkg_reproject(
                layer_objects, output_path, target_crs, save_styles=save_styles
            )

        alg_parameters = {
            'LAYERS': layer_objects,
            'OVERWRITE': True,
            'SAVE_STYLES': save_styles,
            'OUTPUT': output_path
        }

        try:
            output = processing.run("qgis:package", alg_parameters)

            if not output or 'OUTPUT' not in output:
                return ExportResult(
                    success=False,
                    error_message="GPKG export failed: no output returned"
                )

            logger.info(f"GPKG export successful: {output['OUTPUT']}")

            # NOTE: Success message is displayed by finished_handler on main thread
            # DO NOT call iface.messageBar() here - this code runs in background thread!
            # Calling GUI methods from background thread causes crash (access violation)

            return ExportResult(
                success=True,
                exported_count=len(layer_objects),
                output_path=output['OUTPUT']
            )

        except Exception as e:
            logger.error(f"GPKG export failed with exception: {e}")
            return ExportResult(
                success=False,
                error_message=str(e)
            )

    def _export_to_gpkg_reproject(
        self,
        layer_objects: List[QgsVectorLayer],
        output_path: str,
        target_crs: QgsCoordinateReferenceSystem,
        save_styles: bool = False,
    ) -> ExportResult:
        """Multi-layer GPKG export with per-layer reprojection.

        ``processing.run("qgis:package")`` does not accept a CRS parameter,
        so when reprojection is requested we have to drive the export
        ourselves via writeAsVectorFormatV3, layering each table into the
        same .gpkg via ``actionOnExistingFile``.

        When ``save_styles=True``, after the writer loop completes we embed
        QML styles into the GPKG's ``layer_styles`` table via the helper
        in ``gpkg_layer_tree_writer`` — mirroring what
        ``processing.run('qgis:package', SAVE_STYLES=True)`` would have done
        on the non-reprojection branch. (Audit H1 fix.)
        """
        logger.info(
            f"GPKG reprojection export: {len(layer_objects)} layer(s) "
            f"→ {target_crs.authid()} → {output_path}"
        )

        transform_context = (
            QgsProject.instance().transformContext()
            if QgsProject.instance() is not None
            else QgsCoordinateTransformContext()
        )

        # Remove any existing output so the first writer call doesn't append
        # to stale data from a previous run.
        if os.path.isfile(output_path):
            try:
                os.remove(output_path)
            except OSError as e:
                return ExportResult(
                    success=False,
                    error_message=f"Cannot overwrite existing GPKG: {e}",
                )

        for idx, layer in enumerate(layer_objects):
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.fileEncoding = 'UTF-8'
            options.layerName = layer.name()
            # First layer creates the file; subsequent layers append a new
            # table to the same GPKG.
            if idx == 0:
                options.actionOnExistingFile = (
                    QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
                )
            else:
                options.actionOnExistingFile = (
                    QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                )

            source_crs = layer.sourceCrs()
            if source_crs.isValid() and source_crs != target_crs:
                options.ct = QgsCoordinateTransform(
                    source_crs, target_crs, transform_context
                )

            error, error_msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer, output_path, transform_context, options
            )
            if error != QgsVectorFileWriter.NoError:
                msg = error_msg or "Unknown error"
                logger.error(
                    f"GPKG reprojection export failed for '{layer.name()}': {msg}"
                )
                # Cleanup the partial multi-layer GPKG. Even if some earlier
                # layers wrote successfully, the file as a whole is incomplete
                # — better to remove than leave a half-built GPKG that looks
                # like a finished export.
                cleanup_partial_export(output_path, 'GPKG')
                return ExportResult(
                    success=False,
                    error_message=msg,
                )

        # Embed styles in the layer_styles table (H1 fix). qgis:package would
        # have done this on the non-reprojection branch via SAVE_STYLES=True;
        # we have to drive it explicitly here.
        if save_styles:
            try:
                from .gpkg_layer_tree_writer import write_layer_styles_to_gpkg
                pairs = [(layer, layer.name()) for layer in layer_objects]
                ok = write_layer_styles_to_gpkg(output_path, pairs)
                if not ok:
                    logger.warning(
                        f"Layer styles embedding returned False for {output_path} — "
                        f"data exported successfully but styles may be missing"
                    )
            except Exception as e:  # never fail the export over a style write
                logger.warning(
                    f"Style embedding failed for {output_path}: {e}", exc_info=True
                )

        return ExportResult(
            success=True,
            exported_count=len(layer_objects),
            output_path=output_path,
        )

    def export_multiple_to_directory(self, config: ExportConfig) -> ExportResult:
        """
        Export multiple layers to a directory (one file per layer).

        Args:
            config: Export configuration

        Returns:
            ExportResult with export statistics
        """
        from .batch_exporter import _disambiguate_basename, sanitize_filename
        result = ExportResult(success=True, output_path=config.output_path)
        used_basenames = set()

        for layer_name_item in config.layers:
            # Handle both dict and string formats
            layer_name = layer_name_item['layer_name'] if isinstance(layer_name_item, dict) else layer_name_item

            # Build output path for this layer (disambiguate collisions)
            safe = _disambiguate_basename(
                sanitize_filename(layer_name), used_basenames
            )
            ext = get_extension_for_format(config.datatype)
            layer_output = os.path.join(
                config.output_path,
                f"{safe}{ext}"
            )

            # Export layer
            layer_result = self.export_single_layer(
                layer_name,
                layer_output,
                config.projection,
                config.datatype,
                config.style_format,
                config.save_styles
            )

            if layer_result.success:
                result.exported_count += 1
            else:
                result.failed_count += 1
                if layer_result.error_message:
                    result.warnings.append(f"{layer_name}: {layer_result.error_message}")

        # Overall success if at least one layer exported
        result.success = result.exported_count > 0
        if result.failed_count > 0:
            result.error_message = f"{result.failed_count} layer(s) failed to export"

        return result

    def export_batch(self, config: ExportConfig) -> ExportResult:
        """
        Export layers in batch mode (directory or zip).

        Args:
            config: Export configuration with batch settings

        Returns:
            ExportResult with export statistics
        """
        import tempfile
        import shutil
        import zipfile

        if config.batch_zip:
            # v5.0: Implement ZIP archive creation
            # Export to temp directory first, then zip
            temp_dir = tempfile.mkdtemp(prefix='filtermate_export_')
            try:
                # Create temp config pointing to temp directory
                temp_config = ExportConfig(
                    layers=config.layers,
                    output_path=temp_dir,
                    datatype=config.datatype,
                    projection=config.projection,
                    style_format=config.style_format,
                    save_styles=config.save_styles,
                    batch_mode=True,
                    batch_zip=False  # Prevent recursion
                )

                # Export to temp directory
                result = self.export_multiple_to_directory(temp_config)

                if result.success:
                    # Create ZIP archive
                    zip_path = config.output_path
                    if not zip_path.endswith('.zip'):
                        zip_path = zip_path + '.zip'

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, temp_dir)
                                zipf.write(file_path, arcname)

                    result.output_path = zip_path
                    logger.info(f"Created ZIP archive: {zip_path} with {result.exported_count} layers")

                return result

            finally:
                # Clean up temp directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

        return self.export_multiple_to_directory(config)

    def get_layer_by_name(self, layer_name: str) -> Optional[QgsVectorLayer]:
        """
        Get layer object from project by name.

        Args:
            layer_name: Layer name to search for

        Returns:
            QgsVectorLayer or None if not found
        """
        if not self.project:
            return None

        layers_found = self.project.mapLayersByName(layer_name)
        if layers_found:
            return layers_found[0]

        logger.warning(f"Layer '{layer_name}' not found in project")
        return None
