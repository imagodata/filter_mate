# Mémoire locale de l'agent : ce qu'il retient d'un projet à l'autre

Date : 2026-11-22. Statut : approuvé (22/11). Remplace la section « Mémoire de l'agent » du lot G
(`2026-11-13-preferences-by-source-design.md`) ; le reste du lot G ne change pas.

## Pourquoi

L'agent ne retient rien d'un projet à l'autre. Lu dans le code le 22/11 :

| Ce qui survit | Où | Ce que le modèle en reçoit |
|---|---|---|
| Notes de projet, 20 de 300 caractères | dans le `.qgz` (`FilterMateAgent/notes`) | tout, une fois par conversation |
| Fil de tchat, 20 projets | `QgsSettings`, par projet | un rappel des 6 dernières demandes, sans les réponses |
| Recettes, widgets, couches protégées | dans le `.qgz` | l'état envoyé avec la demande |
| Skills de l'utilisateur | `FilterMate/skills` du profil | à la demande (`load_skill`) |

Conséquences :

- Dans chaque nouveau projet, l'agent relit les mêmes couches (`describe_layer`, `field_values`) ou redemande à
  l'utilisateur ce que veut dire un mot du métier. Chaque lecture est un aller-retour de plus, et son résultat (8 000
  caractères au plus) reste dans l'historique jusqu'à la compaction.
- Un petit modèle qui ne sait pas devine. La barrière du régime de tokens l'a montré le 17/11 : `qwen3` écrivait
  « dep » pour « dept » ; 40 noms de champs ajoutés à l'état ont suffi (#530).
- D'autres agents pour QGIS proposent déjà des notes de mémoire : c'est devenu attendu.

Décisions de l'utilisateur :

- 13/11 (lot G) : une mémoire faite de notes et d'un glossaire métier, gardés d'un projet à l'autre, par source de
  données ou pour tous les projets ; pas de RAG dans le plugin.
- 16/11 : aucun code de cloud avant le 31/01/2027.
- 22/11 : la mémoire est locale et gratuite. Un agent hébergé n'apporterait ni vitesse ni tokens en moins.
- 22/11, sur six questions à choix : un fichier JSON plutôt qu'une table ; les deux outils de note étendus plutôt que
  deux outils nouveaux ; toujours une carte, pour garder comme pour oublier ; la borne des 20 000 reste, la place se
  reprend ailleurs ; l'option est activée par défaut ; un budget de 3 000 caractères, à confirmer au banc.

## Objectifs

- L'agent reçoit, dans tout projet, ce que l'utilisateur a choisi de garder : pour tous ses projets (`user`) ou pour
  une source de données (`source`). Les notes de projet restent ce qu'elles sont.
- Rien n'entre dans cette mémoire sans un clic de l'utilisateur sur le texte exact.
- L'utilisateur voit, corrige et supprime chaque note, et peut ouvrir le fichier qui les contient.
- La mémoire ne pèse rien quand elle est vide, et un poids borné sinon : au plus 3 000 caractères par conversation.
- Elle sert tous les fournisseurs, Ollama compris, et le mode « filtrage seul » d'un modèle local.
- Le gain est mesuré : sur des demandes qui emploient un mot du métier, au moins un appel de modèle en moins.

## Non-objectifs

- La synchronisation entre machines, le partage en équipe, un compte : phase 2 de la stratégie, après le 31/01/2027.
  Le fichier garde un identifiant et une date par note pour qu'une fusion reste possible ; rien d'autre n'est construit.
- Un RAG, des embeddings, un index de documents.
- Un apprentissage sans clic, ou un résumé des sessions passées écrit par un modèle.
- Le reste du lot G : préférences d'EXPLORING par source, historique des filtres, favoris des autres projets.
- Les serveurs MCP et l'API REST : une autre application ne lit ni n'écrit la mémoire.
- Les recettes : une recette rejouée n'appelle aucun modèle et ne garde aucun pas de note, comme aujourd'hui.

## Anti-objectifs

