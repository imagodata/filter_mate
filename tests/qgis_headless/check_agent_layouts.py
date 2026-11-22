"""Print layouts of the agent in a real (headless) QGIS: what describe_layout reads, the export as PDF, PNG, JPG,
SVG and TIFF (georeferenced or not), the atlas over a filtered layer and its export, and the undo of the turn.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        python3 /src/tests/qgis_headless/check_agent_layouts.py

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry, QgsProject, QgsRectangle, QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402

RESULTS = []


def check(label, condition, detail=""):
    RESULTS.append(bool(condition))
    print(f"{'PASS' if condition else 'FAIL'} {label}" + (f" -- {str(detail)[:400]}" if not condition else ""))


def refused(call):
    try:
        call()
    except ValueError:
        return True
    return False


def make_layer(path):
    fields = QgsFields()
    fields.append(QgsField("nom", QVariant.String))
    fields.append(QgsField("dept", QVariant.String))
    fields.append(QgsField("pop", QVariant.Int))
    memory = QgsVectorLayer("Polygon?crs=EPSG:2154", "memory", "memory")
    memory.dataProvider().addAttributes(fields.toList())
    memory.updateFields()
    features = []
    for index in range(12):
        feature = QgsFeature(memory.fields())
        x, y = 600000 + (index % 4) * 5000, 6280000 + (index // 4) * 5000
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + 4000, y + 4000)))
        feature.setAttributes([f"Commune {index + 1:02d}", "31" if index < 7 else "32", 100 * (index + 1)])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import layouts
    from filter_mate.core.agent.messages import ToolCallPart
    work = tempfile.mkdtemp()
    path = os.path.join(work, "communes.gpkg")
    make_layer(path)
    layer = QgsVectorLayer(path, "communes", "ogr")
    project = QgsProject.instance()
    project.addMapLayer(layer)
    project.setCrs(layer.crs())
    check("fixture valid", layer.isValid() and layer.featureCount() == 12)

    layouts.create_layout("Carte", title="Communes", extent_layer="communes")
    listed = layouts.describe_layout("")
    check("describe: without a name, the layouts and the templates", "Carte" in listed["layouts"] and
          isinstance(listed["templates"], list), listed)
    read = layouts.describe_layout("Carte")
    kinds = sorted(item["type"] for item in read["items"])
    page = {"page": 1, "width_mm": 297.0, "height_mm": 210.0}
    check("describe: the page in mm and its items", read["pages"] == [page]
          and kinds == ["legend", "map", "picture", "scale_bar", "text"], read)
    map_row = next(item for item in read["items"] if item["type"] == "map")
    check("describe: a map with its place, size and scale", map_row["x_mm"] == 10.0 and map_row["width_mm"] == 277.0
          and "scale" in map_row and map_row["ref"], map_row)  # QGIS 3.22: None until the map is drawn
    check("describe: refuses an unknown layout", refused(lambda: layouts.describe_layout("nope")))

    # --- formats
    folder = os.path.join(work, "out")
    formats = [("pdf", b"%PDF"), ("png", b"\x89PNG"), ("jpg", b"\xff\xd8\xff"), ("svg", b"<?xml")]
    if layouts.tiff_available():
        formats.append(("tif", (b"II*\x00", b"MM\x00*")))
    else:
        check("export: tif refused where Qt has no TIFF plugin", refused(
            lambda: layouts.export_layout("Carte", folder, "tif")))
    for file_format, magic in formats:
        answer = layouts.export_layout("Carte", folder, file_format, dpi=96)
        head = open(answer["path"], "rb").read(5)
        wanted = magic if isinstance(magic, tuple) else (magic,)
        check(f"export {file_format}", answer["bytes"] > 1000 and any(head.startswith(item) for item in wanted),
              (answer, head))
    world = {".pgw", ".jgw", ".tfw", ".wld"}
    found = {os.path.splitext(name)[1] for name in os.listdir(folder)}
    check("export: an image with a map has its world file", found & world, sorted(found))
    plain = os.path.join(work, "plain")
    layouts.export_layout("Carte", plain, "png", dpi=96, georeference=False)
    check("export: georeference false writes no world file",
          not {os.path.splitext(name)[1] for name in os.listdir(plain)} & world, os.listdir(plain))
    check("export: refuses a format", refused(lambda: layouts.export_layout("Carte", folder, "bmp")))

    # --- atlas over the layer as filtered
    layer.setSubsetString("\"dept\" = '31'")
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("a1", "set_atlas", {"layout": "Carte"}))
    answer = layouts.set_atlas("Carte", "communes", page_name="\"nom\"", sort_by="\"pop\"", descending=True)
    check("atlas: one page per feature of the filtered layer", answer["pages"] == 7 and answer["atlas"] and
          answer["maps"] and "note" in answer, answer)
    narrowed = layouts.set_atlas("Carte", "communes", filter_expression="\"pop\" > 300", page_name="\"nom\"")
    check("atlas: its filter narrows it without touching the layer", narrowed["pages"] == 4 and
          layer.subsetString() == "\"dept\" = '31'", narrowed)
    described = layouts.describe_layout("Carte")
    check("describe: the atlas and the map it drives", described.get("atlas", {}).get("pages") == 4 and
          described["atlas"]["maps"] and any(item.get("atlas_driven") for item in described["items"]),
          described.get("atlas"))
    for call, label in ((lambda: layouts.set_atlas("Carte", "nope"), "an unknown layer"),
                        (lambda: layouts.set_atlas("Carte", "communes", page_name="\"nom\" ||"), "a broken expression"),
                        (lambda: layouts.set_atlas("Carte", "communes", map_mode="zoom"), "an unknown mode"),
                        (lambda: layouts.set_atlas("Carte", "communes", maps=["nope"]), "an unknown map")):
        check(f"atlas: refuses {label}", refused(call))
    single = layouts.export_layout("Carte", folder, "pdf", dpi=72, atlas=True)
    check("atlas: one PDF of every page in a new folder", single["files"] == 1 and single["pages"] == 4 and
          os.path.isdir(single["path"]) and single["path"].endswith("Carte_atlas"), single)
    pngs = layouts.export_layout("Carte", folder, "png", dpi=72, atlas=True)
    check("atlas: one image per feature, in another new folder", pngs["files"] >= 4 and
          pngs["path"].endswith("Carte_atlas_2") and
          len([name for name in os.listdir(pngs["path"]) if name.endswith(".png")]) == 4, pngs)
    named = layouts.set_atlas("Carte", "communes", filter_expression="\"pop\" > 300", file_name="\"nom\"")
    pdfs = layouts.export_layout("Carte", folder, "pdf", dpi=72, atlas=True, single_file=False)
    check("atlas: one PDF per feature, named by file_name", named["pages"] == 4 and pdfs["files"] == 4 and
          "Commune 07.pdf" in os.listdir(pdfs["path"]), os.listdir(pdfs["path"]))
    saved = layouts.MAX_ATLAS_PAGES
    layouts.MAX_ATLAS_PAGES = 2
    check("atlas: refuses more pages than the bound", refused(
        lambda: layouts.export_layout("Carte", folder, "pdf", atlas=True)))
    layouts.MAX_ATLAS_PAGES = saved

    effects = recorder.finish()
    check("atlas: the turn keeps the layout before and after", [effect[0] for effect in effects] == ["layout_state"],
          [effect[0] for effect in effects])
    done, left = apply_effects(effects, undo=True)
    back = project.layoutManager().layoutByName("Carte")
    check("atlas: undo puts the layout back without it", not left and back is not None and
          not back.atlas().enabled(), (done, left))
    done, left = apply_effects(effects, undo=False)
    again = project.layoutManager().layoutByName("Carte")
    check("atlas: redo brings it back", not left and again.atlas().enabled() and
          again.atlas().coverageLayer() is not None and again.atlas().coverageLayer().id() == layer.id(), (done, left))
    # --- edit_layout, all or nothing, undone with the turn
    again.atlas().setEnabled(True)
    main_ref = next(item["ref"] for item in layouts.describe_layout("Carte")["items"] if item["type"] == "map")
    before_count = len(layouts.describe_layout("Carte")["items"])
    refused_all = refused(lambda: layouts.edit_layout("Carte", [
        {"do": "add_text", "text": "x"}, {"do": "remove", "ref": "nope"}]))
    check("edit: a change refused leaves the layout as it was", refused_all and
          len(layouts.describe_layout("Carte")["items"]) == before_count)
    layout_now = project.layoutManager().layoutByName("Carte")
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("e1", "edit_layout", {"layout": "Carte"}))
    edited = layouts.edit_layout("Carte", [
        {"do": "add_text", "text": "Commune : [% \"nom\" %]", "font_size": 16, "x": 20, "y": 30, "width": 120,
         "height": 10},
        {"do": "add_map", "overview_of": main_ref, "x": 217, "y": 24, "width": 70, "height": 50},
        {"do": "add_table", "layer": "communes", "columns": ["nom", "pop"], "max_rows": 5, "x": 20, "y": 150,
         "width": 100, "height": 40},
        {"do": "add_shape", "x": 5, "y": 5, "width": 10, "height": 10},
        {"do": "add_page"}])
    kinds = [item["type"] for item in layouts.describe_layout("Carte")["items"]]
    check("edit: text, map of situation, table, frame and page added", [row["do"] for row in edited["done"]] == [
        "add_text", "add_map", "add_table", "add_shape", "add_page"] and edited["pages"] == 2 and
        kinds.count("map") == 2 and "table" in kinds and "shape" in kinds, (edited, kinds))
    overview = [item for item in layout_now.items() if type(item).__name__ == "QgsLayoutItemMap"
                and item.overviews().size() > 0] if layout_now is project.layoutManager().layoutByName("Carte") else []
    check("edit: the map of situation shows the frame of the main map", len(overview) == 1)
    text_ref, shape_ref = edited["done"][0]["ref"], edited["done"][3]["ref"]
    moved = layouts.edit_layout("Carte", [
        {"do": "move", "ref": text_ref, "x": 40, "y": 15, "page": 2},
        {"do": "set_text", "ref": text_ref, "text": "Atlas des communes"},
        {"do": "set_map", "ref": main_ref, "scale": 50000},
        {"do": "remove", "ref": shape_ref}])
    rows = {item["ref"]: item for item in layouts.describe_layout("Carte")["items"]}
    check("edit: moved to page 2, its text set, the map at 1:50 000, the frame removed",
          rows[text_ref]["page"] == 2 and rows[text_ref]["x_mm"] == 40.0 and
          rows[text_ref]["text"] == "Atlas des communes" and shape_ref not in rows and
          rows[main_ref]["scale"] == 50000, (moved, rows.get(text_ref), rows.get(main_ref)))
    effects = recorder.finish()
    check("edit: the turn keeps the layout before and after", [effect[0] for effect in effects] == ["layout_state"])
    done, left = apply_effects(effects, undo=True)
    check("edit: undo takes every change back", not left and
          len(layouts.describe_layout("Carte")["items"]) == before_count, (done, left))
    apply_effects(effects, undo=False)
    check("edit: redo brings them back", len(layouts.describe_layout("Carte")["pages"]) == 2)

    # --- a template of the profile
    from qgis.core import QgsReadWriteContext
    folder_templates = os.path.join(QgsApplication.qgisSettingsDirPath(), "composer_templates")
    os.makedirs(folder_templates, exist_ok=True)
    project.layoutManager().layoutByName("Carte").saveAsTemplate(
        os.path.join(folder_templates, "Modele communes.qpt"), QgsReadWriteContext())
    check("template: listed", "Modele communes" in layouts.describe_layout("")["templates"],
          layouts.describe_layout("")["templates"])
    made = layouts.create_layout("Depuis modele", template="Modele communes", extent_layer="communes")
    from_template = layouts.describe_layout("Depuis modele")
    check("template: a layout made from it, its pages and items", len(from_template["pages"]) == 2 and
          "table" in made["items"] and made["extent_from"] == "layer", made)
    check("template: refuses an unknown one", refused(lambda: layouts.create_layout("x", template="nope")))

    off = layouts.set_atlas("Carte", enabled=False)
    check("atlas: turned off", off == {"layout": "Carte", "atlas": False} and
          not project.layoutManager().layoutByName("Carte").atlas().enabled(), off)
    check("export: an atlas turned off is refused", refused(lambda: layouts.export_layout("Carte", folder, atlas=True)))


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_layouts"], False)
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
