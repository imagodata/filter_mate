<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="ru_RU" sourcelanguage="en_US">
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="171"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Очищены поврежденные фильтры из {0} слоя(ёв). Пожалуйста, примените фильтры заново.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="240"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Обнаружен пустой проект. Добавьте векторные слои для активации плагина.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="307"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>Невозможно получить доступ к базе данных FilterMate. Проверьте права доступа к каталогу проекта.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="321"/>
        <source>Error during database verification: {0}</source>
        <translation>Ошибка при проверке базы данных: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="617"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Загрузка слоя не удалась. Используйте F5 для принудительной перезагрузки.</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="183"/>
        <source>Select Backend:</source>
        <translation>Выберите бэкенд:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="202"/>
        <source>Auto (Default)</source>
        <translation>Авто (По умолчанию)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="210"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Автоматический выбор оптимального для всех слоёв</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="220"/>
        <source>Force {0} for All Layers</source>
        <translation>Принудительно {0} для всех слоёв</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="263"/>
        <source>Click to reload layers</source>
        <translation>Нажмите для перезагрузки слоёв</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="298"/>
        <source>Click to change backend</source>
        <translation>Нажмите для смены бэкенда</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="350"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Ошибка при отмене изменений: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="612"/>
        <source>Property error: {0}</source>
        <translation>Ошибка свойства: {0}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="131"/>
        <source>Database file does not exist: {0}</source>
        <translation>Файл базы данных не существует: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="138"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Не удалось подключиться к базе данных {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="157"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Не удалось создать каталог базы данных {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="211"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Не удалось создать файл базы данных {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="488"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>Невозможно инициализировать базу данных FilterMate: соединение не удалось</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="493"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Критическая ошибка подключения к базе данных: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="527"/>
        <source>Error during database initialization: {0}</source>
        <translation>Ошибка при инициализации базы данных: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="146"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Файл базы данных не существует: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="157"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Не удалось подключиться к базе данных {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Модуль QGIS Processing недоступен для создания пространственного индекса</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="188"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Невозможно создать пространственный индекс: слой недействителен или источник не найден.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="398"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>Обнаружены слои PostgreSQL, но psycopg2 не установлен. Используется локальный бэкенд Spatialite. Для повышения производительности с большими наборами данных установите psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Сохранить слой в файл</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Выберите папку для экспорта слоёв</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="158"/>
        <source>Save your exported data to a zip file</source>
        <translation>Сохранить экспортированные данные в zip-файл</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="116"/>
        <source>{0} couche(s)</source>
        <translation>{0} слой(ёв)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="118"/>
        <source> dans {0} groupe(s)</source>
        <translation> в {0} группе(ах)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="120"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} вне группы</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="127"/>
        <source>Destination : {0}</source>
        <translation>Назначение: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="147"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Группы не обнаружены — все слои на корневом уровне</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="155"/>
        <source>Annuler</source>
        <translation>Отмена</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="161"/>
        <source>Exporter</source>
        <translation>Экспортировать</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation>Нет фильтра</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No active filter to save.</source>
        <translation>Нет активного фильтра для сохранения.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Add Favorite</source>
        <translation>Добавить в избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Favorite name:</source>
        <translation>Имя избранного:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="254"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Избранное &apos;{0}&apos; успешно добавлено</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="399"/>
        <source>Export Favorites</source>
        <translation>Экспорт избранного</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="423"/>
        <source>Exported {0} favorites</source>
        <translation>Экспортировано {0} избранных</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="425"/>
        <source>Failed to export favorites</source>
        <translation>Не удалось экспортировать избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Import Favorites</source>
        <translation>Импорт избранного</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Объединить с существующими избранными?

Да = Добавить к существующим
Нет = Заменить все существующие</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="493"/>
        <source>Imported {0} favorites</source>
        <translation>Импортировано {0} избранных</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="495"/>
        <source>No favorites imported</source>
        <translation>Избранные не импортированы</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="504"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Менеджер избранного не инициализирован. Пожалуйста, перезапустите FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="538"/>
        <source>Favorites manager dialog not available</source>
        <translation>Диалог менеджера избранного недоступен</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1779"/>
        <source>Error: {0}</source>
        <translation>Ошибка: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation>Использовано {0} раз</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation>Добавить текущий фильтр в избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation>Добавить фильтр (нет активного фильтра)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation>Управление избранным...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation>Экспорт...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation>Импорт...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation>Глобальное избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation>Копировать в глобальное...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation>── Доступное глобальное избранное ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation>(Нет глобального избранного)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation>Обслуживание</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation>Сохранить в проект (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation>Восстановить из проекта</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation>Очистить осиротевшие проекты</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation>Статистика базы данных</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation>Недопустимое имя</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Favorite name cannot be empty.</source>
        <translation>Имя избранного не может быть пустым.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>Duplicate Name</source>
        <translation>Дублирующееся имя</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Избранное с именем &apos;{0}&apos; уже существует.
Вы хотите заменить его?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1555"/>
        <source>Favorite copied to global favorites</source>
        <translation>Избранное скопировано в глобальное избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1558"/>
        <source>Failed to copy to global favorites</source>
        <translation>Не удалось скопировать в глобальное избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>Global Favorites</source>
        <translation>Глобальное избранное</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation>{0} глобальных избранных доступно.

Глобальное избранное используется совместно во всех проектах.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1581"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>Сохранено {0} избранных в файл проекта</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1583"/>
        <source>Save failed</source>
        <translation>Сохранение не удалось</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1595"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>Восстановлено {0} избранных из файла проекта</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1597"/>
        <source>No favorites to restore found in project</source>
        <translation>В проекте не найдено избранных для восстановления</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1624"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>Очищено {0} осиротевших проектов</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1626"/>
        <source>No orphan projects to clean up</source>
        <translation>Нет осиротевших проектов для очистки</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1751"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>Статистика базы данных FilterMate

Всего избранных: {0}
   Проект: {1}
   Осиротевшие: {2}
   Глобальные: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1767"/>
        <source>Top projects by favorites:</source>
        <translation>Лучшие проекты по избранным:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1771"/>
        <source>FilterMate Statistics</source>
        <translation>Статистика FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation>Менеджер избранного</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Избранное пока не сохранено.

Примените фильтр к слою, нажмите индикатор ★ и выберите «Добавить текущий фильтр в избранное», чтобы сохранить первое избранное.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation>Импорт из Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Опубликовать в Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation>Опубликовать (нет сохранённого избранного)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1734"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>Каталог конфигурации FilterMate ещё не инициализирован — сначала откройте проект QGIS с FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1692"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation>Расширение Resource Sharing не активно. Включите &apos;favorites_sharing&apos; в настройках FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1700"/>
        <source>Shared favorites service is not available.</source>
        <translation>Служба общего избранного недоступна.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1686"/>
        <source>Shared picker failed: {0}</source>
        <translation>Ошибка выбора общего избранного: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1704"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation>У вас пока нет избранного для публикации. Сначала сохраните фильтр через меню ★.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1720"/>
        <source>Publish dialog failed: {0}</source>
        <translation>Ошибка открытия диалога публикации: {0}</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="118"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Менеджер избранного</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="946"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Сохранённые избранные ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="180"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Поиск по имени, выражению, тегам или описанию...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="444"/>
        <source>General</source>
        <translation>Общие</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Expression</source>
        <translation>Выражение</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="697"/>
        <source>Remote</source>
        <translation>Удалённые</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="466"/>
        <source>Favorite name</source>
        <translation>Имя избранного</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="467"/>
        <source>Name:</source>
        <translation>Имя:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="471"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Описание (автоматически сгенерировано, редактируемое)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="472"/>
        <source>Description:</source>
        <translation>Описание:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="475"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Введите теги через запятую (например, urban, population, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="478"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Теги помогают организовать и искать избранное.
Разделяйте несколько тегов запятыми.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="481"/>
        <source>Tags:</source>
        <translation>Теги:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="486"/>
        <source>Source Layer:</source>
        <translation>Исходный слой:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="490"/>
        <source>Provider:</source>
        <translation>Провайдер:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="498"/>
        <source>Used:</source>
        <translation>Использовано:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="501"/>
        <source>Created:</source>
        <translation>Создано:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="514"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Выражение исходного слоя:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="518"/>
        <source>Filter expression for source layer</source>
        <translation>Выражение фильтра для исходного слоя</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="533"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Отфильтрованные удалённые слои:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Layer</source>
        <translation>Слой</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Features</source>
        <translation>Объекты</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="545"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Нет удалённых слоёв в этом избранном&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="558"/>
        <source>Apply</source>
        <translation>Применить</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="561"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Применить этот избранный фильтр к проекту</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="564"/>
        <source>Save Changes</source>
        <translation>Сохранить изменения</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="567"/>
        <source>Save modifications to this favorite</source>
        <translation>Сохранить изменения в этом избранном</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="570"/>
        <source>Delete</source>
        <translation>Удалить</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="573"/>
        <source>Permanently delete this favorite</source>
        <translation>Навсегда удалить это избранное</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Close</source>
        <translation>Закрыть</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="578"/>
        <source>Close this dialog</source>
        <translation>Закрыть этот диалог</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Избранное ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="691"/>
        <source>Remote ({0})</source>
        <translation>Удалённые ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Delete Favorite</source>
        <translation>Удалить избранное</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="774"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Удалить избранное &apos;{0}&apos;?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="870"/>
        <source>Remote Layers</source>
        <translation>Удалённые слои</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="942"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Сохранённые избранные (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>Favorites Manager</source>
        <translation>Менеджер избранного</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>No favorites saved yet.

Click the ★ indicator and select &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Избранных ещё нет.

Нажмите на индикатор ★ и выберите &apos;Добавить текущий фильтр в избранное&apos;, чтобы сохранить первое избранное.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="146"/>
        <source>Shared...</source>
        <translation>Общие…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="148"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Просмотр избранного, общего через коллекции QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="158"/>
        <source>Publish...</source>
        <translation>Опубликовать…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="160"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Опубликовать выбранное избранное в коллекцию Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Could not delete &apos;{0}&apos;. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation>Не удалось удалить «{0}». Избранное всё ещё в базе данных — подробности в журнале FilterMate.</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="588"/>
        <source>View</source>
        <translation>Просмотр</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="590"/>
        <source>Change</source>
        <translation>Изменить</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="601"/>
        <source>Select a folder</source>
        <translation>Выберите папку</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="608"/>
        <source>Select a file</source>
        <translation>Выберите файл</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="616"/>
        <source>Save to a file</source>
        <translation>Сохранить в файл</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="648"/>
        <source>View</source>
        <translation>Просмотр</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="650"/>
        <source>Change</source>
        <translation>Изменить</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="659"/>
        <source>Select an icon</source>
        <translation>Выберите значок</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Слой недействителен или его источник не найден. Операция отменена.</translation>
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
        <translation>Открыть панель FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset configuration and database</source>
        <translation>Сбросить конфигурацию и базу данных</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Восстановить конфигурацию по умолчанию и удалить базу данных SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Reset Configuration</source>
        <translation>Сбросить конфигурацию</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1357"/>
        <source>Configuration reset successfully.</source>
        <translation>Конфигурация успешно сброшена.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1362"/>
        <source>Default configuration file not found.</source>
        <translation>Файл конфигурации по умолчанию не найден.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1383"/>
        <source>Database deleted: {filename}</source>
        <translation>База данных удалена: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>Restart required</source>
        <translation>Требуется перезапуск</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="403"/>
        <source>Obsolete configuration detected</source>
        <translation>Обнаружена устаревшая конфигурация</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="404"/>
        <source>unknown version</source>
        <translation>неизвестная версия</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="412"/>
        <source>Corrupted configuration detected</source>
        <translation>Обнаружена повреждённая конфигурация</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="469"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Конфигурация не сброшена. Некоторые функции могут работать некорректно.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>Configuration created with default values</source>
        <translation>Конфигурация создана со значениями по умолчанию</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="483"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Повреждённая конфигурация сброшена. Настройки по умолчанию восстановлены.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="486"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Устаревшая конфигурация сброшена. Настройки по умолчанию восстановлены.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="507"/>
        <source>Configuration updated to latest version</source>
        <translation>Конфигурация обновлена до последней версии</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="504"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Конфигурация обновлена: доступны новые настройки ({sections}). Доступ через меню Опции.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="498"/>
        <source>Geometry Simplification</source>
        <translation>Упрощение геометрии</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="499"/>
        <source>Optimization Thresholds</source>
        <translation>Пороги оптимизации</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="644"/>
        <source>Geometry validation setting</source>
        <translation>Настройка проверки геометрии</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="674"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Фильтрация недопустимых геометрий успешно отключена.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="681"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Фильтрация недопустимых геометрий не изменена. Некоторые объекты могут быть исключены из экспорта.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="405"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Обнаружена устаревшая конфигурация ({}).

Хотите сбросить настройки по умолчанию?

• Да: Сбросить (будет создана резервная копия)
• Нет: Сохранить текущую конфигурацию (может вызвать проблемы)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="413"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>Файл конфигурации поврежден и не может быть прочитан.

Хотите сбросить настройки по умолчанию?

• Да: Сбросить (будет создана резервная копия, если возможно)
• Нет: Отмена (плагин может работать некорректно)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="420"/>
        <source>Configuration reset</source>
        <translation>Сброс конфигурации</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="421"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>Конфигурация требует сброса.

Хотите продолжить?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="526"/>
        <source>Error during configuration migration: {}</source>
        <translation>Ошибка при миграции конфигурации: {}</translation>
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
        <translation>Вы уверены, что хотите сбросить конфигурацию по умолчанию?

Это:
- Восстановит настройки по умолчанию
- Удалит базу данных слоев

QGIS должен быть перезапущен для применения изменений.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>Конфигурация была сброшена.

Перезапустите QGIS для применения изменений.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="348"/>
        <source>Initialization error: {0}</source>
        <translation>Ошибка инициализации: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="585"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} ссылающихся слоёв не загружено ({layers_list}). Используется резервное отображение.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1388"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Невозможно удалить {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation>Ошибка при сбросе: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1438"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style=&apos;font-size:13px;&apos;&gt;Спасибо за использование &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Присоединяйтесь к нашему сообществу Discord, чтобы:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Получить помощь и поддержку&lt;/li&gt;&lt;li&gt;Сообщить об ошибках и проблемах&lt;/li&gt;&lt;li&gt;Предложить новые функции&lt;/li&gt;&lt;li&gt;Поделиться советами с другими пользователями&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1454"/>
        <source>  Join us on Discord</source>
        <translation>  Присоединяйтесь к нам в Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1474"/>
        <source>Don&apos;t show this again</source>
        <translation>Больше не показывать</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1477"/>
        <source>Close</source>
        <translation>Закрыть</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1543"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Ошибка загрузки плагина: {0}. Проверьте консоль Python QGIS для получения подробностей.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6711"/>
        <source>Current layer: {0}</source>
        <translation>Текущий слой: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6713"/>
        <source>No layer selected</source>
        <translation>Слой не выбран</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Selected layers:
{0}</source>
        <translation>Выбранные слои:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>No layers selected</source>
        <translation>Слои не выбраны</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6743"/>
        <source>No expression defined</source>
        <translation>Выражение не задано</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6755"/>
        <source>Display expression: {0}</source>
        <translation>Выражение отображения: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6770"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>ID объекта: {0}
Первый атрибут: {1}</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="274"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>Обнаружены слои PostgreSQL ({0}), но psycopg2 не установлен.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="361"/>
        <source>Cleared {0} caches</source>
        <translation>Очищено {0} кэшей</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="795"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Не удалось создать панель: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="805"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Не удалось отобразить панель: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1255"/>
        <source>Error executing {0}: {1}</source>
        <translation>Ошибка выполнения {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1267"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Плагин работает в ограниченном режиме (гексагональные сервисы недоступны). Производительность может быть снижена.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>FilterMate ERROR</source>
        <translation>Ошибка FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Невозможно выполнить {0}: инициализация виджета не удалась.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2167"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Невозможно {0}: слой недействителен или источник не найден.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2304"/>
        <source>All filters cleared - </source>
        <translation>Все фильтры очищены — </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2305"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} объектов видимых в основном слое</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2311"/>
        <source>Error: result handler missing</source>
        <translation>Ошибка: отсутствует обработчик результата</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2324"/>
        <source>Error during filtering: {0}</source>
        <translation>Ошибка при фильтрации: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2455"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>Восстановлено {0} осиротевших избранных: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2591"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Загрузка слоя не удалась — нажмите для повтора</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} слоёв загружено успешно</translation>
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
        <translation>Отмена</translation>
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
        <translation>Ошибка инициализации: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="925"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Конфигурация интерфейса не завершена — проверьте логи</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation>Ошибка размеров интерфейса: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1355"/>
        <source>Favorites manager not available</source>
        <translation>Менеджер избранного недоступен</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1374"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} избранных сохранено
Нажмите, чтобы применить или управлять</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1382"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Нет сохранённых избранных
Нажмите, чтобы добавить текущий фильтр</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1406"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>Принудительно установлен бэкенд {0} для {1} слоёв</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1492"/>
        <source>Backend controller not available</source>
        <translation>Контроллер бэкенда недоступен</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1430"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>Автоочистка PostgreSQL включена</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1431"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>Автоочистка PostgreSQL отключена</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>Представления сессии PostgreSQL очищены</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Нет представлений для очистки или очистка не удалась</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1448"/>
        <source>No PostgreSQL connection available</source>
        <translation>Нет доступного подключения PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1454"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>Схема содержит {0} представлений из других сессий.
Всё равно удалить?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1455"/>
        <source>Other Sessions Active</source>
        <translation>Другие сессии активны</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1457"/>
        <source>Schema cleanup cancelled</source>
        <translation>Очистка схемы отменена</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1462"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Схема &apos;{0}&apos; успешно удалена</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1464"/>
        <source>Schema cleanup failed</source>
        <translation>Очистка схемы не удалась</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1490"/>
        <source>PostgreSQL Session Info</source>
        <translation>Информация о сессии PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Theme adapted: {0}</source>
        <translation>Тема адаптирована: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Dark mode</source>
        <translation>Тёмный режим</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Light mode</source>
        <translation>Светлый режим</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3896"/>
        <source>Selected features have no geometry.</source>
        <translation>Выбранные объекты не имеют геометрии.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3915"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Объект не выбран. Выберите объект из выпадающего списка.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4957"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>Выбранный слой недействителен или его источник не найден.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5667"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Отрицательный буфер (эрозия): сужает полигоны внутрь</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5670"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Значение буфера в метрах (положительное=расширить, отрицательное=сузить полигоны)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6144"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Плагин активирован с {0} векторными слоями</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6227"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Не удалось автоматически перезагрузить плагин.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6229"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Ошибка при перезагрузке плагина: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6282"/>
        <source>Layer properties reset to defaults</source>
        <translation>Свойства слоя сброшены к значениям по умолчанию</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6283"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Ошибка сброса свойств слоя: {}</translation>
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
        <translation>ОДИНОЧНЫЙ ВЫБОР</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="953"/>
        <source>MULTIPLE SELECTION</source>
        <translation>МНОЖЕСТВЕННЫЙ ВЫБОР</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1112"/>
        <source>CUSTOM SELECTION</source>
        <translation>ПОЛЬЗОВАТЕЛЬСКИЙ ВЫБОР</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1374"/>
        <source>FILTERING</source>
        <translation>ФИЛЬТРАЦИЯ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2647"/>
        <source>EXPORTING</source>
        <translation>ЭКСПОРТ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3479"/>
        <source>CONFIGURATION</source>
        <translation>КОНФИГУРАЦИЯ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3225"/>
        <source>Select CRS for export</source>
        <translation>Выбрать систему координат для экспорта</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3747"/>
        <source>Export</source>
        <translation>Экспорт</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2333"/>
        <source>AND</source>
        <translation>И</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2338"/>
        <source>AND NOT</source>
        <translation>И НЕ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2343"/>
        <source>OR</source>
        <translation>ИЛИ</translation>
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
        <translation> м</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2409"/>
        <source>, </source>
        <translation>, </translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1574"/>
        <source>Multi-layer filtering</source>
        <translation>Многослойная фильтрация</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1661"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Аддитивная фильтрация для выбранного слоя</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1947"/>
        <source>Geospatial filtering</source>
        <translation>Геопространственная фильтрация</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2037"/>
        <source>Buffer</source>
        <translation>Буфер</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2282"/>
        <source>Expression layer</source>
        <translation>Слой выражения</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2394"/>
        <source>Geometric predicate</source>
        <translation>Геометрический предикат</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3325"/>
        <source>Output format</source>
        <translation>Выходной формат</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3583"/>
        <source>Filter</source>
        <translation>Фильтр</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3645"/>
        <source>Reset</source>
        <translation>Сбросить</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2751"/>
        <source>Layers to export</source>
        <translation>Слои для экспорта</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2832"/>
        <source>Layers projection</source>
        <translation>Проекция слоёв</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2916"/>
        <source>Save styles</source>
        <translation>Сохранить стили</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2997"/>
        <source>Datatype export</source>
        <translation>Экспорт типа данных</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3078"/>
        <source>Name of file/directory</source>
        <translation>Имя файла/каталога</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2205"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Использовать центроиды вместо полных геометрий для исходного слоя (быстрее для сложных полигонов)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2521"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Значение буфера в метрах (положительное=расширить, отрицательное=сузить полигоны)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2609"/>
        <source>Number of segments for buffer precision</source>
        <translation>Количество сегментов для точности буфера</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3421"/>
        <source>Mode batch</source>
        <translation>Пакетный режим</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="281"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} объектов видимых в основном слое</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="274"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Все фильтры очищены — {count} объектов видимых в основном слое</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="347"/>
        <source>Task failed</source>
        <translation>Задача не выполнена</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="348"/>
        <source>Filter failed for: {0}</source>
        <translation>Фильтр не удался для: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="352"/>
        <source> (+{0} more)</source>
        <translation> (+ещё {0})</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="399"/>
        <source>Layer(s) filtered</source>
        <translation>Слои отфильтрованы</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="403"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Слои отфильтрованы до предыдущего состояния</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="407"/>
        <source>Layer(s) unfiltered</source>
        <translation>Фильтры слоёв сняты</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="411"/>
        <source>Filter task : {0}</source>
        <translation>Задача фильтрации: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="432"/>
        <source>Export task : {0}</source>
        <translation>Задача экспорта: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="457"/>
        <source>Exception: {0}</source>
        <translation>Исключение: {0}</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Меню и панели инструментов Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Свойство</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Значение</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Свойство</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Значение</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="212"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>Обнаружены слои PostgreSQL ({0}), но psycopg2 не установлен. Плагин не может использовать эти слои. Установите psycopg2 для включения поддержки PostgreSQL.</translation>
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
        <translation>Слой PostgreSQL &apos;{0}&apos;: Обнаружены повреждённые данные.

Этот слой использует &apos;virtual_id&apos;, который не существует в PostgreSQL.
Эта ошибка связана с предыдущей версией FilterMate.

Решение: Удалите этот слой из проекта FilterMate, затем добавьте его снова.
Убедитесь, что таблица PostgreSQL имеет определённый PRIMARY KEY.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="970"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>Слой &apos;{0}&apos; не имеет PRIMARY KEY. Ограниченные функции: материализованные представления отключены. Рекомендация: добавьте PRIMARY KEY для оптимальной производительности.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1909"/>
        <source>Exception: {0}</source>
        <translation>Исключение: {0}</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Настройки оптимизации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Настроить параметры оптимизации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Включить автоматическую оптимизацию</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Спрашивать перед применением оптимизаций</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Настройки авто-центроида</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Включить авто-центроид для удалённых слоёв</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Порог расстояния (км):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Порог объектов:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Оптимизации буфера</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Упростить геометрию перед буфером</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Сократить сегменты буфера до:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Общие</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Использовать материализованные представления для фильтрации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Автоматически создавать пространственные индексы</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Использовать пространственный индекс R-дерева</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Использовать предварительный фильтр по ограничивающей рамке</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Бэкенды</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Кэширование</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Включить кэш геометрии</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Пакетная обработка</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Размер пакета:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Расширенные настройки влияют на производительность и использование памяти. Изменяйте только если понимаете последствия.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Расширенные</translation>
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
        <translation>Информация о сеансе PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL активен</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Информация о подключении</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Подключение:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Временная схема:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Статус:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Временные представления</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Параметры очистки</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Автоочистка при закрытии</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Автоматически очищать временные представления при закрытии FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Очистить сейчас</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Удалить все временные представления, созданные FilterMate в этом сеансе.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Нет временных представлений)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Нет представлений</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Нет временных представлений для очистки.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Подтвердить очистку</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Очистка завершена</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Проблема очистки</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Ошибка очистки</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL недоступен&lt;/b&gt;&lt;br&gt;&lt;br&gt;Для использования функций PostgreSQL установите psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Затем перезапустите QGIS для применения изменений.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Сессия: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} представлений в этой сессии</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Будет удалено {view_count} временных представлений, созданных FilterMate.

Все несохранённые результаты фильтрации будут потеряны.

Продолжить?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>Удалено {result.views_dropped} временных представлений.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Некоторые представления не удалось удалить: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Ошибка при очистке: {str(e)}</translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="125"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — Публикация в Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="133"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Опубликовать избранное&lt;/b&gt; — записать общий пакет в коллекцию QGIS Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="153"/>
        <source>Overwrite existing bundle</source>
        <translation>Перезаписать существующий пакет</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="163"/>
        <source>Publish</source>
        <translation>Опубликовать</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="177"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Целевая коллекция&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="190"/>
        <source>Browse...</source>
        <translation>Обзор…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="198"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Имя файла пакета&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="200"/>
        <source>e.g. zones_bruxelles</source>
        <translation>напр. зоны_брюссель</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="203"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;цель&amp;gt;/filter_mate/favorites/&amp;lt;имя&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Метаданные коллекции&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="214"/>
        <source>Collection display name</source>
        <translation>Отображаемое имя коллекции</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="215"/>
        <source>Name:</source>
        <translation>Имя:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="218"/>
        <source>Author / organisation</source>
        <translation>Автор / организация</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="219"/>
        <source>Author:</source>
        <translation>Автор:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="222"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>напр. CC-BY-4.0, MIT, Проприетарная</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="223"/>
        <source>License:</source>
        <translation>Лицензия:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="226"/>
        <source>Comma-separated tags</source>
        <translation>Теги через запятую</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="227"/>
        <source>Tags:</source>
        <translation>Теги:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="230"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="231"/>
        <source>Homepage:</source>
        <translation>Веб-сайт:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="235"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Краткое описание (необязательно, обычный текст)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="238"/>
        <source>Description:</source>
        <translation>Описание:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="250"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Избранное для включения&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="254"/>
        <source>Select all</source>
        <translation>Выбрать всё</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="257"/>
        <source>Select none</source>
        <translation>Снять выбор</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="284"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Новая коллекция в корне Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="288"/>
        <source>Custom directory...</source>
        <translation>Пользовательский каталог…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="340"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Будет создано в корне Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="345"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Нажмите &apos;Обзор…&apos;, чтобы выбрать каталог.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="351"/>
        <source>Choose a collection directory</source>
        <translation>Выберите каталог коллекции</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="402"/>
        <source>{0} / {1} selected</source>
        <translation>Выбрано: {0} / {1}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Cannot create collection</source>
        <translation>Невозможно создать коллекцию</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Корень Resource Sharing не найден. Используйте &apos;Обзор…&apos; для выбора каталога.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Choose a directory</source>
        <translation>Выберите каталог</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Нажмите &apos;Обзор…&apos;, чтобы выбрать целевой каталог.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>No favorites selected</source>
        <translation>Избранное не выбрано</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Выберите хотя бы одно избранное для публикации.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Publish failed</source>
        <translation>Публикация не удалась</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Unknown error.</source>
        <translation>Неизвестная ошибка.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="505"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>Опубликовано {0} избранных в:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="509"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Манифест коллекции обновлён:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="512"/>
        <source>Publish succeeded</source>
        <translation>Публикация успешна</translation>
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
        <translation>Описание:</translation>
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
        <translation>Слой</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="178"/>
        <source>Export</source>
        <translation>Экспорт</translation>
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
        <translation>Ошибка: {0}</translation>
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
        <translation>Статус:</translation>
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
        <translation>Введите для фильтрации...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="661"/>
        <source>Select All</source>
        <translation>Выбрать всё</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="663"/>
        <source>Select All (non subset)</source>
        <translation>Выбрать всё (вне подмножества)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="665"/>
        <source>Select All (subset)</source>
        <translation>Выбрать всё (подмножество)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="667"/>
        <source>De-select All</source>
        <translation>Снять выбор со всего</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="669"/>
        <source>De-select All (non subset)</source>
        <translation>Снять выбор со всего (вне подмножества)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="671"/>
        <source>De-select All (subset)</source>
        <translation>Снять выбор со всего (подмножество)</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="220"/>
        <source>Select All</source>
        <translation>Выбрать всё</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="222"/>
        <source>De-select All</source>
        <translation>Снять выбор со всего</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="224"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Выбрать все слои по типу геометрии (Линии)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="226"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Снять выбор со всех слоёв по типу геометрии (Линии)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="228"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Выбрать все слои по типу геометрии (Точки)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="230"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Снять выбор со всех слоёв по типу геометрии (Точки)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="232"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Выбрать все слои по типу геометрии (Полигоны)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="234"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Снять выбор со всех слоёв по типу геометрии (Полигоны)</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Применить оптимизации?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Доступные оптимизации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Пропустить</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Применить выбранное</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} объектов</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Влияние: {0}</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="75"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Поиск в конфигурации... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="180"/>
        <source>No match</source>
        <translation>Нет совпадений</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="55"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Общее избранное</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="63"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Общее избранное&lt;/b&gt; — обнаруженное в коллекциях QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation>Поиск по имени, описанию, коллекции или тегам…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="98"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Выберите общее избранное для предпросмотра.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="114"/>
        <source>Rescan</source>
        <translation>Пересканировать</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="118"/>
        <source>Fork to my project</source>
        <translation>Форк в мой проект</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="124"/>
        <source>Close</source>
        <translation>Закрыть</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="139"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Общие коллекции не найдены. Подпишитесь на репозиторий Resource Sharing с папкой &lt;code&gt;filter_mate/favorites&lt;/code&gt; или поместите пакет &lt;code&gt;.fmfav.json&lt;/code&gt; в каталог коллекций resource_sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="147"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} избранных в {1} коллекциях: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="160"/>
        <source>Collection: {0}</source>
        <translation>Коллекция: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation>Нет общего избранного, соответствующего поиску.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="194"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — из &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="208"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Выражение&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="213"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Удалённые слои&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="227"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Теги:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="234"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Происхождение&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="236"/>
        <source>Author: {0}</source>
        <translation>Автор: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="238"/>
        <source>License: {0}</source>
        <translation>Лицензия: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Fork shared favorite</source>
        <translation>Форк общего избранного</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Name in your project:</source>
        <translation>Имя в вашем проекте:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>Fork successful</source>
        <translation>Форк успешен</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» добавлено в избранное.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Fork failed</source>
        <translation>Форк не удался</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Не удалось добавить общее избранное в проект.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="468"/>
        <source>Reset to Defaults</source>
        <translation>Сбросить к значениям по умолчанию</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Validation Error</source>
        <translation>Ошибка валидации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Please fix the following errors:

