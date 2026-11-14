# -*- coding: utf-8 -*-
"""WMS and WMTS services of the agent: their capabilities read, a layer added and drawn. Needs the network.

Two documents written here check the reading (nested layers, inherited CRS, links that are no endpoint, a service
that sends its requests elsewhere); then the IGN Géoplateforme is asked for real, and each layer added is drawn over
Toulouse: a layer that is valid proves little, an image that is not blank proves the source QGIS reads.

    docker run --rm -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy; cp -r /src/. /tmp/copy; python3 /tmp/copy/tests/qgis_headless/check_agent_image_services_live.py'
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
TOULOUSE = QgsRectangle(158000, 5400000, 163000, 5405000)  # Web Mercator, about 5 km wide

WMS = b"""<?xml version="1.0"?>
<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms" xmlns:xlink="http://www.w3.org/1999/xlink">
 <Service><Name>WMS</Name><OnlineResource xlink:href="https://elsewhere.example.org/about"/></Service>
 <Capability>
  <Request>
   <GetCapabilities><Format>text/xml</Format><DCPType><HTTP><Get>
     <OnlineResource xlink:href="https://maps.example.org/wms?"/></Get></HTTP></DCPType></GetCapabilities>
   <GetMap><Format>image/jpeg</Format><Format>image/png</Format><DCPType><HTTP><Get>
     <OnlineResource xlink:href="https://maps.example.org/wms?"/></Get></HTTP></DCPType></GetMap>
  </Request>
  <Layer><Title>Everything</Title><CRS>EPSG:4326</CRS><CRS>EPSG:2154</CRS>
   <Layer queryable="1"><Name>relief</Name><Title>Relief &amp; ombrage</Title><Abstract>Le relief</Abstract>
    <CRS>EPSG:3857</CRS>
    <Attribution><OnlineResource xlink:href="https://agency.example.com/"/></Attribution>
    <Style><Name>grey</Name><LegendURL><OnlineResource xlink:href="https://legends.example.net/a.png"/></LegendURL></Style>
    <Style><Name>colour</Name></Style>
    <Layer><Name>relief_detail</Name><Title>Detail</Title></Layer>
   </Layer>
   <Layer><Title>A folder with no name</Title><Layer><Name>roads</Name><Title>Roads</Title></Layer></Layer>
  </Layer>
 </Capability>
</WMS_Capabilities>"""

WMTS = b"""<?xml version="1.0"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
  xmlns:xlink="http://www.w3.org/1999/xlink" version="1.0.0">
 <ows:ServiceProvider><ows:ProviderSite xlink:href="https://agency.example.com"/></ows:ServiceProvider>
 <ows:OperationsMetadata><ows:Operation name="GetTile"><ows:DCP><ows:HTTP>
   <ows:Get xlink:href="https://maps.example.org/wmts?"/></ows:HTTP></ows:DCP></ows:Operation></ows:OperationsMetadata>
 <Contents>
  <Layer><ows:Title>Photos 2020</ows:Title><ows:Abstract>Aerial photographs</ows:Abstract>
   <ows:Identifier>PHOTOS.2020</ows:Identifier>
   <Style isDefault="true"><ows:Identifier>normal</ows:Identifier><LegendURL xlink:href="https://legends.example.net/a.png"/></Style>
   <Format>image/jpeg</Format>
   <TileMatrixSetLink><TileMatrixSet>LAMB93</TileMatrixSet></TileMatrixSetLink>
   <TileMatrixSetLink><TileMatrixSet>PM</TileMatrixSet></TileMatrixSetLink>
  </Layer>
  <TileMatrixSet><ows:Identifier>PM</ows:Identifier><ows:SupportedCRS>urn:ogc:def:crs:EPSG::3857</ows:SupportedCRS>
   <TileMatrix><ows:Identifier>0</ows:Identifier></TileMatrix></TileMatrixSet>
  <TileMatrixSet><ows:Identifier>LAMB93</ows:Identifier><ows:SupportedCRS>EPSG:2154</ows:SupportedCRS></TileMatrixSet>
 </Contents>
