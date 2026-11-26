"""What the user watches while the agent works, in a real (headless) QGIS.

Without a window every tool that needs one is refused cleanly; what needs none (names, expressions, atlas
pages) really runs: the blink itself and the opened designer need QGIS on screen.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_gui.py

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsProject, QgsRectangle, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def refused(call, words=""):
    try:
        call()
    except ValueError as exc:
        return not words or words in str(exc)
    return False


def make_layer():
    fields = QgsFields()
    fields.append(QgsField("nom", QVariant.String))
    fields.append(QgsField("pop", QVariant.Int))
    layer = QgsVectorLayer("Polygon?crs=EPSG:2154", "communes", "memory")
    layer.dataProvider().addAttributes(fields.toList())
    layer.updateFields()
    features = []
    for index in range(5):
        feature = QgsFeature(layer.fields())
        x, y = 600000 + index * 5000, 6280000
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + 4000, y + 4000)))
        feature.setAttributes([f"Commune {index + 1:02d}", 100 * (index + 1)])
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    return layer


def main():
    from filter_mate.adapters.public_api import gui_control, layouts
    project = QgsProject.instance()
    layer = make_layer()
    project.addMapLayer(layer)
    project.setCrs(layer.crs())
    check("fixture valid", layer.isValid() and layer.featureCount() == 5)

    # --- open_layout: names without a window, the window without one
    check("open: refuses an unknown layout", refused(lambda: gui_control.open_layout("nope"), "no print layout"))
    layouts.create_layout("Carte", title="Communes", extent_layer="communes")
    check("open: a layout made is refused for its window, not its name",
          refused(lambda: gui_control.open_layout("Carte"), "no window"))

    # --- flash_features: the expression is read for real, the blink needs a window
    check("flash: refuses an unknown layer", refused(
        lambda: gui_control.flash_features("absente", '"pop" > 100'), "not found"))
    check("flash: refuses an empty expression", refused(
        lambda: gui_control.flash_features("communes", "  "), "an expression is needed"))
    check("flash: refuses a bad expression", refused(
        lambda: gui_control.flash_features("communes", '"pop" >>'), "invalid QGIS expression"))
    check("flash: refuses an unknown field", refused(
        lambda: gui_control.flash_features("communes", '"habitants" > 1'), "unknown field"))
    check("flash: refuses when nothing matches", refused(
        lambda: gui_control.flash_features("communes", '"pop" > 100000'), "no feature"))
    check("flash: a match is refused for its window, not its reading",
          refused(lambda: gui_control.flash_features("communes", '"pop" > 100'), "no window"))

    # --- set_active_layer: the layer is read, the window is missing
    check("active: refuses an unknown layer", refused(
        lambda: gui_control.set_active_layer("absente"), "not found"))
    check("active: a layer is refused for its window",
          refused(lambda: gui_control.set_active_layer("communes"), "no window"))

    # --- show_message: texts and levels without a window, the bar missing
    check("message: refuses an empty text", refused(lambda: gui_control.show_message("  "), "a message is needed"))
    check("message: refuses a bad level", refused(
        lambda: gui_control.show_message("hello", level="loud"), "level is one of"))
    check("message: a text is refused for its window, not its reading",
          refused(lambda: gui_control.show_message("hello"), "no window"))

    # --- preview_atlas: pages turn for real, even headless; the preview flag finds no designer
    check("atlas: refuses an unknown layout", refused(
        lambda: gui_control.preview_atlas("nope"), "no print layout"))
    check("atlas: refuses a layout with no atlas", refused(
        lambda: gui_control.preview_atlas("Carte"), "no atlas: set_atlas first"))
    layouts.set_atlas("Carte", "communes", page_name='"nom"')
    check("atlas: refuses a bad action", refused(
        lambda: gui_control.preview_atlas("Carte", action="back"), "action is one of"))
    turned = gui_control.preview_atlas("Carte", action="next")
    check("atlas: next turns to page 2 of 5, with no designer",
          (turned["page"], turned["pages"], turned["preview"]) == (2, 5, False), turned)
    turned = gui_control.preview_atlas("Carte", action="last")
    check("atlas: last turns to page 5", turned["page"] == 5, turned)
    check("atlas: no next page past the last one", refused(
        lambda: gui_control.preview_atlas("Carte", action="next"), "no next page"))
    turned = gui_control.preview_atlas("Carte", action="first")
    check("atlas: first turns back to page 1", turned["page"] == 1, turned)


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_gui"], False)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    os.symlink(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    print(f"QGIS {__import__('qgis.core').core.Qgis.QGIS_VERSION}, Python {sys.version.split()[0]}")
    main()
    failed = RESULTS.count(False)
    print(f"{len(RESULTS) - failed}/{len(RESULTS)} passed")
    sys.stdout.flush()
    os._exit(1 if failed else 0)
