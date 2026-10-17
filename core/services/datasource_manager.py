"""
DatasourceManager - Centralized datasource and database connection management.

Phase 4.5: God Class Reduction
Extracts ~320 lines from filter_mate_app.py related to:
- Spatialite database connections
- PostgreSQL datasource management
- Spatial index creation
- Datasource tracking and lifecycle

Follows Strangler Fig Pattern with dependency injection for testability.
"""

import os
from typing import Dict, Callable, Any
from qgis.PyQt.QtCore import QObject

# Local imports
from ...config.config import ENV_VARS
from ...infrastructure.logging import get_logger
from ...infrastructure.utils.layer_utils import (
    get_datasource_connexion_from_layer,
    get_data_source_uri,
)
from ...infrastructure.utils.task_utils import spatialite_connect
from ...infrastructure.utils.validation_utils import is_layer_source_available
from ..ports import get_backend_services

_backend_services = get_backend_services()
POSTGRESQL_AVAILABLE = _backend_services.get_postgresql_availability().postgresql_available

logger = get_logger(__name__)

# Conditional imports
try:
    import processing
    PROCESSING_AVAILABLE = True
except ImportError:
    PROCESSING_AVAILABLE = False
    logger.warning("processing module not available - spatial index creation disabled")

# Raster and point cloud layers (FilterMate 5) are not vector datasources: their
# files (.tif, .vrt, .jp2, .laz, .copc.laz...) match no OGR driver.
COVERAGE_PROVIDER_TYPES = ('raster', 'pointcloud')


