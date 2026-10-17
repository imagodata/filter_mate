# -*- coding: utf-8 -*-
"""Quiet GDAL error handler context manager (no QGIS dependency)."""


class GdalErrorHandler:
    """
    Context manager to suppress GDAL errors during operations.

    Use this when performing operations that may trigger non-critical
    GDAL errors that would otherwise pollute the console.

    Example:
        with GdalErrorHandler():
            layer.reload()
    """

    def __init__(self):
        self._pushed = False

    def __enter__(self):
        try:
            from osgeo import gdal  # noqa: F401
            gdal.PushErrorHandler('CPLQuietErrorHandler')
            self._pushed = True
        except Exception:  # nosec B110 - GDAL error handler push is best-effort; GDAL may be unavailable
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Pop only what this instance pushed: an unconditional pop removed the handler of a third party
        # (GetErrorHandler does not exist in the bindings, so the push never happened and the pop did harm).
        if self._pushed:
            self._pushed = False
            try:
                from osgeo import gdal  # noqa: F401
                gdal.PopErrorHandler()
            except Exception:  # nosec B110 - best-effort; GDAL may be unavailable
                pass
        return False
