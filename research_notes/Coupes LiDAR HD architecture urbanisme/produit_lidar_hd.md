# Produit LiDAR HD de l'IGN : ce que contiennent les données et ce qu'elles permettent pour des coupes (état au 9 novembre 2026)

Note de lecture valable pour tout le document. Les descriptifs officiels (DC, SE, DT) en PDF sur geoservices.ign.fr ne sont plus accessibles : leurs URL redirigent en 301 vers `cartes.gouv.fr/explorer-les-cartes/` (vérifié le 9/11/2026), et la Wayback Machine a répondu 429. Les valeurs officielles viennent donc des fiches data.gouv/cartes.gouv.fr, des diapositives IGN et de la spécification reproduite en annexe de FRACTAL (auteurs IGN). Le libellé « mesure propre » désigne des contrôles faits pour cette note sur les données diffusées. Ils ne sont ni publiés ni relus.

## Spécifications officielles et état du programme (densité, précision, vol, couverture, licence)

### Takeaway
Le seul engagement de densité est « au moins 10 impulsions/m² » (5 au-dessus de 3 200 m), mais les dalles diffusées contiennent en médiane environ 24 points/m². La précision absolue annoncée est de 10 cm en Z et 50 cm en XY. Le chiffre de 50 cm en plan compte pour les coupes, car il dépasse largement le bruit local. La couverture publiée atteint 524 687 dalles au 9/11/2026, sans confirmation officielle d'achèvement.

### Cited Findings

