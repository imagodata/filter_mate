# Audit approfondi — FilterMate 5.0.0 — 21 octobre 2026

Révision initialement auditée : `a70da7fa`. Les constats ci-dessous décrivent cette révision. Les correctifs F1–F10 ont ensuite été implémentés dans le dépôt ; leur suivi et leur validation figurent à la fin de ce rapport.

**10 constats : 5 P1 et 5 P2.** Les risques prioritaires concernent la conservation des données à l’export, l’isolation des connexions PostgreSQL, le rétablissement après une panne de base et les modifications concurrentes de filtres. Aucun P0 établi dans le périmètre vérifié.

P1 = correction prioritaire : perte de données ou d’état utilisateur, mauvaise identité de connexion, blocage durable. P2 = défaut fonctionnel, protection incomplète ou lacune de validation à corriger ensuite. Ces niveaux ne constituent pas un score CVSS.

## Périmètre et méthode

- Inventaire des **452 fichiers Python de production suivis par Git**, représentant **205 866 lignes physiques** ; parcours des points d’entrée, des filtres vectoriels/raster/LiDAR, des exports, de l’historique, du pool de connexions, de l’API et du partage Git.
- Lecture ciblée des chemins critiques et des tests existants. Les constats des anciens audits n’ont pas été présumés encore valables.
- Exécution de pytest, du lint utilisé par la CI, de Bandit et de reproductions ciblées sur les méthodes réelles.
- Les reproductions remplacent les frontières QGIS, GDAL, export LiDAR et connexion PostgreSQL par de petits doubles. Les écritures et renommages Python ont lieu dans des répertoires temporaires. **Aucune base ni donnée utilisateur n’a été modifiée.**
- QGIS/GDAL ont aussi été exécutés dans les images Docker **déjà disponibles localement**, avec le dépôt monté en lecture seule, sans réseau et avec des données synthétiques jetables. Les sondes natives reproduisent F1, F3, F6 et F7 sur **QGIS 3.44.15 et 4.2.3**, avec GDAL 3.10.3. Le smoke test existant a été rejoué sur QGIS 3.44.15.
- Limites : pas de pilotage interactif de la GUI, pas de serveur PostgreSQL réel ni de chemin LAS/COPC natif — les images utilisées n’ont pas de provider PDAL. Le scénario F2 vérifie le vrai renommage destructif après un export simulé. Les tests ne certifient pas toutes les versions et plateformes prises en charge.

## Constats classés par impact

| ID | Priorité | Constat | Vérification |
|---|---|---|---|
| F1 | P1 | L’export peut remplacer la source originale d’une couche dérivée | Reproduit aussi avec QGIS/GDAL natifs |
| F2 | P1 | Le repli COPC → LAZ contourne la protection de la destination réelle | Reproduction contrôlée |
| F4 | P1 | Le pool PostgreSQL mélange utilisateurs et paramètres TLS | Reproduction contrôlée |
| F5 | P1 | Le contrôle de santé du pool peut boucler indéfiniment sous verrou | Reproduction bornée |
| F7 | P1 | Une tâche écrase un filtre plus récent ; Undo ne le récupère pas | Reproduit aussi avec QGIS natif |
| F3 | P2 | Les noms temporaires d’export peuvent écraser un autre fichier existant | Reproduit aussi avec QGIS/GDAL natifs |
| F6 | P2 | Le projet explicite n’est pas conservé jusqu’à l’application des résultats | Reproduit aussi avec QGIS natif |
| F8 | P2 | Des erreurs internes de tâches restent visibles dans les réponses REST | Reproduction contrôlée |
| F9 | P2 | La CI standard et le job de tests de publication ignorent les suites REST/MCP | Workflows et conditions de skip vérifiés |
| F10 | P2 | L’export LiDAR synchrone ne transmet pas l’annulation de Processing | Reproduction contrôlée |

### F1 — P1 — La protection des sources oublie les originaux des couches dérivées

