# Usages des coupes en architecture et urbanisme en France, et besoins de données depuis le LiDAR HD

Note de méthode : consultation du 9 novembre 2026. Textes lus directement : Légifrance (R431-10, R111-15 à R111-19, arrêté du 16 septembre 2003), BOFiP, BD TOPO (édition de septembre 2026), fiche 13 du lexique national, recueil de l'Ordre des géomètres-experts (OGE), réponse ministérielle n° 6653. Les éléments marqués « extrait de recherche » viennent d'un résumé de moteur de recherche, sans relecture du document source : à vérifier avant reprise.

## Types de coupes, finalités, échelles et précision graphique

### Takeaway
La coupe recouvre des objets très différents : du relevé d'architecte au 1/50 (hauteurs intérieures, planchers), que l'aéroporté ne peut pas produire, à la coupe urbaine ou de site, où l'on cherche des rapports et des silhouettes. Le LiDAR HD ne peut viser que la seconde famille. Je n'ai trouvé aucune source normative qui associe une échelle à une tolérance pour ces dessins.

### Cited Findings
- L'OGE définit la « coupe de précision » comme un plan d'architecture établi en complément des relevés pour les études de réhabilitation ou de restructuration, levé et reporté du 1/50 au 1/100. Son cadre juridique est indiqué « sans objet » — [Recueil des prestations OGE, §5.7](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- Cette coupe demande les hauteurs accessibles, les retombées de poutres, les faux plafonds, les hauteurs de linteau et d'appui, l'épaisseur des planchers et le nivellement de chaque plancher ; elle peut être rattachée en planimétrie et en altimétrie — [Recueil OGE, §5.7](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- Les plans de façade sont levés et reportés au 1/100 ou au 1/50, avec ouvertures, bandeaux et, sur demande, ornementation — [Recueil OGE, §5.7](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- La coupe de permis montre le profil du terrain naturel avant travaux, le profil après terrassement et les cotes de niveau, selon un guide pratique (source secondaire) — [construires.fr](https://www.construires.fr/plan-coupe-cotes-ngf-guide/)
- Le lexique national définit le gabarit comme l'ensemble des plans verticaux, horizontaux ou obliques constituant la forme extérieure de la construction, résultant de la combinaison des règles de hauteur, de prospects et d'emprise au sol — [Fiche technique 13](https://www.doubs.gouv.fr/contenu/telechargement/34198/214414/file/Lexique%20national%20de%20l'urbanisme.pdf)
- Le profil en travers hydraulique est une coupe perpendiculaire à l'écoulement, avec l'altitude en ordonnée (extrait de recherche) — [Guide plugin surcotes, INRAE/Irstea](https://forge.irstea.fr/attachments/download/3018/Guide%20utilisateur%20plugin%20surcotes2022.pdf)
- Les ouvrages de référence pour l'analyse urbaine française sont *Analyse urbaine* (Panerai, Demorgon, Depaule, Parenthèses) et *Formes urbaines : de l'îlot à la barre* (Castex, Depaule, Panerai) — [Éditions Parenthèses, Analyse urbaine](https://editionsparentheses.com/IMG/pdf/p603_analyse_urbaine.pdf) ; [Formes urbaines](https://editionsparentheses.com/IMG/pdf/p602_formes_urbaines.pdf)
- Dans un travail sur scans terrestres (Rocinha, Rio), largeur de rue et élévation des façades sont calculées sur des bandes de 50 cm, ce qui équivaut à une analyse en coupes sériées (hors France, cité pour la méthode d'analyse) — [Favelas 4D, arXiv](https://arxiv.org/pdf/2105.03235)

### Inferences
- Trois familles d'usage se dégagent. La **mesure** (coupe de relevé, 1/50 à 1/100) exige l'accès à l'intérieur. La **conformité** (coupe PC, gabarit, 1/100 à 1/200) dépend d'un terrain avant travaux et de points précis. La **lecture** (coupe urbaine, de site, paysagère, séquences de rue, 1/500 à 1/5000) vise des proportions.
- Avec la convention usuelle d'erreur graphique de 0,1 à 0,2 mm (convention non sourcée ici, voir Gaps), on obtient : 1/50 = 5 à 10 mm ; 1/100 = 1 à 2 cm ; 1/200 = 2 à 4 cm ; 1/500 = 5 à 10 cm ; 1/1000 = 10 à 20 cm.
- Sur cette base, les 10 cm altimétriques annoncés pour le LiDAR HD (voir section Précision) correspondent à une lecture au 1/500 ou 1/1000 en altitude. Les 50 cm annoncés en planimétrie correspondent plutôt au 1/2500 ou 1/5000 pour la position des façades.

### Gaps
- Aucune source trouvée pour la règle de 0,1 ou 0,2 mm d'erreur graphique, ni pour une table officielle échelle / tolérance. L'article 8 de l'arrêté de 2003 limite seulement la classe d'une image à la taille du pixel.
- La méthode de coupe de Panerai (ratio H/L, échelles utilisées) n'a pas pu être vérifiée : seules les fiches d'éditeur ont été trouvées. Il faut consulter les ouvrages.
- Aucune source sur la coupe paysagère ou la coupe de site en CAUE, ni sur les échelles enseignées en ENSA. Un rapport du laboratoire Cresson expérimenterait transects et coupe urbaine (extrait de recherche, URL non identifiée).

## Usages réglementaires : permis, prospects, hauteurs, géomètre-expert

### Takeaway
La coupe est une pièce obligatoire du permis (R431-10 b) et elle doit montrer l'état initial si le terrain est modifié. Les prospects se calculent sur des différences d'altitude et des distances prises entre des points précis. Rien de ce que j'ai trouvé n'impose un géomètre-expert pour les altitudes, et aucun texte ne traite du statut des données IGN.

### Cited Findings
- **R431-10 (version en vigueur depuis le 1er octobre 2007, constatée le 9 novembre 2026)** : le projet architectural comprend un plan des façades et toitures (a), un plan en coupe précisant l'implantation de la construction par rapport au profil du terrain, avec état initial et état futur si les travaux modifient ce profil (b), un document graphique d'insertion (c) et deux photographies (d) — [Légifrance](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006820087)
- PCMI3 désigne usuellement la coupe du dossier de maison individuelle, et PC3 / DP3 les autres dossiers ; l'intitulé du fichier ne détermine pas le régime applicable — [Cabinet Kohen](https://kohenavocats.fr/?p=2157519)
- Selon le même cabinet, l'article R431-36 en vigueur depuis le 1er juillet 2026 complète le dossier de déclaration préalable, s'il y a lieu, par les pièces a) et b) de R431-10 (non vérifié sur Légifrance) — [Cabinet Kohen](https://kohenavocats.fr/?p=2157519)
- **R111-16** : pour un bâtiment en bordure de voie publique, la distance horizontale de tout point de l'immeuble au point le plus proche de l'alignement opposé doit être au moins égale à la différence d'altitude entre ces deux points (règle L ≥ H) — [Réponse ministérielle n° 6653](https://questions.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE6653.pdf) ; [Légifrance (version au 6 avril 2020)](https://www.legifrance.gouv.fr/codes/id/LEGIARTI000031721286/2020-04-06/)
- **R111-17** : sauf si le bâtiment jouxte la limite, la distance horizontale de tout point au point le plus rapproché de la limite parcellaire doit être au moins égale à la moitié de la différence d'altitude, sans pouvoir être inférieure à 3 mètres (L ≥ H/2, minimum 3 m) — [Réponse n° 6653](https://questions.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE6653.pdf)
- R111-15 à R111-19 sont en vigueur depuis le 1er janvier 2016 (décret n° 2015-1783) ; R111-18 traite des immeubles existants non conformes à R111-17 et R111-19 des dérogations motivées — [Légifrance](https://www.legifrance.gouv.fr/codes/id/LEGIARTI000031721286/2020-04-06/)
- La jurisprudence limite R111-16 et R111-17 aux bâtiments (exclusion des éoliennes et antennes-relais ; CE, 19 septembre 2014, n° 357327, parmi d'autres) — [Réponse n° 6653](https://questions.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE6653.pdf)
- Les PLU reprennent cette écriture : le règlement de la Métropole de Lille utilise la notation L ≥ H/2 avec minimum en mètres, variable selon les zones (extrait de recherche) — [PLU MEL, livre IV](https://www.lillemetropole.fr/sites/plu/files/2018-10/LIVRE-IV_TITRE%201_ZONES-UOP.pdf)
- **Lexique national, définition de la hauteur** : « La hauteur totale d'une construction, d'une façade, ou d'une installation correspond à la différence de niveau entre son point le plus haut et son point le plus bas situé à sa verticale. Elle s'apprécie par rapport au niveau du terrain existant avant travaux, à la date de dépôt de la demande. Le point le plus haut à prendre comme référence correspond au faîtage de la construction, ou au sommet de l'acrotère [...]. Les installations techniques sont exclues du calcul de la hauteur. » — [Fiche technique 13](https://www.doubs.gouv.fr/contenu/telechargement/34198/214414/file/Lexique%20national%20de%20l'urbanisme.pdf)
- Statut de ce lexique : la fiche indique que ses définitions « pourront à terme faire l'objet d'un arrêté » et qu'il est, dans l'attente, « recommandé » aux auteurs de PLU(i) de les utiliser ; ceux-ci peuvent les préciser sans en changer le sens, notamment pour les terrains en pente — [Fiche technique 13](https://www.doubs.gouv.fr/contenu/telechargement/34198/214414/file/Lexique%20national%20de%20l'urbanisme.pdf)
- Le niveau du sol peut intégrer des modifications antérieures au dépôt et sans lien avec le projet, sauf objectif frauduleux. Sont exclues du calcul les antennes, cheminées, dispositifs d'ascenseur, de chaufferie, de climatisation et garde-corps. Le PLU(i) peut régler la hauteur globalement ou façade par façade — [Fiche technique 13](https://www.doubs.gouv.fr/contenu/telechargement/34198/214414/file/Lexique%20national%20de%20l'urbanisme.pdf)
- Dans un règlement local, la hauteur absolue est mesurée verticalement en tout point des façades, du sol naturel à l'égout (ou acrotère) ou au faîtage (extrait de recherche) — [TA Marseille, 30 septembre 2025](https://www.doctrine.fr/d/TA/Marseille/2025/TADF234601A442931CC53C)
- Le géomètre-expert relève de la loi n° 46-942 du 7 mai 1946 ; le monopole porte sur les travaux fixant les limites des biens fonciers, y compris plans de division et de bornage (extrait de recherche) — [Conseil constitutionnel 2022, commentaire](https://www.labase-lextenso.fr/jp-commente/cc/2022-06/20-18-136-CC-29062022-20_18136) ; [Cass. 2015](https://www.doctrine.fr/d/CASS/2015/JURITEXT000031134267)
- Le plan cadastral n'a qu'une valeur d'indice réfutable pour la propriété, sans fixer sa consistance (extrait de recherche) — [Réponse AN 89615](https://www.assemblee-nationale.fr/dyn/13/questions/QANR5L13QE89615.pdf) ; [Réponse AN 72292](https://www.assemblee-nationale.fr/dyn/12/questions/QANR5L12QE72292.pdf)

### Inferences
- Le prospect dépend de **deux** points (façade et alignement ou limite). Une coupe automatique ne peut pas le vérifier si la limite vient du cadastre, puisque celui-ci ne la fixe pas.
- La référence réglementaire est le terrain **avant travaux à la date de dépôt**. Un nuage acquis plusieurs années plus tôt peut donc différer du terrain à retenir, en particulier après terrassement.
- La hauteur se prend au point « situé à sa verticale », façade par façade ou globalement selon le PLU. Il n'existe donc pas de hauteur unique : un calcul automatique doit annoncer quelle définition il applique.
- Le lexique est une fiche recommandée et non un arrêté d'après la version consultée : le règlement local prime et doit être lu pour chaque zone.

### Gaps
- Aucun texte trouvé imposant un géomètre-expert pour les altitudes d'un permis. La réponse ministérielle limitant le monopole à la délimitation est un extrait de recherche, sans URL identifiée avec certitude (probablement [QE 4081](https://www.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE4081.pdf)).
- Aucun texte ni décision trouvé sur la recevabilité de données IGN (RGE ALTI, LiDAR HD) dans une pièce de permis ou un contentieux.
- Non vérifiés sur Légifrance à ce stade : R431-9 (plan de masse coté dans les trois dimensions), R111-1 (articulation RNU / PLU), R151-39 et suivants (règles de hauteur du PLU), décret du 3 mars 2006 sur le rattachement au système légal (cité par l'OGE). Une recherche indique que le RNU ne s'applique pas partout, alors qu'une page Légifrance le présente comme applicable sur tout le territoire : point à trancher dans R111-1.
- Un arrêt du Conseil d'État retiendrait le faîtage pour un mur pignon sans égout (extrait de recherche, numéro non relevé). CE n° 459436 du 3 août 2022 viserait le lexique national (extrait de recherche, [Conseil d'État](https://www.conseil-etat.fr/fr/arianeweb/CE/decision/2022-08-03/459436)). À vérifier avant toute citation.
- La date et la version en vigueur de la fiche 13 n'ont pas été confirmées.

## Exigences de précision : arrêté de 2003, géomètre, LOA, comparaison au LiDAR HD

### Takeaway
L'arrêté de 2003 fournit une méthode de qualification, pas une table de valeurs : la classe est fixée par contrat. Les 10 cm altimétriques et 50 cm planimétriques annoncés pour le LiDAR HD sont d'un ordre de grandeur étranger aux LOA 20 à 50 de l'USIBD, et en planimétrie ils sont insuffisants pour vérifier un retrait réglementaire.

### Cited Findings
- **Arrêté du 16 septembre 2003** (JORF du 30 octobre 2003, NOR EQUP0300864A) : il s'applique aux travaux topographiques de l'État, des collectivités et de leurs établissements publics, ou exécutés pour leur compte, hors levés hydrographiques (art. 1) — [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000794936)
- Art. 3 : les mesures de contrôle doivent être plus précises que la classe visée, avec un coefficient de sécurité C au moins égal à 2. Art. 4 : le gabarit d'erreurs est fixé par contrat. Art. 7 : classes planimétriques et altimétriques distinctes, y compris par type d'objet. Art. 7.4 : classes spécifiques pour la représentation altimétrique du terrain, avec spécifications propres pour thalwegs, crêtes et lignes de rupture. Art. 8 : une classe d'image ne peut pas être inférieure à la taille du pixel — [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000794936)
- Formules telles que reprises par la DGFiP : Emoypos < [yy] × (1 + (2C²)⁻¹) ; premier seuil T = k × [yy] × (1 + (2C²)⁻¹), dépassement toléré pour au plus l'entier supérieur à 0,01 N + 0,232 √N ; second seuil 1,5 × k × [yy] × (1 + (2C²)⁻¹), jamais dépassé ; k = 3,23 (n=1), 2,42 (n=2), 2,11 (n=3). Exemple classe 10 cm, C=2, n=2 : 11,25 / 27,23 / 40,84 cm — [BOFiP, BOI-CAD-TOPO-60](https://bofip.impots.gouv.fr/bofip/5195-PGP.html/identifiant=BOI-CAD-TOPO-60-20170503)
- La classe totale combine erreurs internes, de rattachement et du réseau légal : [yy]² = [xx]² + [zz]² — [BOFiP](https://bofip.impots.gouv.fr/bofip/5195-PGP.html/identifiant=BOI-CAD-TOPO-60-20170503)
- L'arrêté du 19 avril 2005 sur le référentiel à grande échelle renvoie à l'arrêté de 2003 (extrait de recherche) — [Légifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000259279)
- OGE, travaux fonciers : classe 1 de 0 à 5 cm, classe 2 de 5 à 15 cm, classe 9 au-delà. Pour le nivellement : au moins deux repères IGN contrôlés, points doubles, et plan indiquant le système retenu et les repères — [Recueil OGE, §5.2 et 5.3](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- Maquette numérique selon l'OGE : la donnée doit être qualifiée selon le protocole (précision, niveau de détail, durée de vie, aspects juridiques, limites d'utilisation) — [Recueil OGE](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- **USIBD LOA** (source secondaire) : LOA10 au-delà de 50 mm, LOA20 de 15 à 50 mm, LOA30 de 5 à 15 mm, LOA40 de 1 à 5 mm, LOA50 de 0 à 1 mm ; l'exactitude mesurée concerne l'écart réalité / nuage et l'exactitude représentée l'écart nuage / modèle — [Article de recherche, core.ac.uk](https://core.ac.uk/download/188622571.pdf). Version courante : 3.1 — [USIBD](https://usibd.org/level-of-accuracy/)
- **LiDAR HD** : densité moyenne de 10 points/m², précision absolue annoncée de 10 cm en altimétrie et 50 cm en planimétrie (extrait de recherche, présentations IGN ; PDF trop volumineux pour relecture) — [Atelier IGN 2025](https://www.openig.org/sites/default/files/2025-12/IGN-ATELIER%20LIDAR-2025.pdf). Contradiction : le jeu Hauts-de-Seine 2022 indique une classe planimétrique de 0,1 m sur surface dure — [data.gouv](https://www.data.gouv.fr/datasets/lidar-hd-ign-2022/informations)
- Le MNT LiDAR HD dérive des points sol, eau et de points virtuels — [data.gouv](https://www.data.gouv.fr/datasets/mnt-lidar-hd)
- Sur des mires, un MNS IGN à 20 cm présente un RMSE altimétrique de 29,5 cm contre 4,8 cm pour un LiDAR aéroporté ; échantillon réduit, et le LiDAR testé n'est pas identifié comme LiDAR HD (extrait de recherche) — [Tardy, SFPT 2025](https://wpedu2.sedoo.fr/wp-content-omp/uploads/sites/54/2025/05/SFPT-GH-25_Session-3_TARDY_Hugo.pdf)

### Inferences
- L'arrêté vaut pour les commandes publiques ; il sert de référence de fait pour décrire un levé, mais aucune source trouvée ne l'impose à un dossier de permis privé.
- L'arrêté raisonne en écart moyen, pas en écart-type. Pour une loi normale, l'écart moyen vaut environ 0,80 σ en une dimension et 1,25 σ en deux. Une « précision de 10 cm » ne se convertit donc en classe qu'une fois sa statistique connue.
- Pour une classe altimétrique hypothétique de 10 cm (n=1, C=2) : seuil T ≈ 36 cm, second seuil ≈ 54 cm (calcul d'après les formules BOFiP).
- Par effet de pente, une erreur planimétrique de 50 cm produit environ 15 cm d'erreur altimétrique sur une pente de 30 % (calcul). Le 10 cm n'est donc crédible que sur surface peu pentue et dégagée.
- Sur un retrait minimal de 3 m (R111-17), 50 cm représentent 17 % de la distance : le contrôle réglementaire n'est pas possible. À l'inverse, pour H/2, 10 cm sur H ne font que 5 cm sur L : **c'est la planimétrie, pas l'altimétrie, qui bloque**.
- Exprimé en LOA, le LiDAR HD est hors des bandes LOA20 à LOA50 (100 mm et 500 mm), donc au mieux en LOA10.

### Gaps
- Je n'ai pas pu lire les tableaux du Journal officiel (p. 18546-18548), ni la version consolidée de l'arrêté ; les valeurs k viennent du BOFiP. La circulaire est [ici](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000429763), non lue.
- Texte primaire USIBD non consulté (compte requis) : niveau de confiance 2 σ non confirmé.
- **Aucune charte française Scan-to-BIM trouvée** (OGE, Plan BIM, MINnD) : la question reste ouverte.
- Statistique exacte derrière les 10 cm / 50 cm (RMSE, écart-type, EMQ par tuile) non trouvée dans une spécification IGN lue directement.

## Croisement de données : quel attribut corrige quel manque

### Takeaway
La BD TOPO ne fournit ni la hauteur réglementaire ni un sol en pied de façade au sens du droit des sols : ses attributs dérivent en partie de MNT/MNS avec 1 à 2,5 m de précision annoncée. Le croisement utile est donc celui du LiDAR HD (surfaces), du cadastre (repérage seulement), du terrain (limites, pied de façade) et de l'imagerie de rue (ce que le ciel ne voit pas).

### Cited Findings
- **BD TOPO, édition de septembre 2026, classe Bâtiment** — [IGN](https://bdtopoexplorer.ign.fr/batiment) :
  - Hauteur : « mesurée entre le sol et le point haut de la gouttière » ; sol le plus bas si pente, point le plus haut si gouttière non horizontale ; 0 = inconnue.
  - Z_MIN_SOL : au pied, côté bas, ou valeur la plus basse du MNT RGE ALTI dans l'emprise. Z_MAX_SOL : valeur maximale du MNT, non renseignée si le MNT est insuffisant.
  - Z_MIN_TOIT : arête du contour, médiane d'une grille interpolée (bâtiments issus de la BD PARCELLAIRE) ou 2,5e à 4e décile du MNS (bâtiments améliorés par corrélation).
  - Z_MAX_TOIT : faîte, hors cheminées, 9e décile du MNS dans l'emprise, moins fiable pour les petits bâtiments.
  - NB_ETAGES : calculé à partir de Dnbniv.
  - Origine « Cadastre » : contour au sol, volume aplati. Origine « Imagerie aérienne » : contour vu d'avion, altitude des gouttières.
  - Précision altimétrique citée : 2,5 m (BD PARCELLAIRE à altimétrie calculée), 1 m (photogrammétrie), 9999 sans Z.
  - Cour représentée seulement si plus de 10 m de large ; bâtiments contigus fusionnés, sauf différence d'environ 10 m (ou 3 étages) et surface d'environ 400 m² ou plus.
- ACQU_ALTI comprend notamment BDAlti, Corrélation, Lidar, Lidar HD, Photogrammétrie, Levé GPS ; des tables donnent Lidar 0,5 m, Corrélation 1 m, Photogrammétrie 1,5 m, BDAlti 5 m, valeurs variables selon l'édition (extrait de recherche) — [Attributs communs BD TOPO](https://bdtopoexplorer.ign.fr/?attr_communs_total=)
- Une chaîne LiDAR (Strasbourg) retient, par pixel de 50 cm, la hauteur maximale des points « bâtiment » et signale une incertitude sur le sol au pied du bâti (extrait de recherche) — [Eurométropole de Strasbourg, métadonnées](https://www.sig.strasbourg.eu/datastrasbourg/3d_fiches_metadonnees_pdf/2025/metadata_raster_hauteur_bati.pdf)
- La statistique maximale peut capter antennes et cheminées, et la médiane est plus robuste — [LOD1 3D City Model, arXiv](https://arxiv.org/pdf/2505.14747)
- Le LiDAR aéroporté subit des occultations liées à son angle de balayage, surtout près des immeubles hauts — [arXiv 2205.14585](https://arxiv.org/pdf/2205.14585)
- Le cadastre présente fréquemment des écarts de plusieurs mètres avec la réalité, selon un guide pratique (source secondaire) — [construires.fr](https://www.construires.fr/surface-cadastrale-parcelle-evaluer/)
- Pour le zonage, un document d'urbanisme est opposable une fois approuvé et les transmissions et publicités accomplies (extrait de recherche) — [DDT Puy-de-Dôme](https://www.puy-de-dome.gouv.fr/contenu/telechargement/21996/186108/file/docurba2017.pdf)

### Inferences

| Manque du LiDAR HD | Donnée correctrice | Limite |
|---|---|---|
| Position exacte de la façade au sol (occultation, débord) | Contour BD TOPO d'origine « Cadastre » ou PCI ; levé terrestre, mobile | Le PCI a des écarts métriques possibles ; un contour vu d'avion correspond plutôt au toit |
| Égout (hauteur de gouttière) | Attribut Hauteur BD TOPO, Z_MIN_TOIT, façade vue par Panoramax | Précision de 1 à 2,5 m ; définition différente de la hauteur totale du lexique |
| Faîtage / acrotère | Points LiDAR classés bâtiment (classe à filtrer des superstructures) ; Z_MAX_TOIT | 9e décile ≠ point le plus haut réglementaire |
| Sol sous couvert, sous auvent ou en cour | MNT LiDAR HD interpolé, levé au sol | Points virtuels et interpolation : à signaler |
| Terrain avant travaux à la date de dépôt | Levé récent ; millésime LiDAR à afficher | Ancienneté non corrigeable par le calcul |
| Limites séparatives, alignement | Bornage, plan de géomètre | Non substituable par le PCI |
| Règle applicable (zone, hauteur, prospect) | GPU (zonage, prescriptions), règlement écrit | Vérifier la version opposable |
| Nombre de niveaux, hauteurs intérieures | NB_ETAGES (indicatif), relevé intérieur | Inaccessible par voie aérienne |

- La hauteur BD TOPO (à la gouttière) et la hauteur totale du lexique (au faîtage ou à l'acrotère) n'ont pas la même définition. La formule Z_MAX_TOIT − Z_MIN_SOL s'en approche, mais avec un décile de MNS et un minimum sur l'emprise, pas un point « à sa verticale ».
- La règle de fusion des bâtiments contigus empêche d'utiliser sans contrôle un objet BD TOPO comme une unité de façade pour une séquence de rue.

### Gaps
- Scans terrestres, mobile mapping, drone, RGE ALTI, BD ORTHO : aucune spécification vérifiée dans cette recherche ; à documenter.
- Panoramax : aucune source trouvée sur l'usage en relevé de façades ou de hauteurs ; sa mention dans le tableau est une hypothèse d'usage.
- Précision chiffrée du PCI : non trouvée (la fiche IGN Parcellaire Express n'a pas été lue).
- Valeur juridique exacte de la consultation du GPU : seulement des sources secondaires. La règle de publication et d'opposabilité reste à vérifier (L133-1 et suivants, L153-23, à contrôler).
- Débords de toit : la page BD TOPO ne donne aucune règle spécifique. Aucune source fiable n'en traite pour le LiDAR HD.

## Pratiques documentées : agences, Cerema, IGN, climat urbain, risques, patrimoine

### Takeaway
L'usage public documenté porte sur des indicateurs agrégés (LCZ, morphologie, hauteurs raster) et sur les risques. Je n'ai trouvé aucune publication française décrivant des architectes, CAUE ou ENSA produisant des coupes réglementaires ou d'analyse depuis le LiDAR HD.

### Cited Findings
- **Cerema, LCZ nationale** : 17 classes (10 bâties, 7 naturelles), 10 indicateurs (morphologie, occupation du sol, propriétés thermophysiques), hauteur moyenne et emprise moyenne par polygone Urban Atlas, données 3D de bâti ; usage de pré-diagnostic pour cibler des quartiers prioritaires (extrait de recherche) — [Présentation A. Ceyte, DINAMIS](https://theia.sedoo.fr/wp-content-theia/uploads/sites/6/2025/04/Presentation-A.CEYTE-webinaire-de-printemps-DINAMIS_CartographieNationaleLCZ_DINAMIS.pdf)
- **MApUCE** : plus de 50 agglomérations, 80 indicateurs morphologiques, typologiques et socio-économiques, à partir de la seule BD TOPO, de la BD Parcellaire et du recensement, pour homogénéité nationale (extrait de recherche) — [Rapport MApUCE, CNRM](https://www.cnrm.meteo.fr/vurca/IMG/pdf/rapport_scientifique_mapuce_v1.2.pdf). La chaîne GeoClimate calcule indicateurs morphologiques et LCZ — [Documentation GeoClimate](https://zenodo.org/records/6372337/files/GeoClimate_0.0.1_documentation.pdf)
- **Apur** : le jeu « Volume bâti » tire ses hauteurs et types de toiture de traitements d'images, avec statistiques moyenne / minimum / maximum par bâtiment (extrait tronqué) — [Géocatalogue Apur](https://geocatalogue.apur.org/catalogue/srv/api/records/urn:apur:emprise_batie_od)
- **Strasbourg** : raster public de hauteur du bâti dérivé de points classés bâtiment, à 50 cm — [Métadonnées](https://www.sig.strasbourg.eu/datastrasbourg/3d_fiches_metadonnees_pdf/2025/metadata_raster_hauteur_bati.pdf)
- **Risques** : un jeu de données ouvert définit des profils en travers de PPRI portant des cotes NGF de crue de référence — [data.gouv](https://www.data.gouv.fr/datasets/profil-en-travers-de-ppri-2/informations). Pour Exzeco, le Cerema indique que la version 5 m issue du LiDAR est une donnée brute non expertisée — [Cerema](https://www.cerema.fr/fr/print/pdf/node/536). Une présentation Grand Est distingue MNT brut et MNT retravaillé pour le risque (extrait de recherche) — [Reflood, DataGrandEst](https://www.datagrandest.fr/portail/sites/default/files/3-3-presentation-reflood-datagrandest-ic-dt-2025.pdf)
- Une présentation SFPT 2025 intègre le LiDAR HD pour détecter et caractériser des surplombs le long de la RD25 dans l'Hérault ; il semble s'agir de surplombs rocheux et non de bâti (à confirmer) — [Azemard, SFPT](https://www.sfpt.fr/wp-content/uploads/2025/03/02_Azemard_2025-03-17_azemard-SFPT.pdf)
- Une thèse EPFL dérive volumes, surfaces de façades et de toitures depuis LiDAR et modèles 3D sur la vieille ville de Genève (hors France) — [EPFL Infoscience](https://infoscience.epfl.ch/record/151698?ln=fr)

### Inferences
- Les bases climatiques nationales se sont construites sur la BD TOPO pour leur homogénéité : le LiDAR HD apporterait surtout une meilleure hauteur par bâtiment, sans que le passage à un rapport H/L de rue soit documenté.
- L'avertissement du Cerema sur la donnée brute à 5 m est la pratique la plus proche d'une mise en garde formelle trouvée pour un produit dérivé du LiDAR.

### Gaps
- Aucune source trouvée calculant un H/L de rue depuis le LiDAR HD en France, ni pour îlot de chaleur ni pour morphologie.
- Aucune trouvée pour un usage CAUE, ENSA ou agence d'urbanisme de coupes LiDAR HD ; le patrimoine et les coupes paysagères ne sont pas documentés. L'absence peut tenir à la recherche, et une enquête directe auprès de praticiens reste nécessaire.
- L'IGN citerait l'architecture parmi les usages (taille, hauteur, exposition du bâti ; extrait de recherche, source exacte non identifiée).
- Le [guide PPRi débordement de cours d'eau 2024](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide%20PPRI%20debordement%20de%20cours%20d%27eau%202024.pdf) n'a pas été lu : les exigences de levé pour la cote de référence restent à établir.

## Ce qu'un praticien peut accepter d'une coupe automatique LiDAR HD, et les réserves à porter sur le dessin

### Takeaway
Une coupe automatique est défendable comme document d'étude préalable, d'analyse urbaine ou de pré-diagnostic, et non comme pièce contractuelle ou preuve de conformité sans reprise par levé. Cette conclusion est une déduction à partir des textes et des précisions : aucune enquête de praticiens n'a été trouvée.

### Cited Findings
- L'OGE exige de qualifier la donnée livrée (précision, niveau de détail, durée de vie, aspects juridiques, limites d'utilisation) — [Recueil OGE](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- Un plan de nivellement doit indiquer son système altimétrique, ses repères et leur altitude — [Recueil OGE, §5.3](https://www.geometre-expert.fr/wp-content/uploads/2023/12/RecueilDesPrestations_Majdec23.pdf)
- La hauteur s'apprécie par rapport au terrain existant avant travaux à la date de dépôt — [Fiche technique 13](https://www.doubs.gouv.fr/contenu/telechargement/34198/214414/file/Lexique%20national%20de%20l'urbanisme.pdf)
- Le Cerema qualifie de donnée brute non expertisée un produit à 5 m issu du LiDAR — [Cerema](https://www.cerema.fr/fr/print/pdf/node/536)
- Une donnée consultée en ligne doit être vérifiée lorsque l'enjeu est juridique ou financier, le document opposable étant celui en vigueur auprès de la collectivité (source secondaire) — [lecadastre.com](https://lecadastre.com/faq-cadastre-plu)

### Inferences

**Domaines d'acceptabilité proposés (non validés par des praticiens)**

| Usage | Acceptable | Condition |
|---|---|---|
| Lecture de site, topographie générale, coupe de territoire (1/1000 et plus) | Oui | Millésime et source affichés |
| Analyse urbaine, profil de rue, ratio H/L, séquences | Oui, indicatif | Hauteur et largeur arrondies ; définition affichée |
| Pré-faisabilité, capacité, enveloppe indicative de gabarit | Oui, à valider | Limites et hauteurs à reprendre par levé |
| Pièce PC3 / PCMI3 | Non, sauf comme fond provisoire | Reprise sur levé, responsabilité du signataire |
| Contrôle de prospect ou d'une hauteur en contentieux | Non | Levé contradictoire et limites établies |
| Coupe de relevé 1/50 – 1/100, réhabilitation | Non | Accès intérieur nécessaire |

**Réserves à faire figurer sur le dessin**
1. Mention « document d'étude, sans valeur de levé topographique ni de pièce réglementaire ».
2. Source et millésime du nuage (date d'acquisition), rappel que le terrain avant travaux à la date de dépôt peut différer.
3. Précision annoncée (altimétrie et planimétrie) et sa source, avec absence de contrôle local.
4. Système de référence planimétrique et altimétrique.
5. Tracé de coupe, largeur de bande de projection et échelle maximale d'usage.
6. Distinction graphique entre surfaces mesurées et surfaces interpolées (sol sous couvert, points virtuels, façades déduites).
7. Définition de chaque hauteur (égout, faîtage, acrotère ; point au pied retenu ; superstructures exclues ou non).
8. Origine des limites et mention que le cadastre ne les fixe pas ; rappel de vérifier le règlement opposable.
9. Aucun intérieur, et façades ni débords non relevés.

### Gaps
- Aucune enquête, position de CAUE, d'Ordre des architectes ou d'assureur trouvée sur l'usage d'une telle donnée.
- Responsabilité du signataire et de l'éditeur d'un outil automatique : non étudiée.
- Mention légale ou licence IGN à reprendre sur un dessin dérivé : non vérifiée.
