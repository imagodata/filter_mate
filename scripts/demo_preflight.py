#!/usr/bin/env python3
"""Offline checks and portable Sarlat project preparation; no plugin or network needed.

Run with the Python shipped with QGIS, e.g.:
  QT_QPA_PLATFORM=offscreen python3 scripts/demo_preflight.py \
      --data /data/sarlat --project /work/sarlat.qgz --output /work/preflight.json
Without QGIS, the inventory and SQLite checks still run; the result is incomplete.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys


SARLAT_FILES = ("sarlat.gpkg", "mnt_1m.tif", "ortho_rvb.tif", "ortho_irc.tif", "lidar_hd_sarlat.copc.laz")
VECTOR_LAYERS = {"batiment": "Buildings", "parcelle": "Parcels", "troncon_de_route": "Road segments"}
RASTER_LAYERS = {"mnt_1m.tif": "DTM — 1 m", "ortho_rvb.tif": "RGB orthophoto", "ortho_irc.tif": "CIR orthophoto"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpkg_inventory(path):
    """Use a read-only connection, including when a caller passes an absent file."""
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        contents = db.execute("SELECT table_name, data_type, srs_id FROM gpkg_contents").fetchall()
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {}
        for name, kind, _crs in contents:
            if kind == "features":
                quoted = '"' + name.replace('"', '""') + '"'
                counts[name] = db.execute("SELECT count(*) FROM " + quoted).fetchone()[0]
        projects = db.execute("SELECT name FROM qgis_projects").fetchall() if "qgis_projects" in tables else []
    return {"contents": contents, "counts": counts, "embedded_projects": [row[0] for row in projects]}


def inspect(data, project=None):
    result = {"schema": 1, "platform": platform.platform(), "data": str(data), "files": {}, "errors": []}
    for name in SARLAT_FILES:
        path = data / name
        if not path.is_file():
            result["errors"].append("missing " + name)
        else:
            result["files"][name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    if (data / "sarlat.gpkg").is_file():
        result["gpkg"] = gpkg_inventory(data / "sarlat.gpkg")
        for name in VECTOR_LAYERS:
            if result["gpkg"]["counts"].get(name, 0) <= 0:
                result["errors"].append("empty or missing vector table " + name)
    try:
        from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsProject,
                               QgsRasterLayer, QgsVectorLayer, QgsPointCloudLayer, QgsRectangle,
                               QgsReferencedRectangle)
        from qgis.PyQt.QtCore import QT_VERSION_STR
    except ImportError:
        result["errors"].append("QGIS Python unavailable: geometry/raster/provider checks not run")
        return result
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    result.update(qgis=Qgis.QGIS_VERSION, qt=QT_VERSION_STR, pdal=shutil.which("pdal"))
    prj = QgsProject.instance()
    prj.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
    layers = []
    for name, label in VECTOR_LAYERS.items():
        layers.append(QgsVectorLayer(f"{data / 'sarlat.gpkg'}|layername={name}", label, "ogr"))
    for name, label in RASTER_LAYERS.items():
        layers.append(QgsRasterLayer(str(data / name), label, "gdal"))
    layers.append(QgsPointCloudLayer(str(data / SARLAT_FILES[-1]), "LiDAR HD", "copc"))
    result["layers"] = []
    for layer in layers:
        item = {"name": layer.name(), "valid": layer.isValid(), "crs": layer.crs().authid()}
        if isinstance(layer, QgsRasterLayer) and not layer.crs().isValid() and layer.name() in (
                "RGB orthophoto", "CIR orthophoto"):
            # The checked Sarlat package has the same Lambert-93 extent for these untagged TIFFs.
            extent = layer.extent()
            bounds = [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]
            if bounds == [559000.0, 6422000.0, 560000.0, 6423000.0]:
                layer.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))
                item.update(source_crs="", crs="EPSG:2154", crs_assigned_from="Sarlat data-audit.json extent")
        if not layer.isValid():
            result["errors"].append("invalid QGIS layer " + layer.name())
        else:
            if not layer.crs().isValid():
                result["errors"].append("missing CRS " + layer.name())
            if hasattr(layer, "featureCount"):
                item["count"] = layer.featureCount()
            if isinstance(layer, QgsRasterLayer):
                item.update(width=layer.width(), height=layer.height(), bands=layer.bandCount(),
                            pixel_m=[layer.rasterUnitsPerPixelX(), layer.rasterUnitsPerPixelY()])
            prj.addMapLayer(layer)
        result["layers"].append(item)
    if not result["errors"]:
        roads = prj.mapLayersByName("Road segments")[0]
        result["boulevard_segments"] = sum(
            f["nom_collaboratif_gauche"] == "BD HENRI ARLET" for f in roads.getFeatures())
        if result["boulevard_segments"] != 9:
            result["errors"].append("Boulevard Henri Arlet: expected 9 segments")
    if project and not result["errors"]:
        project.parent.mkdir(parents=True, exist_ok=True)
        prj.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(
            QgsRectangle(559000, 6422000, 560000, 6423000), prj.crs()))
        if not prj.write(str(project)):
            result["errors"].append("cannot save project")
        else:
            result["project"] = str(project)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.data.resolve(), args.project)
    result["ok"] = not result["errors"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "qgis": result.get("qgis"), "errors": result["errors"]}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