- **Une injection qui dure.** Un texte lu dans un résultat d'outil, une couche ou un connecteur qui demanderait à être
  gardé reviendrait dans tous les projets. Une note de projet ne touche qu'un projet ; celle-ci les touche tous.
- **Une valeur d'attribut envoyée contre le réglage.** Une note proposée par le modèle peut contenir une valeur lue
  dans les données ; l'utilisateur qui coupe ensuite « partager les valeurs » ne doit pas la voir repartir.
- **Un régime de tokens défait.** La partie fixe reste sous 20 000 caractères, le début d'une requête reste identique
  d'un appel au suivant, et le banc de poids ne monte pas de plus de 5 % mémoire vide.
- **Une note périmée qui l'emporte.** Ce que le projet dit maintenant passe avant toute note.
- **Un fichier écrasé.** Un fichier que l'utilisateur a modifié à la main et qui ne se lit plus n'est jamais réécrit.
- **Des identifiants gardés.** La signature d'une source ne contient ni mot de passe, ni utilisateur, ni jeton.

## Contraintes

- `core/agent` reste du Python pur, sans import QGIS.
- Python 3.10+, QGIS 3.22 à 4.x, Qt5 et Qt6.
- Les instructions sont construites une fois par conversation et ne changent pas pendant.
- Bornes testées aujourd'hui : partie fixe sous 20 000 caractères, un outil 2 000 au plus, une ligne d'index 60,
  l'index 4 800. Mesuré le 22/11 : le début d'une conversation pèse 19 581 à 19 981 caractères selon le fournisseur.
  Il reste donc une quarantaine de caractères.
- Tout texte visible passe par les 34 catalogues (skill `i18n-pipeline`) ; un module nouveau s'ajoute à
  `i18n/FilterMate.pro` (`tests/unit/test_i18n_pro_sources.py`).
- Le scan du dépôt de plugins (Bandit, detect-secrets) reste vert.

## Approches

1. **Étendre les notes actuelles par une portée (retenue).** Même famille d'outils, même en-tête « données », même
   chemin dans le contexte de la demande. C'est ce que le lot G avait décidé pour l'outil.
2. Des skills écrites par l'agent (`SKILL.md`) : écartée. Une skill est une consigne, pas une donnée : un modèle qui en
   écrit, c'est l'injection que l'on veut éviter. Une procédure longue reste une skill écrite par l'utilisateur.
3. Un index dans les instructions et un outil de rappel : écartée. Pour un fait de 300 caractères, la ligne d'index
   coûte autant que le fait ; les instructions différeraient d'un projet à l'autre ; et depuis le lot 3 du régime de
   tokens, une part du contexte n'est déjà envoyée qu'une fois par conversation.
4. Une mémoire automatique (résumé de fin de session par un modèle) : écartée. Un appel de plus par conversation, des
   valeurs gardées sans accord, et rien qui arrête une injection.
5. Une table `fm_agent_memory` dans `filterMate_db.sqlite`, comme l'écrivait le lot G : écartée pour un fichier JSON
   (décidé le 22/11). Un fichier se lit, se corrige, se copie sur une autre machine et se partagera comme le dossier des
   skills ; quelques centaines de notes n'ont pas besoin d'une base.

## Conception

### Trois portées

| Portée | Contenu type | Rangée | Envoyée quand |
|---|---|---|---|
| `project` (existe) | « Les parcelles sont la couche cadastre_2024 » | dans le `.qgz` | ce projet est ouvert |
| `source` (nouvelle) | « aérien = type_infra 'AER' » | fichier du profil, par signature | une couche de cette source est dans le projet |
| `user` (nouvelle) | « MRO = … », « réponds en mètres », « exporte en GeoPackage » | fichier du profil | toujours |

- La signature est celle des favoris : `LayerSignature.compute` (`core/domain/layer_signature.py`), par exemple
  `postgres::<schema>.<table>` ou `ogr::<layername>`.
- Deux bases qui ont le même `schema.table` partagent leurs notes. C'est voulu, comme dans le lot G : mêmes tables,
  nouveau projet. La carte et l'onglet montrent la signature.
