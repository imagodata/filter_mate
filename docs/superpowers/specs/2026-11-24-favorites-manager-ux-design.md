# Favorites manager: display bugs, readability, theme — design (short)

2026-11-24, with Simon. Approach **A** chosen ("réparer et clarifier la boîte actuelle").

## Why

The favorites manager (`ui/dialogs/favorites_manager.py`, opened from the ★ menu) shows display bugs, and a favorite
cannot be read: what it filters, on which layers, with which spatial settings, and — since favorites travel with the
project (#646) — whether it is shared with everyone who opens the project or stays on this computer. It also ignores
the theme of FilterMate.

## Found (QGIS 3.44, French, captures of 2026-11-24)

1. Emoji icons render as empty boxes (search, scope combo, Save, Delete).
2. The list is 220 px: names cut, a horizontal scroll bar, "• ★" repeated before each name.
3. The selected tab is cut ("Expressior", "Distant (2").
4. The "Visibilité" block overlaps: the radios "Ce projet / Tous les projets" (disabled, "coming soon") run into the
   owner line, itself cut on the right.
5. The description box is one and a half lines high, with a spin arrow.
6. "Utilisé : 0 times" (not translated), "Créé : 2026-11-24T12:14" (raw ISO, cut).
7. Colors are written in the dialog (light background, orange selection): the dark theme is not followed.
8. Readability: the expression is in a tab of its own, the remote layers in another with their expressions cut, and the
   spatial settings (predicates, buffer) the favorite stores are shown nowhere.

## Goals

- Every bug above fixed.
- A readable summary at the top of the details, in plain words:

  ```
  Parcelles A > 20 m²                     [Projet · partagé]
  Filtre parcelles :  "type" = 'A' AND "surface" > 20
  Puis 2 couches   :  troncon_de_route (12) · batiment (5)
  Spatial          :  Intersecte, Dans · tampon 25 m
  Tags : urbanisme, PLU           Utilisé 3 fois · créé le 24/11/2026
  ```

  Expressions in full (wrapped, monospace, selectable), each remote layer with its expression readable (tooltip or
  wrapped row).
- Scope shown as a badge: **Projet · partagé** (in the .qgz, everyone who opens the project) or **Global · ce poste**.
- Deleting a project favorite says it is removed for everyone who opens the project.
- Double-click applies; a context menu on the list (apply, rename, duplicate, delete, copy to global); sorting (name,
  last used, most used).
- The dialog follows the theme of FilterMate (light / dark, `ui/styles/mockup_design.py` TOKENS; icons from
  `IconManager` / QGIS theme icons, no emoji).

## Non-goals

- Stays a modal dialog (a non-modal window may come later).
- No "card" list, no favorites section in the dock.
- No change to how favorites are stored or synced (#646).

## Anti-goals

- A new string not translated in the 34 catalogs (`i18n-pipeline` skill).
- A fix that works in light theme only, or on Qt5 only (QGIS 3.22 → 4.x).

## Decided

- Approach A (Simon). The tabs General and Expression merge into the summary; the remote layers stay a table under it
  (or a tab "Couches" if the height asks for it).
- My calls: the owner radios ("Mine / Shared") and the disabled project/global radios are removed from the details
  ("Mine" is a display filter since #646, kept in the scope combo); the menu entries "Save to project (.qgz)" and
  "Restore from project" go (the project is written at each change since #646); the "Replace all" choice of the
  import either works or goes.

## Left to the builder

Layout details, the wording of new strings (then the 34 catalogs), which bugs of the inventory beyond those above are
cheap enough to fix on the way (silent failures of create/restore, rename to an empty or duplicate name).

## Check

Captures of the dialog in QGIS 3.44 and 4.3, light and dark theme, before / after (the throwaway capture script of
2026-11-24 made a bench: favorites with remote layers, spatial settings, a long name, a global one); unit tests of the
summary text; the GUI smoke still passes.
