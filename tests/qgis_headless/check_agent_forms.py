"""Forms and relations of the agent in a real (headless) QGIS: every widget of set_form on a GeoPackage layer, read
back as QGIS keeps it (widget, alias, constraints, default, read only), the refusals and all or nothing, a relation
added and removed, relation_reference on its child field, and the undo and redo of both with the turn.

    docker run --rm -v "$PWD":/src -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \\
        sh -c 'cd /tmp && xvfb-run -a python3 /src/tests/qgis_headless/check_agent_forms.py'

Prints one PASS / FAIL line per check; exits with 1 when one failed.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (  # noqa: E402
    QgsApplication, QgsFeature, QgsField, QgsFieldConstraints, QgsFields, QgsGeometry, QgsProject, QgsRectangle,
    QgsVectorFileWriter, QgsVectorLayer,
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
        if words not in str(exc):
            print(f"     refused, but said: {exc}")
        return words in str(exc)
    return False


def write_gpkg(path, name, geometry, fields, rows):
    definition = QgsFields()
    for field_name, kind in fields:
        definition.append(QgsField(field_name, kind))
    memory = QgsVectorLayer(f"{geometry}?crs=EPSG:2154", name, "memory")
    memory.dataProvider().addAttributes(definition.toList())
    memory.updateFields()
    features = []
    for index, values in enumerate(rows):
        feature = QgsFeature(memory.fields())
        x, y = 600000 + index * 5000, 6280000
        feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + 4000, y + 4000)) if geometry == "Polygon"
                            else QgsGeometry.fromWkt(f"POINT({x + 2000} {y + 2000})"))
        feature.setAttributes(values)
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = name
    QgsVectorFileWriter.writeAsVectorFormatV2(memory, path, QgsProject.instance().transformContext(), options)
    return QgsVectorLayer(path, name, "ogr")


def main():
    from filter_mate.adapters.agent.turn_effects import EffectsRecorder, apply_effects
    from filter_mate.adapters.public_api import forms
    from filter_mate.core.agent.messages import ToolCallPart
    work = tempfile.mkdtemp()
    project = QgsProject.instance()
    communes = write_gpkg(os.path.join(work, "communes.gpkg"), "communes", "Polygon",
                          [("insee", QVariant.String), ("nom", QVariant.String)],
                          [["31555", "Toulouse"], ["31395", "Muret"]])
    usages = write_gpkg(os.path.join(work, "usages.gpkg"), "usages", "Point",
                        [("code", QVariant.String), ("libelle", QVariant.String)],
                        [["R", "Résidentiel"], ["C", "Commercial"]])
    batiments = write_gpkg(os.path.join(work, "batiments.gpkg"), "batiments", "Point",
                           [("statut", QVariant.Int), ("usage", QVariant.String), ("hauteur", QVariant.Double),
                            ("etages", QVariant.Int), ("construit", QVariant.Date), ("vu", QVariant.DateTime),
                            ("habite", QVariant.Bool), ("note", QVariant.String), ("uid", QVariant.String),
                            ("insee_com", QVariant.String), ("surface", QVariant.Double)],
                           [[1, "R", 12.5, 3, None, None, True, "", "a1", "31555", 0.0]])
    project.addMapLayers([communes, usages, batiments])
    fields = batiments.fields()
    check("fixture valid", communes.isValid() and usages.isValid() and batiments.isValid()
          and fields.lookupField("construit") >= 0, [field.typeName() for field in fields])

    def setup(name):
        return batiments.editorWidgetSetup(fields.lookupField(name))

    def constraints(name):
        return batiments.fields().at(fields.lookupField(name)).constraints()

    constraint, strength = QgsFieldConstraints.Constraint, QgsFieldConstraints.ConstraintStrength

    # --- refusals, all or nothing
    before = forms._vector("batiments", "layer")
    check("an unknown layer is refused", refused(lambda: forms.set_form("nope", [{"field": "a"}]), "not found"))
    check("an unknown field is refused, nothing changed", refused(lambda: forms.set_form("batiments", [
        {"field": "note", "alias": "Note"}, {"field": "inconnu", "alias": "X"}]), "no field 'inconnu'")
        and before.attributeAlias(fields.lookupField("note")) == "")
    check("a widget unsuited to its field is refused", all(refused(call, words) for call, words in (
        (lambda: forms.set_form("batiments", [{"field": "usage", "widget": "range", "min": 0}]), "number field"),
        (lambda: forms.set_form("batiments", [{"field": "note", "widget": "date"}]), "date or datetime"),
        (lambda: forms.set_form("batiments", [{"field": "hauteur", "widget": "checkbox"}]), "boolean or integer"),
        (lambda: forms.set_form("batiments", [{"field": "statut", "widget": "value_map", "values": ["1", "x"]}]),
         "no integer number"),
        (lambda: forms.set_form("batiments", [{"field": "etages", "widget": "range", "min": 0.5}]), "whole numbers"),
        (lambda: forms.set_form("batiments", [{"field": "usage", "values": ["R"]}]), "goes with the widget"),
    )))
    check("an expression that does not parse, or a text without quotes, is refused", refused(
        lambda: forms.set_form("batiments", [{"field": "hauteur", "expression": '"hauteur" >= '}]), "no QGIS")
        and refused(lambda: forms.set_form("batiments", [{"field": "note", "default": "Toulouse"}]), "single quotes"))
    check("a lookup layer or field missing is refused", refused(lambda: forms.set_form("batiments", [
        {"field": "usage", "widget": "value_relation", "layer": "usages", "key": "codes"}]), "no field 'codes'")
        and refused(lambda: forms.set_form("batiments", [
            {"field": "usage", "widget": "value_relation", "layer": "absente", "key": "code"}]), "not found"))
    check("relation_reference without a relation is refused", refused(lambda: forms.set_form("batiments", [
        {"field": "insee_com", "widget": "relation_reference"}]), "add one with relations first"))
    check("after every refusal, the form is as it was", setup("usage").type() in ("", "TextEdit")
          and setup("hauteur").type() in ("", "TextEdit") and not batiments.attributeAlias(fields.lookupField("note")))

    # --- every widget, read back, undone and applied again with the turn
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("f1", "set_form", {"layer": "batiments"}))
    answer = forms.set_form("batiments", [
        {"field": "statut", "widget": "value_map", "values": [{"value": "1", "label": "En service"},
                                                               {"value": "2", "label": "En ruine"}]},
        {"field": "usage", "widget": "value_relation", "layer": "usages", "key": "code", "value": "libelle",
         "alias": "Usage"},
        {"field": "hauteur", "widget": "range", "min": 0, "max": 300, "step": 0.5, "alias": "Hauteur (m)",
         "not_null": True, "expression": '"hauteur" >= 0', "constraint_text": "positive", "enforce": True},
        {"field": "etages", "widget": "range", "min": 0, "max": 60},
        {"field": "construit", "widget": "date", "format": "dd/MM/yyyy"},
        {"field": "vu", "widget": "date", "default": "now()", "default_on_update": True},
        {"field": "habite", "widget": "checkbox"},
        {"field": "note", "widget": "text", "multiline": True, "unique": True},
        {"field": "uid", "widget": "hidden"},
        {"field": "surface", "default": "$area", "editable": False},
    ])
    check("set_form answers each field", [row["field"] for row in answer["fields"]][:3] == ["statut", "usage",
                                                                                             "hauteur"], answer)
    check("value_map: a list of {label: value}", setup("statut").type() == "ValueMap" and
          setup("statut").config()["map"] == [{"En service": "1"}, {"En ruine": "2"}], setup("statut").config())
    relation_config = setup("usage").config()
    check("value_relation: the lookup layer and its fields", setup("usage").type() == "ValueRelation" and
          relation_config["Layer"] == usages.id() and (relation_config["Key"], relation_config["Value"]) ==
          ("code", "libelle"), relation_config)
    check("range: bounds, step and precision", setup("hauteur").type() == "Range" and
          (setup("hauteur").config()["Min"], setup("hauteur").config()["Max"], setup("hauteur").config()["Step"],
           setup("hauteur").config()["Precision"]) == (0.0, 300.0, 0.5, 1) and setup("etages").config()["Max"] == 60,
          setup("hauteur").config())
    check("date: shown as asked, stored as the field holds it", setup("construit").type() == "DateTime" and
          setup("construit").config()["display_format"] == "dd/MM/yyyy" and
          setup("vu").config()["field_format"] == "yyyy-MM-dd HH:mm:ss", setup("vu").config())
    check("checkbox, text, hidden", (setup("habite").type(), setup("note").type(), setup("uid").type()) ==
          ("CheckBox", "TextEdit", "Hidden") and setup("note").config()["IsMultiline"] is True)
    check("aliases", batiments.attributeAlias(fields.lookupField("hauteur")) == "Hauteur (m)")
    hauteur = constraints("hauteur")
    check("enforced: not null and the expression are hard, with its text",
          hauteur.constraintStrength(constraint.ConstraintNotNull) == strength.ConstraintStrengthHard and
          hauteur.constraintExpression() == '"hauteur" >= 0' and hauteur.constraintDescription() == "positive" and
          hauteur.constraintStrength(constraint.ConstraintExpression) == strength.ConstraintStrengthHard)
    check("without enforce: unique is soft", constraints("note").constraintStrength(constraint.ConstraintUnique) ==
          strength.ConstraintStrengthSoft and "soft" in answer["note"], answer["note"])
    default = batiments.defaultValueDefinition(fields.lookupField("vu"))
    check("default values and on update", default.expression() == "now()" and default.applyOnUpdate() and
          batiments.defaultValueDefinition(fields.lookupField("surface")).expression() == "$area")
    check("editable false: read only in the form", batiments.editFormConfig().readOnly(fields.lookupField("surface"))
          and not batiments.editFormConfig().readOnly(fields.lookupField("note")))
    check("nothing written to the data", batiments.featureCount() == 1 and not batiments.isModified())
    effects = recorder.finish()
    check("the turn keeps one form effect", [effect[0] for effect in effects] == ["form"], effects)
    done, left = apply_effects(effects, undo=True)
    check("undo puts the form back", not left and setup("statut").type() in ("", "TextEdit") and
          not batiments.attributeAlias(fields.lookupField("hauteur")) and
          not batiments.defaultValueDefinition(fields.lookupField("vu")).expression() and
          not constraints("hauteur").constraintExpression() and
          not batiments.editFormConfig().readOnly(fields.lookupField("surface")), (done, left))
    apply_effects(effects, undo=False)
    check("redo sets it again", setup("statut").type() == "ValueMap" and
          batiments.attributeAlias(fields.lookupField("hauteur")) == "Hauteur (m)" and
          constraints("hauteur").constraintStrength(constraint.ConstraintNotNull) == strength.ConstraintStrengthHard
          and batiments.editFormConfig().readOnly(fields.lookupField("surface")))
    forms.set_form("batiments", [{"field": "hauteur", "alias": "", "not_null": False, "expression": ""},
                                 {"field": "statut", "widget": "default"}])
    check('"" and false remove; default lets QGIS choose', not batiments.attributeAlias(fields.lookupField("hauteur"))
          and not constraints("hauteur").constraintExpression() and setup("statut").type() in ("", "TextEdit") and
          not constraints("hauteur").constraints() & constraint.ConstraintNotNull, setup("statut").type())

    # --- relations
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("r1", "relations", {"action": "add"}))
    added = forms.relations("add", parent_layer="communes", parent_field="insee", child_layer="batiments",
                            child_field="insee_com", strength="composition")
    manager = project.relationManager()
    relation = manager.relation(added["relation"]["id"])
    check("a relation added: valid, its id returned, composition", relation.isValid() and
          added["relation"]["strength"] == "composition" and added["relation"]["fields"] ==
          [{"parent": "insee", "child": "insee_com"}], added)
    check("the parent's form shows its children", [item.id() for item in manager.referencedRelations(communes)] ==
          [relation.id()])
    check("a relation twice, or a field missing, is refused", refused(lambda: forms.relations(
        "add", parent_layer="communes", parent_field="insee", child_layer="batiments", child_field="insee_com"),
        "already linked") and refused(lambda: forms.relations(
            "add", parent_layer="communes", parent_field="code", child_layer="batiments", child_field="insee_com"),
            "no field 'code'"))
    check("list", [row["id"] for row in forms.relations("list")["relations"]] == [relation.id()])
    recorder.before_call(ToolCallPart("f2", "set_form", {"layer": "batiments"}))
    forms.set_form("batiments", [{"field": "insee_com", "widget": "relation_reference", "alias": "Commune"}])
    check("relation_reference on the child field", setup("insee_com").type() == "RelationReference" and
          setup("insee_com").config()["Relation"] == relation.id(), setup("insee_com").config())
    effects = recorder.finish()
    check("the turn keeps the relation added and the form", sorted(effect[0] for effect in effects) ==
          ["form", "relation"] and any(effect[3] == "added" for effect in effects if effect[0] == "relation"),
          [effect[:1] + effect[3:4] for effect in effects])
    done, left = apply_effects(effects, undo=True)
    check("undo removes the relation and the widget", not left and not manager.relations() and
          setup("insee_com").type() in ("", "TextEdit"), (done, left))
    apply_effects(effects, undo=False)
    check("redo adds them again", manager.relation(relation.id()).isValid() and
          setup("insee_com").type() == "RelationReference")

    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("r2", "relations", {"action": "remove", "name": relation.name()}))
    removed = forms.relations("remove", name=relation.name())
    check("remove by name, with a word on the widget left", not manager.relations() and
          removed["removed"]["id"] == relation.id() and "insee_com" in removed.get("note", ""), removed)
    effects = recorder.finish()
    done, left = apply_effects(effects, undo=True)
    check("undo brings the relation removed back", not left and manager.relation(relation.id()).isValid() and
          manager.relation(relation.id()).strength() == forms._strengths()["composition"], (done, left))
    apply_effects(effects, undo=False)
    check("redo removes it again", not manager.relations())
    check("remove of an unknown relation is refused", refused(lambda: forms.relations("remove", name="nope"),
                                                              "no relation 'nope'"))

    # --- a field added in the edit buffer and given a widget in the same turn
    from filter_mate.adapters.public_api import fields_joins
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("a1", "add_field", {"layer": "batiments"}))
    fields_joins.add_field("batiments", "etat", "text")
    recorder.before_call(ToolCallPart("f3", "set_form", {"layer": "batiments"}))
    forms.set_form("batiments", [{"field": "etat", "widget": "value_map", "values": ["neuf", "ancien"]}])
    effects = recorder.finish()

    def etat():
        index = batiments.fields().lookupField("etat")
        return batiments.editorWidgetSetup(index).type() if index >= 0 else None
    check("a new field gets its widget", etat() == "ValueMap" and sorted(effect[0] for effect in effects) ==
          ["edits", "form"], [effect[0] for effect in effects])
    # As TurnCheckpoint undoes a turn: the edits first, then the rest.
    apply_effects(effects, undo=True, presence=False, edits=True)
    done, left = apply_effects(effects, undo=True, presence=False, edits=False)
    check("undo: the field goes, the form is put back", etat() is None and not left, (done, left))
    apply_effects(effects, undo=False)
    check("redo: the field and its widget come back", etat() == "ValueMap", etat())
    batiments.rollBack()

    # --- a relation the turn added, then took away with a layer it removed: an undo does not make it
    recorder = EffectsRecorder()
    recorder.before_call(ToolCallPart("r3", "relations", {"action": "add"}))
    forms.relations("add", parent_layer="communes", parent_field="insee", child_layer="usages", child_field="code")
    recorder.before_call(ToolCallPart("d1", "remove_layers", {"layers": ["usages"]}))
    project.removeMapLayer(usages.id())
    effects = recorder.finish()
    check("the turn keeps the layer removed, not the relation", [effect[0] for effect in effects] == ["removed"],
          [effect[0] for effect in effects])
    apply_effects(effects, undo=True)
    check("undo brings the layer back without the relation", project.mapLayersByName("usages") and
          not manager.relations(), list(manager.relations()))


if __name__ == "__main__":
    app = QgsApplication([b"check_agent_forms"], False)
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
