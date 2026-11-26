# -*- coding: utf-8 -*-
"""Controle rapide du poste Windows / QGIS 4 pour le teaser crue de l'Urumea.

Usage :
  1. Copier ce fichier sur le poste Windows.
  2. Dans QGIS 4 : Extensions > Console Python > Editeur, ouvrir le fichier, Executer.
  3. Renvoyer tout le texte affiche dans la console.

Ne modifie rien : lecture seule (versions, couches du projet courant).
"""
from qgis.core import Qgis, QgsProject
from qgis.utils import plugins

print("=== QGIS ===")
print("version :", Qgis.QGIS_VERSION)

print("=== FilterMate ===")
print("charge :", "filter_mate" in plugins)
if "filter_mate" in plugins:
    fm = plugins["filter_mate"]
    print("classe :", type(fm).__name__)
    app = getattr(fm, "app", None)
    print("app :", type(app).__name__ if app is not None else "absente")

print("=== Projet courant ===")
prj = QgsProject.instance()
print("fichier :", prj.fileName() or "(non enregistre)")
print("SCR :", prj.crs().authid())
for layer in prj.mapLayers().values():
    if layer.type().name == "VectorLayer" if hasattr(layer.type(), "name") else True:
        try:
            kind = {0: "point", 1: "ligne", 2: "polygone"}.get(layer.geometryType(), "?")
            print(f"- {layer.name()} [{kind}] : {layer.featureCount()} entites | {layer.crs().authid()}")
        except Exception as exc:  # noqa: BLE001
            print(f"- {layer.name()} : illisible ({exc})")

print("=== Teaser : attendus ===")
print(" couches OSM : batiments, routes, ponts, riviere Urumea + MNT Copernicus 30 m")
print(" agent : token API Claude + modele Haiku (variable d'environnement du poste)")
print("OK = QGIS 4.x, FilterMate charge, couches presentes.")
