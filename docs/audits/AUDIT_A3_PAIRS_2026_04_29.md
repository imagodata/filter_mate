# Audit A3 — Analyse comparative des 5 paires de services dupliqués (2026-04-29)

Suite au revert 2026-03-25 (`517b66b8` annulant les phases 3-6 d'une consolidation), 5 paires de services se côtoient dans `core/services/`. Audit deep 2026-04-23 (issue #39) a flaggé le besoin de triage, audit 2026-04-29 (A3) a confirmé.

Ce rapport documente l'analyse de chaque paire pour préparer la décision produit. **Aucun code n'est modifié** : chaque action restante demande validation fonctionnelle.

## Synthèse

| # | A (LOC) | B (LOC) | Callers A | Callers B | Recommandation | Risque |
|---|---------|---------|-----------|-----------|----------------|--------|
| 1 | `filter_service` (795) | `filter_application_service` (204) | 10+ | 1 | **STATU QUO** | LOW |
| 2 | `layer_service` (768) | `layer_lifecycle_service` (942) | 0 | 5 | **A à supprimer** | HIGH |
| 3 | `buffer_service` (470) | `source_subset_buffer_builder` (444) | 2 | 1 | **Fusion** | MED |
| 4 | `filter_parameter_builder` (518) | `layer_filter_builder` (348) | 1 | 1 | **Fusion** | LOW |
| 5 | `expression_service` (832) | `backend_expression_builder` (750) | 6 | 1 | **STATU QUO** | LOW |

**Total LOC potentiellement supprimables** : ~1 800 LOC (paires 2/3/4). Paires 1 et 5 restent en place.

---

## Paire 1 — `filter_service` vs `filter_application_service`

**Descriptions** :
- A : *Main orchestration service for filter operations. PURE PYTHON, NO QGIS dependencies.*
- B : *Service for applying and removing subset filters on layers, history management, Spatialite operations.*

**Callers** :
- A : `adapters/app_bridge.py`, `adapters/task_bridge.py`, `adapters/qgis/tasks/filter_task.py`, `infrastructure/di/providers.py`, 5 `ui/controllers/*` → **10+ callers**
- B : `filter_mate_app.py` → **1 caller**

**Responsabilités** : A est un orchestrateur pure-Python (FilterRequest → FilterResponse), B est un adaptateur QGIS (manipulation `QgsVectorLayer`, history Spatialite).

**Recommandation** : **STATU QUO**. Séparation domaine/adaptateur correcte. Fusionner mélangerait logique métier et couche d'application.

**Risque** : LOW (séparé = clarification des responsabilités).

---

## Paire 2 — `layer_service` vs `layer_lifecycle_service`

**Descriptions** :
- A : *Layer Management Business Logic. Centralizes validation, preparation, state. Extracted from filter_mate_dockwidget.py (MIG-077).*
- B : *Manages the complete lifecycle of layers within FilterMate: validation, filtering, project init, PostgreSQL session cleanup.*

**Callers** :
- A : **aucun import direct** (sauf relatif dans `core/services/__init__.py`)
- B : `filter_mate_app.py` (5 appels) → **1 caller actif**

**Responsabilités chevauchantes** :
- A : `filter_usable_layers()`, `validate_layers()`, enum `LayerValidationStatus`
- B : `filter_usable_layers()` (méthode identique), `handle_layers_added()`, `cleanup_postgresql_session_views()` (en plus)

**Observation clé** : `LayerService` est un zombie post-revert. `LayerLifecycleService` couvre toutes ses responsabilités + les events de lifecycle + le cleanup PG.

**Recommandation** : **A à supprimer**. Avant : vérifier l'équivalence des deux implémentations de `filter_usable_layers()` et que l'import via `core/services/__init__.py` n'est pas utilisé par un caller dormant.

**Risque** : HIGH — un appel indirect via le `__init__` peut exister.

**Action proposée** :
1. Diff fonctionnel `filter_usable_layers` A vs B (validation produit nécessaire si comportement diverge).
2. Grep large : `LayerService\b`, `from .layer_service import` dans tout le repo, y compris `tests/` et `extensions/`.
3. Si zéro caller actif : supprimer + tests.

---

## Paire 3 — `buffer_service` vs `source_subset_buffer_builder`

**Descriptions** :
- A : *Buffer Service. Pure Python buffer calculation logic and geometry simplification.*
- B : *SourceSubsetBufferBuilder (Phase 14.5). Initializes source subset expression and buffer parameters.*

**Callers** :
- A : `core/services/geometry_preparer.py`, `core/tasks/geometry_handler.py` → **2 callers**
- B : `core/tasks/initialization_handler.py` → **1 caller**

**Observation clé** : B est un builder/factory qui retourne un `BufferConfig` (classe de A). C'est de la duplication de **construction**, pas de logique.

**Recommandation** : **Fusion**. Intégrer le factory de B comme classmethod ou méthode de A : `BufferService.build_from_source_subset(...)`. Migration : changer l'import dans `initialization_handler.py`.

**Risque** : MED (simple refactor, faible surface).

**Action proposée** :
1. Vérifier que `BufferConfig` retourné par B est strictement équivalent à celui qu'aurait construit A.
2. Ajouter classmethod `BufferService.build_from_source_subset()` qui réplique la logique de B.
3. Migrer `initialization_handler.py` vers la classmethod.
4. Supprimer `source_subset_buffer_builder.py`.

---

## Paire 4 — `filter_parameter_builder` vs `layer_filter_builder`

**Descriptions** :
- A : *FilterParameterBuilder (Phase 14.4). Initializes parameters needed for source layer filtering: auto-fill metadata, provider detection, schema validation.*
- B : *Layer Filter Builder for FilterMate v4.6. Extracts and validates layers for geometric filtering, auto-fills missing properties.*

**Callers** :
- A : `core/tasks/initialization_handler.py` → **1 caller**
- B : `filter_mate_app.py` → **1 caller**

**Observation clé** : Deux contextes (source params vs target layers list) avec patterns "builder" similaires. Peu d'overlap direct, mais l'unification simplifierait l'architecture.

**Recommandation** : **Fusion**. Créer `FilterConfigBuilder` qui fournit les deux capabilities (source params + target validation).

**Risque** : LOW — 2 callers seulement, patterns proches.

**Action proposée** :
1. Concevoir l'API unifiée (deux factory methods distinctes ou méthodes de la classe).
2. Migrer les 2 callers en une seule passe.
3. Supprimer les 2 anciens fichiers.

---

## Paire 5 — `expression_service` vs `backend_expression_builder`

**Descriptions** :
- A : *Expression Service. Core service for expression parsing, validation, and conversion. PURE PYTHON, NO QGIS.*
- B : *Backend Expression Builder (Phase 14.1). Builds filter expressions for different backends: PostgreSQL, Spatialite, OGR.*

**Callers** :
- A : `adapters/app_bridge.py`, `core/services/filter_service.py`, `core/tasks/expression_facade_handler.py`, `core/tasks/executors/attribute_filter_executor.py`, `infrastructure/database/sql_utils.py`, `infrastructure/di/providers.py` → **6 callers**
- B : `core/tasks/filter_task.py` → **1 caller**

**Observation clé** : Séparation nette par couche fonctionnelle. A = parsing/validation générique. B = code generation backend-spécifique (PostgreSQL EXISTS mode, MV optimization, Spatialite syntax). B utilise A pour validation pré-construction.

**Recommandation** : **STATU QUO**. Séparation maintient la pure-Python strategy et la testabilité headless de A.

**Risque** : LOW (aucune dépendance bidirectionnelle).

---

## Plan d'action consolidé

**Sprint 1 (LOW risk, ~3-4h)** :
- Paire 4 : créer `FilterConfigBuilder`, migrer 2 callers, supprimer les 2 anciens.

**Sprint 2 (MED risk, ~2-3h)** :
- Paire 3 : intégrer `source_subset_buffer_builder` comme classmethod de `BufferService`, supprimer le fichier.

**Sprint 3 (HIGH risk, demande validation produit)** :
- Paire 2 : audit fonctionnel `filter_usable_layers` A vs B (diff de comportement), puis suppression `LayerService` si équivalent.

**Pas d'action** :
- Paires 1 et 5 : architecturalement saines, garder séparées.

**Total LOC supprimables si tout est exécuté** : ~1 800 LOC sur les 5 paires actuelles (3 362 LOC).
