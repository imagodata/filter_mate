#!/usr/bin/env bash
# Record and edit the website videos from WSL, with the Windows QGIS 4.2.
#
#   scripts/site_videos.sh clip hero explore ...   record (scripts/site_videos.py), one QGIS per clip
#   scripts/site_videos.sh render hero explore ... edit (scripts/site_video_render.py) into MP4 + WebP poster
#   scripts/site_videos.sh publish hero ...        copy the edited MP4 / WebP into website/video/
#   scripts/site_videos.sh all hero ...            clip, render and publish
#   scripts/site_videos.sh data                    Estavar data of the raster / point cloud clips (FM_LIDAR_TILES:
#                                                  folder with the LiDAR HD tiles 0617_6152 and 0617_6153)
#
# A clip name ending in -dark (hero-dark) is the dark version: QGIS with the Night Mapping theme,
# published as video/<clip>-dark.mp4 / .webp; fm.js picks it when the site is dark.
#
# QGIS runs with its own profile (fm_video\profiles) and a copy of this checkout as the plugin
# (fm_video\plugins\filter_mate), so neither the user's profile nor their installed FilterMate
# is touched. A clip only waits for another recording, not for the user's own QGIS.
#
# Environment: FM_QGIS (QGIS install), FM_GPKG (BD TOPO 31 GeoPackage), FM5_DATA / FM5_GPKG /
# FM5_TILE (Estavar DTM, vectors and LiDAR HD for the raster / point cloud clips),
# FM_FFMPEG (ffmpeg.exe, Windows path), FM_PLUGIN_SRC (checkout used as the plugin, default: this one).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
QGIS="${FM_QGIS:-C:\\Program Files\\QGIS 4.2.3}"
WIN_TEMP="$(cmd.exe /c 'echo %LOCALAPPDATA%' 2>/dev/null | tr -d '\r')\\Temp"
W="$WIN_TEMP\\fm_video"
W_LINUX="$(wslpath -u "$W")"
FFMPEG_DEFAULT="$(find "$(wslpath -u "$WIN_TEMP\\..")/Microsoft/WinGet/Packages" -maxdepth 4 -name ffmpeg.exe 2>/dev/null | head -1)"
FFMPEG="${FM_FFMPEG:-$( [ -n "$FFMPEG_DEFAULT" ] && wslpath -w "$FFMPEG_DEFAULT" )}"

mkdir -p "$W_LINUX/scripts" "$W_LINUX/plugins" "$W_LINUX/profiles" "$W_LINUX/site"

sync_code() {
    cp "$REPO/scripts/site_videos.py" "$REPO/scripts/site_video_render.py" "$W_LINUX/scripts/"
    [ -f "$REPO/scripts/site_stills.json" ] && cp "$REPO/scripts/site_stills.json" "$W_LINUX/scripts/"
    rsync -a --delete \
        --exclude .git --exclude .github --exclude .claude --exclude .serena --exclude _bmad --exclude _bmad-output \
        --exclude tests --exclude website --exclude docs --exclude scripts --exclude knowledge --exclude logs \
        --exclude __pycache__ --exclude '*.pyc' --exclude dist --exclude build \
        "${FM_PLUGIN_SRC:-$REPO}/" "$W_LINUX/plugins/filter_mate/"
}

seed_profile() {
    # A new profile stops on QGIS's first-run dialog before --code runs: start from settings that
    # went through it, with FilterMate enabled and its welcome dialog dismissed.
    # fmvideo-dark has the Night Mapping theme (FilterMate follows the QGIS palette).
    local profile="$1" ini="$W_LINUX/profiles/profiles/$1/QGIS/QGIS4.ini"
    [ -f "$ini" ] && return
    mkdir -p "$(dirname "$ini")"
    printf '%s\r\n' '[Processing]' 'hasPortedOldLog=true' '' '[PythonPlugins]' 'db_manager=true' 'processing=true' \
        'MetaSearch=true' 'grassprovider=true' 'filter_mate=true' '' '[qgis]' 'style=fusion' 'toolbarIconSize=24' \
        '' '[authentication]' 'using-generated-random-password=true' '' '[rendering]' 'main-canvas-preview-jobs=true' \
        '' '[elevation-profile]' 'show-layer-tree=true' '' '[FilterMate]' 'discord_welcome_dismissed=true' '' \
        '[locale]' 'userLocale=en' > "$ini"
    if [ "$profile" = fmvideo-dark ]; then printf '%s\r\n' '' '[UI]' 'UITheme=Night Mapping' >> "$ini"; fi
}

