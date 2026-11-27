# Mise en œuvre de l’audit

Les observations du rapport décrivent les reproductions initiales. Ce suivi distingue les corrections livrées
des propositions encore à réaliser.

| Point | État | Résultat |
| --- | --- | --- |
| R01 — mode d’un message ajouté en cours d’exécution | Corrigé | Un message d’un autre mode rejoint la file avec son mode propre. |
| R03 — capture obligatoire pour l’annulation | Corrigé | Une capture impossible bloque l’action et restaure l’état du checkpoint. |
| R04/R05 — zoom sur points | Corrigé | Les points, y compris `(0, 0)`, gardent une marge exprimée en pixels. |
| R06 — zoom tardif | Corrigé | Une navigation manuelle invalide la réponse asynchrone, même après un aller-retour. |
| R07 — union mixte | Corrigé | Le calcul conserve les emprises raster avec les vecteurs. |
| R09 — banc hors ligne | Corrigé | Les outils désactivés sont exclus et les scénarios concernés explicitement ignorés. |
| R10 — dépendance MCP facultative | Corrigé | Le test d’API est ignoré lorsque MCP manque. |
| Choix intelligent du SCR | Implémenté | Domaine d’utilisation vérifié, diagnostic du SCR actuel, recommandation conserver/changer, distinction affichage/analyse. |
| R02/R08 — budget mémoire et persistance | À réaliser | Conserver la distinction entre données actives et données retenues pour annuler. |
| F01 — conversations dans l’historique | À réaliser | Plusieurs conversations et réouverture, sans rejouer leurs outils. |
| A01 — lectures de sélection et flash | À réaliser | Déplacer les lectures potentiellement lentes hors du fil d’interface. |
| Transitions animées et pilotage étendu de QGIS | À réaliser | Les correctifs de zoom ne constituent pas encore une animation commune. |

## Vérification du choix du SCR

Les tests couvrent le SCR déjà adapté, Web Mercator pour les surfaces, un SCR hors de son domaine, les limites
de fuseaux UTM, les pôles et l’antiméridien. Le moteur consulte la base locale QGIS/PROJ ; les rectangles des
domaines restent approximatifs et ne constituent pas une garantie de précision ni une frontière administrative.
Le skill recommande sans modifier le projet lorsque la demande porte sur un conseil.

Références techniques : [SCR des projets et couches dans QGIS](https://docs.qgis.org/3.44/en/docs/user_manual/working_with_projections/working_with_projections.html),
[domaines fournis par QgsCoordinateReferenceSystem](https://api.qgis.org/api/classQgsCoordinateReferenceSystem.html),
[projection UTM dans PROJ](https://proj.org/en/stable/operations/projections/utm.html).

## Vérifications effectuées

- Navigation : 162 tests unitaires et scénario réel sur QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6.
- SCR et skills : 137 tests unitaires ciblés ; scénarios réels QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6 :
  22 contrôles réussis chacun. Banc hors ligne : 171 scénarios réussis, 4 ignorés pour outils désactivés.
- Les autres résultats sont consignés dans les commits correspondants ; ces contrôles ciblés ne signifient pas
  que toute la suite du dépôt a été exécutée.
