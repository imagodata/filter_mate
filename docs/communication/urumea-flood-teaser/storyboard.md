# Urumea — storyboard réconcilié, 53 s à monter

État au 26/11/2026 : répétition réelle existante, **non validée comme teaser final**.
Les nouveaux plans agent attendent les lots 1 à 3 stabilisés. Les 53 s sont une cible
éditoriale ; les attentes seront accélérées et les coupes calées sur les prises réelles.

Le sujet est une démonstration de tri géographique avec des seuils illustratifs.
Copernicus GLO-30 est un **modèle de surface (MNS/DSM)** : bâtiments et végétation
sont inclus. Une moyenne sur l'emprise d'un bâtiment n'est ni son altitude au sol,
ni sa hauteur, ni une hauteur d'eau. Ne pas présenter ces résultats comme des
bâtiments inondés, un calcul de risque ou des itinéraires d'évacuation sûrs.
Référence : [description officielle Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM).

| Plan | Durée | Action prévue et légende FR / EN | Preuve requise avant validation |
|---|---:|---|---|
| U1 — Sources | 8 s | Apporter bâtiments, routes piétonnes, ponts, Urumea et DSM. « OSM et modèle de surface 30 m. » / “OSM and a 30 m surface model.” | Couches valides, emprise commune, carte visible, sources/date/SCR archivés. La répétition ne comprend que les grands axes : les rues locales et chemins sont à acquérir. |
| U2 — Transformer | 8 s | Statistiques zonales sur les emprises. « Moyenne du DEM par emprise. » / “Mean DEM elevation per footprint.” | Algorithme et paramètres, champ de moyenne, NoData, nombres de valeurs valides et style vérifiés. Le champ `alt_mean` existe dans l'export de répétition ; son calcul n'est pas certifié par ce seul constat. |
| U3 — Pérenniser | 7 s | Exporter les vecteurs dans un GPKG et le DSM séparément. « Vérifier les fichiers exportés. » / “Inspect the exported files.” | Réouverture des fichiers sur un projet neuf. Un `.qgz` doit être sauvegardé explicitement si nécessaire ; **aucun projet embarqué n'est démontré**. |
| U4 — Filtrer | 7 s | Moyenne DEM <5 m, à 200 m de l'Urumea ; routes/ponts à 300 m des emprises retenues. « Seuils illustratifs, filtre actif. » / “Illustrative thresholds, active filter.” | SCR métrique EPSG:32630, source et distances exactes, filtre FilterMate actif, comptes et géométries contrôlés. Un simple sous-ensemble QGIS ne prouve pas l'existence d'un favori. |
| U5 — Accès | 7 s | Aire de desserte piétonne 10 min, vitesse explicitée. « Desserte sur le réseau enregistré. » / “Service area on the recorded network.” | Algorithme réellement utilisé, origines, coût/temps/vitesse, réseau marchable et exclusions archivés. Pas de tampon présenté comme isochrone ; pas de promesse d'évacuation. Si seul un réseau de lignes est produit, le montrer comme tel. |
| U6 — Favori | 8 s | Enregistrer **puis réappliquer** le favori. « Favori enregistré, puis rejoué. » / “Favorite saved, then replayed.” | Succès d'enregistrement, modification volontaire de l'état, rejeu visible, mêmes comptes. Le partage avec un collègue exige un second projet/poste et le test de liaison du lot 1. |
| U7 — Fin | 8 s | Carte de synthèse de la prise. « Tri illustratif sur un modèle de surface 30 m. » / “Illustrative screening on a 30 m surface model.” | Chiffres de la prise uniquement ; crédits. La présentation HTML actuelle est une maquette avec chiffres fictifs, distincte d'une sortie de l'agent. |

Dans la répétition, l'agent est en **Act/autonome**, pas en Plan. Ne pas annoncer
« une phrase en mode Plan » sur ces images. Les six requêtes sont visibles ;
l'acquisition n'est pas un calcul instantané. La configuration automatisée
préautorise trois outils réseau/Processing et doit être mentionnée dans la fiche de prise.

Les intitulés historiques du favori et des couches peuvent contenir « evacuation » :
ce sont des noms de travail, pas une qualification du résultat.
Voir [audit des affirmations](../lot5/claims.json) et [fiche de tournage](fiche-prise-agent.md).
