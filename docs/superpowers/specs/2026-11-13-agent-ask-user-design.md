# Lot D : l'agent pose ses questions comme Claude Code

Date : 2026-11-13. Statut : à approuver. Lots voisins : E (EXPLORING), F (réglages de QGIS).

## Pourquoi

Aujourd'hui, quand l'agent a besoin de l'utilisateur, il écrit ses questions dans sa réponse. C'est le cas dans la
mise en route (« trois ou quatre questions en un message »), dans les réglages et dans les demandes ambiguës.
L'utilisateur doit ensuite répondre à la main dans la ligne de saisie. Seules les confirmations d'action ont une boîte
oui/non (`ask_plain`, `ask_code`).

L'utilisateur veut des questions interactives comme dans Claude Code : des choix cliquables, une réponse libre
possible, et l'agent qui continue avec la réponse.

## Objectifs

- Un outil `ask_user`, propre au chat, qui affiche dans le fil une carte de questions à choix et rend la réponse à
  l'agent dans le même tour.
- Les skills qui posent des questions l'utilisent : `configuration` (mise en route), EXPLORING (lot E), réglages de
  QGIS (lot F), données à chercher.

## Non-objectifs

- Remplacer les confirmations d'action (permissions). Elles gardent leurs boîtes : une question n'autorise rien.
- Les recettes : une recette rejouée n'appelle aucun modèle ; un pas `ask_user` n'y est pas gardé.
- Le serveur MCP du plugin : l'application cliente a ses propres moyens de demander, l'outil n'y est pas listé.

## Anti-objectifs

- Une réponse qui vaudrait accord pour une action. La réponse est une donnée pour le modèle ; une action qui en découle
  passe toujours par les permissions.
- Une carte qui bloque QGIS. L'utilisateur peut faire défiler le fil, lire la carte, et Arrêter.

## Approches

1. **Outil `ask_user` et carte dans le fil (retenue par l'utilisateur).** C'est un appel d'outil comme un autre :
   l'exécuteur attend la réponse, puis le tour continue.
2. Une syntaxe dans le texte, que le panneau transforme en boutons : écartée, car fragile si le modèle écrit mal la
   syntaxe.

## Conception

- **Outil** (`core/agent/tool_catalog.py`, avec les outils propres au chat, géré par l'agent lui-même) :
  - entrée : `questions`, une liste de 1 à 4 questions ;
  - chaque question a `question` (texte, 300 caractères au plus), `header` (12 au plus) et `multi_select` (booléen) ;
  - chaque question a 2 à 4 `options`, avec `label` (60 au plus) et `description` (200 au plus) ;
  - le panneau ajoute toujours « Autre » en texte libre ;
  - la description dit quand s'en servir : une décision qui revient à l'utilisateur et change ce que l'agent va
    faire ; pas pour ce que le projet ou les outils de lecture disent déjà ; mettre en premier le choix recommandé,
    suivi de « (Recommended) ».
- **Réponse** : pour chaque question, les libellés choisis, ou le texte de « Autre ». Si l'utilisateur ferme la carte
  ou appuie sur Arrêter, l'agent reçoit `{"declined": true}`. Le texte libre est borné (1 000 caractères) et traité
  comme une donnée, jamais comme une instruction.
- **Carte** (`ui/widgets/agent_panel.py`, dans le fil) :
  - par question, l'en-tête en puce et le texte ;
  - les choix en boutons à bascule (cases à cocher si `multi_select`) avec leur description en dessous ;
  - le champ « Autre » et le bouton Répondre, actif quand chaque question a une réponse ;
  - au thème du panneau, clair et sombre ;
  - au clavier : Tab, Espace, Entrée.
  - Après la réponse, la carte se fige et montre ce qui a été choisi. Elle est gardée dans la transcription.
- **Attente** : le gestionnaire de l'outil attend la réponse sans bloquer QGIS, dans une boucle d'événements locale.
  Arrêter la termine, comme les attentes actuelles du chat (`owned_by(CHAT_WAITS)`). Le décompte des tours du modèle
  n'avance pas pendant l'attente.
- **Permissions** : `ask_user` ne change rien et se lance seul à tous les niveaux. Il est absent de l'onglet Outils.
- **Skills** :
  - `configuration` (mise en route) pose ses trois ou quatre questions avec `ask_user` ;
  - les skills des lots E et F l'utilisent pour leurs choix ;
  - le prompt système dit d'utiliser `ask_user` plutôt qu'une question écrite quand les choix peuvent être nommés.
- **Fournisseurs** : un outil ordinaire. Avec Ollama et `local_filtering_only`, il fait partie des outils gardés : il
  est léger.

## Ce qui reste au constructeur

- Le style exact de la carte, d'après les cartes existantes du fil (proposition de réglages, étapes).
- Les messages visibles dans les 34 catalogues (skill `i18n-pipeline`).
- Tests :
  - unitaires : schéma, bornes, réponse, refus ;
  - contrôle sans écran de la carte : clic, multi-choix, Autre, Arrêter ;
  - un cas du banc où la mise en route doit appeler `ask_user` avant tout changement.
