<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="zh_CN" sourcelanguage="en_US">
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="171"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>已从 {0} 个图层中清除损坏的过滤器。请重新应用您的过滤器。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="240"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>检测到空项目。添加矢量图层以激活插件。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="307"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>无法访问 FilterMate 数据库。请检查项目目录权限。</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="321"/>
        <source>Error during database verification: {0}</source>
        <translation>数据库验证期间出错：{0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="617"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>图层加载失败。使用 F5 强制重新加载。</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="183"/>
        <source>Select Backend:</source>
        <translation>选择后端：</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="202"/>
        <source>Auto (Default)</source>
        <translation>自动（默认）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="210"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>为所有图层自动选择最优后端</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="220"/>
        <source>Force {0} for All Layers</source>
        <translation>为所有图层强制使用 {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="263"/>
        <source>Click to reload layers</source>
        <translation>点击重新加载图层</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="298"/>
        <source>Click to change backend</source>
        <translation>点击更改后端</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="350"/>
        <source>Error cancelling changes: {0}</source>
        <translation>取消更改时出错：{0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="612"/>
        <source>Property error: {0}</source>
        <translation>属性错误：{0}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="131"/>
        <source>Database file does not exist: {0}</source>
        <translation>数据库文件不存在：{0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="138"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>连接数据库 {0} 失败：{1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="157"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>无法创建数据库目录 {0}：{1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="211"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>创建数据库文件 {0} 失败：{1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="488"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>无法初始化 FilterMate 数据库：连接失败</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="493"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>连接数据库时发生严重错误：{0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="527"/>
        <source>Error during database initialization: {0}</source>
        <translation>数据库初始化期间出错：{0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="146"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>数据库文件不存在：{db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="157"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>连接数据库 {db_file_path} 失败：{error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>无法使用 QGIS Processing 模块创建空间索引</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="188"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>无法创建空间索引：图层无效或未找到数据源。</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="398"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>检测到 PostgreSQL 图层，但未安装 psycopg2。正在使用本地 Spatialite 后端。若要获得更大数据集的更好性能，请安装 psycopg2。</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>将图层保存到文件</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>选择导出图层的文件夹</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="158"/>
        <source>Save your exported data to a zip file</source>
        <translation>将导出数据保存为 zip 文件</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="116"/>
        <source>{0} couche(s)</source>
        <translation>{0} 个图层</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="118"/>
        <source> dans {0} groupe(s)</source>
        <translation> 在 {0} 个组中</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="120"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} 个未分组</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="127"/>
        <source>Destination : {0}</source>
        <translation>目标位置：{0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="147"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>未检测到组 - 所有图层位于根级别</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="155"/>
        <source>Annuler</source>
        <translation>取消</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="161"/>
        <source>Exporter</source>
        <translation>导出</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation>无过滤器</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No active filter to save.</source>
        <translation>没有可保存的活动过滤器。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Add Favorite</source>
        <translation>添加收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Favorite name:</source>
        <translation>收藏名称：</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="254"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>收藏 &apos;{0}&apos; 已成功添加</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="399"/>
        <source>Export Favorites</source>
        <translation>导出收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="423"/>
        <source>Exported {0} favorites</source>
        <translation>已导出 {0} 个收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="425"/>
        <source>Failed to export favorites</source>
        <translation>导出收藏失败</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Import Favorites</source>
        <translation>导入收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>与现有收藏合并？

是 = 添加到现有收藏
否 = 替换所有现有收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="493"/>
        <source>Imported {0} favorites</source>
        <translation>已导入 {0} 个收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="495"/>
        <source>No favorites imported</source>
        <translation>未导入任何收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="504"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>收藏管理器未初始化。请重新启动 FilterMate。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="538"/>
        <source>Favorites manager dialog not available</source>
        <translation>收藏管理器对话框不可用</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1779"/>
        <source>Error: {0}</source>
        <translation>错误：{0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation>已使用 {0} 次</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation>将当前过滤器添加到收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation>添加过滤器（无活动过滤器）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation>管理收藏...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation>导出...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation>导入...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation>全局收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation>复制到全局...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation>── 可用的全局收藏 ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation>（无全局收藏）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation>维护</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation>保存到项目 (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation>从项目恢复</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation>清理孤立项目</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation>数据库统计</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation>无效名称</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Favorite name cannot be empty.</source>
        <translation>收藏名称不能为空。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>Duplicate Name</source>
        <translation>重复名称</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>名为 &apos;{0}&apos; 的收藏已存在。
是否要替换它？</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1555"/>
        <source>Favorite copied to global favorites</source>
        <translation>收藏已复制到全局收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1558"/>
        <source>Failed to copy to global favorites</source>
        <translation>复制到全局收藏失败</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>Global Favorites</source>
        <translation>全局收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation>{0} 个全局收藏可用。

全局收藏在所有项目之间共享。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1581"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>已保存 {0} 个收藏到项目文件</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1583"/>
        <source>Save failed</source>
        <translation>保存失败</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1595"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>已从项目文件恢复 {0} 个收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1597"/>
        <source>No favorites to restore found in project</source>
        <translation>在项目中未找到可恢复的收藏</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1624"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>已清理 {0} 个孤立项目</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1626"/>
        <source>No orphan projects to clean up</source>
        <translation>没有可清理的孤立项目</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1751"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>FilterMate 数据库统计

收藏总数：{0}
   项目：{1}
   孤立：{2}
   全局：{3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1767"/>
        <source>Top projects by favorites:</source>
        <translation>按收藏数排名的项目：</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1771"/>
        <source>FilterMate Statistics</source>
        <translation>FilterMate 统计</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation>收藏管理器</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>尚未保存任何收藏。

请对图层应用筛选器，然后点击 ★ 指示器并选择「将当前筛选器添加到收藏」以保存您的第一个收藏。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation>从 Resource Sharing 导入…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation>发布到 Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation>发布（未保存收藏）</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1734"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>FilterMate 配置目录尚未初始化 — 请先打开启用 FilterMate 的 QGIS 项目。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1692"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation>Resource Sharing 扩展未启用。请在 FilterMate 设置中启用 &apos;favorites_sharing&apos;。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1700"/>
        <source>Shared favorites service is not available.</source>
        <translation>共享收藏服务不可用。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1686"/>
        <source>Shared picker failed: {0}</source>
        <translation>共享收藏选择器失败：{0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1704"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation>您还没有可发布的收藏。请先通过 ★ 菜单保存一个筛选器。</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1720"/>
        <source>Publish dialog failed: {0}</source>
        <translation>打开发布对话框失败：{0}</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="118"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - 收藏管理器</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="946"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;已保存的收藏 ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="180"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>按名称、表达式、标签或描述搜索...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="444"/>
        <source>General</source>
        <translation>常规</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Expression</source>
        <translation>表达式</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="697"/>
        <source>Remote</source>
        <translation>远程</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="466"/>
        <source>Favorite name</source>
        <translation>收藏名称</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="467"/>
        <source>Name:</source>
        <translation>名称：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="471"/>
        <source>Description (auto-generated, editable)</source>
        <translation>描述（自动生成，可编辑）</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="472"/>
        <source>Description:</source>
        <translation>描述：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="475"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>输入以逗号分隔的标签（例如：urban, population, 2024）</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="478"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>标签有助于组织和搜索收藏。
使用逗号分隔多个标签。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="481"/>
        <source>Tags:</source>
        <translation>标签：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="486"/>
        <source>Source Layer:</source>
        <translation>源图层：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="490"/>
        <source>Provider:</source>
        <translation>数据提供者：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="498"/>
        <source>Used:</source>
        <translation>已使用：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="501"/>
        <source>Created:</source>
        <translation>创建时间：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="514"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;源图层表达式：&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="518"/>
        <source>Filter expression for source layer</source>
        <translation>源图层的过滤表达式</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="533"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;已过滤的远程图层：&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Layer</source>
        <translation>图层</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Features</source>
        <translation>要素</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="545"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;此收藏中没有远程图层&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="558"/>
        <source>Apply</source>
        <translation>应用</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="561"/>
        <source>Apply this favorite filter to the project</source>
        <translation>将此收藏过滤器应用到项目</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="564"/>
        <source>Save Changes</source>
        <translation>保存更改</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="567"/>
        <source>Save modifications to this favorite</source>
        <translation>保存对此收藏的修改</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="570"/>
        <source>Delete</source>
        <translation>删除</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="573"/>
        <source>Permanently delete this favorite</source>
        <translation>永久删除此收藏</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Close</source>
        <translation>关闭</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="578"/>
        <source>Close this dialog</source>
        <translation>关闭此对话框</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;收藏 ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="691"/>
        <source>Remote ({0})</source>
        <translation>远程 ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Delete Favorite</source>
        <translation>删除收藏</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="774"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>删除收藏 &apos;{0}&apos;？</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="870"/>
        <source>Remote Layers</source>
        <translation>远程图层</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="942"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;已保存的收藏 (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>Favorites Manager</source>
        <translation>收藏管理器</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>No favorites saved yet.

Click the ★ indicator and select &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>尚未保存任何收藏。

点击 ★ 指示器并选择“将当前过滤器添加到收藏”来保存您的第一个收藏。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="146"/>
        <source>Shared...</source>
        <translation>共享…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="148"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>浏览通过 QGIS Resource Sharing 集合共享的收藏</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="158"/>
        <source>Publish...</source>
        <translation>发布…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="160"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>将选定的收藏发布到 Resource Sharing 集合</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Could not delete &apos;{0}&apos;. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation>无法删除「{0}」。收藏仍在数据库中 — 详情请查看 FilterMate 日志。</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="588"/>
        <source>View</source>
        <translation>查看</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="590"/>
        <source>Change</source>
        <translation>更改</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="601"/>
        <source>Select a folder</source>
        <translation>选择文件夹</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="608"/>
        <source>Select a file</source>
        <translation>选择文件</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="616"/>
        <source>Save to a file</source>
        <translation>保存到文件</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="648"/>
        <source>View</source>
        <translation>查看</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="650"/>
        <source>Change</source>
        <translation>更改</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="659"/>
        <source>Select an icon</source>
        <translation>选择图标</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>图层无效或找不到其数据源。操作已取消。</translation>
    </message>
</context>
<context>
    <name>FilterMate</name>
    <message>
        <location filename="../filter_mate.py" line="190"/>
        <source>&amp;FilterMate</source>
        <translation>&amp;FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="314"/>
        <source>FilterMate</source>
        <translation>FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="314"/>
        <source>Open FilterMate panel</source>
        <translation>打开 FilterMate 面板</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset configuration and database</source>
        <translation>重置配置和数据库</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>恢复默认配置并删除 SQLite 数据库</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Reset Configuration</source>
        <translation>重置配置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1357"/>
        <source>Configuration reset successfully.</source>
        <translation>配置重置成功。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1362"/>
        <source>Default configuration file not found.</source>
        <translation>未找到默认配置文件。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1383"/>
        <source>Database deleted: {filename}</source>
        <translation>数据库已删除：{filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>Restart required</source>
        <translation>需要重新启动</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="403"/>
        <source>Obsolete configuration detected</source>
        <translation>检测到过时配置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="404"/>
        <source>unknown version</source>
        <translation>未知版本</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="412"/>
        <source>Corrupted configuration detected</source>
        <translation>检测到损坏的配置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="469"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>配置未重置。某些功能可能无法正常工作。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>Configuration created with default values</source>
        <translation>已使用默认值创建配置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="483"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>损坏的配置已重置。默认设置已恢复。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="486"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>过时的配置已重置。默认设置已恢复。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="507"/>
        <source>Configuration updated to latest version</source>
        <translation>配置已更新至最新版本</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="504"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>配置已更新：新设置可用 ({sections})。通过选项菜单访问。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="498"/>
        <source>Geometry Simplification</source>
        <translation>几何简化</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="499"/>
        <source>Optimization Thresholds</source>
        <translation>优化阈值</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="644"/>
        <source>Geometry validation setting</source>
        <translation>几何验证设置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="674"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>无效几何过滤已成功禁用。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="681"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>无效几何过滤未修改。某些要素可能会从导出中排除。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="405"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>检测到过时的配置 ({})。

是否要重置为默认设置？

• 是：重置（将创建备份）
• 否：保留当前配置（可能导致问题）</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="413"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>配置文件已损坏，无法读取。

是否要重置为默认设置？

• 是：重置（如果可能，将创建备份）
• 否：取消（插件可能无法正常工作）</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="420"/>
        <source>Configuration reset</source>
        <translation>重置配置</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="421"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>配置需要重置。

是否要继续？</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="526"/>
        <source>Error during configuration migration: {}</source>
        <translation>配置迁移时出错：{}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="646"/>
        <source>The QGIS setting &apos;Invalid features filtering&apos; is currently set to &apos;{mode}&apos;.

FilterMate recommends disabling this setting (value &apos;Off&apos;) for the following reasons:

• Features with invalid geometries could be silently excluded from exports and filters
• FilterMate handles geometry validation internally with automatic repair options
• Some legitimate data may have geometries considered as &apos;invalid&apos; according to strict OGC rules

Do you want to disable this setting now?

• Yes: Disable filtering (recommended for FilterMate)
• No: Keep current setting</source>
        <translation>The QGIS setting &apos;Invalid features filtering&apos; is currently set to &apos;{mode}&apos;.

FilterMate recommends disabling this setting (value &apos;Off&apos;) for the following reasons:

• Features with invalid geometries could be silently excluded from exports and filters
• FilterMate handles geometry validation internally with automatic repair options
• Some legitimate data may have geometries considered as &apos;invalid&apos; according to strict OGC rules

Do you want to disable this setting now?

• Yes: Disable filtering (recommended for FilterMate)
• No: Keep current setting</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>您确定要重置为默认配置吗？

这将：
- 恢复默认设置
- 删除图层数据库

必须重启 QGIS 才能应用更改。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>配置已重置。

请重启 QGIS 以应用更改。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="348"/>
        <source>Initialization error: {0}</source>
        <translation>初始化错误：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="585"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} 个引用的图层未加载 ({layers_list})。使用备用显示。</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1388"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>无法删除 {filename}：{e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation>重置期间出错：{str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1438"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style=&apos;font-size:13px;&apos;&gt;感谢您使用 &lt;b&gt;FilterMate&lt;/b&gt;！&lt;br&gt;加入我们的 Discord 社区：&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;获取帮助和支持&lt;/li&gt;&lt;li&gt;报告错误和问题&lt;/li&gt;&lt;li&gt;建议新功能&lt;/li&gt;&lt;li&gt;与其他用户分享技巧&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1454"/>
        <source>  Join us on Discord</source>
        <translation>  加入我们的 Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1474"/>
        <source>Don&apos;t show this again</source>
        <translation>不再显示</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1477"/>
        <source>Close</source>
        <translation>关闭</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1543"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>加载插件出错：{0}。查看 QGIS Python 控制台了解详情。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6711"/>
        <source>Current layer: {0}</source>
        <translation>当前图层：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6713"/>
        <source>No layer selected</source>
        <translation>未选择图层</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Selected layers:
{0}</source>
        <translation>选定的图层：
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>No layers selected</source>
        <translation>未选择图层</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6743"/>
        <source>No expression defined</source>
        <translation>未定义表达式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6755"/>
        <source>Display expression: {0}</source>
        <translation>显示表达式：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6770"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>要素 ID：{0}
第一个属性：{1}</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="274"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>检测到 PostgreSQL 图层 ({0})，但未安装 psycopg2。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="361"/>
        <source>Cleared {0} caches</source>
        <translation>已清除 {0} 个缓存</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="795"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>创建停靠部件失败：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="805"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>显示停靠部件失败：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1255"/>
        <source>Error executing {0}: {1}</source>
        <translation>执行 {0} 时出错：{1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1267"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>插件在降级模式下运行（六角形服务不可用）。性能可能降低。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate 错误</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>无法执行 {0}：部件初始化失败。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2167"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>无法执行 {0}：图层无效或未找到数据源。</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2304"/>
        <source>All filters cleared - </source>
        <translation>所有过滤器已清除 - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2305"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>主图层中可见 {0}{1} 个要素</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2311"/>
        <source>Error: result handler missing</source>
        <translation>错误：结果处理程序缺失</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2324"/>
        <source>Error during filtering: {0}</source>
        <translation>过滤期间出错：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2455"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>已恢复 {0} 个孤立收藏：{1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2591"/>
        <source>Layer loading failed - click to retry</source>
        <translation>图层加载失败 - 点击重试</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} 个图层已成功加载</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1618"/>
        <source>filter</source>
        <translation>filter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1620"/>
        <source>unfilter</source>
        <translation>unfilter</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1623"/>
        <source>FilterMate – Edit Mode Detected</source>
        <translation>FilterMate – Edit Mode Detected</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1625"/>
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
        <location filename="../filter_mate_app.py" line="1635"/>
        <source>Save Changes &amp; {0}</source>
        <translation>Save Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1642"/>
        <source>Discard Changes &amp; {0}</source>
        <translation>Discard Changes &amp; {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1649"/>
        <source>Cancel</source>
        <translation>取消</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1673"/>
        <source>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</source>
        <translation>Could not save changes for layer &quot;{0}&quot;. Operation cancelled.</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="596"/>
        <source>Initialization error: {}</source>
        <translation>初始化错误：{}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="925"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>UI 配置不完整 - 请检查日志</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation>UI 尺寸错误：{}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1355"/>
        <source>Favorites manager not available</source>
        <translation>收藏管理器不可用</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1374"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ 已保存 {0} 个收藏
点击应用或管理</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1382"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ 未保存收藏
点击添加当前过滤器</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1406"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>为 {1} 个图层强制使用 {0} 后端</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1492"/>
        <source>Backend controller not available</source>
        <translation>后端控制器不可用</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1430"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>PostgreSQL 自动清理已启用</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1431"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>PostgreSQL 自动清理已禁用</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>PostgreSQL 会话视图已清理</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>No views to clean or cleanup failed</source>
        <translation>没有要清理的视图或清理失败</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1448"/>
        <source>No PostgreSQL connection available</source>
        <translation>没有可用的 PostgreSQL 连接</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1454"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>模式有 {0} 个来自其他会话的视图。
仍要删除吗？</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1455"/>
        <source>Other Sessions Active</source>
        <translation>其他会话处于活动状态</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1457"/>
        <source>Schema cleanup cancelled</source>
        <translation>模式清理已取消</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1462"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>模式 &apos;{0}&apos; 已成功删除</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1464"/>
        <source>Schema cleanup failed</source>
        <translation>模式清理失败</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1490"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL 会话信息</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Theme adapted: {0}</source>
        <translation>主题已适配：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Dark mode</source>
        <translation>深色模式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Light mode</source>
        <translation>浅色模式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3896"/>
        <source>Selected features have no geometry.</source>
        <translation>所选要素没有几何图形。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3915"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>未选择要素。请从下拉列表中选择一个要素。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4957"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>所选图层无效或找不到其数据源。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5667"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>负缓冲区（侵蚀）：向内收缩多边形</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5670"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>缓冲区值（米）（正值=扩展，负值=收缩多边形）</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6144"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>插件已激活，包含 {0} 个矢量图层</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6227"/>
        <source>Could not reload plugin automatically.</source>
        <translation>无法自动重新加载插件。</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6229"/>
        <source>Error reloading plugin: {0}</source>
        <translation>重新加载插件时出错：{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6282"/>
        <source>Layer properties reset to defaults</source>
        <translation>图层属性已重置为默认值</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6283"/>
        <source>Error resetting layer properties: {}</source>
        <translation>重置图层属性时出错：{}</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidgetBase</name>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="57"/>
        <source>FilterMate</source>
        <translation>FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="778"/>
        <source>SINGLE SELECTION</source>
        <translation>单选</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="953"/>
        <source>MULTIPLE SELECTION</source>
        <translation>多选</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1112"/>
        <source>CUSTOM SELECTION</source>
        <translation>自定义选择</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1374"/>
        <source>FILTERING</source>
        <translation>过滤</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2647"/>
        <source>EXPORTING</source>
        <translation>导出</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3479"/>
        <source>CONFIGURATION</source>
        <translation>配置</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3225"/>
        <source>Select CRS for export</source>
        <translation>选择导出的坐标参考系</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3747"/>
        <source>Export</source>
        <translation>导出</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2333"/>
        <source>AND</source>
        <translation>与</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2338"/>
        <source>AND NOT</source>
        <translation>与非</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2343"/>
        <source>OR</source>
        <translation>或</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3280"/>
        <source>QML</source>
        <translation>QML</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3285"/>
        <source>SLD</source>
        <translation>SLD</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2536"/>
        <source> m</source>
        <translation> 米</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2409"/>
        <source>, </source>
        <translation>，</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1574"/>
        <source>Multi-layer filtering</source>
        <translation>多图层过滤</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1661"/>
        <source>Additive filtering for the selected layer</source>
        <translation>选定图层的叠加过滤</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1947"/>
        <source>Geospatial filtering</source>
        <translation>地理空间过滤</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2037"/>
        <source>Buffer</source>
        <translation>缓冲区</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2282"/>
        <source>Expression layer</source>
        <translation>表达式图层</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2394"/>
        <source>Geometric predicate</source>
        <translation>几何谓词</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3325"/>
        <source>Output format</source>
        <translation>输出格式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3583"/>
        <source>Filter</source>
        <translation>过滤</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3645"/>
        <source>Reset</source>
        <translation>重置</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2751"/>
        <source>Layers to export</source>
        <translation>要导出的图层</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2832"/>
        <source>Layers projection</source>
        <translation>图层投影</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2916"/>
        <source>Save styles</source>
        <translation>保存样式</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2997"/>
        <source>Datatype export</source>
        <translation>数据类型导出</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3078"/>
        <source>Name of file/directory</source>
        <translation>文件/目录名称</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2205"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>对源图层使用质心而不是完整几何（复杂多边形更快）</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2521"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>缓冲区值（米）（正值=扩展，负值=收缩多边形）</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2609"/>
        <source>Number of segments for buffer precision</source>
        <translation>缓冲区精度的段数</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3421"/>
        <source>Mode batch</source>
        <translation>批处理模式</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="281"/>
        <source>{count} features visible in main layer</source>
        <translation>主图层中可见 {count} 个要素</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="274"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>所有过滤器已清除 - 主图层中可见 {count} 个要素</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="347"/>
        <source>Task failed</source>
        <translation>任务失败</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="348"/>
        <source>Filter failed for: {0}</source>
        <translation>过滤失败：{0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="352"/>
        <source> (+{0} more)</source>
        <translation> （+{0} 个更多）</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="399"/>
        <source>Layer(s) filtered</source>
        <translation>图层已过滤</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="403"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>图层已过滤到之前的状态</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="407"/>
        <source>Layer(s) unfiltered</source>
        <translation>图层已取消过滤</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="411"/>
        <source>Filter task : {0}</source>
        <translation>过滤任务：{0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="432"/>
        <source>Export task : {0}</source>
        <translation>导出任务：{0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="457"/>
        <source>Exception: {0}</source>
        <translation>异常：{0}</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Python 菜单和工具栏</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>属性</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>值</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>属性</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>值</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="212"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>检测到 PostgreSQL 图层 ({0})，但未安装 psycopg2。插件无法使用这些图层。安装 psycopg2 以启用 PostgreSQL 支持。</translation>
    </message>
</context>
<context>
    <name>LayersManagementEngineTask</name>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="944"/>
        <source>PostgreSQL layer &apos;{0}&apos;: Corrupted data detected.

This layer uses &apos;virtual_id&apos; which does not exist in PostgreSQL.
This error originates from a previous version of FilterMate.

Solution: Remove this layer from the FilterMate project, then re-add it.
Make sure the PostgreSQL table has a PRIMARY KEY defined.</source>
        <translation>PostgreSQL 图层 &apos;{0}&apos;：检测到损坏的数据。

此图层使用了 PostgreSQL 中不存在的 &apos;virtual_id&apos;。
此错误源自 FilterMate 的早期版本。

解决方案：从 FilterMate 项目中移除此图层，然后重新添加。
确保 PostgreSQL 表定义了 PRIMARY KEY。</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="970"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>图层 &apos;{0}&apos; 没有 PRIMARY KEY。功能受限：物化视图已禁用。建议：添加 PRIMARY KEY 以获得最佳性能。</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1909"/>
        <source>Exception: {0}</source>
        <translation>异常：{0}</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>优化设置</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>配置优化设置</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>启用自动优化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>应用优化前询问</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>自动质心设置</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>为远程图层启用自动质心</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>距离阈值（公里）：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>要素阈值：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>缓冲区优化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>缓冲前简化几何</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>将缓冲区段减少到：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>常规</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>使用物化视图进行过滤</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>自动创建空间索引</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>使用R树空间索引</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>使用边界框预过滤器</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>后端</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>缓存</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>启用几何缓存</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>批处理</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>批处理大小：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>高级设置会影响性能和内存使用。仅在了解影响的情况下更改。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>高级</translation>
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
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL会话信息</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL已激活</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>连接信息</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>连接：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>临时架构：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>状态：</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>临时视图</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>清理选项</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>关闭时自动清理</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>关闭FilterMate时自动清理临时视图。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ 立即清理</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>删除本次会话中FilterMate创建的所有临时视图。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>（无临时视图）</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>没有视图</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>没有临时视图需要清理。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>确认清理</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>清理完成</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>清理问题</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>清理失败</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL 不可用&lt;/b&gt;&lt;br&gt;&lt;br&gt;要使用 PostgreSQL 功能，请安装 psycopg2：&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;然后重新启动 QGIS 以应用更改。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>会话：{0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>此会话中有 {0} 个视图</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>这将删除 FilterMate 创建的 {view_count} 个临时视图。

所有未保存的过滤结果将丢失。

是否继续？</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>已移除 {result.views_dropped} 个临时视图。</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>部分视图无法移除：{result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>清理期间出错：{str(e)}</translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="125"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — 发布到 Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="133"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;发布收藏&lt;/b&gt; — 将可共享的捆绑包写入 QGIS Resource Sharing 集合。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="153"/>
        <source>Overwrite existing bundle</source>
        <translation>覆盖现有捆绑包</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="163"/>
        <source>Publish</source>
        <translation>发布</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="177"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. 目标集合&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="190"/>
        <source>Browse...</source>
        <translation>浏览…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="198"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. 捆绑包文件名&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="200"/>
        <source>e.g. zones_bruxelles</source>
        <translation>例如：zones_bruxelles</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="203"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;目标&amp;gt;/filter_mate/favorites/&amp;lt;名称&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. 集合元数据&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="214"/>
        <source>Collection display name</source>
        <translation>集合显示名称</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="215"/>
        <source>Name:</source>
        <translation>名称：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="218"/>
        <source>Author / organisation</source>
        <translation>作者 / 组织</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="219"/>
        <source>Author:</source>
        <translation>作者：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="222"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>例如：CC-BY-4.0、MIT、专有</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="223"/>
        <source>License:</source>
        <translation>许可证：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="226"/>
        <source>Comma-separated tags</source>
        <translation>以逗号分隔的标签</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="227"/>
        <source>Tags:</source>
        <translation>标签：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="230"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="231"/>
        <source>Homepage:</source>
        <translation>主页：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="235"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>简短描述（可选，纯文本）</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="238"/>
        <source>Description:</source>
        <translation>描述：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="250"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. 要包含的收藏&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="254"/>
        <source>Select all</source>
        <translation>全选</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="257"/>
        <source>Select none</source>
        <translation>全不选</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="284"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>在 Resource Sharing 根目录新建集合…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="288"/>
        <source>Custom directory...</source>
        <translation>自定义目录…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="340"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>将在 Resource Sharing 根目录下创建。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="345"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>点击 &apos;浏览…&apos; 选择目录。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="351"/>
        <source>Choose a collection directory</source>
        <translation>选择集合目录</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="402"/>
        <source>{0} / {1} selected</source>
        <translation>已选 {0} / {1}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Cannot create collection</source>
        <translation>无法创建集合</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>未找到 Resource Sharing 根目录。请改用 &apos;浏览…&apos; 选择目录。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Choose a directory</source>
        <translation>选择目录</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>点击 &apos;浏览…&apos; 选择目标目录。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>No favorites selected</source>
        <translation>未选择收藏</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>Select at least one favorite to publish.</source>
        <translation>请至少选择一个要发布的收藏。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Publish failed</source>
        <translation>发布失败</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Unknown error.</source>
        <translation>未知错误。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="505"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>已将 {0} 个收藏发布到：

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="509"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>集合清单已更新：
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="512"/>
        <source>Publish succeeded</source>
        <translation>发布成功</translation>
    </message>
</context>
<context>
    <name>QFieldCloudExtension</name>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="114"/>
        <source>QFieldCloud Settings...</source>
        <translation>QFieldCloud Settings...</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/extension.py" line="146"/>
        <source>Export filtered layers to QFieldCloud</source>
        <translation>Export filtered layers to QFieldCloud</translation>
    </message>
</context>
<context>
    <name>QFieldCloudPushDialog</name>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="96"/>
        <source>Export to QFieldCloud</source>
        <translation>Export to QFieldCloud</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="111"/>
        <source>Active Filter</source>
        <translation>Active Filter</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="114"/>
        <source>No active filter</source>
        <translation>No active filter</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="115"/>
        <source>Filter:</source>
        <translation>Filter:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="117"/>
        <source>0 layers</source>
        <translation>0 layers</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="118"/>
        <source>Layers:</source>
        <translation>Layers:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="124"/>
        <source>QFieldCloud Project</source>
        <translation>QFieldCloud Project</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="129"/>
        <source>Project name:</source>
        <translation>Project name:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="133"/>
        <source>Description:</source>
        <translation>描述：</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="137"/>
        <source>Create new</source>
        <translation>Create new</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="138"/>
        <source>Update existing:</source>
        <translation>Update existing:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="142"/>
        <source>Mode:</source>
        <translation>Mode:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="152"/>
        <source>Layer Modes</source>
        <translation>Layer Modes</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Layer</source>
        <translation>图层</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="178"/>
        <source>Export</source>
        <translation>导出</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="203"/>
        <source>{0} layers ({1} features)</source>
        <translation>{0} layers ({1} features)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="211"/>
        <source>{0} layers (no filter active)</source>
        <translation>{0} layers (no filter active)</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="284"/>
        <source>Missing Name</source>
        <translation>Missing Name</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="284"/>
        <source>Please enter a project name.</source>
        <translation>Please enter a project name.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="291"/>
        <source>Not Connected</source>
        <translation>Not Connected</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="291"/>
        <source>QFieldCloud is not connected. Please configure credentials first.</source>
        <translation>QFieldCloud is not connected. Please configure credentials first.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="352"/>
        <source>No Layers</source>
        <translation>No Layers</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="352"/>
        <source>No valid layers to export.</source>
        <translation>No valid layers to export.</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="390"/>
        <source>Export Error</source>
        <translation>Export Error</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="380"/>
        <source>Failed to export layer &apos;{0}&apos;: {1}</source>
        <translation>Failed to export layer &apos;{0}&apos;: {1}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="390"/>
        <source>GPKG export failed: {0}</source>
        <translation>GPKG export failed: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="407"/>
        <source>Push complete!</source>
        <translation>Push complete!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="417"/>
        <source>Project successfully pushed to QFieldCloud!</source>
        <translation>Project successfully pushed to QFieldCloud!</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="417"/>
        <source>Project: {0}</source>
        <translation>Project: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="417"/>
        <source>Files: {0}</source>
        <translation>Files: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="417"/>
        <source>Duration: {0:.1f}s</source>
        <translation>Duration: {0:.1f}s</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="417"/>
        <source>URL: {0}</source>
        <translation>URL: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="425"/>
        <source>Warnings:</source>
        <translation>Warnings:</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="427"/>
        <source>Push Complete</source>
        <translation>Push Complete</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="437"/>
        <source>Error: {0}</source>
        <translation>Error: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="448"/>
        <source>Push Failed</source>
        <translation>Push Failed</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="448"/>
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
        <translation>状态：</translation>
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
        <location filename="../ui/widgets/custom_widgets.py" line="652"/>
        <source>Type to filter...</source>
        <translation>输入以过滤...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="661"/>
        <source>Select All</source>
        <translation>全选</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="663"/>
        <source>Select All (non subset)</source>
        <translation>全选（非子集）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="665"/>
        <source>Select All (subset)</source>
        <translation>全选（子集）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="667"/>
        <source>De-select All</source>
        <translation>取消全选</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="669"/>
        <source>De-select All (non subset)</source>
        <translation>取消全选（非子集）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="671"/>
        <source>De-select All (subset)</source>
        <translation>取消全选（子集）</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="220"/>
        <source>Select All</source>
        <translation>全选</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="222"/>
        <source>De-select All</source>
        <translation>取消全选</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="224"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>按几何类型选择所有图层（线）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="226"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>按几何类型取消选择所有图层（线）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="228"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>按几何类型选择所有图层（点）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="230"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>按几何类型取消选择所有图层（点）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="232"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>按几何类型选择所有图层（面）</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="234"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>按几何类型取消选择所有图层（面）</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>应用优化？</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>可用优化</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>跳过</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>应用所选</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} 个要素</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>影响：{0}</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="75"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>搜索配置... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="180"/>
        <source>No match</source>
        <translation>无匹配</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="55"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — 共享收藏</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="63"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;共享收藏&lt;/b&gt; — 从 QGIS Resource Sharing 集合中发现</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation>按名称、描述、集合或标签搜索…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="98"/>
        <source>Select a shared favorite to preview.</source>
        <translation>选择共享收藏以预览。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="114"/>
        <source>Rescan</source>
        <translation>重新扫描</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="118"/>
        <source>Fork to my project</source>
        <translation>Fork 到我的项目</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="124"/>
        <source>Close</source>
        <translation>关闭</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="139"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>未找到共享集合。请订阅包含 &lt;code&gt;filter_mate/favorites&lt;/code&gt; 文件夹的 Resource Sharing 仓库，或将 &lt;code&gt;.fmfav.json&lt;/code&gt; 捆绑包放入 resource_sharing 集合目录。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="147"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{1} 个集合中的 {0} 个收藏：{2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="160"/>
        <source>Collection: {0}</source>
        <translation>集合：{0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation>没有与您的搜索匹配的共享收藏。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="194"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — 来自 &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="208"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;表达式&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="213"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;远程图层&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="227"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;标签：&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="234"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;来源&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="236"/>
        <source>Author: {0}</source>
        <translation>作者：{0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="238"/>
        <source>License: {0}</source>
        <translation>许可证：{0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Fork shared favorite</source>
        <translation>Fork 共享收藏</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Name in your project:</source>
        <translation>您的项目中的名称：</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>Fork successful</source>
        <translation>Fork 成功</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>「{0}」已添加到您的收藏。</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Fork failed</source>
        <translation>Fork 失败</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>无法将共享收藏添加到您的项目。</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="468"/>
        <source>Reset to Defaults</source>
        <translation>恢复默认</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Validation Error</source>
        <translation>验证错误</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Please fix the following errors:

</source>
        <translation>请修复以下错误：

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset Configuration</source>
        <translation>重置配置</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset all values to defaults?</source>
        <translation>将所有值重置为默认值？</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="151"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - PostgreSQL 类型警告</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="155"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>过滤器中的类型不匹配：{warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="568"/>
        <source>Reset to Defaults</source>
        <translation>恢复默认</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="588"/>
        <source>General</source>
        <translation>常规</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="268"/>
        <source>{count} features visible in main layer</source>
        <translation>主图层中可见 {count} 个要素</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="261"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>所有过滤器已清除 - 主图层中可见 {count} 个要素</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="291"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>过滤器已应用到 &apos;{layer_name}&apos;：{count} 个要素</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="296"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="312"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>&apos;{layer_name}&apos; 的过滤器已清除：{count} 个要素可见</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="909"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>未选择实体！选择部件丢失了要素。请重新选择一个实体。</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1027"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>所选图层无效或找不到其数据源。操作已取消。</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1042"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>图层 &apos;{0}&apos; 尚未初始化。请尝试选择另一个图层，然后再切换回来。</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="178"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>无法撤消：图层无效或未找到数据源。</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="255"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>无法重做：图层无效或未找到数据源。</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="556"/>
        <source>Explore ...</source>
        <translation>浏览...</translation>
    </message>
</context>
<context>
    <name>self.dockwidget</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="664"/>
        <source>Language changed to &apos;{0}&apos;.</source>
        <translation type="obsolete">Language changed to &apos;{0}&apos;.</translation>
    </message>
</context>
</TS>
