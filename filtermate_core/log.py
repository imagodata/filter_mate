# -*- coding: utf-8 -*-
"""Logger access for the core.

The core never configures handlers: it only names its loggers. Vendored in the
plugin, the names fall under the plugin package (``filter_mate.filtermate_core.…``)
and propagate to the handlers ``infrastructure.logging`` installs on that root;
standalone, they are plain ``logging`` loggers the embedding program configures.
"""
import logging


def get_logger(name: str) -> logging.Logger:
    """Return the logger for ``name`` (usually the caller's ``__name__``)."""
    return logging.getLogger(name)


__all__ = ['get_logger']
