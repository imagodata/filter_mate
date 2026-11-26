#!/usr/bin/env bash
# Record and edit the clips of scripts/site_videos.py without a screen: QGIS runs in Docker under Xvfb, so nothing
# opens on the desk and the user's QGIS and profile are not touched. The Recorder grabs the main window of QGIS
# (not the screen), so the footage is the real plugin in a real QGIS.
#
#   scripts/site_videos_headless.sh image                 build the image (QGIS stable + ffmpeg + fonts + pdal)
#   scripts/site_videos_headless.sh clip hero bridges ... record, then edit each clip (one QGIS at a time)
#   scripts/site_videos_headless.sh clip hero-dark ...    the dark version: profile fmvideo-dark (Night Mapping)
#   scripts/site_videos_headless.sh publish hero hero-dark ...  copy the edited MP4 / WebP into website/video/
#   python3 scripts/site_takes_check.py ~/dev/fm-video hero ...  read each take before it is published (dock in one
#                                                         piece, no empty band, the counts the pages quote)
#   scripts/site_videos_headless.sh sam-model             fetch SAM 2.1 and onnxruntime into the recording profile
#
# Environment:
#   FM_WORK        work folder (default ~/dev/fm-video): plugins/, profiles/, out/<clip>/, out/site/<clip>.mp4
#   FM_GPKG_DIR    folder of the BD TOPO GeoPackage (mounted read-write: SQLite keeps its -wal / -shm beside it)
#   FM_GPKG_NAME   its file name
#   FM5_DATA       folder of the raster / point cloud square (mnt_village.tif, pente_village.tif, estavar.gpkg,
#                  estavar_village.copc.laz, ortho_rvb.tif), see "data" of scripts/site_videos.sh
#   FM_SIZE        size of the edited video (default 1920x1080; the site uses FM_SIZE=1280x720 FM_CRF=30)
#   FM_DOCKER_ARGS more arguments of docker run: "--network host" for a local Ollama (clip agent),
#                  "--network <net>" to reach a PostGIS container (clip postgis, with FM_PG)
#   every FM_* / FM5_* variable of scripts/site_videos.py set in this shell is passed to QGIS (FM_PLACE_RIVER,
#   FM5_EXTENT, FM_PG, FM_AGENT_MODEL...)
#
# The teaser of 5.1.1 (Toulouse Métropole, edited by scripts/teaser_compose.py) was recorded with:
#   FM_PLACE_RIVER=Blagnac FM_PLACE_NOISE=Colomiers FM_PLACE_EXPORT=Blagnac \
#   FM5_EXTENT=571000,6289000,572000,6290000 FM5_DTM_RANGE=122,135 FM5_HEIGHT=7 \
#   FM5_SURVEY_EXPR="\"usage_1\" = 'Commercial et services'" FM5_SURVEY_RECT=571230,6289080,571600,6289450 \
#   scripts/site_videos_headless.sh clip metropole bridges explore heights survey compare favorites export processing sam
#   FM_DOCKER_ARGS="--network host" FM_AGENT_MODEL=qwen3.5:4b scripts/site_videos_headless.sh clip agent
# The teaser of the Urumea flood (clip urumea in scripts/site_videos.py, six agent requests, no BD TOPO
# needed: the data comes live from Overpass and Copernicus). The Claude key travels in the environment
# only, into the container's auth database, never in a file:
#   FM_AGENT_KEY=<revocable key> FM_AGENT_MODEL=claude-haiku-5-5 scripts/site_videos_headless.sh clip urumea
# The key needs a working secrets service: /tmp/.cache is owned by root in the image, so mount a
# writable one (FM_DOCKER_ARGS="-v /tmp/fm-cache:/tmp/.cache"); the login keyring is created unlocked
# inside the session bus before QGIS starts (outside the bus it conflicts and hangs the setup).
# Stories 13 to 15 (ndvi, roofs, ground) use the square of FM5_DATA (ortho_irc.tif too); story 16 (wires) a LiDAR
# survey with classified wires, wellington_lines.copc.laz, mounted read-only:
#   FM_DOCKER_ARGS="-v <its folder>:/wires:ro" FM_SIZE=1280x720 FM_CRF=30 scripts/site_videos_headless.sh clip wires
#   FM_DOCKER_ARGS="--network <net of the PostGIS container>" FM_PG="host=... dbname=... user=... password=..." \
#   scripts/site_videos_headless.sh clip postgis
# (a model that does not fit the graphics card never answers within the take: qwen3:8b with a 16k context on 8 GB)
#
# Pitfalls met on 2026-11-14: qgis/qgis:latest shows a tall red message bar (Qt warnings of a debug build);
# without --user the frames belong to root; a new profile needs QGIS4.ini or QGIS stops on its first-run dialog.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${FM_WORK:-$HOME/dev/fm-video}"
IMAGE="${FM_IMAGE:-fm-video}"
GPKG_DIR="${FM_GPKG_DIR:-/mnt/c/Users/Simon/Documents/bdtopo31}"
GPKG_NAME="${FM_GPKG_NAME:-BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg}"
DATA="${FM5_DATA:-$WORK/data}"
PROFILE="$WORK/profiles/profiles/fmvideo"