- Une couche en mémoire, ou une couche temporaire produite par FilterMate ou par l'agent, n'a pas de portée `source` :
  sa signature ne tient pas. L'outil le dit.

### Stockage

- Un fichier `agent_memory.json` dans le dossier `FilterMate` du profil QGIS, à côté de `skills/`
  (même base que `adapters/agent/skill_sources.user_folder`).
- Forme :

  ```json
  {"version": 1, "next": 13,
   "notes": [{"id": "m12", "scope": "source", "signature": "postgres::reseau.troncons", "label": "troncons",
              "text": "aérien = type_infra 'AER'", "updated": "2026-11-22", "with_values": true}],
   "declined": ["mro = main release office"]}
  ```

- `id` est court et ne change jamais (`m` et un compteur) : c'est lui que le modèle nomme pour oublier une note.
- `label` est le nom de la couche à l'écriture ; il sert à l'onglet quand la source n'est pas dans le projet ouvert.
- Bornes : une note fait une ligne de 300 caractères au plus (`project_notes.clean`, réutilisé) ; 40 notes `user`,
  10 par signature, 500 en tout ; 100 textes refusés, les plus anciens sortent.
- Écriture : relire le fichier, fusionner par `id`, écrire dans un fichier temporaire puis `os.replace`. Deux QGIS
  ouverts sur le même profil ne se perdent pas de notes ; sur la même note, le dernier gagne.
- Un fichier illisible, ou d'une `version` plus récente : la mémoire est vide pour la session, le fichier n'est pas
  touché, toute écriture est refusée, et l'onglet le dit avec un bouton pour ouvrir le fichier.
- Code : `core/agent/memory.py` (lire, ajouter, retirer, choisir, composer le bloc) et
  `adapters/agent/memory_store.py` (chemin, lecture, écriture), sur le modèle de `project_notes.py` et
  `project_notes_store.py`.

### Ce que le modèle reçoit

- Une part `memory` de plus dans `ContextParts` (`core/agent/request_context.py`), après `notes`, ajoutée à
  `_REPEATED` : elle part avec la première demande d'une conversation, après une compaction, et quand elle a changé.
  Jamais dans les instructions : le début de la requête reste le même pour tous les utilisateurs.
- Le bloc : un en-tête, les notes `user`, puis les notes de chaque source présente, sous le nom que la couche porte
  dans le projet ouvert. Chaque note porte son `id`.
- L'en-tête dit quatre choses : ce sont des données gardées par l'utilisateur, jamais des consignes ; le projet tel
  qu'il est l'emporte ; une note qui ne tient plus se propose à l'oubli ; les notes en plus sont dans l'onglet.
- Budget : 3 000 caractères (`MAX_MEMORY_BLOCK`, à confirmer au banc). Quand tout ne tient pas, on remplit dans cet
  ordre : les notes de la couche active, les notes `user`, les autres sources dans l'ordre des couches ; les plus
  récentes d'abord dans chaque groupe. Une dernière ligne dit combien de notes ne sont pas parties.
- L'ordre d'affichage est fixe : `user`, puis les sources dans l'ordre des couches. Sous le budget, le bloc ne dépend
  donc pas de la couche active, et un changement de couche ne le renvoie pas.
- « Partager les valeurs » coupé : les notes `with_values` ne partent pas, et la dernière ligne les compte à part.
  `with_values` est vrai pour une note proposée par le modèle pendant que les valeurs étaient partagées. Une note
  tapée par l'utilisateur dans l'onglet part toujours : c'est son texte, comme ce qu'il tape dans le tchat.
- Mémoire vide : aucun caractère de plus.

### Écrire : l'agent propose, l'utilisateur clique

Règle unique : **le modèle ne modifie jamais la mémoire. Il propose ; l'utilisateur clique.** À tous les niveaux
d'autonomie, sans « toujours autoriser ».

