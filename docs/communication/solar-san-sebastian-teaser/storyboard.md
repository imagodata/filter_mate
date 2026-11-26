# Teaser solaire San Sebastián — storyboard 53 s, 7 prises (previz, rien tourné)

Scénario : premier tri (« screening », pas « study ») de sites pour une centrale solaire autour de
San Sebastián / Donostia. Relief 30 m → tri grossier seulement.
Données : prairies, habitations, routes, lignes électriques (OpenStreetMap) ; relief Copernicus 30 m.
Projet partagé : GeoPackage de l'export dans un dossier commun (même projet d'un bout à l'autre).
Modèle : clé d'API du spectateur (pas de modèle local dans le teaser ; la mention
« nothing leaves your computer » reste dans l'article, hors teaser). Undo sorti faute de place.

Tranche filtrée : une seule, prairies à moins de 10 % de pente. Isochrones calculés via
Processing (QNEAT3 / outils natifs) autour de cette tranche. Un favori :
« Solar <10%: isochrones, access, grid ».

| Prise | Temps | Image / interaction | Légende EN | Légende FR |
|---|---|---|---|---|
| 1 Apporter | 0:00–0:08 | Projet vide, mode Plan, une phrase. L'agent apporte prairies, habitations, routes, lignes (OSM) + relief Copernicus. | “One sentence. Meadows, homes, roads, grid, terrain.” | « Une phrase. Prairies, maisons, routes, réseau, relief. » |
| 2 Transformer | 0:08–0:16 | L'agent calcule la pente (Processing), puis la pente moyenne par prairie (statistiques zonales). Les prairies se colorent par pente. | “Slope, then mean slope per meadow.” | « La pente, puis la pente moyenne par prairie. » |
| 3 Exporter | 0:16–0:23 | Fichiers temporaires, perdus à la fermeture. Export GeoPackage avec projet embarqué, panneau face à agent. | “Temporary files don't survive. Export keeps all.” | « Le temporaire ne survit pas. L'export garde tout. » |
| 4 Filtrer | 0:23–0:30 | Prairies à moins de 10 % : la sélection. À 300 m autour : habitations, routes, lignes. Panneau face à agent. | “Under 10% slope. Neighbours, access, grid within 300 m.” | « Moins de 10 % de pente. Voisins, accès, réseau à 300 m. » |
| 5 Isochrones | 0:30–0:37 | L'agent calcule les isochrones (Processing QNEAT3/natif) autour de la tranche <10 % : l'accès réel, pas le cercle. | “Isochrones around the <10% tranche: real access.” | « Isochrones autour de la tranche <10 % : l'accès réel. » |
| 6 Partager | 0:37–0:45 | Le filtre devient le favori « Solar <10%: isochrones, access, grid ». Un collègue le rejoue en un clic ; curseur de pente sous le fil. | “One favorite. Replayed in one click.” | « Un favori. Rejoué en un clic. » |
| 7 Carte fin | 0:45–0:53 | 3 raisons : la règle d'équipe, 3 couches d'un coup (riverains, accès, raccordement), rejouable quand les données changent. Limite 30 m. | “Same rule, three layers, replayable. Screening at 30 m.” | « Même règle, trois couches, rejouable. Tri à 30 m. » |

## Règles tenues
- « screening », jamais « study » (relief 30 m = premier tri).
- L'agent tourne avec la clé d'API du spectateur ; rien sur le local dans le teaser.
- Comptes et emprises = ceux de la prise (exemple, pas de promesse générale).
- Crédits à l'écran : © OpenStreetMap contributors (ODbL), Copernicus DEM.
