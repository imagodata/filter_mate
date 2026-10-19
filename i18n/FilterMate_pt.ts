<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pt_BR" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>Importar do Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Publicar no Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>Publicar (nenhum favorito guardado)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>Publicação rápida no repositório predefinido</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>Gerir repositórios do Resource Sharing...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Filtros corrompidos removidos de {0} camada(s). Por favor, reaplique os seus filtros.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Projeto vazio detetado. Adicione camadas vetoriais para ativar o plugin.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>Não é possível aceder à base de dados do FilterMate. Verifique as permissões do diretório do projeto.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>Erro durante a verificação da base de dados: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Carregamento de camadas falhou. Use F5 para forçar o recarregamento.</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: este serviço web não tem um campo de chave única (chave declarada, id, gml_id, cleabs, objectid...), pelo que as entidades selecionadas não podem ser listadas para o servidor.</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: esta camada não tem um campo de chave única e os identificadores das suas entidades não podem ser listados no respetivo filtro (uma camada virtual precisa de uma coluna de id única, o seu uid).</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: {1} entidades selecionadas, mais do que as {2} enviadas para um serviço web. Reduza a seleção ou utilize um filtro por atributos.</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>Ficheiro remoto: cada leitura passa pela rede. O FilterMate não conta as suas entidades no thread principal.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>Serviço remoto: o filtro é enviado ao servidor quando este o consegue traduzir. O FilterMate não conta as suas entidades no thread principal.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>Um filtro por lista de entidades está limitado a {0} entidades.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="123"/>
        <source>Remote</source>
        <translation>Remoto</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="185"/>
        <source>Select Backend:</source>
        <translation>Selecionar backend:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>Automático (Predefinido)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Seleção automática ótima para todas as camadas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>Forçar {0} para todas as camadas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>Clicar para recarregar as camadas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>Clicar para alterar o backend</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>Testar os alvos de linhas e polígonos selecionados pelos seus centroides (ponto na superfície): mais rápido em geometrias grandes. Cada alvo tem o seu próprio quadrado na lista</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>Os centroides aplicam-se aos alvos de linhas e polígonos: selecione um na lista de camadas a filtrar</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Erro ao cancelar as alterações: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>Erro de propriedade: {0}</translation>
    </message>
</context>
<context>
    <name>CoverageDockExtras</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="303"/>
        <source>1 band</source>
        <translation>1 banda</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="304"/>
        <source>{0} bands</source>
        <translation>{0} bandas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="305"/>
        <source>{0} points</source>
        <translation>{0} pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>Geometria de origem: os píxeis selecionados, vetorizados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="792"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>Geometria de origem: a área ocupada pelos pontos mantidos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="739"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation>Geometria de origem: as entidades selecionadas em EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">Valor sob o cursor: acompanhar o valor do píxel da banda atual ao percorrer o mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">Estatísticas de um retângulo: arrastar no mapa para ler o mínimo, o máximo e a média da banda atual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>Perfil de elevação: abrir o perfil de elevação do QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>Vista 3D: abrir uma nova vista de mapa 3D do QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">nenhuma feição</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} feição(ões)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">todos os píxeis</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} classe(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>expressão</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} feições</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Vector</source>
        <translation>Vetorial</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Raster</source>
        <translation>Raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Point cloud</source>
        <translation>Nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="795"/>
        <source>Kept points</source>
        <translation>Pontos mantidos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Selection → source geometry</source>
        <translation>Seleção → geometria de origem</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>Ligar o intervalo ao estilo: as cores da camada estendem-se sobre o intervalo escolhido</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Conta-gotas de classes: clique no mapa e a classe dos pontos desenhados nesse local é marcada. Ctrl+clique adiciona outra</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>Valor sob o cursor: acompanhar o valor do píxel (ou o declive, a orientação... a que o intervalo se aplica) ao percorrer o mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>Estatísticas de um retângulo: arrastar no mapa para ler o mínimo, o máximo e a média da banda atual (ou do declive, da orientação... a que o intervalo se aplica)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>A ligação ao estilo acompanha os valores dos píxeis: indisponível enquanto o intervalo se aplica a um declive, orientação, sombreamento ou rugosidade</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="920"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>Conta-gotas de classes: esta nuvem de pontos não tem o atributo Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1526"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>O estilo não pode acompanhar o intervalo: requer um estilo de banda única em cinzento ou pseudocor sobre a banda do painel</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>Conta-gotas: clique no mapa e os píxeis parecidos com o que clicou são selecionados (uma cor numa imagem, um valor num MDT ou num índice, uma classe num raster classificado, com a tolerância do painel). Ctrl+clique adiciona outro</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>nenhuma feição selecionada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>toda a camada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>sem restrição</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>expressão raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>todos os pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} objeto(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>apresentados como a classe completa na sua caixa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>Detetor de objetos: clique no mapa e é selecionada a mancha de píxeis semelhantes ao clicado (uma piscina, um telhado, um campo, com a tolerância do painel), e não todos os píxeis da sua cor. Ctrl+clique adiciona outro objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>Objetos semelhantes: clique num objeto e são selecionados todos os objetos do raster semelhantes a ele (as manchas desses píxeis cuja área está dentro das proporções do painel). Ctrl+clique adiciona outro objeto de referência</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>Detetor de objetos: clique no mapa e o objeto sob o clique é selecionado (o grupo de pontos da sua classe: um edifício, uma árvore), e não toda a classe; ou todos os objetos da nuvem semelhantes a ele (clique direito no botão para o alvo). Ctrl+clique adiciona outro objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>Conta-gotas de valor: clique no mapa e é escrita uma condição sobre o atributo escolhido em ATRIBUTOS (Z, intensidade...), em torno do valor do ponto nesse local, com a tolerância do painel. Ctrl+clique adiciona outra condição (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>Zona: desenhe um retângulo, um polígono, uma forma à mão livre ou um círculo no mapa (clique direito no botão para a forma); a sua caixa X / Y vai para ATRIBUTOS, a própria forma recorta os alvos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>Mais ferramentas: o valor sob o cursor, as estatísticas de um retângulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>Entidades semelhantes: clique numa entidade e são selecionadas todas as entidades da camada com o mesmo valor do campo do grupo (a expressão de visualização da seleção simples / múltipla). Ctrl+clique adiciona outro valor</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>Mais ferramentas: as ferramentas de seleção do QGIS (retângulo, polígono, mão livre, raio), selecionar por expressão, inverter ou limpar a seleção, a tabela de atributos da seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>Mais ferramentas: o perfil de elevação e a vista 3D do QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>Só está disponível a seleção por cor: as cores renderizadas dependem do estilo e da escala.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>A ligação de estilo segue o grupo INTERVALO DE VALORES: torne-o primeiro ativo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="794"/>
        <source>Current filter: {0}</source>
        <translation>Filtro atual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="830"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>As cores renderizadas dependem do estilo e da escala.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="929"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>Detetor de objetos: esta nuvem de pontos não tem o atributo Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="978"/>
        <source>Object detector</source>
        <translation>Detetor de objetos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Clicked object</source>
        <translation>Objeto clicado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Similar objects</source>
        <translation>Objetos semelhantes</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1085"/>
        <source>Zone shape</source>
        <translation>Forma da zona</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Rectangle</source>
        <translation>Retângulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Polygon</source>
        <translation>Polígono</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Freehand</source>
        <translation>Mão livre</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Radius</source>
        <translation>Raio</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1134"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>A ligação segue as seleções simples e múltipla: torne primeiro ativa uma delas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1257"/>
        <source>Select on the map</source>
        <translation>Selecionar no mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Select by expression…</source>
        <translation>Selecionar por expressão…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Invert the selection</source>
        <translation>Inverter a seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Clear the selection</source>
        <translation>Limpar a seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1272"/>
        <source>Attribute table of the selection</source>
        <translation>Tabela de atributos da seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Value under the cursor</source>
        <translation>Valor sob o cursor</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1315"/>
        <source>Statistics of a rectangle</source>
        <translation>Estatísticas de um retângulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>Elevation profile</source>
        <translation>Perfil de elevação</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>3D view</source>
        <translation>Vista 3D</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1688"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>Esta nuvem de pontos não tem atributo X / Y por onde filtrar</translation>
    </message>
