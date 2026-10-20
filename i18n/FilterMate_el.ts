<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="el_GR" sourcelanguage="en_US">
<context>
    <name>@default</name>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="312"/>
        <source>Import from Resource Sharing...</source>
        <translation>Εισαγωγή από το Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish to Resource Sharing...</source>
        <translation>Δημοσίευση στο Resource Sharing...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="319"/>
        <source>Publish (no favorites saved)</source>
        <translation>Δημοσίευση (δεν υπάρχουν αποθηκευμένα αγαπημένα)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="332"/>
        <source>Quick publish to default repo</source>
        <translation>Γρήγορη δημοσίευση στο προεπιλεγμένο αποθετήριο</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/extension.py" line="337"/>
        <source>Manage Resource Sharing repos...</source>
        <translation>Διαχείριση αποθετηρίων Resource Sharing...</translation>
    </message>
</context>
<context>
    <name>AppInitializer</name>
    <message>
        <location filename="../core/services/app_initializer.py" line="175"/>
        <source>Cleared corrupted filters from {0} layer(s). Please re-apply your filters.</source>
        <translation>Διαγράφηκαν κατεστραμμένα φίλτρα από {0} επίπεδο(-α). Παρακαλώ εφαρμόστε ξανά τα φίλτρα σας.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="244"/>
        <source>Empty project detected. Add vector layers to activate the plugin.</source>
        <translation>Εντοπίστηκε κενό έργο. Προσθέστε διανυσματικά επίπεδα για να ενεργοποιήσετε το πρόσθετο.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="311"/>
        <source>Cannot access the FilterMate database. Check the project directory permissions.</source>
        <translation>Δεν είναι δυνατή η πρόσβαση στη βάση δεδομένων FilterMate. Ελέγξτε τα δικαιώματα του καταλόγου έργου.</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="325"/>
        <source>Error during database verification: {0}</source>
        <translation>Σφάλμα κατά τον έλεγχο βάσης δεδομένων: {0}</translation>
    </message>
    <message>
        <location filename="../core/services/app_initializer.py" line="605"/>
        <source>Layer loading failed. Use F5 to force reload.</source>
        <translation>Η φόρτωση επιπέδου απέτυχε. Χρησιμοποιήστε F5 για αναγκαστική επαναφόρτωση.</translation>
    </message>
</context>
<context>
    <name>AttributeFilterExecutor</name>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="379"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server.</source>
        <translation>{0}: αυτή η διαδικτυακή υπηρεσία δεν έχει μοναδικό πεδίο κλειδιού (δηλωμένο κλειδί, id, gml_id, cleabs, objectid…), επομένως οι επιλεγμένες οντότητες δεν μπορούν να απαριθμηθούν για τον διακομιστή.</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="384"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid).</source>
        <translation>{0}: αυτό το επίπεδο δεν έχει μοναδικό πεδίο κλειδιού και τα αναγνωριστικά των οντοτήτων του δεν μπορούν να απαριθμηθούν στο φίλτρο του (ένα εικονικό επίπεδο χρειάζεται στήλη μοναδικού id, το uid του).</translation>
    </message>
    <message>
        <location filename="../core/tasks/executors/attribute_filter_executor.py" line="391"/>
        <source>{0}: {1} selected features, more than the {2} sent to a web service. Narrow the selection or use an attribute filter.</source>
        <translation>{0}: {1} επιλεγμένες οντότητες, περισσότερες από τις {2} που στέλνονται σε διαδικτυακή υπηρεσία. Περιορίστε την επιλογή ή χρησιμοποιήστε φίλτρο χαρακτηριστικών.</translation>
    </message>
</context>
<context>
    <name>BackendController</name>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="110"/>
        <source>Remote file: every read goes over the network. FilterMate does not count its features on the main thread.</source>
        <translation>Απομακρυσμένο αρχείο: κάθε ανάγνωση γίνεται μέσω δικτύου. Το FilterMate δεν μετρά τις οντότητές του στο κύριο νήμα.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="115"/>
        <source>Remote service: the filter is sent to the server when it can translate it. FilterMate does not count its features on the main thread.</source>
        <translation>Απομακρυσμένη υπηρεσία: το φίλτρο στέλνεται στον διακομιστή όταν μπορεί να το μεταφράσει. Το FilterMate δεν μετρά τις οντότητές της στο κύριο νήμα.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="120"/>
        <source>A filter by feature list is limited to {0} features.</source>
        <translation>Ένα φίλτρο με λίστα οντοτήτων περιορίζεται σε {0} οντότητες.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="123"/>
        <source>Remote</source>
        <translation>Απομακρυσμένο</translation>
    </message>
</context>
<context>
    <name>BackendIndicatorWidget</name>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="185"/>
        <source>Select Backend:</source>
        <translation>Επιλογή backend:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="204"/>
        <source>Auto (Default)</source>
        <translation>Αυτόματο (Προεπιλογή)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="212"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Αυτόματη βέλτιστη επιλογή για όλα τα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="222"/>
        <source>Force {0} for All Layers</source>
        <translation>Επιβολή {0} για όλα τα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="265"/>
        <source>Click to reload layers</source>
        <translation>Κλικ για επαναφόρτωση επιπέδων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/backend_indicator.py" line="300"/>
        <source>Click to change backend</source>
        <translation>Κλικ για αλλαγή backend</translation>
    </message>
</context>
<context>
    <name>CentroidTargetsSync</name>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Test the checked line and polygon targets by their centroids (point on surface): faster on large geometries. Each target has its own square in the list</source>
        <translation>Έλεγχος των επιλεγμένων στόχων γραμμών και πολυγώνων με τα κεντροειδή τους (σημείο στην επιφάνεια): ταχύτερο σε μεγάλες γεωμετρίες. Κάθε στόχος έχει το δικό του τετράγωνο στη λίστα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/centroid_targets_sync.py" line="186"/>
        <source>Centroids apply to line and polygon targets: check one in the list of layers to filter</source>
        <translation>Τα κεντροειδή ισχύουν για στόχους γραμμών και πολυγώνων: επιλέξτε έναν στη λίστα των επιπέδων προς φιλτράρισμα</translation>
    </message>
</context>
<context>
    <name>ConfigController</name>
    <message>
        <location filename="../ui/controllers/config_controller.py" line="380"/>
        <source>Error cancelling changes: {0}</source>
        <translation>Σφάλμα ακύρωσης αλλαγών: {0}</translation>
    </message>
</context>
<context>
    <name>ControllerIntegration</name>
    <message>
        <location filename="../ui/controllers/integration.py" line="645"/>
        <source>Property error: {0}</source>
        <translation>Σφάλμα ιδιότητας: {0}</translation>
    </message>
</context>
<context>
    <name>CoverageDockExtras</name>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="303"/>
        <source>1 band</source>
        <translation>1 κανάλι</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="304"/>
        <source>{0} bands</source>
        <translation>{0} κανάλια</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="305"/>
        <source>{0} points</source>
        <translation>{0} σημεία</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation>Γεωμετρία πηγής: τα επιλεγμένα εικονοστοιχεία, διανυσματοποιημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="792"/>
        <source>Source geometry: the footprint of the kept points</source>
        <translation>Γεωμετρία πηγής: το αποτύπωμα των σημείων που διατηρούνται</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="739"/>
        <source>Source geometry: the features selected in EXPLORING</source>
        <translation>Γεωμετρία πηγής: οι οντότητες που επιλέχθηκαν στην ΕΞΕΡΕΥΝΗΣΗ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Value under the cursor: follow the pixel value of the current band while moving over the map</source>
        <translation type="obsolete">Τιμή κάτω από τον δρομέα: παρακολούθηση της τιμής εικονοστοιχείου του τρέχοντος καναλιού κατά την κίνηση στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="250"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band</source>
        <translation type="obsolete">Στατιστικά ορθογωνίου: σύρετε στον χάρτη για ελάχιστο, μέγιστο και μέσο όρο του τρέχοντος καναλιού</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Elevation profile: open the QGIS elevation profile of the map</source>
        <translation>Προφίλ υψομέτρου: άνοιγμα του προφίλ υψομέτρου του QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>3D view: open a new QGIS 3D map view</source>
        <translation>Προβολή 3D: άνοιγμα νέας προβολής χάρτη 3D του QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="264"/>
        <source>no feature</source>
        <translation type="obsolete">κανένα στοιχείο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="310"/>
        <source>{0} feature(s)</source>
        <translation>{0} στοιχείο(α)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="266"/>
        <source>every pixel</source>
        <translation type="obsolete">όλα τα εικονοστοιχεία</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="315"/>
        <source>{0} class(es)</source>
        <translation>{0} κλάση(εις)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="312"/>
        <source>expression</source>
        <translation>έκφραση</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="306"/>
        <source>{0} features</source>
        <translation>{0} στοιχεία</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Vector</source>
        <translation>Διανυσματικό</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Raster</source>
        <translation>Ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="807"/>
        <source>Point cloud</source>
        <translation>Νέφος σημείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="795"/>
        <source>Kept points</source>
        <translation>Διατηρούμενα σημεία</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="776"/>
        <source>Selection → source geometry</source>
        <translation>Επιλογή → γεωμετρία πηγής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="384"/>
        <source>Link the range to the style: the layer colours stretch over the selected range</source>
        <translation>Σύνδεση εύρους με το στυλ: τα χρώματα του επιπέδου απλώνονται στο επιλεγμένο εύρος</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="385"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Σταγονόμετρο κλάσης: κάντε κλικ στον χάρτη και επιλέγεται η κλάση των σημείων που σχεδιάζονται εκεί. Το Ctrl+κλικ προσθέτει μία ακόμη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value under the cursor: follow the pixel value (or the slope, aspect... the range applies to) while moving over the map</source>
        <translation>Τιμή κάτω από τον δρομέα: παρακολούθηση της τιμής εικονοστοιχείου (ή της κλίσης, του προσανατολισμού... στην οποία εφαρμόζεται το εύρος) κατά την κίνηση στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Statistics of a rectangle: drag on the map to read the minimum, maximum and mean of the current band (or of the slope, aspect... the range applies to)</source>
        <translation>Στατιστικά ορθογωνίου: σύρετε στον χάρτη για ελάχιστο, μέγιστο και μέσο όρο του τρέχοντος καναλιού (ή της κλίσης, του προσανατολισμού... στην οποία εφαρμόζεται το εύρος)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="569"/>
        <source>The style link follows pixel values: not available while the range applies to a slope, aspect, hillshade or roughness</source>
        <translation>Η σύνδεση στυλ παρακολουθεί τις τιμές εικονοστοιχείων: μη διαθέσιμη όταν το εύρος εφαρμόζεται σε κλίση, προσανατολισμό, σκίαση αναγλύφου ή τραχύτητα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="920"/>
        <source>Class pipette: this point cloud has no Classification attribute</source>
        <translation>Σταγονόμετρο κλάσης: αυτό το νέφος σημείων δεν έχει χαρακτηριστικό Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1526"/>
        <source>The style cannot follow the range: it needs a single band grey or pseudocolor style on the band of the panel</source>
        <translation>Το στυλ δεν μπορεί να παρακολουθήσει το εύρος: απαιτεί στυλ γκρι ή ψευδοχρώματος ενός καναλιού στο κανάλι του πίνακα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Pipette: click the map and the pixels that look like the one you click are selected (a color on an image, a value on a DTM or an index, a class on a classified raster, with the tolerance of the panel). Ctrl+click adds another one</source>
        <translation>Σταγονόμετρο: κάντε κλικ στον χάρτη και επιλέγονται τα εικονοστοιχεία που μοιάζουν με αυτό που πατήσατε (ένα χρώμα σε εικόνα, μια τιμή σε DTM ή δείκτη, μια κλάση σε ταξινομημένο ράστερ, με την ανοχή του πίνακα). Το Ctrl+κλικ προσθέτει ένα ακόμη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="311"/>
        <source>no feature selected</source>
        <translation>κανένα στοιχείο δεν επιλέχθηκε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="313"/>
        <source>whole layer</source>
        <translation>ολόκληρο το επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="314"/>
        <source>no constraint</source>
        <translation>χωρίς περιορισμό</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="316"/>
        <source>raster expression</source>
        <translation>έκφραση ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="317"/>
        <source>all points</source>
        <translation>όλα τα σημεία</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="318"/>
        <source>{0} object(s)</source>
        <translation>{0} αντικείμενο(α)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="319"/>
        <source>shown as the whole class in their box</source>
        <translation>εμφανίζονται ως ολόκληρη η κλάση στο πλαίσιό τους</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="388"/>
        <source>Object detector: click the map and the patch of pixels that look like the one you click is selected (a pool, a roof, a field, with the tolerance of the panel), not every pixel of its colour. Ctrl+click adds another object</source>
        <translation>Ανιχνευτής αντικειμένων: κάντε κλικ στον χάρτη και επιλέγεται η κηλίδα εικονοστοιχείων που μοιάζουν με αυτό του κλικ (πισίνα, στέγη, χωράφι, με την ανοχή του πίνακα), όχι όλα τα εικονοστοιχεία του χρώματός του. Το Ctrl+κλικ προσθέτει άλλο αντικείμενο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar objects: click an object and every object of the raster like it is selected (the patches of such pixels whose area is within the ratios of the panel). Ctrl+click adds another reference object</source>
        <translation>Παρόμοια αντικείμενα: κάντε κλικ σε ένα αντικείμενο και επιλέγονται όλα τα παρόμοια αντικείμενα του ράστερ (οι κηλίδες τέτοιων εικονοστοιχείων με εμβαδόν εντός των λόγων του πίνακα). Το Ctrl+κλικ προσθέτει άλλο αντικείμενο αναφοράς</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Object detector: click the map and the object under the click is selected (the cluster of points of its class: a building, a tree), not the whole class; or every object of the cloud like it (right-click the button for the target). Ctrl+click adds another object</source>
        <translation>Ανιχνευτής αντικειμένων: κάντε κλικ στον χάρτη και επιλέγεται το αντικείμενο κάτω από το κλικ (το σύμπλεγμα σημείων της κλάσης του: κτίριο, δέντρο), όχι ολόκληρη η κλάση· ή κάθε παρόμοιο αντικείμενο του νέφους (δεξί κλικ στο κουμπί για τον στόχο). Το Ctrl+κλικ προσθέτει άλλο αντικείμενο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Value pipette: click the map and a condition is written on the attribute chosen in ATTRIBUTES (Z, intensity...), around the value of the point there, with the tolerance of the panel. Ctrl+click adds another condition (OR)</source>
        <translation>Σταγονόμετρο τιμών: κάντε κλικ στον χάρτη και γράφεται μια συνθήκη για το χαρακτηριστικό που επιλέχθηκε στα ΧΑΡΑΚΤΗΡΙΣΤΙΚΑ (Z, ένταση…), γύρω από την τιμή του σημείου εκεί, με την ανοχή του πίνακα. Το Ctrl+κλικ προσθέτει άλλη συνθήκη (OR)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Zone: draw a rectangle, a polygon, a freehand shape or a circle on the map (right-click the button for the shape); its X / Y box goes to ATTRIBUTES, the shape itself cuts the targets</source>
        <translation>Ζώνη: σχεδιάστε στον χάρτη ορθογώνιο, πολύγωνο, ελεύθερο σχήμα ή κύκλο (δεξί κλικ στο κουμπί για το σχήμα)· το πλαίσιο X / Y πηγαίνει στα ΧΑΡΑΚΤΗΡΙΣΤΙΚΑ, το ίδιο το σχήμα περικόπτει τους στόχους</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the value under the cursor, the statistics of a rectangle</source>
        <translation>Άλλα εργαλεία: η τιμή κάτω από τον δείκτη, τα στατιστικά ενός ορθογωνίου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>Similar features: click a feature and every feature of the layer with the same value of the group&apos;s field (the display expression of the single / multiple selection) is selected. Ctrl+click adds another value</source>
        <translation>Παρόμοιες οντότητες: κάντε κλικ σε μια οντότητα και επιλέγονται όλες οι οντότητες του επιπέδου με την ίδια τιμή του πεδίου της ομάδας (η έκφραση εμφάνισης της μονής / πολλαπλής επιλογής). Το Ctrl+κλικ προσθέτει άλλη τιμή</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the QGIS selection tools (rectangle, polygon, freehand, radius), select by expression, invert or clear the selection, the attribute table of the selection</source>
        <translation>Άλλα εργαλεία: τα εργαλεία επιλογής του QGIS (ορθογώνιο, πολύγωνο, ελεύθερο σχήμα, ακτίνα), επιλογή με έκφραση, αντιστροφή ή εκκαθάριση της επιλογής, ο πίνακας χαρακτηριστικών της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="392"/>
        <source>More tools: the elevation profile and the 3D view of QGIS</source>
        <translation>Άλλα εργαλεία: το προφίλ υψομέτρου και η προβολή 3D του QGIS</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="539"/>
        <source>Only color selection is available: rendered colors depend on style and scale.</source>
        <translation>Διατίθεται μόνο επιλογή με βάση το χρώμα: τα αποδιδόμενα χρώματα εξαρτώνται από το στυλ και την κλίμακα.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="567"/>
        <source>The style link follows the VALUE RANGE group: make it the active one first</source>
        <translation>Η σύνδεση στυλ ακολουθεί την ομάδα ΕΥΡΟΣ ΤΙΜΩΝ: κάντε την πρώτα ενεργή</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="794"/>
        <source>Current filter: {0}</source>
        <translation>Τρέχον φίλτρο: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="830"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>Τα αποδιδόμενα χρώματα εξαρτώνται από το στυλ και την κλίμακα.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="929"/>
        <source>Object detector: this point cloud has no Classification attribute</source>
        <translation>Ανιχνευτής αντικειμένων: αυτό το νέφος σημείων δεν έχει χαρακτηριστικό Classification</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="978"/>
        <source>Object detector</source>
        <translation>Ανιχνευτής αντικειμένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Clicked object</source>
        <translation>Αντικείμενο του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="981"/>
        <source>Similar objects</source>
        <translation>Παρόμοια αντικείμενα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1085"/>
        <source>Zone shape</source>
        <translation>Σχήμα ζώνης</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Rectangle</source>
        <translation>Ορθογώνιο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1258"/>
        <source>Polygon</source>
        <translation>Πολύγωνο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Freehand</source>
        <translation>Ελεύθερο σχέδιο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1259"/>
        <source>Radius</source>
        <translation>Ακτίνα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1134"/>
        <source>The link follows the single and multiple selections: make one of them the active group first</source>
        <translation>Η σύνδεση ακολουθεί τη μονή και την πολλαπλή επιλογή: κάντε πρώτα μία από αυτές ενεργή ομάδα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1257"/>
        <source>Select on the map</source>
        <translation>Επιλογή στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Select by expression…</source>
        <translation>Επιλογή με έκφραση…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Invert the selection</source>
        <translation>Αντιστροφή της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1265"/>
        <source>Clear the selection</source>
        <translation>Εκκαθάριση της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1272"/>
        <source>Attribute table of the selection</source>
        <translation>Πίνακας χαρακτηριστικών της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1311"/>
        <source>Value under the cursor</source>
        <translation>Τιμή κάτω από τον δείκτη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1315"/>
        <source>Statistics of a rectangle</source>
        <translation>Στατιστικά ορθογωνίου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>Elevation profile</source>
        <translation>Προφίλ υψομέτρου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1331"/>
        <source>3D view</source>
        <translation>Προβολή 3D</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="1688"/>
        <source>This point cloud has no X / Y attribute to filter on</source>
        <translation>Αυτό το νέφος σημείων δεν έχει χαρακτηριστικό X / Y για φιλτράρισμα</translation>
    </message>
