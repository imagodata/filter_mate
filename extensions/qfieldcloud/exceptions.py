# -*- coding: utf-8 -*-
"""
QFieldCloud-specific exceptions for FilterMate.

Provides a clear exception hierarchy for error handling and user messaging.
"""


class QFieldCloudError(Exception):
    """Base exception for all QFieldCloud operations."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.details = details


class QFieldCloudAuthError(QFieldCloudError):
    """Authentication failed (bad credentials, expired token, etc.)."""


class QFieldCloudUploadError(QFieldCloudError):
    """File upload failed after retries."""


class QFieldCloudProjectError(QFieldCloudError):
    """Project creation or update failed."""


class QFieldCloudTimeoutError(QFieldCloudError):
    """Operation timed out (upload, job polling, etc.)."""


class QFieldCloudDependencyError(QFieldCloudError):
    """Required dependency (qfieldcloud-sdk) is missing."""
