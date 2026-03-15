"""
Mermaid Diagram Definitions
============================
All 12 Mermaid diagrams extracted from VIDEO_SCRIPT.md.
Used by DiagramGenerator to create HTML/PNG slides.
"""

from __future__ import annotations

DIAGRAMS: dict[str, dict[str, str]] = {

    # ── Diagram 01 ────────────────────────────────────────────────────────────
    "01_positioning": {
        "title": "Positionnement — Sans vs Avec FilterMate",
        "mermaid": """\
flowchart LR
    subgraph PROBLEME["❌ Sans FilterMate"]
        direction TB
        P1["Expressions QGIS\\nmanuelle"]
        P2["Aucun historique"]
        P3["Performance limitée\\nsur gros jeux de données"]
        P4["Export manuel\\net complexe"]
    end

    subgraph SOLUTION["✅ Avec FilterMate"]
        direction TB
        S1["Interface intuitive\\n+ Favoris + Undo/Redo"]
        S2["Filtrage géométrique\\navec prédicats spatiaux"]
        S3["Multi-backend auto\\nPostgreSQL / Spatialite / OGR"]
        S4["Export GPKG avec\\nprojet embarqué"]
    end

    PROBLEME -->|"FilterMate"| SOLUTION
""",
    },

    # ── Diagram 02 ────────────────────────────────────────────────────────────
    "02_backends": {
        "title": "Backends & Compatibilité",
        "mermaid": """\
graph TD
    QP["🧩 QGIS Plugin Manager"] --> FM["FilterMate 4.6.1"]

    FM --> B1["🐘 PostgreSQL / PostGIS\\n(avec psycopg2)"]
    FM --> B2["🗄️ Spatialite\\n(GeoPackage, SQLite)"]
    FM --> B3["📁 OGR\\n(Shapefile, GeoJSON, WFS...)"]
    FM --> B4["💾 Memory\\n(couches QGIS native)"]

    B1 --> P1["< 2s pour 1M d'entités"]
    B2 --> P2["~10s pour 100k entités"]
    B3 --> P3["~30s pour 100k entités"]
    B4 --> P4["< 0.5s pour 50k entités"]

    style FM fill:#4CAF50,color:#fff,stroke:#388E3C
    style B1 fill:#1565C0,color:#fff
    style B2 fill:#6A1B9A,color:#fff
    style B3 fill:#E65100,color:#fff
    style B4 fill:#00695C,color:#fff
""",
    },

    # ── Diagram 03 ────────────────────────────────────────────────────────────
    "03_interface": {
        "title": "Interface Utilisateur — FilterMate Dockwidget",
        "mermaid": """\
graph TD
    DOCK["🖥️ FilterMate Dockwidget"]

    DOCK --> T1["🔍 Onglet FILTRAGE"]
    DOCK --> T2["🔬 Onglet EXPLORATION"]
    DOCK --> T3["📦 Onglet EXPORT"]

    T1 --> T1A["Sélection de couche source"]
    T1 --> T1B["Sélection de couche cible"]
    T1 --> T1C["Prédicats géométriques\\n(touches, intersecte, contient...)"]
    T1 --> T1D["Buffer dynamique (m/km)"]
    T1 --> T1E["⭐ Favoris enregistrés"]
    T1 --> T1F["↩️ Undo / Redo (100 états)"]

    T2 --> T2A["🗺️ Vecteur : parcourir\\nles entités"]
    T2 --> T2B["🏔️ Raster : sélection\\npar valeur / plage"]
    T2 --> T2C["🔬 Pixel Picker\\n⬛ Rectangle Range\\n🔄 Sync Histogram"]

    T3 --> T3A["Export GeoPackage\\navec projet embarqué"]
    T3 --> T3B["Styles préservés"]
    T3 --> T3C["Hiérarchie de groupes\\nreproduire"]
    T3 --> T3D["22 formats de sortie"]

    style DOCK fill:#1976D2,color:#fff
    style T1 fill:#388E3C,color:#fff
    style T2 fill:#7B1FA2,color:#fff
    style T3 fill:#F57C00,color:#fff
""",
    },

    # ── Diagram 04 ────────────────────────────────────────────────────────────
    "04_workflow": {
        "title": "Workflow de Filtrage — Séquence Complète",
        "mermaid": """\
sequenceDiagram
    actor U as 👤 Utilisateur
    participant UI as 🖥️ Interface FilterMate
    participant APP as ⚙️ Application Core
    participant BACK as 🗄️ Backend (Auto-Sélectionné)
    participant QGIS as 🌍 QGIS / Couches

    U->>UI: Sélectionne source + cible + prédicat
    U->>UI: Clique "Filtrer"
    UI->>APP: Crée FilterEngineTask (async)

    APP->>BACK: Détecte provider type
    Note over BACK: PostgreSQL → Materialized View<br/>Spatialite → R-tree Index<br/>OGR → Expression filter<br/>Memory → In-memory query

    BACK-->>APP: Résultat (expression SQL/QGIS)
    APP->>QGIS: setSubsetString(expression)
    QGIS-->>UI: Couche filtrée ✅

    APP->>APP: Sauvegarde état (Undo stack)
    UI->>U: Affiche nombre d'entités filtrées
""",
    },

    # ── Diagram 05 ────────────────────────────────────────────────────────────
    "05_predicates": {
        "title": "Prédicats Géométriques Disponibles",
        "mermaid": """\
graph LR
    subgraph PREDICATS["🔷 Prédicats Spatiaux"]
        direction LR
        PR1["📍 touches\\n(intersecte le contour)"]
        PR2["🔗 intersects\\n(tout contact)"]
        PR3["📦 contains\\n(contient entièrement)"]
        PR4["🎯 within\\n(à l'intérieur de)"]
        PR5["🔲 overlaps\\n(chevauchement partiel)"]
        PR6["📏 is_within_distance\\n(à moins de N mètres)"]
    end

    subgraph BUFFER["🔵 Buffer Dynamique"]
        direction TB
        BUF["Distance configurable\\n(m / km)\\nCalcul côté serveur\\npour PostgreSQL"]
    end

    PREDICATS --> BUFFER
""",
    },

    # ── Diagram 06 ────────────────────────────────────────────────────────────
    "06_raster": {
        "title": "Outils Raster (v5.4+)",
        "mermaid": """\
graph TD
    subgraph RASTER["🏔️ Exploration Raster (v5.4+)"]
        direction LR
        R1["🔬 Pixel Picker\\nClic = valeur unique\\nCtrl+Clic = étend plage"]
        R2["⬛ Rectangle Range\\nGlisser = stats zone\\nMin/Max auto"]
        R3["🔄 Sync Histogram\\nSpinbox ↔ Histogramme\\nbidirectionnel"]
        R4["📊 All Bands Info\\nValeurs de tous\\nles bandes au clic"]
        R5["🎯 Reset Range\\nRéinitialise Min/Max\\naux données réelles"]
    end

    MAP["🗺️ Canvas QGIS"] --> R1
    MAP --> R2
    R3 --> HIST["📈 Histogramme\\ninteractif"]
    R4 --> BANDS["🎨 Multi-bandes\\n(RGB, MNT, etc.)"]
""",
    },

    # ── Diagram 07 ────────────────────────────────────────────────────────────
    "07_export": {
        "title": "Export GeoPackage (v4.6)",
        "mermaid": """\
flowchart TD
    PROJ["📂 Projet QGIS\\n(couches filtrées)"]

    PROJ --> EXP["⚙️ FilterMate Export Engine"]

    EXP --> D1["📋 Données vecteur\\n(entités filtrées)"]
    EXP --> D2["🎨 Styles des couches\\n(renderers, labels)"]
    EXP --> D3["📁 Hiérarchie des groupes\\n(arborescence fidèle)"]
    EXP --> D4["🌐 CRS d'export\\n(reprojection auto)"]

    D1 --> GPKG["📦 GeoPackage .gpkg"]
    D2 --> GPKG
    D3 --> GPKG
    D4 --> GPKG

    GPKG --> EMB["📎 Projet QGZ embarqué\\n(table qgis_projects)"]

    EMB --> OPEN["🔓 Ouverture dans QGIS\\n→ Projet reconstruit\\nautomatiquement ✅"]

    style GPKG fill:#F57C00,color:#fff,stroke:#E65100
    style OPEN fill:#388E3C,color:#fff
""",
    },

    # ── Diagram 08 ────────────────────────────────────────────────────────────
    "08_backends": {
        "title": "Sélection Automatique du Backend",
        "mermaid": """\
flowchart TD
    START["🔍 Requête de filtrage"]

    START --> Q1{"Provider ?"}

    Q1 -->|"postgres"| Q2{"< 5k entités ?"}
    Q1 -->|"spatialite / GPKG"| SPAT["🗄️ Backend Spatialite\\n→ R-tree index\\n→ SQL spatial"]
    Q1 -->|"ogr / shapefile / WFS"| OGR["📁 Backend OGR\\n→ Expression filter\\n→ Universel"]
    Q1 -->|"memory"| MEM["💾 Backend Memory\\n→ In-memory query\\n→ Très rapide"]

    Q2 -->|"Oui"| MEM2["💾 Memory optimization\\n(petites PG layers)"]
    Q2 -->|"Non"| PG["🐘 Backend PostgreSQL\\n→ Materialized View\\n→ Parallel queries\\n→ Spatial indexes GIST"]

    PG --> RES["✅ Expression QGIS\\nsetSubsetString()"]
    SPAT --> RES
    OGR --> RES
    MEM --> RES
    MEM2 --> RES

    style PG fill:#1565C0,color:#fff
    style SPAT fill:#6A1B9A,color:#fff
    style OGR fill:#E65100,color:#fff
    style MEM fill:#00695C,color:#fff
    style MEM2 fill:#00695C,color:#fff
""",
    },

    # ── Diagram 09 ────────────────────────────────────────────────────────────
    "09_architecture": {
        "title": "Architecture Hexagonale — Ports & Adapters",
        "mermaid": """\
graph TD
    subgraph INFRA["🔧 Infrastructure (15k lignes)"]
        I1["Cache LRU"]
        I2["Connection Pool DB"]
        I3["Logging"]
        I4["Dependency Injection"]
    end

    subgraph ADAPTERS["🔌 Adapters (33k lignes)"]
        direction LR
        A1["PostgreSQL\\nBackend"]
        A2["Spatialite\\nBackend"]
        A3["OGR\\nBackend"]
        A4["Memory\\nBackend"]
        A5["QGIS Signals\\nAdapter"]
        A6["Repositories\\n(Data Access)"]
    end

    subgraph CORE["⚙️ Core Domain (50k lignes)"]
        direction TB
        C1["28 Services métier"]
        C2["FilterEngineTask\\n(async QgsTask)"]
        C3["Domain Models\\n(FilterResult, LayerInfo...)"]
        C4["Strategies\\n(Multi-step, Progressive)"]
        C5["Ports (interfaces)"]
    end

    subgraph UI["🖥️ UI Layer (32k lignes)"]
        direction LR
        U1["13 Contrôleurs MVC"]
        U2["Dockwidget (PyQt5/6)"]
        U3["Outils carte\\n(RasterPixelPicker)"]
    end

    UI --> CORE
    CORE --> ADAPTERS
    ADAPTERS --> INFRA
    CORE -.->|"Ports"| ADAPTERS

    style CORE fill:#1976D2,color:#fff
    style ADAPTERS fill:#7B1FA2,color:#fff
    style UI fill:#388E3C,color:#fff
    style INFRA fill:#455A64,color:#fff
""",
    },

    # ── Diagram 10 ────────────────────────────────────────────────────────────
    "10_patterns": {
        "title": "Design Patterns — FilterMate",
        "mermaid": """\
mindmap
  root((FilterMate\\nDesign Patterns))
    Architecture
      Hexagonale\\n(Ports & Adapters)
      Découplage total\\ndomaine / infra
    Créational
      Factory\\n(BackendFactory)
      Dependency Injection\\n(app_bridge.py)
    Comportemental
      Strategy\\n(multi-backend)
      Command\\n(Undo/Redo)
      Observer\\n(Signals Qt)
    Structure
      Repository\\n(data access)
      MVC\\n(UI layer)
      Adapter\\n(QGIS bridge)
""",
    },

    # ── Diagram 11 ────────────────────────────────────────────────────────────
    "11_undo_redo": {
        "title": "Système Undo/Redo — Machine d'État",
        "mermaid": """\
stateDiagram-v2
    [*] --> Idle

    Idle --> Filtering : Applique filtre
    Filtering --> FilterApplied : Succès
    FilterApplied --> HistorySaved : Sauvegarde état\\n(FilterState)

    HistorySaved --> Idle

    Idle --> Undoing : Ctrl+Z / Bouton Undo
    Undoing --> StatePeeked : Lecture historique
    StatePeeked --> SingleLayer : 1 couche dans l'état
    StatePeeked --> MultiLayer : Plusieurs couches\\n(global state)
    SingleLayer --> Restored : Restore layer filter
    MultiLayer --> Restored : Restore all layers
    Restored --> Idle

    note right of HistorySaved : Stack max = 100 états\\nFIFO quand plein
""",
    },

    # ── Diagram 12 ────────────────────────────────────────────────────────────
    "12_metrics": {
        "title": "Métriques Qualité — FilterMate v4.6.1",
        "mermaid": """\
xychart-beta
    title "FilterMate — Métriques Clés (v4.6.1)"
    x-axis ["Tests\\n(396)", "Langues\\n(22)", "Services\\n(28)", "Contrôleurs\\n(13)", "Couverture\\n(75%)"]
    y-axis "Valeur" 0 --> 400
    bar [396, 22, 28, 13, 75]
""",
    },
}

