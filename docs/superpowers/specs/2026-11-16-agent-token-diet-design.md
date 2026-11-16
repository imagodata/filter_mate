# L'agent au plus léger : les outils strictement nécessaires, un historique qui ne gonfle pas

Date : 2026-11-16. Statut : approuvé (16/11).

## Pourquoi

Chaque appel au modèle renvoie les instructions, les outils offerts et toute la conversation. Mesuré le 16/11 sur
`main` (`ea17184f`) :

| Part de la requête | Aujourd'hui |
|---|---|
| Instructions (`SYSTEM_PROMPT`) | 10 333 caractères |
| 71 outils du chat | 91 962 caractères |
| Outils offerts au départ, familles activées (défaut) | 30 outils, 39 566 caractères |
| Outils les plus lourds parmi les 30 | `cross_filter` 6 255, `geometry_filter` 2 477, `point_cloud_filter` 2 123, `apply_filter` 1 857 |
| Notes des sources cochées (dans les instructions) | 864 à 2 086 caractères |
| État du projet, à chaque demande | jusqu'à 30 couches + notes, widgets (JSON), recettes, couches protégées ; chaque copie reste dans l'historique |
| Résultat d'un outil | jusqu'à 20 000 caractères (`tool_executor.MAX_RESULT_CHARS`), gardé tel quel |
| Historique avant compaction | 120 000 caractères (`AgentLimits.max_history_chars`) |

Soit environ 50 000 caractères (≈ 14 000 tokens) avant le premier mot de l'utilisateur, et une conversation qui peut
monter à 170 000 caractères par appel avant que la compaction n'intervienne, pour chaque tour de modèle d'une demande.

Décision de l'utilisateur (16/11) : tout optimiser au maximum, pour tous les fournisseurs, en commençant par **ne
proposer au modèle que les outils strictement nécessaires** ; le modèle choisit lui-même dans un catalogue.

## Objectifs

- Une requête ne porte que les outils dont la demande en cours a besoin : un noyau minimal, plus ceux que le modèle
  a demandés.
- La partie fixe (instructions + outils offerts au départ) passe de ~50 000 à **moins de 20 000 caractères**, dans
  la configuration par défaut : familles activées, aucune source cochée, ni filtrage seul ni Python expert, index
  compris. La cible est tenue à la fin du lot 2 ; un dépassement après le seul lot 1 est accepté (mon choix).
- L'historique grossit moins vite : état du projet en différence, anciens résultats d'outils raccourcis, budget de
  compaction adapté au fournisseur.
- Le début de la requête reste stable d'un appel au suivant, pour que le cache (Anthropic, OpenAI, et le cache KV
  d'Ollama) serve au maximum. Une réécriture de l'historique ne se fait qu'à un moment où le cache est de toute façon
  perdu.
- Chaque lot est chiffré par le même banc de mesure, avant et après.

## Non-objectifs

- Un appel de tri au modèle pour choisir les outils (routeur en deux temps) : écarté, un appel de plus par demande et
  un doublon des familles.
- Une présélection locale par mots-clés : écartée, le plugin parle 34 langues.
- Les fonctions propres à Anthropic (outils chargés à la demande côté serveur, effacement automatique des anciens
  résultats) : peut-être plus tard, pour Anthropic seulement, après vérification de leur fonctionnement exact.
- Le serveur MCP du plugin : les autres applications reçoivent toujours tous les outils.
- Le choix du modèle selon la tâche (lot C) : inchangé.

## Anti-objectifs

- Une baisse de qualité : le banc `scripts/agent_eval.py` ne doit perdre aucun cas, ni en mode scripté ni en appel
  réel sur un petit modèle.
- Un modèle qui dit « je ne peux pas » parce que l'outil n'est pas encore offert, alors que le catalogue le contient.
- Un gain en caractères payé par un cache cassé à chaque appel (plus cher au total chez Anthropic, où une lecture en
  cache coûte un dixième).
- Toucher aux permissions, à l'annulation par tour, aux couches protégées.

## Contraintes

- `core/agent` reste du Python pur, sans import QGIS (les scripts de mesure et les tests le chargent seul).
- Python 3.10+, QGIS 3.22 à 4.x.
- Tout texte visible par l'utilisateur passe par les 34 catalogues (`i18n-pipeline`).
- Les instructions sont construites une fois par conversation (`agent_chat_controller._prompt`) : elles restent
  constantes pendant la conversation.
- Les options existantes restent respectées : règles par outil (`RULE_NEVER`), filtrage seul pour un modèle local,
  Python expert, connecteurs.
- Ollama : `num_ctx` monte par paliers (16k, 32k, 64k) ; changer de palier recharge le modèle.

## Approches

