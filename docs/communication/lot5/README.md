# Lot 5 — démonstrations, livraison locale du 26 novembre 2026

**Nouvelle vidéo Urumea finalisée avec le ZIP 5.1.3 de `dist`** :
[vidéo, narration française et preuves de rejeu](urumea-linkedin-5.1.3/README.md).
Le MP4 dure 64,32 s ; la carte et ses changements sont visibles, avec voix et
sous-titres français. Il est prêt à être téléversé sur LinkedIn. La répétition
historique `urumea-rehearsal` reste distincte et non validée comme film final.


Travail isolé : `/tmp/filter_mate-lot5`, branche `codex/lot5-demonstrations`,
base `8fbd62c5`. Intégration dans main centralisée par la session de consolidation,
à la demande « merger au fur et à mesure ». Aucun push ni publication externe. La voix de la nouvelle vidéo Urumea est
générée avec la voix de synthèse française `fr-FR-HenriNeural`. Les fichiers communs des lots 1–3 et 7 ne sont pas modifiés.

## Sources réconciliées

- Base commune : conserver tous les scénarios existants et le brouillon Urumea.
- `filter_mate-agent-report` à `5d244ac5` + modifications locales : scène `report`,
  style du cours d'eau, langue QGIS configurable par `FM_LANG`.
- `filter_mate-clips` à `e2b3b41d` + modifications locales : film `ln` à **trois**
  chapitres, render, voix et narration. Les anciennes mentions `ln1..ln5` ne
  correspondent pas à la scène réellement présente. Pas de reprise du vieux moteur,
  de sa taille de dock ou de son ordonnanceur ; `maybe/dynamic/until` utilisent
  l'index `RUN['at']` actuel.
- `sources.json` conserve les empreintes des entrées, modifications non commitées incluses.

`site_videos.py` conserve `urumea`, ajoute `report`, `ln` et `sarlat-overview`.
Le lanceur liste les scènes sans importer QGIS, protège les prises existantes,
crée un profil/cache jetable, transmet la langue, arrête les erreurs/timeouts et
contrôle l'intégrité avant montage. Les nouvelles prises ont une provenance avec
empreintes du code et ID de l'image Docker ; elle ne contient pas l'environnement.
Les deux premières prises locales ont précédé cet ajout de provenance automatique.
Le contrôle final `/tmp/fm-lot5-final-check` (123 images, 8,1 s) valide la version
réconciliée du lanceur et conserve sa provenance dans `takes/final-control/`.

`fm5_clip_render.py` lit seulement les lignes dites dans la prise, espace les voix
après accélération, conserve la dernière ligne avant la carte finale et utilise
les polices Linux. `FM_VOICE_ENGINE=none` rend un **montage muet**, à durées de
sous-titres estimées. Les comptes des bandeaux sont ceux des événements `badge`.
La narration ne récite plus de nombres historiques non mesurés dans la prise.
`fm5_clip_voice.py --durations-only` inspecte les pistes existantes hors ligne,
crée le répertoire de durées et conserve la durée maximale des langues.

## Éléments prêts

- [Storyboard Urumea](../urumea-flood-teaser/storyboard.md),
  [fiche de prise](../urumea-flood-teaser/fiche-prise-agent.md),
  [narration/montage](../urumea-flood-teaser/script-montage.md).
- [Storyboard solaire](../solar-san-sebastian-teaser/storyboard.md) et prompts
  bilingue/storyboard + [requêtes EN](../solar-san-sebastian-teaser/requests.json).
  La scène `solar` n'existe pas : tournage manuel préparé, pas de commande fictive.
- Maquettes Urumea HTML locales, sans CDN : filigranes/chiffres fictifs explicites.
- Données Sarlat copiées dans `data/sarlat/`, [préflight QGIS](sarlat-preflight.json)
  et projet `data/sarlat/sarlat-ready.qgz` à chemins relatifs. Les TIFF d'orthophoto
  ne portent pas de SCR : EPSG:2154 est attribué dans le projet d'après l'emprise
  du `data-audit.json` existant ; les sources ne sont pas modifiées.
- Export Urumea de répétition copié dans `data/urumea/legacy-vectors.gpkg` et
  [audité](urumea-export-audit.json). **Vecteurs seulement**, aucun DSM sauvegardé.
- [Recettes de données](data-recipe.json), [registre des affirmations](claims.json)
  et `scripts/qgis4_windows_check.py` en lecture seule, prêt à exécuter sur Windows.

Les gros fichiers de données, images et vidéos restent locaux et ignorés par git,
conformément au dépôt. Aucun téléchargement solaire/Urumea supplémentaire n'a été lancé.

## Prises réalisées

- Vue Sarlat : `/tmp/fm-lot5-overview/out/site/sarlat-overview.mp4` + WebP et planche.
  **8,1 s**, 124 images brutes, montage 1280×800/25 ips. QGIS4.2.3 réel sous Xvfb,
  profil isolé. Carte et panneau visibles ; preuve d'ouverture des sources,
  aucune démonstration de filtre dans cette vue.
- Film Sarlat : `/tmp/fm-lot5-sarlat/out/ln/`, **188,3 s**, 2 835 images brutes,
  1920×1200, trois chapitres. Comptes observés : 113 bâtiments/106 parcelles,
  puis 182 parcelles/187 bâtiments, puis **100** bâtiments après ET LiDAR.
  Intégrité PASS, images de résultats inspectées ; les deux premiers chapitres
  sont aussi reproduits par un calcul QGIS/GDAL indépendant, sans FilterMate
  (`sarlat-independent-check.json`, PASS). Le calcul LiDAR est observé dans la prise,
  sans recalcul indépendant supplémentaire ; montage muet FR **151,28 s**, H.264 1920×1200/25 ips, 102,4 Mo.
  Aucun flux audio : voix et mixage restent à produire. Fichiers et empreintes
  dans [takes.json](takes.json), planche et trois résultats dans `takes/sarlat/`.
