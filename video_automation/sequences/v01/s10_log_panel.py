"""
V01 Sequence 10 — QGIS LOG MESSAGES PANEL (6:00 - 6:20)
========================================================
Ouvrir Vue > Panneaux > Messages de log, cliquer onglet "FilterMate".
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S10LogPanel(VideoSequence):
    name = "V01 — QGIS Log Messages Panel"
    sequence_id = "v01_s10"
    duration_estimate = 20.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = []
    narration_text = V01_NARRATION_TEXTS["v01_s10"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        qgis.focus_qgis()
        qgis.wait(0.5)

        # 1. Open Log Messages panel via View menu
        self._log.info("Opening Log Messages panel")
        qgis.open_log_messages_panel()
        qgis.wait(1.5)

        # 2. Click on the FilterMate tab in the log panel
        self._log.info("Clicking FilterMate tab in log panel")
        region = regions.get("log_panel_filtermate_tab")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=move_dur,
            )
        qgis.wait(2.0)

        # 3. Show existing log entries (from previous s09 filter)
        qgis.wait(2.0)

        # 4. Ensure FILTERING tab is active before triggering a filter
        #    (relies on filter setup from s06 — source/target already configured)
        self._log.info("Ensuring FILTERING tab and performing filter for log entries")
        qgis.focus_filtermate()
        qgis.select_tab("FILTERING")
        qgis.wait(0.3)

        # 5. Verify source layer is set before clicking filter
        qgis.hover_region("source_layer_combo", duration=0.5)
        qgis.click_action_button("filter")
        qgis.wait(2.0)

        # 6. Show new entries in log
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=move_dur,
            )
        qgis.wait(2.0)
