"""QgsProcessingProvider exposant les algorithmes FilterMate dans la Processing Toolbox."""

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms.batch_filter_algorithm import BatchFilterAlgorithm


class FilterMateProcessingProvider(QgsProcessingProvider):
    """Fournisseur Processing regroupant les algorithmes FilterMate."""

    def loadAlgorithms(self):
        """Enregistre les algorithmes FilterMate auprès de Processing."""
        self.addAlgorithm(BatchFilterAlgorithm())

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
