# -*- coding: utf-8 -*-
"""Agent mode of FilterMate: conversation, tools and LLM providers, in pure Python.

Nothing here imports QGIS or Qt, and nothing opens a connection: a provider only
builds HTTP requests and parses response bytes. The transport (``QgsNetworkAccessManager``
in the dock, ``urllib`` in the evaluation bench) belongs to the caller.
See ``docs/AGENT_MODE.md``.
"""
