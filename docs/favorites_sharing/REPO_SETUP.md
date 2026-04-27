# Guide admin — créer un dépôt Git pour collection FilterMate

Comment provisionner un dépôt Git qui hébergera une collection de favoris partagée.
S'adresse à l'admin Git/IT, **pas** aux utilisateurs finaux (voir [USER_GUIDE.md](USER_GUIDE.md)).

---

## 1 · Choisir l'hébergeur

Compatible avec tout serveur Git acceptant HTTPS + auth Basic/PAT :

| Hébergeur | Cloud | Self-hosted |
|---|---|---|
| **GitHub** | ✅ | ❌ |
| **GitLab** | ✅ | ✅ |
| **Gitea / Forgejo** | ❌ | ✅ |
| **Bitbucket** | ✅ | ⚠ Server only |
| **Azure DevOps Git** | ✅ | ✅ |

Recommandation pour un usage public/inter-équipes : **GitHub repo public**, lecture anonyme = "tout le monde peut accéder à la collection".

> Note : le client Git de FilterMate n'utilise **que HTTPS** (subprocess `git`). SSH non supporté côté FilterMate (le user peut quand même cloner manuellement en SSH dans `local_clone` configuré).

---

## 2 · Créer le dépôt

### 2.1 · Visibilité

| Cas | Visibilité du repo |
|---|---|
| Collection publique (catalog ouvert) | **Public** — clone anonyme par les consommateurs |
| Collection interne entreprise | **Privé** — chaque consommateur a aussi besoin d'un PAT (lecture) |

### 2.2 · Structure attendue

FilterMate scanne le sous-arbre canonique. Le squelette minimum :

```
acme-collections/                  ← racine du repo
├── README.md                       ← libre
└── collections/                    ← convention Resource Sharing
    └── acme-favorites/             ← UNE collection (peut en héberger N)
        ├── collection.json         ← manifeste (lu par picker FilterMate)
        ├── icon.svg                ← optionnel, affiché par Resource Sharing
        ├── metadata.txt            ← optionnel, lu par Resource Sharing (INI)
        └── filter_mate/
            └── favorites/
                └── shared.fmfav-pack.json
```

Points clés :
- Le **nom du sous-dossier** sous `collections/` (`acme-favorites`) doit correspondre au champ `target_collection` configuré côté publisher dans FilterMate. Toute incohérence = bundle écrit ailleurs.
- Plusieurs collections par repo = autant de sous-dossiers `collections/<name>/`.
- Plusieurs bundles dans une collection = plusieurs fichiers `.fmfav-pack.json`. Un bundle = un set de favoris cohérent.

### 2.3 · Manifest `collection.json`

À la racine de `collections/<name>/`. C'est ce qui peuple les métadonnées affichées dans le picker FilterMate **et** dans Resource Sharing.

```json
{
  "name": "ACME Favoris",
  "author": "ACME Inc.",
  "license": "CC-BY-4.0",
  "description": "Favoris de filtrage partagés équipe ACME",
  "tags": ["acme", "fttp", "bruxelles"],
  "homepage": "https://acme.example.org",
  "qgis_min": "3.28"
}
```

| Champ | Rôle |
|---|---|
| `name` | Affiché dans Resource Sharing + picker FilterMate |
| `author` | **Important** : peuple le filtre auteur du picker FilterMate |
| `license` | Affiché dans le panneau "Provenance" du picker |
| `description`, `tags`, `homepage` | Métadonnées Resource Sharing |
| `qgis_min` | Resource Sharing refuse l'install si la version QGIS est inférieure |

Les valeurs sont **mergées** lors d'un publish : FilterMate ne clobbe jamais les clés que tu as posées à la main (`qgis_min`, `tags` Resource Sharing-style, etc.).

---

## 3 · Permissions

| Rôle | Accès Git | Authentification FilterMate |
|---|---|---|
| **Consommateur** d'un repo public | Clone read anonyme | Aucune (`authcfg_id` vide) |
| **Consommateur** d'un repo privé | Clone read avec PAT | Authcfg en lecture seule |
| **Publisher** | Push sur la branche cible | PAT scope `repo` / `write_repository` |
| **Admin du repo** | Admin Git | Tooling Git natif (gh/glab/web) |

Recommandations :
- **GitHub** : équipe de publishers en *Write* sur le repo (collaborators ou team).
- **GitLab** : rôle *Developer* minimum sur le projet.
- **Gitea** : `write:repository` collaborator.

### 3.1 · Branch protection (fortement recommandé)

