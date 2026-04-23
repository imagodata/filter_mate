<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fi_FI" sourcelanguage="en_US">
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="171"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Vioittuneet suodattimet poistettu {0} tasolta. Aseta suodattimet uudelleen.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="240"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Tyhja projekti havaittu. Lisaa vektoritasoja aktivoidaksesi laajennuksen.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="307"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>FilterMate-tietokantaan ei paasta. Tarkista projektikansion kayttooikeudet.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="321"/>
        <source>Error during database verification: {0}</source>
        <translation>Virhe tietokannan tarkistuksessa: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="617"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Tason lataus epaonnistui. Kayta F5 pakottaaksesi uudelleenlatauksen.</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="183"/>
        <source>Select Backend:</source>
        <translation>Valitse taustaohjelmisto:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="202"/>
        <source>Auto (Default)</source>
        <translation>Automaattinen (Oletus)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="210"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Valitse automaattisesti optimaalinen kaikille tasoille</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="220"/>
        <source>Force {0} for All Layers</source>
        <translation>Pakota {0} kaikille tasoille</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="263"/>
        <source>Click to reload layers</source>
        <translation>Napsauta ladataksesi tasot uudelleen</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="298"/>
        <source>Click to change backend</source>
        <translation>Napsauta vaihtaaksesi taustaohjelmistoa</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="350"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Virhe muutosten peruuttamisessa: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="612"/>
        <source>Property error: {0}</source>
        <translation>Ominaisuusvirhe: {0}</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="131"/>
        <source>Database file does not exist: {0}</source>
        <translation>Tietokantatiedostoa ei ole olemassa: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="138"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Yhteys tietokantaan {0} epaonnistui: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="157"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Tietokantahakemiston {0} luonti epaonnistui: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="211"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Tietokantatiedoston {0} luonti epaonnistui: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="488"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>FilterMate-tietokantaa ei voi alustaa: yhteys epaonnistui</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="493"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Kriittinen virhe yhdistettaessa tietokantaan: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="527"/>
        <source>Error during database initialization: {0}</source>
        <translation>Virhe tietokannan alustuksessa: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="146"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Tietokantatiedostoa ei ole olemassa: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="157"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Tietokantaan {db_file_path} yhdistäminen epäonnistui: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>QGIS Processing -moduuli ei ole käytettävissä tilaindeksin luomiseen</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="188"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Tilaindeksiä ei voida luoda: taso on virheellinen tai lähdettä ei löydy.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="398"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>PostgreSQL-tasoja havaittu, mutta psycopg2 ei ole asennettu. Käytetään paikallista Spatialite-taustaa. Paremman suorituskyvyn saamiseksi suurille tietoaineistoille asenna psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Tallenna tasosi tiedostoon</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Valitse kansio tasojen vientia varten</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="158"/>
        <source>Save your exported data to a zip file</source>
        <translation>Tallenna viedyt tiedot ZIP-tiedostoon</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="116"/>
        <source>{0} couche(s)</source>
        <translation>{0} taso(a)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="118"/>
        <source> dans {0} groupe(s)</source>
        <translation> {0} ryhmassa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="120"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} ryhman ulkopuolella</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="127"/>
        <source>Destination : {0}</source>
        <translation>Kohde: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="147"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Ryhmaa ei havaittu - kaikki tasot ovat juuritasolla</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="155"/>
        <source>Annuler</source>
        <translation>Peruuta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="161"/>
        <source>Exporter</source>
        <translation>Vie</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation>Ei suodatinta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No active filter to save.</source>
        <translation>Ei aktiivista suodatinta tallennettavaksi.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Add Favorite</source>
        <translation>Lisaa suosikki</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="236"/>
        <source>Favorite name:</source>
        <translation>Suosikin nimi:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="254"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Suosikki &apos;{0}&apos; lisatty onnistuneesti</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="399"/>
        <source>Export Favorites</source>
        <translation>Vie suosikit</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="423"/>
        <source>Exported {0} favorites</source>
        <translation>{0} suosikkia viety</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="425"/>
        <source>Failed to export favorites</source>
        <translation>Suosikkien vienti epaonnistui</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Import Favorites</source>
        <translation>Tuo suosikit</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="455"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Yhdista olemassa oleviin suosikkeihin?

