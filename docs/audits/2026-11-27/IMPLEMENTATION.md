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
| Transitions de zoom | Implémenté | Transition commune de 220 ms pour l’agent, le filtrage et le chemin principal d’exploration ; annulation par navigation manuelle. |
| Pilotage des fenêtres QGIS et panneaux de plugins | Implémenté dans le chat | Capacités disponibles, tables, propriétés natives, panneaux enregistrés, outils cartographiques et historique de vue. |
| Propositions de sauvegarde | Implémenté | Masquage jusqu’au redémarrage de QGIS ; sauvegarde manuelle toujours disponible. |
| Curseurs du plugin | Implémenté | Intentions cohérentes selon le contrôle, attentes locales et restauration sans toucher aux outils de carte. |
| Éditions de couche par l’agent | Implémenté | Confirmation explicite après la demande avant l’enregistrement dans la source, par couche ou groupe de transaction. |
| Dossier des exports de l’agent | Implémenté | Choix local mémorisé par l’utilisateur, annulation sans export et destinations dans les profils QGIS refusées. |
| Réseau SVG au repos et variantes | Implémenté | Icône persistante, repos statique et 22 états liés aux tâches et interactions. |
| Recherche de datasets et sources désactivées | Implémenté | Skill disponible sans source externe active, catalogue local enrichi et propositions d’activation explicites. |
| Découverte Web et sources personnalisées | Implémenté | Recherche Web optionnelle et bornée, candidats non vérifiés, proposition par formulaire prérempli et ajout confirmé par l’utilisateur. |

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
Si ce contexte est incompatible, le transcript reste consultable mais n’est pas transmis automatiquement sous
forme de récapitulatif à la nouvelle destination.

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
100 000 identifiants correspondants et sélectionnés au total, pour rester dans la capacité de capture de
l’annulation, avec refus explicite au-delà plutôt qu’un résultat tronqué.

La surbrillance transmet des copies de géométries à `flashGeometries` : `flashFeatureIds` effectuerait une seconde
lecture du fournisseur dans le fil d’interface. L’itérateur du snapshot garde les protections existantes sur les
expressions et champs virtuels. Comme pour les autres lectures, la fin effective d’un accès réseau dépend de la
coopération du fournisseur ; son résultat tardif ne modifie pas la sélection.

Validation : 452 tests de l’API et des tâches de lecture ; scénario natif QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6
avec une lecture volontairement ralentie, un compteur d’événements d’interface, une sélection manuelle et un délai
court. La lecture directe de la couche est remplacée par un refus dans ce scénario pour vérifier l’usage du snapshot.

Une lecture de sélection refusée après une intervention manuelle ne doit pas attribuer cette intervention à l’agent.
Le checkpoint reçoit désormais le résultat de l’appel et retire cette sélection de ses effets si elle a changé pendant
un appel refusé. La capture d’une sélection existante dépassant la capacité d’annulation bloque également l’action.
Ces cas passent sur les deux versions de QGIS ; 222 tests du moteur, des checkpoints et du contrôleur passent.

## Transitions de zoom

Le zoom de l’agent, l’union du filtrage et le chemin principal de zoom EXPLORING partagent une interpolation
de centre et d’échelle, avec accélération et ralentissement sur 220 ms et environ 30 images par seconde.
`APP.OPTIONS.EXPLORATION.zoom_transition_ms` règle la durée entre 0 et 600 ms ; 0 supprime l’animation.
Les vues masquées, une échelle verrouillée et les traversées de l’antiméridien gardent le comportement immédiat.

Un clic, une touche, la molette, un déplacement de carte, un changement de SCR ou la fermeture du projet arrêtent
le mouvement. Une nouvelle demande remplace la précédente. L’API attend la fin de la transition en continuant
de traiter les événements et renvoie l’emprise effectivement affichée, avec `interrupted` si elle a été interrompue.
Les images intermédiaires remplacent leur entrée précédente dans l’historique natif : « Zoom précédent » revient
à la vue avant la transition en un clic, y compris lorsque cet historique atteint ses 100 entrées.

