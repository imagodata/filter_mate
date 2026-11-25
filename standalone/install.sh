#!/bin/sh
# FilterMate, the standalone application, in one line (macOS, Linux):
#   curl -LsSf https://raw.githubusercontent.com/imagodata/filter_mate/v5.1.2/standalone/install.sh | sh
# Installs the `filtermate` command with pipx (installed first for this user when missing), then says
# which QGIS it will run on. No administrator rights once Python 3.9+ and pipx are there; installing those
# themselves may need them (a system package below). FILTERMATE_SOURCE changes what is installed
# (a wheel, the zip of another tag or branch, git+https://...).
set -eu

# A release tag, not the moving main: what is installed is fixed (audit of 2026-11-24). The release process
# moves this default with the tag.
SOURCE="${FILTERMATE_SOURCE:-https://github.com/imagodata/filter_mate/archive/refs/tags/v5.1.2.zip}"

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
elif "$PYTHON" -m pip install --user --quiet pipx 2>/dev/null; then
    PIPX="$PYTHON -m pipx"
else
    # A Python managed by the system (PEP 668) refuses pip into its user site, where the Python of QGIS
    # lives on some systems: forcing it there (--break-system-packages) could break QGIS, so this stops
    # with the way instead (audit of 2026-11-24).
    echo "FilterMate needs pipx, and this Python refuses it into its user site (PEP 668)." >&2
    echo "On Debian/Ubuntu: sudo apt install pipx python3-venv. On Fedora: sudo dnf install pipx." >&2
    echo "On macOS: brew install pipx. Then run this again." >&2
    exit 1
fi

echo "Installing FilterMate from $SOURCE..."
$PIPX install --force "$SOURCE"
echo "Putting ~/.local/bin on the PATH of new shells (pipx ensurepath)..."
$PIPX ensurepath >/dev/null 2>&1 || true

BIN="$($PYTHON -c 'import os, sysconfig; print(os.path.join(os.path.expanduser("~"), ".local", "bin"))')"
FILTERMATE="filtermate"
command -v filtermate >/dev/null 2>&1 || FILTERMATE="$BIN/filtermate"
echo
"$FILTERMATE" doctor || true
echo
echo "Start it with: filtermate   (open a new terminal if the command is not found yet)"
echo "No QGIS above? \`filtermate setup\` installs one for FilterMate alone, or install QGIS from https://qgis.org"
