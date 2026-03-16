"""
Interactive Calibration Tool
=============================
Records QGIS and FilterMate UI element positions by asking the user to
position the mouse on specific areas. Saves results to config.yaml.

Features:
  - Interactive menu with grouped targets
  - Show all current values with status (calibrated / not calibrated)
  - Recalibrate a single element or a group
  - Edit coordinates manually (type x y)
  - Live mouse position preview (real-time)
  - Validate coherence of positions
  - Undo last change
  - Auto-save after each change

Usage:
    python scripts/calibrate.py                # Interactive menu
    python scripts/calibrate.py --list         # Show current calibration
    python scripts/calibrate.py --reset        # Reset all regions to zero
    python scripts/calibrate.py --group dock   # Calibrate only one group
    python scripts/calibrate.py --live         # Live mouse position monitor
    python scripts/calibrate.py --validate     # Check position coherence
"""

from __future__ import annotations

import argparse
import copy
import sys
import threading
import time
from pathlib import Path

# Windows: reconfigure stdout/stderr to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"

# ── Calibration groups & targets ──────────────────────────────────────────

# Groups for organized calibration
GROUPS: dict[str, dict] = {
    "dock": {
        "label": "FilterMate Dock (contour)",
        "desc": "Contour exterieur du panneau FilterMate",
        "targets": [
            ("filtermate_dock", "coin HAUT-GAUCHE du dock FilterMate", "tl"),
            ("filtermate_dock", "coin BAS-DROITE du dock FilterMate", "br"),
        ],
    },
    "canvas": {
        "label": "Canvas QGIS + Toolbar",
        "desc": "Zones principales de QGIS",
        "targets": [
            ("main_canvas", "coin HAUT-GAUCHE du canvas carte QGIS", "tl"),
            ("main_canvas", "coin BAS-DROITE du canvas carte QGIS", "br"),
            ("toolbar", "coin HAUT-GAUCHE de la barre d'outils QGIS", "tl"),
            ("toolbar", "coin BAS-DROITE de la barre d'outils QGIS", "br"),
        ],
    },
    "header": {
        "label": "Header bar + badges",
        "desc": "En-tete du dock FilterMate avec pastilles",
        "targets": [
            ("header_bar", "coin HAUT-GAUCHE du header FilterMate", "tl"),
            ("header_bar", "coin BAS-DROITE du header FilterMate", "br"),
            ("favorites_button", "le bouton FAVORIS (etoile, dans le header)", "point"),
            ("badge_favorites", "la pastille FAVORIS (orange, dans le header)", "point"),
            ("badge_backend", "la pastille BACKEND (bleue, dans le header)", "point"),
        ],
    },
    "exploring": {
        "label": "Zone d'Exploration",
        "desc": "Zone haute du dock : combos + barre laterale",
        "targets": [
            ("exploring_zone", "coin HAUT-GAUCHE de la Zone d'Exploration", "tl"),
            ("exploring_zone", "coin BAS-DROITE de la Zone d'Exploration", "br"),
            ("tab_exploring", "l'onglet EXPLORING / EXPLORATION", "point"),
            ("exploring_layer_combo", "le combo COUCHE dans la Zone d'Exploration", "point"),
            ("exploring_feature_selector", "le combo ENTITE / FEATURE dans la Zone d'Exploration", "point"),
            ("exploring_display_field_combo", "le combo CHAMP D'AFFICHAGE dans la Zone d'Exploration", "point"),
            ("exploring_feature_prev_btn", "le bouton PRECEDENT (fleche gauche) du selecteur d'entites", "point"),
            ("exploring_feature_next_btn", "le bouton SUIVANT (fleche droite) du selecteur d'entites", "point"),
        ],
    },
    "sidebar": {
        "label": "Barre laterale Exploring (6 boutons)",
        "desc": "Les 6 boutons icones a gauche de la Zone d'Exploration",
        "targets": [
            ("sidebar_identify", "le bouton IDENTIFY (1er, en haut)", "point"),
            ("sidebar_zoom", "le bouton ZOOM (2eme)", "point"),
            ("sidebar_select", "le bouton SELECT (3eme)", "point"),
            ("sidebar_track", "le bouton TRACK (4eme)", "point"),
            ("sidebar_link", "le bouton LINK (5eme)", "point"),
            ("sidebar_reset", "le bouton RESET (6eme, en bas)", "point"),
        ],
    },
    "toolbox": {
        "label": "Toolbox (FILTERING / EXPORTING)",
        "desc": "Zone basse du dock : onglets et widgets de filtrage",
        "targets": [
            ("toolbox_zone", "coin HAUT-GAUCHE de la Toolbox", "tl"),
            ("toolbox_zone", "coin BAS-DROITE de la Toolbox", "br"),
            ("tab_filtering", "l'onglet FILTERING", "point"),
            ("tab_exporting", "l'onglet EXPORTING", "point"),
            ("source_layer_combo", "le combo COUCHE SOURCE", "point"),
        ],
    },
    "filtering_widgets": {
        "label": "Widgets FILTERING (sections depliables)",
        "desc": "IMPORTANT : depliez chaque section AVANT de calibrer !",
        "targets": [
            ("btn_toggle_layers_to_filter", "le pushbutton LAYERS TO FILTER (barre laterale gauche)", "point"),
            ("target_layer_combo", "[depliez LAYERS TO FILTER !] le combo COUCHE CIBLE", "point"),
            ("btn_toggle_geometric_predicates", "le pushbutton GEOMETRIC PREDICATES", "point"),
            ("predicate_combo", "[depliez GEOMETRIC PREDICATES !] le combo PREDICAT", "point"),
            ("btn_toggle_buffer", "le pushbutton BUFFER", "point"),
            ("buffer_enable_checkbox", "[depliez BUFFER !] la checkbox ACTIVER BUFFER", "point"),
            ("buffer_value_spinbox", "[depliez BUFFER !] le spinbox VALEUR BUFFER", "point"),
        ],
    },
    "action_bar": {
        "label": "Action Bar (6 boutons)",
        "desc": "Les 6 boutons d'action en bas du dock",
        "targets": [
            ("action_bar_zone", "coin HAUT-GAUCHE de l'Action Bar", "tl"),
            ("action_bar_zone", "coin BAS-DROITE de l'Action Bar", "br"),
            ("filter_button", "le bouton FILTER", "point"),
            ("undo_button", "le bouton UNDO", "point"),
            ("redo_button", "le bouton REDO", "point"),
            ("unfilter_button", "le bouton UNFILTER", "point"),
            ("export_button", "le bouton EXPORT", "point"),
            ("about_button", "le bouton ABOUT", "point"),
        ],
    },
    "menus": {
        "label": "Menus QGIS (barre de menu)",
        "desc": "Positions des menus dans la barre de menu QGIS",
        "targets": [
            ("menu_settings", "le menu PARAMETRES / SETTINGS dans la barre de menu", "point"),
            ("menu_extensions", "le menu EXTENSIONS / PLUGINS dans la barre de menu", "point"),
            ("menu_view", "le menu VUE / VIEW dans la barre de menu", "point"),
        ],
    },
    "menu_items": {
        "label": "Elements de menus deroulants",
        "desc": "Chaque element necessite d'ouvrir un menu AVANT la capture.",
        "timer": 5,
        "targets": [
            ("menu_extensions_manage", "l'entree GERER LES EXTENSIONS", "point",
             "Ouvrez le menu EXTENSIONS dans la barre de menu QGIS"),
            ("menu_settings_options", "l'entree OPTIONS...", "point",
             "Ouvrez le menu PARAMETRES / SETTINGS dans la barre de menu QGIS"),
            ("menu_view_panels", "le sous-menu PANNEAUX", "point",
             "Ouvrez le menu VUE / VIEW dans la barre de menu QGIS"),
            ("menu_view_panels_log", "l'entree MESSAGES DE LOG", "point",
             "Ouvrez VUE > PANNEAUX (sous-menu deja ouvert)"),
        ],
    },
    "toolbar": {
        "label": "Toolbar QGIS",
        "desc": "Icones dans la barre d'outils QGIS",
        "targets": [
            ("filtermate_toolbar_icon", "l'icone FilterMate dans la toolbar QGIS", "point"),
        ],
    },
    "plugin_manager": {
        "label": "Plugin Manager (dialogue)",
        "desc": "Le dialogue Plugin Manager doit etre ouvert.",
        "timer": 5,
        "prereq": "Ouvrez le Plugin Manager : Extensions > Gerer les extensions",
        "targets": [
            ("plugin_manager_search", "la BARRE DE RECHERCHE en haut du Plugin Manager", "point"),
            ("plugin_manager_all_tab", "l'onglet TOUTES / ALL dans le panneau gauche", "point"),
            ("plugin_manager_entry", "l'entree FilterMate dans la LISTE des plugins", "point"),
            ("plugin_manager_install_btn", "le bouton INSTALLER en bas a droite", "point"),
        ],
    },
    "settings_dialog": {
        "label": "Settings > Options (dialogue)",
        "desc": "Le dialogue Options doit etre ouvert.",
        "timer": 5,
        "prereq": "Ouvrez le dialogue : Parametres > Options",
        "targets": [
            ("settings_options_general_tab", "l'onglet GENERAL dans le panneau gauche", "point"),
            ("settings_options_theme_dropdown", "le menu deroulant THEME UI (section Interface utilisateur)", "point"),
        ],
    },
    "about_config": {
        "label": "About FilterMate > Config (dialogue)",
        "desc": "Le dialogue About de FilterMate doit etre ouvert sur l'onglet Config.",
        "timer": 5,
        "prereq": "Ouvrez le dialogue About FilterMate, puis cliquez sur l'onglet Config",
        "targets": [
            ("about_config_tab", "l'onglet CONFIG dans le dialogue About FilterMate", "point"),
            ("about_config_language_field", "le champ LANGUAGE dans le TreeView config", "point"),
            ("about_config_feedback_level_field", "le champ FEEDBACK_LEVEL dans le TreeView config", "point"),
        ],
    },
    "log_panel": {
        "label": "Panneau Log Messages",
        "desc": "Le panneau Messages de log doit etre visible.",
        "timer": 5,
        "prereq": "Ouvrez le panneau : Vue > Panneaux > Messages de log",
        "targets": [
            ("log_panel_filtermate_tab", "l'onglet FilterMate dans le panneau Log Messages", "point"),
        ],
    },
    "layer_panel": {
        "label": "Panneau Couches (Layers)",
        "desc": "Checkboxes de visibilite des couches dans le panneau Layers",
        "targets": [
            ("layer_panel_visibility_departements", "la checkbox de visibilite de la couche DEPARTEMENTS", "point"),
            ("layer_panel_visibility_communes", "la checkbox de visibilite de la couche COMMUNES", "point"),
        ],
    },
}

