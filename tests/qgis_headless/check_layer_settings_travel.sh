#!/bin/bash
# Runs check_layer_settings_travel.py role after role, each "computer" a QGIS profile of its own (see the .py).
#   docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash /src/tests/qgis_headless/check_layer_settings_travel.sh
export FM_WORK=${FM_WORK:-/work} QT_QPA_PLATFORM=xcb
mkdir -p "$FM_WORK"
status=0
for role in A1 B1 A2 C L; do
  computer=${role:0:1}
  FM_ROLE=$role timeout 300 dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' \
    qgis --nologo --noversioncheck --lang en --profiles-path "$FM_WORK/profiles_$computer" \
    --code "${FM_REPO:-/src}/tests/qgis_headless/check_layer_settings_travel.py" 2>&1 | grep -E '^(PASS|FAIL|SETTINGS|INFO|  step|  modal)|Python exception|Traceback|Error'
  [ "${PIPESTATUS[0]}" = 0 ] || status=1
done
exit $status
