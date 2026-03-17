# V01 — Installation & Premier Pas (~6min25)

> 57 cues · 7 séquences (s00-s06) · 8 diagrammes

---

## s00 — Hook (3 cues, ~15s)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Hook intro | "Un million de bâtiments... Temps de réponse ? Deux secondes." | Hold intro card |
| 1 | Bienvenue | "Bienvenue dans FilterMate." | Switch scène QGIS, focus |
| 2 | Présentation vidéo | "Dans cette première vidéo, on va installer... en moins de 7 min." | Pan souris sur la carte |

---

## s01 — Installation (6 cues, ~30s)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Présentation couches | "Notre projet contient déjà deux couches..." | Focus QGIS |
| 1 | Activation couches | "Activons-les dans le panneau de couches." | Toggle départements + communes |
| 2 | Gestionnaire extensions | "L'installation se fait en 3 clics..." | Ouvre Plugin Manager |
| 3 | Recherche FilterMate | "Dans l'onglet Toutes, tapez FilterMate." | Clic All + tape FilterMate |
| 4 | Plugin trouvé | "Le plugin apparaît. Cliquez sur Installer." | Sélection + hover Install |
| 5 | Conclusion install | "FilterMate est gratuit, open source..." | Diagramme `v01_install_flow` + ferme dialog |

---

## s02 — Premier lancement + Interface (15 cues, ~95s)

### Lancement (cue 0)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Lancement FilterMate | "Cliquez sur son icône dans la barre d'outils..." | Focus QGIS + ouvre FilterMate |

### Les 3 zones (cues 1-5)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 1 | Introduction interface | "Prenons un moment pour comprendre l'interface. 3 zones..." | Focus FilterMate |
| 2 | Zone d'Exploration | "En haut, la Zone d'Exploration..." | Mouvement circulaire sur exploring_zone |
| 3 | Toolbox + onglets | "En bas, la Toolbox. 3 onglets : FILTERING, EXPORTING, CONFIGURATION." | Highlight toolbox + cycle FILTERING → EXPORTING → CONFIGURATION → retour FILTERING |
| 4 | Header badges | "La pastille orange = favoris, bleue = backend actif." | Hover badge favoris + backend |
| 5 | Diagramme zones | *(pas de narration)* | Diagramme `v01_interface_zones` 5s |

### Couche source (cues 6-9)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 6 | Sélection couche source | "Configurons la couche source. Départements dans Filtering." | Switch FILTERING + sélection combo |
| 7 | Synchro couche source | "J'active la synchronisation avec le panneau de couches." | Clic btn_auto_current_layer |
| 8 | Clic communes | "Je clique sur communes. La couche source se met à jour." | Clic layer_panel communes |
| 9 | Retour départements | "Je reviens sur départements. Synchronisation immédiate." | Clic layer_panel départements |

### Exploration (cues 10-14)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 10 | Champ d'affichage | "Je change le champ d'affichage." | Clic combo + Ctrl+A + tape NOM_DEPT + Enter |
| 11 | Feature picker clavier | "Je clique dans le sélecteur et je navigue avec les flèches." | Clic feature_selector + bas x2 |
| 12 | Navigation next/prev | "Bouton précédent puis suivant. Navigation immédiate." | Clic prev + clic next |
| 13 | Auto-détection | "Le sélecteur affiche le nom, pas un identifiant cryptique..." | Hover feature_selector |
| 14 | Diagramme auto-détection | "C'est automatique." | Diagramme `v01_display_field_detection` 5s |

---

## s03 — Barre latérale : 6 boutons (8 cues, ~55s)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Intro sidebar | "La Zone d'Exploration possède 6 boutons. Voyons-les en action." | Focus FM + hover sélecteur |
| 1 | Identify | "Identify. L'entité clignote en rouge sur la carte." | **Clic** sidebar_identify |
| 2 | Zoom | "Zoom. La carte se centre et zoome." | **Clic** sidebar_zoom |
| 3 | Select | "Select ON → next → surbrillance → OFF." | **Clic** ON + next + **clic** OFF |
| 4 | Track | "Track. Suivi automatique. La carte suit chaque sélection." | **Clic** sidebar_track + next x2 |
| 5 | Link | "Link. Déjà actif par défaut. Synchronise les 3 groupes." | Hover sidebar_link |
| 6 | Reset | "Reset réinitialise l'exploration. On ne le déclenche pas." | Hover sidebar_reset |
| 7 | Diagramme sidebar | *(pas de narration)* | Diagramme `v01_sidebar_buttons` 5s |

