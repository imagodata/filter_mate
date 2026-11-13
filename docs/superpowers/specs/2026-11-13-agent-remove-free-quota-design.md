# Lot B : retrait du quota gratuit

Date : 2026-11-13. Statut : à approuver. Petit changement : design court.

## Pourquoi

Le quota gratuit (relais Cloudflare `free-quota-proxy/`, publié avec la 5.1.0) a trois défauts :
- il expose de l'argent de l'auteur (200 $ par mois) à l'usage et aux abus ;
- il demande de surveiller un relais ;
- sa limite de 90 ko par requête contraint tout l'agent : elle a cassé l'agent dès le premier message le 13/11 (lot A).

Décision de l'utilisateur (13/11) : le retirer, code compris. Un nouvel utilisateur choisit un fournisseur, entre sa
clé et choisit un modèle, ou prend Ollama en local.

## Approches

1. **Retrait complet (retenue)** : le préréglage `free`, le client (`adapters/agent/free_quota.py`), le relais
   (`free-quota-proxy/`), les tests et la documentation. Git garde l'historique pour le rallumer un jour.
2. Masquer seulement (`FREE_QUOTA_URL = ""`, le code reste) : écartée par l'utilisateur.

## Conception

- **Code supprimé :**
  - `FREE_PRESET`, `FREE_MODEL`, `FREE_QUOTA_URL` (`core/agent/providers/__init__.py`) ;
  - `free_quota_url` et le cas `free` de `provider_config` (`adapters/agent/settings.py`) ;
  - `adapters/agent/free_quota.py` ;
  - les branches du quota dans le contrôleur et le panneau (renouvellement du jeton, messages 402, ordre des
    préréglages, libellé « FilterMate (free quota) ») ;
  - `tests/qgis_headless/check_free_quota_live.py` et les cas de test qui le concernent ;
  - le dossier `free-quota-proxy/`.
- **Un profil enregistré sur `free`** se lit comme « aucun fournisseur choisi ». Au premier envoi, le dialogue des
  réglages s'ouvre sur l'onglet Fournisseur, comme pour un nouvel utilisateur. Rien d'autre n'est migré : sans
  fournisseur choisi, le consentement reste à donner.
- **Premier usage guidé** (dialogue des réglages, onglet Fournisseur) :
  - choisir un fournisseur : Anthropic, Mistral, OpenAI, Ollama ;
  - pour Anthropic, Mistral et OpenAI, un lien vers la page du fournisseur où créer une clé ;
  - la clé ;
  - le modèle, avec des suggestions pour chaque fournisseur, et un bouton « Tester » qui envoie une requête minuscule
    et dit si la clé et le modèle répondent ;
  - le texte d'accueil du panneau ne parle plus du quota gratuit.
- **Ollama guidé** (ajouté par l'utilisateur le 13/11 ; Ollama devient la seule voie gratuite) :
  - Ollama ne répond pas à l'adresse : une note dit « Ollama does not answer at <address>: install it, start it, then
    Refresh », avec un lien vers `https://ollama.com/download` et un bouton Actualiser (la liste des modèles est lue
    de nouveau) ;
  - Ollama répond mais n'a aucun modèle, ou pas celui tapé : un bouton « Download » télécharge le modèle dans Ollama
    (`POST <address>/api/pull`, en flux) ;
  - modèle proposé par défaut : `qwen3.5:4b`, le seul mesuré au banc. Il tient dans un GPU de 8 Go avec tous les
    outils (42 cas sur 69, `docs/AGENT_MODE.md`). `qwen3:8b` ne tient pas dans 8 Go. L'utilisateur peut taper un
    autre nom ;
  - avant le téléchargement, une question avec le nom du modèle : il pèse plusieurs Go. La taille exacte s'affiche
    dès que le flux la donne ;
  - pendant le téléchargement : une barre de progression et un bouton Annuler. À la fin, la liste des modèles est lue
    de nouveau et le modèle est choisi ;
  - le téléchargement ne va qu'à l'adresse d'Ollama réglée dans le dialogue, comme la liste des modèles aujourd'hui.
- **Messages** : retirer ceux du quota des 34 catalogues et ajouter les nouveaux (skill `i18n-pipeline`).
- **Documentation** : `README.md`, `docs/AGENT_MODE.md`, `docs/ARCHITECTURE.md`, CHANGELOG (section non publiée).
- **Ce que fait l'utilisateur, pas le code** : couper le relais déployé quand il le veut
  (`npx wrangler secret put DISABLED` dans une copie de `free-quota-proxy/` prise dans Git, ou supprimer le Worker
  dans Cloudflare), puis révoquer la clé Anthropic de son espace de travail. Les installations 5.1.0 verront alors
  « The free quota is unavailable for now » et iront vers leur propre clé.

## Ce qui reste au constructeur

- La liste des suggestions de modèles pour Mistral et OpenAI : s'appuyer sur la liste des modèles du fournisseur
  (`/v1/models`) quand une clé est entrée, plutôt que sur des noms écrits en dur qui vieillissent.
- Vérification : tests unitaires, contrôle sans écran du dialogue et du panneau (`qgis-headless-bench`), `flake8`.