**Emplacement :** [core/export/target_guard.py:133](../../../core/export/target_guard.py#L133), utilisé par [adapters/public_api/operations.py:875](../../../adapters/public_api/operations.py#L875).

`ProjectSources` inventorie exclusivement les fichiers de `layer.source()`. Après un filtre raster ou LiDAR qui remplace cette source par un VRT/COPC du cache, le fichier original n’apparaît plus dans cet inventaire. Pourtant `LayerSnapshot.original_source` / `enriched_source` le conserve pour Unfilter, Undo et la sauvegarde du projet.

**Déclencheur :** filtrer `dem.tif`, puis exporter la couche nommée `dem` en GeoTIFF dans son répertoire d’origine. Si aucune autre couche ne référence encore `dem.tif`, `_output_file` autorise cette destination. L’export remplace alors le raster complet par le résultat filtré ; Unfilter revient au fichier désormais modifié.

**Preuve :** la sonde F1 construit une couche dont la source courante est un VRT et dont l’état mémorise `dem.tif` comme original. Le garde ne trouve aucun utilisateur de l’original ; le chemin accepté aboutit à son remplacement par la méthode réelle d’export, avec un writer simulé.

**Confirmation native :** sur QGIS 3.44.15 et 4.2.3, un vrai raster GeoTIFF de 64 pixels valides est filtré par `cross_filter_by_geometry`, puis exporté par `export_layers` dans son dossier d’origine. Le fichier original ne contient ensuite plus que **16 pixels valides**, avec un résultat d’export réussi. Cette sonde utilise les vrais providers, le VRT et le writer GDAL.

**Correction proposée :** protéger l’ensemble des sources nécessaires au rétablissement : source courante, originale, avant enrichissement et sources encore conservées par l’historique. Inclure aussi la source des couches temporaires explicitement exportées. Tester le refus après dérivation et après enrichissement.

### F2 — P1 — Le repli COPC écrit sur une destination qui n’a jamais été contrôlée

**Emplacement :** [adapters/qgis/coverage_layers/exporters.py:272](../../../adapters/qgis/coverage_layers/exporters.py#L272).

La destination contrôlée par l’appelant est `cloud.copc.laz`. Lorsque PDAL est absent ou ne sait pas écrire COPC, `PointCloudExportJob.run()` déplace le fichier intermédiaire vers `cloud.laz` avec `shutil.move`, sans vérifier cette nouvelle destination.

**Déclencheur :** exporter en COPC une couche `cloud` provenant de `cloud.laz`, dans le même dossier, sans PDAL compatible. La protection reconnaîtrait bien `cloud.laz` comme source active, mais elle n’est appelée que pour `cloud.copc.laz`.

**Impact :** sur le système POSIX testé, le nuage original est remplacé par les seuls points exportés, avec un résultat annoncé comme réussi. Un export précédent portant ce nom peut aussi être écrasé.

**Preuve :** F2 vérifie que le garde connaît la source `cloud.laz`, autorise le nom COPC, puis exécute le vrai chemin de repli. Les octets du fichier original sont remplacés dans le répertoire temporaire.

**Correction proposée :** déterminer le format et la destination effectifs avant toute écriture, puis leur appliquer les mêmes protections et règles d’unicité. Le repli peut aussi échouer explicitement plutôt que choisir une nouvelle destination non contrôlée.

### F4 — P1 — Les pools PostgreSQL ne sont pas séparés par identité

**Emplacement :** [infrastructure/database/connection_pool.py:571](../../../infrastructure/database/connection_pool.py#L571), [get_pool:598](../../../infrastructure/database/connection_pool.py#L598). Chemin actif notamment dans [core/tasks/layer_management_task.py:1572](../../../core/tasks/layer_management_task.py#L1572).

La clé du pool est uniquement `host:port/database`. Le compte et `sslmode` sont acceptés par `get_pool`, mais ignorés lorsqu’un pool existe déjà pour ce serveur et cette base.

**Déclencheur :** deux couches du même projet utilisent la même base avec des comptes différents. Le second emprunte le pool créé pour le premier. Une demande `readonly` / `verify-full` peut donc réutiliser un pool `administrator` / `disable`, ou inversement provoquer des refus d’accès imprévus.

**Preuve :** F4 appelle deux fois le véritable gestionnaire avec ces paramètres. Les deux résultats sont le même objet et conservent la première identité et le premier mode TLS. Aucune connexion réelle n’est ouverte.

**Correction proposée :** inclure dans l’identité du pool le compte et les paramètres de connexion pertinents ; traiter aussi les changements d’authentification. Retourner les connexions au pool exact qui les a créées : les méthodes de release/close devront évoluer avec la clé. Ne pas exposer de secret dans une clé journalisée.

### F5 — P1 — Une panne PostgreSQL peut bloquer durablement le pool et son arrêt

**Emplacement :** [infrastructure/database/connection_pool.py:305](../../../infrastructure/database/connection_pool.py#L305), [création:196](../../../infrastructure/database/connection_pool.py#L196), [arrêt:482](../../../infrastructure/database/connection_pool.py#L482).

Lorsqu’une connexion échoue, `_create_connection()` intercepte l’exception et renvoie `None`. La boucle de remise à niveau de `_perform_health_check()` continue tant que le minimum de connexions n’est pas atteint. Elle ne traite pas `None` comme un échec terminal, ne consulte pas l’événement d’arrêt et conserve `_lock` pendant toutes les tentatives.

**Déclencheur :** le contrôle de santé retire des connexions mortes alors que la base reste indisponible. Chaque nouvelle tentative échoue sans augmenter le compteur ; la boucle ne peut pas terminer tant qu’une connexion ne réussit pas. Les délais réseau peuvent espacer les tentatives, sans borner la durée totale.

**Impact :** les emprunts, retours et la fermeture qui nécessitent le verrou peuvent attendre indéfiniment. `shutdown()` attend cinq secondes le thread, puis `close_all()` redemande ce même verrou : le timeout de join ne borne donc pas l’arrêt.

**Preuve :** F5 remplace la création de connexion par un retour `None` et observe cinq appels consécutifs sous verrou. Une exception de contrôle dérivée de `BaseException` arrête volontairement la sonde ; il n’y a aucune boucle illimitée dans le script d’audit.

**Correction proposée :** interrompre le remplissage au premier échec, borner les tentatives et consulter l’événement d’arrêt. Effectuer l’ouverture réseau en dehors du verrou, avec réservation cohérente d’un emplacement de pool.

### F7 — P1 — Les résultats asynchrones écrasent un filtre modifié pendant leur calcul

**Emplacement :** [adapters/qgis/coverage_layers/cross_filter_task.py:102](../../../adapters/qgis/coverage_layers/cross_filter_task.py#L102), [application cible:117](../../../adapters/qgis/coverage_layers/cross_filter_task.py#L117), [VectorTargetJob.apply:524](../../../adapters/qgis/coverage_layers/target_appliers.py#L524).

Le job mémorise `before` au lancement, puis applique son résultat sans vérifier l’état actuel de la couche. La recherche par identifiant vérifie seulement que la couche existe encore. La protection de l’API contre les opérations FilterMate simultanées ne couvre pas une modification depuis les outils natifs de QGIS ou un autre plugin.

**Déclencheur :** lancer un calcul sur une cible portant `initial = 1`, puis lui appliquer `newer_manual_filter = 1` avant la fin du worker. Avec la combinaison AND, le résultat appliqué est `(initial = 1) AND (computed = 1)`.

**Impact :** le filtre plus récent disparaît. L’historique enregistre l’ancien `before`, donc Undo rétablit `initial = 1` et ne permet pas de récupérer le filtre intermédiaire.

**Preuve :** F7 exécute le vrai `VectorTargetJob.apply`, le vrai `CrossFilterTask.apply_results` et le vrai service Undo avec une couche de test. Le filtre intermédiaire est absent à la fin et après Undo.

**Confirmation native :** le même scénario sur une vraie couche QGIS en mémoire, sous QGIS 3.44.15 et 4.2.3, remplace le filtre récent `"id" >= 3` par `("id" >= 1) AND ($id IN (1, 3))`. Undo remet `"id" >= 1`.

**Correction proposée :** comparer l’état courant au snapshot préparé avant toute mutation ; signaler un conflit et conserver la modification récente. Ajouter un identifiant de génération pour les changements que les snapshots ne décrivent pas, si nécessaire. Capturer un état `before` cohérent avec la mutation effectivement autorisée.

### F3 — P2 — Les fichiers intermédiaires ont des noms prévisibles et ne sont pas protégés

**Emplacement :** [adapters/qgis/coverage_layers/exporters.py:84](../../../adapters/qgis/coverage_layers/exporters.py#L84), [temporaires LiDAR:237](../../../adapters/qgis/coverage_layers/exporters.py#L237).

Les chemins `export.tif.staging.tif`, `*.warped.tif`, `*.partial.*` et `*.staging.laz` sont déduits directement de la destination. Le contrôle des sources porte sur le fichier final. Aucun mécanisme de réservation exclusive ne garantit que ces intermédiaires appartiennent à cet export.

**Déclencheur :** un de ces noms existe déjà, par exemple comme donnée encore chargée ou comme intermédiaire d’un autre writer. Il peut être écrasé, renommé ou supprimé par le traitement et son nettoyage.

**Preuve :** F3 place une source active au nom `export.tif.staging.tif`. L’export vers `export.tif` est autorisé, puis remplace et renomme ce fichier ; son ancien chemin disparaît.

**Confirmation native :** le vrai `QgsRasterFileWriter` reproduit l’écrasement et la disparition de cette source chargée sur QGIS 3.44.15 et 4.2.3.

**Correction proposée :** utiliser un sous-répertoire temporaire unique sur le même volume que la destination, conserver l’extension requise par le writer et ne nettoyer que les fichiers créés par l’opération. Tester aussi les collisions avec les intermédiaires LiDAR.

### F6 — P2 — Le projet explicite est abandonné pendant l’exécution

**Emplacement :** [adapters/public_api/operations.py:277](../../../adapters/public_api/operations.py#L277), [CrossFilterTask.apply_results:96](../../../adapters/qgis/coverage_layers/cross_filter_task.py#L96).

Les opérations acceptent `project=` et y résolvent leurs couches. `_run_task` ne transmet toutefois pas ce projet à `build_task`. Même un appel direct à `build_task(..., project=autre_projet)` ne suffit pas : `CrossFilterTask` ne conserve pas le projet et applique ensuite les résultats dans `QgsProject.instance()`.

**Impact :** les cibles du projet explicite sont introuvables, ou des couches du projet global portant les mêmes identifiants sont modifiées. Des identifiants identiques sont possibles lorsque deux projets reprennent les mêmes définitions de couches.

**Preuve :** F6 prépare un job avec la couche du projet explicite via le vrai `build_task`. À l’application, le job reçoit la couche du singleton. Le cas raster sans cible possède déjà un contournement spécifique dans `_source_only`, qui ne corrige pas le chemin général.

**Confirmation native :** avec deux vrais `QgsProject`, le job du projet explicite calcule correctement, puis son application retourne `layer removed` parce que sa cible est cherchée dans le singleton. La couche du projet explicite reste inchangée sur QGIS 3.44.15 et 4.2.3.

**Correction proposée :** transporter le projet, son contexte de transformation et sa durée de vie jusqu’à la tâche ; résoudre et appliquer dans ce projet, puis tester deux projets réellement distincts.

### F8 — P2 — Le masquage des erreurs internes REST ne couvre pas les exceptions des tâches

**Emplacement :** [adapters/qgis/coverage_layers/cross_filter_task.py:85](../../../adapters/qgis/coverage_layers/cross_filter_task.py#L85), [operations._collect:419](../../../adapters/public_api/operations.py#L419), [filtermate_api/qgis_accessor.py:131](../../../filtermate_api/qgis_accessor.py#L131).

Le mapper REST remplace les messages marqués `internal_error` / `internal_failures` par un diagnostic générique. Or les exceptions de calcul et d’application sont converties en `str(exc)` dans la tâche, puis recopiées dans le rapport sans ce marquage. Elles suivent ainsi le chemin des messages de validation destinés au client.

**Impact :** un échec de capture, de provider ou de requête peut retourner des chemins internes ou du SQL au client REST. Une éventuelle présence de secrets dépend du texte du provider ; elle n’est pas démontrée ici.

**Preuve :** F8 fait échouer le vrai `CrossFilterTask.run()` avec un chemin synthétique interne. Le message traverse `_collect` puis `_client_messages` sans modification.

**Correction proposée :** conserver la distinction entre erreur de validation et exception interne dans les outcomes. Journaliser les détails côté QGIS et ne transmettre au client que le diagnostic public et, éventuellement, un identifiant de corrélation.

### F9 — P2 — Les tests API optionnels ne sont pas obligatoires dans la CI

**Emplacement :** [.github/workflows/test.yml:39](../../../.github/workflows/test.yml#L39), [.github/workflows/release.yml:47](../../../.github/workflows/release.yml#L47), [tests/api/conftest.py:12](../../../tests/api/conftest.py#L12), [tests/unit/api/test_mcp_server.py:16](../../../tests/unit/api/test_mcp_server.py#L16).

Les deux jobs installent uniquement `requirements-test.txt`, qui contient pytest et ses extensions. La suite REST est ignorée sans FastAPI ; les tests du serveur MCP sont ignorés sans `mcp`. Les scripts QGIS du workflow headless ne remplacent pas ces tests de contrat HTTP/stdio.

**Impact :** une CI verte et le job de tests précédant la publication ne garantissent pas que l’authentification, les routes et les outils MCP fonctionnent. Les tests existent, mais leurs dépendances ne font pas partie du contrat de CI.

**Vérification :** les skips sont présents dans l’exécution initiale sans ces dépendances. L’audit a installé les extras dans un environnement temporaire pour les exécuter. Cela établit la lacune de configuration ; aucun échec d’un workflow distant n’est présumé.

**Correction proposée :** ajouter un job API qui installe explicitement les dépendances REST, HTTPX et MCP, et exige la collecte de ces suites. Une matrice des versions majeures MCP prises en charge rendrait aussi cette promesse vérifiable.

### F10 — P2 — L’annulation Processing n’atteint pas l’exporteur LiDAR synchrone

**Emplacement :** [adapters/public_api/operations.py:904](../../../adapters/public_api/operations.py#L904), [adapters/qgis/coverage_layers/exporters.py:298](../../../adapters/qgis/coverage_layers/exporters.py#L298).

Contrairement au raster et au vecteur, la branche LiDAR n’envoie pas `feedback` à l’exporteur. Le helper `export_point_cloud()` n’accepte pas ce paramètre et appelle `.run()` sans argument, alors que `PointCloudExportJob.run(feedback)` sait le relayer et vérifier l’annulation.

**Déclencheur :** annuler Processing pendant l’export d’un nuage volumineux. L’opération ne vérifie l’annulation qu’avant le prochain élément ; avec une seule couche, elle peut terminer et annoncer un succès après la demande d’annulation.

**Preuve :** F10 annule le feedback pendant `doExport` et exécute les vrais helpers d’export : la sortie est néanmoins renommée vers son nom final et enregistrée dans `report.done`.

**Correction proposée :** transmettre le feedback jusqu’au job LiDAR, relayer sa progression comme pour le raster et vérifier qu’une annulation tardive ne publie pas le fichier final.

## Validation effectuée

| Vérification | Résultat |
|---|---|
| Suite complète, Python 3.12.3, extras REST/MCP dans un environnement isolé | **5 692 réussis, 40 ignorés, 1 échec**, en 268,20 s |
| Échec restant | Garde Qt qui analyse les anciens worktrees `.claude/`, détaillé ci-dessous ; aucun autre échec |
| Tests ignorés | Modules et cas dépendant de GDAL, NumPy et PyQt, absents de cet environnement au moment de cette exécution |
| Tests client MCP auparavant bloqués par le sandbox | **65 réussis** après autorisation des seuls besoins réseau de test, sur loopback |
| Neuf sondes de défauts F1–F8, F10 | **9/9 reproductions obtenues**, mapper REST de F8 inclus |
| Sondes natives F1, F3, F6, F7 | **4/4 défauts reproduits sur chacune des deux versions**, QGIS 3.44.15 et 4.2.3 / GDAL 3.10.3 |
| Smoke test natif existant, QGIS 3.44.15 | **140 contrôles réussis, 0 échec nouveau, 2 skips, 1 XFAIL connu**, en 8,2 s |
| Tests numériques après installation de NumPy 2.5.4 | **180 réussis, 11 ignorés** faute de GDAL/OGR dans le Python hôte ; exécution ciblée, dont certains tests étaient déjà inclus dans la suite complète |
| `python3 -m flake8 --extend-exclude=tests,scripts,website,docs --count` | **0 erreur** |
| Bandit sur les dossiers de production et points d’entrée | **0 alerte**, 159 470 lignes comptées par l’outil, 283 contrôles explicitement ignorés via les annotations du code |
| Parsing AST des 452 fichiers de production suivis par Git | **0 erreur de syntaxe** |
| Détecteur Qt sur ce même inventaire | **0 occurrence interdite** |

Les extras ont été installés sous `/tmp`, sans modifier les dépendances du dépôt ni l’installation Python système. Versions utilisées pour les tests API : FastAPI 0.156.8, Pydantic 2.14.1, HTTPX 0.28.1 et MCP 2.3.0. La compatibilité MCP 1.x n’a pas été rejouée pendant cet audit.

La première exécution sans les extras et dans le sandbox réseau avait donné 5 329 réussites, 42 skips, 3 échecs et 25 erreurs. Deux échecs et les 25 erreurs provenaient de l’interdiction de créer des sockets ; ils ne sont pas retenus comme bugs du projet. Le second environnement règle aussi la disponibilité des dépendances dans les sous-processus MCP.

Le succès du smoke test natif malgré F1/F3/F6/F7 indique des cas manquants dans les scénarios actuels. Les deux skips concernent le nettoyage PostgreSQL et le scénario à deux bases, faute de `FM_PG_DSN`. Le XFAIL concerne le clipping LiDAR sans provider ni exécutable PDAL ; il est décrit par le script et ne constitue pas un nouveau constat de cet audit.

## Observations de maintenance

- **Garde Qt pollué par les worktrees locaux :** `tests/test_no_unscoped_qt_enums.py` parcourt récursivement le dépôt sans exclure `.claude`. L’échec observé correspond à 55 usages d’enums dans cinq anciens worktrees sous `.claude/worktrees/`. Le même détecteur, appliqué aux **452 fichiers de production suivis par Git**, ne trouve **aucune occurrence**. Exclure les répertoires d’outillage ou partir de l’inventaire Git rendrait ce test reproductible. Ce résultat ne démontre pas un défaut Qt du plugin livré.
- **Licence incohérente dans les fichiers :** `README.md:10,124` annonce GPLv3, tandis que `LICENSE:1` contient MIT. Harmoniser la documentation et le texte de licence selon la décision du mainteneur ; cet audit ne tranche pas les obligations juridiques.
- **Concentration du code :** `filter_mate_dockwidget.py` compte 7 601 lignes ; `exploring_controller.py` 3 896 ; `coverage_mode_controller.py` 3 337 ; `core/tasks/filter_task.py` 3 228. 53 fichiers de `core/` importent QGIS. Ce sont des facteurs de coût de maintenance et de dépendance aux doubles de test, distincts des dix défauts ci-dessus.

## Vérifier les correctifs

[repro_deep_2026_10_21.py](repro_deep_2026_10_21.py) lance les tests de non-régression de F1 à F8 et F10. F9 se vérifie dans les workflows de CI.

```bash
python3 docs/internal/audits/repro_deep_2026_10_21.py
```

Le script nécessite les dépendances de `requirements-test.txt`. Il utilise des doubles aux frontières QGIS/PostgreSQL et ne modifie que des fichiers temporaires. Les assertions expriment désormais le comportement corrigé. La confidentialité du mapper REST est également vérifiée par `tests/api/test_task_error_privacy.py`, avec les dépendances de `requirements-test-api.txt`.

[repro_native_deep_2026_10_21.py](repro_native_deep_2026_10_21.py) lance le test maintenu dans [tests/qgis_headless/check_export_task_safety.py](../../../tests/qgis_headless/check_export_task_safety.py), qui vérifie les correctifs F1, F3, F6 et F7 sans doubles de QGIS/GDAL. Exécution avec une image QGIS locale, depuis la racine du dépôt :

```bash
docker run --rm --network none \
  -v "$PWD:/src:ro" \
  -e QT_QPA_PLATFORM=offscreen -e PYTHONDONTWRITEBYTECODE=1 \
  qgis/qgis:ltr python3 /src/docs/internal/audits/repro_native_deep_2026_10_21.py
```

Remplacer `ltr` par `stable` ou `release-3_22` pour les autres versions vérifiées. Le script imprime `NATIVE_AUDIT_RESULT` et ne travaille que sur des fichiers temporaires du conteneur. La CI QGIS exécute aussi ce test dans sa matrice d’images.

## Ordre de correction proposé

1. Protéger les sources originales et les destinations effectives, puis isoler les fichiers intermédiaires : F1, F2, F3.
2. Réparer l’identité et le rétablissement du pool PostgreSQL : F4, F5.
3. Refuser les résultats devenus obsolètes et conserver le projet explicite : F7, F6.
4. Propager les catégories d’erreur et l’annulation, puis rendre les suites API obligatoires : F8, F10, F9.

## Implémentation des corrections — 21 octobre 2026

| Constat | Correction appliquée |
|---|---|
| F1 | Inventaire des sources courantes, originales, avant enrichissement, conservées dans le registre et l’historique ; protection des couches temporaires exportées. Vérification dans les exports Python/Processing et les jobs du dock. |
| F2 | Suppression du repli automatique vers un nom LAZ non contrôlé. Sans PDAL compatible, COPC échoue explicitement et invite à choisir LAZ. |
| F3 | Un répertoire temporaire unique par job, sur le volume de destination. Nettoyage limité aux fichiers du job ; fermeture des objets QGIS sur le thread principal dans les exports asynchrones. |
| F4 | Identité du pool fondée sur serveur, base, compte, paramètres TLS et identifiants. HMAC propre au processus pour ne pas exposer de mot de passe dans les clés. Retour par propriétaire exact ; aucun héritage implicite d’un compte lorsque l’utilisateur manque. |
| F5 | Arrêt du rétablissement au premier échec, respect de l’arrêt et réservation bornée des connexions en cours d’ouverture. Aucune ouverture réseau sous le verrou du pool. |
| F6 | Transmission du projet jusqu’à la tâche, son contexte et son application, y compris dans les favoris. |
| F7 | Comparaison de l’état préparé avant mutation. Une modification récente de la cible reste intacte et n’ajoute pas de faux état Undo. Le rollback respecte les conflits sur la source. Les sélections vectorielles déjà copiées restent compatibles avec le moteur lié du dock. |
| F8 | Marquage des exceptions internes de source et de cible, propagation dans le rapport, puis remplacement par un diagnostic public dans les réponses REST. |
| F9 | Job REST/MCP avec matrice SDK 1.x/2.x, imports obligatoires et dépendances explicites ; mêmes extras dans le job de tests de publication. Test natif de sécurité ajouté à la CI QGIS. |
| F10 | Feedback enfant transmis à l’exporteur LiDAR, progression et annulation relayées, aucune publication du fichier final après annulation. |

Le garde Qt exclut désormais les worktrees et les dossiers d’outillage. NumPy est installé dans les dépendances de test pour activer les tests numériques. Le nouveau diagnostic est traduit en français et anglais ; les catalogues des autres langues contiennent une entrée à traduire, avec le repli anglais habituel. Les deux catalogues compilés concernés ont été mis à jour.

Les fichiers de licence n’ont pas été modifiés : l’incohérence MIT/GPLv3 relevée dans les observations nécessite un choix du mainteneur.

### Validation des corrections

- Suite complète sur l’état final, Python 3.12.3 et MCP 2.3.0 : **5 872 tests réussis, 38 ignorés, aucun échec**, en 251,35 s. Les skips concernent les dépendances natives absentes du Python hôte. Une exécution ciblée supplémentaire des modules corrigés donne **328 réussites, 7 skips**.
- Sondes natives : quatre scénarios corrigés validés sur QGIS **3.22.16**, **3.44.15** et **4.2.3**. Le raster original conserve **64/64 pixels valides**, le fichier portant l’ancien nom intermédiaire reste intact, le filtre récent survit à la fin du calcul et à Undo, et le projet explicite reçoit son filtre.
- Smoke moteur QGIS 3.44.15 : **140 réussites, aucun échec nouveau**, deux skips PostgreSQL et un XFAIL PDAL attendu.
- Smoke du dock sous Xvfb, QGIS 3.44.15 : **41 réussites, aucun échec, un skip PDAL**, aucun message critique FilterMate ni erreur Python.
- REST/MCP avec SDK **1.30.0** : **404 tests réussis**, aucun skip. SDK **2.3.0** couvert par la suite complète.
- Flake8 : **0 erreur** ; Bandit : **0 alerte** ; YAML des workflows et `git diff --check` valides.

Les limites PostgreSQL réel et écriture LAS/COPC native décrites dans le périmètre restent applicables. Les tests du pool utilisent des connexions simulées ; les images QGIS locales n’ont pas de provider PDAL.
