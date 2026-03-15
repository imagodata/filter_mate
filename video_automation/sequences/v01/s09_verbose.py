"""
V01 Sequence 9 — MODE VERBOSE (5:40 - 6:00)
============================================
Ouvrir la config, changer FEEDBACK_LEVEL a "verbose".
Effectuer un filtrage et montrer les messages detailles.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S09Verbose(VideoSequence):
    name = "V01 — Mode verbose (FEEDBACK_LEVEL)"
    sequence_id = "v01_s09"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_feedback_levels"]
    narration_text = V01_NARRATION_TEXTS["v01_s09"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Open FilterMate config
        self._log.info("Opening config for FEEDBACK_LEVEL")
        qgis.open_filtermate_config()
        qgis.wait(1.5)

        # 2. Navigate to FEEDBACK_LEVEL field
        feedback_field = regions.get("about_config_feedback_level_field")
        if feedback_field:
            self._log.info("Clicking FEEDBACK_LEVEL field")
            pyautogui.click(
                feedback_field["x"], feedback_field["y"],
                duration=move_dur,
            )
            qgis.wait(0.5)

            # 3. Double-click to edit and set to verbose
            pyautogui.doubleClick(feedback_field["x"], feedback_field["y"])
            qgis.wait(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite("verbose", interval=0.05)
            pyautogui.press("return")
            qgis.wait(0.5)
        else:
            self._log.warning(
                "about_config_feedback_level_field not calibrated — "
                "skipping feedback level automation"
            )
            qgis.wait(2.0)

        # 4. Close config
        qgis.close_dialog()
        qgis.wait(0.5)

        # 5. Ensure FILTERING tab is active and filter is configured
        #    (relies on filter setup from s06)
        qgis.select_tab("FILTERING")
        qgis.wait(0.5)

        # 6. Verify a source layer is selected before filtering
        qgis.hover_region("source_layer_combo", duration=1.0)

        # 7. Perform filter to show verbose messages
        self._log.info("Performing filter to show verbose output")
        qgis.click_action_button("filter")
        qgis.wait(3.0)

        # 8. Show feedback levels diagram
        self.show_diagram(obs, "v01_feedback_levels", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