</Capabilities>"""


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""), flush=True)


def colours(layer):
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


def refused(call, words):
    try:
        call()
    except ValueError as exc:
        return words in str(exc), exc
    return False, "not refused"


def main():
    from filter_mate.adapters.agent.bounded_http import BoundedReply
    from filter_mate.adapters.public_api import image_catalog, project_control

    print(f"QGIS {Qgis.QGIS_VERSION}", flush=True)
    layers, endpoints = image_catalog.parse_wms(WMS)
    by_name = {layer["name"]: layer for layer in layers}
    check("WMS: the named layers, the folders left out", sorted(by_name) == ["relief", "relief_detail", "roads"], by_name)
    check("WMS: a layer inherits the CRS of those that hold it",
          image_catalog.offered_crs(by_name["relief_detail"]) == ["EPSG:4326", "EPSG:2154", "EPSG:3857"]
          and image_catalog.offered_crs(by_name["roads"]) == ["EPSG:4326", "EPSG:2154"], by_name)
    check("WMS: title, abstract, styles, formats", by_name["relief"]["title"] == "Relief & ombrage"
          and by_name["relief"]["abstract"] == "Le relief" and by_name["relief"]["styles"] == ["grey", "colour"]
          and by_name["relief"]["formats"] == ["image/jpeg", "image/png"] and by_name["relief_detail"]["styles"] == [],
          by_name["relief"])
    check("WMS: only the addresses of the requests are endpoints", endpoints == ["https://maps.example.org/wms?"] * 2, endpoints)
    base = "https://maps.example.org/wms"
    stay = {"IgnoreGetMapUrl": "1", "IgnoreGetFeatureInfoUrl": "1"}
    check("WMS: the CRS of the project when the layer has it (whatever its case), PNG first, the first style",
          image_catalog.source_parameters("wms", base, by_name["relief"], "epsg:2154")
          == dict(stay, crs="EPSG:2154", format="image/png", layers="relief", styles="grey", url=base))
    layers, _ = image_catalog.parse_wms(WMS, base)
    check("WMS: a layer whose legend is on another host is marked",
          {layer["name"]: layer["foreign"] for layer in layers} == {"relief": True, "relief_detail": False, "roads": False}, layers)
    many = WMS.replace(b"<CRS>EPSG:4326</CRS>", b"<CRS>" + b" ".join(b"EPSG:%d" % code for code in range(20000, 60000)) + b"</CRS>")
    import time
    started = time.time()
    crowded = image_catalog.parse_wms(many)[0]
    check("WMS: 40 000 CRS on the root layer are read at once, and copied to no layer",
          time.time() - started < 1.5 and len(image_catalog.offered_crs(crowded[0])) > 40000
          and all(len(layer["crs"]) <= 1 for layer in crowded), time.time() - started)
    hidden = WMS.replace(b'xmlns:xlink="http://www.w3.org/1999/xlink"', b'xmlns:x="http://www.w3.org/1999/xlink" xmlns:xlink="urn:other"') \
        .replace(b'<GetMap><Format>image/jpeg</Format><Format>image/png</Format><DCPType><HTTP><Get>\n     <OnlineResource xlink:href="https://maps.example.org/wms?"/>',
                 b'<GetMap><Format>image/png</Format><DCPType><HTTP><Get>\n     <OnlineResource x:href="https://maps.example.org/wms?" xlink:href="http://127.0.0.1:8001/internal?"/>')
    check("WMS: a document that shows one address to XML and another to QGIS is refused",
          hidden != WMS and refused(lambda: image_catalog.parse_wms(hidden), "cannot be trusted")[0])
    check("WMS: else Web Mercator, then longitude and latitude",
          image_catalog.source_parameters("wms", base, by_name["relief"], "EPSG:32631")["crs"] == "EPSG:3857"
          and image_catalog.source_parameters("wms", base, by_name["roads"], "EPSG:32631")["crs"] == "EPSG:4326")

    layers, endpoints = image_catalog.parse_wmts(WMTS)
    check("WMTS: the layer, its style, its format and the CRS of its tile matrix sets",
          layers == [{"name": "PHOTOS.2020", "title": "Photos 2020", "abstract": "Aerial photographs", "styles": ["normal"],
                      "formats": ["image/jpeg"], "sets": ["LAMB93", "PM"], "foreign": False, "default_style": "normal",
                      "crs": {"LAMB93": "EPSG:2154", "PM": "EPSG:3857"}}], layers)
    check("WMTS: a layer whose legend, tiles or feature information are on another host is marked",
          image_catalog.parse_wmts(WMTS, "https://maps.example.org/wmts")[0][0]["foreign"] is True
          and image_catalog.parse_wmts(WMTS.replace(b"legends.example.net", b"maps.example.org"),
                                       "https://maps.example.org/wmts")[0][0]["foreign"] is False
          and image_catalog.parse_wmts(WMTS.replace(b"legends.example.net", b"maps.example.org").replace(
              b"<Format>image/jpeg</Format>", b'<Format>image/jpeg</Format><ResourceURL resourceType="FeatureInfo" '
              b'template="https://10.0.0.3/{TileMatrix}/{TileRow}/{TileCol}"/>'), "https://maps.example.org/wmts")[0][0]["foreign"] is True)
    check("WMTS: only the addresses of the requests are endpoints", endpoints == ["https://maps.example.org/wmts?"], endpoints)
    wmts = "https://maps.example.org/wmts"
    check("WMTS: the tile matrix set of the CRS of the project, else Web Mercator",
          image_catalog.source_parameters("wmts", wmts, layers[0], "EPSG:2154")["tileMatrixSet"] == "LAMB93"
          and image_catalog.source_parameters("wmts", wmts, layers[0], "EPSG:4326") == dict(
              stay, crs="EPSG:3857", format="image/jpeg", layers="PHOTOS.2020", styles="normal",
              tileMatrixSet="PM", url=wmts + "?SERVICE=WMTS&REQUEST=GetCapabilities"))

    real_fetch = image_catalog.fetch
    for kind, document, there in (("wms", WMS, "https://maps.example.org/wms"), ("wmts", WMTS, "https://maps.example.org/wmts")):
        image_catalog.fetch = lambda url, **options: BoundedReply(200, {}, document)
        found = image_catalog.search(kind, there, "PHOTOS relief", 5) + image_catalog.search(kind, there, "photos", 5) \
            + image_catalog.search(kind, there, "relief", 5)
        check(f"{kind}: searched by every word, without case", [item["resources"][0]["format"] for item in found]
              == [kind] * len(found) and len(found) in (1, 2), found)
        check(f"{kind}: a layer with a legend on another host is not opened",
              kind == "wmts" or refused(lambda: image_catalog.open_layer(kind, there, "relief", ""), "another host")[0])
        image_catalog._CACHE.clear()
        check(f"{kind}: a service that sends its requests to another host is refused",
              *refused(lambda: image_catalog.catalog(kind, "https://other.example.org/" + kind), "another host"))
        for elsewhere, label in ((there.replace("https://", "http://"), "in clear"), (there.replace(".org/", ".org:8443/"), "another port")):
            image_catalog._CACHE.clear()
            check(f"{kind}: a service that sends its requests {label} is refused",
                  *refused(lambda: image_catalog.catalog(kind, elsewhere), "another host"))
        image_catalog.fetch = lambda url, **options: BoundedReply(200, {}, b"<html>no</html>")
        check(f"{kind}: a page that is no capabilities document is refused",
              *refused(lambda: image_catalog.catalog(kind, "https://page.example.org/" + kind), "offers no layer"))
        image_catalog.fetch = lambda url, **options: BoundedReply(200, {}, document[:len(document) // 2])
        check(f"{kind}: a document cut before its end is refused",
              *refused(lambda: image_catalog.catalog(kind, "https://cut.example.org/" + kind), "broken document"))
    image_catalog.fetch = real_fetch
    image_catalog._CACHE.clear()

    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    data = QgsVectorLayer("Point?crs=EPSG:4326", "data", "memory")
    project.addMapLayer(data)
    for platform, words, wanted in (("ign_wmts", "orthophotos", "ORTHOIMAGERY.ORTHOPHOTOS"),
                                    ("ign_wms", "plan ign", "GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2")):
        found = project_control.search_open_data(words, platform=platform, limit=20)
        ids = [item["id"] for item in found["datasets"]]
        check(f"{platform}: the search finds {wanted}", wanted in ids, ids)
        try:
            summary = project_control.add_service_layer(platform, wanted, name=platform)
        except ValueError as exc:
            check(f"{platform}: the layer is added", False, exc)
            continue
        layer = project.mapLayer(summary["layer_id"])
        order = [node.layerId() for node in project.layerTreeRoot().findLayers()]
        check(f"{platform}: a raster of the wms provider, under the data",
              summary["layer_kind"] == "raster" and summary["provider_type"] == "wms" and layer.isValid()
              and order[0] == data.id() and order.index(layer.id()) > 0, (summary, order))
        drawn = colours(layer)
        check(f"{platform}: draws Toulouse", drawn > 1, f"{drawn} colour(s); {layer.source()}")
        check(f"{platform}: a layer it does not list is refused", *refused(
            lambda: project_control.add_service_layer(platform, "invented&url=https://evil.example.org/"), "does not offer"))
    check("an image service is no basemap, and a basemap no service",
          refused(lambda: project_control.add_basemap("ign_wmts"), "is not a basemap")[0]
          and refused(lambda: project_control.add_service_layer("osm_tiles", "x"), "is not a WFS, WMS or WMTS service")[0])


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
