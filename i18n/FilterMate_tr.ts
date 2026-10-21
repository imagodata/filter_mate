<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="tr_TR" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>Resource Sharing'den içe aktar...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Resource Sharing'e yayımla...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>Yayımla (favori kaydedilmedi)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>Varsayılan depoya hızlı yayımla</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>Resource Sharing depolarını yönet...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>{0} katmandan bozuk filtreler temizlendi. Lütfen filtrelerinizi yeniden uygulayın.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Boş proje algılandı. Eklentiyi etkinleştirmek için vektör katmanlar ekleyin.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>FilterMate veritabanına erişilemiyor. Proje dizini izinlerini kontrol edin.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>Veritabanı doğrulaması sırasında hata: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Katman yüklemesi başarısız. Zorla yeniden yüklemek için F5 kullanın.</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: bu web hizmetinin benzersiz bir anahtar alanı yok (bildirilen anahtar, id, gml_id, cleabs, objectid...); bu nedenle seçili nesneler sunucu için listelenemiyor.</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: bu katmanın benzersiz bir anahtar alanı yok ve nesne kimlikleri filtresinde listelenemiyor (sanal katman için benzersiz bir kimlik sütunu, yani uid gerekir).</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: {1} nesne seçili; bu, bir web hizmetine gönderilebilen {2} sınırını aşıyor. Seçimi daraltın veya bir öznitelik filtresi kullanın.</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>Uzak dosya: her okuma ağ üzerinden yapılır. FilterMate nesnelerini ana iş parçacığında saymaz.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>Uzak hizmet: filtre, sunucu çevirebildiğinde sunucuya gönderilir. FilterMate nesnelerini ana iş parçacığında saymaz.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>Nesne listesine göre filtre {0} nesneyle sınırlıdır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="123"/>
        <source>Remote</source>
        <translation>Uzak</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="185"/>
        <source>Select Backend:</source>
        <translation>Arka uç seçin:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>Otomatik (Varsayılan)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Tüm katmanlar için en uygununu otomatik seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>Tüm katmanlar için {0} zorla</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>Katmanları yeniden yüklemek için tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>Arka ucu değiştirmek için tıklayın</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>İşaretli çizgi ve poligon hedeflerini merkez noktalarıyla (yüzey üzerindeki nokta) test et: büyük geometrilerde daha hızlı. Her hedefin listede kendi karesi vardır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>Merkez noktaları çizgi ve poligon hedefleri için geçerlidir: filtrelenecek katmanlar listesinden birini işaretleyin</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Değişiklikleri iptal ederken hata: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>Özellik hatası: {0}</translation>
    </message>
