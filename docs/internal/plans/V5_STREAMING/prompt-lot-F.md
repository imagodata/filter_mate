# Lot F — Clôture des sources en flux (à lancer quand A à E sont fusionnés)

**But.** Assembler les cinq lots en une fonction cohérente, traduite, testée en CI et documentée.

**Fichiers à toi.** Ceux que les règles communes réservent au lot F : `i18n/*.ts`, `i18n/*.qm`, `.github/workflows/*`, `tests/qgis_headless/run_smoke.py`. S'y ajoutent `CHANGELOG.md`, `docs/ARCHITECTURE.md` et `.claude/memory.md`. Pas `metadata.txt` : la 5.1.0 ne se publie que sur demande de Simon. Pas `website/**` : un push sur `main` publie le site.

**À faire.**
1. Vérifier que les lots A à E sont fusionnés (`gh pr list --state merged --search "stream"`). S'il en manque un, s'arrêter et le dire.
2. Vérifier que les contrats entre lots sont branchés :
   - « traduction `PARTIAL` / `NONE` → matérialisation » (lots A et B) ;
   - la ligne tuiles vectorielles de `get_layer_kind` (lots D et E).
3. Bout en bout dans QGIS 4.2 et 3.44, sur un projet avec communes WFS, ortho WMTS, MNT WCS, plan IGN vectoriel et un COPC distant : un filtre croisé par type, annuler / rétablir, un favori, enregistrer puis rouvrir le projet. Chaque casse est corrigée par une petite PR, selon les règles communes.
4. i18n : `pylupdate5`, puis `scripts/i18n_processing_context.py`, traduction française de toutes les nouvelles chaînes (listées dans les PR A à E), `lrelease`, puis vérifier que les `.qm` se chargent dans QGIS.
5. CI : ajouter les `check_stream_*.py` à `.github/workflows/qgis-headless.yml`. Les étapes réseau restent SKIP sans réseau et ne rendent pas la CI instable.
6. Documentation :
   - `CHANGELOG.md` : regrouper les puces des lots en une section « Streaming sources » sous `## [Unreleased]` ;
   - `docs/ARCHITECTURE.md` : capacité de source, dialectes serveur, matérialisation, rasters rendus et rasters de valeurs, tuiles.
7. Audit : relire l'artifact https://claude.ai/artifact/DJFuADfmk7UXVrpRSYQXux (outil Artifact, action `read`), mettre à jour les sections « Sources en flux » et « Suite » (étapes 3 à 7 et leurs PR), puis republier sur la même URL.
8. `.claude/memory.md` : fusionner les sections des lots en une seule, en ne gardant que les décisions et les pièges QGIS.

**Fini quand.**
- La CI est verte avec les nouveaux scripts.
- Le bout en bout est vert en 4.2 et 3.44.
- Le français est complet.
- L'audit et le CHANGELOG sont à jour.
- Un compte rendu final en français est rendu à Simon.

## Règles communes (identiques dans les six prompts)

**Contexte.** FilterMate est un plugin QGIS (dépôt `/home/simon/projects/filter_mate`, 5.0.0 publiée). Tu réalises une partie du plan « Sources en flux » de l'audit du 17/10/2026 : artifact « Audit FilterMate 5.0 », https://claude.ai/artifact/DJFuADfmk7UXVrpRSYQXux (lis-le avec l'outil Artifact, action `read`, pas WebFetch). Les étapes 0 à 2 sont livrées par la PR #155 (`gh pr view 155`). Cinq sessions (lots A à E) travaillent en même temps ; le lot F clôt après elles.

**À lire avant de coder.** `CLAUDE.md`, `.claude/memory.md`, puis le socle à réutiliser sans le dupliquer :
- `core/domain/source_capability.py` : `classify`, `SourceCapability` (localité, `ServerFilter`, `ValueKind`, `NetworkCost`, `key_list_limit` = 500, `in_list_max`) ;
- `adapters/qgis/source_capability_probe.py` : `capability_for_layer`, `counts_cheaply`, `feature_count_or_none`, `is_remote_layer`, `stable_key_for_layer` ;
- `core/domain/stable_key.py` ; `core/filter/pk_formatter.py` (le seul formateur de littéraux).

