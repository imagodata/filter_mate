"""How a validated server attribute filter reaches its provider, per QGIS version.

No QGIS imports: the adapter passes ``Qgis.QGIS_VERSION_INT`` and whether
the provider metadata declares ``ParallelCreateProvider``.

ASYNC: a QgsTask prepares the filtered provider and its rollback, the layer
consumes the preloaded provider (``readLayerXml``, QGIS >= 3.32).
SYNC: ``setSubsetString`` on the main thread, as FilterMate did before 5.0
(WFS only, where the provider survives it).
REFUSE: the previous filter is kept with a clear message.
"""

ASYNC = 'async'
SYNC = 'sync'
REFUSE = 'refuse'

# readLayerXml(..., preloadedProvider) and ParallelCreateProvider.
PRELOADED_PROVIDER_MIN = 33200

# WFS and ArcGIS Feature Server do not all declare ParallelCreateProvider.
# Their transfer is allowed on every QGIS that has the API, because its
# whole lifecycle passed on each version tested (October 2026, local HTTP
# fixtures of tests/qgis_headless/check_stream_versions.py and
# check_stream_vector_filters.py): candidate and rollback providers created
# in the task, HTTP-200 service errors (ArcGIS JSON, WFS OWS ExceptionReport)
# and HTTP 500 refused, timeout and cancellation without a late mutation,
# failed installation restored, a map canvas downloading the layer
# meanwhile. Proven on 3.32.3 (the last 3.32 release), 3.34.5, 3.36.1,
# 3.36.3, 3.38.3, 3.40.15, 3.42.3, 3.44.15, 4.0.3, 4.2.3 and the 4.3 nightly,
# Qt 5 and Qt 6; no tested version failed, so the rule has no upper bound.
# (QGIS itself reads a WFS 1.0 ServiceExceptionReport as an empty result, on
# every version: that rejection gives an empty layer.) Database connections
# have thread-specific state: never assume they support the pattern unless
# their provider declares it.
_VERIFIED_WEB_PROVIDERS = ('wfs', 'arcgisfeatureserver')

# The WFS setter sends no request (features download when read). On 3.22
# it resets the provider's shared cache in place: a render or any other
# iterator still reading the layer then corrupts the heap (3.22.16: 12
# crashes in 27 runs with a map canvas downloading the layer, during its
# render or just after it was canceled). 3.24.3 and 3.26.1 never crashed
# (0 in 66 runs each, 60 of them under load), nor did 3.28.15 (0 in 18), but
# on 3.24 and 3.26 the setter can wait for that download to end, bounded by
# the running request (up to 4.3 s and 3.6 s measured with a 1.5 s server
# delay under load); 3.28 does not wait (1 - 89 ms). Raise this to 32800 to
# avoid that wait at the cost of refusing WFS on 3.24 - 3.26.
WFS_SETTER_SAFE_MIN = 32400


def transfer_mode(provider_key, qgis_version_int, declares_parallel):
    """Pick ASYNC, SYNC or REFUSE for a server filter.

    Args:
        provider_key: ``layer.providerType()`` (any case).
        qgis_version_int: ``Qgis.QGIS_VERSION_INT``.
        declares_parallel: the provider metadata declares
            ``ParallelCreateProvider`` (always False before QGIS 3.32).

    Returns:
        str: ASYNC, SYNC or REFUSE.
    """
    key = (provider_key or '').lower()
    if qgis_version_int >= PRELOADED_PROVIDER_MIN and (declares_parallel or key in _VERIFIED_WEB_PROVIDERS):
        return ASYNC
    if key == 'wfs' and qgis_version_int >= WFS_SETTER_SAFE_MIN:
        # ArcGIS fetches its object IDs inside the setter and would freeze
        # the interface, so it has no such fallback.
        return SYNC
    return REFUSE