Sur la branche cible (`main`) :
- ✅ **Require pull request reviews** (au moins 1 reviewer) — empêche un publisher de polluer la branche par erreur
- ✅ **Require status checks** si CI configurée (validation JSON, lint…)
- ❌ **Allow force pushes** : à laisser **désactivé**. FilterMate fait `pull --ff-only` à chaque publish ; un force-push distant casse tous les clones publishers (`pull` refuse → conflit à résoudre à la main).
- ❌ **Allow deletions** : désactivé.

> Workflow alternatif si reviews trop lourdes : pousser sur une branche `publishers/<user>` puis ouvrir des PRs vers `main` à la main. Configurer `branch: publishers/marie` côté FilterMate pour cette personne.

---

## 4 · CI optionnelle — valider les bundles avant merge

Workflow GitHub Actions `.github/workflows/validate.yml` minimal :

```yaml
name: validate-bundles
on:
  pull_request:
    paths: ['collections/**/filter_mate/favorites/*.fmfav*.json']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - run: pip install jsonschema
      - name: Validate bundles
        run: |
          python -c "
          import json, sys, glob
          from jsonschema import validate, ValidationError
          schema = json.load(open('schema/favorites-v3.schema.json'))
          ok = True
          for f in glob.glob('collections/**/filter_mate/favorites/*.fmfav*.json', recursive=True):
              try:
                  validate(json.load(open(f)), schema)
                  print(f'OK  {f}')
              except ValidationError as e:
                  print(f'BAD {f}: {e.message}')
                  ok = False
          sys.exit(0 if ok else 1)
          "
```

Note : le schema canonique est dans le repo FilterMate ([schema/favorites-v3.schema.json](../../extensions/favorites_sharing/schema/favorites-v3.schema.json)). Tu peux le copier dans le repo de collection ou le pull au runtime.

---

## 5 · Initialiser et tester

```bash
# Côté admin, depuis ton poste local :
mkdir -p collections/acme-favorites/filter_mate/favorites
cat > collections/acme-favorites/collection.json <<'EOF'
{
  "name": "ACME Favoris",
  "author": "ACME Inc.",
  "license": "CC-BY-4.0",
  "qgis_min": "3.28"
}
EOF

git init && git add -A
git commit -m "init: ACME Favorites collection"
git branch -M main
git remote add origin https://github.com/acme/acme-collections.git
git push -u origin main
```

Côté **publisher** : suivre [USER_GUIDE.md §B](USER_GUIDE.md#b--publier-devenir-publisher) pour configurer FilterMate et publier le premier bundle.

Côté **consommateur** : suivre [USER_GUIDE.md §A](USER_GUIDE.md#a--consommer-une-collection-partagée).

---

## 6 · Pièges à éviter

| Erreur | Conséquence |
|---|---|
| Force-push sur `main` côté serveur | `git pull --ff-only` côté publisher refuse → publish bloqué tant que le clone n'est pas reset à la main |
| `target_collection: "../foo"` côté publisher config | FilterMate refuse (path traversal protection ajoutée) → publish échoue avec warning |
| Renommer `collections/X/` côté serveur | Les publishers configurés sur `target_collection: X` continuent à pousser → le dossier renommé est recréé. Coordonner les renames. |
| Plusieurs publishers même branche, pas de review | Race condition : un push refusé pour cause de FF, le publisher doit ré-essayer (FilterMate refait `pull --ff-only` automatiquement au publish suivant) |
| Mode `Local clone` sur partage SMB/NFS | Pas de garantie d'atomicité si deux publishers écrivent en même temps. Préférer Git distant pour > 1 publisher. |
| PAT expiré côté publisher | Push échoue avec message "401 Unauthorized" ou "could not read Username". Recréer l'authcfg, pas besoin de toucher au repo. |

---

## 7 · Migration / suppression

**Renommer une collection** :
1. `git mv collections/old-name collections/new-name`
2. Updater le `name` dans `collection.json` si besoin
3. Coordonner avec les publishers : ils doivent éditer `target_collection` dans **Manage repos**

**Supprimer une collection** :
1. `git rm -r collections/<name>` côté admin
2. Les consommateurs qui font *Update* depuis Resource Sharing perdent la collection
3. Les forks déjà importés en local restent — ils sont indépendants du dépôt source

**Migrer vers un autre hébergeur** : `git remote set-url origin <new-url>` côté admin + nouveau push. Côté publishers : éditer `git_url` dans **Manage repos**, garder `local_clone` pour préserver le clone existant.
