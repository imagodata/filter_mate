# Lot 3 — Copie locale WFS (audit 24/11/2026)

## Contexte
Plugin FilterMate, base `main` à `a03bb9e0`. Sondes contre serveurs WFS de test, sans réseau. Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Copie WFS tronquée par le serveur marquée complète : 50 entités reçues sur 5 000 annoncées (`numberMatched`), `complete: true`, aucune note. Le nombre annoncé n'est jamais comparé au lu.
   - `adapters/qgis/stream_copy.py:475` (#604)
2. « Copier à nouveau » servi par le cache réseau de QGIS quand le serveur n'envoie pas d'en-tête de cache : aucune requête GetFeature, vieilles données datées du jour.
   - `stream_copy.py:428` (#604, #610) → forcer la relecture (cache-buster / `CacheControl: no-cache`).
3. Filtre écrit pour le GeoPackage de la copie (`json_each`, champ `fid`) reporté tel quel sur le WFS au retour au service et dans le projet enregistré → couche non filtrée, texte affiché.
   - `stream_copy.py:605` et `:680`, `ui/controllers/stream_copy_actions.py:96`
4. Mot de passe WFS/WMS en clair dans le journal quand le retour échoue (seules adresses http masquées).
   - `adapters/qgis/coverage_layers/snapshots.py:57` et `:665` → masquer aussi `password=`.
5. Second rang (à traiter si trivial, sinon signaler) : dialogue « couches indisponibles » avant rattachement hors ligne (`_on_read_project`, confiance 55 %) ; source changée pendant la copie (`stream_copy_actions.py:363`) ; rebascule au déchargement du plugin dans le thread principal (`:93`) ; `QgsProject` lu depuis le thread de travail (`remote_materializer.py:292`, warnings 4.3) ; annulation après `local_copy` (WMS orphelin / WFS sur copie, `snapshots.py:569`) ; « Copier à nouveau » interrompu (`stream_copy_actions.py:322`) ; messages faux (réponse coupée, disque plein, `stream_copy.py:475`) ; copies jamais supprimées + champ `fid` ajouté en tête.

## Travail demandé
- Comparer nombre lu vs annoncé, marquer incomplet + note visible si tronqué.
- Ajouter aux serveurs de test : plafond (troncature) + absence d'en-tête cache ; les verser dans `check_stream_copy.py`.
- Ne jamais reporter sur le service un filtre incompris par lui (traduire ou effacer + prévenir).

## Vérification
- `check_stream_copy.py` vert (3.44 + 4.3), aucune fuite `password=` dans les journaux. Rendre compte sans committer.
