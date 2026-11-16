# Régime de l'agent, lot 4 : le cache — plan d'implémentation

**Goal:** Le début d'une requête reste le même aussi longtemps que possible, pour que le cache de chaque fournisseur
(Anthropic, OpenAI, cache KV d'Ollama) le serve : dans une demande, après une compaction, et d'une conversation à
l'autre de mêmes réglages.

**Spec:** `docs/superpowers/specs/2026-11-16-agent-token-diet-design.md` (« Lot 4 — Le cache », « Anti-objectifs »).

**Constat sur main (dc7db692) :**
- Les notes qui dépendent des réglages (valeurs non partagées, filtrage seul, plateformes, bases, géocodeurs, sources
  non cochées, connecteurs) sont au milieu des instructions, avant l'index.
- Sans les familles, un outil d'une source cochée s'insère au milieu de la liste des outils (ordre du catalogue).
- Anthropic : seul le cache automatique (le dernier bloc). Une compaction réécrit l'historique : tout est réécrit en
  cache, outils et instructions compris ; une nouvelle conversation de mêmes réglages ne relit rien.
- Ollama : `num_ctx` est recalculé à chaque requête ; après une compaction il peut redescendre d'un palier puis
  remonter, et chaque changement recharge le modèle (cache KV perdu).
- Le banc ne vérifie pas qu'entre deux appels d'une même demande le début est identique.

## Tâches

1. **Instructions** (`core/agent/chat_setup.py`) : `SYSTEM_PROMPT`, puis l'index, puis les notes des réglages.
   Test : à réglages différents, le début commun couvre les instructions et l'index des outils constants.
2. **Ordre des outils** : `stable_order(tools)` met après les autres les outils dont la présence dépend d'un réglage
   (`SOURCE_TOOLS`, `run_pyqgis`), ordre relatif gardé ; appliqué par le contrôleur et par le banc. Un outil ajouté
   (`use_tools`, `load_skill`) va déjà en fin de liste : un test le garde.
3. **Anthropic** (`providers/anthropic_messages.py`) : un point de cache explicite sur le bloc des instructions, en plus
   du cache automatique de la fin (combinaison recommandée par la documentation d'Anthropic pour une boucle d'agent ;
   2 points sur 4). Les outils et les instructions sont relus après une compaction et d'une conversation à l'autre
   dans les 5 minutes.
4. **Ollama** (`providers/ollama_chat.py`) : `num_ctx` ne redescend jamais dans une conversation (le fournisseur est
   créé pour une conversation et garde le plus grand palier demandé).
5. **Banc** (`scripts/agent_request_weight.py`) : le modèle du cache d'Anthropic connaît le point des instructions ;
   `--conversation` vérifie qu'entre deux appels d'une même demande aux mêmes outils et au même `num_ctx`, chaque
   fournisseur relit tout l'appel précédent, et échoue sinon ; il chiffre ce qu'une seconde conversation de mêmes
   réglages relit dès sa première requête. Nouvelle référence si le coût baisse.

## Vérification

Tests unitaires, tests d'API (mcp 1.x et 2.x), `agent_eval.py` 116/116 avec et sans `--families`, `--conversation`,
bancs QGIS `check_agent_tools`, `check_agent_chat` et banc GUI en ltr et latest, flake8, revue `opus-reviewer`.
