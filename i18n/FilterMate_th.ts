<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="th_TH" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>นำเข้าจาก Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>เผยแพร่ไปยัง Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>เผยแพร่ (ไม่บันทึกรายการโปรด)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>เผยแพร่ด่วนไปยังที่เก็บเริ่มต้น</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>จัดการที่เก็บ Resource Sharing...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>ล้างตัวกรองที่เสียหายจาก {0} เลเยอร์แล้ว กรุณาใช้ตัวกรองอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>ตรวจพบโปรเจกต์ว่าง เพิ่มเลเยอร์เวกเตอร์เพื่อเปิดใช้งานปลั๊กอิน</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>ไม่สามารถเข้าถึงฐานข้อมูล FilterMate ตรวจสอบสิทธิ์ไดเรกทอรีโปรเจกต์</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>ข้อผิดพลาดระหว่างการตรวจสอบฐานข้อมูล: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>โหลดเลเยอร์ล้มเหลว ใช้ F5 เพื่อบังคับโหลดใหม่</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: เว็บเซอร์วิสนี้ไม่มีฟิลด์คีย์ที่ไม่ซ้ำกัน (คีย์ที่ประกาศไว้, id, gml_id, cleabs, objectid...) จึงไม่สามารถแสดงรายการฟีเจอร์ที่เลือกให้เซิร์ฟเวอร์ได้</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: เลเยอร์นี้ไม่มีฟิลด์คีย์ที่ไม่ซ้ำกัน จึงไม่สามารถแสดงรายการ id ของฟีเจอร์ในตัวกรองได้ (เลเยอร์เสมือนต้องมีคอลัมน์ id ที่ไม่ซ้ำกัน คือ uid)</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: เลือกฟีเจอร์ {1} รายการ มากกว่า {2} รายการที่ส่งไปยังเว็บเซอร์วิสได้ โปรดจำกัดการเลือกหรือใช้ตัวกรองแอตทริบิวต์</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>ไฟล์ระยะไกล: การอ่านทุกครั้งผ่านเครือข่าย FilterMate จะไม่นับฟีเจอร์ของไฟล์บนเธรดหลัก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>บริการระยะไกล: ตัวกรองจะถูกส่งไปยังเซิร์ฟเวอร์เมื่อแปลงได้ FilterMate จะไม่นับฟีเจอร์ของบริการบนเธรดหลัก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>ตัวกรองตามรายการฟีเจอร์จำกัดที่ {0} ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="123"/>
        <source>Remote</source>
        <translation>ระยะไกล</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="185"/>
        <source>Select Backend:</source>
        <translation>เลือกแบ็กเอนด์:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>อัตโนมัติ (ค่าเริ่มต้น)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>เลือกค่าที่เหมาะสมที่สุดสำหรับเลเยอร์ทั้งหมดโดยอัตโนมัติ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>บังคับ {0} สำหรับเลเยอร์ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>คลิกเพื่อโหลดเลเยอร์ใหม่</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>คลิกเพื่อเปลี่ยนแบ็กเอนด์</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>ทดสอบเป้าหมายเส้นและโพลิกอนที่เลือกไว้ด้วยจุดศูนย์กลาง (จุดบนพื้นผิว): เร็วกว่าสำหรับเรขาคณิตขนาดใหญ่ แต่ละเป้าหมายมีช่องสี่เหลี่ยมของตัวเองในรายการ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>จุดศูนย์กลางใช้กับเป้าหมายเส้นและโพลิกอน: เลือกหนึ่งรายการในรายการเลเยอร์ที่จะกรอง</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>ข้อผิดพลาดในการยกเลิกการเปลี่ยนแปลง: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>ข้อผิดพลาดคุณสมบัติ: {0}</translation>
    </message>
</context>
<context>
    <name>CoverageDockExtras</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="303"/>
        <source>1 band</source>
        <translation>1 แบนด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="304"/>
        <source>{0} bands</source>
        <translation>{0} แบนด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="305"/>
        <source>{0} points</source>
        <translation>{0} จุด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="772"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>เรขาคณิตต้นทาง: พิกเซลที่เลือก แปลงเป็นเวกเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="788"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>เรขาคณิตต้นทาง: ขอบเขตของจุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="209"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation type="obsolete">เรขาคณิตต้นทาง: ฟีเจอร์ที่เลือกใน EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">ค่าใต้เคอร์เซอร์: ติดตามค่าพิกเซลของแบนด์ปัจจุบันขณะเลื่อนบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">สถิติของสี่เหลี่ยม: ลากบนแผนที่เพื่ออ่านค่าต่ำสุด สูงสุด และค่าเฉลี่ยของแบนด์ปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>โปรไฟล์ความสูง: เปิดโปรไฟล์ความสูงของ QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>มุมมอง 3D: เปิดมุมมองแผนที่ 3D ใหม่ของ QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">ไม่มีฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">พิกเซลทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} คลาส</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>นิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="803"/>
        <source>Vector</source>
        <translation>เวกเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="803"/>
        <source>Raster</source>
        <translation>ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="803"/>
        <source>Point cloud</source>
        <translation>พอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="791"/>
        <source>Kept points</source>
        <translation>จุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="772"/>
        <source>Selection → source geometry</source>
        <translation>การเลือก → เรขาคณิตต้นทาง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>เชื่อมช่วงกับสไตล์: สีของชั้นข้อมูลยืดไปตามช่วงที่เลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>ตัวเลือกคลาส: คลิกบนแผนที่ แล้วคลาสของจุดที่วาดอยู่ตรงนั้นจะถูกเลือก Ctrl+คลิก เพื่อเพิ่มอีกคลาส</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>ค่าใต้เคอร์เซอร์: ติดตามค่าพิกเซล (หรือความลาดชัน ทิศด้านลาด ฯลฯ ที่ช่วงนำไปใช้) ขณะเลื่อนบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>สถิติของสี่เหลี่ยม: ลากบนแผนที่เพื่ออ่านค่าต่ำสุด สูงสุด และค่าเฉลี่ยของแบนด์ปัจจุบัน (หรือของความลาดชัน ทิศด้านลาด ฯลฯ ที่ช่วงนำไปใช้)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>การเชื่อมสไตล์ติดตามค่าพิกเซล: ใช้ไม่ได้เมื่อช่วงนำไปใช้กับความลาดชัน ทิศด้านลาด ร่มเงาภูมิประเทศ หรือความขรุขระ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="916"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>ตัวเลือกคลาส: พอยต์คลาวด์นี้ไม่มีแอตทริบิวต์ Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1522"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>สไตล์ไม่สามารถติดตามช่วงได้: ต้องใช้สไตล์เกรย์สเกลหรือพซูโดคัลเลอร์แบบแบนด์เดียวบนแบนด์ของแผง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>ตัวเลือก: คลิกบนแผนที่ แล้วพิกเซลที่คล้ายกับพิกเซลที่คลิกจะถูกเลือก (สีบนภาพ ค่าบน DTM หรือดัชนี คลาสบนแรสเตอร์ที่จัดประเภทแล้ว ตามค่าความคลาดเคลื่อนของแผง) Ctrl+คลิก เพื่อเพิ่มอีกพิกเซล</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>ไม่ได้เลือกฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>ทั้งเลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>ไม่มีข้อจำกัด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>นิพจน์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>ทุกจุด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} วัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>แสดงเป็นทั้งคลาสในกล่องของวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>ตัวตรวจจับวัตถุ: คลิกบนแผนที่เพื่อเลือกกลุ่มพิกเซลที่หน้าตาคล้ายพิกเซลที่คลิก (สระน้ำ หลังคา ทุ่งนา ตามค่าความคลาดเคลื่อนของแผง) ไม่ใช่ทุกพิกเซลที่มีสีเดียวกัน Ctrl+คลิก เพื่อเพิ่มอีกวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>วัตถุที่คล้ายกัน: คลิกวัตถุเพื่อเลือกทุกวัตถุของราสเตอร์ที่คล้ายกัน (กลุ่มพิกเซลดังกล่าวที่มีพื้นที่อยู่ในอัตราส่วนของแผง) Ctrl+คลิก เพื่อเพิ่มวัตถุอ้างอิงอีกชิ้น</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>ตัวตรวจจับวัตถุ: คลิกบนแผนที่เพื่อเลือกวัตถุใต้ตำแหน่งที่คลิก (กลุ่มจุดของคลาสนั้น เช่น อาคาร ต้นไม้) ไม่ใช่ทั้งคลาส หรือเลือกทุกวัตถุในพอยต์คลาวด์ที่คล้ายกัน (คลิกขวาที่ปุ่มเพื่อกำหนดเป้าหมาย) Ctrl+คลิก เพื่อเพิ่มอีกวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>ตัวเลือกค่า: คลิกบนแผนที่เพื่อเขียนเงื่อนไขบนแอตทริบิวต์ที่เลือกใน ATTRIBUTES (Z, ความเข้ม...) รอบค่าของจุดตรงนั้น ตามค่าความคลาดเคลื่อนของแผง Ctrl+คลิก เพื่อเพิ่มเงื่อนไขอีกข้อ (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>โซน: วาดสี่เหลี่ยม โพลิกอน รูปร่างอิสระ หรือวงกลมบนแผนที่ (คลิกขวาที่ปุ่มเพื่อเลือกรูปร่าง) กล่อง X / Y ของโซนจะไปที่ ATTRIBUTES ส่วนรูปร่างเองจะตัดเป้าหมาย</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>เครื่องมือเพิ่มเติม: ค่าใต้เคอร์เซอร์ สถิติของสี่เหลี่ยม</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>ฟีเจอร์ที่คล้ายกัน: คลิกฟีเจอร์เพื่อเลือกทุกฟีเจอร์ของเลเยอร์ที่มีค่าเดียวกันของฟิลด์ในกลุ่ม (นิพจน์แสดงผลของการเลือกเดี่ยว / หลายรายการ) Ctrl+คลิก เพื่อเพิ่มอีกค่า</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>เครื่องมือเพิ่มเติม: เครื่องมือเลือกของ QGIS (สี่เหลี่ยม โพลิกอน วาดอิสระ รัศมี) การเลือกด้วยนิพจน์ การกลับหรือล้างการเลือก ตารางแอตทริบิวต์ของการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>เครื่องมือเพิ่มเติม: โปรไฟล์ความสูงและมุมมอง 3D ของ QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>ใช้ได้เฉพาะการเลือกตามสี: สีที่แสดงผลขึ้นอยู่กับสไตล์และมาตราส่วน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>ลิงก์สไตล์ตามกลุ่มช่วงค่า: ตั้งให้เป็นกลุ่มที่ใช้งานก่อน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="790"/>
        <source>Current filter: {0}</source>
        <translation>ตัวกรองปัจจุบัน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="826"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>สีที่แสดงผลขึ้นอยู่กับสไตล์และมาตราส่วน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="925"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>ตัวตรวจจับวัตถุ: พอยต์คลาวด์นี้ไม่มีแอตทริบิวต์ Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="974"/>
        <source>Object detector</source>
        <translation>ตัวตรวจจับวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="977"/>
        <source>Clicked object</source>
        <translation>วัตถุที่คลิก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="977"/>
        <source>Similar objects</source>
        <translation>วัตถุที่คล้ายกัน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1081"/>
        <source>Zone shape</source>
        <translation>รูปร่างของโซน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1254"/>
        <source>Rectangle</source>
        <translation>สี่เหลี่ยม</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1254"/>
        <source>Polygon</source>
        <translation>โพลิกอน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1255"/>
        <source>Freehand</source>
        <translation>วาดอิสระ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1255"/>
        <source>Radius</source>
        <translation>รัศมี</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1130"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>ลิงก์ตามการเลือกเดี่ยวและหลายรายการ: ตั้งให้อย่างใดอย่างหนึ่งเป็นกลุ่มที่ใช้งานก่อน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1253"/>
        <source>Select on the map</source>
        <translation>เลือกบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1261"/>
        <source>Select by expression…</source>
        <translation>เลือกด้วยนิพจน์…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1261"/>
        <source>Invert the selection</source>
        <translation>กลับการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1261"/>
        <source>Clear the selection</source>
        <translation>ล้างการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1268"/>
        <source>Attribute table of the selection</source>
        <translation>ตารางแอตทริบิวต์ของการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1307"/>
        <source>Value under the cursor</source>
        <translation>ค่าใต้เคอร์เซอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Statistics of a rectangle</source>
        <translation>สถิติของสี่เหลี่ยม</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1327"/>
        <source>Elevation profile</source>
        <translation>โปรไฟล์ความสูง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1327"/>
        <source>3D view</source>
        <translation>มุมมอง 3D</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1684"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>พอยต์คลาวด์นี้ไม่มีแอตทริบิวต์ X / Y ให้กรอง</translation>
    </message>