Kylla = Lisaa olemassa oleviin
Ei = Korvaa kaikki olemassa olevat</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="493"/>
        <source>Imported {0} favorites</source>
        <translation>{0} suosikkia tuotu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="495"/>
        <source>No favorites imported</source>
        <translation>Suosikkeja ei tuotu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="504"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Suosikkien hallinta ei ole alustettu. Kaynnista FilterMate uudelleen.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="538"/>
        <source>Favorites manager dialog not available</source>
        <translation>Suosikkien hallinnan valintaikkuna ei ole kaytettavissa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1779"/>
        <source>Error: {0}</source>
        <translation>Virhe: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation>Kaytetty {0} kertaa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation>Lisaa nykyinen suodatin suosikkeihin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation>Lisaa suodatin (ei aktiivista suodatinta)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation>Hallitse suosikkeja...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation>Vie...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation>Tuo...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation>Yleiset suosikit</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation>Kopioi yleisiin...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation>── Kaytettavissa olevat yleiset suosikit ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation>(Ei yleisia suosikkeja)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation>Yllapito</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation>Tallenna projektiin (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation>Palauta projektista</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation>Siivoa orvot projektit</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation>Tietokantatilastot</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation>Virheellinen nimi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Favorite name cannot be empty.</source>
        <translation>Suosikin nimi ei voi olla tyhja.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>Duplicate Name</source>
        <translation>Kaksoisnimi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="920"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Suosikki nimella &apos;{0}&apos; on jo olemassa.
Haluatko korvata sen?</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1555"/>
        <source>Favorite copied to global favorites</source>
        <translation>Suosikki kopioitu yleisiin suosikkeihin</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1558"/>
        <source>Failed to copy to global favorites</source>
        <translation>Kopiointi yleisiin suosikkeihin epaonnistui</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>Global Favorites</source>
        <translation>Yleiset suosikit</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1565"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation>{0} yleista suosikkia kaytettavissa.

Yleiset suosikit jaetaan kaikkien projektien kesken.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1581"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>{0} suosikkia tallennettu projektitiedostoon</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1583"/>
        <source>Save failed</source>
        <translation>Tallennus epaonnistui</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1595"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>{0} suosikkia palautettu projektitiedostosta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1597"/>
        <source>No favorites to restore found in project</source>
        <translation>Ei palautettavia suosikkeja projektissa</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1624"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>{0} orpoa projektia siivottu</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1626"/>
        <source>No orphan projects to clean up</source>
        <translation>Ei orpoja projekteja siivottavaksi</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1751"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>FilterMate tietokantatilastot

Suosikkeja yhteensa: {0}
   Projekti: {1}
   Orvot: {2}
   Yleiset: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1767"/>
        <source>Top projects by favorites:</source>
        <translation>Suosituimmat projektit suosikkien mukaan:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1771"/>
        <source>FilterMate Statistics</source>
        <translation>FilterMate-tilastot</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation>Suosikkien hallinta</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Suosikkeja ei ole vielä tallennettu.

Käytä suodatinta tasoon, napsauta ★-ilmaisinta ja valitse «Lisää nykyinen suodatin suosikkeihin» tallentaaksesi ensimmäisen suosikin.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation>Tuo Resource Sharingistä…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Julkaise Resource Sharingiin…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation>Julkaise (ei tallennettuja suosikkeja)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1734"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>FilterMate-asetushakemistoa ei ole vielä alustettu — avaa ensin QGIS-projekti FilterMatella.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1692"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation>Resource Sharing -laajennus ei ole aktiivinen. Ota &apos;favorites_sharing&apos; käyttöön FilterMate-asetuksissa.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1700"/>
        <source>Shared favorites service is not available.</source>
        <translation>Jaettujen suosikkien palvelu ei ole käytettävissä.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1686"/>
        <source>Shared picker failed: {0}</source>
        <translation>Jaettujen suosikkien valitsin epäonnistui: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1704"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation>Sinulla ei ole vielä julkaistavia suosikkeja. Tallenna ensin suodatin ★-valikosta.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1720"/>
        <source>Publish dialog failed: {0}</source>
        <translation>Julkaisuikkunan avaaminen epäonnistui: {0}</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="118"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Suosikkien hallinta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="946"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Tallennetut suosikit ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="180"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Hae nimella, lausekkeella, tunnisteilla tai kuvauksella...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="444"/>
        <source>General</source>
        <translation>Yleinen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Expression</source>
        <translation>Lauseke</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="697"/>
        <source>Remote</source>
        <translation>Etainen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="466"/>
        <source>Favorite name</source>
        <translation>Suosikin nimi</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="467"/>
        <source>Name:</source>
        <translation>Nimi:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="471"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Kuvaus (automaattisesti luotu, muokattavissa)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="472"/>
        <source>Description:</source>
        <translation>Kuvaus:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="475"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Syota tunnisteet pilkuilla erotettuina (esim. kaupunki, vaesto, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="478"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Tunnisteet auttavat jarjestamaan ja hakemaan suosikkeja.
Erota useammat tunnisteet pilkuilla.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="481"/>
        <source>Tags:</source>
        <translation>Tunnisteet:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="486"/>
        <source>Source Layer:</source>
        <translation>Lahdetaso:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="490"/>
        <source>Provider:</source>
        <translation>Tiedontuottaja:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="498"/>
        <source>Used:</source>
        <translation>Kaytetty:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="501"/>
        <source>Created:</source>
        <translation>Luotu:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="514"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Lahdetason lauseke:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="518"/>
        <source>Filter expression for source layer</source>
        <translation>Suodatinlauseke lahdetasolle</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="533"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Suodatetut etaiset tasot:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Layer</source>
        <translation>Taso</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="537"/>
        <source>Features</source>
        <translation>Kohteet</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="545"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Ei etaisia tasoja tassa suosikissa&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="558"/>
        <source>Apply</source>
        <translation>Kayta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="561"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Kayta tata suosikkisuodatinta projektiin</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="564"/>
        <source>Save Changes</source>
        <translation>Tallenna muutokset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="567"/>
        <source>Save modifications to this favorite</source>
        <translation>Tallenna muutokset tahan suosikkiin</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="570"/>
        <source>Delete</source>
        <translation>Poista</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="573"/>
        <source>Permanently delete this favorite</source>
        <translation>Poista tama suosikki pysyvasti</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Close</source>
        <translation>Sulje</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="578"/>
        <source>Close this dialog</source>
        <translation>Sulje tama valintaikkuna</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Suosikit ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="691"/>
        <source>Remote ({0})</source>
        <translation>Etainen ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Delete Favorite</source>
        <translation>Poista suosikki</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="774"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Poista suosikki &apos;{0}&apos;?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="870"/>
        <source>Remote Layers</source>
        <translation>Etaiset tasot</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="942"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Tallennetut suosikit (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>Favorites Manager</source>
        <translation>Suosikkien hallinta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="965"/>
        <source>No favorites saved yet.

Click the ★ indicator and select &apos;Add current filter to favorites&apos; to save your first favorite.</source>
        <translation>Suosikkeja ei ole viela tallennettu.

Napsauta ★-ilmaisinta ja valitse &apos;Lisaa nykyinen suodatin suosikkeihin&apos; tallentaaksesi ensimmaisen suosikkisi.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="146"/>
        <source>Shared...</source>
        <translation>Jaetut…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="148"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Selaa QGIS Resource Sharing -kokoelmien kautta jaettuja suosikkeja</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="158"/>
        <source>Publish...</source>
        <translation>Julkaise…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="160"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Julkaise valitut suosikit Resource Sharing -kokoelmaan</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="798"/>
        <source>Could not delete &apos;{0}&apos;. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation>Ei voitu poistaa «{0}». Suosikki on edelleen tietokannassa — tarkista FilterMate-loki.</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="588"/>
        <source>View</source>
        <translation>Nayta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="590"/>
        <source>Change</source>
        <translation>Muuta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="601"/>
        <source>Select a folder</source>
        <translation>Valitse kansio</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="608"/>
        <source>Select a file</source>
        <translation>Valitse tiedosto</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="616"/>
        <source>Save to a file</source>
        <translation>Tallenna tiedostoon</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="648"/>
        <source>View</source>
        <translation>Nayta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="650"/>
        <source>Change</source>
        <translation>Muuta</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="659"/>
        <source>Select an icon</source>
        <translation>Valitse kuvake</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Taso on virheellinen tai sen lahdetta ei loydy. Toiminto peruutettu.</translation>
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
        <translation>Avaa FilterMate-paneeli</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset configuration and database</source>
        <translation>Palauta asetukset ja tietokanta</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="323"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Palauta oletusasetukset ja poista SQLite-tietokanta</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1334"/>
        <source>Reset Configuration</source>
        <translation>Palauta asetukset</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1357"/>
        <source>Configuration reset successfully.</source>
        <translation>Asetukset palautettu onnistuneesti.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1362"/>
        <source>Default configuration file not found.</source>
        <translation>Oletusasetustiedostoa ei löydy.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1383"/>
        <source>Database deleted: {filename}</source>
        <translation>Tietokanta poistettu: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>Restart required</source>
        <translation>Uudelleenkäynnistys vaaditaan</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="403"/>
        <source>Obsolete configuration detected</source>
        <translation>Vanhentunut asetustiedosto havaittu</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="404"/>
        <source>unknown version</source>
        <translation>tuntematon versio</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="412"/>
        <source>Corrupted configuration detected</source>
        <translation>Vioittunut asetustiedosto havaittu</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="469"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Asetuksia ei nollattu. Jotkin toiminnot eivät ehkä toimi oikein.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>Configuration created with default values</source>
        <translation>Asetukset luotu oletusarvoilla</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="483"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Vioittunut asetustiedosto nollattu. Oletusasetukset on palautettu.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="486"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Vanhentunut asetustiedosto nollattu. Oletusasetukset on palautettu.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="507"/>
        <source>Configuration updated to latest version</source>
        <translation>Asetukset päivitetty uusimpaan versioon</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="504"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Asetukset päivitetty: uudet asetukset saatavilla ({sections}). Pääsy Asetukset-valikon kautta.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="498"/>
        <source>Geometry Simplification</source>
        <translation>Geometrian yksinkertaistaminen</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="499"/>
        <source>Optimization Thresholds</source>
        <translation>Optimointirajat</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="644"/>
        <source>Geometry validation setting</source>
        <translation>Geometrian tarkistusasetus</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="674"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Virheellisten geometrioiden suodatus poistettu käytöstä onnistuneesti.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="681"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Virheellisten geometrioiden suodatusta ei muutettu. Jotkin kohteet voivat jäädä pois viennistä.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="405"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Vanhentunut konfiguraatio ({}) havaittu.

Haluatko palauttaa oletusasetukset?

• Kyllä: Palauta (varmuuskopio luodaan)
• Ei: Säilytä nykyinen konfiguraatio (voi aiheuttaa ongelmia)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="413"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>Konfiguraatiotiedosto on vioittunut eikä sitä voida lukea.

Haluatko palauttaa oletusasetukset?

• Kyllä: Palauta (varmuuskopio luodaan jos mahdollista)
• Ei: Peruuta (lisäosa ei ehkä toimi oikein)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="420"/>
        <source>Configuration reset</source>
        <translation>Konfiguraation palautus</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="421"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>Konfiguraatio täytyy palauttaa.

Haluatko jatkaa?</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="526"/>
        <source>Error during configuration migration: {}</source>
        <translation>Virhe konfiguraation siirrossa: {}</translation>
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
        <translation>Haluatko varmasti palauttaa oletuskonfiguraation?

Tämä:
- Palauttaa oletusasetukset
- Poistaa tasotietokannan

QGIS on käynnistettävä uudelleen muutosten käyttöönottamiseksi.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1397"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>Konfiguraatio on palautettu.

Käynnistä QGIS uudelleen ottaaksesi muutokset käyttöön.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="348"/>
        <source>Initialization error: {0}</source>
        <translation>Alustusvirhe: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="585"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} viitattua tasoa ei ladattu ({layers_list}). Kaytetaan varanakymaa.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1388"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Tiedostoa {filename} ei voi poistaa: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation>Virhe nollauksen aikana: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1438"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style=&apos;font-size:13px;&apos;&gt;Kiitos &lt;b&gt;FilterMaten&lt;/b&gt; kaytosta!&lt;br&gt;Liity Discord-yhteisoomme:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Saa apua ja tukea&lt;/li&gt;&lt;li&gt;Ilmoita virheista ja ongelmista&lt;/li&gt;&lt;li&gt;Ehdota uusia ominaisuuksia&lt;/li&gt;&lt;li&gt;Jaa vinkkeja muiden kayttajien kanssa&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1454"/>
        <source>  Join us on Discord</source>
        <translation>  Liity Discordiin</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1474"/>
        <source>Don&apos;t show this again</source>
        <translation>Ala nayta tata uudelleen</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1477"/>
        <source>Close</source>
        <translation>Sulje</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1543"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Virhe laajennuksen latauksessa: {0}. Tarkista QGIS Python -konsoli lisatietoja varten.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6711"/>
        <source>Current layer: {0}</source>
        <translation>Nykyinen taso: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6713"/>
        <source>No layer selected</source>
        <translation>Tasoa ei ole valittu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Selected layers:
{0}</source>
        <translation>Valitut tasot:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>No layers selected</source>
        <translation>Tasoja ei ole valittu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6743"/>
        <source>No expression defined</source>
        <translation>Lauseketta ei ole maaritetty</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6755"/>
        <source>Display expression: {0}</source>
        <translation>Nayttolauseke: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6770"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>Kohteen tunnus: {0}
Ensimmainen attribuutti: {1}</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="274"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>PostgreSQL-tasoja havaittu ({0}), mutta psycopg2 ei ole asennettu.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="361"/>
        <source>Cleared {0} caches</source>
        <translation>{0} vailimuistia tyhjennetty</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="795"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Dockwidgetin luonti epaonnistui: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="805"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Dockwidgetin nayttaminen epaonnistui: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1255"/>
        <source>Error executing {0}: {1}</source>
        <translation>Virhe suoritettaessa {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1267"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Laajennus toimii rajoitetussa tilassa (heksagonaalipalvelut eivat ole kaytettavissa). Suorituskyky voi olla alentunut.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate VIRHE</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1396"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Kohdetta {0} ei voi suorittaa: widgetin alustus epaonnistui.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2167"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Toimintoa {0} ei voi suorittaa: taso virheellinen tai lahdetta ei loydy.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2304"/>
        <source>All filters cleared - </source>
        <translation>Kaikki suodattimet poistettu - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2305"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} kohdetta nakyvissa paatasolla</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2311"/>
        <source>Error: result handler missing</source>
        <translation>Virhe: tuloskasittelija puuttuu</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2324"/>
        <source>Error during filtering: {0}</source>
        <translation>Virhe suodatuksen aikana: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2455"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>{0} orpoa suosikkia palautettu: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2591"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Tason lataus epaonnistui - napsauta yrittaaksesi uudelleen</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} tasoa ladattu onnistuneesti</translation>
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
        <translation>Peruuta</translation>
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
        <translation>Alustusvirhe: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="925"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Kayttoliittymaasetukset puutteelliset - tarkista lokit</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation>Kayttoliittyman mittavirhe: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1355"/>
        <source>Favorites manager not available</source>
        <translation>Suosikkien hallinta ei ole kaytettavissa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1374"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} suosikkia tallennettu
Napsauta kayttaaksesi tai hallitaksesi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1382"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Ei tallennettuja suosikkeja
Napsauta lisaataksesi nykyisen suodattimen</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1406"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>{0} taustaohjelmisto pakotettu {1} tasolle</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1492"/>
        <source>Backend controller not available</source>
        <translation>Taustaohjelmiston ohjain ei ole kaytettavissa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1430"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>PostgreSQL automaattinen siivous kaytoessa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1431"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>PostgreSQL automaattinen siivous poissa kaytosta</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>PostgreSQL-istuntonakymat siivottu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1437"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Ei nakymia siivottavaksi tai siivous epaonnistui</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1448"/>
        <source>No PostgreSQL connection available</source>
        <translation>PostgreSQL-yhteytta ei ole kaytettavissa</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1454"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>Skeemassa on {0} nakymaa muista istunnoista.
Poista silti?</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1455"/>
        <source>Other Sessions Active</source>
        <translation>Muita istuntoja aktiivisena</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1457"/>
        <source>Schema cleanup cancelled</source>
        <translation>Skeeman siivous peruutettu</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1462"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Skeema &apos;{0}&apos; poistettu onnistuneesti</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1464"/>
        <source>Schema cleanup failed</source>
        <translation>Skeeman siivous epaonnistui</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1490"/>
        <source>PostgreSQL Session Info</source>
        <translation>PostgreSQL istuntotiedot</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Theme adapted: {0}</source>
        <translation>Teema mukautettu: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Dark mode</source>
        <translation>Tumma tila</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2587"/>
        <source>Light mode</source>
        <translation>Vaalea tila</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3896"/>
        <source>Selected features have no geometry.</source>
        <translation>Valituilla kohteilla ei ole geometriaa.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="3915"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Kohdetta ei ole valittu. Valitse kohde pudotusvalikosta.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4957"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>Valittu taso on virheellinen tai sen lahdetta ei loydy.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5667"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Negatiivinen puskuri (eroosio): kutistaa monikulmioita sisaanpain</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5670"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Puskuriarvo metrissa (positiivinen=laajenna, negatiivinen=kutista monikulmioita)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6144"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Laajennus aktivoitu {0} vektoritasolla</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6227"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Laajennusta ei voitu ladata uudelleen automaattisesti.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6229"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Virhe laajennuksen uudelleenlatauksessa: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6282"/>
        <source>Layer properties reset to defaults</source>
        <translation>Tason ominaisuudet palautettu oletusarvoihin</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6283"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Virhe tason ominaisuuksien nollauksessa: {}</translation>
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
        <translation>YKSITTÄINEN VALINTA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="953"/>
        <source>MULTIPLE SELECTION</source>
        <translation>MONIVALINTA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1112"/>
        <source>CUSTOM SELECTION</source>
        <translation>MUKAUTETTU VALINTA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1374"/>
        <source>FILTERING</source>
        <translation>SUODATUS</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2647"/>
        <source>EXPORTING</source>
        <translation>VIENTI</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3479"/>
        <source>CONFIGURATION</source>
        <translation>ASETUKSET</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3225"/>
        <source>Select CRS for export</source>
        <translation>Valitse koordinaattijärjestelmä vientiin</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3747"/>
        <source>Export</source>
        <translation>Vie</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2333"/>
        <source>AND</source>
        <translation>JA</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2338"/>
        <source>AND NOT</source>
        <translation>JA EI</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2343"/>
        <source>OR</source>
        <translation>TAI</translation>
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
        <translation>Monitasosuodatus</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1661"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Lisäävä suodatus valitulle tasolle</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1947"/>
        <source>Geospatial filtering</source>
        <translation>Geospatiaalinen suodatus</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2037"/>
        <source>Buffer</source>
        <translation>Puskuri</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2282"/>
        <source>Expression layer</source>
        <translation>Lauseketaso</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2394"/>
        <source>Geometric predicate</source>
        <translation>Geometrinen predikaatti</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3325"/>
        <source>Output format</source>
        <translation>Tulostemuoto</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3583"/>
        <source>Filter</source>
        <translation>Suodatin</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3645"/>
        <source>Reset</source>
        <translation>Palauta</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2751"/>
        <source>Layers to export</source>
        <translation>Vietävät tasot</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2832"/>
        <source>Layers projection</source>
        <translation>Tasojen projektio</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2916"/>
        <source>Save styles</source>
        <translation>Tallenna tyylit</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2997"/>
        <source>Datatype export</source>
        <translation>Tietotyypin vienti</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3078"/>
        <source>Name of file/directory</source>
        <translation>Tiedoston/kansion nimi</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2205"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Kayta sentroideja taydellisten geometrioiden sijaan lahdetasolle (nopeampi monimutkaisille monikulmioille)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2521"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Puskuriarvo metrissa (positiivinen=laajenna, negatiivinen=kutista monikulmioita)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2609"/>
        <source>Number of segments for buffer precision</source>
        <translation>Segmenttien maara puskurin tarkkuuteen</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3421"/>
        <source>Mode batch</source>
        <translation>Eratila</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="281"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} kohdetta nakyvissa paatasolla</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="274"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Kaikki suodattimet poistettu - {count} kohdetta nakyvissa paatasolla</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="347"/>
        <source>Task failed</source>
        <translation>Tehtava epaonnistui</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="348"/>
        <source>Filter failed for: {0}</source>
        <translation>Suodatus epaonnistui kohteelle: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="352"/>
        <source> (+{0} more)</source>
        <translation> (+{0} lisaa)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="399"/>
        <source>Layer(s) filtered</source>
        <translation>Taso(t) suodatettu</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="403"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Taso(t) suodatettu edelliseen tilaan</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="407"/>
        <source>Layer(s) unfiltered</source>
        <translation>Taso(t) suodattamaton</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="411"/>
        <source>Filter task : {0}</source>
        <translation>Suodatustehtava: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="432"/>
        <source>Export task : {0}</source>
        <translation>Vientitehtava: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="457"/>
        <source>Exception: {0}</source>
        <translation>Poikkeus: {0}</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Python-valikot ja tyokalurivit</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Ominaisuus</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Arvo</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Ominaisuus</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Arvo</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="212"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>PostgreSQL-tasoja havaittu ({0}), mutta psycopg2 ei ole asennettu. Laajennus ei voi kayttaa naita tasoja. Asenna psycopg2 ottaaksesi PostgreSQL-tuen kayttoon.</translation>
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
        <translation>PostgreSQL-taso &apos;{0}&apos;: Vioittunut data havaittu.

Tama taso kayttaa &apos;virtual_id&apos;-tunnistetta, jota ei ole PostgreSQL:ssa.
Tama virhe on peraisin FilterMaten aiemmasta versiosta.

Ratkaisu: Poista tama taso FilterMate-projektista ja lisaa se uudelleen.
Varmista, etta PostgreSQL-taululla on PRIMARY KEY maaritettyna.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="970"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>Tasolla &apos;{0}&apos; ei ole PRIMARY KEY -avainta. Rajoitettu toiminnallisuus: materialisoidut nakymat poistettu kaytosta. Suositus: lisaa PRIMARY KEY optimaalisen suorituskyvyn varmistamiseksi.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1909"/>
        <source>Exception: {0}</source>
        <translation>Poikkeus: {0}</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Optimointiasetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Määritä optimointiasetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Ota automaattiset optimoinnit käyttöön</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Kysy ennen optimointien käyttöönottoa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Automaattiset keskipisteaseukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Ota automaattiset keskipisteet käyttöön etäisille tasoille</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Etäisyyskynnys (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Kohdekynnys:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Puskurin optimoinnit</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Yksinkertaista geometria ennen puskuria</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Vähennä puskurisegmentit:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Yleiset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Käytä materialisoituja näkymiä suodatukseen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Luo paikkatietoindeksit automaattisesti</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Käytä R-puu paikkatietoindeksiä</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Käytä rajauskehyksen esisuodatinta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Taustajärjestelmät</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Välimuistiin tallentaminen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Ota geometriavälimuisti käyttöön</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Erätoiminta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Eräkoko:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Lisäasetukset vaikuttavat suorituskykyyn ja muistin käyttöön. Muuta vain jos ymmärrät seuraukset.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Lisäasetukset</translation>
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
        <translation>PostgreSQL-istunnon tiedot</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL aktiivinen</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Yhteystiedot</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Yhteys:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Väliaikainen skeema:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Tila:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Väliaikaiset näkymät</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Puhdistusasetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Automaattinen puhdistus suljettaessa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Puhdista väliaikaiset näkymät automaattisesti kun FilterMate sulkeutuu.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Puhdista nyt</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Poista kaikki FilterMaten tässä istunnossa luomat väliaikaiset näkymät.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Ei väliaikaisia näkymiä)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Ei näkymiä</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Ei puhdistettavia väliaikaisia näkymiä.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Vahvista puhdistus</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Puhdistus valmis</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Puhdistusongelma</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Puhdistus epäonnistui</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;PostgreSQL ei ole kaytettavissa&lt;/b&gt;&lt;br&gt;&lt;br&gt;Kayttaaksesi PostgreSQL-ominaisuuksia, asenna psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Kaynnista sitten QGIS uudelleen ottaaksesi muutokset kayttoon.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Istunto: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} nakymaa tassa istunnossa</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Tama poistaa {view_count} FilterMaten luomaa tilapaista nakymaa.

