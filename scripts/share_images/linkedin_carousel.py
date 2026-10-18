import sys
from pathlib import Path
out = Path(sys.argv[1])
CSS = '''<style>
@page{size:1080px 1350px;margin:0}
html,body{margin:0;background:#f3f4ef;color:#16232b;font-family:Barlow,'Segoe UI',system-ui,sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{position:relative;box-sizing:border-box;width:1080px;height:1350px;padding:56px;border:16px solid #16232b;overflow:hidden;page-break-after:always;background:#f3f4ef}
.page:after{content:"";position:absolute;inset:8px;border:1px solid #16232b;pointer-events:none}
.kicker{display:flex;align-items:center;gap:12px;font-weight:600;font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:#3f7a22}
.kicker span{width:13px;height:13px;background:#ffd83d;border:2px solid #16232b}
.num{position:absolute;top:56px;right:56px;font:700 44px/1 'Barlow Condensed',sans-serif;color:#1f66b8}
h1{margin:16px 0 8px;font:700 76px/.98 'Barlow Condensed','Arial Narrow',sans-serif;letter-spacing:-.01em}
h1 em{font-style:normal;color:#1f66b8}
h2{margin:18px 0 10px;font:700 46px/1.02 'Barlow Condensed',sans-serif}
.lead{margin:0;font-size:24px;line-height:1.35;color:#4a5a63;max-width:900px}
.shot{display:block;width:968px;height:572px;object-fit:cover;object-position:right top;border:2px solid #16232b;margin-top:22px;background:#fff}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}
.box{padding:20px 22px;border:1.5px solid #cfd3c8;background:#fff;min-height:250px;box-sizing:border-box}
.box b{display:block;font:600 14px/1.3 Barlow,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#4a5a63;margin-bottom:8px}
.box p{margin:0;font-size:23px;line-height:1.4}
.box code{font-size:18px}
.box.result{background:#e4eef9;border:2.5px solid #1f66b8}
.box.result p{font:600 27px/1.35 Barlow,sans-serif;color:#16232b}
.dir{display:inline-block;margin-top:14px;padding:6px 12px;background:#ffd83d;border:2px solid #16232b;font:600 18px/1.2 Barlow,sans-serif}
.list{margin:34px 0 0;padding:0;list-style:none}
.list li{display:grid;grid-template-columns:70px 1fr;align-items:baseline;gap:14px;padding:14px 0;border-top:1.5px solid #cfd3c8;font-size:26px;line-height:1.3}
.list li i{font:700 40px/1 'Barlow Condensed',sans-serif;color:#1f66b8;font-style:normal}
.list li span{display:block;font-size:18px;color:#4a5a63;margin-top:2px}
.foot{position:absolute;left:56px;right:56px;bottom:56px;display:flex;justify-content:space-between;align-items:flex-end;font-size:17px;color:#4a5a63}
.foot strong{display:block;font:700 30px/1 'Barlow Condensed',sans-serif;color:#16232b;margin-bottom:6px}
.big{font:600 30px/1.3 Barlow,sans-serif;margin:26px 0 0}
.news{margin-top:30px;display:grid;gap:14px}
.news div{padding:16px 18px;background:#fff8d6;border:1.5px solid #e0b400}
.news b{display:block;font:600 26px/1.15 'Barlow Condensed',sans-serif}
.news span{display:block;margin-top:4px;font-size:19px;line-height:1.3;color:#4a5a63}
</style>'''
HEAD = '''<!DOCTYPE html><html lang="__LANG__"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">''' + CSS + '</head><body>'
FR = dict(lang='fr', kicker='FilterMate 5 pour QGIS', title='Cinq questions métier.<br><em>Un seul panneau.</em>',
    lead='Vecteur, raster et nuage de points LiDAR, filtrés les uns par les autres dans QGIS, sans SQL ni script. Cinq scénarios enregistrés sur Estavar (Pyrénées-Orientales) : BD TOPO, cadastre, MNT 1 m, ortho IRC 25 cm, LiDAR HD.',
    do='Ce qu’on fait', get='Ce qu’on obtient', foot='EXPLORING choisit. FILTERING relie. EXPORTING écrit.', tail='Libre et gratuit · QGIS 3.22 à 4.2',
    last_title='Et depuis cette semaine', last_lead='Trois nouveautés fusionnées sur la branche principale, en route vers la 5.0.1.',
    news=[('Pipette « objet cliqué »', 'la tache sous le clic (piscine, toit, parcelle), pas tous les pixels semblables du raster'), ('Entités similaires', 'un clic sur une entité sélectionne toutes celles qui ont la même valeur'), ('Serveur MCP', 'le filtrage piloté depuis un assistant IA, un outil par point d’entrée REST')],
    install='imagodata.github.io/filter_mate · dépôt officiel des extensions QGIS',
    scenarios=[
     ('Les bâtiments le long des grands axes', 'vecteur → vecteur', 'Source : les tronçons de route avec <code>"importance" = \'4\'</code>, 15 tronçons. Prédicat Intersect, tampon de 50 m. Cibles : bâtiments et parcelles.', '39 bâtiments et 11 parcelles, filtrés sur place, exportables en GeoPackage.', 'ln_1_routes_batiments.jpg', 'Les bâtiments à moins de 50 m des routes principales'),
     ('Le dossier de relevé autour de l’église', 'vecteur → raster + nuage de points', 'Source : l’église (sélection simple), tampon de 50 m. Cibles : le MNT à 1 m et la dalle LiDAR HD.', 'Un MNT découpé (VRT) et un nuage dérivé (COPC) qui gardent leur style ; Annuler rend la source.', 'ln_2_eglise_mnt_lidar.jpg', 'Le MNT et le LiDAR découpés à 50 m de l’église'),
     ('Les parcelles en pente', 'raster → vecteur', 'Source : le MNT, grandeur « pente (%) » calculée à la volée, seuil ≥ 20 %. Cible : parcelles, couverture minimale 50 %.', '2 parcelles sur 42 ont plus de la moitié de leur surface en pente.', 'ln_3_pente_parcelles.jpg', 'Les parcelles à plus de 20 % de pente'),
     ('Les parcelles végétalisées', 'raster → vecteur', 'Source : l’ortho IRC, rôles de bandes PIR-R-V, préréglage NDVI végétation (> 0,3). Cible : parcelles, couverture minimale 50 %.', '7 parcelles majoritairement végétalisées ; la sélection est lue à pleine résolution, par tuiles.', 'ln_4_ndvi_parcelles.jpg', 'Les parcelles où le NDVI dépasse 0,3'),
     ('Les routes à élaguer', 'nuage de points → vecteur', 'Source : le LiDAR HD, classe 5 (végétation haute). Cible : tronçons de route, tampon de 3 m autour de l’emprise des points.', '100 tronçons sur 131 touchent de la végétation haute à moins de 3 m.', 'ln_5_vegetation_routes.jpg', 'Les tronçons à moins de 3 m de végétation haute')])
