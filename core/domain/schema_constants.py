# -*- coding: utf-8 -*-
"""Domain-level schema constants shared across the favorites stack.

Single source of truth for SQLite schema identifiers and reserved UUIDs.
Both ``core/domain/favorites_manager.py`` and
``core/services/favorites_migration_service.py`` import from here so the
two never drift apart.
"""

GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"
"""Reserved project_uuid for favorites that are visible in every project."""

TABLE_FAVORITES = "fm_favorites"
TABLE_PROJECTS = "fm_projects"
