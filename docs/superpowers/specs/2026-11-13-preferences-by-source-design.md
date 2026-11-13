# Lot G : préférences et mémoire gardées d'un projet à l'autre, par source de données

Date : 2026-11-13. Statut : à approuver.

## Pourquoi

Le bridge Constructel ouvre un nouveau projet QGIS à chaque fois, avec les mêmes tables PostgreSQL. Or FilterMate
range presque tout par projet et par couche :

- le projet est reconnu par son nom et son chemin (`fm_projects`) ;
- la couche par `layer.id()`, un identifiant de session qui change à chaque ouverture ;
- sont donc perdus à chaque fois :
  - les champs d'EXPLORING et les paramètres de filtrage de chaque couche (`fm_project_layers_properties`) ;
  - l'historique des filtres (`fm_subset_history`) ;
  - les favoris de projet (`fm_favorites`, par `project_uuid`) ;
  - les notes et recettes de l'agent (rangées dans le projet).
- Seuls les favoris globaux survivent.

Décision de l'utilisateur (13/11) :
- se souvenir **par source de données** ;
- ajouter une **mémoire de l'utilisateur** pour l'agent, faite de notes et d'un glossaire métier (MRO, POP, feeder…),
  gardés d'un projet à l'autre ;
- pas de RAG dans le plugin.

## Objectifs

- Une couche ajoutée à un projet neuf retrouve ce que l'utilisateur avait réglé pour **la même source** dans n'importe
  quel autre projet :
  - les expressions d'EXPLORING et le mode actif ;
  - le suivi et la liaison ;
  - les paramètres de filtrage par défaut (prédicats, tampon, couches cibles) ;
  - l'historique des filtres de cette source.
- Les favoris dont les couches sont présentes dans le projet ouvert sont proposés, même s'ils ont été créés ailleurs.
- L'agent garde des notes de l'utilisateur et un glossaire, par source ou pour tous les projets. Il les reçoit quand
  elles concernent le projet ouvert.

## Non-objectifs

- Un RAG ou un index de documents. Des documents à interroger passent par un connecteur MCP (lot A).
- La synchronisation entre machines. C'est local, comme le reste de FilterMate ; les profils de réglages partagent
  déjà la configuration.
- Changer le bridge.

## Anti-objectifs

- Un réglage d'un projet qui écrase en silence un réglage déjà fait dans le projet ouvert. Ce qui est rangé dans le
  projet passe toujours avant ce qui est rangé par source.
- Des identifiants dans la base : la signature ne garde ni mot de passe, ni utilisateur, ni jeton.

## Approches

1. **Par signature de source (retenue par l'utilisateur).** C'est automatique, rien à changer au bridge, et ça marche
   aussi entre deux projets ordinaires qui partagent des données.
2. Un projet modèle : écartée. Un modèle est à tenir à jour, et il faut de toute façon reconnaître les couches par leur
   source, puisque leurs identifiants changent.
3. Un identifiant de projet posé par le bridge : écartée. Il faut modifier le bridge, et ça ne règle pas le changement
   d'identifiant des couches.

## Conception

### Signature

- On reprend `core/domain/layer_signature.py` (`LayerSignature.compute`), déjà la référence unique des favoris :
  `postgres::<schema>.<table>`, `spatialite::<table>`, `ogr::<layername>` ou `ogr::<fichier>`, et
  `<fournisseur>::<nom>` sinon.
- Deux bases avec le même `schema.table` partagent donc leurs préférences. Pour le cas visé (mêmes tables, nouveau
  projet), c'est voulu : les mêmes champs d'EXPLORING s'y appliquent.
- Le constructeur peut ajouter le nom de la base à la signature, si un test montre une collision gênante. Il doit alors
  garder la lecture des favoris existants.
- Les couches en mémoire (`memory`) et les couches temporaires produites par FilterMate ou l'agent ne sont jamais
  gardées : leur signature n'est pas stable.

### Stockage

- Nouvelle table de `filterMate_db.sqlite` : `fm_source_preferences(signature, meta_type, meta_key, meta_value,
  updated_at)`, avec la clé primaire `(signature, meta_type, meta_key)`.
- Elle reprend la forme de `fm_project_layers_properties`, sans projet ni `layer_id`.
- Les clés gardées forment une liste blanche :
  - `exploring` : les trois expressions, `current_exploring_groupbox`, `is_tracking`, `is_linking` ;
  - `filtering` : prédicats, tampon et couches cibles.
- Les couches cibles sont rangées **en signatures**, puis traduites en identifiants de couche à la relecture. Une cible
  absente du projet ouvert est ignorée.

### Écriture

- Quand une préférence d'une couche est enregistrée par le chemin actuel (`settingLayerVariable` puis
  `save_variables_from_layer`), elle est aussi écrite sous la signature de la couche, pour les clés de la liste blanche.
