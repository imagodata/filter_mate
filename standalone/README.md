# FilterMate, as an application of its own

FilterMate explores, filters and exports vector, raster and point-cloud layers. It is a QGIS
plugin; this package starts **the same dock, unchanged, in a window of its own**: a map, a
layer panel, and the QGIS libraries as the engine. The QGIS application is not needed, and
no QGIS profile of yours is read or written.

```bash
pipx install filtermate        # or: pip install filtermate
filtermate                     # the application
filtermate parcels.gpkg dem.tif
filtermate --project town.qgz
```

## The engine

FilterMate runs on the QGIS libraries (PyQGIS 3.22 to 4.x, Qt5 or Qt6). They are not on PyPI,
so the `filtermate` command looks for them, in this order:

1. the Python named by `FILTERMATE_QGIS_PYTHON` (or `--runtime`);
2. the Python that runs the command, when it already has PyQGIS;
3. a runtime installed by `filtermate setup`;
4. the QGIS installs of the machine (OSGeo4W and the installers on Windows, the system Python
   on Linux, `QGIS.app` on macOS, conda environments), the newest first.

On a machine with none of them:

```bash
filtermate setup     # downloads QGIS from conda-forge into the application folder, no administrator rights
filtermate doctor    # says what was found, and what FilterMate starts with
```

`filtermate setup --remove` deletes that runtime. `FILTERMATE_HOME` moves the application
folder (settings, logs, the runtime).

## In a browser

The Docker image serves the same window over the web (noVNC), for a server or a machine where
nothing can be installed. See `docs/STANDALONE.md` in the repository.

## More

Options: `filtermate --help`. Guide, sources and issues:
<https://github.com/imagodata/filter_mate>. License: GPL-3.0-or-later.