- Urumea existant : `/tmp/fm-video/out/urumea/`, 209,2441 s, 3 153 images.
  **Répétition non validée**, pas un teaser final : carte blanche sur les plans
  examinés, favori initialement refusé puis enregistré partiellement pour une seule couche,
  GPKG sans projet ni raster.
  Le nom d'une couche « isochrone » ne valide pas son algorithme.

Le brut Sarlat contient des messages GDAL `unable to open database file` lors de
requêtes de comptage temporaires ; les filtres aboutissent aux comptes consignés.
Conserver le stdout pour investigation, ne pas annoncer une exécution sans avertissement.
Le cadre Sarlat conserve volontairement deux sections du dock ; il n'obéit pas au
contrôle des vidéos de fond du site imposant un dock de 380 px. Ne pas utiliser ce
contrôle pour certifier ce film au dock de 470 px.

## Rejouer sans publication

Depuis la racine du dépôt, avec une image locale contenant QGIS, ffmpeg et PDAL :

```sh
scripts/site_videos_headless.sh list
# Source de données = copie locale préparée ; chemin absolu conseillé pour Docker.
export FM_WORK=/tmp/fm-lot5-new-take
export FM_GPKG_DIR="$PWD/docs/communication/lot5/data/sarlat"
export FM5_DATA="$FM_GPKG_DIR"
export FM_SARLAT_DIR=/data
export FM_IMAGE=fm-video
scripts/site_videos_headless.sh clip sarlat-overview ln
FM_VOICE_ENGINE=none FM_LANG=fr scripts/site_videos_headless.sh render-ln ln
```

`FM_WORK` doit être distinct d'une prise existante. Les profils de capture ne sont
pas des livrables : ils contiennent potentiellement une base d'authentification.
Pour une voix humaine enregistrée, placer les pistes aux chemins attendus puis
calculer les durées avec `fm5_clip_voice.py ROOT ffprobe ln --durations-only`.
La synthèse Sarlat n'a pas été exécutée. Pour la nouvelle vidéo Urumea, les pistes
françaises ont été générées avec Edge TTS puis mixées dans le MP4.

Préflight, avec le Python QGIS et `QT_QPA_PLATFORM=offscreen` :

```sh
python3 scripts/demo_preflight.py --data /chemin/sarlat \
  --project /chemin/sarlat/sarlat-ready.qgz --output /chemin/preflight.json
python3 scripts/demo_take_check.py /chemin/FM_WORK/out/ln
```

## Ce qui reste à produire

1. Après lots 1–3 intégrés : prise agent simple et `report` (Processing, deux
   graphiques, mise en page/PDF). Comparer appels, réponses, couches, graphiques
   et fichier PDF réellement ouvert. Pas de promesse d'atlas implicite.
2. Urumea : le DSM, le filtre actif, les exports rouverts et le rejeu des quatre
   couches sont désormais vérifiés dans le nouveau film 5.1.3. La desserte sur un
   réseau piéton complet et la liaison/reprise sur un second poste restent hors
   de ce montage ; elles nécessitent une démonstration séparée avant toute promesse.
   La maquette historique avec chiffres illustratifs ne sert pas au film final.
3. Solaire : acquisition de toutes les données, pente du MNS en **%**, contrôle
   NoData, filtres, desserte, export/favori, sept prises et narration EN finale.
4. Sarlat : contrôle final du montage, voix FR/EN, mixage et validation après écoute.
5. Exécuter le contrôle fourni sur le vrai poste Windows/QGIS4 ; aucun contrôle
   Windows réel n'a encore été effectué. Les essais ici sont sous Linux/Xvfb.

Validation observée de la première tranche : **13 tests PASS**
(`test_demo_workflow.py` et `test_site_videos_setup_cards.py`), compilation Python,
`bash -n`, préflight QGIS4.2.3 et contrôle indépendant corridor/raster PASS. Ces contrôles ne certifient pas les scénarios
Urumea, solaire ou report. Aucun changement i18n/CHANGELOG/AGENT_MODE/agent_eval.

Sur Windows, utiliser le diagnostic dans la console du QGIS déjà ouvert. Pour
filmer sans WSL, définir `FM_CLIP=ln`, `FM_SARLAT_DIR` sur les données Windows et
`FM_VIDEO_OUT` sur un nouveau dossier, puis lancer `qgis-bin.exe --profiles-path
<profil_de_tournage> --profile lot5 --lang fr --code <repo>/scripts/site_videos.py`.
Initialiser ce profil de tournage une fois avant la prise. Le wrapper historique
`site_videos.sh` n'est pas repris depuis l'ancienne branche ; les outils de voix et
rendu se lancent directement avec le Python QGIS.

Rendu Urumea de répétition disponible : `takes/urumea-rehearsal/urumea-rehearsal.mp4`,
111,4 s, 1920×1080/25 ips, muet, 8,45 Mo, décodage intégral PASS. Les légendes
rapportent les observations : le favori est d’abord refusé puis sauvegardé pour
`Buildings altitude` seulement. Aucun rejeu complet n’est montré. La prise reste
non validée comme teaser final ; les images sources ne sont pas modifiées.