# ---------------------------------------------------------------------------
# V01 Diagrams — Installation & Premier Pas
# Extracted from SCRIPT_V01_INSTALLATION.md
# ---------------------------------------------------------------------------

V01_DIAGRAMS: dict[str, dict[str, str]] = {

    # ── V01 Diagram: Installation flow ──────────────────────────────────
    "v01_install_flow": {
        "title": "V01 — Flux d'installation FilterMate",
        "mermaid": """\
flowchart LR
    A["QGIS Desktop"] --> B["Extensions"]
    B --> C["Gerer les extensions"]
    C --> D["Onglet 'Toutes'"]
    D --> E["Rechercher 'FilterMate'"]
    E --> F["Cliquer 'Installer'"]
    F --> G["FilterMate Dock Widget"]

    G --> H["Exploring Zone"]
    G --> I["Toolbox FILTERING / EXPORTING"]
    G --> J["Action Bar 6 boutons"]

    style A fill:#455A64,color:#fff
    style F fill:#1976D2,color:#fff
    style G fill:#4CAF50,color:#fff
    style H fill:#7B1FA2,color:#fff
    style I fill:#388E3C,color:#fff
    style J fill:#1565C0,color:#fff
""",
    },

    # ── V01 Diagram: Interface 3 zones ──────────────────────────────────
    "v01_interface_zones": {
        "title": "V01 — Architecture de l'interface (3 zones)",
        "mermaid": """\
graph TD
    HEADER["En-tete — Pastille Favoris + Pastille Backend"]

    subgraph ZONE_A["ZONE A — Exploring Zone"]
        direction LR
        A1["Identify"]
        A2["Zoom"]
        A3["Select"]
        A4["Track"]
        A5["Link"]
        A6["Reset"]
    end

    subgraph ZONE_B["ZONE B — Toolbox"]
        direction LR
        B1["FILTERING<br/>Source + Cible + Predicat"]
        B2["EXPORTING<br/>Couches + Format + Options"]
    end

    subgraph ZONE_C["ZONE C — Action Bar"]
        direction LR
        C1["Filter"]
        C2["Undo"]
        C3["Redo"]
        C4["Unfilter"]
        C5["Export"]
        C6["About"]
    end

    HEADER --> ZONE_A
    ZONE_A --> ZONE_B
    ZONE_B --> ZONE_C

    style HEADER fill:#37474F,color:#fff
    style ZONE_A fill:#7B1FA2,color:#fff
    style ZONE_B fill:#388E3C,color:#fff
    style ZONE_C fill:#1565C0,color:#fff
""",
    },

    # ── V01 Diagram: Sidebar buttons ────────────────────────────────────
    "v01_sidebar_buttons": {
        "title": "V01 — Barre laterale Exploring (6 boutons)",
        "mermaid": """\
graph LR
    subgraph SIDEBAR["Barre laterale — 6 boutons"]
        direction TB
        S1["Identify<br/>Inspecter les attributs<br/>1 clic"]
        S2["Zoom<br/>Centrer sur l'entite<br/>1 clic"]
        S3["Select<br/>Surligner<br/>ON / OFF"]
        S4["Track<br/>Suivi automatique<br/>ON / OFF"]
        S5["Link<br/>Synchroniser selecteurs<br/>ON / OFF"]
        S6["Reset<br/>Reinitialiser exploration<br/>1 clic"]
    end

    S1 --> R1["Fenetre Identify Results"]
    S2 --> R2["Carte centree + zoom"]
    S3 --> R3["Entite surlignee"]
    S4 --> R4["Navigation auto"]
    S5 --> R5["Selecteurs synchronises"]
    S6 --> R6["Retour a zero"]

    style SIDEBAR fill:#7B1FA2,color:#fff
    style R1 fill:#CE93D8,color:#333
    style R2 fill:#CE93D8,color:#333
    style R3 fill:#CE93D8,color:#333
    style R4 fill:#CE93D8,color:#333
    style R5 fill:#CE93D8,color:#333
    style R6 fill:#CE93D8,color:#333
""",
    },

    # ── V01 Diagram: Action Bar context ─────────────────────────────────
    "v01_action_bar_context": {
        "title": "V01 — Activation des boutons selon l'onglet",
        "mermaid": """\
graph TD
    subgraph FILTERING["Onglet FILTERING actif"]
        direction LR
        F1["Filter OK"]
        F2["Undo OK"]
        F3["Redo OK"]
        F4["Unfilter OK"]
        F5["Export ---"]
        F6["About OK"]
    end

    subgraph EXPORTING["Onglet EXPORTING actif"]
        direction LR
        E1["Filter ---"]
        E2["Undo ---"]
        E3["Redo ---"]
        E4["Unfilter ---"]
        E5["Export OK"]
        E6["About OK"]
    end

    style FILTERING fill:#388E3C,color:#fff
    style EXPORTING fill:#F57C00,color:#fff
    style F5 fill:#666,color:#999
    style E1 fill:#666,color:#999
    style E2 fill:#666,color:#999
    style E3 fill:#666,color:#999
    style E4 fill:#666,color:#999
""",
    },

    # ── V01 Diagram: First filter workflow ──────────────────────────────
    "v01_first_filter_workflow": {
        "title": "V01 — Workflow du premier filtrage Shapefile",
        "mermaid": """\
sequenceDiagram
    actor U as Utilisateur
    participant EZ as Zone d'Exploration
    participant TB as Toolbox (FILTERING)
    participant AB as Action Bar
    participant FM as FilterMate Engine
    participant QGIS as Carte QGIS

    U->>EZ: Selectionne couche "departements"
    U->>EZ: Choisit entite "Gironde"
    U->>TB: Verifie couche source (auto)
    U->>TB: Selectionne cible "communes"
    U->>TB: Choisit predicat "Intersects"
    U->>AB: Clique "Filter"

    AB->>FM: Lance FilterEngineTask (async)
    FM->>FM: Detecte backend OGR (Shapefile)
    FM->>FM: Construit expression spatiale
    FM->>QGIS: setSubsetString(expression)
    QGIS-->>U: Communes filtrees visibles
    FM-->>AB: Sauvegarde etat dans l'historique
""",
    },

    # ── V01 Diagram: Languages ──────────────────────────────────────────
    "v01_languages": {
        "title": "V01 — 22 langues disponibles",
        "mermaid": """\
mindmap
  root((FilterMate<br/>22 Langues))
    Europe Ouest
      Francais
      English
      Espanol
      Portugues
      Deutsch
      Italiano
      Nederlands
    Europe Est & Nord
      Polski
      Cestina
      Svenska
      Norsk
      Suomi
      Romana
    Asie
      Zhongwen
      Nihongo
      Hangugeo
      Hindi
    Moyen-Orient
      Arabi
      Turk
      Farsi
    Autres
      Bahasa Indonesia
      Tieng Viet
""",
    },

    # ── V01 Diagram: Feedback levels ────────────────────────────────────
    "v01_feedback_levels": {
        "title": "V01 — Niveaux de feedback (FEEDBACK_LEVEL)",
        "mermaid": """\
graph LR
    subgraph LEVELS["FEEDBACK_LEVEL"]
        direction TB
        L1["minimal<br/>Erreurs et alertes uniquement"]
        L2["normal<br/>Succes + erreurs (defaut)"]
        L3["verbose<br/>Tout : info, debug, timing"]
    end

    L1 --> USE1["Production<br/>Interface propre"]
    L2 --> USE2["Equilibre<br/>Messages utiles"]
    L3 --> USE3["Formation<br/>Comprendre chaque etape"]

    style L1 fill:#F44336,color:#fff
    style L2 fill:#FF9800,color:#fff
    style L3 fill:#4CAF50,color:#fff
    style USE3 fill:#4CAF50,color:#fff
""",
    },

    # ── V01 Diagram: Display field detection ────────────────────────────
    "v01_display_field_detection": {
        "title": "V01 — Detection du champ d'affichage (6 niveaux)",
        "mermaid": """\
graph TD
    START["Nouvelle couche chargee"] --> P1

    P1{"1. Expression d'affichage<br/>configuree dans QGIS ?"}
    P1 -->|"Oui"| R1["Utilise l'expression QGIS"]
    P1 -->|"Non"| P2

    P2{"2. Champ avec<br/>ValueRelation ?"}
    P2 -->|"Oui"| R2["Utilise represent_value()"]
    P2 -->|"Non"| P3

    P3{"3. Champ correspondant<br/>a un pattern nom/name/label ?"}
    P3 -->|"Oui + valeurs"| R3["Utilise ce champ"]
    P3 -->|"Non"| P4

    P4{"4. Premier champ texte<br/>non-ID avec valeurs ?"}
    P4 -->|"Oui"| R4["Utilise ce champ texte"]
    P4 -->|"Non"| P5

    P5{"5. Cle primaire<br/>disponible ?"}
    P5 -->|"Oui"| R5["Utilise la cle primaire"]
    P5 -->|"Non"| P6

    P6["6. Premier champ<br/>avec des valeurs"] --> R6["Utilise ce champ"]

    style START fill:#1976D2,color:#fff
    style R1 fill:#4CAF50,color:#fff
    style R2 fill:#4CAF50,color:#fff
    style R3 fill:#4CAF50,color:#fff
    style R4 fill:#FF9800,color:#fff
    style R5 fill:#FF9800,color:#fff
    style R6 fill:#F44336,color:#fff
""",
    },

    # ── V01 Diagram: Persistence ────────────────────────────────────────
    "v01_persistence": {
        "title": "V01 — Persistence de la configuration (SQLite)",
        "mermaid": """\
flowchart LR
    subgraph SESSION_1["Session 1"]
        direction TB
        U1["Configuration de l'exploration"]
        U2["Champ d'affichage choisi"]
        U3["Etat des toggles"]
        U4["Dernier filtre applique"]
    end

    subgraph SQLITE["SQLite local"]
        direction TB
        DB["fm_project_layers<br/>_properties"]
    end

    subgraph SESSION_2["Session 2"]
        direction TB
        R1["Configuration restauree"]
        R2["Champ d'affichage restaure"]
        R3["Toggles restaures"]
        R4["Historique disponible"]
    end

    SESSION_1 -->|"Sauvegarde auto"| SQLITE
    SQLITE -->|"Restauration auto"| SESSION_2

    style SQLITE fill:#1565C0,color:#fff
    style SESSION_1 fill:#7B1FA2,color:#fff
    style SESSION_2 fill:#388E3C,color:#fff
""",
    },
}

# Merge V01 diagrams into the main DIAGRAMS dict
DIAGRAMS.update(V01_DIAGRAMS)

# Convenience list of all diagram IDs in order
DIAGRAM_ORDER: list[str] = list(DIAGRAMS.keys())
