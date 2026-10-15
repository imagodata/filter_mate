# FilterMate 5.0 — Plan d'implémentation raster + nuage de points

> Rédigé le 14/10/2026, branche `claude/v5-raster-lidar`.
> Maquette interactive : https://claude.ai/artifact/3QpJuNR5HnzUnGFdDRyiHH (planches « Vue d'ensemble »,
> « Dock interactif » et « Matrice des filtres croisés »).
> Ce plan remplace la roadmap de février 2026 (`.serena/memories/backlog_raster_pointcloud_v1_2026_02_11.md`,
> `website/roadmap.html`). Il part de l'état réel du code au 14/10.

## État d'avancement (14/10/2026, fin de journée)

| Lot | État | Commits |
|---|---|---|
| 0 Spikes | fait | 6328d3f3 |
| 1 Socle type de couche | fait | 14be40d2 |
| 2 Nuage dans EXPLORING | fait (3 groupes, état par couche, Z à 3 décimales, aperçu en direct, HAG via PDAL, dalles du jeu) | a88af228 |
| 3 Raster dans EXPLORING | fait (bande, pipette, plage + histogramme, aperçu, classes, expression) | a88af228 |
| 4 Filtres croisés | fait : 9 combinaisons, couverture minimale, Disjoint, AND / OR / AND NOT | 08283761, a88af228, 62a84f2d |
| 5 Sélections avancées | fait | a88af228 |
| 6 Export | fait : GeoTIFF/COG, LAZ/LAS/COPC/GPKG/CSV, tâche de fond, depuis EXPORTING ou le bouton Export | a88af228, 62a84f2d |
| 7 Transverse | fait : favoris (758de628), rejeu à la réouverture du projet (54a491fa, sélection raster 89315bc7), Processing `filtermate:cross_filter` (0b1a33b1), API REST `POST /filters/cross` + `layer_kind` (4abdf9cb), traductions des 34 langues (aaf5090e, c79b1e00), page roadmap (2b9828d8), guide EN/FR (eff40f6e). **Non fait : vidéos du site** | — |

Revue adversariale (Opus) : 33 constats, corrigés dans 62a84f2d sauf les points ouverts ci-dessous.

### Suite (14–15/10/2026)

