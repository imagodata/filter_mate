# Urumea — fiche de tournage

Statut : nouveaux plans en attente des lots 1 (interaction/favoris), 2 (rendus)
et 3 (outils GUI/mises en page) stabilisés et testés ensemble. Lire leurs comptes
rendus et relever le commit intégré ainsi que les résultats des contrôles avant tournage.

Les profils partagés n'exportent pas les réglages d'agent. Utiliser un profil
jetable propre à la prise. Le lanceur headless en crée un par exécution, avec cache
séparé, sans effacer une base d'authentification personnelle.

- Fournisseur : `anthropic`, consentement pour `https://api.anthropic.com`.
- Modèle : identifiant exact renvoyé par la liste du fournisseur, dans `FM_AGENT_MODEL`.
  L'ancien identifiant codé en dur n'est plus supposé valide.
- Clé : `FM_AGENT_KEY` injectée dans l'environnement, puis base d'authentification QGIS.
  Ne jamais filmer ni archiver l'environnement complet, le wallet ou le profil.
- Sources : `overpass_fr`, `copernicus_dem`, `photon`. L'acquisition en Espagne
  utilise le géocodeur mondial. Inclure rues locales et chemins piétons pour la desserte.
- Mode réellement automatisé : Act/autonome ; `add_osm_features`, `add_elevation`
  et `run_algorithm` préautorisés. Les autres confirmations restent visibles.
  Pour filmer Plan, tourner un plan séparé et vérifier son comportement.

Avant le moteur :

1. Exécuter `scripts/qgis4_windows_check.py` sur le poste Windows cible. Conserver le
   JSON : version QGIS/Qt/FilterMate, validité/SCR/champs des couches, algorithmes.
   `environment_ready` contrôle l'environnement, jamais les affirmations du scénario.
2. Geler l'emprise, la date et les sources ; sauvegarder les données brutes.
   La copie `../lot5/data/urumea/legacy-vectors.gpkg` ne contient que les six tables
   vectorielles de l'ancienne répétition ; le DSM et un réseau piéton complet restent à préparer.
3. Contrôler la moyenne zonale du **modèle de surface**, les NoData, les distances
   en EPSG:32630 et un échantillon de géométries. Prévoir un plan montrant le zoom réel.
4. Inspecter les fichiers exportés et les rouvrir. Pas de projet GPKG embarqué annoncé.
5. Contrôler algorithme de réseau, coût, vitesse, origines et sorties. Ne jamais
   substituer un rayon à un temps de parcours. Les ponts ne sont pas garantis praticables.
6. Enregistrer puis rejouer le favori ; comparer filtres/comptes. Pour un partage,
   refaire le test dans un second projet avec les données communes et les liaisons du lot 1.

Après chaque requête, `tools.jsonl` conserve appels/résultats et
`urumea-observations.jsonl` conserve transcription complète, comptes, champs,
SCR et sous-ensembles. Vérifier les erreurs et les images, puis renseigner
`../lot5/claims.json`. Un nom de couche « isochrone » ne suffit pas.

Crédits à l'écran : © OpenStreetMap contributors (ODbL), Copernicus DEM.
Afficher « seuils illustratifs, modèle de surface 30 m ». Ces données ne
permettent pas de valider un risque de crue ni une consigne d'évacuation.
