"""
V01 Sequence 8 — CHANGEMENT DE LANGUE (5:20 - 5:40)
====================================================
Ouvrir la config FilterMate, changer la langue FR -> EN -> JA.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S08Language(VideoSequence):
    name = "V01 — Changement de langue (22 langues)"
    sequence_id = "v01_s08"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_languages"]
    narration_text = (
        "FilterMate parle 22 langues. Francais, anglais, espagnol, allemand, "
        "chinois, japonais, arabe... La langue se change dans la configuration. "
        "Changeons vers l'anglais... Toute l'interface se met a jour immediatement, "
        "sans relancer le plugin."
    )

    def execute(self, obs, qgis, config):
        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Open FilterMate config (About > Config tab)
        self._log.info("Opening FilterMate config for language change")
        qgis.open_filtermate_config()
        qgis.wait(1.0)

        # 2. Navigate to language parameter in JSON TreeView
        #    (locale-specific — look for LANGUAGE or LANGUE)
        qgis.wait(2.0)

        # 3. Change to English
        self._log.info("Changing language to English")
        qgis.wait(2.0)

        # 4. Show interface updated
        qgis.focus_filtermate()
        qgis.wait(2.0)

        # 5. Show languages diagram
        self.show_diagram(obs, "v01_languages", duration=5.0)

        qgis.focus_filtermate()
        qgis.wait(0.5)
