# Point d'étape — Audit profond du 12/11/2026 (régressions depuis v5.0.2)

**Date** : 2026-11-12, en cours de session
**Référence** : `v5.0.2` (06/11) → `main`. 279 commits entre les deux au début de l'audit.
**État de `main` à ce point** : `1f502837` (#364)

---

## Contexte

- **CI.** Les workflows GitHub « Tests » et « QGIS headless » sont **désactivés volontairement** depuis le 27/10, et Simon a confirmé le 12/11 qu'ils le restent. Rien de ce qui a été fusionné depuis le 27/10 n'avait donc tourné en CI.
- **Vérification qui remplace la CI** avant chaque fusion :
  - la suite complète locale, lancée dans un dossier nommé `filter_mate` : `python3 -m pytest tests/ -o "addopts=" -p no:cacheprovider -q`, 10 à 30 min selon la charge ;
  - flake8 avec la configuration de la CI : `python3 -m flake8 --extend-exclude=tests,scripts,website,docs --count` ;
  - quand le lot touche QGIS, les contrôles `tests/qgis_headless/*.py` dans le QGIS 3.44.6 Windows (`python-qgis.bat`, à appeler par un `.bat` depuis `cmd.exe` : PowerShell expire sous forte charge).
- **Référence de la suite sur `main`** : 5 échecs connus, rien d'autre.
  - 4 dans `tests/unit/adapters/backends/{postgresql,spatialite}/test_expression_builder.py`. Selon la revue du cœur (point 2 plus bas), ils viennent d'un double chargement de `filtermate_core` sous pytest.
  - 1 dans `test_coverage_raster_target.py::TestSourceClipVrt::test_canceled_selection_is_not_read`.
- **Méthode.**
  - 8 revues Opus en lecture seule, une par zone : cœur extrait et shims, traduction native, moteur, cœur de l'agent, API REST / MCP / publique, contrôleurs et cycle de vie, widgets et Qt5 / Qt6, lectures asynchrones et segmentation.
  - Puis des lots de correctifs, chacun dans son worktree, fusionnés au fur et à mesure (merge commit), avec une revue Opus en parallèle dont les retours partent en PR de suivi.
- **Session parallèle.** Une autre session travaillait en même temps sur la traduction native (branche `claude/native-hybrid-key-lists`, dans l'arbre principal) et sur PostgreSQL (#355, #357, #358, #363). Les trouvailles qui concernent la traduction native lui ont été transmises (voir « Restes »).

## Décisions prises par Simon pendant l'audit

1. **`AND NOT` sans filtre existant** donne `NOT (expr)`, c'est-à-dire toute la couche moins la sélection, partout : dock, API, agent, cœur. Avant, la condition était appliquée telle quelle, donc on gardait exactement ce qu'on voulait exclure. Implémenté dans le lot moteur, pas encore fusionné.
2. **Couches protégées de l'agent** : la protection vaut aussi pour l'API REST et le serveur MCP adossé au REST (403). Fait dans #361.
3. **CI** : rester désactivée.
4. **Cibles raster / LiDAR d'une source vecteur.**
   - Deux options dédiées dans `APP.OPTIONS.CROSS_FILTER`, activées par défaut.
   - Les fonds de plan web (WMS / XYZ) sont affichés grisés avec une explication, au lieu d'être absents sans rien dire. Dans le projet de Simon, OpenStreetMap, UrbIS FR et UrbIS FR Gray étaient écartés en silence parce que ce sont des rasters « rendus ».
   - Le **masque des fonds web hors de la géométrie source** fera l'objet d'une PR séparée, plus tard. Mécanisme proposé : groupe rendu comme une couche avec un masque « Destination In », QGIS ≥ 3.24.
5. **Fusionner au fur et à mesure**, sans attendre la revue, avec des PR de suivi.

## Fusionné dans `main`

| PR | Lot | Contenu |
|---|---|---|
| #356 | sanitizer + rechargement | **Critique, régression de #354.** Un subset natif SQLite `COALESCE(...) GLOB '…'` ou `NOT ("nom d'usage" GLOB '…')` était effacé par le sanitizer, et la couche affichait tout sans message (fuzz : 781 cas sur 20 000 avant, 0 après). Contournement S3 par une apostrophe ou un guillemet dans un commentaire fermé. Au déchargement, libération des 28 alias des shims de `filtermate_core` et des 14 paquets que QGIS ne suit pas : après une mise à jour, l'ancien code tournait jusqu'au redémarrage. `ET.indent` (Python 3.8). |
| #359 | cycle de vie AGENT / dock | Fermer le dock retire SAM, la pipette de classes et l'outil Zone. `forget_layer` garde les opérations qui ont des effets. Annuler / Rétablir de l'agent quand un raster est actif. Un moteur n'est lâché qu'une fois fini. Pas de faux tour au changement de projet. Stop ne coupe plus les clients MCP. Pas de `featureCount` des services web sur le thread GUI. Arrêt en étapes indépendantes. |
| #360 | lectures gardées | Le correctif du plantage #349 (QGIS 4.2.2 Windows) appliqué aux deux appelants qui l'avaient raté (`when_settled` depuis `finished()`). Récepteur pour la couche du cache de sélection. Curseur d'attente compté. |
| #361 | gardes | Un `cross_filter` qui masque ou filtre sa source compte pour la protection. `apply_filter` par id (avec deux couches de même nom, la mauvaise était filtrée). Processing passe à une liste d'acceptation de types : IDW / TIN ouvraient n'importe quel chemin ou URL ; mêmes 187 algorithmes permis, vérifié en QGIS 3.44.6. Protection appliquée au REST (403). Règles « ask » / « never » dans le MCP natif. Protection en échec fermé. `sql_guard` (antislash). `readOnlyHint` des connecteurs ignoré. |
| #362 | segmentation | Fenêtres SAM lues sur le provider seul, avec le SCR, les filtres de rendu et la bande alpha de la couche ; plus de lecture complète d'une couverture WCS. Réutilisation de la fenêtre seulement loin du bord. Nettoyage de la scène. Tâches arrêtées en file. Planification sur grille (148 s → 0,8 s). Nuages : relecture à 1 m bornée, unités du SCR. Installation d'onnxruntime saine. Vérifié en QGIS 3.44.6 : `check_segmentation.py`, 153 contrôles, 0 échec. |
| #364 | suivi de #360 | Les 5 retours de la revue : curseur, Identifier après une lecture remplacée, `addTask` qui lève, parent du récepteur. |

La chaîne de #359 est dans les 34 `.ts`, mais **les `.qm` ne sont pas recompilés** (voir « Restes »).

## Poussé sur GitHub, pas encore fusionné

| Branche | Lot | État | Prochaine étape |
|---|---|---|---|
| `claude/audit-engine` | moteur (10 commits) | Tests de fumée en QGIS 3.44.6 : 163 réussis, comme la référence. Suite complète en cours dans `.claude/worktrees/audit3/filter_mate` (`verify/engine`, fusionné avec `main` d'avant #362). Revue Opus en cours. | Si la suite ne montre que les 5 échecs connus : fusionner `main`, pousser, PR, fusionner. Retours de revue en suivi. |
| `claude/audit-agent-ui` | widgets et fil de l'agent | Retours de la revue corrigés (`fa0ae14e`), `main` fusionné (`a003d9a1`). | Suite complète, puis fusion. |
| `claude/vector-source-coverage-targets` | options de cibles + fonds web grisés | Revue Opus en cours. Deux chaînes nouvelles absentes des `.ts`. | Ajouter les chaînes (`scripts/i18n_add_message.py`), suite, fusion. |
| `claude/audit-lifecycle-followup` | suivi de #359 (5 commits) | Retours de la revue corrigés (Zone / SAM, checkpoint MCP au changement de projet, `abort_active` sur `cleared`, `forget_layer` avec `added`, etc.). | Suite, fusion. |
| `claude/audit-guards-followup` | suivi de #361 | En cours. Commits posés **sur `f2328679`** (la branche d'avant fusion). | Les reprendre par cherry-pick sur `main` (comme pour #364), suite, fusion. |

Contenu du lot moteur :
- une expression source qui ne garde rien ne filtre plus les cibles par toute la source : refus explicite `SourceSelectionError` ;
- l'export retrouve les couches par leur id ;
- `AND NOT` → `NOT (x)` (décision 1) ;
- éditions de l'agent sans mode édition laissé ouvert, et `coerceToType` ;
- style raster sans NaN / Infinity ni bornes inversées ;
- export de mise en page : sous-dossier créé, nom libre ;
- filtre `coalesce(...)` d'une cible combiné au lieu d'être remplacé ;
- SEGMENTS : annulation et géométries courbes.

## Restes connus (non traités)

**Traduction.**
- Pas de `lrelease` dans le QGIS Windows (3.44.6 ni 3.44.2), ni sur le Linux.
- L'installation de `qt5-applications` par pip dans un venv a été refusée par le mode automatique.
- Deux voies possibles : démarrer Docker Desktop et utiliser l'image `qgis/qgis`, comme le prévoit le dépôt ; ou autoriser `qt5-applications`.
- À faire en une seule PR à la fin : ajouter aux 34 `.ts` toutes les chaînes de l'audit (cycle de vie : déjà fait ; options de cibles : 2 ; moteur : nouveaux libellés), puis compiler les `.qm`.

**Traduction native** (transmis à l'autre session, à vérifier sur sa branche).
- `QgsFeatureRequest.NoGeometry` non qualifié dans son travail en cours.
- Moins unaire sur un NULL : QGIS rend 0, SQLite / OGR rendent NULL. Cas à tester : `-"pop" > -1`.
- `AND NOT` / `NOT` au-dessus d'une sortie OGR SQL qui contient un AND : en OGR SQL, `TRUE AND NULL` vaut `FALSE`.
- `source_qgis_expression` perdu après une combinaison.
- Réels mal arrondis par SQLite (`repr`).
- Sémantique OGR mesurée sur GDAL 3.12 / 3.13 seulement.

**Cycle de vie** : point 10 de la revue. Un filtre fait dans le dock pendant un tour de l'agent est rangé dans ce tour et annulé avec lui. Le correctif sûr demande d'identifier positivement les filtres du dock (dock + app).

**Moteur, bugs anciens** (revue du moteur) :
- en mode remplacement, les cibles sont filtrées par « ancien ∧ nouveau » alors que la source affiche « nouveau » ;
- le SQL natif refusé par le fournisseur n'a pas de repli ;
- la marge du préfiltre R-tree Spatialite est convertie dans le mauvais SCR ;
- `_set_query_timeout` ne protège rien (connexion jetable) ;
- clé `ctid` ;
- clés composites ;
- les modes SUBSET / SELECTION gardent leur priorité quand l'expression ne garde rien ;
- « EMERGENCY FALLBACK » de `geometry_preparer`.

**Cœur extrait** :
- double chargement de `filtermate_core` sous pytest : il cause les 4 échecs connus et des tests qui passent peut-être pour de mauvaises raisons ;
- repli relatif → absolu des adaptateurs sans la garde des shims ;
- `combined_query_optimizer` qui altère les littéraux (chemin mort) ;
- seulement 6 SRID géographiques reconnus par défaut dans le cœur PG (hôte autonome seulement).

**Qt6** : le garde-fou `scripts/qt_enum_scan.py` est une liste blanche. Il laisse passer `QEvent.Resize`, `QPalette.Base`, `Qt.ToolButtonIconOnly`… et ne vérifie pas qu'un membre qualifié existe. Piste : introspection PyQt6 quand elle est disponible. Le balayage n'a trouvé aucun vrai problème dans le code modifié depuis v5.0.2.

**API, faibles** :
- SSRF : seul le nom d'hôte est contrôlé, pas l'adresse résolue (`open_data`, `wfs_catalog`, `bounded_http`) ;
- chemins absolus renvoyés par `/export` ;
- `findGroup` en profondeur avec des groupes de même nom ;
- téléchargements `open_data` jamais nettoyés ;
- style gradué sans plafond ;
- `_unless_busy` absent pour le style, les étiquettes et les mises en page ;
- `native:exportlayersinformation` peut exposer les URI des sources.

**Agent, faibles** :
- une recette rejoue des ids de sorties intermédiaires ;
- `apply_effects` n'a pas de contrôle « modifié depuis » ;
- `undo_to_step` ne restaure que les filtres ;
- séparateur SSE coupé entre deux fragments dans `bounded_http` ;
- `qt_transport` passe par le gestionnaire réseau partagé de QGIS (dialogue TLS) ;
- `quotedValue` dans un subset SQL.

**Tests** :
- pollution entre tests (`tests/unit/adapters/backends` lancé d'un bloc, `test_centroid_targets_sync`, `test_public_api.py` selon l'ordre des mocks) ;
- 4 échecs dans `test_mv_references_all_layers` quand il est lancé seul.

**À vérifier dans un vrai QGIS** (les tests des lots sont sur mocks) :
- #349 sous QGIS 4.2.2 Windows : Filtrer ou Identifier pendant le chargement d'une sélection WFS ;
- fermeture du dock avec SAM, la pipette ou Zone actifs ;
- les 403 du REST de bout en bout avec le MCP stdio ;
- la ligne grisée des fonds web sous Qt5 et Qt6 ;
- `AND NOT` sans filtre sur les cibles PG / Spatialite / OGR, raster et nuage.

## Reprendre

- **Worktrees** (dans le dépôt, sous `.claude/worktrees/`) :
  - `audit/filter_mate`, `audit2/filter_mate`, `audit3/filter_mate` : intégration et vérification ;
  - `agent-<id>` : un par lot.
- **Flux d'un lot.**
  1. `git checkout -b verify/<lot> <branche>`, puis `git merge origin/main`.
  2. Conflits du CHANGELOG et de `.claude/memory.md` : garder les deux côtés avec `.claude/worktrees/audit/tools/union_conflicts.py <fichier>`. Exception : un commit qui **modifie** une entrée existante se résout à la main.
  3. Suite complète, puis `git push origin verify/<lot>:<branche>`, `gh pr create`, `gh pr merge --merge`.
- **Sorties des suites et essais des relecteurs** : `.claude/worktrees/audit/out/`. Ces fichiers sont locaux et non versionnés.
- **Pièges rencontrés.**
  - Sous zsh, `"$var:refs/..."` applique le modificateur `:r` : écrire `"${var}:refs/..."`.
  - Une variable non quotée n'est pas découpée en mots sous zsh.
  - Le redémarrage de WSL vide `/tmp` : ne rien garder d'utile dans le scratchpad de session.