# Flat list for backwards compatibility
CALIBRATION_TARGETS = []
for group in GROUPS.values():
    CALIBRATION_TARGETS.extend(group["targets"])


# ── Config I/O ────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict, config_path: Path) -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── Mouse helpers ─────────────────────────────────────────────────────────

def _get_pyautogui():
    """Import pyautogui with error handling."""
    try:
        import pyautogui
        return pyautogui
    except ImportError:
        return None


def get_mouse_position() -> tuple[int, int] | None:
    """Return current mouse position or None if pyautogui unavailable."""
    pag = _get_pyautogui()
    if pag:
        return pag.position()
    return None


# ── Visual feedback helpers ──────────────────────────────────────────────

def _show_position_circle(pag, cx: int, cy: int, radius: int = 25,
                          loops: int = 2, duration: float = 0.8) -> None:
    """Draw a circle around a point to highlight it visually."""
    import math
    steps = 30 * loops
    step_delay = duration / steps
    for i in range(steps + 1):
        angle = 2 * math.pi * i / (steps // loops)
        nx = int(cx + radius * math.cos(angle))
        ny = int(cy + radius * math.sin(angle))
        pag.moveTo(nx, ny, duration=step_delay, _pause=False)
    # Return to center
    pag.moveTo(cx, cy, duration=0.1, _pause=False)


def _show_position_rect(pag, x: int, y: int, w: int, h: int,
                        duration: float = 0.8) -> None:
    """Trace the outline of a rectangle to highlight it visually."""
    step_dur = duration / 4
    pag.moveTo(x, y, duration=0.1, _pause=False)
    pag.moveTo(x + w, y, duration=step_dur, _pause=False)
    pag.moveTo(x + w, y + h, duration=step_dur, _pause=False)
    pag.moveTo(x, y + h, duration=step_dur, _pause=False)
    pag.moveTo(x, y, duration=step_dur, _pause=False)
    # Move to center
    pag.moveTo(x + w // 2, y + h // 2, duration=0.1, _pause=False)


def _show_position_cross(pag, cx: int, cy: int, size: int = 20,
                         duration: float = 0.4) -> None:
    """Draw a + cross at a point to highlight it visually."""
    step_dur = duration / 4
    pag.moveTo(cx - size, cy, duration=0.05, _pause=False)
    pag.moveTo(cx + size, cy, duration=step_dur, _pause=False)
    pag.moveTo(cx, cy, duration=0.05, _pause=False)
    pag.moveTo(cx, cy - size, duration=0.05, _pause=False)
    pag.moveTo(cx, cy + size, duration=step_dur, _pause=False)
    pag.moveTo(cx, cy, duration=0.05, _pause=False)


def _countdown(seconds: int, message: str = "") -> None:
    """Print a visible countdown (e.g. '3... 2... 1...')."""
    if message:
        sys.stdout.write(f"       >> {message} ")
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"{i}... ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("GO!\n")
    sys.stdout.flush()


def show_position(val: dict | None) -> None:
    """Move the mouse to a calibrated position to show it visually.

    - For point regions: draw a cross then circle.
    - For rect regions: trace the rectangle outline then cross at center.
    - Catches PyAutoGUI FailSafeException gracefully (mouse in corner).
    """
    if val is None:
        return
    pag = _get_pyautogui()
    if pag is None:
        return

    try:
        if "width" in val and val.get("width", 0) > 0:
            _show_position_rect(pag, val["x"], val["y"],
                                val["width"], val["height"], duration=0.6)
            cx = val["x"] + val["width"] // 2
            cy = val["y"] + val["height"] // 2
            _show_position_cross(pag, cx, cy, size=15, duration=0.3)
        else:
            cx, cy = val["x"], val["y"]
            pag.moveTo(cx, cy, duration=0.3, _pause=False)
            _show_position_cross(pag, cx, cy, size=20, duration=0.3)
            _show_position_circle(pag, cx, cy, radius=25, loops=1, duration=0.5)
    except Exception:
        # FailSafeException (mouse in corner) or other pyautogui errors
        print(f"       ! Visualisation impossible (souris dans un coin ? deplacez-la)")


def cmd_show_all(config_path: Path) -> None:
    """Preview ALL calibrated positions visually, one by one.

    Moves the mouse to each position with visual feedback.
    Press Enter to advance, 'q' to quit.
    """
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})
    pag = _get_pyautogui()

    if not pag:
        print("  [ERREUR] pyautogui requis pour la visualisation.")
        return

    print()
    print("=" * 65)
    print("  VISUALISATION DES POSITIONS")
    print("  ENTREE = suivant | q = quitter")
    print("=" * 65)

    for group_id, group in GROUPS.items():
        group_keys = []
        for target in group["targets"]:
            if target[0] not in group_keys:
                group_keys.append(target[0])

        group_timer = group.get("timer", 0)
        group_prereq = group.get("prereq", "")

        print(f"\n  ━━━ {group['label']} ━━━")

        # Prereq + countdown once per group if timer is set
        if group_timer > 0:
            prereq_text = group_prereq or group.get("desc", "")
            if prereq_text:
                print(f"       >> {prereq_text}")
                print(f"       Appuyez sur ENTREE quand c'est pret (s = passer)")
                ready = input("       pret ? ").strip().lower()
                if ready == "q":
                    print("  Visualisation terminee.")
                    return
                if ready == "s":
                    continue
            _countdown(group_timer, "Le curseur se deplace dans")

        for key in group_keys:
            val = regions.get(key)
            if val is None or not _is_calibrated(val):
                continue

            status = _status_icon(val)
            print(f"  [{status}] {key:38s} {_format_value(val)}  ", end="", flush=True)

            # Show it visually
            show_position(val)
            time.sleep(0.3)

            raw = input("")
            if raw.strip().lower() == "q":
                print("  Visualisation terminee.")
                return

    print("\n  Toutes les positions ont ete montrees !")
    print()


