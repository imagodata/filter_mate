# Prise agent — fiche de réglages (crue de l'Urumea, à poser à la main)

Les profils partagés ne portent jamais les réglages de l'agent
(`core/agent/settings_profile.py` : ni preset, ni modèle, ni clé) :
tout ci-dessous se règle dans le panneau agent, sur le poste de tournage.

## Fournisseur
- Preset : `anthropic` (défaut) → `https://api.anthropic.com`.
- Clé : la NOUVELLE clé (celle collée en chat est révoquée), saisie dans le panneau ;
  stockée dans la base d'authentification QGIS, jamais dans un fichier.
- Consentement : à donner pour ce serveur, sinon rien ne part.
- Modèle : le Haiku proposé par la liste live du fournisseur (`/v1/models`).

## Sources à activer (aucune par défaut)
- `overpass_fr` — OpenStreetMap via Overpass France (bâtiments, routes, ponts, Urumea).
- `copernicus_dem` — relief mondial 30 m (source du calcul d'altitude).
- `photon` — géocodeur mondial, pour situer San Sebastián
  (le géocodeur IGN est France uniquement : inutilisable ici).

## Pendant la prise
- Niveau d'autonomie standard : demande avant fichiers et réseau → prévoir ces
  confirmations dans le minutage, ou régler l'autonomie en connaissance de cause.
- Changer de fournisseur vide la conversation : figer ces réglages avant le « moteur ».
- La mention « nothing leaves your computer » reste hors teaser (clé API = données envoyées).
