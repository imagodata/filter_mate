<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="hu_HU" sourcelanguage="en_US">
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="171"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Sérült szűrők törölve {0} réteg(ek)ből. Kérjük, alkalmazza újra a szűrőket.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="240"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Üres projekt észlelve. Adjon hozzá vektor rétegeket a bővítmény aktiválásához.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="307"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>Nem lehet hozzáférni a FilterMate adatbázishoz. Ellenőrizze a projektkönyvtár jogosultságait.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="321"/>
        <source>Error during database verification: {0}</source>
        <translation>Hiba az adatbázis ellenőrzése során: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="617"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Réteg betöltése sikertelen. Használja az F5 billentyűt a kényszerített újratöltéshez.</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="183"/>
        <source>Select Backend:</source>
        <translation>Háttérrendszer kiválasztása:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="202"/>
        <source>Auto (Default)</source>
        <translation>Automatikus (Alapértelmezett)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="210"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Optimális automatikus kiválasztás minden réteghez</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="220"/>
        <source>Force {0} for All Layers</source>
        <translation>{0} kényszerítése minden rétegre</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="263"/>
        <source>Click to reload layers</source>
        <translation>Kattintson a rétegek újratöltéséhez</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="298"/>
        <source>Click to change backend</source>
        <translation>Kattintson a háttérrendszer megváltoztatásához</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="350"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Hiba a módosítások visszavonásakor: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="612"/>
        <source>Property error: {0}</source>
        <translation>Tulajdonság hiba: {0}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="131"/>
        <source>Database file does not exist: {0}</source>
        <translation>Az adatbázisfájl nem létezik: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="138"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Nem sikerült csatlakozni az adatbázishoz {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="157"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Nem sikerült létrehozni az adatbázis könyvtárat {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="211"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Nem sikerült létrehozni az adatbázisfájlt {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="488"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>Nem lehet inicializálni a FilterMate adatbázist: a kapcsolódás sikertelen</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="493"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Kritikus hiba az adatbázishoz való csatlakozáskor: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="527"/>
        <source>Error during database initialization: {0}</source>
        <translation>Hiba az adatbázis inicializálása során: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="146"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Az adatbázisfájl nem létezik: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="157"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Nem sikerült csatlakozni az adatbázishoz {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>A QGIS Processing modul nem érhető el a térbeli index létrehozásához</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="188"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Nem hozható létre térbeli index: a réteg érvénytelen vagy a forrás nem található.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="398"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>PostgreSQL rétegek észlelve, de a psycopg2 nincs telepítve. A helyi Spatialite háttér használatban. Jobb teljesítményért nagy adathalmazoknál telepítse a psycopg2-t.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Réteg mentése fájlba</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Válasszon mappát a rétegek exportálásához</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="158"/>
        <source>Save your exported data to a zip file</source>
        <translation>Exportált adatok mentése zip fájlba</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="116"/>
        <source>{0} couche(s)</source>
        <translation>{0} réteg(ek)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="118"/>
        <source> dans {0} groupe(s)</source>
        <translation> {0} csoport(ok)ban</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="120"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} csoporton kívül</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="127"/>
        <source>Destination : {0}</source>
        <translation>Cél: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="147"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Nem észlelhető csoport - minden réteg a gyökérszinten van</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="155"/>
        <source>Annuler</source>
        <translation>Mégse</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="161"/>
        <source>Exporter</source>
        <translation>Exportáló</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation>Nincs szűrő</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No active filter to save.</source>
        <translation>Nincs mentendő aktív szűrő.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Add Favorite</source>
        <translation>Kedvenc hozzáadása</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Favorite name:</source>
        <translation>Kedvenc neve:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="254"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>A(z) &apos;{0}&apos; kedvenc sikeresen hozzáadva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="399"/>
        <source>Export Favorites</source>
        <translation>Kedvencek exportálása</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="423"/>
        <source>Exported {0} favorites</source>
        <translation>{0} kedvenc exportálva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="425"/>
        <source>Failed to export favorites</source>
        <translation>Nem sikerült exportálni a kedvenceket</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Import Favorites</source>
        <translation>Kedvencek importálása</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Egyesítés a meglévő kedvencekkel?

Igen = Hozzáadás a meglévőkhöz
Nem = Összes meglévő cseréje</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="493"/>
        <source>Imported {0} favorites</source>
        <translation>{0} kedvenc importálva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="495"/>
        <source>No favorites imported</source>
        <translation>Nem lettek kedvencek importálva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="504"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>A kedvencek kezelő nincs inicializálva. Kérjük, indítsa újra a FilterMate-et.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="538"/>
        <source>Favorites manager dialog not available</source>
        <translation>A kedvencek kezelő párbeszédablak nem érhető el</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1779"/>
        <source>Error: {0}</source>
        <translation>Hiba: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation>{0} alkalommal használva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation>Jelenlegi szűrő hozzáadása a kedvencekhez</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation>Szűrő hozzáadása (nincs aktív szűrő)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation>Kedvencek kezelése...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation>Exportálás...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation>Importálás...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation>Globális kedvencek</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation>Másolás globálisba...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation>── Elérhető globális kedvencek ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation>(Nincsenek globális kedvencek)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation>Karbantartás</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation>Mentés projektbe (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation>Visszaállítás projektből</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation>Árva projektek eltávolítása</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation>Adatbázis statisztikák</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation>Érvénytelen név</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Favorite name cannot be empty.</source>
        <translation>A kedvenc neve nem lehet üres.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>Duplicate Name</source>
        <translation>Ismétlődő név</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Már létezik egy &apos;{0}&apos; nevű kedvenc.
Szeretné lecserélni?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1555"/>
        <source>Favorite copied to global favorites</source>
        <translation>Kedvenc másolva a globális kedvencekbe</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1558"/>
        <source>Failed to copy to global favorites</source>
        <translation>Nem sikerült a globális kedvencekbe másolni</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>Global Favorites</source>
        <translation>Globális kedvencek</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation>{0} globális kedvenc elérhető.

A globális kedvencek minden projektben elérhetők.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1581"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>{0} kedvenc mentve a projektfájlba</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1583"/>
        <source>Save failed</source>
        <translation>Mentés sikertelen</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1595"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>{0} kedvenc visszaállítva a projektfájlból</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1597"/>
        <source>No favorites to restore found in project</source>
        <translation>Nem találhatók visszaállítandó kedvencek a projektben</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1624"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0} árva projekt eltávolítva</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1626"/>
        <source>No orphan projects to clean up</source>
        <translation>Nincsenek eltávolítandó árva projektek</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1751"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>FilterMate adatbázis statisztikák

Összes kedvenc: {0}
   Projekt: {1}
   Árva: {2}
   Globális: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1767"/>
        <source>Top projects by favorites:</source>
        <translation>Legtöbb kedvenccel rendelkező projektek:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1771"/>
        <source>FilterMate Statistics</source>
        <translation>FilterMate statisztikák</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation>Kedvencek kezelője</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Még nincsenek mentett kedvencek.

Alkalmazzon egy szűrőt egy rétegre, majd kattintson a ★ jelzőre, és válassza a «Jelenlegi szűrő hozzáadása a kedvencekhez» lehetőséget, hogy elmentse első kedvencét.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation>Importálás a Resource Sharingből…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Közzététel a Resource Sharingben…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation>Közzététel (nincs mentett kedvenc)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1734"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>A FilterMate konfigurációs mappa még nincs inicializálva — először nyisson meg egy QGIS projektet a FilterMate-tel.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1692"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation>A Resource Sharing bővítmény nincs aktiválva. Kapcsolja be a &apos;favorites_sharing&apos; opciót a FilterMate beállításaiban.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1700"/>
        <source>Shared favorites service is not available.</source>
        <translation>A megosztott kedvencek szolgáltatás nem érhető el.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1686"/>
        <source>Shared picker failed: {0}</source>
        <translation>A megosztott kedvencek választója nem sikerült: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1704"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation>Még nincsenek közzétehető kedvencei. Először mentsen el egy szűrőt a ★ menüből.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1720"/>
        <source>Publish dialog failed: {0}</source>
        <translation>A közzétételi ablak megnyitása nem sikerült: {0}</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="118"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Kedvencek kezelő</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="946"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Mentett kedvencek ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="180"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Keresés név, kifejezés, címkék vagy leírás alapján...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="444"/>
        <source>General</source>
        <translation>Általános</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Expression</source>
        <translation>Kifejezés</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="697"/>
        <source>Remote</source>
        <translation>Távoli</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="466"/>
        <source>Favorite name</source>
        <translation>Kedvenc neve</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="467"/>
        <source>Name:</source>
        <translation>Név:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="471"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Leírás (automatikusan generált, szerkeszthető)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="472"/>
        <source>Description:</source>
        <translation>Leírás:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="475"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Adjon meg címkéket vesszővel elválasztva (pl. városi, népesség, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="478"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>A címkék segítenek a kedvencek rendszerezésében és keresésében.
Több címkét vesszővel válasszon el.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="481"/>
        <source>Tags:</source>
        <translation>Címkék:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="486"/>
        <source>Source Layer:</source>
        <translation>Forrásréteg:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="490"/>
        <source>Provider:</source>
        <translation>Szolgáltató:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="498"/>
        <source>Used:</source>
        <translation>Használva:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="501"/>
        <source>Created:</source>
        <translation>Létrehozva:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="514"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Forrásréteg kifejezés:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="518"/>
        <source>Filter expression for source layer</source>
        <translation>Szűrőkifejezés a forrásréteghez</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="533"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Szűrt távoli rétegek:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Layer</source>
        <translation>Réteg</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Features</source>
        <translation>Elemek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="545"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Nincsenek távoli rétegek ebben a kedvencben&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="558"/>
        <source>Apply</source>
        <translation>Alkalmaz</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="561"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Kedvenc szűrő alkalmazása a projektre</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="564"/>
        <source>Save Changes</source>
        <translation>Módosítások mentése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="567"/>
        <source>Save modifications to this favorite</source>
        <translation>Módosítások mentése ehhez a kedvenchez</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="570"/>
        <source>Delete</source>
        <translation>Törlés</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="573"/>
        <source>Permanently delete this favorite</source>
        <translation>Kedvenc végleges törlése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Close</source>
        <translation>Bezárás</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="578"/>
        <source>Close this dialog</source>
        <translation>Párbeszédablak bezárása</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kedvencek ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="691"/>
        <source>Remote ({0})</source>
        <translation>Távoli ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Delete Favorite</source>
        <translation>Kedvenc törlése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="774"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Törli a(z) &apos;{0}&apos; kedvencet?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="870"/>
        <source>Remote Layers</source>
        <translation>Távoli rétegek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="942"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Mentett kedvencek (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>Favorites Manager</source>
        <translation>Kedvencek kezelő</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>No favorites saved yet.

Click the ★ indicator and select &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Még nincsenek mentett kedvencek.

Kattintson a ★ jelzőre és válassza a &apos;Jelenlegi szűrő hozzáadása a kedvencekhez&apos; lehetőséget az első kedvenc mentéséhez.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="146"/>
        <source>Shared...</source>
        <translation>Megosztott…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="148"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Böngésszen a QGIS Resource Sharing gyűjtemények megosztott kedvencei között</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="158"/>
        <source>Publish...</source>
        <translation>Közzététel…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="160"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>A kijelölt kedvencek közzététele egy Resource Sharing gyűjteményben</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Could not delete &apos;{0}&apos;. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation>A «{0}» nem törölhető. A kedvenc még mindig az adatbázisban van — a részletekért ellenőrizze a FilterMate naplót.</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="588"/>
        <source>View</source>
        <translation>Nézet</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="590"/>
        <source>Change</source>
        <translation>Módosítás</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="601"/>
        <source>Select a folder</source>
        <translation>Válasszon mappát</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="608"/>
        <source>Select a file</source>
        <translation>Válasszon fájlt</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="616"/>
        <source>Save to a file</source>
        <translation>Mentés fájlba</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="648"/>
        <source>View</source>
        <translation>Nézet</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="650"/>
        <source>Change</source>
        <translation>Módosítás</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="659"/>
        <source>Select an icon</source>
        <translation>Válasszon ikont</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>A réteg érvénytelen vagy a forrása nem található. A művelet megszakítva.</translation>
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
        <translation>FilterMate panel megnyitása</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset configuration and database</source>
        <translation>Konfiguráció és adatbázis visszaállítása</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Alapértelmezett konfiguráció visszaállítása és SQLite adatbázis törlése</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Reset Configuration</source>
        <translation>Konfiguráció visszaállítása</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1357"/>
        <source>Configuration reset successfully.</source>
        <translation>Konfiguráció sikeresen visszaállítva.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1362"/>
        <source>Default configuration file not found.</source>
        <translation>Az alapértelmezett konfigurációs fájl nem található.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1383"/>
        <source>Database deleted: {filename}</source>
        <translation>Adatbázis törölve: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>Restart required</source>
        <translation>Újraindítás szükséges</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="403"/>
        <source>Obsolete configuration detected</source>
        <translation>Elavult konfiguráció észlelve</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="404"/>
        <source>unknown version</source>
        <translation>ismeretlen verzió</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="405"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Elavult konfiguráció ({}) észlelve.

Szeretné visszaállítani az alapértelmezett beállításokat?

• Igen: Visszaállítás (biztonsági mentés készül)
• Nem: Jelenlegi konfiguráció megtartása (problémákat okozhat)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="412"/>
        <source>Corrupted configuration detected</source>
        <translation>Sérült konfiguráció észlelve</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="413"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>A konfigurációs fájl sérült és nem olvasható.

Szeretné visszaállítani az alapértelmezett beállításokat?

• Igen: Visszaállítás (biztonsági mentés készül, ha lehetséges)
• Nem: Mégse (a bővítmény nem működhet megfelelően)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="420"/>
        <source>Configuration reset</source>
        <translation>Konfiguráció visszaállítva</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="421"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>A konfigurációt vissza kell állítani.

Szeretné folytatni?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="469"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>A konfiguráció nem lett visszaállítva. Egyes funkciók nem működhetnek megfelelően.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>Configuration created with default values</source>
        <translation>Konfiguráció alapértelmezett értékekkel létrehozva</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="483"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Sérült konfiguráció visszaállítva. Az alapértelmezett beállítások helyreállítva.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="486"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Elavult konfiguráció visszaállítva. Az alapértelmezett beállítások helyreállítva.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="507"/>
        <source>Configuration updated to latest version</source>
        <translation>Konfiguráció frissítve a legújabb verzióra</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="504"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Konfiguráció frissítve: új beállítások elérhetők ({sections}). Elérhető a Beállítások menüben.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="498"/>
        <source>Geometry Simplification</source>
        <translation>Geometria egyszerűsítés</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="499"/>
        <source>Optimization Thresholds</source>
        <translation>Optimalizálási küszöbértékek</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="526"/>
        <source>Error during configuration migration: {}</source>
        <translation>Hiba a konfiguráció migrálása során: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="644"/>
        <source>Geometry validation setting</source>
        <translation>Geometria érvényesítési beállítás</translation>
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
        <translation>A QGIS beállítás &apos;Érvénytelen elemek szűrése&apos; jelenleg &apos;{mode}&apos; értékre van állítva.

A FilterMate javasolja ennek a beállításnak a letiltását (&apos;Ki&apos; érték) a következő okok miatt:

• Az érvénytelen geometriával rendelkező elemek csendben kizárhatók az exportálásokból és szűrőkből
• A FilterMate belsőleg kezeli a geometria érvényesítést automatikus javítási lehetőségekkel
• Egyes legitim adatok geometriái &apos;érvénytelennek&apos; minősülhetnek a szigorú OGC szabályok szerint

Szeretné most letiltani ezt a beállítást?

• Igen: Szűrés letiltása (FilterMate-hez ajánlott)
• Nem: Jelenlegi beállítás megtartása</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="674"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Érvénytelen geometria szűrés sikeresen letiltva.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="681"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Az érvénytelen geometria szűrés nem módosult. Egyes elemek kizárásra kerülhetnek az exportálásból.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>Biztosan visszaállítja az alapértelmezett konfigurációt?

Ez a következőket fogja tenni:
- Alapértelmezett beállítások visszaállítása
- Réteg adatbázis törlése

A QGIS-t újra kell indítani a módosítások alkalmazásához.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>A konfiguráció visszaállítva.

Kérjük, indítsa újra a QGIS-t a módosítások alkalmazásához.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="348"/>
        <source>Initialization error: {0}</source>
        <translation>Inicializálási hiba: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="585"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} hivatkozott réteg nincs betöltve ({layers_list}). Tartalék megjelenítés használata.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1388"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Nem sikerült törölni: {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation>Hiba a visszaállítás során: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1438"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style=&apos;font-size:13px;&apos;&gt;Köszönjük, hogy a &lt;b&gt;FilterMate&lt;/b&gt;-et használja!&lt;br&gt;Csatlakozzon Discord közösségünkhöz:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Segítség és támogatás&lt;/li&gt;&lt;li&gt;Hibák és problémák bejelentése&lt;/li&gt;&lt;li&gt;Új funkciók javaslása&lt;/li&gt;&lt;li&gt;Tippek megosztása más felhasználókkal&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1454"/>
        <source>  Join us on Discord</source>
        <translation>  Csatlakozz hozzánk a Discordon</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1474"/>
        <source>Don&apos;t show this again</source>
        <translation>Ne mutassa újra</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1477"/>
        <source>Close</source>
        <translation>Bezárás</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1543"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Hiba a bővítmény betöltésekor: {0}. Részletekért ellenőrizze a QGIS Python konzolt.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6711"/>
        <source>Current layer: {0}</source>
        <translation>Aktuális réteg: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6713"/>
        <source>No layer selected</source>
        <translation>Nincs kijelölt réteg</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Selected layers:
{0}</source>
        <translation>Kijelölt rétegek:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>No layers selected</source>
        <translation>Nincsenek kijelölt rétegek</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6743"/>
        <source>No expression defined</source>
        <translation>Nincs meghatározott kifejezés</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6755"/>
        <source>Display expression: {0}</source>
        <translation>Megjelenítési kifejezés: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6770"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>Elem azonosító: {0}
Első attribútum: {1}</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="274"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>PostgreSQL rétegek észlelve ({0}), de a psycopg2 nincs telepítve.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="361"/>
        <source>Cleared {0} caches</source>
        <translation>{0} gyorsítótár törölve</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="795"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Nem sikerült létrehozni a dokkolható ablakot: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="805"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Nem sikerült megjeleníteni a dokkolható ablakot: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1255"/>
        <source>Error executing {0}: {1}</source>
        <translation>Hiba a végrehajtáskor ({0}): {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1267"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>A bővítmény csökkentett módban fut (hexagonális szolgáltatások nem elérhetők). A teljesítmény csökkenhet.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate HIBA</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Nem lehet végrehajtani: {0}: a widget inicializálása sikertelen.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2167"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Nem lehet végrehajtani ({0}): érvénytelen réteg vagy forrás nem található.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2304"/>
        <source>All filters cleared - </source>
        <translation>Minden szűrő törölve - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2305"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} elem látható a fő rétegben</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2311"/>
        <source>Error: result handler missing</source>
        <translation>Hiba: eredménykezelő hiányzik</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2324"/>
        <source>Error during filtering: {0}</source>
        <translation>Hiba a szűrés során: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2455"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0} árva kedvenc helyreállítva: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2591"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Réteg betöltése sikertelen - kattintson az újrapróbálkozáshoz</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} réteg sikeresen betöltve</translation>
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
        <translation>Cancel</translation>
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
        <translation>Inicializálási hiba: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="925"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Felhasználói felület konfiguráció hiányos - ellenőrizze a naplókat</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation>Felhasználói felület méretezési hiba: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1355"/>
        <source>Favorites manager not available</source>
        <translation>A kedvencek kezelő nem érhető el</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1374"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} kedvenc mentve
Kattintson az alkalmazáshoz vagy kezeléshez</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1382"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Nincsenek mentett kedvencek
Kattintson a jelenlegi szűrő hozzáadásához</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1406"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>{0} háttérrendszer kényszerítve {1} réteg(ek)re</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1492"/>
        <source>Backend controller not available</source>
        <translation>A háttérvezérlő nem érhető el</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1430"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>PostgreSQL automatikus tisztítás engedélyezve</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1431"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>PostgreSQL automatikus tisztítás letiltva</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>PostgreSQL munkamenet nézetek eltávolítva</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Nincsenek törlendő nézetek vagy a tisztítás sikertelen</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1448"/>
        <source>No PostgreSQL connection available</source>
        <translation>Nincs elérhető PostgreSQL kapcsolat</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1454"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>A séma {0} nézet(ek)et tartalmaz más munkamenetekből.
Mégis törli?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1455"/>
        <source>Other Sessions Active</source>
        <translation>Más munkamenetek aktívak</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1457"/>
        <source>Schema cleanup cancelled</source>
        <translation>Séma tisztítás megszakítva</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1462"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>A(z) &apos;{0}&apos; séma sikeresen törölve</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1464"/>
        <source>Schema cleanup failed</source>
        <translation>Séma tisztítás sikertelen</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1490"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL munkamenet információ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Theme adapted: {0}</source>
        <translation>Téma alkalmazva: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Dark mode</source>
        <translation>Sötét mód</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Light mode</source>
        <translation>Világos mód</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3896"/>
        <source>Selected features have no geometry.</source>
        <translation>A kijelölt elemeknek nincs geometriájuk.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3915"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Nincs kijelölt elem. Válasszon egy elemet a legördülő listából.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4957"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>A kijelölt réteg érvénytelen vagy a forrása nem található.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5667"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Negatív puffer (erózió): poligonok befelé zsugorítása</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5670"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Pufferérték méterben (pozitív=kiterjesztés, negatív=poligonok zsugorítása)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6144"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Bővítmény aktiválva {0} vektor réteg(ek)gel</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6227"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Nem sikerült automatikusan újratölteni a bővítményt.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6229"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Hiba a bővítmény újratöltésekor: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6282"/>
        <source>Layer properties reset to defaults</source>
        <translation>Réteg tulajdonságok visszaállítva az alapértékekre</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6283"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Hiba a réteg tulajdonságainak visszaállításakor: {}</translation>
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
        <translation>EGYEDI KIJELÖLÉS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="953"/>
        <source>MULTIPLE SELECTION</source>
        <translation>TÖBBSZÖRÖS KIJELÖLÉS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1112"/>
        <source>CUSTOM SELECTION</source>
        <translation>EGYÉNI KIJELÖLÉS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1374"/>
        <source>FILTERING</source>
        <translation>SZŰRÉS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2647"/>
        <source>EXPORTING</source>
        <translation>EXPORTÁLÁS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3479"/>
        <source>CONFIGURATION</source>
        <translation>KONFIGURÁCIÓ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3225"/>
        <source>Select CRS for export</source>
        <translation>CRS kiválasztása exportáláshoz</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3747"/>
        <source>Export</source>
        <translation>Exportálás</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2333"/>
        <source>AND</source>
        <translation>ÉS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2338"/>
        <source>AND NOT</source>
        <translation>ÉS NEM</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2343"/>
        <source>OR</source>
        <translation>VAGY</translation>
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
        <translation>Többrétegű szűrés</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1661"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Additív szűrés a kijelölt rétegre</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1947"/>
        <source>Geospatial filtering</source>
        <translation>Térbeli szűrés</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2037"/>
        <source>Buffer</source>
        <translation>Puffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2282"/>
        <source>Expression layer</source>
        <translation>Kifejezés réteg</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2394"/>
        <source>Geometric predicate</source>
        <translation>Geometriai predikátum</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3325"/>
        <source>Output format</source>
        <translation>Kimeneti formátum</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3583"/>
        <source>Filter</source>
        <translation>Szűrő</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3645"/>
        <source>Reset</source>
        <translation>Visszaállítás</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2751"/>
        <source>Layers to export</source>
        <translation>Exportálandó rétegek</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2832"/>
        <source>Layers projection</source>
        <translation>Rétegek vetülete</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2916"/>
        <source>Save styles</source>
        <translation>Stílusok mentése</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2997"/>
        <source>Datatype export</source>
        <translation>Adattípus exportálás</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3078"/>
        <source>Name of file/directory</source>
        <translation>Fájl/könyvtár neve</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2205"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Centroidok használata teljes geometriák helyett a forrásréteghez (gyorsabb összetett poligonoknál)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2521"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Pufferérték méterben (pozitív=kiterjesztés, negatív=poligonok zsugorítása)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2609"/>
        <source>Number of segments for buffer precision</source>
        <translation>Szegmensek száma a puffer pontosságához</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3421"/>
        <source>Mode batch</source>
        <translation>Kötegelt mód</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="281"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} elem látható a fő rétegben</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="274"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Minden szűrő törölve - {count} elem látható a fő rétegben</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="347"/>
        <source>Task failed</source>
        <translation>Feladat sikertelen</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="348"/>
        <source>Filter failed for: {0}</source>
        <translation>Szűrés sikertelen: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="352"/>
        <source> (+{0} more)</source>
        <translation> (+{0} további)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="399"/>
        <source>Layer(s) filtered</source>
        <translation>Réteg(ek) szűrve</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="403"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Réteg(ek) szűrve az előző állapotra</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="407"/>
        <source>Layer(s) unfiltered</source>
        <translation>Réteg(ek) szűrése megszüntetve</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="411"/>
        <source>Filter task : {0}</source>
        <translation>Szűrési feladat: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="432"/>
        <source>Export task : {0}</source>
        <translation>Exportálási feladat: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="457"/>
        <source>Exception: {0}</source>
        <translation>Kivétel: {0}</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Python menük és eszköztárak</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Tulajdonság</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Érték</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Tulajdonság</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Érték</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="212"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>PostgreSQL rétegek észlelve ({0}), de a psycopg2 nincs telepítve. A bővítmény nem tudja használni ezeket a rétegeket. Telepítse a psycopg2-t a PostgreSQL támogatás engedélyezéséhez.</translation>
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
        <translation>PostgreSQL réteg &apos;{0}&apos;: Sérült adat észlelve.

Ez a réteg &apos;virtual_id&apos;-t használ, ami nem létezik a PostgreSQL-ben.
Ez a hiba a FilterMate egy korábbi verziójából ered.

Megoldás: Távolítsa el ezt a réteget a FilterMate projektből, majd adja hozzá újra.
Győződjön meg róla, hogy a PostgreSQL tábla rendelkezik definiált PRIMARY KEY-jel.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="970"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>A(z) &apos;{0}&apos; rétegnek nincs PRIMARY KEY-e. Korlátozott funkciók: materializált nézetek letiltva. Javaslat: adjon hozzá PRIMARY KEY-t az optimális teljesítményhez.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1909"/>
        <source>Exception: {0}</source>
        <translation>Kivétel: {0}</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Optimalizálási beállítások</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Optimalizálási beállítások konfigurálása</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Automatikus optimalizálások engedélyezése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Kérdezzen az optimalizálások alkalmazása előtt</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Automatikus centroid beállítások</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Automatikus centroid engedélyezése távoli rétegekhez</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Távolsági küszöbérték (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Elem küszöbérték:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Puffer optimalizálások</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Geometria egyszerűsítése pufferelés előtt</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Puffer szegmensek csökkentése:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Általános</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Materializált nézetek használata szűréshez</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Térbeli indexek automatikus létrehozása</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>R-fa térbeli index használata</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Befoglaló téglalap előszűrő használata</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Háttérrendszerek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Gyorsítótárazás</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Geometria gyorsítótár engedélyezése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Kötegelt feldolgozás</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Kötegméret:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>A haladó beállítások hatással vannak a teljesítményre és a memóriahasználatra. Csak akkor módosítsa, ha érti a következményeket.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Haladó</translation>
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
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL munkamenet információ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL aktív</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Kapcsolat információ</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Kapcsolat:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Ideiglenes séma:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Állapot:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Ideiglenes nézetek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Tisztítási lehetőségek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Automatikus tisztítás bezáráskor</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Ideiglenes nézetek automatikus törlése a FilterMate bezárásakor.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Tisztítás most</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Az összes ideiglenes nézet törlése, amelyet a FilterMate hozott létre ebben a munkamenetben.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Nincsenek ideiglenes nézetek)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Nincsenek nézetek</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Nincsenek törlendő ideiglenes nézetek.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Tisztítás megerősítése</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Tisztítás kész</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Tisztítási probléma</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Tisztítás sikertelen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;A PostgreSQL nem érhető el&lt;/b&gt;&lt;br&gt;&lt;br&gt;A PostgreSQL funkciók használatához telepítse a psycopg2-t:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Ezután indítsa újra a QGIS-t a módosítások alkalmazásához.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Munkamenet: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} nézet ebben a munkamenetben</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Ez törölni fogja a FilterMate által létrehozott {view_count} ideiglenes nézet(ek)et.

Minden nem mentett szűrési eredmény elvész.

Folytatja?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped} ideiglenes nézet eltávolítva.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Egyes nézetek nem távolíthatók el: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Hiba a tisztítás során: {str(e)}</translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="125"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — Közzététel a Resource Sharingben</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="133"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Kedvencek közzététele&lt;/b&gt; — megosztható csomag írása egy QGIS Resource Sharing gyűjteménybe.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="153"/>
        <source>Overwrite existing bundle</source>
        <translation>Meglévő csomag felülírása</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="163"/>
        <source>Publish</source>
        <translation>Közzététel</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="177"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Célgyűjtemény&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="190"/>
        <source>Browse...</source>
        <translation>Tallózás…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="198"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Csomag fájlnév&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="200"/>
        <source>e.g. zones_bruxelles</source>
        <translation>pl. zonak_brusszel</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="203"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;cel&amp;gt;/filter_mate/favorites/&amp;lt;nev&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Gyűjtemény metaadatok&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="214"/>
        <source>Collection display name</source>
        <translation>Gyűjtemény megjelenített neve</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="215"/>
        <source>Name:</source>
        <translation>Név:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="218"/>
        <source>Author / organisation</source>
        <translation>Szerző / szervezet</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="219"/>
        <source>Author:</source>
        <translation>Szerző:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="222"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>pl. CC-BY-4.0, MIT, Védett</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="223"/>
        <source>License:</source>
        <translation>Licenc:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="226"/>
        <source>Comma-separated tags</source>
        <translation>Vesszővel elválasztott címkék</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="227"/>
        <source>Tags:</source>
        <translation>Címkék:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="230"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="231"/>
        <source>Homepage:</source>
        <translation>Weboldal:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="235"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Rövid leírás (opcionális, sima szöveg)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="238"/>
        <source>Description:</source>
        <translation>Leírás:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="250"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Felveendő kedvencek&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="254"/>
        <source>Select all</source>
        <translation>Összes kijelölése</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="257"/>
        <source>Select none</source>
        <translation>Kijelölés megszüntetése</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="284"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Új gyűjtemény a Resource Sharing gyökerében…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="288"/>
        <source>Custom directory...</source>
        <translation>Egyéni könyvtár…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="340"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>A Resource Sharing gyökere alatt jön létre.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="345"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Kattintson a &apos;Tallózás…&apos; gombra könyvtár választásához.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="351"/>
        <source>Choose a collection directory</source>
        <translation>Válasszon gyűjteménykönyvtárat</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="402"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} kijelölve</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Cannot create collection</source>
        <translation>Nem hozható létre a gyűjtemény</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>A Resource Sharing gyökér nem található. Használja a &apos;Tallózás…&apos; opciót könyvtár választásához.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Choose a directory</source>
        <translation>Válasszon könyvtárat</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Kattintson a &apos;Tallózás…&apos; gombra célkönyvtár választásához.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>No favorites selected</source>
        <translation>Nincs kijelölt kedvenc</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Jelöljön ki legalább egy kedvencet a közzétételhez.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Publish failed</source>
        <translation>A közzététel nem sikerült</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Unknown error.</source>
        <translation>Ismeretlen hiba.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="505"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>{0} kedvenc közzétéve itt:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="509"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Gyűjtemény manifest frissítve:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="512"/>
        <source>Publish succeeded</source>
        <translation>Közzététel sikeres</translation>
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
        <translation>Leírás:</translation>
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
        <translation>Réteg</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="178"/>
        <source>Export</source>
        <translation>Exportálás</translation>
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
        <translation>Állapot:</translation>
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
        <translation>Gépeljen a szűréshez...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="661"/>
        <source>Select All</source>
        <translation>Összes kijelölése</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="663"/>
        <source>Select All (non subset)</source>
        <translation>Összes kijelölése (nem részhalmaz)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="665"/>
        <source>Select All (subset)</source>
        <translation>Összes kijelölése (részhalmaz)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="667"/>
        <source>De-select All</source>
        <translation>Összes kijelölés megszüntetése</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="669"/>
        <source>De-select All (non subset)</source>
        <translation>Összes kijelölés megszüntetése (nem részhalmaz)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="671"/>
        <source>De-select All (subset)</source>
        <translation>Összes kijelölés megszüntetése (részhalmaz)</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="220"/>
        <source>Select All</source>
        <translation>Összes kijelölése</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="222"/>
        <source>De-select All</source>
        <translation>Összes kijelölés megszüntetése</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="224"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Összes réteg kijelölése geometria típus szerint (Vonalak)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="226"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Összes réteg kijelölésének megszüntetése geometria típus szerint (Vonalak)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="228"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Összes réteg kijelölése geometria típus szerint (Pontok)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="230"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Összes réteg kijelölésének megszüntetése geometria típus szerint (Pontok)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="232"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Összes réteg kijelölése geometria típus szerint (Poligonok)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="234"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Összes réteg kijelölésének megszüntetése geometria típus szerint (Poligonok)</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Optimalizálások alkalmazása?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Elérhető optimalizálások</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Kihagyás</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Kijelöltek alkalmazása</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} u2022 {1} elem</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Hatás: {0}</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="75"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Konfiguráció keresése... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="180"/>
        <source>No match</source>
        <translation>Nincs találat</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="55"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Megosztott kedvencek</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="63"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Megosztott kedvencek&lt;/b&gt; — QGIS Resource Sharing gyűjteményekből felfedezve</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation>Keresés név, leírás, gyűjtemény vagy címkék alapján…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="98"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Válasszon egy megosztott kedvencet az előnézethez.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="114"/>
        <source>Rescan</source>
        <translation>Újra vizsgálat</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="118"/>
        <source>Fork to my project</source>
        <translation>Fork a projektembe</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="124"/>
        <source>Close</source>
        <translation>Bezárás</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="139"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Nincsenek megosztott gyűjtemények. Iratkozzon fel egy Resource Sharing tárolóra, amely &lt;code&gt;filter_mate/favorites&lt;/code&gt; mappát tartalmaz, vagy helyezzen el egy &lt;code&gt;.fmfav.json&lt;/code&gt; csomagot a resource_sharing gyűjtemény könyvtárában.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="147"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} kedvenc {1} gyűjteményben: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="160"/>
        <source>Collection: {0}</source>
        <translation>Gyűjtemény: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation>Nincs a keresésnek megfelelő megosztott kedvenc.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="194"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — innen: &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="208"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Kifejezés&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="213"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Távoli rétegek&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="227"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Címkék:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="234"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Eredet&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="236"/>
        <source>Author: {0}</source>
        <translation>Szerző: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="238"/>
        <source>License: {0}</source>
        <translation>Licenc: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Fork shared favorite</source>
        <translation>Fork megosztott kedvenc</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Name in your project:</source>
        <translation>Név a projektjében:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>Fork successful</source>
        <translation>Fork sikeres</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>A «{0}» hozzáadva a kedvencekhez.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Fork failed</source>
        <translation>Fork sikertelen</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Nem sikerült hozzáadni a megosztott kedvencet a projekthez.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="468"/>
        <source>Reset to Defaults</source>
        <translation>Visszaállítás alapértékekre</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Validation Error</source>
        <translation>Érvényesítési hiba</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Please fix the following errors:

</source>
        <translation>Kérjük, javítsa a következő hibákat:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset Configuration</source>
        <translation>Konfiguráció visszaállítása</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset all values to defaults?</source>
        <translation>Minden érték visszaállítása az alapértékekre?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="151"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - PostgreSQL típus figyelmeztetés</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="155"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Típuseltérés a szűrőben: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="568"/>
        <source>Reset to Defaults</source>
        <translation>Visszaállítás alapértékekre</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="588"/>
        <source>General</source>
        <translation>Általános</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="268"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} elem látható a fő rétegben</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="261"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Minden szűrő törölve - {count} elem látható a fő rétegben</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="291"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Szűrő alkalmazva: &apos;{layer_name}&apos;: {count} elem</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="296"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="312"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Szűrő törölve: &apos;{layer_name}&apos;: {count} elem látható</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="909"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Nincs kijelölt entitás! A kijelölő widget elvesztette az elemet. Jelöljön ki újra egy entitást.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1027"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>A kijelölt réteg érvénytelen vagy a forrása nem található. A művelet megszakítva.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1042"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>A(z) &apos;{0}&apos; réteg még nincs inicializálva. Próbáljon meg másik réteget kiválasztani, majd váltson vissza erre.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="178"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Nem lehet visszavonni: érvénytelen réteg vagy forrás nem található.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="255"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Nem lehet újra végrehajtani: érvénytelen réteg vagy forrás nem található.</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="556"/>
        <source>Explore ...</source>
        <translation>Felfedezés ...</translation>
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