Validation : 526 tests API/navigation et 249 tests de configuration/exploration ; scénarios réels Qt 5 et Qt 6
sur les images intermédiaires, l’interruption, le remplacement, la désactivation et l’historique de navigation saturé.

## Vérification élargie de livraison

- Suite agents, API, tâches QGIS, stockage, checkpoints, contrôleurs, historique et animation : 5 537 tests réussis,
  11 ignorés ; le test `live_transport` est exclu de ce lancement.
- Après le dernier correctif de confidentialité du récapitulatif : 161 tests ciblés réussis, dont trois cas de
  changement de serveur, de compte et de partage des valeurs.
- Banc hors ligne : 171 scénarios réussis, 4 ignorés pour outils désactivés.
- Références de configuration et exports des skills à jour ; vérification des différences sans erreur.

Les scénarios natifs utilisent QGIS 3.44 et QGIS 4.3 avec Qt 5 et Qt 6 hors écran. Ils ne constituent pas une
validation complète de l’installation du plugin dans une session de bureau Windows.

## Interface QGIS et panneaux de plugins

Le chat dispose de `qgis_capabilities` pour lire les actions et panneaux actuellement disponibles, puis de
`control_qgis` pour une action typée. Les tables attributaires acceptent une expression propre à la table, sans
modifier le filtre ou la sélection de la couche. Les propriétés sont planifiées après la fin réussie de la réponse
et l’enregistrement de ses changements : les modifications manuelles ne sont ainsi pas capturées par son checkpoint.
Le résultat `scheduled` annonce cette attente, sans prétendre qu’un réglage a été appliqué. Stop ou un changement
de projet suppriment les ouvertures en attente. Pendant la boîte native modale, les messages en file sont retenus
et le loader passe en attente ; ils retrouvent ensuite leur état antérieur, y compris une pause demandée par l’utilisateur.

Les panneaux QGIS et plugins déjà présents dans la fenêtre principale sont découverts par leur identifiant Qt.
Un identifiant dupliqué ou désactivé est refusé. La découverte est refaite à chaque action pour éviter de conserver
un objet C++ détruit après déchargement d’un plugin. Les outils cartographiques admis sont déplacer, zoom avant,
zoom arrière et identifier ; les vues précédente et suivante utilisent l’historique natif.

Cette première intégration est propre au chat, comme les outils de fenêtre existants. Elle n’exécute aucune action
arbitraire, ne remplit pas les formulaires et ne lance pas le traitement d’un plugin en affichant son panneau.
Les traitements des plugins passent par les algorithmes Processing découverts et leurs contrôles habituels ; un
plugin sans panneau existant ou API prise en charge demande encore un adaptateur dédié.

Le skill `qgis-interface` apporte ces consignes uniquement lorsque les outils sont disponibles. Le dépôt compte
désormais 22 skills, dont 21 pour le chat et 16 pour MCP. L’index des outils reste sous 5 500 caractères grâce à des
résumés plus courts. Le banc hors ligne couvre 174 scénarios actifs, avec trois nouveaux cas d’interface.

Validation native : QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6, avec de vrais panneaux Qt, un outil cartographique et
l’historique de carte. Les entrées de dialogue de `iface` y sont simulées ; leur parcours complet dans QGIS de
bureau reste à vérifier. Les tests couvrent aussi les panneaux disparus, imbriqués, désactivés ou ambigus.

## Masquer les propositions de sauvegarde pour la session

La carte « Enregistrer le projet et les couches » propose « Ne plus proposer pendant cette session ». La question
du même nom lors d’un enregistrement natif QGIS offre également cette option, sous forme de case à cocher.
Ce choix masque les deux sortes de propositions jusqu’au prochain démarrage de QGIS, y compris si le panneau
est fermé puis rouvert ou si l’on change de projet. Il ne vaut pas autorisation de sauvegarder automatiquement.

