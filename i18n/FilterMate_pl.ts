<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pl_PL" sourcelanguage="en_US">
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="171"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Usunięto uszkodzone filtry z {0} warstw(y). Proszę ponownie zastosować filtry.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="240"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Wykryto pusty projekt. Dodaj warstwy wektorowe, aby aktywować wtyczkę.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="307"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>Nie można uzyskać dostępu do bazy danych FilterMate. Sprawdź uprawnienia katalogu projektu.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="321"/>
        <source>Error during database verification: {0}</source>
        <translation>Błąd podczas weryfikacji bazy danych: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="617"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Ładowanie warstwy nie powiodło się. Użyj F5, aby wymusić przeładowanie.</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="183"/>
        <source>Select Backend:</source>
        <translation>Wybierz backend:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="202"/>
        <source>Auto (Default)</source>
        <translation>Auto (Domyślny)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="210"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Automatycznie wybierz optymalny dla wszystkich warstw</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="220"/>
        <source>Force {0} for All Layers</source>
        <translation>Wymuś {0} dla wszystkich warstw</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="263"/>
        <source>Click to reload layers</source>
        <translation>Kliknij, aby przeładować warstwy</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="298"/>
        <source>Click to change backend</source>
        <translation>Kliknij, aby zmienić backend</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="350"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Błąd podczas anulowania zmian: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="612"/>
        <source>Property error: {0}</source>
        <translation>Błąd właściwości: {0}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="131"/>
        <source>Database file does not exist: {0}</source>
        <translation>Plik bazy danych nie istnieje: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="138"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Nie udało się połączyć z bazą danych {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="157"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Nie można utworzyć katalogu bazy danych {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="211"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Nie udało się utworzyć pliku bazy danych {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="488"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>Nie można zainicjalizować bazy danych FilterMate: połączenie nie powiodło się</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="493"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Błąd krytyczny podczas łączenia z bazą danych: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="527"/>
        <source>Error during database initialization: {0}</source>
        <translation>Błąd podczas inicjalizacji bazy danych: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="146"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Plik bazy danych nie istnieje: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="157"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Nie udało się połączyć z bazą danych {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Moduł QGIS Processing niedostępny do utworzenia indeksu przestrzennego</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="188"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Nie można utworzyć indeksu przestrzennego: warstwa nieprawidłowa lub źródło nieznalezione.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="398"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>Wykryto warstwy PostgreSQL, ale psycopg2 nie jest zainstalowane. Używany jest lokalny backend Spatialite. Aby uzyskać lepszą wydajność dla dużych zbiorów danych, zainstaluj psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Zapisz warstwę do pliku</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Wybierz folder, do którego wyeksportować warstwy</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="158"/>
        <source>Save your exported data to a zip file</source>
        <translation>Zapisz wyeksportowane dane do pliku zip</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="116"/>
        <source>{0} couche(s)</source>
        <translation>{0} warstwa(w)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="118"/>
        <source> dans {0} groupe(s)</source>
        <translation> w {0} grupie(ach)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="120"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} poza grupą</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="127"/>
        <source>Destination : {0}</source>
        <translation>Cel: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="147"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Nie wykryto grupy - wszystkie warstwy są na poziomie głównym</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="155"/>
        <source>Annuler</source>
        <translation>Anuluj</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="161"/>
        <source>Exporter</source>
        <translation>Eksportuj</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation>Brak filtra</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No active filter to save.</source>
        <translation>Brak aktywnego filtra do zapisania.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Add Favorite</source>
        <translation>Dodaj ulubiony</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Favorite name:</source>
        <translation>Nazwa ulubionego:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="254"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Ulubiony &apos;{0}&apos; dodany pomyślnie</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="399"/>
        <source>Export Favorites</source>
        <translation>Eksportuj ulubione</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="423"/>
        <source>Exported {0} favorites</source>
        <translation>Wyeksportowano {0} ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="425"/>
        <source>Failed to export favorites</source>
        <translation>Nie udało się wyeksportować ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Import Favorites</source>
        <translation>Importuj ulubione</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Scalić z istniejącymi ulubionymi?

Tak = Dodaj do istniejących
Nie = Zastąp wszystkie istniejące</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="493"/>
        <source>Imported {0} favorites</source>
        <translation>Zaimportowano {0} ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="495"/>
        <source>No favorites imported</source>
        <translation>Nie zaimportowano żadnych ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="504"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Menedżer ulubionych nie został zainicjalizowany. Proszę zrestartować FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="538"/>
        <source>Favorites manager dialog not available</source>
        <translation>Okno menedżera ulubionych niedostępne</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1779"/>
        <source>Error: {0}</source>
        <translation>Błąd: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation>Użyto {0} razy</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation>Dodaj bieżący filtr do ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation>Dodaj filtr (brak aktywnego filtra)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation>Zarządzaj ulubionymi...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation>Eksportuj...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation>Importuj...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation>Ulubione globalne</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation>Kopiuj do globalnych...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation>── Dostępne ulubione globalne ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation>(Brak ulubionych globalnych)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation>Konserwacja</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation>Zapisz do projektu (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation>Przywróć z projektu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation>Oczyść osierocone projekty</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation>Statystyki bazy danych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation>Nieprawidłowa nazwa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Favorite name cannot be empty.</source>
        <translation>Nazwa ulubionego nie może być pusta.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>Duplicate Name</source>
        <translation>Zduplikowana nazwa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Ulubiony o nazwie &apos;{0}&apos; już istnieje.
Czy chcesz go zastąpić?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1555"/>
        <source>Favorite copied to global favorites</source>
        <translation>Ulubiony skopiowany do ulubionych globalnych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1558"/>
        <source>Failed to copy to global favorites</source>
        <translation>Nie udało się skopiować do ulubionych globalnych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>Global Favorites</source>
        <translation>Ulubione globalne</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation>{0} ulubionych globalnych dostępnych.

Ulubione globalne są współdzielone między wszystkimi projektami.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1581"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>Zapisano {0} ulubionych do pliku projektu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1583"/>
        <source>Save failed</source>
        <translation>Zapis nie powiódł się</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1595"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>Przywrócono {0} ulubionych z pliku projektu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1597"/>
        <source>No favorites to restore found in project</source>
        <translation>Nie znaleziono ulubionych do przywrócenia w projekcie</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1624"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>Oczyszczono {0} osieroconych projektów</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1626"/>
        <source>No orphan projects to clean up</source>
        <translation>Brak osieroconych projektów do oczyszczenia</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1751"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>Statystyki bazy danych FilterMate

Łącznie ulubionych: {0}
   Projekt: {1}
   Osierocone: {2}
   Globalne: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1767"/>
        <source>Top projects by favorites:</source>
        <translation>Najlepsze projekty wg ulubionych:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1771"/>
        <source>FilterMate Statistics</source>
        <translation>Statystyki FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation>Menedżer ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Nie zapisano jeszcze żadnych ulubionych.

Zastosuj filtr do warstwy, a następnie kliknij wskaźnik ★ i wybierz «Dodaj bieżący filtr do ulubionych», aby zapisać pierwszy ulubiony.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation>Importuj z Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Opublikuj w Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation>Opublikuj (brak zapisanych ulubionych)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1734"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>Katalog konfiguracji FilterMate nie został jeszcze zainicjalizowany — otwórz najpierw projekt QGIS z FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1692"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation>Rozszerzenie Resource Sharing nie jest aktywne. Włącz &apos;favorites_sharing&apos; w ustawieniach FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1700"/>
        <source>Shared favorites service is not available.</source>
        <translation>Usługa udostępnionych ulubionych nie jest dostępna.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1686"/>
        <source>Shared picker failed: {0}</source>
        <translation>Selektor udostępnionych ulubionych nie powiódł się: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1704"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation>Nie masz jeszcze ulubionych do opublikowania. Zapisz najpierw filtr przez menu ★.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1720"/>
        <source>Publish dialog failed: {0}</source>
        <translation>Otwarcie okna publikacji nie powiodło się: {0}</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="118"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Menedżer ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="946"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Zapisane ulubione ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="180"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Szukaj po nazwie, wyrażeniu, tagach lub opisie...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="444"/>
        <source>General</source>
        <translation>Ogólne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Expression</source>
        <translation>Wyrażenie</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="697"/>
        <source>Remote</source>
        <translation>Zdalne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="466"/>
        <source>Favorite name</source>
        <translation>Nazwa ulubionego</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="467"/>
        <source>Name:</source>
        <translation>Nazwa:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="471"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Opis (wygenerowany automatycznie, edytowalny)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="472"/>
        <source>Description:</source>
        <translation>Opis:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="475"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Wprowadź tagi oddzielone przecinkami (np. urban, population, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="478"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Tagi pomagają organizować i wyszukiwać ulubione.
Oddziel wiele tagów przecinkami.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="481"/>
        <source>Tags:</source>
        <translation>Tagi:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="486"/>
        <source>Source Layer:</source>
        <translation>Warstwa źródłowa:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="490"/>
        <source>Provider:</source>
        <translation>Dostawca:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="498"/>
        <source>Used:</source>
        <translation>Użyto:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="501"/>
        <source>Created:</source>
        <translation>Utworzono:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="514"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Wyrażenie warstwy źródłowej:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="518"/>
        <source>Filter expression for source layer</source>
        <translation>Wyrażenie filtra dla warstwy źródłowej</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="533"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Przefiltrowane warstwy zdalne:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Layer</source>
        <translation>Warstwa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Features</source>
        <translation>Obiekty</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="545"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Brak warstw zdalnych w tym ulubionym&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="558"/>
        <source>Apply</source>
        <translation>Zastosuj</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="561"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Zastosuj ten ulubiony filtr do projektu</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="564"/>
        <source>Save Changes</source>
        <translation>Zapisz zmiany</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="567"/>
        <source>Save modifications to this favorite</source>
        <translation>Zapisz modyfikacje tego ulubionego</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="570"/>
        <source>Delete</source>
        <translation>Usuń</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="573"/>
        <source>Permanently delete this favorite</source>
        <translation>Trwale usuń ten ulubiony</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Close</source>
        <translation>Zamknij</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="578"/>
        <source>Close this dialog</source>
        <translation>Zamknij to okno</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Ulubione ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="691"/>
        <source>Remote ({0})</source>
        <translation>Zdalne ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Delete Favorite</source>
        <translation>Usuń ulubiony</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="774"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Usunąć ulubiony &apos;{0}&apos;?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="870"/>
        <source>Remote Layers</source>
        <translation>Warstwy zdalne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="942"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Zapisane ulubione (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>Favorites Manager</source>
        <translation>Menedżer ulubionych</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>No favorites saved yet.

Click the ★ indicator and select &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Nie zapisano jeszcze żadnych ulubionych.

Kliknij wskaźnik ★ i wybierz &apos;Dodaj bieżący filtr do ulubionych&apos;, aby zapisać pierwszy ulubiony.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="146"/>
        <source>Shared...</source>
        <translation>Udostępnione…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="148"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Przeglądaj ulubione udostępnione przez kolekcje QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="158"/>
        <source>Publish...</source>
        <translation>Opublikuj…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="160"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Opublikuj wybrane ulubione w kolekcji Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Could not delete &apos;{0}&apos;. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation>Nie można usunąć «{0}». Ulubiony nadal jest w bazie danych — sprawdź dziennik FilterMate.</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="588"/>
        <source>View</source>
        <translation>Podgląd</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="590"/>
        <source>Change</source>
        <translation>Zmień</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="601"/>
        <source>Select a folder</source>
        <translation>Wybierz folder</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="608"/>
        <source>Select a file</source>
        <translation>Wybierz plik</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="616"/>
        <source>Save to a file</source>
        <translation>Zapisz do pliku</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="648"/>
        <source>View</source>
        <translation>Podgląd</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="650"/>
        <source>Change</source>
        <translation>Zmień</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="659"/>
        <source>Select an icon</source>
        <translation>Wybierz ikonę</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Warstwa jest nieprawidłowa lub nie można znaleźć jej źródła. Operacja anulowana.</translation>
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
        <translation>Otwórz panel FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset configuration and database</source>
        <translation>Zresetuj konfigurację i bazę danych</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Przywróć domyślną konfigurację i usuń bazę danych SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Reset Configuration</source>
        <translation>Zresetuj konfigurację</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1357"/>
        <source>Configuration reset successfully.</source>
        <translation>Konfiguracja została pomyślnie zresetowana.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1362"/>
        <source>Default configuration file not found.</source>
        <translation>Nie znaleziono domyślnego pliku konfiguracyjnego.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1383"/>
        <source>Database deleted: {filename}</source>
        <translation>Baza danych usunięta: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>Restart required</source>
        <translation>Wymagane ponowne uruchomienie</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="403"/>
        <source>Obsolete configuration detected</source>
        <translation>Wykryto przestarzałą konfigurację</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="404"/>
        <source>unknown version</source>
        <translation>nieznana wersja</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="412"/>
        <source>Corrupted configuration detected</source>
        <translation>Wykryto uszkodzoną konfigurację</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="469"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Konfiguracja nie została zresetowana. Niektóre funkcje mogą nie działać poprawnie.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>Configuration created with default values</source>
        <translation>Konfiguracja utworzona z wartościami domyślnymi</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="483"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Uszkodzona konfiguracja została zresetowana. Przywrócono ustawienia domyślne.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="486"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Przestarzała konfiguracja została zresetowana. Przywrócono ustawienia domyślne.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="507"/>
        <source>Configuration updated to latest version</source>
        <translation>Konfiguracja zaktualizowana do najnowszej wersji</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="504"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Konfiguracja zaktualizowana: nowe ustawienia dostępne ({sections}). Dostęp przez menu Opcje.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="498"/>
        <source>Geometry Simplification</source>
        <translation>Uproszczenie geometrii</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="499"/>
        <source>Optimization Thresholds</source>
        <translation>Progi optymalizacji</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="644"/>
        <source>Geometry validation setting</source>
        <translation>Ustawienie walidacji geometrii</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="674"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Filtrowanie nieprawidłowych geometrii zostało pomyślnie wyłączone.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="681"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Filtrowanie nieprawidłowych geometrii nie zostało zmienione. Niektóre obiekty mogą zostać wykluczone z eksportu.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="405"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Wykryto przestarzałą konfigurację ({}).

Czy chcesz przywrócić ustawienia domyślne?

• Tak: Przywróć (kopia zapasowa zostanie utworzona)
• Nie: Zachowaj bieżącą konfigurację (może powodować problemy)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="413"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>Plik konfiguracji jest uszkodzony i nie można go odczytać.

Czy chcesz przywrócić ustawienia domyślne?

• Tak: Przywróć (kopia zapasowa zostanie utworzona, jeśli to możliwe)
• Nie: Anuluj (wtyczka może nie działać poprawnie)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="420"/>
        <source>Configuration reset</source>
        <translation>Resetowanie konfiguracji</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="421"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>Konfiguracja wymaga zresetowania.

Czy chcesz kontynuować?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="526"/>
        <source>Error during configuration migration: {}</source>
        <translation>Błąd podczas migracji konfiguracji: {}</translation>
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
        <translation>Czy na pewno chcesz przywrócić domyślną konfigurację?

To:
- Przywróci ustawienia domyślne
- Usunie bazę danych warstw

QGIS musi zostać uruchomiony ponownie, aby zastosować zmiany.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>Konfiguracja została zresetowana.

Uruchom ponownie QGIS, aby zastosować zmiany.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="348"/>
        <source>Initialization error: {0}</source>
        <translation>Błąd inicjalizacji: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="585"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} przywoływanych warstw nie załadowano ({layers_list}). Używany jest wyświetlacz zastępczy.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1388"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Nie można usunąć {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation>Błąd podczas resetowania: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1438"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style=&apos;font-size:13px;&apos;&gt;Dziękujemy za korzystanie z &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Dołącz do naszej społeczności Discord, aby:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Uzyskać pomoc i wsparcie&lt;/li&gt;&lt;li&gt;Zgłaszać błędy i problemy&lt;/li&gt;&lt;li&gt;Proponować nowe funkcje&lt;/li&gt;&lt;li&gt;Dzielić się wskazówkami z innymi użytkownikami&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1454"/>
        <source>  Join us on Discord</source>
        <translation>  Dołącz do nas na Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1474"/>
        <source>Don&apos;t show this again</source>
        <translation>Nie pokazuj ponownie</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1477"/>
        <source>Close</source>
        <translation>Zamknij</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1543"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Błąd ładowania wtyczki: {0}. Sprawdź konsolę Python QGIS, aby uzyskać szczegóły.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6711"/>
        <source>Current layer: {0}</source>
        <translation>Bieżąca warstwa: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6713"/>
        <source>No layer selected</source>
        <translation>Nie wybrano warstwy</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Selected layers:
{0}</source>
        <translation>Wybrane warstwy:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>No layers selected</source>
        <translation>Nie wybrano warstw</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6743"/>
        <source>No expression defined</source>
        <translation>Nie zdefiniowano wyrażenia</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6755"/>
        <source>Display expression: {0}</source>
        <translation>Wyrażenie wyświetlania: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6770"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>ID obiektu: {0}
Pierwszy atrybut: {1}</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="274"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>Wykryto warstwy PostgreSQL ({0}), ale psycopg2 nie jest zainstalowany.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="361"/>
        <source>Cleared {0} caches</source>
        <translation>Wyczyszczono {0} pamięci podręcznych</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="795"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Nie udało się utworzyć panelu dokowanego: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="805"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Nie udało się wyświetlić panelu dokowanego: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1255"/>
        <source>Error executing {0}: {1}</source>
        <translation>Błąd wykonywania {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1267"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Wtyczka działa w trybie awaryjnym (usługi hexagonalne niedostępne). Wydajność może być obniżona.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>FilterMate ERROR</source>
        <translation>Błąd FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Nie można wykonać {0}: inicjalizacja widżetu nie powiodła się.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2167"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Nie można {0}: warstwa nieprawidłowa lub nie znaleziono źródła.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2304"/>
        <source>All filters cleared - </source>
        <translation>Wszystkie filtry wyczyszczone - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2305"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} obiektów widocznych w warstwie głównej</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2311"/>
        <source>Error: result handler missing</source>
        <translation>Błąd: brak procedury obsługi wyniku</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2324"/>
        <source>Error during filtering: {0}</source>
        <translation>Błąd podczas filtrowania: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2455"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>Odzyskano {0} osieroconych ulubionych: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2591"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Ładowanie warstwy nie powiodło się - kliknij, aby ponowić</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} warstw(a) załadowanych pomyślnie</translation>
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
        <translation>Anuluj</translation>
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
        <translation>Błąd inicjalizacji: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="925"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Konfiguracja interfejsu niekompletna - sprawdź logi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation>Błąd wymiarów interfejsu: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1355"/>
        <source>Favorites manager not available</source>
        <translation>Menedżer ulubionych niedostępny</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1374"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} ulubionych zapisanych
Kliknij, aby zastosować lub zarządzać</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1382"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Brak zapisanych ulubionych
Kliknij, aby dodać bieżący filtr</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1406"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>Wymuszono backend {0} dla {1} warstw(y)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1492"/>
        <source>Backend controller not available</source>
        <translation>Kontroler backendu niedostępny</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1430"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>Automatyczne czyszczenie PostgreSQL włączone</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1431"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>Automatyczne czyszczenie PostgreSQL wyłączone</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>Widoki sesji PostgreSQL wyczyszczone</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Brak widoków do wyczyszczenia lub czyszczenie nie powiodło się</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1448"/>
        <source>No PostgreSQL connection available</source>
        <translation>Brak dostępnego połączenia PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1454"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>Schemat ma {0} widok(ów) z innych sesji.
Usunąć mimo to?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1455"/>
        <source>Other Sessions Active</source>
        <translation>Inne sesje aktywne</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1457"/>
        <source>Schema cleanup cancelled</source>
        <translation>Czyszczenie schematu anulowane</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1462"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Schemat &apos;{0}&apos; pomyślnie usunięty</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1464"/>
        <source>Schema cleanup failed</source>
        <translation>Czyszczenie schematu nie powiodło się</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1490"/>
        <source>PostgreSQL Session Info</source>
        <translation>Info sesji PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Theme adapted: {0}</source>
        <translation>Motyw dostosowany: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Dark mode</source>
        <translation>Tryb ciemny</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Light mode</source>
        <translation>Tryb jasny</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3896"/>
        <source>Selected features have no geometry.</source>
        <translation>Wybrane obiekty nie mają geometrii.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3915"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Nie wybrano obiektu. Wybierz obiekt z listy rozwijanej.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4957"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>Wybrana warstwa jest nieprawidłowa lub nie można znaleźć jej źródła.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5667"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Bufor ujemny (erozja): zmniejsza wielokąty do wewnątrz</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5670"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Wartość bufora w metrach (dodatnia=rozszerz, ujemna=zmniejsz wielokąty)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6144"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Wtyczka aktywowana z {0} warstwami wektorowymi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6227"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Nie można automatycznie przeładować wtyczki.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6229"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Błąd podczas przeładowywania wtyczki: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6282"/>
        <source>Layer properties reset to defaults</source>
        <translation>Właściwości warstwy zresetowane do domyślnych</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6283"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Błąd resetowania właściwości warstwy: {}</translation>
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
        <translation>POJEDYNCZY WYBÓR</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="953"/>
        <source>MULTIPLE SELECTION</source>
        <translation>WIELOKROTNY WYBÓR</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1112"/>
        <source>CUSTOM SELECTION</source>
        <translation>NIESTANDARDOWY WYBÓR</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1374"/>
        <source>FILTERING</source>
        <translation>FILTROWANIE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2647"/>
        <source>EXPORTING</source>
        <translation>EKSPORTOWANIE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3479"/>
        <source>CONFIGURATION</source>
        <translation>KONFIGURACJA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3225"/>
        <source>Select CRS for export</source>
        <translation>Wybierz układ współrzędnych do eksportu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3747"/>
        <source>Export</source>
        <translation>Eksportuj</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2333"/>
        <source>AND</source>
        <translation>I</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2338"/>
        <source>AND NOT</source>
        <translation>I NIE</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2343"/>
        <source>OR</source>
        <translation>LUB</translation>
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
        <translation> m</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2409"/>
        <source>, </source>
        <translation>, </translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1574"/>
        <source>Multi-layer filtering</source>
        <translation>Filtrowanie wielowarstwowe</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1661"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Filtrowanie addytywne dla wybranej warstwy</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1947"/>
        <source>Geospatial filtering</source>
        <translation>Filtrowanie geoprzestrzenne</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2037"/>
        <source>Buffer</source>
        <translation>Bufor</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2282"/>
        <source>Expression layer</source>
        <translation>Warstwa wyrażenia</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2394"/>
        <source>Geometric predicate</source>
        <translation>Predykat geometryczny</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3325"/>
        <source>Output format</source>
        <translation>Format wyjściowy</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3583"/>
        <source>Filter</source>
        <translation>Filtr</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3645"/>
        <source>Reset</source>
        <translation>Resetuj</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2751"/>
        <source>Layers to export</source>
        <translation>Warstwy do eksportu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2832"/>
        <source>Layers projection</source>
        <translation>Projekcja warstw</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2916"/>
        <source>Save styles</source>
        <translation>Zapisz style</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2997"/>
        <source>Datatype export</source>
        <translation>Eksport typu danych</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3078"/>
        <source>Name of file/directory</source>
        <translation>Nazwa pliku/katalogu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2205"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Użyj centroidów zamiast pełnych geometrii dla warstwy źródłowej (szybsze dla złożonych wielokątów)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2521"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Wartość bufora w metrach (dodatnia=rozszerz, ujemna=zmniejsz wielokąty)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2609"/>
        <source>Number of segments for buffer precision</source>
        <translation>Liczba segmentów dla precyzji bufora</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3421"/>
        <source>Mode batch</source>
        <translation>Tryb wsadowy</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="281"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} obiektów widocznych w warstwie głównej</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="274"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Wszystkie filtry wyczyszczone - {count} obiektów widocznych w warstwie głównej</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="347"/>
        <source>Task failed</source>
        <translation>Zadanie nie powiodło się</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="348"/>
        <source>Filter failed for: {0}</source>
        <translation>Filtr nie powiódł się dla: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="352"/>
        <source> (+{0} more)</source>
        <translation> (+{0} więcej)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="399"/>
        <source>Layer(s) filtered</source>
        <translation>Warstwy przefiltrowane</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="403"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Warstwy przefiltrowane do poprzedniego stanu</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="407"/>
        <source>Layer(s) unfiltered</source>
        <translation>Warstwy odfiltrowane</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="411"/>
        <source>Filter task : {0}</source>
        <translation>Zadanie filtrowania: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="432"/>
        <source>Export task : {0}</source>
        <translation>Zadanie eksportu: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="457"/>
        <source>Exception: {0}</source>
        <translation>Wyjątek: {0}</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Menu i paski narzędzi Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Właściwość</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Wartość</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Właściwość</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Wartość</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="212"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>Wykryto warstwy PostgreSQL ({0}), ale psycopg2 nie jest zainstalowany. Wtyczka nie może używać tych warstw. Zainstaluj psycopg2, aby włączyć obsługę PostgreSQL.</translation>
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
        <translation>Warstwa PostgreSQL &apos;{0}&apos;: Wykryto uszkodzone dane.

Ta warstwa używa &apos;virtual_id&apos;, który nie istnieje w PostgreSQL.
Ten błąd pochodzi z poprzedniej wersji FilterMate.

Rozwiązanie: Usuń tę warstwę z projektu FilterMate, a następnie dodaj ją ponownie.
Upewnij się, że tabela PostgreSQL ma zdefiniowany PRIMARY KEY.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="970"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>Warstwa &apos;{0}&apos; nie ma PRIMARY KEY. Ograniczone funkcje: widoki zmaterializowane wyłączone. Zalecenie: dodaj PRIMARY KEY dla optymalnej wydajności.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1909"/>
        <source>Exception: {0}</source>
        <translation>Wyjątek: {0}</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Ustawienia optymalizacji</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Skonfiguruj ustawienia optymalizacji</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Włącz automatyczne optymalizacje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Pytaj przed zastosowaniem optymalizacji</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Ustawienia auto-centroidu</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Włącz auto-centroid dla odległych warstw</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Próg odległości (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Próg obiektów:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Optymalizacje bufora</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Uprość geometrię przed buforem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Ogranicz segmenty bufora do:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Ogólne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Użyj zmaterializowanych widoków do filtrowania</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Twórz indeksy przestrzenne automatycznie</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Użyj indeksu przestrzennego R-tree</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Użyj pre-filtra bounding box</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Backendy</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Buforowanie</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Włącz pamięć podręczną geometrii</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Przetwarzanie wsadowe</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Rozmiar paczki:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Zaawansowane ustawienia wpływają na wydajność i użycie pamięci. Zmieniaj tylko jeśli rozumiesz konsekwencje.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Zaawansowane</translation>
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
        <translation>Info sesji PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL aktywny</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Info połączenia</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Połączenie:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Schemat tymczasowy:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Status:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Widoki tymczasowe</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Opcje czyszczenia</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Automatyczne czyszczenie przy zamknięciu</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Automatycznie czyść widoki tymczasowe przy zamykaniu FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Wyczyść teraz</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Usuń wszystkie widoki tymczasowe utworzone przez FilterMate w tej sesji.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Brak widoków tymczasowych)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Brak widoków</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Nie ma widoków tymczasowych do wyczyszczenia.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Potwierdź czyszczenie</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Czyszczenie zakończone</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Problem z czyszczeniem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Czyszczenie nie powiodło się</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL nie jest dostępny&lt;/b&gt;&lt;br&gt;&lt;br&gt;Aby korzystać z funkcji PostgreSQL, zainstaluj psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Następnie uruchom ponownie QGIS, aby zastosować zmiany.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Sesja: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} widok(ów) w tej sesji</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Spowoduje to usunięcie {view_count} widoków tymczasowych utworzonych przez FilterMate.

Wszelkie niezapisane wyniki filtrowania zostaną utracone.

Kontynuować?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>Usunięto {result.views_dropped} widoków tymczasowych.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Niektórych widoków nie udało się usunąć: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Błąd podczas czyszczenia: {str(e)}</translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="125"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — Opublikuj w Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="133"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Opublikuj ulubione&lt;/b&gt; — zapisz udostępnialną paczkę w kolekcji QGIS Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="153"/>
        <source>Overwrite existing bundle</source>
        <translation>Nadpisz istniejącą paczkę</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="163"/>
        <source>Publish</source>
        <translation>Opublikuj</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="177"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Kolekcja docelowa&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="190"/>
        <source>Browse...</source>
        <translation>Przeglądaj…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="198"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Nazwa pliku paczki&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="200"/>
        <source>e.g. zones_bruxelles</source>
        <translation>np. strefy_bruksela</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="203"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;cel&amp;gt;/filter_mate/favorites/&amp;lt;nazwa&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Metadane kolekcji&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="214"/>
        <source>Collection display name</source>
        <translation>Wyświetlana nazwa kolekcji</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="215"/>
        <source>Name:</source>
        <translation>Nazwa:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="218"/>
        <source>Author / organisation</source>
        <translation>Autor / organizacja</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="219"/>
        <source>Author:</source>
        <translation>Autor:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="222"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>np. CC-BY-4.0, MIT, Własnościowa</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="223"/>
        <source>License:</source>
        <translation>Licencja:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="226"/>
        <source>Comma-separated tags</source>
        <translation>Tagi oddzielone przecinkami</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="227"/>
        <source>Tags:</source>
        <translation>Tagi:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="230"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="231"/>
        <source>Homepage:</source>
        <translation>Strona internetowa:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="235"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Krótki opis (opcjonalnie, zwykły tekst)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="238"/>
        <source>Description:</source>
        <translation>Opis:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="250"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Ulubione do uwzględnienia&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="254"/>
        <source>Select all</source>
        <translation>Zaznacz wszystko</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="257"/>
        <source>Select none</source>
        <translation>Odznacz wszystko</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="284"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Nowa kolekcja w katalogu głównym Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="288"/>
        <source>Custom directory...</source>
        <translation>Katalog niestandardowy…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="340"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Zostanie utworzony w katalogu głównym Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="345"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Kliknij &apos;Przeglądaj…&apos;, aby wybrać katalog.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="351"/>
        <source>Choose a collection directory</source>
        <translation>Wybierz katalog kolekcji</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="402"/>
        <source>{0} / {1} selected</source>
        <translation>Zaznaczone: {0} / {1}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Cannot create collection</source>
        <translation>Nie można utworzyć kolekcji</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Nie znaleziono katalogu głównego Resource Sharing. Użyj &apos;Przeglądaj…&apos;, aby wybrać katalog.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Choose a directory</source>
        <translation>Wybierz katalog</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Kliknij &apos;Przeglądaj…&apos;, aby wybrać katalog docelowy.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>No favorites selected</source>
        <translation>Nie wybrano ulubionych</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Wybierz co najmniej jeden ulubiony do opublikowania.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Publish failed</source>
        <translation>Publikacja nie powiodła się</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Unknown error.</source>
        <translation>Nieznany błąd.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="505"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>Opublikowano {0} ulubion(y/e) w:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="509"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Manifest kolekcji został zaktualizowany:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="512"/>
        <source>Publish succeeded</source>
        <translation>Publikacja zakończona pomyślnie</translation>
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
        <translation>Opis:</translation>
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
        <translation>Warstwa</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="178"/>
        <source>Export</source>
        <translation>Eksportuj</translation>
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
        <translation>Błąd: {0}</translation>
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
        <translation>Status:</translation>
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
        <translation>Wpisz, aby filtrować...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="661"/>
        <source>Select All</source>
        <translation>Zaznacz wszystko</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="663"/>
        <source>Select All (non subset)</source>
        <translation>Zaznacz wszystko (poza podzbiorem)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="665"/>
        <source>Select All (subset)</source>
        <translation>Zaznacz wszystko (podzbiór)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="667"/>
        <source>De-select All</source>
        <translation>Odznacz wszystko</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="669"/>
        <source>De-select All (non subset)</source>
        <translation>Odznacz wszystko (poza podzbiorem)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="671"/>
        <source>De-select All (subset)</source>
        <translation>Odznacz wszystko (podzbiór)</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="220"/>
        <source>Select All</source>
        <translation>Zaznacz wszystko</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="222"/>
        <source>De-select All</source>
        <translation>Odznacz wszystko</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="224"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Zaznacz wszystkie warstwy wg typu geometrii (Linie)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="226"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Odznacz wszystkie warstwy wg typu geometrii (Linie)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="228"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Zaznacz wszystkie warstwy wg typu geometrii (Punkty)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="230"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Odznacz wszystkie warstwy wg typu geometrii (Punkty)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="232"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Zaznacz wszystkie warstwy wg typu geometrii (Wielokąty)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="234"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Odznacz wszystkie warstwy wg typu geometrii (Wielokąty)</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Zastosować optymalizacje?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Dostępne optymalizacje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Pomiń</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Zastosuj wybrane</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} • {1} obiektów</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Wpływ: {0}</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="75"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Szukaj w konfiguracji... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="180"/>
        <source>No match</source>
        <translation>Brak wyników</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="55"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Udostępnione ulubione</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="63"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Udostępnione ulubione&lt;/b&gt; — wykryte w kolekcjach QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation>Szukaj według nazwy, opisu, kolekcji lub tagów…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="98"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Wybierz udostępniony ulubiony, aby go podejrzeć.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="114"/>
        <source>Rescan</source>
        <translation>Skanuj ponownie</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="118"/>
        <source>Fork to my project</source>
        <translation>Forkuj do mojego projektu</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="124"/>
        <source>Close</source>
        <translation>Zamknij</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="139"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Nie znaleziono udostępnionych kolekcji. Zasubskrybuj repozytorium Resource Sharing z folderem &lt;code&gt;filter_mate/favorites&lt;/code&gt; lub umieść paczkę &lt;code&gt;.fmfav.json&lt;/code&gt; w katalogu kolekcji resource_sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="147"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} ulubion(y/e) w {1} kolekcji: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="160"/>
        <source>Collection: {0}</source>
        <translation>Kolekcja: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation>Żadne udostępnione ulubione nie pasują do wyszukiwania.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="194"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — z &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="208"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Wyrażenie&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="213"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Warstwy zdalne&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="227"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Tagi:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="234"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Pochodzenie&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="236"/>
        <source>Author: {0}</source>
        <translation>Autor: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="238"/>
        <source>License: {0}</source>
        <translation>Licencja: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Fork shared favorite</source>
        <translation>Forkuj udostępniony ulubiony</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Name in your project:</source>
        <translation>Nazwa w Twoim projekcie:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>Fork successful</source>
        <translation>Fork pomyślny</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» został dodany do ulubionych.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Fork failed</source>
        <translation>Fork nie powiódł się</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Nie udało się dodać udostępnionego ulubionego do projektu.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="468"/>
        <source>Reset to Defaults</source>
        <translation>Przywróć domyślne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Validation Error</source>
        <translation>Błąd walidacji</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Please fix the following errors:

</source>
        <translation>Proszę naprawić następujące błędy:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset Configuration</source>
        <translation>Zresetuj konfigurację</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset all values to defaults?</source>
        <translation>Zresetować wszystkie wartości do domyślnych?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="151"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - Ostrzeżenie o typie PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="155"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Niezgodność typów w filtrze: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="568"/>
        <source>Reset to Defaults</source>
        <translation>Przywróć domyślne</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="588"/>
        <source>General</source>
        <translation>Ogólne</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="268"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} obiektów widocznych w warstwie głównej</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="261"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Wszystkie filtry wyczyszczone - {count} obiektów widocznych w warstwie głównej</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="291"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Filtr zastosowany do &apos;{layer_name}&apos;: {count} obiektów</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="296"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="312"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Filtr wyczyszczony dla &apos;{layer_name}&apos;: {count} widocznych obiektów</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="909"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Nie wybrano obiektu! Widżet wyboru utracił obiekt. Wybierz ponownie obiekt.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1027"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Wybrana warstwa jest nieprawidłowa lub nie można znaleźć jej źródła. Operacja anulowana.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1042"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>Warstwa &apos;{0}&apos; nie została jeszcze zainicjalizowana. Spróbuj wybrać inną warstwę, a następnie wróć do tej.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="178"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Nie można cofnąć: warstwa nieprawidłowa lub nie znaleziono źródła.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="255"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Nie można ponowić: warstwa nieprawidłowa lub nie znaleziono źródła.</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="556"/>
        <source>Explore ...</source>
        <translation>Przeglądaj ...</translation>
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
