# FilterMate in a browser: the standalone application on a virtual screen, served by noVNC.
#
# Build from the repository root, after `bash scripts/build_wheel.sh`:
#     docker build -f standalone/docker/Dockerfile -t filtermate .
# Run, then open http://localhost:6080 :
#     docker run --rm -p 127.0.0.1:6080:6080 -v "$PWD:/data" -v filtermate-home:/filtermate filtermate
#
# QGIS_TAG chooses the QGIS of the image: ltr (Qt5), latest (Qt6), or a release-x_y tag.
ARG QGIS_TAG=ltr
FROM qgis/qgis:${QGIS_TAG}

LABEL org.opencontainers.image.title="FilterMate" \
      org.opencontainers.image.description="FilterMate, the dock of the QGIS plugin in an application of its own, in a browser" \
      org.opencontainers.image.source="https://github.com/imagodata/filter_mate" \
      org.opencontainers.image.licenses="GPL-3.0-or-later"

# TigerVNC: the X server and the VNC server in one process. noVNC + websockify: the browser side.
# openbox: a window manager, so that dialogs and floating panels can be moved as on a desktop.
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        tigervnc-standalone-server tigervnc-tools novnc websockify openbox xauth fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# A virtual environment that sees the system's packages: PyQGIS comes from the image, FilterMate from the wheel.
COPY dist/filtermate-*.whl /tmp/wheel/
RUN python3 -m venv --system-site-packages /opt/filtermate \
 && /opt/filtermate/bin/pip install --no-cache-dir --no-deps /tmp/wheel/filtermate-*.whl \
 && rm -rf /tmp/wheel \
 && /opt/filtermate/bin/filtermate version

COPY standalone/docker/start.sh /usr/local/bin/filtermate-web
RUN chmod 755 /usr/local/bin/filtermate-web \
 && ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html 2>/dev/null || true

ENV FILTERMATE_HOME=/filtermate \
    FILTERMATE_SIZE=1600x1000 \
    PATH=/opt/filtermate/bin:$PATH
VOLUME ["/filtermate"]
WORKDIR /data
EXPOSE 6080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6080/vnc.html', timeout=4)" || exit 1

ENTRYPOINT ["/usr/local/bin/filtermate-web"]
