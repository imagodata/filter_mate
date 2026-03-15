"""
Interactive Calibration Tool
=============================
Records QGIS and FilterMate UI element positions by asking the user to click
on specific areas. Saves results to config.yaml.

Usage:
    python scripts/calibrate.py [--config ../config.yaml]
    python scripts/calibrate.py --list   # Show current calibration
    python scripts/calibrate.py --reset  # Reset all regions to zero
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Windows: reconfigure stdout/stderr to UTF-8 to avoid UnicodeEncodeError
# when printing box-drawing or special characters to cmd.exe consoles.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Add parent directory to path so we can import config helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"

# ── Calibration targets ────────────────────────────────────────────────────

# Each entry: (region_key, prompt_text, type)
# type: "region" = ask for two corners (TL + BR)
#       "point"  = ask for single click
CALIBRATION_TARGETS = [
    # Regions (bounding boxes)
    ("filtermate_dock",    "the OUTER BOUNDARY — top-left corner of the FilterMate dock panel", "tl"),
    ("filtermate_dock",    "the OUTER BOUNDARY — bottom-right corner of the FilterMate dock panel", "br"),
    ("main_canvas",        "top-left corner of the main QGIS map canvas", "tl"),
    ("main_canvas",        "bottom-right corner of the main QGIS map canvas", "br"),
    ("toolbar",            "top-left corner of the main QGIS toolbar area", "tl"),
    ("toolbar",            "bottom-right corner of the main QGIS toolbar area", "br"),

    # FilterMate tabs (single points)
    ("tab_filtering",           "the FILTERING tab label", "point"),
    ("tab_exploring",           "the EXPLORING / EXPLORATION tab label", "point"),
    ("tab_exporting",           "the EXPORTING tab label", "point"),

    # FilterMate UI elements (single points)
    ("source_layer_combo",      "the SOURCE LAYER dropdown / combobox", "point"),

    # ── Checkable sidebar pushbuttons (FILTERING tab) ─────────────────
    # These buttons MUST be clicked (checked) to reveal the widgets below.
    # Calibrate them FIRST, then click each one to expand the section.
    ("btn_toggle_layers_to_filter",     "the LAYERS TO FILTER sidebar pushbutton (left side, checkable toggle)", "point"),
    ("btn_toggle_geometric_predicates", "the GEOMETRIC PREDICATES sidebar pushbutton (left side, checkable toggle)", "point"),
    ("btn_toggle_buffer",               "the BUFFER sidebar pushbutton (left side, checkable toggle)", "point"),

    # ── Widgets INSIDE expanded sections ──────────────────────────────
    # IMPORTANT: Before calibrating the next items, make sure you have
    # CLICKED (checked) the corresponding sidebar pushbutton above
    # to reveal the widget!

    # After clicking "LAYERS TO FILTER" pushbutton:
    ("target_layer_combo",      "[expand LAYERS TO FILTER first!] the TARGET LAYER combobox", "point"),

    # After clicking "GEOMETRIC PREDICATES" pushbutton:
    ("predicate_combo",         "[expand GEOMETRIC PREDICATES first!] the PREDICATE dropdown", "point"),

    # After clicking "BUFFER" pushbutton:
    ("buffer_enable_checkbox",  "[expand BUFFER first!] the BUFFER ENABLE checkbox", "point"),
    ("buffer_value_spinbox",    "[expand BUFFER first!] the BUFFER VALUE spinbox", "point"),

    # Action Bar buttons (always visible, 6 buttons)
    ("filter_button",           "the FILTER button", "point"),
    ("undo_button",             "the UNDO button", "point"),
    ("redo_button",             "the REDO button", "point"),
    ("unfilter_button",         "the UNFILTER / REMOVE FILTER button", "point"),
    ("export_button",           "the EXPORT button", "point"),
    ("about_button",            "the ABOUT button (FilterMate icon)", "point"),

    # Header bar indicators
    ("favorites_button",        "the FAVORITES indicator (star, in header bar)", "point"),
    ("badge_backend",           "the BACKEND indicator (blue pill, in header bar)", "point"),
]


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict, config_path: Path) -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def wait_for_click(prompt: str, countdown: int = 3) -> tuple[int, int]:
    """Wait for user to position mouse, then record position."""
    print(f"\n  ► {prompt}")
    print(f"    Move your mouse there, then press ENTER to record position…")
    input("    [Press ENTER] ")

    try:
        import pyautogui  # type: ignore
        x, y = pyautogui.position()
        print(f"    ✓ Recorded: ({x}, {y})")
        return x, y
    except ImportError:
        print("    ⚠ pyautogui not installed. Enter coordinates manually:")
        raw = input("    x y → ").strip().split()
        return int(raw[0]), int(raw[1])


def calibrate(config_path: Path, targets: list) -> None:
    """Run the interactive calibration session."""
    config = load_config(config_path)
    regions = config.setdefault("qgis", {}).setdefault("regions", {})

    print("=" * 65)
    print("  FilterMate Video Automation — Calibration Tool")
    print("=" * 65)
    print("\nThis tool records the screen positions of QGIS and FilterMate")
    print("UI elements so the automation can click them accurately.\n")
    print("Before starting:")
    print("  1. Open QGIS with FilterMate loaded")
    print("  2. Make sure FilterMate dock is visible (not hidden)")
    print("  3. Select the FILTERING tab in the Toolbox zone")
    print("  4. Put your screen in its normal recording position")
    print()
    print("IMPORTANT: Some widgets are hidden behind checkable sidebar buttons.")
    print("The script will ask you to click the sidebar buttons FIRST, then")
    print("to click on the revealed widgets. Follow the instructions carefully.")
    print()
    input("Press ENTER when ready to begin calibration… ")

    # Track corners for region calculation
    corners: dict[str, dict] = {}

    for region_key, prompt, kind in targets:
        if kind in ("tl", "br"):
            # Bounding box: collect TL and BR corners
            x, y = wait_for_click(prompt)
            corners.setdefault(region_key, {})[kind] = (x, y)
            # When we have both corners, compute width/height
            if "tl" in corners.get(region_key, {}) and "br" in corners.get(region_key, {}):
                tl = corners[region_key]["tl"]
                br = corners[region_key]["br"]
                regions[region_key] = {
                    "x": tl[0],
                    "y": tl[1],
                    "width":  max(1, br[0] - tl[0]),
                    "height": max(1, br[1] - tl[1]),
                }
                print(f"    → Region '{region_key}' saved: {regions[region_key]}")
        elif kind == "point":
            x, y = wait_for_click(prompt)
            regions[region_key] = {"x": x, "y": y}
            print(f"    → Point '{region_key}' saved: ({x}, {y})")

    save_config(config, config_path)
    print("\n" + "=" * 65)
    print("  Calibration complete! Saved to:", config_path)
    print("=" * 65)


def list_calibration(config_path: Path) -> None:
    """Print current calibration data."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})
    print(f"\nCalibration data in {config_path}:\n")
    if not regions:
        print("  (none — run calibrate.py to set up)")
        return
    for key, val in regions.items():
        print(f"  {key:35s} → {val}")
    print()


def reset_calibration(config_path: Path) -> None:
    """Zero out all region coordinates."""
    config = load_config(config_path)
    regions = config.get("qgis", {}).get("regions", {})
    for key in regions:
        if "width" in regions[key]:
            regions[key] = {"x": 0, "y": 0, "width": 0, "height": 0}
        else:
            regions[key] = {"x": 0, "y": 0}
    save_config(config, config_path)
    print(f"Calibration reset in {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive calibration for FilterMate video automation."
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help="Path to config.yaml (default: ../config.yaml)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Print current calibration and exit"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset all calibration values to zero"
    )
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        list_calibration(args.config)
    elif args.reset:
        reset_calibration(args.config)
    else:
        calibrate(args.config, CALIBRATION_TARGETS)


if __name__ == "__main__":
    main()