write_bats() {
    cat > "$W_LINUX/clip.bat" <<EOF
@echo off
call "$QGIS\\bin\\o4w_env.bat"
call "$QGIS\\bin\\qt6_env.bat" 2>nul
path %OSGEO4W_ROOT%\\apps\\qgis\\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\\=/%/apps/qgis
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\\apps\\qgis\\qtplugins;%OSGEO4W_ROOT%\\apps\\Qt6\\plugins
set QGIS_PLUGINPATH=$W\\plugins
set FM_VIDEO_OUT=$W
set FM_CLIP=%1
set FM_THEME=%2
cd /d "$W"
"%OSGEO4W_ROOT%\\bin\\qgis-bin.exe" --nologo --noversioncheck --lang en --profiles-path "$W\\profiles" --profile %3 --code "$W\\scripts\\site_videos.py" > "$W\\%1-%2.stdout.txt" 2>&1
EOF
    cat > "$W_LINUX/render.bat" <<EOF
@echo off
call "$QGIS\\bin\\o4w_env.bat"
set FM_VIDEO_OUT=$W
set FM_FFMPEG=$FFMPEG
cd /d "$W"
python "$W\\scripts\\site_video_render.py" %*
EOF
}

recording_running() {
    # Only another recording is waited for: it has its own profile, so the user's QGIS can stay open.
    powershell.exe -NoProfile -Command \
        "@(Get-CimInstance Win32_Process -Filter \"Name='qgis-bin.exe'\" | Where-Object { \$_.CommandLine -like '*fm_video*' }).Count" \
        2>/dev/null | tr -d '\r' | grep -qv '^0$'
}

wait_qgis_idle() {
    while recording_running; do echo "  another recording runs, waiting..."; sleep 20; done
}

# Pass FM_* / FM5_* variables of this shell to the Windows QGIS.
export WSLENV="${WSLENV:-}:FM_GPKG/w:FM5_DATA/w:FM5_GPKG/w:FM5_TILE/w:FM_TAKE"
for v in FM_GPKG FM5_DATA FM5_GPKG FM5_TILE; do [ -n "${!v:-}" ] || unset "$v"; done

