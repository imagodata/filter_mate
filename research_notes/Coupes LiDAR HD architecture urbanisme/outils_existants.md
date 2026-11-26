# Outils existants pour produire des coupes ou profils à partir de nuages de points (état au 9 novembre 2026)

Notes de recherche. Versions consultées indiquées dans chaque section. Les réponses s'appuient sur la documentation officielle quand elle a été lisible. Les sources de moindre poids (blogs d'éditeurs, forums) sont signalées comme telles.

Rappel de lecture : « Lit le COPC » n'a pas le même sens partout. Un fichier `.copc.laz` est un LAZ 1.4 valide ([Lauria Escaner, sept. 2026](https://www.lauriaescaner.com/fr/blog/lidar-hd-ign/)). Un outil peut donc l'ouvrir comme un LAZ ordinaire, en entier, sans exploiter l'index. Les notes distinguent ce cas de la lecture partielle (par emprise, ou à distance en HTTP Range).

## QGIS natif : que fait exactement l'outil de profil d'élévation en 3.40–4.x ?

### Takeaway
Parmi les outils libres examinés, QGIS est le plus complet pour tracer et exporter un profil de nuage de points dans un corridor le long d'une ligne. En mode points individuels, il exporte toutefois des points, pas un dessin de coupe. Il n'a pas de filtre de classe propre au profil, et la documentation ne décrit pas de vectorisation de la silhouette coupée.

### Cited Findings

