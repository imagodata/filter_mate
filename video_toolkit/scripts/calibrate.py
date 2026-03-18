"""
Interactive Calibration Tool
=============================
Records UI element positions for any desktop application by asking the
user to position the mouse on specific elements. Saves results to config.yaml.

This tool is application-agnostic. You define your own GROUPS dict
(or override it in your project-specific calibrate.py) to describe which
UI elements you want to calibrate.

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
    python scripts/calibrate.py                    # Interactive menu
    python scripts/calibrate.py --list             # Show current calibration
    python scripts/calibrate.py --reset            # Reset all regions to zero
    python scripts/calibrate.py --group <group>    # Calibrate only one group
    python scripts/calibrate.py --live             # Live mouse position monitor
    python scripts/calibrate.py --validate         # Check position coherence
    python scripts/calibrate.py --all              # Full calibration session
    python scripts/calibrate.py --review           # Review all positions
    python scripts/calibrate.py --show             # Visualize all positions

Configuration:
    Edit the GROUPS dict below to define the UI elements for YOUR application.
    Each group contains a list of targets: (region_key, prompt, kind)
      - region_key: unique key used in config.yaml regions
      - prompt: description shown to the user
      - kind: "point" for a single x,y; "tl"/"br" for rectangles (top-left, bottom-right)
"""

from __future__ import annotations

import argparse
import copy
import sys
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

# ===========================================================================
# GROUPS — Define your application's UI regions here
# ===========================================================================
# Format for each target tuple:
#   (region_key, description, kind)
#   kind: "point" = single x,y point
#         "tl"    = top-left corner of a rectangle
#         "br"    = bottom-right corner of a rectangle
#         "rect"  = convenience alias for a small rectangular element
#
# Optional 4th element: per-target prerequisite instruction (e.g., "Open menu first")
# Groups with "timer" require the user to position the mouse in advance before
# a countdown captures automatically (useful for menus that auto-close).
#
# Example: customize this for YOUR application.
# ===========================================================================

GROUPS: dict[str, dict] = {
    "main_window": {
        "label": "Main Application Window",
        "desc": "The primary window boundary",
        "targets": [
            ("main_window", "TOP-LEFT corner of the main application window", "tl"),
            ("main_window", "BOTTOM-RIGHT corner of the main application window", "br"),
        ],
    },
    "toolbar": {
        "label": "Toolbar",
        "desc": "Main toolbar / ribbon area",
        "targets": [
            ("toolbar", "TOP-LEFT corner of the toolbar", "tl"),
            ("toolbar", "BOTTOM-RIGHT corner of the toolbar", "br"),
        ],
    },
    "content_area": {
        "label": "Content Area",
        "desc": "Main content / editor / canvas area",
        "targets": [
            ("content_area", "TOP-LEFT corner of the content area", "tl"),
            ("content_area", "BOTTOM-RIGHT corner of the content area", "br"),
        ],
    },
    "menu_bar": {
        "label": "Menu Bar Items",
        "desc": "Menu bar items (File, Edit, View, etc.)",
        "targets": [
            ("menu_file", "the FILE menu item in the menu bar", "point"),
            ("menu_edit", "the EDIT menu item in the menu bar", "point"),
            ("menu_view", "the VIEW menu item in the menu bar", "point"),
            ("menu_help", "the HELP menu item in the menu bar", "point"),
        ],
    },
    "menu_items": {
        "label": "Dropdown Menu Items",
        "desc": "Open each menu BEFORE capturing the item position.",
        "timer": 5,
        "targets": [
            ("menu_file_new", "the NEW item under the File menu", "point",
             "Open the File menu first"),
            ("menu_file_open", "the OPEN item under the File menu", "point",
             "Open the File menu first"),
            ("menu_file_save", "the SAVE item under the File menu", "point",
             "Open the File menu first"),
        ],
    },
    "dialogs": {
        "label": "Dialog Elements",
        "desc": "Elements inside dialogs (open the dialog first).",
        "timer": 5,
        "prereq": "Open the relevant dialog before proceeding.",
        "targets": [
            ("dialog_ok_button", "the OK / Confirm button in the dialog", "point"),
            ("dialog_cancel_button", "the Cancel button in the dialog", "point"),
        ],
    },
    "status_bar": {
        "label": "Status Bar",
        "desc": "Status bar at the bottom of the window",
        "targets": [
            ("status_bar", "TOP-LEFT corner of the status bar", "tl"),
            ("status_bar", "BOTTOM-RIGHT corner of the status bar", "br"),
        ],
    },
}