Tallentamattomat suodatustulokset menetetaan.

Jatketaanko?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>{result.views_dropped} tilapaista nakymaa poistettu.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Joitakin nakymia ei voitu poistaa: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Virhe siivouksen aikana: {str(e)}</translation>
    </message>
</context>
<context>
    <name>PublishFavoritesDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="125"/>
        <source>FilterMate — Publish to Resource Sharing</source>
        <translation>FilterMate — Julkaise Resource Sharingiin</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="133"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Julkaise suosikit&lt;/b&gt; — kirjoita jaettava paketti QGIS Resource Sharing -kokoelmaan.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="153"/>
        <source>Overwrite existing bundle</source>
        <translation>Korvaa olemassa oleva paketti</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="163"/>
        <source>Publish</source>
        <translation>Julkaise</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="177"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Kohdekokoelma&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="190"/>
        <source>Browse...</source>
        <translation>Selaa…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="198"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Pakettitiedoston nimi&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="200"/>
        <source>e.g. zones_bruxelles</source>
        <translation>esim. alueet_bryssel</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="203"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;kohde&amp;gt;/filter_mate/favorites/&amp;lt;nimi&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Kokoelman metatiedot&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="214"/>
        <source>Collection display name</source>
        <translation>Kokoelman näyttönimi</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="215"/>
        <source>Name:</source>
        <translation>Nimi:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="218"/>
        <source>Author / organisation</source>
        <translation>Tekijä / organisaatio</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="219"/>
        <source>Author:</source>
        <translation>Tekijä:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="222"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>esim. CC-BY-4.0, MIT, Suljettu</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="223"/>
        <source>License:</source>
        <translation>Lisenssi:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="226"/>
        <source>Comma-separated tags</source>
        <translation>Pilkulla erotellut tunnisteet</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="227"/>
        <source>Tags:</source>
        <translation>Tunnisteet:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="230"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="231"/>
        <source>Homepage:</source>
        <translation>Kotisivu:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="235"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Lyhyt kuvaus (valinnainen, tavallinen teksti)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="238"/>
        <source>Description:</source>
        <translation>Kuvaus:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="250"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Sisällytettävät suosikit&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="254"/>
        <source>Select all</source>
        <translation>Valitse kaikki</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="257"/>
        <source>Select none</source>
        <translation>Tyhjennä valinnat</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="284"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Uusi kokoelma Resource Sharing -juureen…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="288"/>
        <source>Custom directory...</source>
        <translation>Mukautettu hakemisto…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="340"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Luodaan Resource Sharing -juuren alle.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="345"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Napsauta &apos;Selaa…&apos; valitaksesi hakemiston.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="351"/>
        <source>Choose a collection directory</source>
        <translation>Valitse kokoelmahakemisto</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="402"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} valittu</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Cannot create collection</source>
        <translation>Kokoelmaa ei voi luoda</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="428"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Resource Sharing -juurta ei löydy. Käytä sen sijaan &apos;Selaa…&apos; valitaksesi hakemiston.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Choose a directory</source>
        <translation>Valitse hakemisto</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="445"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Napsauta &apos;Selaa…&apos; valitaksesi kohdehakemiston.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>No favorites selected</source>
        <translation>Suosikkeja ei ole valittu</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="474"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Valitse vähintään yksi julkaistava suosikki.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Publish failed</source>
        <translation>Julkaisu epäonnistui</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="498"/>
        <source>Unknown error.</source>
        <translation>Tuntematon virhe.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="505"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>{0} suosikki(a) julkaistu sijaintiin:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="509"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Kokoelman manifesti päivitetty:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="512"/>
        <source>Publish succeeded</source>
        <translation>Julkaisu onnistui</translation>
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
        <translation>Kuvaus:</translation>
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
        <translation>Taso</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="157"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="178"/>
        <source>Export</source>
        <translation>Vie</translation>
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
        <translation>Virhe: {0}</translation>
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
        <translation>Tila:</translation>
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
        <translation>Kirjoita suodattaaksesi...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="661"/>
        <source>Select All</source>
        <translation>Valitse kaikki</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="663"/>
        <source>Select All (non subset)</source>
        <translation>Valitse kaikki (ei osajoukko)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="665"/>
        <source>Select All (subset)</source>
        <translation>Valitse kaikki (osajoukko)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="667"/>
        <source>De-select All</source>
        <translation>Poista kaikki valinnat</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="669"/>
        <source>De-select All (non subset)</source>
        <translation>Poista kaikki valinnat (ei osajoukko)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="671"/>
        <source>De-select All (subset)</source>
        <translation>Poista kaikki valinnat (osajoukko)</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="220"/>
        <source>Select All</source>
        <translation>Valitse kaikki</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="222"/>
        <source>De-select All</source>
        <translation>Poista kaikki valinnat</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="224"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Valitse kaikki tasot geometriatyypin mukaan (Viivat)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="226"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Poista kaikkien tasojen valinta geometriatyypin mukaan (Viivat)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="228"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Valitse kaikki tasot geometriatyypin mukaan (Pisteet)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="230"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Poista kaikkien tasojen valinta geometriatyypin mukaan (Pisteet)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="232"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Valitse kaikki tasot geometriatyypin mukaan (Monikulmiot)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="234"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Poista kaikkien tasojen valinta geometriatyypin mukaan (Monikulmiot)</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Ota optimoinnit käyttöön?</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Käytettävissä olevat optimoinnit</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Ohita</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Käytä valittuja</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} u2022 {1} kohdetta</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Vaikutus: {0}</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="75"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Hae asetuksista... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="180"/>
        <source>No match</source>
        <translation>Ei tuloksia</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="55"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Jaetut suosikit</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="63"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Jaetut suosikit&lt;/b&gt; — löydetty QGIS Resource Sharing -kokoelmista</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation>Hae nimen, kuvauksen, kokoelman tai tunnisteiden mukaan…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="98"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Valitse jaettu suosikki esikatselua varten.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="114"/>
        <source>Rescan</source>
        <translation>Skannaa uudelleen</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="118"/>
        <source>Fork to my project</source>
        <translation>Forkkaa projektiini</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="124"/>
        <source>Close</source>
        <translation>Sulje</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="139"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Jaettuja kokoelmia ei löytynyt. Tilaa Resource Sharing -tietovarasto, joka sisältää &lt;code&gt;filter_mate/favorites&lt;/code&gt; -kansion, tai pudota &lt;code&gt;.fmfav.json&lt;/code&gt; -paketti resource_sharing-kokoelmahakemistoosi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="147"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} suosikki(a) {1} kokoelmassa: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="160"/>
        <source>Collection: {0}</source>
        <translation>Kokoelma: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation>Mikään jaettu suosikki ei vastaa hakuasi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="194"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — lähteestä &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="208"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Lauseke&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="213"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Etätasot&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="227"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Tunnisteet:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="234"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Alkuperä&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="236"/>
        <source>Author: {0}</source>
        <translation>Tekijä: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="238"/>
        <source>License: {0}</source>
        <translation>Lisenssi: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Fork shared favorite</source>
        <translation>Forkkaa jaettu suosikki</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="254"/>
        <source>Name in your project:</source>
        <translation>Nimi projektissasi:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>Fork successful</source>
        <translation>Forkkaus onnistui</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="268"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>«{0}» lisättiin suosikkeihisi.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Fork failed</source>
        <translation>Forkkaus epäonnistui</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="274"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Jaettua suosikkia ei voitu lisätä projektiisi.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="468"/>
        <source>Reset to Defaults</source>
        <translation>Palauta oletusasetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Validation Error</source>
        <translation>Vahvistusvirhe</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="500"/>
        <source>Please fix the following errors:

