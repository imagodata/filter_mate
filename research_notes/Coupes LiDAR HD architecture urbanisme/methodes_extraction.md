# Méthodes d'extraction de coupes et de profils à partir de nuages aéroportés, jusqu'au dessin vectoriel

Conventions de ces notes : **[texte lu]** = passage lu dans l'article complet ; **[extrait seul]** = seuls un résumé ou un extrait de moteur de recherche ont été vus, à revérifier avant citation ferme. Les formules et ordres de grandeur sans source figurent dans « Inferences » : ce sont des dérivations propres, pas des résultats publiés. Notations : ρ = densité planimétrique (pts/m²), t = épaisseur de tranche, b = pas de station le long de la coupe, s = abscisse curviligne, n = normale au plan de coupe.

## Extraction de la tranche : épaisseur, projection, coupes brisées, index COPC, niveaux de détail

### Takeaway
L'épaisseur se dimensionne par le nombre de points voulu par station (t ≈ n/(ρ·b)), ce qui donne environ 0,25 à 2 m entre 50 et 10 pts/m², et se paie en étalement sur les surfaces obliques à la coupe. La lecture COPC doit passer par un polygone de corridor orienté et non par sa boîte englobante ; les niveaux de l'octree servent à l'aperçu, le calcul final se fait en pleine résolution.