La préférence est une propriété en mémoire de l’application Qt : aucun réglage permanent n’est écrit. La commande
manuelle d’enregistrement reste disponible. Les données transitoires conservent leurs protections existantes.
Validation : contrôles natifs Qt 5 et Qt 6, recréation du contrôleur, sauvegarde manuelle après masquage et tests
de stockage/persistance QGIS 3.44 inchangés.

## Curseurs cohérents et attentes locales

Une politique commune couvre les contrôles existants et créés ensuite, les sections détachées et les fenêtres
propres au plugin : main sur les boutons et listes de choix, curseur de texte dans les champs de saisie, flèche
sur les contrôles désactivés. Les champs de texte des listes éditables restent des zones de saisie. Les curseurs
natifs de déplacement, redimensionnement, histogrammes et outils cartographiques sont conservés.

Les traitements, lectures de couverture, publications de favoris et chargements d’expressions utilisent des
attentes attachées aux widgets concernés. FilterMate ne pousse ni ne dépile plus de curseur global de l’application.
Plusieurs opérations peuvent se terminer dans un ordre différent de leur lancement ; seule la dernière attente
encore active est affichée. La fin, l’erreur, l’annulation et le déchargement restaurent le curseur normal, en tenant
compte d’une désactivation ou d’un changement de thème intervenu pendant l’opération. Un changement explicite
effectué par un autre propriétaire est respecté ; une fin tardive après destruction du widget reste sans effet.

Validation : 1 208 tests des curseurs, contrôleurs, styles, gestionnaires et gel de carte ; 351 tests supplémentaires
des connexions du panneau et du partage de favoris. Scénario natif réussi sur QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6 :
changement d’outil de carte pendant une attente, opérations imbriquées, curseur global d’un autre propriétaire,
contrôles dynamiques, restauration des éditeurs et destruction d’un widget avant la fin de son opération.
Ces vérifications hors écran ne remplacent pas une validation visuelle sur le bureau Windows.

## Enregistrer les éditions de couche après confirmation

Après une demande du chat ou une recette ayant effectivement modifié le tampon d’édition, une carte propose
« Enregistrer les modifications » ou « Garder en attente ». Aucun appel d’enregistrement n’est exposé au modèle.
Il faut un clic explicite pour chaque proposition : l’autonomie de l’agent et le masquage des propositions de
sauvegarde du projet ne valent pas autorisation d’écrire dans la source. Sans ce clic, les modifications restent
dans QGIS et leur annulation conserve le fonctionnement existant.

La confirmation indique qu’elle enregistre toutes les éditions en attente des couches listées, y compris les
éditions manuelles, et qu’elles ne seront plus annulables depuis le chat après enregistrement. Les groupes de
transaction sont résolus avant l’affichage puis vérifiés à nouveau au clic. Les groupes de tampons QGIS sont
enregistrés ensemble par l’API native du projet ; les compagnons du groupe sont tous présentés à l’utilisateur.
Pour une couche mémoire, la carte précise que cet enregistrement ne crée pas de fichier : il faut conserver
le projet et ses couches pour retrouver ces données après fermeture de QGIS.

Une nouvelle édition, une sauvegarde manuelle, un changement de source ou la suppression d’une couche ferme la
proposition devenue périmée. Le clic vérifie aussi l’identité des couches, le groupe, leur état, la conversation,
les tâches en cours et les protections du projet. Une erreur du fournisseur affiche ses détails sans annulation
automatique : certaines étapes d’une écriture peuvent déjà avoir été appliquées. Un retour tardif après fermeture
du projet ne dépose pas de message dans le projet suivant.

Validation : 174 tests ciblés des confirmations, du cycle des demandes et des checkpoints. Scénarios natifs réussis
sur QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6, avec la carte en français et des GeoPackage lus séparément sur disque :
aucune écriture avant confirmation, refus et annulation, enregistrement par clic, expiration d’une proposition après
nouvelle édition et enregistrement simultané d’un groupe de tampons avec éditions manuelles. La résolution des
groupes automatiques de fournisseurs est couverte unitairement ; aucune transaction sur une base distante n’a été
effectuée pour cette vérification.

