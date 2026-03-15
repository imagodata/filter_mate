"""
V01 Sequence 10 — QGIS LOG MESSAGES PANEL (6:00 - 6:20)
========================================================
Ouvrir Vue > Panneaux > Messages de log, cliquer onglet "FilterMate".
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S10LogPanel(VideoSequence):
    name = "V01 — QGIS Log Messages Panel"
    sequence_id = "v01_s10"
    duration_estimate = 20.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = []
    narration_text = (
        "En complement du mode verbose, FilterMate ecrit ses logs dans le panneau "
        "standard de QGIS. Allez dans Vue, Panneaux, Messages de log. "
        "Vous trouverez un onglet dedie FilterMate. "
        "C'est ici que vous pouvez suivre les requetes SQL generees, "
        "les temps d'execution, les erreurs eventuelles."
    )

    def execute(self, obs, qgis, config):
        import pyautogui

        qgis.focus_qgis()
        qgis.wait(0.5)

        # 1. Open Log Messages panel via View menu
        self._log.info("Opening Log Messages panel")
        qgis.open_log_messages_panel()
        qgis.wait(1.5)

        # 2. Click on the FilterMate tab in the log panel
        self._log.info("Clicking FilterMate tab in log panel")
        region = config["qgis"]["regions"].get("log_panel_filtermate_tab")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=config["timing"].get("mouse_move_duration", 0.5),
            )
        qgis.wait(2.0)

        # 3. Show log entries — hover over the content area
        qgis.wait(3.0)

        # 4. Ensure FILTERING tab is active (Filter button disabled on other tabs)
        self._log.info("Performing filter to generate log entries")
        qgis.focus_filtermate()
        qgis.select_tab("FILTERING")
        qgis.wait(0.3)
        qgis.click_action_button("filter")
        qgis.wait(2.0)

        # 5. Show new entries in log
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=config["timing"].get("mouse_move_duration", 0.5),
            )
        qgis.wait(2.0)
