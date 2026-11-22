# FilterMate without the QGIS application

The standalone application opens the dock of the plugin, **unchanged**, in a window of its own:
a map, the layer panel of QGIS, its message bar, and the QGIS libraries as the engine. Every
section works as in QGIS (EXPLORING, FILTERING, EXPORTING, AGENT, CONFIGURATION, favorites,
history, undo), on the same providers (GeoPackage, Shapefile, PostGIS, SpatiaLite, WFS, rasters,
point clouds...).

It is for a machine where QGIS is not wanted as a desktop application, for a user who only
filters and exports, for a server reached from a browser, and for scripts that need the dock.

## Install

In one line, with nothing but Python 3.9 or later (the script installs pipx for you when it is
missing, then the package, then runs `filtermate doctor`; no administrator rights):

```bash
curl -LsSf https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.sh | sh   # macOS, Linux
```

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/imagodata/filter_mate/main/standalone/install.ps1 | iex"
```

The package comes from the zip of `main` on GitHub: git is not needed. Checked: `install.sh` as a plain
user in `qgis/qgis:ltr`, in `qgis/qgis:latest` without git (QGIS found, `check_standalone.py` 42/42) and
in `python:3.12-slim` (no QGIS: `filtermate setup` offered); `install.ps1` on Windows 11 (QGIS 4.2 found,
42/42). Or by hand:

```bash
pipx install https://github.com/imagodata/filter_mate/archive/refs/heads/main.zip   # an isolated install of the command
# or, in any Python 3.9 or later:
pip install "git+https://github.com/imagodata/filter_mate"
```

From a checkout: `bash scripts/build_wheel.sh`, then `pipx install dist/filtermate-<version>-py3-none-any.whl`.

The package needs nothing from PyPI: the command is written with the standard library only.

## Start

```bash
filtermate                                 # an empty map
filtermate parcels.gpkg dem.tif cloud.laz  # data files (every table of a GeoPackage)
filtermate --project town.qgz              # a QGIS project
filtermate --lang fr --basemap             # in French, over the OpenStreetMap tiles
filtermate --help                          # every option
```

Layers are also added from **Layer > Add layers** (the source screens of QGIS: files, GeoPackage,
SpatiaLite, PostgreSQL, WMS/WMTS, WFS/OGC API, XYZ, vector tiles, delimited text, virtual layers,
ArcGIS REST, STAC...), from **View > Panels > Browser**, or by dropping files on the window.

## The engine

FilterMate runs on the QGIS libraries, PyQGIS 3.22 to 4.x (Qt5 or Qt6). They are not on PyPI.
`filtermate` looks for them, in this order, and remembers what it found (`--refresh` searches
again):

1. the Python named by `FILTERMATE_QGIS_PYTHON` (or `--runtime PYTHON`);
2. the Python that runs the command, when it has PyQGIS (a conda environment with `qgis`, the
   Python of a QGIS install);
3. the runtime installed by `filtermate setup`;
4. the QGIS installs of the machine, the newest first: `python-qgis*.bat` of OSGeo4W and of the
   installers on Windows, the system Python on Linux (the `qgis` packages of the distributions),
   `QGIS*.app` on macOS, the conda environments listed in `~/.conda/environments.txt`.

Each candidate is started once to check that it imports `qgis.gui`; a wrong guess costs a second.
The other Python gets the files to open and the options through its environment, never through
its command line: the `python-qgis.bat` of Windows hands that line to cmd.exe, which would read
`&` or `%` in a file name. Variables that point into the environment of the command itself (its
virtual environment, an active conda environment) are not passed on.

```bash
filtermate doctor          # what was found, what FilterMate starts with
filtermate doctor --json   # the same, for a script
```

### A runtime of its own

On a machine with no QGIS:

```bash
filtermate setup           # asks, then installs QGIS from conda-forge (0.8 GB to download, 4.5 GB on disk)
filtermate setup --remove  # deletes it
```

The runtime goes in the folder of the application, without administrator rights: micromamba
(one file, checked against its published SHA-256) creates a conda-forge environment holding
QGIS 4.2 or later. A stalled download is tried again three times; what was downloaded is kept
for the next attempt. `setup` and `setup --remove` touch only a `runtime/` folder that `setup`
made (it leaves a marker there). On Windows the package cache goes in `%LOCALAPPDATA%\fmpk` (a short
path: Windows limits paths to 260 characters unless long paths are on, and the deepest files of QGIS
pass that limit in micromamba's cache), emptied after the install. Checked from a bare Linux machine
(a `python:3.12-slim` container) and on Windows 11 (long paths off); not on macOS, which nobody here
has (the GitHub workflow `standalone.yml` that would run it on a Mac is turned off, as every workflow).
What was checked for macOS from Linux: conda-forge solves the same environment for `osx-arm64` and
`osx-64` (QGIS 4.2.3, draco 1.5.7), micromamba has a build for both, and the `qgis` package of macOS
puts PyQGIS where the runtime expects it (`share/qgis/python`), its activation script setting the same
variables as `filtermate setup` does.

When the QGIS chosen at an earlier launch is gone (uninstalled, an environment deleted), the
next launch says so and searches again. A Python named with `FILTERMATE_QGIS_PYTHON` or
`--runtime` that does not start is reported, never replaced by another QGIS.

## Where things are kept

Everything goes in one folder, which `FILTERMATE_HOME` moves:

| System | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\FilterMate` |
| macOS | `~/Library/Application Support/FilterMate` |
| Linux | `~/.local/share/filtermate` (`$XDG_DATA_HOME`) |