def record_position(prompt: str, current_value: dict | None = None) -> tuple[int, int]:
    """
    Wait for user to position mouse, then record position.
    Shows current value if available. Allows manual entry.
    """
    print(f"\n  >> {prompt}")
    if current_value:
        if "width" in current_value:
            print(f"     Actuel : x={current_value['x']}, y={current_value['y']}, "
                  f"w={current_value['width']}, h={current_value['height']}")
        else:
            print(f"     Actuel : x={current_value['x']}, y={current_value['y']}")

    print("     Placez la souris sur l'element, puis appuyez sur ENTREE")
    print("     Ou tapez les coordonnees manuellement : x y")
    print("     Ou tapez 's' pour garder la valeur actuelle")

    while True:
        raw = input("     > ").strip()

        if raw.lower() == "s" and current_value:
            x = current_value["x"]
            y = current_value["y"]
            print(f"     = Conserve : ({x}, {y})")
            return x, y

        if raw == "":
            # Use mouse position
            pos = get_mouse_position()
            if pos:
                x, y = pos
                print(f"     + Enregistre : ({x}, {y})")
                return x, y
            else:
                print("     ! pyautogui non disponible. Tapez les coordonnees : x y")
                continue

        # Manual entry
        parts = raw.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                x, y = int(parts[0]), int(parts[1])
                print(f"     + Enregistre : ({x}, {y})")
                return x, y
            except ValueError:
                pass
        print("     ! Format invalide. Tapez 'x y' ou appuyez sur ENTREE.")


# ── Display helpers ───────────────────────────────────────────────────────

def _format_value(val: dict) -> str:
    """Format a region dict for display."""
    if "width" in val:
        return f"({val['x']:>5}, {val['y']:>5})  {val['width']:>4}x{val['height']:<4}"
    return f"({val['x']:>5}, {val['y']:>5})"


