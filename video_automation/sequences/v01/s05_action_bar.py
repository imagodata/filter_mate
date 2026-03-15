"""
V01 Sequence 5 — LES 6 BOUTONS DE L'ACTION BAR (3:00 - 3:30)
=============================================================
Zoom sur l'Action Bar. Hover chaque bouton.
Montrer le changement d'activation selon l'onglet FILTERING/EXPORTING.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


ACTION_BUTTONS = [
    ("filter_button", "Filter — applique le filtre configure"),
    ("undo_button", "Undo — annule le dernier filtre"),
    ("redo_button", "Redo — retablit un filtre annule"),
    ("unfilter_button", "Unfilter — retire TOUS les filtres"),
    ("export_button", "Export — exporte les donnees filtrees"),
    ("about_button", "About — toujours actif, infos et config"),
]


class V01S05ActionBar(VideoSequence):
    name = "V01 — Action Bar (6 boutons)"
    sequence_id = "v01_s05"
    duration_estimate = 30.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_action_bar_context"]
    narration_text = V01_NARRATION_TEXTS["v01_s05"]

    def execute(self, obs, qgis, config):
        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Hover each action button
        for region_name, description in ACTION_BUTTONS:
            self._log.info("Hovering: %s", description)
            qgis.hover_region(region_name, duration=2.0)

        # 2. Show FILTERING tab active — buttons Filter/Undo/Redo/Unfilter enabled
        self._log.info("Showing button states: FILTERING tab")
        qgis.select_tab("FILTERING")
        qgis.wait(1.0)
        qgis.highlight_area("action_bar_zone", duration=2.0)

        # 3. Switch to EXPORTING tab — show buttons change state
        self._log.info("Showing button states: EXPORTING tab")
        qgis.select_tab("EXPORTING")
        qgis.wait(1.0)
        qgis.highlight_area("action_bar_zone", duration=2.0)

        # 4. Return to FILTERING
        qgis.select_tab("FILTERING")
        qgis.wait(0.5)

        # 5. Show activation diagram
        self.show_diagram(obs, "v01_action_bar_context", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
