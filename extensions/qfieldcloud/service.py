# -*- coding: utf-8 -*-
"""
QFieldCloud service — orchestrates the full export-to-push workflow.

Coordinates:
1. GPKG export (delegates to existing FilterMate export)
2. Project .qgs generation (delegates to ProjectBuilder)
3. Upload + packaging (delegates to QFieldCloudAdapter)
"""

import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .exceptions import QFieldCloudError

logger = logging.getLogger('FilterMate.Extensions.QFieldCloud.Service')


@dataclass
class QFieldCloudPushResult:
    """Result of a push operation."""
    success: bool = False
    project_id: str = ""
    project_url: str = ""
    job_id: str = ""
    files_uploaded: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        return (
            f"PushResult({status}: project={self.project_id}, "
            f"files={self.files_uploaded}, {self.duration_seconds:.1f}s)"
        )


class QFieldCloudService:
    """
    Orchestrate FilterMate -> QFieldCloud workflow.

    Full push pipeline:
        1. Export GPKG via FilterMate's existing export
        2. Generate .qgs project with QFieldSync properties
        3. Upload to QFieldCloud
        4. Trigger packaging job (optional)
    """

    def __init__(
        self,
        adapter,
        credentials_manager,
        signals=None,
    ):
        """
        Args:
            adapter: QFieldCloudAdapter instance
            credentials_manager: CredentialsManager instance
            signals: QFieldCloudSignals instance (optional)
        """
        self._adapter = adapter
        self._credentials = credentials_manager
        self._signals = signals

    def push_project(
        self,
        project_name: str,
        gpkg_path: Path,
        description: str = "",
        styles_dir: Optional[Path] = None,
        layer_actions: Optional[Dict[str, str]] = None,
        srid: Optional[int] = None,
        auto_package: bool = True,
        existing_project_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> QFieldCloudPushResult:
        """
        Push a GPKG + generated .qgs to QFieldCloud.

        Args:
            project_name: Name for the QFieldCloud project
            gpkg_path: Path to the exported GeoPackage
            description: Project description
            styles_dir: Optional path to QML style files
            layer_actions: Layer -> QFieldSync action mode mapping
            srid: EPSG code for the project CRS. None = read from
                FilterMate config (``default_srid``), falling back to 4326.
            auto_package: Trigger packaging after upload
            existing_project_id: Update existing project instead of creating new
            progress_callback: Called with (percent, message)

        Returns:
            QFieldCloudPushResult
        """
        start_time = time.time()
        result = QFieldCloudPushResult()
        tmp_dir = None

        # Resolve default SRID from team-level config when caller didn't pin one
        if srid is None:
            if self._credentials is not None and hasattr(self._credentials, "get_default_srid"):
                try:
                    srid = self._credentials.get_default_srid()
                except Exception:
                    srid = 4326
            else:
                srid = 4326

        def _progress(percent: int, msg: str):
            if progress_callback:
                progress_callback(percent, msg)
            if self._signals:
                self._signals.progress_updated.emit(percent, msg)

        try:
            _progress(0, "Preparing project files...")

            # Create temporary directory for project assembly
            tmp_dir = Path(tempfile.mkdtemp(prefix="filtermate_qfc_"))

            # Copy GPKG to temp dir
            gpkg_dest = tmp_dir / f"{project_name}.gpkg"
            shutil.copy2(str(gpkg_path), str(gpkg_dest))

            # Copy styles if provided
            if styles_dir and styles_dir.is_dir():
                styles_dest = tmp_dir / "styles"
                shutil.copytree(str(styles_dir), str(styles_dest))
            else:
                styles_dest = None

            _progress(10, "Generating QGIS project file...")

            # Generate .qgs project
            from .project_builder import QFieldProjectBuilder

            builder = QFieldProjectBuilder(
                gpkg_path=gpkg_dest,
                output_dir=tmp_dir,
                project_name=project_name,
                srid=srid,
                styles_dir=styles_dest,
                layer_actions=layer_actions,
            )
            qgs_path = builder.build()

            _progress(25, "Connecting to QFieldCloud...")

            # Create or find project
            if existing_project_id:
                project_id = existing_project_id
                _progress(30, f"Updating project {project_id}...")
            else:
                existing = self._adapter.find_project_by_name(project_name)
                if existing:
                    project_id = existing['id']
                    _progress(30, f"Found existing project: {project_name}")
                else:
                    _progress(30, f"Creating project: {project_name}")
                    project_data = self._adapter.create_project(
                        name=project_name,
                        description=description,
                    )
                    project_id = project_data['id']

            _progress(35, "Uploading files...")

            # Upload all files from temp dir
            def _upload_progress(percent, msg):
                # Scale upload progress to 35-85% range
                scaled = 35 + int(percent * 0.5)
                _progress(scaled, msg)

            files_uploaded = self._adapter.upload_project_files(
                project_id=project_id,
                local_dir=tmp_dir,
                progress_callback=_upload_progress,
            )

            result.files_uploaded = files_uploaded
            result.project_id = project_id
            result.project_url = self._adapter.get_project_url(project_id)

            # Trigger packaging if requested
            if auto_package:
                _progress(85, "Triggering packaging job...")
                try:
                    job_id = self._adapter.trigger_package(project_id)
                    result.job_id = job_id
                    _progress(90, f"Packaging started (job: {job_id})")
                except QFieldCloudError as e:
                    result.warnings.append(f"Packaging trigger failed: {e}")
                    logger.warning("Packaging trigger failed: %s", e)

            result.success = True
            result.duration_seconds = time.time() - start_time

            _progress(100, "Push complete!")

            # Emit success signal
            if self._signals:
                self._signals.project_pushed.emit(
                    project_id, project_name, result.project_url
                )

            logger.info(
                "Push complete: %s (%d files, %.1fs)",
                project_name, files_uploaded, result.duration_seconds,
            )

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.duration_seconds = time.time() - start_time

            if self._signals:
                self._signals.push_failed.emit(project_name, str(e))

            logger.exception("Push failed for '%s': %s", project_name, e)

        finally:
            # Cleanup temp directory
            if tmp_dir and tmp_dir.exists():
                try:
                    shutil.rmtree(str(tmp_dir))
                except Exception as e:
                    logger.warning("Failed to cleanup temp dir %s: %s", tmp_dir, e)

        return result

    def batch_push_zones(
        self,
        zone_configs: List[Dict],
        project_prefix: str = "WYRE",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[QFieldCloudPushResult]:
        """
        Push multiple zones sequentially.

        Each zone_config dict should contain:
            - gpkg_path: Path to the zone's GPKG
            - zone_name: Zone identifier (e.g., "POP_001")
            - styles_dir: Optional path to styles
            - layer_actions: Optional layer action mapping
            - description: Optional description
            - srid: Optional EPSG code

        Args:
            zone_configs: List of zone configuration dicts
            project_prefix: Prefix for project names
            progress_callback: Global progress callback

        Returns:
            List of QFieldCloudPushResult (one per zone)
        """
        results = []
        total = len(zone_configs)

        for i, config in enumerate(zone_configs):
            zone_name = config.get('zone_name', f'zone_{i}')
            project_name = f"{project_prefix}-{zone_name}"

            if progress_callback:
                progress_callback(
                    int(i / total * 100),
                    f"Processing zone {i + 1}/{total}: {zone_name}",
                )

            result = self.push_project(
                project_name=project_name,
                gpkg_path=Path(config['gpkg_path']),
                description=config.get('description', ''),
                styles_dir=Path(config['styles_dir']) if config.get('styles_dir') else None,
                layer_actions=config.get('layer_actions'),
                srid=config.get('srid', 31370),
            )
            results.append(result)

            if not result.success:
                logger.warning(
                    "Zone %s failed: %s", zone_name, result.error_message
                )

        # Emit batch signal
        succeeded = sum(1 for r in results if r.success)
        failed = total - succeeded
        if self._signals:
            self._signals.batch_completed.emit(total, succeeded, failed)

        if progress_callback:
            progress_callback(100, f"Batch complete: {succeeded}/{total} OK")

        return results
