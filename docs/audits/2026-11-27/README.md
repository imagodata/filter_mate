# Audit FilterMate des régressions des flux et des interfaces

Audit du 27 novembre 2026, sur FilterMate 5.1.3, à partir du commit `cf6190cdb`. Le périmètre couvre le filtrage, la persistance, les conversations, les skills, la navigation et le pilotage de QGIS. Les demandes complémentaires portent sur la reprise des conversations et sur une identité animée pour l’agent.

La priorité est de rendre les opérations prévisibles et récupérables. Sept défauts distincts ont été reproduits dans QGIS 3.44 : décalage entre posture affichée et permissions d’un message Push, dépassement du budget mémoire par Processing, deux défauts de zoom sur un point, déplacement manuel écrasé par un auto-zoom tardif, union de zoom incomplète et budget toujours occupé après sauvegarde. La réouverture d’une conversation depuis l’historique constitue une fonctionnalité à développer.

L’icône de réseau pulsé et son indicateur animé ont été intégrés à l’agent, à la demande de l’utilisateur. Les corrections fonctionnelles identifiées ci-dessous restent des propositions priorisées. La nouvelle icône du plugin reste une proposition graphique.

## Résultats prioritaires

P1 désigne un problème de contrôle, de ressources ou de récupération à traiter avant une extension importante des fonctions. P2 désigne un défaut fonctionnel ou un manque de vérification à programmer ensuite. Aucun classement P0 ne ressort des vérifications réalisées.

| Référence | Priorité | Constat | Niveau de preuve |
|---|---|---|---|
| R01 | P1 | Un message Push peut conserver les permissions Agir alors que Répondre est affiché | Interface et politique réelles reproduites |
| R02 | P1 | Les sorties Processing natives peuvent dépasser le budget mémoire | Reproduction avec une limite volontairement réduite |
| R03 | P1 | Une capture des effets peut échouer et laisser une annulation incomplète, signalée dans le journal | Lecture du code et injection de panne du scénario QGIS existant |
| F01 | P1 produit | L’historique ne permet pas de rouvrir une ancienne conversation complète | Contrat de stockage et actions de l’interface examinés |
| R04 | P2 | Le zoom refuse certains points dont X vaut zéro | Reproduction dans QGIS |
| R05 | P2 | Le zoom sur un point peut ajouter dix degrés de marge | Reproduction dans QGIS |
| R06 | P2 | Un auto-zoom tardif écrase une navigation manuelle | Livraison asynchrone reproduite après déplacement |
| R07 | P2 | Le chemin asynchrone d’une union de zoom écarte les rasters | Branche forcée sur de vraies couches, sans service distant |
| R08 | P2 | Sauvegarder ne libère pas le budget mémoire malgré le conseil donné dans l’erreur | Reproduction dans QGIS |
| R09 | P2 | Le banc d’évaluation propose un outil désactivé en production | Comparaison des catalogues |
| R10 | P2 | Avec FastAPI installé sans MCP, la collecte des tests échoue | Échec local reproduit |
| A01 | P1 à qualifier | Sélection et surlignage de l’agent comportent des lectures synchrones | Risque établi par le chemin de code ; latence distante non mesurée |

Les défauts de zoom sont des défauts de l’état actuel ; leur date d’introduction n’a pas été déterminée. R01 concerne directement le nouveau parcours Push ajouté par `fe267b3ce`.

## Reproductions et corrections proposées

### R01 Posture des messages ajoutés pendant une requête

Parcours : lancer une requête en Agir, sélectionner Répondre pendant son exécution, puis envoyer un nouveau message avec Push. Le sélecteur reste modifiable et affiche Répondre. Le panneau émet pourtant `push_requested(text)`, sans posture. Le contrôleur ajoute ce texte à la requête courante et conserve ses permissions.

La reproduction donne `displayed=respond`, `effective_request=act` et `filter_verdict=run`. Il s’agit d’un décalage entre ce que l’interface annonce et le contexte effectif, même si la conservation des permissions du tour en cours est intentionnelle.

Proposition : transporter la posture avec chaque message. Lorsque la posture choisie diffère de celle du tour actif, mettre le message en attente avec sa posture et l’indiquer dans la ligne de saisie. Afficher séparément le mode de la requête en cours et celui de la prochaine. Le bouton Envoyer maintenant d’une requête en attente doit respecter la même règle.

