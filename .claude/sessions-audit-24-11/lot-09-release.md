# Lot 9 — Release 5.1.2, branches, zip (audit 24/11/2026)

## Contexte
Dépôt FilterMate, base `main` à `a03bb9e0`. Aucune PR ouverte. Ne rien corriger hors de ce lot (aucun code produit).

## Défauts / décisions à traiter
1. Étiquette `v5.1.2` posée sur `00f61b8c` (#652, 24/11) et poussée ; aucune Release GitHub 5.1.2 (dernière : v5.1.1 du 17/11). La section 5.1.2 du CHANGELOG contient la ligne « the map zooms to the filtered extent of the source layer » (#655, `822f7a85`) ajoutée APRÈS l'étiquette : le code de #655 n'est pas dans v5.1.2.
   - `git merge-base --is-ancestor 75f114d9 v5.1.2` : non.
   - **Trancher** : déplacer l'étiquette sur un main corrigé, ou remonter la ligne #655 dans Unreleased ?
2. `main` après l'étiquette : 45 commits, 13 PR (#653–#665) ; Unreleased = 8 entrées ; `metadata.txt` n'a pas bougé → préparer la prochaine version proprement.
3. Étiquette `v5.2.0` locale sur `f90da9d2`, absente d'`origin` → supprimer ou pousser ?
4. Ménage : 108 branches locales (93 déjà dans main), 423 distantes (400 déjà dans main), 27 copies de travail dont 12 sur branche fusionnée + celle de l'audit (2,9 Go sous `.claude/worktrees`). 5 branches de code non fusionnées : `claude/agent-memory-lot2` (22/11, +771), `claude/engine-expression-context` (13/11, +138), `claude/agent-settings-hardening` (13/11, +81), `claude/agent-point-cloud-objects` (11/11, +433), `claude/agent-better-results` (10/11) + `claude/linkedin-sarlat-clips`.
5. Poids du zip : `CHANGELOG.md` 754 Ko dans le zip ; `i18n/` 14,7 Mo sur 33,5 Mo décompressés → exclure/alléger si la politique du dépôt l'autorise. Exclusions du zip non ancrées (`scripts/prepare_plugin_zip.sh`).
6. Questions produit ouvertes par l'audit (à consigner, pas à trancher seul) : Ask/Plan `undo_agent_step`/recettes/notes (refuser vs demander) ; REST+MCP sans case « Sources » + MCP au niveau standard quel que soit le tchat ; favoris sans projet (les relister ?) ; règle de nettoyage copies locales + `open_data/elevation-*|population-*|osm-*`.

## Vérification
- `prepare_plugin_zip.sh` puis `publish_qgis.py --validate-only` : zip ~10 Mo, 952 fichiers, `standalone/` exclu, syntaxe 3.8, Bandit/detect-secrets/flake8.
- `git ls-remote --tags`, `gh release list`, `git log v5.1.2..HEAD`. Rendre compte (commandes + sorties) sans pousser ni retagger sans feu vert explicite.
