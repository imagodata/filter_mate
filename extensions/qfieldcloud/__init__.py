# -*- coding: utf-8 -*-
"""
QFieldCloud Extension for FilterMate.

Adds one-click export to QFieldCloud from FilterMate's filtered layers.
Requires the optional `qfieldcloud-sdk` package (pip install qfieldcloud-sdk).

This extension is fully optional — FilterMate works without it.
If qfieldcloud-sdk is not installed, this extension silently disables itself.
"""

from .extension import QFieldCloudExtension

# Entry point for the extension registry
Extension = QFieldCloudExtension

__all__ = ['Extension', 'QFieldCloudExtension']
