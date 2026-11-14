# QGIS stable (a release build: the nightly one pushes Qt warnings in the message bar) with what the recordings of
# scripts/site_videos.py need: ffmpeg for scripts/site_video_render.py, fonts for the symbols of the dock, and a
# recent pdal (the height above ground and the clip of a point cloud).
#   docker build -t fm-video -f scripts/docker/site_videos.Dockerfile .
FROM qgis/qgis:stable
RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        ffmpeg fonts-dejavu-core fonts-noto-color-emoji fonts-symbola \
    && rm -rf /var/lib/apt/lists/* && fc-cache -f
COPY tests/qgis_headless/install_pdal.sh /tmp/install_pdal.sh
RUN bash /tmp/install_pdal.sh
