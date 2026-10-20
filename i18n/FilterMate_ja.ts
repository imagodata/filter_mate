<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ja_JP" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>Resource Sharing からインポート...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Resource Sharing に公開...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>公開（お気に入りが保存されていません）</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>既定のリポジトリにクイック公開</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>Resource Sharing リポジトリを管理...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>{0}個のレイヤーから破損したフィルターを削除しました。フィルターを再適用してください。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>空のプロジェクトが検出されました。プラグインを有効にするにはベクターレイヤーを追加してください。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>FilterMateデータベースにアクセスできません。プロジェクトディレクトリの権限を確認してください。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>データベース検証中のエラー: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>レイヤーの読み込みに失敗しました。F5で強制再読み込みしてください。</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: このウェブサービスには一意のキーフィールド（宣言されたキー、id、gml_id、cleabs、objectid など）がないため、選択した地物をサーバー向けに列挙できません。</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: このレイヤーには一意のキーフィールドがなく、フィルタ内でフィーチャ ID を列挙できません（仮想レイヤーには一意の ID 列、uid が必要です）。</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: 選択した地物 {1} 件は、ウェブサービスに送信できる上限の {2} 件を超えています。選択を絞り込むか、属性フィルタを使用してください。</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>リモートファイル: 読み取りはすべてネットワーク経由で行われます。FilterMate はメインスレッドで地物数を数えません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>リモートサービス: サーバーが変換できる場合、フィルタはサーバーに送信されます。FilterMate はメインスレッドで地物数を数えません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>地物リストによるフィルタは {0} 件までに制限されています。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="123"/>
        <source>Remote</source>
        <translation>リモート</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="185"/>
        <source>Select Backend:</source>
        <translation>バックエンドを選択:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>自動 (デフォルト)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>すべてのレイヤーに最適値を自動選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>すべてのレイヤーに{0}を強制適用</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>クリックしてレイヤーを再読み込み</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>クリックしてバックエンドを変更</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>チェックしたライン/ポリゴン対象を重心 (面上の点) でテスト: 大きなジオメトリで高速です。各対象にはリスト内に専用の四角があります</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>重心はライン/ポリゴン対象に適用されます: フィルタするレイヤのリストで1つチェックしてください</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>変更キャンセルエラー: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>プロパティエラー: {0}</translation>
    </message>
</context>
<context>
    <name>CoverageDockExtras</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="303"/>
        <source>1 band</source>
        <translation>1 バンド</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="304"/>
        <source>{0} bands</source>
        <translation>{0} バンド</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="305"/>
        <source>{0} points</source>
        <translation>{0} ポイント</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>ソースジオメトリ: 選択したピクセル (ベクタ化)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="792"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>ソースジオメトリ: 保持したポイントの範囲</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="739"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation>ソースジオメトリ: EXPLORING で選択した地物</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">カーソル位置の値: 地図上を移動しながら現在のバンドのピクセル値を表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">矩形の統計: 地図上でドラッグして現在のバンドの最小値・最大値・平均値を表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>標高プロファイル: QGIS の標高プロファイルを開く</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>3D ビュー: 新しい QGIS 3D マップビューを開く</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">地物なし</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} 件の地物</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">すべてのピクセル</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} クラス</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>式</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} 件の地物</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Vector</source>
        <translation>ベクタ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Raster</source>
        <translation>ラスタ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Point cloud</source>
        <translation>ポイントクラウド</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="795"/>
        <source>Kept points</source>
        <translation>保持したポイント</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Selection → source geometry</source>
        <translation>選択 → ソースジオメトリ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>範囲をスタイルに連動: レイヤの色を選択した範囲に引き伸ばします</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>クラススポイト: 地図をクリックすると、そこに描画されているポイントのクラスにチェックが入ります。Ctrl+クリックで別のクラスを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>カーソル位置の値: 地図上を移動しながらピクセル値（または範囲を適用している傾斜、傾斜方向など）を表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>矩形の統計: 地図上でドラッグして、現在のバンド（または範囲を適用している傾斜、傾斜方向など）の最小値・最大値・平均値を表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>スタイル連動はピクセル値に追従します: 範囲を傾斜、傾斜方向、陰影起伏、粗度に適用している間は使用できません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="920"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>クラススポイト: このポイントクラウドには Classification 属性がありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1526"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>スタイルを範囲に追従させることができません: パネルのバンドに対する単一バンドのグレーまたは疑似カラースタイルが必要です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>スポイト: 地図をクリックすると、クリックしたピクセルに似たピクセルが選択されます（画像では色、DTM や指数では値、分類ラスタではクラス。パネルの許容差が適用されます）。Ctrl+クリックで別のものを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>地物が選択されていません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>レイヤ全体</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>制約なし</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>ラスタ式</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>すべてのポイント</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} 個のオブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>枠内では分類全体として表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>オブジェクト検出: 地図をクリックすると、クリックしたピクセルに似たピクセルのまとまり（プール、屋根、畑など。パネルの許容差が適用されます）が選択されます。同じ色のピクセルすべてではありません。Ctrl+クリックで別のオブジェクトを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>類似オブジェクト: オブジェクトをクリックすると、ラスタ内でそれに似たすべてのオブジェクト（面積がパネルの比率の範囲内にあるピクセルのまとまり）が選択されます。Ctrl+クリックで別の基準オブジェクトを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>オブジェクト検出: 地図をクリックすると、クリック位置のオブジェクト（その分類のポイントのまとまり。建物や樹木など）が選択されます（分類全体ではありません）。右クリックで対象を切り替えると、ポイントクラウド内の同様のオブジェクトすべてを選択できます。Ctrl+クリックで別のオブジェクトを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>値スポイト: 地図をクリックすると、「属性」で選択した属性（Z、強度など）に対して、その位置のポイントの値を中心に、パネルの許容差で条件が書き込まれます。Ctrl+クリックで別の条件を追加します (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>ゾーン: 地図上に矩形、ポリゴン、フリーハンド図形、または円を描きます（形状はボタンを右クリックで選択）。その X / Y の範囲は「属性」に入り、図形そのものが対象を切り取ります</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>その他のツール: カーソル位置の値、矩形の統計</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>類似地物: 地物をクリックすると、グループのフィールド（単一 / 複数選択の表示式）が同じ値を持つレイヤー内のすべての地物が選択されます。Ctrl+クリックで別の値を追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>その他のツール: QGIS の選択ツール（矩形、ポリゴン、フリーハンド、半径）、式による選択、選択の反転または解除、選択の属性テーブル</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>その他のツール: QGIS の標高プロファイルと 3D ビュー</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>色による選択のみ使用できます: 描画される色はスタイルと縮尺に依存します。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>スタイルのリンクは「値の範囲」グループに連動します: 先にそれをアクティブにしてください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="794"/>
        <source>Current filter: {0}</source>
        <translation>現在のフィルタ: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="830"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>描画される色はスタイルと縮尺に依存します。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="929"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>オブジェクト検出: このポイントクラウドには Classification 属性がありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="978"/>
        <source>Object detector</source>
        <translation>オブジェクト検出</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Clicked object</source>
        <translation>クリックしたオブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Similar objects</source>
        <translation>類似オブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1085"/>
        <source>Zone shape</source>
        <translation>ゾーンの形状</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Rectangle</source>
        <translation>矩形</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Polygon</source>
        <translation>ポリゴン</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Freehand</source>
        <translation>フリーハンド</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Radius</source>
        <translation>半径</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1134"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>リンクは単一選択と複数選択に連動します: 先にどちらかをアクティブなグループにしてください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1257"/>
        <source>Select on the map</source>
        <translation>地図上で選択</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Select by expression…</source>
        <translation>式で選択…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Invert the selection</source>
        <translation>選択を反転</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Clear the selection</source>
        <translation>選択を解除</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1272"/>
        <source>Attribute table of the selection</source>
        <translation>選択の属性テーブル</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Value under the cursor</source>
        <translation>カーソル位置の値</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1315"/>
        <source>Statistics of a rectangle</source>
        <translation>矩形の統計</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>Elevation profile</source>
        <translation>標高プロファイル</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>3D view</source>
        <translation>3D ビュー</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1688"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>このポイントクラウドには、フィルタに使える X / Y 属性がありません</translation>
    </message>
