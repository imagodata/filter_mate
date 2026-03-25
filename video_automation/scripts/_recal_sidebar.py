"""Quick non-interactive recalibration for sidebar_identify and sidebar_zoom."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pyautogui
import yaml

CONFIG = Path(__file__).parent.parent / "config.yaml"

buttons = ["sidebar_identify", "sidebar_zoom"]

positions = {}
for btn in buttons:
    print(f"\n>>> Placez la souris sur  {btn}  — capture dans 4 secondes...")
    for i in range(4, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    x, y = pyautogui.position()
    positions[btn] = {"x": x, "y": y}
    print(f"  Capture : x={x}, y={y}")

# Update config.yaml
with open(CONFIG, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

for btn, pos in positions.items():
    cfg["qgis"]["regions"][btn] = pos

with open(CONFIG, "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("\nconfig.yaml mis a jour :")
for btn, pos in positions.items():
    print(f"  {btn}: x={pos['x']}, y={pos['y']}")
