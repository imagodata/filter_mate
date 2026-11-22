#!/usr/bin/env bash
# Take the screenshots of the user guide (website/guide.html, guide.fr.html) without a screen: QGIS runs in Docker
# under Xvfb, so nothing opens on the desk and the user's QGIS and profile are not touched. Each script grabs the
# widgets of the real plugin (widget.grab(), not the screen) at a 1.5 scale, the scale of the guide's images.
#
#   scripts/guide_screenshots_headless.sh guide       scripts/guide_screenshots.py: EXPLORING, FILTERING, EXPORTING,
#                                                     CONFIGURATION, favorites, Processing, the panels of 5.1.1
#   scripts/guide_screenshots_headless.sh tutorial    scripts/guide_tutorial_screenshots.py: qgis-window, tuto-01..06
#   scripts/guide_screenshots_headless.sh fm5         scripts/fm5_site_screenshots.py: raster and LiDAR (fm5_*.png)
#   scripts/guide_screenshots_headless.sh publish     copy the PNGs of out/ into website/img/guide/
#
# Environment:
#   FM_WORK       work folder (default ~/dev/fm-guide): plugins/, profiles/, out/<run>/, data31/, datatm/
#   FM_GUIDE_GPKG_DIR  folder of the BD TOPO extract of the guide (default $FM_WORK/data31, holding 31.gpkg: a
#                 copy of the commune 31 extract, mounted read-write: SQLite keeps its -wal / -shm beside it)
#   FM5_DATA      folder of the raster / LiDAR square of Fenouillet and Saint-Alban (default $FM_WORK/datatm:
#                 mnt_village.tif, pente_village.tif, estavar.gpkg, estavar_village.copc.laz; copies, the GeoPackage
#                 is in WAL mode)
#   FM_IMAGE      Docker image (default fm-video: qgis/qgis:stable + ffmpeg + PDAL; qgis/qgis:stable also works)
#   FM_GUIDE_UNTIL  a step of guide_screenshots.py: stop after it (one image to retake)
#   FM_GUIDE_LANG   language of QGIS and of the plugin (default en; fr for the pictures that carry words of the panel)
#
# Pitfalls: qgis/qgis:latest shows a tall red message bar (Qt warnings of a debug build); without --user the
# images belong to root; a new profile needs QGIS4.ini or QGIS stops on its first-run dialog.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${FM_WORK:-$HOME/dev/fm-guide}"
IMAGE="${FM_IMAGE:-fm-video}"
GPKG_DIR="${FM_GUIDE_GPKG_DIR:-$WORK/data31}"
DATA="${FM5_DATA:-$WORK/datatm}"

seed_profile() {
    # A fresh profile at every run: the dock of a new install (the rail of sections, nothing apart), FilterMate
    # enabled, its welcome and the offer of its setup dismissed.
    local dir="$WORK/profiles/profiles/fmguide"
    rm -rf "$dir"
    mkdir -p "$dir/QGIS"
    printf '%s\n' '[Processing]' 'hasPortedOldLog=true' '' '[PythonPlugins]' 'processing=true' 'filter_mate=true' '' \
        '[qgis]' 'style=fusion' 'toolbarIconSize=24' '' '[authentication]' 'using-generated-random-password=true' '' \
        '[FilterMate]' 'discord_welcome_dismissed=true' 'whats_new_seen=99' \
        "agent\\setup_offered_version=$(sed -n 's/^version=//p' "$REPO/metadata.txt")" '' \
        '[locale]' "userLocale=${FM_GUIDE_LANG:-en}" > "$dir/QGIS/QGIS4.ini"
    cp "$dir/QGIS/QGIS4.ini" "$dir/QGIS/QGIS3.ini"
}

sync_code() {
    mkdir -p "$WORK/plugins" "$WORK/out" "$WORK/scripts"
    cp "$REPO/scripts/guide_screenshots.py" "$REPO/scripts/guide_tutorial_screenshots.py" \
        "$REPO/scripts/fm5_site_screenshots.py" "$WORK/scripts/"
    rsync -a --delete \
        --exclude .git --exclude .github --exclude .claude --exclude .serena --exclude _bmad --exclude _bmad-output \
        --exclude tests --exclude website --exclude docs --exclude scripts --exclude knowledge --exclude logs \
        --exclude __pycache__ --exclude '*.pyc' --exclude dist --exclude build --exclude reports --exclude research_notes \
        "$REPO/" "$WORK/plugins/filter_mate/"
}

take() {  # take <run> <script> [docker -e arguments...]
    local name="$1" script="$2"; shift 2
    sync_code
    seed_profile
    rm -rf "$WORK/out/$name"; mkdir -p "$WORK/out/$name"
    docker run --rm --init --name "fmguide_$name" --user "$(id -u):$(id -g)" -e HOME=/tmp \
        -v "$WORK:/w" -v "$GPKG_DIR:/bd" -v "$DATA:/data" \
        -e QGIS_PLUGINPATH=/w/plugins -e QT_SCALE_FACTOR=1.5 -e PYTHONDONTWRITEBYTECODE=1 -e FM_PLUGIN_LOADED=1 \
        "$@" "$IMAGE" bash -c \
        "timeout ${FM_TIMEOUT:-900} dbus-run-session -- xvfb-run -a -s '-screen 0 3200x2000x24' qgis --nologo --noversioncheck --lang ${FM_GUIDE_LANG:-en} --profiles-path /w/profiles --profile fmguide --code /w/scripts/$script" \
        > "$WORK/out/$name.stdout.txt" 2>&1 || echo "  $name ended with $?"
    ls "$WORK/out/$name"
}

cmd="${1:-}"; shift || true
case "$cmd" in
    guide)
        take guide guide_screenshots.py -e FM_GUIDE_OUT=/w/out/guide -e FM_GUIDE_GPKG=/bd/31.gpkg \
            -e FM_GUIDE_UNTIL="${FM_GUIDE_UNTIL:-}" -e FM_GUIDE_DOCK_WIDTH="${FM_GUIDE_DOCK_WIDTH:-413}" -e FM_GUIDE_EXPORT_DIR=/home/me/Documents/export
        ;;
    tutorial)
        take tutorial guide_tutorial_screenshots.py -e FM_GUIDE_OUT=/w/out/tutorial -e FM_GUIDE_GPKG=/bd/31.gpkg
        ;;
    fm5)
        take fm5 fm5_site_screenshots.py -e FM5_SITE_OUT=/w/out/fm5 -e FM5_DATA=/data -e FM5_GPKG=/data/estavar.gpkg \
            -e FM5_TILE=/data/estavar_village.copc.laz -e FM_REPO=/w/plugins/filter_mate
        ;;
    publish)
        for run in guide tutorial fm5; do
            for f in "$WORK/out/$run"/*.png; do
                [ -e "$f" ] || continue
                case "$(basename "$f")" in
                    _*) continue ;;  # working images, not in the guide
                    fm5_vector_multiple.png) continue ;;  # the README's image, published with the README
                esac
                cp "$f" "$REPO/website/img/guide/" && echo "published $(basename "$f")"
            done
        done
        ;;
    *)
        sed -n 2,23p "$0"; exit 1 ;;
esac
