# Lot 2 — Zoom et EXPLORING (audit 24/11/2026)

## Contexte
Plugin FilterMate (QGIS, Python 3.10+, PEP 8). Base `main` à `a03bb9e0`. Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Zoom automatique (actif par défaut) : l'étendue reste dans le CRS de la couche au lieu d'être transformée vers le CRS de la carte. Couche EPSG:4326 près de Toulouse + projet EPSG:2154 → la carte part sur (1,4 ; 43,6) en Lambert-93. Le chemin des services web, lui, transforme.
   - `adapters/auto_zoom.py:105` à `:237` (chemin synchrone). Favoris passés par là depuis #655.
2. Un seul point retenu, ou points alignés : plus aucun zoom (étendue « vide ») ; la marge du tampon n'agrandit plus la vue.
   - `adapters/auto_zoom.py:229`
3. Liste multiple d'EXPLORING jamais filtrée par l'expression personnalisée de la liaison : `"name" LIKE 'east%'` laisse les quatre lignes affichées. Le banc ne vérifie que le texte rangé.
   - `ui/widgets/custom_widgets.py:1227` (#647 — la fonction annoncée ne marche que pour la liste simple).

## Travail demandé
- Transformer l'étendue vers le CRS de la carte dans le chemin synchrone (mirror du chemin web).
- Centrer + échelle de repli pour point seul / géométrie d'étendue vide ; réappliquer la marge du tampon.
- Filtrer les lignes affichées de la liste multiple par l'expression de la liaison, pas seulement le texte stocké.

## Vérification
- Sonde 4326-dans-2154 : après filtre/favori, le centre carte ≈ Toulouse en 2154 (pas 1,4/43,6).
- Banc `link` : vérifier les lignes affichées, pas seulement le texte rangé.
- `run_gui_smoke` + bancs EXPLORING verts (3.44 LTR minimum). Rendre compte sans committer.