</context>
<context>
    <name>CoverageModeController</name>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="365"/>
        <source>Restoring the filter of {0} raster / point cloud layer(s)…</source>
        <translation>A restaurar o filtro de {0} camada(s) raster / nuvem de pontos…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>cob. ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>Proporção mínima de um alvo poligonal dentro da geometria de origem (0 = qualquer sobreposição). Utilizada quando a origem é um raster ou uma nuvem de pontos.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>Raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>Nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>Camada {0}: seleção em EXPLORING, relação em FILTERING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">Seletor de píxeis: clique no mapa para ler o valor de cada banda (Ctrl+clique alarga o intervalo)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>Ampliar para a camada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">Pré-visualização: ocultar os píxeis fora da seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>Não utilizado para camadas raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>Repor a seleção do raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">Identificar pontos no mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>Pré-visualização em direto: mostrar apenas os pontos mantidos pela seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>Não utilizado para camadas de nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>Repor os critérios da nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>Expressão da calculadora raster inválida</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>O PDAL não foi encontrado: a altura acima de um MDT requer o executável pdal</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3148"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>Uma tarefa do FilterMate ainda está em execução: aguarde que termine</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>A tarefa do FilterMate falhou: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>Selecione primeiro os píxeis: um intervalo de valores, classes ou uma expressão raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>Raster filtrado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>A expressão da nuvem de pontos foi rejeitada: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>Selecione primeiro os pontos: classes, intervalos de atributos ou uma expressão</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>Nuvem de pontos filtrada: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3253"/>
        <source>Filter not applied: {0}</source>
        <translation>Filtro não aplicado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3110"/>
        <source>canceled</source>
        <translation>cancelado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>{0} alvo(s) filtrado(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2820"/>
        <source>{0} failed: {1}</source>
        <translation>{0} falhou: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2833"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: a filtrar a partir de '{0}'…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2930"/>
        <source>Changed since, left as is: {0}</source>
        <translation>Alterado entretanto, deixado como está: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2936"/>
        <source>{0} layer(s) restored</source>
        <translation>{0} camada(s) restaurada(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2970"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>'{0}' não exportado: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2984"/>
        <source>Exported: {0}</source>
        <translation>Exportado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2986"/>
        <source>Export failed: {0}</source>
        <translation>A exportação falhou: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2993"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>A exportar {0} camada(s)…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2999"/>
        <source>Export folder</source>
        <translation>Pasta de exportação</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3081"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>Alvos raster / nuvem de pontos ignorados: nenhuma entidade de origem selecionada em EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3110"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>Alvos raster / nuvem de pontos não filtrados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3112"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>{0} alvo(s) raster / nuvem de pontos filtrado(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3230"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>Escolha o raster MDT utilizado para a altura acima do solo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3241"/>
        <source>Height above ground not computed: {0}</source>
        <translation>Altura acima do solo não calculada: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3262"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>A calcular a altura acima de '{0}' com o PDAL…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>A cache do FilterMate ocupa {0} GB, acima do seu limite de {1} GB: remova o filtro das camadas raster / nuvem de pontos de que já não precisa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>O PDAL {0} é muito antigo: a altura acima de um MDT requer o PDAL 2.4 ou mais recente</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>Não foi possível executar o PDAL, a altura acima de um MDT não está disponível: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">Seletor de píxeis: clique no mapa para ler o valor de cada banda, e o declive, a orientação... quando o intervalo se aplica a um deles (Ctrl+clique alarga o intervalo)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>Ampliar para os píxeis selecionados (para a camada se nada estiver selecionado)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>Pré-visualização: ocultar os píxeis fora da seleção (um véu branco para um declive, orientação...)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>A pré-visualização de um declive ou de uma orientação requer o mapa no SRC do raster ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>só é possível escolher os pontos desenhados no mapa: desative a pré-visualização para escolher uma classe que ela oculta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>Nenhum ponto classificado sob o clique</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>A classe {0} já está marcada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>A classe {0} não está na lista de classes da camada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>Não utilizado em camadas raster: o conta-gotas lê as bandas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Conta-gotas de classe: clique no mapa e é marcada a classe dos pontos desenhados aí. Ctrl+clique adiciona outra</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>A pré-visualização e as estatísticas usam uma amostra local limitada da extensão visível; a filtragem lê a origem.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>A preparar um instantâneo de cores limitado da extensão visível…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>Não foi possível preparar o instantâneo de cores. Experimente uma extensão visível mais pequena.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>A seleção por cor aplica-se à extensão visível capturada.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>Falha na amostragem do raster. Experimente uma extensão visível mais pequena.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>Não foi possível calcular a pré-visualização do raster amostrado.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>A pré-visualização de uma cor ou de uma expressão requer o mapa no SRC do raster ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>Nenhum ponto desenhado sob o clique</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>Este ponto não tem {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>{0} não pode ser usado numa condição</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>Objeto não lido: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>Demasiados pontos à volta do clique: não foi possível ler o objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>Nenhum ponto da classe {0} sob o clique: clique no próprio objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>Objetos semelhantes não lidos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>Nenhum objeto semelhante dentro das proporções de área: alargue-as</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>A preparar uma amostra para a nova extensão visível. Clique novamente quando estiver pronta.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>A amostra local do raster ainda está a ser preparada. Tente novamente quando estiver pronta.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>Prepare um instantâneo de cores antes de filtrar esta camada renderizada.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>{0} alvo(s) raster reamostrado(s) para o limite de píxeis configurado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2844"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>seleção por cor limitada à extensão capturada; as cores dependem do estilo e da escala</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2846"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>origem raster reamostrada para {0} células dentro do limite de píxeis</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2848"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>seleção raster lida a cada {0} píxeis: acima do limite de píxeis das definições</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>seleção raster densa suavizada para manter leve o seu contorno</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2898"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0} esvaziada(s), nada corresponde à seleção: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2882"/>
        <source>failed</source>
        <translation>falhou</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="234"/>
        <source>Database file does not exist: {0}</source>
        <translation>O ficheiro da base de dados não existe: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Falha ao conectar à base de dados {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Não foi possível criar o diretório da base de dados {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Falha ao criar o ficheiro da base de dados {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>Não é possível inicializar a base de dados do FilterMate: conexão falhada</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Erro crítico na conexão à base de dados: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>Erro durante a inicialização da base de dados: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>O ficheiro de base de dados não existe: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Falha ao ligar à base de dados {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Módulo QGIS Processing indisponível para criar o índice espacial</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Não é possível criar o índice espacial: camada inválida ou fonte não encontrada.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>Camadas PostgreSQL detetadas mas psycopg2 não está instalado. A utilizar o backend Spatialite local. Para melhor desempenho com grandes conjuntos de dados, instale psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2239"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>{0} entidades selecionadas, mais do que as {1} que podem ser enviadas para um serviço web: reduza a seleção ou utilize um filtro por atributos.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Guardar a camada num ficheiro</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Selecione uma pasta para exportar as camadas</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>Guardar os dados exportados num ficheiro ZIP</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0} camada(s)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> em {0} grupo(s)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} sem grupo</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>Destino: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Nenhum grupo detetado – todas as camadas estão no nível raiz</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="154"/>
        <source>Annuler</source>
        <translation>Cancelar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="160"/>
        <source>Exporter</source>
        <translation>Exportar</translation>
    </message>
</context>
<context>
    <name>ExtensionRegistry</name>
    <message>
        <location filename="../extensions/registry.py" line="398"/>
        <source>install the QGIS plugin {0}</source>
        <translation>instale o complemento do QGIS {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>instale {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>A extensão {0} está desativada porque falta {1}: {2} e reinicie o QGIS.</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">Sem filtro</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>Nenhum filtro ativo para guardar.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>Adicionar favorito</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>Nome do favorito:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Favorito '{0}' adicionado com sucesso</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="511"/>
        <source>Export Favorites</source>
        <translation>Exportar favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="535"/>
        <source>Exported {0} favorites</source>
        <translation>{0} favoritos exportados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="537"/>
        <source>Failed to export favorites</source>
        <translation>Falha ao exportar favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Import Favorites</source>
        <translation>Importar favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Fundir com os favoritos existentes?

Sim = Adicionar aos existentes
Não = Substituir todos os existentes</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>{0} favoritos importados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>Nenhum favorito importado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Gestor de favoritos não inicializado. Por favor, reinicie o FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>Diálogo do gestor de favoritos não disponível</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>Erro: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">Utilizado {0} vezes</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">Adicionar filtro atual aos favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">Adicionar filtro (sem filtro ativo)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">Gerir favoritos...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation type="obsolete">Exportar...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation type="obsolete">Importar...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation type="obsolete">Favoritos globais</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">Copiar para globais...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── Favoritos globais disponíveis ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(Sem favoritos globais)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">Manutenção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">Guardar no projeto (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">Restaurar do projeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">Limpar projetos órfãos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">Estatísticas da base de dados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">Nome inválido</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>O nome do favorito não pode estar vazio.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>Nome duplicado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Já existe um favorito com o nome '{0}'.
Deseja substituí-lo?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>Favorito copiado para favoritos globais</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>Falha ao copiar para favoritos globais</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">Favoritos globais</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0} favorito(s) global(ais) disponível(eis).

Os favoritos globais são partilhados entre todos os projetos.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>{0} favorito(s) guardado(s) no ficheiro do projeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>Falha ao guardar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>{0} favorito(s) restaurado(s) do ficheiro do projeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>Nenhum favorito para restaurar encontrado no projeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0} projeto(s) órfão(s) limpo(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>Nenhum projeto órfão para limpar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>Estatísticas da base de dados FilterMate

Total de favoritos: {0}
   Projeto: {1}
   Órfãos: {2}
   Globais: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>Projetos principais por favoritos:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>Estatísticas do FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Gestor de favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Ainda não há favoritos guardados.

Aplique um filtro a uma camada, clique no indicador ★ e escolha «Adicionar filtro atual aos favoritos» para guardar o seu primeiro favorito.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">Importar de Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">Publicar no Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">Publicar (sem favoritos guardados)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>A pasta de configuração do FilterMate ainda não foi inicializada — abra primeiro um projeto QGIS com o FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">A extensão Resource Sharing não está ativa. Ative 'favorites_sharing' nas definições do FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">O serviço de favoritos partilhados não está disponível.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">Falha do seletor de favoritos partilhados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">Ainda não tem favoritos para publicar. Guarde primeiro um filtro através do menu ★.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">Falha ao abrir a janela de publicação: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>Os favoritos ainda não estão prontos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>Não foi possível remover '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>Ainda não há favoritos guardados — aplique um filtro e clique no indicador ★ para guardar o primeiro.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>Não foi possível abrir o gestor de favoritos. Detalhes em filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>Não foi possível substituir '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>Não foi possível guardar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>Não foi possível importar o favorito global: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>Não foi possível copiar para global: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>Não foi possível guardar os favoritos no ficheiro do projeto: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>Não foi possível limpar os projetos órfãos. Detalhes em filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>As estatísticas da base de dados não estão disponíveis. Detalhes em filtermate.log.</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="204"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Gestor de favoritos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1165"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Favoritos guardados ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="266"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Pesquisar por nome, expressão, etiquetas ou descrição...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>Geral</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>Expressão</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>Remoto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>Nome do favorito</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>Nome:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Descrição (gerada automaticamente, editável)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>Descrição:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Introduza etiquetas separadas por vírgulas (ex.: urbano, população, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>As etiquetas ajudam a organizar e pesquisar favoritos.
Separe várias etiquetas com vírgulas.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>Etiquetas:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>Camada de origem:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>Fornecedor:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>Utilizado:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>Criado:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Expressão da camada de origem:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>Expressão de filtro para a camada de origem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Camadas remotas filtradas:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>Camada</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>Elementos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Sem camadas remotas neste favorito&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>Aplicar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Aplicar este filtro favorito ao projeto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>Guardar alterações</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>Guardar as modificações deste favorito</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="733"/>
        <source>Delete</source>
        <translation>Eliminar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="736"/>
        <source>Permanently delete this favorite</source>
        <translation>Eliminar permanentemente este favorito</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="739"/>
        <source>Close</source>
        <translation>Fechar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>Fechar este diálogo</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="849"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Favoritos ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1015"/>
        <source>Remote ({0})</source>
        <translation>Remoto ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete Favorite</source>
        <translation>Eliminar favorito</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Eliminar favorito '{0}'?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>Camadas remotas</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1303"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Favoritos guardados (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Gestor de favoritos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>No favorites saved yet.

Click the ★ indicator and select 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Ainda não há favoritos guardados.

Clique no indicador ★ e selecione 'Adicionar filtro atual aos favoritos' para guardar o seu primeiro favorito.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>Partilhados…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Explorar favoritos partilhados através de coleções QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>Publicar…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Publicar favoritos selecionados numa coleção Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">Não foi possível eliminar «{0}». O favorito continua na base de dados — consulte o registo do FilterMate para mais detalhes.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>Filtrar favoritos por âmbito (proprietário × projeto).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>Todos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>Partilhados · Todos os projetos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>Partilhados · Este projeto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>Meus · Todos os projetos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>Meus · Este projeto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>Meus</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>Partilhados</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>Este projeto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>Todos os projetos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>O âmbito do projeto é definido ao criar o favorito. Mova-o através do separador de filtragem (em breve) para mudar de projeto.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>Visibilidade:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (partilhado com todos)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (você)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — selecionar 'Meus' ao guardar transferirá a propriedade para si</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>Não foi possível guardar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>Não foi possível eliminar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>'{0}' não estava na base de dados — atualize e tente novamente.</translation>
    </message>
</context>
<context>
    <name>FeedbackModule</name>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="112"/>
        <source>Exporting {0} layer(s)</source>
        <translation>A exportar {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="168"/>
        <source>Large dataset ({0} features) using {1}. Consider using PostgreSQL for optimal performance.</source>
        <translation>Conjunto de dados grande ({0} entidades) com {1}. Considere utilizar o PostgreSQL para um desempenho ótimo.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="176"/>
        <source>Medium-large dataset ({0} features) using {1}. PostgreSQL recommended for better performance.</source>
        <translation>Conjunto de dados médio-grande ({0} entidades) com {1}. Recomenda-se o PostgreSQL para um melhor desempenho.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="113"/>
        <source>Processing {0} layer(s)</source>
        <translation>A processar {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="110"/>
        <source>Removing filters from {0} layer(s)</source>
        <translation>A remover os filtros de {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="111"/>
        <source>Resetting {0} layer(s)</source>
        <translation>A repor {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="109"/>
        <source>Starting filter on {0} layer(s)</source>
        <translation>A iniciar o filtro em {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="137"/>
        <source>Successfully exported {0} layer(s)</source>
        <translation>{0} camada(s) exportada(s) com sucesso</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="134"/>
        <source>Successfully filtered {0} layer(s)</source>
        <translation>{0} camada(s) filtrada(s) com sucesso</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="138"/>
        <source>Successfully processed {0} layer(s)</source>
        <translation>{0} camada(s) processada(s) com sucesso</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="135"/>
        <source>Successfully removed filters from {0} layer(s)</source>
        <translation>Filtros removidos com sucesso de {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="136"/>
        <source>Successfully reset {0} layer(s)</source>
        <translation>{0} camada(s) reposta(s) com sucesso</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="604"/>
        <source>View</source>
        <translation>Ver</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="606"/>
        <source>Change</source>
        <translation>Alterar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>Selecionar uma pasta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>Selecionar um ficheiro</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>Guardar num ficheiro</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="664"/>
        <source>View</source>
        <translation>Ver</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="666"/>
        <source>Change</source>
        <translation>Alterar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>Selecionar um ícone</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>A camada é inválida ou a sua fonte não pode ser encontrada. Operação cancelada.</translation>
    </message>
</context>
<context>
    <name>FilterMate</name>
    <message>
        <location filename="../filter_mate.py" line="236"/>
        <source>&amp;FilterMate</source>
        <translation>&amp;FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="363"/>
        <source>FilterMate</source>
        <translation>FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="363"/>
        <source>Open FilterMate panel</source>
        <translation>Abrir painel FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>Redefinir configuração e banco de dados</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Redefinir a configuração padrão e excluir o banco de dados SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>Redefinir Configuração</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>Configuração redefinida com sucesso.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>Arquivo de configuração padrão não encontrado.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>Banco de dados excluído: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>Reinicialização necessária</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>Configuração obsoleta detectada</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>versão desconhecida</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>Configuração corrompida detectada</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Configuração não redefinida. Algumas funcionalidades podem não funcionar corretamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>Configuração criada com valores padrão</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Configuração corrompida redefinida. As configurações padrão foram restauradas.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Configuração obsoleta redefinida. As configurações padrão foram restauradas.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>Configuração atualizada para a versão mais recente</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Configuração atualizada: novas definições disponíveis ({sections}). Acesso via menu Opções.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>Simplificação de geometria</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>Limiares de otimização</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>Configuração de validação de geometria</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Filtragem de geometrias inválidas desativada com sucesso.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Filtragem de geometrias inválidas não modificada. Algumas feições podem ser excluídas das exportações.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Uma configuração obsoleta ({}) foi detectada.

Deseja redefinir para as configurações padrão?

• Sim: Redefinir (um backup será criado)
• Não: Manter a configuração atual (pode causar problemas)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>O arquivo de configuração está corrompido e não pode ser lido.

Deseja redefinir para as configurações padrão?

• Sim: Redefinir (um backup será criado se possível)
• Não: Cancelar (o plugin pode não funcionar corretamente)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>Redefinição de configuração</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>A configuração precisa ser redefinida.

Deseja continuar?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>Erro durante a migração de configuração: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="737"/>
        <source>The QGIS setting 'Invalid features filtering' is currently set to '{mode}'.

FilterMate recommends disabling this setting (value 'Off') for the following reasons:

• Features with invalid geometries could be silently excluded from exports and filters
• FilterMate handles geometry validation internally with automatic repair options
• Some legitimate data may have geometries considered as 'invalid' according to strict OGC rules

Do you want to disable this setting now?

• Yes: Disable filtering (recommended for FilterMate)
• No: Keep current setting</source>
        <translation>The QGIS setting 'Invalid features filtering' is currently set to '{mode}'.

FilterMate recommends disabling this setting (value 'Off') for the following reasons:

• Features with invalid geometries could be silently excluded from exports and filters
• FilterMate handles geometry validation internally with automatic repair options
• Some legitimate data may have geometries considered as 'invalid' according to strict OGC rules

Do you want to disable this setting now?

• Yes: Disable filtering (recommended for FilterMate)
• No: Keep current setting</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>Tem certeza de que deseja redefinir para a configuração padrão?

Isso irá:
- Restaurar as configurações padrão
- Excluir o banco de dados de camadas

O QGIS deve ser reiniciado para aplicar as alterações.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>A configuração foi redefinida.

Reinicie o QGIS para aplicar as alterações.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>Erro de inicialização: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} camada(s) referenciada(s) não carregada(s) ({layers_list}). A utilizar visualização alternativa.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Não é possível eliminar {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">Erro durante a reposição: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;Obrigado por utilizar o &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Junte-se à nossa comunidade Discord para:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;Obter ajuda e suporte&lt;/li&gt;&lt;li&gt;Reportar erros e problemas&lt;/li&gt;&lt;li&gt;Sugerir novas funcionalidades&lt;/li&gt;&lt;li&gt;Partilhar dicas com outros utilizadores&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  Junte-se a nós no Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>Não mostrar novamente</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>Fechar</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Erro ao carregar o plugin: {0}. Verifique a consola Python do QGIS para mais detalhes.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7357"/>
        <source>Current layer: {0}</source>
        <translation>Camada atual: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7359"/>
        <source>No layer selected</source>
        <translation>Nenhuma camada selecionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7369"/>
        <source>Selected layers:
{0}</source>
        <translation>Camadas selecionadas:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7369"/>
        <source>No layers selected</source>
        <translation>Nenhuma camada selecionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7389"/>
        <source>No expression defined</source>
        <translation>Nenhuma expressão definida</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7401"/>
        <source>Display expression: {0}</source>
        <translation>Expressão de visualização: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>ID do elemento: {0}
Primeiro atributo: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>Não foi possível repor a configuração. Verifique se a pasta do plugin é gravável e tente novamente. Detalhes em filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>Novidades do FilterMate 5</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;O FilterMate agora funciona com camadas raster e de nuvens de pontos.&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapta-se à camada atual: intervalo de valores e classes de um raster, classes, elevação e atributos de uma nuvem de pontos LiDAR.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relaciona essa seleção com camadas de qualquer tipo, com os predicados e o buffer habituais: parcelas num intervalo de elevação, pontos LiDAR sob os edifícios, um MDT recortado por um município.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; grava os rasters (GeoTIFF, COG) e as nuvens de pontos (LAZ, COPC) filtrados.&lt;/li&gt;&lt;li&gt;Algoritmos e modelos do Processing, qgis_process, APIs Python e REST.&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>Abrir o guia do utilizador</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="207"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Esta expressão não pode ser avaliada de forma segura para um serviço.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="209"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Não foi possível ler o serviço. Tente novamente.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="210"/>
        <source>Read failed</source>
        <translation>Falha na leitura</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="270"/>
        <source>Loading filtered extent…</source>
        <translation>A carregar a extensão filtrada…</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="306"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>Camadas PostgreSQL detetadas ({0}), mas psycopg2 não está instalado.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="406"/>
        <source>Cleared {0} caches</source>
        <translation>{0} caches limpos</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="912"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Falha ao criar o painel acoplável: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="922"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Falha ao apresentar o painel acoplável: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1493"/>
        <source>Error executing {0}: {1}</source>
        <translation>Erro ao executar {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1505"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Plugin em execução em modo degradado (serviços hexagonais indisponíveis). O desempenho pode ser reduzido.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1854"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate ERRO</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1854"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Não é possível executar {0}: inicialização do widget falhou.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2635"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Não é possível {0}: camada inválida ou fonte não encontrada.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2789"/>
        <source>All filters cleared - </source>
        <translation>Todos os filtros removidos – </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2790"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} elementos visíveis na camada principal</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2802"/>
        <source>Error: result handler missing</source>
        <translation>Erro: manipulador de resultados em falta</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2819"/>
        <source>Error during filtering: {0}</source>
        <translation>Erro durante a filtragem: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2943"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0} favorito(s) órfão(s) recuperado(s): {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3109"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Carregamento de camadas falhou – clique para tentar novamente</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3161"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} camada(s) carregada(s) com sucesso</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2092"/>
        <source>filter</source>
        <translation>filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2094"/>
        <source>unfilter</source>
        <translation>desfiltrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2097"/>
        <source>FilterMate – Edit Mode Detected</source>
        <translation>FilterMate – Modo de edição detectado</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2099"/>
        <source>The following layer(s) are currently in edit mode:
{0}

QGIS cannot apply filters while a layer is being edited.
What would you like to do?</source>
        <translation>The following layer(s) are currently in edit mode:
{0}

QGIS cannot apply filters while a layer is being edited.
What would you like to do?</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2109"/>
        <source>Save Changes &amp; {0}</source>
        <translation>Salvar alterações e {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2116"/>
        <source>Discard Changes &amp; {0}</source>
        <translation>Descartar alterações e {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2123"/>
        <source>Cancel</source>
        <translation>Cancelar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2147"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>Não foi possível salvar as alterações da camada &quot;{0}&quot;. Operação cancelada.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1323"/>
        <source>Pick a layer in the EXPLORING tab before running &apos;{0}&apos;.</source>
        <translation>Escolha uma camada no separador EXPLORING antes de executar '{0}'.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="839"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} camada(s) continuam filtradas: {1}. Reative a opção para remover o filtro.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2621"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>Está a ser preparado um filtro de servidor. Aguarde que termine antes de iniciar outra operação.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1770"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>Está a decorrer uma operação da API do FilterMate. Aguarde que termine.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="445"/>
        <source>Adding layers</source>
        <translation>A adicionar camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="449"/>
        <source>Existing project loaded</source>
        <translation>Projeto existente carregado</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="442"/>
        <source>Exporting data</source>
        <translation>A exportar dados</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="439"/>
        <source>Filtering data</source>
        <translation>A filtrar dados</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="448"/>
        <source>New project</source>
        <translation>Novo projeto</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="444"/>
        <source>Redo filter</source>
        <translation>Refazer filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="450"/>
        <source>Reloading layers</source>
        <translation>A recarregar camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="447"/>
        <source>Removing all layers</source>
        <translation>A remover todas as camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="446"/>
        <source>Removing layers</source>
        <translation>A remover camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="441"/>
        <source>Reseting data</source>
        <translation>A repor dados</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="443"/>
        <source>Undo filter</source>
        <translation>Anular filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="440"/>
        <source>Unfiltering data</source>
        <translation>A desfiltrar dados</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>Erro de inicialização: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Configuração da interface incompleta – verifique os registos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">Erro de dimensão da interface: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>Gestor de favoritos não disponível</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} favoritos guardados
Clique para aplicar ou gerir</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Sem favoritos guardados
Clique para adicionar o filtro atual</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <location filename="../ui/controllers/backend_controller.py" line="822"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>Backend {0} forçado para {1} camada(s)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>Controlador de backend não disponível</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>Limpeza automática do PostgreSQL ativada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>Limpeza automática do PostgreSQL desativada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>Vistas de sessão PostgreSQL limpas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Sem vistas para limpar ou limpeza falhou</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <location filename="../ui/controllers/backend_controller.py" line="1089"/>
        <source>No PostgreSQL connection available</source>
        <translation>Nenhuma conexão PostgreSQL disponível</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>O esquema tem {0} vista(s) de outras sessões.
Eliminar mesmo assim?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>Outras sessões ativas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>Limpeza do esquema cancelada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Esquema '{0}' eliminado com sucesso</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <location filename="../ui/controllers/backend_controller.py" line="1090"/>
        <source>Schema cleanup failed</source>
        <translation>Limpeza do esquema falhou</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>Informação de sessão PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>Tema adaptado: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>Modo escuro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>Modo claro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4102"/>
        <source>Selected features have no geometry.</source>
        <translation>Os elementos selecionados não têm geometria.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4121"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Nenhum elemento selecionado. Selecione um elemento da lista suspensa.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5285"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>A camada selecionada é inválida ou a sua fonte não pode ser encontrada.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6080"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Buffer negativo (erosão): contrai os polígonos para o interior</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6083"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Valor do buffer em metros (positivo=expandir, negativo=contrair polígonos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6585"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Plugin ativado com {0} camada(s) vetorial(ais)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6684"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Não foi possível recarregar o plugin automaticamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6689"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Erro ao recarregar o plugin: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6764"/>
        <source>Layer properties reset to defaults</source>
        <translation>Propriedades da camada repostas para os valores predefinidos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6765"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Erro ao repor as propriedades da camada: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="895"/>
        <source>Filter</source>
        <translation>Filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>Anular o último filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>Refazer o último filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>Remover os filtros</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>Exportar as camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>Sobre o FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>Identificar as entidades selecionadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>Ampliar para as entidades selecionadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>Selecionar as entidades no mapa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>Seguir as entidades no mapa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">Ligar os três modos de seleção</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>Repor as propriedades da camada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>Seguir a camada atual</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>Camadas a filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>Combinar com o filtro existente</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>Predicados geométricos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>Distância do buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>Tipo de buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>Camadas a exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>Projeção da exportação</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>Exportar os estilos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>Formato de exportação</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>Pasta de saída</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>Compactar a exportação em zip</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>Não foi possível aplicar a disposição do painel; são utilizados os tamanhos predefinidos. Detalhes em filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6856"/>
        <location filename="../ui/controllers/backend_controller.py" line="682"/>
        <source>Vector</source>
        <translation>Vetorial</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>Ligar as seleções simples e múltipla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>O esquema '{0}' e os seguintes {1} objeto(s) temporário(s) serão eliminados:</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>... e mais {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>O esquema '{0}' está vazio e será eliminado.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>Eliminar o esquema do FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4224"/>
        <source>Read failed</source>
        <translation>Falha na leitura</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4224"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Não foi possível ler o serviço. Tente novamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4566"/>
        <source>Loading filtered extent…</source>
        <translation>A carregar a extensão filtrada…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5150"/>
        <location filename="../ui/controllers/exploring_controller.py" line="539"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3408"/>
        <source>Loading selected values…</source>
        <translation>A carregar os valores selecionados…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5141"/>
        <location filename="../ui/controllers/exploring_controller.py" line="502"/>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Esta expressão não pode ser avaliada de forma segura para um serviço.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2472"/>
        <source>Error evaluating expression: {0}</source>
        <translation>Erro ao avaliar a expressão: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2471"/>
        <source>Expression Evaluation</source>
        <translation>Avaliação da expressão</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="411"/>
        <source>Loading values…</source>
        <translation>A carregar valores…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="646"/>
        <source>Loading zoom extent…</source>
        <translation>A carregar a extensão do zoom…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="633"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>Nenhuma entidade com geometria corresponde à seleção.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="408"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>Apenas é apresentado um conjunto limitado de valores. Refine a pesquisa para encontrar outros valores.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="475"/>
        <location filename="../ui/controllers/exploring_controller.py" line="483"/>
        <location filename="../ui/controllers/exploring_controller.py" line="502"/>
        <location filename="../ui/controllers/exploring_controller.py" line="566"/>
        <source>Selection</source>
        <translation>Seleção</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="475"/>
        <location filename="../ui/controllers/exploring_controller.py" line="566"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>A seleção do serviço excede o limite de chaves. Refine a seleção.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="483"/>
        <source>This service has no stable key for the selection.</source>
        <translation>Este serviço não tem uma chave estável para a seleção.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="408"/>
        <source>Values</source>
        <translation>Valores</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <location filename="../ui/controllers/exploring_controller.py" line="633"/>
        <source>Zoom</source>
        <translation>Zoom</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1087"/>
        <source>&apos;{0}&apos; is not a FilterMate temporary schema: it is not dropped</source>
        <translation>'{0}' não é um esquema temporário do FilterMate: não é eliminado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1312"/>
        <source>... and {0} more (see details)</source>
        <translation>... e mais {0} (ver detalhes)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="778"/>
        <source>Auto (Default)</source>
        <translation>Auto (predefinição)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="786"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Seleção automática ótima para todas as camadas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="817"/>
        <source>Auto-selected backends for {0} layer(s)</source>
        <translation>Backends selecionados automaticamente para {0} camada(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="838"/>
        <source>Backend forced to {0} for &apos;{1}&apos;</source>
        <translation>Backend forçado para {0} em '{1}'</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="841"/>
        <source>Backend set to Auto for &apos;{0}&apos;</source>
        <translation>Backend definido como Auto para '{0}'</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1336"/>
        <source>Cleanup cancelled</source>
        <translation>Limpeza cancelada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="807"/>
        <source>Clear ALL FilterMate temporary tables from all databases</source>
        <translation>Limpar TODAS as tabelas temporárias do FilterMate de todas as bases de dados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="797"/>
        <source>Clear Temp Tables</source>
        <translation>Limpar tabelas temporárias</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1317"/>
        <source>Clear all FilterMate temporary tables</source>
        <translation>Limpar todas as tabelas temporárias do FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="802"/>
        <source>Clear temporary tables for the current project only</source>
        <translation>Limpar as tabelas temporárias apenas do projeto atual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="828"/>
        <source>Cleared {0} temporary table(s) for current project</source>
        <translation>{0} tabela(s) temporária(s) do projeto atual limpa(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1340"/>
        <source>Cleared {0} temporary table(s) globally</source>
        <translation>{0} tabela(s) temporária(s) limpa(s) globalmente</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1307"/>
        <source>FilterMate will permanently delete {0} temporary table(s) / view(s) from the databases of the project and of the PostgreSQL connection:</source>
        <translation>O FilterMate eliminará permanentemente {0} tabela(s) / vista(s) temporária(s) das bases de dados do projeto e da ligação PostgreSQL:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="791"/>
        <source>Force {0} for All Layers</source>
        <translation>Forçar {0} para todas as camadas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="742"/>
        <source>No alternative backends available for this layer</source>
        <translation>Não existem backends alternativos disponíveis para esta camada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1333"/>
        <location filename="../ui/controllers/backend_controller.py" line="1342"/>
        <source>No temporary tables found</source>
        <translation>Não foram encontradas tabelas temporárias</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="830"/>
        <source>No temporary tables found for current project</source>
        <translation>Não foram encontradas tabelas temporárias para o projeto atual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1080"/>
        <source>Schema &apos;{0}&apos; does not exist: nothing to drop</source>
        <translation>O esquema '{0}' não existe: nada a eliminar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1083"/>
        <source>Schema &apos;{0}&apos; holds objects FilterMate did not create ({1}): it is not dropped</source>
        <translation>O esquema '{0}' contém objetos que o FilterMate não criou ({1}): não é eliminado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="762"/>
        <source>Select Backend:</source>
        <translation>Selecionar backend:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1313"/>
        <source>Your own tables and layers are not touched. Continue?</source>
        <translation>As suas próprias tabelas e camadas não são tocadas. Continuar?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="805"/>
        <source>🌐 All Projects (Global)</source>
        <translation>🌐 Todos os projetos (global)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="800"/>
        <source>📁 Current Project</source>
        <translation>📁 Projeto atual</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidgetBase</name>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="54"/>
        <source>FilterMate</source>
        <translation>FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="775"/>
        <source>SINGLE SELECTION</source>
        <translation>SELEÇÃO SIMPLES</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>SELEÇÃO MÚLTIPLA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>SELEÇÃO PERSONALIZADA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>FILTRAGEM</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>EXPORTAÇÃO</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>CONFIGURAÇÃO</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>Selecionar SRC para exportação</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>Exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2330"/>
        <source>AND</source>
        <translation>E</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2335"/>
        <source>AND NOT</source>
        <translation>E NÃO</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2340"/>
        <source>OR</source>
        <translation>OU</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3277"/>
        <source>QML</source>
        <translation>QML</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3282"/>
        <source>SLD</source>
        <translation>SLD</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2533"/>
        <source> m</source>
        <translation> m</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2406"/>
        <source>, </source>
        <translation>, </translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1571"/>
        <source>Multi-layer filtering</source>
        <translation>Filtragem multicamada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Filtragem aditiva para a camada selecionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>Filtragem geoespacial</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>Buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>Camada de expressão</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>Predicado geométrico</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>Formato de saída</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>Filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>Redefinir</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>Camadas para exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>Projeção das camadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>Salvar estilos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>Exportar tipo de dados</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>Nome do arquivo/diretório</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Usar centróides em vez de geometrias completas para a camada de origem (mais rápido para polígonos complexos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Valor do buffer em metros (positivo=expandir, negativo=contrair polígonos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>Número de segmentos para a precisão do buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>Modo batch</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="556"/>
        <source>FilterMate was unloaded</source>
        <translation>O FilterMate foi descarregado</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="118"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>raster renderizado ou não suportado: não pode ser um alvo do filtro</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="505"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>as origens raster renderizadas requerem uma captura de cor local; as seleções numéricas de píxeis não estão disponíveis</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="577"/>
        <source>the source layer itself was not changed</source>
        <translation>a própria camada de origem não foi alterada</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="347"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} elementos visíveis na camada principal</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Todos os filtros removidos – {count} elementos visíveis na camada principal</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>Tarefa falhou</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>Filtro falhou para: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0} mais)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>Camada(s) filtrada(s)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Camada(s) filtrada(s) para o estado anterior</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>Filtro(s) removido(s) da(s) camada(s)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>Tarefa de filtragem: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>Tarefa de exportação: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>Exceção: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>Filtro não aplicado, filtro anterior mantido: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>Camada(s) removida(s) durante o filtro, ignorada(s): {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>Desenhe uma zona de seleção útil antes de calcular a altura acima do solo remotamente</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>O MDT e a nuvem de pontos não têm uma extensão útil em comum</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>A seleção útil não tem área poligonal</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>A altura acima do solo cobre apenas a área útil; Desfiltrar restaura a nuvem original</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Menus e barras de ferramentas Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Propriedade</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Valor</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Propriedade</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Valor</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="262"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>Camadas PostgreSQL detetadas ({0}), mas psycopg2 não está instalado. O plugin não pode usar estas camadas. Instale psycopg2 para ativar o suporte PostgreSQL.</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>Não foi possível abrir a origem guardada</translation>
    </message>
</context>
<context>
    <name>LayersManagementEngineTask</name>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1074"/>
        <source>PostgreSQL layer &apos;{0}&apos;: Corrupted data detected.

This layer uses &apos;virtual_id&apos; which does not exist in PostgreSQL.
This error originates from a previous version of FilterMate.

Solution: Remove this layer from the FilterMate project, then re-add it.
Make sure the PostgreSQL table has a PRIMARY KEY defined.</source>
        <translation>Camada PostgreSQL '{0}': Dados corrompidos detetados.

Esta camada usa 'virtual_id' que não existe no PostgreSQL.
Este erro tem origem numa versão anterior do FilterMate.

Solução: Remova esta camada do projeto FilterMate e adicione-a novamente.
Certifique-se de que a tabela PostgreSQL tem um PRIMARY KEY definido.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>A camada '{0}' não tem PRIMARY KEY. Funcionalidades limitadas: vistas materializadas desativadas. Recomendação: adicionar um PRIMARY KEY para desempenho ótimo.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>Exceção: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: este fornecedor não pode garantir um filtro de servidor completo. Utilize uma cópia local limitada antes de filtrar.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: não foi possível ler do serviço web os valores de chave das entidades selecionadas.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>mantém o filtro anterior</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>fica sem filtro</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: este serviço web não tem um campo de chave única (chave declarada, id, gml_id, cleabs, objectid...), pelo que as entidades selecionadas não podem ser listadas para o servidor. A camada {1}. Um filtro por atributos ou uma cópia local da camada funciona.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: esta camada não tem um campo de chave única e os identificadores das suas entidades não podem ser listados no respetivo filtro (uma camada virtual precisa de uma coluna de id única, o seu uid). A camada {1}.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: {1} entidades a listar, mais do que as {2} enviadas para um serviço web. A camada {3}. Reduza a seleção, utilize um filtro por atributos ou trabalhe sobre uma cópia local da camada.</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Configurações de otimização</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Configurar definições de otimização</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Ativar otimizações automáticas</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Perguntar antes de aplicar otimizações</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Configurações de centróide automático</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Ativar centróide automático para camadas distantes</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Limiar de distância (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Limiar de feições:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Otimizações de buffer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Simplificar geometria antes do buffer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Reduzir segmentos de buffer para:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Geral</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Usar views materializadas para filtragem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Criar índices espaciais automaticamente</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Usar índice espacial R-tree</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Usar pré-filtro de bounding box</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Backends</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Cache</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Ativar cache de geometria</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Processamento em lote</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Tamanho do lote:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Configurações avançadas afetam desempenho e uso de memória. Altere apenas se entender as implicações.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Avançado</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="323"/>
        <source>PostgreSQL</source>
        <translation>PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="335"/>
        <source>Spatialite</source>
        <translation>Spatialite</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="344"/>
        <source>OGR (Shapefiles, GeoPackage)</source>
        <translation>OGR (Shapefiles, GeoPackage)</translation>
    </message>
</context>
<context>
    <name>PointCloudConditionRow</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="797"/>
        <source>Link with the previous condition</source>
        <translation>Ligação com a condição anterior</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="799"/>
        <source>AND</source>
        <translation>E</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="800"/>
        <source>OR</source>
        <translation>OU</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="801"/>
        <source>Attribute</source>
        <translation>Atributo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>Comparação</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>entre</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>Remover esta condição</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>Comparar com um valor ou outro atributo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="821"/>
        <source>value</source>
        <translation>valor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="822"/>
        <source>Value</source>
        <translation>Valor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="825"/>
        <source>Highest value kept</source>
        <translation>Valor mais alto mantido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>Valores observados: {0} a {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>Sem estatísticas para este atributo</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1053"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>Aplicar aos outros blocos do conjunto de dados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1062"/>
        <source>CLASSES</source>
        <translation>CLASSES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Ground</source>
        <translation>Solo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Vegetation</source>
        <translation>Vegetação</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1069"/>
        <source>Buildings</source>
        <translation>Edifícios</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1070"/>
        <source>Above ground</source>
        <translation>Acima do solo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1071"/>
        <source>Water</source>
        <translation>Água</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1072"/>
        <source>Without noise</source>
        <translation>Sem ruído</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">Marcar apenas estas classes</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">Nenhuma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1101"/>
        <source>Point classes</source>
        <translation>Classes de pontos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">INTERVALOS DE ATRIBUTOS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (m)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">Elevação mais baixa mantida</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">Elevação mais alta mantida</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Intensity</source>
        <translation>Intensidade</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">Intensidade mais baixa mantida</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">Intensidade mais alta mantida</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">Retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">Eco do impulso laser mantido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">Altura acima do MDT ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1290"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>Modelo digital de terreno a partir do qual a altura é medida</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1300"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>Manter os pontos pelo menos a esta altura acima do modelo de terreno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>EXPRESSION</source>
        <translation>EXPRESSÃO</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1379"/>
        <source>Point cloud expression</source>
        <translation>Expressão da nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1380"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>Marque o grupo para editar a expressão manualmente</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">Sem estatísticas de elevação para esta camada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1661"/>
        <source>Height above the terrain is unavailable</source>
        <translation>A altura acima do terreno não está disponível</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">Pontos mantidos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Filtro atual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">nenhum</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">Qualquer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">Primeiro</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Last</source>
        <translation type="obsolete">Último</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Single</source>
        <translation type="obsolete">Único</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1176"/>
        <source>ATTRIBUTES</source>
        <translation>ATRIBUTOS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1194"/>
        <source>+ Condition</source>
        <translation>+ Condição</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1196"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>Adicionar uma condição sobre um atributo da camada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1235"/>
        <source>Returns</source>
        <translation>Retornos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">Manter os retornos primeiros, últimos ou únicos dos pulsos laser</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1242"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>Primeiro retorno (ReturnNumber = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1243"/>
        <source>Last return (ReturnNumber = NumberOfReturns)</source>
        <translation>Último retorno (ReturnNumber = NumberOfReturns)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1244"/>
        <source>Single return (NumberOfReturns = 1)</source>
        <translation>Retorno único (NumberOfReturns = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1349"/>
        <source>Return number</source>
        <translation>Número de retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1350"/>
        <source>Number of returns</source>
        <translation>Número de retornos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1351"/>
        <source>Classification</source>
        <translation>Classificação</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Scan angle</source>
        <translation>Ângulo de varrimento</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>User data</source>
        <translation>Dados do utilizador</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Point source ID</source>
        <translation>ID da fonte</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>GPS time</source>
        <translation>Tempo GPS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Red</source>
        <translation>Vermelho</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1357"/>
        <source>Green</source>
        <translation>Verde</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1358"/>
        <source>Blue</source>
        <translation>Azul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1359"/>
        <source>Infrared</source>
        <translation>Infravermelho</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Scan direction</source>
        <translation>Direção de varrimento</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Edge of flight line</source>
        <translation>Borda da faixa de voo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Synthetic</source>
        <translation>Sintético</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Key point</source>
        <translation>Ponto-chave</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Withheld</source>
        <translation>Retido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1365"/>
        <source>Overlap</source>
        <translation>Sobreposição</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>Scanner channel</source>
        <translation>Canal do scanner</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>Classification flags</source>
        <translation>Indicadores de classificação</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>Height above ground</source>
        <translation>Altura acima do solo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Quick class selection</source>
        <translation>Seleção rápida de classes</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">Seleção rápida…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>All classes</source>
        <translation>Todas as classes</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>No class</source>
        <translation>Nenhuma classe</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>Invert the selection</source>
        <translation>Inverter a seleção</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Selection ▾</source>
        <translation>Seleção ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1115"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>Classes da norma sem qualquer ponto nesta camada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1122"/>
        <source>Classes absent from the layer</source>
        <translation>Classes ausentes da camada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1146"/>
        <source>Similar objects: area ×</source>
        <translation>Objetos semelhantes: área ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Menor objeto semelhante, como proporção do menor dos clicados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Maior objeto semelhante, como múltiplo do maior dos clicados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1164"/>
        <source>to ×</source>
        <translation>a ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1208"/>
        <source>Pipette on</source>
        <translation>Conta-gotas em</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1209"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>Atributo que o conta-gotas de valor da barra lateral lê sob o clique</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1224"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>Tolerância em torno do valor escolhido, em % do intervalo observado do atributo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1236"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>Manter todos os retornos, ou os primeiros, últimos ou únicos retornos dos impulsos laser</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1241"/>
        <source>Any return</source>
        <translation>Qualquer retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1255"/>
        <source>HEIGHT / DTM</source>
        <translation>ALTURA / MDT</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>Always combined (AND) with the active group</source>
        <translation>Sempre combinada (AND) com o grupo ativo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1265"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · nuvem derivada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1267"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>A altura é calculada pelo PDAL numa nuvem de pontos derivada, numa tarefa em segundo plano</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1370"/>
        <source>{0} object(s)</source>
        <translation>{0} objeto(s)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>cut at the window read</source>
        <translation>cortado na janela de leitura</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1372"/>
        <source>shown as the whole class in their box</source>
        <translation>apresentados como a classe completa na sua caixa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1863"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>Outras classes, ausentes da camada ({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1954"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>Um objeto ultrapassa a maior janela de leitura à volta do clique e foi cortado aí</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1956"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>Demasiados objetos para o subconjunto da nuvem: a pré-visualização e a nuvem filtrada mantêm todos os pontos da sua classe na caixa que os rodeia; os alvos são cortados pelos próprios objetos</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">Filtro de nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">Classificação</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">Nenhuma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">Elevação (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">Intensidade</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="175"/>
        <source>Return number</source>
        <translation type="obsolete">Número de retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="199"/>
        <source>Minimum</source>
        <translation type="obsolete">Mínimo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="200"/>
        <source>Maximum</source>
        <translation type="obsolete">Máximo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Filtro atual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">nenhum</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">Qualquer</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>É necessária uma extensão útil para uma nuvem de pontos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>Não existe nenhum leitor PDAL para este formato de nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>É necessário o PDAL 2.4 ou posterior, com uma versão legível, para nuvens de pontos remotas</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>As nuvens de pontos remotas requerem EPT ou COPC para leituras limitadas</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>A extensão útil tem de ser finita e ter uma área positiva</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="435"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>Desenhe uma zona de seleção útil antes de ler uma nuvem de pontos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="468"/>
        <source>The remote point cloud could not be read</source>
        <translation>Não foi possível ler a nuvem de pontos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="472"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>A nuvem de pontos remota rejeitou a seleção</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="605"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>Uma nuvem limitada de altura acima do solo só suporta AND ou AND NOT; desfiltre primeiro</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="631"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>É necessário o PDAL 2.4 ou posterior para recortar uma nuvem de pontos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="682"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Disjoint leria toda a nuvem remota; escolha uma seleção interior</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="689"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>Não foi possível abrir a nuvem de pontos remota original</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>Info de sessão PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL ativo</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Info de conexão</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Conexão:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Schema temporário:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Status:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Views temporárias</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Opções de limpeza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Limpeza automática ao fechar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Limpar automaticamente views temporárias quando FilterMate fecha.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Limpar agora</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Excluir todas as views temporárias criadas pelo FilterMate nesta sessão.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Nenhuma view temporária)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Nenhuma view</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Não há views temporárias para limpar.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Confirmar limpeza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Limpeza concluída</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Problema de limpeza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Limpeza falhou</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL não está disponível&lt;/b&gt;&lt;br&gt;&lt;br&gt;Para utilizar as funcionalidades PostgreSQL, instale psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Depois reinicie o QGIS para aplicar as alterações.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Sessão: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} vista(s) nesta sessão</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Isto irá eliminar {view_count} vista(s) temporária(s) criada(s) pelo FilterMate.

Todos os resultados de filtragem não guardados serão perdidos.

Continuar?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped} vista(s) temporária(s) removida(s).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Algumas vistas não puderam ser removidas: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Erro durante a limpeza: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>Camadas a filtrar</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="139"/>
        <location filename="../processing/algorithms/common.py" line="78"/>
        <source>FilterMate</source>
        <translation>FilterMate</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="56"/>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="125"/>
        <source>Buffer</source>
        <translation>Buffer</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="105"/>
        <source>Band</source>
        <translation>Banda</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>Expressão raster</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>Pasta de saída</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>Predicados geométricos</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>Valor do píxel</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>Declive (graus)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>Declive (%)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>Orientação (graus)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>Sombreamento (0-255)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>O raster de origem foi reamostrado para a captura (grelha: {0}).</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: o raster alvo foi reamostrado para a captura (grelha: {1}).</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="108"/>
        <source>Favorite name or identifier</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="115"/>
        <source>Provide the name of the favorite</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="119"/>
        <source>Favorite: {0}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="126"/>
        <source>Apply a FilterMate favorite</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="129"/>
        <source>Replays a favorite saved in FilterMate (by name or identifier): filters of the vector and point cloud layers, clips of the rasters and point clouds. Layers are found by signature, then identifier, then name. Without the dock (qgis_process), the favorites saved in the project are used.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="66"/>
        <source>Filter expression</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="88"/>
        <source>No layer selected.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="112"/>
        <source>Invalid expression for layer &apos;{0}&apos;, skipped.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="135"/>
        <source>Filter several layers (batch)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="147"/>
        <source>Applies the same filter expression to several vector layers in a single run.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="79"/>
        <source>Layers to clear</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="87"/>
        <source>cleared</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="93"/>
        <source>Clear the filters of layers of any type</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="96"/>
        <source>Removes the filter from the chosen layers: subset cleared for vectors and point clouds, original source restored for clipped rasters and point clouds. Useful at the start of a model to start again from the complete data. Can be undone from FilterMate.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="52"/>
        <source>Source layer</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="54"/>
        <source>Selected features only</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="64"/>
        <source>Invalid source layer</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="67"/>
        <source>{0} source feature(s)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="77"/>
        <source>Filter layers of any type by a vector layer</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="80"/>
        <source>Filters vector, raster and point cloud layers in place by the features of a vector layer, with the geometric predicates, a buffer and a minimum coverage.

</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="250"/>
        <source>Extent</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="251"/>
        <source>Geometry (WKT, takes precedence over the extent)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="267"/>
        <source>Provide an extent or a geometry</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="279"/>
        <source>Filter layers of any type by an extent or a geometry</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="282"/>
        <source>Filters the target layers by an extent (layer, canvas, typed in) or a WKT geometry, with the same predicates, buffer and coverage as the FILTERING tab. The operation is recorded in the history of the first target layer.

</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="197"/>
        <source>Source point cloud</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="199"/>
        <source>Combine the criteria with the existing filter of the source</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="203"/>
        <source>Point footprint resolution (point cloud units)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="212"/>
        <source>Invalid source point cloud</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="215"/>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="53"/>
        <source>Criteria: {0}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="224"/>
        <source>Footprint computed from a limited number of points: increase the resolution</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="231"/>
        <source>Filter layers of any type by the points of a point cloud</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="234"/>
        <source>Applies criteria to the source point cloud (ASPRS classes, Z and intensity ranges, return number, expression), computes the footprint of the retained points and filters the target layers by this area.

Examples: buildings intersecting class 6 points (coverage ≥ 10%); Disjoint = buildings absent from the point cloud; a DEM limited to the extent of the water points (class 9).

Without criteria, the footprint covers the points displayed by the point cloud.

</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="104"/>
        <source>Source raster</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Pixels to keep</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Value range</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Classes</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Range applies to (band read as a DTM for slope, aspect...)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Roughness (TRI)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="114"/>
        <source>Minimum value (range)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="116"/>
        <source>Maximum value (range)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="118"/>
        <source>Class values (e.g. 6,7)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="120"/>
        <source>Raster expression, pixel kept if non-zero (e.g. &quot;dem@1&quot; &gt; 1200)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="123"/>
        <source>Also hide the source raster outside the selection</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="128"/>
        <source>Maximum pixels read (beyond: resampling)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="138"/>
        <source>Invalid source raster</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="150"/>
        <source>Selection: {0}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="162"/>
        <source>{0} of {1} pixel(s) kept</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="169"/>
        <source>Filter layers of any type by the pixels of a raster</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="172"/>
        <source>Keeps the pixels of a raster (value range of a band, classes of a categorized raster or raster expression), vectorizes them at the pixel size and filters the target layers by this area.

Examples: parcels contained in the 1200–1300 m zone with a coverage of 50%; a DEM limited to the forest classes; LiDAR points of the areas with a slope &lt; 15% (choose &quot;Slope (%)&quot; in &quot;Range applies to&quot; with a DEM as the source: no &quot;Slope&quot; step needed before).

The source raster can be a model output: it is read without being modified. With &quot;Also hide the source raster outside the selection&quot; and a project source, the source itself is filtered.

</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="147"/>
        <source>Layers to export</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="149"/>
        <source>Vector format</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="151"/>
        <source>Raster format</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="153"/>
        <source>Point cloud format</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="156"/>
        <source>Output CRS (empty = the layer&apos;s CRS)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="159"/>
        <source>Files written</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="179"/>
        <source>exported</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="188"/>
        <source>Export filtered layers (vector, raster, point cloud)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="191"/>
        <source>Writes each layer as it is filtered, one file per layer named after the layer: subset features for vectors, retained pixels (NoData elsewhere) as GeoTIFF or COG for rasters, retained points as LAZ, COPC, LAS, GPKG or CSV for point clouds.

In a model, connect &quot;Processed layers&quot; of a FilterMate filter to &quot;Layers to export&quot;. COPC requires PDAL (shipped with QGIS); without PDAL, a LAZ is written instead.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="90"/>
        <source>Layers to filter (vector, raster, point cloud)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="96"/>
        <source>Buffer (source units)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="99"/>
        <source>Minimum coverage of the target polygons (%)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="102"/>
        <source>Combine with the existing filter of the targets</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="109"/>
        <source>Vector: subset of the features. Raster: pixels outside the area set to NoData (clipped VRT). Point cloud: points outside the area removed (derived COPC file, PDAL). Disjoint keeps the outside.

Only project layers are filtered. The filter can be undone from FilterMate and the original sources are always recorded in the project. The &quot;Processed layers&quot; output can be chained in a model, for example into &quot;Export filtered layers&quot;.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="117"/>
        <source>Replace</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="123"/>
        <source>ASPRS classes to keep (e.g. 3,4,5; empty = all)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="125"/>
        <source>Minimum Z</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="125"/>
        <source>Maximum Z</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="125"/>
        <source>Minimum intensity</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="125"/>
        <source>Maximum intensity</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="129"/>
        <source>Return number (empty = all)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="132"/>
        <source>Point cloud expression (e.g. ReturnNumber = NumberOfReturns)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="137"/>
        <source>Processed layers</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="185"/>
        <source>Layer skipped: {0} ({1})</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="188"/>
        <source>filtered</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="198"/>
        <source> ({0:.1f} s)</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="201"/>
        <source>{0}: {1}{2}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="206"/>
        <source>{0}: failed — {1}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="42"/>
        <source>Point clouds</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="45"/>
        <source>Combine with the existing filter of each point cloud</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="52"/>
        <source>Provide classes, a range, a return number or an expression</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="64"/>
        <source>Filter point clouds by criteria</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="67"/>
        <source>Applies the same criteria (ASPRS classes, Z and intensity ranges, return number, expression) to one or more point clouds of the project, for example all the LiDAR HD tiles of a work site. The filter is the point cloud expression (subset): it is immediate and can be undone from FilterMate.</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="119"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — Publicar no Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Publicar favoritos&lt;/b&gt; — escrever um pacote partilhável numa coleção QGIS Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>Sobrescrever pacote existente</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>Publicar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Coleção de destino&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>Procurar…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Nome do ficheiro de pacote&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>ex. zonas_bruxelas</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;destino&amp;gt;/filter_mate/favorites/&amp;lt;nome&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Metadados da coleção&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>Nome a apresentar da coleção</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>Nome:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>Autor / organização</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>Autor:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>ex. CC-BY-4.0, MIT, Proprietária</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>Licença:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>Etiquetas separadas por vírgulas</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="221"/>
        <source>Tags:</source>
        <translation>Etiquetas:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="224"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="225"/>
        <source>Homepage:</source>
        <translation>Página web:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="229"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Descrição curta (opcional, texto simples)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>Descrição:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Favoritos a incluir&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>Selecionar tudo</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>Desmarcar tudo</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Nova coleção na raiz do Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>Pasta personalizada…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Será criada na raiz do Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Clique em 'Procurar…' para escolher uma pasta.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>Escolher uma pasta de coleção</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} selecionados</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>Não é possível criar a coleção</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Raiz do Resource Sharing não encontrada. Utilize 'Procurar…' para escolher uma pasta.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>Escolher uma pasta</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Clique em 'Procurar…' para escolher uma pasta de destino.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>Nenhum favorito selecionado</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Selecione pelo menos um favorito para publicar.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>Falha na publicação</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>Erro desconhecido.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>Publicado(s) {0} favorito(s) em:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Manifesto da coleção atualizado:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>Publicação bem-sucedida</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>Repositórios remotos indisponíveis</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>O gestor de repositórios remotos não está inicializado.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>A publicação em &lt;b&gt;{0}&lt;/b&gt; falhou.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>Abrir clone…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>Pacote escrito em:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>Commit &lt;code&gt;{0}&lt;/code&gt; enviado para &lt;b&gt;{1}&lt;/b&gt;.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>Sem git_url configurado — pacote escrito localmente. Envie manualmente com as suas próprias ferramentas.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>Nada para submeter — conteúdo do pacote inalterado.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>A publicar em {0}...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>Cancelar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>A publicar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>Publicação em curso</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>Uma publicação ainda está em curso em segundo plano. Aguarde que termine antes de iniciar outra.</translation>
    </message>
</context>
<context>
    <name>QFieldCloudExtension</name>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="194"/>
        <source>QFieldCloud Settings...</source>
        <translation>Configurações QFieldCloud...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="226"/>
        <source>Export filtered layers to QFieldCloud</source>
        <translation>Exportar camadas filtradas para QFieldCloud</translation>
    </message>
</context>
<context>
    <name>QFieldCloudPushDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="102"/>
        <source>Export to QFieldCloud</source>
        <translation>Exportar para QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="117"/>
        <source>Active Filter</source>
        <translation>Filtro ativo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="120"/>
        <source>No active filter</source>
        <translation>Sem filtro ativo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="121"/>
        <source>Filter:</source>
        <translation>Filtro:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="123"/>
        <source>0 layers</source>
        <translation>0 camadas</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="124"/>
        <source>Layers:</source>
        <translation>Camadas:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="130"/>
        <source>QFieldCloud Project</source>
        <translation>Projeto QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="135"/>
        <source>Project name:</source>
        <translation>Nome do projeto:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="139"/>
        <source>Description:</source>
        <translation>Descrição:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="143"/>
        <source>Create new</source>
        <translation>Criar novo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="144"/>
        <source>Update existing:</source>
        <translation>Atualizar existente:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="148"/>
        <source>Mode:</source>
        <translation>Modo:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="158"/>
        <source>Layer Modes</source>
        <translation>Modos de camada</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Layer</source>
        <translation>Camada</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Mode</source>
        <translation>Modo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="184"/>
        <source>Export</source>
        <translation>Exportar</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="209"/>
        <source>{0} layers ({1} features)</source>
        <translation>{0} camadas ({1} feições)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="217"/>
        <source>{0} layers (no filter active)</source>
        <translation>{0} camadas (sem filtro ativo)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Missing Name</source>
        <translation>Nome ausente</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Please enter a project name.</source>
        <translation>Por favor, insira um nome de projeto.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>Not Connected</source>
        <translation>Não conectado</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>QFieldCloud is not connected. Please configure credentials first.</source>
        <translation>QFieldCloud não está conectado. Configure as credenciais primeiro.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No Layers</source>
        <translation>Sem camadas</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No valid layers to export.</source>
        <translation>Nenhuma camada válida para exportar.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>Export Error</source>
        <translation>Erro de exportação</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="393"/>
        <source>Failed to export layer &apos;{0}&apos;: {1}</source>
        <translation>Failed to export layer '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>GPKG export failed: {0}</source>
        <translation>Exportação GPKG falhou: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="420"/>
        <source>Push complete!</source>
        <translation>Envio concluído!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project successfully pushed to QFieldCloud!</source>
        <translation>Projeto enviado com sucesso para QFieldCloud!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project: {0}</source>
        <translation>Projeto: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Files: {0}</source>
        <translation>Arquivos: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Duration: {0:.1f}s</source>
        <translation>Duração: {0:.1f}s</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>URL: {0}</source>
        <translation>URL: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="438"/>
        <source>Warnings:</source>
        <translation>Avisos:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="440"/>
        <source>Push Complete</source>
        <translation>Envio concluído</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="450"/>
        <source>Error: {0}</source>
        <translation>Erro: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push Failed</source>
        <translation>Falha no envio</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push failed:

{0}</source>
        <translation>Falha no envio:

{0}</translation>
    </message>
</context>
<context>
    <name>QFieldCloudSettingsDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="53"/>
        <source>QFieldCloud Configuration</source>
        <translation>Configuração QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="66"/>
        <source>Server</source>
        <translation>Servidor</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="71"/>
        <source>URL:</source>
        <translation>URL:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="77"/>
        <source>Credentials</source>
        <translation>Credenciais</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="81"/>
        <source>username</source>
        <translation>nome de utilizador</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="82"/>
        <source>Username:</source>
        <translation>Nome de utilizador:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="86"/>
        <source>password (for initial login)</source>
        <translation>senha (para login inicial)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="87"/>
        <source>Password:</source>
        <translation>Senha:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="90"/>
        <source>JWT token (auto-filled after login)</source>
        <translation>Token JWT (preenchido automaticamente após login)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="95"/>
        <source>Login</source>
        <translation>Entrar</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="96"/>
        <source>Login with username/password to get a token</source>
        <translation>Entrar com utilizador/senha para obter um token</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="98"/>
        <source>Token:</source>
        <translation>Token:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="102"/>
        <source>Status:</source>
        <translation>Estado:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="105"/>
        <source>Test Connection</source>
        <translation>Testar conexão</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="112"/>
        <source>Preferences</source>
        <translation>Preferências</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="117"/>
        <source>Default project:</source>
        <translation>Projeto padrão:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="119"/>
        <source>Trigger packaging after upload</source>
        <translation>Acionar empacotamento após o envio</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="144"/>
        <source>Token stored</source>
        <translation>Token armazenado</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Missing Fields</source>
        <translation>Campos ausentes</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Please fill in URL, username, and password.</source>
        <translation>Por favor, preencha URL, utilizador e senha.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="174"/>
        <source>Logging in...</source>
        <translation>Entrando...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="191"/>
        <source>Logged in as {0}</source>
        <translation>Conectado como {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="198"/>
        <source>Login failed: {0}</source>
        <translation>Falha no login: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Missing Configuration</source>
        <translation>Configuração ausente</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Please configure URL and login first.</source>
        <translation>Configure a URL e faça login primeiro.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="219"/>
        <source>Testing connection...</source>
        <translation>Testando conexão...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="229"/>
        <source>Connected! ({0} projects accessible)</source>
        <translation>Conectado! ({0} projetos acessíveis)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="235"/>
        <source>Connection failed: {0}</source>
        <translation>Falha na conexão: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Missing URL</source>
        <translation>URL ausente</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Server URL is required.</source>
        <translation>A URL do servidor é obrigatória.</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxFeaturesListPickerWidget</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="924"/>
        <source>Type to filter...</source>
        <translation>Escreva para filtrar...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>Selecionar tudo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>Selecionar tudo (sem subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>Selecionar tudo (subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>Desselecionar tudo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>Desselecionar tudo (sem subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>Desselecionar tudo (subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>A mostrar as primeiras {0} entidades ordenadas por valor de visualização. Escreva no filtro de texto para pesquisar em toda a camada; &quot;Selecionar tudo&quot; carrega a lista completa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>A mostrar {0} entidades da camada, ordenadas por valor de visualização. Escreva no filtro de texto para pesquisar em toda a camada; &quot;Selecionar tudo&quot; carrega a lista completa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>Resultados da pesquisa de &quot;{0}&quot; em toda a camada.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1768"/>
        <source>Loading values…</source>
        <translation>A carregar valores…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>Values</source>
        <translation>Valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Esta expressão não pode ser avaliada de forma segura para um serviço.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1748"/>
        <source>Selection</source>
        <translation>Seleção</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1748"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>A lista remota excede o limite de seleção segura. Selecione menos entidades ou filtre primeiro a camada.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1924"/>
        <source>Loading selected values…</source>
        <translation>A carregar os valores selecionados…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>Selecionar tudo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>Desselecionar tudo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Selecionar todas as camadas por tipo de geometria (Linhas)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Desselecionar todas as camadas por tipo de geometria (Linhas)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Selecionar todas as camadas por tipo de geometria (Pontos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Desselecionar todas as camadas por tipo de geometria (Pontos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Selecionar todas as camadas por tipo de geometria (Polígonos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Desselecionar todas as camadas por tipo de geometria (Polígonos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>Selecionar todas as camadas raster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>Desselecionar todas as camadas raster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>Selecionar todas as camadas de nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>Desselecionar todas as camadas de nuvem de pontos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>píxeis na zona</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>pontos na zona</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>feições</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>Alvo raster: os píxeis fora da geometria de origem passam a NoData (os de dentro com Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>Alvo nuvem de pontos: os pontos fora da geometria de origem são removidos (os de dentro com Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>Alvo vetorial: as feições que satisfazem o predicado geométrico são mantidas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>Clique no quadrado à direita para testar esta camada pelos seus centroides</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="343"/>
        <source>Select all vector layers</source>
        <translation>Selecionar todas as camadas vetoriais</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="345"/>
        <source>De-select all vector layers</source>
        <translation>Desselecionar todas as camadas vetoriais</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>Histograma do intervalo de valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>Arraste as alças, ou clique, para escolher o intervalo de valores a manter</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>Sem histograma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>Valores mantidos de {0} a {1}</translation>
    </message>
</context>
<context>
    <name>RasterExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="497"/>
        <source>Band</source>
        <translation type="obsolete">Banda</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="500"/>
        <source>Band whose values are selected</source>
        <translation type="obsolete">Banda cujos valores são selecionados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">VALOR DO PÍXEL</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">Valor do píxel da banda atual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">Últimos {0} valores escolhidos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">Clique no mapa com o seletor de píxeis. Ctrl+clique alarga o intervalo até ao valor.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>INTERVALO DE VALORES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>Mín</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>Valor mais baixo mantido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>Máx</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>Valor mais alto mantido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">Pré-visualização no mapa (ocultar os outros píxeis)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">CLASSES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">Classes do raster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">Nenhuma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>EXPRESSÃO RASTER</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>Expressão da calculadora raster; um píxel é mantido onde não é 0</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>Expressão raster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">Utilizar o intervalo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">Escrever o intervalo de valores atual como expressão</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">Píxeis selecionados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>Defina primeiro um intervalo de valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2219"/>
        <source>NoData</source>
        <translation>NoData</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="834"/>
        <source>Last values:</source>
        <translation type="obsolete">Últimos valores:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="629"/>
        <source>Value of the current band under the cursor</source>
        <translation type="obsolete">Valor da banda atual sob o cursor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">Estatísticas da banda atual no último retângulo desenhado no mapa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>Sob o cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>Zona: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>nenhum píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>ÚLTIMAS LEITURAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">Calcular sobre</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">Grandeza a que o intervalo se aplica. O declive, a orientação, o sombreamento e a rugosidade leem a banda como um MDT.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>Valor do píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>Declive (graus)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>Declive (%)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>Orientação (graus)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>Sombreamento (0-255)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>Rugosidade (TRI, diferença média)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>Limiares habituais da grandeza</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">Limiares habituais</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>Plano</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>Suave</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>Moderado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>Íngreme</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>Este</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>Sul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>West</source>
        <translation>Oeste</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Shadow</source>
        <translation>Sombra</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Lit</source>
        <translation>Iluminado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">Limiares habituais…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>CONTA-GOTAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>Tolerância ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>Tolerância em torno da cor ou do valor escolhido, em % do intervalo de valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>Tolerância do conta-gotas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>Bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">O que são as bandas da imagem: as predefinições e o conta-gotas utilizam-nas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">Disposição das bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB (vermelho, verde, azul)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC (infravermelho, vermelho, verde)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + infravermelho</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">Escrever a expressão de um índice habitual (vegetação, água...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">Predefinições espetrais</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">Requer uma imagem de três bandas ou mais (vermelho, verde, azul...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>Vegetação (NDVI &gt; 0.3)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>Sem vegetação (NDVI &lt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>Água (NDWI &gt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>Vegetação (excesso de verde)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">Predefinições espetrais…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>Este píxel não tem valor (NoData): escolha outro</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>A tolerância abrange todos os valores: reduza-a</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">Intervalo {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">Classe(s) {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} cor(es), última: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">Expressão</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>BANDAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>Valor da banda ativa sob o cursor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>Estatísticas da banda ativa no último retângulo desenhado no mapa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>Todas as bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>O intervalo de valores aplica-se a todas as bandas de cor em simultâneo (um píxel é mantido quando cada banda está dentro do intervalo); o histograma mostra a primeira</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>Banda ativa: a que o intervalo, o histograma e o seletor leem</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>O conta-gotas compara esta banda</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>Cor que a banda contém: os índices espectrais e os chips usam-na. Clique para a alterar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>Valor no último clique do conta-gotas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>Nenhuma cor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>As bandas 1, 2, 3 são vermelho, verde, azul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>IRC</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>As bandas 1, 2, 3 são infravermelho, vermelho, verde (ortofoto de cor infravermelha do IGN)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>As bandas 1, 2, 3, 4 são vermelho, verde, azul, infravermelho próximo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>Todas as bandas: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> Funções presumidas, a confirmar.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1019"/>
        <source>R</source>
        <translation>R</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1019"/>
        <source>G</source>
        <translation>G</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1019"/>
        <source>B</source>
        <translation>B</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1020"/>
        <source>NIR</source>
        <translation>NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Red</source>
        <translation>Vermelho</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Green</source>
        <translation>Verde</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Blue</source>
        <translation>Azul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1024"/>
        <source>Near infrared</source>
        <translation>Infravermelho próximo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>funções presumidas, a confirmar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>Selecionar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>Píxeis semelhantes</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>Todos os píxeis do raster próximos da cor ou do valor escolhido (o conta-gotas da barra lateral)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>Objeto clicado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>Apenas a mancha desses píxeis onde cai o clique: uma piscina, um telhado, um campo (o detetor de objetos da barra lateral); Ctrl+clique adiciona outro objeto</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>Objetos semelhantes</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>Todos os objetos do raster semelhantes ao clicado: as manchas desses píxeis cuja área está dentro das proporções abaixo (a ferramenta de objetos semelhantes da barra lateral); Ctrl+clique adiciona outro objeto de referência</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>Área ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Menor objeto semelhante, como proporção do menor dos clicados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Maior objeto semelhante, como múltiplo do maior dos clicados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>a ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>mesma forma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>Manter apenas os objetos com a forma dos clicados: a sua compacidade (4π × área / perímetro², 1 para um disco) dentro das mesmas proporções; desativado, uma estrada com a área de uma piscina é uma piscina</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>Remover esta seleção de valor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>Grandeza</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>Grandeza a que se aplica o intervalo. Declive, exposição, sombreamento e rugosidade leem a banda ativa como um MDT.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>Limiares ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>Inserir ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>Insere uma referência de banda, um índice espectral habitual ou o intervalo atual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>Índices espectrais</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>Intervalo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>O intervalo de valores atual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>As cores renderizadas dependem do estilo e da escala.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>Só está disponível a seleção por cor: as bandas numéricas, os índices, os intervalos, as classes e os derivados não estão disponíveis.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>INTERVALO DE VALORES — todas as bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>INTERVALO DE VALORES — banda {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>seleciona em: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>Um declive, exposição... lê uma banda como um MDT: escolha primeiro uma banda em BANDAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>Não foi possível ler o objeto</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>Nenhum objeto sob o clique: aumente a tolerância ou clique noutro píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>Um objeto é maior do que a janela lida e foi cortado: reduza a tolerância</translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>falhou a captura raster limitada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="224"/>
        <source>local raster capture could not be opened</source>
        <translation>não foi possível abrir a captura raster local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="213"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>a análise raster requer uma captura GDAL local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>captura raster cancelada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>o destino da captura raster tem de estar na cache da sessão</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>não foi possível clonar o fornecedor da captura raster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>a captura raster requer uma extensão finita e não vazia</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>a captura raster requer um limite de píxeis positivo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>a captura raster requer uma resolução positiva</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <source>raster capture source could not be opened</source>
        <translation>não foi possível abrir a origem da captura raster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>a materialização do raster tem de ser executada num thread de trabalho</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="208"/>
        <source>raster selection canceled</source>
        <translation>seleção raster cancelada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="216"/>
        <source>raster selection source could not be opened</source>
        <translation>não foi possível abrir a origem da seleção raster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="204"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>a seleção raster remota tem de ser executada num thread de trabalho</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="210"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>a seleção de cor renderizada requer uma captura renderizada local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>os rasters renderizados requerem uma captura de cor renderizada</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: estatísticas do raster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>Falha na amostra raster; tente novamente com uma extensão visível mais pequena.</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: pré-visualização do raster</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="459"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>o alvo raster remoto tem de ser executado num thread de trabalho</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="470"/>
        <source>local raster target could not be opened</source>
        <translation>não foi possível abrir o alvo raster local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="480"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>As camadas de cor renderizada não podem ser alvos do filtro.</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Aplicar otimizações?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Otimizações disponíveis</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Pular</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Aplicar selecionados</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} elementos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Impacto: {0}</translation>
    </message>
</context>
<context>
    <name>RemoteMaterializer</name>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1000"/>
        <source>Partial result: the remote feature limit was reached.</source>
        <translation>Resultado parcial: foi atingido o limite de entidades remotas.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>Resultado parcial: foi atingido o limite de tempo remoto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>A filtragem remota foi cancelada; o filtro anterior é mantido.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>Seriam enviadas mais de 500 chaves para o serviço; reduza a seleção ou utilize uma cópia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>O serviço não tem uma chave estável; utilize uma cópia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>Selecione ou filtre a origem remota antes da filtragem espacial.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>Não é possível provar que o filtro do serviço está completo. Selecione entidades de origem ou utilize uma cópia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>A cópia da origem remota está incompleta; o filtro anterior é mantido.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>Resultado parcial: nenhuma entidade correspondente foi confirmada antes do limite; o filtro anterior é mantido.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>A cópia remota que interseta está incompleta; não é possível calcular com segurança um filtro disjunto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Disjoint combinado com outro predicado requer uma cópia local do alvo remoto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>Não foi possível avaliar o predicado espacial remoto; o filtro anterior é mantido.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>Não foi possível ler ou filtrar a cópia remota; o filtro anterior é mantido.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="93"/>
        <source>Remote materialization requires a background task.</source>
        <translation>A materialização remota requer uma tarefa em segundo plano.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="566"/>
        <source>Filtering a bounded remote copy</source>
        <translation>A filtrar uma cópia remota limitada</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: instantâneo de cor renderizada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>Falha no instantâneo renderizado; tente novamente com uma extensão visível mais pequena.</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Pesquisar configuração... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>Sem correspondência</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="242"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>Uma tarefa do FilterMate ainda está a ler camadas. Tente novamente quando terminar.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="255"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>Uma camada com armazenamento auxiliar não pode substituir com segurança o seu fornecedor de servidor. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="260"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>Uma junção remota não pode ser reconstruída no thread principal. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="262"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>Já está a ser preparado um filtro de servidor para esta camada.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="250"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>Uma camada de servidor só pode ser modificada no thread a que pertence.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="235"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>Os filtros de servidor assíncronos requerem o QGIS 3.32 ou posterior. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="368"/>
        <source>Could not install the prepared server filter.</source>
        <translation>Não foi possível instalar o filtro de servidor preparado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="44"/>
        <source>Could not preserve the layer state.</source>
        <translation>Não foi possível preservar o estado da camada.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="239"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>Termine a edição da camada antes de aplicar um filtro de servidor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>Expressão de atributos inválida.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="83"/>
        <source>Preparing server attribute filter</source>
        <translation>A preparar o filtro de atributos do servidor</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>O QGIS não consegue traduzir este predicado para um filtro OGC.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="302"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="311"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>Filtro de servidor cancelado ou com tempo esgotado. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="348"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>A instalação do filtro de servidor falhou e não foi possível restaurar o fornecedor anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="340"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>A instalação do filtro de servidor falhou. O fornecedor anterior já era inválido e não foi possível restaurá-lo.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="355"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>A instalação do filtro de servidor falhou. O fornecedor anterior foi restaurado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="33"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>A instalação do filtro de servidor está em curso. Tente novamente quando terminar.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="207"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="237"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>A instalação do filtro de servidor tem de ser iniciada no thread da camada.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>A expressão é demasiado complexa para ser traduzida com segurança.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>A expressão é demasiado grande ou contém sequências de escape SQL com barra invertida ambíguas.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="318"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>A camada mudou enquanto o seu filtro era preparado. O resultado preparado foi descartado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="366"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>A camada já não está disponível. O filtro preparado foi descartado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="311"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>O servidor rejeitou o filtro ou não foi possível contactá-lo. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="253"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>Este fornecedor e esta versão do QGIS não suportam a criação verificada de workers. O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: o filtro de atributos não pode ser executado inteiramente no servidor. Parte não suportada: {1}. {2} O filtro anterior não foi alterado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="265"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: o fornecedor rejeitou o filtro de atributos. O filtro anterior foi restaurado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="264"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: o fornecedor rejeitou o filtro e a restauração falhou.</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Favoritos partilhados</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Favoritos partilhados&lt;/b&gt; — descobertos em coleções QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">Pesquisar por nome, descrição, coleção ou etiquetas…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Selecione um favorito partilhado para pré-visualizar.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>Reanalisar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>Criar fork no meu projeto</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>Fechar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Nenhuma coleção partilhada encontrada. Subscreva um repositório Resource Sharing que contenha uma pasta &lt;code&gt;filter_mate/favorites&lt;/code&gt;, ou coloque um pacote &lt;code&gt;.fmfav.json&lt;/code&gt; na sua pasta de coleções resource_sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} favorito(s) em {1} coleção(ões): {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>Coleção: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">Nenhum favorito partilhado corresponde à pesquisa.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — de &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Expressão&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Camadas remotas&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Etiquetas:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Proveniência&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>Autor: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>Licença: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>Criar fork do favorito partilhado</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>Nome no seu projeto:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>Fork bem-sucedido</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» foi adicionado aos seus favoritos.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>Falha no fork</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Não foi possível adicionar o favorito partilhado ao seu projeto.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>Pesquisar por nome, descrição, coleção, autor ou etiquetas...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>Autor:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>Todos os autores</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>Nenhum favorito partilhado corresponde aos seus filtros.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>Repor valores predefinidos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>Erro de validação</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>Por favor, corrija os seguintes erros:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>Repor configuração</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>Repor todos os valores para os predefinidos?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate – Aviso de tipo PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Incompatibilidade de tipo no filtro: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>Repor valores predefinidos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>Geral</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>Não foi possível aplicar o filtro de {0}; mantém o filtro anterior.</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} elementos visíveis na camada principal</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Todos os filtros removidos – {count} elementos visíveis na camada principal</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Filtro aplicado a '{layer_name}': {count} elementos</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Filtro removido de '{layer_name}': {count} elementos visíveis</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="936"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Nenhuma entidade selecionada! O widget de seleção perdeu o elemento. Selecione novamente uma entidade.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1054"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>A camada selecionada é inválida ou a sua fonte não pode ser encontrada. Operação cancelada.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1069"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>A camada '{0}' ainda não está inicializada. Tente selecionar outra camada e depois volte a esta.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Não é possível desfazer: camada inválida ou fonte não encontrada.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Não é possível refazer: camada inválida ou fonte não encontrada.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>O fornecedor rejeitou o filtro guardado.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>Não foi possível restaurar o filtro: {0}</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="572"/>
        <source>Explore ...</source>
        <translation>Explorar ...</translation>
    </message>
</context>
<context>
    <name>VectorTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="261"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: sem campo de chave única, as suas entidades não podem ser listadas no respetivo filtro (um serviço web, ou uma camada virtual sem coluna de id única).</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="362"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>{0} entidades a listar, mais do que as {1} enviadas para um serviço web: reduza a origem ou utilize um filtro por atributos.</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>A cobertura mínima não está disponível para objetos de mosaicos recortados</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>Os alvos de mosaicos vetoriais só suportam os predicados Intersect e Disjoint</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>A filtragem de mosaicos vetoriais requer um código de autoridade do SRC</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>Filtro de visualização de mosaicos vetoriais: os atributos dependem do zoom; os objetos divididos entre mosaicos podem diferir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>O estilo dos mosaicos vetoriais mudou enquanto o filtro era executado; tente novamente</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>Filtrar os atributos dos mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>Expressão de filtro de mosaicos vetoriais inválida</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>Expressão QGIS (os atributos dependem do zoom):</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>Refazer o filtro de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>Apenas o alvo. Os atributos dependem do zoom. Os objetos divididos entre mosaicos podem ser filtrados de forma diferente.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>O estilo de mosaicos vetoriais guardado é inválido</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>A propriedade de símbolo de mosaicos vetoriais guardada é inválida</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>A seleção de mosaicos excede o orçamento de expressão (1 MB); utilize uma área mais pequena</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>A seleção de mosaicos excede o orçamento de vértices (2000); utilize uma área mais pequena</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>O filtro de mosaicos vetoriais excede o orçamento de expressão (1 MB)</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>O filtro de mosaicos vetoriais excede o orçamento total de expressões do estilo (1 MB); utilize uma área mais pequena</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>Anular o filtro de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>Desfiltrar mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>Filtro de atributos de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="111"/>
        <source>Vector tile favorite</source>
        <translation>Favorito de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>Filtro de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>A filtragem de mosaicos vetoriais requer um renderizador básico</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>A filtragem de mosaicos vetoriais requer uma rotulagem básica</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>Filtros de mosaicos vetoriais</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>Mosaicos vetoriais</translation>
    </message>
</context>
<context>
    <name>self.dockwidget</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="664"/>
        <source>Language changed to &apos;{0}&apos;.</source>
        <translation type="obsolete">Idioma alterado para '{0}'.</translation>
    </message>
</context>
<context>
    <name>self.self</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="735"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation type="obsolete">Geometria de origem: as feições selecionadas em EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">Geometria de origem: os píxeis selecionados, vetorizados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">Pontos mantidos</translation>
    </message>
</context>
</TS>
