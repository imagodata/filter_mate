# Audit du plugin FilterMate du 26 novembre 2026

L'audit de FilterMate 5.1.3 a confirmé et corrigé des défauts de reprise des conversations, de démarrage de l'API REST sans QGIS, de choix d'une couche par `@` et de traduction française. La sauvegarde des conversations passe d'un coût quadratique à un coût linéaire : sur le benchmark de 2 000 messages courts, la médiane descend de 1 515 à 6,86 ms. Les scénarios fonctionnels du dock et de cycle de vie passent dans QGIS 3.44.15 et 4.2.3.

Le point de départ est `8453883a`. La revue des changements fonctionnels récents porte principalement sur `461a9332..8453883a`. Le dépôt a continué à évoluer pendant les vérifications : les commits `67242f07` et `21632b64`, les icônes du panneau et le réglage de l'effort des modèles sont arrivés en parallèle. Ces travaux ont été conservés ; les suites concernées ont été rejouées. Le correctif d'import de `Option` et `Question` dans le contrôleur existait déjà au début de l'audit.

## Changements récents examinés

| Changement | Vérification principale |
|---|---|
| Reprise des conversations par projet (`8fbd62c5`) | Sérialisation, découpage par demande complète, remise à zéro, destination et partage des valeurs |
| Expressions et copies locales (`ef59ab26`) | Variables de projet et de couche, ellipsoïde, unités, champs virtuels, éditions non enregistrées, filtres SQLite conservés après réouverture et échec de recopie |
| Graphiques Python et infographies (`607225b9`) | Huit types de graphiques, SVG, exports PNG/JPEG/PDF, mise en page et actualisation, composition et HTML autonome |
| Postures, confirmations et mémoire (`996625ae`) | Cycle de vie des tours, confirmations, cartes de mémoire, effets du changement de réglages |
| Buffer et boutons EXPLORING (`461a9332`) | Remise à zéro du buffer, conservation du mode quand le bouton est masqué, retour sur une couche |
| Préparation 5.1.3 (`8453883a`) | Imports, catalogue français et traduction réellement chargée par Qt |

## Défauts corrigés

| Priorité | Défaut et conséquence | Correction |
|---|---|---|
| P1 | Une remise à zéro pouvait sauvegarder l'ancienne session, puis la reprendre au prochain message. Le serveur et le compte n'étaient pas vérifiés : même preset et même modèle suffisaient. | La remise à zéro efface la session conservée. La reprise vérifie aussi l'adresse, l'identifiant du compte QGIS et le choix de partage des valeurs. Une ancienne session sans ces informations revient au récapitulatif du fil. Aucune clé API n'est enregistrée dans cette identité. |
| P1 | `filtermate_api.server` ne s'importait plus dans un Python sans QGIS : quatre constantes de la route projet initialisaient indirectement `core.geometry`. | Les routes transmettent directement les noms de familles au garde des sources, qui lit les réglages à la demande. Le test existant en sous-processus reproduit et vérifie le démarrage autonome. |
| P1 | Choisir la première proposition filtrée de `@tron` pouvait insérer `batiment`. L'index du modèle filtré de `QCompleter` était utilisé dans la liste complète des couches. | Le libellé de la proposition choisie retrouve son texte d'insertion. Les homonymes conservent leur insertion par identifiant. Vérifié en PyQt5 et en QGIS Qt6 réel. |
| P2 | Chaque sauvegarde réencodait successivement tous les suffixes de l'historique sur le thread principal. | Chaque message est mesuré une fois ; le JSON reste limité à 250 000 caractères et commence toujours par une demande complète. |
| P2 | 28 chaînes françaises de mémoire, postures et interface manquaient dans leur contexte d'exécution. Dix libellés de raisonnement sont arrivés pendant le rejeu. | 38 traductions ajoutées au `.ts` français, `.qm` recompilé, chargement et traduction contrôlés avec Qt5 et Qt6. |

Fichiers principaux : [session_io.py](../../../core/agent/session_io.py), [agent_chat_controller.py](../../../ui/controllers/agent_chat_controller.py), [agent_panel.py](../../../ui/widgets/agent_panel.py), [project.py](../../../filtermate_api/routers/project.py), [FilterMate_fr.ts](../../../i18n/FilterMate_fr.ts).

## Mesures de performance

Benchmark local Python 3.12.3, trois répétitions, médiane. Le code de référence est celui de `8453883a`. Les deux versions reçoivent les mêmes messages et conservent le même historique dans ces quatre cas ; le nouveau champ d'identité ajoute 15 caractères au JSON sans contexte explicite.

| Messages courts | Avant | Après | Rapport |
|---:|---:|---:|---:|
| 100 | 3,680 ms | 0,341 ms | 10,8 fois |
| 500 | 93,669 ms | 1,592 ms | 58,8 fois |
| 1 000 | 364,702 ms | 4,047 ms | 90,1 fois |
| 2 000 | 1 515,289 ms | 6,861 ms | 220,9 fois |

Ces chiffres mesurent la sérialisation de l'historique, pas la durée d'une requête du modèle ou d'un filtrage GIS.

Les contrôles statiques d'import et de signaux parcouraient aussi les anciennes copies du plugin dans `.claude/worktrees`. Ils pouvaient signaler les imports cassés d'une autre copie et prenaient 27 à 34 secondes chacun. Leur périmètre exclut maintenant les dossiers de développement non livrés : les quatre contrôles concernés prennent environ 2,3 à 2,6 secondes chacun, en gardant les sources de production dans l'analyse.

