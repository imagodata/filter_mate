# Sprint 1 - Narractive Integration Foundation

**Dates :** 2026-03-24 -> 2026-04-07 (2 semaines)
**Milestone GitHub :** [Sprint 1 - Narractive Integration Foundation](https://github.com/imagodata/filter_mate/milestone/1)
**Version FilterMate cible :** 4.7.0 (branche `feature/narractive-public-api`)

---

## Objectif du sprint

Poser les **fondations techniques** de l'intégration entre Narractive et FilterMate. A l'issue de ce sprint, une `FilterMatePublicAPI` stable et testée doit exister, et le protocole de communication inter-plugin doit être documenté et validé.

Les Epics 2 et 4 (UI Narractive, mode narration) ne démarrent qu'en Sprint 2.

---

## Issues du Sprint 1

### Epic 1 - Architecture (Issues #6, #7, #8)

| Issue | Titre | Points | Priorité |
|-------|-------|--------|----------|
| #6 | Protocole d'API inter-plugin (signaux Qt vs appel direct) | 5 | Critique |
| #7 | Point d'entrée FilterMate pour usage externe | 3 | Haute |
| #8 | Contrat d'interface IFilterMatePublicAPI | 3 | Haute |

### Epic 3 - FilterMatePublicAPI (Issues #14, #15, #16, #17)

| Issue | Titre | Points | Priorité |
|-------|-------|--------|----------|
| #14 | Créer FilterMatePublicAPI - façade ports/adapters | 8 | Critique |
| #15 | Implémenter apply_filter() | 5 | Critique |
| #16 | Implémenter get_active_filters() et clear_filters() | 3 | Haute |
| #17 | Signaux Qt FilterMatePublicAPI | 5 | Haute |

### Epic 5 - Tests (Issue #23)

| Issue | Titre | Points | Priorité |
|-------|-------|--------|----------|
| #23 | Tests unitaires FilterMatePublicAPI | 5 | Haute |

**Total Sprint 1 : 37 points**

---

## User Stories

### US-01 : Protocole de communication inter-plugin

**En tant que** Product Owner,
**je veux** qu'un protocole de communication clair soit défini entre Narractive et FilterMate,
**afin de** garantir un couplage faible et une architecture évolutive.

**Criteres d'acceptance :**
- Un ADR (Architecture Decision Record) est rédigé dans `/docs/narractive-integration/adr-001-inter-plugin-protocol.md`
- Le pattern retenu est validé par l'équipe (option hybride recommandee : appel direct + signaux Qt)
- Les cas d'erreur sont documentés (plugin absent, version incompatible, couche introuvable)
- Compatibilite QGIS 3.22+ et QGIS 4.x (Qt5 et Qt6) verifiee

---

### US-02 : Point d'entrée public FilterMate

**En tant que** développeur Narractive,
**je veux** accéder à FilterMate via `qgis.utils.plugins["filter_mate"].get_public_api()`,
**afin de** récupérer une façade stable sans connaitre l'architecture interne.

**Criteres d'acceptance :**
- La methode `get_public_api()` existe sur la classe `FilterMate` dans `filter_mate.py`
- Elle retourne toujours la meme instance (singleton par session)
- Elle expose `version` (semver) et `capabilities` (dict des features)
- Un exemple d'utilisation est documente

---

### US-03 : Contrat d'interface IFilterMatePublicAPI

**En tant que** architecte,
**je veux** qu'un contrat formel `IFilterMatePublicAPI` soit défini comme port dans l'architecture hexagonale,
**afin que** toute implémentation future respecte le même contrat.

**Criteres d'acceptance :**
- `IFilterMatePublicAPI` (ABC) existe dans `/core/ports/public_api_port.py`
- Toutes les methodes sont declarees avec leurs signatures completes et docstrings
- Les exceptions `LayerNotFoundError` et `InvalidFilterExpressionError` sont dans `/core/domain/exceptions.py`
- Le contrat est revue et signé par l'equipe avant implementation

---

### US-04 : Appliquer un filtre via l'API publique

**En tant que** plugin Narractive,
**je veux** appeler `api.apply_filter("communes", "region = 'Normandie'")`,
**afin que** la couche soit filtrée dans le projet QGIS courant.

**Criteres d'acceptance :**
- La methode resout la couche par nom dans `QgsProject.instance()` (insensible a la casse)
- L'expression est validee via `QgsExpression` avant application
- L'appel est delegue au `FilterExecutorPort` existant (pas de duplication)
- Le signal `filter_applied(layer_name, expr)` est emis apres succes
- Le `source_plugin` est trace dans les logs
- Les 4 backends sont supportes (PostgreSQL, Spatialite, GeoPackage, Shapefile)
- `LayerNotFoundError` est levee si la couche n'existe pas
- `InvalidFilterExpressionError` est levee si l'expression est invalide
- Expression vide `""` supprime le filtre existant (comportement coherent avec clear_filter)

---

### US-05 : Interroger et supprimer les filtres via l'API

**En tant que** plugin Narractive,
**je veux** pouvoir lire l'état des filtres actifs et les supprimer,
**afin de** gérer proprement les transitions entre steps de narration.

**Criteres d'acceptance :**
- `get_active_filters()` retourne les `subsetString()` reels des couches vectorielles du projet
- `get_filter_for_layer()` est insensible a la casse
- `clear_filter()` appelle `setSubsetString("")` sur la couche ciblee
- `clear_all_filters()` retourne le nombre exact de filtres supprimes
- `clear_filter()` et `clear_all_filters()` emettent le signal `filter_cleared`

---

### US-06 : Signaux Qt pour notifier des changements de filtre

**En tant que** plugin Narractive,
**je veux** recevoir des signaux Qt quand FilterMate change l'etat des filtres,
**afin de** mettre a jour mon UI en temps reel.

**Criteres d'acceptance :**
- Signaux `filter_applied`, `filter_cleared`, `error_occurred`, `about_to_unload` declares sur `FilterMatePublicAPI`
- `filter_applied` est emis meme quand le filtre vient de l'UI FilterMate (pas seulement de l'API)
- `about_to_unload` est emis dans `FilterMate.unload()` avant la destruction
- Codes d'erreur normalises : `LAYER_NOT_FOUND`, `INVALID_EXPRESSION`, `BACKEND_ERROR`, `PERMISSION_DENIED`
- Pas de memory leak : deconnexion propre testee via `weakref`
- Compatibilite Qt5/Qt6 verifiee