</context>
<context>
    <name>CoverageModeController</name>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="365"/>
        <source>Restoring the filter of {0} raster / point cloud layer(s)…</source>
        <translation>{0} 個のラスタ / ポイントクラウドレイヤのフィルタを復元しています…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>被覆率 ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>ソースジオメトリ内に含まれる対象ポリゴンの最小割合（0 = 重なりがあれば可）。ソースがラスタまたはポイントクラウドの場合に使用されます。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>ラスタ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>ポイントクラウド</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>{0} レイヤ: EXPLORING で選択、FILTERING でリレーション</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">ピクセルピッカー: 地図をクリックすると全バンドの値を読み取ります（Ctrl+クリックで範囲を拡張）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>レイヤにズーム</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">プレビュー: 選択範囲外のピクセルを非表示にする</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>ラスタレイヤでは使用されません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>ラスタの選択をリセット</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">地図上のポイントを識別</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>ライブプレビュー: 選択で残るポイントのみを表示</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>ポイントクラウドレイヤでは使用されません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>ポイントクラウドの条件をリセット</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>ラスタ計算式が無効です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>PDAL が見つかりません: DTM からの高さの計算には pdal 実行ファイルが必要です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3151"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>FilterMate のタスクがまだ実行中です。完了するまでお待ちください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>FilterMate のタスクが失敗しました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>先にピクセルを選択してください: 値の範囲、クラス、またはラスタ式</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>ラスタをフィルタしました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>ポイントクラウドの式が拒否されました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>先にポイントを選択してください: クラス、属性の範囲、または式</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>ポイントクラウドをフィルタしました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3261"/>
        <source>Filter not applied: {0}</source>
        <translation>フィルタは適用されませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>canceled</source>
        <translation>キャンセルされました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>{0} 件の対象をフィルタしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2823"/>
        <source>{0} failed: {1}</source>
        <translation>{0} が失敗しました: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2836"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: '{0}' からフィルタしています…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2933"/>
        <source>Changed since, left as is: {0}</source>
        <translation>その後に変更されたため、そのままにしました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2939"/>
        <source>{0} layer(s) restored</source>
        <translation>{0} 個のレイヤを復元しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2973"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>'{0}' はエクスポートされませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2987"/>
        <source>Exported: {0}</source>
        <translation>エクスポートしました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2989"/>
        <source>Export failed: {0}</source>
        <translation>エクスポートに失敗しました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2996"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>{0} 個のレイヤをエクスポートしています…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3002"/>
        <source>Export folder</source>
        <translation>エクスポート先フォルダ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3084"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>ラスタ / ポイントクラウドの対象をスキップしました: EXPLORING でソースフィーチャが選択されていません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>ラスタ / ポイントクラウドの対象はフィルタされませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3115"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>{0} 件のラスタ / ポイントクラウドの対象をフィルタしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3238"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>地上高の算出に使用する DTM ラスタを選択してください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3249"/>
        <source>Height above ground not computed: {0}</source>
        <translation>地上高は計算されませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3270"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>PDAL で '{0}' からの高さを計算しています…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>FilterMate のキャッシュが {0} GB を使用しており、上限の {1} GB を超えています: 不要になったラスタ / ポイントクラウドレイヤのフィルタを解除してください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>PDAL {0} は古すぎます: DTM からの高さの計算には PDAL 2.4 以降が必要です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>PDAL を実行できませんでした。DTM からの高さは利用できません: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">ピクセルピッカー: 地図をクリックすると全バンドの値を読み取ります。範囲が傾斜や傾斜方向などに適用されている場合はその値も読み取ります（Ctrl+クリックで範囲を拡張）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>選択したピクセルにズーム（選択がない場合はレイヤにズーム）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>プレビュー: 選択範囲外のピクセルを非表示にする（傾斜、傾斜方向などでは白いベール）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>傾斜や傾斜方向のプレビューには、ラスタの CRS（{0}）の地図が必要です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>地図上に描画されているポイントのみ選択できます: プレビューで隠れているクラスを選択するにはプレビューをオフにしてください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>クリック位置に分類されたポイントがありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>クラス {0} はすでにチェックされています</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>クラス {0} はレイヤのクラス一覧にありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>ラスタレイヤーでは使用されません: スポイトはバンドを読み取ります</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>クラススポイト: 地図をクリックすると、そこに描画されているポイントのクラスにチェックが入ります。Ctrl+クリックで別のクラスを追加します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>プレビューと統計には、表示範囲の限定的なローカルサンプルが使用されます。フィルタはソースを読み取ります。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>表示範囲の限定的な色スナップショットを準備しています…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>色スナップショットを準備できませんでした。表示範囲を小さくしてください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>色による選択は、取得した表示範囲に適用されます。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>ラスタのサンプリングに失敗しました。表示範囲を小さくしてください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>サンプリングしたラスタのプレビューを計算できませんでした。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>色または式のプレビューには、ラスタの CRS ({0}) の地図が必要です</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>クリック位置に描画されたポイントがありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>このポイントには {0} がありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>{0} は条件に使用できません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>オブジェクトを読み取れませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>クリック位置の周囲にポイントが多すぎます: オブジェクトを読み取れませんでした</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>クリック位置に分類 {0} のポイントがありません: オブジェクト自体をクリックしてください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>類似オブジェクトを読み取れませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>面積比の範囲内に類似オブジェクトがありません: 範囲を広げてください</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>新しい表示範囲のサンプルを準備しています。準備ができたら、もう一度クリックしてください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>ローカルのラスタサンプルはまだ準備中です。準備ができたら再試行してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>このレンダリング済みレイヤーをフィルタする前に、色スナップショットを準備してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>ラスタ対象 {0} 件を、設定されたピクセル上限にリサンプリングしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2847"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>色による選択は取得した範囲に限定されます。色はスタイルと縮尺に依存します</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2849"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>ラスタソースをピクセル上限内の {0} セルにリサンプリングしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>ラスタ選択を {0} ピクセルごとに読み取りました: 設定のピクセル上限を超えています</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2854"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>密なラスタ選択を、輪郭を軽く保つために平滑化しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2901"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0} は空になりました。選択に一致するものがありません: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2885"/>
        <source>failed</source>
        <translation>失敗</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="234"/>
        <source>Database file does not exist: {0}</source>
        <translation>データベースファイルが存在しません: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>データベース{0}への接続に失敗: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>データベースディレクトリ{0}を作成できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>データベースファイル{0}の作成に失敗: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>FilterMateデータベースを初期化できません: 接続に失敗しました</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>データベース接続の重大エラー: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>データベース初期化中のエラー: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>データベースファイルが存在しません: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>データベース {db_file_path} への接続に失敗しました: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>空間インデックスを作成するための QGIS Processing モジュールが利用できません</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>空間インデックスを作成できません: レイヤが無効、またはソースが見つかりません。</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>PostgreSQL レイヤが検出されましたが psycopg2 がインストールされていません。ローカルの Spatialite バックエンドを使用します。大規模データセットのパフォーマンスを向上させるには psycopg2 をインストールしてください。</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2481"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>選択した地物 {0} 件は、ウェブサービスに送信できる上限の {1} 件を超えています: 選択を絞り込むか、属性フィルタを使用してください。</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>レイヤーをファイルに保存</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>レイヤーをエクスポートするフォルダーを選択</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>エクスポートデータをzipファイルに保存</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0}個のレイヤー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> {0}個のグループ内</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} グループ外</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>出力先 : {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>グループが検出されません - すべてのレイヤーがルートレベルにあります</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="154"/>
        <source>Annuler</source>
        <translation>キャンセル</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="160"/>
        <source>Exporter</source>
        <translation>エクスポーター</translation>
    </message>
</context>
<context>
    <name>ExtensionRegistry</name>
    <message>
        <location filename="../extensions/registry.py" line="398"/>
        <source>install the QGIS plugin {0}</source>
        <translation>QGIS プラグイン {0} をインストールしてください</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>{0} をインストールしてください</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>{1} がないため拡張機能 {0} はオフです: {2}。その後 QGIS を再起動してください。</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">フィルターなし</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>保存するアクティブなフィルターがありません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>お気に入りを追加</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>お気に入り名:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>お気に入り'{0}'が正常に追加されました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="511"/>
        <source>Export Favorites</source>
        <translation>お気に入りをエクスポート</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="535"/>
        <source>Exported {0} favorites</source>
        <translation>{0}個のお気に入りをエクスポートしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="537"/>
        <source>Failed to export favorites</source>
        <translation>お気に入りのエクスポートに失敗</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Import Favorites</source>
        <translation>お気に入りをインポート</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>既存のお気に入りとマージしますか?

はい = 既存に追加
いいえ = すべて置換</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>{0}個のお気に入りをインポートしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>インポートされたお気に入りはありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>お気に入りマネージャーが初期化されていません。FilterMateを再起動してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>お気に入りマネージャーダイアログが利用できません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>エラー: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">{0}回使用</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">現在のフィルターをお気に入りに追加</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">フィルターを追加 (アクティブなフィルターなし)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">お気に入りを管理...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation type="obsolete">エクスポート...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation type="obsolete">インポート...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation type="obsolete">グローバルお気に入り</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">グローバルにコピー...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── 利用可能なグローバルお気に入り ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(グローバルお気に入りなし)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">メンテナンス</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">プロジェクトに保存 (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">プロジェクトから復元</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">孤立プロジェクトのクリーンアップ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">データベース統計</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">無効な名前</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>お気に入り名は空にできません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>名前の重複</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>'{0}'という名前のお気に入りが既に存在します。
置き換えますか?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>お気に入りがグローバルお気に入りにコピーされました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>グローバルお気に入りへのコピーに失敗</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">グローバルお気に入り</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0}個のグローバルお気に入りが利用可能です。

グローバルお気に入りはすべてのプロジェクトで共有されます。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>プロジェクトファイルに{0}個のお気に入りを保存しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>保存に失敗</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>プロジェクトファイルから{0}個のお気に入りを復元しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>プロジェクトに復元するお気に入りが見つかりません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0}個の孤立プロジェクトをクリーンアップしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>クリーンアップする孤立プロジェクトはありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>FilterMateデータベース統計

お気に入り合計: {0}
   プロジェクト: {1}
   孤立: {2}
   グローバル: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>お気に入り数による上位プロジェクト:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>FilterMate統計</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">お気に入りマネージャー</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">まだお気に入りが保存されていません。