seed_profile() {
    # A new profile stops on QGIS's first-run dialog before --code runs: start from settings that went through it,
    # FilterMate enabled, its welcome and the offer of its setup dismissed. fmvideo-dark has the Night Mapping theme.
    # Before every take, what a take may have left is forgotten: the sections apart, the order of the rails and the
    # layout settings (config.json), so each one starts from the dock of a new install.
    local dir="$WORK/profiles/profiles/$1"
    mkdir -p "$dir/QGIS"
    if [ ! -f "$dir/QGIS/QGIS4.ini" ]; then
        printf '%s\n' '[Processing]' 'hasPortedOldLog=true' '' '[PythonPlugins]' 'processing=true' 'filter_mate=true' '' \
            '[qgis]' 'style=fusion' 'toolbarIconSize=24' '' '[authentication]' 'using-generated-random-password=true' '' \
            '[rendering]' 'main-canvas-preview-jobs=true' '' '[FilterMate]' 'discord_welcome_dismissed=true' \
            'whats_new_seen=99' "agent\\setup_offered_version=$(sed -n 's/^version=//p' "$REPO/metadata.txt")" '' \
            '[locale]' 'userLocale=en' > "$dir/QGIS/QGIS4.ini"
        if [ "$1" = fmvideo-dark ]; then printf '%s\n' '' '[UI]' 'UITheme=Night Mapping' >> "$dir/QGIS/QGIS4.ini"; fi
        cp "$dir/QGIS/QGIS4.ini" "$dir/QGIS/QGIS3.ini"
    fi
    sed -i -e '/^panels\\/d' -e '/^sections\\/d' "$dir/QGIS/QGIS4.ini"
    rm -f "$dir/FilterMate/config.json"
    # A previous take may have left its auth database with another master password: the next
    # take would then prompt instead of using its own, hanging headless. Fresh wallet each take.
    rm -f "$dir/QGIS/qgis-auth.db"*
}

sync_code() {
    mkdir -p "$WORK/plugins" "$WORK/out" "$WORK/scripts" "$DATA"
    cp "$REPO/scripts/site_videos.py" "$REPO/scripts/site_video_render.py" "$REPO/scripts/site_stills.json" "$WORK/scripts/"
    rsync -a --delete \
        --exclude .git --exclude .github --exclude .claude --exclude .serena --exclude _bmad --exclude _bmad-output \
        --exclude tests --exclude website --exclude docs --exclude scripts --exclude knowledge --exclude logs \
        --exclude __pycache__ --exclude '*.pyc' --exclude dist --exclude build --exclude reports --exclude research_notes \
        "${FM_PLUGIN_SRC:-$REPO}/" "$WORK/plugins/filter_mate/"
}