---

### US-07 : Suite de tests unitaires FilterMatePublicAPI

**En tant que** développeur,
**je veux** une suite de tests unitaires complete pour `FilterMatePublicAPI`,
**afin de** garantir la stabilite du contrat d'interface.

**Criteres d'acceptance :**
- Fichier `/tests/test_public_api/test_filter_mate_public_api.py` cree
- Groupes de tests : proprietes, apply_filter, clear, get_active_filters, signaux
- Couverture >= 85% sur `filter_mate_public_api.py`
- Tests des signaux via `pytest-qt` et `qtbot.waitSignal`
- Tous les tests passent sans QGIS installe (mock total PyQGIS)
- Temps d'execution total < 30 secondes

---

## Architecture d'intégration recommandee

### Pattern retenu : Hybride (appel direct + signaux Qt)

Ce pattern combine le meilleur des deux approches :
- Les **appels directs** pour les actions synchrones (appliquer un filtre, lire l'etat)
- Les **signaux Qt** pour les notifications asynchrones (filtre change, erreur, unload)

```
Narractive Plugin                          FilterMate Plugin
     │                                           │
     │  qgis.utils.plugins["filter_mate"]        │
     │  .get_public_api()           ──────────►  │ FilterMatePublicAPI
     │                                           │   (Facade / Adapter)
     │                                           │         │
     │  api.apply_filter(               ────────►│         ▼
     │      "communes",                          │   FilterExecutorPort
     │      "region='Normandie'",                │         │
     │      source_plugin="narractive"           │         ▼
     │  )                                        │   Backend (PG/SL/GPKG/SHP)
     │                                           │
     │  ◄── filter_applied signal ──────────────│ (PyQt Signal)
     │  ◄── filter_cleared signal ──────────────│
     │  ◄── error_occurred signal ──────────────│
     │  ◄── about_to_unload signal ─────────────│
     │                                           │
```

### Fichiers a créer dans FilterMate

```
filter_mate.py                              # + get_public_api() methode
core/
  ports/
    public_api_port.py                      # NOUVEAU : IFilterMatePublicAPI (ABC)
  domain/
    exceptions.py                           # + LayerNotFoundError, InvalidFilterExpressionError
adapters/
  public_api/
    __init__.py                             # NOUVEAU
    filter_mate_public_api.py               # NOUVEAU : FilterMatePublicAPI implementation
tests/
  test_public_api/
    __init__.py                             # NOUVEAU
    test_filter_mate_public_api.py          # NOUVEAU : tests unitaires
docs/
  narractive-integration/
    sprint-1.md                             # CE FICHIER
    adr-001-inter-plugin-protocol.md        # A créer en Sprint 1
```

### Gestion du cycle de vie

```python
# Narractive - connexion au demarrage
class NarractivePlugin:
    def initGui(self):
        self._filtermate_adapter = FilterMateAdapter()
        if self._filtermate_adapter.connect():
            api = self._filtermate_adapter._api
            api.filter_applied.connect(self._on_filter_applied)
            api.about_to_unload.connect(self._on_filtermate_unloading)

    def _on_filtermate_unloading(self):
        # Deconnexion propre avant destruction de FilterMate
        try:
            api = qgis.utils.plugins["filter_mate"].get_public_api()
            api.filter_applied.disconnect(self._on_filter_applied)
        except (KeyError, RuntimeError):
            pass
        self._filtermate_adapter.disconnect()

    def unload(self):
        self._on_filtermate_unloading()
```

### Gestion de compatibilite de version

```python
# Dans FilterMateAdapter (Narractive)
MINIMUM_API_VERSION = (1, 0, 0)

def connect(self) -> bool:
    if "filter_mate" not in qgis.utils.plugins:
        return False
    plugin = qgis.utils.plugins["filter_mate"]
    if not hasattr(plugin, "get_public_api"):
        return False  # FilterMate trop ancien (< 4.7.0)
    api = plugin.get_public_api()
    api_version = tuple(int(x) for x in api.version.split("."))
    if api_version < self.MINIMUM_API_VERSION:
        iface.messageBar().pushWarning(
            "Narractive",
            f"FilterMate API {api.version} trop ancienne. Version {'.'.join(map(str, self.MINIMUM_API_VERSION))} requise."
        )
        return False
    self._api = api
    return True
```

---

## Risques identifies

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| Architecture interne FilterMate ne permet pas d'exposer les bons ports facilement | Faible | Haut | Etudier les ports existants avant US-03 |
| Signaux Qt incompatibles Qt5/Qt6 | Moyenne | Moyen | Tester en CI sur les deux versions |
| Performance degradee sur grands projets (get_active_filters itere toutes les couches) | Moyenne | Faible | Ajouter un cache local dans FilterMatePublicAPI |
| Narractive non disponible pour tests d'integration avant Sprint 2 | Haute | Faible | Utiliser MockNarractivePlugin dans les tests |

---

## Definition of Done (DoD)

Une issue est "Done" quand :
- Le code est merge sur la branche `feature/narractive-public-api`
- Les tests unitaires associes passent en CI
- La couverture de code ne regresse pas (>= niveau precedent)
- La docstring est complete (Google style)
- La PR a ete reviewee par au moins un autre developpeur
- Les criteres d'acceptance de la user story sont tous coches

---

## Velocity de reference

- Sprint precedent : non disponible (premier sprint d'integration)
- Capacite estimee Sprint 1 : 37 points (2 devs x 2 semaines)
- Buffer risque : 10% reserve pour imprevu technique

---

## Liens utiles

- Milestone GitHub : https://github.com/imagodata/filter_mate/milestone/1
- Epic Architecture : https://github.com/imagodata/filter_mate/issues/5
- Epic FilterMatePublicAPI : https://github.com/imagodata/filter_mate/issues/13
- Epic Tests : https://github.com/imagodata/filter_mate/issues/22
- Ports existants FilterMate : `/project/core/ports/`
- Architecture hexagonale FilterMate : `/project/core/`, `/project/adapters/`