def _is_calibrated(val: dict) -> bool:
    """Check if a position looks calibrated (not all zeros)."""
    if val.get("x", 0) == 0 and val.get("y", 0) == 0:
        if val.get("width", 1) == 0 and val.get("height", 1) == 0:
            return False
        if "width" not in val:
            return False
    return True


def _status_icon(val: dict | None) -> str:
    """Return a status indicator for a position."""
    if val is None:
        return "  "
    if _is_calibrated(val):
        return "ok"
    return "!!"


# ── Core commands ─────────────────────────────────────────────────────────

def cmd_list(config_path: Path) -> None:
    """Print current calibration data, grouped and with status."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})

    print()
    print("=" * 72)
    print("  FilterMate Video Automation — Calibration actuelle")
    print("=" * 72)

    if not regions:
        print("\n  (aucune calibration — lancez calibrate.py)")
        return

    # Show grouped
    known_keys = set()
    for group_id, group in GROUPS.items():
        print(f"\n  [{group_id}] {group['label']}")
        print(f"  {'─' * 60}")
        group_keys = set()
        for target in group["targets"]:
            group_keys.add(target[0])
        for key in group_keys:
            known_keys.add(key)
            val = regions.get(key)
            status = _status_icon(val)
            if val:
                print(f"  {status}  {key:38s} {_format_value(val)}")
            else:
                print(f"  --  {key:38s} (non defini)")

    # Show any extra keys not in groups
    extra = set(regions.keys()) - known_keys
    if extra:
        print(f"\n  [extra] Autres elements")
        print(f"  {'─' * 60}")
        for key in sorted(extra):
            val = regions[key]
            status = _status_icon(val)
            print(f"  {status}  {key:38s} {_format_value(val)}")

    # Summary
    total = len(regions)
    calibrated = sum(1 for v in regions.values() if _is_calibrated(v))
    missing = total - calibrated
    print(f"\n  {'─' * 60}")
    print(f"  Total: {total} elements | Calibres: {calibrated} | Manquants: {missing}")
    if missing > 0:
        print(f"  !! {missing} element(s) non calibre(s) (marques '!!')")
    print()


def cmd_live(config_path: Path) -> None:
    """Live mouse position monitor with nearest element display."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})
    pag = _get_pyautogui()

    if not pag:
        print("  [ERREUR] pyautogui requis pour le mode live.")
        print("           pip install pyautogui")
        return

    print()
    print("=" * 60)
    print("  Mode LIVE — Position souris en temps reel")
    print("  Appuyez sur Ctrl+C pour quitter")
    print("=" * 60)
    print()

    try:
        while True:
            x, y = pag.position()

            # Find nearest calibrated element
            nearest_key = ""
            nearest_dist = float("inf")
            for key, val in regions.items():
                if not _is_calibrated(val):
                    continue
                if "width" in val:
                    cx = val["x"] + val["width"] // 2
                    cy = val["y"] + val["height"] // 2
                else:
                    cx = val["x"]
                    cy = val["y"]
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_key = key

            nearest_info = ""
            if nearest_key and nearest_dist < 200:
                nearest_info = f"  ~ {nearest_key} ({nearest_dist:.0f}px)"

            sys.stdout.write(f"\r  Souris: ({x:>5}, {y:>5}){nearest_info:50s}")
            sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n  Mode live termine.\n")


