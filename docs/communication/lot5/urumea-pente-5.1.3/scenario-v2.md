# Proposition de scénario — Urumea, une question géographique et un résultat

Proposition non tournée. L'habillage retenu est conservé : frame logo, Tony
uniquement pour « Imagodata présente… FilterMate », Benjamin pour la
démonstration. Sous le titre : « Le meilleur compagnon pour QGIS », puis
« Un exemple d’analyse de l’Urumea — Saint-Sébastien ».

## Angle recommandé : préparer un diagnostic à partir du zonage officiel

Question : **quels bâtiments du secteur étudié intersectent une zone inondable
cartographiée autour de l'Urumea ?**

Le tampon de 500 m délimite le secteur de travail. La pente d'un véritable MNT
aide à lire le relief. La sélection des bâtiments du zonage repose sur une
intersection avec la cartographie officielle, dont le millésime et le scénario
seront affichés. La pente et la proximité ne définissent pas un aléa de crue.

| Temps visé | Carte et action | Proposition de narration |
|---|---|---|
| 0–6 s | Frame logo et textes validés | Tony : « Imagodata présente… FilterMate. » |
| 6–15 s | Urumea, quartiers et bâtiments ; cadrage stable | « À Saint-Sébastien, quels bâtiments se trouvent dans les zones inondables cartographiées autour de l'Urumea ? » |
| 15–30 s | Couloir de 500 m, puis bâtiments du secteur | « Je commence par délimiter notre secteur : cinq cents mètres autour de la rivière. » |
| 30–50 s | MNT officiel, calcul de pente, lecture des versants et de la vallée | « Le modèle du terrain nous permet de lire la pente et de mieux comprendre le relief de la vallée. » |
| 50–72 s | Zonage URA choisi et sourcé ; intersection avec les bâtiments | « Je croise maintenant les bâtiments avec le zonage inondable officiel. La sélection apparaît sur la carte. » |
| 72–88 s | Routes et objets ponts à 300 m des bâtiments retenus | « J'associe les routes et les ponts proches de ces bâtiments pour préparer la suite de l'étude. » |
| 88–105 s | Export réel, résultat lisible, source et millésime | « On obtient un jeu de données ciblé, prêt à être exporté et approfondi dans QGIS. » |

Une seule intention par plan, avec 4 à 6 secondes de résultat stable. Les
compteurs apparaissent après les actions. Les attentes coupées sont indiquées.
Les données déjà préparées sont présentées comme telles ; aucune acquisition
automatique de MNT ou de zonage n'est promise sans prise le démontrant.

## Sources à préparer

- Un **MNT**, par exemple le MDT de GeoEuskadi et son dérivé 5 m. Le Gouvernement
  basque distingue le MDT (terrain sans bâtiments, ponts ni végétation), le MDS
  (surface) et le MDEH (hydrologie). [Catalogue officiel](https://www.euskadi.eus/informacion/productos-de-cartografia-basica-y-ortofotos/web01-a3lurme0/es/).
- Une couche d'inondabilité **URA**, par exemple T100 pour un scénario unique et
  lisible. Le catalogue officiel propose les zonages T10, T100 et T500.
  [Catalogue officiel](https://www.euskadi.eus/cartografia-de-inundabilidad-de-la-capv/web01-a2lurhiz/es/).
- Les bâtiments, routes et objets ponts OSM déjà préparés, avec attribution.

Avant les nouvelles prises, vérifier le millésime, la couverture exacte de
l'emprise, les droits et attributions, les projections et le contenu du zonage.
Recalculer les nombres avec ces nouvelles données. Le chiffre 1 079 du montage
MNS n'est pas transférable à ce scénario.

Le film dira « intersecte le zonage cartographié », sans annoncer qu'un bâtiment
sera inondé ni qu'un bâtiment hors zonage est protégé. Il ne simule pas de crue,
ne calcule pas de hauteur d'eau et ne propose pas de chemin d'évacuation.

## Variante plus légère : présélection terrain/proximité

Si l'on souhaite se concentrer sur les filtres de FilterMate sans couche
d'inondabilité supplémentaire : « Quels bâtiments retenir pour une première
étude autour de l'Urumea ? » Le déroulé devient tampon 500 m, pente d'un MNT,
moyenne du terrain par emprise, seuil illustratif <10 %, réseau proche, export.
Ce serait explicitement une présélection géographique, sans qualification
d'exposition aux crues. Le seuil et les comptes doivent être validés sur le MNT.

Le favori sera réintégré après correction et validation du cas de collision de
signature observé dans la prise technique ; il n'est pas une promesse de cette
proposition.
