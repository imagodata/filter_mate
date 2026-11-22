#!/bin/bash
# =============================================================================
# FilterMate - pip package (wheel) builder
# =============================================================================
# Builds dist/filtermate-<VERSION>-py3-none-any.whl: the plugin as the Python
# package `filter_mate`, with the `filtermate` command (see standalone/).
#
# Only what git tracks goes in, as for the plugin zip: the build runs on a copy
# of the tracked files, so notes, logs and scratch files of the checkout stay out.
#
# Usage:
#   bash scripts/build_wheel.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST="$ROOT/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

if ! git -C "$ROOT" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "ERROR: not a git checkout: the wheel is built from the tracked files." >&2
    exit 1
fi

echo "[1/3] Copying the tracked files..."
(cd "$ROOT" && git ls-files -z | tar --null --files-from=- --ignore-failed-read -cf - 2>/dev/null) | tar -xf - -C "$STAGE"

echo "[2/3] Building the wheel..."
mkdir -p "$DIST"
if command -v uv > /dev/null 2>&1; then
    (cd "$STAGE" && uv build --wheel --out-dir "$STAGE/out" > "$STAGE/build.log" 2>&1) || { cat "$STAGE/build.log"; exit 1; }
else
    (cd "$STAGE" && python3 -m build --wheel --outdir "$STAGE/out" > "$STAGE/build.log" 2>&1) || { cat "$STAGE/build.log"; exit 1; }
fi
WHEEL="$(ls "$STAGE"/out/filtermate-*.whl)"
cp "$WHEEL" "$DIST/"

echo "[3/3] Checking its contents..."
python3 - "$DIST/$(basename "$WHEEL")" <<'PY'
import sys
import zipfile

names = zipfile.ZipFile(sys.argv[1]).namelist()
needed = ("filter_mate/__init__.py", "filter_mate/metadata.txt", "filter_mate/filter_mate_dockwidget_base.ui",
          "filter_mate/standalone/cli.py", "filter_mate/standalone/host/app.py",
          "filter_mate/adapters/backends/memory/backend.py", "filter_mate/i18n/FilterMate_fr.qm",
          "filter_mate/config/config.default.json", "filter_mate/icon.png")
missing = [name for name in needed if name not in names]
stray = [name for name in names if "__pycache__" in name or "/tests/" in name or name.endswith((".ts", ".log"))]
if missing or stray:
    print("ERROR: missing", missing, "stray", stray[:5])
    sys.exit(1)
print(f"  {len(names)} files")
PY

echo ""
echo "Built: $DIST/$(basename "$WHEEL")"
echo "Install: pipx install $DIST/$(basename "$WHEEL")"
