# Urumea — du projet vide aux livrables QGIS

Montage français local d’environ **3 min 40**, avec **Tony — Punchy Ad & Social**
pour l’introduction et **Benjamin — Clear and Engaging** pour le corps.
Le rythme laisse lire le calcul de pente, les résultats et les changements de filtre.
Aucune publication externe n’a été effectuée.

- [Film MP4](urumea-from-zero-5.1.3-fr.mp4) et [sous-titres](urumea-from-zero-5.1.3-fr.srt).
- [PDF final](exports/urumea-analyse.pdf).
- [Projet portable avec données](urumea-projet-portable.zip) : décompresser le dossier entier puis ouvrir `urumea/urumea.qgz`.
- [GeoPackage filtré](exports/urumea_resultats.gpkg) et deux GeoTIFF dans `exports/`.
- [Modèle A3 prêt à tourner](design/Urumea%20A3.qpt), [sources et licences](sources.json), [narration](narration.fr.json).
- [Vérification complète](verified-observations.json), [archive du projet](bundle.json), [édition](edit.json), [contrôle média](media-check.json).

Les médias et les données restent sur le disque local ; les scripts, textes et
preuves sont versionnés. Le ZIP du plugin utilisé est identifié dans [package.json](package.json).
Il a été figé au début de la réalisation ; `dist` a ensuite évolué pendant les prises.
Le [contrôle d’inventaire](package-integrity.json) distingue le code des journaux
modifiés normalement à l’exécution. Aucun correctif du plugin n’a été introduit pour cette vidéo.

## Scénario réalisé et preuves

| Affirmation ou passage | Comportement observé et contrôle |
| --- | --- |
| Départ de zéro | Projet vide avant le premier prompt ; acquisition réelle des couches, sans jeu de couches préchargé. Prise `acquire04`. |
| Acquisition des sources | OSM par Overpass ; liens officiels du MNT GeoEuskadi et du ZIP URA donnés dans le prompt. Le film ne prétend pas que l’agent découvre seul ces liens. |
| Terrain, pente en pourcentage | Véritable MNT 5 m/2017, EPSG:25830 ; `gdal:slope`, pourcentage et calcul des bords ; moyenne par emprise avec `native:zonalstatisticsfb`. Recalcul indépendant : écart maximal **0,0** sur raster et moyennes. |
| Moteur de filtre | 2 995 entités bâtiments OSM acquises → **1 826** après tampon de **500 m** autour de l’Urumea → **108** après intersection ET avec le zonage URA T100. Identifiants comparés aux intersections géométriques indépendantes. |
| Filtre en cascade | À 300 m des bâtiments retenus : **995 voies**, **80 objets ponts linéaires**, **5 objets ponts surfaciques** ; identifiants vérifiés. Les objets ponts ne sont pas un compte d’ouvrages distincts. |
| Graphiques D3 | Deux véritables `run_chart_code`, puis placement des graphiques **c3 et c5**, pas de leurs premières versions Python. Histogramme : **108 valeurs valides, 0 manquante**. |
| Composition QGIS | A3 paysage, carte, progression des comptes, histogramme de pente, KPI **108 / 2 995**, sources et légende. Échelle liée à la carte : **2 × 250 m** ; nord natif QGIS. |
| Export | GeoPackage à sept tables : 108 / 995 / 80 / 5 / 10 / 1 / 2 entités. Deux GeoTIFF et PDF réellement écrits par les outils du plugin. Identifiants des tables OSM comparés aux couches affichées. |
| Sauvegarde proposée par l’agent | Carte native « Conserver ce travail ? », bouton et véritable dialogue QGZ filmés ; liens projet/données affichés. |
| Projet transmissible | Dossier minimal de données référencées copié ailleurs ; réouverture **sans réseau** des **15 couches**, avec filtres et composition. Les deux SVG D3 et le logo sont intégrés ; le nord utilise une ressource standard de QGIS. |
| Interface et zooms | Bureau QGIS réellement enregistré en 1920 × 1080 ; fenêtre QGIS 1920 × 990 et bandeau de légendes extérieur. Loupes de pixels enregistrés dans la carte ; menus, couches et FilterMate restent cadrés. |

La pente décrit le terrain. Elle n’est ni un seuil d’inondabilité ni une simulation
hydraulique. Le zonage officiel T100 est le critère d’aléa ; l’intersection d’une
emprise n’est pas un diagnostic de bâtiment. Les populations du graphique de
progression sont emboîtées et ne s’additionnent pas.

## Prises conservées

