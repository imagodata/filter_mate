# -*- coding: utf-8 -*-
"""Domain-level schema constants shared across the favorites stack.

Single source of truth for reserved UUIDs (and previously SQLite table
names — those constants were dropped 2026-04-29 per CORE-8 since the
22 SQL sites all use the literal table name and threading the constant
through would mostly add ceremony).
"""

GLOBAL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"
"""Reserved project_uuid for favorites that are visible in every project."""
