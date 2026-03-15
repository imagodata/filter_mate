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
        "label": "Menus QGIS",
        "desc": "Positions des menus dans la barre de menu QGIS",
        "targets": [
            ("menu_settings", "le menu SKETCHES / PREFERENCES QGIS", "point"),
            ("menu_extensions", "le menu EXTENSIONS / PLUGINS", "point"),
            ("menu_view", "le menu VUE / VIEW", "point"),
            ("menu_view_panels", "le sous-menu PANNEAUX (apres clic sur Vue)", "point"),
            ("menu_view_panels_log", "l'entree MESSAGES DE LOG (apres Vue > Panneaux)", "point"),
        ],
    },
    "dialogs": {
        "label": "Toolbar + Dialogues",
        "desc": "Icones toolbar et elements de dialogues QGIS",
        "targets": [
            ("filtermate_toolbar_icon", "l'icone FilterMate dans la toolbar QGIS", "point"),
            ("log_panel_filtermate_tab", "l'onglet FilterMate dans le panneau Log Messages", "point"),
            ("about_config_tab", "l'onglet Config dans le dialogue About FilterMate", "point"),
            ("plugin_manager_entry", "l'entree FilterMate dans le Plugin Manager", "point"),
            ("plugin_manager_install_btn", "le bouton Installer dans le Plugin Manager", "point"),
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
        for region_key, _prompt, _kind in group["targets"]:
            group_keys.add(region_key)
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

    _calibrate_targets(config, regions, group["targets"])

    save_config(config, config_path)
    print(f"\n  Groupe '{group_id}' sauvegarde dans {config_path}")


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

        _calibrate_targets(config, regions, group["targets"])

        # Auto-save after each group
        save_config(config, config_path)
        print(f"      (sauvegarde automatique)")

    print()
    print("=" * 65)
    print(f"  Calibration terminee ! Sauvegarde dans : {config_path}")
    print("=" * 65)
    print()


def _calibrate_targets(config: dict, regions: dict, targets: list) -> None:
    """Calibrate a list of targets into regions dict."""
    corners: dict[str, dict] = {}

    for region_key, prompt, kind in targets:
        current = regions.get(region_key)

        if kind in ("tl", "br"):
            x, y = record_position(prompt, current)
            corners.setdefault(region_key, {})[kind] = (x, y)
            if "tl" in corners.get(region_key, {}) and "br" in corners.get(region_key, {}):
                tl = corners[region_key]["tl"]
                br = corners[region_key]["br"]
                regions[region_key] = {
                    "x": tl[0],
                    "y": tl[1],
                    "width": max(1, br[0] - tl[0]),
                    "height": max(1, br[1] - tl[1]),
                }
                print(f"     -> Region '{region_key}' : {_format_value(regions[region_key])}")

        elif kind == "point":
            x, y = record_position(prompt, current)
            regions[region_key] = {"x": x, "y": y}


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
    else:
        cmd_interactive_menu(args.config)


if __name__ == "__main__":
    main()
