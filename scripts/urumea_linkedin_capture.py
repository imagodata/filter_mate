# Run by QGIS --code. The plugin itself is the unmodified dist 5.1.3 ZIP.
from pathlib import Path
exec(compile(Path('/w/scripts/site_videos.py').read_text(encoding='utf-8'), '/w/scripts/site_videos.py', 'exec'), globals())
from dataclasses import replace
from qgis.core import (QgsCoordinateReferenceSystem,QgsCoordinateTransform,QgsFillSymbol,QgsLineSymbol,
                       QgsRasterLayer,QgsGeometry,QgsVectorFileWriter)

WINDOW=(1920,1080)
DOCK_WIDTH=470
AREA=(-1.985,43.295,-1.948,43.324)
AREA_WKT='POLYGON((-1.985 43.295,-1.948 43.295,-1.948 43.324,-1.985 43.324,-1.985 43.295))'
BASE_COUNTS={}
REFERENCE_FILTERS={}
REQUESTS=[
 ('relief',"Ajoute le modèle de surface Copernicus à 30 m sur l'emprise visible de l'Urumea à Saint-Sébastien, en EPSG:32630. Nomme-le « Copernicus 30 m » et affiche-le en ombrage sous les vecteurs. Les couches OSM sont déjà chargées."),
 ('altitude',"Calcule la moyenne du DEM par emprise de bâtiment avec les statistiques zonales sur « Bâtiments ». Crée une couche « Bâtiments altitude » avec un champ alt_mean, conserve les NoData et colore-la par altitude moyenne. Il s'agit d'un modèle de surface, pas d'une hauteur de bâtiment. Masque la couche originale « Bâtiments »."),
 ('filtre',"Dans « Bâtiments altitude », garde alt_mean < 5 m à moins de 200 m de la couche « Urumea ». Filtre « Routes », « Ponts lignes » et « Ponts polygones » à moins de 300 m des bâtiments retenus, avec les distances en mètres. Garde ces filtres actifs, ne modifie pas les données et ne change pas le cadrage."),
 ('favori',"Enregistre l'état actuel des filtres du projet comme favori « Urumea — seuils illustratifs ». Réponds uniquement « Favori enregistré » lorsque le succès est confirmé."),
 ('reset',"Efface maintenant les filtres des couches du projet, sans supprimer les couches ni le favori. Nous allons comparer la carte complète avant de rejouer le favori."),
 ('rejeu',"Réapplique le favori « Urumea — seuils illustratifs ». Ne lance aucune autre opération de filtrage. Réponds uniquement « Favori rejoué » lorsque son application est confirmée."),
 ('export',"Exporte les couches vectorielles visibles et filtrées dans un seul GeoPackage « urumea_resultats » et le raster Copernicus dans un GeoTIFF séparé, avec les styles disponibles. Liste les fichiers réellement écrits. Ne prétends pas qu'un projet QGIS est embarqué dans le GeoPackage."),
]


def setup_visible():
    canvas=prepare_window()
    project=QgsProject.instance();project.clear()
    metric=QgsCoordinateReferenceSystem('EPSG:32630');project.setCrs(metric);canvas.setDestinationCrs(metric)
    for table,name,color,width in [
       ('routes','Routes','#77736b',0.24),
       ('batiments','Bâtiments','#c8a985',None),
       ('ponts_lignes','Ponts lignes','#b47a42',0.75),
       ('ponts_polygones','Ponts polygones','#b47a42',None),
       ('urumea','Urumea','#2185bd',1.75)]:
        vector=QgsVectorLayer('/w/data/urumea-ready.gpkg|layername='+table,name,'ogr')
        if not vector.isValid() or vector.featureCount()==0:raise RuntimeError('Invalid/empty source: '+name)
        if vector.geometryType()==2:
            symbol=QgsFillSymbol.createSimple({'color':color,'outline_color':'#8f7d66','outline_width':'0.08'})
        else:symbol=QgsLineSymbol.createSimple({'line_color':color,'line_width':str(width)})
        vector.setRenderer(QgsSingleSymbolRenderer(symbol));project.addMapLayer(vector)
        BASE_COUNTS[name]=vector.featureCount()
        project.layerTreeRoot().findLayer(vector.id()).setExpanded(False)
    bounds=QgsRectangle(*AREA)
    bounds=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),metric,project).transformBoundingBox(bounds)
    STATE['scene_rect']=bounds;STATE['boot_extent']=bounds
    # prepare_window suspends drawing while data are loaded. It must be re-enabled here.
    canvas.setExtent(bounds);canvas.setRenderFlag(True);canvas.refresh()
    log('visible baseline '+json.dumps(BASE_COUNTS,ensure_ascii=False))


