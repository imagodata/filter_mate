# Lot C : le modèle choisi selon la tâche (mode auto)

Date : 2026-11-13. Statut : à approuver.

## Pourquoi

Un petit modèle (Haiku, mistral-small) suffit pour lire le projet, filtrer, sélectionner, zoomer ou exporter, et
coûte une fraction d'un grand. Un grand modèle (Sonnet, mistral-large) fait mieux pour une analyse, une mise en
page, plusieurs étapes dépendantes ou du code. Aujourd'hui, l'utilisateur choisit un seul modèle pour tout.

Décision de l'utilisateur (13/11) : un interrupteur « mode auto ». Le plugin choisit le modèle au début de chaque
demande, selon ce qu'elle demande. Il ne remonte pas au grand modèle après un échec (escalade écartée).

## Objectifs

- Mode auto : chaque demande part sur le petit ou le grand modèle du fournisseur choisi, d'après la demande.
- Mode manuel : un seul modèle, comme aujourd'hui.
- L'utilisateur voit quel modèle répond.

## Non-objectifs

- Changer de modèle au milieu d'une demande. Le cache de prompt est propre à chaque modèle : on ne change qu'entre deux
  demandes.
- Mélanger les fournisseurs : les deux modèles viennent du même fournisseur, avec la même clé.
- Ollama : un modèle local se charge en mémoire et en changer est lent. Le mode auto n'y est pas proposé.

## Approches

1. **Un appel de tri au petit modèle (retenue, mon choix).** Avant chaque demande, une requête minuscule au petit
   modèle : un prompt court, la demande de l'utilisateur et la classe de la demande précédente, sans outil, réponse
   en un mot (`SIMPLE` ou `COMPLEX`). Environ 300 tokens et moins d'une seconde. Ça marche dans toutes les langues.
2. **Une règle locale, sans appel** (mots-clés, longueur, skills chargés). Rien ne coûte, mais il faudrait des listes
   de mots dans 34 langues, et la règle se tromperait souvent sur des phrases courtes mais difficiles. Écartée.
3. **Le petit modèle démarre et passe la main** avec un outil. C'est changer de modèle au milieu de la demande : ça
   casse le cache, et c'est l'escalade que l'utilisateur a écartée.

## Conception

- **Réglages, onglet Fournisseur** :
  - un interrupteur « Choisir le modèle selon la demande » ;
  - quand il est activé, deux champs : modèle rapide et modèle puissant ;
  - valeurs par défaut : Anthropic `claude-haiku-5-5` et `claude-sonnet-5-5` ; Mistral `mistral-small-latest` et
    `mistral-large-latest` ; OpenAI à choisir dans la liste des modèles du fournisseur (lot B) ;
  - l'interrupteur est grisé pour Ollama, avec une infobulle qui dit pourquoi.
- **Tri** (`core/agent/model_routing.py`, sans QGIS) :
  - construction de la requête de tri et lecture de la réponse ;
  - `COMPLEX` pour une analyse (Processing), des styles, une mise en page, un tableau de bord, du code, plusieurs
    étapes qui dépendent les unes des autres, ou un raisonnement sur les données ;
  - `SIMPLE` pour lire, filtrer, sélectionner, zoomer, exporter ou répondre à une question sur le projet ;
  - une réponse illisible, une erreur ou un délai de plus de 5 secondes donne le modèle puissant (la qualité d'abord),
    et la raison est consignée dans le journal.
- **Envoi** : la session garde un fournisseur. Le modèle de chaque demande est passé à la construction de la requête.
  Le reste de la conversation (historique, outils, prompt) ne change pas.
- **Affichage** : l'en-tête du panneau affiche « auto » et le modèle de la demande en cours (par exemple
  « auto · haiku-5-5 »). Chaque réponse garde le nom du modèle qui l'a écrite, discret, en bas de la bulle.
- **Recettes** : rejouer une recette n'appelle pas de modèle, rien ne change.

## Risques à vérifier

- Anthropic : l'historique peut contenir des blocs de réflexion signés par l'autre modèle. Il faut vérifier sur
  l'API réelle qu'une conversation qui alterne Haiku et Sonnet est acceptée, sinon retirer ces blocs des tours passés.
- Le tri se trompe parfois. On mesure au banc : chaque cas de `agent_eval_cases.json` reçoit sa classe attendue. Le
  banc compare le score et le coût du mode auto, du petit modèle seul et du grand modèle seul.

## Ce qui reste au constructeur

- Le texte exact du prompt de tri, réglé au banc.
- Le passage du modèle par demande dans `Provider.build_request` (ou deux fournisseurs).
- Messages dans les 34 catalogues ; tests unitaires ; contrôle sans écran du dialogue.