### Cited Findings
- COPC est un fichier LAZ 1.4 dont les nœuds d'octree sont des chunks LAZ adressables individuellement ; la hiérarchie (VLR `copc`/1000) est faite de pages d'entrées de 32 octets : VoxelKey (level, x, y, z), offset, byteSize, pointCount — [spécification COPC](https://copc.io/).
- `pointCount > 0` désigne un chunk de données, `-1` une page enfant, `0` un nœud vide dont les enfants peuvent contenir des points — [spécification COPC](https://copc.io/).
- Le VLR info stocke `center_x/y/z`, `halfsize` et `spacing`, espacement au nœud racine qui est divisé par deux à chaque niveau — [spécification COPC](https://copc.io/). La spécification ne décrit aucun algorithme de requête spatiale ni de sélection de niveau de détail (constat sur cette même page).
- COPC impose les formats de point LAS 6, 7 ou 8 — [miroir de la spécification COPC, extrait seul](https://github.com/noahkimtai/copcio.github.io).
- `readers.copc` accepte `bounds` (2D ou 3D), `polygon` (WKT ; plusieurs polygones sont traités comme un multipolygone), `ogr` (requête OGR fournissant des polygones) et `resolution` (« limit the pyramid levels of data to fetch based on the expected resolution of the data », dans l'unité des données, sans limite par défaut) ; `requests` = fils de travail, 15 par défaut — [PDAL readers.copc](https://pdal.io/en/stable/stages/readers.copc.html).
- `filters.crop` accepte `bounds` (boîtes alignées sur les axes, 2D ou 3D), `polygon` (WKT), `point` + `distance`, `outside` — [PDAL filters.crop](https://pdal.io/en/stable/stages/filters.crop.html).
- Précédent aéroporté direct : pour des chemins forestiers à environ 5 pts/m², David et al. calculent des coupes équidistantes dans le nuage brut, sur des boîtes orientées perpendiculairement au tracé, de **1 m d'épaisseur et 20 m de long** ; les échos y sont triés selon l'axe long puis reliés dans cet ordre, chaque coupe étant traitée indépendamment — [David et al., 2009, IGN/MATIS, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/242_laserscanning09.pdf).

### Inferences
**Projection orthogonale (coupe droite A→B).** u = (B−A)/‖B−A‖, n = u tourné de 90° dans le plan horizontal. Pour chaque point P :

```
s = (P − A) · u
d = (P − A) · n
garder si |d| ≤ t/2 et 0 ≤ s ≤ L ; sortie (s, z), conserver d comme attribut
```

Retour au 3D d'un sommet de dessin : P = A + s·u, à l'altitude z (le sommet est dans le plan de coupe).

**Dimensionnement de t.** Densité linéaire sur surface horizontale : λ = ρ·t pts/m. Pour n points attendus par station de largeur b : t ≥ n/(ρ·b). En approximation de Poisson, P(station vide) = exp(−ρ·t·b). L'hypothèse est optimiste : le balayage réel est structuré en lignes, avec des densités hétérogènes entre bandes.

| ρ (pts/m²) | espacement moyen 1/√ρ | t pour n=3, b=0,25 m (5 % de stations vides) | t pour n=5, b=0,25 m (0,7 %) |
|---|---|---|---|
| 10 | 0,32 m | 1,2 m | 2,0 m |
| 20 | 0,22 m | 0,6 m | 1,0 m |
| 50 | 0,14 m | 0,24 m | 0,4 m |

Le choix de 1 m à 5 pts/m² par David et al. correspond à environ 1,25 point par station de 0,25 m : leur b effectif est donc plus large, ou les stations vides sont tolérées.

**Coût de l'épaisseur (étalement).**
- Arête verticale coupée avec une obliquité θ par rapport à la normale : étalement horizontal ≈ t·tan θ (t=1,2 m, θ=10° : 0,21 m ; t=0,24 m : 0,04 m). Il faut donc soit aligner la coupe sur la normale des murs, soit réduire t.
- Pente de toit g dans la direction n (coupe parallèle à l'égout) : bande verticale Δz ≈ t·g (pente 40°, t=1,2 m : 1,0 m ; t=0,24 m : 0,2 m).
- Compensation possible : ajuster un plan local z = f(s, d) dans la tranche puis évaluer à d=0, au lieu de projeter brutalement. Cela permet une tranche épaisse sans perte de netteté sur les surfaces planes, et c'est le seul moyen correct d'exploiter t > 1 m sur toits en pente.

**Coupe brisée (polyligne).** s devient curviligne ; chaque point est affecté au segment le plus proche (partition de Voronoï des segments), ce qui règle les deux défauts du découpage naïf par rectangles :
- côté intérieur d'un sommet de déflexion φ, deux rectangles se recouvrent sur t/2·tan(φ/2) environ, d'où des doublons ;
- côté extérieur, un coin n'est couvert par aucun rectangle.

Tracer une ligne verticale fine sur le dessin à chaque sommet : l'abscisse s y est continue mais le plan change. Les grandeurs angulaires (pentes, verticalité) ne sont comparables qu'à l'intérieur d'un même segment.

**Stratégie d'index.**
- Parcours de l'octree : un nœud (L, x, y, z) a pour côté c = 2·halfsize/2^L et pour coin min = centre − halfsize + c·(x, y, z). Élaguer par test rectangle orienté contre AABB (axes séparateurs) sur le plan XY.
- Ne pas passer la boîte englobante du corridor : une coupe de L à 45° a une AABB de L²/2 contre L·t pour le corridor, soit un facteur L/(2t) = 250 pour L=1 km, t=2 m. Utiliser `polygon` en WKT (le rectangle tamponné), éventuellement en multipolygone pour une série de coupes.
- Volume utile faible : 1 km × 1 m × 50 pts/m² ≈ 50 000 retours, ordre de grandeur à majorer selon le nombre d'échos. Le coût réel vient des chunks entiers à décompresser pour n'en garder qu'une fraction.

**Niveaux de détail.** Niveau cible : L* = ⌈log₂(spacing₀ / espacement voulu)⌉. Attention, les points d'une tranche sont répartis sur tous les niveaux de 0 à la profondeur maximale : un niveau n'est pas une couche indépendante, et il faut lire les nœuds de 0 à L*. Le sous-échantillonnage octree est un espacement 3D : il conserve mal les points rares comme ceux de façade, ce qui le rend inadapté au calcul final. À réserver à l'aperçu interactif.

### Gaps
- Aucune étude trouvée qui compare empiriquement plusieurs épaisseurs de tranche sur données aéroportées pour la qualité d'un dessin de coupe ; les valeurs ci-dessus sont dérivées, sauf le cas 1 m / 5 pts/m².
- Sémantique exacte de `resolution` dans `readers.copc` (critère d'arrêt par rapport à `spacing`) non documentée sur la page lue ; à vérifier dans le code PDAL.
- Le comportement des lectures COPC sur corridors très allongés (nombre de chunks touchés par rapport au volume utile) n'a pas fait l'objet de mesure publiée trouvée.

## Construction de la courbe de profil : enveloppes, alpha shapes, images de densité, percentiles, retours multiples

### Takeaway
Trois représentations sont complémentaires : statistiques par station (robustes, 1D), image de densité (s, z) (conserve les structures multiples, seule base viable pour la détection de segments) et alpha shape (contour fidèle mais sans remède contre les façades manquantes). Les percentiles remplacent avantageusement min/max : la chaîne 3DBAG utilise p5 pour le sol et p70 pour les toits de LoD1.

### Cited Findings
- Recette percentile à l'échelle nationale : le niveau du sol est le **5e percentile** des points sol dans un **tampon de 4 m** autour du bâtiment ; la hauteur de référence LoD1.2/1.3 est le **70e percentile** des points de toit ; min, max, p50 et p70 sont attachés aux parties de toit — [Peters et al., 2022, texte lu](https://arxiv.org/pdf/2201.01191). Attributs correspondants : `b3_h_maaiveld`, `b3_h_50p`, `b3_h_70p`, `b3_h_max`, `b3_h_min` — [3DBAG, schéma des attributs](https://docs.3dbag.nl/en/schema/attributes/).
- Pour les coupes de chemins, David et al. construisent le profil altimétrique à partir du **premier écho**, puis le simplifient par Douglas-Peucker — [David et al., 2009, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/242_laserscanning09.pdf).
- Alpha shape 2D (CGAL) : famille de formes construite sur la triangulation de Delaunay ; α est le **rayon au carré** du disque ; un simplexe est α-exposé si un disque ouvert de rayon √α passant par ses sommets ne contient aucun autre point ; α→0 donne les points, α→∞ l'enveloppe convexe. `find_optimal_alpha(n)` vise n composantes connexes, `find_alpha_solid()` donne le plus petit α formant un solide — [CGAL Alpha_shapes_2](https://doc.cgal.org/latest/Alpha_shapes_2/index.html).
- Alternative GEOS : `shapely.concave_hull(geometry, ratio, allow_holes)` avec ratio dans [0, 1], GEOS ≥ 3.11 — [Shapely](https://shapely.readthedocs.io/en/stable/reference/shapely.concave_hull.html).
- L'alpha shape est réputée donner des points de contour fiables en préservant les petits détails, en pratique sur contours de bâtiments en plan ; résultat jugé bon au-dessus de **6 pts/m²** — [Albers et al., 2016, texte lu](https://isprs-archives.copernicus.org/articles/XLI-B3/555/2016/isprs-archives-XLI-B3-555-2016.pdf).
- `writers.gdal` rasterise avec `min`, `max`, `mean`, `idw`, `count`, `stdev` dans un rayon (par défaut résolution × √2) ; avec `binmode: true`, seuls les points de la cellule comptent et des bandes percentile `p<nn>` deviennent disponibles ; `window_size` comble les cellules vides ; `dimension` choisit l'attribut (Z par défaut) — [PDAL writers.gdal](https://pdal.io/en/stable/stages/writers.gdal.html).
- `filters.smrf` classe le sol ; valeurs par défaut cell=1,0, slope=0,15, scalar=1,25, threshold=0,5, window=18,0, en n'utilisant que les retours « last, only » — [PDAL filters.smrf](https://pdal.io/en/stable/stages/filters.smrf.html). Des utilisateurs signalent que pmf et smrf tendent à inclure la végétation basse dans le sol — [liste PDAL, signalement non vérifié](https://lists.osgeo.org/pipermail/pdal/2018-March/001493.html).
- La hauteur au-dessus du sol par `filters.hag_delaunay` interpole dans une triangulation des `count` (10) plus proches points sol ; hors triangle, la hauteur est relative au point sol le plus proche ; hors de l'emprise des points sol, HAG vaut 0 sauf `allow_extrapolation` — [PDAL hag_delaunay](https://pdal.io/en/stable/stages/filters.hag_delaunay.html).

### Inferences
**Enveloppes par station (largeur b).**

```
pour chaque station k de [s_k − b/2, s_k + b/2] :
  z_sol(k)  = percentile p5 des points classe sol       (ou min si n < 5)
  z_haut(k) = percentile p95 de tous les points non bruit (DSM de coupe)
  z_bati(k) = percentile p95 de la classe bâti
  n(k), étendue z(k), nombre de retours multiples
stations vides : NaN, jamais d'interpolation silencieuse à ce stade
```

Le percentile 5 ou 95 n'a de sens que pour au moins une dizaine de points ; en dessous, il dégénère en min/max. Avec n=3 à 5 par station, min/max plus filtre de bruit préalable valent mieux qu'un percentile nominal.

**Image de densité (s, z).** Effectuer le changement de repère (X,Y,Z)→(s,z,d) puis réutiliser les rasteriseurs plans (`writers.gdal` en `binmode` avec `output_type=count` sur le couple (s,z), après transformation matricielle des coordonnées) est un moyen de réemployer l'outillage PDAL existant. Cellule a ≈ 0,1 à 0,25 m. Appliquer log(1 + count) ou une normalisation par colonne : la dynamique entre toit dense et façade rare est trop grande pour un seuillage direct.

**Occupation multi-valeur.** La distribution par colonne en z révèle plusieurs structures empilées (feuillage puis sol, toit bas puis mur) qu'une enveloppe unique efface. L'image de densité est la seule représentation qui les conserve ; d'où son usage en entrée de la vectorisation.

**Paramétrage d'alpha.** Un trou de largeur g n'est franchi que si √α ≥ g/2, soit α ≥ (g/2)².
- Pour relier le toit à ±1 m : α ≥ 0,25 m².
- Pour franchir un mur sans points de 8 m : √α ≥ 4, α ≥ 16 m², valeur qui lisse complètement cheminées et lucarnes.

Conclusion : alpha shape pour l'enveloppe supérieure et les objets denses, pas pour relier toit et sol. `concave_hull` s'exprime par un ratio sans unité, ce qui le rend moins pilotable qu'un rayon métrique en section.

**Retours multiples et végétation.** Ordre conseillé : conserver tous les échos à la lecture ; tracer sol sur la classe 2 (dernier retour de fait) ; tracer bâti sur la classe 6 ; représenter la végétation séparément (nuage ou enveloppe souple), jamais incluse dans la ligne de coupe bâtie. Les premiers retours donnent l'enveloppe haute sous réserve de filtrer les arbres. Dépendance forte à la qualité de classification, à contrôler sur les pieds de façades et les haies.

### Gaps
- Aucun article trouvé comparant quantitativement enveloppe, alpha shape et image de densité pour des coupes aéroportées.
- Pas de seuil publié pour le nombre minimal de points par station ; la valeur « une dizaine » ci-dessus est un raisonnement statistique.
- Aucune étape PDAL dédiée à la densité en tranche verticale n'a été trouvée ; il faut composer des filtres ou écrire le calcul.

## Vectorisation : détection de segments, simplification, régularisation, reconstruction de profil, comblement des occlusions

### Takeaway
Pour une coupe aéroportée, la voie la plus sûre est de partir d'une enveloppe ou d'un contour puis d'appliquer une détection de segments contrainte (RANSAC ou Hough dans (s, z)), la simplification, et enfin une régularisation par programme quadratique avec directions imposées. LSD appliqué à une image clairsemée sur-segmente et produit des segments parasites le long des lignes de scan ; les vides doivent être marqués comme inférés, non dessinés comme mesurés.

### Cited Findings
- **RANSAC.** Efficient RANSAC décompose un nuage non organisé en formes simples et points restants ; robuste au bruit et aux valeurs aberrantes ; plusieurs millions de points en moins d'une minute — [Schnabel et al., 2007, extrait seul](https://cg.cs.uni-bonn.de/backend/v1/files/publications/schnabel-2007-efficient.pdf). Open3D `segment_plane(distance_threshold, ransac_n, num_iterations)` renvoie (a, b, c, d) et les inliers — [Open3D](https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html).
- **Tolérance d'ajustement dérivée du bruit.** He et al. fixent la tolérance plan à **2σ** mesuré sur surfaces planes (σ observés 0,032 à 0,064 m ; tolérances retenues 0,09 m à Enschede et 0,10 m à Melbourne) — [He et al., 2012, texte lu](https://isprs-archives.copernicus.org/articles/XXXIX-B3/115/2012/isprsarchives-XXXIX-B3-115-2012.pdf).
- **Hough.** Espace (α, d) discrétisé ; chaque point devient une sinusoïde, les points colinéaires s'intersectent ; Albers et al. l'utilisent pour trouver les directions principales puis extraire des segments orientés — [Albers et al., 2016, texte lu](https://isprs-archives.copernicus.org/articles/XLI-B3/555/2016/isprs-archives-XLI-B3-555-2016.pdf). Croissance de régions amorcée par Hough 3D pour extraire des murs : [Rutzinger et al., 2009, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/7_laserscanning09.pdf).
- **LSD.** Temps linéaire, contrôle a contrario du nombre de fausses détections (NFA, en moyenne une fausse alarme par image), sans réglage de paramètre — [von Gioi et al., IPOL, extrait seul](https://www.ipol.im/pub/art/2012/gjmr-lsd/revisions/2012-03-24/article.pdf).
- **Comparaison sur images issues de projection.** Sur des patchs planaires projetés en images, Zhai et al. obtiennent avec LSD et FLD plus de segments mais moins complets (sur-segmentation), leur méthode par graph-cut donnant moins de segments mais plus précis ; ils notent aussi que **les distributions linéaires clairsemées des scanners induisent des segments parasites**. Segments 3D par scène : graph-cut 1505 / 542 / 2393, LSD 1687 / 542 / 2738, FLD 1552 / 427 / 2121 — [Zhai et al., 2025, texte lu](https://isprs-archives.copernicus.org/articles/XLVIII-1-W5-2025/161/2025/isprs-archives-XLVIII-1-W5-2025-161-2025.pdf). Conférence de mobile mapping : le caractère aéroporté des données n'est pas établi, transfert à vérifier.
- **Familles de méthodes par tranches.** Zhai et al. classent les méthodes : par tranchage et projection (la famille qui tranche le nuage selon plusieurs axes, agrège les points de contour, puis ajuste des segments 3D, avec renvoi à Zhao et al. 2022 et Tian et al. 2022), par intersection de plans, par patchs — [Zhai et al., 2025](https://isprs-archives.copernicus.org/articles/XLVIII-1-W5-2025/161/2025/isprs-archives-XLVIII-1-W5-2025-161-2025.pdf). Variante récente par tranches et composantes connexes étiquetées, évaluée notamment sur des données ALS — [He et al., 2026, résumé seul](https://www.sciopen.com/article/10.1080/10095020.2025.2591258).
- **Douglas-Peucker.** `shapely.simplify(tolerance, preserve_topology=True)` utilise cet algorithme, la tolérance étant le déplacement maximal admis — [Shapely](https://shapely.readthedocs.io/en/stable/reference/shapely.simplify.html).
- **Visvalingam-Whyatt.** Élimination progressive selon l'aire effective ; résultats jugés favorables face à une généralisation manuelle sur deux traits de côte, avec Douglas-Peucker comme comparaison — [Visvalingam & Whyatt, 1993, notice](https://hull-repository.worktribe.com/output/380441). Les mêmes auteurs contestent les mesures mathématiques habituelles de qualité — [réévaluation, 1990](https://diglib.eg.org/items/8faa5f5f-83db-4290-abfe-b1dda6a3b1cb). Source ancienne et émanant des auteurs eux-mêmes.
- **Polyligne par transport optimal (City3D).** Sur une carte de hauteurs raster, contours Canny puis triangulation de Delaunay simplifiée par effondrement d'arêtes, sous contrainte de Hausdorff `e_d` et de coût de transport `e_c` ; `e_d=0,25`, `e_c=2,0` ; résolution 0,20 m (AHN3), 0,15 m (DALES), 0,25 m (Vaihingen) — [City3D, Huang et al., 2022, texte lu](https://arxiv.org/pdf/2201.10276).
- **Régularisation par QP.** CGAL Shape Regularization : `Angle_regularization_2` (déviation max dans [0°, 90°], défaut 25°), `Offset_regularization_2` (colinéarité, défaut 0,5 unité), `regularize_open_contour` et `regularize_closed_contour`, directions `Longest_direction_2`, `Multiple_directions_2` ou `User_defined_directions_2`. Énergie = terme de données + terme de paires pondéré par λ, résolue en QP avec OSQP recommandé. Ordre type : angles puis décalages — [CGAL Shape Regularization](https://doc.cgal.org/latest/Shape_regularization/index.html).
- **Régularisation par énergie.** Albers et al. : contour par alpha shape, directions par Hough, puis ajustement global par Viterbi admettant plus d'une orientation principale — [Albers et al., 2016, texte lu](https://isprs-archives.copernicus.org/articles/XLI-B3/555/2016/isprs-archives-XLI-B3-555-2016.pdf). Chez d'autres auteurs, directions dominantes par pics d'histogramme, ou Douglas-Peucker adapté (Vertex-driven DP) — [He et al., 2014, extrait seul](https://isprs-annals.copernicus.org/articles/II-3/65/2014/isprsannals-II-3-65-2014.pdf).
- **Reconstruction de profil de toit par coupe perpendiculaire au faîtage.** Arefi : un modèle 2D prédéfini est ajusté selon le type de toit puis étendu en 3D ; faîtages trouvés par maxima locaux (dilatation géodésique) — [Arefi, ASPRS 2010, extrait seul](https://asprs.org/wp-content/uploads/2013/08/Arefi.pdf) ; pixels de chaque partie projetés dans un plan 2D défini par l'orientation du faîtage — [version ISPRS, extrait seul](https://www.isprs.org/proceedings/XXXVIII/1-W17/15_Arefi.pdf). Choix du modèle par analyse des hauteurs le long du faîtage et perpendiculairement à celui-ci, faîtage ajusté par RANSAC — [Partovi et al., 2013, extrait seul](https://doaj.org/article/d731d6808bcd438c9723754fc4b0c1ab). Ces travaux portent sur MNS satellite ou aéroporté, pas directement sur le nuage.
- **Complétion par apprentissage.** APC2Mesh complète le nuage avant maillage pour les façades occluses — [APC2Mesh, extrait seul](https://www.alphaxiv.org/abs/2404.02391). Seule référence d'apprentissage profond retenue, car elle traite directement l'occlusion ; rien de propre aux coupes.

### Inferences
**Chaîne recommandée dans le plan (s, z).**

1. Séparer les couches (sol, bâti, végétation) et traiter chacune.
2. Bâti : extraire l'enveloppe haute ou le contour (alpha shape avec √α ≈ 1 à 1,5 m), puis RANSAC séquentiel 2D.
3. Pour le RANSAC : N = log(1−p) / log(1−w²) itérations pour une droite, soit 458 à w=0,1 et 49 à w=0,3 pour p=0,99. Seuil ε ≈ 2σ, soit environ 0,1 m. Exiger une longueur minimale et une densité minimale d'inliers le long du segment pour écarter les colinéarités fortuites des lignes de scan.
4. Hough en secours pour imposer des directions connues. Discrétisation Δd ≈ ε et Δα ≈ 1 à 2°.
5. Simplification Douglas-Peucker avec tolérance ≥ 2σ et ≥ b/2 : sous cette valeur on ne vectorise que du bruit. Pour le terrain, Visvalingam ou un Douglas-Peucker à tolérance faible, car la forme compte plus que l'extrémum isolé.
6. Régularisation : `regularize_open_contour` convient exactement à une coupe (contour ouvert), avec directions imposées {0°, 90°} via `User_defined_directions_2`. Déviation max à réduire nettement sous les 25° par défaut, de l'ordre de 5 à 10°, sinon un toit à faible pente bascule à l'horizontale. Laisser les pans de toit libres, mais forcer l'égalité des pentes opposées quand le faîtage est symétrique à la tolérance près.

**Transposition du transport optimal de City3D** : le procédé opère sur tout ensemble de pixels de contour ; il peut s'appliquer à une image (s, z) en dimensionnant `e_d` à environ 0,25 m.

**Comblement.** Trois cas à distinguer sur le dessin : mesuré (trait continu) ; inféré par règle (tireté : mur vertical entre égout et sol) ; inconnu (interruption). Le comblement par coupes voisines (interpolation entre coupes d'une série) est plausible pour les objets extrudés, mais il suppose la continuité longitudinale et doit être marqué.

### Gaps
- Aucun banc d'essai trouvé comparant RANSAC, Hough, LSD et croissance de régions en 2D sur des coupes aéroportées à 10–50 pts/m². Les recommandations ci-dessus s'appuient sur des transferts et un raisonnement.
- Les travaux de Zhao et al. 2022 et Tian et al. 2022 (slicing) n'ont pas été lus ; seule leur description par Zhai et al. est disponible.
- L'application de `regularize_open_contour` à des coupes verticales n'est documentée nulle part : le paquet est générique.
- Détail des équations d'ajustement 2D d'Arefi non lu (PDF indisponible).

## Façades peu denses : inférer les murs, extrusion, emprises, plans verticaux, précision documentée

### Takeaway
En aéroporté, le mur n'est pas mesuré mais déduit : soit par extrusion de l'emprise, soit par extrusion du contour du toit, soit, là où ils existent, par ajustement de plans sur les rares échos de façade. Les RMSE publiées (quelques cm à 0,3 m) mesurent l'écart des points au modèle, et donc essentiellement les toits ; elles ne valident pas la position du mur, pour laquelle les chiffres sont rares et conditionnels.

### Cited Findings
- **Constat.** Les murs verticaux sont « couramment manqués » par le lidar aéroporté alors que les toits sont bien saisis — [City3D, texte lu](https://arxiv.org/pdf/2201.10276). L'ALS représente les murs de manière moins détaillée en raison de faibles densités aggravées par de grands angles d'incidence ; la complétude dépend fortement de la position relative capteur/objet — [Rutzinger et al., 2009, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/7_laserscanning09.pdf).
- **Débord de toit.** Le contour issu du nuage aéroporté ne donne pas la position exacte du mur en présence d'un débord — [Rutzinger et al., 2009, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/7_laserscanning09.pdf). Les polygones BAG représentent les murs extérieurs vus du dessus, précision annoncée 0,3 m — [City3D, texte lu](https://arxiv.org/pdf/2201.10276).
- **Extrusion depuis le contour du toit, sans emprise (City3D).** Carte de hauteurs raster via TIN Delaunay (rendue continue sur les trous), morphologie, Canny, polyligne par transport optimal, extrusion en plans verticaux ; ces plans servent aussi à l'intérieur de l'emprise pour les murs intérieurs — [City3D, texte lu](https://arxiv.org/pdf/2201.10276).
- **Extrusion depuis le bas.** Dans la chaîne 3DBAG, les parties de toit sont extrudées jusqu'au niveau sol pour former un maillage ; les points de façade sont retirés ; les parties de toit exigent au moins 15 points, soit environ 2 m² à 8 pts/m² — [Peters et al., 2022, texte lu](https://arxiv.org/pdf/2201.01191).
- **Plans verticaux par échos de façade.** He et al. cherchent les points de mur au voisinage de chaque segment de toit, ajustent un plan, et déterminent ses limites par relations topologiques avec le toit, « les points de LIDAR seuls ne suffisant pas à décider des limites des murs » ; les murs non illuminés sont déduits du toit et des murs voisins — [He et al., 2012, texte lu](https://isprs-archives.copernicus.org/articles/XXXIX-B3/115/2012/isprsarchives-XXXIX-B3-115-2012.pdf).
- Combinaison de plans inférés depuis l'emprise et de points de murs existants, avec résolution des conflits — [article 2024, extrait seul](https://bohrium.dp.tech/paper/arxiv/37b3315d4326dfc60db0b6f560b3ce44371d9e2b06302b7bf547cfb6f24fa033). Les méthodes par projection du toit donnent des emprises déformées et omettent des détails de façade, d'où une méthode guidée par la façade — [IJGI 14(12), 462, extrait seul](https://api.crossref.org/works/10.3390%2FIJGI14120462). Dépendance de City3D à l'emprise, une emprise défectueuse se propageant au modèle — [Int. J. Digital Earth 2025, extrait seul](https://www.tandfonline.com/doi/full/10.1080/17538947.2025.2458682).
- **Précision documentée :**

| Source | Données | Grandeur mesurée | Résultat |
|---|---|---|---|
| [Rutzinger 2009](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/7_laserscanning09.pdf) | ALS hélicoptère FLI-MAP 400, multi-vues, vs MLS | Position plani des murs appariés (seuils 0,1 m et 3°) | 24 appariements, **0,05 m RMS**, écart-type 0,04 m |
| [He 2012](https://isprs-archives.copernicus.org/articles/XXXIX-B3/115/2012/isprsarchives-XXXIX-B3-115-2012.pdf) | 20 pts/m² (Enschede, fusion de vols) ; 4–5 pts/m² (Melbourne) | Longueur de façades extraites dans un tampon de 40 cm | Correctness **0,75 / 0,65** ; complétude plus faible, « les deux sont faibles » selon les auteurs |
| [City3D 2022](https://arxiv.org/pdf/2201.10276) | AHN3 8, DALES 50, Vaihingen 4 pts/m² | RMSE points→modèle | 0,04 à 0,26 m ; moyenne AHN3 0,128 m (PolyFit 0,242 ; 2.5D DC 0,213) ; DALES 0,184 (0,287 ; 0,204) ; Vaihingen 0,157 (0,275 ; 0,168) |
| [City3D 2022](https://arxiv.org/pdf/2201.10276) | 2 bâtiments AHN3 | RMSE avec / sans emprise | 0,04 / 0,062 m et 0,06 / 0,089 m |
| [Peters 2022](https://arxiv.org/pdf/2201.01191) | AHN3, 10 M de bâtiments | RMSE points→LoD2.2 | < 31 cm pour 95 % ; < 9 cm pour 75 % |

- City3D recommande l'emprise de qualité quand elle existe, car les murs inférés depuis le toit ne s'alignent pas parfaitement sur l'emprise réelle — [City3D, texte lu](https://arxiv.org/pdf/2201.10276).
- Une analyse de la densité sur surfaces verticales selon l'angle de capture et la hauteur de mur existe — [par.nsf.gov, extrait seul, PDF non récupéré](https://par.nsf.gov/servlets/purl/10293986).

### Inferences
**Portée réelle des RMSE.** RMSE points→modèle : les échos de façade étant rares ou retirés, l'erreur reflète les toits. Le gain de 0,04 à 0,062 m entre avec/sans emprise ne dit donc rien sur l'erreur planimétrique du mur, potentiellement de plusieurs dizaines de cm. Le 0,05 m de Rutzinger est conditionné : il ne porte que sur les murs ayant déjà un appariement à moins de 0,1 m, avec un capteur hélicoptère multi-vues. Ne pas le présenter comme précision typique du mur aéroporté.

**Modèle géométrique des échos de façade.** Un mur vu à l'angle de scan θ depuis la verticale reçoit une densité surfacique ρ_mur ≈ ρ·tan θ (par bande, face tournée vers le capteur uniquement).
- θ=10° : 1,8 pts/m² à ρ=10 ; 8,8 à ρ=50.
- θ=20° : 3,6 à ρ=10 ; 18 à ρ=50.

Nombre de points dans une tranche : ρ·t·H·tan θ. Pour ρ=10, t=1 m, H=10 m, θ=10° : environ 18 points, répartis sur H, exploitables pour un ajustement vertical. Sous un angle de scan faible ou sur la face opposée, ce nombre tend vers 0. L'occlusion par le bâti d'en face ne descend à H_opposé − W/tan θ qu'aux grands angles : à W=10 m, elle disparaît sauf θ supérieur à environ 45° pour H=10 m. Le sol encombré (véhicules, arbres) reste la cause principale d'occlusion en pied de façade.

**Chaîne de décision pour un mur dans une coupe :**
1. intersection de la coupe avec l'emprise : abscisse s_mur fournie si l'emprise existe ;
2. contrôle par échos de façade dans un voisinage de s_mur : si ≥ 5 points couvrant ≥ 30 % de la hauteur, ajustement vertical robuste (médiane des s, écart-type) ;
3. sinon, abscisse de l'égout (rupture de l'enveloppe haute) minorée d'un débord estimé si la donnée d'emprise le permet ;
4. pied de mur : p5 des points sol dans le tampon de 4 m, comme 3DBAG, ou mieux intersection avec le profil de terrain de la coupe (Peters et al. évoquent cette option d'intersection de terrain) ;
5. tracé en tireté si le mur est inféré.

Le décalage entre emprise et égout, mesuré à l'échelle du bâtiment, permet en outre de calculer un débord observé.

### Gaps
- Aucune évaluation quantitative trouvée de la **position plani du mur** inférée par extrusion, sur une vérité terrain indépendante, à 10–50 pts/m². C'est la lacune principale sur cette question.
- Valeur exacte de la complétude chez He et al. non relevée (seule l'affirmation qu'elle est inférieure à la correctness).
- Comparaison directe extrusion d'emprise / plans sur échos de façade à données identiques : non trouvée.
- Le fichier NSF sur la densité verticale n'a pas pu être téléchargé ; à relire si le paramètre θ est critique.

## Profils de terrain : classe sol ou MNT, TIN ou grille, canyons urbains, H/W et facteur de vue du ciel

### Takeaway
Un profil de terrain gagne à être calculé par coupe du TIN des points sol, sans passer par une grille intermédiaire, avec marquage des grandes facettes interpolées. La littérature consultée ne propose pas de comparaison TIN/grille à densité fixe. Le H/W et le SVF se déduisent directement d'une coupe, avec une formule analytique en canyon infini, mais aucune publication trouvée ne les calcule par coupes LiDAR.

### Cited Findings
- L'analyse de terrain est sensible à la représentation (TIN, grille, RTN) et à la taille de cellule ; exemple d'erreur verticale de 2 m due à l'interpolation TIN en zone peu dense, malgré une précision capteur de 10 cm ; dimensionnement « de type Nyquist » (relief de 30 cm : espacement < 15 cm) — [Penn State GEOG 892](https://courses.ems.psu.edu/geog892/node/713).
- La réduction de densité dégrade le MNT dans tous les cas ; MNT restant assez précis jusqu'à 0,40–0,50 pts/m² avec un interpolateur adapté ; IDW peu résistant sous environ 0,60 pts/m² — [Forests 2021, extrait seul](https://mdpi.com/1999-4907/12/3/265/xml). IDW le meilleur dans une zone test italienne, avec absence de règles sur le calcul d'une grille depuis un TIN — [Garnero & Godone, 2013, extrait seul](https://isprs-archives.copernicus.org/articles/XL-5-W3/139/2013/).
- Le sol par `filters.hag_delaunay` utilise la triangulation locale (voir plus haut) ; `filters.hag_nn` requiert la classe 2 — [PDAL hag_nn](https://PDAL.io/stages/filters.hag_nn.html).
- Bordures : ordre de 10 cm détectable en aéroporté, côtés de voie ajustés par RANSAC sur extrémités de segments à faible pente, après segmentation du profil en droites — [Laser scanning 2009, n° 111, extrait seul](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/111_laserscanning09.pdf).
- **Canyon urbain.** H/W est le paramètre géométrique central, dit rapport d'aspect — [Wikipédia, Urban canyon](https://en.wikipedia.org/wiki/Urban_canyon). SVF en milieu de chaussée pour un canyon symétrique infiniment long : **SVF = cos(arctan(2H/W))**, solution attribuée à Oke, valable seulement pour un canyon infini — [Bernard et al., 2018, Climate, extrait seul](https://halshs.archives-ouvertes.fr/halshs-01831117v1/file/climate-06-00060.pdf).
- 1600 canyons genevois mesurés en SVF et rapport d'aspect asymétrique — [EPFL, extrait seul](https://infoscience.epfl.ch/record/265522?ln=en). Le MNS lidar résout mieux les motifs d'ombre et la structure des toits que des données vectorielles à toits plats, mais la dérivation de H/W sur données réelles est difficile — [étude Londres, extrait seul](https://core.ac.uk/download/42150204.pdf). SVF calculé depuis lidar aéroporté — [Remote Sensing 2023, extrait seul](https://doaj.org/article/3a9d6eea80b84aaf88caa598b41c1c07) ; [UCL/CEUS, extrait seul](https://discovery.ucl.ac.uk/10148543/1/CEUS-D-21-00581_R3-chen.pdf).

### Inferences
**Trois modes d'obtention du profil, du plus au moins fidèle aux mesures :**
- *Coupe du TIN des points sol* : l'intersection du plan avec les triangles fournit un profil linéaire par morceaux, sans pas d'échantillonnage. Avantage : pas de double interpolation. Conserver le long du profil la longueur de la plus grande arête du triangle traversé comme indicateur de confiance (au-delà d'un seuil de 3 à 5 m, trait interrompu ou tireté).
- *Échantillonnage d'une grille MNT* : bilinéaire au pas ≤ cellule. Lisse bordures et talus d'environ une cellule ; à réserver à des rendus d'ensemble ou là où la classification est absente.
- *Points sol bruts dans la tranche* : présentent tout le bruit vertical (1σ) ; bon contrôle visuel, à afficher en semis sous le trait.

**Canyons.** La chaussée sous arbres et véhicules est mal couverte : le TIN y tend de longues facettes entre trottoirs, souvent crédibles sur voirie plate, mais qui effacent bordures et caniveaux. Une tranche large et en percentile bas est possible pour les bordures (10 cm ≈ 2σ à 3σ ; à la limite du détectable).

**Dérivation de H/W et SVF depuis la coupe.**
- W : distance en s entre abscisses de murs (cf. chaîne de décision). H : haut de mur (égout) moins sol au pied ; calculer H_G, H_D et leur moyenne, ainsi que H/W asymétrique.
- SVF en canyon infini, généralisation à profil quelconque en station s (dérivation propre, à valider). Avec β_G, β_D les élévations d'horizon maximales à gauche et à droite :

```
β_G(s) = max sur s' < s de arctan((z_haut(s') − z_sol(s)) / (s − s'))
β_D(s) = max sur s' > s de arctan((z_haut(s') − z_sol(s)) / (s' − s))
SVF(s) = ½ (cos β_G + cos β_D)
```

Le cas symétrique redonne bien la formule d'Oke, car cos(arctan(2H/W)) = (W/2)/√(H²+W²/4). Ce calcul fait l'hypothèse d'un canyon infini ; il surestime l'occlusion aux carrefours. Une valeur sans arbres (classes bâti) et une valeur avec arbres (arbres opaques) donnent un encadrement simple.

### Gaps
- Aucune comparaison TIN contre grille à densité fixe trouvée ; le besoin reste ouvert.
- Aucune publication trouvée calculant SVF par intégration de coupes LiDAR en travers ; la formule généralisée ci-dessus est donc une proposition non validée.
- Formule d'Oke vérifiée seulement via citation (Bernard et al.), l'article de 1981 n'ayant pas été consulté.
- Pas de valeur publiée fiable sur l'exactitude de pente transversale en aéroporté : le chiffre de 2 % rencontré (route forestière, source [dergipark, extrait altéré](https://dergipark.org.tr/en/download/article-file/60118)) est trop mal attesté pour être retenu.

## Travaux de reconstruction LoD2 reliés aux coupes (City3D, PolyFit, 3dfier, emprises, méthodes par tranches)

### Takeaway
Ces méthodes reconstruisent par intersection de plans ou par extrusion, et non par coupes ; une coupe est donc dans ce cadre un sous-produit : on peut soit couper le modèle LoD2 (propre, mais hérite de ses hypothèses), soit vectoriser le nuage directement (fidèle à la mesure, moins régulier). Les méthodes réellement fondées sur des tranches restent marginales en aéroporté.

### Cited Findings
- **PolyFit** : plans primitifs intersectés en faces candidates, sélection par étiquetage binaire et programmation linéaire binaire avec contraintes de variété, surface étanche ; pour objets par morceaux plans — [Nan & Wonka, ICCV 2017, extrait seul](https://openaccess.thecvf.com/content_ICCV_2017/papers/Nan_PolyFit_Polygonal_Surface_ICCV_2017_paper.pdf).
- **City3D** : étend PolyFit avec plans verticaux inférés et terme d'énergie de préférence de toit ; poids λ_d=0,34, λ_c=0,62, λ_r=0,04 ; plus de 20 000 bâtiments testés, généralement moins de 30 s par bâtiment, jusqu'à 42 min pour un bâtiment complexe. Comparaison avec BAG3D : RMSE 0,088/0,079, 0,139/0,138, 0,140/0,132, 0,146/0,128 m (BAG3D/City3D, quatre régions) — [City3D, texte lu](https://arxiv.org/pdf/2201.10276).
- **3DBAG/chaîne de Peters** : partition plane de l'emprise à partir des points de toit, LoD1.2, 1.3, 2.2 à partir d'une même source ; qualité suivie par RMSE point/modèle, erreur maximale, codes de validité — [Peters et al., 2022, texte lu](https://arxiv.org/pdf/2201.01191). Attribut `b3_rmse_lod22`, codes `b3_val3dity_*` — [3DBAG](https://docs.3dbag.nl/en/schema/attributes/).
- **3dfier** : relève en 3D des polygones 2D selon leur sémantique, blocs LoD1 pour le bâti, eau plane, routes lissées, assemblage en surface étanche — [3dfier](https://tudelft3d.github.io/3dfier/).
- **Sensibilité à la densité.** Comparaison à vérité manuelle (Pfäffikon, CH, densité déclarée ≥ 5 pts/m²) : les méthodes pilotées par les données (City3D, Augmented KSR) requièrent une densité supérieure ; vers 5 pts/m², éléments manquants et ambiguïtés ; les méthodes à gabarits (BREC, RoofGenerator) résistent mieux mais divergent davantage de la référence. Paramétrage global plausible contre réglage par bâtiment : un réglage améliorant un bâtiment peut en dégrader d'autres — [Jarząbek-Rychard et al., 2025, texte lu](https://isprs-archives.copernicus.org/articles/XLVIII-G-2025/701/2025/isprs-archives-XLVIII-G-2025-701-2025.pdf).
- **Coupe horizontale à hauteur choisie.** Rottmann et al. utilisent une estimation de densité par noyau pour fixer la hauteur de coupe, ordonnent les points par TSP, éliminent les aberrants avec DBSCAN, généralisent ; IoU 0,930 à 0,998. Méthode pensée pour capteur mobile ou drone, car l'ALS montre surtout les toits : **transfert limité à l'aéroporté** — [Rottmann et al., 2022, texte lu](https://isprs-annals.copernicus.org/articles/X-4-W2-2022/233/2022/isprs-annals-X-4-W2-2022-233-2022.pdf).

### Inferences
- Deux voies pour une « coupe de bâtiment » : (a) coupe plane d'un modèle LoD2 (intersection plan/maillage) : traits propres et fermés, murs verticaux par construction, mais c'est la coupe d'une hypothèse ; (b) vectorisation directe du nuage : traits réellement observés, mais incomplets. Superposer (a) en filigrane à (b) donne la lecture la plus honnête.
- Les LoD2 sont sans ouverture, façades planes, et sans intérieur : leur coupe ne dit rien des modénatures et encorbellements.
- À 10–50 pts/m², on se trouve au-dessus du seuil de difficulté d'environ 5 pts/m² signalé pour les méthodes pilotées par les données, ce qui rend City3D raisonnablement applicable, sous réserve du temps de calcul (MIP) sur grands bâtiments.
- La méthode d'Arefi (projection dans le plan perpendiculaire au faîtage) est la plus proche d'une coupe au sens architectural, utile comme ajustement de gabarit sur toits simples.

### Gaps
- Pas d'étude trouvée évaluant la qualité d'une coupe tirée d'un LoD2 par rapport à une coupe de référence.
- Détails des termes d'énergie de PolyFit non lus directement (seule l'existence du terme de complexité est confirmée dans ces notes via la pondération reprise par City3D).
- Aucune méthode en tranches verticales spécifiquement conçue pour l'ALS n'a été trouvée ; He et al. 2026 inclut des données ALS parmi d'autres, sans détail accessible.

## Génération par lots : séries le long d'un axe, sections transversales sur axe de voie, formats d'export

### Takeaway
Le calcul en série est trivial une fois un corridor par coupe défini, l'enjeu est d'éviter les lectures répétées et de conserver l'identité et la nature (mesuré/inféré) de chaque trait à l'export. GeoPackage convient pour la géométrie géoréférencée en XYZ, DXF et SVG pour le dessin (s, z) ; aucun format ne porte seul les deux repères.

### Cited Findings
- Coupes équidistantes perpendiculaires à un tracé vectoriel, boîtes de dimensions constantes, chaque coupe traitée indépendamment, géométrie exportée en vecteur : [David et al., 2009, texte lu](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/242_laserscanning09.pdf). Évoque en perspective l'appariement de profils et le filtrage de Kalman pour exploiter la continuité entre coupes successives.
- Démarche par axe (travail antérieur décrit par David et al., dont l'auteur n'a pas été relevé) : initialisation des axes depuis une base routière, analyse de coupes perpendiculaires par rapport à un modèle théorique de route, puis paramètres géométriques pris sur les coupes les mieux ajustées — [David et al., 2009](https://www.isprs.org/proceedings/XXXVIII/3-W8/papers/242_laserscanning09.pdf).
- Besoins types des gestionnaires routiers en sections à intervalles réguliers : largeurs de voie, accotements, talus, fossés — [ISPRS Annals II-3/W4, extrait seul](https://isprs-annals.copernicus.org/articles/II-3-W4/239/2015/isprsannals-II-3-W4-239-2015.pdf). L'aéroporté ne permet pas d'extraire les paramètres demandant une meilleure résolution (remarque d'un article sur mobile mapping : **transfert inverse, à titre de limite**) — [Remote Sensing 15(5) 1351, extrait seul](https://mdpi.com/2072-4292/15/5/1351).
- `LWPOLYLINE` DXF : entité plane, tous points dans l'OCS, en (x, y), avec `dxf.elevation` commune ; bulge et largeurs par sommet ; `vertices_in_wcs()` pour le monde ; entité unique, plus légère que le POLYLINE historique composé de sous-entités — [ezdxf LWPolyline](https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html) ; [tutoriel ezdxf](https://ezdxf.readthedocs.io/en/stable/tutorials/lwpolyline.html).
- `readers.copc` traite plusieurs polygones comme un multipolygone — [PDAL readers.copc](https://pdal.io/en/stable/stages/readers.copc.html).

### Inferences
**Génération.**

```
axe = polyligne ; pas Δ ; demi-largeur W ; épaisseur t
stations : s_k = k·Δ le long de l'axe
tangente τ_k = lissée sur ±une demi-longueur, pour éviter le bruit de l'axe
coupe_k = segment centré en P(s_k), direction τ_k tournée de 90°, longueur 2W
```

- Coupes sériées (axe droit) : stations équidistantes le long d'une direction, orientation constante, facilement empilables. Sections transversales (axe courbe) : l'orientation varie, l'espace inter-coupes se contracte à l'intérieur des courbes, et des coupes peuvent se croiser si W > rayon de courbure.
- Pas Δ et épaisseur t indépendants : Δ ≥ t pour éviter qu'un même point serve deux coupes ; autoriser Δ < t seulement pour une moyenne glissante documentée.
- Lecture : réunion des corridors en multipolygone, une seule passe, puis affectation par station. Plus économique qu'une lecture par coupe quand elles sont serrées ; passer en lectures séparées si Δ est grand devant t, pour éviter d'exécuter tout le nuage.
- Exploiter la continuité : médiane glissante sur 3 à 5 coupes voisines pour la position des murs (hypothèse d'objet extrudé) ; Kalman ou appariement de profils à titre de piste, comme David et al.

**Modèle de données et export.**
- *GeoPackage* : couche de lignes d'axe (2D, CRS projeté, attributs coupe_id, t, Δ, date, source) ; couche de traits en LineStringZ dans le CRS réel (x, y, z exacts, reconstruits par P = A + s·u) ; attributs : classe (sol, toit, mur, végétation), `statut` (mesuré, inféré_emprise, inféré_égout, comblé), nb_points, sigma, méthode. Stocker aussi le SVF et H/W par station dans une table de points.
- *DXF* : deux choix. Dessin à plat (s, z) en `LWPOLYLINE`, avec décalage par coupe pour une planche ; ou vertical dans l'espace via OCS de normale horizontale, ou POLYLINE 3D. Calques par classe × statut, tireté pour l'inféré, annotation d'échelle et de cote. L'exagération verticale doit être inscrite sur le dessin.
- *SVG* : (s, z) avec inversion de y, un groupe par couche et `data-*` pour coupe_id et statut. Bon format de publication ; à éviter pour de la mesure (unités sans CRS).
- Toujours exporter une table de métadonnées par coupe (densité observée, nombre de points, part inférée). Sans cela, un dessin propre masque la part d'interprétation.

**Recette synthétique à 10–50 pts/m².** Tranche t = max(0,25 m, 3/(ρ·b)), b = 0,25 m ; lecture COPC par polygone orienté en pleine résolution ; classes sol/bâti/végétation séparées ; TIN sol coupé pour le terrain ; enveloppe haute bâtie et RANSAC séquentiel ε = 0,1 m ; Douglas-Peucker ≥ 2σ ; `regularize_open_contour` (directions 0°/90°, déviation max 5 à 10°) ; murs selon la chaîne de décision (emprise puis échos puis égout) ; statut sur chaque trait. Non validée sur données réelles : à tester avant toute promesse de précision.

### Gaps
- Espacements et largeurs réellement pratiqués pour des sections transversales en aéroporté : aucune valeur normative trouvée.
- La spécification GeoPackage et le comportement SVG n'ont pas été consultés directement : les choix ci-dessus sont des propositions techniques.
- Aucun dépôt open source spécialisé dans la coupe aéroportée vers dessin vectoriel n'a été identifié dans cette passe ; seul l'outillage générique (PDAL, CGAL, Open3D, Shapely, ezdxf) est documenté.