def cmd_validate(config_path: Path) -> None:
    """Validate coherence of calibrated positions."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})

    print()
    print("=" * 60)
    print("  Validation de coherence des positions")
    print("=" * 60)

    errors = []
    warnings = []

    dock = regions.get("filtermate_dock", {})
    if not dock or not _is_calibrated(dock):
        errors.append("filtermate_dock non calibre — base de reference manquante")
    else:
        dx, dy = dock["x"], dock["y"]
        dw, dh = dock.get("width", 0), dock.get("height", 0)
        dr = dx + dw
        db = dy + dh

        # Check that dock-internal elements are within dock bounds
        dock_elements = [
            "tab_filtering", "tab_exploring", "tab_exporting",
            "source_layer_combo", "filter_button", "undo_button",
            "redo_button", "unfilter_button", "export_button", "about_button",
            "favorites_button", "badge_backend", "badge_favorites",
            "exploring_layer_combo", "exploring_feature_selector",
            "exploring_display_field_combo",
            "exploring_feature_prev_btn", "exploring_feature_next_btn",
            "sidebar_identify", "sidebar_zoom", "sidebar_select",
            "sidebar_track", "sidebar_link", "sidebar_reset",
            "btn_toggle_layers_to_filter", "btn_toggle_geometric_predicates",
            "btn_toggle_buffer", "target_layer_combo", "predicate_combo",
            "buffer_enable_checkbox", "buffer_value_spinbox",
        ]
        for key in dock_elements:
            val = regions.get(key)
            if val is None or not _is_calibrated(val):
                continue
            vx, vy = val["x"], val["y"]
            if vx < dx - 10 or vx > dr + 10 or vy < dy - 10 or vy > db + 10:
                errors.append(
                    f"{key} ({vx}, {vy}) est EN DEHORS du dock "
                    f"({dx},{dy})-({dr},{db})"
                )

        # Check vertical ordering within dock
        order_checks = [
            ("header_bar", "exploring_zone", "header au-dessus de exploring zone"),
            ("exploring_zone", "toolbox_zone", "exploring zone au-dessus de toolbox"),
            ("toolbox_zone", "action_bar_zone", "toolbox au-dessus de action bar"),
            ("tab_exploring", "tab_filtering", "onglet exploring avant filtering (y)"),
            ("tab_filtering", "tab_exporting", "onglet filtering avant exporting (y)"),
        ]
        for key_a, key_b, desc in order_checks:
            va = regions.get(key_a)
            vb = regions.get(key_b)
            if va and vb and _is_calibrated(va) and _is_calibrated(vb):
                ya = va["y"]
                yb = vb["y"]
                if ya >= yb:
                    errors.append(f"Ordre vertical: {desc} — {key_a} y={ya} >= {key_b} y={yb}")

        # Check sidebar buttons are vertically ordered
        sidebar_keys = [
            "sidebar_identify", "sidebar_zoom", "sidebar_select",
            "sidebar_track", "sidebar_link", "sidebar_reset",
        ]
        prev_y = 0
        for key in sidebar_keys:
            val = regions.get(key)
            if val and _is_calibrated(val):
                if val["y"] <= prev_y:
                    warnings.append(
                        f"Sidebar: {key} y={val['y']} devrait etre > {prev_y}"
                    )
                prev_y = val["y"]

        # Check sidebar buttons have similar x
        sidebar_xs = []
        for key in sidebar_keys:
            val = regions.get(key)
            if val and _is_calibrated(val):
                sidebar_xs.append((key, val["x"]))
        if len(sidebar_xs) >= 2:
            xs = [x for _, x in sidebar_xs]
            if max(xs) - min(xs) > 30:
                warnings.append(
                    f"Sidebar: les x varient trop ({min(xs)}-{max(xs)}), "
                    f"les boutons devraient etre alignes verticalement"
                )

        # Check action bar buttons have similar y
        action_keys = [
            "filter_button", "undo_button", "redo_button",
            "unfilter_button", "export_button", "about_button",
        ]
        action_ys = []
        for key in action_keys:
            val = regions.get(key)
            if val and _is_calibrated(val):
                action_ys.append((key, val["y"]))
        if len(action_ys) >= 2:
            ys = [y for _, y in action_ys]
            if max(ys) - min(ys) > 30:
                warnings.append(
                    f"Action bar: les y varient trop ({min(ys)}-{max(ys)}), "
                    f"les boutons devraient etre sur une meme ligne"
                )

        # Check action bar buttons are ordered left-to-right
        action_xvals = []
        for key in action_keys:
            val = regions.get(key)
            if val and _is_calibrated(val):
                action_xvals.append((key, val["x"]))
        if len(action_xvals) >= 2:
            for i in range(len(action_xvals) - 1):
                if action_xvals[i][1] >= action_xvals[i + 1][1]:
                    warnings.append(
                        f"Action bar: {action_xvals[i][0]} x={action_xvals[i][1]} "
                        f">= {action_xvals[i + 1][0]} x={action_xvals[i + 1][1]}"
                    )

    # Check menu bar items have consistent y (should all be on the same bar)
    menu_bar_keys = ["menu_settings", "menu_extensions", "menu_view"]
    menu_ys = []
    for key in menu_bar_keys:
        val = regions.get(key)
        if val and _is_calibrated(val):
            menu_ys.append((key, val["y"]))
    if len(menu_ys) >= 2:
        ys = [y for _, y in menu_ys]
        if max(ys) - min(ys) > 10:
            warnings.append(
                f"Menus: les y de la barre de menu varient trop "
                f"({min(ys)}-{max(ys)}), ils devraient etre alignes"
            )

    # Check menu bar items are above toolbar
    toolbar_val = regions.get("toolbar")
    if toolbar_val and _is_calibrated(toolbar_val):
        for key in menu_bar_keys:
            val = regions.get(key)
            if val and _is_calibrated(val):
                if val["y"] >= toolbar_val["y"]:
                    errors.append(
                        f"{key} y={val['y']} est EN DESSOUS de toolbar y={toolbar_val['y']}"
                    )

    # Check dropdown items are below their parent menu
    dropdown_checks = [
        ("menu_extensions", "menu_extensions_manage", "Extensions > Gerer"),
        ("menu_settings", "menu_settings_options", "Parametres > Options"),
        ("menu_view", "menu_view_panels", "Vue > Panneaux"),
    ]
    for parent_key, child_key, desc in dropdown_checks:
        parent = regions.get(parent_key)
        child = regions.get(child_key)
        if parent and child and _is_calibrated(parent) and _is_calibrated(child):
            if child["y"] <= parent["y"]:
                errors.append(
                    f"{desc}: {child_key} y={child['y']} devrait etre "
                    f"en dessous de {parent_key} y={parent['y']}"
                )

    # Check toolbar icon is within toolbar area
    toolbar_icon = regions.get("filtermate_toolbar_icon")
    if toolbar_icon and toolbar_val and _is_calibrated(toolbar_icon) and _is_calibrated(toolbar_val):
        ty = toolbar_val["y"]
        tb = ty + toolbar_val.get("height", 168)
        if toolbar_icon["y"] < ty - 5 or toolbar_icon["y"] > tb + 5:
            warnings.append(
                f"filtermate_toolbar_icon y={toolbar_icon['y']} "
                f"est en dehors de toolbar ({ty}-{tb})"
            )

    # Check for (0,0) positions
    for key, val in regions.items():
        if val.get("x", 0) == 0 and val.get("y", 0) == 0:
            if "width" in val:
                if val.get("width", 0) == 0:
                    warnings.append(f"{key} : position (0, 0) avec taille 0 — probablement non calibre")
            else:
                warnings.append(f"{key} : position (0, 0) — probablement non calibre")

    # Report
    if errors:
        print(f"\n  ERREURS ({len(errors)}):")
        for e in errors:
            print(f"    !! {e}")

    if warnings:
        print(f"\n  AVERTISSEMENTS ({len(warnings)}):")
        for w in warnings:
            print(f"    ?? {w}")

    if not errors and not warnings:
        print("\n  Toutes les positions sont coherentes !")

    print()


def cmd_edit(config_path: Path, region_key: str) -> None:
    """Edit a single region's coordinates manually."""
    config = load_config(config_path)
    regions = config.setdefault("qgis", {}).setdefault("regions", {})

    val = regions.get(region_key)
    print(f"\n  Edition de : {region_key}")
    if val:
        print(f"  Valeur actuelle : {_format_value(val)}")
    else:
        print(f"  (non defini)")

    if val and "width" in val:
        print("  Entrez : x y width height")
        raw = input("  > ").strip().replace(",", " ").split()
        if len(raw) >= 4:
            try:
                regions[region_key] = {
                    "x": int(raw[0]), "y": int(raw[1]),
                    "width": int(raw[2]), "height": int(raw[3]),
                }
                save_config(config, config_path)
                print(f"  + Sauvegarde : {_format_value(regions[region_key])}")
                return
            except ValueError:
                pass
        print("  ! Format invalide.")
    else:
        print("  Entrez : x y")
        raw = input("  > ").strip().replace(",", " ").split()
        if len(raw) >= 2:
            try:
                regions[region_key] = {"x": int(raw[0]), "y": int(raw[1])}
                save_config(config, config_path)
                print(f"  + Sauvegarde : {_format_value(regions[region_key])}")
                return
            except ValueError:
                pass
        print("  ! Format invalide.")


