# Project Memory
_Auto-maintained by project agent_


## [2026-07-31] Portage QGIS 4.2 / Qt6 — 2e passe : la clôture précédente était incomplète
Suite immédiate de l'entrée ci-dessous ("suite et clôture"), qui affirmait le
portage Qt6 terminé après vérification manuelle + agent dédié. Un re-balayage
ciblé (grep sur les enums plats connus pour casser sous PyQt6 + sur les
classes déplacées QtWidgets→QtGui) a trouvé 4 fichiers non couverts par
l'audit précédent (qui portait sur "50 fichiers" — celui-ci en touchait
d'autres, notamment tout `ui/widgets/json_view/`, resté hors radar) :
- `filter_mate_dockwidget.py` + `ui/widgets/json_view/searchable_view.py` :
  `QShortcut` importé depuis `QtWidgets` au lieu de `QtGui` — Qt6/PyQt6 a
  déplacé `QAction`, `QActionGroup`, `QFileSystemModel`, `QShortcut`,
  `QUndoCommand`, `QUndoGroup`, `QUndoStack` de `QtWidgets` vers `QtGui`.
  Cassait au chargement du dockwidget (`_setup_keyboard_shortcuts`) et du
  widget de recherche JSON sous QGIS4/PyQt6 — pas du tout détectable par
  l'audit "enums plats" précédent, car c'est un problème d'emplacement de
  classe, pas d'enum.
- `ui/widgets/json_view/datatypes.py` (×4), `view.py` (×2 + 1 QPalette),
  `searchable_view.py` (`Qt.CaseInsensitive` + `QPalette.Window`),
  `ui/managers/configuration_manager.py` (×2 `Qt.RightToLeft`) : enums plats
  historiques (`Qt.ForegroundRole`, `Qt.CaseInsensitive`, `Qt.RightToLeft`,
  `QPalette.Window`) valides en PyQt5 par promotion dans l'espace de noms
  global, supprimés en PyQt6 — même famille de bug que l'audit "~165 accès"
  de la session précédente, juste dans des fichiers qu'il n'avait pas
  couverts.
Fix : forme scopée partout (`Qt.ItemDataRole.ForegroundRole`,
`Qt.CaseSensitivity.CaseInsensitive`, `Qt.LayoutDirection.RightToLeft`,
`QPalette.ColorRole.Window`, imports `QShortcut` déplacés vers `QtGui`).
Ajout de `tests/test_no_qtwidgets_relocated_symbols.py` (garde-fou AST, même
esprit que `tests/test_no_unguarded_sip_import.py` pour #47) pour empêcher la
réintroduction de `QAction`/`QActionGroup`/`QFileSystemModel`/`QShortcut`/
`QUndoCommand`/`QUndoGroup`/`QUndoStack` importés ou référencés via
`QtWidgets`. Pas de garde-fou générique ajouté pour les enums plats
(ensemble de noms trop large pour un AST-check fiable sans faux positifs ;
seule la classe de bug QtWidgets→QtGui, précise et bornée, a été couverte).
Suite complète `tests/unit/` : 1484 passed / 7 failed (mêmes échecs
pré-existants que la session précédente, `test_export_bugfix.py`, aucune
régression introduite).
Complément (autopilot, même journée) : élargissement du balayage à d'autres
familles d'enums (QIcon, QLineEdit.EchoMode, QPainter render hints, Qt.Key_*
en forme attribut, Qt.SortOrder/ArrowType/Corner/Edge/FillRule/PenCapStyle/
PenJoinStyle/ClipOperation/TimeSpec/DateFormat/ToolButtonStyle/InputMethodHint/
FocusReason/ScreenOrientation/ApplicationState) — toutes propres, aucune
occurrence. `Qt.QueuedConnection` et `Qt.LeftDockWidgetArea` trouvés en forme
plate mais uniquement dans des commentaires/docstrings (pas de code réel,
laissés tels quels). En revanche `QStyle` a livré 2 vrais positifs manqués par
tous les passages précédents : `ui/widgets/json_view/datatypes.py:470`
(`QtWidgets.QStyle.CC_SpinBox` → `.ComplexControl.CC_SpinBox`) et
`ui/widgets/custom_widgets.py:163` (`QStyle.PE_IndicatorViewItemCheck` →
`.PrimitiveElement.PE_IndicatorViewItemCheck`), plus un `QAbstractSpinBox.
NoButtons` plat au même endroit (`datatypes.py:463` → `.ButtonSymbols.
NoButtons`). Les 12 autres usages de `QStyle` dans le repo (delegate.py,
custom_widgets.py) étaient déjà correctement scopés — seuls ces 2 CC_/PE_
isolés avaient été oubliés. Suite complète re-vérifiée après coup : 1486
passed / 7 failed (mêmes échecs pré-existants).
Leçon retenue : ne pas prendre "audité, plus aucune occurrence" pour acquis
même juste après une clôture annoncée — un balayage automatisé peut avoir un
périmètre de fichiers incomplet (ex. `ui/widgets/json_view/` semble avoir été
ajouté/modifié hors du balayage initial). Si on reprend ce portage plus tard,
il reste probablement utile de refaire un balayage large avec la liste
complète des membres d'enum PyQt5 promus globalement (Qt.Key_*, QIcon.*,
QPainter.*, etc.) — non exhaustif ici, seuls les motifs à forte confiance
trouvés par grep ciblé ont été corrigés.


