"""FilterMate MCP server: lets an AI assistant drive the FilterMate REST API.

The server speaks the Model Context Protocol over stdio and relays each tool
call to the local REST API (``filtermate_api``) that runs inside QGIS. It runs
*outside* QGIS, started by the MCP client::

    python -m filtermate_api.mcp

Nothing in this sub-package imports ``qgis`` or ``fastapi``, and the ``mcp``
SDK is only imported by :mod:`filtermate_api.mcp.server`: loading the plugin
(or this package) never needs the SDK. Requires Python 3.10+ and
``pip install mcp`` (see ``requirements-mcp.txt``).
"""
