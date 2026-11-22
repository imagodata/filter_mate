# -*- coding: utf-8 -*-
"""
Layer facts for the workers of FilterMate's tasks (2026-11-20).

A worker asked each layer of the project its provider, its source, its id and
its name: QGIS 4.3 reports each of those calls ("providerType ... is run from a
different thread than the object lives in"), and a layer removed under a
running task was read while QGIS deleted it. They are read on the main thread
when a task is created (:func:`capture_layer_facts`) and the code that runs in
the worker asks ``filtermate_core.domain.layer_facts`` (``provider_key_of``,
``source_of``, ``id_of``, ``name_of``), which answers from that reading there
and from the layer itself everywhere else.
"""

import logging
from typing import Any, Iterable, Optional

try:
    from ...filtermate_core.domain import layer_facts
except ImportError:  # loaded outside the plugin package (unit tests)
    from filtermate_core.domain import layer_facts

from .validation_utils import is_sip_deleted

logger = logging.getLogger('FilterMate.Infrastructure.LayerFacts')


def capture_layer_facts(layers: Iterable[Any] = ()) -> Optional[layer_facts.LayerFactsSnapshot]:
    """Main thread: read the layers of the project, and ``layers``, for the worker of a task being created.

    Args:
        layers: Layers the task is given that may not be in the project (yet, or any more).

    Returns:
        The snapshot the task keeps and releases in finished(), None when the project cannot be read
        (the worker then reads the layers themselves, as before).
    """
    try:
        from qgis.core import QgsProject
        found = list(QgsProject.instance().mapLayers().values())
        found.extend(layer for layer in layers if not isinstance(layer, str))
        return layer_facts.capture(found, is_sip_deleted)
    except Exception as exc:  # catch-all safety net: a task must start without them
        logger.debug(f"Layer facts not captured: {exc}")
        return None


def release_layer_facts(snapshot: Optional[layer_facts.LayerFactsSnapshot]) -> None:
    """Main thread, when the task ends: its layers answer for themselves again."""
    if snapshot is not None:
        snapshot.release()
