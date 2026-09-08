# FilterMate — optimisation des thèmes QGIS 3 et 4

## Adaptation des thèmes implémentée

Le mode `auto` suit les couleurs effectives de QGIS : fonds, champs, texte,
sélections et contraste des icônes. Il devient le choix des configurations
livrées. L'ancien choix enregistré `default` suit également QGIS, pour les
profils existants sous QGIS 3 et 4. Les choix explicites `light` et `dark`
restent disponibles pour imposer une apparence.

Les couleurs sont lues sur des widgets Qt non affichés, indépendants du panneau
FilterMate. Cela tient compte des thèmes QSS qui ne modifient pas la palette
globale de l'application. Les changements de couleurs sont surveillés même
si deux thèmes utilisent le même contraste d'icônes.

| Apparence QGIS | Comportement attendu |
| --- | --- |
| Default, système clair | Fonds et champs clairs, icônes foncées |
| Default, système sombre | Fonds et champs sombres, icônes claires |
| Night Mapping | Couleurs nocturnes de QGIS, sélections et texte coordonnés |
| Blend of Gray | Nuances grises de QGIS, texte et icônes adaptés aux champs |

Sources : [configuration QGIS](https://docs.qgis.org/3.44/en/docs/user_manual/introduction/qgis_configuration.html),
[API des thèmes](https://api.qgis.org/api/master/classQgsApplication.html).

## Périmètre conservé

La trame, tous les boutons et leurs icônes, les libellés et les contraintes de
taille et de disposition restent identiques. Les propositions de refonte UI/UX
ne sont pas appliquées. Seules la détection des thèmes et les couleurs changent.

À la demande suivante, la barre d'icônes de filtrage est resserrée pour prendre
la même largeur que celle d'exploration : l'espace horizontal disponible est
attribué aux champs. Les boutons et leurs dimensions restent conservés.

## Compatibilité et validation

Le signal `themeChanged` est utilisé lorsqu'il existe (QGIS 4). Sous QGIS 3,
la surveillance utilise `paletteChanged`. Les accès aux palettes et l'inversion
des icônes sont compatibles Qt 5 et Qt 6. Les fichiers d'icônes sont conservés :
les variantes sombres sont dérivées du dessin clair, car plusieurs fichiers
nommés `white` contiennent en réalité des pixels noirs.

Les 37 tests ciblés passent avec PyQt5 et PyQt6 : synchronisation, ancienne
configuration, absence du signal QGIS 4, contraste des icônes et conservation
des contraintes des boutons lors du remplacement des couleurs.

Captures réalisées le 8 septembre 2026 sous Windows avec QGIS 3.44.8 / Qt 5.15.13
et QGIS 4.2.0 / Qt 6.11.0, pour les quatre apparences ci-dessus. Elles rendent
le formulaire `.ui` original avec les widgets QGIS réels et des couches mémoire,
dans un processus isolé. Le mode système sombre utilise une palette simulée ;
Night Mapping et Blend of Gray utilisent les thèmes installés. Les 24 boutons
du formulaire et leurs contraintes sont contrôlés par le script de capture.

Ces rendus ne constituent pas un test complet du plugin dans le projet utilisateur.
Pour chaque apparence, il reste à vérifier dans une session interactive :

- ouverture, changement de thème et rechargement du plugin ;
- champs, listes déroulantes, boutons cochés, désactivés, survolés et au focus ;
- panneau étroit puis large, mise à l'échelle Windows 100 %, 150 % et 200 % ;
- ouverture de l'éditeur d'expression : aucun style FilterMate ne doit déborder ;
- panneaux Favoris et Configuration, qui possèdent encore des styles propres.

La correction porte sur les couleurs du panneau principal et leur synchronisation.

Les icônes PNG chargées avant le thème sont réappliquées après synchronisation.
Les rechargements et changements d’état passent par IconManager, y compris
les onglets et les cases de centroïdes. La deuxième ligne de filtrage reçoit
le même facteur d’étirement horizontal que la première.
