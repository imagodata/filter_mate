"""
FilterMate Export Module

v4.0 EPIC-1 Phase E1-E11: Extracted from filter_task.py

This module handles layer export operations, including:
- Export parameter validation
- Style export (QML, SLD, LYRX)
- Single layer export
- Batch export to folder/zip (E11: BatchExporter)
- GeoPackage export
- Streaming export for large datasets

Exported from modules.tasks.filter_task (~1,000 lines)
Pattern: Strangler Fig migration with legacy fallback
"""

from .layer_exporter import (  # noqa: F401
    LayerExporter,
    ExportConfig,
    ExportResult,
    ExportFormat,
    OGR_EXTENSION_MAP,
    get_extension_for_format,
)

from .style_exporter import (  # noqa: F401
    StyleExporter,
    StyleFormat,
    save_layer_style,
)

from .export_validator import (  # noqa: F401
    validate_export_parameters,
    ExportValidationResult,
)

from .batch_exporter import (  # noqa: F401
    BatchExporter,
    BatchExportResult,
    sanitize_filename,
)

from .gpkg_layer_tree_writer import (  # noqa: F401
    write_layer_tree_to_gpkg,
)

from .kml_folder_writer import (  # noqa: F401
    merge_kml_with_folders,
    cleanup_individual_kmls,
)

__all__ = [
    # Layer exporter
    'LayerExporter',
    'ExportConfig',
    'ExportResult',
    'ExportFormat',
    'OGR_EXTENSION_MAP',
    'get_extension_for_format',
    # Style exporter
    'StyleExporter',
    'StyleFormat',
    'save_layer_style',
    # Validator
    'validate_export_parameters',
    'ExportValidationResult',
    # Batch exporter (v4.0 E11)
    'BatchExporter',
    'BatchExportResult',
    'sanitize_filename',
    # GPKG layer tree writer
    'write_layer_tree_to_gpkg',
    # KML folder writer
    'merge_kml_with_folders',
    'cleanup_individual_kmls',
]