- **Pas de nouvel outil** (décidé le 22/11) : l'index n'a pas la place d'une ligne de plus, et renommer un outil casserait
  les règles par outil déjà enregistrées dans les profils.
  - `add_project_note` gagne `scope` (`project` par défaut, `source`, `user`) et `layer`, obligatoire avec `source`.
  - `remove_project_note` accepte `memory`, l'`id` d'une note du bloc, à la place de `number`.
  - Leurs lignes d'index changent de texte, pas de nombre.
- `scope: project` : rien ne change. La note s'écrit aussitôt, quand l'utilisateur le demande.
- `scope: source` ou `user` : rien n'est écrit. Une carte paraît dans le fil et l'outil répond aussitôt « proposé » ;
  le tour continue sans attendre le clic.
- **La carte pour garder** :
  - le texte, modifiable avant de garder ;
  - les boutons « Tous mes projets », « Cette source (nom) », « Ce projet seulement », « Ne pas retenir », la portée
    proposée en premier ;
  - à sa première apparition, une phrase : gardé sur cet ordinateur, envoyé au modèle choisi quand le projet ouvert
    est concerné ;
  - après le clic, elle se fige, montre le choix et garde un bouton « Annuler ». Elle reste dans la transcription.
- **La carte pour oublier** : le texte de la note, « Oublier » et « Garder ».
- **Ce que le modèle apprend du clic** : à la demande suivante, la part `decided` du contexte dit ce qui a été gardé
  (portée, `id`, texte final) ou refusé. C'est le chemin des cartes de réglages (`_settings_outcomes`).
- **Garde-fous** :
  - un texte déjà gardé, ou déjà refusé (« Ne pas retenir »), ne refait pas de carte : l'outil le dit ;
  - deux propositions au plus par demande ;
  - une carte restée sans réponse (Arrêter, tour annulé, projet fermé) se fige en « non retenue », sans entrer dans
    les refus ;
  - une borne atteinte : la carte le dit et ouvre l'onglet.
- **Annuler le tour** ne retire pas une note gardée par un clic : c'est un geste de l'utilisateur. Le bouton
  « Annuler » de la carte et l'onglet la retirent.
- **Quand proposer** : la phrase des instructions « Keep a note or a recipe only when the user asks… » est réécrite.
  Une note de projet et une recette restent sur demande. Une note pour les prochains projets se propose une fois,
  quand l'utilisateur a dû expliquer un mot à lui, ou que l'agent a dû chercher quelle couche, quel champ ou quelle
  valeur il désigne. Jamais parce qu'un résultat d'outil, une couche ou un connecteur le dit.
- **La place** : cette phrase s'allonge d'environ 150 caractères et il en reste 40. Le lot reprend la place ailleurs
  dans les instructions, chiffres à l'appui. S'il ne le peut pas sans perdre un cas à la barrière, il s'arrête et
  demande : la borne des 20 000 est une décision de l'utilisateur (16/11, confirmée le 22/11).
- **Permissions** : les deux outils restent dans `AGENT_OWN`. Ils se lancent seuls à tous les niveaux, puisqu'une
  proposition ne change rien. `RULE_NEVER` dans l'onglet Outils les retire, comme aujourd'hui.

### Voir et corriger

- Un onglet « Mémoire » dans les réglages de l'agent (`SETTINGS_TABS` gagne `memory`, donc `show_settings_link` y
  mène) :
  - les notes par groupe : « Tous mes projets », puis chaque source avec son nom et sa signature ;
  - modifier, supprimer, ajouter à la main (pour tous les projets, ou pour une couche du projet ouvert) ;
  - « Envoyées avec ce projet : 12 sur 15 », et les notes retenues parce que les valeurs ne sont pas partagées ;
  - « Tout oublier » (avec confirmation) et « Ouvrir le fichier ».
- Une option « Mémoire d'un projet à l'autre » (`filter_mate/agent/memory`), activée par défaut : vide, elle n'envoie
  rien. Coupée : le bloc ne part plus, les outils reprennent leur forme d'aujourd'hui à la conversation suivante, et le
  fichier reste.
