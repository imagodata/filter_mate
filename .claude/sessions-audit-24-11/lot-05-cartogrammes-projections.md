# Lot 5 — Cartogrammes et projections (audit 24/11/2026)

## Contexte
Plugin FilterMate, base `main` à `a03bb9e0`. Sondes relancées en Python pur + QGIS 3.22/4.3. Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Cartogramme contigu figé par une seule valeur à 0 ou NULL : déplacement max d'un sommet 5e-11 m contre 367 m si tout > 0. La carte d'origine est rendue sans erreur.
   - `core/agent/cartograms.py:154` (#623)
2. Dorling/Demers sur couche de points en projeté : centroïde du mini-carré faux par annulation numérique. Point Lambert-93 sorti à 2 295 km ; sur 60 points, médiane 4,5 km, 24 à > 10 km.
   - `adapters/public_api/cartograms.py:93`, `core/agent/cartograms.py:58` (#623, #628) → calcul en double / recentrage local.
3. `suggest_crs` sans couche nommée : un fond XYZ visible donne l'emprise du monde → Toulouse reçoit Robinson en premier (le skill dit de prendre le premier).
   - `adapters/public_api/project_control.py:205` (#621) → ignorer les fonds de carte.
4. `suggest_crs` propose le pays voisin (Strasbourg→UTM 32N Allemagne, Lille→Lambert belge, Corse→italien ; EPSG:2154 absent des 6).
   - `core/agent/projections.py:228` → pondérer par pays / inclure le national.
5. `suggest_crs` lit jusqu'à 20 000 entités/couche sur le thread principal (4,8 s pour 20 000 polygones × N couches).
   - `project_control.py:214` → plafond + échantillon + tâche de fond.
6. Second rang : widgets envoient min/max au modèle sans réglage (`core/agent/widgets.py:258`) ; widget écrase le filtre du dock (`adapters/agent/agent_widgets.py:121`) ; `set_project_crs` accepte PROJ/WKT quelconque + grilles distantes (`project_control.py:155`, requête réseau non vérifiée) ; `make_cartogram` accepte service web + plafond sauté si `featureCount()==-1` + 7,2 s sur thread principal (`cartograms.py:69`, `core/agent/cartograms.py:26`) ; `dot_density` révèle le max par dichotomie (`layer_style.py:644`, #624) ; cartogramme en dossier temp QGIS perdu au redémarrage (`cartograms.py:166`) ; `set_project_crs` répond `crs: ''` pour CRS sur mesure (`project_control.py:163`).

## Vérification
- Sondes rejouées (contigu avec NULL, 60 points Lambert-93, suggest_crs avec fond XYZ + Strasbourg/Lille/Corse).
- `check_agent_cartograms.py`, `check_agent_projections.py` verts. Rendre compte sans committer.