レイヤにフィルタを適用し、★ インジケータをクリックして「現在のフィルタをお気に入りに追加」を選択すると、最初のお気に入りが保存されます。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">Resource Sharing からインポート…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">Resource Sharing に公開…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">公開(保存されたお気に入りなし)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>FilterMate 設定ディレクトリはまだ初期化されていません — 最初に FilterMate を有効にした QGIS プロジェクトを開いてください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">Resource Sharing 拡張機能が有効になっていません。FilterMate 設定で 'favorites_sharing' を有効にしてください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">共有お気に入りサービスが利用できません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">共有お気に入り選択に失敗しました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">公開できるお気に入りがまだありません。先に ★ メニューからフィルタを保存してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">公開ダイアログの起動に失敗しました: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>お気に入りの準備がまだできていません: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>'{0}' を削除できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>保存されたお気に入りはまだありません。フィルタを適用し、★ インジケータをクリックして最初のお気に入りを保存してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>お気に入りマネージャを開けませんでした。詳細は filtermate.log を参照してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>'{0}' を置換できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>'{0}' を保存できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>グローバルお気に入りをインポートできませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>グローバルにコピーできませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>お気に入りをプロジェクトファイルに保存できませんでした: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>孤立したプロジェクトをクリーンアップできませんでした。詳細は filtermate.log を参照してください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>データベースの統計情報を利用できません。詳細は filtermate.log を参照してください。</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="204"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - お気に入りマネージャー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1165"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;保存済みお気に入り ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="266"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>名前、式、タグ、または説明で検索...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>一般</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>式</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>リモート</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>お気に入り名</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>名前:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>説明 (自動生成、編集可能)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>説明:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>タグをカンマで区切って入力 (例: 都市, 人口, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>タグはお気に入りの整理と検索に役立ちます。
複数のタグはカンマで区切ってください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>タグ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>ソースレイヤー:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>プロバイダー:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>使用日:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>作成日:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;ソースレイヤー式:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>ソースレイヤーのフィルター式</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;フィルター済みリモートレイヤー:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>レイヤー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>地物</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;このお気に入りにリモートレイヤーはありません&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>適用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>このお気に入りフィルターをプロジェクトに適用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>変更を保存</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>このお気に入りの変更を保存</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="733"/>
        <source>Delete</source>
        <translation>削除</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="736"/>
        <source>Permanently delete this favorite</source>
        <translation>このお気に入りを完全に削除</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="739"/>
        <source>Close</source>
        <translation>閉じる</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>このダイアログを閉じる</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="849"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;お気に入り ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1015"/>
        <source>Remote ({0})</source>
        <translation>リモート ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete Favorite</source>
        <translation>お気に入りを削除</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>お気に入り'{0}'を削除しますか?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>リモートレイヤー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1303"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;保存済みお気に入り (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">お気に入りマネージャー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>No favorites saved yet.

Click the ★ indicator and select 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">お気に入りはまだ保存されていません。

★インジケーターをクリックし、「現在のフィルターをお気に入りに追加」を選択して最初のお気に入りを保存してください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>共有…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>QGIS Resource Sharing コレクション経由で共有されたお気に入りを参照</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>公開…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>選択したお気に入りを Resource Sharing コレクションに公開</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">「{0}」を削除できませんでした。お気に入りはデータベースに残っています — 詳細は FilterMate ログを確認してください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>範囲(所有者 × プロジェクト)でお気に入りをフィルタ。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>すべて</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>共有 · すべてのプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>共有 · このプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>自分 · すべてのプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>自分 · このプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>自分</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>共有</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>このプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>すべてのプロジェクト</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>プロジェクト範囲はお気に入り作成時に設定されます。プロジェクトを切り替えるには、フィルタリング タブ(近日公開)から移動してください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>可視性:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (全員と共有)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (あなた)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — 保存時に '自分' を選択すると所有権があなたに移ります</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>'{0}' を保存できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>'{0}' を削除できませんでした: {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>'{0}' はデータベースにありませんでした。更新してからもう一度お試しください。</translation>
    </message>
</context>
<context>
    <name>FeedbackModule</name>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="112"/>
        <source>Exporting {0} layer(s)</source>
        <translation>{0} 個のレイヤーをエクスポート中</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="168"/>
        <source>Large dataset ({0} features) using {1}. Consider using PostgreSQL for optimal performance.</source>
        <translation>大規模データセット ({0} 件の地物) で {1} を使用しています。最適なパフォーマンスを得るには PostgreSQL の使用を検討してください。</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="176"/>
        <source>Medium-large dataset ({0} features) using {1}. PostgreSQL recommended for better performance.</source>
        <translation>中～大規模データセット ({0} 件の地物) で {1} を使用しています。パフォーマンス向上のため PostgreSQL を推奨します。</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="113"/>
        <source>Processing {0} layer(s)</source>
        <translation>{0} 個のレイヤーを処理中</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="110"/>
        <source>Removing filters from {0} layer(s)</source>
        <translation>{0} 個のレイヤーのフィルタを解除中</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="111"/>
        <source>Resetting {0} layer(s)</source>
        <translation>{0} 個のレイヤーをリセット中</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="109"/>
        <source>Starting filter on {0} layer(s)</source>
        <translation>{0} 個のレイヤーのフィルタを開始</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="137"/>
        <source>Successfully exported {0} layer(s)</source>
        <translation>{0} 個のレイヤーを正常にエクスポートしました</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="134"/>
        <source>Successfully filtered {0} layer(s)</source>
        <translation>{0} 個のレイヤーを正常にフィルタしました</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="138"/>
        <source>Successfully processed {0} layer(s)</source>
        <translation>{0} 個のレイヤーを正常に処理しました</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="135"/>
        <source>Successfully removed filters from {0} layer(s)</source>
        <translation>{0} 個のレイヤーのフィルタを正常に解除しました</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="136"/>
        <source>Successfully reset {0} layer(s)</source>
        <translation>{0} 個のレイヤーを正常にリセットしました</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="604"/>
        <source>View</source>
        <translation>ビュー</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="606"/>
        <source>Change</source>
        <translation>変更</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>フォルダーを選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>ファイルを選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>ファイルに保存</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="664"/>
        <source>View</source>
        <translation>ビュー</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="666"/>
        <source>Change</source>
        <translation>変更</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>アイコンを選択</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>レイヤーが無効またはソースが見つかりません。操作がキャンセルされました。</translation>
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
        <translation>FilterMateパネルを開く</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>設定とデータベースをリセット</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>デフォルト設定をリセットしSQLiteデータベースを削除</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>設定リセット</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>設定が正常にリセットされました。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>デフォルト設定ファイルが見つかりません。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>データベース削除済み: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>再起動が必要</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>廃止された設定が検出されました</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>不明なバージョン</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>廃止された設定({})が検出されました。

デフォルト設定にリセットしますか?

• はい: リセット (バックアップが作成されます)
• いいえ: 現在の設定を維持 (問題が発生する可能性があります)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>破損した設定が検出されました</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>設定ファイルが破損しており、読み取れません。

デフォルト設定にリセットしますか?

• はい: リセット (可能な場合バックアップが作成されます)
• いいえ: キャンセル (プラグインが正しく動作しない可能性があります)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>設定リセット</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>設定をリセットする必要があります。

続行しますか?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>設定がリセットされませんでした。一部の機能が正しく動作しない可能性があります。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>デフォルト値で設定が作成されました</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>破損した設定がリセットされました。デフォルト設定が復元されました。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>廃止された設定がリセットされました。デフォルト設定が復元されました。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>設定が最新バージョンに更新されました</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>設定更新: 新しい設定が利用可能です ({sections})。オプションメニューからアクセスしてください。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>ジオメトリ簡略化</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>最適化しきい値</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>設定移行中のエラー: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>ジオメトリ検証設定</translation>
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
        <translation>QGIS設定「無効な地物のフィルタリング」が現在'{mode}'に設定されています。

FilterMateは以下の理由からこの設定を無効('Off')にすることを推奨します:

• 無効なジオメトリを持つ地物がエクスポートやフィルターから暗黙的に除外される可能性があります
• FilterMateはジオメトリ検証を自動修復オプション付きで内部的に処理します
• 一部の正当なデータが厳格なOGCルールに従って「無効」と見なされる場合があります

この設定を今すぐ無効にしますか?

• はい: フィルタリングを無効にする (FilterMateに推奨)
• いいえ: 現在の設定を維持</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>無効なジオメトリフィルタリングが正常に無効化されました。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>無効なジオメトリフィルタリングは変更されませんでした。一部の地物がエクスポートから除外される場合があります。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>デフォルト設定にリセットしてよろしいですか?

この操作は:
- デフォルト設定を復元します
- レイヤーデータベースを削除します

変更を適用するにはQGISを再起動する必要があります。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>設定がリセットされました。

変更を適用するにはQGISを再起動してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>初期化エラー: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count}個の参照レイヤーが読み込まれていません ({layers_list})。フォールバック表示を使用します。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>{filename}を削除できません: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">リセット中のエラー: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;FilterMate&lt;/b&gt;をご利用いただきありがとうございます!&lt;br&gt;Discordコミュニティに参加しましょう:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;ヘルプとサポートを受ける&lt;/li&gt;&lt;li&gt;バグや問題を報告する&lt;/li&gt;&lt;li&gt;新機能を提案する&lt;/li&gt;&lt;li&gt;他のユーザーとヒントを共有する&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  Discordに参加する</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>今後表示しない</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>閉じる</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>プラグインの読み込みエラー: {0}。詳細はQGIS Pythonコンソールを確認してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Current layer: {0}</source>
        <translation>現在のレイヤー: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7418"/>
        <source>No layer selected</source>
        <translation>レイヤーが選択されていません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>Selected layers:
{0}</source>
        <translation>選択されたレイヤー:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>No layers selected</source>
        <translation>レイヤーが選択されていません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7448"/>
        <source>No expression defined</source>
        <translation>式が定義されていません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7460"/>
        <source>Display expression: {0}</source>
        <translation>表示式: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7477"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>地物ID: {0}