---

## s04 — Premier filtrage (11 cues, ~75s)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Introduction démo | "Passons à la pratique. Deux couches chargées." | Focus FM |
| 1 | Navigation entité | "Avec suivant et précédent, je me place sur un département." | next + next |
| 2 | Onglet FILTERING | "FilterMate a reconnu ma sélection." | Switch FILTERING |
| 3 | Couche cible | "En couche cible, je choisis communes." | select_target_layer |
| 4 | Prédicat | "Prédicat spatial : Intersects." | select_predicate |
| 5 | Clic Filter | "Je clique sur Filter." | click_action_button filter |
| 6 | Résultat | "35 000 communes filtrées instantanément." | Pan souris sur carte |
| 7 | Undo | "Undo. Toutes les communes réapparaissent." | click undo |
| 8 | Redo | "Redo. Le filtre est rétabli." | click redo |
| 9 | Unfilter | "Unfilter retire tous les filtres. Chaque action est réversible." | click unfilter |
| 10 | Backend OGR | "FilterMate a détecté le backend OGR automatiquement." | Hover badge + diagramme `v01_first_filter_workflow` |

---

## s05 — Configuration & Debug (10 cues, ~45s)

### Langues (cues 0-4)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Intro langues | "FilterMate parle 22 langues..." | Focus FM |
| 1 | Changement EN | "La langue se change dans la configuration..." | Ouvre config + change → en + ferme |
| 2 | Interface EN | "Toute l'interface se met à jour immédiatement." | Focus FM |
| 3 | Diagramme langues | *(pas de narration)* | Diagramme `v01_languages` 4s |
| 4 | Retour FR | "Repassons en français." | Ouvre config + change → fr + ferme |

### Mode verbose (cues 5-7)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 5 | Intro verbose | "Activez le mode verbose. Changez FEEDBACK_LEVEL." | Ouvre config + change → verbose + ferme |
| 6 | Démo verbose | "FilterMate vous explique tout. 3 niveaux." | Switch FILTERING + filter |
| 7 | Diagramme feedback | *(pas de narration)* | Diagramme `v01_feedback_levels` 4s |

### Panneau de logs (cues 8-9)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 8 | Panneau de logs | "FilterMate écrit ses logs dans le panneau standard QGIS." | Ouvre log panel + clic onglet FM |
| 9 | Entrées de log | "Requêtes SQL, temps d'exécution, erreurs." | Filter + clic onglet log |

---

## s06 — Persistance & Conclusion (4 cues, ~25s)

| Cue | Label | Narration | Actions |
|-----|-------|-----------|---------|
| 0 | Persistance SQLite | "Tout est sauvegardé automatiquement. SQLite locale." | Focus FM + highlight dock |
| 1 | Diagramme persistance | *(pas de narration)* | Diagramme `v01_persistence` 5s |
| 2 | Conclusion | "Voilà, vous avez installé, découvert, filtré... Pas mal pour 7 min !" | Switch scène Outro |
| 3 | Ressources & CTA | "GitHub, dépôt QGIS, documentation. Prochaine vidéo..." | Hold outro 8s |

---

## Diagrammes utilisés

| ID | Séquence |
|----|----------|
| `v01_install_flow` | s01 |
| `v01_interface_zones` | s02 |
| `v01_display_field_detection` | s02 |
| `v01_sidebar_buttons` | s03 |
| `v01_first_filter_workflow` | s04 |
| `v01_languages` | s05 |
| `v01_feedback_levels` | s05 |
| `v01_persistence` | s06 |

---

## Flow narratif

```
s00 Hook → s01 Installation → s02 Lancement + Interface
→ s03 Sidebar (démo live) → s04 Premier filtrage → s05 Config & Debug
→ s06 Persistance & Conclusion
```

## État à la fin de chaque séquence

| Seq | État laissé |
|-----|-------------|
| s00 | Scène QGIS Fullscreen, carte visible |
| s01 | Couches activées, Plugin Manager fermé |
| s02 | FilterMate ouvert, départements sélectionné, EXPLORING, NOM_DEPT, synchro ON |
| s03 | Track ON, entité quelques pas après Seine-et-Marne |
| s04 | Filtres retirés (unfilter), FILTERING tab |
| s05 | Langue FR, verbose ON, log panel ouvert |
| s06 | Scène Outro |
