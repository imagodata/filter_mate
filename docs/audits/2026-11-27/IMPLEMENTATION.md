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
| R02 — budget des sorties Processing | Corrigé pour les fichiers gérés | Précontrôle, surveillance, annulation coopérative et rejet des résultats trop volumineux avant leur ajout. |
| R08 — message trompeur après sauvegarde | Corrigé | Le message indique que l’annulation retient les données et que sauvegarder seul ne les libère pas. |
| F01 — conversations dans l’historique | Implémenté | Onglet Conversations, reprise dans le projet d’origine, consultation des autres projets, migration des anciens échanges. |
| A01 — lectures de sélection et flash | Implémenté | Lectures sur snapshots en arrière-plan, attente annulable et résultat invalidé par une sélection manuelle. |
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

## Conversations conservées et rouvertes

« Nouvelle conversation » archive les échanges et le contexte compatible du modèle. L’onglet Conversations
permet de les rouvrir dans leur projet d’origine ; une conversation d’un autre projet s’affiche dans une fenêtre
de consultation, sans changer de projet ni transmettre son contenu à la conversation active. Aucun outil passé
n’est relancé. Les permissions sont oubliées lors d’un changement de conversation et la compatibilité du serveur,
du compte, du modèle et du partage des valeurs reste vérifiée avant reprise du contexte.

L’archive SQLite réside dans le profil QGIS (`filter_mate/agent-conversations.sqlite3`) et ne modifie pas le projet.
Elle conserve les 200 conversations les plus récentes contenant une demande. Les limites existantes du transcript
(60 000 caractères) et de la session modèle (250 000 caractères) continuent de s’appliquer. Les anciens emplacements
par projet sont importés une fois. « Enregistrer sous » conserve l’identité de la conversation ; les projets jamais
enregistrés ont des identités distinctes. Après redémarrage, leurs échanges restent consultables dans l’historique.

La création d’une conversation est refusée si son archivage échoue, afin de conserver les échanges affichés.
Les contrôles couvrent aussi le signal de changement de nom pendant l’ouverture d’un projet, qui doit retrouver
son archive et non la remplacer par celle du projet vide intermédiaire.

Validation : 1 141 tests des contrôleurs et de l’historique passent ; le scénario natif passe sur QGIS 3.44 / Qt 5
et QGIS 4.3 / Qt 6, y compris la migration et la conservation d’un projet non modifié.

## Budget des résultats natifs

Les écritures natives OGR/GDAL qui ne passent pas par le téléchargement contrôlé ont désormais un précontrôle
de capacité et une surveillance du stockage virtuel toutes les 50 ms. L’annulation est demandée dans le fil
d’interface de QGIS. Un contrôle final empêche d’ajouter un résultat dépassant le budget ; l’échec ou l’annulation
supprime uniquement ses nouveaux fichiers et fichiers annexes. Les données antérieures et celles nécessaires
à l’annulation restent disponibles. Une fermeture de projet attend que les écrivains natifs aient terminé avant
de supprimer leurs fichiers virtuels.

Ce budget porte sur les fichiers gérés dans `/vsimem`, pas sur toute la mémoire du processus QGIS. Un fournisseur
peut allouer de la mémoire entre deux contrôles ou ignorer une annulation : cette protection ne constitue pas un
plafond matériel de RAM. Les intermédiaires `memory:` de certains modèles restent également hors de ce comptage.
La sauvegarde conserve volontairement les originaux nécessaires à l’annulation ; le message conseille une emprise
plus petite ou la sauvegarde puis la réouverture du projet, sans promettre que sauvegarder libère immédiatement la RAM.

Validation : 78 tests unitaires ; scénarios natifs de dépassement sur QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6,
stockage/persistance et modèles Processing sur QGIS 3.44. Le budget d’un octet bloque le lancement,
un résultat trop grand est refusé sans ajout de couche,
et un budget suffisant conserve le fonctionnement normal.

## Sélection et surbrillance sans lecture bloquante

La sélection et la surbrillance lisent un snapshot de la couche dans une tâche QGIS. L’API reste synchrone, mais
sa boucle d’attente traite les événements de l’interface. Stop, un délai de 30 secondes, un changement de source
ou de sélection invalident le résultat ; aucune sélection partielle n’est appliquée. La sélection est limitée à
200 000 identifiants correspondants, avec refus explicite au-delà plutôt qu’un résultat tronqué.

La surbrillance transmet des copies de géométries à `flashGeometries` : `flashFeatureIds` effectuerait une seconde
lecture du fournisseur dans le fil d’interface. L’itérateur du snapshot garde les protections existantes sur les
expressions et champs virtuels. Comme pour les autres lectures, la fin effective d’un accès réseau dépend de la
coopération du fournisseur ; son résultat tardif ne modifie pas la sélection.

Validation : 452 tests de l’API et des tâches de lecture ; scénario natif QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6
avec une lecture volontairement ralentie, un compteur d’événements d’interface, une sélection manuelle et un délai
court. La lecture directe de la couche est remplacée par un refus dans ce scénario pour vérifier l’usage du snapshot.