最初の属性: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>設定をリセットできませんでした。プラグインのフォルダが書き込み可能か確認してから、もう一度お試しください。詳細は filtermate.log を参照してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>FilterMate 5 の新機能</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;FilterMate はラスタレイヤとポイントクラウドレイヤに対応しました。&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; は現在のレイヤに合わせて変わります: ラスタの値の範囲とクラス、LiDAR ポイントクラウドのクラス、標高、属性。&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; はその選択を、いつもの述語とバッファで、あらゆる種類のレイヤに関連付けます: 標高範囲内の区画、建物の下の LiDAR 点、市町村で切り抜いた DTM。&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; はフィルタしたラスタ (GeoTIFF、COG) とポイントクラウド (LAZ、COPC) を書き出します。&lt;/li&gt;&lt;li&gt;Processing のアルゴリズムとモデル、qgis_process、Python および REST API。&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>ユーザーガイドを開く</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="409"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>この式はサービス向けに安全に評価できません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>The service could not be read. Please retry.</source>
        <translation>サービスを読み取れませんでした。再試行してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>Read failed</source>
        <translation>読み取りに失敗しました</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="287"/>
        <source>Loading filtered extent…</source>
        <translation>フィルタ後の範囲を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="404"/>
        <source>The expression is not valid for this layer. Check its syntax and field names.</source>
        <translation>この式はこのレイヤーでは無効です。構文とフィールド名を確認してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="407"/>
        <source>A virtual field of this layer cannot be evaluated safely for a service.</source>
        <translation>このレイヤーの仮想フィールドは、サービス向けに安全に評価できません。</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="319"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>PostgreSQLレイヤーが検出されました ({0})がpsycopg2がインストールされていません。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="419"/>
        <source>Cleared {0} caches</source>
        <translation>{0}個のキャッシュを削除</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="925"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>ドックウィジェットの作成に失敗: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="935"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>ドックウィジェットの表示に失敗: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1501"/>
        <source>Error executing {0}: {1}</source>
        <translation>{0}の実行エラー: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1513"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>プラグインが低下モードで実行中です (ヘキサゴナルサービスが利用不可)。パフォーマンスが低下する可能性があります。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate エラー</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>{0}を実行できません: ウィジェットの初期化に失敗しました。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>{0}できません: レイヤーが無効またはソースが見つかりません。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2792"/>
        <source>All filters cleared - </source>
        <translation>すべてのフィルターを解除 - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2793"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>メインレイヤーに{0}{1}個の地物が表示</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2805"/>
        <source>Error: result handler missing</source>
        <translation>エラー: 結果ハンドラーがありません</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2822"/>
        <source>Error during filtering: {0}</source>
        <translation>フィルタリング中のエラー: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2946"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0}個の孤立お気に入りを回復: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3112"/>
        <source>Layer loading failed - click to retry</source>
        <translation>レイヤーの読み込みに失敗 - クリックして再試行</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3164"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0}個のレイヤーが正常に読み込まれました</translation>
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
        <translation>Cancel</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2150"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1331"/>
        <source>Pick a layer in the EXPLORING tab before running &apos;{0}&apos;.</source>
        <translation>'{0}' を実行する前に、EXPLORING タブでレイヤを選択してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="852"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} 個のレイヤーはフィルターされたままです: {1}。フィルターを解除するにはオプションを再度オンにしてください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2624"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>サーバーフィルタを準備中です。別の操作を開始する前に完了をお待ちください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1773"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>FilterMate API の操作が実行中です。完了するまでお待ちください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="458"/>
        <source>Adding layers</source>
        <translation>レイヤーを追加中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="462"/>
        <source>Existing project loaded</source>
        <translation>既存のプロジェクトを読み込みました</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="455"/>
        <source>Exporting data</source>
        <translation>データをエクスポート中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="452"/>
        <source>Filtering data</source>
        <translation>データをフィルタ中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="461"/>
        <source>New project</source>
        <translation>新規プロジェクト</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="457"/>
        <source>Redo filter</source>
        <translation>フィルタをやり直す</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="463"/>
        <source>Reloading layers</source>
        <translation>レイヤーを再読み込み中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="460"/>
        <source>Removing all layers</source>
        <translation>すべてのレイヤーを削除中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="459"/>
        <source>Removing layers</source>
        <translation>レイヤーを削除中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="454"/>
        <source>Reseting data</source>
        <translation>データをリセット中</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="456"/>
        <source>Undo filter</source>
        <translation>フィルタを元に戻す</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="453"/>
        <source>Unfiltering data</source>
        <translation>データのフィルタを解除中</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>初期化エラー: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>UI設定が不完全です - ログを確認してください</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">UIサイズエラー: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>お気に入りマネージャーが利用できません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0}個のお気に入りが保存済み
クリックして適用または管理</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ お気に入りは保存されていません
クリックして現在のフィルターを追加</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <location filename="../ui/controllers/backend_controller.py" line="822"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>{1}個のレイヤーに{0}バックエンドを強制適用</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>バックエンドコントローラーが利用できません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>PostgreSQL自動クリーンアップ有効</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>PostgreSQL自動クリーンアップ無効</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>PostgreSQLセッションビューがクリーンアップされました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>クリーンアップするビューがないか、クリーンアップに失敗しました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <location filename="../ui/controllers/backend_controller.py" line="1089"/>
        <source>No PostgreSQL connection available</source>
        <translation>利用可能なPostgreSQL接続がありません</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>スキーマに他のセッションからの{0}個のビューがあります。