## Exports dans le dossier choisi par l’utilisateur

Le premier export réel ouvre le choix du dossier par défaut. Ce choix est mémorisé dans les préférences QGIS et
peut être modifié depuis « Dossier d’export par défaut… » dans le menu de l’agent. Construire les outils, lire un
fichier absolu ou ouvrir la conversation ne déclenche aucun sélecteur. Une annulation ou un changement de projet
pendant le sélecteur empêche l’export, sans repli automatique. Le choix du dossier reste distinct de la permission
d’exécuter l’export. Il s’applique aussi aux mises en page, graphiques, infographies et exports de profils de réglages.

La préparation du dossier et la résolution du sous-dossier refusent les emplacements dans le profil QGIS actif,
ses profils voisins et les liens qui y conduisent. Un ancien choix devenu interdit ou indisponible demande un
nouveau choix. La sauvegarde du projet avec ses couches refuse également le profil QGIS. Les résultats transmis
au modèle continuent de donner des noms relatifs ; les chemins complets restent dans l’interface locale.

Les dossiers existants explicitement sélectionnés conservent leurs permissions. Les nouveaux dossiers de sortie
gardent les protections existantes, ainsi que les refus de liens, de jonctions et de propriétaires étrangers.
Le serveur REST conserve ses réglages explicites de dossier ; son repli est désormais dans Documents et les
destinations dans les profils QGIS restent refusées. Les fichiers déjà présents ne sont pas déplacés.

Validation : 20 tests de configuration et de destination des exports, 59 tests ciblés du sélecteur, du menu,
des graphiques et des sorties locales ; banc hors ligne inchangé à 174 scénarios actifs réussis. Scénario natif
QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6 : export réel puis relecture d’un GeoPackage dans le dossier sélectionné,
réutilisation du choix, refus du profil et d’un sous-dossier interdit, annulation sans repli et refus de sauvegarder
le projet avec ses couches dans le profil. La réponse du sélecteur de dossier est simulée dans ce scénario.

## Réseau SVG persistant et variations d’activité

L’indicateur reste visible après la réponse, sous forme statique. Les 22 états distinguent les tâches réelles des
outils et les interactions : recherche, calcul, édition, export, style, navigation, rédaction, confirmation,
dictée, transcription, brouillon, file d’attente, fin, erreur et arrêt. Les états de repos, fin, brouillon,
file et erreur ne déclenchent aucune animation SVG. La dictée anime l’indicateur même sans requête modèle.
Un brouillon saisi pendant un traitement ne masque pas l’activité de ce traitement.

Les variantes claires et sombres, leurs SVG individuels et les planches de comparaison sont dans
[l’identité de l’agent](../../design/agent-identity/README.md). Les petits symboles centraux complètent la couleur,
avec un nom accessible et une infobulle traduits. Le titre de l’onglet conserve son ancienne icône.

La pulsation utilise désormais deux composantes explicites d’échelle ; la forme à une composante pouvait rester
figée dans Qt 6 tout en étant déclarée animée. Les contrôles natifs vérifient le changement réel des images des
orbites et de la pulsation, ainsi que l’immobilité de l’état terminé et l’arrêt lorsque le panneau est masqué.
Validation : 160 tests ciblés des widgets et du contrôleur, 46 SVG générés vérifiés ; comparaison de 22 dessins
distincts dans chaque thème et contrôle des images animées dans QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6.

## Datasets et propositions de sources

Le skill `datasets` reste disponible dans le chat lorsque les outils de recherche externe sont absents, dès lors
que la lecture des options et le lien vers les réglages sont autorisés. Il guide le choix du territoire, du thème,
de la période et de l’usage, propose au maximum trois sources adaptées, puis distingue les données d’analyse des
fonds de carte et des simples notices.