EN = dict(lang='en', kicker='FilterMate 5 for QGIS', title='Five business questions.<br><em>One panel.</em>',
    lead='Vector, raster and LiDAR point cloud layers filtered by one another in QGIS, with no SQL and no script. Five scenarios recorded on Estavar (French Pyrenees): BD TOPO, cadastre, 1 m DTM, 25 cm CIR orthophoto, LiDAR HD.',
    do='What you do', get='What you get', foot='EXPLORING selects. FILTERING relates. EXPORTING writes.', tail='Free and open source · QGIS 3.22 to 4.2',
    last_title='New this week', last_lead='Three features merged on the main branch, on their way to 5.0.1.',
    news=[('Clicked-object pipette', 'the patch under the click (pool, roof, field), not every similar pixel of the raster'), ('Similar features', 'one click on a feature selects every feature with the same value'), ('MCP server', 'the filtering driven from an AI assistant, one tool per REST endpoint')],
    install='imagodata.github.io/filter_mate · official QGIS plugin repository',
    scenarios=[
     ('Buildings along the main roads', 'vector → vector', 'Source: the road segments with <code>"importance" = \'4\'</code>, 15 segments. Intersect predicate, 50 m buffer. Targets: buildings and parcels.', '39 buildings and 11 parcels, filtered in place, ready to export as GeoPackage.', 'ln_1_routes_batiments.jpg', 'Buildings within 50 m of the main roads'),
     ('The survey package around the church', 'vector → raster + point cloud', 'Source: the church (single selection), 50 m buffer. Targets: the 1 m DTM and the LiDAR HD tile.', 'A clipped DTM (VRT) and a derived cloud (COPC) that keep their style; Undo brings the source back.', 'ln_2_eglise_mnt_lidar.jpg', 'The DTM and the LiDAR clipped 50 m around the church'),
     ('Parcels on a slope', 'raster → vector', 'Source: the DTM, "slope (%)" computed on the fly, threshold ≥ 20 %. Target: parcels, minimum coverage 50 %.', '2 parcels out of 42 have more than half of their area on the slope.', 'ln_3_pente_parcelles.jpg', 'Parcels with a slope above 20 %'),
     ('Vegetated parcels', 'raster → vector', 'Source: the CIR orthophoto, band roles NIR-R-G, NDVI vegetation preset (> 0.3). Target: parcels, minimum coverage 50 %.', '7 mostly vegetated parcels; the selection is read at full resolution, tile by tile.', 'ln_4_ndvi_parcelles.jpg', 'Parcels where NDVI exceeds 0.3'),
     ('Roads to prune', 'point cloud → vector', 'Source: the LiDAR HD, class 5 (high vegetation). Target: road segments, 3 m buffer around the footprint of the points.', '100 segments out of 131 touch high vegetation within 3 m.', 'ln_5_vegetation_routes.jpg', 'Road segments within 3 m of high vegetation')])
