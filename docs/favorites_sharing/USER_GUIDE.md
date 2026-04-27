# Guide utilisateur — Partage de favoris FilterMate

FilterMate permet de partager des **collections de favoris** (filtres + configs spatiales) entre utilisateurs via des dépôts Git.
Trois rôles, trois flux :

| Rôle | Accès | Outils |
|---|---|---|
| **Consommateur** | Lecture publique | Plugin QGIS *Resource Sharing* + menu ★ |
| **Publisher** | Écriture (token) | FilterMate "Manage repos" + Quick publish |
| **Admin du dépôt** | Écriture/admin Git | GitHub/GitLab/Gitea, voir [REPO_SETUP.md](REPO_SETUP.md) |

> Pré-requis : plugin QGIS officiel *Resource Sharing* installé. Sans lui, FilterMate fonctionne en local mais n'expose pas les collections distantes.

---

## A · Consommer une collection partagée

### A.1 · S'abonner à une collection

1. Ouvrir le plugin **Resource Sharing** (menu *Plugins → Resource Sharing*).
2. Onglet **Settings → Add repository** → coller l'URL Git fournie par l'admin (ex. `https://github.com/acme/acme-collections.git`).
3. Onglet **All Collections** → la collection apparaît → cliquer **Install**.

À l'install, Resource Sharing clone le dépôt et FilterMate scanne automatiquement le sous-arbre `filter_mate/favorites/` au prochain chargement de projet.

### A.2 · Parcourir et importer un favori partagé

Menu favoris ★ → **📡 Import from Resource Sharing…**

Le picker affiche :
- 🔍 **Recherche** par nom / description / collection / auteur / tags
- **Author** : combobox de filtrage par auteur de collection
- Liste : `★ Nom du favori   · auteur` (badge auteur visible)

Sélectionner → bouton **⑂ Fork to my project** → choisir le nom local → le favori est ajouté à la base SQLite du projet courant.

Note technique : le fork **rebinde** les couches via leur signature portable (`postgres::schema.table`, `spatialite::table`, `ogr::layername`). Si la couche cible n'existe pas dans le projet, un warning est loggé mais le favori est créé.

### A.3 · Limiter aux collections approuvées (admin)

Pour une équipe IT qui veut imposer une whitelist :

```json
"EXTENSIONS": {
  "favorites_sharing": {
    "allowed_collections": {"value": ["acme-favorites", "internal-curated"]}
  }
}
```

Quand non vide, FilterMate ignore toutes les collections dont le nom de dossier n'est pas listé.

---

## B · Publier (devenir publisher)

### B.1 · Pré-requis : token d'authentification

Pour pousser sur le dépôt il faut un **Personal Access Token** (GitHub) ou équivalent.

| Hébergeur | Création | Scope minimum |
|---|---|---|
| GitHub | Settings → Developer settings → PAT | `repo` |
| GitLab | Preferences → Access Tokens | `write_repository` |
| Gitea  | Settings → Applications → Generate token | `write:repository` |

### B.2 · Stocker le token dans QGIS Auth Manager (chiffré)

