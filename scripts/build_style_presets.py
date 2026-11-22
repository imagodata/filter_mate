# -*- coding: utf-8 -*-
"""Build the official styles the agent applies to data layers (``list_style_presets``, ``apply_style_preset``).

The producers draw their vector tiles with MapLibre styles; QGIS converts those (``QgsMapBoxGlStyleConverter``) into
styles of vector tile layers, a style per source layer with a filter, a symbol and a zoom range. This script makes
each source layer a QML for a plain vector layer of that table (a GeoPackage of the BD TOPO, OpenStreetMap features
brought by ``add_osm_features``):

* a rule-based renderer, a rule per style of that source layer: its filter, its symbol, its zoom range as a scale
  range (``core/agent/style_presets.scale_range``: the convention QGIS draws vector tiles with), drawn in the order of
  the style (symbol levels); a line drawn on an area becomes the outline of the area;
* rule-based labels when the style labels that source layer;
* the zoom of the map (``@vector_tile_zoom``, in widths and opacities that change with the zoom) computed from the
  scale of the map.

Written to ``resources/styles/<family>/<dataset>/<style>/<table>.qml`` with ``resources/styles/manifest.json``. The
variants (``gris``, ``sombre``) are computed from the colours of these files when they are applied
(``core/agent/style_presets.variant_rgb``), not written here.

Sources and licences (checked 2026-11-22):

* IGN, BD TOPO (flux ``BDTOPO`` of the Géoplateforme, "BD TOPO® personnalisable"): the styles ``classique``,
  ``routier``, ``bati`` and ``hydrographie`` at ``https://data.geopf.fr/annexes/ressources/vectorTiles/styles/BDTOPO/``,
  their sprite, and the description of the tables (``https://data.geopf.fr/tms/1.0.0/BDTOPO/metadata.json``). The
  styles carry no licence of their own; the terms of cartes.gouv.fr give the content of the Géoplateforme the
  Licence Ouverte / Open Licence 2.0 (Etalab) where its producer gives none, and the BD TOPO is under that licence:
  reuse and redistribution free, the source named. A copy is kept in ``resources/styles/sources``.
* OpenStreetMap: the VersaTiles style ``colorful`` (CC0, as its metadata says) of the Shortbread vector tiles of the
  OSMF (``https://vector.openstreetmap.org/styles/shortbread/colorful.json``). Shortbread names its classes
  (``streets``, ``land``...) and their ``kind``; the layers ``add_osm_features`` makes hold the OSM tags themselves, a
  column per key asked (``highway``, ``building``...). ``OSM_CLASSES`` below maps one onto the other: the filters of
  the style are rewritten on those columns before the conversion. What the columns cannot say is left out: tunnels and
  bridges, links that Shortbread tells by a flag, bicycle roads, one-way arrows, icons (in ``other_tags``). The layers
  of the style this uses are kept in ``resources/styles/sources`` (CC0). The data drawn are OpenStreetMap's (ODbL).

Run it in QGIS (the newest converts best; what it writes loads in QGIS 3.22, checked by
``tests/qgis_headless/check_agent_style_presets.py``)::

    docker run --rm -v "$PWD":/src -w /src -e QT_QPA_PLATFORM=offscreen qgis/qgis:latest \\
        python3 scripts/build_style_presets.py            # downloads the sources again
    ... python3 scripts/build_style_presets.py --offline  # from the copies in resources/styles/sources
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.request
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core", "agent"))
import style_presets as presets  # noqa: E402  (plain Python: imported alone, without the plugin package)

STYLES_DIR = os.path.join(ROOT, "resources", "styles")
SOURCES_DIR = os.path.join(STYLES_DIR, "sources")
IGN_BASE = "https://data.geopf.fr/annexes/ressources/vectorTiles/styles/BDTOPO/"
IGN_STYLES = ("classique", "routier", "bati", "hydrographie")
IGN_METADATA = "https://data.geopf.fr/tms/1.0.0/BDTOPO/metadata.json"
IGN_LICENCE = "Licence Ouverte / Open Licence 2.0 (Etalab)"
IGN_ATTRIBUTION = "IGN, BD TOPO® (style of the Géoplateforme)"
OSM_STYLE = "colorful"
OSM_URL = f"https://vector.openstreetmap.org/styles/shortbread/{OSM_STYLE}.json"
OSM_LICENCE = "Style: CC0 (VersaTiles); data: ODbL"
OSM_ATTRIBUTION = "© OpenStreetMap contributors; style VersaTiles Colorful"
GEOMETRY_OF_METADATA = {"POINT": "point", "MULTIPOINT": "point", "LINESTRING": "line", "MULTILINESTRING": "line",
                        "POLYGON": "polygon", "MULTIPOLYGON": "polygon"}
# A field in this share of the tables of the BD TOPO or more tells none apart (cleabs, nature, toponyme, dates...).
COMMON_SHARE = 0.2

ROAD_KINDS = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
              "pedestrian", "service", "track", "footway", "steps", "path", "cycleway", "busway", "bus_guideway",
              "bridleway")
RAIL_KINDS = ("rail", "light_rail", "subway", "tram", "narrow_gauge", "monorail", "funicular")
# Shortbread class -> how the layers of add_osm_features hold it: the source layers of the style it comes from, the
# column (an OSM key), the geometry of the layer, and for each kind of Shortbread the values of that key (None: the
# kind is the value itself; a class with no kinds takes any value).
OSM_CLASSES: Dict[str, Dict[str, Any]] = {
    "roads": {"layers": ("streets", "street_labels"), "column": "highway", "geometry": "line",
              "kinds": {kind: None for kind in ROAD_KINDS}, "links": True},
    "railways": {"layers": ("streets",), "column": "railway", "geometry": "line",
                 "kinds": {kind: None for kind in RAIL_KINDS}},
    "waterways": {"layers": ("water_lines",), "column": "waterway", "geometry": "line",
                  "kinds": {kind: None for kind in ("river", "canal", "stream", "ditch", "drain")}},
    "landuse": {"layers": ("land", "water_polygons"), "column": "landuse", "geometry": "polygon", "kinds": {
        **{kind: None for kind in (
            "commercial", "retail", "industrial", "quarry", "railway", "garages", "residential", "brownfield",
            "farmland", "farmyard", "greenfield", "greenhouse_horticulture", "orchard", "plant_nursery", "vineyard",
            "landfill", "allotments", "cemetery", "forest", "grass", "meadow", "recreation_ground", "village_green",
            "reservoir", "basin")}}},
    "natural": {"layers": ("land", "water_polygons"), "column": "natural", "geometry": "polygon", "kinds": {
        "forest": ("wood",), "water": ("water",), "glacier": ("glacier",), "marsh": ("wetland",),
        **{kind: None for kind in ("heath", "scrub", "grassland", "bare_rock", "scree", "shingle", "sand", "beach")}}},
    "leisure": {"layers": ("land",), "column": "leisure", "geometry": "polygon",
                "kinds": {kind: None for kind in ("park", "garden", "golf_course", "miniature_golf", "playground")}},
    "buildings": {"layers": ("buildings",), "column": "building", "geometry": "polygon", "kinds": None},
    "boundaries": {"layers": ("boundaries",), "column": "admin_level", "geometry": "polygon", "level": True,
                   "kinds": None},
}
_DROP = "drop"
# Flags of Shortbread the columns of add_osm_features do not hold: a style for them alone is left out, a style that
# only excludes them is kept.
_FLAGS = ("tunnel", "bridge", "maritime", "disputed", "coastline")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "FilterMate style presets builder"})
    with urllib.request.urlopen(request, timeout=60) as reply:  # nosec B310 - fixed https addresses of producers
        return reply.read()


def _source(name: str, url: str, offline: bool, keep: bool = True) -> bytes:
    path = os.path.join(SOURCES_DIR, name)
    if offline:
        with open(path, "rb") as stream:
            return stream.read()
    content = fetch(url)
    if keep:
        os.makedirs(SOURCES_DIR, exist_ok=True)
        with open(path, "wb") as stream:
            stream.write(content)
    return content


# ---------------------------------------------------------------------------------------------------------------------
# OpenStreetMap: Shortbread filters rewritten on the columns of add_osm_features.
# ---------------------------------------------------------------------------------------------------------------------

def _key(term: Any) -> Optional[str]:
    """The attribute a term reads: ``["get", "kind"]`` (expressions) or ``"kind"`` (legacy filters)."""
    if isinstance(term, list) and len(term) == 2 and term[0] == "get":
        return term[1]
    return term if isinstance(term, str) else None


def _values(term: Any) -> List[Any]:
    if isinstance(term, list) and term and term[0] == "literal":
        return list(term[1])
    return list(term) if isinstance(term, list) else [term]


def _clause(expression: Any, state: Dict[str, Any], kind_key: str) -> Optional[str]:
    """Read one clause of a Shortbread filter into ``state`` (kinds, link); _DROP when the columns cannot say it."""
    if not isinstance(expression, list) or not expression:
        return _DROP
    operator = expression[0]
    if operator == "all":
        for part in expression[1:]:
            if _clause(part, state, kind_key) == _DROP:
                return _DROP
        return None
    if operator == "!" and isinstance(expression[1], list) and expression[1][:1] == ["has"]:
        return None if expression[1][1] == "service" else _DROP  # a railway that is no siding: every one here
    if operator == "has":
        return _DROP
    if operator in ("==", "!=", "in") and len(expression) >= 3:
        key = _key(expression[1])
        values = _values(expression[2]) if operator == "in" and len(expression) == 3 else expression[2:]
        if key in _FLAGS or key == "link":
            if values != [True]:
                return _DROP
            if key == "link":
                state["link"] = operator == "=="
                return None
            return None if operator == "!=" else _DROP  # a tunnel or a bridge alone: not in the columns
        if key == kind_key and operator in ("==", "in"):
            kinds = {str(value) for value in values}
            state["kinds"] = kinds if state.get("kinds") is None else state["kinds"] & kinds
            return None
    return _DROP


def osm_filter(layer: Dict[str, Any], spec: Dict[str, Any]) -> Optional[List[Any]]:
    """The filter of a style of the Shortbread layer ``layer`` written on the column of ``spec``; None when the
    columns of add_osm_features cannot say it."""
    kind_key = "admin_level" if spec.get("level") else "kind"
    state: Dict[str, Any] = {"kinds": None, "link": None}
    if "filter" in layer and _clause(layer["filter"], state, kind_key) == _DROP:
        return None
    column = spec["column"]
    if spec.get("level"):
        if state["kinds"] is None:
            return None
        return ["in", ["get", column], ["literal", sorted(str(value) for value in state["kinds"])]]
    if spec["kinds"] is None:
        return ["has", column] if state["kinds"] is None else None
    if state["kinds"] is None:
        return None
    values: List[str] = []
    for kind in sorted(state["kinds"]):
        if kind not in spec["kinds"]:
            continue
        for value in spec["kinds"][kind] or (kind,):
            values.append(value + "_link" if state["link"] and spec.get("links") else value)
    if state["link"] and not spec.get("links"):
        return None
    return ["in", ["get", column], ["literal", values]] if values else None


def osm_style(style: Dict[str, Any]) -> Tuple[Dict[str, Any], Counter]:
    """The style with its layers rewritten for the classes of OSM_CLASSES: the source layer of each is its class."""
    layers, left = [], Counter()
    for name, spec in OSM_CLASSES.items():
        for layer in style["layers"]:
            if layer.get("source-layer") not in spec["layers"] or layer.get("type") not in ("fill", "line", "symbol"):
                continue
            # Counted as left out of a class only when it draws one of its kinds (the streets hold roads and rails).
            mentions = not spec["kinds"] or any(f'"{kind}"' in json.dumps(layer.get("filter"))
                                                for kind in spec["kinds"])
            if layer["type"] == "symbol" and ("icon-image" in layer.get("layout", {})
                                              or layer.get("layout", {}).get("text-field") != ["get", "name"]):
                left[name] += mentions  # icons and shields: not drawn from the columns
                continue
            rewritten = osm_filter(layer, spec)
            if rewritten is None:
                left[name] += mentions
                continue
            copy = json.loads(json.dumps(layer))
            copy.update({"id": f"{name}:{layer['id']}", "source-layer": name, "filter": rewritten})
            layers.append(copy)
    made = {key: value for key, value in style.items() if key not in ("layers", "sprite")}
    made["layers"] = layers
    return made, left


def osm_used_layers(style: Dict[str, Any]) -> Dict[str, Any]:
    """The part of the style this script reads (its source layers of OSM_CLASSES), kept as the source."""
    wanted = {name for spec in OSM_CLASSES.values() for name in spec["layers"]}
    kept = {key: value for key, value in style.items() if key != "layers"}
    kept["layers"] = [layer for layer in style["layers"] if layer.get("source-layer") in wanted]
    return kept


# ---------------------------------------------------------------------------------------------------------------------
# QGIS: the converted styles of a source layer made into the style of a plain layer.
# ---------------------------------------------------------------------------------------------------------------------

def convert(style: Dict[str, Any], sprite: Optional[Tuple[bytes, Dict[str, Any]]] = None):
    """(converter, renderer, labeling, warnings) of a MapLibre style.

    The converter is given back to be kept as long as its renderer and labeling: freed before them, it leaves their
    symbols to memory it no longer holds (QGIS 4.3, 2026-11-22: the heap broken a few tables later).
    """
    from qgis.core import QgsMapBoxGlStyleConversionContext, QgsMapBoxGlStyleConverter, QgsUnitTypes
    from qgis.PyQt.QtGui import QImage
    context = QgsMapBoxGlStyleConversionContext()
    context.setTargetUnit(QgsUnitTypes.RenderMillimeters)
    context.setPixelSizeConversionFactor(25.4 / 96.0)
    if sprite is not None:
        image = QImage()
        image.loadFromData(sprite[0])
        context.setSprites(image, sprite[1])
    converter = QgsMapBoxGlStyleConverter()
    converter.convert(style, context)
    if converter.errorMessage():
        raise RuntimeError(converter.errorMessage())
    return converter, converter.renderer(), converter.labeling(), list(converter.warnings())


def _geometry_index(geometry: str) -> int:
    return {"point": 0, "line": 1, "polygon": 2}[geometry]


def _as_outline(symbol):
    """A line symbol drawn as the outline of an area: a fill symbol holding its symbol layers."""
    from qgis.core import QgsFillSymbol
    fill = QgsFillSymbol()
    if not all(fill.appendSymbolLayer(layer.clone()) for layer in symbol.symbolLayers()):
        return None
    fill.deleteSymbolLayer(0)
    fill.setOpacity(symbol.opacity())
    return fill


def _fields_of(expression_text: str) -> List[str]:
    from qgis.core import QgsExpression
    if not expression_text:
        return []
    return sorted(name for name in QgsExpression(expression_text).referencedColumns() if name and name != "*")


def table_style(table: str, geometry: str, renderer, labeling) -> Optional[Dict[str, Any]]:
    """The rule-based renderer and labeling of ``table`` from the converted styles of its source layer, with what they
    read; None when no style of the source layer can draw a layer of that geometry."""
    from qgis.core import (QgsFeatureRequest, QgsFillSymbol, QgsPalLayerSettings, QgsRenderContext,
                           QgsRuleBasedLabeling, QgsRuleBasedRenderer)
    wanted = _geometry_index(geometry)
    # Made from a symbol, its rules hung on the root it makes, the root removed with it: a root made in Python and given
    # to the renderer broke the heap (QGIS 3.44 and 4.3, 2026-11-22).
    made = QgsRuleBasedRenderer(QgsFillSymbol())
    root = made.rootRule()
    root.removeChildAt(0)
    used: set = set()
    rules = skipped = 0
    minimum_scales: List[float] = []
    for style in renderer.styles():
        if style.layerName() != table or not style.isEnabled() or style.symbol() is None:
            continue
        symbol = style.symbol().clone()
        kind = int(style.geometryType())
        if kind != wanted:
            if wanted == 2 and kind == 1:
                symbol = _as_outline(symbol)
            else:
                symbol = None
        if symbol is None:
            skipped += 1
            continue
        for index in range(symbol.symbolLayerCount()):
            symbol.symbolLayer(index).setRenderingPass(rules)  # drawn in the order of the style
        minimum, maximum = presets.scale_range(style.minZoomLevel(), style.maxZoomLevel())
        minimum_scales.append(minimum)
        rule = QgsRuleBasedRenderer.Rule(symbol, maximum, minimum, style.filterExpression(), style.styleName())
        root.appendChild(rule)
        used.update(_fields_of(style.filterExpression()))
        used.update(name for name in symbol.usedAttributes(QgsRenderContext()) if name)
        rules += 1
    made_labels = QgsRuleBasedLabeling(QgsRuleBasedLabeling.Rule(None))
    label_root = made_labels.rootRule()
    labels = 0
    for style in (labeling.styles() if labeling is not None else []):
        if style.layerName() != table or not style.isEnabled():
            continue
        settings = QgsPalLayerSettings(style.labelSettings())
        minimum, maximum = presets.scale_range(style.minZoomLevel(), style.maxZoomLevel())
        minimum_scales.append(minimum)
        label_root.appendChild(QgsRuleBasedLabeling.Rule(settings, maximum, minimum, style.filterExpression(),
                                                         style.styleName()))
        used.update(_fields_of(style.filterExpression()))
        used.update(_fields_of(settings.fieldName) if settings.isExpression else [settings.fieldName])
        used.update(name for name in settings.referencedFields(QgsRenderContext()) if name)
        labels += 1
    if not rules and not labels:
        return None
    made.setUsingSymbolLevels(True)
    used.discard(QgsFeatureRequest.ALL_ATTRIBUTES)  # an expression that may read any field: none in particular
    return {"renderer": made if rules else None, "labeling": made_labels if labels else None, "rules": rules,
            "labels": labels, "skipped": skipped, "required": sorted(name for name in used if name),
            # The most zoomed out scale anything is drawn at: 0 when something is drawn at every scale.
            "scale": 0 if not minimum_scales or 0 in minimum_scales else max(minimum_scales)}


def write_qml(path: str, geometry: str, made: Dict[str, Any]) -> None:
    from qgis.core import QgsField, QgsMapLayer, QgsReadWriteContext, QgsVectorLayer
    from qgis.PyQt.QtCore import QVariant
    from qgis.PyQt.QtXml import QDomDocument
    layer = QgsVectorLayer({"point": "Point", "line": "LineString", "polygon": "Polygon"}[geometry] + "?crs=EPSG:3857",
                           "style", "memory")
    layer.dataProvider().addAttributes([QgsField(name, QVariant.String) for name in made["required"]])
    layer.updateFields()
    if made["renderer"] is not None:
        layer.setRenderer(made["renderer"])
    else:  # labels alone: nothing drawn but them
        from qgis.core import QgsNullSymbolRenderer
        layer.setRenderer(QgsNullSymbolRenderer())
    if made["labeling"] is not None:
        layer.setLabeling(made["labeling"])
        layer.setLabelsEnabled(True)
    category = getattr(QgsMapLayer, "StyleCategory", QgsMapLayer)
    document = QDomDocument("qgis")
    error = layer.exportNamedStyle(document, QgsReadWriteContext(),
                                   category.Symbology | category.Labeling | category.Rendering)
    if error:
        raise RuntimeError(f"{path}: {error}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(presets.zoom_free(document.toString(1)))


# ---------------------------------------------------------------------------------------------------------------------

def bdtopo_tables(metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """{table: {geometry, fields, all}} of the tables of the BD TOPO tiles: ``all`` their fields, ``fields`` those
    that tell the table apart (not those of most tables: cleabs, nature, toponyme, dates...)."""
    layers = metadata["vector_layers"]
    counts = Counter(field for layer in layers for field in layer.get("fields", {}))
    common = {field for field, count in counts.items() if count >= COMMON_SHARE * len(layers)}
    return {layer["id"]: {"geometry": GEOMETRY_OF_METADATA.get(str(layer.get("geometry", "")).upper(), ""),
                          "fields": sorted(set(layer.get("fields", {})) - common),
                          "all": sorted(layer.get("fields", {}))} for layer in layers}


def build_ign(offline: bool, today: str) -> Dict[str, Any]:
    sprite = (_source("ign_bdtopo_sprite.png", IGN_BASE + "sprite/sprite_bdtopo.png", offline),
              json.loads(_source("ign_bdtopo_sprite.json", IGN_BASE + "sprite/sprite_bdtopo.json", offline)))
    if offline:
        with open(os.path.join(SOURCES_DIR, "ign_bdtopo_tables.json"), encoding="utf-8") as stream:
            tables = json.load(stream)
    else:
        tables = bdtopo_tables(json.loads(fetch(IGN_METADATA)))
        with open(os.path.join(SOURCES_DIR, "ign_bdtopo_tables.json"), "w", encoding="utf-8") as stream:
            json.dump(tables, stream, ensure_ascii=False, indent=1, sort_keys=True)
    made: Dict[str, Any] = {}
    for name in IGN_STYLES:
        url = IGN_BASE + f"{name}.json"
        style = json.loads(_source(f"ign_bdtopo_{name}.json", url, offline))
        converter, renderer, labeling, warnings = convert(style, sprite if style.get("sprite") else None)
        entries: Dict[str, Any] = {}
        skipped = 0
        for table in sorted({layer.get("source-layer") for layer in style["layers"] if layer.get("source-layer")}):
            described = tables.get(table)
            if not described or not described["geometry"]:
                print(f"  {name}/{table}: not a table of the tiles, left out")
                continue
            result = table_style(table, described["geometry"], renderer, labeling)
            if result is None:  # its styles are hidden in the style of IGN (visibility none)
                print(f"  {name}/{table}: nothing drawn on a {described['geometry']} layer, left out")
                skipped += sum(1 for layer in style["layers"] if layer.get("source-layer") == table)
                continue
            unknown = [field for field in result["required"] if field not in described["all"]]
            if unknown:
                print(f"  {name}/{table}: reads fields the tiles do not describe: {unknown}")
            relative = f"ign/bdtopo/{name}/{table}.qml"
            write_qml(os.path.join(STYLES_DIR, relative), described["geometry"], result)
            skipped += result["skipped"]
            entries[table] = {"file": relative, "geometry": described["geometry"], "required": result["required"],
                              "fields": described["fields"], "rules": result["rules"], "labels": result["labels"],
                              "scale": result["scale"]}
        made[f"ign/bdtopo/{name}"] = {
            "family": "ign", "dataset": "bdtopo", "style": name, "title": f"BD TOPO {name} (IGN)",
            "source": url, "licence": IGN_LICENCE, "attribution": IGN_ATTRIBUTION, "generated": today,
            "warnings": len(warnings), "skipped": skipped, "variants": list(presets.VARIANTS), "tables": entries}
        del renderer, labeling, converter  # in this order: the converter last
        print(f"ign/bdtopo/{name}: {len(entries)} tables, {len(warnings)} warnings, {skipped} styles left out")
        for warning in warnings:
            print("   warning:", warning)
    return made


def build_osm(offline: bool, today: str) -> Dict[str, Any]:
    if offline:
        with open(os.path.join(SOURCES_DIR, f"osm_versatiles_{OSM_STYLE}.json"), encoding="utf-8") as stream:
            style = json.load(stream)
    else:
        style = osm_used_layers(json.loads(fetch(OSM_URL)))
        os.makedirs(SOURCES_DIR, exist_ok=True)
        with open(os.path.join(SOURCES_DIR, f"osm_versatiles_{OSM_STYLE}.json"), "w", encoding="utf-8") as stream:
            json.dump(style, stream, ensure_ascii=False, separators=(",", ":"))
    rewritten, left = osm_style(style)
    converter, renderer, labeling, warnings = convert(rewritten)
    entries: Dict[str, Any] = {}
    for name, spec in OSM_CLASSES.items():
        result = table_style(name, spec["geometry"], renderer, labeling)
        if result is None:
            print(f"  osm/{name}: nothing drawn, left out")
            continue
        # The labels read the name, which every layer of add_osm_features has; the style reads nothing else.
        extra = [field for field in result["required"] if field not in (spec["column"], "name")]
        if extra:
            raise RuntimeError(f"osm/{name} reads {extra}: not in the columns of add_osm_features")
        relative = f"osm/{OSM_STYLE}/{name}.qml"
        write_qml(os.path.join(STYLES_DIR, relative), spec["geometry"], result)
        entries[name] = {"file": relative, "geometry": spec["geometry"], "required": result["required"],
                         "fields": [spec["column"]], "by_name": False, "rules": result["rules"],
                         "labels": result["labels"], "scale": result["scale"]}
        print(f"  osm/{name}: {result['rules']} rules, {result['labels']} labels, "
              f"{left[name] + result['skipped']} styles left out")
    del renderer, labeling, converter
    print(f"osm/{OSM_STYLE}: {len(entries)} classes, {len(warnings)} warnings")
    for warning in warnings:
        print("   warning:", warning)
    return {f"osm/{OSM_STYLE}": {
        "family": "osm", "dataset": "openstreetmap", "style": OSM_STYLE, "title": "OpenStreetMap, VersaTiles colorful",
        "source": OSM_URL, "licence": OSM_LICENCE, "attribution": OSM_ATTRIBUTION, "generated": today,
        "warnings": len(warnings), "skipped": sum(left.values()), "variants": list(presets.VARIANTS),
        "tables": entries}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="convert the copies in resources/styles/sources")
    options = parser.parse_args()
    from qgis.core import Qgis, QgsApplication
    app = QgsApplication([b"build_style_presets"], False)
    app.initQgis()
    today = datetime.date.today().isoformat()
    print(f"QGIS {Qgis.QGIS_VERSION}")
    made = {**build_ign(options.offline, today), **build_osm(options.offline, today)}
    manifest = {"version": 1, "generated": today, "qgis": Qgis.QGIS_VERSION,
                "zoom": "a zoom level z is shown from 1:%d/2^(z-0.5) to 1:%d/2^(z+0.5)" % (presets.Z0_SCALE,
                                                                                         presets.Z0_SCALE),
                "presets": made}
    with open(os.path.join(STYLES_DIR, "manifest.json"), "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=1, sort_keys=True)
        stream.write("\n")
    app.exitQgis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
