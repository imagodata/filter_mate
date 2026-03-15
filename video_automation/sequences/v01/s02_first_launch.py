"""
V01 Sequence 2 — PREMIER LANCEMENT (0:45 - 1:15)
=================================================
Cliquer sur l'icone FilterMate, le dock widget s'ouvre.
Charger les donnees de demo (departements + communes).
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S02FirstLaunch(VideoSequence):
    name = "V01 — Premier lancement"
    sequence_id = "v01_s02"
    duration_estimate = 30.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = []
    narration_text = V01_NARRATION_TEXTS["v01_s02"]

    def execute(self, obs, qgis, config):
        qgis.focus_qgis()
        qgis.wait(1.0)

        # 1. Click FilterMate toolbar icon
        qgis.open_filtermate_toolbar()
        qgis.wait(2.0)

        # 2. Show the empty dock widget
        qgis.focus_filtermate()
        qgis.wait(2.0)

        # 3. Hover over the empty panel to show it's blank
        qgis.hover_region("filtermate_dock", duration=1.5)

        # 4. Load demo data — drag & drop or use Layer > Add Vector Layer
        # (Data should be pre-loaded in the demo project)
        # Here we simulate the layers appearing after project load
        qgis.wait(2.0)

        # 5. Show that the dock widget now has content
        qgis.focus_filtermate()
        qgis.wait(2.0)