1. **Optimisation dans le code de l'agent, par lots mesurés (retenue par l'utilisateur).** Valable pour Ollama,
   OpenAI et Anthropic ; chaque gain est chiffré ; plus de travail.
2. **Les fonctions intégrées d'Anthropic.** Moins de code, mais rien pour Ollama ni OpenAI. Écartée pour l'instant.
3. **Un routeur en deux temps** (un premier appel choisit les outils). Un appel de plus par demande, plus lent, et
   une erreur de tri coûte la demande. Écartée.

Pour choisir les outils, dans l'approche 1 :

- **a. Le modèle choisit dans un catalogue (retenue par l'utilisateur).** Un noyau offert d'office, un index d'une
  ligne par outil dans les instructions, un outil `use_tools` qui ajoute exactement les outils nommés. Un aller-retour
  de plus quand un outil manque, léger puisque la requête l'est.
- b. Présélection locale en Python : écartée (34 langues).

## Conception

### Lot 0 — Le banc de mesure

`scripts/agent_request_weight.py` gagne un mode `--conversation` : il rejoue, avec un modèle scripté (comme le mode
sans `--live` de `agent_eval.py`), une conversation type d'une dizaine de demandes sur le projet simulé du banc —
filtres attributaires, un filtre croisé, un style, une statistique, un export — et imprime pour chaque appel :

- les caractères envoyés, séparés en instructions, outils, historique ;
- la longueur du début identique à l'appel précédent (la part que le cache peut servir), mesurée sur le corps réel
  que construit `build_request` de chaque fournisseur (Anthropic, OpenAI, Ollama), dans son ordre de sérialisation :
  plus long préfixe commun en caractères ;
- le palier `num_ctx` Ollama demandé.

Et un total sur la conversation, plus un **coût estimé** au tarif relatif d'Anthropic (entrée non servie par le
cache 1, écriture en cache 1,25, lecture en cache 0,1, en caractères). Critère d'un lot (mon choix) : le coût estimé
et la plus grosse requête de la conversation baissent ; aucun des deux ne monte de plus de 5 %. Les chiffres du 16/11 deviennent la référence, notée dans le script comme
aujourd'hui (`NOTES_OF_SOURCES`). Un test vérifie que le mode tourne sans réseau.

### Lot 1 — Les outils strictement nécessaires

- **Le noyau**, offert d'office : `use_tools`, `load_skill`, `ask_user` et les outils sans lesquels la demande la
  plus courante (filtrer une couche sur un champ) ne se fait pas en un tour : `apply_filter`, `field_values`,
  `describe_layer`, `clear_filters`, `undo_agent_step`. La liste exacte se décide au lot 1, chiffres du banc à
  l'appui ; elle vit dans `core/agent/families.py` à la place de `ALWAYS`.
- **L'index** : chaque `ToolSpec` gagne un champ `summary` (une ligne, 90 caractères au plus, en anglais comme les
  descriptions). Les instructions finissent par un bloc « Tools you can add with use_tools » qui liste, dans un ordre
  fixe, le nom et le `summary` de chaque outil offert à cette conversation mais pas encore dans la requête (règles,
  filtrage seul, expert et connecteurs déjà appliqués). Construit avec les instructions, donc constant pendant la
  conversation. Un test borne sa taille.
- **`use_tools(names)`** : ajoute à la requête suivante les outils nommés (`ChatEngine.offer_tools`, déjà là pour
  `load_skill`), en fin de liste et dans l'ordre demandé ; répond la liste ajoutée. Un nom inconnu ou refusé par une
  règle : une erreur qui le dit, sans rien ajouter. Lecture seule, sans confirmation. Un outil déjà offert : ignoré.
- **Le prix d'un ajout** : chez les trois fournisseurs les outils précèdent les instructions et les messages ; un
  outil ajouté, même en fin de liste, oblige à remettre en cache tout ce qui suit. Accepté (mon choix) : tôt dans une
  conversation la requête est courte, et c'est le prix d'outils stricts. Pour le limiter, les instructions demandent
  au modèle d'ajouter **en un seul appel** tous les outils dont la demande aura besoin, et un outil ajouté reste
  jusqu'à la prochaine compaction. Le banc chiffre ce coût.
- **`load_skill`** continue d'apporter les outils de sa skill, comme aujourd'hui.
- **Un outil retenu** (`ToolExecutor.hold`) appelé quand même : la réponse dit d'appeler `use_tools` d'abord, comme
  aujourd'hui pour les familles.
- **Retrait des outils inutilisés** : un outil ajouté qui n'a pas servi pendant les 3 dernières demandes sort de la
  requête, mais **seulement quand la compaction réécrit l'historique** (le cache est alors perdu de toute façon). Il
  repasse dans l'index.
