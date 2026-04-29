# -*- coding: utf-8 -*-
"""
Filter Configuration Builder Service.

A3 paire 4 fusion (audit 2026-04-29): consolidates the two former
modules ``filter_parameter_builder.py`` and ``layer_filter_builder.py``
into a single namespace. Both belonged to the same conceptual unit —
"build the configuration needed to run a filter task" — but were split
across two files with very few shared callers (initialization_handler
and filter_mate_app respectively).

The two responsibilities remain functionally distinct and so live as
two classes side by side:

* :class:`FilterParameterBuilder` (formerly ``filter_parameter_builder``)
    initialises the per-layer parameters needed to filter the *source*
    layer: provider detection, schema validation, geometry column,
    primary key, combine operators, etc.

* :class:`LayerFilterBuilder` (formerly ``layer_filter_builder``)
    extracts and validates the *list of cascade layers* the user
    selected as filter targets. Auto-fills missing properties, refreshes
    PROJECT_LAYERS in place.

Co-locating them simplifies the import surface (one module instead of
two) and makes the conceptual link explicit. They keep their own
loggers / dataclasses so existing callers and log scrapers see no
behavioural change.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from qgis.core import QgsProject, QgsVectorLayer

# infrastructure deps used by LayerFilterBuilder ------------------------
from ...infrastructure.utils.layer_utils import detect_layer_provider_type
from ...infrastructure.utils.validation_utils import is_layer_source_available


# ===========================================================================
# Section 1 — Filter Parameter Builder
# ===========================================================================
# Initialises filter parameters for the SOURCE layer. Was extracted from
# FilterTask._initialize_source_filtering_parameters() in EPIC-1 Phase 14.4.

_param_logger = logging.getLogger('FilterMate.Core.Services.FilterParameterBuilder')


# Constants ------------------------------------------------------------------

PROVIDER_POSTGRES = 'postgresql'
PROVIDER_SPATIALITE = 'spatialite'
PROVIDER_OGR = 'ogr'

REQUIRED_INFO_KEYS = [
    "layer_provider_type",
    "layer_name",
    "layer_id",
    "layer_geometry_field",
    "primary_key_name"
]


# Data Classes ---------------------------------------------------------------


@dataclass
class FilterParameters:
    """Result of filter parameter initialization."""
    # Basic layer info
    provider_type: str
    layer_name: str
    layer_id: str
    table_name: str
    schema: str
    geometry_field: str
    primary_key_name: str

    # Provider detection flags
    forced_backend: bool = False
    postgresql_fallback: bool = False

    # Filtering configuration
    has_combine_operator: bool = False
    source_layer_combine_operator: str = "AND"
    other_layers_combine_operator: str = "AND"
    old_subset: str = ""
    field_names: List[str] = field(default_factory=list)

    # Auto-filled info dict (for reference)
    infos: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterBuilderContext:
    """Context for parameter building."""
    task_parameters: Dict[str, Any]
    source_layer: Any  # QgsVectorLayer
    postgresql_available: bool = True
    detect_provider_fn: Optional[Callable] = None
    sanitize_subset_fn: Optional[Callable] = None


# Service --------------------------------------------------------------------


class FilterParameterBuilder:
    """
    Service for building filter parameters from task parameters and source layer.

    Example:
        builder = FilterParameterBuilder()
        params = builder.build(context)
    """

    def build(self, context: ParameterBuilderContext) -> FilterParameters:
        """Build filter parameters from context."""
        infos = context.task_parameters.get("infos", {}).copy()

        # Step 1: Auto-fill missing metadata
        self._auto_fill_metadata(infos, context)

        # Step 2: Validate required keys
        self._validate_required_keys(infos)

        # Step 3: Determine effective provider type
        provider_info = self._determine_provider_type(infos, context)

        # Step 4: Validate schema for PostgreSQL
        schema = self._validate_schema(infos, context, provider_info['provider_type'])

        # Step 5: Extract basic parameters
        table_name = infos.get("layer_table_name") or infos["layer_name"]

        # Step 6: Extract filtering configuration
        filtering_config = self._extract_filtering_config(context, infos)

        # Build result
        return FilterParameters(
            provider_type=provider_info['provider_type'],
            layer_name=infos["layer_name"],
            layer_id=infos["layer_id"],
            table_name=table_name,
            schema=schema,
            geometry_field=infos["layer_geometry_field"],
            primary_key_name=infos["primary_key_name"],
            forced_backend=provider_info['forced_backend'],
            postgresql_fallback=provider_info['postgresql_fallback'],
            has_combine_operator=filtering_config['has_combine_operator'],
            source_layer_combine_operator=filtering_config['source_layer_combine_operator'],
            other_layers_combine_operator=filtering_config['other_layers_combine_operator'],
            old_subset=filtering_config['old_subset'],
            field_names=filtering_config['field_names'],
            infos=infos
        )

    def _auto_fill_metadata(
        self,
        infos: Dict[str, Any],
        context: ParameterBuilderContext
    ) -> None:
        """Auto-fill missing metadata from source layer."""
        if not context.source_layer:
            return

        # Auto-fill layer_name
        if "layer_name" not in infos or infos["layer_name"] is None:
            infos["layer_name"] = context.source_layer.name()
            _param_logger.info(f"Auto-filled layer_name='{infos['layer_name']}'")

        # Auto-fill layer_id
        if "layer_id" not in infos or infos["layer_id"] is None:
            infos["layer_id"] = context.source_layer.id()
            _param_logger.info(f"Auto-filled layer_id='{infos['layer_id']}'")

        # Auto-fill layer_provider_type
        if "layer_provider_type" not in infos or infos["layer_provider_type"] is None:
            if context.detect_provider_fn:
                detected_type = context.detect_provider_fn(context.source_layer)
                infos["layer_provider_type"] = detected_type
                _param_logger.debug(f"Auto-filled layer_provider_type='{detected_type}'")
            else:
                infos["layer_provider_type"] = 'unknown'

        # Auto-fill layer_geometry_field — see history in legacy file:
        # FIX v4.0.7 / v4.2.15 / v4.4.2 — always re-detect for PostgreSQL.
        stored_geom_field = infos.get("layer_geometry_field")
        needs_detection = (
            not stored_geom_field
            or stored_geom_field in ('NULL', 'None', '', 'geom', 'geometry')
        )
        if needs_detection:
            try:
                from qgis.core import QgsDataSourceUri
                uri = QgsDataSourceUri(context.source_layer.source())
                geom_col = uri.geometryColumn()
                if geom_col:
                    infos["layer_geometry_field"] = geom_col
                    _param_logger.info(f"Detected geometry column from URI: '{geom_col}'")
                else:
                    if infos.get("layer_provider_type") == PROVIDER_POSTGRES:
                        pg_geom_col = self._query_postgresql_geometry_column(
                            context.source_layer,
                            uri.schema() or 'public',
                            uri.table()
                        )
                        if pg_geom_col:
                            infos["layer_geometry_field"] = pg_geom_col
                            _param_logger.info(
                                "Detected geometry column from PostgreSQL catalog: "
                                f"'{pg_geom_col}'"
                            )
                        else:
                            infos["layer_geometry_field"] = stored_geom_field or 'geom'
                            _param_logger.warning(
                                "Could not detect geometry column from PostgreSQL "
                                f"catalog, using '{infos['layer_geometry_field']}'"
                            )
                    else:
                        infos["layer_geometry_field"] = stored_geom_field or 'geometry'
                _param_logger.info(
                    f"Auto-filled layer_geometry_field='{infos['layer_geometry_field']}'"
                )
            except Exception as e:
                infos["layer_geometry_field"] = stored_geom_field or 'geom'
                _param_logger.warning(f"Could not detect geometry column: {e}")

        # Auto-fill primary_key_name
        if "primary_key_name" not in infos or infos["primary_key_name"] is None:
            pk_indices = context.source_layer.primaryKeyAttributes()
            if pk_indices:
                infos["primary_key_name"] = context.source_layer.fields()[pk_indices[0]].name()
            else:
                if context.source_layer.fields():
                    infos["primary_key_name"] = context.source_layer.fields()[0].name()
                else:
                    infos["primary_key_name"] = 'id'
            _param_logger.info(f"Auto-filled primary_key_name='{infos['primary_key_name']}'")

        # Auto-fill layer_schema (empty for non-PostgreSQL)
        if "layer_schema" not in infos or infos["layer_schema"] is None:
            if infos.get("layer_provider_type") == PROVIDER_POSTGRES:
                source = context.source_layer.source()
                match = re.search(r'table="([^"]+)"\.', source)
                if match:
                    infos["layer_schema"] = match.group(1)
                else:
                    infos["layer_schema"] = 'public'
            else:
                infos["layer_schema"] = ''
            _param_logger.info(f"Auto-filled layer_schema='{infos['layer_schema']}'")

    def _query_postgresql_geometry_column(
        self,
        layer,
        schema: str,
        table: str
    ) -> Optional[str]:
        """Query PostgreSQL geometry_columns catalog (FIX v4.2.15)."""
        try:
            from ...infrastructure.utils import get_datasource_connexion_from_layer

            conn, source_uri = get_datasource_connexion_from_layer(layer)
            if conn is None:
                _param_logger.debug(
                    "No PostgreSQL connection for geometry column detection"
                )
                return None

            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f_geometry_column
                    FROM geometry_columns
                    WHERE f_table_schema = %s AND f_table_name = %s
                    LIMIT 1
                """, (schema, table))
                result = cursor.fetchone()
                if result and result[0]:
                    _param_logger.debug(
                        f"Found geometry column '{result[0]}' from catalog"
                    )
                    return result[0]

                cursor.execute("""
                    SELECT f_geography_column
                    FROM geography_columns
                    WHERE f_table_schema = %s AND f_table_name = %s
                    LIMIT 1
                """, (schema, table))
                result = cursor.fetchone()
                if result and result[0]:
                    _param_logger.debug(
                        f"Found geography column '{result[0]}' from catalog"
                    )
                    return result[0]

                _param_logger.debug(
                    f"No geometry column found in catalog for {schema}.{table}"
                )
                return None
            finally:
                if cursor:
                    cursor.close()
        except Exception as e:
            _param_logger.debug(f"Error querying PostgreSQL geometry column: {e}")
            return None

    def _validate_required_keys(self, infos: Dict[str, Any]) -> None:
        missing_keys = [
            k for k in REQUIRED_INFO_KEYS
            if k not in infos or infos[k] is None
        ]
        if missing_keys:
            error_msg = f"task_parameters['infos'] missing required keys: {missing_keys}"
            _param_logger.error(error_msg)
            raise KeyError(error_msg)

    def _determine_provider_type(
        self,
        infos: Dict[str, Any],
        context: ParameterBuilderContext
    ) -> Dict[str, Any]:
        provider_type = infos["layer_provider_type"]

        forced_backends = context.task_parameters.get('forced_backends', {})
        source_layer_id = infos.get("layer_id")
        forced = forced_backends.get(source_layer_id) if source_layer_id else None

        if forced:
            _param_logger.debug(f"🔒 Source layer: Using FORCED backend '{forced}'")
            return {
                'provider_type': forced,
                'forced_backend': True,
                'postgresql_fallback': False
            }

        if provider_type == PROVIDER_POSTGRES:
            if not context.postgresql_available:
                _param_logger.info(
                    "PostgreSQL layer: using QGIS native API "
                    "(psycopg2 not available for advanced features)"
                )
            else:
                _param_logger.debug("PostgreSQL backend: full functionality with psycopg2")

        return {
            'provider_type': provider_type,
            'forced_backend': False,
            'postgresql_fallback': False
        }

    def _validate_schema(
        self,
        infos: Dict[str, Any],
        context: ParameterBuilderContext,
        provider_type: str
    ) -> str:
        stored_schema = infos.get("layer_schema", "")

        if provider_type != PROVIDER_POSTGRES or not context.source_layer:
            return stored_schema

        try:
            from qgis.core import QgsDataSourceUri
            source_uri = QgsDataSourceUri(context.source_layer.source())
            detected_schema = source_uri.schema()

            if detected_schema:
                if stored_schema != detected_schema:
                    _param_logger.info(
                        f"Schema mismatch: stored='{stored_schema}', actual='{detected_schema}'"
                    )
                    _param_logger.info(f"Using actual schema: '{detected_schema}'")
                return detected_schema
            elif stored_schema and stored_schema != 'NULL':
                return stored_schema
            else:
                _param_logger.info("No schema detected, using default: 'public'")
                return 'public'
        except Exception as e:
            _param_logger.warning(f"Could not detect schema from layer source: {e}")
            return stored_schema if stored_schema and stored_schema != 'NULL' else 'public'

    def _extract_filtering_config(
        self,
        context: ParameterBuilderContext,
        infos: Dict[str, Any]
    ) -> Dict[str, Any]:
        filtering_params = context.task_parameters.get("filtering", {})

        has_combine_operator = filtering_params.get("has_combine_operator", False)

        source_combine_op = "AND"
        other_combine_op = "AND"

        if has_combine_operator:
            source_combine_op = filtering_params.get("source_layer_combine_operator", "AND") or "AND"
            other_combine_op = filtering_params.get("other_layers_combine_operator", "AND") or "AND"

        primary_key_name = infos["primary_key_name"]
        field_names = []

        if context.source_layer:
            field_names = [
                f.name()
                for f in context.source_layer.fields()
                if f.name() != primary_key_name
            ]

        old_subset = ""
        if context.source_layer and context.source_layer.subsetString():
            old_subset_raw = context.source_layer.subsetString()

            if context.sanitize_subset_fn:
                old_subset = context.sanitize_subset_fn(old_subset_raw)
            else:
                old_subset = old_subset_raw

            table_name = infos.get("layer_table_name") or infos["layer_name"]
            _param_logger.info(
                f"FilterMate: Existing filter detected on {table_name}: {old_subset[:100]}..."
            )

        return {
            'has_combine_operator': has_combine_operator,
            'source_layer_combine_operator': source_combine_op,
            'other_layers_combine_operator': other_combine_op,
            'old_subset': old_subset,
            'field_names': field_names
        }


