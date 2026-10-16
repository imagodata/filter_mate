"""QgsProcessingProvider exposant les algorithmes FilterMate dans la Processing Toolbox."""

import atexit
import glob
import os

from qgis.core import QgsApplication, QgsProcessingModelAlgorithm, QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from ..infrastructure.logging import get_logger
from .algorithms.batch_filter_algorithm import BatchFilterAlgorithm
from .algorithms.cross_filter_algorithm import (
    CrossFilterAlgorithm,
    CrossFilterFromGeometryAlgorithm,
    CrossFilterFromPointCloudAlgorithm,
    CrossFilterFromRasterAlgorithm,
)
from .algorithms.layer_operations_algorithms import (
    ApplyFavoriteAlgorithm,
    ClearFiltersAlgorithm,
    ExportFilteredLayersAlgorithm,
    FilterPointCloudAlgorithm,
)

logger = get_logger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def _purge_cache_at_exit():
    """Sans interface (``qgis_process``) : supprime les fichiers dérivés du lancement à la sortie.

    Le plugin n'y est jamais déchargé (le déchargement vide la session du
    cache) et ``qgis_process`` n'enregistre pas le projet : plus rien n'y fait
    référence. À défaut, la session suivante supprime le dossier (non verrouillé).
    """
    try:
        from ..adapters.qgis.coverage_layers import cache
        cache.purge_session()
    except Exception:  # nosec B110 - interpreter shutting down, the next session cleans up
        pass


class FilterMateProcessingProvider(QgsProcessingProvider):
    """Fournisseur Processing regroupant les algorithmes et les modèles FilterMate."""

    _exit_purge_registered = False

    def __init__(self):
        super().__init__()
        self._waiting_for_registry = False
        try:
            from qgis.utils import iface
        except ImportError:
            iface = None
        if iface is None and not FilterMateProcessingProvider._exit_purge_registered:
            atexit.register(_purge_cache_at_exit)
            FilterMateProcessingProvider._exit_purge_registered = True

    def loadAlgorithms(self):
        """Enregistre les algorithmes FilterMate, puis les modèles livrés (``processing/models``).

        Le registre n'ajoute le fournisseur qu'après ce premier chargement : les
        étapes ``filtermate:*`` des modèles ne seraient pas encore résolues et
        leurs sorties (dossier) disparaîtraient. Les modèles sont donc chargés
        par un rafraîchissement, dès que le fournisseur est enregistré.
        """
        for algorithm in (BatchFilterAlgorithm(), CrossFilterAlgorithm(), CrossFilterFromRasterAlgorithm(),
                          CrossFilterFromPointCloudAlgorithm(), CrossFilterFromGeometryAlgorithm(),
                          FilterPointCloudAlgorithm(), ClearFiltersAlgorithm(), ApplyFavoriteAlgorithm(),
                          ExportFilteredLayersAlgorithm()):
            self.addAlgorithm(algorithm)
        registry = QgsApplication.processingRegistry()
        if registry.providerById(self.id()) is not None:
            self._load_models()
        elif not self._waiting_for_registry:
            self._waiting_for_registry = True
            registry.providerAdded.connect(self._on_provider_added)

    def _on_provider_added(self, provider_id):
        if provider_id != self.id():
            return
        try:
            QgsApplication.processingRegistry().providerAdded.disconnect(self._on_provider_added)
        except (TypeError, RuntimeError):
            pass
        self._waiting_for_registry = False
        self.refreshAlgorithms()

    def _load_models(self):
        for path in sorted(glob.glob(os.path.join(MODELS_DIR, "*.model3"))):
            model = QgsProcessingModelAlgorithm()
            if model.fromFile(path):
                self.addAlgorithm(model)
            else:
                logger.warning(f"FilterMate: model not loaded: {path}")

    def id(self):
        """Retourne l'identifiant technique du fournisseur."""
        return "filtermate"

    def name(self):
        """Retourne le nom affiché du fournisseur."""
        return "FilterMate"

    def icon(self):
        """Retourne l'icône du fournisseur (icône du plugin si disponible)."""
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return super().icon()
