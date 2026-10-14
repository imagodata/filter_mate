# -*- coding: utf-8 -*-
"""
FilterMate Public API Adapter.

Provides the concrete implementation of the public API port
for inter-plugin communication.

Version: 4.7.0 (Sprint 1 - Narractive Integration)
"""
__all__ = [
    'FilterMatePublicAPI',
]


def __getattr__(name):
    """Import the Qt adapter lazily: ``operations`` stays importable on its own."""
    if name == 'FilterMatePublicAPI':
        from .filter_mate_public_api import FilterMatePublicAPI
        return FilterMatePublicAPI
    raise AttributeError(name)
