"""QgsProcessingProvider exposant les algorithmes FilterMate dans la Processing Toolbox."""

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


class FilterMateProcessingProvider(QgsProcessingProvider):
    """Fournisseur Processing regroupant les algorithmes et les modèles FilterMate."""

    def __init__(self):
        super().__init__()
        self._waiting_for_registry = False

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