**Isolation.** Travaille uniquement dans ton propre worktree (outil `EnterWorktree`, ou `git worktree add .claude/worktrees/stream-<lot> -b claude/v5-stream-<lot>-<sujet> origin/main`), jamais dans `/home/simon/projects/filter_mate` lui-même. Une branche par PR, toujours partie d'`origin/main` à jour.

**Fichiers.** Tu possèdes ceux de ton lot ; ailleurs, modifications minimales. Fichiers partagés :
- `core/domain/source_capability.py` : ajouts seulement, sans renommer ni réordonner ;
- `CHANGELOG.md` : tes puces sous `## [Unreleased]` ;
- `.claude/memory.md` : ta section datée en tête.

En cas de conflit sur ces fichiers, garde les deux côtés. Réservés au lot F : `i18n/*.ts`, `i18n/*.qm`, `.github/workflows/*`, `tests/qgis_headless/run_smoke.py`, `metadata.txt`. Nouvelles chaînes : `tr()` / `translate()` seulement, listées dans la description de la PR.

**Contraintes.**
- QGIS 3.22 → 4.2, Qt5 et Qt6 (enums scopés, `exec()`), syntaxe Python 3.8.
- `core/domain` reste pur Python ; QGIS seulement dans `adapters/`.
- Aucun appel réseau, `featureCount()` ou `uniqueValues()` distant, ni lecture de pixels distants sur le thread principal.
- Jamais de résultat faux silencieux : un refus ou un résultat partiel donne un message clair.
- Aucun identifiant dans les journaux ni dans `config.json`. Ne pas toucher à la configuration QGIS système.
- Code, commentaires, commits et PR en anglais (style du dépôt), PEP 8, docstrings Google.

**Méthode.** Mesure d'abord le comportement actuel sur un vrai service et note-le dans la PR. TDD : chaque comportement a un test qui échoue sans le correctif. Petites PR. Si une décision change ce qui est livré et que ni l'audit ni le code ne la tranchent, pose une seule question à Simon ; sinon prends le défaut le plus prudent et écris-le dans la PR.

**Vérification dans un vrai QGIS.** Ton propre script `tests/qgis_headless/check_stream_<lot>.py` (modèle : `check_combine_literals.py`), lancé dans les images `qgis/qgis:ltr` et `qgis/qgis:stable` (commandes en tête de `.github/workflows/qgis-headless.yml`). Sans réseau, une étape qui a besoin d'un service est SKIP, jamais FAIL. Fixtures locales pour l'automatique (serveur HTTP local, pygeoapi en Docker) ; services publics en vérification manuelle : WFS / WMTS / WMS de la Géoplateforme (`https://data.geopf.fr/wfs/ows`, `ADMINEXPRESS-COG.LATEST:commune`), pygeoapi (OGC API), sampleserver6.arcgisonline.com (ArcGIS), COPC Autzen, EPT USGS 3DEP.

**Avant chaque PR.**
1. `git fetch && git merge origin/main`.
2. `python -m pytest tests/ -q -o "addopts="` vert.
3. `python -m flake8 --extend-exclude=tests,scripts,website,docs --count` = 0.
4. Smoke en ltr et stable.
5. Revue adversariale par le sous-agent `opus-reviewer` ; chaque trouvaille corrigée, ou écartée avec sa raison.

Puis `git push`, `gh pr create`, `gh pr merge --merge` sans redemander (consigne de Simon : fusionner chaque lot vérifié), et une nouvelle branche depuis `origin/main` pour la suite. Ne pas taguer ni changer de version.

**Compte rendu.** À chaque PR fusionnée, en français : fait, vérifié (nombre de tests, smoke, services essayés), non vérifié, limites connues, numéro de PR.
