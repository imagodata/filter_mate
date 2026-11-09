"""Main-thread application state shared by server jobs and mutation entry points.

No QGIS imports: adapters own the jobs stored here. Workers never mutate the
registry or touch project layers. Keeping this separate lets GUI and REST
guards consult it without importing Qt/task classes.
"""

ACTIVE_SERVER_FILTERS = {}


def server_filter_pending():
    """Whether a server provider is being prepared or installed."""
    return bool(ACTIVE_SERVER_FILTERS)
