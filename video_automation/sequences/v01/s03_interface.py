"""
V01 Sequence 3 — (ABSORBÉE DANS s02_first_launch.py)
======================================================
Le contenu de l'Action Bar a été fusionné dans la séquence 2
(Premier lancement + Découverte interface + Action Bar).

Cette séquence est désormais vide et ne produit aucune cue.
Elle est conservée pour maintenir la numérotation s00-s08.
"""
from __future__ import annotations

from sequences.base import TimelineSequence


class V01S03Interface(TimelineSequence):
    name = "V01 — (Action Bar absorbée dans s02)"
    sequence_id = "v01_s03"
    duration_estimate = 0.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = []
    narration_text = ""

    def build_timeline(self, obs, qgis, config):
        return []
