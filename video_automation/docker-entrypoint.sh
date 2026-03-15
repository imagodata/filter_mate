#!/usr/bin/env bash
# =============================================================================
# FilterMate Video Automation — Docker Entrypoint
# =============================================================================
# Starts Xvfb (virtual display), openbox (window manager), then runs the
# video automation pipeline.
#
# Environment variables:
#   DISPLAY      — X display number (default :99)
#   RESOLUTION   — Xvfb resolution (default 1920x1080x24)
#   CAPTURE_FPS  — Frame capture rate (default 10)
#   QGIS_PROJECT — Path to .qgz project file to open (optional)
# =============================================================================

set -euo pipefail

DISPLAY="${DISPLAY:-:99}"
RESOLUTION="${RESOLUTION:-1920x1080x24}"
CAPTURE_FPS="${CAPTURE_FPS:-10}"

echo "══════════════════════════════════════════════════════════════"
echo "  FilterMate Video Automation — Headless Mode"
echo "══════════════════════════════════════════════════════════════"
echo "  Display:     $DISPLAY"
echo "  Resolution:  $RESOLUTION"
echo "  Capture FPS: $CAPTURE_FPS"
echo "══════════════════════════════════════════════════════════════"

# ── 1. Start Xvfb ───────────────────────────────────────────────────────────
echo "[1/4] Starting Xvfb on $DISPLAY ($RESOLUTION)..."
Xvfb "$DISPLAY" -screen 0 "$RESOLUTION" -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to be ready
for i in $(seq 1 30); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        echo "       Xvfb is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Xvfb did not start in 30 seconds."
        exit 1
    fi
    sleep 1
done

export DISPLAY

# ── 2. Start window manager ─────────────────────────────────────────────────
echo "[2/4] Starting openbox window manager..."
openbox &
WM_PID=$!
sleep 1

# ── 3. Start dbus (required by Qt/QGIS) ─────────────────────────────────────
echo "[3/4] Starting dbus session..."
eval "$(dbus-launch --sh-syntax)" 2>/dev/null || true

# ── 4. Launch QGIS if a project is specified ─────────────────────────────────
if [ -n "${QGIS_PROJECT:-}" ] && [ -f "$QGIS_PROJECT" ]; then
    echo "[4/4] Launching QGIS with project: $QGIS_PROJECT"
    qgis --nologo --noplugins "$QGIS_PROJECT" &
    QGIS_PID=$!
    # Wait for QGIS window to appear
    for i in $(seq 1 60); do
        if xdotool search --name "QGIS" >/dev/null 2>&1; then
            echo "       QGIS window detected."
            break
        fi
        if [ "$i" -eq 60 ]; then
            echo "WARNING: QGIS window not detected after 60s."
        fi
        sleep 1
    done
    # Maximize QGIS window
    WID=$(xdotool search --name "QGIS" 2>/dev/null | head -1 || true)
    if [ -n "$WID" ]; then
        xdotool windowactivate "$WID"
        xdotool windowsize "$WID" 1920 1080
        xdotool windowmove "$WID" 0 0
        echo "       QGIS window maximized to 1920x1080."
    fi
else
    echo "[4/4] No QGIS_PROJECT specified — skipping QGIS launch."
fi

# ── 5. Run the video automation ──────────────────────────────────────────────
echo ""
echo "Running video automation..."
echo ""

# Pass all arguments to run.py with --capture flag for headless frame capture
python3 /app/run.py --capture --capture-fps "$CAPTURE_FPS" "$@"
EXIT_CODE=$?

# ── Cleanup ──────────────────────────────────────────────────────────────────
echo ""
echo "Cleaning up..."
kill "$WM_PID" 2>/dev/null || true
kill "${QGIS_PID:-}" 2>/dev/null || true
kill "$XVFB_PID" 2>/dev/null || true

exit $EXIT_CODE
