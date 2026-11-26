# Parcours Agent à montrer — acquisition et conservation du projet

Relecture des implémentations actuelles du checkout commun, sans modification
du cœur du plugin. Ce document décrit le parcours à filmer ; il ne constitue
pas une prise validée de l'acquisition MNT/URA depuis zéro.

## Ce que le code fait aujourd'hui

`ui/controllers/agent_chat_controller.py` appelle `_data.offer()` à la fin de
la requête, après avoir arrêté l'indicateur de travail et enregistré la session.

Dans `ui/controllers/agent_data.py`, `AgentDataController.offer()` :

- examine les couches encore gérées en mémoire, avec `data_store.pending_layers` ;
- présente une nouvelle carte pour les nouveaux couples identifiant/source ;
- affiche « Conserver ce travail ? », « Enregistrer le projet et les couches… »
  et « Continuer en mémoire » ;
- déclenche `save()` si la carte est acceptée pour la génération de projet en
  cours. Une réponse liée à un ancien projet ne sauvegarde pas le suivant.

`save()` attend la fin du travail courant, ouvre le dialogue natif QGIS pour
choisir un fichier QGZ/QGS, puis appelle `data_store.persist`. La conversation
affiche ensuite les liens vers le projet et son dossier de données.

Dans `adapters/agent/data_store.py`, `persist()` copie les sources complètes
gérées en mémoire dans un nouveau sous-dossier auprès du projet, puis reconnecte
les mêmes objets couche à ces sources. L'état XML, les sous-ensembles, styles et
sélections sont rétablis. Le projet est écrit avec ses références actualisées.
La destination choisie permet ensuite les sorties de fournisseurs nécessitant
un vrai fichier, comme GDAL.

L'enregistrement QGIS natif propose lui aussi de conserver les données encore
en mémoire avant d'écrire le projet. Une couche distante lue directement sur le
serveur ne devient pas une copie locale par le seul fait d'enregistrer le QGZ.

## Mise en scène conforme

1. Filmer le projet vide et le panneau des couches vide avant tout prompt.
2. Demander réellement les données par les outils de l'agent, avec les sources
   autorisées et les ressources officielles vérifiées.
3. Laisser apparaître la carte de conservation après l'acquisition ; zoom de
   lecture, contexte QGIS et panneau FilterMate toujours visibles.
4. Cliquer sur le choix d'enregistrement, montrer le dialogue de destination
   et le nom du projet, puis les liens vers les fichiers créés.
5. Contrôler la persistance des couches acquises, puis poursuivre les filtres.
6. À la fin, sauvegarder les nouveaux résultats, la composition et les SVG,
   et rouvrir une copie du dossier livré.

Le préenregistrement silencieux de l'ancien driver MNS ne convient pas à cette
séquence. La conservation n'est pas une permission d'acquisition, et n'est pas
une sauvegarde automatique décidée par le modèle.

## Preuves à recueillir

- Projet initial : aucun fichier nommé et aucune couche chargée.
- Sources : outils appelés, URL ou plateforme, emprise, millésime, résolution,
  vrai MNT et géométries d'inondabilité exploitables.
- Sauvegarde : carte visible, choix utilisateur, projet écrit, couches valides
  et références durables. Relever aussi les ressources qui restent distantes.
- Filtre : paramètres du moteur, identifiants retenus et effectifs observés.
- Export : fichiers filtrés rouverts et comptes identiques au résultat du moteur.
- Projet : copie déplacée puis rouverte, styles, filtres, composition et SVG
  présents ; copies locales des données nécessaires contrôlées.

Ces contrôles distinguent les résultats exportés des sources conservées avec
leurs filtres dans le projet réutilisable.