# Flat list for backwards compatibility
CALIBRATION_TARGETS = []
for _g in GROUPS.values():
    CALIBRATION_TARGETS.extend(_g["targets"])


# ── Config I/O ────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict, config_path: Path) -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── Mouse helpers ─────────────────────────────────────────────────────────

def _get_pyautogui():
    try:
        import pyautogui
        return pyautogui
    except ImportError:
        return None


def get_mouse_position():
    pag = _get_pyautogui()
    if pag:
        return pag.position()
    return None


# ── Visual feedback helpers ──────────────────────────────────────────────

def _show_position_circle(pag, cx, cy, radius=25, loops=2, duration=0.8):
    import math
    steps = 30 * loops
    step_delay = duration / steps
    for i in range(steps + 1):
        angle = 2 * math.pi * i / (steps // loops)
        nx = int(cx + radius * math.cos(angle))
        ny = int(cy + radius * math.sin(angle))
        pag.moveTo(nx, ny, duration=step_delay, _pause=False)
    pag.moveTo(cx, cy, duration=0.1, _pause=False)


def _show_position_rect(pag, x, y, w, h, duration=0.8):
    step_dur = duration / 4
    pag.moveTo(x, y, duration=0.1, _pause=False)
    pag.moveTo(x + w, y, duration=step_dur, _pause=False)
    pag.moveTo(x + w, y + h, duration=step_dur, _pause=False)
    pag.moveTo(x, y + h, duration=step_dur, _pause=False)
    pag.moveTo(x, y, duration=step_dur, _pause=False)
    pag.moveTo(x + w // 2, y + h // 2, duration=0.1, _pause=False)


def _show_position_cross(pag, cx, cy, size=20, duration=0.4):
    step_dur = duration / 4
    pag.moveTo(cx - size, cy, duration=0.05, _pause=False)
    pag.moveTo(cx + size, cy, duration=step_dur, _pause=False)
    pag.moveTo(cx, cy, duration=0.05, _pause=False)
    pag.moveTo(cx, cy - size, duration=0.05, _pause=False)
    pag.moveTo(cx, cy + size, duration=step_dur, _pause=False)
    pag.moveTo(cx, cy, duration=0.05, _pause=False)


def _countdown(seconds, message=""):
    if message:
        sys.stdout.write(f"       >> {message} ")
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"{i}... ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("GO!\n")
    sys.stdout.flush()


def show_position(val):
    if val is None:
        return
    pag = _get_pyautogui()
    if pag is None:
        return
    try:
        if "width" in val and val.get("width", 0) > 0:
            _show_position_rect(pag, val["x"], val["y"], val["width"], val["height"], duration=0.6)
            cx = val["x"] + val["width"] // 2
            cy = val["y"] + val["height"] // 2
            _show_position_cross(pag, cx, cy, size=15, duration=0.3)
        else:
            cx, cy = val["x"], val["y"]
            pag.moveTo(cx, cy, duration=0.3, _pause=False)
            _show_position_cross(pag, cx, cy, size=20, duration=0.3)
            _show_position_circle(pag, cx, cy, radius=25, loops=1, duration=0.5)
    except Exception:
        print("       ! Visualisation impossible (mouse in corner? move it away)")


# ── Display helpers ───────────────────────────────────────────────────────

def _format_value(val):
    if "width" in val:
        return f"({val['x']:>5}, {val['y']:>5})  {val['width']:>4}x{val['height']:<4}"
    return f"({val['x']:>5}, {val['y']:>5})"


def _is_calibrated(val):
    if val.get("x", 0) == 0 and val.get("y", 0) == 0:
        if val.get("width", 1) == 0 and val.get("height", 1) == 0:
            return False
        if "width" not in val:
            return False
    return True


def _status_icon(val):
    if val is None:
        return "  "
    return "ok" if _is_calibrated(val) else "!!"


# ── Config key for regions ────────────────────────────────────────────────

def _get_regions(config: dict) -> dict:
    """Get the regions dict from config, supporting both 'app' and 'qgis' nesting."""
    if "app" in config:
        return config["app"].setdefault("regions", {})
    if "qgis" in config:
        return config["qgis"].setdefault("regions", {})
    # Flat config
    return config.setdefault("regions", {})


# ── Core commands ─────────────────────────────────────────────────────────

def cmd_list(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)
    print()
    print("=" * 72)
    print("  Video Toolkit — Current Calibration")
    print("=" * 72)

    if not regions:
        print("\n  (no calibration yet — run calibrate.py)")
        return

    known_keys = set()
    for group_id, group in GROUPS.items():
        print(f"\n  [{group_id}] {group['label']}")
        print(f"  {'─' * 60}")
        group_keys = {t[0] for t in group["targets"]}
        for key in group_keys:
            known_keys.add(key)
            val = regions.get(key)
            status = _status_icon(val)
            if val:
                print(f"  {status}  {key:38s} {_format_value(val)}")
            else:
                print(f"  --  {key:38s} (not defined)")

    extra = set(regions.keys()) - known_keys
    if extra:
        print(f"\n  [extra] Additional elements")
        print(f"  {'─' * 60}")
        for key in sorted(extra):
            val = regions[key]
            status = _status_icon(val)
            print(f"  {status}  {key:38s} {_format_value(val)}")

    total = len(regions)
    calibrated = sum(1 for v in regions.values() if _is_calibrated(v))
    missing = total - calibrated
    print(f"\n  {'─' * 60}")
    print(f"  Total: {total} | Calibrated: {calibrated} | Missing: {missing}")
    if missing > 0:
        print(f"  !! {missing} element(s) not calibrated (marked '!!')")
    print()


def cmd_live(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)
    pag = _get_pyautogui()
    if not pag:
        print("  pyautogui required. pip install pyautogui")
        return

    print()
    print("=" * 60)
    print("  LIVE Mode — Real-time mouse position")
    print("  Press Ctrl+C to quit")
    print("=" * 60)
    print()
    try:
        while True:
            x, y = pag.position()
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
            nearest_info = f"  ~ {nearest_key} ({nearest_dist:.0f}px)" if nearest_key and nearest_dist < 200 else ""
            sys.stdout.write(f"\r  Mouse: ({x:>5}, {y:>5}){nearest_info:50s}")
            sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n  Live mode ended.\n")


def cmd_validate(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)
    print()
    print("=" * 60)
    print("  Calibration Validation")
    print("=" * 60)

    errors = []
    warnings = []

    # Check for uncalibrated positions
    for key, val in regions.items():
        if val.get("x", 0) == 0 and val.get("y", 0) == 0:
            warnings.append(f"{key}: position (0, 0) — probably not calibrated")

    # Check all known group targets are defined
    for group_id, group in GROUPS.items():
        for target in group["targets"]:
            key = target[0]
            if key not in regions:
                warnings.append(f"{key}: not in config (group: {group_id})")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    !! {e}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    ?? {w}")

    if not errors and not warnings:
        print("\n  All positions look coherent!")
    print()


def record_position(prompt, current_value=None):
    print(f"\n  >> {prompt}")
    if current_value:
        if "width" in current_value:
            print(f"     Current: x={current_value['x']}, y={current_value['y']}, "
                  f"w={current_value['width']}, h={current_value['height']}")
        else:
            print(f"     Current: x={current_value['x']}, y={current_value['y']}")

    print("     Position mouse on element, then press ENTER")
    print("     Or type coordinates manually: x y")
    print("     Or type 's' to keep current value")

    while True:
        raw = input("     > ").strip()

        if raw.lower() == "s" and current_value:
            return current_value["x"], current_value["y"]

        if raw == "":
            pos = get_mouse_position()
            if pos:
                x, y = pos
                print(f"     + Recorded: ({x}, {y})")
                return x, y
            else:
                print("     ! pyautogui not available. Type coordinates: x y")
                continue

        parts = raw.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                x, y = int(parts[0]), int(parts[1])
                print(f"     + Recorded: ({x}, {y})")
                return x, y
            except ValueError:
                pass
        print("     ! Invalid format. Type 'x y' or press ENTER.")


def cmd_calibrate_group(config_path: Path, group_id: str) -> None:
    if group_id not in GROUPS:
        print(f"  Unknown group: '{group_id}'")
        print(f"  Available groups: {', '.join(GROUPS.keys())}")
        return

    group = GROUPS[group_id]
    config = load_config(config_path)
    regions = _get_regions(config)

    print(f"\n  Calibrating group: {group['label']}")
    print(f"  {group['desc']}")
    print()

    _calibrate_targets(config, regions, group["targets"], config_path=config_path,
                       group_timer=group.get("timer", 0), group_prereq=group.get("prereq", ""))
    print(f"\n  Group '{group_id}' done.")


def cmd_calibrate_all(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)

    print()
    print("=" * 65)
    print("  Video Toolkit — Interactive Calibration")
    print("=" * 65)
    print()
    print("  Before starting:")
    print("  1. Open your application and make it fully visible")
    print("  2. Set the screen to your recording resolution")
    print()
    print("  For each element:")
    print("    ENTER       = record mouse position")
    print("    x y         = enter coordinates manually")
    print("    s           = skip (keep current value)")
    print()

    for idx, (group_id, group) in enumerate(GROUPS.items(), 1):
        print(f"\n  ━━━ [{idx}/{len(GROUPS)}] {group['label']} ━━━")
        if group.get("desc"):
            print(f"      {group['desc']}")
        _calibrate_targets(config, regions, group["targets"], config_path=config_path,
                           group_timer=group.get("timer", 0), group_prereq=group.get("prereq", ""))

    print()
    print("=" * 65)
    print(f"  Calibration complete! Saved to: {config_path}")
    print("=" * 65)
    print()


def _calibrate_targets(config, regions, targets, config_path=None,
                       group_timer=0, group_prereq=""):
    corners: dict[str, dict] = {}

    if group_prereq:
        print(f"\n  ┌─ PREREQUISITE ─────────────────────────────────")
        print(f"  │  {group_prereq}")
        print(f"  └────────────────────────────────────────────────")

    def _auto_save(region_key, new_val):
        old_val = regions.get(region_key)
        regions[region_key] = new_val
        if config_path and new_val != old_val:
            save_config(config, config_path)

    for target in targets:
        region_key, prompt, kind = target[0], target[1], target[2]
        target_prereq = target[3] if len(target) > 3 else ""
        current = regions.get(region_key)

        auto_capture = False
        if target_prereq:
            print(f"\n     ┌─ PREREQUISITE ─────────────────────────")
            print(f"     │  {target_prereq}")
            print(f"     │  Then position mouse on: {prompt}")
            print(f"     │  Press ENTER when ready (s = skip)")
            print(f"     └──────────────────────────────────────────")
            ready = input("     ready? ").strip().lower()
            if ready == "s":
                print(f"     (skipped)")
                continue
            if group_timer > 0:
                _countdown(group_timer, "Capturing in")
                auto_capture = True
        elif group_timer > 0:
            print(f"\n  >> {prompt}")
            print(f"     Position mouse on element.")
            print(f"     Press ENTER when ready (s = skip)")
            ready = input("     ready? ").strip().lower()
            if ready == "s":
                print(f"     (skipped)")
                continue
            _countdown(group_timer, "Capturing in")
            auto_capture = True

        if auto_capture:
            pos = get_mouse_position()
            if pos:
                x, y = pos
                print(f"     + Recorded: ({x}, {y})")
            else:
                print(f"     ! pyautogui not available, manual entry required")
                x, y = record_position(prompt, current)
        else:
            x, y = record_position(prompt, current)

        if kind in ("tl", "br"):
            corners.setdefault(region_key, {})[kind] = (x, y)
            if "tl" in corners.get(region_key, {}) and "br" in corners.get(region_key, {}):
                tl = corners[region_key]["tl"]
                br = corners[region_key]["br"]
                new_val = {
                    "x": tl[0], "y": tl[1],
                    "width": max(1, br[0] - tl[0]),
                    "height": max(1, br[1] - tl[1]),
                }
                print(f"     -> Region '{region_key}': {_format_value(new_val)}")
                _auto_save(region_key, new_val)
        elif kind == "point":
            new_val = {"x": x, "y": y}
            _auto_save(region_key, new_val)
        else:  # "rect" and others
            new_val = {"x": x, "y": y}
            _auto_save(region_key, new_val)


def cmd_review(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)

    print()
    print("=" * 72)
    print("  REVIEW ALL POSITIONS (with visual feedback)")
    print("=" * 72)
    print()
    print("  The cursor moves to each registered position.")
    print("  Verify visually if the position is correct.")
    print()
    print("  For each element:")
    print("    ENTER        = keep current value (OK)")
    print("    m + ENTER    = capture current mouse position")
    print("    x y          = enter new coordinates")
    print("    d            = delete this element")
    print("    q            = quit (saves changes)")
    print()

    modified = 0
    total = 0

    for group_id, group in GROUPS.items():
        group_keys = []
        for target in group["targets"]:
            if target[0] not in group_keys:
                group_keys.append(target[0])

        print(f"\n  ━━━ {group['label']} ━━━")

        for key in group_keys:
            total += 1
            val = regions.get(key)
            action, changed = _review_single(key, val, regions)
            if changed:
                modified += 1
                save_config(config, config_path)
            if action == "quit":
                save_config(config, config_path)
                print(f"\n  Review interrupted. {modified} change(s) saved.")
                return

    save_config(config, config_path)
    print()
    print("=" * 72)
    print(f"  Review done: {total} elements, {modified} change(s)")
    print(f"  Saved to: {config_path}")
    print("=" * 72)
    print()


def _review_single(key, val, regions):
    status = _status_icon(val)
    val_str = _format_value(val) if val else "(not defined)"

    print(f"\n  [{status}] {key}")
    print(f"       Current: {val_str}")

    if val and _is_calibrated(val):
        show_position(val)

    raw = input("       > ").strip()

    if raw.lower() == "q":
        return "quit", False
    if raw.lower() == "d":
        if key in regions:
            del regions[key]
            print(f"       - Deleted")
        return "continue", True
    if raw == "":
        return "continue", False
    if raw.lower() == "m":
        pos = get_mouse_position()
        if pos:
            x, y = pos
            if val and "width" in val:
                regions[key] = {"x": x, "y": y, "width": val["width"], "height": val["height"]}
            else:
                regions[key] = {"x": x, "y": y}
            print(f"       + Updated: {_format_value(regions[key])}")
            show_position(regions[key])
            return "continue", True
        return "continue", False

    parts = raw.replace(",", " ").split()
    if len(parts) >= 4 and val and "width" in val:
        try:
            regions[key] = {
                "x": int(parts[0]), "y": int(parts[1]),
                "width": int(parts[2]), "height": int(parts[3]),
            }
            print(f"       + Updated: {_format_value(regions[key])}")
            show_position(regions[key])
            return "continue", True
        except ValueError:
            pass
    if len(parts) >= 2:
        try:
            x, y = int(parts[0]), int(parts[1])
            if val and "width" in val:
                regions[key] = {"x": x, "y": y, "width": val["width"], "height": val["height"]}
            else:
                regions[key] = {"x": x, "y": y}
            print(f"       + Updated: {_format_value(regions[key])}")
            show_position(regions[key])
            return "continue", True
        except ValueError:
            pass

    print("       ! Invalid format, value unchanged")
    return "continue", False


def cmd_reset(config_path: Path) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)
    print(f"\n  WARNING: This will reset ALL {len(regions)} positions to zero!")
    confirm = input("  Confirm? (yes/no) > ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Cancelled.")
        return
    for key in regions:
        if "width" in regions[key]:
            regions[key] = {"x": 0, "y": 0, "width": 0, "height": 0}
        else:
            regions[key] = {"x": 0, "y": 0}
    save_config(config, config_path)
    print(f"  All positions reset in {config_path}")


def cmd_edit(config_path: Path, region_key: str) -> None:
    config = load_config(config_path)
    regions = _get_regions(config)
    val = regions.get(region_key)
    print(f"\n  Editing: {region_key}")
    if val:
        print(f"  Current value: {_format_value(val)}")
    else:
        print("  (not defined)")

    x, y = record_position(region_key, val)
    if val and "width" in val:
        print("  Position mouse on BOTTOM-RIGHT corner, then ENTER")
        br_x, br_y = record_position("bottom-right corner", None)
        regions[region_key] = {
            "x": x, "y": y,
            "width": max(1, br_x - x), "height": max(1, br_y - y),
        }
    else:
        regions[region_key] = {"x": x, "y": y}
    save_config(config, config_path)
    print(f"  + Saved: {_format_value(regions[region_key])}")


def cmd_interactive_menu(config_path: Path) -> None:
    print()
    print("=" * 65)
    print("  Video Toolkit — Calibration Tool")
    print("=" * 65)

    while True:
        config = load_config(config_path)
        regions = _get_regions(config)
        total = len(regions)
        calibrated = sum(1 for v in regions.values() if _is_calibrated(v))

        print()
        print(f"  Positions: {calibrated}/{total} calibrated")
        print()
        print("  Commands:")
        print("    list         List all positions")
        print("    review       Review ALL positions (correct)")
        print("    all          Full calibration session")
        print("    group <id>   Calibrate a specific group")
        print("    edit <key>   Edit a single position")
        print("    live         Live mouse position mode")
        print("    validate     Check position coherence")
        print("    reset        Reset all to zero")
        print("    quit         Exit")
        print()
        print(f"  Groups: {', '.join(GROUPS.keys())}")
        print()

        raw = input("  > ").strip()
        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "q", "exit"):
            print("  Goodbye!")
            break
        elif cmd in ("list", "ls", "l"):
            cmd_list(config_path)
        elif cmd in ("review", "r"):
            cmd_review(config_path)
        elif cmd in ("all", "a"):
            cmd_calibrate_all(config_path)
        elif cmd in ("group", "g"):
            if arg:
                cmd_calibrate_group(config_path, arg)
            else:
                print(f"  Usage: group <id>  |  Groups: {', '.join(GROUPS.keys())}")
        elif cmd in ("edit", "e"):
            if arg:
                cmd_edit(config_path, arg)
            else:
                print("  Usage: edit <region_key>")
        elif cmd == "live":
            cmd_live(config_path)
        elif cmd in ("validate", "check", "v"):
            cmd_validate(config_path)
        elif cmd == "reset":
            cmd_reset(config_path)
        elif cmd in GROUPS:
            cmd_calibrate_group(config_path, cmd)
        else:
            print(f"  Unknown command: '{cmd}'")


# ── CLI entry point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive calibration tool for Video Toolkit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calibrate.py                       Interactive menu
  python calibrate.py --list                Show current positions
  python calibrate.py --group main_window   Calibrate main window
  python calibrate.py --edit menu_file      Edit a single position
  python calibrate.py --live                Live mouse position
  python calibrate.py --validate            Check coherence
  python calibrate.py --all                 Full calibration session
        """,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="Path to config.yaml")
    parser.add_argument("--list", action="store_true", help="List current positions")
    parser.add_argument("--reset", action="store_true", help="Reset all positions to zero")
    parser.add_argument("--group", type=str, metavar="ID", help="Calibrate a specific group")
    parser.add_argument("--edit", type=str, metavar="KEY", help="Edit a single position")
    parser.add_argument("--live", action="store_true", help="Live mouse position mode")
    parser.add_argument("--validate", action="store_true", help="Check position coherence")
    parser.add_argument("--all", action="store_true", help="Full calibration session")
    parser.add_argument("--review", action="store_true", help="Review all positions")

    args = parser.parse_args()

    if not args.config.exists():
        print(f"Error: config not found: {args.config}", file=sys.stderr)
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
    else:
        cmd_interactive_menu(args.config)


if __name__ == "__main__":
    main()
