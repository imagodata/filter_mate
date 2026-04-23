# -*- coding: utf-8 -*-
"""
Favorites Sharing Extension for FilterMate.

Optional extension that turns the QGIS ``resource_sharing`` plugin into a
distribution channel for FilterMate favorite collections. Scans subscribed
Resource Sharing collections for ``filter_mate/favorites/*.fmfav.json`` (or
``*.fmfav-pack.json``) files, exposes the discovered favorites as
read-only entries in a new "Shared" section of the Favorites Manager
dialog, and offers a "Fork" action that materializes a shared favorite
into the current project's SQLite database.

The extension is fully optional — FilterMate works without it, and
without the ``resource_sharing`` QGIS plugin it simply scans an empty
directory and disables its UI section.
"""

from .extension import FavoritesSharingExtension

Extension = FavoritesSharingExtension

__all__ = ['Extension', 'FavoritesSharingExtension']
