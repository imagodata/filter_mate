# -*- coding: utf-8 -*-
"""The basemaps of the agent against their real servers: needs the network, asks a few tiles, sends nothing else.

Each basemap of the list is added by ``add_basemap`` and drawn over Toulouse: a layer that is valid proves nothing
(QGIS opens an XYZ layer without asking its server), an image that is not blank proves the address QGIS reads.

    docker run --rm -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_agent_basemaps_live.py'
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (  # noqa: E402
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsMapRendererSequentialJob, QgsMapSettings, QgsProject,
    QgsRectangle, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize  # noqa: E402

RESULTS = []
# Toulouse, in Web Mercator, about 5 km wide: zoom 13 or so on a 512 px image.
TOULOUSE = QgsRectangle(158000, 5400000, 163000, 5405000)


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:300]}" if not condition else ""), flush=True)


def colours(layer):
    """How many colours the layer draws over Toulouse: one means nothing came from its server."""
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    settings.setExtent(TOULOUSE)
    settings.setOutputSize(QSize(512, 512))
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    return len({image.pixel(x, y) for x in range(0, 512, 16) for y in range(0, 512, 16)})


def main():
    from filter_mate.adapters.public_api import project_control
    from filter_mate.core.agent.basemaps import BASEMAPS
    from filter_mate.core.agent.sources import make_source, platform_domains, platform_name

    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    project = QgsProject.instance()
    data = QgsVectorLayer("Point?crs=EPSG:4326", "data", "memory")
    project.addMapLayer(data)
    for basemap in BASEMAPS:
        try:
            summary = project_control.add_basemap(basemap.id)
        except ValueError as exc:
            check(f"{basemap.id}: added", False, exc)
            continue
        layer = project.mapLayer(summary["layer_id"])
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check(f"{basemap.id}: a raster of the wms provider, named by its title",
              summary["layer_kind"] == "raster" and summary["provider_type"] == "wms" and summary["name"] == basemap.title
              and layer.isValid(), summary)
        check(f"{basemap.id}: under every other layer", order[0] == data.id() and order[-1] == layer.id(), order)
        check(f"{basemap.id}: keeps its attribution", layer.metadata().rights() == [basemap.attribution],
              layer.metadata().rights())
        drawn = colours(layer)
        check(f"{basemap.id}: draws Toulouse", drawn > 1, f"{drawn} colour(s)")

    # An address the user added, written with a query as a WMTS asked by parameters: the same path as the chat.
    mine = make_source("https://data.geopf.fr/wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"
                       "&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}", "xyz")
    summary = project_control.add_basemap(platform_name(mine), name="mine", extra_domains=platform_domains([mine]))
    check("an address the user added: draws Toulouse", colours(project.mapLayer(summary["layer_id"])) > 1, summary)

    count = len(project.mapLayers())
    wrong = make_source("https://data.geopf.fr/nothing/{z}/{x}/{y}.png", "xyz")
    try:
        project_control.add_basemap(platform_name(wrong), extra_domains=platform_domains([wrong]))
        check("an address that serves no tile is refused, nothing added", False)
    except ValueError as exc:
        check("an address that serves no tile is refused, nothing added",
              len(project.mapLayers()) == count and "basemap" in str(exc), exc)
    try:
        project_control.add_basemap("https://tile.openstreetmap.org/{z}/{x}/{y}.png")
        check("an address that is not in the list is refused", False)
    except ValueError as exc:
        check("an address that is not in the list is refused", "not a basemap of the list" in str(exc), exc)

    # A server of one country has no tile for a quarter of the world: the tile of the place the map shows is asked.
    swiss = make_source("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg",
                        "xyz")
    project_control._map_place = lambda: (7.45, 46.95)  # Bern; there is no map window here
    try:
        summary = project_control.add_basemap(platform_name(swiss), extra_domains=platform_domains([swiss]))
        check("a server of one country: added when the map is over it",
              colours(project.mapLayer(summary["layer_id"])) >= 1, summary)
    except ValueError as exc:
        check("a server of one country: added when the map is over it", False, exc)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(root, "filter_mate"))
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        RESULTS.append(False)
    print(f"{RESULTS.count(True)}/{len(RESULTS)} passed", flush=True)
    os._exit(1 if RESULTS.count(False) else 0)