| Prise | Contenu | Durée brute |
| --- | --- | --- |
| `acquire04` | Projet vide, acquisition, carte visible, proposition native et sauvegarde | 70,7 s |
| `analysis03` | Reprojection, pente, moyennes, filtres 500 m / T100 / réseau et panneau FILTERING | 183,1 s |
| `composer02` | Deux D3, création du composeur, exports, panneau EXPORTING et sauvegarde | 183,2 s |
| `finish01` | Correction native de l’échelle, ajout du nord et réexport du PDF final | 164,8 s |
| `review02` | Livraison déplacée ouverte hors réseau, composeur cadré et lecteur PDF réel | 23,7 s |

Les fichiers de preuve sont dans `evidence/` ; les JPEG bruts restent dans
`/tmp/fm-urumea-from-zero/out/<prise>/urumea/frames/`.
Les prises complètes, muettes et sans accélération, sont aussi lisibles en MP4 :
[acquisition](prises/acquisition.mp4), [analyse](prises/analyse.mp4),
[composition](prises/composition.mp4), [finition](prises/finition.mp4),
[relecture](prises/relecture.mp4). Leur [inventaire](prises/takes-mp4.json)
contrôle les durées par rapport à l’horloge des captures.
Les attentes sont raccourcies au montage. Les vues de relecture montrent les
livrables ; les prises de création de l’agent sont conservées séparément.
Les graphiques D3 restent figés à leur état enregistré dans le projet.

Prises écartées : démarrage de scène incorrect (`acquire01`), cadrage/saisie du
dialogue (`acquire02`), requête au nom exact qui omettait « Urumea ibaia »
(`acquire03`, `analysis02`), destination de traitement non choisie dans la nouvelle
session (`analysis01`), saisie Qt d’un retour à la ligne (`composer01`). `review01`
précède la correction d’échelle. La répétition historique silencieuse et les
anciens montages Copernicus **MNS** sont des archives, pas la source du nouveau MNT.

## Scripts et reprise

- `scripts/urumea_full_capture.py` : phases `acquire`, `analysis`, `composer`, `finish_layout` ; vraie saisie et dialogues, contrôles bloquants sur les couches et sélections vides.
- `scripts/urumea_review_capture.py` : relecture de la livraison et du PDF, sans agent ni réseau.
- `scripts/urumea_composer_template.py` : modèle QPT ; l’échelle et le nord sont ajoutés après cadrage de la carte réelle.
- `scripts/urumea_progression.d3.js`, `scripts/urumea_slope_histogram.d3.js` : dessins sur les données réellement lues.
- `scripts/urumea_full_verify.py` : géométrie, identifiants, recalcul numérique, exports, D3, échelle et réouverture déplacée.
- `scripts/urumea_project_bundle.py` : copie des seuls dossiers de données référencés, inventaire SHA-256 et ZIP.
- `scripts/urumea_voice_elevenlabs.py`, `scripts/urumea_full_render.py` : voix mises en cache, montage et loupes sur interface entière.
- `scripts/urumea_raw_takes.py` : MP4 des prises complètes sur leurs horodatages d’origine.
- `scripts/docker/site_videos_d3.Dockerfile` : QtWebEngine pour D3 et QtPdf pour le lecteur réel ; image de réalisation `fm-video-pdf-lot5`.

Le dossier de travail isolé est monté en `/w`. Il contient le plugin extrait
dans `release/filter_mate`, un profil QGIS jetable configuré, les scripts et
`sources/mnt-source.json` / `sources/ura-source.json` issus de `sources.json`.
Le pilote se lance avec QGIS `--code /w/scripts/urumea_full_capture.py`,
`FM_CLIP=urumea`, `FM_FIT=0`, `FM_ZERO_PHASE=<phase>` et
`FM_VIDEO_OUT=/w/out/<prise>`. Pour le composeur, préciser
`FM_ANALYSIS_TAKE=/w/out/analysis03/urumea` et
`FM_ACQUIRE_TAKE=/w/out/acquire04/urumea`.

Une nouvelle session doit rechoisir sa destination via le véritable contrôleur
de sauvegarde avant les traitements GDAL ; le pilote le filme. Aucun profil,
portefeuille d’authentification ni clé de fournisseur n’entre dans les livrables.

Validation effectuée sous **QGIS 4.2.3 / Qt6 / Linux**, GDAL 3.12.2. Le contrôle
spécifique Windows/QGIS 4 reste à réaliser ; aucune prise Windows n’est annoncée.
Le scénario solaire et les autres démonstrations du lot restent décrits dans
le [rapport général du lot 5](../README.md).
