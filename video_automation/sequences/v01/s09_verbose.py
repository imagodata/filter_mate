"""
V01 Sequence 9 — MODE VERBOSE (5:40 - 6:00)
============================================
Ouvrir la config, changer FEEDBACK_LEVEL a "verbose".
Effectuer un filtrage et montrer les messages detailles.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S09Verbose(VideoSequence):
    name = "V01 — Mode verbose (FEEDBACK_LEVEL)"
    sequence_id = "v01_s09"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_feedback_levels"]
    narration_text = (
        "Astuce pour les debutants : activez le mode verbose. "
        "Dans la configuration, changez FEEDBACK_LEVEL de normal a verbose. "
        "En mode verbose, FilterMate vous explique tout ce qu'il fait. "
        "Trois niveaux : minimal pour les erreurs, normal pour un retour equilibre, "
        "et verbose pour tout voir."
    )

    def execute(self, obs, qgis, config):
        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Open FilterMate config
        self._log.info("Opening config for FEEDBACK_LEVEL")
        qgis.open_filtermate_config()
        qgis.wait(1.5)

        # 2. Navigate to FEEDBACK_LEVEL parameter
        #    (Scroll in JSON TreeView to APP > DOCKWIDGET > FEEDBACK_LEVEL)
        qgis.wait(2.0)

        # 3. Show the 3 options
        qgis.wait(2.0)

        # 4. Close config
        qgis.close_dialog()
        qgis.wait(0.5)

        # 5. Ensure we are on the FILTERING tab (Filter button is disabled on other tabs)
        qgis.select_tab("FILTERING")
        qgis.wait(0.5)

        # 6. Perform a quick filter to show verbose messages
        self._log.info("Performing filter to show verbose output")
        qgis.click_action_button("filter")
        qgis.wait(3.0)

        # 7. Show feedback levels diagram
        self.show_diagram(obs, "v01_feedback_levels", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