def configure_agent():
    from filter_mate.adapters.agent.settings import load_settings,save_settings
    from qgis.core import QgsSettings
    chat=agent_chat();old=load_settings()
    if not QgsApplication.authManager().setMasterPassword('fm-video-take',True):raise RuntimeError('Recording wallet is locked')
    if not old.ready:raise RuntimeError('Agent settings not ready')
    save_settings(replace(old,autonomy='autonomous',memory=False,keep_request_history=False,tool_families=False,
       enabled_sources=('overpass_fr','copernicus_dem','photon'),
       tool_rules=json.dumps({'add_osm_features':'allow','add_elevation':'allow','run_algorithm':'allow','export_layers':'allow'})))
    QgsSettings().setValue('FilterMate/agent/setup_offered_version',chat.plugin_version())
    chat._settings_dialog=lambda:False;chat.open_settings=lambda:False
    chat._refresh_ready();chat.new_conversation()
    if hasattr(chat,'_on_posture_changed'):chat._on_posture_changed('act')
    install_demo_trace('urumea-linkedin')
    # Keep a running observation log alongside the real UI.
    previous=chat.on_tool_end
    def end(call,result):
        log('tool '+call.name+(' ERROR' if result.is_error else ' OK'))
        REC.event('tool',name=call.name,is_error=bool(result.is_error))
        value=previous(call,result)
        QTimer.singleShot(500,restore_view)
        return value
    chat.on_tool_end=end
    log('recording plugin '+chat.plugin_version()+' model='+old.model)


def restore_view():
    canvas=iface.mapCanvas()
    canvas.setRenderFlag(True)
    canvas.setExtent(STATE['scene_rect']);canvas.refresh()


def align_dock():
    iface.mainWindow().resizeDocks([dock()],[470],Qt.Orientation.Horizontal)
    sections=getattr(dock(),'_fm_sections',None)
    if sections is not None:
        try:sections.open_top('agent')
        except Exception:pass
    iface.mapCanvas().setRenderFlag(True)


def wait_agent(stage):
    seen=set();state={'ticks':0}
    def step():
        from filter_mate.ui.widgets.agent_thread import ConfirmCard
        state['ticks']+=1
        for card in agent_panel().thread.findChildren(ConfirmCard):
            if card.isVisible() and not card.done and id(card) not in seen:
                seen.add(id(card));REC.event('speed',factor=1.0)
                def answer(card=card):
                    box_=resolve(card.yes_button);REC.event('click',x=box_.center().x(),y=box_.center().y());card.yes_button.click()
                QTimer.singleShot(1800,answer)
                QTimer.singleShot(3000,lambda:REC.event('speed',factor=8.0))
        busy=agent_chat().chat_busy() or agent_panel()._working
        if state['ticks']%80==0:log('waiting '+stage)
        if not busy and state['ticks']>=3:
            log('completed '+stage)
            return False
        return True
    step.max_tries=2400
    return step


def exact_count(layer):
    count=layer.featureCount()
    if count<0:
        request=QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)
        request.setSubsetOfAttributes([])
        count=sum(1 for _ in layer.getFeatures(request))
    return count


def current_filters():
    return {layer.name():{'count':exact_count(layer),'subset':layer.subsetString()}
            for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer,QgsVectorLayer) and layer.subsetString().strip()}


def checkpoint(stage):
    def step():
        project=QgsProject.instance();canvas=iface.mapCanvas()
        if not canvas.renderFlag() or canvas.extent().isEmpty():raise RuntimeError('Map rendering is not active')
        restore_view()
        layers=[]
        for layer in project.mapLayers().values():
            item={'name':layer.name(),'valid':layer.isValid(),'crs':layer.crs().authid()}
            if isinstance(layer,QgsVectorLayer):item.update(count=exact_count(layer),subset=layer.subsetString(),fields=[f.name() for f in layer.fields()])
            layers.append(item)
        filters=current_filters()
        if stage=='relief' and not any(isinstance(layer,QgsRasterLayer) for layer in project.mapLayers().values()):
            raise RuntimeError('No elevation raster created')
        if stage=='filtre':
            if not filters:raise RuntimeError('No active filters created')
            REFERENCE_FILTERS.clear();REFERENCE_FILTERS.update(filters)
        if stage=='reset' and filters:raise RuntimeError('Filters were not cleared')
        comparison=None
        if stage=='rejeu':
            comparison={name:{'before':values['count'],'after':filters.get(name,{}).get('count')}
                        for name,values in REFERENCE_FILTERS.items()}
            if any(v['before']!=v['after'] for v in comparison.values()):
                raise RuntimeError('Favorite did not restore all counts: '+json.dumps(comparison,ensure_ascii=False))
        observation={'stage':stage,'layers':layers,'filters':filters,'replay_comparison':comparison,'render_flag':canvas.renderFlag(),
                     'thread':agent_panel().thread.toPlainText()}
        Path(OUT,f'{stage}-observed.json').write_text(json.dumps(observation,ensure_ascii=False,indent=2)+'\n')
        REC.event('mark',name='done:'+stage)
        log('checkpoint '+stage+' '+json.dumps({n:v['count'] for n,v in filters.items()},ensure_ascii=False))
    return step


