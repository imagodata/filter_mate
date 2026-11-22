#!/bin/bash
# =============================================================================
# FilterMate - publish the `filtermate` package on PyPI (or TestPyPI)
# =============================================================================
# Builds the wheel and the source archive from the tracked files, checks them
# with twine, then uploads them. Needs an API token of the PyPI account:
#
#   PYPI_TOKEN=pypi-... bash scripts/publish_pypi.sh            # pypi.org
#   PYPI_TOKEN=pypi-... bash scripts/publish_pypi.sh --test     # test.pypi.org
#   bash scripts/publish_pypi.sh --dry-run                      # build and check only
#
# The version is the plugin's (metadata.txt). PyPI refuses a version already
# uploaded: bump metadata.txt first.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPOSITORY="https://upload.pypi.org/legacy/"
DRY_RUN=0
for argument in "$@"; do
    case "$argument" in
        --test) REPOSITORY="https://test.pypi.org/legacy/" ;;
        --dry-run) DRY_RUN=1 ;;
        *) echo "Unknown option: $argument" >&2; exit 2 ;;
    esac
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
(cd "$ROOT" && git ls-files -z | tar --null --files-from=- --ignore-failed-read -cf - 2>/dev/null) | tar -xf - -C "$STAGE"

echo "[1/3] Building the wheel and the source archive..."
(cd "$STAGE" && uv build --out-dir "$STAGE/out" > "$STAGE/build.log" 2>&1) || { cat "$STAGE/build.log"; exit 1; }
ls -1 "$STAGE"/out/filtermate-*

echo "[2/3] Checking them..."
uvx twine check --strict "$STAGE"/out/filtermate-*

if [ "$DRY_RUN" = 1 ]; then
    mkdir -p "$ROOT/dist" && cp "$STAGE"/out/filtermate-* "$ROOT/dist/"
    echo "Dry run: copied to dist/, nothing uploaded."
    exit 0
fi
if [ -z "${PYPI_TOKEN:-}" ]; then
    echo "PYPI_TOKEN is not set: nothing uploaded." >&2
    exit 1
fi

echo "[3/3] Uploading to $REPOSITORY..."
TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_TOKEN" uvx twine upload --non-interactive \
    --repository-url "$REPOSITORY" "$STAGE"/out/filtermate-*
echo "Published. Install with: pipx install filtermate"