# Factory + convenience -----------------------------------------------------


def create_filter_parameter_builder() -> FilterParameterBuilder:
    """Factory function to create a FilterParameterBuilder."""
    return FilterParameterBuilder()


def build_filter_parameters(
    task_parameters: Dict[str, Any],
    source_layer: Any,
    postgresql_available: bool = True,
    detect_provider_fn: Optional[Callable] = None,
    sanitize_subset_fn: Optional[Callable] = None
) -> FilterParameters:
    """Build filter parameters (convenience wrapper)."""
    context = ParameterBuilderContext(
        task_parameters=task_parameters,
        source_layer=source_layer,
        postgresql_available=postgresql_available,
        detect_provider_fn=detect_provider_fn,
        sanitize_subset_fn=sanitize_subset_fn
    )
    return create_filter_parameter_builder().build(context)


# ===========================================================================
# Section 2 — Layer Filter Builder
# ===========================================================================
# Builds the list of cascade target layers for geometric filtering. Was
# extracted from FilterMateApp._build_layers_to_filter() for testability.

_layer_logger = logging.getLogger('FilterMate.LayerFilterBuilder')


@dataclass
class LayerFilterConfig:
    """Configuration for layer filter building."""
    auto_fill_missing: bool = True
    log_diagnostics: bool = True