**Densité : spécification**
- Fiche produit : « densité d'au moins 10 impulsions au m² et 5 impulsions au m² au-dessus de 3200 m d'altitude » — [data.gouv.fr, Nuages de points LiDAR HD, mise à jour 30/09/2026](https://www.data.gouv.fr/datasets/nuages-de-points-lidar-hd/informations)
- Les supports IGN mélangent les unités dans un même document : « 10 impulsions/m² en moyenne », « 10 points au m² en moyenne » et « 10-15 pts/m² en moyenne » — [IGN, Atelier LiDAR, diapositives CRIG Occitanie du 20/11/2024, PDF déposé 12/2025](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf)
- Des auteurs IGN écrivent « 10 pulses/m², about 40 pts/m² » — [Gaydon et al., FRACTAL, arXiv 2405.04634](https://arxiv.org/pdf/2405.04634v4). Le jeu FRACTAL lui-même fait 37 pts/m² en moyenne, mais il est échantillonné et concentre volontairement certaines scènes.

**Densité : mesure propre sur les métadonnées diffusées**
- Échantillon de 20 087 dalles (100 pages de 200 entités à intervalle régulier, 213 missions) sur [la couche WFS IGNF_LIDAR-HD_METADONNEE:metadata](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities), `nombre_points`/1 km², dalles de plus de 3 pts/m² seulement (n = 19 646) : moyenne 27,5 ; p5 14,1 ; p25 19,1 ; médiane 24,2 ; p75 32,3 ; p95 51,7 pts/m². Ces comptes incluent tous les échos, les recouvrements et les éventuels points virtuels.
- Dalles urbaines kilométriques, même source : Toulouse centre 47,9 pts/m² ; Marseille 40,1 ; Lyon Presqu'île 29,5 ; Nantes 28,5 ; Paris centre 17,2 ; Strasbourg 16,0. L'écart entre villes dépasse donc un facteur 3.

**Précision**
- « Précisions absolues : 10 cm en altimétrie, 50 cm en planimétrie » — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf). Ce sont des objectifs de programme, non des résultats de contrôle.
- Résultat indépendant, un seul site (arboriculture, projet ANR CANOP) : RMSE Z de 13,1 cm pour le LiDAR HD sans recalage manuel, contre 4,8 cm pour un LiDAR aéroporté dédié, 4,5 cm pour la photogrammétrie drone et 29,5 cm pour le MNS IGN à 20 cm — [Tardy et al., ONERA, SFPT 2025](https://wpedu2.sedoo.fr/wp-content-omp/uploads/sites/54/2025/05/SFPT-GH-25_Session-3_TARDY_Hugo.pdf). La présentation compare des MNS pour de l'orthorectification, pas des nuages sur des surfaces de contrôle.

**Capteurs et prestataires**
- Mesure propre sur le même échantillon, part des dalles citant chaque capteur (une dalle peut en citer plusieurs) : Leica TerrainMapper 38 % ; RIEGL VQ-780 II-S 33 % ; Optech Galaxy T2000 15 % ; RIEGL VQ-1560 II 14 % ; Leica CityMapper-2 9 % ; Optech Galaxy T1000 2 % ; RIEGL VQ-1460 0,6 % — [WFS métadonnées](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities). Le VQ-1560 II et la CityMapper-2 figurent bien dans le programme, alors que des listes plus anciennes ne citent pas le VQ-1560.
- Prestataires les plus présents dans l'échantillon : APEI, Sintegra, IGN, Geofit, Eurosense/SFS, ATGT — même source.
- Le programme doit rester « compatible with a variety of Lidar sensors (Leica, Riegl, and Teledyne/Optech) » — [FRACTAL](https://arxiv.org/pdf/2405.04634v4).

**Couverture et calendrier**
- Cible : France métropolitaine et DROM sauf Guyane « d'ici 2026 » — [data.gouv.fr](https://www.data.gouv.fr/datasets/nuages-de-points-lidar-hd/informations). Total annoncé de 550 000 km² — [FRACTAL](https://arxiv.org/pdf/2405.04634v4). Autres ordres de grandeur IGN : 7 000 h de vol, 3 Po, environ 5 600 milliards de points — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf).
- 524 687 dalles référencées dans le WFS au 9/11/2026 (mesure propre, `numberMatched`) — [WFS métadonnées](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities). Un inventaire tiers en comptait 507 791 au 6/09/2026, avec 30 933 communes couvertes à 99 % ou plus, 3 054 sans aucune dalle et 78 % de la surface communale couverte (inventaire tiers publié sur data.gouv.fr).
- Le même inventaire indique que le nuage classé est publié un à deux ans après le vol (relevé via résultat de recherche).
- Suivi officiel par bloc : [carte de diffusion IGN](https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD).
- Le champ « couverture temporelle 2021-2024 » de la fiche data.gouv est périmé : le WFS contient des fins d'acquisition en 2025 et 2026 — [API data.gouv](https://www.data.gouv.fr/api/1/datasets/nuages-de-points-lidar-hd/) et WFS ci-dessus.

**Licence et restrictions**
- Licence Ouverte / Open Licence 2.0 (Etalab) — [data.gouv.fr](https://www.data.gouv.fr/datasets/nuages-de-points-lidar-hd/informations).
- Les modèles numériques sont soumis aux restrictions ZICAD : pas de données sur ces zones, valeur nodata — [API data.gouv, MNT LiDAR HD](https://www.data.gouv.fr/api/1/datasets/mnt-lidar-hd/).

### Inferences
- Avec 524 687 dalles sur environ 550 000 km², la couverture hors Guyane serait de l'ordre de 95 %. C'est un majorant, car les dalles côtières et frontalières sont partielles.
- Les 78 % de l'inventaire tiers semblent cohérents avec ce chiffre si le dénominateur inclut la Guyane (environ 84 000 km² de communes). 507 791 dalles sur environ 640 000 km² donnent 79 %. Cette explication n'est pas confirmée par la source.
- Une coupe ne doit pas être dimensionnée sur « 10 pts/m² » : la densité locale réelle se lit dans `nombre_points` de chaque dalle et varie de 14 à 52 pts/m² entre p5 et p95.
- La différence impulsions/points reste limitée en ville : dans les quatre carrés de la section sur les façades, les derniers échos représentent 86 à 95 % des points (86 % à Paris, 94 à 95 % ailleurs).

### Gaps
- Hauteur de vol, angle de scan maximal, recouvrement entre bandes et vitesse : je n'ai trouvé aucune valeur officielle lisible. Les PDF DC/DT/SE sont inaccessibles. Seule une observation locale d'angle est disponible, dans la section sur la géométrie des façades.
- Le support [Geospatial World Forum 2026 de S. Chataigner (IGN)](https://geospatialworld.net/gwf/2026/presentations/lidar-and-scanning/session1/ign-french-national-lidar-hd-project-geospatial-world-forum-2026_stephane-chataigner.pdf) aurait pu donner l'état 2026 : le téléchargement renvoie 403.
- Aucun bilan officiel chiffré d'avancement au 11/2026, ni confirmation de la fin du programme. Le [document IGN de janvier 2026](https://www.ign.fr/files/default/2026-01/IGN_lidarhd_janvier2026.pdf) n'a pas de texte exploitable (contenu en images).
- Précision planimétrique mesurée sur le LiDAR HD : je n'ai trouvé aucune étude publiée. Un résultat de recherche mentionne 0,1 m en planimétrie pour un jeu des Hauts-de-Seine (2022), non vérifié et peut-être hors programme national. Aucune évaluation qualité publiée par le Cerema n'a été trouvée.

## Produits, format, découpage, référentiels et canaux d'accès

### Takeaway
Le produit utile aux coupes est le nuage classé COPC LAZ 1.4 en dalles de 1 km, en Lambert-93/IGN69 pour la métropole, avec une résolution de coordonnées de 1 cm. Les MNT/MNS/MNH à 0,5 m sont des grilles 2,5D et ne peuvent pas représenter un mur ni un surplomb. L'accès passe désormais par la métadonnée WFS `IGNF_LIDAR-HD_METADONNEE:metadata`, qui donne l'URL de chaque dalle.

### Cited Findings

**Nuages de points**
- LAS/LAZ 1.4, blocs de 50 × 50 km en général, découpés en dalles de 1 × 1 km ; poids indicatif de 500 Mo à 2 Go par dalle — [data.gouv.fr](https://www.data.gouv.fr/datasets/nuages-de-points-lidar-hd/informations). La fiche liste aussi des liens de téléchargement de nuages classés et de nuages bruts — [API data.gouv](https://www.data.gouv.fr/api/1/datasets/nuages-de-points-lidar-hd/).
- Diffusion des nuages classés par dalle kilométrique depuis juin 2023 — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf).
- Mesure propre sur les en-têtes de quatre dalles (Toulouse, Lyon, Nantes pour l'en-tête brut ; Paris via lecteur COPC), éditions 12/2024 à 07/2025 : LAS 1.4, VLR `copc`, format de point 6, 30 octets par point, échelle 0,01 m, WKT « RGF93 v1 / Lambert-93 » (WKT lu sur les trois en-têtes bruts) — exemple : [dalle Toulouse 0574-6280](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_IQ_2024-12-20/LHD_FXX_0574_6280_PTS_LAMB93_IGN69.copc.laz).
- Motif d'URL observé : `https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_<BLOC>_<AAAA-MM-JJ>/LHD_FXX_<XXXX>_<YYYY>_PTS_LAMB93_IGN69.copc.laz`. `XXXX` et `YYYY` sont le coin nord-ouest en km : la dalle 0574_6280 s'étend de X 574 000 à 575 000 et de Y 6 279 000 à 6 280 000 — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities) (mesure propre).
- Le service de téléchargement limite le débit : 429 Too Many Requests sur lecture COPC à requêtes parallèles, lecture réussie en un seul fil (mesure propre, 9/11/2026, [dalle Toulouse](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_IQ_2024-12-20/LHD_FXX_0574_6280_PTS_LAMB93_IGN69.copc.laz)).

**Modèles numériques**
- MNT en GeoTIFF, dalles de 1 × 1 km, pas de 50 cm ; version 5 m annoncée « prochainement » sur la fiche à jour du 30/09/2026 — [data.gouv.fr, MNT LiDAR HD](https://www.data.gouv.fr/datasets/mnt-lidar-hd/informations). Les diapositives IGN listent déjà 0,5 m et 5 m comme livrables — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf).
- Le MNT dérive des classes sol, eau et points virtuels — [API data.gouv, MNT](https://www.data.gouv.fr/api/1/datasets/mnt-lidar-hd/).
- Coordonnées des nœuds « valeurs métriques entières en projection » — [API data.gouv, MNT](https://www.data.gouv.fr/api/1/datasets/mnt-lidar-hd/). Les URL WMS du WFS demandent 2000 × 2000 pixels sur BBOX `573999.75 ... 574999.75`, soit des pixels centrés sur les nœuds à 0,5 m — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities). Nommage observé : `LHD_FXX_0574_6280_MNT_O_0M50_LAMB93_IGN69.tif`.
- Premiers 55 blocs de MNT/MNS/MNH publiés en mars 2025, fondés sur la classification « Version 5 », avec sélection des points utiles dans les recouvrements pour améliorer les fortes pentes, lisières et bords de ponts — [cartes.gouv.fr, actualité de mars 2025](https://cartes.gouv.fr/aide/fr/partenaires/ign/generalites-ign/actualites/2025-03-lidarhd-et-produits-derives/).
- Données accompagnantes : cartes de densité de points sol, fichiers de trajectographie, bandes de vol — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf). Couches WMS de densité : `IGNF_LIDAR-HD_DENSITE-SOL` et `IGNF_LIDAR-HD_DENSITE-SURSOL` — [API data.gouv](https://www.data.gouv.fr/api/1/datasets/nuages-de-points-lidar-hd/).

**Référentiels**
- `systeme_planimetrique` = LAMB93 et `systeme_altimetrique` = IGN69 dans les métadonnées de dalle (mesure propre sur Toulouse) — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities).
- En outre-mer, les dalles sont diffusées dans le système légal du territoire — [DC LiDAR HD, extrait vu en résultat de recherche seulement](https://geoservices.ign.fr/sites/default/files/2023-09/DC_LiDAR_HD_1-0_PTS.pdf).

**Canaux d'accès**
- Catalogue : [cartes.gouv.fr, IGNF_NUAGES-DE-POINTS-LIDAR-HD](https://cartes.gouv.fr/catalogue/dataset/IGNF_NUAGES-DE-POINTS-LIDAR-HD). L'ancienne page geoservices.ign.fr/lidarhd redirige en 301 vers cartes.gouv.fr (vérifié le 9/11/2026), et le rendu de la page ne contient pas de texte accessible sans navigateur.
- La couche `IGNF_LIDAR-HD_METADONNEE:metadata` expose par dalle : `capteur`, `url_npl`, `url_mnt`, `url_mns`, `url_mnh`, `code_mission`, `date_edition`, `date_debut_acquisition`, `date_fin_acquisition`, `nombre_points`, `coordonnees_nw`, `moa_acquisition`, `moe_acquisition`, `procede_classement`, `moe_classement_manuel`, `moe_classement_automatique`, `systeme_altimetrique`, `systeme_planimetrique` — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities) (mesure propre).
- La fiche data.gouv liste encore `IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle`, mais le WFS a répondu « Unknown namespace » pour cette couche le 9/11/2026 — [API data.gouv](https://www.data.gouv.fr/api/1/datasets/nuages-de-points-lidar-hd/) et test direct sur le WFS.

### Inferences
- La résolution de 1 cm du LAS est bien inférieure à la précision absolue de 10 à 50 cm. Afficher des cotes au centimètre sur une coupe serait trompeur.
- Une coupe verticale doit être construite sur le nuage. Le MNS à 0,5 m lisse les bords de toit sur un pas de 50 cm et remplace tout mur par une transition entre deux pixels.
- Pour le terrain seul, le MNT à 0,5 m est utilisable, en rappelant que sous les ponts il est alimenté par des points virtuels, donc interpolé.

### Gaps
- Méthode d'interpolation et précision propres des MNT/MNS/MNH : introuvables dans les pages accessibles.
- Attributs `DTM_MAKER`/`DSM_MAKER` : voir la section sur les attributs. Leur diffusion généralisée n'est pas établie.

## Classification : codes, définitions et fiabilité

### Takeaway
Les façades relèvent de la classe 6 par spécification, mais ce choix n'en garantit pas la capture. La spécification vise des rappels de 99,5 à 99,9 % par bâtiment pour la seule version corrigée manuellement, alors que 83 % des dalles échantillonnées portent le code IGN_AUTO_V5, dont le nom indique un traitement automatique. Aucune mesure publiée ne porte sur la classification des points de façade.

### Cited Findings

**Nomenclature à 11 classes** — synthèse de [FRACTAL, annexe D.1](https://arxiv.org/pdf/2405.04634v4), [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf) et [data.gouv.fr](https://www.data.gouv.fr/datasets/nuages-de-points-lidar-hd/informations)

| Code | Nom | Contenu utile aux coupes |
|---|---|---|
| 1 | Non classé | Véhicules, personnes, objets temporaires, tas de bois (FRACTAL). Cultures annuelles, ruines, piles et parapets de ponts (IGN) |
| 2 | Sol | Sol naturel et artificiel, tabliers de pont exclus. IGN : hors classes 9 et 17 |
| 3 | Végétation basse | Moins de 0,5 m. Végétation de moins de 20 cm rangée en végétation seulement s'il reste assez de points sol |
| 4 | Végétation moyenne | 0,5 à 1,5 m. Inclut vergers, vignes, cultures arborées |
| 5 | Végétation haute | 1,5 m ou plus |
| 6 | Bâtiment | Structure permanente de plus de 10 m². Toits, façades, cheminées, lucarnes, châssis de toit, balcons. Inclut monuments, châteaux, remparts, fortifications, cheminées industrielles, et aussi bâtiments légers, auvents, bâches de marché |
| 9 | Eau | Rivières, plans d'eau, mer. IGN : « plans d'eau non exhaustifs » |
| 17 | Tablier de pont | Points de tablier. Piles et parapets en classe 1. Éléments à 5 m ou plus au-dessus du tablier en classe 64 |
| 64 | Sursol pérenne | Éoliennes, antennes, câbles, réseaux, éléments de pont au-dessus du tablier |
| 65 | Artefact | Points ne correspondant à aucun objet ni terrain |
| 66 | Points virtuels (synthétiques) | Créés sous les ponts et sur l'eau pour les modèles numériques |
| 67 | Divers bâtis | Bâtiments non confirmés dans la BD Topo |

- Divergence entre sources : data.gouv compte 11 catégories avec la 67 et sans artefact, FRACTAL compte 11 classes avec artefact et synthétique sans la 67, l'IGN liste 10 codes sans la 65. La classe 65 existe bien dans les fichiers diffusés : 194 points sur le carré de Paris (mesure propre, [dalle Paris 0651-6862](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_KE_2025-06-06/LHD_FXX_0651_6862_PTS_LAMB93_IGN69.copc.laz)). La classe 67 aussi, 1 140 points sur le carré de Nantes ([dalle Nantes 0355-6690](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_EH_2025-07-21/LHD_FXX_0355_6690_PTS_LAMB93_IGN69.copc.laz)).

**Chaîne et exigences**
- Classification automatique avec Terrasolid et des modules d'IA — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf).
- Deux niveaux : « Classified » entièrement automatique et « Optimized » avec corrections manuelles. Pour l'Optimized, audit visuel d'environ 10 % des nuages livrés, erreurs listées et notées, attention particulière aux confusions bâtiments/ponts/sol, rappel minimal par bâtiment de 99,9 % en zones à enjeux (inondables, urbaines) et 99,5 % ailleurs — [FRACTAL](https://arxiv.org/pdf/2405.04634v4). La spécification « tolère certaines erreurs » selon la classe — même source.
- Fusion règles + probabilités d'apprentissage profond + base bâtiment, en production seulement pour les bâtiments dans `lidar-prod`. Les bases 2D peuvent être incomplètes, périmées et décalées en XY — [IGNF/lidar-prod](https://github.com/IGNF/lidar-prod).
- Contrainte de qualité de la validation bâtiment « precision and recall above 98 % ». Vérification automatique de 85 % des groupes de points en janvier 2022, puis 96 % — [LIDAR Magazine, mai 2024](https://lidarmag.com/2024/05/04/3d-ai-in-the-lidar-hd-production-process/). L'unité est le groupe de points connexes, pas le point.

**Part de chaque procédé de classement** (mesure propre, 20 087 dalles, champ `procede_classement`, [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities))
- IGN_AUTO_V5 82,6 % ; ST_AUTO_MANUEL 13,1 % ; IGN_AUTO_POST_EXP 2,3 % ; LHDV5 1,0 % ; IGN_AUTO_POST_CHAMPS 0,8 %. Exemple : Paris centre en IGN_AUTO_MANUEL, Lyon en ST_AUTO_MANUEL, Toulouse, Nantes, Strasbourg et Marseille en IGN_AUTO_V5.

**Performance mesurée, modèle de référence et non production**
- Modèle RandLA-Net à 7 classes sur FRACTAL : mIoU 77,5 %, OA 96,1 %. Bâtiment IoU 90,4, précision 96,2, rappel 93,7 ; sol IoU 91,9 ; végétation 93,8 ; eau 90,1 ; pont 65,2 ; sursol pérenne 63,5 ; autre 47,5 — [FRACTAL, tab. 4 et annexe C.1](https://arxiv.org/pdf/2405.04634v4). La vérité terrain vient de zones corrigées et auditées. Ces chiffres évaluent un modèle de recherche sur des classes regroupées, pas le produit.
- Un benchmark LoD2 du LASTIG utilise les classes 6 et 67 pour conserver tous les bâtiments potentiels — [Geniet et al., ISPRS Archives XLVIII-1/W6-2025](https://isprs-archives.copernicus.org/articles/XLVIII-1-W6-2025/83/2025/isprs-archives-XLVIII-1-W6-2025-83-2025.pdf) (classes relevées via résultat de recherche).

### Inferences
- `ST` dans ST_AUTO_MANUEL désigne probablement un sous-traitant. Je n'ai pas de définition officielle des codes de `procede_classement`.
- Pour une coupe de bâtiment, retenir 6 + 67 évite de perdre les bâtiments récents absents de la BD Topo. Il faut prévoir que la classe 6 contient aussi des auvents et des structures légères.
- Pour un pont, seule la coupe combinant 17, 1 et 64 décrit l'ouvrage, et il faut exclure 66. Les piles se trouvent en classe 1, avec les véhicules et le mobilier temporaire.
- Une ruine ou un monument partiellement détruit peut basculer de 6 à 1 : la spécification range les ruines en 1 alors que châteaux et fortifications sont en 6.
- Les objectifs de rappel portent sur l'existence d'un bâtiment. Ils ne disent rien de l'étiquette des points de façade individuels, en bord de toit ou sur balcon.

### Gaps
- Taux d'erreur par classe de la version de production V5, matrice de confusion officielle et rapports qualité par bloc : introuvables.
- Défauts documentés spécifiques à la végétation contre les façades (lierre, arbres contigus) : aucune source quantitative trouvée.
- L'outil tiers `ign-lidar-hd` revendique 94 à 97 % de détection de façade : affirmation non évaluée par des pairs, à ne pas reprendre comme preuve.

## Échantillonnage des surfaces verticales, occlusions, débords de toit et comparaison aux détails d'architecture

### Takeaway
Aucune étude publiée ne quantifie les façades du LiDAR HD. Sur quatre carrés urbains de 120 m, ma mesure donne une médiane de 1,2 à 4,9 points/m² de mur sur les colonnes de mur détectées, soit 9 à 14 fois moins que la densité horizontale et un espacement moyen de 0,45 à 0,9 m. Cela situe bien la masse d'un mur et la hauteur d'une corniche, mais pas les baies, moulures ou débords fins. Ces valeurs excluent par construction les murs non vus.

### Cited Findings

**Mesure propre sur le LiDAR HD (non publiée, faible échantillon)**

Méthode : quatre carrés de 120 × 120 m en centre-ville, lus dans les dalles COPC diffusées : [Toulouse 0574-6280](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_IQ_2024-12-20/LHD_FXX_0574_6280_PTS_LAMB93_IGN69.copc.laz), [Lyon 0842-6520](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_OL_2025-02-20/LHD_FXX_0842_6520_PTS_LAMB93_IGN69.copc.laz), [Paris 0651-6862](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_KE_2025-06-06/LHD_FXX_0651_6862_PTS_LAMB93_IGN69.copc.laz), [Nantes 0355-6690](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_EH_2025-07-21/LHD_FXX_0355_6690_PTS_LAMB93_IGN69.copc.laz). Sur les classes 6 et 67, une « colonne de mur » est une cellule XY de 0,5 m contenant au moins 3 points et au moins 3 m d'étendue en Z. La densité de mur vaut n / (0,5 m × étendue Z).

| | Toulouse | Lyon | Paris | Nantes |
|---|---|---|---|---|
| Capteur | RIEGL VQ-1560 II | RIEGL VQ-780 II-S | Leica TerrainMapper | Optech T2000 |
| Tous points, pts/m² (carré) | 56,9 | 39,3 | 13,5 | 24,6 |
| Derniers échos/m² (approximation des impulsions) | 53,7 | 36,9 | 11,6 | 23,4 |
| Bandes distinctes dans le carré | 4 | 3 | 2 | 2 |
| Angle de scan absolu médian / p95, tous points (°) | 17,7 / 27,5 | 15,0 / 26,0 | 6,1 / 8,8 | 10,4 / 12,5 |
| Colonnes de mur | 6 584 | 7 484 | 3 700 | 3 428 |
| Densité de mur p25 / médiane / p75 (pts/m²) | 2,9 / 4,9 / 7,9 | 1,6 / 2,8 / 5,0 | 0,9 / 1,2 / 1,6 | 1,8 / 2,9 / 4,2 |
| Rapport densité tous points / densité de mur médiane | 11,7 | 14,2 | 11,0 | 8,6 |
| Bins de 1 m remplis entre le point haut et le point bas de la colonne, médiane | 53 % | 44 % | 40 % | 50 % |
| Colonnes vues par 2 bandes ou plus | 99,6 % | 96,5 % | 92,7 % | 98,3 % |
| Part de points à normale quasi horizontale parmi 6+67 (ACP, 12 voisins) | 13,0 % | 14,9 % | 13,6 % | 4,6 % |
| Angle absolu médian : points verticaux / autres (°) | 25,0 / 17,8 | 23,0 / 15,0 | 6,4 / 6,1 | 10,2 / 10,4 |

Limites à conserver :
- Biais de survie : un mur sans point, ou avec moins de 3 points par colonne, disparaît de la statistique. Les médianes décrivent des murs vus, pas tous les murs.
- Aucune vérité terrain sur le linéaire réel de façades. La complétude n'est donc pas mesurée.
- L'angle de scan d'un carré de 120 m dépend de sa position dans la fauchée, donc ces angles ne sont pas des paramètres de vol. Leur comparaison entre scanners est aussi incertaine, car les géométries de balayage diffèrent.
- Une colonne vue par deux bandes peut l'être deux fois du même côté. Cela ne prouve pas que les deux faces d'un bâtiment sont vues.
- Une cellule mesurant 0,5 m surestime légèrement la longueur de mur pour un mur oblique, et les points de pignon ou de lucarne peuvent contaminer les colonnes.

**Études ALS comparables (non LiDAR HD, mention obligatoire)**
- Métriques de densité verticale sur Brooklyn : relevé USGS 2014 à 6,50 pts/m² horizontal pour 0,14 pt/m² vertical (écart-type 0,12) ; NYC 2017 à 10,93 pts/m² pour 0,66 pt/m² (écart-type 1,39) ; Sunset Park 2019 à 510 pts/m² pour 49,74 pts/m². Rapport horizontal/vertical de 46,1, 16,5 et 10,3 — [Stanley & Laefer, ISPRS J. 2021, arXiv 2010.09951](https://export.arxiv.org/abs/2010.09951). Le nombre moyen de passages vus sur les murs est de 0,60 et 0,65 pour les deux jeux à densité comparable au LiDAR HD, contre 9,49 à Sunset Park.
- Pour un scanner au nadir, la densité verticale croît avec l'angle de 0 à 45° (ρ_V = ρ_H tan θ) et dépend de la hauteur du mur ; l'estimation directe depuis la densité horizontale n'est pas possible — [Stanley & Laefer](https://export.arxiv.org/abs/2010.09951).
- Le recalage entre passages pèse de façon disproportionnée sur l'erreur des surfaces verticales, pas des surfaces horizontales — [Stanley & Laefer](https://export.arxiv.org/abs/2010.09951).
- Pour réduire les occlusions, il a été proposé des recouvrements d'au moins 67 %, à basse altitude (300 à 400 m), lente vitesse (90 km/h), en passages diagonaux à la trame des rues, soit l'inverse d'un levé national — [Stanley & Laefer, citant Hinks et al. 2009](https://export.arxiv.org/abs/2010.09951).
- Des résultats de recherche, sans lecture intégrale de ma part, signalent : retours manquants sur surfaces verticales et obliques à Dublin — [Gharibi & Habib, PE&RS](https://www.citedrive.com/en/discovery/scan-angle-analysis-of-airborne-lidar-data-for-missing-return-approximation-in-urban-areas) ; façades clairsemées en ALS — [Zhang, Verbree & Wang, IEEE Access 2021](https://pure.tudelft.nl/ws/portalfiles/portal/89156182/09380239.pdf) ; trous entre bâtiments hauts et rapprochés à Manhattan — [arXiv 2205.14585](https://arxiv.org/pdf/2205.14585) ; façades souvent vides dans les données ALS ouvertes — [Remote Sensing 2019](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-11-00420/article_deploy/remotesensing-11-00420.pdf).

### Inferences
- L'espacement moyen 1/√ρ de mes médianes de mur est d'environ 0,45 m à Toulouse, 0,6 m à Lyon et Nantes, 0,9 m à Paris. Un trumeau, une baie ou un bandeau plus petit que 2 à 3 espacements n'est pas résolu. Une tranche de 1 m d'épaisseur sur un mur parisien contiendrait typiquement à peine plus d'un point par mètre de hauteur.
- Le rapport de 9 à 14 entre horizontal et vertical rejoint l'intervalle de 10 à 46 de Stanley & Laefer, et mes densités de mur dépassent celles des deux jeux ALS à 6-11 pts/m². Ce rapprochement reste indicatif : mon calcul ne retient que les murs vus, ce qui favorise mes valeurs, alors que Stanley & Laefer agrègent sur les surfaces verticales.
- Le rapport horizontal/vertical ne suit pas l'angle médian dans mes quatre carrés (Nantes 8,6 à 10°, Paris 11,0 à 6°, Toulouse 11,7 à 18°, Lyon 14,2 à 15°). La relation ρ_V = ρ_H tan θ de Stanley & Laefer n'est donc ni confirmée ni infirmée ici. En revanche, à Toulouse et à Lyon, les points à normale horizontale ont un angle médian nettement plus fort que les autres (25° contre 18°, 23° contre 15°), ce qui va dans le sens attendu.
- Géométrie d'une rue de largeur L bordée de murs de hauteur H (calcul simple, sans donnée LiDAR HD) : un rayon d'angle θ à la verticale, rasant le toit opposé, atteint le mur à une profondeur L/tan θ sous la corniche. Le pied du mur n'est donc visible que si tan θ ≤ L/H. À 25°, cela autorise H/L jusqu'à 2,1 ; à 28°, jusqu'à 1,9. Près du nadir, le masquage par le bâtiment opposé est faible, mais les rayons rasent le mur et la densité chute (tan 6° ≈ 0,1). Un mur tourné à l'opposé de toutes les bandes ne reçoit aucun point, quel que soit l'angle.
- La hauteur du toit et le profil de faîtage sont bien échantillonnés (11 à 55 points par m² de cellule occupée en médiane). La sous-face d'un débord de toit n'est pas visible par construction, car un rayon descendant ne l'atteint pas. La coupe situera l'égout, pas l'épaisseur du débord, ni la position du mur derrière lui.
- Sous un pont, seul un rayon oblique atteint le sol. Le nuage comporte alors des points virtuels (classe 66) dans les zones sans mesure, à exclure de toute coupe fine.
- Sous canopée, la présence de points sol dépend de la saison et de la densité du feuillage. Je n'ai chiffré ce point ni en forêt ni sous alignements d'arbres.

### Gaps
- Aucune étude publiée à ma connaissance sur les façades du LiDAR HD : densité par orientation, complétude par rapport à une référence terrestre ou cadastrale, façades vues d'un seul côté.
- Largeur de faisceau et diamètre d'empreinte du LiDAR HD : inconnus faute de hauteur de vol officielle.
- Études quantitatives sur débords de toit et sous-faces en ALS à 10-20 pts/m² : non trouvées.
- Distribution des façades selon leur orientation par rapport aux lignes de vol : non mesurée ici.

## Attributs disponibles par point et utilité pour séparer façades et bandes

### Takeaway
Le format 6 contient intensité, échos, angle de scan, temps GPS et identifiant de bande, mais ni RVB ni infrarouge. `point_source_id` et `gps_time` séparent bien les bandes dans les tuiles contrôlées. Une colorisation par ortho verticale externe, comme celle de FRACTAL, attribue aux façades une couleur qui n'est pas la leur.

### Cited Findings
- Mesure propre, carrés urbains COPC, dimensions lues dans le fichier pour les quatre villes : `X, Y, Z, intensity, return_number, number_of_returns, synthetic, key_point, withheld, overlap, scanner_channel, scan_direction_flag, edge_of_flight_line, classification, user_data, scan_angle, point_source_id, gps_time`. Format de point 6, 30 octets, sans canal RVB/NIR et, sur les trois en-têtes bruts contrôlés, sans VLR d'octets supplémentaires — [dalle Lyon](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_OL_2025-02-20/LHD_FXX_0842_6520_PTS_LAMB93_IGN69.copc.laz).
- `gps_time`, converti en temps GPS absolu (+10⁹ s), retrouve exactement les dates du WFS sur Toulouse : du 29/05/2022 au 15/06/2022 — [dalle Toulouse](https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_IQ_2024-12-20/LHD_FXX_0574_6280_PTS_LAMB93_IGN69.copc.laz) (mesure propre).
- `point_source_id` portait 2 à 4 valeurs distinctes selon le carré, et un ajustement par bande a convergé sur chacune (voir section suivante) — mêmes dalles (mesure propre).
- Intensité : « une valeur non normée qui varie selon les Lidar » — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf). Les médianes observées illustrent ce point : 820 à Toulouse, 1 082 à Lyon, 604 à Paris, 240 à Nantes (mesure propre, mêmes dalles).
- Échos : la part de points à écho unique est de 88,8 % à Toulouse, 87,8 % à Lyon, 73,7 % à Paris et 90,2 % à Nantes (mesure propre). Numéro d'écho maximal : 6 à Toulouse et Paris, 4 à Lyon et Nantes.
- La colorisation n'est pas livrée dans ces dalles. Les jeux FRACTAL sont colorisés a posteriori par ORTHO HR (RVB + PIR, 20 cm) à l'aplomb, « regardless of potential obstructions » : un point sol sous un arbre prend la couleur de l'arbre — [FRACTAL](https://arxiv.org/pdf/2405.04634v4). Les auteurs notent aussi le flou des limites entre objets.
- L'IGN a annoncé deux attributs supplémentaires, `DTM_MAKER` et `DSM_MAKER`, signalant les points utilisés pour les modèles, dans des versions devant remplacer les nuages existants — [cartes.gouv.fr, mars 2025](https://cartes.gouv.fr/aide/fr/partenaires/ign/generalites-ign/actualites/2025-03-lidarhd-et-produits-derives/). Ils sont absents des dalles de Toulouse, Lyon et Nantes (éditions 12/2024 à 07/2025, mesure propre).

### Inferences
- `point_source_id` et `gps_time` permettent de séparer les bandes dans une tranche, d'attribuer chaque point de mur à son passage et de détecter les bandes acquises à des dates différentes.
- `scan_angle` signé peut indiquer le côté de l'avion, mais le signe dépend du cap de chaque bande. Sans la trajectographie, il ne donne pas la direction d'où la façade est vue.
- L'intensité peut être utile à l'intérieur d'une même bande, pas pour comparer deux capteurs. Une intensité normalisée suppose de connaître capteur, distance et incidence.
- Coloriser un mur par une ortho verticale n'a pas de sens : un point de façade prendrait la couleur du trottoir ou du toit voisin.

### Gaps
- Sémantique opérationnelle de `edge_of_flight_line`, `overlap`, `scanner_channel` et `user_data` sur les tuiles LiDAR HD : non vérifiée.
- Existence de dalles au format 8 (RVB + NIR) : aucune observée sur quatre dalles, sans preuve qu'il n'en existe pas ailleurs.
- Diffusion effective de `DTM_MAKER`/`DSM_MAKER` en 11/2026 : non établie.

## Hétérogénéité des dates, saison et décalages entre bandes

### Takeaway
Les vols s'étendent de 2021 à 2026, sans sélection de saison feuillue ou non. Un carré de 120 m à Lyon combine des bandes acquises à cinq mois d'écart. Les décalages mesurés entre bandes restent centimétriques sur surfaces planes (médianes de 0,6 à 2,5 cm en Z) et de 2 à 9 cm sur façades, avec un p95 de 16 cm à Nantes. Un mur peut donc apparaître doublé, soit environ 0,5 à 1,6 mm au 1:100.

### Cited Findings

**Dates et saisons**
- Acquisitions « estivales et hivernales (suivant les contraintes commanditaires) » — [IGN, Atelier LiDAR](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf). Le programme doit gérer les saisons « leaf-on or leaf-off » — [FRACTAL](https://arxiv.org/pdf/2405.04634v4).
- Mesure propre, 20 087 dalles, `date_fin_acquisition` : 2021 22 %, 2022 27 %, 2023 24 %, 2024 16 %, 2025 11 %, 2026 0,5 %. Par mois : novembre à mars 41,6 %, avril 11,9 %, mai à octobre 46,4 % — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities). Le champ donne une date de fin par dalle, sans indiquer l'état des feuilles.
- Mesure propre, intervalle GPS à l'intérieur d'un carré de 120 m : Lyon du 14/04/2021 au 24/09/2021 (5 mois) ; Toulouse du 29/05 au 15/06/2022 (17 jours) ; Nantes du 21/03 au 12/04/2024 (22 jours) ; Paris le 03/03/2023 (un seul jour) — dalles citées dans la section précédente.
- Le WFS expose `date_debut_acquisition` et `date_fin_acquisition` par dalle — [WFS](https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities).

**Décalages entre bandes** (mesure propre, mêmes quatre carrés, pas d'équivalent publié sur le LiDAR HD)
- Méthode Z : dans les cellules de 2 m où un plan commun avec un décalage par bande s'ajuste à moins de 5 cm d'écart-type résiduel, écart absolu entre décalages des bandes.
- Méthode façade : sur les points à normale quasi horizontale, dans des cellules de 3 m contenant un mur rectiligne et au moins 8 points par bande, écart absolu entre positions moyennes des bandes selon la normale.

| Écart absolu entre bandes, médiane / p95 | Toulouse | Lyon | Paris | Nantes |
|---|---|---|---|---|
| Sol, classe 2, Z (cm) | 0,8 / 2,9 | 0,9 / 3,2 | 1,1 / 3,2 | 1,4 / 2,9 |
| Bâtiment, classe 6, Z (cm) | 0,6 / 2,1 | 1,8 / 5,4 | 1,4 / 4,0 | 2,5 / 10,7 |
| Façades, selon la normale (cm) | 2,1 / 5,5 | 3,7 / 10,1 | 4,7 / 10,9 | 8,7 / 15,8 |
| Paires comparées (sol / bâtiment / façade) | 4 223 / 3 622 / 221 | 2 600 / 1 737 / 69 | 1 089 / 435 / 142 | 1 048 / 777 / 113 |

Ces cellules sélectionnent des surfaces planes et des murs rectilignes. Les doublons nets de plus de 30 à 40 cm en sont en partie exclus, et un relief réel de façade (balcon, retrait) vu sous deux angles peut créer un faux décalage. Une valeur par ville reste très insuffisante pour généraliser.

**Étude comparable (ALS italien LiDAR-ITA, capteurs de même famille)**
- Sur 3 500 zones de contrôle entre bandes adjacentes : RMSE médiane Est 7,1 cm, Nord 7,4 cm, verticale 2,6 cm, pour des seuils de 15 cm en 2D et 8 cm en Z. Les plus grands écarts sont attribués à la végétation, vue depuis deux points de vue à des instants différents — [Casella et al., ISPRS Archives XLIX-B2-2026](https://isprs-archives.copernicus.org/articles/XLIX-B2-2026/125/2026/).

### Inferences
- Dans une coupe perpendiculaire à un mur, le doublement apparaît dans le plan de la coupe et ne dépend pas de l'épaisseur de la tranche : il faut le traiter par bande (`point_source_id`), pas en réduisant l'épaisseur.
- L'épaisseur fixe le nombre de points de mur disponibles. Avec 1,2 à 4,9 pts/m² de mur, une tranche de 20 à 50 cm ne fournit qu'environ 0,25 à 2,5 points par mètre de hauteur. Il faut donc des tranches larges pour voir un profil de mur continu, au prix d'un mélange d'éléments distincts le long du mur.
- Le décalage interne entre bandes (quelques cm) et l'erreur absolue annoncée (jusqu'à 50 cm en XY) sont deux grandeurs différentes. Une coupe peut être cohérente en elle-même et décalée de plusieurs décimètres par rapport au cadastre ou à un relevé terrestre.
- Dans une coupe de terrain ou de voirie, il faut signaler la date de chaque bande : une tranche peut combiner une bande feuillue et une bande sans feuilles, ce qui change l'apparence de la canopée sur quelques mètres.
- Le raccord entre deux blocs de 50 km ou deux missions n'a pas été mesuré ici. Les plus fortes différences de date et de capteur devraient s'y trouver.

### Gaps
- Aucun rapport IGN public trouvé sur l'ajustement des bandes (tolérance, résidus par bloc).
- Décalages entre blocs, entre missions ou entre capteurs : non mesurés.
- Effet d'une saison sur la pénétration sous arbres, chiffré sur le LiDAR HD : non trouvé.
- Temps d'acquisition par bande et état phénologique réel en un point donné : seules les dates sont accessibles.