</source>
        <translation>Korjaa seuraavat virheet:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset Configuration</source>
        <translation>Nollaa asetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="511"/>
        <source>Reset all values to defaults?</source>
        <translation>Palauta kaikki arvot oletusarvoihin?</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="151"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - PostgreSQL tyyppivaroitus</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="155"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Tyyppivirhe suodattimessa: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="568"/>
        <source>Reset to Defaults</source>
        <translation>Palauta oletusasetukset</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="588"/>
        <source>General</source>
        <translation>Yleinen</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="268"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} kohdetta nakyvissa paatasolla</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="261"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Kaikki suodattimet poistettu - {count} kohdetta nakyvissa paatasolla</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="291"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Suodatin kaytetty tasolle &apos;{layer_name}&apos;: {count} kohdetta</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="296"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="312"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Suodatin poistettu tasolta &apos;{layer_name}&apos;: {count} kohdetta nakyvissa</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="909"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Kohdetta ei ole valittu! Valintawidget menetti kohteen. Valitse kohde uudelleen.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1027"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Valittu taso on virheellinen tai sen lahdetta ei loydy. Toiminto peruutettu.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1042"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>Tasoa &apos;{0}&apos; ei ole viela alustettu. Kokeile valita toinen taso ja vaihda sitten takaisin.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="178"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Kumoaminen ei onnistu: taso virheellinen tai lahdetta ei loydy.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="255"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Uudelleenteko ei onnistu: taso virheellinen tai lahdetta ei loydy.</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="556"/>
        <source>Explore ...</source>
        <translation>Selaa...</translation>
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
