"""
V01 Sequence 0 — HOOK (0:00 - 0:15)
====================================
Ecran QGIS avec carte chargee, texte anime "1 million d'entites / 2 secondes".
Transition vers logo FilterMate.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S00Hook(VideoSequence):
    name = "V01 — Hook"
    sequence_id = "v01_s00"
    duration_estimate = 15.0
    obs_scene = "Intro"
    diagram_ids = []
    narration_text = (
        "Un million de batiments dans votre base de donnees. "
        "Vous cherchez uniquement ceux qui touchent une route precise. "
        "Temps de reponse ? Deux secondes. Bienvenue dans FilterMate. "
        "Dans cette premiere video, on va installer le plugin ensemble, "
        "decouvrir son interface, et realiser votre tout premier filtrage "
        "en moins de 7 minutes."
    )

    def execute(self, obs, qgis, config):
        # 1. Show intro title card (narration fills the time)
        qgis.wait(5.0)

        # 2. Cut to QGIS with loaded project — show complexity
        obs.switch_scene(config["obs"]["scenes"].get("qgis_fullscreen", "QGIS Fullscreen"))
        qgis.focus_qgis()
        qgis.wait(1.0)

        # 3. Pan mouse over map canvas to show 10+ layers
        canvas = config["qgis"]["regions"].get("main_canvas", {})
        if canvas:
            cx = canvas["x"] + canvas["width"] // 2
            cy = canvas["y"] + canvas["height"] // 2
            qgis.move_mouse_to(cx - 200, cy - 100, duration=1.5)
            qgis.wait(0.5)
            qgis.move_mouse_to(cx + 200, cy + 100, duration=1.5)

        # 4. Quick flash of FilterMate dock
        obs.switch_scene(config["obs"]["scenes"].get("qgis_with_filtermate", "QGIS + FilterMate"))
        qgis.focus_filtermate()
        qgis.wait(2.0)
