# Urumea — narration et montage de travail

Le storyboard réconcilié fait foi. Aucune des phrases conditionnelles ci-dessous
ne devient une affirmation validée avant le contrôle de sa prise.

| Plan | Voix FR proposée | Voice EN |
|---|---|---|
| U1 | « L'agent apporte les couches OSM et le modèle de surface à trente mètres. » | “The agent brings in OSM layers and a thirty metre surface model.” |
| U2 | « Il calcule la moyenne du DEM sur chaque emprise de bâtiment. » | “It computes mean DEM elevation over each building footprint.” |
| U3 | « Les vecteurs sont exportés en GeoPackage, le relief dans un fichier séparé. Vérifions leur réouverture. » | “Vectors go to a GeoPackage, elevation to a separate file. Check that both reopen.” |
| U4 | « Moins de cinq mètres dans le DEM, près de la rivière : des seuils illustratifs pour filtrer plusieurs couches. » | “Below five metres in the DEM, near the river: illustrative thresholds for filtering several layers.” |
| U5 | « Le réseau enregistré sert à calculer une desserte piétonne de dix minutes, à vitesse fixée. » | “The recorded network supports a ten minute walking service area at a stated speed.” |
| U6 | « On enregistre le favori, puis on le rejoue et on compare les résultats. » | “Save the favorite, replay it, and compare the results.” |
| U7 | « Un premier tri sur un modèle de surface. Les seuils ne décrivent ni une crue ni un trajet sûr. » | “A first screening on a surface model. These thresholds describe neither a flood nor a safe route.” |

La durée de voix est à mesurer ; aucune piste audio finale n'est livrée pour Urumea.
Les durées 8/8/7/7/7/8/8 s totalisent 53 s, mais ne sont pas des repères du brut.

Répétition retrouvée : `/tmp/fm-video/out/urumea/` (209,2441 s, 3 153 images).
Repères bruts des fins de requête : 47,610 / 69,376 / 89,826 / 125,563 /
181,119 / 204,664 s, d'après les événements `speed` et `camera` de `meta.json`.
Ne pas découper automatiquement à 8/16/23/30/37 s. La répétition reste non validée :
carte blanche sur les images examinées, export incomplet par rapport au scénario,
favori d’abord refusé puis sauvegardé partiellement pour une seule couche.
Aucun rejeu complet n’est montré. Ses légendes anciennes ne sont pas des preuves.

`animatique.html` est une prévisualisation textuelle hors ligne, pas une capture de QGIS.
`presentation.html` est une carte finale illustrative imprimable depuis le navigateur ;
son PDF ne doit pas être présenté comme un export de mise en page par l'agent.
La mention de l'ancien MP4 previz 53 s n'est pas une livraison : ce fichier n'a pas
été retrouvé dans les sources inspectées et son script temporaire n'est pas disponible.

Après validation des vrais plans, relever les entrées/sorties dans une liste de
montage séparée et employer `scripts/teaser_compose.py`. Ne pas remplacer ses
segments existants tant qu'Urumea n'a pas de prise validée.
