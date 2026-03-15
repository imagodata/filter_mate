"""
V01 Sequence 13 — CONCLUSION & RESSOURCES (6:55 - 7:10)
========================================================
Ecran de fin : logo, liens GitHub / QGIS Plugins / Documentation, CTA.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S13Conclusion(VideoSequence):
    name = "V01 — Conclusion & Ressources"
    sequence_id = "v01_s13"
    duration_estimate = 15.0
    obs_scene = "Outro"
    diagram_ids = []
    narration_text = V01_NARRATION_TEXTS["v01_s13"]

    def setup(self, obs, qgis, config):
        obs.switch_scene(config["obs"]["scenes"].get("outro_scene", "Outro"))
        qgis.wait(2.0)

    def execute(self, obs, qgis, config):
        # Outro title card plays for the full duration (narration fills the time)
        self._log.info("Playing outro with links")
        qgis.wait(12.0)