- **Les familles** deviennent ce mode : l'option existante (`offer_tools_by_task`, activée par défaut) reste la même
  clé ; désactivée, tous les outils sont offerts comme aujourd'hui. Son libellé change si le sens change (34
  catalogues).
- **Les instructions** perdent les paragraphes qui décrivent un outil un par un (styles, mises en page, champs,
  groupes, thèmes, signets, widgets, édition…) : l'index et la description de l'outil ajouté les portent. Restent la
  manière de travailler et les règles transverses (ne jamais deviner un nom, filtrer plutôt que créer une couche,
  éditer seulement sur demande, dire que les éditions ne sont pas sauvées). Ce qui est propre à une tâche va dans sa
  skill. Une consigne s'ajoute : ne pas appeler un outil de lecture quand l'état du projet envoyé contient déjà la
  réponse.

### Lot 2 — Des outils plus courts

- Les descriptions et schémas des outils les plus lourds sont réécrits : `cross_filter` et `set_layer_style` d'abord,
  puis tout outil au-dessus de 1 500 caractères. Les exemples longs et les cas rares vont dans la skill de la tâche.
- Les schémas perdent ce qui ne guide pas le modèle (titres, valeurs par défaut redites dans la description,
  descriptions de propriété qui répètent leur nom).
- Un test borne le poids de chaque outil (2 000 caractères) et celui du noyau.

### Lot 3 — Un historique qui ne gonfle pas

- **L'état du projet en différence** : la nouvelle demande porte l'état complet quand elle est la première de la
  conversation ou qu'une compaction vient de réécrire l'historique ; sinon, seulement la liste « changed since » que
  `project_summary(before=…)` sait déjà faire, ou la ligne « Project unchanged since the last request. ». Notes,
  widgets, recettes et couches protégées : envoyés quand ils ont changé, omis sinon. Ajout seul en fin de
  conversation : le cache tient.
  Câblage (mon choix) : `AgentSession.add_user_text` compacte d'abord, puis demande le contexte par une fonction
  `context(full: bool)` que le contrôleur lui passe (au lieu d'une chaîne déjà faite) ; `full` vaut vrai à la
  première demande et après une compaction. Les anciens messages ne sont jamais réécrits pour leur état.
- **Les anciens résultats d'outils raccourcis** : premier étage de la compaction, avant de résumer des demandes
  entières : les résultats des demandes anciennes (toutes sauf les 2 dernières) deviennent une ligne « résultat de N
  caractères retiré, rappeler l'outil au besoin », l'appel gardé. Si cela suffit à repasser sous le budget, aucune
  demande n'est résumée (voulu). Seulement à une compaction.
- **Plafond d'un résultat** : de 20 000 à 8 000 caractères, avec la marque `truncated` existante qui dit comment
  demander la suite quand l'outil le permet.
- **Budget de compaction selon le fournisseur** : Ollama le dérive du palier de 32k moins la partie fixe ; les
  fournisseurs distants passent de 120 000 à 60 000 caractères. Chiffres à confirmer au banc.

### Lot 4 — Le cache

- L'ordre des outils reste fixe ; un outil ajouté va en fin de liste.
- Les notes des sources cochées sortent du milieu des instructions pour leur fin, après l'index : rien de ce qui
  dépend d'un réglage ne précède une partie constante. Le gain vaut d'une conversation à l'autre (le noyau et le
  début des instructions restent en cache entre deux conversations de mêmes réglages) ; dans une conversation, les
  instructions ne changent déjà pas.
- Le banc du lot 0 vérifie qu'entre deux appels d'une même demande, tout le début est identique.

### Ordre et vérification

Lot 0, puis 1, 3, 2, 4 (le plus gros gain d'abord). Chaque lot : son worktree, les tests de `tests/` qui touchent
l'agent, le banc de poids avant/après dans la description de la PR, `agent_eval.py` en mode scripté. Les lots 1 et 2
changent ce que lit le modèle : la barrière de qualité (décision de l'utilisateur, 16/11) est un passage réel de
`agent_eval.py --live --provider ollama --model qwen3:8b`, gratuit et local, sans fournisseur payant. Une référence
est prise sur `main` avant le lot 1. Chaque cas tourne 3 fois ; un cas est perdu s'il passait au moins 2 fois sur 3
sur la référence et passe au plus 1 fois sur 3 après. Aucun cas perdu : condition pour fusionner les lots 1 et 2. Les changements du dock passent par `qgis-headless-bench`.

## Laissé au constructeur

- La liste exacte du noyau, chiffres à l'appui.
- Le texte des `summary`, de l'index et des instructions raccourcies.
- La forme exacte de la différence d'état du projet.
- Les budgets de compaction, après mesure.
