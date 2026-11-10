#!/usr/bin/env bash
# Compile every i18n/FilterMate_*.ts into its .qm with lrelease, inside a qgis/qgis image (Windows QGIS has no lrelease).
#
#   docker run --rm -v "$PWD:/src" -w /src -e OWNER="$(id -u):$(id -g)" qgis/qgis:ltr bash scripts/i18n_release.sh
set -euo pipefail
release=$(command -v lrelease || ls /usr/lib/qt5/bin/lrelease /usr/lib/x86_64-linux-gnu/qt5/bin/lrelease 2>/dev/null | head -1)
echo "lrelease: ${release}"
failed=0
for ts in i18n/FilterMate_*.ts; do
    "${release}" -silent "${ts}" || { echo "FAIL ${ts}"; failed=1; }
done
if [ -n "${OWNER:-}" ]; then
    chown "${OWNER}" i18n/FilterMate_*.qm
fi
exit "${failed}"