class DatasourceManager(QObject):
    """
    Manages database connections, datasources, and spatial operations.

    Responsibilities:
    - Spatialite database connections with error handling
    - PostgreSQL datasource tracking and temp schema creation
    - OGR datasource management (GeoPackage, Shapefiles, etc.)
    - Spatial index creation for layers
    - Datasource lifecycle (add/update/remove)

    Phase 4.5: Extracts from filter_mate_app.py:
    - get_spatialite_connection() (58 lines)
    - add_project_datasource() (35 lines)
    - _update_datasource_for_layer() (77 lines)
    - _remove_datasource_for_layer() (77 lines)
    - update_datasource() (63 lines)
    - create_spatial_index_for_layer() (15 lines)

    Total: ~356 lines extracted (target was ~320)

    Dependency Injection:
    Uses callbacks to avoid direct coupling with FilterMateApp:
    - get_project_callback: Get current QgsProject
    - get_iface_callback: Get QGIS interface
    - get_config_data_callback: Get current CONFIG_DATA
    - set_config_data_callback: Update CONFIG_DATA
    - get_db_file_path_callback: Get Spatialite database path
    - get_temp_schema_callback: Get PostgreSQL temp schema name
    - show_error_callback: Display error messages to user
    - show_warning_callback: Display warning messages to user
    """

    def __init__(
        self,
        get_project_callback: Callable[[], Any],
        get_iface_callback: Callable[[], Any],
        get_config_data_callback: Callable[[], Dict],
        set_config_data_callback: Callable[[Dict], None],
        get_db_file_path_callback: Callable[[], str],
        get_temp_schema_callback: Callable[[], str],
        show_error_callback: Callable[[str], None],
        show_warning_callback: Callable[[str], None]
    ):
        """
        Initialize DatasourceManager with dependency injection.

        Args:
            get_project_callback: Returns current QgsProject instance
            get_iface_callback: Returns QGIS iface object
            get_config_data_callback: Returns CONFIG_DATA dictionary
            set_config_data_callback: Updates CONFIG_DATA dictionary
            get_db_file_path_callback: Returns path to Spatialite database
            get_temp_schema_callback: Returns PostgreSQL temp schema name
            show_error_callback: Shows error message to user
            show_warning_callback: Shows warning message to user
        """
        super().__init__()

        # Store callbacks
        self._get_project = get_project_callback
        self._get_iface = get_iface_callback
        self._get_config_data = get_config_data_callback
        self._set_config_data = set_config_data_callback
        self._get_db_file_path = get_db_file_path_callback
        self._get_temp_schema = get_temp_schema_callback
        self._show_error = show_error_callback
        self._show_warning = show_warning_callback

        # Internal state
        self.project_datasources: Dict[str, Dict] = {}

        logger.info("DatasourceManager initialized")

    # ====================
    # Spatialite Operations
    # ====================

    def get_spatialite_connection(self):
        """
        Get a Spatialite connection with proper error handling.

        Returns:
            Connection object or None if connection fails

        Notes:
            - Verifies database file exists
            - Uses spatialite_connect() from appUtils
            - Shows user-friendly error messages on failure
        """
        db_file_path = self._get_db_file_path()

        if not os.path.exists(db_file_path):
            error_msg = self.tr(
                "Database file does not exist: {db_file_path}"
            ).format(db_file_path=db_file_path)
            logger.error(error_msg)
            self._show_error(error_msg)
            return None

        try:
            conn = spatialite_connect(db_file_path)
            return conn
        except Exception as error:
            error_msg = self.tr(
                "Failed to connect to database {db_file_path}: {error}"
            ).format(db_file_path=db_file_path, error=error)
            logger.error(error_msg)
            self._show_error(error_msg)
            return None

    # ====================
    # Spatial Index Operations
    # ====================

    def create_spatial_index_for_layer(self, layer):
        """
        Create spatial index for a layer using QGIS processing.

        Args:
            layer: QgsVectorLayer to create spatial index for

        Notes:
            - Guards against invalid/missing source layers
            - Uses qgis:createspatialindex processing algorithm
            - Shows warning if layer invalid
        """
        if not PROCESSING_AVAILABLE:
            logger.warning("Processing module not available, cannot create spatial index")
            self._show_warning(self.tr("QGIS processing module not available to create spatial index"))
            return

        # Guard invalid/missing-source layers
        if not is_layer_source_available(layer):
            logger.warning("create_spatial_index_for_layer: layer invalid or source missing; skipping.")
            self._show_warning(self.tr("Cannot create spatial index: layer invalid or source not found."))
            return

        alg_params_createspatialindex = {
            "INPUT": layer
        }
        processing.run('qgis:createspatialindex', alg_params_createspatialindex)

    # ====================
    # PostgreSQL Datasource Operations
    # ====================

    def add_project_datasource(self, layer):
        """
        Add PostgreSQL datasource and create temp schema if needed.

        Args:
            layer: PostgreSQL layer to get connection from

        Notes:
            - Creates temp schema if not exists
            - Handles connection failures gracefully
            - Closes connection after use
        """
        connexion, source_uri = get_datasource_connexion_from_layer(layer)

        # CRITICAL FIX: Check if connexion is None (PostgreSQL unavailable or connection failed)
        if connexion is None:
            logger.warning(f"Cannot add project datasource for layer {layer.name()}: no database connection")
            return

        temp_schema = self._get_temp_schema()

        try:
            sql_statement = f'CREATE SCHEMA IF NOT EXISTS {temp_schema} AUTHORIZATION postgres;'
            logger.debug(f"SQL statement: {sql_statement}")

            with connexion.cursor() as cursor:
                cursor.execute(sql_statement)
            connexion.commit()
        except Exception as e:
            logger.warning(f"Error creating temp schema for layer {layer.name()}: {e}")
        finally:
            try:
                connexion.close()
            except (OSError, AttributeError) as e:
                logger.debug(f"Could not close connection: {e}")

    # ====================
    # Datasource Tracking Operations
    # ====================

    @staticmethod
    def _postgresql_datasource_key(source_uri) -> str:
        """Key of a PostgreSQL layer that has no authentication config.

        Built from the service, or the user / host / port / database: the
        password (which the URI of such a layer carries in clear) must never
        end up in a dictionary that is logged or saved.

        Args:
            source_uri: QgsDataSourceUri of the layer.

        Returns:
            str: e.g. ``bob@db.example:5432/gis``, or '' when nothing identifies it.
        """
        service = source_uri.service()
        if service:
            return f"service={service}"
        database = source_uri.database()
        host = source_uri.host()
        if not (database or host):
            return ''
        return f"{source_uri.username()}@{host}:{source_uri.port()}/{database}"

    def update_datasource_for_layer(self, layer_info: Dict):
        """
        Update project datasources for a given layer.

        Args:
            layer_info: Layer info dictionary with keys:
                - layer_provider_type: 'postgresql', 'ogr', 'spatialite'
                - layer_name: Display name of layer
                - layer_id: Unique layer identifier

        Notes:
            - Tracks PostgreSQL connections by authcfg_id
            - Tracks file-based datasources by absolute path
            - Handles relative paths from project directory
        """
        project = self._get_project()
        if project is None:
            logger.warning("No project available, cannot update datasource")
            return

        layer_source_type = layer_info["layer_provider_type"]
        if layer_source_type in COVERAGE_PROVIDER_TYPES:
            return
        if layer_source_type not in self.project_datasources:
            self.project_datasources[layer_source_type] = {}

        layers = [layer for layer in project.mapLayersByName(layer_info["layer_name"])
                 if layer.id() == layer_info["layer_id"]]

        if len(layers) != 1:
            return

        layer = layers[0]
        source_uri, authcfg_id = get_data_source_uri(layer)
        if source_uri is None:
            return

        if authcfg_id is not None or layer_source_type == 'postgresql':
            # PostgreSQL database: keyed by the authentication config, or by the
            # host / database / user of a layer without one. Never by the URI itself,
            # which carries the password. No connection is opened (nor kept) here: a
            # shared connection would make every task use the database of the first
            # layer; each task opens its own from its source layer.
            key = authcfg_id if authcfg_id is not None else self._postgresql_datasource_key(source_uri)
            if key and key not in self.project_datasources[layer_source_type].keys():
                self.project_datasources[layer_source_type][key] = None
        else:
            # File-based datasource (GeoPackage, Shapefile, etc.)
            uri = source_uri.uri().strip()
            relative_path = uri.split('|')[0] if len(uri.split('|')) == 2 else uri
            layer_name = uri.split('|')[1] if len(uri.split('|')) == 2 else None
            absolute_path = os.path.join(os.path.normpath(ENV_VARS["PATH_ABSOLUTE_PROJECT"]),
                                        os.path.normpath(relative_path))

            if absolute_path not in self.project_datasources[layer_source_type].keys():
                self.project_datasources[layer_source_type][absolute_path] = []

            if uri not in self.project_datasources[layer_source_type][absolute_path]:
                full_uri = absolute_path + ('|' + layer_name if layer_name is not None else '')
                self.project_datasources[layer_source_type][absolute_path].append(full_uri)

    def remove_datasource_for_layer(self, layer_info: Dict):
        """
        Remove project datasources for a given layer.

        Args:
            layer_info: Layer info dictionary with keys:
                - layer_provider_type: 'postgresql', 'ogr', 'spatialite'
                - layer_name: Display name of layer
                - layer_id: Unique layer identifier

        Notes:
            - Removes datasource from tracking
            - Handles both PostgreSQL and file-based datasources
            - Safe to call if datasource not tracked
        """
        project = self._get_project()
        if project is None:
            logger.warning("No project available, cannot remove datasource")
            return

        layer_source_type = layer_info["layer_provider_type"]
        if layer_source_type in COVERAGE_PROVIDER_TYPES:
            return
        if layer_source_type not in self.project_datasources:
            self.project_datasources[layer_source_type] = {}

        layers = [layer for layer in project.mapLayersByName(layer_info["layer_name"])
                 if layer.id() == layer_info["layer_id"]]

        if len(layers) != 1:
            return

        layer = layers[0]
        source_uri, authcfg_id = get_data_source_uri(layer)
        if source_uri is None:
            return

        if authcfg_id is not None or layer_source_type == 'postgresql':
            # PostgreSQL connection - remove from tracking
            key = authcfg_id if authcfg_id is not None else self._postgresql_datasource_key(source_uri)
            if key in self.project_datasources[layer_source_type].keys():
                del self.project_datasources[layer_source_type][key]
        else:
            # File-based datasource - remove URI from list
            uri = source_uri.uri().strip()
            relative_path = uri.split('|')[0] if len(uri.split('|')) == 2 else uri
            absolute_path = os.path.normpath(os.path.join(ENV_VARS["PATH_ABSOLUTE_PROJECT"], relative_path))

            if absolute_path in self.project_datasources[layer_source_type].keys():
                if uri in self.project_datasources[layer_source_type][absolute_path]:
                    self.project_datasources[layer_source_type][absolute_path].remove(uri)

    # ====================
    # Multi-Datasource Operations
    # ====================

    def update_datasource(self):
        """
        Update CONFIG_DATA with the active datasource.

        Determines which datasource should be active for operations:
        - PostgreSQL: If available and the project has PostgreSQL layers
        - Spatialite: Fallback for local operations

        Notes:
            - CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] is always
              empty: neither a connection nor an URI is stored (each task opens its
              own connection from its source layer)
            - Updates CONFIG_DATA["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"]
            - Shows warning if PostgreSQL layers detected but psycopg2 unavailable
            - Runs no SQL: the foreign data wrappers once created here were removed
              (the SQL was invalid and nothing read the tables)
        """
        config_data = self._get_config_data()

        # ACTIVE_POSTGRESQL never holds a connection (nor an URI): it is saved with the
        # project settings, and one connection shared by all tasks would be the wrong
        # database for every layer but the first. Each task opens its own.
        if 'postgresql' in self.project_datasources and POSTGRESQL_AVAILABLE:
            config_data["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] = ""
            config_data["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"] = \
                len(self.project_datasources['postgresql']) >= 1

        elif 'postgresql' in self.project_datasources and not POSTGRESQL_AVAILABLE:
            # PostgreSQL layers detected but psycopg2 not available
            config_data["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] = ""
            config_data["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"] = False
            self._show_warning(
                self.tr(
                    "PostgreSQL layers detected but psycopg2 is not installed. "
                    "Using local Spatialite backend. "
                    "For better performance with large datasets, install psycopg2."
                )
            )
        else:
            config_data["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] = ""
            config_data["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"] = False

        # Update CONFIG_DATA
        self._set_config_data(config_data)

    # ====================
    # State Management
    # ====================

    def get_project_datasources(self) -> Dict[str, Dict]:
        """
        Get current project datasources dictionary.

        Returns:
            Dictionary with structure:
            {
                'postgresql': {authcfg_id: connection_object, ...},
                'ogr': {absolute_path: [uri1, uri2, ...], ...},
                'spatialite': {absolute_path: [uri1, uri2, ...], ...}
            }
        """
        return self.project_datasources

    def set_project_datasources(self, datasources: Dict[str, Dict]):
        """
        Set project datasources dictionary.

        Args:
            datasources: Dictionary with datasource structure
        """
        self.project_datasources = datasources
        logger.debug(f"Updated project_datasources: {len(datasources)} provider types")

    def clear_project_datasources(self):
        """
        Clear all project datasources.

        Useful when closing project or resetting state.
        """
        self.project_datasources = {}
        logger.info("Cleared all project datasources")
