# -*- coding: utf-8 -*-
"""Routes are plain functions: FastAPI runs them in its thread pool.

The accessor blocks until the Qt main thread has run the operation (an export
can take minutes). An ``async def`` route would run that wait on the event loop
and freeze every other request, health check included, for its whole duration.
"""
from __future__ import annotations

import inspect

from fastapi.routing import APIRoute

from filtermate_api.server import create_app


def test_business_routes_are_not_coroutines():
    app = create_app(allow_insecure=True)
    blocking = [route.path for route in app.routes
                if isinstance(route, APIRoute) and route.path != "/"
                and inspect.iscoroutinefunction(route.endpoint)]
    assert blocking == []