def cmd_calibrate_group(config_path: Path, group_id: str) -> None:
    """Calibrate all targets in a specific group."""
    if group_id not in GROUPS:
        print(f"  [ERREUR] Groupe inconnu : '{group_id}'")
        print(f"  Groupes disponibles : {', '.join(GROUPS.keys())}")
        return

    group = GROUPS[group_id]
    config = load_config(config_path)
    regions = config.setdefault("qgis", {}).setdefault("regions", {})

    print(f"\n  Calibration du groupe : {group['label']}")
    print(f"  {group['desc']}")
    print(f"  {len(group['targets'])} element(s) a calibrer")
    print()

    _calibrate_targets(
        config, regions, group["targets"],
        config_path=config_path,
        group_timer=group.get("timer", 0),
        group_prereq=group.get("prereq", ""),
    )

    print(f"\n  Groupe '{group_id}' termine.")


def cmd_calibrate_all(config_path: Path) -> None:
    """Full interactive calibration session."""
    config = load_config(config_path)
    regions = config.setdefault("qgis", {}).setdefault("regions", {})
    undo_stack: list[dict] = []

    print()
    print("=" * 65)
    print("  FilterMate Video Automation — Calibration Interactive")
    print("=" * 65)
    print()
    print("  Avant de commencer :")
    print("  1. QGIS ouvert avec FilterMate charge et visible")
    print("  2. Onglet FILTERING selectionne dans la Toolbox")
    print("  3. Ecran en position normale d'enregistrement")
    print()
    print("  Pour chaque element :")
    print("    ENTREE      = enregistrer la position de la souris")
    print("    x y          = entrer les coordonnees manuellement")
    print("    s            = garder la valeur actuelle (skip)")
    print()

    total_groups = len(GROUPS)
    for idx, (group_id, group) in enumerate(GROUPS.items(), 1):
        print()
        print(f"  ━━━ [{idx}/{total_groups}] {group['label']} ━━━")
        if group["desc"]:
            print(f"      {group['desc']}")

        # Save state for undo
        undo_stack.append(copy.deepcopy(regions))

        _calibrate_targets(
            config, regions, group["targets"],
            config_path=config_path,
            group_timer=group.get("timer", 0),
            group_prereq=group.get("prereq", ""),
        )

    print()
    print("=" * 65)
    print(f"  Calibration terminee ! Sauvegarde dans : {config_path}")
    print("=" * 65)
    print()


def _calibrate_targets(config: dict, regions: dict, targets: list,
                       config_path: Path | None = None,
                       group_timer: int = 0,
                       group_prereq: str = "") -> None:
    """Calibrate a list of targets into regions dict.

    Auto-saves to config_path after each real change.

    Parameters
    ----------
    group_timer : int
        Countdown seconds before each target (for menus/dropdowns that
        need to be opened first).
    group_prereq : str
        Instruction displayed once at the start for the whole group
        (e.g. "Ouvrez le Plugin Manager").
    """
    corners: dict[str, dict] = {}

    # Show group prereq once if present
    if group_prereq:
        print(f"\n  ┌─ PREREQUIS ──────────────────────────────────")
        print(f"  │  {group_prereq}")
        print(f"  └──────────────────────────────────────────────")

    def _auto_save(region_key: str, new_val: dict) -> None:
        """Save only if value actually changed."""
        old_val = regions.get(region_key)
        regions[region_key] = new_val
        if config_path and new_val != old_val:
            save_config(config, config_path)
            print(f"     (sauvegarde automatique)")

    for target in targets:
        region_key, prompt, kind = target[0], target[1], target[2]
        # Per-target prereq (4th element in tuple, if present)
        target_prereq = target[3] if len(target) > 3 else ""
        current = regions.get(region_key)

        # For targets that need a menu/dialog open first:
        # show prereq, wait for user, countdown, then capture mouse directly
        auto_capture = False
        if target_prereq:
            print(f"\n     ┌─ PREREQUIS ─────────────────────────────")
            print(f"     │  {target_prereq}")
            print(f"     │  Puis placez la souris sur : {prompt}")
            print(f"     │  Appuyez sur ENTREE quand c'est pret (s = passer)")
            print(f"     └─────────────────────────────────────────")
            ready = input("     pret ? ").strip().lower()
            if ready == "s":
                print(f"     (passe)")
                continue
            if group_timer > 0:
                _countdown(group_timer, "Capture dans")
                auto_capture = True
        elif group_timer > 0:
            print(f"\n  >> {prompt}")
            print(f"     Placez la souris sur l'element.")
            print(f"     Appuyez sur ENTREE quand c'est pret (s = passer)")
            ready = input("     pret ? ").strip().lower()
            if ready == "s":
                print(f"     (passe)")
                continue
            _countdown(group_timer, "Capture dans")
            auto_capture = True

        if auto_capture:
            # Capture mouse position directly after countdown
            pos = get_mouse_position()
            if pos:
                x, y = pos
                print(f"     + Enregistre : ({x}, {y})")
            else:
                print(f"     ! pyautogui non disponible, saisie manuelle requise")
                x, y = record_position(prompt, current)
        elif kind in ("tl", "br"):
            x, y = record_position(prompt, current)
        else:
            x, y = record_position(prompt, current)

        if kind in ("tl", "br"):
            corners.setdefault(region_key, {})[kind] = (x, y)
            if "tl" in corners.get(region_key, {}) and "br" in corners.get(region_key, {}):
                tl = corners[region_key]["tl"]
                br = corners[region_key]["br"]
                new_val = {
                    "x": tl[0],
                    "y": tl[1],
                    "width": max(1, br[0] - tl[0]),
                    "height": max(1, br[1] - tl[1]),
                }
                print(f"     -> Region '{region_key}' : {_format_value(new_val)}")
                _auto_save(region_key, new_val)

        elif kind == "point":
            new_val = {"x": x, "y": y}
            _auto_save(region_key, new_val)


