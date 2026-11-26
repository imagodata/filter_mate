# San Sebastián solaire — storyboard prêt pour répétition, 53 s

État : aucun tournage solaire retrouvé. Acquisition et calculs non exécutés ;
prises agent après stabilisation des lots 1 à 3. Les prompts de
[requests.json](requests.json) préparent une exécution manuelle : le lanceur ne
possède pas encore de scène `solar`.

Sujet : tri géographique illustratif de prairies OSM. Copernicus GLO-30 est un
**modèle de surface** incluant végétation et constructions, pas un MNT de sol nu.
La pente dérivée est celle de ce modèle ; elle ne démontre ni potentiel énergétique,
ni aptitude d'une parcelle, ni coût de raccordement. [Source Copernicus](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM).

| Plan | Durée | Interaction et légende FR / EN | Contrôle avant prise |
|---|---:|---|---|
| S1 | 8 s | Apporter prairies, habitations, routes, lignes électriques, DSM. « OSM et surface 30 m. » / “OSM and a 30 m surface model.” | Emprise/date/sources figées, couches valides et visibles. |
| S2 | 8 s | Reprojeter en EPSG:32630, calculer pente en **%**, moyenne zonale par prairie. « Pente du modèle, moyenne par prairie. » / “Model slope, mean per meadow.” | `gdal:slope` avec `AS_PERCENT=true`, ou conversion explicite degrés → %. 10 % ≈ 5,71°, pas 10°. NoData et champ/unités contrôlés. |
| S3 | 7 s | Exporter les vecteurs en GPKG, rasters séparés, projet QGZ explicite. « Exporter puis rouvrir. » / “Export, then reopen.” | Réouverture ; ne pas annoncer de projet embarqué sans preuve. |
| S4 | 7 s | Moyenne de pente <10 %, voisinage 300 m. « Seuils illustratifs, trois cibles. » / “Illustrative thresholds, three targets.” | Pente et distances exactes ; trois cibles = habitations, routes et lignes. Proximité d'une ligne ne signifie pas raccordabilité. |
| S5 | 7 s | Desserte sur réseau, mode/vitesse/durée affichés. « Desserte sur le réseau enregistré. » / “Service area on the recorded network.” | Algorithme, réseau, origines et temps archivés ; pas de tampon présenté comme isochrone. |
| S6 | 8 s | Enregistrer, dérégler puis rejouer le favori. « Favori enregistré puis rejoué. » / “Favorite saved, then replayed.” | Filtre actif, succès, mêmes comptes après rejeu ; second projet pour annoncer le partage. |
| S7 | 8 s | Carte finale des résultats de la prise. « Tri illustratif, modèle de surface 30 m. » / “Illustrative screening, 30 m surface model.” | Comptes réellement obtenus, limites et crédits ; aucun chiffre d'Urumea réutilisé. |

Voix FR de travail : « Des prairies et leur voisinage depuis OSM. On calcule la
pente du modèle de surface, en pourcentage, puis sa moyenne par prairie. On exporte
les résultats et on vérifie leur réouverture. Moins de dix pour cent : un seuil
illustratif. Les routes et lignes voisines sont montrées dans trois couches cibles.
La desserte se calcule sur le réseau enregistré. Le favori est enregistré puis
rejoué. Ce premier tri ne constitue pas une étude de faisabilité solaire. »

Mode Act/autonome si les réglages Urumea sont réutilisés ; Plan exige une prise
spécifique. Fournisseur distant = ne pas annoncer que tout reste sur le poste.
Crédits : © OpenStreetMap contributors (ODbL), Copernicus DEM.
