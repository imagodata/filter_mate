# Lot E : l'agent règle EXPLORING, FILTERING et EXPORTING

Date : 2026-11-13, étendu le 2026-11-16. Statut : approuvé le 13/11 ; extension à EXPORTING demandée le 16/11 (« ok go »).
Lots voisins : D (`ask_user`), F (réglages de QGIS), régime de tokens (`2026-11-16-agent-token-diet-design.md`).

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
  - des variables de couche `<groupe>_<clé>` (par exemple `exploring_single_selection_expression`), gardées dans le
    projet (corrigé le 16/11 : le préfixe `filterMate_` n'existe pas dans le code).
- **Écriture depuis le panneau :** `exploring_controller.exploring_source_params_changed`, puis le signal
  `settingLayerVariable`, puis `save_variables_from_layer`. Les widgets se mettent à jour par
  `_force_update_exploring_widgets`.

- **EXPORTING, pour le projet** (ajout du 16/11) : `CONFIG_DATA["CURRENT_PROJECT"]["EXPORTING"]` —
  `LAYERS_TO_EXPORT`, `PROJECTION_TO_EXPORT`, `STYLES_TO_EXPORT`, `DATATYPE_TO_EXPORT`, `OUTPUT_FOLDER_TO_EXPORT`,
  `ZIP_TO_EXPORT`, chacune avec sa case `HAS_…`, plus `BATCH_OUTPUT_FOLDER`, `BATCH_ZIP` ; gardé en JSON dans
  `fm_projects.project_settings`. Aucun outil n'y touche ; `export_layers` prend ses propres arguments.

## Objectifs

- L'agent règle, pour une couche ou pour tout le projet :
  - les trois expressions d'EXPLORING, le mode actif, le suivi et la liaison ;
  - les paramètres de filtrage par défaut de la couche ;
  - (16/11) les paramètres d'EXPORTING du projet : couches, format, projection, styles, dossier, zip.
- Le panneau ainsi réglé sert ensuite à l'utilisateur : l'agent prépare FilterMate, l'utilisateur s'en sert à la main.
- Il choisit des libellés parlants en regardant les champs et les valeurs, et non le premier champ venu.
- Le changement passe par le même chemin que le panneau : les widgets suivent, c'est gardé avec le projet, et c'est
  annulé avec le tour.

## Non-objectifs

- Changer l'heuristique du premier ajout. Elle reste ; l'agent vient après, à la demande.
- Les réglages globaux de FilterMate : ils ont déjà leurs outils (`change_settings`).
- (16/11) Faire filtrer ou exporter l'agent avec l'état du panneau : `apply_filter`, `cross_filter` et `export_layers`
  gardent leurs arguments.
- (16/11) Alourdir la requête de départ : voir Contraintes.

## Contraintes (16/11)

- Les nouveaux outils viennent avec leur skill (familles d'outils) : la requête de départ de la configuration par
  défaut ne grossit que de la ligne de la nouvelle skill dans `load_skill`. Le banc
  `scripts/agent_request_weight.py --conversation` reste sous +5 % de sa référence, et la PR donne l'écart.
- Aucun paragraphe nouveau dans `SYSTEM_PROMPT` : la méthode est dans les skills.

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
- **Skill `panels`** (nouveau, `skills/panels/SKILL.md` ; nommée `exploring` le 13/11, renommée le 16/11 parce qu'elle
  porte aussi EXPORTING), qui apprend la méthode :
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
- **EXPORTING** (16/11), même modèle :
  - `export_options()` lit l'état d'EXPORTING du projet avec les choix permis ; `set_export_options(changes)` écrit
    les clés demandées d'une liste blanche (couches du projet, format connu de FilterMate, projection valide, dossier
    existant et accessible en écriture, booléens) ;
  - l'écriture suit le chemin du panneau (dict du projet, sauvegarde du projet de FilterMate, widgets d'EXPORTING mis
    à jour) ; annulée avec le tour ;
  - outils dans la skill `panels` (il n'y a pas de skill source `export`), qui dit quand préparer le panneau plutôt
    qu'exporter (« prépare l'export des couches filtrées en GeoPackage »).

## Ce qui reste au constructeur

- La liste blanche exacte des clés de `filtering` (lire `configuration_manager.get_layer_properties_tuples_dict`).
- L'ordre de mise à jour des widgets quand la couche réglée n'est pas celle du dock.
- Les messages dans les 34 catalogues.
- La liste blanche exacte d'EXPORTING et les formats permis (lire `core/export/export_validator.py`).
- Tests :
  - unitaires : vérifications des valeurs, liste blanche, couche protégée ;
  - contrôle sans écran : l'outil change l'expression, le combo d'EXPLORING suit, et l'annulation du tour remet
    l'ancienne ;
  - un cas du banc : sur une couche communes, l'agent choisit un libellé avec le nom et pas `fid`.