それでも削除しますか?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>他のセッションがアクティブ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>スキーマのクリーンアップがキャンセルされました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>スキーマ'{0}'が正常に削除されました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <location filename="../ui/controllers/backend_controller.py" line="1090"/>
        <source>Schema cleanup failed</source>
        <translation>スキーマのクリーンアップに失敗しました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQLセッション情報</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>テーマ適用: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>ダークモード</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>ライトモード</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4116"/>
        <location filename="../ui/controllers/exploring_controller.py" line="884"/>
        <source>Selected features have no geometry.</source>
        <translation>選択された地物にジオメトリがありません。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4135"/>
        <location filename="../ui/controllers/exploring_controller.py" line="885"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>地物が選択されていません。ドロップダウンリストから地物を選択してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5319"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>選択されたレイヤーが無効またはソースが見つかりません。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6114"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>負のバッファ (浸食): ポリゴンを内側に縮小</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6117"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>メートル単位のバッファ値 (正=拡大、負=ポリゴン縮小)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6619"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>{0}個のベクターレイヤーでプラグインが有効化されました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6718"/>
        <source>Could not reload plugin automatically.</source>
        <translation>プラグインを自動的に再読み込みできませんでした。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Error reloading plugin: {0}</source>
        <translation>プラグインの再読み込みエラー: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6798"/>
        <source>Layer properties reset to defaults</source>
        <translation>レイヤープロパティがデフォルトにリセットされました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6799"/>
        <source>Error resetting layer properties: {}</source>
        <translation>レイヤープロパティのリセットエラー: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>Filter</source>
        <translation>フィルタ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>最後のフィルタを元に戻す</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>最後のフィルタをやり直す</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>フィルタを解除</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>レイヤをエクスポート</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>FilterMate について</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>選択したフィーチャを識別</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>選択したフィーチャにズーム</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>地図上でフィーチャを選択</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>地図上でフィーチャを追跡</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">3 つの選択モードをリンク</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>レイヤのプロパティをリセット</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>現在のレイヤを追跡</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>フィルタするレイヤ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>既存のフィルタと組み合わせる</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>ジオメトリ述語</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>バッファ距離</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>バッファタイプ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>エクスポートするレイヤ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>エクスポートの投影法</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>スタイルをエクスポート</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>エクスポート形式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>出力フォルダ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>エクスポートを zip 圧縮</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>パネルのレイアウトを適用できませんでした。既定のサイズを使用します。詳細は filtermate.log を参照してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6890"/>
        <location filename="../ui/controllers/backend_controller.py" line="682"/>
        <source>Vector</source>
        <translation>ベクタ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>単一選択と複数選択をリンク</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>スキーマ '{0}' と、次の {1} 個の一時オブジェクトが削除されます:</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>… 他 {0} 件</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>スキーマ '{0}' は空であり、削除されます。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>FilterMate スキーマを削除</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>Read failed</source>
        <translation>読み取りに失敗しました</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>The service could not be read. Please retry.</source>
        <translation>サービスを読み取れませんでした。再試行してください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4589"/>
        <source>Loading filtered extent…</source>
        <translation>フィルタ後の範囲を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5184"/>
        <location filename="../ui/controllers/exploring_controller.py" line="742"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3658"/>
        <source>Loading selected values…</source>
        <translation>選択した値を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">この式はサービス向けに安全に評価できません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2715"/>
        <source>Error evaluating expression: {0}</source>
        <translation>式の評価エラー: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2716"/>
        <source>Expression Evaluation</source>
        <translation>式の評価</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="444"/>
        <source>Loading values…</source>
        <translation>値を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="846"/>
        <source>Loading zoom extent…</source>
        <translation>ズーム範囲を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>選択に一致するジオメトリ付きの地物がありません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="434"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>表示されるのは一部の値のみです。他の値を探すには検索条件を絞り込んでください。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5119"/>
        <location filename="../ui/controllers/exploring_controller.py" line="551"/>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <location filename="../ui/controllers/exploring_controller.py" line="691"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3651"/>
        <source>Selection</source>
        <translation>選択</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="550"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>サービスの選択がキーの上限を超えています。選択を絞り込んでください。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <source>This service has no stable key for the selection.</source>
        <translation>このサービスには、選択に使用できる安定したキーがありません。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="436"/>
        <location filename="../ui/controllers/exploring_controller.py" line="438"/>
        <source>Values</source>
        <translation>値</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="808"/>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>Zoom</source>
        <translation>ズーム</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1087"/>
        <source>&apos;{0}&apos; is not a FilterMate temporary schema: it is not dropped</source>
        <translation>'{0}' は FilterMate の一時スキーマではないため、削除されません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1312"/>
        <source>... and {0} more (see details)</source>
        <translation>… 他 {0} 件（詳細を参照）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="778"/>
        <source>Auto (Default)</source>
        <translation>自動（デフォルト）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="786"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>すべてのレイヤーに最適なものを自動選択</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="817"/>
        <source>Auto-selected backends for {0} layer(s)</source>
        <translation>{0} 個のレイヤーのバックエンドを自動選択しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="838"/>
        <source>Backend forced to {0} for &apos;{1}&apos;</source>
        <translation>'{1}' のバックエンドを {0} に固定しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="841"/>
        <source>Backend set to Auto for &apos;{0}&apos;</source>
        <translation>'{0}' のバックエンドを自動に設定しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1336"/>
        <source>Cleanup cancelled</source>
        <translation>クリーンアップをキャンセルしました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="807"/>
        <source>Clear ALL FilterMate temporary tables from all databases</source>
        <translation>すべてのデータベースから FilterMate の一時テーブルをすべて消去</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="797"/>
        <source>Clear Temp Tables</source>
        <translation>一時テーブルを消去</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1317"/>
        <source>Clear all FilterMate temporary tables</source>
        <translation>FilterMate の一時テーブルをすべて消去</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="802"/>
        <source>Clear temporary tables for the current project only</source>
        <translation>現在のプロジェクトの一時テーブルのみを消去</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="828"/>
        <source>Cleared {0} temporary table(s) for current project</source>
        <translation>現在のプロジェクトの一時テーブルを {0} 個消去しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1340"/>
        <source>Cleared {0} temporary table(s) globally</source>
        <translation>一時テーブルを全体で {0} 個消去しました</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1307"/>
        <source>FilterMate will permanently delete {0} temporary table(s) / view(s) from the databases of the project and of the PostgreSQL connection:</source>
        <translation>FilterMate は、プロジェクトおよび PostgreSQL 接続のデータベースから、{0} 個の一時テーブル / ビューを完全に削除します:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="791"/>
        <source>Force {0} for All Layers</source>
        <translation>すべてのレイヤーに {0} を強制</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="742"/>
        <source>No alternative backends available for this layer</source>
        <translation>このレイヤーで利用できる代替バックエンドはありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1333"/>
        <location filename="../ui/controllers/backend_controller.py" line="1342"/>
        <source>No temporary tables found</source>
        <translation>一時テーブルが見つかりません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="830"/>
        <source>No temporary tables found for current project</source>
        <translation>現在のプロジェクトの一時テーブルが見つかりません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1080"/>
        <source>Schema &apos;{0}&apos; does not exist: nothing to drop</source>
        <translation>スキーマ '{0}' は存在しないため、削除するものはありません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1083"/>
        <source>Schema &apos;{0}&apos; holds objects FilterMate did not create ({1}): it is not dropped</source>
        <translation>スキーマ '{0}' に FilterMate が作成していないオブジェクト ({1}) があるため、削除されません</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="762"/>
        <source>Select Backend:</source>
        <translation>バックエンドを選択:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1313"/>
        <source>Your own tables and layers are not touched. Continue?</source>
        <translation>ユーザー自身のテーブルとレイヤーには影響しません。続行しますか?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="805"/>
        <source>🌐 All Projects (Global)</source>
        <translation>🌐 すべてのプロジェクト（グローバル）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="800"/>
        <source>📁 Current Project</source>
        <translation>📁 現在のプロジェクト</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>The filter was not launched: its selection changed or could not be read. Click Filter again.</source>
        <translation>フィルタは開始されませんでした: 選択が変更されたか、読み取れませんでした。もう一度「フィルタ」をクリックしてください。</translation>
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
        <translation>単一選択</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>複数選択</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>カスタム選択</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>フィルタリング</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>エクスポート</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>設定</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>エクスポート用CRSを選択</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>エクスポート</translation>
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
        <translation>マルチレイヤーフィルタリング</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>選択したレイヤーの追加フィルタリング</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>地理空間フィルタリング</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>バッファ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>式レイヤー</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>空間述語</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>出力形式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>フィルター</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>リセット</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>エクスポートするレイヤー</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>レイヤー座標系</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>スタイルを保存</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>データ型エクスポート</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>ファイル/ディレクトリ名</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>ソースレイヤーに完全なジオメトリの代わりに重心を使用 (複雑なポリゴンに高速)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>メートル単位のバッファ値 (正=拡大、負=ポリゴン縮小)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>バッファ精度のセグメント数</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>バッチモード</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="633"/>
        <source>FilterMate was unloaded</source>
        <translation>FilterMate はアンロードされました</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="119"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>レンダリング済みまたは未対応のラスタ: フィルタ対象にはできません</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="582"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>レンダリング済みラスタソースにはローカルの色キャプチャが必要です。数値ピクセルによる選択は使用できません</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="654"/>
        <source>the source layer itself was not changed</source>
        <translation>ソースレイヤー自体は変更されていません</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="347"/>
        <source>{count} features visible in main layer</source>
        <translation>メインレイヤーに{count}個の地物が表示</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>すべてのフィルターを解除 - メインレイヤーに{count}個の地物が表示</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>タスク失敗</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>フィルター失敗: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0}件追加)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>レイヤーがフィルタリングされました</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>レイヤーが前の状態にフィルタリングされました</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>レイヤーのフィルター解除</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>フィルタータスク : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>エクスポートタスク : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>例外: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>フィルタは適用されず、以前のフィルタを維持しました: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>フィルタ中に削除されたレイヤーは除外されました: {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>リモートで地表からの高さを計算する前に、有効な選択範囲を描画してください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>DTM とポイントクラウドに共通の有効範囲がありません</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>有効な選択範囲にポリゴン面積がありません</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>地表からの高さは有効範囲のみを対象とします。フィルタ解除で元のクラウドに戻ります</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Pythonメニューとツールバー</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>プロパティ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>値</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>プロパティ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>値</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="262"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>PostgreSQLレイヤーが検出されました ({0})がpsycopg2がインストールされていません。プラグインはこれらのレイヤーを使用できません。PostgreSQLサポートを有効にするにはpsycopg2をインストールしてください。</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>保存されたソースを開けませんでした</translation>
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
        <translation>PostgreSQLレイヤー'{0}': 破損データが検出されました。

このレイヤーはPostgreSQLに存在しない'virtual_id'を使用しています。
このエラーは以前のバージョンのFilterMateに起因します。

解決方法: このレイヤーをFilterMateプロジェクトから削除し、再度追加してください。
PostgreSQLテーブルにPRIMARY KEYが定義されていることを確認してください。</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>レイヤー'{0}'にPRIMARY KEYがありません。機能制限: マテリアライズドビューが無効です。最適なパフォーマンスのためにPRIMARY KEYを追加することをお勧めします。</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>例外: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: このプロバイダーでは、サーバーフィルタの完全性を保証できません。フィルタする前に、範囲を限定したローカルコピーを使用してください。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: 選択した地物のキー値をウェブサービスから読み取れませんでした。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>は以前のフィルタを維持します</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>はフィルタされないままです</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: このウェブサービスには一意のキーフィールド（宣言されたキー、id、gml_id、cleabs、objectid など）がないため、選択した地物をサーバー向けに列挙できません。レイヤー{1}。属性フィルタまたはレイヤーのローカルコピーを使用すれば処理できます。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: このレイヤーには一意のキーフィールドがなく、フィーチャ ID をフィルタ内で列挙できません（仮想レイヤーには一意の ID 列、uid が必要です）。レイヤー{1}。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: 列挙する地物 {1} 件は、ウェブサービスに送信できる上限の {2} 件を超えています。レイヤー{3}。選択を絞り込むか、属性フィルタを使用するか、レイヤーのローカルコピーで作業してください。</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>最適化設定</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>最適化設定の構成</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>自動最適化を有効にする</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>最適化適用前に確認する</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>自動重心設定</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>遠距離レイヤーの自動重心を有効にする</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>距離しきい値 (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>地物しきい値:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>バッファ最適化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>バッファ前にジオメトリを簡略化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>バッファセグメントを削減:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>一般</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>フィルタリングにマテリアライズドビューを使用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>空間インデックスを自動作成</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>R-tree空間インデックスを使用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>バウンディングボックスプレフィルターを使用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>バックエンド</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>キャッシュ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>ジオメトリキャッシュを有効にする</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>一括処理</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>バッチサイズ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>詳細設定はパフォーマンスとメモリ使用量に影響します。影響を理解している場合のみ変更してください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>詳細</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="323"/>
        <source>PostgreSQL</source>
        <translation>PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="335"/>
        <source>Spatialite</source>
        <translation>SpatiaLite</translation>
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
        <translation>前の条件との結合</translation>
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
        <translation>属性</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>比較</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>範囲内</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>この条件を削除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>値または別の属性と比較</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="821"/>
        <source>value</source>
        <translation>値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="822"/>
        <source>Value</source>
        <translation>値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="825"/>
        <source>Highest value kept</source>
        <translation>残す最大値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>観測値: {0} ～ {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>この属性の統計はありません</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1053"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>データセットの他のタイルにも適用</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1062"/>
        <source>CLASSES</source>
        <translation>クラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Ground</source>
        <translation>地面</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Vegetation</source>
        <translation>植生</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1069"/>
        <source>Buildings</source>
        <translation>建物</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1070"/>
        <source>Above ground</source>
        <translation>地上物</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1071"/>
        <source>Water</source>
        <translation>水域</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1072"/>
        <source>Without noise</source>
        <translation>ノイズなし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">これらのクラスのみチェック</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">すべて</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1101"/>
        <source>Point classes</source>
        <translation>ポイントのクラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">属性の範囲</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (m)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">残す最低標高</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">残す最高標高</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Intensity</source>
        <translation>強度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">残す最低強度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">残す最高強度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">リターン</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">残すレーザーパルスのエコー</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">DTM からの高さ ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1290"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>高さの基準とする数値地形モデル</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1300"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>地形モデルからこの高さ以上にあるポイントを残す</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>EXPRESSION</source>
        <translation>式</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1379"/>
        <source>Point cloud expression</source>
        <translation>ポイントクラウドの式</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1380"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>グループにチェックを入れると式を手動で編集できます</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">このレイヤには標高の統計がありません</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1661"/>
        <source>Height above the terrain is unavailable</source>
        <translation>地形からの高さは利用できません</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">残るポイント: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">現在のフィルタ: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">すべて</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">最初</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Last</source>
        <translation type="obsolete">最後</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Single</source>
        <translation type="obsolete">単一</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1176"/>
        <source>ATTRIBUTES</source>
        <translation>属性</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1194"/>
        <source>+ Condition</source>
        <translation>+ 条件</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1196"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>レイヤの属性に条件を追加</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1235"/>
        <source>Returns</source>
        <translation>リターン</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">レーザーパルスの最初、最後、または単一のリターンを残す</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1242"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>最初のリターン (ReturnNumber = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1243"/>
        <source>Last return (ReturnNumber = NumberOfReturns)</source>
        <translation>最後のリターン (ReturnNumber = NumberOfReturns)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1244"/>
        <source>Single return (NumberOfReturns = 1)</source>
        <translation>単一リターン (NumberOfReturns = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1349"/>
        <source>Return number</source>
        <translation>リターン番号</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1350"/>
        <source>Number of returns</source>
        <translation>リターン数</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1351"/>
        <source>Classification</source>
        <translation>分類</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Scan angle</source>
        <translation>スキャン角度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>User data</source>
        <translation>ユーザーデータ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Point source ID</source>
        <translation>点群ソース ID</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>GPS time</source>
        <translation>GPS 時刻</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Red</source>
        <translation>赤</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1357"/>
        <source>Green</source>
        <translation>緑</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1358"/>
        <source>Blue</source>
        <translation>青</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1359"/>
        <source>Infrared</source>
        <translation>近赤外</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Scan direction</source>
        <translation>スキャン方向</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Edge of flight line</source>
        <translation>飛行ラインの端</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Synthetic</source>
        <translation>合成</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Key point</source>
        <translation>キーポイント</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Withheld</source>
        <translation>保留</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1365"/>
        <source>Overlap</source>
        <translation>オーバーラップ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>Scanner channel</source>
        <translation>スキャナチャンネル</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>Classification flags</source>
        <translation>分類フラグ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>Height above ground</source>
        <translation>地表からの高さ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Quick class selection</source>
        <translation>クラスのクイック選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">クイック選択…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>All classes</source>
        <translation>すべてのクラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>No class</source>
        <translation>クラスなし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>Invert the selection</source>
        <translation>選択を反転</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Selection ▾</source>
        <translation>選択 ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1115"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>規格のクラスのうち、このレイヤーにポイントがないもの</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1122"/>
        <source>Classes absent from the layer</source>
        <translation>レイヤーにないクラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1146"/>
        <source>Similar objects: area ×</source>
        <translation>類似オブジェクト: 面積 ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>最小の類似オブジェクト（クリックした最小のオブジェクトに対する割合）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>最大の類似オブジェクト（クリックした最大のオブジェクトに対する倍率）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1164"/>
        <source>to ×</source>
        <translation>〜 ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1208"/>
        <source>Pipette on</source>
        <translation>スポイト オン</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1209"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>レールの値スポイトがクリック位置で読み取る属性</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1224"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>取得した値を中心とする許容差（属性の観測範囲に対する %）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1236"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>すべてのリターン、またはレーザーパルスの最初、最後、単一のリターンを保持します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1241"/>
        <source>Any return</source>
        <translation>すべてのリターン</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1255"/>
        <source>HEIGHT / DTM</source>
        <translation>高さ / DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>Always combined (AND) with the active group</source>
        <translation>アクティブなグループと常に結合 (AND)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1265"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · 派生クラウド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1267"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>高さは PDAL がバックグラウンドタスクで派生ポイントクラウドとして計算します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1370"/>
        <source>{0} object(s)</source>
        <translation>{0} 個のオブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>cut at the window read</source>
        <translation>読み取りウィンドウで切り取り</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1372"/>
        <source>shown as the whole class in their box</source>
        <translation>枠内では分類全体として表示</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1863"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>その他のクラス（レイヤーにないもの）({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1954"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>オブジェクトがクリック周辺で読み取った最大のウィンドウを超えており、そこで切り取られました</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1956"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>クラウドの一部に対してオブジェクトが多すぎます: プレビューとフィルタ後のクラウドでは、周囲の枠内にある同じ分類のポイントがすべて保持されます。対象はオブジェクト単位で切り取られます</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">ポイントクラウドフィルタ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">分類</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">すべて</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">標高 (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">強度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="175"/>
        <source>Return number</source>
        <translation type="obsolete">リターン番号</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="199"/>
        <source>Minimum</source>
        <translation type="obsolete">最小</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="200"/>
        <source>Maximum</source>
        <translation type="obsolete">最大</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">現在のフィルタ: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">すべて</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>リモートのポイントクラウドには有効範囲が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>このポイントクラウド形式に対応する PDAL リーダーがありません</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>リモートのポイントクラウドには、バージョンを取得できる PDAL 2.4 以降が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>リモートのポイントクラウドで範囲を限定した読み取りを行うには、EPT または COPC が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>有効範囲は有限で、正の面積を持つ必要があります</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="513"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>リモートのポイントクラウドを読み取る前に、有効な選択範囲を描画してください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="546"/>
        <source>The remote point cloud could not be read</source>
        <translation>リモートのポイントクラウドを読み取れませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="550"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>リモートのポイントクラウドが選択を受け付けませんでした</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="811"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>範囲を限定した地表からの高さのクラウドは AND または AND NOT のみ対応しています。先にフィルタを解除してください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="837"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>リモートのポイントクラウドをクリップするには PDAL 2.4 以降が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="888"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Disjoint ではリモートクラウド全体を読み取ることになります。内側の選択を選んでください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="895"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>元のリモートポイントクラウドを開けませんでした</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQLセッション情報</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQLアクティブ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>接続情報</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>接続:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>一時スキーマ:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>ステータス:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>一時ビュー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>クリーンアップオプション</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>終了時に自動クリーンアップ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>FilterMate終了時に一時ビューを自動的にクリーンアップします。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ 今すぐクリーンアップ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>このセッションでFilterMateが作成したすべての一時ビューを削除します。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(一時ビューなし)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>ビューなし</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>クリーンアップする一時ビューはありません。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>クリーンアップの確認</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>クリーンアップ完了</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>クリーンアップの問題</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>クリーンアップ失敗</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQLが利用できません&lt;/b&gt;&lt;br&gt;&lt;br&gt;PostgreSQL機能を使用するには、psycopg2をインストールしてください:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;変更を適用するにはQGISを再起動してください。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>セッション: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>このセッションに{0}個のビュー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>FilterMateが作成した{view_count}個の一時ビューが削除されます。

保存されていないフィルター結果は失われます。

続行しますか?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped}個の一時ビューを削除しました。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>一部のビューを削除できませんでした: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>クリーンアップ中のエラー: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>フィルタするレイヤ</translation>
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
        <translation>バッファ</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="105"/>
        <source>Band</source>
        <translation>バンド</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>ラスタ式</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>出力フォルダ</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>ジオメトリ述語</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>ピクセル値</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>傾斜（度）</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>傾斜（%）</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>傾斜方向（度）</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>陰影起伏（0-255）</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>ソースラスタはキャプチャ用にリサンプリングされました（グリッド: {0}）。</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: 対象ラスタはキャプチャ用にリサンプリングされました（グリッド: {1}）。</translation>
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
        <translation>FilterMate — Resource Sharing に公開</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;お気に入りを公開&lt;/b&gt; — 共有可能なバンドルを QGIS Resource Sharing コレクションに書き込みます。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>既存のバンドルを上書き</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>公開</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. 対象コレクション&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>参照…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. バンドルファイル名&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>例: zones_bruxelles</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;対象&amp;gt;/filter_mate/favorites/&amp;lt;名前&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. コレクションのメタデータ&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>コレクション表示名</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>名前:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>作成者 / 組織</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>作成者:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>例: CC-BY-4.0、MIT、独自</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>ライセンス:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>カンマ区切りのタグ</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="221"/>
        <source>Tags:</source>
        <translation>タグ:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="224"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="225"/>
        <source>Homepage:</source>
        <translation>ホームページ:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="229"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>短い説明(任意、プレーンテキスト)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>説明:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. 含めるお気に入り&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>すべて選択</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>選択を解除</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Resource Sharing のルートに新しいコレクション…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>カスタムディレクトリ…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Resource Sharing のルート下に作成されます。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>'参照…' をクリックしてディレクトリを選択してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>コレクションディレクトリを選択</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} 個選択</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>コレクションを作成できません</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Resource Sharing のルートが見つかりません。代わりに '参照…' を使ってディレクトリを選択してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>ディレクトリを選択</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>'参照…' をクリックして対象ディレクトリを選択してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>お気に入りが選択されていません</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>公開するお気に入りを少なくとも1つ選択してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>公開に失敗しました</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>不明なエラーです。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>{0} 個のお気に入りを以下に公開しました:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>コレクションマニフェストを更新しました:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>公開に成功しました</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>リモートリポジトリが利用できません</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>リモートリポジトリマネージャが初期化されていません。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; への公開に失敗しました。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>クローンを開く…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>バンドルの書き込み先:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>コミット &lt;code&gt;{0}&lt;/code&gt; を &lt;b&gt;{1}&lt;/b&gt; にプッシュしました。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>git_url が設定されていません — バンドルはローカルに書き込まれました。独自のツールで手動プッシュしてください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>コミットする内容がありません — バンドルの内容に変更なし。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>{0} に公開しています...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>キャンセル</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>公開中</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>公開を実行中</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>公開処理がバックグラウンドでまだ実行中です。完了してから次の公開を開始してください。</translation>
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
        <translation>説明:</translation>
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
        <translation>レイヤー</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="184"/>
        <source>Export</source>
        <translation>エクスポート</translation>
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
        <translation>ステータス:</translation>
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
        <translation>フィルター入力...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>すべて選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>すべて選択 (非サブセット)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>すべて選択 (サブセット)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>すべて選択解除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>すべて選択解除 (非サブセット)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>すべて選択解除 (サブセット)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>表示値順に並べた最初の {0} 件のフィーチャを表示しています。レイヤ全体を検索するにはテキストフィルタに入力してください。「すべて選択」で全リストを読み込みます。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>レイヤの {0} 件のフィーチャを表示値順に表示しています。レイヤ全体を検索するにはテキストフィルタに入力してください。「すべて選択」で全リストを読み込みます。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>レイヤ全体での「{0}」の検索結果。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1808"/>
        <source>Loading values…</source>
        <translation>値を読み込んでいます…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1735"/>
        <source>Values</source>
        <translation>値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">この式はサービス向けに安全に評価できません。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>Selection</source>
        <translation>選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>リモートのリストが安全な選択上限を超えています。選択する地物を減らすか、先にレイヤーをフィルタしてください。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="2008"/>
        <source>Loading selected values…</source>
        <translation>選択した値を読み込んでいます…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>すべて選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>すべて選択解除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーを選択 (ライン)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーの選択を解除 (ライン)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーを選択 (ポイント)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーの選択を解除 (ポイント)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーを選択 (ポリゴン)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>ジオメトリタイプ別にすべてのレイヤーの選択を解除 (ポリゴン)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>すべてのラスタレイヤを選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>すべてのラスタレイヤの選択を解除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>すべてのポイントクラウドレイヤを選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>すべてのポイントクラウドレイヤの選択を解除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>ゾーン内のピクセル</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>ゾーン内のポイント</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>地物</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>ラスタ対象: ソースジオメトリ外のピクセルは NoData になります (内側は Disjoint 使用時)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>ポイントクラウド対象: ソースジオメトリ外のポイントは削除されます (内側は Disjoint 使用時)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>ベクタ対象: 空間述語を満たす地物が保持されます</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>右側の四角をクリックすると、このレイヤを重心でテストします</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="343"/>
        <source>Select all vector layers</source>
        <translation>すべてのベクタレイヤーを選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="345"/>
        <source>De-select all vector layers</source>
        <translation>すべてのベクタレイヤーの選択を解除</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>値範囲のヒストグラム</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>ハンドルをドラッグするかクリックして、残す値の範囲を選択します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>ヒストグラムなし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>{0} から {1} までの値を残します</translation>
    </message>
</context>
<context>
    <name>RasterExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="497"/>
        <source>Band</source>
        <translation type="obsolete">バンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="500"/>
        <source>Band whose values are selected</source>
        <translation type="obsolete">値を選択するバンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">ピクセル値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">現在のバンドのピクセル値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">最後に取得した {0} 個の値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">ピクセルピッカーで地図をクリックします。Ctrl+クリックで範囲をその値まで拡張します。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>値の範囲</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>最小</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>残す最小値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>最大</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>残す最大値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">地図上でプレビュー（他のピクセルを非表示）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">クラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">ラスタのクラス</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">すべて</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>ラスタ式</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>ラスタ計算式。値が 0 でないピクセルが残ります</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>ラスタ式</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">範囲を使用</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">現在の値の範囲を式として書き出す</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">選択されたピクセル: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>先に値の範囲を設定してください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2219"/>
        <source>NoData</source>
        <translation>NoData</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="834"/>
        <source>Last values:</source>
        <translation type="obsolete">最後の値:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="629"/>
        <source>Value of the current band under the cursor</source>
        <translation type="obsolete">カーソル位置の現在のバンドの値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">地図上に最後に描いた矩形内の現在のバンドの統計</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>カーソル位置: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>範囲: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>ピクセルなし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>最近の読み取り</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">計算対象</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">範囲を適用する量。傾斜、傾斜方向、陰影起伏、粗度ではバンドを DTM として読み取ります。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>ピクセル値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>傾斜（度）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>傾斜（%）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>傾斜方向（度）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>陰影起伏（0-255）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>粗度（TRI、平均差）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>この量の一般的なしきい値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">一般的なしきい値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>平坦</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>緩やか</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>中程度</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>急</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>東</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>南</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>West</source>
        <translation>西</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Shadow</source>
        <translation>影</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Lit</source>
        <translation>日向</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">一般的なしきい値…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>スポイト</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>許容差 ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>選択した色または値の周囲の許容差（値の範囲に対する %）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>スポイトの許容差</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>バンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">画像のバンドの内容: プリセットとスポイトがこれを使用します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">バンド構成</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB（赤、緑、青）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC（赤外、赤、緑）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + 赤外</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">よく使われる指数（植生、水域...）の式を書き出します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">スペクトルプリセット</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">3 バンド以上の画像が必要です（赤、緑、青...）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>植生（NDVI &gt; 0.3）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>植生なし（NDVI &lt; 0.1）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>水域（NDWI &gt; 0.1）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>植生（過剰緑色）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">スペクトルプリセット…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>このピクセルには値がありません（NoData）: 別のピクセルを選択してください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>許容差がすべての値を含んでいます: 小さくしてください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">範囲 {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">クラス {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} 色、最後: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">式</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>バンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>カーソル位置のアクティブバンドの値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>地図上で最後に描いた矩形内のアクティブバンドの統計</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>すべてのバンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>値の範囲はすべての色バンドに同時に適用されます（すべてのバンドが範囲内にあるピクセルが保持されます）。ヒストグラムは最初のバンドを表示します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>アクティブバンド: 範囲、ヒストグラム、ピッカーが読み取るバンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>スポイトはこのバンドを比較します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>バンドが持つ色: スペクトル指数とチップがこれを使用します。クリックして変更</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>スポイトで最後にクリックした位置の値</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>色なし</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>バンド 1、2、3 は赤、緑、青です</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>IRC</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>バンド 1、2、3 は赤外、赤、緑です（IGN 赤外カラーオルソフォト）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>バンド 1、2、3、4 は赤、緑、青、近赤外です</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>すべてのバンド: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> ロールは推測です。確認してください。</translation>
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
        <translation>赤</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Green</source>
        <translation>緑</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Blue</source>
        <translation>青</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1024"/>
        <source>Near infrared</source>
        <translation>近赤外</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>ロールは推測です。確認してください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>選択</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>類似ピクセル</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>選択した色または値に近いラスタ内のすべてのピクセル（レールのスポイト）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>クリックしたオブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>クリック位置を含む、そのようなピクセルのまとまりのみ: プール、屋根、畑など（レールのオブジェクト検出）。Ctrl+クリックで別のオブジェクトを追加します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>類似オブジェクト</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>クリックしたものに似たラスタ内のすべてのオブジェクト: 面積が下の比率の範囲内にあるピクセルのまとまり（レールの類似オブジェクトツール）。Ctrl+クリックで別の基準オブジェクトを追加します</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>面積 ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>最小の類似オブジェクト（クリックした最小のオブジェクトに対する割合）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>最大の類似オブジェクト（クリックした最大のオブジェクトに対する倍率）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>〜 ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>同じ形状</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>クリックしたオブジェクトと同じ形のオブジェクトのみを残します: 同じ比率の範囲内で、コンパクト度（4π × 面積 / 周長²、円盤なら 1）が一致するもの。オフの場合、プールと同じ面積の道路もプールとして扱われます</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>この取得を削除</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>量</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>範囲を適用する量。傾斜、傾斜方向、陰影起伏、粗度は、アクティブバンドを DTM として読み取ります。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>しきい値 ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>挿入 ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>バンド参照、一般的なスペクトル指数、または現在の範囲を挿入</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>スペクトル指数</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>範囲</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>現在の値の範囲</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>描画される色はスタイルと縮尺に依存します。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>色による選択のみ使用できます: 数値バンド、指数、範囲、クラス、派生データは使用できません。</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>値の範囲 — すべてのバンド</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>値の範囲 — バンド {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>取得元: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>傾斜や傾斜方向などは、1 つのバンドを DTM として読み取ります: 先に「バンド」でバンドを選択してください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>オブジェクトを読み取れませんでした</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>クリック位置にオブジェクトがありません: 許容差を上げるか、別のピクセルをクリックしてください</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>オブジェクトが読み取りウィンドウより大きく、切り取られました: 許容差を下げてください</translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>範囲を限定したラスタキャプチャに失敗しました</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="302"/>
        <source>local raster capture could not be opened</source>
        <translation>ローカルのラスタキャプチャを開けませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="284"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>ラスタ解析にはローカルの GDAL キャプチャが必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>ラスタキャプチャがキャンセルされました</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>ラスタキャプチャの保存先はセッションキャッシュ内である必要があります</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>ラスタキャプチャのプロバイダーを複製できませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>ラスタキャプチャには、有限で空でない範囲が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>ラスタキャプチャには正のピクセル上限が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>ラスタキャプチャには正の解像度が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="646"/>
        <source>raster capture source could not be opened</source>
        <translation>ラスタキャプチャのソースを開けませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>ラスタのマテリアライズはワーカースレッドで実行する必要があります</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="279"/>
        <source>raster selection canceled</source>
        <translation>ラスタ選択がキャンセルされました</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="294"/>
        <source>raster selection source could not be opened</source>
        <translation>ラスタ選択のソースを開けませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="275"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>リモートラスタの選択はワーカースレッドで実行する必要があります</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="281"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>描画された色による選択には、ローカルのレンダリングキャプチャが必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>レンダリング済みラスタには、描画色のキャプチャが必要です</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: ラスタ統計</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>ラスタのサンプリングに失敗しました。表示範囲を小さくして再試行してください。</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: ラスタプレビュー</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="642"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>リモートラスタ対象はワーカースレッドで実行する必要があります</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="671"/>
        <source>local raster target could not be opened</source>
        <translation>ローカルのラスタ対象を開けませんでした</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="681"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>レンダリング済みの色レイヤーはフィルタ対象にできません。</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>最適化を適用しますか?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>利用可能な最適化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>スキップ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>選択項目を適用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} u2022 {1}個の地物</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>影響: {0}</translation>
    </message>
</context>
<context>
    <name>RemoteMaterializer</name>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1000"/>
        <source>Partial result: the remote feature limit was reached.</source>
        <translation>部分的な結果: リモートの地物数の上限に達しました。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>部分的な結果: リモートの時間制限に達しました。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>リモートのフィルタ処理はキャンセルされました。以前のフィルタを維持します。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>500 個を超えるキーがサービスに送信されることになります。選択を絞り込むか、ローカルコピーを使用してください。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>サービスに安定したキーがありません。ローカルコピーを使用してください。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>空間フィルタの前に、リモートソースを選択またはフィルタしてください。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>サービスのフィルタが完全であることを証明できません。ソース地物を選択するか、ローカルコピーを使用してください。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>リモートソースのコピーが不完全です。以前のフィルタを維持します。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>部分的な結果: 上限に達するまで一致する地物が確認されませんでした。以前のフィルタを維持します。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>交差するリモートコピーが不完全なため、Disjoint フィルタを安全に計算できません。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Disjoint を他の述語と組み合わせるには、リモート対象のローカルコピーが必要です。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>リモートの空間述語を評価できませんでした。以前のフィルタを維持します。</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>リモートコピーを読み取れないか、フィルタできませんでした。以前のフィルタを維持します。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="138"/>
        <source>Remote materialization requires a background task.</source>
        <translation>リモートのマテリアライズにはバックグラウンドタスクが必要です。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="626"/>
        <source>Filtering a bounded remote copy</source>
        <translation>範囲を限定したリモートコピーをフィルタしています</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: レンダリング済みの色スナップショット</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>レンダリング済みスナップショットに失敗しました。表示範囲を小さくして再試行してください。</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>設定を検索... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>一致なし</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="285"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="460"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>FilterMate のタスクがレイヤーを読み取り中です。完了してから再試行してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="289"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>補助ストレージを持つレイヤーは、サーバープロバイダーを安全に置き換えられません。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="294"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>リモート結合はメインスレッドで再構築できません。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="296"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>このレイヤーのサーバーフィルタは既に準備中です。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="255"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>サーバーレイヤーは、所有スレッドでのみ変更できます。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="278"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>非同期のサーバーフィルタには QGIS 3.32 以降が必要です。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="404"/>
        <source>Could not install the prepared server filter.</source>
        <translation>準備したサーバーフィルタをインストールできませんでした。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="67"/>
        <source>Could not preserve the layer state.</source>
        <translation>レイヤーの状態を保持できませんでした。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="282"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="453"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>サーバーフィルタを適用する前に、レイヤーの編集を終了してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>属性式が無効です。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="106"/>
        <source>Preparing server attribute filter</source>
        <translation>サーバー属性フィルタを準備しています</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>QGIS はこの述語を OGC フィルタに変換できません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="336"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>サーバーフィルタがキャンセルされたか、タイムアウトしました。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="384"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>サーバーフィルタのインストールに失敗し、以前のプロバイダーを復元できませんでした。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="376"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="456"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>サーバーフィルタのインストールに失敗しました。以前のプロバイダーは既に無効で、復元できませんでした。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="391"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>サーバーフィルタのインストールに失敗しました。以前のプロバイダーを復元しました。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="56"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>サーバーフィルタをインストール中です。完了してから再試行してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="249"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="280"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="451"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>サーバーフィルタのインストールは、レイヤーのスレッドで開始する必要があります。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>式が複雑すぎて、安全に変換できません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>式が大きすぎるか、あいまいな SQL のバックスラッシュエスケープを含んでいます。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="354"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>フィルタの準備中にレイヤーが変更されました。準備した結果は破棄されました。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="402"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>レイヤーが利用できなくなりました。準備したフィルタは破棄されました。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>サーバーがフィルタを拒否したか、サーバーに接続できませんでした。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="287"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>このプロバイダーと QGIS のバージョンでは、検証済みワーカーの作成に対応していません。以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: 属性フィルタを完全にサーバー上で実行することはできません。未対応の部分: {1}。{2} 以前のフィルタは変更されていません。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="270"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="494"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: プロバイダーが属性フィルタを拒否しました。以前のフィルタを復元しました。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="269"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="493"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: プロバイダーがフィルタを拒否し、復元にも失敗しました。</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — 共有お気に入り</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;共有お気に入り&lt;/b&gt; — QGIS Resource Sharing コレクションから検出</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">名前、説明、コレクション、またはタグで検索…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>プレビューする共有お気に入りを選択してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>再スキャン</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>自分のプロジェクトにフォーク</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>閉じる</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>共有コレクションが見つかりませんでした。&lt;code&gt;filter_mate/favorites&lt;/code&gt; フォルダを含む Resource Sharing リポジトリを購読するか、resource_sharing コレクションディレクトリに &lt;code&gt;.fmfav.json&lt;/code&gt; バンドルを配置してください。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{1} 個のコレクション内の {0} 個のお気に入り: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>コレクション: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">検索に一致する共有お気に入りがありません。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — 出所: &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;式&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;リモートレイヤ&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;タグ:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;出所&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>作成者: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>ライセンス: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>共有お気に入りをフォーク</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>プロジェクト内の名前:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>フォーク成功</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>「{0}」がお気に入りに追加されました。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>フォークに失敗しました</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>共有お気に入りをプロジェクトに追加できませんでした。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>名前、説明、コレクション、作成者、タグで検索...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>作成者:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>すべての作成者</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>フィルタに一致する共有お気に入りはありません。</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>デフォルトにリセット</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>検証エラー</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>以下のエラーを修正してください:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>設定リセット</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>すべての値をデフォルトにリセットしますか?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - PostgreSQL型警告</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>フィルターで型の不一致: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>デフォルトにリセット</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>一般</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>{0} のフィルタを適用できませんでした。以前のフィルタを維持します。</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>メインレイヤーに{count}個の地物が表示</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>すべてのフィルターを解除 - メインレイヤーに{count}個の地物が表示</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>'{layer_name}'にフィルター適用: {count}個の地物</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>'{layer_name}'のフィルター解除: {count}個の地物が表示</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="942"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>エンティティが選択されていません! 選択ウィジェットが地物を失いました。エンティティを再選択してください。</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1060"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>選択されたレイヤーが無効またはソースが見つかりません。操作がキャンセルされました。</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1075"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>レイヤー'{0}'はまだ初期化されていません。別のレイヤーを選択してから、このレイヤーに切り替えてみてください。</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>元に戻せません: レイヤーが無効またはソースが見つかりません。</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>やり直しできません: レイヤーが無効またはソースが見つかりません。</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>プロバイダーが保存済みのフィルタを拒否しました。</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>フィルタを復元できませんでした: {0}</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="572"/>
        <source>Explore ...</source>
        <translation>探索 ...</translation>
    </message>
</context>
<context>
    <name>VectorTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="301"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: 一意のキーフィールドがないため、フィルタ内で地物を列挙できません（ウェブサービス、または一意の ID 列のない仮想レイヤー）。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="452"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>列挙する地物 {0} 件は、ウェブサービスに送信できる上限の {1} 件を超えています: ソースを絞り込むか、属性フィルタを使用してください。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="392"/>
        <source>{0} AND NOT would keep the features not read; the previous filter is kept.</source>
        <translation>{0} の AND NOT では読み取れなかった地物が残ってしまいます。以前のフィルタを維持します。</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>クリップされたタイルオブジェクトでは最小カバー率を使用できません</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>ベクタタイル対象は Intersect と Disjoint のみ対応しています</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>ベクタタイルのフィルタには CRS の権限コードが必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>ベクタタイルの表示フィルタ: 属性はズームレベルに依存します。タイルをまたいで分割されたオブジェクトは異なる場合があります</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>フィルタの実行中にベクタタイルのスタイルが変更されました。もう一度お試しください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>ベクタタイルの属性をフィルタ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>ベクタタイルのフィルタ式が無効です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>QGIS 式（属性はズームレベルに依存）:</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>ベクタタイルのフィルタをやり直す</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>対象のみ。属性はズームレベルに依存します。タイルをまたいで分割されたオブジェクトは、異なる方法でフィルタされる場合があります。</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>保存されたベクタタイルのスタイルが無効です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>保存されたベクタタイルのシンボルプロパティが無効です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>タイルの選択が式の上限（1 MB）を超えています。範囲を小さくしてください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>タイルの選択が頂点数の上限（2000）を超えています。範囲を小さくしてください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>ベクタタイルのフィルタが式の上限（1 MB）を超えています</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>ベクタタイルのフィルタが、スタイル式の合計上限（1 MB）を超えています。範囲を小さくしてください</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>ベクタタイルのフィルタを元に戻す</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>ベクタタイルのフィルタを解除</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>ベクタタイルの属性フィルタ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="131"/>
        <source>Vector tile favorite</source>
        <translation>ベクタタイルのお気に入り</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>ベクタタイルのフィルタ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>ベクタタイルのフィルタには基本レンダラーが必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>ベクタタイルのフィルタには基本ラベル設定が必要です</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>ベクタタイルのフィルタ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>ベクタタイル</translation>
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
        <translation type="obsolete">ソースジオメトリ: EXPLORING で選択した地物</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">ソースジオメトリ: 選択したピクセル (ベクタ化)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">保持したポイント</translation>
    </message>
</context>
</TS>