`profile/` is the QGIS profile of the application (its settings, its authentication database
where the agent keeps API keys, FilterMate's `config.json`, favorites and history), `logs/` the
log of FilterMate, `runtime/` the runtime of `filtermate setup`. No QGIS profile of yours is read
or written: favorites and settings of the plugin in QGIS stay apart.

## In a browser (Docker)

The image runs the application on a virtual screen and serves it with noVNC:

```bash
bash scripts/build_wheel.sh
docker build -f standalone/docker/Dockerfile -t filtermate .                       # QGIS LTR (Qt5)
docker build -f standalone/docker/Dockerfile --build-arg QGIS_TAG=latest -t filtermate:qt6 .

docker run --rm -p 127.0.0.1:6080:6080 -v "$PWD:/data" -v filtermate-home:/filtermate filtermate
# then open http://localhost:6080/vnc.html?autoconnect=1&resize=scale
```

- `/data` is the working folder: `docker run ... filtermate --project town.qgz` opens `/data/town.qgz`.
- `/filtermate` keeps the profile from one run to the next.
- `FILTERMATE_SIZE` (default `1600x1000`) is the size of the screen; `FILTERMATE_PASSWORD` asks a
  password in the browser. Without it, publish the port on `127.0.0.1` only, or behind a proxy that
  authenticates: whoever reaches the page uses the application.
- The container ends when the application is closed.

## Automation

The host takes `--offscreen` (no window: servers, continuous integration) and `--code FILE`
(a Python file run once the window is up, as `qgis --code`). The public API of the plugin is
there as in QGIS:

```python
import qgis.utils
api = qgis.utils.plugins["filter_mate"].get_public_api()
api.apply_filter("parcels", "\"surface\" > 1000", "my-script")
```

`tests/qgis_headless/check_standalone.py` is a complete example.

## What differs from QGIS

- One map, one layer panel; no print layouts, no editing toolbar, no Processing toolbox window
  (the algorithms run: the agent and the automation use them). **Layer > Save layer edits** saves
  what the agent edited; leaving, opening another project or closing the window asks first, as
  QGIS does, and so do running tasks (an export cut short would leave a partial file).
- Other QGIS plugins are not loaded: the extensions of FilterMate that need one (QFieldCloud needs
  QFieldSync, favorites sharing needs Resource Sharing) say once that they are off (their message
  says to restart QGIS: it is written for the plugin).
- Each plugin menu sits in the menu bar instead of under Vector.
- On Windows, the console the command was started from stays open while the application runs.

## For contributors

- `standalone/cli.py`, `runtime.py`, `provision.py`, `paths.py`: the command, standard library only
  (a unit test checks the imports).
- `standalone/host/`: the window (`window.py`), the `iface` it gives the plugin (`interface.py`),
  the map tools QGIS has and the libraries do not (`map_tools.py`), the source screens
  (`sources.py`), the start and the end (`app.py`). The plugin does not import any of it.
- `tests/unit/standalone/`: the launcher, the runtime install, and a scan of the plugin that fails
  when it calls a method of `iface` the window lacks.
- In a real QGIS (Docker, as the other benches):

```bash
docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash -c \
  'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm >/dev/null 2>&1; cp -r /src /tmp/copy; \
   FM_FIXTURES=/tmp/fm FILTERMATE_HOME=/tmp/fmhome python3 /tmp/copy/standalone/_bootstrap.py \
   --offscreen --size 1600x1000 --code /tmp/copy/tests/qgis_headless/check_standalone.py'
```

  The GUI smoke of the plugin runs in the window with
  `python3 standalone/_bootstrap.py --no-plugin --size 1600x1000 --code tests/qgis_headless/run_gui_smoke.py`
  under `xvfb-run` (see the skill `qgis-headless-bench`).

## Publishing on PyPI

`bash scripts/publish_pypi.sh --dry-run` builds the wheel and the source archive from the tracked
files and checks them with twine. With an API token of the PyPI account,
`PYPI_TOKEN=pypi-... bash scripts/publish_pypi.sh` uploads them (`--test` for test.pypi.org); the
version is the plugin's, in `metadata.txt`. Once published, the install is `pipx install filtermate`.
