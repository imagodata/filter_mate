"""
V01 Sequence 4 — LES 6 BOUTONS DE LA BARRE LATERALE (2:30 - 3:00)
==================================================================
Zoom sur la barre laterale de la Zone d'Exploration.
Hover chaque bouton avec annotation.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


SIDEBAR_BUTTONS = [
    ("sidebar_identify", "Identify — inspecter les attributs"),
    ("sidebar_zoom", "Zoom — centrer sur l'entite"),
    ("sidebar_select", "Select — surligner (bascule ON/OFF)"),
    ("sidebar_track", "Track — suivi automatique (bascule ON/OFF)"),
    ("sidebar_link", "Link — synchroniser les selecteurs (bascule ON/OFF)"),
    ("sidebar_reset", "Reset — reinitialiser l'exploration"),
]


class V01S04Sidebar(VideoSequence):
    name = "V01 — Barre laterale (6 boutons)"
    sequence_id = "v01_s04"
    duration_estimate = 30.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_sidebar_buttons"]
    narration_text = V01_NARRATION_TEXTS["v01_s04"]

    def execute(self, obs, qgis, config):
        qgis.focus_filtermate()
        qgis.wait(0.5)

        # Hover each sidebar button sequentially
        for region_name, description in SIDEBAR_BUTTONS:
            self._log.info("Hovering: %s", description)
            qgis.hover_region(region_name, duration=2.5)

        # Show sidebar diagram
        self.show_diagram(obs, "v01_sidebar_buttons", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
