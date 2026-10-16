# FilterMate — Audit & Plan de Production : Serie de Tutoriels Video

**Version** : 4.6.1 | **Date** : 14 Mars 2026
**Auteur** : Audit automatise (Claude Code)
**Statut** : PLAN INITIAL — A valider par PO (Jordan)

---

## 1. ANALYSE DE L'EXISTANT

### 1.1 Documentation video actuelle
Le fichier `VIDEO_SCRIPT.md` contient **1 seule video** (8-10 min) de type "overview".
Elle couvre : intro, installation, interface, demo filtrage, exploration, export, multi-backend, architecture, conclusion.

### 1.2 Lacunes identifiees

| Aspect du plugin | Couvert dans l'overview ? | Necessite un tutoriel dedie ? |
|---|:---:|:---:|
| Installation & premier lancement | Partiellement (30s) | Oui |
| Filtrage geometrique basique | Oui (2 min) | Oui — approfondi |
| Predicats spatiaux (8 types) | Mentionne | Oui — cas par cas |
| Buffer dynamique & expressions | Mentionne | Oui |
| Combine operators (AND/OR/REPLACE) | Non | Oui |
| Exploration vecteur | Partiellement | Oui |
| Selection multiple & custom | Non | Oui |
| Favoris (CRUD, import/export) | Mentionne | Oui |
| Undo/Redo (100 etats) | Mentionne | Integrer |
| Export GeoPackage avec projet | Oui (1 min) | Oui — approfondi |
| Export GPKG + KML (avec styles QML/SLD) | Non | Oui |
| Multi-backend & optimisation | Oui (45s) | Oui — approfondi |
| PostgreSQL avance (MV, PK, cleanup) | Non | Oui |
| Configuration & personnalisation | Non | Oui |
| Theme sombre & i18n | Mentionne | Integrer |
| Edit mode awareness | Non | Integrer |
| Architecture technique | Oui (45s) | Oui — dev audience |
| Cas d'usage metier | Non | Oui |

### 1.3 Recommandation

Produire **10 tutoriels** organises en 4 niveaux.
Duree totale estimee : **~75 minutes** de contenu.

---

## 2. PLAN DE LA SERIE — VUE D'ENSEMBLE

```mermaid
mindmap
  root((FilterMate<br/>Tutorial Series<br/>10 Videos))
    DEBUTANT
      V01 — Installation & Premier Pas
      V02 — Filtrage Geometrique : Les Bases
      V03 — Explorer Vos Donnees
    INTERMEDIAIRE
      V04 — Predicats Spatiaux & Buffer
      V05 — Favoris & Historique
      V06 — Export GeoPackage & KML Pro
    AVANCE
      V07 — Multi-Backend & Optimisation
      V08 — PostgreSQL Power User
    EXPERT / DEV
      V09 — Configuration Avancee
      V10 — Architecture & Contribution
```

---

## 3. FICHES DETAILLEES PAR VIDEO

---

### VIDEO 01 — Installation & Premier Pas
**Niveau** : Debutant | **Duree** : 5-7 min | **Prerequis** : QGIS installe

#### Objectifs pedagogiques
- Installer FilterMate depuis le depot QGIS
- Comprendre l'architecture : Exploring Zone, Toolbox (Filtering/Exporting), Action Bar (6 boutons dont About)
- Decouvrir les 6 boutons de l'Action Bar dont le bouton About (toujours actif)
- Effectuer un premier filtrage simple
- Decouvrir le theme sombre et le changement de langue
- Activer le mode verbose comme outil d'apprentissage temps reel
- Comprendre la persistence automatique de la configuration (SQLite)
- Utiliser le panneau Log Messages de QGIS (onglet FilterMate)

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Hook : "Filtrer 1M d'entites en 2 secondes" | Voix + texte |
| 0:15 | Installation via Plugin Manager | Capture QGIS |
| 0:45 | Installation psycopg2 (optionnel) | Terminal |
| 1:15 | Premier lancement — dock widget apparait | Capture QGIS |
| 1:45 | Architecture : Exploring Zone + Toolbox (FILTERING/EXPORTING) + Action Bar (6 boutons) | Capture annotee |
| 3:00 | Premier filtrage : Shapefile local | Demo live |
| 4:30 | Theme sombre automatique | Capture QGIS |
| 5:00 | Changement de langue (22 langues) | Capture QGIS |
| 5:20 | Activer le mode verbose pour l'apprentissage (FEEDBACK_LEVEL) | Capture QGIS |
| 5:40 | QGIS Log Messages Panel → onglet FilterMate (View → Panels → Log Messages) | Capture QGIS |
| 6:00 | Auto-detection du champ d'affichage (get_best_display_field, 6 niveaux) | Demo live |
| 6:20 | Config sauvegardee automatiquement entre sessions (SQLite fm_project_layers_properties) | Voix + schema |
| 6:30 | Ou trouver l'aide / GitHub / docs | Ecran liens |

#### Diagramme — Interface Principale

```mermaid
graph TD
    QGIS["QGIS Desktop"] --> INSTALL["Plugins > Gerer les extensions"]
    INSTALL --> SEARCH["Rechercher 'FilterMate'"]
    SEARCH --> CLICK["Installer"]
    CLICK --> DOCK["FilterMate Dock Widget"]

    DOCK --> EZ["Exploring Zone<br/>Parcourir les entites"]
    DOCK --> TOOLBOX["Toolbox"]
    TOOLBOX --> TAB_FILT["Onglet FILTERING<br/>Source + Cible + Predicat"]
    TOOLBOX --> TAB_EXP["Onglet EXPORTING<br/>GeoPackage & KML"]
    DOCK --> ACTIONBAR["Action Bar (6 boutons)<br/>dont About (toujours actif)"]

    DOCK --> SIDEBAR["Barre laterale<br/>Undo / Redo / Favoris<br/>Backend / Config"]

    style DOCK fill:#1976D2,color:#fff
    style EZ fill:#7B1FA2,color:#fff
    style TOOLBOX fill:#388E3C,color:#fff
    style TAB_FILT fill:#388E3C,color:#fff
    style TAB_EXP fill:#F57C00,color:#fff
    style ACTIONBAR fill:#1565C0,color:#fff
```

#### Captures QGIS requises
1. Plugin Manager avec FilterMate visible
2. Dock widget vide au premier lancement
3. Exploring Zone + Toolbox (FILTERING/EXPORTING) + Action Bar en vue rapprochee
4. Barre laterale avec icones annotees
5. Menu de selection de langue
6. Basculement theme clair/sombre

#### Donnees de demo
- Shapefile departements France (polygones, ~100 entites)
- Shapefile communes (polygones, ~35 000 entites)
- Pas besoin de PostgreSQL pour cette video

---

### VIDEO 02 — Filtrage Geometrique : Les Bases
**Niveau** : Debutant | **Duree** : 8-10 min | **Prerequis** : V01

