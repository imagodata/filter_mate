# Opportunités FilterMate pour des coupes LiDAR HD

Cadre de la recherche : lecture statique du checkout `main` (a19657cf, version 5.0.2, `metadata.txt:11`), le 2026-11-09. QGIS n'a pas été lancé : aucun appel PyQGIS n'a été exécuté ici. Les références de code sont en `chemin:ligne`, relatives à `/home/simon/dev/filter_mate`. Les fichiers mémoire sont historiques : quand ils sont cités, c'est soit après vérification dans le code, soit avec la mention « mémoire, non revérifié ». Les pages PyQGIS consultées sont la branche `master` (4.x au moment de la recherche).

## Quelles fonctions nuage de points existent aujourd'hui, et où sont leurs points d'entrée ?

### Takeaway
FilterMate possède une chaîne nuage de points complète pour **filtrer, sélectionner et exporter en plan** (classes, plages, expression, hauteur sur MNT, pipettes, zone, objets, export, Processing, REST, MCP), mais **aucune fonction de coupe** : le seul lien avec le profil est un raccourci qui ouvre l'outil natif de QGIS, sans ligne, sans tolérance ni export. Le paquet `filtermate_core/` n'est pas dans `main`.

### Cited Findings
**Activation et versions**
- Plugin déclaré pour QGIS 3.22 à 4.99 — `metadata.txt:8-9`. Le filtrage nuage exige QGIS 3.26 (`POINT_CLOUD_MIN_QGIS_VERSION_INT = 32600`) — `core/domain/point_cloud_support.py:14`, garde en `core/domain/point_cloud_support.py:74`.
- L'option nuage est désormais active par défaut — `config/config.default.json:745-748`. Cela contredit la mémoire `point-cloud-merge-2026-10-01.md`, qui date de la fusion initiale (désactivée par défaut) : le code fait foi.

**Filtrage (subset strings)**
- Critères purs Python : `PointCloudFilterCriteria` — `core/domain/point_cloud_filter_criteria.py:131` ; rendu en subset string (`Classification IN (...)`, plages, `ReturnNumber`, clauses libres) — `core/domain/point_cloud_filter_criteria.py:179-198`.
- Ports sans QGIS : `PointCloudRepositoryPort`, `PointCloudFilterPort` — `core/ports/point_cloud_port.py:17`, `core/ports/point_cloud_port.py:29` ; registre d'attributs — `core/domain/point_cloud_attributes.py`.
- Adaptateur QGIS : lecture du résumé `read_point_cloud_summary` — `adapters/qgis/point_cloud_layer_adapter.py:154` ; application du subset — `adapters/qgis/point_cloud_layer_adapter.py:179`.
- Panneau EXPLORING nuage à quatre groupes : classes `ui/widgets/coverage_panels/point_cloud_exploring_panel.py:1061`, plages `:1175`, hauteur `:1253`, expression `:1374`.
- Application et aperçu : `_apply_point_cloud_preview` — `ui/controllers/coverage_mode_controller.py:1922` ; `_run_filter` — `ui/controllers/coverage_mode_controller.py:2841` ; propagation aux dalles du même dossier — `ui/controllers/coverage_mode_controller.py:2936`.

**Pipettes et zone**
- Lecture sous le curseur : `attributes_at` — `adapters/qgis/point_cloud_layer_adapter.py:227`, `class_at` — `:269`, `attribute_value` — `:247`, classe majoritaire `dominant_class` — `:212`. Passent par `QgsMapToolIdentify` — `:233-236`.
- Réactions du contrôleur : classe `ui/controllers/coverage_mode_controller.py:2328`, valeur `:2363`, objet `:2385`.
- Outil Zone : `ShapeZoneTool` (rectangle, polygone, main levée, rayon) — `ui/tools/zone_tools.py:29`, `ui/tools/zone_tools.py:65`, branché par `ui/controllers/coverage_dock_extras.py:1029` et `:1580`.

**Détection d'objets LiDAR**
- `object_footprint` (classe + grille) — `adapters/qgis/coverage_layers/point_cloud_objects.py:238` ; `class_footprint` — `:350` ; `similar_objects_footprint` — `:379` ; cellule de 2 m `OBJECT_RESOLUTION` — `:45` ; `class_subset` — `:339`.
- Contrôleur : `_pick_point_cloud_object` — `ui/controllers/coverage_mode_controller.py:2400`, `_similar_point_cloud_objects` — `:2546`.

