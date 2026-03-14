"""
Séquence 7 — MULTI-BACKEND COULISSES (0:45)
============================================
Visuel: Animation — même requête → 4 backends → chronométrages.
Diagramme 8 (Sélection Automatique du Backend) affiché.
"""

from __future__ import annotations

from sequences.base import VideoSequence


class Seq07Backends(VideoSequence):
    name = "Multi-Backend — Coulisses"
    sequence_id = "seq07"
    duration_estimate = 45.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["08_backends"]
    narration_text = (
        "Derrière l'interface simple, FilterMate embarque 4 backends optimisés. "
        "Il choisit automatiquement le meilleur selon le type de votre source de données. "
        "Pour PostgreSQL : vues matérialisées et requêtes parallèles. "
        "Pour Spatialite : index R-tree. "
        "Et pour tout le reste : le backend OGR universel."
    )

    def execute(self, obs, qgis, config):
        """
        This sequence is mostly diagram-driven. We briefly show QGIS,
        then dive into diagram animations.
        """
        qgis.focus_qgis()
        qgis.wait(1.0)

        # 1. Show a quick filter on different layer types to illustrate auto-selection
        qgis.focus_filtermate()
        qgis.select_tab("FILTERING")
        qgis.wait(0.5)

        # Demonstrate selecting a PostgreSQL layer (if available)
        qgis.select_layer("routes")  # PostgreSQL layer
        qgis.wait(1.0)

        # 2. Display the backend selection diagram — main content of this sequence
        self.show_diagram(obs, "08_backends", duration=20.0)

        # 3. Return to QGIS
        qgis.focus_qgis()
        qgis.wait(1.0)
