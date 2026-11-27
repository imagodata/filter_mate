# Identité du réseau pulsé pour FilterMate et son agent

Le réseau pulsé est la direction retenue par l’utilisateur. L’agent reprend ce symbole dans son icône compacte et dans son indicateur d’activité animé. Pour le plugin, la variante proposée renforce le contraste du centre et simplifie les détails aux tailles des barres d’outils.

![Icône intégrée et propositions du réseau pulsé](identity-proposals.png)

## Agent intégré

- [Icône claire](agent-light.svg) et [icône sombre](agent-dark.svg), dessinées sur une grille de 24 unités.
- [Animation claire](agent-loader-light.svg) et [animation sombre](agent-loader-dark.svg).
- Quatre branches colorées, centre suivant le thème, onde de deux secondes et orbite de huit secondes.
- Animation limitée à 20 images par seconde dans le composant Qt, active pendant une requête, arrêtée lorsque le panneau est masqué ou inactif. Elle reprend si le panneau redevient visible pendant le travail.

L’icône de bienvenue et les en-têtes utilisent le rendu partagé de `ui/styles/mockup_design.py`. Le composant `ui/widgets/agent_activity.py` possède son propre moteur SVG ; les animations ne sont pas placées dans le cache global des icônes.

Les fichiers fournis comme références utilisent `animate` et `animateMotion`. QtSvg les charge comme images mais ne reconnaît pas leurs animations dans les environnements vérifiés. Les variantes utilisent `animateTransform`, pris en charge par Qt5 et Qt6. Cette adaptation conserve la pulsation et les orbites sans ajouter de navigateur embarqué. [Prise en charge SVG par Qt](https://doc.qt.io/qt-6/topics-vectorimageformats.html).

## Proposition pour le plugin

La variante C1 Réseau contrasté est recommandée : un centre clair avec contour gris, quatre nœuds colorés et des connexions plus épaisses. C2 ajoute un halo discret ; C3 présente le même réseau sur une pastille sombre. La planche compare leurs rendus à 16, 24, 32 et 64 pixels, sur fonds clair et sombre.

Les fichiers prêts à examiner sont :

- C1 statique : [thème clair](plugin-network-pulse-refined-light.svg), [thème sombre](plugin-network-pulse-refined-dark.svg).
- C1 animée : [thème clair](plugin-network-pulse-refined-animated-light.svg), [thème sombre](plugin-network-pulse-refined-animated-dark.svg).
- [Planche vectorielle](identity-proposals.svg) et [aperçu PNG](identity-proposals.png).

L’icône principale `icon.png` et sa copie `icons/icon.png` restent inchangées. Une adoption de C1 pourra produire les PNG de distribution depuis le SVG. La version animée convient aux composants qui possèdent un moteur d’animation ; une icône PNG du gestionnaire des extensions reste statique.

## Vérifications

Les rendus et le cycle de vie du composant ont été vérifiés dans QGIS 3.44.15 avec Qt 5.15.18 et QGIS 4.3.0 Master avec Qt 6.10.2. Les contrôles couvrent l’animation réelle des images, l’arrêt lorsque le parent est masqué, la reprise, les thèmes et les tailles de l’icône. Les tests automatisés vérifient aussi que deux indicateurs ne partagent pas leur moteur et que l’absence de QtSvg laisse le panneau utilisable.

Résultats : [Qt5](validation-qt5.json), [Qt6](validation-qt6.json). Les références originales sont conservées dans [favicon-reference.svg](favicon-reference.svg) et [logo-reference.svg](logo-reference.svg).