**Hauteur / MNT**
- `filters.hag_dem` de PDAL réécrit un COPC doté de `HeightAboveGround`, ensuite filtrable en subset ; 2,2 M points en 14 s mesurés sur la Cerdagne — `adapters/qgis/coverage_layers/hag_task.py:1-10`, pipeline `:126-135` ; déclenchement `ui/controllers/coverage_mode_controller.py:3424`.

**Export**
- `PointCloudExportJob` — `adapters/qgis/coverage_layers/exporters.py:205` ; formats LAZ, LAS, COPC, GPKG, CSV — `:24` ; tâche `make_export_task` — `:349`.

**Automatisation**
- Neuf algorithmes Processing, dont `filter_point_cloud` — `processing/algorithms/layer_operations_algorithms.py:61`, `cross_filter_from_point_cloud` — `processing/algorithms/cross_filter_algorithm.py:228`, `cross_filter_from_geometry` — `:276`, `export_filtered_layers` — `processing/algorithms/layer_operations_algorithms.py:185`, `batch_filter` — `processing/algorithms/batch_filter_algorithm.py:131`. Quatre modèles dans `processing/models/`.
- API Python : `cross_filter_by_geometry` — `adapters/public_api/operations.py:681`, `filter_point_clouds` — `:728`, `export_layers` — `:842`.
- REST : `POST /geometry` (WKT + CRS + buffer) — `filtermate_api/routers/filters.py:306`, `POST /point-cloud` — `:325`, export — `filtermate_api/routers/export.py:84`. MCP : `point_cloud_filter` — `filtermate_api/mcp/server.py:287-288`.

**Profil existant**
- `_open_elevation_profile` déclenche simplement l'action `mActionElevationProfile` après `setActiveLayer` — `ui/controllers/coverage_dock_extras.py:67`, `:1630-1645`, proposé dans le menu « ⋯ » — `:1283-1292`.
- Le bouton dédié `pushButton_exploring_point_cloud_profile` est listé dans `RAIL_ORDER` (`ui/layout/mockup_layout.py:187`) mais n'est pas créé : il est absent de `RAIL_TOOLS` (`ui/controllers/coverage_dock_extras.py:231-235`) et les specs sont filtrées (`:447`).
- Le plan 5.0 listait déjà « profil d'élévation (`QgsElevationProfileCanvas`…) » parmi les outils — `docs/internal/plans/V5_RASTER_LIDAR_PLAN.md:243`.

**`filtermate_core/`**
- Absent de `main` : le dossier n'existe pas à la racine, et le commit 80285f48 n'est pas ancêtre de `main` (vérifié par `git merge-base --is-ancestor`). Il vit sur les branches `claude/s0-*` et dans `.claude/worktrees/s0-filtermate-core/filtermate_core/`, qui contient `domain/point_cloud_attributes.py`, `point_cloud_filter_criteria.py`, `point_cloud_support.py`.

### Inferences
- La partie réutilisable sans changement est le critère de sélection des points : une coupe peut prendre en entrée le subset déjà composé dans le panneau (classes, plages, hauteur).
- Un futur module de coupe pur (projection distance/décalage, gabarits de sortie) irait logiquement dans `core/domain` aujourd'hui, puis `filtermate_core` si les PR S0 sont fusionnées. C'est une décision à prendre, pas un fait établi.

### Gaps
- L'état d'avancement des PR #232 à #235 n'a pas été recherché sur GitHub ; seule l'absence dans `main` est établie.

## Comment les nuages sont-ils lus, et quelles voies peuvent alimenter l'extraction d'une tranche ?

### Takeaway
Le plugin lit les points par **`provider.identify()`** (dicts Python, tous attributs) et les écrit par **`QgsPointCloudLayerExporter`** ou **PDAL en ligne de commande**. Il n'utilise ni `QgsPointCloudRequest` ni `QgsPointCloudBlock`, et ces voies ne sont de toute façon pas exploitables proprement depuis Python. Pour une tranche, l'exporteur avec `setFilterGeometry` + `setZRange` et `identify` sur un polygone de couloir sont les deux voies viables.