- Le dernier réglage gagne. Il n'y a pas d'historique des préférences.

### Lecture

- Quand une couche arrive sans propriétés dans le projet (`layer_management_task.py`, vers 932-958), les préférences
  de sa source sont appliquées **avant** l'heuristique `get_best_display_field`.
- Chaque expression est vérifiée sur la couche (champs connus). Une expression qui ne vaut plus est laissée de côté, et
  l'heuristique prend le relais.
- Une couche qui a déjà des propriétés dans le projet les garde.

### Historique des filtres

- `fm_subset_history` a déjà une colonne `layer_source_id` : on y écrit la signature.
- Dans un projet neuf, l'historique d'une couche montre aussi les filtres passés de sa source, marqués « d'un autre
  projet ».
- La pile annuler/rétablir de la session n'est pas concernée.

### Favoris

- Les favoris gardent déjà `spatial_config.source_layer_signature`.
- Le menu des favoris ajoute une section « De vos autres projets » : les favoris de n'importe quel projet dont toutes
  les couches nommées sont présentes, par signature, dans le projet ouvert.
- Appliquer un tel favori le copie dans le projet ouvert, comme l'actuel « copier en global », mais vers le projet.

### Mémoire de l'agent

- Nouvelle table : `fm_agent_memory(id, scope, signature, text, created, updated)`. `scope` vaut `user` (tous les
  projets) ou `source` (une signature).
- Les notes de projet (`add_project_note`) restent ce qu'elles sont.
- L'outil de note gagne un argument `scope` (`project`, `source`, `user`), plus `layer` quand le scope est `source`.
  Le glossaire est fait de notes `user` courtes, comme « MRO = … ».
- Dans le contexte de chaque requête, l'agent reçoit :
  - les notes `user` ;
  - les notes `source` des couches présentes dans le projet.
- Le tout est borné en nombre et en longueur, comme les notes de projet aujourd'hui. Ce sont des données, jamais des
  instructions, comme les notes actuelles.
- L'utilisateur voit, modifie et supprime ces notes dans le panneau, à côté des notes de projet. L'agent propose d'en
  ajouter quand il apprend un terme, et ne les écrit qu'avec l'accord de l'utilisateur, comme les notes actuelles.

### Option et vie privée

- Option `APP.OPTIONS.REMEMBER_BY_SOURCE`, activée par défaut. La désactiver arrête l'écriture et la lecture par source.
- Une commande « Oublier ce qui est gardé pour cette couche », et une pour tout effacer.
- La base reste locale, dans le profil. Les signatures contiennent des noms de schéma et de table, rien de plus.

## Ce qui reste au constructeur

- La liste exacte des clés de `filtering` (`configuration_manager.get_layer_properties_tuples_dict`).
- L'endroit exact de l'écriture par source : un seul point, de préférence là où `fm_project_layers_properties` est
  écrit.
- La migration de la base : création des tables à l'ouverture, comme pour les autres tables `fm_*`.
- Les messages dans les 34 catalogues.
- Tests :
  - unitaires : signature, liste blanche, traduction des cibles, préséance du projet, expressions invalides, option
    coupée, mémoire bornée ;
  - contrôle sans écran : deux projets successifs sur le même GeoPackage, où le second retrouve les champs d'EXPLORING,
    les favoris et l'historique ;
  - un contrôle PostGIS sur le scénario Constructel, avec les mêmes tables et un nouveau projet.