</context>
<context>
    <name>CoverageModeController</name>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="365"/>
        <source>Restoring the filter of {0} raster / point cloud layer(s)…</source>
        <translation>กำลังคืนค่าตัวกรองของเลเยอร์ราสเตอร์ / พอยต์คลาวด์ {0} เลเยอร์…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>ครอบคลุม ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>สัดส่วนขั้นต่ำของเลเยอร์เป้าหมายแบบโพลิกอนที่อยู่ภายในเรขาคณิตต้นทาง (0 = ซ้อนทับเท่าใดก็ได้) ใช้เมื่อต้นทางเป็นราสเตอร์หรือพอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>พอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>เลเยอร์{0}: เลือกใน EXPLORING, ความสัมพันธ์ใน FILTERING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">ตัวเลือกพิกเซล: คลิกบนแผนที่เพื่ออ่านค่าของทุกแบนด์ (Ctrl+คลิก เพื่อขยายช่วง)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>ซูมไปที่เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">ดูตัวอย่าง: ซ่อนพิกเซลนอกการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>ไม่ใช้กับเลเยอร์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>รีเซ็ตการเลือกราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">ระบุจุดบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>ดูตัวอย่างสด: แสดงเฉพาะจุดที่การเลือกเก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>ไม่ใช้กับเลเยอร์พอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>รีเซ็ตเกณฑ์พอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>นิพจน์ตัวคำนวณราสเตอร์ไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>ไม่พบ PDAL: การคำนวณความสูงเหนือ DTM ต้องใช้ไฟล์ปฏิบัติการ pdal</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3147"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>งาน FilterMate ยังทำงานอยู่: โปรดรอให้เสร็จสิ้น</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>งาน FilterMate ล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>เลือกพิกเซลก่อน: ช่วงค่า คลาส หรือนิพจน์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>กรองราสเตอร์แล้ว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>นิพจน์พอยต์คลาวด์ถูกปฏิเสธ: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>เลือกจุดก่อน: คลาส ช่วงแอตทริบิวต์ หรือนิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>กรองพอยต์คลาวด์แล้ว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3252"/>
        <source>Filter not applied: {0}</source>
        <translation>ไม่ได้ใช้ตัวกรอง: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3109"/>
        <source>canceled</source>
        <translation>ยกเลิกแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>กรองเลเยอร์เป้าหมายแล้ว {0} เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2820"/>
        <source>{0} failed: {1}</source>
        <translation>{0} ล้มเหลว: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2833"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: กำลังกรองจาก '{0}'…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2929"/>
        <source>Changed since, left as is: {0}</source>
        <translation>มีการเปลี่ยนแปลงภายหลัง คงไว้ตามเดิม: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2935"/>
        <source>{0} layer(s) restored</source>
        <translation>คืนค่าแล้ว {0} เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2969"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>ไม่ได้ส่งออก '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2983"/>
        <source>Exported: {0}</source>
        <translation>ส่งออกแล้ว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2985"/>
        <source>Export failed: {0}</source>
        <translation>ส่งออกล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2992"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>กำลังส่งออก {0} เลเยอร์…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2998"/>
        <source>Export folder</source>
        <translation>โฟลเดอร์ส่งออก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3080"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>ข้ามเลเยอร์เป้าหมายราสเตอร์ / พอยต์คลาวด์: ไม่ได้เลือกฟีเจอร์ต้นทางใน EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3109"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>ไม่ได้กรองเลเยอร์เป้าหมายราสเตอร์ / พอยต์คลาวด์: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3111"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>กรองเลเยอร์เป้าหมายราสเตอร์ / พอยต์คลาวด์แล้ว {0} เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3229"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>เลือกราสเตอร์ DTM ที่ใช้คำนวณความสูงเหนือพื้นดิน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3240"/>
        <source>Height above ground not computed: {0}</source>
        <translation>ไม่ได้คำนวณความสูงเหนือพื้นดิน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3261"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>กำลังคำนวณความสูงเหนือ '{0}' ด้วย PDAL…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>แคชของ FilterMate ใช้พื้นที่ {0} GB เกินขีดจำกัด {1} GB: โปรดยกเลิกตัวกรองของชั้นข้อมูลแรสเตอร์ / พอยต์คลาวด์ที่คุณไม่ต้องการแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>PDAL {0} เก่าเกินไป: การคำนวณความสูงเหนือ DTM ต้องใช้ PDAL 2.4 ขึ้นไป</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>ไม่สามารถเรียกใช้ PDAL ได้ ความสูงเหนือ DTM ใช้งานไม่ได้: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">ตัวเลือกพิกเซล: คลิกบนแผนที่เพื่ออ่านค่าของทุกแบนด์ และความลาดชัน ทิศด้านลาด ฯลฯ เมื่อช่วงนำไปใช้กับค่านั้น (Ctrl+คลิก เพื่อขยายช่วง)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>ซูมไปที่พิกเซลที่เลือก (ไปที่เลเยอร์เมื่อไม่ได้เลือกอะไร)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>ดูตัวอย่าง: ซ่อนพิกเซลนอกการเลือก (ม่านสีขาวสำหรับความลาดชัน ทิศด้านลาด ฯลฯ)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>การดูตัวอย่างความลาดชันหรือทิศด้านลาดต้องใช้แผนที่ใน CRS ของราสเตอร์ ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>เลือกได้เฉพาะจุดที่วาดอยู่บนแผนที่: ปิดการดูตัวอย่างเพื่อเลือกคลาสที่ถูกซ่อนไว้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>ไม่มีจุดที่จำแนกประเภทแล้วใต้ตำแหน่งที่คลิก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>คลาส {0} ถูกเลือกไว้แล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>คลาส {0} ไม่อยู่ในรายการคลาสของเลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>ไม่ใช้กับเลเยอร์ราสเตอร์: ตัวเลือกจะอ่านแบนด์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>ตัวเลือกคลาส: คลิกบนแผนที่ แล้วคลาสของจุดที่วาดอยู่ตรงนั้นจะถูกเลือก Ctrl+คลิก เพื่อเพิ่มอีกคลาส</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>การดูตัวอย่างและสถิติใช้ตัวอย่างในเครื่องแบบจำกัดของขอบเขตที่มองเห็น ส่วนการกรองจะอ่านจากต้นทาง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>กำลังเตรียมสแนปช็อตสีแบบจำกัดของขอบเขตที่มองเห็น…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>ไม่สามารถเตรียมสแนปช็อตสีได้ ลองใช้ขอบเขตที่มองเห็นที่เล็กลง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>การเลือกตามสีใช้กับขอบเขตที่มองเห็นซึ่งบันทึกไว้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>การสุ่มตัวอย่างราสเตอร์ล้มเหลว ลองใช้ขอบเขตที่มองเห็นที่เล็กลง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>ไม่สามารถคำนวณตัวอย่างราสเตอร์ที่สุ่มสำหรับการดูตัวอย่างได้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>การดูตัวอย่างสีหรือนิพจน์ต้องใช้แผนที่ใน CRS ของราสเตอร์ ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>ไม่มีจุดที่วาดอยู่ใต้ตำแหน่งที่คลิก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>จุดนี้ไม่มี {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>ไม่สามารถใช้ {0} ในเงื่อนไขได้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>ไม่ได้อ่านวัตถุ: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>มีจุดรอบตำแหน่งที่คลิกมากเกินไป: ไม่สามารถอ่านวัตถุได้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>ไม่มีจุดของคลาส {0} ใต้ตำแหน่งที่คลิก: คลิกที่วัตถุโดยตรง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>ไม่ได้อ่านวัตถุที่คล้ายกัน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>ไม่มีวัตถุที่คล้ายกันภายในอัตราส่วนพื้นที่: ขยายอัตราส่วน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>กำลังเตรียมตัวอย่างสำหรับขอบเขตที่มองเห็นใหม่ คลิกอีกครั้งเมื่อพร้อม</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>ตัวอย่างราสเตอร์ในเครื่องยังเตรียมไม่เสร็จ ลองอีกครั้งเมื่อพร้อม</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>เตรียมสแนปช็อตสีก่อนกรองเลเยอร์ที่แสดงผลนี้</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>เลเยอร์เป้าหมายราสเตอร์ {0} เลเยอร์ถูกสุ่มใหม่ตามขีดจำกัดพิกเซลที่กำหนด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2844"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>การเลือกตามสีจำกัดอยู่ที่ขอบเขตที่บันทึกไว้ สีขึ้นอยู่กับสไตล์และมาตราส่วน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2846"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>ราสเตอร์ต้นทางถูกสุ่มใหม่เป็น {0} เซลล์ภายในขีดจำกัดพิกเซล</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2848"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>การเลือกราสเตอร์อ่านทุก {0} พิกเซล: เกินขีดจำกัดพิกเซลในการตั้งค่า</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>การเลือกราสเตอร์ที่หนาแน่นถูกทำให้เรียบเพื่อให้เส้นขอบเบา</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2897"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0} ถูกทำให้ว่าง ไม่มีสิ่งใดตรงกับการเลือก: {1}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="234"/>
        <source>Database file does not exist: {0}</source>
        <translation>ไฟล์ฐานข้อมูลไม่มีอยู่: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>เชื่อมต่อฐานข้อมูลล้มเหลว {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>ไม่สามารถสร้างไดเรกทอรีฐานข้อมูล {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>สร้างไฟล์ฐานข้อมูลล้มเหลว {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>ไม่สามารถเริ่มต้นฐานข้อมูล FilterMate: การเชื่อมต่อล้มเหลว</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>ข้อผิดพลาดร้ายแรงในการเชื่อมต่อฐานข้อมูล: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>ข้อผิดพลาดระหว่างการเริ่มต้นฐานข้อมูล: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>ไม่มีไฟล์ฐานข้อมูล: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>ไม่สามารถเชื่อมต่อกับฐานข้อมูล {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>ไม่สามารถใช้โมดูล QGIS Processing เพื่อสร้างดัชนีเชิงพื้นที่</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>ไม่สามารถสร้างดัชนีเชิงพื้นที่: ชั้นข้อมูลไม่ถูกต้องหรือไม่พบแหล่งที่มา</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>ตรวจพบชั้นข้อมูล PostgreSQL แต่ไม่ได้ติดตั้ง psycopg2 กำลังใช้แบ็กเอนด์ Spatialite ในเครื่อง ติดตั้ง psycopg2 เพื่อประสิทธิภาพที่ดีขึ้นกับชุดข้อมูลขนาดใหญ่</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2239"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>เลือกฟีเจอร์ {0} รายการ มากกว่า {1} รายการที่ส่งไปยังเว็บเซอร์วิสได้: โปรดจำกัดการเลือกหรือใช้ตัวกรองแอตทริบิวต์</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>บันทึกเลเยอร์ของคุณเป็นไฟล์</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>เลือกโฟลเดอร์สำหรับส่งออกเลเยอร์ของคุณ</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>บันทึกข้อมูลที่ส่งออกเป็นไฟล์ zip</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0} เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> ใน {0} กลุ่ม</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} นอกกลุ่ม</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>ปลายทาง : {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>ไม่พบกลุ่ม - เลเยอร์ทั้งหมดอยู่ที่ระดับราก</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="154"/>
        <source>Annuler</source>
        <translation>ยกเลิก</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="160"/>
        <source>Exporter</source>
        <translation>ตัวส่งออก</translation>
    </message>
</context>
<context>
    <name>ExtensionRegistry</name>
    <message>
        <location filename="../extensions/registry.py" line="398"/>
        <source>install the QGIS plugin {0}</source>
        <translation>ติดตั้งปลั๊กอิน QGIS {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>ติดตั้ง {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>ส่วนขยาย {0} ปิดอยู่เนื่องจากไม่มี {1}: {2} แล้วเริ่ม QGIS ใหม่</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">ไม่มีตัวกรอง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>ไม่มีตัวกรองที่ใช้งานเพื่อบันทึก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>เพิ่มรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>ชื่อรายการโปรด:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>เพิ่มรายการโปรด '{0}' สำเร็จแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="511"/>
        <source>Export Favorites</source>
        <translation>ส่งออกรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="535"/>
        <source>Exported {0} favorites</source>
        <translation>ส่งออก {0} รายการโปรดแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="537"/>
        <source>Failed to export favorites</source>
        <translation>ส่งออกรายการโปรดล้มเหลว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Import Favorites</source>
        <translation>นำเข้ารายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>รวมกับรายการโปรดที่มีอยู่หรือไม่?

ใช่ = เพิ่มไปยังที่มีอยู่
ไม่ = แทนที่ทั้งหมดที่มีอยู่</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>นำเข้า {0} รายการโปรดแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>ไม่มีรายการโปรดที่นำเข้า</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>ตัวจัดการรายการโปรดยังไม่ได้เริ่มต้น กรุณารีสตาร์ท FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>กล่องโต้ตอบตัวจัดการรายการโปรดไม่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>ข้อผิดพลาด: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">ใช้แล้ว {0} ครั้ง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">เพิ่มตัวกรองปัจจุบันไปยังรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">เพิ่มตัวกรอง (ไม่มีตัวกรองที่ใช้งาน)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">จัดการรายการโปรด...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation type="obsolete">ส่งออก...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation type="obsolete">นำเข้า...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation type="obsolete">รายการโปรดส่วนกลาง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">คัดลอกไปยังส่วนกลาง...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── รายการโปรดส่วนกลางที่พร้อมใช้งาน ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(ไม่มีรายการโปรดส่วนกลาง)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">การบำรุงรักษา</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">บันทึกในโปรเจกต์ (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">กู้คืนจากโปรเจกต์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">ล้างโปรเจกต์ที่ไม่มีเจ้าของ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">สถิติฐานข้อมูล</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">ชื่อไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>ชื่อรายการโปรดต้องไม่ว่างเปล่า</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>ชื่อซ้ำ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>รายการโปรดชื่อ '{0}' มีอยู่แล้ว
คุณต้องการแทนที่หรือไม่?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>คัดลอกรายการโปรดไปยังรายการโปรดส่วนกลางแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>คัดลอกไปยังรายการโปรดส่วนกลางล้มเหลว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">รายการโปรดส่วนกลาง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0} รายการโปรดส่วนกลางที่พร้อมใช้งาน

รายการโปรดส่วนกลางใช้ร่วมกันในทุกโปรเจกต์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>บันทึก {0} รายการโปรดไปยังไฟล์โปรเจกต์แล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>บันทึกล้มเหลว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>กู้คืน {0} รายการโปรดจากไฟล์โปรเจกต์แล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>ไม่พบรายการโปรดที่จะกู้คืนในโปรเจกต์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>ล้างโปรเจกต์ที่ไม่มีเจ้าของ {0} โปรเจกต์แล้ว</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>ไม่มีโปรเจกต์ที่ไม่มีเจ้าของที่จะล้าง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>สถิติฐานข้อมูล FilterMate

รายการโปรดทั้งหมด: {0}
   โปรเจกต์: {1}
   ไม่มีเจ้าของ: {2}
   ส่วนกลาง: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>โปรเจกต์ยอดนิยมตามรายการโปรด:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>สถิติ FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">ตัวจัดการรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">ยังไม่มีรายการโปรดที่บันทึก

ใช้ตัวกรองกับชั้นข้อมูล แล้วคลิกตัวแสดง ★ และเลือก «เพิ่มตัวกรองปัจจุบันไปยังรายการโปรด» เพื่อบันทึกรายการโปรดแรกของคุณ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">นำเข้าจาก Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">เผยแพร่ไปยัง Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">เผยแพร่ (ไม่มีรายการโปรดที่บันทึก)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>ยังไม่ได้เริ่มต้นไดเรกทอรีการตั้งค่า FilterMate — เปิดโปรเจกต์ QGIS ที่ใช้ FilterMate ก่อน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">ส่วนขยาย Resource Sharing ไม่ทำงาน เปิดใช้ 'favorites_sharing' ในการตั้งค่า FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">บริการรายการโปรดที่แบ่งปันไม่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">ตัวเลือกรายการโปรดที่แบ่งปันล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">คุณยังไม่มีรายการโปรดที่จะเผยแพร่ บันทึกตัวกรองผ่านเมนู ★ ก่อน</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">เปิดหน้าต่างเผยแพร่ล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>รายการโปรดยังไม่พร้อม: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>ไม่สามารถลบ '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>ยังไม่มีรายการโปรดที่บันทึกไว้ — ใช้ตัวกรองแล้วคลิกตัวบ่งชี้ ★ เพื่อบันทึกรายการแรกของคุณ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>ไม่สามารถเปิดตัวจัดการรายการโปรดได้ ดูรายละเอียดใน filtermate.log</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>ไม่สามารถแทนที่ '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>ไม่สามารถบันทึก '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>ไม่สามารถนำเข้ารายการโปรดส่วนกลาง: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>ไม่สามารถคัดลอกไปยังส่วนกลาง: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>ไม่สามารถบันทึกรายการโปรดลงในไฟล์โปรเจกต์: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>ไม่สามารถล้างโปรเจกต์ที่ไม่มีเจ้าของได้ ดูรายละเอียดใน filtermate.log</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>ไม่มีสถิติฐานข้อมูล ดูรายละเอียดใน filtermate.log</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="204"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - ตัวจัดการรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1165"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;รายการโปรดที่บันทึก ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="266"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>ค้นหาตามชื่อ นิพจน์ แท็ก หรือคำอธิบาย...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>ทั่วไป</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>นิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>ระยะไกล</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>ชื่อรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>ชื่อ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>คำอธิบาย (สร้างอัตโนมัติ, แก้ไขได้)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>คำอธิบาย:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>ป้อนแท็กคั่นด้วยเครื่องหมายจุลภาค (เช่น เมือง, ประชากร, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>แท็กช่วยจัดระเบียบและค้นหารายการโปรด
คั่นแท็กหลายรายการด้วยเครื่องหมายจุลภาค</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>แท็ก:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>เลเยอร์ต้นทาง:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>ผู้ให้บริการ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>ใช้แล้ว:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>สร้างเมื่อ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;นิพจน์เลเยอร์ต้นทาง:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>นิพจน์ตัวกรองสำหรับเลเยอร์ต้นทาง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;เลเยอร์ระยะไกลที่กรองแล้ว:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>เลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;ไม่มีเลเยอร์ระยะไกลในรายการโปรดนี้&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>ใช้งาน</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>ใช้ตัวกรองรายการโปรดนี้กับโปรเจกต์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>บันทึกการเปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>บันทึกการแก้ไขรายการโปรดนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="733"/>
        <source>Delete</source>
        <translation>ลบ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="736"/>
        <source>Permanently delete this favorite</source>
        <translation>ลบรายการโปรดนี้อย่างถาวร</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="739"/>
        <source>Close</source>
        <translation>ปิด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>ปิดกล่องโต้ตอบนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="849"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;รายการโปรด ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1015"/>
        <source>Remote ({0})</source>
        <translation>ระยะไกล ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete Favorite</source>
        <translation>ลบรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>ลบรายการโปรด '{0}' หรือไม่?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>เลเยอร์ระยะไกล</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1303"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;รายการโปรดที่บันทึก (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">ตัวจัดการรายการโปรด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>No favorites saved yet.

Click the ★ indicator and select 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">ยังไม่มีรายการโปรดที่บันทึก

คลิกตัวบ่งชี้ ★ และเลือก 'เพิ่มตัวกรองปัจจุบันไปยังรายการโปรด' เพื่อบันทึกรายการโปรดแรกของคุณ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>แบ่งปัน…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>เรียกดูรายการโปรดที่แบ่งปันผ่านคอลเลกชัน QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>เผยแพร่…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>เผยแพร่รายการโปรดที่เลือกไปยังคอลเลกชัน Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">ไม่สามารถลบ «{0}» รายการโปรดยังคงอยู่ในฐานข้อมูล — ตรวจสอบบันทึกของ FilterMate สำหรับรายละเอียด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>กรองรายการโปรดตามขอบเขต (เจ้าของ × โครงการ)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>แบ่งปัน · ทุกโครงการ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>แบ่งปัน · โครงการนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>ของฉัน · ทุกโครงการ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>ของฉัน · โครงการนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>ของฉัน</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>แบ่งปัน</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>โครงการนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>ทุกโครงการ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>ขอบเขตของโครงการจะถูกกำหนดเมื่อสร้างรายการโปรด ย้ายผ่านแท็บกรอง (เร็ว ๆ นี้) เพื่อสลับโครงการ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>การมองเห็น:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (แบ่งปันกับทุกคน)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (คุณ)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — การเลือก 'ของฉัน' เมื่อบันทึกจะโอนความเป็นเจ้าของให้คุณ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>ไม่สามารถบันทึก '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>ไม่สามารถลบ '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>ไม่พบ '{0}' ในฐานข้อมูล — รีเฟรชแล้วลองอีกครั้ง</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="604"/>
        <source>View</source>
        <translation>วิว</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="606"/>
        <source>Change</source>
        <translation>เปลี่ยน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>เลือกโฟลเดอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>เลือกไฟล์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>บันทึกเป็นไฟล์</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="664"/>
        <source>View</source>
        <translation>วิว</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="666"/>
        <source>Change</source>
        <translation>เปลี่ยน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>เลือกไอคอน</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>เลเยอร์ไม่ถูกต้องหรือไม่พบแหล่งข้อมูล ยกเลิกการดำเนินการแล้ว</translation>
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
        <translation>เปิดแผง FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>รีเซ็ตการกำหนดค่าและฐานข้อมูล</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>รีเซ็ตการกำหนดค่าเริ่มต้นและลบฐานข้อมูล SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>รีเซ็ตการกำหนดค่า</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>รีเซ็ตการกำหนดค่าสำเร็จแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>ไม่พบไฟล์การกำหนดค่าเริ่มต้น</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>ลบฐานข้อมูลแล้ว: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>ต้องรีสตาร์ท</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>ตรวจพบการกำหนดค่าที่ล้าสมัย</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>เวอร์ชันไม่ทราบ</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>ตรวจพบการกำหนดค่าที่ล้าสมัย ({}).

คุณต้องการรีเซ็ตเป็นค่าเริ่มต้นหรือไม่?

• ใช่: รีเซ็ต (จะสร้างสำเนาสำรอง)
• ไม่: เก็บการกำหนดค่าปัจจุบัน (อาจทำให้เกิดปัญหา)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>ตรวจพบการกำหนดค่าที่เสียหาย</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>ไฟล์การกำหนดค่าเสียหายและไม่สามารถอ่านได้

คุณต้องการรีเซ็ตเป็นค่าเริ่มต้นหรือไม่?

• ใช่: รีเซ็ต (จะสร้างสำเนาสำรองถ้าเป็นไปได้)
• ไม่: ยกเลิก (ปลั๊กอินอาจทำงานไม่ถูกต้อง)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>รีเซ็ตการกำหนดค่า</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>ต้องรีเซ็ตการกำหนดค่า

คุณต้องการดำเนินการต่อหรือไม่?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>ไม่ได้รีเซ็ตการกำหนดค่า ฟีเจอร์บางอย่างอาจทำงานไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>สร้างการกำหนดค่าด้วยค่าเริ่มต้นแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>รีเซ็ตการกำหนดค่าที่เสียหายแล้ว คืนค่าการตั้งค่าเริ่มต้นแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>รีเซ็ตการกำหนดค่าที่ล้าสมัยแล้ว คืนค่าการตั้งค่าเริ่มต้นแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>อัปเดตการกำหนดค่าเป็นเวอร์ชันล่าสุดแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>อัปเดตการกำหนดค่าแล้ว: การตั้งค่าใหม่พร้อมใช้งาน ({sections}) เข้าถึงผ่านเมนูตัวเลือก</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>การลดความซับซ้อนของเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>เกณฑ์การปรับปรุง</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>ข้อผิดพลาดระหว่างการย้ายการกำหนดค่า: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>การตั้งค่าการตรวจสอบเรขาคณิต</translation>
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
        <translation>การตั้งค่า QGIS 'การกรองฟีเจอร์ที่ไม่ถูกต้อง' ตั้งค่าเป็น '{mode}' อยู่ในปัจจุบัน

FilterMate แนะนำให้ปิดการตั้งค่านี้ (ค่า 'Off') ด้วยเหตุผลต่อไปนี้:

• ฟีเจอร์ที่มีเรขาคณิตไม่ถูกต้องอาจถูกยกเว้นจากการส่งออกและตัวกรองโดยไม่แจ้ง
• FilterMate จัดการการตรวจสอบเรขาคณิตภายในพร้อมตัวเลือกซ่อมแซมอัตโนมัติ
• ข้อมูลที่ถูกต้องบางส่วนอาจมีเรขาคณิตที่ถือว่า 'ไม่ถูกต้อง' ตามกฎ OGC ที่เข้มงวด

คุณต้องการปิดการตั้งค่านี้ตอนนี้หรือไม่?

• ใช่: ปิดการกรอง (แนะนำสำหรับ FilterMate)
• ไม่: เก็บการตั้งค่าปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>ปิดการกรองเรขาคณิตที่ไม่ถูกต้องสำเร็จแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>ไม่ได้แก้ไขการกรองเรขาคณิตที่ไม่ถูกต้อง ฟีเจอร์บางอย่างอาจถูกยกเว้นจากการส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>คุณแน่ใจหรือไม่ที่จะรีเซ็ตเป็นการกำหนดค่าเริ่มต้น?

การดำเนินการนี้จะ:
- คืนค่าการตั้งค่าเริ่มต้น
- ลบฐานข้อมูลเลเยอร์

ต้องรีสตาร์ท QGIS เพื่อใช้การเปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>รีเซ็ตการกำหนดค่าแล้ว

กรุณารีสตาร์ท QGIS เพื่อใช้การเปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>ข้อผิดพลาดในการเริ่มต้น: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} เลเยอร์อ้างอิงไม่ได้โหลด ({layers_list}) ใช้การแสดงผลสำรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>ไม่สามารถลบ {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">ข้อผิดพลาดระหว่างการรีเซ็ต: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;ขอบคุณที่ใช้ &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;เข้าร่วมชุมชน Discord ของเราเพื่อ:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;รับความช่วยเหลือและการสนับสนุน&lt;/li&gt;&lt;li&gt;รายงานข้อผิดพลาดและปัญหา&lt;/li&gt;&lt;li&gt;แนะนำฟีเจอร์ใหม่&lt;/li&gt;&lt;li&gt;แบ่งปันเคล็ดลับกับผู้ใช้อื่น&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  เข้าร่วมกับเราบน Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>ไม่ต้องแสดงอีก</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>ปิด</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>ข้อผิดพลาดในการโหลดปลั๊กอิน: {0} ตรวจสอบคอนโซล QGIS Python สำหรับรายละเอียด</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7357"/>
        <source>Current layer: {0}</source>
        <translation>เลเยอร์ปัจจุบัน: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7359"/>
        <source>No layer selected</source>
        <translation>ไม่ได้เลือกเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7369"/>
        <source>Selected layers:
{0}</source>
        <translation>เลเยอร์ที่เลือก:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7369"/>
        <source>No layers selected</source>
        <translation>ไม่ได้เลือกเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7389"/>
        <source>No expression defined</source>
        <translation>ไม่มีนิพจน์ที่กำหนด</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7401"/>
        <source>Display expression: {0}</source>
        <translation>นิพจน์การแสดงผล: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>รหัสฟีเจอร์: {0}
แอตทริบิวต์แรก: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>ไม่สามารถรีเซ็ตการกำหนดค่าได้ ตรวจสอบว่าโฟลเดอร์ปลั๊กอินเขียนได้ แล้วลองอีกครั้ง ดูรายละเอียดใน filtermate.log</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>มีอะไรใหม่ใน FilterMate 5</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;ตอนนี้ FilterMate ทำงานกับชั้นข้อมูลแรสเตอร์และพอยต์คลาวด์ได้แล้ว&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; ปรับตามชั้นข้อมูลปัจจุบัน: ช่วงค่าและคลาสของแรสเตอร์ คลาส ความสูง และแอตทริบิวต์ของพอยต์คลาวด์ LiDAR&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; เชื่อมโยงการเลือกนั้นกับชั้นข้อมูลทุกประเภท ด้วยเพรดิเคตและบัฟเฟอร์ตามปกติ: แปลงที่ดินในช่วงความสูง จุด LiDAR ใต้อาคาร DTM ที่ตัดตามขอบเขตเทศบาล&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; บันทึกแรสเตอร์ (GeoTIFF, COG) และพอยต์คลาวด์ (LAZ, COPC) ที่กรองแล้ว&lt;/li&gt;&lt;li&gt;อัลกอริทึมและโมเดลของ Processing, qgis_process, API ของ Python และ REST&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>เปิดคู่มือผู้ใช้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="207"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>ไม่สามารถประเมินนิพจน์นี้สำหรับบริการได้อย่างปลอดภัย</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="209"/>
        <source>The service could not be read. Please retry.</source>
        <translation>ไม่สามารถอ่านบริการได้ โปรดลองอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="210"/>
        <source>Read failed</source>
        <translation>อ่านล้มเหลว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="270"/>
        <source>Loading filtered extent…</source>
        <translation>กำลังโหลดขอบเขตที่กรอง…</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="306"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>ตรวจพบเลเยอร์ PostgreSQL ({0}) แต่ไม่ได้ติดตั้ง psycopg2</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="406"/>
        <source>Cleared {0} caches</source>
        <translation>ล้างแคช {0} รายการแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="912"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>สร้างด็อควิดเจ็ตล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="922"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>แสดงด็อควิดเจ็ตล้มเหลว: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1493"/>
        <source>Error executing {0}: {1}</source>
        <translation>ข้อผิดพลาดในการรัน {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1505"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>ปลั๊กอินทำงานในโหมดลดประสิทธิภาพ (บริการหกเหลี่ยมไม่พร้อมใช้งาน) ประสิทธิภาพอาจลดลง</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1854"/>
        <source>FilterMate ERROR</source>
        <translation>ข้อผิดพลาด FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1854"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>ไม่สามารถรัน {0}: การเริ่มต้นวิดเจ็ตล้มเหลว</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2635"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>ไม่สามารถ {0}: เลเยอร์ไม่ถูกต้องหรือไม่พบแหล่งข้อมูล</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2789"/>
        <source>All filters cleared - </source>
        <translation>ล้างตัวกรองทั้งหมดแล้ว - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2790"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} ฟีเจอร์ที่มองเห็นในเลเยอร์หลัก</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2802"/>
        <source>Error: result handler missing</source>
        <translation>ข้อผิดพลาด: ไม่พบตัวจัดการผลลัพธ์</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2819"/>
        <source>Error during filtering: {0}</source>
        <translation>ข้อผิดพลาดระหว่างการกรอง: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2943"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>กู้คืน {0} รายการโปรดที่ไม่มีเจ้าของ: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3109"/>
        <source>Layer loading failed - click to retry</source>
        <translation>โหลดเลเยอร์ล้มเหลว - คลิกเพื่อลองใหม่</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3161"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>โหลด {0} เลเยอร์สำเร็จแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2092"/>
        <source>filter</source>
        <translation>filter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2094"/>
        <source>unfilter</source>
        <translation>unfilter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2097"/>
        <source>FilterMate – Edit Mode Detected</source>
        <translation>FilterMate – Edit Mode Detected</translation>
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
        <translation>Save Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2116"/>
        <source>Discard Changes &amp; {0}</source>
        <translation>Discard Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2123"/>
        <source>Cancel</source>
        <translation>Cancel</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2147"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1323"/>
        <source>Pick a layer in the EXPLORING tab before running &apos;{0}&apos;.</source>
        <translation>เลือกเลเยอร์ในแท็บ EXPLORING ก่อนเรียกใช้ '{0}'</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="839"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} ชั้นข้อมูลยังคงถูกกรอง: {1} เปิดตัวเลือกอีกครั้งเพื่อยกเลิกการกรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2621"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>กำลังเตรียมตัวกรองเซิร์ฟเวอร์ โปรดรอให้เสร็จสิ้นก่อนเริ่มการดำเนินการอื่น</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1770"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>การดำเนินการ FilterMate API กำลังทำงานอยู่ โปรดรอให้เสร็จสิ้น</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>ข้อผิดพลาดในการเริ่มต้น: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>การกำหนดค่า UI ไม่สมบูรณ์ - ตรวจสอบบันทึก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">ข้อผิดพลาดมิติ UI: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>ตัวจัดการรายการโปรดไม่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} รายการโปรดที่บันทึก
คลิกเพื่อใช้หรือจัดการ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ ไม่มีรายการโปรดที่บันทึก
คลิกเพื่อเพิ่มตัวกรองปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>บังคับแบ็กเอนด์ {0} สำหรับ {1} เลเยอร์แล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>ตัวควบคุมแบ็กเอนด์ไม่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>เปิดการล้างอัตโนมัติ PostgreSQL แล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>ปิดการล้างอัตโนมัติ PostgreSQL แล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>ล้างวิวเซสชัน PostgreSQL แล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>ไม่มีวิวที่จะล้างหรือการล้างล้มเหลว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <source>No PostgreSQL connection available</source>
        <translation>ไม่มีการเชื่อมต่อ PostgreSQL ที่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>สคีมามี {0} วิวจากเซสชันอื่น
ลบอยู่ดีหรือไม่?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>เซสชันอื่นที่ใช้งานอยู่</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>ยกเลิกการล้างสคีมาแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>ลบสคีมา '{0}' สำเร็จแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <source>Schema cleanup failed</source>
        <translation>การล้างสคีมาล้มเหลว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>ข้อมูลเซสชัน PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>ปรับธีมแล้ว: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>โหมดมืด</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>โหมดสว่าง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4102"/>
        <source>Selected features have no geometry.</source>
        <translation>ฟีเจอร์ที่เลือกไม่มีเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4121"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>ไม่ได้เลือกฟีเจอร์ เลือกฟีเจอร์จากรายการแบบเลื่อนลง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5285"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>เลเยอร์ที่เลือกไม่ถูกต้องหรือไม่พบแหล่งข้อมูล</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6080"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>บัฟเฟอร์ลบ (การกัดเซาะ): หดรูปหลายเหลี่ยมเข้าด้านใน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6083"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>ค่าบัฟเฟอร์เป็นเมตร (บวก=ขยาย, ลบ=หดรูปหลายเหลี่ยม)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6585"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>เปิดใช้งานปลั๊กอินด้วย {0} เลเยอร์เวกเตอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6684"/>
        <source>Could not reload plugin automatically.</source>
        <translation>ไม่สามารถโหลดปลั๊กอินใหม่โดยอัตโนมัติ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6689"/>
        <source>Error reloading plugin: {0}</source>
        <translation>ข้อผิดพลาดในการโหลดปลั๊กอินใหม่: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6764"/>
        <source>Layer properties reset to defaults</source>
        <translation>รีเซ็ตคุณสมบัติเลเยอร์เป็นค่าเริ่มต้นแล้ว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6765"/>
        <source>Error resetting layer properties: {}</source>
        <translation>ข้อผิดพลาดในการรีเซ็ตคุณสมบัติเลเยอร์: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="895"/>
        <source>Filter</source>
        <translation>กรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>เลิกทำตัวกรองล่าสุด</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>ทำซ้ำตัวกรองล่าสุด</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>ลบตัวกรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>ส่งออกเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>เกี่ยวกับ FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>ระบุฟีเจอร์ที่เลือก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>ซูมไปที่ฟีเจอร์ที่เลือก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>เลือกฟีเจอร์บนแผนที่</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>ติดตามฟีเจอร์บนแผนที่</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">เชื่อมโหมดการเลือกทั้งสามเข้าด้วยกัน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>รีเซ็ตคุณสมบัติของเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>ติดตามเลเยอร์ปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>เลเยอร์ที่จะกรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>รวมกับตัวกรองที่มีอยู่</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>เพรดิเคตเชิงเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>ระยะบัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>ชนิดบัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>เลเยอร์ที่จะส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>ระบบพิกัดของการส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>ส่งออกสไตล์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>รูปแบบการส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>โฟลเดอร์ปลายทาง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>บีบอัดการส่งออกเป็น ZIP</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>ไม่สามารถใช้เลย์เอาต์ของแผงได้ จึงใช้ขนาดเริ่มต้น ดูรายละเอียดใน filtermate.log</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6856"/>
        <source>Vector</source>
        <translation>เวกเตอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>ลิงก์การเลือกเดี่ยวและหลายรายการ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>สคีมา '{0}' และอ็อบเจกต์ชั่วคราว {1} รายการต่อไปนี้จะถูกลบ:</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>... และอีก {0} รายการ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>สคีมา '{0}' ว่างเปล่าและจะถูกลบ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>ลบสคีมา FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4224"/>
        <source>Read failed</source>
        <translation>อ่านล้มเหลว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4224"/>
        <source>The service could not be read. Please retry.</source>
        <translation>ไม่สามารถอ่านบริการได้ โปรดลองอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4566"/>
        <source>Loading filtered extent…</source>
        <translation>กำลังโหลดขอบเขตที่กรอง…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5150"/>
        <location filename="../ui/controllers/exploring_controller.py" line="539"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3408"/>
        <source>Loading selected values…</source>
        <translation>กำลังโหลดค่าที่เลือก…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5141"/>
        <location filename="../ui/controllers/exploring_controller.py" line="502"/>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>ไม่สามารถประเมินนิพจน์นี้สำหรับบริการได้อย่างปลอดภัย</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2472"/>
        <source>Error evaluating expression: {0}</source>
        <translation>เกิดข้อผิดพลาดในการประเมินนิพจน์: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2471"/>
        <source>Expression Evaluation</source>
        <translation>การประเมินนิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="411"/>
        <source>Loading values…</source>
        <translation>กำลังโหลดค่า…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="646"/>
        <source>Loading zoom extent…</source>
        <translation>กำลังโหลดขอบเขตการซูม…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="633"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>ไม่มีฟีเจอร์ที่มีเรขาคณิตตรงกับการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="408"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>แสดงค่าเพียงบางส่วนเท่านั้น โปรดปรับการค้นหาให้เจาะจงขึ้นเพื่อหาค่าอื่น</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="475"/>
        <location filename="../ui/controllers/exploring_controller.py" line="483"/>
        <location filename="../ui/controllers/exploring_controller.py" line="502"/>
        <location filename="../ui/controllers/exploring_controller.py" line="566"/>
        <source>Selection</source>
        <translation>การเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="475"/>
        <location filename="../ui/controllers/exploring_controller.py" line="566"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>การเลือกบริการเกินขีดจำกัดคีย์ โปรดปรับการเลือกให้แคบลง</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="483"/>
        <source>This service has no stable key for the selection.</source>
        <translation>บริการนี้ไม่มีคีย์ที่คงที่สำหรับการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="408"/>
        <source>Values</source>
        <translation>ค่า</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <location filename="../ui/controllers/exploring_controller.py" line="633"/>
        <source>Zoom</source>
        <translation>ซูม</translation>
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
        <translation>การเลือกรายการเดียว</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>การเลือกหลายรายการ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>การเลือกแบบกำหนดเอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>การกรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>การส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>การกำหนดค่า</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>เลือก CRS สำหรับการส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>ส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2330"/>
        <source>AND</source>
        <translation>AND</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2335"/>
        <source>AND NOT</source>
        <translation>AND NOT</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2340"/>
        <source>OR</source>
        <translation>OR</translation>
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
        <translation>การกรองหลายเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>การกรองแบบสะสมสำหรับเลเยอร์ที่เลือก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>การกรองเชิงพื้นที่</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>บัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>เลเยอร์นิพจน์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>เพรดิเคตเชิงเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>รูปแบบผลลัพธ์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>ตัวกรอง</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>รีเซ็ต</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>เลเยอร์ที่จะส่งออก</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>การฉายเลเยอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>บันทึกสไตล์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>ส่งออกชนิดข้อมูล</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>ชื่อไฟล์/ไดเรกทอรี</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>ใช้จุดศูนย์กลางแทนเรขาคณิตเต็มสำหรับเลเยอร์ต้นทาง (เร็วกว่าสำหรับรูปหลายเหลี่ยมซับซ้อน)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>ค่าบัฟเฟอร์เป็นเมตร (บวก=ขยาย, ลบ=หดรูปหลายเหลี่ยม)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>จำนวนเซกเมนต์สำหรับความแม่นยำของบัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>โหมดชุด</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="556"/>
        <source>FilterMate was unloaded</source>
        <translation>FilterMate ถูกยกเลิกการโหลดแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="118"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>ราสเตอร์ที่แสดงผลหรือไม่รองรับ: ไม่สามารถเป็นเป้าหมายของตัวกรองได้</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="505"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>แหล่งราสเตอร์ที่แสดงผลต้องใช้การจับภาพสีในเครื่อง ไม่สามารถเลือกพิกเซลตามตัวเลขได้</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="577"/>
        <source>the source layer itself was not changed</source>
        <translation>เลเยอร์ต้นทางเองไม่ได้ถูกเปลี่ยนแปลง</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="347"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} ฟีเจอร์ที่มองเห็นในเลเยอร์หลัก</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>ล้างตัวกรองทั้งหมดแล้ว - {count} ฟีเจอร์ที่มองเห็นในเลเยอร์หลัก</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>งานล้มเหลว</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>ตัวกรองล้มเหลวสำหรับ: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0} เพิ่มเติม)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>กรองเลเยอร์แล้ว</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>กรองเลเยอร์เป็นสถานะก่อนหน้าแล้ว</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>ยกเลิกการกรองเลเยอร์แล้ว</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>งานตัวกรอง : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>งานส่งออก : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>ข้อยกเว้น: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>ไม่ได้ใช้ตัวกรอง คงตัวกรองก่อนหน้าไว้: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>เลเยอร์ถูกลบระหว่างการกรอง จึงถูกข้าม: {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>วาดโซนการเลือกที่ใช้งานได้ก่อนคำนวณความสูงเหนือพื้นดินจากระยะไกล</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>DTM และพอยต์คลาวด์ไม่มีขอบเขตที่ใช้งานได้ร่วมกัน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>การเลือกที่ใช้งานได้ไม่มีพื้นที่โพลิกอน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>ความสูงเหนือพื้นดินครอบคลุมเฉพาะพื้นที่ที่ใช้งานได้ Unfilter จะคืนค่าพอยต์คลาวด์เดิม</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>เมนูและแถบเครื่องมือ Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>คุณสมบัติ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>ค่า</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>คุณสมบัติ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>ค่า</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="262"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>ตรวจพบเลเยอร์ PostgreSQL ({0}) แต่ไม่ได้ติดตั้ง psycopg2 ปลั๊กอินไม่สามารถใช้เลเยอร์เหล่านี้ได้ ติดตั้ง psycopg2 เพื่อเปิดใช้การสนับสนุน PostgreSQL</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>ไม่สามารถเปิดต้นทางที่บันทึกไว้ได้</translation>
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
        <translation>เลเยอร์ PostgreSQL '{0}': ตรวจพบข้อมูลที่เสียหาย

เลเยอร์นี้ใช้ 'virtual_id' ซึ่งไม่มีอยู่ใน PostgreSQL
ข้อผิดพลาดนี้มาจากเวอร์ชันก่อนหน้าของ FilterMate

วิธีแก้: ลบเลเยอร์นี้จากโปรเจกต์ FilterMate แล้วเพิ่มใหม่
ตรวจสอบให้แน่ใจว่าตาราง PostgreSQL มี PRIMARY KEY ที่กำหนดไว้</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>เลเยอร์ '{0}' ไม่มี PRIMARY KEY ฟีเจอร์จำกัด: วิวแบบ materialized ถูกปิด คำแนะนำ: เพิ่ม PRIMARY KEY เพื่อประสิทธิภาพที่ดีที่สุด</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>ข้อยกเว้น: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: ผู้ให้บริการนี้ไม่สามารถรับประกันตัวกรองเซิร์ฟเวอร์ที่สมบูรณ์ได้ โปรดใช้สำเนาในเครื่องแบบจำกัดก่อนกรอง</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: ไม่สามารถอ่านค่าคีย์ของฟีเจอร์ที่เลือกจากเว็บเซอร์วิสได้</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>ไม่ถูกกรอง</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: เว็บเซอร์วิสนี้ไม่มีฟิลด์คีย์ที่ไม่ซ้ำกัน (คีย์ที่ประกาศไว้, id, gml_id, cleabs, objectid...) จึงไม่สามารถแสดงรายการฟีเจอร์ที่เลือกให้เซิร์ฟเวอร์ได้ เลเยอร์ {1} ตัวกรองแอตทริบิวต์หรือสำเนาของเลเยอร์ในเครื่องใช้งานได้</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: เลเยอร์นี้ไม่มีฟิลด์คีย์ที่ไม่ซ้ำกัน จึงไม่สามารถแสดงรายการ id ของฟีเจอร์ในตัวกรองได้ (เลเยอร์เสมือนต้องมีคอลัมน์ id ที่ไม่ซ้ำกัน คือ uid) เลเยอร์ {1}</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: มีฟีเจอร์ที่ต้องแสดงรายการ {1} รายการ มากกว่า {2} รายการที่ส่งไปยังเว็บเซอร์วิสได้ เลเยอร์ {3} โปรดจำกัดการเลือก ใช้ตัวกรองแอตทริบิวต์ หรือทำงานกับสำเนาของเลเยอร์ในเครื่อง</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>การตั้งค่าการปรับปรุง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>กำหนดค่าการตั้งค่าการปรับปรุง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>เปิดใช้การปรับปรุงอัตโนมัติ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>ถามก่อนใช้การปรับปรุง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>การตั้งค่าจุดศูนย์กลางอัตโนมัติ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>เปิดใช้จุดศูนย์กลางอัตโนมัติสำหรับเลเยอร์ที่อยู่ไกล</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>เกณฑ์ระยะทาง (กม.):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>เกณฑ์ฟีเจอร์:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>การปรับปรุงบัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>ลดความซับซ้อนของเรขาคณิตก่อนบัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>ลดเซกเมนต์บัฟเฟอร์เป็น:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>ทั่วไป</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>ใช้วิวแบบ materialized สำหรับการกรอง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>สร้างดัชนีเชิงพื้นที่โดยอัตโนมัติ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>ใช้ดัชนีเชิงพื้นที่ R-tree</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>ใช้ตัวกรองเบื้องต้นกรอบขอบเขต</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>แบ็กเอนด์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>แคช</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>เปิดใช้แคชเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>การประมวลผลแบบชุด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>ขนาดชุด:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>การตั้งค่าขั้นสูงส่งผลต่อประสิทธิภาพและการใช้หน่วยความจำ เปลี่ยนเฉพาะเมื่อคุณเข้าใจผลกระทบ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>ขั้นสูง</translation>
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
        <translation>การเชื่อมกับเงื่อนไขก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="799"/>
        <source>AND</source>
        <translation>AND</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="800"/>
        <source>OR</source>
        <translation>OR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="801"/>
        <source>Attribute</source>
        <translation>แอตทริบิวต์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>การเปรียบเทียบ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>ระหว่าง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>ลบเงื่อนไขนี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>เปรียบเทียบกับค่าหรือแอตทริบิวต์อื่น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="821"/>
        <source>value</source>
        <translation>ค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="822"/>
        <source>Value</source>
        <translation>ค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="825"/>
        <source>Highest value kept</source>
        <translation>ค่าสูงสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>ค่าที่พบ: {0} ถึง {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>ไม่มีสถิติสำหรับแอตทริบิวต์นี้</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1049"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>นำไปใช้กับไทล์อื่นของชุดข้อมูล</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1058"/>
        <source>CLASSES</source>
        <translation>คลาส</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1063"/>
        <source>Ground</source>
        <translation>พื้นดิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1064"/>
        <source>Vegetation</source>
        <translation>พืชพรรณ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1065"/>
        <source>Buildings</source>
        <translation>อาคาร</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1066"/>
        <source>Above ground</source>
        <translation>เหนือพื้นดิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Water</source>
        <translation>น้ำ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Without noise</source>
        <translation>ไม่รวมสัญญาณรบกวน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">ติ๊กเฉพาะคลาสเหล่านี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">ไม่มี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1097"/>
        <source>Point classes</source>
        <translation>คลาสของจุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">ช่วงแอตทริบิวต์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (ม.)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">ความสูงต่ำสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">ความสูงสูงสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1344"/>
        <source>Intensity</source>
        <translation>ความเข้ม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">ความเข้มต่ำสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">ความเข้มสูงสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">รีเทิร์น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">เอคโคของพัลส์เลเซอร์ที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">ความสูงเหนือ DTM ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1286"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>แบบจำลองภูมิประเทศเชิงเลขที่ใช้วัดความสูง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1296"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>เก็บจุดที่สูงกว่าแบบจำลองภูมิประเทศอย่างน้อยเท่านี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>EXPRESSION</source>
        <translation>นิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>Point cloud expression</source>
        <translation>นิพจน์พอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1376"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>ติ๊กกลุ่มนี้เพื่อแก้ไขนิพจน์ด้วยตนเอง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">ไม่มีสถิติความสูงสำหรับเลเยอร์นี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1657"/>
        <source>Height above the terrain is unavailable</source>
        <translation>ไม่สามารถใช้ความสูงเหนือภูมิประเทศได้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">จุดที่เก็บไว้: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">ตัวกรองปัจจุบัน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">ไม่มี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">ใดก็ได้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">แรก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Last</source>
        <translation type="obsolete">สุดท้าย</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Single</source>
        <translation type="obsolete">เดี่ยว</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1172"/>
        <source>ATTRIBUTES</source>
        <translation>แอตทริบิวต์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1190"/>
        <source>+ Condition</source>
        <translation>+ เงื่อนไข</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1192"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>เพิ่มเงื่อนไขบนแอตทริบิวต์ของชั้นข้อมูล</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1231"/>
        <source>Returns</source>
        <translation>การสะท้อนกลับ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">เก็บการสะท้อนกลับแรก สุดท้าย หรือเดี่ยวของพัลส์เลเซอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1238"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>การสะท้อนแรก (ReturnNumber = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1239"/>
        <source>Last return (ReturnNumber = NumberOfReturns)</source>
        <translation>การสะท้อนสุดท้าย (ReturnNumber = NumberOfReturns)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1240"/>
        <source>Single return (NumberOfReturns = 1)</source>
        <translation>การสะท้อนเดี่ยว (NumberOfReturns = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1345"/>
        <source>Return number</source>
        <translation>หมายเลขรีเทิร์น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1346"/>
        <source>Number of returns</source>
        <translation>จำนวนการสะท้อน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1347"/>
        <source>Classification</source>
        <translation>การจัดประเภท</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Scan angle</source>
        <translation>มุมสแกน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1349"/>
        <source>User data</source>
        <translation>ข้อมูลผู้ใช้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1350"/>
        <source>Point source ID</source>
        <translation>รหัสแหล่งจุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1351"/>
        <source>GPS time</source>
        <translation>เวลา GPS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Red</source>
        <translation>แดง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>Green</source>
        <translation>เขียว</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Blue</source>
        <translation>น้ำเงิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>Infrared</source>
        <translation>อินฟราเรด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Scan direction</source>
        <translation>ทิศทางการสแกน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1357"/>
        <source>Edge of flight line</source>
        <translation>ขอบแนวบิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1358"/>
        <source>Synthetic</source>
        <translation>สังเคราะห์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1359"/>
        <source>Key point</source>
        <translation>จุดสำคัญ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Withheld</source>
        <translation>ถูกระงับ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Overlap</source>
        <translation>ส่วนซ้อนทับ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Scanner channel</source>
        <translation>ช่องสัญญาณสแกนเนอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Classification flags</source>
        <translation>แฟล็กการจำแนก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Height above ground</source>
        <translation>ความสูงเหนือพื้นดิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1077"/>
        <source>Quick class selection</source>
        <translation>เลือกคลาสด่วน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">เลือกด่วน…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1087"/>
        <source>All classes</source>
        <translation>ทุกคลาส</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1087"/>
        <source>No class</source>
        <translation>ไม่มีคลาส</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1087"/>
        <source>Invert the selection</source>
        <translation>กลับการเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1077"/>
        <source>Selection ▾</source>
        <translation>การเลือก ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1111"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>คลาสของมาตรฐานที่ไม่มีจุดใดในเลเยอร์นี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1118"/>
        <source>Classes absent from the layer</source>
        <translation>คลาสที่ไม่มีในเลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1142"/>
        <source>Similar objects: area ×</source>
        <translation>วัตถุที่คล้ายกัน: พื้นที่ ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1145"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>วัตถุที่คล้ายกันที่เล็กที่สุด เป็นสัดส่วนของวัตถุที่คลิกที่เล็กที่สุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1145"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>วัตถุที่คล้ายกันที่ใหญ่ที่สุด เป็นกี่เท่าของวัตถุที่คลิกที่ใหญ่ที่สุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1160"/>
        <source>to ×</source>
        <translation>ถึง ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1204"/>
        <source>Pipette on</source>
        <translation>เปิดตัวเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1205"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>แอตทริบิวต์ที่ตัวเลือกค่าของแถบด้านข้างอ่านใต้ตำแหน่งที่คลิก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1220"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>ค่าความคลาดเคลื่อนรอบค่าที่เลือก เป็น % ของช่วงที่สังเกตได้ของแอตทริบิวต์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1232"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>เก็บทุกรีเทิร์น หรือรีเทิร์นแรก สุดท้าย หรือรีเทิร์นเดียวของพัลส์เลเซอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1237"/>
        <source>Any return</source>
        <translation>รีเทิร์นใดก็ได้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1251"/>
        <source>HEIGHT / DTM</source>
        <translation>ความสูง / DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1257"/>
        <source>Always combined (AND) with the active group</source>
        <translation>รวมกับกลุ่มที่ใช้งานด้วย (AND) เสมอ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · พอยต์คลาวด์ที่สร้างขึ้น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1263"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>ความสูงถูกคำนวณโดย PDAL เป็นพอยต์คลาวด์ที่สร้างขึ้น ในงานเบื้องหลัง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>{0} object(s)</source>
        <translation>{0} วัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>cut at the window read</source>
        <translation>ถูกตัดที่หน้าต่างที่อ่าน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>shown as the whole class in their box</source>
        <translation>แสดงเป็นทั้งคลาสในกล่องของวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1859"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>คลาสอื่นที่ไม่มีในเลเยอร์ ({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1950"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>มีวัตถุขยายเกินหน้าต่างอ่านที่ใหญ่ที่สุดรอบตำแหน่งที่คลิกและถูกตัดที่ขอบหน้าต่าง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1952"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>วัตถุมากเกินไปสำหรับส่วนย่อยของพอยต์คลาวด์: การดูตัวอย่างและพอยต์คลาวด์ที่กรองจะเก็บทุกจุดของคลาสของตนในกล่องรอบวัตถุ ส่วนเป้าหมายจะถูกตัดตามวัตถุเอง</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">ตัวกรองพอยต์คลาวด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">การจัดประเภท</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">ไม่มี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">ความสูง (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">ความเข้ม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="175"/>
        <source>Return number</source>
        <translation type="obsolete">หมายเลขรีเทิร์น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="199"/>
        <source>Minimum</source>
        <translation type="obsolete">ต่ำสุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="200"/>
        <source>Maximum</source>
        <translation type="obsolete">สูงสุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">ตัวกรองปัจจุบัน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">ไม่มี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">ใดก็ได้</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>พอยต์คลาวด์ระยะไกลต้องมีขอบเขตที่ใช้งานได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>ไม่มีตัวอ่าน PDAL สำหรับรูปแบบพอยต์คลาวด์นี้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>พอยต์คลาวด์ระยะไกลต้องใช้ PDAL 2.4 ขึ้นไปที่อ่านเวอร์ชันได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>พอยต์คลาวด์ระยะไกลต้องเป็น EPT หรือ COPC เพื่อการอ่านแบบจำกัด</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>ขอบเขตที่ใช้งานได้ต้องมีขอบเขตจำกัดและมีพื้นที่เป็นบวก</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="435"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>วาดโซนการเลือกที่ใช้งานได้ก่อนอ่านพอยต์คลาวด์ระยะไกล</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="468"/>
        <source>The remote point cloud could not be read</source>
        <translation>ไม่สามารถอ่านพอยต์คลาวด์ระยะไกลได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="472"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>พอยต์คลาวด์ระยะไกลปฏิเสธการเลือก</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="605"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>พอยต์คลาวด์ความสูงเหนือพื้นดินแบบจำกัดรองรับเฉพาะ AND หรือ AND NOT เท่านั้น ให้ Unfilter ก่อน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="631"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>ต้องใช้ PDAL 2.4 ขึ้นไปเพื่อตัดพอยต์คลาวด์ระยะไกล</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="682"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Disjoint จะอ่านพอยต์คลาวด์ระยะไกลทั้งหมด โปรดเลือกการเลือกแบบอยู่ภายใน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="689"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>ไม่สามารถเปิดพอยต์คลาวด์ระยะไกลต้นฉบับได้</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>ข้อมูลเซสชัน PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL ใช้งานอยู่</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>ข้อมูลการเชื่อมต่อ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>การเชื่อมต่อ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>สคีมาชั่วคราว:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>สถานะ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>วิวชั่วคราว</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>ตัวเลือกการล้าง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>ล้างอัตโนมัติเมื่อปิด</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>ล้างวิวชั่วคราวอัตโนมัติเมื่อปิด FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ ล้างตอนนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>ลบวิวชั่วคราวทั้งหมดที่สร้างโดย FilterMate ในเซสชันนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(ไม่มีวิวชั่วคราว)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>ไม่มีวิว</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>ไม่มีวิวชั่วคราวที่จะล้าง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>ยืนยันการล้าง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>การล้างเสร็จสมบูรณ์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>ปัญหาการล้าง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>การล้างล้มเหลว</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL ไม่พร้อมใช้งาน&lt;/b&gt;&lt;br&gt;&lt;br&gt;หากต้องการใช้ฟีเจอร์ PostgreSQL ให้ติดตั้ง psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;จากนั้นรีสตาร์ท QGIS เพื่อใช้การเปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>เซสชัน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} วิวในเซสชันนี้</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>การดำเนินการนี้จะลบวิวชั่วคราว {view_count} รายการที่สร้างโดย FilterMate

ผลลัพธ์ตัวกรองที่ไม่ได้บันทึกจะสูญหาย

ดำเนินการต่อหรือไม่?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>ลบวิวชั่วคราว {result.views_dropped} รายการแล้ว</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>ไม่สามารถลบวิวบางรายการได้: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>ข้อผิดพลาดระหว่างการล้าง: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>เลเยอร์ที่จะกรอง</translation>
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
        <translation>บัฟเฟอร์</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="105"/>
        <source>Band</source>
        <translation>แบนด์</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>นิพจน์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="147"/>
        <source>Layers to export</source>
        <translation>เลเยอร์ที่จะส่งออก</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>โฟลเดอร์ปลายทาง</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>เพรดิเคตเชิงเรขาคณิต</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>ค่าพิกเซล</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>ความลาดชัน (องศา)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>ความลาดชัน (%)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>ทิศด้านลาด (องศา)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>ร่มเงาภูมิประเทศ (0-255)</translation>
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
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>ราสเตอร์ต้นทางถูกสุ่มใหม่เพื่อการจับภาพ (กริด: {0})</translation>
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
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: ราสเตอร์เป้าหมายถูกสุ่มใหม่เพื่อการจับภาพ (กริด: {1})</translation>
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
        <translation>FilterMate — เผยแพร่ไปยัง Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;เผยแพร่รายการโปรด&lt;/b&gt; — เขียนบันเดิลที่แบ่งปันได้ไปยังคอลเลกชัน QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>เขียนทับบันเดิลที่มีอยู่</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>เผยแพร่</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. คอลเลกชันเป้าหมาย&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>เรียกดู…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. ชื่อไฟล์บันเดิล&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>เช่น zones_bruxelles</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;เป้าหมาย&amp;gt;/filter_mate/favorites/&amp;lt;ชื่อ&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. เมตาดาต้าของคอลเลกชัน&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>ชื่อที่แสดงของคอลเลกชัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>ชื่อ:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>ผู้เขียน / องค์กร</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>ผู้เขียน:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>เช่น CC-BY-4.0, MIT, ลิขสิทธิ์เฉพาะ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>ใบอนุญาต:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>แท็กคั่นด้วยเครื่องหมายจุลภาค</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="221"/>
        <source>Tags:</source>
        <translation>แท็ก:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="224"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="225"/>
        <source>Homepage:</source>
        <translation>หน้าแรก:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="229"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>คำอธิบายสั้น ๆ (ไม่บังคับ, ข้อความธรรมดา)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>คำอธิบาย:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. รายการโปรดที่จะรวม&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>เลือกทั้งหมด</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>ไม่เลือก</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>คอลเลกชันใหม่ในรูทของ Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>ไดเรกทอรีที่กำหนดเอง…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>จะถูกสร้างภายใต้รูทของ Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>คลิก 'เรียกดู…' เพื่อเลือกไดเรกทอรี</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>เลือกไดเรกทอรีคอลเลกชัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>เลือกแล้ว {0} / {1}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>ไม่สามารถสร้างคอลเลกชัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>ไม่พบรูทของ Resource Sharing ใช้ 'เรียกดู…' เพื่อเลือกไดเรกทอรีแทน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>เลือกไดเรกทอรี</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>คลิก 'เรียกดู…' เพื่อเลือกไดเรกทอรีเป้าหมาย</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>ไม่ได้เลือกรายการโปรด</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>เลือกรายการโปรดอย่างน้อยหนึ่งรายการเพื่อเผยแพร่</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>การเผยแพร่ล้มเหลว</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>ข้อผิดพลาดที่ไม่รู้จัก</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>เผยแพร่รายการโปรด {0} รายการไปยัง:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>อัพเดทรายการของคอลเลกชันแล้ว:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>การเผยแพร่สำเร็จ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>ที่เก็บข้อมูลระยะไกลไม่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>ตัวจัดการที่เก็บข้อมูลระยะไกลไม่ได้เริ่มต้น</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>การเผยแพร่ไปยัง &lt;b&gt;{0}&lt;/b&gt; ล้มเหลว</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>เปิดโคลน…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>เขียนบันเดิลไปยัง:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>ส่ง commit &lt;code&gt;{0}&lt;/code&gt; ไปยัง &lt;b&gt;{1}&lt;/b&gt; แล้ว</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>ไม่ได้กำหนดค่า git_url — บันเดิลเขียนไว้ในเครื่อง ส่งด้วยตนเองผ่านเครื่องมือของคุณ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>ไม่มีอะไรจะ commit — เนื้อหาบันเดิลไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>กำลังเผยแพร่ไปยัง {0}...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>ยกเลิก</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>กำลังเผยแพร่</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>กำลังเผยแพร่</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>การเผยแพร่ยังทำงานอยู่เบื้องหลัง รอให้เสร็จก่อนเริ่มรายการใหม่</translation>
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
        <translation>คำอธิบาย:</translation>
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
        <translation>เลเยอร์</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="184"/>
        <source>Export</source>
        <translation>ส่งออก</translation>
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
        <translation>Error: {0}</translation>
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
        <translation>สถานะ:</translation>
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
        <translation>พิมพ์เพื่อกรอง...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>เลือกทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>เลือกทั้งหมด (ไม่ใช่ชุดย่อย)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>เลือกทั้งหมด (ชุดย่อย)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>ยกเลิกการเลือกทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>ยกเลิกการเลือกทั้งหมด (ไม่ใช่ชุดย่อย)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>ยกเลิกการเลือกทั้งหมด (ชุดย่อย)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>แสดง {0} ฟีเจอร์แรก เรียงตามค่าที่แสดง พิมพ์ในตัวกรองข้อความเพื่อค้นหาทั้งเลเยอร์ &quot;เลือกทั้งหมด&quot; จะโหลดรายการเต็ม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>แสดง {0} ฟีเจอร์ของเลเยอร์ เรียงตามค่าที่แสดง พิมพ์ในตัวกรองข้อความเพื่อค้นหาทั้งเลเยอร์ &quot;เลือกทั้งหมด&quot; จะโหลดรายการเต็ม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>ผลการค้นหา &quot;{0}&quot; ทั้งเลเยอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1768"/>
        <source>Loading values…</source>
        <translation>กำลังโหลดค่า…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>Values</source>
        <translation>ค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>ไม่สามารถประเมินนิพจน์นี้สำหรับบริการได้อย่างปลอดภัย</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1748"/>
        <source>Selection</source>
        <translation>การเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1748"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>รายการระยะไกลเกินขีดจำกัดการเลือกที่ปลอดภัย โปรดเลือกฟีเจอร์ให้น้อยลงหรือกรองเลเยอร์ก่อน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1924"/>
        <source>Loading selected values…</source>
        <translation>กำลังโหลดค่าที่เลือก…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>เลือกทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>ยกเลิกการเลือกทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>เลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (เส้น)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>ยกเลิกการเลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (เส้น)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>เลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (จุด)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>ยกเลิกการเลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (จุด)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>เลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (รูปหลายเหลี่ยม)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>ยกเลิกการเลือกเลเยอร์ทั้งหมดตามประเภทเรขาคณิต (รูปหลายเหลี่ยม)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>เลือกเลเยอร์ราสเตอร์ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>ยกเลิกการเลือกเลเยอร์ราสเตอร์ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>เลือกเลเยอร์พอยต์คลาวด์ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>ยกเลิกการเลือกเลเยอร์พอยต์คลาวด์ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>พิกเซลในโซน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>จุดในโซน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>เป้าหมายราสเตอร์: พิกเซลนอกเรขาคณิตต้นทางจะกลายเป็น NoData (พิกเซลด้านในเมื่อใช้ Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>เป้าหมายพอยต์คลาวด์: จุดนอกเรขาคณิตต้นทางจะถูกลบออก (จุดด้านในเมื่อใช้ Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>เป้าหมายเวกเตอร์: ฟีเจอร์ที่ตรงตามเพรดิเคตเชิงเรขาคณิตจะถูกเก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>คลิกช่องสี่เหลี่ยมทางขวาเพื่อทดสอบเลเยอร์นี้ด้วยจุดศูนย์กลาง</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>ฮิสโทแกรมช่วงค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>ลากที่จับ หรือคลิก เพื่อเลือกช่วงค่าที่จะเก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>ไม่มีฮิสโทแกรม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>เก็บค่าตั้งแต่ {0} ถึง {1}</translation>
    </message>
</context>
<context>
    <name>RasterExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="497"/>
        <source>Band</source>
        <translation type="obsolete">แบนด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="500"/>
        <source>Band whose values are selected</source>
        <translation type="obsolete">แบนด์ที่เลือกค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">ค่าพิกเซล</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">ค่าพิกเซลของแบนด์ปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">{0} ค่าล่าสุดที่เลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">คลิกบนแผนที่ด้วยตัวเลือกพิกเซล Ctrl+คลิก เพื่อขยายช่วงไปถึงค่านั้น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>ช่วงค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>ต่ำสุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>ค่าต่ำสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>สูงสุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>ค่าสูงสุดที่เก็บไว้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">ดูตัวอย่างบนแผนที่ (ซ่อนพิกเซลอื่น)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">คลาส</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">คลาสราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">ทั้งหมด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">ไม่มี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>นิพจน์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>นิพจน์ตัวคำนวณราสเตอร์ พิกเซลจะถูกเก็บไว้ที่ที่ค่าไม่เท่ากับ 0</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>นิพจน์ราสเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">ใช้ช่วงค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">เขียนช่วงค่าปัจจุบันเป็นนิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">พิกเซลที่เลือก: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>กำหนดช่วงค่าก่อน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2219"/>
        <source>NoData</source>
        <translation>NoData</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="834"/>
        <source>Last values:</source>
        <translation type="obsolete">ค่าล่าสุด:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="629"/>
        <source>Value of the current band under the cursor</source>
        <translation type="obsolete">ค่าของแบนด์ปัจจุบันใต้เคอร์เซอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">สถิติของแบนด์ปัจจุบันในสี่เหลี่ยมล่าสุดที่วาดบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>ใต้เคอร์เซอร์: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>โซน: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>ไม่มีพิกเซล</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>การอ่านล่าสุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">คำนวณจาก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">ปริมาณที่ช่วงนำไปใช้ ความลาดชัน ทิศด้านลาด ร่มเงาภูมิประเทศ และความขรุขระจะอ่านแบนด์เป็น DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>ค่าพิกเซล</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>ความลาดชัน (องศา)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>ความลาดชัน (%)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>ทิศด้านลาด (องศา)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>ร่มเงาภูมิประเทศ (0-255)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>ความขรุขระ (TRI, ผลต่างเฉลี่ย)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>ค่าเกณฑ์ที่ใช้บ่อยของปริมาณนี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">ค่าเกณฑ์ที่ใช้บ่อย</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>ราบ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>ลาดเล็กน้อย</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>ปานกลาง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>ชัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>ตะวันออก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>ใต้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>West</source>
        <translation>ตะวันตก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Shadow</source>
        <translation>เงา</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Lit</source>
        <translation>สว่าง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">ค่าเกณฑ์ที่ใช้บ่อย…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>ตัวเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>ค่าเผื่อ ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>ค่าเผื่อรอบสีหรือค่าที่เลือก เป็น % ของช่วงค่า</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>ค่าเผื่อของตัวเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>แบนด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">แบนด์ของภาพคืออะไร: พรีเซ็ตและตัวเลือกใช้ข้อมูลนี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">การจัดวางแบนด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB (แดง เขียว น้ำเงิน)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC (อินฟราเรด แดง เขียว)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + อินฟราเรด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">เขียนนิพจน์ของดัชนีที่ใช้บ่อย (พืชพรรณ น้ำ...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">พรีเซ็ตสเปกตรัม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">ต้องใช้ภาพที่มีสามแบนด์ขึ้นไป (แดง เขียว น้ำเงิน...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>พืชพรรณ (NDVI &gt; 0.3)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>ไม่มีพืชพรรณ (NDVI &lt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>น้ำ (NDWI &gt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>พืชพรรณ (สีเขียวส่วนเกิน)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">พรีเซ็ตสเปกตรัม…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>พิกเซลนี้ไม่มีค่า (NoData): เลือกพิกเซลอื่น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>ค่าเผื่อครอบคลุมทุกค่า: ลดลง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">ช่วง {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">คลาส {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} สี ล่าสุด: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">นิพจน์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>BANDS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>ค่าของแบนด์ที่ใช้งานใต้เคอร์เซอร์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>สถิติของแบนด์ที่ใช้งานในสี่เหลี่ยมสุดท้ายที่วาดบนแผนที่</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>ทุกแบนด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>ช่วงค่านำไปใช้กับทุกแบนด์สีพร้อมกัน (พิกเซลจะถูกเก็บไว้เมื่อทุกแบนด์อยู่ในช่วง) ฮิสโตแกรมแสดงแบนด์แรก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>แบนด์ที่ใช้งาน: แบนด์ที่ช่วงค่า ฮิสโตแกรม และตัวเลือกอ่าน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>ตัวเลือกเปรียบเทียบแบนด์นี้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>สีที่แบนด์ถืออยู่: ดัชนีสเปกตรัมและชิปใช้สีนี้ คลิกเพื่อเปลี่ยน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>ค่าที่การคลิกครั้งสุดท้ายของตัวเลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>ไม่มีสี</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>แบนด์ 1, 2, 3 คือแดง เขียว น้ำเงิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>IRC</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>แบนด์ 1, 2, 3 คืออินฟราเรด แดง เขียว (ออร์โทโฟโตอินฟราเรดสี IGN)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>แบนด์ 1, 2, 3, 4 คือแดง เขียว น้ำเงิน อินฟราเรดใกล้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>ทุกแบนด์: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> คาดเดาบทบาทไว้ โปรดยืนยัน</translation>
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
        <translation>แดง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Green</source>
        <translation>เขียว</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Blue</source>
        <translation>น้ำเงิน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1024"/>
        <source>Near infrared</source>
        <translation>อินฟราเรดใกล้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>คาดเดาบทบาทไว้ โปรดยืนยัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>เลือก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>พิกเซลที่คล้ายกัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>ทุกพิกเซลของราสเตอร์ที่ใกล้เคียงสีหรือค่าที่เลือก (ตัวเลือกของแถบด้านข้าง)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>วัตถุที่คลิก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>เฉพาะกลุ่มพิกเซลดังกล่าวที่ตำแหน่งคลิกตกอยู่: สระน้ำ หลังคา ทุ่งนา (ตัวตรวจจับวัตถุของแถบด้านข้าง) Ctrl+คลิก เพื่อเพิ่มอีกวัตถุ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>วัตถุที่คล้ายกัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>ทุกวัตถุของราสเตอร์ที่คล้ายวัตถุที่คลิก: กลุ่มพิกเซลดังกล่าวที่มีพื้นที่อยู่ในอัตราส่วนด้านล่าง (เครื่องมือวัตถุที่คล้ายกันของแถบด้านข้าง) Ctrl+คลิก เพื่อเพิ่มวัตถุอ้างอิงอีกชิ้น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>พื้นที่ ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>วัตถุที่คล้ายกันที่เล็กที่สุด เป็นสัดส่วนของวัตถุที่คลิกที่เล็กที่สุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>วัตถุที่คล้ายกันที่ใหญ่ที่สุด เป็นกี่เท่าของวัตถุที่คลิกที่ใหญ่ที่สุด</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>ถึง ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>รูปร่างเดียวกัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>เก็บเฉพาะวัตถุที่มีรูปร่างเหมือนวัตถุที่คลิก: ความกะทัดรัด (4π × พื้นที่ / เส้นรอบรูป², เท่ากับ 1 สำหรับวงกลม) ภายในอัตราส่วนเดียวกัน เมื่อปิด ถนนที่มีพื้นที่เท่าสระน้ำจะถูกนับเป็นสระน้ำ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>เอาการเลือกนี้ออก</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>ปริมาณ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>ปริมาณที่ช่วงค่านำไปใช้ ความลาดชัน ทิศด้านลาด เงาเขา และความขรุขระอ่านแบนด์ที่ใช้งานเป็น DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>เกณฑ์ ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>แทรก ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>แทรกการอ้างอิงแบนด์ ดัชนีสเปกตรัมที่ใช้บ่อย หรือช่วงปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>ดัชนีสเปกตรัม</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>ช่วง</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>ช่วงค่าปัจจุบัน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>สีที่แสดงผลขึ้นอยู่กับสไตล์และมาตราส่วน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>ใช้ได้เฉพาะการเลือกตามสี: แบนด์ตัวเลข ดัชนี ช่วง คลาส และข้อมูลอนุพันธ์ใช้ไม่ได้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>ช่วงค่า — ทุกแบนด์</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>ช่วงค่า — แบนด์ {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>เลือกจาก: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>ความลาดชัน ทิศด้านลาด ฯลฯ อ่านหนึ่งแบนด์เป็น DTM: เลือกแบนด์ใน BANDS ก่อน</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>ไม่สามารถอ่านวัตถุได้</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>ไม่มีวัตถุใต้ตำแหน่งที่คลิก: เพิ่มค่าความคลาดเคลื่อนหรือคลิกพิกเซลอื่น</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>มีวัตถุใหญ่กว่าหน้าต่างที่อ่านและถูกตัด: ลดค่าความคลาดเคลื่อน</translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>การจับภาพราสเตอร์แบบจำกัดล้มเหลว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="224"/>
        <source>local raster capture could not be opened</source>
        <translation>ไม่สามารถเปิดการจับภาพราสเตอร์ในเครื่องได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="213"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>การวิเคราะห์ราสเตอร์ต้องใช้การจับภาพ GDAL ในเครื่อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>ยกเลิกการจับภาพราสเตอร์แล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>ปลายทางการจับภาพราสเตอร์ต้องอยู่ในแคชของเซสชัน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>ไม่สามารถโคลนผู้ให้บริการการจับภาพราสเตอร์ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>การจับภาพราสเตอร์ต้องใช้ขอบเขตที่จำกัดและไม่ว่างเปล่า</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>การจับภาพราสเตอร์ต้องใช้ขีดจำกัดพิกเซลที่เป็นบวก</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>การจับภาพราสเตอร์ต้องใช้ความละเอียดที่เป็นบวก</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <source>raster capture source could not be opened</source>
        <translation>ไม่สามารถเปิดต้นทางการจับภาพราสเตอร์ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>การสร้างราสเตอร์จริงต้องทำงานในเวิร์กเกอร์เธรด</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="208"/>
        <source>raster selection canceled</source>
        <translation>ยกเลิกการเลือกราสเตอร์แล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="216"/>
        <source>raster selection source could not be opened</source>
        <translation>ไม่สามารถเปิดต้นทางการเลือกราสเตอร์ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="204"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>การเลือกราสเตอร์ระยะไกลต้องทำงานในเวิร์กเกอร์เธรด</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="210"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>การเลือกสีที่แสดงผลต้องใช้การจับภาพที่แสดงผลในเครื่อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>ราสเตอร์ที่แสดงผลต้องใช้การจับภาพสีที่แสดงผล</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: สถิติราสเตอร์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>การสุ่มตัวอย่างราสเตอร์ล้มเหลว ลองอีกครั้งด้วยขอบเขตที่มองเห็นที่เล็กลง</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: ตัวอย่างราสเตอร์</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="459"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>เป้าหมายราสเตอร์ระยะไกลต้องทำงานในเวิร์กเกอร์เธรด</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="470"/>
        <source>local raster target could not be opened</source>
        <translation>ไม่สามารถเปิดเป้าหมายราสเตอร์ในเครื่องได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="480"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>เลเยอร์สีที่แสดงผลไม่สามารถเป็นเป้าหมายของตัวกรองได้</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>ใช้การปรับปรุงหรือไม่?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>การปรับปรุงที่พร้อมใช้งาน</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>ข้าม</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>ใช้ที่เลือก</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} u2022 {1} ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>ผลกระทบ: {0}</translation>
    </message>
</context>
<context>
    <name>RemoteMaterializer</name>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1000"/>
        <source>Partial result: the remote feature limit was reached.</source>
        <translation>ผลลัพธ์บางส่วน: ถึงขีดจำกัดจำนวนฟีเจอร์ระยะไกลแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>ผลลัพธ์บางส่วน: ถึงขีดจำกัดเวลาระยะไกลแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>ยกเลิกการกรองระยะไกลแล้ว ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>จะมีการส่งคีย์มากกว่า 500 รายการไปยังบริการ โปรดจำกัดการเลือกหรือใช้สำเนาในเครื่อง</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>บริการไม่มีคีย์ที่คงที่ โปรดใช้สำเนาในเครื่อง</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>เลือกหรือกรองต้นทางระยะไกลก่อนการกรองเชิงพื้นที่</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>ไม่สามารถพิสูจน์ได้ว่าตัวกรองของบริการสมบูรณ์ โปรดเลือกฟีเจอร์ต้นทางหรือใช้สำเนาในเครื่อง</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>สำเนาต้นทางระยะไกลไม่สมบูรณ์ ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>ผลลัพธ์บางส่วน: ไม่พบฟีเจอร์ที่ตรงกันก่อนถึงขีดจำกัด ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>สำเนาระยะไกลที่ตัดกันไม่สมบูรณ์ ไม่สามารถคำนวณตัวกรอง disjoint ได้อย่างปลอดภัย</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Disjoint ร่วมกับเงื่อนไขอื่นต้องใช้สำเนาในเครื่องของเป้าหมายระยะไกล</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>ไม่สามารถประเมินเพรดิเคตเชิงพื้นที่ระยะไกลได้ ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>ไม่สามารถอ่านหรือกรองสำเนาระยะไกลได้ ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="93"/>
        <source>Remote materialization requires a background task.</source>
        <translation>การสร้างสำเนาระยะไกลต้องใช้งานเบื้องหลัง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="566"/>
        <source>Filtering a bounded remote copy</source>
        <translation>กำลังกรองสำเนาระยะไกลแบบจำกัด</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: สแนปช็อตสีที่แสดงผล</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>สแนปช็อตที่แสดงผลล้มเหลว ลองอีกครั้งด้วยขอบเขตที่มองเห็นที่เล็กลง</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>ค้นหาการกำหนดค่า... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>ไม่ตรงกัน</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="242"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>งาน FilterMate ยังคงอ่านเลเยอร์อยู่ โปรดลองอีกครั้งหลังจากเสร็จสิ้น</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="255"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>เลเยอร์ที่มีที่เก็บข้อมูลเสริมไม่สามารถแทนที่ผู้ให้บริการเซิร์ฟเวอร์ได้อย่างปลอดภัย ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="260"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>ไม่สามารถสร้างการเชื่อมโยงระยะไกลใหม่บนเธรดหลักได้ ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="262"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>กำลังเตรียมตัวกรองเซิร์ฟเวอร์สำหรับเลเยอร์นี้อยู่แล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="250"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>เลเยอร์เซิร์ฟเวอร์แก้ไขได้เฉพาะบนเธรดที่เป็นเจ้าของเท่านั้น</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="235"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>ตัวกรองเซิร์ฟเวอร์แบบอะซิงโครนัสต้องใช้ QGIS 3.32 ขึ้นไป ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="368"/>
        <source>Could not install the prepared server filter.</source>
        <translation>ไม่สามารถติดตั้งตัวกรองเซิร์ฟเวอร์ที่เตรียมไว้ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="44"/>
        <source>Could not preserve the layer state.</source>
        <translation>ไม่สามารถรักษาสถานะของเลเยอร์ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="239"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>แก้ไขเลเยอร์ให้เสร็จก่อนใช้ตัวกรองเซิร์ฟเวอร์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>นิพจน์แอตทริบิวต์ไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="83"/>
        <source>Preparing server attribute filter</source>
        <translation>กำลังเตรียมตัวกรองแอตทริบิวต์เซิร์ฟเวอร์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>QGIS ไม่สามารถแปลงเพรดิเคตนี้เป็นตัวกรอง OGC ได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="302"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="311"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>ตัวกรองเซิร์ฟเวอร์ถูกยกเลิกหรือหมดเวลา ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="348"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>การติดตั้งตัวกรองเซิร์ฟเวอร์ล้มเหลวและไม่สามารถคืนค่าผู้ให้บริการก่อนหน้าได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="340"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>การติดตั้งตัวกรองเซิร์ฟเวอร์ล้มเหลว ผู้ให้บริการก่อนหน้าไม่ถูกต้องอยู่แล้วและไม่สามารถคืนค่าได้</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="355"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>การติดตั้งตัวกรองเซิร์ฟเวอร์ล้มเหลว คืนค่าผู้ให้บริการก่อนหน้าแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="33"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>กำลังติดตั้งตัวกรองเซิร์ฟเวอร์ โปรดลองอีกครั้งหลังจากเสร็จสิ้น</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="207"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="237"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>การติดตั้งตัวกรองเซิร์ฟเวอร์ต้องเริ่มบนเธรดของเลเยอร์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>นิพจน์ซับซ้อนเกินกว่าจะแปลงได้อย่างปลอดภัย</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>นิพจน์ใหญ่เกินไปหรือมีการ escape ด้วยแบ็กสแลช SQL ที่กำกวม</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="318"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>เลเยอร์เปลี่ยนแปลงระหว่างเตรียมตัวกรอง ผลลัพธ์ที่เตรียมไว้ถูกทิ้ง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="366"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>เลเยอร์ไม่พร้อมใช้งานอีกต่อไป ตัวกรองที่เตรียมไว้ถูกทิ้ง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="311"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>เซิร์ฟเวอร์ปฏิเสธตัวกรองหรือไม่สามารถเข้าถึงได้ ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="253"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>ผู้ให้บริการนี้และ QGIS เวอร์ชันนี้ไม่รองรับการสร้างเวิร์กเกอร์ที่ผ่านการตรวจสอบ ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: ตัวกรองแอตทริบิวต์ไม่สามารถทำงานบนเซิร์ฟเวอร์ได้ทั้งหมด ส่วนที่ไม่รองรับ: {1} {2} ตัวกรองก่อนหน้าไม่เปลี่ยนแปลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="265"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: ผู้ให้บริการปฏิเสธตัวกรองแอตทริบิวต์ คืนค่าตัวกรองก่อนหน้าแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="264"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: ผู้ให้บริการปฏิเสธตัวกรองและการคืนค่าล้มเหลว</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — รายการโปรดที่แบ่งปัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;รายการโปรดที่แบ่งปัน&lt;/b&gt; — พบจากคอลเลกชัน QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">ค้นหาตามชื่อ คำอธิบาย คอลเลกชัน หรือแท็ก…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>เลือกรายการโปรดที่แบ่งปันเพื่อดูตัวอย่าง</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>สแกนอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>Fork ไปยังโปรเจกต์ของฉัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>ปิด</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>ไม่พบคอลเลกชันที่แบ่งปัน ติดตามที่เก็บ Resource Sharing ที่มีโฟลเดอร์ &lt;code&gt;filter_mate/favorites&lt;/code&gt; หรือวางบันเดิล &lt;code&gt;.fmfav.json&lt;/code&gt; ในไดเรกทอรีคอลเลกชัน resource_sharing ของคุณ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} รายการโปรดใน {1} คอลเลกชัน: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>คอลเลกชัน: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">ไม่มีรายการโปรดที่แบ่งปันตรงกับการค้นหา</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — จาก &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;นิพจน์&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;ชั้นข้อมูลระยะไกล&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;แท็ก:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;แหล่งที่มา&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>ผู้เขียน: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>ใบอนุญาต: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>Fork รายการโปรดที่แบ่งปัน</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>ชื่อในโปรเจกต์ของคุณ:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>Fork สำเร็จ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» ถูกเพิ่มในรายการโปรดของคุณ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>Fork ล้มเหลว</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>ไม่สามารถเพิ่มรายการโปรดที่แบ่งปันไปยังโปรเจกต์ของคุณ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>ค้นหาตามชื่อ คำอธิบาย คอลเลกชัน ผู้เขียน หรือแท็ก...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>ผู้เขียน:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>ผู้เขียนทั้งหมด</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>ไม่มีรายการโปรดที่แชร์ตรงกับตัวกรองของคุณ</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>รีเซ็ตเป็นค่าเริ่มต้น</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>ข้อผิดพลาดการตรวจสอบ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>กรุณาแก้ไขข้อผิดพลาดต่อไปนี้:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>รีเซ็ตการกำหนดค่า</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>รีเซ็ตค่าทั้งหมดเป็นค่าเริ่มต้นหรือไม่?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - คำเตือนประเภท PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>ประเภทไม่ตรงกันในตัวกรอง: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>รีเซ็ตเป็นค่าเริ่มต้น</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>ทั่วไป</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>ไม่สามารถใช้ตัวกรองของ {0} ได้ ยังคงใช้ตัวกรองก่อนหน้า</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} ฟีเจอร์ที่มองเห็นในเลเยอร์หลัก</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>ล้างตัวกรองทั้งหมดแล้ว - {count} ฟีเจอร์ที่มองเห็นในเลเยอร์หลัก</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>ใช้ตัวกรองกับ '{layer_name}': {count} ฟีเจอร์</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>ล้างตัวกรองสำหรับ '{layer_name}': {count} ฟีเจอร์ที่มองเห็น</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="936"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>ไม่ได้เลือกเอนทิตี! วิดเจ็ตการเลือกสูญเสียฟีเจอร์ เลือกเอนทิตีอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1054"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>เลเยอร์ที่เลือกไม่ถูกต้องหรือไม่พบแหล่งข้อมูล ยกเลิกการดำเนินการแล้ว</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1069"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>เลเยอร์ '{0}' ยังไม่ได้เริ่มต้น ลองเลือกเลเยอร์อื่นแล้วสลับกลับมา</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>ไม่สามารถเลิกทำ: เลเยอร์ไม่ถูกต้องหรือไม่พบแหล่งข้อมูล</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>ไม่สามารถทำซ้ำ: เลเยอร์ไม่ถูกต้องหรือไม่พบแหล่งข้อมูล</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>ผู้ให้บริการปฏิเสธตัวกรองที่บันทึกไว้</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>ไม่สามารถคืนค่าตัวกรอง: {0}</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="572"/>
        <source>Explore ...</source>
        <translation>สำรวจ ...</translation>
    </message>
</context>
<context>
    <name>VectorTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="261"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: ไม่มีฟิลด์คีย์ที่ไม่ซ้ำกัน จึงไม่สามารถแสดงรายการฟีเจอร์ในตัวกรองได้ (เว็บเซอร์วิส หรือเลเยอร์เสมือนที่ไม่มีคอลัมน์ id ที่ไม่ซ้ำกัน)</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="362"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>มีฟีเจอร์ที่ต้องแสดงรายการ {0} รายการ มากกว่า {1} รายการที่ส่งไปยังเว็บเซอร์วิสได้: โปรดจำกัดต้นทางหรือใช้ตัวกรองแอตทริบิวต์</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>ไม่มีค่าความครอบคลุมขั้นต่ำสำหรับวัตถุไทล์ที่ถูกตัด</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>เป้าหมายเวกเตอร์ไทล์รองรับเฉพาะ Intersect และ Disjoint</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>การกรองเวกเตอร์ไทล์ต้องมีรหัสผู้ให้อำนาจ CRS</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>ตัวกรองการแสดงผลเวกเตอร์ไทล์: แอตทริบิวต์ขึ้นอยู่กับระดับการซูม วัตถุที่ถูกแบ่งข้ามไทล์อาจต่างกัน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>สไตล์เวกเตอร์ไทล์เปลี่ยนแปลงขณะตัวกรองกำลังทำงาน โปรดลองอีกครั้ง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>กรองแอตทริบิวต์เวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>นิพจน์ตัวกรองเวกเตอร์ไทล์ไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>นิพจน์ QGIS (แอตทริบิวต์ขึ้นอยู่กับระดับการซูม):</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>ทำซ้ำตัวกรองเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>เฉพาะเป้าหมาย แอตทริบิวต์ขึ้นอยู่กับระดับการซูม วัตถุที่ถูกแบ่งข้ามไทล์อาจถูกกรองต่างกัน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>สไตล์เวกเตอร์ไทล์ที่บันทึกไว้ไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>คุณสมบัติสัญลักษณ์เวกเตอร์ไทล์ที่บันทึกไว้ไม่ถูกต้อง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>การเลือกไทล์เกินงบประมาณนิพจน์ (1 MB) โปรดใช้พื้นที่ที่เล็กลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>การเลือกไทล์เกินงบประมาณจุดยอด (2000) โปรดใช้พื้นที่ที่เล็กลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>ตัวกรองเวกเตอร์ไทล์เกินงบประมาณนิพจน์ (1 MB)</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>ตัวกรองเวกเตอร์ไทล์เกินงบประมาณนิพจน์สไตล์รวม (1 MB) โปรดใช้พื้นที่ที่เล็กลง</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>เลิกทำตัวกรองเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>ยกเลิกการกรองเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>ตัวกรองแอตทริบิวต์เวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="111"/>
        <source>Vector tile favorite</source>
        <translation>รายการโปรดเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>ตัวกรองเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>การกรองเวกเตอร์ไทล์ต้องใช้ตัวแสดงผลพื้นฐาน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>การกรองเวกเตอร์ไทล์ต้องใช้การติดป้ายกำกับพื้นฐาน</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>ตัวกรองเวกเตอร์ไทล์</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>เวกเตอร์ไทล์</translation>
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
        <translation>เรขาคณิตต้นทาง: ฟีเจอร์ที่เลือกใน EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">เรขาคณิตต้นทาง: พิกเซลที่เลือก แปลงเป็นเวกเตอร์</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">จุดที่เก็บไว้</translation>
    </message>
</context>
</TS>