## Vérification de non régression

| Vérification | Résultat |
|---|---|
| Suite générale Python avec dépendances API, MCP, PyQt5 et PyQt6 | 12 721 réussites, 41 ignorés ; un échec de traduction dû aux libellés de raisonnement ajoutés en parallèle, corrigé puis rejoué |
| Rejeu agent, contrôleurs, widgets, REST, MCP et garde des traductions, avec le panneau Qt6 isolé | 4 635 réussites, aucun échec ni test ignoré ; panneau Qt6 : 17 réussites séparément |
| GDAL dans QGIS stable | 302 + 199 tests réussis, aucun échec ni test ignoré dans ces deux groupes |
| Expressions, graphiques standards, outils GUI, Processing et copies locales, QGIS 3.22.16 | 145 contrôles réussis ; un groupe navigateur absent de cette image |
| Mêmes cinq groupes, QGIS 3.44.15 et 4.2.3 | 163 contrôles réussis par version ; navigateur vérifié séparément |
| Moteur et Processing, QGIS LTR et stable | 162 réussites par version ; deux contrôles PostgreSQL ignorés et un échec attendu sans PDAL |
| Parcours fonctionnel du dock jusqu'aux expressions de sélection | 134 réussites par version, un cas PDAL ignoré |
| Tâches concurrentes, couches retirées, changements de couche, déchargement et rechargement, panneaux séparés | 44 réussites par version |
| Graphiques avec QtWebEngine, QGIS 4.2.3 et Qt 6.10.2 | 69 contrôles réussis : code expert, confidentialité des erreurs, arrêt d'un script bloqué et HTML hors ligne compris |
| Nouveaux tests de l'effort des modèles arrivés en parallèle | 39 réussites dans le premier rejeu dédié |
| Panneau Qt6 dans un processus séparé | 17 réussites |
| Analyse statique de production et espaces du diff | `flake8` sans erreur ; `git diff --check` propre |

Les résultats détaillés et les mesures sont conservés dans [AUDIT_DEEP_2026_11_26.json](AUDIT_DEEP_2026_11_26.json). Les journaux complets de cette exécution se trouvent sous `/tmp/filtermate-audit-20261126*`.

Plusieurs scénarios de test ont été corrigés sans modifier le comportement du plugin : la recherche de réglages accepte volontairement une correspondance partielle, donc « nothing » n'est plus un mot garanti absent ; une demande en attente utilise désormais le signal qui transporte aussi sa posture ; le scénario de mode masqué doit réellement activer le mode puis quitter la couche ; le contrôle de liste multiple doit regarder la couche active et créer sa liste avant de la compter.

## Architecture et priorités suivantes

Le découpage entre `filtermate_core`, adaptateurs et interface est utile, et les tests du cœur sans hôte protègent une frontière concrète. `core` conserve toutefois des imports QGIS lors de son initialisation : l'incident REST montre qu'un simple import de constantes peut franchir cette frontière. Les tests de démarrage dans un sous-processus sans mocks doivent rester dans les validations de livraison.

Le dock dépasse 8 000 lignes et le contrôleur de l'agent 4 500 lignes. La persistance des conversations et les décisions de mémoire sont de bons prochains candidats à une extraction limitée, avec leurs contrats de cycle de vie existants. Une réécriture générale augmenterait le nombre de comportements à revérifier sans résoudre un défaut mesuré supplémentaire.

La localisation des autres langues reste à compléter : après l'arrivée des libellés de raisonnement, l'allemand et l'espagnol ont chacun 74 chaînes auxiliaires absentes ou non finalisées dans les contextes examinés. Le français n'en a plus. Le catalogue anglais utilise également le texte source comme repli ; il ne doit pas être traité comme une traduction française manquante.

Les tests réels Qt5 et Qt6 doivent être exécutés dans des processus séparés. Le passage en parallèle du test de panneau à PyQt6 a provoqué un arrêt natif d'un rejeu mêlant les deux Qt au moment de traiter leurs événements ; le test Qt6 passe seul. Cette limite concerne l'assemblage des tests, QGIS chargeant une seule version de Qt dans son processus.

## Portée de la validation

La campagne GUI complète, qui inclut de nombreux redimensionnements et déplacements de panneaux, a atteint la limite locale de 480 secondes. Le parcours fonctionnel de 134 contrôles et le cycle de vie de 44 contrôles ont terminé séparément sur les deux versions. La fin de la campagne étendue de dimensions n'est donc pas certifiée par cet audit.

Les connexions PostgreSQL réelles demandent `FM_PG_DSN` ; elles n'ont pas été validées ici. Les images QGIS utilisées pour les tests moteur ne disposent pas de PDAL pour certains découpages de nuages. Les deux tests SAM nécessitant ONNX et les poids restent également hors validation. Ces exclusions ne sont pas comptées comme des réussites.

La consolidation demandée après l'audit inclut les correctifs, les travaux d'interface et les nouveaux modules de réglage de l'effort, avec leurs tests. Ces modules doivent être suivis par Git : le constructeur utilise `git ls-files`. L'archive `dist/filter_mate_v5.1.3.zip` n'a pas été reconstruite par cet audit. Aucune publication ni modification de configuration QGIS personnelle n'a été effectuée.
