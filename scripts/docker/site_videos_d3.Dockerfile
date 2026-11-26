# Additional recording environment for real D3.js code charts in QGIS 4.
# Build the base fm-video first, then:
# docker build -t fm-video-d3 -f scripts/docker/site_videos_d3.Dockerfile .
# No plugin, data, profile or API key is copied into this image.
ARG BASE_IMAGE=fm-video
FROM ${BASE_IMAGE}
USER root
RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends python3-pyqt6.qtwebengine \
    && rm -rf /var/lib/apt/lists/*