Critère : un message rédigé sous Répondre ne peut provoquer une modification automatique, y compris lorsqu’il est promu depuis la file.

Sources : [envoi et suivi des postures](../../../ui/controllers/agent_chat_controller.py#L3159), [promotion depuis la file](../../../ui/controllers/agent_chat_controller.py#L3187), [émission Push](../../../ui/widgets/agent_panel.py#L2097).

### R02 Budget mémoire des résultats Processing

Le budget de `AgentDataStore` est contrôlé lors de certaines allocations et pendant les téléchargements qui passent par `writer`. Processing peut écrire directement dans un chemin `/vsimem` obtenu sans estimation de taille.

Dans la reproduction, la limite est fixée à un octet avant un `native:buffer`. L’algorithme termine et ajoute un GeoPackage valide de 98 304 octets. Cette limite réduite rend le défaut facile à tester ; elle ne mesure pas la consommation maximale en usage réel. Le plafond par défaut de 1 Gio n’est donc pas une garantie pour ces producteurs.

Proposition : réserver la capacité avant les traitements estimables, contrôler les octets réellement produits et prévoir une stratégie de stockage choisie par l’utilisateur pour les sorties non bornées. Un contrôle après production permet de refuser un résultat trop volumineux, mais ne protège pas à lui seul contre le pic mémoire pendant son calcul. Les intermédiaires des modèles doivent entrer dans le même bilan.

Critère : tous les producteurs déclarent leur stratégie mémoire ou disque ; aucun traitement annoncé comme borné ne peut dépasser silencieusement sa réservation.

Sources : [budget](../../../adapters/agent/data_store.py#L102), [destinations Processing](../../../adapters/public_api/processing_tools.py#L503), [exécution](../../../adapters/public_api/processing_tools.py#L753).

### R03 Annulation partielle après une panne de capture

`TurnCheckpoint.begin` conserve les filtres, puis intercepte une erreur de `EffectsRecorder.before_call` et laisse continuer l’outil. Le journal avertit que les effets hors filtres ne seront pas enregistrés. Une panne de capture de style, de formulaire ou d’autres effets peut ainsi laisser un changement sans restauration complète par le tour.

Le scénario existant `check_undo_point_of_a_call` injecte une erreur de capture et observe que le gestionnaire est exécuté. Son attente de refus est devenue incompatible avec la politique actuelle. Ce résultat confirme le comportement conditionnel, sans démontrer que les captures échouent dans un usage ordinaire.

Proposition : distinguer capture obligatoire pour les effets que l’outil va modifier et capture facultative du contexte. Une capture obligatoire manquante doit empêcher cet effet ou donner un résultat explicite « annulation incomplète ». La carte et l’historique doivent montrer la couverture réelle de l’annulation.

Critère : une carte proposant Annuler ne présente pas comme intégralement réversible une opération dont un effet connu manque au checkpoint.

Sources : [capture des effets](../../../adapters/agent/turn_checkpoint.py#L80), [injection existante](../../../tests/qgis_headless/check_agent_chat.py#L490).

### R04 et R05 Zoom sur une entité ponctuelle

Le test d’emprise de `zoom_to` utilise notamment la vérité de `xMinimum`. Un point sélectionné en `(0, 45)` est refusé avec « has nothing to zoom to ». Ce point possède pourtant une géométrie valide.

Pour un point en `(1, 45)` dans une carte en EPSG:4326, la marge `rect.grow(10)` est exprimée dans les unités de la carte. La reproduction produit une vue allant de 35 à 55 degrés de latitude, à une échelle d’environ 1:9 153 361. Une demande de rapprochement peut ainsi éloigner fortement la vue.

Proposition : distinguer absence d’emprise et emprise dégénérée sans tester la valeur numérique d’une coordonnée. Centraliser la marge ponctuelle en pixels, avec une politique de conservation d’échelle, et réutiliser ce comportement dans l’agent, EXPLORING, les favoris et les API.

Critère : les points sur les axes et à l’origine restent ciblables ; la marge visuelle reste comparable entre carte géographique et carte projetée.

Source : [zoom de l’agent](../../../adapters/public_api/project_control.py#L79). Le parcours d’auto-zoom possède déjà un [agrandissement en pixels](../../../adapters/auto_zoom.py#L163) dont le contrat peut être partagé.

### R06 Navigation manuelle remplacée par un résultat tardif

La livraison de `queue_union_zoom` vérifie le jeton de filtrage, le CRS et l’identité des sources. Elle ne vérifie pas si l’utilisateur a déplacé ou zoomé la carte entre-temps.

La reproduction prépare la livraison, déplace la carte vers une autre région, puis livre l’emprise calculée : la vue manuelle est remplacée. Le calcul des entités est remplacé par une livraison contrôlée dans ce scénario ; aucun réseau n’est nécessaire pour démontrer le défaut de contrôle à l’arrivée.

Proposition : maintenir une génération de navigation distincte de celle des filtres. Une interaction manuelle annule les auto-zooms en attente. Un zoom explicitement demandé par l’utilisateur peut avoir une politique différente, clairement définie.

Critère : une tâche de filtrage ancienne ne reprend pas la main après une interaction cartographique plus récente.

Source : [livraison du zoom asynchrone](../../../adapters/qgis/async_query.py#L344).

### R07 Union de zoom incomplète

Si une couche vectorielle nécessite la lecture asynchrone, `auto_zoom_to_filtered` transmet uniquement les vecteurs à `queue_union_zoom`, puis retourne. Les autres couches retenues pour le zoom ne participent plus à l’union.

La reproduction fournit une couche vectorielle et un raster réels et force seulement le classement du vecteur comme coûteux. La file reçoit uniquement le vecteur. Le défaut concerne les appels demandant une union mixte ; le parcours habituel qui ne cible que sa source vectorielle n’est pas concerné.

Proposition : réunir les emprises déjà disponibles des autres types avec les emprises vectorielles calculées, dans le CRS de la carte, avant une livraison unique.

Source : [choix de la branche asynchrone](../../../adapters/auto_zoom.py#L257).

### R08 Sauvegarde et saturation mémoire

La sauvegarde rend les sources durables mais conserve les fichiers virtuels, notamment pour l’annulation et le rétablissement. Le budget continue de les compter. La reproduction sauvegarde une source de 125 octets avec un budget de 125 octets : l’octet suivant reste refusé et le message conseille encore de sauvegarder.

La conservation des données pour l’historique répond à un besoin réel. L’incohérence est le conseil présenté comme une solution à la saturation alors que cette sauvegarde ne libère pas cette capacité.

Proposition : réécrire les références vers les sources durables, puis libérer les actifs virtuels devenus inutiles. Tant qu’une référence de l’historique les requiert, présenter séparément mémoire active, mémoire retenue pour annulation et données sauvegardées. Proposer une libération explicite avec son effet sur l’historique.

Sources : [contrôle de capacité](../../../adapters/agent/data_store.py#L102), [fin de persistance](../../../adapters/agent/data_store.py#L369).

### R09 et R10 Fiabilité des validations

Le banc `agent_eval.py` construit ses outils depuis `chat_tools` sans appliquer `DISABLED_TOOLS`. Il peut ainsi tester `open_model`, alors que le contrôleur de production retire cet outil. Le skill `processing-models`, qui le requiert, est alors masqué dans le chat réel. Les 173 cas hors ligne passent, mais leur catalogue ne reproduit pas entièrement la disponibilité de production. Ce banc rejoue des réponses attendues ; son résultat ne mesure pas la qualité d’un modèle réel.

Proposition : partager le calcul des capacités entre le chat et le banc. Distinguer un cas actif, indisponible et volontairement désactivé. Garder les scénarios du designer pour une éventuelle réactivation, en rendant leur statut explicite.

Avec FastAPI installé sans le SDK MCP, `tests/api/test_mcp_add_layer_timeout.py` importe directement le serveur MCP et interrompt la collecte de l’ensemble des tests. Ce constat concerne cette combinaison de dépendances ; il ne démontre pas un échec du job CI propre qui peut ignorer la suite API lorsque FastAPI est absent.

Proposition : déclarer les prérequis au niveau du module et vérifier séparément les installations minimale et API complète.

Sources : [outils désactivés](../../../core/agent/tool_catalog.py#L72), [catalogue de production](../../../ui/controllers/agent_chat_controller.py#L1518), [catalogue du banc](../../../scripts/agent_eval.py#L1084), [import MCP du test](../../../tests/api/test_mcp_add_layer_timeout.py#L12).

### A01 Lectures synchrones dans les outils de vue

`select_features` appelle `selectByExpression` directement. `flash_features` lit les objets par `getFeatures` sur le chemin principal, sans les protections de durée et d’annulation du service de lectures asynchrones. Un plafond de 500 résultats limite leur nombre, pas le temps nécessaire pour les trouver.

Proposition : emprunter les snapshots et tâches existants pour les couches lentes ou distantes, puis appliquer les identifiants sur le thread graphique après validation de la génération du projet. Mesurer les délais de sélection et de surlignage sur une fixture HTTP locale ralentie. Le loader doit rester un indicateur d’activité ; sa présence ne démontre pas que le thread graphique reste disponible.

Sources : [sélection](../../../adapters/public_api/project_control.py#L338), [surlignage](../../../adapters/public_api/gui_control.py#L83), [service asynchrone](../../../adapters/qgis/async_query.py#L29).

## Reprendre une conversation depuis son historique

L’état actuel conserve un transcript et une session par projet nommé, dans `QgsSettings`, avec une rétention de vingt projets. La reprise automatique existe pour la session courante compatible. L’historique global conserve des requêtes et offre Renvoyer. Nouvelle conversation efface le slot courant ; les conversations successives ne sont pas archivées avec leur propre identité. Les projets jamais sauvegardés n’ont pas de clé persistante.

Le besoin demandé exige un objet conversation indépendant du chemin du projet, avec plusieurs conversations par projet.

| Action proposée | Comportement attendu |
|---|---|
| Ouvrir | Afficher l’échange complet, ses fichiers et ses actions, sans exécuter une action passée |
| Continuer | Restaurer le contexte compatible et ajouter le prochain message à cette conversation |
| Dupliquer | Créer une branche de discussion en conservant l’original |
| Renvoyer une requête | Préparer une nouvelle demande avec le texte sélectionné ; opération distincte de Continuer |
| Nouvelle conversation | Archiver l’échange actuel et ouvrir un échange vide |

Proposition système : utiliser des identifiants UUID pour les conversations et les projets, un stockage SQLite transactionnel dans le profil, et une migration des slots existants. Conserver messages, résultats d’outils nécessaires, transcript visible, modèle, destination et paramètres de partage. Le renommage ou le déplacement d’un projet doit conserver le lien logique.

La reprise compare le projet courant avec les couches et les sorties référencées. Si des éléments manquent, elle le signale et actualise le contexte. Une conversation ouverte dans un autre projet peut être consultée ; sa continuation nécessite un rattachement explicite. Les permissions accordées pour un échange ne doivent pas se réactiver implicitement après une nouvelle ouverture.

L’historique des opérations garde son rôle : rouvrir une discussion ne reconstitue pas une pile d’annulation disparue et ne rejoue pas ses effets.

Critères de recette : deux conversations du même projet restent accessibles après Nouvelle conversation et redémarrage ; projet sans nom et Enregistrer sous sont couverts ; la reprise n’exécute aucun ancien outil ; les contextes incompatibles sont expliqués dans l’interface.

Sources : [transcripts](../../../adapters/agent/transcript_store.py), [sessions](../../../adapters/agent/session_store.py), [journal des requêtes](../../../core/agent/request_log.py), [nouvelle conversation](../../../ui/controllers/agent_chat_controller.py#L3146), [interface de l’historique](../../../ui/widgets/agent_panel.py#L1050).

## Transitions de zoom et contrôle de QGIS

### Service de navigation commun

Créer un service de navigation partagé par le panneau, les favoris, l’agent et les API. Il reçoit une destination, son CRS, une marge visuelle et l’intention de navigation. Il arbitre les résultats tardifs et annule une transition lorsque l’utilisateur reprend la carte.

Une transition proposée dure environ 180 à 300 ms, avec interpolation du centre et de l’échelle logarithmique. Cette durée est un choix de conception à tester. Les changements très lointains doivent préserver l’orientation spatiale ; les filtrages en chaîne regroupent leurs demandes pour ne cadrer que le résultat utile. La carte conserve ses outils, son focus et sa sélection pendant le mouvement. Une option de réduction des animations reste disponible.

Les méthodes et signaux de `QgsMapCanvas` permettent de contrôler les emprises, le rafraîchissement et le rendu. L’interpolation et la gestion des priorités seraient une couche ajoutée à FilterMate. [API officielle QgsMapCanvas 3.44](https://api.qgis.org/api/3.44/classQgsMapCanvas.html).

### Interface native et autres plugins

Le plugin sait déjà activer et révéler une couche, surligner des entités, ouvrir une mise en page et naviguer dans un atlas. Le pilotage de l’interface peut être étendu avec des outils typés.

| Besoin | Extension proposée | Voie d’intégration |
|---|---|---|
| Examiner les résultats | Ouvrir une table filtrée ou les propriétés de la couche | `iface.showAttributeTable`, `iface.showLayerProperties` |
| Afficher un outil natif | Montrer un panneau enregistré et lui donner le focus | Adaptateur de panneaux avec identifiants stables |
| Explorer la carte | Déplacer, cadrer, revenir à la vue précédente | Service de navigation commun |
| Exécuter un traitement d’un plugin | Découvrir son algorithme et ses paramètres | Registre Processing actif, déjà exploité en partie |
| Utiliser un plugin sans fournisseur Processing | Appeler une fonction ou ouvrir son interface | Adaptateur dédié vers son API publique ou une action identifiée |

QGIS expose les ouvertures natives par `QgisInterface`, et un plugin peut publier ses algorithmes au registre Processing. Ces points d’entrée sont documentés ; ils ne garantissent pas qu’un plugin tiers offre une API automatisable. [API officielle QgisInterface](https://api.qgis.org/api/3.44/classQgisInterface.html), [fournisseurs Processing](https://docs.qgis.org/3.44/en/docs/pyqgis_developer_cookbook/processing.html).

Proposition : un registre de capacités décrit pour chaque action son propriétaire, sa version, ses entrées, sa disponibilité et ses effets. L’agent choisit une capacité vérifiée et reçoit un résultat observable. L’ouverture d’une interface et l’exécution de son traitement sont deux capacités distinctes. Les actions de plugins qui écrivent des fichiers ou modifient des données doivent annoncer leur couverture d’annulation.

## États de travail et ergonomie de l’agent

La barre actuelle est indéterminée, et les étapes d’outils sont suivies du statut générique Thinking. L’animation ajoutée apporte une identité et un signal d’activité. Elle ne sépare pas encore les phases de travail.

| État proposé | Présentation | Action disponible |
|---|---|---|
| Préparation | Contexte du projet et périmètre de la demande | Arrêter |
| Attente de réponse | Indicateur discret et temps écoulé | Arrêter, ajouter un message selon le mode affiché |
| Réponse reçue progressivement | Texte et indicateur d’écriture | Arrêter |
| Outil en cours | Étape, couche ou fichier concerné, durée | Annuler lorsque le traitement le permet |
| Attente de décision | Question au premier plan, activité visuelle apaisée | Accepter ou refuser chaque action |
| Nouvelle tentative | Cause courte et compte à rebours | Arrêter ou relancer ensuite |
| Interrompu après des effets | Étapes conservées et prochaine étape possible | Continuer, annuler les effets disponibles |
| Terminé | Résultats, avertissements, fichiers et sauvegarde | Explorer, comparer, exporter, continuer |

Créer des événements d’activité structurés dans le moteur pour alimenter ces états. Les phases décrivent des signaux observables ; le texte interne de réflexion du modèle ne constitue pas un indicateur de progression. Un pourcentage est pertinent lorsque le traitement fournit un total, sinon afficher l’étape et le temps écoulé.

Le bouton Stop doit rester identifiable quand la saisie contient du texte : aujourd’hui, ce bouton devient un envoi Push ou Queue et Échap demeure le raccourci d’arrêt. Une action d’arrêt dédiée réduit cette ambiguïté. La file doit montrer le mode de chaque message et permettre sa modification avant départ.

Le loader retenu reprend le réseau pulsé : quatre branches, un centre contrasté, une onde lente et trois particules en orbite. Il est limité à 20 images par seconde et son document animé est remplacé par un document statique lorsque le panneau disparaît ou que la requête se termine.

## Bilan des skills

Le dépôt contient 21 skills valides, dont 20 déclarés pour le chat et 16 pour MCP, avec recouvrement entre audiences. Les fichiers de skills contiennent 119 cas d’évaluation. Leur disponibilité effective dépend des outils et options autorisés ; `pyqgis` requiert le mode expert et `processing-models` requiert actuellement un outil désactivé.

| Skill | Apport actuel | Amélioration utile |
|---|---|---|
| `workflows` | Enchaînement des filtres, statistiques, acquisition et livraison | Préconditions, étapes vérifiées et reprise après interruption |
| `analysis` | Processing, champs et jointures | Coût des traitements, capacité de stockage et contrôles de résultat |
| `terrain` | Relief, ombrage, courbes et pentes | Résolution, couverture et qualité des sources rendues visibles |
| `open-data` | Portails, services et acquisition | Provenance, date, licence et état hors ligne des jeux ajoutés |
| `basemaps` | Fonds régionaux et ressources locales | Prévisualisation du fond et lisibilité des attributions |
| `cartography` | Styles, étiquettes, CRS, arbre et thèmes | Extraire les consignes de navigation vers un skill dédié |
| `styles` | Palettes, styles et variantes | Aperçu et comparaison avant application |
| `layouts` | Mises en page et atlas | Contrôles des éléments manquants avant export |
| `charts` | Graphiques et infographies | Fraîcheur du résultat et synchronisation avec les filtres |
| `dashboards` | Widgets interactifs du panneau | État persistant et lien explicite avec les couches |
| `deliver` | Formats et conditionnement des fichiers | Manifeste de livraison et contrôle de complétude |
| `editing` | Création, modification et suppression d’entités | Bilan des modifications et récupération après erreur |
| `forms` | Formulaires, contraintes et relations | Vérification des relations et aperçu de saisie |
| `projections` | Choix et configuration du CRS | Cohérence avec les unités et les opérations de mesure |
| `raster-objects` | Objets et segmentation guidée | État du modèle, qualité et validation des objets proposés |
| `configuration` | Réglages, profils et diagnostic | Diagnostic guidé utilisant des capacités réellement actives |
| `panels` | Contrôle des panneaux FilterMate | Séparer cette fonction du futur pilotage des panneaux QGIS |
| `processing-models` | Instructions du designer et des chaînes réutilisables | Statut désactivé explicite et évaluation alignée sur la production |
| `cartograms` | Cartogrammes et grilles | Présentation de la déformation et comparaison géographique |
| `pyqgis` | Extension experte par code confirmé | Garder les nouveaux usages courants dans des outils typés |
| `qgis` | Consignes destinées aux clients MCP | Aligner le suivi des capacités et la reprise avec le chat intégré |

La couverture métier est déjà étendue. La valeur supplémentaire vient d’abord des outils et des services qui rendent leurs consignes exécutables.

| Ajout proposé | Priorité | Dépendance concrète |
|---|---|---|
| `navigation` | P1 | Service commun de zoom, cadrage et restauration des vues |
| `workflow-recovery` | P1 | Identité des étapes, résultats conservés et contexte de reprise |
| `qgis-interface` | P1 | Outils typés pour les tables, propriétés, panneaux et actions enregistrées |
| `quality-control` | P2 | Contrôles de géométrie, CRS, valeurs manquantes et complétude par Processing |
| `data-catalog` | P2 | Métadonnées et provenance persistantes des couches et fichiers |

Ces skills doivent être conditionnés par leurs capacités réelles. Ajouter uniquement un fichier de consignes ne rendrait pas disponibles les panneaux natifs, une reprise d’étape ou un contrôle de ressources.

## Évolutions système recommandées

Le moteur de conversation indépendant de Qt, les adaptateurs, les tâches sur snapshots et les mécanismes de restauration offrent des points d’appui réutilisables. Leur cohérence doit être renforcée entre parcours.

1. Unifier le contexte d’exécution : projet, génération, annulation, posture, capacités disponibles et effets enregistrés. Chaque livraison tardive vérifie ce contexte.
2. Centraliser le suivi des ressources : réservation, production, persistance, références d’annulation et libération. Exposer ce bilan au diagnostic et à l’utilisateur lorsqu’un plafond est atteint.
3. Introduire le stockage des conversations comme service distinct du journal des requêtes et de la pile des opérations.
4. Donner au résultat d’outil un état explicite : réussi, partiel, refusé, annulé ou échoué, avec effets conservés, sorties et possibilité de reprise. Une carte peut alors présenter correctement une réussite partielle.
5. Mutualiser la découverte des capacités entre chat, MCP et évaluations. Les sources désactivées, les dépendances manquantes et les fonctions retirées ont un statut distinct.
6. Extraire progressivement navigation, présentation de l’activité et historique du contrôleur central. À la base auditée, le dock compte environ 8 094 lignes, le contrôleur de chat 4 697 et le panneau 3 566 ; ces zones concentrent les changements et les interactions.

## Ordre de réalisation proposé

| Lot | Contenu | Condition de validation |
|---|---|---|
| 1 | Posture Push, budget Processing, couverture des checkpoints | R01, R02 et scénario de panne R03 ont des contrats testés |
| 2 | Conversations multiples et réouverture depuis l’historique | Archiver, rouvrir et continuer après redémarrage sans rejouer d’effet |
| 3 | Service de navigation et défauts de zoom | Points, CRS différents, union mixte et interaction pendant calcul couverts |
| 4 | États de travail, arrêt dédié et file de messages | Phase et permissions visibles, récupération explicite après interruption |
| 5 | Tables, propriétés et panneaux QGIS | Chaque capacité a une entrée stable, une disponibilité et un résultat vérifié |
| 6 | Adaptateurs de plugins et nouveaux skills | Scénarios réels validés sur les versions des extensions prises en charge |

L’identité animée de l’agent est livrée séparément dans le commit `7dde44e96`. Elle fournit le composant visuel du lot 4 ; les événements de phase et les autres évolutions de ce lot restent à développer.

## Validations et limites

| Vérification | Résultat |
|---|---|
| Reproductions de navigation, posture et mémoire | Résultats conservés dans [reproductions.json](reproductions.json) |
| Tests ciblés agent, auto-zoom, stockage et standard des skills | 266 réussis |
| Parcours étendu agent, adaptateurs, contrôleurs et extensions | 5 306 réussis et 11 ignorés avant interruption ; exécution partielle |
| Contrôleurs et extensions relancés séparément | 1 503 réussis |
| Interface et identité de l’agent | 76 réussis, dont cycle de vie de l’animation |
| Banc hors ligne | 173 sur 173 ; aucun appel à un modèle réel |
| Export des skills | Vérification de synchronisation réussie |
| QGIS réel, stockage et Processing | Scénarios existants réussis sur QGIS 3.44.15 |
| Identité et animation | Rendu et cycle de vie vérifiés sur Qt 5.15.18 / QGIS 3.44.15 et Qt 6.10.2 / QGIS 4.3.0 Master |

Les nombres de tests se recouvrent et ne doivent pas être additionnés. L’ensemble des tests du dépôt n’a pas été validé en une exécution complète. La première collecte a rencontré le cas FastAPI sans MCP décrit en R10. Les tests de serveur local ont nécessité une exécution hors sandbox après refus d’ouverture de socket ; ce refus ne constitue pas une régression du plugin.

Le grand scénario `check_agent_chat.py` comporte des attentes devenues incompatibles avec le fonctionnement courant : ancien défaut Queue, session restaurée désormais conservée et libellés de modèle maintenant élidés. Il signale aussi le changement de contrat de capture R03. Ce scénario nécessite une remise à jour avant de servir de validation globale du chat ; ses échecs ne sont pas comptés comme autant de régressions produit.

La reprise de ce scénario avec un répertoire de journalisation inscriptible a atteint son délai de 210 secondes après les contrôles de recettes. Elle ne constitue pas une exécution complète réussie.

Les appels externes publics, les modèles payants, le parcours Windows réel et l’ensemble des combinaisons de fournisseurs n’ont pas été exercés. Les propositions de zoom animé et de ponts vers d’autres plugins sont des conceptions à implémenter et à vérifier.

## Livrables

- [Script de reproduction QGIS](reproduce_qgis.py) et [résultats structurés](reproductions.json).
- [Planche des propositions graphiques](../../design/agent-identity/identity-proposals.png).
- [Identité animée et variantes du plugin](../../design/agent-identity/README.md).

Le script de reproduction s’exécute dans un conteneur isolé, avec le dépôt monté sous `/src` et un profil QGIS jetable. Certaines branches utilisent une injection explicitée dans les constats. Exemple :

```sh
docker run --rm --network none \
  -v "$PWD:/src:ro" -e QT_QPA_PLATFORM=offscreen \
  -e PYTHONDONTWRITEBYTECODE=1 qgis/qgis:ltr \
  python3 /src/docs/audits/2026-11-27/reproduce_qgis.py
```
