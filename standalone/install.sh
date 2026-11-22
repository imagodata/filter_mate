#!/bin/sh
# FilterMate, the standalone application, in one line (macOS, Linux):
#   curl -LsSf https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.sh | sh
# Installs the `filtermate` command with pipx (installed first for this user when missing), then says
# which QGIS it will run on. Nothing needs administrator rights. FILTERMATE_SOURCE changes what is
# installed (a wheel, a branch: git+https://github.com/imagodata/filter_mate@<branch>).
set -eu

SOURCE="${FILTERMATE_SOURCE:-git+https://github.com/imagodata/filter_mate}"

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "FilterMate needs Python 3.9 or later: install it (https://www.python.org/downloads/), then run this again." >&2
    exit 1
fi

if command -v pipx >/dev/null 2>&1; then
    PIPX="pipx"
elif "$PYTHON" -m pipx --version >/dev/null 2>&1; then
    PIPX="$PYTHON -m pipx"
else
    echo "Installing pipx for this user..."
    if ! "$PYTHON" -m pip install --user --quiet pipx 2>/dev/null; then
        # A Python managed by the system (PEP 668) refuses pip: its own pipx package, or a private copy.
        "$PYTHON" -m pip install --user --quiet --break-system-packages pipx
    fi
    PIPX="$PYTHON -m pipx"
fi

echo "Installing FilterMate from $SOURCE..."
$PIPX install --force "$SOURCE"
$PIPX ensurepath >/dev/null 2>&1 || true

BIN="$($PYTHON -c 'import os, sysconfig; print(os.path.join(os.path.expanduser("~"), ".local", "bin"))')"
FILTERMATE="filtermate"
command -v filtermate >/dev/null 2>&1 || FILTERMATE="$BIN/filtermate"
echo
"$FILTERMATE" doctor || true
echo
echo "Start it with: filtermate   (open a new terminal if the command is not found yet)"
echo "No QGIS above? \`filtermate setup\` installs one for FilterMate alone, or install QGIS from https://qgis.org"