| PR | Contenu |
|---|---|
| #95, #96 | Automatisation : 7 algorithmes Processing + 4 modèles, `qgis_process`, API Python et REST (`docs/AUTOMATION.md`) |
| #97–#100 | Design de la maquette : carte de couche, outils par type, échelle d'espacement, pipette, icônes du rail |
| #101, #102 | Nuages : conditions d'attributs dynamiques et chaînées, panneau qui suit les statistiques de la couche ; outils raster d'EXPLORING |
| `claude/v5-release-hardening` | Avant la sortie : fonds de plan web exclus du combo, cache des fichiers dérivés nettoyé et plafonné (verrou de session, repli dans le temp, fichiers en cours d'écriture protégés), échecs nommés par couche, tâches annulées au déchargement, fenêtre « Nouveautés de FilterMate 5 », metadata ; job CI QGIS sans interface (Docker, 8 images de 3.22 à la nightly), qui a trouvé trois incompatibilités, corrigées : plugin non chargé avant QGIS 3.34.2 (`QAction` / `QShortcut`), rasters cibles non découpés avec GDAL < 3.9 (`cutlineWKT`), PDAL < 2.4 sans `writers.copc` ; options raster et nuage (actives par défaut) appliquées dès leur modification dans l'onglet Configuration |

**Vérifications** : suite unitaire 2266 OK ; tests API 126 OK (fastapi en dossier isolé) ; flake8 (config CI) 0 ; `scripts/fm5_scenarios.py` 62/62 (QGIS 4.2
sans interface, dalle LiDAR HD 0616_6153 Cerdagne, MNT 1 m et classes dérivés par PDAL, BD TOPO et parcelles WFS) ;
`scripts/fm5_gui_check.py` 26/26 sur QGIS 4.2 (Qt6) et 25/25 sur QGIS 3.44 LTR (Qt5), profil jetable.

**Points ouverts**
- QGIS 3.44 plante à la fermeture avec ces couches chargées, **même sans FilterMate** (vérifié) : à signaler à QGIS si reproductible hors `\\wsl.localhost`.
- QGIS 3.22, 3.28 et 3.34 testés **sans interface** (job CI `qgis-headless` : chargement du plugin, Processing, filtres croisés) ; le dock n'est vérifié en interface que sur 3.44 et 4.2 (`scripts/fm5_gui_check.py`).
- PDAL sous Linux vérifié en CI : pdal 2.3 des images 3.22–3.34 (repli sur l'exporteur QGIS, HAG indisponible avec message) et pdal récent de conda-forge. macOS non vérifié. Les images QGIS compilées sans PDAL ne savent pas ouvrir le LAS dérivé : nuage cible en échec avec message (mode `bbox` possible).
- Avec l'option zip, les fichiers raster / nuage vont dans `<nom>_raster_lidar.zip` à côté de l'archive vecteur (pas dans la même archive).
- Traductions des 32 langues hors fr/en produites par modèle : relecture humaine souhaitable avant la sortie.

## 1. Objectifs

1. **EXPLORING s'adapte à la couche courante.** Vecteur, raster ou nuage de points : la barre d'outils et les trois
   groupes repliables gardent leur forme, leur contenu change.
2. **EXPLORING sélectionne sur la couche source, FILTERING décrit la relation avec les cibles.** FILTERING garde
   sa structure actuelle : couches à filtrer, combinateurs, prédicat géométrique, tampon. Il accepte les trois types
   en source *et* en cible, soit 9 combinaisons (§ 3). (Révision du 14/10 après retour : plus de « méthode » par
   cible ni de choix aperçu / exact dans l'interface.)
3. **EXPORTING sait écrire chaque type** : vecteur (existant), raster GeoTIFF / COG, nuage LAZ / COPC / GPKG.
4. Chaque lot livre l'**interface et la fonctionnalité ensemble**, derrière une option de config tant qu'il n'est pas prêt.

## 2. Point de départ (audit du 14/10)

| Sujet | État | Référence |
|---|---|---|
| Tests | 2 173 réussis, 2 ignorés | `pytest` |
| Raster | **aucun code actif**. Seul le domaine pur `core/domain/raster_filter_criteria.py` existe, et seuls les tests l'utilisent. Le raster a été fusionné puis annulé deux fois. | `docs/audits/AUDIT_2026_04_22.md` |
| Nuage de points | expérimental, option `APP.OPTIONS.POINT_CLOUD.enabled` à false par défaut. Le panneau est dans FILTERING et **désactive `frame_exploring`**. | `ui/controllers/point_cloud_ui_controller.py:487-512` |
| Défauts nuage | saisie remise à zéro à chaque activation ; Z arrondi à 2 décimales ; statistiques lues une seule fois ; filtre jamais combiné (`combine_with_existing` non utilisé) ; pile d'historique partagée ; export refusé | voir la mémoire projet `point-cloud-merge-2026-10-01` |
| Couche courante | un seul combo, `comboBox_filtering_current_layer`, filtré par `HasGeometry`, ce qui exclut les rasters | `ui/managers/configuration_manager.py:876-906` |
| Rejets vecteur | `_validate_and_prepare_layer` (`filter_mate_dockwidget.py:5058`), `:6281`, `exploring_controller.py:2032`, `layer_sync_controller.py:479,521`, `filtering_controller.py:406`, etc. | rapport d'exploration |
| Code mort | `ExploringController._setup_layer_combo` / `_populate_field_combo` cherchent des combos qui n'existent pas | `ui/controllers/exploring_controller.py:127-233` |
| Docs contradictoires | `roadmap.html`, `VIDEO_SCRIPT.md` (« 5 outils raster v5.4+ ») et les annonces Discord présentent le raster comme acquis | — |

### Ce que les spikes du 14/10 ont confirmé (QGIS 4.2.3, GDAL 3.13)

Scripts : `scripts/fm5_probe_api.py` et `scripts/fm5_spike_api.py`, lancés via `python-qgis.bat`. Données : LAZ IGN de 16 874 points,
MNT `valence.tif` de 6724 × 5627 pixels.

| Mécanisme | Résultat |
|---|---|
| Expression X/Y sur un nuage (`X >= … AND Y <= …`) | ✅ `setSubsetString` accepté |
| `QgsPointCloudLayerExporter` | ✅ **respecte le subset actif** (4 068 points exportés sur 16 874), `setFilterGeometry` découpe exactement par polygone (8 144), export LAZ OK, formats Memory / GPKG / SHP / CSV / DXF / LAS |
| `QgsPointCloudDataProvider.identify(maxError, geom, zRange, limit)` | ✅ renvoie les attributs des points dans un polygone (8 144 avec maxError 0) |
| `setDataSource` sur un nuage ou un raster | ✅ garde l'identifiant de la couche, et le renderer pour le raster |
| Raster virtuel (`virtualraster`) avec `if()` | ✅ valide, mais **le NoData n'est pas déclaré** : poser `setUserNoDataValue` nous-mêmes |
| `QgsRasterTransparency` avec plages de valeurs | ✅ deux plages transparentes acceptées |
| `gdal.Warp(format=VRT, cutlineDSName, cropToCutline)` | ✅ VRT de 2,6 Ko, ouvert par QGIS, puis `gdal.Translate(format=COG)` OK |
| Algos Processing | 4.2 : `pdal:clip`, `pdal:filter`, `pdal:boundary`, `pdal:exportraster`, `pdal:createcopc`, `pdal:virtualpointcloud`, **`pdal:heightabovegroundby*`**, `native:zonalstatisticsfb`, `native:rastersampling`. 3.44 : idem **sans les deux algos de hauteur au-dessus du sol** |
| PDAL | `pdal.exe` est livré dans `bin/` de QGIS Windows (4.2 et 3.44). Pas de module Python `pdal`. |
| Fournisseurs | `virtualraster`, `vpc` (nuage virtuel multi-dalles), `copc`, `pdal`, `ept` |
| ⚠️ QGIS 3.44 | le LAZ ne s'ouvre pas en ligne de commande (`pc valid False`). C'est probablement l'environnement (chemin des plugins PDAL) : **à revérifier dans l'interface graphique** (lot 0) |

## 3. Modèle : EXPLORING sélectionne, FILTERING relie

```
EXPLORING (couche source)          FILTERING (inchangé dans sa forme)          cibles (tout type)
sélection selon le type   ──►  géométrie source  ──►  prédicat + tampon + combinateur  ──►  vecteur / raster / nuage
```

**Sélection et géométrie source, selon le type de la source**

| Source | Sélection dans EXPLORING | Géométrie source |
|---|---|---|
| Vecteur | entité unique, multiple, expression (existant) | les entités (moteur actuel) |
| Raster | plage de valeurs d'une bande, classes cochées (raster à palette), expression raster | masque des pixels retenus (`virtualraster`) → `gdal.Polygonize` (tamisage et simplification à la taille du pixel), limité à l'emprise affichée ou à l'emprise de la couche |
| Nuage | classes ASPRS, plages Z / intensité / retour, hauteur au-dessus d'un MNT (PDAL), expression | empreinte des points retenus : `pdal:boundary` (3.32+) ou grille de densité vectorisée (repli) |

**Application du prédicat, selon le type de la cible**

| Cible | Prédicats proposés | Effet | Mécanisme |
|---|---|---|---|
| Vecteur | tous les prédicats actuels + tampon + couverture minimale (nouveau, polygones) | sous-ensemble d'entités | source vecteur : moteur actuel inchangé. Source raster / nuage : test par entité (index spatial + géométrie préparée) → `pk IN (…)` combiné au filtre existant |
| Raster | Intersecte, Est contenu dans (pixels dans la zone) ; Disjoint (pixels hors zone) | pixels hors zone en NoData, identifiant et style conservés | VRT GDAL découpé (`gdal.Warp`, cutline) branché par `setDataSource` ; Disjoint = découpe par « emprise moins zone » |
| Nuage | Intersecte, Est contenu dans ; Disjoint | points hors zone retirés | `QgsPointCloudLayerExporter` + `setFilterGeometry` → LAZ temporaire → `setDataSource` (tâche). Option de config : boîtes X/Y instantanées (approximatif) |

Les prédicats qui n'ont pas de sens pour des pixels ou des points (touche, croise, chevauche) sont **ramenés à
Intersecte** pour ces cibles, avec une info-bulle. Le tampon s'applique toujours à la géométrie source.

**Exemples (planche « Relations » de la maquette)**

| Source → cible | Exemple |
|---|---|
| V → V | routes à moins de 25 m des bâtiments sélectionnés (existant) |
| V → R | MNT limité à la commune sélectionnée |
| V → P | points LiDAR sous les bâtiments sélectionnés, tampon 1 m |
| R → V | parcelles contenues dans la zone 200–260 m, couverture ≥ 50 % |
| R → R | MNT limité aux classes forêt de l'OCS GE |
| R → P | points dans les zones de pente < 15 % |
| P → V | bâtiments recoupant les points de classe 6 (couverture ≥ 10 %) ; Disjoint = bâtiments absents du nuage |
| P → R | MNT limité à l'emprise des points eau (classe 9) |
| P → P | points d'une dalle voisine sous la végétation haute ; pour appliquer simplement les mêmes critères à toutes les dalles : case « appliquer aux dalles du jeu » dans EXPLORING |

**Réutilisation clé.** Quand la source est un vecteur, rien ne change pour les cibles vecteur. Les cibles raster
et nuage sont traitées après le moteur vecteur, avec la même géométrie source (sélection EXPLORING + tampon).

## 4. Architecture

### 4.1 Domaine (pur Python, testable sans QGIS)

| Fichier | Contenu |
|---|---|
| `core/domain/layer_kind.py` | `LayerKind` (VECTOR, RASTER, POINT_CLOUD) et `kind_of(layer)` côté adaptateur |
| `core/domain/raster_filter_criteria.py` | **réutilisé** : `ComparisonOperator`, `SamplingMethod` (on ajoute MAX, MIN, MAJORITY), `RasterSamplingCriteria`. Ajout de `RasterRangeCriteria` (bande, min, max, inclusif) et `to_calc_expression()` |
| `core/domain/point_cloud_filter_criteria.py` | **existant** : ajout de `extra_dimensions` (HeightAboveGround, NumberOfReturns) et du Z exact (aucun arrondi) |
| `core/domain/cross_filter.py` | `SpatialPredicate` (les prédicats actuels), `TargetSpec(layer_id, kind)`, `CrossFilterRequest(source_kind, predicates, buffer, coverage_min, targets, combine_operator)`, et la **réduction des prédicats par type de cible** (raster / nuage : intérieur ou extérieur) |
| `core/domain/filter_state.py` | état filtré d'une couche, quel que soit son type : `SubsetState(subset)`, `RendererMaskState(xml)`, `DataSourceState(original_uri, provider, derived_uri, params)` |

### 4.2 Ports et adaptateurs

| Port (`core/ports/`) | Adaptateur (`adapters/qgis/`) | Rôle |
|---|---|---|
| `FootprintPort` | `vector_footprint.py`, `raster_footprint.py` (masque puis `gdal.Polygonize`), `point_cloud_footprint.py` (`pdal:boundary`, avec repli par densité) | produire l'empreinte d'une source |
| `SamplingPort` | `raster_sampler.py` (`provider.sample`, zonale Processing), `point_cloud_sampler.py` (`identify`, rasterisation) | lire des valeurs par entité |
| `TargetApplierPort` | `vector_target_applier.py` (enveloppe le moteur existant), `raster_target_applier.py` (VRT cutline, `virtualraster`, masque de transparence), `point_cloud_target_applier.py` (expression, exporter → `setDataSource`) | appliquer à une cible |
| `ExportPort` | `raster_exporter.py` (`gdal.Translate` GeoTIFF / COG), `point_cloud_exporter.py` (`QgsPointCloudLayerExporter`, `pdal:createcopc`) | écrire |
| `PdalPort` | `pdal_cli.py` (détection de `pdal.exe` / `pdal`, pipelines JSON, `QgsTask` annulable) | HAG par DEM, colorisation |
| `CapabilityPort` | `layer_capabilities.py` (**généralise** `point_cloud_capability.py`) | version QGIS, options, présence des algos (`pdal:*`), PDAL CLI, formats GDAL (COG) |

`point_cloud_capability.py` reste en façade de compatibilité. Ses tests restent verts.

### 4.3 Service

`core/services/cross_filter_service.py` exécute une `CrossFilterRequest` :

1. il obtient la géométrie source : sélection vecteur (moteur existant), raster vectorisé ou empreinte du nuage ;
   puis il applique le tampon ;
2. pour chaque cible non traitée par le moteur vecteur actuel, il choisit l'applicateur selon le type de la cible ;
3. il exécute en `QgsTask` (une tâche par cible, annulable) ;
4. il enregistre l'état précédent de chaque couche dans un historique **par couche** (§ 4.5).

Le chemin vecteur → vecteur actuel n'est **pas réécrit**. Quand la source est un vecteur, le moteur actuel traite
les cibles vecteur et le service traite ensuite les cibles raster et nuage.

### 4.4 Interface

| Élément | Changement |
|---|---|
| `ui/widgets/exploring_host.py` (nouveau) | `QStackedWidget` placé dans `frame_exploring` : page 0 = les groupes vecteur actuels (déplacés, pas réécrits), page 1 = `RasterExploringPanel`, page 2 = `PointCloudExploringPanel`. Expose `criteria()` et `kind` |
| barre d'outils `widget_exploring_keys` | les 6 boutons existants sont réaffectés par type (icône, infobulle, action) au lieu d'en créer d'autres : vecteur (identifier, zoom, sélectionner, suivre, lier, réinitialiser) ; raster (pipette, zoom plage, rectangle, valeur sous le curseur, lier la plage au rendu, réinitialiser) ; nuage (identifier un point, zoom, profil d'élévation, aperçu direct, vue 3D, réinitialiser) |
| `ui/controllers/exploring/` (nouveau) | `VectorExploringStrategy` (enveloppe `ExploringController`), `RasterExploringController`, `PointCloudExploringController`. Le dock choisit le contrôleur dans `current_layer_changed`, au même endroit que la délégation nuage actuelle (`filter_mate_dockwidget.py:5603`) |
| `ui/widgets/raster/` | `HistogramWidget` (QPainter, poignées min/max, histogramme calculé par `provider.histogram` en tâche), `PixelPickerTool` (`QgsMapToolEmitPoint` + `identify` sur toutes les bandes), `RasterClassListWidget` (rasters à palette) |
| `ui/widgets/point_cloud/` | refonte de `PointCloudFilterWidget` en 3 groupes : classes + préréglages (nomenclature LiDAR HD : 1, 2, 3, 4, 5, 6, 9, 17, 64, 65, 66), plages Z / intensité / retour avec histogramme Z, expression éditable |
| bandeau d'info + badge | type · fournisseur · métadonnées (bandes, résolution, NoData / nombre de points, plage Z) |
| FILTERING | **même disposition qu'aujourd'hui** : couche source, couches à filtrer (désormais tous types, avec icône de type), combinateurs, prédicats, tampon. Ajouts : une ligne « géométrie source » sous la couche source et une couverture minimale (%) à côté du prédicat |
| EXPORTING | les formats proposés dépendent des types des couches cochées (§ 6) |
| combo couche courante | les filtres `HasGeometry` + `RasterLayer` + `PointCloudLayer` dépendent des options `APP.OPTIONS.RASTER.enabled` et `POINT_CLOUD.enabled` |

### 4.5 Historique, projet, cache

- **Historique par couche.** `HistoryEntry.previous_filters` contient aujourd'hui des `(layer_id, subset)`. Il
  devient `(layer_id, FilterState sérialisé)`. Une migration lit l'ancien format comme `SubsetState`. Annuler et
  rétablir restaurent le bon type d'état. `LayerRefreshManager._do_refresh` ne doit plus appeler
  `featureCount()` / `updateExtents()` sur un raster ou un nuage (défaut c).
- **Sauvegarde du projet.** Une source dérivée (VRT, LAZ temporaire) ne doit jamais être écrite dans le `.qgz`.
  On se branche sur `QgsProject.writeMapLayer` : dans le DOM, on remplace la source par l'originale et on ajoute une
  propriété `filtermate/derived` contenant les paramètres. À l'ouverture du projet, on propose de rejouer le filtre,
  ou on le rejoue automatiquement selon la config.
- **Cache.** Le cache vit dans `<profil>/filtermate/cache/<projet>/` : VRT, GPKG d'empreintes, LAZ dérivés. Il est
  purgé à la fermeture du projet, avec un plafond en Go (config).

### 4.6 Options de config (`config/config.default.json`)

`APP.OPTIONS.RASTER.enabled`, `APP.OPTIONS.POINT_CLOUD.enabled`, `APP.OPTIONS.CROSS_FILTER.default_mode`
(`live` | `exact`), `APP.OPTIONS.CROSS_FILTER.max_live_boxes` (50), `APP.OPTIONS.CACHE.max_gb` (5),
`APP.OPTIONS.PDAL.path` (vide = détection automatique). Prévoir aussi les migrations de config (cf.
`tests/unit/test_config_migration.py`).

## 5. Lots

Chaque lot = une ou deux PR, interface et fonctionnalité ensemble, tests unitaires + un scénario QGIS réel.
Estimations en jours de développement.

### Lot 0 — Spikes restants (2 j)
- [ ] QGIS 3.44 en interface : ouvrir le LAZ, `setSubsetString`, export LAS (erreur `a_srs` vue en ligne de commande).
- [ ] QGIS 3.28 / 3.34 si disponibles : exporter, `virtualraster` avec `if()`, `vpc`.
- [ ] `virtualraster` : NoData (`setUserNoDataValue`), coût de rendu sur un MNT de 1 Go, rééchantillonnage quand les
      grilles diffèrent (R → R).
- [ ] `setDataSource` sur un nuage : style, renderer de classification, index COPC.
- [ ] Pipeline `pdal.exe` `readers.las → filters.hag_dem(raster) → writers.copc` sur une dalle LiDAR HD + RGE ALTI.
      Mesurer le temps et vérifier la présence de PDAL sous Linux / macOS.
- [ ] Signal `QgsProject.writeMapLayer` : réécriture du DOM sans casser la sauvegarde.
- [ ] Données de test : 4 dalles LiDAR HD COPC, RGE ALTI 1 m sur la même emprise, OCS GE raster, BD TOPO 31 (déjà
      présente). Les poser sous `~/Documents/ign/fm5/`.

### Lot 1 — Socle « type de couche » (5 j)
- [ ] `LayerKind`, `layer_capabilities.py` (+ façade `point_cloud_capability`), options RASTER / CROSS_FILTER / CACHE.
- [ ] Combo de couche courante : rasters inclus derrière l'option.
- [ ] Dispatch par type à la place des rejets vecteur (liste du § 2). Chaque rejet devient « vecteur seulement »
      explicite ou un aiguillage.
- [ ] `ExploringHost` (pile de pages) + page vecteur = groupes actuels **déplacés sans changement de
      comportement**.
- [ ] Réaffectation de la barre d'outils, bandeau d'info, badge de type.
- [ ] `FilterState` + historique par couche + correction de `LayerRefreshManager`.
- [ ] Suppression du code mort de `ExploringController` (`_setup_layer_combo`, `_populate_field_combo`).
- **Acceptation** : en vecteur, rien ne change (tests existants + scénario BD TOPO). Un raster ou un nuage
  sélectionné affiche une page vide mais propre, sans erreur dans le log.

### Lot 2 — Nuage de points dans EXPLORING (5 j)
- [ ] `PointCloudExploringPanel` en 3 groupes (maquette), état conservé **par couche** (défaut d).
- [ ] Z sans arrondi (`setDecimals(3)` + valeur brute conservée) ; rafraîchissement des statistiques quand
      `statistics_available` change (défaut e).
- [ ] Filtre combiné avec le subset existant (`combine_with_existing`), nombre de points retenus en direct.
- [ ] Outils : identifier un point, zoom sur l'emprise, profil d'élévation (`QgsElevationProfileCanvas` /
      action QGIS), vue 3D.
- [ ] Le panneau quitte FILTERING : retrait de `_apply_point_cloud_layout` et de la désactivation de `frame_exploring`.
- [ ] Prise en compte du changement d'option sans rechargement (combo rafraîchi, défaut f).
- **Acceptation** : filtre classe + Z + retour sur une dalle LiDAR HD, annuler / rétablir, changement de couche aller-retour sans perte de saisie.

### Lot 3 — Raster dans EXPLORING (6 j)
- [ ] `RasterExploringPanel` : choix de bande, valeur au pixel (+ derniers relevés, Ctrl+clic qui étend la plage),
      plage avec histogramme, expression raster validée par `QgsRasterCalcNode.parseRasterCalcString`.
- [ ] Aperçu « masquer hors plage » : `QgsRasterTransparency` sur une copie du renderer, restauré au défiltrage et à
      la fermeture.
- [ ] Rasters à palette / catégoriels : le groupe Plage devient une liste de classes cochables.
- [ ] Outils : rectangle → statistiques de zone, valeur sous le curseur, lier la plage au rendu (min / max de la
      symbologie).
- [ ] Filtrer la couche raster elle-même = `virtualraster` (valeur) branché par `setDataSource`.
- **Acceptation** : MNT 1 m de 1 km² et MNT départemental en VRT, histogramme calculé en moins de 1 s sur la dalle,
  aperçu réversible, projet sauvegardé sans source dérivée.

### Lot 4 — Filtres croisés (10 j)
- [ ] `cross_filter.py` (domaine) + réduction des prédicats par type de cible + `CrossFilterService`.
- [ ] Géométrie source : vecteur (sélection EXPLORING), raster (masque → polygonisation), nuage (`pdal:boundary`,
      avec repli par grille de densité). Tampon appliqué à la géométrie source.
- [ ] Applicateurs : cible vecteur (test par entité → `pk IN (…)` combiné), cible raster (VRT découpé, Disjoint
      inclus), cible nuage (exporter + géométrie → LAZ → `setDataSource`).
- [ ] FILTERING : couches à filtrer tous types (icône de type), ligne « géométrie source », couverture minimale.
- [ ] Source vecteur + cibles raster / nuage : traitées après le moteur vecteur, avec la même géométrie source.
- **Acceptation** : les 9 combinaisons sur les données de Cerdagne (LiDAR HD 0616_6153, MNT 1 m dérivé, BD TOPO,
  parcelles), chacune annulable, temps relevés dans le log.

### Lot 5 — Sélections avancées dans EXPLORING (5 j)
- [ ] Nuage : hauteur au-dessus d'un MNT choisi (pipeline `pdal.exe` `filters.hag_dem` → nuage dérivé avec
      `HeightAboveGround`, ensuite filtrable en direct) ; repli sans PDAL : critère masqué avec un message.
- [ ] Nuage : case « appliquer aux dalles du jeu » (même expression sur les nuages du même dossier / VPC).
- [ ] Raster : classes d'un raster à palette, expression raster multi-couches.
- **Acceptation** : végétation de plus de 2 m sur la dalle de Cerdagne ; filtre appliqué aux 4 dalles.

### Lot 6 — Export (5 j)
- [ ] Raster : couche filtrée (VRT / virtuelle / masque) → GeoTIFF ou COG (`gdal.Translate`, compression, NoData,
      recadrage à l'empreinte), style `.qml` à côté.
- [ ] Nuage : `QgsPointCloudLayerExporter` (respecte le subset et la géométrie) → LAZ / GPKG / CSV ; COPC via
      `pdal:createcopc`. Le bouton Export n'est plus intercepté (défaut b).
- [ ] Export groupé mixte : `batch_exporter.py` aiguille par type, et la récapitulation de groupe
      (`export_group_recap_dialog.py`) affiche les trois types.
- [ ] Tâches avec progression et annulation, chemins de sortie, CRS de sortie (reprojection raster via `gdal.Warp`).
- **Acceptation** : export d'un MNT découpé en COG lisible par QGIS, export d'un nuage filtré en LAZ (vérifier le
  nombre de points) puis en COPC, export groupé vecteur + raster + nuage.

### Lot 7 — Transverse et sortie 5.0 (6 j)
- [ ] Favoris : sérialiser les critères par type (`favorites_service.py`), compatibilité des anciens favoris.
- [ ] `filtermate_api` + algorithmes Processing (filtre croisé, export de couche filtrée) pour les modèles et le batch.
- [ ] Sauvegarde et réouverture de projet avec sources dérivées (§ 4.5).
- [ ] Docs : `roadmap.html` réécrite, guide, `VIDEO_SCRIPT` et annonces corrigés, CHANGELOG, captures et vidéos via
      `scripts/site_videos.py`.
- [ ] Recette QGIS réelle 3.44 LTR + 4.2 (Windows), puis Linux. Option nuage activée par défaut, option raster
      activée par défaut si la recette passe.
- [ ] Release 5.0 (`metadata.txt`, `qgisMinimumVersion` inchangé à 3.22, fonctions masquées selon les capacités).

**Total estimé : ~44 jours.** Ordre : 0 → 1 → (2 ∥ 3) → 4 → 5 → 6 → 7. Les lots 2 et 3 sont indépendants, et le
lot 6 peut commencer dès la fin du lot 4 pour l'export raster et nuage simple.

## 6. Export par type

| Type | Formats | Mécanisme | Ce qui est exporté |
|---|---|---|---|
| Vecteur | GPKG, SHP, KML, CSV, … (existant) | `core/export/*` | entités du subset |
| Raster | GeoTIFF, COG, (VRT) | `gdal.Translate` / `gdal.Warp` depuis la source courante (VRT découpé, virtuel) ou depuis la source + plage | pixels retenus, NoData ailleurs, option de recadrage |
| Nuage | LAZ, LAS, COPC, GPKG (points), CSV | `QgsPointCloudLayerExporter` (+ `pdal:createcopc`) | points du subset et de l'empreinte |

## 7. Compatibilité QGIS

| Fonction | Minimum | Si absent |
|---|---|---|
| Raster (exploring, VRT, virtuel, zonale) | 3.22 | — |
| Nuage, exporter, `identify` | 3.26 | type masqué du combo |
| Algos `pdal:*` (boundary, exportraster, createcopc, vpc) | 3.32 | repli par densité ; pas de COPC (LAZ seulement) |
| Hauteur au-dessus du sol (algos natifs) | 4.2 (absent en 3.44) | `pdal.exe filters.hag_dem` si PDAL est détecté, sinon empreinte |
| PDAL CLI | livré avec QGIS Windows | désactiver R → P exact avec un message |

## 8. Tests

- **Unitaires (sans QGIS)** : domaine (`cross_filter`, critères, table de compatibilité, `FilterState` et migration
  d'historique), construction des expressions et des formules, choix d'adaptateur. Cible : chaque lot ajoute ses tests,
  aucun test existant n'est désactivé.
- **Garde-fous statiques** (comme les tests `test_no_*` existants) : pas de `featureCount()` sur un nuage ou un
  raster dans les chemins communs, pas d'appel `setDataSource` hors des applicateurs.
- **Scénarios QGIS réels** : `scripts/fm5_scenarios.py`, lancé via `python-qgis.bat` sur les données du lot 0. Il
  produit un tableau temps / nombre par combinaison, sur le modèle de `scripts/recipe_screenshots.py`.
- **Performance (cibles)** : aperçu < 200 ms ; histogramme d'une dalle 1 km² < 1 s ; zonale 10 000 parcelles × MNT
  1 m < 30 s ; HAG d'une dalle LiDAR HD < 60 s.

## 9. Risques et décisions ouvertes

| # | Sujet | Proposition |
|---|---|---|
| D1 | « Filtrer un raster » = masque visuel ou source dérivée ? | **Les deux** : aperçu de la sélection dans EXPLORING = transparence ; raster cible filtré = source dérivée (VRT découpé) branchée par `setDataSource`. La couche garde son identifiant et son style, ce qui est cohérent avec le subset vecteur. |
| D7 | Relations « par valeur » (statistiques zonales) | **remplacées** par le modèle sélection → géométrie → prédicat (retour du 14/10). La couverture minimale couvre l'essentiel du besoin « parcelles majoritairement dans la plage ». |
| D2 | Source dérivée dans un projet sauvegardé | réécriture du DOM sur `writeMapLayer` (lot 0 puis lot 7) |
| D3 | PDAL absent sous Linux / macOS | détection + repli par empreinte, message clair |
| D4 | Grandes listes de fid (R → V, P → V) sous PostgreSQL | table temporaire ou `ANY(array)`, à mesurer |
| D5 | Coût du rendu `virtualraster` sur de gros rasters | mesurer au lot 0 ; repli en VRT GDAL + calcul matérialisé en tâche |
| D6 | Pile d'historique globale | entrées par couche, annulation de la couche courante d'abord (comportement actuel « source seule » conservé) |
| R1 | Régression du chemin vecteur | page vecteur déplacée sans réécriture, délégation au moteur existant, tests existants obligatoires |