#### Objectifs pedagogiques
- Comprendre source vs cible
- Appliquer un filtre geometrique simple (intersects)
- Comprendre quand le bouton Filter est desactive (onglet Export actif, aucune feature selectionnee, filtrage en cours)
- Distinguer Unfilter (retire le filtre, utilise l'historique si disponible) et Reset (remet l'etat d'exploration FilterMate aux defaults, ≠ CRS ou styles QGIS)
- Comprendre les deux niveaux de Combine Operators : Source layer operator (combiner plusieurs features sources) et Other layers operator (combiner entre couches cibles)
- Gerer le conflit Edit Mode (popup de resolution quand la couche est en mode edition)

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Rappel : qu'est-ce que le filtrage spatial ? | Diagramme anime |
| 0:30 | Charger 2 couches : routes + batiments | Capture QGIS |
| 1:00 | Selectionner source = route specifique | Demo live |
| 1:30 | Selectionner cible = batiments | Demo live |
| 2:00 | Appliquer "Intersects" | Demo live |
| 3:00 | Resultat : batiments filtres | Capture QGIS |
| 3:30 | Bouton Unfilter — retire le filtre, utilise l'historique si disponible | Demo live |
| 4:00 | Bouton Reset — remet l'etat d'exploration FilterMate aux defaults (≠ CRS ou styles QGIS) | Demo live |
| 4:30 | Niveau 1 : Source layer operator (REPLACE/AND/OR) — combiner plusieurs features sources | Demo live |
| 5:00 | Niveau 2 : Other layers operator — combiner entre les couches cibles | Demo live |
| 5:30 | Edit Mode Conflict : si la couche est en edition, FilterMate affiche un popup de resolution | Demo live |
| 6:00 | Exercice : filtrer communes d'un departement | Demo live |
| 7:30 | Exercice : enchainer 2 filtres avec AND | Demo live |

#### Diagramme — Concept Source/Cible

```mermaid
flowchart LR
    subgraph SOURCE["COUCHE SOURCE"]
        direction TB
        S1["Selection geometrique<br/>(ex: une route)"]
    end

    subgraph PREDICAT["PREDICAT SPATIAL"]
        direction TB
        P1["Intersects ?<br/>Contains ?<br/>Within ?<br/>Touches ?"]
    end

    subgraph CIBLE["COUCHE(S) CIBLE"]
        direction TB
        T1["Toutes les entites<br/>testees contre la source"]
        T2["Resultat : seules les<br/>entites correspondantes<br/>restent visibles"]
    end

    SOURCE --> PREDICAT
    PREDICAT --> CIBLE

    style SOURCE fill:#1565C0,color:#fff
    style PREDICAT fill:#E65100,color:#fff
    style CIBLE fill:#388E3C,color:#fff
```

#### Diagramme — Combine Operators (2 niveaux)

```mermaid
flowchart TD
    subgraph NIVEAU1["NIVEAU 1 — Source layer operator<br/>(combiner plusieurs features sources)"]
        S1["Feature source A<br/>(ex: Route 1)"]
        S2["Feature source B<br/>(ex: Route 2)"]
        S1 --> SOP_R["REPLACE : seule la feature B active"]
        S1 --> SOP_A["AND : intersection A et B"]
        S1 --> SOP_O["OR : union A et B"]
    end

    subgraph NIVEAU2["NIVEAU 2 — Other layers operator<br/>(combiner entre couches cibles)"]
        T1["Couche cible 1<br/>(ex: Batiments)"]
        T2["Couche cible 2<br/>(ex: Parcelles)"]
        T1 --> TOP_R["REPLACE : seule la derniere couche filtree"]
        T1 --> TOP_A["AND : entites dans les deux couches"]
        T1 --> TOP_O["OR : entites dans l'une ou l'autre"]
    end

    NIVEAU1 --> NIVEAU2

    style NIVEAU1 fill:#1565C0,color:#fff
    style NIVEAU2 fill:#388E3C,color:#fff
    style SOP_R fill:#D32F2F,color:#fff
    style TOP_R fill:#D32F2F,color:#fff
```

#### Captures QGIS requises
1. Carte avec routes + batiments avant filtrage
2. Selection d'une route comme source
3. Resultat apres filtrage (batiments filtres)
4. Comparaison avant/apres (split screen)
5. Interface avec combos source/cible annotes
6. Boutons Unfilter (retire filtre, historique si dispo) / Reset (defaults exploration FilterMate) en action avec annotations
7. Menu Combine Operators niveau 1 (source) et niveau 2 (autres couches)
8. Popup Edit Mode Conflict avec options de resolution

#### Donnees de demo
- Shapefile routes (lignes, ~5 000 entites)
- Shapefile batiments (polygones, ~50 000 entites)
- Shapefile departements (polygones, reference)

---

### VIDEO 03 — Explorer Vos Donnees
**Niveau** : Debutant | **Duree** : 7-8 min | **Prerequis** : V01

#### Objectifs pedagogiques
- Naviguer dans les entites d'une couche
- Utiliser Flash, Zoom, Identify
- Modes de selection : simple, multiple, custom
- Synchronisation selection QGIS <-> FilterMate

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | A quoi sert l'onglet Exploration ? | Voix + diagramme |
| 0:30 | Auto Current Layer toggle — la combo Source suit automatiquement la couche selectionnee dans le Layers Panel | Demo live |
| 0:50 | Selectionner une couche a explorer | Demo live |
| 1:20 | Choisir un champ (nom, type, code...) | Demo live |
| 1:30 | Liste des valeurs uniques | Demo live |
| 2:00 | Flash Feature : surbrillance temporaire | Demo live |
| 2:30 | Zoom to Feature : centrer la carte | Demo live |
| 3:00 | Identify : attributs complets | Demo live |
| 3:30 | Mode selection simple | Demo live |
| 4:00 | Mode selection multiple (checkboxes) | Demo live |
| 4:30 | Mode selection custom (expression libre) | Demo live |
| 5:30 | Synchronisation avec la selection QGIS | Demo live |
| 6:30 | Lier les widgets d'exploration | Demo live |

#### Diagramme — Modes de Selection

```mermaid
flowchart TD
    EXPLORER["Onglet Exploration"]

    EXPLORER --> SIMPLE["Mode Simple<br/>1 entite a la fois"]
    EXPLORER --> MULTI["Mode Multiple<br/>Checkboxes"]
    EXPLORER --> CUSTOM["Mode Custom<br/>Expression libre"]

    SIMPLE --> EXPR1["field = 'value'"]
    MULTI --> EXPR2["field IN ('v1', 'v2', 'v3')"]
    CUSTOM --> EXPR3["Toute expression QGIS valide"]

    EXPR1 --> SYNC["Synchronisation<br/>bidirectionnelle<br/>QGIS <-> FilterMate"]
    EXPR2 --> SYNC
    EXPR3 --> SYNC

    style SIMPLE fill:#1976D2,color:#fff
    style MULTI fill:#7B1FA2,color:#fff
    style CUSTOM fill:#E65100,color:#fff
```

#### Diagramme — Outils de Navigation

```mermaid
graph LR
    subgraph TOOLS["Outils Navigation"]
        FLASH["Flash<br/>Surbrillance jaune<br/>temporaire"]
        ZOOM["Zoom To<br/>Centrer + zoom<br/>sur l'entite"]
        IDENTIFY["Identify<br/>Tous les attributs<br/>et proprietes"]
        ZOOM_SEL["Zoom Selection<br/>Vue d'ensemble<br/>des selectionnes"]
    end

    TOOLS --> MAP["Canvas QGIS"]

    style FLASH fill:#FFC107,color:#000
    style ZOOM fill:#1976D2,color:#fff
    style IDENTIFY fill:#388E3C,color:#fff
    style ZOOM_SEL fill:#7B1FA2,color:#fff
```

#### Captures QGIS requises
1. Onglet exploration avec liste d'entites
2. Flash d'une entite sur la carte (capture animee GIF)
3. Zoom sur une entite
4. Panel Identify avec attributs
5. Checkboxes en mode multi-selection
6. Champ d'expression en mode custom
7. Selection synchronisee entre table QGIS et FilterMate

---

### VIDEO 04 — Predicats Spatiaux & Buffer Dynamique
**Niveau** : Intermediaire | **Duree** : 10-12 min | **Prerequis** : V02

#### Objectifs pedagogiques
- Maitriser les 8 predicats spatiaux (Touches, Intersects, Contains, Within, Overlaps, Crosses, Disjoint, Is Within Distance)
- Comprendre quand utiliser chaque predicat
- Configurer un buffer en metres/km
- Utiliser les expressions dynamiques pour le buffer
- Buffer negatif pour filtrage inverse
- Comprendre les seuils d'auto-activation des centroïdes (cible > 5 000 features, source > 50 000 features)
- Regler les Buffer Segments (moins = plus rapide pour geometries complexes)

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Rappel : qu'est-ce qu'un predicat spatial ? | Diagramme anime |
| 0:45 | Touches — quand l'utiliser ? | Demo + schema |
| 1:30 | Intersects — le plus polyvalent | Demo + schema |
| 2:15 | Contains — source contient cible | Demo + schema |
| 3:00 | Within — cible a l'interieur de source | Demo + schema |
| 3:45 | Overlaps — chevauchement partiel | Demo + schema |
| 4:15 | Crosses — ligne coupe un polygone | Demo + schema |
| 4:45 | Disjoint — aucun contact spatial | Demo + schema |
| 5:15 | Is Within Distance — buffer implicite | Demo + schema |
| 5:45 | Seuils auto-centroide : cible > 5 000 → centroide auto ; source > 50 000 → centroide auto | Demo live |
| 6:15 | Ajouter un buffer explicite (50m, 200m, 1km) | Demo live |
| 7:30 | Buffer dynamique avec expression QGIS | Demo live |
| 8:30 | Buffer negatif (filtrage inverse) | Demo live |
| 9:00 | Buffer Segments : moins de segments = geometrie plus simple = filtrage plus rapide | Demo live |
| 9:30 | Cas d'usage : zones tampon reglementaires | Demo live |
| 11:00 | Comparaison visuelle des 8 predicats | Recapitulatif |

#### Diagramme — Les 8 Predicats Illustres

```mermaid
graph TD
    subgraph TOUCHES["TOUCHES"]
        direction LR
        T_A["Polygone A"] ---|"bord commun"| T_B["Polygone B"]
    end

    subgraph INTERSECTS["INTERSECTS"]
        direction LR
        I_A["Polygone A"] ---|"tout contact<br/>spatial"| I_B["Polygone B"]
    end

    subgraph CONTAINS["CONTAINS"]
        direction TB
        C_A["Polygone A<br/>(englobant)"]
        C_B["Polygone B<br/>(a l'interieur)"]
    end

    subgraph WITHIN["WITHIN"]
        direction TB
        W_A["Polygone A<br/>(a l'interieur)"]
        W_B["Polygone B<br/>(englobant)"]
    end

    subgraph OVERLAPS["OVERLAPS"]
        direction LR
        O_A["Polygone A"] ---|"zone commune<br/>partielle"| O_B["Polygone B"]
    end

    subgraph CROSSES["CROSSES"]
        direction LR
        CR_A["Ligne A"] ---|"coupe le<br/>polygone B"| CR_B["Polygone B"]
    end

    subgraph DISJOINT["DISJOINT"]
        direction LR
        DJ_A["Geom A"] -.-|"aucun contact<br/>spatial"| DJ_B["Geom B"]
    end

    subgraph DWITHIN["IS WITHIN DISTANCE"]
        direction LR
        D_A["Polygone A"] -.-|"distance < N m"| D_B["Polygone B"]
    end
```

#### Diagramme — Pipeline Buffer

```mermaid
flowchart LR
    INPUT["Geometrie source"]

    INPUT --> BUFFER["Buffer"]

    BUFFER --> STATIC["Statique<br/>50m / 200m / 1km"]
    BUFFER --> DYNAMIC["Dynamique<br/>Expression QGIS<br/>ex: $area * 0.01"]
    BUFFER --> NEGATIVE["Negatif<br/>Retrecir le polygone<br/>Filtrage inverse"]
    BUFFER --> SEGMENTS["Buffer Segments<br/>Moins de segments =<br/>geometrie plus simple =<br/>filtrage plus rapide"]

    STATIC --> RESULT["Geometrie<br/>bufferisee"]
    DYNAMIC --> RESULT
    NEGATIVE --> RESULT
    SEGMENTS --> RESULT

    RESULT --> PREDICATE["Application du<br/>predicat spatial<br/>sur la geometrie etendue"]

    style BUFFER fill:#1976D2,color:#fff
    style DYNAMIC fill:#E65100,color:#fff
    style NEGATIVE fill:#D32F2F,color:#fff
    style SEGMENTS fill:#6A1B9A,color:#fff
```

#### Captures QGIS requises
1. Illustration de chacun des 8 predicats avec 2 geometries coloriees
2. Resultat de chaque predicat sur le meme jeu de donnees
3. Configuration du buffer dans l'interface
4. Comparaison buffer 50m vs 200m vs 1km
5. Expression dynamique dans le champ buffer
6. Buffer negatif avec geometrie retrecie visible
7. Tableau comparatif des 8 predicats (recapitulatif)
8. Badge centroide auto-active (cible > 5 000 ou source > 50 000 features)

#### Donnees de demo
- Couche zones inondables (polygones)
- Couche batiments avec attribut "etages"
- Couche riviere (lignes)
- Couche routes (lignes)

---

### VIDEO 05 — Favoris & Historique
**Niveau** : Intermediaire | **Duree** : 6-8 min | **Prerequis** : V02

#### Objectifs pedagogiques
- Sauvegarder un filtre en favori
- Rappeler un favori (1 clic = filtre applique automatiquement, sans clic supplementaire)
- Renommer, dupliquer, supprimer un favori
- Explorer le Favorites Manager Dialog (3 onglets : General, Expression, Remote)
- Importer/exporter des favoris (JSON)
- Naviguer dans l'historique (100 etats) — persistence optionnelle via APP.OPTIONS.HISTORY
- Undo/Redo avec Ctrl+Z / Ctrl+Y

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Pourquoi sauvegarder ses filtres ? | Voix + diagramme |
| 0:30 | Sauvegarder le filtre actuel en favori | Demo live |
| 1:00 | Badge favori — indicateur visuel | Capture annotee |
| 1:30 | Rappeler un favori — 1 clic declenche automatiquement le filtre (pas de double clic) | Demo live |
| 2:00 | Renommer, dupliquer, supprimer | Demo live |
| 2:30 | Favoris globaux vs projet | Demo live |
| 3:00 | Favorites Manager Dialog — onglet General (nom, description, tags, use_count, last_used_at) | Demo live |
| 3:30 | Favorites Manager Dialog — onglet Expression (texte complet de l'expression) | Demo live |
| 4:00 | Favorites Manager Dialog — onglet Remote (couches cibles + config spatiale) | Demo live |
| 4:30 | Export JSON — partager avec l'equipe | Demo live |
| 5:00 | Import JSON → dialog : Merge (ajouter) / Replace All (remplacer) / Cancel | Demo live |
| 5:30 | History Widget : compteur "3/7" (position/total), tooltips "Undo: Filter on communes", right-click Clear History | Demo live |
| 6:00 | Unfilter et historique : Unfilter utilise l'historique si disponible, sinon supprime le filtre directement | Demo live |
| 6:15 | Undo multi-couches (global state) | Demo live |
| 6:30 | Persistance historique : per-session par defaut, activer dans APP.OPTIONS.HISTORY | Demo live |

#### Diagramme — Cycle de Vie d'un Favori

```mermaid
stateDiagram-v2
    [*] --> FilterActif : Appliquer un filtre
    FilterActif --> Sauvegarde : Clic Sauvegarder

    Sauvegarde --> FavoriStocke : Nom + contexte spatial

    FavoriStocke --> Rappel : 1 clic Application
    Rappel --> FilterActif

    FavoriStocke --> Renommer : Edition du nom
    Renommer --> FavoriStocke

    FavoriStocke --> Dupliquer : Creer variante
    Dupliquer --> FavoriStocke

    FavoriStocke --> ExportJSON : Partager
    ExportJSON --> Fichier : favorites.json

    Fichier --> ImportJSON : Charger
    ImportJSON --> FavoriStocke

    FavoriStocke --> Supprimer : Action destructive
    Supprimer --> [*]

    note right of FavoriStocke : Stockage SQLite<br/>Persistant entre sessions<br/>Global ou par projet
```

#### Diagramme — Undo/Redo Stack

```mermaid
flowchart TD
    subgraph STACK["Pile d'historique (max 100)"]
        direction LR
        S1["Etat 1<br/>Aucun filtre"]
        S2["Etat 2<br/>Intersects routes"]
        S3["Etat 3<br/>+ AND riviere"]
        S4["Etat 4<br/>Buffer 200m"]
        CURRENT["ETAT ACTUEL<br/>Buffer 500m"]
    end

    UNDO["Ctrl+Z<br/>UNDO"] --> |"Revient a"| S4
    REDO["Ctrl+Y<br/>REDO"] --> |"Retablit"| CURRENT

    style CURRENT fill:#388E3C,color:#fff
    style UNDO fill:#D32F2F,color:#fff
    style REDO fill:#1565C0,color:#fff
```

#### Captures QGIS requises
1. Bouton "Sauvegarder en favori" dans l'interface
2. Badge compteur de favoris
3. Menu de rappel rapide (top 10)
4. Dialogue gestionnaire de favoris
5. Dialogue export/import JSON
6. Boutons Undo/Redo en action
7. Indicateur de position dans l'historique

---

### VIDEO 06 — Export GeoPackage & KML Pro
**Niveau** : Intermediaire | **Duree** : 8-10 min | **Prerequis** : V02

#### Objectifs pedagogiques
- Comprendre le dialogue ExportGroupRecapDialog (confirmation avant export)
- Choisir entre GPKG et KML selon le cas d'usage
- Comprendre QML (fidelite QGIS) vs SLD (portabilite OGC) pour les styles
- Preserver la hierarchie de groupes dans le GPKG (Preserve group structure)
- Utiliser le batch mode (un fichier par couche)
- Export streaming pour volumes > 10k entites
- Cas d'usage : livrable client QGIS-to-QGIS vs partage Google Earth

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Pourquoi exporter ? Deux cas : livrable QGIS-to-QGIS vs partage Google Earth | Diagramme |
| 0:30 | Onglet Export — vue d'ensemble | Demo live |
| 1:00 | ExportGroupRecapDialog : arborescence QTreeWidget, resume N couches / M groupes, chemin de sortie | Demo live |
| 1:45 | Checkbox "Preserve group structure in GPKG" + bouton Export vert #27ae60 | Demo live |
| 2:15 | GPKG : format recommande pour livrable QGIS-to-QGIS complet | Demo live |
| 3:00 | KML : format recommande pour partage Google Earth / utilisateurs non-QGIS | Demo live |
| 3:30 | QML vs SLD : QML = fidelite QGIS totale ; SLD = standard OGC portable — les deux activables simultanement | Demo live |
| 4:15 | Preserve group structure : la vraie valeur ajoutee — hierarchie reconstruite a l'ouverture | Demo live |
| 5:00 | Batch mode : un fichier par couche (vs tout dans un GPKG) | Demo live |
| 5:45 | Streaming 10k+ : FilterMate fragmente et reassemble pour eviter les timeout memoire | Demo live |
| 6:30 | Ouvrir le GPKG resultant — projet embarque, styles et groupes intacts | Demo live |
| 7:30 | Recapitulatif : GPKG pour equipe QGIS, KML pour livraison terrain / client non-SIG | Schema |
| — | ⚠️ Piege : Export = features visibles (filtrees). Faire Unfilter avant si on veut tout exporter. | Info |

#### Diagramme — Pipeline d'Export GeoPackage

```mermaid
flowchart TD
    subgraph INPUT["Projet QGIS actuel"]
        L1["Couche 1 (filtree)"]
        L2["Couche 2 (filtree)"]
        L3["Couche 3 (non filtree)"]
        G1["Groupe 'Transport'"]
        G2["Groupe 'Bati'"]
        STYLES["Styles / Symbologie"]
        CRS_IN["CRS : EPSG:2154"]
    end

    INPUT --> ENGINE["FilterMate Export Engine"]

    ENGINE --> STEP1["1. Extraction des entites filtrees"]
    ENGINE --> STEP2["2. Copie des styles QML"]
    ENGINE --> STEP3["3. Reconstruction arborescence"]
    ENGINE --> STEP4["4. Reprojection CRS"]
    ENGINE --> STEP5["5. Generation projet QGZ"]

    STEP1 --> GPKG["GeoPackage .gpkg"]
    STEP2 --> GPKG
    STEP3 --> GPKG
    STEP4 --> GPKG
    STEP5 --> GPKG

    GPKG --> TABLE1["Table : couche_1<br/>(donnees vecteur)"]
    GPKG --> TABLE2["Table : couche_2<br/>(donnees vecteur)"]
    GPKG --> TABLE_PROJ["Table : qgis_projects<br/>(projet QGZ embarque)"]
    GPKG --> TABLE_STYLE["Table : layer_styles<br/>(symbologie)"]

    TABLE_PROJ --> OPEN["Double-clic<br/>→ QGIS ouvre le projet<br/>→ Tout est reconstruit"]

    style ENGINE fill:#F57C00,color:#fff
    style GPKG fill:#1565C0,color:#fff
    style OPEN fill:#388E3C,color:#fff
```

#### Diagramme — GPKG vs KML : Quand Utiliser Lequel

```mermaid
flowchart TD
    EXPORT["FilterMate Export Engine"]

    EXPORT --> GPKG_PATH["GeoPackage .gpkg"]
    EXPORT --> KML_PATH["KML/KMZ"]

    GPKG_PATH --> GPKG_USE["Usage : Livrable QGIS-to-QGIS<br/>✔ Projet embarque<br/>✔ Styles QML (fidelite totale)<br/>✔ Hierarchie de groupes preservee<br/>✔ Multi-couches dans 1 fichier"]

    KML_PATH --> KML_USE["Usage : Partage Google Earth<br/>✔ Ouverture universelle<br/>✔ Styles SLD (standard OGC)<br/>✔ Partage terrain / clients non-SIG<br/>✗ Pas de projet embarque"]

    GPKG_USE --> STYLES["Styles exportes :"]
    KML_USE --> STYLES

    STYLES --> QML["QML — fidelite QGIS totale<br/>(QGIS-to-QGIS)"]
    STYLES --> SLD["SLD — standard OGC portable<br/>(inter-outils)<br/>Les deux activables simultanement"]

    style GPKG_PATH fill:#1565C0,color:#fff
    style KML_PATH fill:#E65100,color:#fff
    style EXPORT fill:#F57C00,color:#fff
    style QML fill:#388E3C,color:#fff
    style SLD fill:#7B1FA2,color:#fff
```

#### Captures QGIS requises
1. Onglet Export avec options selectionnees
2. ExportGroupRecapDialog — arborescence QTreeWidget avec groupes et couches
3. ExportGroupRecapDialog — resume N couches / M groupes + checkbox "Preserve group structure" + bouton vert
4. Progress bar / streaming pendant l'export (>10k entites)
5. GeoPackage ouvert dans QGIS — hierarchie de groupes reconstruite
6. Comparaison cote a cote : projet original vs GPKG reconstruit
7. KML ouvert dans Google Earth — rendu des styles SLD
8. Comparaison QML (rendu QGIS fidele) vs SLD (rendu OGC standard)

---

### VIDEO 07 — Multi-Backend & Optimisation
**Niveau** : Avance | **Duree** : 10-12 min | **Prerequis** : V02, V04

#### Objectifs pedagogiques
- Identifier les 4 backends par leurs couleurs (vert=PG, violet=Spatialite, bleu=OGR, orange=Memory)
- Forcer un backend et comprendre que c'est session-scoped (non persistant entre restarts)
- Utiliser "Auto-select Optimal for All Layers" et "Force [X] for All Layers"
- Configurer les optimisations automatiques
- Comprendre la strategie centroide
- Dialogue d'optimisation
- PostgreSQL session management

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Pourquoi plusieurs backends ? | Diagramme |
| 0:45 | Badge backend — identification visuelle | Capture annotee |
| 1:15 | Auto-selection : comment ca marche ? | Diagramme anime |
| 2:00 | Demo : meme filtre sur 4 backends | Demo live chrono |
| 3:30 | Forcer un backend manuellement (session-scoped : non persistant entre restarts) | Demo live |
| 3:45 | Options menu : "Auto-select Optimal for All Layers" et "Force [X] for All Layers" | Demo live |
| 4:00 | Memory optimization (PG < 5k → Memory) | Demo live |
| 4:30 | Query Cache : toujours actif, LRU 100 entrees | Demo live |
| 5:00 | Parallel Filtering : active des 2 couches cibles | Demo live |
| 5:30 | Progressive Filtering : PostgreSQL + complexite > 100 | Demo live |
| 6:00 | Geometry Simplification : WKT source > 100K chars | Demo live |
| 6:30 | EXISTS subquery : si FIDs source > 500 → evite d'inliner le WKT geant | Diagramme |
| 7:00 | Materialized View : si FIDs source > 500 sur PostgreSQL | Demo live |
| 7:30 | Dialogue d'optimisation avec recommandations | Demo live |
| 8:30 | Benchmarks : tableau comparatif par backend | Tableau anime |

#### Diagramme — Selection Automatique du Backend

```mermaid
flowchart TD
    START["Requete de filtrage lancee"]

    START --> Q0{"Backend FORCE<br/>par l'utilisateur ?"}
    Q0 -->|Oui| FORCED["Utiliser le backend<br/>selectionne"]
    Q0 -->|Non| Q1{"Type de provider ?"}

    Q1 -->|"memory"| MEM["💭 Backend MEMORY<br/>In-memory query<br/>< 0.5s / 50k"]

    Q1 -->|"postgres"| Q2{"< 5k entites ?"}
    Q2 -->|Oui| MEM2["💭 Backend MEMORY<br/>Optimisation petits PG"]
    Q2 -->|Non| PG["🐘 Backend POSTGRESQL<br/>Materialized View<br/>Requetes paralleles<br/>Index GIST<br/>< 2s / 1M"]

    Q1 -->|"spatialite<br/>GeoPackage"| SPAT["💾 Backend SPATIALITE<br/>Index R-tree<br/>SQL spatial<br/>~10s / 100k"]

    Q1 -->|"ogr / shapefile<br/>GeoJSON / WFS"| OGR["📁 Backend OGR<br/>Expression QGIS<br/>Universel<br/>~30s / 100k"]

    FORCED --> RESULT["Expression appliquee<br/>setSubsetString()"]
    MEM --> RESULT
    MEM2 --> RESULT
    PG --> RESULT
    SPAT --> RESULT
    OGR --> RESULT

    style PG fill:#27ae60,color:#fff
    style SPAT fill:#9b59b6,color:#fff
    style OGR fill:#3498db,color:#fff
    style MEM fill:#e67e22,color:#fff
    style MEM2 fill:#e67e22,color:#fff
    style RESULT fill:#388E3C,color:#fff
```

#### Diagramme — Benchmark Comparatif

```mermaid
xychart-beta
    title "Temps de filtrage par backend (secondes)"
    x-axis ["10k", "50k", "100k", "500k", "1M"]
    y-axis "Temps (s)" 0 --> 120
    bar "PostgreSQL" [0.5, 0.8, 1.2, 1.8, 2.5]
    bar "Spatialite" [1.5, 5, 10, 35, 60]
    bar "OGR" [5, 15, 30, 80, 120]
    bar "Memory" [0.2, 0.3, 0.5, 2, 5]
```

#### Diagramme — 4 Optimiseurs avec Seuils Precis

```mermaid
flowchart TD
    ANALYSER["Analyse de la requete"]

    ANALYSER --> OPT1["Query Cache<br/>TOUJOURS ACTIF<br/>LRU 100 entrees"]
    ANALYSER --> OPT2["Parallel Filtering<br/>ACTIVE si >= 2 couches cibles"]
    ANALYSER --> OPT3["Progressive Filtering<br/>ACTIVE si PostgreSQL<br/>+ complexite requete > 100"]
    ANALYSER --> OPT4["Geometry Simplification<br/>ACTIVE si WKT source > 100K chars"]

    OPT4 --> EXISTS["Si FIDs source > 500<br/>→ EXISTS subquery<br/>(evite d'inliner le WKT)"]

    OPT3 --> MATVIEW["Si FIDs source > 500<br/>→ Materialized View PostgreSQL<br/>(fm_temp_mv_*)"]

    OPT1 --> RESULT["Requete optimisee"]
    OPT2 --> RESULT
    EXISTS --> RESULT
    MATVIEW --> RESULT

    style OPT1 fill:#388E3C,color:#fff
    style OPT2 fill:#1565C0,color:#fff
    style OPT3 fill:#6A1B9A,color:#fff
    style OPT4 fill:#E65100,color:#fff
    style EXISTS fill:#D32F2F,color:#fff
    style MATVIEW fill:#D32F2F,color:#fff
    style ANALYSER fill:#F57C00,color:#fff
```

#### Captures QGIS requises
1. Badge backend avec icone (PostgreSQL, Spatialite, OGR, Memory)
2. Menu de selection de backend
3. Chronometre visible pendant filtrage sur chaque backend
4. Dialogue d'optimisation avec recommandations
5. Option centroide activee/desactivee — comparaison visuelle
6. Tab configuration avec seuils

---

### VIDEO 08 — PostgreSQL Power User
**Niveau** : Avance | **Duree** : 10-12 min | **Prerequis** : V07, PostgreSQL

#### Objectifs pedagogiques
- Comprendre les vues materialisees (fm_temp_mv_*)
- Detection automatique de la cle primaire
- Session management et cleanup
- Filtrage parallele multi-couches
- Performances sur BDTopo / OSM
- Tuning : connexion pool, timeouts

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | PostgreSQL + FilterMate = performance extreme | Voix |
| 0:30 | Vue materialisee : qu'est-ce que c'est ? | Diagramme |
| 1:30 | Demo : voir les MV dans pgAdmin | Capture pgAdmin |
| 2:30 | Prefix fm_temp_ : identification facile | Capture pgAdmin |
| 3:00 | Auto-cleanup vs cleanup manuel | Demo live |
| 3:30 | Dialogue info session PostgreSQL | Demo live |
| 4:00 | Detection cle primaire (id, fid, ogc_fid, cleabs) | Diagramme |
| 5:00 | Demo BDTopo : 1M batiments, filtrage < 2s | Demo live |
| 6:00 | Demo OSM : tables sans PK standard | Demo live |
| 6:30 | Filtrage parallele multi-couches | Demo live |
| 7:30 | Configuration : timeouts, batch size, pool | Demo live |
| 8:30 | Securite : sanitize_sql_identifier | Diagramme |
| 9:30 | Bonnes pratiques PostgreSQL | Recapitulatif |

#### Diagramme — Cycle de Vie Materialized View

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant FM as FilterMate
    participant PG as PostgreSQL

    U->>FM: Appliquer filtre spatial
    FM->>PG: CREATE MATERIALIZED VIEW fm_temp_mv_xxx AS ...
    PG-->>FM: Vue creee (index GIST auto)

    FM->>PG: SELECT ... FROM fm_temp_mv_xxx<br/>WHERE ST_Intersects(...)
    PG-->>FM: Resultats (< 2s pour 1M)

    FM->>FM: setSubsetString() sur couche QGIS

    Note over FM,PG: A la fin de session ou<br/>manuellement

    U->>FM: Cleanup (auto ou manuel)
    FM->>PG: DROP MATERIALIZED VIEW fm_temp_mv_xxx
    PG-->>FM: Vue supprimee
```

#### Diagramme — Detection Cle Primaire

```mermaid
flowchart TD
    START["Table PostgreSQL"]

    START --> Q1{"pg_index<br/>primary key ?"}
    Q1 -->|Trouvee| FOUND["PK detectee<br/>automatiquement"]

    Q1 -->|Non trouvee| Q2{"Essayer noms<br/>courants ?"}
    Q2 --> F1["id"]
    Q2 --> F2["fid"]
    Q2 --> F3["ogc_fid"]
    Q2 --> F4["cleabs (BDTopo)"]
    Q2 --> F5["gid"]
    Q2 --> F6["objectid"]

    F1 --> CHECK{"Colonne existe ?"}
    F2 --> CHECK
    F3 --> CHECK
    F4 --> CHECK
    F5 --> CHECK
    F6 --> CHECK

    CHECK -->|Oui| FOUND
    CHECK -->|Non| FALLBACK["Fallback :<br/>row_number() ou ctid"]

    style FOUND fill:#388E3C,color:#fff
    style FALLBACK fill:#F57C00,color:#fff
```

#### Captures QGIS requises
1. pgAdmin avec vues materialisees fm_temp_mv_* visibles
2. Dialogue info session PostgreSQL dans FilterMate
3. Bouton cleanup en action
4. Demo BDTopo avec chronometre
5. Tab config PostgreSQL (timeouts, pool size)
6. Logs de filtrage parallele

#### Donnees de demo
- BDTopo batiments PostGIS (~1M entites)
- OSM routes PostGIS (~500k entites)
- Schema temporaire avec vues materialisees

---

### VIDEO 09 — Configuration Avancee
**Niveau** : Expert | **Duree** : 8-10 min | **Prerequis** : V01

#### Objectifs pedagogiques
- Naviguer dans l'editeur de configuration
- Personnaliser les debounce timers
- Ajuster les seuils de performance
- Configurer le cache d'expressions
- Personnaliser le theme et les couleurs
- Comprendre les profils UI : compact (width < 1920 ou height < 1080), normal, HiDPI (pixel ratio > 1.5 ou width > 3840)
- Comprendre la migration automatique de config (mise a jour sans perte de configuration)
- TreeView JSON pour reglages fins

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Ouvrir les parametres FilterMate | Demo live |
| 0:30 | Structure de la configuration | Diagramme |
| 1:00 | Feedback level : minimal / normal / verbose | Demo live |
| 1:30 | Theme : auto / default / dark / light | Demo live |
| 2:00 | Position du dock et de la barre d'actions | Demo live |
| 2:30 | Profil UI : compact (width < 1920 ou height < 1080) / normal / HiDPI (pixel ratio > 1.5 ou width > 3840) | Demo live |
| 3:00 | Debounce timers (expression, filtre, canvas) | Demo live |
| 3:30 | Cache d'expressions (taille, TTL) | Demo live |
| 4:00 | Seuils d'optimisation | Demo live |
| 4:30 | Spatialite tuning (batch size, timeout) | Demo live |
| 5:00 | Expression builder limits | Demo live |
| 5:30 | Export defaults (GPKG, streaming) | Demo live |
| 6:00 | JSON TreeView pour reglages fins | Demo live |
| 7:00 | config.default.json vs config.json | Diagramme |
| 7:30 | Reset configuration | Demo live |
| 8:00 | Migration automatique de config au demarrage : ajout cles manquantes, renommage, nettoyage — non-destructif | Demo live |

#### Diagramme — Arborescence Configuration

```mermaid
graph TD
    CONFIG["Configuration FilterMate"]

    CONFIG --> APP["APP"]
    APP --> AUTO["AUTO_ACTIVATE : bool"]
    APP --> DOCK["DOCKWIDGET"]
    DOCK --> FEED["FEEDBACK_LEVEL<br/>minimal / normal / verbose"]
    DOCK --> LANG["LANGUAGE<br/>auto / en / fr / de / ..."]
    DOCK --> COLORS["COLORS"]
    COLORS --> THEME["ACTIVE_THEME<br/>auto / default / dark / light"]

    APP --> OPTIONS["OPTIONS (16 params)"]
    OPTIONS --> DEB["Debounce Timers<br/>300-1500 ms"]
    OPTIONS --> CACHE["Expression Cache<br/>100 entries, TTL"]
    OPTIONS --> QUERY["Query Timeout<br/>30s local / 60s PG"]
    OPTIONS --> SPAT["Spatialite Tuning<br/>batch 5000, timeout 120s"]
    OPTIONS --> EXPR["Expression Limits<br/>max FIDs 5000"]
    OPTIONS --> STREAM["Streaming Export<br/>threshold 10k"]

    CONFIG --> DEFAULT["config.default.json<br/>(SOURCE OF TRUTH)"]
    CONFIG --> USER["config.json<br/>(User overrides)"]

    style DEFAULT fill:#388E3C,color:#fff
    style OPTIONS fill:#1976D2,color:#fff
```

#### Captures QGIS requises
1. Dialogue de configuration — vue d'ensemble
2. Onglets de configuration (par categorie)
3. Spinbox avec validation min/max
4. Color picker pour themes
5. JSON TreeView avec config brute
6. Comparaison feedback minimal vs verbose

---

### VIDEO 10 — Architecture & Contribution
**Niveau** : Expert/Dev | **Duree** : 10-12 min | **Prerequis** : Connaissances Python

#### Objectifs pedagogiques
- Comprendre l'architecture hexagonale de FilterMate
- Naviguer dans la structure du code
- Comprendre les patterns (Factory, Strategy, Command, MVC)
- Comprendre le systeme de tests (600 tests)
- Comment contribuer au projet

#### Plan sequence

| Temps | Contenu | Type |
|-------|---------|------|
| 0:00 | Pourquoi l'architecture est importante | Voix |
| 0:30 | Vue d'ensemble hexagonale (4 couches) | Diagramme anime |
| 1:30 | Core Domain : modeles purs Python | Code + diagramme |
| 2:30 | Ports & Adapters : les interfaces | Code + diagramme |
| 3:30 | Backend Factory : ajout d'un backend | Code + diagramme |
| 4:30 | 13 Controllers MVC | Diagramme |
| 5:30 | FilterEngineTask : les 12 handlers | Diagramme |
| 6:30 | Systeme de signaux Qt | Diagramme |
| 7:30 | Thread safety dans QGIS | Code + diagramme |
| 8:00 | Suite de tests : 600 tests | Terminal |
| 8:30 | CI/CD GitHub Actions | Capture GitHub |
| 9:00 | Comment contribuer : fork, branch, PR | Terminal |
| 9:30 | Bonnes pratiques du projet | Recapitulatif |

#### Diagramme — Architecture Hexagonale Complete

```mermaid
graph TD
    subgraph UI["UI LAYER — 32k LOC"]
        direction LR
        U1["13 Controllers MVC"]
        U2["Dockwidget PyQt5/6<br/>6 925 lignes"]
        U3["Widgets & Dialogs"]
        U4["Tools"]
    end

    subgraph CORE["CORE DOMAIN — 50k LOC"]
        direction TB
        C1["28 Services metier"]
        C2["Domain Models<br/>(FilterResult, LayerInfo<br/>FilterExpression)"]
        C3["FilterEngineTask<br/>+ 12 Handlers"]
        C4["Ports (Interfaces)<br/>BackendPort<br/>CachePort<br/>RepositoryPort"]
    end

    subgraph ADAPTERS["ADAPTERS — 33k LOC"]
        direction LR
        A1["PostgreSQL<br/>Backend"]
        A2["Spatialite<br/>Backend"]
        A3["OGR<br/>Backend"]
        A4["Memory<br/>Backend"]
        A5["Repositories"]
        A6["AppBridge (DI)"]
    end

    subgraph INFRA["INFRASTRUCTURE — 15k LOC"]
        direction LR
        I1["Cache LRU"]
        I2["DB Connection Pool"]
        I3["Logging"]
        I4["Constants"]
        I5["Resilience"]
        I6["Signal Utils"]
    end

    UI -->|"Signals"| CORE
    CORE -->|"Ports"| ADAPTERS
    ADAPTERS --> INFRA

    style UI fill:#388E3C,color:#fff
    style CORE fill:#1976D2,color:#fff
    style ADAPTERS fill:#7B1FA2,color:#fff
    style INFRA fill:#455A64,color:#fff
```

#### Diagramme — Les 12 Handlers du FilterEngineTask

```mermaid
flowchart LR
    TASK["FilterEngineTask.run()"]

    TASK --> H1["1. Initialization<br/>Handler"]
    H1 --> H2["2. Source Geometry<br/>Preparer"]
    H2 --> H3["3. Expression<br/>Facade"]
    H3 --> H4["4. Filtering<br/>Orchestrator"]
    H4 --> H5["5. Attribute Filter<br/>Executor"]
    H5 --> H6["6. Spatial Filter<br/>Executor"]
    H6 --> H7["7. Backend<br/>Connector"]
    H7 --> H8["8. Materialized View<br/>Handler"]
    H8 --> H9["9. Subset Management<br/>Handler"]
    H9 --> H10["10. Export<br/>Handler"]
    H10 --> H11["11. Cleanup<br/>Handler"]
    H11 --> H12["12. Finished<br/>Handler"]
```

#### Diagramme — Thread Safety QGIS

```mermaid
flowchart TD
    subgraph MAIN["THREAD PRINCIPAL (UI)"]
        direction TB
        M1["Emission de signaux"]
        M2["Mise a jour UI"]
        M3["Acces QgsVectorLayer"]
    end

    subgraph WORKER["WORKER THREAD (QgsTask)"]
        direction TB
        W1["FilterEngineTask.run()"]
        W2["Requetes backend"]
        W3["Traitement geometrie"]
        W4["PAS d'acces QgsVectorLayer"]
    end

    RULE1["Regle 1 : Stocker URI dans __init__<br/>Recreer provider dans run()"]
    RULE2["Regle 2 : QgsGeometry OK<br/>(cree depuis WKT/WKB)"]
    RULE3["Regle 3 : Signals uniquement<br/>dans finished() callback"]

    WORKER -.->|"INTERDIT"| M3
    WORKER -->|"finished()"| MAIN

    style MAIN fill:#388E3C,color:#fff
    style WORKER fill:#1565C0,color:#fff
    style RULE1 fill:#FFC107,color:#000
    style RULE2 fill:#FFC107,color:#000
    style RULE3 fill:#FFC107,color:#000
```

#### Diagramme — Patterns Utilises

```mermaid
mindmap
  root((Design Patterns<br/>FilterMate))
    Creational
      Factory<br/>(BackendFactory)
      DI Container<br/>(AppBridge)
    Structural
      Adapter<br/>(QGIS Bridge)
      Repository<br/>(Data Access)
      MVC<br/>(Controllers)
    Behavioral
      Strategy<br/>(Multi-backend)
      Command<br/>(Undo/Redo)
      Observer<br/>(Qt Signals)
      Template Method<br/>(BaseController)
      Chain of Responsibility<br/>(12 Handlers)
    Architectural
      Hexagonal<br/>(Ports & Adapters)
      Service Locator<br/>(AppBridge)
```

#### Captures QGIS requises / Code
1. Arborescence du projet dans un IDE
2. Core domain models (code Python)
3. Interface Port (code Python)
4. Backend Factory (code Python)
5. Tests en execution dans le terminal
6. GitHub Actions CI/CD (capture GitHub)
7. Page de contribution GitHub

---

## 4. RECAPITULATIF DE PRODUCTION

### 4.1 Inventaire des Ressources

#### Diagrammes Mermaid par video

| Video | Diagrammes | Types |
|-------|:---:|--------|
| V01 | 1 | flowchart |
| V02 | 2 | flowchart |
| V03 | 2 | flowchart, graph |
| V04 | 2 | graph, flowchart |
| V05 | 2 | stateDiagram, flowchart |
| V06 | 2 | flowchart, graph |
| V07 | 3 | flowchart, xychart, flowchart |
| V08 | 2 | sequenceDiagram, flowchart |
| V09 | 1 | graph |
| V10 | 4 | graph, flowchart, flowchart, mindmap |
| **TOTAL** | **21** | |

#### Captures QGIS requises par video

| Video | Captures | Categories |
|-------|:---:|---------|
| V01 | 6 | Installation, UI, theme |
| V02 | 7 | Filtrage, comparaison, boutons |
| V03 | 7 | Exploration, selection, sync |
| V04 | 7 | Predicats, buffer, comparaison |
| V05 | 7 | Favoris, historique, badges |
| V06 | 7 | Export, GPKG, multi-format |
| V07 | 6 | Backends, benchmark, optimisation |
| V08 | 6 | pgAdmin, MV, BDTopo, config |
| V09 | 6 | Config dialog, JSON, themes |
| V10 | 7 | Code, IDE, tests, GitHub |
| **TOTAL** | **66** | |

### 4.2 Donnees de Demo Necessaires

| Dataset | Type | Source | Videos |
|---------|------|--------|--------|
| Departements France | Polygones, Shapefile | admin-express IGN | V01, V02 |
| Communes France | Polygones, Shapefile | admin-express IGN | V01, V02 |
| Routes BDTopo | Lignes, Shapefile/PG | BDTopo IGN | V02, V04, V08 |
| Batiments BDTopo | Polygones, PostGIS | BDTopo IGN | V02, V04, V07, V08 |
| Zones inondables | Polygones | Georisques | V04 |
| Riviere | Lignes | BD Carthage | V04 |
| OSM routes | Lignes, PostGIS | OpenStreetMap | V08 |
| GeoPackage exemple | Vecteur multi-couches | Auto-genere | V06 |
| GeoJSON communes | GeoJSON | Export | V06 |

### 4.3 Logiciels & Outils de Production

| Outil | Usage |
|-------|-------|
| OBS Studio | Capture ecran QGIS |
| QGIS 3.34+ LTR | Demo live |
| pgAdmin 4 | Captures PostgreSQL |
| Mermaid Live Editor | Generation diagrammes SVG/PNG |
| DaVinci Resolve / Shotcut | Montage video |
| Canva / Figma | Thumbnails, annotations |
| Audacity | Voix off |
| GitHub Pages | Hebergement site + videos |

### 4.4 Planning de Production Suggere

```mermaid
gantt
    title Plan de production — Serie tutoriels FilterMate
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Preparation
    Collecte donnees demo          :prep1, 2026-03-17, 5d
    Generation diagrammes Mermaid  :prep2, 2026-03-17, 3d
    Configuration QGIS + themes   :prep3, 2026-03-20, 2d

    section Captures QGIS
    V01-V03 Debutant              :cap1, 2026-03-24, 3d
    V04-V06 Intermediaire         :cap2, after cap1, 4d
    V07-V08 Avance                :cap3, after cap2, 4d
    V09-V10 Expert                :cap4, after cap3, 3d

    section Post-production
    Montage V01-V03               :post1, after cap1, 5d
    Montage V04-V06               :post2, after cap2, 5d
    Montage V07-V08               :post3, after cap3, 4d
    Montage V09-V10               :post4, after cap4, 4d

    section Publication
    V01-V03 en ligne              :milestone, after post1, 0d
    V04-V06 en ligne              :milestone, after post2, 0d
    V07-V08 en ligne              :milestone, after post3, 0d
    V09-V10 en ligne              :milestone, after post4, 0d
```

---

## 5. SPECIFICATIONS TECHNIQUES VIDEO

### 5.1 Format & Qualite

| Parametre | Valeur |
|-----------|--------|
| Resolution | 1920x1080 (Full HD) |
| FPS | 30 |
| Codec | H.264 / H.265 |
| Bitrate | 8-12 Mbps |
| Audio | AAC 128kbps, mono |
| Langue | Francais (voix off) |
| Sous-titres | EN, FR (SRT) |
| Ratio | 16:9 |
| Intro/Outro | 3-5 secondes |

### 5.2 Charte Graphique

| Element | Specification |
|---------|---------------|
| Police titres | Inter Bold |
| Police texte | Inter Regular |
| Couleur primaire | #1976D2 (bleu) |
| Couleur secondaire | #388E3C (vert) |
| Couleur accent | #F57C00 (orange) |
| Fond sombre | #0a0e1a |
| Fond clair | #ffffff |
| Logo | FilterMate SVG (resources/) |
| Watermark | Coin bas-droit, semi-transparent |

### 5.3 Nomenclature Fichiers

```
filtermate-tutorial-v01-installation.mp4
filtermate-tutorial-v02-filtrage-bases.mp4
filtermate-tutorial-v03-exploration.mp4
filtermate-tutorial-v04-predicats-buffer.mp4
filtermate-tutorial-v05-favoris-historique.mp4
filtermate-tutorial-v06-export-gpkg-kml.mp4
filtermate-tutorial-v07-multi-backend.mp4
filtermate-tutorial-v08-postgresql-power.mp4
filtermate-tutorial-v09-configuration.mp4
filtermate-tutorial-v10-architecture.mp4
```

---

## 6. MATRICE DE COUVERTURE FONCTIONNELLE

Cette matrice garantit que **chaque fonctionnalite du plugin est couverte par au moins une video**.

| Fonctionnalite | V01 | V02 | V03 | V04 | V05 | V06 | V07 | V08 | V09 | V10 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Installation | X | | | | | | | | | |
| Architecture Exploring/Toolbox/ActionBar | X | | | | | | | | | |
| Action Bar 6 boutons | X | | | | | | | | | |
| Theme sombre/clair | X | | | | | | | | X | |
| 22 langues | X | | | | | | | | X | |
| Filtrage simple | X | X | | | | | | | | |
| Source / Cible | | X | | | | | | | | |
| 8 predicats (Touches, Intersects, Contains, Within, Overlaps, Crosses, Disjoint, DWithin) | | | | X | | | | | | |
| Buffer m/km | | | | X | | | | | | |
| Buffer dynamique | | | | X | | | | | | |
| Buffer negatif | | | | X | | | | | | |
| Buffer Segments | | | | X | | | | | | |
| REPLACE / AND / OR | | X | | | | | | | | |
| Unfilter / Reset | | X | | | | | | | | |
| Filter button states | | X | | | | | | | | |
| Exploration vecteur | | | X | | | | | | | |
| Flash / Zoom / Identify | | | X | | | | | | | |
| Selection simple | | | X | | | | | | | |
| Selection multiple | | | X | | | | | | | |
| Selection custom | | | X | | | | | | | |
| Sync selection QGIS | | | X | | | | | | | |
| Lier widgets | | | X | | | | | | | |
| Favoris CRUD | | | | | X | | | | | |
| Favoris import/export | | | | | X | | | | | |
| Badge favori | | | | | X | | | | | |
| Undo/Redo 100 etats | | | | | X | | | | | |
| History Widget (compteur, tooltips) | | | | | X | | | | | |
| Historique persistant | | | | | X | | | | | |
| Export GeoPackage | | | | | | X | | | | |
| Projet embarque | | | | | | X | | | | |
| Styles preserves | | | | | | X | | | | |
| Groupes preserves | | | | | | X | | | | |
| Export GPKG + KML (styles QML/SLD) | | | | | | X | | | | |
| Streaming export | | | | | | X | | | | |
| ExportGroupRecapDialog | | | | | | X | | | | |
| Styles QML vs SLD | | | | | | X | | | | |
| 4 backends | | | | | | | X | | | |
| Badge backend | | | | | | | X | | | |
| Auto-selection | | | | | | | X | | | |
| Forcer backend | | | | | | | X | | | |
| Optimisation auto | | | | | | | X | | | |
| Centroide auto (seuils 5k/50k) | | | | X | | | X | | | |
| Seuils auto-centroide | | | | X | | | | | | |
| Strategies filtrage | | | | | | | X | | | |
| Query Cache LRU | | | | | | | X | | | |
| Parallel Filtering | | | | | | | X | | | |
| Progressive Filtering | | | | | | | X | | | |
| EXISTS subquery (WKT > 100K) | | | | | | | X | | | |
| Materialized Views | | | | | | | | X | | |
| PK auto-detection | | | | | | | | X | | |
| Session cleanup | | | | | | | | X | | |
| Filtrage parallele | | | | | | | | X | | |
| BDTopo / OSM | | | | | | | | X | | |
| Tuning PostgreSQL | | | | | | | | X | | |
| Verbose mode (outil pedagogique) | X | | | | | | | | X | |
| SQLite persistence config | X | | | | | | | | | |
| Log Messages Panel FilterMate | X | | | | | | | | | |
| Auto-detection champ affichage | X | | | | | | | | | |
| Edit Mode Conflict popup | | X | | | | | | | | |
| Auto Current Layer toggle | | | X | | | | | | | |
| Favorites Apply = filtre auto | | | | | X | | | | | |
| Historique persistence optionnelle | | | | | X | | | | | |
| Favorites Manager 3 onglets | | | | | X | | | | | |
| UI Profile HiDPI seuils | | | | | | | | | X | |
| Config Migration auto | | | | | | | | | X | |
| Config editor | | | | | | | | | X | |
| Debounce timers | | | | | | | | | X | |
| Cache expressions | | | | | | | | | X | |
| Seuils performance | | | | | | | | | X | |
| JSON TreeView | | | | | | | | | X | |
| Architecture hexa | | | | | | | | | | X |
| 12 handlers | | | | | | | | | | X |
| Thread safety | | | | | | | | | | X |
| 600 tests | | | | | | | | | | X |
| CI/CD GitHub | | | | | | | | | | X |
| Contribution | | | | | | | | | | X |

**Couverture : 76/76 fonctionnalites = 100%** *(+24 nouvelles fonctionnalites documentees dans la v3)*

---

## 7. KPI & METRIQUES DE SUCCES

| KPI | Objectif |
|-----|---------|
| Nombre de videos | 10 |
| Duree totale | ~75 min |
| Diagrammes Mermaid | 21 |
| Captures QGIS | 66 |
| Fonctionnalites couvertes | 100% (76/76) |
| Langues sous-titres | 2 (FR, EN) |
| Datasets demo | 9 |
| Niveaux de difficulte | 4 (debutant, intermediaire, avance, expert) |
| Vues cibles (6 mois) | 500+ par video |
| Taux d'installation post-video | +20% |

---

*Audit genere le 14 Mars 2026 — FilterMate v4.6.1*
*A valider par Jordan (PO) avant lancement de la production*