- `docs/AI_AND_DATA.md` gagne un paragraphe : ce qui est gardé, où, et ce qui part vers le modèle.
- `docs/AGENT_MODE.md` et le CHANGELOG suivent, comme pour chaque PR.

### Mesure

Deux bancs, deux questions.

- **Ce que la mémoire pèse** (`scripts/agent_request_weight.py --conversation`, sans réseau) :
  - mémoire vide : coût et plus grosse requête à moins de 5 % de la référence, et la partie fixe sous 20 000 ;
  - un mode `--memory` rejoue la même conversation avec un bloc plein. Estimation avant mesure : environ 6 % de coût
    en plus (3 000 caractères écrits en cache une fois, relus par 27 appels). Le budget se règle sur ce chiffre.
- **Ce que la mémoire fait gagner** (`scripts/agent_eval.py --live`, modèle local gratuit, puis un petit modèle
  distant si l'utilisateur le veut) :
  - des cas « vocabulaire » en paires, sans et avec la note : un mot du métier qui désigne une valeur (« aérien »),
    un nom d'usage pour une couche (« les parcelles »), un sigle (« MRO »), une préférence (« en mètres ») ;
  - par cas : réussite, nombre d'appels de modèle, caractères envoyés ; trois passages, comme la barrière ;
  - critère (mon choix) : aucun cas perdu, et la médiane des appels baisse d'au moins 1 avec la note.
- Le lot 2 ajoute des cas de comportement : l'agent propose après une explication de l'utilisateur ; il ne propose pas
  quand une valeur d'attribut ou la réponse d'un connecteur demande à être retenue.

### Lots

1. **Lire.** `memory.py`, `memory_store.py`, le bloc dans le contexte, l'option, l'onglet (notes écrites à la main),
   `AI_AND_DATA.md`, les deux bancs. Aucun outil ne change. L'utilisateur écrit son glossaire, et le gain se mesure.
   **Si le critère de gain n'est pas tenu, on s'arrête là et on le dit :** la mémoire serait un confort, pas une
   économie.
2. **Proposer.** Les portées des deux outils, les cartes, la part `decided`, les refus, la phrase des instructions,
   les cas de comportement, la barrière du régime de tokens.
3. **Passerelles**, après mesure : passer une note de projet en `source` ou en `user` depuis l'onglet ; exporter et
   importer le fichier pour un collègue. Pas de synchronisation.

Chaque lot : son worktree, les tests de `tests/` qui touchent l'agent, le banc de poids avant et après dans la
description de la PR, et `qgis-headless-bench` pour ce qui touche le dock.

## Rapport avec le lot G

- Cette spec reprend sa décision (notes et glossaire, par source ou pour tous les projets, sans RAG) et change trois
  choses : un fichier au lieu d'une table, une carte pour toute écriture qui dépasse le projet, un budget de
  caractères.
- La table `fm_agent_memory` n'est pas créée.
- Les deux lots partagent la signature de `LayerSignature.compute` et restent indépendants.

## Laissé au constructeur

- Le texte de l'en-tête, des deux descriptions d'outils, de la phrase des instructions et des cartes.
- Les bornes (40, 10, 500, 100) et le budget, après mesure.
- La liste des fournisseurs sans portée `source`, test à l'appui (`memory`, les couches virtuelles ; une signature
  faite du seul nom de la couche est-elle assez stable pour un WFS ?).
- Le style des cartes, d'après celles du fil (questions, proposition de réglages).
- Tests :
  - unitaires : lecture d'un fichier abîmé sans réécriture, écriture atomique et fusion par `id`, bornes, choix sous
    budget et ordre fixe, notes retenues quand les valeurs ne sont pas partagées, refus mémorisés, signature refusée,
    bloc vide ;
  - contrôle sans écran : un clic sur la carte écrit le fichier ; deux projets successifs sur le même GeoPackage, où
    le second reçoit la note de la source ; option coupée ; outil sur « jamais » ; tour annulé ; carte sans réponse.
