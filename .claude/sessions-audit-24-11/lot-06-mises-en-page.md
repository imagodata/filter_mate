# Lot 6 — Mises en page, atlas, graphiques (audit 24/11/2026)

## Contexte
Plugin FilterMate, base `main` à `a03bb9e0`. Ne rien corriger hors de ce lot. Aucun outil n'écrit hors de la racine d'export (garder cette propriété).

## Défauts à corriger
1. Annuler un tour qui a créé une mise en page supprime toute mise en page de ce nom (même retouchée par l'utilisateur ou créée pendant le tour).
   - `adapters/agent/turn_effects.py:692` et `:978` (#615) → annulation par empreinte/identité, pas par nom.
2. Empreinte mise en page ne retient que position/taille/texte : cadre, jeu de couches, fond changés par l'utilisateur écrasés à l'annulation.
   - `adapters/public_api/layouts.py:943` (#629) → empreinte complète.
3. Page d'atlas au nom de fichier NULL/vide écrite à côté du dossier, non comptée (« files: 5, pages: 6 »), peut écraser un fichier.
   - `layouts.py:374` (#615, #628) → nom de repli + comptage cohérent.
4. `edit_layout set_text` écrit du HTML (scripts compris) dans une étiquette déjà en mode HTML ; sous 3.22 le script s'exécute et appelle une adresse sans question (sous 4.3 rien ne part).
   - `layouts.py:766` (#616) → neutraliser le script / mode texte.
5. Second rang : `describe_layout`/`set_atlas` lisent toute la couche de couverture sur le thread principal (`layouts.py:486`) ; messages d'échec d'export envoient le chemin absolu au fournisseur (`operations.py:1210`, `layouts.py:348`) ; catégorie « (empty) »/« Others » fusionne avec NULL/reste, `aggregate` ignoré, camembert retire les négatifs sans le dire (`core/agent/charts.py:270`, `:379`, `fm_charts.js:183`) ; `export_chart` dit « The user is asked first », faux en autonome (`core/agent/tool_catalog.py:258`) ; noms réservés Windows CON/NUL (`layouts.py:233`).

## Vérification
- `check_agent_layouts.py` sous 3.22 ET latest 4.3 (comportement HTML/script diffère).
- Preuve : annulation ne touche plus la mise en page de l'utilisateur ; atlas NULL compté et confiné. Rendre compte sans committer.
