---
name: Pas de batch destructif large
description: L'utilisateur préfère valider chaque suppression majeure plutôt qu'un batch de 20+ opérations destructives parallèles
type: feedback
originSessionId: 04ffee9f-d166-4bfb-8e9c-251c39a97c3e
---
Lors d'un audit deep de la feature exporting (2026-04-30), j'ai lancé 27 `safe_delete_symbol` en parallèle pour purger les delegates orphelins de `integration.py`. L'utilisateur a interrompu et fait `git reset --hard origin/main`, perdant aussi les suppressions précédentes (`export_service.py`, `ExportTask`, etc.) qui semblaient pourtant validées.

**Why:** Une rafale de 20+ outils destructifs successifs sans pause de validation est trop opaque. L'utilisateur perd la visibilité sur ce qui se passe, ne peut pas intervenir granulairement, et préfère tout reset que démêler après coup.

**How to apply:**
- Pour suppressions multiples (>5), proposer un plan détaillé puis demander OK avant d'exécuter par lot
- Préférer petits commits atomiques avec pause entre chaque pour permettre revue/abort
- Pour suppressions massives même "sûres", lister précisément ce qui va sauter et attendre validation explicite — un "continuer" générique ne couvre pas 27 deletes
- Quand le user dit "continuer" sur une question à choix multiples, demander lequel plutôt qu'avancer sur tous les fronts
