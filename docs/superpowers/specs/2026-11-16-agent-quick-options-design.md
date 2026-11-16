# Activer et désactiver fournisseurs, sources et MCP depuis l'agent

Date : 2026-11-16. Statut : approuvé (« les deux, ok go », 16/11).

## Pourquoi

Aujourd'hui, choisir un fournisseur ou un modèle, cocher une source ou un connecteur MCP, ou ouvrir le serveur MCP du
plugin passe par la boîte de réglages de l'agent, onglet par onglet. L'utilisateur veut le faire depuis l'agent
directement : d'un clic dans le panneau AGENT, et en le demandant à l'agent dans le chat.

## Objectifs

- **Dans le panneau** (menu « ⋯ » du panneau AGENT) :
  - **Sources** : un sous-menu par sorte de source (fonds de carte, géocodeurs, données ouvertes, altitude,
    population, OpenStreetMap, imagerie, bases de données, connecteurs MCP, sources ajoutées), une case par source ;
    « Réglages des sources… » ouvre l'onglet Sources ;
  - **Modèle** : les fournisseurs déjà configurés (fournisseur, modèle, adresse, clé, accord d'envoi), celui en cours
    coché ; en choisir un en change ; « Retirer de la liste » sur chacun ; « Autre fournisseur ou modèle… » ouvre
    l'onglet Fournisseur ;
  - **Serveur MCP du plugin** : une case.
- **Dans le chat**, trois outils (skill `configuration`) :
  - `agent_options` (lecture) : le fournisseur et le modèle en cours, les fournisseurs configurés, chaque source avec
    sa sorte et son état, le serveur MCP ;
  - `turn_off_agent_options(sources, mcp_server)` : décoche des sources ou coupe le serveur MCP, sans question (cela
    ne fait que réduire ce que l'agent atteint) ;
  - `turn_on_agent_options(sources, mcp_server, provider)` : coche des sources, ouvre le serveur MCP ou change de
    fournisseur configuré ; demandé à l'utilisateur à chaque niveau d'autonomie, seul, comme `change_settings`.
- Un changement demandé par l'agent s'applique **à la fin de sa demande** : la conversation avec le modèle reprend
  avec les nouveaux outils sous le même fil (`_restart_engine`) ; un autre fournisseur ouvre un fil neuf
  (`_reset_view`), et l'outil le dit.

## Non-objectifs

- Saisir une clé, accepter l'envoi des données à un nouveau fournisseur, changer l'autonomie ou les règles des
  outils depuis le chat : jamais (un agent n'élargit pas seul ce qu'il atteint ni ne s'autorise lui-même). Ils
  restent dans la boîte de réglages.
- Annuler ces changements avec le tour : ils se défont du même menu.

## Contraintes

- Les sources sont celles de la boîte de réglages (`all_sources(custom) + qgis_databases()`), mêmes identifiants
  (`AgentSettings.enabled_sources`).
- Un clic dans le menu enregistre comme la boîte de réglages (`save_settings`) et suit la même suite : autres outils
  → `_restart_engine` ; autre fournisseur → `_reset_view` ; `_sync_mcp`, `_refresh_ready`.
- Fournisseurs configurés : une liste dans les réglages (`agent/providers`, JSON, 8 au plus, le plus récent en tête),
  complétée à chaque enregistrement d'un fournisseur accepté (accord coché) ; la clé reste dans la base
  d'authentification de QGIS (son `authcfg`).
- Textes visibles : 34 catalogues. Poids : les trois outils viennent avec la skill `configuration` (index du lot 1).

## Approches

1. **Menu « ⋯ » existant + trois outils du chat (retenue).** Peu d'interface nouvelle, mêmes chemins d'enregistrement
   que la boîte de réglages ; activer demande toujours l'accord.
2. Une barre d'interrupteurs permanente au-dessus du fil : plus visible, mais prend de la place dans un panneau déjà
   dense. Écartée.
3. Laisser l'agent tout changer sans question : contraire à la règle « un agent n'élargit pas seul ce qu'il atteint ».
   Écartée.
