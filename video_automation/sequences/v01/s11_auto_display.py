"""
V01 Sequence 11 — AUTO-DETECTION DU CHAMP D'AFFICHAGE (6:20 - 6:40)
====================================================================
Montrer que le selecteur affiche les noms, pas les IDs.
Charger une couche avec champ "nom"/"name" vs une couche generique.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S11AutoDisplay(VideoSequence):
    name = "V01 — Auto-detection champ d'affichage"
    sequence_id = "v01_s11"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_display_field_detection"]
    narration_text = V01_NARRATION_TEXTS["v01_s11"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Show the exploring layer combo with "departements" selected
        self._log.info("Showing auto-detected display field")
        qgis.select_exploring_layer("departements")
        qgis.wait(1.0)

        # 2. Open the feature selector to show readable names
        qgis.hover_region("exploring_feature_selector", duration=1.0)
        region = regions.get("exploring_feature_selector")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=move_dur,
            )
        qgis.wait(1.5)

        # 3. Scroll through a few entries to show names
        qgis.scroll_down(3)
        qgis.wait(1.0)
        qgis.scroll_up(3)
        qgis.wait(0.5)

        # Close dropdown
        pyautogui.press("escape")
        qgis.wait(0.5)

        # 4. Show detection priority diagram
        self.show_diagram(obs, "v01_display_field_detection", duration=6.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
