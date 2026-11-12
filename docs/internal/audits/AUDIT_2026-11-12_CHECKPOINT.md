# Point d'étape — Audit profond du 12/11/2026 (régressions depuis v5.0.2)

**Date** : 2026-11-12, fin de journée (2ᵉ version du point d'étape)
**Référence** : `v5.0.2` (06/11) → `main`. 279 commits entre les deux au début de l'audit.
**État** : 11 PR de l'audit fusionnées (#356 → #370). Une branche est en vérification : `claude/audit-engine-followup`.

---

## Contexte

- **CI.** Les workflows GitHub « Tests » et « QGIS headless » sont **désactivés volontairement** depuis le 27/10, et Simon a confirmé le 12/11 qu'ils le restent.
- **Vérification qui remplace la CI** avant chaque fusion :
  - la suite complète locale, lancée dans un dossier nommé `filter_mate` : `python3 -m pytest tests/ -o "addopts=" -p no:cacheprovider -q` ;
  - flake8 avec la configuration de la CI ;
  - pour les lots qui touchent QGIS, les contrôles `tests/qgis_headless/*.py` dans le QGIS 3.44.6 Windows : `python-qgis.bat` appelé par un `.bat` depuis `cmd.exe`.
- **Référence de la suite sur `main`** : 5 échecs connus.
  - 4 dans `test_expression_builder.py` (PostgreSQL et Spatialite), causés par le double chargement de `filtermate_core` sous pytest (voir « Restes »).
  - `test_coverage_raster_target.py::TestSourceClipVrt::test_canceled_selection_is_not_read`.
- **Méthode.**
  - 8 revues Opus en lecture seule, une par zone.
  - Des lots de correctifs, chacun dans son worktree.
  - Une fusion dès que la suite passe (merge commit), une revue Opus en parallèle, et ses retours en PR de suivi.
- **Sessions parallèles.** D'autres sessions travaillaient en même temps sur la traduction native (#373, mode hybride) et sur PostgreSQL (#355, #357, #358, #363, #368).
  - Le checkout principal `/home/simon/projects/filter_mate` est l'arbre de travail de la session de la traduction native.
  - **Ne jamais y faire checkout / pull / stash / reset.** Travailler dans `.claude/worktrees/…` ; `git fetch` suffit pour voir `main`.

## Décisions prises par Simon pendant l'audit

1. **`AND NOT` sans filtre existant** donne `NOT (expr)`, c'est-à-dire toute la couche moins la sélection, partout : dock, API, agent, cœur. Fait dans #365 ; le suivi en cours corrige le cas d'un filtre précédent remplacé.
2. **Couches protégées de l'agent** : la protection vaut aussi pour l'API REST et le serveur MCP adossé au REST (403). Fait dans #361 et #369.
3. **CI** : rester désactivée.
4. **Cibles raster / LiDAR d'une source vecteur.**
   - Deux options dédiées, activées par défaut, et les fonds de plan web (WMS / XYZ) grisés avec une explication. Fait dans #370.
   - Le **masque des fonds web hors de la géométrie source** fera l'objet d'une PR séparée, plus tard. Mécanisme proposé : groupe rendu comme une couche avec un masque « Destination In », QGIS ≥ 3.24.
5. **Fusionner au fur et à mesure**, sans attendre la revue, avec des PR de suivi.

## Fusionné dans `main`

| PR | Lot | Contenu |
|---|---|---|
| #356 | sanitizer + rechargement | **Critique, régression de #354.** Un subset natif SQLite `COALESCE(...) GLOB` ou `NOT ("nom d'usage" GLOB …)` était effacé par le sanitizer, et la couche affichait tout sans message. Contournement S3 par un guillemet dans un commentaire. Libération des alias des shims et des modules que QGIS ne suit pas au déchargement. `ET.indent` (Python 3.8). |
| #359 | cycle de vie AGENT / dock | SAM, la pipette et Zone quittent la carte à la fermeture du dock. Les tours de l'agent qui ont des effets survivent au retrait d'une couche. Annuler / Rétablir de l'agent avec un raster actif. Un moteur n'est lâché qu'une fois fini. Pas de faux tour au changement de projet. Stop ne coupe pas les clients MCP. Pas de `featureCount` des services web sur le thread GUI. |
| #360 | lectures gardées | Correctif du plantage #349 (QGIS 4.2.2 Windows) étendu aux deux appelants qui l'avaient raté. |
| #361 | gardes | `cross_filter` qui modifie sa source, `apply_filter` par id, Processing en liste d'acceptation de types (IDW / TIN ouvraient n'importe quel chemin ou URL), protection appliquée au REST, règles « ask » / « never » dans le MCP natif, échec fermé, `sql_guard`, `readOnlyHint`. |
| #362 | segmentation | Fenêtres SAM lues sur le provider seul, avec les réglages de la couche (plus de lecture complète d'une couverture WCS). Réutilisation de la fenêtre loin du bord seulement, scène nettoyée, planification sur grille, nuages bornés, onnxruntime. QGIS 3.44.6 : 153 contrôles, 0 échec. |
| #364 | suivi de #360 | Curseur d'attente, Identifier après une lecture remplacée, `addTask` qui lève, parent du récepteur. |
| #365 | moteur | Une source qui ne garde rien ne filtre plus les cibles par toute la source. Export par id. `AND NOT` → `NOT (x)`. Éditions de l'agent sans mode édition laissé ouvert. Style NaN / Inf. Export de mise en page. SEGMENTS. Tests de fumée en QGIS 3.44.6 identiques à `main`. |
| #366 | interface AGENT | Plage exacte : avant, elle arrondissait à 2 décimales, d'où des filtres faux. Flux regroupé : 246 s → 16 s de thread GUI pour 12 000 caractères. Bande des widgets. Graphiques bornés. Infobulles en texte brut. |
| #367 | suivi de #359 | Les outils des panneaux se passent l'outil qu'ils ont remplacé (Zone / SAM). `abort_active` et le checkpoint MCP jetés au changement de projet. `forget_layer` avec un effet `added`. |
| #369 | suivi de #361 | Un id trouve sa couche ou rien. Référence vide contrôlée. `map_theme apply` sur une couche protégée refusé. Couches jointes à une couche retirée. Entrée protégée illisible. Undo de l'agent. Bornes IDW. `sql_guard` ASCII. |
| #370 | options de cibles | `vector_source_raster_targets` / `vector_source_point_cloud_targets`. Fonds web grisés et non cochables. Rafraîchissement qui garde exactement les coches de l'utilisateur. |

**Traductions** : les nouvelles chaînes de #359, #369 et #370 sont dans les 34 `.ts`, mais **les `.qm` ne sont pas recompilés** (voir « Restes »).

## En vérification

`claude/audit-engine-followup` : suivi de #365 après sa revue, qui avait trouvé des résultats faux en silence.
- **`AND NOT` après un filtre remplacé** : avec une liste de clés précédente, vraie combinaison `(clés) AND NOT (nouveau)` ; avec un filtre spatial ou de style précédent, `NOT (nouveau)`. Avant, le second `AND NOT` gardait ce qu'il devait retirer.
- **Repli liste d'ids de la source** : même règle.
- **OGC API Features** : refuse `AND NOT` sans filtre.
- **Expression « style »** réduite à `coalesce(champ, 'texte')`. #365 remplaçait en silence `regexp_match(...)`, une colonne booléenne, etc.
- **Source vide** : la nouvelle sélection est lue telle qu'écrite, et un refus ne filtre plus rien.
- **SpatiaLite** : `prédicat = 1`, pour qu'une géométrie NULL ne soit plus gardée selon la présence d'un index R-tree.
- **Points mineurs** : export GeoPackage avec des noms de table uniques, `NOT (\nx\n)`, PNG multipage.
- **Vérification en cours** : suite complète et tests de fumée moteur en QGIS 3.44.6, dans `.claude/worktrees/audit3/filter_mate` (`verify/engine-followup`). `main` a reçu entre-temps #373 (traduction native, mode hybride) : à refusionner avant de pousser.

## Restes connus (non traités)

**Traduction (`.qm`).**
- Pas de `lrelease` dans le QGIS Windows, ni sur le Linux. L'installation de `qt5-applications` par pip a été refusée par le mode automatique.
- Deux voies possibles : démarrer Docker Desktop et utiliser l'image `qgis/qgis`, comme le prévoit le dépôt ; ou autoriser `qt5-applications`. **En attente du choix de Simon.**
- Les deux chaînes du contexte `SourceSelection` (#365, `adapters/backends/source_refusal.py`, déclaré dans `FilterMate.pro`) ne sont pas encore dans les `.ts`. Le contexte n'existe pas, donc `scripts/i18n_add_message.py` ne suffit pas : une passe `pylupdate5` + `scripts/i18n_processing_context.py` + `scripts/i18n_runtime_contexts.py` est nécessaire.

**Traduction native** (transmis à la session concernée ; #373 en a peut-être traité une partie) :
- moins unaire sur un NULL : QGIS rend 0, SQLite / OGR rendent NULL ;
- `NOT` au-dessus d'une sortie OGR SQL qui contient un AND (`TRUE AND NULL` = `FALSE`) ;
- réels arrondis par SQLite ;
- sémantique OGR mesurée sur GDAL 3.12 / 3.13 seulement ;
- `attribute_filter_executor.py` court-circuite sans ancien subset : la règle `AND NOT` est appliquée en amont, dans `ExpressionFacadeHandler`, et reste à aligner dans ce fichier.

**Moteur** :
- **Encore des remplacements** : un filtre spatial précédent est remplacé (`NOT (nouveau)`), pas combiné en « ancien moins nouveau » ; en mode SUBSET avec un ancien subset non vide, la source reste les entités de l'ancien subset quelle que soit x.
- **Après un refus** : pour une source PostgreSQL, l'historique a peut-être été écrit avant le refus ; une liste de clés combinée peut dépasser la limite d'un Shapefile.
- **Bugs anciens** (revue du 12/11) : en mode remplacement, les cibles sont filtrées par « ancien ∧ nouveau » ; pas de repli quand le fournisseur refuse le SQL natif ; marge R-tree convertie dans le mauvais SCR ; `_set_query_timeout` inefficace ; clé `ctid` ; clés composites ; « EMERGENCY FALLBACK » de `geometry_preparer`.

**Export** : la liste d'export propose les fonds de plan web (WMS / XYZ) comme rasters cochables, ce qui n'a pas de sens pour eux.

**Cycle de vie** : un filtre fait dans le dock pendant un tour de l'agent est rangé dans ce tour et annulé avec lui. Le correctif sûr demande d'identifier positivement les filtres du dock.

**Cœur extrait** :
- double chargement de `filtermate_core` sous pytest : il cause les 4 échecs connus et des tests qui passent peut-être pour de mauvaises raisons ;
- repli relatif → absolu des adaptateurs sans la garde des shims ;
- `combined_query_optimizer` (chemin mort) ;
- seulement 6 SRID géographiques reconnus par défaut dans le cœur PostgreSQL.

**Qt6** : le garde-fou `scripts/qt_enum_scan.py` est une liste blanche qui ne vérifie pas l'existence des membres. Piste : introspection PyQt6.

**API / agent, faibles** :
- SSRF : nom d'hôte contrôlé mais pas l'adresse résolue ;
- chemins absolus renvoyés par `/export` ;
- `findGroup` avec des groupes de même nom ;
- téléchargements `open_data` jamais nettoyés ;
- style gradué sans plafond ;
- `_unless_busy` absent pour le style et les mises en page ;
- `native:exportlayersinformation` ;
- recettes qui rejouent des ids intermédiaires ;
- `apply_effects` sans contrôle « modifié depuis » ;
- `undo_to_step` qui ne restaure que les filtres ;
- séparateur SSE coupé dans `bounded_http` ;
- `qt_transport` (dialogue TLS de QGIS).

**Segmentation** : la relecture à 1 m d'un nuage peut encore geler QGIS 10 à 15 s sur le thread GUI (sous 200 000 points). La placer dans une tâche demande un rafraîchissement différé dans `coverage_mode_controller.py`.

**Tests** :
- pollution entre tests selon l'ordre (`tests/unit/adapters/backends` lancé d'un bloc, `test_source_union_semantics.py[...$id]` qui échoue seul sur `main`, `test_centroid_targets_sync`, `test_public_api.py`) ;
- `test_mv_references_all_layers` lancé seul.

**À vérifier dans un vrai QGIS** (les tests des lots sont sur mocks) :
- #349 sous QGIS 4.2.2 Windows : Filtrer ou Identifier pendant le chargement d'une sélection WFS ;
- fermeture du dock avec SAM, la pipette ou Zone actifs ;
- les 403 du REST avec le MCP stdio ;
- la ligne grisée des fonds web sous Qt5 et Qt6, en thème clair et sombre ;
- `AND NOT` sans filtre et après un filtre sur PostgreSQL, Spatialite, OGR, raster et nuage ;
- le refus d'une source qui ne garde rien, sur GeoPackage et Shapefile.

## Reprendre

- **Worktrees** (dans le dépôt, sous `.claude/worktrees/`) :
  - `audit/filter_mate`, `audit2/filter_mate`, `audit3/filter_mate` : intégration et vérification ;
  - `agent-<id>` : un par lot.
- **Flux d'un lot.**
  1. `git checkout -B verify/<lot> <branche>`, puis `git merge origin/main`.
  2. Conflits du CHANGELOG et de `.claude/memory.md` : garder les deux côtés avec `.claude/worktrees/audit/tools/union_conflicts.py <fichier>`.
  3. **Si la branche modifie des entrées existantes**, vérifier ensuite qu'aucune n'est en double dans la section `[Unreleased]` (le cas s'est produit une fois ; corrigé).
  4. Suite complète, puis `git push origin verify/<lot>:<branche>`, `gh pr create`, `gh pr merge --merge`.
- **Sorties des suites et essais des relecteurs** : `.claude/worktrees/audit/out/`. Ces fichiers sont locaux et non versionnés.
- **Pièges rencontrés.**
  - Sous zsh, `"$var:refs/..."` applique le modificateur `:r` : écrire `"${var}:refs/..."`.
  - Une variable non quotée n'est pas découpée en mots sous zsh : écrire `${=var}`.
  - Le redémarrage de WSL vide `/tmp`.
  - Sous forte charge, l'interopérabilité vers Windows expire par PowerShell : passer par `cmd.exe` et un `.bat`.