</context>
<context>
    <name>CoverageDockExtras</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="303"/>
        <source>1 band</source>
        <translation>1 bant</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="304"/>
        <source>{0} bands</source>
        <translation>{0} bant</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="305"/>
        <source>{0} points</source>
        <translation>{0} nokta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>Kaynak geometri: seçili pikseller, vektörleştirilmiş</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="792"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>Kaynak geometri: tutulan noktaların kapladığı alan</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="739"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation>Kaynak geometri: EXPLORING'de seçili nesneler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">İmlecin altındaki değer: harita üzerinde gezinirken geçerli bandın piksel değerini izle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">Dikdörtgen istatistikleri: geçerli bandın minimum, maksimum ve ortalamasını okumak için haritada sürükleyin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>Yükseklik profili: haritanın QGIS yükseklik profilini aç</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>3B görünüm: yeni bir QGIS 3B harita görünümü aç</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">detay yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} detay</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">tüm pikseller</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} sınıf</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>ifade</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} detay</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Vector</source>
        <translation>Vektör</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Raster</source>
        <translation>Raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Point cloud</source>
        <translation>Nokta bulutu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="795"/>
        <source>Kept points</source>
        <translation>Tutulan noktalar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Selection → source geometry</source>
        <translation>Seçim → kaynak geometri</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>Aralığı stile bağla: katman renkleri seçilen aralığa yayılır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Sınıf pipeti: haritaya tıklayın, orada çizilen noktaların sınıfı işaretlenir. Ctrl+tıklama bir tane daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>İmlecin altındaki değer: harita üzerinde gezinirken piksel değerini (veya aralığın uygulandığı eğimi, bakıyı...) izle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>Dikdörtgen istatistikleri: geçerli bandın (veya aralığın uygulandığı eğimin, bakının...) minimum, maksimum ve ortalamasını okumak için haritada sürükleyin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>Stil bağlantısı piksel değerlerini izler: aralık eğime, bakıya, gölgelendirmeye veya pürüzlülüğe uygulanırken kullanılamaz</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="920"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>Sınıf pipeti: bu nokta bulutunda Classification özniteliği yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1526"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>Stil aralığı izleyemez: panelin bandı üzerinde tek bantlı gri veya sahte renkli bir stil gerekir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>Pipet: haritaya tıklayın, tıkladığınız piksele benzeyen pikseller seçilir (görüntüde bir renk, DTM veya indekste bir değer, sınıflandırılmış rasterde bir sınıf; panelin toleransıyla). Ctrl+tıklama bir tane daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>seçili detay yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>tüm katman</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>kısıt yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>raster ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>tüm noktalar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} nesne</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>kutularında sınıfın tamamı olarak gösterilir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>Nesne algılayıcı: haritaya tıklayın, tıkladığınıza benzeyen piksellerin öbeği seçilir (bir havuz, bir çatı, bir tarla; panelin toleransıyla), rengindeki tüm pikseller değil. Ctrl+tıklama bir nesne daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>Benzer nesneler: bir nesneye tıklayın, rasterdeki ona benzeyen tüm nesneler seçilir (alanı panelin oranları içinde kalan bu tür piksel öbekleri). Ctrl+tıklama bir referans nesnesi daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>Nesne algılayıcı: haritaya tıklayın, tıklanan yerdeki nesne seçilir (sınıfının nokta kümesi: bir bina, bir ağaç), sınıfın tamamı değil; ya da buluttaki ona benzeyen tüm nesneler (hedef için düğmeye sağ tıklayın). Ctrl+tıklama bir nesne daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>Değer pipeti: haritaya tıklayın, ÖZNİTELİKLER'de seçilen öznitelik (Z, yoğunluk...) için oradaki noktanın değeri çevresinde, panelin toleransıyla bir koşul yazılır. Ctrl+tıklama bir koşul daha ekler (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>Bölge: haritada bir dikdörtgen, çokgen, serbest çizim veya daire çizin (şekil için düğmeye sağ tıklayın); X / Y kutusu ÖZNİTELİKLER'e gider, şeklin kendisi hedefleri keser</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>Diğer araçlar: imlecin altındaki değer, bir dikdörtgenin istatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>Benzer nesneler: bir nesneye tıklayın, katmandaki grubun alanının (tekli / çoklu seçimin görüntüleme ifadesi) değeri aynı olan tüm nesneler seçilir. Ctrl+tıklama bir değer daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>Diğer araçlar: QGIS seçim araçları (dikdörtgen, çokgen, serbest çizim, yarıçap), ifadeyle seçim, seçimi ters çevirme veya temizleme, seçimin öznitelik tablosu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>Diğer araçlar: QGIS'in yükseklik profili ve 3B görünümü</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>Yalnızca renk seçimi kullanılabilir: işlenen renkler stile ve ölçeğe bağlıdır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>Stil bağlantısı DEĞER ARALIĞI grubunu izler: önce onu etkin yapın</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="794"/>
        <source>Current filter: {0}</source>
        <translation>Geçerli filtre: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="830"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>İşlenen renkler stile ve ölçeğe bağlıdır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="929"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>Nesne algılayıcı: bu nokta bulutunda Classification özniteliği yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="978"/>
        <source>Object detector</source>
        <translation>Nesne algılayıcı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Clicked object</source>
        <translation>Tıklanan nesne</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Similar objects</source>
        <translation>Benzer nesneler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1085"/>
        <source>Zone shape</source>
        <translation>Bölge şekli</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Rectangle</source>
        <translation>Dikdörtgen</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Polygon</source>
        <translation>Çokgen</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Freehand</source>
        <translation>Serbest çizim</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Radius</source>
        <translation>Yarıçap</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1134"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>Bağlantı tekli ve çoklu seçimi izler: önce bunlardan birini etkin grup yapın</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1257"/>
        <source>Select on the map</source>
        <translation>Haritada seç</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Select by expression…</source>
        <translation>İfadeyle seç…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Invert the selection</source>
        <translation>Seçimi ters çevir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Clear the selection</source>
        <translation>Seçimi temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1272"/>
        <source>Attribute table of the selection</source>
        <translation>Seçimin öznitelik tablosu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Value under the cursor</source>
        <translation>İmlecin altındaki değer</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1315"/>
        <source>Statistics of a rectangle</source>
        <translation>Bir dikdörtgenin istatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>Elevation profile</source>
        <translation>Yükseklik profili</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>3D view</source>
        <translation>3B görünüm</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1688"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>Bu nokta bulutunda filtrelenecek X / Y özniteliği yok</translation>
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
        <translation>{0} raster / nokta bulutu katmanının filtresi geri yükleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>kapsama ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>Hedef çokgenin kaynak geometrinin içinde kalan en küçük payı (0 = herhangi bir örtüşme). Kaynak bir raster veya nokta bulutu olduğunda kullanılır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>Raster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>Nokta bulutu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>{0} katmanı: seçim EXPLORING'de, ilişki FILTERING'de</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">Piksel seçici: her bandın değerini okumak için haritaya tıklayın (Ctrl+tıklama aralığı genişletir)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>Katmana yakınlaştır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">Önizleme: seçimin dışındaki pikselleri gizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>Raster katmanları için kullanılmaz</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>Raster seçimini sıfırla</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">Haritada noktaları sorgula</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>Canlı önizleme: yalnızca seçimin tuttuğu noktaları göster</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>Nokta bulutu katmanları için kullanılmaz</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>Nokta bulutu ölçütlerini sıfırla</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>Geçersiz raster hesaplayıcı ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>PDAL bulunamadı: DTM üzerindeki yükseklik için pdal çalıştırılabilir dosyası gerekir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3151"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>Bir FilterMate görevi hâlâ çalışıyor: bitmesini bekleyin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>FilterMate görevi başarısız oldu: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>Önce pikselleri seçin: bir değer aralığı, sınıflar veya bir raster ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>Raster filtrelendi: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>Nokta bulutu ifadesi reddedildi: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>Önce noktaları seçin: sınıflar, öznitelik aralıkları veya bir ifade</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>Nokta bulutu filtrelendi: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3261"/>
        <source>Filter not applied: {0}</source>
        <translation>Filtre uygulanmadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>canceled</source>
        <translation>iptal edildi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>{0} hedef filtrelendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2823"/>
        <source>{0} failed: {1}</source>
        <translation>{0} başarısız oldu: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2836"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: '{0}' kaynağından filtreleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2933"/>
        <source>Changed since, left as is: {0}</source>
        <translation>Sonradan değişti, olduğu gibi bırakıldı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2939"/>
        <source>{0} layer(s) restored</source>
        <translation>{0} katman geri yüklendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2973"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>'{0}' dışa aktarılamadı: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2987"/>
        <source>Exported: {0}</source>
        <translation>Dışa aktarıldı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2989"/>
        <source>Export failed: {0}</source>
        <translation>Dışa aktarma başarısız oldu: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2996"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>{0} katman dışa aktarılıyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3002"/>
        <source>Export folder</source>
        <translation>Dışa aktarma klasörü</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3084"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>Raster / nokta bulutu hedefleri atlandı: EXPLORING'de kaynak nesne seçilmedi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>Raster / nokta bulutu hedefleri filtrelenmedi: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3115"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>{0} raster / nokta bulutu hedefi filtrelendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3238"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>Zeminden yükseklik için kullanılacak DTM rasterini seçin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3249"/>
        <source>Height above ground not computed: {0}</source>
        <translation>Zeminden yükseklik hesaplanmadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3270"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>'{0}' üzerindeki yükseklik PDAL ile hesaplanıyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>FilterMate önbelleği {0} GB yer kaplıyor ve {1} GB sınırını aşıyor: artık ihtiyaç duymadığınız raster / nokta bulutu katmanlarının filtresini kaldırın</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>PDAL {0} çok eski: DTM üzerindeki yükseklik için PDAL 2.4 veya üstü gerekir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>PDAL çalıştırılamadı, DTM üzerindeki yükseklik kullanılamıyor: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">Piksel seçici: her bandın değerini ve aralık bunlardan birine uygulanıyorsa eğimi, bakıyı... okumak için haritaya tıklayın (Ctrl+tıklama aralığı genişletir)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>Seçili piksellere yakınlaştır (hiçbir şey seçili değilse katmana)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>Önizleme: seçimin dışındaki pikselleri gizle (eğim, bakı... için beyaz bir örtü)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>Eğim veya bakı önizlemesi için haritanın rasterin CRS'sinde ({0}) olması gerekir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>yalnızca haritada çizilen noktalar seçilebilir: gizlediği bir sınıfı seçmek için önizlemeyi kapatın</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>Tıklanan yerde sınıflandırılmış nokta yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>{0} sınıfı zaten işaretli</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>{0} sınıfı katmanın sınıf listesinde yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>Raster katmanları için kullanılmaz: pipet bantları okur</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Sınıf pipeti: haritaya tıklayın, orada çizilen noktaların sınıfı işaretlenir. Ctrl+tıklama bir tane daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>Önizleme ve istatistikler, görünür kapsamın sınırlı bir yerel örneğini kullanır; filtreleme kaynağı okur.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>Görünür kapsamın sınırlı bir renk anlık görüntüsü hazırlanıyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>Renk anlık görüntüsü hazırlanamadı. Daha küçük bir görünür kapsam deneyin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>Renk seçimi, yakalanan görünür kapsama uygulanır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>Raster örneklemesi başarısız oldu. Daha küçük bir görünür kapsam deneyin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>Örneklenen raster önizlemesi hesaplanamadı.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>Bir rengin veya ifadenin önizlemesi için harita rasterin CRS'sinde ({0}) olmalıdır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>Tıklamanın altında çizilmiş nokta yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>Bu noktada {0} yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>{0} bir koşulda kullanılamaz</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>Nesne okunamadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>Tıklama çevresinde çok fazla nokta var: nesne okunamadı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>Tıklanan yerde {0} sınıfından nokta yok: nesnenin kendisine tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>Benzer nesneler okunamadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>Alan oranları içinde benzer nesne yok: oranları genişletin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>Yeni görünür kapsam için bir örnek hazırlanıyor. Hazır olduğunda yeniden tıklayın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>Yerel raster örneği hâlâ hazırlanıyor. Hazır olduğunda yeniden deneyin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>Bu işlenmiş katmanı filtrelemeden önce bir renk anlık görüntüsü hazırlayın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>{0} raster hedefi yapılandırılan piksel sınırına göre yeniden örneklendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2847"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>renk seçimi yakalanan kapsamla sınırlı; renkler stile ve ölçeğe bağlıdır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2849"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>raster kaynağı piksel sınırı dahilinde {0} hücreye yeniden örneklendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>raster seçimi her {0} pikselde bir okundu: ayarlardaki piksel sınırının üzerinde</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2854"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>yoğun raster seçimi, ana hattı hafif tutmak için yumuşatıldı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2901"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0} boşaltıldı, hiçbir şey seçimle eşleşmiyor: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2885"/>
        <source>failed</source>
        <translation>başarısız oldu</translation>
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
        <translation>Veritabanı dosyası mevcut değil: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Veritabanına bağlanılamadı {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Veritabanı dizini oluşturulamadı {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Veritabanı dosyası oluşturulamadı {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>FilterMate veritabanı başlatılamıyor: bağlantı başarısız</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Veritabanına bağlanırken kritik hata: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>Veritabanı başlatma sırasında hata: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Veritabanı dosyası mevcut değil: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>{db_file_path} veritabanına bağlanılamadı: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Mekânsal dizin oluşturmak için QGIS Processing modülü kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Mekânsal dizin oluşturulamıyor: katman geçersiz veya kaynak bulunamadı.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>PostgreSQL katmanları algılandı ancak psycopg2 kurulu değil. Yerel Spatialite arka ucu kullanılıyor. Büyük veri kümelerinde daha iyi performans için psycopg2 kurun.</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2481"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>{0} nesne seçildi; bu, bir web hizmetine gönderilebilen {1} sınırını aşıyor: seçimi daraltın veya bir öznitelik filtresi kullanın.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Katmanınızı bir dosyaya kaydedin</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Katmanlarınızı dışa aktaracağınız klasörü seçin</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>Dışa aktarılan verilerinizi bir zip dosyasına kaydedin</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0} katman</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> {0} grupta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} grup dışı</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>Hedef: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Grup algılanmadı - tüm katmanlar kök seviyesinde</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="154"/>
        <source>Annuler</source>
        <translation>İptal</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="160"/>
        <source>Exporter</source>
        <translation>Dışa Aktar</translation>
    </message>
</context>
<context>
    <name>ExtensionRegistry</name>
    <message>
        <location filename="../extensions/registry.py" line="398"/>
        <source>install the QGIS plugin {0}</source>
        <translation>{0} QGIS eklentisini yükleyin</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>{0} yükleyin</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>{1} eksik olduğu için {0} uzantısı kapalı: {2}, ardından QGIS'i yeniden başlatın.</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">Filtre yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>Kaydedilecek aktif filtre yok.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>Favori ekle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>Favori adı:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Favori '{0}' başarıyla eklendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="511"/>
        <source>Export Favorites</source>
        <translation>Favorileri dışa aktar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="535"/>
        <source>Exported {0} favorites</source>
        <translation>{0} favori dışa aktarıldı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="537"/>
        <source>Failed to export favorites</source>
        <translation>Favorileri dışa aktarma başarısız</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Import Favorites</source>
        <translation>Favorileri içe aktar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Mevcut favorilerle birleştirilsin mi?

Evet = Mevcut olanlara ekle
Hayır = Tüm mevcut olanları değiştir</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>{0} favori içe aktarıldı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>Hiçbir favori içe aktarılmadı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Favori yöneticisi başlatılmadı. Lütfen FilterMate'i yeniden başlatın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>Favori yöneticisi iletişim kutusu kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>Hata: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">{0} kez kullanıldı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">Geçerli filtreyi favorilere ekle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">Filtre ekle (aktif filtre yok)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">Favorileri yönet...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation type="obsolete">Dışa aktar...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation type="obsolete">İçe aktar...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation type="obsolete">Genel favoriler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">Genele kopyala...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── Mevcut genel favoriler ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(Genel favori yok)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">Bakım</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">Projeye kaydet (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">Projeden geri yükle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">Öksüz projeleri temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">Veritabanı istatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">Geçersiz ad</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>Favori adı boş olamaz.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>Yinelenen ad</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>'{0}' adlı bir favori zaten var.
Değiştirmek istiyor musunuz?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>Favori genel favorilere kopyalandı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>Genel favorilere kopyalama başarısız</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">Genel Favoriler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0} genel favori mevcut.

Genel favoriler tüm projeler arasında paylaşılır.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>{0} favori proje dosyasına kaydedildi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>Kaydetme başarısız</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>Proje dosyasından {0} favori geri yüklendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>Projede geri yüklenecek favori bulunamadı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0} öksüz proje temizlendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>Temizlenecek öksüz proje yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>FilterMate Veritabanı İstatistikleri

Toplam favoriler: {0}
   Proje: {1}
   Öksüzler: {2}
   Genel: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>Favorilere göre en iyi projeler:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>FilterMate İstatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Sık Kullanılanlar Yöneticisi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Henüz kaydedilmiş sık kullanılan yok.

Bir katmana filtre uygulayın, ★ göstergesine tıklayın ve ilk sık kullanılanınızı kaydetmek için «Geçerli filtreyi sık kullanılanlara ekle»yi seçin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">Resource Sharing'ten içe aktar…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">Resource Sharing'te yayımla…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">Yayımla (kaydedilmiş sık kullanılan yok)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>FilterMate yapılandırma dizini henüz başlatılmadı — önce FilterMate ile bir QGIS projesi açın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">Resource Sharing uzantısı aktif değil. FilterMate ayarlarında 'favorites_sharing' seçeneğini etkinleştirin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">Paylaşılan sık kullanılanlar hizmeti kullanılamıyor.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">Paylaşılan sık kullanılanlar seçici başarısız oldu: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">Henüz yayımlanacak sık kullanılanınız yok. Önce ★ menüsünden bir filtre kaydedin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">Yayımlama iletişim kutusu açılamadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>Favoriler henüz hazır değil: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>'{0}' kaldırılamadı: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>Henüz kaydedilmiş favori yok — bir filtre uygulayın, ardından ilk favorinizi kaydetmek için ★ göstergesine tıklayın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>Favori yöneticisi açılamadı. Ayrıntılar filtermate.log dosyasında.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>'{0}' değiştirilemedi: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>'{0}' kaydedilemedi: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>Genel favori içe aktarılamadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>Genele kopyalanamadı: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>Favoriler proje dosyasına kaydedilemedi: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>Yetim projeler temizlenemedi. Ayrıntılar filtermate.log dosyasında.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>Veritabanı istatistikleri kullanılamıyor. Ayrıntılar filtermate.log dosyasında.</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="204"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Favori Yöneticisi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1165"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kaydedilmiş Favoriler ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="266"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Ad, ifade, etiket veya açıklamaya göre ara...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>Genel</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>İfade</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>Uzak</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>Favori adı</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>Ad:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Açıklama (otomatik oluşturulmuş, düzenlenebilir)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>Açıklama:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Virgülle ayrılmış etiketler girin (ör. urban, population, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Etiketler favorileri düzenlemeye ve aramaya yardımcı olur.
Birden fazla etiketi virgülle ayırın.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>Etiketler:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>Kaynak katman:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>Sağlayıcı:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>Kullanıldı:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>Oluşturuldu:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kaynak Katman İfadesi:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>Kaynak katman için filtre ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Filtrelenmiş Uzak Katmanlar:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>Katman</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>Özellikler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Bu favoride uzak katman yok&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>Uygula</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Bu favori filtreyi projeye uygula</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>Değişiklikleri kaydet</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>Bu favorideki değişiklikleri kaydet</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="733"/>
        <source>Delete</source>
        <translation>Sil</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="736"/>
        <source>Permanently delete this favorite</source>
        <translation>Bu favoriyi kalıcı olarak sil</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="739"/>
        <source>Close</source>
        <translation>Kapat</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>Bu iletişim kutusunu kapat</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="849"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Favoriler ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1015"/>
        <source>Remote ({0})</source>
        <translation>Uzak ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete Favorite</source>
        <translation>Favoriyi sil</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Favori '{0}' silinsin mi?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>Uzak Katmanlar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1303"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kaydedilmiş Favoriler (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Favori Yöneticisi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>No favorites saved yet.

Click the ★ indicator and select 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Henüz kaydedilmiş favori yok.

İlk favorinizi kaydetmek için ★ göstergesine tıklayın ve 'Geçerli filtreyi favorilere ekle' seçeneğini seçin.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>Paylaşılan…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>QGIS Resource Sharing koleksiyonları aracılığıyla paylaşılan sık kullanılanlara göz atın</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>Yayımla…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Seçilen sık kullanılanları bir Resource Sharing koleksiyonunda yayımla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">«{0}» silinemedi. Sık kullanılan hâlâ veritabanında — ayrıntılar için FilterMate günlüğüne bakın.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>Sık kullanılanları kapsama göre filtrele (sahip × proje).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>Tümü</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>Paylaşılan · Tüm projeler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>Paylaşılan · Bu proje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>Benimkiler · Tüm projeler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>Benimkiler · Bu proje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>Benimkiler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>Paylaşılan</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>Bu proje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>Tüm projeler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>Proje kapsamı, sık kullanılan oluşturulduğunda ayarlanır. Proje değiştirmek için filtreleme sekmesinden (yakında) taşıyın.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>Görünürlük:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (herkesle paylaşıldı)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (siz)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — kaydederken 'Benimkiler' seçmek sahipliği size aktarır</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>'{0}' kaydedilemedi: {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>'{0}' silinemedi: {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>'{0}' veritabanında yoktu — yenileyip tekrar deneyin.</translation>
    </message>
</context>
<context>
    <name>FeedbackModule</name>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="112"/>
        <source>Exporting {0} layer(s)</source>
        <translation>{0} katman dışa aktarılıyor</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="168"/>
        <source>Large dataset ({0} features) using {1}. Consider using PostgreSQL for optimal performance.</source>
        <translation>Büyük veri kümesi ({0} nesne), kullanılan: {1}. En iyi performans için PostgreSQL kullanmayı düşünün.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="176"/>
        <source>Medium-large dataset ({0} features) using {1}. PostgreSQL recommended for better performance.</source>
        <translation>Orta-büyük veri kümesi ({0} nesne), kullanılan: {1}. Daha iyi performans için PostgreSQL önerilir.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="113"/>
        <source>Processing {0} layer(s)</source>
        <translation>{0} katman işleniyor</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="110"/>
        <source>Removing filters from {0} layer(s)</source>
        <translation>{0} katmandan filtreler kaldırılıyor</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="111"/>
        <source>Resetting {0} layer(s)</source>
        <translation>{0} katman sıfırlanıyor</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="109"/>
        <source>Starting filter on {0} layer(s)</source>
        <translation>{0} katmanda filtreleme başlatılıyor</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="137"/>
        <source>Successfully exported {0} layer(s)</source>
        <translation>{0} katman başarıyla dışa aktarıldı</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="134"/>
        <source>Successfully filtered {0} layer(s)</source>
        <translation>{0} katman başarıyla filtrelendi</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="138"/>
        <source>Successfully processed {0} layer(s)</source>
        <translation>{0} katman başarıyla işlendi</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="135"/>
        <source>Successfully removed filters from {0} layer(s)</source>
        <translation>{0} katmandan filtreler başarıyla kaldırıldı</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="136"/>
        <source>Successfully reset {0} layer(s)</source>
        <translation>{0} katman başarıyla sıfırlandı</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="604"/>
        <source>View</source>
        <translation>Görüntüle</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="606"/>
        <source>Change</source>
        <translation>Değiştir</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>Bir klasör seçin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>Bir dosya seçin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>Bir dosyaya kaydet</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="664"/>
        <source>View</source>
        <translation>Görüntüle</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="666"/>
        <source>Change</source>
        <translation>Değiştir</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>Bir simge seçin</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Katman geçersiz veya kaynağı bulunamıyor. İşlem iptal edildi.</translation>
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
        <translation>FilterMate panelini aç</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>Yapılandırmayı ve veritabanını sıfırla</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Varsayılan yapılandırmayı geri yükle ve SQLite veritabanını sil</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>Yapılandırmayı Sıfırla</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>Yapılandırma başarıyla sıfırlandı.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>Varsayılan yapılandırma dosyası bulunamadı.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>Veritabanı silindi: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>Yeniden başlatma gerekli</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>Eski yapılandırma algılandı</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>bilinmeyen sürüm</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>Bozuk yapılandırma algılandı</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Yapılandırma sıfırlanmadı. Bazı özellikler düzgün çalışmayabilir.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>Yapılandırma varsayılan değerlerle oluşturuldu</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Bozuk yapılandırma sıfırlandı. Varsayılan ayarlar geri yüklendi.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Eski yapılandırma sıfırlandı. Varsayılan ayarlar geri yüklendi.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>Yapılandırma en son sürüme güncellendi</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Yapılandırma güncellendi: yeni ayarlar mevcut ({sections}). Seçenekler menüsünden erişin.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>Geometri Basitleştirme</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>Optimizasyon Eşikleri</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>Geometri doğrulama ayarı</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Geçersiz geometri filtreleme başarıyla devre dışı bırakıldı.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Geçersiz geometri filtreleme değiştirilmedi. Bazı özellikler dışa aktarmalardan hariç tutulabilir.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Eski bir yapılandırma ({}) tespit edildi.

Varsayılan ayarlara sıfırlamak istiyor musunuz?

• Evet: Sıfırla (bir yedek oluşturulacak)
• Hayır: Mevcut yapılandırmayı koru (sorunlara neden olabilir)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>Yapılandırma dosyası bozuk ve okunamıyor.

Varsayılan ayarlara sıfırlamak istiyor musunuz?

• Evet: Sıfırla (mümkünse bir yedek oluşturulacak)
• Hayır: İptal (eklenti düzgün çalışmayabilir)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>Yapılandırma sıfırlama</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>Yapılandırmanın sıfırlanması gerekiyor.

Devam etmek istiyor musunuz?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>Yapılandırma geçişi sırasında hata: {}</translation>
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
        <translation>Varsayılan yapılandırmaya sıfırlamak istediğinizden emin misiniz?

Bu:
- Varsayılan ayarları geri yükleyecek
- Katman veritabanını silecek

Değişiklikleri uygulamak için QGIS yeniden başlatılmalıdır.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>Yapılandırma sıfırlandı.

Değişiklikleri uygulamak için lütfen QGIS'i yeniden başlatın.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>Başlatma hatası: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} referanslı katman yüklenmedi ({layers_list}). Yedek görüntüleme kullanılıyor.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>{filename} silinemedi: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">Sıfırlama sırasında hata: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;FilterMate&lt;/b&gt; kullandığınız için teşekkürler!&lt;br&gt;Discord topluluğumuza katılarak:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;Yardım ve destek alın&lt;/li&gt;&lt;li&gt;Hata ve sorunları bildirin&lt;/li&gt;&lt;li&gt;Yeni özellikler önerin&lt;/li&gt;&lt;li&gt;Diğer kullanıcılarla ipuçlarını paylaşın&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  Discord'da bize katılın</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>Bunu bir daha gösterme</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>Kapat</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Eklenti yüklenirken hata: {0}. Ayrıntılar için QGIS Python konsolunu kontrol edin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Current layer: {0}</source>
        <translation>Geçerli katman: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7418"/>
        <source>No layer selected</source>
        <translation>Katman seçilmedi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>Selected layers:
{0}</source>
        <translation>Seçili katmanlar:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>No layers selected</source>
        <translation>Katman seçilmedi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7448"/>
        <source>No expression defined</source>
        <translation>İfade tanımlanmadı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7460"/>
        <source>Display expression: {0}</source>
        <translation>Görüntüleme ifadesi: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7477"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>Özellik kimliği: {0}
İlk öznitelik: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>Yapılandırma sıfırlanamadı. Eklenti klasörünün yazılabilir olduğunu denetleyip tekrar deneyin. Ayrıntılar filtermate.log dosyasında.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>FilterMate 5'teki yenilikler</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;FilterMate artık raster ve nokta bulutu katmanlarıyla çalışıyor.&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; geçerli katmana uyum sağlar: bir rasterin değer aralığı ve sınıfları, bir LiDAR nokta bulutunun sınıfları, yüksekliği ve öznitelikleri.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; bu seçimi, alışılmış yüklemler ve tampon bölgeyle her türden katmanla ilişkilendirir: bir yükseklik aralığındaki parseller, binaların altındaki LiDAR noktaları, bir belediye sınırına göre kırpılmış bir SAM.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; filtrelenmiş rasterleri (GeoTIFF, COG) ve nokta bulutlarını (LAZ, COPC) yazar.&lt;/li&gt;&lt;li&gt;Processing algoritmaları ve modelleri, qgis_process, Python ve REST API'leri.&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>Kullanıcı kılavuzunu aç</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="409"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Bu ifade bir hizmet için güvenle değerlendirilemez.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Hizmet okunamadı. Lütfen yeniden deneyin.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>Read failed</source>
        <translation>Okuma başarısız oldu</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="287"/>
        <source>Loading filtered extent…</source>
        <translation>Filtrelenmiş kapsam yükleniyor…</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="404"/>
        <source>The expression is not valid for this layer. Check its syntax and field names.</source>
        <translation>İfade bu katman için geçerli değil. Sözdizimini ve alan adlarını kontrol edin.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="407"/>
        <source>A virtual field of this layer cannot be evaluated safely for a service.</source>
        <translation>Bu katmanın sanal bir alanı bir hizmet için güvenle değerlendirilemez.</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="319"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>PostgreSQL katmanları algılandı ({0}) ancak psycopg2 yüklü değil.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="419"/>
        <source>Cleared {0} caches</source>
        <translation>{0} önbellek temizlendi</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="925"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Yerleşik panel oluşturulamadı: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="935"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Yerleşik panel görüntülenemedi: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1501"/>
        <source>Error executing {0}: {1}</source>
        <translation>{0} yürütülürken hata: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1513"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Eklenti düşük modda çalışıyor (altıgen servisler kullanılamıyor). Performans düşebilir.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate HATASI</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>{0} yürütülemiyor: bileşen başlatma başarısız.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>{0} yapılamıyor: katman geçersiz veya kaynak bulunamadı.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2792"/>
        <source>All filters cleared - </source>
        <translation>Tüm filtreler temizlendi - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2793"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>Ana katmanda {0}{1} özellik görünür</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2805"/>
        <source>Error: result handler missing</source>
        <translation>Hata: sonuç işleyici eksik</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2822"/>
        <source>Error during filtering: {0}</source>
        <translation>Filtreleme sırasında hata: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2946"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0} öksüz favori kurtarıldı: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3112"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Katman yüklemesi başarısız - yeniden denemek için tıklayın</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3164"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} katman başarıyla yüklendi</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2095"/>
        <source>filter</source>
        <translation>filter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2097"/>
        <source>unfilter</source>
        <translation>unfilter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2100"/>
        <source>FilterMate – Edit Mode Detected</source>
        <translation>FilterMate – Edit Mode Detected</translation>
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
        <translation>Save Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2119"/>
        <source>Discard Changes &amp; {0}</source>
        <translation>Discard Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2126"/>
        <source>Cancel</source>
        <translation>İptal</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2150"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1331"/>
        <source>Pick a layer in the EXPLORING tab before running &apos;{0}&apos;.</source>
        <translation>'{0}' çalıştırılmadan önce EXPLORING sekmesinden bir katman seçin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="852"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} katman filtreli kalıyor: {1}. Filtreyi kaldırmak için seçeneği yeniden açın.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2624"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>Bir sunucu filtresi hazırlanıyor. Başka bir işlem başlatmadan önce bitmesini bekleyin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1773"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>Bir FilterMate API işlemi çalışıyor. Bitmesini bekleyin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="458"/>
        <source>Adding layers</source>
        <translation>Katmanlar ekleniyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="462"/>
        <source>Existing project loaded</source>
        <translation>Mevcut proje yüklendi</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="455"/>
        <source>Exporting data</source>
        <translation>Veriler dışa aktarılıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="452"/>
        <source>Filtering data</source>
        <translation>Veriler filtreleniyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="461"/>
        <source>New project</source>
        <translation>Yeni proje</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="457"/>
        <source>Redo filter</source>
        <translation>Filtreyi yinele</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="463"/>
        <source>Reloading layers</source>
        <translation>Katmanlar yeniden yükleniyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="460"/>
        <source>Removing all layers</source>
        <translation>Tüm katmanlar kaldırılıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="459"/>
        <source>Removing layers</source>
        <translation>Katmanlar kaldırılıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="454"/>
        <source>Reseting data</source>
        <translation>Veriler sıfırlanıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="456"/>
        <source>Undo filter</source>
        <translation>Filtreyi geri al</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="453"/>
        <source>Unfiltering data</source>
        <translation>Verilerin filtresi kaldırılıyor</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>Başlatma hatası: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Arayüz yapılandırması tamamlanmadı - günlükleri kontrol edin</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">Arayüz boyut hatası: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>Favori yöneticisi kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} favori kaydedildi
Uygulamak veya yönetmek için tıklayın</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Kaydedilmiş favori yok
Geçerli filtreyi eklemek için tıklayın</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <location filename="../ui/controllers/backend_controller.py" line="822"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>{1} katman için {0} arka ucu zorlandı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>Arka uç denetleyicisi kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>PostgreSQL otomatik temizleme etkinleştirildi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>PostgreSQL otomatik temizleme devre dışı bırakıldı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>PostgreSQL oturum görünümleri temizlendi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Temizlenecek görünüm yok veya temizleme başarısız</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <location filename="../ui/controllers/backend_controller.py" line="1089"/>
        <source>No PostgreSQL connection available</source>
        <translation>Kullanılabilir PostgreSQL bağlantısı yok</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>Şema diğer oturumlardan {0} görünüm içeriyor.
Yine de silinsin mi?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>Diğer oturumlar aktif</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>Şema temizleme iptal edildi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Şema '{0}' başarıyla silindi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <location filename="../ui/controllers/backend_controller.py" line="1090"/>
        <source>Schema cleanup failed</source>
        <translation>Şema temizleme başarısız</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL Oturum Bilgisi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>Tema uyarlandı: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>Karanlık mod</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>Açık mod</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4116"/>
        <location filename="../ui/controllers/exploring_controller.py" line="884"/>
        <source>Selected features have no geometry.</source>
        <translation>Seçili özelliklerin geometrisi yok.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4135"/>
        <location filename="../ui/controllers/exploring_controller.py" line="885"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Özellik seçilmedi. Açılır listeden bir özellik seçin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5319"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>Seçilen katman geçersiz veya kaynağı bulunamıyor.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6114"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Negatif tampon (erozyon): poligonları içe doğru daraltır</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6117"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Metre cinsinden tampon değeri (pozitif=genişlet, negatif=poligonları daralt)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6619"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Eklenti {0} vektör katmanla etkinleştirildi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6718"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Eklenti otomatik olarak yeniden yüklenemedi.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Eklenti yeniden yüklenirken hata: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6798"/>
        <source>Layer properties reset to defaults</source>
        <translation>Katman özellikleri varsayılanlara sıfırlandı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6799"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Katman özelliklerini sıfırlarken hata: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>Filter</source>
        <translation>Filtrele</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>Son filtreyi geri al</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>Son filtreyi yinele</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>Filtreleri kaldır</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>Katmanları dışa aktar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>FilterMate Hakkında</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>Seçili nesneleri sorgula</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>Seçili nesnelere yakınlaştır</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>Nesneleri haritada seç</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>Nesneleri haritada izle</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">Üç seçim kipini bağla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>Katman özelliklerini sıfırla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>Geçerli katmanı izle</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>Filtrelenecek katmanlar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>Mevcut filtreyle birleştir</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>Geometrik yüklemler</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>Tampon mesafesi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>Tampon türü</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>Dışa aktarılacak katmanlar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>Dışa aktarma projeksiyonu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>Stilleri dışa aktar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>Dışa aktarma biçimi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>Çıktı klasörü</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>Dışa aktarmayı zip'le</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>Panel yerleşimi uygulanamadı; varsayılan boyutlar kullanılıyor. Ayrıntılar filtermate.log dosyasında.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6890"/>
        <location filename="../ui/controllers/backend_controller.py" line="682"/>
        <source>Vector</source>
        <translation>Vektör</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>Tekli ve çoklu seçimleri bağla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>'{0}' şeması ve aşağıdaki {1} geçici nesne silinecek:</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>... ve {0} tane daha</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>'{0}' şeması boş ve silinecek.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>FilterMate şemasını sil</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>Read failed</source>
        <translation>Okuma başarısız oldu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Hizmet okunamadı. Lütfen yeniden deneyin.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4589"/>
        <source>Loading filtered extent…</source>
        <translation>Filtrelenmiş kapsam yükleniyor…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5184"/>
        <location filename="../ui/controllers/exploring_controller.py" line="742"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3658"/>
        <source>Loading selected values…</source>
        <translation>Seçili değerler yükleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Bu ifade bir hizmet için güvenle değerlendirilemez.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2715"/>
        <source>Error evaluating expression: {0}</source>
        <translation>İfade değerlendirilirken hata: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2716"/>
        <source>Expression Evaluation</source>
        <translation>İfade Değerlendirmesi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="444"/>
        <source>Loading values…</source>
        <translation>Değerler yükleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="846"/>
        <source>Loading zoom extent…</source>
        <translation>Yakınlaştırma kapsamı yükleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>Hiçbir geometrili nesne seçimle eşleşmiyor.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="434"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>Yalnızca sınırlı bir değer kümesi gösteriliyor. Diğer değerleri bulmak için aramayı daraltın.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5119"/>
        <location filename="../ui/controllers/exploring_controller.py" line="551"/>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <location filename="../ui/controllers/exploring_controller.py" line="691"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3651"/>
        <source>Selection</source>
        <translation>Seçim</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="550"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>Hizmet seçimi anahtar sınırını aşıyor. Seçimi daraltın.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <source>This service has no stable key for the selection.</source>
        <translation>Bu hizmetin seçim için kararlı bir anahtarı yok.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="436"/>
        <location filename="../ui/controllers/exploring_controller.py" line="438"/>
        <source>Values</source>
        <translation>Değerler</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="808"/>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>Zoom</source>
        <translation>Yakınlaştır</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1087"/>
        <source>&apos;{0}&apos; is not a FilterMate temporary schema: it is not dropped</source>
        <translation>'{0}' bir FilterMate geçici şeması değil: silinmeyecek</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1312"/>
        <source>... and {0} more (see details)</source>
        <translation>... ve {0} tane daha (ayrıntılara bakın)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="778"/>
        <source>Auto (Default)</source>
        <translation>Otomatik (varsayılan)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="786"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Tüm katmanlar için en uygun arka ucu otomatik seç</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="817"/>
        <source>Auto-selected backends for {0} layer(s)</source>
        <translation>{0} katman için arka uçlar otomatik seçildi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="838"/>
        <source>Backend forced to {0} for &apos;{1}&apos;</source>
        <translation>'{1}' için arka uç {0} olarak zorlandı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="841"/>
        <source>Backend set to Auto for &apos;{0}&apos;</source>
        <translation>'{0}' için arka uç Otomatik olarak ayarlandı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1336"/>
        <source>Cleanup cancelled</source>
        <translation>Temizleme iptal edildi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="807"/>
        <source>Clear ALL FilterMate temporary tables from all databases</source>
        <translation>FilterMate'in TÜM geçici tablolarını tüm veritabanlarından temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="797"/>
        <source>Clear Temp Tables</source>
        <translation>Geçici tabloları temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1317"/>
        <source>Clear all FilterMate temporary tables</source>
        <translation>FilterMate'in tüm geçici tablolarını temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="802"/>
        <source>Clear temporary tables for the current project only</source>
        <translation>Geçici tabloları yalnızca geçerli proje için temizle</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="828"/>
        <source>Cleared {0} temporary table(s) for current project</source>
        <translation>Geçerli proje için {0} geçici tablo temizlendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1340"/>
        <source>Cleared {0} temporary table(s) globally</source>
        <translation>{0} geçici tablo genel olarak temizlendi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1307"/>
        <source>FilterMate will permanently delete {0} temporary table(s) / view(s) from the databases of the project and of the PostgreSQL connection:</source>
        <translation>FilterMate, projenin ve PostgreSQL bağlantısının veritabanlarından {0} geçici tabloyu / görünümü kalıcı olarak silecek:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="791"/>
        <source>Force {0} for All Layers</source>
        <translation>Tüm katmanlar için {0} zorla</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="742"/>
        <source>No alternative backends available for this layer</source>
        <translation>Bu katman için kullanılabilir alternatif arka uç yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1333"/>
        <location filename="../ui/controllers/backend_controller.py" line="1342"/>
        <source>No temporary tables found</source>
        <translation>Geçici tablo bulunamadı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="830"/>
        <source>No temporary tables found for current project</source>
        <translation>Geçerli proje için geçici tablo bulunamadı</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1080"/>
        <source>Schema &apos;{0}&apos; does not exist: nothing to drop</source>
        <translation>'{0}' şeması mevcut değil: silinecek bir şey yok</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1083"/>
        <source>Schema &apos;{0}&apos; holds objects FilterMate did not create ({1}): it is not dropped</source>
        <translation>'{0}' şeması FilterMate'in oluşturmadığı nesneler içeriyor ({1}): silinmeyecek</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="762"/>
        <source>Select Backend:</source>
        <translation>Arka uç seçin:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1313"/>
        <source>Your own tables and layers are not touched. Continue?</source>
        <translation>Kendi tablolarınıza ve katmanlarınıza dokunulmaz. Devam edilsin mi?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="805"/>
        <source>🌐 All Projects (Global)</source>
        <translation>🌐 Tüm projeler (genel)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="800"/>
        <source>📁 Current Project</source>
        <translation>📁 Geçerli proje</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>The filter was not launched: its selection changed or could not be read. Click Filter again.</source>
        <translation>Filtre başlatılmadı: seçimi değişti veya okunamadı. Yeniden Filtrele'ye tıklayın.</translation>
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
        <translation>TEKLİ SEÇİM</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>ÇOKLU SEÇİM</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>ÖZEL SEÇİM</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>FİLTRELEME</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>DIŞA AKTARMA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>YAPILANDIRMA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>Dışa aktarma için CRS seç</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>Dışa Aktar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2330"/>
        <source>AND</source>
        <translation>VE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2335"/>
        <source>AND NOT</source>
        <translation>VE DEĞİL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2340"/>
        <source>OR</source>
        <translation>VEYA</translation>
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
        <translation>Çoklu katman filtreleme</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Seçili katman için eklemeli filtreleme</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>Jeo-mekansal filtreleme</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>Tampon</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>İfade katmanı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>Geometrik yüklem</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>Çıktı formatı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>Filtre</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>Sıfırla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>Dışa aktarılacak katmanlar</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>Katman projeksiyonu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>Stilleri kaydet</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>Veri türü dışa aktarma</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>Dosya/dizin adı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Kaynak katman için tam geometriler yerine merkeznoktaları kullanın (karmaşık poligonlar için daha hızlı)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Metre cinsinden tampon değeri (pozitif=genişlet, negatif=poligonları daralt)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>Tampon hassasiyeti için segment sayısı</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>Toplu mod</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="633"/>
        <source>FilterMate was unloaded</source>
        <translation>FilterMate kaldırıldı</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="119"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>işlenmiş veya desteklenmeyen raster: filtre hedefi olamaz</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="582"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>işlenmiş raster kaynakları yerel bir renk yakalaması gerektirir; sayısal piksel seçimleri kullanılamaz</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="654"/>
        <source>the source layer itself was not changed</source>
        <translation>kaynak katmanın kendisi değiştirilmedi</translation>
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
        <translation>Ana katmanda {count} özellik görünür</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Tüm filtreler temizlendi - ana katmanda {count} özellik görünür</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>Görev başarısız</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>Filtre başarısız: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0} daha)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>Katmanlar filtrelendi</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Katmanlar önceki duruma filtrelendi</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>Katman filtreleri kaldırıldı</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>Filtreleme görevi: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>Dışa aktarma görevi: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>İstisna: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>Filtre uygulanmadı, önceki filtre korundu: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>Filtreleme sırasında kaldırılan katman(lar), dışarıda bırakıldı: {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>Zeminden yüksekliği uzaktan hesaplamadan önce yararlı bir seçim bölgesi çizin</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>DTM ile nokta bulutunun ortak bir yararlı kapsamı yok</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>Yararlı seçimin çokgen alanı yok</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>Zeminden yükseklik yalnızca yararlı alanı kapsar; Filtreyi kaldır özgün bulutu geri yükler</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Python Menüleri ve Araç Çubukları</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Özellik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Değer</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Özellik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Değer</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="262"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>PostgreSQL katmanları algılandı ({0}) ancak psycopg2 yüklü değil. Eklenti bu katmanları kullanamıyor. PostgreSQL desteğini etkinleştirmek için psycopg2 yükleyin.</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>Kaydedilen kaynak açılamadı</translation>
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
        <translation>PostgreSQL katmanı '{0}': Bozuk veri algılandı.

Bu katman PostgreSQL'de bulunmayan 'virtual_id' kullanıyor.
Bu hata FilterMate'in önceki bir sürümünden kaynaklanıyor.

Çözüm: Bu katmanı FilterMate projesinden kaldırın, ardından yeniden ekleyin.
PostgreSQL tablosunun tanımlı bir PRIMARY KEY içerdiğinden emin olun.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>Katman '{0}' PRIMARY KEY içermiyor. Sınırlı özellikler: materyalize görünümler devre dışı. Öneri: optimum performans için PRIMARY KEY ekleyin.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>İstisna: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: bu sağlayıcı tam bir sunucu filtresini garanti edemez. Filtrelemeden önce sınırlı bir yerel kopya kullanın.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: seçili nesnelerin anahtar değerleri web hizmetinden okunamadı.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>önceki filtresini korur</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>filtrelenmeden bırakıldı</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: bu web hizmetinin benzersiz bir anahtar alanı yok (bildirilen anahtar, id, gml_id, cleabs, objectid...); bu nedenle seçili nesneler sunucu için listelenemiyor. Katman {1}. Bir öznitelik filtresi veya katmanın yerel bir kopyası işe yarar.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: bu katmanın benzersiz bir anahtar alanı yok ve nesne kimlikleri filtresinde listelenemiyor (sanal katman için benzersiz bir kimlik sütunu, yani uid gerekir). Katman {1}.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: listelenecek {1} nesne var; bu, bir web hizmetine gönderilebilen {2} sınırını aşıyor. Katman {3}. Seçimi daraltın, bir öznitelik filtresi kullanın veya katmanın yerel bir kopyası üzerinde çalışın.</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Optimizasyon Ayarları</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Optimizasyon ayarlarını yapılandır</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Otomatik optimizasyonları etkinleştir</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Optimizasyonları uygulamadan önce sor</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Otomatik-Centroid Ayarları</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Uzak katmanlar için otomatik-centroid'i etkinleştir</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Mesafe eşiği (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Özellik eşiği:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Tampon Optimizasyonları</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Tampon öncesi geometriyi basitleştir</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Tampon segmentlerini şuna düşür:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Genel</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Filtreleme için materialized view kullan</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Mekansal indeksleri otomatik oluştur</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>R-tree mekansal indeks kullan</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Sınırlayıcı kutu ön filtresi kullan</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Backend'ler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Önbellekleme</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Geometri önbelleğini etkinleştir</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Toplu İşlem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Parti boyutu:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Gelişmiş ayarlar performansı ve bellek kullanımını etkiler. Yalnızca sonuçlarını anlıyorsanız değiştirin.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Gelişmiş</translation>
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
        <translation>Önceki koşulla bağlantı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="799"/>
        <source>AND</source>
        <translation>VE</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="800"/>
        <source>OR</source>
        <translation>VEYA</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="801"/>
        <source>Attribute</source>
        <translation>Öznitelik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>Karşılaştırma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>arasında</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>Bu koşulu kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>Bir değerle veya başka bir öznitelikle karşılaştır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="821"/>
        <source>value</source>
        <translation>değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="822"/>
        <source>Value</source>
        <translation>Değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="825"/>
        <source>Highest value kept</source>
        <translation>Tutulan en yüksek değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>Gözlenen değerler: {0} ile {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>Bu öznitelik için istatistik yok</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1053"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>Veri kümesinin diğer karolarına uygula</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1062"/>
        <source>CLASSES</source>
        <translation>SINIFLAR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Ground</source>
        <translation>Zemin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Vegetation</source>
        <translation>Bitki örtüsü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1069"/>
        <source>Buildings</source>
        <translation>Binalar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1070"/>
        <source>Above ground</source>
        <translation>Zemin üstü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1071"/>
        <source>Water</source>
        <translation>Su</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1072"/>
        <source>Without noise</source>
        <translation>Gürültüsüz</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">Yalnızca bu sınıfları işaretle</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">Tümü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">Hiçbiri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1101"/>
        <source>Point classes</source>
        <translation>Nokta sınıfları</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">ÖZNİTELİK ARALIKLARI</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (m)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">Tutulan en düşük yükseklik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">Tutulan en yüksek yükseklik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Intensity</source>
        <translation>Yoğunluk</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">Tutulan en düşük yoğunluk</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">Tutulan en yüksek yoğunluk</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">Dönüş</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">Tutulan lazer darbesi yankısı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">DTM üzerindeki yükseklik ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1290"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>Yüksekliğin ölçüldüğü sayısal arazi modeli</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1300"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>Noktaları arazi modelinin en az bu kadar üstünde tut</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>EXPRESSION</source>
        <translation>İFADE</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1379"/>
        <source>Point cloud expression</source>
        <translation>Nokta bulutu ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1380"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>İfadeyi elle düzenlemek için grubu işaretleyin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">Bu katman için yükseklik istatistiği yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1661"/>
        <source>Height above the terrain is unavailable</source>
        <translation>Araziden yükseklik kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">Tutulan noktalar: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Geçerli filtre: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">Herhangi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">İlk</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Last</source>
        <translation type="obsolete">Son</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Single</source>
        <translation type="obsolete">Tek</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1176"/>
        <source>ATTRIBUTES</source>
        <translation>ÖZNİTELİKLER</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1194"/>
        <source>+ Condition</source>
        <translation>+ Koşul</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1196"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>Katmanın bir özniteliğine koşul ekle</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1235"/>
        <source>Returns</source>
        <translation>Dönüşler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">Lazer darbelerinin ilk, son veya tekil dönüşlerini tut</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1242"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>İlk dönüş (ReturnNumber = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1243"/>
        <source>Last return (ReturnNumber = NumberOfReturns)</source>
        <translation>Son dönüş (ReturnNumber = NumberOfReturns)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1244"/>
        <source>Single return (NumberOfReturns = 1)</source>
        <translation>Tekil dönüş (NumberOfReturns = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1349"/>
        <source>Return number</source>
        <translation>Dönüş numarası</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1350"/>
        <source>Number of returns</source>
        <translation>Dönüş sayısı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1351"/>
        <source>Classification</source>
        <translation>Sınıflandırma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Scan angle</source>
        <translation>Tarama açısı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>User data</source>
        <translation>Kullanıcı verisi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Point source ID</source>
        <translation>Nokta kaynağı kimliği</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>GPS time</source>
        <translation>GPS zamanı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Red</source>
        <translation>Kırmızı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1357"/>
        <source>Green</source>
        <translation>Yeşil</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1358"/>
        <source>Blue</source>
        <translation>Mavi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1359"/>
        <source>Infrared</source>
        <translation>Kızılötesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Scan direction</source>
        <translation>Tarama yönü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Edge of flight line</source>
        <translation>Uçuş hattı kenarı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Synthetic</source>
        <translation>Sentetik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Key point</source>
        <translation>Anahtar nokta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Withheld</source>
        <translation>Alıkonulmuş</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1365"/>
        <source>Overlap</source>
        <translation>Örtüşme</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>Scanner channel</source>
        <translation>Tarayıcı kanalı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>Classification flags</source>
        <translation>Sınıflandırma bayrakları</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>Height above ground</source>
        <translation>Zemin üstü yükseklik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Quick class selection</source>
        <translation>Hızlı sınıf seçimi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">Hızlı seçim…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>All classes</source>
        <translation>Tüm sınıflar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>No class</source>
        <translation>Sınıf yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>Invert the selection</source>
        <translation>Seçimi tersine çevir</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Selection ▾</source>
        <translation>Seçim ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1115"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>Standartta bulunan ama bu katmanda hiç noktası olmayan sınıflar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1122"/>
        <source>Classes absent from the layer</source>
        <translation>Katmanda bulunmayan sınıflar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1146"/>
        <source>Similar objects: area ×</source>
        <translation>Benzer nesneler: alan ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>En küçük benzer nesne, tıklanan en küçük nesnenin oranı olarak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>En büyük benzer nesne, tıklanan en büyük nesnenin katı olarak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1164"/>
        <source>to ×</source>
        <translation>– ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1208"/>
        <source>Pipette on</source>
        <translation>Pipet açık</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1209"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>Kenar çubuğundaki değer pipetinin tıklamanın altında okuduğu öznitelik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1224"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>Alınan değer çevresindeki tolerans, özniteliğin gözlenen aralığının % değeri olarak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1236"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>Tüm dönüşleri veya lazer darbelerinin ilk, son ya da tekil dönüşlerini tut</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1241"/>
        <source>Any return</source>
        <translation>Herhangi bir dönüş</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1255"/>
        <source>HEIGHT / DTM</source>
        <translation>YÜKSEKLİK / DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>Always combined (AND) with the active group</source>
        <translation>Etkin grupla her zaman birleştirilir (AND)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1265"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · türetilmiş bulut</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1267"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>Yükseklik, PDAL tarafından bir arka plan görevinde türetilmiş bir nokta bulutuna hesaplanır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1370"/>
        <source>{0} object(s)</source>
        <translation>{0} nesne</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>cut at the window read</source>
        <translation>okunan pencerede kesildi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1372"/>
        <source>shown as the whole class in their box</source>
        <translation>kutularında sınıfın tamamı olarak gösterilir</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1863"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>Katmanda bulunmayan diğer sınıflar ({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1954"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>Bir nesne, tıklama çevresinde okunan en büyük pencerenin dışına taşıyor ve orada kesildi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1956"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>Bulutun alt kümesi için çok fazla nesne var: önizleme ve filtrelenmiş bulut, çevrelerindeki kutuda sınıflarının tüm noktalarını korur; hedefler nesnelerin kendileri tarafından kesilir</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">Nokta bulutu filtresi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">Sınıflandırma</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">Tümü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">Hiçbiri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">Yükseklik (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">Yoğunluk</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="175"/>
        <source>Return number</source>
        <translation type="obsolete">Dönüş numarası</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="199"/>
        <source>Minimum</source>
        <translation type="obsolete">En az</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="200"/>
        <source>Maximum</source>
        <translation type="obsolete">En çok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Geçerli filtre: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">Herhangi</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>Uzak bir nokta bulutu için yararlı bir kapsam gerekir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>Bu nokta bulutu biçimi için PDAL okuyucusu yok</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>Uzak nokta bulutları için okunabilir sürüme sahip PDAL 2.4 veya üstü gerekir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>Uzak nokta bulutları, sınırlı okumalar için EPT veya COPC gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>Yararlı kapsam sonlu olmalı ve pozitif alana sahip olmalıdır</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="513"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>Uzak bir nokta bulutunu okumadan önce yararlı bir seçim bölgesi çizin</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="546"/>
        <source>The remote point cloud could not be read</source>
        <translation>Uzak nokta bulutu okunamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="550"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>Uzak nokta bulutu seçimi reddetti</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="811"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>Sınırlı zeminden yükseklik bulutu yalnızca AND veya AND NOT destekler; önce filtreyi kaldırın</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="837"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>Uzak bir nokta bulutunu kırpmak için PDAL 2.4 veya üstü gerekir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="888"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Disjoint tüm uzak bulutu okurdu; içeride kalan bir seçim yapın</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="895"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>Özgün uzak nokta bulutu açılamadı</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL Oturum Bilgisi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL Aktif</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Bağlantı Bilgisi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Bağlantı:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Geçici Şema:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Durum:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Geçici Görünümler</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Temizleme Seçenekleri</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Kapatırken otomatik temizlik</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>FilterMate kapatılırken geçici görünümleri otomatik temizle.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Şimdi Temizle</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Bu oturumda FilterMate tarafından oluşturulan tüm geçici görünümleri sil.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Geçici görünüm yok)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Görünüm yok</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Temizlenecek geçici görünüm yok.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Temizliği Onayla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Temizlik Tamamlandı</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Temizlik Sorunu</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Temizlik Başarısız</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL kullanılamıyor&lt;/b&gt;&lt;br&gt;&lt;br&gt;PostgreSQL özelliklerini kullanmak için psycopg2 yükleyin:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Ardından değişiklikleri uygulamak için QGIS'i yeniden başlatın.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Oturum: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>Bu oturumda {0} görünüm</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Bu, FilterMate tarafından oluşturulan {view_count} geçici görünümü silecek.

Kaydedilmemiş filtre sonuçları kaybolacak.

Devam edilsin mi?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped} geçici görünüm kaldırıldı.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Bazı görünümler kaldırılamadı: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Temizleme sırasında hata: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>Filtrelenecek katmanlar</translation>
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
        <translation>Tampon</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="105"/>
        <source>Band</source>
        <translation>Bant</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>Raster ifadesi</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="147"/>
        <source>Layers to export</source>
        <translation>Dışa aktarılacak katmanlar</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>Çıktı klasörü</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>Geometrik yüklemler</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>Piksel değeri</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>Eğim (derece)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>Eğim (%)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>Bakı (derece)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>Gölgelendirme (0-255)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>Kaynak raster yakalama için yeniden örneklendi (ızgara: {0}).</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: hedef raster yakalama için yeniden örneklendi (ızgara: {1}).</translation>
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
        <translation>FilterMate — Resource Sharing'te yayımla</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Sık kullanılanları yayımla&lt;/b&gt; — bir QGIS Resource Sharing koleksiyonuna paylaşılabilir paket yaz.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>Mevcut paketin üzerine yaz</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>Yayımla</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Hedef koleksiyon&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>Gözat…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Paket dosya adı&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>ör. bolgeler_bruksel</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;hedef&amp;gt;/filter_mate/favorites/&amp;lt;ad&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Koleksiyon üstverileri&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>Koleksiyon görüntülenecek adı</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>Ad:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>Yazar / kuruluş</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>Yazar:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>ör. CC-BY-4.0, MIT, Özel</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>Lisans:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>Virgülle ayrılmış etiketler</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="221"/>
        <source>Tags:</source>
        <translation>Etiketler:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="224"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="225"/>
        <source>Homepage:</source>
        <translation>Web sayfası:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="229"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Kısa açıklama (isteğe bağlı, düz metin)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>Açıklama:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Dahil edilecek sık kullanılanlar&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>Tümünü seç</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>Hiçbirini seçme</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Resource Sharing kökünde yeni koleksiyon…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>Özel dizin…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Resource Sharing kökünün altında oluşturulacak.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Dizin seçmek için 'Gözat…' düğmesine tıklayın.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>Koleksiyon dizini seçin</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} seçildi</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>Koleksiyon oluşturulamıyor</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Resource Sharing kökü bulunamadı. Bunun yerine dizin seçmek için 'Gözat…' kullanın.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>Bir dizin seçin</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Hedef dizin seçmek için 'Gözat…' düğmesine tıklayın.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>Seçili sık kullanılan yok</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Yayımlamak için en az bir sık kullanılan seçin.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>Yayımlama başarısız</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>Bilinmeyen hata.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>{0} sık kullanılan şuraya yayımlandı:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Koleksiyon bildirimi güncellendi:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>Yayımlama başarılı</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>Uzak depolar kullanılamıyor</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>Uzak depo yöneticisi başlatılmadı.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; konumuna yayımlama başarısız oldu.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>Klonu aç…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>Paket şuraya yazıldı:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>Commit &lt;code&gt;{0}&lt;/code&gt; &lt;b&gt;{1}&lt;/b&gt; konumuna pushlandı.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>Yapılandırılmış git_url yok — paket yerel olarak yazıldı. Kendi araçlarınızla elle pushlayın.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>Commit edilecek bir şey yok — paket içeriği değişmedi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>{0} deposuna yayımlanıyor...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>İptal</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>Yayımlanıyor</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>Yayımlama sürüyor</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>Arka planda bir yayımlama hâlâ çalışıyor. Yenisini başlatmadan önce bitmesini bekleyin.</translation>
    </message>
</context>
<context>
    <name>QFieldCloudExtension</name>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="194"/>
        <source>QFieldCloud Settings...</source>
        <translation>QFieldCloud Settings...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="226"/>
        <source>Export filtered layers to QFieldCloud</source>
        <translation>Export filtered layers to QFieldCloud</translation>
    </message>
</context>
<context>
    <name>QFieldCloudPushDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="102"/>
        <source>Export to QFieldCloud</source>
        <translation>Export to QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="117"/>
        <source>Active Filter</source>
        <translation>Active Filter</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="120"/>
        <source>No active filter</source>
        <translation>No active filter</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="121"/>
        <source>Filter:</source>
        <translation>Filter:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="123"/>
        <source>0 layers</source>
        <translation>0 layers</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="124"/>
        <source>Layers:</source>
        <translation>Layers:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="130"/>
        <source>QFieldCloud Project</source>
        <translation>QFieldCloud Project</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="135"/>
        <source>Project name:</source>
        <translation>Project name:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="139"/>
        <source>Description:</source>
        <translation>Açıklama:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="143"/>
        <source>Create new</source>
        <translation>Create new</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="144"/>
        <source>Update existing:</source>
        <translation>Update existing:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="148"/>
        <source>Mode:</source>
        <translation>Mode:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="158"/>
        <source>Layer Modes</source>
        <translation>Layer Modes</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Layer</source>
        <translation>Katman</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="184"/>
        <source>Export</source>
        <translation>Dışa Aktar</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="209"/>
        <source>{0} layers ({1} features)</source>
        <translation>{0} layers ({1} features)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="217"/>
        <source>{0} layers (no filter active)</source>
        <translation>{0} layers (no filter active)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Missing Name</source>
        <translation>Missing Name</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="290"/>
        <source>Please enter a project name.</source>
        <translation>Please enter a project name.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>Not Connected</source>
        <translation>Not Connected</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="297"/>
        <source>QFieldCloud is not connected. Please configure credentials first.</source>
        <translation>QFieldCloud is not connected. Please configure credentials first.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No Layers</source>
        <translation>No Layers</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="365"/>
        <source>No valid layers to export.</source>
        <translation>No valid layers to export.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>Export Error</source>
        <translation>Export Error</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="393"/>
        <source>Failed to export layer &apos;{0}&apos;: {1}</source>
        <translation>Failed to export layer '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="403"/>
        <source>GPKG export failed: {0}</source>
        <translation>GPKG export failed: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="420"/>
        <source>Push complete!</source>
        <translation>Push complete!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project successfully pushed to QFieldCloud!</source>
        <translation>Project successfully pushed to QFieldCloud!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Project: {0}</source>
        <translation>Project: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Files: {0}</source>
        <translation>Files: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>Duration: {0:.1f}s</source>
        <translation>Duration: {0:.1f}s</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="430"/>
        <source>URL: {0}</source>
        <translation>URL: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="438"/>
        <source>Warnings:</source>
        <translation>Warnings:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="440"/>
        <source>Push Complete</source>
        <translation>Push Complete</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="450"/>
        <source>Error: {0}</source>
        <translation>Hata: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push Failed</source>
        <translation>Push Failed</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="461"/>
        <source>Push failed:

{0}</source>
        <translation>Push failed:

{0}</translation>
    </message>
</context>
<context>
    <name>QFieldCloudSettingsDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="53"/>
        <source>QFieldCloud Configuration</source>
        <translation>QFieldCloud Configuration</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="66"/>
        <source>Server</source>
        <translation>Server</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="71"/>
        <source>URL:</source>
        <translation>URL:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="77"/>
        <source>Credentials</source>
        <translation>Credentials</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="81"/>
        <source>username</source>
        <translation>username</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="82"/>
        <source>Username:</source>
        <translation>Username:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="86"/>
        <source>password (for initial login)</source>
        <translation>password (for initial login)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="87"/>
        <source>Password:</source>
        <translation>Password:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="90"/>
        <source>JWT token (auto-filled after login)</source>
        <translation>JWT token (auto-filled after login)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="95"/>
        <source>Login</source>
        <translation>Login</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="96"/>
        <source>Login with username/password to get a token</source>
        <translation>Login with username/password to get a token</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="98"/>
        <source>Token:</source>
        <translation>Token:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="102"/>
        <source>Status:</source>
        <translation>Durum:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="105"/>
        <source>Test Connection</source>
        <translation>Test Connection</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="112"/>
        <source>Preferences</source>
        <translation>Preferences</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="117"/>
        <source>Default project:</source>
        <translation>Default project:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="119"/>
        <source>Trigger packaging after upload</source>
        <translation>Trigger packaging after upload</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="144"/>
        <source>Token stored</source>
        <translation>Token stored</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Missing Fields</source>
        <translation>Missing Fields</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="168"/>
        <source>Please fill in URL, username, and password.</source>
        <translation>Please fill in URL, username, and password.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="174"/>
        <source>Logging in...</source>
        <translation>Logging in...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="191"/>
        <source>Logged in as {0}</source>
        <translation>Logged in as {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="198"/>
        <source>Login failed: {0}</source>
        <translation>Login failed: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Missing Configuration</source>
        <translation>Missing Configuration</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="213"/>
        <source>Please configure URL and login first.</source>
        <translation>Please configure URL and login first.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="219"/>
        <source>Testing connection...</source>
        <translation>Testing connection...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="229"/>
        <source>Connected! ({0} projects accessible)</source>
        <translation>Connected! ({0} projects accessible)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="235"/>
        <source>Connection failed: {0}</source>
        <translation>Connection failed: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Missing URL</source>
        <translation>Missing URL</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/settings_dialog.py" line="247"/>
        <source>Server URL is required.</source>
        <translation>Server URL is required.</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxFeaturesListPickerWidget</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="924"/>
        <source>Type to filter...</source>
        <translation>Filtrelemek için yazın...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>Tümünü seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>Tümünü seç (alt küme dışı)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>Tümünü seç (alt küme)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>Tüm seçimi kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>Tüm seçimi kaldır (alt küme dışı)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>Tüm seçimi kaldır (alt küme)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Görüntü değerine göre sıralanmış ilk {0} nesne gösteriliyor. Katmanın tamamında aramak için metin filtresine yazın; &quot;Tümünü Seç&quot; tam listeyi yükler.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Katmanın {0} nesnesi, görüntü değerine göre sıralanmış olarak gösteriliyor. Katmanın tamamında aramak için metin filtresine yazın; &quot;Tümünü Seç&quot; tam listeyi yükler.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>Katmanın tamamında &quot;{0}&quot; için arama sonuçları.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1808"/>
        <source>Loading values…</source>
        <translation>Değerler yükleniyor…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1735"/>
        <source>Values</source>
        <translation>Değerler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Bu ifade bir hizmet için güvenle değerlendirilemez.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>Selection</source>
        <translation>Seçim</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>Uzak liste güvenli seçim sınırını aşıyor. Daha az nesne seçin veya önce katmanı filtreleyin.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="2008"/>
        <source>Loading selected values…</source>
        <translation>Seçili değerler yükleniyor…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>Tümünü seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>Tüm seçimi kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Geometri türüne göre tüm katmanları seç (Çizgiler)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Geometri türüne göre tüm katman seçimini kaldır (Çizgiler)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Geometri türüne göre tüm katmanları seç (Noktalar)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Geometri türüne göre tüm katman seçimini kaldır (Noktalar)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Geometri türüne göre tüm katmanları seç (Poligonlar)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Geometri türüne göre tüm katman seçimini kaldır (Poligonlar)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>Tüm raster katmanlarını seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>Tüm raster katmanlarının seçimini kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>Tüm nokta bulutu katmanlarını seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>Tüm nokta bulutu katmanlarının seçimini kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>bölgedeki pikseller</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>bölgedeki noktalar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>detaylar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>Raster hedef: kaynak geometri dışındaki pikseller NoData olur (içerdekiler Disjoint ile)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>Nokta bulutu hedefi: kaynak geometri dışındaki noktalar kaldırılır (içerdekiler Disjoint ile)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>Vektör hedef: geometrik yüklemi sağlayan detaylar korunur</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>Bu katmanı merkez noktalarıyla test etmek için sağdaki kareye tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="343"/>
        <source>Select all vector layers</source>
        <translation>Tüm vektör katmanlarını seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="345"/>
        <source>De-select all vector layers</source>
        <translation>Tüm vektör katmanlarının seçimini kaldır</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>Değer aralığı histogramı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>Tutulacak değer aralığını seçmek için tutamaçları sürükleyin veya tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>Histogram yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>Tutulan değerler: {0} ile {1} arası</translation>
    </message>
</context>
<context>
    <name>RasterExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="497"/>
        <source>Band</source>
        <translation type="obsolete">Bant</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="500"/>
        <source>Band whose values are selected</source>
        <translation type="obsolete">Değerleri seçilen bant</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">PİKSEL DEĞERİ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">Geçerli bandın piksel değeri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">Seçilen son {0} değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">Piksel seçici ile haritaya tıklayın. Ctrl+tıklama aralığı bu değere kadar genişletir.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>DEĞER ARALIĞI</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>En az</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>Tutulan en düşük değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>En çok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>Tutulan en yüksek değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">Haritada önizleme (diğer pikselleri gizle)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">SINIFLAR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">Raster sınıfları</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">Tümü</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">Hiçbiri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>RASTER İFADESİ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>Raster hesaplayıcı ifadesi; piksel, sonuç 0 olmadığı yerde tutulur</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>Raster ifadesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">Aralığı kullan</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">Geçerli değer aralığını ifade olarak yaz</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">Seçilen pikseller: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>Önce bir değer aralığı belirleyin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2219"/>
        <source>NoData</source>
        <translation>NoData</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="834"/>
        <source>Last values:</source>
        <translation type="obsolete">Son değerler:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="629"/>
        <source>Value of the current band under the cursor</source>
        <translation type="obsolete">İmlecin altındaki geçerli bant değeri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">Haritada son çizilen dikdörtgendeki geçerli bant istatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>İmlecin altında: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>Bölge: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>piksel yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>SON ÖLÇÜMLER</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">Hesaplama kaynağı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">Aralığın uygulandığı nicelik. Eğim, bakı, gölgelendirme ve pürüzlülük bandı bir DTM olarak okur.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>Piksel değeri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>Eğim (derece)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>Eğim (%)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>Bakı (derece)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>Gölgelendirme (0-255)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>Pürüzlülük (TRI, ortalama fark)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>Niceliğin olağan eşikleri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">Olağan eşikler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>Düz</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>Hafif</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>Orta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>Dik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>Doğu</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>Güney</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>West</source>
        <translation>Batı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Shadow</source>
        <translation>Gölge</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Lit</source>
        <translation>Aydınlık</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">Olağan eşikler…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>PİPET</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>Tolerans ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>Seçilen renk veya değer çevresindeki tolerans, değer aralığının % cinsinden</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>Pipet toleransı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>Bantlar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">Görüntünün bantlarının ne olduğu: hazır ayarlar ve pipet bunları kullanır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">Bant düzeni</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB (kırmızı, yeşil, mavi)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC (kızılötesi, kırmızı, yeşil)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + kızılötesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">Yaygın bir indeksin ifadesini yazın (bitki örtüsü, su...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">Spektral hazır ayarlar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">Üç veya daha fazla bantlı bir görüntü gerekir (kırmızı, yeşil, mavi...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>Bitki örtüsü (NDVI &gt; 0.3)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>Bitki örtüsü yok (NDVI &lt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>Su (NDWI &gt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>Bitki örtüsü (aşırı yeşil)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">Spektral hazır ayarlar…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>Bu pikselin değeri yok (NoData): başka bir tane seçin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>Tolerans tüm değerleri kapsıyor: düşürün</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">Aralık {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">Sınıf(lar) {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} renk, sonuncusu: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">İfade</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>BANTLAR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>Etkin bandın imlecin altındaki değeri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>Haritada çizilen son dikdörtgendeki etkin bandın istatistikleri</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>Tüm bantlar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>Değer aralığı tüm renk bantlarına aynı anda uygulanır (her bant aralıktaysa piksel tutulur); histogram ilkini gösterir</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>Etkin bant: değer aralığının, histogramın ve seçicinin okuduğu bant</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>Pipet bu bandı karşılaştırır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>Bandın taşıdığı renk: spektral indeksler ve çipler bunu kullanır. Değiştirmek için tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>Pipetin son tıklamasındaki değer</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>Renk yok</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>1, 2, 3. bantlar kırmızı, yeşil, mavi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>IRC</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>1, 2, 3. bantlar kızılötesi, kırmızı, yeşil (IGN kızılötesi renkli ortofoto)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>1, 2, 3, 4. bantlar kırmızı, yeşil, mavi, yakın kızılötesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>Tüm bantlar: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> Roller tahmin edildi, onaylayın.</translation>
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
        <translation>Kırmızı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Green</source>
        <translation>Yeşil</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Blue</source>
        <translation>Mavi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1024"/>
        <source>Near infrared</source>
        <translation>Yakın kızılötesi</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>roller tahmin edildi, onaylayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>Seç</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>Benzer pikseller</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>Rasterin, alınan renge veya değere yakın tüm pikselleri (kenar çubuğundaki pipet)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>Tıklanan nesne</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>Yalnızca tıklamanın düştüğü bu tür piksellerin öbeği: bir havuz, bir çatı, bir tarla (kenar çubuğundaki nesne algılayıcı); Ctrl+tıklama bir nesne daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>Benzer nesneler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>Rasterin tıklanana benzeyen tüm nesneleri: alanı aşağıdaki oranlar içinde kalan bu tür piksel öbekleri (kenar çubuğundaki benzer nesneler aracı); Ctrl+tıklama bir referans nesnesi daha ekler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>Alan ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>En küçük benzer nesne, tıklanan en küçük nesnenin oranı olarak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>En büyük benzer nesne, tıklanan en büyük nesnenin katı olarak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>– ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>aynı şekil</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>Yalnızca tıklananlara benzer şekilli nesneleri tut: kompaktlıkları (4π × alan / çevre², daire için 1) aynı oranlar içinde; kapalıysa bir havuz alanındaki yol da havuz sayılır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>Bu seçimi kaldır</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>Nicelik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>Aralığın uygulandığı nicelik. Eğim, bakı, gölgelendirme ve pürüzlülük etkin bandı DTM olarak okur.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>Eşikler ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>Ekle ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>Bir bant referansı, yaygın bir spektral indeks veya geçerli aralığı ekle</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>Spektral indeksler</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>Aralık</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>Geçerli değer aralığı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>İşlenen renkler stile ve ölçeğe bağlıdır.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>Yalnızca renk seçimi kullanılabilir: sayısal bantlar, indeksler, aralıklar, sınıflar ve türevler kullanılamaz.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>DEĞER ARALIĞI — tüm bantlar</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>DEĞER ARALIĞI — {0}. bant</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>şuradan örnek alır: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>Eğim, bakı... bir bandı DTM olarak okur: önce BANTLAR'dan bir bant seçin</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>Nesne okunamadı</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>Tıklamanın altında nesne yok: toleransı artırın veya başka bir piksele tıklayın</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>Bir nesne okunan pencereden büyük ve kesildi: toleransı düşürün</translation>
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
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2327"/>
        <source>Choose at least one band in BANDS before using the pipette.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="863"/>
        <source>Display the first checked band in grey or the checked bands as a colour composite</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="861"/>
        <source>First checked band</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="930"/>
        <source>Select or clear every band. The histogram shows the first checked band.</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="940"/>
        <source>Use this band for the pipette, value range and selected bands display</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2051"/>
        <source>VALUE RANGE — selected bands</source>
        <translation type="unfinished"></translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>sınırlı raster yakalaması başarısız oldu</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="302"/>
        <source>local raster capture could not be opened</source>
        <translation>yerel raster yakalaması açılamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="284"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>raster analizi yerel bir GDAL yakalaması gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>raster yakalaması iptal edildi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>raster yakalaması hedefi oturum önbelleğinde olmalıdır</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>raster yakalaması sağlayıcısı klonlanamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>raster yakalaması sonlu, boş olmayan bir kapsam gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>raster yakalaması pozitif bir piksel sınırı gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>raster yakalaması pozitif bir çözünürlük gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="646"/>
        <source>raster capture source could not be opened</source>
        <translation>raster yakalaması kaynağı açılamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>raster somutlaştırma bir çalışan iş parçacığında yürütülmelidir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="279"/>
        <source>raster selection canceled</source>
        <translation>raster seçimi iptal edildi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="294"/>
        <source>raster selection source could not be opened</source>
        <translation>raster seçimi kaynağı açılamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="275"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>uzak raster seçimi bir çalışan iş parçacığında yürütülmelidir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="281"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>işlenmiş renk seçimi yerel bir işlenmiş yakalama gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>işlenmiş rasterler bir işlenmiş renk yakalaması gerektirir</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: raster istatistikleri</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>Raster örneklemesi başarısız oldu; daha küçük bir görünür kapsamla yeniden deneyin.</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: raster önizlemesi</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="642"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>uzak raster hedefi bir çalışan iş parçacığında yürütülmelidir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="671"/>
        <source>local raster target could not be opened</source>
        <translation>yerel raster hedefi açılamadı</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="681"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>İşlenmiş renk katmanları filtre hedefi olamaz.</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Optimizasyonları uygula?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Mevcut Optimizasyonlar</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Atla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Seçilenleri uygula</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} özellik</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Etki: {0}</translation>
    </message>
</context>
<context>
    <name>RemoteMaterializer</name>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1000"/>
        <source>Partial result: the remote feature limit was reached.</source>
        <translation>Kısmi sonuç: uzak nesne sınırına ulaşıldı.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>Kısmi sonuç: uzak zaman sınırına ulaşıldı.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>Uzak filtreleme iptal edildi; önceki filtre korunuyor.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>Hizmete 500'den fazla anahtar gönderilecekti; seçimi daraltın veya yerel bir kopya kullanın.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>Hizmetin kararlı bir anahtarı yok; yerel bir kopya kullanın.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>Mekânsal filtrelemeden önce uzak kaynağı seçin veya filtreleyin.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>Hizmet filtresinin eksiksiz olduğu kanıtlanamıyor. Kaynak nesneleri seçin veya yerel bir kopya kullanın.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>Uzak kaynak kopyası eksik; önceki filtre korunuyor.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>Kısmi sonuç: sınıra kadar eşleşen hiçbir nesne doğrulanamadı; önceki filtre korunuyor.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>Kesişen uzak kopya eksik; ayrık (disjoint) bir filtre güvenle hesaplanamaz.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Başka bir yüklemle birleştirilen Disjoint, uzak hedefin yerel bir kopyasını gerektirir.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>Uzak mekânsal yüklem değerlendirilemedi; önceki filtre korunuyor.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>Uzak kopya okunamadı veya filtrelenemedi; önceki filtre korunuyor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="138"/>
        <source>Remote materialization requires a background task.</source>
        <translation>Uzak somutlaştırma bir arka plan görevi gerektirir.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="715"/>
        <source>Filtering a bounded remote copy</source>
        <translation>Sınırlı bir uzak kopya filtreleniyor</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: işlenmiş renk anlık görüntüsü</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>İşlenmiş anlık görüntü başarısız oldu; daha küçük bir görünür kapsamla yeniden deneyin.</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Yapılandırmada ara... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>Eşleşme yok</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="285"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="460"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>Bir FilterMate görevi hâlâ katmanları okuyor. Bittikten sonra yeniden deneyin.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="289"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>Yardımcı depolaması olan bir katman, sunucu sağlayıcısını güvenle değiştiremez. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="294"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>Uzak bir birleştirme ana iş parçacığında yeniden oluşturulamaz. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="296"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>Bu katman için bir sunucu filtresi zaten hazırlanıyor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="255"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>Bir sunucu katmanı yalnızca sahibi olan iş parçacığında değiştirilebilir.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="278"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>Eşzamansız sunucu filtreleri QGIS 3.32 veya üstünü gerektirir. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="404"/>
        <source>Could not install the prepared server filter.</source>
        <translation>Hazırlanan sunucu filtresi kurulamadı.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="67"/>
        <source>Could not preserve the layer state.</source>
        <translation>Katman durumu korunamadı.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="282"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="453"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>Sunucu filtresini uygulamadan önce katmanın düzenlemesini bitirin.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>Geçersiz öznitelik ifadesi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="106"/>
        <source>Preparing server attribute filter</source>
        <translation>Sunucu öznitelik filtresi hazırlanıyor</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>QGIS bu yüklemi bir OGC filtresine çeviremiyor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="336"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>Sunucu filtresi iptal edildi veya zaman aşımına uğradı. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="384"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>Sunucu filtresi kurulumu başarısız oldu ve önceki sağlayıcı geri yüklenemedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="376"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="456"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>Sunucu filtresi kurulumu başarısız oldu. Önceki sağlayıcı zaten geçersizdi ve geri yüklenemedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="391"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>Sunucu filtresi kurulumu başarısız oldu. Önceki sağlayıcı geri yüklendi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="56"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>Sunucu filtresi kurulumu sürüyor. Bittikten sonra yeniden deneyin.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="249"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="280"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="451"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>Sunucu filtresi kurulumu katmanın iş parçacığında başlamalıdır.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>İfade güvenle çevrilemeyecek kadar karmaşık.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>İfade çok büyük veya belirsiz SQL ters eğik çizgi kaçışları içeriyor.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="354"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>Filtre hazırlanırken katman değişti. Hazırlanan sonuç atıldı.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="402"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>Katman artık kullanılamıyor. Hazırlanan filtre atıldı.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>Sunucu filtreyi reddetti veya sunucuya ulaşılamadı. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="287"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>Bu sağlayıcı ve QGIS sürümü doğrulanmış çalışan oluşturmayı desteklemiyor. Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: öznitelik filtresi tamamen sunucuda çalıştırılamıyor. Desteklenmeyen kısım: {1}. {2} Önceki filtre değişmedi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="270"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="494"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: sağlayıcı öznitelik filtresini reddetti. Önceki filtre geri yüklendi.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="269"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="493"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: sağlayıcı filtreyi reddetti ve geri yükleme başarısız oldu.</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Paylaşılan sık kullanılanlar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Paylaşılan sık kullanılanlar&lt;/b&gt; — QGIS Resource Sharing koleksiyonlarında keşfedildi</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">Ad, açıklama, koleksiyon veya etiketlere göre ara…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Önizleme için bir paylaşılan sık kullanılan seçin.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>Yeniden tara</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>Projeme fork et</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>Kapat</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Paylaşılan koleksiyon bulunamadı. &lt;code&gt;filter_mate/favorites&lt;/code&gt; klasörü içeren bir Resource Sharing deposuna abone olun veya resource_sharing koleksiyon dizininize bir &lt;code&gt;.fmfav.json&lt;/code&gt; paketi bırakın.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{1} koleksiyonda {0} sık kullanılan: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>Koleksiyon: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">Arama ile eşleşen paylaşılan sık kullanılan yok.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — kaynak: &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;İfade&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Uzak katmanlar&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Etiketler:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kaynak&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>Yazar: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>Lisans: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>Paylaşılan sık kullanılanı fork et</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>Projenizdeki ad:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>Fork başarılı</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» sık kullanılanlarınıza eklendi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>Fork başarısız</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Paylaşılan sık kullanılan projenize eklenemedi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>Ada, açıklamaya, koleksiyona, yazara veya etiketlere göre ara...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>Yazar:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>Tüm yazarlar</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>Filtrelerinizle eşleşen paylaşılan favori yok.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>Varsayılanlara sıfırla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>Doğrulama hatası</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>Lütfen aşağıdaki hataları düzeltin:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>Yapılandırmayı sıfırla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>Tüm değerler varsayılanlara sıfırlansın mı?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - PostgreSQL Tür Uyarısı</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Filtrede tür uyumsuzluğu: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>Varsayılanlara sıfırla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>Genel</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>{0} filtresi uygulanamadı; önceki filtresini koruyor.</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>Ana katmanda {count} özellik görünür</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Tüm filtreler temizlendi - ana katmanda {count} özellik görünür</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Filtre '{layer_name}' katmanına uygulandı: {count} özellik</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>'{layer_name}' için filtre temizlendi: {count} özellik görünür</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="942"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Varlık seçilmedi! Seçim bileşeni özelliği kaybetti. Bir varlığı yeniden seçin.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1060"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Seçilen katman geçersiz veya kaynağı bulunamıyor. İşlem iptal edildi.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1075"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>Katman '{0}' henüz başlatılmadı. Başka bir katman seçip tekrar bu katmana dönmeyi deneyin.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Geri alınamıyor: katman geçersiz veya kaynak bulunamadı.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Yinelenemez: katman geçersiz veya kaynak bulunamadı.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>Sağlayıcı kaydedilen filtreyi reddetti.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>Filtre geri yüklenemedi: {0}</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="572"/>
        <source>Explore ...</source>
        <translation>Gözat ...</translation>
    </message>
</context>
<context>
    <name>VectorTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="301"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: benzersiz anahtar alanı yok, nesneleri filtresinde listelenemiyor (bir web hizmeti veya benzersiz kimlik sütunu olmayan bir sanal katman).</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="452"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>Listelenecek {0} nesne var; bu, bir web hizmetine gönderilebilen {1} sınırını aşıyor: kaynağı daraltın veya bir öznitelik filtresi kullanın.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="392"/>
        <source>{0} AND NOT would keep the features not read; the previous filter is kept.</source>
        <translation>{0} AND NOT, okunmayan nesneleri tutardı; önceki filtre korunuyor.</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>Kesilmiş karo nesneleri için en düşük kapsama kullanılamaz</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>Vektör karo hedefleri yalnızca Intersect ve Disjoint destekler</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>Vektör karo filtreleme bir CRS yetki kodu gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>Vektör karo görüntüleme filtresi: öznitelikler yakınlaştırmaya bağlıdır; karolara bölünmüş nesneler farklılık gösterebilir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>Filtre çalışırken vektör karo stili değişti; yeniden deneyin</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>Vektör karo özniteliklerini filtrele</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>Geçersiz vektör karo filtre ifadesi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>QGIS ifadesi (öznitelikler yakınlaştırmaya bağlıdır):</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>Vektör karo filtresini yinele</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>Yalnızca hedef. Öznitelikler yakınlaştırmaya bağlıdır. Karolara bölünmüş nesneler farklı filtrelenebilir.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>Kaydedilen vektör karo stili geçersiz</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>Kaydedilen vektör karo sembol özelliği geçersiz</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>Karo seçimi ifade bütçesini (1 MB) aşıyor; daha küçük bir alan kullanın</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>Karo seçimi köşe noktası bütçesini (2000) aşıyor; daha küçük bir alan kullanın</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>Vektör karo filtresi ifade bütçesini (1 MB) aşıyor</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>Vektör karo filtresi toplam stil ifadesi bütçesini (1 MB) aşıyor; daha küçük bir alan kullanın</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>Vektör karo filtresini geri al</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>Vektör karoların filtresini kaldır</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>Vektör karo öznitelik filtresi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="131"/>
        <source>Vector tile favorite</source>
        <translation>Vektör karo favorisi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>Vektör karo filtresi</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>Vektör karo filtreleme temel bir işleyici gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>Vektör karo filtreleme temel etiketleme gerektirir</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>Vektör karo filtreleri</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>Vektör karolar</translation>
    </message>
</context>
<context>
    <name>self.dockwidget</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="664"/>
        <source>Language changed to &apos;{0}&apos;.</source>
        <translation type="obsolete">Language changed to '{0}'.</translation>
    </message>
</context>
<context>
    <name>self.self</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="735"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation type="obsolete">Kaynak geometri: EXPLORING içinde seçilen detaylar</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">Kaynak geometri: seçili pikseller, vektörleştirilmiş</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">Tutulan noktalar</translation>
    </message>
</context>
</TS>