for name, d in (('carousel.fr', FR), ('carousel', EN)):
    h = HEAD.replace('__LANG__', d['lang'])
    items = ''.join(f'<li><i>{i+1}</i><div>{s[0]}<span>{s[1]}</span></div></li>' for i, s in enumerate(d['scenarios']))
    h += f'<div class="page"><div class="kicker"><span></span>{d["kicker"]}</div><h1>{d["title"]}</h1><p class="lead">{d["lead"]}</p><ul class="list">{items}</ul><div class="foot"><div><strong>{d["foot"]}</strong>{d["install"]}</div><div>{d["tail"]}</div></div></div>'
    for i, (title, direction, do, get, img, alt) in enumerate(d['scenarios']):
        h += f'<div class="page"><div class="kicker"><span></span>{d["kicker"]}</div><div class="num">{i+1} / 5</div><h2>{title}</h2><span class="dir">{direction}</span><img class="shot" src="{img}" alt="{alt}"><div class="cols"><div class="box"><b>{d["do"]}</b><p>{do}</p></div><div class="box result"><b>{d["get"]}</b><p>{get}</p></div></div><div class="foot"><div><strong>{d["foot"]}</strong>{d["install"]}</div><div>{d["tail"]}</div></div></div>'
    news = ''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in d['news'])
    h += f'<div class="page"><div class="kicker"><span></span>{d["kicker"]}</div><h1>{d["last_title"]}</h1><p class="lead">{d["last_lead"]}</p><div class="news">{news}</div><p class="big">{d["foot"]}</p><div class="foot"><div><strong>{d["install"]}</strong></div><div>{d["tail"]}</div></div></div>'
    h += '</body></html>'
    (out / f'{name}.html').write_text(h, encoding='utf-8')
print('html ok')