1. QGIS → **Settings → Options → Authentication** → **➕** (Add new authentication configuration)
2. Remplir :
   - **Name** : `acme-pat` (libre, sert d'étiquette)
   - **Resource** : laisser vide
   - **Authentication method** : **Basic authentication**
   - **Username** : peu importe (ex. `git`) — GitHub ne l'utilise pas
   - **Password** : coller le PAT (`ghp_...`)
3. **Save** → noter l'**Id** généré (10 caractères, ex. `qg1xy7w`)

Le token n'apparaît jamais en clair dans la config FilterMate. Le master-password QGIS ne sera demandé qu'au premier `publish`.

### B.3 · Configurer le dépôt dans FilterMate

Menu favoris ★ → **🌐 Manage Resource Sharing repos…** → **➕ Add**

| Champ | Exemple | Notes |
|---|---|---|
| **Name** | `Acme team` | Affiché dans les menus |
| **Git URL** | `https://github.com/acme/acme-collections.git` | Vide = mode local-only (write sans push) |
| **Branch** | `main` | Vide = HEAD du remote |
| **Local clone** | (vide) | Auto = `[profil QGIS]/FilterMate/repos/<slug>` |
| **Collection** | `acme-favorites` | Sous-dossier sous `collections/` |
| **Authentication** | sélectionner `acme-pat` | Combobox QgsAuthConfigSelect |
| **Use as default** | ☑ | Facultatif mais permet le Quick Publish |

Bouton **🔌 Test connection** → doit afficher `✔ OK — remote reachable.` Sinon, vérifier l'URL et le token.

### B.4 · Publier — flux complet (avec choix par favori)

Menu ★ → **📤 Publish to Resource Sharing…**

1. **Target collection** : sélectionner le repo configuré (apparaît avec 🌐 et le statut)
2. **Bundle file name** : nom court du fichier (ex. `zones_bruxelles`)
3. **Collection metadata** : nom, auteur, licence, tags, homepage, description
   - L'auteur est crucial : c'est ce qui peuplera le filtre auteur côté consommateurs
4. **Favorites to include** : cocher les favoris à embarquer (bouton "Select all")
5. ☐ **Overwrite existing bundle** : à cocher si on republie sur le même nom
6. **📤 Publish**

FilterMate exécute : `clone si besoin → pull --ff-only → écrire le bundle → git add → commit → push`.

En cas d'erreur (conflit de merge, push refusé, token expiré) : message + bouton **Open clone…** pour résoudre dans tes outils Git habituels. **FilterMate ne fait jamais de force-push ni de rebase auto.**

### B.5 · Quick Publish (1 clic)

Menu ★ → **🚀 Quick publish to default repo**

Apparaît seulement si :
- Un repo `is_default = true` est configuré
- Au moins 1 favori existe dans le projet

Confirme une fois → publie **TOUS les favoris du projet** vers le dépôt par défaut, avec les métadonnées par défaut (`default_publish_metadata` dans la config). Bypass complet du dialog.

Idéal pour les workflows "j'ai modifié 3 favoris, je sync".

### B.6 · Métadonnées par défaut (gain de temps)

Pour ne pas re-saisir auteur/licence à chaque publish :

```json
"EXTENSIONS": {
  "favorites_sharing": {
    "default_publish_metadata": {
      "value": {
        "author": "Équipe Géomatique ACME",
        "license": "CC-BY-4.0",
        "homepage": "https://geo.acme.example.org"
      }
    }
  }
}
```

Ces valeurs pré-remplissent le dialog et sont utilisées telles quelles par Quick Publish.

---

## C · Cas d'usage hors-ligne (fallback A)

Pas de Git distant disponible (intranet sans GitHub, restrictions firewall) ?

Dans **Manage repos → Add** : laisser **Git URL vide**, renseigner un **Local clone** sur un partage réseau (SMB / NFS / Drive sync) :

```
Local clone : /mnt/equipe/qgis-collections
Collection   : acme-favorites
```

FilterMate **écrit** le bundle dans ce dossier sans tenter de push. Les autres utilisateurs configurent la même collection en pointant le même partage (avec resource_sharing_root personnalisé) et voient les bundles via leur propre scan.

---

## D · Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `git command failed (exit 128) ... could not read Username for…` | Token manquant ou révoqué | Recréer l'authcfg, refaire **Test connection** |
| `[REDACTED]` dans les logs | Volontaire — scrubbing des secrets | Aucune action, c'est normal |
| Statut repo `⚪ not cloned` | Premier publish jamais lancé | Lancer un publish (clone auto) ou cliquer Test connection |
| Statut repo `⚠ invalid` | `local_clone` introuvable / non absolu | Éditer le repo, vérifier le chemin |
| Picker vide après install d'une collection | Scan pas rafraîchi | Bouton **🔄 Rescan** ou recharger le projet |
| `target_collection ... escapes local_clone — refusing` | `target_collection` contient `..` | Editer en chemin relatif simple (`acme-favorites`, pas `../acme`) |
| Le master-password QGIS demande à chaque publish | `Settings → Auth Manager → "Store password in keychain"` désactivé | Activer pour cache de session |

---

## E · Format de bundle (référence)

Voir [README technique](../../extensions/favorites_sharing/README.md#bundle-format-schema-v3) pour le détail v3.

Minimum pour un bundle valide :

```json
{
  "schema": "filter_mate.favorites",
  "schema_version": 3,
  "collection": {"name": "X", "author": "Y", "license": "CC-BY-4.0"},
  "favorites": [
    {"name": "Mon filtre", "expression": "\"col\" = 'val'"}
  ]
}
```

FilterMate **valide** chaque bundle au scan via le validateur intégré. Les bundles malformés sont loggés et ignorés (jamais ingérés en DB).