passed_env() {
    # every FM_* / FM5_* variable of this shell, except the ones this script sets itself
    env | grep -E '^(FM_|FM5_)' | grep -vE '^(FM_WORK|FM_IMAGE|FM_GPKG_DIR|FM_GPKG_NAME|FM5_DATA|FM_DOCKER_ARGS|FM_PLUGIN_SRC|FM_SIZE|FM_TIMEOUT)=' \
        | while IFS='=' read -r name _; do printf -- '-e\n%s\n' "$name"; done
}

run() {
    # shellcheck disable=SC2086
    docker run --rm --init ${FM_DOCKER_ARGS:-} --user "$(id -u):$(id -g)" -e HOME=/tmp \
        -v "$WORK:/w" -v "$GPKG_DIR:/bd" -v "$DATA:/data" "$@"
}

cmd="${1:-}"; shift || true
case "$cmd" in
    image)
        docker build -t "$IMAGE" -f "$REPO/scripts/docker/site_videos.Dockerfile" "$REPO"
        ;;
    clip)
        sync_code
        mapfile -t extra < <(passed_env)
        for c in "$@"; do
            echo "== clip $c"
            scene="${c%-dark}"; theme=light; profile=fmvideo
            if [ "$scene" != "$c" ]; then theme=dark; profile=fmvideo-dark; fi
            seed_profile "$profile"
            run --name "fmvideo_$c" -e FILTERMATE_NO_FEEDBACK_INVITE=1 -e QGIS_PLUGINPATH=/w/plugins -e FM_VIDEO_OUT=/w/out -e FM_CLIP="$scene" \
                -e FM5_DIR=/data -e FM_GPKG="/bd/$GPKG_NAME" "${extra[@]}" -e FM_THEME="$theme" "$IMAGE" bash -c \
                "timeout ${FM_TIMEOUT:-1500} dbus-run-session -- xvfb-run -a -s '-screen 0 1920x1200x24' qgis --nologo --noversioncheck --lang en --profiles-path /w/profiles --profile $profile --code /w/scripts/site_videos.py" \
                > "$WORK/out/$c.stdout.txt" 2>&1 || echo "  clip $c ended with $?"
            grep -n 'stopped\|Traceback\|counts' "$WORK/out/$c/capture.log" | cut -c1-300 | tail -3 || true
            run -e FM_VIDEO_OUT=/w/out -e FM_SIZE="${FM_SIZE:-1920x1080}" -e FM_CRF="${FM_CRF:-23}" "$IMAGE" \
                python3 /w/scripts/site_video_render.py "$c" 2>&1 | tail -1
        done
        ;;
    publish)
        for c in "$@"; do
            cp "$WORK/out/site/$c.mp4" "$WORK/out/site/$c.webp" "$REPO/website/video/" && echo "published $c"
        done
        ;;
    sam-model)
        # The files and the runtime where the plugin looks for them: no question is asked during the recording.
        sync_code
        M="$PROFILE/filtermate/models/sam2.1-hiera-tiny-q"; mkdir -p "$M"
        base='https://huggingface.co/onnx-community/sam2.1-hiera-tiny-ONNX/resolve/814a066640debee5a91e70aa401fb8e17e030503/onnx'
        for f in vision_encoder_quantized.onnx vision_encoder_quantized.onnx_data \
                 prompt_encoder_mask_decoder_quantized.onnx prompt_encoder_mask_decoder_quantized.onnx_data; do
            [ -s "$M/$f" ] || curl -sS -L -m 600 -A 'FilterMate-QGIS-plugin' -o "$M/$f" "$base/$f"
        done
        run "$IMAGE" bash -c 'V=$(python3 -c "import sys; print(f\"py{sys.version_info[0]}{sys.version_info[1]}\")"); \
            echo "numpy==$(python3 -c "import numpy; print(numpy.__version__)")" > /tmp/c.txt; \
            python3 -m pip install -q --no-cache-dir --target /w/profiles/profiles/fmvideo/filtermate/python/$V --constraint /tmp/c.txt onnxruntime'
        ;;
    *)
        sed -n 2,36p "$0"; exit 1 ;;
esac
