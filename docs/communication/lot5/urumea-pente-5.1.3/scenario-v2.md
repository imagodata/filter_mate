# Proposition de scénario — Urumea, une question géographique et un résultat

Proposition non tournée. L'habillage retenu est conservé : frame logo, Tony
uniquement pour « Imagodata présente… FilterMate », Benjamin pour la
démonstration. Sous le titre : « Le meilleur compagnon pour QGIS », puis
« Un exemple d’analyse de l’Urumea — Saint-Sébastien ».

## Angle recommandé : préparer un diagnostic à partir du zonage officiel

Question : **quels bâtiments du secteur étudié intersectent une zone inondable
cartographiée autour de l'Urumea ?**

La démonstration met en avant le **moteur de filtrage et les exports de
FilterMate**. Elle commence dans un **projet QGIS vide**, sans couche chargée.
L'agent acquiert les données à partir des prompts, puis propose d'enregistrer
le travail. Les panneaux natifs FILTERING et EXPORTING, les paramètres et les
résultats sont montrés à l'écran. Le fil est « partir de zéro → acquérir les
couches → conserver le projet → croiser les filtres → produire un livrable ».

Le tampon de 500 m délimite le secteur de travail. La pente d'un véritable MNT
aide à lire le relief. La sélection des bâtiments du zonage repose sur une
intersection avec la cartographie officielle, dont le millésime et le scénario
seront affichés. La pente et la proximité ne définissent pas un aléa de crue.

| Temps visé | Carte et action | Proposition de narration |
|---|---|---|
| 0–6 s | Frame logo et textes validés | Tony : « Imagodata présente… FilterMate. » |
| 6–13 s | Projet vide, liste des couches vide ; premier prompt lisible dans l'agent | « On part d'un projet vide. Je demande à FilterMate de préparer les données de l'Urumea à Saint-Sébastien. » |
| 13–36 s | Prompts d'acquisition, sources identifiées, arrivée des couches OSM, MNT et zonage URA | « L'agent acquiert les données du secteur depuis les sources choisies. Les couches apparaissent dans QGIS. » |
| 36–50 s | Carte « Conserver ce travail ? », clic sur « Enregistrer le projet et les couches… », choix du QGZ et lien vers les données | « FilterMate me propose de conserver ce travail. J'enregistre le projet avec ses données avant de poursuivre. » |
| 50–67 s | Panneau FILTERING : source Urumea, cible Bâtiments, tampon 500 m ; résultat cartographique | « Avec le moteur de FilterMate, je garde les bâtiments dans un couloir de cinq cents mètres autour de la rivière. » |
| 67–83 s | MNT officiel, calcul de pente, lecture des versants et de la vallée | « Le modèle du terrain nous permet de lire la pente et de mieux comprendre le relief de la vallée. » |
| 83–104 s | Panneau FILTERING : intersection avec le zonage URA, combinaison ET avec le filtre de 500 m ; compteurs réels | « Je combine ce premier filtre avec le zonage inondable officiel. FilterMate croise les critères et actualise les couches. » |
| 104–120 s | Source Bâtiments retenus ; cibles Routes et Ponts ; tampon 300 m, puis résultat sur les couches | « La sélection sert maintenant à filtrer les routes et les ponts environnants. » |
| 120–134 s | Génération de deux graphiques D3.js depuis les résultats contrôlés | « Je résume le résultat avec des graphiques calculés sur les données de l'étude. » |
| 134–154 s | Composeur QGIS visible : carte, graphiques, indicateurs, légende et sources ; pause sur la mise en page | « J'assemble la carte et les graphiques dans une composition prête à partager. » |
| 154–167 s | Panneau EXPORTING, export des couches filtrées, puis PDF de la composition réellement ouvert | « J'exporte les couches retenues et la synthèse cartographique en PDF. » |
| 167–180 s | Enregistrement final du projet et de ses données ; réouverture du projet livré | « Le projet conserve les sources et leurs filtres, les styles et la mise en page pour reprendre l'analyse. » |

Une seule intention par plan, avec 4 à 6 secondes de résultat stable. Les
compteurs apparaissent après les actions. Les attentes coupées sont indiquées.
La configuration de l'agent, les sources autorisées et les URL officielles
peuvent être préparées avant le tournage. Le projet et sa liste de couches
restent réellement vides au départ. Les fichiers sources doivent être acquis
par les outils de l'agent pendant la prise ; aucun chargement caché de couches
préparées ne remplace cette acquisition. Les attentes réseau peuvent être
coupées avec une indication visible, en conservant le prompt, l'acquisition et
l'arrivée des couches comme preuves.

