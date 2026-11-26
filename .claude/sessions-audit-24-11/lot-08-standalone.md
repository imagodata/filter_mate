# Lot 8 — Application autonome (audit 24/11/2026)

## Contexte
Application autonome FilterMate (`standalone/`), HORS du zip du plugin. Base `main` à `a03bb9e0`. Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Clé d'API de l'agent impossible à enregistrer sans mot de passe maître QGIS dans le trousseau : aucune boîte d'identifiants installée, personne ne le demande ; seul Ollama marche.
   - `adapters/agent/settings.py:199`, `standalone/host/app.py` (#602, E sous LTR) → installer une boîte d'identifiants / repli fichier chiffré.
2. Profil nommé `default` → lit le mot de passe maître du vrai QGIS dans le trousseau système et chiffre sa base avec. Le README dit « no QGIS profile of yours is read or written ».
   - `standalone/paths.py:28`, `standalone/host/app.py:27` → profil dédié (ex. `filtermate-standalone`).
3. Installation en une ligne : zip de main sans version figée ni somme ; dépôt suivi 217 Mo dont 145 Mo de `website/` ; `hatchling` non figé ; `qgis>=4.2` et `micromamba latest` non figés.
   - `standalone/install.sh:9`, `install.ps1:6`, `pyproject.toml:9`, `standalone/provision.py:22` (#605, #607, #609)
4. `install.sh` : repli `--break-system-packages` installe pipx dans le site utilisateur du Python système (celui de QGIS sous Linux) ; « Nothing needs administrator rights » faux sans `python3-pip`/`python3-venv` ; `pipx ensurepath` modifie le profil shell sans le dire.
   - `install.sh:4`, `:27`, `:38`
5. `install.ps1` : filtre `*WindowsApps*` écarte un vrai Python du Store ; `exit 1` ferme la session PowerShell.
   - `install.ps1:12`
6. L'autonome écrit hors de son dossier : `~/.grass8`, `~/.cache` (init Processing).
   - confiner sous le dossier de l'app.

## Vérification
- `check_standalone.py` avec un trousseau (vierge + avec mot de passe maître QGIS préexistant) : clé enregistrable sans maître préexistant ; profil réel jamais lu/écrit.
- Install rejouée sur Debian/Ubuntu nu + Windows (ou à défaut relecture + tests unitaires). Rendre compte sans committer.