</source>
        <translation>Пожалуйста, исправьте следующие ошибки:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset Configuration</source>
        <translation>Сброс конфигурации</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset all values to defaults?</source>
        <translation>Сбросить все значения к значениям по умолчанию?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="151"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate — Предупреждение о типе PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="155"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Несоответствие типов в фильтре: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="568"/>
        <source>Reset to Defaults</source>
        <translation>Сбросить к значениям по умолчанию</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="588"/>
        <source>General</source>
        <translation>Общие</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="268"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} объектов видимых в основном слое</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="261"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Все фильтры очищены — {count} объектов видимых в основном слое</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="291"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Фильтр применён к &apos;{layer_name}&apos;: {count} объектов</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="296"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="312"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Фильтр снят для &apos;{layer_name}&apos;: {count} видимых объектов</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="909"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Объект не выбран! Виджет выбора потерял объект. Выберите объект повторно.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1027"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Выбранный слой недействителен или его источник не найден. Операция отменена.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1042"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>Слой &apos;{0}&apos; ещё не инициализирован. Попробуйте выбрать другой слой, затем вернитесь к этому.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="178"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Невозможно отменить: слой недействителен или источник не найден.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="255"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Невозможно повторить: слой недействителен или источник не найден.</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="556"/>
        <source>Explore ...</source>
        <translation>Обзор ...</translation>
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