@dataclass
class LayerValidationResult:
    """Result of layer validation."""
    layer_id: str
    layer_name: str
    is_valid: bool
    layer_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LayerFilterBuilder:
    """
    Builds validated lists of layers for geometric filtering.

    Example:
        builder = LayerFilterBuilder(project_layers, project)
        validated_layers = builder.build_layers_to_filter(source_layer)
    """

    def __init__(
        self,
        project_layers: Dict[str, Dict],
        project: 'QgsProject',
        config: Optional[LayerFilterConfig] = None
    ):
        self._project_layers = project_layers
        self._project = project
        self._config = config or LayerFilterConfig()

    def build_layers_to_filter(
        self,
        source_layer: 'QgsVectorLayer'
    ) -> List[Dict[str, Any]]:
        """Build list of layers to filter with validation."""
        layers_to_filter = []

        if source_layer.id() not in self._project_layers:
            _layer_logger.warning(
                f"build_layers_to_filter: layer {source_layer.name()} not in PROJECT_LAYERS"
            )
            return layers_to_filter

        raw_layers_list = self._project_layers[source_layer.id()]["filtering"].get(
            "layers_to_filter", []
        )

        if self._config.log_diagnostics:
            self._log_diagnostics(source_layer, raw_layers_list)

        for layer_id in raw_layers_list:
            result = self._validate_and_build_layer_info(layer_id, source_layer.id())

            if result.is_valid and result.layer_info:
                layers_to_filter.append(result.layer_info)
                _layer_logger.debug(f"✓ Added layer: {result.layer_name}")
            else:
                _layer_logger.warning(f"✗ Skipped layer {result.layer_name}: {result.error}")

        _layer_logger.info(f"Built layers_to_filter list with {len(layers_to_filter)} layers")
        return layers_to_filter

    def _validate_and_build_layer_info(
        self,
        layer_id: str,
        source_layer_id: str
    ) -> LayerValidationResult:
        if layer_id not in self._project_layers:
            layer_obj = self._project.mapLayer(layer_id)
            layer_name = layer_obj.name() if layer_obj else "unknown"
            return LayerValidationResult(
                layer_id=layer_id,
                layer_name=layer_name,
                is_valid=False,
                error="Not in PROJECT_LAYERS"
            )

        layer_info = self._project_layers[layer_id]["infos"].copy()
        layer_name = layer_info.get("layer_name", layer_id[:16])

        for stale_key in ['_effective_provider_type', '_postgresql_fallback', '_forced_backend']:
            layer_info.pop(stale_key, None)

        layer = self._project.mapLayer(layer_id)
        if not layer:
            return LayerValidationResult(
                layer_id=layer_id,
                layer_name=layer_name,
                is_valid=False,
                error="Layer not found in project"
            )

        if not is_layer_source_available(layer):
            return LayerValidationResult(
                layer_id=layer_id,
                layer_name=layer_name,
                is_valid=False,
                error="Invalid or source missing"
            )

        required_keys = [
            'layer_name', 'layer_id', 'layer_provider_type',
            'primary_key_name', 'layer_geometry_field', 'layer_schema'
        ]

        missing_keys = [k for k in required_keys if k not in layer_info or layer_info[k] is None]

        if missing_keys and self._config.auto_fill_missing:
            layer_info = self._auto_fill_layer_info(layer, layer_info, missing_keys)

            still_missing = [k for k in required_keys if k not in layer_info or layer_info[k] is None]
            if still_missing:
                return LayerValidationResult(
                    layer_id=layer_id,
                    layer_name=layer_name,
                    is_valid=False,
                    error=f"Missing required keys: {still_missing}"
                )

            update_info = {
                k: v for k, v in layer_info.items()
                if k not in ['_effective_provider_type', '_postgresql_fallback', '_forced_backend']
            }
            self._project_layers[layer_id]["infos"].update(update_info)

        return LayerValidationResult(
            layer_id=layer_id,
            layer_name=layer_name,
            is_valid=True,
            layer_info=layer_info
        )

    def _auto_fill_layer_info(
        self,
        layer: 'QgsVectorLayer',
        layer_info: Dict[str, Any],
        missing_keys: List[str]
    ) -> Dict[str, Any]:
        _layer_logger.debug(f"Auto-filling missing keys for {layer.name()}: {missing_keys}")

        if 'layer_name' in missing_keys or layer_info.get('layer_name') is None:
            layer_info['layer_name'] = layer.name()
        if 'layer_id' in missing_keys or layer_info.get('layer_id') is None:
            layer_info['layer_id'] = layer.id()
        if 'layer_geometry_field' in missing_keys or layer_info.get('layer_geometry_field') is None:
            layer_info['layer_geometry_field'] = self._detect_geometry_field(layer)
        if 'layer_provider_type' in missing_keys or layer_info.get('layer_provider_type') is None:
            layer_info['layer_provider_type'] = detect_layer_provider_type(layer)
        if 'layer_schema' in missing_keys or layer_info.get('layer_schema') is None:
            layer_info['layer_schema'] = self._detect_schema(layer, layer_info)
        if 'primary_key_name' in missing_keys or layer_info.get('primary_key_name') is None:
            layer_info['primary_key_name'] = self._detect_primary_key(layer)

        return layer_info

    def _detect_geometry_field(self, layer: 'QgsVectorLayer') -> str:
        try:
            from qgis.core import QgsDataSourceUri
            uri = QgsDataSourceUri(layer.source())
            geom_col = uri.geometryColumn()
            if geom_col:
                return geom_col
        except Exception:
            pass

        provider = layer.providerType()
        if provider == 'postgres':
            return 'geom'
        elif provider == 'spatialite':
            return 'geometry'
        return 'geom'

    def _detect_schema(self, layer: 'QgsVectorLayer', layer_info: Dict) -> str:
        provider_type = layer_info.get('layer_provider_type', '')

        if provider_type == 'postgresql':
            try:
                from qgis.core import QgsDataSourceUri
                source_uri = QgsDataSourceUri(layer.source())
                schema = source_uri.schema()
                if schema:
                    return schema
            except Exception:
                pass

            source = layer.source()
            match = re.search(r'table="([^"]+)"\.', source)
            if match:
                return match.group(1)
            return 'public'

        return 'NULL'

    def _detect_primary_key(self, layer: 'QgsVectorLayer') -> Optional[str]:
        pk_attrs = layer.primaryKeyAttributes()
        if pk_attrs:
            field_obj = layer.fields()[pk_attrs[0]]
            return field_obj.name()

        for f in layer.fields():
            if 'id' in f.name().lower():
                return f.name()

        for f in layer.fields():
            if f.isNumeric():
                return f.name()

        return None

    def _log_diagnostics(self, source_layer: 'QgsVectorLayer', raw_layers_list: List[str]):
        from qgis.core import QgsVectorLayer as QVL

        _layer_logger.info("=== LayerFilterBuilder DIAGNOSTIC ===")
        _layer_logger.info(f"  Source layer: {source_layer.name()} (id={source_layer.id()[:8]}...)")
        _layer_logger.info(f"  User-selected layers: {len(raw_layers_list)}")

        all_available = []
        for key in list(self._project_layers.keys()):
            if key != source_layer.id():
                layer_obj = self._project.mapLayer(key)
                if layer_obj:
                    all_available.append((layer_obj.name(), key[:8], key))

        _layer_logger.info(f"  Available layers in PROJECT_LAYERS: {len(all_available)}")
        for name, key_prefix, full_key in all_available[:5]:
            is_selected = full_key in raw_layers_list
            status = "✓" if is_selected else "✗"
            _layer_logger.debug(f"    {status} {name} ({key_prefix}...)")

        if len(all_available) > 5:
            _layer_logger.debug(f"    ... and {len(all_available) - 5} more")

        qgis_layers = [l for l in self._project.mapLayers().values() if isinstance(l, QVL)]
        missing = [
            l.name() for l in qgis_layers
            if l.id() not in self._project_layers and l.id() != source_layer.id()
        ]

        if missing:
            _layer_logger.warning(f"  ⚠️ Layers in QGIS but not in PROJECT_LAYERS: {missing[:3]}")

        _layer_logger.info("=== END DIAGNOSTIC ===")


__all__ = [
    # Section 1 — filter parameter builder
    "PROVIDER_POSTGRES",
    "PROVIDER_SPATIALITE",
    "PROVIDER_OGR",
    "REQUIRED_INFO_KEYS",
    "FilterParameters",
    "ParameterBuilderContext",
    "FilterParameterBuilder",
    "create_filter_parameter_builder",
    "build_filter_parameters",
    # Section 2 — layer filter builder
    "LayerFilterConfig",
    "LayerValidationResult",
    "LayerFilterBuilder",
]
