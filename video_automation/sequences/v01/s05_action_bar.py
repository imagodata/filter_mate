"""
V01 Sequence 5 — (ABSORBÉE DANS s03_interface.py)
===================================================
Le contenu de l'Action Bar a été fusionné dans la séquence 3
(Découverte de l'interface : 3 zones + Action Bar).

Cette séquence est désormais vide et ne produit aucune cue.
Elle est conservée pour maintenir la numérotation s00-s08.
"""
from __future__ import annotations

from sequences.base import TimelineSequence


class V01S05ActionBar(TimelineSequence):
    name = "V01 — (Action Bar absorbée dans s03)"
    sequence_id = "v01_s05"
    duration_estimate = 0.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = []
    narration_text = ""

    def build_timeline(self, obs, qgis, config):
        return []