**Versions**
- QGIS 4.0 est sorti le 2026-03-06 ([changelog 4.0](https://www.qgis.org/project/visual-changelogs/visualchangelog40/)) et QGIS 4.2 le 2026-07-03 ([changelog 4.2](https://www.qgis.org/project/visual-changelogs/visualchangelog42/)).
- Une source tierce annonçait la 4.2 comme future LTR pour octobre 2026 ([MIERUNE](https://qgis.mierune.co.jp/en/posts/blog_new_402)). Ce statut n'a pas été confirmé par une source officielle.
- La page « latest » du manuel servait encore la 3.44 ([manuel](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html)). L'URL 4.2 servait la branche « testing », mise à jour le 2026-11-08 ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)).

**Corridor et tolérance**
- La tolérance définit la distance maximale à la ligne de profil, en unités de carte, et dessine un tampon plat sur le canevas. Les couches points, lignes et polygones peuvent la remplacer par une valeur propre ([manuel 3.44](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html)).
- Une tolérance plus grande renvoie plus de points du nuage ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)).
- Nudge Left et Nudge Right décalent latéralement la ligne d'une distance égale à la tolérance ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)).

**Rendu du nuage dans le profil**
- Les propriétés d'élévation d'un nuage proposent deux interprétations : « Individual points » et « Triangulated surface ». S'y ajoutent la taille et le style des points, une couleur unique ou « Respect layer's coloring », une opacité selon la distance à la courbe, et une erreur maximale ([manuel testing, nuages de points](https://docs.qgis.org/4.2/en/docs/user_manual/working_with_point_clouds/point_clouds.html)).
- QGIS 4.0 ajoute le rendu en ligne d'élévation continue, un rapport d'échelle distance:élévation, et un gestionnaire qui conserve les profils avec le projet ([changelog 4.0](https://www.qgis.org/project/visual-changelogs/visualchangelog40/)).
- QGIS 3.44 ajoute des indicateurs de sous-sections, en vue profil et en mise en page ([changelog 3.44](https://qgis.org/project/visual-changelogs/visualchangelog344/)).
- QGIS 4.2 ajoute « Show Profile in 3D Views » ([changelog 4.2](https://www.qgis.org/project/visual-changelogs/visualchangelog42/)).

**Export**
- Le PDF est vectoriel. Les images sont exportées dans plusieurs formats raster. Les résultats s'exportent en DXF, CSV, Shapefile ou GeoPackage, sous trois formes : entités 3D, profil 2D, table distance/élévation ([manuel 3.44](https://docs.qgis.org/latest/en/docs/user_manual/map_views/elevation_profile.html)). L'export des résultats date de la 3.32 ([changelog 3.32 via entrée 2441](https://changelog.qgis.org/en/entry/2441)).
- Dans le code `master` (4.3), chaque point exporté devient une géométrie ponctuelle : `QgsPoint(x,y,z)` en 3D, `QgsPoint(distance, z)` en 2D, attributs `distance` et `elevation` en table. Aucun plafond de nombre de points n'apparaît dans la partie lue, soit les 100 000 premiers caractères de la page ([source C++](https://api.qgis.org/api/master/qgspointcloudlayerprofilegenerator_8cpp_source.html)).
- QGIS 3.42 ajoute un algorithme Processing qui génère des images de profil ([changelog 3.42](https://www.qgis.org/project/visual-changelogs/visualchangelog342/)).

**Filtrage par classe**
- Le manuel ne décrit aucun filtre de classe dédié au profil ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)).
- Deux mécanismes généraux existent. Le premier est le filtre fournisseur (Query Builder), qui traite le sous-ensemble comme la couche entière. Le second consiste à décocher une classe dans le rendu Classification ([manuel testing, nuages de points](https://docs.qgis.org/4.2/en/docs/user_manual/working_with_point_clouds/point_clouds.html)).
- Avec « respecter les couleurs de la couche », le générateur ignore les points dont la couleur renvoyée est invalide (`if (!color.isValid()) continue;`) ([source C++](https://api.qgis.org/api/master/qgspointcloudlayerprofilegenerator_8cpp_source.html)).

**Niveau de détail**
- L'erreur maximale règle la densité : une valeur plus grande donne un résultat plus rapide avec moins de points ([manuel testing, nuages de points](https://docs.qgis.org/4.2/en/docs/user_manual/working_with_point_clouds/point_clouds.html)).
- Le générateur plafonne l'erreur cible à un quart de la tolérance en pixels, puis parcourt l'octree jusqu'à ce seuil ([source C++](https://api.qgis.org/api/master/qgspointcloudlayerprofilegenerator_8cpp_source.html)).

**API Python**
- `QgsProfileExporter` est exposé en PyQGIS depuis la 3.32. Son constructeur prend `(sources, request, type)`. `run()` est utilisable en arrière-plan et `toLayers()` renvoie des `QgsVectorLayer` ([PyQGIS](https://qgis.org/pyqgis/master/core/QgsProfileExporter.html)).
- `QgsPointCloudLayerProfileGenerator` implémente le générateur abstrait pour les nuages ([API C++](https://api.qgis.org/api/3.44/classQgsPointCloudLayerProfileGenerator.html)). La classe de base `QgsPointCloudLayerProfileGeneratorBase`, ajoutée en 4.0, n'est pas disponible en Python ([API master](https://api.qgis.org/api/master/classQgsPointCloudLayerProfileGeneratorBase.html)).

**Mise en page**
- L'élément `QgsLayoutItemElevationProfile` existe depuis la 3.30 ([PyQGIS 3.30](https://qgis.org/pyqgis/3.30/core/QgsLayoutItemElevationProfile.html)).
- Il accepte une courbe copiée d'une vue de profil ou pilotée par un atlas (couverture linéaire), une tolérance définissable par données, et des axes et plages configurables. La page ajoute que seules les entités ponctuelles sont renvoyées actuellement, et elle ne parle pas des nuages ([manuel 3.44](https://docs.qgis.org/3.44/en/docs/user_manual/print_layout/layout_items/layout_elevation_profile.html)).

**Coupe dans la vue 3D**
- Les plans de clipping OpenGL arrivent à l'API en 3.40, avec `enableClipping()`, `disableClipping()` et par défaut jusqu'à 8 plans ([qgs3dmapscene.sip.in, miroir du dépôt QGIS](https://git.sharpetronics.com/sharpetronics/QGIS/src/commit/e38ac6c7b94723c08359b3b90461366fb0d76e55/python/3d/auto_generated/qgs3dmapscene.sip.in)).
- L'outil de coupe 3D arrive en 3.44 : trois clics sur le canevas 2D (début, fin, épaisseur), régions rectangulaires tournées, pas de rechargement de la scène ([changelog 3.44](https://qgis.org/project/visual-changelogs/visualchangelog344/)).
- QGIS 4.0 ajoute une largeur fixe, le décalage gauche/droite, l'exposition du mode coupe en PyQGIS et une caméra orthographique rétablie ([changelog 4.0](https://www.qgis.org/project/visual-changelogs/visualchangelog40/)).

**Limites documentées**
- L'extrusion des polygones est ignorée quand la tolérance est active, et les rasters non marqués comme altimétriques sont ignorés ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)).
- Le manuel indique encore que fermer une vue de profil ou le projet retire la vue du projet ([manuel 4.2/testing](https://docs.qgis.org/4.2/en/docs/user_manual/map_views/elevation_profile.html)). Cela contredit le gestionnaire de profils 4.0 ([changelog 4.0](https://www.qgis.org/project/visual-changelogs/visualchangelog40/)), donc le manuel semble en retard sur ce point.
- Le ticket ouvert #59551 signale qu'un profil sur VPC n'affiche pas les points après déplacement vers une autre dalle ([GitHub #59551](https://github.com/qgis/QGIS/issues/59551)).

### Inferences
- Pour une coupe architecturale, l'export QGIS fournit une nuée de points en DXF, et non des polylignes de silhouette. Il faut donc redessiner ou vectoriser ailleurs. Cette conclusion vient du code d'export lu pour les points individuels.
- Le profil n'est pas garanti à pleine densité : le niveau d'octree dépend de l'erreur maximale et de la tolérance en pixels. À tester sur dalle réelle avant de s'y fier pour un relevé.
- Masquer une classe décochée dans le rendu devrait la retirer du profil si « Respect layer's coloring » est actif. C'est déduit du contrôle générique de couleur invalide, sans essai réel.

### Gaps
- Comportement exact de l'export pour l'interprétation « Triangulated surface » : ligne ou points ? Non établi.
- Prise en compte du filtre fournisseur dans le générateur : rien dans la partie lue du code, qui passe par l'index de la couche.
- Présence effective d'un nuage dans l'élément de mise en page : non documentée. La phrase « seules les entités ponctuelles » reste ambiguë.
- Pages `QgsProfileRequest`, `QgsProfilePlotRenderer` et `QgsElevationProfileCanvas` non lues. Exposition Python de `QgsPointCloudLayerProfileGenerator` non confirmée.
- Aucun exemple PyQGIS complet trouvé pour un profil de nuage.
- Tickets : une seule recherche par titre sur GitHub, donc la liste des limites connues n'est pas exhaustive.

## Extensions QGIS et algorithmes Processing liés aux coupes et au LiDAR HD

### Takeaway
Plusieurs extensions accèdent aux dalles LiDAR HD et d'autres tracent des profils sur raster, mais aucune extension de coupe sur nuage de points n'a été trouvée. Processing permet de découper un nuage, sans algorithme de coupe dédié.

### Cited Findings

**Accès aux dalles LiDAR HD (aucune confirmée sur plugins.qgis.org)**
- `romain974/qgis-lidar-hd` v1.0.0 : affichage des dalles `.copc.laz` de l'emprise en lecture distante (HTTP Range) ou téléchargement, QGIS ≥ 3.32, GPL-2.0-or-later. Archive prête pour soumission, publication non confirmée ([GitHub](https://github.com/romain974/qgis-lidar-hd)).
- `IGNF-Xavier/qgis_gpf_lidarhd_COPC` : Processing, extraction d'une zone en COPC local à partir de la lecture distante. Expérimental, non supporté par l'IGN, GPL v2+, testé surtout sous Windows avec QGIS 3.40 et PDAL 2.10, QGIS 4 non validé ([GitHub](https://github.com/IGNF-Xavier/qgis_gpf_lidarhd_COPC)).
- `frdyvn/lidar_ign_downloader` : téléchargement des dalles et dérivés, QGIS ≥ 3.28 ([GitHub](https://github.com/frdyvn/lidar_ign_downloader)).
- `a-maurin/Telechargeur-LiDAR-HD` : MNT 0,50 m seulement, pas de nuages ([GitHub](https://github.com/a-maurin/Telechargeur-LiDAR-HD)).

**Profils (raster/MNT)**
- Profile tool 4.3.4, avec prise en charge QGIS 4 ([plugins.qgis.org](https://plugins.qgis.org/plugins/profiletool/latest/)).
- Dual Profile Viewer 2.1.0 : MNT/MNS, comparaison de plusieurs MNT, sections par côté de polygone, exports vecteur géoréférencé, CSV, PNG. La page ne mentionne pas les nuages ([plugins.qgis.org](https://plugins.qgis.org/plugins/dual_profile_viewer/version/2.1.0)).
- Advanced Profile Tool : coupes sur axe, multi-MNT, volumes, exports CAO. La fiche ne mentionne pas les nuages ([plugins.qgis.org](https://plugins.qgis.org/plugins/advanced_profile_tool/)).
- Topographic Profile 1.3 (QGIS ≥ 4.0) : la page ne décrit pas sa fonction ([plugins.qgis.org](https://plugins.qgis.org/plugins/Topographical_profiles/latest/)).
- qgis2potree exporte des projets Potree depuis des couches LAS, LAZ ou COPC ([plugins.qgis.org](https://plugins.qgis.org/plugins/qgis2potree/)).

**Processing (pdal_wrench)**
- Le fournisseur natif (3.32) exige PDAL ≥ 2.5.0. Il comprend notamment le découpage par polygones, le filtre PDAL et l'export raster/TIN/vecteur ([changelog](https://changelog.qgis.org/id/entry/2495) ; [wrench](https://github.com/PDAL/wrench)).
- QGIS 3.44 met à jour pdal_wrench en 1.2, ajoute la sortie directe COPC et utilise automatiquement l'index COPC, ce qui accélère notamment le découpage ([changelog 3.44](https://qgis.org/project/visual-changelogs/visualchangelog344/)).
- QGIS 4.0 ajoute hauteur au-dessus du sol (classe 2 requise), classification SMRF, filtre de bruit, transformation et M3C2 ([changelog 4.0](https://www.qgis.org/project/visual-changelogs/visualchangelog40/)).

### Inferences
- Une chaîne reproductible dans QGIS peut combiner découpe Processing par polygone et hauteur au-dessus du sol, mais l'étape « tracer la coupe » reste manuelle ou scriptée.

### Gaps
- Le fournisseur LAStools pour Processing n'a pas été examiné.
- Absence de ces extensions LiDAR HD sur plugins.qgis.org non vérifiée sur le site lui-même.
- La recherche n'a pas trouvé d'extension de coupe sur nuage, ce qui ne prouve pas qu'il n'en existe aucune.

## PDAL : extraire des tranches depuis des COPC

### Takeaway
PDAL est la brique la plus adaptée pour extraire une tranche scriptée depuis des COPC locaux ou distants. Il produit des points et des rasters, pas de vue en coupe ni de vectorisation de silhouette.

### Cited Findings
- Dernière version publiée : 2.10.2, le 2026-06-12 ([GitHub API, PDAL releases](https://github.com/PDAL/PDAL/releases/latest)). Licence BSD ([LICENSE.txt](https://github.com/PDAL/PDAL/blob/master/LICENSE.txt)).
- `readers.copc` accepte des fichiers distants (http, AWS, Google, Azure, Dropbox), `bounds` 2D ou 3D, `polygon` WKT répétable, `ogr`, `resolution` (limite les niveaux lus), `requests` (15 par défaut), `count`, et des en-têtes HTTP ([doc PDAL stable](https://pdal.io/en/stable/stages/readers.copc.html)).
- `filters.crop` accepte `bounds`, `polygon`, `point` + `distance` (cercle ou sphère), `outside` et `a_srs`. La documentation ne propose pas de boîte tournée, seulement des bornes min/max ([doc filters.crop](https://pdal.io/en/stable/stages/filters.crop.html)).
- `filters.hag_nn`, `filters.hag_delaunay` et `filters.hag_dem` ont reçu un argument de classe en 2.10, et `filters.hag_dem` des options `min_clamp`, `max_clamp` et `nodata` ([notes 2.10.0](https://newreleases.io/project/github/PDAL/PDAL/release/2.10.0)).
- `filters.range` rejette les NaN ([notes 1.7.1](https://newreleases.io/project/github/PDAL/PDAL/release/1.7.1)). La syntaxe `Classification[2:2]` est illustrée dans une note tierce ([aso-lidar](https://github.com/Stevexe/aso-lidar/blob/master/pdal-pipelines/pdal_notes_README.md)).
- Retour de terrain sur LiDAR HD : la lecture de plusieurs dalles exige un `filters.merge` explicite. Sur deux dalles avec PDAL 2.10, l'auteur obtient 160 659 points avec et 75 085 sans ([IGNF-Xavier](https://github.com/IGNF-Xavier/qgis_gpf_lidarhd_COPC)).

### Inferences
- Une coupe oblique s'obtient en passant un rectangle tourné en `polygon` WKT, directement au lecteur COPC. Cette forme n'a pas été exécutée ici.
- Une tranche selon une polyligne se ferait avec un tampon fourni par WKT ou `ogr`, mais le dépliage (distance le long de l'axe) n'apparaît pas dans les pages lues et serait à calculer après coup.

### Gaps
- Aucun stage de coupe ou de dépliage trouvé dans les pages lues. La liste complète des filtres n'a pas été parcourue.
- `writers.*` non détaillés.

## CloudCompare : coupes, extraction le long d'une polyligne, dépliage, ligne de commande

### Takeaway
CloudCompare est l'outil libre le plus complet pour obtenir de vraies polylignes de section en interactif. Sa ligne de commande documente l'extraction de tranches, mais aucune option de contours ou de polylignes. Il ne documente pas de lecture partielle du COPC.

### Cited Findings
- Version : la dernière release GitHub stable est v2.13.2, publiée le 2024-07-11 ([GitHub](https://github.com/CloudCompare/CloudCompare/releases/latest)). La branche courante est en 2.14.beta, sans date dans le changelog ([CHANGELOG](https://github.com/CloudCompare/CloudCompare/blob/master/CHANGELOG.md)). Licence GPL ([license.txt](https://github.com/CloudCompare/CloudCompare/blob/master/license.txt)).
- Cross Section : boîte de coupe interactive ou numérique, orientable. Export de tranche, enveloppes 2D (Full, Lower, Upper, enveloppe concave), contours sur grille depuis la 2.12, répétition selon une ou plusieurs dimensions avec écart ([wiki Cross Section](https://www.cloudcompare.org/doc/wiki/index.php/Cross_Section)).
- Extract Sections : polylignes dessinées ou importées, génération de sections orthogonales avec pas et largeur, profils Lower, Upper ou Both, dépliage du nuage le long d'une polyligne avec distance maximale ([wiki Extract Sections](https://www.cloudcompare.org/doc/wiki/index.php/Extract_Sections)).
- DXF : le changelog mentionne l'export de nuages en DXF avec un nombre de points qui doit rester très limité, et une prise en charge du décalage global (grandes coordonnées) ([CHANGELOG](https://github.com/CloudCompare/CloudCompare/blob/master/CHANGELOG.md)).
- Ligne de commande (2.14.beta) : `-CROSS_SECTION` extrait des sections et les sauvegarde dans des sous-dossiers. `-RASTERIZE`, `-CROP` et `-CROP2D` sont documentés. Aucune option de la page ne sort de contours ou de polylignes, et `-EXTRACT_VERTICES` est indiqué comme non activé ([wiki Command line](https://www.cloudcompare.org/doc/wiki/index.php/Command_line_mode)). Sur le forum, l'administrateur confirmait que seules les tranches sont automatisables, mais ces fils datent d'environ 2016–2022 ([forum](https://mail.cloudcompare.org/forum/viewtopic.php?p=7812)).
- Le greffon LAS gère les versions 1.0 à 1.4 ([notes 2.13.0](https://www.cloudcompare.org/release/notes/20240214)).
- Le CHANGELOG ne contient aucune occurrence de « COPC » (recherche du 2026-11-09), et CloudCompare n'est pas listé sur [copc.io](https://copc.io/software.html).

### Inferences
- Une dalle IGN s'ouvre comme un LAZ 1.4 ordinaire, donc en entier, sans profiter de l'octree. Déduit de l'absence de COPC dans le changelog et de la prise en charge LAS 1.4.
- CloudCompare produit déjà la ligne de coupe que QGIS ne donne pas, mais en interactif.

### Gaps
- Fonction Rasterize et ses exports en interface non examinés en détail.
- Filtres de sélection à l'import (classe, emprise) non vérifiés pour COPC.
- Date de sortie de la 2.14 stable : aucune trouvée.

## LAStools, Potree, iTowns, Giro3D et visualiseurs web IGN

### Takeaway
Potree est le seul visualiseur web examiné dont un outil de profil avec export a été documenté, par un guide portant sur la version 1.6. Giro3D et iTowns lisent le COPC et servent de bibliothèques, mais aucun outil de coupe prêt à l'emploi n'a été trouvé. Aucun outil de coupe documenté n'a été trouvé pour cartes.gouv.fr.

### Cited Findings

**LAStools**
- Les bibliothèques LASzip et LASlib sont sous LGPL, le reste est propriétaire ([README/LICENSE](https://lastools.osgeo.org/download/LICENSE.txt)). L'usage éducatif et l'évaluation sont gratuits, et les sorties non licenciées peuvent être légèrement altérées au-delà de certains seuils de points ([LICENSE](https://lastools.osgeo.org/download/LICENSE.txt)).
- Depuis la version 250219, `-fail` est le comportement par défaut sans licence, et `-demo` sert à tester ([groupe LAStools](https://groups.google.com/g/lastools/c/uk9CxIh5gnk)). Un développeur a indiqué plus tard que l'option était ignorée dans certaines versions. Point à vérifier.
- Un seuil d'environ 3 à 5 millions de points est indiqué pour l'essai des outils licenciés ([rapidlasso](https://rapidlasso.de/?p=96)).
- LAStools figure sur la liste des implémentations COPC, avec lien vers une pull request ([copc.io](https://copc.io/software.html)).

**Potree**
- Dernière release 1.8.2, publiée le 2023-12-12 ([GitHub](https://github.com/potree/potree/releases/latest)). Le support initial de COPC et LAS 1.4 a été intégré le 2023-12-12 ([PR #1381](https://github.com/potree/potree/pull/1381)).
- Un guide de Potree 1.6 décrit l'export du profil en CSV ou LAS ([guide](https://www.scribd.com/document/721722540/potree-EN)). Le projet CPotree fournit `extract_profile` en ligne de commande, vers .potree, .las ou .csv ([CPotree](https://github.com/loicgasser/CPotree)).
- Potree-Next est une réécriture WebGPU. Son README annonce que beaucoup de fonctions manqueront au début ([README](https://github.com/m-schuetz/Potree-Next)). Parité avec 1.8 visée pour une future 3.0 ([netidee](https://www.netidee.at/node/2672)).
- Licence de Potree-Next : le fichier indique AGPL ([LICENSE](https://github.com/m-schuetz/Potree-Next/blob/main/LICENSE)), alors qu'un document du projet indique CC BY-SA ([doc netidee](https://www.netidee.at/sites/default/files/2025-10/prj6863_Call18_Entwicklerdokumentation_0.pdf)). Sources contradictoires.

**Giro3D et iTowns**
- Giro3D 2.0.6, licence MIT ([npm](https://registry.npmjs.org/@giro3d/giro3d/latest)). Plans de clipping listés parmi ses fonctions, avec un exemple appliqué à une carte et à un nuage ([exemple](https://giro3d.org/latest/examples/clipping-planes)).
- L'exemple LiDAR HD charge un tileset 3D Tiles, sans clipping ni profil ([exemple LiDAR HD](https://giro3d.org/latest/examples/lidar-hd)). La version 0.41 décrit plus de 3 milliards de points issus de 180 fichiers COPC IGN ([Oslandia](https://oslandia.com/en/2025/01/14/les-nouveautes-giro3d-0-41/)).
- iTowns v2.46.0 (2025-10-07), double licence CeCILL-B et MIT ([LICENSE](https://github.com/iTowns/itowns/blob/master/LICENSE.md)). COPC listé et propulsé par copc.js ([copc.io](https://copc.io/software.html)).

**Visualiseurs LiDAR HD**
- cartes.gouv.fr annonce un visualiseur intégré avec outils de mesure et d'analyse ([Découvrir](https://cartes.gouv.fr/decouvrir/)). Rien ne documente un outil de coupe.
- LIDAR HD Viewer (projet communautaire, hors IGN) streame des blocs COPC en WebGL ([data.gouv.fr](https://www.data.gouv.fr/reuses/lidar-hd-viewer)).

### Inferences
- Un outil de coupe web sur COPC IGN serait techniquement à portée de Giro3D ou iTowns, mais il resterait à développer d'après les exemples consultés.

### Gaps
- Licence exacte de Potree 1.8 non lue (en-tête seul).
- Fonctions de `lasclip`, `lasheight` et `las2dem` non vérifiées dans leurs README. Tarifs non trouvés ([page tarifs](https://rapidlasso.de/pricing) sans prix).
- Exemple de clipping sur source COPC dans Giro3D non confirmé. Exemples iTowns non parcourus.
- Présence ou non d'une coupe dans le visualiseur cartes.gouv.fr non vérifiée en le testant. Base MapLibre non confirmée.

## Architecture et CAO : quelles méthodes, et quel accès aux données LiDAR HD ?

### Takeaway
Les logiciels d'architecture savent couper un nuage, mais aucun de ceux examinés ne documente la lecture de COPC. L'entrée passe en pratique par une conversion (E57, RCP). Seuls Rhino et AutoCAD documentent ici une extraction de courbes de section depuis le nuage. Aucun tutoriel complet « LiDAR HD vers coupe architecturale » n'a été trouvé.

### Cited Findings

**Rhino et Grasshopper**
- `PointCloudSection` crée une courbe plane à partir d'un plan. « Maximum distance to plane » fixe l'épaisseur de la tranche, les points y sont projetés puis reliés. `PointCloudContour` répète l'opération. Une tolérance d'ajustement règle les courbes lisses ([doc Rhino 8](https://docs.mcneel.com/rhino/8/help/en-us/commands/pointcloud.htm)).
- Import E57 documenté en Rhino 8 et 9 ([doc Rhino 8](https://docs.mcneel.com/rhino/8/help/en-us/fileio/e57_import.htm)). LAS et LAZ : un fil McNeel dit non, un blog tiers dit oui, sans doc officielle ([forum McNeel](https://discourse.mcneel.com/t/getting-laz-file-into-rhino/153233) ; [Novedge](https://novedge.com/blogs/design-news/rhino-3d-tip-efficient-management-and-integration-of-point-clouds-in-rhino-3d)). Sources en conflit.
- Contournement courant : convertir le LAZ en E57 dans CloudCompare, avec perte signalée de la classification ([forum McNeel](https://discourse.mcneel.com/t/getting-laz-file-into-rhino/153233)).
- Grasshopper peut référencer un nuage en Rhino 8 ([forum McNeel](https://discourse.mcneel.com/t/point-cloud-in-rhino-to-list-of-points-in-grasshopper/151155)). Volvox pour des coupes courbes et Cockroach pour aplatir une bande : témoignages de forum, pas de documentation lue ([grasshopper3d.com](https://grasshopper3d.com/xn/detail/2985220:Comment:1953664)).
- Un utilisateur signale que les nuages n'apparaissent pas dans les dessins dérivés de plans de coupe ([forum McNeel](https://discourse.mcneel.com/t/view-point-cloud-in-clipping-drawing/180724)). Fil à dater.
- Veesus Point Clouds for Rhino annonce clipping, découpe selon la géométrie et vectorisation automatique ([food4rhino](https://www.food4rhino.com/en/app/point-clouds-rhino)).

**Revit, ReCap, AutoCAD**
- Revit 2025 importe RCP et RCS, le E57 et le LAS/LAZ passant par ReCap Pro selon un blog d'éditeur ([thefuture3d](https://www.thefuture3d.com/learn/revit-point-cloud-import-guide)).
- Autodesk liste LAS en entrée, sans LAZ dans sa page de formats ([aide Autodesk](https://help.autodesk.com/cloudhelp/ENU/Reality-Capture/files/Getting_Started/supported_file_formats.html)). Un forum indique LAZ en entrée ([cadforum](https://www.cadforum.cz/cz/souborove-formaty-podporovane-v-autodesk-recap-a-recap-pro-tip11517)), et un article de mai 2026 indique que l'import direct LAZ n'est plus possible dans AutoCAD depuis 2018 ([Topolia](https://topolia.fr/articles/lidar-hd-ign/)). Point non tranché pour ReCap.
- AutoCAD : `PCEXTRACTSECTION` produit des lignes ou polylignes 2D à l'intersection estimée du plan de coupe, documenté jusqu'en 2026 ([aide AutoCAD 2026](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-C6D09456-7D5D-401F-AB5A-00D1D788A323.htm)). Un praticien rapporte que le résultat n'est bon que sur nuage propre à murs plans ([Unsurveyed](https://sites.google.com/view/unsurveyed/my-tutorials/deliver/cw-3dr-pointfuse-scan-2-plan)).

**Autres**
- Archicad ouvre E57 et XYZ, et l'aide n'évoque pas LAS ([aide Archicad 25](https://help.graphisoft.com/AC/25/INT/_AC25_Help/120_Interoperability/120_Interoperability-32.htm)). Le module tiers BIMmTool lit E57 et LAZ ([Graphisoft Community](https://community.graphisoft.com/t5/Modeling/Improved-BIMmTool-for-better-point-cloud-handling/ta-p/631570)).
- BricsCAD annonce E57, PTX et certains RCP ([Bricsys](https://www.bricsys.com/bricscad-for-point-clouds)). LAS passe par exemple via CloudWorx de Leica ([Leica](https://rcdocs.leica-geosystems.com/cloudworx/latest/import-point-cloud)).
- SketchUp Scan Essentials (Windows, abonnement Studio) coupe le nuage avec l'objet section natif ([aide SketchUp](https://help.sketchup.com/en/scan-essentials-sketchup/point-cloud-manager)).
- Blender : Point Cloud I/O 0.5.1 (Blender ≥ 5.1) lit LAS et LAZ et conserve classification et intensité en attributs pour Geometry Nodes ([extensions.blender.org](https://extensions.blender.org/add-ons/point-cloud-io/)). Point Cloud Visualizer lit LAS et LAZ via laspy et lazrs ([PCV](https://blendermarket.com/products/pcv/faq)).

**Chaînes documentées à partir du LiDAR HD**
- Revit, AutoCAD, Civil 3D : conversion préalable en RCP via ReCap. En Lambert-93, lier le nuage en coordonnées partagées ou via un point de base, pas à l'origine ([Lauria Escaner, 26 sept. 2026](https://www.lauriaescaner.com/fr/blog/lidar-hd-ign/)).
- AutoCAD via ReCap : saisir EPSG:2154 dès l'import. L'article traite de courbes, MNT et TIN, pas de coupes ([Topolia, 29 mai 2026](https://topolia.fr/articles/lidar-hd-ign/)).
- Un tutoriel QGIS montre une coupe sur LiDAR HD avec une tolérance de 5 puis 15 m et l'extrusion des bâtiments ([sigterritoires](https://www.sigterritoires.fr/index.php/comment-faire-un-profil-topographique-avec-qgis-3-26-3eme-partie/)).

### Inferences
- Le passage du LAZ IGN au E57 peut perdre la classification, alors qu'elle est l'atout principal des dalles pour isoler sol, bâti et végétation. Le filtrage devrait donc se faire avant la conversion.

### Gaps
- Pas de source sur la méthode de Tarsier appliquée aux coupes.
- Vectorworks : aucun résultat exploitable.
- Civil 3D : aucun résultat sur les profils de nuage de points.
- Aucune ressource d'école d'architecture ni de fil forumsig ou geotribu trouvée sur la coupe à partir de LiDAR HD. Recherche limitée à deux requêtes en français.
- Blender : aucune recette de coupe documentée trouvée, seulement l'import et la manipulation par attributs.
- Les formats de Rhino 9 pour LAS et LAZ restent à vérifier.

## Outils commerciaux et en ligne, nouveautés 2024–2026

### Takeaway
Les suites commerciales font les coupes depuis longtemps. Les promesses récentes de sections automatisées viennent surtout de pages d'éditeurs, et aucune n'a été vérifiée indépendamment.

### Cited Findings
- Global Mapper Pro : Path Profile sur grilles et nuages avec largeur de bande, classification manuelle et séries de profils perpendiculaires ; le support LiDAR dans cet outil exige la version Pro ([base de connaissances](https://www.bluemarblegeo.com/knowledgebase/global-mapper/Path_Profile/PathProfile_Lidar_Module.htm) ; [blog](https://www.bluemarblegeo.com/blog/exploring-the-path-profile-tool/)).
- FME : lecteur et écrivain COPC, lecture HTTP, FTP ou locale, sélection par enveloppe rectangulaire ([doc FME](https://docs.safe.com/fme/html/FME-Form-Documentation/FME-ReadersWriters/copc/copc.htm)). FME est aussi listé par [copc.io](https://copc.io/software.html).
- TerraScan : outils Draw Section, Cut Section, Move Section, et Draw Plane Section depuis 017.039 ([GeoCue](https://support.geocue.com/wp-content/uploads/2018/03/TerraScan_Draw-Plane-Section-tool-1.pdf) ; [manuel](https://community.esri.com/ccqpr47374/attachments/ccqpr47374/gis-blog/507/2/TerraScan_UserManual.pdf)).
- Leica Cyclone 3DR dispose d'une documentation de création de sections en 2025.2 ([Leica](https://rcdocs.leica-geosystems.com/cyclone-3dr/2025.2/Create_sections)). Trimble Business Center documente l'extraction de sections ([Trimble](https://help.fieldsystems.trimble.com/tbc/25811.htm)).
- GstarCAD Point Cloud 2026 (plugin Undet) : vue en coupe avec outil Auto Line et insertion de murs, portes, fenêtres. Blog d'éditeur ([GstarCAD](https://blog.gstarcad.net/gstarcad-point-cloud-2026-core-features-whats-different/)).
- Neurones 3D annonce des plans automatiques avec coupes et élévations en SVG, DXF, PDF. Page rédigée par l'éditeur ([Neurones 3D](https://neurones3d.com/best-point-cloud-software/)).
- CHCNAV CoProcess (mai 2026) annonce une découpe à la volée et un environnement DWG natif. Communiqué ([GlobeNewswire](https://www.globenewswire.com/news-release/2026/05/29/3303377/0/en/chcnav-unveils-next-generation-coprocess-for-point-cloud-processing-and-survey-deliverables.html)).

### Inferences
- Les fonctions de « plan et coupe automatiques » annoncées visent des relevés intérieurs denses. Leur pertinence sur un LiDAR aérien à densité urbaine (toitures et sol, peu de façades) n'est pas démontrée par ces sources.

### Gaps
- Pointfuse, Nira, Cintoo : aucune information actuelle sur leurs coupes (seul un article de 2018 sur Cintoo).
- InfraWorks : non examiné.
- Licence et tarifs de TerraScan, Global Mapper : non trouvés.
- Lecture COPC par Global Mapper : absente de copc.io, non établie.

## Tableau comparatif et manques restants

### Takeaway
Aucun outil examiné ne réunit à la fois lecture COPC partielle, filtrage par classe dans la coupe, tracé selon un axe et sortie vectorielle de silhouette prête pour la CAO. QGIS et PDAL couvrent l'accès aux données, CloudCompare, Rhino et AutoCAD la vectorisation, chacun avec une limite propre.

### Cited Findings

Les cellules reprennent les sources des sections précédentes. « Non établi » signifie qu'aucune source lue ne tranche. « Ouverture complète » désigne un LAZ lu sans profiter de l'index.

| Outil (version consultée) | Licence | Lecture COPC IGN | Corridor ou tranche | Filtre de classe | Sortie vectorielle de silhouette | Exports | Automatisation | Limite principale |
|---|---|---|---|---|---|---|---|---|
| QGIS profil 3.44–4.2 | GPL-2.0 | Oui, partielle, locale et distante | Oui, tolérance le long d'une ligne | Indirect (requête ou rendu), non dédié | Non documentée (points ; ligne continue en vue) | PDF, image, DXF, CSV, SHP, GPKG | PyQGIS (`QgsProfileExporter`), atlas en mise en page | Points exportés, densité selon erreur max |
| QGIS vue 3D 3.44–4.0 | GPL-2.0 | Oui | Oui, rectangle tourné | Par rendu | Non | Non établi | PyQGIS depuis 4.0 | Visualisation |
| Processing / pdal_wrench | GPL (QGIS) ; GPL-3.0 (wrench) | Oui | Découpe par polygone | Oui, expression PDAL | Non | Nuage, raster, vecteur | Oui | Pas de coupe dédiée |
| PDAL 2.10.2 | BSD | Oui, partielle, distante (bounds, polygon) | Oui, polygone | Oui, `filters.range` | Non | Nuage, raster | Oui, pipelines | Pas de dépliage dans les pages lues |
| CloudCompare 2.13.2 / 2.14.beta | GPL | Ouverture complète (déduit) | Oui, boîte, polyligne, dépliage | Non établi | Oui, enveloppes, contours, profils | DXF cité, nombreux formats nuage | Tranches seulement (CLI) | Contours non automatisables en CLI |
| LAStools | Mixte : LGPL (bibliothèques), propriétaire | Listé par copc.io, détail non établi | Non établi | Non établi | Non établi | Non établi | Oui, CLI | Licence requise pour usage commercial |
| Potree 1.8.2 | Non vérifiée | Support initial intégré | Oui, profil | Non établi | Non | CSV, LAS (doc ancienne) | CPotree | Conversion ou mise en ligne à prévoir |
| Giro3D 2.0.6 / iTowns 2.46.0 | MIT / CeCILL-B + MIT | Oui, à distance | Plans de clipping (Giro3D) | Non établi | Non | Non établi | Bibliothèques JS | Pas d'outil de coupe prêt |
| cartes.gouv.fr (visualiseur) | Service public | Non établi | Non documenté | Non établi | Non | Non établi | Non | Coupe non documentée |
| Rhino 8 | Propriétaire | Non documentée (E57 documenté ; LAS/LAZ en conflit) | Plan avec épaisseur | Non établi | Oui, `PointCloudSection` | Formats Rhino | Grasshopper | Plan unique, conversion avec perte possible de classes |
| Revit + ReCap | Propriétaire | Non documenté, passage par RCP | Boîte de section | Non établi | Non établi | Formats Revit | Non établi | Conversion préalable, géoréférencement |
| AutoCAD | Propriétaire | Non documenté, passage par RCP | Plan de coupe | Non établi | Oui, `PCEXTRACTSECTION` | DWG | Non établi | Qualité sur nuage propre seulement (retour d'usage) |
| Archicad 25 (aide) | Propriétaire | Non documentée (E57, XYZ) | Non établi | Non établi | Non établi | Non établi | Non établi | Plugin tiers pour LAZ |
| BricsCAD | Propriétaire | Non documenté | Non établi | Non établi | Non établi | Non établi | Non établi | Formats à confirmer |
| Blender + Point Cloud I/O 0.5.1 | Non vérifiée | Ouverture complète (déduit de LAZ) | À construire | Attribut disponible | À construire | Selon nœuds | Python, Geometry Nodes | Aucune coupe prête |
| Global Mapper Pro | Propriétaire | Non établi | Oui, largeur de bande, profils perpendiculaires | Non établi | Non établi | Non établi | Non établi | Licence Pro requise |
| FME | Propriétaire | Oui, HTTP, enveloppe rectangulaire | À construire | Non établi | À construire | Très nombreux | Oui, workspaces | Pas de coupe native établie |
| TerraScan | Propriétaire | Non établi | Oui, outils de section | Non établi | Vectorisation sur plan | Non établi | Non établi | Licence et plateforme non vérifiées |

Accès aux dalles sans logiciel lourd : `romain974/qgis-lidar-hd` et `IGNF-Xavier/qgis_gpf_lidarhd_COPC` s'appuient sur la lecture distante HTTP Range ([romain974](https://github.com/romain974/qgis-lidar-hd) ; [IGNF-Xavier](https://github.com/IGNF-Xavier/qgis_gpf_lidarhd_COPC)).

### Inferences

Manques qui semblent subsister, d'après ce corpus :
- **Silhouette vectorielle depuis COPC.** Aucun outil de la liste ne va directement d'un COPC lu partiellement à une polyligne de coupe. QGIS exporte des points en mode points individuels (export du mode triangulé non établi), CloudCompare ouvre le fichier entier.
- **Filtre de classe propre à la coupe.** QGIS passe par des réglages de couche globaux. Un réglage par coupe ou par profil n'a pas été trouvé.
- **Coupe composée.** Aucune source lue ne décrit la superposition, dans un même dessin, du sol en ligne, du bâti en silhouette et de la végétation en masse.
- **Sorties pour architectes.** Les exports DXF restent ponctuels. Les chemins vers Rhino ou Revit imposent une conversion qui peut perdre la classification.
- **Automatisation sur un axe avec cartouche.** L'atlas QGIS pilote une courbe, mais sa prise en compte des nuages n'est pas documentée. La CLI CloudCompare ne sort pas de contours.
- **Limite commune aux données aériennes.** Toutes ces méthodes héritent de la faible couverture des façades en LiDAR aérien (hypothèse à confirmer par les notes sur le produit).

### Gaps
- Aucun essai réel n'a été mené : tous les constats proviennent de documentation, de code source ou de retours publiés.
- Les cases « Non établi » signalent une absence de source lue, pas une absence de fonction.
- Produits non couverts faute de source trouvée ou de recherche dédiée : Pointfuse, Nira, Cintoo (état actuel), InfraWorks, Vectorworks, Tarsier et le fournisseur LAStools de QGIS.
