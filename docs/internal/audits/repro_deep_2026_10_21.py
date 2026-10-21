"""Regression checks for audit F1-F8 and F10 (no QGIS or network required).

Run this script from any folder with pytest and the test dependencies installed.
The native QGIS companion script checks the actual raster writers and projects.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TESTS = [
    # F1: pristine, enriched, temporary and history source files.
    "tests/unit/core/export/test_export_target_guard.py::TestProjectSources",
    "tests/unit/adapters/qgis/test_coverage_exports.py::TestPointCloudExport::test_original_source_of_a_derived_cloud_is_refused_before_export",
    # F2/F3/F10: no implicit LAZ fallback, private staging, cancellation.
    "tests/unit/adapters/qgis/test_coverage_exports.py::TestPointCloudExport::test_missing_copc_support_keeps_the_original_laz_and_writes_no_fallback",
    "tests/unit/adapters/qgis/test_coverage_exports.py::TestPointCloudExport::test_existing_partial_name_is_never_used_as_staging",
    "tests/unit/adapters/qgis/test_coverage_exports.py::TestPointCloudExport::test_synchronous_helper_relays_cancel_during_export",
    # F4/F5: identity, exact ownership, bounded recovery and nonblocking shutdown.
    "tests/unit/infrastructure/database/test_connection_pool_identity_and_recovery.py",
    # F6/F7/F8: project binding, stale results, typed internal diagnostics.
    "tests/unit/adapters/qgis/test_cross_filter_task_state.py",
    "tests/unit/adapters/public_api/test_operations.py::TestUnexpectedErrorsFlagged",
]

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", *TESTS, "-q", "-o", "addopts="], cwd=str(ROOT)))
