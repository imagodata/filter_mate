# -*- coding: utf-8 -*-
"""The options of the host, apart from it: the launcher lists them without starting QGIS (standard library only)."""

import argparse

from .. import paths, version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filtermate",
        description="FilterMate as an application of its own: the dock of the QGIS plugin, a map and a layer panel.")
    parser.add_argument("paths", nargs="*", metavar="FILE",
                        help="a QGIS project (.qgz, .qgs) or data files to open (GeoPackage, Shapefile, GeoTIFF, LAZ...)")
    parser.add_argument("--project", metavar="FILE", help="a QGIS project to open")
    parser.add_argument("--basemap", action="store_true", help="add the OpenStreetMap basemap")
    parser.add_argument("--lang", metavar="CODE", help="language of the interface (fr, en, de...); the system's by default")
    parser.add_argument("--profile", metavar="FOLDER",
                        help=f"folder of the application's settings (default: {paths.profile_dir()})")
    parser.add_argument("--size", metavar="WxH", help="size of the window, for instance 1600x1000")
    parser.add_argument("--maximized", action="store_true", help="open the window maximized (the size of the screen)")
    parser.add_argument("--offscreen", action="store_true", help="no window on screen (automation, servers)")
    parser.add_argument("--code", metavar="FILE", help="run this Python file once the window is up, as `qgis --code`")
    parser.add_argument("--no-plugin", action="store_true",
                        help="do not load FilterMate: the file given to --code loads it itself")
    parser.add_argument("--no-welcome", action="store_true", help="skip the dialogs of a first start")
    parser.add_argument("--version", action="version", version=f"FilterMate {version()}")
    return parser
