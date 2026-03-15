"""
V01 Sequence 8 — CHANGEMENT DE LANGUE (5:20 - 5:40)
====================================================
Ouvrir la config FilterMate, changer la langue FR -> EN -> JA.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S08Language(VideoSequence):
    name = "V01 — Changement de langue (22 langues)"
    sequence_id = "v01_s08"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_languages"]
    narration_text = V01_NARRATION_TEXTS["v01_s08"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Open FilterMate config (About > Config tab)
        self._log.info("Opening FilterMate config for language change")
        qgis.open_filtermate_config()
        qgis.wait(1.0)

        # 2. Navigate to the language field in config
        lang_field = regions.get("about_config_language_field")
        if lang_field:
            self._log.info("Clicking language field")
            pyautogui.click(
                lang_field["x"], lang_field["y"],
                duration=move_dur,
            )
            qgis.wait(0.5)

            # 3. Double-click to edit, then type the new language code
            pyautogui.doubleClick(lang_field["x"], lang_field["y"])
            qgis.wait(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.typewrite("en", interval=0.08)
            pyautogui.press("return")
            qgis.wait(1.0)
        else:
            self._log.warning(
                "about_config_language_field not calibrated — "
                "skipping language change automation"
            )
            qgis.wait(2.0)

        # 4. Close config dialog
        qgis.close_dialog()
        qgis.wait(0.5)

        # 5. Show interface updated in English
        qgis.focus_filtermate()
        qgis.wait(2.0)

        # 6. Show languages diagram
        self.show_diagram(obs, "v01_languages", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
