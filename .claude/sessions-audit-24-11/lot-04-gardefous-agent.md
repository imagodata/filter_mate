# Lot 4 — Garde-fous de l'agent (Ask/Plan, tchat) (audit 24/11/2026)

## Contexte
Plugin FilterMate, base `main` à `a03bb9e0`. Promesse produit : en Ask et Plan « rien n'est changé ». Ne rien corriger hors de ce lot.

## Défauts à corriger
1. Ask/Plan contourné quand le dialogue des réglages s'ouvre à l'envoi (premier usage, consentement retiré) : enregistrer remet le niveau de l'onglet Autonomie, la demande part en « standard » avec la note « Ask ».
   - `agent_chat_controller.py:2667` puis `:1116` (#630) → reposer le niveau du mode après le dialogue.
2. « Continuer » après le Go d'un plan repart en Plan : rien ne s'exécute, nouveau Go.
   - `agent_chat_controller.py:3885` (#627, #630) → Continuer/Go dans le mode de la demande.
3. En Ask et Plan, `undo_agent_step`, `save_recipe`, `remove_recipe` et notes projet s'exécutent sans question (`AGENT_OWN` passe à tous les niveaux).
   - `core/agent/permissions.py:93` et `:350` → **trancher d'abord** : refuser ou demander ? (question ouverte de l'audit).
4. Demande en attente écrase le brouillon tapé pendant l'attente ; second Entrée remplace la première sans trace.
   - `ui/widgets/agent_panel.py:1629` (Qt5+Qt6) → garder le brouillon.
5. `run_chart_code` renvoie les valeurs au modèle malgré le réglage (erreur `throw new Error(JSON.stringify(data))` remontée telle quelle) → filtrer les erreurs.
   - `adapters/agent/chart_renderer.py:217`, `ui/controllers/agent_charts.py:169` (#613, #618)
6. Bannière « The model runs on this computer » fausse pour `-cloud` via Ollama local et hôte `127.x` (`startswith("127.")`).
   - `core/agent/local_model.py:13` (#665)
7. Second rang : après erreur fournisseur, demande « rendue » écrasée par celle en attente (`agent_chat_controller.py:3775`) ; Go/Continuer muet si envoi refusé (`:3832`) ; « Oui pour cette conversation » perdu via Ask/Plan (`permissions.py:428`) ; « Envoyer de nouveau » coupe à 500 caractères + journal en clair (`core/agent/request_log.py:14`, #661) ; ouverture réglages compte toutes les entités sur thread principal (`:1047`) ; `@` homonymes (`agent_panel.py:384`) ; bouton mode `max-width: 16777215px` (`agent_panel.py:1170`).

## Vérification
- Tests des modes + `check_agent_chat.py` verts (3.44 + latest 4.3).
- Preuve par exécution : Ask/Plan ne changent rien dans les 3 cas, brouillon conservé, bannière correcte. Rendre compte sans committer.
