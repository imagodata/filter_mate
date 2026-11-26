# Teaser crue de l'Urumea — voix, montage, checklist (previz)

## Voix EN (53 s lues à ~150 mots/min ≈ 130 mots)
1. “One sentence in Plan mode: buildings, roads, bridges, the Urumea, and the terrain.”
2. “The agent derives height, then the mean height of every building. They color by exposure.”
3. “These results are temporary files. The export to a GeoPackage keeps the project with them.”
4. “Buildings under five meters by the river become the selection. Roads and bridges, within three
hundred meters.”
5. “Foot-evacuation isochrones around the exposed buildings: real escape, not a circle.”
6. “The filter becomes a favorite. A colleague replays it in one click, and tunes the height slider.”
7. “Same rule for the team, three layers at once, replayable when data change. A screening, at
thirty meters — not a risk assessment.”

## Voix FR (même minutage)
1. « Une phrase en mode Plan : bâtiments, routes, ponts, l'Urumea et le relief. »
2. « L'agent calcule l'altitude, puis l'altitude moyenne de chaque bâtiment. Ils se colorent par exposition. »
3. « Ces résultats sont des fichiers temporaires. L'export GeoPackage garde le projet avec eux. »
4. « Les bâtiments sous cinq mètres près de la rivière deviennent la sélection. Routes et ponts,
dans un rayon de trois cents mètres. »
5. « Les isochrones d'évacuation à pied autour des bâtiments exposés : la vraie fuite, pas un cercle. »
6. « Le filtre devient un favori. Un collègue le rejoue en un clic, et règle le curseur d'altitude. »
7. « Même règle pour l'équipe, trois couches d'un coup, rejouable quand les données changent.
Un premier tri, à trente mètres — pas une évaluation du risque. »

## SEGMENTS pour scripts/teaser_compose.py (prises à tourner sous ces noms)
# Montage : une seule prise 'urumea' (clip scripts/site_videos.py), 7 segments aux durées du
# storyboard (8, 8, 7, 7, 7, 8, 8), starts à relever au urumea-sheet.jpg après
# `scripts/site_videos_headless.sh clip urumea`, puis carte de fin presentation.html.
# SEGMENTS = [
#     ('urumea', 0.0, 8.0, ('One sentence. Buildings, roads, bridges, river, terrain.', ...)),
#     ('urumea', 8.0, 8.0, ('Height, then mean height per building.', ...)),
#     ('urumea', 16.0, 7.0, ('Temporary files don\'t survive. Export keeps all.', ...)),
#     ('urumea', 23.0, 7.0, ('Under 5 m by the river. Roads and bridges within 300 m.', ...)),
#     ('urumea', 30.0, 7.0, ('Foot-evacuation isochrones around exposed buildings.', ...)),
#     ('urumea', 37.0, 8.0, ('One favorite. Replayed in one click.', ...)),
#     ('card:end', 0, 8.0, ('FilterMate\nFree and open source · QGIS 3.22 to 4.x\nimagodata.github.io/filter_mate', ...)),
# ] (starts 8/16/23/30/37 provisoires : les caler sur la prise réelle, total 53 s)

## Rendu previz (MP4 de travail, PAS le teaser final)
- `previz-teaser-53s.mp4` : 53,0 s, 25 im/s, 1920×1080, H.264 + faststart, 7 schémas de synthèse
  filigranés « PREVIZ — NON TOURNÉ », légendes du storyboard. Vérifié : 1325 images, 6 coupes franches.
- Re-rendre : venv + `pillow imageio imageio-ffmpeg` (binaire ffmpeg statique), script scratch
  `/tmp/render_previz.py` (non versionné, à recopier dans `scripts/` s'il doit devenir un outil).
- Le MP4 final exigera les vraies prises QGIS (cf. checklist) montées via `scripts/teaser_compose.py`.

## Fin : présentation (`presentation.html`, chiffres illustratifs)
- 4 KPI + barres par tranche d'altitude + donut de la part exposée, filigrane PREVIZ.
- Bouton « Exporter PDF » (print A4 paysage, fond blanc) : le livrable papier du tri.
- Au tournage, remplacer les chiffres par ceux de la prise ; garder les mentions seuils
  illustratifs / pas une évaluation du risque.

## Checklist hors caméra (4 points, adaptés Urumea)
1. Bâtiments OSM : assez de bâtiments sous 5 m près de l'Urumea dans l'emprise, sinon élargir
   (Amara, Loiola, Martutene) ou changer d'emprise.
2. Chaîne de l'agent : du lieu jusqu'au style des bâtiments, ~10 appels d'outils, avec le token
   API Claude en modèle Haiku (variable d'environnement du poste de tournage, jamais dans le plan).
3. Favori : garde ses trois couches (bâtiments, routes+ponts, isochrones) et ses distances
   d'un poste à l'autre via le GeoPackage du dossier commun.
4. Export par l'agent : vérifié qu'il embarque le projet dans le GeoPackage.
