# =============================================================================
# FilterMate Video Automation — Headless QGIS + Frame Capture
# =============================================================================
# Runs QGIS in a virtual framebuffer (Xvfb), captures frames via scrot/import,
# and assembles final video with FFmpeg. No OBS required.
#
# Build:
#   docker build -t filtermate-video .
#
# Run:
#   docker run --rm -v $(pwd)/output:/app/output filtermate-video --all --video v01
# =============================================================================

FROM qgis/qgis:release-3_36

LABEL maintainer="FilterMate Team"
LABEL description="Headless QGIS + FFmpeg frame capture for video automation"

# Avoid interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Virtual framebuffer
    xvfb \
    # Window management in Xvfb
    xdotool \
    wmctrl \
    openbox \
    # Screenshot capture
    scrot \
    imagemagick \
    # Video encoding
    ffmpeg \
    # Python build deps
    python3-pip \
    python3-dev \
    # X11 libs for PyAutoGUI
    python3-tk \
    python3-xlib \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    # Fonts for UI rendering
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-core \
    # Misc
    dbus-x11 \
    at-spi2-core \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ── Python packages ──────────────────────────────────────────────────────────
COPY requirements-docker.txt /tmp/requirements-docker.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-docker.txt \
    && rm /tmp/requirements-docker.txt

# ── Playwright for diagram rendering (optional) ─────────────────────────────
RUN pip3 install --no-cache-dir --break-system-packages playwright \
    && python3 -m playwright install --with-deps chromium \
    || echo "Playwright install failed (optional — diagrams will be HTML only)"

# ── Xvfb configuration ──────────────────────────────────────────────────────
ENV DISPLAY=:99
ENV RESOLUTION=1920x1080x24
ENV QGIS_PREFIX_PATH=/usr
ENV QT_QPA_PLATFORM=xcb

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app
COPY . /app/

# ── FilterMate plugin mount point ────────────────────────────────────────────
# Mount the plugin at runtime:
#   -v /path/to/filter_mate:/root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/filter_mate
VOLUME ["/root/.local/share/QGIS/QGIS3/profiles/default/python/plugins"]
VOLUME ["/app/output"]

# ── Entrypoint ───────────────────────────────────────────────────────────────
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]
