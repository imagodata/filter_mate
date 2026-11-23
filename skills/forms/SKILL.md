---
name: forms
title: Forms and relations for data entry
description: data entry: form widgets, constraints, relations
metadata:
  version: 1
  plugin_min: 5.1.2
  audience: chat, mcp
  tools: describe_layer, field_values, list_layers, set_form, relations, add_field
  risk: change
  trust: builtin
---

# Forms and relations for data entry

The attribute form is what QGIS shows to whom adds or edits a feature. set_form chooses, field by field, its widget,
its alias, its constraints, its default value and whether it can be edited. relations links a child layer to a
parent layer by a field. Neither changes the data; both are properties of the project.

## Method

1. describe_layer on each layer first: its fields with their types, its relations. field_values on a field shows the
   codes it holds.
2. The widget from what the field holds:
   - a few fixed codes (a status, a type, a usage): value_map, values as texts, or {value, label} when the codes
     say little ("R" shown as "Résidentiel");
   - codes kept in another table (a lookup table, the list of communes): value_relation with layer (that table),
     key (its field stored here) and value (its field shown);
   - a bounded number (a height, floors, a percentage): range with min, max and step;
   - a date or datetime field: date, with format as the user reads it (dd/MM/yyyy);
   - a boolean, or an integer holding 0 and 1: checkbox;
   - a long text (a comment, a description): text with multiline;
   - a technical id, a key nobody types: hidden; a value computed or imported: editable false;
   - back to what QGIS chooses by itself: default.
3. alias in the user's words and language ("Hauteur (m)" for h_m).
4. Constraints: not_null for what must be filled, unique for an identifier, expression for a rule
   ("hauteur" >= 0 AND "hauteur" < 400) with constraint_text saying it in words. They warn and still save (soft);
   set enforce only when the user wants such entries refused, and tell them which constraints are hard.
5. Defaults: an expression, such as now(), @user_account_name, $area, or 'a text' in single quotes;
   default_on_update when the value must follow each edit (the date of the last change, an area).
6. One set_form call per layer with all its fields: it is all or none, so a refusal names the entry to fix and
   nothing changed. "" removes an alias, an expression or a default.

## Relations

- The child holds the key of its parent: buildings hold the INSEE code of their commune (parent_layer communes,
  parent_field insee, child_layer buildings, child_field the field holding that code).
- relations with action add, then set_form with widget relation_reference on the child field: each child picks its
  parent from a list, and the form of the parent lists its children.
- strength composition only when the children cannot exist without their parent (the rooms of a building):
  deleting a parent deletes them. Otherwise association, the default.
- No field for the key yet: add_field first, then the relation.
- relations with action list before removing one; remove it by its id or name.
- A form laid out by hand (the drag and drop designer) shows the children once the user puts the relation in it, in
  the layer properties: say so when describe_layer or the user says the form is drawn by hand.

## What never to do

- Never change features or their values to set up a form: a form changes no data.
- Never make constraints hard without the user asking: a hard constraint refuses to save a feature that breaks it,
  an old one too when it is edited.
- Never use composition for a lookup table (communes, types): deleting one row would delete every feature that
  points to it.
- Never use run_pyqgis for what set_form or relations refuse: tell the user why.
