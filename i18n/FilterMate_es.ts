<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="es_ES" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>Importar desde Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Publicar en Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>Publicar (sin favoritos guardados)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>Publicación rápida en el repositorio predeterminado</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>Administrar repositorios de Resource Sharing...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Filtros corruptos eliminados de {0} capa(s). Vuelva a aplicar sus filtros.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Proyecto vacío detectado. Añada capas vectoriales para activar el complemento.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>No se puede acceder a la base de datos de FilterMate. Compruebe los permisos del directorio del proyecto.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>Error durante la verificación de la base de datos: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Error al cargar la capa. Use F5 para forzar la recarga.</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: este servicio web no tiene un campo de clave única (clave declarada, id, gml_id, cleabs, objectid...), por lo que las entidades seleccionadas no se pueden enumerar para el servidor.</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: esta capa no tiene un campo de clave única y los identificadores de sus entidades no se pueden enumerar en su filtro (una capa virtual necesita una columna de id única, su uid).</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: {1} entidades seleccionadas, más de las {2} que se envían a un servicio web. Reduzca la selección o utilice un filtro por atributos.</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>Archivo remoto: cada lectura pasa por la red. FilterMate no cuenta sus entidades en el hilo principal.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>Servicio remoto: el filtro se envía al servidor cuando este puede traducirlo. FilterMate no cuenta sus entidades en el hilo principal.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>Un filtro por lista de entidades está limitado a {0} entidades.</translation>
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
        <translation>Seleccionar backend:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>Automático (Predeterminado)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Selección automática óptima para todas las capas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>Forzar {0} para todas las capas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>Clic para recargar las capas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>Clic para cambiar el backend</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>Probar los objetivos de línea y polígono marcados por sus centroides (punto sobre la superficie): más rápido con geometrías grandes. Cada objetivo tiene su propio cuadrado en la lista</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>Los centroides se aplican a los objetivos de línea y polígono: marque uno en la lista de capas a filtrar</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Error al cancelar los cambios: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>Error de propiedad: {0}</translation>
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
        <translation>{0} puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>Geometría de origen: los píxeles seleccionados, vectorizados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="792"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>Geometría de origen: la huella de los puntos conservados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="739"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation>Geometría de origen: las entidades seleccionadas en EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">Valor bajo el cursor: seguir el valor del píxel de la banda actual al recorrer el mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">Estadísticas de un rectángulo: arrastrar en el mapa para leer el mínimo, el máximo y la media de la banda actual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>Perfil de elevación: abrir el perfil de elevación de QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>Vista 3D: abrir una nueva vista de mapa 3D de QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">ninguna entidad</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} entidad(es)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">todos los píxeles</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} clase(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>expresión</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} entidades</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Vector</source>
        <translation>Vectorial</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Raster</source>
        <translation>Ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Point cloud</source>
        <translation>Nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="795"/>
        <source>Kept points</source>
        <translation>Puntos conservados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Selection → source geometry</source>
        <translation>Selección → geometría de origen</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>Vincular el rango al estilo: los colores de la capa se extienden sobre el rango elegido</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Cuentagotas de clases: haga clic en el mapa y se marca la clase de los puntos dibujados allí. Ctrl+clic añade otra</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>Valor bajo el cursor: seguir el valor del píxel (o la pendiente, la orientación... a la que se aplica el rango) al recorrer el mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>Estadísticas de un rectángulo: arrastrar en el mapa para leer el mínimo, el máximo y la media de la banda actual (o de la pendiente, la orientación... a la que se aplica el rango)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>El vínculo de estilo sigue los valores de los píxeles: no disponible mientras el rango se aplica a una pendiente, orientación, sombreado o rugosidad</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="920"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>Cuentagotas de clases: esta nube de puntos no tiene el atributo Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1526"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>El estilo no puede seguir el rango: necesita un estilo de una sola banda en gris o pseudocolor sobre la banda del panel</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>Cuentagotas: haga clic en el mapa y se seleccionan los píxeles que se parecen al que ha pulsado (un color en una imagen, un valor en un MDT o un índice, una clase en un ráster clasificado, con la tolerancia del panel). Ctrl+clic añade otro</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>ninguna entidad seleccionada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>toda la capa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>sin restricción</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>expresión ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>todos los puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} objeto(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>mostrados como la clase completa en su recuadro</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>Detector de objetos: haga clic en el mapa y se selecciona la mancha de píxeles parecidos al que se pulsa (una piscina, un tejado, un campo, con la tolerancia del panel), no todos los píxeles de su color. Ctrl+clic añade otro objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>Objetos similares: haga clic en un objeto y se seleccionan todos los objetos del ráster parecidos a él (las manchas de esos píxeles cuya área está dentro de las proporciones del panel). Ctrl+clic añade otro objeto de referencia</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>Detector de objetos: haga clic en el mapa y se selecciona el objeto bajo el clic (el grupo de puntos de su clase: un edificio, un árbol), no toda la clase; o todos los objetos de la nube parecidos a él (clic derecho en el botón para el objetivo). Ctrl+clic añade otro objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>Cuentagotas de valor: haga clic en el mapa y se escribe una condición sobre el atributo elegido en ATRIBUTOS (Z, intensidad...), alrededor del valor del punto en ese lugar, con la tolerancia del panel. Ctrl+clic añade otra condición (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>Zona: dibuje un rectángulo, un polígono, una forma a mano alzada o un círculo en el mapa (clic derecho en el botón para la forma); su recuadro X / Y va a ATRIBUTOS, la forma en sí recorta los objetivos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>Más herramientas: el valor bajo el cursor, las estadísticas de un rectángulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>Entidades similares: haga clic en una entidad y se seleccionan todas las entidades de la capa con el mismo valor del campo del grupo (la expresión de visualización de la selección simple / múltiple). Ctrl+clic añade otro valor</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>Más herramientas: las herramientas de selección de QGIS (rectángulo, polígono, mano alzada, radio), seleccionar por expresión, invertir o borrar la selección, la tabla de atributos de la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>Más herramientas: el perfil de elevación y la vista 3D de QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>Solo está disponible la selección por color: los colores renderizados dependen del estilo y de la escala.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>El vínculo de estilo sigue al grupo RANGO DE VALORES: actívelo primero</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="794"/>
        <source>Current filter: {0}</source>
        <translation>Filtro actual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="830"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>Los colores renderizados dependen del estilo y de la escala.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="929"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>Detector de objetos: esta nube de puntos no tiene el atributo Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="978"/>
        <source>Object detector</source>
        <translation>Detector de objetos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Clicked object</source>
        <translation>Objeto seleccionado con el clic</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Similar objects</source>
        <translation>Objetos similares</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1085"/>
        <source>Zone shape</source>
        <translation>Forma de la zona</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Rectangle</source>
        <translation>Rectángulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Polygon</source>
        <translation>Polígono</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Freehand</source>
        <translation>Mano alzada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Radius</source>
        <translation>Radio</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1134"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>El vínculo sigue las selecciones simple y múltiple: active primero una de ellas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1257"/>
        <source>Select on the map</source>
        <translation>Seleccionar en el mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Select by expression…</source>
        <translation>Seleccionar por expresión…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Invert the selection</source>
        <translation>Invertir la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Clear the selection</source>
        <translation>Borrar la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1272"/>
        <source>Attribute table of the selection</source>
        <translation>Tabla de atributos de la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Value under the cursor</source>
        <translation>Valor bajo el cursor</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1315"/>
        <source>Statistics of a rectangle</source>
        <translation>Estadísticas de un rectángulo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>Elevation profile</source>
        <translation>Perfil de elevación</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>3D view</source>
        <translation>Vista 3D</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1688"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>Esta nube de puntos no tiene atributo X / Y por el que filtrar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="559"/>
        <source>To link the range to the style, choose Layer style in Map display</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>CoverageModeController</name>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="365"/>
        <source>Restoring the filter of {0} raster / point cloud layer(s)…</source>
        <translation>Restaurando el filtro de {0} capa(s) ráster / nube de puntos…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>cob. ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>Proporción mínima de un objetivo poligonal dentro de la geometría de origen (0 = cualquier solapamiento). Se usa cuando el origen es un ráster o una nube de puntos.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>Ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>Nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>Capa {0}: selección en EXPLORING, relación en FILTERING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">Selector de píxeles: haga clic en el mapa para leer el valor de cada banda (Ctrl+clic amplía el rango)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>Ampliar a la capa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">Vista previa: ocultar los píxeles fuera de la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>No se usa para capas ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>Restablecer la selección ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">Identificar puntos en el mapa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>Vista previa en vivo: mostrar solo los puntos conservados por la selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>No se usa para capas de nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>Restablecer los criterios de la nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>Expresión de la calculadora ráster no válida</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>No se encontró PDAL: la altura sobre un MDT requiere el ejecutable pdal</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3151"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>Una tarea de FilterMate sigue en ejecución: espere a que termine</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>La tarea de FilterMate falló: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>Seleccione primero los píxeles: un rango de valores, clases o una expresión ráster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>Ráster filtrado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>Se rechazó la expresión de la nube de puntos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>Seleccione primero los puntos: clases, rangos de atributos o una expresión</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>Nube de puntos filtrada: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3261"/>
        <source>Filter not applied: {0}</source>
        <translation>Filtro no aplicado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>canceled</source>
        <translation>cancelado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>{0} objetivo(s) filtrado(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2823"/>
        <source>{0} failed: {1}</source>
        <translation>{0} falló: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2836"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: filtrando desde '{0}'…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2933"/>
        <source>Changed since, left as is: {0}</source>
        <translation>Modificada desde entonces, se deja como está: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2939"/>
        <source>{0} layer(s) restored</source>
        <translation>{0} capa(s) restaurada(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2973"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>'{0}' no exportada: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2987"/>
        <source>Exported: {0}</source>
        <translation>Exportado: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2989"/>
        <source>Export failed: {0}</source>
        <translation>Error de exportación: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2996"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>Exportando {0} capa(s)…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3002"/>
        <source>Export folder</source>
        <translation>Carpeta de exportación</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3084"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>Objetivos ráster / nube de puntos omitidos: ninguna entidad de origen seleccionada en EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>Objetivos ráster / nube de puntos no filtrados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3115"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>{0} objetivo(s) ráster / nube de puntos filtrado(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3238"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>Elija el ráster MDT utilizado para la altura sobre el suelo</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3249"/>
        <source>Height above ground not computed: {0}</source>
        <translation>Altura sobre el suelo no calculada: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3270"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>Calculando la altura sobre '{0}' con PDAL…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>La caché de FilterMate ocupa {0} GB, por encima de su límite de {1} GB: quite el filtro de las capas ráster / nube de puntos que ya no necesite</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>PDAL {0} es demasiado antiguo: la altura sobre un MDT requiere PDAL 2.4 o posterior</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>No se pudo ejecutar PDAL, la altura sobre un MDT no está disponible: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">Selector de píxeles: haga clic en el mapa para leer el valor de cada banda, y la pendiente, la orientación... cuando el rango se aplica a una de ellas (Ctrl+clic amplía el rango)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>Ampliar a los píxeles seleccionados (a la capa si no hay nada seleccionado)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>Vista previa: ocultar los píxeles fuera de la selección (un velo blanco para una pendiente, orientación...)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>La vista previa de una pendiente o de una orientación requiere el mapa en el SRC del ráster ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>solo se pueden elegir los puntos dibujados en el mapa: desactive la vista previa para elegir una clase que oculta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>Ningún punto clasificado bajo el clic</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>La clase {0} ya está marcada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>La clase {0} no está en la lista de clases de la capa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>No se usa para capas ráster: el cuentagotas lee las bandas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Cuentagotas de clase: haga clic en el mapa y se marca la clase de los puntos dibujados allí. Ctrl+clic añade otra</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>La vista previa y las estadísticas usan una muestra local acotada de la extensión visible; el filtrado lee el origen.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>Preparando una instantánea de color acotada de la extensión visible…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>No se pudo preparar la instantánea de color. Pruebe con una extensión visible más pequeña.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>La selección por color se aplica a la extensión visible capturada.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>Error en el muestreo del ráster. Pruebe con una extensión visible más pequeña.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>No se pudo calcular la vista previa del ráster muestreado.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>La vista previa de un color o de una expresión requiere el mapa en el SRC del ráster ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>Ningún punto dibujado bajo el clic</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>Este punto no tiene {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>{0} no se puede usar en una condición</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>Objeto no leído: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>Demasiados puntos alrededor del clic: no se pudo leer el objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>Ningún punto de la clase {0} bajo el clic: haga clic sobre el propio objeto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>Objetos similares no leídos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>Ningún objeto similar dentro de las proporciones de área: amplíelas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>Preparando una muestra para la nueva extensión visible. Vuelva a hacer clic cuando esté lista.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>La muestra local del ráster aún se está preparando. Vuelva a intentarlo cuando esté lista.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>Prepare una instantánea de color antes de filtrar esta capa renderizada.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>{0} objetivo(s) ráster remuestreado(s) al límite de píxeles configurado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2847"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>selección por color limitada a la extensión capturada; los colores dependen del estilo y de la escala</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2849"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>origen ráster remuestreado a {0} celdas dentro del límite de píxeles</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>selección ráster leída cada {0} píxeles: por encima del límite de píxeles de los ajustes</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2854"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>selección ráster densa suavizada para mantener ligero su contorno</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2901"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0} vaciada(s), nada coincide con la selección: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2885"/>
        <source>failed</source>
        <translation>fallido</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1446"/>
        <source>No valid pixels to display in the selected bands.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1440"/>
        <source>Preparing band display…</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1319"/>
        <source>The selected bands could not be displayed.</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="234"/>
        <source>Database file does not exist: {0}</source>
        <translation>El archivo de base de datos no existe: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Error al conectar a la base de datos {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>No se pudo crear el directorio de base de datos {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Error al crear el archivo de base de datos {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>No se puede inicializar la base de datos de FilterMate: conexión fallida</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Error crítico al conectar a la base de datos: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>Error durante la inicialización de la base de datos: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>El archivo de base de datos no existe: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Error al conectar a la base de datos {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Módulo Processing de QGIS no disponible para crear el índice espacial</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>No se puede crear el índice espacial: capa no válida o fuente no encontrada.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>Se detectaron capas PostgreSQL pero psycopg2 no está instalado. Usando el backend Spatialite local. Para un mejor rendimiento con grandes conjuntos de datos, instale psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2481"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>{0} entidades seleccionadas, más de las {1} que se pueden enviar a un servicio web: reduzca la selección o utilice un filtro por atributos.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Guardar la capa en un archivo</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Seleccione una carpeta donde exportar sus capas</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>Guardar los datos exportados en un archivo ZIP</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0} capa(s)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> en {0} grupo(s)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} sin grupo</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>Destino: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Ningún grupo detectado: todas las capas están en el nivel raíz</translation>
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
        <translation>instale el complemento de QGIS {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>instale {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>La extensión {0} está desactivada porque falta {1}: {2} y reinicie QGIS.</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">Sin filtro</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>No hay filtro activo que guardar.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>Añadir favorito</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>Nombre del favorito:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Favorito '{0}' añadido correctamente</translation>
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
        <translation>Error al exportar los favoritos</translation>
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
        <translation>¿Fusionar con los favoritos existentes?

Sí = Añadir a los existentes
No = Reemplazar todos los existentes</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>{0} favoritos importados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>No se importaron favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Gestor de favoritos no inicializado. Reinicie FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>Diálogo del gestor de favoritos no disponible</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>Error: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">Usado {0} veces</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">Añadir filtro actual a favoritos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">Añadir filtro (sin filtro activo)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">Gestionar favoritos...</translation>
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
        <translation type="obsolete">Favoritos globales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">Copiar a globales...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── Favoritos globales disponibles ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(Sin favoritos globales)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">Mantenimiento</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">Guardar en proyecto (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">Restaurar desde proyecto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">Limpiar proyectos huérfanos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">Estadísticas de la base de datos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">Nombre inválido</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>El nombre del favorito no puede estar vacío.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>Nombre duplicado</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Ya existe un favorito llamado '{0}'.
¿Desea reemplazarlo?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>Favorito copiado a favoritos globales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>Error al copiar a favoritos globales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">Favoritos globales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0} favorito(s) global(es) disponible(s).

Los favoritos globales se comparten entre todos los proyectos.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>{0} favorito(s) guardado(s) en el archivo del proyecto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>Error al guardar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>{0} favorito(s) restaurado(s) desde el archivo del proyecto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>No se encontraron favoritos para restaurar en el proyecto</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0} proyecto(s) huérfano(s) limpiado(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>No hay proyectos huérfanos que limpiar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>Estadísticas de la base de datos FilterMate

Total de favoritos: {0}
   Proyecto: {1}
   Huérfanos: {2}
   Globales: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>Proyectos principales por favoritos:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>Estadísticas de FilterMate</translation>
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
        <translation type="obsolete">Aún no hay favoritos guardados.

Aplique un filtro a una capa, haga clic en el indicador ★ y elija «Añadir filtro actual a favoritos» para guardar su primer favorito.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">Importar desde Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">Publicar en Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">Publicar (sin favoritos guardados)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>El directorio de configuración de FilterMate aún no está inicializado: abra primero un proyecto QGIS con FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">La extensión Resource Sharing no está activa. Active 'favorites_sharing' en la configuración de FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">El servicio de favoritos compartidos no está disponible.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">Fallo del selector de favoritos compartidos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">Aún no tiene favoritos para publicar. Guarde primero un filtro mediante el menú ★.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">Error al abrir el diálogo de publicación: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>Los favoritos aún no están listos: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>No se pudo eliminar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>Aún no hay favoritos guardados — aplique un filtro y haga clic en el indicador ★ para guardar el primero.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>No se pudo abrir el administrador de favoritos. Detalles en filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>No se pudo reemplazar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>No se pudo guardar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>No se pudo importar el favorito global: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>No se pudo copiar a global: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>No se pudieron guardar los favoritos en el archivo del proyecto: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>No se pudieron limpiar los proyectos huérfanos. Detalles en filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>Las estadísticas de la base de datos no están disponibles. Detalles en filtermate.log.</translation>
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
        <translation>Buscar por nombre, expresión, etiquetas o descripción...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>General</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>Expresión</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>Remoto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>Nombre del favorito</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>Nombre:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Descripción (generada automáticamente, editable)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>Descripción:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Introduzca etiquetas separadas por comas (ej.: urbano, población, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Las etiquetas ayudan a organizar y buscar favoritos.
Separe varias etiquetas con comas.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>Etiquetas:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>Capa fuente:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>Proveedor:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>Usado:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>Creado:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Expresión de la capa fuente:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>Expresión de filtro para la capa fuente</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Capas remotas filtradas:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>Capa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>Entidades</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Sin capas remotas en este favorito&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>Aplicar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Aplicar este filtro favorito al proyecto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>Guardar cambios</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>Guardar las modificaciones de este favorito</translation>
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
        <translation>Cerrar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>Cerrar este diálogo</translation>
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
        <translation>¿Eliminar favorito '{0}'?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>Capas remotas</translation>
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
        <translation type="obsolete">Aún no hay favoritos guardados.

Haga clic en el indicador ★ y seleccione 'Añadir filtro actual a favoritos' para guardar su primer favorito.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>Compartidos…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Explorar favoritos compartidos a través de colecciones QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>Publicar…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Publicar favoritos seleccionados en una colección Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">No se pudo eliminar «{0}». El favorito sigue en la base de datos: consulte el registro de FilterMate para más detalles.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>Filtrar favoritos por ámbito (propietario × proyecto).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>Todos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>Compartidos · Todos los proyectos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>Compartidos · Este proyecto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>Míos · Todos los proyectos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>Míos · Este proyecto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>Míos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>Compartidos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>Este proyecto</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>Todos los proyectos</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>El ámbito del proyecto se establece al crear el favorito. Muévalo a través de la pestaña de filtrado (próximamente) para cambiar de proyecto.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>Visibilidad:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (compartido con todos)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (usted)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — seleccionar 'Míos' al guardar transferirá la propiedad a usted</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>No se pudo guardar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>No se pudo eliminar '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>'{0}' no estaba en la base de datos — actualice e inténtelo de nuevo.</translation>
    </message>
</context>
<context>
    <name>FeedbackModule</name>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="112"/>
        <source>Exporting {0} layer(s)</source>
        <translation>Exportando {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="168"/>
        <source>Large dataset ({0} features) using {1}. Consider using PostgreSQL for optimal performance.</source>
        <translation>Conjunto de datos grande ({0} entidades) con {1}. Considere usar PostgreSQL para un rendimiento óptimo.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="176"/>
        <source>Medium-large dataset ({0} features) using {1}. PostgreSQL recommended for better performance.</source>
        <translation>Conjunto de datos mediano-grande ({0} entidades) con {1}. Se recomienda PostgreSQL para un mejor rendimiento.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="113"/>
        <source>Processing {0} layer(s)</source>
        <translation>Procesando {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="110"/>
        <source>Removing filters from {0} layer(s)</source>
        <translation>Quitando los filtros de {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="111"/>
        <source>Resetting {0} layer(s)</source>
        <translation>Restableciendo {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="109"/>
        <source>Starting filter on {0} layer(s)</source>
        <translation>Iniciando el filtro en {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="137"/>
        <source>Successfully exported {0} layer(s)</source>
        <translation>{0} capa(s) exportada(s) correctamente</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="134"/>
        <source>Successfully filtered {0} layer(s)</source>
        <translation>{0} capa(s) filtrada(s) correctamente</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="138"/>
        <source>Successfully processed {0} layer(s)</source>
        <translation>{0} capa(s) procesada(s) correctamente</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="135"/>
        <source>Successfully removed filters from {0} layer(s)</source>
        <translation>Filtros quitados correctamente de {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="136"/>
        <source>Successfully reset {0} layer(s)</source>
        <translation>{0} capa(s) restablecida(s) correctamente</translation>
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
        <translation>Cambiar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>Seleccionar una carpeta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>Seleccionar un archivo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>Guardar en un archivo</translation>
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
        <translation>Cambiar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>Seleccionar un icono</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>La capa es inválida o no se puede encontrar su fuente. Operación cancelada.</translation>
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
        <translation>Abrir panel FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>Restablecer configuración y base de datos</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Restablecer la configuración predeterminada y eliminar la base de datos SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>Restablecer Configuración</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>Configuración restablecida correctamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>Archivo de configuración predeterminado no encontrado.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>Base de datos eliminada: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>Se requiere reinicio</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>Configuración obsoleta detectada</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>versión desconocida</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>Configuración dañada detectada</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Configuración no restablecida. Algunas funciones pueden no funcionar correctamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>Configuración creada con valores predeterminados</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Configuración dañada restablecida. Se han restaurado los ajustes predeterminados.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Configuración obsoleta restablecida. Se han restaurado los ajustes predeterminados.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>Configuración actualizada a la última versión</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Configuración actualizada: nuevos ajustes disponibles ({sections}). Acceso mediante el menú Opciones.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>Simplificación de geometría</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>Umbrales de optimización</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>Configuración de validación de geometría</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Filtrado de geometrías inválidas desactivado correctamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Filtrado de geometrías inválidas no modificado. Algunas entidades pueden excluirse de las exportaciones.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Se ha detectado una configuración obsoleta ({}).

¿Desea restablecer la configuración predeterminada?

• Sí: Restablecer (se creará una copia de seguridad)
• No: Mantener la configuración actual (puede causar problemas)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>El archivo de configuración está corrupto y no se puede leer.

¿Desea restablecer la configuración predeterminada?

• Sí: Restablecer (se creará una copia de seguridad si es posible)
• No: Cancelar (el plugin puede no funcionar correctamente)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>Restablecer configuración</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>La configuración necesita ser restablecida.

¿Desea continuar?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>Error durante la migración de configuración: {}</translation>
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
        <translation>¿Está seguro de que desea restablecer la configuración predeterminada?

Esto:
- Restaurará la configuración predeterminada
- Eliminará la base de datos de capas

QGIS debe reiniciarse para aplicar los cambios.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>La configuración se ha restablecido.

Reinicie QGIS para aplicar los cambios.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>Error de inicialización: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} capa(s) referenciada(s) no cargada(s) ({layers_list}). Se usa la visualización alternativa.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>No se puede eliminar {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">Error durante el restablecimiento: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;¡Gracias por usar &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Únase a nuestra comunidad de Discord para:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;Obtener ayuda y soporte&lt;/li&gt;&lt;li&gt;Reportar errores y problemas&lt;/li&gt;&lt;li&gt;Sugerir nuevas funcionalidades&lt;/li&gt;&lt;li&gt;Compartir consejos con otros usuarios&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  Únase a nosotros en Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>No mostrar de nuevo</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>Cerrar</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Error al cargar el complemento: {0}. Consulte la consola Python de QGIS para más detalles.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Current layer: {0}</source>
        <translation>Capa actual: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7418"/>
        <source>No layer selected</source>
        <translation>Ninguna capa seleccionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>Selected layers:
{0}</source>
        <translation>Capas seleccionadas:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>No layers selected</source>
        <translation>Ninguna capa seleccionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7448"/>
        <source>No expression defined</source>
        <translation>Ninguna expresión definida</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7460"/>
        <source>Display expression: {0}</source>
        <translation>Expresión de visualización: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7477"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>ID de entidad: {0}
Primer atributo: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>No se pudo restablecer la configuración. Compruebe que la carpeta del complemento tenga permiso de escritura e inténtelo de nuevo. Detalles en filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>Novedades de FilterMate 5</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;FilterMate ahora trabaja con capas ráster y de nubes de puntos.&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; se adapta a la capa actual: rango de valores y clases de un ráster, clases, elevación y atributos de una nube de puntos LiDAR.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relaciona esa selección con capas de cualquier tipo, con los predicados y el búfer habituales: parcelas dentro de un rango de elevación, puntos LiDAR bajo los edificios, un MDT recortado a un municipio.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; escribe los ráster (GeoTIFF, COG) y las nubes de puntos (LAZ, COPC) filtrados.&lt;/li&gt;&lt;li&gt;Algoritmos y modelos de Processing, qgis_process, API de Python y REST.&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>Abrir la guía del usuario</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="409"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Esta expresión no se puede evaluar de forma segura para un servicio.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>The service could not be read. Please retry.</source>
        <translation>No se pudo leer el servicio. Inténtelo de nuevo.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>Read failed</source>
        <translation>Error de lectura</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="287"/>
        <source>Loading filtered extent…</source>
        <translation>Cargando la extensión filtrada…</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="404"/>
        <source>The expression is not valid for this layer. Check its syntax and field names.</source>
        <translation>La expresión no es válida para esta capa. Compruebe su sintaxis y los nombres de los campos.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="407"/>
        <source>A virtual field of this layer cannot be evaluated safely for a service.</source>
        <translation>Un campo virtual de esta capa no se puede evaluar de forma segura para un servicio.</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="319"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>Capas PostgreSQL detectadas ({0}), pero psycopg2 no está instalado.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="419"/>
        <source>Cleared {0} caches</source>
        <translation>{0} cachés limpiadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="925"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Error al crear el panel acoplable: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="935"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Error al mostrar el panel acoplable: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1501"/>
        <source>Error executing {0}: {1}</source>
        <translation>Error al ejecutar {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1513"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Complemento ejecutándose en modo degradado (servicios hexagonales no disponibles). El rendimiento puede verse reducido.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate ERROR</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>No se puede ejecutar {0}: error en la inicialización del widget.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>No se puede {0}: capa inválida o fuente no encontrada.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2792"/>
        <source>All filters cleared - </source>
        <translation>Todos los filtros eliminados – </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2793"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} entidades visibles en la capa principal</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2805"/>
        <source>Error: result handler missing</source>
        <translation>Error: manejador de resultados no encontrado</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2822"/>
        <source>Error during filtering: {0}</source>
        <translation>Error durante el filtrado: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2946"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0} favorito(s) huérfano(s) recuperado(s): {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3112"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Error al cargar la capa – clic para reintentar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3164"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} capa(s) cargada(s) correctamente</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2095"/>
        <source>filter</source>
        <translation>filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2097"/>
        <source>unfilter</source>
        <translation>desfiltrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2100"/>
        <source>FilterMate – Edit Mode Detected</source>
        <translation>FilterMate – Modo de edición detectado</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2102"/>
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
        <location filename="../filter_mate_app.py" line="2112"/>
        <source>Save Changes &amp; {0}</source>
        <translation>Guardar cambios y {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2119"/>
        <source>Discard Changes &amp; {0}</source>
        <translation>Descartar cambios y {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2126"/>
        <source>Cancel</source>
        <translation>Cancelar</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2150"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>No se pudieron guardar los cambios de la capa &quot;{0}&quot;. Operación cancelada.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1331"/>
        <source>Pick a layer in the EXPLORING tab before running &apos;{0}&apos;.</source>
        <translation>Elija una capa en la pestaña EXPLORING antes de ejecutar '{0}'.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="852"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} capa(s) siguen filtradas: {1}. Vuelva a activar la opción para quitarles el filtro.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2624"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>Se está preparando un filtro de servidor. Espere a que termine antes de iniciar otra operación.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1773"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>Se está ejecutando una operación de la API de FilterMate. Espere a que termine.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="458"/>
        <source>Adding layers</source>
        <translation>Añadiendo capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="462"/>
        <source>Existing project loaded</source>
        <translation>Proyecto existente cargado</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="455"/>
        <source>Exporting data</source>
        <translation>Exportando datos</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="452"/>
        <source>Filtering data</source>
        <translation>Filtrando datos</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="461"/>
        <source>New project</source>
        <translation>Nuevo proyecto</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="457"/>
        <source>Redo filter</source>
        <translation>Rehacer filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="463"/>
        <source>Reloading layers</source>
        <translation>Recargando capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="460"/>
        <source>Removing all layers</source>
        <translation>Quitando todas las capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="459"/>
        <source>Removing layers</source>
        <translation>Quitando capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="454"/>
        <source>Reseting data</source>
        <translation>Restableciendo datos</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="456"/>
        <source>Undo filter</source>
        <translation>Deshacer filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="453"/>
        <source>Unfiltering data</source>
        <translation>Desfiltrando datos</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>Error de inicialización: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Configuración de la interfaz incompleta – revise los registros</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">Error de dimensión de la interfaz: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>Gestor de favoritos no disponible</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} favoritos guardados
Haga clic para aplicar o gestionar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Sin favoritos guardados
Haga clic para añadir el filtro actual</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <location filename="../ui/controllers/backend_controller.py" line="822"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>Backend {0} forzado para {1} capa(s)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>Controlador de backend no disponible</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>Limpieza automática de PostgreSQL activada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>Limpieza automática de PostgreSQL desactivada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>Vistas de sesión PostgreSQL limpiadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>No hay vistas que limpiar o la limpieza falló</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <location filename="../ui/controllers/backend_controller.py" line="1089"/>
        <source>No PostgreSQL connection available</source>
        <translation>No hay conexión PostgreSQL disponible</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>El esquema tiene {0} vista(s) de otras sesiones.
¿Eliminar de todos modos?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>Otras sesiones activas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>Limpieza del esquema cancelada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Esquema '{0}' eliminado correctamente</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <location filename="../ui/controllers/backend_controller.py" line="1090"/>
        <source>Schema cleanup failed</source>
        <translation>Error en la limpieza del esquema</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>Información de sesión PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>Tema adaptado: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>Modo oscuro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>Modo claro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4116"/>
        <location filename="../ui/controllers/exploring_controller.py" line="884"/>
        <source>Selected features have no geometry.</source>
        <translation>Las entidades seleccionadas no tienen geometría.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4135"/>
        <location filename="../ui/controllers/exploring_controller.py" line="885"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Ninguna entidad seleccionada. Seleccione una entidad de la lista desplegable.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5319"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>La capa seleccionada es inválida o no se puede encontrar su fuente.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6114"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Buffer negativo (erosión): contrae los polígonos hacia el interior</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6117"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Valor de buffer en metros (positivo=expandir, negativo=contraer polígonos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6619"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Complemento activado con {0} capa(s) vectorial(es)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6718"/>
        <source>Could not reload plugin automatically.</source>
        <translation>No se pudo recargar el complemento automáticamente.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Error al recargar el complemento: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6798"/>
        <source>Layer properties reset to defaults</source>
        <translation>Propiedades de la capa restablecidas a valores predeterminados</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6799"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Error al restablecer las propiedades de la capa: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>Filter</source>
        <translation>Filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>Deshacer el último filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>Rehacer el último filtro</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>Quitar los filtros</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>Exportar las capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>Acerca de FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>Identificar las entidades seleccionadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>Ampliar a las entidades seleccionadas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>Seleccionar las entidades en el mapa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>Seguir las entidades en el mapa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">Vincular los tres modos de selección</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>Restablecer las propiedades de la capa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>Seguir la capa actual</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>Capas a filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>Combinar con el filtro existente</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>Predicados geométricos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>Distancia de búfer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>Tipo de búfer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>Capas a exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>Proyección de la exportación</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>Exportar los estilos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>Formato de exportación</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>Carpeta de salida</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>Comprimir la exportación en ZIP</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>No se pudo aplicar la disposición del panel; se usan los tamaños predeterminados. Detalles en filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6890"/>
        <location filename="../ui/controllers/backend_controller.py" line="682"/>
        <source>Vector</source>
        <translation>Vectorial</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>Vincular las selecciones simple y múltiple</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>Se eliminarán el esquema '{0}' y los siguientes {1} objeto(s) temporal(es):</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>... y {0} más</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>El esquema '{0}' está vacío y se eliminará.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>Eliminar el esquema de FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>Read failed</source>
        <translation>Error de lectura</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>The service could not be read. Please retry.</source>
        <translation>No se pudo leer el servicio. Inténtelo de nuevo.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4589"/>
        <source>Loading filtered extent…</source>
        <translation>Cargando la extensión filtrada…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5184"/>
        <location filename="../ui/controllers/exploring_controller.py" line="742"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3658"/>
        <source>Loading selected values…</source>
        <translation>Cargando los valores seleccionados…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Esta expresión no se puede evaluar de forma segura para un servicio.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2715"/>
        <source>Error evaluating expression: {0}</source>
        <translation>Error al evaluar la expresión: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2716"/>
        <source>Expression Evaluation</source>
        <translation>Evaluación de la expresión</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="444"/>
        <source>Loading values…</source>
        <translation>Cargando valores…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="846"/>
        <source>Loading zoom extent…</source>
        <translation>Cargando la extensión del zoom…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>Ninguna entidad con geometría coincide con la selección.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="434"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>Solo se muestra un conjunto limitado de valores. Refine la búsqueda para encontrar otros valores.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5119"/>
        <location filename="../ui/controllers/exploring_controller.py" line="551"/>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <location filename="../ui/controllers/exploring_controller.py" line="691"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3651"/>
        <source>Selection</source>
        <translation>Selección</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="550"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>La selección del servicio supera el límite de claves. Refine la selección.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <source>This service has no stable key for the selection.</source>
        <translation>Este servicio no tiene una clave estable para la selección.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="436"/>
        <location filename="../ui/controllers/exploring_controller.py" line="438"/>
        <source>Values</source>
        <translation>Valores</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="808"/>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>Zoom</source>
        <translation>Zoom</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1087"/>
        <source>&apos;{0}&apos; is not a FilterMate temporary schema: it is not dropped</source>
        <translation>'{0}' no es un esquema temporal de FilterMate: no se elimina</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1312"/>
        <source>... and {0} more (see details)</source>
        <translation>... y {0} más (ver detalles)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="778"/>
        <source>Auto (Default)</source>
        <translation>Auto (predeterminado)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="786"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Selección automática óptima para todas las capas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="817"/>
        <source>Auto-selected backends for {0} layer(s)</source>
        <translation>Backends seleccionados automáticamente para {0} capa(s)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="838"/>
        <source>Backend forced to {0} for &apos;{1}&apos;</source>
        <translation>Backend forzado a {0} para '{1}'</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="841"/>
        <source>Backend set to Auto for &apos;{0}&apos;</source>
        <translation>Backend establecido en Auto para '{0}'</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1336"/>
        <source>Cleanup cancelled</source>
        <translation>Limpieza cancelada</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="807"/>
        <source>Clear ALL FilterMate temporary tables from all databases</source>
        <translation>Borrar TODAS las tablas temporales de FilterMate de todas las bases de datos</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="797"/>
        <source>Clear Temp Tables</source>
        <translation>Borrar tablas temporales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1317"/>
        <source>Clear all FilterMate temporary tables</source>
        <translation>Borrar todas las tablas temporales de FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="802"/>
        <source>Clear temporary tables for the current project only</source>
        <translation>Borrar las tablas temporales solo del proyecto actual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="828"/>
        <source>Cleared {0} temporary table(s) for current project</source>
        <translation>Se borraron {0} tabla(s) temporal(es) del proyecto actual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1340"/>
        <source>Cleared {0} temporary table(s) globally</source>
        <translation>Se borraron {0} tabla(s) temporal(es) en todo el sistema</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1307"/>
        <source>FilterMate will permanently delete {0} temporary table(s) / view(s) from the databases of the project and of the PostgreSQL connection:</source>
        <translation>FilterMate eliminará de forma permanente {0} tabla(s) / vista(s) temporal(es) de las bases de datos del proyecto y de la conexión PostgreSQL:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="791"/>
        <source>Force {0} for All Layers</source>
        <translation>Forzar {0} para todas las capas</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="742"/>
        <source>No alternative backends available for this layer</source>
        <translation>No hay backends alternativos disponibles para esta capa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1333"/>
        <location filename="../ui/controllers/backend_controller.py" line="1342"/>
        <source>No temporary tables found</source>
        <translation>No se encontraron tablas temporales</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="830"/>
        <source>No temporary tables found for current project</source>
        <translation>No se encontraron tablas temporales para el proyecto actual</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1080"/>
        <source>Schema &apos;{0}&apos; does not exist: nothing to drop</source>
        <translation>El esquema '{0}' no existe: nada que eliminar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1083"/>
        <source>Schema &apos;{0}&apos; holds objects FilterMate did not create ({1}): it is not dropped</source>
        <translation>El esquema '{0}' contiene objetos que FilterMate no creó ({1}): no se elimina</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="762"/>
        <source>Select Backend:</source>
        <translation>Seleccionar backend:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1313"/>
        <source>Your own tables and layers are not touched. Continue?</source>
        <translation>Sus propias tablas y capas no se tocan. ¿Continuar?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="805"/>
        <source>🌐 All Projects (Global)</source>
        <translation>🌐 Todos los proyectos (global)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="800"/>
        <source>📁 Current Project</source>
        <translation>📁 Proyecto actual</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>The filter was not launched: its selection changed or could not be read. Click Filter again.</source>
        <translation>El filtro no se inició: su selección cambió o no se pudo leer. Haga clic en Filtrar de nuevo.</translation>
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
        <translation>SELECCIÓN SIMPLE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>SELECCIÓN MÚLTIPLE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>SELECCIÓN PERSONALIZADA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>FILTRADO</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>EXPORTACIÓN</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>CONFIGURACIÓN</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>Seleccionar SRC para exportación</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>Exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2330"/>
        <source>AND</source>
        <translation>Y</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2335"/>
        <source>AND NOT</source>
        <translation>Y NO</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2340"/>
        <source>OR</source>
        <translation>O</translation>
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
        <translation>Filtrado multicapa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Filtrado aditivo para la capa seleccionada</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>Filtrado geoespacial</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>Búfer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>Capa de expresión</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>Predicado geométrico</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>Formato de salida</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>Filtrar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>Restablecer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>Capas a exportar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>Proyección de capas</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>Guardar estilos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>Exportar tipo de datos</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>Nombre de archivo/directorio</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Usar centroides en lugar de geometrías completas para la capa fuente (más rápido para polígonos complejos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Valor de buffer en metros (positivo=expandir, negativo=contraer polígonos)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>Número de segmentos para la precisión del buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>Modo por lotes</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="633"/>
        <source>FilterMate was unloaded</source>
        <translation>FilterMate se ha descargado</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="119"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>ráster renderizado o no compatible: no puede ser un objetivo del filtro</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="582"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>las fuentes ráster renderizadas requieren una captura de color local; las selecciones numéricas de píxeles no están disponibles</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="654"/>
        <source>the source layer itself was not changed</source>
        <translation>la propia capa de origen no se modificó</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="643"/>
        <source>source changed while the filter was running: nothing was applied</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="347"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} entidades visibles en la capa principal</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Todos los filtros eliminados – {count} entidades visibles en la capa principal</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>Tarea fallida</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>Filtro fallido para: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0} más)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>Capa(s) filtrada(s)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Capa(s) filtrada(s) al estado anterior</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>Filtro(s) eliminado(s) de la(s) capa(s)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>Tarea de filtrado: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>Tarea de exportación: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>Excepción: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>Filtro no aplicado, se conserva el filtro anterior: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>Capa(s) eliminada(s) durante el filtrado, omitida(s): {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>Dibuje una zona de selección útil antes de calcular la altura sobre el suelo de forma remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>El MDT y la nube de puntos no tienen una extensión útil en común</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>La selección útil no tiene área poligonal</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>La altura sobre el suelo cubre solo el área útil; Desfiltrar restaura la nube original</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Menús y barras de herramientas Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Propiedad</translation>
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
        <translation>Propiedad</translation>
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
        <translation>Capas PostgreSQL detectadas ({0}), pero psycopg2 no está instalado. El complemento no puede usar estas capas. Instale psycopg2 para habilitar el soporte de PostgreSQL.</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>No se pudo abrir el origen guardado</translation>
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
        <translation>Capa PostgreSQL '{0}': Datos corruptos detectados.

Esta capa usa 'virtual_id' que no existe en PostgreSQL.
Este error proviene de una versión anterior de FilterMate.

Solución: Elimine esta capa del proyecto FilterMate y vuelva a añadirla.
Asegúrese de que la tabla PostgreSQL tenga un PRIMARY KEY definido.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>La capa '{0}' no tiene PRIMARY KEY. Funciones limitadas: vistas materializadas desactivadas. Recomendación: añadir un PRIMARY KEY para un rendimiento óptimo.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>Excepción: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: este proveedor no puede garantizar un filtro de servidor completo. Utilice una copia local acotada antes de filtrar.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: no se pudieron leer del servicio web los valores de clave de las entidades seleccionadas.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>conserva su filtro anterior</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>queda sin filtrar</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: este servicio web no tiene un campo de clave única (clave declarada, id, gml_id, cleabs, objectid...), por lo que las entidades seleccionadas no se pueden enumerar para el servidor. La capa {1}. Sirve un filtro por atributos o una copia local de la capa.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: esta capa no tiene un campo de clave única y los identificadores de sus entidades no se pueden enumerar en su filtro (una capa virtual necesita una columna de id única, su uid). La capa {1}.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: {1} entidades que enumerar, más de las {2} que se envían a un servicio web. La capa {3}. Reduzca la selección, utilice un filtro por atributos o trabaje con una copia local de la capa.</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Configuración de optimización</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Configurar ajustes de optimización</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Habilitar optimizaciones automáticas</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Preguntar antes de aplicar optimizaciones</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Configuración de centroide automático</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Habilitar centroide automático para capas distantes</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Umbral de distancia (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Umbral de entidades:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Optimizaciones de búfer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Simplificar geometría antes del búfer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Reducir segmentos de búfer a:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>General</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Usar vistas materializadas para filtrado</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Crear índices espaciales automáticamente</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Usar índice espacial R-tree</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Usar pre-filtro de caja delimitadora</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Backends</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Almacenamiento en caché</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Habilitar caché de geometría</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Procesamiento por lotes</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Tamaño del lote:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Los ajustes avanzados afectan el rendimiento y uso de memoria. Cambie solo si entiende las implicaciones.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Avanzado</translation>
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
        <translation>Enlace con la condición anterior</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="799"/>
        <source>AND</source>
        <translation>Y</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="800"/>
        <source>OR</source>
        <translation>O</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="801"/>
        <source>Attribute</source>
        <translation>Atributo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>Comparación</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>entre</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>Eliminar esta condición</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>Comparar con un valor o con otro atributo</translation>
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
        <translation>Valor máximo conservado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>Valores observados: {0} a {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>Sin estadísticas para este atributo</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1053"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>Aplicar a las demás teselas del conjunto de datos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1062"/>
        <source>CLASSES</source>
        <translation>CLASES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Ground</source>
        <translation>Suelo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Vegetation</source>
        <translation>Vegetación</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1069"/>
        <source>Buildings</source>
        <translation>Edificios</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1070"/>
        <source>Above ground</source>
        <translation>Sobre el suelo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1071"/>
        <source>Water</source>
        <translation>Agua</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1072"/>
        <source>Without noise</source>
        <translation>Sin ruido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">Marcar solo estas clases</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">Ninguna</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1101"/>
        <source>Point classes</source>
        <translation>Clases de puntos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">RANGOS DE ATRIBUTOS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (m)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">Elevación mínima conservada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">Elevación máxima conservada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Intensity</source>
        <translation>Intensidad</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">Intensidad mínima conservada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">Intensidad máxima conservada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">Retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">Eco del pulso láser conservado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">Altura sobre MDT ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1290"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>Modelo digital del terreno desde el que se mide la altura</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1300"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>Conservar los puntos situados al menos a esta altura sobre el modelo del terreno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>EXPRESSION</source>
        <translation>EXPRESIÓN</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1379"/>
        <source>Point cloud expression</source>
        <translation>Expresión de la nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1380"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>Marque el grupo para editar la expresión manualmente</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">No hay estadísticas de elevación para esta capa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1661"/>
        <source>Height above the terrain is unavailable</source>
        <translation>La altura sobre el terreno no está disponible</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">Puntos conservados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Filtro actual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">ninguno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">Cualquiera</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">Primero</translation>
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
        <translation>+ Condición</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1196"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>Añadir una condición sobre un atributo de la capa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1235"/>
        <source>Returns</source>
        <translation>Retornos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">Conservar los retornos primeros, últimos o únicos de los pulsos láser</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1242"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>Primer retorno (ReturnNumber = 1)</translation>
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
        <translation>Clasificación</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Scan angle</source>
        <translation>Ángulo de escaneo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>User data</source>
        <translation>Datos de usuario</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Point source ID</source>
        <translation>ID de origen</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>GPS time</source>
        <translation>Tiempo GPS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Red</source>
        <translation>Rojo</translation>
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
        <translation>Infrarrojo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Scan direction</source>
        <translation>Dirección de escaneo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Edge of flight line</source>
        <translation>Borde de línea de vuelo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Synthetic</source>
        <translation>Sintético</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Key point</source>
        <translation>Punto clave</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Withheld</source>
        <translation>Retenido</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1365"/>
        <source>Overlap</source>
        <translation>Solape</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>Scanner channel</source>
        <translation>Canal del escáner</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>Classification flags</source>
        <translation>Indicadores de clasificación</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>Height above ground</source>
        <translation>Altura sobre el suelo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Quick class selection</source>
        <translation>Selección rápida de clases</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">Selección rápida…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>All classes</source>
        <translation>Todas las clases</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>No class</source>
        <translation>Ninguna clase</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>Invert the selection</source>
        <translation>Invertir la selección</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Selection ▾</source>
        <translation>Selección ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1115"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>Clases del estándar sin ningún punto en esta capa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1122"/>
        <source>Classes absent from the layer</source>
        <translation>Clases ausentes de la capa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1146"/>
        <source>Similar objects: area ×</source>
        <translation>Objetos similares: área ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Objeto similar más pequeño, como proporción del más pequeño de los seleccionados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Objeto similar más grande, como múltiplo del más grande de los seleccionados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1164"/>
        <source>to ×</source>
        <translation>a ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1208"/>
        <source>Pipette on</source>
        <translation>Cuentagotas en</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1209"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>Atributo que el cuentagotas de valor de la barra lateral lee bajo el clic</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1224"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>Tolerancia alrededor del valor elegido, en % del rango observado del atributo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1236"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>Conservar todos los retornos, o los primeros, últimos o únicos retornos de los pulsos láser</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1241"/>
        <source>Any return</source>
        <translation>Cualquier retorno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1255"/>
        <source>HEIGHT / DTM</source>
        <translation>ALTURA / MDT</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>Always combined (AND) with the active group</source>
        <translation>Siempre combinada (AND) con el grupo activo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1265"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · nube derivada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1267"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>La altura la calcula PDAL en una nube de puntos derivada, en una tarea en segundo plano</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1370"/>
        <source>{0} object(s)</source>
        <translation>{0} objeto(s)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>cut at the window read</source>
        <translation>cortado en la ventana de lectura</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1372"/>
        <source>shown as the whole class in their box</source>
        <translation>mostrados como la clase completa en su recuadro</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1863"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>Otras clases, ausentes de la capa ({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1954"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>Un objeto sobrepasa la ventana de lectura más grande alrededor del clic y se cortó ahí</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1956"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>Demasiados objetos para el subconjunto de la nube: la vista previa y la nube filtrada conservan todos los puntos de su clase en el recuadro que los rodea; los objetivos se recortan por los propios objetos</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">Filtro de nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">Clasificación</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">Ninguna</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">Elevación (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">Intensidad</translation>
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
        <translation type="obsolete">Filtro actual: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">ninguno</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">Cualquiera</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>Se requiere una extensión útil para una nube de puntos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>No hay ningún lector PDAL para este formato de nube de puntos</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>Se requiere PDAL 2.4 o superior con una versión legible para las nubes de puntos remotas</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>Las nubes de puntos remotas requieren EPT o COPC para lecturas acotadas</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>La extensión útil debe ser finita y tener un área positiva</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="513"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>Dibuje una zona de selección útil antes de leer una nube de puntos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="546"/>
        <source>The remote point cloud could not be read</source>
        <translation>No se pudo leer la nube de puntos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="550"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>La nube de puntos remota rechazó la selección</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="811"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>Una nube acotada de altura sobre el suelo solo admite AND o AND NOT; Desfiltre primero</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="837"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>Se requiere PDAL 2.4 o superior para recortar una nube de puntos remota</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="888"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Disjoint leería toda la nube remota; elija una selección interior</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="895"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>No se pudo abrir la nube de puntos remota original</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>Info de sesión PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL activo</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Info de conexión</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Conexión:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Esquema temporal:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Estado:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Vistas temporales</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Opciones de limpieza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Limpieza automática al cerrar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Limpiar automáticamente las vistas temporales cuando FilterMate se cierra.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Limpiar ahora</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Eliminar todas las vistas temporales creadas por FilterMate en esta sesión.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Sin vistas temporales)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Sin vistas</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>No hay vistas temporales para limpiar.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Confirmar limpieza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Limpieza completada</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Problema de limpieza</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Limpieza fallida</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL no está disponible&lt;/b&gt;&lt;br&gt;&lt;br&gt;Para usar las funciones de PostgreSQL, instale psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Luego reinicie QGIS para aplicar los cambios.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Sesión: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} vista(s) en esta sesión</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Esto eliminará {view_count} vista(s) temporal(es) creada(s) por FilterMate.

Todos los resultados de filtrado no guardados se perderán.

¿Continuar?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped} vista(s) temporal(es) eliminada(s).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Algunas vistas no se pudieron eliminar: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Error durante la limpieza: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>Capas a filtrar</translation>
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
        <translation>Búfer</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="105"/>
        <source>Band</source>
        <translation>Banda</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>Expresión ráster</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="147"/>
        <source>Layers to export</source>
        <translation>Capas a exportar</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>Carpeta de salida</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>Predicados geométricos</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>Valor de píxel</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>Pendiente (grados)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>Pendiente (%)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>Orientación (grados)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>Sombreado (0-255)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>El ráster de origen se remuestreó para la captura (cuadrícula: {0}).</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: el ráster objetivo se remuestreó para la captura (cuadrícula: {1}).</translation>
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
        <location filename="../processing/algorithms/common.py" line="208"/>
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
        <translation>FilterMate — Publicar en Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Publicar favoritos&lt;/b&gt; — escribir un paquete compartible en una colección QGIS Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>Sobrescribir paquete existente</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>Publicar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Colección de destino&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>Examinar…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Nombre del archivo del paquete&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>p. ej. zonas_bruselas</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;destino&amp;gt;/filter_mate/favorites/&amp;lt;nombre&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Metadatos de la colección&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>Nombre a mostrar de la colección</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>Nombre:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>Autor / organización</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>Autor:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>p. ej. CC-BY-4.0, MIT, Propietaria</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>Licencia:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>Etiquetas separadas por comas</translation>
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
        <translation>Descripción corta (opcional, texto plano)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>Descripción:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Favoritos a incluir&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>Seleccionar todo</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>Deseleccionar todo</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Nueva colección en la raíz de Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>Directorio personalizado…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Se creará bajo la raíz de Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Haga clic en 'Examinar…' para elegir un directorio.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>Elegir un directorio de colección</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} seleccionados</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>No se puede crear la colección</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>No se encontró la raíz de Resource Sharing. Utilice 'Examinar…' para elegir un directorio.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>Elegir un directorio</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Haga clic en 'Examinar…' para elegir un directorio de destino.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>No hay favoritos seleccionados</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Seleccione al menos un favorito para publicar.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>Error de publicación</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>Error desconocido.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>Se publicaron {0} favorito(s) en:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Manifiesto de colección actualizado:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>Publicación correcta</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>Repositorios remotos no disponibles</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>El gestor de repositorios remotos no está inicializado.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>La publicación en &lt;b&gt;{0}&lt;/b&gt; falló.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>Abrir clon…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>Paquete escrito en:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>Commit &lt;code&gt;{0}&lt;/code&gt; enviado a &lt;b&gt;{1}&lt;/b&gt;.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>Sin git_url configurada — paquete escrito localmente. Envíe manualmente con sus propias herramientas.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>Nada que confirmar — el contenido del paquete no cambió.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>Publicando en {0}...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>Cancelar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>Publicación</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>Publicación en curso</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>Una publicación sigue en ejecución en segundo plano. Espere a que termine antes de iniciar otra.</translation>
    </message>
</context>
<context>
    <name>QFieldCloudExtension</name>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="194"/>
        <source>QFieldCloud Settings...</source>
        <translation>Configuración de QFieldCloud...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="226"/>
        <source>Export filtered layers to QFieldCloud</source>
        <translation>Exportar capas filtradas a QFieldCloud</translation>
    </message>
</context>
<context>
    <name>QFieldCloudPushDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="102"/>
        <source>Export to QFieldCloud</source>
        <translation>Exportar a QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="117"/>
        <source>Active Filter</source>
        <translation>Filtro activo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="120"/>
        <source>No active filter</source>
        <translation>Sin filtro activo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="121"/>
        <source>Filter:</source>
        <translation>Filtro:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="123"/>
        <source>0 layers</source>
        <translation>0 capas</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="124"/>
        <source>Layers:</source>
        <translation>Capas:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="130"/>
        <source>QFieldCloud Project</source>
        <translation>Proyecto QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="135"/>
        <source>Project name:</source>
        <translation>Nombre del proyecto:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="139"/>
        <source>Description:</source>
        <translation>Descripción:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="143"/>
        <source>Create new</source>
        <translation>Crear nuevo</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="144"/>
        <source>Update existing:</source>
        <translation>Actualizar existente:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="148"/>
        <source>Mode:</source>
        <translation>Modo:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="158"/>
        <source>Layer Modes</source>
        <translation>Modos de capa</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Layer</source>
        <translation>Capa</translation>
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
        <translation>{0} capas ({1} entidades)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="217"/>
        <source>{0} layers (no filter active)</source>
        <translation>{0} capas (sin filtro activo)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Missing Name</source>
        <translation>Nombre faltante</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Please enter a project name.</source>
        <translation>Por favor ingrese un nombre de proyecto.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>Not Connected</source>
        <translation>No conectado</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>QFieldCloud is not connected. Please configure credentials first.</source>
        <translation>QFieldCloud no está conectado. Configure las credenciales primero.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No Layers</source>
        <translation>Sin capas</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No valid layers to export.</source>
        <translation>No hay capas válidas para exportar.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>Export Error</source>
        <translation>Error de exportación</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="393"/>
        <source>Failed to export layer &apos;{0}&apos;: {1}</source>
        <translation>Failed to export layer '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>GPKG export failed: {0}</source>
        <translation>Exportación GPKG fallida: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="420"/>
        <source>Push complete!</source>
        <translation>¡Envío completado!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project successfully pushed to QFieldCloud!</source>
        <translation>¡Proyecto enviado exitosamente a QFieldCloud!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project: {0}</source>
        <translation>Proyecto: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Files: {0}</source>
        <translation>Archivos: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Duration: {0:.1f}s</source>
        <translation>Duración: {0:.1f}s</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>URL: {0}</source>
        <translation>URL: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="438"/>
        <source>Warnings:</source>
        <translation>Advertencias:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="440"/>
        <source>Push Complete</source>
        <translation>Envío completado</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="450"/>
        <source>Error: {0}</source>
        <translation>Error: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push Failed</source>
        <translation>Error de envío</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push failed:

{0}</source>
        <translation>Error de envío:

{0}</translation>
    </message>
</context>
<context>
    <name>QFieldCloudSettingsDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="53"/>
        <source>QFieldCloud Configuration</source>
        <translation>Configuración de QFieldCloud</translation>
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
        <translation>Credenciales</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="81"/>
        <source>username</source>
        <translation>nombre de usuario</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="82"/>
        <source>Username:</source>
        <translation>Nombre de usuario:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="86"/>
        <source>password (for initial login)</source>
        <translation>contraseña (para inicio de sesión inicial)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="87"/>
        <source>Password:</source>
        <translation>Contraseña:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="90"/>
        <source>JWT token (auto-filled after login)</source>
        <translation>Token JWT (autocompletado después del inicio de sesión)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="95"/>
        <source>Login</source>
        <translation>Iniciar sesión</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="96"/>
        <source>Login with username/password to get a token</source>
        <translation>Iniciar sesión con usuario/contraseña para obtener un token</translation>
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
        <translation>Probar conexión</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="112"/>
        <source>Preferences</source>
        <translation>Preferencias</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="117"/>
        <source>Default project:</source>
        <translation>Proyecto predeterminado:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="119"/>
        <source>Trigger packaging after upload</source>
        <translation>Activar empaquetado después de la carga</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="144"/>
        <source>Token stored</source>
        <translation>Token almacenado</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Missing Fields</source>
        <translation>Campos faltantes</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Please fill in URL, username, and password.</source>
        <translation>Por favor complete URL, nombre de usuario y contraseña.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="174"/>
        <source>Logging in...</source>
        <translation>Iniciando sesión...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="191"/>
        <source>Logged in as {0}</source>
        <translation>Conectado como {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="198"/>
        <source>Login failed: {0}</source>
        <translation>Error de inicio de sesión: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Missing Configuration</source>
        <translation>Configuración faltante</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Please configure URL and login first.</source>
        <translation>Configure la URL e inicie sesión primero.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="219"/>
        <source>Testing connection...</source>
        <translation>Probando conexión...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="229"/>
        <source>Connected! ({0} projects accessible)</source>
        <translation>¡Conectado! ({0} proyectos accesibles)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="235"/>
        <source>Connection failed: {0}</source>
        <translation>Error de conexión: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Missing URL</source>
        <translation>URL faltante</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Server URL is required.</source>
        <translation>La URL del servidor es obligatoria.</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxFeaturesListPickerWidget</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="924"/>
        <source>Type to filter...</source>
        <translation>Escriba para filtrar...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>Seleccionar todo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>Seleccionar todo (sin subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>Seleccionar todo (subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>Deseleccionar todo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>Deseleccionar todo (sin subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>Deseleccionar todo (subconjunto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Se muestran las primeras {0} entidades ordenadas por valor de visualización. Escriba en el filtro de texto para buscar en toda la capa; &quot;Seleccionar todo&quot; carga la lista completa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Se muestran {0} entidades de la capa, ordenadas por valor de visualización. Escriba en el filtro de texto para buscar en toda la capa; &quot;Seleccionar todo&quot; carga la lista completa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>Resultados de la búsqueda de &quot;{0}&quot; en toda la capa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1808"/>
        <source>Loading values…</source>
        <translation>Cargando valores…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1735"/>
        <source>Values</source>
        <translation>Valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Esta expresión no se puede evaluar de forma segura para un servicio.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>Selection</source>
        <translation>Selección</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>La lista remota supera el límite de selección segura. Seleccione menos entidades o filtre primero la capa.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="2008"/>
        <source>Loading selected values…</source>
        <translation>Cargando los valores seleccionados…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>Seleccionar todo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>Deseleccionar todo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Seleccionar todas las capas por tipo de geometría (Líneas)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Deseleccionar todas las capas por tipo de geometría (Líneas)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Seleccionar todas las capas por tipo de geometría (Puntos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Deseleccionar todas las capas por tipo de geometría (Puntos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Seleccionar todas las capas por tipo de geometría (Polígonos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Deseleccionar todas las capas por tipo de geometría (Polígonos)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>Seleccionar todas las capas ráster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>Deseleccionar todas las capas ráster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>Seleccionar todas las capas de nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>Deseleccionar todas las capas de nube de puntos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>píxeles en la zona</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>puntos en la zona</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>entidades</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>Objetivo ráster: los píxeles fuera de la geometría de origen pasan a NoData (los del interior con Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>Objetivo nube de puntos: los puntos fuera de la geometría de origen se eliminan (los del interior con Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>Objetivo vectorial: se conservan las entidades que cumplen el predicado geométrico</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>Haga clic en el cuadrado de la derecha para probar esta capa por sus centroides</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="343"/>
        <source>Select all vector layers</source>
        <translation>Seleccionar todas las capas vectoriales</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="345"/>
        <source>De-select all vector layers</source>
        <translation>Deseleccionar todas las capas vectoriales</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>Histograma del rango de valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>Arrastre los controles, o haga clic, para elegir el rango de valores que se conservará</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>Sin histograma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>Valores conservados de {0} a {1}</translation>
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
        <translation type="obsolete">Banda cuyos valores se seleccionan</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">VALOR DE PÍXEL</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">Valor de píxel de la banda actual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">Últimos {0} valores elegidos</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">Haga clic en el mapa con el selector de píxeles. Ctrl+clic amplía el rango hasta el valor.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>RANGO DE VALORES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>Mín.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>Valor mínimo conservado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>Máx.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>Valor máximo conservado</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">Vista previa en el mapa (ocultar los demás píxeles)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">CLASES</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">Clases ráster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">Todas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">Ninguna</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>EXPRESIÓN RÁSTER</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>Expresión de la calculadora ráster; se conserva un píxel donde no sea 0</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>Expresión ráster</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">Usar el rango</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">Escribir el rango de valores actual como una expresión</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">Píxeles seleccionados: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>Defina primero un rango de valores</translation>
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
        <translation type="obsolete">Valor de la banda actual bajo el cursor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">Estadísticas de la banda actual en el último rectángulo dibujado en el mapa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>Bajo el cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>Zona: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>ningún píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>ÚLTIMAS LECTURAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">Calcular sobre</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">Magnitud a la que se aplica el rango. La pendiente, la orientación, el sombreado y la rugosidad leen la banda como un MDT.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>Valor de píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>Pendiente (grados)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>Pendiente (%)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>Orientación (grados)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>Sombreado (0-255)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>Rugosidad (TRI, diferencia media)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>Umbrales habituales de la magnitud</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">Umbrales habituales</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>Plana</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>Suave</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>Moderada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>Empinada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>Este</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>Sur</translation>
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
        <translation>Iluminada</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">Umbrales habituales…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>CUENTAGOTAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>Tolerancia ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>Tolerancia alrededor del color o valor elegido, en % del rango de valores</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>Tolerancia del cuentagotas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>Bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">Qué son las bandas de la imagen: los preajustes y el cuentagotas las utilizan</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">Disposición de las bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB (rojo, verde, azul)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC (infrarrojo, rojo, verde)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + infrarrojo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">Escribir la expresión de un índice habitual (vegetación, agua...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">Preajustes espectrales</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">Requiere una imagen de tres bandas o más (rojo, verde, azul...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>Vegetación (NDVI &gt; 0.3)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>Sin vegetación (NDVI &lt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>Agua (NDWI &gt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>Vegetación (exceso de verde)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">Preajustes espectrales…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>Este píxel no tiene valor (NoData): elija otro</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>La tolerancia cubre todos los valores: redúzcala</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">Rango {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">Clase(s) {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} color(es), último: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">Expresión</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>BANDAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>Valor de la banda activa bajo el cursor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>Estadísticas de la banda activa en el último rectángulo dibujado en el mapa</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>Todas las bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>El rango de valores se aplica a todas las bandas de color a la vez (se conserva un píxel cuando cada banda está dentro del rango); el histograma muestra la primera</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>Banda activa: la que leen el rango, el histograma y el selector</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>El cuentagotas compara esta banda</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>Color que contiene la banda: los índices espectrales y los chips lo usan. Haga clic para cambiarlo</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>Valor en el último clic del cuentagotas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>Ningún color</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>Las bandas 1, 2, 3 son rojo, verde, azul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>IRC</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>Las bandas 1, 2, 3 son infrarrojo, rojo, verde (ortofoto infrarroja en color del IGN)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>Las bandas 1, 2, 3, 4 son rojo, verde, azul, infrarrojo cercano</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>Todas las bandas: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> Roles supuestos, por confirmar.</translation>
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
        <translation>Rojo</translation>
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
        <translation>Infrarrojo cercano</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>roles supuestos, por confirmar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>Seleccionar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>Píxeles similares</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>Todos los píxeles del ráster cercanos al color o valor elegido (el cuentagotas de la barra lateral)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>Objeto seleccionado con el clic</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>Solo la mancha de esos píxeles donde cae el clic: una piscina, un tejado, un campo (el detector de objetos de la barra lateral); Ctrl+clic añade otro objeto</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>Objetos similares</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>Todos los objetos del ráster parecidos al seleccionado: las manchas de esos píxeles cuya área está dentro de las proporciones de abajo (la herramienta de objetos similares de la barra lateral); Ctrl+clic añade otro objeto de referencia</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>Área ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Objeto similar más pequeño, como proporción del más pequeño de los seleccionados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Objeto similar más grande, como múltiplo del más grande de los seleccionados</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>a ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>misma forma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>Conservar solo los objetos con la forma de los seleccionados: su compacidad (4π × área / perímetro², 1 para un disco) dentro de las mismas proporciones; desactivado, una carretera con el área de una piscina es una piscina</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>Quitar esta muestra</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>Magnitud</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>Magnitud a la que se aplica el rango. Pendiente, orientación, sombreado y rugosidad leen la banda activa como un MDT.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>Umbrales ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>Insertar ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>Inserta una referencia de banda, un índice espectral habitual o el rango actual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>Índices espectrales</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>Rango</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>El rango de valores actual</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>Los colores renderizados dependen del estilo y de la escala.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>Solo está disponible la selección por color: las bandas numéricas, los índices, los rangos, las clases y los derivados no están disponibles.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>RANGO DE VALORES — todas las bandas</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>RANGO DE VALORES — banda {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>toma de: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>Una pendiente, orientación... lee una banda como un MDT: elija primero una banda en BANDAS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>No se pudo leer el objeto</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>Ningún objeto bajo el clic: aumente la tolerancia o haga clic en otro píxel</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>Un objeto es mayor que la ventana leída y se cortó: reduzca la tolerancia</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>Active band</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1083"/>
        <source>Choose 1 to 3 bands for display.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="862"/>
        <source>Display the active band in grey or the checked bands as a colour composite</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1085"/>
        <source>Grey: band {0}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="859"/>
        <source>Layer style</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="855"/>
        <source>Map display</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1087"/>
        <source>R: {0} · G: {1} · B: {2}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="954"/>
        <source>Select band {0}</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="861"/>
        <source>Selected bands</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="953"/>
        <source>Use this band for the pipette and the selected bands display</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>falló la captura ráster acotada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="302"/>
        <source>local raster capture could not be opened</source>
        <translation>no se pudo abrir la captura ráster local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="284"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>el análisis ráster requiere una captura GDAL local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>captura ráster cancelada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>el destino de la captura ráster debe estar en la caché de la sesión</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>no se pudo clonar el proveedor de la captura ráster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>la captura ráster requiere una extensión finita y no vacía</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>la captura ráster requiere un límite de píxeles positivo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>la captura ráster requiere una resolución positiva</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="646"/>
        <source>raster capture source could not be opened</source>
        <translation>no se pudo abrir el origen de la captura ráster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>la materialización del ráster debe ejecutarse en un hilo de trabajo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="279"/>
        <source>raster selection canceled</source>
        <translation>selección ráster cancelada</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="294"/>
        <source>raster selection source could not be opened</source>
        <translation>no se pudo abrir el origen de la selección ráster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="275"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>la selección ráster remota debe ejecutarse en un hilo de trabajo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="281"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>la selección de color renderizado requiere una captura renderizada local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>los ráster renderizados requieren una captura de color renderizado</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: estadísticas ráster</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>Error en la muestra ráster; vuelva a intentarlo con una extensión visible más pequeña.</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: vista previa ráster</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="642"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>el objetivo ráster remoto debe ejecutarse en un hilo de trabajo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="671"/>
        <source>local raster target could not be opened</source>
        <translation>no se pudo abrir el objetivo ráster local</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="681"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>Las capas de color renderizado no pueden ser objetivos del filtro.</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>¿Aplicar optimizaciones?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Optimizaciones disponibles</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Omitir</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Aplicar seleccionados</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} entidades</translation>
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
        <translation>Resultado parcial: se alcanzó el límite de entidades remotas.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>Resultado parcial: se alcanzó el límite de tiempo remoto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>Se canceló el filtrado remoto; se conserva el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>Se enviarían más de 500 claves al servicio; reduzca la selección o utilice una copia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>El servicio no tiene una clave estable; utilice una copia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>Seleccione o filtre el origen remoto antes del filtrado espacial.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>No se puede demostrar que el filtro del servicio sea completo. Seleccione entidades de origen o utilice una copia local.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>La copia del origen remoto está incompleta; se conserva el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>Resultado parcial: no se confirmó ninguna entidad coincidente antes del límite; se conserva el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>La copia remota que intersecta está incompleta; no se puede calcular de forma segura un filtro disjunto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Disjoint combinado con otro predicado requiere una copia local del objetivo remoto.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>No se pudo evaluar el predicado espacial remoto; se conserva el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>No se pudo leer o filtrar la copia remota; se conserva el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="138"/>
        <source>Remote materialization requires a background task.</source>
        <translation>La materialización remota requiere una tarea en segundo plano.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="715"/>
        <source>Filtering a bounded remote copy</source>
        <translation>Filtrando una copia remota acotada</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: instantánea de color renderizado</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>Error en la instantánea renderizada; vuelva a intentarlo con una extensión visible más pequeña.</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Buscar en la configuración... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>Sin coincidencias</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="285"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="460"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>Una tarea de FilterMate sigue leyendo capas. Vuelva a intentarlo cuando termine.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="289"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>Una capa con almacenamiento auxiliar no puede reemplazar de forma segura a su proveedor de servidor. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="294"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>Una unión remota no se puede reconstruir en el hilo principal. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="296"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>Ya se está preparando un filtro de servidor para esta capa.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="255"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>Una capa de servidor solo se puede modificar en el hilo al que pertenece.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="278"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>Los filtros de servidor asíncronos requieren QGIS 3.32 o superior. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="404"/>
        <source>Could not install the prepared server filter.</source>
        <translation>No se pudo instalar el filtro de servidor preparado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="67"/>
        <source>Could not preserve the layer state.</source>
        <translation>No se pudo conservar el estado de la capa.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="282"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="453"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>Termine de editar la capa antes de aplicar un filtro de servidor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>Expresión de atributos no válida.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="106"/>
        <source>Preparing server attribute filter</source>
        <translation>Preparando el filtro de atributos del servidor</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>QGIS no puede traducir este predicado a un filtro OGC.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="336"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>Filtro de servidor cancelado o con tiempo de espera agotado. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="384"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>Falló la instalación del filtro de servidor y no se pudo restaurar el proveedor anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="376"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="456"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>Falló la instalación del filtro de servidor. El proveedor anterior ya no era válido y no se pudo restaurar.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="391"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>Falló la instalación del filtro de servidor. Se restauró el proveedor anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="56"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>La instalación del filtro de servidor está en curso. Vuelva a intentarlo cuando termine.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="249"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="280"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="451"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>La instalación del filtro de servidor debe iniciarse en el hilo de la capa.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>La expresión es demasiado compleja para traducirla de forma segura.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>La expresión es demasiado grande o contiene secuencias de escape SQL con barra invertida ambiguas.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="354"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>La capa cambió mientras se preparaba su filtro. Se descartó el resultado preparado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="402"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>La capa ya no está disponible. Se descartó el filtro preparado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>El servidor rechazó el filtro o no se pudo contactar con él. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="287"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>Este proveedor y esta versión de QGIS no admiten la creación verificada de procesos de trabajo. El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: el filtro de atributos no se puede ejecutar por completo en el servidor. Parte no admitida: {1}. {2} El filtro anterior no ha cambiado.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="270"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="494"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: el proveedor rechazó el filtro de atributos. Se restauró el filtro anterior.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="269"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="493"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: el proveedor rechazó el filtro y falló la restauración.</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Favoritos compartidos</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Favoritos compartidos&lt;/b&gt; — descubiertos desde colecciones QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">Buscar por nombre, descripción, colección o etiquetas…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Seleccione un favorito compartido para previsualizarlo.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>Volver a escanear</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>Bifurcar a mi proyecto</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>Cerrar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>No se encontraron colecciones compartidas. Suscríbase a un repositorio Resource Sharing que contenga una carpeta &lt;code&gt;filter_mate/favorites&lt;/code&gt;, o coloque un paquete &lt;code&gt;.fmfav.json&lt;/code&gt; en su directorio de colecciones resource_sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} favorito(s) en {1} colección(es): {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>Colección: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">Ningún favorito compartido coincide con su búsqueda.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — desde &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Expresión&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Capas remotas&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Etiquetas:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Procedencia&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>Autor: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>Licencia: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>Bifurcar favorito compartido</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>Nombre en su proyecto:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>Bifurcación correcta</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» se añadió a sus favoritos.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>Error de bifurcación</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>No se pudo añadir el favorito compartido a su proyecto.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>Buscar por nombre, descripción, colección, autor o etiquetas...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>Autor:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>Todos los autores</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>Ningún favorito compartido coincide con sus filtros.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>Restablecer valores predeterminados</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>Error de validación</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>Por favor corrija los siguientes errores:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>Restablecer configuración</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>¿Restablecer todos los valores a los predeterminados?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate – Advertencia de tipo PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Incompatibilidad de tipo en el filtro: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>Restablecer valores predeterminados</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>General</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>No se pudo aplicar el filtro de {0}; conserva su filtro anterior.</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} entidades visibles en la capa principal</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Todos los filtros eliminados – {count} entidades visibles en la capa principal</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Filtro aplicado a '{layer_name}': {count} entidades</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Filtro eliminado de '{layer_name}': {count} entidades visibles</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="942"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>¡Ninguna entidad seleccionada! El widget de selección perdió la entidad. Vuelva a seleccionar una entidad.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1060"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>La capa seleccionada es inválida o no se puede encontrar su fuente. Operación cancelada.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1075"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>La capa '{0}' aún no está inicializada. Seleccione otra capa y luego vuelva a esta.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>No se puede deshacer: capa inválida o fuente no encontrada.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>No se puede rehacer: capa inválida o fuente no encontrada.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>El proveedor rechazó el filtro guardado.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>No se pudo restaurar el filtro: {0}</translation>
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
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="301"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: sin campo de clave única, sus entidades no se pueden enumerar en su filtro (un servicio web, o una capa virtual sin columna de id única).</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="452"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>{0} entidades que enumerar, más de las {1} que se envían a un servicio web: reduzca el origen o utilice un filtro por atributos.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="392"/>
        <source>{0} AND NOT would keep the features not read; the previous filter is kept.</source>
        <translation>{0} AND NOT conservaría las entidades no leídas; se conserva el filtro anterior.</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>La cobertura mínima no está disponible para objetos de teselas recortados</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>Los objetivos de teselas vectoriales solo admiten los predicados Intersect y Disjoint</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>El filtrado de teselas vectoriales requiere un código de autoridad de SRC</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>Filtro de visualización de teselas vectoriales: los atributos dependen del zoom; los objetos divididos entre teselas pueden diferir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>El estilo de las teselas vectoriales cambió mientras se ejecutaba el filtro; inténtelo de nuevo</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>Filtrar los atributos de las teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>Expresión de filtro de teselas vectoriales no válida</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>Expresión QGIS (los atributos dependen del zoom):</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>Rehacer el filtro de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>Solo el objetivo. Los atributos dependen del zoom. Los objetos divididos entre teselas pueden filtrarse de forma distinta.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>El estilo de teselas vectoriales guardado no es válido</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>La propiedad de símbolo de teselas vectoriales guardada no es válida</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>La selección de teselas supera el presupuesto de expresión (1 MB); utilice un área más pequeña</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>La selección de teselas supera el presupuesto de vértices (2000); utilice un área más pequeña</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>El filtro de teselas vectoriales supera el presupuesto de expresión (1 MB)</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>El filtro de teselas vectoriales supera el presupuesto total de expresiones del estilo (1 MB); utilice un área más pequeña</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>Deshacer el filtro de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>Desfiltrar teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>Filtro de atributos de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="131"/>
        <source>Vector tile favorite</source>
        <translation>Favorito de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>Filtro de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>El filtrado de teselas vectoriales requiere un renderizador básico</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>El filtrado de teselas vectoriales requiere un etiquetado básico</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>Filtros de teselas vectoriales</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>Teselas vectoriales</translation>
    </message>
</context>
<context>
    <name>self.dockwidget</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="664"/>
        <source>Language changed to &apos;{0}&apos;.</source>
        <translation type="obsolete">Idioma cambiado a '{0}'.</translation>
    </message>
</context>
<context>
    <name>self.self</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="735"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation type="obsolete">Geometría de origen: las entidades seleccionadas en EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">Geometría de origen: los píxeles seleccionados, vectorizados</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">Puntos conservados</translation>
    </message>
</context>
</TS>