## [2026-07-31] Portage QGIS 4.2 / Qt6 — suite et clôture du passage QMetaType + câblage Processing Toolbox
Contexte : v4.7.3 (commit `eb9353c1`) avait déjà qualifié ~165 accès enum
PyQt/PyQGIS non scopés sur 50 fichiers, renommé `.exec_()` → `.exec()`, et
sécurisé tous les `import sip` (fallback `PyQt6.sip`). Cette session a
terminé le reliquat trouvé dans le worktree (branche
`claude/fix-processing-typevectorany`), non lié au code déjà commité :

1. **Migration `QVariant.Xxx` → `QMetaType.Type.Xxx`** (commit `656ab053`) :
   `QgsField.type()` renvoie un `QMetaType.Type` sous les bindings Qt6/QGIS4.
   6 fichiers touchés (`adapters/app_bridge.py`,
   `adapters/backends/ogr/expression_builder.py`,
   `adapters/backends/postgresql/filter_executor.py`,
   `adapters/qgis/layer_adapter.py`, `core/services/layer_service.py`,
   `infrastructure/utils/layer_utils.py`) pour la détection de PK
   numérique/texte. Piège à retenir : les membres `Int/UInt/LongLong/
   ULongLong/Double` gardent le même nom entre `QVariant.Type` et
   `QMetaType.Type`, mais `String/Date/Time/DateTime/ByteArray/Char`
   deviennent `QString/QDate/QTime/QDateTime/QByteArray/QChar` (préfixe `Q`)
   — erreur facile si on renomme mécaniquement sans vérifier chaque membre.
   Toutes les formes utilisées restent valides sous PyQt5/QGIS3.22+ (pas de
   rupture sur l'install Qt5 actuelle) — pattern additif, cohérent avec
   `eb9353c1`.
   Complément : `QgsMessageLog.INFO/WARNING` → `Qgis.MessageLevel.Info/
   Warning` (`geometry_optimizer.py`), `event.pos()` →
   `event.position().toPoint()` pour `QMouseEvent` (`custom_widgets.py`),
   et `supportsQt6=yes` déclaré dans `metadata.txt`.
2. **Câblage Processing Toolbox** (commit `efbedc2e`) : un fichier
   `processing/algorithms/batch_filter_algorithm.py` (nouvel algorithme
   `BatchFilterAlgorithm`, applique une expression à plusieurs couches)
   existait déjà dans le worktree mais n'était enregistré nulle part — pas
   de `QgsProcessingProvider`, rien chargé depuis `filter_mate.py`. Ajout de
   `processing/provider.py` (`FilterMateProcessingProvider`) + enregistrement
   dans `initGui()` / désenregistrement dans `unload()` via
   `QgsApplication.processingRegistry()`, suivant le même pattern
   défensif try/except que `_init_extensions()` (un échec ne doit jamais
   bloquer le chargement du cœur du plugin). Corrigé au passage : import
   cassé `from ...infrastructure.logging.logger import get_logger` (le
   sous-module `logger` n'existe pas — `get_logger` vit dans
   `infrastructure/logging/__init__.py`).

Vérification faite avant/après (balayage manuel + agent dédié) : plus aucun
`QVariant`, `QRegExp`, `.exec_()`, import PyQt5 direct, `import sip` non
gardé, ou énum non scopée dans tout le repo (hors tests/). Le portage Qt6
semble donc complet à ce stade. Suite de tests : 1485 passed / 7 failed
(préexistants, `tests/unit/core/export/test_export_bugfix.py`, confirmés
présents avant tout changement de cette session — sans rapport avec Qt6,
non traités ici).

Note pour la suite : `.serena/project.yml` a une diff non commitée (mise à
jour auto du format de config Serena — `languages` → `language_servers`,
etc.), sans rapport avec le plugin, laissée telle quelle intentionnellement.


## [2026-07-30] Fix: sélection "all-features" (expression toujours vraie) écrasée par une sélection QGIS résiduelle
Bug rapporté: filtre "intersecte" GeoPackage (backend Spatialite, routé via
`.gpkg` → provider 'spatialite') retournait 0 entités sans erreur quand la
couche source utilisait "Custom Selection" avec une expression toujours vraie
(ex: `1`) — cas destiné à dire "utilise TOUTES les features de la couche
source dans son état actuel (filtrée ou non)".
Root cause: `determine_spatialite_source_mode()`
(`adapters/backends/spatialite/filter_executor.py`) a une cascade de priorité
TASK_PARAMS > SUBSET > SELECTION > FIELD_BASED > FALLBACK où la branche
`elif has_selection:` n'était PAS gardée par `and not is_field_based_mode`,
contrairement au garde déjà présent dans la classe sœur
`SourceFeatureResolver._resolve_from_selection` (`adapters/qgis/source_feature_resolver.py`,
écrite ~13h plus tôt le même jour, MIG-204). Donc si la couche source avait
une sélection résiduelle QGIS (features surlignées, sans rapport avec
l'intention "toutes les features"), le mode SELECTION gagnait sur FIELD_BASED
→ géométrie source construite à partir d'une poignée de features non
pertinentes au lieu de toutes les features respectant le subset courant →
intersection avec la couche distante ne matchait rien, silencieusement.
Même bug dupliqué dans `adapters/backends/ogr/filter_executor.py::determine_source_mode()`
(`elif has_subset or has_selection:` sans garde `is_field_based`) — corrigé
en parallèle car ce backend est aussi emprunté par GeoPackage via le sentinel
`USE_OGR_FALLBACK` (buffer dynamique, GeometryCollection).
Fix: ajout du garde `and not is_field_based_mode` (spatialite) /
`and not is_field_based` (ogr) sur la branche SELECTION dans les deux fichiers.
Tests: nouveau fichier `tests/unit/adapters/backends/spatialite/test_filter_executor.py`
(6 tests) + 2 tests ajoutés à `tests/unit/adapters/backends/ogr/test_filter_executor.py`
(`TestDetermineSourceMode`). Suite complète `tests/unit/` validée : 1491 passed.
Note: la syntaxe SQL générée (`ST_Intersects`/`ST_MakeValid`/`ST_GeomFromText`
pour GeoPackage-via-OGR) N'ÉTAIT PAS en cause — vérifiée empiriquement valide
via `ogrinfo`/GDAL 3.11 avant d'investiguer plus loin (voir historique
conversation pour le détail des tests GDAL).

## [2026-07-29] Fix: SpatialiteExpressionBuilder ignorait le kwarg source_srid
Branche: `claude/spatialite-empty-filter-fix`
Bug: `build_expression()` appelait toujours `self._get_source_srid()` (lit
`task_params['infos']['layer_crs_authid']`, rempli une seule fois à
l'initialisation, jamais mis à jour après `configure_metric_crs()`) au lieu du
kwarg `source_srid` passé par l'appelant réel (qui, lui, reflète la CRS
post-reprojection). Résultat : quand CRS source originale == CRS cible,
`ST_Transform` était sauté, le WKT reprojeté (métrique) était comparé avec un
SRID géographique erroné → `ST_Intersects` ne matchait jamais → couche filtrée
à 0 entités sans erreur visible.
Fix: `source_srid = kwargs.get('source_srid') or self._get_source_srid()` —
aligne Spatialite sur le pattern déjà utilisé par
`PostgreSQLExpressionBuilder.build_expression()`.
Tests ajoutés dans `tests/unit/adapters/backends/spatialite/test_expression_builder.py`
(`test_source_srid_kwarg_overrides_task_params`,
`test_source_srid_falls_back_when_kwarg_missing`). Détail complet dans la
mémoire Serena `spatialite_source_srid_kwarg_fix_2026_07_29`.
Note env: pas de pytest/pip dans ce sandbox — validation faite via script
Python autonome reproduisant le harnais de mocks du fichier de test.


## [2026-03-24 13:37]
Delegate task: fais brainstormer les agents de narractive et FilterMate pour ajouter comme extension qgis pyqgis de narractive la gestion du plug-in FilterMate et son ui
Result: Je ne trouve pas de trace de "Narractive" dans le codebase FilterMate. Pour lancer un brainstorming utile, j'ai besoin de contexte :

**1. Qu'est-ce que Narractive ?**
- Un plugin QGIS externe (tiers) pour la narration cartographique/storytelling ?
- Ton propre projet de plugin QGIS dans un autre repo ?
- Un concept/nouveau projet à créer from scratch ?
- Autre chose (outil de présentation, narration vidéo QGIS...) ?

**2. Quelle intégration tu envisages ?**
- Embarquer l'UI de FilterMate **dans


## [2026-03-24 13:39]
Delegate task: fais brainstormer les agents de narractive et FilterMate pour ajouter comme extension qgis pyqgis de narractive la gestion du plug-in FilterMate et son ui
Result: 🎉 **PARTY MODE ACTIVÉ !** 🎉

Bonjour Simon ! J'ai rassemblé notre équipe d'experts pour cette session de brainstorming. Voici nos agents présents :

---

**Agents chargés pour cette session :**

| Agent | Rôle |
|---|---|
| 🏗️ **Winston** (Architecte) | Architecture système, patterns d'extension QGIS |
| 🎨 **Sally** (UX Designer) | Intégration UI/UX inter-plugins |
| 📋 **John** (Product Manager) | Vision produit, use cases |
| 💻 **Amelia** (Dev Senior) | Implémentation PyQGIS, API plugin |
| 📊 *


## [2026-03-24 18:38]
Delegate task: ## Import pattern OGR adapter : filtermate → fibreflow

Marco a analysé les deux repos (accessibles via GitHub CLI). Voici le bilan :

---

### Diagnostic clé

**filtermate** (`imagodata/filter_mate`) : architecture hexagonale mature, mais son `OGRBackend` est **couplé à QGIS** (`QgsProject`, `QgsExpression`). Il **ne peut pas être importé tel quel** dans fibreflow.

**Décision : copier le pattern, pas la dépendance.**

`core/ports/backend_port.py` de filtermate est pur Python (sans import QGIS) — c'est ça qu'on transpose.

---

### Architecture cible dans fibreflow

```
fibreflow/
├── core/
│   ├── ports/
│   │   └── ogr_reader_port.py      # OGRReaderPort + OGRWriterPort (ABC)
│   ├── adapters/
│   │   └── ogr/
│   │       └── gdal_adapter.py     # GDALOGRAdapter (GeoPandas/Fiona, sans QGIS)
│   ├── terrain_importer.py         # MODIFIÉ — injection de dépendance
│   └── geometry_validators.py      # INCHANGÉ — déjà pur
```

---

### Décisions d'implémentation

| Question | Décision |
|----------|----------|
| Copier ou dépendre de filtermate ? | **Copier le pattern** — filtermate requiert QgsProject |
| Interface ? | Nouveau `OGRReaderPort` orienté ETL (vs `BackendPort` orienté filter QGIS) |
| Injection dans TerrainImporter ? | **Oui, avec fallback** — `GDALOGRAdapter` par défaut, mockable en tests |
| `geometry_validators.py` ? | **Inchangé** — fonctions pures, architecture déjà idéale |

---

### Fichiers à créer dans `imagodata/fibreflow`

1. `fibreflow/core/ports/ogr_reader_port.py` — Ports abstraits + `OGRCapability`, `OGRSourceInfo`, `OGRReadResult`
2. `fibreflow/core/adapters/ogr/gdal_adapter.py` — `GDALOGRAdapter` (lecture, streaming, écriture, métriques)
3. `fibreflow/core/terrain_importer.py` — Modifier `__init__` + `_load_file` pour injection du reader

---
Result: **8 issues créées** sur `imagodata/filter_mate` pour le sprint REST API :

| # | Ticket | Priorité |
|---|--------|----------|
| [#35](https://github.com/imagodata/filter_mate/issues/35) | EPIC — FilterMate REST API | — |
| [#27](https://github.com/imagodata/filter_mate/issues/27) | T1 Bootstrap serveur FastAPI | 🔴 Critique |
| [#28](https://github.com/imagodata/filter_mate/issues/28) | T9 Auth & Config (API key) | 🟡 Important |
| [#29](https://github.com/imagodata/filter_mate/issues/29) | T2 PO


## [2026-03-25 12:35]
Delegate task: Enrichir les blueprints avec le code réel de FilterMate/FibreFlow comme référence
Lancer la veille techno sur les sources configurées
Result: Que veux-tu faire dans cette session ?

- Enrichir les blueprints Forge avec le code réel de FilterMate/FibreFlow
- Lancer la veille techno
- Continuer le sprint REST API FilterMate (T2, T9...)
- Autre chose sur FilterMate
