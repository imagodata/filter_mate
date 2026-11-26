# Lot 1 — Favoris et projet (audit 24/11/2026)

## Contexte
Plugin FilterMate (QGIS, Python 3.10+, PEP 8). Base : `main` à `a03bb9e0` (étiquette `v5.1.2` sur `00f61b8c`).
Ne rien corriger hors de ce lot. Ne pas modifier les fichiers de config QGIS système.

## Défauts à corriger (tous reproduits, détails dans l'audit § Projet)
1. Copie de projet (« Enregistrer sous ») ouverte puis fermée sans enregistrer : la synchro échoue sur `UNIQUE constraint failed: fm_favorites.id` et ne se répare plus. Favoris absents du `.qgz` pour toujours, sans message.
   - `core/domain/project_favorites.py:94`, `favorites_manager.py:882`, `favorites_service.py:257`
2. Favori non enregistré supprimé après un F5 (seconde liaison + fermeture sans enregistrer ; en lecture seule un seul F5 suffit).
   - `core/services/favorites_service.py:925` et `:935`
3. Ouverture d'un projet sans réglages FilterMate le marque modifié (demande d'enregistrer sans action utilisateur).
   - `core/tasks/layer_management_task.py:2262`, `infrastructure/utils/layer_settings.py:106`
4. Session sans projet enregistré : favoris/réglages perdus au redémarrage (id neuf à chaque session).
   - `adapters/database_manager.py:484`, `filter_mate_app.py:3074`
5. Doublons à la migration quand deux machines ont le même favori sous des ids différents.
   - `project_favorites.py:94`
6. Dédoublonnage compare nom+expression+couche : deux favoris qui ne diffèrent que par le tampon fusionnent à tort.
   - `core/services/favorites_migration_service.py:260`
7. Premier affichage du dock sur projet vide / projet en lecture seule marque modifié (`setProjectVariable`).
   - `filter_mate_app.py:2946`, `core/services/app_initializer.py:206`, `favorites_service.py:948`
8. `VariablesPersistenceManager` ne déconnecte jamais `cleared` ni `readProject`.
   - `adapters/variables_manager.py:277`
9. Tampon d'une couche recopié sur la suivante au changement de couche (`clearValue()` ne remet rien à zéro) + annulation d'un tour d'agent qui laisse son tampon. Cause du smoke GUI rouge depuis #649.
   - `ui/controllers/property_controller.py:1087` et `:1151`, via `layer_sync_controller.py:908`
10. Masquer le bouton « link » éteint la liaison courante et c'est enregistré dans le `.qgz` ; la réafficher ne rallume pas.
    - `filter_mate_dockwidget.py:3290`, `ui/controllers/coverage_dock_extras.py:1077`, `ui/managers/config_model_manager.py:388`
11. `name` non textuel dans un `.qgz` partagé fait planter le tri ; `set-url` git sans origine / réécriture d'origine sans avertissement.
    - `ui/dialogs/favorite_order.py:17`, `extensions/favorites_sharing/remote_repo_manager.py:623`

## Travail demandé
- Reproduire d'abord chaque défaut au niveau service (sondes de l'audit relancées sans QGIS quand possible), puis corriger à la racine.
- Transformer les deux sondes (copie + F5) en tests automatiques.
- Étendre `check_favorites_travel.sh` à la copie et au F5.
- Objectif : smoke GUI de nouveau à 0 échec.

## Vérification
- Tests du lot + `run_gui_smoke` verts sous QGIS LTR 3.44 (minimum).
- Rouvrir un projet inchangé ne doit produire aucune écriture ; un projet en lecture seule ne doit jamais être marqué modifié.
- Rendre compte : fichiers changés, tests lancés et résultats observés. Ne pas committer sans demande.
