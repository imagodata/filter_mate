# -*- coding: utf-8 -*-
"""
FilterMate Public API Adapter.

Provides the concrete implementation of the public API port
for inter-plugin communication.

Version: 4.7.0 (Sprint 1 - Narractive Integration)
"""
from .filter_mate_public_api import FilterMatePublicAPI  # noqa: F401

__all__ = [
    'FilterMatePublicAPI',
]
