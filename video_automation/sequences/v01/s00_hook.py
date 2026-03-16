"""
V01 Sequence 0 — HOOK (0:00 - 0:15)
====================================
Ecran QGIS avec carte chargee, texte anime "1 million d'entites / 2 secondes".
Transition vers logo FilterMate.

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S00Hook(TimelineSequence):
    name = "V01 — Hook"
    sequence_id = "v01_s00"
    duration_estimate = 15.0
    obs_scene = "Intro"
    diagram_ids = []
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        scenes = config["obs"]["scenes"]
        canvas = config["qgis"]["regions"].get("main_canvas", {})
        qgis_scene = scenes.get("qgis_fullscreen", "QGIS Fullscreen")

        # Compute canvas center for mouse panning
        if canvas:
            cx = canvas["x"] + canvas["width"] // 2
            cy = canvas["y"] + canvas["height"] // 2
        else:
            cx, cy = 960, 540

        return [
            # Cue 0: Title card — narration starts over intro scene
            NarrationCue(
                label="Hook intro",
                text=(
                    "Un million de bâtiments dans votre base de données. "
                    "Vous cherchez uniquement ceux qui touchent une route précise. "
                    "Temps de réponse ? Deux secondes."
                ),
                sync="during",
                actions=lambda: qgis.wait(2.0),  # Hold on intro card
                post_delay=0.5,
            ),
            # Cue 1: Cut to QGIS — show map complexity
            NarrationCue(
                label="Bienvenue dans FilterMate",
                text="Bienvenue dans FilterMate.",
                scene=qgis_scene,
                sync="before",  # Switch scene + focus, THEN narrate
                actions=lambda: (
                    qgis.focus_qgis(),
                ),
                post_delay=0.3,
            ),
            # Cue 2: Pan over the map while narrating the video overview
            NarrationCue(
                label="Presentation video",
                text=(
                    "Dans cette première vidéo, on va installer le plugin ensemble, "
                    "découvrir son interface, et réaliser votre tout premier filtrage "
                    "en moins de 7 minutes."
                ),
                sync="during",
                actions=lambda: (
                    qgis.move_mouse_to(cx - 200, cy - 100, duration=1.5),
                    qgis.wait(0.5),
                    qgis.move_mouse_to(cx + 200, cy + 100, duration=1.5),
                ),
                post_delay=1.0,
            ),
        ]