</context>
<context>
    <name>CoverageModeController</name>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="365"/>
        <source>Restoring the filter of {0} raster / point cloud layer(s)…</source>
        <translation>Επαναφορά του φίλτρου {0} επιπέδου(ων) ράστερ / νέφους σημείων…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="747"/>
        <source>cov. ≥ </source>
        <translation>κάλ. ≥ </translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="748"/>
        <source>Minimum share of a polygon target inside the source geometry (0 = any overlap). Used when the source is a raster or a point cloud.</source>
        <translation>Ελάχιστο ποσοστό ενός πολυγωνικού στόχου εντός της γεωμετρίας πηγής (0 = οποιαδήποτε επικάλυψη). Χρησιμοποιείται όταν η πηγή είναι ράστερ ή νέφος σημείων.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Raster</source>
        <translation>Ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="863"/>
        <source>Point cloud</source>
        <translation>Νέφος σημείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="872"/>
        <source>{0} layer: selection in EXPLORING, relation in FILTERING</source>
        <translation>Επίπεδο {0}: επιλογή στο EXPLORING, σχέση στο FILTERING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="586"/>
        <source>Pixel picker: click on the map to read the value of every band (Ctrl+click extends the range)</source>
        <translation type="obsolete">Επιλογέας εικονοστοιχείων: κάντε κλικ στον χάρτη για να διαβάσετε την τιμή κάθε καναλιού (το Ctrl+κλικ επεκτείνει το εύρος)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="918"/>
        <source>Zoom to the layer</source>
        <translation>Εστίαση στο επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="588"/>
        <source>Preview: hide the pixels outside the selection</source>
        <translation type="obsolete">Προεπισκόπηση: απόκρυψη των εικονοστοιχείων εκτός της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="911"/>
        <source>Not used for raster layers</source>
        <translation>Δεν χρησιμοποιείται για επίπεδα ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="912"/>
        <source>Reset the raster selection</source>
        <translation>Επαναφορά της επιλογής ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="733"/>
        <source>Identify points on the map</source>
        <translation type="obsolete">Αναγνώριση σημείων στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="919"/>
        <source>Live preview: show only the points kept by the selection</source>
        <translation>Ζωντανή προεπισκόπηση: εμφάνιση μόνο των σημείων που διατηρούνται από την επιλογή</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="921"/>
        <source>Not used for point cloud layers</source>
        <translation>Δεν χρησιμοποιείται για επίπεδα νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="922"/>
        <source>Reset the point cloud criteria</source>
        <translation>Επαναφορά των κριτηρίων του νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1390"/>
        <source>Invalid raster calculator expression</source>
        <translation>Μη έγκυρη έκφραση υπολογιστή ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1688"/>
        <source>PDAL was not found: the height above a DTM needs the pdal executable</source>
        <translation>Το PDAL δεν βρέθηκε: το ύψος πάνω από ένα DTM απαιτεί το εκτελέσιμο pdal</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3151"/>
        <source>A FilterMate task is still running: wait for it to finish</source>
        <translation>Μια εργασία του FilterMate εκτελείται ακόμη: περιμένετε να ολοκληρωθεί</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2629"/>
        <source>FilterMate task failed: {0}</source>
        <translation>Η εργασία του FilterMate απέτυχε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2666"/>
        <source>Select pixels first: a value range, classes or a raster expression</source>
        <translation>Επιλέξτε πρώτα εικονοστοιχεία: ένα εύρος τιμών, κλάσεις ή μια έκφραση ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2679"/>
        <source>Raster filtered: {0}</source>
        <translation>Το ράστερ φιλτραρίστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2713"/>
        <source>The point cloud expression was rejected: {0}</source>
        <translation>Η έκφραση του νέφους σημείων απορρίφθηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2716"/>
        <source>Select points first: classes, attribute ranges or an expression</source>
        <translation>Επιλέξτε πρώτα σημεία: κλάσεις, εύρη χαρακτηριστικών ή μια έκφραση</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2730"/>
        <source>Point cloud filtered: {0}</source>
        <translation>Το νέφος σημείων φιλτραρίστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3261"/>
        <source>Filter not applied: {0}</source>
        <translation>Το φίλτρο δεν εφαρμόστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>canceled</source>
        <translation>ακυρώθηκε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2812"/>
        <source>{0} target(s) filtered</source>
        <translation>{0} στόχος(οι) φιλτραρίστηκε(αν)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2823"/>
        <source>{0} failed: {1}</source>
        <translation>{0} απέτυχε: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2836"/>
        <source>FilterMate: filtering from '{0}'…</source>
        <translation>FilterMate: φιλτράρισμα από το '{0}'…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2933"/>
        <source>Changed since, left as is: {0}</source>
        <translation>Τροποποιήθηκε στο μεταξύ, παραμένει ως έχει: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2939"/>
        <source>{0} layer(s) restored</source>
        <translation>{0} επίπεδο(α) επαναφέρθηκε(αν)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2973"/>
        <source>&apos;{0}&apos; not exported: {1}</source>
        <translation>Το '{0}' δεν εξήχθη: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2987"/>
        <source>Exported: {0}</source>
        <translation>Εξήχθη: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2989"/>
        <source>Export failed: {0}</source>
        <translation>Η εξαγωγή απέτυχε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2996"/>
        <source>Exporting {0} layer(s)…</source>
        <translation>Εξαγωγή {0} επιπέδου(ων)…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3002"/>
        <source>Export folder</source>
        <translation>Φάκελος εξαγωγής</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3084"/>
        <source>Raster / point cloud targets skipped: no source feature selected in EXPLORING</source>
        <translation>Παραλείφθηκαν οι στόχοι ράστερ / νέφους σημείων: δεν έχει επιλεγεί οντότητα πηγής στο EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3113"/>
        <source>Raster / point cloud targets not filtered: {0}</source>
        <translation>Οι στόχοι ράστερ / νέφους σημείων δεν φιλτραρίστηκαν: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3115"/>
        <source>{0} raster / point cloud target(s) filtered</source>
        <translation>{0} στόχος(οι) ράστερ / νέφους σημείων φιλτραρίστηκε(αν)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3238"/>
        <source>Choose the DTM raster used for the height above ground</source>
        <translation>Επιλέξτε το ράστερ DTM που χρησιμοποιείται για το ύψος πάνω από το έδαφος</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3249"/>
        <source>Height above ground not computed: {0}</source>
        <translation>Το ύψος πάνω από το έδαφος δεν υπολογίστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="3270"/>
        <source>Computing the height above '{0}' with PDAL…</source>
        <translation>Υπολογισμός του ύψους πάνω από το '{0}' με το PDAL…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="342"/>
        <source>The FilterMate cache holds {0} GB, over its {1} GB limit: unfilter the raster / point cloud layers you no longer need</source>
        <translation>Η κρυφή μνήμη του FilterMate καταλαμβάνει {0} GB, πάνω από το όριό της των {1} GB: αφαιρέστε το φίλτρο από τα επίπεδα ράστερ / νέφους σημείων που δεν χρειάζεστε πλέον</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1690"/>
        <source>PDAL {0} is too old: the height above a DTM needs PDAL 2.4 or later</source>
        <translation>Το PDAL {0} είναι πολύ παλιό: το ύψος πάνω από ένα DTM απαιτεί PDAL 2.4 ή νεότερο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1693"/>
        <source>PDAL could not be run, the height above a DTM is unavailable: {0}</source>
        <translation>Δεν ήταν δυνατή η εκτέλεση του PDAL, το ύψος πάνω από ένα DTM δεν είναι διαθέσιμο: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="722"/>
        <source>Pixel picker: click on the map to read the value of every band, and the slope, aspect... when the range applies to one (Ctrl+click extends the range)</source>
        <translation type="obsolete">Επιλογέας εικονοστοιχείων: κάντε κλικ στον χάρτη για να διαβάσετε την τιμή κάθε καναλιού, καθώς και την κλίση, τον προσανατολισμό... όταν το εύρος εφαρμόζεται σε κάποιο από αυτά (το Ctrl+κλικ επεκτείνει το εύρος)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="907"/>
        <source>Zoom to the selected pixels (to the layer when nothing is selected)</source>
        <translation>Εστίαση στα επιλεγμένα εικονοστοιχεία (στο επίπεδο όταν δεν υπάρχει επιλογή)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="908"/>
        <source>Preview: hide the pixels outside the selection (a white veil for a slope, aspect...)</source>
        <translation>Προεπισκόπηση: απόκρυψη των εικονοστοιχείων εκτός της επιλογής (λευκό πέπλο για κλίση, προσανατολισμό...)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a slope or aspect needs the map in the CRS of the raster ({0})</source>
        <translation>Η προεπισκόπηση κλίσης ή προσανατολισμού απαιτεί τον χάρτη στο CRS του ράστερ ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2165"/>
        <source>only the points drawn on the map can be picked: turn the preview off to pick a class it hides</source>
        <translation>μόνο τα σημεία που σχεδιάζονται στον χάρτη μπορούν να επιλεγούν: απενεργοποιήστε την προεπισκόπηση για να επιλέξετε μια κλάση που αυτή αποκρύπτει</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2236"/>
        <source>No classified point under the click</source>
        <translation>Κανένα ταξινομημένο σημείο κάτω από το κλικ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2171"/>
        <source>Class {0} is already checked</source>
        <translation>Η κλάση {0} είναι ήδη επιλεγμένη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2260"/>
        <source>Class {0} is not in the class list of the layer</source>
        <translation>Η κλάση {0} δεν βρίσκεται στη λίστα κλάσεων του επιπέδου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="906"/>
        <source>Not used for raster layers: the pipette reads the bands</source>
        <translation>Δεν χρησιμοποιείται για επίπεδα ράστερ: το σταγονόμετρο διαβάζει τα κανάλια</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="915"/>
        <source>Class pipette: click the map and the class of the points drawn there is checked. Ctrl+click adds another one</source>
        <translation>Σταγονόμετρο κλάσης: κάντε κλικ στον χάρτη και επιλέγεται η κλάση των σημείων που σχεδιάζονται εκεί. Το Ctrl+κλικ προσθέτει άλλη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1070"/>
        <source>Preview and statistics use a bounded local sample of the visible extent; filtering reads the source.</source>
        <translation>Η προεπισκόπηση και τα στατιστικά χρησιμοποιούν ένα περιορισμένο τοπικό δείγμα της ορατής έκτασης· το φιλτράρισμα διαβάζει την πηγή.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1211"/>
        <source>Preparing a bounded color snapshot of the visible extent…</source>
        <translation>Προετοιμασία περιορισμένου στιγμιότυπου χρωμάτων της ορατής έκτασης…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1223"/>
        <source>The color snapshot could not be prepared. Try a smaller visible extent.</source>
        <translation>Δεν ήταν δυνατή η προετοιμασία του στιγμιότυπου χρωμάτων. Δοκιμάστε μικρότερη ορατή έκταση.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1227"/>
        <source>Color selection applies to the captured visible extent.</source>
        <translation>Η επιλογή χρώματος εφαρμόζεται στην καταγεγραμμένη ορατή έκταση.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1268"/>
        <source>Raster sampling failed. Try a smaller visible extent.</source>
        <translation>Η δειγματοληψία του ράστερ απέτυχε. Δοκιμάστε μικρότερη ορατή έκταση.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1515"/>
        <source>The sampled raster preview could not be calculated.</source>
        <translation>Δεν ήταν δυνατός ο υπολογισμός της προεπισκόπησης του δείγματος ράστερ.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="1569"/>
        <source>The preview of a color or an expression needs the map in the CRS of the raster ({0})</source>
        <translation>Η προεπισκόπηση χρώματος ή έκφρασης απαιτεί τον χάρτη στο CRS του ράστερ ({0})</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2189"/>
        <source>No point drawn under the click</source>
        <translation>Κανένα σημείο δεν σχεδιάζεται κάτω από το κλικ</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2191"/>
        <source>This point has no {0}</source>
        <translation>Αυτό το σημείο δεν έχει {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2193"/>
        <source>{0} cannot be used in a condition</source>
        <translation>Το {0} δεν μπορεί να χρησιμοποιηθεί σε συνθήκη</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2250"/>
        <source>Object not read: {0}</source>
        <translation>Το αντικείμενο δεν διαβάστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2252"/>
        <source>Too many points around the click: the object could not be read</source>
        <translation>Πάρα πολλά σημεία γύρω από το κλικ: το αντικείμενο δεν ήταν δυνατό να διαβαστεί</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2254"/>
        <source>No point of class {0} under the click: click on the object itself</source>
        <translation>Κανένα σημείο κλάσης {0} κάτω από το κλικ: κάντε κλικ στο ίδιο το αντικείμενο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2391"/>
        <source>Similar objects not read: {0}</source>
        <translation>Τα παρόμοια αντικείμενα δεν διαβάστηκαν: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2394"/>
        <source>No similar object within the area ratios: widen them</source>
        <translation>Κανένα παρόμοιο αντικείμενο εντός των λόγων εμβαδού: διευρύνετέ τους</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2462"/>
        <source>Preparing a sample for the new visible extent. Click again when it is ready.</source>
        <translation>Προετοιμασία δείγματος για τη νέα ορατή έκταση. Κάντε ξανά κλικ όταν είναι έτοιμο.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2469"/>
        <source>The local raster sample is still being prepared. Retry when it is ready.</source>
        <translation>Το τοπικό δείγμα ράστερ ετοιμάζεται ακόμη. Δοκιμάστε ξανά όταν είναι έτοιμο.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2673"/>
        <source>Prepare a color snapshot before filtering this rendered layer.</source>
        <translation>Προετοιμάστε ένα στιγμιότυπο χρωμάτων πριν φιλτράρετε αυτό το αποδιδόμενο επίπεδο.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2815"/>
        <source>{0} raster target(s) resampled to the configured pixel limit</source>
        <translation>{0} στόχος(οι) ράστερ επαναδειγματοληπτήθηκε(αν) στο ρυθμισμένο όριο εικονοστοιχείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2847"/>
        <source>color selection limited to the captured extent; colors depend on style and scale</source>
        <translation>η επιλογή χρώματος περιορίζεται στην καταγεγραμμένη έκταση· τα χρώματα εξαρτώνται από το στυλ και την κλίμακα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2849"/>
        <source>raster source resampled to {0} cells within the pixel limit</source>
        <translation>η πηγή ράστερ επαναδειγματοληπτήθηκε σε {0} κελιά εντός του ορίου εικονοστοιχείων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2851"/>
        <source>raster selection read every {0} pixels: over the pixel limit of the settings</source>
        <translation>η επιλογή ράστερ διαβάστηκε ανά {0} εικονοστοιχεία: πάνω από το όριο εικονοστοιχείων των ρυθμίσεων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2854"/>
        <source>dense raster selection smoothed to keep its outline light</source>
        <translation>η πυκνή επιλογή ράστερ εξομαλύνθηκε για να παραμείνει ελαφρύ το περίγραμμά της</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2901"/>
        <source>{0} left empty, nothing matches the selection: {1}</source>
        <translation>{0}: αδειάστηκε(αν), τίποτα δεν ταιριάζει με την επιλογή: {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_mode_controller.py" line="2885"/>
        <source>failed</source>
        <translation>απέτυχε</translation>
    </message>
</context>
<context>
    <name>DatabaseManager</name>
    <message>
        <location filename="../adapters/database_manager.py" line="234"/>
        <source>Database file does not exist: {0}</source>
        <translation>Το αρχείο βάσης δεδομένων δεν υπάρχει: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="241"/>
        <source>Failed to connect to database {0}: {1}</source>
        <translation>Η σύνδεση στη βάση δεδομένων {0} απέτυχε: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="260"/>
        <source>Could not create database directory {0}: {1}</source>
        <translation>Δεν ήταν δυνατή η δημιουργία του καταλόγου βάσης δεδομένων {0}: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="314"/>
        <source>Failed to create database file {0}: {1}</source>
        <translation>Η δημιουργία αρχείου βάσης δεδομένων {0} απέτυχε: {1}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="591"/>
        <source>Cannot initialize FilterMate database: connection failed</source>
        <translation>Δεν είναι δυνατή η αρχικοποίηση της βάσης δεδομένων FilterMate: η σύνδεση απέτυχε</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="596"/>
        <source>Critical error connecting to database: {0}</source>
        <translation>Κρίσιμο σφάλμα σύνδεσης στη βάση δεδομένων: {0}</translation>
    </message>
    <message>
        <location filename="../adapters/database_manager.py" line="651"/>
        <source>Error during database initialization: {0}</source>
        <translation>Σφάλμα κατά την αρχικοποίηση βάσης δεδομένων: {0}</translation>
    </message>
</context>
<context>
    <name>DatasourceManager</name>
    <message>
        <location filename="../core/services/datasource_manager.py" line="140"/>
        <source>Database file does not exist: {db_file_path}</source>
        <translation>Το αρχείο της βάσης δεδομένων δεν υπάρχει: {db_file_path}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="151"/>
        <source>Failed to connect to database {db_file_path}: {error}</source>
        <translation>Αποτυχία σύνδεσης στη βάση δεδομένων {db_file_path}: {error}</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="176"/>
        <source>QGIS processing module not available to create spatial index</source>
        <translation>Το άρθρωμα QGIS Processing δεν είναι διαθέσιμο για τη δημιουργία χωρικού ευρετηρίου</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="182"/>
        <source>Cannot create spatial index: layer invalid or source not found.</source>
        <translation>Αδύνατη η δημιουργία χωρικού ευρετηρίου: μη έγκυρο επίπεδο ή η πηγή δεν βρέθηκε.</translation>
    </message>
    <message>
        <location filename="../core/services/datasource_manager.py" line="405"/>
        <source>PostgreSQL layers detected but psycopg2 is not installed. Using local Spatialite backend. For better performance with large datasets, install psycopg2.</source>
        <translation>Εντοπίστηκαν επίπεδα PostgreSQL αλλά το psycopg2 δεν είναι εγκατεστημένο. Χρήση του τοπικού Spatialite. Για καλύτερη απόδοση με μεγάλα σύνολα δεδομένων, εγκαταστήστε το psycopg2.</translation>
    </message>
</context>
<context>
    <name>ExploringController</name>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2481"/>
        <source>{0} features selected, more than the {1} a web service can be sent: narrow the selection or use an attribute filter.</source>
        <translation>{0} επιλεγμένες οντότητες, περισσότερες από τις {1} που μπορούν να σταλούν σε διαδικτυακή υπηρεσία: περιορίστε την επιλογή ή χρησιμοποιήστε φίλτρο χαρακτηριστικών.</translation>
    </message>
</context>
<context>
    <name>ExportDialogManager</name>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="92"/>
        <source>Save your layer to a file</source>
        <translation>Αποθηκεύστε το επίπεδο σε αρχείο</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="108"/>
        <source>Select a folder where to export your layers</source>
        <translation>Επιλέξτε φάκελο για εξαγωγή των επιπέδων σας</translation>
    </message>
    <message>
        <location filename="../ui/managers/export_dialog_manager.py" line="159"/>
        <source>Save your exported data to a zip file</source>
        <translation>Αποθηκεύστε τα εξαγόμενα δεδομένα σε αρχείο zip</translation>
    </message>
</context>
<context>
    <name>ExportGroupRecapDialog</name>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="115"/>
        <source>{0} couche(s)</source>
        <translation>{0} επίπεδο(-α)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="117"/>
        <source> dans {0} groupe(s)</source>
        <translation> σε {0} ομάδα(-ες)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="119"/>
        <source> + {0} hors groupe</source>
        <translation> + {0} εκτός ομάδας</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="126"/>
        <source>Destination : {0}</source>
        <translation>Προορισμός : {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="146"/>
        <source>No group detected - all layers are at the root level</source>
        <translation>Δεν εντοπίστηκε ομάδα - όλα τα επίπεδα είναι στο ριζικό επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="154"/>
        <source>Annuler</source>
        <translation>Ακύρωση</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/export_group_recap_dialog.py" line="160"/>
        <source>Exporter</source>
        <translation>Εξαγωγέας</translation>
    </message>
</context>
<context>
    <name>ExtensionRegistry</name>
    <message>
        <location filename="../extensions/registry.py" line="398"/>
        <source>install the QGIS plugin {0}</source>
        <translation>εγκαταστήστε το πρόσθετο QGIS {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="402"/>
        <source>install {0}</source>
        <translation>εγκαταστήστε το {0}</translation>
    </message>
    <message>
        <location filename="../extensions/registry.py" line="403"/>
        <source>The {0} extension is off because {1} is missing: {2}, then restart QGIS.</source>
        <translation>Η επέκταση {0} είναι απενεργοποιημένη επειδή λείπει το {1}: {2} και επανεκκινήστε το QGIS.</translation>
    </message>
</context>
<context>
    <name>FavoritesController</name>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="228"/>
        <source>No Filter</source>
        <translation type="obsolete">Χωρίς φίλτρο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="270"/>
        <source>No active filter to save.</source>
        <translation>Κανένα ενεργό φίλτρο για αποθήκευση.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Add Favorite</source>
        <translation>Προσθήκη αγαπημένου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="274"/>
        <source>Favorite name:</source>
        <translation>Όνομα αγαπημένου:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="292"/>
        <source>Favorite &apos;{0}&apos; added successfully</source>
        <translation>Το αγαπημένο '{0}' προστέθηκε επιτυχώς</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="511"/>
        <source>Export Favorites</source>
        <translation>Εξαγωγή αγαπημένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="535"/>
        <source>Exported {0} favorites</source>
        <translation>Εξήχθησαν {0} αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="537"/>
        <source>Failed to export favorites</source>
        <translation>Η εξαγωγή αγαπημένων απέτυχε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Import Favorites</source>
        <translation>Εισαγωγή αγαπημένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="570"/>
        <source>Merge with existing favorites?

Yes = Add to existing
No = Replace all existing</source>
        <translation>Συγχώνευση με υπάρχοντα αγαπημένα;

Ναι = Προσθήκη στα υπάρχοντα
Όχι = Αντικατάσταση όλων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="608"/>
        <source>Imported {0} favorites</source>
        <translation>Εισήχθησαν {0} αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="610"/>
        <source>No favorites imported</source>
        <translation>Δεν εισήχθησαν αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="619"/>
        <source>Favorites manager not initialized. Please restart FilterMate.</source>
        <translation>Η διαχείριση αγαπημένων δεν αρχικοποιήθηκε. Παρακαλώ επανεκκινήστε το FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="664"/>
        <source>Favorites manager dialog not available</source>
        <translation>Το παράθυρο διαχείρισης αγαπημένων δεν είναι διαθέσιμο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1174"/>
        <source>Error: {0}</source>
        <translation>Σφάλμα: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="775"/>
        <source>Used {0} times</source>
        <translation type="obsolete">Χρησιμοποιήθηκε {0} φορές</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="786"/>
        <source>Add current filter to favorites</source>
        <translation type="obsolete">Προσθήκη τρέχοντος φίλτρου στα αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="790"/>
        <source>Add filter (no active filter)</source>
        <translation type="obsolete">Προσθήκη φίλτρου (κανένα ενεργό φίλτρο)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="795"/>
        <source>Manage favorites...</source>
        <translation type="obsolete">Διαχείριση αγαπημένων...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="798"/>
        <source>Export...</source>
        <translation type="obsolete">Εξαγωγή...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="801"/>
        <source>Import...</source>
        <translation type="obsolete">Εισαγωγή...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="822"/>
        <source>Global favorites</source>
        <translation type="obsolete">Καθολικά αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="826"/>
        <source>Copy to global...</source>
        <translation type="obsolete">Αντιγραφή σε καθολικά...</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="837"/>
        <source>── Available global favorites ──</source>
        <translation type="obsolete">── Διαθέσιμα καθολικά αγαπημένα ──</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="845"/>
        <source>(No global favorites)</source>
        <translation type="obsolete">(Χωρίς καθολικά αγαπημένα)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="849"/>
        <source>Maintenance</source>
        <translation type="obsolete">Συντήρηση</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="851"/>
        <source>Save to project (.qgz)</source>
        <translation type="obsolete">Αποθήκευση σε έργο (.qgz)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="854"/>
        <source>Restore from project</source>
        <translation type="obsolete">Επαναφορά από έργο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="859"/>
        <source>Clean up orphan projects</source>
        <translation type="obsolete">Καθαρισμός ορφανών έργων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="862"/>
        <source>Database statistics</source>
        <translation type="obsolete">Στατιστικά βάσης δεδομένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="909"/>
        <source>Invalid Name</source>
        <translation type="obsolete">Μη έγκυρο όνομα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="769"/>
        <source>Favorite name cannot be empty.</source>
        <translation>Το όνομα αγαπημένου δεν μπορεί να είναι κενό.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>Duplicate Name</source>
        <translation>Διπλό όνομα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="779"/>
        <source>A favorite named &apos;{0}&apos; already exists.
Do you want to replace it?</source>
        <translation>Ένα αγαπημένο με το όνομα '{0}' υπάρχει ήδη.
Θέλετε να το αντικαταστήσετε;</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1050"/>
        <source>Favorite copied to global favorites</source>
        <translation>Το αγαπημένο αντιγράφηκε στα καθολικά αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1053"/>
        <source>Failed to copy to global favorites</source>
        <translation>Η αντιγραφή στα καθολικά αγαπημένα απέτυχε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>Global Favorites</source>
        <translation type="obsolete">Καθολικά αγαπημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1587"/>
        <source>{0} global favorite(s) available.

Global favorites are shared across all projects.</source>
        <translation type="obsolete">{0} καθολικό(-ά) αγαπημένο(-α) διαθέσιμο(-α).

Τα καθολικά αγαπημένα μοιράζονται σε όλα τα έργα.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1070"/>
        <source>Saved {0} favorite(s) to project file</source>
        <translation>Αποθηκεύτηκαν {0} αγαπημένο(-α) στο αρχείο έργου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1072"/>
        <source>Save failed</source>
        <translation>Η αποθήκευση απέτυχε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1083"/>
        <source>Restored {0} favorite(s) from project file</source>
        <translation>Επαναφέρθηκαν {0} αγαπημένο(-α) από το αρχείο έργου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1085"/>
        <source>No favorites to restore found in project</source>
        <translation>Δεν βρέθηκαν αγαπημένα για επαναφορά στο έργο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1116"/>
        <source>Cleaned up {0} orphan project(s)</source>
        <translation>Καθαρίστηκαν {0} ορφανό(-ά) έργο(-α)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1118"/>
        <source>No orphan projects to clean up</source>
        <translation>Δεν υπάρχουν ορφανά έργα για καθαρισμό</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1178"/>
        <source>FilterMate Database Statistics

Total favorites: {0}
   Project: {1}
   Orphans: {2}
   Global: {3}
</source>
        <translation>Στατιστικά βάσης δεδομένων FilterMate

Σύνολο αγαπημένων: {0}
   Έργο: {1}
   Ορφανά: {2}
   Καθολικά: {3}
</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1194"/>
        <source>Top projects by favorites:</source>
        <translation>Κορυφαία έργα κατά αγαπημένα:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1198"/>
        <source>FilterMate Statistics</source>
        <translation>Στατιστικά FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Διαχειριστής αγαπημένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="513"/>
        <source>No favorites saved yet.

Apply a filter to a layer, then click the ★ indicator and choose 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Δεν υπάρχουν αποθηκευμένα αγαπημένα ακόμη.

Εφαρμόστε ένα φίλτρο σε ένα επίπεδο, κάντε κλικ στον δείκτη ★ και επιλέξτε «Προσθήκη τρέχοντος φίλτρου στα αγαπημένα» για να αποθηκεύσετε το πρώτο σας αγαπημένο.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="808"/>
        <source>Import from Resource Sharing...</source>
        <translation type="obsolete">Εισαγωγή από Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="811"/>
        <source>Publish to Resource Sharing...</source>
        <translation type="obsolete">Δημοσίευση στο Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="816"/>
        <source>Publish (no favorites saved)</source>
        <translation type="obsolete">Δημοσίευση (χωρίς αποθηκευμένα αγαπημένα)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1100"/>
        <source>FilterMate config directory is not initialized yet — open a QGIS project with FilterMate first.</source>
        <translation>Ο κατάλογος παραμετροποίησης FilterMate δεν έχει αρχικοποιηθεί ακόμη — ανοίξτε πρώτα ένα έργο QGIS με FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1714"/>
        <source>Resource Sharing extension is not active. Enable &apos;favorites_sharing&apos; in FilterMate settings.</source>
        <translation type="obsolete">Η επέκταση Resource Sharing δεν είναι ενεργή. Ενεργοποιήστε το 'favorites_sharing' στις ρυθμίσεις του FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1722"/>
        <source>Shared favorites service is not available.</source>
        <translation type="obsolete">Η υπηρεσία κοινόχρηστων αγαπημένων δεν είναι διαθέσιμη.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1708"/>
        <source>Shared picker failed: {0}</source>
        <translation type="obsolete">Αποτυχία επιλογέα κοινόχρηστων αγαπημένων: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1726"/>
        <source>You have no favorites to publish yet. Save a filter via the ★ menu first.</source>
        <translation type="obsolete">Δεν έχετε αγαπημένα προς δημοσίευση ακόμη. Αποθηκεύστε πρώτα ένα φίλτρο μέσω του μενού ★.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1742"/>
        <source>Publish dialog failed: {0}</source>
        <translation type="obsolete">Αποτυχία ανοίγματος παραθύρου δημοσίευσης: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="388"/>
        <source>Favorites are not ready yet: {0}</source>
        <translation>Τα αγαπημένα δεν είναι ακόμη έτοιμα: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="393"/>
        <source>Could not remove &apos;{0}&apos;: {1}</source>
        <translation>Δεν ήταν δυνατή η αφαίρεση του '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="628"/>
        <source>No favorites saved yet — apply a filter then click the ★ indicator to save your first one.</source>
        <translation>Δεν υπάρχουν ακόμη αποθηκευμένα αγαπημένα — εφαρμόστε ένα φίλτρο και κάντε κλικ στον δείκτη ★ για να αποθηκεύσετε το πρώτο σας.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="667"/>
        <source>The favorites manager could not be opened. Details in filtermate.log.</source>
        <translation>Δεν ήταν δυνατό το άνοιγμα της διαχείρισης αγαπημένων. Λεπτομέρειες στο filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="792"/>
        <source>Could not replace &apos;{0}&apos;: {1}</source>
        <translation>Δεν ήταν δυνατή η αντικατάσταση του '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="903"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>Δεν ήταν δυνατή η αποθήκευση του '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1027"/>
        <source>Could not import global favorite: {0}</source>
        <translation>Δεν ήταν δυνατή η εισαγωγή του καθολικού αγαπημένου: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1045"/>
        <source>Could not copy to global: {0}</source>
        <translation>Δεν ήταν δυνατή η αντιγραφή στα καθολικά: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1065"/>
        <source>Could not save favorites to project file: {0}</source>
        <translation>Δεν ήταν δυνατή η αποθήκευση των αγαπημένων στο αρχείο του έργου: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1121"/>
        <source>Orphan projects could not be cleaned up. Details in filtermate.log.</source>
        <translation>Δεν ήταν δυνατός ο καθαρισμός των ορφανών έργων. Λεπτομέρειες στο filtermate.log.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/favorites_controller.py" line="1205"/>
        <source>Database statistics are unavailable. Details in filtermate.log.</source>
        <translation>Τα στατιστικά της βάσης δεδομένων δεν είναι διαθέσιμα. Λεπτομέρειες στο filtermate.log.</translation>
    </message>
</context>
<context>
    <name>FavoritesManagerDialog</name>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="204"/>
        <source>FilterMate - Favorites Manager</source>
        <translation>FilterMate - Διαχείριση αγαπημένων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1165"/>
        <source>&lt;b&gt;Saved Favorites ({0})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Αποθηκευμένα αγαπημένα ({0})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="266"/>
        <source>Search by name, expression, tags, or description...</source>
        <translation>Αναζήτηση κατά όνομα, έκφραση, ετικέτες ή περιγραφή...</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="553"/>
        <source>General</source>
        <translation>Γενικά</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Expression</source>
        <translation>Έκφραση</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1021"/>
        <source>Remote</source>
        <translation>Απομακρυσμένο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="575"/>
        <source>Favorite name</source>
        <translation>Όνομα αγαπημένου</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="576"/>
        <source>Name:</source>
        <translation>Όνομα:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="580"/>
        <source>Description (auto-generated, editable)</source>
        <translation>Περιγραφή (αυτόματη, επεξεργάσιμη)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="581"/>
        <source>Description:</source>
        <translation>Περιγραφή:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="584"/>
        <source>Enter tags separated by commas (e.g., urban, population, 2024)</source>
        <translation>Εισάγετε ετικέτες χωρισμένες με κόμμα (π.χ., αστικό, πληθυσμός, 2024)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="587"/>
        <source>Tags help organize and search favorites.
Separate multiple tags with commas.</source>
        <translation>Οι ετικέτες βοηθούν στην οργάνωση και αναζήτηση αγαπημένων.
Διαχωρίστε πολλαπλές ετικέτες με κόμμα.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="590"/>
        <source>Tags:</source>
        <translation>Ετικέτες:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="595"/>
        <source>Source Layer:</source>
        <translation>Επίπεδο πηγής:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="599"/>
        <source>Provider:</source>
        <translation>Πάροχος:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="607"/>
        <source>Used:</source>
        <translation>Χρήση:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="610"/>
        <source>Created:</source>
        <translation>Δημιουργήθηκε:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="677"/>
        <source>&lt;b&gt;Source Layer Expression:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Έκφραση επιπέδου πηγής:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="681"/>
        <source>Filter expression for source layer</source>
        <translation>Έκφραση φίλτρου για το επίπεδο πηγής</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="696"/>
        <source>&lt;b&gt;Filtered Remote Layers:&lt;/b&gt;</source>
        <translation>&lt;b&gt;Φιλτραρισμένα απομακρυσμένα επίπεδα:&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Layer</source>
        <translation>Επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="700"/>
        <source>Features</source>
        <translation>Οντότητες</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="708"/>
        <source>&lt;i&gt;No remote layers in this favorite&lt;/i&gt;</source>
        <translation>&lt;i&gt;Χωρίς απομακρυσμένα επίπεδα σε αυτό το αγαπημένο&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="721"/>
        <source>Apply</source>
        <translation>Εφαρμογή</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="724"/>
        <source>Apply this favorite filter to the project</source>
        <translation>Εφαρμογή αυτού του αγαπημένου φίλτρου στο έργο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="727"/>
        <source>Save Changes</source>
        <translation>Αποθήκευση αλλαγών</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="730"/>
        <source>Save modifications to this favorite</source>
        <translation>Αποθήκευση τροποποιήσεων σε αυτό το αγαπημένο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="733"/>
        <source>Delete</source>
        <translation>Διαγραφή</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="736"/>
        <source>Permanently delete this favorite</source>
        <translation>Οριστική διαγραφή αυτού του αγαπημένου</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="739"/>
        <source>Close</source>
        <translation>Κλείσιμο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="741"/>
        <source>Close this dialog</source>
        <translation>Κλείστε αυτό το παράθυρο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="849"/>
        <source>&lt;b&gt;Favorites ({0}/{1})&lt;/b&gt;</source>
        <translation>&lt;b&gt;Αγαπημένα ({0}/{1})&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1015"/>
        <source>Remote ({0})</source>
        <translation>Απομακρυσμένο ({0})</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete Favorite</source>
        <translation>Διαγραφή αγαπημένου</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1120"/>
        <source>Delete favorite &apos;{0}&apos;?</source>
        <translation>Διαγραφή αγαπημένου '{0}';</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1232"/>
        <source>Remote Layers</source>
        <translation>Απομακρυσμένα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1303"/>
        <source>&lt;b&gt;Saved Favorites (0)&lt;/b&gt;</source>
        <translation>&lt;b&gt;Αποθηκευμένα αγαπημένα (0)&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>Favorites Manager</source>
        <translation type="obsolete">Διαχείριση αγαπημένων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1262"/>
        <source>No favorites saved yet.

Click the ★ indicator and select 'Add current filter to favorites' to save your first favorite.</source>
        <translation type="obsolete">Δεν υπάρχουν αποθηκευμένα αγαπημένα.

Κάντε κλικ στον δείκτη ★ και επιλέξτε 'Προσθήκη τρέχοντος φίλτρου στα αγαπημένα' για να αποθηκεύσετε το πρώτο σας αγαπημένο.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="232"/>
        <source>Shared...</source>
        <translation>Κοινόχρηστα…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="234"/>
        <source>Browse favorites shared via QGIS Resource Sharing collections</source>
        <translation>Περιήγηση σε αγαπημένα που έχουν μοιραστεί μέσω συλλογών QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="244"/>
        <source>Publish...</source>
        <translation>Δημοσίευση…</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="246"/>
        <source>Publish selected favorites into a Resource Sharing collection</source>
        <translation>Δημοσίευση επιλεγμένων αγαπημένων σε μια συλλογή Resource Sharing</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not delete '{0}'. The favorite is still in the database — check the FilterMate log for details.</source>
        <translation type="obsolete">Αδύνατη η διαγραφή του «{0}». Το αγαπημένο βρίσκεται ακόμη στη βάση δεδομένων — ελέγξτε το αρχείο καταγραφής του FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="279"/>
        <source>Filter favorites by scope (owner × project).</source>
        <translation>Φιλτράρισμα αγαπημένων κατά εμβέλεια (κάτοχος × έργο).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="284"/>
        <source>All</source>
        <translation>Όλα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="285"/>
        <source>Shared · All projects</source>
        <translation>Κοινόχρηστα · Όλα τα έργα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="286"/>
        <source>Shared · This project</source>
        <translation>Κοινόχρηστα · Αυτό το έργο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="287"/>
        <source>Mine · All projects</source>
        <translation>Δικά μου · Όλα τα έργα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="288"/>
        <source>Mine · This project</source>
        <translation>Δικά μου · Αυτό το έργο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="625"/>
        <source>Mine</source>
        <translation>Δικά μου</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="626"/>
        <source>Shared</source>
        <translation>Κοινόχρηστα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="637"/>
        <source>This project</source>
        <translation>Αυτό το έργο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="638"/>
        <source>All projects</source>
        <translation>Όλα τα έργα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="645"/>
        <source>Project scope is set when the favorite is created. Move it via the filtering tab (coming soon) to switch projects.</source>
        <translation>Η εμβέλεια έργου ορίζεται κατά τη δημιουργία του αγαπημένου. Μετακινήστε το μέσω της καρτέλας φιλτραρίσματος (σύντομα διαθέσιμη) για αλλαγή έργου.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="666"/>
        <source>Visibility:</source>
        <translation>Ορατότητα:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="966"/>
        <source>— (shared with everyone)</source>
        <translation>— (κοινόχρηστο με όλους)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="968"/>
        <source>{0} (you)</source>
        <translation>{0} (εσείς)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="972"/>
        <source>{0} — selecting 'Mine' on save will transfer ownership to you</source>
        <translation>{0} — η επιλογή 'Δικά μου' κατά την αποθήκευση θα μεταφέρει την κυριότητα σε εσάς</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1080"/>
        <source>Could not save &apos;{0}&apos;: {1}</source>
        <translation>Δεν ήταν δυνατή η αποθήκευση του '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1139"/>
        <source>Could not delete &apos;{0}&apos;: {1}</source>
        <translation>Δεν ήταν δυνατή η διαγραφή του '{0}': {1}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/favorites_manager.py" line="1150"/>
        <source>'{0}' was not in the database — refresh and try again.</source>
        <translation>Το '{0}' δεν υπήρχε στη βάση δεδομένων — ανανεώστε και δοκιμάστε ξανά.</translation>
    </message>
</context>
<context>
    <name>FeedbackModule</name>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="112"/>
        <source>Exporting {0} layer(s)</source>
        <translation>Εξαγωγή επιπέδων: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="168"/>
        <source>Large dataset ({0} features) using {1}. Consider using PostgreSQL for optimal performance.</source>
        <translation>Μεγάλο σύνολο δεδομένων ({0} οντότητες) με χρήση {1}. Εξετάστε το ενδεχόμενο χρήσης PostgreSQL για βέλτιστη απόδοση.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="176"/>
        <source>Medium-large dataset ({0} features) using {1}. PostgreSQL recommended for better performance.</source>
        <translation>Μεσαίο-μεγάλο σύνολο δεδομένων ({0} οντότητες) με χρήση {1}. Συνιστάται PostgreSQL για καλύτερη απόδοση.</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="113"/>
        <source>Processing {0} layer(s)</source>
        <translation>Επεξεργασία επιπέδων: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="110"/>
        <source>Removing filters from {0} layer(s)</source>
        <translation>Αφαίρεση φίλτρων από επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="111"/>
        <source>Resetting {0} layer(s)</source>
        <translation>Επαναφορά επιπέδων: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="109"/>
        <source>Starting filter on {0} layer(s)</source>
        <translation>Έναρξη φιλτραρίσματος επιπέδων: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="137"/>
        <source>Successfully exported {0} layer(s)</source>
        <translation>Εξήχθησαν επιτυχώς επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="134"/>
        <source>Successfully filtered {0} layer(s)</source>
        <translation>Φιλτραρίστηκαν επιτυχώς επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="138"/>
        <source>Successfully processed {0} layer(s)</source>
        <translation>Επεξεργάστηκαν επιτυχώς επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="135"/>
        <source>Successfully removed filters from {0} layer(s)</source>
        <translation>Τα φίλτρα αφαιρέθηκαν επιτυχώς από επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../infrastructure/feedback/__init__.py" line="136"/>
        <source>Successfully reset {0} layer(s)</source>
        <translation>Επαναφέρθηκαν επιτυχώς επίπεδα: {0}</translation>
    </message>
</context>
<context>
    <name>FilepathType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="604"/>
        <source>View</source>
        <translation>Προβολή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="606"/>
        <source>Change</source>
        <translation>Αλλαγή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="617"/>
        <source>Select a folder</source>
        <translation>Επιλέξτε έναν φάκελο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="624"/>
        <source>Select a file</source>
        <translation>Επιλέξτε ένα αρχείο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="632"/>
        <source>Save to a file</source>
        <translation>Αποθήκευση σε αρχείο</translation>
    </message>
</context>
<context>
    <name>FilepathTypeImages</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="664"/>
        <source>View</source>
        <translation>Προβολή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="666"/>
        <source>Change</source>
        <translation>Αλλαγή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="675"/>
        <source>Select an icon</source>
        <translation>Επιλέξτε ένα εικονίδιο</translation>
    </message>
</context>
<context>
    <name>FilterApplicationService</name>
    <message>
        <location filename="../core/services/filter_application_service.py" line="102"/>
        <source>Layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Το επίπεδο δεν είναι έγκυρο ή η πηγή του δεν βρέθηκε. Η λειτουργία ακυρώθηκε.</translation>
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
        <translation>Άνοιγμα πίνακα FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset configuration and database</source>
        <translation>Επαναφορά διαμόρφωσης και βάσης δεδομένων</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="372"/>
        <source>Reset the default configuration and delete the SQLite database</source>
        <translation>Επαναφορά της προεπιλεγμένης διαμόρφωσης και διαγραφή της βάσης δεδομένων SQLite</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Reset Configuration</source>
        <translation>Επαναφορά διαμόρφωσης</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1589"/>
        <source>Configuration reset successfully.</source>
        <translation>Η διαμόρφωση επαναφέρθηκε επιτυχώς.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1594"/>
        <source>Default configuration file not found.</source>
        <translation>Δεν βρέθηκε το προεπιλεγμένο αρχείο διαμόρφωσης.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1617"/>
        <source>Database deleted: {filename}</source>
        <translation>Η βάση δεδομένων διαγράφηκε: {filename}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>Restart required</source>
        <translation>Απαιτείται επανεκκίνηση</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="479"/>
        <source>Obsolete configuration detected</source>
        <translation>Εντοπίστηκε παρωχημένη διαμόρφωση</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="480"/>
        <source>unknown version</source>
        <translation>άγνωστη έκδοση</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="481"/>
        <source>An obsolete configuration ({}) has been detected.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created)
• No: Keep current configuration (may cause issues)</source>
        <translation>Εντοπίστηκε παρωχημένη διαμόρφωση ({}).

Θέλετε να επαναφέρετε τις προεπιλεγμένες ρυθμίσεις;

• Ναι: Επαναφορά (θα δημιουργηθεί αντίγραφο ασφαλείας)
• Όχι: Διατήρηση τρέχουσας διαμόρφωσης (μπορεί να προκαλέσει προβλήματα)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="488"/>
        <source>Corrupted configuration detected</source>
        <translation>Εντοπίστηκε κατεστραμμένη διαμόρφωση</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="489"/>
        <source>The configuration file is corrupted and cannot be read.

Do you want to reset to default settings?

• Yes: Reset (a backup will be created if possible)
• No: Cancel (the plugin may not work correctly)</source>
        <translation>Το αρχείο διαμόρφωσης είναι κατεστραμμένο και δεν μπορεί να αναγνωστεί.

Θέλετε να επαναφέρετε τις προεπιλεγμένες ρυθμίσεις;

• Ναι: Επαναφορά (θα δημιουργηθεί αντίγραφο ασφαλείας αν είναι δυνατόν)
• Όχι: Ακύρωση (το πρόσθετο μπορεί να μην λειτουργεί σωστά)</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="496"/>
        <source>Configuration reset</source>
        <translation>Επαναφορά διαμόρφωσης</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="497"/>
        <source>The configuration needs to be reset.

Do you want to continue?</source>
        <translation>Η διαμόρφωση πρέπει να επαναφερθεί.

Θέλετε να συνεχίσετε;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="545"/>
        <source>Configuration not reset. Some features may not work correctly.</source>
        <translation>Η διαμόρφωση δεν επαναφέρθηκε. Ορισμένες λειτουργίες μπορεί να μην λειτουργούν σωστά.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="556"/>
        <source>Configuration created with default values</source>
        <translation>Η διαμόρφωση δημιουργήθηκε με προεπιλεγμένες τιμές</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="559"/>
        <source>Corrupted configuration reset. Default settings have been restored.</source>
        <translation>Η κατεστραμμένη διαμόρφωση επαναφέρθηκε. Οι προεπιλεγμένες ρυθμίσεις αποκαταστάθηκαν.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="562"/>
        <source>Obsolete configuration reset. Default settings have been restored.</source>
        <translation>Η παρωχημένη διαμόρφωση επαναφέρθηκε. Οι προεπιλεγμένες ρυθμίσεις αποκαταστάθηκαν.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="583"/>
        <source>Configuration updated to latest version</source>
        <translation>Η διαμόρφωση ενημερώθηκε στην τελευταία έκδοση</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="580"/>
        <source>Configuration updated: new settings available ({sections}). Access via Options menu.</source>
        <translation>Η διαμόρφωση ενημερώθηκε: νέες ρυθμίσεις διαθέσιμες ({sections}). Πρόσβαση μέσω του μενού Επιλογές.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="574"/>
        <source>Geometry Simplification</source>
        <translation>Απλοποίηση γεωμετρίας</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="575"/>
        <source>Optimization Thresholds</source>
        <translation>Όρια βελτιστοποίησης</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="602"/>
        <source>Error during configuration migration: {}</source>
        <translation>Σφάλμα κατά τη μετεγκατάσταση διαμόρφωσης: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="735"/>
        <source>Geometry validation setting</source>
        <translation>Ρύθμιση επικύρωσης γεωμετρίας</translation>
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
        <translation>Η ρύθμιση QGIS 'Φιλτράρισμα μη έγκυρων οντοτήτων' είναι ρυθμισμένη στο '{mode}'.

Το FilterMate συνιστά την απενεργοποίηση αυτής της ρύθμισης (τιμή 'Off') για τους εξής λόγους:

• Οντότητες με μη έγκυρες γεωμετρίες μπορεί να εξαιρεθούν σιωπηλά από εξαγωγές και φίλτρα
• Το FilterMate διαχειρίζεται την επικύρωση γεωμετρίας εσωτερικά με αυτόματες επιλογές επιδιόρθωσης
• Ορισμένα νόμιμα δεδομένα μπορεί να έχουν γεωμετρίες που θεωρούνται 'μη έγκυρες' σύμφωνα με αυστηρούς κανόνες OGC

Θέλετε να απενεργοποιήσετε αυτή τη ρύθμιση τώρα;

• Ναι: Απενεργοποίηση φιλτραρίσματος (συνιστάται για FilterMate)
• Όχι: Διατήρηση τρέχουσας ρύθμισης</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="765"/>
        <source>Invalid geometry filtering disabled successfully.</source>
        <translation>Το φιλτράρισμα μη έγκυρης γεωμετρίας απενεργοποιήθηκε επιτυχώς.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="772"/>
        <source>Invalid geometry filtering not modified. Some features may be excluded from exports.</source>
        <translation>Το φιλτράρισμα μη έγκυρης γεωμετρίας δεν τροποποιήθηκε. Ορισμένες οντότητες μπορεί να εξαιρεθούν από τις εξαγωγές.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1563"/>
        <source>Are you sure you want to reset to the default configuration?

This will:
- Restore default settings
- Delete the layer database

QGIS must be restarted to apply the changes.</source>
        <translation>Είστε σίγουροι ότι θέλετε να επαναφέρετε την προεπιλεγμένη διαμόρφωση;

Αυτό θα:
- Επαναφέρει τις προεπιλεγμένες ρυθμίσεις
- Διαγράψει τη βάση δεδομένων επιπέδων

Το QGIS πρέπει να επανεκκινηθεί για να εφαρμοστούν οι αλλαγές.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1641"/>
        <source>The configuration has been reset.

Please restart QGIS to apply the changes.</source>
        <translation>Η διαμόρφωση επαναφέρθηκε.

Παρακαλώ επανεκκινήστε το QGIS για να εφαρμοστούν οι αλλαγές.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="411"/>
        <source>Initialization error: {0}</source>
        <translation>Σφάλμα αρχικοποίησης: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="667"/>
        <source>{count} referenced layer(s) not loaded ({layers_list}). Using fallback display.</source>
        <translation>{count} αναφερόμενο(-α) επίπεδο(-α) δεν φορτώθηκαν ({layers_list}). Χρήση εναλλακτικής εμφάνισης.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1632"/>
        <source>Unable to delete {filename}: {e}</source>
        <translation>Αδυναμία διαγραφής {filename}: {e}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1405"/>
        <source>Error during reset: {str(e)}</source>
        <translation type="obsolete">Σφάλμα κατά την επαναφορά: {str(e)}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1684"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;Thank you for using &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Join our Discord community to:&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;Get help and support&lt;/li&gt;&lt;li&gt;Report bugs and issues&lt;/li&gt;&lt;li&gt;Suggest new features&lt;/li&gt;&lt;li&gt;Share tips with other users&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;Ευχαριστούμε που χρησιμοποιείτε το &lt;b&gt;FilterMate&lt;/b&gt;!&lt;br&gt;Γίνετε μέλος της κοινότητας Discord για να:&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;Λάβετε βοήθεια και υποστήριξη&lt;/li&gt;&lt;li&gt;Αναφέρετε σφάλματα και προβλήματα&lt;/li&gt;&lt;li&gt;Προτείνετε νέες λειτουργίες&lt;/li&gt;&lt;li&gt;Μοιραστείτε συμβουλές με άλλους χρήστες&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1700"/>
        <source>  Join us on Discord</source>
        <translation>  Ελάτε στο Discord</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1720"/>
        <source>Don&apos;t show this again</source>
        <translation>Να μην εμφανιστεί ξανά</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1776"/>
        <source>Close</source>
        <translation>Κλείσιμο</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1843"/>
        <source>Error loading plugin: {0}. Check QGIS Python console for details.</source>
        <translation>Σφάλμα φόρτωσης πρόσθετου: {0}. Ελέγξτε την κονσόλα Python του QGIS για λεπτομέρειες.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7416"/>
        <source>Current layer: {0}</source>
        <translation>Τρέχον επίπεδο: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7418"/>
        <source>No layer selected</source>
        <translation>Δεν επιλέχθηκε επίπεδο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>Selected layers:
{0}</source>
        <translation>Επιλεγμένα επίπεδα:
{0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7428"/>
        <source>No layers selected</source>
        <translation>Δεν επιλέχθηκαν επίπεδα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7448"/>
        <source>No expression defined</source>
        <translation>Δεν έχει οριστεί έκφραση</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7460"/>
        <source>Display expression: {0}</source>
        <translation>Έκφραση εμφάνισης: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7477"/>
        <source>Feature ID: {0}
First attribute: {1}</source>
        <translation>Αναγνωριστικό οντότητας: {0}
Πρώτο χαρακτηριστικό: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1650"/>
        <source>The configuration could not be reset. Check that the plugin folder is writable, then try again. Details in filtermate.log.</source>
        <translation>Δεν ήταν δυνατή η επαναφορά της διαμόρφωσης. Ελέγξτε ότι ο φάκελος του πρόσθετου είναι εγγράψιμος και δοκιμάστε ξανά. Λεπτομέρειες στο filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1750"/>
        <source>What&apos;s new in FilterMate 5</source>
        <translation>Τι νέο υπάρχει στο FilterMate 5</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1756"/>
        <source>&lt;p style=&apos;font-size:13px;&apos;&gt;&lt;b&gt;FilterMate now works with raster and point cloud layers.&lt;/b&gt;&lt;/p&gt;&lt;ul style=&apos;margin-left:10px; font-size:12px;&apos;&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; adapts to the current layer: value range and classes of a raster, classes, elevation and attributes of a LiDAR point cloud.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; relates that selection to layers of any kind, with the usual predicates and buffer: parcels within an elevation range, LiDAR points under buildings, a DTM clipped to a municipality.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; writes filtered rasters (GeoTIFF, COG) and point clouds (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Processing algorithms and models, qgis_process, Python and REST APIs.&lt;/li&gt;&lt;/ul&gt;</source>
        <translation>&lt;p style='font-size:13px;'&gt;&lt;b&gt;Το FilterMate λειτουργεί πλέον με επίπεδα ράστερ και νέφους σημείων.&lt;/b&gt;&lt;/p&gt;&lt;ul style='margin-left:10px; font-size:12px;'&gt;&lt;li&gt;&lt;b&gt;EXPLORING&lt;/b&gt; προσαρμόζεται στο τρέχον επίπεδο: εύρος τιμών και κλάσεις ενός ράστερ, κλάσεις, υψόμετρο και ιδιότητες ενός νέφους σημείων LiDAR.&lt;/li&gt;&lt;li&gt;&lt;b&gt;FILTERING&lt;/b&gt; συσχετίζει αυτή την επιλογή με επίπεδα κάθε τύπου, με τα συνήθη κατηγορήματα και τη ζώνη επιρροής: αγροτεμάχια εντός εύρους υψομέτρου, σημεία LiDAR κάτω από κτίρια, ένα ΨΜΕ αποκομμένο στα όρια ενός δήμου.&lt;/li&gt;&lt;li&gt;&lt;b&gt;EXPORTING&lt;/b&gt; γράφει τα φιλτραρισμένα ράστερ (GeoTIFF, COG) και νέφη σημείων (LAZ, COPC).&lt;/li&gt;&lt;li&gt;Αλγόριθμοι και μοντέλα Processing, qgis_process, API Python και REST.&lt;/li&gt;&lt;/ul&gt;</translation>
    </message>
    <message>
        <location filename="../filter_mate.py" line="1772"/>
        <source>Open the user guide</source>
        <translation>Άνοιγμα του οδηγού χρήσης</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="409"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation>Αυτή η έκφραση δεν μπορεί να αξιολογηθεί με ασφάλεια για μια υπηρεσία.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Δεν ήταν δυνατή η ανάγνωση της υπηρεσίας. Δοκιμάστε ξανά.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="496"/>
        <source>Read failed</source>
        <translation>Η ανάγνωση απέτυχε</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="287"/>
        <source>Loading filtered extent…</source>
        <translation>Φόρτωση φιλτραρισμένης έκτασης…</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="404"/>
        <source>The expression is not valid for this layer. Check its syntax and field names.</source>
        <translation>Η έκφραση δεν είναι έγκυρη για αυτό το επίπεδο. Ελέγξτε τη σύνταξη και τα ονόματα των πεδίων.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/async_query.py" line="407"/>
        <source>A virtual field of this layer cannot be evaluated safely for a service.</source>
        <translation>Ένα εικονικό πεδίο αυτού του επιπέδου δεν μπορεί να αξιολογηθεί με ασφάλεια για μια υπηρεσία.</translation>
    </message>
</context>
<context>
    <name>FilterMateApp</name>
    <message>
        <location filename="../filter_mate_app.py" line="319"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed.</source>
        <translation>Εντοπίστηκαν επίπεδα PostgreSQL ({0}) αλλά το psycopg2 δεν είναι εγκατεστημένο.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="419"/>
        <source>Cleared {0} caches</source>
        <translation>Διαγράφηκαν {0} μνήμες cache</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="925"/>
        <source>Failed to create dockwidget: {0}</source>
        <translation>Η δημιουργία dockwidget απέτυχε: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="935"/>
        <source>Failed to display dockwidget: {0}</source>
        <translation>Η εμφάνιση dockwidget απέτυχε: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1501"/>
        <source>Error executing {0}: {1}</source>
        <translation>Σφάλμα εκτέλεσης {0}: {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1513"/>
        <source>Plugin running in degraded mode (hexagonal services unavailable). Performance may be reduced.</source>
        <translation>Το πρόσθετο εκτελείται σε υποβαθμισμένη λειτουργία (εξαγωνικές υπηρεσίες μη διαθέσιμες). Η απόδοση μπορεί να μειωθεί.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>FilterMate ERROR</source>
        <translation>FilterMate ΣΦΑΛΜΑ</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1857"/>
        <source>Cannot execute {0}: widget initialization failed.</source>
        <translation>Δεν είναι δυνατή η εκτέλεση {0}: η αρχικοποίηση widget απέτυχε.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2638"/>
        <source>Cannot {0}: layer invalid or source not found.</source>
        <translation>Δεν είναι δυνατό {0}: μη έγκυρο επίπεδο ή η πηγή δεν βρέθηκε.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2792"/>
        <source>All filters cleared - </source>
        <translation>Όλα τα φίλτρα διαγράφηκαν - </translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2793"/>
        <source>{0}{1} features visible in main layer</source>
        <translation>{0}{1} ορατές οντότητες στο κύριο επίπεδο</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2805"/>
        <source>Error: result handler missing</source>
        <translation>Σφάλμα: λείπει ο handler αποτελέσματος</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2822"/>
        <source>Error during filtering: {0}</source>
        <translation>Σφάλμα κατά το φιλτράρισμα: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2946"/>
        <source>Recovered {0} orphan favorite(s): {1}</source>
        <translation>Ανακτήθηκαν {0} ορφανό(-ά) αγαπημένο(-α): {1}</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3112"/>
        <source>Layer loading failed - click to retry</source>
        <translation>Η φόρτωση επιπέδου απέτυχε - κλικ για επανάληψη</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="3164"/>
        <source>{0} layer(s) loaded successfully</source>
        <translation>{0} επίπεδο(-α) φορτώθηκαν επιτυχώς</translation>
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
        <translation>Επιλέξτε ένα επίπεδο στην καρτέλα EXPLORING πριν εκτελέσετε το '{0}'.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="852"/>
        <source>{0} layer(s) stay filtered: {1}. Turn the option back on to unfilter them.</source>
        <translation>{0} επίπεδο(α) παραμένουν φιλτραρισμένα: {1}. Ενεργοποιήστε ξανά την επιλογή για να αφαιρέσετε το φίλτρο.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="2624"/>
        <source>A server filter is being prepared. Wait for it to finish before starting another operation.</source>
        <translation>Ετοιμάζεται ένα φίλτρο διακομιστή. Περιμένετε να ολοκληρωθεί πριν ξεκινήσετε άλλη λειτουργία.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="1773"/>
        <source>A FilterMate API operation is running. Wait for it to finish.</source>
        <translation>Εκτελείται μια λειτουργία του API του FilterMate. Περιμένετε να ολοκληρωθεί.</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="458"/>
        <source>Adding layers</source>
        <translation>Προσθήκη επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="462"/>
        <source>Existing project loaded</source>
        <translation>Φορτώθηκε υπάρχον έργο</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="455"/>
        <source>Exporting data</source>
        <translation>Εξαγωγή δεδομένων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="452"/>
        <source>Filtering data</source>
        <translation>Φιλτράρισμα δεδομένων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="461"/>
        <source>New project</source>
        <translation>Νέο έργο</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="457"/>
        <source>Redo filter</source>
        <translation>Επανάληψη φίλτρου</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="463"/>
        <source>Reloading layers</source>
        <translation>Επαναφόρτωση επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="460"/>
        <source>Removing all layers</source>
        <translation>Αφαίρεση όλων των επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="459"/>
        <source>Removing layers</source>
        <translation>Αφαίρεση επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="454"/>
        <source>Reseting data</source>
        <translation>Επαναφορά δεδομένων</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="456"/>
        <source>Undo filter</source>
        <translation>Αναίρεση φίλτρου</translation>
    </message>
    <message>
        <location filename="../filter_mate_app.py" line="453"/>
        <source>Unfiltering data</source>
        <translation>Αφαίρεση φίλτρου από δεδομένα</translation>
    </message>
</context>
<context>
    <name>FilterMateDockWidget</name>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="621"/>
        <source>Initialization error: {}</source>
        <translation>Σφάλμα αρχικοποίησης: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1028"/>
        <source>UI configuration incomplete - check logs</source>
        <translation>Ελλιπής διαμόρφωση UI - ελέγξτε τα αρχεία καταγραφής</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="929"/>
        <source>UI dimension error: {}</source>
        <translation type="obsolete">Σφάλμα διαστάσεων UI: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1488"/>
        <source>Favorites manager not available</source>
        <translation>Η διαχείριση αγαπημένων δεν είναι διαθέσιμη</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1509"/>
        <source>★ {0} Favorites saved
Click to apply or manage</source>
        <translation>★ {0} Αγαπημένα αποθηκευμένα
Κλικ για εφαρμογή ή διαχείριση</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1512"/>
        <source>★ No favorites saved
Click to add current filter</source>
        <translation>★ Χωρίς αποθηκευμένα αγαπημένα
Κλικ για προσθήκη τρέχοντος φίλτρου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1532"/>
        <location filename="../ui/controllers/backend_controller.py" line="822"/>
        <source>Forced {0} backend for {1} layer(s)</source>
        <translation>Επιβλήθηκε backend {0} για {1} επίπεδο(-α)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1638"/>
        <source>Backend controller not available</source>
        <translation>Ο ελεγκτής backend δεν είναι διαθέσιμος</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1556"/>
        <source>PostgreSQL auto-cleanup enabled</source>
        <translation>Αυτόματος καθαρισμός PostgreSQL ενεργοποιημένος</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1557"/>
        <source>PostgreSQL auto-cleanup disabled</source>
        <translation>Αυτόματος καθαρισμός PostgreSQL απενεργοποιημένος</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>PostgreSQL session views cleaned up</source>
        <translation>Οι προβολές συνεδρίας PostgreSQL καθαρίστηκαν</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1563"/>
        <source>No views to clean or cleanup failed</source>
        <translation>Δεν υπάρχουν προβολές για καθαρισμό ή ο καθαρισμός απέτυχε</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1574"/>
        <location filename="../ui/controllers/backend_controller.py" line="1089"/>
        <source>No PostgreSQL connection available</source>
        <translation>Δεν υπάρχει διαθέσιμη σύνδεση PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1600"/>
        <source>Schema has {0} view(s) from other sessions.
Drop anyway?</source>
        <translation>Το σχήμα έχει {0} προβολή(-ές) από άλλες συνεδρίες.
Διαγραφή ούτως ή άλλως;</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1601"/>
        <source>Other Sessions Active</source>
        <translation>Άλλες ενεργές συνεδρίες</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1603"/>
        <source>Schema cleanup cancelled</source>
        <translation>Ο καθαρισμός σχήματος ακυρώθηκε</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1608"/>
        <source>Schema &apos;{0}&apos; dropped successfully</source>
        <translation>Το σχήμα '{0}' διαγράφηκε επιτυχώς</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1610"/>
        <location filename="../ui/controllers/backend_controller.py" line="1090"/>
        <source>Schema cleanup failed</source>
        <translation>Ο καθαρισμός σχήματος απέτυχε</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1636"/>
        <source>PostgreSQL Session Info</source>
        <translation>Πληροφορίες συνεδρίας PostgreSQL</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Theme adapted: {0}</source>
        <translation>Το θέμα προσαρμόστηκε: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Dark mode</source>
        <translation>Σκούρο θέμα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="2753"/>
        <source>Light mode</source>
        <translation>Φωτεινό θέμα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4116"/>
        <location filename="../ui/controllers/exploring_controller.py" line="884"/>
        <source>Selected features have no geometry.</source>
        <translation>Οι επιλεγμένες οντότητες δεν έχουν γεωμετρία.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4135"/>
        <location filename="../ui/controllers/exploring_controller.py" line="885"/>
        <source>No feature selected. Select a feature from the dropdown list.</source>
        <translation>Δεν επιλέχθηκε οντότητα. Επιλέξτε μια οντότητα από την αναπτυσσόμενη λίστα.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5319"/>
        <source>The selected layer is invalid or its source cannot be found.</source>
        <translation>Το επιλεγμένο επίπεδο δεν είναι έγκυρο ή η πηγή του δεν βρέθηκε.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6114"/>
        <source>Negative buffer (erosion): shrinks polygons inward</source>
        <translation>Αρνητικό buffer (διάβρωση): συρρικνώνει τα πολύγωνα προς τα μέσα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6117"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Τιμή buffer σε μέτρα (θετική=επέκταση, αρνητική=σμίκρυνση πολυγώνων)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6619"/>
        <source>Plugin activated with {0} vector layer(s)</source>
        <translation>Το πρόσθετο ενεργοποιήθηκε με {0} διανυσματικό(-ά) επίπεδο(-α)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6718"/>
        <source>Could not reload plugin automatically.</source>
        <translation>Δεν ήταν δυνατή η αυτόματη επαναφόρτωση του πρόσθετου.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6723"/>
        <source>Error reloading plugin: {0}</source>
        <translation>Σφάλμα επαναφόρτωσης πρόσθετου: {0}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6798"/>
        <source>Layer properties reset to defaults</source>
        <translation>Οι ιδιότητες επιπέδου επαναφέρθηκαν στις προεπιλογές</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6799"/>
        <source>Error resetting layer properties: {}</source>
        <translation>Σφάλμα επαναφοράς ιδιοτήτων επιπέδου: {}</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>Filter</source>
        <translation>Φίλτρο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="896"/>
        <source>Undo the last filter</source>
        <translation>Αναίρεση του τελευταίου φίλτρου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="897"/>
        <source>Redo the last filter</source>
        <translation>Επανάληψη του τελευταίου φίλτρου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="898"/>
        <source>Remove the filters</source>
        <translation>Αφαίρεση των φίλτρων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="899"/>
        <source>Export the layers</source>
        <translation>Εξαγωγή των επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="900"/>
        <source>About FilterMate</source>
        <translation>Σχετικά με το FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="901"/>
        <source>QFieldCloud</source>
        <translation>QFieldCloud</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="902"/>
        <source>Identify the selected features</source>
        <translation>Αναγνώριση των επιλεγμένων οντοτήτων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="903"/>
        <source>Zoom to the selected features</source>
        <translation>Εστίαση στις επιλεγμένες οντότητες</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="904"/>
        <source>Select the features on the map</source>
        <translation>Επιλογή των οντοτήτων στον χάρτη</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="905"/>
        <source>Follow the features on the map</source>
        <translation>Παρακολούθηση των οντοτήτων στον χάρτη</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="886"/>
        <source>Link the three selection modes</source>
        <translation type="obsolete">Σύνδεση των τριών τρόπων επιλογής</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="907"/>
        <source>Reset the layer properties</source>
        <translation>Επαναφορά των ιδιοτήτων του επιπέδου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="908"/>
        <source>Follow the current layer</source>
        <translation>Παρακολούθηση του τρέχοντος επιπέδου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="909"/>
        <source>Layers to filter</source>
        <translation>Επίπεδα προς φιλτράρισμα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="910"/>
        <source>Combine with the existing filter</source>
        <translation>Συνδυασμός με το υπάρχον φίλτρο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="911"/>
        <source>Geometric predicates</source>
        <translation>Γεωμετρικά κατηγορήματα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="912"/>
        <source>Buffer distance</source>
        <translation>Απόσταση ζώνης (buffer)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="913"/>
        <source>Buffer type</source>
        <translation>Τύπος ζώνης (buffer)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="914"/>
        <source>Layers to export</source>
        <translation>Επίπεδα προς εξαγωγή</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="915"/>
        <source>Projection of the export</source>
        <translation>Προβολή της εξαγωγής</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="916"/>
        <source>Export the styles</source>
        <translation>Εξαγωγή των στυλ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="917"/>
        <source>Export format</source>
        <translation>Μορφή εξαγωγής</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="918"/>
        <source>Output folder</source>
        <translation>Φάκελος εξόδου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="919"/>
        <source>Zip the export</source>
        <translation>Συμπίεση της εξαγωγής σε zip</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1033"/>
        <source>The panel layout could not be applied; default sizes are used. Details in filtermate.log.</source>
        <translation>Η διάταξη του πίνακα δεν μπόρεσε να εφαρμοστεί· χρησιμοποιούνται τα προεπιλεγμένα μεγέθη. Λεπτομέρειες στο filtermate.log.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="6890"/>
        <location filename="../ui/controllers/backend_controller.py" line="682"/>
        <source>Vector</source>
        <translation>Διανυσματικό</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="906"/>
        <source>Link the single and multiple selections</source>
        <translation>Σύνδεση της μονής και της πολλαπλής επιλογής</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1586"/>
        <source>Schema &apos;{0}&apos; and the following {1} temporary object(s) will be dropped:</source>
        <translation>Το σχήμα «{0}» και τα ακόλουθα {1} προσωρινά αντικείμενα θα διαγραφούν:</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1589"/>
        <source>... and {0} more</source>
        <translation>… και {0} ακόμη</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1591"/>
        <source>Schema &apos;{0}&apos; is empty and will be dropped.</source>
        <translation>Το σχήμα «{0}» είναι κενό και θα διαγραφεί.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="1592"/>
        <source>Drop FilterMate schema</source>
        <translation>Διαγραφή σχήματος FilterMate</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>Read failed</source>
        <translation>Η ανάγνωση απέτυχε</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4247"/>
        <source>The service could not be read. Please retry.</source>
        <translation>Δεν ήταν δυνατή η ανάγνωση της υπηρεσίας. Δοκιμάστε ξανά.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="4589"/>
        <source>Loading filtered extent…</source>
        <translation>Φόρτωση φιλτραρισμένης έκτασης…</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5184"/>
        <location filename="../ui/controllers/exploring_controller.py" line="742"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3658"/>
        <source>Loading selected values…</source>
        <translation>Φόρτωση επιλεγμένων τιμών…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="603"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Αυτή η έκφραση δεν μπορεί να αξιολογηθεί με ασφάλεια για μια υπηρεσία.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2715"/>
        <source>Error evaluating expression: {0}</source>
        <translation>Σφάλμα κατά την αξιολόγηση της έκφρασης: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="2716"/>
        <source>Expression Evaluation</source>
        <translation>Αξιολόγηση έκφρασης</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="444"/>
        <source>Loading values…</source>
        <translation>Φόρτωση τιμών…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="846"/>
        <source>Loading zoom extent…</source>
        <translation>Φόρτωση έκτασης εστίασης…</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>No feature with geometry matches the selection.</source>
        <translation>Καμία οντότητα με γεωμετρία δεν ταιριάζει με την επιλογή.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="434"/>
        <source>Only a limited set of values is shown. Refine the search to find other values.</source>
        <translation>Εμφανίζεται μόνο ένα περιορισμένο σύνολο τιμών. Περιορίστε την αναζήτηση για να βρείτε άλλες τιμές.</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="5119"/>
        <location filename="../ui/controllers/exploring_controller.py" line="551"/>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <location filename="../ui/controllers/exploring_controller.py" line="691"/>
        <location filename="../ui/controllers/exploring_controller.py" line="3651"/>
        <source>Selection</source>
        <translation>Επιλογή</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="550"/>
        <source>The service selection exceeds the key limit. Refine the selection.</source>
        <translation>Η επιλογή της υπηρεσίας υπερβαίνει το όριο κλειδιών. Περιορίστε την επιλογή.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="568"/>
        <location filename="../ui/controllers/exploring_controller.py" line="636"/>
        <source>This service has no stable key for the selection.</source>
        <translation>Αυτή η υπηρεσία δεν έχει σταθερό κλειδί για την επιλογή.</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="436"/>
        <location filename="../ui/controllers/exploring_controller.py" line="438"/>
        <source>Values</source>
        <translation>Τιμές</translation>
    </message>
    <message>
        <location filename="../ui/controllers/exploring_controller.py" line="808"/>
        <location filename="../ui/controllers/exploring_controller.py" line="835"/>
        <source>Zoom</source>
        <translation>Εστίαση</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1087"/>
        <source>&apos;{0}&apos; is not a FilterMate temporary schema: it is not dropped</source>
        <translation>Το «{0}» δεν είναι προσωρινό σχήμα του FilterMate: δεν διαγράφεται</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1312"/>
        <source>... and {0} more (see details)</source>
        <translation>… και {0} ακόμη (δείτε λεπτομέρειες)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="778"/>
        <source>Auto (Default)</source>
        <translation>Αυτόματο (προεπιλογή)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="786"/>
        <source>Auto-select Optimal for All Layers</source>
        <translation>Αυτόματη βέλτιστη επιλογή για όλα τα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="817"/>
        <source>Auto-selected backends for {0} layer(s)</source>
        <translation>Αυτόματη επιλογή backend για επίπεδα: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="838"/>
        <source>Backend forced to {0} for &apos;{1}&apos;</source>
        <translation>Το backend επιβλήθηκε σε {0} για το «{1}»</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="841"/>
        <source>Backend set to Auto for &apos;{0}&apos;</source>
        <translation>Το backend για το «{0}» ορίστηκε σε Αυτόματο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1336"/>
        <source>Cleanup cancelled</source>
        <translation>Ο καθαρισμός ακυρώθηκε</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="807"/>
        <source>Clear ALL FilterMate temporary tables from all databases</source>
        <translation>Εκκαθάριση ΟΛΩΝ των προσωρινών πινάκων του FilterMate από όλες τις βάσεις δεδομένων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="797"/>
        <source>Clear Temp Tables</source>
        <translation>Εκκαθάριση προσωρ. πινάκων</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1317"/>
        <source>Clear all FilterMate temporary tables</source>
        <translation>Εκκαθάριση όλων των προσωρινών πινάκων του FilterMate</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="802"/>
        <source>Clear temporary tables for the current project only</source>
        <translation>Εκκαθάριση προσωρινών πινάκων μόνο του τρέχοντος έργου</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="828"/>
        <source>Cleared {0} temporary table(s) for current project</source>
        <translation>Εκκαθαρίστηκαν προσωρινοί πίνακες του τρέχοντος έργου: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1340"/>
        <source>Cleared {0} temporary table(s) globally</source>
        <translation>Εκκαθαρίστηκαν προσωρινοί πίνακες καθολικά: {0}</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1307"/>
        <source>FilterMate will permanently delete {0} temporary table(s) / view(s) from the databases of the project and of the PostgreSQL connection:</source>
        <translation>Το FilterMate θα διαγράψει οριστικά {0} προσωρινούς πίνακες / προβολές από τις βάσεις δεδομένων του έργου και της σύνδεσης PostgreSQL:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="791"/>
        <source>Force {0} for All Layers</source>
        <translation>Επιβολή {0} για όλα τα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="742"/>
        <source>No alternative backends available for this layer</source>
        <translation>Δεν υπάρχουν εναλλακτικά backend για αυτό το επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1333"/>
        <location filename="../ui/controllers/backend_controller.py" line="1342"/>
        <source>No temporary tables found</source>
        <translation>Δεν βρέθηκαν προσωρινοί πίνακες</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="830"/>
        <source>No temporary tables found for current project</source>
        <translation>Δεν βρέθηκαν προσωρινοί πίνακες για το τρέχον έργο</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1080"/>
        <source>Schema &apos;{0}&apos; does not exist: nothing to drop</source>
        <translation>Το σχήμα «{0}» δεν υπάρχει: δεν υπάρχει τίποτα προς διαγραφή</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1083"/>
        <source>Schema &apos;{0}&apos; holds objects FilterMate did not create ({1}): it is not dropped</source>
        <translation>Το σχήμα «{0}» περιέχει αντικείμενα που δεν δημιουργήθηκαν από το FilterMate ({1}): δεν διαγράφεται</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="762"/>
        <source>Select Backend:</source>
        <translation>Επιλογή backend:</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="1313"/>
        <source>Your own tables and layers are not touched. Continue?</source>
        <translation>Οι δικοί σας πίνακες και τα επίπεδά σας δεν θίγονται. Συνέχεια;</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="805"/>
        <source>🌐 All Projects (Global)</source>
        <translation>🌐 Όλα τα έργα (καθολικά)</translation>
    </message>
    <message>
        <location filename="../ui/controllers/backend_controller.py" line="800"/>
        <source>📁 Current Project</source>
        <translation>📁 Τρέχον έργο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget.py" line="7062"/>
        <source>The filter was not launched: its selection changed or could not be read. Click Filter again.</source>
        <translation>Το φίλτρο δεν ξεκίνησε: η επιλογή του άλλαξε ή δεν ήταν δυνατό να διαβαστεί. Κάντε ξανά κλικ στο «Φίλτρο».</translation>
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
        <translation>ΜΟΝΗ ΕΠΙΛΟΓΗ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="950"/>
        <source>MULTIPLE SELECTION</source>
        <translation>ΠΟΛΛΑΠΛΗ ΕΠΙΛΟΓΗ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1109"/>
        <source>CUSTOM SELECTION</source>
        <translation>ΠΡΟΣΑΡΜΟΣΜΕΝΗ ΕΠΙΛΟΓΗ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1371"/>
        <source>FILTERING</source>
        <translation>ΦΙΛΤΡΑΡΙΣΜΑ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2644"/>
        <source>EXPORTING</source>
        <translation>ΕΞΑΓΩΓΗ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3476"/>
        <source>CONFIGURATION</source>
        <translation>ΔΙΑΜΟΡΦΩΣΗ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3222"/>
        <source>Select CRS for export</source>
        <translation>Επιλογή CRS για εξαγωγή</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3744"/>
        <source>Export</source>
        <translation>Εξαγωγή</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2330"/>
        <source>AND</source>
        <translation>ΚΑΙ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2335"/>
        <source>AND NOT</source>
        <translation>ΚΑΙ ΟΧΙ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2340"/>
        <source>OR</source>
        <translation>Ή</translation>
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
        <translation>Φιλτράρισμα πολλαπλών επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1658"/>
        <source>Additive filtering for the selected layer</source>
        <translation>Αθροιστικό φιλτράρισμα για το επιλεγμένο επίπεδο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="1944"/>
        <source>Geospatial filtering</source>
        <translation>Γεωχωρικό φιλτράρισμα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2034"/>
        <source>Buffer</source>
        <translation>Buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2279"/>
        <source>Expression layer</source>
        <translation>Επίπεδο έκφρασης</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2391"/>
        <source>Geometric predicate</source>
        <translation>Γεωμετρικό κατηγόρημα</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3322"/>
        <source>Output format</source>
        <translation>Μορφή εξόδου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3580"/>
        <source>Filter</source>
        <translation>Φίλτρο</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3642"/>
        <source>Reset</source>
        <translation>Επαναφορά</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2748"/>
        <source>Layers to export</source>
        <translation>Επίπεδα προς εξαγωγή</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2829"/>
        <source>Layers projection</source>
        <translation>Προβολή επιπέδων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2913"/>
        <source>Save styles</source>
        <translation>Αποθήκευση στυλ</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2994"/>
        <source>Datatype export</source>
        <translation>Εξαγωγή τύπου δεδομένων</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3075"/>
        <source>Name of file/directory</source>
        <translation>Όνομα αρχείου/καταλόγου</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2202"/>
        <source>Use centroids instead of full geometries for source layer (faster for complex polygons)</source>
        <translation>Χρήση κεντροειδών αντί πλήρων γεωμετριών για το επίπεδο πηγής (ταχύτερο για σύνθετα πολύγωνα)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2518"/>
        <source>Buffer value in meters (positive=expand, negative=shrink polygons)</source>
        <translation>Τιμή buffer σε μέτρα (θετική=επέκταση, αρνητική=σμίκρυνση πολυγώνων)</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="2606"/>
        <source>Number of segments for buffer precision</source>
        <translation>Αριθμός τμημάτων για ακρίβεια buffer</translation>
    </message>
    <message>
        <location filename="../filter_mate_dockwidget_base.ui" line="3418"/>
        <source>Mode batch</source>
        <translation>Λειτουργία δέσμης</translation>
    </message>
</context>
<context>
    <name>FilterMateOperations</name>
    <message>
        <location filename="../adapters/public_api/operations.py" line="633"/>
        <source>FilterMate was unloaded</source>
        <translation>Το FilterMate εκφορτώθηκε</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="119"/>
        <source>rendered or unsupported raster: cannot be a filter target</source>
        <translation>αποδιδόμενο ή μη υποστηριζόμενο ράστερ: δεν μπορεί να είναι στόχος φίλτρου</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="582"/>
        <source>rendered raster sources require a local colour capture; numeric pixel selections are unavailable</source>
        <translation>οι αποδιδόμενες πηγές ράστερ απαιτούν τοπική καταγραφή χρωμάτων· η αριθμητική επιλογή εικονοστοιχείων δεν είναι διαθέσιμη</translation>
    </message>
    <message>
        <location filename="../adapters/public_api/operations.py" line="654"/>
        <source>the source layer itself was not changed</source>
        <translation>το ίδιο το επίπεδο πηγής δεν τροποποιήθηκε</translation>
    </message>
</context>
<context>
    <name>FilterResultHandler</name>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="347"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} ορατές οντότητες στο κύριο επίπεδο</translation>
    </message>
    <message>
        <location filename="../adapters/filter_result_handler.py" line="340"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Όλα τα φίλτρα διαγράφηκαν - {count} οντότητες ορατές στο κύριο επίπεδο</translation>
    </message>
</context>
<context>
    <name>FinishedHandler</name>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="387"/>
        <source>Task failed</source>
        <translation>Η εργασία απέτυχε</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="388"/>
        <source>Filter failed for: {0}</source>
        <translation>Το φιλτράρισμα απέτυχε για: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="392"/>
        <source> (+{0} more)</source>
        <translation> (+{0} ακόμη)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="439"/>
        <source>Layer(s) filtered</source>
        <translation>Επίπεδο(-α) φιλτραρισμένο(-α)</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="443"/>
        <source>Layer(s) filtered to precedent state</source>
        <translation>Επίπεδο(-α) φιλτραρισμένο(-α) στην προηγούμενη κατάσταση</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="447"/>
        <source>Layer(s) unfiltered</source>
        <translation>Επίπεδο(-α) χωρίς φίλτρο</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="451"/>
        <source>Filter task : {0}</source>
        <translation>Εργασία φιλτραρίσματος : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="472"/>
        <source>Export task : {0}</source>
        <translation>Εργασία εξαγωγής : {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="497"/>
        <source>Exception: {0}</source>
        <translation>Εξαίρεση: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="523"/>
        <source>Filter not applied, previous filter kept: {0}</source>
        <translation>Το φίλτρο δεν εφαρμόστηκε, διατηρείται το προηγούμενο φίλτρο: {0}</translation>
    </message>
    <message>
        <location filename="../core/tasks/finished_handler.py" line="569"/>
        <source>Layer(s) removed during the filter, left out: {0}</source>
        <translation>Επίπεδα που αφαιρέθηκαν κατά το φιλτράρισμα, παραλείφθηκαν: {0}</translation>
    </message>
</context>
<context>
    <name>HeightAboveGround</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="93"/>
        <source>Draw a useful selection zone before computing height above ground remotely</source>
        <translation>Σχεδιάστε μια χρήσιμη ζώνη επιλογής πριν υπολογίσετε εξ αποστάσεως το ύψος πάνω από το έδαφος</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="117"/>
        <source>The DTM and point cloud have no common useful extent</source>
        <translation>Το DTM και το νέφος σημείων δεν έχουν κοινή χρήσιμη έκταση</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="124"/>
        <source>The useful selection has no polygon area</source>
        <translation>Η χρήσιμη επιλογή δεν έχει εμβαδόν πολυγώνου</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/hag_task.py" line="169"/>
        <source>Height above ground covers the useful area only; Unfilter restores the original cloud</source>
        <translation>Το ύψος πάνω από το έδαφος καλύπτει μόνο τη χρήσιμη περιοχή· η Αφαίρεση φίλτρου επαναφέρει το αρχικό νέφος</translation>
    </message>
</context>
<context>
    <name>InputWindow</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="12"/>
        <source>Python Menus &amp; Toolbars</source>
        <translation>Μενού και γραμμές εργαλείων Python</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="24"/>
        <source>Property</source>
        <translation>Ιδιότητα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="25"/>
        <source>Value</source>
        <translation>Τιμή</translation>
    </message>
</context>
<context>
    <name>JsonModel</name>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Property</source>
        <translation>Ιδιότητα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/model.py" line="54"/>
        <source>Value</source>
        <translation>Τιμή</translation>
    </message>
</context>
<context>
    <name>LayerLifecycleService</name>
    <message>
        <location filename="../core/services/layer_lifecycle_service.py" line="262"/>
        <source>PostgreSQL layers detected ({0}) but psycopg2 is not installed. The plugin cannot use these layers. Install psycopg2 to enable PostgreSQL support.</source>
        <translation>Εντοπίστηκαν επίπεδα PostgreSQL ({0}) αλλά το psycopg2 δεν είναι εγκατεστημένο. Το πρόσθετο δεν μπορεί να χρησιμοποιήσει αυτά τα επίπεδα. Εγκαταστήστε το psycopg2 για να ενεργοποιήσετε την υποστήριξη PostgreSQL.</translation>
    </message>
</context>
<context>
    <name>LayerSnapshot</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/snapshots.py" line="619"/>
        <source>The saved source could not be opened</source>
        <translation>Δεν ήταν δυνατό το άνοιγμα της αποθηκευμένης πηγής</translation>
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
        <translation>Επίπεδο PostgreSQL '{0}': Εντοπίστηκαν κατεστραμμένα δεδομένα.

Αυτό το επίπεδο χρησιμοποιεί 'virtual_id' που δεν υπάρχει στο PostgreSQL.
Αυτό το σφάλμα προέρχεται από προηγούμενη έκδοση του FilterMate.

Λύση: Αφαιρέστε αυτό το επίπεδο από το έργο FilterMate και προσθέστε το ξανά.
Βεβαιωθείτε ότι ο πίνακας PostgreSQL έχει ορισμένο PRIMARY KEY.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="1101"/>
        <source>Layer &apos;{0}&apos; has no PRIMARY KEY. Limited features: materialized views disabled. Recommendation: add a PRIMARY KEY for optimal performance.</source>
        <translation>Το επίπεδο '{0}' δεν έχει PRIMARY KEY. Περιορισμένες λειτουργίες: οι υλοποιημένες προβολές είναι απενεργοποιημένες. Σύσταση: προσθέστε ένα PRIMARY KEY για βέλτιστη απόδοση.</translation>
    </message>
    <message>
        <location filename="../core/tasks/layer_management_task.py" line="2203"/>
        <source>Exception: {0}</source>
        <translation>Εξαίρεση: {0}</translation>
    </message>
</context>
<context>
    <name>OGRExpressionBuilder</name>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="499"/>
        <source>{0}: this provider cannot guarantee a complete server filter. Use a bounded local copy before filtering.</source>
        <translation>{0}: αυτός ο πάροχος δεν μπορεί να εγγυηθεί πλήρες φίλτρο διακομιστή. Χρησιμοποιήστε ένα περιορισμένο τοπικό αντίγραφο πριν το φιλτράρισμα.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="699"/>
        <source>{0}: the key values of the selected features could not be read from the web service.</source>
        <translation>{0}: οι τιμές κλειδιών των επιλεγμένων οντοτήτων δεν ήταν δυνατό να διαβαστούν από τη διαδικτυακή υπηρεσία.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="800"/>
        <source>keeps its previous filter</source>
        <translation>διατηρεί το προηγούμενο φίλτρο του</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="802"/>
        <source>is left unfiltered</source>
        <translation>μένει χωρίς φίλτρο</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="807"/>
        <source>{0}: this web service has no unique key field (declared key, id, gml_id, cleabs, objectid...), so the selected features cannot be listed for the server. The layer {1}. An attribute filter, or a local copy of the layer, works.</source>
        <translation>{0}: αυτή η διαδικτυακή υπηρεσία δεν έχει μοναδικό πεδίο κλειδιού (δηλωμένο κλειδί, id, gml_id, cleabs, objectid…), επομένως οι επιλεγμένες οντότητες δεν μπορούν να απαριθμηθούν για τον διακομιστή. Το επίπεδο {1}. Ένα φίλτρο χαρακτηριστικών ή ένα τοπικό αντίγραφο του επιπέδου λειτουργεί.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="813"/>
        <source>{0}: this layer has no unique key field and its feature ids cannot be listed in its filter (a virtual layer needs a unique id column, its uid). The layer {1}.</source>
        <translation>{0}: αυτό το επίπεδο δεν έχει μοναδικό πεδίο κλειδιού και τα αναγνωριστικά των οντοτήτων του δεν μπορούν να απαριθμηθούν στο φίλτρο του (ένα εικονικό επίπεδο χρειάζεται στήλη μοναδικού id, το uid του). Το επίπεδο {1}.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/expression_builder.py" line="822"/>
        <source>{0}: {1} features to list, more than the {2} sent to a web service. The layer {3}. Narrow the selection, use an attribute filter, or work on a local copy of the layer.</source>
        <translation>{0}: {1} οντότητες προς απαρίθμηση, περισσότερες από τις {2} που στέλνονται σε διαδικτυακή υπηρεσία. Το επίπεδο {3}. Περιορίστε την επιλογή, χρησιμοποιήστε φίλτρο χαρακτηριστικών ή εργαστείτε σε τοπικό αντίγραφο του επιπέδου.</translation>
    </message>
</context>
<context>
    <name>OptimizationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="203"/>
        <source>Optimization Settings</source>
        <translation>Ρυθμίσεις βελτιστοποίησης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="230"/>
        <source>Configure Optimization Settings</source>
        <translation>Διαμόρφωση ρυθμίσεων βελτιστοποίησης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="260"/>
        <source>Enable automatic optimizations</source>
        <translation>Ενεργοποίηση αυτόματων βελτιστοποιήσεων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="264"/>
        <source>Ask before applying optimizations</source>
        <translation>Ερώτηση πριν την εφαρμογή βελτιστοποιήσεων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="268"/>
        <source>Auto-Centroid Settings</source>
        <translation>Ρυθμίσεις αυτόματου κεντροειδούς</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="271"/>
        <source>Enable auto-centroid for distant layers</source>
        <translation>Ενεργοποίηση αυτόματου κεντροειδούς για απομακρυσμένα επίπεδα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="276"/>
        <source>Distance threshold (km):</source>
        <translation>Όριο απόστασης (km):</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="283"/>
        <source>Feature threshold:</source>
        <translation>Όριο οντοτήτων:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="293"/>
        <source>Buffer Optimizations</source>
        <translation>Βελτιστοποιήσεις buffer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="296"/>
        <source>Simplify geometry before buffer</source>
        <translation>Απλοποίηση γεωμετρίας πριν το buffer</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="300"/>
        <source>Reduce buffer segments to:</source>
        <translation>Μείωση τμημάτων buffer σε:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="314"/>
        <source>General</source>
        <translation>Γενικά</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="326"/>
        <source>Use materialized views for filtering</source>
        <translation>Χρήση υλοποιημένων προβολών για φιλτράρισμα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="329"/>
        <source>Create spatial indices automatically</source>
        <translation>Αυτόματη δημιουργία χωρικών ευρετηρίων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="338"/>
        <source>Use R-tree spatial index</source>
        <translation>Χρήση χωρικού ευρετηρίου R-tree</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="347"/>
        <source>Use bounding box pre-filter</source>
        <translation>Χρήση προ-φίλτρου πλαισίου οριοθέτησης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="354"/>
        <source>Backends</source>
        <translation>Backends</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="363"/>
        <source>Caching</source>
        <translation>Αποθήκευση στη μνήμη</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="366"/>
        <source>Enable geometry cache</source>
        <translation>Ενεργοποίηση μνήμης cache γεωμετρίας</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="372"/>
        <source>Batch Processing</source>
        <translation>Μαζική επεξεργασία</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="375"/>
        <source>Batch size:</source>
        <translation>Μέγεθος δέσμης:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="385"/>
        <source>Advanced settings affect performance and memory usage. Change only if you understand the implications.</source>
        <translation>Οι προχωρημένες ρυθμίσεις επηρεάζουν την απόδοση και τη χρήση μνήμης. Αλλάξτε μόνο αν κατανοείτε τις επιπτώσεις.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="397"/>
        <source>Advanced</source>
        <translation>Προχωρημένα</translation>
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
        <translation>Σύνδεση με την προηγούμενη συνθήκη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="799"/>
        <source>AND</source>
        <translation>ΚΑΙ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="800"/>
        <source>OR</source>
        <translation>Ή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="801"/>
        <source>Attribute</source>
        <translation>Χαρακτηριστικό</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="804"/>
        <source>Comparison</source>
        <translation>Σύγκριση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="807"/>
        <source>between</source>
        <translation>μεταξύ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Remove this condition</source>
        <translation>Αφαίρεση αυτής της συνθήκης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="818"/>
        <source>Compare with a value or another attribute</source>
        <translation>Σύγκριση με τιμή ή άλλο χαρακτηριστικό</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="821"/>
        <source>value</source>
        <translation>τιμή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="822"/>
        <source>Value</source>
        <translation>Τιμή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="825"/>
        <source>Highest value kept</source>
        <translation>Υψηλότερη τιμή που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>Observed values: {0} to {1}</source>
        <translation>Παρατηρούμενες τιμές: {0} έως {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="905"/>
        <source>No statistics for this attribute</source>
        <translation>Χωρίς στατιστικά για αυτό το χαρακτηριστικό</translation>
    </message>
</context>
<context>
    <name>PointCloudExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1053"/>
        <source>Apply to the other tiles of the dataset</source>
        <translation>Εφαρμογή στα υπόλοιπα πλακίδια του συνόλου δεδομένων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1062"/>
        <source>CLASSES</source>
        <translation>ΚΛΑΣΕΙΣ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1067"/>
        <source>Ground</source>
        <translation>Έδαφος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1068"/>
        <source>Vegetation</source>
        <translation>Βλάστηση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1069"/>
        <source>Buildings</source>
        <translation>Κτίρια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1070"/>
        <source>Above ground</source>
        <translation>Πάνω από το έδαφος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1071"/>
        <source>Water</source>
        <translation>Νερό</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1072"/>
        <source>Without noise</source>
        <translation>Χωρίς θόρυβο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="724"/>
        <source>Check only these classes</source>
        <translation type="obsolete">Επιλογή μόνο αυτών των κλάσεων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="732"/>
        <source>All</source>
        <translation type="obsolete">Όλες</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="733"/>
        <source>None</source>
        <translation type="obsolete">Καμία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1101"/>
        <source>Point classes</source>
        <translation>Κλάσεις σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="474"/>
        <source>ATTRIBUTE RANGES</source>
        <translation type="obsolete">ΕΥΡΗ ΧΑΡΑΚΤΗΡΙΣΤΙΚΩΝ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="480"/>
        <source>Z (m)</source>
        <translation type="obsolete">Z (m)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="481"/>
        <source>Lowest elevation kept</source>
        <translation type="obsolete">Χαμηλότερο υψόμετρο που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="482"/>
        <source>Highest elevation kept</source>
        <translation type="obsolete">Υψηλότερο υψόμετρο που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1348"/>
        <source>Intensity</source>
        <translation>Ένταση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="491"/>
        <source>Lowest intensity kept</source>
        <translation type="obsolete">Χαμηλότερη ένταση που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="492"/>
        <source>Highest intensity kept</source>
        <translation type="obsolete">Υψηλότερη ένταση που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="503"/>
        <source>Return</source>
        <translation type="obsolete">Επιστροφή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="505"/>
        <source>Echo of the laser pulse kept</source>
        <translation type="obsolete">Ηχώ του παλμού λέιζερ που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="832"/>
        <source>Height above DTM ≥</source>
        <translation type="obsolete">Ύψος πάνω από DTM ≥</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1290"/>
        <source>Digital terrain model the height is measured from</source>
        <translation>Ψηφιακό μοντέλο εδάφους από το οποίο μετράται το ύψος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1300"/>
        <source>Keep the points at least this high above the terrain model</source>
        <translation>Διατήρηση των σημείων που βρίσκονται τουλάχιστον τόσο ψηλά πάνω από το μοντέλο εδάφους</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1375"/>
        <source>EXPRESSION</source>
        <translation>ΕΚΦΡΑΣΗ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1379"/>
        <source>Point cloud expression</source>
        <translation>Έκφραση νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1380"/>
        <source>Check the group to edit the expression by hand</source>
        <translation>Επιλέξτε την ομάδα για να επεξεργαστείτε την έκφραση χειροκίνητα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="578"/>
        <source>No elevation statistics for this layer</source>
        <translation type="obsolete">Δεν υπάρχουν στατιστικά υψομέτρου για αυτό το επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1661"/>
        <source>Height above the terrain is unavailable</source>
        <translation>Το ύψος πάνω από το έδαφος δεν είναι διαθέσιμο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="974"/>
        <source>Kept points: {0}</source>
        <translation type="obsolete">Σημεία που διατηρούνται: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Τρέχον φίλτρο: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="991"/>
        <source>none</source>
        <translation type="obsolete">κανένα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>Any</source>
        <translation type="obsolete">Οποιαδήποτε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="874"/>
        <source>First</source>
        <translation type="obsolete">Πρώτη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Last</source>
        <translation type="obsolete">Τελευταία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="875"/>
        <source>Single</source>
        <translation type="obsolete">Μοναδική</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1176"/>
        <source>ATTRIBUTES</source>
        <translation>ΧΑΡΑΚΤΗΡΙΣΤΙΚΑ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1194"/>
        <source>+ Condition</source>
        <translation>+ Συνθήκη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1196"/>
        <source>Add a condition on an attribute of the layer</source>
        <translation>Προσθήκη συνθήκης σε χαρακτηριστικό του επιπέδου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1235"/>
        <source>Returns</source>
        <translation>Επιστροφές</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="811"/>
        <source>Keep the first, last or single returns of the laser pulses</source>
        <translation type="obsolete">Διατήρηση των πρώτων, τελευταίων ή μοναδικών επιστροφών των παλμών λέιζερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1242"/>
        <source>First return (ReturnNumber = 1)</source>
        <translation>Πρώτη επιστροφή (ReturnNumber = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1243"/>
        <source>Last return (ReturnNumber = NumberOfReturns)</source>
        <translation>Τελευταία επιστροφή (ReturnNumber = NumberOfReturns)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1244"/>
        <source>Single return (NumberOfReturns = 1)</source>
        <translation>Μοναδική επιστροφή (NumberOfReturns = 1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1349"/>
        <source>Return number</source>
        <translation>Αριθμός επιστροφής</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1350"/>
        <source>Number of returns</source>
        <translation>Πλήθος επιστροφών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1351"/>
        <source>Classification</source>
        <translation>Ταξινόμηση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1352"/>
        <source>Scan angle</source>
        <translation>Γωνία σάρωσης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1353"/>
        <source>User data</source>
        <translation>Δεδομένα χρήστη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1354"/>
        <source>Point source ID</source>
        <translation>ID πηγής σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1355"/>
        <source>GPS time</source>
        <translation>Χρόνος GPS</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1356"/>
        <source>Red</source>
        <translation>Κόκκινο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1357"/>
        <source>Green</source>
        <translation>Πράσινο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1358"/>
        <source>Blue</source>
        <translation>Μπλε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1359"/>
        <source>Infrared</source>
        <translation>Υπέρυθρο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1360"/>
        <source>Scan direction</source>
        <translation>Κατεύθυνση σάρωσης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1361"/>
        <source>Edge of flight line</source>
        <translation>Άκρη γραμμής πτήσης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1362"/>
        <source>Synthetic</source>
        <translation>Συνθετικό</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1363"/>
        <source>Key point</source>
        <translation>Σημείο κλειδί</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1364"/>
        <source>Withheld</source>
        <translation>Παρακρατημένο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1365"/>
        <source>Overlap</source>
        <translation>Επικάλυψη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1366"/>
        <source>Scanner channel</source>
        <translation>Κανάλι σαρωτή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1367"/>
        <source>Classification flags</source>
        <translation>Σημαίες ταξινόμησης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1368"/>
        <source>Height above ground</source>
        <translation>Ύψος από το έδαφος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Quick class selection</source>
        <translation>Γρήγορη επιλογή κλάσεων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="765"/>
        <source>Quick selection…</source>
        <translation type="obsolete">Γρήγορη επιλογή…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>All classes</source>
        <translation>Όλες οι κλάσεις</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>No class</source>
        <translation>Καμία κλάση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1091"/>
        <source>Invert the selection</source>
        <translation>Αντιστροφή της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1081"/>
        <source>Selection ▾</source>
        <translation>Επιλογή ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1115"/>
        <source>Classes of the standard that hold no point of this layer</source>
        <translation>Κλάσεις του προτύπου που δεν περιέχουν κανένα σημείο αυτού του επιπέδου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1122"/>
        <source>Classes absent from the layer</source>
        <translation>Κλάσεις που λείπουν από το επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1146"/>
        <source>Similar objects: area ×</source>
        <translation>Παρόμοια αντικείμενα: εμβαδόν ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Μικρότερο παρόμοιο αντικείμενο, ως ποσοστό του μικρότερου αντικειμένου του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1149"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Μεγαλύτερο παρόμοιο αντικείμενο, ως πολλαπλάσιο του μεγαλύτερου αντικειμένου του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1164"/>
        <source>to ×</source>
        <translation>έως ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1208"/>
        <source>Pipette on</source>
        <translation>Σταγονόμετρο ενεργό</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1209"/>
        <source>Attribute the value pipette of the rail reads under the click</source>
        <translation>Χαρακτηριστικό που διαβάζει το σταγονόμετρο τιμών της μπάρας κάτω από το κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1224"/>
        <source>Tolerance around the picked value, in % of the observed range of the attribute</source>
        <translation>Ανοχή γύρω από την τιμή που επιλέχθηκε, σε % του παρατηρούμενου εύρους του χαρακτηριστικού</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1236"/>
        <source>Keep every return, or the first, last or single returns of the laser pulses</source>
        <translation>Διατήρηση όλων των επιστροφών ή των πρώτων, τελευταίων ή μοναδικών επιστροφών των παλμών λέιζερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1241"/>
        <source>Any return</source>
        <translation>Οποιαδήποτε επιστροφή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1255"/>
        <source>HEIGHT / DTM</source>
        <translation>ΥΨΟΣ / DTM</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1261"/>
        <source>Always combined (AND) with the active group</source>
        <translation>Πάντα συνδυάζεται (AND) με την ενεργή ομάδα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1265"/>
        <source>PDAL · derived cloud</source>
        <translation>PDAL · παράγωγο νέφος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1267"/>
        <source>The height is computed by PDAL into a derived point cloud, in a background task</source>
        <translation>Το ύψος υπολογίζεται από το PDAL σε παράγωγο νέφος σημείων, σε εργασία παρασκηνίου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1370"/>
        <source>{0} object(s)</source>
        <translation>{0} αντικείμενο(α)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1371"/>
        <source>cut at the window read</source>
        <translation>περικομμένα στο παράθυρο ανάγνωσης</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1372"/>
        <source>shown as the whole class in their box</source>
        <translation>εμφανίζονται ως ολόκληρη η κλάση στο πλαίσιό τους</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1863"/>
        <source>Other classes, absent from the layer ({0})</source>
        <translation>Άλλες κλάσεις, που λείπουν από το επίπεδο ({0})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1954"/>
        <source>An object runs past the largest window read around the click and was cut there</source>
        <translation>Ένα αντικείμενο εκτείνεται πέρα από το μεγαλύτερο παράθυρο ανάγνωσης γύρω από το κλικ και περικόπηκε εκεί</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/point_cloud_exploring_panel.py" line="1956"/>
        <source>Too many objects for the subset of the cloud: the preview and the filtered cloud keep every point of their class in the box around them; the targets are cut by the objects themselves</source>
        <translation>Πάρα πολλά αντικείμενα για το υποσύνολο του νέφους: η προεπισκόπηση και το φιλτραρισμένο νέφος διατηρούν κάθε σημείο της κλάσης τους στο πλαίσιο γύρω τους· οι στόχοι περικόπτονται από τα ίδια τα αντικείμενα</translation>
    </message>
</context>
<context>
    <name>PointCloudFilterWidget</name>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="141"/>
        <source>Point cloud filter</source>
        <translation type="obsolete">Φίλτρο νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="152"/>
        <source>Classification</source>
        <translation type="obsolete">Ταξινόμηση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="157"/>
        <source>All</source>
        <translation type="obsolete">Όλες</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="158"/>
        <source>None</source>
        <translation type="obsolete">Καμία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="167"/>
        <source>Elevation (Z)</source>
        <translation type="obsolete">Υψόμετρο (Z)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="169"/>
        <source>Intensity</source>
        <translation type="obsolete">Ένταση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="175"/>
        <source>Return number</source>
        <translation type="obsolete">Αριθμός επιστροφής</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="199"/>
        <source>Minimum</source>
        <translation type="obsolete">Ελάχιστο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="200"/>
        <source>Maximum</source>
        <translation type="obsolete">Μέγιστο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>Current filter: {0}</source>
        <translation type="obsolete">Τρέχον φίλτρο: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="250"/>
        <source>none</source>
        <translation type="obsolete">κανένα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/point_cloud_filter_widget.py" line="329"/>
        <source>Any</source>
        <translation type="obsolete">Οποιαδήποτε</translation>
    </message>
</context>
<context>
    <name>PointCloudReader</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="221"/>
        <source>A useful extent is required for a remote point cloud</source>
        <translation>Απαιτείται χρήσιμη έκταση για ένα απομακρυσμένο νέφος σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="187"/>
        <source>No PDAL reader for this point cloud format</source>
        <translation>Δεν υπάρχει αναγνώστης PDAL για αυτή τη μορφή νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="217"/>
        <source>PDAL 2.4 or newer with a readable version is required for remote point clouds</source>
        <translation>Απαιτείται PDAL 2.4 ή νεότερο με αναγνώσιμη έκδοση για απομακρυσμένα νέφη σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="219"/>
        <source>Remote point clouds require EPT or COPC for bounded reads</source>
        <translation>Τα απομακρυσμένα νέφη σημείων απαιτούν EPT ή COPC για περιορισμένες αναγνώσεις</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/pdal_cli.py" line="227"/>
        <source>The useful extent must be finite and have positive area</source>
        <translation>Η χρήσιμη έκταση πρέπει να είναι πεπερασμένη και με θετικό εμβαδόν</translation>
    </message>
</context>
<context>
    <name>PointCloudSource</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="513"/>
        <source>Draw a useful selection zone before reading a remote point cloud</source>
        <translation>Σχεδιάστε μια χρήσιμη ζώνη επιλογής πριν διαβάσετε ένα απομακρυσμένο νέφος σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="546"/>
        <source>The remote point cloud could not be read</source>
        <translation>Δεν ήταν δυνατή η ανάγνωση του απομακρυσμένου νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="550"/>
        <source>The remote point cloud rejected the selection</source>
        <translation>Το απομακρυσμένο νέφος σημείων απέρριψε την επιλογή</translation>
    </message>
</context>
<context>
    <name>PointCloudTarget</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="811"/>
        <source>A bounded height-above-ground cloud only supports AND or AND NOT; Unfilter first</source>
        <translation>Ένα περιορισμένο νέφος ύψους πάνω από το έδαφος υποστηρίζει μόνο AND ή AND NOT· κάντε πρώτα Αφαίρεση φίλτρου</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="837"/>
        <source>PDAL 2.4 or newer is required to clip a remote point cloud</source>
        <translation>Απαιτείται PDAL 2.4 ή νεότερο για την περικοπή απομακρυσμένου νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="888"/>
        <source>Disjoint would read the whole remote cloud; choose an inside selection</source>
        <translation>Το Disjoint θα διάβαζε ολόκληρο το απομακρυσμένο νέφος· επιλέξτε επιλογή εσωτερικά</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="895"/>
        <source>The original remote point cloud could not be opened</source>
        <translation>Δεν ήταν δυνατό το άνοιγμα του αρχικού απομακρυσμένου νέφους σημείων</translation>
    </message>
</context>
<context>
    <name>PostgresInfoDialog</name>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="80"/>
        <source>PostgreSQL Session Info</source>
        <translation>Πληροφορίες συνεδρίας PostgreSQL</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="144"/>
        <source>PostgreSQL Active</source>
        <translation>PostgreSQL ενεργό</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="157"/>
        <source>Connection Info</source>
        <translation>Πληροφορίες σύνδεσης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="163"/>
        <source>Connection:</source>
        <translation>Σύνδεση:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="167"/>
        <source>Temp Schema:</source>
        <translation>Προσωρινό σχήμα:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="171"/>
        <source>Status:</source>
        <translation>Κατάσταση:</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="177"/>
        <source>Temporary Views</source>
        <translation>Προσωρινές προβολές</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="196"/>
        <source>Cleanup Options</source>
        <translation>Επιλογές καθαρισμού</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="201"/>
        <source>Auto-cleanup on close</source>
        <translation>Αυτόματος καθαρισμός στο κλείσιμο</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="203"/>
        <source>Automatically cleanup temporary views when FilterMate closes.</source>
        <translation>Αυτόματος καθαρισμός προσωρινών προβολών κατά το κλείσιμο του FilterMate.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="211"/>
        <source>🗑️ Cleanup Now</source>
        <translation>🗑️ Καθαρισμός τώρα</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="212"/>
        <source>Drop all temporary views created by FilterMate in this session.</source>
        <translation>Διαγραφή όλων των προσωρινών προβολών που δημιούργησε το FilterMate σε αυτή τη συνεδρία.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="239"/>
        <source>(No temporary views)</source>
        <translation>(Χωρίς προσωρινές προβολές)</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>No Views</source>
        <translation>Χωρίς προβολές</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="260"/>
        <source>There are no temporary views to clean up.</source>
        <translation>Δεν υπάρχουν προσωρινές προβολές για καθαρισμό.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>Confirm Cleanup</source>
        <translation>Επιβεβαίωση καθαρισμού</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Cleanup Complete</source>
        <translation>Καθαρισμός ολοκληρώθηκε</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Cleanup Issue</source>
        <translation>Πρόβλημα καθαρισμού</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Cleanup Failed</source>
        <translation>Ο καθαρισμός απέτυχε</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="119"/>
        <source>&lt;b&gt;PostgreSQL is not available&lt;/b&gt;&lt;br&gt;&lt;br&gt;To use PostgreSQL features, install psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Then restart QGIS to apply changes.</source>
        <translation>&lt;b&gt;Το PostgreSQL δεν είναι διαθέσιμο&lt;/b&gt;&lt;br&gt;&lt;br&gt;Για να χρησιμοποιήσετε τις λειτουργίες PostgreSQL, εγκαταστήστε το psycopg2:&lt;br&gt;&lt;br&gt;&lt;code&gt;pip install psycopg2-binary&lt;/code&gt;&lt;br&gt;&lt;br&gt;Στη συνέχεια επανεκκινήστε το QGIS για να εφαρμοστούν οι αλλαγές.</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="150"/>
        <source>Session: {0}</source>
        <translation>Συνεδρία: {0}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="188"/>
        <source>{0} view(s) in this session</source>
        <translation>{0} προβολή(-ές) σε αυτή τη συνεδρία</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="267"/>
        <source>This will drop {view_count} temporary view(s) created by FilterMate.

Any unsaved filter results will be lost.

Continue?</source>
        <translation>Αυτό θα διαγράψει {view_count} προσωρινή(-ές) προβολή(-ές) που δημιούργησε το FilterMate.

Τυχόν μη αποθηκευμένα αποτελέσματα φίλτρων θα χαθούν.

Συνέχεια;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="287"/>
        <source>Removed {result.views_dropped} temporary view(s).</source>
        <translation>Αφαιρέθηκαν {result.views_dropped} προσωρινή(-ές) προβολή(-ές).</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="293"/>
        <source>Some views could not be removed: {result.error_message}</source>
        <translation>Ορισμένες προβολές δεν μπόρεσαν να αφαιρεθούν: {result.error_message}</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/postgres_info_dialog.py" line="303"/>
        <source>Error during cleanup: {str(e)}</source>
        <translation>Σφάλμα κατά τον καθαρισμό: {str(e)}</translation>
    </message>
</context>
<context>
    <name>Processing</name>
    <message>
        <location filename="../processing/algorithms/batch_filter_algorithm.py" line="59"/>
        <source>Layers to filter</source>
        <translation>Επίπεδα προς φιλτράρισμα</translation>
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
        <translation>Κανάλι</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="106"/>
        <source>Raster expression</source>
        <translation>Έκφραση ράστερ</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="147"/>
        <source>Layers to export</source>
        <translation>Επίπεδα προς εξαγωγή</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/layer_operations_algorithms.py" line="158"/>
        <source>Output folder</source>
        <translation>Φάκελος εξόδου</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="93"/>
        <source>Geometric predicates</source>
        <translation>Γεωμετρικά κατηγορήματα</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Pixel value</source>
        <translation>Τιμή εικονοστοιχείου</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (degrees)</source>
        <translation>Κλίση (μοίρες)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Slope (%)</source>
        <translation>Κλίση (%)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Aspect (degrees)</source>
        <translation>Προσανατολισμός (μοίρες)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/cross_filter_algorithm.py" line="109"/>
        <source>Hillshade (0-255)</source>
        <translation>Σκίαση αναγλύφου (0-255)</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="191"/>
        <source>Source raster was resampled for capture (grid: {0}).</source>
        <translation>Το ράστερ πηγής επαναδειγματοληπτήθηκε για καταγραφή (πλέγμα: {0}).</translation>
    </message>
    <message>
        <location filename="../processing/algorithms/common.py" line="203"/>
        <source>{0}: target raster was resampled for capture (grid: {1}).</source>
        <translation>{0}: το ράστερ-στόχος επαναδειγματοληπτήθηκε για καταγραφή (πλέγμα: {1}).</translation>
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
        <translation>FilterMate — Δημοσίευση στο Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="127"/>
        <source>&lt;b&gt;Publish Favorites&lt;/b&gt; — write a shareable bundle into a QGIS Resource Sharing collection.</source>
        <translation>&lt;b&gt;Δημοσίευση αγαπημένων&lt;/b&gt; — εγγραφή κοινόχρηστου πακέτου σε συλλογή QGIS Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="147"/>
        <source>Overwrite existing bundle</source>
        <translation>Αντικατάσταση υπάρχοντος πακέτου</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="157"/>
        <source>Publish</source>
        <translation>Δημοσίευση</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="171"/>
        <source>&lt;b&gt;1. Target collection&lt;/b&gt;</source>
        <translation>&lt;b&gt;1. Συλλογή προορισμού&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="184"/>
        <source>Browse...</source>
        <translation>Αναζήτηση…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="192"/>
        <source>&lt;b&gt;2. Bundle file name&lt;/b&gt;</source>
        <translation>&lt;b&gt;2. Όνομα αρχείου πακέτου&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="194"/>
        <source>e.g. zones_bruxelles</source>
        <translation>π.χ. ζωνες_βρυξελλες</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="197"/>
        <source>&lt;small&gt;→ &lt;code&gt;&amp;lt;target&amp;gt;/filter_mate/favorites/&amp;lt;name&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</source>
        <translation>&lt;small&gt;→ &lt;code&gt;&amp;lt;προορισμος&amp;gt;/filter_mate/favorites/&amp;lt;ονομα&amp;gt;.fmfav-pack.json&lt;/code&gt;&lt;/small&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="202"/>
        <source>&lt;b&gt;3. Collection metadata&lt;/b&gt;</source>
        <translation>&lt;b&gt;3. Μεταδεδομένα συλλογής&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="208"/>
        <source>Collection display name</source>
        <translation>Όνομα εμφάνισης συλλογής</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="209"/>
        <source>Name:</source>
        <translation>Όνομα:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="212"/>
        <source>Author / organisation</source>
        <translation>Συντάκτης / οργανισμός</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="213"/>
        <source>Author:</source>
        <translation>Συντάκτης:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="216"/>
        <source>e.g. CC-BY-4.0, MIT, Proprietary</source>
        <translation>π.χ. CC-BY-4.0, MIT, Ιδιοταγής</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="217"/>
        <source>License:</source>
        <translation>Άδεια:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="220"/>
        <source>Comma-separated tags</source>
        <translation>Ετικέτες χωρισμένες με κόμμα</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="221"/>
        <source>Tags:</source>
        <translation>Ετικέτες:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="224"/>
        <source>https://...</source>
        <translation>https://…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="225"/>
        <source>Homepage:</source>
        <translation>Αρχική σελίδα:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="229"/>
        <source>Short description (optional, supports plain text)</source>
        <translation>Σύντομη περιγραφή (προαιρετικό, απλό κείμενο)</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="232"/>
        <source>Description:</source>
        <translation>Περιγραφή:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="244"/>
        <source>&lt;b&gt;4. Favorites to include&lt;/b&gt;</source>
        <translation>&lt;b&gt;4. Αγαπημένα προς συμπερίληψη&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="248"/>
        <source>Select all</source>
        <translation>Επιλογή όλων</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="251"/>
        <source>Select none</source>
        <translation>Αποεπιλογή όλων</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="290"/>
        <source>New collection in Resource Sharing root...</source>
        <translation>Νέα συλλογή στη ρίζα του Resource Sharing…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="294"/>
        <source>Custom directory...</source>
        <translation>Προσαρμοσμένος κατάλογος…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="368"/>
        <source>Will be created under the Resource Sharing root.</source>
        <translation>Θα δημιουργηθεί κάτω από τη ρίζα του Resource Sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="373"/>
        <source>Click &apos;Browse...&apos; to choose a directory.</source>
        <translation>Κάντε κλικ στο 'Αναζήτηση…' για να επιλέξετε έναν κατάλογο.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="379"/>
        <source>Choose a collection directory</source>
        <translation>Επιλέξτε κατάλογο συλλογής</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="430"/>
        <source>{0} / {1} selected</source>
        <translation>{0} / {1} επιλεγμένα</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Cannot create collection</source>
        <translation>Αδύνατη η δημιουργία συλλογής</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="480"/>
        <source>Resource Sharing root not found. Use &apos;Browse...&apos; to pick a directory instead.</source>
        <translation>Δεν βρέθηκε η ρίζα του Resource Sharing. Χρησιμοποιήστε 'Αναζήτηση…' για να επιλέξετε κατάλογο.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Choose a directory</source>
        <translation>Επιλέξτε κατάλογο</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="497"/>
        <source>Click &apos;Browse...&apos; to pick a target directory.</source>
        <translation>Κάντε κλικ στο 'Αναζήτηση…' για να επιλέξετε κατάλογο προορισμού.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>No favorites selected</source>
        <translation>Δεν επιλέχθηκαν αγαπημένα</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="696"/>
        <source>Select at least one favorite to publish.</source>
        <translation>Επιλέξτε τουλάχιστον ένα αγαπημένο προς δημοσίευση.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Publish failed</source>
        <translation>Αποτυχία δημοσίευσης</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="729"/>
        <source>Unknown error.</source>
        <translation>Άγνωστο σφάλμα.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="736"/>
        <source>Published {0} favorite(s) to:

&lt;code&gt;{1}&lt;/code&gt;</source>
        <translation>Δημοσιεύτηκαν {0} αγαπημένα στο:

&lt;code&gt;{1}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="740"/>
        <source>Collection manifest updated:
&lt;code&gt;{0}&lt;/code&gt;</source>
        <translation>Το μανιφέστο της συλλογής ενημερώθηκε:
&lt;code&gt;{0}&lt;/code&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="743"/>
        <source>Publish succeeded</source>
        <translation>Η δημοσίευση ολοκληρώθηκε</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repos unavailable</source>
        <translation>Απομακρυσμένα αποθετήρια μη διαθέσιμα</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="539"/>
        <source>Remote repo manager is not initialized.</source>
        <translation>Ο διαχειριστής απομακρυσμένων αποθετηρίων δεν έχει αρχικοποιηθεί.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="632"/>
        <source>Publishing to &lt;b&gt;{0}&lt;/b&gt; failed.</source>
        <translation>Η δημοσίευση στο &lt;b&gt;{0}&lt;/b&gt; απέτυχε.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="637"/>
        <source>Open clone...</source>
        <translation>Άνοιγμα κλώνου…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="648"/>
        <source>Wrote bundle to:</source>
        <translation>Πακέτο γράφτηκε στο:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="651"/>
        <source>Pushed commit &lt;code&gt;{0}&lt;/code&gt; to &lt;b&gt;{1}&lt;/b&gt;.</source>
        <translation>Το commit &lt;code&gt;{0}&lt;/code&gt; προωθήθηκε στο &lt;b&gt;{1}&lt;/b&gt;.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="656"/>
        <source>No git_url configured — bundle written locally. Push manually via your own tooling.</source>
        <translation>Δεν έχει ρυθμιστεί git_url — πακέτο γράφτηκε τοπικά. Προωθήστε χειροκίνητα με τα δικά σας εργαλεία.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="661"/>
        <source>Nothing to commit — bundle content unchanged.</source>
        <translation>Τίποτα για commit — το περιεχόμενο του πακέτου είναι αμετάβλητο.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Publishing to {0}...</source>
        <translation>Δημοσίευση στο {0}...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="587"/>
        <source>Cancel</source>
        <translation>Ακύρωση</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="591"/>
        <source>Publishing</source>
        <translation>Δημοσίευση</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>Publish in progress</source>
        <translation>Δημοσίευση σε εξέλιξη</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/publish_dialog.py" line="685"/>
        <source>A publish is still running in the background. Wait for it to finish before starting another one.</source>
        <translation>Μια δημοσίευση εκτελείται ακόμη στο παρασκήνιο. Περιμένετε να ολοκληρωθεί πριν ξεκινήσετε άλλη.</translation>
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
        <translation>Περιγραφή:</translation>
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
        <translation>Επίπεδο</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="163"/>
        <source>Mode</source>
        <translation>Mode</translation>
    </message>
    <message>
        <location filename="../extensions/qfieldcloud/ui/push_dialog.py" line="184"/>
        <source>Export</source>
        <translation>Εξαγωγή</translation>
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
        <translation>Κατάσταση:</translation>
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
        <translation>Πληκτρολογήστε για φιλτράρισμα...</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="933"/>
        <source>Select All</source>
        <translation>Επιλογή όλων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="935"/>
        <source>Select All (non subset)</source>
        <translation>Επιλογή όλων (μη υποσύνολο)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="937"/>
        <source>Select All (subset)</source>
        <translation>Επιλογή όλων (υποσύνολο)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="939"/>
        <source>De-select All</source>
        <translation>Αποεπιλογή όλων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="941"/>
        <source>De-select All (non subset)</source>
        <translation>Αποεπιλογή όλων (μη υποσύνολο)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="943"/>
        <source>De-select All (subset)</source>
        <translation>Αποεπιλογή όλων (υποσύνολο)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1599"/>
        <source>Showing the first {0} features sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Εμφανίζονται οι πρώτες {0} οντότητες ταξινομημένες κατά τιμή εμφάνισης. Πληκτρολογήστε στο φίλτρο κειμένου για αναζήτηση σε όλο το επίπεδο· η «Επιλογή όλων» φορτώνει την πλήρη λίστα.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1607"/>
        <source>Showing {0} features of the layer, sorted by display value. Type in the text filter to search the whole layer; &quot;Select All&quot; loads the full list.</source>
        <translation>Εμφανίζονται {0} οντότητες του επιπέδου, ταξινομημένες κατά τιμή εμφάνισης. Πληκτρολογήστε στο φίλτρο κειμένου για αναζήτηση σε όλο το επίπεδο· η «Επιλογή όλων» φορτώνει την πλήρη λίστα.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1614"/>
        <source>Search results for &quot;{0}&quot; over the whole layer.</source>
        <translation>Αποτελέσματα αναζήτησης για «{0}» σε ολόκληρο το επίπεδο.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1808"/>
        <source>Loading values…</source>
        <translation>Φόρτωση τιμών…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1735"/>
        <source>Values</source>
        <translation>Τιμές</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1683"/>
        <source>This expression cannot be evaluated safely for a service.</source>
        <translation type="obsolete">Αυτή η έκφραση δεν μπορεί να αξιολογηθεί με ασφάλεια για μια υπηρεσία.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>Selection</source>
        <translation>Επιλογή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="1779"/>
        <source>The remote list exceeds the safe selection limit. Select fewer features or filter the layer first.</source>
        <translation>Η απομακρυσμένη λίστα υπερβαίνει το ασφαλές όριο επιλογής. Επιλέξτε λιγότερες οντότητες ή φιλτράρετε πρώτα το επίπεδο.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="2008"/>
        <source>Loading selected values…</source>
        <translation>Φόρτωση επιλεγμένων τιμών…</translation>
    </message>
</context>
<context>
    <name>QgsCheckableComboBoxLayer</name>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="339"/>
        <source>Select All</source>
        <translation>Επιλογή όλων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="341"/>
        <source>De-select All</source>
        <translation>Αποεπιλογή όλων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="347"/>
        <source>Select all layers by geometry type (Lines)</source>
        <translation>Επιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Γραμμές)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="349"/>
        <source>De-Select all layers by geometry type (Lines)</source>
        <translation>Αποεπιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Γραμμές)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="351"/>
        <source>Select all layers by geometry type (Points)</source>
        <translation>Επιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Σημεία)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="353"/>
        <source>De-Select all layers by geometry type (Points)</source>
        <translation>Αποεπιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Σημεία)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="355"/>
        <source>Select all layers by geometry type (Polygons)</source>
        <translation>Επιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Πολύγωνα)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="357"/>
        <source>De-Select all layers by geometry type (Polygons)</source>
        <translation>Αποεπιλογή όλων των επιπέδων κατά τύπο γεωμετρίας (Πολύγωνα)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="376"/>
        <source>Select all raster layers</source>
        <translation>Επιλογή όλων των επιπέδων ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="378"/>
        <source>De-select all raster layers</source>
        <translation>Αποεπιλογή όλων των επιπέδων ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="380"/>
        <source>Select all point cloud layers</source>
        <translation>Επιλογή όλων των επιπέδων νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="382"/>
        <source>De-select all point cloud layers</source>
        <translation>Αποεπιλογή όλων των επιπέδων νέφους σημείων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>pixels in the zone</source>
        <translation>εικονοστοιχεία στη ζώνη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>points in the zone</source>
        <translation>σημεία στη ζώνη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="418"/>
        <source>features</source>
        <translation>στοιχεία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="424"/>
        <source>Raster target: the pixels outside the source geometry become NoData (those inside with Disjoint)</source>
        <translation>Στόχος ράστερ: τα εικονοστοιχεία εκτός της γεωμετρίας πηγής γίνονται NoData (αυτά εντός με Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="426"/>
        <source>Point cloud target: the points outside the source geometry are removed (those inside with Disjoint)</source>
        <translation>Στόχος νέφους σημείων: τα σημεία εκτός της γεωμετρίας πηγής αφαιρούνται (αυτά εντός με Disjoint)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="428"/>
        <source>Vector target: the features that satisfy the geometric predicate are kept</source>
        <translation>Διανυσματικός στόχος: διατηρούνται τα στοιχεία που ικανοποιούν το γεωμετρικό κατηγόρημα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="515"/>
        <source>Click the square on the right to test this layer by its centroids</source>
        <translation>Κάντε κλικ στο τετράγωνο δεξιά για να ελέγξετε αυτό το επίπεδο με τα κεντροειδή του</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="343"/>
        <source>Select all vector layers</source>
        <translation>Επιλογή όλων των διανυσματικών επιπέδων</translation>
    </message>
    <message>
        <location filename="../ui/widgets/custom_widgets.py" line="345"/>
        <source>De-select all vector layers</source>
        <translation>Αποεπιλογή όλων των διανυσματικών επιπέδων</translation>
    </message>
</context>
<context>
    <name>RangeHistogramWidget</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="240"/>
        <source>Value range histogram</source>
        <translation>Ιστόγραμμα εύρους τιμών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="241"/>
        <source>Drag the handles, or click, to choose the range of values to keep</source>
        <translation>Σύρετε τις λαβές ή κάντε κλικ για να επιλέξετε το εύρος τιμών που θα διατηρηθεί</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="329"/>
        <source>No histogram</source>
        <translation>Χωρίς ιστόγραμμα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/histogram_widget.py" line="358"/>
        <source>Kept values from {0} to {1}</source>
        <translation>Τιμές που διατηρούνται από {0} έως {1}</translation>
    </message>
</context>
<context>
    <name>RasterExploringPanel</name>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="497"/>
        <source>Band</source>
        <translation type="obsolete">Κανάλι</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="500"/>
        <source>Band whose values are selected</source>
        <translation type="obsolete">Κανάλι του οποίου οι τιμές επιλέγονται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="598"/>
        <source>PIXEL VALUE</source>
        <translation type="obsolete">ΤΙΜΗ ΕΙΚΟΝΟΣΤΟΙΧΕΙΟΥ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="606"/>
        <source>Pixel value of the current band</source>
        <translation type="obsolete">Τιμή εικονοστοιχείου του τρέχοντος καναλιού</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="625"/>
        <source>Last {0} values picked</source>
        <translation type="obsolete">Τελευταίες {0} τιμές που επιλέχθηκαν</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="638"/>
        <source>Click on the map with the pixel picker. Ctrl+click extends the range to the value.</source>
        <translation type="obsolete">Κάντε κλικ στον χάρτη με τον επιλογέα εικονοστοιχείων. Το Ctrl+κλικ επεκτείνει το εύρος μέχρι την τιμή.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1821"/>
        <source>VALUE RANGE</source>
        <translation>ΕΥΡΟΣ ΤΙΜΩΝ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Min</source>
        <translation>Ελάχ.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Lowest value kept</source>
        <translation>Χαμηλότερη τιμή που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Max</source>
        <translation>Μέγ.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1255"/>
        <source>Highest value kept</source>
        <translation>Υψηλότερη τιμή που διατηρείται</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="681"/>
        <source>Preview on the map (hide the other pixels)</source>
        <translation type="obsolete">Προεπισκόπηση στον χάρτη (απόκρυψη των υπόλοιπων εικονοστοιχείων)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="688"/>
        <source>CLASSES</source>
        <translation type="obsolete">ΚΛΑΣΕΙΣ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="692"/>
        <source>Raster classes</source>
        <translation type="obsolete">Κλάσεις ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="696"/>
        <source>All</source>
        <translation type="obsolete">Όλες</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="697"/>
        <source>None</source>
        <translation type="obsolete">Καμία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1275"/>
        <source>RASTER EXPRESSION</source>
        <translation>ΕΚΦΡΑΣΗ ΡΑΣΤΕΡ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1279"/>
        <source>Raster calculator expression; a pixel is kept where it is not 0</source>
        <translation>Έκφραση υπολογιστή ράστερ· ένα εικονοστοιχείο διατηρείται όπου δεν είναι 0</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1280"/>
        <source>Raster expression</source>
        <translation>Έκφραση ράστερ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="721"/>
        <source>Use the range</source>
        <translation type="obsolete">Χρήση του εύρους</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="722"/>
        <source>Write the current value range as an expression</source>
        <translation type="obsolete">Εγγραφή του τρέχοντος εύρους τιμών ως έκφραση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="812"/>
        <source>Selected pixels: {0}</source>
        <translation type="obsolete">Επιλεγμένα εικονοστοιχεία: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1349"/>
        <source>Set a value range first</source>
        <translation>Ορίστε πρώτα ένα εύρος τιμών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2219"/>
        <source>NoData</source>
        <translation>NoData</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="834"/>
        <source>Last values:</source>
        <translation type="obsolete">Τελευταίες τιμές:</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="629"/>
        <source>Value of the current band under the cursor</source>
        <translation type="obsolete">Τιμή του τρέχοντος καναλιού κάτω από τον δρομέα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="635"/>
        <source>Statistics of the current band in the last rectangle drawn on the map</source>
        <translation type="obsolete">Στατιστικά του τρέχοντος καναλιού στο τελευταίο ορθογώνιο που σχεδιάστηκε στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1577"/>
        <source>Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})</source>
        <translation>Κάτω από τον δρομέα: {0}  (X {1:.{3}f}  Y {2:.{3}f})</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>Zone: {0}</source>
        <translation>Ζώνη: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1587"/>
        <source>no pixel</source>
        <translation>κανένα εικονοστοιχείο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2234"/>
        <source>LAST PICKS</source>
        <translation>ΤΕΛΕΥΤΑΙΕΣ ΜΕΤΡΗΣΕΙΣ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="509"/>
        <source>Compute on</source>
        <translation type="obsolete">Υπολογισμός σε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="512"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM.</source>
        <translation type="obsolete">Μέγεθος στο οποίο εφαρμόζεται το εύρος. Η κλίση, ο προσανατολισμός, η σκίαση αναγλύφου και η τραχύτητα διαβάζουν το κανάλι ως DTM.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Pixel value</source>
        <translation>Τιμή εικονοστοιχείου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (degrees)</source>
        <translation>Κλίση (μοίρες)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Slope (%)</source>
        <translation>Κλίση (%)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Aspect (degrees)</source>
        <translation>Προσανατολισμός (μοίρες)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Hillshade (0-255)</source>
        <translation>Σκίαση αναγλύφου (0-255)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1233"/>
        <source>Roughness (TRI, mean difference)</source>
        <translation>Τραχύτητα (TRI, μέση διαφορά)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Usual thresholds of the quantity</source>
        <translation>Συνήθη όρια του μεγέθους</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="677"/>
        <source>Usual thresholds</source>
        <translation type="obsolete">Συνήθη όρια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Flat</source>
        <translation>Επίπεδο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Gentle</source>
        <translation>Ήπια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1931"/>
        <source>Moderate</source>
        <translation>Μέτρια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>Steep</source>
        <translation>Απότομη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>East</source>
        <translation>Ανατολή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1932"/>
        <source>South</source>
        <translation>Νότος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>West</source>
        <translation>Δύση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Shadow</source>
        <translation>Σκιά</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1933"/>
        <source>Lit</source>
        <translation>Φωτισμένο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1109"/>
        <source>Usual thresholds…</source>
        <translation type="obsolete">Συνήθη όρια…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1041"/>
        <source>PIPETTE</source>
        <translation>ΣΤΑΓΟΝΟΜΕΤΡΟ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1105"/>
        <source>Tolerance ±</source>
        <translation>Ανοχή ±</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1112"/>
        <source>Tolerance around the picked color or value, in % of the value range</source>
        <translation>Ανοχή γύρω από το επιλεγμένο χρώμα ή την τιμή, ως % του εύρους τιμών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1113"/>
        <source>Pipette tolerance</source>
        <translation>Ανοχή σταγονομέτρου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1305"/>
        <source>Bands</source>
        <translation>Κανάλια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1231"/>
        <source>What the bands of the image are: the presets and the pipette use them</source>
        <translation type="obsolete">Ποια είναι τα κανάλια της εικόνας: οι προεπιλογές και το σταγονόμετρο τα χρησιμοποιούν</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="576"/>
        <source>Band layout</source>
        <translation type="obsolete">Διάταξη καναλιών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB (red, green, blue)</source>
        <translation type="obsolete">RGB (κόκκινο, πράσινο, μπλε)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>IRC (infrared, red, green)</source>
        <translation type="obsolete">IRC (υπέρυθρο, κόκκινο, πράσινο)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="577"/>
        <source>RGB + infrared</source>
        <translation type="obsolete">RGB + υπέρυθρο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1232"/>
        <source>Write the expression of a usual index (vegetation, water...)</source>
        <translation type="obsolete">Γράψτε την έκφραση ενός συνήθους δείκτη (βλάστηση, νερό...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="585"/>
        <source>Spectral presets</source>
        <translation type="obsolete">Φασματικές προεπιλογές</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1228"/>
        <source>Needs an image of three bands or more (red, green, blue...)</source>
        <translation type="obsolete">Απαιτεί εικόνα τριών καναλιών ή περισσότερων (κόκκινο, πράσινο, μπλε...)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>Vegetation (NDVI &gt; 0.3)</source>
        <translation>Βλάστηση (NDVI &gt; 0.3)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1324"/>
        <source>No vegetation (NDVI &lt; 0.1)</source>
        <translation>Χωρίς βλάστηση (NDVI &lt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Water (NDWI &gt; 0.1)</source>
        <translation>Νερό (NDWI &gt; 0.1)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1325"/>
        <source>Vegetation (excess green)</source>
        <translation>Βλάστηση (περίσσεια πράσινου)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1239"/>
        <source>Spectral presets…</source>
        <translation type="obsolete">Φασματικές προεπιλογές…</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2039"/>
        <source>This pixel has no value (NoData): pick another one</source>
        <translation>Αυτό το εικονοστοιχείο δεν έχει τιμή (NoData): επιλέξτε άλλο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2124"/>
        <source>The tolerance covers every value: lower it</source>
        <translation>Η ανοχή καλύπτει όλες τις τιμές: μειώστε την</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1354"/>
        <source>Range {0} → {1}{2}</source>
        <translation type="obsolete">Εύρος {0} → {1}{2}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1356"/>
        <source>Class(es) {0}</source>
        <translation type="obsolete">Κλάσεις {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1359"/>
        <source>{0} color(s), last: {1}</source>
        <translation type="obsolete">{0} χρώμα(τα), τελευταίο: {1}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1363"/>
        <source>Expression</source>
        <translation type="obsolete">Έκφραση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="778"/>
        <source>BANDS</source>
        <translation>ΚΑΝΑΛΙΑ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="805"/>
        <source>Value of the active band under the cursor</source>
        <translation>Τιμή του ενεργού καναλιού κάτω από τον δείκτη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="811"/>
        <source>Statistics of the active band in the last rectangle drawn on the map</source>
        <translation>Στατιστικά του ενεργού καναλιού στο τελευταίο ορθογώνιο που σχεδιάστηκε στον χάρτη</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="858"/>
        <source>Every band</source>
        <translation>Όλα τα κανάλια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="860"/>
        <source>The value range applies to every colour band at once (a pixel is kept when each band is in the range); the histogram shows the first one</source>
        <translation>Το εύρος τιμών εφαρμόζεται σε όλα τα κανάλια χρώματος ταυτόχρονα (ένα εικονοστοιχείο διατηρείται όταν κάθε κανάλι είναι εντός του εύρους)· το ιστόγραμμα δείχνει το πρώτο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="872"/>
        <source>Active band: the one the range, the histogram and the picker read</source>
        <translation>Ενεργό κανάλι: αυτό που διαβάζουν το εύρος, το ιστόγραμμα και ο επιλογέας</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="881"/>
        <source>The pipette compares this band</source>
        <translation>Το σταγονόμετρο συγκρίνει αυτό το κανάλι</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="991"/>
        <source>Colour the band holds: the spectral indexes and the chips use it. Click to change it</source>
        <translation>Χρώμα του καναλιού: το χρησιμοποιούν οι φασματικοί δείκτες και τα chips. Κάντε κλικ για να το αλλάξετε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1001"/>
        <source>Value at the last click of the pipette</source>
        <translation>Τιμή στο τελευταίο κλικ του σταγονομέτρου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="928"/>
        <source>No colour</source>
        <translation>Χωρίς χρώμα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB</source>
        <translation>RGB</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are red, green, blue</source>
        <translation>Τα κανάλια 1, 2, 3 είναι κόκκινο, πράσινο, μπλε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>IRC</source>
        <translation>CIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)</source>
        <translation>Τα κανάλια 1, 2, 3 είναι υπέρυθρο, κόκκινο, πράσινο (έγχρωμο υπέρυθρο ορθοφωτογράφημα IGN)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>RGB + NIR</source>
        <translation>RGB + NIR</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="936"/>
        <source>Bands 1, 2, 3, 4 are red, green, blue, near infrared</source>
        <translation>Τα κανάλια 1, 2, 3, 4 είναι κόκκινο, πράσινο, μπλε, εγγύς υπέρυθρο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="939"/>
        <source>Every band: {0}</source>
        <translation>Όλα τα κανάλια: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="990"/>
        <source> Roles guessed, to confirm.</source>
        <translation> Οι ρόλοι εικάστηκαν, προς επιβεβαίωση.</translation>
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
        <translation>Κόκκινο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Green</source>
        <translation>Πράσινο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1023"/>
        <source>Blue</source>
        <translation>Μπλε</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1024"/>
        <source>Near infrared</source>
        <translation>Εγγύς υπέρυθρο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1030"/>
        <source>roles guessed, to confirm</source>
        <translation>οι ρόλοι εικάστηκαν, προς επιβεβαίωση</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1045"/>
        <source>Select</source>
        <translation>Επιλογή</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar pixels</source>
        <translation>Παρόμοια εικονοστοιχεία</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every pixel of the raster close to the picked colour or value (the pipette of the rail)</source>
        <translation>Όλα τα εικονοστοιχεία του ράστερ κοντά στο χρώμα ή την τιμή που επιλέχθηκε (το σταγονόμετρο της μπάρας)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Clicked object</source>
        <translation>Αντικείμενο του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Only the patch of such pixels the click falls in: a pool, a roof, a field (the object detector of the rail); Ctrl+click adds another object</source>
        <translation>Μόνο η κηλίδα τέτοιων εικονοστοιχείων στην οποία πέφτει το κλικ: πισίνα, στέγη, χωράφι (ο ανιχνευτής αντικειμένων της μπάρας)· το Ctrl+κλικ προσθέτει άλλο αντικείμενο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Similar objects</source>
        <translation>Παρόμοια αντικείμενα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1049"/>
        <source>Every object of the raster like the clicked one: the patches of such pixels whose area is within the ratios below (the similar objects tool of the rail); Ctrl+click adds another reference object</source>
        <translation>Όλα τα αντικείμενα του ράστερ που μοιάζουν με αυτό του κλικ: οι κηλίδες τέτοιων εικονοστοιχείων με εμβαδόν εντός των λόγων παρακάτω (το εργαλείο παρόμοιων αντικειμένων της μπάρας)· το Ctrl+κλικ προσθέτει άλλο αντικείμενο αναφοράς</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1073"/>
        <source>Area ×</source>
        <translation>Εμβαδόν ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Smallest similar object, as a share of the smallest clicked one</source>
        <translation>Μικρότερο παρόμοιο αντικείμενο, ως ποσοστό του μικρότερου αντικειμένου του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1076"/>
        <source>Largest similar object, as a multiple of the largest clicked one</source>
        <translation>Μεγαλύτερο παρόμοιο αντικείμενο, ως πολλαπλάσιο του μεγαλύτερου αντικειμένου του κλικ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1089"/>
        <source>to ×</source>
        <translation>έως ×</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1092"/>
        <source>same shape</source>
        <translation>ίδιο σχήμα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1095"/>
        <source>Keep only the objects shaped like the clicked ones: their compactness (4π × area / perimeter², 1 for a disc) within the same ratios; off, a road of the area of a pool is a pool</source>
        <translation>Διατήρηση μόνο των αντικειμένων με σχήμα όπως τα επιλεγμένα με κλικ: η συμπάγειά τους (4π × εμβαδόν / περίμετρος², 1 για δίσκο) εντός των ίδιων λόγων· όταν είναι απενεργοποιημένο, ένας δρόμος με το εμβαδόν μιας πισίνας είναι πισίνα</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1146"/>
        <source>Remove this pick</source>
        <translation>Αφαίρεση αυτής της επιλογής</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1225"/>
        <source>Quantity</source>
        <translation>Μέγεθος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM.</source>
        <translation>Μέγεθος στο οποίο εφαρμόζεται το εύρος. Η κλίση, ο προσανατολισμός, η σκίαση ανάγλυφου και η τραχύτητα διαβάζουν το ενεργό κανάλι ως DTM.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1242"/>
        <source>Thresholds ▾</source>
        <translation>Όρια ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert ▾</source>
        <translation>Εισαγωγή ▾</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1288"/>
        <source>Insert a band reference, a usual spectral index or the current range</source>
        <translation>Εισαγωγή αναφοράς καναλιού, συνηθισμένου φασματικού δείκτη ή του τρέχοντος εύρους</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1313"/>
        <source>Spectral indexes</source>
        <translation>Φασματικοί δείκτες</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1318"/>
        <source>Range</source>
        <translation>Εύρος</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1319"/>
        <source>The current value range</source>
        <translation>Το τρέχον εύρος τιμών</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Rendered colors depend on style and scale.</source>
        <translation>Τα αποδιδόμενα χρώματα εξαρτώνται από το στυλ και την κλίμακα.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1391"/>
        <source>Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.</source>
        <translation>Διατίθεται μόνο επιλογή με βάση το χρώμα: οι αριθμητικές ζώνες, οι δείκτες, τα εύρη, οι κλάσεις και τα παράγωγα δεν είναι διαθέσιμα.</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1817"/>
        <source>VALUE RANGE — every band</source>
        <translation>ΕΥΡΟΣ ΤΙΜΩΝ — όλα τα κανάλια</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1819"/>
        <source>VALUE RANGE — band {0}</source>
        <translation>ΕΥΡΟΣ ΤΙΜΩΝ — κανάλι {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1952"/>
        <source>picks on: {0}</source>
        <translation>λαμβάνει τιμές από: {0}</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="1956"/>
        <source>A slope, aspect... reads one band as a DTM: choose a band in BANDS first</source>
        <translation>Η κλίση, ο προσανατολισμός κ.λπ. διαβάζουν ένα κανάλι ως DTM: επιλέξτε πρώτα κανάλι στα ΚΑΝΑΛΙΑ</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2159"/>
        <source>The object could not be read</source>
        <translation>Δεν ήταν δυνατή η ανάγνωση του αντικειμένου</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2161"/>
        <source>No object under the click: raise the tolerance or click another pixel</source>
        <translation>Κανένα αντικείμενο κάτω από το κλικ: αυξήστε την ανοχή ή κάντε κλικ σε άλλο εικονοστοιχείο</translation>
    </message>
    <message>
        <location filename="../ui/widgets/coverage_panels/raster_exploring_panel.py" line="2163"/>
        <source>An object is larger than the window read and was cut: lower the tolerance</source>
        <translation>Ένα αντικείμενο είναι μεγαλύτερο από το παράθυρο ανάγνωσης και περικόπηκε: μειώστε την ανοχή</translation>
    </message>
</context>
<context>
    <name>RasterMaterialization</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="121"/>
        <source>bounded raster capture failed</source>
        <translation>η περιορισμένη καταγραφή ράστερ απέτυχε</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="302"/>
        <source>local raster capture could not be opened</source>
        <translation>δεν ήταν δυνατό το άνοιγμα της τοπικής καταγραφής ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="284"/>
        <source>raster analysis requires a local GDAL capture</source>
        <translation>η ανάλυση ράστερ απαιτεί τοπική καταγραφή GDAL</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="85"/>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="119"/>
        <source>raster capture canceled</source>
        <translation>η καταγραφή ράστερ ακυρώθηκε</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="101"/>
        <source>raster capture destination must be in the session cache</source>
        <translation>ο προορισμός της καταγραφής ράστερ πρέπει να βρίσκεται στην προσωρινή μνήμη της συνεδρίας</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="105"/>
        <source>raster capture provider could not be cloned</source>
        <translation>δεν ήταν δυνατή η κλωνοποίηση του παρόχου καταγραφής ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="38"/>
        <source>raster capture requires a finite, non-empty extent</source>
        <translation>η καταγραφή ράστερ απαιτεί πεπερασμένη, μη κενή έκταση</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="41"/>
        <source>raster capture requires a positive pixel limit</source>
        <translation>η καταγραφή ράστερ απαιτεί θετικό όριο εικονοστοιχείων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="46"/>
        <source>raster capture requires a positive resolution</source>
        <translation>η καταγραφή ράστερ απαιτεί θετική ανάλυση</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="87"/>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="646"/>
        <source>raster capture source could not be opened</source>
        <translation>δεν ήταν δυνατό το άνοιγμα της πηγής καταγραφής ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="79"/>
        <source>raster materialization must run in a worker thread</source>
        <translation>η υλοποίηση ράστερ πρέπει να εκτελείται σε νήμα εργασίας</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="279"/>
        <source>raster selection canceled</source>
        <translation>η επιλογή ράστερ ακυρώθηκε</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="294"/>
        <source>raster selection source could not be opened</source>
        <translation>δεν ήταν δυνατό το άνοιγμα της πηγής επιλογής ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="275"/>
        <source>remote raster selection must run in a worker thread</source>
        <translation>η επιλογή απομακρυσμένου ράστερ πρέπει να εκτελείται σε νήμα εργασίας</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/source_jobs.py" line="281"/>
        <source>rendered color selection requires a local rendered capture</source>
        <translation>η επιλογή αποδιδόμενου χρώματος απαιτεί τοπική καταγραφή απόδοσης</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_materialization.py" line="90"/>
        <source>rendered rasters require a rendered color capture</source>
        <translation>τα αποδιδόμενα ράστερ απαιτούν καταγραφή αποδιδόμενων χρωμάτων</translation>
    </message>
</context>
<context>
    <name>RasterStatisticsTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="20"/>
        <source>FilterMate: raster statistics</source>
        <translation>FilterMate: στατιστικά ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_statistics_task.py" line="64"/>
        <source>Raster sample failed; retry with a smaller visible extent.</source>
        <translation>Η δειγματοληψία ράστερ απέτυχε· δοκιμάστε ξανά με μικρότερη ορατή έκταση.</translation>
    </message>
</context>
<context>
    <name>RasterSurfaceTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/raster_surface_task.py" line="11"/>
        <source>FilterMate: raster preview</source>
        <translation>FilterMate: προεπισκόπηση ράστερ</translation>
    </message>
</context>
<context>
    <name>RasterTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="642"/>
        <source>remote raster target must run in a worker thread</source>
        <translation>ο απομακρυσμένος στόχος ράστερ πρέπει να εκτελείται σε νήμα εργασίας</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="671"/>
        <source>local raster target could not be opened</source>
        <translation>δεν ήταν δυνατό το άνοιγμα του τοπικού στόχου ράστερ</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="681"/>
        <source>Rendered color layers cannot be filter targets.</source>
        <translation>Τα επίπεδα αποδιδόμενων χρωμάτων δεν μπορούν να είναι στόχοι φίλτρου.</translation>
    </message>
</context>
<context>
    <name>RecommendationDialog</name>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="508"/>
        <source>Apply Optimizations?</source>
        <translation>Εφαρμογή βελτιστοποιήσεων;</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="528"/>
        <source>Optimizations Available</source>
        <translation>Διαθέσιμες βελτιστοποιήσεις</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="581"/>
        <source>Skip</source>
        <translation>Παράλειψη</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="587"/>
        <source>Apply Selected</source>
        <translation>Εφαρμογή επιλεγμένων</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="533"/>
        <source>{0} u2022 {1} features</source>
        <translation>{0} u2022 {1} οντότητες</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/optimization_dialog.py" line="571"/>
        <source>Impact: {0}</source>
        <translation>Επίδραση: {0}</translation>
    </message>
</context>
<context>
    <name>RemoteMaterializer</name>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1000"/>
        <source>Partial result: the remote feature limit was reached.</source>
        <translation>Μερικό αποτέλεσμα: επιτεύχθηκε το όριο απομακρυσμένων οντοτήτων.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1002"/>
        <source>Partial result: the remote time limit was reached.</source>
        <translation>Μερικό αποτέλεσμα: επιτεύχθηκε το χρονικό όριο της απομακρυσμένης λειτουργίας.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1004"/>
        <source>Remote filtering was cancelled; the previous filter is kept.</source>
        <translation>Το απομακρυσμένο φιλτράρισμα ακυρώθηκε· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1006"/>
        <source>More than 500 keys would be sent to the service; narrow the selection or use a local copy.</source>
        <translation>Θα στέλνονταν στην υπηρεσία περισσότερα από 500 κλειδιά· περιορίστε την επιλογή ή χρησιμοποιήστε τοπικό αντίγραφο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1008"/>
        <source>The service has no stable key; use a local copy.</source>
        <translation>Η υπηρεσία δεν έχει σταθερό κλειδί· χρησιμοποιήστε τοπικό αντίγραφο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1010"/>
        <source>Select or filter the remote source before spatial filtering.</source>
        <translation>Επιλέξτε ή φιλτράρετε την απομακρυσμένη πηγή πριν από το χωρικό φιλτράρισμα.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1012"/>
        <source>The service filter cannot be proved complete. Select source features or use a local copy.</source>
        <translation>Η πληρότητα του φίλτρου της υπηρεσίας δεν μπορεί να αποδειχθεί. Επιλέξτε οντότητες πηγής ή χρησιμοποιήστε τοπικό αντίγραφο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1014"/>
        <source>The remote source copy is incomplete; the previous filter is kept.</source>
        <translation>Το αντίγραφο της απομακρυσμένης πηγής είναι ελλιπές· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1016"/>
        <source>Partial result: no matching feature was confirmed before the limit; the previous filter is kept.</source>
        <translation>Μερικό αποτέλεσμα: δεν επιβεβαιώθηκε καμία ταιριαστή οντότητα πριν από το όριο· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1018"/>
        <source>The intersecting remote copy is incomplete; a disjoint filter cannot be computed safely.</source>
        <translation>Το τεμνόμενο απομακρυσμένο αντίγραφο είναι ελλιπές· ένα φίλτρο Disjoint δεν μπορεί να υπολογιστεί με ασφάλεια.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1020"/>
        <source>Disjoint combined with another predicate requires a local copy of the remote target.</source>
        <translation>Το Disjoint σε συνδυασμό με άλλο κατηγόρημα απαιτεί τοπικό αντίγραφο του απομακρυσμένου στόχου.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1022"/>
        <source>The remote spatial predicate could not be evaluated; the previous filter is kept.</source>
        <translation>Το απομακρυσμένο χωρικό κατηγόρημα δεν ήταν δυνατό να αξιολογηθεί· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/backends/ogr/filter_executor.py" line="1025"/>
        <source>The remote copy could not be read or filtered; the previous filter is kept.</source>
        <translation>Το απομακρυσμένο αντίγραφο δεν ήταν δυνατό να διαβαστεί ή να φιλτραριστεί· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="138"/>
        <source>Remote materialization requires a background task.</source>
        <translation>Η υλοποίηση απομακρυσμένων δεδομένων απαιτεί εργασία παρασκηνίου.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/remote_materializer.py" line="626"/>
        <source>Filtering a bounded remote copy</source>
        <translation>Φιλτράρισμα περιορισμένου απομακρυσμένου αντιγράφου</translation>
    </message>
</context>
<context>
    <name>RenderedRasterTask</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="88"/>
        <source>FilterMate: rendered colour snapshot</source>
        <translation>FilterMate: στιγμιότυπο αποδιδόμενων χρωμάτων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/rendered_raster.py" line="158"/>
        <source>Rendered snapshot failed; retry with a smaller visible extent.</source>
        <translation>Το στιγμιότυπο απόδοσης απέτυχε· δοκιμάστε ξανά με μικρότερη ορατή έκταση.</translation>
    </message>
</context>
<context>
    <name>SearchableJsonView</name>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="79"/>
        <source>Search configuration... (Ctrl+F)</source>
        <translation>Αναζήτηση διαμόρφωσης... (Ctrl+F)</translation>
    </message>
    <message>
        <location filename="../ui/widgets/json_view/searchable_view.py" line="184"/>
        <source>No match</source>
        <translation>Χωρίς αντιστοιχία</translation>
    </message>
</context>
<context>
    <name>ServerFilterTranslation</name>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="285"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="460"/>
        <source>A FilterMate task is still reading layers. Retry after it finishes.</source>
        <translation>Μια εργασία του FilterMate διαβάζει ακόμη επίπεδα. Δοκιμάστε ξανά μετά την ολοκλήρωσή της.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="289"/>
        <source>A layer with auxiliary storage cannot safely replace its server provider. The previous filter is unchanged.</source>
        <translation>Ένα επίπεδο με βοηθητικό χώρο αποθήκευσης δεν μπορεί να αντικαταστήσει με ασφάλεια τον πάροχο διακομιστή του. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="294"/>
        <source>A remote join cannot be rebuilt on the main thread. The previous filter is unchanged.</source>
        <translation>Μια απομακρυσμένη σύζευξη δεν μπορεί να ξαναχτιστεί στο κύριο νήμα. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="296"/>
        <source>A server filter is already being prepared for this layer.</source>
        <translation>Ετοιμάζεται ήδη ένα φίλτρο διακομιστή για αυτό το επίπεδο.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="189"/>
        <location filename="../adapters/qgis/server_filter_translation.py" line="255"/>
        <source>A server layer can only be modified on its owning thread.</source>
        <translation>Ένα επίπεδο διακομιστή μπορεί να τροποποιηθεί μόνο στο νήμα στο οποίο ανήκει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="278"/>
        <source>Asynchronous server filters require QGIS 3.32 or newer. The previous filter is unchanged.</source>
        <translation>Τα ασύγχρονα φίλτρα διακομιστή απαιτούν QGIS 3.32 ή νεότερο. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="404"/>
        <source>Could not install the prepared server filter.</source>
        <translation>Δεν ήταν δυνατή η εγκατάσταση του προετοιμασμένου φίλτρου διακομιστή.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="67"/>
        <source>Could not preserve the layer state.</source>
        <translation>Δεν ήταν δυνατή η διατήρηση της κατάστασης του επιπέδου.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="282"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="453"/>
        <source>Finish editing the layer before applying a server filter.</source>
        <translation>Ολοκληρώστε την επεξεργασία του επιπέδου πριν εφαρμόσετε φίλτρο διακομιστή.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="104"/>
        <source>Invalid attribute expression.</source>
        <translation>Μη έγκυρη έκφραση χαρακτηριστικού.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="106"/>
        <source>Preparing server attribute filter</source>
        <translation>Προετοιμασία φίλτρου χαρακτηριστικών διακομιστή</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="140"/>
        <source>QGIS cannot translate this predicate to an OGC filter.</source>
        <translation>Το QGIS δεν μπορεί να μεταφράσει αυτό το κατηγόρημα σε φίλτρο OGC.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="336"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>Server filter canceled or timed out. The previous filter is unchanged.</source>
        <translation>Το φίλτρο διακομιστή ακυρώθηκε ή έληξε ο χρόνος του. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="384"/>
        <source>Server filter installation failed and the previous provider could not be restored.</source>
        <translation>Η εγκατάσταση του φίλτρου διακομιστή απέτυχε και ο προηγούμενος πάροχος δεν ήταν δυνατό να αποκατασταθεί.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="376"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="456"/>
        <source>Server filter installation failed. The previous provider was already invalid and could not be restored.</source>
        <translation>Η εγκατάσταση του φίλτρου διακομιστή απέτυχε. Ο προηγούμενος πάροχος ήταν ήδη άκυρος και δεν ήταν δυνατό να αποκατασταθεί.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="391"/>
        <source>Server filter installation failed. The previous provider was restored.</source>
        <translation>Η εγκατάσταση του φίλτρου διακομιστή απέτυχε. Ο προηγούμενος πάροχος αποκαταστάθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="56"/>
        <source>Server filter installation is in progress. Retry after it finishes.</source>
        <translation>Η εγκατάσταση του φίλτρου διακομιστή βρίσκεται σε εξέλιξη. Δοκιμάστε ξανά μετά την ολοκλήρωσή της.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="249"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="280"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="451"/>
        <source>Server filter installation must start on the layer thread.</source>
        <translation>Η εγκατάσταση του φίλτρου διακομιστή πρέπει να ξεκινά στο νήμα του επιπέδου.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="126"/>
        <source>The expression is too complex to translate safely.</source>
        <translation>Η έκφραση είναι πολύ σύνθετη για ασφαλή μετάφραση.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="100"/>
        <source>The expression is too large or contains ambiguous SQL backslash escapes.</source>
        <translation>Η έκφραση είναι πολύ μεγάλη ή περιέχει διφορούμενες ανάστροφες κάθετους SQL.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="354"/>
        <source>The layer changed while preparing its filter. The prepared result was discarded.</source>
        <translation>Το επίπεδο άλλαξε κατά την προετοιμασία του φίλτρου του. Το προετοιμασμένο αποτέλεσμα απορρίφθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="402"/>
        <source>The layer is no longer available. The prepared filter was discarded.</source>
        <translation>Το επίπεδο δεν είναι πλέον διαθέσιμο. Το προετοιμασμένο φίλτρο απορρίφθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="347"/>
        <source>The server rejected the filter or could not be reached. The previous filter is unchanged.</source>
        <translation>Ο διακομιστής απέρριψε το φίλτρο ή δεν ήταν προσβάσιμος. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_subset_job.py" line="287"/>
        <source>This provider and QGIS version do not support verified worker creation. The previous filter is unchanged.</source>
        <translation>Αυτός ο πάροχος και αυτή η έκδοση του QGIS δεν υποστηρίζουν επαληθευμένη δημιουργία εργάτη. Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="225"/>
        <source>{0}: the attribute filter cannot run entirely on the server. Unsupported part: {1}. {2} The previous filter is unchanged.</source>
        <translation>{0}: το φίλτρο χαρακτηριστικών δεν μπορεί να εκτελεστεί εξ ολοκλήρου στον διακομιστή. Μη υποστηριζόμενο τμήμα: {1}. {2} Το προηγούμενο φίλτρο δεν έχει αλλάξει.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="270"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="494"/>
        <source>{0}: the provider rejected the attribute filter. The previous filter was restored.</source>
        <translation>{0}: ο πάροχος απέρριψε το φίλτρο χαρακτηριστικών. Το προηγούμενο φίλτρο αποκαταστάθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/server_filter_translation.py" line="269"/>
        <location filename="../adapters/qgis/server_subset_job.py" line="493"/>
        <source>{0}: the provider rejected the filter and restoration failed.</source>
        <translation>{0}: ο πάροχος απέρριψε το φίλτρο και η αποκατάσταση απέτυχε.</translation>
    </message>
</context>
<context>
    <name>SharedFavoritesPickerDialog</name>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="77"/>
        <source>FilterMate — Shared Favorites</source>
        <translation>FilterMate — Κοινόχρηστα αγαπημένα</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="85"/>
        <source>&lt;b&gt;Shared Favorites&lt;/b&gt; — discovered from QGIS Resource Sharing collections</source>
        <translation>&lt;b&gt;Κοινόχρηστα αγαπημένα&lt;/b&gt; — εντοπίστηκαν από συλλογές QGIS Resource Sharing</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="76"/>
        <source>Search by name, description, collection, or tags...</source>
        <translation type="obsolete">Αναζήτηση με όνομα, περιγραφή, συλλογή ή ετικέτες…</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="129"/>
        <source>Select a shared favorite to preview.</source>
        <translation>Επιλέξτε ένα κοινόχρηστο αγαπημένο για προεπισκόπηση.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="145"/>
        <source>Rescan</source>
        <translation>Επανασάρωση</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="149"/>
        <source>Fork to my project</source>
        <translation>Fork στο έργο μου</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="155"/>
        <source>Close</source>
        <translation>Κλείσιμο</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="211"/>
        <source>No shared collections found. Subscribe to a Resource Sharing repository that ships a &lt;code&gt;filter_mate/favorites&lt;/code&gt; folder, or drop a &lt;code&gt;.fmfav.json&lt;/code&gt; bundle in your resource_sharing collections directory.</source>
        <translation>Δεν βρέθηκαν κοινόχρηστες συλλογές. Εγγραφείτε σε αποθετήριο Resource Sharing με φάκελο &lt;code&gt;filter_mate/favorites&lt;/code&gt;, ή τοποθετήστε ένα πακέτο &lt;code&gt;.fmfav.json&lt;/code&gt; στον κατάλογο συλλογών resource_sharing.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="219"/>
        <source>{0} favorite(s) across {1} collection(s): {2}</source>
        <translation>{0} αγαπημένα σε {1} συλλογές: {2}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="248"/>
        <source>Collection: {0}</source>
        <translation>Συλλογή: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="172"/>
        <source>No shared favorites match your search.</source>
        <translation type="obsolete">Κανένα κοινόχρηστο αγαπημένο δεν ταιριάζει στην αναζήτησή σας.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="280"/>
        <source>&lt;b&gt;{0}&lt;/b&gt; — from &lt;i&gt;{1}&lt;/i&gt;</source>
        <translation>&lt;b&gt;{0}&lt;/b&gt; — από &lt;i&gt;{1}&lt;/i&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="294"/>
        <source>&lt;b&gt;Expression&lt;/b&gt;</source>
        <translation>&lt;b&gt;Έκφραση&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="299"/>
        <source>&lt;b&gt;Remote layers&lt;/b&gt;</source>
        <translation>&lt;b&gt;Απομακρυσμένα επίπεδα&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="313"/>
        <source>&lt;b&gt;Tags:&lt;/b&gt; {0}</source>
        <translation>&lt;b&gt;Ετικέτες:&lt;/b&gt; {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="320"/>
        <source>&lt;b&gt;Provenance&lt;/b&gt;</source>
        <translation>&lt;b&gt;Προέλευση&lt;/b&gt;</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="322"/>
        <source>Author: {0}</source>
        <translation>Συντάκτης: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="324"/>
        <source>License: {0}</source>
        <translation>Άδεια: {0}</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Fork shared favorite</source>
        <translation>Fork κοινόχρηστου αγαπημένου</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="340"/>
        <source>Name in your project:</source>
        <translation>Όνομα στο έργο σας:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>Fork successful</source>
        <translation>Επιτυχές fork</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="354"/>
        <source>&apos;{0}&apos; was added to your favorites.</source>
        <translation>Το «{0}» προστέθηκε στα αγαπημένα σας.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Fork failed</source>
        <translation>Αποτυχία fork</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="360"/>
        <source>Could not add the shared favorite to your project.</source>
        <translation>Αδύνατη η προσθήκη του κοινόχρηστου αγαπημένου στο έργο σας.</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="100"/>
        <source>Search by name, description, collection, author, or tags...</source>
        <translation>Αναζήτηση κατά όνομα, περιγραφή, συλλογή, συγγραφέα ή ετικέτες...</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="107"/>
        <source>Author:</source>
        <translation>Συγγραφέας:</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="180"/>
        <source>All authors</source>
        <translation>Όλοι οι συγγραφείς</translation>
    </message>
    <message>
        <location filename="../extensions/favorites_sharing/ui/shared_picker_dialog.py" line="262"/>
        <source>No shared favorites match your filters.</source>
        <translation>Κανένα κοινόχρηστο αγαπημένο δεν ταιριάζει με τα φίλτρα σας.</translation>
    </message>
</context>
<context>
    <name>SimpleConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="470"/>
        <source>Reset to Defaults</source>
        <translation>Επαναφορά στις προεπιλογές</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Validation Error</source>
        <translation>Σφάλμα επικύρωσης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="502"/>
        <source>Please fix the following errors:

</source>
        <translation>Παρακαλώ διορθώστε τα ακόλουθα σφάλματα:

</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset Configuration</source>
        <translation>Επαναφορά διαμόρφωσης</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="513"/>
        <source>Reset all values to defaults?</source>
        <translation>Επαναφορά όλων των τιμών στις προεπιλογές;</translation>
    </message>
</context>
<context>
    <name>SqlUtils</name>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="266"/>
        <source>FilterMate - PostgreSQL Type Warning</source>
        <translation>FilterMate - Προειδοποίηση τύπου PostgreSQL</translation>
    </message>
    <message>
        <location filename="../infrastructure/database/sql_utils.py" line="270"/>
        <source>Type mismatch in filter: {warning_detail}...</source>
        <translation>Αναντιστοιχία τύπου στο φίλτρο: {warning_detail}...</translation>
    </message>
</context>
<context>
    <name>TabbedConfigDialog</name>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="570"/>
        <source>Reset to Defaults</source>
        <translation>Επαναφορά στις προεπιλογές</translation>
    </message>
    <message>
        <location filename="../ui/dialogs/config_editor_widget.py" line="590"/>
        <source>General</source>
        <translation>Γενικά</translation>
    </message>
</context>
<context>
    <name>TaskCompletionHandler</name>
    <message>
        <location filename="../core/tasks/task_completion_handler.py" line="519"/>
        <source>The filter of {0} could not be applied; it keeps its previous filter.</source>
        <translation>Το φίλτρο του {0} δεν ήταν δυνατό να εφαρμοστεί· διατηρεί το προηγούμενο φίλτρο του.</translation>
    </message>
</context>
<context>
    <name>TaskCompletionMessenger</name>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="280"/>
        <source>{count} features visible in main layer</source>
        <translation>{count} ορατές οντότητες στο κύριο επίπεδο</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="273"/>
        <source>All filters cleared - {count} features visible in main layer</source>
        <translation>Όλα τα φίλτρα διαγράφηκαν - {count} οντότητες ορατές στο κύριο επίπεδο</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="303"/>
        <source>Filter applied to &apos;{layer_name}&apos;: {count} features</source>
        <translation>Φίλτρο εφαρμόστηκε στο '{layer_name}': {count} οντότητες</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="308"/>
        <source> ({expression_preview})</source>
        <translation> ({expression_preview})</translation>
    </message>
    <message>
        <location filename="../adapters/layer_refresh_manager.py" line="324"/>
        <source>Filter cleared for &apos;{layer_name}&apos;: {count} features visible</source>
        <translation>Φίλτρο αφαιρέθηκε για '{layer_name}': {count} ορατές οντότητες</translation>
    </message>
</context>
<context>
    <name>TaskParameterBuilder</name>
    <message>
        <location filename="../adapters/task_builder.py" line="942"/>
        <source>No entity selected! The selection widget lost the feature. Re-select an entity.</source>
        <translation>Δεν επιλέχθηκε οντότητα! Το widget επιλογής έχασε την οντότητα. Επιλέξτε ξανά μια οντότητα.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1060"/>
        <source>Selected layer is invalid or its source cannot be found. Operation cancelled.</source>
        <translation>Το επιλεγμένο επίπεδο δεν είναι έγκυρο ή η πηγή του δεν βρέθηκε. Η λειτουργία ακυρώθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/task_builder.py" line="1075"/>
        <source>Layer &apos;{0}&apos; is not yet initialized. Try selecting another layer then switch back to this one.</source>
        <translation>Το επίπεδο '{0}' δεν έχει αρχικοποιηθεί ακόμη. Δοκιμάστε να επιλέξετε άλλο επίπεδο και μετά επιστρέψτε σε αυτό.</translation>
    </message>
</context>
<context>
    <name>UndoRedoHandler</name>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="227"/>
        <source>Cannot undo: layer invalid or source not found.</source>
        <translation>Δεν είναι δυνατή η αναίρεση: μη έγκυρο επίπεδο ή η πηγή δεν βρέθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="304"/>
        <source>Cannot redo: layer invalid or source not found.</source>
        <translation>Δεν είναι δυνατή η επανάληψη: μη έγκυρο επίπεδο ή η πηγή δεν βρέθηκε.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="64"/>
        <source>The provider rejected the saved filter.</source>
        <translation>Ο πάροχος απέρριψε το αποθηκευμένο φίλτρο.</translation>
    </message>
    <message>
        <location filename="../adapters/undo_redo_handler.py" line="67"/>
        <source>Could not restore the filter: {0}</source>
        <translation>Δεν ήταν δυνατή η αποκατάσταση του φίλτρου: {0}</translation>
    </message>
</context>
<context>
    <name>UrlType</name>
    <message>
        <location filename="../ui/widgets/json_view/datatypes.py" line="572"/>
        <source>Explore ...</source>
        <translation>Εξερεύνηση ...</translation>
    </message>
</context>
<context>
    <name>VectorTargetJob</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="301"/>
        <source>{0}: no unique key field, its features cannot be listed in its filter (a web service, or a virtual layer without a unique id column).</source>
        <translation>{0}: δεν υπάρχει μοναδικό πεδίο κλειδιού, οι οντότητές του δεν μπορούν να απαριθμηθούν στο φίλτρο του (διαδικτυακή υπηρεσία ή εικονικό επίπεδο χωρίς στήλη μοναδικού id).</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="452"/>
        <source>{0} features to list, more than the {1} sent to a web service: narrow the source or use an attribute filter.</source>
        <translation>{0} οντότητες προς απαρίθμηση, περισσότερες από τις {1} που στέλνονται σε διαδικτυακή υπηρεσία: περιορίστε την πηγή ή χρησιμοποιήστε φίλτρο χαρακτηριστικών.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/target_appliers.py" line="392"/>
        <source>{0} AND NOT would keep the features not read; the previous filter is kept.</source>
        <translation>Το {0} AND NOT θα διατηρούσε τις οντότητες που δεν διαβάστηκαν· διατηρείται το προηγούμενο φίλτρο.</translation>
    </message>
</context>
<context>
    <name>VectorTileFilter</name>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="26"/>
        <source>Minimum coverage is unavailable for clipped tile objects</source>
        <translation>Η ελάχιστη κάλυψη δεν είναι διαθέσιμη για περικομμένα αντικείμενα πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="29"/>
        <source>Vector tile targets support Intersect and Disjoint only</source>
        <translation>Οι στόχοι διανυσματικών πλακιδίων υποστηρίζουν μόνο Intersect και Disjoint</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="32"/>
        <source>Vector tile filtering requires a CRS authority code</source>
        <translation>Το φιλτράρισμα διανυσματικών πλακιδίων απαιτεί κωδικό αρχής CRS</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="51"/>
        <source>Vector tile display filter: attributes depend on zoom; objects split across tiles may differ</source>
        <translation>Φίλτρο εμφάνισης διανυσματικών πλακιδίων: τα χαρακτηριστικά εξαρτώνται από το επίπεδο εστίασης· αντικείμενα που διαιρούνται σε πλακίδια μπορεί να διαφέρουν</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_target.py" line="58"/>
        <source>The vector tile style changed while the filter was running; try again</source>
        <translation>Το στυλ των διανυσματικών πλακιδίων άλλαξε ενώ εκτελούνταν το φίλτρο· δοκιμάστε ξανά</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="340"/>
        <source>Filter vector tile attributes</source>
        <translation>Φιλτράρισμα χαρακτηριστικών διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="248"/>
        <source>Invalid vector tile filter expression</source>
        <translation>Μη έγκυρη έκφραση φίλτρου διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="341"/>
        <source>QGIS expression (attributes depend on zoom):</source>
        <translation>Έκφραση QGIS (τα χαρακτηριστικά εξαρτώνται από το επίπεδο εστίασης):</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Redo vector tile filter</source>
        <translation>Επανάληψη φίλτρου διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="298"/>
        <source>Target only. Attributes depend on zoom. Objects split across tiles may be filtered differently.</source>
        <translation>Μόνο στόχος. Τα χαρακτηριστικά εξαρτώνται από το επίπεδο εστίασης. Αντικείμενα που διαιρούνται σε πλακίδια μπορεί να φιλτράρονται διαφορετικά.</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="99"/>
        <source>The saved vector tile style is invalid</source>
        <translation>Το αποθηκευμένο στυλ διανυσματικών πλακιδίων δεν είναι έγκυρο</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="113"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="116"/>
        <source>The saved vector tile symbol property is invalid</source>
        <translation>Η αποθηκευμένη ιδιότητα συμβόλου διανυσματικών πλακιδίων δεν είναι έγκυρη</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="39"/>
        <source>The tile selection exceeds the expression budget (1 MB); use a smaller area</source>
        <translation>Η επιλογή πλακιδίων υπερβαίνει τον προϋπολογισμό έκφρασης (1 MB)· χρησιμοποιήστε μικρότερη περιοχή</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="36"/>
        <source>The tile selection exceeds the vertex budget (2000); use a smaller area</source>
        <translation>Η επιλογή πλακιδίων υπερβαίνει τον προϋπολογισμό κορυφών (2000)· χρησιμοποιήστε μικρότερη περιοχή</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="257"/>
        <source>The vector tile filter exceeds the expression budget (1 MB)</source>
        <translation>Το φίλτρο διανυσματικών πλακιδίων υπερβαίνει τον προϋπολογισμό έκφρασης (1 MB)</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="264"/>
        <source>The vector tile filter exceeds the total style expression budget (1 MB); use a smaller area</source>
        <translation>Το φίλτρο διανυσματικών πλακιδίων υπερβαίνει τον συνολικό προϋπολογισμό εκφράσεων στυλ (1 MB)· χρησιμοποιήστε μικρότερη περιοχή</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="317"/>
        <source>Undo vector tile filter</source>
        <translation>Αναίρεση φίλτρου διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="318"/>
        <source>Unfilter vector tiles</source>
        <translation>Αφαίρεση φίλτρου από διανυσματικά πλακίδια</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="346"/>
        <source>Vector tile attribute filter</source>
        <translation>Φίλτρο χαρακτηριστικών διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/favorites_bridge.py" line="131"/>
        <source>Vector tile favorite</source>
        <translation>Αγαπημένο διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="349"/>
        <source>Vector tile filter</source>
        <translation>Φίλτρο διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="172"/>
        <source>Vector tile filtering requires a basic renderer</source>
        <translation>Το φιλτράρισμα διανυσματικών πλακιδίων απαιτεί βασικό renderer</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="125"/>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="175"/>
        <source>Vector tile filtering requires basic labeling</source>
        <translation>Το φιλτράρισμα διανυσματικών πλακιδίων απαιτεί βασική επισήμανση</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="353"/>
        <source>Vector tile filters</source>
        <translation>Φίλτρα διανυσματικών πλακιδίων</translation>
    </message>
    <message>
        <location filename="../adapters/qgis/coverage_layers/vector_tile_filters.py" line="294"/>
        <source>Vector tiles</source>
        <translation>Διανυσματικά πλακίδια</translation>
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
        <translation type="obsolete">Γεωμετρία πηγής: τα στοιχεία που επιλέχθηκαν στο EXPLORING</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="624"/>
        <source>Source geometry: the selected pixels, vectorized</source>
        <translation type="obsolete">Γεωμετρία πηγής: τα επιλεγμένα εικονοστοιχεία, διανυσματοποιημένα</translation>
    </message>
    <message>
        <location filename="../ui/controllers/coverage_dock_extras.py" line="638"/>
        <source>Kept points</source>
        <translation type="obsolete">Σημεία που διατηρούνται</translation>
    </message>
</context>
</TS>
