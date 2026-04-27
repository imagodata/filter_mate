# -*- coding: utf-8 -*-
"""Single source of truth for ``QgsMapLayer`` → portable signature.

Replaces three near-identical implementations that used to live in
``favorites_controller._layer_signature_for``,
``favorites_manager._backfill_remote_layer_signatures`` and
``favorites_service._resolve_signature_to_layer_id`` — every fix to the
provider parsing rules had to be applied three times. Centralising it
here means the logic can evolve in one place and the
:class:`LayerSignatureIndex` can build a project-wide map once per
operation instead of each caller re-walking ``QgsProject``.

A *signature* is a portable, project-independent string identifier of
the form ``"<provider>::<resource>"`` that survives moving a favorite
between projects whose ``QgsMapLayer`` UUIDs differ. The provider
parsing rules are:

* ``postgres`` → ``"postgres::<schema>.<table>"``
* ``spatialite`` → ``"spatialite::<table>"``
* ``ogr`` (GPKG with ``layername=``) → ``"ogr::<layername>"``
* ``ogr`` (file-based) → ``"ogr::<basename-without-extension>"``
* anything else → ``"<provider-or-unknown>::<layer.name()>"``
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LayerSignature:
    """Stateless ``QgsMapLayer`` → signature compute. The only place that
    parses provider-specific URI conventions; both forward (layer →
    signature) and inverse (signature → layer) flows funnel through it.
    """

    @staticmethod
    def compute(layer: Any) -> str:
        """Return the portable signature for ``layer``.

        Never raises. Falls back to ``"<provider>::<layer.name()>"`` (or
        ``"unknown::?"`` as last resort) when URI parsing fails — the
        caller can still use the value as a dict key, it just won't
        resolve across projects.
        """
        try:
            provider = layer.providerType() if hasattr(layer, 'providerType') else ''
        except (RuntimeError, AttributeError):
            provider = ''

        try:
            from qgis.core import QgsDataSourceUri
            if provider == 'postgres':
                uri = QgsDataSourceUri(layer.source())
                schema = uri.schema() or 'public'
                table = uri.table() or ''
                if table:
                    return f"postgres::{schema}.{table}"
            elif provider == 'spatialite':
                uri = QgsDataSourceUri(layer.source())
                table = uri.table() or ''
                if table:
                    return f"spatialite::{table}"
            elif provider == 'ogr':
                src = layer.source() or ''
                if '|layername=' in src:
                    tail = src.split('|layername=', 1)[1]
                    layername = tail.split('|', 1)[0]
                    return f"ogr::{layername}"
                base = os.path.basename(src.split('|', 1)[0])
                if base:
                    stem, _ = os.path.splitext(base)
                    return f"ogr::{stem}"
        except Exception:
            pass

        try:
            return f"{provider or 'unknown'}::{layer.name()}"
        except (RuntimeError, AttributeError):
            return f"{provider or 'unknown'}::?"


class LayerSignatureIndex:
    """Project-wide signature lookup, built once per operation.

    Walks ``QgsProject.instance().mapLayers()`` at construction time and
    caches both forward (id/name → signature) and inverse (signature →
    id) maps. Callers that resolve many signatures in one pass (import,
    backfill, restore) avoid re-enumerating the project for each entry.

    Outside QGIS (e.g. headless tests) the index is constructible but
    empty — every ``resolve`` returns ``None`` and consumers degrade to
    legacy / signature-less behaviour, matching the previous fallbacks.
    """

    def __init__(self, qgs_project: Any = None) -> None:
        self._id_to_signature: Dict[str, str] = {}
        self._signature_to_id: Dict[str, str] = {}
        self._name_to_signature: Dict[str, str] = {}

        project = qgs_project
        if project is None:
            try:
                from qgis.core import QgsProject
                project = QgsProject.instance()
            except ImportError:
                return

        if project is None:
            return

        try:
            layers = project.mapLayers()
        except (RuntimeError, AttributeError):
            return

        for lid, layer in layers.items():
            try:
                signature = LayerSignature.compute(layer)
                self._id_to_signature[lid] = signature
                self._signature_to_id.setdefault(signature, lid)
                try:
                    self._name_to_signature.setdefault(layer.name(), signature)
                except (RuntimeError, AttributeError):
                    pass
            except (RuntimeError, AttributeError):
                continue

    def resolve(self, signature: Optional[str]) -> Optional[str]:
        """Return the layer id matching ``signature`` in this project, or
        ``None`` if the signature is empty/unknown. First match wins —
        signatures should be unique within a project, but if the same
        ``schema.table`` is loaded twice we still pick deterministically.
        """
        if not signature:
            return None
        return self._signature_to_id.get(signature)

    def signature_for_id(self, lid: Optional[str]) -> Optional[str]:
        """Inverse lookup, used by ``RemoteLayersNormalizer.backfill``."""
        if not lid:
            return None
        return self._id_to_signature.get(lid)

    def signature_for_name(self, name: Optional[str]) -> Optional[str]:
        """Best-effort name lookup for legacy entries that only stored
        ``layer.name()``. Ambiguous (two layers with the same name return
        only the first) — kept for backfill of pre-signature payloads,
        not for new code.
        """
        if not name:
            return None
        return self._name_to_signature.get(name)

    @property
    def id_to_signature(self) -> Dict[str, str]:
        return self._id_to_signature

    @property
    def name_to_signature(self) -> Dict[str, str]:
        return self._name_to_signature
