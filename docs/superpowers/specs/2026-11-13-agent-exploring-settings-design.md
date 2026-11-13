# Lot E : l'agent règle EXPLORING et les paramètres de chaque couche

Date : 2026-11-13. Statut : à approuver. Lots voisins : D (`ask_user`), F (réglages de QGIS).

## Pourquoi

EXPLORING montre les entités d'une couche avec un champ ou une expression par mode : sélection simple, multiple et
personnalisée. Au premier ajout d'une couche, une heuristique choisit ce champ (`get_best_display_field`,
`infrastructure/utils/layer_utils.py:439`) : l'expression d'affichage de QGIS, un ValueRelation, un champ qui ressemble
à un nom, un texte, la clé, puis le premier champ. Souvent, cela donne un identifiant ou un code peu parlant, et
l'utilisateur doit tout régler à la main, couche par couche.

Aucun outil ne peut aujourd'hui changer ces réglages ni les autres paramètres d'une couche. L'utilisateur veut que
l'agent les règle intelligemment.

## Ce qui existe (13/11, `main` f2ae0b7e)

- **Par couche, dans `PROJECT_LAYERS[layer_id]` :**
  - `exploring` : `single_selection_expression`, `multiple_selection_expression`, `custom_selection_expression`,
    `current_exploring_groupbox`, `is_selecting`, `is_tracking`, `is_linking` ;
  - `filtering` : `has_layers_to_filter`, `layers_to_filter`, `buffer_value`, `geometric_predicates`, etc.
- **Stockage :**
  - la table `fm_project_layers_properties` de la base de FilterMate ;
  - des variables de couche `filterMate_<groupe>_<clé>`, gardées dans le projet.
- **Écriture depuis le panneau :** `exploring_controller.exploring_source_params_changed`, puis le signal
  `settingLayerVariable`, puis `save_variables_from_layer`. Les widgets se mettent à jour par
  `_force_update_exploring_widgets`.

## Objectifs

- L'agent règle, pour une couche ou pour tout le projet :
  - les trois expressions d'EXPLORING, le mode actif, le suivi et la liaison ;
  - les paramètres de filtrage par défaut de la couche.
- Il choisit des libellés parlants en regardant les champs et les valeurs, et non le premier champ venu.
- Le changement passe par le même chemin que le panneau : les widgets suivent, c'est gardé avec le projet, et c'est
  annulé avec le tour.

## Non-objectifs

- Changer l'heuristique du premier ajout. Elle reste ; l'agent vient après, à la demande.
- Les réglages globaux de FilterMate : ils ont déjà leurs outils (`change_settings`).

## Conception

- **API publique** (`filtermate_api/`), dans un seul module, avec deux opérations :
  - `layer_options(layer)` lit les clés d'`exploring` et de `filtering` d'une couche, avec leurs valeurs et leurs choix ;
  - `set_layer_options(layer, changes)` écrit les clés demandées.
  - Les clés sont dans une liste blanche, avec des valeurs vérifiées :
    - une expression doit être valide pour la couche (`QgsExpression`, champs connus) ;
    - un mode doit être l'un des trois ;
    - les couches cibles doivent exister dans le projet ;
    - les prédicats doivent être dans la liste de FilterMate ;
    - le tampon doit être un nombre dans les bornes.
  - L'écriture suit exactement le chemin du panneau (dict, signal `settingLayerVariable`, mise à jour des widgets si la
    couche est celle du dock).
- **Outils de l'agent :**
  - `layer_options` (lecture) ;
  - `set_layer_options` (une couche ou plusieurs dans un seul appel, avec la raison du choix) ;
  - en classe de risque PROJECT : le changement s'affiche dans le fil, et il est annulé avec le tour comme un filtre
    (valeurs d'avant gardées par le point de reprise du tour) ;
  - les couches protégées par l'utilisateur sont refusées, comme partout.
- **Skill `exploring`** (nouveau, `skills/exploring/SKILL.md`), qui apprend la méthode :
  - lire `describe_layer` et `field_values` (si l'envoi des valeurs est autorisé) ;
  - choisir pour la sélection simple un libellé lisible et unique si possible, par exemple
    `"nom" || ' (' || "code_insee" || ')'` ;
  - pour la sélection multiple, un champ court qui se trie ;
  - ne jamais prendre un identifiant technique (fid, uuid, clé numérique) comme libellé quand un nom existe ;
  - sans valeurs partagées, partir des noms de champs et de l'expression d'affichage de QGIS ;
  - s'il y a un vrai choix à faire, le proposer par `ask_user` (lot D) ;
  - pour « règle tout le projet » : une proposition par couche dans un seul `ask_user` ou un seul appel, jamais une
    question par couche.
- **Mise en route** (skill `configuration`) : elle propose de régler EXPLORING pour les couches du projet ouvert.

## Ce qui reste au constructeur

- La liste blanche exacte des clés de `filtering` (lire `configuration_manager.get_layer_properties_tuples_dict`).
- L'ordre de mise à jour des widgets quand la couche réglée n'est pas celle du dock.
- Les messages dans les 34 catalogues.
- Tests :
  - unitaires : vérifications des valeurs, liste blanche, couche protégée ;
  - contrôle sans écran : l'outil change l'expression, le combo d'EXPLORING suit, et l'annulation du tour remet
    l'ancienne ;
  - un cas du banc : sur une couche communes, l'agent choisit un libellé avec le nom et pas `fid`.