def _review_single(key: str, val: dict | None, regions: dict,
                   timer: int = 0, prereq: str = "") -> tuple[str, bool]:
    """Review a single region. Returns (action, modified).

    action: 'continue' | 'quit'
    modified: True if the value was changed.
    timer: seconds to count down before moving cursor (for dropdowns/dialogs).
    prereq: instruction to display and wait for before starting countdown.
    """
    status = _status_icon(val)
    val_str = _format_value(val) if val else "(non defini)"

    print(f"\n  [{status}] {key}")
    print(f"       Actuel : {val_str}")

    # Prerequisite + countdown before moving cursor
    if prereq and timer > 0 and val and _is_calibrated(val):
        print(f"       ┌─ PREREQUIS ──────────────────────────────────")
        print(f"       │  {prereq}")
        print(f"       │  Appuyez sur ENTREE quand c'est pret (s = passer)")
        print(f"       └──────────────────────────────────────────────")
        ready = input("       pret ? ").strip().lower()
        if ready == "q":
            return "quit", False
        if ready != "s":
            _countdown(timer, "Le curseur se deplace dans")
            show_position(val)
        else:
            print(f"       (visualisation sautee)")
    elif timer > 0 and val and _is_calibrated(val):
        # Timer without specific prereq text
        _countdown(timer, "Le curseur se deplace dans")
        show_position(val)
    elif val and _is_calibrated(val):
        # No timer needed — show immediately
        show_position(val)

    raw = input("       > ").strip()

    if raw.lower() == "q":
        return "quit", False

    if raw.lower() == "d":
        if key in regions:
            del regions[key]
            print(f"       - Supprime")
        return "continue", True

    if raw == "":
        return "continue", False

    if raw.lower() == "m":
        pos = get_mouse_position()
        if pos:
            x, y = pos
            if val and "width" in val:
                regions[key] = {
                    "x": x, "y": y,
                    "width": val["width"], "height": val["height"],
                }
            else:
                regions[key] = {"x": x, "y": y}
            print(f"       + Modifie : {_format_value(regions[key])}")
            # Show the new position
            show_position(regions[key])
            return "continue", True
        else:
            print("       ! pyautogui non disponible")
            return "continue", False

    # Manual coordinates
    parts = raw.replace(",", " ").split()
    if len(parts) >= 4 and val and "width" in val:
        try:
            regions[key] = {
                "x": int(parts[0]), "y": int(parts[1]),
                "width": int(parts[2]), "height": int(parts[3]),
            }
            print(f"       + Modifie : {_format_value(regions[key])}")
            show_position(regions[key])
            return "continue", True
        except ValueError:
            pass
    if len(parts) >= 2:
        try:
            x, y = int(parts[0]), int(parts[1])
            if val and "width" in val:
                regions[key] = {
                    "x": x, "y": y,
                    "width": val["width"], "height": val["height"],
                }
            else:
                regions[key] = {"x": x, "y": y}
            print(f"       + Modifie : {_format_value(regions[key])}")
            show_position(regions[key])
            return "continue", True
        except ValueError:
            pass

    print("       ! Format invalide, valeur conservee")
    return "continue", False


def cmd_review(config_path: Path) -> None:
    """Review ALL positions one by one with visual feedback and correction.

    The mouse cursor moves to each registered position (circle / rectangle
    outline) so you can visually verify if it's correct, then:
      Enter  = keep current value (OK)
      m      = capture current mouse position
      x y    = enter new coordinates manually
      d      = delete this element
      q      = quit review (saves changes)
    """
    config = load_config(config_path)
    regions = config.setdefault("qgis", {}).setdefault("regions", {})

    print()
    print("=" * 72)
    print("  REVUE DE TOUTES LES POSITIONS (avec visualisation)")
    print("=" * 72)
    print()
    print("  Le curseur se deplace vers chaque position enregistree.")
    print("  Verifiez visuellement si la position est correcte.")
    print()
    print("  Pour chaque element :")
    print("    ENTREE       = garder la valeur actuelle (OK)")
    print("    m + ENTREE   = capturer la position actuelle de la souris")
    print("    x y          = entrer de nouvelles coordonnees")
    print("    d            = supprimer cet element")
    print("    q            = quitter la revue (sauvegarde les changements)")
    print()

    modified = 0
    total = 0

    for group_id, group in GROUPS.items():
        # Build unique keys + per-element prereqs
        group_keys = []
        element_prereqs: dict[str, str] = {}
        for target in group["targets"]:
            region_key = target[0]
            if region_key not in group_keys:
                group_keys.append(region_key)
            # Target can be (key, prompt, kind) or (key, prompt, kind, prereq)
            if len(target) >= 4:
                element_prereqs[region_key] = target[3]

        print(f"\n  ━━━ {group['label']} ━━━")
        if group.get("desc"):
            print(f"      {group['desc']}")

        group_timer = group.get("timer", 0)
        group_prereq = group.get("prereq", "")

        # For groups with a group-level prereq (not per-element),
        # show the prereq once and wait before starting
        if group_prereq and group_timer > 0:
            print(f"\n       ┌─ PREREQUIS GROUPE ────────────────────────────")
            print(f"       │  {group_prereq}")
            print(f"       │  Appuyez sur ENTREE quand c'est pret (s = passer le groupe)")
            print(f"       └──────────────────────────────────────────────")
            ready = input("       pret ? ").strip().lower()
            if ready == "q":
                save_config(config, config_path)
                print(f"\n  Revue interrompue. {modified} modification(s) sauvegardee(s).")
                return
            if ready == "s":
                total += len(group_keys)
                print(f"       (groupe saute)")
                continue

        for key in group_keys:
            total += 1
            val = regions.get(key)
            # Per-element prereq (menu_items) or no prereq (group already handled)
            elem_prereq = element_prereqs.get(key, "")
            # If group has a group-level prereq, don't repeat per element
            effective_timer = group_timer if (elem_prereq or not group_prereq) else 0
            action, changed = _review_single(
                key, val, regions,
                timer=effective_timer, prereq=elem_prereq,
            )
            if changed:
                modified += 1
                save_config(config, config_path)
                print(f"       (sauvegarde automatique)")
            if action == "quit":
                save_config(config, config_path)
                print(f"\n  Revue interrompue. {modified} modification(s) sauvegardee(s).")
                return

    # Also review extra keys not in any group
    known_keys = set()
    for group in GROUPS.values():
        for target in group["targets"]:
            known_keys.add(target[0])

    extra_keys = sorted(set(regions.keys()) - known_keys)
    if extra_keys:
        print(f"\n  ━━━ Elements supplementaires (hors groupes) ━━━")
        for key in extra_keys:
            total += 1
            val = regions[key]
            action, changed = _review_single(key, val, regions)
            if changed:
                modified += 1
                save_config(config, config_path)
                print(f"       (sauvegarde automatique)")
            if action == "quit":
                break

    save_config(config, config_path)
    print()
    print("=" * 72)
    print(f"  Revue terminee : {total} elements, {modified} modification(s)")
    print(f"  Sauvegarde dans : {config_path}")
    print("=" * 72)
    print()


