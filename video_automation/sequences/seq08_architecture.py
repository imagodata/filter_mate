"""
Séquence 8 — ARCHITECTURE HEXAGONALE (0:45)
============================================
Visuel: Schéma animé hexagone, couche par couche.
Diagrammes 9 (Hexagonale) et 10 (Design Patterns).
"""

from __future__ import annotations

from sequences.base import VideoSequence


class Seq08Architecture(VideoSequence):
    name = "Architecture Hexagonale"
    sequence_id = "seq08"
    duration_estimate = 45.0
    obs_scene = "Diagram Overlay"
    diagram_ids = ["09_architecture", "10_patterns"]
    narration_text = (
        "FilterMate est construit sur une architecture hexagonale — "
        "aussi appelée Ports & Adapters. "
        "Le domaine métier pur est au centre, totalement indépendant de QGIS, "
        "de la base de données ou de l'interface graphique. "
        "Cela rend le code testable à 75%, maintenable, "
        "et extensible pour de futurs backends."
    )

    def setup(self, obs, qgis, config):
        # For this sequence, start on the diagram overlay directly
        obs.switch_scene(obs.scenes.get("diagram_overlay", "Diagram Overlay"))
        qgis.wait(1.0)

    def execute(self, obs, qgis, config):
        """Show both architecture diagrams back-to-back."""
        # 1. Hexagonal architecture diagram
        self._log.info("Showing hexagonal architecture diagram")
        # (OBS browser source is already pointing to 09_architecture.html)
        qgis.wait(20.0)  # Stay on diagram while narration plays

        # 2. Design patterns mindmap
        self._log.info("Showing design patterns diagram")
        # Switch OBS browser source to patterns diagram
        # (This is handled by set_source_visibility in a real setup)
        obs.switch_scene(obs.scenes.get("diagram_overlay", "Diagram Overlay"))
        qgis.wait(15.0)

        # 3. Return to QGIS
        obs.transition_to_qgis()
        qgis.focus_qgis()
        qgis.wait(1.0)

    def teardown(self, obs, qgis, config):
        obs.transition_to_qgis()
        super().teardown(obs, qgis, config)
