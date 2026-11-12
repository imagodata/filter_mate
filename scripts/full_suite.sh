#!/usr/bin/env bash
# The whole test suite with every optional dependency the tests import, so that no test module is skipped
# without a word. The system python3 has no PyQt, GDAL, mcp nor fastapi: there, about 620 tests skip and the
# suite still passes (the tool catalog left stale by #365 went through that way).
#
#   scripts/full_suite.sh [pytest arguments]        e.g. scripts/full_suite.sh -x
#
# 1. A uv venv (FM_TEST_VENV, default ~/.cache/filter_mate/test-venv) with requirements-test*.txt, PyQt5, PyQt6 and
#    Pillow: everything but GDAL, which pip cannot build without the system library.
# 2. The test files that skipped for GDAL, again in the qgis/qgis Docker image (FM_GDAL_IMAGE, default
#    qgis/qgis:stable). FM_SKIP_DOCKER=1 leaves them out and fails, so that a partial run never looks whole.
#
# Fails when pytest fails, or when a test skipped because an import is missing (onnxruntime aside: SAM
# installs it on demand, and its tests also need the model files).
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
if [ "$(basename "$ROOT")" != "filter_mate" ]; then
    echo "The checkout must be in a folder named filter_mate (the tests import the plugin as a package)." >&2
    exit 2
fi

VENV=${FM_TEST_VENV:-$HOME/.cache/filter_mate/test-venv}
IMAGE=${FM_GDAL_IMAGE:-qgis/qgis:stable}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

if [ ! -x "$VENV/bin/python" ]; then
    uv venv -q -p 3.12 "$VENV"
fi
VIRTUAL_ENV="$VENV" uv pip install -q -r requirements-test.txt -r requirements-test-api.txt PyQt5 PyQt6 Pillow

status=0
echo "== 1. venv $VENV"
# pipefail and "|| true" would put the status of true in PIPESTATUS: read it with -e and pipefail off.
set +e +o pipefail
QT_QPA_PLATFORM=offscreen "$VENV/bin/python" -m pytest tests/ -o addopts= -p no:cacheprovider -q -rfEs "$@" \
    | tee "$OUT/venv.txt" | grep -E '^(FAILED|ERROR) |[0-9]+ (passed|failed)'
pytest_status=${PIPESTATUS[0]}
set -e -o pipefail
[ "$pytest_status" -eq 0 ] || status=1

# Skips for a missing import, the GDAL ones apart: they run in step 2.
missing=$(grep -E '^SKIPPED' "$OUT/venv.txt" | grep -i -E "could not import|No module named" \
    | grep -v -i -E "osgeo|onnxruntime" || true)

gdal_files=$(grep -E '^SKIPPED' "$OUT/venv.txt" | grep -i -E "osgeo|GDAL" \
    | sed -E 's/^SKIPPED \[[0-9]+\] ([^:]+):.*/\1/' | sort -u | tr '\n' ' ')

if [ -n "$gdal_files" ]; then
    if [ "${FM_SKIP_DOCKER:-}" = "1" ]; then
        echo "== 2. GDAL files left out (FM_SKIP_DOCKER=1): $gdal_files"
        status=1
    else
        echo "== 2. $IMAGE: $gdal_files"
        set +e +o pipefail
        docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -e QT_QPA_PLATFORM=offscreen \
            -v "$ROOT":/w/filter_mate:ro -w /w/filter_mate "$IMAGE" bash -c \
            "pip install -q --break-system-packages --root-user-action=ignore 'pytest<9.2' pytest-mock shapely pyproj numpy >/dev/null \
             && python3 -m pytest -o addopts= -p no:cacheprovider -q -rfEs $gdal_files" \
            | tee "$OUT/gdal.txt" | grep -E '^(FAILED|ERROR) |[0-9]+ (passed|failed)'
        docker_status=${PIPESTATUS[0]}
        set -e -o pipefail
        [ "$docker_status" -eq 0 ] || status=1
        missing="$missing
$(grep -E '^SKIPPED' "$OUT/gdal.txt" | grep -i -E "could not import|No module named|GDAL" | grep -v -i onnxruntime || true)"
    fi
fi

missing=$(printf '%s\n' "$missing" | sed '/^$/d')
if [ -n "$missing" ]; then
    echo "== Skipped for a missing dependency (the suite is not whole):"
    printf '%s\n' "$missing"
    status=1
fi
exit "$status"
