#!/bin/bash
# Install a recent pdal command line tool from conda-forge, inside a qgis/qgis container.
#
# No QGIS Docker image ships a pdal recent enough for FilterMate (writers.copc
# needs PDAL 2.4; release-3_* have 2.3, the others none) and Ubuntu 24.04 /
# 25.10 and Debian 13 have no pdal package. The images have no curl nor bzip2:
# micromamba is fetched with Python.
#
# Usage: bash install_pdal.sh [prefix]   (default /opt/pdal; pdal ends up on PATH)
set -euo pipefail
PREFIX="${1:-/opt/pdal}"
python3 - <<'EOF'
import io
import tarfile
import urllib.request

data = urllib.request.urlopen('https://micro.mamba.pm/api/micromamba/linux-64/latest', timeout=300).read()
archive = tarfile.open(fileobj=io.BytesIO(data), mode='r:bz2')
options = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
archive.extract('bin/micromamba', '/tmp', **options)
EOF
/tmp/bin/micromamba create --yes --quiet --prefix "$PREFIX" --channel conda-forge pdal > /dev/null
printf '#!/bin/sh\nexec %s/bin/pdal "$@"\n' "$PREFIX" > /usr/local/bin/pdal
chmod +x /usr/local/bin/pdal
pdal --version | sed -n 2p
