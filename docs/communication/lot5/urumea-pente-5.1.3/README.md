# Urumea — pente, tampon rivière et voix ElevenLabs

**Version de travail MNS, 1 min 42,4 s.** La proposition de reprise avec MNT et
zonage officiel est dans [scenario-v2.md](scenario-v2.md) ; elle n'est pas encore
tournée. Cette version conserve les éléments validés de rythme, d'habillage et
de voix.

Le scénario de reprise vise désormais **environ 3 minutes**, depuis un projet
vide : acquisition par prompts, proposition native de sauvegarde, filtres du
moteur FilterMate, graphiques D3.js, composition, export PDF et projet réouvrable.
La fenêtre QGIS et le panneau du plugin restent visibles, avec loupes ponctuelles.
La [maquette A3](composer-maquette.png), le [plan](composer-plan.json) et la
[relecture du parcours de sauvegarde](agent-save-flow.md) préparent ces prises.
Le [prévol technique](preflight-composer/preflight.json) valide D3 → SVG intégré
au composeur → PDF et QGZ déplacé/rouvert sur données fictives ; il ne valide
pas encore l'acquisition MNT/URA ni la portabilité du futur projet complet.

Reprise du film Urumea : la pente remplace le seuil d'altitude, le tampon
rivière passe à 500 m, et les résultats restent plus longtemps visibles.
Le montage utilise uniquement des captures de la vraie fenêtre QGIS et une
frame graphique d'ouverture. Il n'a pas été publié.

## Introduction et voix

La frame d'ouverture emploie le logo officiel `icons/logo.png` du dépôt avec :

- `imagodata présente`
- `FilterMate`
- `Le meilleur compagnon pour QGIS`
- `Un exemple d’analyse de l’Urumea — Saint-Sébastien`

**Tony - Punchy Ad & Social** (`fsYODoWLWYJ5ai6CAN3M`) dit uniquement
« Imagodata présente… FilterMate. » dans cette introduction. **Benjamin - Clear
and Engaging** (`F9KUTOne5xOKqAbIU7yg`, français standard) conserve la narration
de la démonstration. Le moteur réellement utilisé est `eleven_v4` ; les pauses
et la consigne de débit sont données dans le texte, sans curseur de vitesse
inopérant sur ce modèle. Voir la
[documentation de génération](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
et les [consignes de rythme](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices).

Les pistes, leur texte, leurs durées et leurs empreintes se trouvent dans
`voice/body/` et `voice/intro/`. La piste Benjamin `07-favori` a été préparée
mais n'est pas employée dans le montage analyse/export. Les clés et profils ne font pas partie de
cette livraison.

Le script `scripts/urumea_voice_elevenlabs.py` lit la clé locale sans la
journaliser. Son cache vérifie le contenu de la requête et l'empreinte du MP3
avant de réutiliser une piste ; aucun nouvel appel n'a été nécessaire pour
contrôler la réutilisation de Benjamin.

## Prise et contrôles

Le plugin provient du ZIP 5.1.3 dont l'empreinte est dans `package.json`.
Les 969 fichiers extraits ont été comparés au ZIP sans différence. Le tournage
est réalisé avec QGIS 4.2.3 sous Linux/Xvfb, dans un profil jetable. Il ne
constitue pas une validation native Windows.

Le modèle Copernicus de 30 m et les 3 073 objets bâtiment sont préparés avant
la prise. L'agent calcule réellement `gdal:slope` en pourcentage, puis la moyenne
zonale, les filtres et les exports. La destination du projet est choisie avant
le calcul GDAL par le contrôleur normal « Enregistrer le projet et les couches ».
La préparation du tournage ne modifie pas le code du plugin.

L'assistance de présentation fixe le cadrage, place les rasters sous les
vecteurs et donne aux bâtiments une palette contrastée. La pente colorée est
montrée pendant son calcul ; le fond redevient un relief discret pour lire les
bâtiments et le couloir. Cette assistance ne crée ni ne rétablit de filtre.

Le vérificateur rouvre les exports, recalcule indépendamment la pente et les
moyennes, compare les identifiants des bâtiments retenus et recalcule les comptes
routes/ponts par SQL. Il vérifie les unités, le tampon de 500 m, les couches
exportées et les arguments du filtre réseau à 300 m. Les messages de l'agent
ne servent pas de preuve. Le reçu est `verified-observations.json`.

| Couche | Complète | Retenue / exportée |
|---|---:|---:|
| Bâtiments | 3 073 | 1 079 |
| Routes | 701 | 587 |
| Ponts lignes | 158 | 130 |
| Ponts polygones | 8 | 8 |

Le filtre de pente seul retient 1 463 bâtiments. La sélection finale est
reproduite indépendamment, identifiants compris ; les écarts maximum sur le
raster de pente et les moyennes sont nuls. Les six tables vectorielles, dont
la rivière et le couloir, et les deux GeoTIFF sont rouverts sans erreur. Le
contrôle ne relève aucune erreur d'outil dans la prise analyse/export.

Le tampon réellement utilisé est polygonisé avec `SEGMENTS=5` et retient
1 079 bâtiments. Le calcul préparatoire par distance directe en retenait
1 080 ; le chiffre du film vient de la géométrie effectivement employée.

Les distances et le seuil sont illustratifs. Copernicus représente la surface,
incluant constructions et végétation, à 30 m ; il ne mesure pas précisément la
pente du terrain ou du toit de chaque bâtiment. La vidéo ne prédit pas de crue.
Les ponts sont des objets OSM, et non un nombre de ponts physiques distincts.

## Reproduction

Le dossier local de travail est `/tmp/fm-urumea-pente-513`, avec les sources
publiques, le plugin extrait et les scripts sous `data/`, `release/` et
`scripts/`. Les profils d'authentification restent exclusivement dans ce dossier
de travail. La prise finale analyse/export est `out/take05/urumea`.

Dans l'image `fm-video`, ce travail est monté sous `/w`. Lancer QGIS avec
`FM_CLIP=urumea`, `FM_ANALYSIS_ONLY=1`, un nouveau profil et
`--code /w/scripts/urumea_slope_capture.py`. Le script s'appuie sur les helpers
`site_videos.py` et `urumea_linkedin_capture.py`.

```sh
python3 /w/scripts/urumea_slope_verify.py \
  --root /w --take /w/out/take05/urumea --analysis-only
python3 /w/scripts/urumea_slope_render.py \
  --root /w --take /w/out/take05/urumea --analysis-only
```

Le renderer s'appuie sur les fonctions graphiques de `urumea_linkedin_render.py`.
Les plans, sources, voix et durées sont dans le reçu de montage. Les médias et
données restent locaux et ignorés par Git ; les scripts et preuves textuelles
sont versionnés.

## Point restant : favori

La prise technique `take03` a révélé un rejeu incorrect : le filtre des bâtiments
a été posé sur le couloir, tandis que les filtres du réseau étaient rétablis.
Deux sorties Processing persistées ont le même nom `output.gpkg`, produisant
la même signature `ogr::output` ; la résolution par signature précède l'ID.
Le problème a été transmis à la session de consolidation. Il faut corriger puis
retester ce cas avant une nouvelle démonstration de rejeu sur ce paquet.

Cette étape et sa narration sont donc absentes du montage analyse/export. Les
preuves de la limite sont conservées ; aucune restauration manuelle ne simule
un favori réussi. La vidéo finale reste centrée sur la pente, le tampon et les
exports effectivement vérifiés.