La durée visée devient **environ 3 minutes** pour conserver un rythme lisible
avec l'acquisition, la sauvegarde proposée et la restitution finale.
Les voix restent Tony pour l'intro seule et Benjamin
pour l'ensemble de la démonstration, y compris cette nouvelle fin.

## Acquisition depuis zéro et sauvegarde proposée par le mode Agent

Prompts de départ proposés, à adapter aux ressources officielles effectivement
accessibles dans les sources configurées :

1. « Localise l'Urumea à Donostia / Saint-Sébastien, en Espagne, et prépare le
   secteur d'étude dans un système de coordonnées métrique. »
2. « Acquiers les couches OSM du secteur : rivière Urumea, bâtiments, routes et
   ponts. Nomme clairement les couches et conserve leurs sources. »
3. « Charge un véritable MNT officiel du secteur et le zonage inondable URA
   choisi pour cette étude. Indique les sources, millésimes et résolutions. »

Préparer et tester les URL de fichiers ou identifiants de service réels pour le
MNT et le zonage avant la prise. Si un catalogue n'est pas pris en charge par la
recherche du plugin, donner l'URL officielle dans le prompt et montrer cet
apport ; ne pas présenter un catalogue configuré comme une découverte spontanée.
Un WMS/WMTS est une image de contexte, et ne remplace ni le raster d'altitudes
numériques du MNT ni les géométries vectorielles à intersecter. Pour le projet
livré, contrôler les copies locales des données nécessaires.

Le parcours relu dans les implémentations actuelles est celui de
`ui/controllers/agent_data.py`, `adapters/agent/data_store.py` et de la fin de
requête dans `ui/controllers/agent_chat_controller.py` :

- Les données gérées en mémoire déclenchent, à la fin d'une requête, la carte
  **« Conserver ce travail ? »** avec les choix **« Enregistrer le projet et les
  couches… »** et **« Continuer en mémoire »**.
- Accepter ouvre le dialogue natif du projet QGIS. Le choix de dossier puis le
  QGZ et les données réellement écrits doivent être visibles dans la prise.
- Le choix de conservation est indépendant des permissions des outils et de
  l'autonomie de l'agent. Il ne s'agit pas d'une sauvegarde automatique.
- La persistance conserve l'état des couches ; contrôler les styles, filtres
  et sélections, les liens du projet et les fichiers après l'enregistrement.
- Les fournisseurs Processing nécessitant des fichiers, tel GDAL pour la
  pente, ont besoin de cette destination avant le calcul.

La proposition n'apparaît que pour les données gérées encore en mémoire : une
couche distante lue directement sur le serveur ne suffit pas à la déclencher.
L'acquisition OSM et le parcours de conservation doivent donc être testés de
bout en bout. Les nouveaux résultats en mémoire peuvent susciter de nouvelles
propositions ; la sauvegarde finale conserve aussi ces résultats et la composition.

Le nouveau script de tournage devra commencer à enregistrer avant le premier
prompt et laisser apparaître cette carte. Il ne doit pas reprendre le
préenregistrement silencieux utilisé pour débloquer GDAL dans le montage MNS
de travail précédent.

La différence entre les deux livrables est centrale : **l'export de couches
écrit les résultats filtrés**, tandis que **la sauvegarde du projet conserve
les sources complètes avec leur état de filtrage**, pour poursuivre le travail.
Le détail de l'implémentation relue est dans [agent-save-flow.md](agent-save-flow.md).

## Cadrage : interface complète et zooms de lecture

- Pendant la démonstration, conserver la fenêtre QGIS complète et le panneau
  FilterMate visibles : menus, couches, carte, boutons et panneaux natifs.
- Montrer les prompts puis le panneau correspondant à l'action. Ne pas laisser
  toute la démonstration dans le seul fil de conversation de l'agent.
- Ajouter des loupes ponctuelles de 2 à 4 secondes sur le prompt envoyé, les
  paramètres source/cibles/prédicat/tampon, les compteurs et changements de
  carte, les graphiques, les options d'export et les fichiers réellement créés.
- Garder la vue d'ensemble en contexte pendant les loupes, puis y revenir.
  Utiliser uniquement des agrandissements des pixels réellement enregistrés.
  Aucune carte recadrée seule en plein écran pendant les plans de démonstration.
- Positionner les fenêtres du composeur et du lecteur PDF sur la zone centrale
  de la carte, en laissant visibles le panneau FilterMate et les menus QGIS.
- Capturer le bureau virtuel isolé pour inclure ces fenêtres réelles : une
  capture du seul widget principal QGIS ne montre pas forcément le composeur.
