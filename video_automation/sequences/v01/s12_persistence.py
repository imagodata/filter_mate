"""
V01 Sequence 12 — CONFIGURATION SAUVEGARDEE AUTOMATIQUEMENT (6:40 - 6:55)
=========================================================================
Montrer le concept de persistence SQLite : config sauvee entre sessions.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S12Persistence(VideoSequence):
    name = "V01 — Config sauvegardee (SQLite)"
    sequence_id = "v01_s12"
    duration_estimate = 15.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_persistence"]
    narration_text = V01_NARRATION_TEXTS["v01_s12"]

    def execute(self, obs, qgis, config):
        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Show current state of FilterMate (configured toggles, display field)
        self._log.info("Showing persistence concept")
        qgis.highlight_area("filtermate_dock", duration=2.0)
        qgis.wait(1.0)

        # 2. Show persistence diagram
        self.show_diagram(obs, "v01_persistence", duration=6.0)

        qgis.focus_filtermate()
        qgis.wait(1.0)
