# Urumea — vidéo LinkedIn avec voix française, FilterMate 5.1.3

Nouvelle prise réelle, distincte de `urumea-rehearsal` : carte visible, changements
de données visibles, remise à zéro puis rejeu du favori. Le plugin est celui du
ZIP `dist/filter_mate_v5.1.3.zip`, empreinte
`5ac5cdde9970e31c64a3b79ed3cfb9408e3d5850c3619e1ea46e02c3c6357625`.
Les 833 fichiers source/ressource contrôlés sont identiques au ZIP : voir
[package-integrity.json](package-integrity.json).

Le montage final local est `urumea-linkedin-5.1.3-fr.mp4` : **64,32 s**, H.264,
1920×1080, 25 images/s, voix française AAC stéréo 48 kHz. Les sous-titres sont
incrustés ; un `.srt`, une couverture et une planche accompagnent le MP4.
Le format et la durée respectent les [spécifications de partage vidéo LinkedIn](https://www.linkedin.com/help/linkedin/answer/a7494039).
La vidéo n'a pas été téléversée ni publiée.

La voix de synthèse française `fr-FR-HenriNeural` accompagne les scènes :
comparaison initiale, données de départ, ajout du modèle de surface, moyenne
zonale par emprise, filtrage, sauvegarde, remise à zéro, rejeu et export.
[narration.fr.json](narration.fr.json) conserve les phrases et
[narration-durations.json](narration-durations.json) leurs durées mesurées.
Les attentes sont montées et les résultats conservés à l'image le temps de la voix.
Les compteurs ne s'affichent qu'après l'action correspondante.

## Résultats observés et vérifiés

La prise finale contient 2 304 images de la vraie fenêtre QGIS 4.2.3 sous Xvfb,
environ 153,4 s de brut. La carte est rendue dès l'ouverture et conserve son
cadrage pendant les traitements. Le script réactive le rendu suspendu pendant le
chargement ; ce point causait la carte blanche de l'ancienne répétition.

| Couche | Carte complète | Après filtrage | Après remise à zéro | Après rejeu |
|---|---:|---:|---:|---:|
| Bâtiments altitude | 3 073 | 63 | 3 073 | 63 |
| Routes | 701 | 304 | 701 | 304 |
| Ponts lignes | 158 | 92 | 158 | 92 |
| Ponts polygones | 8 | 6 | 8 | 6 |

Les lignes et polygones de pont sont des objets OSM, pas un décompte de ponts
physiques distincts. Les nombres viennent des sorties des outils et des données,
pas du texte de l'agent. Les expressions restaurées sont identiques ; les comptes
routes/ponts ont été recalculés par SQL en lecture seule, puis comparés aux
tables exportées. Le rejeu n'appelle que `apply_favorite` : aucune autre opération
de filtrage ne rétablit les couches à sa place. Voir
[verified-observations.json](verified-observations.json).

L'export réellement rouvert contient cinq tables vectorielles dans
`urumea_resultats.gpkg`, dont l'Urumea de contexte, et un GeoTIFF Copernicus séparé
de 163×132 pixels avec son style. Aucun projet embarqué n'est annoncé.

Le seuil <5 m porte sur la moyenne d'un **modèle de surface** par emprise, incluant
bâtiments et végétation ; il ne mesure pas la hauteur d'un bâtiment ni un niveau
de crue. Les distances 200/300 m et le seuil sont illustratifs. Le film mentionne
qu'il ne s'agit pas d'une évaluation du risque. [Description Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM).

## Reproduction et provenance

Les scripts `urumea_prepare_data.py`, `urumea_linkedin_capture.py`,
`urumea_verify_take.py`, `urumea_linkedin_voice.py` et `urumea_linkedin_render.py` utilisent le dossier de
travail monté sous `/w`, comme les autres scripts vidéo headless du dépôt.
Le script de capture s'appuie sur `site_videos.py`, placé dans `/w/scripts/`.
Les données préparées, le plugin extrait et un profil de tournage configuré
doivent être présents avant de lancer la prise. Les identifiants restent dans le
profil local isolé ; ce profil ne fait pas partie des médias livrés.

La prise définitive est
`/tmp/fm-urumea-linkedin-513/out/take03/urumea`. Les données complètes préparées
et les exports restent sous `/tmp/fm-urumea-linkedin-513/data` et dans `exports/`
de cette prise. Le gros brut, les images, les pistes et les vidéos restent locaux,
ignorés par git selon la convention du dépôt.

```sh
# Depuis l'image fm-video avec le dossier de travail monté sous /w :
python3 /w/scripts/urumea_verify_take.py --take /w/out/take03/urumea
python3 /w/scripts/urumea_linkedin_render.py --take /w/out/take03/urumea
```

Le profil de la prise expose les outils et utilise Agir/autonome ; la vidéo ne
prétend pas montrer les réglages par défaut ni le mode Proposer. Une première
prise a été interrompue ; une seconde a servi à vérifier le comportement avant
de reprendre les confirmations de favori pour la prise définitive. Le paquet du
plugin est resté intact pendant ces essais. Les messages rédigés par le modèle
ne sont pas employés comme preuve de la portée d'un favori.

Le calcul de desserte piétonne, le partage sur un autre poste et l'embarquement
du projet dans un GeoPackage ne sont pas montrés ni revendiqués dans ce film.