- Réserver un bandeau extérieur à la fenêtre QGIS pour les sous-titres et
  annotations, afin de garder les contrôles et la barre d'état lisibles.

La frame logo d'introduction reste le plan graphique distinct demandé. Les
captures seules de cartes du montage MNS de travail ne définissent plus le
cadrage de cette nouvelle version.

## Capacités FilterMate à rendre visibles

1. **Moteur de filtre** : source, cibles, prédicat spatial et distance métrique ;
   résultat réel sur les couches et leurs effectifs.
2. **Combinaison de critères** : conserver le couloir de 500 m ET l'intersection
   avec le zonage ; montrer l'opérateur et vérifier les identifiants retenus.
3. **Filtrage croisé multicouche** : les bâtiments retenus deviennent la source
   du filtre sur les routes et les deux représentations des ponts à 300 m.
4. **Moteur d'export** : choisir les couches actuellement filtrées, le format,
   les styles et le dossier dans EXPORTING ; contrôler le fichier réellement
   écrit. `set_export_options` prépare le panneau, sans constituer un export.
5. **Restitution** : composer une page dans QGIS, exporter son PDF, sauvegarder
   le projet avec les données nécessaires et le rouvrir.

Ne pas annoncer un temps de traitement, un volume maximum, un mode distant ou
un projet embarqué dans un GeoPackage sans preuve sur la prise concernée. La
fin doit montrer un export effectif, et pas uniquement un message de succès.

## Graphiques D3.js appropriés

Deux graphiques, accompagnés d'un indicateur du nombre de bâtiments retenus :

- **Barres horizontales — progression des effectifs** : tous les bâtiments du
  périmètre initial, ceux du couloir de 500 m, puis ceux intersectant le zonage
  dans ce couloir. Chaque barre utilise des identifiants bâtiment uniques et
  les comptes observés à l'étape correspondante. Ces populations sont emboîtées,
  pas des catégories à additionner.
- **Histogramme — pente moyenne du terrain sous les bâtiments retenus (%)** :
  calcul zonal sur le MNT, sans utiliser le MNS Copernicus. Afficher le nombre de
  valeurs renseignées et traiter les valeurs manquantes explicitement. Cette
  distribution décrit le relief ; elle ne représente pas une probabilité de crue.

Le chiffre principal et les barres doivent correspondre aux couches exportées.
Les bâtiments, routes et objets ponts ne sont pas additionnés en un même total.
Le pourcentage éventuel a pour dénominateur explicite les bâtiments du secteur
d'étude, et non un total de couches ou un ensemble différent.

Pour filmer réellement du D3.js, utiliser `run_chart_code` en mode expert sous
QGIS 4 avec QtWebEngine, à partir des données effectivement lues. Les graphiques
standards de `show_chart` sont actuellement dessinés en Python ; ils ne seront
pas présentés comme une exécution de D3.js. Le rendu D3 est intégré dans la
composition sous forme de SVG. Le PDF conserve une version statique de ce rendu.

## Mise en page et livrables de fin

Composition **A3 paysage**, fond clair, marges régulières, titre hiérarchisé et
palette cohérente avec les couches. La carte occupe environ deux tiers de la
largeur ; les indicateurs et les deux graphiques forment une colonne à droite.
Légende, échelle, nord, sources, millésimes, projection et date complètent la page.
Le logo reste discret pour laisser la place aux données.
La [maquette de composition](composer-maquette.svg) et le
[plan de placement](composer-plan.json) préparent ce design sans inventer de
résultat géographique ou de valeur statistique.

Livrables à filmer et à rouvrir :

- `urumea_synthese.pdf` : carte et graphiques lisibles, unités, légende et crédits.
- `urumea_resultats.gpkg` : les couches vectorielles retenues et leurs styles
  disponibles ; les rasters sont conservés séparément au format GeoTIFF.
- `urumea_projet.qgz` avec son dossier de données et de ressources : couches,
  filtres, styles, composition et graphiques SVG intégrés. Un ZIP peut regrouper
  ce dossier pour la livraison. L'enregistrement d'un QGZ seul n'est pas une
  preuve que ses données externes sont transportables.

Avant de valider la fin : rouvrir le PDF et le GeoPackage, déplacer une copie du
dossier projet puis rouvrir le QGZ depuis cette copie. Comparer les comptes,
filtres, styles, mise en page et graphiques ; vérifier les chemins relatifs et
l'absence de dépendance aux profils ou aux fichiers temporaires du tournage.
Les graphiques D3 restent affichés comme enregistrés : aucun rafraîchissement
automatique de leur code n'est promis à la réouverture.

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