def cmd_reset(config_path: Path) -> None:
    """Zero out all region coordinates."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})

    print(f"\n  ATTENTION : Ceci va remettre TOUTES les {len(regions)} positions a zero !")
    confirm = input("  Confirmer ? (oui/non) > ").strip().lower()
    if confirm not in ("oui", "o", "yes", "y"):
        print("  Annule.")
        return

    for key in regions:
        if "width" in regions[key]:
            regions[key] = {"x": 0, "y": 0, "width": 0, "height": 0}
        else:
            regions[key] = {"x": 0, "y": 0}
    save_config(config, config_path)
    print(f"  Toutes les positions remises a zero dans {config_path}")


def cmd_interactive_menu(config_path: Path) -> None:
    """Main interactive menu loop."""
    print()
    print("=" * 65)
    print("  FilterMate Video Automation — Outil de Calibration")
    print("=" * 65)

    while True:
        config = load_config(config_path)
        regions = config.get("qgis", {}).get("regions", {})
        total = len(regions)
        calibrated = sum(1 for v in regions.values() if _is_calibrated(v))

        print()
        print(f"  Positions : {calibrated}/{total} calibrees")
        print()
        print("  Commandes :")
        print("    list         Afficher toutes les positions")
        print("    review       Passer en revue TOUTES les positions (corriger)")
        print("    show         Visualiser toutes les positions (curseur)")
        print("    all          Calibrer TOUT (session complete)")
        print("    group <id>   Calibrer un groupe specifique")
        print("    edit <key>   Modifier une position manuellement")
        print("    live         Mode live (position souris en temps reel)")
        print("    validate     Verifier la coherence des positions")
        print("    reset        Remettre tout a zero")
        print("    quit         Quitter")
        print()
        print(f"  Groupes : {', '.join(GROUPS.keys())}")
        print()

        raw = input("  > ").strip()
        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "q", "exit"):
            print("  Au revoir !")
            break
        elif cmd in ("list", "ls", "l"):
            cmd_list(config_path)
        elif cmd in ("review", "r"):
            cmd_review(config_path)
        elif cmd in ("show", "preview", "p"):
            cmd_show_all(config_path)
        elif cmd in ("all", "a"):
            cmd_calibrate_all(config_path)
        elif cmd in ("group", "g"):
            if arg:
                cmd_calibrate_group(config_path, arg)
            else:
                print("  Usage : group <id>")
                print(f"  Groupes : {', '.join(GROUPS.keys())}")
        elif cmd in ("edit", "e"):
            if arg:
                cmd_edit(config_path, arg)
            else:
                print("  Usage : edit <region_key>")
                print("  Exemple : edit sidebar_identify")
        elif cmd == "live":
            cmd_live(config_path)
        elif cmd in ("validate", "check", "v"):
            cmd_validate(config_path)
        elif cmd == "reset":
            cmd_reset(config_path)
        else:
            # Check if it's a group name directly
            if cmd in GROUPS:
                cmd_calibrate_group(config_path, cmd)
            else:
                print(f"  Commande inconnue : '{cmd}'")


# ── CLI entry point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Outil de calibration interactif pour FilterMate Video Automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python calibrate.py                 Menu interactif
  python calibrate.py --list          Afficher les positions
  python calibrate.py --group sidebar Calibrer les boutons sidebar
  python calibrate.py --edit sidebar_identify  Modifier une position
  python calibrate.py --live          Position souris en temps reel
  python calibrate.py --validate      Verifier la coherence
        """,
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Chemin vers config.yaml (defaut: ../config.yaml)",
    )
    parser.add_argument("--list", action="store_true", help="Afficher les positions actuelles")
    parser.add_argument("--reset", action="store_true", help="Remettre toutes les positions a zero")
    parser.add_argument("--group", type=str, metavar="ID", help="Calibrer un groupe specifique")
    parser.add_argument("--edit", type=str, metavar="KEY", help="Modifier une position manuellement")
    parser.add_argument("--live", action="store_true", help="Mode live (position souris en temps reel)")
    parser.add_argument("--validate", action="store_true", help="Verifier la coherence des positions")
    parser.add_argument("--all", action="store_true", help="Calibrer tout (session complete)")
    parser.add_argument("--review", action="store_true", help="Passer en revue toutes les positions (avec visualisation)")
    parser.add_argument("--show", action="store_true", help="Visualiser toutes les positions (curseur sur ecran)")

    args = parser.parse_args()

    if not args.config.exists():
        print(f"Erreur: fichier config introuvable: {args.config}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        cmd_list(args.config)
    elif args.reset:
        cmd_reset(args.config)
    elif args.group:
        cmd_calibrate_group(args.config, args.group)
    elif args.edit:
        cmd_edit(args.config, args.edit)
    elif args.live:
        cmd_live(args.config)
    elif args.validate:
        cmd_validate(args.config)
    elif args.all:
        cmd_calibrate_all(args.config)
    elif args.review:
        cmd_review(args.config)
    elif args.show:
        cmd_show_all(args.config)
    else:
        cmd_interactive_menu(args.config)


if __name__ == "__main__":
    main()
