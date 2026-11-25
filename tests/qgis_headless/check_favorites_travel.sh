#!/bin/bash
# Runs check_favorites_travel.py role after role, each "computer" a QGIS profile of its own (see the .py).
#   docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash /src/tests/qgis_headless/check_favorites_travel.sh
export FM_WORK=${FM_WORK:-/work} QT_QPA_PLATFORM=xcb
mkdir -p "$FM_WORK"
status=0
for role in ${FM_ROLES:-A1 B1 A2 B2 A3 C AX AY AD AC AT AF AZ AC2 AF5}; do
  computer=${role:0:1}
  if [ "$role" = AT ]; then  # the "New from Template" menu lists the templates of the profile at QGIS's start
    mkdir -p "$FM_WORK/profiles_A/profiles/default/project_templates"
    cp "$FM_WORK/travel.qgz" "$FM_WORK/profiles_A/profiles/default/project_templates/travel_template.qgz"
    cp "$FM_WORK/data.gpkg" "$FM_WORK/profiles_A/profiles/default/project_templates/"  # its layer, by a relative path
  fi
  FM_ROLE=$role timeout 300 dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' \
    qgis --nologo --noversioncheck --lang en --profiles-path "$FM_WORK/profiles_$computer" \
    --code "${FM_REPO:-/src}/tests/qgis_headless/check_favorites_travel.py" 2>&1 | grep -E '^(PASS|FAIL|FAVS|INFO|  step|  modal)|Python exception|Traceback'
  [ "${PIPESTATUS[0]}" = 0 ] || status=1
done
exit $status
