# Lot F : l'agent règle QGIS (« le max »)

Date : 2026-11-13. Statut : à approuver. Lots voisins : D (`ask_user`), E (EXPLORING).

## Pourquoi

L'agent sait régler FilterMate (`describe_settings`, `get_setting`, `change_settings`, les profils) et une partie du
projet : SCR, styles, étiquettes, arbre des couches. Il ne sait rien régler de QGIS lui-même ni des propriétés du
projet : accrochage, unités, ellipsoïde, SCR par défaut, rendu, numérisation, identification. L'utilisateur veut
« le max » : tout ce qui peut l'être, avec des garde-fous.

## Objectifs

- L'agent trouve, explique et change les réglages de QGIS (profil de l'utilisateur) et les propriétés du projet ouvert.
- Chaque changement est montré avant et après, confirmé, et annulé avec le tour.
- Les réglages dangereux restent hors de portée, quoi qu'on lui demande.

## Non-objectifs

- Installer ou mettre à jour des extensions, gérer des dépôts.
- Remplacer le mode expert (`run_pyqgis`), qui reste le recours pour le reste et garde ses propres confirmations.

## Anti-objectifs

- Un réglage qui ouvre une porte :
  - exécution de code (macros, Python au démarrage, « faire confiance au projet ») ;
  - identifiants (authentification, proxy) ;
  - sécurité réseau (exceptions TLS, certificats) ;
  - extensions (dépôts, installation).
  - Même à la demande explicite de l'utilisateur, l'agent dit où le régler lui-même, sans le faire.

## Approches

1. **Tout, sauf une liste noire (retenue par l'utilisateur).**
2. Une liste blanche riche : plus sûre, mais pas « le max ». Écartée.
3. Tout, sans exclusion : écartée, car un modèle trompé par le texte d'une donnée ou d'un connecteur pourrait proposer
   un réglage dangereux.

## Conception

- **Lecture des réglages de QGIS :**
  - avec QGIS 3.30 ou plus, par l'arbre des réglages (`QgsSettingsTree`, `QgsSettingsEntry*`) : clé, type, valeur,
    défaut, description, choix et bornes quand QGIS les donne ;
  - avant 3.30, ou pour une clé hors de l'arbre, par `QgsSettings` brut (clé, valeur, type déduit, sans description).
    L'agent le dit alors, et ne devine jamais une valeur.
- **Propriétés du projet** (`QgsProject`) : titre, SCR, ellipsoïde, unités de distance et de surface, accrochage
  (`QgsSnappingConfig`), mode des transactions, évaluation des valeurs par défaut côté fournisseur, sauvegarde
  automatique. On les lit et on les écrit par l'API du projet, pas par des clés brutes. Une table de correspondance
  donne un nom stable à chacune (`project.snapping.enabled`, `project.units.distance`…).
- **Outils de l'agent :**
  - `describe_qgis_settings(query, scope)` : `scope` vaut `qgis` ou `project` ; c'est une recherche par mots, comme
    `describe_settings` ;
  - `get_qgis_setting(key)` ;
  - `change_qgis_settings(changes, reason)` : tout ou rien, chaque valeur vérifiée par son type, ses choix et ses
    bornes ;
  - même carte que `change_settings` (avant et après, demandée à chaque niveau, jamais autorisée pour la
    conversation) ;
  - les valeurs d'avant sont gardées par `turn_effects` pour l'annulation du tour.
- **Liste noire** (`core/agent/qgis_settings_policy.py`, sans QGIS, testée) :
  - préfixes et clés refusés à la lecture et à l'écriture : authentification et `auth*`, `proxy/*`, identifiants
    réseau, `qgis/networkAndProxy/*`, exceptions SSL et TLS, `qgis/enableMacros`, Python au démarrage et
    `pythonInit`, `trustedProjects` et confiance des projets, `app/plugin_repositories/*` et installation
    d'extensions, chemins de scripts lancés automatiquement ;
  - une valeur qui ressemble à un secret (mot de passe, jeton) n'est jamais montrée au modèle, elle est dite
    « définie » ;
  - la liste est un refus par motif : ce qui ressemble à ces familles est refusé aussi, avec un test par famille.
- **Effet** : la réponse dit quand un réglage prend effet (tout de suite, à la prochaine carte, au redémarrage de
  QGIS). Pour les réglages de l'arbre, c'est QGIS qui le dit ; sinon, c'est « peut demander un redémarrage ».
- **Profils** : `export_settings_profile` peut inclure une section `qgis` des réglages changés par l'agent (sans la
  liste noire), pour partager une configuration d'équipe.
- **Skill** : le skill `configuration` gagne une partie QGIS : chercher, expliquer la valeur actuelle, proposer, une
  carte, dire quand c'est appliqué. La mise en route peut proposer quelques réglages QGIS utiles (accrochage, unités,
  SCR par défaut) en une `ask_user` (lot D).

## Ce qui reste au constructeur

- La liste exacte des propriétés du projet, et les motifs de la liste noire, vérifiés sur QGIS 3.22, LTR et latest.
- Les messages dans les 34 catalogues.
- Tests :
  - unitaires : politique, vérification des valeurs, secrets masqués ;
  - contrôle sans écran : un réglage QGIS et une propriété du projet changés puis annulés avec le tour, sur QGIS 3.22
    et latest ;
  - un cas piège du banc : on demande d'activer les macros, l'agent refuse et dit où le régler.
