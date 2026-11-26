# Teaser crue de l'Urumea — storyboard 53 s, 7 prises (previz, rien tourné)

Scénario : premier tri (« screening », pas « study ») des bâtiments exposés à la crue autour de
l'Urumea à San Sebastián / Donostia. Relief 30 m → tri grossier seulement.
Données : bâtiments, routes, ponts, rivière Urumea (OpenStreetMap) ; relief Copernicus 30 m.
Projet partagé : GeoPackage de l'export dans un dossier commun (même projet d'un bout à l'autre).
Modèle : token API Claude du spectateur, modèle Haiku (pas de modèle local dans le teaser ;
la mention « nothing leaves your computer » reste dans l'article, hors teaser).
Undo sorti faute de place.

Tranche filtrée : une seule, bâtiments sous 5 m d'altitude (seuil illustratif, pas une norme)
à moins de 200 m de la rivière (illustratif). Isochrones d'évacuation à pied calculés via
Processing (QNEAT3 / outils natifs) autour des bâtiments exposés. Un favori :
« Flood <5 m: evacuation, access, bridges ».

| Prise | Temps | Image / interaction | Légende EN | Légende FR |
|---|---|---|---|---|
| 1 Apporter | 0:00–0:08 | Projet vide, mode Plan, une phrase. L'agent apporte bâtiments, routes, ponts, rivière (OSM) + relief Copernicus. | “One sentence. Buildings, roads, bridges, river, terrain.” | « Une phrase. Bâtiments, routes, ponts, rivière, relief. » |
| 2 Transformer | 0:08–0:16 | L'agent calcule altitude et pente (Processing), puis l'altitude moyenne par bâtiment (statistiques zonales). Les bâtiments se colorent par exposition. | “Height, then mean height per building.” | « L'altitude, puis l'altitude moyenne par bâtiment. » |
| 3 Exporter | 0:16–0:23 | Fichiers temporaires, perdus à la fermeture. Export GeoPackage avec projet embarqué, panneau face à agent. | “Temporary files don't survive. Export keeps all.” | « Le temporaire ne survit pas. L'export garde tout. » |
| 4 Filtrer | 0:23–0:30 | Bâtiments sous 5 m près de la rivière : la sélection. Routes et ponts autour à 300 m. Panneau face à agent. | “Under 5 m by the river. Roads and bridges within 300 m.” | « Moins de 5 m près de la rivière. Routes et ponts à 300 m. » |
| 5 Isochrones | 0:30–0:37 | L'agent calcule les isochrones d'évacuation à pied (Processing QNEAT3/natif) autour des bâtiments exposés. | “Foot-evacuation isochrones around exposed buildings.” | « Isochrones d'évacuation à pied autour des bâtiments exposés. » |
| 6 Partager | 0:37–0:45 | Le filtre devient le favori « Flood <5 m: evacuation, access, bridges ». Un collègue le rejoue en un clic ; curseur d'altitude sous le fil. | “One favorite. Replayed in one click.” | « Un favori. Rejoué en un clic. » |
| 7 Carte fin | 0:45–0:53 | Fin sur la présentation D3 (`presentation.html`) : 3 raisons (règle d'équipe, 3 couches, rejouable), limite 30 m. Bouton Exporter PDF (A4 paysage). | “Same rule, three layers, replayable. Screening at 30 m.” | « Même règle, trois couches, rejouable. Tri à 30 m. » |

## Règles tenues
- « screening », jamais « study » (relief 30 m = premier tri).
- Seuils 5 m / 200 m / 300 m dits illustratifs, pas des normes (même discipline que le 18 % de Katmandou).
- L'agent tourne avec le token API Claude du spectateur, modèle Haiku ; rien sur le local dans le teaser.
- Comptes et emprises = ceux de la prise (exemple, pas de promesse générale).
- Crédits à l'écran : © OpenStreetMap contributors (ODbL), Copernicus DEM.
- Ne pas présenter comme une évaluation du risque ni une consigne d'évacuation.