def focus_filtered_buildings():
    for vector in QgsProject.instance().mapLayers().values():
        if isinstance(vector,QgsVectorLayer) and vector.subsetString() and ('altitude' in vector.name().lower() or 'alt_mean' in vector.fields().names()):
            iface.setActiveLayer(vector)
            return


def ask(stage,text):
    steps=[(0,lambda:STATE.update(demo_request=stage)),(0,lambda:REC.event('mark',name='ask:'+stage)),(400,agent_open)]
    if stage=='favori':steps += [(0,focus_filtered_buildings)]
    steps += [(0,cam('full',dur=0.8))]
    steps += act(lambda:agent_panel().input,lambda:agent_panel().input.setFocus(),lead=350,after=300)
    steps += type_into(lambda:agent_panel().input,text,per_char=14)
    steps += act(lambda:agent_panel().send_button,lambda:agent_panel().send_button.click(),lead=350,after=400)
    steps += [(300,speed(8.0)),(1400,wait_agent(stage)),(200,speed(1.0)),(600,wait_idle()),(0,checkpoint(stage)),
              (700,wait_idle()),(0,cam('canvas',dur=1.0)),hold(2600),still('result-'+stage),hold(2000),
              (0,cam('full',dur=0.8)),hold(1300)]
    return steps


def collect_deliverables():
    import shutil
    root=Path(QgsApplication.qgisSettingsDirPath())/'FilterMate/exports'
    destination=Path(OUT)/'exports';destination.mkdir(exist_ok=True)
    if root.exists():
        for path in root.rglob('*'):
            if path.is_file():
                target=destination/path.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    QgsProject.instance().setFileName(str(Path(OUT)/'urumea-session.qgz'))
    QgsProject.instance().write()
    log('collected exports '+str([str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()]))

STEPS=[(1000,setup_visible),(3000,open_plugin),(8000,size_dock),(1500,wait_idle()),(600,configure_agent),
       (400,agent_open),(800,align_dock),(800,wait_idle()),(500,rec_start),
       title('FilterMate 5.1.3 · Urumea'),(0,cam('full',dur=0)),hold(3500),still('baseline')]
for stage,request in REQUESTS:STEPS+=ask(stage,request)
STEPS += [(0,collect_deliverables),hold(1500),(0,stop_recording),(500,quit_when_idle)]
log('Urumea LinkedIn overrides scene with '+str(len(STEPS))+' steps')

# Keep a persistent Qt timer for the capture state machine, including waits between requests.
# The base's initial singleShot calls step 0, then hands control to this runner.
RUN_CLOCK={'index':None,'tries':0,'due':0.0,'last_progress':time.monotonic()}
RUN_TIMER=QTimer();RUN_TIMER.setInterval(10)

def run_steps(i=0,tries=0):
    if i>=len(STEPS):
        RUN_TIMER.stop();return
    RUN_CLOCK.update(index=i,tries=tries,due=time.monotonic()+STEPS[i][0]/1000,last_progress=time.monotonic())
    RUN_TIMER.start()

def tick_steps():
    if RUN_CLOCK['index'] is None or time.monotonic()<RUN_CLOCK['due']:return
    index=RUN_CLOCK['index'];delay,fn=STEPS[index];RUN['at']=index
    if RUN_CLOCK['tries']==0:log(f'--- stable step {index} {getattr(fn,"__name__",fn)}')
    try:again=fn() is True
    except Exception:
        RUN_TIMER.stop();capture_failed(traceback.format_exc());return
    if again:
        RUN_CLOCK['tries']+=1
        if RUN_CLOCK['tries']>getattr(fn,'max_tries',400):
            RUN_TIMER.stop();capture_failed('timeout at stable step '+str(index));return
        RUN_CLOCK['due']=time.monotonic()+0.25
    else:run_steps(index+1)
RUN_TIMER.timeout.connect(tick_steps)

import signal

def interrupted(signum,frame):
    RUN_TIMER.stop();log('EXTERNAL SIGNAL '+str(signum))
    STATE.update(capture_status='interrupted',capture_error='signal '+str(signum))
    if REC.running:stop_recording()
    QgsApplication.instance().quit()
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