cmd="${1:-}"; shift || true
case "$cmd" in
    clip|all)
        sync_code; write_bats; seed_profile fmvideo; seed_profile fmvideo-dark
        for c in "$@"; do
            # "<clip>-dark" records the dark version (Night Mapping profile)
            name="${c%-dark}"; theme=light; profile=fmvideo
            [ "$name" != "$c" ] && { theme=dark; profile=fmvideo-dark; }
            wait_qgis_idle
            echo "== clip $c"
            (cd "$W_LINUX" && timeout 1500 cmd.exe /c clip.bat "$name" "$theme" "$profile") || echo "  clip $c ended with $?"
            tail -3 "$W_LINUX/$c/capture.log" 2>/dev/null || true
        done
        [ "$cmd" = all ] || exit 0
        ;;&
    render|all)
        sync_code; write_bats
        (cd "$W_LINUX" && cmd.exe /c render.bat "$@")
        [ "$cmd" = all ] || exit 0
        ;;&
    publish|all)
        for c in "$@"; do
            cp "$W_LINUX/site/$c.mp4" "$W_LINUX/site/$c.webp" "$REPO/website/video/"
            echo "published $c ($(du -h "$REPO/website/video/$c.mp4" | cut -f1))"
        done
        # step images of the stories (site_stills.json / still() marks)
        if [ -d "$W_LINUX/site/stills" ] && ls "$W_LINUX/site/stills/"*.webp >/dev/null 2>&1; then
            mkdir -p "$REPO/website/img/stories"
            cp "$W_LINUX/site/stills/"*.webp "$REPO/website/img/stories/"
            echo "published $(ls "$W_LINUX/site/stills/"*.webp | wc -l) story images"
        fi
        ;;
    data)
        # One square kilometre of the village of Estavar (west of it lies Llívia, a Spanish enclave without French cadastre): LiDAR HD (IGN, COPC) cropped and merged with PDAL, DTM from its
        # ground points, slope in percent, BD TOPO from the IGN WFS, Etalab cadastre of the commune (66072).
        tiles="${FM_LIDAR_TILES:?folder of LHD_FXX_0617_6152 / 0617_6153 .copc.laz}"
        tiles_w="$(wslpath -w "$tiles")"
        D="$W_LINUX/data"; mkdir -p "$D"; cd "$D"
        curl -sSL "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/communes/66072/geojson/parcelles" | gunzip > parcelles.json
        for t in batiment troncon_de_route troncon_hydrographique; do
            curl -sSL -o "bdtopo_$t.json" "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:$t&SRSNAME=EPSG:2154&BBOX=616800,6151900,618200,6153300,EPSG:2154&COUNT=5000&outputFormat=application/json"
        done
        bounds='([617000,618000],[6152100,6153100])'
        cat > crop.json <<EOF2
{"pipeline":[
 {"type":"readers.copc","filename":"${tiles_w//\\/\\\\}\\\\LHD_FXX_0617_6152_PTS_C_LAMB93_IGN69.copc.laz","bounds":"$bounds"},
 {"type":"readers.copc","filename":"${tiles_w//\\/\\\\}\\\\LHD_FXX_0617_6153_PTS_C_LAMB93_IGN69.copc.laz","bounds":"$bounds"},
 {"type":"filters.merge"}, {"type":"filters.crop","bounds":"$bounds"},
 {"type":"writers.copc","filename":"estavar_village.copc.laz","a_srs":"EPSG:2154"}]}
EOF2
        cat > dtm.json <<'EOF2'
{"pipeline":[
 {"type":"readers.copc","filename":"estavar_village.copc.laz"},
 {"type":"filters.range","limits":"Classification[2:2]"},
 {"type":"writers.gdal","filename":"mnt_village.tif","resolution":1,"output_type":"idw","window_size":12,"nodata":-9999,
  "data_type":"float32","origin_x":617000,"origin_y":6152100,"width":1000,"height":1000,"gdalopts":"COMPRESS=DEFLATE,TILED=YES"}]}
EOF2
        printf '%s\r\n' '@echo off' "call \"$QGIS\\bin\\o4w_env.bat\"" 'cd /d %~dp0' \
            'pdal pipeline crop.json || exit /b 1' 'pdal pipeline dtm.json || exit /b 1' \
            'gdaldem slope -p -compute_edges mnt_village.tif pente_village.tif -co COMPRESS=DEFLATE' \
            'del estavar.gpkg 2>nul' \
            'ogr2ogr -f GPKG estavar.gpkg bdtopo_batiment.json -nln batiment -a_srs EPSG:2154' \
            'ogr2ogr -f GPKG -update estavar.gpkg bdtopo_troncon_de_route.json -nln troncon_de_route -a_srs EPSG:2154' \
            'ogr2ogr -f GPKG -update estavar.gpkg bdtopo_troncon_hydrographique.json -nln troncon_hydrographique -a_srs EPSG:2154' \
            'ogr2ogr -f GPKG -update estavar.gpkg parcelles.json -nln parcelle -t_srs EPSG:2154' > prep.bat
        cmd.exe /c prep.bat
        ;;
    *)
        sed -n 2,18p "$0"; exit 1 ;;
esac