### Cited Findings
**`identify`**
- Boucle bornée `_read_xy` : tuiles, budget de 200 000 points par appel, plafond global par défaut de 3 M, découpage des tuiles saturées — `adapters/qgis/coverage_layers/point_cloud_footprint.py:212-250`, constantes `:31`, `:33`, appel `:232`.
- `_split` prévoit déjà le cas d'un couloir (« a corridor is cut along its length ») — `adapters/qgis/coverage_layers/point_cloud_footprint.py:192-199`.
- `_read_xy` ne garde que X et Y (`:245-246`), mais les dicts contiennent les autres attributs, par exemple `Classification` — `adapters/qgis/coverage_layers/point_cloud_objects.py:267`.
- Signature `identify(maxErrorInMapCoords, extentGeometry, extentZRange, pointsLimit)` : prend une géométrie quelconque et un intervalle Z, mais n'applique pas les propriétés d'élévation de la couche — [QgsPointCloudDataProvider](https://qgis.org/pyqgis/master/core/QgsPointCloudDataProvider.html).
- Mesure du plan 5.0 : `identify` avec `maxError` 0 sur un polygone renvoie 8 144 points, le même nombre que `setFilterGeometry` de l'exporteur — `docs/internal/plans/V5_RASTER_LIDAR_PLAN.md:82-83`.
- Débit : environ 30 000 points/s en dicts (mémoire `v5-object-detection-cores-2026-10-18.md`, non revérifié).

**Exporteur**
- `QgsPointCloudLayerExporter` (3.28) : `setFilterGeometry` (CRS du nuage), `setZRange`, `setPointsLimit`, formats Memory, Las, Gpkg, Shp, Dxf, Csv — [QgsPointCloudLayerExporter](https://qgis.org/pyqgis/master/core/QgsPointCloudLayerExporter.html).
- Déjà utilisé avec un polygone pour découper une cible — `adapters/qgis/coverage_layers/target_appliers.py:979-986`. Repli à la 3.28 géré par `point_cloud_exporter_class` — `adapters/qgis/coverage_layers/point_cloud_footprint.py:64-75`.

**PDAL en ligne de commande**
- `read_stages(source, bounds, polygon)` et `run_pipeline` — `adapters/qgis/coverage_layers/pdal_cli.py:204`, `:253`. Découpe distante conditionnée à PDAL ≥ 2.4 — `adapters/qgis/coverage_layers/target_appliers.py:853`.

**Voies bas niveau**
- `QgsPointCloudIndex` n'est exposé que depuis 3.42 — [qgspointcloudindex.sip.in](https://raw.githubusercontent.com/qgis/QGIS/master/python/PyQt6/core/auto_generated/pointcloud/qgspointcloudindex.sip.in), confirmé par le commentaire de `adapters/qgis/coverage_layers/point_cloud_footprint.py:124`. Ce fichier sip n'expose pas `nodeData` ; on n'y trouve que `getNode`, `root`, `hasNode`, etc.
- `QgsPointCloudBlock.data()` est un pointeur brut typé `str | None` en Python, et la classe est marquée expérimentale — [QgsPointCloudBlock](https://qgis.org/pyqgis/master/core/QgsPointCloudBlock.html).
- `QgsPointCloudRequest` date de 3.18, `setFilterRect` de 3.30 — [API C++](https://api.qgis.org/api/classQgsPointCloudRequest.html). La page PyQGIS de cette classe a répondu 404 lors de la recherche.
- Aucune occurrence de `QgsPointCloudRequest` ni de `QgsPointCloudBlock` dans `adapters`, `core`, `processing`, `ui`, `infrastructure`, `extensions`, `filtermate_api` (recherche du 2026-11-09).

**Pièges inscrits dans le code (vérifiés)**
- Un traitement en thread doit lire une copie privée de la couche : `private_point_cloud` — `adapters/qgis/coverage_layers/exporters.py:176` ; même règle pour les tâches source — `adapters/qgis/coverage_layers/source_jobs.py:510-512`. La mémoire `v5-pc-export-private-layer-2026-10-17.md` en donne la cause mesurée : depuis 3.42 l'index est partagé, un export « classe 9 » (0 point) a écrit 34 Mo quand le filtre affiché a changé (non revérifié).
- `prepareExport` doit tourner sur le thread principal — `adapters/qgis/coverage_layers/exporters.py:208`, `adapters/qgis/coverage_layers/target_appliers.py:867`.
- L'exporteur lit l'index sans le vérifier et plante sur un index nul, d'où `index_ready` — `adapters/qgis/coverage_layers/exporters.py:234-238`.
- Les VPC sont refusés en export (`exporters.py:235`), en source (`source_jobs.py:507-508`) et pour les objets (`point_cloud_objects.py:231`).
- QGIS met les blocs en cache sous le texte du subset, et une copie filtrée juste après ouverture a servi tous les points : `open_point_cloud` désactive statistiques et index — `adapters/qgis/coverage_layers/point_cloud_footprint.py:101-118` ; le subset est réécrit entre parenthèses pour changer la clé de cache — `adapters/qgis/coverage_layers/source_jobs.py:524-528`, `adapters/qgis/coverage_layers/point_cloud_objects.py:339-347`. La clé de cache inclut bien le filtre — [qgspointcloudindex.cpp](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudindex.cpp).
- `identify` omet les points sur le bord de l'emprise : l'emprise est élargie d'une demi-cellule — `adapters/qgis/coverage_layers/point_cloud_footprint.py:277`, `adapters/qgis/coverage_layers/point_cloud_objects.py:271`.
- Un nuage en SCR géographique se lit en degrés : conversion par `layer_resolution` — `adapters/qgis/coverage_layers/point_cloud_footprint.py:53-62`.
- Un COPC distant ne peut pas être lu comme source sans zone — `adapters/qgis/coverage_layers/source_jobs.py:515-519`.

### Inferences
- Tranche simple au format fichier : réutiliser le patron de `PointCloudExportJob` en ajoutant `setFilterGeometry(couloir)` et `setZRange`. Le GPKG est déjà proposé par `POINT_CLOUD_FORMATS` ; le DXF est un format de l'exporteur que cette table ne propose pas encore.
- Tranche analysable avec la classe et l'intensité : `identify` sur le polygone de couloir, en extrayant `X, Y, Z, Classification, Intensity` au lieu de X/Y seuls. Il faut garder l'élargissement du bord, puis recouper exactement sur le polygone.
- La copie privée vaut aussi pour une coupe en tâche de fond, quelle que soit la voie choisie.

### Gaps
- Pas de débit mesuré pour une tranche LiDAR HD réelle ; le chiffre de 30 000 points/s vient d'un autre usage.
- Non vérifié : les noms exacts des clés Z et intensité renvoyées par `identify` selon les fournisseurs (COPC, EPT, LAS indexé).

## Comment la ligne de coupe et son couloir s'insèrent-ils dans le modèle géométrique et l'interface ?

### Takeaway
Le modèle **source géométrique + tampon** accueille naturellement une ligne : une ligne plus un tampon plat donne exactement un couloir. Le verrou est ailleurs : le subset d'un nuage ne connaît que des boîtes X/Y, donc **une coupe oblique ne peut pas être un simple filtre de couche**. Elle doit être un produit dérivé (fichier, couche, profil). L'outil Zone doit gagner une forme « ligne », car il ne produit aujourd'hui que des polygones.

### Cited Findings
**Sources et tampons**
- `SourceJob.compute` et `_buffer`, avec passage en UTM pour un SCR géographique — `adapters/qgis/coverage_layers/source_jobs.py:48-71`.
- `FixedGeometrySourceJob` accepte n'importe quel WKT — `adapters/qgis/coverage_layers/source_jobs.py:592-602`, utilisé par `cross_filter_by_geometry` — `adapters/public_api/operations.py:681-712`.
- `CrossFilterRequest` porte `buffer_value`, `buffer_segments`, `buffer_type` (`Round`, `Flat`, `Square`) — `core/domain/cross_filter.py:197-207`.
- `buffer_geometry` applique ces styles ; `Flat` donne des extrémités plates et des jonctions en onglet — `adapters/qgis/coverage_layers/geometry_tools.py:28-62`.
- Une source linéaire sans tampon est refusée (« the source geometry has no area (lines or points only): add a buffer ») — `adapters/qgis/coverage_layers/target_appliers.py:67`, levé notamment dans le chemin de la cible nuage `:920`.
- Le couloir natif de QGIS est un tampon de la ligne de `tolerance`, à extrémités plates, jonctions rondes, 8 segments par quart — [générateur de profil](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.cpp).

**Limite du subset**
- La docstring de la zone le dit : « the subset string of the cloud only knows the box » — `ui/widgets/coverage_panels/point_cloud_exploring_panel.py:1481-1488`. Le WKT exact est conservé à part pour les cibles — `:1497`, relu par `_zone_geometry` — `ui/controllers/coverage_mode_controller.py:2083-2095`. Même constat dans `adapters/qgis/coverage_layers/source_jobs.py:489-495`.

**Outil de tracé**
- `SHAPES` se limite à des formes surfaciques — `ui/tools/zone_tools.py:29` ; `polygon_wkt` renvoie une chaîne vide sous trois sommets — `ui/tools/zone_tools.py:44` ; la bande élastique est de type polygone — `ui/tools/zone_tools.py:107`.
- L'outil natif de QGIS propose « Capture Curve » et « Capture Curve From Feature », un décalage latéral de la tolérance (« Nudge »), et le verrouillage d'échelles — [manuel QGIS, profil d'élévation](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html).

**Rail et synchronisation**
- Ordre commun `RAIL_ORDER` — `ui/layout/mockup_layout.py:168-190`. Menus par type — `ui/controllers/coverage_dock_extras.py:231-235`.
- Règles R1 à R5 entre outil et groupe — `ui/controllers/selection_modes.py:7-12`. Pour le nuage, les groupes sont `classes`, `ranges`, `expression` ; un bouton absent d'un type est « partagé » — `ui/controllers/selection_modes.py:21-42`.

**Objets comme graines**
- Un objet détecté fournit un polygone exact — `adapters/qgis/coverage_layers/point_cloud_objects.py:238-289`, conservé en WKT — `ui/widgets/coverage_panels/point_cloud_exploring_panel.py:1625`.

### Inferences
- Représentation proposée : une section est une `QgsLineString` + demi-largeur + intervalle Z, stockée à côté du subset. Sa géométrie tamponnée peut servir de source de filtre pour les cibles vecteur et raster via `cross_filter_by_geometry` (par exemple « bâtiments traversés par la coupe »).
- Les points de la coupe ne doivent pas être obtenus par filtrage de la couche affichée, sauf ligne parallèle aux axes, où la boîte X/Y coïncide avec le couloir.
- Surfaces d'interface naturelles, par coût croissant : (1) entrée « Coupe… » dans le menu ⋯ du nuage, à côté de l'entrée existante ; (2) activer le bouton `pushButton_exploring_point_cloud_profile`, déjà réservé dans `RAIL_ORDER` ; (3) un groupe « COUPE » dans le panneau, mais il entrerait dans l'exclusivité des groupes, alors qu'une coupe consomme le filtre courant au lieu de le remplacer. Un bouton partagé, hors `GROUP_TOOLS`, paraît donc plus cohérent.
- Ligne depuis une entité vecteur sélectionnée : le modèle `VectorSourceJob` et la sélection du rail vecteur s'y prêtent. Un axe proposé à partir de l'objet cliqué est une idée possible, mais la cellule de 2 m est grossière pour une coupe.

### Gaps
- Une expression de tranche oblique, du type `abs((X-x0)*a + (Y-y0)*b) <= d`, éviterait la limite des boîtes si `QgsPointCloudExpression` accepte l'arithmétique et `abs`. Non vérifié : la grammaire n'a pas été consultée, et rien n'indique le coût côté décodage.

## Quelles API QGIS conviennent, depuis quelle version, et quelles sont les différences entre 3.x et 4.x ?

### Takeaway
Tout le socle natif existe en Python depuis **3.26** (requête, génération, tracé) et devient vraiment productif à partir de **3.32** (export). Le minimum du plugin (3.22, ou 3.26 pour le nuage) impose des gardes de version. Le profil natif a deux limites structurantes pour une coupe analytique : **il ne conserve ni classe ni intensité par point**, et **sa densité dépend d'un contexte d'écran**.

### Cited Findings
**Tableau des versions (pages PyQGIS `master`)**

| Élément | Depuis | Remarque | Source |
|---|---|---|---|
| `QgsProfileRequest` | 3.26 | `setCrs`, `setTolerance`, `setStepDistance`, `setTerrainProvider` | [doc](https://qgis.org/pyqgis/master/core/QgsProfileRequest.html) |
| `QgsProfileGenerationContext` | 3.26 | `setMapUnitsPerDistancePixel`, `setMaximumErrorMapUnits` (NaN = précision maximale), `setDistanceRange`, `setElevationRange` | [doc](https://qgis.org/pyqgis/master/core/QgsProfileGenerationContext.html) |
| `createProfileGenerator` | 3.26 | via `QgsAbstractProfileSource`, dont hérite `QgsPointCloudLayer` | [doc](https://qgis.org/pyqgis/master/core/QgsAbstractProfileSource.html) |
| `QgsAbstractProfileGenerator` | 3.26 | créé sur le thread principal, `generateProfile` sur un thread de travail | [doc](https://qgis.org/pyqgis/master/core/QgsAbstractProfileGenerator.html) |
| `QgsAbstractProfileResults` | 3.26 | `sampledPoints`, `asGeometries`, `zRange` ; `asFeatures` depuis 3.32 | [doc](https://qgis.org/pyqgis/master/core/QgsAbstractProfileResults.html) |
| `QgsProfilePlotRenderer` | 3.26 | `renderToImage`, `render` ; `generateSynchronously` 3.30 (bloquant, déconseillé) ; `asFeatures` 3.32 | [doc](https://qgis.org/pyqgis/master/core/QgsProfilePlotRenderer.html) |
| `QgsElevationProfileCanvas` | 3.26 | échelles verrouillables 3.32 ; `setAxisScaleRatio` 4.0 ; `dataElevationRange` 4.2 | [doc](https://qgis.org/pyqgis/master/gui/QgsElevationProfileCanvas.html) |
| `QgsLayoutItemElevationProfile` | 3.30 | `setAtlasDriven` sur une couverture linéaire | [doc](https://qgis.org/pyqgis/master/core/QgsLayoutItemElevationProfile.html) |
| `QgsProfileExporter` | 3.32 | `run` utilisable en arrière-plan, `toLayers` | [doc](https://qgis.org/pyqgis/master/core/QgsProfileExporter.html) |
| `QgsProfileExporterTask` | 3.32 | `QgsTask`, destination fichier, `DxfExportFailed` | [doc](https://qgis.org/pyqgis/master/core/QgsProfileExporterTask.html) |
| `maximumScreenError` | 3.26 | sur les propriétés d'élévation du nuage | [doc](https://qgis.org/pyqgis/master/core/QgsPointCloudLayerElevationProperties.html) |
| `QgsPointCloudLayer.index()` | 3.42 | index accessible en Python | [doc](https://qgis.org/pyqgis/master/core/QgsPointCloudLayer.html) |
| Profil triangulé (`TriangulatedSurface`) | 4.0 | `setType`, `setProfileSymbology` | [doc](https://qgis.org/pyqgis/master/core/QgsPointCloudLayerElevationProperties.html) |

**Comportement du générateur nuage**
- Résultat par point : `x, y, z, distanceAlongCurve, distanceFromCurve, color`, **sans classification ni intensité** ; classe en `SIP_NO_FILE`, donc non exposée en Python — [en-tête du générateur](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.h).
- `asFeatures` : point 3D sans attribut (`Features3D`), point `(distance, z)` sans attribut (`Profile2D`), point 3D avec seulement `distance` et `elevation` (`DistanceVsElevationTable`) — [générateur](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.cpp).
- Parcours de l'octree : descente tant que l'erreur dépasse le maximum en pixels. `maximumScreenError` vient des propriétés de la couche (défaut 0,3 mm) et est plafonné par `tolérance_en_pixels / 4`. Aucun plafond du nombre de points — [générateur](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.cpp).
- Le générateur prend `layer->index()` et les sous-index du fournisseur, en ne retenant que ceux qui intersectent le couloir. Il ne pose pas de filtre sur sa requête — [générateur](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.cpp).
- L'index COPC applique son propre `mFilterExpression` au décodage, sauf `ignoreIndexFilterEnabled` — [qgscopcpointcloudindex.cpp](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgscopcpointcloudindex.cpp).
- `maximumErrorMapUnits` : la doc de contexte indique NaN = précision maximale — [contexte](https://qgis.org/pyqgis/master/core/QgsProfileGenerationContext.html).

**Différences 3.x / 4.x et compatibilité**
- `QgsPointCloudIndex` wrapper depuis 3.42, `QgsPointCloudNode` 3.42 — [sip](https://raw.githubusercontent.com/qgis/QGIS/master/python/PyQt6/core/auto_generated/pointcloud/qgspointcloudindex.sip.in).
- `subIndexes()` documenté en Python à partir de 4.0 — [QgsPointCloudDataProvider](https://qgis.org/pyqgis/master/core/QgsPointCloudDataProvider.html).
- `profileSourceId` et `profileSourceName` en 4.0, sources personnalisées via `setSources` — [QgsAbstractProfileSource](https://qgis.org/pyqgis/master/core/QgsAbstractProfileSource.html), [canvas](https://qgis.org/pyqgis/master/gui/QgsElevationProfileCanvas.html).
- Patrons de compatibilité déjà présents : import gardé (`adapters/qgis/coverage_layers/point_cloud_footprint.py:64-75`), `getattr` sur énumérations (`adapters/qgis/point_cloud_layer_adapter.py:233-236`), repli d'options de création (`adapters/qgis/coverage_layers/exporters.py:39`).

### Inferences
- Une garde « coupe disponible à partir de 3.32 » est raisonnable. Entre 3.26 et 3.31, seule la génération sans export natif resterait possible, ce qui ne mérite probablement pas une branche de code.
- Une coupe par classe avec l'API native exige une passe par classe sur une copie privée filtrée. Le filtre de la couche devrait se propager, puisque le générateur lit `layer->index()` et que l'index COPC filtre au décodage, mais cette chaîne n'a pas été testée.
- La copie privée compte aussi ici : le générateur partage l'index de la couche qu'on lui donne, comme l'exporteur dans le piège documenté.
- Pour une tranche exhaustive, ne pas dépendre du profil natif : son volume varie avec le contexte. L'exporteur ou `identify` à `maxError` 0 sont plus prévisibles.
- Le type triangulé de la 4.0 offre une surface continue en coupe, utile pour un rendu « trait de terrain », mais uniquement à partir de 4.0.

### Gaps
- Non établi : le comportement du générateur vis-à-vis des VPC avant 4.0. Les sous-index figurent dans la classe de base « since 4.0 », et aucune source consultée ne décrit les versions antérieures.
- Non testé : combien de points le profil natif renvoie selon `setMapUnitsPerDistancePixel` et `setDpi` sur un COPC LiDAR HD, et si une valeur de contexte permet d'atteindre tous les points.
- Non confirmé : qu'un sous-classement Python de `QgsAbstractProfileSource` est stable. La doc dit que seules les méthodes virtuelles se surchargent sûrement.
- Le manuel consulté couvre la 3.44 ; les versions d'introduction des options d'interface n'y figurent pas.

## Quelles sorties sont naturelles, et quelles dépendances poseraient problème ?

### Takeaway
GeoPackage, DXF, CSV, SHP, PDF, image et élément de mise en page sont **tous natifs** ; aucune dépendance nouvelle n'est nécessaire pour un premier produit. NumPy suffit pour le calcul. Le SVG passe par la mise en page ou un `QPainter`. Laspy, SciPy, Matplotlib ou ezdxf n'apportent rien qui justifie le risque de packaging.

### Cited Findings
- Export des résultats de profil en DXF, CSV, SHP, GPKG et autres formats vecteur, en trois modes (entités 3D, profil 2D, table distance/altitude), plus PDF et image — [manuel QGIS](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html).
- Tâche d'export avec `createdFiles()` et `takeLayers()` (plusieurs couches possibles si les géométries diffèrent) — [QgsProfileExporterTask](https://qgis.org/pyqgis/master/core/QgsProfileExporterTask.html).
- L'exporteur de nuage écrit Las, Gpkg, Shp, Dxf, Csv, Memory, ce qui donne une tranche sous forme de points — [QgsPointCloudLayerExporter](https://qgis.org/pyqgis/master/core/QgsPointCloudLayerExporter.html).
- `renderToImage` et `render` sur `QgsRenderContext` — [QgsProfilePlotRenderer](https://qgis.org/pyqgis/master/core/QgsProfilePlotRenderer.html). Élément de mise en page pilotable par atlas — [QgsLayoutItemElevationProfile](https://qgis.org/pyqgis/master/core/QgsLayoutItemElevationProfile.html).
- Le code livré n'importe NumPy qu'à l'exécution (`adapters/qgis/coverage_layers/point_cloud_footprint.py:220`, `:272`). Une recherche sur le code d'exécution ne trouve aucun import de `scipy`, `laspy`, `matplotlib`, `shapely`, `ezdxf`, `pyproj`, `lazrs`, `open3d`, `pdal` ou `pandas`.
- `requirements-api.txt` ne liste que FastAPI, Uvicorn, Pydantic, pour l'API optionnelle — `requirements-api.txt:3-5`.
- Scan de plugins.qgis.org : Bandit + detect-secrets bloquent la version au moindre constat critique, même faux positif ; un contrôle Qt6 refuse les énumérations non qualifiées — mémoire `plugin-repo-security-scan.md` (non revérifié auprès du dépôt). Reproduction prévue sur le zip de `scripts/prepare_plugin_zip.sh`.
- Les appels `subprocess` de PDAL sont déjà annotés `# nosec B404/B603` — `adapters/qgis/coverage_layers/pdal_cli.py:15`, `:109`, `:132`, `:271`.

### Inferences
- Jeu de sorties cohérent pour un premier produit : GPKG (lignes et points de coupe, avec attributs ajoutés par le plugin), DXF natif pour l'échange avec les logiciels de CAO, CSV pour la table, image et élément de mise en page pour la planche.
- SVG : la voie la plus simple paraît être l'export SVG d'une mise en page contenant `QgsLayoutItemElevationProfile`, ou `render` sur un `QSvgGenerator`. Non vérifié dans cette recherche.
- Dépendances à éviter : tout paquet à extension binaire (laspy avec lazrs, Open3D) ne s'installe pas via le dépôt de plugins et imposerait un pip manuel à l'utilisateur. Shapely est présent seulement sur les branches S0.
- Un nouveau SQL ou un nouveau nom de variable sensible (`token`, `password`) dans le module de coupe suit les mêmes règles de scan que le reste. Un module de coupe sans SQL ni sous-processus reste a priori hors de portée de ces alertes.

### Gaps
- Pas de source consultée sur la présence garantie de NumPy ou Matplotlib dans chaque distribution QGIS ; le code suppose NumPy à l'exécution pour les fonctions concernées.
- Pas de règle écrite trouvée sur le vendoring de binaires dans plugins.qgis.org.

## Quels paliers de faisabilité se dégagent ?

### Takeaway
Un **premier palier réaliste** enchaîne ligne + largeur + filtre courant, puis `QgsProfileExporterTask` et l'élément de mise en page : peu de code nouveau, surtout du câblage. La **valeur propre à FilterMate** arrive au second palier : coupes par classe, attributs conservés, ligne de sol ou de toit. Le reste relève de logiciels métier.

### Cited Findings
- Base de tout le palier 1 : API et versions du tableau précédent ; `QgsProfileExporterTask` (3.32) — [doc](https://qgis.org/pyqgis/master/core/QgsProfileExporterTask.html).
- Points d'ancrage existants : entrée de menu `ui/controllers/coverage_dock_extras.py:1283-1292`, bouton réservé `ui/layout/mockup_layout.py:187`, tâche d'export `adapters/qgis/coverage_layers/exporters.py:349`, tampon plat `adapters/qgis/coverage_layers/geometry_tools.py:44`, Processing `processing/algorithms/layer_operations_algorithms.py`, REST `filtermate_api/routers/filters.py:306`.
- Absence de classe dans les résultats natifs, qui motive le palier 2 — [en-tête du générateur](https://raw.githubusercontent.com/qgis/QGIS/master/src/core/pointcloud/qgspointcloudlayerprofilegenerator.h).
- Lecture bornée déjà écrite, réutilisable pour le palier 2 — `adapters/qgis/coverage_layers/point_cloud_footprint.py:212-250`.

### Inferences
**Palier 1 : câblage natif (peu d'algorithmique)**
- Forme « ligne » dans `ShapeZoneTool`, ou reprise d'une entité linéaire sélectionnée, avec demi-largeur.
- Aperçu du couloir (tampon plat) sur le canevas, en réutilisant le principe de `adapters/qgis/coverage_layers/preview_overlay.py`.
- Copie privée du nuage au filtre courant, puis `QgsProfileExporterTask` vers GPKG, DXF ou CSV.
- `QgsPrintLayout` avec `QgsLayoutItemElevationProfile`, et atlas sur une couche de lignes de coupe.
- Tranche brute : `QgsPointCloudLayerExporter` + `setFilterGeometry` + `setZRange`, sur le patron de `PointCloudExportJob`.
- Algorithme Processing `filtermate:section_from_line` et route REST, sur le modèle de `cross_filter_from_geometry`.

**Palier 2 : nouveau code algorithmique (NumPy, Python pur testable)**
- Extraction par `identify` sur le couloir, avec `Classification` et `Intensity` conservés, recoupe exacte, gestion du bord et des saturations.
- Projection sur la polyligne (distance curviligne, décalage signé), y compris coudes et sommets : c'est le cœur à écrire et à tester.
- Polylignes par classe : enveloppe haute, sol, toit, par intervalles de distance. Une passe par classe avec le profil natif reste une alternative moins riche.
- Couches de coupe attributées (identifiant de section, classe, nombre de points, épaisseur).
- Lots de coupes parallèles et équidistantes, à intervalle réglable, avec gestion des dalles voisines. `_apply_to_sibling_tiles` donne une logique de voisinage pour un dossier de dalles.
- Coupe sur hauteur au-dessus du MNT : le COPC dérivé de `HeightAboveGroundTask` (`adapters/qgis/coverage_layers/hag_task.py:73`) fournit `HeightAboveGround` comme attribut.

**Hors périmètre probable**
- Reconstruction volumique ou BIM (IFC, façades, toitures paramétriques) ; dessin architectural normalisé ; exports DWG natifs.
- Accès bloc par bloc en Python, non exposé proprement.
- Traitement massif pleine résolution sur de grandes étendues depuis l'interface, qui relève de PDAL ou d'un outil externe.
- Présenter une coupe oblique comme un filtre de couche, puisque le subset ne connaît que des boîtes.

**Séquence suggérée**
- D'abord une preuve de concept hors interface (sonde courte, fenêtre réduite, à valider avec l'utilisateur) : comparer le nombre de points du profil natif avec celui de `identify` à `maxError` 0 sur un même couloir, et vérifier que le subset se propage bien. Ces deux réponses décident de l'architecture.

### Gaps
- Aucun chiffre de coût n'a été produit : les charges ci-dessus sont des ordres de grandeur qualitatifs.
- Non évalué ici : les besoins métier et la densité LiDAR HD, traités par d'autres recherches.
