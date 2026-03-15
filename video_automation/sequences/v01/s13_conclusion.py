"""
V01 Sequence 13 — CONCLUSION & RESSOURCES (6:55 - 7:10)
========================================================
Ecran de fin : logo, liens GitHub / QGIS Plugins / Documentation, CTA.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S13Conclusion(VideoSequence):
    name = "V01 — Conclusion & Ressources"
    sequence_id = "v01_s13"
    duration_estimate = 15.0
    obs_scene = "Outro"
    diagram_ids = []
    narration_text = (
        "Voila, vous avez installe FilterMate, decouvert les 3 zones de l'interface, "
        "utilise les boutons de la barre laterale et de l'Action Bar, "
        "et realise votre premier filtrage spatial. Pas mal pour 7 minutes ! "
        "Retrouvez le code source sur GitHub, le plugin sur le depot officiel QGIS, "
        "et la documentation complete sur le site dedie. Les liens sont dans la description. "
        "Dans la prochaine video, on approfondit le filtrage geometrique. A tres vite !"
    )

    def setup(self, obs, qgis, config):
        obs.switch_scene(config["obs"]["scenes"].get("outro_scene", "Outro"))
        qgis.wait(2.0)

    def execute(self, obs, qgis, config):
        # Outro title card plays for the full duration (narration fills the time)
        self._log.info("Playing outro with links")
        qgis.wait(12.0)
