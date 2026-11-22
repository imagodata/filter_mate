#!/bin/bash
# Entry of the FilterMate image: a virtual screen, a window manager, the VNC bridge for the
# browser, then the application in the foreground. The container ends with the application.
#
#   FILTERMATE_SIZE      size of the screen (default 1600x1000)
#   FILTERMATE_PASSWORD  a password asked by the browser page (none by default: publish the port
#                        on 127.0.0.1 only, or behind a proxy that authenticates)
#   FILTERMATE_PORT      port of the page inside the container (default 6080)
# Arguments are passed to `filtermate` (files, --project, --lang...).
set -euo pipefail

SIZE="${FILTERMATE_SIZE:-1600x1000}"
PORT="${FILTERMATE_PORT:-6080}"
DISPLAY_NUMBER=1
export DISPLAY=":${DISPLAY_NUMBER}"
RUN_DIR="$(mktemp -d)"
cleanup() { kill $(jobs -p) 2>/dev/null || true; rm -rf "$RUN_DIR"; }
trap cleanup EXIT

SECURITY=(-SecurityTypes None)
if [ -n "${FILTERMATE_PASSWORD:-}" ]; then
    printf '%s\n' "$FILTERMATE_PASSWORD" | vncpasswd -f > "$RUN_DIR/passwd"
    chmod 600 "$RUN_DIR/passwd"
    SECURITY=(-SecurityTypes VncAuth -PasswordFile "$RUN_DIR/passwd")
fi

# The VNC server listens on the loopback only: the browser reaches it through websockify.
Xvnc "$DISPLAY" -geometry "$SIZE" -depth 24 -localhost -rfbport 5900 -AlwaysShared "${SECURITY[@]}" \
    -nolisten tcp > "$RUN_DIR/xvnc.log" 2>&1 &
for _ in $(seq 50); do
    [ -e "/tmp/.X11-unix/X${DISPLAY_NUMBER}" ] && break
    sleep 0.1
done
openbox > "$RUN_DIR/openbox.log" 2>&1 &
websockify --web /usr/share/novnc "$PORT" localhost:5900 > "$RUN_DIR/websockify.log" 2>&1 &

echo "FilterMate: open http://localhost:${PORT}/vnc.html?autoconnect=1&resize=scale in a browser"

# QGIS waits for a D-Bus session bus before Python on Ubuntu 26.04: one for the application.
cd /data 2>/dev/null || cd /
set +e
dbus-run-session -- filtermate --maximized "$@"
code=$?
set -e
exit "$code"
