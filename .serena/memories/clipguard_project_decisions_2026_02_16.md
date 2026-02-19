# ClipGuard — Decisions Fondatrices & Specifications
> **Date de creation** : 2026-02-16
> **Auteur** : Utilisateur (archivage par The Elder Scrolls)
> **Portee** : Permanent — Projet ClipGuard (independant de FilterMate)
> **Statut** : FIABLE — Decisions initiales validees

---

## 1. Concept General

**ClipGuard** est un cache webcam universel imprimable en 3D (FDM), concu pour etre :
- **Compatible tout laptop** : plage d'epaisseur de cadre 3.5 - 8.0 mm
- **Personnalisable** : modele OpenSCAD parametrique
- **Feature unique "Anti-Hacker"** : un symbole est visible par la webcam quand le cache est ferme, permettant a l'utilisateur de confirmer visuellement que la webcam est bien obstruee

---

## 2. Options de Prototypage Retenues

### Option 1 — Lithophanie

| Aspect | Detail |
|--------|--------|
| **Principe** | Epaisseur variable du PLA controle la translucidite |
| **Zones opaques** | 1.5 mm d'epaisseur |
| **Zones translucides** | 0.4 mm d'epaisseur |
| **Effet** | Le symbole apparait en silhouette lumineuse quand la lumiere ambiante traverse le PLA fin |
| **Visibilite** | Le symbole n'est visible QUE quand le cache est sur la webcam (lumiere par l'arriere) |
| **Materiau** | PLA blanc uniquement |
| **Avantages** | Mono-materiau, mono-extrudeur, zero post-traitement, effet "magique" |
| **Complexite** | Faible — impression directe |

### Option 2 — Slider 3 Positions

| Position | Fonction |
|----------|----------|
| **Position 1** | Ferme total — surface opaque, privacite maximale |
| **Position 2** | Ouvert — webcam libre, pas d'obstruction |
| **Position 3** | "Troll" — symbole ajoure/decoupe dans le slider, silhouette visible par webcam |

| Aspect | Detail |
|--------|--------|
| **Principe** | Symbole ajoure laisse passer la lumiere = silhouette visible par la webcam |
| **Avantages** | Plus polyvalent (3 etats distincts) |
| **Inconvenients** | Plus complexe mecaniquement |

---

## 3. Specifications Techniques

| Parametre | Valeur |
|-----------|--------|
| Plage epaisseur cadre laptop | 3.5 - 8.0 mm |
| Taille fenetre symbole | ~8 x 10 mm |
| Materiau principal | PLA (corps) |
| Materiau optionnel | TPU (pads de grip) |
| Impression | Sans supports, orientation a plat |
| Temps d'impression estime | 10 - 15 min |
| Cout matiere | < 0.30 EUR |
| Outil de conception | OpenSCAD (parametrique) |

---

## 4. Analyse de Marche

| Indicateur | Valeur |
|------------|--------|
| Marche mondial caches webcam | 1.2 milliard USD |
| Taux de croissance (CAGR) | 9.2% |
| Prix concurrents | 2 - 10 EUR/lot |
| **Differenciation ClipGuard** | Personnalisation parametrique + feature Anti-Hacker (aucun concurrent identifie) |

---

## 5. Decisions Cles a Prendre (Prochaines Etapes)

- [ ] Choix de l'option de prototypage prioritaire (Lithophanie vs Slider)
- [ ] Design du ou des symboles Anti-Hacker par defaut
- [ ] Validation du mecanisme de clip universel (3.5-8mm)
- [ ] Tests d'impression FDM et validation des tolerances
- [ ] Choix de la licence (open-source ? commerciale ?)

---

## References Croisees
- Aucune dependance avec le projet FilterMate
- Projet autonome — domaine : hardware / impression 3D / OpenSCAD