`agent_options` expose désormais le type, l’origine et la description publique des sources intégrées, avec leur
état activé ou désactivé. Cette lecture consulte le catalogue local : elle ne contacte aucune source et n’en active
aucune. Les adresses, notes personnelles et détails de connexion des sources personnalisées ou bases restent
hors de ces nouvelles métadonnées.

Pour une source pertinente mais désactivée, le skill propose son activation et un bouton vers les Sources.
`turn_on_agent_options` n’est appelé qu’après une demande explicite, avec sa confirmation habituelle ; son effet
arrive après la demande en cours. Une recherche ou une recommandation ne charge aucune couche. La comparaison
des jeux de données ne présente comme vérifiés que les résultats réellement retournés, avec leurs métadonnées
disponibles et la page source ; les informations absentes sont signalées. Une source activée ne contourne pas
un outil désactivé dans les réglages.

Le dépôt compte 23 skills, dont 22 pour le chat et 16 pour MCP. Ce nouveau skill dépend de l’interface du chat ;
les exports de skills MCP restent cohérents. Le banc hors ligne couvre 178 scénarios actifs, dont quatre nouveaux
sur l’inspection locale, la proposition sans activation, la recherche sans chargement et l’activation différée.
Ces scénarios sont scriptés : ils ne constituent pas un benchmark de qualité d’un modèle distant.

## Recherche Web de sources et ajout personnalisé

La source intégrée `web_search`, désactivée par défaut, autorise `search_data_sources` dans le chat. Les requêtes
publiques sont envoyées à DuckDuckGo, sans consulter les sites trouvés. L’activation de ce moteur n’autorise ni
les domaines des candidats ni leur téléchargement. Le client existant borne chaque lecture à 20 secondes et
2 Mio, respecte le proxy QGIS et l’annulation. Les liens et extraits renvoyés restent des candidats non vérifiés.

Un contrôle navigateur, une erreur HTTP ou une réponse illisible produit un échec explicite avec une proposition
d’ouverture manuelle de la recherche. Aucun contournement ni résultat fictif n’est utilisé. Le skill `datasets`
guide la recherche de portails puis d’endpoints, sans présenter une page d’accueil comme un service fonctionnel.
Le mode HTML est documenté par [DuckDuckGo](https://duckduckgo.com/duckduckgo-help-pages/features/non-javascript) ;
sa disponibilité et son format peuvent évoluer, d’où ce repli explicite vers le navigateur.

`show_settings_link`, avec `target: sources` et un objet `source`, propose un bouton de révision. Le clic ouvre
les Sources avec nom, adresse et type préremplis. La source n’est ni enregistrée, ni testée, ni activée à ce stade.
« Activer après l’ajout » est décoché pour une proposition de l’agent. L’utilisateur choisit Tester, Ajouter puis
Enregistrer les paramètres ; une simple suggestion du modèle ne vaut pas autorisation.

L’ajout manuel reconnaît les types explicites des URL, conserve le choix de type effectué par l’utilisateur et
accepte un nom facultatif. Les liens GetCapabilities et les URL d’API CKAN/Opendatasoft sont ramenés à leur base
de service, en préservant les paramètres de routage OGC. La nouvelle source est sélectionnée pour faciliter son
test. Le formulaire gère les doublons et demande un type lorsqu’il ne peut pas être déduit.

Validation : scénarios de formulaire réels en français sur QGIS 3.44 / Qt 5 et QGIS 4.3 / Qt 6, sans écriture des
préférences avant Enregistrer. Une recherche réelle de portails géographiques belges a retourné trois candidats ;
aucun de leurs sites n’a été consulté ni activé. Rapports [Qt 5](source-discovery-qt5.json),
[Qt 6](source-discovery-qt6.json) et [lecture Web réelle](source-web-live-summary.json).
Le banc hors ligne couvre désormais 181 scénarios actifs, avec les propositions de source et les recherches sans
activation ni chargement.
