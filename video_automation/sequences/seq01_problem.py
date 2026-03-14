"""
Séquence 1 — LE PROBLÈME (0:45)
=================================
Visuel: Frictions avec le filtrage natif QGIS.
Diagramme 1 affiché après la narration.
"""

from __future__ import annotations

from sequences.base import VideoSequence


class Seq01Problem(VideoSequence):
    name = "Le Problème — Pourquoi FilterMate ?"
    sequence_id = "seq01"
    duration_estimate = 45.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = ["01_positioning"]
    narration_text = (
        "En SIG, le filtrage est une tâche centrale. "
        "Mais QGIS native a ses limites : expressions complexes, aucun historique, "
        "aucun système de favoris, performance dégradée sur les grosses sources. "
        "FilterMate résout tout ça. C'est un plugin open source, "
        "entièrement intégré à QGIS 3 et 4, avec une architecture multi-backend "
        "qui choisit automatiquement la meilleure stratégie selon votre données source."
    )

    def execute(self, obs, qgis, config):
        """
        Show the QGIS expression builder to illustrate complexity,
        then display the positioning diagram.
        """
        # 1. Open the Layer Properties / Expression dialog to show complexity
        #    (Ctrl+F opens Feature Filter / Attribute Table query in some contexts)
        #    In this demo we simply open the attribute table and show the expression.
        import pyautogui  # type: ignore
        qgis.focus_qgis()
        qgis.wait(1.0)

        # 2. Demonstrate the pain: open a layer properties or attribute filter
        #    We simulate this by pressing Ctrl+F (search / find) or F6 (open attribute table)
        # NOTE: In a real run, ensure a layer is selected in QGIS before this step.
        pyautogui.hotkey("ctrl", "F6")   # Open attribute table
        qgis.wait(2.0)

        # Move mouse to expression bar area to draw attention
        qgis.move_mouse_to(960, 540, duration=1.0)
        qgis.wait(1.5)

        # Close the dialog
        pyautogui.press("escape")
        qgis.wait(1.0)

        # 3. Display the positioning diagram (Problem vs Solution)
        self.show_diagram(obs, "01_positioning", duration=10.0)

        # 4. Return focus to QGIS
        qgis.focus_qgis()
        qgis.wait(1.0)
